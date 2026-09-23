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

Ejecutar con el intérprete del venv del proyecto:
    ./venv/bin/python3 Prueba.py

Historial de cambios relevantes: ver CHANGELOG.md.
Última actualización: 2026-09-23.
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
            label = handedness[0].category_name
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


def _centroid(hand_landmarks):
    xs = [lm.x for lm in hand_landmarks]
    ys = [lm.y for lm in hand_landmarks]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _distance(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def draw_landmarks(frame, tracked_hands):
    """
    Dibuja el esqueleto de cada mano sobre el frame.

    Esquema de color: cada dedo tiene su propio color (ver hand_style.py),
    consistente con plot_csv.py, para poder identificar de un vistazo qué
    landmark pertenece a qué dedo sin contar índices. Las conexiones
    muñeca-nudillo (estructura de la palma, no un dedo) van en gris
    neutro. Las puntas de los dedos (landmarks 4/8/12/16/20) se dibujan
    más grandes, con un aro blanco y la inicial del dedo al lado; el
    resto de los landmarks conserva su índice numérico (0-20) como antes.
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
                cv2.putText(frame, hand_style.FINGER_NAMES[finger],
                            (x + 8, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                            color, 1, cv2.LINE_AA)
            else:
                cv2.putText(frame, str(lm_idx), (x + 5, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.3, (230, 230, 230), 1,
                            cv2.LINE_AA)

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


def landmarks_to_rows(frame_idx, timestamp_ms, tracked_hands):
    rows = []
    for track_id, label, score, hand_landmarks in tracked_hands:
        for lm_idx, lm in enumerate(hand_landmarks):
            rows.append([
                frame_idx, timestamp_ms, track_id, label, score,
                lm_idx, lm.x, lm.y, lm.z,
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
        writer.writerow([
            "frame", "timestamp_ms", "hand_id", "handedness", "score",
            "landmark_index", "x", "y", "z",
        ])
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

    start_time = time.time()
    frame_idx = 0
    records = []
    tracker = HandTracker()

    with vision.HandLandmarker.create_from_options(options) as landmarker:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            timestamp_ms = int((time.time() - start_time) * 1000)
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            if result.hand_landmarks:
                tracked_hands = tracker.update(result.hand_landmarks, result.handedness)
                draw_landmarks(frame, tracked_hands)
                records.extend(landmarks_to_rows(frame_idx, timestamp_ms, tracked_hands))

            cv2.imshow("MediaPipe Hands", frame)
            frame_idx += 1
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()
    export_to_csv(records)


if __name__ == "__main__":
    main()
