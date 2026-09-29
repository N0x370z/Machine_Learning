"""
Velocidad de cada punto de la mano (y del codo) a partir de su posición
3D (x, y, z) y del tiempo real de cada fotograma.

Cómo se calcula (para cada punto, en cada frame):
    v = (posición_actual - posición_anterior) / (t_actual - t_anterior)
  - La posición es la de la escena 3D (ver viewer3d.py): X = x,
    Y = y * alto/ancho, Z = z. Las tres en la misma escala (fracción del
    ancho del frame), así la velocidad no se deforma según la dirección.
  - El tiempo sale del timestamp de cada fotograma, no del número de
    frame: los FPS reales varían (YOLO, luz, carga de la máquina), así que
    suponer "1 frame = 1/30 s" daría velocidades falsas cuando el bucle se
    frena. Se usan juntas las dos cosas: posición x, y, z y el tiempo de
    los fotogramas.
  - La derivada cuadro a cuadro es muy ruidosa (MediaPipe tiembla un poco
    aunque la mano esté quieta). Desde la 28-C se filtra con un filtro
    One Euro (Casiez, Roussel y Vogel, CHI 2012), ver OneEuroFilter:
    filtra fuerte cuando el punto va lento (quita el temblor) y casi nada
    cuando va rápido (no se atrasa). La velocidad es la derivada de la
    posición filtrada. Antes se usaba una media exponencial fija
    (VELOCITY_SMOOTHING = 0.35), que tenía que elegir entre temblar o
    atrasarse. Comparación con datos simulados (30 FPS, temblor de 0.8 px
    en x/y): con la mano quieta la rapidez de ruido baja de 2.3 a 0.8 cm/s
    de media (p95: 4.6 -> 1.9), al arrancar a 40 cm/s llega al 90 % en
    ~95 ms en vez de ~190 ms, y al frenar vuelve a cero en ~80 ms en vez
    de ~150 ms. Lo que se paga: en movimiento constante la rapidez oscila
    un poco más (desvío 2.0 cm/s en vez de 0.9).
  - Solo se filtra para calcular la velocidad: las posiciones que se
    dibujan y se guardan en el CSV siguen siendo las de MediaPipe.
  - Si un punto no se vio por más de MAX_GAP_S (mano perdida y vuelta a
    encontrar), la velocidad se reinicia en 0 en lugar de calcular un
    salto enorme entre dos posiciones muy separadas en el tiempo.

Velocidad de cada dedo (finger_speeds, desde la versión 24-D):
  La velocidad de un dedo es la de su PUNTA (landmarks 4, 8, 12, 16, 20):
  es el punto que más se mueve y el que describe lo que "hace" el dedo.
  Se da de dos formas:
  - absoluta: rapidez de la punta tal cual (incluye el movimiento de
    toda la mano; si mueves el brazo, todos los dedos "van rápido").
  - relativa a la muñeca: rapidez de (v_punta - v_muñeca), o sea, solo
    lo que el dedo se mueve respecto a la mano (doblarlo, estirarlo,
    tocar algo). Con la mano quieta y un dedo moviéndose, solo ese dedo
    sube.

Unidades:
  - vx, vy, vz: anchos de frame por segundo (u/s). vy positiva = hacia
    abajo en la imagen; vz positiva = alejándose de la cámara.
  - rapidez en cm/s: aproximada. Se convierte suponiendo que la palma
    (muñeca -> nudillo del medio, landmarks 0 -> 9) mide PALM_LENGTH_CM
    (9.5 cm), o lo que se indique con --palma-cm (desde la 28-B). Con
    una sola cámara sirve para comparar movimientos, no como medición de
    laboratorio; con dos cámaras (--estereo, 28-D) la escala se mide.

Última actualización: 2026-09-28. Historial: ver CHANGELOG.md.
"""

import argparse
import math

import hand_style

