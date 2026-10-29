"""Builds art/blender/viewmodels/viewmodels.blend and public/assets/models/viewmodels.glb.

First-person models. Game space with the camera looking down -Z: barrels point
-Z, the right hand is +X. Each model is a top-level object VM_<id> with empties
for attach points (muzzle, flame, tip; only a rod's tip is read by code).

They're on screen the whole game, so they carry the most detail. The weapon
sits right of centre and the lantern left of it (src/player/Viewmodel.ts), so
you mostly see the weapon's top and left side and the lantern's right side;
the detail goes there. The bolt-caster is held in one hand, the lantern in the
other, so it's built like a heavy pistol: a carved stock and grip, an iron
lock housing with the glowing bolt chamber on top, a pressure gauge turned
toward your eye, and the barrel.

    blender -b --factory-startup --python tools/blender/build/viewmodels.py
"""

import math
import os
import sys

from mathutils import Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import kit  # noqa: E402
from kit import MB, Paint  # noqa: E402

kit.reset()
P = kit.palette()
WOOD, CLOTH, IRON, PAINT = P["timber"].mat, P["cloth"].mat, P["iron"].mat, P["paint_white"].mat
OAK = Paint(WOOD, 0x8E6842)
WALNUT = Paint(WOOD, 0x5E3C28)
ROSEWOOD = Paint(WOOD, 0x4A2B23)
EBONY = Paint(WOOD, 0x2E241E)
GUNMETAL = Paint(IRON, 0x3A4047)
BLUED = Paint(IRON, 0x2F3E4E)
BAMBOO = Paint(WOOD, 0xB49A6A)
NODE = Paint(WOOD, 0x8C7048)
LACQUER = Paint(WOOD, 0x5C2A20)
CORK = Paint(CLOTH, 0xB08A5C)
LINE = Paint(CLOTH, 0xD8D3C2)
DIAL = Paint(PAINT, 0xE6DCC3)

bolt_glow = kit.material("bolt_amber", 0xFFC46B, rough=0.2, emit=0xFFB347, strength=3.0)
chamber_glass = kit.material("chamber_glass", 0xFFD49A, rough=0.08, emit=0xFFA545, strength=1.6)
glass_hot = kit.material("lantern_glass", 0xFFE2A8, rough=0.15, emit=0xFFB347, strength=2.4)
glass_dim = kit.material("lantern_glass_dim", 0xF2C890, rough=0.15, emit=0xF09A3A, strength=1.3)
lens_rib = kit.material("lens_rib", 0xC8873A, rough=0.1, emit=0xB86A28, strength=0.5)

FWD = -math.pi / 2  # pitch: a Y-axis cylinder or lathe points down game -Z
ACROSS = math.pi / 2  # roll: a Y-axis cylinder lies along game X (its top toward -X)
FACING = math.pi / 2  # ring pitch: the ring stands in the XY plane, facing the camera
AXIS = 0.012  # bolt-caster barrel axis height


def aim(n):
    """(pitch, roll) that turn a primitive's +Y axis toward the unit vector n."""
    return math.asin(max(-1.0, min(1.0, n[2]))), math.atan2(-n[0], n[1])


def squircle(hw, hh, n=20, e=0.55):
    """Rounded-rectangle outline, counter-clockwise from +X."""
    out = []
    for i in range(n):
        a = i / n * math.tau
        c, s = math.cos(a), math.sin(a)
        out.append((hw * math.copysign(abs(c) ** e, c), hh * math.copysign(abs(s) ** e, s)))
    return out


def prof_r(prof, y):
    """Radius of a (radius, y) profile at height y."""
    for (r0, y0), (r1, y1) in zip(prof, prof[1:]):
        if y0 <= y <= y1:
            return kit.lerp(r0, r1, (y - y0) / (y1 - y0))
    return prof[0][0] if y < prof[0][1] else prof[-1][0]


def tup(v):
    return (v.x, v.y, v.z)


# ------------------------------------------------------------ bolt-caster


def stock_at(rows, z):
    """(bottom, top, half-width) of the stock at depth z."""
    for a, b in zip(rows, rows[1:]):
        if a[0] <= z <= b[0]:
            t = (z - a[0]) / (b[0] - a[0])
            return tuple(kit.lerp(a[k], b[k], t) for k in (1, 2, 3))
    r = rows[0] if z < rows[0][0] else rows[-1]
    return r[1], r[2], r[3]


def grain(m, mat, n=20):
    """A shade per band round a loft: long streaks that read as wood grain."""
    return [(mat, 1.0 + (m.rnd.random() - 0.5) * 0.12) for _ in range(n)]


