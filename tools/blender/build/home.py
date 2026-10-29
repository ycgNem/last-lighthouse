"""Builds art/blender/home/home.blend and public/assets/models/home.glb.

Lantern's Rest's buildings and dressing. Home is laid out in code
(src/world/home/HomeLevel.ts, docs/LEVELS.md) because progression changes so
much of it, so this file makes models, not a level: each HOME_<name> has its
own origin and the code sets it over the collision box it already uses. The
sizes here match those boxes (each docstring says which).

Children the code looks for by name:
  window_*   a cottage's front panes, lit one by one as the stage rises
  mouth      the forge's firebox (glows once the forge is repaired)
  coals      the hearth's embers
  smoke      an empty where chimney smoke starts
  COL_*      extra collision (benches, barrels, the anvil): hidden, made solid
Materials patched by name: GLASS_lantern (the lamp room glazing, made
transparent), EMBER (firebox and coals).

    blender -b --factory-startup --python tools/blender/build/home.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import kit  # noqa: E402
from kit import MB, Paint, hull_sections  # noqa: E402

kit.reset()
P = kit.palette()
T = kit.load_props()
STONE, PAINT, WOOD, IRON, GLASS, VERD = (P[k].mat for k in ("stone", "paint_white", "timber", "iron", "glass_white", "copper"))

WASH = Paint(STONE, 0xE6E1D5)
OCHRE = Paint(STONE, 0xDCC9A0)
GREYWASH = Paint(STONE, 0xC9CFCB)
QUOIN = P["stone_dark"]
RED = Paint(PAINT, 0x9A3A30)
BRICK = Paint(STONE, 0x8A4A36)
TERRACOTTA = Paint(STONE, 0xA45A3A)
RIDGE = Paint(STONE, 0x7E4636)
SLATE = P["slate"]
ASH = Paint(STONE, 0x4A4642)
CHAR = Paint(WOOD, 0x2E2722)
DARK_GLASS = Paint(GLASS, 0x22303A)
WATER = Paint(GLASS, 0x3C6670)
LEAF = P["moss"]
VERD_LIGHT = Paint(VERD, 0x7FAE9A)
BLOOMS = [P["paint_red"], P["paint_yellow"], P["paint_white"], Paint(PAINT, 0xC77DB5)]
DOORS = {"blue": P["paint_blue"], "red": Paint(PAINT, 0x8E3B2E), "green": Paint(PAINT, 0x3E6B4E)}

glass = kit.material("GLASS_lantern", 0xFFF1C9, rough=0.05, emit=0xFFB347, strength=0.25)
ember = kit.material("EMBER", 0x331A0A, rough=0.9, emit=0xFF7A1A, strength=1.4)
window = kit.material("WINDOW", 0x1A1F24, rough=0.3)
lamp = P["lamp"]

ACROSS = math.pi / 2  # roll: a Y-axis cylinder lies along X
FACING = math.pi / 2  # ring pitch: the ring stands in the XY plane


def aim(n):
    """(pitch, roll) that turn a primitive's +Y axis toward the unit vector n."""
    return math.asin(max(-1.0, min(1.0, n[2]))), math.atan2(-n[0], n[1])


def col(name, size, at, parent, yaw=0.0):
    """A collision box for the code to make solid (it hides it)."""
    return MB().box(size, at=at, mat=P["tar"], yaw=yaw, bev=0).build(name, parent=parent, ao=0, grime=0, ground=False)


# ------------------------------------------------------------- lighthouse

TOWER = 24.0  # src/world/Lighthouse.ts TOWER_HEIGHT; the beam pivots at TOWER + 1.9


def tower_r(y):
    """The shaft's radius: 3.8 at the plinth, curving in to 2.68 under the gallery."""
    t = max(0.0, min(1.0, (y - 0.3) / (23.4 - 0.3)))
    return 2.68 + 1.12 * (1 - t) ** 1.35


def on_tower(th, lx, y, lz):
    """A point in a frame facing out of the tower at angle th (0 = +Z, the door)."""
    return (lx * math.cos(th) + lz * math.sin(th), y, -lx * math.sin(th) + lz * math.cos(th))


def lighthouse():
    """The keeper's tower over HomeLevel's 3.8 m collision cylinder: whitewashed
    courses with the two red bands, a stone door surround facing the square
    (+Z), small windows climbing round it, a corbelled gallery with railings,
    the lamp room glazed in a diamond lattice, a copper dome and vane."""
    m = MB(200)
    iron = P["iron"]
    m.lathe([(0.0, 0.0), (4.0, 0.0), (4.0, 0.24), (3.9, 0.3), (0.0, 0.3)], mat=QUOIN, segs=32)
    for y0, y1, n, paint in ((0.3, 6.2, 9, WASH), (6.2, 7.8, 3, RED), (7.8, 14.2, 11, WASH), (14.2, 15.8, 3, RED), (15.8, 23.4, 13, WASH)):
        for k in range(n):
            a, b = y0 + (y1 - y0) * k / n, y0 + (y1 - y0) * (k + 1) / n
            m.lathe([(tower_r(a), a), (tower_r(b), b)], mat=paint, segs=32, cap=False, tint=1.0 + (m.rnd.random() - 0.5) * 0.06)

    # Windows: a dark pane set back in a stone frame.
    for y, th in ((4.6, 3.5), (9.8, 2.2), (12.4, 5.1), (17.6, 0.6), (20.6, 3.9)):
        r = tower_r(y)
        m.box((0.56, 1.06, 0.1), at=on_tower(th, 0, y, r), mat=DARK_GLASS, yaw=th, centered=True, bev=0)
        m.box((0.92, 0.12, 0.3), at=on_tower(th, 0, y - 0.6, r + 0.06), mat=QUOIN, yaw=th, centered=True, bev=0.02)
        m.box((0.92, 0.18, 0.28), at=on_tower(th, 0, y + 0.62, r + 0.05), mat=QUOIN, yaw=th, centered=True, bev=0.02)
        for s in (-1, 1):
            m.box((0.16, 1.1, 0.24), at=on_tower(th, s * 0.36, y, r + 0.04), mat=QUOIN, yaw=th, centered=True, bev=0.02)

    # Door: stone surround, plank leaf with iron straps, threshold, a lamp beside it.
    for s in (-1, 1):
        m.box((0.32, 2.5, 0.5), at=(s * 0.86, 0.3, 3.8), mat=QUOIN, bev=0.03)
    m.box((2.1, 0.36, 0.52), at=(0, 2.8, 3.8), mat=QUOIN, bev=0.03)
    m.prism([(-1.15, 0.0), (1.15, 0.0), (0.0, 0.5)], 0.44, at=(0, 3.16, 3.8), mat=QUOIN, bev=0.02)
    for k in range(5):
        m.box((0.27, 2.5, 0.07), at=(-0.56 + k * 0.28, 0.3, 3.84), mat=P["hull"], bev=0.01, jit=0.08)
    for y in (0.85, 2.15):
        m.box((1.3, 0.07, 0.03), at=(0, y, 3.885), mat=iron, centered=True, bev=0)
    m.ring(0.06, 0.012, at=(0.36, 1.45, 3.9), mat=iron, pitch=FACING, segs=10, tube_segs=4)
    m.box((1.5, 0.08, 0.4), at=(0, 0.3, 3.8), mat=QUOIN, bev=0.01)
    m.tube([(1.3, 2.65, 3.5), (1.3, 2.8, 3.85), (1.3, 2.72, 4.0)], 0.025, mat=iron, segs=5)
    m.box((0.2, 0.3, 0.2), at=(1.3, 2.3, 4.0), mat=lamp, bev=0)
    m.cyl(0.16, 0.04, 0.12, at=(1.3, 2.6, 4.0), mat=iron, segs=8, bev=0)

    # Corbelled gallery, deck and railing.
    m.lathe([(2.68, 23.3), (2.9, 23.45), (2.95, 23.6), (3.25, 23.75), (3.3, 23.9), (3.62, 24.0)], mat=QUOIN, segs=32, cap=False)
    m.cyl(3.75, 3.75, 0.2, at=(0, 24.0, 0), mat=QUOIN, segs=32, bev=0.03)
    for k in range(32):
        a = k / 32 * math.tau
        m.cyl(0.03, 0.03, 1.0, at=(math.cos(a) * 3.62, 24.2, math.sin(a) * 3.62), mat=iron, segs=5, bev=0)
    for y, t in ((25.2, 0.045), (24.7, 0.025)):
        m.ring(3.62, t, at=(0, y, 0), mat=iron, segs=48, tube_segs=5)

    # Lamp room: pedestal, glazing in a diamond lattice of astragals, cornice.
    m.cyl(2.3, 2.3, 0.7, at=(0, 24.2, 0), mat=WASH, segs=24, bev=0.03)
    m.cyl(2.32, 2.32, 0.08, at=(0, 24.9, 0), mat=iron, segs=24, bev=0.01)
    m.lathe([(2.15, 24.95), (2.15, 27.45)], mat=glass, segs=24, cap=False)
    for k in range(12):
        a0 = k / 12 * math.tau
        for d in (-1, 1):
            pts = []
            for j in range(7):
                t = j / 6
                a = a0 + d * t * math.tau / 12
                pts.append((math.cos(a) * 2.18, 24.95 + t * 2.5, math.sin(a) * 2.18))
            m.tube(pts, 0.026, mat=iron, segs=4)
    for y in (24.97, 27.43):
        m.ring(2.19, 0.045, at=(0, y, 0), mat=iron, segs=36, tube_segs=4)
    m.cyl(2.45, 2.45, 0.12, at=(0, 27.45, 0), mat=iron, segs=32, bev=0.02)

    # Copper dome with ribs, ventilator ball, lightning rod and vane.
    dome = [(2.5, 27.57), (2.38, 27.75), (2.05, 28.2), (1.55, 28.7), (0.95, 29.1), (0.35, 29.35), (0.0, 29.4)]
    m.lathe(dome, mat=P["copper"], segs=32)
    for k in range(16):
        a = k / 16 * math.tau
        m.tube([(math.cos(a) * (r + 0.03), y + 0.02, math.sin(a) * (r + 0.03)) for r, y in dome[:-1]], 0.035, mat=VERD_LIGHT, segs=4)
    m.cyl(0.12, 0.16, 0.3, at=(0, 29.3, 0), mat=P["copper"], segs=10)
    m.uvsphere(0.32, at=(0, 29.85, 0), mat=P["copper"], segs=16, rings=10)
    m.cyl(0.035, 0.02, 1.4, at=(0, 30.1, 0), mat=iron, segs=6, bev=0)
    m.prism([(-0.45, -0.05), (0.3, -0.05), (0.3, -0.15), (0.5, 0.0), (0.3, 0.15), (0.3, 0.05), (-0.45, 0.05)], 0.02, at=(0, 31.0, 0), mat=iron, bev=0)
    return m.build("HOME_lighthouse", loc=(0, 0, 0), ao=0.55, ao_dist=1.2, grime=0.12, grime_h=2.5, smooth=30)


# ---------------------------------------------------------------- cottages


