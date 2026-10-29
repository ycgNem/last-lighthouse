"""Renders review sheets of built art so it can be checked by eye (EEVEE, headless).

Objects: every top-level object whose name starts with a prefix, each framed on
its own, one tile per view, labelled with its size, laid out on one sheet.

    blender -b art/blender/props/props.blend --python tools/blender/review.py -- .previews/props.png --prefix PROP_ --views 2

Shots: camera positions in game space (x, y-up, z), e.g. eye-level views of a
location, optionally with the sea at a given height.

    blender -b art/blender/locations/wreck.blend --python tools/blender/review.py -- .previews/wreck.png --shots shots.json --water 1.8

shots.json: [{"name": "landing", "eye": [-35, 4.6, 4], "look": [-20, 4, -6], "fov": 70}, ...]

Other flags: --only a,b,c (exact names)  --cols N  --tile 420x320  --az 35  --el 22
             --bg 0d1318  --ground 0|1  --show-col (draw COL_ collision boxes)
"""

import json
import math
import os
import sys
import tempfile

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.abspath(argv[0]) if argv else os.path.abspath("review.png")


def flag(name, default=None):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else default


prefix = flag("--prefix", "")
only = [s for s in (flag("--only") or "").split(",") if s]
views = max(1, int(flag("--views", "1")))
cols = int(flag("--cols", "0"))
tile_w, tile_h = (int(v) for v in flag("--tile", "420x320").split("x"))
az0 = float(flag("--az", "35"))
el0 = float(flag("--el", "22"))
bg = flag("--bg", "0d1318")
show_ground = flag("--ground", "1") == "1"
shots_file = flag("--shots")
water = flag("--water")


def B(x, y, z):
    return Vector((x, -z, y))


