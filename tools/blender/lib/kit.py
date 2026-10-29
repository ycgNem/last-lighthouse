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

Look (docs/ART_PIPELINE.md, "Materials & look")
  * A handful of shading materials (wood, stone, iron, brass, cloth …) take
    their colour from a vertex-colour layer, so one material covers every
    timber tone and a prop costs few draw calls. P["timber"] is a Paint: a
    material plus the palette colour it's painted with. Emissive and GLOW_
    surfaces stay plain materials.
  * MB bakes that colour per vertex with a little variation per piece, ambient
    occlusion (rays cast against the object itself and the ground under it),
    grime toward the base and, for things standing in the sea, a dark wet band
    under the high-tide line with a pale salt line on it. Hard pieces get
    chamfered edges so they catch the light.
"""

import math
import os
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# Game-space water heights (src/data/tide.ts): low water and the high-tide line.
LOW_WATER = 0.0
HIGH_WATER = 1.8


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


def lerp(a, b, t):
    return a + (b - a) * t


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


def _hash(ix, iy, iz, seed):
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h &= 0xFFFFFFFF
    h ^= h >> 15
    h = (h * 2246822519) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 3266489917) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 0xFFFFFFFF


def vnoise3(x, y, z, seed=0):
    """Smooth 3D value noise in [0, 1]."""
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    ux, uy, uz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)

    def c(dx, dy, dz):
        return _hash(ix + dx, iy + dy, iz + dz, seed)

    x00 = lerp(c(0, 0, 0), c(1, 0, 0), ux)
    x10 = lerp(c(0, 1, 0), c(1, 1, 0), ux)
    x01 = lerp(c(0, 0, 1), c(1, 0, 1), ux)
    x11 = lerp(c(0, 1, 1), c(1, 1, 1), ux)
    return lerp(lerp(x00, x10, uy), lerp(x01, x11, uy), uz)


def fbm3(x, y, z, seed=0, octaves=3):
    """Fractal value noise in roughly [-1, 1]."""
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total += amp * (vnoise3(x, y, z, seed + o * 17) * 2 - 1)
        norm += amp
        amp *= 0.5
        x, y, z = x * 2.03, y * 2.03, z * 2.03
    return total / norm


def smax(a, b, k):
    """Smooth max: the larger of two heights, rounded over where they're within k of each other."""
    h = max(k - abs(a - b), 0.0) / k
    return max(a, b) + h * h * k * 0.25


def mix(a, b, t):
    """Blends two 0xRRGGBB colours."""
    t = max(0.0, min(1.0, t))
    out = 0
    for sh in (16, 8, 0):
        ca, cb = (a >> sh) & 255, (b >> sh) & 255
        out |= int(round(ca + (cb - ca) * t)) << sh
    return out


def turn(yaw, lx, lz):
    """A local (x, z) offset turned by yaw, the way three.js turns rotation.y."""
    c, s = math.cos(yaw), math.sin(yaw)
    return lx * c + lz * s, -lx * s + lz * c


def facing(dx, dz):
    """The yaw that turns a model's front (+Z) toward (dx, dz)."""
    return math.atan2(dx, dz)


def look(dx, dz):
    """The yaw for a spawn whose view looks toward (dx, dz) (a camera looks down its -Z)."""
    return math.atan2(-dx, -dz)


def poly_sd(px, pz, poly):
    """Signed distance to a closed polygon (negative inside) and the nearest edge."""
    best, edge, inside = 1e9, 0, False
    n = len(poly)
    for i in range(n):
        ax, az = poly[i]
        bx, bz = poly[(i + 1) % n]
        d = seg_dist(px, pz, ax, az, bx, bz)
        if d < best:
            best, edge = d, i
        if (az > pz) != (bz > pz) and px < ax + (pz - az) * (bx - ax) / (bz - az):
            inside = not inside
    return (-best if inside else best), edge


def along(px, pz, pts):
    """Nearest point on a polyline of (x, z, y): its distance, its y and how far along (segments)."""
    best = (1e9, 0.0, 0.0)
    for i, ((ax, az, ay), (bx, bz, by)) in enumerate(zip(pts, pts[1:])):
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2)) if L2 else 0.0
        d = math.hypot(px - ax - t * dx, pz - az - t * dz)
        if d < best[0]:
            best = (d, ay + (by - ay) * t, i + t)
    return best


# ------------------------------------------------------------- materials


def material(name, color=0xFFFFFF, rough=0.85, metal=0.0, emit=None, strength=1.0, vcol=False):
    """Principled material. vcol=True takes Base Color from the 'Col' colour attribute."""
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


class Paint:
    """A shading material and the colour it's painted with (baked per vertex)."""

    __slots__ = ("mat", "color")

    def __init__(self, mat, color):
        self.mat = mat
        self.color = color

    def __repr__(self):
        return f"Paint({self.mat.name}, #{self.color:06x})"


def surface(name, rough=0.85, metal=0.0):
    """A vertex-coloured shading material: the colour comes from each Paint."""
    return material(name, 0xFFFFFF, rough=rough, metal=metal, vcol=True)


