"""
Prueba de estereo.py (versión 28-D) con un par de cámaras SIMULADO: no
hacen falta webcams. De aquí salen los números del README (sección "Dos
cámaras" -> "Qué tan preciso es").

Uso:
    ./venv/bin/python3 pruebas/estereo_simulado.py

Qué hace:
  1. Inventa dos cámaras (lentes con distorsión, separadas 18 cm, la
     segunda girada 12°) y proyecta un tablero de 9x6 en 18 posiciones
     con 0.2 px de ruido. Calibra con estereo.calibrate_from_corners y
     compara con los valores reales.
  2. Guarda y vuelve a leer la calibración (StereoRig.save/load).
  3. Proyecta dos manos 3D (a 45 y 60 cm, palmas de 9.0 y 8.0 cm, enteras en las dos imágenes) en las
     dos cámaras con 1 px de ruido, la cámara 1 en espejo como en
     captura.py, y la cámara 2 entregando las manos en el orden
     contrario. Comprueba el emparejamiento, la palma, la distancia y el
     error de posición.
  4. Una mano con algunos dedos fuera de la imagen de la cámara 2: esos
     puntos no se triangulan (quedan sin cm) y el resto sí.
  5. Casos borde: la cámara 2 ve una sola mano, no ve ninguna, y una
     resolución distinta a la de la calibración.

Sale con código 1 si algo queda fuera de tolerancia.
"""

import sys
import tempfile
from collections import namedtuple
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import estereo  # noqa: E402

W, H = 1280, 720
K1 = np.array([[1000, 0, 640], [0, 1000, 360], [0, 0, 1.0]])
K2 = np.array([[980, 0, 630], [0, 985, 355], [0, 0, 1.0]])
D1 = np.array([0.05, -0.1, 0, 0, 0.0])
D2 = np.array([0.03, -0.05, 0, 0, 0.0])
R_TRUE, _ = cv2.Rodrigues(np.array([0, np.radians(-12), np.radians(1)]))
T_TRUE = np.array([-18.0, 0.5, 1.0])  # cm

Landmark = namedtuple("Landmark", "x y z")


