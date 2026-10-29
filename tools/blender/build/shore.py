"""Builds art/blender/locations/shore.blend and public/assets/models/locations/shore.glb.

Gullwash Shore, laid out per docs/LEVELS.md (game space, metres):
  south: dunes (dry, y 2.4–4) with the landing jetty and the cliff path home
  middle: wet sand flats (y 0.3–1.3) that flood at high tide
  north-east: a sandbar (y 0.6) out to a dry islet (y 2.7) — a low-tide trip
  north-west: a rocky spit (y 2.6, always dry) with the Glowgill shoal off its tip

Collision is kept as plain shapes (COL_); over it: a pile-built landing jetty
with a ladder and bollards, the old fisher's hut (an upturned boat on a stone
footing, roped down against the gales), a fishing boat lying where a storm left
it on the strand, net poles, a navigation perch on the spit's tip, a boardwalk
to the cliff path, marram on the dunes and rippled, pooled sand on the flats.

    blender -b --factory-startup --python tools/blender/build/shore.py
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import bpy  # noqa: E402,F401
import kit  # noqa: E402
from kit import MB, Paint, fbm3, hull_sections, noise2, seg_dist, smoothstep  # noqa: E402

kit.reset()

TEMPLATES = kit.load_props()
P = kit.palette()
# `rnd` lays out the level and is drawn in the same order as it always was;
# the dressing has its own dice so it never moves a rock or a node.
rnd = random.Random(21)
vr = random.Random(121)

WOOD = P["timber"].mat
TAR = P["tar"]
WEATHERED = P["driftwood"]
NET = Paint(P["cloth"].mat, 0x4A5046)
DOOR = Paint(P["paint_blue"].mat, 0x4F6A75)
GRASS = [Paint(P["grass"].mat, c) for c in (0x8C9461, 0x9AA06A, 0xA89F6A, 0x7C8655, 0xB5A877)]


def lerp(a, b, t):
    return a + (b - a) * t


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    out = 0
    for sh in (16, 8, 0):
        ca, cb = (a >> sh) & 255, (b >> sh) & 255
        out |= int(round(ca + (cb - ca) * t)) << sh
    return out


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
    n = fbm3(x * 0.12, 0.0, z * 0.12, 51)
    f = fbm3(x * 0.7, 0.0, z * 0.7, 52)
    rock = max(1 - smoothstep(2.0, 6.0, seg_dist(x, z, -40, 20, -46, -24)), 1 - smoothstep(6.5, 10.0, math.hypot(x - 54, z + 50)))
    if rock > 0.5 and y > 0.5:
        # Bare rock: lichen above the spray, weed and barnacles below high water.
        c = mix(0x6A665E, 0x8A857A, 0.5 + 0.6 * n)
        c = mix(c, 0xA0915A, smoothstep(0.35, 0.6, f) * 0.5 * smoothstep(2.1, 2.5, y))
        if y < 1.9:
            c = mix(c, 0x4E5640, 0.55)
        if math.hypot(x - 54, z + 50) < 7.0 and y > 2.3:
            c = mix(c, 0x6F7A48, smoothstep(-0.1, 0.4, n) * 0.6)
        return c
    if y < -0.5:
        return mix(0x4F5040, 0x5E5A48, 0.5 + 0.5 * n)
    if y < 0.25:
        return mix(0x6E6A52, 0x7C755A, 0.5 + 0.5 * f)
    if y < 1.8:
        # Wet flats: ripples the last tide left, and pools that kept their water.
        ripple = 0.5 + 0.5 * math.sin(z * 2.6 + x * 0.35 + n * 4.0)
        c = mix(0x857A5E, 0x9A8D6C, ripple * 0.6 + 0.2 * f)
        return mix(c, 0x5F6A5E, smoothstep(0.35, 0.6, n) * 0.6)
    if y < 2.4:
        # The strand: damp sand and a dark line of wrack at the high-water mark.
        c = mix(0xA8996F, 0xB8A87E, 0.5 + 0.5 * f)
        return mix(c, 0x5A5236, smoothstep(0.15, 0.0, abs(y - 1.95)) * 0.6)
    path = 3 < x < 13 and 34 < z < 50 and abs(x - 8) < 3.0
    if y < 3.3 or path:
        return mix(0xC6B68C, 0xD4C49A, 0.5 + 0.5 * f)
    # Dunes: pale sand, marram in patches.
    c = mix(0xC8B88E, 0xD6C69C, 0.5 + 0.5 * f)
    return mix(c, 0x8E9461, smoothstep(0.0, 0.45, n + 0.3 * f) * 0.65)


ground = kit.material("TIDE_sand", 0xFFFFFF, rough=0.95, vcol=True)
kit.terrain("terrain", -80, 80, -72, 78, 1.0, height, color, ground, props={"col": 1})


def H(x, z):
    return height(x, z)


def prop(kind, name, x, z, y=None, yaw=None, props=None, scale=1.0):
    """A layout prop: a random turn (yaw None) comes from `rnd`."""
    return kit.place(TEMPLATES, kind, name, (x, H(x, z) if y is None else y, z), yaw=rnd.random() * math.tau if yaw is None else yaw, props=props, scale=scale)


def dress(kind, name, x, z, y=None, yaw=None, scale=1.0):
    """A dressing prop: its turn comes from `vr`."""
    return kit.place(TEMPLATES, kind, name, (x, H(x, z) if y is None else y, z), yaw=vr.random() * math.tau if yaw is None else yaw, scale=scale)


def run(m, pts, w, h, mat, bev=0.015, tint=1.0):
    """Boxes along consecutive game points, w across and h tall, centred on them."""
    for p, q in zip(pts, pts[1:]):
        dx, dy, dz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
        L = math.sqrt(dx * dx + dy * dy + dz * dz)
        if L < 1e-4:
            continue
        m.box((L + 0.02, h, w), at=((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2), mat=mat,
              yaw=math.atan2(-dz, dx), roll=math.atan2(dy, math.hypot(dx, dz)), centered=True, bev=bev, tint=tint)


def sag(a, b, drop, n=8):
    return [(lerp(a[0], b[0], t), lerp(a[1], b[1], t) - drop * 4 * t * (1 - t), lerp(a[2], b[2], t)) for t in (k / n for k in range(n + 1))]


def barnacles(m, centre, spread, count, size=0.045, axis=None):
    cx, cy, cz = centre
    for _ in range(count):
        a = vr.random() * math.tau
        x, z = cx + math.cos(a) * spread[0], cz + math.sin(a) * spread[0]
        y = cy + (vr.random() - 0.5) * 2 * spread[1]
        r = size * (0.6 + vr.random() * 0.7)
        yaw = -a if axis is None else axis
        m.cyl(r, r * 0.35, r * 1.1, at=(x, y, z), mat=P["barnacle"], roll=-math.pi / 2, yaw=yaw, segs=5, bev=0, jit=0.12)


# ------------------------------------------------------------ landing jetty

JX, JY = 8.0, 3.0
JZ0, JZ1 = 45.575, 68.275
PILE_Z = [49 + i * 3.2 for i in range(7)]
jcol = MB()
for i in range(24):
    jcol.box((3.0, 0.15, 0.85), at=(0, -0.15, 46 + i * 0.95), bev=0)
for z in PILE_Z:
    for side in (-1.35, 1.35):
        jcol.cyl(0.16, 0.2, JY - SEA + 0.1, at=(side, SEA - JY, z), segs=7, bev=0)
jcol.build("COL_jetty", loc=(JX, JY, 0), ao=0, grime=0)

# The jetty you see: deck boards on three stringers, pile caps, round piles
# braced in pairs, a kerb along each edge and a ladder down at the end.
jt = MB(41)
z = JZ0 + 0.13
while z < JZ1 - 0.1:
    w = 0.22 + vr.random() * 0.04
    jt.box((3.1 + (vr.random() - 0.5) * 0.08, 0.07, w), at=((vr.random() - 0.5) * 0.04, -0.07, z), mat=P["timber"] if vr.random() < 0.7 else P["driftwood"], bev=0.012, tint=0.8 + 0.3 * vr.random(), yaw=(vr.random() - 0.5) * 0.015)
    z += w + 0.03
for x in (-1.2, 0.0, 1.2):
    jt.box((0.18, 0.25, JZ1 - JZ0), at=(x, -0.32, (JZ0 + JZ1) / 2), mat=P["timber"], tint=0.8, bev=0.02)
for x in (-1.5, 1.5):
    jt.box((0.12, 0.13, JZ1 - JZ0), at=(x, 0.0, (JZ0 + JZ1) / 2), mat=P["timber_light"], tint=0.85, bev=0.02)
for k, z in enumerate(PILE_Z):
    jt.box((3.4, 0.3, 0.26), at=(0, -0.62, z), mat=P["timber"], tint=0.75, bev=0.025)
    for side in (-1.35, 1.35):
        jt.cyl(0.21, 0.18, -0.62 - (SEA - JY) + 0.02, at=(side, SEA - JY, z), mat=P["driftwood_dark"], segs=10)
        barnacles(jt, (side, -2.2, z), (0.2, 0.5), 10)
    # X-braces between each pair, a little below the deck.
    for a, b in (((-1.35, -0.75), (1.35, -2.6)), ((1.35, -0.75), (-1.35, -2.6))):
        run(jt, [(a[0], a[1], z + 0.24), (b[0], b[1], z + 0.24)], 0.08, 0.16, P["timber"], tint=0.7)
LX, LZ = 0.85, JZ1 + 0.06
for x in (LX - 0.25, LX + 0.25):
    jt.box((0.07, 4.0, 0.08), at=(x, -3.9, LZ), mat=P["iron"], bev=0.01)
for k in range(10):
    jt.cyl(0.02, 0.02, 0.5, at=(LX, -3.6 + k * 0.38, LZ), mat=P["iron"], roll=math.pi / 2, centered=True, segs=6, bev=0)
jt.build("jetty", loc=(JX, JY, 0), tideline=True, grime=0.0, ao=0.75)
for i, (dx, z) in enumerate(((-1.3, 67.6), (1.3, 67.6), (1.3, 58.0))):
    dress("bollard", f"bollard_jetty_{i}", JX + dx, z, y=JY, yaw=0.0)
dress("rope_coil", "rope_jetty", JX - 0.9, 66.4, y=JY, yaw=0.7)

# The boat floats (BUOY_) and is still the travel interact.
prop("rowboat", "BUOY_boat", JX + 3.0, 64, y=0.25, yaw=0.0, props={"interact": "boat", "range": 5.0, "float": -0.15, "min": -1.0, "max": 2.5})
prop("lantern_post", "lantern_jetty", JX - 1.3, 47, y=JY, yaw=math.pi)
prop("lantern_post", "lantern_dunes", 2, 40, yaw=0.3)
kit.empty("SPAWN_landing", (JX, JY, 52), yaw=0.0)

# ---------------------------------------------------------- cliff path home

prop("signpost", "INT_path_home", -57, 31, yaw=-math.pi / 2, props={"interact": "path_home"})
prop("lantern_post", "lantern_path", -55, 27, yaw=0.0)
kit.empty("SPAWN_path", (-53, H(-53, 31) + 0.1, 31), yaw=-math.pi / 2)

# A boardwalk of sleepers through the marram to the signpost, roped either side.
bw = MB(42)
x = -48.0
while x > -57.5:
    y = H(x, 31) + 0.04
    slope = math.atan2(H(x + 0.3, 31) - H(x - 0.3, 31), 0.6)
    bw.box((0.24, 0.07, 1.3), at=(x, y - 0.06, 31 + (vr.random() - 0.5) * 0.08), mat=P["driftwood"], roll=slope, yaw=(vr.random() - 0.5) * 0.06, bev=0.01, tint=0.8 + 0.3 * vr.random())
    x -= 0.34
for side in (-1, 1):
    tops = []
    for k in range(6):
        px, pz = -48.2 - k * 1.9, 31 + side * 0.95
        h = 0.85 + vr.random() * 0.15
        bw.cyl(0.05, 0.045, h + 0.3, at=(px, H(px, pz) - 0.3, pz), mat=P["driftwood_dark"], segs=6, bev=0)
        tops.append((px, H(px, pz) + h - 0.05, pz))
    for a, b in zip(tops, tops[1:]):
        bw.tube(sag(a, b, 0.18, 6), 0.018, mat=P["rope"], segs=4)
bw.build("boardwalk", grime=0.1)

# ---------------------------------------------------------------- landmarks

# The old fisher's hut: an upturned boat on a low stone footing, its door in
# the transom end, roped down against the gales.
HUT = (-22.0, 38.0, 0.2)
hx, hz, hyaw = HUT
hut_ground = H(hx, hz) - 0.1
BASE = 0.8
hut_st = [
    (-3.5, 0.92, 1.5, 0.0, 0.92),
    (-2.6, 1.45, 1.62, 0.0, 0.88),
    (-1.2, 1.7, 1.7, 0.0, 0.82),
    (0.4, 1.72, 1.72, 0.0, 0.78),
    (1.8, 1.5, 1.74, 0.0, 0.66),
    (2.9, 0.95, 1.76, 0.0, 0.45),
    (3.6, 0.06, 1.8, 0.0, 0.15),
]


def upturn(sections):
    """Turn hull sections keel-up so each gunwale rests at BASE."""
    out = []
    for sec, (_z, _b, d, yk, _f) in zip(sections, hut_st):
        gun = yk + d
        out.append([(px, BASE + gun - py, pz) for px, py, pz in sec])
    return out


hut = MB(43)
shell = upturn(hull_sections(hut_st, 8, overlap=0.025))
strips = [(TAR, 1.0 if k % 2 else 0.85) for k in range(len(shell[0]) - 1)]
hut.loft(shell, strips=strips, flip=True)
# Keel along the top, and the stem post at the far end.
hut.tube([(0.0, BASE + d + 0.04, z) for z, _b, d, _yk, _f in hut_st], 0.07, mat=P["hull_dark"], segs=6)
# Footing: rough stone under the gunwales, open at the door end.
outline = [(-b * 1.02, z) for z, b, _d, _yk, _f in hut_st] + [(b * 1.02, z) for z, b, _d, _yk, _f in reversed(hut_st)]
for k, (px, pz) in enumerate(outline):
    if abs(pz + 3.5) < 0.01:
        continue
    hut.rock(0.32 + vr.random() * 0.08, at=(px, 0.25, pz), mat=P["stone_dark"] if k % 2 else P["rock"], seed=60 + k, squash=0.9, scale=(1.3, 1.2, 1.0))
footing = []
for y in (-0.1, BASE):
    footing.append([(px * (1.05 if y < 0 else 1.0), y, pz) for px, pz in outline])
hut.loft(footing, mat=P["stone_dark"], tint=0.9)
# The planked end with its door, and a little light over it.
b0 = hut_st[0][1]
end_sec = upturn(hull_sections(hut_st[:1], 8, overlap=0.0))[0]
end = [(-b0, 0.0)] + [(px, py) for px, py, _pz in end_sec] + [(b0, 0.0)]
hut.prism(list(reversed(end)), 0.08, at=(0, 0, -3.52), mat=P["driftwood"], bev=0)
for k in range(7):
    hut.box((0.04, BASE + 1.2, 0.02), at=(-0.75 + k * 0.25, 0.0, -3.57), mat=P["driftwood_dark"], bev=0)
hut.box((0.8, 1.72, 0.07), at=(0.25, 0.0, -3.6), mat=DOOR, bev=0.015)
for dy in (0.3, 1.35):
    hut.box((0.84, 0.08, 0.04), at=(0.25, dy, -3.64), mat=P["driftwood_dark"], bev=0.005)
hut.cyl(0.03, 0.03, 0.05, at=(-0.07, 0.95, -3.66), mat=P["iron"], pitch=math.pi / 2, centered=True, segs=6)
hut.box((1.2, 0.14, 0.5), at=(0.25, -0.05, -3.85), mat=P["stone"], bev=0.03)
# Portholes cut in the planking, a stovepipe through the side.


def side_x(sec, y):
    """Where an upturned section's side reaches height y."""
    pts = sorted(((px, py) for px, py, _pz in sec if px >= 0), key=lambda q: q[1])
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if y0 <= y <= y1 and y1 > y0:
            return x0 + (x1 - x0) * (y - y0) / (y1 - y0)
    return pts[0][0]