def stock(m, rows, mat):
    """Carved stock: rounded sections (z, bottom, top, half-width), front to back."""
    secs = []
    for z, bot, top, hw in rows:
        cy, hh = (bot + top) / 2, (top - bot) / 2
        secs.append([(x, cy + y, z) for x, y in squircle(hw, hh)])
    m.loft(secs, closed=True, cap=True, strips=grain(m, mat))


def grip(m, rows, mat):
    """Pistol grip: level rounded sections (y, z-centre, half-depth, half-width), top to bottom."""
    secs = [[(x, y, cz + z) for x, z in squircle(hx, hz)] for y, cz, hz, hx in rows]
    m.loft(secs, closed=True, cap=True, strips=grain(m, mat))


def wrap(m, rows, z, length, mat, strands=1):
    """A binding round the barrel and the forestock at z: twine turns or a metal band."""
    bot, _, hw = stock_at(rows, z)
    top = AXIS + 0.024
    cy, hh = (bot + top) / 2, (top - bot) / 2 + 0.003
    w = length / strands
    for k in range(strands):
        z0 = z - length / 2 + k * w
        secs = [[(x, cy + y, zz) for x, y in squircle(max(hw, 0.022) + 0.003, hh)] for zz in (z0 + w * 0.06, z0 + w * 0.94)]
        m.loft(secs, mat=mat, closed=True, cap=True, tint=1.0 if k % 2 == 0 else 0.86)


def barrel(m, z0, length, metal, band):
    """Octagonal breech (a flat on top) then a round barrel, from z0 forward. Returns the muzzle z."""
    oct_len = 0.12
    m.lathe([(0.027, 0.0), (0.026, oct_len)], at=(0, AXIS, z0), mat=metal, segs=8, pitch=FWD, smooth_ring=True)
    m.cyl(0.0285, 0.0285, 0.009, at=(0, AXIS, z0 - oct_len), mat=band, segs=20, pitch=FWD, centered=True, bev=0.0015)
    m.lathe([(0.023, 0.0), (0.0215, length - oct_len)], at=(0, AXIS, z0 - oct_len), mat=metal, segs=20, pitch=FWD)
    return z0 - length


def gauge(m, base, n, size, bezel, needle):
    """A pressure gauge on a short stem at `base`, its face turned toward n."""
    n = Vector(n).normalized()
    p, r = aim(n)
    b = Vector(base)
    m.cyl(size * 0.3, size * 0.3, size * 0.9, at=tup(b), mat=bezel, segs=10, pitch=p, roll=r, bev=0)
    body = b + n * (size * 0.8)
    m.cyl(size * 0.94, size, size * 0.5, at=tup(body), mat=bezel, segs=20, pitch=p, roll=r, bev=size * 0.06)
    face = body + n * (size * 0.5)
    m.cyl(size * 0.8, size * 0.8, size * 0.04, at=tup(face), mat=DIAL, segs=20, pitch=p, roll=r, bev=0)
    m.ring(size * 0.86, size * 0.09, at=tup(face + n * (size * 0.04)), mat=bezel, pitch=p, roll=r, segs=20, tube_segs=4)
    up = (Vector((0, 1, 0)) - n * n.y).normalized()
    right = up.cross(n)
    top = face + n * (size * 0.06)

    def on_face(deg, rad):
        a = math.radians(deg)
        return top + (up * math.cos(a) + right * math.sin(a)) * (size * rad)

    for k in range(7):
        m.tube([tup(on_face(-120 + k * 40, 0.56)), tup(on_face(-120 + k * 40, 0.7))], size * 0.04, mat=P["tar"], segs=4)
    m.tube([tup(on_face(a, 0.63)) for a in (82, 100, 118)], size * 0.05, mat=P["paint_red"], segs=4)
    m.tube([tup(on_face(205, 0.12)), tup(on_face(25, 0.6))], [size * 0.06, size * 0.03], mat=needle, segs=4)
    m.cyl(size * 0.1, size * 0.1, size * 0.08, at=tup(top), mat=P["tar"], segs=8, pitch=p, roll=r, bev=0)


