"""
Detección del antebrazo (codo -> muñeca) con YOLO pose y estimación de
su profundidad (z), para extender el esqueleto de MediaPipe Hands, que
solo llega hasta la muñeca.

Por qué YOLO y no MediaPipe/OpenCV:
  - MediaPipe Hands solo entrega los 21 puntos de la mano.
  - OpenCV por sí solo no trae un detector de codo listo para usar (habría
    que cargar a mano un modelo tipo OpenPose, mucho más pesado).
  - YOLO pose (ultralytics) detecta los 17 keypoints COCO del cuerpo,
    entre ellos codos (7, 8) y muñecas (9, 10).

Modelo: por defecto yolo11s-pose.pt (~9 ms por frame con MPS en Apple
Silicon). Con yolo11n-pose.pt (el de la primera versión, ~6 ms) el codo
se detectaba tarde y mal a distancia de webcam (bug del 2026-09-24, ver
CHANGELOG.md). Se elige con --yolo-modelo en Prueba.py.

Cómo se decide el codo de cada mano, en orden:
  1. YOLO con muñeca visible: la mano de MediaPipe se empareja con el
     brazo de YOLO cuya muñeca esté más cerca de su landmark 0.
  2. YOLO sin muñeca confiable (pasa seguido: la mano tapa la muñeca o
     YOLO duda de ella): se acepta un codo de YOLO si está a una
     distancia plausible (menos de 1.3 antebrazos) y del lado contrario
     a los dedos.
  3. Memoria: si YOLO pierde el codo, se sigue usando el último codo
     detectado (pegado a la muñeca, moviéndose con ella) durante
     HOLD_FRAMES frames. Evita que el antebrazo parpadee.
  4. Estimado: si no hay nada de lo anterior, se prolonga el eje de la
     palma (nudillo del medio -> muñeca) un largo de antebrazo. Se marca
     como "estimado" (línea punteada) y se puede desactivar con
     --antebrazo-solo-yolo.
  No se usa la etiqueta izquierda/derecha de YOLO: con el frame en espejo
  sale invertida, y la cercanía a la muñeca es más confiable.

Profundidad (z) del codo:
  YOLO solo da coordenadas 2D. La z se estima suponiendo un largo real
  de antebrazo proporcional al tamaño de la mano:
      largo_antebrazo = FOREARM_TO_PALM_RATIO * largo_palma_3D
  (largo_palma_3D = muñeca -> nudillo del medio, landmarks 0 -> 9, con z).
  Si el antebrazo se ve más corto en la imagen que ese largo, la diferencia
  se atribuye a que el codo está a otra profundidad:
      dz = sqrt(largo_antebrazo^2 - largo_2D^2)
  El signo es ambiguo con una sola cámara (el codo podría estar delante o
  detrás de la muñeca); se asume DETRÁS (más lejos de la cámara), que es la
  postura normal al mostrarle la mano a la webcam. Es una estimación, no
  una medición: sirve para visualizar, no para medir ángulos exactos.

Última actualización: 2026-09-24. Historial: ver CHANGELOG.md.
"""

import math
from collections import namedtuple
from pathlib import Path

import numpy as np

MODELS_DIR = Path(__file__).parent / "models"
DEFAULT_MODEL = "s"  # n (más rápido), s (default), m (más preciso)

# Codo de una mano. source: "yolo" (detectado ahora o hace pocos frames)
# o "estimado" (prolongación del eje de la palma, ver paso 4 arriba).
Elbow = namedtuple("Elbow", "x y z source")

# Brazo detectado por YOLO. wrist es None si YOLO no confía en la muñeca.
_Arm = namedtuple("_Arm", "wrist elbow")

# Índices de keypoints COCO que usa YOLO pose.
COCO_ELBOWS = (7, 8)    # codo izquierdo, codo derecho
COCO_WRISTS = (9, 10)   # muñeca izquierda, muñeca derecha

# Confianzas mínimas. La primera versión pedía 0.4 a codo Y muñeca a la
# vez, y a distancia de webcam el codo casi nunca llegaba: se bajaron.
YOLO_PERSON_CONF = 0.15   # confianza de la caja de la persona
MIN_ELBOW_CONF = 0.25
MIN_WRIST_CONF = 0.25

# Distancia máxima muñeca YOLO <-> muñeca MediaPipe (unidades del ancho
# del frame): la mayor entre este mínimo y 1.5 palmas (se adapta a lo
# cerca/lejos que esté la mano).
MIN_WRIST_MATCH_DIST = 0.06
WRIST_MATCH_PALMS = 1.5

