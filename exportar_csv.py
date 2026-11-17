"""
Exporta una captura (CSV de HandMotion3D) a DOS CSV de resultados para
artículos científicos, uno con el formato de ingeniería y otro con el de
medicina (desde la versión 17-B, 2026-11-17; reemplaza a
exportar_excel.py de la 19-A).

  <captura>_ingenieria.csv   Unidades del SI (m/s): N, T, f_s, media, RMS,
                             σ y pico de la rapidez de cada serie.
  <captura>_medicina.csv     cm/s, estadística descriptiva: n, media (DE),
                             mediana [Q1-Q3], mín-máx, más una columna
                             «participante» para juntar sesiones.

Los dos van en la carpeta articulos/ junto a la captura
(capturas/articulos/), así plot_csv.py no los confunde con capturas.

Formato de los dos archivos (pensado para R, Python/pandas, SPSS o Excel):
  - Una fila por SERIE: mano x punto x tipo de rapidez (absoluta, o
    relativa a la muñeca en las puntas de los dedos). Por defecto: muñeca,
    las cinco puntas y el codo; con --todos-los-puntos, los 22 puntos.
  - Separador coma, punto decimal, UTF-8, primera fila = nombres de
    columna en ASCII con la unidad al final (media_m_s, de_cm_s...).
  - Los números ya vienen calculados (no son fórmulas) y una celda vacía
    significa "no se puede calcular" (p. ej. la DE con n < 2).
El significado de cada columna está en el README (sección "Exportar
para artículos") y en INGENIERIA_COLUMNS / MEDICINA_COLUMNS.

Por qué así y no un Excel (17-B): se pidió que solo se generen CSV. Un CSV
lo abre cualquier programa de estadística sin conversión, se puede
versionar y comparar, y no depende de openpyxl ni de que Excel recalcule
fórmulas al abrir.

Estadística (igual que la de la 19-A):
  - DE y σ son muestrales (n - 1). Cuartiles con el método inclusivo
    (el de QUARTILE / QUARTILE.INC de Excel y numpy.percentile por defecto).
  - NO se calculan intervalos de confianza ni valores p: los fotogramas
    consecutivos no son independientes. Para comparar personas o
    condiciones, resume cada participante en un valor (ver README).

Uso:
    ./venv/bin/python3 exportar_csv.py                                  # el último CSV de capturas/
    ./venv/bin/python3 exportar_csv.py capturas/hand_data_X.csv --participante P01
    ./venv/bin/python3 exportar_csv.py --formato medicina --todos-los-puntos
El participante sale de --participante o, si no se da, del .json de la
sesión (captura.py --participante, desde la 17-D).
Desde captura.py: tecla 'e' (los dos, con lo grabado hasta ese momento).

Historial de cambios relevantes: ver CHANGELOG.md.
Última actualización: 2026-11-17.
"""

import argparse
import csv
import math
from collections import Counter
from pathlib import Path

import numpy as np

import hand_style
import sesion

FORMATS = ("ingenieria", "medicina")
OUT_SUBDIR = "articulos"

# Puntos que se exportan por defecto: muñeca, las cinco puntas y el codo.
KEY_POINTS = (0, 4, 8, 12, 16, 20, hand_style.ELBOW_INDEX)
FINGERTIPS = (4, 8, 12, 16, 20)

