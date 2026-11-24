"""
Panel de HandMotion3D (desde la versión 23-A, 2026-11-23): una ventana
para lanzar cada parte del proyecto sin recordar comandos ni flags.

Cada tarea (capturar, analizar un video, reproducir un CSV en Unreal,
graficar, exportar, calibrar...) tiene su formulario; abajo se ve el
comando exacto que se va a ejecutar (se puede copiar y usar en la
terminal) y la salida del programa mientras corre.

No reemplaza a nada: los scripts siguen funcionando igual desde la
terminal. El panel solo arma el comando y lo ejecuta con el mismo Python
con el que se abrió (el del venv).

Uso:
    venv\\Scripts\\python panel.py          (Windows)
    ./venv/bin/python3 panel.py            (macOS / Linux)

Historial de cambios relevantes: ver CHANGELOG.md.
Última actualización: 2026-11-24.
"""

import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QProcess, QProcessEnvironment, Qt, QTimer
from PySide6.QtGui import QFont, QFontDatabase, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QSplitter,
    QVBoxLayout, QWidget,
)

REPO = Path(__file__).resolve().parent
CAPTURAS = REPO / "capturas"
UE_PROJECT = REPO / "unreal" / "HandMotionUE" / "HandMotionUE.uproject"
PALMA_DEFAULT = 9.5        # kinematics.PALM_LENGTH_CM (sin importar todo kinematics)

# Líneas internas de MediaPipe / TensorFlow Lite que no le dicen nada al
# usuario (se pueden ver con "Mostrar mensajes internos").
NOISE = re.compile(r"^(W0000|I0000|E0000|INFO: Created TensorFlow|WARNING: All log messages)")


# ------------------------------------------------------------- estilo

PALETTE = {
    "bg": "#232323", "panel": "#2c2c2c", "field": "#1a1a1a", "line": "#3a3a3a",
    "text": "#e4e4e4", "muted": "#8e8e8e", "accent": "#d99a2b", "accent_text": "#1a1a1a",
    "ok": "#7fb069", "err": "#e06c5a",
}

STYLE = """
* { color: %(text)s; font-size: 10pt; }
QMainWindow, QWidget#root { background: %(bg)s; }
QWidget#form { background: %(bg)s; }
QListWidget#nav { background: %(panel)s; border: none; border-right: 1px solid %(line)s;
    padding: 6px 0; outline: 0; }
QListWidget#nav::item { padding: 6px 14px; border: none; }
QListWidget#nav::item:selected { background: #3b3b3b; color: %(text)s;
    border-left: 2px solid %(accent)s; padding-left: 12px; }
QListWidget#nav::item:hover:!selected { background: #333333; }
QLabel#title { font-size: 15pt; font-weight: 600; }
QLabel#desc { color: %(muted)s; }
QLabel#hint { color: %(muted)s; font-size: 9pt; }
QLabel#section { color: %(muted)s; font-size: 8pt; letter-spacing: 1px; }
QLabel#status { color: %(muted)s; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: %(field)s; border: 1px solid %(line)s; border-radius: 3px;
    padding: 4px 6px; selection-background-color: %(accent)s; selection-color: %(accent_text)s; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: #5a5a5a; }
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled { color: #5c5c5c; }
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView { background: %(field)s; border: 1px solid %(line)s;
    selection-background-color: #3b3b3b; }
QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #5a5a5a;
    border-radius: 2px; background: %(field)s; }
QCheckBox::indicator:checked { background: %(accent)s; border-color: %(accent)s; }
QPushButton { background: #3a3a3a; border: 1px solid #474747; border-radius: 3px;
    padding: 5px 14px; }
QPushButton:hover { background: #444444; }
QPushButton:disabled { color: #666666; background: #2e2e2e; border-color: #383838; }
QPushButton#run { background: %(accent)s; color: %(accent_text)s; border: none; font-weight: 600; }
QPushButton#run:hover { background: #e6aa43; }
QPushButton#run:disabled { background: #5a4a2c; color: #2a2a2a; }
QPushButton#flat { background: transparent; border: none; color: %(muted)s; padding: 2px 6px; }
QPushButton#flat:hover { color: %(text)s; }
QLineEdit#cmd { background: #151515; border: 1px solid %(line)s; color: #c8c8c8; }
QPlainTextEdit#console { background: #151515; border: none; border-top: 1px solid %(line)s;
    color: #cfcfcf; padding: 6px; }
QSplitter::handle { background: %(line)s; }
QScrollArea { background: %(bg)s; border: none; }
QScrollBar:vertical { background: %(bg)s; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #474747; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QFrame#rule { color: %(line)s; }
""" % PALETTE