def palette():
    """Shared palette (docs/ART_PIPELINE.md). Values are Paints, except emissives."""
    wood = surface("wood", rough=0.82)
    stone = surface("stone", rough=0.93)
    iron = surface("iron", rough=0.55, metal=0.6)
    brass = surface("brass", rough=0.3, metal=0.9)
    verdigris = surface("verdigris", rough=0.6, metal=0.4)
    rust = surface("rust", rough=0.88, metal=0.25)
    cloth = surface("cloth", rough=0.96)
    plant = surface("plant", rough=0.65)
    glass = surface("glass", rough=0.1)
    paint = surface("paint", rough=0.55)
    sand = surface("sand", rough=0.97)
    shell = surface("shell", rough=0.42)
    return {
        "timber": Paint(wood, 0x6B4F3A),
        "timber_light": Paint(wood, 0x8A6A4F),
        "timber_pale": Paint(wood, 0xA88A68),
        "driftwood": Paint(wood, 0x9C9384),
        "driftwood_dark": Paint(wood, 0x7D766B),
        "hull": Paint(wood, 0x4A3A2C),
        "hull_dark": Paint(wood, 0x33281F),
        "tar": Paint(wood, 0x241D17),
        "stone": Paint(stone, 0xC9C3B5),
        "stone_dark": Paint(stone, 0xA39E92),
        "rock": Paint(stone, 0x7E7B73),
        "rock_dark": Paint(stone, 0x4E4C47),
        "slate": Paint(stone, 0x3D4A52),
        "iron": Paint(iron, 0x2B2F33),
        "iron_light": Paint(iron, 0x4A5056),
        "rust": Paint(rust, 0x7A4A2E),
        "rust_light": Paint(rust, 0x9A5F38),
        "brass": Paint(brass, 0xB8913A),
        "gilt": Paint(brass, 0xD8B04A),
        "copper": Paint(verdigris, 0x5E8C7A),
        "rope": Paint(cloth, 0xA88F64),
        "cloth": Paint(cloth, 0x8E8166),
        "canvas": Paint(cloth, 0xC8BBA0),
        "leather": Paint(cloth, 0x4A3326),
        "kelp": Paint(plant, 0x3F5A2E),
        "kelp_dark": Paint(plant, 0x2D4224),
        "grass": Paint(plant, 0x8C9461),
        "moss": Paint(plant, 0x56653A),
        "sand": Paint(sand, 0xBFAE86),
        "glass_white": Paint(glass, 0xDDEEEA),
        "glass_green": Paint(glass, 0x8FC9A8),
        "glass_blue": Paint(glass, 0x7FA8C9),
        "glass_amber": Paint(glass, 0xC98A3A),
        "paint_red": Paint(paint, 0xB03A2E),
        "paint_white": Paint(paint, 0xE8E4DA),
        "paint_yellow": Paint(paint, 0xE0B040),
        "paint_blue": Paint(paint, 0x3F6279),
        "barnacle": Paint(shell, 0xD8D2C4),
        "bone": Paint(shell, 0xE9E2CF),
        "lamp": material("lamp", 0xFFF1C9, emit=0xFFB347, strength=2.0),
    }


# ----------------------------------------------------------- mesh builder


def _hemisphere(n, seed=3):
    """Cosine-weighted, stratified directions around +Z."""
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        u = (i + rnd.random()) / n
        phi = 2 * math.pi * ((i * 0.618034 + rnd.random() * 0.2) % 1.0)
        r = math.sqrt(u)
        out.append((r * math.cos(phi), r * math.sin(phi), math.sqrt(max(0.0, 1 - u))))
    return out


