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

What you collide with stays a set of plain shapes (COL_). Over them: a coursed
stone lighthouse with red bands, a corbelled gallery and a full-size lantern
room; an arched gate; menhirs and fluted pillars round a flagged arena with a
brass compass rose; a stepped, walled stair on piers; a quay at the landing.

    blender -b --factory-startup --python tools/blender/build/beacon.py
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import bmesh  # noqa: E402
import bpy  # noqa: E402
import kit  # noqa: E402
from kit import B, MB, Paint, fbm3, noise2, smoothstep  # noqa: E402
from mathutils import Euler  # noqa: E402

kit.reset()

TEMPLATES = kit.load_props()
P = kit.palette()
FIRE = kit.material("brazier_fire", 0xFFB347, emit=0xFF8A2A, strength=4.0)
# `rnd` lays out the level and is drawn in the same order as it always was;
# the dressing has its own dice.
rnd = random.Random(31)
vr = random.Random(131)

STONE = P["stone"]
STONE_DARK = P["stone_dark"]
ROCK, ROCK_DARK = P["rock"], P["rock_dark"]
RED = Paint(P["paint_red"].mat, 0xA03A2E)
FLAG = Paint(P["stone"].mat, 0xA8A398)
NIGHT = Paint(P["glass_white"].mat, 0x26343C)

SEA = -6.0
ARENA_Y = 3.0
ARENA_R = 15.0
PLATFORM_Y = 7.0
CAUSEWAY_Y = 2.8
TOWER_Z = -32.5
# The arena gate's footing: a plinth from the arena's edge out under the arch, its
# sill the floor you walk through on (the rock falls away steeply there).
GATE_X0, GATE_X1, GATE_HALF = 14.7, 16.9, 4.1
SILL_Y = ARENA_Y + 0.06


def lerp(a, b, t):
    return a + (b - a) * t


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    out = 0
    for sh in (16, 8, 0):
        ca, cb = (a >> sh) & 255, (b >> sh) & 255
        out |= int(round(ca + (cb - ca) * t)) << sh
    return out


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
    n = fbm3(x * 0.14, 0.0, z * 0.14, 61)
    f = fbm3(x * 0.8, 0.0, z * 0.8, 62)
    if y > 2.4:
        # Weathered grey rock, lichen on the tops, darker in the cracks.
        c = mix(0x6C6962, 0x8A867C, 0.5 + 0.6 * n)
        c = mix(c, 0x9A8C56, smoothstep(0.32, 0.6, f) * 0.5)
        return mix(c, 0x55524C, smoothstep(-0.35, -0.6, f) * 0.7)
    if y > 0.5:
        # Between the tides: barnacle grey over weed green.
        return mix(mix(0x5C5A55, 0x4E5842, smoothstep(1.9, 0.6, y)), 0x76726A, smoothstep(0.3, 0.6, f) * 0.4)
    return mix(0x333D38, 0x3F4A40, 0.5 + 0.5 * n)


ground = kit.material("TIDE_rock", 0xFFFFFF, rough=0.95, vcol=True)
kit.terrain("terrain", -50, 75, -55, 45, 1.0, height, color, ground, props={"col": 1})


def H(x, z):
    return height(x, z)


def prop(kind, name, x, z, y=None, yaw=None, props=None, scale=1.0, parent=None):
    """A layout prop: a random turn (yaw None) comes from `rnd`."""
    return kit.place(TEMPLATES, kind, name, (x, H(x, z) if y is None else y, z), yaw=rnd.random() * math.tau if yaw is None else yaw, props=props, scale=scale, parent=parent)


def dress(kind, name, x, z, y=None, yaw=None, scale=1.0, parent=None):
    """A dressing prop: its turn comes from `vr`."""
    return kit.place(TEMPLATES, kind, name, (x, H(x, z) if y is None else y, z), yaw=vr.random() * math.tau if yaw is None else yaw, scale=scale, parent=parent)


def ramp(m, a, b, width, thick, mat=None, bev=0):
    """A flat ramp whose top surface runs from game point a (low) to b (high)."""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    run = math.hypot(dx, dz)
    pitch = math.atan2(dy, run)
    yaw = math.atan2(-dx, -dz)
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - thick / 2 / math.cos(pitch), (a[2] + b[2]) / 2)
    m.box((width, thick, math.hypot(run, dy)), at=mid, mat=mat, pitch=pitch, yaw=yaw, centered=True, bev=bev)


def turned(m, centre, yaw=0.0, roll=0.0, pitch=0.0):
    """Context for rotating whatever primitives are added inside it about `centre`."""

    class _Turn:
        # New vertices are found by identity: a bevel frees and refills slots,
        # so the newest ones aren't always at the end.
        def __enter__(self):
            self.before = set(m.bm.verts)

        def __exit__(self, *exc):
            c = B(*centre)
            R = Euler((pitch, -roll, yaw)).to_matrix()
            for v in m.bm.verts:
                if v not in self.before:
                    v.co = c + R @ (v.co - c)

    return _Turn()


