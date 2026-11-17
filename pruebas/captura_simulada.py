"""
Prueba de punta a punta de captura.py y plot_csv.py SIN cámara ni
pantalla. Se reemplazan por simulaciones:
  - cv2.VideoCapture: cámaras que devuelven imágenes negras;
  - las ventanas de OpenCV (imshow, waitKey...): no se abre nada, y
    waitKey "presiona" teclas en frames fijos ('q' para salir);
  - HandLandmarker de MediaPipe: devuelve una mano sintética de palma
    8.5 cm que va y vuelve a 20 cm/s a 45 cm de la cámara, proyectada en
    un par de cámaras simulado (el mismo de pruebas/estereo_simulado.py)
    con 0.7 px de ruido. La cámara 2 no la detecta si la muñeca queda
    fuera de su imagen, como MediaPipe real.
Todo lo demás es el código real: HandTracker, estereo.py, YOLO (si el
modelo ya está descargado en models/), la velocidad, el visor 3D (dibuja
en memoria) y CsvRecorder. Los CSV se escriben en una carpeta temporal,
no en capturas/.

Uso:
    ./venv/bin/python3 pruebas/captura_simulada.py

De aquí salen los números del README sobre --palma-cm (28-B), la
captura con dos cámaras (28-D) y el CSV escrito durante la sesión.
Sale con código 1 si algo queda fuera de tolerancia.
"""

import csv
import sys
import tempfile
import time
from collections import namedtuple
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import captura  # noqa: E402
import estereo_simulado as sim  # noqa: E402
from mediapipe.tasks.python import vision  # noqa: E402

W, H = sim.W, sim.H
PALM_CM = 8.5
SPEED_CM_S = 20.0
HAS_YOLO = (REPO / "models" / "yolo11s-pose.pt").exists()

Category = namedtuple("Category", "category_name score")
Result = namedtuple("Result", "hand_landmarks handedness")


def hand_at(t):
    """
    Mano 3D (cm) en el instante t: va y viene entre x=+2 y x=+22 a 20 cm/s.
    En ese recorrido la cámara 2 la ve entera en el medio y con algunos
    dedos fuera de su imagen en los extremos, como pasa en la realidad.
    """
    pts = [np.zeros(3)]
    for f, ang in enumerate(np.radians([-50, -20, 0, 15, 30])):
        d = np.array([np.sin(ang), -np.cos(ang), 0.0])
        for k in range(1, 5):
            pts.append(d * PALM_CM * (0.45 + 0.3 * k) + np.array([0, 0, -1.2 * k * (f % 2)]))
    pts = np.array(pts)
    pts[9] = np.array([0, -PALM_CM, 0])
    phase = (SPEED_CM_S * t) % 40
    x = 2 + (phase if phase < 20 else 40 - phase)
    return pts + np.array([x, 3, 45.0])


class State:
    """Lo que cambia entre corridas: qué ve la cámara 2, teclas, etc."""
    cam2_sees = lambda ts: True  # noqa: E731
    no_hands = False
    frames = 60
    keys = {}
    calls = 0
    on_key = None       # función extra llamada en cada waitKey
    landmarkers = 0


class FakeLandmarker:
    """HandLandmarker simulado: el 1º creado es la cámara 1, el 2º la 2."""

    def __init__(self):
        State.landmarkers += 1
        self.cam = State.landmarkers
        self.last_ts = -1

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def close(self):
        pass

    def detect_for_video(self, _image, ts):
        assert ts > self.last_ts, "los timestamps tienen que crecer siempre"
        self.last_ts = ts
        if State.no_hands:
            return Result([], [])
        X = hand_at(ts / 1000)
        rng = np.random.default_rng(ts)
        if self.cam == 1:
            p, _ = cv2.projectPoints(X, np.zeros(3), np.zeros(3), sim.K1, sim.D1)
            p = p[:, 0] + rng.normal(0, 0.7, (21, 2))
            frame_w_cm = W * X[0, 2] / sim.K1[0, 0]
            # z "de MediaPipe": relativa a la muñeca y al 60 % de la real,
            # para que se note la diferencia con la z medida en estéreo.
            lms = [sim.Landmark(1 - u / W, v / H, (X[i, 2] - X[0, 2]) / frame_w_cm * 0.6)
                   for i, (u, v) in enumerate(p)]
            return Result([lms], [[Category("Left", 0.95)]])  # "Left" crudo = Right real
        if not State.cam2_sees(ts):
            return Result([], [])
        p, _ = cv2.projectPoints((sim.R_TRUE @ X.T).T + sim.T_TRUE, np.zeros(3),
                                 np.zeros(3), sim.K2, sim.D2)
        p = p[:, 0] + rng.normal(0, 0.7, (21, 2))
        # Como MediaPipe real: sin la muñeca en la imagen no hay mano (si
        # solo se salen dedos, sí la devuelve, con esos puntos afuera).
        if not (0 <= p[0, 0] < W and 0 <= p[0, 1] < H):
            return Result([], [])
        return Result([[sim.Landmark(u / W, v / H, 0.0) for u, v in p]],
                      [[Category("Right", 0.9)]])


