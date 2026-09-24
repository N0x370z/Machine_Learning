"""
Visor 3D con dos puntos de vista (POV) de la misma escena, al estilo de
los viewports divididos de Blender: la misma mano (y antebrazo) se ve a
la vez desde dos ángulos distintos, y cada vista se gira con el mouse de
forma independiente.

Desde el 2026-09-24 (segunda versión) se dibuja con OpenCV, no con
matplotlib. La primera versión usaba matplotlib y tenía dos problemas
(ver CHANGELOG.md):
  - 'q' no cerraba bien: 'q' es la tecla de matplotlib para cerrar SU
    ventana (rcParams["keymap.quit"]), así que cerraba solo el visor y la
    cámara seguía; además, el bucle de eventos de matplotlib
    (flush_events) consumía las teclas de la ventana de OpenCV antes de
    que cv2.waitKey las viera, y había que presionar varias veces.
  - Se alentaba: redibujar dos ejes 3D de matplotlib cuesta ~90 ms por
    frame. Proyectar y dibujar los mismos segmentos con OpenCV cuesta
    unos pocos ms.
Ahora todo (cámara y visor) vive en un solo sistema de ventanas, y
cv2.waitKey recibe las teclas de las dos ventanas.

Lo usan:
  - Prueba.py (en vivo, junto a la ventana de la cámara).
  - plot_csv.py --3d (reproducción de un CSV ya grabado).

Controles (con cualquiera de las ventanas activa):
  - Arrastrar con clic izquierdo sobre una vista: la gira (órbita).
  - Rueda del mouse, clic derecho arrastrando o teclas + / -: zoom.
  - Teclas tipo numpad de Blender, aplicadas a la vista bajo el mouse:
        1 = Frente (como la ve la cámara)   3 = Lado   7 = Arriba
        9 = Vista opuesta (frente <-> atrás, arriba <-> abajo)
        . = Encuadrar manos on/off (como "View Selected" de Blender)
        l = Vincular 180° on/off         r = reiniciar vistas y zoom
  - Botones abajo: Frente / Atras / Lado / Arriba de cada vista, y los
    interruptores Vincular 180 y Encuadrar.
  - "Vincular 180°" (activo por defecto): el POV 2 sigue siempre al POV 1
    girado 180° en horizontal (misma elevación, azimut + 180°), así una
    vista muestra la mano por delante y la otra por detrás. Si se gira el
    POV 2, el POV 1 lo sigue igual. Apagado, cada vista va por su cuenta.
  - "Encuadrar" (activo por defecto): la vista sigue a las manos para
    verlas grandes. Apagado, se ve el frame completo de la cámara.

Proyección ortográfica (como las vistas numéricas de Blender): sin
perspectiva, así las distancias se comparan igual en toda la vista.

Sistema de coordenadas de la escena (las "unidades" son el ancho del
frame de la cámara, igual que la z de MediaPipe):
    X = x              (0 = borde izquierdo, 1 = borde derecho)
    Y = y * alto/ancho (0 = borde superior, crece hacia abajo)
    Z = z              (profundidad relativa a la muñeca; + = más lejos
                        de la cámara)
Para las vistas se reordena a (X, Z, -Y): X a la derecha, profundidad
hacia el fondo y altura hacia arriba. La cámara se dibuja como una
pirámide gris delante de la escena.

Última actualización: 2026-09-24. Historial: ver CHANGELOG.md.
"""

import math

import cv2
import numpy as np
from mediapipe.tasks.python import vision

import hand_style
import kinematics

HAND_CONNECTIONS = vision.HandLandmarksConnections.HAND_CONNECTIONS

WINDOW = "Vista 3D - dos POV"
VIEW_W, VIEW_H = 640, 520   # tamaño de cada POV en píxeles
BAR_H = 76                  # barra inferior con botones y ayuda

# Vistas predefinidas (elevación, azimut) en grados. Frente = mirando en
# la misma dirección que la cámara. Nombres sin acento: las fuentes de
# OpenCV solo soportan ASCII.
VIEWS = {
    "Frente": (0, -90),
    "Atras": (0, 90),
    "Lado": (0, 0),
    "Arriba": (90, -90),
}
# Vista inicial del POV 1: frente levemente desde arriba y de costado,
# para que se note la profundidad desde el primer momento. El POV 2
# arranca en su opuesto a 180° (ver opposite_180).
DEFAULT_POV1 = (15, -70)

