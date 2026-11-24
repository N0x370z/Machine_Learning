"""
Escena de HandMotion3D en Unreal: una mano de esferas (articulaciones) y
cilindros (huesos) con los colores por dedo de hand_style.py, cubierta
por una piel translúcida (2026-11-24), y la función que la pone en la
pose de un mensaje de unreal_bridge.py.

La piel: un cilindro por falange (más delgado hacia la punta), una esfera
en cada articulación y en cada punta (cada dedo queda como una cápsula) y
la palma como una esfera aplastada entre la muñeca y los nudillos. El
material (M_PielTranslucida_v3, se crea solo la primera vez en
Content/HandMotion/) es translúcido y SIN iluminación, tipo rayos X: más
visible en los bordes que de frente (Fresnel), así el esqueleto se ve
adentro. Con iluminación, la piel reflejaba el mapa de ambiente y salía
con manchas blancas.

La usan receptor_handmotion.py (en vivo, dentro del editor) y
capturar_imagenes.py (imágenes para la documentación, sin ventana).

Formato del mensaje: ver unreal_bridge.py / UNREAL.md (87 floats; ejes de
Unreal: X adelante = se aleja de la cámara, Y derecha, Z arriba; cm).
"""

import struct

import unreal

ORIGIN = unreal.Vector(0.0, 0.0, 120.0)     # dónde se dibuja la muñeca
EV100 = 2.0       # exposición fija: una superficie gris con ~10 lux de luz
JOINT_RADIUS_CM = 0.85
TIP_RADIUS_CM = 0.75
BONE_RADIUS_CM = 0.5
PREFIX = "HM_"

# Piel: radio de cada dedo en la falange proximal (cm); se afina un 12 %
# por falange hacia la punta. Grosor de la palma (cm).
SKIN_RADIUS_CM = {"thumb": 1.1, "index": 0.95, "middle": 0.98, "ring": 0.92, "pinky": 0.8}
SKIN_TAPER = 0.88
PALM_THICKNESS_CM = 2.4
SKIN_COLOR = (0.85, 0.58, 0.45)        # tono piel, lineal
SKIN_MATERIAL = "/Game/HandMotion/M_PielTranslucida_v3"
BONE_MATERIAL = "/Game/HandMotion/M_HuesoMate_v1"   # el esqueleto: mate, sin brillos blancos
# Huesos con piel: los de los dedos (los de la palma los cubre la placa).
SKIN_BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (7, 8), (9, 10), (10, 11),
              (11, 12), (13, 14), (14, 15), (15, 16), (17, 18), (18, 19), (19, 20)]
TIPS = (4, 8, 12, 16, 20)
SKIN_JOINTS = (1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15, 17, 18, 19)   # articulaciones con piel

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