class FakeCapture:
    """Cámara simulada: imágenes negras de W x H."""

    def __init__(self, _index):
        pass

    def isOpened(self):
        return True

    def set(self, *_):
        return True

    def get(self, prop):
        return {cv2.CAP_PROP_FRAME_WIDTH: W, cv2.CAP_PROP_FRAME_HEIGHT: H}.get(prop, 0)

    def read(self):
        time.sleep(0.02)
        return True, np.zeros((H, W, 3), np.uint8)

    def grab(self):
        time.sleep(0.01)
        return True

    def retrieve(self):
        return True, np.zeros((H, W, 3), np.uint8)

    def release(self):
        pass


def fake_wait_key(_delay=0):
    """waitKey simulado: 'q' en el frame State.frames, otras teclas en State.keys."""
    State.calls += 1
    if State.on_key:
        State.on_key(State.calls)
    if State.calls == State.frames:
        return ord("q")
    return State.keys.get(State.calls, -1)


def patch_everything(out_dir):
    """Reemplaza cámaras, ventanas y MediaPipe por las simulaciones."""
    cv2.VideoCapture = FakeCapture
    for name in ("imshow", "namedWindow", "setMouseCallback", "destroyWindow"):
        setattr(cv2, name, lambda *a, **k: None)
    cv2.destroyAllWindows = lambda: None
    cv2.getWindowProperty = lambda *a: 1
    cv2.waitKey = fake_wait_key
    vision.HandLandmarker.create_from_options = staticmethod(lambda _o: FakeLandmarker())
    captura.CsvRecorder.__init__.__defaults__ = (out_dir,)


def run_capture(argv, out_dir, frames=60, keys=None):
    """Corre captura.main() y devuelve las filas del CSV nuevo (o [])."""
    State.landmarkers, State.calls, State.frames = 0, 0, frames
    State.keys = keys or {}
    before = set(out_dir.glob("*.csv"))
    sys.argv = ["captura.py", *argv]
    captura.main()
    new = sorted(set(out_dir.glob("*.csv")) - before)
    return list(csv.DictReader(open(new[-1]))) if new else []


def wrist_speed(rows):
    """Mediana de la rapidez de la muñeca desde el frame 10 (ya arrancado)."""
    wrist = [r for r in rows if r["landmark_index"] == "0"]
    return float(np.median([float(r["rapidez_cm_s"]) for r in wrist[10:]]))


