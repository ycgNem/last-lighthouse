"""Builds art/blender/locations/wreck.blend and public/assets/models/locations/wreck.glb.

The Wreck of the Meridian, laid out per docs/LEVELS.md (game space, metres;
water sits at y 0 at low tide and 1.8 at high tide):

  ship      stern x -34 .. bow x +42, beam z -18 .. -6, main deck y 6,
            stern castle (the chart room, with the Drowned Lens) at x -34 .. -25
  shelf     the rock landing, y 2.8, south-west; the stern rail overhangs it
  lagoon    between the shelf and mid-ship, floor y -0.5: a wade at low tide,
            a swim at high tide
  flats     reef flats to the east, y 0.2 - 1.0, leading to the hull breach

Two ways up to the chart room, and the tide picks which:
  low tide   flats -> hull breach (x -3 .. 7) -> hold (floor 0.3 -> 0.9)
             -> the ramp along the north wall -> deck hatch
  high tide  shelf -> floating cargo crates (BUOY_) across the lagoon
             -> the fallen mast (its foot hangs at y 2.2, out of reach at low
             water) -> deck
Ways down: drop through the broken stern rail onto the shelf, or, once you have
the lens, the rope ladder.

    blender -b --factory-startup --python tools/blender/build/wreck.py
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
GLOW = kit.material("glow_sea", 0x3DFFB0, emit=0x3DFFB0, strength=3.0)
rnd = random.Random(7)

SEA = -3.0
DECK = 6.0
STERN, BOW_START, BOW_TIP = -34.0, 34.0, 42.0
NORTH, SOUTH = -18.0, -6.0  # hull side planes (z)
WALL = 0.4
BULWARK = 7.0
KEEL = -1.5


def lerp(a, b, t):
    return a + (b - a) * t


def rect_dist(x, z, x0, x1, z0, z1):
    """Distance from (x, z) to an axis-aligned rectangle (0 inside)."""
    dx = max(x0 - x, 0.0, x - x1)
    dz = max(z0 - z, 0.0, z - z1)
    return math.hypot(dx, dz)


# ------------------------------------------------------------------ terrain


def flats(x, z):
    return 0.2 + 0.8 * smoothstep(-6, 30, z) + 0.08 * noise2(x * 0.7, z * 0.7, 3)


def height(x, z):
    # Reef platform: the flats, falling away to open sea at the edges.
    reef = rect_dist(x, z, -24, 50, -26, 32) + 3 * noise2(x * 0.2, z * 0.2, 11)
    y = lerp(flats(x, z), SEA, smoothstep(0, 9, reef))
    # Lagoon between the landing and mid-ship.
    lag = rect_dist(x, z, -18.5, -6, -5, 11)
    y = lerp(-0.5 + 0.05 * noise2(x, z, 4), y, smoothstep(0, 2.5, lag))
    # Under the hull the seabed drops away (the hold floor is its own mesh).
    if STERN - 1 < x < BOW_TIP and NORTH < z < SOUTH - 0.5:
        y = min(y, -1.0)
    # Rock shelf (the landing). Steep sides.
    shelf = rect_dist(x, z, -38, -19.5, -5.8, 13)
    y = max(y, 2.8 + 0.04 * noise2(x * 2, z * 2, 5) - smoothstep(0, 1.4, shelf) * 7.0)
    # A rocky slope from the shelf's south end down to the flats. East of the
    # shelf it keeps clear of the lagoon so you can't jump to the mast's foot.
    slope = min(rect_dist(x, z, -38, -19, 12, 24), rect_dist(x, z, -19, -3, 15, 24))
    target = lerp(2.8, flats(x, z), smoothstep(-24, -5, x)) + 0.06 * noise2(x * 1.3, z * 1.3, 8)
    y = max(y, target - smoothstep(0, 1.6, slope) * 7.0)
    return y


def color(x, z, y):
    if y > 2.3:
        c = 0x77736A if noise2(x * 3, z * 3, 2) > -0.3 else 0x6A675F
    elif y < -0.3:
        c = 0x3F4436
    elif y < 0.45:
        c = 0x5F654A
    elif y < 1.1:
        c = 0x7C7558
    else:
        c = 0x948767
    return c


ground = kit.material("TIDE_reef", 0xFFFFFF, rough=0.95, vcol=True)
kit.terrain("terrain", -70, 70, -48, 52, 1.0, height, color, ground, props={"col": 1})


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


def ramp(m, a, b, width, thick, mat):
    """A flat plank ramp whose top surface runs from game point a (low) to b (high)."""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    run = math.hypot(dx, dz)
    length = math.hypot(run, dy)
    pitch = math.atan2(dy, run)
    yaw = math.atan2(-dx, -dz)
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - thick / 2 / math.cos(pitch), (a[2] + b[2]) / 2)
    m.box((width, thick, length), at=mid, mat=mat, pitch=pitch, yaw=yaw, centered=True)


# ---------------------------------------------------------------- the hull

hull = MB()
side_mat = P["hull"]
# North side, full length.
hull.box((BOW_START - STERN, BULWARK - KEEL, WALL), at=((STERN + BOW_START) / 2, KEEL, NORTH), mat=side_mat)
# South side in pieces: broken rail over the shelf, the mast notch, the breach.
south = [
    (STERN, -23.0, BULWARK),
    (-23.0, -20.5, DECK),  # broken rail: drop to the shelf
    (-20.5, -9.9, BULWARK),
    (-9.9, -7.7, 5.5),  # where the fallen mast comes over the side
    (-7.7, -3.0, BULWARK),
    (7.0, BOW_START, BULWARK),
]
for x0, x1, top in south:
    hull.box((x1 - x0, top - KEEL, WALL), at=((x0 + x1) / 2, KEEL, SOUTH), mat=side_mat)
# Above the breach.
hull.box((10.0, BULWARK - 3.5, WALL), at=(2.0, 3.5, SOUTH), mat=side_mat)
# Bow: two angled walls meeting at the tip.
for zs in (NORTH, SOUTH):
    dx, dz = BOW_TIP - BOW_START, -12.0 - zs
    length = math.hypot(dx, dz)
    yaw = math.atan2(-dx, -dz) + math.pi / 2
    hull.box((length + 0.4, BULWARK + 1.0 - KEEL, WALL), at=(BOW_START + dx / 2, KEEL, zs + dz / 2), mat=side_mat, yaw=yaw)
# Bulkhead closing off the bow from the hold.
hull.box((WALL, DECK - KEEL, SOUTH - NORTH), at=(BOW_START - 0.2, KEEL, (NORTH + SOUTH) / 2), mat=P["hull_dark"])
# Transom (flat stern), up to the castle roof.
hull.box((WALL, 9.5 - KEEL, SOUTH - NORTH + WALL), at=(STERN, KEEL, (NORTH + SOUTH) / 2), mat=P["hull_dark"])
hull.build("hull", props={"col": 1})

# Rub rails for shape. Visual only, and the south one skips the two gaps you
# walk through (the mast notch and the broken rail).
rub = MB()
rub.box((BOW_START - STERN, 0.25, 0.1), at=((STERN + BOW_START) / 2, 6.6, NORTH - 0.22), mat=P["timber_light"])
for x0, x1 in ((STERN, -23.0), (-20.5, -9.9), (-7.7, BOW_START)):
    rub.box((x1 - x0, 0.25, 0.1), at=((x0 + x1) / 2, 6.6, SOUTH + 0.22), mat=P["timber_light"])
rub.build("rub_rails")

# Jagged planks around the breach (visual).
bre = MB()
for i in range(9):
    x = -3.0 + i * 1.25
    h = 0.6 + rnd.random() * 1.4
    bre.box((0.9, h, 0.18), at=(x, 3.5 - h * 0.7, SOUTH + 0.1), mat=P["hull_dark"], roll=(rnd.random() - 0.5) * 0.6)
bre.build("breach_edge")

# Planks spilling out of the breach: an easy ramp from the flats into the hold.
spill = MB()
ramp(spill, (2.0, 0.12, -2.8), (2.0, 0.34, -6.7), 9.5, 0.25, P["hull"])
spill.build("breach_spill", props={"col": 1})

# ---------------------------------------------------------------- the decks

deck = MB()
DT = 0.3
# The hatch over the hold ramp is open: x -24 .. -16, z -18 .. -15.3.
deck.box((-24.0 - STERN, DT, SOUTH - NORTH), at=((STERN - 24.0) / 2, DECK - DT, (NORTH + SOUTH) / 2), mat=P["timber"])
deck.box((8.0, DT, SOUTH - (-15.3)), at=(-20.0, DECK - DT, (-15.3 + SOUTH) / 2), mat=P["timber_light"])
deck.box((BOW_START - (-16.0), DT, SOUTH - NORTH), at=((BOW_START - 16.0) / 2, DECK - DT, (NORTH + SOUTH) / 2), mat=P["timber"])
deck.box((4.0, DT, 5.2), at=(BOW_START + 2.0, DECK - DT, -12.0), mat=P["timber"])
# Planking lines (visual only, inset into the deck).
deck.build("deck", props={"col": 1})

planks = MB()
for i in range(10):
    z = NORTH + 0.6 + i * 1.2
    planks.box((BOW_START - STERN - 2, 0.02, 0.06), at=((STERN + BOW_START) / 2, DECK, z), mat=P["hull_dark"])
planks.build("deck_lines")


def hold_floor(x, z):
    # 0.3 at the breach and forward, rising to 0.9 toward the stern.
    return lerp(0.3, 0.9, smoothstep(0.0, -12.0, x)) + 0.03 * noise2(x * 2, z * 2, 6)


def hold_color(x, z, y):
    return 0x5A4634 if int((z + 40) / 0.6) % 2 else 0x4E3D2E


kit.terrain("hold_floor", STERN + WALL, BOW_START, NORTH + WALL / 2, SOUTH - WALL / 2, 0.6, hold_floor, hold_color, kit.material("TIDE_planks", 0xFFFFFF, rough=0.9, vcol=True), props={"col": 1})

# The ramp in the hold, along the north wall, up through the hatch.
inner = MB()
ramp(inner, (-9.5, 0.74, -16.7), (-24.0, DECK, -16.7), 2.0, 0.3, P["timber_light"])
for i in range(6):
    x = -11.0 - i * 2.4
    y = 0.74 + (DECK - 0.74) * (-9.5 - x) / 14.5
    inner.cyl(0.12, 0.12, max(0.2, y - 0.3), at=(x, 0.3, -15.85), mat=P["timber"], segs=6)
inner.build("hold_ramp", props={"col": 1})

# Support posts down the middle of the hold.
posts = MB()
for x in (-20.0, -8.0, 4.0, 16.0, 28.0):
    posts.cyl(0.28, 0.28, DECK - 0.5, at=(x, 0.3, -12.0), mat=P["timber"], segs=8)
posts.build("hold_posts", props={"col": 1})

# ---------------------------------------------------------- the fallen mast

# The foot hangs at 2.6: 1.2 m over anything you can stand on at low tide.
MAST_FOOT = (-8.8, 2.6, 10.0)
MAST_TOP = (-8.8, DECK, -7.3)
mast = MB()
ramp(mast, MAST_FOOT, MAST_TOP, 1.6, 0.22, P["timber_light"])
mast.build("mast_ramp", props={"col": 1})
spar = MB()
dx, dy, dz = 0.0, MAST_TOP[1] - MAST_FOOT[1], MAST_TOP[2] - MAST_FOOT[2]
L = math.hypot(dy, dz)
slope_a = math.atan2(dy, -dz)
spar.cyl(0.42, 0.34, L + 3.0, at=(-8.8, MAST_FOOT[1] - 0.6 - 1.6 * math.tan(slope_a), MAST_FOOT[2] + 1.6), mat=P["timber"], segs=10, pitch=-(math.pi / 2 - slope_a))
spar.build("mast_spar")
# Ropes from the mast to the rail (visual).
rig = MB()
for i in range(3):
    rig.cyl(0.03, 0.03, 9.0, at=(-9.9 + i * 1.1, 2.6 + i * 0.3, 7.0), mat=P["rope"], segs=4, pitch=-1.05)
rig.build("mast_rigging")

# Cargo crates that float up with the tide: the high-water bridge from the
# shelf to the mast's foot. They rest on the lagoon floor at low tide.
# At high water their tops sit at 2.4: step down from the shelf, along the
# row, and up onto the mast's foot from the last one.
for i, x in enumerate((-18.6, -16.6, -14.6, -12.6, -10.6, -8.8)):
    prop("buoy_crate", f"BUOY_crate_{i}", x, 10.95, y=-0.5, yaw=0.0, props={"float": -0.3, "min": -0.5, "max": 1.5})

# --------------------------------------------------- the stern castle (chart room)

CR_X0, CR_X1 = STERN, -25.0
castle = MB()
ch = 3.2
castle.box((WALL, ch, -13.2 - NORTH), at=(CR_X1, DECK, (NORTH - 13.2) / 2), mat=P["hull"])
castle.box((WALL, ch, SOUTH - (-10.8)), at=(CR_X1, DECK, (-10.8 + SOUTH) / 2), mat=P["hull"])
castle.box((WALL, ch - 2.4, 2.4), at=(CR_X1, DECK + 2.4, -12.0), mat=P["hull"])
castle.box((CR_X1 - CR_X0, 0.3, SOUTH - NORTH + WALL), at=((CR_X0 + CR_X1) / 2, DECK + ch, (NORTH + SOUTH) / 2), mat=P["hull_dark"])
# The castle's side walls are the hull's bulwarks; raise them to the roof.
for zs in (NORTH, SOUTH):
    castle.box((CR_X1 - CR_X0, ch - (BULWARK - DECK), WALL), at=((CR_X0 + CR_X1) / 2, BULWARK, zs), mat=P["hull"])
castle.build("chart_room", props={"col": 1})

trim = MB()
for zs, off in ((NORTH, 0.22), (SOUTH, -0.22)):
    for i in range(3):
        trim.box((1.0, 0.6, 0.05), at=(-32.0 + i * 3.0, DECK + 1.6, zs - off), mat=P["lamp"])
trim.box((2.6, 0.25, 0.6), at=(CR_X1 + 0.1, DECK + ch - 0.2, -12.0), mat=P["brass"])
trim.build("chart_room_windows")

furn = MB()
furn.box((2.4, 0.9, 1.4), at=(-27.6, DECK, -15.6), mat=P["timber_light"])
furn.box((2.6, 0.04, 1.6), at=(-27.6, DECK + 0.9, -15.6), mat=P["cloth"])
furn.box((0.5, 2.2, 3.0), at=(-33.4, DECK, -9.0), mat=P["timber"])
for i in range(3):
    furn.box((0.45, 0.05, 2.8), at=(-33.35, DECK + 0.6 + i * 0.6, -9.0), mat=P["timber_light"])
furn.build("chart_room_furniture", props={"col": 1})
prop("lantern_post", "lantern_chart_room", -32.6, -16.6, y=DECK, yaw=0.0)
prop("lens_pedestal", "NODE_lens_pedestal_00", -30.5, -12.0, y=DECK, yaw=math.pi / 2, props={"node": "lens_pedestal"})

# Rope ladder from the stern rail to the shelf; the game shows it once you
# hold the lens. Using it from the deck drops you at SPAWN_ladder.
prop("rope_ladder", "INT_rope_ladder", -29.5, -5.75, y=1.0, yaw=0.0, props={"interact": "rope_ladder", "range": 3.5})
kit.empty("SPAWN_ladder", (-29.5, 2.9, -4.4), yaw=math.pi)

# --------------------------------------------------------------- deck dressing

stack = MB()
stack.cyl(1.1, 1.0, 5.5, at=(-4.0, DECK, -12.0), mat=P["rust"], segs=14)
stack.cyl(1.15, 1.15, 0.4, at=(-4.0, DECK + 5.5, -12.0), mat=P["iron"], segs=14)
stack.build("funnel", props={"col": 1})

masts = MB()
masts.cyl(0.45, 0.35, 15.0, at=(6.0, DECK, -12.0), mat=P["timber"], segs=10)
masts.cyl(0.12, 0.12, 9.0, at=(6.0, DECK + 10.5, -12.0), mat=P["timber"], segs=6, pitch=math.pi / 2, centered=True)
masts.cyl(0.9, 1.0, 0.8, at=(6.0, DECK + 12.0, -12.0), mat=P["timber_light"], segs=10)
masts.cyl(0.4, 0.15, 7.5, at=(22.0, DECK, -12.0), mat=P["timber"], segs=10)
masts.cyl(0.18, 0.12, 9.0, at=(BOW_TIP - 1.0, DECK + 0.5, -12.0), mat=P["timber"], segs=8, roll=-1.1)
masts.build("masts", props={"col": 1})

for i, (x, z) in enumerate([(-14.0, -8.0), (-13.0, -8.6), (12.0, -16.5), (25.0, -7.5), (26.0, -16.8)]):
    prop("barrel", f"barrel_deck_{i}", x, z, y=DECK)
for i, (x, z) in enumerate([(14.5, -7.2), (15.6, -7.4)]):
    prop("supply_crate", f"crate_deck_{i}", x, z, y=DECK, yaw=0.3 * i)
prop("lantern_post", "lantern_deck", -21.5, -7.0, y=DECK, yaw=math.pi)
prop("lantern_post", "lantern_shelf", -22.5, 9.0, yaw=0.0)

# Lanterns someone left burning in the hold.
prop("lantern_post", "lantern_hold_aft", -12.5, -8.0, y=hold_floor(-12.5, -8.0), yaw=math.pi)
prop("lantern_post", "lantern_hold_fore", 18.0, -8.0, y=hold_floor(18.0, -8.0), yaw=math.pi)

# Clutter in the hold.
for i, (x, z) in enumerate([(22.0, -8.0), (23.5, -8.2), (-2.0, -16.6), (10.0, -16.4), (-15.0, -8.0)]):
    prop("barrel", f"barrel_hold_{i}", x, z, y=hold_floor(x, z))
for i, (x, z) in enumerate([(18.0, -15.8), (-13.5, -9.0)]):
    prop("supply_crate", f"crate_hold_{i}", x, z, y=hold_floor(x, z), yaw=0.2 + i)

# --------------------------------------------------------- landing and the reef

prop("rowboat", "BUOY_boat", -42.5, 4.0, y=0.0, yaw=math.pi / 2, props={"interact": "boat", "range": 6.0, "float": -0.15, "min": -1.0, "max": 2.5})
kit.empty("SPAWN_landing", (-35.0, 2.9, 4.0), yaw=-math.pi / 4)

# Rocks around the shelf (clear of the boat on its west side and of the path
# down the slope) and along the reef edge.
for i in range(10):
    z = rnd.choice((-3.5, -2.0, 9.5, 11.0, 12.5)) + (rnd.random() - 0.5)
    x = -39.2 - rnd.random() * 1.5
    r = 0.8 + rnd.random() * 1.2
    MB().rock(r, mat=P["rock"] if i % 3 else P["rock_dark"], seed=400 + i, squash=0.7).build(f"rock_shelf_{i:02d}", loc=(x, H(x, z) - r * 0.4, z), props={"col": 1})
for i in range(8):
    x = -37.5 + rnd.random() * 7
    z = 21.5 + rnd.random() * 3
    r = 0.8 + rnd.random() * 1.2
    MB().rock(r, mat=P["rock"], seed=450 + i, squash=0.7).build(f"rock_slope_{i:02d}", loc=(x, H(x, z) - r * 0.4, z), props={"col": 1})
for i in range(14):
    x = 46 + (rnd.random() - 0.5) * 6
    z = -20 + rnd.random() * 48
    r = 0.9 + rnd.random() * 1.6
    MB().rock(r, mat=P["rock_dark"], seed=500 + i).build(f"rock_reef_{i:02d}", loc=(x, H(x, z) - r * 0.35, z), props={"col": 1})

# Debris field to the east: wisp country, faint sea-green glows.
for i, (x, z, yaw) in enumerate([(32, 14, 0.4), (38, 22, 2.1), (28, 24, 1.2)]):
    prop("hull_ribs", f"ribs_{i}", x, z, yaw=yaw)
glow = MB()
for i in range(16):
    x = 26 + rnd.random() * 16
    z = 10 + rnd.random() * 16
    glow.sphere(0.08 + rnd.random() * 0.1, at=(x, H(x, z) + 0.05, z), mat=GLOW, subdiv=1)
glow.build("debris_glows")

for i, (x, z) in enumerate([(-2, 26), (16, 28), (34, 6)]):
    prop("dune_grass", f"grass_{i}", x, z, scale=0.9)
prop("tide_pole", "tidepole_reef", -2.5, 9.0, y=0.0, yaw=0.0)
prop("tide_pole", "tidepole_shelf", -18.8, 14.5, y=0.0, yaw=0.0)

# --------------------------------------------------------------- gathering


def node(kind, i, x, z, y=None, prop_name=None):
    return prop(prop_name or kind, f"NODE_{kind}_{i:02d}", x, z, y=y, props={"node": kind})


for i, (x, z) in enumerate([(10, 22), (24, 10), (-2, 14), (38, 3)]):
    node("driftwood", i, x, z)
for i, (x, z, y) in enumerate([(14, 3, None), (30, 20, None), (-12.0, -12.5, DECK), (19.0, -9.0, DECK)]):
    node("scrap_pile", i, x, z, y=y)
for i, (x, z) in enumerate([(24.0, -7.3), (14.0, -16.7), (-6.0, -7.3), (-20.0, -7.3)]):
    node("reinforced_wreckage", i, x, z, y=hold_floor(x, z))
for i, (x, z) in enumerate([(-1, 2), (12, -3)]):
    node("kelp_bed", i, x, z)
node("strongbox", 0, 33.5, -12.0, y=DECK)
kit.empty("NODE_fish_glowgill_00", (-44.0, 0, -8.0), props={"node": "fish_glowgill"})

# ----------------------------------------------------------------- enemies

for i, (x, z) in enumerate([(5, 7), (16, 14), (26, 3), (-1, 19)]):
    kit.empty(f"ENEMY_crab_low_{i}", (x, H(x, z), z), props={"enemy": "brine_crab", "tide": "low"})
for i, (x, y, z) in enumerate([(12.0, 0.3, -12.5), (-3.0, 0.55, -9.0), (30.0, DECK, -12.0)]):
    kit.empty(f"ENEMY_spitter_{i}", (x, y, z), props={"enemy": "drowned_spitter", "tide": "any"})
for i, (x, y, z) in enumerate([(34.0, 2.5, 16.0), (2.0, DECK + 2.0, -12.0), (-17.0, DECK + 2.5, -2.0)]):
    kit.empty(f"ENEMY_wisp_{i}", (x, y, z), props={"enemy": "lantern_wisp", "tide": "any"})
for i, (x, z) in enumerate([(-13.0, 3.0), (8.0, 1.0)]):
    kit.empty(f"ENEMY_lurker_{i}", (x, 0.0, z), props={"enemy": "tide_lurker", "tide": "high"})

# Taking the lens wakes the ship: FX_ambush_<enemy id>_<n>.
kit.empty("FX_ambush_lantern_wisp_1", (-19.0, DECK + 2.5, -10.0))
kit.empty("FX_ambush_lantern_wisp_2", (-29.0, DECK + 3.5, -1.5))
kit.empty("FX_ambush_drowned_spitter_1", (-14.0, DECK, -9.5))

# ---------------------------------------------------- anchors and the beam

# Ground level only: being rescued onto the deck would skip both routes.
for name, (x, z) in {"reef_shelf": (-28, 6), "slope": (-14, 18), "flats": (18, 18), "bow_sand": (36, 12)}.items():
    kit.empty(f"ANCHOR_{name}", (x, H(x, z) + 0.1, z))
# Lantern's Rest lies to the north; its beam shows on the horizon.
kit.empty("FX_home_light", (-140, 0, -320))

kit.save_and_export("art/blender/locations/wreck.blend", "public/assets/models/locations/wreck.glb")
