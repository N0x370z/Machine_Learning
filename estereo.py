"""
Profundidad real con dos cámaras (estéreo), desde la versión 28-D.

Con una sola cámara, la z de MediaPipe es una profundidad RELATIVA a la
muñeca que la red "adivina" a partir de la forma de la mano, y la escala
en cm sale de suponer una palma de 9.5 cm (o la de --palma-cm). Con dos
cámaras que ven la misma mano desde lugares distintos se puede
TRIANGULAR cada punto: se sabe dónde está cada cámara y hacia dónde mira
(calibración), cada una dice en qué dirección ve el punto, y el punto
está donde se cruzan las dos rectas. Así se obtiene la posición 3D real
en cm de los 21 puntos de la mano, sin suponer nada sobre su tamaño.

Uso (dos webcams fijas, separadas 10-30 cm, mirando a la misma zona):

    1. Imprimir un tablero de ajedrez (o generarlo con este script):
         ./venv/bin/python3 estereo.py tablero
       y medir con una regla el lado de un cuadro impreso, en mm.
    2. Calibrar (una vez, y de nuevo cada vez que se mueva una cámara):
         ./venv/bin/python3 estereo.py calibrar --cuadro-mm 25
       Mostrar el tablero a las dos cámaras en 15-20 posiciones distintas
       (cerca, lejos, inclinado, en las esquinas) y presionar espacio en
       cada una; luego 'c' para calcular. Se guarda en
       calibracion/estereo.npz.
    3. Capturar con las dos cámaras:
         ./venv/bin/python3 captura.py --estereo

Qué cambia en la captura con --estereo (ver captura.py):
  - La z de cada landmark (0-20) es la triangulada, pasada a la misma
    convención que la de MediaPipe (relativa a la muñeca, en anchos de
    frame), así el visor 3D, la velocidad y el CSV funcionan igual.
  - El largo de la palma se MIDE (suavizado en el tiempo) y reemplaza a
    --palma-cm: los cm/s dejan de ser aproximados.
  - El CSV agrega la posición absoluta de cada punto en cm (x_cm, y_cm,
    z_cm, respecto a la cámara 1) y fuente = "estereo".
  - Si una mano de la cámara 1 no se encuentra en la cámara 2 (tapada,
    fuera de cuadro), esa mano sigue como antes (z de MediaPipe).

Cómo se empareja cada mano de la cámara 1 con la de la cámara 2: se
triangulan los 21 puntos con cada combinación posible y se mide el error
de reproyección (cuánto se equivoca el punto 3D al volver a proyectarlo
en cada cámara, en píxeles). La combinación correcta da un error chico;
una incorrecta, enorme. Se acepta si el error medio es menor que
MAX_REPROJ_FRAC del ancho del frame.

Convenciones:
  - La cámara 1 es la principal (la de la ventana y la de la vista 3D).
    Su imagen se voltea en espejo antes de MediaPipe (como siempre), así
    que para triangular se "desvoltea": u = (1 - x) * ancho. La cámara 2
    NO se voltea.
  - Coordenadas de la calibración: las de la cámara 1 en cm (X a la
    derecha de la imagen SIN espejo, Y hacia abajo, Z hacia adelante).
    Para el CSV, x_cm se invierte para que coincida con la imagen en
    espejo que se ve en la ventana.

Limitaciones:
  - Las dos webcams no están sincronizadas por hardware: se toman los dos
    frames lo más juntos posible (grab() en las dos y después
    retrieve()), pero con movimientos muy rápidos puede haber unos ms de
    diferencia, que se ven como error de reproyección más alto.
  - El codo sigue viniendo de YOLO en la cámara 1 con z estimada (ver
    forearm.py), aunque ahora a partir de una palma con z medida.
  - Las dos cámaras deben usar la misma resolución que en la calibración.

Última actualización: 2026-09-28. Historial: ver CHANGELOG.md.
"""

import argparse
from collections import namedtuple
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

CALIB_DIR = Path(__file__).parent / "calibracion"
DEFAULT_CALIB = CALIB_DIR / "estereo.npz"

# Tablero de ajedrez: esquinas INTERNAS (columnas x filas). Un tablero de
# 10 x 7 cuadros tiene 9 x 6 esquinas internas.
DEFAULT_BOARD = (9, 6)
MIN_PAIRS = 10            # pares de fotos mínimos para calibrar
RECOMMENDED_PAIRS = 15