def mono_font(size=9):
    """Cascadia Mono / Consolas / Menlo, la que haya."""
    for name in ("Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono"):
        if name in QFontDatabase.families():
            return QFont(name, size)
    font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    font.setPointSize(size)
    return font


# ------------------------------------------------------------- campos

class Field:
    """Un campo del formulario: su widget y los argumentos que aporta."""

    label = ""
    hint = ""

    def widget(self):
        raise NotImplementedError

    def args(self):
        return []

    def on_change(self, callback):
        """Llama a callback cuando cambia el valor (para el comando)."""


class Check(Field):
    """Casilla. flag_on se pasa si está marcada; flag_off si no."""

    def __init__(self, label, hint="", flag_on=None, flag_off=None, default=False):
        self.label, self.hint = label, hint
        self.flag_on, self.flag_off = flag_on, flag_off
        self.w = QCheckBox()
        self.w.setChecked(default)

    def widget(self):
        return self.w

    def value(self):
        return self.w.isChecked()

    def args(self):
        flag = self.flag_on if self.value() else self.flag_off
        return [flag] if flag else []

    def on_change(self, callback):
        self.w.toggled.connect(lambda _v: callback())


class Number(Field):
    """Número entero o decimal; skip_default: no pasa el flag si no se cambió."""

    def __init__(self, label, flag, default, hint="", minimum=0, maximum=100,
                 decimals=0, step=1, suffix="", skip_default=False):
        self.label, self.hint, self.flag = label, hint, flag
        self.default, self.skip_default = default, skip_default
        if decimals:
            self.w = QDoubleSpinBox()
            self.w.setDecimals(decimals)
        else:
            self.w = QSpinBox()
        self.w.setRange(minimum, maximum)
        self.w.setSingleStep(step)
        self.w.setValue(default)
        if suffix:
            self.w.setSuffix(f" {suffix}")
        self.w.setFixedWidth(120)

    def widget(self):
        return self.w

    def value(self):
        return self.w.value()

    def args(self):
        if not self.w.isEnabled() or (self.skip_default and self.value() == self.default):
            return []
        v = self.value()
        text = f"{v:g}" if isinstance(v, float) else str(v)
        return [self.flag, text] if self.flag else [text]

    def on_change(self, callback):
        self.w.valueChanged.connect(lambda _v: callback())


class Text(Field):
    """Texto libre; vacío = no se pasa."""

    def __init__(self, label, flag, hint="", placeholder="", default=""):
        self.label, self.hint, self.flag = label, hint, flag
        self.w = QLineEdit(default)
        self.w.setPlaceholderText(placeholder)

    def widget(self):
        return self.w

    def args(self):
        text = self.w.text().strip()
        if not text or not self.w.isEnabled():
            return []
        return [self.flag, text] if self.flag else [text]

    def on_change(self, callback):
        self.w.textChanged.connect(lambda _v: callback())


class Choice(Field):
    """Lista de opciones: (texto visible, [argumentos])."""

    def __init__(self, label, options, hint="", default=0):
        self.label, self.hint, self.options = label, hint, options
        self.w = QComboBox()
        for text, _args in options:
            self.w.addItem(text)
        self.w.setCurrentIndex(default)

    def widget(self):
        return self.w

    def args(self):
        return list(self.options[self.w.currentIndex()][1])

    def on_change(self, callback):
        self.w.currentIndexChanged.connect(lambda _v: callback())