def boltcaster(name, x, tier):
    """Mk I: oiled oak, plain iron and a twine binding. Mk II: walnut, blued
    steel and brass, a ported shroud and a muzzle brake. The Lamplighter:
    ebony and gilt, with a lamp-glass round the muzzle that the bolts burn
    through."""
    m = MB(100 + tier)
    wood = (OAK, WALNUT, ROSEWOOD)[tier - 1]
    metal = (GUNMETAL, BLUED, GUNMETAL)[tier - 1]
    fit = (P["brass"], P["brass"], P["gilt"])[tier - 1]
    band = (P["iron_light"], P["brass"], P["gilt"])[tier - 1]
    length = (0.46, 0.52, 0.5)[tier - 1]
    zh = -0.16  # front of the lock housing, where the barrel leaves it
    zn = zh - length * 0.55  # forestock nose

    # Stock, grip and the brass pommel.
    rows = [
        (zn, -0.024, -0.006, 0.019),
        (zn + 0.014, -0.027, -0.004, 0.021),
        (-0.25, -0.034, -0.002, 0.025),
        (-0.15, -0.042, 0.0, 0.029),
        (-0.06, -0.047, 0.0, 0.031),
        (0.0, -0.05, 0.0, 0.031),
        (0.035, -0.053, 0.034, 0.03),
        (0.075, -0.057, 0.03, 0.028),
        (0.108, -0.058, 0.014, 0.025),
        (0.128, -0.05, -0.008, 0.021),
    ]
    stock(m, rows, wood)
    grip(m, [(-0.03, 0.07, 0.036, 0.026), (-0.06, 0.08, 0.031, 0.022), (-0.1, 0.093, 0.029, 0.022), (-0.14, 0.106, 0.031, 0.023), (-0.165, 0.114, 0.034, 0.025)], wood)
    m.uvsphere(0.032, at=(0, -0.171, 0.116), mat=fit, scale=(0.84, 0.5, 1.12), segs=16, rings=8)
    m.box((0.042, 0.022, 0.014), at=(0, -0.015, zn + 0.005), mat=band, centered=True, bev=0.003)
    # Tang over the wrist, trigger and guard.
    m.box((0.016, 0.005, 0.05), at=(0, 0.032, 0.06), mat=fit, pitch=0.1, centered=True, bev=0.0015)
    m.tube([(0, -0.046, -0.04), (0, -0.074, -0.034), (0, -0.088, -0.008), (0, -0.085, 0.022), (0, -0.07, 0.052)], 0.0035, mat=fit, segs=6)
    m.tube([(0, -0.048, -0.006), (0, -0.062, -0.003), (0, -0.073, 0.006)], [0.004, 0.0034, 0.0028], mat=metal, segs=6)

    # Lock housing, its side plate and rivets, the hammer spur behind the chamber.
    m.box((0.068, 0.068, 0.19), at=(0, 0.012, -0.065), mat=metal, centered=True, bev=0.006)
    m.box((0.004, 0.044, 0.13), at=(-0.035, 0.008, -0.075), mat=fit if tier > 1 else metal, centered=True, bev=0.0015, tint=1.0 if tier > 1 else 1.25)
    for zz in (-0.13, -0.02):
        for yy in (-0.008, 0.024):
            m.uvsphere(0.0034, at=(-0.0372, yy, zz), mat=fit, scale=(0.6, 1, 1), segs=8, rings=4)
    m.tube([(0, 0.044, 0.018), (0, 0.06, 0.03), (0, 0.072, 0.046), (0, 0.076, 0.056)], [0.0055, 0.005, 0.0045, 0.0045], mat=metal, segs=6)
    m.cyl(0.0075, 0.0075, 0.012, at=(0, 0.077, 0.058), mat=metal, roll=ACROSS, centered=True, segs=10, bev=0.001)

    # The bolt chamber: the next bolt glowing in an open cage between turned caps.
    cr = 0.026 if tier < 3 else 0.029
    cy = 0.046 + cr
    m.box((0.03, 0.006, 0.12), at=(0, 0.046, -0.078), mat=P["tar"], bev=0)
    br = 0.0085 if tier < 3 else 0.0095
    m.cyl(br, br, 0.088, at=(0, cy, -0.012), mat=bolt_glow, segs=10, pitch=FWD, bev=0)
    m.uvsphere(br * 1.15, at=(0, cy, -0.012), mat=bolt_glow, segs=10, rings=6)
    m.lathe([(br * 1.5, 0.0), (br * 1.25, 0.01), (0.0, 0.028)], at=(0, cy, -0.1), mat=bolt_glow, segs=10, pitch=FWD)
    for k in range(3):
        th = k / 3 * math.tau + math.pi / 2
        m.box((0.0016, 0.013, 0.024), at=(math.cos(th) * br * 1.6, cy + math.sin(th) * br * 1.6, -0.03), mat=bolt_glow, roll=th - math.pi / 2, centered=True, bev=0)
    # The rear collar is open, so you look down the chamber at the bolt's tail.
    ri = cr - 0.0028
    m.lathe([(ri, 0.0), (cr + 0.003, 0.0), (cr + 0.003, 0.022), (cr + 0.001, 0.026), (cr + 0.001, 0.032), (ri, 0.032), (ri, 0.0)], at=(0, cy, 0.012), mat=fit, segs=20, pitch=FWD, cap=False, staves=0.08)
    m.lathe([(cr + 0.001, 0.0), (cr + 0.001, 0.006), (cr + 0.004, 0.01), (cr + 0.004, 0.024), (0.02, 0.03), (0.0, 0.032)], at=(0, cy, -0.133), mat=fit, segs=20, pitch=FWD)
    cage = metal if tier == 1 else fit
    for th in (math.pi / 2 + 0.8, math.pi / 2 - 0.8, math.pi / 2 + 1.9, math.pi / 2 - 1.9):
        rr = cr - 0.001
        m.box((0.0045, 0.0045, 0.114), at=(math.cos(th) * rr, cy + math.sin(th) * rr, -0.078), mat=cage, roll=th - math.pi / 2, centered=True, bev=0.001)
    for zz in (-0.058, -0.1):
        m.ring(cr - 0.001, 0.0024, at=(0, cy, zz), mat=cage, pitch=FACING, segs=20, tube_segs=4)

    # Pressure gauge on the rear-left corner, turned to the player's eye.
    gauge(m, base=(-0.04, 0.03, 0.008), n=(-0.37, 0.35, 0.86), size=0.019, bezel=fit, needle=P["paint_red"])

    # Barrel, bindings and muzzle.
    zm = barrel(m, zh + 0.01, length + 0.01, metal, band)
    wrap(m, rows, zn + 0.03, 0.012, band)
    if tier == 1:
        wrap(m, rows, -0.33, 0.034, P["rope"], strands=5)
        m.cyl(0.0236, 0.0236, 0.01, at=(0, AXIS, zm + 0.1), mat=P["rust"], segs=20, pitch=FWD, centered=True, bev=0.0012)
    else:
        wrap(m, rows, -0.32, 0.012, band)
    m.box((0.004, 0.013, 0.02), at=(0, AXIS + 0.02, zm + 0.05), mat=fit, bev=0.0008)
    if tier == 1:
        m.lathe([(0.0215, 0.0), (0.026, 0.004), (0.0268, 0.018), (0.024, 0.024), (0.0135, 0.025)], at=(0, AXIS, zm + 0.024), mat=metal, segs=20, pitch=FWD)
    elif tier == 2:
        z0s = zn - 0.004
        m.cyl(0.0285, 0.0285, z0s - (zm + 0.06), at=(0, AXIS, z0s), mat=fit, segs=20, pitch=FWD, bev=0.002)
        for k in range(4):
            zz = z0s - 0.028 - k * 0.04
            for th in (math.pi / 2, math.pi / 2 + 0.75):
                m.box((0.007, 0.004, 0.024), at=(math.cos(th) * 0.0278, AXIS + math.sin(th) * 0.0278, zz), mat=P["tar"], roll=th - math.pi / 2, centered=True, bev=0)
        m.lathe([(0.0215, 0.0), (0.027, 0.004), (0.0278, 0.036), (0.025, 0.042), (0.0135, 0.043)], at=(0, AXIS, zm + 0.042), mat=fit, segs=20, pitch=FWD)
        for side in (-1, 1):
            for k in range(2):
                m.box((0.004, 0.012, 0.007), at=(side * 0.0265, AXIS, zm + 0.03 - k * 0.013), mat=P["tar"], centered=True, bev=0)
    else:
        for zz in (zm + 0.09, zm + 0.105, zh - 0.2):
            m.ring(0.0228, 0.0016, at=(0, AXIS, zz), mat=fit, pitch=FACING, segs=20, tube_segs=4)
        m.box((0.002, 0.016, 0.016), at=(-0.029, -0.012, 0.07), mat=fit, pitch=math.pi / 4, centered=True, bev=0)
        lamp = [(0.0215, 0.0), (0.03, 0.01), (0.038, 0.026), (0.039, 0.044), (0.031, 0.062), (0.019, 0.072)]
        m.lathe(lamp, at=(0, AXIS, zm + 0.004), mat=bolt_glow, segs=24, pitch=FWD, cap=False)
        for k in range(6):
            th = k / 6 * math.tau
            pts = [(math.cos(th) * r, AXIS + math.sin(th) * r, zm + 0.004 - t) for r, t in ((0.022, -0.002), (0.033, 0.012), (0.0415, 0.03), (0.0415, 0.044), (0.033, 0.062), (0.021, 0.074))]
            m.tube(pts, 0.0022, mat=fit, segs=5)
        m.ring(0.0225, 0.0028, at=(0, AXIS, zm + 0.006), mat=fit, pitch=FACING, segs=20, tube_segs=5)
        m.ring(0.021, 0.0028, at=(0, AXIS, zm - 0.07), mat=fit, pitch=FACING, segs=20, tube_segs=5)
        for k in range(8):
            th = k / 8 * math.tau
            m.cyl(0.0032, 0.0, 0.012, at=(math.cos(th) * 0.021, AXIS + math.sin(th) * 0.021, zm - 0.07), mat=fit, segs=5, pitch=FWD, bev=0)
        zm -= 0.08
    m.cyl(0.0125, 0.0125, 0.002, at=(0, AXIS, zm + 0.0005), mat=P["tar"], segs=12, pitch=FWD, centered=True, bev=0)

    ob = m.build(name, loc=(x, 0, 0), ground=False, grime=0.0, ao=0.6, ao_dist=0.04, smooth=30)
    kit.empty("muzzle", (0, AXIS, zm), parent=ob, size=0.05)
    # Where the salvage hook's line reel clamps on, under the forestock.
    kit.empty("reel", (0, -0.035, zh - 0.12), parent=ob, size=0.03)
    return ob


