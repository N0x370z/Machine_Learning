"""
Exporta una captura (CSV de HandMotion3D) a un Excel listo para redactar
un artículo, en uno de dos formatos (desde la versión 19-A, 2026-10-19):

  ingenieria  Estilo IEEE: unidades del SI (m/s), hoja de PARÁMETROS con
              símbolos, hoja de ECUACIONES numeradas (texto y LaTeX) y
              RESULTADOS como media, RMS, desviación y pico por punto.
  medicina    Estilo de revista médica: hoja de MÉTODOS (con campos por
              completar: ética, participante, instrumento), TABLA 1 de
              características, TABLA 2 de resultados como "media (DE)" y
              "mediana [Q1-Q3]" en cm/s, y NOTAS ESTADÍSTICAS.

Por qué dos formatos: en ingeniería se presenta CÓMO se calcula la
magnitud (ecuaciones numeradas, símbolos, unidades del SI) y el resultado
como error o magnitud con su dispersión; en medicina se presenta el
método de medición y los resultados como estadística descriptiva
(media (DE), mediana [rango intercuartílico]), sin ecuaciones físicas
pero con la definición de las medidas y las limitaciones.

Cómo está armado el libro:
  - La hoja Datos tiene una fila por fotograma y una columna por serie
    (mano x punto x tipo de rapidez), en cm/s tal cual salen del CSV.
  - Los resultados son FÓRMULAS de Excel (AVERAGE, STDEV, MEDIAN,
    QUARTILE...) sobre esas columnas: cualquier número de la tabla se puede
    rastrear a sus datos, y si borras filas de Datos (p. ej. un tramo mal
    detectado) los resultados se recalculan solos. Excel calcula al abrir.
  - Solo se usan funciones clásicas de Excel (STDEV, QUARTILE, FIXED...)
    para que abra igual en Excel, LibreOffice y Google Sheets.

Uso:
    ./venv/bin/python3 exportar_excel.py --formato ingenieria
    ./venv/bin/python3 exportar_excel.py capturas/hand_data_X.csv --formato medicina
    ./venv/bin/python3 exportar_excel.py --formato medicina --todos-los-puntos
Desde captura.py: tecla 'e' (ingeniería) o 'm' (medicina) durante la captura.

Requiere openpyxl (requirements.txt). Los textos de las hojas están en
español, como el resto del repositorio.

Historial de cambios relevantes: ver CHANGELOG.md.
Última actualización: 2026-10-19.
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

import hand_style
import kinematics

FORMATS = ("ingenieria", "medicina")
SHEET_DATA = "Datos"

# Puntos que se exportan por defecto: muñeca, las cinco puntas y el codo.
# Con --todos-los-puntos, los 22.
KEY_POINTS = (0, 4, 8, 12, 16, 20, hand_style.ELBOW_INDEX)
FINGERTIPS = (4, 8, 12, 16, 20)

PLACEHOLDER = "[completar]"


class ExportError(Exception):
    """Error que se le puede mostrar tal cual a la persona que exporta."""


# ------------------------------------------------------------ lectura

def load_capture(csv_path, all_points=False):
    """
    Lee el CSV y lo arma como series. Devuelve un dict con:
      frames: [números de frame] ordenados; times: {frame: t en s}
      series: [(clave, nombre, {frame: cm/s})] con clave (id, mano, punto, tipo)
      meta: resolución, palma, fuentes, etc.
    Salta filas dañadas (p. ej. la última si el programa se cortó).
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise ExportError(f"No existe {csv_path}")
    wanted = None if all_points else set(KEY_POINTS)
    times, values, palms, sizes, sources = {}, {}, Counter(), Counter(), Counter()
    with open(csv_path, newline="") as f:
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
                frame, idx = int(row["frame"]), int(row["landmark_index"])
                t = float(row["timestamp_ms"]) / 1000.0
                hand = (int(row["hand_id"]), row["handedness"])
                speed = float(row["rapidez_cm_s"])
                rel = float(row["rapidez_rel_cm_s"]) if has_rel and row["rapidez_rel_cm_s"] else None
            except (ValueError, KeyError, TypeError):
                continue
            times[frame] = t
            sizes[(row.get("img_w"), row.get("img_h"))] += 1
            if row.get("palma_cm"):
                palms[row["palma_cm"]] += 1
            sources[row.get("fuente", "")] += 1
            if wanted is not None and idx not in wanted:
                continue
            values.setdefault((*hand, idx, "abs"), {})[frame] = speed
            if rel is not None and idx in FINGERTIPS:
                values.setdefault((*hand, idx, "rel"), {})[frame] = rel
    if not times:
        raise ExportError(f"{csv_path.name} no tiene filas válidas.")
    series = []
    for key in sorted(values, key=lambda k: (k[1], k[0], k[2], k[3] != "abs")):
        hid, label, idx, kind = key
        kind_text = "absoluta" if kind == "abs" else "relativa a la muñeca"
        name = f"{label} #{hid} · {hand_style.point_name(idx)} ({kind_text})"
        series.append((key, name, values[key]))
    size = sizes.most_common(1)[0][0] if sizes else (None, None)
    return {
        "path": csv_path,
        "frames": sorted(times),
        "times": times,
        "series": series,
        "meta": {
            "img": size,
            "palm_cm": float(palms.most_common(1)[0][0]) if palms else None,
            "stereo": sources.get("estereo", 0) > 0,
            "n_hands": len({(k[0], k[1]) for k, *_ in series}),
        },
    }


