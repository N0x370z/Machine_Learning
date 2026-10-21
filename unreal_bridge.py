"""
Puente de HandMotion3D hacia Unreal Engine (desde la versión 19-A,
2026-10-19): manda por red, en tiempo real, la pose de cada mano para que
un modelo 3D de Unreal la siga.

Cómo viaja: OSC (Open Sound Control) sobre UDP. Unreal Engine 5 trae el
plugin "OSC" (Edit > Plugins), que recibe estos mensajes en un Blueprint
sin instalar nada más. Aquí el codificador OSC es propio (unas 30 líneas,
sin dependencias nuevas): solo hacen falta los tipos int, float y string.

Qué manda (un mensaje por mano y por fotograma, y uno por fotograma).
TODO va como floats (ningún int ni string): en Blueprint se lee con un
solo nodo ("Get Floats") y el índice no depende de cómo cuente Unreal.

  /handmotion/frame     floats: [n_fotograma, n_manos, t_segundos]
  /handmotion/Left      mano izquierda  (la lateralidad real, ya corregida)
  /handmotion/Right     mano derecha
      floats: 87 valores, en este orden (ver FLOAT_LAYOUT):
        [0]      id de la mano (el seguimiento; cambia si la pierde)
        [1]      tiene codo: 1 si hay codo (YOLO o estimado), 0 si no
        [2]      largo de palma en cm (escala de la mano)
        [3:6]    posición de la muñeca en cm, ejes de Unreal
        [6:69]   21 puntos (x, y, z) en cm, RELATIVOS a la muñeca
        [69:72]  codo (x, y, z) en cm relativo a la muñeca (0 si no hay)
        [72:87]  flexión en grados de 15 articulaciones (ver JOINTS)

Ejes (convención de Unreal Engine: X adelante, Y derecha, Z arriba, cm):
    Unreal X = profundidad (z de la escena: positiva = se aleja de la cámara)
    Unreal Y = x de la imagen en espejo (positiva = derecha de la pantalla)
    Unreal Z = -y de la imagen (positiva = arriba)
  Con una cámara la profundidad de la muñeca no se conoce (queda en 0) y
  la de los dedos es la z relativa de MediaPipe; con --estereo la posición
  de la muñeca sí es absoluta (cm respecto a la cámara 1).

Flexión: 0° = dedo estirado, positiva = doblado: 180° menos el ángulo
interno entre los dos huesos que se unen en la articulación. Es lo más
cómodo para mover los huesos de un esqueleto en Unreal (un giro por
articulación) sin depender de la orientación de la mano.

Uso suelto (herramientas para probar sin Unreal ni cámara):
    ./venv/bin/python3 unreal_bridge.py --escuchar 8000      # mostrar lo que llega
    ./venv/bin/python3 unreal_bridge.py --demo 127.0.0.1:8000  # mano sintética

Uso real: ./venv/bin/python3 captura.py --unreal 127.0.0.1:8000
Guía de Unreal paso a paso: UNREAL.md.

Historial de cambios relevantes: ver CHANGELOG.md.
Última actualización: 2026-10-19.
"""

import argparse
import math
import socket
import struct
import time

import hand_style
import kinematics

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

ADDR_FRAME = "/handmotion/frame"
ADDR_HAND = "/handmotion/{label}"   # label: Left o Right

# Articulaciones de las que se manda la flexión: (dedo, nombre, a, b, c),
# con el ángulo medido en el punto b entre los puntos a y c (índices de
# MediaPipe). El orden es el de los floats [70:85].
JOINTS = [
    ("Pulgar", "CMC", 0, 1, 2), ("Pulgar", "MCP", 1, 2, 3), ("Pulgar", "IP", 2, 3, 4),
    ("Indice", "MCP", 0, 5, 6), ("Indice", "PIP", 5, 6, 7), ("Indice", "DIP", 6, 7, 8),
    ("Medio", "MCP", 0, 9, 10), ("Medio", "PIP", 9, 10, 11), ("Medio", "DIP", 10, 11, 12),
    ("Anular", "MCP", 0, 13, 14), ("Anular", "PIP", 13, 14, 15), ("Anular", "DIP", 14, 15, 16),
    ("Menique", "MCP", 0, 17, 18), ("Menique", "PIP", 17, 18, 19), ("Menique", "DIP", 18, 19, 20),
]

