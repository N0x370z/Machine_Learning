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
    aunque la mano esté quieta), así que se suaviza con una media
    exponencial (VELOCITY_SMOOTHING).
  - Si un punto no se vio por más de MAX_GAP_S (mano perdida y vuelta a
    encontrar), la velocidad se reinicia en 0 en lugar de calcular un
    salto enorme entre dos posiciones muy separadas en el tiempo.

Unidades:
  - vx, vy, vz: anchos de frame por segundo (u/s). vy positiva = hacia
    abajo en la imagen; vz positiva = alejándose de la cámara.
  - rapidez en cm/s: aproximada. Se convierte suponiendo que la palma
    (muñeca -> nudillo del medio, landmarks 0 -> 9) mide PALM_LENGTH_CM,
    igual que en forearm.py. Sirve para comparar movimientos, no como
    medición de laboratorio.

Última actualización: 2026-09-24. Historial: ver CHANGELOG.md.
"""

import math

# Largo típico de la palma adulta (muñeca -> nudillo del dedo medio).
PALM_LENGTH_CM = 9.5

# Suavizado exponencial de la velocidad (1 = sin suavizar, cada frame
# reemplaza al anterior; valores bajos = más estable pero reacciona tarde).
VELOCITY_SMOOTHING = 0.35

# Hueco máximo entre dos observaciones del mismo punto para seguir
# calculando su velocidad (segundos).
MAX_GAP_S = 0.25

# Los estados de puntos no vistos en este tiempo se borran (segundos).
FORGET_AFTER_S = 1.0


def _norm(v):
    return math.sqrt(sum(c * c for c in v))


def cm_per_unit(points):
    """Centímetros por unidad de escena, según el largo 3D de la palma."""
    palm = _norm([a - b for a, b in zip(points[9], points[0])])
    return PALM_LENGTH_CM / palm if palm > 1e-6 else 0.0


class VelocityEstimator:
    """Guarda la última posición/velocidad de cada (mano, punto)."""

    def __init__(self):
        self._state = {}  # (hand_id, idx) -> (t_s, pos, vel)

    def update(self, hand_id, t_s, points):
        """
        points: {índice: (X, Y, Z)} en unidades de escena (índices 0-20 de
        la mano y 21 del codo, si hay). Devuelve {índice: (vx, vy, vz)}.
        """
        velocities = {}
        for idx, pos in points.items():
            key = (hand_id, idx)
            prev = self._state.get(key)
            vel = (0.0, 0.0, 0.0)
            if prev is not None:
                t0, p0, v0 = prev
                dt = t_s - t0
                if 0 < dt <= MAX_GAP_S:
                    raw = tuple((a - b) / dt for a, b in zip(pos, p0))
                    a = VELOCITY_SMOOTHING
                    vel = tuple(a * r + (1 - a) * o for r, o in zip(raw, v0))
                elif dt == 0:
                    vel = v0
            self._state[key] = (t_s, pos, vel)
            velocities[idx] = vel
        self._forget_old(t_s)
        return velocities

    def _forget_old(self, t_s):
        stale = [k for k, (t0, _p, _v) in self._state.items()
                 if t_s - t0 > FORGET_AFTER_S]
        for k in stale:
            del self._state[k]


def speed_cm_s(velocity, scale_cm_per_unit):
    """Rapidez (módulo de la velocidad) en cm/s aproximados."""
    return _norm(velocity) * scale_cm_per_unit
