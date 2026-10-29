import * as THREE from "three";
import { describe, expect, it } from "vitest";
import type { Action } from "../src/data/controls";
import { BALANCE } from "../src/data/balance";
import type { Input } from "../src/core/Input";
import { StaticCollider } from "../src/physics/StaticCollider";
import { PlayerController, type PlayerEnv } from "../src/player/PlayerController";

// The dash should go exactly its distance at any frame rate, hand straight back
// to walking (no slide), and hold level when used in the air.

const D = BALANCE.player.dash;

function ground(): StaticCollider {
  const slab = new THREE.Mesh(new THREE.BoxGeometry(400, 1, 400));
  slab.position.y = -0.5;
  return new StaticCollider([slab]);
}

function env(collider: StaticCollider): PlayerEnv {
  return { collider, dynamics: [], waterY: -50, anchors: [], sensitivity: 1, dashCharges: 1, dashCooldownMul: 1, speedMul: 1, rooted: false };
}

/** Runs `seconds` of play at `hz` (to the nearest step), holding `held`, with `press` pressed on the first step. Returns the time run. */
function run(p: PlayerController, e: PlayerEnv, hz: number, seconds: number, held: Action[], press: Action[] = []): number {
  let fresh = new Set(press);
  const input = {
    consumeMouse: () => ({ dx: 0, dy: 0 }),
    edgeTurn: () => 0,
    held: (a: Action) => held.includes(a),
    pressed: (a: Action) => fresh.has(a),
  } as unknown as Input;
  const steps = Math.round(seconds * hz);
  for (let i = 0; i < steps; i++) {
    p.update(1 / hz, input, e);
    fresh = new Set();
  }
  return steps / hz;
}

function settled(e: PlayerEnv): PlayerController {
  const p = new PlayerController();
  p.spawn(new THREE.Vector3(0, 0.05, 0), 0);
  run(p, e, 60, 0.5, []);
  return p;
}

describe("dash", () => {
  for (const hz of [30, 60, 144]) {
    it(`covers exactly its distance at ${hz} Hz, then walks on`, () => {
      const e = env(ground());
      const p = settled(e);
      const z0 = p.position.z;
      const t = run(p, e, hz, D.duration, ["forward"], ["dash"]);
      // Any part of the last step past the dash's end is walking.
      expect(z0 - p.position.z).toBeCloseTo(D.distance + BALANCE.player.walkSpeed * (t - D.duration), 2);
      // Straight back to walking pace: a second later you've walked one second's worth.
      const z1 = p.position.z;
      run(p, e, hz, 1, ["forward"]);
      expect(z1 - p.position.z).toBeCloseTo(BALANCE.player.walkSpeed, 1);
    });
  }

  it("stops without sliding when you let go", () => {
    const e = env(ground());
    const p = settled(e);
    const z0 = p.position.z;
    run(p, e, 60, 1.5, [], ["dash"]);
    // Forward when idle, and at most a hand's breadth past the dash itself.
    expect(z0 - p.position.z).toBeGreaterThan(D.distance - 0.01);
    expect(z0 - p.position.z).toBeLessThan(D.distance + 0.35);
  });

  it("holds nearly level in the air", () => {
    const e = env(ground());
    const p = new PlayerController();
    p.spawn(new THREE.Vector3(0, 8, 0), 0);
    p.velocity.y = -6;
    const y0 = p.position.y;
    run(p, e, 60, D.duration, ["forward"], ["dash"]);
    expect(y0 - p.position.y).toBeLessThan(0.25);
  });

  it("takes a buffered press as soon as a charge returns", () => {
    const e = env(ground());
    const p = settled(e);
    run(p, e, 60, D.duration, ["forward"], ["dash"]);
    expect(p.dashCharges).toBe(0);
    // Pressed just before the cooldown runs out: it still fires.
    run(p, e, 60, D.cooldown - D.duration - D.buffer / 2, ["forward"]);
    const z0 = p.position.z;
    run(p, e, 60, D.buffer + D.duration, ["forward"], ["dash"]);
    expect(z0 - p.position.z).toBeGreaterThan(D.distance);
  });
});
