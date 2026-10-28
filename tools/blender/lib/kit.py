"""Shared helpers for the Blender build scripts (tools/blender/build/*.py).

Python because Blender's scripting API is Python-only; the game is TypeScript.

Conventions
  * Positions and sizes are given in GAME space: metres, +Y up, the game's
    +Z is Blender's -Y. B(x, y, z) converts. Characters face game +Z
    (Blender -Y, the Front view), which is what Object3D.lookAt expects.
  * Geometry is built Z-up inside Blender so the .blend files look normal
    when opened for hand editing.
  * Object names and custom properties follow docs/ART_PIPELINE.md; the game
    reads them (COL_, SPAWN_, NODE_, ENEMY_, ANCHOR_, BUOY_, TRIG_, INT_ …).
"""

import math
import os
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


# ----------------------------------------------------------------- basics


def B(x, y, z):
    """Game (x, y-up, z) to Blender (x, y, z-up)."""
    return Vector((x, -z, y))


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0


def srgb_to_linear(hex_color):
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    return (ch((hex_color >> 16) & 255), ch((hex_color >> 8) & 255), ch(hex_color & 255))


def hex_rgb(hex_color):
    return (((hex_color >> 16) & 255) / 255.0, ((hex_color >> 8) & 255) / 255.0, (hex_color & 255) / 255.0)


# ------------------------------------------------------------- materials


def material(name, color, rough=0.85, metal=0.0, emit=None, strength=1.0, vcol=False):
    """Principled material. vcol=True multiplies in the 'Col' colour attribute."""
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    m = bpy.data.materials.new(name)
    if m.node_tree is None:
        m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    lin = srgb_to_linear(color)
    bsdf.inputs["Base Color"].default_value = (*lin, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit is not None:
        bsdf.inputs["Emission Color"].default_value = (*srgb_to_linear(emit), 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
    if vcol:
        node = nt.nodes.new("ShaderNodeVertexColor")
        node.layer_name = "Col"
        nt.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
    m.diffuse_color = (*lin, 1.0)
    return m


# Shared palette (docs/ART_PIPELINE.md).
def palette():
    return {
        "timber": material("timber", 0x6B4F3A),
        "timber_light": material("timber_light", 0x8A6A4F),
        "driftwood": material("driftwood", 0x9C9384, rough=0.95),
        "stone": material("stone", 0xC9C3B5),
        "rock": material("rock", 0x7E7B73, rough=0.95),
        "rock_dark": material("rock_dark", 0x4E4C47, rough=0.95),
        "iron": material("iron", 0x2B2F33, rough=0.6, metal=0.6),
        "rust": material("rust", 0x7A4A2E, rough=0.9, metal=0.3),
        "brass": material("brass", 0xB8913A, rough=0.35, metal=0.9),
        "rope": material("rope", 0xA88F64),
        "kelp": material("kelp", 0x3F5A2E, rough=0.7),
        "kelp_dark": material("kelp_dark", 0x2D4224, rough=0.7),
        "sand": material("sand", 0xBFAE86),
        "glass_white": material("glass_white", 0xDDEEEA, rough=0.2),
        "glass_green": material("glass_green", 0x8FC9A8, rough=0.2),
        "glass_blue": material("glass_blue", 0x7FA8C9, rough=0.2),
        "cloth": material("cloth", 0x8E8166),
        "paint_red": material("paint_red", 0xB03A2E),
        "paint_white": material("paint_white", 0xE8E4DA),
        "paint_yellow": material("paint_yellow", 0xE0B040),
        "lamp": material("lamp", 0xFFF1C9, emit=0xFFB347, strength=2.0),
        "hull": material("hull", 0x4A3A2C),
        "hull_dark": material("hull_dark", 0x33281F),
        "copper": material("copper", 0x5E8C7A, rough=0.6, metal=0.5),
    }


# ----------------------------------------------------------- mesh builder


class MB:
    """Accumulates primitives (in the object's local GAME space) into one mesh."""

    def __init__(self):
        self.bm = bmesh.new()
        self.mats = []

    def _mi(self, mat):
        if mat is None:
            return 0
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _paint(self, verts, mat):
        idx = self._mi(mat)
        faces = {f for v in verts for f in v.link_faces}
        for f in faces:
            f.material_index = idx

    def box(self, size, at=(0, 0, 0), mat=None, yaw=0.0, pitch=0.0, roll=0.0, centered=False):
        """size = (x, y-up, z) in game metres. Base sits on `at` unless centered."""
        sx, sy, sz = size
        c = B(*at) + (Vector((0, 0, 0)) if centered else Vector((0, 0, sy / 2)))
        m = Matrix.LocRotScale(c, Euler((pitch, -roll, yaw)), Vector((sx, sz, sy)))
        ret = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        self._paint(ret["verts"], mat)
        return self

    def cyl(self, r1, r2, h, at=(0, 0, 0), mat=None, segs=10, pitch=0.0, yaw=0.0, roll=0.0, centered=False):
        """Cylinder/cone along game Y (before rotation). Base at `at` unless centered."""
        rot = Euler((pitch, -roll, yaw)).to_matrix().to_4x4()
        off = Vector((0, 0, 0 if centered else h / 2))
        m = Matrix.Translation(B(*at)) @ rot @ Matrix.Translation(off)
        ret = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=h, matrix=m)
        self._paint(ret["verts"], mat)
        return self

    def sphere(self, r, at=(0, 0, 0), mat=None, scale=(1, 1, 1), subdiv=1, yaw=0.0, pitch=0.0, roll=0.0):
        sx, sy, sz = scale
        m = Matrix.LocRotScale(B(*at), Euler((pitch, -roll, yaw)), Vector((sx, sz, sy)))
        ret = bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=r, matrix=m)
        self._paint(ret["verts"], mat)
        return self

    def rock(self, r, at=(0, 0, 0), mat=None, seed=0, squash=0.75, jitter=0.28, subdiv=1):
        rnd = random.Random(seed)
        m = Matrix.LocRotScale(B(*at), Euler((rnd.random() * 3, rnd.random() * 3, rnd.random() * 3)), Vector((1, 1, 1)))
        ret = bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=r, matrix=Matrix.Identity(4))
        for v in ret["verts"]:
            v.co *= 1.0 + (rnd.random() - 0.5) * 2 * jitter
        bmesh.ops.transform(self.bm, matrix=m, verts=ret["verts"])
        for v in ret["verts"]:
            v.co.z = B(*at).z + (v.co.z - B(*at).z) * squash
        self._paint(ret["verts"], mat)
        return self

    def build(self, name, loc=(0, 0, 0), yaw=0.0, roll=0.0, parent=None, props=None, col=False, origin_from_parent=False):
        me = bpy.data.meshes.new(name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        if parent is not None:
            ob.parent = parent
        ob.location = B(*loc)
        ob.rotation_euler = (roll, 0.0, yaw)
        if col:
            ob["col"] = 1
        for k, v in (props or {}).items():
            ob[k] = v
        return ob


def empty(name, loc=(0, 0, 0), props=None, yaw=0.0, parent=None, size=0.5):
    ob = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    ob.empty_display_type = "PLAIN_AXES"
    ob.empty_display_size = size
    ob.location = B(*loc)
    ob.rotation_euler = (0.0, 0.0, yaw)
    for k, v in (props or {}).items():
        ob[k] = v
    return ob


# --------------------------------------------------------------- terrain


def terrain(name, x0, x1, z0, z1, step, height, color, mat, props=None):
    """Heightfield grid in game space. height(x, z) -> y; color(x, z, y) -> 0xRRGGBB."""
    bm = bmesh.new()
    nx = int(round((x1 - x0) / step)) + 1
    nz = int(round((z1 - z0) / step)) + 1
    grid = []
    for j in range(nz):
        z = z0 + j * step
        row = []
        for i in range(nx):
            x = x0 + i * step
            row.append(bm.verts.new(B(x, height(x, z), z)))
        grid.append(row)
    for j in range(nz - 1):
        for i in range(nx - 1):
            bm.faces.new((grid[j][i], grid[j + 1][i], grid[j + 1][i + 1], grid[j][i + 1]))
    bm.normal_update()
    if bm.faces and next(iter(bm.faces)).normal.z < 0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)

    attr = me.color_attributes.new(name="Col", type="BYTE_COLOR", domain="CORNER")
    rnd = random.Random(1)
    for loop in me.loops:
        co = me.vertices[loop.vertex_index].co
        gx, gy, gz = co.x, co.z, -co.y
        r, g, b = hex_rgb(color(gx, gz, gy))
        n = (rnd.random() - 0.5) * 0.05
        attr.data[loop.index].color_srgb = (min(1, max(0, r + n)), min(1, max(0, g + n)), min(1, max(0, b + n)), 1.0)

    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for k, v in (props or {}).items():
        ob[k] = v
    return ob


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def seg_dist(px, pz, ax, az, bx, bz):
    """Distance from point to segment in the XZ plane."""
    dx, dz = bx - ax, bz - az
    L = dx * dx + dz * dz
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L))
    cx, cz = ax + t * dx, az + t * dz
    return math.hypot(px - cx, pz - cz)


