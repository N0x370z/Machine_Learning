"""
Grafica los puntos (landmarks) de mano guardados en un CSV exportado por
Prueba.py, reproduciendo el mismo esqueleto (puntos + conexiones) que se
dibuja en vivo sobre el video.

Uso:
    ./venv/bin/python3 plot_csv.py                       # último CSV en capturas/
    ./venv/bin/python3 plot_csv.py capturas/archivo.csv  # CSV específico
    ./venv/bin/python3 plot_csv.py --frame 38            # solo un frame, estático
    ./venv/bin/python3 plot_csv.py --swap-hands          # CSV viejo con Left/Right invertidos
    ./venv/bin/python3 plot_csv.py --3d                  # en 3D (x, y, z), dos POV

Con --3d usa el mismo visor de dos puntos de vista que la captura en vivo
(viewer3d.py, ventana de OpenCV), incluyendo la profundidad z, el
antebrazo (codo, landmark 21) si el CSV lo tiene y las flechas de
velocidad. La velocidad se recalcula al leer, desde x, y, z y el
timestamp de cada fotograma (kinematics.py), así funciona también con
CSVs viejos que no traen las columnas vx/vy/vz.

Teclas en la reproducción 3D (además de las del visor, ver viewer3d.py):
    espacio = pausa / seguir     a / d = frame anterior / siguiente
    v = flechas de velocidad     q o Esc = salir
    f = velocidad de cada dedo absoluta / relativa a la muñeca

Historial de cambios relevantes: ver CHANGELOG.md.
Última actualización: 2026-09-24.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.lines import Line2D
from mediapipe.tasks.python import vision

import cv2

import hand_style
import kinematics
import viewer3d

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


def load_frames(csv_path, swap_hands=False):
    """frame_idx -> {(hand_id, handedness): {landmark_index: (x, y, z)}, ...}

    También devuelve el aspecto (alto/ancho) del frame original, tomado de
    las columnas img_w/img_h (CSVs desde el 2026-09-24). En CSVs más
    viejos no existen y se asume 16:9 (1280x720, la resolución por defecto
    de Prueba.py). El landmark 21, si está, es el codo (ver forearm.py).
    Y devuelve {(frame_idx, hand_id): "yolo"|"estimado"} con el origen de
    cada codo (columna "fuente", desde el 2026-09-24; si falta, "yolo").

    swap_hands invierte Left/Right al leer: sirve para CSVs grabados antes
    del 2026-09-23, cuando Prueba.py exportaba la lateralidad invertida.
    """
    frames = defaultdict(lambda: defaultdict(dict))
    timestamps = {}
    aspect = 720 / 1280
    elbow_sources = {}
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            frame_idx = int(row["frame"])
            # "hand_id" (tracker estable) en CSVs nuevos; "hand_index" (por
            # frame, sin persistencia) en CSVs generados antes del tracker.
            raw_id = row["hand_id"] if "hand_id" in row else row["hand_index"]
            label = row["handedness"]
            if swap_hands:
                label = {"Left": "Right", "Right": "Left"}.get(label, label)
            key = (int(raw_id), label)
            frames[frame_idx][key][int(row["landmark_index"])] = (
                float(row["x"]), float(row["y"]), float(row["z"]),
            )
            timestamps[frame_idx] = int(row["timestamp_ms"])
            if int(row["landmark_index"]) == hand_style.ELBOW_INDEX:
                elbow_sources[(frame_idx, key[0])] = row.get("fuente") or "yolo"
            if row.get("img_w") and row.get("img_h"):
                aspect = int(row["img_h"]) / int(row["img_w"])
    return frames, timestamps, aspect, elbow_sources


def frame_to_scene(hands_in_frame, aspect, frame_idx=None, elbow_sources=None):
    """Manos de un frame del CSV -> formato de escena de viewer3d
    (sin velocidades: las agrega show_3d con kinematics.py)."""
    elbow_sources = elbow_sources or {}
    hands = []
    for (hand_id, label), landmarks in hands_in_frame.items():
        elbow = landmarks.get(hand_style.ELBOW_INDEX)
        hands.append({
            "id": hand_id,
            "label": label,
            "points": [(x, y * aspect, z) for x, y, z in
                       (landmarks[i] for i in range(21))],
            "elbow": (elbow[0], elbow[1] * aspect, elbow[2]) if elbow else None,
            "elbow_source": elbow_sources.get((frame_idx, hand_id), "yolo")
                            if elbow else None,
            "velocities": {},
        })
    return hands


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
        # Solo los 21 de MediaPipe; el codo (21) va aparte, abajo.
        points = [landmarks[i] for i in range(21)]
        seen_sides.add(label)

        # Antebrazo (codo -> muñeca), debajo de la mano como en la vista
        # en vivo. Solo existe en CSVs grabados con YOLO activo.
        elbow = landmarks.get(hand_style.ELBOW_INDEX)
        if elbow is not None:
            fcolor = _mpl_color(hand_style.FINGER_COLORS_RGB["forearm"])
            ax.plot([elbow[0], points[0][0]], [elbow[1], points[0][1]],
                    color=fcolor, linewidth=5, solid_capstyle="round",
                    zorder=0)
            ax.scatter([elbow[0]], [elbow[1]], s=60, color=fcolor, zorder=0)
            ax.annotate(hand_style.ELBOW_NAME, elbow[:2], xytext=(6, 0),
                        textcoords="offset points", fontsize=7,
                        color=fcolor, zorder=3)

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
        # con el nombre del dedo; el resto va sin etiqueta numérica.
        for lm_idx, (x, y, _z) in enumerate(points):
            finger = hand_style.finger_of(lm_idx)
            color = _mpl_color(hand_style.FINGER_COLORS_RGB[finger])
            is_tip = lm_idx in hand_style.FINGERTIPS
            ax.scatter([x], [y], s=70 if is_tip else 36, color=color,
                       edgecolors=SURFACE, linewidths=0.6, zorder=2)
            if is_tip:
                ax.annotate(hand_style.FINGER_NAMES[finger], (x, y),
                            xytext=(4, 4), textcoords="offset points",
                            fontsize=7, fontweight="bold", color=INK,
                            zorder=3)

        # Etiqueta de mano (label + hand_id): con varias manos del mismo
        # lado (ej. dos personas mostrando la izquierda) hace falta el id
        # explícito para distinguirlas, igual que en la vista en vivo.
        wx, wy, _ = points[0]
        ax.annotate(f"{label} #{hand_id}", (wx, wy), xytext=(0, -12),
                    textcoords="offset points", fontsize=8, color=INK,
                    ha="center", zorder=3)

    if seen_sides:
        finger_handles = [
            Line2D([0], [0], color=_mpl_color(hand_style.FINGER_COLORS_RGB[f]),
                   lw=2, label=name)
            for f, name in hand_style.FINGER_NAMES.items()
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
    parser.add_argument("--swap-hands", action="store_true",
                         help="Invierte Left/Right (para CSVs grabados antes "
                              "del 2026-09-23, con la lateralidad invertida)")
    parser.add_argument("--3d", dest="three_d", action="store_true",
                         help="Grafica en 3D (x, y, z) con dos puntos de vista "
                              "(ver viewer3d.py)")
    args = parser.parse_args()

    csv_path = args.csv_path or latest_csv()
    frames, timestamps, aspect, elbow_sources = load_frames(csv_path, args.swap_hands)
    frame_indices = sorted(frames)

    if args.frame is not None and args.frame not in frames:
        raise SystemExit(f"El frame {args.frame} no existe en {csv_path}")

    if args.three_d:
        show_3d(csv_path, frames, timestamps, aspect, elbow_sources,
                frame_indices, args)
        return

    fig, ax = plt.subplots(figsize=(6, 6))
    fig.patch.set_facecolor(SURFACE)

    if args.frame is not None:
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


def show_3d(csv_path, frames, timestamps, aspect, elbow_sources,
            frame_indices, args):
    """
    Reproduce el CSV en el visor de dos POV de OpenCV (viewer3d.py), en
    bucle. Con --frame arranca en pausa en ese frame.

    Las velocidades se calculan una sola vez, recorriendo los frames en
    orden, para que pausar o retroceder no las altere.
    """
    velocity = kinematics.VelocityEstimator()
    scenes = {}
    for frame_idx in frame_indices:
        hands = frame_to_scene(frames[frame_idx], aspect, frame_idx, elbow_sources)
        for hand in hands:
            hand["velocities"] = velocity.update(
                hand["id"], timestamps[frame_idx] / 1000,
                viewer3d.scene_points(hand))
        scenes[frame_idx] = hands

    viewer = viewer3d.DualPOVViewer(aspect=aspect)
    pos = frame_indices.index(args.frame) if args.frame is not None else 0
    paused = args.frame is not None
    show_velocity = True
    relative_fingers = False
    try:
        while True:
            frame_idx = frame_indices[pos]
            state = "  [pausa]" if paused else ""
            viewer.render(scenes[frame_idx],
                          f"{csv_path.name}  frame {frame_idx} "
                          f"({timestamps[frame_idx]} ms){state}", show_velocity,
                          relative_fingers)
            key = cv2.waitKey(args.interval) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord(" "):
                paused = not paused
            elif key == ord("a"):
                paused, pos = True, (pos - 1) % len(frame_indices)
            elif key == ord("d"):
                paused, pos = True, (pos + 1) % len(frame_indices)
            elif key == ord("v"):
                show_velocity = not show_velocity
            elif key == ord("f"):
                relative_fingers = not relative_fingers
            else:
                viewer.handle_key(key)
            if not paused:
                pos = (pos + 1) % len(frame_indices)
            if not viewer.is_open():
                break
    except KeyboardInterrupt:
        pass
    finally:
        viewer.close()
        # En macOS la ventana no desaparece hasta procesar sus eventos.
        for _ in range(10):
            cv2.waitKey(1)


if __name__ == "__main__":
    main()