def cottage(name, x, seed, wall, door, chimneys=(1,), porch=False, flowers=False, shutters=False, bench=False, butt=False, pots=False):
    """A whitewashed cottage over HomeLevel's 6 x 3.2 x 5 m collision box:
    stone plinth and quoins, a slate roof (ridge along X), chimney stacks with
    pots, the door and two windows on the +Z front (window_0/1 are the panes
    the code lights). Extras outside the box carry COL_ boxes."""
    m = MB(seed)
    rnd = m.rnd
    W, D, H, rise = 6.0, 5.0, 3.2, 2.1
    hw, hd = W / 2, D / 2
    m.box((W + 0.04, 0.42, D + 0.04), mat=QUOIN, bev=0.02)
    m.box((W, H - 0.42, D), at=(0, 0.42, 0), mat=wall, bev=0.03)
    for sx in (-1, 1):
        for sz in (-1, 1):
            for k in range(7):
                lx, lz = (0.56, 0.3) if k % 2 == 0 else (0.3, 0.56)
                m.box((lx, 0.35, lz), at=(sx * (hw - lx / 2 + 0.03), 0.45 + k * 0.39, sz * (hd - lz / 2 + 0.03)), mat=QUOIN, bev=0.025, jit=0.08)
    for s in (-1, 1):
        m.prism([(-hd, 0.0), (hd, 0.0), (0.0, rise)], 0.3, at=(s * (hw - 0.15), H, 0), mat=wall, yaw=math.pi / 2, bev=0.02)

    # Roof: a slab each side, then overlapping slate courses (mossier toward the eaves) and a ridge.
    pitch = math.atan2(rise, hd)
    L = math.hypot(hd, rise) + 0.4
    cp, sp = math.cos(pitch), math.sin(pitch)
    for s in (-1, 1):
        zc, yc = s * (L / 2) * cp, H + rise - (L / 2) * sp
        m.box((W + 0.6, 0.14, L), at=(0, yc + 0.07 * cp, zc + s * 0.07 * sp), mat=SLATE, pitch=s * pitch, centered=True, bev=0.02)
        rows = 12
        for k in range(rows):
            d = 0.25 + (L - 0.35) * k / (rows - 1)
            moss = (k / (rows - 1)) ** 2 * (0.22 if s < 0 else 0.1)
            shade = 0.88 + rnd.random() * 0.2
            m.box((W + 0.62, 0.035, 0.36), at=(0, H + rise - d * sp + 0.155 * cp, s * (d * cp + 0.155 * sp)), mat=SLATE,
                  pitch=s * (pitch - 0.06), centered=True, bev=0, tint=(shade * (1 - moss), shade, shade * (1 - moss * 1.6)))
    m.cyl(0.12, 0.12, W + 0.66, at=(0, H + rise + 0.13, 0), mat=RIDGE, segs=8, roll=ACROSS, centered=True, bev=0)

    smoke = None
    for c in chimneys:
        cx = c * (hw - 0.5)
        m.box((0.9, 2.35, 0.75), at=(cx, H + rise - 1.25, 0), mat=wall, bev=0.03)
        m.box((1.04, 0.12, 0.89), at=(cx, H + rise + 1.1, 0), mat=QUOIN, bev=0.02)
        for dx in (-0.2, 0.2):
            m.cyl(0.12, 0.1, 0.36, at=(cx + dx, H + rise + 1.22, 0), mat=TERRACOTTA, segs=10, bev=0.01)
        smoke = smoke or (cx - 0.2, H + rise + 1.6, 0.0)

    # Door: stone frame, painted boards with battens and a ring, a step.
    zf = hd
    for sx in (-1, 1):
        m.box((0.16, 2.05, 0.14), at=(sx * 0.58, 0.0, zf + 0.04), mat=QUOIN, bev=0.02)
    m.box((1.36, 0.24, 0.16), at=(0, 2.0, zf + 0.04), mat=QUOIN, bev=0.02)
    for k in range(4):
        m.box((0.245, 1.9, 0.06), at=(-0.375 + k * 0.25, 0.05, zf + 0.02), mat=door, bev=0.008, tint=1.0 + (k % 2) * 0.05)
    for y in (0.5, 1.45):
        m.box((0.9, 0.08, 0.03), at=(0, y, zf + 0.06), mat=door, bev=0.005, tint=0.82)
    m.ring(0.055, 0.012, at=(0.32, 1.0, zf + 0.08), mat=P["iron"], pitch=FACING, segs=10, tube_segs=4)
    m.box((1.4, 0.12, 0.45), at=(0, 0.0, zf + 0.22), mat=QUOIN, bev=0.02)
    if porch:
        for sx in (-1, 1):
            m.prism([(0.0, 0.0), (0.0, 0.42), (0.5, 0.42)], 0.08, at=(sx * 0.62, 2.05, zf + 0.04), mat=P["timber"], yaw=-math.pi / 2, bev=0.01)
        m.box((1.7, 0.08, 0.8), at=(0, 2.55, zf + 0.36), mat=SLATE, pitch=0.22, centered=True, bev=0.01)

    # Windows: stone sill and lintel, white frame and glazing bars; shutters or a flower box.
    for wx in (-1.9, 1.9):
        m.box((1.16, 0.09, 0.2), at=(wx, 1.31, zf + 0.06), mat=QUOIN, bev=0.015)
        m.box((1.16, 0.16, 0.12), at=(wx, 2.4, zf + 0.04), mat=QUOIN, bev=0.015)
        for sx in (-1, 1):
            m.box((0.08, 1.0, 0.08), at=(wx + sx * 0.46, 1.4, zf + 0.04), mat=P["paint_white"], bev=0.01)
        m.box((0.05, 0.98, 0.04), at=(wx, 1.41, zf + 0.055), mat=P["paint_white"], bev=0)
        m.box((0.86, 0.05, 0.04), at=(wx, 1.88, zf + 0.055), mat=P["paint_white"], centered=True, bev=0)
        if shutters:
            sx = 1 if wx < 0 else -1  # the door side; the corner side is all quoins
            m.box((0.4, 1.0, 0.04), at=(wx + sx * 0.72, 1.4, zf + 0.03), mat=door, bev=0.008)
            for yy in (1.55, 2.2):
                m.box((0.4, 0.06, 0.02), at=(wx + sx * 0.72, yy, zf + 0.055), mat=door, bev=0, tint=0.82)
        if flowers:
            m.box((0.96, 0.18, 0.2), at=(wx, 1.1, zf + 0.13), mat=P["timber"], bev=0.01)
            for k in range(7):
                fx = wx - 0.4 + k * 0.133 + (rnd.random() - 0.5) * 0.05
                m.uvsphere(0.07, at=(fx, 1.3 + rnd.random() * 0.06, zf + 0.12 + (rnd.random() - 0.5) * 0.08), mat=LEAF, segs=6, rings=4)
                m.uvsphere(0.045, at=(fx + 0.02, 1.36 + rnd.random() * 0.06, zf + 0.16), mat=BLOOMS[k % len(BLOOMS)], segs=6, rings=4)
    # A small dark window at the back.
    m.box((0.7, 0.8, 0.06), at=(1.2, 1.6, -hd - 0.01), mat=DARK_GLASS, bev=0)
    m.box((0.9, 0.09, 0.18), at=(1.2, 1.52, -hd - 0.06), mat=QUOIN, bev=0.015)
    m.box((0.9, 0.14, 0.12), at=(1.2, 2.42, -hd - 0.04), mat=QUOIN, bev=0.015)
    if bench:
        for bx in (-2.45, -1.35):
            m.box((0.3, 0.4, 0.3), at=(bx, 0.0, zf + 0.35), mat=QUOIN, bev=0.03)
        m.plank(1.4, 0.36, 0.07, at=(-1.9, 0.4, zf + 0.35), mat=P["timber_light"], warp=0.02)

    ob = m.build(name, loc=(x, 0, 0), ao=0.6, ao_dist=0.9, grime=0.15, grime_h=0.8)
    col("COL_body", (W, H, D), (0, 0, 0), ob)
    for i, wx in enumerate((-1.9, 1.9)):
        MB(seed + 10 + i).box((0.84, 0.94, 0.02), at=(wx, 1.43, zf + 0.012), mat=window, bev=0).build(f"window_{i}", parent=ob, ao=0, grime=0, ground=False)
    kit.empty("smoke", smoke, parent=ob, size=0.3)
    if bench:
        col("COL_bench", (1.4, 0.5, 0.45), (-1.9, 0, zf + 0.35), ob)
    if butt:
        kit.place(T, "barrel", f"{name}_butt", (hw + 0.5, 0, hd - 0.7), yaw=0.4, parent=ob, scale=1.1)
        col("COL_butt", (0.85, 1.0, 0.85), (hw + 0.5, 0, hd - 0.7), ob)
    if pots:
        kit.place(T, "lobster_pot", f"{name}_pot1", (-hw - 0.55, 0, 1.2), yaw=1.4, parent=ob)
        kit.place(T, "lobster_pot", f"{name}_pot2", (-hw - 0.5, 0.45, 1.25), yaw=1.7, parent=ob)
        kit.place(T, "lobster_pot", f"{name}_pot3", (-hw - 0.6, 0, 0.3), yaw=1.2, parent=ob)
        col("COL_pots", (0.9, 0.9, 1.9), (-hw - 0.55, 0, 0.75), ob)
    return ob


# ------------------------------------------------------------------- forge


