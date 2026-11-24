"""
Regenera las imágenes de Unreal Engine de la documentación (desde la
23-A, 2026-11-23): docs/unreal_abierta.png, unreal_cerrada.png,
unreal_tres_cuartos.png y unreal_mano.png (las tres juntas).

Son renders REALES de Unreal Engine (no una simulación como
docs/unreal_simulado.png): se abre el proyecto unreal/HandMotionUE sin
ventana (-RenderOffscreen: el motor corre normal pero no crea ventana, así no
interrumpe lo que haya en pantalla), se le manda una captura con unreal_bridge.py
--csv por UDP, igual que en vivo, y Unreal renderiza la mano más abierta
y la más cerrada que recibió. Aquí solo se reducen a la mitad (bordes
suaves) y se juntan.

Uso (desde la raíz del repositorio, con Unreal 5.x instalado):
    venv\\Scripts\\python docs\\imagenes_unreal.py [captura.csv]
Sin CSV usa el más reciente de capturas/.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import panel            # noqa: E402  (find_unreal_editor, UE_PROJECT)
import plot_csv         # noqa: E402
import unreal_bridge    # noqa: E402

PORT = 8020
NAMES = [("unreal_abierta.png", "Mano abierta"), ("unreal_cerrada.png", "Mano cerrada"),
         ("unreal_tres_cuartos.png", "Cerrada, vista de 3/4")]


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else plot_csv.latest_csv()
    editor = panel.find_unreal_editor()
    if editor is None:
        raise SystemExit("No encontré Unreal Engine (Epic Games Launcher).")
    out = Path(tempfile.mkdtemp(prefix="hm_unreal_"))
    env = dict(os.environ, HM_CAPTURA="1", HM_SALIDA=str(out), HM_PUERTO=str(PORT),
               HM_SEGUNDOS="10")
    print(f"Unreal: {editor.parents[3].name} (sin ventana). Captura: {csv_path.name}")
    proc = subprocess.Popen(
        [str(editor), str(panel.UE_PROJECT), "-RenderOffscreen", "-unattended", "-nosplash",
         "-nosound", "-stdout", "-FullStdOutLogOutput"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace")

    ready = threading.Event()
    log_lines = []

    def pump():
        for line in proc.stdout:
            log_lines.append(line.rstrip())
            if "[HandMotion]" in line:
                print("  " + line.split("[HandMotion]", 1)[1].strip())
            if "esperando datos" in line:
                ready.set()
    threading.Thread(target=pump, daemon=True).start()

    t0 = time.monotonic()
    while not ready.wait(1):
        if proc.poll() is not None or time.monotonic() - t0 > 900:
            break
    if not ready.is_set():
        proc.kill()
        print("\n".join(log_lines[-30:]))
        raise SystemExit("Unreal no llegó a escuchar (ver el registro de arriba).")
    unreal_bridge.run_csv(csv_path, ("127.0.0.1", PORT), loop=True, seconds=12)
    proc.wait(600)

    meta_path = out / "unreal_imagenes.json"
    if not meta_path.exists():
        print("\n".join([l for l in log_lines if "Error" in l or "HandMotion" in l][-30:]))
        raise SystemExit("Unreal no generó las imágenes.")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("error"):
        raise SystemExit(f"Unreal: {meta['error']}")
    meta["captura"] = csv_path.name

    docs = REPO / "docs"
    tiles = []
    for name, caption in NAMES:
        img = Image.open(out / name).convert("RGB")
        img = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
        img.save(docs / name, optimize=True)
        tiles.append((img, caption))
        print(f"  docs/{name}")

    # Las tres juntas, con un pie de foto discreto.
    tw, th = 640, 360
    pad, foot = 12, 34
    sheet = Image.new("RGB", (pad + 3 * (tw + pad), pad + th + foot), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("segoeui.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    for i, (img, caption) in enumerate(tiles):
        x = pad + i * (tw + pad)
        sheet.paste(img.resize((tw, th), Image.LANCZOS), (x, pad))
        draw.text((x + 2, pad + th + 9), caption, fill=(170, 170, 170), font=font)
    sheet.save(docs / "unreal_mano.png", optimize=True)
    (docs / "unreal_imagenes.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  docs/unreal_mano.png  ({meta['fotogramas_recibidos']} fotogramas recibidos, "
          f"{meta['motor']})")


if __name__ == "__main__":
    main()
