"""Builds art/blender/locations/beacon.blend and public/assets/models/locations/beacon.glb.

Saltmere Beacon, the chapter finale, per docs/LEVELS.md (game space, metres;
water at y 0 at low tide and 1.8 at high tide):

  stack       a broken sea stack north of the arena, layered rock rising to a
              summit about y 17 behind and west of the tower, sheer to deep
              water on the west, north and east. The tower stands on a shoulder
              cut into its south face (the platform, y 7), walled into the rock
  stair       steps up a stone-faced cleft in the stack's south face, from the
              arena's north edge to the platform; rubble
              (STATE_guardian_defeated_off) blocks its foot until the Guardian
              falls. Nothing else climbs the stack
  arena       the old landing stage round the brass compass rose, y 3,
              walkable out to 15 m from FX_arena: the stack's foot on the north,
              rocks rising on the west, a broken sea wall over deep water on the
              south, the gate on the east. Two roofless store sheds, a fallen
              crane and a stack of dressed blocks are the cover; bollards and
              broken lamp posts stand round the rim. The Wreck Guardian rises
              from the sea to the south, framed by a sea arch beyond it
  breakwater  a mole of dressed blocks on a rubble mound and a chain of
              skerries, its walk at y 2.8 (it never floods), from the landing to
              the gate; a broken parapet on its weather (north) side, a Spitter
              on a skerry either side
  landing     a rock headland to the east with a gut cut into it from the sea,
              the boat afloat in it at any tide: a quay with landing steps,
              bollards, a crane and lamp posts, a roofless boathouse and its
              slip at the gut's head

Only the water round the rock changes with the tide: low water bares ledges,
skerries and weed; the arena, the breakwater and the quay never flood. What
you collide with is the terrain, plain COL_ shapes and the walls' own boxes.

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
from kit import B, MB, Paint, along, facing, fbm3, lerp, look, mix, noise2, poly_sd, smoothstep  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402

kit.reset()

TEMPLATES = kit.load_props()
HOME = kit.load_home()
P = kit.palette()
FIRE = kit.material("brazier_fire", 0xFFB347, emit=0xFF8A2A, strength=4.0)
# `rnd` lays out the level and `vr` dresses it.
rnd = random.Random(31)
vr = random.Random(131)

STONE = P["stone"]
STONE_DARK = P["stone_dark"]
ROCK, ROCK_DARK = P["rock"], P["rock_dark"]
IRON, RUST, TIMBER, KELP = P["iron"], P["rust"], P["timber"], P["kelp_dark"]
RED = Paint(P["paint_red"].mat, 0xA03A2E)
NIGHT = Paint(P["glass_white"].mat, 0x26343C)
CHAR = Paint(P["timber"].mat, 0x2E2924)
SETTS = [Paint(P["stone"].mat, c) for c in (0x8A857B, 0x7E796F, 0x938D82, 0x767167, 0x878172)]
FLAGS = [Paint(P["stone"].mat, c) for c in (0x9C978B, 0x8F8A7F, 0xA39D90, 0x878275, 0x7E8072, 0x969182, 0x8A8C7A)]

HW = kit.HIGH_WATER
SEA = -5.0  # the sea floor off the rock: swimming depth at any tide
ARENA_Y = 3.0
PLATFORM_Y = 7.0
WALK_Y = 2.8  # the breakwater's walk
TOWER_Z = -32.5
# The arena gate's footing: a plinth from the arena's edge out under the arch, its
# sill the floor you walk through on (the rock falls away steeply there).
GATE_X0, GATE_X1, GATE_HALF = 14.7, 16.9, 4.1
SILL_Y = ARENA_Y + 0.06
STAIR_FOOT = (0.0, ARENA_Y, -14.4)
STAIR_TOP = (0.0, PLATFORM_Y, -27.0)
STAIR_HALF = 1.5


# ------------------------------------------------------------------ terrain
# Off the rock the sea floor is swimming depth even at low water, so a fall off
# any edge ends with the current bringing you in (the tide sweep, GDD section 6).
# The grid lies on the half metres, so the walls cut into the rock (the stair's
# cleft, the platform, the quay) stand on its lines: each has the low ground at
# its face and the rock's rise hidden behind it.

BENCH = 8.4  # the stack's shoulder either side of the cleft: out of reach of the stair and the platform
WALL_N = 9.4  # the platform's back wall, and the rock no higher just behind it
SUMMIT, KNOB = (-12.5, -47.0), (10.5, -48.5)  # the stack's top (about y 17) and its lower east top
# The stack's cliff line: west along the arena's north edge from the cleft, round
# the west, north and east sides, down the platform's sea edge and back along the
# arena's edge to the cleft.
STACK = [(-2.5, -15.3), (-6.0, -14.6), (-9.5, -13.0), (-12.6, -10.4), (-15.8, -12.0), (-19.5, -15.5), (-23.0, -21.0), (-25.0, -28.0),
         (-25.5, -36.0), (-24.0, -44.0), (-21.0, -51.0), (-15.0, -56.5), (-7.0, -58.5), (2.0, -57.5), (9.5, -55.5), (14.5, -51.0),
         (15.5, -45.0), (13.0, -40.5), (8.0, -39.0), (8.0, -26.0), (8.5, -21.0), (10.0, -17.0), (12.0, -14.6), (9.0, -14.2),
         (6.0, -14.8), (2.5, -15.3)]
# Its faces over the arena and the platform's sea edge stay where they're put; the rest weathers.
STACK_SET = {0, 1, 2, 3, 18, 19, 21, 22, 23, 24, 25}
# The rocks along the arena's west side: (x, z, crest y).
SPUR = [(-13.4, -9.8, 4.9), (-15.9, -4.8, 5.5), (-17.0, 1.0, 5.2), (-16.3, 6.5, 4.6), (-14.4, 10.2, 3.8)]
# The old landing stage's sea wall stands on three stretches of its south rim
# (bearings from the compass rose in degrees: east 0, south 90).
SEAWALL = [(50.0, 77.0), (87.0, 113.0), (123.0, 138.0)]
# The landing's headland; the gut cut into it from the east (the quay's face on
# its north side, rock on its south side, the slip at its head).
LAND = [(39.0, -4.5), (40.5, -9.5), (44.5, -13.0), (50.5, -14.0), (56.5, -12.0), (60.0, -7.5), (61.5, -1.5), (61.5, 3.5),
        (62.0, 9.0), (59.5, 13.5), (53.5, 15.5), (46.5, 15.0), (41.5, 12.5), (39.0, 7.0), (38.5, 2.5)]
GUT_N, GUT_S, GUT_X = 3.5, 8.9, 46.0
SLIP_X1, SLIP_Y1 = 52.0, -1.2  # the slip runs from the boathouse (x 46, y 3) down into the gut
# Skerries: (x, z, top, radius). A chain along the breakwater, a few more out in the sound.
SKERRIES = [(19.5, -5.2, 0.9, 3.0), (23.5, 5.0, 0.5, 2.6), (29.2, -5.4, 1.2, 3.2), (33.8, 5.2, 0.6, 2.8), (34.2, -6.2, 0.9, 2.6),
            (21.5, 11.5, 1.3, 2.8), (44.0, 22.0, 1.5, 3.2), (14.0, -21.5, 0.9, 3.0), (37.0, -16.0, 1.1, 2.6)]
SPITTER_ROCKS = [(27.0, -8.5), (33.0, 8.5)]  # flat-topped at y 3.4, the Spitters' perches


def strata(h, step=0.55):
    """Rock that breaks in ledges: each `step` of height a flat, then a short rise."""
    k = math.floor(h / step)
    return (k + smoothstep(0.55, 1.0, h / step - k)) * step


def stair_y(z):
    t = (STAIR_FOOT[2] - z) / (STAIR_FOOT[2] - STAIR_TOP[2])
    return ARENA_Y + (PLATFORM_Y - ARENA_Y) * max(0.0, min(1.0, t))


def slip_y(x):
    return ARENA_Y + (SLIP_Y1 - ARENA_Y) * (x - GUT_X) / (SLIP_X1 - GUT_X)


def bearing(x, z):
    return math.degrees(math.atan2(z, x)) % 360.0


def stage_r(b):
    """How far the landing stage reaches from the compass rose at bearing b."""
    a = math.radians(b)
    r = 15.9 + 0.55 * noise2(math.cos(a) * 3.0, math.sin(a) * 3.0, 5) + 0.35 * noise2(math.cos(a) * 7.0, math.sin(a) * 7.0, 6)
    return lerp(15.0, r, smoothstep(14.0, 24.0, min(b, 360.0 - b)))  # under the gate's footing


def walled(b):
    """1 where the sea wall stands on the stage's rim."""
    return max(smoothstep(b0 - 1.5, b0 + 1.5, b) * (1.0 - smoothstep(b1 - 1.5, b1 + 1.5, b)) for b0, b1 in SEAWALL)


def ledge(x, z, d, seed):
    """Here and there a shelf of rock at a cliff's foot (d metres out), bared at
    low water. It slopes gently off into swimming depth before the drop, so
    wherever the ebb leaves you on it you can walk off it into the sea. Only
    under cliffs you can't climb down: dropped onto from walkable rock, a shelf
    and the cliff's ragged foot can make a pocket you can't walk out of."""
    n = fbm3(x * 0.08, 0.0, z * 0.08, seed)
    if n < 0.0:
        return -99.0
    w = 3.0 + 4.0 * n
    y = lerp(0.3 + 0.7 * n + 0.1 * noise2(x * 0.9, z * 0.9, seed + 1), -1.5, min(1.0, d / w))
    return y - (-1.5 - SEA) * smoothstep(w, w + 1.5, d)