def skin_material():
    """
    El material de la piel: translúcido y sin iluminación (rayos X). Color
    piel al 30 % de frente y al 100 % en los bordes; opacidad de 0.16 a
    0.7 (Fresnel). Se crea y guarda la primera vez en Content/HandMotion/
    (no va en git: se regenera).
    """
    lib = unreal.EditorAssetLibrary
    if lib.does_asset_exist(SKIN_MATERIAL):
        return unreal.load_asset(SKIN_MATERIAL)
    folder, name = SKIN_MATERIAL.rsplit("/", 1)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, folder, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    mel = unreal.MaterialEditingLibrary
    color = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -700, 0)
    color.set_editor_property("parameter_name", "Color")
    color.set_editor_property("default_value", unreal.LinearColor(*SKIN_COLOR, 1.0))
    fresnel = mel.create_material_expression(mat, unreal.MaterialExpressionFresnel, -700, 250)
    fresnel.set_editor_property("exponent", 2.0)
    glow = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -450, 150)
    glow.set_editor_property("const_a", 0.3)
    glow.set_editor_property("const_b", 1.0)
    mel.connect_material_expressions(fresnel, "", glow, "Alpha")
    emissive = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -250, 0)
    mel.connect_material_expressions(color, "", emissive, "A")
    mel.connect_material_expressions(glow, "", emissive, "B")
    opacity = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -250, 250)
    opacity.set_editor_property("const_a", 0.16)
    opacity.set_editor_property("const_b", 0.7)
    mel.connect_material_expressions(fresnel, "", opacity, "Alpha")
    mel.connect_material_property(emissive, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(mat)
    lib.save_loaded_asset(mat)
    return mat


def bone_material():
    """
    Material del esqueleto: opaco, mate (rugosidad 0.8, especular 0.2) y con
    un parámetro Color. El BasicShapeMaterial de Unreal es muy brillante y
    hacía bordes blancos en los huesos vistos de costado. Se crea la primera
    vez en Content/HandMotion/.
    """
    lib = unreal.EditorAssetLibrary
    if lib.does_asset_exist(BONE_MATERIAL):
        return unreal.load_asset(BONE_MATERIAL)
    folder, name = BONE_MATERIAL.rsplit("/", 1)
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, folder, unreal.Material, unreal.MaterialFactoryNew())
    mel = unreal.MaterialEditingLibrary
    color = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -500, 0)
    color.set_editor_property("parameter_name", "Color")
    color.set_editor_property("default_value", unreal.LinearColor(0.5, 0.5, 0.5, 1.0))
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -500, 200)
    rough.set_editor_property("r", 0.8)
    spec = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -500, 300)
    spec.set_editor_property("r", 0.2)
    mel.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)
    mel.recompile_material(mat)
    lib.save_loaded_asset(mat)
    return mat


def _skin_shape(mesh, label):
    actor = spawn(unreal.StaticMeshActor)
    actor.set_actor_label(PREFIX + label)
    comp = actor.static_mesh_component
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_static_mesh(unreal.load_asset(f"/Engine/BasicShapes/{mesh}"))
    comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    comp.set_cast_shadow(False)          # una piel translúcida no debe tapar la luz
    comp.set_material(0, skin_material())
    return actor


def _shape(mesh, label, color):
    actor = spawn(unreal.StaticMeshActor)
    actor.set_actor_label(PREFIX + label)
    comp = actor.static_mesh_component
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_static_mesh(unreal.load_asset(f"/Engine/BasicShapes/{mesh}"))
    comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    mid = comp.create_dynamic_material_instance(0, bone_material())
    if mid:
        mid.set_vector_parameter_value("Color", color)
    return actor