# ------------------------------------------------------------- estilo

def _styles(fmt):
    """Fuente, relleno y bordes de cada formato (todo con openpyxl)."""
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    font_name = "Times New Roman" if fmt == "ingenieria" else "Arial"
    thin, thick = Side(style="thin"), Side(style="medium")
    return {
        "font": Font(name=font_name, size=10),
        "bold": Font(name=font_name, size=10, bold=True),
        "caption": Font(name=font_name, size=10, bold=(fmt == "medicina"),
                        italic=(fmt == "ingenieria")),
        "title": Font(name=font_name, size=13, bold=True),
        "note": Font(name=font_name, size=9, italic=True, color="555555"),
        "todo": PatternFill("solid", fgColor="FFF2CC"),
        "head_border": Border(top=thick, bottom=thin),
        "last_border": Border(bottom=thick),
        "wrap": Alignment(wrap_text=True, vertical="top"),
        "center": Alignment(horizontal="center", vertical="center", wrap_text=True),
    }


def _put(ws, cell, value, style, font="font", fill=None, align=None, border=None, fmt=None):
    """Escribe un valor con el estilo indicado."""
    c = ws[cell]
    c.value = value
    c.font = style[font]
    if fill:
        c.fill = style[fill]
    if align:
        c.alignment = style[align]
    if border:
        c.border = style[border]
    if fmt:
        c.number_format = fmt
    return c


def _table(ws, top, headers, rows, style, widths=None, number_formats=None):
    """
    Tabla de tres líneas (borde arriba, bajo el encabezado y al final,
    sin líneas verticales), el estilo habitual de IEEE y de las revistas
    médicas. rows: lista de listas; un str que empieza con "=" es fórmula.
    Devuelve la fila siguiente a la tabla.
    """
    from openpyxl.utils import get_column_letter
    for j, h in enumerate(headers, 1):
        c = ws.cell(row=top, column=j, value=h)
        c.font, c.alignment, c.border = style["bold"], style["center"], style["head_border"]
    for i, row in enumerate(rows, 1):
        for j, value in enumerate(row, 1):
            c = ws.cell(row=top + i, column=j, value=value)
            c.font, c.alignment = style["font"], style["wrap"]
            if number_formats and number_formats.get(j):
                c.number_format = number_formats[j]
            if value == PLACEHOLDER:
                c.fill = style["todo"]
            if i == len(rows):
                c.border = style["last_border"]
    if widths:
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(j)].width = w
    return top + len(rows) + 2


# -------------------------------------------------------------- datos