def floor(x, z):
    """The sea floor, and the rubble mound the breakwater stands on."""
    y = SEA + 0.6 * fbm3(x * 0.05, 0.0, z * 0.05, 9)
    k = smoothstep(14.0, 17.0, x) * (1.0 - smoothstep(39.0, 42.0, x))
    if k > 0:
        mound = -2.5 + 0.3 * noise2(x * 0.7, z * 0.7, 13) - 2.5 * smoothstep(3.0, 6.5, abs(z) + 0.8 * fbm3(x * 0.2, 0.0, z * 0.2, 14))
        y = max(y, lerp(y, mound, k))
    return y


def stage(x, z):
    """The old landing stage: flat round the compass rose, worn rock at its rim
    rolling off into the sea, or a sheer drop under the sea wall."""
    b = bearing(x, z)
    d = math.hypot(x, z) - stage_r(b)
    if d > 4.0:
        return -99.0
    w = walled(b)
    top = ARENA_Y + 0.02 * noise2(x * 2.0, z * 2.0, 3)
    top += (1.0 - w) * smoothstep(-2.5, 0.0, d) * (0.14 * fbm3(x * 0.6, 0.0, z * 0.6, 7) - 0.2)
    # Under the wall the rock drops away behind its face, hidden by it.
    d += w * 0.9 + (1.0 - w) * 0.7 * fbm3(x * 0.3, 0.0, z * 0.3, 8)
    return top - (top - SEA) * smoothstep(0.0, lerp(2.6, 1.5, w), d)


def stack(x, z):
    d, edge = poly_sd(x, z, STACK)
    crisp = edge in STACK_SET
    if not crisp:
        d += 1.0 * fbm3(x * 0.12, 0.0, z * 0.12, 15)
    if d > 8.0:
        return -99.0
    rs = math.hypot(x - SUMMIT[0], z - SUMMIT[1]) + 2.5 * fbm3(x * 0.09, 0.0, z * 0.09, 16)
    rk = math.hypot(x - KNOB[0], z - KNOB[1]) + 1.5 * fbm3(x * 0.15, 0.0, z * 0.15, 17)
    # Level along the cleft's edges, where its walls meet the rock.
    rough = smoothstep(2.6, 5.0, abs(x)) if z > -27.0 else 1.0
    top = BENCH + (0.45 + 0.7 * smoothstep(-21.0, -16.0, z)) * fbm3(x * 0.22, 0.0, z * 0.22, 18) * rough
    top += strata(9.0 * smoothstep(10.5, 5.0, rs), 0.65) + strata(3.6 * smoothstep(7.0, 3.0, rk), 0.6)
    if d <= 0:
        return top
    if crisp:
        return top - (top - SEA) * smoothstep(0.0, 1.0, d)
    # Elsewhere it comes down to the sea in tall ledges, none of them a step you could climb.
    return max(top - strata((top - SEA) * smoothstep(0.0, 2.4, d), 1.3), ledge(x, z, d, 21))


def spur(x, z):
    """A ridge of rock along the arena's west side: ledges you can climb on the
    arena's side, a cliff to the sea on the other."""
    d, cy, t = along(x, z, SPUR)
    if d > 7.0:
        return -99.0
    i = min(int(t), len(SPUR) - 2)
    (ax, az, _), (bx, bz, _) = SPUR[i], SPUR[i + 1]
    inside = ((x - ax) * (bz - az) - (z - az) * (bx - ax)) / math.hypot(bx - ax, bz - az)  # > 0 on the arena's side
    cy += 0.25 * fbm3(x * 0.4, 0.0, z * 0.4, 19)
    over = max(0.0, d - 1.4 - 0.6 * fbm3(x * 0.3, 0.0, z * 0.3, 20))
    if inside > 0:
        return cy - strata(over * 0.8, 0.45)
    return cy - (cy - SEA) * smoothstep(0.0, 2.0, over)


def rect_dist(x, z, x0, x1, z0, z1):
    return math.hypot(max(x0 - x, 0.0, x - x1), max(z0 - z, 0.0, z - z1))


def worked(x, z):
    """How far it is to the quay, the way up from the breakwater or the boathouse."""
    return min(rect_dist(x, z, 38.0, 47.0, -2.2, 2.2), rect_dist(x, z, 45.5, 61.0, -1.0, GUT_N), rect_dist(x, z, 40.0, 46.6, GUT_N - 0.5, GUT_S + 0.5))


def land(x, z):
    """The landing's headland: level rock where the quay is, rough on its south arm."""
    d, _ = poly_sd(x, z, LAND)
    d += 0.9 * fbm3(x * 0.12, 0.0, z * 0.12, 31) * smoothstep(41.0, 44.0, x)  # the mole comes ashore on its west end
    if d > 8.0:
        return -99.0
    arm = smoothstep(GUT_S - 0.5, GUT_S + 3.0, z)
    top = ARENA_Y + 0.03 * noise2(x * 1.6, z * 1.6, 32)
    top += strata(1.3 * max(0.0, fbm3(x * 0.15, 0.0, z * 0.15, 37) + 0.25), 0.3) * smoothstep(1.0, 4.0, worked(x, z))
    top = lerp(top, 2.5 + strata(1.4 * (0.5 + 0.5 * fbm3(x * 0.2, 0.0, z * 0.2, 33)), 0.35) - 0.05 * max(0.0, x - 52.0), arm)
    if d <= 0:
        return top
    return top - (top - SEA) * smoothstep(0.0, 2.0, d)


def skerries(x, z):
    y = -99.0
    for sx, sz, top, r in SKERRIES:
        d = math.hypot(x - sx, z - sz) + 0.9 * fbm3(x * 0.3, 0.0, z * 0.3, 41)
        if d < r * 1.4:
            t = top + 0.3 * noise2(x * 0.9, z * 0.9, 42)
            k = smoothstep(0.3 * r, r * 1.3, d)
            y = max(y, t - (t - SEA) * k + 0.3 * fbm3(x * 0.8, 0.0, z * 0.8, 45) * (1.0 - k))
    for sx, sz in SPITTER_ROCKS:
        d = math.hypot(x - sx, z - sz) + 0.5 * fbm3(x * 0.4, 0.0, z * 0.4, 43)
        if d < 7.0:
            # A flat cap, craggy sides down to a ledge bared at low water, sloping off into the deep.
            cap = 3.4 + 0.03 * noise2(x * 2.0, z * 2.0, 44)
            y = max(y, cap - strata((cap - 0.9) * smoothstep(1.9, 2.7, d), 0.5) - 2.4 * min(1.0, max(0.0, d - 2.7) / 2.8) - (-1.5 - SEA) * smoothstep(5.5, 7.0, d))
    return y


def cut(x, z, y):
    """The stair's cleft and the platform, cut into the stack; the gut and its slip."""
    if abs(x) < 2.0 and -27.0 < z < -14.0:
        y = min(y, stair_y(z) - 0.7)
    if -9.0 < x < 8.0 and -39.0 < z < -26.0:
        y = min(y, PLATFORM_Y)
    # A metre behind the platform's walls the rock comes no higher than their tops.
    if -10.0 < x < 8.0 and -40.0 < z < -26.0 and (z <= -39.0 or x <= -9.0):
        y = min(y, WALL_N if z <= -39.0 else BENCH)
    if -10.0 < x < 8.0 and -26.0 <= z < -25.0:
        y = min(y, BENCH)
    # Swimming depth along both faces of the breakwater, so a fall off it ends in the sea.
    if GATE_X1 - 0.5 < x < 40.0 and abs(z) < 3.9:
        y = min(y, -1.4 + 0.1 * noise2(x * 0.9, z * 0.9, 38))
    if x > GUT_X - 1.0 and GUT_N - 1.0 < z < GUT_S + 4.0:
        floor_y = -2.4 - 0.2 * smoothstep(52.0, 64.0, x) + 0.1 * noise2(x * 0.8, z * 0.8, 35)
        k = smoothstep(GUT_N - 1.0, GUT_N, z) * (1.0 - smoothstep(GUT_S - 0.6, GUT_S + 1.6 + 0.8 * fbm3(x * 0.3, 0.0, z * 0.3, 36), z))
        k *= smoothstep(GUT_X - 0.5, GUT_X + 0.5, x)
        y = min(y, lerp(y, floor_y, k))
    return y


_heights = {}


def H(x, z):
    key = (round(x, 3), round(z, 3))
    y = _heights.get(key)
    if y is None:
        y = max(floor(x, z), stage(x, z), stack(x, z), spur(x, z), land(x, z), skerries(x, z))
        y = _heights[key] = cut(x, z, y)
    return y


def grade(x, z):
    return math.hypot(H(x + 1, z) - H(x - 1, z), H(x, z + 1) - H(x, z - 1)) / 2


