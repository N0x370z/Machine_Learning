"""
Receptor de HandMotion3D dentro del editor de Unreal Engine 5 (23-A).

Escucha los mensajes OSC de unreal_bridge.py (captura.py --unreal, o
unreal_bridge.py --csv / --demo, o el panel) y mueve hasta DOS manos de
handmotion_escena.py en el nivel abierto. Arranca solo al abrir
HandMotionUE.uproject (lo importa init_unreal.py).

Dos manos (2026-11-24): las capturas guardadas tienen las dos manos en el
65-100 % de los fotogramas. Cada mano que llega (por su id) ocupa un
lugar libre; si deja de llegar durante HIDE_AFTER_S se oculta y el lugar
queda libre. Se dibujan con su separación real, centradas en pantalla: el
centro es el promedio (suavizado) de las muñecas.

Vista del editor (2026-11-24): exposición fija como en las imágenes de
la documentación (sin ella el viewport se quema o se oscurece según la
escena), vista de juego (sin iconos de luces) y sin el freno de Unreal
cuando su ventana no está al frente (la reproducción se trababa).

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
MAX_HANDS = 2
HIDE_AFTER_S = 0.5             # sin mensajes de una mano durante esto: se oculta
CENTER_SMOOTHING = 0.08        # cuánto se mueve el centro hacia las muñecas por mensaje
LOG_PATH = os.path.join(unreal.Paths.project_saved_dir(), "handmotion_receptor.log")
_log_file = open(LOG_PATH, "w", encoding="utf-8")


def log(text):
    _log_file.write(f"{time.strftime('%H:%M:%S')} {text}\n")
    _log_file.flush()
    unreal.log(f"[HandMotion] {text}")


def setup_editor_view():
    """Cámara frente a las manos y vista de juego (sin iconos de luces)."""
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    editor.set_level_viewport_camera_info(*escena.look_from(escena.TWO_HANDS_VIEW))
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
    except Exception as exc:
        log(f"vista de juego no disponible: {exc}")
    # El freno en segundo plano se quita en Config/DefaultEditorPerProjectUserSettings.ini.


escena.new_level()
escena.build_stage()
setup_editor_view()
slots = [escena.HandModel(tag) for tag in ("", "B")[:MAX_HANDS]]
for s in slots:
    s.set_visible(False)
slot_of = {}                   # id de la mano -> índice en slots
last_seen = [0.0] * MAX_HANDS
state = {"frames": 0, "msgs": 0, "t_log": time.monotonic(), "last": None, "center": None,
         "labels": set()}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PORT))
sock.setblocking(False)


def _slot_for(hand_id, now):
    """Lugar de esta mano: el que ya tenía, o uno libre (o el más viejo)."""
    i = slot_of.get(hand_id)
    if i is not None and now - last_seen[i] < HIDE_AFTER_S * 4:
        return i
    free = [k for k in range(MAX_HANDS) if now - last_seen[k] >= HIDE_AFTER_S]
    i = free[0] if free else min(range(MAX_HANDS), key=lambda k: last_seen[k])
    for other, k in list(slot_of.items()):
        if k == i:
            del slot_of[other]
    slot_of[hand_id] = i
    return i


def _on_message(address, floats, now):
    state["msgs"] += 1
    if address == "/handmotion/frame":
        state["frames"] += 1
        return
    if not address.startswith("/handmotion/") or len(floats) != 87:
        log(f"mensaje ignorado: {address} con {len(floats)} floats")
        return
    label = address.rsplit("/", 1)[-1]
    if label not in state["labels"]:
        state["labels"].add(label)
        log(f"llegó la mano {label}")
    wrist = unreal.Vector(*floats[3:6])
    c = state["center"]
    state["center"] = wrist if c is None else c + (wrist - c) * CENTER_SMOOTHING
    i = _slot_for(int(floats[0]), now)
    last_seen[i] = now
    slots[i].set_visible(True)
    pts = slots[i].apply(floats, base=escena.ORIGIN + (wrist - state["center"]))
    state["last"] = (label, pts[0], pts[8], floats[2], floats[72:87])


def _tick(_dt):
    now = time.monotonic()
    while True:
        try:
            packet, _ = sock.recvfrom(4096)
        except (BlockingIOError, OSError):
            break
        try:
            _on_message(*escena.osc_decode(packet), now)
        except Exception as exc:          # un paquete raro no debe tumbar el tick
            log(f"paquete inválido: {exc!r}")
    for k in range(MAX_HANDS):
        if now - last_seen[k] >= HIDE_AFTER_S:
            slots[k].set_visible(False)
    if now - state["t_log"] >= 1.0 and state["last"]:
        state["t_log"] = now
        label, wrist, tip, palm, flex = state["last"]
        shown = sum(1 for s in slots if s.visible)
        log(f"{state['frames']} fotogramas, {shown} mano(s) en pantalla; {label}: palma {palm:.1f} cm, "
            f"muñeca ({wrist.x:.1f}, {wrist.y:.1f}, {wrist.z:.1f}), "
            f"punta del índice ({tip.x:.1f}, {tip.y:.1f}, {tip.z:.1f}), "
            f"flexión del índice {flex[3]:.0f}/{flex[4]:.0f}/{flex[5]:.0f}°")


tick_handle = unreal.register_slate_post_tick_callback(_tick)
log(f"receptor listo: esperando mensajes OSC en el puerto {PORT} (hasta {MAX_HANDS} manos)")