def forge(name, x, broken):
    """The smithy over HomeLevel's 4 x 2.2 x 3 m collision box: a brick furnace
    with its firebox ("mouth") waist high in the +Z face, the chimney stack at
    the back right, bellows on the left, an anvil on a stump, a quench tub and
    a tool rack. Broken: the stack has come down in a spill of bricks, the
    slab is cracked, the bellows are gone and the anvil lies on its side."""
    m = MB(240 + int(broken))
    rnd = m.rnd
    iron = P["iron"]
    m.box((4.0, 0.5, 3.0), mat=P["stone_dark"], bev=0.03)
    m.box((3.9, 1.6, 2.9), at=(0, 0.5, 0), mat=BRICK, bev=0.02)
    for sx in (-1, 1):
        for sz in (-1, 1):
            for k in range(4):
                lx, lz = (0.5, 0.28) if k % 2 == 0 else (0.28, 0.5)
                m.box((lx, 0.36, lz), at=(sx * (1.95 - lx / 2 + 0.03), 0.52 + k * 0.4, sz * (1.45 - lz / 2 + 0.03)), mat=QUOIN, bev=0.025, jit=0.08)
    if broken:
        m.box((2.2, 0.14, 3.1), at=(-0.95, 2.1, 0), mat=P["rock"], bev=0.03, roll=0.03)
        m.box((1.8, 0.14, 2.6), at=(1.2, 2.04, 0.15), mat=P["rock"], bev=0.03, roll=-0.12, pitch=0.05)
    else:
        m.box((4.1, 0.14, 3.1), at=(0, 2.1, 0), mat=P["rock"], bev=0.03)

    # Firebox: a dark recess under a stone arch, jamb stones either side.
    m.box((1.5, 0.9, 0.24), at=(0, 0.45, 1.36), mat=P["tar"], bev=0)
    for k in range(7):
        a = math.radians(20 + k * 140 / 6)
        m.box((0.24, 0.3, 0.22), at=(math.cos(a) * 0.86, 1.0 + math.sin(a) * 0.55, 1.47), mat=QUOIN, roll=a - math.pi / 2, centered=True, bev=0.02, jit=0.1)
    for sx in (-1, 1):
        m.box((0.24, 0.62, 0.22), at=(sx * 0.86, 0.45, 1.47), mat=QUOIN, bev=0.02)
    m.box((1.9, 0.12, 0.3), at=(0, 0.42, 1.5), mat=P["stone_dark"], bev=0.02)

    # Chimney stack (back right).
    if broken:
        m.box((1.0, 0.9, 1.0), at=(1.2, 2.1, 0.6), mat=BRICK, bev=0.02)
        for k in range(9):
            m.box((0.24, 0.1, 0.12), at=(0.85 + rnd.random() * 0.7, 3.0 + rnd.random() * 0.12, 0.25 + rnd.random() * 0.7), mat=BRICK, yaw=rnd.random() * 3, bev=0.008, jit=0.1)
        m.box((0.9, 0.9, 1.7), at=(3.0, 0.0, -0.9), mat=BRICK, yaw=0.5, roll=0.15, bev=0.03)
        for k in range(34):
            bx, bz = 2.1 + rnd.random() * 1.6, -1.8 + rnd.random() * 3.4
            m.box((0.24, 0.1, 0.12), at=(bx, rnd.random() * 0.08, bz), mat=BRICK, yaw=rnd.random() * 3, pitch=(rnd.random() - 0.5) * 0.6, bev=0.008, jit=0.12)
    else:
        m.box((1.0, 3.2, 1.0), at=(1.2, 2.1, 0.6), mat=BRICK, bev=0.02)
        m.box((1.2, 0.16, 1.2), at=(1.2, 5.3, 0.6), mat=P["rock"], bev=0.02)
        m.cyl(0.18, 0.18, 0.55, at=(1.2, 5.46, 0.6), mat=iron, segs=10, bev=0.01)
        m.cyl(0.36, 0.05, 0.22, at=(1.2, 6.05, 0.6), mat=iron, segs=10, bev=0)
        for dx in (-0.12, 0.12):
            m.box((0.02, 0.1, 0.02), at=(1.2 + dx, 5.98, 0.6), mat=iron, bev=0)

    # Bellows on a frame, the nozzle into the furnace's left side.
    m.box((0.12, 0.7, 0.12), at=(-2.35, 0.0, -0.45), mat=P["timber"], bev=0.015)
    m.box((0.12, 0.7, 0.12), at=(-2.35, 0.0, 0.45), mat=P["timber"], bev=0.015)
    m.box((0.12, 0.1, 1.05), at=(-2.35, 0.7, 0.0), mat=P["timber"], bev=0.015)
    board = [(0.0, -0.05), (-0.55, -0.32), (-1.1, -0.3), (-1.25, 0.0), (-1.1, 0.3), (-0.55, 0.32), (0.0, 0.05)]
    bx0 = -2.05
    m.prism(board, 0.05, at=(bx0, 0.8, 0.0), mat=P["timber_light"], pitch=-math.pi / 2, bev=0.01)
    if not broken:
        m.prism(board, 0.05, at=(bx0, 1.12, 0.0), mat=P["timber_light"], pitch=-math.pi / 2, bev=0.01)
        secs = []
        for yy, k in ((0.83, 1.0), (0.93, 0.86), (1.0, 1.02), (1.07, 0.86), (1.09, 0.98)):
            secs.append([(bx0 + px * k, yy, pz * k) for px, pz in board])
        m.loft(secs, mat=P["leather"], closed=True)
        m.cyl(0.06, 0.03, 0.2, at=(bx0 - 0.05, 0.96, 0.0), mat=iron, segs=8, roll=-math.pi / 2, bev=0)
        m.tube([(bx0 - 1.2, 1.15, 0.0), (bx0 - 1.7, 1.6, 0.0)], 0.03, mat=P["timber"], segs=5)
    col("COL_bellows", (1.6, 1.3, 1.1), (-2.85, 0, 0), None)

    # Anvil on its stump; broken, it lies beside it.
    m.cyl(0.3, 0.33, 0.52, at=(-2.6, 0.0, 2.2), mat=P["timber"], segs=10, bev=0.02)
    m.cyl(0.29, 0.29, 0.02, at=(-2.6, 0.52, 2.2), mat=P["timber_pale"], segs=10, bev=0)
    def anvil(ax, ay, az, r):
        def at(dx, dy):
            return (ax + dx * math.cos(r) - dy * math.sin(r), ay + dx * math.sin(r) + dy * math.cos(r), az)
        m.box((0.36, 0.16, 0.24), at=at(0, 0.08), mat=iron, roll=r, centered=True, bev=0.015)
        m.box((0.22, 0.12, 0.18), at=at(0, 0.22), mat=iron, roll=r, centered=True, bev=0.01)
        m.box((0.58, 0.1, 0.24), at=at(0, 0.33), mat=P["iron_light"], roll=r, centered=True, bev=0.012)
        m.cyl(0.085, 0.0, 0.32, at=at(0.29, 0.33), mat=P["iron_light"], segs=8, roll=-math.pi / 2 + r, bev=0)
    if broken:
        anvil(-3.1, 0.3, 2.65, math.pi / 2)
    else:
        anvil(-2.6, 0.53, 2.2, 0.0)
        for k, (dx, dz) in enumerate(((0.05, -0.05), (-0.08, 0.06))):
            m.tube([(-2.6 + dx, 0.9, 2.2 + dz), (-2.45 + dx, 0.92, 2.32 + dz)], 0.018, mat=iron, segs=4)
    col("COL_anvil", (0.8, 0.9, 0.8), (-2.6, 0, 2.2), None)
    col("COL_body", (4.0, 2.2, 3.0), (0, 0, 0), None)

    # Quench tub (dry when broken), tongs leaning in it.
    m.lathe([(0.0, 0.0), (0.4, 0.0), (0.42, 0.25), (0.43, 0.5), (0.39, 0.5), (0.36, 0.1), (0.0, 0.1)], at=(2.45, 0, 2.0), mat=P["timber"], segs=14, staves=0.12)
    for y in (0.08, 0.42):
        m.ring(0.425 + y * 0.03, 0.014, at=(2.45, y, 2.0), mat=iron, segs=16, tube_segs=4)
    if not broken:
        m.cyl(0.39, 0.39, 0.01, at=(2.45, 0.42, 2.0), mat=WATER, segs=14, bev=0)
        m.tube([(2.3, 0.3, 2.05), (2.2, 1.0, 2.25)], 0.014, mat=iron, segs=4)
        m.tube([(2.35, 0.3, 1.95), (2.22, 1.0, 2.2)], 0.014, mat=iron, segs=4)
    col("COL_tub", (0.95, 0.6, 0.95), (2.45, 0, 2.0), None)

    if not broken:
        # Tool rack on the right wall: a batten, pegs, two hammers and tongs.
        m.box((0.06, 0.1, 1.5), at=(2.0, 1.75, -0.15), mat=P["timber"], bev=0.01)
        for k, z in enumerate((-0.7, -0.3, 0.1, 0.45)):
            m.cyl(0.015, 0.015, 0.1, at=(2.03, 1.8, z), mat=P["timber_pale"], segs=5, roll=-math.pi / 2, bev=0)
        for z in (-0.7, -0.3):
            m.cyl(0.02, 0.02, 0.4, at=(2.08, 1.4, z), mat=P["timber_pale"], segs=6, bev=0)
            m.box((0.07, 0.07, 0.17), at=(2.08, 1.38, z), mat=iron, centered=True, bev=0.008)
        m.tube([(2.07, 1.8, 0.1), (2.08, 1.2, 0.05)], 0.012, mat=iron, segs=4)
        m.tube([(2.07, 1.8, 0.14), (2.08, 1.2, 0.2)], 0.012, mat=iron, segs=4)
        # Coal heap behind the bellows.
        for k in range(16):
            a, d = rnd.random() * math.tau, rnd.random() * 0.45
            m.rock(0.09 + rnd.random() * 0.1, at=(-2.7 + math.cos(a) * d, 0.0, -1.2 + math.sin(a) * d), mat=P["rock_dark"], seed=k + 260, squash=0.7, subdiv=1, tint=0.45)
    ob = m.build(name, loc=(x, 0, 0), ao=0.6, ao_dist=0.9, grime=0.15, grime_h=0.7)
    for c in [o for o in bpy_objects() if o.name.startswith("COL_") and o.parent is None]:
        c.parent = ob
    mm = MB(250 + int(broken))
    mm.box((1.36, 0.78, 0.04), at=(0, 0.5, 1.38), mat=ember, bev=0)
    for k in range(9):
        mm.rock(0.08 + rnd.random() * 0.05, at=(-0.5 + k * 0.125, 0.48, 1.28 + (rnd.random() - 0.5) * 0.1), mat=ember, seed=270 + k, subdiv=1, squash=0.7)
    mm.build("mouth", parent=ob, ao=0, grime=0, ground=False)
    kit.empty("station", (0.0, 0.0, 2.6), parent=ob, size=0.3)
    if broken:
        for k, (gx, gz, s) in enumerate(((-1.4, 0.8, 0.5), (0.4, -1.0, 0.45), (1.8, 1.2, 0.6), (-1.9, -1.3, 0.55))):
            kit.place(T, "dune_grass", f"{name}_weed{k}", (gx, 2.17 if abs(gx) < 1.9 and abs(gz) < 1.4 else 0.0, gz), yaw=k * 1.7, parent=ob, scale=s)
    return ob


def bpy_objects():
    import bpy

    return list(bpy.context.scene.objects)


# ------------------------------------------------------------ hearth, chest


def hearth(x):
    """The square's fire pit over HomeLevel's 1.1 m collision ring: a ring of
    stones on an ash bed, embers ("coals"), charred logs, an iron tripod with
    a pot on its chain, and two log benches (with COL_ boxes)."""
    m = MB(230)
    rnd = m.rnd
    m.cyl(0.98, 1.02, 0.05, mat=ASH, segs=20, bev=0)
    for k in range(11):
        a = k / 11 * math.tau + rnd.random() * 0.2
        m.rock(0.24 + rnd.random() * 0.07, at=(math.cos(a) * 0.98, 0.0, math.sin(a) * 0.98), mat=P["rock"] if k % 3 else P["rock_dark"], seed=231 + k, squash=0.75)
    for k, a in enumerate((0.3, 2.4, 4.4)):
        m.tube([(math.cos(a) * 0.62, 0.12, math.sin(a) * 0.62), (math.cos(a) * 0.08, 0.32, math.sin(a) * 0.08)], 0.07, mat=CHAR, segs=7)
    # Tripod, chain and pot.
    for k in range(3):
        a = k / 3 * math.tau + 0.5
        m.tube([(math.cos(a) * 0.86, 0.0, math.sin(a) * 0.86), (math.cos(a) * 0.05, 1.58, math.sin(a) * 0.05)], 0.025, mat=P["iron"], segs=5)
    m.uvsphere(0.06, at=(0, 1.6, 0), mat=P["iron"], segs=8, rings=5)
    for k in range(6):
        m.ring(0.03, 0.007, at=(0, 1.52 - k * 0.07, 0), mat=P["iron"], yaw=k * math.pi / 2, pitch=FACING, segs=8, tube_segs=3)
    m.lathe([(0.0, 0.48), (0.16, 0.5), (0.25, 0.58), (0.27, 0.7), (0.25, 0.8), (0.27, 0.83), (0.24, 0.84), (0.22, 0.81), (0.0, 0.79)], mat=P["iron"], segs=16)
    m.tube([(-0.25, 0.82, 0), (-0.18, 0.98, 0), (0, 1.1, 0), (0.18, 0.98, 0), (0.25, 0.82, 0)], 0.008, mat=P["iron"], segs=4)
    # Benches: split logs on stump legs.
    benches = ((0.0, -2.35, 0.0), (-2.3, -0.4, 1.4))
    for bx, bz, yaw in benches:
        c, s = math.cos(yaw), math.sin(yaw)
        for d in (-0.55, 0.55):
            m.cyl(0.13, 0.15, 0.3, at=(bx + c * d, 0.0, bz - s * d), mat=P["timber"], segs=8, bev=0.015)
        m.lathe([(0.17, 0.0), (0.17, 1.6)], at=(bx - c * 0.8, 0.42, bz + s * 0.8), mat=P["timber_light"], segs=10, pitch=-math.pi / 2, yaw=yaw - math.pi / 2, arc=(0.0, math.pi))
        m.box((1.6, 0.03, 0.32), at=(bx, 0.42, bz), mat=P["timber_pale"], yaw=yaw, centered=True, bev=0.005)
    ob = m.build("HOME_hearth", loc=(x, 0, 0), ao=0.6, ao_dist=0.6, grime=0.1)
    cm = MB(239)
    cm.lathe([(0.0, 0.03), (0.62, 0.03), (0.5, 0.09), (0.25, 0.14), (0.0, 0.16)], mat=ember, segs=14)
    for k in range(12):
        a, d = rnd.random() * math.tau, rnd.random() * 0.5
        cm.rock(0.06 + rnd.random() * 0.05, at=(math.cos(a) * d, 0.1, math.sin(a) * d), mat=ember, seed=300 + k, subdiv=1, squash=0.7)
    cm.build("coals", parent=ob, ao=0, grime=0, ground=False)
    for i, (bx, bz, yaw) in enumerate(benches):
        col(f"COL_bench{i}", (1.7, 0.5, 0.45), (bx, 0, bz), ob, yaw=yaw)
    return ob


def chest(x):
    """The storage sea chest over HomeLevel's 1.4 x 0.8 x 0.8 m box: planked
    sides, a rounded lid, iron straps and corners, rope beckets and a hasp."""
    m = MB(235)
    iron = P["iron"]
    m.box((1.36, 0.6, 0.76), mat=P["timber_light"], bev=0.02)
    for k in range(3):
        m.box((1.37, 0.012, 0.77), at=(0, 0.2 + k * 0.2, 0), mat=P["hull"], centered=True, bev=0)
    lid = [(-0.4, 0.0), (0.4, 0.0), (0.4, 0.12), (0.3, 0.2), (0.12, 0.24), (-0.12, 0.24), (-0.3, 0.2), (-0.4, 0.12)]
    m.prism(lid, 1.42, at=(0, 0.6, 0), mat=P["timber_light"], yaw=math.pi / 2, bev=0.015)
    for sx in (-0.45, 0.0, 0.45):
        m.prism([(px * 1.02, py * 1.04) for px, py in lid], 0.07, at=(sx, 0.598, 0), mat=iron, yaw=math.pi / 2, bev=0.004)
        m.box((0.07, 0.6, 0.78), at=(sx, 0.0, 0), mat=iron, bev=0.004)
    for sx in (-1, 1):
        m.ring(0.07, 0.016, at=(sx * 0.7, 0.42, 0), mat=P["rope"], roll=math.pi / 2, segs=10, tube_segs=4)
    m.box((0.12, 0.16, 0.03), at=(0, 0.5, 0.39), mat=P["brass"], bev=0.005)
    return m.build("HOME_chest", loc=(x, 0, 0), ao=0.6, ao_dist=0.4)


# ------------------------------------------------------------------- boat