def color(x, z, y):
    n = fbm3(x * 0.13, 0.0, z * 0.13, 61)
    f = fbm3(x * 0.7, 0.0, z * 0.7, 62)
    steep = smoothstep(0.6, 1.3, grade(x, z) + 0.15 * f)
    if y < -1.2:
        return mix(0x242C28, 0x323C33, 0.5 + 0.5 * n)  # the sea floor
    # Dark layered rock, banded up the faces; lichen on the dry tops, the gulls' lime on the stack's.
    band = 0.5 + 0.5 * math.sin(y * 4.6 + 1.7 * n)
    rock = mix(mix(0x5C5A53, 0x78746A, 0.5 + 0.6 * n), mix(0x3F3E3A, 0x55534D, 0.5 + 0.6 * n), band * 0.7)
    rock = mix(rock, 0x9F9560, smoothstep(0.3, 0.6, f) * 0.35 * smoothstep(HW + 0.8, HW + 1.6, y))
    rock = mix(rock, 0xCFCCC0, smoothstep(0.45, 0.8, f) * 0.55 * smoothstep(7.5, 9.5, y))
    # Barnacles in a pale band under the high-water line, weed below it.
    rock = mix(rock, mix(0x77726A, 0x8A857A, 0.5 + 0.5 * f), smoothstep(HW + 0.3, HW - 0.2, y) * smoothstep(0.3, 1.0, y) * 0.6)
    rock = mix(rock, mix(0x2F3A2A, 0x445138, 0.5 + 0.5 * n), smoothstep(0.8, 0.0, y) * 0.85)
    if abs(y - ARENA_Y) < 0.25 and math.hypot(x, z) < 15.5:
        # The stage: the old paving's bed, worn smooth.
        bed = mix(mix(0x6F6C64, 0x827D72, 0.5 + 0.5 * f), 0x59603F, smoothstep(0.35, 0.7, f) * 0.35)
        return mix(bed, rock, smoothstep(0.1, 0.6, n) * 0.5)
    if y > BENCH - 0.6 and steep < 0.6 and n > 0.0:
        # Patches of thin turf and thrift on the stack's top, the rock through them.
        turf = mix(mix(0x4F5C3C, 0x6A7048, 0.5 + 0.6 * n), 0x8C6F78, smoothstep(0.55, 0.75, f) * 0.5)
        return mix(turf, rock, max(steep, smoothstep(0.1, 0.55, f + 0.4 * (0.2 - n))))
    if 2.4 < y < 3.8 and x > 36.0 and steep < 0.6:
        # Salt-burnt grass in the landing's hollows.
        return mix(rock, mix(0x5E6440, 0x76744C, 0.5 + 0.5 * f), smoothstep(0.0, 0.5, n) * 0.5)
    return rock


ground = kit.material("TIDE_rock", 0xFFFFFF, rough=0.95, vcol=True)
kit.terrain("terrain", -55.5, 75.5, -62.5, 46.5, 1.0, H, color, ground, props={"col": 1})


def prop(kind, name, x, z, y=None, yaw=None, props=None, scale=1.0, parent=None):
    """A layout prop: a random turn (yaw None) comes from `rnd`."""
    return kit.place(TEMPLATES, kind, name, (x, H(x, z) if y is None else y, z), yaw=rnd.random() * math.tau if yaw is None else yaw, props=props, scale=scale, parent=parent)


def dress(kind, name, x, z, y=None, yaw=None, scale=1.0, parent=None, props=None):
    """A dressing prop: its turn comes from `vr`."""
    return kit.place(TEMPLATES, kind, name, (x, H(x, z) if y is None else y, z), yaw=vr.random() * math.tau if yaw is None else yaw, scale=scale, parent=parent, props=props)


def ramp(m, a, b, width, thick, mat=None, bev=0):
    """A flat ramp whose top surface runs from game point a (low) to b (high)."""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    run = math.hypot(dx, dz)
    pitch = math.atan2(dy, run)
    yaw = math.atan2(-dx, -dz)
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - thick / 2 / math.cos(pitch), (a[2] + b[2]) / 2)
    m.box((width, thick, math.hypot(run, dy)), at=mid, mat=mat, pitch=pitch, yaw=yaw, centered=True, bev=bev)