def hexcol(h):
    v = int(h, 16)

    def ch(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return (ch((v >> 16) & 255), ch((v >> 8) & 255), ch(v & 255))


scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = tile_w
scene.render.resolution_y = tile_h
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.render.image_settings.file_format = "PNG"
try:
    scene.view_settings.view_transform = "AgX"
except TypeError:
    pass
if scene.world is None:
    scene.world = bpy.data.worlds.new("review_world")
scene.world.use_nodes = True
bgn = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
bgn.inputs["Color"].default_value = (*hexcol(bg), 1.0)
bgn.inputs["Strength"].default_value = 1.0


def sun(name, color, energy, rot):
    d = bpy.data.lights.new(name, "SUN")
    d.color = color
    d.energy = energy
    d.angle = math.radians(6)
    o = bpy.data.objects.new(name, d)
    scene.collection.objects.link(o)
    o.rotation_euler = tuple(math.radians(a) for a in rot)
    return o


sun("_key", (1.0, 0.9, 0.78), 3.2, (50, 0, -35))
sun("_fill", (0.7, 0.82, 1.0), 0.9, (65, 0, 120))
sun("_rim", (0.85, 0.95, 1.0), 1.6, (-60, 0, 200))

cam_data = bpy.data.cameras.new("_review_cam")
cam_data.lens = 50
cam = bpy.data.objects.new("_review_cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

label_mat = bpy.data.materials.new("_label")
label_mat.use_nodes = True
lnt = label_mat.node_tree
for node in list(lnt.nodes):
    lnt.nodes.remove(node)
em = lnt.nodes.new("ShaderNodeEmission")
em.inputs["Color"].default_value = (1, 1, 1, 1)
lout = lnt.nodes.new("ShaderNodeOutputMaterial")
lnt.links.new(em.outputs[0], lout.inputs["Surface"])
label_curve = bpy.data.curves.new("_label", "FONT")
label_curve.materials.append(label_mat)
label = bpy.data.objects.new("_label", label_curve)
scene.collection.objects.link(label)
label.parent = cam


def set_label(text):
    label_curve.body = text or " "
    d = 1.0
    if cam_data.sensor_fit == "VERTICAL":
        half_h = d * (cam_data.sensor_height / 2) / cam_data.lens
        half_w = half_h * tile_w / tile_h
    else:
        half_w = d * (cam_data.sensor_width / 2) / cam_data.lens
        half_h = half_w * tile_h / tile_w
    label_curve.size = half_h * 0.1
    label.location = (-half_w * 0.95, -half_h * 0.93, -d)


ground = None
if show_ground and not shots_file:
    gm = bpy.data.meshes.new("_ground")
    gm.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new("_ground", gm)
    scene.collection.objects.link(ground)
    gmat = bpy.data.materials.new("_ground")
    gb = next(n for n in gmat.node_tree.nodes if n.type == "BSDF_PRINCIPLED") if gmat.node_tree else None
    if gb is None:
        gmat.use_nodes = True
        gb = next(n for n in gmat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    gb.inputs["Base Color"].default_value = (*hexcol("26313a"), 1)
    gb.inputs["Roughness"].default_value = 0.9
    gm.materials.append(gmat)

if water is not None:
    wy = float(water)
    s = 3000
    wm = bpy.data.meshes.new("_water")
    wm.from_pydata([(-s, -s, wy), (s, -s, wy), (s, s, wy), (-s, s, wy)], [], [(0, 1, 2, 3)])
    wo = bpy.data.objects.new("_water", wm)
    scene.collection.objects.link(wo)
    wmat = bpy.data.materials.new("_water")
    if wmat.node_tree is None:
        wmat.use_nodes = True
    wb = next(n for n in wmat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    wb.inputs["Base Color"].default_value = (*hexcol("1f5f68"), 1)
    wb.inputs["Roughness"].default_value = 0.12
    wm.materials.append(wmat)

helpers = {o for o in scene.objects if o.name.startswith("_")}
# Collision boxes aren't drawn in the game.
for o in scene.objects:
    if o.name.startswith("COL_") and "--show-col" not in argv:
        o.hide_render = True
        helpers.add(o)


def descendants(o):
    out_list = [o]
    for c in o.children:
        out_list += descendants(c)
    return out_list


def bounds(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    found = False
    for o in objs:
        if o.type not in {"MESH", "CURVE", "FONT"}:
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
            found = True
    return (lo, hi) if found else (Vector((-1, -1, -1)), Vector((1, 1, 1)))


def aim(eye, target):
    cam.location = eye
    cam.rotation_euler = (target - eye).to_track_quat("-Z", "Y").to_euler()


tmp = tempfile.mkdtemp(prefix="review_")
tiles = []


def render_tile():
    path = os.path.join(tmp, f"{len(tiles):03d}.png")
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    tiles.append(path)


if shots_file:
    with open(shots_file) as f:
        shots = json.load(f)
    cam_data.sensor_fit = "VERTICAL"
    cam_data.sensor_height = 24
    cam_data.clip_start = 0.05
    cam_data.clip_end = 3000
    for s in shots:
        fov = math.radians(s.get("fov", 70))
        cam_data.lens = (cam_data.sensor_height / 2) / math.tan(fov / 2)
        aim(B(*s["eye"]), B(*s["look"]))
        set_label(s["name"])
        render_tile()
    per_row = cols or 2
else:
    targets = [o for o in scene.objects if o.parent is None and o not in helpers and o.type in {"MESH", "EMPTY"}]
    targets = [o for o in targets if o.name in only] if only else [o for o in targets if o.name.startswith(prefix)]
    targets.sort(key=lambda o: o.name)
    angles = [(az0, el0), (az0 + 180, el0), (az0 + 90, 6), (az0, 75)][:views]
    fov = 2 * math.atan((cam_data.sensor_width / 2) / cam_data.lens)
    for t in targets:
        group = set(descendants(t))
        for o in scene.objects:
            if o not in helpers:
                o.hide_render = o not in group
        lo, hi = bounds(group)
        center = (lo + hi) / 2
        radius = max((hi - lo).length / 2, 0.1)
        if ground is not None:
            ground.location = (center.x, center.y, lo.z - 0.001)
            ground.scale = (radius * 10, radius * 10, 1)
        dist = radius / math.sin(fov * min(1.0, tile_h / tile_w) / 2) * 1.02
        cam_data.clip_start = dist * 0.01
        cam_data.clip_end = dist * 20
        for k, (az, el) in enumerate(angles):
            a, e = math.radians(az), math.radians(el)
            direction = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
            aim(center + direction * dist, center)
            size = hi - lo
            set_label(f"{t.name}   {size.x:.2f} x {size.z:.2f} x {size.y:.2f} m" if k == 0 else "")
            render_tile()
    per_row = cols or (views * max(1, 4 // views) if views > 1 else 5)

# Contact sheet (Blender's pixel rows run bottom to top).
n = len(tiles)
per_row = max(1, min(per_row, n))
rows = math.ceil(n / per_row)
W, H = per_row * tile_w, rows * tile_h
sheet_px = np.zeros((H, W, 4), dtype=np.float32)
sheet_px[..., :3] = 0.03
sheet_px[..., 3] = 1.0
for i, path in enumerate(tiles):
    img = bpy.data.images.load(path)
    arr = np.empty(tile_w * tile_h * 4, dtype=np.float32)
    img.pixels.foreach_get(arr)
    r, c = divmod(i, per_row)
    ox, oy = c * tile_w, (rows - 1 - r) * tile_h
    sheet_px[oy:oy + tile_h, ox:ox + tile_w] = arr.reshape(tile_h, tile_w, 4)
    sheet_px[oy:oy + tile_h, ox:ox + 1, :3] = 0.0
    bpy.data.images.remove(img)
sheet = bpy.data.images.new("_sheet", W, H, alpha=False)
sheet.pixels.foreach_set(sheet_px.ravel())
os.makedirs(os.path.dirname(out), exist_ok=True)
sheet.filepath_raw = out
sheet.file_format = "PNG"
sheet.save()
print(f"[review] wrote {out} ({n} tiles)")
