"""Builds art/blender/locations/home.blend and public/assets/models/locations/home.glb.

Lantern's Rest, the player's base, laid out per docs/LEVELS.md (game space,
metres; the sea is at y 0 at low tide and 1.8 at high tide, and the cove opens
south, toward +z):

  village   the upper terrace, y 7: the square on its sea wall (the hearth,
            the chest, a parapet to look out over the cove), the forge plot on
            its west side and three cottage plots round it; the well, the
            washing, fields and the memorial behind
  knoll     the lighthouse on its rock, y 12.5, north-east; a path climbs the
            knoll's south flank from the village
  quay      the lower terrace, y 4, down a ramp from the square: the net loft
            and smokehouse plots, Tib's other boat on its trestles
  cove      the beach under the quay's sea wall, a slipway down the middle and
            the jetty plot along the east side; the wreck field the low tide
            uncovers; two rock arms with walks along their crowns, a fishing
            ledge under the west one, and the mouth between their tips where
            the drift comes in

Plots (PLOT_<project>, turned to face the way in) carry both states,
<id>_ruin and <id>_built, and a name board (<id>_board, interact plot:<id>);
the game shows one and raises the other as materials come in. The other
markers: SPAWN_start (a new game, at the lighthouse door), SPAWN_landing (the
beach by the jetty: where the tide sweep starts), SPAWN_jetty (off the boat);
NPC_<id> and PLACE_family_<n>_<i> (where people stand); PLACE_lighthouse (the
tower, for the beam to stand in); INT_hearth, INT_chest, INT_lamp; BUOY_boat
and BUOY_boat_2 (moored once the jetty stands); FX_drift_<lane>_<k> (each lane
from beyond the mouth to the strand); FX_strand_<n> (where beached drift
lies); NODE_ (the wreck field and the fishing); FX_decor_<n> (the outline you
may decorate inside) and CLEAR_<n> (a radius kept clear of decor);
FX_perch_<n>, FX_gulls; ANCHOR_. SCATTER_grass holds one triangle per tuft
(first corner: where it grows; the second: which way it turns and how big)
for the game to instance.

    blender -b --factory-startup --python tools/blender/build/home_map.py
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import kit  # noqa: E402
from kit import MB, Paint, fbm3, lerp, noise2, seg_dist, smoothstep  # noqa: E402

kit.reset()

T = kit.load_props()
HOME = kit.load_home()
P = kit.palette()
# `rnd` lays out the level, `vr` dresses it: changing the dressing never moves a marker.
rnd = random.Random(5)
vr = random.Random(55)

TAU = math.tau
HW = kit.HIGH_WATER
VT, LT, KNOLL = 7.0, 4.0, 12.5  # village terrace, quay, knoll top
DEEP = -8.0
# Off the cove the coast (the village's cliffs, the knoll, the arms' seaward
# flanks) runs steep all the way down to a flat sea floor this deep, past
# wading at low water: nothing out there is a shelf in the tide's reach you
# could wade onto at one tide and not climb off before the next (the tide sweep,
# GDD section 6). Fall off the outside of the Rest and you're swimming, and the
# current brings you in. The cove's beach, flats and shelf are what the tide is for.
SEA_FLOOR = -3.0
SEA_ROCK = -0.7  # ground lower than this, and a boulder is a sea rock instead
SEA_ROCK_GAP = 1.8  # the least water between a sea rock and the shore
KC = (33.0, -35.0)  # the knoll's centre
TOWER = (34.0, -37.0)
TOWER_YAW = -0.983  # its door faces the square


def smax(a, b, k):
    """Smooth max: the larger of two heights, rounded over where they're within k of each other."""
    h = max(k - abs(a - b), 0.0) / k
    return max(a, b) + h * h * k * 0.25


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    out = 0
    for sh in (16, 8, 0):
        ca, cb = (a >> sh) & 255, (b >> sh) & 255
        out |= int(round(ca + (cb - ca) * t)) << sh
    return out


def turn(yaw, lx, lz):
    """A local (x, z) offset turned by yaw, the way three.js turns rotation.y."""
    c, s = math.cos(yaw), math.sin(yaw)
    return lx * c + lz * s, -lx * s + lz * c


def facing(dx, dz):
    """The yaw that turns a model's front (+Z) toward (dx, dz)."""
    return math.atan2(dx, dz)


def look(dx, dz):
    """The yaw for a spawn whose view looks toward (dx, dz) (a camera looks down its -Z)."""
    return math.atan2(-dx, -dz)


# ------------------------------------------------------------------ layout

# The village's front steps out over the quay in the middle: the square stands
# on a bastion, the ramp going down from its front.
VILLAGE = [(34, -10), (34, -18), (28, -24), (26, -40), (22, -52), (8, -57), (-8, -58), (-26, -56), (-41, -51), (-50, -42), (-53, -28), (-50, -14),
           (-44, -10), (-6, -10), (-6, -8), (14, -8), (14, -10)]
VILLAGE_FRONT = {12, 13, 14, 15, 16}  # the walls over the quay
VILLAGE_INLAND = {0, 1, 2, 3}  # edges against the knoll and the east arm
QUAY = [(-36, -10), (31, -10), (31, 5), (28, 13), (-33, 13), (-37, 5)]
# The west arm hooks round to shelter the cove; the east arm is the knoll's
# rocky spur, ending in a point. The mouth opens between them, south-south-east.
COVE = [(-31, 12), (31, 12), (30, 24), (28, 36), (25, 47), (19, 55), (24, 70), (36, 104), (-12, 104), (-4, 72), (-6, 62), (-14, 58), (-24, 53),
        (-32, 44), (-35, 32), (-34, 20)]
WEST_ARM = [(-40, -12, 7.6), (-44, 2, 8.4), (-43, 16, 7.8), (-40, 28, 6.8), (-35, 40, 5.4), (-27, 51, 3.9), (-18, 59, 2.6), (-10, 64, 1.4), (-5, 66.5, 0.4)]
EAST_ARM = [(38, -22, 11.0), (41, -8, 9.8), (41, 6, 8.4), (39, 20, 7.0), (35, 34, 5.6), (30, 46, 4.2), (25, 54, 2.8), (21, 58.5, 1.2)]
# Crags on the arms' crowns: (x, z, how big).
TORS = [(-44.0, 7.0, 1.0), (-38.0, 34.0, 0.8), (-23.0, 55.0, 0.9), (41.5, -1.0, 1.0), (37.5, 26.0, 0.9), (27.5, 50.5, 1.1)]
STACKS = [(25.0, 62.5, 2.0), (28.5, 59.0, 1.5), (-7.0, 71.0, 1.4)]
# The cove floor by z: the dry beach under the sea wall, the high-water line at
# z 27, the flats the low tide uncovers, then the mouth.
BEACH = [(13, 2.9), (18, 2.45), (24, 2.0), (27, 1.8), (30, 1.25), (34, 0.6), (38, 0.32), (44, 0.12), (48, 0.0), (52, -0.8), (58, -2.4), (64, -4.5), (72, -7.0), (85, -9.0)]
# Deeper water along the east side, where the jetty runs out and the boats lie.
CHANNEL = [(20, 26, 0.0), (17, 44, 0.0), (13, 70, 0.0)]
KNOLL_PATH = [(17.0, -27.0, 7.0), (20.0, -27.5, 7.0), (24.8, -25.2, 8.1), (28.9, -23.7, 9.2), (33.0, -23.8, 10.3), (36.5, -25.3, 11.4), (38.5, -28.5, 12.5), (37.6, -30.6, 12.5)]
# Under the west arm: a shelf above high water from the beach to the fishing ledge, and a rock pool off it.
SHELF = [(-28.0, 18.5, 2.4), (-31.5, 25.0, 2.48), (-33.0, 30.0, 2.55), (-32.0, 34.0, 2.6)]
LEDGE = (-30.6, 36.0, 3.2)
POOL = (-26.8, 38.6, 4.2)

# The drift's ways in: from beyond the mouth to the strand (the game floats it on the water).
LANES = [
    [(0, 98), (2, 80), (4, 66), (-6, 56), (-15, 46), (-21, 36), (-23, 26)],
    [(4, 98), (5, 80), (6, 66), (-1, 56), (-7, 46), (-12, 36), (-13, 25)],
    [(8, 98), (8, 80), (8, 66), (4, 56), (0, 46), (-3, 36), (-4, 25)],
    [(12, 98), (11, 80), (10, 66), (8, 56), (8, 46), (9, 36), (9.5, 24)],
    [(16, 98), (14, 80), (13, 66), (12, 56), (13, 46), (13.5, 36), (13.5, 23)],
]
LANE_LINES = [[(x, z, 0.0) for x, z in lane] for lane in LANES]
# Where what the tide left lies when you come home.
STRAND = [(-25, 26.0), (-20, 25.4), (-15.5, 26.2), (-10.5, 25.6), (-6, 26.4), (-1.5, 25.8), (9.6, 25.2), (12.4, 26.0), (-18, 23.6), (-8, 23.4)]