def noise2(x, z, seed=0):
    """Cheap smooth-ish value noise in [-1, 1]."""
    s = math.sin(x * 0.173 + seed) * math.cos(z * 0.137 - seed * 0.5)
    s += 0.5 * math.sin(x * 0.41 + z * 0.29 + seed * 1.7)
    s += 0.25 * math.cos(x * 0.83 - z * 0.67 + seed * 2.3)
    return s / 1.75


# ---------------------------------------------------------------- output


def ignored(ob):
    return ob.name.startswith("_") or any(c.name == "_ignore" for c in ob.users_collection)


def check(objs):
    required = {"NODE_": ["node"], "ENEMY_": ["enemy"], "BUOY_": ["min", "max"], "TRIG_": ["event"], "INT_": ["interact"]}
    problems = []
    for ob in objs:
        for prefix, keys in required.items():
            if ob.name.startswith(prefix):
                problems += [f"{ob.name}: missing custom property '{k}'" for k in keys if k not in ob.keys()]
    return problems


def export_glb(path):
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    keep = [o for o in bpy.context.scene.objects if not ignored(o)]
    for p in check(keep):
        print(f"[export] WARNING {p}")
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in keep:
        o.hide_set(False)
        o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_extras=True,
        export_cameras=False,
        export_lights=False,
        export_animations=False,
        export_vertex_color="MATERIAL",
    )
    print(f"[export] wrote {path} ({len(keep)} objects)")


def save_and_export(blend_rel, glb_rel):
    blend = os.path.join(ROOT, blend_rel)
    os.makedirs(os.path.dirname(blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    print(f"[build] saved {blend}")
    export_glb(os.path.join(ROOT, glb_rel))
