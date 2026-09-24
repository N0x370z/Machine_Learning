"""
Estilo visual compartido para el dibujo de manos: colores por dedo y el
mapeo landmark -> dedo. Lo usan tanto la vista en vivo (Prueba.py, OpenCV
en BGR) como el reproductor de CSV (plot_csv.py, matplotlib en RGB
0-1), para que ambas vistas se vean siempre igual y no se desincronicen
si alguien cambia un color en un solo archivo.

Antes de esta versión, tanto Prueba.py como plot_csv.py coloreaban todo
el esqueleto de una mano con un único color según su lateralidad
(Left/Right). Eso identificaba manos pero no dedos: no se podía saber,
de un vistazo, cuál landmark pertenecía a qué dedo sin contar índices.
Ahora el color primario identifica el dedo (consistente entre ambas
vistas) y la lateralidad se indica aparte (ver Prueba.py/plot_csv.py).

Desde el 2026-09-24 también define el estilo del antebrazo (codo ->
muñeca), detectado con YOLO pose (ver forearm.py).

Última actualización: 2026-09-24
"""

# Nombre de cada dedo, usado como etiqueta junto a la punta (y en la
# leyenda de plot_csv.py). Reemplaza a las iniciales en inglés
# (T/I/M/R/P) y a los índices numéricos que se mostraban antes.
FINGER_NAMES = {
    "thumb": "Pulgar",
    "index": "Índice",
    "middle": "Medio",
    "ring": "Anular",
    "pinky": "Meñique",
}

# Mismos nombres sin acentos ni ñ: las fuentes Hershey de OpenCV
# (cv2.putText) solo soportan ASCII y dibujan "??" en su lugar.
FINGER_NAMES_ASCII = {
    "thumb": "Pulgar",
    "index": "Indice",
    "middle": "Medio",
    "ring": "Anular",
    "pinky": "Menique",
}

# landmark_index -> dedo. El 0 es la muñeca y no pertenece a ningún dedo.
_RANGES = {
    "thumb": range(1, 5),
    "index": range(5, 9),
    "middle": range(9, 13),
    "ring": range(13, 17),
    "pinky": range(17, 21),
}
LANDMARK_FINGER = {0: "wrist"}
for _finger, _idxs in _RANGES.items():
    for _i in _idxs:
        LANDMARK_FINGER[_i] = _finger

# Punta de cada dedo (último landmark de su rango): 4, 8, 12, 16, 20.
FINGERTIPS = {idxs[-1]: finger for finger, idxs in
              ((f, list(r)) for f, r in _RANGES.items())}

# Paleta por dedo en RGB (0-255). Es la paleta categórica de Wong (2011),
# diseñada para seguir siendo distinguible en las formas más comunes de
# daltonismo (protanopía/deuteranopía) y no solo por matiz "semáforo"
# rojo/verde. "palm" son las conexiones muñeca-nudillo que no pertenecen
# a ningún dedo (ver HAND_CONNECTIONS en Prueba.py/plot_csv.py).
FINGER_COLORS_RGB = {
    "thumb":  (230, 159, 0),    # ámbar
    "index":  (86, 180, 233),   # azul cielo
    "middle": (0, 158, 115),    # verde azulado
    "ring":   (204, 121, 167),  # magenta
    "pinky":  (213, 94, 0),     # rojo coral
    "wrist":  (120, 120, 120),  # gris neutro
    "palm":   (120, 120, 120),  # gris neutro
    # Antebrazo (codo -> muñeca, ver forearm.py): azul de la misma
    # paleta de Wong, distinto de los cinco dedos.
    "forearm": (0, 114, 178),   # azul
}

# Índice "virtual" del codo. Los landmarks de MediaPipe van de 0 a 20;
# el codo lo aporta YOLO pose y se guarda en el CSV como landmark 21
# para no cambiar el formato de filas (ver Prueba.py/plot_csv.py).
ELBOW_INDEX = 21
ELBOW_NAME = "Codo"


def finger_of(landmark_index):
    """Dedo ('thumb'..'pinky') al que pertenece un landmark, o 'wrist'."""
    return LANDMARK_FINGER.get(landmark_index, "wrist")


def connection_color_rgb(start_idx, end_idx):
    """
    Color RGB (0-255) de una conexión del esqueleto: el color del dedo si
    ambos extremos son del mismo dedo, o el gris neutro de 'palm' si la
    conexión une la muñeca con un nudillo (estructura de la palma, no un
    dedo en particular).
    """
    f_start = finger_of(start_idx)
    f_end = finger_of(end_idx)
    if f_start == f_end and f_start != "wrist":
        return FINGER_COLORS_RGB[f_start]
    return FINGER_COLORS_RGB["palm"]


def rgb_to_bgr(rgb):
    """Convierte un color RGB (matplotlib/estándar) a BGR (OpenCV)."""
    r, g, b = rgb
    return (b, g, r)
