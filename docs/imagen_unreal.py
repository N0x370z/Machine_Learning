"""
Genera docs/unreal_simulado.png: una imagen SIMULADA de cómo se vería
HandMotion3D conectado con Unreal Engine 5 (versión 17-A, 2026-11-17).

No es una captura de Unreal Engine (no se tiene Unreal a mano, ver
UNREAL.md). Pero los datos de la imagen SÍ son los del programa: la mano
de `unreal_bridge.py --demo` se codifica como el mensaje OSC que recibe
Unreal, se decodifica y el modelo 3D de la imagen se arma SOLO con esos
87 floats (puntos en cm relativos a la muñeca, ejes de Unreal y flexión
en grados). Es decir: si el Blueprint de UNREAL.md lee bien el mensaje,
esta es la pose que tiene que ver en el modelo.

Qué muestra:
  - Cámara: la ventana de captura.py --unreal (mano y aviso del envío).
  - Viewport: la mano reconstruida en los ejes de Unreal (X adelante,
    Y derecha, Z arriba, cm), con la cuadrícula del piso y los ejes.
  - Flexión: los 15 ángulos que llegan (floats [72:87]) por articulación.
  - Blueprint: los nodos de la guía (UNREAL.md, pasos 3 y 4) y el
    registro con los mensajes tal como los muestra --escuchar.

Uso (desde la raíz del repositorio):
    ./venv/bin/python3 docs/imagen_unreal.py            # pose a medio cerrar
    ./venv/bin/python3 docs/imagen_unreal.py --t 0.0    # mano abierta
Historial de cambios relevantes: ver CHANGELOG.md.
"""

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import hand_style  # noqa: E402
import unreal_bridge as ub  # noqa: E402

OUT = Path(__file__).resolve().parent / "unreal_simulado.png"

# Colores de un editor oscuro (genérico, sin marcas).
BG, PANEL, BORDER = "#151515", "#242424", "#3a3a3a"
TEXT, MUTED, ACCENT = "#e6e6e6", "#9a9a9a", "#f2b400"
SKIN = "#d9a982"

CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
               (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16),
               (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]


def rgb(name):
    """Color de un dedo de hand_style en RGB 0-1."""
    return tuple(c / 255 for c in hand_style.FINGER_COLORS_RGB[name])


def bone_color(a, b):
    """Color de un hueso: el del dedo, o gris si es de la palma."""
    fa, fb = hand_style.finger_of(a), hand_style.finger_of(b)
    return rgb(fb) if fa == fb or (fa == "wrist" and b == 1) else rgb("palm")


def received(t):
    """
    Lo que recibe Unreal en el instante t de --demo: (mano de la escena,
    mensajes decodificados, floats de la mano). Pasa por el codificador
    y el decodificador OSC reales.
    """
    hand = ub.demo_hand(t)
    frame_msg = ub.osc_decode(ub.osc_message(ub.ADDR_FRAME, [float(round(t * 30)), 1.0, t]))
    hand_msg = ub.osc_decode(ub.hand_message(hand))
    return hand, [frame_msg, hand_msg], hand_msg[1]


def panel(fig, rect, title):
    """Recuadro de panel del editor con su título; devuelve un eje vacío encima."""
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.01",
                                transform=ax.transAxes, fc=PANEL, ec=BORDER, lw=1))
    ax.text(0.015, 0.975, title, color=TEXT, fontsize=10, fontweight="bold",
            va="top", transform=ax.transAxes)
    return ax


