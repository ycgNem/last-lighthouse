"""Export the open .blend to a .glb the game can read.

Python because Blender's scripting API is Python-only; everything else in the
project is TypeScript.

Usage (headless):
    blender -b art/blender/locations/wreck.blend --python tools/blender/export_gltf.py -- public/assets/models/locations/wreck.glb

Rules (see docs/ART_PIPELINE.md): objects starting with "_" and anything in a
collection named "_ignore" are skipped; modifiers are applied; +Y up; custom
properties are exported as glTF extras; marker objects are checked for their
required custom properties.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import bpy  # noqa: E402
import kit  # noqa: E402


def out_path() -> str:
    argv = sys.argv
    if "--" not in argv or argv.index("--") + 1 >= len(argv):
        raise SystemExit("export_gltf.py: pass the output path after --")
    return os.path.abspath(argv[argv.index("--") + 1])


if bpy.context.object and bpy.context.object.mode != "OBJECT":
    bpy.ops.object.mode_set(mode="OBJECT")
kit.export_glb(out_path())