def sailboat(x):
    """A small gaff-rigged fishing boat (replaces HomeLevel's box boats):
    clinker hull, green topsides with a cream sheer, oxblood under the
    waterline (its origin: the code floats it there), foredeck, thwarts, the
    mast stepped forward with the sail furled on the boom, shrouds and a
    forestay, rudder and tiller. Bow toward +Z."""
    m = MB(290)
    stations = [
        (-2.45, 0.66, 0.95, -0.32, 0.9),
        (-1.7, 0.86, 1.05, -0.45, 0.86),
        (-0.6, 0.93, 1.1, -0.5, 0.8),
        (0.55, 0.9, 1.12, -0.5, 0.74),
        (1.5, 0.74, 1.15, -0.46, 0.6),
        (2.2, 0.42, 1.22, -0.38, 0.4),
        (2.7, 0.04, 1.32, -0.28, 0.15),
    ]
    outer = hull_sections(stations, 7, overlap=0.02)
    green, cream, red = Paint(PAINT, 0x2E4A3A), Paint(PAINT, 0xD9D2BE), Paint(PAINT, 0x6E2A22)
    mid = outer[2]
    strips = []
    for i in range(len(mid) - 1):
        y = (mid[i][1] + mid[i + 1][1]) / 2
        if i < 1 or i >= len(mid) - 2:
            strips.append((cream, 1.0))
        elif y < 0.02:
            strips.append((red, 0.92 + 0.05 * (i % 2)))
        else:
            strips.append((green, 1.0 + 0.05 * ((i % 2) * 2 - 1)))
    m.loft(outer, strips=strips)
    inner_st = [(z + (0.05 if z < 0 else -0.06), b - 0.05, d - 0.04, yk + 0.06, f) for z, b, d, yk, f in stations]
    m.loft(hull_sections(inner_st, 3, overlap=0.0), mat=P["timber_light"], flip=True)
    tr = [(px, py) for px, py, pz in hull_sections([stations[0]], 3, overlap=0.0)[0]]
    m.prism([(px, py) for px, py in reversed(tr)], 0.06, at=(0, 0, -2.43), mat=green, bev=0)
    m.box((0.1, 0.12, 5.0), at=(0, -0.62, 0.1), mat=P["hull_dark"], bev=0.02)
    m.tube([(0, -0.5, 2.55), (0, 0.3, 2.85), (0, 1.12, 2.88)], 0.06, mat=P["hull_dark"], segs=6)
    for side in (-1, 1):
        m.tube([(sec[-1][0] if side > 0 else sec[0][0], sec[-1][1] + 0.012, sec[-1][2]) for sec in outer], 0.04, mat=P["timber"], segs=5)
    # Foredeck: planks between the gunwales from z 1.0 forward.
    secs = []
    for z, b, d, yk, f in stations[3:]:
        y = yk + d - 0.03
        hb = b - 0.03
        secs.append([(-hb, y, z), (0.0, y + 0.05, z), (hb, y, z)])
    m.loft(secs[::-1], mat=P["timber_pale"])
    for z, w in ((-1.6, 1.5), (-0.4, 1.75), (0.45, 1.7)):
        m.plank(w, 0.26, 0.05, at=(0, 0.3, z), mat=P["timber_light"])
    m.box((0.8, 0.03, 3.0), at=(0, -0.3, -0.6), mat=P["timber"], bev=0)
    # Mast, boom with the furled sail, gaff, rigging.
    mz = 1.2
    m.cyl(0.075, 0.05, 5.0, at=(0, -0.45, mz), mat=P["timber_light"], segs=10, bev=0)
    m.cyl(0.05, 0.045, 3.6, at=(0, 1.3, mz - 0.05), mat=P["timber_light"], segs=8, pitch=-math.pi / 2, bev=0)
    m.cyl(0.04, 0.035, 3.1, at=(0, 1.65, mz - 0.05), mat=P["timber_light"], segs=8, pitch=-math.pi / 2 + 0.08, bev=0)
    sail = []
    for k in range(9):
        t = k / 8
        sail.append((0.0, 1.47 + 0.02 * math.sin(t * 9), mz - 0.15 - t * 3.3))
    m.tube(sail, [0.13 + 0.05 * math.sin(math.pi * k / 8) for k in range(9)], mat=P["canvas"], segs=8)
    for k in range(5):
        m.ring(0.17, 0.012, at=(0, 1.47, mz - 0.6 - k * 0.6), mat=P["rope"], pitch=FACING, segs=10, tube_segs=3)
    top = (0, 4.5, mz)
    m.tube([top, (0, 1.15, 2.85)], 0.012, mat=P["rope"], segs=4)
    for side in (-1, 1):
        m.tube([top, (side * 0.9, 0.6, mz - 0.1)], 0.012, mat=P["rope"], segs=4)
    m.tube([top, (0, 1.32, mz - 3.6)], 0.01, mat=P["rope"], segs=4)
    # Rudder and tiller.
    m.prism([(0.0, -0.75), (0.32, -0.6), (0.36, 0.0), (0.0, 0.62)], 0.06, at=(0, 0.0, -2.52), mat=green, yaw=math.pi / 2, bev=0.01)
    m.tube([(0, 0.62, -2.5), (0, 0.75, -2.0), (0, 0.78, -1.5)], 0.035, mat=P["timber_pale"], segs=5)
    # Fenders over the side, a coil of rope in the bottom.
    for side in (-1, 1):
        m.cyl(0.09, 0.09, 0.32, at=(side * 0.93, 0.08, -0.2), mat=P["rope"], segs=8, bev=0.03)
    m.ring(0.2, 0.03, at=(0.2, -0.24, -1.0), mat=P["rope"], segs=12, tube_segs=4)
    return m.build("HOME_sailboat", loc=(x, 0, 0), ao=0.5, ao_dist=0.6, grime=0, ground=False)


# ------------------------------------------------------------------ rocks


def rocks(x):
    """Unit boulders for the cliff foot; the code scales them (1.5 - 5 m) and turns them."""
    for i in range(6):
        m = MB(300 + i)
        m.rock(1.0, mat=P["rock"] if i % 3 else P["rock_dark"], seed=310 + i, squash=0.62 + (i % 3) * 0.08, jitter=0.24, subdiv=2, cuts=6)
        m.build(f"HOME_rock_{i}", loc=(x + i * 3.0, 0, 0), ao=0.45, ao_dist=0.6, grime=0.3, grime_h=0.5)


# ---------------------------------------------------------------- dressing
# What makes the Rest a place people live, not a set: field walls, a kitchen
# garden, the washing out, nets drying, a woodpile, the well, Tib's boat up on
# trestles, and the stone for those the sea took. HomeLevel places them
# (DRESSING there); each origin is its base, centred, and anything you could
# walk into carries a COL_ box.

SOIL = Paint(P["sand"].mat, 0x4A3A2A)
KALE = [Paint(P["moss"].mat, c) for c in (0x4E6B3A, 0x5C7A44, 0x3F5A34)]
LINEN = [Paint(P["cloth"].mat, c) for c in (0xE6E1D3, 0xC9D6DE, 0xB24A3A, 0xD9C27A, 0x8EA6B8)]
GORSE = Paint(P["moss"].mat, 0x3E5530)
BLOOM = Paint(P["paint_yellow"].mat, 0xE3B93A)


def wall_run(x):
    """4 m of dry-stone field wall, 0.9 m high: courses of flat stones,
    battered in, coping stones on edge along the top."""
    m = MB(400)
    rnd = m.rnd
    L = 4.0
    field = [P["stone_dark"], P["rock"], Paint(STONE, 0x8F8A7E), Paint(STONE, 0x9C978A)]
    for course in range(4):
        y = course * 0.2
        w = 0.62 - course * 0.06
        u = -L / 2 + rnd.random() * 0.2
        while u < L / 2 - 0.05:
            sl = min(0.22 + rnd.random() * 0.45, L / 2 - u)
            for side in (-1, 1):
                h = 0.15 + rnd.random() * 0.07
                # Unbevelled: a run's 70-odd course stones would cost 3000 triangles with chamfers.
                m.box((sl - 0.04, h, w / 2 - 0.03), at=(u + sl / 2, y + (0.19 - h) * rnd.random(), side * w / 4), mat=field[int(rnd.random() * len(field))],
                      yaw=(rnd.random() - 0.5) * 0.14, pitch=(rnd.random() - 0.5) * 0.08, roll=(rnd.random() - 0.5) * 0.1, tint=0.72 + 0.28 * rnd.random(), bev=0)
            u += sl
    u = -L / 2
    while u < L / 2 - 0.05:
        t = 0.12 + rnd.random() * 0.06
        m.box((t, 0.24 + rnd.random() * 0.06, 0.4), at=(u + t / 2, 0.8, 0), mat=P["rock"] if rnd.random() < 0.5 else P["stone_dark"], roll=(rnd.random() - 0.5) * 0.25, tint=0.75 + 0.25 * rnd.random(), bev=0.02)
        u += t + 0.01
    for k in range(3):
        m.sphere(0.18 + rnd.random() * 0.1, at=(-1.5 + k * 1.4 + rnd.random() * 0.3, 0.0, (rnd.random() - 0.5) * 0.7), mat=P["moss"], scale=(1.4, 0.45, 1.0), subdiv=1)
    ob = m.build("HOME_wall_run", loc=(x, 0, 0), ao=0.55, ao_dist=0.5, grime=0.2)
    col("COL_wall", (L, 0.95, 0.6), (0, 0, 0), ob)
    return ob


def garden(x):
    """A kitchen garden: dug beds of kale and onions, a bean wigwam, a
    scarecrow in an old oilskin keeping the gulls honest."""
    m = MB(410)
    rnd = m.rnd
    for bz in (-1.3, 0.0, 1.3):
        m.box((5.6, 0.16, 1.0), at=(0, -0.05, bz), mat=SOIL, tint=0.85 + 0.15 * rnd.random(), bev=0.06)
        for k in range(9):
            px = -2.4 + k * 0.6 + (rnd.random() - 0.5) * 0.1
            if bz < 0:
                for leaf in range(4):
                    a = leaf / 4 * math.tau + rnd.random()
                    m.sphere(0.13, at=(px + math.cos(a) * 0.09, 0.14, bz + math.sin(a) * 0.09), mat=KALE[(k + leaf) % 3], scale=(1.0, 0.7, 1.0), subdiv=1)
                m.sphere(0.1, at=(px, 0.2, bz), mat=KALE[1], subdiv=1)
            else:
                for b in range(3):
                    m.tube([(px + (b - 1) * 0.07, 0.1, bz), (px + (b - 1) * 0.12, 0.42 + rnd.random() * 0.12, bz + (rnd.random() - 0.5) * 0.1)], [0.018, 0.006], mat=KALE[2], segs=4)
    # Bean poles, tied at the top, leaves climbing.
    wx, wz = 2.9, -1.9
    for k in range(5):
        a = k / 5 * math.tau
        m.tube([(wx + math.cos(a) * 0.45, 0.0, wz + math.sin(a) * 0.45), (wx, 1.9, wz)], 0.022, mat=P["driftwood"], segs=4)
        for j in range(5):
            t = 0.15 + j * 0.15
            m.sphere(0.09, at=(wx + math.cos(a) * 0.45 * (1 - t), 1.9 * t, wz + math.sin(a) * 0.45 * (1 - t)), mat=KALE[j % 3], scale=(1.0, 0.6, 1.0), subdiv=1)
    # The scarecrow.
    sx, sz = -2.9, 1.9
    m.box((0.08, 1.9, 0.08), at=(sx, 0.0, sz), mat=P["driftwood_dark"], bev=0.01)
    m.box((1.3, 0.07, 0.07), at=(sx, 1.4, sz), mat=P["driftwood_dark"], centered=True, bev=0.01)
    m.lathe([(0.0, 0.85), (0.3, 0.88), (0.34, 1.2), (0.3, 1.45), (0.16, 1.5), (0.0, 1.5)], at=(sx, 0, sz), mat=Paint(P["paint_yellow"].mat, 0x9C8A3C), segs=8)
    for side in (-1, 1):
        m.box((0.42, 0.24, 0.2), at=(sx + side * 0.48, 1.3, sz), mat=Paint(P["paint_yellow"].mat, 0x9C8A3C), roll=side * 0.15, bev=0.02)
    m.uvsphere(0.16, at=(sx, 1.68, sz), mat=P["canvas"], segs=8, rings=6)
    m.cyl(0.24, 0.24, 0.03, at=(sx, 1.8, sz), mat=P["leather"], segs=10)
    m.cyl(0.13, 0.11, 0.16, at=(sx, 1.81, sz), mat=P["leather"], segs=10)
    ob = m.build("HOME_garden", loc=(x, 0, 0), ao=0.5, ao_dist=0.5, grime=0.1)
    col("COL_scarecrow", (0.3, 1.9, 0.3), (sx, 0, sz), ob)
    return ob


