"""Builds art/blender/locations/shore.blend and public/assets/models/locations/shore.glb.

Gullwash Shore, laid out per docs/LEVELS.md (game space, metres):
  south: dunes (dry, y 2.4–4) with the landing jetty and the cliff path home
  middle: wet sand flats (y 0.3–1.3) that flood at high tide
  north-east: a sandbar (y 0.6) out to a dry islet (y 2.7) — a low-tide trip
  north-west: a rocky spit (y 2.6, always dry) with the Glowgill shoal off its tip

    blender -b --factory-startup --python tools/blender/build/shore.py
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import bpy  # noqa: E402
import kit  # noqa: E402
from kit import MB, smoothstep, seg_dist, noise2  # noqa: E402

kit.reset()

# Props come from props.blend as linked duplicates (shared meshes), so the level
# file shows real models and the .glb instances them.
with bpy.data.libraries.load(os.path.join(kit.ROOT, "art/blender/props/props.blend"), link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.startswith("PROP_")]
TEMPLATES = {o.name[5:]: o for o in dst.objects}
P = kit.palette()


def lerp(a, b, t):
    return a + (b - a) * t


SEA = -3.0


def dune(x, z):
    return 2.75 + 0.7 * max(0.0, noise2(x * 0.9, z * 0.9, 1)) + 0.25 * noise2(x * 2.1, z * 1.7, 3)


def height(x, z):
    # North → south profile.
    if z < -18:
        y = lerp(0.3, SEA, smoothstep(-18, -34, z))
    elif z < 16:
        y = lerp(0.3, 1.3, (z + 18) / 34) + 0.07 * noise2(x * 3, z * 3, 5)
    elif z < 23:
        y = lerp(1.3, dune(x, z), smoothstep(16, 23, z))
    elif z < 47:
        y = dune(x, z)
    elif z < 58:
        y = lerp(dune(x, z), 0.4, smoothstep(47, 58, z))
    else:
        y = lerp(0.4, SEA, smoothstep(58, 70, z))
    # Island edge east/west.
    y = lerp(y, SEA, smoothstep(50, 66, abs(x) + 4 * noise2(z * 0.6, x * 0.1, 7)))

    # Sandbar out to the islet.
    d = seg_dist(x, z, 22, -16, 50, -44)
    y = max(y, 0.6 - (d / 4.0) ** 2 * 1.2)
    # Islet.
    d = math.hypot(x - 54, z + 50)
    y = max(y, 2.75 - (d / 10.0) ** 2 * 4.5 + 0.15 * noise2(x * 2, z * 2, 9))
    # Rocky spit (always dry).
    d = seg_dist(x, z, -40, 20, -46, -24)
    y = max(y, 2.6 - smoothstep(3.0, 7.5, d) * 5.6)
    # Sandy path down to the jetty and up to the cliff path.
    if 3 < x < 13 and 34 < z < 50:
        y = lerp(y, 2.9, 1 - smoothstep(3.0, 4.6, abs(x - 8)))
    return y


def color(x, z, y):
    spit = 1 - smoothstep(2.0, 6.0, seg_dist(x, z, -40, 20, -46, -24))
    if y < -0.5:
        c = 0x5E5A48
    elif y < 0.2:
        c = 0x7A7258
    elif y < 1.8:
        c = 0x8F8366 if (y < 1.0) else 0x998B6B
    elif y < 2.4:
        c = 0xB3A37E
    elif y < 3.35:
        c = 0xC9B98F
    else:
        c = 0x9A9A6A if noise2(x * 4, z * 4, 2) > -0.2 else 0xC2B289
    if spit > 0.5 and y > 0.5:
        c = 0x77736A
    return c


rnd = random.Random(21)
ground = kit.material("TIDE_sand", 0xFFFFFF, rough=0.95, vcol=True)
kit.terrain("terrain", -80, 80, -72, 78, 1.0, height, color, ground, props={"col": 1})


def H(x, z):
    return height(x, z)


def prop(kind, name, x, z, y=None, yaw=None, props=None, scale=1.0):
    t = TEMPLATES[kind]
    ob = t.copy()
    ob.name = name
    bpy.context.scene.collection.objects.link(ob)
    ob.location = kit.B(x, H(x, z) if y is None else y, z)
    ob.rotation_euler = (0, 0, rnd.random() * math.tau if yaw is None else yaw)
    ob.scale = (scale, scale, scale)
    for k, v in (props or {}).items():
        ob[k] = v
    return ob


# ------------------------------------------------------------ landing jetty

JX, JY = 8.0, 3.0
jetty = MB()
for i in range(24):
    z = 46 + i * 0.95
    jetty.box((3.0, 0.15, 0.85), at=(0, -0.15, z), mat=P["timber"] if i % 3 else P["timber_light"])
for i in range(7):
    for side in (-1.35, 1.35):
        jetty.cyl(0.16, 0.2, JY - SEA + 0.1, at=(side, SEA - JY, 49 + i * 3.2), mat=P["timber"], segs=7)
jetty.build("jetty", loc=(JX, JY, 0), props={"col": 1})
# The boat floats (BUOY_) and is still the travel interact.
prop("rowboat", "BUOY_boat", JX + 3.0, 64, y=0.25, yaw=0.0, props={"interact": "boat", "range": 5.0, "float": -0.15, "min": -1.0, "max": 2.5})
prop("lantern_post", "lantern_jetty", JX - 1.3, 47, y=JY, yaw=math.pi)
prop("lantern_post", "lantern_dunes", 2, 40, yaw=0.3)
kit.empty("SPAWN_landing", (JX, JY, 52), yaw=0.0)

# ---------------------------------------------------------- cliff path home

prop("signpost", "INT_path_home", -57, 31, yaw=-math.pi / 2, props={"interact": "path_home"})
prop("lantern_post", "lantern_path", -55, 27, yaw=0.0)
kit.empty("SPAWN_path", (-53, H(-53, 31) + 0.1, 31), yaw=-math.pi / 2)

# ---------------------------------------------------------------- landmarks

# Old fisher's hut on the dunes (broken walls, no roof).
hut = MB()
hut.box((6, 2.4, 0.4), at=(0, 0, -2.5), mat=P["timber"])
hut.box((0.4, 2.4, 5.0), at=(-3.0, 0, 0), mat=P["timber"])
hut.box((0.4, 1.4, 5.0), at=(3.0, 0, 0), mat=P["timber_light"])
hut.box((2.4, 2.4, 0.4), at=(-1.8, 0, 2.5), mat=P["timber"])
hut.box((0.3, 2.8, 0.3), at=(-3, 0, 2.5), mat=P["timber_light"])
hut.box((0.3, 2.8, 0.3), at=(3, 0, -2.5), mat=P["timber_light"])
hut.build("hut", loc=(-22, H(-22, 38) - 0.2, 38), yaw=0.2, props={"col": 1})
prop("barrel", "barrel_hut1", -19.5, 35.5)
prop("barrel", "barrel_hut2", -20.4, 35.0)
prop("hull_ribs", "wreck_ribs", 20, -10, yaw=0.7)

# Rocks along the spit and the island edges.
for i in range(26):
    t = i / 25
    x = lerp(-40, -46, t) + (rnd.random() - 0.5) * 6
    z = lerp(20, -24, t) + (rnd.random() - 0.5) * 3
    r = 0.9 + rnd.random() * 1.6
    MB().rock(r, mat=P["rock"] if i % 3 else P["rock_dark"], seed=100 + i, squash=0.7).build(f"rock_spit_{i:02d}", loc=(x, H(x, z) - r * 0.35, z), props={"col": 1})
for i in range(18):
    a = rnd.random() * math.tau
    x, z = 54 + math.cos(a) * 9.5, -50 + math.sin(a) * 9.5
    r = 0.7 + rnd.random() * 1.2
    MB().rock(r, mat=P["rock"], seed=200 + i).build(f"rock_islet_{i:02d}", loc=(x, H(x, z) - r * 0.3, z), props={"col": 1})
for i in range(16):
    x = (rnd.random() - 0.5) * 100
    z = 25 + rnd.random() * 20
    if abs(x - JX) < 6 or abs(x + 22) < 6:
        continue
    prop("dune_grass", f"grass_{i:02d}", x, z, scale=1.0 + rnd.random() * 0.6)
for i in range(10):
    x = (rnd.random() - 0.5) * 90
    z = 24 + rnd.random() * 22
    if abs(x - JX) < 5:
        continue
    r = 0.5 + rnd.random() * 0.9
    MB().rock(r, mat=P["rock"], seed=300 + i).build(f"rock_dune_{i:02d}", loc=(x, H(x, z) - r * 0.3, z), props={"col": 1})

# Tide poles: the painted bands sit at world heights 0 / 0.9 / 1.8.
prop("tide_pole", "tidepole_flats", 0, -6, y=0.0, yaw=0)
prop("tide_pole", "tidepole_spit", -42, -16, y=0.0, yaw=0)

# --------------------------------------------------------------- gathering

def node(kind, i, x, z, prop_name=None, y=None):
    return prop(prop_name or kind, f"NODE_{kind}_{i:02d}", x, z, y=y, props={"node": kind})


for i, (x, z) in enumerate([(-30, 20.5), (-8, 19.5), (14, 21), (31, 26), (-44, 34), (40, 13)]):
    node("driftwood", i, x, z)
for i, (x, z) in enumerate([(-18, 17), (26, 18), (2, 2)]):
    node("scrap_pile", i, x, z)
for i, (x, z) in enumerate([(-12, -12), (8, -15), (30, -12), (-34, -10)]):
    node("kelp_bed", i, x, z)
for i, (x, z) in enumerate([(-16, -2), (12, -4), (36, 0)]):
    node("glass_bed", i, x, z)
node("supply_crate", 0, 51, -47)
node("sealed_cache", 0, 56.5, -52.5)
kit.empty("NODE_fish_silverfin_00", (JX + 1.5, 0, 72), props={"node": "fish_silverfin"})
kit.empty("NODE_fish_glowgill_00", (-51, 0, -29.5), props={"node": "fish_glowgill"})

# ----------------------------------------------------------------- enemies

for i, (x, z) in enumerate([(-10, -2), (5, -8), (18, 4), (-22, 6)]):
    kit.empty(f"ENEMY_crab_low_{i}", (x, H(x, z), z), props={"enemy": "brine_crab", "tide": "low"})
for i, (x, z) in enumerate([(-15, 23), (20, 25)]):
    kit.empty(f"ENEMY_crab_high_{i}", (x, H(x, z), z), props={"enemy": "brine_crab", "tide": "high"})

# ---------------------------------------------------- anchors and the beam

for i, (x, z) in enumerate([(-30, 30), (25, 32), (0, 26), (54, -50), (-43, -12), (-44, 8)]):
    kit.empty(f"ANCHOR_{i}", (x, H(x, z) + 0.1, z))
kit.empty("ANCHOR_jetty", (JX, JY, 50))
# Lantern's Rest lies south-west; its beam shows on the horizon there.
kit.empty("FX_home_light", (-260, 0, 230))

kit.save_and_export("art/blender/locations/shore.blend", "public/assets/models/locations/shore.glb")