def lettering(m, text, origin, right, up, normal, size, mat):
    """Raised letters: font x along `right`, y along `up`, its face toward `normal` (game vectors)."""
    cu = bpy.data.curves.new("lettering", "FONT")
    cu.body = text
    cu.size = size
    cu.extrude = 0.01
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    ob = bpy.data.objects.new("lettering", cu)
    bpy.context.scene.collection.objects.link(ob)
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(ob)
    tmp = bmesh.new()
    tmp.from_mesh(me)
    vmap = {}
    for v in tmp.verts:
        p = [origin[i] + v.co.x * right[i] + v.co.y * up[i] + v.co.z * normal[i] for i in range(3)]
        vmap[v] = m.bm.verts.new(B(*p))
    m._paint([m.bm.faces.new([vmap[v] for v in f.verts]) for f in tmp.faces], mat, 0.02)
    tmp.free()
    bpy.data.meshes.remove(me)


def barnacles(m, centre, radius, ys, count, size=0.05):
    """Barnacles round a post. `radius` is a number, or a function of height for a tapered pier."""
    cx, cz = centre
    for _ in range(count):
        a = vr.random() * math.tau
        r = size * (0.6 + vr.random() * 0.7)
        y = vr.uniform(*ys)
        rad = radius(y) if callable(radius) else radius
        m.cyl(r, r * 0.35, r * 1.1, at=(cx + math.cos(a) * rad, y, cz + math.sin(a) * rad), mat=P["barnacle"], roll=-math.pi / 2, yaw=-a, segs=5, bev=0, jit=0.12)


def flare(r_base, r_top, y_base, y_top):
    """The surface radius of a pier that widens from r_base to r_top, as a function of height."""
    return lambda y: r_base + (r_top - r_base) * (y - y_base) / (y_top - y_base) - 0.01


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
    MB().rock(r, mat=ROCK, seed=600 + i, squash=0.7).build(f"rock_landing_{i:02d}", loc=(x, H(x, z) - r * 0.4, z), tideline=True, props={"col": 1})

# A quay along the landing's sea edge: dressed blocks, bollards, an iron ring.
quay = MB(61)
for course, y in enumerate((-1.2, 0.0, 1.2, 2.25)):
    z = -9.0 + (0.6 if course % 2 else 0.0)
    while z < 9.0:
        L = min(1.3 + vr.random() * 0.5, 9.0 - z)
        top = min(y + 1.2, 3.05)
        quay.box((0.9, top - y - 0.04, L - 0.06), at=(56.05, y, z + L / 2), mat=STONE_DARK if course < 2 else STONE, bev=0.06, tint=0.8 + 0.25 * vr.random())
        z += L
quay.box((1.1, 0.16, 18.2), at=(55.95, 2.95, 0.0), mat=STONE, bev=0.04, tint=0.9)
quay.ring(0.16, 0.035, at=(56.55, 2.2, 3.0), mat=P["iron"], pitch=math.pi / 2, yaw=math.pi / 2, segs=12, tube_segs=4)
quay.build("quay", tideline=True, grime=0.15)
for i, z in enumerate((-3.2, 3.2)):
    dress("bollard", f"bollard_quay_{i}", 55.3, z, y=3.05, yaw=0.0)
    # Gulls on the bollards and the quay edge: they go up as you land.
    kit.empty(f"FX_perch_bollard_{i}", (55.3, 4.05, z))
kit.empty("FX_perch_quay", (56.2, 3.6, 6.8))

# ---------------------------------------------------------------- causeway

cause_col = MB()
stones = []
x = 41.6
i = 0
while x > 16.4:
    w = 1.8 + rnd.random() * 0.5
    cx = x - w / 2
    h = CAUSEWAY_Y + (rnd.random() - 0.5) * 0.06
    depth = 3.4 + rnd.random() * 0.4
    cz = (rnd.random() - 0.5) * 0.3
    yaw = (rnd.random() - 0.5) * 0.08
    # The last stone runs in under the gate's sill; its pier (slimmer) stands just clear of the footing.
    px, pr = (cx, 1.0) if cx > GATE_X1 + 0.6 else (GATE_X1 + 0.6, 0.7)
    cause_col.box((w - 0.12, 0.5, depth), at=(cx, h - 0.5, cz), yaw=yaw, bev=0)
    cause_col.cyl(0.5 * pr, 0.7 * pr, h - 0.5 - SEA, at=(px, SEA, 0), segs=7, bev=0)
    stones.append((cx, h, w, depth, cz, yaw, i, px, pr))
    x -= w
    i += 1
cause_col.build("COL_causeway", ao=0, grime=0)

# The stones you see: dressed slabs on rough piers, weed and barnacles below the tide.
cause = MB(62)
for cx, h, w, depth, cz, yaw, k, px, pr in stones:
    cause.box((w - 0.16, 0.5, depth - 0.06), at=(cx, h - 0.5, cz), mat=STONE if k % 2 else STONE_DARK, yaw=yaw, bev=0.08, tint=0.85 + 0.2 * vr.random())
    cause.box((w - 0.5, 0.06, depth - 0.5), at=(cx, h - 0.02, cz), mat=STONE, yaw=yaw, bev=0.02, tint=0.75 + 0.15 * vr.random())
    cause.cyl(0.55 * pr, 0.78 * pr, h - 0.5 - SEA, at=(px, SEA, 0), mat=ROCK_DARK, segs=9, tint=0.9)
    # On the pier's surface (it widens as it rises), between the tides.
    barnacles(cause, (px, 0.0), flare(0.55 * pr, 0.78 * pr, SEA, h - 0.5), (-0.4, 1.7), 8)
cause.build("causeway", tideline=True, grime=0.1)

