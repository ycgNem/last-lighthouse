"""Builds art/blender/props/props.blend and public/assets/models/props.glb.

Every prop is a top-level object named PROP_<id>, base centred on its origin,
front facing game +Z. The game clones them by name onto NODE_ markers and the
location scripts place copies (kit.place). Gather nodes have to read at a
glance as "something to take", so each one has a clear silhouette and a
material story: bleached driftwood, rust and iron, olive kelp, frosted glass,
brass that catches the light.

    blender -b --factory-startup --python tools/blender/build/props.py
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import kit  # noqa: E402
from kit import MB, Paint, hull_sections  # noqa: E402

kit.reset()
P = kit.palette()
LAMP = P["lamp"]
LENS = kit.material("lens_glass", 0xF4FBFF, rough=0.05, emit=0xFFF1C9, strength=0.6)
FROST = kit.surface("seaglass", rough=0.45)
SEAGLASS = [Paint(FROST, c) for c in (0xA8D8C8, 0x6FAF8A, 0x4F7FB8, 0xC98A3A, 0xE6EEEA)]
KELP = [P["kelp"], P["kelp_dark"], Paint(P["kelp"].mat, 0x5A5328), Paint(P["kelp"].mat, 0x6B5A2A)]
TAU = math.tau

slot = [0]


def place():
    """Spread props along X in the .blend so they're easy to find by eye."""
    slot[0] += 1
    return ((slot[0] % 8) * 5.0, 0, (slot[0] // 8) * 5.0)


# ----------------------------------------------------------- small parts


def lantern(m, at, s=1.0):
    """A square ship's lantern, glass centred on `at`: base, corner posts,
    glowing panes, a pyramid cap and a carrying ring."""
    x, y, z = at
    iron = P["iron"]
    m.cyl(0.115 * s, 0.125 * s, 0.045 * s, at=(x, y - 0.2 * s, z), mat=iron, segs=4, yaw=math.pi / 4)
    m.box((0.15 * s, 0.27 * s, 0.15 * s), at=(x, y - 0.155 * s, z), mat=LAMP, bev=0)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        m.box((0.022 * s, 0.31 * s, 0.022 * s), at=(x + math.cos(a) * 0.105 * s, y - 0.17 * s, z + math.sin(a) * 0.105 * s), mat=iron, bev=0)
    m.box((0.17 * s, 0.018 * s, 0.17 * s), at=(x, y - 0.02 * s, z), mat=iron, bev=0)
    m.cyl(0.135 * s, 0.035 * s, 0.13 * s, at=(x, y + 0.13 * s, z), mat=iron, segs=4, yaw=math.pi / 4)
    m.cyl(0.03 * s, 0.03 * s, 0.05 * s, at=(x, y + 0.25 * s, z), mat=iron, segs=6)
    m.ring(0.045 * s, 0.009 * s, at=(x, y + 0.33 * s, z), mat=iron, pitch=math.pi / 2, segs=10, tube_segs=4)


def barnacles(m, rnd, center, spread, count, up=(0, 1, 0), size=0.05):
    """Little volcano cones in clusters (barnacles) around `center`."""
    cx, cy, cz = center
    for _ in range(count):
        dx = (rnd.random() - 0.5) * 2 * spread[0]
        dy = (rnd.random() - 0.5) * 2 * spread[1]
        dz = (rnd.random() - 0.5) * 2 * spread[2]
        r = size * (0.6 + rnd.random() * 0.7)
        prof = [(r, 0), (r * 0.75, r * 0.7), (r * 0.35, r * 0.95), (r * 0.25, r * 0.7), (0, r * 0.6)]
        pitch = math.atan2(up[2], up[1]) if up != (0, 1, 0) else 0.0
        m.lathe(prof, at=(cx + dx, cy + dy, cz + dz), mat=P["barnacle"], segs=6, pitch=pitch, jit=0.1)


def chain(m, a, b, link=0.09, thick=0.016, mat=None, sag=0.0):
    """Interlocking oval links from a to b (game points), each turned 90 degrees
    from the last. `sag` drops the middle (negative lifts it)."""
    ax, ay, az = a
    bx, by, bz = b
    L = math.dist(a, b)
    n = max(2, int(L / (link * 0.78)))

    def at(t):
        return (ax + (bx - ax) * t, ay + (by - ay) * t - math.sin(t * math.pi) * sag, az + (bz - az) * t)

    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        p0, p1 = at(t0), at(t1)
        d = [p1[k] - p0[k] for k in range(3)]
        dl = math.sqrt(sum(c * c for c in d)) or 1.0
        d = [c / dl for c in d]
        # Two perpendiculars to the chain; links alternate between them.
        ref = (0.0, 1.0, 0.0) if abs(d[1]) < 0.9 else (1.0, 0.0, 0.0)
        u = (d[1] * ref[2] - d[2] * ref[1], d[2] * ref[0] - d[0] * ref[2], d[0] * ref[1] - d[1] * ref[0])
        ul = math.sqrt(sum(c * c for c in u)) or 1.0
        u = [c / ul for c in u]
        if i % 2:
            u = [d[1] * u[2] - d[2] * u[1], d[2] * u[0] - d[0] * u[2], d[0] * u[1] - d[1] * u[0]]
        c = [(p0[k] + p1[k]) / 2 for k in range(3)]
        half_l, half_w = link * 0.62, link * 0.32
        pts = []
        for s in range(11):
            ang = s / 10 * TAU
            pts.append(tuple(c[k] + d[k] * math.cos(ang) * half_l + u[k] * math.sin(ang) * half_w for k in range(3)))
        m.tube(pts, thick, mat=mat or P["iron"], segs=4, cap=False, jit=0.06)


def rivets(m, pts, r=0.018, mat=None, axis="z"):
    for p in pts:
        pitch = math.pi / 2 if axis == "z" else 0.0
        roll = math.pi / 2 if axis == "x" else 0.0
        m.cyl(r, r * 0.8, r * 0.7, at=p, mat=mat or P["iron"], segs=6, pitch=pitch, roll=roll, centered=True, bev=0)


def ribbon(m, pts, widths, mat, normal=(0, 1, 0), jit=0.06, tint=1.0):
    """A flat strip through game points (kelp blades, weed, cloth strips)."""
    nx, ny, nz = normal
    secs = []
    for i, (x, y, z) in enumerate(pts):
        j = min(i + 1, len(pts) - 1)
        k = max(i - 1, 0)
        tx, ty, tz = pts[j][0] - pts[k][0], pts[j][1] - pts[k][1], pts[j][2] - pts[k][2]
        # side = tangent x normal
        sx, sy, sz = ty * nz - tz * ny, tz * nx - tx * nz, tx * ny - ty * nx
        sl = math.sqrt(sx * sx + sy * sy + sz * sz) or 1.0
        w = widths[i] / 2 / sl
        secs.append([(x - sx * w, y - sy * w, z - sz * w), (x + sx * w, y + sy * w, z + sz * w)])
    m.loft(secs, mat=mat, jit=jit, tint=tint)


def seaweed_clump(m, rnd, at, count=5, length=0.7):
    x0, y0, z0 = at
    for i in range(count):
        a = rnd.random() * TAU
        L = length * (0.6 + rnd.random() * 0.6)
        pts = []
        for k in range(5):
            t = k / 4
            pts.append((x0 + math.cos(a) * L * t + math.sin(t * 6 + i) * 0.05, y0 + 0.02 + math.sin(t * math.pi) * 0.04, z0 + math.sin(a) * L * t))
        ribbon(m, pts, [0.05, 0.08, 0.09, 0.07, 0.02], rnd.choice(KELP))


# ------------------------------------------------------------ gather nodes


def driftwood():
    """A bleached log with its root flare, a crossing branch and a few sticks."""
    m = MB(11)
    rnd = random.Random(11)
    pts, radii = [], []
    for i in range(10):
        t = i / 9
        pts.append((-1.3 + t * 2.75, 0.22 - t * 0.09 + math.sin(t * 2.6) * 0.035, math.sin(t * 2.1 + 0.3) * 0.2))
        radii.append(0.23 - 0.15 * t ** 0.8)
    m.tube(pts, radii, mat=P["driftwood"], segs=9)
    # Root flare: short tapering roots splayed back and out from the thick end.
    for k in range(7):
        a = k / 7 * TAU + rnd.random() * 0.5
        L = 0.4 + rnd.random() * 0.35
        base = (-1.25, 0.22, 0.04)
        tip = (base[0] - 0.25 - rnd.random() * 0.3, max(0.04, base[1] + math.sin(a) * L), base[2] + math.cos(a) * L)
        mid = ((base[0] + tip[0]) / 2 - 0.05, (base[1] + tip[1]) / 2 + 0.06, (base[2] + tip[2]) / 2)
        m.tube([base, mid, tip], [0.09, 0.05, 0.012], mat=P["driftwood_dark"] if k % 3 == 0 else P["driftwood"], segs=6)
    # Broken branch stubs along the trunk.
    for t, a in ((0.38, 0.9), (0.62, -1.4), (0.8, 0.4)):
        i = int(t * 9)
        x, y, z = pts[i]
        m.tube([(x, y, z), (x + 0.12, y + 0.18 * math.cos(a), z + 0.2 * math.sin(a))], [0.06, 0.03], mat=P["driftwood"], segs=6)
    # A thinner, darker branch lying across it.
    m.tube([(-0.2, 0.06, -0.75), (0.15, 0.3, -0.1), (0.35, 0.34, 0.25), (0.7, 0.07, 0.8)], [0.07, 0.065, 0.06, 0.045], mat=P["driftwood_dark"], segs=7)
    # Sticks.
    for k in range(4):
        x, z = 0.5 + rnd.random() * 0.8, (rnd.random() - 0.5) * 1.3
        a = rnd.random() * TAU
        L = 0.4 + rnd.random() * 0.3
        m.tube([(x, 0.035, z), (x + math.cos(a) * L, 0.03, z + math.sin(a) * L)], [0.03, 0.018], mat=P["driftwood"], segs=5)
    m.rock(0.22, at=(1.05, 0.0, -0.45), mat=P["rock"], seed=4, squash=0.55)
    m.rock(0.14, at=(-0.6, 0.0, 0.55), mat=P["rock_dark"], seed=5, squash=0.6)
    m.build("PROP_driftwood", loc=place())


def scrap_pile():
    """Rusted junk: crumpled plates, a corrugated sheet, a gear, a bent pipe, chain."""
    m = MB(2)
    rnd = random.Random(2)
    paint_scrap = Paint(P["paint_blue"].mat, 0x4F6E6A)
    # A low bed of grit and pebbles the junk has settled into.
    m.lathe([(0.0, 0.07), (0.5, 0.06), (0.85, 0.02), (1.0, -0.03)], mat=Paint(P["sand"].mat, 0x7D7262), segs=16)
    for i in range(8):
        a = rnd.random() * TAU
        r = 0.6 + rnd.random() * 0.35
        m.rock(0.05 + rnd.random() * 0.05, at=(math.cos(a) * r, 0.0, math.sin(a) * r), mat=P["rock_dark"], seed=60 + i, squash=0.6, cuts=2, subdiv=1)
    # Crumpled plates, stacked and tipped, resting on each other.
    plates = (P["iron"], P["rust"], paint_scrap, P["iron_light"], P["rust"], P["iron"])
    for i, mat in enumerate(plates):
        w, d = 0.55 + rnd.random() * 0.55, 0.4 + rnd.random() * 0.45
        m.box((w, 0.035, d), at=((rnd.random() - 0.5) * 0.8, 0.09 + i * 0.05, (rnd.random() - 0.5) * 0.6), mat=mat,
              yaw=rnd.random() * 3, pitch=(rnd.random() - 0.5) * 0.3, roll=(rnd.random() - 0.5) * 0.3, centered=True, bev=0.008)
    # A corrugated sheet leaning on the heap.
    wave = [(-0.6 + k * 0.1, 0.035 * (1 if k % 2 else -1)) for k in range(13)]
    outline = wave + [(x, y - 0.025) for x, y in reversed(wave)]
    m.prism(outline, 0.9, at=(0.3, 0.36, -0.3), mat=P["rust"], yaw=0.5, roll=0.5, bev=0)
    # A cog leaning against it, and a valve wheel lying on top.
    teeth = []
    for k in range(32):
        a = k / 32 * TAU
        r = 0.3 if (k // 2) % 2 else 0.25
        teeth.append((math.cos(a) * r, math.sin(a) * r))
    m.prism(teeth, 0.06, at=(-0.48, 0.33, 0.22), mat=P["iron_light"], yaw=0.4, pitch=-0.35, bev=0.006)
    m.cyl(0.08, 0.08, 0.09, at=(-0.48, 0.33, 0.22), mat=P["rust"], segs=8, pitch=math.pi / 2 - 0.35, yaw=0.4, centered=True)
    m.ring(0.2, 0.022, at=(0.05, 0.42, 0.1), mat=P["iron"], segs=16, tube_segs=4, pitch=0.12)
    for k in range(4):
        a = k / 4 * TAU
        m.tube([(0.05, 0.42, 0.1), (0.05 + math.cos(a) * 0.2, 0.42 + math.sin(a) * 0.02, 0.1 + math.sin(a) * 0.2)], 0.014, mat=P["iron"], segs=4)
    # A bent pipe with a flange, sticking out of the heap.
    m.tube([(0.1, 0.12, 0.5), (0.5, 0.14, 0.45), (0.74, 0.24, 0.2), (0.8, 0.52, 0.05)], 0.06, mat=P["iron_light"], segs=8)
    m.ring(0.07, 0.022, at=(0.8, 0.52, 0.05), mat=P["rust"], segs=10, tube_segs=4)
    chain(m, (-0.35, 0.36, -0.15), (0.35, 0.44, 0.28), sag=0.1)
    m.build("PROP_scrap_pile", loc=place(), grime=0.25)


def kelp_bed():
    """A wet boulder with olive-brown kelp flopped over it and out across the sand."""
    m = MB(3)
    rnd = random.Random(3)
    m.rock(0.55, at=(0, -0.05, 0), mat=P["rock_dark"], seed=8, squash=0.5)
    m.rock(0.3, at=(0.55, -0.05, 0.3), mat=P["rock_dark"], seed=9, squash=0.45)
    # Fronds: stipe up over the rock, then a long ribbon blade lying out.
    for i in range(11):
        a = i / 11 * TAU + rnd.random() * 0.4
        L = 1.0 + rnd.random() * 0.7
        base = (math.cos(a) * 0.15, 0.32, math.sin(a) * 0.12)
        pts = [base]
        for k in range(1, 8):
            t = k / 7
            r = 0.15 + t * L
            pts.append((math.cos(a + math.sin(t * 5 + i) * 0.12) * r, max(0.03, 0.32 + 0.12 * math.sin(t * math.pi * 0.8) - t * 0.42), math.sin(a + math.sin(t * 4 + i) * 0.12) * r))
        widths = [0.04, 0.09, 0.15, 0.17, 0.17, 0.15, 0.11, 0.04]
        ribbon(m, pts, widths, KELP[i % len(KELP)])
        # Gas bladders along the stipe.
        for k in (1, 2):
            x, y, z = pts[k]
            m.sphere(0.035, at=(x, y + 0.02, z), mat=KELP[2], scale=(1.0, 0.8, 1.3), subdiv=1)
    seaweed_clump(m, rnd, (-0.4, 0.0, 0.5), count=4, length=0.6)
    m.build("PROP_kelp_bed", loc=place(), grime=0.1)


def glass_bed():
    """A low sandy hump strewn with pebbles, shells and frosted sea glass."""
    m = MB(5)
    rnd = random.Random(5)
    m.lathe([(0.0, 0.09), (0.35, 0.085), (0.65, 0.06), (0.88, 0.02), (1.0, -0.03)], mat=P["sand"], segs=18)
    for i in range(12):
        a = rnd.random() * TAU
        r = 0.15 + rnd.random() * 0.7
        m.rock(0.04 + rnd.random() * 0.05, at=(math.cos(a) * r, 0.06 - r * 0.05, math.sin(a) * r * 0.85), mat=rnd.choice((P["rock"], P["rock_dark"], P["stone_dark"])), seed=50 + i, squash=0.5, cuts=2, subdiv=1)
    for i in range(16):
        a = rnd.random() * TAU
        r = rnd.random() * 0.72
        s = 0.045 + rnd.random() * 0.04
        m.sphere(s, at=(math.cos(a) * r, 0.11 - r * 0.07, math.sin(a) * r * 0.85), mat=SEAGLASS[i % len(SEAGLASS)], scale=(1.35, 0.42, 1.0), subdiv=1, yaw=rnd.random() * TAU, jit=0.08)
    # Two cockle shells.
    for i, (x, z) in enumerate(((0.35, -0.3), (-0.5, 0.15))):
        prof = [(0.0, 0.0), (0.07, 0.0), (0.065, 0.02), (0.04, 0.035), (0.0, 0.04)]
        m.lathe(prof, at=(x, 0.08, z), mat=P["bone"], segs=10, staves=0.12, tint=1.0, jit=0.04)
    m.build("PROP_glass_bed", loc=place(), grime=0.0)


def reinforced_wreckage():
    """A torn-off piece of hull leaning back: tarred strakes on two frames,
    iron knees, brass bolts and a brass porthole. The brass is why you come."""
    m = MB(6)
    rnd = random.Random(6)
    th = 0.32  # lean back from vertical

    def panel(u, v, w=0.0):
        """Point on the leaning panel: u across, v up its face, w out of it."""
        return (u, v * math.cos(th) + w * math.sin(th), -v * math.sin(th) + w * math.cos(th))

    # Frames behind the planking.
    for x in (-0.75, 0.75):
        m.box((0.16, 1.8, 0.18), at=panel(x, 0.9, -0.13), mat=P["hull_dark"], pitch=-th, centered=True)
    # Strakes, each a little proud of the one below; a ragged top edge.
    for i in range(6):
        v = 0.14 + i * 0.27
        w = 2.3 - (0.9 * rnd.random() if i == 5 else 0.25 * rnd.random())
        off = (rnd.random() - 0.5) * 0.25 + (0.35 if i == 5 else 0.0)
        m.box((w, 0.26, 0.07), at=panel(off, v, 0.0 + (i % 2) * 0.012), mat=P["hull"] if i % 2 else P["hull_dark"], pitch=-th, roll=(rnd.random() - 0.5) * 0.03, centered=True, jit=0.08)
    # Snapped strake ends at the top, showing paler wood where they broke.
    for x, v, ang in ((-0.95, 1.6, 0.35), (0.95, 1.52, -0.5)):
        m.box((0.45, 0.2, 0.07), at=panel(x, v, 0.01), mat=P["hull"], pitch=-th, roll=ang, centered=True)
        m.box((0.06, 0.16, 0.06), at=panel(x + math.copysign(0.24, ang) * -1, v + 0.06, 0.01), mat=P["timber_pale"], pitch=-th, roll=ang * 1.5, centered=True, bev=0)
    # Iron straps over the frames, brass bolts through them.
    for x in (-0.75, 0.75):
        m.box((0.11, 1.55, 0.025), at=panel(x, 0.85, 0.05), mat=P["iron"], pitch=-th, centered=True, bev=0.004)
        for k in range(5):
            m.cyl(0.027, 0.022, 0.03, at=panel(x, 0.25 + k * 0.3, 0.07), mat=P["brass"], segs=8, pitch=math.pi / 2 - th, centered=True, bev=0)
    # The porthole: brass rim, blue-grey glass, gilt bolts round it.
    m.cyl(0.24, 0.24, 0.07, at=panel(0.1, 0.86, 0.05), mat=P["brass"], segs=18, pitch=math.pi / 2 - th, centered=True)
    m.cyl(0.17, 0.17, 0.09, at=panel(0.1, 0.86, 0.05), mat=P["glass_blue"], segs=18, pitch=math.pi / 2 - th, centered=True)
    for k in range(8):
        a = k / 8 * TAU
        m.sphere(0.022, at=panel(0.1 + math.cos(a) * 0.205, 0.86 + math.sin(a) * 0.205, 0.09), mat=P["gilt"], subdiv=1)
    # A brass cleat and a hinge plate.
    m.box((0.34, 0.06, 0.07), at=panel(-0.4, 1.3, 0.07), mat=P["brass"], pitch=-th, centered=True, bev=0.012)
    m.box((0.2, 0.15, 0.02), at=panel(0.62, 0.45, 0.05), mat=P["brass"], pitch=-th, centered=True, bev=0.004)
    barnacles(m, rnd, panel(0.0, 0.2, 0.05), (1.0, 0.1, 0.03), 16, up=(0, math.sin(th), math.cos(th)), size=0.035)
    m.build("PROP_reinforced_wreckage", loc=place(), grime=0.3)


def slatted_crate(m, size, at=(0, 0, 0), wood=None, frame=None, gap=0.012, yaw=0.0, slats=3):
    """A crate of real slats: dark core, slats on every side, corner battens."""
    sx, sy, sz = size
    x0, y0, z0 = at
    wood = wood or P["timber_light"]
    frame = frame or P["timber"]
    m.box((sx - 0.04, sy - 0.04, sz - 0.04), at=(x0, y0 + 0.02, z0), mat=P["tar"], bev=0, yaw=yaw)
    h = (sy - gap * (slats - 1)) / slats
    c, s = math.cos(yaw), math.sin(yaw)

    def rot(x, z):
        return (x0 + x * c + z * s, z0 - x * s + z * c)

    for k in range(slats):
        y = y0 + k * (h + gap)
        for side in (-1, 1):
            x, z = rot(0, side * (sz / 2 - 0.012))
            m.box((sx - 0.02, h, 0.024), at=(x, y, z), mat=wood, yaw=yaw, jit=0.09)
            x, z = rot(side * (sx / 2 - 0.012), 0)
            m.box((0.024, h, sz - 0.05), at=(x, y, z), mat=wood, yaw=yaw, jit=0.09)
    # Lid planks.
    n = 4
    w = (sx - gap * (n - 1)) / n
    for k in range(n):
        x, z = rot(-sx / 2 + w / 2 + k * (w + gap), 0)
        m.box((w, 0.026, sz), at=(x, y0 + sy - 0.026, z), mat=wood, yaw=yaw, jit=0.09)
    # Corner battens and rims.
    for dx in (-1, 1):
        for dz in (-1, 1):
            x, z = rot(dx * (sx / 2 - 0.01), dz * (sz / 2 - 0.01))
            m.box((0.07, sy + 0.01, 0.07), at=(x, y0, z), mat=frame, yaw=yaw)
    for y in (y0, y0 + sy - 0.06):
        for side in (-1, 1):
            x, z = rot(0, side * (sz / 2 + 0.006))
            m.box((sx, 0.06, 0.03), at=(x, y, z), mat=frame, yaw=yaw)


def supply_crate():
    """A slatted crate with rope handles and a faded painted band."""
    m = MB(7)
    slatted_crate(m, (0.9, 0.78, 0.9))
    # Diagonal brace on the front and back.
    for side in (-1, 1):
        m.box((1.05, 0.06, 0.03), at=(0, 0.38, side * 0.468), mat=P["timber"], roll=0.72 * side, centered=True)
        m.box((0.5, 0.14, 0.006), at=(0, 0.52, side * 0.4535), mat=Paint(P["paint_white"].mat, 0xB9B2A2), bev=0)
    for side in (-1, 1):
        m.tube([(side * 0.47, 0.6, -0.16), (side * 0.53, 0.52, -0.1), (side * 0.53, 0.52, 0.1), (side * 0.47, 0.6, 0.16)], 0.018, mat=P["rope"], segs=5)
    m.build("PROP_supply_crate", loc=place())


def sealed_cache():
    """A sea chest half sunk in sand, barnacled, chained and padlocked."""
    m = MB(8)
    rnd = random.Random(9)
    m.sphere(0.9, at=(0, -0.08, 0), mat=P["sand"], scale=(1.0, 0.22, 0.75), subdiv=2)
    m.box((1.2, 0.5, 0.78), at=(0, 0.0, 0), mat=P["hull_dark"])
    # Camel-back lid: a half-round prism along X.
    arc = [(math.cos(a) * 0.4, math.sin(a) * 0.22) for a in [k / 10 * math.pi for k in range(11)]]
    m.prism(arc, 1.2, at=(0, 0.5, 0), mat=P["hull"], yaw=math.pi / 2, bev=0.01)
    # Iron bands over the lid and round the body.
    for x in (-0.42, 0.0, 0.42):
        band = [(x, 0.0, -0.405)] + [(x, 0.5 + math.sin(a) * 0.235, -math.cos(a) * 0.415) for a in [k / 10 * math.pi for k in range(11)]] + [(x, 0.0, 0.405)]
        m.tube(band, 0.03, mat=P["iron"], segs=4, cap=True)
    m.box((1.24, 0.07, 0.82), at=(0, 0.42, 0), mat=P["iron"], bev=0.01)
    # Chain across the lid to a big padlock.
    chain(m, (-0.62, 0.38, 0.42), (0.0, 0.68, 0.36), link=0.1, thick=0.018, mat=P["rust"], sag=-0.05)
    chain(m, (0.0, 0.68, 0.36), (0.62, 0.38, 0.42), link=0.1, thick=0.018, mat=P["rust"], sag=-0.05)
    m.box((0.18, 0.2, 0.08), at=(0, 0.2, 0.43), mat=P["brass"], bev=0.015)
    m.ring(0.065, 0.018, at=(0, 0.42, 0.43), mat=P["iron_light"], pitch=math.pi / 2, segs=12, tube_segs=5)
    barnacles(m, rnd, (0.0, 0.12, 0.4), (0.6, 0.1, 0.01), 18, up=(0, 0, 1), size=0.04)
    barnacles(m, rnd, (0.55, 0.3, 0.0), (0.02, 0.15, 0.35), 8, size=0.035)
    seaweed_clump(m, rnd, (-0.5, 0.02, 0.45), count=3, length=0.5)
    m.build("PROP_sealed_cache", loc=place(), grime=0.3)


def strongbox():
    """The captain's strongbox: riveted iron plates, brass corners, a brass lock."""
    m = MB(10)
    m.box((0.8, 0.42, 0.55), mat=P["iron"])
    m.box((0.84, 0.12, 0.59), at=(0, 0.42, 0), mat=P["iron_light"], bev=0.012)
    for dx in (-1, 1):
        for dz in (-1, 1):
            for y in (0.0, 0.38):
                m.box((0.12, 0.16, 0.12), at=(dx * 0.36, y, dz * 0.24), mat=P["brass"], bev=0.01)
    m.box((0.2, 0.22, 0.03), at=(0, 0.14, 0.285), mat=P["brass"], bev=0.01)
    m.cyl(0.025, 0.025, 0.035, at=(0, 0.27, 0.3), mat=P["tar"], segs=8, pitch=math.pi / 2, centered=True, bev=0)
    m.box((0.016, 0.05, 0.035), at=(0, 0.2, 0.3), mat=P["tar"], bev=0)
    rivets(m, [(x, y, 0.278) for x in (-0.28, -0.14, 0.14, 0.28) for y in (0.08, 0.32)], r=0.014)
    rivets(m, [(0.405, y, z) for z in (-0.15, 0.0, 0.15) for y in (0.08, 0.32)], r=0.014, axis="x")
    for side in (-1, 1):
        m.ring(0.07, 0.014, at=(side * 0.43, 0.3, 0), mat=P["iron_light"], roll=math.pi / 2, segs=12, tube_segs=4)
    m.build("PROP_strongbox", loc=place())


def lens_pedestal():
    """A stone column with a brass yoke holding the Drowned Lens. The lens and
    its ring are a separate child (part: lens) so the game can take them away."""
    m = MB(12)
    m.box((0.95, 0.16, 0.95), mat=P["stone_dark"], bev=0.03)
    prof = [(0.4, 0.16), (0.4, 0.24), (0.33, 0.3), (0.28, 0.36), (0.25, 1.0), (0.3, 1.06), (0.36, 1.12), (0.36, 1.2), (0.0, 1.2)]
    m.lathe(prof, mat=P["stone"], segs=14, cap=True, jit=0.04)
    # Brass yoke.
    m.cyl(0.3, 0.3, 0.05, at=(0, 1.2, 0), mat=P["brass"], segs=16)
    for side in (-1, 1):
        m.box((0.06, 0.62, 0.08), at=(side * 0.43, 1.2, 0), mat=P["brass"], bev=0.01)
        m.cyl(0.05, 0.05, 0.1, at=(side * 0.43, 1.62, 0), mat=P["gilt"], segs=10, roll=math.pi / 2, centered=True)
    m.box((0.92, 0.06, 0.1), at=(0, 1.2, 0), mat=P["brass"], bev=0.01)
    base = m.build("PROP_lens_pedestal", loc=place())

    lens = MB(13)
    # A Fresnel lens: flat back, stepped prism rings, a bull's-eye in the middle.
    prof = [(0.0, -0.045), (0.34, -0.045), (0.34, 0.01)]
    for r in (0.34, 0.27, 0.2, 0.13):
        prof += [(r - 0.055, 0.045), (r - 0.065, 0.005)]
    prof += [(0.05, 0.06), (0.0, 0.07)]
    lens.lathe(prof, mat=LENS, segs=24, pitch=math.pi / 2, at=(0, 0, 0), cap=False)
    lens.ring(0.355, 0.025, mat=P["brass"], pitch=math.pi / 2, segs=24, tube_segs=6)
    lens.build("lens", loc=(0, 1.62, 0), parent=base, props={"part": "lens"}, ao=0.4)


def tide_pole():
    """Origin at world water height 0. Painted bands mark low (white, 0), mid
    (yellow, 0.9) and high (red, 1.8) water, with a tick every 30 cm."""
    m = MB(14)
    m.cyl(0.1, 0.11, 4.8, at=(0, -1.6, 0), mat=P["timber"], segs=8)
    m.cyl(0.115, 0.115, 1.6, at=(0, -1.6, 0), mat=P["tar"], segs=8, bev=0)
    for y, mat in ((0.0, P["paint_white"]), (0.9, P["paint_yellow"]), (1.8, P["paint_red"])):
        m.cyl(0.125, 0.125, 0.16, at=(0, y - 0.08, 0), mat=mat, segs=8, bev=0.01)
    for k in range(-3, 10):
        y = k * 0.3
        if any(abs(y - b) < 0.05 for b in (0.0, 0.9, 1.8)):
            continue
        m.cyl(0.118, 0.118, 0.025, at=(0, y - 0.012, 0), mat=P["tar"], segs=8, bev=0)
    m.cyl(0.13, 0.08, 0.12, at=(0, 3.2, 0), mat=P["iron"], segs=8)
    # Weed and barnacles round the foot.
    rnd = random.Random(14)
    barnacles(m, rnd, (0.0, -0.6, 0.0), (0.1, 0.7, 0.1), 14, size=0.03)
    m.build("PROP_tide_pole", loc=place(), grime=0.0, ground=False)


def buoy_crate():
    """A cargo crate lashed to a barrel float. Its bounding box is a platform you
    stand on at high tide, so it stays 1.7 x 0.9 x 1.7 with the float on +X."""
    m = MB(15)
    slatted_crate(m, (1.7, 0.9, 1.7), wood=P["timber_light"], frame=P["timber"], slats=4)
    prof = [(0.27, -0.6), (0.31, -0.45), (0.32, 0.0), (0.31, 0.45), (0.27, 0.6)]
    m.lathe(prof, at=(0.95, 0.35, 0), mat=P["timber"], segs=12, pitch=math.pi / 2, staves=0.1)
    for z in (-0.4, 0.4):
        m.ring(0.325, 0.016, at=(0.95, 0.35, z), mat=P["iron"], pitch=math.pi / 2, segs=14, tube_segs=4)
    # Lashings over the crate and round the float.
    for z in (-0.45, 0.45):
        m.tube([(-0.86, 0.1, z), (-0.86, 0.905, z), (0.86, 0.905, z), (1.1, 0.68, z), (1.27, 0.35, z)], 0.022, mat=P["rope"], segs=5)
    m.build("PROP_buoy_crate", loc=place(), ground=False, grime=0.3)


def rope_ladder():
    """Two ropes hanging 6 m with wooden rungs whipped on."""
    m = MB(16)
    for x in (-0.3, 0.3):
        pts = [(x + math.sin(k * 0.7) * 0.01, k * 0.4, math.sin(k * 0.5) * 0.02) for k in range(16)]
        m.tube(pts, 0.022, mat=P["rope"], segs=5)
        m.ring(0.05, 0.018, at=(x, 6.0, 0), mat=P["iron"], pitch=math.pi / 2, segs=10, tube_segs=4)
    for i in range(14):
        y = 0.3 + i * 0.4
        m.plank(0.72, 0.07, 0.045, at=(0, y, math.sin(i * 0.5) * 0.02), mat=P["timber"], warp=0.04)
        for x in (-0.3, 0.3):
            m.cyl(0.032, 0.032, 0.08, at=(x, y + 0.02, math.sin(i * 0.5) * 0.02), mat=P["rope"], segs=6, centered=True, bev=0)
    m.build("PROP_rope_ladder", loc=place(), ground=False, grime=0.0)


def beacon_lamp():
    """Saltmere's lantern room: iron sill, a Fresnel beehive lens on a brass
    pedestal, diagonal astragals, a verdigris copper dome, ball vent and rod."""
    m = MB(17)
    m.cyl(0.86, 0.86, 0.24, mat=P["iron"], segs=16)
    m.cyl(0.18, 0.24, 0.3, at=(0, 0.24, 0), mat=P["brass"], segs=12)
    # Beehive lens: stacked glass rings narrowing to top and bottom.
    prof = [(0.0, 0.54)]
    for k in range(9):
        y = 0.56 + k * 0.1
        r = 0.42 - abs(k - 4) * 0.035
        prof += [(r, y), (r - 0.03, y + 0.06)]
    prof += [(0.0, 1.5)]
    m.lathe(prof, mat=P["glass_white"], segs=16, cap=False, jit=0.02)
    m.cyl(0.44, 0.44, 0.04, at=(0, 0.52, 0), mat=P["brass"], segs=16)
    m.cyl(0.44, 0.44, 0.04, at=(0, 1.5, 0), mat=P["brass"], segs=16)
    # Astragals: verticals plus a ring of diagonals.
    for k in range(10):
        a = k / 10 * TAU
        m.box((0.045, 1.55, 0.045), at=(math.cos(a) * 0.78, 0.24, math.sin(a) * 0.78), mat=P["iron"], yaw=-a, bev=0)
    for k in range(10):
        a0, a1 = k / 10 * TAU, (k + 1) / 10 * TAU
        m.tube([(math.cos(a0) * 0.78, 0.6, math.sin(a0) * 0.78), (math.cos(a1) * 0.78, 1.2, math.sin(a1) * 0.78)], 0.016, mat=P["iron"], segs=4)
    m.cyl(0.8, 0.8, 0.07, at=(0, 1.79, 0), mat=P["iron"], segs=20)
    # Dome, vent ball, finial and lightning rod.
    dome = [(0.92, 1.86), (0.9, 1.92), (0.78, 2.08), (0.6, 2.24), (0.36, 2.36), (0.14, 2.42), (0.0, 2.43)]
    m.lathe([(0.0, 1.84)] + dome, mat=P["copper"], segs=20, cap=False, staves=0.04)
    m.uvsphere(0.13, at=(0, 2.52, 0), mat=P["copper"], segs=10, rings=6)
    m.cyl(0.02, 0.01, 0.6, at=(0, 2.6, 0), mat=P["iron"], segs=5)
    m.build("PROP_beacon_lamp", loc=place(), ground=False)


def rowboat():
    """A clinker-built rowboat: painted strakes stepping over each other, red
    below the waterline, raw wood inside, thwarts, oars in brass oarlocks.
    Floats with its origin 0.15 m under the water (BUOY_ float -0.15)."""
    m = MB(18)
    # (z, half beam at the gunwale, depth keel->gunwale, keel y, bilge fullness)
    stations = [
        (-1.62, 0.52, 0.56, -0.04, 0.9),
        (-1.1, 0.65, 0.66, -0.12, 0.86),
        (-0.4, 0.71, 0.69, -0.15, 0.8),
        (0.35, 0.69, 0.7, -0.15, 0.74),
        (0.95, 0.57, 0.74, -0.13, 0.6),
        (1.42, 0.33, 0.8, -0.08, 0.4),
        (1.76, 0.04, 0.86, -0.01, 0.15),
    ]
    WATERLINE = 0.13  # origin floats 0.15 under the surface
    K = 6
    outer = hull_sections(stations, K)
    # Weathered teal topsides, a cream sheer strake, oxblood antifouling below the waterline.
    blue = Paint(P["paint_blue"].mat, 0x2F5D62)
    white = Paint(P["paint_white"].mat, 0xD9D2BE)
    red = Paint(P["paint_red"].mat, 0x6E2A22)
    mid = outer[2]
    n = len(mid) - 1
    strips = []
    for i in range(n):
        y = (mid[i][1] + mid[i + 1][1]) / 2
        top = i < 1 or i >= n - 1
        if top:
            strips.append((white, 1.0))
        elif y < WATERLINE:
            strips.append((red, 0.92 + 0.05 * (i % 2)))
        else:
            strips.append((blue, 1.0 + 0.05 * ((i % 2) * 2 - 1)))
    m.loft(outer, strips=strips)
    inner_st = [(z + (0.04 if z < 0 else -0.05), b - 0.04, d - 0.03, yk + 0.05, f) for z, b, d, yk, f in stations]
    m.loft(hull_sections(inner_st, 3, overlap=0.0), mat=P["timber_light"], flip=True)
    # Transom, keel, stem.
    tr = [(x, y) for x, y, z in hull_sections([stations[0]], 3, overlap=0.0)[0]]
    m.prism([(x, y) for x, y in reversed(tr)], 0.05, at=(0, 0, -1.6), mat=P["timber"], bev=0)
    m.box((0.08, 0.1, 3.25), at=(0, -0.24, 0.06), mat=P["hull_dark"], bev=0.015)
    m.tube([(0, -0.16, 1.5), (0, 0.25, 1.78), (0, 0.9, 1.83)], 0.045, mat=P["hull_dark"], segs=6)
    # Gunwale rails along the sheer.
    for side in (-1, 1):
        rail = [(sec[-1][0] if side > 0 else sec[0][0], sec[-1][1] + 0.01, sec[-1][2]) for sec in outer]
        m.tube(rail, 0.032, mat=P["timber"], segs=5)
    # Thwarts.
    for z, w in ((-0.95, 1.16), (0.0, 1.32), (0.85, 1.06)):
        m.plank(w, 0.24, 0.045, at=(0, 0.27, z), mat=P["timber_light"])
    # Oars across the thwarts, blades out over the stern; brass oarlocks.
    gun = stations[3][3] + stations[3][2]
    for side in (-1, 1):
        m.tube([(side * 0.3, 0.33, 1.0), (side * 0.47, 0.35, -1.55)], 0.03, mat=P["timber_pale"], segs=6)
        m.prism([(-0.075, 0), (0.075, 0), (0.06, 0.45), (-0.06, 0.45)], 0.02, at=(side * 0.48, 0.35, -1.55), mat=P["timber_pale"], pitch=-math.pi / 2, yaw=side * 0.06, bev=0)
        m.cyl(0.035, 0.03, 0.08, at=(side * 0.69, gun, 0.05), mat=P["brass"], segs=6)
    m.build("PROP_rowboat", loc=place(), ground=False, grime=0.0)


def signpost():
    """A weathered post with two arrow boards and a lantern hook."""
    m = MB(19)
    m.box((0.16, 2.35, 0.16), mat=P["timber"], bev=0.02)
    m.cyl(0.13, 0.02, 0.14, at=(0, 2.35, 0), mat=P["hull"], segs=4, yaw=math.pi / 4)
    arrow = [(-0.7, -0.17), (0.55, -0.17), (0.72, 0.0), (0.55, 0.17), (-0.7, 0.17)]
    m.prism(arrow, 0.05, at=(0.42, 1.95, 0.0), mat=P["timber_pale"], roll=0.04, bev=0.01)
    m.prism([(-x, y) for x, y in reversed(arrow)], 0.05, at=(-0.36, 1.48, 0.03), mat=P["timber_light"], roll=-0.06, bev=0.01)
    # Painted letters suggested by dark dashes.
    for k in range(4):
        m.box((0.13, 0.05, 0.008), at=(0.08 + k * 0.17, 1.93, 0.028), mat=P["tar"], bev=0)
        m.box((0.11, 0.05, 0.008), at=(-0.62 + k * 0.15, 1.46, 0.058), mat=P["tar"], bev=0)
    m.tube([(0.0, 2.15, 0.08), (0.0, 2.15, 0.28), (0.0, 2.06, 0.32)], 0.012, mat=P["iron"], segs=4)
    m.rock(0.16, at=(0.15, 0.0, 0.12), mat=P["rock"], seed=19, squash=0.6)
    m.rock(0.12, at=(-0.12, 0.0, -0.13), mat=P["rock_dark"], seed=20, squash=0.6)
    m.build("PROP_signpost", loc=place())


def barrel():
    """An oak barrel: bellied staves, three iron hoops, a planked head and a bung."""
    m = MB(20)
    prof = [(0.3, 0.0), (0.335, 0.12), (0.36, 0.3), (0.365, 0.45), (0.36, 0.6), (0.335, 0.78), (0.3, 0.9)]
    m.lathe(prof, mat=P["timber"], segs=14, staves=0.12, cap=True)
    for y in (0.1, 0.33, 0.57, 0.8):
        r = 0.3 + 0.065 * math.sin(math.pi * y / 0.9) + 0.012
        m.ring(r, 0.016, at=(0, y, 0), mat=P["iron"], segs=16, tube_segs=4)
    for k in range(4):
        m.box((0.56, 0.01, 0.006), at=(0, 0.9, -0.21 + k * 0.14), mat=P["tar"], bev=0)
    m.cyl(0.035, 0.035, 0.02, at=(0.364, 0.45, 0), mat=P["hull_dark"], segs=8, roll=math.pi / 2, centered=True, bev=0)
    m.build("PROP_barrel", loc=place())


def hull_ribs():
    """A small boat's skeleton half sunk in sand: keel, curved ribs (some
    snapped), a couple of strakes left at the turn of the bilge, weed."""
    m = MB(21)
    rnd = random.Random(21)
    m.sphere(1.6, at=(0, -0.25, 0), mat=P["sand"], scale=(1.15, 0.18, 2.4), subdiv=2)
    m.box((0.3, 0.32, 6.2), at=(0, -0.12, 0), mat=P["hull_dark"], pitch=0.02)
    for i in range(7):
        z = -2.7 + i * 0.9
        half = 1.35 - abs(i - 3) * 0.16
        height = 1.9 - abs(i - 3) * 0.18
        for side in (-1, 1):
            # A quarter ellipse from the keel out along the bilge and up the
            # side; most ribs have snapped somewhere along the way.
            intact = (i * 2 + side) % 5 == 0
            a_max = math.pi / 2 if intact else 0.55 + rnd.random() * 0.75
            pts = []
            for k in range(7):
                a = k / 6 * a_max
                pts.append((side * (0.15 + half * math.sin(a)), -0.12 + height * (1 - math.cos(a)), z + (rnd.random() - 0.5) * 0.03))
            radii = [0.1 - 0.035 * (k / 6) for k in range(7)]
            m.tube(pts, radii, mat=P["hull_dark"] if i % 2 else P["hull"], segs=5)
            if not intact:
                x, y, zz = pts[-1]
                m.prism([(0, 0), (0.07, 0.0), (0.02, 0.16)], 0.08, at=(x, y, zz), mat=P["timber_pale"], roll=-side * a_max, bev=0)
    for side in (-1, 1):
        m.plank(3.0, 0.22, 0.06, at=(side * 1.05, 0.28, -0.5), mat=P["hull"], yaw=math.pi / 2, roll=side * 0.5, warp=0.08)
    for i in range(4):
        seaweed_clump(m, rnd, ((rnd.random() - 0.5) * 2, -0.05, -2.5 + i * 1.6), count=3, length=0.6)
    m.build("PROP_hull_ribs", loc=place(), grime=0.35)


def lantern_post():
    """An iron lamp post: moulded foot, shaft, a scrolled bracket and a hanging
    lantern. The game adds a warm light at (0.5, 1.9, 0), the lantern's glass."""
    m = MB(22)
    prof = [(0.16, 0.0), (0.16, 0.06), (0.11, 0.12), (0.075, 0.2), (0.06, 0.3), (0.05, 2.3), (0.065, 2.34), (0.065, 2.4), (0.0, 2.42)]
    m.lathe(prof, mat=P["iron"], segs=8)
    m.tube([(0.0, 2.3, 0.0), (0.3, 2.3, 0.0), (0.56, 2.28, 0.0)], 0.025, mat=P["iron"], segs=5)
    m.tube([(0.04, 1.95, 0.0), (0.18, 2.12, 0.0), (0.33, 2.27, 0.0)], 0.018, mat=P["iron"], segs=4)
    m.tube([(0.5, 2.28, 0), (0.5, 2.2, 0)], 0.008, mat=P["iron"], segs=4)
    lantern(m, (0.5, 1.92, 0.0), 1.0)
    m.build("PROP_lantern_post", loc=place(), props={"light": "warm"})


def dune_grass():
    """A marram tuft: stiff blades fanning out of a sandy base, green to straw."""
    m = MB(23)
    rnd = random.Random(11)
    colours = [Paint(P["grass"].mat, c) for c in (0x8C9461, 0x9AA06A, 0xA89F6A, 0x7C8655, 0xB5A877)]
    m.sphere(0.22, at=(0, -0.08, 0), mat=P["sand"], scale=(1, 0.4, 1), subdiv=1)
    for i in range(26):
        a = rnd.random() * TAU
        r = rnd.random() * 0.16
        h = 0.45 + rnd.random() * 0.5
        lean = 0.15 + rnd.random() * 0.45
        x0, z0 = math.cos(a) * r, math.sin(a) * r
        pts = []
        for k in range(4):
            t = k / 3
            out = lean * t * t * h
            pts.append((x0 + math.cos(a) * out, t * h * (1 - 0.15 * t * lean), z0 + math.sin(a) * out))
        m.tube(pts, [0.012, 0.009, 0.006, 0.001], mat=colours[i % len(colours)], segs=3, cap=False)
    m.build("PROP_dune_grass", loc=place(), ao=0.5, grime=0.3)


# ------------------------------------------------------------- dressing


def bollard():
    """A cast-iron mooring bollard."""
    m = MB(30)
    prof = [(0.2, 0.0), (0.2, 0.06), (0.15, 0.1), (0.13, 0.4), (0.17, 0.46), (0.19, 0.52), (0.16, 0.58), (0.0, 0.6)]
    m.lathe(prof, mat=P["iron"], segs=12)
    m.box((0.5, 0.05, 0.5), mat=P["iron_light"], bev=0.01)
    m.build("PROP_bollard", loc=place())


def rope_coil():
    """A flat coil of rope with its end trailing."""
    m = MB(31)
    pts = []
    for k in range(80):
        t = k / 79
        a = t * 4.2 * TAU
        r = 0.1 + t * 0.26
        pts.append((math.cos(a) * r, 0.035 + 0.035 * (k % 2) * 0 + t * 0.03, math.sin(a) * r))
    pts.append((0.5, 0.03, 0.2))
    pts.append((0.75, 0.03, 0.35))
    m.tube(pts, 0.032, mat=P["rope"], segs=5)
    m.build("PROP_rope_coil", loc=place(), ao=0.6)


def anchor():
    """A rusted stockless anchor lying flat: shank, crown, curved arms with
    spade flukes, and the ring."""
    m = MB(32)
    m.box((0.14, 0.12, 1.75), at=(0, 0.0, 0.08), mat=P["iron"], bev=0.02)
    for z in (-0.3, 0.35):
        m.box((0.16, 0.135, 0.22), at=(0, -0.005, z), mat=P["rust"], bev=0.01, jit=0.12)
    arm = []
    for k in range(9):
        a = -math.pi * 0.42 + k / 8 * math.pi * 0.84
        arm.append((math.sin(a) * 0.72, 0.07, -0.78 + (1 - math.cos(a)) * 0.62))
    m.tube(arm, [0.06, 0.07, 0.075, 0.08, 0.085, 0.08, 0.075, 0.07, 0.06], mat=P["rust"], segs=6)
    m.sphere(0.14, at=(0, 0.06, -0.8), mat=P["iron"], scale=(1.25, 0.6, 1.0), subdiv=1)
    for side in (-1, 1):
        x, y, z = arm[0] if side < 0 else arm[-1]
        # Spade fluke: a pointed blade pointing back up the arm.
        m.prism([(0, -0.12), (0.2, 0.06), (0.05, 0.3), (0, 0.36), (-0.05, 0.3), (-0.2, 0.06)], 0.05, at=(x, 0.05, z - 0.05), mat=P["rust_light"], pitch=-math.pi / 2, yaw=-side * 0.75, bev=0.01)
    m.ring(0.15, 0.032, at=(0, 0.04, 1.05), mat=P["rust"], segs=14, tube_segs=5)
    m.build("PROP_anchor", loc=place(), grime=0.2)


def plank_pile():
    """Salvaged boards stacked on two bearers."""
    m = MB(33)
    for z in (-0.9, 0.9):
        m.box((0.9, 0.1, 0.12), at=(0, 0, z), mat=P["hull_dark"])
    rnd = random.Random(33)
    for k in range(9):
        layer = k // 3
        x = -0.3 + (k % 3) * 0.3 + (rnd.random() - 0.5) * 0.04
        m.plank(2.2 + rnd.random() * 0.3, 0.26, 0.05, at=(x, 0.1 + layer * 0.055, (rnd.random() - 0.5) * 0.2), mat=rnd.choice((P["timber"], P["timber_light"], P["driftwood"])), yaw=math.pi / 2 + (rnd.random() - 0.5) * 0.08, warp=0.04)
    m.build("PROP_plank_pile", loc=place())


def lantern_hanging():
    """A lantern on a short chain, for hanging from a beam (origin at the hook)."""
    m = MB(34)
    chain(m, (0, 0, 0), (0, -0.45, 0), link=0.07, thick=0.01, mat=P["iron"])
    lantern(m, (0, -0.72, 0), 1.0)
    m.build("PROP_lantern_hanging", loc=place(), ground=False, props={"light": "warm", "light_offset": [0, -0.72, 0]})


def seaweed():
    """A drift line of wrack left on the sand by the last tide."""
    m = MB(35)
    rnd = random.Random(35)
    for i in range(16):
        x = -1.6 + i * 0.2 + (rnd.random() - 0.5) * 0.15
        a = (rnd.random() - 0.5) * 2.6
        L = 0.3 + rnd.random() * 0.4
        pts = [(x + math.sin(a) * L * t + math.sin(t * 9 + i) * 0.03, 0.015 + 0.01 * math.sin(t * 7), math.cos(a) * L * (t - 0.5)) for t in (0, 0.33, 0.66, 1.0)]
        ribbon(m, pts, [0.04, 0.07, 0.06, 0.02], KELP[i % len(KELP)])
    for i in range(5):
        m.sphere(0.03, at=(-1.4 + i * 0.7, 0.02, (rnd.random() - 0.5) * 0.3), mat=KELP[2], scale=(1, 0.7, 1.3), subdiv=1)
    m.build("PROP_seaweed", loc=place(), ao=0.3, grime=0.0)


def lobster_pot():
    """A creel: slatted base, three bent hoops, netting lines and a rope."""
    m = MB(36)
    for k in range(4):
        m.plank(0.75, 0.09, 0.025, at=(0, 0, -0.18 + k * 0.12), mat=P["driftwood"])
    for z in (-0.25, 0.0, 0.25):
        arc = [(math.cos(a) * 0.33, math.sin(a) * 0.36, z) for a in [k / 10 * math.pi for k in range(11)]]
        m.tube(arc, 0.014, mat=P["timber"], segs=4)
    for k in range(1, 10):
        a = k / 10 * math.pi
        m.tube([(math.cos(a) * 0.33, math.sin(a) * 0.36, -0.27), (math.cos(a) * 0.33, math.sin(a) * 0.36, 0.27)], 0.004, mat=P["rope"], segs=3)
    m.tube([(0.36, 0.05, 0.2), (0.5, 0.03, 0.45), (0.7, 0.03, 0.5)], 0.012, mat=P["rope"], segs=4)
    m.build("PROP_lobster_pot", loc=place(), ao=0.5)


def cask_small():
    """A small keg lying on its side, chocked with a stone."""
    m = MB(37)
    prof = [(0.17, -0.25), (0.2, -0.15), (0.21, 0.0), (0.2, 0.15), (0.17, 0.25)]
    m.lathe(prof, at=(0, 0.2, 0), mat=P["timber_light"], segs=12, staves=0.12, roll=math.pi / 2)
    for x in (-0.17, 0.17):
        m.ring(0.2, 0.012, at=(x, 0.2, 0), mat=P["iron"], roll=math.pi / 2, segs=12, tube_segs=4)
    m.rock(0.08, at=(0.05, 0.0, 0.2), mat=P["rock"], seed=37, squash=0.6, cuts=2, subdiv=1)
    m.build("PROP_cask_small", loc=place())


def gull():
    """Herring gulls. PROP_gull stands (feet at the origin, facing +Z). In flight
    the game assembles PROP_gull_body (origin between the shoulders) and the two
    wings, PROP_gull_wing_l along +X and PROP_gull_wing_r along -X, each with its
    origin at the shoulder so it can flap about the body's long axis."""
    F = P["cloth"].mat
    WHITE, GREY, BLACK = Paint(F, 0xF0EEE6), Paint(F, 0x98A2A9), Paint(F, 0x222428)
    BILL, LEGS, EYE, SPOT = Paint(F, 0xE3B53C), Paint(F, 0xD49A88), Paint(F, 0x111214), Paint(F, 0xC0392B)

    def head(m, at):
        x, y, z = at
        m.sphere(0.062, at=(x, y, z), mat=WHITE, scale=(0.9, 0.95, 1.1), subdiv=2, jit=0.02)
        m.cyl(0.016, 0.006, 0.075, at=(x, y - 0.008, z + 0.085), mat=BILL, segs=6, pitch=math.pi / 2, centered=True, jit=0.02)
        m.sphere(0.008, at=(x, y - 0.019, z + 0.1), mat=SPOT, subdiv=1, jit=0.0)
        for sx in (-1, 1):
            m.sphere(0.009, at=(x + sx * 0.047, y + 0.014, z + 0.03), mat=EYE, subdiv=1, jit=0.0)

    # Standing: pink legs and webbed feet, chest up, folded grey wings crossing
    # over the tail in black, white-spotted tips.
    m = MB(90)
    for sx in (-1, 1):
        m.tube([(sx * 0.035, 0.0, 0.015), (sx * 0.037, 0.07, 0.005), (sx * 0.04, 0.14, -0.005)], 0.009, mat=LEGS, segs=4)
        m.box((0.05, 0.008, 0.065), at=(sx * 0.035, 0.0, 0.035), mat=LEGS, bev=0)
    m.sphere(0.1, at=(0, 0.2, 0), mat=WHITE, scale=(0.9, 0.85, 1.55), subdiv=2, pitch=0.25, jit=0.02)
    m.sphere(0.058, at=(0, 0.29, 0.1), mat=WHITE, scale=(1.0, 1.4, 1.0), subdiv=1, jit=0.02)
    head(m, (0, 0.36, 0.14))
    for sx in (-1, 1):
        m.sphere(0.1, at=(sx * 0.058, 0.23, -0.05), mat=GREY, scale=(0.48, 0.42, 1.75), subdiv=2, roll=sx * 0.22, pitch=0.12, jit=0.03)
        m.sphere(0.06, at=(sx * 0.018, 0.19, -0.23), mat=BLACK, scale=(0.55, 0.3, 1.6), subdiv=1, pitch=0.15, jit=0.02)
        m.sphere(0.012, at=(sx * 0.03, 0.188, -0.29), mat=WHITE, subdiv=1, jit=0.0)
    m.sphere(0.05, at=(0, 0.17, -0.16), mat=WHITE, scale=(0.9, 0.45, 1.3), subdiv=1, jit=0.02)
    m.build("PROP_gull", loc=place(), ao=0.3, grime=0.0)

    # In flight: a long white body, head out front, the tail a fan.
    m = MB(91)
    m.sphere(0.095, at=(0, 0, -0.02), mat=WHITE, scale=(0.85, 0.8, 1.75), subdiv=2, jit=0.02)
    m.sphere(0.05, at=(0, 0.02, 0.14), mat=WHITE, scale=(1.0, 1.0, 1.3), subdiv=1, jit=0.02)
    head(m, (0, 0.035, 0.2))
    m.sphere(0.06, at=(0, 0.0, -0.21), mat=WHITE, scale=(1.05, 0.22, 1.4), subdiv=1, jit=0.02)
    m.sphere(0.02, at=(0, -0.06, -0.08), mat=LEGS, scale=(1.4, 0.6, 1.8), subdiv=1, jit=0.0)
    m.build("PROP_gull_body", loc=place(), ground=False, ao=0.25, grime=0.0)

    # Wings: (out from the shoulder, leading edge z, trailing edge z, thickness,
    # lift). The arm rises and the hand droops, the gull's M when it glides.
    span = [
        (0.0, 0.07, -0.12, 0.035, 0.0),
        (0.16, 0.08, -0.13, 0.028, 0.025),
        (0.31, 0.075, -0.125, 0.022, 0.035),
        (0.45, 0.035, -0.145, 0.016, 0.02),
        (0.57, -0.03, -0.15, 0.01, -0.005),
        (0.66, -0.1, -0.13, 0.004, -0.02),
    ]
    for sign, name, seed in ((1, "PROP_gull_wing_l", 92), (-1, "PROP_gull_wing_r", 93)):
        sec = []
        for x, zl, zt, t, y in span:
            zm = zl * 0.65 + zt * 0.35
            sec.append([(sign * x, y, zl), (sign * x, y + t / 2, zm), (sign * x, y, zt), (sign * x, y - t / 2, zm)])
        m = MB(seed)
        # Grey above, white beneath; the hand black on both faces.
        m.loft(sec[:4], closed=True, cap=True, flip=sign < 0, strips=[(GREY, 1.0), (GREY, 1.0), (WHITE, 1.0), (WHITE, 1.0)])
        m.loft(sec[3:], closed=True, cap=True, flip=sign < 0, strips=[(BLACK, 1.0)])
        tx, ty, tz = sec[4][1]
        m.sphere(0.016, at=(tx, ty + 0.002, tz - 0.012), mat=WHITE, scale=(1.3, 0.3, 1.0), subdiv=1, jit=0.0)
        m.build(name, loc=place(), ground=False, ao=0.2, grime=0.0)


for build in (driftwood, scrap_pile, kelp_bed, glass_bed, reinforced_wreckage, supply_crate, sealed_cache, strongbox, lens_pedestal,
              tide_pole, buoy_crate, rope_ladder, beacon_lamp, rowboat, signpost, barrel, hull_ribs, lantern_post, dune_grass,
              bollard, rope_coil, anchor, plank_pile, lantern_hanging, seaweed, lobster_pot, cask_small, gull):
    build()

kit.save_and_export("art/blender/props/props.blend", "public/assets/models/props.glb")