# Encuadre: margen alrededor de las manos, tamaño mínimo del cubo (para
# que una mano lejana no se amplifique hasta verse ruidosa) y suavizado
# exponencial (1 = sin suavizar; sin él la vista "vibra" con la mano).
FIT_PADDING = 1.3
FIT_MIN_SIZE = 0.25
FIT_SMOOTHING = 0.25

# Flechas de velocidad: largo = velocidad * ARROW_SECONDS (dónde estaría
# el punto dentro de ese tiempo si siguiera igual). Por debajo de
# MIN_ARROW_CM_S no se dibujan (temblor, no movimiento).
ARROW_SECONDS = 0.15
MIN_ARROW_CM_S = 4.0
# Puntos con flecha: muñeca, puntas de los dedos y codo (con los 22 la
# vista se satura).
ARROW_POINTS = (0, *hand_style.FINGERTIPS, hand_style.ELBOW_INDEX)

# Paleta oscura tipo viewport de Blender (BGR).
BG = (40, 40, 40)
BG_ACTIVE = (46, 46, 46)
GRID = (62, 62, 62)
TEXT = (225, 225, 225)
TEXT_DIM = (150, 150, 150)
OUTLINE = (15, 15, 15)
CAMERA_COLOR = (140, 140, 140)
ARROW_COLOR = (80, 235, 255)   # amarillo
BTN = (70, 70, 70)
BTN_ON = (150, 110, 40)        # azul apagado = interruptor encendido
AXIS_COLORS = {"X": (80, 80, 230), "Prof": (90, 200, 90), "Alto": (230, 140, 70)}

FONT = cv2.FONT_HERSHEY_SIMPLEX


def opposite_180(elev, azim):
    """Misma elevación, girada 180° en horizontal (usado por 'Vincular')."""
    return elev, (azim + 360) % 360 - 180


def opposite_blender(elev, azim):
    """Vista opuesta como la tecla 9 de Blender: frente<->atrás, arriba<->abajo."""
    return -elev, (azim + 360) % 360 - 180


def _to_plot(p):
    """Escena (X, Y hacia abajo, Z profundidad) -> (X, profundidad, altura)."""
    x, y, z = p
    return np.array([x, z, -y], dtype=float)


def _basis(elev, azim):
    """Vectores derecha/arriba/hacia-el-observador de una vista ortográfica.

    Misma convención de ángulos que matplotlib: azim = -90 y elev = 0 es
    mirar desde el lado de la cámara hacia el fondo.
    """
    e, a = math.radians(elev), math.radians(azim)
    eye = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
    right = np.array([-math.sin(a), math.cos(a), 0.0])
    up = np.array([-math.sin(e) * math.cos(a), -math.sin(e) * math.sin(a), math.cos(e)])
    return right, up, eye


def _text(img, text, org, color=TEXT, scale=0.45, thick=1):
    """
    Texto con sombra oscura de 1 px, legible sobre cualquier fondo.

    No se usa el truco de "contorno" (mismo texto con más grosor debajo):
    en OpenCV el avance de cada letra crece con el grosor, así que en
    textos largos el contorno queda más largo que el texto y se ven letras
    fantasma al final.
    """
    x, y = org
    cv2.putText(img, text, (x + 1, y + 1), FONT, scale, OUTLINE, thick, cv2.LINE_AA)
    cv2.putText(img, text, org, FONT, scale, color, thick, cv2.LINE_AA)


def _dashed(img, p0, p1, color, thick, dash=9, gap=6):
    """Línea punteada (OpenCV no trae una)."""
    p0, p1 = np.array(p0, float), np.array(p1, float)
    length = float(np.linalg.norm(p1 - p0))
    if length < 1:
        return
    step = (p1 - p0) / length
    pos = 0.0
    while pos < length:
        a = p0 + step * pos
        b = p0 + step * min(pos + dash, length)
        cv2.line(img, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])),
                 color, thick, cv2.LINE_AA)
        pos += dash + gap