for i, (cx, cz) in enumerate(((27.0, -8.5), (33.0, 8.5))):
    for k in range(5):
        a = rnd.random() * math.tau
        r = 0.6 + rnd.random() * 0.9
        px, pz = cx + math.cos(a) * 2.6, cz + math.sin(a) * 2.6
        MB().rock(r, mat=ROCK_DARK, seed=700 + i * 10 + k).build(f"rock_perch_{i}_{k}", loc=(px, H(px, pz) - r * 0.5, pz), tideline=True)

# -------------------------------------------------------------------- gate

gate_col = MB()
for gz in (-3.2, 3.2):
    gate_col.box((1.4, 5.2, 1.4), at=(16.0, ARENA_Y, gz), bev=0)
    gate_col.box((1.7, 0.4, 1.7), at=(16.0, ARENA_Y + 5.2, gz), bev=0)
gate_col.box((1.4, 0.9, 8.0), at=(16.0, ARENA_Y + 5.6, 0), bev=0)
gate_col.box((GATE_X1 - GATE_X0, SILL_Y - SEA, 2 * GATE_HALF), at=((GATE_X0 + GATE_X1) / 2, SEA, 0), bev=0)  # footing and sill
gate_col.build("COL_gate", ao=0, grime=0)

# Coursed piers, moulded caps, and an arch of voussoirs over the way in.
gate = MB(63)
for gz in (-3.2, 3.2):
    y = ARENA_Y - 0.3
    k = 0
    while y < ARENA_Y + 5.2 - 0.01:
        hgt = min(0.55 + vr.random() * 0.15, ARENA_Y + 5.2 - y)
        gate.box((1.42 + (vr.random() - 0.5) * 0.05, hgt - 0.03, 1.42 + (vr.random() - 0.5) * 0.05), at=(16.0, y, gz), mat=STONE if k % 2 else STONE_DARK, bev=0.06, tint=0.85 + 0.2 * vr.random(), yaw=(vr.random() - 0.5) * 0.04)
        y += hgt
        k += 1
    gate.box((1.75, 0.18, 1.75), at=(16.0, ARENA_Y + 5.2, gz), mat=STONE, bev=0.04)
    gate.box((1.6, 0.24, 1.6), at=(16.0, ARENA_Y + 5.38, gz), mat=STONE_DARK, bev=0.05)
SPRING, SPAN = ARENA_Y + 5.2, 2.5
for k in range(9):
    a0, a1 = math.pi * k / 9, math.pi * (k + 1) / 9
    inner, outer = SPAN, SPAN + 0.9
    pts = [(math.cos(a0) * inner, SPRING + math.sin(a0) * inner * 0.45), (math.cos(a1) * inner, SPRING + math.sin(a1) * inner * 0.45),
           (math.cos(a1) * outer, SPRING + math.sin(a1) * outer * 0.42), (math.cos(a0) * outer, SPRING + math.sin(a0) * outer * 0.42)]
    # Prism outlines lie in the game XY plane; the arch spans z, so build it across x and turn it a quarter.
    with turned(gate, (16.0, 0.0, 0.0), yaw=math.pi / 2):
        gate.prism(pts, 1.3, at=(16.0, 0.0, 0.0), mat=STONE if k % 2 else STONE_DARK, bev=0.03, tint=0.85 + 0.2 * vr.random())
gate.box((1.3, 0.3, 8.2), at=(16.0, ARENA_Y + 6.42, 0), mat=STONE, bev=0.05, tint=0.8)
for gz in (-3.2, 3.2):
    gate.tube([(16.72, ARENA_Y + 0.4, gz + 0.3 * k) for k in range(-1, 2)], 0.05, mat=P["kelp_dark"], segs=4)
gate.build("gate", grime=0.3)

# The footing: big coursed blocks built out from the arena's edge and down into the
# rock, battered (each course down sits a little further out). The top course between
# the piers is the sill, paler and worn; the first causeway stone runs in under it.
plinth = MB(71)
y = -5.0
course = 0
while y < SILL_Y - 0.01:
    hgt = 0.55 + vr.random() * 0.2
    if SILL_Y - (y + hgt) < 0.35:
        hgt = SILL_Y - y
    top = y + hgt
    bat = (SILL_Y - top) * 0.035
    x1, z1 = GATE_X1 + bat, GATE_HALF + bat
    if top < SILL_Y - 0.01:
        # Long blocks along the seaward face, each split once front to back at a staggered joint.
        xm = GATE_X0 + (GATE_X1 - GATE_X0) * (0.35 + 0.3 * vr.random())
        z = -z1
        while z < z1 - 0.01:
            L = min(1.1 + vr.random() * 0.6, z1 - z)
            if z1 - (z + L) < 0.5:
                L = z1 - z
            for xa, xb in ((GATE_X0, xm), (xm, x1)):
                plinth.box((xb - xa - 0.03, hgt - 0.03, L - 0.03), at=((xa + xb) / 2, y, z + L / 2), mat=STONE if (course + round(z)) % 2 else STONE_DARK, bev=0.06, tint=0.72 + 0.25 * vr.random())
            z += L
    else:
        # Under each pier a single block; between them three sill slabs, worn round at the edges.
        for za, zb in ((-z1, -2.5), (2.5, z1)):
            plinth.box((x1 - GATE_X0 - 0.03, hgt - 0.03, zb - za - 0.03), at=((GATE_X0 + x1) / 2, y, (za + zb) / 2), mat=STONE_DARK, bev=0.06, tint=0.8 + 0.15 * vr.random())
        for k, (za, zb) in enumerate(((-2.5, -0.8), (-0.8, 0.85), (0.85, 2.5))):
            plinth.box((x1 - GATE_X0 - 0.04, hgt - 0.02, zb - za - 0.04), at=((GATE_X0 + x1) / 2, y, (za + zb) / 2), mat=STONE, bev=0.1, tint=0.88 + 0.12 * vr.random(), yaw=(vr.random() - 0.5) * 0.015)
    y = top
    course += 1