def washing_line(x):
    """Two T-posts and a line between them, with the week's wash on it."""
    m = MB(420)
    rnd = m.rnd
    span = 5.2
    for sx in (-1, 1):
        m.box((0.11, 2.15, 0.11), at=(sx * span / 2, 0.0, 0), mat=P["timber"], bev=0.015)
        m.box((0.08, 0.08, 0.7), at=(sx * span / 2, 2.05, 0), mat=P["timber"], centered=True, bev=0.01)
    for lz in (-0.3, 0.3):
        pts = [(-span / 2 + span * t, 2.05 - 0.28 * 4 * t * (1 - t), lz) for t in (k / 10 for k in range(11))]
        m.tube(pts, 0.008, mat=P["rope"], segs=4, cap=False)
    # Sheets and shirts pegged out on the front line, a little breeze in them.
    u = -span / 2 + 0.35
    k = 0
    while u < span / 2 - 0.6:
        w = 0.55 + rnd.random() * 0.75
        t = (u + w / 2 + span / 2) / span
        y = 2.05 - 0.28 * 4 * t * (1 - t)
        h = 0.7 + rnd.random() * 0.5
        m.box((w, h, 0.02), at=(u + w / 2, y - h, -0.3 + 0.03), mat=LINEN[k % len(LINEN)], pitch=0.08 + rnd.random() * 0.08, tint=0.9 + 0.1 * rnd.random(), bev=0)
        for e in (0.06, w - 0.06):
            m.box((0.025, 0.07, 0.03), at=(u + e, y - 0.04, -0.3), mat=P["timber_pale"], bev=0)
        u += w + 0.12
        k += 1
    m.box((0.5, 0.35, 0.35), at=(-span / 2 + 0.6, 0.0, 0.6), mat=P["rope"], bev=0.04)
    ob = m.build("HOME_washing_line", loc=(x, 0, 0), ao=0.45, ao_dist=0.5, grime=0.05)
    for sx in (-1, 1):
        col(f"COL_post{(sx + 1) // 2}", (0.2, 2.2, 0.2), (sx * span / 2, 0, 0), ob)
    return ob


def net_frame(x):
    """A drying frame by the dock: two posts and a pole with a net hung over
    it in deep folds, cork floats along its edge."""
    m = MB(430)
    rnd = m.rnd
    W, H = 3.6, 2.0
    for sx in (-1, 1):
        m.box((0.13, H + 0.1, 0.13), at=(sx * W / 2, 0.0, 0), mat=P["driftwood_dark"], bev=0.015)
    m.cyl(0.06, 0.06, W + 0.5, at=(0, H, 0), mat=P["driftwood"], roll=ACROSS, centered=True, segs=8)
    netcol = Paint(P["cloth"].mat, 0x4A5046)
    # Open mesh, not a sheet: cords along and across, so the sea shows through.
    NI, NJ = 17, 8
    for side in (-1, 1):
        rows = []
        for j in range(NJ):
            t = j / (NJ - 1)
            row = []
            for i in range(NI):
                s = i / (NI - 1)
                u = -W / 2 + 0.1 + (W - 0.2) * s
                fold = 0.08 * math.sin(s * 20 + side) * t
                row.append((u, H - 0.06 - t * (H - 0.35) - 0.1 * math.sin(s * math.pi) * t, side * (0.08 + t * 0.32) + fold))
            rows.append(row)
        for row in rows:
            m.tube(row, 0.012, mat=netcol, segs=3)
        for i in range(NI):
            m.tube([row[i] for row in rows], 0.012, mat=netcol, segs=3)
        for i in range(0, NI, 4):
            px, py, pz = rows[-1][i]
            m.sphere(0.06, at=(px, py - 0.03, pz), mat=Paint(P["cloth"].mat, 0xB08A55), scale=(1.0, 0.8, 1.0), subdiv=1)
    # Where it folds over the pole the net bunches into a rope of its own.
    m.tube([(-W / 2 + 0.05 + (W - 0.1) * k / 10, H + 0.02 + 0.025 * math.sin(k * 2.3), 0.0) for k in range(11)], 0.085, mat=netcol, segs=6)
    ob = m.build("HOME_net_frame", loc=(x, 0, 0), ao=0.5, ao_dist=0.5, grime=0.1)
    col("COL_net_frame", (W + 0.2, H, 0.8), (0, 0, 0), ob)
    return ob


def woodpile(x):
    """Split logs stacked between two posts under a scrap of tarred canvas, and
    the chopping block with the axe left in it."""
    m = MB(440)
    rnd = m.rnd
    L, rows = 2.4, 5
    for sx in (-1, 1):
        m.box((0.1, 1.15, 0.1), at=(sx * L / 2, 0.0, 0.0), mat=P["timber"], bev=0.01)
    for r in range(rows):
        n = 9 - (r % 2)
        for i in range(n):
            px = -L / 2 + 0.16 + (L - 0.32) * (i + (0.5 if r % 2 else 0.0)) / 9
            m.lathe([(0.0, -0.32), (0.11, -0.32), (0.11, 0.32), (0.0, 0.32)], at=(px, 0.12 + r * 0.2, 0.0), mat=P["timber_light"] if (i + r) % 3 else P["timber_pale"], segs=6, pitch=math.pi / 2, tint=0.85 + 0.25 * rnd.random(), arc=None)
    m.box((L + 0.3, 0.03, 0.9), at=(0, 1.13, 0.0), mat=P["tar"], pitch=0.15, centered=True, bev=0)
    # Chopping block and axe.
    bx, bz = L / 2 + 0.8, 0.5
    m.cyl(0.28, 0.3, 0.5, at=(bx, 0.0, bz), mat=P["timber"], segs=10, bev=0.02)
    m.cyl(0.25, 0.25, 0.012, at=(bx, 0.5, bz), mat=P["timber_pale"], segs=10, bev=0)
    m.box((0.05, 0.75, 0.05), at=(bx + 0.1, 0.48, bz), mat=P["timber_pale"], roll=-0.5, bev=0.005)
    m.box((0.2, 0.12, 0.03), at=(bx - 0.04, 0.47, bz), mat=P["iron"], roll=-0.5, bev=0.005)
    for k in range(5):
        a = rnd.random() * math.tau
        m.box((0.3, 0.06, 0.1), at=(bx + math.cos(a) * 0.55, 0.0, bz + math.sin(a) * 0.55), mat=P["timber_pale"], yaw=a, bev=0.01)
    ob = m.build("HOME_woodpile", loc=(x, 0, 0), ao=0.55, ao_dist=0.4, grime=0.15)
    col("COL_woodpile", (L + 0.3, 1.2, 0.8), (0, 0, 0), ob)
    col("COL_block", (0.6, 0.55, 0.6), (bx, 0, bz), ob)
    return ob


def well(x):
    """The village well: a round stone kerb, a little slate roof on two posts,
    the winch and its rope, a bucket on the kerb."""
    m = MB(450)
    rnd = m.rnd
    R = 0.85
    for k in range(14):
        a = k / 14 * math.tau
        for c in range(3):
            aa = a + (0.5 / 14 * math.tau if c % 2 else 0)
            m.box((0.38, 0.24, 0.3), at=(math.cos(aa) * R, c * 0.25, math.sin(aa) * R), mat=P["stone_dark"] if (k + c) % 3 else P["rock"], yaw=-aa, tint=0.8 + 0.2 * rnd.random(), bev=0.03)
    m.cyl(R - 0.12, R - 0.12, 0.02, at=(0, 0.55, 0), mat=WATER, segs=16, bev=0)
    for sx in (-1, 1):
        m.box((0.13, 2.1, 0.13), at=(sx * (R + 0.05), 0.0, 0), mat=P["timber"], bev=0.015)
    m.cyl(0.08, 0.08, 2 * R + 0.3, at=(0, 1.3, 0), mat=P["timber_light"], roll=ACROSS, centered=True, segs=8)
    m.tube([(0.2, 1.3, 0.0), (0.2, 0.95, 0.0)], 0.015, mat=P["rope"], segs=4)
    m.box((0.2, 0.06, 0.04), at=(R + 0.2, 1.3, 0.0), mat=P["iron"], centered=True, bev=0)
    for side in (-1, 1):
        m.box((2 * R + 0.7, 0.06, 0.9), at=(0, 2.25, side * 0.34), mat=SLATE, pitch=-side * 0.55, centered=True, bev=0.01)
    m.lathe([(0.0, 0.0), (0.13, 0.0), (0.16, 0.24), (0.0, 0.24)], at=(R * 0.75, 0.75, R * 0.55), mat=P["timber"], segs=8, staves=0.15)
    ob = m.build("HOME_well", loc=(x, 0, 0), ao=0.55, ao_dist=0.5, grime=0.15)
    col("COL_well", (2 * R + 0.3, 0.8, 2 * R + 0.3), (0, 0, 0), ob)
    return ob


def boat_trestles(x):
    """Tib's other boat, upturned on two trestles while he mends her: a gap of
    fresh planks in her side, the rest of them on the grass with the tar pot."""
    m = MB(460)
    rnd = m.rnd
    # Round bilges (low fullness) so she reads as a hull, not a box, upside down.
    st = [(-2.0, 0.6, 0.6, 0.0, 0.55), (-1.2, 0.8, 0.64, 0.0, 0.5), (0.0, 0.86, 0.66, 0.0, 0.45), (1.2, 0.74, 0.69, 0.0, 0.38), (1.95, 0.34, 0.74, 0.0, 0.25), (2.15, 0.04, 0.78, 0.0, 0.1)]
    base = 0.95
    shell = hull_sections(st, 6, overlap=0.02)
    flipped = []
    for sec, (_z, _b, d, yk, _f) in zip(shell, st):
        flipped.append([(px, base + yk + d - py, pz) for px, py, pz in sec])
    strakes = [(P["hull"], 1.0 if k % 2 else 0.85) for k in range(len(flipped[0]) - 1)]
    strakes[2] = (P["timber_pale"], 1.0)
    m.loft(flipped, strips=strakes, flip=True)
    # Her transom board, closing the stern.
    z0, b0, d0, _yk0, f0 = st[0]
    half = []
    for k in range(9):
        u = k / 8
        half.append((2 * (1 - u) * u * b0 * f0 + u * u * b0, base + d0 - u * u * d0))
    m.prism(list(reversed(half)) + [(-hx, hy) for hx, hy in half[1:]], 0.05, at=(0, 0, z0 + 0.03), mat=P["hull_dark"], bev=0)
    m.tube([(0.0, base + d + 0.03, z) for z, _b, d, _yk, _f in st], 0.05, mat=P["hull_dark"], segs=6)
    for tz in (-1.2, 1.1):
        for sx in (-1, 1):
            m.box((0.08, base + 0.05, 0.08), at=(sx * 0.78, 0.0, tz), mat=P["timber"], roll=sx * 0.18, bev=0.01)
        m.box((1.95, 0.1, 0.12), at=(0, base - 0.05, tz), mat=P["timber"], bev=0.01)
    for k in range(4):
        m.plank(2.2, 0.16, 0.035, at=(1.2 + k * 0.04, 0.035 * k, 1.9 + k * 0.05), mat=P["timber_pale"], yaw=0.3 + k * 0.05, warp=0.05)
    m.cyl(0.13, 0.12, 0.22, at=(-1.0, 0.0, 1.7), mat=P["tar"], segs=10)
    m.box((0.03, 0.4, 0.03), at=(-0.98, 0.12, 1.7), mat=P["timber_pale"], roll=0.4, bev=0)
    ob = m.build("HOME_boat_trestles", loc=(x, 0, 0), ao=0.55, ao_dist=0.6, grime=0.1)
    col("COL_boat", (1.9, 1.7, 4.4), (0, 0, 0), ob)
    return ob