# Largo típico de la palma adulta (muñeca -> nudillo del dedo medio). Es
# el valor por defecto: desde la 28-B se puede poner el de cada persona
# con --palma-cm (captura.py y plot_csv.py), y con dos cámaras (--estereo,
# ver estereo.py) se mide solo.
PALM_LENGTH_CM = 9.5

# Rango aceptado para --palma-cm. Fuera de esto casi seguro es un error
# de medición o de unidades (p. ej. milímetros en vez de centímetros).
PALM_CM_RANGE = (5.0, 15.0)

# Filtro One Euro (desde la 28-C, reemplaza a VELOCITY_SMOOTHING = 0.35).
# Las posiciones están en unidades de escena (1 = ancho del frame, ~1 m
# con la mano a distancia de webcam), así que beta está en esa escala.
#   EURO_MIN_CUTOFF: frecuencia de corte (Hz) con el punto quieto. Más baja
#     = menos temblor, pero más retraso al arrancar.
#   EURO_BETA: cuánto sube el corte con la velocidad. Más alto = menos
#     retraso en movimientos rápidos, pero más ruido en ellos.
#   EURO_D_CUTOFF: corte (Hz) del filtro de la derivada que decide cuánto
#     subir el corte.
# Elegidos comparando con datos simulados (ver el docstring del módulo).
EURO_MIN_CUTOFF = 0.5
EURO_BETA = 10.0
EURO_D_CUTOFF = 2.0

# Hueco máximo entre dos observaciones del mismo punto para seguir
# calculando su velocidad (segundos).
MAX_GAP_S = 0.25

# Los estados de puntos no vistos en este tiempo se borran (segundos).
FORGET_AFTER_S = 1.0


def _norm(v):
    return math.sqrt(sum(c * c for c in v))


def cm_per_unit(points, palm_cm=PALM_LENGTH_CM):
    """
    Centímetros por unidad de escena, según el largo 3D de la palma:
    si la palma mide palm_cm y en la escena ocupa `palm` unidades, cada
    unidad son palm_cm / palm centímetros.
    """
    palm = _norm([a - b for a, b in zip(points[9], points[0])])
    return palm_cm / palm if palm > 1e-6 else 0.0


def palm_cm_arg(text):
    """
    Tipo de argparse para --palma-cm (captura.py y plot_csv.py): un
    número de centímetros dentro de PALM_CM_RANGE.
    """
    value = float(text)
    lo, hi = PALM_CM_RANGE
    if not lo <= value <= hi:
        raise argparse.ArgumentTypeError(
            f"{value} cm está fuera de lo normal ({lo}-{hi} cm). Se mide del "
            "pliegue de la muñeca al nudillo del dedo medio, en centímetros.")
    return value


def hand_scale(hand):
    """
    Centímetros por unidad de escena de una mano de la escena (ver
    viewer3d.hands_to_scene). Usa hand["cm_per_unit"] si ya viene
    calculado (con --palma-cm o medido con dos cámaras); si no, supone
    la palma de PALM_LENGTH_CM.
    """
    return hand.get("cm_per_unit") or cm_per_unit(hand["points"])


