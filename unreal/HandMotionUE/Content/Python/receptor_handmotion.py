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
CENTER_SMOOTHING = 0.05        # cuánto se mueve el centro hacia las muñecas por mensaje
# Posición de cada mano en pantalla (2026-11-24). Con una cámara, la
# muñeca en cm se calcula con el largo de la palma en la imagen; cuando la
# palma gira se ve más corta, la escala cambia y la muñeca salta 8-16 cm
# entre fotogramas (en las capturas guardadas recorre hasta 140 cm). Por
# eso se sigue solo una fracción del movimiento y más suavizado que la
# forma de la mano: la mano se desplaza sin brincar ni salir de cuadro.
FOLLOW = 0.35                  # fracción del desplazamiento del par de manos que se muestra
SEPARATION = 0.8               # fracción de la separación entre las dos manos que se respeta
MIN_GAP_CM = 14.0              # separación horizontal mínima entre las dos manos en pantalla
BASE_SMOOTHING = 0.25          # por mensaje (~0.2 s a 15 fotogramas por segundo)
MIN_MESSAGES = 3               # una mano nueva aparece tras 3 mensajes (filtra detecciones falsas)
LOG_PATH = os.path.join(unreal.Paths.project_saved_dir(), "handmotion_receptor.log")
_log_file = open(LOG_PATH, "w", encoding="utf-8")


def log(text):
    _log_file.write(f"{time.strftime('%H:%M:%S')} {text}\n")
    _log_file.flush()
    unreal.log(f"[HandMotion] {text}")


def setup_editor_view():
    """
    Cámara del viewport frente a las manos y vista de juego (sin iconos de
    luces). Se llama desde el tick, cuando el editor ya terminó de cargar:
    al importar este módulo el viewport todavía no existe y la cámara se
    quedaba donde estaba, mirando a otro lado (2026-11-24). Devuelve dónde
    quedó la cámara.
    """
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    loc, rot = escena.look_from(escena.TWO_HANDS_VIEW)
    editor.set_level_viewport_camera_info(loc, rot)
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_set_game_view(True)
    except Exception as exc:
        log(f"vista de juego no disponible: {exc}")
    # El freno en segundo plano se quita en Config/DefaultEditorPerProjectUserSettings.ini.
    got = editor.get_level_viewport_camera_info()
    return got[0] if isinstance(got, (tuple, list)) else None


escena.new_level()
escena.build_stage()
slots = [escena.make_hand(tag) for tag in ("", "B")[:MAX_HANDS]]
for s in slots:
    s.set_visible(False)
slot_of = {}                   # id de la mano -> índice en slots
last_seen = [0.0] * MAX_HANDS
bases = [None] * MAX_HANDS     # posición suavizada de la muñeca de cada lugar
wrists = [None] * MAX_HANDS    # última muñeca recibida de cada lugar (cm de la captura)
pending = {}                   # id nuevo -> (mensajes vistos, último instante)
state = {"frames": 0, "msgs": 0, "t_log": time.monotonic(), "last": None, "center": None,
         "labels": set(), "t_start": time.monotonic(), "camera_ok": False}
CAMERA_CHECK_S = 2.0           # colocar la cámara desde 2 s después de arrancar

# Manos con huesos: hace falta el modo Simulate (ver mano_esqueletal.py).
NEEDS_SIMULATE = any(getattr(s, "NEEDS_SIMULATE", False) for s in slots)
state["sim"] = "no" if not NEEDS_SIMULATE else "pendiente"   # pendiente -> arrancando -> listo


def pie_copy(actor):
    """La copia de un actor del editor en el mundo de Simulate (o None)."""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if world is None:
        return None
    name = actor.get_name()
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, type(actor)):
        if a.get_name() == name:
            return a
    return None