class MB:
    """Accumulates primitives (in the object's local GAME space) into one mesh.

    Every primitive takes `mat`: a Paint (vertex-coloured) or a plain material
    (emissive and GLOW_ surfaces). `bev` chamfers the primitive's hard edges
    (metres; None picks a size-relative default, 0 turns it off). `jit` varies
    its colour a little and `tint` scales it, so repeated pieces don't look
    stamped out.
    """

    def __init__(self, seed=0):
        self.bm = bmesh.new()
        self.layer = self.bm.faces.layers.int.new("pc")
        self.mats = []
        self.colors = []
        self.rnd = random.Random(seed)

    # ---- painting

    def _slot(self, mat):
        m = mat.mat if isinstance(mat, Paint) else mat
        if m is None:
            m = palette()["timber"].mat
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def _color(self, mat, jit, tint):
        base = srgb_to_linear(mat.color) if isinstance(mat, Paint) else (1.0, 1.0, 1.0)
        if isinstance(tint, (int, float)):
            tint = (tint, tint, tint)
        k = 1.0 + (self.rnd.random() * 2 - 1) * jit
        warm = (self.rnd.random() * 2 - 1) * jit * 0.35
        c = (base[0] * tint[0] * k * (1 + warm), base[1] * tint[1] * k, base[2] * tint[2] * k * (1 - warm))
        self.colors.append(c)
        return len(self.colors) - 1

    def _paint(self, faces, mat, jit=0.05, tint=1.0):
        mi = self._slot(mat)
        ci = self._color(mat, jit, tint)
        for f in faces:
            f.material_index = mi
            f[self.layer] = ci
        return faces

    def _bevel(self, faces, width, angle=0.75):
        if not width or width <= 0:
            return
        edges = {e for f in faces for e in f.edges}
        sharp = [e for e in edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > angle]
        if sharp:
            bmesh.ops.bevel(self.bm, geom=sharp, offset=width, offset_type="OFFSET", segments=1, profile=0.5, affect="EDGES", clamp_overlap=True)

    @staticmethod
    def _faces_of(verts):
        return list({f for v in verts for f in v.link_faces})

    def _finish(self, verts, mat, bev, jit, tint, auto_bev):
        faces = self._faces_of(verts)
        self._paint(faces, mat, jit, tint)
        self._bevel(faces, auto_bev if bev is None else bev)
        return self

    # ---- primitives

    def box(self, size, at=(0, 0, 0), mat=None, yaw=0.0, pitch=0.0, roll=0.0, centered=False, bev=None, jit=0.05, tint=1.0, cuts=0):
        """size = (x, y-up, z) in game metres. Base sits on `at` unless centered."""
        sx, sy, sz = size
        c = B(*at) + (Vector((0, 0, 0)) if centered else Vector((0, 0, sy / 2)))
        m = Matrix.LocRotScale(c, Euler((pitch, -roll, yaw)), Vector((sx, sz, sy)))
        ret = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        verts = ret["verts"]
        if cuts:
            edges = list({e for v in verts for e in v.link_edges})
            sub = bmesh.ops.subdivide_edges(self.bm, edges=edges, cuts=cuts, use_grid_fill=True)
            verts = list(set(verts) | {g for g in sub["geom"] if isinstance(g, bmesh.types.BMVert)})
        return self._finish(verts, mat, bev, jit, tint, min(0.035, min(size) * 0.12))

    def cyl(self, r1, r2, h, at=(0, 0, 0), mat=None, segs=10, pitch=0.0, yaw=0.0, roll=0.0, centered=False, bev=None, jit=0.05, tint=1.0):
        """Cylinder/cone along game Y (before rotation). Base at `at` unless centered."""
        rot = Euler((pitch, -roll, yaw)).to_matrix().to_4x4()
        off = Vector((0, 0, 0 if centered else h / 2))
        m = Matrix.Translation(B(*at)) @ rot @ Matrix.Translation(off)
        ret = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r1, radius2=r2, depth=h, matrix=m)
        return self._finish(ret["verts"], mat, bev, jit, tint, min(0.03, max(r1, r2) * 0.15, h * 0.15))

    def quad(self, corners, mat=None, jit=0.05, tint=1.0):
        """One face through three or four game points, counter-clockwise seen from the side it faces."""
        verts = [self.bm.verts.new(B(*p)) for p in corners]
        self._paint([self.bm.faces.new(verts)], mat, jit, tint)
        return self

    def sphere(self, r, at=(0, 0, 0), mat=None, scale=(1, 1, 1), subdiv=1, yaw=0.0, pitch=0.0, roll=0.0, jit=0.05, tint=1.0):
        sx, sy, sz = scale
        m = Matrix.LocRotScale(B(*at), Euler((pitch, -roll, yaw)), Vector((sx, sz, sy)))
        ret = bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=r, matrix=m)
        return self._finish(ret["verts"], mat, 0, jit, tint, 0)

    def uvsphere(self, r, at=(0, 0, 0), mat=None, scale=(1, 1, 1), segs=12, rings=8, yaw=0.0, pitch=0.0, roll=0.0, jit=0.05, tint=1.0):
        sx, sy, sz = scale
        m = Matrix.LocRotScale(B(*at), Euler((pitch, -roll, yaw)), Vector((sx, sz, sy)))
        ret = bmesh.ops.create_uvsphere(self.bm, u_segments=segs, v_segments=rings, radius=r, matrix=m)
        return self._finish(ret["verts"], mat, 0, jit, tint, 0)

    def rock(self, r, at=(0, 0, 0), mat=None, seed=0, squash=0.75, jitter=0.28, subdiv=2, cuts=5, flat=0.35, scale=(1, 1, 1), jit=0.06, tint=1.0):
        """A faceted boulder: an icosphere chiselled by a few random planes,
        roughened with noise, squashed and given a flat-ish base."""
        rnd = random.Random(seed)
        ret = bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=1.0, matrix=Matrix.Identity(4))
        verts = ret["verts"]
        planes = []
        for _ in range(cuts):
            n = Vector((rnd.gauss(0, 1), rnd.gauss(0, 1), rnd.gauss(0, 0.6))).normalized()
            planes.append((n, 0.62 + rnd.random() * 0.3))
        for v in verts:
            p = v.co.copy()
            p *= 1.0 + fbm3(p.x * 1.7, p.y * 1.7, p.z * 1.7, seed) * jitter
            for n, d in planes:
                k = p.dot(n) - d
                if k > 0:
                    p -= n * k
            v.co = p
        sx, sy, sz = scale
        rot = Euler((rnd.random() * 0.4 - 0.2, rnd.random() * 0.4 - 0.2, rnd.random() * math.tau))
        m = Matrix.LocRotScale(B(*at), rot, Vector((r * sx, r * sz, r * sy * squash)))
        bmesh.ops.transform(self.bm, matrix=m, verts=verts)
        base = B(*at).z - r * squash * flat
        for v in verts:
            if v.co.z < base:
                v.co.z = base + (v.co.z - base) * 0.15
        return self._finish(verts, mat, 0, jit, tint, 0)

    def lathe(self, profile, at=(0, 0, 0), mat=None, segs=12, yaw=0.0, pitch=0.0, roll=0.0, cap=True, jit=0.05, tint=1.0, bev=0, smooth_ring=False, staves=0.0, arc=None):
        """Revolves a profile of (radius, y) points, bottom to top, around game Y.
        A radius of 0 makes a pole; otherwise the ends are capped (cap=True).
        `staves` > 0 gives each segment column its own shade (barrel staves).
        `arc` = (a0, a1) revolves only part way (radians; game +Z is -pi/2),
        leaving an opening and no caps."""
        rot = Euler((pitch, -roll, yaw)).to_matrix().to_4x4()
        m = Matrix.Translation(B(*at)) @ rot
        n_ring = segs + 1 if arc else segs
        rings = []
        verts = []
        for r, y in profile:
            if r <= 1e-6:
                v = self.bm.verts.new(m @ Vector((0, 0, y)))
                rings.append([v])
                verts.append(v)
                continue
            ring = []
            for i in range(n_ring):
                if arc:
                    a = arc[0] + (arc[1] - arc[0]) * i / segs
                else:
                    a = (i + (0.5 if smooth_ring else 0)) / segs * math.tau
                ring.append(self.bm.verts.new(m @ Vector((math.cos(a) * r, math.sin(a) * r, y))))
            rings.append(ring)
            verts += ring
        if arc:
            cap = False
        columns = [[] for _ in range(segs)]
        for lo, hi in zip(rings, rings[1:]):
            if len(lo) == 1 and len(hi) == 1:
                continue
            for i in range(segs):
                j = (i + 1) % n_ring
                if len(lo) == 1:
                    columns[i].append(self.bm.faces.new((lo[0], hi[j], hi[i])))
                elif len(hi) == 1:
                    columns[i].append(self.bm.faces.new((lo[i], lo[j], hi[0])))
                else:
                    columns[i].append(self.bm.faces.new((lo[i], lo[j], hi[j], hi[i])))
        caps = []
        if cap:
            if len(rings[0]) > 1:
                caps.append(self.bm.faces.new(list(reversed(rings[0]))))
            if len(rings[-1]) > 1:
                caps.append(self.bm.faces.new(rings[-1]))
        if staves > 0:
            for col in columns:
                self._paint(col, mat, jit, tint * (1.0 + (self.rnd.random() * 2 - 1) * staves))
            self._paint(caps, mat, jit, tint)
            self._bevel(self._faces_of(verts), bev)
            return self
        return self._finish(verts, mat, bev, jit, tint, 0)

    def tube(self, points, r, mat=None, segs=6, cap=True, jit=0.05, tint=1.0):
        """A tube along game-space points (rope, chain, cables, tendrils).
        `r` is a radius or a list with one radius per point (tapers)."""
        pts = [B(*p) for p in points]
        radii = r if isinstance(r, (list, tuple)) else [r] * len(pts)
        rings = []
        verts = []
        prev_n = None
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            if prev_n is None:
                n = t.orthogonal().normalized()
            else:
                n = (prev_n - t * prev_n.dot(t)).normalized()
            prev_n = n
            b = t.cross(n)
            ring = []
            for k in range(segs):
                a = k / segs * math.tau
                ring.append(self.bm.verts.new(p + (n * math.cos(a) + b * math.sin(a)) * radii[i]))
            rings.append(ring)
            verts += ring
        for lo, hi in zip(rings, rings[1:]):
            for k in range(segs):
                j = (k + 1) % segs
                self.bm.faces.new((lo[k], lo[j], hi[j], hi[k]))
        if cap:
            self.bm.faces.new(list(reversed(rings[0])))
            self.bm.faces.new(rings[-1])
        return self._finish(verts, mat, 0, jit, tint, 0)

    def loft(self, sections, mat=None, closed=False, cap=False, jit=0.05, tint=1.0, flip=False, strips=None):
        """Skins game-space sections (lists of points, equal counts) in order.
        `closed` joins each section's last point to its first. `strips` paints
        the band between point i and i+1 with strips[i % len] = (paint, tint),
        e.g. a boat's strakes or a painted stripe."""
        rows = [[self.bm.verts.new(B(*p)) for p in s] for s in sections]
        n = len(rows[0])
        everything = []
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            band = []
            for lo, hi in zip(rows, rows[1:]):
                quad = (lo[i], lo[j], hi[j], hi[i])
                band.append(self.bm.faces.new(tuple(reversed(quad)) if flip else quad))
            if strips:
                pm, pt = strips[i % len(strips)]
                self._paint(band, pm, jit, pt)
            everything += band
        caps = []
        if cap and closed:
            caps.append(self.bm.faces.new(list(reversed(rows[0])) if not flip else rows[0]))
            caps.append(self.bm.faces.new(rows[-1] if not flip else list(reversed(rows[-1]))))
        if strips:
            self._paint(caps, strips[0][0], jit, strips[0][1])
        else:
            self._paint(everything + caps, mat, jit, tint)
        return self

    def prism(self, outline, depth, at=(0, 0, 0), mat=None, yaw=0.0, pitch=0.0, roll=0.0, bev=None, jit=0.05, tint=1.0):
        """A flat shape: `outline` is (x, y) points in the game XY plane
        (counter-clockwise seen from +Z), extruded `depth` along Z, centred."""
        rot = Euler((pitch, -roll, yaw)).to_matrix().to_4x4()
        m = Matrix.Translation(B(*at)) @ rot
        front = [self.bm.verts.new(m @ B(x, y, depth / 2)) for x, y in outline]
        back = [self.bm.verts.new(m @ B(x, y, -depth / 2)) for x, y in outline]
        n = len(outline)
        self.bm.faces.new(front)
        self.bm.faces.new(list(reversed(back)))
        for i in range(n):
            j = (i + 1) % n
            self.bm.faces.new((back[i], back[j], front[j], front[i]))
        faces = self._faces_of(front + back)
        bmesh.ops.recalc_face_normals(self.bm, faces=faces)
        return self._finish(front + back, mat, bev, jit, tint, min(0.02, depth * 0.3))

    def plank(self, length, width, thick, at=(0, 0, 0), mat=None, yaw=0.0, pitch=0.0, roll=0.0, warp=0.0, jit=0.07, tint=1.0, bev=None):
        """A board along game X, top face at `at` (like box). `warp` twists it a little."""
        w = (self.rnd.random() - 0.5) * warp
        return self.box((length, thick, width), at=at, mat=mat, yaw=yaw + w * 0.3, pitch=pitch + w * 0.2, roll=roll + w, jit=jit, tint=tint, bev=bev)

    def ring(self, r, thick, at=(0, 0, 0), mat=None, segs=16, tube_segs=5, yaw=0.0, pitch=0.0, roll=0.0, jit=0.04, tint=1.0):
        """A torus in the game XZ plane (barrel hoops, rings, chain links)."""
        pts = []
        for i in range(segs + 1):
            a = i / segs * math.tau
            pts.append((math.cos(a) * r, 0.0, math.sin(a) * r))
        rot = Euler((pitch, -roll, yaw)).to_matrix()
        c = Vector(at)
        world = []
        for p in pts:
            v = rot @ B(*p)
            g = Vector((v.x, v.z, -v.y)) + c
            world.append((g.x, g.y, g.z))
        return self.tube(world, thick, mat=mat, segs=tube_segs, cap=False, jit=jit, tint=tint)

    # ---- output

    def build(self, name, loc=(0, 0, 0), yaw=0.0, roll=0.0, parent=None, props=None, col=False, origin_from_parent=False,
              ao=0.8, ao_dist=None, ao_samples=20, ground=True, grime=0.18, grime_h=0.45, tideline=False, smooth=None, waterline=None):
        """Bakes colour and occlusion into the 'Col' layer and links the object.

        ao        strength of the ambient occlusion (0 = none)
        ground    a ground plane under the object occludes too (props on floors)
        grime     darkening toward the base, over `grime_h` metres
        tideline  wet, darker band below the high-tide line (world height), a
                  pale salt line on it, and weed-dark below low water
        waterline something afloat: wet and darker below this local height
                  (flotsam rides with its origin on the surface: 0)
        smooth    smooth shading with hard edges past this angle (degrees)
        """
        bm = self.bm
        loc_v = B(*loc)
        if tideline:
            # Edge loops exactly at the bands, so the colour change is crisp.
            geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
            for y in (LOW_WATER, HIGH_WATER - 0.06, HIGH_WATER + 0.07):
                z = y - loc_v.z
                ret = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, z), plane_no=(0, 0, 1))
                geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bm.normal_update()
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()

        zs = [v.co.z for v in bm.verts] or [0.0]
        zmin, zmax = min(zs), max(zs)
        shade = [1.0] * len(bm.verts)
        if ao > 0 and bm.faces:
            lo = Vector((min(v.co.x for v in bm.verts), min(v.co.y for v in bm.verts), zmin))
            hi = Vector((max(v.co.x for v in bm.verts), max(v.co.y for v in bm.verts), zmax))
            dist = ao_dist if ao_dist is not None else max(0.18, min(1.6, (hi - lo).length * 0.22))
            bvh = BVHTree.FromBMesh(bm)
            dirs = _hemisphere(ao_samples)
            gz = zmin if ground else None
            for v in bm.verts:
                n = v.normal
                if n.length_squared < 1e-12:
                    continue
                t = n.orthogonal().normalized()
                b = n.cross(t)
                o = v.co + n * 0.004
                occ = 0.0
                for dx, dy, dz in dirs:
                    d = t * dx + b * dy + n * dz
                    hit = bvh.ray_cast(o, d, dist)
                    if hit[0] is not None:
                        occ += 1.0 - 0.5 * (hit[3] / dist)
                    elif gz is not None and d.z < -1e-3:
                        tg = (gz - o.z) / d.z
                        if 0 < tg < dist:
                            occ += 1.0 - 0.5 * (tg / dist)
                shade[v.index] = 1.0 - ao * occ / len(dirs)
        for v in bm.verts:
            h = v.co.z - zmin
            shade[v.index] *= 1.0 - grime * (1.0 - smoothstep(0.0, grime_h, h))

        wet = None
        if waterline is not None:
            wet = []
            for v in bm.verts:
                d = waterline - v.co.z + (vnoise3(v.co.x * 3.1, v.co.y * 3.1, 0.5, 11) - 0.5) * 0.03
                k = smoothstep(-0.01, 0.04, d)
                wet.append((1.0 - 0.4 * k, 1.0 - 0.33 * k, 1.0 - 0.38 * k))
        if tideline:
            wet = []
            for v in bm.verts:
                wy = v.co.z + loc_v.z + (vnoise3(v.co.x * 2.1, v.co.y * 2.1, 0.5, 9) - 0.5) * 0.05
                if wy < LOW_WATER:
                    wet.append((0.42, 0.52, 0.4))
                elif wy < HIGH_WATER - 0.05:
                    k = 0.55 + 0.12 * smoothstep(LOW_WATER, HIGH_WATER, wy)
                    wet.append((k * 0.92, k * 0.98, k * 0.86))
                elif wy < HIGH_WATER + 0.06:
                    wet.append((1.18, 1.17, 1.12))
                else:
                    wet.append((1.0, 1.0, 1.0))

        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        n_loops = len(me.loops)
        pcs = [0] * len(me.polygons)
        if "pc" in me.attributes:
            me.attributes["pc"].data.foreach_get("value", pcs)
            me.attributes.remove(me.attributes["pc"])
        cols = [0.0] * (n_loops * 4)
        loop_vert = [0] * n_loops
        me.loops.foreach_get("vertex_index", loop_vert)
        for p in me.polygons:
            c = self.colors[pcs[p.index]] if self.colors else (1.0, 1.0, 1.0)
            for li in p.loop_indices:
                vi = loop_vert[li]
                s = shade[vi]
                r, g, b = c[0] * s, c[1] * s, c[2] * s
                if wet is not None:
                    w = wet[vi]
                    r, g, b = r * w[0], g * w[1], b * w[2]
                k = li * 4
                cols[k] = min(1.0, max(0.0, r))
                cols[k + 1] = min(1.0, max(0.0, g))
                cols[k + 2] = min(1.0, max(0.0, b))
                cols[k + 3] = 1.0
        attr = me.color_attributes.new(name="Col", type="BYTE_COLOR", domain="CORNER")
        attr.data.foreach_set("color", cols)
        me.color_attributes.active_color = attr
        bm.free()
        for m in self.mats:
            me.materials.append(m)
        if smooth is not None:
            me.shade_smooth()
            me.set_sharp_from_angle(angle=math.radians(smooth))
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        if parent is not None:
            ob.parent = parent
        ob.location = loc_v
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