# Weed hanging down the seaward face between the tides, clear of the causeway's stone.
for gz in (-3.3, -2.1, 2.4, 3.4):
    hang = [(GATE_X1 + (SILL_Y - yy) * 0.035 + 0.03, yy, gz + 0.12 * math.sin(yy * 3.0 + gz)) for yy in (1.7, 1.25, 0.8, 0.4)]
    plinth.tube(hang, 0.045, mat=P["kelp_dark"], segs=4)
plinth.build("gate_footing", tideline=True, grime=0.25)

# ------------------------------------------------------------------- arena

ring_col = MB()
menhirs = []
for k in range(18):
    a = k / 18 * math.tau
    deg = math.degrees(a)
    # Openings: the gate (east), the stair (north) and the Guardian's side (south).
    if deg < 22 or deg > 338 or 248 < deg < 292 or 80 < deg < 100:
        continue
    r = ARENA_R - 0.9
    sx, sz = math.cos(a) * r, math.sin(a) * r
    h = 1.0 + rnd.random() * 0.9
    roll = (rnd.random() - 0.5) * 0.15
    ring_col.box((1.3, h, 0.8), at=(sx, ARENA_Y - 0.2, sz), yaw=-a + math.pi / 2, roll=roll, bev=0)
    menhirs.append((sx, sz, h, -a + math.pi / 2, roll, k))
ring_col.build("COL_arena_stones", ao=0, grime=0)

# Each stone fills its collision box: rings of a rounded oblong, weathered
# with noise and drawn in to a rounded top, stood at the box's own lean.
stones_v = MB(64)
for sx, sz, h, yaw, roll, k in menhirs:
    y0 = ARENA_Y - 0.2
    secs = []
    for t in (1.0, 0.93, 0.8, 0.6, 0.35, 0.1, 0.0):
        n0 = fbm3(sx * 0.7, t * 3.0, sz * 0.7, 70 + k)
        shrink = (1.0 - 0.3 * t * t) * (0.97 + 0.06 * n0) * (0.55 if t == 1.0 else 1.0)
        y = y0 + h * t - (0.0 if t < 0.9 else 0.1 * h * (1.0 + n0))
        ring = []
        for j in range(12):
            a = j / 12 * math.tau
            ca, sa = math.cos(a), math.sin(a)
            bump = 1.0 + 0.07 * fbm3(ca * 2.0 + k, t * 4.0, sa * 2.0, 90)
            ring.append((sx + math.copysign(abs(ca) ** 0.6, ca) * 0.65 * shrink * bump, y, sz + math.copysign(abs(sa) ** 0.6, sa) * 0.4 * shrink * bump))
        secs.append(ring)
    with turned(stones_v, (sx, y0 + h / 2, sz), yaw=yaw, roll=roll):
        stones_v.loft(secs, mat=STONE_DARK if k % 3 else ROCK, closed=True, cap=True, tint=0.85 + 0.2 * vr.random())
stones_v.build("arena_stones", grime=0.35, smooth=40)

cover_col = MB()
for k in range(4):
    a = math.pi / 4 + k * math.pi / 2
    cover_col.cyl(1.1, 1.25, 2.3, at=(math.cos(a) * 8.0, ARENA_Y - 0.1, math.sin(a) * 8.0), segs=9, bev=0)
    cover_col.cyl(1.35, 1.35, 0.3, at=(math.cos(a) * 8.0, ARENA_Y + 2.2, math.sin(a) * 8.0), segs=9, bev=0)
cover_col.build("COL_arena_pillars", ao=0, grime=0)

# Fluted columns in stacked drums, capitals on top; two have cracked and slipped.
pillars = MB(65)
for k in range(4):
    a = math.pi / 4 + k * math.pi / 2
    px, pz = math.cos(a) * 8.0, math.sin(a) * 8.0
    pillars.cyl(1.32, 1.36, 0.3, at=(px, ARENA_Y - 0.1, pz), mat=STONE_DARK, segs=16, bev=0.04)
    y = ARENA_Y + 0.2
    for d in range(4):
        r0 = 1.22 - d * 0.03
        tilt = 0.04 if (k % 2 and d == 3) else 0.0
        with turned(pillars, (px, y, pz), roll=tilt, yaw=a):
            pillars.lathe([(r0, 0.0), (r0 - 0.02, 0.48)], at=(px + (vr.random() - 0.5) * 0.03, y, pz), mat=STONE, segs=16, staves=0.07, tint=0.85 + 0.15 * vr.random())
        y += 0.5
    with turned(pillars, (px, ARENA_Y + 2.2, pz), roll=0.05 if k % 2 else 0.0):
        pillars.box((2.5, 0.16, 2.5), at=(px, ARENA_Y + 2.2, pz), mat=STONE, bev=0.04, yaw=a)
        pillars.box((2.2, 0.16, 2.2), at=(px, ARENA_Y + 2.36, pz), mat=STONE_DARK, bev=0.04, yaw=a)
pillars.build("arena_pillars", grime=0.3)