def draw_camera(fig, rect, hand):
    """Ventana de captura.py: la mano en 2D y el aviso de Unreal en el panel."""
    ax = panel(fig, rect, "Cámara — captura.py --unreal")
    img = fig.add_axes([rect[0] + 0.008, rect[1] + 0.012, rect[2] - 0.016, rect[3] - 0.06])
    img.set_facecolor("#2b2f33")
    img.set_xticks([])
    img.set_yticks([])
    for s in img.spines.values():
        s.set_color(BORDER)
    pts = hand["points"]
    for a, b in CONNECTIONS:
        img.plot([pts[a][0], pts[b][0]], [pts[a][1], pts[b][1]], color=bone_color(a, b), lw=3,
                 solid_capstyle="round")
    for i, p in enumerate(pts):
        img.plot(p[0], p[1], "o", ms=5, color="white", mec=rgb(hand_style.finger_of(i)), mew=1.5)
    img.set_xlim(0.30, 0.70)
    img.set_ylim(0.66, 0.40)          # y de la imagen crece hacia abajo
    img.set_aspect("equal")
    hud = [  # como el panel real de captura.py
           "FPS: 30.0   Manos: 1", "Frames grabados: 412",
           "Unreal 127.0.0.1:8000: enviando ([u])"]
    for k, line in enumerate(hud):
        img.text(0.02, 0.97 - k * 0.07, line, color=ACCENT if "Unreal" in line else "white",
                 fontsize=8, family="monospace", va="top", transform=img.transAxes,
                 bbox=dict(fc="black", ec="none", alpha=0.55, pad=1.5))
    img.text(0.98, 0.03, "Right #0", color="white", fontsize=8, ha="right",
             transform=img.transAxes)
    return ax


def unreal_points(floats):
    """Los 21 puntos (cm, ejes de Unreal) reconstruidos SOLO con los floats del mensaje."""
    lo, _hi = ub.FLOAT_LAYOUT["puntos_cm"]
    return [tuple(floats[lo + 3 * i: lo + 3 * i + 3]) for i in range(ub.N_POINTS)]


def draw_viewport(fig, rect, floats):
    """Viewport 3D: la mano en los ejes de Unreal, con piso y ejes."""
    panel(fig, rect, "Viewport — Perspectiva (BP_ManoReceptor, mano derecha)")
    ax = fig.add_axes([rect[0] + 0.005, rect[1] + 0.005, rect[2] - 0.01, rect[3] - 0.045],
                      projection="3d")
    ax.set_facecolor(PANEL)
    ax.xaxis.set_pane_color((0, 0, 0, 0))
    ax.yaxis.set_pane_color((0, 0, 0, 0))
    ax.zaxis.set_pane_color((0, 0, 0, 0))
    ax.grid(False)
    ax.set_axis_off()
    pts = unreal_points(floats)
    # Matplotlib (x, y, z) = Unreal (Y derecha, X adelante, Z arriba).
    P = [(p[1], p[0], p[2]) for p in pts]
    zmin = min(p[2] for p in P) - 3
    # Piso: cuadrícula de 2 cm, como la del editor.
    for g in range(-10, 11, 2):
        ax.plot([g, g], [-10, 10], [zmin] * 2, color="#3c3c3c", lw=0.6)
        ax.plot([-10, 10], [g, g], [zmin] * 2, color="#3c3c3c", lw=0.6)
    # Antebrazo de adorno (el demo no manda codo): sale de la muñeca hacia abajo.
    ax.plot([0, 0], [0, 0], [0, zmin + 0.2], color=SKIN, lw=16, alpha=0.6, solid_capstyle="round")
    palm = [P[i] for i in (0, 1, 5, 9, 13, 17)]
    ax.add_collection3d(Poly3DCollection([palm], fc=SKIN, ec="none", alpha=0.85))
    for a, b in CONNECTIONS:
        xs, ys, zs = zip(P[a], P[b])
        ax.plot(xs, ys, zs, color=SKIN, lw=11, solid_capstyle="round", alpha=0.95)
        ax.plot(xs, ys, zs, color=bone_color(a, b), lw=2.2, solid_capstyle="round")
    for i, p in enumerate(P):
        ax.scatter(*p, s=22, color="white", edgecolors=rgb(hand_style.finger_of(i)),
                   linewidths=1.2, depthshade=False)
    # Gizmo de ejes de Unreal (X rojo, Y verde, Z azul), en una esquina.
    o = (-9, -9, zmin)
    for d, c, lab in (((0, 4, 0), "#e04b4b", "X"), ((4, 0, 0), "#5bc85b", "Y"),
                      ((0, 0, 4), "#4b8be0", "Z")):
        ax.plot([o[0], o[0] + d[0]], [o[1], o[1] + d[1]], [o[2], o[2] + d[2]], color=c, lw=2.5)
        ax.text(o[0] + d[0] * 1.25, o[1] + d[1] * 1.25, o[2] + d[2] * 1.25, lab, color=c,
                fontsize=9, fontweight="bold")
    ax.set_xlim(-9, 9)
    ax.set_ylim(-9, 9)
    ax.set_zlim(zmin, zmin + 18)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=14, azim=-130)
    fig.text(rect[0] + 0.012, rect[1] + 0.015,
             "Pose armada solo con los floats [6:69] del mensaje /handmotion/Right "
             "(cm relativos a la muñeca, ejes de Unreal)", color=MUTED, fontsize=8)


