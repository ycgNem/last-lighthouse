"""Builds art/blender/props/props.blend and public/assets/models/props.glb.

Every prop is a top-level object named PROP_<id>, base centred on its origin,
front facing game +Z. The game clones them by name onto NODE_ markers.

    blender -b --factory-startup --python tools/blender/build/props.py
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import kit  # noqa: E402
from kit import MB  # noqa: E402

kit.reset()
P = kit.palette()
seaweed_glass = kit.material("lens_glass", 0xF4FBFF, rough=0.1, emit=0xFFF1C9, strength=0.6)
barnacle = kit.material("barnacle", 0xD8D2C4)

slot = [0]


def place():
    """Spread props along X in the .blend so they're easy to find by eye."""
    slot[0] += 1
    return ((slot[0] % 8) * 4.0, 0, (slot[0] // 8) * 4.0)


def driftwood():
    m = MB()
    m.cyl(0.22, 0.17, 2.6, at=(0, 0.2, 0), mat=P["driftwood"], segs=8, roll=math.pi / 2, centered=True)
    m.cyl(0.08, 0.05, 0.7, at=(0.5, 0.35, 0.1), mat=P["driftwood"], segs=6, roll=-0.9, yaw=0.4, centered=True)
    m.cyl(0.15, 0.12, 1.6, at=(-0.3, 0.42, 0.3), mat=P["driftwood"], segs=7, roll=math.pi / 2 - 0.15, yaw=0.7, centered=True)
    m.rock(0.25, at=(0.9, 0.08, -0.3), mat=P["rock"], seed=4, squash=0.5)
    m.build("PROP_driftwood", loc=place())


def scrap_pile():
    rnd = random.Random(2)
    m = MB()
    for i in range(9):
        w, h, d = 0.5 + rnd.random() * 0.7, 0.07 + rnd.random() * 0.12, 0.4 + rnd.random() * 0.6
        m.box((w, h, d), at=((rnd.random() - 0.5) * 1.0, 0.04 + i * 0.07, (rnd.random() - 0.5) * 0.8), mat=P["rust"] if i % 2 else P["iron"],
              yaw=rnd.random() * 3, pitch=(rnd.random() - 0.5) * 0.6, roll=(rnd.random() - 0.5) * 0.6, centered=True)
    m.cyl(0.32, 0.32, 0.08, at=(0.3, 0.45, 0.1), mat=P["rust"], segs=12, pitch=1.2, centered=True)
    m.cyl(0.07, 0.07, 1.3, at=(-0.2, 0.28, -0.2), mat=P["iron"], segs=8, roll=math.pi / 2, yaw=0.6, centered=True)
    m.build("PROP_scrap_pile", loc=place())


def kelp_bed():
    rnd = random.Random(3)
    m = MB()
    m.rock(0.55, at=(0, 0.05, 0), mat=P["rock_dark"], seed=8, squash=0.45)
    for i in range(9):
        a = rnd.random() * math.tau
        r = 0.3 + rnd.random() * 0.6
        L = 0.9 + rnd.random() * 0.8
        m.box((0.14, 0.03, L), at=(math.cos(a) * r, 0.06 + rnd.random() * 0.06, math.sin(a) * r), mat=P["kelp"] if i % 2 else P["kelp_dark"],
              yaw=a + rnd.random(), pitch=0.08, centered=True)
    for i in range(3):
        m.box((0.12, 0.7, 0.03), at=((rnd.random() - 0.5) * 0.5, 0.2, (rnd.random() - 0.5) * 0.5), mat=P["kelp"], yaw=rnd.random() * 3, pitch=0.35, roll=0.2)
    m.build("PROP_kelp_bed", loc=place())


def glass_bed():
    rnd = random.Random(5)
    m = MB()
    m.sphere(0.9, at=(0, -0.05, 0), mat=P["sand"], scale=(1.0, 0.22, 0.85), subdiv=2)
    glass = [P["glass_white"], P["glass_green"], P["glass_blue"]]
    for i in range(12):
        a = rnd.random() * math.tau
        r = rnd.random() * 0.7
        m.sphere(0.05 + rnd.random() * 0.05, at=(math.cos(a) * r, 0.13 - r * 0.08, math.sin(a) * r), mat=glass[i % 3], scale=(1.3, 0.6, 1.0), subdiv=0)
    m.build("PROP_glass_bed", loc=place())


def reinforced_wreckage():
    m = MB()
    for i in range(5):
        m.box((2.2, 0.18, 0.3), at=(0, 0.25 + i * 0.26, -i * 0.05), mat=P["hull"] if i % 2 else P["hull_dark"], roll=0.08 * (i - 2), pitch=-0.25, centered=True)
    for x in (-0.8, 0.0, 0.8):
        m.box((0.12, 1.5, 0.06), at=(x, 0.0, 0.18), mat=P["iron"], pitch=-0.25)
        for k in range(4):
            m.cyl(0.05, 0.05, 0.05, at=(x, 0.3 + k * 0.3, 0.26 - k * 0.07), mat=P["brass"], segs=8, pitch=math.pi / 2 - 0.25, centered=True)
    m.cyl(0.26, 0.26, 0.08, at=(0.4, 0.75, 0.22), mat=P["brass"], segs=14, pitch=math.pi / 2 - 0.25, centered=True)
    m.cyl(0.17, 0.17, 0.1, at=(0.4, 0.75, 0.23), mat=P["glass_blue"], segs=14, pitch=math.pi / 2 - 0.25, centered=True)
    m.build("PROP_reinforced_wreckage", loc=place())


def crate(name, size, body, frame):
    sx, sy, sz = size
    m = MB()
    m.box(size, mat=body)
    t = 0.06
    for y in (0.0, sy - t):
        m.box((sx + 0.02, t, sz + 0.02), at=(0, y, 0), mat=frame)
    for x in (-sx / 2, sx / 2):
        for z in (-sz / 2, sz / 2):
            m.box((t, sy, t), at=(x, 0, z), mat=frame)
    m.box((sx * 1.05, 0.05, 0.08), at=(0, sy * 0.5, sz / 2 + 0.01), mat=frame, roll=0.6)
    return m


def supply_crate():
    crate("PROP_supply_crate", (0.9, 0.8, 0.9), P["timber_light"], P["timber"]).build("PROP_supply_crate", loc=place())


def sealed_cache():
    m = crate("x", (1.2, 0.75, 0.8), P["hull_dark"], P["iron"])
    m.box((0.22, 0.26, 0.08), at=(0, 0.3, 0.43), mat=P["brass"])
    m.cyl(0.07, 0.07, 0.05, at=(0, 0.62, 0.43), mat=P["brass"], segs=8, pitch=math.pi / 2, centered=True)
    rnd = random.Random(9)
    for i in range(10):
        m.sphere(0.04 + rnd.random() * 0.03, at=((rnd.random() - 0.5) * 1.1, rnd.random() * 0.5, 0.41), mat=barnacle, subdiv=0)
    m.build("PROP_sealed_cache", loc=place())


def strongbox():
    m = crate("x", (0.8, 0.5, 0.55), P["iron"], P["brass"])
    m.box((0.16, 0.16, 0.05), at=(0, 0.22, 0.3), mat=P["brass"])
    m.build("PROP_strongbox", loc=place())


def lens_pedestal():
    m = MB()
    m.cyl(0.45, 0.5, 0.15, mat=P["stone"], segs=10)
    m.cyl(0.28, 0.32, 0.95, at=(0, 0.15, 0), mat=P["stone"], segs=10)
    m.cyl(0.4, 0.4, 0.08, at=(0, 1.1, 0), mat=P["brass"], segs=12)
    m.cyl(0.36, 0.36, 0.1, at=(0, 1.62, 0), mat=P["brass"], segs=16, pitch=math.pi / 2, centered=True)
    m.cyl(0.31, 0.31, 0.14, at=(0, 1.62, 0), mat=seaweed_glass, segs=16, pitch=math.pi / 2, centered=True)
    m.box((0.1, 0.3, 0.1), at=(0, 1.15, 0), mat=P["brass"])
    m.build("PROP_lens_pedestal", loc=place())


def tide_pole():
    """Origin at world water height 0: bands mark low (0), mid (0.9) and high (1.8) water."""
    m = MB()
    m.cyl(0.1, 0.1, 4.8, at=(0, -1.6, 0), mat=P["timber"], segs=8)
    for y, mat in ((0.0, P["paint_white"]), (0.9, P["paint_yellow"]), (1.8, P["paint_red"])):
        m.cyl(0.13, 0.13, 0.16, at=(0, y - 0.08, 0), mat=mat, segs=8)
    m.build("PROP_tide_pole", loc=place())


def buoy_crate():
    m = crate("x", (1.7, 0.9, 1.7), P["timber_light"], P["timber"])
    m.cyl(0.32, 0.32, 1.2, at=(0.95, 0.35, 0), mat=P["timber"], segs=10, pitch=math.pi / 2, centered=True)
    m.cyl(0.04, 0.04, 1.8, at=(0, 0.6, 0.86), mat=P["rope"], segs=6, roll=math.pi / 2, centered=True)
    m.build("PROP_buoy_crate", loc=place())


def rope_ladder():
    m = MB()
    for x in (-0.3, 0.3):
        m.cyl(0.03, 0.03, 6.0, at=(x, 0, 0), mat=P["rope"], segs=6)
    for i in range(14):
        m.box((0.7, 0.05, 0.08), at=(0, 0.3 + i * 0.4, 0), mat=P["timber"])
    m.build("PROP_rope_ladder", loc=place())


def beacon_lamp():
    m = MB()
    m.cyl(0.8, 0.85, 0.2, mat=P["iron"], segs=12)
    for i in range(8):
        a = i / 8 * math.tau
        m.box((0.06, 1.6, 0.06), at=(math.cos(a) * 0.7, 0.2, math.sin(a) * 0.7), mat=P["iron"])
    m.cyl(0.8, 0.2, 0.5, at=(0, 1.8, 0), mat=P["iron"], segs=12)
    m.cyl(0.45, 0.45, 0.9, at=(0, 0.45, 0), mat=P["glass_white"], segs=12)
    m.build("PROP_beacon_lamp", loc=place())


def rowboat():
    m = MB()
    m.box((1.4, 0.55, 3.4), at=(0, -0.2, 0), mat=P["timber"])
    # Pointed bow: two planks meeting in a V ahead of the hull.
    for side in (-1, 1):
        m.box((0.12, 0.55, 1.15), at=(side * 0.36, -0.2, 2.1), mat=P["timber"], yaw=-side * 0.55)
    m.box((0.9, 0.06, 0.5), at=(0, 0.3, 1.85), mat=P["timber_light"])
    m.box((1.3, 0.06, 0.3), at=(0, 0.3, 0.6), mat=P["timber_light"])
    m.box((1.3, 0.06, 0.3), at=(0, 0.3, -0.8), mat=P["timber_light"])
    m.cyl(0.03, 0.03, 2.2, at=(0.55, 0.42, -0.1), mat=P["timber_light"], segs=6, pitch=math.pi / 2 - 0.1, yaw=0.15, centered=True)
    m.cyl(0.03, 0.03, 2.2, at=(-0.55, 0.42, -0.1), mat=P["timber_light"], segs=6, pitch=math.pi / 2 - 0.1, yaw=-0.15, centered=True)
    m.build("PROP_rowboat", loc=place())


def signpost():
    m = MB()
    m.box((0.18, 2.3, 0.18), mat=P["timber"])
    m.box((1.5, 0.4, 0.07), at=(0.5, 1.75, 0), mat=P["timber_light"], roll=0.05)
    m.box((1.2, 0.35, 0.07), at=(-0.35, 1.25, 0.02), mat=P["timber_light"], roll=-0.08)
    m.build("PROP_signpost", loc=place())


def barrel():
    m = MB()
    m.cyl(0.32, 0.36, 0.45, mat=P["timber"], segs=12)
    m.cyl(0.36, 0.32, 0.45, at=(0, 0.45, 0), mat=P["timber"], segs=12)
    for y in (0.12, 0.45, 0.78):
        m.cyl(0.37, 0.37, 0.05, at=(0, y, 0), mat=P["iron"], segs=12)
    m.build("PROP_barrel", loc=place())


def hull_ribs():
    m = MB()
    for i in range(6):
        z = -2.5 + i
        for side in (-1, 1):
            m.box((0.22, 2.6 - abs(i - 2.5) * 0.25, 0.25), at=(side * 1.3, -0.2, z), mat=P["hull_dark"], roll=side * 0.45)
    m.box((0.35, 0.3, 6.0), at=(0, -0.15, -0.0), mat=P["hull"])
    m.build("PROP_hull_ribs", loc=place())


def lantern_post():
    m = MB()
    m.cyl(0.07, 0.09, 2.4, mat=P["iron"], segs=6)
    m.box((0.6, 0.05, 0.05), at=(0.25, 2.3, 0), mat=P["iron"])
    m.box((0.26, 0.36, 0.26), at=(0.5, 1.9, 0), mat=P["lamp"])
    m.build("PROP_lantern_post", loc=place(), props={"light": "warm"})


def dune_grass():
    rnd = random.Random(11)
    m = MB()
    grass = kit.material("dune_grass", 0x8C9461)
    for i in range(9):
        a = rnd.random() * math.tau
        r = rnd.random() * 0.35
        m.cyl(0.05, 0.0, 0.5 + rnd.random() * 0.5, at=(math.cos(a) * r, -0.05, math.sin(a) * r), mat=grass, segs=3, pitch=(rnd.random() - 0.5) * 0.6, roll=(rnd.random() - 0.5) * 0.6)
    m.build("PROP_dune_grass", loc=place())


for build in (driftwood, scrap_pile, kelp_bed, glass_bed, reinforced_wreckage, supply_crate, sealed_cache, strongbox, lens_pedestal,
              tide_pole, buoy_crate, rope_ladder, beacon_lamp, rowboat, signpost, barrel, hull_ribs, lantern_post, dune_grass):
    build()

kit.save_and_export("art/blender/props/props.blend", "public/assets/models/props.glb")