def _session_info(csv_path):
    """Resumen de una captura para la lista: fecha, duración, participante."""
    stamp = re.search(r"(\d{8})_(\d{6})", csv_path.name)
    when = (datetime.strptime("".join(stamp.groups()), "%Y%m%d%H%M%S").strftime("%d/%m/%Y %H:%M")
            if stamp else csv_path.name)
    parts = [when]
    meta = csv_path.with_suffix(".json")
    if meta.exists():
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            res = data.get("resultado") or {}
            if res.get("duracion_s") is not None:
                parts.append(f"{res['duracion_s']:.1f} s")
            if res.get("fotogramas_con_mano") is not None:
                parts.append(f"{res['fotogramas_con_mano']} fotogramas")
            if data.get("participante"):
                parts.append(data["participante"])
            if (data.get("fuente") or {}).get("tipo") == "video":
                parts.append("video")
        except (OSError, ValueError):
            pass
    else:
        parts.append(f"{csv_path.stat().st_size / 1e6:.1f} MB")
    return "   ·   ".join(parts)


class CsvPicker(Field):
    """Elige una captura de capturas/ (la más nueva primero) u otro archivo."""

    def __init__(self, label="Captura", hint="", flag=None):
        self.label, self.hint, self.flag = label, hint, flag
        self.box = QWidget()
        row = QHBoxLayout(self.box)
        row.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.setMinimumWidth(380)
        browse = QPushButton("Otro…")
        browse.clicked.connect(self._browse)
        refresh = QPushButton("Actualizar")
        refresh.setObjectName("flat")
        refresh.clicked.connect(self.refresh)
        row.addWidget(self.combo, 1)
        row.addWidget(browse)
        row.addWidget(refresh)
        self.refresh()

    def refresh(self):
        current = self.path()
        self.combo.clear()
        files = sorted(CAPTURAS.glob("hand_data_*.csv"), reverse=True)
        for f in files:
            self.combo.addItem(_session_info(f), str(f))
        if not files:
            self.combo.addItem("No hay capturas en capturas/", "")
        if current:
            i = self.combo.findData(str(current))
            if i >= 0:
                self.combo.setCurrentIndex(i)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self.box, "Elegir CSV", str(CAPTURAS), "CSV (*.csv)")
        if path:
            self.combo.insertItem(0, Path(path).name, path)
            self.combo.setCurrentIndex(0)

    def path(self):
        data = self.combo.currentData() if hasattr(self, "combo") else None
        return Path(data) if data else None

    def widget(self):
        return self.box

    def args(self):
        p = self.path()
        if p is None:
            return []
        rel = os.path.relpath(p, REPO) if p.is_relative_to(REPO) else str(p)
        return [self.flag, rel] if self.flag else [rel]

    def on_change(self, callback):
        self.combo.currentIndexChanged.connect(lambda _v: callback())


class FilePicker(Field):
    """Un archivo cualquiera (p. ej. un video)."""

    def __init__(self, label, flag, filter_text, hint=""):
        self.label, self.hint, self.flag, self.filter = label, hint, flag, filter_text
        self.box = QWidget()
        row = QHBoxLayout(self.box)
        row.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Ningún archivo elegido")
        browse = QPushButton("Elegir…")
        browse.clicked.connect(self._browse)
        row.addWidget(self.edit, 1)
        row.addWidget(browse)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self.box, "Elegir archivo", str(Path.home()), self.filter)
        if path:
            self.edit.setText(path)

    def widget(self):
        return self.box

    def args(self):
        text = self.edit.text().strip()
        return [self.flag, text] if text else []

    def on_change(self, callback):
        self.edit.textChanged.connect(lambda _v: callback())


def ue_style_field():
    """Estilo de las manos en Unreal: no es un flag, se usa al abrir el proyecto."""
    f = Choice("Estilo en Unreal", [("Mano con huesos, aspecto VR", ["vr"]),
                                    ("Mano con huesos, piel translúcida", ["piel"]),
                                    ("Manos de VR simples (elipsoides)", ["vr_simple"]),
                                    ("Esqueleto de colores con piel", ["esqueleto"])],
               hint="Cómo se ven las manos al abrir el proyecto con el botón de abajo "
                    "(si ya está abierto, ciérralo y ábrelo de nuevo).")
    f.style = lambda: f.options[f.w.currentIndex()][1][0]
    f.args = lambda: []
    return f