# Columnas de cada formato, en orden, con su significado (van al README).
COMMON_COLUMNS = [
    ("archivo", "CSV de la captura de la que salen los datos"),
    ("mano", "Lateralidad real de la mano: Left o Right"),
    ("id_mano", "Número de seguimiento (cambia si la mano sale de cámara y vuelve)"),
    ("punto", "Nombre del punto: Muñeca, Pulgar, Índice, Medio, Anular, Meñique (punta) o Codo"),
    ("indice_punto", "Índice del punto en MediaPipe (0-20; 21 = codo)"),
    ("rapidez", "absoluta, o relativa_muneca (lo que se mueve el dedo dentro de la mano)"),
]
INGENIERIA_COLUMNS = COMMON_COLUMNS + [
    ("N", "Fotogramas en que se vio el punto"),
    ("T_s", "Duración: del primer al último de esos fotogramas, s"),
    ("fs_hz", "Frecuencia de muestreo efectiva (N - 1) / T, Hz"),
    ("media_m_s", "Media de la rapidez, m/s"),
    ("rms_m_s", "Valor cuadrático medio de la rapidez, m/s"),
    ("sigma_m_s", "Desviación estándar muestral (N - 1), m/s"),
    ("pico_m_s", "Rapidez máxima observada, m/s"),
    ("palma_cm", "Largo de palma con el que se pasó a cm (mediana de esa mano), cm"),
    ("profundidad", "monocular (z de MediaPipe), estereo (dos cámaras) o mixta"),
    ("resolucion_px", "Resolución de la imagen, ancho x alto en px"),
]
MEDICINA_COLUMNS = [("participante", "Código del participante (--participante o por completar)")] \
    + COMMON_COLUMNS + [
    ("n", "Fotogramas en que se vio el punto"),
    ("duracion_s", "Duración: del primer al último de esos fotogramas, s"),
    ("media_cm_s", "Media, cm/s"),
    ("de_cm_s", "Desviación estándar muestral (n - 1), cm/s"),
    ("mediana_cm_s", "Mediana, cm/s"),
    ("q1_cm_s", "Primer cuartil (método inclusivo), cm/s"),
    ("q3_cm_s", "Tercer cuartil (método inclusivo), cm/s"),
    ("min_cm_s", "Mínimo, cm/s"),
    ("max_cm_s", "Máximo, cm/s"),
    ("media_de", "Texto listo para la tabla: «media (DE)», 1 decimal"),
    ("mediana_q1_q3", "Texto listo para la tabla: «mediana [Q1-Q3]», 1 decimal"),
    ("palma_cm", "Largo de palma con el que se pasó a cm (mediana de esa mano), cm"),
    ("profundidad", "monocular (z de MediaPipe), estereo (dos cámaras) o mixta"),
]


class ExportError(Exception):
    """Error que se le puede mostrar tal cual a la persona que exporta."""


# ------------------------------------------------------------ lectura