# Flagstones in rings round the compass rose (a hair above the rock you
# stand on), some cracked, some lost to the sea.
flags = MB(66)
r = 3.5
while r < ARENA_R - 1.6:
    width = 1.05 + vr.random() * 0.2
    n = max(8, int(2 * math.pi * (r + width / 2) / 1.35))
    off = vr.random()
    for s in range(n):
        if vr.random() < 0.06:
            continue
        a0 = (s + off) / n * math.tau + 0.012
        a1 = (s + 1 + off) / n * math.tau - 0.012
        r0, r1 = r + 0.025, r + width - 0.025
        y = ARENA_Y + 0.05 + vr.random() * 0.012
        pts = [(math.cos(a1) * r0, math.sin(a1) * r0), (math.cos(a1) * r1, math.sin(a1) * r1), (math.cos(a0) * r1, math.sin(a0) * r1), (math.cos(a0) * r0, math.sin(a0) * r0)]
        q = [flags.bm.verts.new(B(px, y, pz)) for px, pz in pts]
        flags._paint([flags.bm.faces.new(q)], FLAG, 0.1, 0.75 + 0.3 * vr.random())
    r += width
flags.build("arena_flags", ao=0.0, grime=0.0)

# The compass rose: a dark disc, a brass ring, eight brass points and the
# letters of the four winds (north is the tower).
rose = MB(67)
rose.cyl(3.3, 3.3, 0.05, at=(0, ARENA_Y + 0.01, 0), mat=ROCK_DARK, segs=32)
rose.ring(3.2, 0.06, at=(0, ARENA_Y + 0.06, 0), mat=P["brass"], segs=40, tube_segs=4)
rose.ring(2.15, 0.035, at=(0, ARENA_Y + 0.06, 0), mat=P["brass"], segs=32, tube_segs=4)
for k in range(8):
    a = k * math.pi / 4
    L = 2.9 if k % 2 == 0 else 1.9
    tip = (math.cos(a) * L, math.sin(a) * L)
    side = (-math.sin(a) * (0.32 if k % 2 == 0 else 0.22), math.cos(a) * (0.32 if k % 2 == 0 else 0.22))
    for sgn in (1, -1):
        q = [rose.bm.verts.new(B(px, ARENA_Y + 0.065, pz)) for px, pz in ((0.0, 0.0), (side[0] * sgn, side[1] * sgn), tip)]
        f = rose.bm.faces.new(q if sgn > 0 else list(reversed(q)))
        rose._paint([f], P["gilt"] if sgn > 0 else P["brass"], 0.03)
for letter, (dx, dz) in (("N", (0.0, -1.0)), ("E", (1.0, 0.0)), ("S", (0.0, 1.0)), ("W", (-1.0, 0.0))):
    lettering(rose, letter, (dx * 2.65, ARENA_Y + 0.07, dz * 2.65), (-dz, 0.0, dx), (dx, 0.0, dz), (0.0, 1.0, 0.0), 0.55, P["gilt"])
rose.build("arena_rose", grime=0.0, ao=0.3)

kit.empty("FX_arena", (0, ARENA_Y, 0))
# Entering the ring wakes the Guardian; leaving it (19 m out) sends it back down.
trig = MB().box((32.0, 8.0, 32.0), at=(0, ARENA_Y - 1.0, 0)).build("TRIG_boss", props={"event": "boss"})
trig.display_type = "WIRE"  # so it doesn't hide the arena when you open the .blend
trig.hide_render = True
kit.empty("ENEMY_guardian", (0, 0, 18.5), props={"enemy": "wreck_guardian", "tide": "any"})

# ------------------------------------------------- the stair up to the tower

STAIR_FOOT = (0.0, ARENA_Y, -14.4)
STAIR_TOP = (0.0, PLATFORM_Y, -27.0)
stair_col = MB()
ramp(stair_col, STAIR_FOOT, STAIR_TOP, 3.2, 0.5)
# Side walls a metre over the ramp: you can't hop onto it from the arena's edge.
for sx in (-1.8, 1.8):
    ramp(stair_col, (sx, STAIR_FOOT[1] + 1.0, STAIR_FOOT[2] - 1.0), (sx, STAIR_TOP[1] + 1.0, STAIR_TOP[2]), 0.4, 1.6)
# Piers holding the stair over the water.
PIERS = []
for k in range(4):
    z = -16.5 - k * 3.0
    y = ARENA_Y + (PLATFORM_Y - ARENA_Y) * (STAIR_FOOT[2] - z) / (STAIR_FOOT[2] - STAIR_TOP[2])
    stair_col.cyl(1.2, 1.5, y - 0.4 - SEA, at=(0, SEA, z), segs=8, bev=0)
    PIERS.append((z, y))
stair_col.build("COL_stair", ao=0, grime=0)


def stair_y(z):
    return ARENA_Y + (PLATFORM_Y - ARENA_Y) * (STAIR_FOOT[2] - z) / (STAIR_FOOT[2] - STAIR_TOP[2])


# Steps over the ramp (their treads straddle its surface), coped parapets,
# and the piers with arches between them.
stair = MB(68)
n_steps = 20
for k in range(n_steps):
    z0 = STAIR_FOOT[2] - (STAIR_FOOT[2] - STAIR_TOP[2]) * k / n_steps
    z1 = STAIR_FOOT[2] - (STAIR_FOOT[2] - STAIR_TOP[2]) * (k + 1) / n_steps
    top = stair_y((z0 + z1) / 2) + 0.1
    stair.box((3.2, top - (stair_y(z0) - 0.6), z0 - z1 + 0.04), at=(0.0, stair_y(z0) - 0.6, (z0 + z1) / 2), mat=STONE if k % 2 else STONE_DARK, bev=0.04, tint=0.85 + 0.2 * vr.random())