for k in (2, 4):
    py = BASE + 0.5
    bx = side_x(shell[k], py) + 0.03
    for side in (-1, 1):
        hut.ring(0.16, 0.035, at=(side * bx, py, hut_st[k][0]), mat=P["brass"], pitch=math.pi / 2, yaw=math.pi / 2, segs=12, tube_segs=4)
        hut.cyl(0.14, 0.14, 0.03, at=(side * bx, py, hut_st[k][0]), mat=P["glass_blue"], pitch=math.pi / 2, yaw=math.pi / 2, centered=True, segs=12, tint=0.4)
hut.cyl(0.09, 0.09, 1.2, at=(0.75, BASE + 1.2, 1.4), mat=P["iron"], segs=8)
hut.cyl(0.2, 0.04, 0.22, at=(0.75, BASE + 2.4, 1.4), mat=P["iron"], segs=8)
# Ropes over the hull, weighted with stones either side.
for z in (-2.2, 0.2, 2.2):
    sec = min(range(len(hut_st)), key=lambda i: abs(hut_st[i][0] - z))
    pts = [(px * 1.03, py + 0.04, z) for px, py, _pz in shell[sec]]
    hut.tube([(-hut_st[sec][1] * 1.1, 0.35, z)] + pts + [(hut_st[sec][1] * 1.1, 0.35, z)], 0.022, mat=P["rope"], segs=4)
    for side in (-1, 1):
        hut.rock(0.22, at=(side * (hut_st[sec][1] + 0.35), 0.1, z), mat=P["rock"], seed=80 + int(z * 10) + side, squash=0.8)
