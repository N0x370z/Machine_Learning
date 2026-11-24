"""
Escena de HandMotion3D en Unreal: una mano de esferas (articulaciones) y
cilindros (huesos) con los colores por dedo de hand_style.py, y la
función que la pone en la pose de un mensaje de unreal_bridge.py.

La usan receptor_handmotion.py (en vivo, dentro del editor) y
capturar_imagenes.py (imágenes para la documentación, sin ventana).

Formato del mensaje: ver unreal_bridge.py / UNREAL.md (87 floats; ejes de
Unreal: X adelante = se aleja de la cámara, Y derecha, Z arriba; cm).
"""

import struct

import unreal

ORIGIN = unreal.Vector(0.0, 0.0, 120.0)     # dónde se dibuja la muñeca
JOINT_RADIUS_CM = 0.85
TIP_RADIUS_CM = 0.75
BONE_RADIUS_CM = 0.5
PREFIX = "HM_"

CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
               (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
               (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]

# Colores de hand_style.FINGER_COLORS_RGB (paleta de Wong, apta para daltonismo).
_RGB = {"thumb": (230, 159, 0), "index": (86, 180, 233), "middle": (0, 158, 115),
        "ring": (204, 121, 167), "pinky": (213, 94, 0), "palm": (150, 150, 150),
        "forearm": (0, 114, 178)}
_FINGER = ["palm"] + ["thumb"] * 4 + ["index"] * 4 + ["middle"] * 4 + ["ring"] * 4 + ["pinky"] * 4


def _bone_color(a, b):
    """Color de un hueso: el del dedo, o gris si une la muñeca con un nudillo."""
    if a in (0, 5, 9, 13, 17) and b in (5, 9, 13, 17):
        return "palm"
    return _FINGER[b]


def _linear(name):
    r, g, b = _RGB[name]
    return unreal.LinearColor(*((c / 255.0) ** 2.2 for c in (r, g, b)), 1.0)


def _actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def spawn(cls, location=ORIGIN):
    """
    Crea un actor en el nivel del editor. En el modo sin ventana
    (capturar_imagenes.py) EditorActorSubsystem puede devolver None; ahí se
    usa el camino de GameplayStatics, que funciona en cualquier mundo.
    """
    actor = _actors().spawn_actor_from_class(cls, location)
    if actor is None:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        xf = unreal.Transform(location=location)
        actor = unreal.GameplayStatics.begin_deferred_actor_spawn_from_class(world, cls, xf)
        actor = unreal.GameplayStatics.finish_spawning_actor(actor, xf)
    if actor is None:
        raise RuntimeError(f"no se pudo crear un {cls.__name__} (¿hay un nivel abierto?)")
    return actor


def _shape(mesh, label, color):
    actor = spawn(unreal.StaticMeshActor)
    actor.set_actor_label(PREFIX + label)
    comp = actor.static_mesh_component
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_static_mesh(unreal.load_asset(f"/Engine/BasicShapes/{mesh}"))
    comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    mid = comp.create_dynamic_material_instance(
        0, unreal.load_asset("/Engine/BasicShapes/BasicShapeMaterial"))
    if mid:
        mid.set_vector_parameter_value("Color", color)
    return actor


class HandModel:
    """Los actores de una mano en el nivel y cómo ponerla en una pose."""

    def __init__(self):
        for a in _actors().get_all_level_actors():
            if a.get_actor_label().startswith(PREFIX + "Mano_"):
                a.destroy_actor()
        self.joints = []
        for i in range(21):
            radius = TIP_RADIUS_CM if i in (4, 8, 12, 16, 20) else JOINT_RADIUS_CM
            if i == 0:
                radius = 1.2
            j = _shape("Sphere", f"Mano_Punto_{i:02d}", _linear(_FINGER[i]))
            j.set_actor_scale3d(unreal.Vector(1, 1, 1) * (radius / 50.0))
            self.joints.append(j)
        self.bones = [(a, b, _shape("Cylinder", f"Mano_Hueso_{a}_{b}",
                                    _linear(_bone_color(a, b))))
                      for a, b in CONNECTIONS]
        self.forearm = _shape("Cylinder", "Mano_Antebrazo", _linear("forearm"))
        self.forearm.set_actor_hidden_in_game(True)
        self.forearm.set_is_temporarily_hidden_in_editor(True)
        self.wrist0 = None
        self.points = None

    @staticmethod
    def _place_bone(actor, p, q, radius):
        d = q - p
        length = d.length()
        if length < 1e-4:
            return
        actor.set_actor_location((p + q) * 0.5, False, False)
        actor.set_actor_rotation(unreal.MathLibrary.make_rot_from_z(d), False)
        actor.set_actor_scale3d(unreal.Vector(radius / 50.0, radius / 50.0, length / 100.0))

    def apply(self, floats, follow_wrist=0.3):
        """
        Pone la mano en la pose de un mensaje /handmotion/Left|Right.
        follow_wrist: fracción del desplazamiento de la muñeca (respecto al
        primer mensaje) que se aplica, para que se mueva sin salir de cuadro
        (con una cámara la muñeca está en cm de la imagen, lejos del origen).
        """
        wrist = unreal.Vector(*floats[3:6])
        if self.wrist0 is None:
            self.wrist0 = wrist
        base = ORIGIN + (wrist - self.wrist0) * follow_wrist
        pts = [base + unreal.Vector(*floats[6 + 3 * i: 9 + 3 * i]) for i in range(21)]
        for actor, p in zip(self.joints, pts):
            actor.set_actor_location(p, False, False)
        for a, b, actor in self.bones:
            self._place_bone(actor, pts[a], pts[b], BONE_RADIUS_CM)
        has_elbow = floats[1] > 0.5
        self.forearm.set_is_temporarily_hidden_in_editor(not has_elbow)
        if has_elbow:
            self._place_bone(self.forearm, pts[0] + unreal.Vector(*floats[69:72]), pts[0], 1.6)
        self.points = pts
        return pts


def new_level():
    """
    Nivel en blanco: sin el cielo, el terreno ni el sol del nivel por
    defecto del editor (con su sol la escena sale quemada). Solo se ve lo
    que pone build_stage. No se guarda en disco.
    """
    unreal.EditorLoadingAndSavingUtils.new_blank_map(False)


def build_stage():
    """Luz principal, luz de contorno y luz de ambiente (la mano sobre negro)."""
    for a in _actors().get_all_level_actors():
        label = a.get_actor_label()
        if label.startswith(PREFIX) and not label.startswith(PREFIX + "Mano_"):
            a.destroy_actor()
    # Sin piso ni fondo: la mano sobre negro. Un piso visto de costado
    # reflejaba el cielo del mapa de ambiente y salía blanco, y un plano de
    # fondo con color oscuro también salía blanco con estas luces.

    key = spawn(unreal.DirectionalLight)
    key.set_actor_label(PREFIX + "Luz_principal")
    key.set_actor_rotation(unreal.Rotator(0, -42, 35), False)
    key.light_component.set_intensity(4.0)
    key.light_component.set_light_color(unreal.LinearColor(1.0, 0.95, 0.88, 1.0))

    rim = spawn(unreal.PointLight, ORIGIN + unreal.Vector(30, 20, 25))
    rim.set_actor_label(PREFIX + "Luz_contorno")
    rim.light_component.set_intensity(1800.0)
    rim.light_component.set_attenuation_radius(200.0)
    rim.light_component.set_light_color(unreal.LinearColor(0.75, 0.85, 1.0, 1.0))

    sky = spawn(unreal.SkyLight)
    sky.set_actor_label(PREFIX + "Luz_ambiente")
    comp = sky.light_component
    comp.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    comp.set_editor_property("cubemap", unreal.load_asset(
        "/Engine/MapTemplates/Sky/DaylightAmbientCubemap"))
    comp.set_intensity(0.6)
    comp.recapture_sky()


def look_from(offset, target_offset=unreal.Vector(0, 0, 8)):
    """(ubicación, rotación) de una cámara en ORIGIN + offset mirando a la mano."""
    loc = ORIGIN + offset
    return loc, unreal.MathLibrary.find_look_at_rotation(loc, ORIGIN + target_offset)


# Vista por defecto: de frente, como la webcam (la cámara mira hacia +X).
FRONT_VIEW = unreal.Vector(-62, 0, 10)
THREE_QUARTER_VIEW = unreal.Vector(-40, -32, 10)


def osc_decode(packet):
    """(dirección, [floats]) de un mensaje OSC de unreal_bridge.py."""
    end = packet.index(b"\0")
    address = packet[:end].decode()
    i = (end + 4) & ~3
    end = packet.index(b"\0", i)
    tags = packet[i + 1:end].decode()
    i = (end + 4) & ~3
    return address, [struct.unpack(">f", packet[i + 4 * k: i + 4 * k + 4])[0]
                     for k in range(len(tags)) if tags[k] == "f"]
