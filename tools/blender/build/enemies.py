"""Builds art/blender/enemies/enemies.blend and public/assets/models/enemies.glb.

Each enemy is an empty named MODEL_<enemy id> with named child parts. The game
animates the parts procedurally (claws, legs, jaw, arms) and drives the
emission of every GLOW_* material for attack telegraphs, so keep those names,
the pivots (each part's origin) and the overall sizes: hit spheres in
src/enemies/*.ts assume them. Feet (or the waterline for sea creatures) sit at
the origin; front is game +Z.

Sea-green glow is the danger language (docs/ART_PIPELINE.md): it marks what
hurts you and where to aim. Bodies stay dark and wet so the glow reads.

    blender -b --factory-startup --python tools/blender/build/enemies.py
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
SEA_GREEN = 0x3DFFB0
TAU = math.tau
SHELL = kit.surface("carapace", rough=0.4)
SKIN = kit.surface("skin_wet", rough=0.5)
HIDE = kit.surface("hide", rough=0.35)


def glow(name):
    return kit.material(f"GLOW_{name}", 0x1B5E48, rough=0.4, emit=SEA_GREEN, strength=1.0)


def barnacles(m, rnd, center, spread, count, size=0.05):
    cx, cy, cz = center
    for _ in range(count):
        r = size * (0.6 + rnd.random() * 0.7)
        prof = [(r, 0), (r * 0.75, r * 0.7), (r * 0.35, r * 0.95), (r * 0.25, r * 0.7), (0, r * 0.6)]
        m.lathe(prof, at=(cx + (rnd.random() - 0.5) * 2 * spread[0], cy + (rnd.random() - 0.5) * 2 * spread[1], cz + (rnd.random() - 0.5) * 2 * spread[2]), mat=P["barnacle"], segs=6, jit=0.1)


def ribbon(m, pts, widths, mat, normal=(0, 0, 1)):
    nx, ny, nz = normal
    secs = []
    for i, (x, y, z) in enumerate(pts):
        j, k = min(i + 1, len(pts) - 1), max(i - 1, 0)
        tx, ty, tz = pts[j][0] - pts[k][0], pts[j][1] - pts[k][1], pts[j][2] - pts[k][2]
        sx, sy, sz = ty * nz - tz * ny, tz * nx - tx * nz, tx * ny - ty * nx
        sl = math.sqrt(sx * sx + sy * sy + sz * sz) or 1.0
        w = widths[i] / 2 / sl
        secs.append([(x - sx * w, y - sy * w, z - sz * w), (x + sx * w, y + sy * w, z + sz * w)])
    m.loft(secs, mat=mat, jit=0.08)


def hanging_weed(m, rnd, at, length, count=3, mats=None):
    """Kelp strands hanging from a point, swaying a little sideways."""
    x0, y0, z0 = at
    mats = mats or (P["kelp"], P["kelp_dark"])
    for i in range(count):
        dx, dz = (rnd.random() - 0.5) * 0.2, (rnd.random() - 0.5) * 0.2
        L = length * (0.6 + rnd.random() * 0.6)
        pts = [(x0 + dx + math.sin(t * 5 + i) * 0.06, y0 - L * t, z0 + dz + math.cos(t * 4 + i) * 0.04) for t in (0, 0.25, 0.5, 0.75, 1.0)]
        ribbon(m, pts, [0.06, 0.09, 0.08, 0.06, 0.02], mats[i % len(mats)], normal=(0, 0, 1) if i % 2 else (1, 0, 0))


# ------------------------------------------------------------- brine crab


def brine_crab():
    root = kit.empty("MODEL_brine_crab", (0, 0, 0))
    shell = Paint(SHELL, 0x8A3B2A)
    shell_dark = Paint(SHELL, 0x5E261C)
    belly = Paint(SHELL, 0xC79A6B)
    tip = Paint(SHELL, 0x2E1712)
    g = glow("crab")
    rnd = random.Random(4)

    body = MB(40)
    # Carapace: broad and low, wider than long, a ridge down the middle.
    body.uvsphere(0.55, at=(0, 0.56, 0), mat=shell, scale=(1.38, 0.42, 1.0), segs=18, rings=9)
    body.uvsphere(0.32, at=(0, 0.66, -0.05), mat=shell_dark, scale=(1.1, 0.42, 1.2), segs=12, rings=6)
    body.uvsphere(0.5, at=(0, 0.44, 0.02), mat=belly, scale=(1.2, 0.3, 0.9), segs=14, rings=6)
    # Spines along the front-lateral margin, and teeth between the eyes.
    for side in (-1, 1):
        for k in range(5):
            a = 0.25 + k * 0.22
            x, z = side * math.sin(a) * 0.74, math.cos(a) * 0.5
            body.cyl(0.05, 0.0, 0.16, at=(x, 0.55, z), mat=shell_dark, segs=5, roll=-side * (math.pi / 2 - 0.25), yaw=side * (a - 0.2), centered=True)
    for k in range(4):
        body.cyl(0.03, 0.0, 0.09, at=(-0.09 + k * 0.06, 0.58, 0.56), mat=shell_dark, segs=4, pitch=math.pi / 2 - 0.3, centered=True)
    # Eyes on stalks, glossy black.
    for side in (-1, 1):
        body.tube([(side * 0.13, 0.62, 0.44), (side * 0.15, 0.78, 0.5)], 0.028, mat=shell, segs=5)
        body.uvsphere(0.055, at=(side * 0.15, 0.82, 0.51), mat=P["tar"], segs=8, rings=5)
    # Mouthparts.
    body.box((0.22, 0.12, 0.06), at=(0, 0.36, 0.5), mat=shell_dark)
    # Bioluminescent spots: dark until it winds up, then they flare.
    for i in range(9):
        a = rnd.random() * TAU
        r = 0.2 + rnd.random() * 0.25
        body.uvsphere(0.04, at=(math.cos(a) * r * 1.3, 0.73 - r * 0.15, math.sin(a) * r * 0.9), mat=g, segs=6, rings=4)
    barnacles(body, rnd, (0.25, 0.72, -0.2), (0.15, 0.02, 0.15), 5, size=0.035)
    body.build("body", parent=root, smooth=38, grime=0.0, ground=False)

    for side, name in ((-1, "claw_l"), (1, "claw_r")):
        c = MB(41 + side)
        # Built round the shoulder pivot; the arm reaches forward and out.
        c.tube([(0, 0, 0), (side * 0.1, 0.04, 0.16), (side * 0.2, 0.05, 0.32)], [0.1, 0.095, 0.1], mat=shell, segs=7)
        c.uvsphere(0.13, at=(side * 0.2, 0.05, 0.33), mat=shell_dark, segs=8, rings=5)
        # The hand: a swollen, knobbly propodus.
        c.uvsphere(0.25, at=(side * 0.29, 0.06, 0.6), mat=shell, scale=(0.9, 0.78, 1.35), segs=12, rings=7)
        for k in range(4):
            c.cyl(0.04, 0.0, 0.08, at=(side * (0.4 + k * 0.01), 0.22, 0.45 + k * 0.1), mat=shell_dark, segs=4, centered=True)
        # Fixed finger and the movable one above it, inner edges glowing.
        c.tube([(side * 0.33, -0.02, 0.86), (side * 0.35, -0.05, 1.02), (side * 0.33, 0.0, 1.17)], [0.085, 0.06, 0.014], mat=shell, segs=6)
        c.tube([(side * 0.21, 0.12, 0.82), (side * 0.23, 0.17, 1.0), (side * 0.29, 0.08, 1.14)], [0.075, 0.055, 0.014], mat=shell, segs=6)
        c.tube([(side * 0.34, 0.0, 1.15), (side * 0.33, 0.0, 1.2)], [0.014, 0.004], mat=tip, segs=4)
        for k in range(3):
            c.cyl(0.022, 0.0, 0.06, at=(side * 0.3, 0.03, 0.9 + k * 0.08), mat=g, segs=4, centered=True)
            c.cyl(0.02, 0.0, 0.055, at=(side * 0.25, 0.1, 0.88 + k * 0.08), mat=g, segs=4, pitch=math.pi, centered=True)
        c.box((0.05, 0.035, 0.26), at=(side * 0.27, 0.05, 0.88), mat=g, bev=0)
        c.build(name, loc=(side * 0.55, 0.52, 0.38), parent=root, smooth=40, ground=False, grime=0.0)

    for side, s in ((-1, "l"), (1, "r")):
        for i in range(3):
            leg = MB(50 + i + (side + 1) * 3)
            # Coxa at the pivot, merus up and out to the knee, dactyl down to a point.
            dz = (0.22, 0.0, -0.28)[i]
            pts = [(0, 0, 0), (side * 0.2, 0.12, dz * 0.25), (side * 0.42, 0.24, dz * 0.55), (side * 0.64, 0.04, dz * 0.85), (side * 0.76, -0.44, dz)]
            leg.tube(pts, [0.085, 0.085, 0.07, 0.045, 0.01], mat=shell, segs=7)
            leg.uvsphere(0.075, at=pts[2], mat=shell_dark, segs=8, rings=5)
            leg.tube([pts[3], ((pts[3][0] + pts[4][0]) / 2, (pts[3][1] + pts[4][1]) / 2, (pts[3][2] + pts[4][2]) / 2)], [0.036, 0.025], mat=shell_dark, segs=5)
            leg.build(f"leg_{s}{i}", loc=(side * 0.58, 0.45, 0.16 - i * 0.3), parent=root, smooth=40, ground=False, grime=0.0)
    return root


# -------------------------------------------------------- drowned spitter


def drowned_spitter():
    """A drowned sailor grown into the kelp: a lump of rags and weed for legs,
    a bloated sea-green throat sac, a hanging jaw and long arms."""
    root = kit.empty("MODEL_drowned_spitter", (4, 0, 0))
    skin = Paint(SKIN, 0x4F5E57)
    skin_dark = Paint(SKIN, 0x37443F)
    coat = Paint(P["cloth"].mat, 0x26303A)
    rag = Paint(P["cloth"].mat, 0x3B3A33)
    g = glow("spitter")
    rnd = random.Random(6)

    body = MB(60)
    # Rooted base: a mound of rags and weed.
    body.rock(0.55, at=(0, 0.0, 0), mat=rag, seed=61, squash=0.85, cuts=3, jitter=0.35, scale=(1.0, 1.0, 0.9))
    body.lathe([(0.48, 0.05), (0.5, 0.3), (0.44, 0.6), (0.4, 0.75)], mat=rag, segs=10, cap=False)
    # Torso under a tattered sailor's coat, narrowing to a scrawny neck so the
    # throat sac (a separate part at z 0.27) bulges out in front.
    body.lathe([(0.4, 0.7), (0.44, 0.95), (0.42, 1.15), (0.33, 1.34), (0.22, 1.5), (0.12, 1.66), (0.0, 1.7)], at=(0, 0, -0.1), mat=skin, segs=12)
    body.lathe([(0.47, 0.62), (0.5, 0.85), (0.48, 1.08), (0.41, 1.26), (0.3, 1.4)], at=(0, 0, -0.1), mat=coat, segs=12, cap=False)
    # Hunched shoulders.
    for side in (-1, 1):
        body.uvsphere(0.2, at=(side * 0.36, 1.48, -0.12), mat=coat, scale=(1.2, 0.8, 1.0), segs=10, rings=6)
    # Coat tails and rags hanging in strips.
    for k in range(9):
        a = k / 9 * TAU + 0.2
        x, z = math.sin(a) * 0.5, math.cos(a) * 0.5 - 0.06
        L = 0.45 + rnd.random() * 0.35
        ribbon(body, [(x, 0.75, z), (x * 1.05, 0.75 - L * 0.5, z * 1.05), (x * 1.08, 0.75 - L, z * 1.1)], [0.16, 0.13, 0.05], coat if k % 2 else rag, normal=(math.sin(a), 0, math.cos(a)))
    # Brass buttons gone green, a collar.
    for k in range(3):
        body.uvsphere(0.03, at=(0.0, 1.0 + k * 0.14, 0.43 + k * 0.02), mat=P["copper"], segs=6, rings=4)
    body.ring(0.3, 0.06, at=(0, 1.5, 0.08), mat=coat, segs=12, tube_segs=5, pitch=0.25)
    # Weed hanging from the shoulders, barnacles crusting them.
    for side in (-1, 1):
        hanging_weed(body, rnd, (side * 0.42, 1.6, 0.05), 1.0, count=4)
        hanging_weed(body, rnd, (side * 0.3, 1.62, 0.25), 0.7, count=2)
        barnacles(body, rnd, (side * 0.38, 1.62, -0.05), (0.12, 0.04, 0.12), 7, size=0.04)
    hanging_weed(body, rnd, (0.0, 1.55, -0.3), 1.2, count=5)
    # Kelp spilling round the base, rooting it to the spot.
    for k in range(10):
        a = k / 10 * TAU
        r0 = 0.45
        pts = [(math.cos(a) * r0, 0.35, math.sin(a) * r0), (math.cos(a) * 0.7, 0.12, math.sin(a) * 0.7), (math.cos(a + 0.3) * 1.0, 0.02, math.sin(a + 0.3) * 1.0)]
        ribbon(body, pts, [0.14, 0.12, 0.04], (P["kelp"], P["kelp_dark"])[k % 2], normal=(0, 1, 0))
    body.build("body", parent=root, smooth=35, grime=0.25)

    throat = MB(61)
    throat.uvsphere(0.2, mat=g, scale=(1.0, 1.15, 0.85), segs=12, rings=8)
    throat.build("throat", loc=(0, 1.42, 0.27), parent=root, smooth=60, ao=0.0, ground=False, grime=0.0)

    head = MB(62)
    # Skull-like head, sunken sockets, glowing eyes, the jaw hanging open.
    head.uvsphere(0.25, at=(0, 0.2, 0.04), mat=skin, scale=(0.92, 1.05, 1.0), segs=12, rings=8)
    head.box((0.3, 0.09, 0.2), at=(0, -0.05, 0.14), mat=skin_dark, pitch=0.35, centered=True)
    head.box((0.24, 0.07, 0.04), at=(0, 0.04, 0.24), mat=P["tar"], centered=True, bev=0)
    for k in range(5):
        head.cyl(0.012, 0.0, 0.04, at=(-0.08 + k * 0.04, 0.07, 0.25), mat=P["bone"], segs=4, pitch=math.pi, centered=True)
    for side in (-1, 1):
        head.uvsphere(0.065, at=(side * 0.1, 0.25, 0.2), mat=P["tar"], segs=8, rings=5)
        head.uvsphere(0.04, at=(side * 0.1, 0.25, 0.235), mat=g, segs=8, rings=5)
    # A sodden knit cap and kelp hair.
    head.lathe([(0.24, 0.32), (0.25, 0.4), (0.22, 0.48), (0.12, 0.54), (0.0, 0.55)], at=(0, 0, 0.0), mat=Paint(P["cloth"].mat, 0x5A2A26), segs=12, pitch=-0.15)
    head.ring(0.245, 0.035, at=(0, 0.34, 0.0), mat=Paint(P["cloth"].mat, 0x4A2220), pitch=-0.15, segs=14, tube_segs=4)
    hanging_weed(head, rnd, (0.0, 0.38, -0.18), 0.55, count=4)
    head.build("head", loc=(0, 1.72, 0.05), parent=root, smooth=35, ground=False, grime=0.0)

    for side, name in ((-1, "arm_l"), (1, "arm_r")):
        a = MB(63 + side)
        # Upper arm, forearm, a long-fingered hand hanging by the knees.
        a.tube([(0, 0, 0), (side * 0.06, -0.45, 0.04), (side * 0.04, -0.9, 0.1)], [0.1, 0.085, 0.075], mat=coat, segs=7)
        a.tube([(side * 0.04, -0.88, 0.1), (side * 0.03, -1.1, 0.14)], [0.065, 0.055], mat=skin, segs=6)
        for k in range(4):
            fx = side * (0.0 + k * 0.025)
            a.tube([(fx + side * 0.02, -1.1, 0.14), (fx + side * 0.02, -1.22, 0.16 + k * 0.012), (fx + side * 0.015, -1.3, 0.13 + k * 0.01)], [0.018, 0.014, 0.006], mat=skin_dark, segs=4)
        hanging_weed(a, rnd, (side * 0.06, -0.3, 0.0), 0.6, count=2)
        a.build(name, loc=(side * 0.5, 1.6, 0), parent=root, smooth=35, ground=False, grime=0.0)
    return root


# ------------------------------------------------------------ lantern wisp


def lantern_wisp():
    """A drowned ship's lantern possessed by the Gloom: verdigris cage, a
    sea-green flame for a core, cracked panes, glowing weed trailing below."""
    root = kit.empty("MODEL_lantern_wisp", (8, 0, 0))
    g = glow("wisp")

    core = MB(70)
    core.uvsphere(0.17, mat=g, segs=12, rings=8)
    core.lathe([(0.0, 0.1), (0.1, 0.16), (0.08, 0.26), (0.03, 0.36), (0.0, 0.4)], mat=g, segs=8)
    core.build("core", parent=root, smooth=60, ao=0.0, ground=False, grime=0.0)

    cage = MB(71)
    cu = P["copper"]
    cage.lathe([(0.22, -0.42), (0.3, -0.38), (0.33, -0.33), (0.0, -0.33)], mat=cu, segs=12)
    cage.ring(0.31, 0.025, at=(0, -0.3, 0), mat=cu, segs=16, tube_segs=4)
    cage.ring(0.3, 0.025, at=(0, 0.3, 0), mat=cu, segs=16, tube_segs=4)
    for k in range(6):
        a = k / 6 * TAU
        pts = [(math.cos(a) * r, y, math.sin(a) * r) for r, y in ((0.31, -0.32), (0.34, -0.1), (0.34, 0.1), (0.3, 0.32))]
        cage.tube(pts, 0.022, mat=cu, segs=4)
    # Two cracked panes left in the frame.
    for k in (0, 3):
        a = (k + 0.5) / 6 * TAU
        cage.box((0.28, 0.4, 0.012), at=(math.cos(a) * 0.32, -0.2, math.sin(a) * 0.32), mat=P["glass_green"], yaw=-a + math.pi / 2, jit=0.1)
    cage.lathe([(0.32, 0.32), (0.26, 0.4), (0.12, 0.5), (0.05, 0.56), (0.0, 0.57)], mat=cu, segs=12)
    cage.ring(0.07, 0.016, at=(0, 0.66, 0), mat=P["iron"], pitch=math.pi / 2, segs=12, tube_segs=4)
    cage.build("cage", parent=root, smooth=30, ground=False, grime=0.0)

    for i in range(4):
        a = i / 4 * TAU + 0.4
        t = MB(72 + i)
        pts = [(0, 0, 0), (math.cos(a) * 0.08, -0.25, math.sin(a) * 0.08), (math.cos(a + 0.6) * 0.06, -0.5, math.sin(a + 0.6) * 0.1), (math.cos(a + 1.2) * 0.1, -0.8, math.sin(a + 1.2) * 0.06)]
        t.tube(pts, [0.045, 0.035, 0.022, 0.004], mat=g, segs=5)
        t.build(f"tendril_{i}", loc=(math.cos(a) * 0.18, -0.38, math.sin(a) * 0.18), parent=root, smooth=60, ao=0.0, ground=False, grime=0.0)
    return root


# ------------------------------------------------------------- tide lurker


def tide_lurker():
    """An angler-headed eel that rises from deep water: slick dark hide, a
    pale belly, a lure on a stalk, frilled fins and a lot of teeth."""
    root = kit.empty("MODEL_tide_lurker", (12, 0, 0))
    hide = Paint(HIDE, 0x1F2B33)
    hide2 = Paint(HIDE, 0x2C3B44)
    belly = Paint(HIDE, 0x55635D)
    gum = Paint(SKIN, 0x5A2E33)
    g = glow("lurker")
    rnd = random.Random(12)

    body = MB(80)
    front = -math.pi / 2
    # The long neck dropping into the water, a pale belly down its front.
    neck = [(0.62, -3.0), (0.7, -2.0), (0.78, -1.0), (0.82, -0.2), (0.8, 0.25)]
    body.lathe(neck, at=(0, 0, -0.25), mat=hide, segs=14, cap=False)
    body.lathe([(r + 0.025, y) for r, y in neck[:-1]], at=(0, 0, -0.25), mat=belly, segs=6, arc=(front - 0.7, front + 0.7))
    # The skull: low, broad and flat, the upper jaw overhanging the maw.
    body.uvsphere(0.86, at=(0, 0.56, 0.0), mat=hide, scale=(1.18, 0.6, 1.25), segs=18, rings=10)
    body.uvsphere(0.7, at=(0, 0.42, 0.42), mat=hide2, scale=(1.08, 0.42, 1.05), segs=16, rings=8)
    # Inside of the mouth: a dark maw with a raw rim.
    body.uvsphere(0.58, at=(0, 0.22, 0.5), mat=P["tar"], scale=(1.0, 0.42, 1.0), segs=14, rings=8)
    body.ring(0.62, 0.05, at=(0, 0.26, 0.5), mat=gum, segs=18, tube_segs=4, pitch=0.05)
    # Fangs hanging from the upper jaw, longest at the front.
    for k in range(11):
        a = (k / 10 - 0.5) * 2.3
        x, z = math.sin(a) * 0.66, 0.48 + math.cos(a) * 0.62
        L = 0.3 - abs(k - 5) * 0.035
        body.cyl(0.05 - abs(k - 5) * 0.004, 0.0, L, at=(x, 0.3 - L / 2, z), mat=P["bone"], segs=5, pitch=math.pi + 0.15, centered=True)
    # Small eyes deep under heavy brows; the lure on its stalk.
    for side in (-1, 1):
        body.uvsphere(0.2, at=(side * 0.48, 0.98, 0.48), mat=hide, scale=(1.4, 0.55, 1.0), segs=10, rings=6, roll=side * 0.35)
        body.uvsphere(0.1, at=(side * 0.5, 0.86, 0.66), mat=P["tar"], segs=8, rings=5)
        body.uvsphere(0.065, at=(side * 0.51, 0.86, 0.72), mat=g, segs=8, rings=5)
    body.tube([(0, 1.02, 0.3), (0, 1.45, 0.45), (0, 1.75, 0.8), (0, 1.68, 1.08)], [0.05, 0.04, 0.028, 0.02], mat=hide2, segs=5)
    body.uvsphere(0.13, at=(0, 1.6, 1.12), mat=g, segs=10, rings=6)
    # A frilled dorsal fin down the back of the head and neck.
    spines = [(0.0, 0.0)]
    for k in range(7):
        spines += [(k * 0.24 + 0.12, 0.42 - k * 0.04), (k * 0.24 + 0.24, 0.1)]
    spines += [(1.75, 0.0)]
    body.prism([(x, y) for x, y in reversed(spines)], 0.05, at=(0, 0.95, -0.15), mat=hide2, yaw=math.pi / 2, roll=0.0, pitch=0.0, bev=0)
    # Fins behind the jaw hinge, and gill slits that glow faintly.
    for side in (-1, 1):
        fin = [(0.0, 0.0), (0.6, 0.3), (0.85, 0.06), (0.7, -0.16), (0.38, -0.22)]
        body.prism([(x * side, y) for x, y in (fin if side > 0 else list(reversed(fin)))], 0.04, at=(side * 0.85, 0.32, -0.2), mat=hide2, yaw=side * 0.9, bev=0)
        for k in range(3):
            body.box((0.03, 0.32, 0.06), at=(side * 0.78, 0.0 - k * 0.12, -0.05 + k * 0.1), mat=g, yaw=side * 0.5, roll=side * 0.15, centered=True, bev=0)
    barnacles(body, rnd, (0.3, 1.0, -0.35), (0.3, 0.04, 0.2), 8, size=0.05)
    body.build("body", parent=root, smooth=40, ground=False, grime=0.0)

    jaw = MB(81)
    # A heavy underslung jaw, fangs pointing up, the tongue dark.
    jaw.uvsphere(0.72, at=(0, -0.1, 0.52), mat=belly, scale=(1.02, 0.34, 1.12), segs=16, rings=8)
    jaw.uvsphere(0.56, at=(0, 0.0, 0.56), mat=P["tar"], scale=(0.95, 0.2, 1.0), segs=14, rings=6)
    jaw.ring(0.6, 0.045, at=(0, 0.03, 0.56), mat=gum, segs=18, tube_segs=4)
    for k in range(9):
        a = (k / 8 - 0.5) * 2.1
        x, z = math.sin(a) * 0.6, 0.55 + math.cos(a) * 0.56
        L = 0.24 - abs(k - 4) * 0.03
        jaw.cyl(0.045, 0.0, L, at=(x, 0.03 + L / 2, z), mat=P["bone"], segs=5, pitch=-0.1, centered=True)
    jaw.build("jaw", loc=(0, 0.2, -0.1), parent=root, smooth=40, ground=False, grime=0.0)
    return root


# ----------------------------------------------------------- wreck guardian


def hull_shell(m, length, beam, depth, at, mat, keel_up=True, stations=7, strakes=6, strips=None):
    """A boat hull (loft) for shoulders and the capsized base. keel_up turns it over."""
    x0, y0, z0 = at
    secs = []
    for s in range(stations):
        t = s / (stations - 1)
        z = z0 - length / 2 + t * length
        k = math.sin(t * math.pi) ** 0.6
        b, d = beam / 2 * max(0.05, k), depth * (0.55 + 0.45 * k)
        pts = []
        for j in range(-strakes, strakes + 1):
            u = j / strakes
            x = b * math.sin(u * math.pi / 2)
            y = -d * math.cos(u * math.pi / 2)
            pts.append((x0 + x, y0 + (-y if keel_up else y), z))
        secs.append(pts)
    m.loft(secs, mat=mat, strips=strips, flip=keel_up)


def wreck_guardian():
    """A colossus of fused hulls and chain: a capsized hull for a base, a
    staved barrel of a chest caging the heart-lantern, upturned dinghies for
    shoulders, a drowned lantern room for a head, a chain arm ending in an
    anchor and a hull-plank arm carrying a brine mortar."""
    root = kit.empty("MODEL_wreck_guardian", (20, 0, 0))
    hull, hull_dark = P["hull"], P["hull_dark"]
    heart = glow("heart")
    vents = glow("vents")
    chain_glow = glow("chain")
    rnd = random.Random(12)

    body = MB(90)
    # Lower body: a capsized hull, keel up, sunk to the waterline.
    hull_shell(body, 6.4, 7.0, 2.2, (0, -1.6, -0.2), hull_dark, keel_up=True, strips=[(hull_dark, 0.9), (hull, 1.0)])
    body.box((0.35, 0.4, 6.6), at=(0, 0.55, -0.2), mat=P["tar"], centered=True)
    # The chest: a staved barrel of hull planks with iron bands, open at the
    # front where the ribs cage the heart.
    front = -math.pi / 2  # lathe angle that faces game +Z
    # Narrow at the waist, broadening into a hulking chest and shoulders.
    body.lathe([(1.6, 0.6), (1.78, 1.4), (1.98, 2.4), (2.02, 2.6)], at=(0, 0, -0.45), mat=hull, segs=16, staves=0.14, cap=False)
    body.lathe([(2.03, 2.52), (2.12, 3.3), (2.24, 4.28)], at=(0, 0, -0.45), mat=hull, segs=14, staves=0.14, arc=(front + 0.62, front + math.tau - 0.62))
    body.lathe([(2.22, 4.2), (2.3, 4.7), (2.1, 5.3), (1.5, 5.8), (0.0, 5.9)], at=(0, 0, -0.45), mat=hull, segs=16, staves=0.14, cap=False)
    # A dark hollow behind the heart.
    body.uvsphere(1.15, at=(0, 3.4, -0.55), mat=P["tar"], scale=(1.0, 0.9, 1.0), segs=12, rings=8)
    for y, r in ((1.3, 1.8), (2.9, 2.08), (4.6, 2.3)):
        body.ring(r, 0.075, at=(0, y, -0.45), mat=P["iron"], segs=20, tube_segs=4)
    # Ribs arcing round the heart opening.
    for k in range(5):
        y = 2.4 + k * 0.42
        w = 1.3 - abs(k - 2) * 0.22
        pts = [(-w, y - 0.3, 1.0), (-w * 0.8, y, 1.45), (0.0, y + 0.1, 1.62), (w * 0.8, y, 1.45), (w, y - 0.3, 1.0)]
        if k == 2:
            continue  # the gap the heart shows through
        body.tube(pts, 0.12, mat=P["timber_pale"], segs=6)
    # Upturned dinghies as shoulders.
    for side in (-1, 1):
        hull_shell(body, 3.8, 2.6, 1.0, (side * 2.35, 5.15, -0.35), hull, keel_up=True, stations=7, strakes=5, strips=[(Paint(P["paint_blue"].mat, 0x2F4A52), 1.0), (hull, 1.0), (Paint(P["paint_white"].mat, 0x9C9686), 1.0)])
    # Broken spars jutting back and out from the shoulders, rags of sail on them.
    for side in (-1, 1):
        base = (side * 1.3, 5.2, -1.4)
        top = (side * 3.6, 8.6, -3.2)
        mid = ((base[0] + top[0]) / 2, (base[1] + top[1]) / 2 + 0.2, (base[2] + top[2]) / 2)
        body.tube([base, mid, top], [0.24, 0.2, 0.1], mat=P["timber"], segs=7)
        ribbon(body, [(mid[0] + side * 0.6, 7.6, -2.6), (mid[0] + side * 0.75, 6.6, -2.4), (mid[0] + side * 0.6, 5.8, -2.2)], [1.0, 0.85, 0.4], P["canvas"], normal=(0.5, 0, 1))
    # Glowing vents along the upper back (the mortar tell).
    for side in (-1, 1):
        for k in range(3):
            body.box((0.55, 0.22, 0.12), at=(side * (0.7 + k * 0.42), 5.0 + k * 0.18, -2.0 + k * 0.12), mat=vents, roll=side * 0.3, yaw=side * 0.4, centered=True)
    # Barnacle crust and weed.
    for cx, cy, cz in ((-1.0, 1.0, 1.35), (1.2, 1.6, 1.35), (0.4, 0.8, 1.5), (-1.5, 4.9, 1.0), (1.6, 4.4, 1.2)):
        barnacles(body, rnd, (cx, cy, cz), (0.45, 0.35, 0.15), 9, size=0.11)
    for k in range(10):
        a = -1.2 + k * 0.27
        hanging_weed(body, rnd, (math.sin(a) * 1.9, 4.9 - abs(a) * 0.3, math.cos(a) * 1.9 - 0.45), 2.2, count=2)
    body.build("body", parent=root, smooth=32, ground=False, grime=0.0, ao_dist=1.6)

    h = MB(91)
    h.uvsphere(0.82, mat=heart, segs=16, rings=10)
    h.lathe([(0.0, -1.0), (0.3, -0.85), (0.45, -0.5), (0.0, -0.5)], mat=heart, segs=10)
    h.build("heart", loc=(0, 3.4, 0.55), parent=root, smooth=60, ao=0.0, ground=False, grime=0.0)

    head = MB(92)
    # A drowned lantern room: iron sill, bars, a dome, the eye glowing inside.
    head.cyl(1.0, 1.08, 0.3, at=(0, 0, 0), mat=P["iron"], segs=14)
    for k in range(10):
        a = k / 10 * TAU
        head.box((0.12, 1.4, 0.12), at=(math.cos(a) * 0.92, 0.3, math.sin(a) * 0.92), mat=P["iron"], yaw=-a)
    head.ring(0.95, 0.07, at=(0, 1.7, 0), mat=P["iron"], segs=18, tube_segs=4)
    head.lathe([(1.08, 1.72), (1.0, 1.95), (0.7, 2.3), (0.3, 2.5), (0.0, 2.55)], mat=P["copper"], segs=16, cap=False)
    head.uvsphere(0.5, at=(0, 0.95, 0.1), mat=heart, segs=12, rings=8)
    head.cyl(0.04, 0.02, 0.9, at=(0, 2.5, 0), mat=P["iron"], segs=5)
    hanging_weed(head, rnd, (0.6, 1.75, 0.5), 1.0, count=3)
    head.build("head", loc=(0, 6.0, -0.2), parent=root, smooth=30, ground=False, grime=0.0)

    # Left: the chain arm that sweeps, ending in an anchor. Pivot at the shoulder.
    arm = MB(93)
    for k in range(10):
        x = -0.5 - k * 0.52
        mat = chain_glow if k % 3 == 0 else P["iron"]
        if k % 2:
            arm.ring(0.32, 0.075, at=(x, -0.25, 0), mat=mat, segs=12, tube_segs=5)
        else:
            arm.ring(0.32, 0.075, at=(x, -0.25, 0), mat=mat, segs=12, tube_segs=5, pitch=math.pi / 2)
    ax = -5.7
    arm.box((0.36, 2.3, 0.36), at=(ax, -2.2, 0), mat=P["rust"])
    arc = [(ax + math.sin(a) * 1.25, -2.2 + (1 - math.cos(a)) * 0.9, 0.0) for a in [(-0.45 + k / 8 * 0.9) * math.pi for k in range(9)]]
    arm.tube(arc, 0.17, mat=P["rust"], segs=6)
    for side in (-1, 1):
        x, y, z = arc[0] if side < 0 else arc[-1]
        arm.prism([(0, -0.3), (0.38, 0.1), (0.08, 0.6), (0, 0.7), (-0.08, 0.6), (-0.38, 0.1)], 0.12, at=(x, y, z), mat=P["rust_light"], roll=-side * 0.75, bev=0.02)
    arm.ring(0.4, 0.09, at=(ax, 0.2, 0), mat=P["iron"], pitch=math.pi / 2, segs=14, tube_segs=5)
    arm.build("arm_l", loc=(-2.6, 5.2, 0), parent=root, smooth=40, ground=False, grime=0.0)

    # Right: a beam of hull planks carrying the brine mortar (muzzle at x 4.3).
    arm = MB(94)
    for k, (yo, zo) in enumerate(((0.25, 0.25), (0.25, -0.25), (-0.25, 0.25), (-0.25, -0.25))):
        arm.plank(3.3, 0.36, 0.3, at=(1.6, yo - 0.15, zo), mat=hull if k % 2 else hull_dark)
    for x in (0.6, 1.8, 2.9):
        arm.box((0.2, 1.1, 1.1), at=(x, -0.55, 0), mat=P["iron"], centered=False)
    prof = [(0.48, -0.85), (0.56, -0.6), (0.55, 0.0), (0.46, 0.55), (0.5, 0.65), (0.5, 0.85), (0.4, 0.85)]
    arm.lathe(prof, at=(3.45, 0.0, 0), mat=P["iron"], segs=14, roll=-math.pi / 2)
    arm.cyl(0.36, 0.36, 0.1, at=(4.3, 0.0, 0), mat=vents, segs=14, roll=-math.pi / 2, centered=True)
    for k in range(3):
        arm.ring(0.57, 0.05, at=(2.9 + k * 0.35, 0.0, 0), mat=P["brass"], roll=math.pi / 2, segs=16, tube_segs=4)
    hanging_weed(arm, rnd, (2.2, -0.4, 0.3), 1.4, count=3)
    arm.build("arm_r", loc=(2.6, 5.2, 0), parent=root, smooth=40, ground=False, grime=0.0)
    return root


for build in (brine_crab, drowned_spitter, lantern_wisp, tide_lurker, wreck_guardian):
    build()

kit.save_and_export("art/blender/enemies/enemies.blend", "public/assets/models/enemies.glb")