def hull_sections(stations, strakes, overlap=0.014):
    """Clinker hull sections from (z, half_beam, depth, keel_y, fullness)
    stations: each a list of game points across the boat, port gunwale to
    starboard gunwale, every strake stepping out over the one below."""
    out = []
    for z, b, d, yk, full in stations:
        half = []
        for j in range(strakes + 1):
            s = j / strakes
            # Quadratic Bezier keel -> bilge -> gunwale; `full` pushes the bilge out.
            p0, p1, p2 = (0.0, yk), (b * full, yk), (b, yk + d)
            x = (1 - s) ** 2 * p0[0] + 2 * (1 - s) * s * p1[0] + s * s * p2[0]
            y = (1 - s) ** 2 * p0[1] + 2 * (1 - s) * s * p1[1] + s * s * p2[1]
            half.append((x, y))
        pts = []
        for j, (x, y) in enumerate(half):
            if 0 < j < strakes:
                nx, ny = half[j + 1][1] - half[j - 1][1], -(half[j + 1][0] - half[j - 1][0])
                L = math.hypot(nx, ny) or 1
                pts.append((x, y))
                pts.append((x + nx / L * overlap, y + ny / L * overlap - 0.004))
            else:
                pts.append((x, y))
        full_pts = [(-x, y, z) for x, y in reversed(pts)] + [(x, y, z) for x, y in pts[1:]]
        out.append(full_pts)
    return out


