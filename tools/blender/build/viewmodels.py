"""Builds art/blender/viewmodels/viewmodels.blend and public/assets/models/viewmodels.glb.

First-person models. Game space with the camera looking down -Z: barrels point
-Z, the right hand is +X. Each model is a top-level object VM_<id> with empties
for attach points (muzzle, flame, tip).

    blender -b --factory-startup --python tools/blender/build/viewmodels.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import kit  # noqa: E402
from kit import MB  # noqa: E402

kit.reset()
P = kit.palette()
amber = kit.material("bolt_amber", 0xFFC46B, rough=0.2, emit=0xFFB347, strength=3.0)
grip = kit.material("grip_leather", 0x4A3326, rough=0.8)
gold = kit.material("gilt", 0xD8B04A, rough=0.25, metal=1.0)

FWD = -math.pi / 2  # pitch that points a Y-axis cylinder down game -Z


def boltcaster(name, x, tier):
    m = MB()
    body = P["timber"] if tier == 1 else P["hull_dark"]
    trim = P["brass"] if tier < 3 else gold
    # Stock and grip.
    m.box((0.07, 0.11, 0.24), at=(0, -0.06, 0.12), mat=body, pitch=0.1, centered=True)
    m.box((0.05, 0.14, 0.06), at=(0, -0.13, 0.03), mat=grip, pitch=-0.35, centered=True)
    # Receiver with the glowing bolt chamber.
    m.box((0.085, 0.09, 0.3), at=(0, 0.0, -0.12), mat=body, centered=True)
    m.box((0.095, 0.02, 0.32), at=(0, 0.05, -0.12), mat=trim, centered=True)
    m.cyl(0.032, 0.032, 0.16, at=(0, 0.075, -0.08), mat=amber, segs=10, pitch=FWD, centered=True)
    # Barrel.
    length = 0.36 + 0.06 * tier
    m.cyl(0.022, 0.026, length, at=(0, 0.01, -0.27 - length / 2), mat=P["iron"], segs=10, pitch=FWD, centered=True)
    if tier >= 2:
        m.cyl(0.034, 0.034, 0.14, at=(0, 0.01, -0.32), mat=trim, segs=10, pitch=FWD, centered=True)
    # Vanes at the muzzle.
    for a in range(3):
        ang = a / 3 * math.tau
        m.box((0.012, 0.05, 0.07), at=(math.cos(ang) * 0.03, 0.01 + math.sin(ang) * 0.03, -0.27 - length + 0.04), mat=trim, roll=ang, centered=True)
    if tier == 3:
        m.cyl(0.05, 0.05, 0.06, at=(0, 0.01, -0.27 - length - 0.02), mat=amber, segs=10, pitch=FWD, centered=True)
    ob = m.build(name, loc=(x, 0, 0))
    kit.empty("muzzle", (0, 0.01, -0.29 - length), parent=ob, size=0.05)
    return ob


def lantern():
    m = MB()
    m.cyl(0.06, 0.07, 0.02, at=(0, -0.1, 0), mat=P["iron"], segs=8)
    m.cyl(0.05, 0.05, 0.14, at=(0, -0.08, 0), mat=kit.material("lantern_glass", 0xFFE7B0, rough=0.15, emit=0xFFB347, strength=2.5), segs=8)
    for i in range(4):
        a = i / 4 * math.tau + math.pi / 4
        m.box((0.008, 0.16, 0.008), at=(math.cos(a) * 0.055, -0.09, math.sin(a) * 0.055), mat=P["iron"])
    m.cyl(0.065, 0.02, 0.05, at=(0, 0.06, 0), mat=P["iron"], segs=8)
    m.box((0.006, 0.08, 0.05), at=(0, 0.1, 0), mat=P["iron"])
    ob = m.build("VM_lantern", loc=(1.0, 0, 0))
    kit.empty("flame", (0, -0.01, 0), parent=ob, size=0.03)
    return ob


def rod(name, x, reinforced):
    m = MB()
    m.cyl(0.018, 0.008, 1.3, at=(0, 0, -0.65), mat=P["timber_light"], segs=6, pitch=FWD + 0.0, centered=True)
    m.cyl(0.024, 0.024, 0.22, at=(0, 0, 0.05), mat=grip, segs=8, pitch=FWD, centered=True)
    m.cyl(0.04, 0.04, 0.03, at=(0.035, -0.02, -0.08), mat=P["brass"] if reinforced else P["iron"], segs=10, roll=math.pi / 2, centered=True)
    if reinforced:
        for z in (-0.3, -0.6, -0.9):
            m.cyl(0.02, 0.02, 0.03, at=(0, 0, z), mat=P["brass"], segs=8, pitch=FWD, centered=True)
    ob = m.build(name, loc=(x, 0, 0))
    kit.empty("tip", (0, 0, -1.3), parent=ob, size=0.03)
    return ob


def bobber():
    m = MB()
    m.sphere(0.06, at=(0, 0.02, 0), mat=P["paint_red"], scale=(1, 0.8, 1), subdiv=1)
    m.sphere(0.055, at=(0, 0.06, 0), mat=P["paint_white"], scale=(1, 0.6, 1), subdiv=1)
    m.cyl(0.008, 0.008, 0.08, at=(0, 0.08, 0), mat=P["iron"], segs=5)
    return m.build("VM_bobber", loc=(2.0, 0, 0))


boltcaster("VM_boltcaster_mk1", -1.0, 1)
boltcaster("VM_boltcaster_mk2", -1.5, 2)
boltcaster("VM_lamplighter", -2.0, 3)
lantern()
rod("VM_rod_basic", 1.5, False)
rod("VM_rod_reinforced", 1.7, True)
bobber()

kit.save_and_export("art/blender/viewmodels/viewmodels.blend", "public/assets/models/viewmodels.glb")
