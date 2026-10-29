"""Builds art/blender/locations/wreck.blend and public/assets/models/locations/wreck.glb.

The Wreck of the Meridian, laid out per docs/LEVELS.md (game space, metres;
water sits at y 0 at low tide and 1.8 at high tide):

  ship      stern x -34 .. stem x +42.6, beam z -18 .. -6, main deck y 6,
            stern castle (the chart room, with the Drowned Lens) at x -34 .. -25
  islet     the landing: dark layered rock under turf, its crown y 3 by the
            stern, rising south-west to a crag with the reef beacon on it; the
            boat in a gut on its west side; an abandoned salvagers' camp
  lagoon    between the islet's sheer east face and mid-ship, floor y -0.5: a
            wade at low tide, a swim at high tide
  reef      rock ribs and sand gullies south and east of the ship, low and wet
            between the islet and the breach (a swim at high water), rising to
            a belt you can wade at high water from the islet's tail to the bow;
            the ship's cargo spilled from the breach across it, an older hulk's
            ribs on its far side; its rim drops away to the open sea

Two ways up to the chart room, and the tide picks which:
  low tide   the islet's tail -> the reef -> hull breach (x -3 .. 7) -> hold
             (floor 0.3 -> 0.9) -> the ramp along the north wall -> deck hatch
  high tide  islet -> floating cargo crates (BUOY_) jammed across the lagoon
             -> the fallen mizzen (its foot hangs at y 2.6, out of reach at low
             water) -> deck
Ways down: drop through the broken stern rail onto the islet, or, once you have
the lens, the rope ladder.

Everything you walk on or bump into is a plain shape, kept as a hidden COL_
mesh, so the routes never depend on the dressing. The ship you see is built
over them: a steam-sail merchantman with a copper bottom, painted ports and a
clipper bow with a figurehead; a timbered hold; masts, yards and rigging; and a
panelled chart room with stern windows and the ship's name on the transom.

    blender -b --factory-startup --python tools/blender/build/wreck.py
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import bmesh  # noqa: E402
import bpy  # noqa: E402
import kit  # noqa: E402
from kit import B, MB, Paint, along, fbm3, look, mix, noise2, poly_sd, smoothstep  # noqa: E402

kit.reset()

TEMPLATES = kit.load_props()
HOME = kit.load_home()
P = kit.palette()
GLOW = kit.material("glow_sea", 0x3DFFB0, emit=0x3DFFB0, strength=3.0)
LIT = kit.material("glass_lit", 0xFFE2A8, emit=0xFFA040, strength=1.4)
# Two sets of dice. `rnd` lays out the level (rocks, barrels, which way nodes
# face) and is drawn in the same order as it always was, so dressing the ship
# never moves them; `vr` is the dressing's own.
rnd = random.Random(7)
vr = random.Random(77)

WOOD = P["timber"].mat
BLACK = Paint(WOOD, 0x2D2B28)
CREAM = Paint(WOOD, 0xC4B590)
CREAM_IN = Paint(WOOD, 0xB3A383)
BOOT = Paint(WOOD, 0x6A3828)
COPPER = Paint(P["copper"].mat, 0x5A8674)
DECKW = Paint(WOOD, 0x8A7D68)
HOLDW = Paint(WOOD, 0x4C3B2C)
HOLD_IN = Paint(WOOD, 0x5F4B38)
FRAME = Paint(WOOD, 0x7A6247)
BUFF = Paint(WOOD, 0xA59474)
TEAK = Paint(WOOD, 0x6E4E36)
PANEL = Paint(WOOD, 0x5A3A26)
SOOT = Paint(P["iron"].mat, 0x1C1B1A)
FUNNEL = Paint(P["paint_white"].mat, 0xA8864E)
VENT_RED = Paint(P["paint_red"].mat, 0x8E3328)
PAPER = Paint(P["cloth"].mat, 0xD9CCA8)
NIGHT = Paint(P["glass_white"].mat, 0x26343C)
TARRED = Paint(P["cloth"].mat, 0x3A3229)
FIGURE = Paint(P["paint_white"].mat, 0xD6CFBC)
SPAR = P["driftwood_dark"]
HOLD_FLOOR = Paint(kit.material("TIDE_planks", 0xFFFFFF, rough=0.9, vcol=True), 0x705C44)
IRON, RUST, ROPE, CANVAS, GILT, BRASS = P["iron"], P["rust"], P["rope"], P["canvas"], P["gilt"], P["brass"]

SEA = -3.0
DECK = 6.0
STERN, BOW_TIP = -34.0, 42.0  # the reef under the bow still ends where the old box ship did
NORTH, SOUTH = -18.0, -6.0  # hull side planes (z)
ZC = (NORTH + SOUTH) / 2
WALL = 0.4
BULWARK = 7.0
KEEL = -1.5
HB = (SOUTH - NORTH) / 2 + WALL / 2  # outside half-beam amidships
TAPER, STEM = 30.0, 42.6  # the bow narrows from TAPER to the stem (at the waterline)
SHEER_BOW = 7.75
CASTLE = -25.0  # the chart room's front wall
ROOF = 9.2


def lerp(a, b, t):
    return a + (b - a) * t


def frange(a, b, step):
    n = int(round((b - a) / step))
    return [round(a + i * step, 4) for i in range(n + 1)]


# ------------------------------------------------------------------ terrain
# The Meridian drove up onto the back of a reef and lies with her stern against
# the islet you land on. The reef runs out south and east of her: rock ribs
# with sand between, bared at low water. Off the reef and the islet the sea
# floor is swimming depth even at low water, so a fall off the outside always
# ends with the current bringing you in (the tide sweep, GDD section 6).

HW = kit.HIGH_WATER
SEA_FLOOR = SEA
# The islet's cliff top, from its north-west corner beside the stern, round by
# the hull, down its east face over the lagoon and back up its west side.
ISLET = [(-45.0, -10.5), (-38.5, -9.2), (-35.4, -7.4), (-19.8, -7.4), (-18.7, -3.0), (-19.0, 3.5), (-19.0, 9.6), (-20.3, 13.0),
         (-24.5, 16.6), (-30.0, 20.5), (-37.5, 22.0), (-44.5, 19.5), (-48.5, 13.0), (-48.2, 7.5), (-47.6, 1.0), (-48.2, -4.5)]
ISLET_SHEER = {3, 4, 5, 6}  # its faces over the lagoon drop sheer, so the floating cargo can lie close in
CRAG = (-40.5, 14.0)  # the islet's high end, where the reef beacon stands
# Where you come ashore, at the gut's head: a level ledge of rock.
LANDING = (-37.6, 4.3, 3.35)
# The boat's gut, cut into the islet's west side: (x, z, floor).
GUT = [(-57.0, 4.3, -2.4), (-47.5, 4.3, -2.1), (-42.0, 4.2, -1.7)]
# Outcrops breaking the islet's turf: (x, z, radius, height).
OUTCROPS = [(-34.0, 0.5, 2.6, 1.1), (-27.5, 8.0, 2.2, 0.9), (-43.0, -4.0, 2.4, 1.3), (-33.0, 17.0, 2.8, 1.4), (-24.0, -2.5, 1.8, 0.7)]
# The islet's tail: from its crown down to the rampart, the way out at low water
# and the way home at high.
TAIL = [(-25.0, 11.0, 2.98), (-21.0, 14.6, 2.45), (-16.5, 18.2, 1.85), (-12.0, 20.6, 1.55), (-8.5, 22.0, 1.6)]
# The rampart: the reef's rim, a ridge of rock along its south and east sides,
# dry at high water, the open sea breaking on its outside. (x, z, crest y)
# Its south-east corner rises into a knoll, the Horn, the one place you can see the whole wreck from.
RAMPART = [(-9.0, 22.4, 1.6), (-2.0, 26.8, 2.3), (10.0, 30.4, 2.8), (22.0, 31.2, 3.1), (34.0, 28.8, 3.6), (44.0, 23.8, 6.2),
           (51.5, 15.0, 3.3), (55.5, 4.0, 2.4), (54.0, -6.5, 1.9), (48.0, -13.5, 1.5), (44.5, -16.6, 0.9)]
TORS = [(16.0, 31.5, 1.0), (53.5, 9.5, 0.9), (52.0, -10.0, 0.8)]  # crags on its crest: (x, z, how big)
# Sea stacks standing in deep water round the reef: (x, z, top, how big).
STACKS = [(-57.0, 14.0, 9.5, 2.2), (-46.0, 30.0, 6.5, 1.7), (-16.0, 31.5, 5.0, 1.5), (14.0, 40.0, 7.5, 2.0), (60.0, 27.0, 11.0, 2.4),
          (64.0, -2.0, 6.0, 1.7), (55.0, -26.0, 8.0, 1.9), (-48.0, -22.0, 7.0, 1.8)]
LAGOON = [(-19.5, -6.5), (-7.0, -6.5), (-4.5, -2.0), (-4.0, 4.0), (-5.0, 10.5), (-8.0, 14.0), (-12.0, 14.5), (-16.5, 13.5), (-19.5, 10.0)]
# Between the islet and the breach the reef stays a swim at high water (the
# flood closes the low route); round that it rises to the rampart's foot, a
# wade at high water, so the rescue current never puts you back in the sea.
SWIM = [(-20.0, -6.5), (24.0, -6.5), (25.0, 3.0), (15.0, 10.0), (3.0, 14.0), (-8.0, 15.0), (-19.5, 13.5)]
# The reef flats inside the rampart (its crest is their edge), the ship's north side and the islet.
REEF = [(-36.0, -18.6), (44.0, -18.6), (48.0, -13.5), (54.0, -6.5), (55.5, 4.0), (51.5, 15.0), (44.0, 23.8), (34.0, 28.8), (22.0, 31.2),
        (10.0, 30.4), (-2.0, 26.8), (-9.0, 22.4), (-15.0, 19.0), (-22.0, 12.0), (-20.5, -6.0), (-36.0, -6.0)]
# Rock ribs running out south-east across the flats, with sand in the gullies between them.
RIBS = [[(x, z, 0.0) for x, z in rib] for rib in (
    [(-3.0, 17.5), (6.0, 21.0), (14.0, 25.5)],
    [(8.0, 9.5), (17.0, 15.0), (26.0, 19.5), (34.0, 22.5)],
    [(16.0, -1.0), (24.0, 5.5), (33.0, 11.5), (42.0, 16.0)],
    [(30.0, -6.0), (38.0, 0.0), (46.0, 6.0)],
)]
POOLS = [(-1.0, 6.0, 2.4), (15.5, 3.5, 2.6), (8.0, 24.0, 2.2), (30.0, 15.5, 2.0), (41.0, 9.0, 2.2), (22.0, 26.0, 1.8)]


def strata(h, step=0.55):
    """Rock that breaks in ledges: each `step` of height a flat, then a short rise."""
    k = math.floor(h / step)
    return (k + smoothstep(0.55, 1.0, h / step - k)) * step


_ribs = {}


def ribness(x, z):
    key = (round(x, 3), round(z, 3))
    r = _ribs.get(key)
    if r is None:
        w = 0.8 * fbm3(x * 0.3, 0.0, z * 0.3, 24)
        r = _ribs[key] = max(1 - smoothstep(0.5, 2.2, along(x, z, rib)[0] + w) for rib in RIBS)
    return r


def belt(x, z):
    """0 in the band that's a swim at high water, 1 on the belt you can wade then."""
    return smoothstep(0.0, 7.0, poly_sd(x, z, SWIM)[0] + 1.5 * fbm3(x * 0.08, 0.0, z * 0.08, 21))


def reef(x, z):
    b = belt(x, z)
    y = lerp(0.16, 0.86, b) + 0.05 * noise2(x * 0.9, z * 0.9, 22) + 0.04 * fbm3(x * 0.35, 0.0, z * 0.35, 23)
    y += ribness(x, z) * lerp(0.3, 0.45, b) * (0.75 + 0.25 * noise2(x * 0.5, z * 0.5, 25))
    for px, pz, r in POOLS:
        d = math.hypot(x - px, z - pz) + 0.5 * noise2(x * 0.8, z * 0.8, 26)
        y = min(y, lerp(-0.35, y, smoothstep(0.35 * r, r, d)))
    d = poly_sd(x, z, REEF)[0] + 2.0 * fbm3(x * 0.07, 0.0, z * 0.07, 27)
    return y if d <= 0 else y - (y - SEA_FLOOR) * smoothstep(0.0, 6.0, d)


def lagoon(x, z, y):
    d = poly_sd(x, z, LAGOON)[0] + 0.8 * fbm3(x * 0.15, 0.0, z * 0.15, 28)
    return lerp(-0.5 + 0.06 * noise2(x * 0.7, z * 0.7, 29), y, smoothstep(-0.5, 3.0, d))


def rampart(x, z):
    """A flat crest a few metres wide along the spine, an easy slope down to the
    flats inside, and outside one plunge to the sea floor."""
    d, cy, t = along(x, z, RAMPART)
    i = min(int(t), len(RAMPART) - 2)
    (ax, az, _), (bx, bz, _) = RAMPART[i], RAMPART[i + 1]
    inside = ((x - ax) * (bz - az) - (z - az) * (bx - ax)) / math.hypot(bx - ax, bz - az)  # > 0 toward the flats
    d += 1.2 * fbm3(x * 0.08, 0.0, z * 0.08, 53)
    over = max(0.0, d - 2.2 - 1.0 * (fbm3(t * 0.7, 0.0, 0.0, 54) + 0.4))
    y = lerp(cy - (cy - SEA_FLOOR) * smoothstep(0.0, 4.0, over), cy - over * over * 0.08, smoothstep(-1.5, 1.5, inside))
    y += 0.12 * noise2(x * 0.9, z * 0.9, 55) + 0.45 * fbm3(x * 0.25, 0.0, z * 0.25, 56) * smoothstep(1.5, 3.5, d)
    for tx, tz, s in TORS:
        r = math.hypot(x - tx, z - tz)
        if r < 5.0 * s:
            y += 1.5 * s * (1 - smoothstep(1.0 * s, 4.0 * s, r + 0.8 * fbm3(x * 0.5, 0.0, z * 0.5, 57)))
    return y


def islet(x, z):
    d, edge = poly_sd(x, z, ISLET)
    sheer = edge in ISLET_SHEER
    if not sheer:
        d += 1.3 * fbm3(x * 0.09, 0.0, z * 0.09, 41)
    r = math.hypot(x - CRAG[0], z - CRAG[1]) + 1.2 * fbm3(x * 0.2, 0.0, z * 0.2, 44)
    top = 2.95 + 0.55 * (fbm3(x * 0.1, 0.0, z * 0.1, 42) + 0.35) * smoothstep(-2.0, 8.0, z + 0.2 * x) + strata(6.5 * (1 - smoothstep(2.0, 13.0, r)))
    for ox, oz, orad, oh in OUTCROPS:
        k = math.hypot(x - ox, z - oz) + 0.7 * fbm3(x * 0.4, 0.0, z * 0.4, 43)
        top += strata(oh * (1 - smoothstep(0.5 * orad, orad, k)), 0.35)
    if d <= 0:
        return top
    return top - (top - SEA_FLOOR) * smoothstep(0.0, 1.0 if sheer else 3.0, d)


def under_hull(x, z):
    """Inside the hull's waterline, where the hold floor (its own mesh) is the ground."""
    if not STERN - 1.0 < x < STEM:
        return False
    half = HB if x < TAPER else HB * max(0.0, 1.0 - ((x - TAPER) / (STEM - TAPER)) ** 1.6)
    return abs(z - ZC) < half - 0.5


_heights = {}


def H(x, z):
    key = (round(x, 3), round(z, 3))
    y = _heights.get(key)
    if y is not None:
        return y
    y = max(lagoon(x, z, reef(x, z)), islet(x, z), rampart(x, z))
    y = lerp(LANDING[2] + 0.03 * noise2(x * 1.7, z * 1.7, 48), y, smoothstep(2.2, 3.8, math.hypot(x - LANDING[0], z - LANDING[1])))
    d, gy, _ = along(x, z, GUT)
    y = min(y, lerp(gy, y, smoothstep(1.4, 3.2, d + 0.4 * noise2(x * 0.6, z * 0.6, 45))))
    d, ty, _ = along(x, z, TAIL)
    y = max(y, lerp(y, ty + 0.12 * noise2(x * 1.1, z * 1.1, 47), 1.0 - smoothstep(2.4, 4.6, d + 0.6 * noise2(x * 0.4, z * 0.4, 46))))
    if under_hull(x, z):
        # Hidden under the hold floor, and too close under it to stand in.
        y = min(y, -0.6)
    _heights[key] = y
    return y


def grade(x, z):
    return math.hypot(H(x + 1, z) - H(x - 1, z), H(x, z + 1) - H(x, z - 1)) / 2


def on_islet(x, z):
    return poly_sd(x, z, ISLET)[0] < 0.6 or along(x, z, TAIL)[0] < 3.0