# ---------------------------------------------------------------- lantern


def lantern():
    """The keeper's lantern, a lighthouse in miniature: a brass font, ribbed
    glass like a Fresnel lens, wire guards, a gallery of vents under a copper
    dome with a ball vent, and the bail it's carried by."""
    m = MB(110)
    brass, iron, cop = P["brass"], P["iron"], P["copper"]
    m.lathe([(0.0, -0.128), (0.05, -0.128), (0.057, -0.124), (0.061, -0.113), (0.0605, -0.098), (0.055, -0.086), (0.045, -0.077), (0.037, -0.072), (0.0, -0.071)], mat=brass, segs=24)
    m.ring(0.053, 0.0028, at=(0, -0.127, 0), mat=iron, segs=24, tube_segs=4)
    m.cyl(0.008, 0.007, 0.012, at=(0.036, -0.086, -0.026), mat=brass, segs=8, bev=0.001)
    glass = [(0.034, -0.073), (0.042, -0.059), (0.047, -0.037), (0.049, -0.012), (0.048, 0.014), (0.044, 0.039), (0.037, 0.06), (0.031, 0.07)]
    for y0, y1, mat in ((-0.073, -0.036, glass_dim), (-0.036, 0.03, glass_hot), (0.03, 0.07, glass_dim)):
        ys = sorted({y0, y1} | {y for _, y in glass if y0 < y < y1})
        m.lathe([(prof_r(glass, y), y) for y in ys], mat=mat, segs=24, cap=False)
    for y in (-0.05, -0.026, -0.002, 0.022, 0.046):
        m.ring(prof_r(glass, y) + 0.001, 0.0018, at=(0, y, 0), mat=lens_rib, segs=24, tube_segs=4)
    for k in range(4):
        a = k / 4 * math.tau + math.pi / 4
        pts = []
        for y in (-0.074, -0.055, -0.03, -0.005, 0.02, 0.045, 0.068):
            r = prof_r(glass, y) + 0.009
            pts.append((math.cos(a) * r, y, math.sin(a) * r))
        m.tube(pts, 0.0021, mat=iron, segs=5)
    m.ring(prof_r(glass, -0.01) + 0.009, 0.0021, at=(0, -0.01, 0), mat=iron, segs=24, tube_segs=4)
    # Collar, vent gallery, dome, ball vent and spike.
    m.cyl(0.043, 0.041, 0.008, at=(0, 0.067, 0), mat=brass, segs=24, bev=0.0015)
    m.cyl(0.037, 0.037, 0.01, at=(0, 0.075, 0), mat=P["tar"], segs=24, bev=0)
    for k in range(10):
        a = k / 10 * math.tau
        m.box((0.004, 0.01, 0.004), at=(math.cos(a) * 0.0385, 0.075, math.sin(a) * 0.0385), mat=brass, yaw=-a, bev=0)
    m.lathe([(0.0, 0.084), (0.052, 0.084), (0.053, 0.088), (0.048, 0.094), (0.04, 0.104), (0.029, 0.113), (0.016, 0.12), (0.0, 0.123)], mat=cop, segs=24)
    m.uvsphere(0.0115, at=(0, 0.131, 0), mat=brass, segs=14, rings=8)
    m.cyl(0.0022, 0.0006, 0.024, at=(0, 0.14, 0), mat=iron, segs=6, bev=0)
    # Bail: eyes on the eave, the wire, a wooden grip.
    for s in (-1, 1):
        m.ring(0.005, 0.0016, at=(s * 0.055, 0.088, 0), mat=iron, pitch=FACING, segs=10, tube_segs=4)
    m.tube([(-math.cos(a) * 0.055, 0.088 + math.sin(a) * 0.112, 0.0) for a in [k / 14 * math.pi for k in range(15)]], 0.0024, mat=iron, segs=6)
    m.cyl(0.0068, 0.0068, 0.032, at=(0, 0.2, 0), mat=P["timber"], segs=12, roll=ACROSS, centered=True, bev=0.0015)
    ob = m.build("VM_lantern", loc=(1.0, 0, 0), ground=False, grime=0.0, ao=0.5, ao_dist=0.03, smooth=35)
    kit.empty("flame", (0, -0.02, 0), parent=ob, size=0.03)
    return ob


