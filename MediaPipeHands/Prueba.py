"""
Detección de manos en tiempo real con MediaPipe (Tasks API).

El detector de manos vive en la Tasks API:
mediapipe.tasks.python.vision.HandLandmarker, y requiere un modelo .task
descargado aparte (ver models/hand_landmarker.task).

IMPORTANTE: el proyecto está fijado a mediapipe==0.10.35 (ver
requirements.txt). Las versiones 1.0.0/1.0.1 tienen un bug conocido en
macOS que crashea cualquier tarea de visión con
"Check failed: service_ Service is unavailable" / DrishtiMetalHelper
(TensorsToDetectionsCalculator intenta inicializar un helper de Metal/GPU
que nunca se registra en un grafo de solo-CPU). Ver:
https://github.com/google-ai-edge/mediapipe/issues/6356
No actualizar mediapipe sin volver a probar en macOS.

Además de la ventana de la cámara (2D), abre un visor 3D con dos puntos
de vista (POV) de la misma escena, como los viewports de Blender (ver
viewer3d.py), que usa la profundidad z de MediaPipe. El esqueleto se
extiende hasta el antebrazo (codo -> muñeca) con YOLO pose (ver
forearm.py), y se calcula la velocidad de cada punto a partir de su
posición x, y, z y del tiempo de cada fotograma (ver kinematics.py).

Ejecutar con el intérprete del venv del proyecto:
    ./venv/bin/python3 Prueba.py
    ./venv/bin/python3 Prueba.py --sin-antebrazo   # sin YOLO (más liviano)
    ./venv/bin/python3 Prueba.py --sin-3d          # sin el visor de dos POV

Velocidad: de cada punto (flechas), de la muñeca y de cada dedo (su
punta), absoluta o relativa a la muñeca (tecla 'f'). Ver kinematics.py.

Para salir: 'q' o Esc en cualquiera de las dos ventanas, o cerrar la
ventana de la cámara. En los tres casos se guarda el CSV (también con
Ctrl+C en la terminal).

Historial de cambios relevantes: ver CHANGELOG.md.
Última actualización: 2026-09-24.
"""

import argparse
import csv
import time
from collections import Counter, deque
from datetime import datetime
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision

import hand_style
import kinematics
import viewer3d

MODEL_PATH = Path(__file__).parent / "models" / "hand_landmarker.task"
OUTPUT_DIR = Path(__file__).parent / "capturas"

# Conexiones entre landmarks para dibujar el "esqueleto" de la mano.
HAND_CONNECTIONS = vision.HandLandmarksConnections.HAND_CONNECTIONS

# Manos simultáneas por defecto. No hay límite físico de "2" real: el modelo
# puede rastrear tantas manos como veas en cámara (varias personas incluidas),
# num_hands solo pone un tope al costo de cómputo. Ajustable con --max-hands.
DEFAULT_MAX_HANDS = 4

# Umbrales de confianza del detector, expuestos como flags (ver
# parse_args). Antes estaban fijos en el código (0.5 los tres) y, con
# cámaras de baja resolución o poca luz, MediaPipe fallaba en reconocer
# la mano o la perdía apenas se giraba/alejaba un poco (bug documentado
# en CHANGELOG.md, corregido en esta versión). Bajarlos ayuda a que se
# reconozca antes a costa de más falsos positivos; subirlos hace lo
# contrario.
DEFAULT_MIN_DETECTION_CONFIDENCE = 0.5
DEFAULT_MIN_PRESENCE_CONFIDENCE = 0.5
DEFAULT_MIN_TRACKING_CONFIDENCE = 0.5

# Resolución de captura solicitada a la cámara. Muchas webcams abren por
# defecto a 640x480, lo que deja muy pocos píxeles por mano cuando está
# a media distancia y degrada la precisión de MediaPipe. Pedir una
# resolución mayor (si la cámara la soporta; si no, cv2 ignora el pedido
# sin fallar) fue parte de la corrección del bug de reconocimiento.
DEFAULT_CAM_WIDTH = 1280
DEFAULT_CAM_HEIGHT = 720