hut.build("fisher_hut", loc=(hx, hut_ground, hz), yaw=hyaw, ground=True, grime=0.25)
MB().box((3.6, 2.7, 7.4), at=(0, 0, 0)).build("COL_fisher_hut", loc=(hx, hut_ground, hz), yaw=hyaw, ao=0, grime=0)

prop("barrel", "barrel_hut1", -19.5, 35.5)
prop("barrel", "barrel_hut2", -20.4, 35.0)
prop("hull_ribs", "wreck_ribs", 20, -10, yaw=0.7)

# Net poles beside the hut with a net drying between them, and the fire ring.
net = MB(44)
poles = [(-26.6, 35.0), (-26.9, 38.0), (-26.5, 41.0)]
tops = []
for px, pz in poles:
    base = H(px, pz)
    net.cyl(0.07, 0.06, 2.4, at=(px, base - 0.3, pz), mat=P["driftwood"], segs=7, roll=(vr.random() - 0.5) * 0.08)
    tops.append((px, base + 1.95, pz))
for a, b in zip(tops, tops[1:]):
    rows = []
    for r in range(5):
        rows.append(sag((a[0], a[1] - r * 0.33, a[2]), (b[0], b[1] - r * 0.33, b[2]), 0.25 + r * 0.04, 10))
    for row in rows:
        net.tube(row, 0.008, mat=NET, segs=3)
    for c in range(11):
        net.tube([row[c] for row in rows], 0.007, mat=NET, segs=3)
    for c in range(1, 10, 2):
        net.uvsphere(0.06, at=rows[0][c], mat=P["timber_pale"], segs=8, rings=5)
