"""
Datos de cada sesión de captura (desde la versión 17-D, 2026-11-17).

Junto a cada CSV de captura (capturas/hand_data_<inicio>.csv) queda un
archivo con el mismo nombre y extensión .json que dice CÓMO se obtuvieron
esos datos: participante, de dónde vinieron las imágenes (cámara o video,
con la huella SHA-256 del video), resolución, parámetros (palma, umbrales,
filtro, modelo YOLO), versiones del programa y de las librerías, hora de
inicio y fin, y si la sesión terminó bien.

Para qué: reproducibilidad. Las revistas piden poder decir con qué
versión y con qué parámetros se midió, y con la huella del video otra
persona puede comprobar que reprocesa EXACTAMENTE el mismo archivo
(captura.py --video). Sin esto, esos datos se perdían al cerrar la
terminal.

Cuándo se escribe:
  - al grabar la primera mano: con "estado": "en curso";
  - al terminar: con la hora de fin, los fotogramas y "estado":
    "completa" (o "error" si el programa terminó por un error). Si el
    archivo sigue diciendo "en curso", el proceso murió sin poder cerrar
    (se cortó la luz, se mató el proceso); el CSV tiene lo grabado hasta
    ese momento.
Nada de esto interrumpe una captura: si algo falla al escribirlo, se avisa
en la terminal y se sigue.

Privacidad: el campo participante es un CÓDIGO (P01, S-12...), nunca el
nombre. Los .json de capturas/ no se suben a git (.gitignore).

Historial de cambios relevantes: ver CHANGELOG.md.
Última actualización: 2026-11-17.
"""

import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime
from importlib import metadata
from pathlib import Path

import kinematics

FORMAT = "HandMotion3D sesion v1"
REPO = Path(__file__).resolve().parent
PACKAGES = ("mediapipe", "opencv-contrib-python", "opencv-python", "numpy",
            "ultralytics", "torch")


def now_iso():
    """Hora local con zona horaria, en ISO 8601 (p. ej. 2026-11-17T10:00:00-06:00)."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def file_sha256(path, chunk=1 << 20):
    """Huella SHA-256 de un archivo (leído por partes: sirve para videos grandes)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _git(*args):
    """Salida de un comando git en el repositorio, o None si no hay git."""
    try:
        out = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                             timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def program_version():
    """Versión del CHANGELOG más reciente (p. ej. "17-D"), o None."""
    try:
        text = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r"^## \d{4}-\d{2}-\d{2} \(versión ([0-9]+-[A-Z])", text, re.M)
    return m.group(1) if m else None


def software_info():
    """Versión del programa (CHANGELOG y commit de git) y de Python y las librerías."""
    packages = {}
    for name in PACKAGES:
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    status = _git("status", "--porcelain", "--untracked-files=no")
    return {
        "version": program_version(),
        "commit": _git("rev-parse", "HEAD"),
        # Cambios sin commit en archivos del repositorio: el commit no
        # describe exactamente el código que corrió.
        "cambios_sin_commit": None if status is None else bool(status),
        "python": platform.python_version(),
        "sistema": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "paquetes": packages,
    }


def parameters(args):
    """Los parámetros de captura.py que cambian lo que se mide."""
    return {
        "palma_cm": args.palma_cm,
        "max_manos": args.max_hands,
        "min_deteccion": args.min_detection_confidence,
        "min_presencia": args.min_presence_confidence,
        "min_seguimiento": args.min_tracking_confidence,
        "antebrazo": None if args.sin_antebrazo else f"yolo11{args.yolo_modelo}-pose",
        "antebrazo_solo_yolo": args.antebrazo_solo_yolo,
        "filtro_one_euro": {"min_cutoff_hz": kinematics.EURO_MIN_CUTOFF,
                            "beta": kinematics.EURO_BETA,
                            "d_cutoff_hz": kinematics.EURO_D_CUTOFF},
        "max_hueco_s": kinematics.MAX_GAP_S,
    }


class SessionLog:
    """
    El .json de una sesión (ver el docstring del módulo). start() lo crea
    con "en curso"; finish() lo completa. Los errores al escribir se
    avisan y no se lanzan: nunca deben cortar una captura.
    """

    def __init__(self, csv_path, args, source):
        """csv_path: el CSV de la sesión; args: los de captura.py; source: dict de la fuente."""
        self.path = Path(csv_path).with_suffix(".json")
        self.data = {
            "formato": FORMAT,
            "csv": Path(csv_path).name,
            "participante": getattr(args, "participante", "") or "",
            "notas": getattr(args, "notas", "") or "",
            "estado": "en curso",
            "inicio": now_iso(),
            "fin": None,
            "fuente": source,
            "parametros": parameters(args),
            "unreal": (f"{args.unreal[0]}:{args.unreal[1]}"
                       if getattr(args, "unreal", None) else None),
            "software": software_info(),
            "resultado": None,
        }
        self.started = False

    def _write(self):
        """Escribe el .json de una vez (archivo temporal + renombrar)."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
            tmp.replace(self.path)
        except OSError as err:
            print(f"Aviso: no se pudo guardar {self.path.name}: {err}", file=sys.stderr)

    def start(self):
        """Crea el .json con "estado": "en curso" (al grabar la primera mano)."""
        if not self.started:
            self.started = True
            self._write()

    def finish(self, frames_processed, frames_with_hands, duration_s, reason):
        """Completa el .json al terminar (solo si la sesión llegó a grabar algo)."""
        if not self.started:
            return
        self.data["estado"] = "error" if reason == "error" else "completa"
        self.data["fin"] = now_iso()
        self.data["resultado"] = {
            "motivo_fin": reason,
            "fotogramas_procesados": frames_processed,
            "fotogramas_con_mano": frames_with_hands,
            "duracion_s": round(duration_s, 3),
            "fps_efectivo": (round(frames_processed / duration_s, 2)
                             if duration_s > 0 else None),
        }
        self._write()


def read(csv_path):
    """El .json de una captura como dict, o None si no hay (capturas de antes de la 17-D)."""
    path = Path(csv_path).with_suffix(".json")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