def _write_data(wb, cap, style):
    """
    Hoja Datos: una fila por fotograma y una columna por serie. Devuelve
    {nombre de serie: rango "Datos!$C$2:$C$N"} para las fórmulas.
    """
    from openpyxl.utils import get_column_letter
    ws = wb.create_sheet(SHEET_DATA)
    headers = ["Frame", "t (s)"] + [name for _k, name, _v in cap["series"]]
    for j, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=j, value=h)
        c.font, c.alignment, c.border = style["bold"], style["center"], style["head_border"]
        ws.column_dimensions[get_column_letter(j)].width = 8 if j == 1 else (9 if j == 2 else 24)
    ws.row_dimensions[1].height = 45
    t0 = cap["times"][cap["frames"][0]]
    for i, frame in enumerate(cap["frames"], 2):
        ws.cell(row=i, column=1, value=frame).font = style["font"]
        c = ws.cell(row=i, column=2, value=round(cap["times"][frame] - t0, 4))
        c.font, c.number_format = style["font"], "0.000"
        for j, (_k, _n, vals) in enumerate(cap["series"], 3):
            if frame in vals:
                c = ws.cell(row=i, column=j, value=round(vals[frame], 3))
                c.font, c.number_format = style["font"], "0.00"
    ws.freeze_panes = "C2"
    last = len(cap["frames"]) + 1
    ranges = {name: f"{SHEET_DATA}!${get_column_letter(j)}$2:${get_column_letter(j)}${last}"
              for j, (_k, name, _v) in enumerate(cap["series"], 3)}
    ranges["_frame"] = f"{SHEET_DATA}!$A$2:$A${last}"
    ranges["_t"] = f"{SHEET_DATA}!$B$2:$B${last}"
    return ranges


def _sheet_text(ws, title, paragraphs, style, width=110):
    """Hoja de texto: título y párrafos (los que empiezan con '[' son por completar)."""
    ws.column_dimensions["A"].width = width
    _put(ws, "A1", title, style, "title")
    for i, text in enumerate(paragraphs, 3):
        c = _put(ws, f"A{i}", text, style, "font", align="wrap")
        if PLACEHOLDER in text:
            c.fill = style["todo"]


LIMITATIONS = [
    "La rapidez se estima con visión por computadora (MediaPipe) y una sola cámara: la "
    "profundidad z es una estimación relativa, salvo en capturas con dos cámaras (--estereo). "
    "No se ha validado contra un sistema de referencia (captura de movimiento óptica, "
    "goniómetro, sensores inerciales). Antes de usar estas cifras como medida clínica o de "
    "ingeniería hay que validarlas con una referencia.",
    "Los cm/s se obtienen con la longitud de la palma como regla (palma_cm). Si la palma real "
    "es distinta a la indicada, todas las rapideces se desvían en la misma proporción.",
    "La velocidad se calcula con un filtro One Euro: quita el temblor del detector, pero "
    "atenúa un poco los picos más breves (el filtro tiene un retraso del orden de 0.1 s).",
    "Solo se registran los fotogramas en que se detectó una mano: los huecos no cuentan como "
    "cero. Con la mano perdida más de 0.25 s la velocidad se reinicia.",
    "Cada identificador de mano (#n) es un seguimiento: si la mano sale de cámara y vuelve, "
    "recibe otro número aunque sea la misma.",
]


# ---------------------------------------------------------- ingeniería

