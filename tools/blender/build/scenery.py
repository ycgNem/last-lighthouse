"""Builds art/blender/scenery/scenery.blend and public/assets/models/scenery.glb.

The drowned world on the horizon: what the sea took, standing out of it. Every
location sets some of these round itself, far out past where you can go
(src/data/scenery.ts), so the first thing you see past the surf is the
premise: rooftops and a church spire with the tide round their eaves,
telegraph poles walking a drowned road out to sea, the masts of a ship that
went down whole, sea stacks, a far headland and a lighthouse whose light went
out.

Each SCENE_<piece> stands on the low-water line (y 0 = low water, y 1.8 =
high water) and runs down to the seabed, so the sea always hides its foot, and
the tideline band shows how far up each tide climbs. They're seen at 70-170 m
through fog, so they're built for the silhouette and the big shapes: clear
roof pitches, tall verticals, broken edges. Nothing here is solid; the game
merges them all into a few draw calls.

    blender -b --factory-startup --python tools/blender/build/scenery.py
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import kit  # noqa: E402
from kit import MB, Paint  # noqa: E402

kit.reset()
P = kit.palette()
rnd = random.Random(7)

STONE, WOOD, IRON, GLASS, PLANT, PAINT = (P[k].mat for k in ("stone", "timber", "iron", "glass_white", "grass", "paint_white"))
WASH = Paint(STONE, 0xD9D3C4)
OCHRE = Paint(STONE, 0xC9B48A)
GREYWASH = Paint(STONE, 0xB4BAB4)
GRANITE = Paint(STONE, 0x8F8B82)
SLATE = Paint(STONE, 0x3A434A)
SLATE_DARK = Paint(STONE, 0x2C3338)
DARK = Paint(GLASS, 0x161C20)
TAR = P["tar"]
RAFTER = Paint(WOOD, 0x3C3128)
FRAME = Paint(PAINT, 0xBDB6A4)
REDBAND = Paint(PAINT, 0x8E3A30)
TURF = Paint(PLANT, 0x5F6B3F)
CANVAS = Paint(P["canvas"].mat, 0x9C927C)
SEABED = -4.5


def slope(m, w, run, rise, at, mat, back=False, thick=0.16, overhang=0.35):
    """One pitch of a gable roof, its eave on the ridge's front (+z) side, or back.
    `at` = (x, eave y, eave z); `run` is the horizontal eave-to-ridge distance."""
    x, y, z = at
    ang = math.atan2(rise, run)
    L = math.hypot(run, rise) + overhang
    s = -1 if back else 1
    cz = z - s * (run - overhang) / 2
    m.box((w + 2 * overhang, thick, L), at=(x, y + rise / 2, cz), mat=mat, pitch=s * ang, centered=True, bev=0.03)


def rafters(m, w, run, rise, at, back=False, gap=0.55, missing=()):
    """Bare rafters where a pitch has lost its slates."""
    x0, y, z = at
    ang = math.atan2(rise, run)
    L = math.hypot(run, rise)
    s = -1 if back else 1
    n = int(w / gap)
    for i in range(n + 1):
        if i in missing:
            continue
        x = x0 - w / 2 + i * w / n
        m.box((0.09, 0.14, L), at=(x, y + rise / 2, z - s * run / 2), mat=RAFTER, pitch=s * ang, centered=True, bev=0.01, jit=0.12)
    # The ridge beam and a purlin halfway down.
    m.box((w + 0.2, 0.18, 0.16), at=(x0, y + rise - 0.05, z - s * run), mat=RAFTER, centered=True, bev=0.02)
    m.box((w + 0.2, 0.12, 0.12), at=(x0, y + rise / 2 - 0.05, z - s * run / 2), mat=RAFTER, pitch=s * ang, centered=True, bev=0.01)


def gable_end(m, d, rise, at, mat):
    """The triangle of wall under a gable, at an end of the ridge (ridge along x)."""
    x, y, z = at
    m.prism([(-d / 2, 0.0), (d / 2, 0.0), (0.0, rise)], 0.3, at=(x, y, z), mat=mat, yaw=math.pi / 2, bev=0.03)


def chimney(m, at, w=0.9, h=1.9, mat=GRANITE, pots=2):
    x, y, z = at
    m.box((w, h, 0.75), at=(x, y, z), mat=mat, bev=0.04)
    m.box((w + 0.12, 0.14, 0.87), at=(x, y + h - 0.14, z), mat=mat, bev=0.03)
    for k in range(pots):
        px = x + (k - (pots - 1) / 2) * 0.36
        m.cyl(0.13, 0.11, 0.4, at=(px, y + h, z), mat=Paint(STONE, 0x8A5A44), segs=8)


def window(m, at, w=0.8, h=1.0, broken=False):
    """A dark upper-floor window in a +z wall, with its frame and sill."""
    x, y, z = at
    m.box((w, h, 0.06), at=(x, y, z + 0.02), mat=DARK, bev=0)
    m.box((w + 0.16, 0.1, 0.12), at=(x, y - 0.08, z + 0.06), mat=FRAME, bev=0.015)
    m.box((w + 0.12, 0.08, 0.08), at=(x, y + h, z + 0.05), mat=FRAME, bev=0.01)
    for sx in (-1, 1):
        m.box((0.07, h, 0.08), at=(x + sx * w / 2, y, z + 0.05), mat=FRAME, bev=0.01)
    if not broken:
        m.box((0.05, h, 0.07), at=(x, y, z + 0.05), mat=FRAME, bev=0)
        m.box((w, 0.05, 0.07), at=(x, y + h / 2, z + 0.05), mat=FRAME, bev=0)


# ------------------------------------------------------------- house row
# Three cottages of a drowned street, eaves a few feet above high water: whitewash,
# ochre and grey, slate roofs, the end one stripped to its rafters.

row = MB(1)
D = 6.0
houses = [(-6.2, 6.0, 3.6, WASH, False), (-0.3, 5.6, 3.1, OCHRE, False), (5.9, 6.6, 3.9, GREYWASH, True)]
for i, (cx, w, eave, wall, stripped) in enumerate(houses):
    row.box((w, eave - SEABED, D), at=(cx, SEABED, 0), mat=wall, bev=0.05, tint=0.95 + 0.1 * rnd.random())
    rise = 2.3
    if stripped:
        rafters(row, w, D / 2, rise, (cx, eave, D / 2), missing=(3, 4))
        rafters(row, w, D / 2, rise, (cx, eave, -D / 2), back=True, missing=(6,))
        # A few slates still clinging on near the eaves.
        slope(row, w * 0.45, D / 2 * 0.35, rise * 0.35, (cx - w * 0.25, eave, D / 2), SLATE)
    else:
        slope(row, w, D / 2, rise, (cx, eave, D / 2), SLATE if i % 2 == 0 else SLATE_DARK)
        slope(row, w, D / 2, rise, (cx, eave, -D / 2), SLATE, back=True)
    # Upper windows on the street side; the doors are long under.
    for k in (-1, 1):
        window(row, (cx + k * w * 0.24, eave - 1.65, D / 2), broken=(i == 1 and k == 1))
    chimney(row, (cx + w / 2 - 0.55, eave + rise - 0.6, 0.0), pots=1 + (i % 2))
# Gable ends of the row, and the steps where the eaves change height.
gable_end(row, D, 2.3, (houses[0][0] - houses[0][1] / 2 + 0.15, houses[0][2], 0.0), WASH)
gable_end(row, D, 2.3, (houses[2][0] + houses[2][1] / 2 - 0.15, houses[2][2], 0.0), GREYWASH)
# A garden wall and its gatepost, just breaking the surface in front.
for k in range(7):
    x = -9.0 + k * 1.9
    row.box((1.8, 0.5 + 0.25 * rnd.random(), 0.45), at=(x, -0.2, D / 2 + 2.6), mat=GRANITE, bev=0.08, tint=0.8 + 0.3 * rnd.random())
row.box((0.5, 1.3, 0.5), at=(4.4, -0.2, D / 2 + 2.6), mat=GRANITE, bev=0.06)
row.build("SCENE_house_row", tideline=True, grime=0.0, ao=0.6)

# --------------------------------------------------------------- spire
# The parish church: a square tower to the belfry, a slate spire on it and the
# nave's roof ridge behind, the clock stopped at the hour the water came.

sp = MB(2)
T = 2.6  # tower half-width
TOP = 14.0
sp.box((2 * T, TOP - SEABED, 2 * T), at=(0, SEABED, 0), mat=GRANITE, bev=0.08)
for y in (3.6, 8.8):
    sp.box((2 * T + 0.3, 0.28, 2 * T + 0.3), at=(0, y, 0), mat=Paint(STONE, 0xA7A398), bev=0.05)
# Corner buttresses, stepping in as they rise.
for sx in (-1, 1):
    for sz in (-1, 1):
        for y0, y1, w in ((SEABED, 6.0, 0.9), (6.0, 9.4, 0.6)):
            sp.box((w, y1 - y0, w), at=(sx * (T + w / 2 - 0.15), y0, sz * (T + w / 2 - 0.15)), mat=GRANITE, bev=0.06)
# Belfry: paired louvred openings on every face.
for face in range(4):
    a = face * math.pi / 2
    for k in (-0.75, 0.75):
        lx, lz = math.cos(a) * k, -math.sin(a) * k
        nx, nz = math.sin(a) * (T + 0.01), math.cos(a) * (T + 0.01)
        sp.box((0.75, 2.3, 0.12), at=(nx + lx, 10.3, nz + lz), mat=DARK, yaw=a, bev=0)
        for j in range(4):
            sp.box((0.8, 0.07, 0.16), at=(nx + lx, 10.6 + j * 0.5, nz + lz), mat=RAFTER, yaw=a, bev=0)
# The clock, under the belfry on the side facing the land.
sp.cyl(0.85, 0.85, 0.12, at=(0, 7.2, T + 0.02), mat=Paint(PAINT, 0xD8D2BE), pitch=math.pi / 2, segs=20, centered=True)
sp.cyl(0.95, 0.95, 0.08, at=(0, 7.2, T + 0.0), mat=SLATE_DARK, pitch=math.pi / 2, segs=20, centered=True)
sp.box((0.07, 0.62, 0.05), at=(0.0, 7.2, T + 0.1), mat=P["iron"], bev=0)
sp.box((0.42, 0.07, 0.05), at=(0.2, 7.18, T + 0.1), mat=P["iron"], centered=True, bev=0)
# Parapet, corner pinnacles and the spire.
for face in range(4):
    a = face * math.pi / 2
    sp.box((2 * T + 0.2, 0.7, 0.3), at=(math.sin(a) * (T - 0.05), TOP, math.cos(a) * (T - 0.05)), mat=GRANITE, yaw=a, bev=0.05)
for sx in (-1, 1):
    for sz in (-1, 1):
        sp.cyl(0.32, 0.0, 1.7, at=(sx * (T - 0.1), TOP + 0.7, sz * (T - 0.1)), mat=GRANITE, segs=4, yaw=math.pi / 4)
sp.cyl(T * 1.02, 0.05, 9.0, at=(0, TOP, 0), mat=SLATE, segs=8, yaw=math.pi / 8)
sp.cyl(0.04, 0.03, 1.6, at=(0, TOP + 8.9, 0), mat=P["iron"], segs=5)
sp.prism([(-0.45, 0.0), (0.35, 0.05), (0.5, 0.35), (0.15, 0.3), (0.0, 0.62), (-0.2, 0.3), (-0.5, 0.28)], 0.04, at=(0, TOP + 10.1, 0), mat=P["iron"], bev=0)
sp.box((1.0, 0.04, 0.04), at=(0, TOP + 9.8, 0), mat=P["iron"], centered=True, bev=0)
sp.box((0.04, 0.04, 1.0), at=(0, TOP + 9.8, 0), mat=P["iron"], centered=True, bev=0)
# The nave behind, drowned to its eaves: only the roof stands proud.
NW, NL, NE = 7.5, 13.0, 0.4
nave_z = -(T + NL / 2 - 0.3)
sp.box((NW, NE - SEABED, NL), at=(0, SEABED, nave_z), mat=GRANITE, bev=0.05)
for i in range(2):
    # Its ridge runs away from the tower, so the pitches fall to either side (x).
    s = 1 if i == 0 else -1
    ang = math.atan2(3.1, NW / 2)
    Ls = math.hypot(NW / 2, 3.1) + 0.35
    sp.box((Ls, 0.2, NL + 0.5), at=(s * (NW / 4 - 0.1), NE + 1.55, nave_z), mat=SLATE if i == 0 else SLATE_DARK, roll=-s * ang, centered=True, bev=0.03)
sp.prism([(-NW / 2, 0.0), (NW / 2, 0.0), (0.0, 3.1)], 0.3, at=(0, NE, nave_z - NL / 2 + 0.15), mat=GRANITE, bev=0.03)
sp.build("SCENE_spire", tideline=True, grime=0.0, ao=0.6)

# ---------------------------------------------------------------- poles
# The coast road's telegraph line, walking out from the shallows into deep
# water: each pole leaning its own way, wires sagging between, the last one
# trailing its wire into the sea.

pl = MB(3)
tops = []
for i in range(6):
    x = i * 9.5
    h = 9.2 - i * 0.35
    lean_x = (rnd.random() - 0.5) * 0.12 + i * 0.025
    lean_z = (rnd.random() - 0.5) * 0.16 + (0.1 if i == 5 else 0)
    base = (x, -3.0, 0.0)
    pl.cyl(0.24, 0.17, h, at=base, mat=TAR, segs=8, roll=-lean_x, pitch=lean_z)
    # Where the top ends up after the lean (small angles: offset ~ h * angle).
    tx, ty, tz = x + math.sin(lean_x) * math.cos(lean_z) * h, -3.0 + h * math.cos(lean_x) * math.cos(lean_z), math.sin(lean_z) * h
    arm_y = ty - 0.45
    pl.box((1.7, 0.12, 0.12), at=(tx, arm_y, tz), mat=TAR, roll=-lean_x, centered=True, bev=0.02)
    pins = []
    for k in (-0.65, 0.0, 0.65):
        px = tx + k * math.cos(lean_x)
        py = arm_y + 0.06 - k * math.sin(lean_x)
        pl.cyl(0.05, 0.035, 0.16, at=(px, py, tz), mat=P["glass_green"], segs=6)
        pins.append((px, py + 0.16, tz))
    tops.append(pins)
for a, b in zip(tops, tops[1:]):
    for p, q in zip(a, b):
        pl.tube([(p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t - 0.55 * 4 * t * (1 - t), p[2] + (q[2] - p[2]) * t) for t in (k / 8 for k in range(9))], 0.014, mat=P["iron"], segs=4, cap=False)
# The last wire, snapped and trailing into the water.
p = tops[-1][1]
pl.tube([(p[0], p[1], p[2]), (p[0] + 1.5, p[1] - 2.0, p[2] + 0.4), (p[0] + 2.4, -0.6, p[2] + 0.9)], 0.014, mat=P["iron"], segs=4, cap=False)
pl.build("SCENE_poles", tideline=True, grime=0.0, ao=0.4)

# ---------------------------------------------------------------- stacks
# A sea stack and its little sister: pillars the waves cut off the cliffs, in
# tall overlapping blocks, a flat cap with turf over it, paler toward the top
# where the gulls sit. (A tall rock's base flattening has to clear its whole
# height, hence flat = tall.)

st = MB(4)
for k, (r, tall, cy, col) in enumerate(((4.5, 1.3, -1.5, 0x6E6B64), (4.1, 1.25, 4.0, 0x7A776F), (3.8, 1.2, 8.5, 0x87847C), (3.5, 1.1, 12.0, 0x98958C))):
    st.rock(r, at=((rnd.random() - 0.5) * 0.9, cy, (rnd.random() - 0.5) * 0.9), mat=Paint(STONE, col), seed=10 + k, squash=1.0, scale=(1.0, tall, 0.92), subdiv=2, flat=tall)
st.rock(3.5, at=(0.2, 15.0, 0.1), mat=Paint(STONE, 0xA9A69C), seed=14, squash=0.4, flat=0.9)
st.rock(3.45, at=(0.2, 15.9, 0.1), mat=TURF, seed=20, squash=0.2, flat=0.9)
# The little one, and rocks round their feet.
for k, (r, tall, cy) in enumerate(((2.7, 1.3, -1.5), (2.3, 1.2, 2.2), (1.9, 1.1, 5.0))):
    st.rock(r, at=(8.0 + (rnd.random() - 0.5) * 0.5, cy, 2.5), mat=Paint(STONE, (0x6E6B64, 0x7E7B73, 0x908D85)[k]), seed=40 + k, squash=1.0, scale=(1.0, tall, 1.0), flat=tall)
for k in range(7):
    a = k / 7 * math.tau + 0.3
    st.rock(1.2 + rnd.random() * 1.4, at=(math.cos(a) * 6.5 + 1.5, -1.6, math.sin(a) * 5.0), mat=P["rock_dark"], seed=50 + k, squash=0.7, flat=0.9)
st.build("SCENE_stack", tideline=True, grime=0.0, ao=0.5)

# ----------------------------------------------------------- dead light
# Another keeper's lighthouse, gone dark: whitewashed tower with a red band,
# black lantern glazing, verdigris dome. The light everyone left.

dl = MB(5)
for k in range(6):
    a = k / 6 * math.tau + 0.2
    dl.rock(3.2 + rnd.random() * 1.8, at=(math.cos(a) * 3.4, -1.6, math.sin(a) * 3.4), mat=P["rock_dark"] if k % 2 else P["rock"], seed=60 + k, squash=0.9, flat=0.9)
dl.rock(4.0, at=(0, 0.4, 0), mat=P["rock"], seed=66, squash=0.65, flat=0.9)
BASE_Y = 2.6
dl.cyl(3.0, 3.0, 1.2, at=(0, BASE_Y - 0.6, 0), mat=GRANITE, segs=16)
bands = [(2.35, 2.2, 0.0, 5.0, WASH), (2.2, 2.05, 5.0, 8.4, REDBAND), (2.05, 1.9, 8.4, 12.6, WASH)]
for r0, r1, y0, y1, pm in bands:
    dl.lathe([(r0, BASE_Y + y0), (r1, BASE_Y + y1)], mat=pm, segs=16, cap=False)


def tower_r(y):
    for r0, r1, y0, y1, _ in bands:
        if y0 <= y <= y1:
            return r0 + (r1 - r0) * (y - y0) / (y1 - y0)
    return bands[-1][1]


for y in (3.0, 6.6, 10.4):
    dl.box((0.5, 0.75, 0.12), at=(0, BASE_Y + y, tower_r(y + 0.4) - 0.03), mat=DARK, bev=0)
G = BASE_Y + 12.6
dl.cyl(2.7, 2.6, 0.3, at=(0, G, 0), mat=P["iron"], segs=16)
dl.ring(2.55, 0.035, at=(0, G + 1.0, 0), mat=P["iron"], segs=24)
for k in range(12):
    a = k / 12 * math.tau
    dl.box((0.05, 1.0, 0.05), at=(math.cos(a) * 2.55, G + 0.3, math.sin(a) * 2.55), mat=P["iron"], bev=0)
dl.cyl(1.45, 1.45, 2.1, at=(0, G + 0.3, 0), mat=DARK, segs=10)
for k in range(10):
    a = k / 10 * math.tau
    dl.box((0.08, 2.1, 0.08), at=(math.cos(a) * 1.47, G + 0.3, math.sin(a) * 1.47), mat=P["iron"], bev=0)
dl.lathe([(1.65, G + 2.4), (1.4, G + 3.0), (0.75, G + 3.5), (0.0, G + 3.75)], mat=P["copper"], segs=12)
dl.uvsphere(0.22, at=(0, G + 3.9, 0), mat=P["copper"], segs=8, rings=6)
dl.cyl(0.03, 0.02, 0.9, at=(0, G + 4.0, 0), mat=P["iron"], segs=4)
dl.build("SCENE_dead_light", tideline=True, grime=0.0, ao=0.5)

# ----------------------------------------------------------------- masts
# A ship that went down whole, listing on the bottom: two masts and their yards
# out of the water, rags of sail, shrouds running down into the sea.

ms = MB(6)
LIST = 0.2
for i, (x, h) in enumerate(((0.0, 15.0), (8.5, 13.0))):
    base = (x, -7.0, 0.0)
    ms.cyl(0.24, 0.15, h, at=base, mat=P["hull_dark"], segs=8, roll=-LIST)
    tx = x + math.sin(LIST) * h
    for k, (yy, w) in enumerate(((h - 6.5, 7.0), (h - 10.0, 8.5))):
        cx = x + math.sin(LIST) * yy
        cy = -7.0 + math.cos(LIST) * yy
        ms.cyl(0.11, 0.11, w, at=(cx, cy, 0.0), mat=P["hull_dark"], segs=6, pitch=math.pi / 2, yaw=0.3 * (1 if i else -1), centered=True)
        # A rag of sail still bent to the yard.
        if (i, k) in ((0, 0), (1, 1)):
            for j in range(3):
                ms.box((0.04, 1.2 + rnd.random() * 1.4, 0.9), at=(cx + 0.05, cy - 1.0 - j * 0.2, -2.2 + j * 1.6), mat=CANVAS, roll=-LIST + 0.1, pitch=0.25 * (rnd.random() - 0.5), bev=0, jit=0.15)
    if i == 0:
        ny = -7.0 + math.cos(LIST) * (h - 4.0)
        nx = x + math.sin(LIST) * (h - 4.0)
        ms.cyl(0.85, 0.85, 0.15, at=(nx, ny, 0.0), mat=P["hull"], segs=10, roll=-LIST)
        ms.ring(0.85, 0.05, at=(nx, ny + 0.7, 0.0), mat=P["hull"], segs=12, roll=-LIST)
    top = (tx, -7.0 + math.cos(LIST) * h, 0.0)
    for sz in (-1, 1):
        ms.tube([top, (x - 1.2, -0.2, sz * 2.8)], 0.025, mat=P["rope"], segs=4, cap=False)
        ms.tube([(top[0], top[1] - 3.0, top[2]), (x + 1.8, -0.2, sz * 2.4)], 0.02, mat=P["rope"], segs=4, cap=False)
ms.tube([(math.sin(LIST) * 15.0, -7.0 + math.cos(LIST) * 15.0 - 0.2, 0.0), (8.5 + math.sin(LIST) * 12.0, -7.0 + math.cos(LIST) * 13.0 - 0.4, 0.0)], 0.022, mat=P["rope"], segs=4, cap=False)
ms.build("SCENE_masts", tideline=True, grime=0.0, ao=0.4)

# -------------------------------------------------------------- windmill
# A tower mill that once stood on a rise above the fields, now out at sea:
# its cap askew, two sails gone, the other two a bare lattice.

wm = MB(7)
wm.lathe([(3.4, SEABED), (3.2, 0.5), (2.7, 6.0), (2.4, 8.2)], mat=WASH, segs=14)
wm.cyl(2.65, 2.65, 0.25, at=(0, 8.1, 0), mat=RAFTER, segs=14)
wm.lathe([(2.6, 8.3), (2.3, 9.4), (1.2, 10.4), (0.0, 10.8)], mat=SLATE_DARK, segs=12, roll=0.08)
for y in (2.6, 5.4):
    # The wall's radius at the window, from the lathe profile above.
    r = 3.2 - 0.5 * (y + 0.4 - 0.5) / 5.5
    window(wm, (0.0, y, r - 0.02), w=0.6, h=0.8, broken=(y > 3))
HUB = (0.0, 9.2, 2.85)
wm.cyl(0.32, 0.28, 0.9, at=HUB, mat=P["iron"], segs=10, pitch=math.pi / 2, centered=True)
for k, (length, a) in enumerate(((8.0, 0.35), (5.2, 0.35 + math.pi / 2), (7.6, 0.35 + math.pi), (2.0, 0.35 + 1.5 * math.pi))):
    cx = HUB[0] + math.cos(a) * length / 2
    cy = HUB[1] + math.sin(a) * length / 2
    wm.box((length, 0.2, 0.2), at=(cx, cy, HUB[2] + 0.35), mat=RAFTER, roll=a, centered=True, bev=0.02)
    if length > 6:
        # The lattice that held the sailcloth.
        for j in range(1, 7):
            d = 1.2 + j * (length - 1.4) / 7
            px, py = HUB[0] + math.cos(a) * d, HUB[1] + math.sin(a) * d
            wm.box((0.06, 1.5, 0.06), at=(px - math.sin(a) * 0.7, py + math.cos(a) * 0.7, HUB[2] + 0.38), mat=RAFTER, roll=a, centered=True, bev=0)
        wm.box((length - 1.2, 0.07, 0.07), at=(cx - math.sin(a) * 1.4 + math.cos(a) * 0.6, cy + math.cos(a) * 1.4 + math.sin(a) * 0.6, HUB[2] + 0.38), mat=RAFTER, roll=a, centered=True, bev=0)
wm.build("SCENE_windmill", tideline=True, grime=0.0, ao=0.5)

# -------------------------------------------------------------- headland
# A far shore: a long run of cliff, its face battered back and cut by gullies,
# banded where the strata change, boulders bedded in it and fallen along its
# foot, turf over the top. Seen through the fog at the edge of the world, it's
# what makes the sea feel like a coast.

hd = MB(8)
N = 44
xs = [-55.0 + i * 110.0 / N for i in range(N + 1)]
noise2 = kit.noise2


def crest(x):
    t = (x + 55.0) / 110.0
    return 11.0 + 9.0 * math.sin(t * math.pi) ** 0.7 + 2.2 * noise2(x * 0.08, 3.0, 4) + 1.2 * noise2(x * 0.3, 1.0, 5)


def gully(x):
    return 2.4 * max(0.0, noise2(x * 0.22, 7.0, 6)) ** 2


FACE = ((0.0, 7.5), (0.18, 6.3), (0.36, 5.1), (0.54, 3.9), (0.72, 2.7), (0.88, 1.4), (1.0, 0.0))


def face_point(x, frac, back):
    top = crest(x)
    inner = math.sin(frac * math.pi)
    y = SEABED + (top - SEABED) * frac + 0.7 * noise2(x * 0.4, frac * 7, 12) * inner
    z = back - gully(x) * inner + 1.2 * noise2(x * 0.35, frac * 6, 9) * inner
    return (x + 0.5 * noise2(x, frac * 9, 8) * inner, y, z)


rows = [[face_point(x, frac, back) for x in xs] for frac, back in FACE]
STRATA = [(P["rock"], t) for t in (0.9, 0.84, 0.95, 0.88, 0.8, 0.92, 0.86, 0.97, 0.82)]
hd.loft(rows, strips=STRATA, jit=0.12)
turf = [rows[-1], [(x, crest(x) + 0.5 + 0.4 * noise2(x * 0.2, 2, 11), -6.0) for x in xs], [(x, crest(x) - 1.5, -16.0) for x in xs], [(x, SEABED, -20.0) for x in xs]]
hd.loft(turf[:2], mat=TURF, jit=0.1)
hd.loft(turf[1:], mat=P["rock_dark"], jit=0.1)
# Boulders bedded in the face, and fallen ones along the foot.
for k in range(16):
    x = -50.0 + k * 6.6 + (rnd.random() - 0.5) * 3.0
    frac = 0.15 + rnd.random() * 0.55
    fx, fy, fz = face_point(x, frac, 7.5 - frac * 7.0)
    hd.rock(1.8 + rnd.random() * 2.2, at=(fx, fy, fz - 0.6), mat=P["rock"], tint=0.75 + 0.2 * rnd.random(), seed=130 + k, squash=0.8, flat=0.9)
# Ends, so it doesn't read as a stage flat from an angle.
for x0, sgn in ((xs[0], -1), (xs[-1], 1)):
    top = crest(x0)
    hd.rock(6.0, at=(x0 + sgn * 2.0, (top + SEABED) / 2, -6.0), mat=P["rock"], seed=120 + (sgn > 0), squash=(top - SEABED) / 2 / 6.0 * 0.95, scale=(1.0, 1.0, 1.6), flat=0.95)
for k in range(12):
    x = -50.0 + k * 9.0 + (rnd.random() - 0.5) * 5.0
    hd.rock(1.8 + rnd.random() * 2.6, at=(x, -1.4, 8.0 + rnd.random() * 3.0), mat=P["rock_dark"], seed=110 + k, squash=0.6, flat=0.9)
hd.build("SCENE_headland", tideline=True, grime=0.0, ao=0.6)

# ------------------------------------------------------------------ buoy
# A channel buoy still riding its chain: red can, cage top and the bell that
# nobody hears any more.

by = MB(9)
by.lathe([(0.0, -0.6), (0.85, -0.45), (0.95, 0.1), (0.95, 0.5), (0.8, 0.62), (0.0, 0.62)], mat=Paint(PAINT, 0xA8392C), segs=14)
by.ring(0.95, 0.05, at=(0, 0.3, 0), mat=Paint(PAINT, 0xE8E4DA), segs=16)
for k in range(4):
    a = k / 4 * math.tau + math.pi / 4
    by.box((0.06, 1.7, 0.06), at=(math.cos(a) * 0.5, 0.6, math.sin(a) * 0.5), mat=P["iron"], roll=-math.cos(a) * 0.2, pitch=math.sin(a) * 0.2, bev=0)
by.lathe([(0.0, 2.05), (0.18, 2.0), (0.26, 1.75), (0.3, 1.55), (0.0, 1.55)], mat=P["brass"], segs=10)
by.cyl(0.24, 0.0, 0.5, at=(0, 2.1, 0), mat=Paint(PAINT, 0xA8392C), segs=4, yaw=math.pi / 4)
by.tube([(0, -0.6, 0), (0.5, -2.0, 0.6), (1.2, -3.5, 1.4)], 0.04, mat=P["rust"], segs=4)
by.build("SCENE_buoy", tideline=True, grime=0.0, ao=0.5)

kit.save_and_export("art/blender/scenery/scenery.blend", "public/assets/models/scenery.glb")