N_POINTS = 21
N_FLOATS = 2 + 1 + 3 + 3 * N_POINTS + 3 + len(JOINTS)   # 87
FLOAT_LAYOUT = {
    "id": (0, 1),
    "tiene_codo": (1, 2),
    "palma_cm": (2, 3),
    "muneca_cm": (3, 6),
    "puntos_cm": (6, 6 + 3 * N_POINTS),
    "codo_cm": (6 + 3 * N_POINTS, 9 + 3 * N_POINTS),
    "flexion_grados": (9 + 3 * N_POINTS, N_FLOATS),
}


# ---------------------------------------------------------------- OSC

def _pad(data):
    """Rellena con ceros hasta un múltiplo de 4 bytes (regla de OSC)."""
    return data + b"\0" * (-len(data) % 4)


def _osc_string(text):
    """String OSC: UTF-8, terminado en cero y alineado a 4 bytes."""
    return _pad(text.encode("utf-8") + b"\0")


def osc_message(address, args):
    """
    Codifica un mensaje OSC 1.0. args: lista de int, float o str (el tipo
    de Python decide el de OSC: int -> 'i', float -> 'f', str -> 's').
    """
    tags, payload = ",", b""
    for arg in args:
        if isinstance(arg, bool):
            arg = int(arg)
        if isinstance(arg, int):
            tags += "i"
            payload += struct.pack(">i", arg)
        elif isinstance(arg, float):
            tags += "f"
            payload += struct.pack(">f", arg)
        elif isinstance(arg, str):
            tags += "s"
            payload += _osc_string(arg)
        else:
            raise TypeError(f"Tipo no soportado en OSC: {type(arg).__name__}")
    return _osc_string(address) + _osc_string(tags) + payload


def osc_decode(packet):
    """
    Decodifica un mensaje OSC (el inverso de osc_message). Devuelve
    (dirección, [argumentos]). Sirve para --escuchar y para las pruebas.
    """
    def read_string(pos):
        end = packet.index(b"\0", pos)
        return packet[pos:end].decode("utf-8"), (end + 4) & ~3

    address, pos = read_string(0)
    tags, pos = read_string(pos)
    args = []
    for tag in tags[1:]:
        if tag == "i":
            args.append(struct.unpack_from(">i", packet, pos)[0])
            pos += 4
        elif tag == "f":
            args.append(struct.unpack_from(">f", packet, pos)[0])
            pos += 4
        elif tag == "s":
            text, pos = read_string(pos)
            args.append(text)
        else:
            raise ValueError(f"Tipo OSC no soportado: {tag!r}")
    return address, args


# ------------------------------------------------- de la escena a Unreal

def _to_unreal(v):
    """(X, Y, Z) de la escena -> (X, Y, Z) de Unreal (ver el docstring)."""
    return (v[2], v[0], -v[1])


def flexion_degrees(points):
    """
    Flexión en grados de las 15 articulaciones de JOINTS a partir de los
    21 puntos de la escena. 0 = estirado; positivo = doblado. Un punto
    repetido (vector de largo cero) da 0.
    """
    angles = []
    for _finger, _joint, a, b, c in JOINTS:
        u = [pa - pb for pa, pb in zip(points[a], points[b])]
        w = [pc - pb for pc, pb in zip(points[c], points[b])]
        nu, nw = kinematics._norm(u), kinematics._norm(w)
        if nu < 1e-9 or nw < 1e-9:
            angles.append(0.0)
            continue
        cos = max(-1.0, min(1.0, sum(x * y for x, y in zip(u, w)) / (nu * nw)))
        angles.append(180.0 - math.degrees(math.acos(cos)))
    return angles


