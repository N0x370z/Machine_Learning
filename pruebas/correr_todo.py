"""
Corre todas las pruebas de pruebas/ y resume el resultado.

Uso (desde la raíz del repositorio):
    ./venv/bin/python3 pruebas/correr_todo.py

Cada prueba corre en su propio proceso (captura_simulada.py reemplaza
funciones de OpenCV y MediaPipe, y así no afecta a las otras). No hace
falta cámara ni pantalla. Tarda ~30 s (la mayor parte, cargar YOLO).
Sale con código 1 si alguna falla.
"""

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS = [
    ("filtro_velocidad.py", "Filtro One Euro vs media exponencial (28-C)"),
    ("estereo_simulado.py", "Calibración y triangulación con dos cámaras (28-D)"),
    ("captura_simulada.py", "captura.py y plot_csv.py de punta a punta (28-B, 28-D, 28-E)"),
]


def main():
    """Corre cada prueba, muestra su salida y un resumen al final."""
    summary = []
    for script, description in TESTS:
        print(f"\n{'=' * 70}\n{script}: {description}\n{'=' * 70}")
        t0 = time.monotonic()
        proc = subprocess.run([sys.executable, str(HERE / script)], cwd=HERE.parent)
        summary.append((script, proc.returncode == 0, time.monotonic() - t0))
    print(f"\n{'=' * 70}\nRESUMEN")
    for script, ok, secs in summary:
        print(f"  {'OK   ' if ok else 'FALLA'} {script} ({secs:.0f} s)")
    sys.exit(0 if all(ok for _s, ok, _t in summary) else 1)


if __name__ == "__main__":
    main()