def hands_to_scene(tracked_hands, elbows, aspect, velocities=None):
    """
    Convierte las manos de Prueba.py (tuplas del HandTracker, landmarks de
    MediaPipe), los codos de forearm.py y las velocidades de
    kinematics.py a la escena del visor.

    Devuelve una lista de dicts {id, label, points: [21 x (X,Y,Z)],
    elbow: (X,Y,Z) o None, elbow_source, velocities: {idx: (vx,vy,vz)}}.
    """
    velocities = velocities or {}
    hands = []
    for track_id, label, _score, lms in tracked_hands:
        elbow = elbows.get(track_id)
        hands.append({
            "id": track_id,
            "label": label,
            "points": [(lm.x, lm.y * aspect, lm.z) for lm in lms],
            "elbow": (elbow.x, elbow.y * aspect, elbow.z) if elbow else None,
            "elbow_source": elbow.source if elbow else None,
            "velocities": velocities.get(track_id, {}),
        })
    return hands


def scene_points(hand):
    """{índice: (X,Y,Z)} de una mano de escena, con el codo como 21."""
    points = dict(enumerate(hand["points"]))
    if hand["elbow"] is not None:
        points[hand_style.ELBOW_INDEX] = hand["elbow"]
    return points


class _POV:
    def __init__(self, elev, azim):
        self.elev, self.azim, self.zoom = elev, azim, 1.0

    def set(self, elev, azim):
        self.elev = max(-90.0, min(90.0, elev))
        self.azim = (azim + 180) % 360 - 180


class _Projector:
    """Proyección ortográfica de coords de vista a píxeles de un POV."""

    def __init__(self, pov, center, size):
        self.right, self.up, self.eye = _basis(pov.elev, pov.azim)
        self.center = center
        self.scale = 0.85 * min(VIEW_W, VIEW_H) / size * pov.zoom

    def px(self, p):
        rel = np.asarray(p, float) - self.center
        x = VIEW_W / 2 + self.scale * float(rel @ self.right)
        y = VIEW_H / 2 - self.scale * float(rel @ self.up)
        # Recorte a un rango razonable: cv2 falla con coordenadas enormes
        # (p. ej. la pirámide de la cámara con mucho zoom).
        return (int(max(-10000, min(10000, x))), int(max(-10000, min(10000, y))))

    def depth(self, p):
        """Mayor = más cerca del observador (se dibuja después)."""
        return float((np.asarray(p, float) - self.center) @ self.eye)