# Built ground, (x0, x1, z0, z1): the ramp from the square down to the quay,
# the slipway from the quay to the beach, and steps down at the jetty and the west end.
RAMP = (1.0, 7.0, -8.0, 2.0)
SLIP = (1.0, 7.0, 13.0, 22.0)
JETTY_STEPS = (16.0, 20.0, 10.5, 14.5)
WEST_STEPS = (-26.0, -23.0, 10.0, 14.5)
SQUARE = (-5.0, 13.2, -24.0, -8.2)


def ramp_y(z):
    return lerp(VT, LT, (z - RAMP[2]) / (RAMP[3] - RAMP[2]))


def slip_y(z):
    return lerp(LT, 2.2, max(0.0, z - SLIP[2]) / (SLIP[3] - SLIP[2]))


def jsteps_y(z):
    return lerp(LT, 2.75, max(0.0, z - JETTY_STEPS[2]) / (JETTY_STEPS[3] - JETTY_STEPS[2]))


def wsteps_y(z):
    return lerp(LT, 2.8, max(0.0, z - WEST_STEPS[2]) / (WEST_STEPS[3] - WEST_STEPS[2]))


def in_rect(x, z, r, pad=0.0):
    return r[0] - pad <= x <= r[1] + pad and r[2] - pad <= z <= r[3] + pad


# ---------------------------------------------------------------- terrain


def poly_sd(px, pz, poly):
    """Signed distance to a closed polygon (negative inside) and the nearest edge."""
    best, edge, inside = 1e9, 0, False
    n = len(poly)
    for i in range(n):
        ax, az = poly[i]
        bx, bz = poly[(i + 1) % n]
        d = seg_dist(px, pz, ax, az, bx, bz)
        if d < best:
            best, edge = d, i
        if (az > pz) != (bz > pz) and px < ax + (pz - az) * (bx - ax) / (bz - az):
            inside = not inside
    return (-best if inside else best), edge


def along(px, pz, pts):
    """Nearest point on a polyline of (x, z, y): its distance, its y and how far along (segments)."""
    best = (1e9, 0.0, 0.0)
    for i, ((ax, az, ay), (bx, bz, by)) in enumerate(zip(pts, pts[1:])):
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / L2)) if L2 else 0.0
        d = math.hypot(px - ax - t * dx, pz - az - t * dz)
        if d < best[0]:
            best = (d, ay + (by - ay) * t, i + t)
    return best


def profile(z):
    if z <= BEACH[0][0]:
        return BEACH[0][1]
    for (z0, y0), (z1, y1) in zip(BEACH, BEACH[1:]):
        if z <= z1:
            return lerp(y0, y1, (z - z0) / (z1 - z0))
    return BEACH[-1][1]


def cove_floor(x, z):
    y = profile(z) + 0.07 * noise2(x * 0.21, z * 0.17, 71) * smoothstep(15, 22, z)
    dc = along(x, z, CHANNEL)[0] + 2.2 * fbm3(x * 0.12, 0.0, z * 0.12, 72)
    y -= 2.2 * (1 - smoothstep(1.5, 9.0, dc)) * smoothstep(25, 37, z)
    return y


def seabed(x, z):
    d = poly_sd(x, z, COVE)[0]
    y = cove_floor(x, z)
    return y if d <= 0 else lerp(y, DEEP, smoothstep(0.0, 12.0, d))


def drop(d, top, natural):
    """Land `d` metres past its edge: a rock cliff into the sea, or a built wall's sharp step.
    The cliff runs steep all the way down to the sea floor, with no shelf at its foot."""
    if d <= 0:
        return top
    if natural:
        return top - (top - SEA_FLOOR) * smoothstep(0.0, 5.0, d)
    return top - (top + 2.0) * smoothstep(0.0, 1.0, d) - 6.0 * smoothstep(1.0, 8.0, d)


def village(x, z):
    d, edge = poly_sd(x, z, VILLAGE)
    natural = edge not in VILLAGE_FRONT
    if natural:
        d += 2.2 * fbm3(x * 0.08, 0.0, z * 0.08, 51)
    fields = max(smoothstep(-40, -48, z), smoothstep(-36, -44, x))
    return drop(d, VT + 0.45 * (fbm3(x * 0.05, 0.0, z * 0.05, 53) + 0.35) * fields, natural)


def quay(x, z):
    return drop(poly_sd(x, z, QUAY)[0], LT, False)


def knoll(x, z):
    """The lighthouse's rock: a flat top, then one plunge into deep water. (A
    shoulder part-way down left ledges over the sea you could drop onto and
    never climb off; the village terrace covers its landward side anyway.)"""
    r = math.hypot(x - KC[0], z - KC[1]) + 1.0 * fbm3(x * 0.09, 0.0, z * 0.09, 61)
    top = KNOLL + 0.05 * noise2(x * 0.6, z * 0.6, 62)
    if r <= 10.0:
        return top
    y = top - (KNOLL - SEA_FLOOR) * smoothstep(10.0, 19.0, r)
    return y + 0.45 * fbm3(x * 0.32, 0.0, z * 0.32, 63) * smoothstep(10.0, 12.0, r)


def ridge(x, z, spine, seed, outer):
    """An arm: a rounded crown, its flanks steepening into the sea, its width
    and roughness wandering along it, crags standing up out of the turf. Its
    seaward flank (`outer`: +1 east of the southward spine, -1 west) plunges
    straight to the sea floor; the cove side eases down to the flats."""
    d, y, t = along(x, z, spine)
    i = min(int(t), len(spine) - 2)
    (ax, az, _), (bx, bz, _) = spine[i], spine[i + 1]
    side = ((x - ax) * (bz - az) - (z - az) * (bx - ax)) / math.hypot(bx - ax, bz - az) * outer
    d += 1.4 * fbm3(x * 0.07, 0.0, z * 0.07, seed)
    crown = 2.0 + 1.4 * (fbm3(t * 0.6, 0.0, 0.0, seed + 2) + 0.4)
    over = max(0.0, d - crown)
    cove = y - over * over * 0.115
    sea = y - (y - SEA_FLOOR) * smoothstep(0.0, 6.5, over)
    y = lerp(cove, sea, smoothstep(-3.0, 3.0, side)) + 0.55 * fbm3(x * 0.3, 0.0, z * 0.3, seed + 1) * smoothstep(3.0, 6.0, d)
    for tx, tz, s in TORS:
        r = math.hypot(x - tx, z - tz)
        if r < 5.0 * s:
            y += 1.6 * s * (1 - smoothstep(1.2 * s, 4.5 * s, r + 0.8 * fbm3(x * 0.5, 0.0, z * 0.5, 77)))
    return y


_heights = {}


def H(x, z):
    key = (round(x, 3), round(z, 3))
    y = _heights.get(key)
    if y is not None:
        return y
    # Where the village's cliff meets the knoll's they're blended into one hollow:
    # a hard crease between two falling slopes leaves odd flat facets you could
    # drop onto and not climb off.
    y = max(seabed(x, z), smax(village(x, z), knoll(x, z), 5.0), quay(x, z), ridge(x, z, WEST_ARM, 71, -1), ridge(x, z, EAST_ARM, 75, 1))
    if in_rect(x, z, RAMP):
        y = max(y, ramp_y(z))
    if in_rect(x, z, SLIP):
        y = max(y, slip_y(z))
    # The knoll path: cut into the flank on the uphill side, built out on the other.
    d, py, _ = along(x, z, KNOLL_PATH)
    y = lerp(y, py, 1.0 - smoothstep(1.7, 2.9, d))
    d, py, _ = along(x, z, SHELF)
    y = lerp(y, py, 1.0 - smoothstep(1.4, 2.4, d))
    y = lerp(y, 2.6, 1.0 - smoothstep(LEDGE[2], LEDGE[2] + 0.8, math.hypot(x - LEDGE[0], z - LEDGE[1])))
    y = min(y, lerp(-1.0, y, smoothstep(0.8, POOL[2], math.hypot(x - POOL[0], z - POOL[1]) + 0.5 * noise2(x * 1.3, z * 1.3, 93))))
    if in_rect(x, z, JETTY_STEPS):
        y = jsteps_y(z)
    if in_rect(x, z, WEST_STEPS):
        y = wsteps_y(z)
    y = scour(x, z, y)
    _heights[key] = y
    return y