def _simulate(now):
    """Arranca Simulate cuando el editor ya cargó y enlaza las manos con sus copias."""
    if state["sim"] == "pendiente" and now - state["t_start"] >= CAMERA_CHECK_S:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_play_simulate()
        state["sim"] = "arrancando"
        log("modo Simulate: arrancando (la mano con huesos solo se redibuja así)")
    elif state["sim"] == "arrancando":
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        if world is not None and all(s.bind(world) for s in slots):
            state["sim"] = "listo"
            state["camera_ok"] = False           # colocar la cámara otra vez, ya en Simulate
            log("modo Simulate: listo")
    elif state["sim"] == "listo" and not state.get("closing"):
        # Si alguien detiene Simulate (Stop), las copias desaparecen: se vuelve a arrancar.
        if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None:
            state["sim"] = "pendiente"
            state["t_start"] = now - CAMERA_CHECK_S + 1.0
            log("modo Simulate: se detuvo; se vuelve a arrancar en 1 s")


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
    slots[i].reset()                 # otra mano: sin arrastrar la pose anterior
    bases[i] = None
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
    hand_id = int(floats[0])
    if hand_id not in slot_of:        # mano nueva: esperar MIN_MESSAGES seguidos
        n, t = pending.get(hand_id, (0, now))
        n = n + 1 if now - t < 0.3 else 1
        pending[hand_id] = (n, now)
        if n < MIN_MESSAGES:
            return
        pending.pop(hand_id, None)
    wrist = unreal.Vector(*floats[3:6])
    c = state["center"]
    state["center"] = wrist if c is None else c + (wrist - c) * CENTER_SMOOTHING
    i = _slot_for(hand_id, now)
    last_seen[i] = now
    slots[i].set_visible(True)
    wrists[i] = wrist
    shown = [k for k in range(MAX_HANDS) if wrists[k] is not None and now - last_seen[k] < HIDE_AFTER_S]
    pair = wrists[i]
    if len(shown) > 1:
        pair = wrists[shown[0]]
        for k in shown[1:]:
            pair = pair + wrists[k]
        pair = pair * (1.0 / len(shown))
    target = (escena.ORIGIN + (pair - state["center"]) * FOLLOW
              + (wrist - pair) * SEPARATION)
    bases[i] = target if bases[i] is None else bases[i] + (target - bases[i]) * BASE_SMOOTHING
    other = [k for k in shown if k != i and bases[k] is not None]
    if other:                        # que no se encimen
        j = other[0]
        gap = bases[i].y - bases[j].y
        if abs(gap) < MIN_GAP_CM:
            side = 1.0 if (gap > 0 or (gap == 0 and wrist.y >= wrists[j].y)) else -1.0
            bases[i] = unreal.Vector(bases[j].y * 0 + bases[i].x, bases[j].y + side * MIN_GAP_CM, bases[i].z)
    pts = slots[i].apply(floats, base=bases[i], label=label)
    state["last"] = (label, pts[0], pts[8], floats[2], floats[72:87])


def _place_camera(now):
    """Coloca la cámara una vez que el viewport existe (lo comprueba leyéndola)."""
    if state["camera_ok"] or now - state["t_start"] < CAMERA_CHECK_S:
        return
    if state["sim"] in ("pendiente", "arrancando"):
        return
    target = escena.look_from(escena.TWO_HANDS_VIEW)[0]
    got = setup_editor_view()
    if got is not None and (got - target).length() < 1.0:
        state["camera_ok"] = True
        log(f"cámara del viewport frente a las manos ({got.x:.0f}, {got.y:.0f}, {got.z:.0f})")
    elif now - state["t_start"] > 60:
        state["camera_ok"] = True
        log(f"no se pudo colocar la cámara del viewport (quedó en {got})")


def _tick(_dt):
    now = time.monotonic()
    _simulate(now)
    _place_camera(now)
    if state["sim"] in ("pendiente", "arrancando") or state.get("closing"):
        while True:                      # mientras arranca Simulate, se descartan los mensajes
            try:
                sock.recvfrom(4096)
            except (BlockingIOError, OSError):
                return
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
        elif slots[k].visible:
            slots[k].step(_dt)       # suavizado entre fotogramas (ver handmotion_escena)
    if now - state["t_log"] >= 1.0 and state["last"]:
        state["t_log"] = now
        label, wrist, tip, palm, flex = state["last"]
        shown = sum(1 for s in slots if s.visible)
        log(f"{state['frames']} fotogramas, {shown} mano(s) en pantalla; {label}: palma {palm:.1f} cm, "
            f"muñeca ({wrist.x:.1f}, {wrist.y:.1f}, {wrist.z:.1f}), "
            f"punta del índice ({tip.x:.1f}, {tip.y:.1f}, {tip.z:.1f}), "
            f"flexión del índice {flex[3]:.0f}/{flex[4]:.0f}/{flex[5]:.0f}°")


tick_handle = unreal.register_slate_post_tick_callback(_tick)
log(f"receptor listo: esperando mensajes OSC en el puerto {PORT} (hasta {MAX_HANDS} manos, estilo {escena.STYLE})")