def memorial(x):
    """The stone for those the sea took: a tall slab with a slate plaque, a
    ring of small stones the villagers leave, jam-jar lights and wild flowers."""
    m = MB(470)
    rnd = m.rnd
    m.box((0.9, 2.1, 0.3), at=(0, -0.1, 0), mat=P["stone"], roll=0.03, bev=0.06)
    m.box((0.56, 0.7, 0.04), at=(0, 1.0, 0.16), mat=SLATE, bev=0.01)
    for k in range(5):
        m.box((0.34 - k * 0.03, 0.025, 0.01), at=(0, 1.55 - k * 0.12, 0.185), mat=Paint(STONE, 0xBFB8A8), bev=0)
    for k in range(22):
        a = k / 22 * math.tau + rnd.random() * 0.2
        r = 0.95 + rnd.random() * 0.25
        m.rock(0.08 + rnd.random() * 0.07, at=(math.cos(a) * r, 0.0, math.sin(a) * r * 0.75 + 0.15), mat=P["stone"] if k % 3 else P["rock"], seed=470 + k, subdiv=1, squash=0.7)
    for k, (jx, jz) in enumerate(((-0.55, 0.45), (0.15, 0.6), (0.6, 0.38))):
        m.lathe([(0.0, 0.0), (0.06, 0.0), (0.065, 0.13), (0.045, 0.16), (0.0, 0.16)], at=(jx, 0.0, jz), mat=P["glass_amber"], segs=8)
    for k in range(9):
        a = rnd.random() * math.tau
        r = 0.35 + rnd.random() * 0.4
        fx, fz = math.cos(a) * r, 0.3 + math.sin(a) * r * 0.5
        m.tube([(fx, 0.0, fz), (fx + 0.02, 0.22, fz)], 0.006, mat=P["moss"], segs=3)
        m.sphere(0.035, at=(fx + 0.02, 0.24, fz), mat=BLOOMS[k % len(BLOOMS)], subdiv=0)
    ob = m.build("HOME_memorial", loc=(x, 0, 0), ao=0.55, ao_dist=0.5, grime=0.15)
    col("COL_memorial", (1.0, 2.0, 0.45), (0, 0, 0), ob)
    return ob


def gorse(x):
    """A gorse bush: a mound of dark spiny clumps, yellow flower in it."""
    m = MB(480)
    rnd = m.rnd
    for k in range(9):
        a = rnd.random() * math.tau
        d = rnd.random() * 0.55
        r = 0.32 + rnd.random() * 0.22
        m.rock(r, at=(math.cos(a) * d, r * 0.25, math.sin(a) * d), mat=GORSE, seed=480 + k, subdiv=1, squash=0.75, jitter=0.45, tint=0.85 + 0.25 * rnd.random())
    for k in range(26):
        a = rnd.random() * math.tau
        d = rnd.random() * 0.7
        m.sphere(0.04, at=(math.cos(a) * d * 0.8, 0.2 + rnd.random() * 0.28, math.sin(a) * d * 0.8), mat=BLOOM, subdiv=0)
    return m.build("HOME_gorse", loc=(x, 0, 0), ao=0.5, ao_dist=0.4, grime=0.1)


TAU = math.tau


def barnacles(m, rnd, center, spread, count, size=0.045):
    """Little volcano cones scattered about `center` (piles, hulls)."""
    cx, cy, cz = center
    for _ in range(count):
        r = size * (0.6 + rnd.random() * 0.7)
        at = (cx + (rnd.random() - 0.5) * 2 * spread[0], cy + (rnd.random() - 0.5) * 2 * spread[1], cz + (rnd.random() - 0.5) * 2 * spread[2])
        m.lathe([(r, 0), (r * 0.75, r * 0.7), (r * 0.35, r * 0.95), (r * 0.25, r * 0.7), (0, r * 0.6)], at=at, mat=P["barnacle"], segs=6, jit=0.1)


def seaweed_clump(m, rnd, at, count=5, length=0.7):
    """Strands of weed lying out from a point."""
    x0, y0, z0 = at
    for i in range(count):
        a = rnd.random() * TAU
        L = length * (0.6 + rnd.random() * 0.6)
        pts = [(x0 + math.cos(a) * L * t + math.sin(t * 6 + i) * 0.05, y0 + 0.02 + math.sin(t * math.pi) * 0.04, z0 + math.sin(a) * L * t) for t in (k / 4 for k in range(5))]
        m.tube(pts, [0.03, 0.035, 0.03, 0.02, 0.008], mat=P["kelp"] if i % 2 else P["kelp_dark"], segs=4)


# ------------------------------------------------------------ the Rest's plots
# Each plot the player rebuilds has a ruin and the building that replaces it,
# both with their origin at the plot's base, front toward +Z, and COL_ boxes
# for what's solid. The home map (home_map.py) stands them on PLOT_ markers;
# the game shows one or the other and raises the building as materials come
# in. Children the code looks for: station (where you work it), smoke.

JETTY_LEN = 26.0
HEAD = 21.5  # the T-head starts here
DECK_Y = 2.7  # the deck stands this high in the cove (home_map.py), above any tide


def stone_patch(m, rnd, x0, x1, y0, y1, z, along_x=True, n=5, face=1):
    """Patches where the render has fallen off a wall and the stone shows."""
    for _ in range(n):
        w, h = 0.25 + rnd.random() * 0.5, 0.15 + rnd.random() * 0.35
        u = x0 + w / 2 + rnd.random() * max(0.01, x1 - x0 - w)
        v = y0 + rnd.random() * max(0.01, y1 - y0 - h)
        at = (u, v, z + face * 0.012) if along_x else (z + face * 0.012, v, u)
        m.box((w, h, 0.03) if along_x else (0.03, h, w), at=at, mat=QUOIN, tint=0.75 + 0.2 * rnd.random(), bev=0.01)


