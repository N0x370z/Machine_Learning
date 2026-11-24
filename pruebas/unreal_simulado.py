"""
Prueba de unreal_bridge.py (19-A) SIN Unreal Engine ni cámara: comprueba
el codificador OSC, el cambio de ejes a Unreal, los ángulos de flexión y
el envío por UDP a un receptor de prueba en esta misma máquina, y desde la
23-A la reproducción de un CSV (--csv): tiempos, ejes y estéreo.

Qué NO cubre: que Unreal Engine los reciba y los use. Eso se comprobó en
Unreal Engine 5.8 el 2026-11-23 con unreal/HandMotionUE y se repite con
docs/imagenes_unreal.py (ver UNREAL.md).

Uso:
    ./venv/bin/python3 pruebas/unreal_simulado.py
Sale con código 1 si algo queda fuera de tolerancia.
"""

import argparse
import socket
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import unreal_bridge as ub  # noqa: E402


def flat_hand(cm_per_unit=10.0):
    """Mano de escena con los 21 puntos en el origen, palma de 1 unidad."""
    points = [(0.0, 0.0, 0.0)] * 21
    points[9] = (0.0, -1.0, 0.0)
    return {"id": 7, "label": "Left", "points": points, "elbow": None,
            "elbow_source": None, "palm_cm": 10.0, "cm_per_unit": cm_per_unit}


