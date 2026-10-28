"""Builds art/blender/locations/beacon.blend and public/assets/models/locations/beacon.glb.

Saltmere Beacon, the chapter finale, per docs/LEVELS.md (game space, metres):

  landing    east, rock, y 3.0; the boat floats off its east side
  causeway   stepping stones at y 2.8 (never floods) from the landing to the
             arena gate, with two Spitters on rocks either side
  gate       the arena's east entrance; two Wisps; TRIG_boss covers the arena
  arena      a ring of rock, y 3.0, radius 15, standing stones round the edge
             and four cover pillars; the Wreck Guardian rises from the sea to
             the south (FX_arena is the centre the fight is measured from)
  stair      a ramp north from the arena to the tower platform (y 7); rubble
             (STATE_guardian_defeated_off) blocks it until the Guardian falls
  beacon     the tower on the platform; INT_beacon at its door relights it,
             the beam turns at FX_beacon_lamp

    blender -b --factory-startup --python tools/blender/build/beacon.py
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import bpy  # noqa: E402
import kit  # noqa: E402
from kit import MB, smoothstep, noise2  # noqa: E402

kit.reset()

with bpy.data.libraries.load(os.path.join(kit.ROOT, "art/blender/props/props.blend"), link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.startswith("PROP_")]
TEMPLATES = {o.name[5:]: o for o in dst.objects}
P = kit.palette()
FIRE = kit.material("brazier_fire", 0xFFB347, emit=0xFF8A2A, strength=4.0)
rnd = random.Random(31)

SEA = -6.0
ARENA_Y = 3.0
ARENA_R = 15.0
PLATFORM_Y = 7.0
CAUSEWAY_Y = 2.8


def lerp(a, b, t):
    return a + (b - a) * t


def rect_dist(x, z, x0, x1, z0, z1):
    dx = max(x0 - x, 0.0, x - x1)
    dz = max(z0 - z, 0.0, z - z1)
    return math.hypot(dx, dz)


# ------------------------------------------------------------------ terrain


def height(x, z):
    # Rocky shoals around the stack, well under the low-water line.
    y = SEA + 3.0 * max(0.0, noise2(x * 0.08, z * 0.08, 2)) - smoothstep(40, 80, math.hypot(x - 15, z + 5)) * 2
    # The arena: a flat ring of rock with steep sides.
    d = math.hypot(x, z)
    y = max(y, ARENA_Y + 0.03 * noise2(x * 2, z * 2, 3) - smoothstep(ARENA_R, ARENA_R + 3.0, d) * 9.0)
    # The landing.
    y = max(y, 3.0 + 0.04 * noise2(x * 1.5, z * 1.5, 4) - smoothstep(0, 3.0, rect_dist(x, z, 42, 56, -9, 9)) * 9.0)
    # Rocks either side of the causeway, flat-topped: the Spitters' perches.
    for cx, cz in ((27.0, -8.5), (33.0, 8.5)):
        y = max(y, 3.4 - smoothstep(2.2, 3.8, math.hypot(x - cx, z - cz)) * 9.4)
    # The tower platform, north.
    y = max(y, PLATFORM_Y + 0.03 * noise2(x * 2, z * 2, 6) - smoothstep(0, 3.0, rect_dist(x, z, -9, 9, -38, -26.5)) * 13.0)
    return y


def color(x, z, y):
    if y > 2.4:
        return 0x7E7B73 if noise2(x * 2.5, z * 2.5, 7) > -0.25 else 0x6E6B64
    if y > 0.5:
        return 0x5C5A55
    return 0x3C4440


ground = kit.material("TIDE_rock", 0xFFFFFF, rough=0.95, vcol=True)
kit.terrain("terrain", -50, 75, -55, 45, 1.0, height, color, ground, props={"col": 1})


def H(x, z):
    return height(x, z)


def prop(kind, name, x, z, y=None, yaw=None, props=None, scale=1.0, parent=None):
    t = TEMPLATES[kind]
    ob = t.copy()
    ob.name = name
    bpy.context.scene.collection.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    ob.location = kit.B(x, H(x, z) if y is None else y, z)
    ob.rotation_euler = (0, 0, rnd.random() * math.tau if yaw is None else yaw)
    ob.scale = (scale, scale, scale)
    for k, v in (props or {}).items():
        ob[k] = v
    return ob


def ramp(m, a, b, width, thick, mat):
    """A flat ramp whose top surface runs from game point a (low) to b (high)."""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    run = math.hypot(dx, dz)
    pitch = math.atan2(dy, run)
    yaw = math.atan2(-dx, -dz)
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - thick / 2 / math.cos(pitch), (a[2] + b[2]) / 2)
    m.box((width, thick, math.hypot(run, dy)), at=mid, mat=mat, pitch=pitch, yaw=yaw, centered=True)


# ----------------------------------------------------------------- landing

prop("rowboat", "BUOY_boat", 59.0, 3.0, y=0.0, yaw=math.pi / 2, props={"interact": "boat", "range": 6.0, "float": -0.15, "min": -1.0, "max": 2.5})
kit.empty("SPAWN_landing", (50.0, 3.1, 0.0), yaw=math.pi / 2)
prop("lantern_post", "lantern_landing", 44.0, -3.0, yaw=math.pi / 2)
for i in range(10):
    a = rnd.random() * math.tau
    x, z = 49 + math.cos(a) * 9.5, math.sin(a) * 10.5
    if x > 54:  # keep the boat side clear
        continue
    r = 0.7 + rnd.random() * 1.1
    MB().rock(r, mat=P["rock"], seed=600 + i, squash=0.7).build(f"rock_landing_{i:02d}", loc=(x, H(x, z) - r * 0.4, z), props={"col": 1})

# ---------------------------------------------------------------- causeway

cause = MB()
x = 41.6
i = 0
while x > 16.4:
    w = 1.8 + rnd.random() * 0.5
    cx = x - w / 2
    h = CAUSEWAY_Y + (rnd.random() - 0.5) * 0.06
    cause.box((w - 0.12, 0.5, 3.4 + rnd.random() * 0.4), at=(cx, h - 0.5, (rnd.random() - 0.5) * 0.3), mat=P["stone"] if i % 2 else P["rock"], yaw=(rnd.random() - 0.5) * 0.08)
    cause.cyl(0.5, 0.7, h - 0.5 - SEA, at=(cx, SEA, 0), mat=P["rock_dark"], segs=7)
    x -= w
    i += 1
cause.build("causeway", props={"col": 1})

for i, (cx, cz) in enumerate(((27.0, -8.5), (33.0, 8.5))):
    for k in range(5):
        a = rnd.random() * math.tau
        r = 0.6 + rnd.random() * 0.9
        px, pz = cx + math.cos(a) * 2.6, cz + math.sin(a) * 2.6
        MB().rock(r, mat=P["rock_dark"], seed=700 + i * 10 + k).build(f"rock_perch_{i}_{k}", loc=(px, H(px, pz) - r * 0.5, pz))

# -------------------------------------------------------------------- gate

gate = MB()
for gz in (-3.2, 3.2):
    gate.box((1.4, 5.2, 1.4), at=(16.0, ARENA_Y, gz), mat=P["stone"])
    gate.box((1.7, 0.4, 1.7), at=(16.0, ARENA_Y + 5.2, gz), mat=P["rock"])
gate.box((1.4, 0.9, 8.0), at=(16.0, ARENA_Y + 5.6, 0), mat=P["stone"])
gate.build("gate", props={"col": 1})

# ------------------------------------------------------------------- arena

ring = MB()
for k in range(18):
    a = k / 18 * math.tau
    deg = math.degrees(a)
    # Openings: the gate (east), the stair (north) and the Guardian's side (south).
    if deg < 22 or deg > 338 or 248 < deg < 292 or 80 < deg < 100:
        continue
    r = ARENA_R - 0.9
    sx, sz = math.cos(a) * r, math.sin(a) * r
    h = 1.0 + rnd.random() * 0.9
    ring.box((1.3, h, 0.8), at=(sx, ARENA_Y - 0.2, sz), mat=P["stone"] if k % 2 else P["rock"], yaw=-a + math.pi / 2, roll=(rnd.random() - 0.5) * 0.15)
ring.build("arena_stones", props={"col": 1})

cover = MB()
for k in range(4):
    a = math.pi / 4 + k * math.pi / 2
    cover.cyl(1.1, 1.25, 2.3, at=(math.cos(a) * 8.0, ARENA_Y - 0.1, math.sin(a) * 8.0), mat=P["stone"], segs=9)
    cover.cyl(1.35, 1.35, 0.3, at=(math.cos(a) * 8.0, ARENA_Y + 2.2, math.sin(a) * 8.0), mat=P["rock"], segs=9)
cover.build("arena_pillars", props={"col": 1})

# Old flagstones and a worn compass rose (visual).
rose = MB()
rose.cyl(3.2, 3.2, 0.04, at=(0, ARENA_Y, 0), mat=P["rock_dark"], segs=24)
for k in range(8):
    a = k * math.pi / 4
    rose.box((0.35, 0.05, 2.9 if k % 2 == 0 else 1.9), at=(math.cos(a) * 1.4, ARENA_Y + 0.01, math.sin(a) * 1.4), mat=P["brass"], yaw=-a + math.pi / 2)
rose.build("arena_rose")

kit.empty("FX_arena", (0, ARENA_Y, 0))
# Entering the ring wakes the Guardian; leaving it (19 m out) sends it back down.
trig = MB().box((32.0, 8.0, 32.0), at=(0, ARENA_Y - 1.0, 0)).build("TRIG_boss", props={"event": "boss"})
trig.display_type = "WIRE"  # so it doesn't hide the arena when you open the .blend
trig.hide_render = True
kit.empty("ENEMY_guardian", (0, 0, 18.5), props={"enemy": "wreck_guardian", "tide": "any"})

# ------------------------------------------------- the stair up to the tower

STAIR_FOOT = (0.0, ARENA_Y, -14.4)
STAIR_TOP = (0.0, PLATFORM_Y, -27.0)
stair = MB()
ramp(stair, STAIR_FOOT, STAIR_TOP, 3.2, 0.5, P["stone"])
# Side walls a metre over the ramp: you can't hop onto it from the arena's edge.
for sx in (-1.8, 1.8):
    ramp(stair, (sx, STAIR_FOOT[1] + 1.0, STAIR_FOOT[2] - 1.0), (sx, STAIR_TOP[1] + 1.0, STAIR_TOP[2]), 0.4, 1.6, P["rock"])
# Piers holding the stair over the water.
for k in range(4):
    z = -16.5 - k * 3.0
    y = ARENA_Y + (PLATFORM_Y - ARENA_Y) * (STAIR_FOOT[2] - z) / (STAIR_FOOT[2] - STAIR_TOP[2])
    stair.cyl(1.2, 1.5, y - 0.4 - SEA, at=(0, SEA, z), mat=P["rock_dark"], segs=8)
stair.build("stair", props={"col": 1})

# Rubble across the stair's foot until the Guardian falls.
rubble = MB()
for k in range(9):
    rx = -1.9 + (k % 3) * 1.9 + (rnd.random() - 0.5) * 0.4
    rz = -15.0 - (k // 3) * 0.75
    r = 0.9 + rnd.random() * 0.4
    rubble.rock(r, at=(rx, ARENA_Y + 0.5 + (k // 3) * 0.55, rz), mat=P["rock"] if k % 2 else P["rock_dark"], seed=800 + k, squash=0.85)
rubble.box((4.6, 2.7, 2.6), at=(0, ARENA_Y, -15.6), mat=P["rock_dark"])
rubble.build("STATE_guardian_defeated_off", props={"col": 1})

# Braziers that light the way once the Guardian is gone.
lit = kit.empty("STATE_guardian_defeated_on", (0, 0, 0))
for k, bx in enumerate((-2.6, 2.6)):
    br = MB()
    br.cyl(0.25, 0.3, 1.1, mat=P["iron"], segs=8)
    br.cyl(0.55, 0.35, 0.35, at=(0, 1.1, 0), mat=P["iron"], segs=10)
    br.sphere(0.32, at=(0, 1.42, 0), mat=FIRE, scale=(1, 0.7, 1), subdiv=1)
    ob = br.build(f"brazier_{k}", loc=(bx, ARENA_Y, -13.8), parent=lit, props={"light": "warm", "light_offset": [0, 1.6, 0]})

# ----------------------------------------------------------- tower platform

tower = MB()
tower.cyl(3.4, 2.9, 12.0, at=(0, PLATFORM_Y, -32.5), mat=P["stone"], segs=18)
for y in (PLATFORM_Y + 4.0, PLATFORM_Y + 8.5):
    tower.cyl(3.32 - (y - PLATFORM_Y) * 0.04, 3.36 - (y - PLATFORM_Y) * 0.04, 1.0, at=(0, y, -32.5), mat=P["paint_red"], segs=18)
tower.cyl(3.7, 3.7, 0.45, at=(0, PLATFORM_Y + 12.0, -32.5), mat=P["iron"], segs=18)
tower.cyl(2.6, 0.3, 2.4, at=(0, PLATFORM_Y + 15.4, -32.5), mat=P["iron"], segs=12)
for k in range(10):
    a = k / 10 * math.tau
    tower.box((0.08, 1.0, 0.08), at=(math.cos(a) * 3.55, PLATFORM_Y + 12.45, -32.5 + math.sin(a) * 3.55), mat=P["iron"])
tower.build("tower", props={"col": 1})
door = MB()
door.box((1.6, 2.6, 0.3), at=(0, PLATFORM_Y, -29.4), mat=P["hull_dark"])
door.cyl(0.8, 0.8, 0.3, at=(0, PLATFORM_Y + 2.6, -29.4), mat=P["hull_dark"], segs=12, pitch=math.pi / 2, centered=True)
door.build("tower_door")
prop("beacon_lamp", "beacon_lamp_top", 0, -32.5, y=PLATFORM_Y + 12.45, yaw=0.0)
kit.empty("FX_beacon_lamp", (0, PLATFORM_Y + 13.5, -32.5))

# Where you carry the Ember: a stone plinth and a brass bowl at the door.
plinth = MB()
plinth.cyl(0.6, 0.75, 1.0, mat=P["stone"], segs=10)
plinth.cyl(0.65, 0.45, 0.3, at=(0, 1.0, 0), mat=P["brass"], segs=12)
plinth.build("INT_beacon", loc=(0, PLATFORM_Y, -27.6), props={"interact": "beacon", "range": 3.6, "col": 1})

for k in range(8):
    a = rnd.random() * math.tau
    px, pz = math.cos(a) * 7.5, -32.0 + math.sin(a) * 4.5
    if pz > -28:
        continue
    r = 0.6 + rnd.random() * 0.8
    MB().rock(r, mat=P["rock"], seed=900 + k, squash=0.7).build(f"rock_platform_{k}", loc=(px, H(px, pz) - r * 0.4, pz), props={"col": 1})

# Lanterns along the causeway, lit once the chapter's done.
done = kit.empty("STATE_chapter1_complete_on", (0, 0, 0))
for k, lx in enumerate((22.0, 30.0, 38.0)):
    prop("lantern_post", f"lantern_causeway_{k}", lx, 1.9 if k % 2 else -1.9, y=CAUSEWAY_Y, yaw=math.pi / 2, parent=done)

# ----------------------------------------------------------------- enemies

for k, (sx, sz) in enumerate(((27.0, -8.5), (33.0, 8.5))):
    kit.empty(f"ENEMY_spitter_{k}", (sx, 3.4, sz), props={"enemy": "drowned_spitter", "tide": "any"})
for k, gz in enumerate((-4.5, 4.5)):
    kit.empty(f"ENEMY_wisp_{k}", (18.5, ARENA_Y + 2.5, gz), props={"enemy": "lantern_wisp", "tide": "any"})

# ---------------------------------------------------- anchors and the beam

for name, (ax, ay, az) in {"landing": (48, 3.1, 0), "causeway": (30, CAUSEWAY_Y + 0.1, 0), "arena_e": (11, 3.1, 0), "arena_n": (0, 3.1, -10)}.items():
    kit.empty(f"ANCHOR_{name}", (ax, ay, az))
# Lantern's Rest lies south-west.
kit.empty("FX_home_light", (-250, 0, 260))

kit.save_and_export("art/blender/locations/beacon.blend", "public/assets/models/locations/beacon.glb")