def draw_flexion(fig, rect, floats):
    """Barras de los 15 ángulos de flexión recibidos (floats [72:87])."""
    panel(fig, rect, "Detalles — flexión recibida (grados), floats [72:87]")
    ax = fig.add_axes([rect[0] + 0.075, rect[1] + 0.03, rect[2] - 0.09, rect[3] - 0.08])
    ax.set_facecolor(PANEL)
    lo, hi = ub.FLOAT_LAYOUT["flexion_grados"]
    flex = floats[lo:hi]
    fingers = ["thumb"] * 3 + ["index"] * 3 + ["middle"] * 3 + ["ring"] * 3 + ["pinky"] * 3
    labels = [f"{dedo} {art}" for dedo, art, *_ in ub.JOINTS]
    y = list(range(len(flex)))[::-1]
    ax.barh(y, flex, color=[rgb(f) for f in fingers], height=0.7)
    for yi, v in zip(y, flex):
        ax.text(v + 1.5, yi, f"{v:.0f}°", color=TEXT, va="center", fontsize=7)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7, color=TEXT)
    ax.set_xlim(0, 120)
    ax.tick_params(axis="x", colors=MUTED, labelsize=7)
    for s in ax.spines.values():
        s.set_color(BORDER)


def node(ax, x, y, w, title, rows, color):
    """Un nodo de Blueprint: cabecera de color y filas de pines."""
    h = 0.11 + 0.075 * len(rows)
    ax.add_patch(FancyBboxPatch((x, y - h), w, h, boxstyle="round,pad=0,rounding_size=0.015",
                                fc="#1c1c1c", ec="#555555", lw=1))
    ax.add_patch(FancyBboxPatch((x, y - 0.1), w, 0.1, boxstyle="round,pad=0,rounding_size=0.015",
                                fc=color, ec="none"))
    ax.text(x + 0.01, y - 0.05, title, color="white", fontsize=7.5, fontweight="bold", va="center")
    for k, r in enumerate(rows):
        ax.text(x + 0.012, y - 0.15 - 0.075 * k, r, color=TEXT, fontsize=6.5, va="center")
    return (x + w, y - 0.05), (x, y - 0.05)


def wire(ax, a, b, color="white"):
    """Cable entre dos pines (curva suave, como en el editor)."""
    import numpy as np
    t = np.linspace(0, 1, 30)
    dx = max(0.04, (b[0] - a[0]) * 0.5)
    xs = (1 - t) ** 3 * a[0] + 3 * (1 - t) ** 2 * t * (a[0] + dx) + 3 * (1 - t) * t ** 2 * (b[0] - dx) + t ** 3 * b[0]
    ys = (1 - t) ** 3 * a[1] + 3 * (1 - t) ** 2 * t * a[1] + 3 * (1 - t) * t ** 2 * b[1] + t ** 3 * b[1]
    ax.plot(xs, ys, color=color, lw=1.4)