def jetty():
    """The new jetty: a plank deck on three stringers and pile bents every 3.2 m,
    braced in pairs, out to a T-head where the boat ties up; kerbs, bollards,
    a ladder down the end and rope fenders on the mooring side."""
    m = MB(800)
    rnd = m.rnd
    z = 0.12
    while z < JETTY_LEN - 0.1:
        w = 0.22 + rnd.random() * 0.03
        half = 3.0 if z > HEAD else 1.5
        m.box((2 * half + (rnd.random() - 0.5) * 0.08, 0.06, w), at=((rnd.random() - 0.5) * 0.04, -0.06, z), mat=P["timber"] if rnd.random() < 0.75 else P["timber_light"], bev=0.012, tint=0.8 + 0.3 * rnd.random(), yaw=(rnd.random() - 0.5) * 0.012)
        z += w + 0.03
    for x in (-1.2, 0.0, 1.2):
        m.box((0.16, 0.22, JETTY_LEN - 0.1), at=(x, -0.28, JETTY_LEN / 2), mat=P["timber"], tint=0.8, bev=0.02)
    for x in (-2.6, 2.6):
        m.box((0.16, 0.22, JETTY_LEN - HEAD), at=(x, -0.28, (JETTY_LEN + HEAD) / 2), mat=P["timber"], tint=0.8, bev=0.02)
    for x in (-1.55, 1.55):
        m.box((0.12, 0.13, HEAD - 0.1), at=(x, 0.0, HEAD / 2), mat=P["timber_light"], tint=0.85, bev=0.02)
    for x in (-3.05, 3.05):
        m.box((0.12, 0.13, JETTY_LEN - HEAD), at=(x, 0.0, (JETTY_LEN + HEAD) / 2), mat=P["timber_light"], tint=0.85, bev=0.02)
    m.box((6.2, 0.13, 0.12), at=(0, 0.0, JETTY_LEN - 0.05), mat=P["timber_light"], tint=0.85, bev=0.02)
    bents = [1.6 + i * 3.2 for i in range(7)] + [HEAD + 1.0, JETTY_LEN - 0.6]
    for k, bz in enumerate(bents):
        wide = bz > HEAD
        xs = (-2.8, -1.35, 1.35, 2.8) if wide else (-1.35, 1.35)
        m.box((6.4 if wide else 3.4, 0.3, 0.26), at=(0, -0.68, bz), mat=P["timber"], tint=0.72, bev=0.025)
        for px in xs:
            m.cyl(0.23, 0.19, 11.5 - 0.62, at=(px, -11.5, bz), mat=P["hull"], segs=10)
            barnacles(m, rnd, (px, -2.4, bz), (0.24, 0.5, 0.24), 3)
        for a, b in (((-1.35, -0.85), (1.35, -3.0)), ((1.35, -0.85), (-1.35, -3.0))):
            pts = [(a[0], a[1], bz + 0.25), (b[0], b[1], bz + 0.25)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            m.box((math.hypot(dx, dy), 0.16, 0.08), at=((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, bz + 0.25), mat=P["timber"], roll=math.atan2(dy, dx), centered=True, tint=0.7, bev=0.015)
    # Ladder down the end, east side of the head, into the water.
    LX, LZ = 2.2, JETTY_LEN + 0.07
    for x in (LX - 0.25, LX + 0.25):
        m.box((0.07, 4.6, 0.08), at=(x, -4.5, LZ), mat=P["iron"], bev=0.01)
    for k in range(11):
        m.cyl(0.02, 0.02, 0.5, at=(LX, -4.2 + k * 0.38, LZ), mat=P["iron"], roll=ACROSS, centered=True, segs=6, bev=0)
    # Rope fenders hung on the mooring side.
    for fz in (22.6, 24.4):
        m.tube([(3.12, 0.05, fz), (3.18, -0.3, fz)], 0.012, mat=P["rope"], segs=4)
        m.cyl(0.11, 0.11, 0.42, at=(3.2, -0.75, fz), mat=P["rope"], segs=8, bev=0.04)
    ob = m.build("HOME_jetty", loc=(200, DECK_Y, 0), ao=0.6, ao_dist=0.8, grime=0.0, ground=False, tideline=True)
    for k, (bx, bz) in enumerate(((-2.75, 22.0), (2.75, 22.4), (2.75, 25.6), (-2.75, 25.6), (-1.3, 10.0))):
        kit.place(T, "bollard", f"jetty_bollard{k}", (bx, 0, bz), yaw=k * 1.3, parent=ob, scale=0.8)
    kit.place(T, "rope_coil", "jetty_rope0", (-1.9, 0, 24.0), yaw=0.6, parent=ob)
    kit.place(T, "lobster_pot", "jetty_pot0", (-2.3, 0, 21.9), yaw=0.3, parent=ob)
    c = MB(801)
    c.box((3.1, 0.25, HEAD + 0.1), at=(0, -0.25, (HEAD + 0.1) / 2), bev=0)
    c.box((6.2, 0.25, JETTY_LEN - HEAD), at=(0, -0.25, (JETTY_LEN + HEAD) / 2), bev=0)
    c.build("COL_jetty", parent=ob, ao=0, grime=0, ground=False)
    # Where you take the boat from: the mooring side, facing the berth.
    kit.empty("station", (2.6, 0.0, 23.5), yaw=-math.pi / 2, parent=ob, size=0.3)
    return ob


def jetty_ruin():
    """The old jetty, what the storms left: a stub of rotten deck at the beach,
    a line of pile stumps walking out into the cove, a cap beam hanging off two."""
    m = MB(810)
    rnd = m.rnd
    z = 0.12
    while z < 3.0:
        w = 0.22 + rnd.random() * 0.03
        if rnd.random() < 0.8:
            m.box((3.0 + (rnd.random() - 0.5) * 0.3, 0.06, w), at=((rnd.random() - 0.5) * 0.2, -0.06 - rnd.random() * 0.03, z), mat=P["driftwood_dark"], bev=0.012, tint=0.75 + 0.25 * rnd.random(), yaw=(rnd.random() - 0.5) * 0.08, roll=(rnd.random() - 0.5) * 0.06)
        z += w + 0.03 + rnd.random() * 0.06
    for x in (-1.2, 1.2):
        m.box((0.16, 0.22, 3.4), at=(x, -0.28, 1.6), mat=P["hull_dark"], tint=0.8, bev=0.02)
    # Stumps: lower and more broken the further out they stand.
    for k, bz in enumerate([1.6 + i * 3.2 for i in range(8)]):
        for px in (-1.35, 1.35):
            if rnd.random() < 0.18:
                continue
            top = -0.7 - k * 0.32 - rnd.random() * 0.9
            lean = (rnd.random() - 0.5) * 0.18
            m.cyl(0.22, 0.17, top + 11.5, at=(px, -11.5, bz), mat=P["hull_dark"], segs=9, roll=lean)
            m.cyl(0.15, 0.04, 0.22, at=(px - math.sin(lean) * (top + 11.5), top, bz), mat=P["driftwood_dark"], segs=7, roll=lean, bev=0)
            barnacles(m, rnd, (px, top - 0.9, bz), (0.23, 0.6, 0.23), 3)
    m.box((3.4, 0.26, 0.24), at=(0.2, -0.95, 4.8), mat=P["hull_dark"], roll=0.22, centered=True, tint=0.75, bev=0.025)
    seaweed_clump(m, rnd, (0.3, -1.2, 6.5), count=4, length=0.7)
    ob = m.build("HOME_jetty_ruin", loc=(232, DECK_Y, 0), ao=0.6, ao_dist=0.7, grime=0.0, ground=False, tideline=True)
    c = MB(811)
    c.box((3.0, 0.25, 3.0), at=(0, -0.25, 1.5), bev=0)
    c.build("COL_jetty_ruin", parent=ob, ao=0, grime=0, ground=False)
    return ob


def cottage_ruin(name, x, seed, wall, chimney=1):
    """A cottage the sea wind unroofed, on the 6 x 5 m footprint it will be
    rebuilt on: render falling off rubble walls at broken heights, the door gap
    and window holes, one gable and its chimney still standing, rafters fallen
    in, slates and rubble round the foot of the walls, nettles inside."""
    m = MB(seed)
    rnd = m.rnd
    c = MB(seed + 1)
    W, D, TH = 6.0, 5.0, 0.4
    hw, hd = W / 2, D / 2
    weathered = Paint(wall.mat, wall.color)
    m.box((W + 0.04, 0.42, D + 0.04), mat=QUOIN, bev=0.02, tint=0.85)

    def run(u0, u1, h, fixed, along_x, face):
        if h <= 0.05:
            return
        L = u1 - u0
        size = (L, h, TH) if along_x else (TH, h, L)
        at = ((u0 + u1) / 2, 0.42, fixed) if along_x else (fixed, 0.42, (u0 + u1) / 2)
        m.box(size, at=at, mat=weathered, tint=0.78 + 0.12 * rnd.random(), bev=0.04)
        c.box(size, at=at, bev=0)
        stone_patch(m, rnd, u0, u1, 0.6, 0.42 + h - 0.2, fixed + face * TH / 2, along_x=along_x, n=2 + int(L), face=face)
        # A ragged top: a few stones standing proud.
        for _ in range(int(L * 2)):
            u = u0 + rnd.random() * L
            s = 0.18 + rnd.random() * 0.16
            at2 = (u, 0.42 + h - 0.04, fixed) if along_x else (fixed, 0.42 + h - 0.04, u)
            m.box((s, 0.14, TH * 0.8) if along_x else (TH * 0.8, 0.14, s), at=at2, mat=QUOIN, yaw=(rnd.random() - 0.5) * 0.2, tint=0.75 + 0.2 * rnd.random(), bev=0.03)

    zf, zb = hd - TH / 2, -hd + TH / 2
    # Front: corner piers, sills under the window holes, the door gap.
    for u0, u1, h in ((-hw, -2.45, 2.2), (-2.45, -1.35, 0.9), (-1.35, -0.55, 1.9), (0.55, 1.35, 2.5), (1.35, 2.45, 0.9), (2.45, hw, 2.75)):
        run(u0, u1, h + (rnd.random() - 0.5) * 0.2, zf, True, 1)
    m.box((1.4, 0.12, 0.45), at=(0, 0.0, hd + 0.22), mat=QUOIN, bev=0.02)
    # Back, broken low in the middle.
    for u0, u1, h in ((-hw, -1.0, 2.3), (-1.0, 0.7, 1.2), (0.7, hw, 1.9)):
        run(u0, u1, h + (rnd.random() - 0.5) * 0.2, zb, True, -1)
    # The gable end still stands; the other end is down to the sill.
    gx = chimney * (hw - TH / 2)
    run(-hd + TH, hd - TH, 2.78, gx, False, chimney)
    m.prism([(-hd + 0.3, 0.0), (hd - 0.3, 0.0), (0.4, 1.5), (-0.6, 1.2)], TH, at=(gx, 3.2, 0), mat=weathered, yaw=math.pi / 2, bev=0.04, tint=0.82)
    m.box((0.9, 2.6, 0.75), at=(gx - chimney * 0.05, 3.2, 0), mat=weathered, bev=0.03, tint=0.8)
    m.box((1.04, 0.12, 0.89), at=(gx - chimney * 0.05, 5.8, 0), mat=QUOIN, bev=0.02)
    m.cyl(0.12, 0.1, 0.36, at=(gx - chimney * 0.05 + 0.2, 5.92, 0), mat=TERRACOTTA, segs=10, bev=0.01)
    ox = -chimney * (hw - TH / 2)
    run(-hd + TH, -0.4, 1.4, ox, False, -chimney)
    run(-0.4, hd - TH, 0.8, ox, False, -chimney)
    # Rafters fallen in, slates and rubble about the walls, weeds where the floor was.
    for k in range(4):
        m.box((0.13, 0.13, 3.9), at=(-1.9 + k * 1.25, 0.5 + 0.3 * k * (k % 2), -0.3), mat=P["driftwood_dark"], pitch=0.25 + 0.1 * k, roll=(rnd.random() - 0.5) * 0.4, centered=True, bev=0.02)
    for _ in range(26):
        a = rnd.random() * TAU
        r = 2.4 + rnd.random() * 1.6
        sx, sz = math.cos(a) * r * 1.15, math.sin(a) * r * 0.9
        if abs(sx) < 0.8 and sz > 0:
            continue
        m.box((0.32, 0.03, 0.22), at=(sx, rnd.random() * 0.05, sz), mat=SLATE, yaw=rnd.random() * TAU, pitch=(rnd.random() - 0.5) * 0.4, tint=0.8 + 0.25 * rnd.random(), bev=0)
    for k in range(14):
        a = rnd.random() * TAU
        r = 2.9 + rnd.random() * 0.8
        m.rock(0.16 + rnd.random() * 0.16, at=(math.cos(a) * r * 1.1, 0.0, math.sin(a) * r * 0.9), mat=QUOIN if k % 2 else weathered, seed=seed + 20 + k, squash=0.7)
    for k in range(5):
        kit.place(T, "dune_grass", f"{name}_weed{k}", ((rnd.random() - 0.5) * 3.6, 0.42, (rnd.random() - 0.5) * 2.8), yaw=rnd.random() * 6, parent=None, scale=0.5 + rnd.random() * 0.4)
    ob = m.build(name, loc=(x, 0, 0), ao=0.6, ao_dist=0.9, grime=0.25, grime_h=1.0)
    for o in [o for o in bpy_objects() if o.name.startswith(f"{name}_weed") and o.parent is None]:
        o.parent = ob
    c.build("COL_ruin", parent=ob, ao=0, grime=0, ground=False)
    return ob


def net_loft(name, x, ruined):
    """The net loft, 7 x 5 m: a rubble-stone ground floor with wide doors, a
    tarred timber loft over it with its own doors and a hoist beam, a slate
    roof, and a stone stair up the side. Nets hung to dry, floats, oars.
    Ruined: the walls broken down, the loft burnt and fallen in."""
    m = MB(820 + int(ruined))
    rnd = m.rnd
    c = MB(830 + int(ruined))
    W, D, G, U = 7.0, 5.0, 2.7, 2.5  # width, depth, ground storey, upper storey
    hw, hd = W / 2, D / 2
    TAR = P["tar"]
    boards = Paint(P["hull"].mat, 0x3A322B)
    m.box((W + 0.1, 0.35, D + 0.1), mat=QUOIN, bev=0.02)
    if ruined:
        heights = ((-hw, -1.2, 2.1), (-1.2, 1.2, 0.0), (1.2, hw, 1.5))
        for u0, u1, h in heights:
            if h > 0:
                m.box((u1 - u0, h, 0.5), at=((u0 + u1) / 2, 0.35, hd - 0.25), mat=P["stone_dark"], tint=0.8 + 0.15 * rnd.random(), bev=0.05)
                c.box((u1 - u0, h, 0.5), at=((u0 + u1) / 2, 0.35, hd - 0.25), bev=0)
        for fixed, h in ((-hd + 0.25, 2.4),):
            m.box((W, h, 0.5), at=(0, 0.35, fixed), mat=P["stone_dark"], tint=0.82, bev=0.05)
            c.box((W, h, 0.5), at=(0, 0.35, fixed), bev=0)
        for gx, h in ((-hw + 0.25, 2.5), (hw - 0.25, 1.1)):
            m.box((0.5, h, D - 1.0), at=(gx, 0.35, 0), mat=P["stone_dark"], tint=0.8, bev=0.05)
            c.box((0.5, h, D - 1.0), at=(gx, 0.35, 0), bev=0)
        # The loft's floor joists burnt through and fallen, the hoist beam down in the grass.
        for k in range(5):
            m.box((0.16, 0.18, 4.4), at=(-2.6 + k * 1.3, 0.6 + (k % 2) * 0.5, 0.0), mat=Paint(P["tar"].mat, 0x2A2420), pitch=(0.3 if k % 2 else -0.2), roll=(rnd.random() - 0.5) * 0.3, centered=True, bev=0.02)
        m.box((0.2, 0.2, 3.2), at=(1.6, 0.1, hd + 1.4), mat=P["driftwood_dark"], yaw=0.6, centered=True, bev=0.02)
        # Stair stub up the side.
        for k in range(4):
            m.box((1.0, 0.3 * (k + 1), 0.4), at=(hw + 0.55, 0.0, hd - 0.6 - k * 0.4), mat=P["stone_dark"], tint=0.85, bev=0.03)
        for k in range(16):
            a = rnd.random() * TAU
            r = 3.2 + rnd.random() * 1.4
            m.rock(0.16 + rnd.random() * 0.18, at=(math.cos(a) * r, 0.0, math.sin(a) * r * 0.8), mat=P["stone_dark"], seed=840 + k, squash=0.7)
        ob = m.build(name, loc=(x, 0, 0), ao=0.6, ao_dist=0.9, grime=0.25, grime_h=1.0)
        c.build("COL_ruin", parent=ob, ao=0, grime=0, ground=False)
        return ob

    # Ground storey: rubble stone, quoined corners, the wide doors (one leaf open).
    m.box((W, G - 0.35, D), at=(0, 0.35, 0), mat=P["stone_dark"], bev=0.03)
    stone_patch(m, rnd, -hw, hw, 0.5, G - 0.3, hd, n=10)
    for sx in (-1, 1):
        for k in range(6):
            lx, lz = (0.5, 0.28) if k % 2 == 0 else (0.28, 0.5)
            m.box((lx, 0.36, lz), at=(sx * (hw - lx / 2 + 0.03), 0.38 + k * 0.38, hd - lz / 2 + 0.03), mat=QUOIN, bev=0.025, jit=0.08)
    m.box((2.4, 2.2, 0.1), at=(0, 0.35, hd + 0.0), mat=P["tar"], bev=0)
    m.box((2.6, 0.24, 0.2), at=(0, 2.4, hd + 0.04), mat=P["timber"], bev=0.02)
    for k in range(5):
        m.box((0.23, 2.1, 0.06), at=(-1.12 + k * 0.24, 0.35, hd + 0.06), mat=P["timber_light"], bev=0.008, tint=0.9 + 0.08 * (k % 2))
    for k in range(5):
        m.box((0.23, 2.1, 0.06), at=(1.35 + 0.18 * k * math.cos(1.2), 0.35, hd + 0.2 + k * 0.22), mat=P["timber_light"], yaw=-1.2, bev=0.008, tint=0.9)
    # Upper storey: tarred boards, jettied out a little, loft doors over the ground doors.
    m.box((W + 0.3, 0.2, D + 0.3), at=(0, G, 0), mat=P["timber"], bev=0.02)
    for k in range(int(W / 0.24)):
        u = -hw - 0.1 + k * 0.24
        m.box((0.23, U, 0.05), at=(u + 0.12, G + 0.2, hd + 0.13), mat=boards, tint=0.85 + 0.25 * rnd.random(), bev=0.006)
        m.box((0.23, U, 0.05), at=(u + 0.12, G + 0.2, -hd - 0.13), mat=boards, tint=0.85 + 0.25 * rnd.random(), bev=0.006)
    m.box((W + 0.2, U, D + 0.2), at=(0, G + 0.2, 0), mat=boards, bev=0.01)
    m.box((1.5, 1.8, 0.08), at=(0, G + 0.4, hd + 0.17), mat=P["timber_pale"], bev=0.01)
    m.box((1.7, 0.14, 0.12), at=(0, G + 2.2, hd + 0.2), mat=P["timber"], bev=0.01)
    # Gables and the slate roof (ridge along X).
    rise = 2.0
    for s in (-1, 1):
        m.prism([(-hd - 0.15, 0.0), (hd + 0.15, 0.0), (0.0, rise)], 0.3, at=(s * (hw - 0.0), G + 0.2 + U, 0), mat=boards, yaw=math.pi / 2, bev=0.02)
    pitch = math.atan2(rise, hd + 0.15)
    L = math.hypot(hd + 0.15, rise) + 0.45
    cp, sp = math.cos(pitch), math.sin(pitch)
    top = G + 0.2 + U + rise
    for s in (-1, 1):
        m.box((W + 0.7, 0.14, L), at=(0, top - (L / 2) * sp + 0.07 * cp, s * (L / 2) * cp + s * 0.07 * sp), mat=SLATE, pitch=s * pitch, centered=True, bev=0.02)
        for k in range(10):
            d = 0.25 + (L - 0.35) * k / 9
            shade = 0.85 + rnd.random() * 0.2
            m.box((W + 0.72, 0.035, 0.36), at=(0, top - d * sp + 0.155 * cp, s * (d * cp + 0.155 * sp)), mat=SLATE, pitch=s * (pitch - 0.06), centered=True, bev=0, tint=shade)
    m.cyl(0.12, 0.12, W + 0.76, at=(0, top + 0.13, 0), mat=RIDGE, segs=8, roll=ACROSS, centered=True, bev=0)
    # Hoist beam out of the front gable apex, a pulley, the rope down to a hanging net.
    m.box((0.2, 0.2, 1.6), at=(0, G + U, hd + 0.75), mat=P["timber"], centered=True, bev=0.02)
    m.cyl(0.14, 0.14, 0.08, at=(0, G + U - 0.2, hd + 1.4), mat=P["iron"], roll=ACROSS, centered=True, segs=12, bev=0)
    m.tube([(0.0, G + U - 0.2, hd + 1.42), (0.0, G + 0.9, hd + 1.45)], 0.015, mat=P["rope"], segs=4)
    m.tube([(0.0, G + 0.9, hd + 1.45), (-0.3, G + 0.3, hd + 1.4), (0.0, G - 0.4, hd + 1.5), (0.3, G + 0.3, hd + 1.4), (0.0, G + 0.9, hd + 1.45)], 0.09, mat=Paint(P["cloth"].mat, 0x4A5046), segs=6)
    # Stone stair up the east side to a door into the loft.
    for k in range(9):
        y = 0.3 * (k + 1)
        m.box((1.0, y, 0.42), at=(hw + 0.55, 0.0, hd - 0.4 - k * 0.42), mat=P["stone_dark"], tint=0.85 + 0.1 * (k % 2), bev=0.03)
    m.box((1.0, G, 0.9), at=(hw + 0.55, 0.0, -hd + 0.45), mat=P["stone_dark"], tint=0.85, bev=0.03)
    m.box((0.06, 1.8, 0.9), at=(hw + 0.12, G + 0.2, -hd + 0.6), mat=P["timber_pale"], bev=0.01)
    c.box((W + 0.3, G + 0.2 + U + rise * 0.6, D + 0.3), bev=0)
    c.box((1.0, G, D), at=(hw + 0.55, 0.0, 0.0), bev=0)
    # Nets drying on the front wall, glass floats, oars against it, pots stacked.
    netcol = Paint(P["cloth"].mat, 0x4A5046)
    for k, (u, sag) in enumerate(((-2.6, 0.9), (2.4, 1.1))):
        pts = [(u - 0.7 + t * 1.4, G - 0.15 - sag * math.sin(math.pi * t), hd + 0.13) for t in (j / 8 for j in range(9))]
        m.tube(pts, 0.05, mat=netcol, segs=5)
        for t in (0.2, 0.5, 0.8):
            px = u - 0.7 + t * 1.4
            m.uvsphere(0.08, at=(px, G - 0.25 - sag * math.sin(math.pi * t), hd + 0.2), mat=P["glass_green"] if k else P["glass_blue"], segs=8, rings=6)
    for k in range(2):
        m.box((0.08, 2.6, 0.05), at=(-1.9 + k * 0.25, 0.0, hd + 0.3), mat=P["timber_pale"], roll=0.12 + k * 0.04, bev=0.01)
        m.box((0.18, 0.55, 0.03), at=(-1.9 + k * 0.25 + 0.04, 0.05, hd + 0.33), mat=P["timber_pale"], roll=0.12 + k * 0.04, bev=0.005)
    ob = m.build(name, loc=(x, 0, 0), ao=0.6, ao_dist=0.9, grime=0.15, grime_h=0.9)
    for k, (px, pz) in enumerate(((-hw - 0.6, 1.2), (-hw - 0.55, 0.3))):
        kit.place(T, "lobster_pot", f"{name}_pot{k}", (px, 0.0 + 0.45 * k, pz), yaw=1.2 + k, parent=ob)
    c.build("COL_body", parent=ob, ao=0, grime=0, ground=False)
    kit.empty("station", (0.0, 0.0, hd + 1.4), parent=ob, size=0.3)
    return ob


def smokehouse(name, x, ruined):
    """The smokehouse, 4.4 x 4 m: rubble walls, a low plank door, a steep
    shingled roof gone black with soot and a louvred vent on top; a lean-to
    rack of split fish curing in the open and its woodpile. Ruined: the roof
    fallen in, the vent in the nettles, a cold firepit."""
    m = MB(850 + int(ruined))
    rnd = m.rnd
    c = MB(860 + int(ruined))
    W, D, H = 4.4, 4.0, 2.3
    hw, hd = W / 2, D / 2
    soot = Paint(P["tar"].mat, 0x2C2622)
    m.box((W + 0.1, 0.3, D + 0.1), mat=QUOIN, bev=0.02)
    if ruined:
        for at, size in (((0, 0.3, -hd + 0.25), (W, 1.5, 0.5)), ((-hw + 0.25, 0.3, 0), (0.5, 1.1, D - 1.0)), ((hw - 0.25, 0.3, 0.3), (0.5, 0.7, D - 1.6)), ((-1.3, 0.3, hd - 0.25), (1.8, 1.2, 0.5)), ((1.5, 0.3, hd - 0.25), (1.4, 0.6, 0.5))):
            m.box(size, at=at, mat=P["stone_dark"], tint=0.75 + 0.15 * rnd.random(), bev=0.05)
            c.box(size, at=at, bev=0)
        # The roof slid in: two shingled panels, the vent upside down outside.
        for s in (-1, 1):
            m.box((2.6, 0.08, 2.4), at=(s * 0.7, 0.9, 0.1 * s), mat=soot, roll=s * 0.5, pitch=0.2 * s, centered=True, bev=0.02)
        m.box((0.7, 0.6, 0.7), at=(2.9, 0.0, 1.6), mat=Paint(P["timber"].mat, 0x3A2E26), yaw=0.5, roll=1.4, bev=0.02)
        m.cyl(0.5, 0.55, 0.1, at=(0.2, 0.3, -0.2), mat=ASH, segs=12, bev=0)
        for k in range(10):
            a = rnd.random() * TAU
            r = 2.6 + rnd.random() * 1.2
            m.rock(0.14 + rnd.random() * 0.14, at=(math.cos(a) * r, 0.0, math.sin(a) * r * 0.9), mat=P["stone_dark"], seed=870 + k, squash=0.7)
        ob = m.build(name, loc=(x, 0, 0), ao=0.6, ao_dist=0.8, grime=0.25, grime_h=1.0)
        c.build("COL_ruin", parent=ob, ao=0, grime=0, ground=False)
        return ob

    m.box((W, H - 0.3, D), at=(0, 0.3, 0), mat=P["stone_dark"], bev=0.03)
    stone_patch(m, rnd, -hw, hw, 0.4, H - 0.2, hd, n=7)
    # Low plank door with strap hinges, a hatch on the side.
    for k in range(4):
        m.box((0.22, 1.7, 0.06), at=(-0.33 + k * 0.22, 0.3, hd + 0.02), mat=P["hull"], bev=0.008, tint=0.9 + 0.08 * (k % 2))
    for y in (0.65, 1.6):
        m.box((0.8, 0.06, 0.03), at=(0, y, hd + 0.06), mat=P["iron"], bev=0)
    m.box((1.1, 0.2, 0.2), at=(0, 2.0, hd + 0.06), mat=QUOIN, bev=0.02)
    m.box((0.06, 0.6, 0.7), at=(hw + 0.02, 1.0, -0.5), mat=P["hull"], bev=0.01)
    # A steep hipped roof of sooty shingles to a louvred vent.
    apex = H + 2.4
    for k in range(9):
        t0, t1 = k / 9, (k + 1) / 9
        y0, y1 = H + t0 * 2.15, H + t1 * 2.15
        r0, r1 = (1 - t0 * 0.82), (1 - t1 * 0.82)
        m.lathe([(r0 * 3.35, y0), (r1 * 3.35, y1)], mat=soot if k > 4 else Paint(P["hull"].mat, 0x40362E), segs=4, yaw=math.pi / 4, cap=False, tint=0.85 + 0.2 * rnd.random())
    m.box((0.7, 0.5, 0.7), at=(0, H + 2.1, 0), mat=Paint(P["timber"].mat, 0x3A2E26), bev=0.02)
    for k in range(3):
        for s in (-1, 1):
            m.box((0.74, 0.05, 0.08), at=(0, H + 2.18 + k * 0.13, s * 0.36), mat=soot, pitch=0.5 * s, centered=True, bev=0)
    m.cyl(0.62, 0.0, 0.42, at=(0, H + 2.6, 0), mat=soot, segs=4, yaw=math.pi / 4, bev=0.01)
    # Lean-to drying rack on the west side: fish split and hung in rows.
    rx = -hw - 0.75
    for z in (-1.3, 1.3):
        m.box((0.1, 2.0, 0.1), at=(rx - 0.5, 0.0, z), mat=P["timber"], bev=0.01)
    m.box((1.4, 0.06, 3.0), at=(rx, 2.05, 0.0), mat=SLATE, roll=-0.3, centered=True, bev=0.01)
    for y in (1.15, 1.6):
        m.cyl(0.03, 0.03, 2.7, at=(rx - 0.2, y, 0.0), mat=P["timber_pale"], pitch=math.pi / 2, centered=True, segs=6, bev=0)
        for k in range(9):
            fz = -1.15 + k * 0.29
            m.prism([(0.0, 0.0), (0.07, -0.08), (0.05, -0.34), (0.0, -0.42), (-0.05, -0.34), (-0.07, -0.08)], 0.02, at=(rx - 0.2, y - 0.02, fz), mat=Paint(P["paint_yellow"].mat, 0xB89A5A), yaw=math.pi / 2, bev=0, tint=0.8 + 0.3 * rnd.random())
    ob = m.build(name, loc=(x, 0, 0), ao=0.6, ao_dist=0.8, grime=0.18, grime_h=0.8)
    kit.place(T, "plank_pile", f"{name}_wood", (hw + 0.7, 0.0, 0.8), yaw=1.57, parent=ob)
    c.box((W + 0.2, H + 1.2, D + 0.2), bev=0)
    c.box((1.2, 2.0, 3.0), at=(rx - 0.1, 0.0, 0.0), bev=0)
    c.build("COL_body", parent=ob, ao=0, grime=0, ground=False)
    kit.empty("smoke", (0.0, H + 2.9, 0.0), parent=ob, size=0.3)
    kit.empty("station", (0.0, 0.0, hd + 1.3), parent=ob, size=0.3)
    return ob


# ------------------------------------------------------------------ build

lighthouse()
cottage("HOME_cottage_a", 14, 210, WASH, DOORS["blue"], chimneys=(1,), flowers=True, bench=True)
cottage("HOME_cottage_b", 24, 211, OCHRE, DOORS["red"], chimneys=(-1, 1), porch=True, shutters=True, pots=True)
cottage("HOME_cottage_c", 34, 212, GREYWASH, DOORS["green"], chimneys=(-1,), shutters=True, butt=True, bench=True)
forge("HOME_forge", 46, broken=False)
forge("HOME_forge_broken", 56, broken=True)
hearth(66)
chest(72)
sailboat(104)
rocks(112)
wall_run(120)
garden(128)
washing_line(138)
net_frame(146)
woodpile(152)
well(158)
boat_trestles(164)
memorial(172)
gorse(178)
jetty()
jetty_ruin()
cottage_ruin("HOME_cottage_a_ruin", 240, 900, WASH, chimney=1)
cottage_ruin("HOME_cottage_b_ruin", 250, 910, OCHRE, chimney=-1)
cottage_ruin("HOME_cottage_c_ruin", 260, 920, GREYWASH, chimney=-1)
net_loft("HOME_net_loft", 272, False)
net_loft("HOME_net_loft_ruin", 284, True)
smokehouse("HOME_smokehouse", 296, False)
smokehouse("HOME_smokehouse_ruin", 306, True)

kit.save_and_export("art/blender/home/home.blend", "public/assets/models/home.glb")