class DualPOVViewer:
    """Ventana de OpenCV con dos vistas 3D (POV 1 y POV 2) de la escena."""

    def __init__(self, aspect=9 / 16):
        self.aspect = aspect
        self.linked = True
        self.fit = True
        self.povs = [_POV(*DEFAULT_POV1), _POV(*opposite_180(*DEFAULT_POV1))]
        self._fit = None      # (centro, tamaño) suavizado del encuadre
        self._hover = 0       # POV bajo el mouse (para las teclas 1/3/7/9)
        self._drag = None     # (pov, botón, x, y) mientras se arrastra
        self._buttons = []    # [(x0, y0, x1, y1, acción)] de la barra
        self._open = True
        cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(WINDOW, self._on_mouse)

    # ------------------------------------------------------------ vistas

    def set_view(self, idx, elev, azim):
        """Pone una vista en (elev, azim); si están vinculadas, la otra la sigue."""
        self.povs[idx].set(elev, azim)
        if self.linked:
            self.povs[1 - idx].set(*opposite_180(self.povs[idx].elev,
                                                  self.povs[idx].azim))

    def reset(self):
        self.povs = [_POV(*DEFAULT_POV1), _POV(*opposite_180(*DEFAULT_POV1))]

    def toggle_link(self):
        self.linked = not self.linked
        if self.linked:
            self.set_view(0, self.povs[0].elev, self.povs[0].azim)

    def toggle_fit(self):
        self.fit = not self.fit
        self._fit = None

    def handle_key(self, key):
        """
        Teclas del visor (llamar con el resultado de cv2.waitKey, que
        recibe las teclas de TODAS las ventanas de OpenCV). Devuelve True
        si la tecla era del visor.
        """
        pov = self.povs[self._hover]
        if key == ord("1"):
            self.set_view(self._hover, *VIEWS["Frente"])
        elif key == ord("3"):
            self.set_view(self._hover, *VIEWS["Lado"])
        elif key == ord("7"):
            self.set_view(self._hover, *VIEWS["Arriba"])
        elif key == ord("9"):
            self.set_view(self._hover, *opposite_blender(pov.elev, pov.azim))
        elif key == ord("."):
            self.toggle_fit()
        elif key == ord("l"):
            self.toggle_link()
        elif key == ord("r"):
            self.reset()
        elif key in (ord("+"), ord("=")):
            pov.zoom *= 1.15
        elif key == ord("-"):
            pov.zoom /= 1.15
        else:
            return False
        return True

    def _on_mouse(self, event, x, y, flags, _param):
        if y < VIEW_H:
            self._hover = 0 if x < VIEW_W else 1
        if event == cv2.EVENT_LBUTTONDOWN and y >= VIEW_H:
            for x0, y0, x1, y1, action in self._buttons:
                if x0 <= x <= x1 and y0 <= y <= y1:
                    action()
            return
        if event in (cv2.EVENT_LBUTTONDOWN, cv2.EVENT_RBUTTONDOWN) and y < VIEW_H:
            self._drag = (self._hover, event, x, y)
        elif event in (cv2.EVENT_LBUTTONUP, cv2.EVENT_RBUTTONUP):
            self._drag = None
        elif event == cv2.EVENT_MOUSEMOVE and self._drag is not None:
            idx, button, x0, y0 = self._drag
            dx, dy = x - x0, y - y0
            pov = self.povs[idx]
            if button == cv2.EVENT_LBUTTONDOWN:
                # Arrastrar a la derecha gira la escena a la derecha, como
                # la órbita de Blender. 0.4° por píxel.
                self.set_view(idx, pov.elev + dy * 0.4, pov.azim - dx * 0.4)
            else:
                pov.zoom *= 1.01 ** (-dy)
            self._drag = (idx, button, x, y)
        elif event == cv2.EVENT_MOUSEWHEEL:
            delta = cv2.getMouseWheelDelta(flags)
            self.povs[self._hover].zoom *= 1.1 if delta > 0 else 1 / 1.1

    # ------------------------------------------------------------ encuadre

    def _frame_target(self, hands):
        """(centro, tamaño) de la región a mostrar, en coords de vista."""
        if not self.fit:
            return np.array([0.5, 0.0, -self.aspect / 2]), 1.1
        if not hands:
            if self._fit is None:
                return np.array([0.5, 0.0, -self.aspect / 2]), 1.1
            return self._fit  # sin manos: se queda donde estaba
        pts = [_to_plot(p) for h in hands for p in scene_points(h).values()]
        lo, hi = np.min(pts, axis=0), np.max(pts, axis=0)
        target = ((lo + hi) / 2,
                  max(FIT_MIN_SIZE, FIT_PADDING * float(np.max(hi - lo))))
        if self._fit is not None:
            a = FIT_SMOOTHING
            target = (a * target[0] + (1 - a) * self._fit[0],
                      a * target[1] + (1 - a) * self._fit[1])
        self._fit = target
        return target

    # ------------------------------------------------------------ dibujo

    def render(self, hands, subtitle="", show_velocity=True):
        """
        Dibuja las dos vistas y la barra inferior y muestra la ventana.
        hands: lista de hands_to_scene (o frame_to_scene de plot_csv.py).
        """
        if not self._open:
            return
        center, size = self._frame_target(hands)
        views = []
        for idx, pov in enumerate(self.povs):
            img = np.full((VIEW_H, VIEW_W, 3),
                          BG_ACTIVE if idx == self._hover else BG, np.uint8)
            proj = _Projector(pov, center, size)
            self._draw_grid(img, proj, center, size)
            self._draw_camera(img, proj)
            for hand in hands:
                self._draw_hand(img, proj, hand, show_velocity)
            self._draw_gizmo(img, pov)
            _text(img, f"POV {idx + 1}", (12, 24), TEXT, 0.6)
            _text(img, f"elev {pov.elev:+.0f}  azim {pov.azim:+.0f}  zoom {pov.zoom:.1f}x",
                  (12, 46), TEXT_DIM, 0.4)
            views.append(img)
        top = np.hstack(views)
        cv2.line(top, (VIEW_W, 0), (VIEW_W, VIEW_H), OUTLINE, 2)
        if subtitle:
            (tw, _), _ = cv2.getTextSize(subtitle, FONT, 0.5, 1)
            _text(top, subtitle, (2 * VIEW_W - tw - 12, 24), TEXT, 0.5)
        canvas = np.vstack([top, self._draw_bar(show_velocity)])
        cv2.imshow(WINDOW, canvas)
        return canvas

    def _draw_grid(self, img, proj, center, size):
        """Piso de referencia (plano horizontal bajo la escena), como Blender."""
        floor = center[2] - size / 2
        step, n = size / 8, 8
        for i in range(-n, n + 1):
            a = (center[0] + i * step, center[1] - n * step, floor)
            b = (center[0] + i * step, center[1] + n * step, floor)
            c = (center[0] - n * step, center[1] + i * step, floor)
            d = (center[0] + n * step, center[1] + i * step, floor)
            cv2.line(img, proj.px(a), proj.px(b), GRID, 1, cv2.LINE_AA)
            cv2.line(img, proj.px(c), proj.px(d), GRID, 1, cv2.LINE_AA)

    def _draw_camera(self, img, proj):
        """Pirámide gris: dónde está la webcam (delante de la escena)."""
        apex = np.array([0.5, -0.5, -self.aspect / 2])
        s, d = 0.06, 0.08
        corners = [apex + (dx * s, d, dz * s * 0.6)
                   for dx, dz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for c in corners:
            cv2.line(img, proj.px(apex), proj.px(c), CAMERA_COLOR, 1, cv2.LINE_AA)
        for c0, c1 in zip(corners, corners[1:] + corners[:1]):
            cv2.line(img, proj.px(c0), proj.px(c1), CAMERA_COLOR, 1, cv2.LINE_AA)
        x, y = proj.px(apex)
        _text(img, "Camara", (x - 25, y + 18), CAMERA_COLOR, 0.4)

    def _draw_hand(self, img, proj, hand, show_velocity):
        """
        Dibuja una mano con sus conexiones ordenadas de atrás hacia
        adelante (algoritmo del pintor), para que los dedos más cercanos
        a la vista tapen a los más lejanos al girar.
        """
        pts = scene_points(hand)
        plot = {i: _to_plot(p) for i, p in pts.items()}
        px = {i: proj.px(p) for i, p in plot.items()}
        dashed = hand["label"] == "Left"  # igual que plot_csv.py: Left punteado
        elbow_idx = hand_style.ELBOW_INDEX
        forearm_color = hand_style.rgb_to_bgr(hand_style.FINGER_COLORS_RGB["forearm"])

        items = []  # (profundidad, función de dibujo)
        for conn in HAND_CONNECTIONS:
            s, e = conn.start, conn.end
            color = hand_style.rgb_to_bgr(hand_style.connection_color_rgb(s, e))
            depth = proj.depth((plot[s] + plot[e]) / 2)
            items.append((depth, _segment(img, px[s], px[e], color, 3, dashed)))
        if elbow_idx in px:
            estimated = hand["elbow_source"] == "estimado"
            depth = proj.depth((plot[0] + plot[elbow_idx]) / 2)
            items.append((depth, _segment(img, px[elbow_idx], px[0], forearm_color,
                                          4 if estimated else 8, estimated)))
        for i in range(21):
            finger = hand_style.finger_of(i)
            color = hand_style.rgb_to_bgr(hand_style.FINGER_COLORS_RGB[finger])
            is_tip = i in hand_style.FINGERTIPS
            items.append((proj.depth(plot[i]) + 1e-4,
                          _dot(img, px[i], 6 if is_tip else 3, color, is_tip)))
        for _depth, draw in sorted(items, key=lambda it: it[0]):
            draw()

        if show_velocity:
            self._draw_velocity(img, proj, hand, pts)

        wx, wy = px[0]
        _text(img, f"{hand['label']} #{hand['id']}", (wx + 10, wy + 22), TEXT, 0.45)
        if elbow_idx in px:
            ex, ey = px[elbow_idx]
            label = hand_style.ELBOW_NAME
            if hand["elbow_source"] == "estimado":
                label += " (estimado)"
            _text(img, label, (ex + 10, ey + 5), forearm_color, 0.42)

    def _draw_velocity(self, img, proj, hand, pts):
        """Flechas de velocidad en muñeca, puntas y codo (ver ARROW_*)."""
        vels = hand.get("velocities") or {}
        scale = kinematics.cm_per_unit(hand["points"])
        for i in ARROW_POINTS:
            v = vels.get(i)
            if v is None or i not in pts:
                continue
            if kinematics.speed_cm_s(v, scale) < MIN_ARROW_CM_S:
                continue
            p = np.array(pts[i])
            end = p + np.array(v) * ARROW_SECONDS
            p0, p1 = proj.px(_to_plot(p)), proj.px(_to_plot(end))
            cv2.arrowedLine(img, p0, p1, OUTLINE, 4, cv2.LINE_AA, tipLength=0.3)
            cv2.arrowedLine(img, p0, p1, ARROW_COLOR, 2, cv2.LINE_AA, tipLength=0.3)
        wrist_v = vels.get(0)
        if wrist_v is not None:
            wx, wy = proj.px(_to_plot(pts[0]))
            _text(img, f"{kinematics.speed_cm_s(wrist_v, scale):.0f} cm/s",
                  (wx + 10, wy + 42), ARROW_COLOR, 0.42)

    def _draw_gizmo(self, img, pov):
        """Ejes de orientación en la esquina inferior izquierda, como Blender."""
        right, up, eye = _basis(pov.elev, pov.azim)
        origin = (48, VIEW_H - 48)
        axes = {"X": np.array([1, 0, 0]), "Prof": np.array([0, 1, 0]),
                "Alto": np.array([0, 0, 1])}
        # Los ejes que apuntan hacia el observador se dibujan al final.
        for name, vec in sorted(axes.items(), key=lambda kv: float(kv[1] @ eye)):
            end = (int(origin[0] + 32 * float(vec @ right)),
                   int(origin[1] - 32 * float(vec @ up)))
            cv2.line(img, origin, end, AXIS_COLORS[name], 2, cv2.LINE_AA)
            _text(img, name, (end[0] + 3, end[1] + 4), AXIS_COLORS[name], 0.38)

    def _draw_bar(self, show_velocity):
        """Barra inferior: botones de vista por POV, interruptores y ayuda."""
        bar = np.full((BAR_H, 2 * VIEW_W, 3), (30, 30, 30), np.uint8)
        self._buttons = []

        def button(x, w, label, action, on=False):
            y = 8
            cv2.rectangle(bar, (x, y), (x + w, y + 26), BTN_ON if on else BTN, -1)
            cv2.rectangle(bar, (x, y), (x + w, y + 26), (95, 95, 95), 1)
            (tw, _), _ = cv2.getTextSize(label, FONT, 0.42, 1)
            cv2.putText(bar, label, (x + (w - tw) // 2, y + 18), FONT, 0.42,
                        TEXT, 1, cv2.LINE_AA)
            # Coordenadas en la ventana completa (la barra va debajo).
            self._buttons.append((x, VIEW_H + y, x + w, VIEW_H + y + 26, action))

        # Botones de vista bajo cada POV.
        for idx, left in enumerate((10, VIEW_W + 10)):
            for j, name in enumerate(VIEWS):
                button(left + j * 74, 68, name,
                       lambda i=idx, n=name: self.set_view(i, *VIEWS[n]))
        # Interruptores en el hueco de la derecha de cada grupo.
        button(320, 150, "Vincular 180", self.toggle_link, self.linked)
        button(480, 150, "Encuadrar", self.toggle_fit, self.fit)
        help_text = (f"[v] velocidad: {'si' if show_velocity else 'no'}   "
                     "arrastrar: girar | rueda o +/-: zoom | 1 frente  3 lado  "
                     "7 arriba  9 opuesta | . encuadrar | l vincular | r reiniciar | q salir")
        _text(bar, help_text, (10, 60), TEXT_DIM, 0.4)
        return bar

    # ------------------------------------------------------------ ventana

    def is_open(self):
        """False si el usuario cerró la ventana del visor con el botón rojo."""
        if not self._open:
            return False
        try:
            self._open = cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) >= 1
        except cv2.error:
            self._open = False
        return self._open

    def close(self):
        if self._open:
            try:
                cv2.destroyWindow(WINDOW)
            except cv2.error:
                pass
            self._open = False


def _segment(img, p0, p1, color, thick, dashed):
    """Función que dibuja un hueso (con contorno) cuando se la llama."""
    def draw():
        line = _dashed if dashed else (
            lambda im, a, b, c, t: cv2.line(im, a, b, c, t, cv2.LINE_AA))
        line(img, p0, p1, OUTLINE, thick + 2)
        line(img, p0, p1, color, thick)
    return draw


def _dot(img, p, radius, color, tip):
    """Función que dibuja una articulación (punta = con aro blanco)."""
    def draw():
        cv2.circle(img, p, radius + 1, OUTLINE, -1, cv2.LINE_AA)
        cv2.circle(img, p, radius, color, -1, cv2.LINE_AA)
        if tip:
            cv2.circle(img, p, radius + 3, (255, 255, 255), 1, cv2.LINE_AA)
    return draw