def draw_blueprint(fig, rect, flex_index_pip):
    """Grafo de Blueprint de la guía (UNREAL.md, pasos 3 y 4)."""
    ax = panel(fig, rect, "Blueprint — BP_ManoReceptor (Event Graph)")
    ax.set_facecolor("#1a1a1a")
    red, blue, green, purple = "#8c2a2a", "#2a4f8c", "#2a7a4a", "#5a3a8c"
    o1, _ = node(ax, 0.02, 0.88, 0.17, "Event BeginPlay", ["Exec ▷"], red)
    o2, i2 = node(ax, 0.23, 0.88, 0.22, "Create OSC Server",
                  ["Receive IP: 0.0.0.0", "Port: 8000", "Start Listening: ✓"], blue)
    o3, i3 = node(ax, 0.49, 0.88, 0.25, "Bind Event to On OSC\nMessage Received",
                  ["Target: OscServer", "Event: AlRecibirOSC"], blue)
    wire(ax, o1, i2)
    wire(ax, o2, i3)
    o4, _ = node(ax, 0.02, 0.42, 0.17, "AlRecibirOSC", ["Message ▷"], red)
    o5, i5 = node(ax, 0.23, 0.42, 0.21, "Get OSC Address",
                  ["== /handmotion/Right", "→ Branch (True)"], green)
    o6, i6 = node(ax, 0.48, 0.42, 0.21, "Get Floats",
                  ["Array[87]", "[76] = flexión índice PIP"], green)
    _o7, i7 = node(ax, 0.73, 0.42, 0.25, "Transform (Modify) Bone",
                   ["Bone: index_02_r", f"Rotation (Pitch): {flex_index_pip:.0f}°",
                    "FInterp To (suavizado)"], purple)
    wire(ax, o4, i5)
    wire(ax, o5, i6)
    wire(ax, o6, i7)
    ax.text(0.78, 0.83, "Nodos según UNREAL.md;\nlos nombres exactos pueden\nvariar entre versiones de UE 5.",
            color=MUTED, fontsize=7, va="top")


def draw_log(fig, rect, msgs):
    """Registro con los mensajes, como los muestra unreal_bridge.py --escuchar."""
    ax = panel(fig, rect, "Output Log — OSC recibido en el puerto 8000")
    (addr_f, args_f), (addr_h, args_h) = msgs
    lo = ub.FLOAT_LAYOUT["flexion_grados"][0]
    lines = [
        f"{addr_f}  fotograma {args_f[0]:.0f}, manos {args_f[1]:.0f}, t = {args_f[2]:.3f} s",
        f"{addr_h}  id {args_h[0]:.0f}, codo {args_h[1]:.0f}, {len(args_h)} floats, palma {args_h[2]:.1f} cm",
        "  muñeca [3:6] = (" + ", ".join(f"{v:.1f}" for v in args_h[3:6]) + ") cm",
        "  punta del índice [30:33] = (" + ", ".join(f"{v:.1f}" for v in args_h[30:33]) + ") cm",
        "  flexión índice MCP/PIP/DIP = " + " / ".join(f"{a:.1f}°" for a in args_h[lo + 3:lo + 6]),
    ]
    for k, line in enumerate(lines):
        ax.text(0.015, 0.8 - k * 0.16, line, color="#b8d7a3" if k < 2 else TEXT,
                fontsize=7.5, family="monospace", va="top")


def main():
    """Arma la imagen y la guarda en docs/unreal_simulado.png."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--t", type=float, default=0.62,
                        help="Instante de la mano de --demo (0 = abierta, 1 = cerrada; default 0.62).")
    parser.add_argument("--salida", type=Path, default=OUT)
    args = parser.parse_args()
    hand, msgs, floats = received(args.t)

    fig = plt.figure(figsize=(16, 9), dpi=120, facecolor=BG)
    fig.text(0.012, 0.972, "HandMotion3D  →  Unreal Engine 5", color=TEXT, fontsize=15,
             fontweight="bold", va="center")
    fig.text(0.30, 0.972, "IMAGEN SIMULADA: no es una captura de Unreal. La pose y los números "
             "son los mensajes OSC reales de unreal_bridge.py --demo.", color=ACCENT, fontsize=9.5,
             va="center")
    draw_camera(fig, [0.008, 0.52, 0.27, 0.42], hand)
    draw_log(fig, [0.008, 0.33, 0.27, 0.175], msgs)
    draw_flexion(fig, [0.008, 0.012, 0.27, 0.305], floats)
    draw_viewport(fig, [0.285, 0.33, 0.707, 0.61], floats)
    draw_blueprint(fig, [0.285, 0.012, 0.707, 0.305], floats[ub.FLOAT_LAYOUT["flexion_grados"][0] + 4])
    args.salida.parent.mkdir(exist_ok=True)
    fig.savefig(args.salida, facecolor=BG)
    print(f"Imagen guardada en {args.salida}")


if __name__ == "__main__":
    main()