# Parámetros del tracker de manos (ver HandTracker más abajo).
TRACK_MATCH_MAX_DIST = 0.25   # distancia máxima (coords normalizadas) para emparejar con un track existente
TRACK_MAX_AGE = 10            # frames que un track sobrevive sin ser emparejado antes de descartarse
HANDEDNESS_WINDOW = 15        # frames de historial usados para estabilizar Left/Right (~0.5s a 30fps)

CAMERA_WINDOW = "MediaPipe Hands"

# Teclas de salida: 'q' y Esc (27).
QUIT_KEYS = (ord("q"), 27)


class HandTrack:
    _next_id = 0

    def __init__(self, centroid, label, score):
        self.id = HandTrack._next_id
        HandTrack._next_id += 1
        self.centroid = centroid
        self.history = deque(maxlen=HANDEDNESS_WINDOW)
        self.history.append((label, score))
        self.age = 0

    def update(self, centroid, label, score):
        self.centroid = centroid
        self.history.append((label, score))
        self.age = 0

    @property
    def stable_label(self):
        totals = Counter()
        for label, score in self.history:
            totals[label] += score
        return max(totals, key=totals.get)

    @property
    def stable_score(self):
        scores = [score for label, score in self.history if label == self.stable_label]
        return sum(scores) / len(scores)


class HandTracker:
    """
    Asigna una identidad estable (track id) a cada mano entre frames y
    suaviza la clasificación Left/Right de MediaPipe con un voto ponderado
    sobre una ventana de frames recientes.

    MediaPipe reclasifica "handedness" de forma independiente en cada frame,
    así que con ciertos movimientos (mano de perfil, dorso hacia la cámara,
    manos cruzándose) puede parpadear entre Left/Right de un frame a otro
    aunque sea físicamente la misma mano. Emparejar por cercanía del
    centroide entre frames + votar en una ventana corta filtra esos
    parpadeos puntuales sin introducir un retraso perceptible, y además
    mantiene la identidad de la mano si desaparece un par de frames
    (oclusión momentánea) y vuelve a aparecer cerca de donde estaba.
    """

    def __init__(self):
        self.tracks = []

    def update(self, hand_landmarks_list, handedness_list):
        centroids = [_centroid(lm) for lm in hand_landmarks_list]

        pairs = []
        for det_idx, centroid in enumerate(centroids):
            for track in self.tracks:
                dist = _distance(centroid, track.centroid)
                if dist <= TRACK_MATCH_MAX_DIST:
                    pairs.append((dist, det_idx, track))
        pairs.sort(key=lambda p: p[0])

        assignments = [None] * len(hand_landmarks_list)
        used_tracks = set()
        for dist, det_idx, track in pairs:
            if assignments[det_idx] is not None or id(track) in used_tracks:
                continue
            assignments[det_idx] = track
            used_tracks.add(id(track))

        results = []
        for det_idx, (landmarks, handedness) in enumerate(
            zip(hand_landmarks_list, handedness_list)
        ):
            label = _swap_handedness(handedness[0].category_name)
            score = handedness[0].score
            centroid = centroids[det_idx]
            track = assignments[det_idx]
            if track is None:
                track = HandTrack(centroid, label, score)
                self.tracks.append(track)
                assignments[det_idx] = track
            else:
                track.update(centroid, label, score)
            results.append((track.id, track.stable_label, track.stable_score, landmarks))

        matched_ids = {id(t) for t in assignments if t is not None}
        still_alive = []
        for track in self.tracks:
            if id(track) not in matched_ids:
                track.age += 1
            if track.age <= TRACK_MAX_AGE:
                still_alive.append(track)
        self.tracks = still_alive

        return results


def _swap_handedness(label):
    """
    Corrige la lateralidad cruda de MediaPipe, que sale invertida en este
    flujo: el frame se voltea (efecto espejo) antes de pasarlo al modelo,
    y con eso la mano derecha real llegaba etiquetada como "Left" y
    viceversa. Se corrige aquí, antes del tracker, para que tanto la vista
    en vivo como el CSV exportado usen la lateralidad real de la persona.
    """
    return {"Left": "Right", "Right": "Left"}.get(label, label)