def _alpha(dt, cutoff_hz):
    """Peso de un paso de filtro pasa bajos de primer orden con ese corte."""
    tau = 1.0 / (2 * math.pi * cutoff_hz)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter:
    """
    Filtro One Euro para un punto 3D (Casiez et al., 2012). Es un pasa
    bajos cuya frecuencia de corte sube con la velocidad:
        corte = EURO_MIN_CUTOFF + EURO_BETA * |velocidad filtrada|
    Quieto: corte bajo, se quita el temblor. Rápido: corte alto, sigue al
    punto sin retraso. Se usa el mismo corte en los tres ejes (con el
    módulo de la velocidad 3D) para no torcer la dirección del movimiento.

    update() devuelve la velocidad (u/s): la derivada de la posición
    filtrada.
    """

    def __init__(self, t_s, pos, min_cutoff=EURO_MIN_CUTOFF, beta=EURO_BETA,
                 d_cutoff=EURO_D_CUTOFF):
        self.t = t_s
        self.pos = tuple(pos)          # posición filtrada
        self.dpos = (0.0, 0.0, 0.0)    # derivada filtrada (decide el corte)
        self.vel = (0.0, 0.0, 0.0)     # última velocidad devuelta
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff

    def update(self, t_s, pos):
        """Agrega una observación y devuelve (vx, vy, vz)."""
        dt = t_s - self.t
        if dt <= 0:
            return self.vel  # mismo instante: nada nuevo que medir
        raw_d = tuple((p - q) / dt for p, q in zip(pos, self.pos))
        a_d = _alpha(dt, self.d_cutoff)
        self.dpos = tuple(q + a_d * (r - q) for r, q in zip(raw_d, self.dpos))
        cutoff = self.min_cutoff + self.beta * _norm(self.dpos)
        a = _alpha(dt, cutoff)
        new = tuple(q + a * (p - q) for p, q in zip(pos, self.pos))
        self.vel = tuple((n - q) / dt for n, q in zip(new, self.pos))
        self.pos, self.t = new, t_s
        return self.vel


class VelocityEstimator:
    """Un OneEuroFilter por cada (mano, punto)."""

    def __init__(self):
        self._filters = {}  # (hand_id, idx) -> OneEuroFilter

    def update(self, hand_id, t_s, points):
        """
        points: {índice: (X, Y, Z)} en unidades de escena (índices 0-20 de
        la mano y 21 del codo, si hay). Devuelve {índice: (vx, vy, vz)}.
        Un punto nuevo, o que no se vio por más de MAX_GAP_S, arranca con
        velocidad 0 en lugar de calcular un salto enorme.
        """
        velocities = {}
        for idx, pos in points.items():
            key = (hand_id, idx)
            filt = self._filters.get(key)
            if filt is None or t_s - filt.t > MAX_GAP_S:
                self._filters[key] = OneEuroFilter(t_s, pos)
                velocities[idx] = (0.0, 0.0, 0.0)
            else:
                velocities[idx] = filt.update(t_s, pos)
        self._forget_old(t_s)
        return velocities

    def _forget_old(self, t_s):
        """
        Borra los puntos que no se ven hace más de FORGET_AFTER_S, para que
        el estado no crezca con manos que ya salieron de cámara.
        """
        stale = [k for k, f in self._filters.items() if t_s - f.t > FORGET_AFTER_S]
        for k in stale:
            del self._filters[k]


def speed_cm_s(velocity, scale_cm_per_unit):
    """Rapidez (módulo de la velocidad) en cm/s aproximados."""
    return _norm(velocity) * scale_cm_per_unit


def finger_speeds(points, velocities, scale=None):
    """
    Rapidez de cada dedo en cm/s, usando su punta (ver docstring).

    points: los 21 puntos de la mano (X, Y, Z); velocities: {índice:
    (vx, vy, vz)} de VelocityEstimator.update; scale: cm por unidad de
    escena (hand_scale); si es None se calcula con la palma de
    PALM_LENGTH_CM. Devuelve {dedo: (absoluta, relativa_a_la_muñeca)} con
    dedo = "thumb", "index", "middle", "ring", "pinky" (nombres en
    español en hand_style.FINGER_NAMES).
    """
    if scale is None:
        scale = cm_per_unit(points)
    wrist = velocities.get(0, (0.0, 0.0, 0.0))
    speeds = {}
    for tip, finger in hand_style.FINGERTIPS.items():
        v = velocities.get(tip, (0.0, 0.0, 0.0))
        rel = tuple(a - b for a, b in zip(v, wrist))
        speeds[finger] = (speed_cm_s(v, scale), speed_cm_s(rel, scale))
    return speeds


def relative_speed_cm_s(velocity, wrist_velocity, scale_cm_per_unit):
    """Rapidez de un punto respecto a la muñeca, en cm/s aproximados."""
    rel = tuple(a - b for a, b in zip(velocity, wrist_velocity))
    return speed_cm_s(rel, scale_cm_per_unit)