# --------------------------------------------------------------- props


def load_props():
    """PROP_ templates from props.blend, keyed by id (locations place copies)."""
    # Everything comes across (children of a prop too); only what place() links is exported.
    with bpy.data.libraries.load(os.path.join(ROOT, "art/blender/props/props.blend"), link=False) as (src, dst):
        dst.objects = list(src.objects)
    return {o.name[5:]: o for o in dst.objects if o is not None and o.name.startswith("PROP_")}


def load_home():
    """HOME_ templates from home.blend, keyed by name without the prefix (the home map places copies)."""
    with bpy.data.libraries.load(os.path.join(ROOT, "art/blender/home/home.blend"), link=False) as (src, dst):
        dst.objects = list(src.objects)
    return {o.name[5:]: o for o in dst.objects if o is not None and o.name.startswith("HOME_") and o.parent is None}


def merge_materials():
    """Folds the copies appending brings (wood.001 ...) into the originals, so a
    level exports each material once and the game's batching can merge it."""
    for m in list(bpy.data.materials):
        base, dot, num = m.name.rpartition(".")
        if dot and num.isdigit() and base in bpy.data.materials:
            m.user_remap(bpy.data.materials[base])
            bpy.data.materials.remove(m)


def _copy_children(src, dst):
    for c in src.children:
        cc = c.copy()
        bpy.context.scene.collection.objects.link(cc)
        cc.parent = dst
        cc.matrix_parent_inverse = c.matrix_parent_inverse.copy()
        _copy_children(c, cc)