def _centroid(hand_landmarks):
    xs = [lm.x for lm in hand_landmarks]
    ys = [lm.y for lm in hand_landmarks]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _distance(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def draw_landmarks(frame, tracked_hands, show_names=True, finger_speeds=None):
    """
    Dibuja el esqueleto de cada mano sobre el frame.

    Esquema de color: cada dedo tiene su propio color (ver hand_style.py),
    consistente con plot_csv.py, para poder identificar de un vistazo qué
    landmark pertenece a qué dedo sin contar índices. Las conexiones
    muñeca-nudillo (estructura de la palma, no un dedo) van en gris
    neutro. Las puntas de los dedos (landmarks 4/8/12/16/20) se dibujan
    más grandes, con un aro blanco y el nombre del dedo al lado (Pulgar,
    Indice, ...). El resto de los landmarks ya no lleva su índice numérico
    (0-20): saturaba la vista y tapaba los nombres de los dedos.

    show_names=False oculta los nombres de los dedos (tecla 'n'), útil
    cuando los dedos están juntos (puño, mano de perfil) y se enciman.

    finger_speeds: {track_id: {dedo: cm/s}} (ver kinematics.finger_speeds).
    Si se pasa, la rapidez de cada dedo se escribe junto a su nombre
    (p. ej. "Indice 32"); None la oculta (tecla 'v').
    """
    h, w, _ = frame.shape
    for track_id, label, score, hand_landmarks in tracked_hands:
        points = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks]

        # Conexiones: un trazo oscuro debajo del color para que el
        # esqueleto se lea nítido tanto sobre fondos claros como oscuros.
        for connection in HAND_CONNECTIONS:
            start_idx, end_idx = connection.start, connection.end
            p0, p1 = points[start_idx], points[end_idx]
            color = hand_style.rgb_to_bgr(
                hand_style.connection_color_rgb(start_idx, end_idx)
            )
            cv2.line(frame, p0, p1, (20, 20, 20), 4, cv2.LINE_AA)
            cv2.line(frame, p0, p1, color, 2, cv2.LINE_AA)

        # Vértices (landmarks): color por dedo, puntas resaltadas.
        for lm_idx, (x, y) in enumerate(points):
            finger = hand_style.finger_of(lm_idx)
            color = hand_style.rgb_to_bgr(hand_style.FINGER_COLORS_RGB[finger])
            is_tip = lm_idx in hand_style.FINGERTIPS
            radius = 7 if is_tip else 4
            cv2.circle(frame, (x, y), radius, (20, 20, 20), -1, cv2.LINE_AA)
            cv2.circle(frame, (x, y), radius - 1, color, -1, cv2.LINE_AA)
            if is_tip:
                cv2.circle(frame, (x, y), radius + 2, (255, 255, 255), 1,
                           cv2.LINE_AA)
            if is_tip and show_names:
                # Contorno oscuro debajo del texto para que el nombre se
                # lea sobre cualquier fondo, igual que las conexiones.
                name = hand_style.FINGER_NAMES_ASCII[finger]
                if finger_speeds and track_id in finger_speeds:
                    name += f" {finger_speeds[track_id][finger]:.0f}"
                # Sombra de 1 px (no contorno grueso): con el número de
                # velocidad el texto es más largo y el contorno grueso
                # dejaba letras "fantasma" al final (ver viewer3d._text).
                viewer3d._text(frame, name, (x + 10, y - 10), color, 0.5)

        # Etiqueta Left/Right + track id, con fondo oscurecido para que se
        # lea sobre cualquier color de piel, ropa o fondo de la escena.
        x0, y0 = points[0]
        text = f"{label} #{track_id}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        pad = 4
        bx0, by0 = max(0, x0 - 20 - pad), max(0, y0 + 30 - th - pad)
        bx1, by1 = min(w, x0 - 20 + tw + pad), min(h, y0 + 30 + pad)
        if bx1 > bx0 and by1 > by0:
            frame[by0:by1, bx0:bx1] = (frame[by0:by1, bx0:bx1] * 0.4).astype(
                frame.dtype
            )
        cv2.putText(frame, text, (x0 - 20, y0 + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2,
                    cv2.LINE_AA)


def draw_forearms(frame, tracked_hands, elbows, show_names=True):
    """
    Dibuja el antebrazo (codo -> muñeca de MediaPipe) de cada mano que
    tenga codo (ver forearm.py), en el azul de 'forearm' de hand_style.py.
    Codo de YOLO: línea gruesa y sólida. Codo estimado (sin YOLO, por el
    eje de la palma): línea fina y punteada, con "(estimado)" en el
    nombre, para no confundirlo con una detección real. Se dibuja ANTES
    que la mano para quedar por debajo de ella, igual que en el cuerpo.
    """
    h, w, _ = frame.shape
    color = hand_style.rgb_to_bgr(hand_style.FINGER_COLORS_RGB["forearm"])
    for track_id, _label, _score, hand_landmarks in tracked_hands:
        elbow = elbows.get(track_id)
        if elbow is None:
            continue
        estimated = elbow.source == "estimado"
        wrist = hand_landmarks[0]
        p_wrist = (int(wrist.x * w), int(wrist.y * h))
        p_elbow = (int(elbow.x * w), int(elbow.y * h))
        if estimated:
            viewer3d._dashed(frame, p_elbow, p_wrist, (20, 20, 20), 5)
            viewer3d._dashed(frame, p_elbow, p_wrist, color, 3)
        else:
            cv2.line(frame, p_elbow, p_wrist, (20, 20, 20), 9, cv2.LINE_AA)
            cv2.line(frame, p_elbow, p_wrist, color, 6, cv2.LINE_AA)
        radius = 5 if estimated else 7
        cv2.circle(frame, p_elbow, radius + 1, (20, 20, 20), -1, cv2.LINE_AA)
        cv2.circle(frame, p_elbow, radius, color, -1, cv2.LINE_AA)
        if show_names:
            name = hand_style.ELBOW_NAME + (" (estimado)" if estimated else "")
            viewer3d._text(frame, name, (p_elbow[0] + 12, p_elbow[1] + 5),
                           color, 0.5)


def draw_velocity(frame, hands_scene):
    """
    Flechas de velocidad sobre el video (tecla 'v'): muñeca, puntas de los
    dedos y codo, con la misma regla que la vista 3D (viewer3d.ARROW_*):
    la flecha apunta a donde estaría el punto dentro de 0.15 s si siguiera
    igual, y no se dibuja por debajo de 4 cm/s (temblor). En 2D solo se
    ve la parte de la velocidad paralela a la imagen (vx, vy); vz se ve en
    la vista 3D.

    Las velocidades están en anchos de frame por segundo en los tres ejes
    (ver kinematics.py), así que tanto vx como vy pasan a píxeles
    multiplicando por el ancho del frame.
    """
    h, w, _ = frame.shape
    for hand in hands_scene:
        vels = hand["velocities"]
        scale = kinematics.cm_per_unit(hand["points"])
        points = viewer3d.scene_points(hand)
        for idx in viewer3d.ARROW_POINTS:
            v = vels.get(idx)
            if v is None or idx not in points:
                continue
            if kinematics.speed_cm_s(v, scale) < viewer3d.MIN_ARROW_CM_S:
                continue
            X, Y, _Z = points[idx]
            p0 = (int(X * w), int(Y * w))
            p1 = (int((X + v[0] * viewer3d.ARROW_SECONDS) * w),
                  int((Y + v[1] * viewer3d.ARROW_SECONDS) * w))
            cv2.arrowedLine(frame, p0, p1, (20, 20, 20), 5, cv2.LINE_AA, tipLength=0.3)
            cv2.arrowedLine(frame, p0, p1, (80, 235, 255), 2, cv2.LINE_AA, tipLength=0.3)


def draw_hud(frame, fps, n_hands, n_frames_recorded, show_names,
             n_elbows=None, show_velocity=True, hand_speeds=(), timings=None,
             finger_rows=(), relative_fingers=False):
    """
    Panel de estado en la esquina superior izquierda: FPS reales del
    bucle, manos detectadas en este frame, frames con manos acumulados
    para el CSV, y las teclas disponibles. Sirve para saber si la
    detección va fluida (FPS bajos -> bajar --max-hands o la resolución)
    y si de verdad se están grabando datos antes de cerrar con 'q'.

    n_elbows: (detectados por YOLO, estimados) en este frame, o None si
    se corrió con --sin-antebrazo.
    hand_speeds: [(etiqueta, cm/s de la muñeca)] por mano.
    finger_rows: [(etiqueta, {dedo: cm/s})] por mano: velocidad de cada
    dedo (absoluta o relativa a la muñeca según relative_fingers, tecla
    'f'; ver kinematics.finger_speeds).
    timings: ms promedio de cada etapa {"mano", "yolo", "3D"}, para ver
    qué es lo que frena el bucle si los FPS bajan.
    """
    if n_elbows is None:
        forearm_text = "off"
    else:
        forearm_text = f"{n_elbows[0]} YOLO + {n_elbows[1]} estimados"
    lines = [
        f"FPS: {fps:4.1f}",
        f"Manos: {n_hands}",
        f"Antebrazos: {forearm_text}",
        f"Frames grabados: {n_frames_recorded}",
    ]
    for label, speed in hand_speeds:
        lines.append(f"Vel. {label}: {speed:5.1f} cm/s")
    if finger_rows:
        mode = "relativa a la muneca" if relative_fingers else "absoluta"
        lines.append(f"Dedos (cm/s, {mode}):")
        for label, speeds in finger_rows:
            lines.append(f"  {label}: " + "  ".join(
                f"{abbr} {speeds[finger]:3.0f}"
                for finger, abbr in hand_style.FINGER_ABBR.items()))
    if timings:
        lines.append("ms: " + "  ".join(f"{k} {v:.0f}" for k, v in timings.items()))
    lines.append(f"[n] nombres: {'si' if show_names else 'no'}  "
                 f"[v] velocidad: {'si' if show_velocity else 'no'}  "
                 f"[f] dedos: {'relativa' if relative_fingers else 'absoluta'}  "
                 "[s] foto  [q] salir")
    font, scale, thick = cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
    line_h = 20
    width = max(cv2.getTextSize(t, font, scale, thick)[0][0] for t in lines)
    x1, y1 = min(frame.shape[1], 10 + width + 16), min(frame.shape[0], 10 + line_h * len(lines) + 10)
    frame[10:y1, 10:x1] = (frame[10:y1, 10:x1] * 0.4).astype(frame.dtype)
    for i, text in enumerate(lines):
        cv2.putText(frame, text, (18, 10 + line_h * (i + 1)), font, scale,
                    (240, 240, 240), thick, cv2.LINE_AA)


def save_screenshot(frame):
    """Guarda el frame mostrado (con el dibujo encima) como PNG en capturas/."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"screenshot_{datetime.now():%Y%m%d_%H%M%S_%f}.png"
    cv2.imwrite(str(out_path), frame)
    print(f"Captura de pantalla guardada en {out_path}")


CSV_HEADER = [
    "frame", "timestamp_ms", "hand_id", "handedness", "score",
    "landmark_index", "x", "y", "z", "img_w", "img_h",
    "vx", "vy", "vz", "rapidez_cm_s", "rapidez_rel_cm_s", "dedo", "fuente",
]


def landmarks_to_rows(frame_idx, timestamp_ms, hands_scene, scores,
                      img_w, img_h):
    """
    Filas del CSV: 21 por mano (landmarks de MediaPipe, 0-20) y, si esa
    mano tiene antebrazo, una fila más con el codo como landmark 21
    (hand_style.ELBOW_INDEX), con z estimada (ver forearm.py).

    - x, y, z: como los da MediaPipe (x, y normalizados 0-1; z relativa a
      la muñeca). Para el codo, en la misma convención.
    - img_w/img_h: tamaño del frame, para reconstruir la escena 3D con la
      proporción correcta en plot_csv.py --3d.
    - vx, vy, vz: velocidad en anchos de frame por segundo (ver
      kinematics.py); rapidez_cm_s: su módulo en cm/s aproximados.
    - rapidez_rel_cm_s: rapidez respecto a la muñeca (lo que se mueve el
      punto dentro de la mano). En las puntas (4, 8, 12, 16, 20) es la
      velocidad relativa de ese dedo; en la muñeca siempre es 0.
    - dedo: a qué parte pertenece el punto (Pulgar, Índice, Medio,
      Anular, Meñique, Muñeca o Codo), para filtrar por dedo sin
      memorizar índices.
    - fuente: "mediapipe" (0-20), "yolo" o "estimado" (codo).

    hands_scene: lista de viewer3d.hands_to_scene (tiene posiciones,
    codo y velocidades de cada mano); scores: {track_id: score}.
    """
    aspect = img_h / img_w
    rows = []
    for hand in hands_scene:
        scale = kinematics.cm_per_unit(hand["points"])
        points = viewer3d.scene_points(hand)
        wrist_v = hand["velocities"].get(0, (0.0, 0.0, 0.0))
        for idx in sorted(points):
            X, Y, Z = points[idx]
            v = hand["velocities"].get(idx, (0.0, 0.0, 0.0))
            source = "mediapipe" if idx < 21 else hand["elbow_source"]
            rows.append([
                frame_idx, timestamp_ms, hand["id"], hand["label"],
                scores[hand["id"]], idx, X, Y / aspect, Z, img_w, img_h,
                *v, kinematics.speed_cm_s(v, scale),
                kinematics.relative_speed_cm_s(v, wrist_v, scale),
                hand_style.point_name(idx), source,
            ])
    return rows


def export_to_csv(records):
    if not records:
        print("No se detectaron manos, no hay datos que exportar.")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"hand_data_{datetime.now():%Y%m%d_%H%M%S}.csv"

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        writer.writerows(records)

    print(f"Datos exportados a {out_path}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-hands", type=int, default=DEFAULT_MAX_HANDS,
        help=(
            "Número máximo de manos a detectar a la vez "
            f"(default: {DEFAULT_MAX_HANDS}). Súbelo si hay varias personas "
            "en cámara; cada mano extra cuesta más cómputo por frame."
        ),
    )
    parser.add_argument(
        "--min-detection-confidence", type=float,
        default=DEFAULT_MIN_DETECTION_CONFIDENCE,
        help=(
            "Confianza mínima para detectar una mano nueva "
            f"(default: {DEFAULT_MIN_DETECTION_CONFIDENCE}). Bájalo si "
            "cuesta que te reconozca la mano; subirlo reduce falsos "
            "positivos."
        ),
    )
    parser.add_argument(
        "--min-presence-confidence", type=float,
        default=DEFAULT_MIN_PRESENCE_CONFIDENCE,
        help=(
            "Confianza mínima para seguir considerando presente una mano "
            f"ya detectada (default: {DEFAULT_MIN_PRESENCE_CONFIDENCE})."
        ),
    )
    parser.add_argument(
        "--min-tracking-confidence", type=float,
        default=DEFAULT_MIN_TRACKING_CONFIDENCE,
        help=(
            "Confianza mínima del tracking entre frames "
            f"(default: {DEFAULT_MIN_TRACKING_CONFIDENCE}). Bájalo si la "
            "mano se 'pierde' seguido con movimiento rápido."
        ),
    )
    parser.add_argument(
        "--cam-width", type=int, default=DEFAULT_CAM_WIDTH,
        help=f"Ancho de captura solicitado a la cámara (default: {DEFAULT_CAM_WIDTH}).",
    )
    parser.add_argument(
        "--cam-height", type=int, default=DEFAULT_CAM_HEIGHT,
        help=f"Alto de captura solicitado a la cámara (default: {DEFAULT_CAM_HEIGHT}).",
    )
    parser.add_argument(
        "--sin-antebrazo", action="store_true",
        help=(
            "No detecta el antebrazo con YOLO pose (el esqueleto llega solo "
            "hasta la muñeca). Más liviano si los FPS bajan."
        ),
    )
    parser.add_argument(
        "--sin-3d", action="store_true",
        help="No abre el visor 3D de dos POV (solo la ventana de la cámara).",
    )
    parser.add_argument(
        "--yolo-modelo", choices=("n", "s", "m"), default="s",
        help=(
            "Tamaño del modelo YOLO pose para el antebrazo (default: s). "
            "n = más rápido (~6 ms) pero detecta peor el codo; s = ~9 ms; "
            "m = más preciso (~17 ms). Se descarga solo a models/."
        ),
    )
    parser.add_argument(
        "--antebrazo-solo-yolo", action="store_true",
        help=(
            "No estima el antebrazo cuando YOLO no ve el codo: solo se "
            "dibuja cuando YOLO lo detecta de verdad."
        ),
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró el modelo en {MODEL_PATH}. "
            "Descárgalo desde "
            "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
            "hand_landmarker/float16/1/hand_landmarker.task"
        )

    options = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=args.max_hands,
        min_hand_detection_confidence=args.min_detection_confidence,
        min_hand_presence_confidence=args.min_presence_confidence,
        min_tracking_confidence=args.min_tracking_confidence,
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError(
            "No se pudo abrir la cámara. En macOS revisa Ajustes del Sistema > "
            "Privacidad y Seguridad > Cámara y dale permiso a tu terminal."
        )
    # Pedimos más resolución que el default de la webcam (suele ser
    # 640x480) para darle a MediaPipe más píxeles por mano y mejorar el
    # reconocimiento a media/larga distancia. Si la cámara no soporta la
    # resolución pedida, cv2 la ignora sin lanzar error.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.cam_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.cam_height)

    # Tamaño real del frame (la cámara puede ignorar el pedido de arriba).
    img_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    img_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    aspect = img_h / img_w

    forearms = None
    if not args.sin_antebrazo:
        import forearm  # diferido: carga torch/ultralytics (~1-2 s)
        print(f"Cargando YOLO pose (yolo11{args.yolo_modelo}) para el antebrazo...")
        forearms = forearm.ForearmDetector(
            model_size=args.yolo_modelo,
            estimate_fallback=not args.antebrazo_solo_yolo,
        )

    viewer = None if args.sin_3d else viewer3d.DualPOVViewer(aspect=aspect)

    start_time = time.time()
    frame_idx = 0
    records = []
    tracker = HandTracker()
    velocity = kinematics.VelocityEstimator()
    show_names = True
    show_velocity = True
    relative_fingers = False  # tecla 'f': velocidad de dedos absoluta/relativa
    frames_recorded = 0
    fps = 0.0
    last_tick = time.time()
    # ms promedio por etapa (media exponencial), para el panel de estado.
    timings = {"mano": 0.0, "yolo": 0.0, "3D": 0.0}

    def timed(stage, t0):
        timings[stage] = 0.9 * timings[stage] + 0.1 * (time.time() - t0) * 1000

    # try/finally: pase lo que pase (q, Esc, cerrar la ventana, Ctrl+C o
    # un error) se libera la cámara, se cierran las ventanas y se guarda
    # el CSV con lo grabado hasta ese momento.
    try:
        with vision.HandLandmarker.create_from_options(options) as landmarker:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

                timestamp_ms = int((time.time() - start_time) * 1000)
                t0 = time.time()
                result = landmarker.detect_for_video(mp_image, timestamp_ms)
                timed("mano", t0)

                tracked_hands, elbows, hands_scene, finger_speeds = [], {}, [], {}
                if result.hand_landmarks:
                    tracked_hands = tracker.update(result.hand_landmarks, result.handedness)
                    # YOLO solo corre si hay manos: sin mano no hay antebrazo
                    # que unir y así no se gasta cómputo de más.
                    if forearms is not None:
                        t0 = time.time()
                        arms = forearms.detect_arms(frame)
                        elbows = forearms.update(arms, tracked_hands, aspect)
                        timed("yolo", t0)
                    hands_scene = viewer3d.hands_to_scene(tracked_hands, elbows, aspect)
                    # Velocidad de cada punto: posición x, y, z + tiempo real
                    # del fotograma (ver kinematics.py).
                    for hand in hands_scene:
                        hand["velocities"] = velocity.update(
                            hand["id"], timestamp_ms / 1000,
                            viewer3d.scene_points(hand))
                    finger_speeds = {
                        h["id"]: {f: v[1 if relative_fingers else 0] for f, v in
                                  kinematics.finger_speeds(h["points"], h["velocities"]).items()}
                        for h in hands_scene
                    }
                    draw_forearms(frame, tracked_hands, elbows, show_names)
                    draw_landmarks(frame, tracked_hands, show_names,
                                   finger_speeds if show_velocity else None)
                    if show_velocity:
                        draw_velocity(frame, hands_scene)
                    scores = {t[0]: t[2] for t in tracked_hands}
                    records.extend(landmarks_to_rows(frame_idx, timestamp_ms,
                                                     hands_scene, scores,
                                                     img_w, img_h))
                    frames_recorded += 1
                n_hands = len(tracked_hands)

                if viewer is not None:
                    if viewer.is_open():
                        t0 = time.time()
                        viewer.render(hands_scene, f"manos: {n_hands}", show_velocity,
                                      relative_fingers)
                        timed("3D", t0)
                    else:
                        viewer = None  # la cerró el usuario: se sigue sin 3D

                # FPS suavizado (media exponencial) para que el número no
                # salte cuadro a cuadro.
                now = time.time()
                dt = now - last_tick
                last_tick = now
                if dt > 0:
                    fps = 1 / dt if fps == 0 else 0.9 * fps + 0.1 / dt

                # Una sola cv2.waitKey recibe las teclas de las dos ventanas
                # (cámara y vista 3D), porque ambas son de OpenCV.
                # La foto se guarda antes de dibujar el HUD para que no salga
                # el panel de estado en la imagen.
                key = cv2.waitKey(1) & 0xFF
                if key in QUIT_KEYS:
                    break
                if key == ord("s"):
                    save_screenshot(frame)
                elif key == ord("n"):
                    show_names = not show_names
                elif key == ord("v"):
                    show_velocity = not show_velocity
                elif key == ord("f"):
                    relative_fingers = not relative_fingers
                elif viewer is not None:
                    viewer.handle_key(key)

                n_elbows = None
                if forearms is not None:
                    n_yolo = sum(e.source == "yolo" for e in elbows.values())
                    n_elbows = (n_yolo, len(elbows) - n_yolo)
                hand_speeds = [
                    (f"{h['label']} #{h['id']}",
                     kinematics.speed_cm_s(h["velocities"].get(0, (0, 0, 0)),
                                           kinematics.cm_per_unit(h["points"])))
                    for h in hands_scene
                ]
                finger_rows = [(f"{h['label']} #{h['id']}", finger_speeds[h["id"]])
                               for h in hands_scene] if show_velocity else []
                draw_hud(frame, fps, n_hands, frames_recorded, show_names,
                         n_elbows, show_velocity, hand_speeds, timings,
                         finger_rows, relative_fingers)
                cv2.imshow(CAMERA_WINDOW, frame)
                frame_idx += 1

                # Cerrar la ventana de la cámara con el botón rojo también
                # termina (antes el bucle seguía corriendo sin ventana).
                if cv2.getWindowProperty(CAMERA_WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                    break
    except KeyboardInterrupt:
        print("\nInterrumpido con Ctrl+C.")
    finally:
        cap.release()
        if viewer is not None:
            viewer.close()
        cv2.destroyAllWindows()
        # En macOS las ventanas de OpenCV no desaparecen hasta que se
        # procesan sus eventos: sin estas vueltas de waitKey quedaban
        # congeladas en pantalla después de salir (parte del bug de 'q').
        for _ in range(10):
            cv2.waitKey(1)
        export_to_csv(records)


if __name__ == "__main__":
    main()
