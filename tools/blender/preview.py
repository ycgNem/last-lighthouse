"""Render a quick Workbench preview of a .blend (for checking models by eye).

    blender -b art/blender/props/props.blend --python tools/blender/preview.py -- out.png [azimuth_deg elevation_deg] [object_prefix]
"""

import math
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = args[0] if args else "//preview.png"
az = math.radians(float(args[1])) if len(args) > 1 else math.radians(35)
el = math.radians(float(args[2])) if len(args) > 2 else math.radians(30)
prefix = args[3] if len(args) > 3 else ""

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.render.resolution_x = 1400
scene.render.resolution_y = 800
scene.render.film_transparent = False
if scene.world is None:
    scene.world = bpy.data.worlds.new("w")
scene.world.color = (0.05, 0.08, 0.1)

objs = [o for o in scene.objects if o.type == "MESH" and not o.name.startswith("_") and o.name.startswith(prefix) or (prefix and o.parent and o.parent.name.startswith(prefix) and o.type == "MESH")]
lo = Vector((1e9, 1e9, 1e9))
hi = Vector((-1e9, -1e9, -1e9))
for o in objs:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, w))
        hi = Vector(map(max, hi, w))
center = (lo + hi) / 2
radius = max((hi - lo).length / 2, 0.5)

cam_data = bpy.data.cameras.new("preview_cam")
cam_data.lens = 35
cam = bpy.data.objects.new("preview_cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
direction = Vector((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)))
cam.location = center + direction * radius * 2.4
cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
cam_data.clip_end = radius * 20

scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("[preview] wrote", out)
