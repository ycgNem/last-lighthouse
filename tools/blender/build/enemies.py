"""Builds art/blender/enemies/enemies.blend and public/assets/models/enemies.glb.

Each enemy is an empty named MODEL_<enemy id> with named child parts. The game
animates the parts procedurally (claws, legs, jaw, arms) and drives the
emission of every GLOW_* material for attack telegraphs, so keep those names.
Feet (or the waterline for sea creatures) sit at the origin; front is game +Z.

    blender -b --factory-startup --python tools/blender/build/enemies.py
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import kit  # noqa: E402
from kit import MB  # noqa: E402

kit.reset()
P = kit.palette()
SEA_GREEN = 0x3DFFB0


def glow(name):
    return kit.material(f"GLOW_{name}", 0x1B5E48, rough=0.4, emit=SEA_GREEN, strength=1.0)


# ------------------------------------------------------------- brine crab


def brine_crab():
    root = kit.empty("MODEL_brine_crab", (0, 0, 0))
    shell = kit.material("crab_shell", 0x8A3B2A, rough=0.55)
    belly = kit.material("crab_belly", 0xC79A6B, rough=0.7)
    g = glow("crab")

    body = MB()
    body.sphere(0.55, at=(0, 0.5, 0), mat=shell, scale=(1.3, 0.5, 1.0), subdiv=2)
    body.sphere(0.5, at=(0, 0.42, 0.02), mat=belly, scale=(1.15, 0.32, 0.9), subdiv=1)
    for i, x in enumerate((-0.35, 0.0, 0.35)):
        body.cyl(0.07, 0.0, 0.18, at=(x, 0.72, -0.1 + abs(x) * 0.2), mat=shell, segs=5)
    rnd = random.Random(4)
    for i in range(7):
        a = rnd.random() * math.tau
        body.sphere(0.045, at=(math.cos(a) * 0.45, 0.68, math.sin(a) * 0.32), mat=g, subdiv=0)
    for side in (-1, 1):
        body.cyl(0.025, 0.025, 0.28, at=(side * 0.14, 0.66, 0.42), mat=shell, segs=5)
        body.sphere(0.06, at=(side * 0.14, 0.95, 0.43), mat=P["iron"], subdiv=1)
    body.build("body", parent=root)

    for side, name in ((-1, "claw_l"), (1, "claw_r")):
        c = MB()
        # Built around the shoulder pivot; arm reaches forward and out.
        c.box((0.14, 0.14, 0.42), at=(side * 0.12, -0.07, 0.2), mat=shell, yaw=-side * 0.35)
        c.sphere(0.2, at=(side * 0.3, 0.0, 0.5), mat=shell, scale=(1.0, 0.75, 1.3), subdiv=1)
        c.box((0.1, 0.09, 0.34), at=(side * 0.36, 0.02, 0.78), mat=shell, yaw=side * 0.15)
        c.box((0.09, 0.07, 0.28), at=(side * 0.22, -0.08, 0.74), mat=shell, yaw=-side * 0.25)
        c.box((0.05, 0.04, 0.22), at=(side * 0.3, -0.03, 0.74), mat=g, yaw=0.0)
        c.build(name, loc=(side * 0.55, 0.5, 0.35), parent=root)

    for side, s in ((-1, "l"), (1, "r")):
        for i in range(3):
            leg = MB()
            leg.box((0.42, 0.07, 0.07), at=(side * 0.2, -0.04, 0), mat=shell, roll=-side * 0.35)
            leg.box((0.07, 0.42, 0.07), at=(side * 0.42, -0.42, 0), mat=shell, roll=side * 0.25)
            leg.build(f"leg_{s}{i}", loc=(side * 0.55, 0.42, 0.15 - i * 0.28), parent=root)
    return root


# -------------------------------------------------------- drowned spitter


def drowned_spitter():
    root = kit.empty("MODEL_drowned_spitter", (4, 0, 0))
    skin = kit.material("drowned_skin", 0x4F5E57, rough=0.8)
    rag = kit.material("drowned_rag", 0x3B3A33, rough=0.95)
    g = glow("spitter")

    body = MB()
    body.cyl(0.32, 0.42, 0.9, at=(0, 0.0, 0), mat=rag, segs=9)
    body.cyl(0.42, 0.36, 0.75, at=(0, 0.9, 0), mat=skin, segs=9)
    body.sphere(0.4, at=(0, 1.35, -0.05), mat=skin, scale=(1.0, 0.8, 0.9), subdiv=1)
    rnd = random.Random(6)
    for i in range(10):
        a = rnd.random() * math.tau
        body.box((0.1, 0.9 + rnd.random() * 0.6, 0.03), at=(math.cos(a) * 0.4, 0.4 + rnd.random() * 0.8, math.sin(a) * 0.35), mat=P["kelp"] if i % 2 else P["kelp_dark"], yaw=a, roll=(rnd.random() - 0.5) * 0.4)
    for i in range(6):
        body.sphere(0.05, at=((rnd.random() - 0.5) * 0.6, 1.0 + rnd.random() * 0.6, -0.3), mat=kit.material("barnacle", 0xD8D2C4), subdiv=0)
    body.build("body", parent=root)

    throat = MB()
    throat.sphere(0.2, at=(0, 0, 0), mat=g, scale=(1.0, 1.2, 0.8), subdiv=2)
    throat.build("throat", loc=(0, 1.42, 0.27), parent=root)

    head = MB()
    head.sphere(0.27, at=(0, 0.2, 0.05), mat=skin, scale=(0.95, 1.05, 1.0), subdiv=2)
    head.box((0.34, 0.1, 0.22), at=(0, -0.02, 0.18), mat=skin)
    for side in (-1, 1):
        head.sphere(0.055, at=(side * 0.11, 0.28, 0.26), mat=g, subdiv=1)
    head.box((0.5, 0.08, 0.4), at=(0, 0.42, 0.02), mat=P["kelp_dark"], roll=0.15)
    head.build("head", loc=(0, 1.72, 0.05), parent=root)

    for side, name in ((-1, "arm_l"), (1, "arm_r")):
        a = MB()
        a.cyl(0.09, 0.07, 0.95, at=(0, -0.95, 0), mat=skin, segs=7)
        a.sphere(0.11, at=(0, -1.0, 0.02), mat=skin, subdiv=1)
        a.box((0.06, 0.5, 0.03), at=(side * 0.04, -0.9, 0.08), mat=P["kelp"])
        a.build(name, loc=(side * 0.5, 1.6, 0), parent=root)
    return root


# ------------------------------------------------------------ lantern wisp


def lantern_wisp():
    root = kit.empty("MODEL_lantern_wisp", (8, 0, 0))
    g = glow("wisp")

    core = MB()
    core.sphere(0.2, mat=g, subdiv=2)
    core.build("core", parent=root)

    cage = MB()
    cage.cyl(0.32, 0.32, 0.05, at=(0, 0.32, 0), mat=P["copper"], segs=8)
    cage.cyl(0.32, 0.32, 0.05, at=(0, -0.37, 0), mat=P["copper"], segs=8)
    cage.cyl(0.32, 0.08, 0.2, at=(0, 0.37, 0), mat=P["copper"], segs=8)
    cage.cyl(0.04, 0.04, 0.18, at=(0, 0.57, 0), mat=P["copper"], segs=6)
    for i in range(6):
        a = i / 6 * math.tau
        cage.box((0.03, 0.68, 0.03), at=(math.cos(a) * 0.3, -0.34, math.sin(a) * 0.3), mat=P["copper"])
    cage.build("cage", parent=root)

    for i in range(4):
        a = i / 4 * math.tau + 0.4
        t = MB()
        t.cyl(0.04, 0.0, 0.8, at=(0, -0.8, 0), mat=g, segs=5)
        t.build(f"tendril_{i}", loc=(math.cos(a) * 0.18, -0.38, math.sin(a) * 0.18), parent=root)
    return root


# ------------------------------------------------------------- tide lurker


def tide_lurker():
    root = kit.empty("MODEL_tide_lurker", (12, 0, 0))
    hide = kit.material("lurker_hide", 0x1F2B33, rough=0.45)
    belly = kit.material("lurker_belly", 0x6C7A72, rough=0.6)
    tooth = kit.material("tooth", 0xE9E2CF, rough=0.5)
    g = glow("lurker")

    body = MB()
    body.cyl(0.55, 0.75, 2.6, at=(0, -2.6, -0.2), mat=hide, segs=10)
    body.sphere(0.85, at=(0, 0.45, 0), mat=hide, scale=(1.05, 0.75, 1.25), subdiv=2)
    body.sphere(0.7, at=(0, 0.25, 0.35), mat=belly, scale=(0.95, 0.45, 1.0), subdiv=1)
    for side in (-1, 1):
        body.sphere(0.12, at=(side * 0.45, 0.8, 0.55), mat=g, subdiv=1)
        body.box((0.08, 0.5, 0.5), at=(side * 0.85, 0.2, -0.2), mat=hide, roll=side * 0.6)
    body.cyl(0.03, 0.02, 0.9, at=(0, 1.0, 0.3), mat=hide, segs=5, pitch=0.7)
    body.sphere(0.11, at=(0, 1.62, 0.95), mat=g, subdiv=1)
    for i in range(7):
        x = -0.45 + i * 0.15
        body.cyl(0.05, 0.0, 0.18, at=(x, 0.28, 1.0 - abs(x) * 0.35), mat=tooth, segs=4, pitch=math.pi)
    body.build("body", parent=root)

    jaw = MB()
    jaw.sphere(0.7, at=(0, -0.05, 0.45), mat=belly, scale=(1.0, 0.3, 1.05), subdiv=1)
    for i in range(6):
        x = -0.38 + i * 0.15
        jaw.cyl(0.045, 0.0, 0.16, at=(x, 0.1, 0.95 - abs(x) * 0.35), mat=tooth, segs=4)
    jaw.build("jaw", loc=(0, 0.2, -0.1), parent=root)
    return root


# ----------------------------------------------------------- wreck guardian


def wreck_guardian():
    root = kit.empty("MODEL_wreck_guardian", (20, 0, 0))
    hull = P["hull"]
    hull_dark = P["hull_dark"]
    barn = kit.material("barnacle", 0xD8D2C4)
    heart = glow("heart")
    vents = glow("vents")
    chain = glow("chain")
    rnd = random.Random(12)

    body = MB()
    # Lower body: a capsized hull sunk in the sea.
    body.sphere(3.2, at=(0, -1.2, 0), mat=hull_dark, scale=(1.1, 0.75, 0.8), subdiv=2)
    # Torso of stacked planks around a rib cage.
    for i in range(9):
        y = 1.0 + i * 0.55
        w = 3.6 - abs(i - 4) * 0.25
        body.box((w, 0.45, 0.35), at=(0, y, -0.9), mat=hull if i % 2 else hull_dark, roll=(rnd.random() - 0.5) * 0.08)
        if i in (3, 4, 5, 6):
            for side in (-1, 1):
                body.box((0.9, 0.42, 0.3), at=(side * 1.25, y, 0.75), mat=hull_dark, yaw=side * 0.5)
        else:
            body.box((w * 0.85, 0.45, 0.3), at=(0, y, 0.85), mat=hull_dark)
    for side in (-1, 1):
        body.sphere(1.1, at=(side * 2.3, 5.3, 0), mat=hull, scale=(1.2, 0.6, 0.9), subdiv=1)
    for i in range(30):
        body.sphere(0.12 + rnd.random() * 0.1, at=((rnd.random() - 0.5) * 4.0, 1.0 + rnd.random() * 4.5, 1.0 + rnd.random() * 0.2), mat=barn, subdiv=0)
    for side in (-1, 1):
        for k in range(3):
            body.box((0.5, 0.25, 0.08), at=(side * (1.0 + k * 0.5), 5.5 + k * 0.15, -1.15), mat=vents, roll=side * 0.3)
    body.build("body", parent=root)

    h = MB()
    h.sphere(1.0, at=(0, 0, 0), mat=heart, subdiv=2)
    h.build("heart", loc=(0, 3.4, 0.55), parent=root)

    head = MB()
    head.cyl(0.9, 1.0, 0.25, at=(0, 0, 0), mat=P["iron"], segs=10)
    for i in range(8):
        a = i / 8 * math.tau
        head.box((0.1, 1.3, 0.1), at=(math.cos(a) * 0.85, 0.2, math.sin(a) * 0.85), mat=P["iron"])
    head.cyl(1.0, 0.25, 0.6, at=(0, 1.5, 0), mat=P["iron"], segs=10)
    head.sphere(0.5, at=(0, 0.8, 0), mat=heart, subdiv=1)
    head.build("head", loc=(0, 6.0, -0.2), parent=root)

    # Left: the chain arm that sweeps, ending in an anchor. Pivot at the shoulder.
    arm = MB()
    for k in range(9):
        arm.box((0.32, 0.5, 0.12) if k % 2 else (0.12, 0.5, 0.32), at=(-0.5 - k * 0.55, -0.25, 0), mat=chain if k % 3 == 0 else P["iron"], roll=math.pi / 2)
    ax = -5.6
    arm.box((0.3, 2.0, 0.3), at=(ax, -1.9, 0), mat=P["iron"])
    arm.box((2.2, 0.3, 0.3), at=(ax, -1.9, 0), mat=P["iron"])
    for side in (-1, 1):
        arm.cyl(0.18, 0.0, 0.7, at=(ax + side * 1.1, -1.75, 0), mat=P["iron"], segs=5)
    arm.cyl(0.35, 0.35, 0.15, at=(ax, 0.2, 0), mat=P["iron"], segs=10, pitch=math.pi / 2, centered=True)
    arm.build("arm_l", loc=(-2.6, 5.2, 0), parent=root)

    # Right: a hull-plank arm with a brine-mortar barrel.
    arm = MB()
    arm.box((3.2, 0.7, 0.8), at=(1.7, -0.35, 0), mat=hull_dark, centered=True)
    arm.cyl(0.45, 0.55, 1.6, at=(3.4, 0.0, 0), mat=P["iron"], segs=10, roll=-math.pi / 2, centered=True)
    arm.cyl(0.3, 0.3, 0.2, at=(4.25, 0.0, 0), mat=vents, segs=10, roll=-math.pi / 2, centered=True)
    arm.build("arm_r", loc=(2.6, 5.2, 0), parent=root)
    return root


for build in (brine_crab, drowned_spitter, lantern_wisp, tide_lurker, wreck_guardian):
    build()

kit.save_and_export("art/blender/enemies/enemies.blend", "public/assets/models/enemies.glb")