def antebrazo_field():
    return Choice("Antebrazo", [
        ("YOLO s: equilibrado (recomendado)", []),
        ("YOLO n: más rápido, codo menos estable", ["--yolo-modelo", "n"]),
        ("YOLO m: más preciso, más lento", ["--yolo-modelo", "m"]),
        ("Sin antebrazo (lo más liviano)", ["--sin-antebrazo"]),
    ], hint="El codo se detecta con YOLO pose. Sin tarjeta NVIDIA configurada, YOLO corre "
            "en el procesador: si los FPS bajan, usa n o quítalo.")


def palma_field():
    return Number("Largo de tu palma", "--palma-cm", PALMA_DEFAULT, decimals=1, step=0.1,
                  minimum=4, maximum=15, suffix="cm", skip_default=True,
                  hint="Del pliegue de la muñeca al nudillo del dedo medio. Es la regla "
                       "de los cm/s: si no la mides se suponen 9.5 cm.")


def unreal_fields():
    send = Check("Mandar a Unreal", flag_on=None,
                 hint="Envía la pose por OSC mientras capturas (ver UNREAL.md).")
    dest = Text("Destino", None, placeholder="127.0.0.1:8000",
                hint="Vacío = esta misma computadora, puerto 8000. Otra IP si Unreal "
                     "corre en otra computadora de la red.")
    # Los dos se combinan en "--unreal [destino]" en el extra de la tarea.
    dest.args = lambda: []
    dest.w.setEnabled(False)
    send.w.toggled.connect(dest.w.setEnabled)
    return send, dest


# ------------------------------------------------------------- tareas

class Task:
    """Una pantalla del panel: título, explicación, script y campos."""

    def __init__(self, section, title, desc, script, fields, base_args=(),
                 note="", extra=None):
        self.section, self.title, self.desc = section, title, desc
        self.script, self.fields, self.base_args = script, fields, list(base_args)
        self.note, self.extra = note, extra or (lambda: [])

    def args(self):
        out = list(self.base_args)
        for f in self.fields:
            out += f.args()
        return out + self.extra()


