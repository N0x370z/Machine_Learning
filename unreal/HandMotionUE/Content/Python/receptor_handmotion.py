"""
Receptor de HandMotion3D dentro del editor de Unreal Engine 5 (23-A).

Escucha los mensajes OSC de unreal_bridge.py (captura.py --unreal, o
unreal_bridge.py --csv / --demo, o el panel) y mueve la mano de
handmotion_escena.py en el nivel abierto. Arranca solo al abrir
HandMotionUE.uproject (lo importa init_unreal.py).

Por qué un socket de Python y no el plugin OSC: comprobado en UE 5.8 que
el plugin OSC recibe los paquetes y dispara On OSC Message Received, pero
FOSCMessage guarda el paquete en un campo que no es UPROPERTY y Python
recibe una copia vacía (dirección "/", sin floats). Desde Blueprint sí
funciona (ver UNREAL.md). Este receptor decodifica el OSC él mismo.

Registro: Saved/handmotion_receptor.log.
"""

import os
import socket
import time

import unreal

import handmotion_escena as escena

PORT = int(os.environ.get("HM_PUERTO", "8000"))
LOG_PATH = os.path.join(unreal.Paths.project_saved_dir(), "handmotion_receptor.log")
_log_file = open(LOG_PATH, "w", encoding="utf-8")


def log(text):
    _log_file.write(f"{time.strftime('%H:%M:%S')} {text}\n")
    _log_file.flush()
    unreal.log(f"[HandMotion] {text}")


escena.new_level()
escena.build_stage()
hands = {}                     # "Left"/"Right" -> HandModel (se crea al llegar)
state = {"frames": 0, "msgs": 0, "t_log": time.monotonic(), "last": None}

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
editor.set_level_viewport_camera_info(*escena.look_from(escena.FRONT_VIEW))

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PORT))
sock.setblocking(False)


def _on_message(address, floats):
    state["msgs"] += 1
    if address == "/handmotion/frame":
        state["frames"] += 1
        return
    if not address.startswith("/handmotion/") or len(floats) != 87:
        log(f"mensaje ignorado: {address} con {len(floats)} floats")
        return
    label = address.rsplit("/", 1)[-1]
    if label not in hands:
        hands[label] = escena.HandModel() if not hands else None
        log(f"llegó la mano {label}")
    if hands[label] is not None:         # una sola mano dibujada (la primera)
        pts = hands[label].apply(floats)
        state["last"] = (label, pts[0], pts[8], floats[2], floats[72:87])


def _tick(_dt):
    while True:
        try:
            packet, _ = sock.recvfrom(4096)
        except (BlockingIOError, OSError):
            break
        try:
            _on_message(*escena.osc_decode(packet))
        except Exception as exc:          # un paquete raro no debe tumbar el tick
            log(f"paquete inválido: {exc!r}")
    now = time.monotonic()
    if now - state["t_log"] >= 1.0 and state["last"]:
        state["t_log"] = now
        label, wrist, tip, palm, flex = state["last"]
        log(f"{state['frames']} fotogramas; {label}: palma {palm:.1f} cm, "
            f"muñeca ({wrist.x:.1f}, {wrist.y:.1f}, {wrist.z:.1f}), "
            f"punta del índice ({tip.x:.1f}, {tip.y:.1f}, {tip.z:.1f}), "
            f"flexión del índice {flex[3]:.0f}/{flex[4]:.0f}/{flex[5]:.0f}°")


tick_handle = unreal.register_slate_post_tick_callback(_tick)
log(f"receptor listo: esperando mensajes OSC en el puerto {PORT}")
