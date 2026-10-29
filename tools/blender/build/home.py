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


# ------------------------------------------------------------------- dock

DOCK_Y = 2.7  # deck top (HomeLevel DOCK_Y); planks are 0.15 m thick, centred 0.075 under it


def dock_plank(name, x, seed, paint):
    """One 3 x 0.95 m deck section (HomeLevel's plank box, origin at its
    centre): four boards across the dock with gaps, nail heads over the
    stringers."""
    m = MB(seed)
    rnd = m.rnd
    for k in range(4):
        z = -0.355 + k * 0.237
        L = 3.0 - rnd.random() * 0.12
        m.plank(L, 0.215, 0.06, at=((rnd.random() - 0.5) * 0.06, 0.015, z), mat=paint, warp=0.02, tint=0.9 + rnd.random() * 0.18)
        for nx in (-1.2, 0.0, 1.2):
            for dz in (-0.05, 0.05):
                m.box((0.018, 0.006, 0.018), at=(nx, 0.075, z + dz), mat=P["iron"], bev=0)
    return m.build(name, loc=(x, 0, 0), ao=0.5, ao_dist=0.2, grime=0, ground=False)


def dock_frame(x):
    """Everything under the deck boards, in home coordinates relative to
    (DOCK_X, 0, 0): three stringers, a cap beam per pile pair, the piles with
    their wet band and barnacles, cross bracing, a ladder off the end, and
    bollards and rope on the deck edge."""
    m = MB(280)
    rnd = m.rnd
    z0, z1 = 44.5, 75.5
    for sx in (-1.2, 0.0, 1.2):
        m.box((0.16, 0.14, z1 - z0), at=(sx, DOCK_Y - 0.2, (z0 + z1) / 2), mat=P["timber"], bev=0.015)
    for i in range(8):
        z = 46 + i * 4
        m.box((3.3, 0.18, 0.24), at=(0, DOCK_Y - 0.38, z), mat=P["hull"], bev=0.02)
        for sx in (-1.4, 1.4):
            m.cyl(0.2, 0.23, DOCK_Y - 0.38 + 5.2, at=(sx, -5.2, z), mat=P["hull"], segs=9, bev=0.02)
            for k in range(7):
                a, y = rnd.random() * math.tau, -0.4 + rnd.random() * 1.9
                bp, br = aim((math.cos(a), 0.0, math.sin(a)))
                m.cyl(0.05, 0.015, 0.05, at=(sx + math.cos(a) * 0.2, y, z + math.sin(a) * 0.2), mat=P["barnacle"], segs=5, pitch=bp, roll=br, bev=0)
        m.tube([(-1.4, DOCK_Y - 0.6, z), (1.4, -0.6, z)], 0.07, mat=P["hull"], segs=6)
        m.tube([(1.4, DOCK_Y - 0.6, z), (-1.4, -0.6, z)], 0.07, mat=P["hull"], segs=6)
    for sx in (-1.4, 1.4):
        m.tube([(sx, 1.2, 46.2), (sx, 1.2, 73.8)], 0.06, mat=P["hull"], segs=6)
    # Ladder down the end into the water.
    for sx in (0.65, 1.15):
        m.box((0.07, DOCK_Y + 1.2, 0.07), at=(sx, -1.2, z1 + 0.06), mat=P["hull"], bev=0.01)
    for k in range(9):
        m.cyl(0.025, 0.025, 0.5, at=(0.9, -1.0 + k * 0.4, z1 + 0.06), mat=P["timber"], segs=5, roll=ACROSS, centered=True, bev=0)
    ob = m.build("HOME_dock_frame", loc=(x, 0, 0), ao=0.5, ao_dist=0.8, grime=0, ground=False, tideline=True)
    for k, (bx, bz) in enumerate(((-1.38, 50.0), (1.38, 58.0), (-1.38, 66.0), (1.38, 74.0))):
        kit.place(T, "bollard", f"dock_bollard{k}", (bx, DOCK_Y, bz), yaw=k * 1.3, parent=ob, scale=0.8)
    kit.place(T, "rope_coil", "dock_rope0", (-1.0, DOCK_Y, 66.9), yaw=0.6, parent=ob)
    kit.place(T, "rope_coil", "dock_rope1", (1.0, DOCK_Y, 73.2), yaw=2.0, parent=ob)
    return ob


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