def beam(m, p, q, w, h, mat, bev=0.02, tint=1.0):
    """A squared timber (or girder) from game point p to q, w across and h deep."""
    dx, dy, dz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
    L = math.sqrt(dx * dx + dy * dy + dz * dz)
    m.box((L, h, w), at=((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2), mat=mat,
          yaw=math.atan2(-dz, dx), roll=math.atan2(dy, math.hypot(dx, dz)), centered=True, bev=bev, tint=tint)


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


def wall(ms, a, b, base, h, w=0.5):
    """A free-standing wall along a -> b (its centre line), faced both sides and at both ends."""
    ms.parapet(a, b, base, h=h, w=w)
    (ax, az), (bx, bz) = a, b
    L = math.hypot(bx - ax, bz - az)
    ux, uz = (bx - ax) / L, (bz - az) / L
    for (px, pz), s in ((a, -1.0), (b, 1.0)):
        ms.face((px - uz * w / 2, pz + ux * w / 2), (px + uz * w / 2, pz - ux * w / 2), (ux * s, uz * s), (base, base), (base + h, base + h), ms.rng)


def weed(m, a, b, out, n, top=1.6, bottom=-0.3):
    """Kelp hanging down a wall's face between the tides."""
    (ax, az), (bx, bz) = a, b
    for _ in range(n):
        t = vr.random()
        x, z = lerp(ax, bx, t) + out[0] * 0.05, lerp(az, bz, t) + out[1] * 0.05
        y0 = top - vr.random() * 0.6
        pts = [(x + out[0] * 0.03 * k, y0 - k * (y0 - bottom) / 4, z + out[1] * 0.03 * k + 0.08 * math.sin(k * 1.7 + t * 9)) for k in range(5)]
        m.tube(pts, [0.05, 0.045, 0.04, 0.03, 0.015], mat=KELP, segs=4, cap=False)


def frame(cx, cz, b):
    """Local axes at a point on the arena, at bearing b: u out from the rose, v across."""
    a = math.radians(b)
    ox, oz = math.cos(a), math.sin(a)

    def at(u, v):
        return (cx + ox * u - oz * v, cz + oz * u + ox * v)

    return at, (ox, oz), (-oz, ox)


# ----------------------------------------------------------------- landing

BOAT = (54.0, 6.1)
prop("rowboat", "BUOY_boat", BOAT[0], BOAT[1], y=0.0, yaw=facing(1.0, 0.0), props={"interact": "boat", "range": 6.0, "float": -0.15, "min": -1.0, "max": 2.5})
kit.empty("SPAWN_landing", (52.8, ARENA_Y + 0.05, 1.2), yaw=look(-1.0, -0.3))

# The quay: a dressed face down into the gut, setts on its deck, landing steps
# going down along its face to the water at any tide.
quay = kit.Masonry(P, vr, seeds=(930, 931))
QUAY_X1 = 60.0
quay.retaining((GUT_X, GUT_N), (QUAY_X1, GUT_N), (0.0, 1.0), (-2.6, -2.6), (ARENA_Y, ARENA_Y))
STEP_X, STEP_N = 55.4, 12
steps_col = MB()
for k in range(STEP_N):
    y = ARENA_Y + 0.04 - 0.3 * (k + 1)
    x0 = STEP_X + 0.32 * k
    steps_col.box((0.32, y + 2.6, 1.1), at=(x0 + 0.16, -2.6, GUT_N + 0.55), bev=0)
    quay.walls.box((0.34, 0.3, 1.14), at=(x0 + 0.16, y - 0.3, GUT_N + 0.57), mat=STONE if k % 2 else STONE_DARK, bev=0.03, tint=0.8 + 0.25 * vr.random())
end_x = STEP_X + 0.32 * STEP_N
# Under the steps' nosings, the face they're built out on.
quay.face((STEP_X, GUT_N + 1.1), (end_x, GUT_N + 1.1), (0.0, 1.0), (-2.6, -2.6), (ARENA_Y + 0.04 - 0.3, ARENA_Y + 0.04 - 0.3 * (STEP_N + 1)), vr)
quay.face((end_x, GUT_N), (end_x, GUT_N + 1.1), (1.0, 0.0), (-2.6, -2.6), (ARENA_Y + 0.04 - 0.3 * (STEP_N + 1),) * 2, vr)
steps_col.build("COL_steps", ao=0, grime=0)
weed(quay.walls, (GUT_X + 0.5, GUT_N), (STEP_X - 0.5, GUT_N), (0.0, 1.0), 14)
quay.walls.ring(0.16, 0.035, at=(50.2, 2.3, GUT_N + 0.06), mat=IRON, pitch=math.pi / 2, segs=12, tube_segs=4)
quay.walls.ring(0.16, 0.035, at=(56.8, 2.3, GUT_N + 1.16), mat=IRON, pitch=math.pi / 2, segs=12, tube_segs=4)
kit.pave(quay.walls, GUT_X + 0.5, QUAY_X1, -0.4, GUT_N - 1.06, lambda x, z: ARENA_Y + 0.02, vr, SETTS, row=(0.4, 0.6), width=(0.5, 0.9),
         keep=lambda x, z: z > 0.4 * noise2(x * 0.6, 0.0, 78) and vr.random() > 0.04)
kit.pave(quay.walls, 39.2, GUT_X + 0.5, -1.7, 1.7, lambda x, z: ARENA_Y + 0.02, vr, SETTS, row=(0.4, 0.6), width=(0.5, 0.9),
         keep=lambda x, z: abs(z) < 1.4 + 0.4 * noise2(x * 0.7, 0.0, 79) and vr.random() > 0.06)
quay.build("quay", "COL_quay", tideline=True, ao=0.5, ao_dist=0.5, grime=0.2, grime_h=0.6)

for i, bx in enumerate((48.8, 53.4)):
    prop("bollard", f"bollard_quay_{i}", bx, GUT_N - 0.5, y=ARENA_Y + 0.04, yaw=0.0, props={"col": 1})
    # Gulls on the bollards and the crane: they go up as you land.
    kit.empty(f"FX_perch_bollard_{i}", (bx, ARENA_Y + 0.7, GUT_N - 0.5))

# A post crane on the quay's edge, its jib out over the boat.
CX, CZ = 51.0, GUT_N - 0.95
crane = MB(73)
crane.box((1.3, 0.45, 1.3), at=(CX, ARENA_Y, CZ), mat=STONE_DARK, bev=0.05)
crane.box((0.36, 4.5, 0.36), at=(CX, ARENA_Y + 0.45, CZ), mat=TIMBER, bev=0.03)
tip = (CX + 0.4, ARENA_Y + 5.0, GUT_N + 2.7)
beam(crane, (CX, ARENA_Y + 1.6, CZ + 0.15), tip, 0.26, 0.3, TIMBER)
beam(crane, (CX, ARENA_Y + 4.9, CZ + 0.1), (tip[0], tip[1] + 0.12, tip[2] - 0.3), 0.06, 0.06, IRON, bev=0)
for y in (ARENA_Y + 1.5, ARENA_Y + 4.85):
    crane.box((0.44, 0.1, 0.44), at=(CX, y, CZ), mat=IRON, bev=0.01)
crane.cyl(0.22, 0.22, 0.6, at=(CX - 0.48, ARENA_Y + 1.25, CZ), mat=TIMBER, roll=math.pi / 2, centered=True, segs=10)
crane.tube([(CX - 0.48, ARENA_Y + 1.25, CZ - 0.3), (CX - 0.48, ARENA_Y + 0.95, CZ - 0.45), (CX - 0.48, ARENA_Y + 0.9, CZ - 0.65)], 0.025, mat=IRON, segs=5)
crane.box((0.22, 0.3, 0.16), at=(tip[0], tip[1] - 0.42, tip[2]), mat=TIMBER, bev=0.02)
crane.tube([(tip[0], tip[1] - 0.4, tip[2]), (tip[0] + 0.02, ARENA_Y + 2.0, tip[2] + 0.05)], 0.018, mat=P["rope"], segs=4)
crane.tube([(tip[0] + 0.02, ARENA_Y + 2.0, tip[2] + 0.05), (tip[0] + 0.02, ARENA_Y + 1.82, tip[2] + 0.05), (tip[0] + 0.15, ARENA_Y + 1.75, tip[2] + 0.05)], 0.03, mat=IRON, segs=5)
crane.build("crane", grime=0.2, ao=0.5)
MB().box((0.5, 4.95, 0.5), at=(CX, ARENA_Y, CZ), bev=0).box((1.3, 0.45, 1.3), at=(CX, ARENA_Y, CZ), bev=0).build("COL_crane", ao=0, grime=0)
kit.empty("FX_perch_quay", (tip[0], tip[1] + 0.25, tip[2]))

# The roofless boathouse at the gut's head: crow-stepped back gable, a door
# onto the quay, its slip running out of the open end into the gut.
house = kit.Masonry(P, vr, seeds=(940, 941))
HX0 = 40.5
wall(house, (HX0 + 0.25, GUT_N), (HX0 + 0.25, GUT_S), ARENA_Y, 2.8)
for k, (half, h) in enumerate(((2.0, 0.5), (1.4, 0.5), (0.7, 0.45))):
    zc = (GUT_N + GUT_S) / 2
    wall(house, (HX0 + 0.25, zc - half), (HX0 + 0.25, zc + half), ARENA_Y + 2.9 + 0.6 * k, h)
for (x0, x1, h) in ((HX0 + 0.5, 42.3, 2.6), (43.4, 44.8, 2.6), (44.8, GUT_X, 1.9)):
    wall(house, (x0, GUT_N + 0.25), (x1, GUT_N + 0.25), ARENA_Y, h)
wall(house, (42.3, GUT_N + 0.25), (43.4, GUT_N + 0.25), ARENA_Y + 2.15, 0.45)
house.walls.box((1.3, 0.16, 0.56), at=(42.85, ARENA_Y + 2.0, GUT_N + 0.25), mat=TIMBER, bev=0.02)
for (x0, x1, h) in ((HX0 + 0.5, 44.0, 2.6), (44.0, GUT_X, 1.35)):
    wall(house, (x0, GUT_S - 0.25), (x1, GUT_S - 0.25), ARENA_Y, h)
# Charred rafters across it, one come down; a broken-up boat on trestles inside.
beam(house.walls, (42.6, ARENA_Y + 2.72, GUT_N + 0.1), (42.6, ARENA_Y + 2.72, GUT_S - 0.1), 0.18, 0.22, CHAR)
beam(house.walls, (44.4, ARENA_Y + 1.5, GUT_N + 0.1), (44.9, ARENA_Y + 0.15, GUT_S - 1.2), 0.18, 0.22, CHAR)
for k in range(5):
    house.walls.box((0.42 + vr.random() * 0.3, 0.28, 0.35 + vr.random() * 0.2), at=(45.0 + vr.uniform(-0.4, 0.8), ARENA_Y, GUT_S - 0.9 - vr.random() * 1.6),
                    mat=STONE if k % 2 else STONE_DARK, yaw=vr.random() * math.tau, bev=0.04, tint=0.8 + 0.2 * vr.random())
house.build("boathouse", "COL_boathouse", ao=0.55, ao_dist=0.5, grime=0.25, grime_h=0.8)
for k, z in enumerate((GUT_N + 1.6, GUT_S - 1.6)):
    dress("decor_barrels" if k else "plank_pile", f"boathouse_{k}", 42.2, z, y=ARENA_Y, yaw=vr.uniform(-0.3, 0.3))
dress("rope_coil", "boathouse_rope", 41.7, GUT_N + 3.0, y=ARENA_Y)
dress("lobster_pot", "boathouse_pot", 43.6, GUT_N - 0.9, y=ARENA_Y + 0.02)

# The slip: setts between two timber runners, weed below high water.
slip_col = MB()
ZM = (GUT_N + GUT_S) / 2
ramp(slip_col, (SLIP_X1, SLIP_Y1, ZM), (GUT_X, ARENA_Y, ZM), GUT_S - GUT_N, 3.0)
slip_col.build("COL_slip", ao=0, grime=0)
slip = MB(74)
kit.pave(slip, GUT_X, SLIP_X1, GUT_N + 0.05, GUT_S - 0.05, lambda x, z: slip_y(x) - 0.02, vr, SETTS, row=(0.35, 0.5), width=(0.6, 1.0))
for z in (ZM - 0.7, ZM + 0.7):
    beam(slip, (GUT_X, ARENA_Y + 0.08, z), (SLIP_X1, SLIP_Y1 + 0.08, z), 0.2, 0.14, P["hull_dark"])
slip.build("slip", tideline=True, ao=0.3, grime=0.0)

prop("lantern_post", "lantern_landing", 41.6, -3.6, y=H(41.6, -3.6), yaw=math.pi / 2)
prop("lantern_post", "lantern_quay", 59.4, GUT_N - 1.3, y=ARENA_Y + 0.03, yaw=-math.pi / 2)

# --------------------------------------------------------------- breakwater
# A mole of dressed blocks on its rubble mound, the walk paved; a parapet on its
# north side, knocked down here and there by the weather.

MOLE_X0, MOLE_X1, MOLE_HALF = GATE_X1, 39.5, 2.3
mole = kit.Masonry(P, vr, seeds=(950, 951))
for side in (-1.0, 1.0):
    a, b = (MOLE_X0, side * MOLE_HALF), (MOLE_X1, side * MOLE_HALF)
    mole.face(a, b, (0.0, side), (-2.8, -2.8), (WALK_Y, WALK_Y), vr)
    mole.coping(a, b, (0.0, side), (WALK_Y + 0.04, WALK_Y + 0.04), 0.55, vr)
    mole.solid(a, b, (0.0, side), (-2.8, -2.8), (WALK_Y + 0.04, WALK_Y + 0.04), MOLE_HALF)
    weed(mole.walls, a, b, (0.0, side), 26)
PARAPET = [(17.6, 21.2, 0.9), (23.6, 26.8, 0.9), (26.8, 28.0, 0.45), (28.0, 31.4, 0.9), (33.8, 37.6, 0.9), (37.6, 39.3, 0.55)]
for x0, x1, h in PARAPET:
    wall(mole, (x0, -MOLE_HALF + 0.25), (x1, -MOLE_HALF + 0.25), WALK_Y + 0.04, h)
kit.pave(mole.walls, MOLE_X0, MOLE_X1, -MOLE_HALF + 0.6, MOLE_HALF - 0.6, lambda x, z: WALK_Y + 0.01, vr, SETTS, row=(0.7, 1.1), width=(0.9, 1.5))
# Blocks thrown off the parapet: on the walk, and in the sea where the gaps are.
for x0, x1 in ((21.2, 23.6), (31.4, 33.8)):
    for k in range(4):
        x = vr.uniform(x0, x1)
        z = -MOLE_HALF - 1.2 - vr.random() * 2.5 if k else -MOLE_HALF + 0.9
        mole.walls.box((0.7 + vr.random() * 0.4, 0.4, 0.45 + vr.random() * 0.2), at=(x, (H(x, z) - 0.15) if k else WALK_Y + 0.04, z),
                       mat=STONE if k % 2 else STONE_DARK, yaw=vr.random() * math.tau, roll=vr.uniform(-0.2, 0.2) if k else 0.0, bev=0.05, tint=0.85)
mole.build("breakwater", "COL_breakwater", tideline=True, ao=0.5, ao_dist=0.5, grime=0.2, grime_h=0.6)

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
    gate.tube([(16.72, ARENA_Y + 0.4, gz + 0.3 * k) for k in range(-1, 2)], 0.05, mat=KELP, segs=4)
gate.build("gate", grime=0.3)

# The footing: big coursed blocks built out from the arena's edge and down into the
# rock, battered (each course down sits a little further out). The top course between
# the piers is the sill, paler and worn; the breakwater's walk runs in under it.
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
# Weed hanging down the seaward face between the tides, either side of the breakwater.
for gz in (-3.6, -2.8, 2.9, 3.7):
    hang = [(GATE_X1 + (SILL_Y - yy) * 0.035 + 0.03, yy, gz + 0.12 * math.sin(yy * 3.0 + gz)) for yy in (1.7, 1.25, 0.8, 0.4)]
    plinth.tube(hang, 0.045, mat=KELP, segs=4)
plinth.build("gate_footing", tideline=True, grime=0.25)

# ------------------------------------------------------------------- arena
# The old landing stage. Its sea wall: a dressed face down into deep water on
# three stretches of the south rim, the rock showing where it has fallen.

seawall = kit.Masonry(P, vr, seeds=(960, 961))
for b0, b1 in SEAWALL:
    n = max(1, int(round((b1 - b0) / 14.0)))
    pts = [(math.cos(math.radians(b)) * stage_r(b), math.sin(math.radians(b)) * stage_r(b)) for b in (b0 + (b1 - b0) * k / n for k in range(n + 1))]
    for (ax, az), (bx, bz) in zip(pts, pts[1:]):
        L = math.hypot(bx - ax, bz - az)
        nx, nz = (bz - az) / L, -(bx - ax) / L
        if nx * (ax + bx) + nz * (az + bz) < 0:
            nx, nz = -nx, -nz
        seawall.retaining((ax, az), (bx, bz), (nx, nz), (-2.4, -2.4), (ARENA_Y, ARENA_Y))
        weed(seawall.walls, (ax, az), (bx, bz), (nx, nz), 6)
    # Where it has broken, its blocks lie tumbled at its foot.
    for b in (b0 - 2.5, b1 + 2.5):
        r = stage_r(b) + 1.6
        for k in range(3):
            x, z = math.cos(math.radians(b + vr.uniform(-3, 3))) * (r + vr.random() * 1.5), math.sin(math.radians(b + vr.uniform(-3, 3))) * (r + vr.random() * 1.5)
            seawall.walls.box((0.9 + vr.random() * 0.4, 0.5, 0.55 + vr.random() * 0.2), at=(x, H(x, z) - 0.2, z), mat=STONE_DARK, yaw=vr.random() * math.tau,
                              roll=vr.uniform(-0.3, 0.3), pitch=vr.uniform(-0.2, 0.2), bev=0.05, tint=0.8)
seawall.build("seawall", "COL_seawall", tideline=True, ao=0.5, ao_dist=0.5, grime=0.2, grime_h=0.6)

# Bollards and rings round the rim, from when boats lay alongside.
for k, b in enumerate((57.0, 71.0, 97.0, 108.0, 131.0, 26.0, 336.0)):
    on_wall = walled(b) > 0.5
    r = stage_r(b) - (0.55 if on_wall else 1.2)
    x, z = math.cos(math.radians(b)) * r, math.sin(math.radians(b)) * r
    prop("bollard", f"bollard_arena_{k}", x, z, y=ARENA_Y + 0.04 if on_wall else H(x, z) - 0.03, yaw=math.radians(-b), props={"col": 1})

# The cover. Two roofless store sheds (north-east and north-west), their doors
# away from the sea; the old stage crane fallen across the south-west; a stack of
# dressed blocks waiting on a ship that never came, and its capstan (south-east).
sheds = kit.Masonry(P, vr, seeds=(980, 981))
cover = MB(75)
cover_col = MB()
FOOTPRINTS = []
for name, b in (("ne", 315.0), ("nw", 225.0)):
    cx, cz = math.cos(math.radians(b)) * 8.2, math.sin(math.radians(b)) * 8.2
    at, (ox, oz), (ax_, az_) = frame(cx, cz, b)
    L, D, W = 4.2, 3.2, 0.45
    FOOTPRINTS.append((cx, cz, 3.0))
    # Its long sides across the bearing; the inner one (toward the sea and the
    # Guardian) whole but for a breach, the outer one with the door.
    inner, outer = -D / 2 + W / 2, D / 2 - W / 2
    for v0, v1, h in ((-L / 2, -0.7, 2.6), (-0.7, 0.6, 1.5), (0.6, L / 2, 2.6)):
        wall(sheds, at(inner, v0), at(inner, v1), ARENA_Y, h, W)
    for v0, v1, h in ((-L / 2, 0.15, 2.4), (1.3, L / 2, 2.4)):
        wall(sheds, at(outer, v0), at(outer, v1), ARENA_Y, h, W)
    wall(sheds, at(outer, 0.15), at(outer, 1.3), ARENA_Y + 2.05, 0.35, W)
    lx, lz = at(outer, 0.725)
    sheds.walls.box((1.35, 0.15, W + 0.08), at=(lx, ARENA_Y + 1.92, lz), mat=TIMBER, yaw=math.atan2(-az_, ax_), bev=0.02)
    for v in (-L / 2 + W / 2, L / 2 - W / 2):
        wall(sheds, at(inner + W / 2, v), at(outer - W / 2, v), ARENA_Y, 2.4 if v < 0 else 2.2, W)
    # Rafters: one still across, one fallen in.
    p0, p1 = at(inner, -0.9), at(outer, -0.9)
    beam(cover, (p0[0], ARENA_Y + 2.62, p0[1]), (p1[0], ARENA_Y + 2.47, p1[1]), 0.16, 0.2, CHAR)
    p0, p1 = at(inner + 0.3, 1.2), at(outer - 0.2, 0.4)
    beam(cover, (p0[0], ARENA_Y + 1.5, p0[1]), (p1[0], ARENA_Y + 0.1, p1[1]), 0.16, 0.2, CHAR)
    for k in range(5):
        px, pz = at(inner - 0.9 - vr.random() * 0.8, vr.uniform(-0.8, 0.7))
        cover.box((0.45 + vr.random() * 0.25, 0.3, 0.3 + vr.random() * 0.15), at=(px, ARENA_Y, pz), mat=sheds.coursed[k % len(sheds.coursed)], yaw=vr.random() * math.tau, roll=vr.uniform(-0.15, 0.15), bev=0.04, tint=0.8)
    px, pz = at(inner, L / 2 - 0.4)
    kit.empty(f"FX_perch_shed_{name}", (px, ARENA_Y + 2.75, pz))

# The crane: its stone pedestal and snapped post at the rim, the jib fallen across
# the flags toward the rose, the winch thrown down beside it.
at, (ox, oz), (tx, tz) = frame(0.0, 0.0, 135.0)
PX, PZ = at(11.0, 0.0)
FOOTPRINTS += [(PX, PZ, 1.9)]
pyaw = math.atan2(-oz, ox)
for k, (s, h) in enumerate(((2.5, 0.62), (2.3, 0.6))):
    y0 = ARENA_Y + 0.62 * k
    cover.box((s, h - 0.02, s), at=(PX, y0, PZ), mat=STONE_DARK if k else STONE, yaw=pyaw, bev=0.06, tint=0.85 + 0.1 * k)
cover.cyl(0.75, 0.75, 0.16, at=(PX, ARENA_Y + 1.22, PZ), mat=IRON, segs=14)
cover.cyl(0.28, 0.3, 1.05, at=(PX, ARENA_Y + 1.38, PZ), mat=RUST, segs=10)
cover.cyl(0.29, 0.24, 0.12, at=(PX + 0.05, ARENA_Y + 2.43, PZ), mat=RUST, segs=10, roll=0.25)
cover_col.box((2.5, 1.24, 2.5), at=(PX, ARENA_Y, PZ), yaw=pyaw, bev=0)
# The jib: a lattice girder, its foot on the pedestal's edge, its head on the flags.
j0 = at(9.6, 0.4)
j1 = at(3.4, 1.6)
J0, J1 = (j0[0], ARENA_Y + 1.5, j0[1]), (j1[0], ARENA_Y + 0.3, j1[1])
jx, jy, jz = J1[0] - J0[0], J1[1] - J0[1], J1[2] - J0[2]
jl = math.sqrt(jx * jx + jy * jy + jz * jz)
sx, sz = -jz / math.hypot(jx, jz), jx / math.hypot(jx, jz)  # across the jib


def jib_pt(t, side, up):
    return (J0[0] + jx * t + sx * side, J0[1] + jy * t + up, J0[2] + jz * t + sz * side)


GIRDER = Paint(IRON.mat, 0x3A3632)
for side in (-0.32, 0.32):
    for up in (-0.36, 0.36):
        beam(cover, jib_pt(0.0, side, up), jib_pt(1.0, side * 0.6, up * 0.6), 0.14, 0.14, GIRDER, bev=0.01)


def lace(a, b, n=9):
    """Zigzag lacing between two chords, a and b as (side, up) at the jib's foot."""
    for k in range(n):
        t0, t1 = k / n, (k + 1) / n
        s0, s1 = 1 - 0.4 * t0, 1 - 0.4 * t1
        p, q = (a, b) if k % 2 else (b, a)
        beam(cover, jib_pt(t0, p[0] * s0, p[1] * s0), jib_pt(t1, q[0] * s1, q[1] * s1), 0.06, 0.06, RUST if k % 3 else GIRDER, bev=0)


for a, b in (((-0.32, -0.36), (-0.32, 0.36)), ((0.32, -0.36), (0.32, 0.36)), ((-0.32, 0.36), (0.32, 0.36)), ((-0.32, -0.36), (0.32, -0.36))):
    lace(a, b)
hx, hy, hz = jib_pt(1.04, 0.0, 0.0)
cover.cyl(0.24, 0.24, 0.22, at=(hx, hy, hz), mat=IRON, pitch=math.pi / 2, yaw=math.atan2(-jz, jx), centered=True, segs=12)
chain = [(hx, hy, hz), (hx + ox * 0.6, ARENA_Y + 0.06, hz + oz * 0.6), (hx + tx * 1.4 + ox * 0.4, ARENA_Y + 0.06, hz + tz * 1.4 + oz * 0.4), (hx + tx * 2.0 - ox * 0.5, ARENA_Y + 0.06, hz + tz * 2.0 - oz * 0.5)]
cover.tube(chain, 0.045, mat=IRON, segs=4)
ramp(cover_col, (J1[0], J1[1] + 0.22, J1[2]), (J0[0], J0[1] + 0.36, J0[2]), 0.8, 0.72)
# The winch, on its side by the pedestal.
WX, WZ = at(9.6, -2.3)
with turned(cover, (WX, ARENA_Y + 0.6, WZ), yaw=pyaw + 0.5, roll=math.pi / 2 - 0.1):
    for side in (-0.55, 0.55):
        cover.box((1.4, 1.1, 0.08), at=(WX, ARENA_Y + 0.05, WZ + side), mat=IRON, bev=0.01)
    cover.cyl(0.32, 0.32, 1.0, at=(WX, ARENA_Y + 0.6, WZ), mat=RUST, pitch=math.pi / 2, centered=True, segs=12)
    cover.cyl(0.5, 0.5, 0.06, at=(WX, ARENA_Y + 0.6, WZ + 0.62), mat=IRON, pitch=math.pi / 2, centered=True, segs=16)
cover_col.box((1.6, 1.15, 1.5), at=(WX, ARENA_Y, WZ), yaw=pyaw + 0.5, bev=0)
FOOTPRINTS += [(WX, WZ, 1.2), ((J0[0] + J1[0]) / 2, (J0[2] + J1[2]) / 2, 3.4)]

# The block stack and its capstan.
at, (ox, oz), (tx, tz) = frame(0.0, 0.0, 45.0)
byaw = math.atan2(-tz, tx)
for layer, row in enumerate(((-1.35, 0.0, 1.35), (-0.68, 0.68), (0.0,))):
    for k, v in enumerate(row):
        bx, bz = at(8.2 + vr.uniform(-0.08, 0.08), v + vr.uniform(-0.06, 0.06))
        y0 = ARENA_Y + layer * 0.78
        yaw = byaw + vr.uniform(-0.06, 0.06)
        cover.box((1.28, 0.76, 1.05), at=(bx, y0, bz), mat=STONE if (layer + k) % 2 else STONE_DARK, yaw=yaw, bev=0.05, tint=0.85 + 0.15 * vr.random())
        cover_col.box((1.28, 0.78, 1.05), at=(bx, y0, bz), yaw=yaw, bev=0)
cx, cz = at(8.4, -2.7)
cover.cyl(0.55, 0.62, 0.16, at=(cx, ARENA_Y, cz), mat=IRON, segs=12)
cover.cyl(0.42, 0.38, 0.7, at=(cx, ARENA_Y + 0.16, cz), mat=IRON, segs=12)
cover.cyl(0.5, 0.5, 0.14, at=(cx, ARENA_Y + 0.86, cz), mat=IRON, segs=12)
for k in range(4):
    a = k * math.pi / 2 + 0.3
    cover.box((0.16, 0.12, 0.16), at=(cx + math.cos(a) * 0.47, ARENA_Y + 0.88, cz + math.sin(a) * 0.47), mat=IRON, yaw=-a, bev=0.01)
for k in range(2):
    a = vr.random() * math.tau
    p = (cx + math.cos(a) * 0.9, ARENA_Y + 0.07, cz + math.sin(a) * 0.9)
    beam(cover, p, (p[0] + math.cos(a + 1.3) * 2.0, ARENA_Y + 0.07, p[2] + math.sin(a + 1.3) * 2.0), 0.12, 0.12, P["timber_light"])
cover_col.cyl(0.6, 0.6, 1.0, at=(cx, ARENA_Y, cz), segs=10, bev=0)
FOOTPRINTS += [(*at(8.2, 0.0), 2.4), (cx, cz, 0.9)]

# Lamp posts round the rim, long dark: two still stand, two snapped.
for k, (b, broken) in enumerate(((22.0, False), (162.0, True), (203.0, False), (338.0, True))):
    r = stage_r(b) - 1.6
    x, z = math.cos(math.radians(b)) * r, math.sin(math.radians(b)) * r
    lean = vr.uniform(-0.12, 0.12)
    with turned(cover, (x, ARENA_Y, z), roll=lean):
        cover.cyl(0.2, 0.17, 0.4, at=(x, ARENA_Y, z), mat=IRON, segs=10)
        cover.cyl(0.075, 0.06, 1.3 if broken else 3.1, at=(x, ARENA_Y + 0.4, z), mat=IRON, segs=8)
        if not broken:
            # The lamp's head, dark: a sill, the glass, its corner bars and a pointed cap.
            yaw = math.radians(-b)
            cover.box((0.36, 0.05, 0.36), at=(x, ARENA_Y + 3.5, z), mat=IRON, yaw=yaw, bev=0)
            cover.box((0.28, 0.44, 0.28), at=(x, ARENA_Y + 3.55, z), mat=NIGHT, yaw=yaw, bev=0)
            for cxo, czo in ((-0.15, -0.15), (-0.15, 0.15), (0.15, -0.15), (0.15, 0.15)):
                ox_, oz_ = kit.turn(yaw, cxo, czo)
                cover.box((0.035, 0.46, 0.035), at=(x + ox_, ARENA_Y + 3.54, z + oz_), mat=IRON, yaw=yaw, bev=0)
            cover.cyl(0.25, 0.02, 0.24, at=(x, ARENA_Y + 3.99, z), mat=IRON, segs=4, yaw=yaw + math.pi / 4)
    if broken:
        a = vr.random() * math.tau
        beam(cover, (x + math.cos(a) * 0.5, ARENA_Y + 0.08, z + math.sin(a) * 0.5), (x + math.cos(a) * 2.3, ARENA_Y + 0.08, z + math.sin(a) * 2.3), 0.12, 0.12, IRON, bev=0)
    else:
        kit.empty(f"FX_perch_lamp_{k}", (x, ARENA_Y + 4.0, z))
    cover_col.cyl(0.2, 0.2, 1.7 if broken else 3.5, at=(x, ARENA_Y, z), segs=8, bev=0)
sheds.build("sheds", "COL_sheds", ao=0.55, ao_dist=0.5, grime=0.25, grime_h=0.8)
cover.build("arena_cover", grime=0.25, ao=0.55)
cover_col.build("COL_arena_cover", ao=0, grime=0)


def under_cover(x, z):
    return any(math.hypot(x - fx, z - fz) < fr for fx, fz, fr in FOOTPRINTS)


# Flagstones in rings round the compass rose (a hair above the rock you stand
# on): cracked, sunk, lost in patches where the stage is worn to the rock, more
# of them toward the rim.
flags = MB(66)
r = 3.5
while r < 13.6:
    width = 1.05 + vr.random() * 0.2
    n = max(8, int(2 * math.pi * (r + width / 2) / 1.35))
    off = vr.random()
    for s in range(n):
        a0 = (s + off) / n * math.tau + 0.012
        a1 = (s + 1 + off) / n * math.tau - 0.012
        am = (a0 + a1) / 2
        mx, mz = math.cos(am) * (r + width / 2), math.sin(am) * (r + width / 2)
        worn = fbm3(mx * 0.16, 0.0, mz * 0.16, 81) + 0.25 * noise2(mx * 0.7, mz * 0.7, 82)
        if worn < -0.32 + 0.55 * smoothstep(8.0, 13.5, r) or vr.random() < 0.05 or under_cover(mx, mz):
            continue
        r0, r1 = r + 0.025, r + width - 0.025
        y = ARENA_Y + 0.05 + vr.random() * 0.012 - (0.03 if vr.random() < 0.12 else 0.0)
        pts = [(math.cos(a1) * r0, math.sin(a1) * r0), (math.cos(a1) * r1, math.sin(a1) * r1), (math.cos(a0) * r1, math.sin(a0) * r1), (math.cos(a0) * r0, math.sin(a0) * r0)]
        tint = 0.78 + 0.22 * vr.random()
        flag = FLAGS[int(vr.random() * len(FLAGS))]
        if vr.random() < 0.15:
            # Cracked across.
            k = 0.35 + 0.3 * vr.random()
            mid = [(lerp(pts[0][0], pts[1][0], k), lerp(pts[0][1], pts[1][1], k)), (lerp(pts[3][0], pts[2][0], k + 0.1), lerp(pts[3][1], pts[2][1], k + 0.1))]
            halves = ([pts[0], mid[0], mid[1], pts[3]], [mid[0], pts[1], pts[2], mid[1]])
            for h, half in enumerate(halves):
                q = [flags.bm.verts.new(B(px, y - 0.012 * h, pz)) for px, pz in half]
                flags._paint([flags.bm.faces.new(q)], flag, 0.1, tint)
            continue
        q = [flags.bm.verts.new(B(px, y, pz)) for px, pz in pts]
        flags._paint([flags.bm.faces.new(q)], flag, 0.1, tint)
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
    tip_ = (math.cos(a) * L, math.sin(a) * L)
    side = (-math.sin(a) * (0.32 if k % 2 == 0 else 0.22), math.cos(a) * (0.32 if k % 2 == 0 else 0.22))
    for sgn in (1, -1):
        q = [rose.bm.verts.new(B(px, ARENA_Y + 0.065, pz)) for px, pz in ((0.0, 0.0), (side[0] * sgn, side[1] * sgn), tip_)]
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
# Steps up a cleft in the stack, its sides faced with coursed stone to the rock's
# shoulder, ending in two piers at the arena's edge.

stair_col = MB()
ramp(stair_col, STAIR_FOOT, STAIR_TOP, 2 * STAIR_HALF, 0.5)
stair_col.box((2 * STAIR_HALF, 0.5, 0.9), at=(0.0, PLATFORM_Y - 0.5, STAIR_TOP[2] - 0.45), bev=0)  # level with the platform past the top
stair_col.build("COL_stair", ao=0, grime=0)

stair = MB(68)
n_steps = 20
for k in range(n_steps):
    z0 = STAIR_FOOT[2] - (STAIR_FOOT[2] - STAIR_TOP[2]) * k / n_steps
    z1 = STAIR_FOOT[2] - (STAIR_FOOT[2] - STAIR_TOP[2]) * (k + 1) / n_steps
    top = stair_y((z0 + z1) / 2) + 0.1
    stair.box((2 * STAIR_HALF, top - (stair_y(z0) - 0.6), z0 - z1 + 0.04), at=(0.0, stair_y(z0) - 0.6, (z0 + z1) / 2), mat=STONE if k % 2 else STONE_DARK, bev=0.04, tint=0.85 + 0.2 * vr.random())
# Thresholds at the foot and the head.
stair.box((2 * STAIR_HALF + 0.3, 0.5, 1.0), at=(0.0, ARENA_Y - 0.44, STAIR_FOOT[2] + 0.5), mat=STONE, bev=0.04, tint=0.8)
stair.box((2 * STAIR_HALF, 0.5, 0.9), at=(0.0, PLATFORM_Y - 0.47, STAIR_TOP[2] - 0.45), mat=STONE, bev=0.04, tint=0.8)
stair.build("stair", grime=0.2)

cleft = kit.Masonry(P, vr, seeds=(970, 971))
for s in (-1.0, 1.0):
    fx = s * STAIR_HALF
    cleft.retaining((fx, STAIR_FOOT[2]), (fx, -26.5), (-s, 0.0), (stair_y(STAIR_FOOT[2]) - 0.1, stair_y(-26.5)), (BENCH, BENCH))
    # The pier's front, facing the arena, and its side, where it stands clear of the cliff.
    bx = s * (STAIR_HALF + 1.05)
    cleft.face((fx, STAIR_FOOT[2]), (bx, STAIR_FOOT[2]), (0.0, 1.0), (ARENA_Y - 0.1, ARENA_Y - 0.1), (BENCH, BENCH), vr)
    cleft.face((bx, STAIR_FOOT[2]), (bx, -15.8), (s, 0.0), (ARENA_Y - 0.1, ARENA_Y - 0.1), (BENCH, BENCH), vr)
    cleft.solids.box((1.05, BENCH + 0.04 - ARENA_Y + 0.2, 1.4), at=(s * (STAIR_HALF + 0.525), ARENA_Y - 0.2, STAIR_FOOT[2] - 0.7), bev=0)

# Rubble across the stair's foot until the Guardian falls (the solid part is a
# hidden box under the rocks, so it goes when they do).
rubble = MB()
for k in range(9):
    rx = -1.7 + (k % 3) * 1.7 + (rnd.random() - 0.5) * 0.4
    rz = -15.0 - (k // 3) * 0.75
    r = 0.9 + rnd.random() * 0.4
    rubble.rock(r, at=(rx, ARENA_Y + 0.5 + (k // 3) * 0.55, rz), mat=ROCK if k % 2 else ROCK_DARK, seed=800 + k, squash=0.85)
for k in range(6):
    rubble.rock(0.55 + vr.random() * 0.35, at=(vr.uniform(-1.6, 1.6), ARENA_Y + 1.4 + vr.random() * 1.0, vr.uniform(-16.8, -14.8)), mat=STONE_DARK if k % 2 else ROCK, seed=820 + k, squash=0.8)
rubble_ob = rubble.build("STATE_guardian_defeated_off", props={"col": 1})
MB().box((4.6, 2.7, 2.6), at=(0, ARENA_Y, -15.6), bev=0).build("COL_rubble", parent=rubble_ob, ao=0, grime=0)

# Braziers that light the way once the Guardian is gone.
lit = kit.empty("STATE_guardian_defeated_on", (0, 0, 0))
for k, bx in enumerate((-2.2, 2.2)):
    br = MB()
    br.cyl(0.25, 0.3, 1.1, mat=IRON, segs=8)
    br.cyl(0.55, 0.35, 0.35, at=(0, 1.1, 0), mat=IRON, segs=10)
    br.sphere(0.32, at=(0, 1.42, 0), mat=FIRE, scale=(1, 0.7, 1), subdiv=1)
    for j in range(3):
        a = j / 3 * math.tau
        br.box((0.06, 0.5, 0.06), at=(math.cos(a) * 0.45, 1.05, math.sin(a) * 0.45), mat=IRON, yaw=-a, roll=0.35, bev=0)
    br.build(f"brazier_{k}", loc=(bx, ARENA_Y, -13.55), parent=lit, props={"light": "warm", "light_offset": [0, 1.6, 0]})

# ----------------------------------------------------------- tower platform
# A shoulder cut into the stack: walled on three sides where the rock was cut
# back, a parapet along its edge over the sea. None of them can be climbed, so
# the stack's top stays out of reach.

for a, b, out, top in (((-8.5, -26.5), (-STAIR_HALF, -26.5), (0.0, -1.0), BENCH), ((STAIR_HALF, -26.5), (7.5, -26.5), (0.0, -1.0), BENCH),
                       ((-8.5, -26.5), (-8.5, -38.5), (1.0, 0.0), BENCH), ((-8.5, -38.5), (7.5, -38.5), (0.0, 1.0), WALL_N)):
    cleft.retaining(a, b, out, (PLATFORM_Y, PLATFORM_Y), (top, top))
wall(cleft, (7.25, -26.5), (7.25, -38.5), PLATFORM_Y, 1.1)
kit.pave(cleft.walls, -8.4, 6.95, -38.4, -26.6, lambda x, z: PLATFORM_Y, vr, SETTS, row=(0.8, 1.2), width=(0.9, 1.5),
         keep=lambda x, z: math.hypot(x, z - TOWER_Z) > 3.85 and vr.random() > 0.06)
cleft.build("cleft_walls", "COL_cleft_walls", ao=0.55, ao_dist=0.6, grime=0.2, grime_h=0.8)

tower_col = MB()
tower_col.cyl(3.4, 2.9, 12.0, at=(0, PLATFORM_Y, TOWER_Z), segs=18, bev=0)
tower_col.cyl(3.75, 3.75, 0.45, at=(0, PLATFORM_Y + 12.0, TOWER_Z), segs=18, bev=0)
tower_col.cyl(1.8, 1.8, 4.6, at=(0, PLATFORM_Y + 12.45, TOWER_Z), segs=12, bev=0)
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
for sx_ in (-1.05, 1.05):
    tower.box((0.36, 2.5, 0.3), at=(sx_, PLATFORM_Y, DZ + 0.06), mat=STONE, bev=0.03)
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
    tower.cyl(0.035, 0.035, 1.05, at=(math.cos(a) * 3.6, PLATFORM_Y + TOP + 0.45, TOWER_Z + math.sin(a) * 3.6), mat=IRON, segs=6, bev=0)
for ry in (0.55, 1.08):
    tower.ring(3.6, 0.03, at=(0, PLATFORM_Y + TOP + 0.45 + ry, TOWER_Z), mat=IRON, segs=48, tube_segs=4)
tower.build("tower", grime=0.25, smooth=35)

# The lantern room: Saltmere's beehive lens, astragals and copper dome, at
# full size on the gallery. The beam turns at the lens.
LAMP_SCALE = 2.0
prop("beacon_lamp", "beacon_lamp_top", 0, TOWER_Z, y=PLATFORM_Y + TOP + 0.45, yaw=0.0, scale=LAMP_SCALE)
kit.empty("FX_beacon_lamp", (0, PLATFORM_Y + TOP + 0.45 + 1.02 * LAMP_SCALE, TOWER_Z))
kit.empty("FX_gulls", (0, 0, TOWER_Z))

# Where you carry the Ember: a stone plinth and a brass bowl at the door.
ember = MB()
ember.cyl(0.6, 0.75, 1.0, mat=STONE, segs=10)
ember.cyl(0.65, 0.45, 0.3, at=(0, 1.0, 0), mat=P["brass"], segs=12)
ember.build("INT_beacon", loc=(0, PLATFORM_Y, -27.6), props={"interact": "beacon", "range": 3.6, "col": 1})

# ---------------------------------------------------------------- sea arch
# Out in the deep beyond where the Guardian rises: rock bridging two legs, the
# Guardian framed in it from the arena.

ARCH = [(-10.6, SEA - 0.8, 31.5), (-9.8, 1.5, 31.9), (-8.9, 5.5, 32.4), (-7.0, 9.0, 32.9), (-3.8, 11.6, 33.3), (0.2, 12.6, 33.6),
        (4.2, 11.7, 33.8), (7.3, 9.2, 33.9), (9.2, 5.6, 34.0), (10.2, 1.5, 34.1), (10.9, SEA - 0.8, 34.2)]


def catmull(pts, per=3):
    out = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        for k in range(per):
            t = k / per
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(3)))
    out.append(pts[-1])
    return out


arch = MB(76)
path = catmull(ARCH, 4)
sections = []
for i, p in enumerate(path):
    q0, q1 = path[max(i - 1, 0)], path[min(i + 1, len(path) - 1)]
    t = Vector((q1[0] - q0[0], q1[1] - q0[1], q1[2] - q0[2])).normalized()
    u = (Vector((0.0, 0.0, 1.0)) - t * t.z).normalized()  # through the arch, roughly south
    v = t.cross(u).normalized()
    s = i / (len(path) - 1)
    mid = math.sin(math.pi * s)
    bulge = 1.0 + 0.2 * fbm3(s * 7.0, 0.0, 0.0, 78)  # thicker and thinner along its length
    ring = []
    for k in range(12):
        a = k / 12 * math.tau
        n = fbm3(p[0] * 0.6 + math.cos(a) * 1.4, p[1] * 0.6, p[2] * 0.6 + math.sin(a) * 1.4, 77)
        rr = bulge * (1.0 + 0.32 * n) * (1.0 + 0.07 * math.sin(p[1] * 3.4 + n * 2.0))
        ru, rv = lerp(3.0, 2.3, mid) * rr, lerp(3.2, 1.7, mid) * rr
        c = Vector(p) + u * (math.cos(a) * ru) + v * (math.sin(a) * rv)
        ring.append((c.x, min(c.y, 13.6 + 0.3 * n), c.z))
    sections.append(ring)
arch.loft(sections, mat=ROCK_DARK, closed=True, cap=True)
bmesh.ops.recalc_face_normals(arch.bm, faces=list(arch.bm.faces))
# Banded like the stack's rock.
BANDS = [ROCK_DARK, Paint(ROCK.mat, 0x5F5C55), ROCK, Paint(ROCK.mat, 0x6E6A61)]
for f in arch.bm.faces:
    c = f.calc_center_median()
    arch._paint([f], BANDS[int((c.z + 6.0) / 1.1 + 0.35 * fbm3(c.x * 0.2, c.z * 0.2, c.y * 0.2, 79)) % len(BANDS)], 0.04)
arch.build("sea_arch", tideline=True, ao=0.5, grime=0.0, smooth=50, props={"col": 1})
kit.empty("FX_perch_arch", (0.2, 12.6 + 1.9, 33.6))

# ------------------------------------------------------------------ rocks
# home.blend's unit boulders (kit.Boulders): bedded where the ground is high,
# sea rocks stood up out of the deep where it falls away, kept clear of the
# arena, the breakwater, the gut and the water the Guardian rises from.

rocks = kit.Boulders(HOME, H, vr)
boulder = rocks.boulder


def rock_ok(x, z):
    if math.hypot(x, z) < 21.0 or (13.0 < x < 43.0 and abs(z) < 6.5) or (x > 44.0 and 1.0 < z < 11.5):
        return False
    if math.hypot(x, z - 18.5) < 10.0 or (abs(x) < 13.0 and 24.0 < z < 41.0):
        return False
    if any(math.hypot(x - sx, z - sz) < 6.0 for sx, sz in SPITTER_ROCKS):
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


coast(outward(STACK, STACK_SET), (4.0, 8.0), 3.6, (1.8, 3.6))
# Stones round the headland's rim, clear of the quay, the gut and the way up from the breakwater.
for (ax, az), (bx, bz), (nx, nz) in outward(LAND, {6, 7, 13, 14}):
    L = math.hypot(bx - ax, bz - az)
    t = vr.random() * 3.0
    while t < L:
        x, z = ax + (bx - ax) * t / L - nx * (0.6 + vr.random()), az + (bz - az) * t / L - nz * (0.6 + vr.random())
        if H(x, z) > 2.0 and not (GUT_N - 1.5 < z < GUT_S + 1.0 and x > GUT_X - 1.0):
            boulder(x, z, 0.8 + vr.random() * 0.7, sink=0.45)
        t += 2.5 + vr.random() * 2.5
# Sea rocks off the west rocks and round the stage's open rim, out of the fight.
for b in range(150, 215, 9):
    r = 23.0 + vr.random() * 4.0
    x, z = math.cos(math.radians(b)) * r, math.sin(math.radians(b)) * r
    if rock_ok(x, z):
        boulder(x, z, 2.0 + vr.random() * 1.4)
# Fallen rock at the foot of the stack's cliff over the arena, too big to climb.
for x0, x1 in ((-12.0, -4.0), (4.0, 9.5)):
    x = x0
    while x < x1:
        z = -math.sqrt(max(0.0, 15.7 ** 2 - x * x)) - 0.4
        if H(x, z + 0.9) < ARENA_Y + 0.3:
            boulder(x, z + 0.4, 1.7 + vr.random() * 0.6, sink=0.25)
        x += 2.2 + vr.random() * 1.6
# Stones on the west rocks' crest and sea side.
for k in range(7):
    i = vr.random() * (len(SPUR) - 1)
    (ax, az, _), (bx, bz, _) = SPUR[int(i)], SPUR[int(i) + 1]
    t = i - int(i)
    x, z = lerp(ax, bx, t) - 0.8 - vr.random() * 1.5, lerp(az, bz, t)
    boulder(x, z, 0.9 + vr.random() * 0.8, sink=0.45)
# Sea stacks standing off: (x, z, top, how big).
for x, z, top, size in ((-36.0, -12.0, 8.5, 2.1), (-33.0, 17.0, 6.5, 1.8), (23.0, -31.0, 9.5, 2.3), (-23.0, 29.0, 5.5, 1.6),
                        (41.0, 31.0, 7.0, 1.9), (69.0, -19.0, 6.0, 1.7), (-40.0, -45.0, 7.5, 2.0)):
    rocks.stack(x, z, top, size, SEA)
# At the arch's feet.
for x, z in ((-11.0, 29.5), (-12.5, 34.0), (11.5, 31.5), (12.5, 36.5)):
    boulder(x, z, 2.2 + vr.random())

# ---------------------------------------------------------------- dressing

# Lanterns along the breakwater, lit once the chapter's done.
done = kit.empty("STATE_chapter1_complete_on", (0, 0, 0))
for k, lx in enumerate((21.0, 28.5, 36.0)):
    prop("lantern_post", f"lantern_breakwater_{k}", lx, MOLE_HALF - 0.3, y=WALK_Y + 0.04, yaw=math.pi / 2, parent=done)

# Weed on the ledges and skerries the ebb bares.
placed = 0
for _ in range(900):
    if placed >= 34:
        break
    x, z = vr.uniform(-45.0, 70.0), vr.uniform(-60.0, 40.0)
    y = H(x, z)
    if 0.05 < y < 1.3 and grade(x, z) < 0.6 and not (13.0 < x < 43.0 and abs(z) < 3.0):
        dress("seaweed", f"weed_{placed:02d}", x, z, y=y)
        placed += 1

# ----------------------------------------------------------------- enemies

for k, (sx, sz) in enumerate(SPITTER_ROCKS):
    kit.empty(f"ENEMY_spitter_{k}", (sx, 3.4, sz), props={"enemy": "drowned_spitter", "tide": "any"})
for k, gz in enumerate((-4.5, 4.5)):
    kit.empty(f"ENEMY_wisp_{k}", (18.5, ARENA_Y + 2.5, gz), props={"enemy": "lantern_wisp", "tide": "any"})

# ------------------------------------------------------------------ gloom

# GLOOM_ pockets on the breakwater, between the Spitters' skerries: flare through
# them (and dazzle whoever's spitting) or take the chill. Clear of the anchor.
for k, gx in enumerate((35.5, 24.0)):
    kit.empty(f"GLOOM_breakwater_{k}", (gx, WALK_Y, 0.0), props={"radius": 2.6})

# ---------------------------------------------------- anchors and the beam

for name, (ax, ay, az) in {"landing": (47.5, ARENA_Y + 0.1, -2.0), "breakwater": (30.0, WALK_Y + 0.14, 0.6), "arena_e": (11.0, ARENA_Y + 0.1, 0.0),
                           "arena_n": (0.0, ARENA_Y + 0.1, -10.5), "arena_w": (-10.5, ARENA_Y + 0.1, 2.0)}.items():
    kit.empty(f"ANCHOR_{name}", (ax, ay, az))
# Lantern's Rest lies south-west.
kit.empty("FX_home_light", (-250, 0, 260))

kit.save_and_export("art/blender/locations/beacon.blend", "public/assets/models/locations/beacon.glb")
