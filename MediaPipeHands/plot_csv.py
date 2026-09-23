"""
Grafica los puntos (landmarks) de mano guardados en un CSV exportado por
Prueba.py, reproduciendo el mismo esqueleto (puntos + conexiones) que se
dibuja en vivo sobre el video.

Uso:
    ./venv/bin/python3 plot_csv.py                       # último CSV en capturas/
    ./venv/bin/python3 plot_csv.py capturas/archivo.csv  # CSV específico
    ./venv/bin/python3 plot_csv.py --frame 38            # solo un frame, estático

Historial de cambios relevantes: ver CHANGELOG.md.
Última actualización: 2026-09-23.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.lines import Line2D
from mediapipe.tasks.python import vision

import hand_style

CAPTURAS_DIR = Path(__file__).parent / "capturas"
HAND_CONNECTIONS = vision.HandLandmarksConnections.HAND_CONNECTIONS

# Lateralidad: antes se codificaba solo con color (azul=Left,
# naranja=Right). Ahora el color identifica el DEDO (ver hand_style.py,
# compartido con Prueba.py) y la lateralidad se indica con el estilo de
# línea, para no perder esa distinción.
HAND_LINESTYLE = {
    "Left": (0, (4, 2)),  # punteado
    "Right": "solid",
}
INK = "#0b0b0b"
SURFACE = "#fcfcfb"


def _mpl_color(rgb_255):
    return tuple(c / 255 for c in rgb_255)


def latest_csv():
    files = sorted(CAPTURAS_DIR.glob("hand_data_*.csv"))
    if not files:
        raise FileNotFoundError(f"No hay CSVs en {CAPTURAS_DIR}")
    return files[-1]


def load_frames(csv_path):
    """frame_idx -> {(hand_id, handedness): {landmark_index: (x, y, z)}, ...}"""
    frames = defaultdict(lambda: defaultdict(dict))
    timestamps = {}
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            frame_idx = int(row["frame"])
            # "hand_id" (tracker estable) en CSVs nuevos; "hand_index" (por
            # frame, sin persistencia) en CSVs generados antes del tracker.
            raw_id = row["hand_id"] if "hand_id" in row else row["hand_index"]
            key = (int(raw_id), row["handedness"])
            frames[frame_idx][key][int(row["landmark_index"])] = (
                float(row["x"]), float(row["y"]), float(row["z"]),
            )
            timestamps[frame_idx] = int(row["timestamp_ms"])
    return frames, timestamps


def draw_frame(ax, hands_in_frame):
    ax.clear()
    ax.set_facecolor(SURFACE)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.invert_yaxis()  # y de MediaPipe crece hacia abajo, igual que en la imagen
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    seen_sides = set()
    for (hand_id, label), landmarks in hands_in_frame.items():
        linestyle = HAND_LINESTYLE.get(label, "solid")
        points = [landmarks[i] for i in sorted(landmarks)]
        seen_sides.add(label)

        # Conexiones: color por dedo (gris neutro para las conexiones
        # muñeca-nudillo, que son estructura de la palma, no un dedo).
        for connection in HAND_CONNECTIONS:
            x0, y0, _ = points[connection.start]
            x1, y1, _ = points[connection.end]
            color = _mpl_color(
                hand_style.connection_color_rgb(connection.start, connection.end)
            )
            ax.plot([x0, x1], [y0, y1], color=color, linewidth=2,
                    linestyle=linestyle, zorder=1)

        # Vértices: color por dedo, puntas (4/8/12/16/20) más grandes y
        # con la inicial del dedo; el resto conserva su índice numérico.
        for lm_idx, (x, y, _z) in enumerate(points):
            finger = hand_style.finger_of(lm_idx)
            color = _mpl_color(hand_style.FINGER_COLORS_RGB[finger])
            is_tip = lm_idx in hand_style.FINGERTIPS
            ax.scatter([x], [y], s=70 if is_tip else 36, color=color,
                       edgecolors=SURFACE, linewidths=0.6, zorder=2)
            tag = hand_style.FINGER_NAMES[finger] if is_tip else str(lm_idx)
            ax.annotate(tag, (x, y), xytext=(3, 3),
                        textcoords="offset points",
                        fontsize=6.5 if is_tip else 6,
                        fontweight="bold" if is_tip else "normal",
                        color=INK, zorder=3)

        # Etiqueta de mano (label + hand_id): con varias manos del mismo
        # lado (ej. dos personas mostrando la izquierda) hace falta el id
        # explícito para distinguirlas, igual que en la vista en vivo.
        wx, wy, _ = points[0]
        ax.annotate(f"{label} #{hand_id}", (wx, wy), xytext=(0, -12),
                    textcoords="offset points", fontsize=8, color=INK,
                    ha="center", zorder=3)

    if seen_sides:
        finger_handles = [
            Line2D([0], [0], color=_mpl_color(rgb), lw=2, label=name.capitalize())
            for name, rgb in hand_style.FINGER_COLORS_RGB.items()
            if name not in ("wrist", "palm")
        ]
        side_handles = [
            Line2D([0], [0], color=INK, lw=2, linestyle=HAND_LINESTYLE[side],
                   label=side)
            for side in ("Left", "Right") if side in seen_sides
        ]
        ax.legend(handles=finger_handles + side_handles, loc="upper right",
                  frameon=False, labelcolor=INK, fontsize=7, ncols=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", nargs="?", type=Path, default=None)
    parser.add_argument("--frame", type=int, default=None,
                         help="Grafica solo este número de frame (estático)")
    parser.add_argument("--interval", type=int, default=33,
                         help="Milisegundos entre frames en la animación")
    args = parser.parse_args()

    csv_path = args.csv_path or latest_csv()
    frames, timestamps = load_frames(csv_path)
    frame_indices = sorted(frames)

    fig, ax = plt.subplots(figsize=(6, 6))
    fig.patch.set_facecolor(SURFACE)

    if args.frame is not None:
        if args.frame not in frames:
            raise SystemExit(f"El frame {args.frame} no existe en {csv_path}")
        draw_frame(ax, frames[args.frame])
        ax.set_title(f"{csv_path.name} — frame {args.frame} "
                     f"({timestamps[args.frame]} ms)", color=INK)
        plt.show()
        return

    def update(frame_idx):
        draw_frame(ax, frames[frame_idx])
        ax.set_title(f"{csv_path.name} — frame {frame_idx} "
                     f"({timestamps[frame_idx]} ms)", color=INK)

    anim = animation.FuncAnimation(
        fig, update, frames=frame_indices, interval=args.interval, repeat=True,
    )
    plt.show()


if __name__ == "__main__":
    main()