def build_tasks():
    tasks = []

    # Capturar con la cámara
    send, dest = unreal_fields()
    estereo = Check("Dos cámaras", flag_on="--estereo",
                    hint="Mide la profundidad real (hay que calibrar antes, ver Dos cámaras).")
    cam2 = Number("Cámara 2", "--cam2", 1, maximum=9, skip_default=True,
                  hint="Solo con dos cámaras.")
    cam2.w.setEnabled(False)
    estereo.w.toggled.connect(cam2.w.setEnabled)
    fields = [
        Number("Cámara", "--cam", 0, maximum=9, skip_default=True,
               hint="0 es la webcam principal. Prueba 1 o 2 si tienes varias."),
        palma_field(), antebrazo_field(),
        Check("Vista 3D de dos POV", flag_off="--sin-3d", default=True,
              hint="La segunda ventana con la mano en 3D."),
        estereo, cam2,
        send, dest,
        Text("Participante", "--participante", placeholder="P07",
             hint="Código que se guarda en el .json de la sesión."),
        Text("Notas", "--notas", placeholder="tarea, condición…"),
    ]
    tasks.append(Task(
        "Captura", "Capturar con la cámara",
        "Detecta tus manos, el antebrazo y la velocidad de cada dedo, y lo graba en un CSV "
        "dentro de capturas/ mientras capturas.",
        "captura.py", fields,
        note="Para terminar, pulsa q en la ventana de la cámara (o Esc). «Detener» la cierra "
             "en seco; lo grabado hasta ahí ya está en el CSV.",
        extra=lambda s=send, d=dest: (["--unreal"] + ([d.w.text().strip()] if d.w.text().strip() else []))
        if s.value() else []))

    # Analizar un video
    send, dest = unreal_fields()
    tasks.append(Task(
        "Captura", "Analizar un video",
        "Lo mismo que la captura, pero sobre un video grabado (cuadro por cuadro, sin perder "
        "fotogramas aunque el video vaya a 120 FPS).",
        "captura.py", [
            FilePicker("Video", "--video", "Videos (*.mp4 *.mov *.avi *.mkv);;Todos (*.*)"),
            Check("Video espejado", flag_on="--video-espejado",
                  hint="Márcalo si el video ya viene como espejo (cámara frontal del teléfono)."),
            palma_field(), antebrazo_field(),
            Check("Vista 3D de dos POV", flag_off="--sin-3d", default=True),
            send, dest,
            Text("Participante", "--participante", placeholder="P07"),
        ],
        extra=lambda s=send, d=dest: (["--unreal"] + ([d.w.text().strip()] if d.w.text().strip() else []))
        if s.value() else []))

    # Datos
    frame = Number("Fotograma", "--frame", 0, maximum=1_000_000, skip_default=True,
                   hint="0 = animación completa. Otro número = solo ese fotograma.")
    tasks.append(Task(
        "Datos", "Ver una captura",
        "Vuelve a dibujar los puntos de un CSV, sin cámara: en 2D o en la vista 3D de dos POV "
        "con la velocidad recalculada.",
        "plot_csv.py", [
            CsvPicker(),
            Check("Vista 3D", flag_on="--3d", default=True),
            Check("Invertir izquierda/derecha", flag_on="--swap-hands",
                  hint="Para capturas de antes del 23/09/2026 (11:59), que guardaban "
                       "la lateralidad al revés."),
            frame,
            Number("Largo de palma", "--palma-cm", PALMA_DEFAULT, decimals=1, step=0.1, minimum=4,
                   maximum=15, suffix="cm", skip_default=True,
                   hint="Solo si quieres otra palma que la guardada en el CSV."),
        ]))
    tasks.append(Task(
        "Datos", "Exportar para artículos",
        "Resume una captura en dos CSV de resultados: uno de ingeniería (m/s, RMS, pico) y otro "
        "de medicina (cm/s, media (DE), mediana [Q1-Q3]). Van a capturas/articulos/.",
        "exportar_csv.py", [
            CsvPicker(),
            Choice("Formato", [("Los dos", []), ("Ingeniería", ["--formato", "ingenieria"]),
                               ("Medicina", ["--formato", "medicina"])]),
            Text("Participante", "--participante", placeholder="del .json si se deja vacío"),
            Check("Los 22 puntos", flag_on="--todos-los-puntos",
                  hint="Por defecto: muñeca, las cinco puntas y el codo."),
        ]))

    # Unreal
    tasks.append(Task(
        "Unreal Engine", "Reproducir en Unreal",
        "Manda una captura guardada a Unreal como si fuera en vivo, con los mismos tiempos con "
        "los que se grabó. Abre antes el proyecto de Unreal (botón de abajo).",
        "unreal_bridge.py", [
            CsvPicker(flag="--csv"),
            Text("Destino", "--destino", placeholder="127.0.0.1:8000",
                 hint="Vacío = esta misma computadora, puerto 8000."),
            Number("Velocidad", "--velocidad", 1.0, decimals=2, step=0.25, minimum=0.1,
                   maximum=8, suffix="x", skip_default=True),
            Check("En bucle", flag_on="--bucle", default=True,
                  hint="Vuelve a empezar al terminar."),
            Check("Invertir izquierda/derecha", flag_on="--swap-hands",
                  hint="Para capturas de antes del 23/09/2026 (11:59), que guardaban "
                       "la lateralidad al revés."),
            ue_style_field(),
        ], note="UE_BUTTON"))
    tasks.append(Task(
        "Unreal Engine", "Mano de prueba",
        "Una mano sintética que abre y cierra los dedos, para armar o depurar el lado de Unreal "
        "sin cámara ni capturas.",
        "unreal_bridge.py", [
            Text("Destino", None, placeholder="127.0.0.1:8000", default="127.0.0.1:8000"),
            ue_style_field(),
        ], base_args=["--demo"], note="UE_BUTTON"))
    tasks.append(Task(
        "Unreal Engine", "Ver lo que llega",
        "Escucha un puerto y muestra cada mensaje OSC que llega. Sirve para comprobar el envío "
        "sin abrir Unreal (no lo uses con Unreal abierto: los dos quieren el mismo puerto).",
        "unreal_bridge.py", [
            Number("Puerto", "--escuchar", 8000, minimum=1, maximum=65535),
        ]))

    # Dos cámaras
    tasks.append(Task(
        "Dos cámaras", "Imprimir el tablero",
        "Genera el tablero de ajedrez para calibrar (calibracion/tablero.png). Imprímelo a "
        "tamaño real y mide un cuadro con una regla.",
        "estereo.py", [], base_args=["tablero"]))
    tasks.append(Task(
        "Dos cámaras", "Calibrar",
        "Calcula dónde está cada cámara respecto a la otra mostrando el tablero a las dos. Se "
        "hace una vez cada vez que muevas las cámaras.",
        "estereo.py", [
            Number("Lado de un cuadro", "--cuadro-mm", 25.0, decimals=1, step=0.5, minimum=5,
                   maximum=100, suffix="mm", hint="Medido con una regla en el tablero impreso."),
            Number("Cámara 1", "--cam1", 0, maximum=9, skip_default=True),
            Number("Cámara 2", "--cam2", 1, maximum=9, skip_default=True),
        ], base_args=["calibrar"]))

    # Mantenimiento
    tasks.append(Task(
        "Proyecto", "Pruebas",
        "Corre las pruebas sin cámara (filtro de velocidad, dos cámaras, captura de punta a "
        "punta, exportar y Unreal). Tardan menos de un minuto.",
        str(Path("pruebas") / "correr_todo.py"), []))
    return tasks