def color(x, z, y):
    n = fbm3(x * 0.13, 0.0, z * 0.13, 31)
    f = fbm3(x * 0.7, 0.0, z * 0.7, 32)
    steep = smoothstep(0.5, 1.0, grade(x, z) + 0.15 * f)
    # Dark layered rock: bands of lighter and darker stone up the faces, ochre lichen on the dry tops.
    band = 0.5 + 0.5 * math.sin(y * 5.2 + 1.8 * n)
    rock = mix(mix(0x4A4741, 0x67635A, 0.5 + 0.6 * n), mix(0x34322F, 0x4B4843, 0.5 + 0.6 * n), band * 0.75)
    rock = mix(rock, 0x9E8C55, smoothstep(0.35, 0.65, f) * 0.4 * smoothstep(HW + 0.6, HW + 1.4, y))
    # Barnacles in a pale band under the high-water line, weed below it.
    rock = mix(rock, mix(0x77726A, 0x8A857A, 0.5 + 0.5 * f), smoothstep(HW + 0.3, HW - 0.2, y) * smoothstep(0.4, 1.0, y) * 0.6)
    rock = mix(rock, mix(0x323C2B, 0x45503A, 0.5 + 0.5 * n), smoothstep(0.8, 0.1, y) * 0.8)
    if y < -0.4:
        # The lagoon's bed and the sea floor.
        return mix(0x27302A, 0x34402F, 0.5 + 0.5 * n)
    if on_islet(x, z) and y > HW + 0.6:
        # Turf over the crown, thin and worn, the rock showing through where it's steep.
        turf = mix(0x46533A, 0x63704A, 0.5 + 0.6 * n)
        turf = mix(turf, 0x7E7656, smoothstep(0.2, 0.55, f) * 0.45)
        return mix(turf, rock, max(steep, smoothstep(0.5, 0.8, f) * 0.7))
    if y > HW + 0.4:
        # The rampart's crest: bare rock, salt-burnt grass in its hollows.
        return mix(rock, mix(0x5E6440, 0x76744C, 0.5 + 0.5 * f), smoothstep(0.1, 0.5, n) * (1 - steep) * 0.55)
    # The flats: rock on the ribs, rippled wet sand in the gullies, weed where the water lies longest.
    ripple = 0.5 + 0.5 * math.sin(z * 1.3 + x * 0.45 + n * 3.0)
    sand = mix(0x6F6650, 0x847960, ripple * 0.6 + 0.2 * f)
    sand = mix(sand, mix(0x434E36, 0x56603E, 0.5 + 0.5 * f), smoothstep(0.45, 0.05, y) * (0.45 + 0.45 * smoothstep(-0.2, 0.4, n)))
    c = mix(sand, rock, max(steep, smoothstep(0.3, 0.65, ribness(x, z))))
    # A dark line of wrack where high water stops.
    return mix(c, 0x3E3826, smoothstep(0.2, 0.0, abs(y - HW - 0.05)) * 0.6)


ground = kit.material("TIDE_reef", 0xFFFFFF, rough=0.95, vcol=True)
kit.terrain("terrain", -70, 70, -48, 52, 1.0, H, color, ground, props={"col": 1})


def prop(kind, name, x, z, y=None, yaw=None, props=None, scale=1.0):
    """A layout prop: a random turn (yaw None) comes from `rnd`."""
    return kit.place(TEMPLATES, kind, name, (x, H(x, z) if y is None else y, z), yaw=rnd.random() * math.tau if yaw is None else yaw, props=props, scale=scale)


def dress(kind, name, x, z, y=None, yaw=None, scale=1.0):
    """A dressing prop: its turn comes from `vr`."""
    return kit.place(TEMPLATES, kind, name, (x, H(x, z) if y is None else y, z), yaw=vr.random() * math.tau if yaw is None else yaw, scale=scale)


def ramp(m, a, b, width, thick, mat=None):
    """A flat plank ramp whose top surface runs from game point a (low) to b (high)."""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    run = math.hypot(dx, dz)
    length = math.hypot(run, dy)
    pitch = math.atan2(dy, run)
    yaw = math.atan2(-dx, -dz)
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - thick / 2 / math.cos(pitch), (a[2] + b[2]) / 2)
    m.box((width, thick, length), at=mid, mat=mat, pitch=pitch, yaw=yaw, centered=True, bev=0)