# ------------------------------------------------------------------- rods

BLANK = [(0.012, 0.0), (0.0105, 0.3), (0.0083, 0.62), (0.006, 0.88), (0.0039, 1.07), (0.003, 1.15)]
BLANK_Z = -0.15  # the blank runs from here to the tip at z -1.3


def rod(name, x, reinforced):
    """Basic: split bamboo, a cord-wrapped grip, a wooden centrepin reel and red
    silk whippings. Reinforced: lacquered cane, a cork grip, brass ferrules, a
    brass reel and green whippings. The reel sits on top, ahead of the hand."""
    m = MB(120 + int(reinforced))
    blank = LACQUER if reinforced else BAMBOO
    fit = P["brass"] if reinforced else P["iron_light"]
    thread = Paint(CLOTH, 0x2F6B4A) if reinforced else Paint(CLOTH, 0xA0302A)
    z0 = -0.04  # front of the grip
    m.lathe([(0.0, 0.0), (0.015, 0.0), (0.0205, 0.005), (0.0215, 0.016)], at=(0, 0, 0.214), mat=fit, segs=16, pitch=FWD)
    n, span = 20, 0.198 - z0
    for k in range(n):
        r = 0.0182 + 0.004 * math.sin(math.pi * (k + 0.5) / n) ** 0.7
        m.cyl(r, r, span / n * 0.97, at=(0, 0, 0.198 - k * span / n), mat=CORK if reinforced else P["rope"], segs=16, pitch=FWD, bev=0.0012, tint=1.0 if k % 2 else 0.88)
    # Reel seat and the centrepin reel.
    m.cyl(0.0155, 0.0155, 0.13, at=(0, 0, z0), mat=fit, segs=16, pitch=FWD, bev=0.001)
    for zz in (z0, z0 - 0.122):
        m.cyl(0.0185, 0.0185, 0.008, at=(0, 0, zz), mat=fit, segs=16, pitch=FWD, bev=0.0015)
    rc = (0, 0.06, z0 - 0.065)
    reel = P["brass"] if reinforced else P["timber"]
    m.box((0.012, 0.03, 0.034), at=(0, 0.014, rc[2]), mat=fit, bev=0.002)
    for s in (-1, 1):
        m.cyl(0.04, 0.04, 0.0045, at=(s * 0.0135, rc[1], rc[2]), mat=reel, segs=24, roll=ACROSS, centered=True, bev=0.0012)
    m.cyl(0.029, 0.029, 0.022, at=rc, mat=LINE, segs=20, roll=ACROSS, centered=True, bev=0)
    m.cyl(0.008, 0.008, 0.036, at=rc, mat=fit, segs=10, roll=ACROSS, centered=True, bev=0.001)
    for a in (0.6, 0.6 + math.pi):
        hy, hz = rc[1] + math.sin(a) * 0.027, rc[2] + math.cos(a) * 0.027
        m.cyl(0.0022, 0.0022, 0.008, at=(-0.016, hy, hz), mat=fit, roll=ACROSS, segs=6, bev=0)
        m.cyl(0.0048, 0.0042, 0.013, at=(-0.024, hy, hz), mat=EBONY if reinforced else P["timber_pale"], roll=ACROSS, segs=8, bev=0.0008)
    if reinforced:
        for a in (0.6 + math.pi / 2, 0.6 + math.pi * 1.5):
            m.cyl(0.006, 0.006, 0.001, at=(-0.0159, rc[1] + math.sin(a) * 0.019, rc[2] + math.cos(a) * 0.019), mat=P["tar"], roll=ACROSS, segs=10, bev=0)
    # Blank, joints, guides with their whippings, tip-top.
    m.lathe(BLANK, at=(0, 0, BLANK_Z), mat=blank, segs=12, pitch=FWD)
    if reinforced:
        for t in (0.38, 0.76):
            r = prof_r(BLANK, t)
            m.cyl(r + 0.0026, r + 0.0022, 0.034, at=(0, 0, BLANK_Z - t + 0.017), mat=P["brass"], segs=12, pitch=FWD, bev=0.001)
    else:
        for t in (0.12, 0.31, 0.5, 0.68, 0.85, 1.0):
            m.ring(prof_r(BLANK, t) + 0.0004, 0.0014, at=(0, 0, BLANK_Z - t), mat=NODE, pitch=FACING, segs=12, tube_segs=4)
    for k, t in enumerate((0.16, 0.37, 0.56, 0.73, 0.88, 1.01)):
        r = prof_r(BLANK, t)
        g = 0.0075 - k * 0.0007
        zz = BLANK_Z - t
        gy = r + 0.004 + g
        m.cyl(r + 0.0009, r + 0.0009, 0.018, at=(0, 0, zz + 0.009), mat=thread, segs=12, pitch=FWD, bev=0)
        m.tube([(0, r, zz + 0.008), (0, r + 0.003, zz + 0.002), (0, gy - g, zz)], 0.0011, mat=fit, segs=4)
        m.ring(g, 0.0011, at=(0, gy, zz), mat=fit, pitch=FACING, segs=12, tube_segs=4)
    m.ring(0.0032, 0.001, at=(0, 0.0045, -1.3), mat=fit, pitch=FACING, segs=10, tube_segs=3)
    ob = m.build(name, loc=(x, 0, 0), ground=False, grime=0.0, ao=0.45, ao_dist=0.025, smooth=35)
    kit.empty("tip", (0, 0, -1.3), parent=ob, size=0.03)
    return ob