def scour(x, z, y):
    """The stacks stand in scour holes, so their feet are in deep water like the rest of the outer coast's."""
    for sx, sz, size in STACKS:
        d = math.hypot(x - sx, z - sz) + 0.6 * noise2(x * 0.4, z * 0.4, 97)
        y = min(y, lerp(SEA_FLOOR, y, smoothstep(1.2 * size, 3.2 * size, d)))
    return y


def slope(x, z):
    return math.hypot(H(x + 1, z) - H(x - 1, z), H(x, z + 1) - H(x, z - 1)) / 2


# Worn ground: (x0, z0, x1, z1) paths and (x, z, radius, strength) patches.
PATHS = [
    # the square to the doors, the knoll path, the fields, the garden and the memorial
    (5, -24, 5, -27.6), (-1, -23, -10.5, -31), (-4, -21, -12, -22.6), (-12, -22.6, -22.8, -23.0),
    (12, -21, 17, -27), (-24, -27, -30, -44), (3, -34.5, 9, -41), (-29, -29, -42, -42),
    # the quay: the ramp's foot to the slipway, the net loft, the smokehouse and the jetty, the west steps
    (4, 2, 4, 13), (2, 5.5, -13, 5.8), (6, 5.5, 14, 8.2), (14, 8.2, 18, 10.5), (-4, 8.5, -24.5, 10),
    # the arm walks
    (-38, -12, -44, 2), (-44, 2, -42, 16), (-42, 16, -40, 28), (-40, 28, -35.5, 39), (-35.5, 39, -27.5, 50),
    (38, -22, 41, -8), (41, -8, 40.5, 6), (40.5, 6, 39, 20), (39, 20, 35, 33), (35, 33, 30, 45),
]
WORN = [(-5.6, -17.0, 2.6, 0.8), (5.0, -27.0, 1.8, 0.7), (-10.8, -30.8, 1.8, 0.7), (-23.8, -22.6, 1.8, 0.7), (29.5, -33.5, 3.0, 0.6),
        (-16.0, 5.6, 2.0, 0.7), (16.0, 7.6, 2.0, 0.7), (4.0, 3.5, 3.0, 0.6), (-24.5, 9.5, 1.6, 0.6), (18.0, 10.0, 1.6, 0.6)]


def wear(x, z):
    wob = 0.6 * noise2(x * 0.7, z * 0.7, 37)
    k = 0.0
    for ax, az, bx, bz in PATHS:
        k = max(k, smoothstep(1.6, 0.7, seg_dist(x, z, ax, az, bx, bz) + wob))
    for wx, wz, r, s in WORN:
        k = max(k, s * smoothstep(r, r * 0.45, math.hypot(x - wx, z - wz) + wob))
    return max(k, smoothstep(1.9, 1.2, along(x, z, KNOLL_PATH)[0] + wob * 0.3))


def built(x, z):
    return any(in_rect(x, z, r) for r in (RAMP, SLIP, JETTY_STEPS, WEST_STEPS, SQUARE))


_colors = {}


def color(x, z, y):
    key = (round(x, 3), round(z, 3))
    c = _colors.get(key)
    if c is None:
        c = _colors[key] = surface(x, z, y)
    return c


def surface(x, z, y):
    n = fbm3(x * 0.11, 0.0, z * 0.11, 31)
    f = fbm3(x * 0.6, 0.0, z * 0.6, 32)
    if built(x, z):
        return mix(0x45413B, 0x524D45, 0.5 + 0.5 * f)
    if y <= seabed(x, z) + 0.02:
        # The cove floor and the sea bed.
        if y < -0.5:
            return mix(0x4F5040, 0x5E5A48, 0.5 + 0.5 * n)
        if y < 0.25:
            return mix(0x6E6A52, 0x7C755A, 0.5 + 0.5 * f)
        if y < HW:
            # Wet flats: the ripples the last tide left, weedy where the water lies longest.
            ripple = 0.5 + 0.5 * math.sin(z * 1.1 + x * 0.2 + n * 3.0)
            c = mix(0x857A5E, 0x9A8D6C, ripple * 0.6 + 0.2 * f)
            return mix(c, 0x5F6A5E, smoothstep(0.35, 0.6, n) * 0.6)
        if y < 2.4:
            # The strand, with a dark line of wrack where high water stops.
            c = mix(0xA8996F, 0xB8A87E, 0.5 + 0.5 * f)
            return mix(c, 0x5A5236, smoothstep(0.15, 0.0, abs(y - 1.95)) * 0.6)
        return mix(0xC6B68C, 0xD4C49A, 0.5 + 0.5 * f)
    if along(x, z, SHELF)[0] < 1.8 or math.hypot(x - LEDGE[0], z - LEDGE[1]) < LEDGE[2]:
        return mix(0x8E846C, 0xA0957A, 0.5 + 0.5 * f)
    wet = smoothstep(HW + 0.5, HW - 0.2, y)
    rock = mix(0x58554E, 0x76726A, 0.5 + 0.6 * n)
    rock = mix(rock, 0xA0915A, smoothstep(0.35, 0.65, f) * 0.3 * smoothstep(2.5, 3.5, y))
    rock = mix(rock, 0x4F5442, wet * 0.75)
    turf = mix(0x4C5C3A, 0x6A794A, 0.5 + 0.6 * n)
    turf = mix(turf, 0x868052, smoothstep(0.2, 0.5, f) * 0.5)
    if abs(y - LT) < 0.05 and poly_sd(x, z, QUAY)[0] < 0:
        # The quay is worked ground: hard-standing toward the sea wall, turf only at its back.
        turf = mix(turf, mix(0x7E7462, 0x958B76, 0.5 + 0.5 * f), smoothstep(-6, 5, z) * (0.7 + 0.25 * n))
    turf = mix(turf, mix(0x857760, 0x9B907A, 0.5 + 0.5 * f), wear(x, z))
    steep = smoothstep(0.55, 0.95, slope(x, z) + 0.15 * f)
    return mix(turf, rock, max(steep, wet))


ground = kit.material("TIDE_ground", 0xFFFFFF, rough=0.95, vcol=True)
kit.terrain("terrain", -66, 62, -72, 90, 1.0, H, color, ground, props={"col": 1})


# ------------------------------------------------------------------- walls
# Mortared stone: a dark mortar face with coursed stones a little proud of it,
# coping slabs over the top. Every wall has a plain collision box behind its
# face, so the terrain's one-metre step under it never decides where you stop.

STONE = P["stone"].mat
MORTAR = Paint(STONE, 0x57524A)
COURSED = [Paint(STONE, c) for c in (0x9C968A, 0x8E887C, 0xA7A194, 0x857F73, 0x948C7C, 0xACA596)]
COPING = [Paint(STONE, c) for c in (0xB4AEA1, 0xA8A294, 0xBDB7A9)]
FLAGS = [Paint(STONE, c) for c in (0x8F897D, 0x9C9588, 0x857F74, 0xA49D8F, 0x7D776C)]

walls = MB(900)
solids = MB(901)


def wall_face(m, a, b, out, foot, top, rng):
    """Coursed stone on a vertical face from a to b (x, z). `out` is the face's
    outward normal (x, z); foot and top are heights at a and at b."""
    (ax, az), (bx, bz) = a, b
    L = math.hypot(bx - ax, bz - az)
    ux, uz = (bx - ax) / L, (bz - az) / L
    if -uz * out[0] + ux * out[1] < 0:  # walk the face the way that makes its quads look out
        (ax, az), (bx, bz), ux, uz = (bx, bz), (ax, az), -ux, -uz
        foot, top = (foot[1], foot[0]), (top[1], top[0])
    nx, nz = out

    def pt(s, y, pro):
        return (ax + ux * s + nx * pro, y, az + uz * s + nz * pro)

    def lo(s):
        return lerp(foot[0], foot[1], s / L)

    def hi(s):
        return lerp(top[0], top[1], s / L)

    m.quad([pt(0, lo(0), 0), pt(L, lo(L), 0), pt(L, hi(L), 0), pt(0, hi(0), 0)], mat=MORTAR, jit=0.03)
    y0 = min(foot)
    while y0 < max(top) - 0.05:
        ch = 0.28 + rng.random() * 0.17
        s = -rng.random() * 0.6
        while s < L:
            sl = 0.45 + rng.random() * 0.75
            s0, s1 = max(0.0, s) + 0.022, min(L, s + sl) - 0.022
            s += sl
            if s1 - s0 < 0.12:
                continue
            b0, b1 = max(y0 + 0.022, lo(s0)), max(y0 + 0.022, lo(s1))
            t0, t1 = min(y0 + ch - 0.022, hi(s0) - 0.03), min(y0 + ch - 0.022, hi(s1) - 0.03)
            if t0 - b0 < 0.06 or t1 - b1 < 0.06:
                continue
            pro = 0.012 + rng.random() * 0.03
            m.quad([pt(s0, b0, pro), pt(s1, b1, pro), pt(s1, t1, pro), pt(s0, t0, pro)], mat=COURSED[int(rng.random() * len(COURSED))], jit=0.06, tint=0.82 + 0.3 * rng.random())
        y0 += ch