# Largo del antebrazo (codo -> muñeca) / largo de la palma (muñeca ->
# nudillo del dedo medio). Antropométricamente ~25 cm / ~9.5 cm ≈ 2.6.
FOREARM_TO_PALM_RATIO = 2.6

# Frames que se "recuerda" el último codo de YOLO si deja de verse.
HOLD_FRAMES = 10

# Suavizado exponencial del codo por mano (1 = sin suavizar). YOLO
# tiembla unos píxeles entre frames; esto lo estabiliza y además hace
# suave el paso entre codo detectado y estimado.
ELBOW_SMOOTHING = 0.5


def _pick_device():
    """MPS (GPU de Apple Silicon) si está disponible, si no CPU."""
    try:
        import torch
        if torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


def _scene(lm, aspect):
    """Landmark de MediaPipe -> (X, Y, Z) en la escala del ancho del frame."""
    return np.array([lm.x, lm.y * aspect, lm.z])


class ForearmDetector:
    """
    Envuelve YOLO pose y devuelve, para cada mano rastreada, su codo como
    Elbow(x, y, z, source), con la misma convención que los landmarks de
    MediaPipe: x, y normalizados 0-1 al frame, z relativa a la muñeca y en
    la misma escala que x.
    """

    def __init__(self, model_size=DEFAULT_MODEL, estimate_fallback=True):
        # Import diferido: ultralytics/torch tardan ~1-2 s en cargar y solo
        # hacen falta si se usa el antebrazo (ver --sin-antebrazo).
        from ultralytics import YOLO

        MODELS_DIR.mkdir(exist_ok=True)
        # Si el .pt no está, ultralytics lo descarga a esta ruta.
        self.model = YOLO(str(MODELS_DIR / f"yolo11{model_size}-pose.pt"))
        self.device = _pick_device()
        self.estimate_fallback = estimate_fallback
        self._smoothed = {}  # track_id -> np.array(x, y, z) suavizado
        self._memory = {}    # track_id -> (offset codo-muñeca, frames sin ver)
        self._warmup()

    def _warmup(self):
        """
        La primera inferencia de YOLO (sobre todo en MPS) tarda 0.3-0.7 s
        porque compila/carga los kernels. Antes eso pasaba con la primera
        mano en cámara y se notaba como un tirón y un antebrazo que tardaba
        en aparecer; ahora se paga al arrancar, antes de abrir la cámara.
        """
        dummy = np.zeros((384, 640, 3), dtype=np.uint8)
        for _ in range(2):
            self.model(dummy, verbose=False, device=self.device)

    def detect_arms(self, frame_bgr):
        """
        Corre YOLO pose sobre el frame y devuelve los brazos con codo
        confiable, en coordenadas normalizadas.
        """
        h, w = frame_bgr.shape[:2]
        result = self.model(frame_bgr, verbose=False, device=self.device,
                            conf=YOLO_PERSON_CONF)[0]
        arms = []
        if result.keypoints is None or result.keypoints.data is None:
            return arms
        for person in result.keypoints.data.cpu().numpy():  # (17, 3): x, y, conf
            for elbow_idx, wrist_idx in zip(COCO_ELBOWS, COCO_WRISTS):
                ex, ey, ec = person[elbow_idx]
                wx, wy, wc = person[wrist_idx]
                if ec < MIN_ELBOW_CONF:
                    continue
                wrist = (float(wx / w), float(wy / h)) if wc >= MIN_WRIST_CONF else None
                arms.append(_Arm(wrist, (float(ex / w), float(ey / h))))
        return arms

    def update(self, arms, tracked_hands, aspect):
        """
        Decide el codo de cada mano (ver pasos 1-4 en el docstring del
        módulo). arms puede ser [] (p. ej. si YOLO no corrió).

        aspect = alto/ancho del frame: x e y están normalizados por ancho y
        alto respectivamente, así que y se multiplica por aspect para medir
        distancias en una sola escala (la del ancho, igual que z).

        Devuelve {track_id: Elbow}.
        """
        matches = self._match(arms, tracked_hands, aspect)
        elbows = {}
        for track_id, _label, _score, lms in tracked_hands:
            wrist = _scene(lms[0], aspect)
            if track_id in matches:
                ex, ey = matches[track_id]
                ez = estimate_elbow_z(lms, ex, ey, aspect)
                point = np.array([ex, ey * aspect, ez])
                self._memory[track_id] = (point - wrist, 0)
                source = "yolo"
            elif track_id in self._memory and self._memory[track_id][1] < HOLD_FRAMES:
                offset, age = self._memory[track_id]
                self._memory[track_id] = (offset, age + 1)
                point = wrist + offset
                source = "yolo"
            elif self.estimate_fallback:
                point = estimate_elbow_from_palm(lms, aspect)
                source = "estimado"
            else:
                continue
            point = self._smooth(track_id, point)
            elbows[track_id] = Elbow(float(point[0]), float(point[1] / aspect),
                                     float(point[2]), source)

        # Olvida el estado de manos que ya no están, para que al reaparecer
        # no arranquen desde una posición vieja.
        alive = {t[0] for t in tracked_hands}
        for store in (self._smoothed, self._memory):
            for track_id in list(store):
                if track_id not in alive:
                    del store[track_id]
        return elbows

    def _match(self, arms, tracked_hands, aspect):
        """{track_id: (x, y) del codo de YOLO} por asignación voraz."""
        candidates = []
        for track_id, _label, _score, lms in tracked_hands:
            wrist = _scene(lms[0], aspect)[:2]
            knuckle = _scene(lms[9], aspect)[:2]
            palm = float(np.linalg.norm(_scene(lms[9], aspect) - _scene(lms[0], aspect)))
            forearm_len = FOREARM_TO_PALM_RATIO * palm
            max_wrist_dist = max(MIN_WRIST_MATCH_DIST, WRIST_MATCH_PALMS * palm)
            for arm_idx, arm in enumerate(arms):
                elbow = np.array([arm.elbow[0], arm.elbow[1] * aspect])
                if arm.wrist is not None:
                    yw = np.array([arm.wrist[0], arm.wrist[1] * aspect])
                    d = float(np.linalg.norm(yw - wrist))
                    if d <= max_wrist_dist:
                        candidates.append((d, track_id, arm_idx))
                    continue
                # Sin muñeca de YOLO: codo a distancia plausible y del lado
                # opuesto a los dedos (con margen: la muñeca se dobla).
                to_elbow = elbow - wrist
                d = float(np.linalg.norm(to_elbow))
                palm_dir = wrist - knuckle
                cos = float(np.dot(to_elbow, palm_dir) /
                            (d * np.linalg.norm(palm_dir) + 1e-9))
                if d <= 1.3 * forearm_len and cos >= -0.3:
                    # Penalización: se prefiere un emparejamiento por muñeca.
                    candidates.append((1.0 + d, track_id, arm_idx))
        candidates.sort(key=lambda c: c[0])

        matches, used_arms = {}, set()
        for _cost, track_id, arm_idx in candidates:
            if track_id in matches or arm_idx in used_arms:
                continue
            matches[track_id] = arms[arm_idx].elbow
            used_arms.add(arm_idx)
        return matches

    def _smooth(self, track_id, point):
        prev = self._smoothed.get(track_id)
        if prev is not None:
            a = ELBOW_SMOOTHING
            point = a * point + (1 - a) * prev
        self._smoothed[track_id] = point
        return point