for k in range(9):
    a = k / 9 * math.tau
    px, pz = -17.6 + math.cos(a) * 0.55, 40.8 + math.sin(a) * 0.55
    net.rock(0.15 + vr.random() * 0.05, at=(px, H(px, pz) + 0.02, pz), mat=P["stone_dark"], seed=90 + k, squash=0.7)
net.box((0.8, 0.12, 0.12), at=(-17.6, H(-17.6, 40.8) - 0.02, 40.8), mat=Paint(WOOD, 0x2A2420), yaw=0.5, bev=0.03)
net.box((0.7, 0.11, 0.11), at=(-17.55, H(-17.6, 40.8) - 0.02, 40.75), mat=Paint(WOOD, 0x2A2420), yaw=-0.7, bev=0.03)
net.build("hut_yard", grime=0.15)
for i, (x, z, yaw) in enumerate(((-24.6, 34.4, 0.3), (-25.4, 34.9, 1.4), (-25.0, 34.0, 2.6))):
    dress("lobster_pot", f"pot_hut_{i}", x, z, yaw=yaw)
dress("rope_coil", "rope_hut", -18.9, 35.4, yaw=0.8)
dress("anchor", "anchor_dunes", -12.0, 31.5, yaw=2.2)

# A fishing boat the storms left on the strand, heeled over and half full of
# sand, planks sprung along her side.
boat_st = [
    (-2.8, 0.8, 1.0, -0.2, 0.9),
    (-1.9, 1.08, 1.05, -0.32, 0.85),
    (-0.6, 1.2, 1.08, -0.36, 0.8),
    (0.7, 1.16, 1.1, -0.36, 0.72),
    (1.8, 0.9, 1.14, -0.32, 0.55),
    (2.6, 0.45, 1.2, -0.26, 0.35),
    (3.0, 0.04, 1.26, -0.2, 0.12),
]
fb = MB(45)
outer = hull_sections(boat_st, 6, overlap=0.02)
npts = len(outer[0])
sprung = {(5, 2), (5, 3), (6, 3), (7, 2), (7, 3), (7, 4), (9, 1)}
hull_cols = [Paint(P["paint_blue"].mat, 0x3E5A6A), Paint(P["paint_white"].mat, 0xD2CAB4), Paint(P["paint_red"].mat, 0x6E2E24)]
for i in range(npts - 1):
    y_mid = (outer[2][i][1] + outer[2][i + 1][1]) / 2
    pm = hull_cols[1] if (i < 1 or i >= npts - 2) else hull_cols[2] if y_mid < 0.05 else hull_cols[0]
    for k in range(len(outer) - 1):
        if (i, k) in sprung:
            continue
        fb.loft([[outer[k][i], outer[k][i + 1]], [outer[k + 1][i], outer[k + 1][i + 1]]], mat=pm, jit=0.1, tint=0.75 + 0.2 * vr.random())
# Frames inside (they show where the planks have gone), thwarts, sand inside.
for k in range(1, len(outer) - 1):
    fb.tube([(px * 0.94, py + 0.05, pz) for px, py, pz in outer[k][1:-1]], 0.035, mat=P["timber"], segs=5)
for z, w in ((-1.5, 1.9), (0.1, 2.1)):
    fb.plank(w, 0.24, 0.05, at=(0.0, 0.42, z), mat=P["timber_light"], warp=0.1)