for sx in (-1.8, 1.8):
    segs = 6
    for k in range(segs):
        za = STAIR_FOOT[2] - 1.0 + (STAIR_TOP[2] - STAIR_FOOT[2] + 1.0) * k / segs
        zb = STAIR_FOOT[2] - 1.0 + (STAIR_TOP[2] - STAIR_FOOT[2] + 1.0) * (k + 1) / segs
        ya = STAIR_FOOT[1] + 1.0 + (STAIR_TOP[1] - STAIR_FOOT[1]) * k / segs
        yb = STAIR_FOOT[1] + 1.0 + (STAIR_TOP[1] - STAIR_FOOT[1]) * (k + 1) / segs
        ramp(stair, (sx, ya - 0.12, za), (sx, yb - 0.12, zb), 0.42, 1.55, STONE_DARK if k % 2 else STONE, bev=0.04)
        ramp(stair, (sx, ya + 0.02, za), (sx, yb + 0.02, zb), 0.56, 0.16, STONE, bev=0.03)
for z, y in PIERS:
    stair.cyl(1.25, 1.55, y - 0.45 - SEA, at=(0, SEA, z), mat=ROCK_DARK, segs=10, tint=0.85)
    barnacles(stair, (0.0, z), flare(1.25, 1.55, SEA, y - 0.45), (-1.0, 1.7), 14)
for (za, ya), (zb, yb) in zip(PIERS, PIERS[1:]):
    zm = (za + zb) / 2
    for k in range(7):
        a0, a1 = math.pi * k / 7, math.pi * (k + 1) / 7
        rr, ro = 0.85, 1.35
        top = min(ya, yb) - 0.5
        pts = [(zm + math.cos(a0) * rr, top - 1.3 + math.sin(a0) * rr), (zm + math.cos(a1) * rr, top - 1.3 + math.sin(a1) * rr),
               (zm + math.cos(a1) * ro, top - 1.3 + math.sin(a1) * ro), (zm + math.cos(a0) * ro, top - 1.3 + math.sin(a0) * ro)]
        with turned(stair, (0.0, 0.0, 0.0), yaw=math.pi / 2):
            stair.prism([(-p[0], p[1]) for p in pts], 2.6, at=(0.0, 0.0, 0.0), mat=STONE_DARK, bev=0.02, tint=0.8 + 0.2 * vr.random())
stair.build("stair", tideline=True, grime=0.2)

