"""
Mano con huesos (2026-11-24): un modelo de mano real (malla con esqueleto)
que se mueve girando sus huesos con los 21 puntos de HandMotion3D.

El modelo es MannequinHand_Right, la mano del maniquí de Unreal que viene
con el motor (recursos de la plantilla Collaborative Viewer). Es contenido
de Epic: NO va en el repositorio. ensure_assets() lo copia desde la
instalación de Unreal a Content/CollaborativeViewer/ la primera vez (fuera
de git). Tiene 16 huesos: hand_r y, por dedo, *_01_r, *_02_r, *_03_r.

Cómo se mueve (solo con direcciones, no con posiciones, para que el
modelo conserve el largo de sus dedos aunque los de la captura midan
distinto):
  1. Orientación de la mano: un marco con muñeca -> nudillo del medio y
     nudillo del índice -> del meñique, en los datos y en la pose de
     referencia del modelo; hand_r gira para que coincidan.
  2. Cada falange gira lo mínimo para apuntar de su articulación a la
     siguiente en los datos, de la base a la punta.
  3. Escala: el largo de la palma del modelo se ajusta al de los datos.
  4. Mano izquierda: el mismo modelo en espejo (escala Y negativa), con los
     datos reflejados.

Simulate: en el editor (fuera de Play/Simulate) un PoseableMeshComponent
no hace tick y la malla NO se redibuja aunque los huesos ya estén girados
(comprobado en UE 5.8: los huesos quedan bien y la malla sigue en la pose
de reposo). Por eso el receptor arranca el modo Simulate del editor y
bind() enlaza esta mano con su copia en el mundo simulado, donde sí hace
tick.

La interfaz es la de handmotion_escena.HandModel (apply, step, reset,
set_visible), así el receptor usa cualquiera de las dos.
"""

import math
import os
import shutil

import unreal

import handmotion_escena as escena

MESH = "/Game/CollaborativeViewer/Meshes/Avatar/MannequinHand_Right"
_FILES = ("MannequinHand_Right.uasset", "MannequinHand_Right_Skeleton.uasset",
          "MannequinHand_Right_PhysicsAsset.uasset")
# Hueso -> (punto de MediaPipe donde empieza, punto hacia donde apunta).
CHAINS = [
    ("thumb", [("thumb_01_r", 1, 2), ("thumb_02_r", 2, 3), ("thumb_03_r", 3, 4)]),
    ("index", [("index_01_r", 5, 6), ("index_02_r", 6, 7), ("index_03_r", 7, 8)]),
    ("middle", [("middle_01_r", 9, 10), ("middle_02_r", 10, 11), ("middle_03_r", 11, 12)]),
    ("ring", [("ring_01_r", 13, 14), ("ring_02_r", 14, 15), ("ring_03_r", 15, 16)]),
    ("pinky", [("pinky_01_r", 17, 18), ("pinky_02_r", 18, 19), ("pinky_03_r", 19, 20)]),
]
CS = unreal.BoneSpaces.COMPONENT_SPACE


def ensure_assets():
    """Copia la mano de Epic de la instalación de Unreal al proyecto (si falta)."""
    if unreal.EditorAssetLibrary.does_asset_exist(MESH):
        return unreal.load_asset(MESH)
    engine = unreal.Paths.convert_relative_path_to_full(unreal.Paths.engine_dir())
    src = os.path.join(engine, "..", "Templates", "TemplateResources", "Standard",
                       "CollaborativeViewer", "Content", "Meshes", "Avatar")
    content = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
    dst = os.path.join(content, "CollaborativeViewer", "Meshes", "Avatar")
    os.makedirs(dst, exist_ok=True)
    for f in _FILES:
        if not os.path.exists(os.path.join(dst, f)):
            shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
    unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous(
        ["/Game/CollaborativeViewer"], True)
    return unreal.load_asset(MESH)


# ------------------------------------------------ vectores y cuaterniones
# Tuplas (x, y, z) y (x, y, z, w), misma convención que unreal.Quat.

def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(_dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n) if n > 1e-9 else (0.0, 0.0, 0.0)


