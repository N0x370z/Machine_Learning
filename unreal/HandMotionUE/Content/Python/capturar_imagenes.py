"""
Imágenes de la documentación, renderizadas por Unreal sin ventana.

Se activa con HM_CAPTURA=1 (lo hace docs/imagenes_unreal.py, que abre el
editor con -RenderOffscreen: el motor corre normal pero no crea ninguna
ventana, así no interrumpe lo que haya en pantalla). En vez del receptor
en vivo, init_unreal.py importa este módulo, que:

  1. arma la misma escena que el receptor (handmotion_escena.py);
  2. recibe por UDP los mensajes REALES de unreal_bridge.py (--csv de una
     captura) durante HM_SEGUNDOS segundos;
  3. elige la mano más abierta y la más cerrada que llegaron;
  4. las renderiza con una SceneCapture2D, tick a tick (el motor tiene que
     avanzar entre poner la pose y capturar: en un commandlet no avanza y
     la imagen sale negra), y exporta cada una a PNG en HM_SALIDA;
  5. escribe unreal_imagenes.json y cierra el editor.
"""

import json
import os
import socket
import time

import unreal

import handmotion_escena as escena

OUT = os.environ.get("HM_SALIDA") or os.path.join(unreal.Paths.project_saved_dir(), "Imagenes")
PORT = int(os.environ.get("HM_PUERTO", "8020"))
SECONDS = float(os.environ.get("HM_SEGUNDOS", "6"))
EV100 = float(os.environ.get("HM_EV", "2"))
W, H = 2560, 1440          # el doble del tamaño final: se reduce después (antialias)
WARMUP_TICKS = 12          # ticks capturando antes de exportar (sombras estables)


def log(text):
    unreal.log(f"[HandMotion] {text}")


def make_capture():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actor = escena.spawn(unreal.SceneCapture2D)
    actor.set_actor_label(escena.PREFIX + "Camara_imagenes")
    comp = actor.capture_component2d
    rt = unreal.RenderingLibrary.create_render_target2d(
        world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB,
        unreal.LinearColor(0, 0, 0, 1), False)
    comp.set_editor_property("texture_target", rt)
    comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    comp.set_editor_property("capture_every_frame", False)
    comp.set_editor_property("fov_angle", 38.0)
    pp = comp.get_editor_property("post_process_settings")
    # Exposición fija (EV100 = 2: una superficie gris con ~10 lux de luz).
    # La automática no tiene tiempo de adaptarse en una captura suelta, y
    # la manual por defecto (EV100 ~10, sol de día) deja la escena negra.
    for name, value in [
        ("override_auto_exposure_method", True),
        ("auto_exposure_method", unreal.AutoExposureMethod.AEM_HISTOGRAM),
        ("override_auto_exposure_min_brightness", True), ("auto_exposure_min_brightness", EV100),
        ("override_auto_exposure_max_brightness", True), ("auto_exposure_max_brightness", EV100),
        ("override_auto_exposure_bias", True), ("auto_exposure_bias", 0.0),
        ("override_vignette_intensity", True), ("vignette_intensity", 0.35),
        ("override_bloom_intensity", True), ("bloom_intensity", 0.0),
    ]:
        try:
            pp.set_editor_property(name, value)
        except Exception as exc:
            log(f"post-proceso {name}: {exc}")
    comp.set_editor_property("post_process_settings", pp)
    comp.set_editor_property("post_process_blend_weight", 1.0)
    return world, actor, comp, rt


def curl(floats):
    """Flexión media de índice a meñique (grados)."""
    return sum(floats[75:87]) / 12


class Capturer:
    def __init__(self):
        os.makedirs(OUT, exist_ok=True)
        escena.new_level()
        escena.build_stage()
        self.hand = escena.HandModel()
        self.world, self.actor, self.comp, self.rt = make_capture()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", PORT))
        self.sock.setblocking(False)
        self.frames, self.hands = 0, []
        self.t_first = None
        self.plan, self.shots, self.ticks = None, [], 0
        self.t_start = time.monotonic()
        self.done = False
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
        log(f"esperando datos en 127.0.0.1:{PORT}")

    def receive(self):
        while True:
            try:
                packet, _ = self.sock.recvfrom(4096)
            except (BlockingIOError, OSError):
                return
            address, floats = escena.osc_decode(packet)
            if self.t_first is None:
                self.t_first = time.monotonic()
            if address == "/handmotion/frame":
                self.frames += 1
            elif len(floats) == 87:
                self.hands.append((address, floats))

    def tick(self, _dt):
        if self.done:
            return
        try:
            self._tick()
        except Exception as exc:
            log(f"error: {exc!r}")
            self.finish(error=repr(exc))

    def _tick(self):
        if self.plan is None:                          # fase 1: recibir
            self.receive()
            if self.t_first is None:
                if time.monotonic() - self.t_start > 120:
                    self.finish(error="no llegaron datos en 120 s")
                return
            if time.monotonic() - self.t_first < SECONDS:
                return
            self.sock.close()
            log(f"recibidos {self.frames} fotogramas y {len(self.hands)} mensajes de mano")
            if not self.hands:
                self.finish(error="no llegó ninguna mano")
                return
            opened = min(self.hands, key=lambda h: curl(h[1]))
            closed = max(self.hands, key=lambda h: curl(h[1]))
            self.plan = [("abierta", opened, escena.FRONT_VIEW),
                         ("cerrada", closed, escena.FRONT_VIEW),
                         ("tres_cuartos", closed, escena.THREE_QUARTER_VIEW)]
            self.ticks = 0
            return
        tag, (address, floats), view = self.plan[0]   # fase 2: una imagen por vez
        if self.ticks == 0:
            self.hand.wrist0 = None
            self.hand.apply(floats)
            loc, rot = escena.look_from(view)
            self.actor.set_actor_location(loc, False, False)
            self.actor.set_actor_rotation(rot, False)
        self.comp.capture_scene()
        self.ticks += 1
        if self.ticks < WARMUP_TICKS:
            return
        name = f"unreal_{tag}.png"
        unreal.RenderingLibrary.export_render_target(self.world, self.rt, OUT, name)
        log(f"imagen: {name}")
        self.shots.append({"imagen": name, "mensaje": address,
                           "flexion_media_grados": round(curl(floats), 1),
                           "palma_cm": round(floats[2], 2)})
        self.plan.pop(0)
        self.ticks = 0
        if not self.plan:
            self.finish()

    def finish(self, error=None):
        self.done = True
        unreal.unregister_slate_post_tick_callback(self.handle)
        meta = {"fotogramas_recibidos": self.frames, "mensajes_de_mano": len(self.hands),
                "motor": unreal.SystemLibrary.get_engine_version(), "imagenes": self.shots}
        if error:
            meta["error"] = error
        with open(os.path.join(OUT, "unreal_imagenes.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        log("listo" if not error else f"terminó con error: {error}")
        unreal.SystemLibrary.quit_editor()


capturer = Capturer()