def _equations():
    """Ecuaciones de ingeniería: (texto, LaTeX, descripción, unidades)."""
    return [
        ("v⃗ₖ = (p̂ₖ − p̂ₖ₋₁) / (tₖ − tₖ₋₁)",
         r"\vec{v}_k = \frac{\hat{\vec{p}}_k - \hat{\vec{p}}_{k-1}}{t_k - t_{k-1}}",
         "Velocidad de un punto: derivada de su posición filtrada p̂ (x, y, z de la escena, "
         "con la unidad de longitud = ancho del fotograma) entre fotogramas consecutivos.",
         "u/s (anchos de fotograma por segundo)"),
        ("κ = L_palma / ‖p₉ − p₀‖",
         r"\kappa = \frac{L_{palma}}{\lVert \vec{p}_9 - \vec{p}_0 \rVert}",
         "Escala: centímetros por unidad de escena, a partir del largo de la palma "
         "(muñeca, punto 0, a nudillo del medio, punto 9).",
         "cm/u"),
        ("s = κ · ‖v⃗‖",
         r"s = \kappa \,\lVert \vec{v} \rVert",
         "Rapidez absoluta de un punto (columna rapidez_cm_s del CSV).",
         "cm/s"),
        ("s_rel = κ · ‖v⃗ − v⃗_muñeca‖",
         r"s_{rel} = \kappa \,\lVert \vec{v} - \vec{v}_{mu\tilde{n}eca} \rVert",
         "Rapidez relativa a la muñeca: lo que se mueve el punto dentro de la mano.",
         "cm/s"),
        ("α = 1 / (1 + τ/Tₑ),  τ = 1 / (2π f_c),  f_c = f_min + β·|ẋ̂|",
         r"\alpha = \frac{1}{1+\tau/T_e},\; \tau = \frac{1}{2\pi f_c},\; f_c = f_{min} + \beta\,|\hat{\dot{x}}|",
         "Filtro One Euro (Casiez, Roussel y Vogel, CHI 2012) aplicado a cada coordenada antes "
         "de derivar. Tₑ: periodo de muestreo. Parámetros: "
         f"f_min = {kinematics.EURO_MIN_CUTOFF} Hz, β = {kinematics.EURO_BETA}, "
         f"corte de la derivada = {kinematics.EURO_D_CUTOFF} Hz.",
         "Hz; adimensional"),
        ("x̂ₖ = α·xₖ + (1 − α)·x̂ₖ₋₁",
         r"\hat{x}_k = \alpha\, x_k + (1-\alpha)\,\hat{x}_{k-1}",
         "Suavizado exponencial con el α de la ecuación anterior.",
         "—"),
        ("v̄ = (1/N) Σ sₖ",
         r"\bar{v} = \frac{1}{N}\sum_{k=1}^{N} s_k",
         "Media de la rapidez (columna «Media» de Resultados; N = fotogramas con el punto visto).",
         "m/s"),
        ("v_RMS = √( (1/N) Σ sₖ² )",
         r"v_{RMS} = \sqrt{\frac{1}{N}\sum_{k=1}^{N} s_k^2}",
         "Valor cuadrático medio de la rapidez.",
         "m/s"),
        ("σ = √( (1/(N−1)) Σ (sₖ − v̄)² )",
         r"\sigma = \sqrt{\frac{1}{N-1}\sum_{k=1}^{N} (s_k-\bar{v})^2}",
         "Desviación estándar muestral de la rapidez.",
         "m/s"),
        ("v_pico = máx(sₖ)",
         r"v_{pico} = \max_k s_k",
         "Rapidez máxima observada (atenuada por el filtro, ver Limitaciones).",
         "m/s"),
        ("f_s = (N − 1) / (t_N − t₁)",
         r"f_s = \frac{N-1}{t_N - t_1}",
         "Frecuencia de muestreo efectiva. Subestima la real si hubo fotogramas sin mano.",
         "Hz"),
        ("xᵢ ≃ Pᵢ·X,  Pᵢ = Kᵢ[Rᵢ | tᵢ],  i = 1, 2",
         r"\mathbf{x}_i \simeq \mathbf{P}_i \mathbf{X},\; \mathbf{P}_i = \mathbf{K}_i[\mathbf{R}_i \mid \mathbf{t}_i]",
         "Solo en capturas con dos cámaras (fuente = estereo): triangulación lineal (DLT) de "
         "cada punto con las matrices de proyección calibradas (cv2.triangulatePoints).",
         "px; cm"),
    ]