def make_calibration(path=None, seed=1):
    """
    Calibra el par simulado con 18 tableros y devuelve el StereoRig. Si se
    pasa path, lo guarda ahí (lo reutiliza pruebas/captura_simulada.py).
    """
    rng = np.random.default_rng(seed)
    cols, rows, square_cm = 9, 6, 2.5
    objp = np.zeros((cols * rows, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2) * square_cm
    obj, c1s, c2s = [], [], []

    def inside(p):
        return ((p[:, 0, 0] > 0) & (p[:, 0, 0] < W) & (p[:, 0, 1] > 0) & (p[:, 0, 1] < H)).all()

    while len(obj) < 18:
        rb, _ = cv2.Rodrigues(rng.normal(0, 0.35, 3))
        tv = np.array([rng.uniform(-15, 5), rng.uniform(-10, 3), rng.uniform(40, 80)])
        xc = (rb @ objp.T).T + tv
        x2 = (R_TRUE @ xc.T).T + T_TRUE
        if (x2[:, 2] <= 0).any():
            continue
        p1, _ = cv2.projectPoints(xc, np.zeros(3), np.zeros(3), K1, D1)
        p2, _ = cv2.projectPoints(x2, np.zeros(3), np.zeros(3), K2, D2)
        if not (inside(p1) and inside(p2)):
            continue
        obj.append(objp)
        c1s.append((p1 + rng.normal(0, 0.2, p1.shape)).astype(np.float32))
        c2s.append((p2 + rng.normal(0, 0.2, p2.shape)).astype(np.float32))
    rig = estereo.calibrate_from_corners(obj, c1s, c2s, (W, H))
    if path is not None:
        rig.save(path)
    return rig


def hand_3d(center, palm_cm, rng):
    """21 puntos 3D (cm) con forma de mano, girada al azar, palma = palm_cm."""
    pts = [np.zeros(3)]
    for f, ang in enumerate(np.radians([-50, -20, 0, 15, 30])):
        d = np.array([np.sin(ang), -np.cos(ang), 0.0])
        for k in range(1, 5):
            pts.append(d * palm_cm * (0.45 + 0.3 * k) + np.array([0, 0, -1.5 * k * (f % 2)]))
    pts = np.array(pts)
    pts[9] = np.array([0, -palm_cm, 0])  # nudillo del medio: define la palma
    rot, _ = cv2.Rodrigues(rng.normal(0, 0.5, 3))
    return (rot @ pts.T).T + center


def project_hand(X, rng, noise_px=1.0):
    """Landmarks como los daría MediaPipe: cámara 1 en espejo, cámara 2 no."""
    p1, _ = cv2.projectPoints(X, np.zeros(3), np.zeros(3), K1, D1)
    p2, _ = cv2.projectPoints((R_TRUE @ X.T).T + T_TRUE, np.zeros(3), np.zeros(3), K2, D2)
    p1 = p1[:, 0] + rng.normal(0, noise_px, (21, 2))
    p2 = p2[:, 0] + rng.normal(0, noise_px, (21, 2))
    return ([Landmark(1 - u / W, v / H, 0.0) for u, v in p1],
            [Landmark(u / W, v / H, 0.0) for u, v in p2])


def visible_in_both(X):
    """Máscara de los puntos 3D que caen dentro de las dos imágenes."""
    p1, _ = cv2.projectPoints(X, np.zeros(3), np.zeros(3), K1, D1)
    p2, _ = cv2.projectPoints((R_TRUE @ X.T).T + T_TRUE, np.zeros(3), np.zeros(3), K2, D2)
    inside = lambda p: (p[:, 0, 0] >= 0) & (p[:, 0, 0] < W) & (p[:, 0, 1] >= 0) & (p[:, 0, 1] < H)
    return inside(p1) & inside(p2)


def main():
    """Corre las comprobaciones y sale con 0 (OK) o 1 (FALLA)."""
    results = []

    def check(name, passed, detail):
        results.append(passed)
        print(f"  {'OK   ' if passed else 'FALLA'} {name}: {detail}")

    print("1. Calibración con 18 tableros simulados")
    rig = make_calibration()
    t = rig.T.ravel()
    check("distancia entre cámaras", abs(rig.baseline_cm - np.linalg.norm(T_TRUE)) < 0.2,
          f"{rig.baseline_cm:.2f} cm (real {np.linalg.norm(T_TRUE):.2f})")
    check("traslación", np.abs(t - T_TRUE).max() < 0.3, f"{t.round(2)} (real {T_TRUE})")
    check("error RMS", rig.info["rms_estereo"] < 0.5, f"{rig.info['rms_estereo']:.2f} px")

    print("2. Guardar y leer la calibración")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "estereo.npz"
        rig.save(path)
        loaded = estereo.StereoRig.load(path)
    check("se lee igual", np.allclose(loaded.T, rig.T) and loaded.size == (W, H)
          and loaded.info["pares"] == 18, f"pares {loaded.info['pares']}, tamaño {loaded.size}")

    print("3. Dos manos (la cámara 2 las entrega en orden contrario)")
    rng = np.random.default_rng(2)
    hand_a = hand_3d(np.array([18, 6, 45.0]), 9.0, rng)
    hand_b = hand_3d(np.array([10, 0, 60.0]), 8.0, rng)
    for X in (hand_a, hand_b):
        assert visible_in_both(X).all(), "la mano de prueba tiene que verse entera"
    stereo = estereo.StereoHands(loaded, W, H)
    for _ in range(40):  # varios frames: la palma se suaviza en el tiempo
        a1, a2 = project_hand(hand_a, rng)
        b1, b2 = project_hand(hand_b, rng)
        new, info = stereo.update([(7, "Right", 0.9, a1), (3, "Left", 0.9, b1)], [b2, a2])
    for tid, X, palm in ((7, hand_a, 9.0), (3, hand_b, 8.0)):
        i = info[tid]
        pc = np.array(i.points_cm)
        pc[:, 0] *= -1  # x_cm viene en espejo
        err = np.linalg.norm(pc - X, axis=1).max()
        check(f"mano #{tid} (palma {palm} cm, a {X[0, 2]:.0f} cm)",
              abs(i.palm_cm - palm) < 0.3 and abs(i.distance_cm - X[0, 2]) < 1 and err < 1.5,
              f"palma {i.palm_cm:.2f}, distancia {i.distance_cm:.1f}, error máx {err:.2f} cm, "
              f"reproyección {i.error_px:.2f} px")
    wrist_z = hand_a[0, 2]
    z_true = (hand_a[:, 2] - wrist_z) / (W * wrist_z / K1[0, 0])
    z_new = np.array([lm.z for lm in dict((h[0], h[3]) for h in new)[7]])
    check("z en la convención de MediaPipe", np.abs(z_new - z_true).max() < 0.03,
          f"error máx {np.abs(z_new - z_true).max():.4f} anchos de frame")

    print("4. Mano con dedos fuera del cuadro de la cámara 2")
    # Como la mano que destapó el problema: a la izquierda, con parte de
    # los dedos fuera de la imagen de la cámara 2 (MediaPipe los extrapola).
    partial = hand_3d(np.array([7, -2, 45.0]), 9.0, np.random.default_rng(7))
    vis = visible_in_both(partial)
    st2 = estereo.StereoHands(loaded, W, H)
    p1, p2 = project_hand(partial, rng)
    _, info_p = st2.update([(1, "Right", 0.9, p1)], [p2])
    if 1 in info_p:
        ip = info_p[1]
        # Con ruido, un punto justo en el borde puede caer de cualquier
        # lado: se exige que TODO punto realmente afuera quede sin cm y que
        # los triangulados sean precisos.
        measured = [i for i in range(21) if ip.points_cm[i] is not None]
        got = np.array([ip.points_cm[i] for i in measured])
        got[:, 0] *= -1
        err = np.linalg.norm(got - partial[measured], axis=1).max()
        outside_none = all(ip.points_cm[i] is None for i in range(21) if not vis[i])
        check(f"{(~vis).sum()} de 21 puntos fuera de cuadro", outside_none and err < 1.5,
              f"quedan sin cm {21 - len(measured)} puntos; los otros {len(measured)} "
              f"con error máx {err:.2f} cm; palma {ip.palm_cm:.2f} cm (real 9.0)")
    else:
        check(f"{(~vis).sum()} de 21 puntos fuera de cuadro", vis.sum() < estereo.MIN_VISIBLE_POINTS
              or not vis[0], "no se trianguló (muy pocos puntos visibles)")

    # El caso que destapó el problema: mano a la izquierda, con puntos a
    # cientos de píxeles fuera de la imagen de la cámara 2.
    far = hand_3d(np.array([-8, 2, 45.0]), 9.0, np.random.default_rng(99))
    f1, f2 = project_hand(far, rng)
    px1 = estereo.landmarks_px(f1, W, H, True)
    px2 = estereo.landmarks_px(f2, W, H, False)
    X_all, _ = loaded.triangulate(px1, px2)
    before = np.linalg.norm(X_all - far, axis=1).max()
    _, info_f = estereo.StereoHands(loaded, W, H).update([(1, "Right", 0.9, f1)], [f2])
    if 1 in info_f:
        pts = [(i, info_f[1].points_cm[i]) for i in range(21)
               if info_f[1].points_cm[i] is not None]
        after = max(np.linalg.norm(np.array([-p[0], p[1], p[2]]) - far[i]) for i, p in pts)
        detail = f"triangulando todo: {before:.2f} cm; ahora: {after:.2f} cm"
    else:
        after, detail = 0.0, f"triangulando todo: {before:.2f} cm; ahora no se triangula"
    check("puntos lejos del cuadro (antes daban varios cm de error)", after < 1.5, detail)

    print("5. Casos borde")
    new, info = stereo.update([(7, "Right", 0.9, a1), (3, "Left", 0.9, b1)], [b2])
    check("la cámara 2 ve una sola mano", sorted(info) == [3] and new[0][3] is a1,
          "solo se triangula esa; la otra queda intacta")
    check("palma conservada de la mano no vista", stereo.known_palm(7) is not None,
          f"known_palm(7) = {stereo.known_palm(7):.2f} cm")
    _, info = stereo.update([(7, "Right", 0.9, a1)], [])
    check("la cámara 2 no ve nada", info == {}, "ninguna mano triangulada")
    try:
        estereo.StereoHands(loaded, 640, 480)
        check("resolución distinta a la calibración", False, "no dio error")
    except ValueError as e:
        check("resolución distinta a la calibración", True, str(e)[:60] + "...")

    ok = all(results)
    print("\nRESULTADO:", "OK" if ok else "FALLA")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