# ------------------------------------------------------------- Unreal

def find_unreal_editor():
    """UnrealEditor.exe de la instalación del Epic Launcher (la más nueva)."""
    dat = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Epic" / \
        "UnrealEngineLauncher" / "LauncherInstalled.dat"
    try:
        items = json.loads(dat.read_text(encoding="utf-8"))["InstallationList"]
    except (OSError, ValueError, KeyError):
        return None
    engines = sorted({i["InstallLocation"] for i in items if i.get("NamespaceId") == "ue"},
                     reverse=True)
    for root in engines:
        exe = Path(root) / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
        if exe.exists():
            return exe
    return None


# ------------------------------------------------------------- ventana

class Panel(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("HandMotion3D")
        self.resize(1080, 760)
        self.tasks = build_tasks()
        self.proc = None
        self.started = None
        self.show_noise = False

        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Navegación
        self.nav = QListWidget(objectName="nav")
        self.nav.setFixedWidth(220)
        self.pages = []
        section = None
        for task in self.tasks:
            if task.section != section:
                section = task.section
                head = QListWidgetItem(section.upper())
                head.setFlags(Qt.NoItemFlags)
                head.setForeground(Qt.gray)
                f = head.font()
                f.setPointSize(8)
                head.setFont(f)
                self.nav.addItem(head)
            item = QListWidgetItem(task.title)
            item.setData(Qt.UserRole, len(self.pages))
            self.nav.addItem(item)
            self.pages.append(task)
        outer.addWidget(self.nav)

        # Derecha: formulario arriba, consola abajo
        split = QSplitter(Qt.Vertical)
        outer.addWidget(split, 1)

        self.form_host = QWidget(objectName="form")
        self.form_layout = QVBoxLayout(self.form_host)
        self.form_layout.setContentsMargins(28, 22, 28, 16)
        scroll = QScrollArea()
        scroll.setWidget(self.form_host)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        split.addWidget(scroll)

        bottom = QWidget()
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)
        bar = QHBoxLayout()
        bar.setContentsMargins(28, 6, 16, 6)
        self.status = QLabel("Listo", objectName="status")
        bar.addWidget(self.status, 1)
        noise = QCheckBox("Mostrar mensajes internos")
        noise.toggled.connect(lambda v: setattr(self, "show_noise", v))
        bar.addWidget(noise)
        bar.addSpacing(10)
        clear = QPushButton("Limpiar", objectName="flat")
        bar.addWidget(clear)
        bl.addLayout(bar)
        self.console = QPlainTextEdit(objectName="console")
        self.console.setReadOnly(True)
        self.console.setFont(mono_font(9))
        self.console.setMaximumBlockCount(5000)
        clear.clicked.connect(self.console.clear)
        bl.addWidget(self.console, 1)
        split.addWidget(bottom)
        split.setSizes([520, 240])
        split.setChildrenCollapsible(False)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.nav.currentItemChanged.connect(self._select)
        self.nav.setCurrentRow(1)

    # --- formulario

    def _select(self, item, _prev=None):
        if item is None or item.data(Qt.UserRole) is None:
            return
        self.task = self.pages[item.data(Qt.UserRole)]
        lay = self.form_layout
        while lay.count():
            child = lay.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
        # Los widgets de los campos se reutilizan entre visitas: se
        # vuelven a colgar de un contenedor nuevo.
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        title = QLabel(self.task.title, objectName="title")
        desc = QLabel(self.task.desc, objectName="desc")
        desc.setWordWrap(True)
        v.addWidget(title)
        v.addWidget(desc)
        v.addSpacing(14)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(2)
        grid.setColumnStretch(1, 1)
        row = 0
        for f in self.task.fields:
            label = QLabel(f.label)
            grid.addWidget(label, row, 0, Qt.AlignRight | Qt.AlignVCenter)
            w = f.widget()
            if isinstance(w, (QSpinBox, QDoubleSpinBox, QCheckBox)):
                holder = QWidget()
                h = QHBoxLayout(holder)
                h.setContentsMargins(0, 0, 0, 0)
                h.addWidget(w)
                h.addStretch(1)
                w = holder
            grid.addWidget(w, row, 1)
            row += 1
            if f.hint:
                hint = QLabel(f.hint, objectName="hint")
                hint.setWordWrap(True)
                grid.addWidget(hint, row, 1)
                row += 1
            grid.setRowMinimumHeight(row, 8)
            row += 1
            if not getattr(f, "_hooked", False):
                f.on_change(self._update_command)
                f._hooked = True
        if not self.task.fields:
            grid.addWidget(QLabel("Esta tarea no tiene opciones.", objectName="hint"), 0, 1)
        v.addLayout(grid)
        v.addStretch(1)

        if self.task.note and self.task.note != "UE_BUTTON":
            note = QLabel(self.task.note, objectName="hint")
            note.setWordWrap(True)
            v.addWidget(note)
            v.addSpacing(6)

        rule = QFrame(objectName="rule")
        rule.setFrameShape(QFrame.HLine)
        v.addWidget(rule)
        v.addSpacing(6)
        v.addWidget(QLabel("COMANDO", objectName="section"))
        cmd_row = QHBoxLayout()
        self.cmd = QLineEdit(objectName="cmd")
        self.cmd.setReadOnly(True)
        self.cmd.setFont(mono_font(9))
        copy = QPushButton("Copiar", objectName="flat")
        copy.clicked.connect(lambda: QApplication.clipboard().setText(self.cmd.text()))
        cmd_row.addWidget(self.cmd, 1)
        cmd_row.addWidget(copy)
        v.addLayout(cmd_row)
        v.addSpacing(8)

        buttons = QHBoxLayout()
        self.run_btn = QPushButton("Ejecutar", objectName="run")
        self.run_btn.clicked.connect(self._run)
        self.stop_btn = QPushButton("Detener")
        self.stop_btn.clicked.connect(self._stop)
        buttons.addWidget(self.run_btn)
        buttons.addWidget(self.stop_btn)
        if self.task.note == "UE_BUTTON":
            ue = QPushButton("Abrir proyecto de Unreal")
            ue.clicked.connect(self._open_unreal)
            buttons.addSpacing(12)
            buttons.addWidget(ue)
        buttons.addStretch(1)
        v.addLayout(buttons)

        lay.addWidget(page)
        self._update_command()
        self._sync_buttons()

    def _command(self):
        return [sys.executable, self.task.script, *self.task.args()]

    def _update_command(self):
        if not hasattr(self, "cmd"):
            return
        args = self.task.args()
        py = r"venv\Scripts\python" if os.name == "nt" else "./venv/bin/python3"
        shown = " ".join([py, self.task.script] + [
            (f'"{a}"' if (" " in a or not a) else a) if os.name == "nt" else shlex.quote(a)
            for a in args])
        self.cmd.setText(shown)

    # --- procesos

    def _sync_buttons(self):
        running = self.proc is not None
        self.run_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)

    def _print(self, text, color=None):
        cur = self.console.textCursor()
        cur.movePosition(QTextCursor.End)
        if color:
            safe = text.replace("&", "&amp;").replace("<", "&lt;")
            self.console.appendHtml(f'<span style="color:{color}">{safe}</span>')
        else:
            self.console.appendPlainText(text)
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def _run(self):
        cmd = self._command()
        self._print(f"$ {self.cmd.text()}", PALETTE["muted"])
        self.proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("PYTHONUNBUFFERED", "1")
        self.proc.setProcessEnvironment(env)
        self.proc.setWorkingDirectory(str(REPO))
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.finished.connect(self._finished)
        self.proc.errorOccurred.connect(self._error)
        self._partial = ""
        self.proc.start(cmd[0], cmd[1:])
        self.started = time.monotonic()
        self.running_title = self.task.title
        self.timer.start(500)
        self._tick()
        self._sync_buttons()

    def _read(self):
        data = self._partial + bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        lines = re.split(r"\r\n|\n|\r", data)
        self._partial = lines.pop()
        for line in lines:
            if line and (self.show_noise or not NOISE.match(line)):
                color = PALETTE["err"] if ("Traceback" in line or "Error" in line
                                           or "FALLA" in line) else None
                self._print(line, color)

    def _tick(self):
        if self.proc is None:
            return
        s = int(time.monotonic() - self.started)
        self.status.setText(f"En marcha: {self.running_title}   {s // 60:02d}:{s % 60:02d}")

    def _finished(self, code, _status):
        self._read()
        if self._partial:
            self._print(self._partial)
        ok = code == 0
        self._print(f"— terminó {'bien' if ok else f'con código {code}'}",
                    PALETTE["ok"] if ok else PALETTE["err"])
        self.status.setText("Listo" if ok else f"Terminó con código {code}")
        self.proc = None
        self.timer.stop()
        self._sync_buttons()
        for f in self.task.fields:        # puede haber una captura nueva
            if isinstance(f, CsvPicker):
                f.refresh()

    def _error(self, err):
        if err == QProcess.FailedToStart:
            self._print("No se pudo iniciar el programa.", PALETTE["err"])
            self.proc = None
            self.timer.stop()
            self._sync_buttons()

    def _stop(self):
        if self.proc is not None:
            self.proc.kill()

    def _open_unreal(self):
        exe = find_unreal_editor()
        if exe is None:
            self._print("No encontré Unreal Engine instalado desde el Epic Games Launcher.",
                        PALETTE["err"])
            return
        if not UE_PROJECT.exists():
            self._print(f"No existe {UE_PROJECT}", PALETTE["err"])
            return
        style = next((f.style() for f in self.task.fields if hasattr(f, "style")), "vr")
        env = dict(os.environ, HM_ESTILO=style)
        subprocess.Popen([str(exe), str(UE_PROJECT)], cwd=str(UE_PROJECT.parent), env=env)
        self._print(f"Abriendo Unreal ({exe.parents[3].name}) con {UE_PROJECT.name}. "
                    "Tarda unos segundos; la mano aparece cuando empiecen a llegar datos.",
                    PALETTE["muted"])

    def closeEvent(self, event):
        if self.proc is not None:
            self.proc.kill()
            self.proc.waitForFinished(2000)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI" if os.name == "nt" else app.font().family(), 10))
    app.setStyleSheet(STYLE)
    win = Panel()
    if "--captura" in sys.argv:         # para la imagen de la documentación
        out = Path(sys.argv[sys.argv.index("--captura") + 1])
        page = int(sys.argv[sys.argv.index("--pagina") + 1]) if "--pagina" in sys.argv else 0
        win.nav.setCurrentRow([i for i in range(win.nav.count())
                               if win.nav.item(i).data(Qt.UserRole) == page][0])
        win.resize(1080, 760)
        win.setAttribute(Qt.WA_DontShowOnScreen)
        win.show()
        QTimer.singleShot(400, lambda: (win.grab().save(str(out)), app.quit()))
        return app.exec()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