def main():
    """Corre todos los casos y sale con 0 (OK) o 1 (FALLA)."""
    results = []

    def check(name, passed, detail):
        results.append(passed)
        print(f"  {'OK   ' if passed else 'FALLA'} {name}: {detail}")

    print("1. OSC")
    packet = ub.osc_message("/a", [1])
    check("bytes de un mensaje conocido", packet == b"/a\0\0,i\0\0\0\0\0\1", repr(packet))
    args = [-5, 3, 1.5, -0.25, "Índice", "", "ab"]   # el codificador admite los tres tipos
    packet = ub.osc_message("/handmotion/Right", args)
    address, back = ub.osc_decode(packet)
    check("ida y vuelta (int, float, string con acento y vacío)",
          address == "/handmotion/Right" and back == args and len(packet) % 4 == 0,
          f"{len(packet)} bytes, alineado a 4")
    try:
        ub.osc_message("/x", [None])
        check("tipo no soportado", False, "no falló")
    except TypeError:
        check("tipo no soportado: error claro", True, "TypeError")

    print("2. Flexión y ejes")
    pts = [(0.0, 0.0, 0.0)] * 21
    pts[0], pts[5], pts[6], pts[7], pts[8] = (0, 0, 0), (0, -1, 0), (0, -2, 0), (0, -3, 0), (0, -4, 0)
    flex = ub.flexion_degrees(pts)
    check("dedo estirado: 0°", abs(flex[3]) < 1e-6 and abs(flex[4]) < 1e-6, f"{flex[3]:.2f}°, {flex[4]:.2f}°")
    pts[7], pts[8] = (1, -2, 0), (2, -2, 0)       # PIP doblado 90°, DIP estirado
    flex = ub.flexion_degrees(pts)
    check("codo del dedo a 90°", abs(flex[4] - 90) < 1e-6, f"PIP {flex[4]:.2f}°")
    pts[7], pts[8] = (0, -1, 0), (0, -1.5, 0)     # vuelto sobre sí mismo
    check("dedo totalmente doblado: 180°", abs(ub.flexion_degrees(pts)[4] - 180) < 1e-6,
          f"{ub.flexion_degrees(pts)[4]:.2f}°")
    check("puntos repetidos no dan error", ub.flexion_degrees([(0.0, 0.0, 0.0)] * 21) == [0.0] * 15,
          "15 ceros")

    hand = flat_hand(10.0)
    hand["points"][8] = (1.0, -1.0, 0.1)    # derecha, arriba (y negativa) y lejos
    f = ub.hand_floats(hand)
    lo = ub.FLOAT_LAYOUT["puntos_cm"][0]
    tip = f[lo + 3 * 8: lo + 3 * 8 + 3]
    check("ejes: escena (x der, y abajo, z lejos) -> Unreal (X adelante, Y der, Z arriba), cm",
          all(abs(a - b) < 1e-5 for a, b in zip(tip, (1.0, 10.0, 10.0))), f"punta = {tip}")
    hand["points_cm"] = [(5.0, 10.0, 45.0)] + [(0.0, 0.0, 0.0)] * 20
    f = ub.hand_floats(hand)
    check("estéreo: muñeca absoluta (x der, y abajo, z adelante) -> Unreal",
          f[3:6] == [45.0, 5.0, -10.0], f"muñeca = {f[3:6]}")
    hand["elbow"] = (0.0, 2.0, 0.0)
    f = ub.hand_floats(hand)
    check("codo relativo a la muñeca y bandera tiene_codo",
          f[69:72] == [0.0, 0.0, -20.0] and f[1] == 1.0, f"codo = {f[69:72]}, tiene_codo = {f[1]}")
    check("87 floats y el orden de FLOAT_LAYOUT", len(f) == ub.N_FLOATS == 87
          and ub.FLOAT_LAYOUT["flexion_grados"] == (72, 87), str(ub.FLOAT_LAYOUT))
    check("el mensaje es solo floats (sin ints ni strings)",
          all(isinstance(a, float) for a in ub.osc_decode(ub.hand_message(hand))[1]), "87 argumentos float")

    print("3. Envío por UDP")
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", 0))
    rx.settimeout(1.0)
    port = rx.getsockname()[1]
    bridge = ub.UnrealBridge("127.0.0.1", port)
    left, right = flat_hand(), flat_hand()
    right["id"], right["label"] = 8, "Right"
    bridge.send_frame(12, 400.0, [left, right])
    got = [ub.osc_decode(rx.recv(4096)) for _ in range(3)]
    check("un fotograma = 1 mensaje de fotograma + 1 por mano",
          [g[0] for g in got] == ["/handmotion/frame", "/handmotion/Left", "/handmotion/Right"],
          ", ".join(g[0] for g in got))
    check("mensaje de fotograma: número, manos y tiempo (s)",
          got[0][1][:2] == [12.0, 2.0] and abs(got[0][1][2] - 0.4) < 1e-6, str(got[0][1]))
    check("mensaje de mano: id y tiene_codo van de primeros", got[2][1][:2] == [8.0, 0.0],
          f"id = {got[2][1][0]:.0f}, tiene_codo = {got[2][1][1]:.0f}")
    size = len(ub.hand_message(left))
    check("cada mensaje cabe en un paquete UDP sin fragmentar (< 1400 bytes)", size < 1400, f"{size} bytes")
    bridge.send_frame(13, 433.0, [])
    check("sin manos: solo el mensaje de fotograma", ub.osc_decode(rx.recv(4096))[1][:2] == [13.0, 0.0], "n_manos = 0")
    rx.close()
    for _ in range(3):                      # sin nadie escuchando: no lanza error
        bridge.send_frame(14, 466.0, [left])
    check("sin receptor no se cae", True, f"{bridge.frames_sent} fotogramas enviados, "
          f"{bridge.errors} rechazados por el sistema")
    bridge.close()

    print("4. Destino y mano de demostración")
    cases = [("127.0.0.1:9000", ("127.0.0.1", 9000)), ("9001", ("127.0.0.1", 9001)),
             ("192.168.1.20", ("192.168.1.20", 8000)), (":9002", ("127.0.0.1", 9002))]
    check("parse_destino", all(ub.parse_destino(t) == e for t, e in cases), f"{len(cases)} formas")
    bad = 0
    for text in ("host:abc", "127.0.0.1:0", "127.0.0.1:70000"):
        try:
            ub.parse_destino(text)
        except argparse.ArgumentTypeError:
            bad += 1
    check("parse_destino rechaza puertos inválidos", bad == 3, f"{bad} de 3 rechazados")
    open_, closed = ub.demo_hand(0.0), ub.demo_hand(1.0)
    f0, f1 = ub.flexion_degrees(open_["points"]), ub.flexion_degrees(closed["points"])
    check("demo: dedos abiertos en t=0 y doblados en t=1 s",
          f0[4] < 5 and f0[5] < 5 and f1[4] > 40 and f1[5] > 40,
          f"índice PIP/DIP: {f0[4]:.0f}°/{f0[5]:.0f}° -> {f1[4]:.0f}°/{f1[5]:.0f}°")
    # 17-A: antes el nudillo del medio se sobrescribía y ese dedo salía doblado
    # 109° hacia atrás con la mano abierta.
    check("demo: mano abierta sin ninguna articulación doblada (< 15°)", max(f0) < 15,
          f"máximo {max(f0):.0f}° ({ub.JOINTS[f0.index(max(f0))][:2]})")
    expected = [m for *_x, flex in ub._DEMO_FINGERS for m in flex]
    check("demo: mano cerrada = flexión máxima de cada articulación (±2°)",
          all(abs(a - e) < 2 for a, e in zip(f1, expected)),
          "medio MCP/PIP/DIP " + "/".join(f"{a:.0f}°" for a in f1[6:9]))
    palm = ub.kinematics._norm([a - b for a, b in zip(open_["points"][9], open_["points"][0])]) \
        * open_["cm_per_unit"]
    check("demo: la palma mide lo que dice palm_cm", abs(palm - open_["palm_cm"]) < 0.01,
          f"{palm:.2f} cm")

    print("7. Reproducir un CSV (--csv, 23-A)")
    import csv
    import tempfile
    import time
    header = ["frame", "timestamp_ms", "hand_id", "handedness", "score", "landmark_index",
              "x", "y", "z", "img_w", "img_h", "vx", "vy", "vz", "rapidez_cm_s",
              "rapidez_rel_cm_s", "dedo", "fuente", "palma_cm", "x_cm", "y_cm", "z_cm"]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "hand_data_20990101_000000.csv"
        # 3 fotogramas con 100 ms entre sí; en el último, la muñeca con cm
        # de estéreo. "Índice"/"Muñeca" en UTF-8: en Windows se leían mal.
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(header)
            for frame, ts in enumerate((1000, 1100, 1200)):
                for i in range(21):
                    x, y = 0.5 + 0.01 * (i % 5), 0.6 - 0.02 * (i // 4)
                    xyz_cm = ("10", "-5", "45") if frame == 2 and i == 0 else ("", "", "")
                    w.writerow([frame, ts, 3, "Right", 0.9, i, x, y, 0.0, 1280, 720,
                                0, 0, 0, 0, 0, "Muñeca" if i == 0 else "Índice", "mediapipe",
                                8.5, *xyz_cm])
        rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rx.bind(("127.0.0.1", 0))
        rx.settimeout(1.0)
        import threading
        result = {}
        sender = threading.Thread(target=lambda: result.update(
            sent=ub.run_csv(path, rx.getsockname(), speed=2.0)))
        sender.start()
        got, arrivals = [], []
        for _ in range(6):          # se recibe mientras se manda: llegada real de cada uno
            got.append(ub.osc_decode(rx.recv(4096)))
            arrivals.append(time.monotonic())
        sender.join()
        rx.close()
        sent = result.get("sent")
        elapsed = arrivals[4] - arrivals[0]     # 1er y 3er mensaje de fotograma
        rx2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)   # --swap-hands
        rx2.bind(("127.0.0.1", 0))
        rx2.settimeout(1.0)
        ub.run_csv(path, rx2.getsockname(), speed=50.0, swap_hands=True)
        swapped = ub.osc_decode(rx2.recv(4096)), ub.osc_decode(rx2.recv(4096))
        rx2.close()
    check("--csv: manda todos los fotogramas", sent == 3, f"{sent} de 3")
    check("--csv: un mensaje de fotograma y uno de mano por fotograma",
          [a for a, _ in got] == ["/handmotion/frame", "/handmotion/Right"] * 3,
          ", ".join(a for a, _ in got[:2]))
    check("--csv: respeta los tiempos (200 ms grabados a x2 = 100 ms)",
          0.08 <= elapsed < 0.16, f"{elapsed * 1000:.0f} ms")
    check("--csv: tiempo relativo al primer fotograma (s)",
          [round(got[k][1][2], 3) for k in (0, 2, 4)] == [0.0, 0.1, 0.2],
          str([round(got[k][1][2], 3) for k in (0, 2, 4)]))
    check("--csv: palma y id de la mano del CSV", got[1][1][2] == 8.5 and got[1][1][0] == 3.0,
          f"palma {got[1][1][2]}, id {got[1][1][0]:.0f}")
    check("--csv --swap-hands: Right del CSV llega como Left (CSV de antes del 2026-09-23)",
          swapped[1][0] == "/handmotion/Left", swapped[1][0])
    check("--csv: muñeca absoluta del estéreo -> ejes de Unreal (X=z, Y=x, Z=-y)",
          got[5][1][3:6] == [45.0, 10.0, 5.0], str(got[5][1][3:6]))

    ok = all(results)
    print("\nRESULTADO:", "OK" if ok else "FALLA")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