def bobber():
    """A painted cork float riding at the waterline (its origin): red above
    the water, white below, a quill on top."""
    m = MB(130)
    m.lathe([(0.0, -0.058), (0.018, -0.055), (0.035, -0.043), (0.047, -0.024), (0.052, -0.004), (0.0522, 0.002)], mat=P["paint_white"], segs=20, cap=False)
    m.lathe([(0.0522, 0.002), (0.05, 0.018), (0.042, 0.034), (0.029, 0.046), (0.013, 0.053), (0.0, 0.055)], mat=P["paint_red"], segs=20, cap=False)
    m.ring(0.0526, 0.0017, at=(0, 0.002, 0), mat=P["tar"], segs=20, tube_segs=4)
    m.cyl(0.0034, 0.0028, 0.075, at=(0, 0.05, 0), mat=P["paint_white"], segs=8, bev=0)
    m.cyl(0.003, 0.0012, 0.022, at=(0, 0.124, 0), mat=P["paint_red"], segs=8, bev=0)
    m.ring(0.0055, 0.0015, at=(0, -0.064, 0), mat=P["iron"], pitch=FACING, segs=10, tube_segs=4)
    return m.build("VM_bobber", loc=(2.0, 0, 0), ground=False, grime=0.0, ao=0.3, ao_dist=0.02, smooth=40)