fb.box((1.9, 0.4, 3.4), at=(0, -0.38, 0.0), mat=P["sand"], bev=0.15)
fb.tube([(0.0, -0.3, -2.9), (0.0, -0.35, 2.9), (0.0, 0.7, 3.25)], 0.06, mat=P["hull_dark"], segs=6)
ob = fb.build("beached_boat", loc=(-1.0, H(-1.0, 18.0) - 0.42, 18.0), grime=0.2)
ob.rotation_euler = (0.0, 0.42, 0.95)  # heeled over on her side, then turned
MB().box((2.1, 1.2, 5.6), at=(0, -0.2, 0)).build("COL_beached_boat", loc=(-1.0, H(-1.0, 18.0) - 0.42, 18.0), yaw=0.95, ao=0, grime=0)
# Her mast, snapped and lying in the sand beside her.
mast = MB(46)
mast.cyl(0.08, 0.06, 3.2, at=(0, 0.06, 0), mat=P["driftwood"], pitch=math.pi / 2, centered=True, segs=8)
mast.tube([(0.0, 0.08, 1.6), (0.15, 0.04, 2.3), (0.3, 0.02, 2.9)], 0.012, mat=P["rope"], segs=4)
mast.build("beached_mast", loc=(1.6, H(1.6, 16.6), 16.6), yaw=0.4, grime=0.2)

# ------------------------------------------------------------- rocks and grass

for i in range(26):
    t = i / 25
    x = lerp(-40, -46, t) + (rnd.random() - 0.5) * 6
    z = lerp(20, -24, t) + (rnd.random() - 0.5) * 3
    r = 0.9 + rnd.random() * 1.6
    MB().rock(r, mat=P["rock"] if i % 3 else P["rock_dark"], seed=100 + i, squash=0.7).build(f"rock_spit_{i:02d}", loc=(x, H(x, z) - r * 0.35, z), tideline=True, props={"col": 1})
for i in range(18):
    a = rnd.random() * math.tau
    x, z = 54 + math.cos(a) * 9.5, -50 + math.sin(a) * 9.5
    r = 0.7 + rnd.random() * 1.2
    MB().rock(r, mat=P["rock"], seed=200 + i).build(f"rock_islet_{i:02d}", loc=(x, H(x, z) - r * 0.3, z), tideline=True, props={"col": 1})
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

# A perch on the spit's tip: a tarred pole with a topmark, chained to the rock.
PX, PZ = -46.6, -25.2
perch = MB(47)
pb = H(PX, PZ)
perch.cyl(0.14, 0.11, 5.6, at=(0, -0.4, 0), mat=TAR, segs=10)
for k in range(3):
    perch.ring(0.15 - k * 0.005, 0.02, at=(0, 0.6 + k * 1.6, 0), mat=P["iron"], segs=12, tube_segs=4)
perch.cyl(0.42, 0.0, 0.62, at=(0, 5.25, 0), mat=Paint(P["paint_red"].mat, 0x1E1E1E), segs=10)
perch.cyl(0.0, 0.42, 0.62, at=(0, 4.55, 0), mat=Paint(P["paint_red"].mat, 0x1E1E1E), segs=10)
perch.box((0.2, 0.12, 0.2), at=(0, 5.12, 0), mat=P["iron"], bev=0.01)
for k in range(3):
    a = k / 3 * math.tau + 0.4
    gx, gz = math.cos(a) * 2.2, math.sin(a) * 2.2
    gy = H(PX + gx, PZ + gz) - pb
    perch.tube(sag((0.0, 3.1, 0.0), (gx, gy + 0.05, gz), 0.15, 6), 0.025, mat=P["rust"], segs=4)
    perch.rock(0.22, at=(gx, gy, gz), mat=P["rock_dark"], seed=95 + k, squash=0.8)
barnacles(perch, (0.0, 0.2, 0.0), (0.15, 0.25), 14)
perch.build("perch", loc=(PX, pb, PZ), tideline=True, grime=0.2)
MB().cyl(0.16, 0.16, 5.6, at=(0, -0.4, 0), segs=8, bev=0).build("COL_perch", loc=(PX, pb, PZ), ao=0, grime=0)

# A cairn on the islet, where you'd look back for the jetty.
cairn = MB(48)
y = 0.0
for k in range(6):
    r = 0.55 - k * 0.07
    cairn.rock(r, at=(0.04 * (vr.random() - 0.5), y, 0.04 * (vr.random() - 0.5)), mat=P["rock"] if k % 2 else P["stone_dark"], seed=40 + k, squash=0.45, scale=(1.2, 1.0, 1.0))
    y += r * 0.62
cairn.build("cairn", loc=(58.4, H(58.4, -46.8) - 0.1, -46.8), tideline=True, props={"col": 1})

# Marram over the dunes: one mesh of tufts, kept off the paths, the hut, the
# nodes and the boardwalk.
CLEAR = [(JX, 48.0, 5.5), (hx, hz, 5.5), (-52.5, 31.0, 3.5), (-17.6, 40.8, 1.5)]
CLEAR += [(x, z, 2.5) for x, z in ((-30, 20.5), (-8, 19.5), (14, 21), (31, 26), (-44, 34), (40, 13), (-18, 17), (26, 18))]
field = MB(49)
tufts = 0
for _ in range(400):
    if tufts >= 80:
        break
    x, z = vr.uniform(-50.0, 50.0), vr.uniform(22.0, 47.0)
    y = H(x, z)
    if y < 3.0 or any(math.hypot(x - cx, z - cz) < r for cx, cz, r in CLEAR) or (3 < x < 13 and z > 34):
        continue
    tufts += 1
    s = 0.7 + vr.random() * 0.6
    for b in range(9):
        a = vr.random() * math.tau
        h = (0.45 + vr.random() * 0.45) * s
        lean = 0.15 + vr.random() * 0.4
        w = 0.025 * s
        ca, sa = math.cos(a), math.sin(a)
        x0, z0 = x + ca * vr.random() * 0.12, z + sa * vr.random() * 0.12
        secs = []
        for k in range(4):
            t = k / 3
            out = lean * t * t * h
            half = w * (1 - t * 0.9)
            px, py, pz = x0 + ca * out, y - 0.05 + t * h, z0 + sa * out
            secs.append([(px - sa * half, py, pz + ca * half), (px + sa * half, py, pz - ca * half)])
        field.loft(secs, mat=GRASS[b % len(GRASS)], jit=0.1)
field.build("marram", ao=0.3, grime=0.25)