# Rubble across the stair's foot until the Guardian falls (the solid part is a
# hidden box under the rocks, so it goes when they do).
rubble = MB()
for k in range(9):
    rx = -1.9 + (k % 3) * 1.9 + (rnd.random() - 0.5) * 0.4
    rz = -15.0 - (k // 3) * 0.75
    r = 0.9 + rnd.random() * 0.4
    rubble.rock(r, at=(rx, ARENA_Y + 0.5 + (k // 3) * 0.55, rz), mat=ROCK if k % 2 else ROCK_DARK, seed=800 + k, squash=0.85)
for k in range(6):
    rubble.rock(0.55 + vr.random() * 0.35, at=(vr.uniform(-2.0, 2.0), ARENA_Y + 1.4 + vr.random() * 1.0, vr.uniform(-16.8, -14.8)), mat=STONE_DARK if k % 2 else ROCK, seed=820 + k, squash=0.8)
rubble_ob = rubble.build("STATE_guardian_defeated_off", props={"col": 1})
blocker = MB().box((4.6, 2.7, 2.6), at=(0, ARENA_Y, -15.6), bev=0).build("COL_rubble", parent=rubble_ob, ao=0, grime=0)

# Braziers that light the way once the Guardian is gone.
lit = kit.empty("STATE_guardian_defeated_on", (0, 0, 0))
for k, bx in enumerate((-2.6, 2.6)):
    br = MB()
    br.cyl(0.25, 0.3, 1.1, mat=P["iron"], segs=8)
    br.cyl(0.55, 0.35, 0.35, at=(0, 1.1, 0), mat=P["iron"], segs=10)
    br.sphere(0.32, at=(0, 1.42, 0), mat=FIRE, scale=(1, 0.7, 1), subdiv=1)
    for j in range(3):
        a = j / 3 * math.tau
        br.box((0.06, 0.5, 0.06), at=(math.cos(a) * 0.45, 1.05, math.sin(a) * 0.45), mat=P["iron"], yaw=-a, roll=0.35, bev=0)
    br.build(f"brazier_{k}", loc=(bx, ARENA_Y, -13.8), parent=lit, props={"light": "warm", "light_offset": [0, 1.6, 0]})

# ----------------------------------------------------------- tower platform

tower_col = MB()
tower_col.cyl(3.4, 2.9, 12.0, at=(0, PLATFORM_Y, TOWER_Z), segs=18, bev=0)
tower_col.cyl(3.75, 3.75, 0.45, at=(0, PLATFORM_Y + 12.0, TOWER_Z), segs=18, bev=0)
tower_col.cyl(1.8, 1.8, 4.6, at=(0, PLATFORM_Y + 12.45, TOWER_Z), segs=12, bev=0)
# A parapet round the platform's edge, open where the stair arrives.
for x0, x1, z0, z1 in ((-9.0, -1.9, -26.75, -26.25), (1.9, 9.0, -26.75, -26.25), (-9.25, -8.75, -38.0, -26.5), (8.75, 9.25, -38.0, -26.5), (-9.0, 9.0, -38.25, -37.75)):
    tower_col.box((x1 - x0, 0.75, z1 - z0), at=((x0 + x1) / 2, PLATFORM_Y - 0.1, (z0 + z1) / 2), bev=0)
tower_col.build("COL_tower", ao=0, grime=0)

tower = MB(69)
TOP = 12.0  # shaft height over the platform


def shaft_r(y):
    return 3.4 + (2.9 - 3.4) * y / TOP


tower.cyl(3.75, 3.6, 0.6, at=(0, PLATFORM_Y - 0.1, TOWER_Z), mat=STONE_DARK, segs=24, bev=0.05)
y = 0.5
k = 0
while y < TOP - 0.01:
    hgt = min(0.5, TOP - y)
    banded = 4.0 <= y < 5.0 or 8.5 <= y < 9.5
    tower.cyl(shaft_r(y) + 0.01, shaft_r(y + hgt) + 0.01, hgt - 0.02, at=(0, PLATFORM_Y + y + 0.01, TOWER_Z), mat=RED if banded else STONE, segs=24, bev=0.012, tint=(0.95 if k % 2 else 0.86) + 0.06 * vr.random(), yaw=k * 0.13)
    y += hgt
    k += 1
# The door, facing the stair: an arched recess with a stone surround and a step.
DZ = TOWER_Z + shaft_r(1.3)
tower.box((1.7, 2.5, 0.3), at=(0.0, PLATFORM_Y, DZ - 0.12), mat=P["hull_dark"], bev=0.01)
tower.cyl(0.85, 0.85, 0.3, at=(0.0, PLATFORM_Y + 2.5, DZ - 0.12), mat=P["hull_dark"], pitch=math.pi / 2, centered=True, segs=14)
for j in range(9):
    a = math.pi * j / 8
    tower.box((0.36, 0.36, 0.3), at=(math.cos(a) * 1.05, PLATFORM_Y + 2.5 + math.sin(a) * 1.05, DZ + 0.06), mat=STONE_DARK if j % 2 else STONE, roll=a - math.pi / 2, centered=True, bev=0.03)
for sx in (-1.05, 1.05):
    tower.box((0.36, 2.5, 0.3), at=(sx, PLATFORM_Y, DZ + 0.06), mat=STONE, bev=0.03)
tower.box((2.6, 0.18, 0.9), at=(0.0, PLATFORM_Y, DZ + 0.45), mat=STONE_DARK, bev=0.04)
# Small arched windows climbing round the shaft.
for j, (wy, wa) in enumerate(((3.6, 0.9), (6.8, -1.1), (10.0, 2.4))):
    r = shaft_r(wy)
    cx, cz = math.sin(wa) * (r + 0.02), TOWER_Z + math.cos(wa) * (r + 0.02)
    with turned(tower, (cx, 0.0, cz), yaw=wa):
        tower.box((0.55, 0.9, 0.12), at=(cx, PLATFORM_Y + wy, cz), mat=NIGHT, bev=0)
        tower.cyl(0.275, 0.275, 0.12, at=(cx, PLATFORM_Y + wy + 0.9, cz), mat=NIGHT, pitch=math.pi / 2, centered=True, segs=10)
        tower.box((0.85, 0.12, 0.26), at=(cx, PLATFORM_Y + wy - 0.12, cz), mat=STONE, bev=0.02)
        for s in (-0.36, 0.36):
            tower.box((0.14, 1.0, 0.18), at=(cx + s, PLATFORM_Y + wy - 0.05, cz), mat=STONE, bev=0.02)
# Corbels under the gallery, the gallery deck, and its iron railing.
for j in range(24):
    a = j / 24 * math.tau
    ca, sa = math.cos(a), math.sin(a)
    with turned(tower, (ca * 2.95, 0.0, TOWER_Z + sa * 2.95), yaw=-a):
        tower.prism([(0.0, 0.0), (0.0, -0.8), (0.2, -0.75), (0.75, 0.0)], 0.32, at=(ca * 2.95, PLATFORM_Y + TOP, TOWER_Z + sa * 2.95), mat=STONE, bev=0.02)
tower.cyl(3.78, 3.78, 0.45, at=(0, PLATFORM_Y + TOP, TOWER_Z), mat=STONE_DARK, segs=32, bev=0.03)
for j in range(32):
    a = j / 32 * math.tau
    tower.cyl(0.035, 0.035, 1.05, at=(math.cos(a) * 3.6, PLATFORM_Y + TOP + 0.45, TOWER_Z + math.sin(a) * 3.6), mat=P["iron"], segs=6, bev=0)
for ry in (0.55, 1.08):
    tower.ring(3.6, 0.03, at=(0, PLATFORM_Y + TOP + 0.45 + ry, TOWER_Z), mat=P["iron"], segs=48, tube_segs=4)
tower.build("tower", grime=0.25, smooth=35)

# The lantern room: Saltmere's beehive lens, astragals and copper dome, at
# full size on the gallery. The beam turns at the lens.
LAMP_SCALE = 2.0
prop("beacon_lamp", "beacon_lamp_top", 0, TOWER_Z, y=PLATFORM_Y + TOP + 0.45, yaw=0.0, scale=LAMP_SCALE)
kit.empty("FX_beacon_lamp", (0, PLATFORM_Y + TOP + 0.45 + 1.02 * LAMP_SCALE, TOWER_Z))
kit.empty("FX_gulls", (0, 0, TOWER_Z))

# Where you carry the Ember: a stone plinth and a brass bowl at the door.
plinth = MB()
plinth.cyl(0.6, 0.75, 1.0, mat=STONE, segs=10)
plinth.cyl(0.65, 0.45, 0.3, at=(0, 1.0, 0), mat=P["brass"], segs=12)
plinth.build("INT_beacon", loc=(0, PLATFORM_Y, -27.6), props={"interact": "beacon", "range": 3.6, "col": 1})

# The platform's parapet and paving.
plat = MB(70)
for x0, x1, z0, z1 in ((-9.0, -1.9, -26.75, -26.25), (1.9, 9.0, -26.75, -26.25), (-9.25, -8.75, -38.0, -26.5), (8.75, 9.25, -38.0, -26.5), (-9.0, 9.0, -38.25, -37.75)):
    along_x = (x1 - x0) > (z1 - z0)
    L = (x1 - x0) if along_x else (z1 - z0)
    n = max(1, int(L / 1.4))
    for j in range(n):
        if along_x:
            a, b = x0 + L * j / n, x0 + L * (j + 1) / n
            plat.box((b - a - 0.04, 0.62, 0.5), at=((a + b) / 2, PLATFORM_Y - 0.1, (z0 + z1) / 2), mat=STONE if j % 2 else STONE_DARK, bev=0.05, tint=0.85 + 0.2 * vr.random())
        else:
            a, b = z0 + L * j / n, z0 + L * (j + 1) / n
            plat.box((0.5, 0.62, b - a - 0.04), at=((x0 + x1) / 2, PLATFORM_Y - 0.1, (a + b) / 2), mat=STONE if j % 2 else STONE_DARK, bev=0.05, tint=0.85 + 0.2 * vr.random())
    plat.box(((x1 - x0) + 0.12, 0.14, (z1 - z0) + 0.12), at=((x0 + x1) / 2, PLATFORM_Y + 0.52, (z0 + z1) / 2), mat=STONE, bev=0.03)
for gx in range(-4, 4):
    for gz in range(5):
        x, z = gx * 2.0 + 1.0, -27.6 - gz * 2.0 - 1.0
        if math.hypot(x, z - TOWER_Z) < 4.0 or vr.random() < 0.1:
            continue
        plat.box((1.94, 0.04, 1.94), at=(x, PLATFORM_Y + 0.03, z), mat=FLAG, bev=0.015, tint=0.75 + 0.3 * vr.random())
plat.build("platform", grime=0.15)

for k in range(8):
    a = rnd.random() * math.tau
    px, pz = math.cos(a) * 7.5, -32.0 + math.sin(a) * 4.5
    if pz > -28:
        continue
    r = 0.6 + rnd.random() * 0.8
    MB().rock(r, mat=ROCK, seed=900 + k, squash=0.7).build(f"rock_platform_{k}", loc=(px, H(px, pz) - r * 0.4, pz), props={"col": 1})

# Lanterns along the causeway, lit once the chapter's done.
done = kit.empty("STATE_chapter1_complete_on", (0, 0, 0))
for k, lx in enumerate((22.0, 30.0, 38.0)):
    prop("lantern_post", f"lantern_causeway_{k}", lx, 1.9 if k % 2 else -1.9, y=CAUSEWAY_Y, yaw=math.pi / 2, parent=done)

# Wrack on the landing and at the arena's seaward edge.
for i, (x, z, yaw) in enumerate(((46.5, 6.0, 0.3), (52.5, -7.0, 2.0), (-9.0, 10.8, 0.9), (6.5, 12.6, 2.6))):
    dress("seaweed", f"wrack_{i}", x, z, yaw=yaw)

# ----------------------------------------------------------------- enemies

for k, (sx, sz) in enumerate(((27.0, -8.5), (33.0, 8.5))):
    kit.empty(f"ENEMY_spitter_{k}", (sx, 3.4, sz), props={"enemy": "drowned_spitter", "tide": "any"})
for k, gz in enumerate((-4.5, 4.5)):
    kit.empty(f"ENEMY_wisp_{k}", (18.5, ARENA_Y + 2.5, gz), props={"enemy": "lantern_wisp", "tide": "any"})

# ------------------------------------------------------------------ gloom

# GLOOM_ pockets on the causeway, between the Spitters' rocks: flare through
# them (and dazzle whoever's spitting) or take the chill. Clear of the anchor.
for k, gx in enumerate((35.5, 24.0)):
    kit.empty(f"GLOOM_causeway_{k}", (gx, CAUSEWAY_Y, 0.0), props={"radius": 2.6})

# ---------------------------------------------------- anchors and the beam

for name, (ax, ay, az) in {"landing": (48, 3.1, 0), "causeway": (30, CAUSEWAY_Y + 0.1, 0), "arena_e": (11, 3.1, 0), "arena_n": (0, 3.1, -10)}.items():
    kit.empty(f"ANCHOR_{name}", (ax, ay, az))
# Lantern's Rest lies south-west.
kit.empty("FX_home_light", (-250, 0, 260))

kit.save_and_export("art/blender/locations/beacon.blend", "public/assets/models/locations/beacon.glb")