# ------------------------------------------------------------ salvage hook
# The bolt-caster fires a grapnel on a line from a reel under its forestock
# (src/gather/Hook.ts). Three tiers, like the gear: rope, iron, brass.


def grapnel(name, x, tier):
    """The grapnel, eye toward you (its origin, where the line ties on), tines
    forward down -Z and curving back. Rope: three hand-forged prongs, the shank
    bound in tarred twine. Iron: four barbed tines. Brass: four flared brass
    tines on an iron shank, a band of rivets at the crown."""
    m = MB(140 + tier)
    tine = (P["iron"], P["iron_light"], P["brass"])[tier - 1]
    shank = P["iron"] if tier < 3 else Paint(IRON, 0x2E3238)
    n = 3 if tier == 1 else 4
    L = 0.075 + 0.005 * tier
    m.cyl(0.0042, 0.0048, L, at=(0, 0, 0), mat=shank, segs=8, pitch=FWD, bev=0.0008)
    m.ring(0.0085, 0.0021, at=(0, 0, 0.007), mat=shank, segs=12, tube_segs=4, roll=ACROSS)
    m.cyl(0.0072, 0.0055, 0.012, at=(0, 0, -L + 0.006), mat=tine, segs=10, pitch=FWD, centered=True, bev=0.001)
    if tier == 1:
        for k in range(7):
            m.ring(0.0052, 0.0013, at=(0, 0, -0.012 - k * 0.0045), mat=Paint(CLOTH, 0x3A3026), pitch=FACING, segs=10, tube_segs=3)
    if tier == 3:
        for k in range(6):
            a = k / 6 * math.tau
            m.uvsphere(0.0012, at=(math.cos(a) * 0.0062, math.sin(a) * 0.0062, -L + 0.004), mat=P["gilt"], segs=6, rings=4)
    flare = (0.03, 0.033, 0.038)[tier - 1]
    for k in range(n):
        a = k / n * math.tau + (math.pi / 2 if n == 3 else math.pi / 4)
        ca, sa = math.cos(a), math.sin(a)
        pts, radii = [], []
        for j in range(7):
            t = j / 6
            r = 0.005 + flare * math.sin(t * math.pi * 0.62)
            z = -L - 0.004 * math.sin(t * math.pi) + t * t * 0.046
            pts.append((ca * r, sa * r, z))
            radii.append(0.0042 - t * 0.0028)
        m.tube(pts, radii, mat=tine, segs=6)
        if tier > 1:
            # A barb inside each point.
            tx, ty, tz = pts[-2]
            m.cyl(0.0016, 0.0, 0.009, at=(tx * 0.88, ty * 0.88, tz - 0.002), mat=tine, segs=5, pitch=0.6, yaw=-a, bev=0)
    return m.build(name, loc=(x, 0, 0.5), ground=False, grime=0.0, ao=0.4, ao_dist=0.015, smooth=35)