# Wrack along the strand line.
for i in range(9):
    x = -36.0 + i * 9.0 + (vr.random() - 0.5) * 4.0
    z = 19.2 + (vr.random() - 0.5) * 1.6
    dress("seaweed", f"wrack_{i}", x, z)

# ------------------------------------------------------- what the sea took
# Gullwash used to be a village shore, not an island. Its own dice (`dr`), so
# none of this moves a node, a rock or the marram. Nothing here is in the way
# of a node, an enemy's ground or a path; what you could walk into is solid.

dr = random.Random(321)
KEEP_CLEAR = [(x, z, 3.0) for x, z in ((-30, 20.5), (-8, 19.5), (14, 21), (31, 26), (-44, 34), (40, 13), (-18, 17), (26, 18), (2, 2),
                                       (-12, -12), (8, -15), (30, -12), (-34, -10), (-16, -2), (12, -4), (36, 0), (0, -6))]
KEEP_CLEAR += [(x, z, 4.0) for x, z in ((-10, -2), (5, -8), (18, 4), (-22, 6), (-15, 23), (20, 25))]
KEEP_CLEAR += [(JX, 48.0, 6.0), (hx, hz, 6.0), (-1.0, 18.0, 4.0), (-52.5, 31.0, 4.0), (-17.6, 40.8, 2.0)]


def clear(x, z, pad=0.0):
    return all(math.hypot(x - cx, z - cz) > r + pad for cx, cz, r in KEEP_CLEAR)


# The coast road: it came down off the dunes past the hut and ran north across
# what were fields, toward the village that's out there now under the water.
# Its setts show through the sand in patches, its iron lamps lean further the
# deeper they stand, and the last one is in the sea.
ROAD = [(-33.0, 21.0), (-31.5, 8.0), (-29.5, -6.0), (-28.0, -20.0), (-27.0, -34.0)]


def road_at(t):
    """Point and heading along the road, t in 0..1."""
    n = len(ROAD) - 1
    i = min(int(t * n), n - 1)
    u = t * n - i
    (ax, az), (bx, bz) = ROAD[i], ROAD[i + 1]
    return ax + (bx - ax) * u, az + (bz - az) * u, math.atan2(bx - ax, bz - az)


setts = MB(60)
for k in range(260):
    t = dr.random()
    cx, cz, head = road_at(t)
    # Patches, not a whole road: the sand's taken most of it.
    if noise2(t * 9.0, 0.5, 31) < 0.05:
        continue
    across = (dr.random() - 0.5) * 3.4
    x, z = cx + math.cos(head) * across, cz - math.sin(head) * across
    if not clear(x, z, 0.4):
        continue
    y = H(x, z)
    setts.box((0.24 + dr.random() * 0.08, 0.1, 0.14 + dr.random() * 0.05), at=(x, y - 0.075, z), mat=P["stone_dark"] if k % 3 else P["stone"],
              yaw=head + (dr.random() - 0.5) * 0.15, tint=0.8 + dr.random() * 0.3, bev=0.012)
# Kerb stones along both sides where the road is clearest.
for side in (-1, 1):
    for k in range(34):
        t = 0.08 + k / 34 * 0.6
        cx, cz, head = road_at(t)
        if noise2(t * 7.0, side, 33) < 0.15:
            continue
        x, z = cx + math.cos(head) * side * 1.85, cz - math.sin(head) * side * 1.85
        if clear(x, z, 0.3):
            setts.box((0.18, 0.16, 0.55), at=(x, H(x, z) - 0.09, z), mat=P["stone"], yaw=head, tint=0.85 + dr.random() * 0.2, bev=0.02)
setts.build("road_setts", ao=0.5, grime=0.3, tideline=True)

lamps = MB(61)
lamp_col = MB()
for k, t in enumerate((0.06, 0.27, 0.48, 0.69, 0.9)):
    cx, cz, head = road_at(t)
    x, z = cx + math.cos(head) * 2.4, cz - math.sin(head) * 2.4
    base = H(x, z)
    lean = 0.05 + k * 0.07
    # Lean seaward (north) and a little across.
    pitch, roll = -lean, (dr.random() - 0.5) * 0.12
    h = 3.4
    lamps.lathe([(0.17, -0.5), (0.17, 0.05), (0.12, 0.12), (0.08, 0.25), (0.06, 0.4), (0.05, h - 0.1), (0.065, h), (0.0, h + 0.05)], at=(x, base, z), mat=P["iron"], segs=8, pitch=pitch, roll=roll)
    # Where the top went after the lean (pitch tips +y toward -z; roll toward +x).
    tx, ty, tz = x + math.sin(-roll) * h, base + h * math.cos(lean), z - math.sin(lean) * h
    if k < 4:
        # The crossbar the lamplighter leaned his ladder on, and an empty lantern cage.
        lamps.box((0.7, 0.05, 0.05), at=(tx, ty - 0.55, tz), mat=P["iron"], yaw=head, roll=roll, centered=True, bev=0)
        for sx in (-1, 1):
            lamps.cyl(0.03, 0.03, 0.45, at=(tx + math.cos(head) * sx * 0.12, ty, tz - math.sin(head) * sx * 0.12), mat=P["iron"], segs=4, pitch=pitch, roll=roll)
        lamps.cyl(0.2, 0.05, 0.22, at=(tx, ty + 0.42, tz), mat=P["iron"], segs=6, pitch=pitch, roll=roll)
    lamp_col.cyl(0.17, 0.12, h, at=(x, base - 0.5, z), segs=6, pitch=pitch, roll=roll, bev=0)
    # Gulls stand on the bare post at the end and on a crossbar (src/world/Gulls.ts).
    if k == 4:
        kit.empty("FX_perch_lamp", (tx, ty + 0.1, tz))
    elif k == 1:
        kit.empty("FX_perch_lamp_bar", (tx + math.cos(head) * 0.3, ty - 0.45, tz - math.sin(head) * 0.3))
    barnacles(lamps, (x, max(base, 0.0) + 0.3, z), (0.17, 0.25), 6 + k * 3, size=0.04)