def estimate_elbow_z(hand_landmarks, ex, ey, aspect):
    """
    z del codo relativa a la muñeca (ver docstring del módulo). Todo se
    mide en la escala del ancho del frame: x tal cual, y * aspect, z tal
    cual (MediaPipe ya da z aproximadamente en la escala de x).
    """
    w, m = hand_landmarks[0], hand_landmarks[9]
    palm = math.sqrt((m.x - w.x) ** 2 + ((m.y - w.y) * aspect) ** 2
                     + (m.z - w.z) ** 2)
    forearm_len = FOREARM_TO_PALM_RATIO * palm
    len_2d = math.hypot(ex - w.x, (ey - w.y) * aspect)
    dz = math.sqrt(max(forearm_len ** 2 - len_2d ** 2, 0.0))
    return w.z + dz  # + = más lejos de la cámara (convención de MediaPipe)


def estimate_elbow_from_palm(hand_landmarks, aspect):
    """
    Codo estimado (paso 4): prolonga en 3D el eje nudillo del medio ->
    muñeca un largo de antebrazo. Supone la muñeca recta; con la muñeca
    doblada el antebrazo estimado sale torcido. Devuelve (X, Y, Z) en
    escala de escena.
    """
    wrist = _scene(hand_landmarks[0], aspect)
    knuckle = _scene(hand_landmarks[9], aspect)
    axis = wrist - knuckle
    palm = float(np.linalg.norm(axis))
    if palm < 1e-6:
        return wrist
    return wrist + axis / palm * FOREARM_TO_PALM_RATIO * palm