def hand_floats(hand):
    """
    Los 87 floats de una mano de la escena (viewer3d.hands_to_scene, con
    "points_cm" si hay estéreo). Ver FLOAT_LAYOUT.
    """
    cm = kinematics.hand_scale(hand)
    points = hand["points"]
    wrist = points[0]
    points_cm = hand.get("points_cm")
    if points_cm is not None and points_cm[0] is not None:
        # Estéreo: posición absoluta en cm (x derecha, y abajo, z adelante).
        wx, wy, wz = points_cm[0]
        wrist_abs = (wz, wx, -wy)
    else:
        wrist_abs = (0.0, wrist[0] * cm, -wrist[1] * cm)
    floats = [float(hand["id"]), 1.0 if hand.get("elbow") is not None else 0.0,
              float(hand.get("palm_cm", kinematics.PALM_LENGTH_CM))]
    floats.extend(wrist_abs)
    for p in points:
        floats.extend(_to_unreal([(pc - wc) * cm for pc, wc in zip(p, wrist)]))
    elbow = hand.get("elbow")
    if elbow is not None:
        floats.extend(_to_unreal([(e - wc) * cm for e, wc in zip(elbow, wrist)]))
    else:
        floats.extend((0.0, 0.0, 0.0))
    floats.extend(flexion_degrees(points))
    assert len(floats) == N_FLOATS
    return [float(f) for f in floats]


def hand_message(hand):
    """Mensaje OSC (bytes) de una mano de la escena."""
    return osc_message(ADDR_HAND.format(label=hand["label"]), hand_floats(hand))


class UnrealBridge:
    """
    Envía por UDP la pose de las manos a Unreal Engine. send_frame no
    bloquea ni lanza errores de red: si Unreal no está escuchando, UDP
    simplemente tira los paquetes (errors cuenta los que el sistema
    rechazó, p. ej. "conexión rehusada" en localhost).
    """

    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        self.address = (host, port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(False)
        self.frames_sent = 0
        self.errors = 0

    def _send(self, packet):
        """Un paquete UDP; los errores de red se cuentan, no se lanzan."""
        try:
            self._sock.sendto(packet, self.address)
        except OSError:
            self.errors += 1

    def send_frame(self, frame_idx, timestamp_ms, hands_scene):
        """Manda el mensaje del fotograma y uno por cada mano."""
        self._send(osc_message(ADDR_FRAME, [
            float(frame_idx), float(len(hands_scene)), float(timestamp_ms) / 1000.0]))
        for hand in hands_scene:
            self._send(hand_message(hand))
        self.frames_sent += 1

    def close(self):
        """Cierra el socket."""
        self._sock.close()


def parse_destino(text):
    """
    "host:puerto", "puerto" o "host" -> (host, puerto). Lanza
    argparse.ArgumentTypeError si el puerto no es válido (1-65535).
    """
    host, port = DEFAULT_HOST, DEFAULT_PORT
    if ":" in text:
        host, _, port_text = text.rpartition(":")
    elif text.isdigit():
        port_text = text
    else:
        host, port_text = text, str(DEFAULT_PORT)
    try:
        port = int(port_text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"puerto inválido: {port_text!r}")
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"el puerto debe estar entre 1 y 65535, no {port}")
    return host or DEFAULT_HOST, port


# ------------------------------------------- herramientas de prueba (CLI)