def main():
    """Corre todos los casos y sale con 0 (OK) o 1 (FALLA)."""
    results = []

    def check(name, passed, detail):
        results.append(passed)
        print(f"  {'OK   ' if passed else 'FALLA'} {name}: {detail}")

    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        calib = out_dir / "estereo.npz"
        sim.make_calibration(calib)
        patch_everything(out_dir)
        yolo = [] if HAS_YOLO else ["--sin-antebrazo"]
        print(f"(YOLO {'real' if HAS_YOLO else 'desactivado: falta models/yolo11s-pose.pt'})")

        print("1. Una cámara: palma supuesta vs --palma-cm (28-B)")
        rows = run_capture(["--sin-antebrazo", "--sin-3d"], out_dir)
        v_default = wrist_speed(rows)
        check("palma por defecto (9.5 cm, la real es 8.5)", 21 < v_default < 24,
              f"{v_default:.1f} cm/s (real {SPEED_CM_S}): sale ~12 % alta, como se espera")
        rows = run_capture(["--sin-antebrazo", "--palma-cm", str(PALM_CM)], out_dir)
        v_palm = wrist_speed(rows)
        check("--palma-cm 8.5 (con vista 3D)", abs(v_palm - SPEED_CM_S) < 1,
              f"{v_palm:.1f} cm/s; columna palma_cm = {rows[0]['palma_cm']}")
        check("columnas del CSV", list(rows[0])[-4:] == ["palma_cm", "x_cm", "y_cm", "z_cm"]
              and len(rows[0]) == len(captura.CSV_HEADER), f"{len(rows[0])} columnas")

        print("2. Dos cámaras (28-D)")
        State.cam2_sees = lambda ts: True
        rows = run_capture(["--estereo", "--calibracion", str(calib), *yolo], out_dir,
                           frames=80, keys={20: ord("f"), 30: ord("v"), 40: ord("v"),
                                            50: ord("1")})
        wrist = [r for r in rows if r["landmark_index"] == "0"]
        palms = sorted({float(r["palma_cm"]) for r in wrist[10:]})
        z = [float(r["z_cm"]) for r in wrist if r["z_cm"]]
        v = wrist_speed(rows)
        check("palma medida", abs(palms[0] - PALM_CM) < 0.2 and abs(palms[-1] - PALM_CM) < 0.2,
              f"{palms[0]:.2f}-{palms[-1]:.2f} cm (real {PALM_CM})")
        check("rapidez", abs(v - SPEED_CM_S) < 1, f"{v:.1f} cm/s (real {SPEED_CM_S})")
        check("distancia a la cámara", abs(np.median(z) - 45) < 0.5, f"{np.median(z):.1f} cm (real 45)")
        sources = {r["fuente"] for r in rows if int(r["landmark_index"]) < 21}
        missing = sum(1 for r in rows if int(r["landmark_index"]) < 21 and not r["x_cm"])
        check("fuente", sources == {"estereo"},
              f"estereo en los puntos 0-20; {missing} puntos sin cm (fuera del cuadro "
              "de la cámara 2 en los extremos del recorrido)")

        State.cam2_sees = lambda ts: (ts // 450) % 2 == 0
        rows = run_capture(["--estereo", "--calibracion", str(calib), "--sin-antebrazo",
                            "--sin-3d"], out_dir, frames=80)
        speeds = [float(r["rapidez_cm_s"]) for r in rows if r["landmark_index"] == "0"][10:]
        check("la cámara 2 ve la mano de a ratos",
              abs(np.median(speeds) - SPEED_CM_S) < 1 and np.percentile(speeds, 95) < 30,
              f"mediana {np.median(speeds):.1f} cm/s, p95 {np.percentile(speeds, 95):.1f} "
              "(sin picos por cambio de escala)")

        State.cam2_sees = lambda ts: False
        rows = run_capture(["--estereo", "--calibracion", str(calib), "--sin-antebrazo",
                            "--sin-3d"], out_dir)
        check("la cámara 2 nunca ve la mano", {r["fuente"] for r in rows} == {"mediapipe"}
              and rows[0]["palma_cm"] == "9.5", "vuelve a una cámara con la palma supuesta")
        State.cam2_sees = lambda ts: True

        print("3. CSV durante la sesión y formas de salir (28-B, 28-E)")
        seen = {}

        def spy(call):
            if call == 50:
                f = sorted(out_dir.glob("*.csv"))[-1]
                seen["bytes"] = f.stat().st_size
        State.on_key = spy
        rows = run_capture(["--sin-antebrazo", "--sin-3d"], out_dir, frames=70)
        State.on_key = None
        check("el CSV ya está en disco en el frame 50", seen.get("bytes", 0) > 50_000,
              f"{seen.get('bytes', 0)} bytes antes de salir")

        def ctrl_c(call):
            if call == 30:
                raise KeyboardInterrupt
        State.on_key = ctrl_c
        rows = run_capture(["--sin-antebrazo", "--sin-3d"], out_dir, frames=999)
        State.on_key = None
        check("Ctrl+C a mitad", len(rows) == 30 * 21, f"{len(rows)} filas guardadas (30 frames)")

        State.no_hands = True
        rows = run_capture(["--sin-antebrazo", "--sin-3d"], out_dir, frames=15)
        State.no_hands = False
        check("sin manos no se crea CSV", rows == [], "ningún archivo nuevo")

        n_before = len(list(out_dir.glob("*.csv")))
        run_capture(["--sin-antebrazo", "--sin-3d"], out_dir, frames=5)
        run_capture(["--sin-antebrazo", "--sin-3d"], out_dir, frames=5)
        n_after = len(list(out_dir.glob("*.csv")))
        check("dos sesiones seguidas no se pisan", n_after - n_before == 2,
              f"{n_after - n_before} archivos nuevos")

        print("4. plot_csv.py con el CSV grabado con --estereo")
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import kinematics
        import plot_csv
        import viewer3d
        plt.show = lambda *a, **k: None
        State.cam2_sees = lambda ts: True
        run_capture(["--estereo", "--calibracion", str(calib), "--sin-antebrazo", "--sin-3d"],
                    out_dir, frames=60)
        stereo_csv = sorted(out_dir.glob("*.csv"))[-1]
        rendered = []
        original = viewer3d.DualPOVViewer.render

        def record(self, hands, *a, **k):
            rendered.append(hands)
            return original(self, hands, *a, **k)
        viewer3d.DualPOVViewer.render = record
        for extra, expected in (([], PALM_CM), (["--palma-cm", "10"], 10.0)):
            rendered.clear()
            State.calls, State.frames, State.keys = 0, 40, {}
            sys.argv = ["plot_csv.py", str(stereo_csv), "--3d", *extra]
            plot_csv.main()
            hands = [h for frame in rendered for h in frame]
            palm = np.median([h["palm_cm"] for h in hands])
            speed = np.median([kinematics.speed_cm_s(h["velocities"].get(0, (0, 0, 0)),
                                                     kinematics.hand_scale(h)) for h in hands[10:]])
            check(f"--3d {' '.join(extra) or '(palma del CSV)'}", abs(palm - expected) < 0.1,
                  f"palma {palm:.2f} cm, rapidez mediana {speed:.1f} cm/s")
        viewer3d.DualPOVViewer.render = original
        sys.argv = ["plot_csv.py", str(stereo_csv), "--frame", "3"]
        plot_csv.main()
        check("2D con --frame", True, "sin errores")

        print("5. Pausa y Unreal (19-A), CSV para artículos (17-B)")
        import socket
        import unreal_bridge
        State.cam2_sees = lambda ts: True
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", 0))
        sock.setblocking(False)
        dest = f"127.0.0.1:{sock.getsockname()[1]}"

        def packets():
            """Mensajes OSC recibidos desde la última vez (decodificados)."""
            out = []
            while True:
                try:
                    out.append(unreal_bridge.osc_decode(sock.recv(4096)))
                except BlockingIOError:
                    return out

        arts = out_dir / "articulos"

        def exported():
            """{formato: N de la muñeca} de los CSV para artículos que haya en articulos/."""
            out = {}
            for p in arts.glob("*.csv"):
                rows = list(csv.DictReader(open(p, encoding="utf-8")))
                n_col = "N" if p.stem.endswith("ingenieria") else "n"
                out[p.stem.rsplit("_", 1)[1]] = int(rows[0][n_col])
            return out

        def clear_exports():
            """Borra los CSV para artículos de la prueba anterior."""
            for p in arts.glob("*.csv"):
                p.unlink()

        SPACE = ord(" ")
        packets()
        rows = run_capture(["--sin-antebrazo", "--sin-3d", "--unreal", dest], out_dir, frames=70,
                           keys={20: SPACE, 40: SPACE})
        frames = sorted({int(r["frame"]) for r in rows})
        check("pausa: no se graba mientras está en pausa",
              frames == list(range(50)), f"{len(frames)} frames seguidos (0-{frames[-1]}); "
              "20 vueltas del bucle en pausa")
        msgs = packets()
        frame_msgs = [a for ad, a in msgs if ad == unreal_bridge.ADDR_FRAME]
        check("pausa: tampoco se manda nada a Unreal", [int(a[0]) for a in frame_msgs] == list(range(50)),
              f"{len(frame_msgs)} mensajes de fotograma, números 0-{frame_msgs[-1][0]:.0f} sin saltos")
        hand_msgs = [(ad, a) for ad, a in msgs if ad.startswith("/handmotion/") and ad != unreal_bridge.ADDR_FRAME]
        ad, a = hand_msgs[0]
        floats = a
        check("Unreal: un mensaje por mano con 87 floats", ad == "/handmotion/Right"
              and len(floats) == unreal_bridge.N_FLOATS and len(hand_msgs) == 50,
              f"{ad}, {len(floats)} floats, {len(hand_msgs)} mensajes de mano")
        lo = unreal_bridge.FLOAT_LAYOUT["puntos_cm"][0]
        wrist_rel = floats[lo:lo + 3]
        check("Unreal: la muñeca es el origen de los puntos relativos",
              all(abs(v) < 1e-6 for v in wrist_rel), f"muñeca relativa = {wrist_rel}")

        rows = run_capture(["--sin-antebrazo", "--sin-3d", "--unreal", dest], out_dir, frames=50,
                           keys={10: ord("u"), 30: ord("u")})
        n = len([1 for ad, _a in packets() if ad == unreal_bridge.ADDR_FRAME])
        check("tecla 'u': pausa y reanuda el envío (graba igual)", n == 30 and len(rows) == 50 * 21,
              f"{n} fotogramas enviados de 50; CSV con {len(rows) // 21} frames")

        clear_exports()
        run_capture(["--sin-antebrazo", "--sin-3d"], out_dir, frames=60, keys={30: ord("e")})
        got = exported()
        check("tecla 'e': los dos CSV para artículos, en articulos/", sorted(got) == ["ingenieria", "medicina"],
              ", ".join(p.name for p in sorted(arts.glob("*.csv"))))
        check("traen lo grabado hasta ese momento (sin parar la captura)",
              got == {"ingenieria": 30, "medicina": 30}, f"fotogramas de la muñeca: {got}")
        plot_latest = sorted(out_dir.glob("hand_data_*.csv"))[-1]
        check("plot_csv.py no los confunde con capturas (están en una subcarpeta)",
              not plot_latest.stem.endswith(("_ingenieria", "_medicina")), plot_latest.name)

        clear_exports()
        run_capture(["--sin-antebrazo", "--sin-3d"], out_dir, frames=60, keys={20: ord("e"), 45: ord("e")})
        got = exported()
        check("'e' dos veces: reemplaza con lo grabado hasta la segunda", got == {"ingenieria": 45, "medicina": 45}
              and len(list(arts.glob("*.csv"))) == 2, f"{got}")

        clear_exports()
        run_capture(["--sin-antebrazo", "--sin-3d"], out_dir, frames=40,
                    keys={10: SPACE, 12: ord("e"), 15: SPACE})
        got = exported()
        check("'e' en pausa", got == {"ingenieria": 10, "medicina": 10}, f"{got}")

        clear_exports()
        State.no_hands = True
        run_capture(["--sin-antebrazo", "--sin-3d"], out_dir, frames=8, keys={3: ord("e")})
        State.no_hands = False
        check("'e' sin datos: avisa y no se cae", not list(arts.glob("*.csv")), "no se crea ningún CSV")

        run_capture(["--sin-antebrazo", "--sin-3d"], out_dir, frames=20, keys={10: ord("m")})
        check("'m' ya no exporta (17-B: era el Excel de medicina)", not list(arts.glob("*.csv")),
              "sin archivos en articulos/")

        # plot_csv.py --3d: espacio pausa (se repite el mismo frame con "[pausa]")
        titles = []
        original = viewer3d.DualPOVViewer.render

        def record_title(self, hands, title, *a, **k):
            titles.append(title)
            return original(self, hands, title, *a, **k)
        viewer3d.DualPOVViewer.render = record_title
        State.calls, State.frames, State.keys = 0, 30, {5: SPACE, 10: ord("p")}
        sys.argv = ["plot_csv.py", str(stereo_csv), "--3d"]
        plot_csv.main()
        viewer3d.DualPOVViewer.render = original
        paused_renders = sum("[pausa]" in t for t in titles)
        check("plot_csv --3d: espacio pausa y 'p' sigue", paused_renders == 5,
              f"{paused_renders} dibujos en pausa")
        sock.close()

    ok = all(results)
    print("\nRESULTADO:", "OK" if ok else "FALLA")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