lamps.build("road_lamps", tideline=True, grime=0.15)
lamp_col.build("COL_road_lamps", ao=0, grime=0)

# A milestone on the verge, and the fingerpost that stood at the junction, down
# in the sand. The arms pointed the way the road still goes: into the sea.
rx, rz, mh = road_at(0.18)
mx, mz = rx - 2.6, rz
mile = MB(62)
mile.box((0.42, 0.95, 0.24), at=(0, -0.25, 0), mat=P["stone"], bev=0.05)
mile.cyl(0.21, 0.21, 0.24, at=(0, 0.7, 0), mat=P["stone"], pitch=math.pi / 2, centered=True, segs=12)
mile.box((0.3, 0.2, 0.03), at=(0, 0.25, 0.12), mat=P["stone_dark"], bev=0)
mile.build("milestone", loc=(mx, H(mx, mz), mz), yaw=mh + 0.15, roll=0.08, grime=0.3)
MB().box((0.45, 1.1, 0.3), at=(0, -0.3, 0), bev=0).build("COL_milestone", loc=(mx, H(mx, mz), mz), yaw=mh + 0.15, ao=0, grime=0)
fx, fz, fh = road_at(0.33)
fx += 2.8
finger = MB(63)
finger.box((0.14, 0.14, 2.6), at=(0, 0.07, 0), mat=P["driftwood_dark"], bev=0.02)
for k, (dz, ang) in enumerate(((0.9, 0.5), (0.6, -0.7))):
    finger.prism([(-0.55, -0.1), (0.4, -0.1), (0.55, 0.0), (0.4, 0.1), (-0.55, 0.1)], 0.04, at=(0.0, 0.2 + k * 0.03, dz), mat=Paint(P["paint_white"].mat, 0xB9B2A0), yaw=ang, pitch=-math.pi / 2, bev=0)
finger.build("fingerpost_fallen", loc=(fx, H(fx, fz), fz), yaw=fh + 1.1, grime=0.35)

# An older wreck than the Meridian: a coaster's skeleton on the east flats,
# keel to the sea. The tide fills her at high water.
bx, bz = 43.5, 4.5
rib = kit.place(TEMPLATES, "hull_ribs", "old_wreck", (bx, H(bx, bz) - 0.25, bz), yaw=0.25, scale=1.75)
MB().box((0.6, 0.6, 10.6), at=(0, -0.2, 0), bev=0).build("COL_old_wreck_keel", loc=(bx, H(bx, bz) - 0.25, bz), yaw=0.25, ao=0, grime=0)
for k in range(3):
    a = 0.25 + k * 0.4
    x, z = bx + math.sin(a) * (2.5 + k * 1.2) + 2.2, bz + math.cos(a) * 3.0 - 5.5
    if clear(x, z):
        kit.place(TEMPLATES, "seaweed", f"old_wreck_weed_{k}", (x, H(x, z), z), yaw=dr.random() * math.tau)

# Rocks in the shallows off the flats' north edge, weed below and barnacles at
# the waterline: where the land used to end in a field wall.
for i, (x, z, r) in enumerate(((-10.0, -21.0, 2.0), (-7.0, -22.5, 1.4), (15.0, -20.5, 1.8), (17.5, -22.0, 1.2), (-39.0, -26.5, 2.2), (43.0, -16.5, 1.6), (45.5, -19.0, 1.1))):
    rk = MB(70 + i)
    rk.rock(r, mat=P["rock"] if i % 2 else P["rock_dark"], seed=400 + i, squash=0.75)
    seaweed_y = 0.0 - H(x, z) + r * 0.1
    for k in range(5):
        a = dr.random() * math.tau
        rk.tube([(math.cos(a) * r * 0.8, seaweed_y, math.sin(a) * r * 0.8), (math.cos(a) * r * 1.2, seaweed_y - 0.25, math.sin(a) * r * 1.25)], [0.05, 0.02], mat=P["kelp_dark"], segs=4)
    barnacles(rk, (0.0, -H(x, z) + 0.9, 0.0), (r * 0.95, 0.5), 10, size=0.05)
    rk.build(f"rock_shallows_{i}", loc=(x, H(x, z) - r * 0.25, z), tideline=True, props={"col": 1})

# A crofter's cottage on the east dunes, roofless since before anyone here
# remembers: walls of rubble stone, one gable still standing with its chimney,
# a door gap facing the jetty, the fallen roof timbers inside.
CX, CZ, CYAW = 41.0, 37.0, -0.35
cg = H(CX, CZ) - 0.15
cot = MB(80)
cot_col = MB()
W, Dp, T = 6.4, 4.6, 0.5
RUBBLE = [Paint(P["stone"].mat, c) for c in (0x9A958A, 0x8C877C, 0xA39D90)]
walls = [
    # (centre x, centre z, length, along x?, height left, height right)
    (0.0, -Dp / 2, W, True, 1.6, 2.2),
    (-W / 2, 0.0, Dp, False, 2.3, 2.3),
    (W / 2, 0.0, Dp, False, 1.0, 1.5),
]
for wx, wz, L, along, h0, h1 in walls:
    # Broken walls step down in a few runs; the standing gable is one piece.
    n = 1 if h0 == h1 else 4
    for k in range(n):
        u0 = k / n
        h = h0 + (h1 - h0) * (u0 + 0.5 / n) - (0.12 * dr.random() if h0 != h1 else 0.0)
        seg = L / n
        px = wx + ((u0 + 0.5 / n) - 0.5) * L if along else wx
        pz = wz if along else wz + ((u0 + 0.5 / n) - 0.5) * L
        size = (seg + 0.02, h, T) if along else (T, h, seg + 0.02)
        cot.box(size, at=(px, -0.1, pz), mat=RUBBLE[k % 3], tint=0.85 + 0.2 * dr.random(), bev=0.06)
        cot_col.box(size, at=(px, -0.1, pz), bev=0)