def reel(name, x, tier):
    """The line reel clamped under the forestock: a drum of line between two
    cheeks, a crank on your side, a clamp up to the stock. Rope: oak cheeks and
    hemp. Iron: iron cheeks and tarred line. Brass: brass cheeks, a ratchet
    pawl and pale silk line. Its origin is the clamp's top."""
    m = MB(150 + tier)
    cheek = (OAK, GUNMETAL, P["brass"])[tier - 1]
    line = (Paint(CLOTH, 0xB59A6A), Paint(CLOTH, 0x3E352C), Paint(CLOTH, 0xE2DCCB))[tier - 1]
    fit = P["iron_light"] if tier < 3 else P["brass"]
    r = 0.026 + 0.002 * tier
    c = (0, -0.012 - r, 0)
    m.box((0.012, 0.014, 0.05), at=(0, -0.014, 0), mat=fit, centered=False, bev=0.0015)
    m.box((0.03, 0.004, 0.052), at=(0, -0.002, 0), mat=fit, centered=True, bev=0.001)
    for sgn in (-1, 1):
        m.cyl(r, r, 0.004, at=(sgn * 0.017, c[1], c[2]), mat=cheek, segs=24, roll=ACROSS, centered=True, bev=0.001)
        m.box((0.004, r + 0.006, 0.012), at=(sgn * 0.017, c[1], c[2]), mat=fit, centered=False, bev=0.0008)
    m.cyl(r - 0.006, r - 0.006, 0.03, at=c, mat=line, segs=20, roll=ACROSS, centered=True, bev=0)
    for k in range(5):
        m.ring(r - 0.0055, 0.0011, at=(-0.012 + k * 0.006, c[1], c[2]), mat=line, roll=ACROSS, segs=20, tube_segs=3, tint=0.85)
    m.cyl(0.0045, 0.0045, 0.042, at=c, mat=fit, segs=10, roll=ACROSS, centered=True, bev=0.0008)
    # Crank on the left, toward the lantern hand.
    arm_end = (-0.024, c[1] - r * 0.7, c[2] + 0.004)
    m.tube([(-0.021, c[1], c[2]), arm_end], 0.0025, mat=fit, segs=5)
    m.cyl(0.0042, 0.0038, 0.014, at=(arm_end[0] - 0.007, arm_end[1], arm_end[2]), mat=EBONY if tier == 3 else P["timber_pale"], roll=ACROSS, centered=True, segs=8, bev=0.001)
    if tier == 3:
        m.box((0.004, 0.003, 0.016), at=(0.02, c[1] + r * 0.6, c[2] - r * 0.4), mat=fit, pitch=0.5, centered=True, bev=0.0006)
    # The line leaves the drum's top for the muzzle.
    m.tube([(0, c[1] + r - 0.006, c[2] - 0.006), (0, -0.006, -0.05)], 0.0012, mat=line, segs=4)
    return m.build(name, loc=(x, 0, 0.8), ground=False, grime=0.0, ao=0.45, ao_dist=0.015, smooth=35)


boltcaster("VM_boltcaster_mk1", -1.0, 1)
boltcaster("VM_boltcaster_mk2", -1.5, 2)
boltcaster("VM_lamplighter", -2.0, 3)
lantern()
rod("VM_rod_basic", 1.5, False)
rod("VM_rod_reinforced", 1.7, True)
bobber()
for tier, gid in enumerate(("rope", "iron", "brass"), start=1):
    grapnel(f"VM_grapnel_{gid}", -1.0 + tier * 0.3, tier)
    reel(f"VM_reel_{gid}", -1.0 + tier * 0.3, tier)

kit.save_and_export("art/blender/viewmodels/viewmodels.blend", "public/assets/models/viewmodels.glb")