# ------------------------------------------------------------ rocks, cliff


def rocks(x):
    """Unit boulders for the cliff foot; the code scales them (1.5 - 5 m) and turns them."""
    for i in range(6):
        m = MB(300 + i)
        m.rock(1.0, mat=P["rock"] if i % 3 else P["rock_dark"], seed=310 + i, squash=0.62 + (i % 3) * 0.08, jitter=0.24, subdiv=2, cuts=6)
        m.build(f"HOME_rock_{i}", loc=(x + i * 3.0, 0, 0), ao=0.45, ao_dist=0.6, grime=0.3, grime_h=0.5)


CLIFF_ROWS = [(3.0, 0.0), (2.78, 0.3), (2.3, 0.5), (1.7, 0.75), (1.0, 1.0), (0.3, 1.3), (-0.5, 1.8), (-1.5, 2.4), (-2.7, 3.3), (-3.9, 4.6), (-5.3, 6.3)]
STRATA = [P["grass"], Paint(STONE, 0x8C877C), Paint(STONE, 0x7A766D), Paint(STONE, 0x8F8A7E), Paint(STONE, 0x6F6B63),
          Paint(STONE, 0x847F74), Paint(STONE, 0x75716A), Paint(STONE, 0x6A675F), Paint(STONE, 0x5E5B55), Paint(STONE, 0x55524D)]


def cliff():
    """The headland's sea cliff: a ring from the grass edge (radius 46 at
    y 3, HomeLevel's headland) down to the seabed, in strata bands that jut
    and recede, wet below the high-tide line and weedy under low water."""
    m = MB(270)
    N = 240
    rings = []
    for j, (y, off) in enumerate(CLIFF_ROWS):
        ring = []
        for i in range(N):
            a = i / N * math.tau
            cx, cz = math.cos(a), math.sin(a)
            amp = 0.0 if j == 0 else 0.25 + j * 0.14
            n = kit.fbm3(cx * 9.0, y * 0.35, cz * 9.0, seed=27 + j % 3) * amp
            ledge = 0.0 if j == 0 else kit.fbm3(cx * 4.0, 0.5, cz * 4.0, seed=40 + j) * 0.5
            r = 46.0 + off + n + ledge
            ring.append((cx * r, y, cz * r))
        rings.append(ring)
    for j in range(len(rings) - 1):
        m.loft([rings[j], rings[j + 1]], mat=STRATA[j], closed=True, jit=0.04)
    return m.build("HOME_cliff", loc=(0, 0, 0), ao=0.45, ao_dist=2.5, grime=0, ground=False, tideline=True)


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
                m.box((sl - 0.04, h, w / 2 - 0.03), at=(u + sl / 2, y + (0.19 - h) * rnd.random(), side * w / 4), mat=field[int(rnd.random() * len(field))],
                      yaw=(rnd.random() - 0.5) * 0.14, pitch=(rnd.random() - 0.5) * 0.08, roll=(rnd.random() - 0.5) * 0.1, tint=0.72 + 0.28 * rnd.random(), bev=0.035)
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


# ------------------------------------------------------------------ build

lighthouse()
cottage("HOME_cottage_a", 14, 210, WASH, DOORS["blue"], chimneys=(1,), flowers=True, bench=True)
cottage("HOME_cottage_b", 24, 211, OCHRE, DOORS["red"], chimneys=(-1, 1), porch=True, shutters=True, pots=True)
cottage("HOME_cottage_c", 34, 212, GREYWASH, DOORS["green"], chimneys=(-1,), shutters=True, butt=True, bench=True)
forge("HOME_forge", 46, broken=False)
forge("HOME_forge_broken", 56, broken=True)
hearth(66)
chest(72)
dock_plank("HOME_dock_plank_0", 76, 281, P["timber"])
dock_plank("HOME_dock_plank_1", 80, 282, P["hull"])
dock_plank("HOME_dock_plank_2", 84, 283, P["driftwood"])
dock_plank("HOME_dock_plank_new", 88, 284, P["timber_pale"])
dock_frame(95)
sailboat(104)
rocks(112)
cliff()
wall_run(120)
garden(128)
washing_line(138)
net_frame(146)
woodpile(152)
well(158)
boat_trestles(164)
memorial(172)
gorse(178)

kit.save_and_export("art/blender/home/home.blend", "public/assets/models/home.glb")