# Front wall (+z, toward the jetty): a door gap in the middle, a window gap left.
for x0, x1, h in ((-W / 2, -0.7, 1.5), (0.7, W / 2, 1.2)):
    L = x1 - x0
    cot.box((L, h, T), at=((x0 + x1) / 2, -0.1, Dp / 2), mat=RUBBLE[1], tint=0.9, bev=0.06)
    cot_col.box((L, h, T), at=((x0 + x1) / 2, -0.1, Dp / 2), bev=0)
# The gable on the west wall, and its chimney.
cot.prism([(-Dp / 2 - T / 2, 0.0), (Dp / 2 + T / 2, 0.0), (0.0, 1.8)], T, at=(-W / 2, 2.2, 0.0), mat=RUBBLE[0], yaw=math.pi / 2, bev=0.05)
cot.box((0.75, 1.7, 0.8), at=(-W / 2 - 0.02, 3.4, 0.0), mat=RUBBLE[1], bev=0.05)
cot.cyl(0.14, 0.12, 0.35, at=(-W / 2 - 0.02, 5.1, 0.0), mat=Paint(P["stone"].mat, 0x8A5A44), segs=8)
# Roof timbers fallen in, and rubble along the low walls.
for k in range(4):
    cot.box((0.14, 0.14, 3.8), at=(-1.8 + k * 1.2, 0.1 + 0.18 * k, -0.4), mat=P["driftwood_dark"], pitch=0.22 + 0.08 * k, roll=0.2 * (dr.random() - 0.5), bev=0.02)
for k in range(14):
    x = (dr.random() - 0.5) * (W + 1.5)
    z = (dr.random() - 0.5) * (Dp + 1.5)
    if abs(x) < W / 2 - 0.5 and abs(z) < Dp / 2 - 0.5:
        continue
    cot.rock(0.18 + dr.random() * 0.15, at=(x, 0.0, z), mat=RUBBLE[k % 3], seed=500 + k, squash=0.7)
cot.build("croft_ruin", loc=(CX, cg, CZ), yaw=CYAW, grime=0.3)
cot_col.build("COL_croft_ruin", loc=(CX, cg, CZ), yaw=CYAW, ao=0, grime=0)


def croft_at(lx, ly, lz):
    c, s = math.cos(CYAW), math.sin(CYAW)
    return (CX + lx * c + lz * s, cg + ly, CZ - lx * s + lz * c)


# A gull on the chimney beside its pot, another on the low east wall.
kit.empty("FX_perch_croft_chimney", croft_at(-W / 2 - 0.02, 5.4, 0.28))
kit.empty("FX_perch_croft_wall", croft_at(W / 2, 1.8, 0.9))

# The sand itself: shells and pebbles, broken crab shells and strands of weed
# the last tide left, thickest along the strand line. One mesh, nothing solid.
litter = MB(90)
n_items = 0
for _ in range(2600):
    if n_items >= 520:
        break
    x, z = dr.uniform(-48.0, 50.0), dr.uniform(-22.0, 24.0)
    y = H(x, z)
    if y < -0.4 or y > 3.1 or not clear(x, z, -1.5):
        continue
    # Densest on the strand (y ~ 1.9) and in the pools' rims.
    strand = math.exp(-((y - 1.95) / 0.35) ** 2)
    if dr.random() > 0.25 + 0.75 * strand:
        continue
    n_items += 1
    kind = dr.random()
    if kind < 0.45:
        litter.sphere(0.035 + dr.random() * 0.05, at=(x, y + 0.005, z), mat=P["stone"] if dr.random() < 0.5 else P["rock"], scale=(1.0, 0.55, 0.8), subdiv=1, yaw=dr.random() * math.tau, tint=0.75 + 0.4 * dr.random())
    elif kind < 0.75:
        litter.sphere(0.04 + dr.random() * 0.03, at=(x, y + 0.004, z), mat=P["bone"] if dr.random() < 0.7 else P["barnacle"], scale=(1.0, 0.3, 0.75), subdiv=0, yaw=dr.random() * math.tau, tint=0.85 + 0.2 * dr.random())
    elif kind < 0.9:
        a = dr.random() * math.tau
        L = 0.4 + dr.random() * 0.7
        pts = [(x + math.cos(a) * L * t + 0.08 * math.sin(t * 7 + a), y + 0.01, z + math.sin(a) * L * t + 0.08 * math.cos(t * 6)) for t in (0.0, 0.33, 0.66, 1.0)]
        litter.tube(pts, [0.03, 0.025, 0.02, 0.012], mat=P["kelp"] if dr.random() < 0.6 else P["kelp_dark"], segs=3, cap=False)
    else:
        # A crab's cast shell, pale and upside down.
        litter.sphere(0.09, at=(x, y + 0.01, z), mat=Paint(P["bone"].mat, 0xC9A08A), scale=(1.0, 0.35, 0.8), subdiv=1, yaw=dr.random() * math.tau)
litter.build("beach_litter", ao=0.3, grime=0.0)

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

# ------------------------------------------------------------------ gloom

# GLOOM_ pockets (docs/ART_PIPELINE.md): darkness hanging over the sealed cache
# on the islet. The Lantern Flare burns it off. Clear of the islet's anchor, so
# the current never rescues you into it.
kit.empty("GLOOM_islet", (58.5, H(58.5, -53.5), -53.5), props={"radius": 3.5})

# ---------------------------------------------------- anchors and the beam

for i, (x, z) in enumerate([(-30, 30), (25, 32), (0, 26), (54, -50), (-43, -12), (-44, 8)]):
    kit.empty(f"ANCHOR_{i}", (x, H(x, z) + 0.1, z))
kit.empty("ANCHOR_jetty", (JX, JY, 50))
# Lantern's Rest lies south-west; its beam shows on the horizon there.
kit.empty("FX_home_light", (-260, 0, 230))

kit.save_and_export("art/blender/locations/shore.blend", "public/assets/models/locations/shore.glb")
