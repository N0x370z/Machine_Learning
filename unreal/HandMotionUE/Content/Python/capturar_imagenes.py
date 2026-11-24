"""
Imágenes de la documentación, renderizadas por Unreal sin ventana.

Se activa con HM_CAPTURA=1 (lo hace docs/imagenes_unreal.py, que abre el
editor con -RenderOffscreen: el motor corre normal pero no crea ninguna
ventana, así no interrumpe lo que haya en pantalla).

Desde el 2026-11-24 usa el MISMO receptor que en vivo
(receptor_handmotion.py: dos manos, piel, la misma cámara y exposición),
así las imágenes son lo que se ve en el editor. Este módulo solo agrega
una cámara de captura y:

  1. espera a que lleguen datos (unreal_bridge.py --csv, en el puerto
     HM_PUERTO, que también usa el receptor);
  2. a los SHOT_TIMES segundos del primer fotograma renderiza la vista
     del receptor (y la última, de 3/4) con una SceneCapture2D, tick a
     tick (el motor tiene que avanzar: en un commandlet la imagen sale
     negra), y exporta cada una a PNG en HM_SALIDA;
  3. escribe unreal_imagenes.json y cierra el editor.
"""

import json
import os
import time

import unreal

import handmotion_escena as escena
import receptor_handmotion as receptor

OUT = os.environ.get("HM_SALIDA") or os.path.join(unreal.Paths.project_saved_dir(), "Imagenes")
W, H = 2560, 1440          # el doble del tamaño final: se reduce después (antialias)
WARMUP_TICKS = 12          # ticks capturando antes de exportar (sombras estables)
SHOTS = [("vista_1", 3.0, escena.TWO_HANDS_VIEW),
         ("vista_2", 7.0, escena.TWO_HANDS_VIEW),
         ("tres_cuartos", 11.0, escena.THREE_QUARTER_FAR_VIEW)]


def log(text):
    receptor.log(text)


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
    comp.set_editor_property("fov_angle", 90.0)    # el del viewport del editor
    return world, actor, comp, rt


class Capturer:
    def __init__(self):
        os.makedirs(OUT, exist_ok=True)
        self.world, self.actor, self.comp, self.rt = make_capture()
        self.plan = list(SHOTS)
        self.shots, self.ticks = [], 0
        self.t_first = None
        self.t_start = time.monotonic()
        self.done = False
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
        log(f"capturas: esperando datos en el puerto {receptor.PORT}")

    def tick(self, _dt):
        if self.done:
            return
        try:
            self._tick()
        except Exception as exc:
            log(f"error: {exc!r}")
            self.finish(error=repr(exc))

    def _tick(self):
        now = time.monotonic()
        if receptor.state["sim"] == "listo" and not getattr(self, "bound", False):
            copy = receptor.pie_copy(self.actor)       # la cámara también va al mundo simulado
            if copy is not None:
                self.actor = copy
                self.comp = copy.capture_component2d
                self.world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
                self.rt = unreal.RenderingLibrary.create_render_target2d(
                    self.world, W, H, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB,
                    unreal.LinearColor(0, 0, 0, 1), False)
                self.comp.set_editor_property("texture_target", self.rt)
                self.comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
                self.comp.set_editor_property("fov_angle", 90.0)
                self.bound = True
        if receptor.state["sim"] in ("pendiente", "arrancando"):
            return
        if self.t_first is None:
            if receptor.state["frames"]:
                self.t_first = now
            elif now - self.t_start > 120:
                self.finish(error="no llegaron datos en 120 s")
            return
        name, at, view = self.plan[0]
        if self.ticks == 0:
            if now - self.t_first < at:
                return
            loc, rot = escena.look_from(view)
            self.actor.set_actor_location(loc, False, False)
            self.actor.set_actor_rotation(rot, False)
        self.comp.capture_scene()
        self.ticks += 1
        if self.ticks < WARMUP_TICKS:
            return
        png = f"unreal_{name}.png"
        unreal.RenderingLibrary.export_render_target(self.world, self.rt, OUT, png)
        shown = sum(1 for s in receptor.slots if s.visible)
        log(f"imagen: {png} ({shown} mano(s))")
        self.shots.append({"imagen": png, "segundo": at, "manos_en_pantalla": shown})
        self.plan.pop(0)
        self.ticks = 0
        if not self.plan:
            self.finish()

    def finish(self, error=None):
        self.done = True
        unreal.unregister_slate_post_tick_callback(self.handle)
        meta = {"fotogramas_recibidos": receptor.state["frames"],
                "manos": sorted(receptor.state["labels"]),
                "motor": unreal.SystemLibrary.get_engine_version(), "imagenes": self.shots}
        if error:
            meta["error"] = error
        with open(os.path.join(OUT, "unreal_imagenes.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        log("listo" if not error else f"terminó con error: {error}")
        receptor.state["closing"] = True
        if receptor.state["sim"] != "no":
            try:
                unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
            except Exception:
                pass
        unreal.SystemLibrary.quit_editor()


capturer = Capturer()