def run(m, pts, w, h, mat, bev=0.015, tint=1.0):
    """Boxes along consecutive game points (rails, wales, stringers), w across and h tall, centred on them."""
    for p, q in zip(pts, pts[1:]):
        dx, dy, dz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
        L = math.sqrt(dx * dx + dy * dy + dz * dz)
        if L < 1e-4:
            continue
        m.box((L + 0.02, h, w), at=((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2), mat=mat,
              yaw=math.atan2(-dz, dx), roll=math.atan2(dy, math.hypot(dx, dz)), centered=True, bev=bev, tint=tint)


def sag(a, b, drop, n=8):
    return [(lerp(a[0], b[0], t), lerp(a[1], b[1], t) - drop * 4 * t * (1 - t), lerp(a[2], b[2], t)) for t in (k / n for k in range(n + 1))]


def prune(m):
    """Drops the vertices no face uses (the skins leave some behind at openings)."""
    loose = [v for v in m.bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(m.bm, geom=loose, context="VERTS")


# ------------------------------------------------------------ hull geometry
#
# A station s runs along the ship: amidships it is just x; past TAPER it is a
# fraction of the way to the stem, which rakes forward as it rises.


def sheer(x):
    """Top of the bulwark: level amidships, rising toward the bow."""
    return BULWARK + (SHEER_BOW - BULWARK) * smoothstep(22.0, STEM, x) ** 1.4


def stem_x(y):
    return STEM + 0.9 * smoothstep(0.5, SHEER_BOW + 0.4, y)


def bow_t(s):
    return min(1.0, max(0.0, (s - TAPER) / (STEM - TAPER)))


def station_x(s, y):
    t = bow_t(s)
    return s if t <= 0 else TAPER + t * (stem_x(y) - TAPER)


def beam(s, y):
    """Outside half-beam at station s, height y: wall-sided, a round bilge, a full bow that flares."""
    b = HB
    if y < -0.2:
        d = min(1.3, -0.2 - y)
        b -= 1.3 - math.sqrt(max(0.0, 1.69 - d * d))
    t = bow_t(s)
    if t > 0:
        p = 1.55 + 0.6 * smoothstep(-1.5, 8.6, y)
        b *= max(0.0, 1 - t ** p) ** 0.72
    return b


def inner_beam(s, y):
    b = beam(s, y)
    if s <= TAPER:
        return b - WALL
    ds = 0.05
    s0, s1 = s - ds, min(STEM, s + ds)
    slope = (beam(s1, y) - beam(s0, y)) / max(1e-6, station_x(s1, y) - station_x(s0, y))
    return max(0.0, b - WALL * math.sqrt(1 + slope * slope))


def hull_pt(s, y, side, inner=False, out=0.0):
    b = (inner_beam(s, y) if inner else beam(s, y)) + out
    return (station_x(s, y), y, ZC + side * b)


YS = [-1.5, -1.0, -0.5, -0.2, 0.15, 0.5, 0.85, 1.2, 1.55, 1.9, 2.1, 2.45, 2.8, 3.15, 3.5, 3.85, 4.2, 4.55, 4.9, 5.25, 5.5, 5.75, 6.0, 6.3]


def rows_for(s):
    top = sheer(station_x(s, 6.6))
    return YS + [(6.3 + top) / 2, top]


BOW_N = 24
BOW_S = [TAPER + (STEM - TAPER) * (1 - (1 - k / BOW_N) ** 1.35) for k in range(1, BOW_N + 1)]
DENSE = ((-4.0, 8.0), (-10.6, -7.0), (-23.6, -19.9))


def mid_stations(x0, extra=()):
    xs = set(frange(x0, TAPER, 1.0)) | {x0, TAPER, CASTLE, *extra}
    for a, b in DENSE:
        xs |= set(frange(a, b, 0.25))
    return sorted(x for x in xs if x0 - 1e-6 <= x <= TAPER + 1e-6) + BOW_S


EXT = mid_stations(-34.2)
INT = mid_stations(-33.8, extra=(CASTLE - 0.2,))

# Where the south side is broken open, per band of planking (index into rows_for):
# the breach into the hold, the notch the mizzen fell through, and the broken
# rail over the shelf. Each is at least as big as the gap in the collision.
R0 = rows_for(0.0)
BREACH, NOTCH, RAIL = {}, {}, {}
for j in range(len(R0) - 1):
    y0, y1 = R0[j], R0[j + 1]
    if y0 >= -0.5 and y1 <= 3.5 + 1e-6:
        reach = 0.3 if y1 < 2.3 else 0.55
        BREACH[j] = (-3.0 - reach * vr.random(), 7.0 + reach * vr.random())
    elif 3.5 - 1e-6 <= y0 < 4.9:
        f = (y0 - 3.5) / 1.4
        lo = -3.0 + f * 4.0 + (vr.random() - 0.5) * 1.4 - 0.2
        hi = 7.0 - f * 4.0 + (vr.random() - 0.5) * 1.4 + 0.2
        if hi - lo > 0.6:
            BREACH[j] = (lo, hi)
    if y0 >= 5.5 - 1e-6:
        NOTCH[j] = (-9.9 - 0.3 * vr.random(), -7.7 + 0.3 * vr.random())
    elif y0 >= 5.25 - 1e-6:
        NOTCH[j] = (-9.45, -8.15)
    if y0 >= 6.0 - 1e-6:
        RAIL[j] = (-23.0 - 0.25 * vr.random(), -20.5 + 0.25 * vr.random())


def opening(side, x, j):
    if side < 0:
        return False
    for table in (BREACH, NOTCH, RAIL):
        r = table.get(j)
        if r and r[0] < x < r[1]:
            return True
    return False


_butts = {}


def plank_no(tag, j, x, length=6.5):
    """Which plank along a strake x falls in: butt joints are staggered strake to strake."""
    if (tag, j) not in _butts:
        _butts[(tag, j)] = vr.random() * length
    return math.floor((x - _butts[(tag, j)]) / length)


def skin(m, xs, rows, side, inner, paint, keep):
    """Planking between stations xs and each station's rows, on one side (side -1 north, +1 south).
    paint(x, j, y, i) -> (Paint, key, tint): faces sharing a key are one plank."""
    R = [rows(s) for s in xs]
    grid = [[m.bm.verts.new(B(*hull_pt(s, y, side, inner))) for y in r] for s, r in zip(xs, R)]
    flip = (side < 0) != inner
    groups = {}
    for i in range(len(xs) - 1):
        xm = (xs[i] + xs[i + 1]) / 2
        a, b = grid[i], grid[i + 1]
        for j in range(len(a) - 1):
            ym = (R[i][j] + R[i][j + 1]) / 2
            if not keep(xm, j, ym):
                continue
            quad = (a[j], b[j], b[j + 1], a[j + 1])
            f = m.bm.faces.new(tuple(reversed(quad)) if flip else quad)
            pm, key, tint = paint(xm, j, ym, i)
            groups.setdefault((pm, key, tint), []).append(f)
    for (pm, _key, tint), faces in groups.items():
        m._paint(faces, pm, 0.05, tint)


def outside_paint(side):
    def paint(x, j, y, i):
        if y < 2.05:  # copper sheets, each its own shade
            return COPPER, ("cu", side, i, j), 1.0 - 0.07 * ((i + j) % 2)
        pm = BOOT if y < 2.45 else CREAM if 4.9 <= y < 5.5 else BLACK
        return pm, ("ext", side, j, plank_no(("ext", side), j, x)), 1.0 if j % 2 else 0.92
    return paint


def inside_paint(side):
    def paint(x, j, y, i):
        pm = HOLD_IN if y < DECK else BUFF
        return pm, ("int", side, j, plank_no(("int", side), j, x, 5.0)), 1.0 if j % 2 else 0.9
    return paint


def flat_face(m, x, rows, face, paint, inner=False, n=16):
    """A flat athwartships face at x (the transom, a bulkhead); face -1 looks aft, +1 forward."""
    grid = []
    for y in rows:
        b = beam(STERN, y) - (WALL if inner else 0.0)
        grid.append([m.bm.verts.new(B(x, y, ZC - b + 2 * b * k / n)) for k in range(n + 1)])
    groups = {}
    for r in range(len(rows) - 1):
        ym = (rows[r] + rows[r + 1]) / 2
        for k in range(n):
            quad = (grid[r][k], grid[r][k + 1], grid[r + 1][k + 1], grid[r + 1][k])
            f = m.bm.faces.new(quad if face < 0 else tuple(reversed(quad)))
            pm, key, tint = paint(k, r, ym)
            groups.setdefault((pm, key, tint), []).append(f)
    for (pm, _key, tint), faces in groups.items():
        m._paint(faces, pm, 0.05, tint)


def window(m, c, axis, out, w, h, glass, frame=CREAM, sill=True):
    """Glass with a frame and glazing bars on a wall. c is the bottom centre on
    the wall's surface; the wall faces along `axis` ("x" or "z") toward `out` (+1/-1)."""
    x, y, z = c

    def piece(du, dv, sw, sh, depth, mat, off):
        if axis == "z":
            m.box((sw, sh, depth), at=(x + du, y + dv, z + out * off), mat=mat, bev=0.008)
        else:
            m.box((depth, sh, sw), at=(x + out * off, y + dv, z + du), mat=mat, bev=0.008)

    piece(0, 0, w, h, 0.03, glass, 0.0)
    for du in (-(w / 2 + 0.04), w / 2 + 0.04):
        piece(du, -0.04, 0.08, h + 0.08, 0.08, frame, 0.03)
    for dv in (-0.08, h):
        piece(0, dv, w + 0.16, 0.08, 0.08, frame, 0.03)
    piece(0, 0, 0.035, h, 0.05, frame, 0.03)
    piece(0, h * 0.5 - 0.0175, w, 0.035, 0.05, frame, 0.03)
    if sill:
        piece(0, -0.14, w + 0.34, 0.06, 0.16, frame, 0.06)


# ---------------------------------------------------------------- collision
#
# The shapes the game actually collides with. Kept from the blockout (only the
# bow follows the new hull) and hidden in game.


def bow_walls(m):
    """The bow's two sides as boxes along its curve: low ones follow the hull
    where you wade, high ones the flared bulwark you stand behind on deck."""
    ss = [TAPER - 0.4, TAPER] + BOW_S
    for side in (-1, 1):
        for y_ref, y0, y1 in ((1.5, KEEL, 4.0), (6.6, 4.0, None)):
            pts = [(station_x(s, y_ref), ZC + side * beam(s, y_ref)) for s in ss]
            for (xa, za), (xb, zb) in zip(pts, pts[1:]):
                dx, dz = xb - xa, zb - za
                L = math.hypot(dx, dz)
                if L < 1e-4:
                    continue
                nx, nz = side * dz / L, -side * dx / L  # inward
                top = y1 if y1 is not None else max(sheer(xa), sheer(xb))
                m.box((L + 0.3, top - y0, WALL), at=((xa + xb) / 2 + nx * WALL / 2, y0, (za + zb) / 2 + nz * WALL / 2), yaw=math.atan2(-dz, dx), bev=0)


def bow_outline(y, ss=None):
    """The inside of the bow at height y, as an (x, z) loop from amidships round the stem."""
    ss = ss or [TAPER - 0.3, TAPER] + BOW_S
    north = [(station_x(s, y), ZC - inner_beam(s, y)) for s in ss]
    south = [(station_x(s, y), ZC + inner_beam(s, y)) for s in reversed(ss)]
    out = []
    for p in north + south:
        if not out or math.dist(p, out[-1]) > 0.02:
            out.append(p)
    if math.dist(out[0], out[-1]) < 0.02:
        out.pop()
    return out


def slab(m, outline, y0, y1, mat=None):
    """A flat slab between y0 and y1 over an (x, z) outline."""
    top = [m.bm.verts.new(B(x, y1, z)) for x, z in outline]
    bot = [m.bm.verts.new(B(x, y0, z)) for x, z in outline]
    faces = [m.bm.faces.new(top), m.bm.faces.new(list(reversed(bot)))]
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        faces.append(m.bm.faces.new((bot[i], bot[j], top[j], top[i])))
    bmesh.ops.recalc_face_normals(m.bm, faces=faces)
    # recalc can guess wrong on a long, thin slab with a many-sided top: make sure the top faces up.
    faces[0].normal_update()
    if faces[0].normal.z < 0:
        bmesh.ops.reverse_faces(m.bm, faces=faces)
    m._paint(faces, mat or DECKW)


col = MB()
col.box((TAPER - STERN, BULWARK - KEEL, WALL), at=((STERN + TAPER) / 2, KEEL, NORTH), bev=0)
# South side in pieces: broken rail over the shelf, the mast notch, the breach.
for x0, x1, top in ((STERN, -23.0, BULWARK), (-23.0, -20.5, DECK), (-20.5, -9.9, BULWARK), (-9.9, -7.7, 5.5), (-7.7, -3.0, BULWARK), (7.0, TAPER, BULWARK)):
    col.box((x1 - x0, top - KEEL, WALL), at=((x0 + x1) / 2, KEEL, SOUTH), bev=0)
col.box((10.0, BULWARK - 3.5, WALL), at=(2.0, 3.5, SOUTH), bev=0)  # above the breach
bow_walls(col)
col.box((WALL, DECK - KEEL, SOUTH - NORTH), at=(TAPER + WALL / 2, KEEL, ZC), bev=0)  # bulkhead: hold / bow
col.box((WALL, 9.5 - KEEL, SOUTH - NORTH + WALL), at=(STERN, KEEL, ZC), bev=0)  # transom, up to the castle roof
col.build("COL_hull", ao=0, grime=0)

# Planks spilling out of the breach: an easy ramp from the flats into the hold.
spill = MB()
ramp(spill, (2.0, 0.12, -2.8), (2.0, 0.34, -6.7), 9.5, 0.25)
spill.build("COL_breach_spill", ao=0, grime=0)

DT = 0.3
deck_col = MB()
# The hatch over the hold ramp is open: x -24 .. -16, z -18 .. -15.3.
deck_col.box((-24.0 - STERN, DT, SOUTH - NORTH), at=((STERN - 24.0) / 2, DECK - DT, ZC), bev=0)
deck_col.box((8.0, DT, SOUTH - (-15.3)), at=(-20.0, DECK - DT, (-15.3 + SOUTH) / 2), bev=0)
deck_col.box((TAPER + 16.0, DT, SOUTH - NORTH), at=((TAPER - 16.0) / 2, DECK - DT, ZC), bev=0)
slab(deck_col, bow_outline(DECK), DECK - DT, DECK)
deck_col.build("COL_deck", ao=0, grime=0)


def hold_floor(x, z):
    # 0.3 at the breach and forward, rising to 0.9 toward the stern.
    return lerp(0.3, 0.9, smoothstep(0.0, -12.0, x)) + 0.03 * noise2(x * 2, z * 2, 6)


kit.terrain("COL_hold_floor", STERN + WALL, TAPER, NORTH, SOUTH, 0.6, hold_floor, lambda x, z, y: 0x4E3D2E, kit.material("TIDE_planks", 0xFFFFFF, rough=0.9, vcol=True), shade=False)

# The ramp in the hold, along the north wall, up through the hatch.
RAMP_A, RAMP_B = (-9.5, 0.74, -16.7), (-24.0, DECK, -16.7)
RAMP_POSTS = [-11.0 - i * 2.4 for i in range(6)]


def ramp_y(x):
    return RAMP_A[1] + (DECK - RAMP_A[1]) * (RAMP_A[0] - x) / (RAMP_A[0] - RAMP_B[0])


inner = MB()
ramp(inner, RAMP_A, RAMP_B, 2.0, 0.3)
for x in RAMP_POSTS:
    inner.cyl(0.12, 0.12, max(0.2, ramp_y(x) - 0.3), at=(x, 0.3, -15.85), segs=6, bev=0)
inner.build("COL_hold_ramp", ao=0, grime=0)

# The fallen mizzen: its foot hangs at 2.6, 1.2 m over anything you can stand
# on at low tide.
MAST_FOOT = (-8.8, 2.6, 10.0)
MAST_TOP = (-8.8, DECK, -7.3)
mast_col = MB()
ramp(mast_col, MAST_FOOT, MAST_TOP, 1.6, 0.22)
mast_col.build("COL_mast_ramp", ao=0, grime=0)

# The stern castle (chart room): front wall with a door, roof, raised sides.
CR_X0, CR_X1 = STERN, CASTLE
CH = ROOF - DECK
castle_col = MB()
castle_col.box((WALL, CH, -13.2 - NORTH), at=(CR_X1, DECK, (NORTH - 13.2) / 2), bev=0)
castle_col.box((WALL, CH, SOUTH - (-10.8)), at=(CR_X1, DECK, (-10.8 + SOUTH) / 2), bev=0)
castle_col.box((WALL, CH - 2.4, 2.4), at=(CR_X1, DECK + 2.4, -12.0), bev=0)
castle_col.box((CR_X1 - CR_X0, 0.3, SOUTH - NORTH + WALL), at=((CR_X0 + CR_X1) / 2, ROOF, ZC), bev=0)
for zs in (NORTH, SOUTH):
    castle_col.box((CR_X1 - CR_X0, ROOF - BULWARK, WALL), at=((CR_X0 + CR_X1) / 2, BULWARK, zs), bev=0)
castle_col.build("COL_chart_room", ao=0, grime=0)

furn_col = MB()
furn_col.box((2.4, 0.9, 1.4), at=(-27.6, DECK, -15.6), bev=0)  # chart table
furn_col.box((0.5, 2.2, 3.0), at=(-33.4, DECK, -9.0), bev=0)  # chart case
furn_col.box((2.2, 0.95, 1.0), at=(-32.6, DECK, -17.3), bev=0)  # bunk
furn_col.box((1.0, 0.6, 0.6), at=(-30.8, DECK, -17.45), bev=0)  # sea chest
furn_col.build("COL_chart_room_furniture", ao=0, grime=0)

# Funnel, masts, bowsprit and the deck fittings you'd bump into.
FUNNEL_X, MAIN_X, FORE_X, MIZZEN_X = -4.0, 6.0, 22.0, -8.8
BOWSPRIT = ((39.6, 7.45, ZC), (50.6, 11.45, ZC))
rig_col = MB()
rig_col.cyl(1.1, 1.0, 5.5, at=(FUNNEL_X, DECK, ZC), segs=14, bev=0)
rig_col.cyl(1.15, 1.15, 0.4, at=(FUNNEL_X, DECK + 5.5, ZC), segs=14, bev=0)
rig_col.cyl(0.45, 0.35, 15.0, at=(MAIN_X, DECK, ZC), segs=10, bev=0)
rig_col.cyl(0.12, 0.12, 9.0, at=(MAIN_X, DECK + 10.5, ZC), segs=6, pitch=math.pi / 2, centered=True, bev=0)
rig_col.cyl(0.9, 1.0, 0.8, at=(MAIN_X, DECK + 12.0, ZC), segs=10, bev=0)
rig_col.cyl(0.43, 0.4, 7.5, at=(FORE_X, DECK, ZC), segs=10, bev=0)
rig_col.cyl(0.44, 0.42, 1.9, at=(MIZZEN_X, DECK, ZC), segs=10, bev=0)
(bx0, by0, _), (bx1, by1, _) = BOWSPRIT
rig_col.cyl(0.3, 0.2, math.hypot(bx1 - bx0, by1 - by0), at=BOWSPRIT[0], segs=8, roll=-(math.pi / 2 - math.atan2(by1 - by0, bx1 - bx0)), bev=0)
for z in (ZC - 2.4, ZC + 2.4):
    rig_col.cyl(0.26, 0.26, 2.3, at=(-1.5, DECK, z), segs=8, bev=0)  # cowl vents
rig_col.box((2.6, 0.75, 1.8), at=(1.6, DECK, ZC), bev=0)  # engine-room skylight
rig_col.cyl(0.56, 0.56, 1.12, at=(11.0, DECK, ZC), segs=10, bev=0)  # capstan
rig_col.box((3.0, 0.55, 2.6), at=(19.5, DECK, ZC), bev=0)  # fore hatch
for z in (ZC - 1.4, ZC + 1.4):
    rig_col.box((0.34, 0.95, 0.34), at=(24.2, DECK, z), bev=0)  # towing bitts
rig_col.box((0.9, 1.25, 3.4), at=(36.4, DECK, ZC), bev=0)  # windlass
rig_col.build("COL_fittings", ao=0, grime=0)

# --------------------------------------------------------- the ship you see

# ---- outside: planking, wales, ports, rails, channels, stern and bow

hull = MB(11)
for side in (-1, 1):
    skin(hull, EXT, rows_for, side, False, outside_paint(side), lambda x, j, y, side=side: not opening(side, x, j))

CASTLE_ROWS = [BULWARK, 7.35, 7.7, 8.05, 8.4, 8.75, ROOF]
CX = [s for s in EXT if s <= CASTLE + 1e-6]
for side in (-1, 1):
    skin(hull, CX, lambda s: CASTLE_ROWS, side, False,
         lambda x, j, y, i, side=side: (CREAM, ("castle", side, j), 1.0) if j == 5 else (BLACK, ("castle", side, j, plank_no(("castle", side), j, x)), 1.0 if j % 2 else 0.92),
         lambda x, j, y: True)

TRANSOM_ROWS = YS + [6.65, 7.0, 7.35, 7.7, 8.05, 8.4, 8.75, ROOF]


def transom_paint(k, r, y):
    if y < 2.05:
        return COPPER, ("tcu", k, r), 1.0 - 0.07 * ((k + r) % 2)
    pm = BOOT if y < 2.45 else CREAM if (4.9 <= y < 5.5 or y > 8.75) else BLACK
    return pm, ("t", r, k // 7), 1.0 if r % 2 else 0.92


flat_face(hull, STERN - WALL / 2, TRANSOM_ROWS, -1, transom_paint)

# Stout corner posts where the sides meet the transom.
for side in (-1, 1):
    hull.box((0.34, ROOF + 0.3 - 0.3, 0.34), at=(STERN - 0.12, 0.3, ZC + side * (HB - 0.05)), mat=BLACK, bev=0.05)

# Wales: thick strakes standing proud, broken over the breach.
RUN_X = sorted(set(frange(-34.0, TAPER, 2.0)) | {-23.0, -20.5, -9.9, -7.7, -3.6, 7.6, TAPER})
WALE_S = RUN_X + BOW_S[:-1]
for side in (-1, 1):
    seg = []
    for s in WALE_S:
        if side > 0 and -3.6 < s < 7.6:
            run(hull, seg, 0.22, 0.35, BLACK)
            seg = []
            continue
        x, y, z = hull_pt(s, 4.03, side, out=0.05)
        seg.append((x, y, z))
    run(hull, seg, 0.22, 0.35, BLACK)

# A cream moulding along the sheer strake and a teak cap on the rail, both
# broken where the side is.
for side in (-1, 1):
    for y_of, w, h, mat, out in ((lambda s: 6.3, 0.07, 0.08, CREAM, 0.02), (lambda s: rows_for(s)[-1] + 0.05, 0.56, 0.12, TEAK, -WALL / 2)):
        seg = []
        for s in [x for x in RUN_X if x >= CASTLE] + BOW_S[:-1]:
            x = station_x(s, 6.6)
            broken = side > 0 and (-23.0 < x < -20.5 or -9.9 < x < -7.7)
            if broken:
                run(hull, seg, w, h, mat)
                seg = []
                continue
            seg.append(hull_pt(s, y_of(s), side, out=out))
        run(hull, seg, w, h, mat)
# The castle's own rail cap, at the poop.
for side in (-1, 1):
    run(hull, [(STERN - 0.2, ROOF + 0.06, ZC + side * (HB - WALL / 2)), (CASTLE + 0.15, ROOF + 0.06, ZC + side * (HB - WALL / 2))], 0.56, 0.12, TEAK)
run(hull, [(STERN - 0.2, ROOF + 0.06, ZC - HB), (STERN - 0.2, ROOF + 0.06, ZC + HB)], 0.5, 0.12, TEAK)

# Painted ports along the cream band, the old merchantman's chequer.
for side in (-1, 1):
    for k in range(22):
        x = -22.0 + k * 2.4
        if x > 27.5 or -10.8 < x < -6.8 or 3.6 < x < 8.4 or 19.6 < x < 24.4:
            continue
        hull.box((0.72, 0.42, 0.04), at=(x, 4.99, ZC + side * (HB + 0.012)), mat=BLACK, tint=0.75, bev=0.006)

# Channels at the masts: ledges with deadeyes for the shrouds, chain plates down the side.
SHROUD_FEET = {}
for mx in (MAIN_X, FORE_X):
    for side in (-1, 1):
        zc = ZC + side * (HB + 0.31)
        hull.box((3.6, 0.1, 0.62), at=(mx, 6.5, zc), mat=BLACK, bev=0.02)
        feet = []
        for dx in (-1.1, 0.0, 1.1):
            dz = ZC + side * (HB + 0.55)
            hull.cyl(0.11, 0.11, 0.08, at=(mx + dx, 6.78, dz), mat=TEAK, pitch=math.pi / 2, centered=True, segs=10)
            hull.box((0.07, 6.7 - 4.55, 0.04), at=(mx + dx, 4.55, ZC + side * (HB + 0.03)), mat=IRON, bev=0.008)
            hull.box((0.05, 0.6, 0.04), at=(mx + dx, 6.45, dz), mat=IRON, bev=0.006)
            feet.append((mx + dx, 6.9, dz))
        SHROUD_FEET[(mx, side)] = feet
        # Rust bleeding down from the chain plates.
        for dx in (-1.1, 0.0, 1.1):
            hull.box((0.12, 1.3, 0.012), at=(mx + dx + 0.04, 3.2, ZC + side * (HB + 0.008)), mat=RUST, tint=0.8, jit=0.15, bev=0)

# Stern windows, lit: someone has a lamp burning in the chart room.
for dz in (-4.2, -2.1, 0.0, 2.1, 4.2):
    window(hull, (STERN - WALL / 2, 7.35, ZC + dz), "x", -1, 1.05, 0.95, LIT)
# The name board.
hull.box((0.06, 0.62, 4.6), at=(STERN - WALL / 2 - 0.02, 6.32, ZC), mat=BLACK, bev=0.015)
for dv in (6.3, 6.92):
    hull.box((0.08, 0.05, 4.7), at=(STERN - WALL / 2 - 0.03, dv, ZC), mat=GILT, bev=0.008)


def lettering(m, text, at, size, mat):
    """Raised letters on the transom, reading from astern (game +z is to your right)."""
    cu = bpy.data.curves.new("lettering", "FONT")
    cu.body = text
    cu.size = size
    cu.extrude = 0.012
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.space_character = 1.15
    ob = bpy.data.objects.new("lettering", cu)
    bpy.context.scene.collection.objects.link(ob)
    deps = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(deps))
    bpy.data.objects.remove(ob)
    tmp = bmesh.new()
    tmp.from_mesh(me)
    x0, y0, z0 = at
    vmap = {v: m.bm.verts.new(B(x0 - v.co.z, y0 + v.co.y, z0 + v.co.x)) for v in tmp.verts}
    faces = [m.bm.faces.new([vmap[v] for v in f.verts]) for f in tmp.faces]
    m._paint(faces, mat, 0.02)
    tmp.free()
    bpy.data.meshes.remove(me)


lettering(hull, "MERIDIAN", (STERN - WALL / 2 - 0.05, 6.63, ZC), 0.42, GILT)

# Quarter galleries: bay windows at the stern's corners.
for side in (-1, 1):
    zf = ZC + side * (HB + 0.6)
    gx0, gx1 = STERN - WALL / 2 - 0.1, STERN + 2.35
    gm = (gx0 + gx1) / 2
    hull.box((gx1 - gx0, 2.2, 0.62), at=(gm, 6.75, ZC + side * (HB + 0.29)), mat=CREAM, bev=0.03)
    hull.box((gx1 - gx0 + 0.2, 0.14, 0.78), at=(gm, 8.95, ZC + side * (HB + 0.33)), mat=TEAK, bev=0.02)
    hull.box((gx1 - gx0 - 0.3, 0.2, 0.5), at=(gm, 9.09, ZC + side * (HB + 0.25)), mat=P["copper"], bev=0.04)
    hull.box((gx1 - gx0 - 0.4, 0.32, 0.46), at=(gm, 6.43, ZC + side * (HB + 0.23)), mat=CREAM, bev=0.05)
    hull.cyl(0.02, 0.12, 0.4, at=(gm, 6.03, ZC + side * (HB + 0.25)), mat=GILT, segs=8)
    for dx in (-0.62, 0.62):
        window(hull, (gm + dx, 7.25, zf), "z", side, 0.85, 1.1, LIT, frame=GILT, sill=False)
    window(hull, (gx0 - 0.01, 7.25, ZC + side * (HB + 0.3)), "x", -1, 0.4, 1.1, LIT, frame=GILT, sill=False)

# Castle side windows (the rope ladder hangs from the south one's sill at x -29.5).
for side in (-1, 1):
    for x in (-29.5, -26.6):
        window(hull, (x, 7.1, ZC + side * (HB + 0.01)), "z", side, 0.9, 0.8, LIT)
    # The break of the poop: a post where the rail steps up to the castle.
    hull.box((0.36, ROOF + 0.12 - DECK, 0.56), at=(CASTLE + 0.06, DECK, ZC + side * (HB - 0.2)), mat=CREAM, bev=0.04)
    hull.uvsphere(0.13, at=(CASTLE + 0.06, ROOF + 0.25, ZC + side * (HB - 0.2)), mat=GILT, segs=10, rings=6)

# Hawse pipes and catheads at the bow.
HAWSE_S = TAPER + (STEM - TAPER) * 0.8
for side in (-1, 1):
    hx, hy, hz = hull_pt(HAWSE_S, 5.55, side, out=0.04)
    yaw = side * 0.95
    hull.ring(0.2, 0.055, at=(hx, hy, hz), mat=IRON, pitch=math.pi / 2, yaw=yaw, segs=12, tube_segs=5)
    hull.cyl(0.17, 0.17, 0.05, at=(hx, hy, hz), mat=SOOT, pitch=math.pi / 2, yaw=yaw, centered=True, segs=12)
CAT_S = TAPER + (STEM - TAPER) * 0.62
CATHEADS = {}
for side in (-1, 1):
    cx, cy, cz = hull_pt(CAT_S, 7.35, side, out=-0.3)
    ex, ey, ez = hull_pt(CAT_S + 0.9, 7.45, side, out=1.0)
    run(hull, [(cx, cy, cz), (ex, ey, ez)], 0.34, 0.34, BLACK)
    hull.box((0.1, 0.36, 0.38), at=(ex + 0.05, ey - 0.18, ez), mat=GILT, bev=0.01, yaw=side * 0.5)
    CATHEADS[side] = (ex, ey, ez)

# The stem, raking forward, and the head knee under the bowsprit.
stem_pts = [(stem_x(y) + 0.1, y, ZC) for y in (-1.5, -0.5, 0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.4, SHEER_BOW + 0.3)]
hull.tube(stem_pts, 0.21, mat=BLACK, segs=6)
hull.tube([(stem_x(5.2) + 0.15, 5.2, ZC), (stem_x(6.2) + 0.55, 6.25, ZC), (stem_x(7.2) + 0.85, 7.15, ZC)], [0.16, 0.2, 0.18], mat=BLACK, segs=6)
# Gilt trail boards: scrolls running aft from the head.
for side in (-1, 1):
    pts = [hull_pt(TAPER + (STEM - TAPER) * t, 6.0 + 0.5 * t, side, out=0.05) for t in (0.62, 0.72, 0.82, 0.9, 0.96)]
    hull.tube(pts, 0.045, mat=GILT, segs=5)
    x, y, z = pts[0]
    hull.ring(0.13, 0.04, at=(x - 0.1, y - 0.05, z), mat=GILT, pitch=math.pi / 2, yaw=side * 0.25, segs=10, tube_segs=4)

# Barnacles and weed along the waterline.
for k in range(300):
    side = -1 if k % 2 else 1
    s = vr.uniform(-33.5, STEM - 1.5)
    y = vr.uniform(-0.4, 1.85) if vr.random() < 0.8 else vr.uniform(1.85, 2.4)
    if side > 0 and -3.4 < s < 7.4 and y < 3.5:
        continue
    x, y, z = hull_pt(s, y, side, out=0.0)
    r = 0.03 + vr.random() * 0.05
    hull.cyl(r, r * 0.35, r * 1.1, at=(x, y, z), mat=P["barnacle"], pitch=side * math.pi / 2, segs=5, bev=0, jit=0.12)
for k in range(46):
    side = -1 if k % 2 else 1
    s = vr.uniform(-33.0, STEM - 2.0)
    if side > 0 and -3.6 < s < 7.6:
        continue
    y0 = 1.5 + vr.random() * 0.35
    L = 0.5 + vr.random() * 0.8
    pts = [hull_pt(s + 0.08 * math.sin(t * 5 + k), y0 - L * t, side, out=0.02 + 0.03 * t) for t in (0.0, 0.33, 0.66, 1.0)]
    hull.tube(pts, [0.03, 0.025, 0.02, 0.01], mat=P["kelp"] if k % 3 else P["kelp_dark"], segs=4)

prune(hull)
hull.build("ship_hull", ground=False, grime=0.0, tideline=True, smooth=40, ao=0.7)

# The rudder, hung on the sternpost: solid, since you can swim into it.
rud = MB(12)
rud.box((1.5, 7.6, 0.36), at=(STERN - 0.95, KEEL, ZC), mat=BLACK, bev=0.05)
rud.box((1.5, 2.05 - KEEL + 0.05, 0.38), at=(STERN - 0.95, KEEL - 0.03, ZC), mat=COPPER, bev=0.05)
rud.cyl(0.2, 0.2, 2.6, at=(STERN - 0.35, 6.0, ZC), mat=BLACK, segs=8)
for y in (0.2, 1.7, 3.2, 4.7):
    rud.box((1.55, 0.14, 0.42), at=(STERN - 0.95, y, ZC), mat=IRON, bev=0.01)
rud.build("rudder", tideline=True, grime=0.0, props={"col": 1})

# ---- the hold: inside planking, frames and beams, the bulkhead, floorboards,
# the ramp and the breach

hold = MB(13)
for side in (-1, 1):
    skin(hold, INT, rows_for, side, True, inside_paint(side), lambda x, j, y, side=side: 0.15 < y < DECK and x < TAPER and not opening(side, x, j))
flat_face(hold, STERN + WALL / 2, YS[4:23], 1, lambda k, r, y: (HOLD_IN, ("aft", r, k // 6), 1.0 if r % 2 else 0.9), inner=True)

FRAME_X = frange(-32.0, 28.0, 1.5)
for x in FRAME_X:
    for side in (-1, 1):
        if side > 0 and -3.4 < x < 7.4:
            continue
        hold.box((0.22, 5.56 - 0.2, 0.2), at=(x, 0.2, ZC + side * (HB - WALL - 0.08)), mat=FRAME, tint=0.9)
    z0, z1 = NORTH + WALL / 2, SOUTH - WALL / 2
    if -24.0 <= x <= -16.0:
        z0 = -15.3
    hold.box((0.26, 0.42, z1 - z0), at=(x, 5.56, (z0 + z1) / 2), mat=FRAME, tint=0.85)
# Framing round the hatch.
for x in (-24.0, -16.0):
    hold.box((0.3, 0.42, 2.5), at=(x, 5.56, -16.55), mat=HOLDW, tint=0.75)
hold.box((8.3, 0.42, 0.3), at=(-20.0, 5.56, -15.3), mat=HOLDW, tint=0.75)

# The bulkhead closing off the bow, planked upright.
BH = TAPER - 0.02
grid = []
bz = [NORTH + WALL / 2 + k * (SOUTH - NORTH - WALL) / 38 for k in range(39)]
for y in (0.25, DECK):
    grid.append([hold.bm.verts.new(B(BH, y, z)) for z in bz])
for k in range(38):
    f = hold.bm.faces.new((grid[0][k], grid[0][k + 1], grid[1][k + 1], grid[1][k]))
    hold._paint([f], HOLD_IN, 0.08, 0.95 if k % 2 else 0.85)
for y in (1.6, 3.4, 5.0):
    hold.box((0.2, 0.3, SOUTH - NORTH - WALL), at=(BH - 0.1, y, ZC), mat=FRAME, tint=0.8)

# Floorboards over the hold's collision floor (a touch above it, and flat
# where it's lumpy), sanded with silt by the breach and dark where it's damp.


def floor_y(x):
    return lerp(0.3, 0.9, smoothstep(0.0, -12.0, x)) + 0.035


FZ = [NORTH + WALL / 2 + k * 0.29 for k in range(41)]
FX = frange(STERN + WALL / 2, TAPER, 1.0)
for k in range(len(FZ) - 1):
    z0, z1 = FZ[k], FZ[k + 1] - 0.012
    zm = (z0 + z1) / 2
    for i in range(len(FX) - 1):
        x0, x1 = FX[i], FX[i + 1]
        xm = (x0 + x1) / 2
        silt = smoothstep(7.0, 0.0, abs(xm - 2.0)) * smoothstep(-12.0, -6.5, zm)
        damp = smoothstep(0.2, 0.55, fbm3(xm * 0.4, 0.0, zm * 0.4, 41))
        quad = [hold.bm.verts.new(B(x, floor_y(x), z)) for x, z in ((x0, z0), (x0, z1), (x1, z1), (x1, z0))]
        f = hold.bm.faces.new(quad)
        tint = (1.0 if k % 2 else 0.9) * (1 - 0.35 * damp)
        hold._paint([f], Paint(HOLD_FLOOR.mat, mix(HOLD_FLOOR.color, 0x7A7058, silt * 0.85)), 0.06, tint)

# The hold ramp: treads on two stringers, square posts under it.
rdx, rdy = RAMP_B[0] - RAMP_A[0], RAMP_B[1] - RAMP_A[1]
rlen = math.hypot(rdx, rdy)
phi = math.atan2(rdy, -rdx)
nrm = (math.sin(phi), math.cos(phi))
for zs in (-17.55, -15.85):
    a = (RAMP_A[0] - 0.3 - nrm[0] * 0.24, RAMP_A[1] - 0.12 - nrm[1] * 0.24, zs)
    b = (RAMP_B[0] - nrm[0] * 0.24, RAMP_B[1] - nrm[1] * 0.24, zs)
    run(hold, [a, b], 0.14, 0.34, TEAK, tint=0.8)
n_treads = int(rlen / 0.34)
for i in range(n_treads):
    t = (i + 0.5) / n_treads
    x = RAMP_A[0] + rdx * t - nrm[0] * 0.03
    y = RAMP_A[1] + rdy * t - nrm[1] * 0.03
    hold.box((0.3, 0.06, 2.0), at=(x, y, -16.7), mat=TEAK, roll=-phi, centered=True, bev=0.01, tint=0.85 + 0.15 * vr.random())
for x in RAMP_POSTS:
    hold.box((0.24, ramp_y(x) - 0.42, 0.24), at=(x, 0.3, -15.85), mat=FRAME, tint=0.9)

# The breach: its edge frames, broken frame ends hanging from the top, and
# boards spilled out over the reef.
for x in (-3.15, 7.15):
    hold.box((0.3, 6.2, 0.38), at=(x, -0.6, SOUTH), mat=HOLDW, tint=0.75)
for x in (-1.9, -0.4, 1.1, 2.6, 4.1, 5.6):
    top = 3.5 + 0.3
    bottom = 2.75 + vr.random() * 0.55
    hold.box((0.24, top - bottom, 0.34), at=(x, bottom, SOUTH), mat=HOLDW, tint=0.8, roll=(vr.random() - 0.5) * 0.25)
    hold.prism([(-0.1, 0.0), (0.1, 0.0), (0.03, -0.22)], 0.3, at=(x, bottom, SOUTH), mat=TEAK, tint=0.9)
for k, x in enumerate((-2.2, -0.9, 0.6, 2.2, 3.4, 5.1, 6.3)):
    # Strakes snapped and bent down over the hole.
    L = 0.9 + vr.random() * 0.7
    hold.box((0.32, 0.06, L), at=(x, 3.55 - L * 0.45, SOUTH + 0.1), mat=BLACK if k % 2 else CREAM if k == 2 else BLACK, pitch=-1.1 - vr.random() * 0.3, yaw=(vr.random() - 0.5) * 0.5, centered=True, bev=0.006, tint=0.85)
for side_x, d in ((-3.0, -1), (7.0, 1)):
    for k in range(6):
        y = 0.8 + k * 0.5 + vr.random() * 0.3
        L = 0.2 + vr.random() * 0.35
        hold.box((L, 0.035, 0.1 + vr.random() * 0.08), at=(side_x + d * 0.1 - d * L / 2, y, SOUTH + 0.22), mat=BLACK if k % 2 else HOLDW, yaw=(vr.random() - 0.5) * 0.5, roll=(vr.random() - 0.5) * 0.6, centered=True, bev=0.004)
for k in range(9):
    x = vr.uniform(-2.8, 6.8)
    y = 3.5 + vr.random() * 0.8
    L = 0.25 + vr.random() * 0.35
    hold.box((0.12, 0.04, L), at=(x, y, SOUTH + 0.2 + L / 2), mat=BLACK, pitch=0.3 + vr.random() * 0.5, yaw=(vr.random() - 0.5) * 0.6, centered=True, bev=0.004)

for k in range(14):
    x = -2.45 + k * 0.68 + (vr.random() - 0.5) * 0.12
    w = 0.5 + vr.random() * 0.15
    L = 3.6 + vr.random() * 0.6
    zc = -4.75 + (vr.random() - 0.5) * 0.4
    y = 0.12 + (0.34 - 0.12) * (-2.8 - zc) / 3.9 - 0.02 + (vr.random() - 0.5) * 0.03
    hold.box((w, 0.05, L), at=(x, y, zc), mat=BLACK if k % 3 == 0 else HOLDW, pitch=0.056, yaw=(vr.random() - 0.5) * 0.12, bev=0.008, tint=0.8 + 0.25 * vr.random())

prune(hold)
hold.build("ship_hold", ground=False, grime=0.0, tideline=True, ao=0.85)

# ---- the deck: bulwarks inside, planking, waterways and the broken hatch

deck = MB(14)
for side in (-1, 1):
    skin(deck, INT, rows_for, side, True, inside_paint(side), lambda x, j, y, side=side: y > DECK and x > CASTLE and not opening(side, x, j))


def plank_end(need, y=DECK):
    """How far forward a deck plank `need` off the centreline reaches before the bow closes in."""
    lo, hi = TAPER, STEM
    if inner_beam(hi, y) >= need:
        return station_x(hi, y)
    for _ in range(30):
        mid = (lo + hi) / 2
        if inner_beam(mid, y) >= need:
            lo = mid
        else:
            hi = mid
    return station_x(lo, y)


def planking(m, x0, rows_z, y, paint, butt=5.5, hatch=None, x_end=None, split=()):
    """Deck planks along x between z rows: each plank a run of quads, joints staggered."""
    for k in range(len(rows_z) - 1):
        z0, z1 = rows_z[k], rows_z[k + 1]
        need = max(abs(z0 - ZC), abs(z1 - ZC))
        x1 = x_end(need) if x_end else TAPER
        cuts = [x0]
        off = vr.random() * butt
        x = x0 + off
        while x < x1:
            cuts.append(x)
            x += butt
        cuts += [c for c in split if x0 < c < x1]
        holes = []
        if hatch and z0 < hatch[3] and z1 > hatch[2]:
            a, b = hatch[0] - vr.random() * 0.12, hatch[1] + vr.random() * 0.12
            cuts += [a, b]
            holes.append((a, b))
        cuts = sorted(set(cuts + [x1]))
        for xa, xb in zip(cuts, cuts[1:]):
            xm = (xa + xb) / 2
            if any(a <= xm <= b for a, b in holes) or xb - xa < 0.02:
                continue
            q = [m.bm.verts.new(B(px, y, pz)) for px, pz in ((xa, z0), (xa, z1), (xb, z1), (xb, z0))]
            f = m.bm.faces.new(q)
            pm, tint = paint(xm, k)
            m._paint([f], pm, 0.06, tint)


DECK_Z = [NORTH + WALL / 2 + k * 0.25 for k in range(11)] + [-15.3 + k * (9.1 / 45) for k in range(1, 46)]
planking(deck, STERN + WALL / 2, DECK_Z, DECK, lambda x, k: (DECKW, (0.8 if x < CASTLE else 1.0) * (1.0 if k % 2 else 0.93)),
         hatch=(-24.0, -16.0, NORTH, -15.3), x_end=plank_end, split=(CASTLE,))
# Waterways along the bulwarks hide the planks' ends where the bow closes in.
for side in (-1, 1):
    pts = []
    for s in [x for x in RUN_X if x >= CASTLE] + BOW_S[:-2]:
        if side > 0 and -9.9 < s < -7.7:
            run(deck, pts, 0.34, 0.07, TEAK, tint=0.85)
            pts = []
            continue
        x = station_x(s, DECK)
        pts.append((x, DECK + 0.03, ZC + side * (inner_beam(s, DECK) - 0.16)))
    run(deck, pts, 0.34, 0.07, TEAK, tint=0.85)
# Where the side is broken down, the deck's edge shows.
deck.box((2.5, 0.3, 0.42), at=(-21.75, DECK - 0.3, SOUTH + 0.01), mat=TEAK, tint=0.7)
deck.box((2.3, 0.26, 0.06), at=(-8.8, 5.74, SOUTH - WALL / 2), mat=TEAK, tint=0.7)
for x in [lerp(-23.0, -20.5, (k + 0.5) / 5) + (vr.random() - 0.5) * 0.2 for k in range(5)]:
    deck.box((0.2, DECK + 0.1 + vr.random() * 0.25 - 4.9, 0.32), at=(x, 4.9, SOUTH), mat=HOLDW, tint=0.75)
for x in (-9.75, -7.85):
    deck.box((0.2, 5.4 + vr.random() * 0.2 - 4.4, 0.32), at=(x, 4.4, SOUTH), mat=HOLDW, tint=0.75)
# Stanchions inside the bulwarks.
for side in (-1, 1):
    for s in frange(-23.9, 38.0, 1.6):
        x = station_x(s, 6.5)
        if side > 0 and (-23.2 < x < -20.3 or -10.1 < x < -7.5):
            continue
        b = inner_beam(s, 6.5)
        if b < 1.0:
            continue
        top = sheer(x)
        deck.box((0.14, top - DECK, 0.14), at=(x, DECK, ZC + side * (b - 0.06)), mat=BUFF, tint=0.85, bev=0.01)
# Splintered plank ends round the hatch.
for k in range(12):
    edge = vr.choice(("aft", "fore", "side"))
    if edge == "side":
        x, z, yaw = vr.uniform(-23.6, -16.4), -15.3, math.pi / 2
    else:
        x, z, yaw = (-24.0 if edge == "aft" else -16.0), vr.uniform(-17.6, -15.5), (0.0 if edge == "aft" else math.pi)
    L = 0.15 + vr.random() * 0.25
    deck.box((L, 0.04, 0.07 + vr.random() * 0.08), at=(x + math.cos(yaw) * L / 2, DECK - 0.04, z - math.sin(yaw) * L / 2), mat=DECKW, yaw=yaw, roll=-0.25 - vr.random() * 0.4, centered=True, bev=0.004, tint=0.8)

prune(deck)
deck.build("ship_deck", ground=False, grime=0.0, ao=0.8)

# ---- the stern castle: its front, the poop deck above, the chart room inside

castle = MB(15)
# The front wall, matching its collision, with a door, windows and trim.
for z0, z1, y0, y1 in ((NORTH + WALL / 2, -13.2, DECK, ROOF), (-10.8, SOUTH - WALL / 2, DECK, ROOF), (-13.2, -10.8, DECK + 2.4, ROOF)):
    castle.box((WALL, y1 - y0, z1 - z0), at=(CASTLE, y0, (z0 + z1) / 2), mat=CREAM, bev=0.02)
FRONT = CASTLE + WALL / 2
for z0, z1 in ((NORTH + WALL / 2, -13.2), (-10.8, SOUTH - WALL / 2)):
    castle.box((0.06, 0.22, z1 - z0), at=(FRONT + 0.02, DECK, (z0 + z1) / 2), mat=TEAK, bev=0.01)
    castle.box((0.05, 0.07, z1 - z0), at=(FRONT + 0.02, 7.0, (z0 + z1) / 2), mat=TEAK, bev=0.01)
for z in (-13.32, -10.68):
    castle.box((0.1, 2.5, 0.2), at=(FRONT + 0.04, DECK, z), mat=TEAK, bev=0.015)
for z0, z1 in ((NORTH + WALL / 2, -13.45), (-10.55, SOUTH - WALL / 2)):
    for z in (z0 + 0.06, (z0 + z1) / 2, z1 - 0.06):
        castle.box((0.05, ROOF - 0.25 - 7.07, 0.1), at=(FRONT + 0.02, 7.07, z), mat=CREAM, tint=0.9, bev=0.008)
        castle.box((0.05, 0.8, 0.1), at=(FRONT + 0.02, DECK + 0.22, z), mat=PANEL, tint=1.1, bev=0.008)
castle.box((0.16, 0.2, 2 * (HB - WALL)), at=(FRONT + 0.07, ROOF - 0.25, ZC), mat=TEAK, bev=0.02)
castle.box((0.06, 0.06, 2 * (HB - WALL)), at=(FRONT + 0.06, ROOF - 0.32, ZC), mat=GILT, bev=0.008)
castle.box((0.16, 0.22, 2.9), at=(FRONT + 0.06, DECK + 2.4, -12.0), mat=TEAK, bev=0.02)
castle.box((0.06, 0.1, 2.5), at=(FRONT + 0.06, DECK + 2.62, -12.0), mat=GILT, bev=0.01)
for z in (-15.7, -8.3):
    window(castle, (FRONT, 7.05, z), "x", 1, 0.9, 0.85, LIT)
# The doors: one leaf swung back against the wall, the other down on the deck.
castle.box((0.06, 2.3, 1.15), at=(FRONT + 0.05, DECK + 0.04, -14.0), mat=TEAK, bev=0.01)
for dv in (0.4, 1.4):
    castle.box((0.03, 0.75, 0.85), at=(FRONT + 0.09, DECK + 0.04 + dv, -14.0), mat=PANEL, bev=0.006)
castle.box((1.15, 0.06, 2.3), at=(-23.1, DECK, -11.2), mat=TEAK, yaw=0.35, bev=0.01)
castle.box((0.85, 0.03, 0.75), at=(-23.1, DECK + 0.06, -11.6), mat=PANEL, yaw=0.35, bev=0.006)

# The poop deck on the roof: planks, a rail all round, wheel, binnacle,
# skylight, and the ship's bell at the break.
castle.box((CASTLE - STERN + 0.45, 0.3, 2 * HB), at=((STERN + CASTLE) / 2 + 0.02, ROOF, ZC), mat=TEAK, tint=0.7, bev=0.02)
POOP_Z = [ZC - HB + 0.06 + k * (2 * HB - 0.12) / 46 for k in range(47)]
planking(castle, STERN - 0.2, POOP_Z, ROOF + 0.302, lambda x, k: (DECKW, 0.92 if k % 2 else 0.85), butt=4.0, x_end=lambda need: CASTLE + 0.22)
RAIL_Y = ROOF + 0.3
corners = [(STERN - 0.05, ZC - HB + 0.15), (CASTLE + 0.1, ZC - HB + 0.15), (CASTLE + 0.1, ZC + HB - 0.15), (STERN - 0.05, ZC + HB - 0.15)]
for (xa, za), (xb, zb) in zip(corners, corners[1:] + corners[:1]):
    L = math.hypot(xb - xa, zb - za)
    n = max(2, int(L / 0.9))
    for k in range(n):
        t = k / n
        castle.lathe([(0.06, 0.0), (0.06, 0.08), (0.035, 0.16), (0.05, 0.45), (0.035, 0.74), (0.05, 0.8), (0.05, 0.85)],
                     at=(lerp(xa, xb, t), RAIL_Y, lerp(za, zb, t)), mat=CREAM, segs=6)
    run(castle, [(xa, RAIL_Y + 0.89, za), (xb, RAIL_Y + 0.89, zb)], 0.14, 0.08, TEAK)
WHEEL = (STERN + 1.55, RAIL_Y + 1.05, ZC)
castle.box((0.5, 0.75, 0.36), at=(WHEEL[0] - 0.05, RAIL_Y, ZC), mat=TEAK, bev=0.03)
castle.cyl(0.07, 0.07, 0.5, at=(WHEEL[0] + 0.1, WHEEL[1], ZC), mat=BRASS, roll=math.pi / 2, centered=True, segs=8)
castle.ring(0.66, 0.045, at=(WHEEL[0] + 0.3, WHEEL[1], ZC), mat=TEAK, roll=math.pi / 2, segs=24, tube_segs=5)
castle.ring(0.3, 0.03, at=(WHEEL[0] + 0.3, WHEEL[1], ZC), mat=BRASS, roll=math.pi / 2, segs=16, tube_segs=4)
for k in range(8):
    a = k / 8 * math.tau
    ca, sa = math.cos(a), math.sin(a)
    castle.tube([(WHEEL[0] + 0.3, WHEEL[1] + ca * 0.1, ZC + sa * 0.1), (WHEEL[0] + 0.3, WHEEL[1] + ca * 0.92, ZC + sa * 0.92)], [0.03, 0.022], mat=TEAK, segs=5)
castle.lathe([(0.2, 0.0), (0.16, 0.1), (0.12, 0.8), (0.24, 0.9), (0.24, 1.05), (0.2, 1.2), (0.0, 1.3)], at=(STERN + 2.75, RAIL_Y, ZC), mat=TEAK, segs=10)
castle.lathe([(0.22, 1.04), (0.2, 1.22), (0.12, 1.34), (0.0, 1.38)], at=(STERN + 2.75, RAIL_Y, ZC), mat=BRASS, segs=12)
castle.box((1.5, 0.45, 1.1), at=(-28.4, RAIL_Y, ZC), mat=TEAK, bev=0.03)
for side in (-1, 1):
    castle.box((1.4, 0.04, 0.6), at=(-28.4, RAIL_Y + 0.55, ZC + side * 0.28), mat=LIT, roll=0.0, pitch=side * 0.32, centered=True, bev=0)
    for dx in (-0.35, 0.0, 0.35):
        castle.box((0.04, 0.05, 0.62), at=(-28.4 + dx, RAIL_Y + 0.57, ZC + side * 0.28), mat=BRASS, pitch=side * 0.32, centered=True, bev=0)
BELL_X = CASTLE + 0.1
for dz in (-0.45, 0.45):
    castle.box((0.1, 0.8, 0.1), at=(BELL_X, RAIL_Y + 0.89, ZC + dz), mat=TEAK, bev=0.01)
castle.box((0.14, 0.12, 1.1), at=(BELL_X, RAIL_Y + 1.69, ZC), mat=TEAK, bev=0.015)
castle.lathe([(0.0, -0.36), (0.21, -0.36), (0.19, -0.3), (0.15, -0.12), (0.12, 0.0), (0.0, 0.03)], at=(BELL_X, RAIL_Y + 1.62, ZC), mat=BRASS, segs=14)

# Inside: panelled walls, the stern windows from within, ceiling beams.
CI_ROWS = [DECK, 6.3, 6.65, 7.0, 7.35, 7.7, 8.05, 8.4, 8.75, ROOF]
CIX = [s for s in INT if s <= CASTLE - 0.2 + 1e-6]
for side in (-1, 1):
    skin(castle, CIX, lambda s: CI_ROWS, side, True,
         lambda x, j, y, i, side=side: (PANEL, ("ci", side, j, plank_no(("ci", side), j, x, 3.0)), 1.0 if j % 2 else 0.88) if y < 7.0 else (CREAM_IN, ("ci", side, j), 1.0),
         lambda x, j, y: True)
flat_face(castle, STERN + WALL / 2, CI_ROWS, 1, lambda k, r, y: (PANEL, ("ca", r, k // 4), 1.0 if r % 2 else 0.88) if y < 7.0 else (CREAM_IN, ("ca", r), 1.0), inner=True)
for z in (ZC - 4.2, ZC - 2.1, ZC, ZC + 2.1, ZC + 4.2):
    castle.box((0.03, 0.95, 1.05), at=(STERN + WALL / 2 + 0.02, 7.35, z), mat=NIGHT, bev=0)
    castle.box((0.08, 0.06, 1.3), at=(STERN + WALL / 2 + 0.05, 7.26, z), mat=TEAK, bev=0.01)
for side in (-1, 1):
    for x in (-29.5, -26.6):
        castle.box((0.9, 0.8, 0.03), at=(x, 7.1, ZC + side * (HB - WALL - 0.02)), mat=NIGHT, bev=0)
    for x in (-32.98 - 0.62, -32.98 + 0.62):
        castle.box((0.85, 1.1, 0.03), at=(x, 7.25, ZC + side * (HB - WALL - 0.02)), mat=NIGHT, bev=0)
for z in (-15.7, -8.3):
    castle.box((0.03, 0.85, 0.9), at=(CASTLE - WALL / 2 - 0.02, 7.05, z), mat=NIGHT, bev=0)
for x in frange(STERN + 1.1, CASTLE - 0.6, 1.2):
    castle.box((0.2, 0.24, 2 * (HB - WALL)), at=(x, ROOF - 0.24, ZC), mat=PANEL, tint=0.8, bev=0.015)

prune(castle)
castle.build("ship_castle", ground=False, grime=0.0, ao=0.8)

# The chart room's furniture (collision is COL_chart_room_furniture).
chart = MB(16)
TX, TZ = -27.6, -15.6
chart.box((2.5, 0.07, 1.5), at=(TX, DECK + 0.85, TZ), mat=TEAK, bev=0.015)
chart.box((2.3, 0.16, 1.3), at=(TX, DECK + 0.7, TZ), mat=PANEL, bev=0.01)
for dx in (-1.08, 1.08):
    for dz in (-0.58, 0.58):
        chart.lathe([(0.06, 0.0), (0.045, 0.1), (0.055, 0.35), (0.04, 0.6), (0.055, 0.7), (0.055, 0.85)], at=(TX + dx, DECK, TZ + dz), mat=TEAK, segs=8)
for k in range(5):
    a = (vr.random() - 0.5) * 0.4
    chart.box((0.9 + vr.random() * 0.3, 0.006, 0.65 + vr.random() * 0.2), at=(TX - 0.6 + k * 0.32, DECK + 0.922 + k * 0.004, TZ + (vr.random() - 0.5) * 0.3), mat=PAPER, yaw=a, bev=0, tint=0.85 + 0.15 * vr.random())
chart.tube([(TX + 0.9, DECK + 0.96, TZ - 0.5), (TX + 0.95, DECK + 0.96, TZ + 0.45)], 0.04, mat=PAPER, segs=8)
for a in (0.3, 0.55):
    chart.tube([(TX - 0.2, DECK + 0.935, TZ + 0.1), (TX - 0.2 + math.cos(a) * 0.32, DECK + 0.935, TZ + 0.1 + math.sin(a) * 0.32)], 0.006, mat=BRASS, segs=4)
chart.cyl(0.05, 0.05, 0.07, at=(TX + 0.5, DECK + 0.92, TZ + 0.45), mat=P["glass_blue"], segs=8)
# The chart case against the transom: shelves of books and rolled charts.
CASE_X, CASE_Z = -33.4, -9.0
chart.box((0.06, 2.2, 3.0), at=(CASE_X - 0.22, DECK, CASE_Z), mat=PANEL, tint=0.7, bev=0.01)
for dz in (-1.47, 1.47):
    chart.box((0.5, 2.2, 0.06), at=(CASE_X, DECK, CASE_Z + dz), mat=PANEL, bev=0.01)
chart.box((0.52, 0.08, 3.04), at=(CASE_X, DECK + 2.14, CASE_Z), mat=PANEL, bev=0.015)
for k, y in enumerate((0.25, 0.85, 1.45)):
    chart.box((0.48, 0.04, 2.9), at=(CASE_X, DECK + y - 0.04, CASE_Z), mat=PANEL, bev=0.005)
    z = CASE_Z - 1.35
    while z < CASE_Z + 1.3:
        w = 0.05 + vr.random() * 0.06
        h = 0.32 + vr.random() * 0.14
        if k == 2:
            chart.cyl(0.05, 0.05, 0.45, at=(CASE_X + 0.02, DECK + y + 0.05 + (vr.random() * 0.15), z), mat=PAPER, roll=math.pi / 2, centered=True, segs=7, tint=0.8 + 0.2 * vr.random())
            z += 0.11
            continue
        book = vr.choice((P["leather"], P["paint_red"], P["paint_blue"], TEAK, P["moss"]))
        chart.box((0.3, h, w), at=(CASE_X + 0.02, DECK + y, z + w / 2), mat=book, tint=0.6 + 0.3 * vr.random(), yaw=(vr.random() - 0.5) * 0.06, bev=0.005)
        z += w + 0.008
# The captain's bunk and sea chest.
chart.box((2.2, 0.5, 1.0), at=(-32.6, DECK, -17.3), mat=PANEL, bev=0.02)
chart.box((2.1, 0.16, 0.9), at=(-32.6, DECK + 0.5, -17.3), mat=CANVAS, tint=0.75, bev=0.05)
chart.box((2.2, 0.45, 0.06), at=(-32.6, DECK + 0.5, -16.83), mat=PANEL, bev=0.01)
chart.box((0.5, 0.14, 0.7), at=(-33.3, DECK + 0.66, -17.35), mat=PAPER, tint=0.8, bev=0.05)
chart.box((1.0, 0.5, 0.6), at=(-30.8, DECK, -17.45), mat=TEAK, bev=0.02)
chart.cyl(0.3, 0.3, 1.0, at=(-30.8, DECK + 0.5, -17.45), mat=TEAK, roll=math.pi / 2, centered=True, segs=12)
for dx in (-0.4, 0.4):
    chart.box((0.05, 0.62, 0.62), at=(-30.8 + dx, DECK, -17.45), mat=IRON, bev=0.005)
# A chair knocked over, a rug, the barometer.
chart.box((0.45, 0.05, 0.45), at=(-26.4, DECK + 0.23, -13.9), mat=TEAK, roll=1.45, yaw=0.4, centered=True, bev=0.01)
chart.box((0.45, 0.5, 0.05), at=(-26.62, DECK + 0.45, -14.0), mat=TEAK, roll=1.45, yaw=0.4, centered=True, bev=0.01)
chart.box((3.0, 0.012, 2.0), at=(-30.4, DECK, -12.0), mat=Paint(P["cloth"].mat, 0x6B2F27), bev=0)
chart.box((2.6, 0.014, 1.6), at=(-30.4, DECK, -12.0), mat=Paint(P["cloth"].mat, 0x8A6A3A), bev=0)
chart.cyl(0.17, 0.17, 0.06, at=(-29.0, 7.6, NORTH + WALL / 2 + 0.03), mat=BRASS, pitch=math.pi / 2, centered=True, segs=14)
chart.cyl(0.14, 0.14, 0.02, at=(-29.0, 7.6, NORTH + WALL / 2 + 0.065), mat=PAPER, pitch=math.pi / 2, centered=True, segs=14)
chart.build("chart_room_furniture", ground=False, grime=0.1, ao=0.8)
dress("lantern_hanging", "lantern_chart_room", -28.1, -14.9, y=ROOF - 0.24, yaw=0.0)
prop("lens_pedestal", "NODE_lens_pedestal_00", -30.5, -12.0, y=DECK, yaw=math.pi / 2, props={"node": "lens_pedestal"})

# Rope ladder from the chart room's south window to the shelf; the game shows
# it once you hold the lens. Using it from the deck drops you at SPAWN_ladder.
prop("rope_ladder", "INT_rope_ladder", -29.5, -5.75, y=1.0, yaw=0.0, props={"interact": "rope_ladder", "range": 3.5})
kit.empty("SPAWN_ladder", (-29.5, 2.9, -4.4), yaw=math.pi)

# ---- masts, yards, sails and rigging

rig = MB(17)
TARRED_ROPE = TARRED
# Main mast: lower mast with iron hoops, the top, topmast, yard, sails.
rig.cyl(0.47, 0.39, 12.0, at=(MAIN_X, DECK, ZC), mat=SPAR, segs=12)
for y in frange(7.0, 17.0, 1.6):
    r = 0.47 - (y - DECK) / 12.0 * 0.08
    rig.ring(r + 0.01, 0.022, at=(MAIN_X, y, ZC), mat=IRON, segs=14, tube_segs=4)
TOP_Y = DECK + 12.0
for yaw in (0.0, math.pi / 2):
    rig.box((2.1, 0.22, 0.24), at=(MAIN_X, TOP_Y - 0.22, ZC), mat=TEAK, yaw=yaw, bev=0.02)
rig.cyl(0.92, 0.92, 0.08, at=(MAIN_X, TOP_Y - 0.02, ZC), mat=TEAK, segs=16)
rig.lathe([(0.9, 0.0), (0.97, 0.76), (1.0, 0.8), (0.95, 0.82), (0.88, 0.04)], at=(MAIN_X, TOP_Y, ZC), mat=TEAK, segs=16, cap=False, staves=0.08)
for y in (0.15, 0.62):
    rig.ring(0.95 + y * 0.05, 0.02, at=(MAIN_X, TOP_Y + y, ZC), mat=IRON, segs=18, tube_segs=4)
rig.cyl(0.25, 0.16, 7.4, at=(MAIN_X, TOP_Y - 0.4, ZC), mat=SPAR, segs=10)
rig.cyl(0.2, 0.2, 0.14, at=(MAIN_X, TOP_Y + 7.0, ZC), mat=TEAK, segs=10)
YARD = (MAIN_X + 0.55, DECK + 10.5, ZC)
for d in (1, -1):
    rig.cyl(0.18, 0.08, 4.7, at=YARD, mat=SPAR, pitch=d * math.pi / 2, segs=10)
rig.box((0.35, 0.5, 0.35), at=(MAIN_X + 0.35, YARD[1] - 0.25, ZC), mat=TEAK, bev=0.03)
# Furled sail on the north arm, gasket-tied; the south arm's sail hangs in tatters.
pts = [(YARD[0], YARD[1] + 0.2, z) for z in frange(ZC - 4.2, ZC - 0.5, 0.41)]
rig.tube(pts, [0.1 + 0.16 * math.sin(math.pi * k / (len(pts) - 1)) + 0.03 * vr.random() for k in range(len(pts))], mat=CANVAS, segs=8, tint=0.82)
for k in range(1, len(pts) - 1, 2):
    rig.ring(0.24, 0.018, at=pts[k], mat=ROPE, pitch=math.pi / 2, segs=10, tube_segs=4)
sections = []
ragged = [3.6 * (0.45 + 0.55 * vr.random()) for _ in range(11)]
for r in range(8):
    v = r / 7
    sec = []
    for c in range(11):
        u = c / 10
        d = ragged[c] * v
        sec.append((YARD[0] + 0.12 + 0.55 * math.sin(math.pi * u) * math.sin(math.pi * min(1.0, v * 1.15)), YARD[1] - 0.1 - d, ZC + 0.4 + 3.9 * u))
    sections.append(sec)
rig.loft(sections, mat=CANVAS, tint=0.78, jit=0.08)
for d in (1, -1):
    rig.tube(sag((YARD[0] + 0.1, YARD[1] - 0.25, ZC + d * 0.4), (YARD[0] + 0.1, YARD[1] - 0.2, ZC + d * 4.4), 0.55), 0.018, mat=TARRED_ROPE, segs=4)


def shrouds(mx, top_y, head_r, feet_side, rat_to, loose=None):
    """Shrouds from the channel's deadeyes up to the masthead, with ratlines."""
    lines = []
    for side in (-1, 1):
        feet = SHROUD_FEET[(mx, side)]
        tops = [(mx + (fx - mx) * 0.12, top_y, ZC + side * head_r) for fx, _, _ in feet]
        for k, (f, t) in enumerate(zip(feet, tops)):
            if loose is not None and k == loose and side > 0:
                # Parted: hangs from the top in a long curve to the deck.
                rig.tube(sag(t, (f[0] + 0.8, DECK + 0.1, ZC + side * 4.2), 0.8, 10), 0.028, mat=TARRED_ROPE, segs=5)
                continue
            rig.tube([f, t], 0.028, mat=TARRED_ROPE, segs=5)
        lines.append((feet, tops, side))
    for feet, tops, side in lines:
        y = feet[0][1] + 0.5
        while y < rat_to:
            pts = []
            for k, (f, t) in enumerate(zip(feet, tops)):
                if loose is not None and k == loose and side > 0:
                    continue
                u = (y - f[1]) / (t[1] - f[1])
                pts.append((lerp(f[0], t[0], u), y, lerp(f[2], t[2], u)))
            if len(pts) > 1:
                rig.tube(pts, 0.011, mat=ROPE, segs=3, tint=0.8)
            y += 0.42


shrouds(MAIN_X, TOP_Y - 0.15, 0.5, SHROUD_FEET, TOP_Y - 0.9)
# Foremast: snapped off at 7.5 m, splinters at the break, one shroud parted.
FORE_TOP = DECK + 7.1
rig.cyl(0.43, 0.4, FORE_TOP - DECK, at=(FORE_X, DECK, ZC), mat=SPAR, segs=12)
for y in frange(7.0, FORE_TOP - 0.5, 1.6):
    rig.ring(0.43 - (y - DECK) * 0.004 + 0.01, 0.022, at=(FORE_X, y, ZC), mat=IRON, segs=14, tube_segs=4)
for k in range(9):
    a = k / 9 * math.tau + vr.random() * 0.3
    h = 0.25 + vr.random() * 0.75
    rig.box((0.1, h, 0.16), at=(FORE_X + math.cos(a) * 0.27, FORE_TOP - 0.05, ZC - math.sin(a) * 0.27), mat=SPAR, yaw=a, roll=(vr.random() - 0.5) * 0.3, tint=1.1, bev=0.01)
shrouds(FORE_X, FORE_TOP - 0.4, 0.42, SHROUD_FEET, FORE_TOP - 1.2, loose=2)
# Gulls: on the snapped foremast, the main top and the capstan; the flock wheels over the main mast.
kit.empty("FX_perch_foremast", (FORE_X, FORE_TOP + 0.4, ZC))
kit.empty("FX_perch_maintop", (MAIN_X + 0.55, DECK + 13.2, ZC))
kit.empty("FX_perch_capstan", (11.0, DECK + 1.5, ZC + 0.25))
kit.empty("FX_gulls", (MAIN_X, 0.0, ZC))
# Mizzen: a stump where it broke, before it fell over the side.
MIZ_TOP = DECK + 1.75
rig.cyl(0.44, 0.42, MIZ_TOP - DECK, at=(MIZZEN_X, DECK, ZC), mat=SPAR, segs=12)
for k in range(8):
    a = k / 8 * math.tau + vr.random() * 0.4
    h = 0.2 + vr.random() * 0.55
    rig.box((0.1, h, 0.16), at=(MIZZEN_X + math.cos(a) * 0.28, MIZ_TOP - 0.05, ZC - math.sin(a) * 0.28), mat=SPAR, yaw=a, roll=(vr.random() - 0.5) * 0.4, tint=1.1, bev=0.01)
# Bowsprit and a broken jib boom; the bobstay chain down to the stem.
(bx0, by0, _), (bx1, by1, _) = BOWSPRIT
rig.tube([(bx0, by0, ZC), (lerp(bx0, bx1, 0.5), lerp(by0, by1, 0.5), ZC), (bx1, by1, ZC)], [0.36, 0.3, 0.2], mat=SPAR, segs=10)
for t in (0.35, 0.62, 0.9):
    rig.ring(0.36 - t * 0.17, 0.022, at=(lerp(bx0, bx1, t), lerp(by0, by1, t), ZC), mat=IRON, roll=-(math.pi / 2 - math.atan2(by1 - by0, bx1 - bx0)), segs=12, tube_segs=4)
jb = (lerp(bx0, bx1, 0.82), lerp(by0, by1, 0.82) + 0.25, ZC)
jb_end = (jb[0] + 3.2, jb[1] + 1.15, ZC)
rig.tube([jb, jb_end], [0.13, 0.1], mat=SPAR, segs=8)
for k in range(5):
    a = k / 5 * math.tau
    rig.box((0.22 + vr.random() * 0.3, 0.05, 0.06), at=(jb_end[0] + 0.1, jb_end[1] + math.cos(a) * 0.05, ZC + math.sin(a) * 0.05), mat=SPAR, roll=0.34 + (vr.random() - 0.5) * 0.4, yaw=(vr.random() - 0.5) * 0.4, centered=True, bev=0)
rig.tube(sag((bx1 - 0.2, by1 - 0.25, ZC), (stem_x(1.6) + 0.25, 1.6, ZC), 0.3), 0.05, mat=IRON, segs=5)
# Stays: the forestay to the bowsprit, the mainstay down to the foremast's
# stump, backstays to the rails, and a jib stay trailing in the sea.
rig.tube(sag((MAIN_X + 0.15, TOP_Y + 6.2, ZC), (bx1 - 0.3, by1 + 0.1, ZC), 0.5, 12), 0.035, mat=TARRED_ROPE, segs=5)
rig.tube(sag((MAIN_X + 0.4, TOP_Y - 0.3, ZC), (FORE_X - 0.35, FORE_TOP - 0.6, ZC), 0.35), 0.04, mat=TARRED_ROPE, segs=5)
for side in (-1, 1):
    rig.tube(sag((MAIN_X - 0.2, TOP_Y + 5.4, ZC + side * 0.2), (-2.6, BULWARK + 0.1, ZC + side * (HB - 0.15)), 0.3), 0.03, mat=TARRED_ROPE, segs=5)
rig.tube([(bx1 - 0.6, by1 - 0.15, ZC + 0.1), (bx1 - 0.1, by1 - 2.6, ZC + 0.3), (bx1 + 0.3, 5.5, ZC + 0.6), (bx1 + 0.6, 2.5, ZC + 0.9), (bx1 + 0.9, -0.4, ZC + 1.2)], 0.025, mat=TARRED_ROPE, segs=4)

prune(rig)
rig.build("ship_rig", ground=False, grime=0.0, ao=0.35, smooth=50)

# ---- deck fittings: funnel and vents, skylight, capstan, hatch, bitts,
# windlass, anchors and the figurehead

fit = MB(18)
FUNNEL_TOP = DECK + 5.5
fit.cyl(1.26, 1.2, 0.16, at=(FUNNEL_X, DECK, ZC), mat=IRON, segs=24)
fit.cyl(1.12, 1.04, 4.6, at=(FUNNEL_X, DECK + 0.1, ZC), mat=FUNNEL, segs=24)
fit.cyl(1.04, 1.01, FUNNEL_TOP - DECK - 4.7, at=(FUNNEL_X, DECK + 4.7, ZC), mat=SOOT, segs=24)
fit.lathe([(1.0, 0.0), (1.16, 0.06), (1.16, 0.28), (1.05, 0.34), (0.96, 0.3), (0.96, 0.0)], at=(FUNNEL_X, FUNNEL_TOP, ZC), mat=SOOT, segs=24, cap=False)
fit.cyl(0.96, 0.96, 0.02, at=(FUNNEL_X, FUNNEL_TOP - 0.6, ZC), mat=Paint(P["iron"].mat, 0x0E0E0E), segs=20)
for y in (7.25, 8.45, 9.65):
    r = 1.12 - (y - DECK - 0.1) / 4.6 * 0.08
    fit.ring(r + 0.008, 0.022, at=(FUNNEL_X, y, ZC), mat=RUST, segs=28, tube_segs=4)
for k in range(14):
    a = vr.random() * math.tau
    y1 = vr.choice((7.2, 8.4, 9.6, 10.7)) - 0.02
    h = 0.5 + vr.random() * 1.3
    r = 1.12 - (y1 - h / 2 - DECK) / 4.6 * 0.08 + 0.012
    fit.box((0.07 + vr.random() * 0.08, h, 0.012), at=(FUNNEL_X + math.cos(a) * r, y1 - h, ZC - math.sin(a) * r), mat=RUST, yaw=math.pi / 2 + a, jit=0.15, bev=0, tint=0.7 + 0.4 * vr.random())
fit.tube([(FUNNEL_X + 1.24, DECK, ZC + 0.32), (FUNNEL_X + 1.24, 10.9, ZC + 0.32)], 0.08, mat=IRON, segs=8)
fit.cyl(0.08, 0.1, 0.32, at=(FUNNEL_X + 1.24, 10.9, ZC + 0.32), mat=BRASS, segs=10)
fit.lathe([(0.1, 0.0), (0.14, 0.08), (0.0, 0.1)], at=(FUNNEL_X + 1.24, 11.22, ZC + 0.32), mat=BRASS, segs=10)
for y in (7.0, 8.8, 10.4):
    fit.box((0.26, 0.06, 0.06), at=(FUNNEL_X + 1.12, y, ZC + 0.32), mat=IRON, bev=0)
for a in (math.pi / 4, 3 * math.pi / 4, 5 * math.pi / 4, 7 * math.pi / 4):
    ca, sa = math.cos(a), math.sin(a)
    top = (FUNNEL_X + ca * 1.05, 10.1, ZC - sa * 1.05)
    foot = (FUNNEL_X + ca * 4.0, DECK + 0.05, ZC - sa * 4.0)
    fit.tube([top, foot], 0.016, mat=IRON, segs=4)
    fit.ring(0.06, 0.015, at=foot, mat=IRON, pitch=math.pi / 2, yaw=a, segs=8, tube_segs=3)
# Cowl vents: cream outside, red in the throat, turned to the bow.
for z in (ZC - 2.4, ZC + 2.4):
    fit.cyl(0.24, 0.24, 1.75, at=(-1.5, DECK, z), mat=CREAM, segs=12)
    fit.cyl(0.3, 0.3, 0.12, at=(-1.5, DECK, z), mat=IRON, segs=12)
    fit.uvsphere(0.27, at=(-1.5, DECK + 1.78, z), mat=CREAM, segs=12, rings=8)
    prof = [(0.24, 0.0), (0.27, 0.12), (0.34, 0.28), (0.45, 0.44), (0.54, 0.58), (0.56, 0.64)]
    fit.lathe(prof, at=(-1.5, DECK + 1.72, z), mat=CREAM, segs=14, roll=-1.2, cap=False)
    fit.lathe([(r - 0.025, y + 0.01) for r, y in prof], at=(-1.5, DECK + 1.72, z), mat=VENT_RED, segs=14, roll=-1.2, cap=False)
# The engine-room skylight: one lid's glass gone.
fit.box((2.6, 0.55, 1.8), at=(1.6, DECK, ZC), mat=CREAM, bev=0.03)
fit.box((2.7, 0.08, 0.14), at=(1.6, DECK + 0.83, ZC), mat=TEAK, bev=0.01)
for side, glass in ((-1, NIGHT), (1, None)):
    if glass:
        fit.box((2.5, 0.03, 0.88), at=(1.6, DECK + 0.7, ZC + side * 0.42), mat=glass, pitch=side * 0.33, centered=True, bev=0)
    for dx in (-1.2, -0.6, 0.0, 0.6, 1.2):
        fit.box((0.05, 0.05, 0.92), at=(1.6 + dx, DECK + 0.72, ZC + side * 0.42), mat=BRASS, pitch=side * 0.33, centered=True, bev=0)
# Capstan.
fit.lathe([(0.52, 0.0), (0.52, 0.08), (0.36, 0.14), (0.31, 0.55), (0.36, 0.86), (0.56, 0.92), (0.56, 1.05), (0.42, 1.12), (0.0, 1.13)], at=(11.0, DECK, ZC), mat=TEAK, segs=16)
for k in range(8):
    a = k / 8 * math.tau
    fit.box((0.08, 0.66, 0.12), at=(11.0 + math.cos(a) * 0.36, DECK + 0.16, ZC - math.sin(a) * 0.36), mat=TEAK, yaw=a, tint=0.85, bev=0.01)
    fit.box((0.06, 0.08, 0.1), at=(11.0 + math.cos(a + 0.4) * 0.5, DECK + 0.95, ZC - math.sin(a + 0.4) * 0.5), mat=SOOT, yaw=a + 0.4, bev=0)
fit.ring(0.53, 0.025, at=(11.0, DECK + 0.98, ZC), mat=IRON, segs=18, tube_segs=4)
# The fore hatch, battened down under a tarpaulin.
fit.box((3.0, 0.45, 2.6), at=(19.5, DECK, ZC), mat=TEAK, bev=0.03)
fit.box((2.92, 0.1, 2.52), at=(19.5, DECK + 0.43, ZC), mat=CANVAS, tint=0.62, bev=0.05)
for dz in (-1.27, 1.27):
    fit.box((2.9, 0.06, 0.06), at=(19.5, DECK + 0.36, ZC + dz), mat=IRON, bev=0)
for dx in (-1.47, 1.47):
    fit.box((0.06, 0.06, 2.5), at=(19.5 + dx, DECK + 0.36, ZC), mat=IRON, bev=0)
# Towing bitts.
for z in (ZC - 1.4, ZC + 1.4):
    fit.box((0.34, 0.9, 0.34), at=(24.2, DECK, z), mat=TEAK, bev=0.03)
    fit.box((0.12, 0.12, 0.6), at=(24.2, DECK + 0.62, z), mat=IRON, bev=0.01)
# The windlass on the foredeck, cable running out to the hawse pipes.
WX = 36.4
for z in (ZC - 1.45, ZC + 1.45):
    fit.box((0.42, 1.2, 0.4), at=(WX, DECK, z), mat=TEAK, bev=0.03)
fit.cyl(0.34, 0.34, 2.5, at=(WX, DECK + 0.72, ZC), mat=TEAK, pitch=math.pi / 2, centered=True, segs=12)
for dz in (-1.05, -0.4, 0.4, 1.05):
    fit.cyl(0.36, 0.36, 0.06, at=(WX, DECK + 0.72, ZC + dz), mat=IRON, pitch=math.pi / 2, centered=True, segs=12)
for dz in (-0.85, 0.85):
    fit.cyl(0.44, 0.44, 0.16, at=(WX, DECK + 0.72, ZC + dz), mat=IRON, pitch=math.pi / 2, centered=True, segs=10)
fit.box((0.14, 0.5, 0.2), at=(WX + 0.3, DECK + 0.9, ZC), mat=IRON, roll=0.5, bev=0.01)
for side in (-1, 1):
    hx, hy, hz = hull_pt(HAWSE_S, 5.55, side, inner=True)
    fit.tube(sag((WX + 0.3, DECK + 0.72, ZC + side * 0.85), (hx - 0.2, DECK + 0.05, hz - side * 0.2), 0.08, 5), 0.055, mat=RUST, segs=5)
# North anchor catted; the south one let go, its cable running out to the reef.
nx, ny, nz = CATHEADS[-1]
anchor = kit.place(TEMPLATES, "anchor", "ship_anchor", (nx + 0.05, ny - 1.95, nz - 0.2), scale=1.3)
anchor.rotation_euler = (-math.pi / 2, 0.0, 0.0)
fit.tube([(nx + 0.05, ny - 0.15, nz), (nx + 0.05, ny - 0.62, nz - 0.18)], 0.04, mat=RUST, segs=5)
hx, hy, hz = hull_pt(HAWSE_S, 5.55, 1, out=0.12)
fit.tube(sag((hx, hy - 0.1, hz), (hx + 3.5, -0.6, hz + 3.8), 0.9, 10), 0.06, mat=RUST, segs=5)
# The figurehead: a woman leaning out over the sea, a lantern held up ahead.
sx, sy = stem_x(7.0) + 0.75, 7.0
body = [(sx - 0.3, sy - 1.1, ZC), (sx - 0.05, sy - 0.55, ZC), (sx + 0.25, sy - 0.05, ZC), (sx + 0.55, sy + 0.4, ZC), (sx + 0.8, sy + 0.72, ZC)]
fit.tube(body, [0.12, 0.24, 0.27, 0.23, 0.15], mat=FIGURE, segs=10)
fit.uvsphere(0.17, at=(sx + 0.98, sy + 0.92, ZC), mat=FIGURE, segs=12, rings=8)
fit.uvsphere(0.18, at=(sx + 0.92, sy + 0.97, ZC), mat=GILT, scale=(1.0, 0.75, 1.05), segs=12, rings=8)
for side in (-1, 1):
    fit.tube([(sx + 0.62, sy + 0.55, ZC + side * 0.18), (sx + 0.95, sy + 0.62, ZC + side * 0.25), (sx + 1.3, sy + 0.82, ZC + side * 0.12)], [0.075, 0.065, 0.05], mat=FIGURE, segs=7)
fit.tube([(sx + 1.33, sy + 0.84, ZC), (sx + 1.36, sy + 0.62, ZC)], 0.012, mat=GILT, segs=4)
fit.lathe([(0.0, -0.2), (0.1, -0.18), (0.11, -0.04), (0.06, 0.02), (0.0, 0.06)], at=(sx + 1.36, sy + 0.56, ZC), mat=GILT, segs=8)
fit.tube([(sx - 0.25, sy - 1.0, ZC), (sx - 0.55, sy - 1.35, ZC), (sx - 0.7, sy - 1.05, ZC), (sx - 0.5, sy - 0.85, ZC)], [0.1, 0.08, 0.06, 0.04], mat=GILT, segs=6)

prune(fit)
fit.build("ship_fittings", ground=False, grime=0.0, ao=0.7, smooth=45)

# ---- the fallen mizzen: over the south rail into the lagoon, planked over
# so it can be walked; its foot hangs out of reach until the tide floats the
# crates up to it.

fm = MB(19)
ax, ay, az = MAST_FOOT
ux, uy, uz = 0.0, MAST_TOP[1] - ay, MAST_TOP[2] - az
mlen = math.sqrt(uy * uy + uz * uz)
uy, uz = uy / mlen, uz / mlen
ny_, nz_ = -uz, uy  # surface normal (up, toward the lagoon)
if ny_ < 0:
    ny_, nz_ = -ny_, -nz_
slope = math.atan2(nz_, ny_)


def on_mast(t, below):
    return (ax, ay + uy * mlen * t - ny_ * below, az + uz * mlen * t - nz_ * below)


spar_t = [-0.12, 0.1, 0.35, 0.6, 0.85, 1.06]
spar_r = [lerp(0.33, 0.46, max(0.0, t)) for t in spar_t]
fm.tube([on_mast(t, 0.06 + r) for t, r in zip(spar_t, spar_r)], spar_r, mat=SPAR, segs=12)
for t in (0.05, 0.3, 0.55, 0.8):
    r = lerp(0.33, 0.46, t)
    fm.ring(r + 0.01, 0.022, at=on_mast(t, 0.06 + r), mat=IRON, pitch=-slope + math.pi / 2, segs=14, tube_segs=4)
# The masthead (cap and trestle-trees) over the lagoon.
hx_, hy_, hz_ = on_mast(-0.12, 0.39)
fm.box((0.7, 0.3, 0.5), at=(hx_, hy_, hz_ + 0.15), mat=TEAK, pitch=slope, centered=True, bev=0.03)
fm.box((1.6, 0.16, 0.22), at=(hx_, hy_ - 0.1, hz_ - 0.3), mat=TEAK, pitch=slope, centered=True, bev=0.02)
# The broken butt on deck.
bx_, by_, bz_ = on_mast(1.06, 0.52)
for k in range(7):
    a = k / 7 * math.tau
    fm.box((0.08, 0.12, 0.3 + vr.random() * 0.4), at=(bx_ + math.cos(a) * 0.3, by_ + math.sin(a) * 0.3, bz_ - 0.1), mat=SPAR, pitch=slope + (vr.random() - 0.5) * 0.3, centered=True, tint=1.1, bev=0.006)
# Boards nailed across it: what you actually walk on.
n_boards = int(mlen / 0.55)
for i in range(n_boards):
    t = (i + 0.5) / n_boards
    x, y, z = on_mast(t, 0.03)
    fm.box((1.6 + (vr.random() - 0.5) * 0.12, 0.06, 0.27), at=(x + (vr.random() - 0.5) * 0.06, y, z), mat=DECKW if i % 4 else TEAK, pitch=slope, yaw=(vr.random() - 0.5) * 0.06, centered=True, bev=0.008, tint=0.75 + 0.2 * vr.random())
    if i % 5 == 2:
        r = lerp(0.33, 0.46, t)
        cx_, cy_, cz_ = on_mast(t, 0.06 + r)
        fm.ring(r + 0.04, 0.025, at=(cx_, cy_, cz_), mat=ROPE, pitch=-slope + math.pi / 2, segs=12, tube_segs=4)
# Its rigging still hangs from the rail.
for k in range(3):
    t = 0.3 + k * 0.17
    a = (-9.9 + k * 1.1, BULWARK - 0.4, SOUTH + 0.2)
    b = on_mast(t, 0.4)
    fm.tube(sag(a, (b[0] + 0.5 - k * 0.5, b[1], b[2]), 0.6, 8), 0.03, mat=TARRED, segs=4)
fm.build("mast_fallen", ground=False, grime=0.0, ao=0.6, tideline=True)

# Support posts down the middle of the hold (solid): square timbers under the beams.
posts = MB(20)
for x in (-20.0, -8.0, 4.0, 16.0, 28.0):
    posts.box((0.46, 5.56 - 0.3, 0.46), at=(x, 0.3, ZC), mat=FRAME, tint=0.95, bev=0.03)
    posts.box((1.1, 0.16, 0.5), at=(x, 5.4, ZC), mat=FRAME, tint=0.85, bev=0.02)
posts.build("hold_posts", grime=0.2, tideline=True, props={"col": 1})

# Cargo crates that float up with the tide: the high-water bridge from the
# islet to the mast's foot, jammed in a curve across the lagoon where the swell
# left them. They rest on the lagoon floor at low tide. At high water their
# tops sit at 2.4: hop down from the islet's sheer face, along the jam, and up
# onto the mast's foot from the last one, right under it.
for _ in range(18):
    rnd.random()  # the blockout's breach planks drew these; keep the deck's barrels where they were


def jam(n, p0=(-16.6, 9.2), c=(-12.5, 14.0), p2=(-8.8, 10.95)):
    """n points evenly along a curve from p0 to p2 (bowed toward c), with the turn that lays a crate along it."""
    pts = [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p2[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p2[1]) for t in (k / 200 for k in range(201))]
    run = [0.0]
    for a, b in zip(pts, pts[1:]):
        run.append(run[-1] + math.dist(a, b))
    out = []
    for i in range(n):
        k = min(range(len(run)), key=lambda j: abs(run[j] - run[-1] * i / (n - 1)))
        a, b = pts[max(0, k - 1)], pts[min(len(pts) - 1, k + 1)]
        out.append((pts[k][0], pts[k][1], math.atan2(-(b[1] - a[1]), b[0] - a[0])))
    return out


JAM = jam(6)
jr = random.Random(17)  # the jam's own dice: knocked askew, not laid in a row
for i, (x, z, yaw) in enumerate(JAM):
    off = (jr.random() - 0.5) * 0.5 if 0 < i < len(JAM) - 1 else 0.0
    x, z = x - math.sin(yaw) * off, z - math.cos(yaw) * off
    prop("buoy_crate", f"BUOY_crate_{i}", x, z, y=-0.5, yaw=yaw + (jr.random() - 0.5) * (0.35 if i == len(JAM) - 1 else 0.9),
         props={"float": -0.3, "min": -0.5, "max": 1.5})

# --------------------------------------------------------------- deck dressing

for i, (x, z) in enumerate([(-14.0, -8.0), (-13.0, -8.6), (12.0, -16.5), (25.0, -7.5), (26.0, -16.8)]):
    prop("barrel", f"barrel_deck_{i}", x, z, y=DECK)
for i, (x, z) in enumerate([(14.5, -7.2), (15.6, -7.4)]):
    prop("supply_crate", f"crate_deck_{i}", x, z, y=DECK, yaw=0.3 * i)
prop("lantern_post", "lantern_deck", -21.5, -7.0, y=DECK, yaw=math.pi)

# Lanterns someone left burning in the hold.
prop("lantern_post", "lantern_hold_aft", -12.5, -8.0, y=floor_y(-12.5), yaw=math.pi)
prop("lantern_post", "lantern_hold_fore", 18.0, -8.0, y=floor_y(18.0), yaw=math.pi)
dress("lantern_hanging", "lantern_hold_ramp", -9.5, -14.4, y=5.56, yaw=0.0)

# Clutter in the hold.
for i, (x, z) in enumerate([(22.0, -8.0), (23.5, -8.2), (-2.0, -16.6), (10.0, -16.4), (-15.0, -8.0)]):
    prop("barrel", f"barrel_hold_{i}", x, z, y=floor_y(x))
for i, (x, z) in enumerate([(18.0, -15.8), (-13.5, -9.0)]):
    prop("supply_crate", f"crate_hold_{i}", x, z, y=floor_y(x), yaw=0.2 + i)

# Ropes and casks about the deck.
for i, (x, z, yaw) in enumerate([(8.6, -16.9, 0.4), (-6.4, -16.8, 2.0), (27.6, -15.6, 1.1), (-19.0, -7.0, 0.2)]):
    dress("rope_coil", f"rope_deck_{i}", x, z, y=DECK, yaw=yaw)
for i, (x, z) in enumerate([(13.2, -16.7), (-11.6, -16.8), (-12.3, -16.2)]):
    dress("cask_small", f"cask_deck_{i}", x, z, y=DECK)

# ------------------------------------------------------------ the islet and the boat

# The boat lies in the gut at any tide; you come ashore at its head.
prop("rowboat", "BUOY_boat", -42.6, 4.25, y=0.0, yaw=math.pi / 2, props={"interact": "boat", "range": 6.0, "float": -0.15, "min": -1.0, "max": 2.5})
kit.empty("SPAWN_landing", (LANDING[0], H(LANDING[0], LANDING[1]) + 0.05, LANDING[1]), yaw=look(1.0, -0.45))
HULK = (44.0, 22.0)  # the older wreck's bones, on the reef's far side
# The way the Meridian's cargo spilled from the breach across the reef.
SPILL = [(2.0, -4.0, 0.0), (9.0, 6.0, 0.0), (16.0, 14.0, 0.0), (22.0, 22.0, 0.0)]

# ------------------------------------------------------------------ rocks
# home.blend's unit boulders (kit.Boulders): bedded on the reef's outer parts,
# or, where the ground falls away, sea rocks stood up out of the deep.

rocks = kit.Boulders(HOME, H, vr)
boulder = rocks.boulder


def rock_ok(x, z):
    """Boulders keep off the low band between the islet and the breach, the
    lagoon, the islet and its tail, the gut, the hull's sides, the spill, the
    old hulk and the cliff faces."""
    if poly_sd(x, z, SWIM)[0] < 1.5 or poly_sd(x, z, LAGOON)[0] < 2.0 or poly_sd(x, z, ISLET)[0] < 1.5:
        return False
    if along(x, z, TAIL)[0] < 5.0 or along(x, z, GUT)[0] < 4.5 or along(x, z, SPILL)[0] < 4.0 or math.hypot(x - HULK[0], z - HULK[1]) < 6.0:
        return False
    if STERN - 3.0 < x < STEM + 3.0 and NORTH - 3.0 < z < SOUTH + 3.0:
        return False
    return not (H(x, z) > rocks.sea_rock and grade(x, z) > 1.0)


def coast(edges, off, gap, size, fit=rock_ok):
    """Rocks along a coast: `edges` are (a, b, outward normal); each rock
    `off` metres out from its edge, about `gap` apart."""
    for (ax, az), (bx, bz), (nx, nz) in edges:
        L = math.hypot(bx - ax, bz - az)
        t = vr.random() * gap
        while t < L:
            if vr.random() < 0.6:
                o = off[0] + vr.random() * (off[1] - off[0])
                x, z = ax + (bx - ax) * t / L + nx * o, az + (bz - az) * t / L + nz * o
                if fit(x, z):
                    boulder(x, z, size[0] + vr.random() * (size[1] - size[0]))
            t += gap * (0.8 + 0.5 * vr.random())


def outward(poly, skip=()):
    """A closed outline's edges with the normal that points out of it."""
    for i in range(len(poly)):
        if i in skip:
            continue
        (ax, az), (bx, bz) = poly[i], poly[(i + 1) % len(poly)]
        L = math.hypot(bx - ax, bz - az)
        nx, nz = (bz - az) / L, -(bx - ax) / L
        if poly_sd((ax + bx) / 2 + nx, (az + bz) / 2 + nz, poly)[0] < 0:
            nx, nz = -nx, -nz
        yield (ax, az), (bx, bz), (nx, nz)


def seaward(line):
    """A ridge's segments with the normal on its outside (the rampart's flats are on its left)."""
    for (ax, az, _), (bx, bz, _) in zip(line, line[1:]):
        L = math.hypot(bx - ax, bz - az)
        yield (ax, az), (bx, bz), (-(bz - az) / L, (bx - ax) / L)


coast(outward(ISLET, {2, 3, 4, 5, 6}), (4.0, 7.0), 3.4, (1.6, 3.4))
coast(seaward(RAMPART), (5.5, 9.5), 4.2, (1.8, 3.6))
# Boulders along the rampart's crest, on its seaward half: the walk along its top stays clear.
coast(seaward(RAMPART[1:-1]), (1.4, 2.6), 5.0, (0.9, 1.9), fit=lambda x, z: True)
# A few sea rocks off the ship's north side, where the reef ends at her hull.
for x, z in [(-40.0, -24.0), (-28.0, -27.5), (22.0, -26.0), (49.0, -21.0), (54.0, -15.5)]:
    for _ in range(3):
        boulder(x + vr.uniform(-3.0, 3.0), z + vr.uniform(-2.5, 2.5), 2.0 + vr.random() * 1.6)
# Rock heads standing out of the flats by the rampart's foot, dry at high water.
heads = 0
for _ in range(600):
    if heads >= 10:
        break
    x, z = vr.uniform(-6.0, 52.0), vr.uniform(-12.0, 30.0)
    if (x > 30.0 or z > 20.0) and poly_sd(x, z, REEF)[0] < -3.0 and belt(x, z) > 0.9 and along(x, z, RAMPART)[0] > 5.0 and rock_ok(x, z):
        boulder(x, z, 1.0 + vr.random() * 1.3, sink=0.35)
        heads += 1
# The stacks: unit boulders piled and stretched up out of the deep.
for x, z, top, size in STACKS:
    rocks.stack(x, z, top, size, SEA_FLOOR)
# Stones bedded round the islet's outcrops.
for ox, oz, orad, _ in OUTCROPS:
    for _ in range(2):
        a = vr.random() * math.tau
        boulder(ox + math.cos(a) * orad * 0.9, oz + math.sin(a) * orad * 0.9, 0.7 + vr.random() * 0.6, sink=0.5)

# ---------------------------------------------------------------- dressing

# The reef beacon on the islet's crag: an iron pole with a basket on top, a
# daymark for boats coming in, guyed with chain to rings in the rock.
bx, bz = CRAG
by = H(bx, bz)
beacon = MB(60)
beacon.rock(1.1, at=(0.0, -0.4, 0.0), mat=P["rock_dark"], seed=61, squash=0.45, cuts=5)
for k in range(9):
    a = k / 9 * math.tau
    beacon.rock(0.32 + vr.random() * 0.12, at=(math.cos(a) * 0.75, 0.1 + vr.random() * 0.15, math.sin(a) * 0.75), mat=P["rock"], seed=62 + k, squash=0.7, cuts=3)
beacon.cyl(0.11, 0.08, 6.4, at=(0.0, 0.0, 0.0), mat=IRON, segs=8)
for y in (5.0, 5.75, 6.5):
    beacon.ring(0.55 - (y - 5.0) * 0.16, 0.035, at=(0.0, y, 0.0), mat=RUST, segs=14, tube_segs=4)
for k in range(6):
    a = k / 6 * math.tau
    beacon.tube([(math.cos(a) * 0.55, 5.0, math.sin(a) * 0.55), (math.cos(a) * 0.31, 6.5, math.sin(a) * 0.31)], 0.03, mat=RUST, segs=4)
for k in range(3):
    a = k / 3 * math.tau + 0.4
    beacon.tube(sag((0.0, 4.6, 0.0), (math.cos(a) * 3.2, 0.25, math.sin(a) * 3.2), 0.2), 0.022, mat=IRON, segs=4)
    beacon.ring(0.09, 0.025, at=(math.cos(a) * 3.2, 0.2, math.sin(a) * 3.2), mat=IRON, segs=8, tube_segs=4)
beacon.build("reef_beacon", loc=(bx, by, bz), grime=0.3, props={"col": 1})
kit.empty("FX_perch_beacon", (bx, by + 6.75, bz))

# The old hulk: an older wooden wreck's ribs, half sunk in the reef.
for i, (dx, dz, yaw) in enumerate([(0.0, 0.0, 0.5), (3.4, 2.1, 0.62)]):
    prop("hull_ribs", f"hulk_ribs_{i}", HULK[0] + dx, HULK[1] + dz, yaw=yaw)
glow = MB()
for i in range(14):
    x = HULK[0] - 6 + rnd.random() * 12
    z = HULK[1] - 5 + rnd.random() * 10
    glow.sphere(0.08 + rnd.random() * 0.1, at=(x, H(x, z) + 0.05, z), mat=GLOW, subdiv=1)
glow.build("debris_glows")

def tip(ob, pitch=0.0, roll=0.0):
    """Knocks a placed prop over: pitch about its own x, roll about its z (game axes)."""
    yaw = ob.rotation_euler[2]
    ob.rotation_euler = (pitch, roll, yaw)
    return ob


def bale(m, at, yaw, size=(1.0, 0.7, 0.75)):
    """A canvas-wrapped bale, roped twice round."""
    x, y, z = at
    sx, sy, sz = size
    m.box((sx, sy, sz), at=(x, y, z), mat=CANVAS, yaw=yaw, bev=0.08, jit=0.12)
    for k in (-0.28, 0.28):
        ox, oz = math.cos(yaw) * k * sx, -math.sin(yaw) * k * sx
        m.box((0.05, sy + 0.03, sz + 0.03), at=(x + ox, y - 0.015, z + oz), mat=ROPE, yaw=yaw, bev=0.012)


# The salvagers' camp, on the islet's crown in the lee of its outcrops: a lean-to
# of canvas over two pairs of crossed oars, a cold fire ring, what they'd hauled
# up, and the sheerlegs they hauled it with, over the lagoon's sheer face.
CAMP = (-31.2, 8.6)
camp = MB(70)
cx, cz = CAMP
cy = H(cx, cz)
for dx in (-1.6, 1.6):
    for s in (-1, 1):
        camp.tube([(dx, -0.05, s * 0.9), (dx + 0.05 * s, 1.75, -0.08 * s)], 0.035, mat=TEAK, segs=5)
        camp.box((0.16, 0.5, 0.03), at=(dx + 0.05 * s, 1.55, -0.07 * s), mat=TEAK, yaw=0.0, bev=0.005)
camp.tube([(-1.9, 1.62, 0.0), (1.9, 1.62, 0.0)], 0.045, mat=SPAR, segs=6)
# The canvas: over the ridge and down to pegs on the windward side, sagging between.
secs = []
for k in range(6):
    x = -1.85 + k * 0.74
    sag_ = 0.12 * math.sin(k / 5 * math.pi)
    secs.append([(x, 1.66, 0.0), (x, 1.05 - sag_, 1.05), (x, 0.42 - sag_ * 0.5, 1.9), (x, 0.06, 2.25)])
camp.loft(secs, mat=Paint(CANVAS.mat, 0xB8AA88), jit=0.08)
for k in (-1.7, 0.0, 1.7):
    camp.tube([(k, 0.06, 2.25), (k, -0.05, 2.45)], 0.025, mat=TEAK, segs=4)
# The fire ring, cold, a charred log across it, and a kettle.
for k in range(9):
    a = k / 9 * math.tau
    camp.rock(0.16 + vr.random() * 0.05, at=(0.6 + math.cos(a) * 0.62, -0.02, -1.6 + math.sin(a) * 0.62), mat=P["rock"], seed=71 + k, squash=0.7, cuts=2)
camp.cyl(0.5, 0.5, 0.03, at=(0.6, -0.01, -1.6), mat=SOOT, segs=12, bev=0)
for k in range(3):
    a = 0.4 + k * 2.1
    camp.tube([(0.6 + math.cos(a) * 0.4, 0.06, -1.6 + math.sin(a) * 0.4), (0.6 - math.cos(a) * 0.35, 0.09, -1.6 - math.sin(a) * 0.35)], 0.07, mat=SOOT, segs=6)
camp.cyl(0.16, 0.13, 0.22, at=(1.3, 0.0, -2.2), mat=IRON, segs=10)
camp.build("camp", loc=(cx, cy, cz), yaw=0.35, grime=0.3)
prop("supply_crate", "camp_crate_0", cx - 2.6, cz + 0.6, yaw=0.3)
prop("supply_crate", "camp_crate_1", cx - 2.4, cz - 0.6, yaw=1.1)
prop("cask_small", "camp_cask_0", cx + 2.4, cz + 1.4)
prop("cask_small", "camp_cask_1", cx + 2.9, cz + 0.8)
prop("barrel", "camp_barrel", cx - 2.0, cz + 2.0)
prop("plank_pile", "camp_planks", cx + 2.0, cz - 2.6, yaw=0.9)
prop("lobster_pot", "camp_pot", cx - 1.2, cz - 2.4, yaw=2.0)
dress("rope_coil", "camp_rope", cx + 1.0, cz + 2.4)
prop("lantern_post", "lantern_camp", cx + 1.9, cz - 0.4, yaw=-2.4)
prop("lantern_post", "lantern_landing", -39.4, 6.6, yaw=2.6)

# The sheerlegs over the lagoon: three spars lashed at the head, a block and fall hanging down to the water.
SHEER = (-20.2, 4.6)
legs = MB(72)
head = (SHEER[0] + 0.9, 5.4, SHEER[1])
for fx, fz in ((-2.6, -1.6), (-2.6, 1.6), (-0.3, 0.0)):
    fy = H(SHEER[0] + fx, SHEER[1] + fz) - 0.15
    legs.tube([(SHEER[0] + fx, fy, SHEER[1] + fz), head], 0.09, mat=SPAR, segs=7)
legs.cyl(0.16, 0.16, 0.3, at=(head[0], head[1] - 0.15, head[2]), mat=ROPE, segs=8)
legs.box((0.14, 0.36, 0.22), at=(head[0] + 0.15, head[1] - 0.62, head[2]), mat=TEAK, bev=0.02)
legs.tube([(head[0] + 0.2, head[1] - 0.8, head[2]), (head[0] + 0.25, 1.0, head[2] + 0.1)], 0.02, mat=ROPE, segs=4)
legs.tube([(head[0] + 0.1, head[1] - 0.8, head[2]), (SHEER[0] - 2.2, H(SHEER[0] - 2.2, SHEER[1] + 2.4) + 0.1, SHEER[1] + 2.4)], 0.02, mat=ROPE, segs=4)
legs.build("sheerlegs", grime=0.2)
kit.empty("FX_perch_sheerlegs", (head[0], head[1] + 0.15, head[2]))

# What spilled from the breach: the cargo she carried, thinning out across the reef.
spill = MB(74)
cargo = 0


def cargo_prop(kind, x, z, pitch=0.0, roll=0.0, yaw=None):
    global cargo
    ob = dress(kind, f"spill_{kind}_{cargo}", x, z, y=H(x, z) - 0.04, yaw=yaw)
    cargo += 1
    return tip(ob, pitch, roll)


for x, z, kind, p_, r_ in [(-1.5, -3.2, "supply_crate", 0.0, 0.2), (0.5, -1.0, "barrel", 1.57, 0.0), (3.6, -2.4, "supply_crate", 0.25, 0.0),
                           (6.0, -0.4, "barrel", 0.0, 0.0), (4.4, 2.8, "cask_small", 1.4, 0.0), (8.2, 3.6, "supply_crate", 0.0, -0.3),
                           (11.5, 6.0, "barrel", 1.57, 0.5), (13.0, 10.8, "supply_crate", 0.0, 0.0), (15.8, 12.6, "cask_small", 0.0, 0.0),
                           (17.5, 15.5, "barrel", 1.5, 0.0), (21.0, 19.8, "supply_crate", 0.3, 0.0), (19.5, 21.5, "barrel", 0.0, 0.0),
                           (-3.8, 0.8, "plank_pile", 0.0, 0.0), (9.5, 12.5, "plank_pile", 0.0, 0.1), (2.2, 6.5, "rope_coil", 0.0, 0.0)]:
    cargo_prop(kind, x, z, p_, r_)
for x, z, yaw in [(1.8, 0.6, 0.4), (7.0, 1.2, 1.9), (10.2, 4.0, 0.7), (16.4, 17.6, 2.4)]:
    bale(spill, (x, H(x, z) + 0.3, z), yaw)
# Coal from her bunkers, in heaps where the sea dropped it.
for k, (x, z, n) in enumerate([(-0.8, 3.4, 9), (5.2, 6.4, 6), (12.4, 15.6, 4)]):
    for j in range(n):
        a, r = vr.random() * math.tau, vr.random() * 0.9
        spill.rock(0.12 + vr.random() * 0.12, at=(x + math.cos(a) * r, H(x, z) - 0.02, z + math.sin(a) * r), mat=SOOT, seed=80 + k * 10 + j, squash=0.7, cuts=2)
# Her lifeboat, stove in and swamped where it fetched up.
tip(dress("wreck_boat", "spill_lifeboat", 6.4, 10.8, y=H(6.4, 10.8) - 0.2, yaw=0.8, scale=0.8), 0.0, 0.0)
# A broken yard with its rigging, dragged out by the tide.
spill.tube([(13.5, H(13.5, 8.0) + 0.12, 8.0), (18.0, H(18.0, 10.5) + 0.2, 10.5), (22.5, H(22.5, 12.0) + 0.1, 12.0)], [0.16, 0.13, 0.1], mat=SPAR, segs=8)
for t in (0.2, 0.5, 0.8):
    x, z = lerp(13.5, 22.5, t), lerp(8.0, 12.0, t)
    spill.tube(sag((x, H(x, z) + 0.3, z), (x + 1.2, H(x + 1.2, z + 2.5) + 0.04, z + 2.5), 0.1, 6), 0.02, mat=TARRED, segs=4)
spill.build("spill", grime=0.25, tideline=True)
# Her anchor, dragged from the bow, and its cable run out over the reef.
dress("anchor", "spill_anchor", 30.5, 9.0, y=H(30.5, 9.0) - 0.05, yaw=2.6)
cable = MB(75)
cable.tube(sag((35.5, 3.2, -7.4), (30.8, H(30.8, 8.2) + 0.12, 8.2), -0.2, 12), 0.09, mat=RUST, segs=6)
cable.build("anchor_cable", grime=0.3, tideline=True)

# Junk on the lagoon's bed, under the crates: a hatch cover and a spar, chained to the islet's rock.
junk = MB(76)
junk.box((2.6, 0.18, 2.0), at=(-13.4, -0.46, 5.0), mat=DECKW, yaw=0.4, bev=0.03, tint=0.7)
for k in range(5):
    junk.box((2.7, 0.06, 0.3), at=(-13.4, -0.27, 4.2 + k * 0.4), mat=TEAK, yaw=0.4, bev=0.01, tint=0.75)
junk.tube([(-17.6, -0.4, 1.6), (-12.0, -0.38, 0.4), (-8.6, -0.42, -1.6)], [0.22, 0.2, 0.16], mat=SPAR, segs=8)
junk.tube(sag((-18.9, 1.4, 1.2), (-17.4, -0.35, 1.6), -0.1, 8), 0.05, mat=RUST, segs=5)
junk.build("lagoon_junk", grime=0.2, tideline=True)

# The old hulk's keel and stem, her knees and a few planks still on her.
hulk = MB(77)
hx, hz = HULK
ky = H(hx, hz) - 0.25
a = 0.55
ux, uz = math.cos(a), -math.sin(a)
hulk.tube([(hx - ux * 7.0, ky - 0.1, hz - uz * 7.0), (hx, ky + 0.05, hz), (hx + ux * 7.5, ky + 0.15, hz + uz * 7.5)], 0.22, mat=P["driftwood_dark"], segs=7)
sx_, sz_ = hx + ux * 7.5, hz + uz * 7.5
hulk.tube([(sx_, ky + 0.15, sz_), (sx_ + ux * 1.2, ky + 2.0, sz_ + uz * 1.2), (sx_ + ux * 1.1, ky + 3.9, sz_ + uz * 1.1)], [0.2, 0.17, 0.12], mat=P["driftwood_dark"], segs=7)
for k in range(5):
    t = -5.0 + k * 2.4
    px, pz = hx + ux * t, hz + uz * t
    hulk.box((2.4 + vr.random(), 0.06, 0.28), at=(px - uz * 1.2, H(px - uz * 1.2, pz + ux * 1.2) + 0.05, pz + ux * 1.2), mat=P["hull"], yaw=a + (vr.random() - 0.5) * 0.4, bev=0.01, tint=0.8)
hulk.build("hulk", grime=0.3, tideline=True)
kit.empty("FX_perch_hulk", (sx_ + ux * 1.1, ky + 4.0, sz_ + uz * 1.1))

# Weed in the gullies and the tide pools, and wrack along the rampart's foot where high water stops.
weeds = 0
for _ in range(900):
    if weeds >= 46:
        break
    x, z = vr.uniform(-18.0, 52.0), vr.uniform(-5.0, 28.0)
    y = H(x, z)
    if poly_sd(x, z, REEF)[0] > -1.0 or poly_sd(x, z, LAGOON)[0] < 0.5 or along(x, z, SPILL)[0] < 2.0 or under_hull(x, z):
        continue
    if (y < 0.55 and ribness(x, z) < 0.3) or abs(y - HW) < 0.25:
        dress("seaweed", f"weed_{weeds}", x, z, scale=0.8 + vr.random() * 0.6)
        weeds += 1
# Barnacled stones along the ribs' crests.
stones = MB(78)
for rib in RIBS:
    for (ax, az, _), (bx, bz, _) in zip(rib, rib[1:]):
        L = math.hypot(bx - ax, bz - az)
        for k in range(int(L / 1.4)):
            t = (k + vr.random()) / int(L / 1.4)
            x, z = lerp(ax, bx, t) + vr.uniform(-0.9, 0.9), lerp(az, bz, t) + vr.uniform(-0.9, 0.9)
            stones.rock(0.14 + vr.random() * 0.16, at=(x, H(x, z) - 0.05, z), mat=P["rock_dark"] if vr.random() < 0.6 else P["rock"], seed=200 + int(x * 7 + z * 13) % 997, squash=0.55, cuts=2)
stones.build("reef_stones", grime=0.2, tideline=True)

prop("tide_pole", "tidepole_lagoon", -6.5, 12.5, y=0.0, yaw=0.0)
prop("tide_pole", "tidepole_reef", 20.0, 9.0, y=0.0, yaw=0.0)

# --------------------------------------------------------------- gathering


def node(kind, i, x, z, y=None, prop_name=None):
    return prop(prop_name or kind, f"NODE_{kind}_{i:02d}", x, z, y=y, props={"node": kind})


# The spill: broken spars, and the machinery the sea broke out of her.
for i, (x, z) in enumerate([(10.0, 8.5), (19.0, 17.5), (-3.5, 17.0), (36.5, 4.5)]):
    node("driftwood", i, x, z)
for i, (x, z, y) in enumerate([(5.5, 1.5, None), (27.0, 22.0, None), (-12.0, -12.5, DECK), (19.0, -9.0, DECK)]):
    node("scrap_pile", i, x, z, y=y)
# Brass-strapped plating: along the hold, and torn off by the breach.
for i, (x, z, y) in enumerate([(24.0, -7.3, floor_y(24.0)), (-6.0, -7.3, floor_y(-6.0)), (-20.0, -7.3, floor_y(-20.0)), (8.6, -4.5, None)]):
    node("reinforced_wreckage", i, x, z, y=y)
# Kelp in the tide pools nearest the breach (low water).
for i, (x, z) in enumerate([(-1.0, 6.0), (15.5, 3.5)]):
    node("kelp_bed", i, x, z)
node("strongbox", 0, 33.5, -12.0, y=DECK)
kit.empty("NODE_fish_glowgill_00", (-44.0, 0, -14.0), props={"node": "fish_glowgill"})

# ----------------------------------------------------------------- enemies

for i, (x, z) in enumerate([(2.0, 8.0), (14.0, 12.5), (26.0, 5.0), (-3.0, 19.5)]):
    kit.empty(f"ENEMY_crab_low_{i}", (x, H(x, z), z), props={"enemy": "brine_crab", "tide": "low"})
for i, (x, y, z) in enumerate([(12.0, 0.3, -12.5), (-3.0, 0.55, -9.0), (30.0, DECK, -12.0)]):
    kit.empty(f"ENEMY_spitter_{i}", (x, y, z), props={"enemy": "drowned_spitter", "tide": "any"})
for i, (x, y, z) in enumerate([(HULK[0] - 2.0, 2.8, HULK[1] - 1.0), (2.0, DECK + 2.0, -12.0), (-17.0, DECK + 2.5, -2.0)]):
    kit.empty(f"ENEMY_wisp_{i}", (x, y, z), props={"enemy": "lantern_wisp", "tide": "any"})
for i, (x, z) in enumerate([(-12.5, 4.0), (8.0, 3.0)]):
    kit.empty(f"ENEMY_lurker_{i}", (x, 0.0, z), props={"enemy": "tide_lurker", "tide": "high"})

# Taking the lens wakes the ship: FX_ambush_<enemy id>_<n>.
kit.empty("FX_ambush_lantern_wisp_1", (-19.0, DECK + 2.5, -10.0))
kit.empty("FX_ambush_lantern_wisp_2", (-29.0, DECK + 3.5, -1.5))
kit.empty("FX_ambush_drowned_spitter_1", (-14.0, DECK, -9.5))

# ------------------------------------------------------------------ gloom

# GLOOM_ pockets: the Gloom has settled in the dark rooms. One wraps the Drowned
# Lens in the chart room (the game's first lesson in the Lantern Flare), one
# sits in the aft hold over a heap of brass.
kit.empty("GLOOM_chart_room", (-30.5, DECK, -12.0), props={"radius": 3.2})
kit.empty("GLOOM_hold", (-19.0, floor_y(-19.0), -9.5), props={"radius": 3.0})

# ---------------------------------------------------- anchors and the beam

# Ground level only (being rescued onto the deck would skip both routes), and
# none deeper than a wade at high water, or the current would put you back in.
for name, (x, z) in {"islet": (-31.0, 4.0), "islet_south": (-28.5, 13.5), "tail": (-14.0, 19.5), "rampart_w": (4.0, 28.4),
                     "horn": (43.5, 23.0), "bow_sand": (36.0, 10.0)}.items():
    kit.empty(f"ANCHOR_{name}", (x, H(x, z) + 0.1, z))
# Lantern's Rest lies to the north; its beam shows on the horizon.
kit.empty("FX_home_light", (-140, 0, -320))

kit.save_and_export("art/blender/locations/wreck.blend", "public/assets/models/locations/wreck.glb")