def _build_engineering(wb, cap, ranges, style):
    """Hojas Parámetros, Ecuaciones, Resultados y Limitaciones (ingeniería)."""
    meta = cap["meta"]
    r_frame, r_t = ranges["_frame"], ranges["_t"]

    ws = wb.create_sheet("Parámetros", 0)
    _put(ws, "A1", "Parámetros de la captura", style, "title")
    _put(ws, "A2", "TABLA I. Parámetros experimentales", style, "caption")
    # Encabezado en la fila 3: los datos empiezan en la 4 (N = C4, T = C5).
    rows = [
        ["Fotogramas con mano", "N", f"=COUNT({r_frame})", "—"],
        ["Duración", "T", f"=MAX({r_t})-MIN({r_t})", "s"],
        ["Frecuencia de muestreo efectiva", "f_s", '=IF(C5>0,(C4-1)/C5,"")', "Hz"],
        ["Resolución de imagen", "W × H",
         f"{meta['img'][0]} × {meta['img'][1]}" if meta["img"][0] else PLACEHOLDER, "px"],
        ["Largo de palma", "L_palma", meta["palm_cm"] if meta["palm_cm"] else PLACEHOLDER, "cm"],
        ["Profundidad", "—",
         "dos cámaras (estéreo)" if meta["stereo"] else "una cámara (z de MediaPipe)", "—"],
        ["Manos (seguimientos) y series", "—",
         f"{meta['n_hands']} manos, {len(cap['series'])} series", "—"],
    ]
    _table(ws, 3, ["Parámetro", "Símbolo", "Valor", "Unidad"], rows, style, [34, 12, 28, 10],
           {3: "0.00"})
    _put(ws, "A12", f"Archivo: {cap['path'].name}", style, "note")

    ws = wb.create_sheet("Ecuaciones", 1)
    _put(ws, "A1", "Ecuaciones", style, "title")
    rows = [[f"({i})", txt, tex, desc, unit]
            for i, (txt, tex, desc, unit) in enumerate(_equations(), 1)]
    _table(ws, 3, ["N.º", "Ecuación", "LaTeX (para copiar al artículo)", "Descripción", "Unidades"],
           rows, style, [6, 38, 52, 70, 22])
    _put(ws, f"A{len(rows) + 5}",
         "Los símbolos de rapidez de las ecuaciones (7)-(10) están en m/s: el Excel convierte "
         "los cm/s del CSV dividiendo entre 100.", style, "note")

    ws = wb.create_sheet("Resultados", 2)
    _put(ws, "A1", "TABLA II. Rapidez de los puntos de la mano (SI)", style, "caption")
    rows = []
    for _k, name, _v in cap["series"]:
        rng = ranges[name]
        guard = f'IF(COUNT({rng})=0,"",'
        rows.append([
            name, f"=COUNT({rng})",
            f"={guard}AVERAGE({rng})/100)",
            f"={guard}SQRT(SUMSQ({rng})/COUNT({rng}))/100)",
            f'=IF(COUNT({rng})<2,"",STDEV({rng})/100)',
            f"={guard}MAX({rng})/100)",
        ])
    _table(ws, 2, ["Serie", "N", "Media (m/s)", "RMS (m/s)", "σ (m/s)", "Pico (m/s)"],
           rows, style, [52, 8, 14, 14, 14, 14], {3: "0.000", 4: "0.000", 5: "0.000", 6: "0.000"})
    ws.freeze_panes = "B3"
    _put(ws, f"A{len(rows) + 5}",
         "Cada celda es una fórmula sobre la hoja Datos (cm/s ÷ 100). Ecuaciones (7)-(10).",
         style, "note")
    _limitations_sheet(wb, style)


def _limitations_sheet(wb, style):
    """Hoja Limitaciones (común a los dos formatos)."""
    ws = wb.create_sheet("Limitaciones")
    _sheet_text(ws, "Limitaciones de la medición", [f"{i}. {t}" for i, t in enumerate(LIMITATIONS, 1)],
                style)


# ------------------------------------------------------------- medicina