# Emparejamiento de manos: error de reproyección medio máximo, como
# fracción del ancho del frame (0.015 = ~19 px a 1280). MediaPipe no
# marca exactamente el mismo punto de la piel en las dos vistas, así que
# un error de algunos píxeles es normal.
MAX_REPROJ_FRAC = 0.015

# Suavizado del largo de la palma medido (1 = sin suavizar). La palma no
# cambia de tamaño, así que se suaviza mucho: lo que varía entre frames es
# ruido de medición.
PALM_SMOOTHING = 0.1

# Landmark con la z reemplazada (mismos atributos que los de MediaPipe).
Landmark = namedtuple("Landmark", "x y z")

# Resultado estéreo de una mano:
#   points_cm: 21 x (x, y, z) en cm respecto a la cámara 1, con x en espejo
#   palm_cm: largo de la palma medido (suavizado)
#   error_px: error de reproyección medio
#   distance_cm: distancia de la muñeca a la cámara 1
StereoHand = namedtuple("StereoHand", "points_cm palm_cm error_px distance_cm")


class StereoRig:
    """
    Par de cámaras calibrado: intrínsecos de cada una (K = matriz de la
    cámara, D = distorsión) y la pose de la cámara 2 respecto a la 1
    (R rotación, T traslación en cm).
    """

    def __init__(self, K1, D1, K2, D2, R, T, size, info=None):
        self.K1, self.D1 = np.asarray(K1, float), np.asarray(D1, float)
        self.K2, self.D2 = np.asarray(K2, float), np.asarray(D2, float)
        self.R = np.asarray(R, float)
        self.T = np.asarray(T, float).reshape(3, 1)
        self.size = (int(size[0]), int(size[1]))  # (ancho, alto)
        self.info = info or {}
        self._rvec2, _ = cv2.Rodrigues(self.R)

    @property
    def baseline_cm(self):
        """Distancia entre las dos cámaras."""
        return float(np.linalg.norm(self.T))

    @classmethod
    def load(cls, path=DEFAULT_CALIB):
        """Lee una calibración guardada por `estereo.py calibrar`."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(
                f"No hay calibración en {path}. Primero: "
                "./venv/bin/python3 estereo.py calibrar --cuadro-mm <lado>")
        data = np.load(path)
        info = {k: data[k].item() for k in ("rms1", "rms2", "rms_estereo", "pares")
                if k in data}
        return cls(data["K1"], data["D1"], data["K2"], data["D2"], data["R"],
                   data["T"], data["size"], info)

    def save(self, path=DEFAULT_CALIB):
        """Guarda la calibración (y sus errores, en self.info) en un .npz."""
        path = Path(path)
        path.parent.mkdir(exist_ok=True)
        np.savez(path, K1=self.K1, D1=self.D1, K2=self.K2, D2=self.D2,
                 R=self.R, T=self.T, size=np.array(self.size),
                 **{k: np.array(v) for k, v in self.info.items()})

    def triangulate(self, px1, px2):
        """
        px1, px2: (N, 2) píxeles del mismo punto en cada cámara (imagen sin
        espejo). Devuelve (puntos (N, 3) en cm en coords de la cámara 1,
        error de reproyección medio en píxeles).
        """
        px1 = np.asarray(px1, float).reshape(-1, 1, 2)
        px2 = np.asarray(px2, float).reshape(-1, 1, 2)
        # Quitar la distorsión del lente y pasar a coordenadas normalizadas
        # (como si las dos cámaras fueran ideales con foco 1).
        n1 = cv2.undistortPoints(px1, self.K1, self.D1).reshape(-1, 2).T
        n2 = cv2.undistortPoints(px2, self.K2, self.D2).reshape(-1, 2).T
        P1 = np.hstack([np.eye(3), np.zeros((3, 1))])
        P2 = np.hstack([self.R, self.T])
        X = cv2.triangulatePoints(P1, P2, n1, n2)
        X = (X[:3] / X[3]).T
        r1, _ = cv2.projectPoints(X, np.zeros(3), np.zeros(3), self.K1, self.D1)
        r2, _ = cv2.projectPoints(X, self._rvec2, self.T, self.K2, self.D2)
        err = (np.linalg.norm(r1 - px1, axis=2).mean()
               + np.linalg.norm(r2 - px2, axis=2).mean()) / 2
        return X, float(err)


def calibrate_from_corners(object_points, corners1, corners2, size):
    """
    Calibra el par a partir de las esquinas del tablero vistas por las dos
    cámaras en varias fotos. object_points: [(N, 3)] en cm (el tablero en
    su propio plano); corners1/2: [(N, 1, 2)] píxeles; size: (ancho, alto).

    Primero calibra cada cámara por separado (foco, centro, distorsión) y
    después solo la pose relativa entre ellas (CALIB_FIX_INTRINSIC): así
    cada paso tiene menos incógnitas y es más estable. Devuelve un
    StereoRig con los errores RMS (en píxeles) en .info.
    """
    obj = [np.asarray(o, np.float32) for o in object_points]
    c1 = [np.asarray(c, np.float32) for c in corners1]
    c2 = [np.asarray(c, np.float32) for c in corners2]
    rms1, K1, D1, _, _ = cv2.calibrateCamera(obj, c1, size, None, None)
    rms2, K2, D2, _, _ = cv2.calibrateCamera(obj, c2, size, None, None)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-6)
    rms, K1, D1, K2, D2, R, T, _E, _F = cv2.stereoCalibrate(
        obj, c1, c2, K1, D1, K2, D2, size, criteria=criteria,
        flags=cv2.CALIB_FIX_INTRINSIC)
    info = {"rms1": float(rms1), "rms2": float(rms2), "rms_estereo": float(rms),
            "pares": len(obj)}
    return StereoRig(K1, D1, K2, D2, R, T, size, info)


def landmarks_px(landmarks, width, height, mirrored):
    """Landmarks normalizados de MediaPipe -> (21, 2) píxeles sin espejo."""
    return np.array([((1 - lm.x) if mirrored else lm.x, lm.y) for lm in landmarks]
                    ) * (width, height)


class StereoHands:
    """
    Empareja cada mano rastreada de la cámara 1 con una detección de la
    cámara 2, la triangula y le reemplaza la z (ver docstring del módulo).
    """

    def __init__(self, rig, img_w, img_h):
        if (img_w, img_h) != rig.size:
            raise ValueError(
                f"La cámara abrió a {img_w}x{img_h} pero la calibración es de "
                f"{rig.size[0]}x{rig.size[1]}. Usa --cam-width {rig.size[0]} "
                f"--cam-height {rig.size[1]} o vuelve a calibrar.")
        self.rig = rig
        self.w, self.h = img_w, img_h
        self._palm = {}  # track_id -> largo de palma suavizado (cm)

    def update(self, tracked_hands, hands2):
        """
        tracked_hands: salida de HandTracker.update (cámara 1, en espejo).
        hands2: lista de landmarks de MediaPipe de la cámara 2 (sin espejo).

        Devuelve (tracked_hands con la z triangulada en las manos que se
        encontraron en las dos cámaras, {track_id: StereoHand}).
        """
        fx = self.rig.K1[0, 0]
        candidates = []
        for t_idx, (_tid, _label, _score, lms1) in enumerate(tracked_hands):
            px1 = landmarks_px(lms1, self.w, self.h, mirrored=True)
            for d_idx, lms2 in enumerate(hands2):
                px2 = landmarks_px(lms2, self.w, self.h, mirrored=False)
                X, err = self.rig.triangulate(px1, px2)
                if np.all(X[:, 2] > 0):  # delante de la cámara
                    candidates.append((err, t_idx, d_idx, X))
        candidates.sort(key=lambda c: c[0])

        max_err = MAX_REPROJ_FRAC * self.w
        used_t, used_d, found = set(), set(), {}
        for err, t_idx, d_idx, X in candidates:
            if err > max_err:
                break
            if t_idx in used_t or d_idx in used_d:
                continue
            used_t.add(t_idx)
            used_d.add(d_idx)
            found[t_idx] = (X, err)

        new_hands, info = [], {}
        for t_idx, (tid, label, score, lms1) in enumerate(tracked_hands):
            if t_idx not in found:
                new_hands.append((tid, label, score, lms1))
                continue
            X, err = found[t_idx]
            wrist_z = X[0, 2]
            # Ancho del frame en cm a la distancia de la muñeca: pasa la
            # profundidad de cm a "anchos de frame", la unidad de MediaPipe.
            frame_w_cm = self.w * wrist_z / fx
            lms = [Landmark(lm.x, lm.y, float((X[i, 2] - wrist_z) / frame_w_cm))
                   for i, lm in enumerate(lms1)]
            new_hands.append((tid, label, score, lms))

            palm = float(np.linalg.norm(X[9] - X[0]))
            prev = self._palm.get(tid)
            if prev is not None:
                palm = PALM_SMOOTHING * palm + (1 - PALM_SMOOTHING) * prev
            self._palm[tid] = palm
            points_cm = [(float(-x), float(y), float(z)) for x, y, z in X]
            info[tid] = StereoHand(points_cm, palm, err, float(wrist_z))

        alive = {t[0] for t in tracked_hands}
        for tid in list(self._palm):
            if tid not in alive:
                del self._palm[tid]
        return new_hands, info

    def known_palm(self, track_id):
        """
        Última palma medida de esa mano (cm), o None si nunca se midió.
        Si la cámara 2 pierde la mano un rato, captura.py sigue usando
        esta palma para los cm/s en vez de volver a la supuesta: si no, la
        escala saltaría entre las dos y aparecerían picos falsos de
        velocidad.
        """
        return self._palm.get(track_id)


# --------------------------------------------------------------- comandos


def _open_camera(index, width, height):
    """Abre una cámara pidiendo esa resolución; error claro si no abre."""
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        raise RuntimeError(
            f"No se pudo abrir la cámara {index}. Revisa que esté conectada y "
            "que la terminal tenga permiso de cámara.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    return cap


def _board(text):
    """Tipo de argparse para --tablero: 'COLxFIL' (esquinas internas)."""
    try:
        cols, rows = (int(v) for v in text.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError("usa el formato COLxFIL, p. ej. 9x6")
    return cols, rows


def cmd_tablero(args):
    """Genera un PNG del tablero de ajedrez para imprimir."""
    cols, rows = args.tablero
    sq, margin = args.cuadro_px, args.cuadro_px
    img = np.full(((rows + 1) * sq + 2 * margin, (cols + 1) * sq + 2 * margin),
                  255, np.uint8)
    for r in range(rows + 1):
        for c in range(cols + 1):
            if (r + c) % 2 == 0:
                y, x = margin + r * sq, margin + c * sq
                img[y:y + sq, x:x + sq] = 0
    CALIB_DIR.mkdir(exist_ok=True)
    out = CALIB_DIR / f"tablero_{cols}x{rows}.png"
    cv2.imwrite(str(out), img)
    print(f"Tablero guardado en {out} ({cols + 1}x{rows + 1} cuadros, "
          f"{cols}x{rows} esquinas internas).")
    print("Imprímelo al 100 % (sin 'ajustar a la página'), pégalo sobre algo "
          "rígido y plano, y mide el lado de un cuadro en mm para --cuadro-mm.")


def cmd_calibrar(args):
    """Captura pares de fotos del tablero con las dos cámaras y calibra."""
    cols, rows = args.tablero
    # Esquinas del tablero en su propio plano (z = 0), en cm.
    objp = np.zeros((cols * rows, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2) * (args.cuadro_mm / 10)

    cap1 = _open_camera(args.cam1, args.cam_width, args.cam_height)
    cap2 = _open_camera(args.cam2, args.cam_width, args.cam_height)
    size1 = (int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    size2 = (int(cap2.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap2.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    if size1 != size2:
        raise RuntimeError(f"Las cámaras abrieron a resoluciones distintas "
                           f"({size1} y {size2}); prueba otra --cam-width/--cam-height.")

    flags = (cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE
             + cv2.CALIB_CB_FAST_CHECK)
    subpix = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    window = "Calibracion estereo"
    pairs1, pairs2 = [], []
    message = ""
    try:
        while True:
            # grab() en las dos y después retrieve(): los dos frames quedan
            # lo más cerca posible en el tiempo.
            if not (cap1.grab() and cap2.grab()):
                raise RuntimeError("Se perdió la imagen de una de las cámaras.")
            _, f1 = cap1.retrieve()
            _, f2 = cap2.retrieve()
            g1 = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY)
            g2 = cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY)
            ok1, c1 = cv2.findChessboardCorners(g1, (cols, rows), flags=flags)
            ok2, c2 = cv2.findChessboardCorners(g2, (cols, rows), flags=flags)

            view = [f1.copy(), f2.copy()]
            for img, ok, c in ((view[0], ok1, c1), (view[1], ok2, c2)):
                if ok:
                    cv2.drawChessboardCorners(img, (cols, rows), c, ok)
            preview = np.hstack([cv2.resize(v, (v.shape[1] // 2, v.shape[0] // 2))
                                 for v in view])
            status = (f"pares: {len(pairs1)} (min {MIN_PAIRS}, ideal {RECOMMENDED_PAIRS}+)"
                      f"  cam1 {'OK' if ok1 else '--'}  cam2 {'OK' if ok2 else '--'}"
                      "  [espacio] guardar  [c] calibrar  [q] salir")
            for text, y in ((status, 24), (message, 48)):
                cv2.putText(preview, text, (11, y + 1), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (0, 0, 0), 1, cv2.LINE_AA)
                cv2.putText(preview, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (0, 255, 255), 1, cv2.LINE_AA)
            cv2.imshow(window, preview)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                print("Calibración cancelada.")
                return
            if key == ord(" "):
                if ok1 and ok2:
                    pairs1.append(cv2.cornerSubPix(g1, c1, (11, 11), (-1, -1), subpix))
                    pairs2.append(cv2.cornerSubPix(g2, c2, (11, 11), (-1, -1), subpix))
                    message = f"Par {len(pairs1)} guardado. Mueve el tablero a otra posicion."
                else:
                    message = "El tablero tiene que verse ENTERO en las dos camaras."
            elif key == ord("c"):
                if len(pairs1) < MIN_PAIRS:
                    message = f"Faltan pares: {len(pairs1)} de {MIN_PAIRS}."
                    continue
                print(f"Calibrando con {len(pairs1)} pares...")
                rig = calibrate_from_corners([objp] * len(pairs1), pairs1, pairs2, size1)
                out = Path(args.salida)
                rig.save(out)
                _report(rig, out)
                return
    finally:
        cap1.release()
        cap2.release()
        cv2.destroyAllWindows()
        for _ in range(10):
            cv2.waitKey(1)


def _report(rig, path):
    """Imprime el resultado de la calibración y si es aceptable."""
    info = rig.info
    print(f"Calibración guardada en {path} ({datetime.now():%Y-%m-%d %H:%M}).")
    print(f"  Error RMS cámara 1: {info['rms1']:.2f} px, cámara 2: "
          f"{info['rms2']:.2f} px, par estéreo: {info['rms_estereo']:.2f} px")
    print(f"  Distancia entre cámaras: {rig.baseline_cm:.1f} cm")
    if info["rms_estereo"] > 1.0:
        print("  AVISO: error mayor a 1 px. Repite con más pares, el tablero bien "
              "plano y en posiciones más variadas.")


def parse_args(argv=None):
    """Subcomandos: tablero y calibrar."""
    parser = argparse.ArgumentParser(
        description="Calibración de dos cámaras para captura.py --estereo.")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("tablero", help="Genera un tablero de ajedrez para imprimir.")
    p.add_argument("--tablero", type=_board, default=DEFAULT_BOARD,
                   help="Esquinas internas COLxFIL (default: 9x6).")
    p.add_argument("--cuadro-px", type=int, default=120,
                   help="Lado de cada cuadro en el PNG, en píxeles (default: 120).")
    p.set_defaults(func=cmd_tablero)

    p = sub.add_parser("calibrar", help="Calibra las dos cámaras con el tablero.")
    p.add_argument("--cuadro-mm", type=float, required=True,
                   help="Lado de un cuadro del tablero IMPRESO, medido con regla (mm).")
    p.add_argument("--tablero", type=_board, default=DEFAULT_BOARD,
                   help="Esquinas internas COLxFIL (default: 9x6).")
    p.add_argument("--cam1", type=int, default=0, help="Índice de la cámara 1 (default: 0).")
    p.add_argument("--cam2", type=int, default=1, help="Índice de la cámara 2 (default: 1).")
    p.add_argument("--cam-width", type=int, default=1280)
    p.add_argument("--cam-height", type=int, default=720)
    p.add_argument("--salida", default=str(DEFAULT_CALIB),
                   help=f"Archivo de calibración (default: {DEFAULT_CALIB.relative_to(Path(__file__).parent)}).")
    p.set_defaults(func=cmd_calibrar)
    return parser.parse_args(argv)


if __name__ == "__main__":
    ARGS = parse_args()
    ARGS.func(ARGS)