def _qmul(a, b):
    """a * b: primero b, después a."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def _qrot(q, v):
    """Rota el vector v con q."""
    x, y, z, w = q
    t = _cross((x, y, z), v)
    t = (2 * t[0], 2 * t[1], 2 * t[2])
    c = _cross((x, y, z), t)
    return (v[0] + w * t[0] + c[0], v[1] + w * t[1] + c[1], v[2] + w * t[2] + c[2])


def _from_to(u, v):
    """Giro mínimo que lleva la dirección u a la v (unitarias)."""
    d = _dot(u, v)
    if d < -0.999999:                       # opuestas: 180° sobre un eje perpendicular
        axis = _cross((1, 0, 0), u)
        if _dot(axis, axis) < 1e-6:
            axis = _cross((0, 1, 0), u)
        axis = _norm(axis)
        return (axis[0], axis[1], axis[2], 0.0)
    c = _cross(u, v)
    q = (c[0], c[1], c[2], 1.0 + d)
    n = math.sqrt(sum(x * x for x in q))
    return tuple(x / n for x in q)


def _q_from_axes(x, y, z):
    """Cuaternión de una base ortonormal (columnas x, y, z)."""
    m00, m01, m02 = x[0], y[0], z[0]
    m10, m11, m12 = x[1], y[1], z[1]
    m20, m21, m22 = x[2], y[2], z[2]
    tr = m00 + m11 + m22
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = ((m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s, 0.25 * s)
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2
        q = (0.25 * s, (m01 + m10) / s, (m02 + m20) / s, (m21 - m12) / s)
    elif m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2
        q = ((m01 + m10) / s, 0.25 * s, (m12 + m21) / s, (m02 - m20) / s)
    else:
        s = math.sqrt(1.0 + m22 - m00 - m11) * 2
        q = ((m02 + m20) / s, (m12 + m21) / s, 0.25 * s, (m10 - m01) / s)
    n = math.sqrt(sum(v * v for v in q))
    return tuple(v / n for v in q)


def _qinv(q): return (-q[0], -q[1], -q[2], q[3])


def _hand_frame(wrist, middle, index, pinky):
    """Marco de la palma: x = muñeca -> medio, y = índice -> meñique, z = normal."""
    fx = _norm(_sub(middle, wrist))
    side = _sub(pinky, index)
    fz = _norm(_cross(fx, side))
    fy = _cross(fz, fx)
    return _q_from_axes(fx, fy, fz)


def _v(t): return (t.x, t.y, t.z)


# ------------------------------------------------------------ la mano

class SkinnedHand:
    """Una mano con huesos en el nivel; misma interfaz que escena.HandModel."""

    def __init__(self, tag="", material=None):
        mesh = ensure_assets()
        self.holder = escena.spawn(unreal.StaticMeshActor)
        self.holder.set_actor_label(f"{escena.PREFIX}Mano{tag}_ConHuesos")
        self.holder.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        root = sub.k2_gather_subobject_data_for_instance(self.holder)[0]
        res = sub.add_new_subobject(unreal.AddNewSubobjectParams(
            parent_handle=root, new_class=unreal.PoseableMeshComponent))
        handle = res[0] if isinstance(res, (tuple, list)) else res
        lib = unreal.SubobjectDataBlueprintFunctionLibrary
        self.comp = lib.get_object(lib.get_data(handle))
        self.comp.set_skinned_asset_and_update(mesh, True)
        self.material = material or escena.skin_material()
        self.comp.set_material(0, self.material)
        self.comp.set_cast_shadow(False)
        # Pose de referencia (espacio del componente, con el actor en el origen).
        self.ref_q, self.ref_p, self.ref_dir = {}, {}, {}
        for i in range(self.comp.get_num_bones()):
            name = str(self.comp.get_bone_name(i))
            t = self.comp.get_bone_transform_by_name(name, CS)
            q = t.rotation
            self.ref_q[name] = (q.x, q.y, q.z, q.w)
            self.ref_p[name] = _v(t.translation)
        for _finger, chain in CHAINS:          # dirección de cada hueso hacia el siguiente
            for k, (bone, _a, _b) in enumerate(chain):
                if k + 1 < len(chain):
                    self.ref_dir[bone] = _norm(_sub(self.ref_p[chain[k + 1][0]], self.ref_p[bone]))
                else:                          # la punta: sigue la del hueso anterior
                    self.ref_dir[bone] = self.ref_dir[chain[k - 1][0]]
        p = self.ref_p
        self.ref_frame = _hand_frame(p["hand_r"], p["middle_01_r"], p["index_01_r"], p["pinky_01_r"])
        palm = _sub(p["middle_01_r"], p["hand_r"])
        self.ref_palm = math.sqrt(_dot(palm, palm))
        self.left = False
        self.scale = None
        self.visible = True
        self.target = None
        self.current = None
        self.points = None

    NEEDS_SIMULATE = True

    def bind(self, world):
        """Pasa a usar la copia de esta mano en el mundo de Simulate."""
        name = self.holder.get_name()
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.StaticMeshActor):
            if actor.get_name() == name:
                self.holder = actor
                self.comp = actor.get_component_by_class(unreal.PoseableMeshComponent)
                self.comp.set_material(0, self.material)   # no se copia al mundo simulado
                self.comp.set_visibility(self.visible, True)
                self.current = None
                return True
        return False

    # -- interfaz de HandModel
    def set_visible(self, visible):
        if visible != self.visible:
            self.visible = visible
            self.holder.set_is_temporarily_hidden_in_editor(not visible)
            self.comp.set_visibility(visible, True)

    def reset(self):
        self.current = None
        self.scale = None

    def apply(self, floats, follow_wrist=0.3, base=None, label=None):
        if label is not None:
            self.left = label == "Left"
        if base is None:
            base = escena.ORIGIN
        pts = [base + unreal.Vector(*floats[6 + 3 * i: 9 + 3 * i]) for i in range(21)]
        self.target = pts
        if self.current is None:
            self.current = [unreal.Vector(q.x, q.y, q.z) for q in pts]
            self._pose(self.current)
        self.points = pts
        return pts

    def step(self, dt, tau=escena.SMOOTH_TAU_S):
        if self.target is None:
            return
        if self.current is None or tau <= 0:
            self.current = [unreal.Vector(q.x, q.y, q.z) for q in self.target]
        else:
            k = 1.0 - math.exp(-max(dt, 0.0) / tau)
            for i, t in enumerate(self.target):
                self.current[i] = self.current[i] + (t - self.current[i]) * k
        self._pose(self.current)

    # -- los huesos
    def _pose(self, pts):
        w = pts[0]
        palm = (pts[9] - w).length()
        if palm < 1e-3:
            return
        s = palm / self.ref_palm
        self.scale = s if self.scale is None else self.scale + (s - self.scale) * 0.2
        m = -1.0 if self.left else 1.0
        self.holder.set_actor_location(w, False, False)
        self.holder.set_actor_scale3d(unreal.Vector(self.scale, m * self.scale, self.scale))
        # Puntos en el espacio del componente (la muñeca en el origen, sin escala, sin espejo).
        q = [((p.x - w.x) / self.scale, m * (p.y - w.y) / self.scale, (p.z - w.z) / self.scale)
             for p in pts]
        frame = _hand_frame(q[0], q[9], q[5], q[17])
        r_hand = _qmul(frame, _qinv(self.ref_frame))
        self._set("hand_r", _qmul(r_hand, self.ref_q["hand_r"]))
        for _finger, chain in CHAINS:
            for bone, a, b in chain:
                target = _norm(_sub(q[b], q[a]))
                if target == (0.0, 0.0, 0.0):
                    continue
                predicted = _qrot(r_hand, self.ref_dir[bone])
                fix = _from_to(predicted, target)
                self._set(bone, _qmul(fix, _qmul(r_hand, self.ref_q[bone])))

    def _set(self, bone, q):
        self.comp.set_bone_rotation_by_name(bone, unreal.Quat(*q).rotator(), CS)