def _build_medicine(wb, cap, ranges, style):
    """Hojas Métodos, Tabla 1, Tabla 2 y Notas estadísticas (medicina)."""
    meta = cap["meta"]
    r_frame, r_t = ranges["_frame"], ranges["_t"]

    ws = wb.create_sheet("Métodos", 0)
    depth = ("dos cámaras con triangulación estéreo" if meta["stereo"]
             else "una cámara (profundidad estimada por el modelo)")
    _sheet_text(ws, "Métodos (borrador para la sección de Métodos)", [
        "Instrumento. Seguimiento de la mano con MediaPipe HandLandmarker (21 puntos por mano) "
        f"y antebrazo con YOLO pose; {depth}. Cámara y resolución: {PLACEHOLDER}",
        "Variable medida. Rapidez (cm/s) del punto indicado: módulo de su velocidad "
        "tridimensional, calculada a partir de la posición filtrada (filtro One Euro) y el "
        "tiempo de cada fotograma. La escala en cm usa el largo de la palma "
        f"({meta['palm_cm'] if meta['palm_cm'] else PLACEHOLDER} cm, del pliegue de la muñeca "
        "al nudillo del dedo medio). «Relativa a la muñeca» es la rapidez del punto respecto "
        "a la muñeca (movimiento propio del dedo).",
        f"Procedimiento. Posición del participante, distancia a la cámara, iluminación y "
        f"tarea realizada: {PLACEHOLDER}",
        f"Participantes y consentimiento. Criterios de inclusión, aprobación del comité de "
        f"ética y consentimiento informado: {PLACEHOLDER}",
        f"Análisis estadístico. Estadística descriptiva por serie: media (desviación "
        f"estándar), mediana [primer-tercer cuartil] y rango. Ver «Notas estadísticas». {PLACEHOLDER}",
    ], style)

    ws = wb.create_sheet("Tabla 1", 1)
    _put(ws, "A1", "Tabla 1. Características de la captura y del participante", style, "caption")
    rows = [
        ["Participante (código)", PLACEHOLDER],
        ["Edad (años)", PLACEHOLDER],
        ["Sexo", PLACEHOLDER],
        ["Mano dominante", PLACEHOLDER],
        ["Condición clínica / grupo", PLACEHOLDER],
        ["Fotogramas con mano, n", f"=COUNT({r_frame})"],
        ["Duración de la captura, s", f"=MAX({r_t})-MIN({r_t})"],
        ["Manos detectadas (seguimientos), n", meta["n_hands"]],
        ["Resolución de imagen, px",
         f"{meta['img'][0]} × {meta['img'][1]}" if meta["img"][0] else PLACEHOLDER],
    ]
    _table(ws, 2, ["Característica", "Valor"], rows, style, [44, 30], {2: "0.0"})
    _put(ws, f"A{len(rows) + 4}", "Los campos amarillos los completa quien redacta; "
         "el programa no conoce al participante.", style, "note")

    ws = wb.create_sheet("Tabla 2", 2)
    _put(ws, "A1", "Tabla 2. Rapidez de los puntos de la mano (cm/s)", style, "caption")
    rows = []
    for _k, name, _v in cap["series"]:
        r = ranges[name]
        n = f"COUNT({r})"
        rows.append([
            name, f"={n}",
            f'=IF({n}<2,"",FIXED(AVERAGE({r}),1,TRUE)&" ("&FIXED(STDEV({r}),1,TRUE)&")")',
            f'=IF({n}=0,"",FIXED(MEDIAN({r}),1,TRUE)&" ["&FIXED(QUARTILE({r},1),1,TRUE)'
            f'&"-"&FIXED(QUARTILE({r},3),1,TRUE)&"]")',
            f'=IF({n}=0,"",FIXED(MIN({r}),1,TRUE)&"-"&FIXED(MAX({r}),1,TRUE))',
            f'=IF({n}=0,"",AVERAGE({r}))', f'=IF({n}<2,"",STDEV({r}))',
            f'=IF({n}=0,"",MEDIAN({r}))', f'=IF({n}=0,"",QUARTILE({r},1))',
            f'=IF({n}=0,"",QUARTILE({r},3))', f'=IF({n}=0,"",MIN({r}))', f'=IF({n}=0,"",MAX({r}))',
        ])
    _table(ws, 2, ["Serie", "n", "Media (DE)", "Mediana [Q1-Q3]", "Mín-máx",
                   "Media", "DE", "Mediana", "Q1", "Q3", "Mín", "Máx"],
           rows, style, [52, 8, 16, 22, 14] + [9] * 7, {j: "0.00" for j in range(6, 13)})
    ws.freeze_panes = "B3"
    _put(ws, f"A{len(rows) + 5}",
         "Datos como media (desviación estándar) y mediana [primer-tercer cuartil]; n = fotogramas "
         "con el punto visible. Las columnas F-L son los mismos valores en número, para otras "
         "tablas o gráficos.", style, "note")

    ws = wb.create_sheet("Notas estadísticas")
    _sheet_text(ws, "Notas estadísticas y limitaciones", [
        "Definiciones. Media = (1/n)·Σxᵢ. Desviación estándar muestral (DE) = √(Σ(xᵢ−x̄)²/(n−1)). "
        "Mediana y cuartiles con el método inclusivo de Excel (QUARTILE). n = fotogramas en que "
        "se vio el punto.",
        "Fotogramas consecutivos NO son observaciones independientes (la rapidez de un fotograma "
        "se parece a la del anterior). Por eso esta hoja no calcula intervalos de confianza ni "
        "valores p entre fotogramas: serían demasiado optimistas. Para comparar grupos o "
        "condiciones, resume cada participante en UN valor (p. ej. su mediana) y analiza esos "
        "valores.",
        "Si comparas contra un método de referencia, el análisis habitual es Bland-Altman "
        "(sesgo y límites de concordancia al 95 %) y el coeficiente de correlación intraclase, "
        "con una medida por participante o repetición.",
        "Redondeo: rapidez con 1 decimal (cm/s); el Excel guarda más cifras en las columnas numéricas.",
        "", *[f"Limitación {i}. {t}" for i, t in enumerate(LIMITATIONS, 1)],
    ], style)