class HandModel:
    """Los actores de una mano en el nivel y cómo ponerla en una pose."""

    def __init__(self, tag="", skin=True):
        """tag distingue varias manos en el nivel ("", "B"...); skin: con piel."""
        name = f"Mano{tag}_"
        for a in _actors().get_all_level_actors():
            if a.get_actor_label().startswith(PREFIX + name):
                a.destroy_actor()
        self.joints = []
        for i in range(21):
            radius = TIP_RADIUS_CM if i in (4, 8, 12, 16, 20) else JOINT_RADIUS_CM
            if i == 0:
                radius = 1.2
            j = _shape("Sphere", f"{name}Punto_{i:02d}", _linear(_FINGER[i]))
            j.set_actor_scale3d(unreal.Vector(1, 1, 1) * (radius / 50.0))
            self.joints.append(j)
        self.bones = [(a, b, _shape("Cylinder", f"{name}Hueso_{a}_{b}",
                                    _linear(_bone_color(a, b))))
                      for a, b in CONNECTIONS]
        self.forearm = _shape("Cylinder", f"{name}Antebrazo", _linear("forearm"))
        self.skin_bones, self.skin_tips, self.palm = [], [], None
        if skin:
            for a, b in SKIN_BONES:
                finger = _FINGER[b]
                k = (b - 1) % 4 if finger == "thumb" else (b - 2) % 4   # falange 0, 1, 2
                radius = SKIN_RADIUS_CM[finger] * SKIN_TAPER ** k
                self.skin_bones.append((a, b, radius, _skin_shape("Cylinder", f"{name}Piel_{a}_{b}")))
            for t in TIPS:
                radius = SKIN_RADIUS_CM[_FINGER[t]] * SKIN_TAPER ** (2 if t != 4 else 3)
                tip = _skin_shape("Sphere", f"{name}Piel_punta_{t}")
                tip.set_actor_scale3d(unreal.Vector(1, 1, 1) * (radius / 50.0))
                self.skin_tips.append((t, tip))
            for j in SKIN_JOINTS:
                finger = _FINGER[j + 1]
                k = j % 4 if finger == "thumb" else (j - 1) % 4      # falange que empieza aquí
                radius = SKIN_RADIUS_CM[finger] * SKIN_TAPER ** max(k - (0 if finger == "thumb" else 0), 0)
                joint = _skin_shape("Sphere", f"{name}Piel_art_{j}")
                joint.set_actor_scale3d(unreal.Vector(1, 1, 1) * (radius / 50.0))
                self.skin_tips.append((j, joint))
            self.palm = _skin_shape("Sphere", f"{name}Piel_palma")
        self.forearm.set_actor_hidden_in_game(True)
        self.forearm.set_is_temporarily_hidden_in_editor(True)
        self.wrist0 = None
        self.points = None
        self.visible = True
        self.has_elbow = False

    def set_visible(self, visible):
        """Muestra u oculta toda la mano (p. ej. cuando deja de llegar)."""
        if visible == self.visible:
            return
        self.visible = visible
        skin = [b[3] for b in self.skin_bones] + [t[1] for t in self.skin_tips]
        skin += [self.palm] if self.palm else []
        for actor in self.joints + [b[2] for b in self.bones] + skin:
            actor.set_is_temporarily_hidden_in_editor(not visible)
        self.forearm.set_is_temporarily_hidden_in_editor(not (visible and self.has_elbow))

    @staticmethod
    def _place_bone(actor, p, q, radius):
        d = q - p
        length = d.length()
        if length < 1e-4:
            return
        actor.set_actor_location((p + q) * 0.5, False, False)
        actor.set_actor_rotation(unreal.MathLibrary.make_rot_from_z(d), False)
        actor.set_actor_scale3d(unreal.Vector(radius / 50.0, radius / 50.0, length / 100.0))

    def _place_palm(self, pts):
        """Placa de la palma: de la muñeca a los nudillos, del índice al meñique."""
        across = pts[17] - pts[5]
        along = pts[9] - pts[0]
        width = across.length()
        if width < 1e-3 or along.length() < 1e-3:
            return
        x = across * (1.0 / width)
        z = x.cross(along)
        if z.length() < 1e-6:
            return
        z = z * (1.0 / z.length())
        knuckles = (pts[5] + pts[9] + pts[13] + pts[17]) * 0.25
        length = (knuckles - pts[0]).length()
        center = (knuckles + pts[0]) * 0.5
        self.palm.set_actor_location(center, False, False)
        self.palm.set_actor_rotation(unreal.MathLibrary.make_rot_from_xz(x, z), False)
        # Esfera de 100 cm aplastada: X = ancho (más el grosor de los dedos
        # de los bordes), Y = de la muñeca a los nudillos, Z = grosor.
        self.palm.set_actor_scale3d(unreal.Vector((width + 2.6) / 100.0, (length + 3.0) / 100.0,
                                                  PALM_THICKNESS_CM / 100.0))

    def apply(self, floats, follow_wrist=0.3, base=None):
        """
        Pone la mano en la pose de un mensaje /handmotion/Left|Right.
        follow_wrist: fracción del desplazamiento de la muñeca (respecto al
        primer mensaje) que se aplica, para que se mueva sin salir de cuadro
        (con una cámara la muñeca está en cm de la imagen, lejos del origen).
        base: dónde poner la muñeca (si se da, se ignora follow_wrist); lo
        usa el receptor para dibujar dos manos con su separación real.
        """
        wrist = unreal.Vector(*floats[3:6])
        if base is None:
            if self.wrist0 is None:
                self.wrist0 = wrist
            base = ORIGIN + (wrist - self.wrist0) * follow_wrist
        pts = [base + unreal.Vector(*floats[6 + 3 * i: 9 + 3 * i]) for i in range(21)]
        for actor, p in zip(self.joints, pts):
            actor.set_actor_location(p, False, False)
        for a, b, actor in self.bones:
            self._place_bone(actor, pts[a], pts[b], BONE_RADIUS_CM)
        for a, b, radius, actor in self.skin_bones:
            self._place_bone(actor, pts[a], pts[b], radius)
        for t, actor in self.skin_tips:
            actor.set_actor_location(pts[t], False, False)
        if self.palm:
            self._place_palm(pts)
        has_elbow = floats[1] > 0.5
        self.has_elbow = has_elbow
        self.forearm.set_is_temporarily_hidden_in_editor(not (has_elbow and self.visible))
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
        if label.startswith(PREFIX) and not label.startswith(PREFIX + "Mano"):
            a.destroy_actor()
    # Sin piso ni fondo: la mano sobre negro. Un piso visto de costado
    # reflejaba el cielo del mapa de ambiente y salía blanco, y un plano de
    # fondo con color oscuro también salía blanco con estas luces.

    key = spawn(unreal.DirectionalLight)
    key.set_actor_label(PREFIX + "Luz_principal")
    key.set_actor_rotation(unreal.Rotator(0, -42, 35), False)
    key.light_component.set_intensity(6.0)
    key.light_component.set_light_color(unreal.LinearColor(1.0, 0.95, 0.88, 1.0))

    rim = spawn(unreal.PointLight, ORIGIN + unreal.Vector(30, 20, 25))
    rim.set_actor_label(PREFIX + "Luz_contorno")
    rim.light_component.set_intensity(120.0)     # con 1800 quemaba en blanco el borde de las esferas
    rim.light_component.set_attenuation_radius(200.0)
    rim.light_component.set_light_color(unreal.LinearColor(0.75, 0.85, 1.0, 1.0))

    sky = spawn(unreal.SkyLight)
    sky.set_actor_label(PREFIX + "Luz_ambiente")
    comp = sky.light_component
    comp.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    comp.set_editor_property("cubemap", unreal.load_asset(
        "/Engine/MapTemplates/Sky/DaylightAmbientCubemap"))
    comp.set_intensity(0.25)    # más baja: el mapa de ambiente hacía brillos blancos
    comp.recapture_sky()

    # Exposición fija también en el viewport del editor (2026-11-24): sin
    # esto la exposición automática quemaba u oscurecía la mano según la
    # escena. Los mismos valores que las imágenes de la documentación.
    ppv = spawn(unreal.PostProcessVolume)
    ppv.set_actor_label(PREFIX + "Postproceso")
    ppv.set_editor_property("unbound", True)
    pp = ppv.get_editor_property("settings")
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
        except Exception:
            pass
    ppv.set_editor_property("settings", pp)


def look_from(offset, target_offset=unreal.Vector(0, 0, 8)):
    """(ubicación, rotación) de una cámara en ORIGIN + offset mirando a la mano."""
    loc = ORIGIN + offset
    return loc, unreal.MathLibrary.find_look_at_rotation(loc, ORIGIN + target_offset)


# Vista por defecto: de frente, como la webcam (la cámara mira hacia +X).
FRONT_VIEW = unreal.Vector(-62, 0, 10)
TWO_HANDS_VIEW = unreal.Vector(-42, 0, 9)    # el receptor (viewport de 90°): caben dos manos
THREE_QUARTER_VIEW = unreal.Vector(-40, -32, 10)
THREE_QUARTER_FAR_VIEW = unreal.Vector(-32, -28, 12)   # 3/4 con las dos manos


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