def piece(m, p, q, h, depth, mat, tint=1.0):
    """A slab from game point p to q (its top edge's centre line), h thick, depth across."""
    dx, dy, dz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
    m.box((math.hypot(dx, dz), h, depth), at=((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 - h / 2, (p[2] + q[2]) / 2), mat=mat,
          yaw=math.atan2(-dz, dx), roll=math.atan2(dy, math.hypot(dx, dz)), centered=True, bev=0, tint=tint)


def coping(m, a, b, out, top, back, rng, over=0.07, thick=0.16):
    """Coping slabs along a wall's top from a to b, from `back` behind the face to `over` in front."""
    (ax, az), (bx, bz) = a, b
    L = math.hypot(bx - ax, bz - az)
    ux, uz = (bx - ax) / L, (bz - az) / L
    c = (over - back) / 2
    s = 0.0
    while s < L - 0.05:
        sl = min(0.7 + rng.random() * 0.5, L - s)
        p = (ax + ux * s + out[0] * c, lerp(top[0], top[1], s / L), az + uz * s + out[1] * c)
        q = (ax + ux * (s + sl - 0.02) + out[0] * c, lerp(top[0], top[1], (s + sl - 0.02) / L), az + uz * (s + sl - 0.02) + out[1] * c)
        piece(m, p, q, thick, back + over, COPING[int(rng.random() * len(COPING))], tint=0.85 + 0.25 * rng.random())
        s += sl


def solid(a, b, out, foot, top, back):
    """The collision behind a wall face: a box hung from its top edge, deep enough to reach its foot."""
    (ax, az), (bx, bz) = a, b
    h = max(top[0] - foot[0], top[1] - foot[1]) + 0.3
    p = (ax - out[0] * back / 2, top[0], az - out[1] * back / 2)
    q = (bx - out[0] * back / 2, top[1], bz - out[1] * back / 2)
    piece(solids, p, q, h, back, P["tar"])


def retaining(a, b, out, foot, top, back=0.95, rng=vr):
    """A retaining wall: face, coping and collision. foot and top are (at a, at b)."""
    wall_face(walls, a, b, out, foot, top, rng)
    coping(walls, a, b, out, (top[0] + 0.04, top[1] + 0.04), back + 0.1, rng)
    solid(a, b, out, foot, (top[0] + 0.04, top[1] + 0.04), back)


def parapet(a, b, base, rng=vr, h=0.9, w=0.45):
    """A free-standing wall on top of another, faced both sides."""
    (ax, az), (bx, bz) = a, b
    L = math.hypot(bx - ax, bz - az)
    nx, nz = (bz - az) / L, -(bx - ax) / L
    for s in (1, -1):
        o = (nx * s, nz * s)
        wall_face(walls, (ax + o[0] * w / 2, az + o[1] * w / 2), (bx + o[0] * w / 2, bz + o[1] * w / 2), o, (base, base), (base + h, base + h), rng)
    coping(walls, (ax + nx * w / 2, az + nz * w / 2), (bx + nx * w / 2, bz + nz * w / 2), (nx, nz), (base + h + 0.1, base + h + 0.1), w + 0.07, rng, over=0.05, thick=0.12)
    piece(solids, (ax, base + h + 0.1, az), (bx, base + h + 0.1, bz), h + 0.1, w, P["tar"])


# The village's wall over the quay, the square's bastion stepping out of it,
# the ramp's sides turning down from the bastion's front.
FACE_V = -10 + 0.95  # the long runs
FACE_B = RAMP[2] + 0.95  # the bastion's front
BW, BE = -6 - 0.95, 14 + 0.95  # the bastion's sides
FOOT = (LT - 0.3, LT - 0.3)
retaining((-32.5, FACE_V), (BW, FACE_V), (0, 1), FOOT, (VT, VT))
retaining((BE, FACE_V), (30.5, FACE_V), (0, 1), FOOT, (VT, VT))
retaining((BW, FACE_V), (BW, FACE_B), (-1, 0), FOOT, (VT, VT))
retaining((BE, FACE_V), (BE, FACE_B), (1, 0), FOOT, (VT, VT))
retaining((BW, FACE_B), (RAMP[0] - 0.95, FACE_B), (0, 1), FOOT, (VT, VT))
retaining((RAMP[1] + 0.95, FACE_B), (BE, FACE_B), (0, 1), FOOT, (VT, VT))
retaining((RAMP[0] - 0.95, RAMP[2]), (RAMP[0] - 0.95, RAMP[3]), (-1, 0), FOOT, (VT, LT))
retaining((RAMP[1] + 0.95, RAMP[2]), (RAMP[1] + 0.95, RAMP[3]), (1, 0), FOOT, (VT, LT))
# A low parapet round the bastion, seat-high, so the cove stays in view.
for a, b in (((BW + 0.3, FACE_V - 0.6), (BW + 0.3, FACE_B - 0.3)), ((BW + 0.3, FACE_B - 0.3), (RAMP[0] - 0.95, FACE_B - 0.3)),
             ((RAMP[1] + 0.95, FACE_B - 0.3), (BE - 0.3, FACE_B - 0.3)), ((BE - 0.3, FACE_B - 0.3), (BE - 0.3, FACE_V - 0.6))):
    parapet(a, b, VT + 0.04, h=0.5)

# The quay's sea wall, broken by the steps, the slipway and the jetty's steps.
FACE_Q = SLIP[2] + 0.95
BEACH_TOP = profile(FACE_Q) - 0.3
for x0, x1 in ((-32.5, WEST_STEPS[0] - 0.05), (WEST_STEPS[1] + 0.05, SLIP[0] - 0.95), (SLIP[1] + 0.95, JETTY_STEPS[0] - 0.05), (JETTY_STEPS[1] + 0.05, 28.6)):
    retaining((x0, FACE_Q), (x1, FACE_Q), (0, 1), (BEACH_TOP, BEACH_TOP), (LT, LT))
retaining((28.6, FACE_Q), (30.6, 11.2), (0.81, 0.59), (BEACH_TOP, BEACH_TOP + 0.4), (LT, LT))
# The slipway's sides, down to the beach.
for x, out in ((SLIP[0] - 0.95, (-1, 0)), (SLIP[1] + 0.95, (1, 0))):
    retaining((x, SLIP[2] - 0.05), (x, SLIP[3]), out, (profile(SLIP[2]) - 0.3, profile(SLIP[3]) - 0.3), (LT, slip_y(SLIP[3])))
# The steps' sides, cut down into the quay.
for r, fy in ((JETTY_STEPS, jsteps_y), (WEST_STEPS, wsteps_y)):
    for x, out in ((r[0] - 0.05, (1, 0)), (r[1] + 0.05, (-1, 0))):
        retaining((x, r[2]), (x, FACE_Q), out, (fy(r[2]) - 0.1, fy(FACE_Q) - 0.1), (LT, LT))

walls.build("walls", ao=0.5, ao_dist=0.5, grime=0.25, grime_h=0.8, ground=False)
solids.build("COL_walls", ao=0, grime=0, ground=False)


# ------------------------------------------------------------------ paving


COBBLES = [Paint(STONE, c) for c in (0x6F6A61, 0x7B756A, 0x857E72, 0x67625A, 0x8A8376, 0x746B5E)]


def pave(m, x0, x1, z0, z1, y_of, rng, row=(0.42, 0.62), width=(0.5, 0.95), keep=None, gap=0.035, lift=0.03, stones=FLAGS):
    """Stone setts in rows across x, each corner on the ground under it."""
    z = z0
    while z < z1 - 0.1:
        rh = min(row[0] + rng.random() * (row[1] - row[0]), z1 - z)
        x = x0 - rng.random() * width[0]
        while x < x1:
            sw = width[0] + rng.random() * (width[1] - width[0])
            a, b = max(x0, x) + gap, min(x1, x + sw) - gap
            c, d = z + gap, z + rh - gap
            x += sw
            if b - a < 0.15 or (keep and not keep((a + b) / 2, (c + d) / 2)):
                continue
            up = lift + rng.random() * 0.025
            m.quad([(a, y_of(a, c) + up, c), (a, y_of(a, d) + up, d), (b, y_of(b, d) + up, d), (b, y_of(b, c) + up, c)],
                   mat=stones[int(rng.random() * len(stones))], jit=0.06, tint=0.78 + 0.34 * rng.random())
        z += rh


setts = MB(910)
HEARTH = (3.0, -16.0)


def on_square(x, z):
    if math.hypot(x - HEARTH[0], z - HEARTH[1]) < 1.25:
        return False
    # Ragged at the back and the sides, where the turf has crept in.
    edge = min(x - SQUARE[0], SQUARE[1] - x, z - SQUARE[2])
    return edge > 0.6 * (noise2(x * 0.9, z * 0.9, 91) + 0.4)


pave(setts, SQUARE[0], SQUARE[1], SQUARE[2], SQUARE[3], lambda x, z: VT, vr, row=(0.36, 0.52), width=(0.4, 0.75), keep=on_square, gap=0.04, stones=COBBLES)
pave(setts, RAMP[0], RAMP[1], RAMP[2] + 0.1, RAMP[3], lambda x, z: ramp_y(z), vr)
pave(setts, JETTY_STEPS[0], JETTY_STEPS[1], JETTY_STEPS[2], JETTY_STEPS[3] + 0.2, lambda x, z: jsteps_y(z), vr)
pave(setts, WEST_STEPS[0], WEST_STEPS[1], WEST_STEPS[2], WEST_STEPS[3] + 0.2, lambda x, z: wsteps_y(z), vr)
setts.build("setts", ao=0.3, ao_dist=0.3, grime=0.0, ground=False)
# The slipway runs on down the beach under the tide: wet and weedy below high water.
slipway = MB(911)
pave(slipway, SLIP[0], SLIP[1], SLIP[2] - 0.05, 30.0, lambda x, z: H(min(max(x, SLIP[0]), SLIP[1]), z), vr, row=(0.5, 0.7), width=(0.6, 1.1))
slipway.build("slipway", ao=0.3, ao_dist=0.3, grime=0.0, ground=False, tideline=True)

# Kerb stones along the outside of the knoll path.
kerb = MB(912)
s = 0.0
segs = list(zip(KNOLL_PATH[1:], KNOLL_PATH[2:]))
for (ax, az, ay), (bx, bz, by) in segs:
    L = math.hypot(bx - ax, bz - az)
    ux, uz = (bx - ax) / L, (bz - az) / L
    # Outside is away from the knoll's centre.
    nx, nz = uz, -ux
    if nx * (ax - KC[0]) + nz * (az - KC[1]) < 0:
        nx, nz = -nx, -nz
    t = vr.random() * 0.3
    while t < L:
        k = 0.35 + vr.random() * 0.25
        x, z = ax + ux * t + nx * 1.75, az + uz * t + nz * 1.75
        kerb.box((k, 0.14 + vr.random() * 0.1, 0.32), at=(x, H(x, z) - 0.07, z), mat=COPING[int(vr.random() * len(COPING))], yaw=math.atan2(-uz, ux) + (vr.random() - 0.5) * 0.25, bev=0.02, tint=0.85 + 0.25 * vr.random())
        t += k + 0.25 + vr.random() * 0.6
kerb.build("kerb", ao=0.4, ao_dist=0.3, grime=0.2)


# ------------------------------------------------------------------ plots
# (project, ruin, built, x, y, z, yaw, the name board's local (x, z) and turn)

PLOTS = [
    ("forge", "forge_broken", "forge", -9.0, VT, -17.0, math.pi / 2, (0.2, 3.6, 0.0)),
    ("cottage_1", "cottage_a_ruin", "cottage_a", 5.0, VT, -31.0, 0.0, (-1.4, 3.7, 0.15)),
    ("cottage_2", "cottage_b_ruin", "cottage_b", -12.0, VT, -34.0, 0.3, (-1.4, 3.7, 0.15)),
    ("cottage_3", "cottage_c_ruin", "cottage_c", -27.0, VT, -24.0, 1.2, (-1.4, 3.7, 0.15)),
    ("net_loft", "net_loft_ruin", "net_loft", -16.0, LT, 1.0, 0.0, (-2.6, 4.6, 0.2)),
    ("smokehouse", "smokehouse_ruin", "smokehouse", 16.0, LT, 4.0, 0.0, (2.4, 3.6, -0.2)),
    ("jetty", "jetty_ruin", "jetty", 18.0, 2.7, 13.5, 0.0, (-2.7, 1.8, 0.4)),
]
for pid, ruin, done, x, y, z, yaw, (bx, bz, byaw) in PLOTS:
    plot = kit.empty(f"PLOT_{pid}", (x, y, z), yaw=yaw, props={"plot": pid})
    kit.place(HOME, ruin, f"{pid}_ruin", (0, 0, 0), parent=plot)
    kit.place(HOME, done, f"{pid}_built", (0, 0, 0), parent=plot)
    wx, wz = turn(yaw, bx, bz)
    kit.place(T, "plot_board", f"{pid}_board", (bx, H(x + wx, z + wz) - y, bz), yaw=byaw, parent=plot, props={"interact": f"plot:{pid}", "range": 3.2})


def plot_at(pid, lx, lz):
    """A point in front of (or round) a plot, in world x, z."""
    _, _, _, x, _, z, yaw, _ = next(p for p in PLOTS if p[0] == pid)
    dx, dz = turn(yaw, lx, lz)
    return x + dx, z + dz


# ------------------------------------------------------- the lighthouse

place = kit.empty("PLACE_lighthouse", (TOWER[0], KNOLL, TOWER[1]), yaw=TOWER_YAW)
kit.place(HOME, "lighthouse", "lighthouse", (0, 0, 0), parent=place)
MB().cyl(3.85, 3.85, 30.0, segs=16, mat=P["tar"], bev=0).build("COL_lighthouse", parent=place, ao=0, grime=0, ground=False)
door = turn(TOWER_YAW, 0.0, 3.8)
DOOR = (TOWER[0] + door[0], TOWER[1] + door[1])
# The lamp's interaction: the door, as a box the game hides.
MB().box((1.7, 2.7, 0.5), mat=P["tar"], bev=0).build("INT_lamp", loc=(DOOR[0], KNOLL, DOOR[1]), yaw=TOWER_YAW, ao=0, grime=0, ground=False, props={"interact": "lamp", "range": 3.6, "proxy": 1})


# ------------------------------------------------------ hearth and chest

hearth = kit.place(HOME, "hearth", "INT_hearth", (HEARTH[0], VT, HEARTH[1]), yaw=0.0, props={"interact": "hearth", "range": 3.6})
MB().cyl(1.15, 1.15, 0.55, segs=12, mat=P["tar"], bev=0).build("COL_hearth_ring", parent=hearth, ao=0, grime=0, ground=False)
CHEST = (-1.5, -19.8)
chest = kit.place(HOME, "chest", "INT_chest", (CHEST[0], VT, CHEST[1]), yaw=0.25, props={"interact": "storage", "range": 3.6})
MB().box((1.45, 0.86, 0.82), mat=P["tar"], bev=0).build("COL_chest", parent=chest, ao=0, grime=0, ground=False)


# ------------------------------------------------------------- dressing


def home_piece(kind, name, x, z, yaw=0.0, y=None, scale=1.0, props=None):
    return kit.place(HOME, kind, name, (x, H(x, z) if y is None else y, z), yaw=yaw, scale=scale, props=props)


def prop(kind, name, x, z, yaw=None, y=None, scale=1.0, props=None):
    return kit.place(T, kind, name, (x, H(x, z) if y is None else y, z), yaw=vr.random() * TAU if yaw is None else yaw, scale=scale, props=props)


DRESSING = [
    ("well", -4.0, -27.0, 0.3),
    ("garden", 11.0, -41.0, 0.15),
    ("washing_line", -20.0, -41.0, 0.5),
    ("woodpile", -12.3, -16.6, math.pi / 2),
    ("boat_trestles", -5.0, 7.5, 0.25),
    ("net_frame", -28.5, 5.5, 0.45),
]
for k, (kind, x, z, yaw) in enumerate(DRESSING):
    home_piece(kind, f"{kind}_{k}", x, z, yaw)
MEMORIAL = (-43.5, -43.5)
home_piece("memorial", "memorial", MEMORIAL[0], MEMORIAL[1], math.pi / 4, y=H(*MEMORIAL) - 0.05)

# Dry-stone field walls behind the village (4 m runs, stretched to meet).
FIELD_WALLS = [
    [(-34, -47), (-22, -50.5), (-10, -51.5)],
    [(3, -50), (16, -46.5)],
    [(-45.5, -18), (-46.5, -30), (-44.5, -38)],
]
for w, run in enumerate(FIELD_WALLS):
    for i, ((ax, az), (bx, bz)) in enumerate(zip(run, run[1:])):
        L = math.hypot(bx - ax, bz - az)
        n = max(1, round(L / 4))
        for k in range(n):
            t = (k + 0.5) / n
            x, z = lerp(ax, bx, t), lerp(az, bz, t)
            wall = home_piece("wall_run", f"field_wall_{w}_{i}_{k}", x, z, math.atan2(-(bz - az), bx - ax), y=H(x, z) - 0.04)
            wall.scale = (L / n / 4, 1.0, 1.0)

# The knoll's top: a dry-stone wall round its seaward side, a bench looking over the village.
KNOLL_WALL = [(KC[0] + math.cos(math.radians(-160 + k * 24)) * 8.6, KC[1] + math.sin(math.radians(-160 + k * 24)) * 8.6) for k in range(9)]
walls, solids = MB(921), MB(922)  # parapet() draws into these
for a, b in zip(KNOLL_WALL, KNOLL_WALL[1:]):
    parapet(a, b, KNOLL - 0.15, h=0.85)
walls.build("knoll_wall", ao=0.5, ao_dist=0.5, grime=0.25, grime_h=0.6, ground=False)
solids.build("COL_knoll_wall", ao=0, grime=0, ground=False)
BENCH = (KC[0] + math.cos(math.radians(205)) * 8.0, KC[1] + math.sin(math.radians(205)) * 8.0)
kit.place(T, "decor_bench", "knoll_bench", (BENCH[0], KNOLL, BENCH[1]), yaw=facing(math.cos(math.radians(205)), math.sin(math.radians(205))), props={"col": 1})

GORSE = [(27.5, -42.5), (39.5, -40.5), (-46, -21), (-47.5, -33), (-38, -47), (-16, -53), (14, -50.5), (23.5, -35), (36, -17), (41, 8), (37.5, 25), (-44.5, 6),
         (-41.5, 18), (-37.5, 31), (-31, -46), (20, -31), (-33.5, 42), (31, 39), (44, -4), (-47, 10)]
for k, (x, z) in enumerate(GORSE):
    home_piece("gorse", f"gorse_{k}", x, z, vr.random() * TAU, scale=0.85 + vr.random() * 0.5)

# Lamp posts (each lights itself in the game): the square, the ramp's foot,
# the slipway, the jetty steps and halfway up the knoll.
LAMPS = [(-5.2, -10.0, 0.4), (13.4, -10.0, 2.6), (8.6, 2.8, -0.6), (-0.6, 11.8, 3.6), (21.4, 10.0, 2.2), (26.7, -22.3, 1.0)]
for k, (x, z, yaw) in enumerate(LAMPS):
    prop("lantern_post", f"lamp_post_{k}", x, z, yaw=yaw)

ODDS = [
    ("barrel", 20.6, 2.5), ("barrel", 21.4, 3.4), ("cask_small", 20.2, 3.6),
    ("lobster_pot", 11.5, 9.5), ("lobster_pot", 12.4, 10.2), ("lobster_pot", 10.8, 10.8), ("rope_coil", 14.2, 11.4),
    ("plank_pile", -9.5, 10.2), ("cask_small", -1.0, -21.6), ("barrel", -6.4, -21.2), ("barrel", -7.2, -21.9),
    ("rope_coil", -21.0, 8.6), ("lobster_pot", -25.0, 2.6), ("bollard", -12.0, 12.2), ("bollard", 24.5, 12.2), ("bollard", 8.9, 12.3),
]
for k, (kind, x, z) in enumerate(ODDS):
    prop(kind, f"odd_{kind}_{k}", x, z, props={"col": 1} if kind in ("barrel", "bollard") else None)
# The quay at work: pots, crates and casks against the wall and by the sheds, a
# net rack by the loft; on the beach a boat hauled up and an old anchor.
QUAY_GEAR = [
    ("decor_crates", -14.0, -8.0, 0.1), ("decor_barrels", -17.2, -8.2, -0.2), ("lobster_pot", -19.0, -8.4, 0.6), ("decor_crates", 22.0, -8.1, -0.15),
    ("barrel", 24.6, -8.3, 0.0), ("cask_small", 25.4, -7.5, 0.0), ("decor_net_rack", -23.6, 3.8, math.pi / 2), ("lobster_pot", -22.6, 0.4, 0.3),
    ("lobster_pot", -22.2, -0.5, 1.4), ("decor_crates", 10.6, 11.2, 0.35), ("decor_barrels", 23.6, 5.2, 1.2), ("decor_crates", 23.2, 8.4, -0.3),
]
for k, (kind, x, z, yaw) in enumerate(QUAY_GEAR):
    prop(kind, f"quay_{kind}_{k}", x, z, yaw=yaw, y=LT, props={"col": 1})
prop("rowboat", "beach_rowboat", -16.0, 18.5, yaw=1.3, y=H(-16.0, 18.5) - 0.05, props={"col": 1})
prop("anchor", "beach_anchor", -7.5, 20.0, yaw=0.4, y=H(-7.5, 20.0) - 0.15)
for k, (x, z, s) in enumerate(((-29.5, 16.5, 0.8), (26.6, 16.0, 0.9), (-31.0, 21.0, 1.1))):
    home_piece(f"rock_{k + 2}", f"beach_rock_{k}", x, z, vr.random() * TAU, y=H(x, z) - s * 0.35, scale=s, props={"col": 1})

# The keeper's things on the knoll: oil and coal by the tower's back, a flagstaff, the vegetable bed.
for k, (kind, x, z, yaw) in enumerate((("decor_barrels", 37.2, -42.4, 0.5), ("decor_crates", 40.0, -38.6, -0.4), ("decor_planter", 27.6, -39.8, 1.2), ("decor_planter", 28.9, -41.3, 1.2))):
    prop(kind, f"knoll_{kind}_{k}", x, z, yaw=yaw, y=KNOLL, props={"col": 1})
FLAG = (39.2, -33.4)
staff = MB(920)
staff.cyl(0.07, 0.045, 7.5, mat=P["paint_white"], segs=8)
staff.uvsphere(0.1, at=(0, 7.55, 0), mat=P["gilt"], segs=8, rings=5)
staff.prism([(0.0, 0.0), (1.7, -0.3), (0.0, -0.75)], 0.02, at=(0.06, 7.2, 0.0), mat=P["paint_red"], bev=0)
staff.cyl(0.35, 0.4, 0.25, mat=P["stone_dark"], segs=10, bev=0.03)
staff.build("flagstaff", loc=(FLAG[0], KNOLL, FLAG[1]), yaw=0.6, ao=0.4, ao_dist=0.4, props={"col": 1})

prop("signpost", "signpost", 13.8, -11.6, yaw=-0.5)
prop("tide_pole", "tide_pole_slip", 8.6, 27.5, yaw=0.0, y=0.0)
prop("tide_pole", "tide_pole_jetty", 21.6, 31.5, yaw=0.0, y=0.0)
# Wrack along the high-water line.
for k in range(12):
    x = -26 + k * 4.6 + vr.random() * 2
    if SLIP[0] - 1 < x < SLIP[1] + 1 or 15.5 < x < 20.5:
        continue
    z = 26.6 + vr.random() * 1.4
    prop("seaweed", f"wrack_{k}", x, z, scale=0.8 + vr.random() * 0.4)


# ------------------------------------------------------------------ rocks
# The island's cliff foot, the knoll's seaward side and the arms' flanks, from
# home.blend's unit boulders; the cove's own rocks wear the tide on them.

rocks = 0


def boulder(x, z, s, sink=0.4):
    """A boulder bedded in the ground, or out where the coast drops away, a sea
    rock: stood on the sea floor and stretched up clear of high water. Too tall
    to climb onto from the water, and kept back from the cliffs (shrunk if it
    must be) so you can't drop onto one either: never a perch to be stranded on."""
    global rocks
    kind = f"rock_{int(vr.random() * 6)}"
    yaw, w, h = vr.random() * TAU, 0.9 + vr.random() * 0.3, 0.75 + vr.random() * 0.35
    ground = H(x, z)
    if ground > SEA_ROCK:
        home_piece(kind, f"rock_{rocks:03d}", x, z, yaw, y=ground - s * sink, scale=(s * w, s * h, s), props={"col": 1})
        rocks += 1
        return
    # In clusters with open water between, big and small, not a string of beads.
    group = noise2(x * 0.22, z * 0.22, 103)
    if group < -0.15:
        return
    box = HOME[kind].bound_box
    reach = max(max(abs(c[0]) for c in box) * w, max(abs(c[1]) for c in box))
    s = min(max(s, 2.4) * (0.7 + 0.9 * group), (sea_room(x, z) - SEA_ROCK_GAP) / reach)
    if s < 1.4:
        return
    lo, hi = min(c[2] for c in box), max(c[2] for c in box)
    top = HW + 0.5 + 0.6 * (noise2(x * 0.7, z * 0.7, 101) + 1.0)
    tall = (top - ground) / (hi - lo)
    home_piece(kind, f"rock_{rocks:03d}", x, z, yaw, y=ground - lo * tall, scale=(s * w, tall, s), props={"col": 1})
    rocks += 1


def sea_room(x, z):
    """How far it is from (x, z) to the nearest ground above the sea floor (up to 9 m)."""
    for k in range(2, 19):
        r = k * 0.5
        for j in range(16):
            a = j * TAU / 16
            if H(x + math.cos(a) * r, z + math.sin(a) * r) > SEA_ROCK:
                return r
    return 9.0



def rock_ok(x, z):
    """Boulders stay off the village, the quay, the knoll's top and its path, the
    beach and the flats, the shelf and the ledge, the jetty's water, the drift's
    way in and the cliffs."""
    if poly_sd(x, z, VILLAGE)[0] < 2.5 or poly_sd(x, z, QUAY)[0] < 2.5:
        return False
    if math.hypot(x - KC[0], z - KC[1]) < 11.5 or along(x, z, KNOLL_PATH)[0] < 4.0:
        return False
    if poly_sd(x, z, COVE)[0] < 0 and H(x, z) < HW + 0.6 and z < 62:
        return False
    if along(x, z, SHELF)[0] < 3.5 or math.hypot(x - LEDGE[0], z - LEDGE[1]) < 6.0 or (13 < x < 25.5 and 12 < z < 48):
        return False
    # Nor on a cliff face, where its top would be a ledge you could drop onto and never climb off.
    if H(x, z) > SEA_ROCK and slope(x, z) > 1.0:
        return False
    return min(along(x, z, lane)[0] for lane in LANE_LINES) > 4.0


for i in range(len(VILLAGE)):
    if i in VILLAGE_FRONT or i in VILLAGE_INLAND:
        continue
    (ax, az), (bx, bz) = VILLAGE[i], VILLAGE[(i + 1) % len(VILLAGE)]
    L = math.hypot(bx - ax, bz - az)
    nx, nz = -(bz - az) / L, (bx - ax) / L  # outward: the polygon runs clockwise (x right, z up)
    t = vr.random() * 2
    while t < L:
        if vr.random() < 0.65:
            off = 4.2 + vr.random() * 2.2
            x, z = ax + (bx - ax) * t / L + nx * off, az + (bz - az) * t / L + nz * off
            if rock_ok(x, z):
                boulder(x, z, 1.6 + vr.random() * 2.2)
        t += 2.6 + vr.random() * 1.2
for k in range(30):
    a = math.radians(170 + k * 8 + vr.random() * 4)
    r = 17.0 + vr.random() * 2.5
    x, z = KC[0] + math.cos(a) * r, KC[1] + math.sin(a) * r
    if vr.random() < 0.75 and rock_ok(x, z):
        boulder(x, z, 1.8 + vr.random() * 2.4)
for spine, inner in ((WEST_ARM, 1), (EAST_ARM, -1)):
    for (ax, az, _), (bx, bz, _) in zip(spine, spine[1:]):
        L = math.hypot(bx - ax, bz - az)
        nx, nz = (bz - az) / L, -(bx - ax) / L  # +x side of a southward spine is east
        t = vr.random() * 2
        while t < L:
            for side in (1, -1):
                off = 9.5 + vr.random() * 2.5
                x, z = ax + (bx - ax) * t / L + nx * off * side, az + (bz - az) * t / L + nz * off * side
                if vr.random() < 0.55 and rock_ok(x, z):
                    boulder(x, z, 1.4 + vr.random() * 2.0)
            t += 3.4 + vr.random() * 1.4
# Boulders set into the knoll path's cut bank, uphill of the path.
for k, (px, pz, _) in enumerate(KNOLL_PATH[2:6]):
    ix, iz = KC[0] - px, KC[1] - pz
    d = math.hypot(ix, iz)
    for j in range(2):
        along_off = (j - 0.5) * 2.2
        x = px + ix / d * 3.1 + iz / d * along_off
        z = pz + iz / d * 3.1 - ix / d * along_off
        boulder(x, z, 1.1 + vr.random() * 0.6, sink=0.55)
# Crags on the arms' crowns, and stacks off the point and the hook's end.
for tx, tz, sz in TORS:
    for k in range(3 + int(vr.random() * 2)):
        a, r = vr.random() * TAU, vr.random() * 1.4 * sz
        boulder(tx + math.cos(a) * r, tz + math.sin(a) * r, (1.3 + vr.random() * 0.9) * sz, sink=0.3)
for k, (x, z, sz) in enumerate(STACKS):
    stack = MB(970 + k)
    y, r = H(x, z), sz * 1.5
    for j in range(4):
        stack.rock(r, at=(vr.uniform(-0.3, 0.3) * sz, y - r * 0.2, vr.uniform(-0.3, 0.3) * sz), mat=P["rock_dark"] if j % 2 else P["rock"], seed=975 + k * 7 + j, squash=0.8, cuts=6)
        y += r * 1.2
        r *= 0.78
        if y > 2.6 + sz:
            break
    stack.build(f"rock_stack_{k}", loc=(x, 0.0, z), tideline=True, props={"col": 1})
for k, (x, z) in enumerate(((-17, 31), (-11, 42.5), (-2, 36), (6, 40), (-22, 40), (-5, 46.5), (10, 33), (-14, 51))):
    prop("seaweed", f"flats_weed_{k}", x, z, scale=0.9 + vr.random() * 0.5)
prop("hull_ribs", "flats_ribs", -24.0, 45.0, yaw=0.9)
# Barnacled rocks on the flats under the arms and in the mouth.
for k, (x, z, r) in enumerate([(-29, 44, 1.1), (-25, 49, 0.8), (-20, 54, 1.1), (-15, 58.5, 0.9), (-33.5, 40.5, 0.7),
                               (25.5, 47, 1.0), (23, 52, 0.8), (19.5, 56.5, 1.2), (-11, 61, 0.7)]):
    MB(950 + k).rock(r, mat=P["rock"] if k % 3 else P["rock_dark"], seed=960 + k, squash=0.6).build(f"rock_tide_{k:02d}", loc=(x, H(x, z) - r * 0.35, z), tideline=True, props={"col": 1})


# ------------------------------------------------------------ the cove's work

# The wreck field (low tide) and the fishing.
WRECKS = [("sunken_boat", "wreck_boat", -9.0, 39.0, 0.6), ("boiler", "wreck_boiler", 3.0, 43.0, -0.4),
          ("old_pilings", "wreck_pilings", -19.0, 35.0, 0.2), ("old_pilings", "wreck_pilings", -14.0, 46.0, 1.4)]
count = {}
for node, model, x, z, yaw in WRECKS:
    i = count.get(node, 0)
    count[node] = i + 1
    kit.place(T, model, f"NODE_{node}_{i:02d}", (x, H(x, z), z), yaw=yaw, props={"node": node})
kit.empty("NODE_fish_silverfin_00", (POOL[0], 0.0, POOL[1]), props={"node": "fish_silverfin"})
kit.empty("NODE_fish_glowgill_00", (18.0, 0.0, 43.5), props={"node": "fish_glowgill"})

for lane, pts in enumerate(LANES):
    for k, (x, z) in enumerate(pts):
        kit.empty(f"FX_drift_{lane}_{k}", (x, 0.0, z))
# Where what the tide left lies when you come home.
for k, (x, z) in enumerate(STRAND):
    kit.empty(f"FX_strand_{k}", (x, H(x, z), z))

# The boat, moored at the jetty's head once it stands, and a second at stage 2.
kit.place(HOME, "sailboat", "BUOY_boat", (22.6, 0.0, 37.0), yaw=0.0, props={"interact": "boat", "range": 6.0, "float": 0.0, "min": -0.6, "max": 2.5})
kit.place(HOME, "sailboat", "BUOY_boat_2", (20.9, 0.0, 28.6), yaw=0.08, props={"float": 0.0, "min": 1.35, "max": 2.5})


# ------------------------------------------------------------------ people

SPAWN = (DOOR[0] - 0.832 * 2.6, DOOR[1] + 0.555 * 2.6)
kit.empty("SPAWN_start", (SPAWN[0], KNOLL, SPAWN[1]), yaw=look(-SPAWN[0], 64.0 - SPAWN[1]))
kit.empty("SPAWN_landing", (12.0, H(12.0, 17.0), 17.0), yaw=look(0, -1))
kit.empty("SPAWN_jetty", (18.0, 2.7, 36.5), yaw=look(0, -1))
MAREN = (SPAWN[0] + 0.45, SPAWN[1] + 3.17)
NPCS = {
    "maren": (MAREN, facing(SPAWN[0] - MAREN[0], SPAWN[1] - MAREN[1])),
    "odile": ((5.6, -14.0), facing(HEARTH[0] - 5.6, HEARTH[1] + 14.0)),
    "hesk": ((-5.0, -19.6), facing(-9.0 + 5.0, -17.0 + 19.6)),
    "tib": ((19.6, 16.8), facing(-1, -1)),
}
for npc, ((x, z), yaw) in NPCS.items():
    kit.empty(f"NPC_{npc}", (x, H(x, z), z), yaw=yaw)
# Families at their doors, once their cottages stand (cottage_2, cottage_3).
for fam, pid in enumerate(("cottage_2", "cottage_3")):
    door_x, door_z = plot_at(pid, 0.0, 2.5)
    for i, (lx, lz) in enumerate(((-1.2, 2.0), (0.0, 2.9), (1.1, 1.6))):
        x, z = plot_at(pid, lx, 2.5 + lz)
        kit.empty(f"PLACE_family_{fam}_{i}", (x, VT, z), yaw=facing(door_x - x, door_z - z) + math.pi)

# Where the anti-trap current carries a swimmer: all above high water.
ANCHORS = {"beach_w": (-18, 17), "beach_e": (12, 16), "quay": (4, 9), "ledge": (-29.5, 33.5), "arm_w": (-38.5, 26), "arm_w_tip": (-27.5, 50),
           "arm_e": (36.5, 28), "arm_e_tip": (28, 48), "square": (4, -13), "knoll": (28, -37)}
for name, (x, z) in ANCHORS.items():
    kit.empty(f"ANCHOR_{name}", (x, H(x, z) + 0.1, z))

# Gulls: perches (the game stands each on whatever's drawn under it) and the flock's centre.
PERCHES = [(x, H(x, z) + 2.7, z) for x, z, _ in LAMPS] + [
    (MEMORIAL[0], H(*MEMORIAL) + 2.3, MEMORIAL[1]), (-22, H(-22, -50.5) + 1.3, -50.5), (-46.5, H(-46.5, -30) + 1.3, -30),
    (-5, LT + 2.0, 7.5), (-12, LT + 0.9, 12.2), (24.5, LT + 0.9, 12.2), (-9.0, VT + 1.2, -7.4), (11.0, VT + 1.2, -7.4),
]
for k, p in enumerate(PERCHES):
    kit.empty(f"FX_perch_{k}", p)
kit.empty("FX_gulls", (12.0, 0.0, 18.0))


# ------------------------------------------------------------ decorating

DECOR_BOUNDS = [(-45, -9), (-49, -26), (-46, -40), (-38, -48), (-22, -52), (-6, -53), (8, -51), (18, -47), (24, -41), (27, -42),
                (33, -44.5), (40, -41), (42.5, -34), (39.5, -27.5), (34, -25), (31, -20), (32, -10), (30, 5), (27, 12.5), (24, 14),
                (24, 24), (-27, 24), (-31, 14), (-34, 10), (-34, -7), (-40, -8)]
for k, (x, z) in enumerate(DECOR_BOUNDS):
    kit.empty(f"FX_decor_{k}", (x, 0.0, z))

CLEAR = [
    # plots
    (-8.5, -16.6, 4.6), (5.0, -31.0, 5.0), (-12.0, -34.0, 5.0), (-27.0, -24.0, 5.0), (-16.0, 1.0, 6.0), (16.0, 4.0, 4.8), (18.0, 15.0, 2.8), (18.0, 20.0, 2.8),
    # the hearth, the chest, the lighthouse and its door, where you wake
    (HEARTH[0], HEARTH[1], 3.0), (CHEST[0], CHEST[1], 1.6), (TOWER[0], TOWER[1], 5.8), (DOOR[0], DOOR[1], 2.0), (SPAWN[0], SPAWN[1], 1.6),
    # the ramp, the slipway, the steps
    (4.0, -7.0, 3.4), (4.0, -3.0, 3.4), (4.0, 1.0, 3.4), (4.0, 4.0, 3.0), (4.0, 11.5, 3.2), (4.0, 15.0, 3.2),
    (18.0, 9.5, 2.5), (18.0, 12.5, 2.5), (-24.5, 9.5, 2.2), (-24.5, 12.5, 2.2),
    # the dressing
    (-4.0, -27.0, 1.9), (11.0, -41.0, 3.4), (-20.0, -41.0, 3.0), (-12.3, -16.6, 1.6), (-5.0, 7.5, 3.0), (-28.5, 5.5, 2.4), (MEMORIAL[0], MEMORIAL[1], 1.8), (13.8, -11.6, 0.8), (BENCH[0], BENCH[1], 1.4),
] + [(x, z, 2.2) for x, z, _ in KNOLL_PATH] + [(x, z, 0.8) for x, z, _ in LAMPS] + [(p[0][0], p[0][1], 1.2) for p in NPCS.values()] + [
    (x, z, 1.2) for _, x, z, _ in QUAY_GEAR] + [(-16.0, 18.5, 2.4), (-7.5, 20.0, 1.2), (FLAG[0], FLAG[1], 0.8), (37.2, -42.4, 1.2), (40.0, -38.6, 1.2), (28.2, -40.5, 1.6)]
for k, (x, z, r) in enumerate(CLEAR):
    kit.empty(f"CLEAR_{k:02d}", (x, H(x, z), z), props={"radius": r})


# ------------------------------------------------------------------- grass
# One triangle per tuft: where it grows, a corner out along its turn (0.1 m
# per unit of scale) and a corner 0.1 m straight above the first, so the game
# can tell them apart whatever order they arrive in. It instances the dune
# grass prop on them.

WALL_LINES = [[(x, z, 0.0) for x, z in run] for run in FIELD_WALLS + [KNOLL_WALL]]
grass = MB(990)
tufts = 0
x = -60.0
while x < 56:
    z = -66.0
    while z < 60:
        gx, gz = x + vr.random() * 1.6, z + vr.random() * 1.6
        z += 1.7
        y = H(gx, gz)
        if y < 3.0 or y <= seabed(gx, gz) + 0.02 or built(gx, gz):
            continue
        sl = slope(round(gx), round(gz))
        if sl > 0.45 or wear(gx, gz) > 0.2 or along(gx, gz, SHELF)[0] < 2.5:
            continue
        if any(math.hypot(gx - cx, gz - cz) < cr for cx, cz, cr in CLEAR) or any(along(gx, gz, w)[0] < 0.9 for w in WALL_LINES):
            continue
        edge = smoothstep(0.15, 0.45, sl)
        if vr.random() > 0.3 + 0.5 * edge + 0.2 * (fbm3(gx * 0.1, 0.0, gz * 0.1, 99) + 0.5):
            continue
        sc = 0.35 + vr.random() * 0.3 + edge * 0.4
        a = vr.random() * TAU
        grass.quad([(gx, y, gz), (gx + math.cos(a) * 0.1 * sc, y, gz + math.sin(a) * 0.1 * sc), (gx, y + 0.1, gz)], mat=P["grass"])
        tufts += 1
    x += 1.7
print(f"[home_map] {tufts} grass tufts, {rocks} boulders")
grass.build("SCATTER_grass", ao=0, grime=0, ground=False)

kit.merge_materials()
kit.save_and_export("art/blender/locations/home.blend", "public/assets/models/locations/home.glb")