# ------------------------------------------------------------ principal

def export(csv_path, fmt, out_path=None, all_points=False):
    """
    Genera el Excel de una captura. fmt: "ingenieria" o "medicina".
    Devuelve la ruta del .xlsx. Lanza ExportError con un mensaje claro
    si falta openpyxl o el CSV no sirve.
    """
    if fmt not in FORMATS:
        raise ExportError(f"Formato desconocido {fmt!r}: usa {' o '.join(FORMATS)}.")
    try:
        from openpyxl import Workbook
    except ImportError:
        raise ExportError("Falta openpyxl: ./venv/bin/python3 -m pip install -r requirements.txt")
    cap = load_capture(csv_path, all_points)
    style = _styles(fmt)
    wb = Workbook()
    wb.remove(wb.active)
    ranges = _write_data(wb, cap, style)
    (_build_engineering if fmt == "ingenieria" else _build_medicine)(wb, cap, ranges, style)
    wb.move_sheet(SHEET_DATA, offset=len(wb.sheetnames))   # Datos al final
    wb.calculation.fullCalcOnLoad = True                    # Excel calcula las fórmulas al abrir
    out = Path(out_path) if out_path else cap["path"].with_name(f"{cap['path'].stem}_{fmt}.xlsx")
    wb.save(out)
    return out


def latest_csv(folder=Path(__file__).parent / "capturas"):
    """El CSV más reciente de capturas/ (como plot_csv.py)."""
    files = sorted(folder.glob("hand_data_*.csv"))
    if not files:
        raise ExportError(f"No hay CSV en {folder}. Graba uno con captura.py.")
    return files[-1]


def main():
    """Línea de comandos: exportar_excel.py [csv] --formato ingenieria|medicina."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("csv_path", nargs="?", type=Path, default=None,
                        help="CSV a exportar (default: el último de capturas/).")
    parser.add_argument("--formato", choices=FORMATS, required=True)
    parser.add_argument("--salida", type=Path, default=None,
                        help="Ruta del .xlsx (default: junto al CSV, con el formato en el nombre).")
    parser.add_argument("--todos-los-puntos", action="store_true",
                        help="Una serie por cada uno de los 22 puntos (default: muñeca, "
                             "puntas de los dedos y codo).")
    args = parser.parse_args()
    try:
        out = export(args.csv_path or latest_csv(), args.formato, args.salida,
                     args.todos_los_puntos)
    except ExportError as err:
        raise SystemExit(f"Error: {err}")
    print(f"Excel ({args.formato}) guardado en {out}")


if __name__ == "__main__":
    main()