def listen(port, seconds=None):
    """
    Escucha en el puerto y muestra un resumen de cada mensaje (para
    comprobar el puente sin Unreal). Termina con Ctrl+C o tras `seconds`.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    sock.settimeout(0.5)
    print(f"Escuchando OSC en el puerto {port} (Ctrl+C para salir)...")
    t_end = None if seconds is None else time.monotonic() + seconds
    try:
        while t_end is None or time.monotonic() < t_end:
            try:
                packet, _ = sock.recvfrom(4096)
            except socket.timeout:
                continue
            address, args = osc_decode(packet)
            if address == ADDR_FRAME:
                print(f"{address}  fotograma {args[0]:.0f}, manos {args[1]:.0f}, t = {args[2]:.3f} s")
            else:
                flex = args[FLOAT_LAYOUT["flexion_grados"][0]:]
                print(f"{address}  id {args[0]:.0f}, codo {args[1]:.0f}, {len(args)} floats; "
                      f"flexión índice (MCP/PIP/DIP): "
                      + " / ".join(f"{a:5.1f}" for a in flex[3:6]))
    except KeyboardInterrupt:
        print()
    finally:
        sock.close()


def demo_hand(t, palm_cm=9.0):
    """
    Mano sintética (21 puntos de la escena) que abre y cierra los dedos
    con el tiempo t (s). Sirve para probar Unreal sin cámara.
    """
    cm = 0.012                           # unidades de escena por cm (1 u ~ 83 cm)
    palm = palm_cm * cm
    points = [(0.5, 0.6, 0.0)] + [(0.0, 0.0, 0.0)] * 20
    curl = 0.5 * (1 - math.cos(2 * math.pi * 0.5 * t))   # 0..1, un ciclo cada 2 s
    spread = [-0.5, -0.2, 0.0, 0.15, 0.3]
    for finger in range(5):
        base_x = 0.5 + (finger - 2) * palm * 0.22
        mcp = (base_x, 0.6 - palm * (0.55 if finger else 0.2), 0.0)
        pts = [mcp]
        x, y, z, ang = mcp[0], mcp[1], mcp[2], spread[finger]
        for k in range(3):
            ang += curl * math.radians(55 if k else 35) * (1 if finger else 0.6)
            step = palm * (0.45 - 0.05 * k)
            x += step * math.sin(spread[finger]) * 0.3
            y -= step * math.cos(ang)
            z -= step * math.sin(ang) * 0.6
            pts.append((x, y, z))
        for k, p in enumerate(pts):
            idx = 1 + finger * 4 + k
            points[idx] = p
    points[9] = (0.5, 0.6 - palm, 0.0)
    return {"id": 0, "label": "Right", "points": points, "elbow": None,
            "elbow_source": None, "palm_cm": palm_cm, "cm_per_unit": 1 / cm}


def run_demo(destino, seconds, fps=30):
    """Manda una mano sintética a destino durante `seconds` s (None = sin fin)."""
    host, port = destino
    bridge = UnrealBridge(host, port)
    print(f"Mandando una mano sintética a {host}:{port} a {fps} FPS (Ctrl+C para salir)...")
    t0 = time.monotonic()
    idx = 0
    try:
        while seconds is None or time.monotonic() - t0 < seconds:
            t = time.monotonic() - t0
            bridge.send_frame(idx, t * 1000, [demo_hand(t)])
            idx += 1
            time.sleep(1 / fps)
    except KeyboardInterrupt:
        print()
    finally:
        bridge.close()
    print(f"{bridge.frames_sent} fotogramas enviados.")


def parse_args(argv=None):
    """Flags de las herramientas de prueba (--escuchar y --demo)."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--escuchar", type=int, metavar="PUERTO",
                       help="Muestra los mensajes que llegan a ese puerto.")
    group.add_argument("--demo", type=parse_destino, metavar="HOST:PUERTO",
                       help="Manda una mano sintética (abre y cierra los dedos).")
    parser.add_argument("--segundos", type=float, default=None,
                        help="Termina solo tras estos segundos (default: sin fin).")
    return parser.parse_args(argv)


def main():
    """Punto de entrada de las herramientas de prueba."""
    args = parse_args()
    if args.escuchar is not None:
        listen(args.escuchar, args.segundos)
    else:
        run_demo(args.demo, args.segundos)


if __name__ == "__main__":
    main()