def load_capture(csv_path, all_points=False):
    """
    Lee el CSV de una captura y lo arma por series. Devuelve un dict:
      series: [(clave, [(t_s, cm/s), ...])] con clave (id, mano, punto, tipo),
              ordenadas por mano, id, punto y tipo (absoluta primero);
      hands:  {(id, mano): {"palma_cm": mediana o None, "profundidad": str}};
      img:    "ancho x alto" más frecuente, o "".
    Salta filas dañadas (p. ej. la última si el programa se cortó).
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise ExportError(f"No existe {csv_path}")
    wanted = None if all_points else set(KEY_POINTS)
    values, palms, sources, sizes = {}, {}, {}, Counter()
    # errors="replace": en Windows la captura puede quedar en otra codificación;
    # las columnas que se usan aquí son ASCII.
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        missing = {"frame", "timestamp_ms", "hand_id", "handedness",
                   "landmark_index", "rapidez_cm_s"} - set(reader.fieldnames or [])
        if missing:
            raise ExportError(
                f"{csv_path.name} no tiene la(s) columna(s) {sorted(missing)}: es un "
                "CSV de antes de la versión 24-A (sin velocidad). Graba uno nuevo.")
        has_rel = "rapidez_rel_cm_s" in reader.fieldnames
        for row in reader:
            try:
                idx = int(row["landmark_index"])
                t = float(row["timestamp_ms"]) / 1000.0
                hand = (int(row["hand_id"]), row["handedness"])
                speed = float(row["rapidez_cm_s"])
                rel = float(row["rapidez_rel_cm_s"]) if has_rel and row["rapidez_rel_cm_s"] else None
                int(row["frame"])
            except (ValueError, KeyError, TypeError):
                continue
            if not (math.isfinite(t) and math.isfinite(speed)):
                continue
            sizes[f"{row.get('img_w', '')} x {row.get('img_h', '')}"] += 1
            if idx < 21:
                sources.setdefault(hand, set()).add(row.get("fuente", ""))
                if row.get("palma_cm"):
                    try:
                        palms.setdefault(hand, []).append(float(row["palma_cm"]))
                    except ValueError:
                        pass
            if wanted is not None and idx not in wanted:
                continue
            values.setdefault((*hand, idx, "absoluta"), []).append((t, speed))
            if rel is not None and idx in FINGERTIPS:
                values.setdefault((*hand, idx, "relativa_muneca"), []).append((t, rel))
    if not values:
        raise ExportError(f"{csv_path.name} no tiene filas válidas.")
    hands = {}
    for hand in {(k[0], k[1]) for k in values}:
        src = sources.get(hand, set())
        depth = ("estereo" if src == {"estereo"} else
                 "mixta" if "estereo" in src else "monocular")
        hands[hand] = {
            "palma_cm": float(np.median(palms[hand])) if palms.get(hand) else None,
            "profundidad": depth,
        }
    order = sorted(values, key=lambda k: (k[1], k[0], k[2], k[3] != "absoluta"))
    img = sizes.most_common(1)[0][0] if sizes else ""
    return {"path": csv_path, "series": [(k, values[k]) for k in order], "hands": hands,
            "img": "" if img.strip() == "x" else img}


# --------------------------------------------------------- estadística

def describe(samples):
    """
    Estadística de una serie [(t_s, cm/s)]: n, duración, f_s, media, RMS,
    DE (n - 1), mediana, cuartiles inclusivos, mín y máx (cm/s). Lo que no
    se puede calcular (DE con n < 2, f_s con duración 0) queda en None.
    """
    t = np.array([s[0] for s in samples], dtype=float)
    v = np.array([s[1] for s in samples], dtype=float)
    n = len(v)
    duration = float(t.max() - t.min()) if n else 0.0
    q1, med, q3 = np.percentile(v, [25, 50, 75])   # lineal = QUARTILE.INC de Excel
    return {
        "n": n,
        "duracion_s": duration,
        "fs_hz": (n - 1) / duration if duration > 0 else None,
        "media": float(v.mean()),
        "rms": float(np.sqrt(np.mean(v ** 2))),
        "de": float(v.std(ddof=1)) if n >= 2 else None,
        "mediana": float(med), "q1": float(q1), "q3": float(q3),
        "min": float(v.min()), "max": float(v.max()),
    }


def _num(x, decimals):
    """Número redondeado, o "" si no se puede calcular."""
    return "" if x is None else round(x, decimals)


def _common(cap, key):
    """Columnas comunes de una serie (archivo, mano, id, punto...)."""
    hid, label, idx, kind = key
    return [cap["path"].name, label, hid, hand_style.point_name(idx), idx, kind]


def engineering_rows(cap):
    """Filas del CSV de ingeniería (SI: m/s, 4 decimales = 0.1 mm/s)."""
    rows = []
    for key, samples in cap["series"]:
        d, hand = describe(samples), cap["hands"][(key[0], key[1])]
        rows.append(_common(cap, key) + [
            d["n"], _num(d["duracion_s"], 3), _num(d["fs_hz"], 2),
            _num(d["media"] / 100, 4), _num(d["rms"] / 100, 4),
            _num(d["de"] / 100 if d["de"] is not None else None, 4), _num(d["max"] / 100, 4),
            _num(hand["palma_cm"], 2), hand["profundidad"], cap["img"],
        ])
    return rows


def medicine_rows(cap, participant=""):
    """Filas del CSV de medicina (cm/s, 2 decimales; textos con 1 decimal)."""
    rows = []
    for key, samples in cap["series"]:
        d, hand = describe(samples), cap["hands"][(key[0], key[1])]
        media_de = f"{d['media']:.1f} ({d['de']:.1f})" if d["de"] is not None else ""
        rows.append([participant] + _common(cap, key) + [
            d["n"], _num(d["duracion_s"], 3),
            _num(d["media"], 2), _num(d["de"], 2), _num(d["mediana"], 2),
            _num(d["q1"], 2), _num(d["q3"], 2), _num(d["min"], 2), _num(d["max"], 2),
            media_de, f"{d['mediana']:.1f} [{d['q1']:.1f}-{d['q3']:.1f}]",
            _num(hand["palma_cm"], 2), hand["profundidad"],
        ])
    return rows


# ------------------------------------------------------------ principal

def output_paths(csv_path, out_dir=None):
    """{formato: ruta} de los CSV de una captura (por defecto en <carpeta>/articulos/)."""
    csv_path = Path(csv_path)
    out_dir = Path(out_dir) if out_dir else csv_path.parent / OUT_SUBDIR
    return {fmt: out_dir / f"{csv_path.stem}_{fmt}.csv" for fmt in FORMATS}


def export(csv_path, formats=FORMATS, out_dir=None, all_points=False, participant=""):
    """
    Genera los CSV de resultados de una captura. formats: los que se
    quieran de FORMATS. Devuelve {formato: ruta}. Si ya existían (p. ej. al
    exportar dos veces durante la misma captura), se reemplazan. Lanza
    ExportError con un mensaje claro si el CSV no sirve.
    """
    unknown = set(formats) - set(FORMATS)
    if unknown or not formats:
        raise ExportError(f"Formato desconocido {sorted(unknown)}: usa {' o '.join(FORMATS)}.")
    cap = load_capture(csv_path, all_points)
    if not participant:
        # 17-D: el código guardado en el .json de la sesión (captura.py
        # --participante), si lo hay.
        participant = (sesion.read(csv_path) or {}).get("participante", "")
    paths = output_paths(csv_path, out_dir)
    builders = {
        "ingenieria": (INGENIERIA_COLUMNS, lambda: engineering_rows(cap)),
        "medicina": (MEDICINA_COLUMNS, lambda: medicine_rows(cap, participant)),
    }
    written = {}
    for fmt in FORMATS:
        if fmt not in formats:
            continue
        columns, build = builders[fmt]
        path = paths[fmt]
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".csv.tmp")
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([name for name, _desc in columns])
            writer.writerows(build())
        tmp.replace(path)      # nunca queda un CSV a medio escribir
        written[fmt] = path
    return written


def latest_csv(folder=Path(__file__).parent / "capturas"):
    """El CSV de captura más reciente de capturas/ (como plot_csv.py)."""
    files = sorted(folder.glob("hand_data_*.csv"))
    if not files:
        raise ExportError(f"No hay CSV en {folder}. Graba uno con captura.py.")
    return files[-1]


def main():
    """Línea de comandos: exportar_csv.py [csv] [--formato ...] [--participante ...]."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("csv_path", nargs="?", type=Path, default=None,
                        help="CSV de la captura (default: el último de capturas/).")
    parser.add_argument("--formato", choices=FORMATS + ("ambos",), default="ambos",
                        help="Qué CSV generar (default: ambos).")
    parser.add_argument("--participante", default="",
                        help="Código del participante para la columna 'participante' "
                             "(solo medicina; default: el del .json de la sesión, o vacío).")
    parser.add_argument("--salida", type=Path, default=None,
                        help="Carpeta donde guardarlos (default: articulos/ junto a la captura).")
    parser.add_argument("--todos-los-puntos", action="store_true",
                        help="Una serie por cada uno de los 22 puntos (default: muñeca, "
                             "puntas de los dedos y codo).")
    args = parser.parse_args()
    formats = FORMATS if args.formato == "ambos" else (args.formato,)
    try:
        written = export(args.csv_path or latest_csv(), formats, args.salida,
                         args.todos_los_puntos, args.participante)
    except ExportError as err:
        raise SystemExit(f"Error: {err}")
    for fmt, path in written.items():
        print(f"CSV ({fmt}) guardado en {path}")


if __name__ == "__main__":
    main()