def place(templates, kind, name, at, yaw=0.0, props=None, scale=1.0, parent=None):
    """A linked duplicate of a PROP_ template (shares its meshes, children too) at game point `at`."""
    t = templates[kind]
    ob = t.copy()
    ob.name = name
    bpy.context.scene.collection.objects.link(ob)
    _copy_children(t, ob)
    if parent is not None:
        ob.parent = parent
    ob.location = B(*at)
    ob.rotation_euler = (0, 0, yaw)
    ob.scale = (scale, scale, scale) if isinstance(scale, (int, float)) else (scale[0], scale[2], scale[1])
    for k, v in (props or {}).items():
        ob[k] = v
    return ob


# --------------------------------------------------------------- terrain


def terrain(name, x0, x1, z0, z1, step, height, color, mat, props=None, shade=True):
    """Heightfield grid in game space. height(x, z) -> y; color(x, z, y) -> 0xRRGGBB.

    shade=True darkens hollows and steep faces a touch (cheap terrain AO)."""
    bm = bmesh.new()
    nx = int(round((x1 - x0) / step)) + 1
    nz = int(round((z1 - z0) / step)) + 1
    hs = [[height(x0 + i * step, z0 + j * step) for i in range(nx)] for j in range(nz)]
    grid = []
    for j in range(nz):
        z = z0 + j * step
        grid.append([bm.verts.new(B(x0 + i * step, hs[j][i], z)) for i in range(nx)])
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

    occl = {}
    if shade:
        for j in range(nz):
            for i in range(nx):
                h = hs[j][i]
                ring = []
                for dj, di in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)):
                    jj, ii = min(nz - 1, max(0, j + dj)), min(nx - 1, max(0, i + di))
                    ring.append(hs[jj][ii])
                cav = sum(ring) / len(ring) - h  # > 0 in hollows
                gx = hs[j][min(nx - 1, i + 1)] - hs[j][max(0, i - 1)]
                gz = hs[min(nz - 1, j + 1)][i] - hs[max(0, j - 1)][i]
                slope = math.hypot(gx, gz) / (2 * step)
                occl[(i, j)] = max(0.62, 1.0 - max(0.0, cav) * 0.22 - smoothstep(0.6, 2.5, slope) * 0.18)

    attr = me.color_attributes.new(name="Col", type="BYTE_COLOR", domain="CORNER")
    rnd = random.Random(1)
    cols = [0.0] * (len(me.loops) * 4)
    for loop in me.loops:
        vi = loop.vertex_index
        co = me.vertices[vi].co
        gx, gy, gz = co.x, co.z, -co.y
        r, g, b = srgb_to_linear(color(gx, gz, gy))
        n = 1.0 + (rnd.random() - 0.5) * 0.08
        s = occl.get((vi % nx, vi // nx), 1.0) * n
        k = loop.index * 4
        cols[k], cols[k + 1], cols[k + 2], cols[k + 3] = min(1, r * s), min(1, g * s), min(1, b * s), 1.0
    attr.data.foreach_set("color", cols)

    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for k, v in (props or {}).items():
        ob[k] = v
    return ob


# --------------------------------------------------------------- masonry
# Mortared stone: a dark mortar face with coursed stones a little proud of it,
# coping slabs over the top. Every wall has a plain collision box behind its
# face, so the terrain's one-metre step under it never decides where you stop.


def slab(m, p, q, h, depth, mat, tint=1.0):
    """A slab from game point p to q (its top edge's centre line), h thick, depth across."""
    dx, dy, dz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
    m.box((math.hypot(dx, dz), h, depth), at=((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 - h / 2, (p[2] + q[2]) / 2), mat=mat,
          yaw=math.atan2(-dz, dx), roll=math.atan2(dy, math.hypot(dx, dz)), centered=True, bev=0, tint=tint)


class Masonry:
    """Walls drawn into one model (`walls`) and their collision into another
    (`solids`); build() makes the pair. `rng` lays the stones unless a wall
    brings its own dice."""

    def __init__(self, P, rng, seeds=(900, 901)):
        stone = P["stone"].mat
        self.rng = rng
        self.walls, self.solids = MB(seeds[0]), MB(seeds[1])
        self.tar = P["tar"]
        self.mortar = Paint(stone, 0x57524A)
        self.coursed = [Paint(stone, c) for c in (0x9C968A, 0x8E887C, 0xA7A194, 0x857F73, 0x948C7C, 0xACA596)]
        self.copings = [Paint(stone, c) for c in (0xB4AEA1, 0xA8A294, 0xBDB7A9)]

    def face(self, a, b, out, foot, top, rng):
        """Coursed stone on a vertical face from a to b (x, z). `out` is the face's
        outward normal (x, z); foot and top are heights at a and at b."""
        m = self.walls
        (ax, az), (bx, bz) = a, b
        L = math.hypot(bx - ax, bz - az)
        ux, uz = (bx - ax) / L, (bz - az) / L
        if -uz * out[0] + ux * out[1] < 0:  # walk the face the way that makes its quads look out
            (ax, az), (bx, bz), ux, uz = (bx, bz), (ax, az), -ux, -uz
            foot, top = (foot[1], foot[0]), (top[1], top[0])
        nx, nz = out

        def pt(s, y, pro):
            return (ax + ux * s + nx * pro, y, az + uz * s + nz * pro)

        def lo(s):
            return lerp(foot[0], foot[1], s / L)

        def hi(s):
            return lerp(top[0], top[1], s / L)

        m.quad([pt(0, lo(0), 0), pt(L, lo(L), 0), pt(L, hi(L), 0), pt(0, hi(0), 0)], mat=self.mortar, jit=0.03)
        y0 = min(foot)
        while y0 < max(top) - 0.05:
            ch = 0.28 + rng.random() * 0.17
            s = -rng.random() * 0.6
            while s < L:
                sl = 0.45 + rng.random() * 0.75
                s0, s1 = max(0.0, s) + 0.022, min(L, s + sl) - 0.022
                s += sl
                if s1 - s0 < 0.12:
                    continue
                b0, b1 = max(y0 + 0.022, lo(s0)), max(y0 + 0.022, lo(s1))
                t0, t1 = min(y0 + ch - 0.022, hi(s0) - 0.03), min(y0 + ch - 0.022, hi(s1) - 0.03)
                if t0 - b0 < 0.06 or t1 - b1 < 0.06:
                    continue
                pro = 0.012 + rng.random() * 0.03
                m.quad([pt(s0, b0, pro), pt(s1, b1, pro), pt(s1, t1, pro), pt(s0, t0, pro)], mat=self.coursed[int(rng.random() * len(self.coursed))], jit=0.06, tint=0.82 + 0.3 * rng.random())
            y0 += ch

    def coping(self, a, b, out, top, back, rng, over=0.07, thick=0.16):
        """Coping slabs along a wall's top from a to b, from `back` behind the face to `over` in front."""
        (ax, az), (bx, bz) = a, b
        L = math.hypot(bx - ax, bz - az)
        ux, uz = (bx - ax) / L, (bz - az) / L
        c = (over - back) / 2
        s = 0.0
        while s < L - 0.05:
            sl = min(0.7 + rng.random() * 0.5, L - s)
            p = (ax + ux * s + out[0] * c, lerp(top[0], top[1], s / L), az + uz * s + out[1] * c)
            q = (ax + ux * (s + sl - 0.02) + out[0] * c, lerp(top[0], top[1], (s + sl - 0.02) / L), az + uz * (s + sl - 0.02) + out[1] * c)
            slab(self.walls, p, q, thick, back + over, self.copings[int(rng.random() * len(self.copings))], tint=0.85 + 0.25 * rng.random())
            s += sl

    def solid(self, a, b, out, foot, top, back):
        """The collision behind a wall face: a box hung from its top edge, deep enough to reach its foot."""
        (ax, az), (bx, bz) = a, b
        h = max(top[0] - foot[0], top[1] - foot[1]) + 0.3
        p = (ax - out[0] * back / 2, top[0], az - out[1] * back / 2)
        q = (bx - out[0] * back / 2, top[1], bz - out[1] * back / 2)
        slab(self.solids, p, q, h, back, self.tar)

    def retaining(self, a, b, out, foot, top, back=0.95, rng=None):
        """A retaining wall: face, coping and collision. foot and top are (at a, at b)."""
        rng = rng or self.rng
        self.face(a, b, out, foot, top, rng)
        self.coping(a, b, out, (top[0] + 0.04, top[1] + 0.04), back + 0.1, rng)
        self.solid(a, b, out, foot, (top[0] + 0.04, top[1] + 0.04), back)

    def parapet(self, a, b, base, rng=None, h=0.9, w=0.45):
        """A free-standing wall on top of another, faced both sides."""
        rng = rng or self.rng
        (ax, az), (bx, bz) = a, b
        L = math.hypot(bx - ax, bz - az)
        nx, nz = (bz - az) / L, -(bx - ax) / L
        for s in (1, -1):
            o = (nx * s, nz * s)
            self.face((ax + o[0] * w / 2, az + o[1] * w / 2), (bx + o[0] * w / 2, bz + o[1] * w / 2), o, (base, base), (base + h, base + h), rng)
        self.coping((ax + nx * w / 2, az + nz * w / 2), (bx + nx * w / 2, bz + nz * w / 2), (nx, nz), (base + h + 0.1, base + h + 0.1), w + 0.07, rng, over=0.05, thick=0.12)
        slab(self.solids, (ax, base + h + 0.1, az), (bx, base + h + 0.1, bz), h + 0.1, w, self.tar)

    def build(self, name, col_name, **kw):
        """The walls as `name` (MB.build's look arguments in kw) and their collision as `col_name`."""
        walls = self.walls.build(name, ground=False, **kw)
        self.solids.build(col_name, ao=0, grime=0, ground=False)
        return walls


class Boulders:
    """home.blend's unit boulders (HOME_rock_<n>) set into a level whose ground
    is `height(x, z)`: bedded in the ground, or, where it falls away, sea rocks
    stood on the sea floor and stretched up clear of high water. Too tall to
    climb onto from the water and kept back from the shore (shrunk if they must
    be), so never a perch to be stranded on."""

    def __init__(self, templates, height, rng, sea_rock=-0.7, gap=1.8, name="rock"):
        self.templates, self.height, self.rng = templates, height, rng
        self.sea_rock = sea_rock  # ground lower than this, and a boulder is a sea rock instead
        self.gap = gap  # the least water between a sea rock and the shore
        self.name, self.count = name, 0

    def _place(self, kind, at, yaw, scale):
        place(self.templates, kind, f"{self.name}_{self.count:03d}", at, yaw=yaw, scale=scale, props={"col": 1})
        self.count += 1

    def sea_room(self, x, z):
        """How far it is from (x, z) to the nearest ground above the sea floor (up to 9 m)."""
        for k in range(2, 19):
            r = k * 0.5
            for j in range(16):
                a = j * math.tau / 16
                if self.height(x + math.cos(a) * r, z + math.sin(a) * r) > self.sea_rock:
                    return r
        return 9.0

    def boulder(self, x, z, s, sink=0.4):
        rng = self.rng
        kind = f"rock_{int(rng.random() * 6)}"
        yaw, w, h = rng.random() * math.tau, 0.9 + rng.random() * 0.3, 0.75 + rng.random() * 0.35
        ground = self.height(x, z)
        if ground > self.sea_rock:
            self._place(kind, (x, ground - s * sink, z), yaw, (s * w, s * h, s))
            return
        # In clusters with open water between, big and small, not a string of beads.
        group = noise2(x * 0.22, z * 0.22, 103)
        if group < -0.15:
            return
        box = self.templates[kind].bound_box
        reach = max(max(abs(c[0]) for c in box) * w, max(abs(c[1]) for c in box))
        s = min(max(s, 2.4) * (0.7 + 0.9 * group), (self.sea_room(x, z) - self.gap) / reach)
        if s < 1.4:
            return
        lo, hi = min(c[2] for c in box), max(c[2] for c in box)
        top = HIGH_WATER + 0.5 + 0.6 * (noise2(x * 0.7, z * 0.7, 101) + 1.0)
        tall = (top - ground) / (hi - lo)
        self._place(kind, (x, ground - lo * tall, z), yaw, (s * w, tall, s))

    def stack(self, x, z, top, size, sea_floor):
        """A sea stack: boulders piled and stretched up out of deep water to `top`."""
        rng = self.rng
        y, r = self.height(x, z), size
        for k in range(4):
            if y > top - 0.6:
                break
            kind = f"rock_{int(rng.random() * 6)}"
            box = self.templates[kind].bound_box
            lo, hi = min(c[2] for c in box), max(c[2] for c in box)
            h = min(top - y, (top - sea_floor) * (0.6 if k == 0 else 0.4)) + 0.6
            tall = h / (hi - lo)
            self._place(kind, (x + rng.uniform(-0.3, 0.3) * size, y - lo * tall - 0.3, z + rng.uniform(-0.3, 0.3) * size), rng.random() * math.tau,
                        (r * (0.9 + 0.3 * rng.random()), tall, r))
            y += h - 0.6
            r *= 0.7


def pave(m, x0, x1, z0, z1, y_of, rng, stones, row=(0.42, 0.62), width=(0.5, 0.95), keep=None, gap=0.035, lift=0.03):
    """Stone setts in rows across x, each corner on the ground under it."""
    z = z0
    while z < z1 - 0.1:
        rh = min(row[0] + rng.random() * (row[1] - row[0]), z1 - z)
        x = x0 - rng.random() * width[0]
        while x < x1:
            sw = width[0] + rng.random() * (width[1] - width[0])
            a, b = max(x0, x) + gap, min(x1, x + sw) - gap
            c, d = z + gap, z + rh - gap
            x += sw
            if b - a < 0.15 or (keep and not keep((a + b) / 2, (c + d) / 2)):
                continue
            up = lift + rng.random() * 0.025
            m.quad([(a, y_of(a, c) + up, c), (a, y_of(a, d) + up, d), (b, y_of(b, d) + up, d), (b, y_of(b, c) + up, c)],
                   mat=stones[int(rng.random() * len(stones))], jit=0.06, tint=0.78 + 0.34 * rng.random())
        z += rh


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
    tris = sum(len(o.data.loop_triangles) for o in keep if o.type == "MESH" and (o.data.calc_loop_triangles() or True))
    print(f"[export] wrote {path} ({len(keep)} objects, {tris} triangles)")


def save_and_export(blend_rel, glb_rel):
    blend = os.path.join(ROOT, blend_rel)
    os.makedirs(os.path.dirname(blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    print(f"[build] saved {blend}")
    export_glb(os.path.join(ROOT, glb_rel))
