import * as THREE from "three";
import type { Assets } from "../core/Assets";
import { damp, rng } from "../core/math";
import { GULLS } from "../data/wildlife";
import type { StaticCollider } from "../physics/StaticCollider";
import type { Level } from "./Level";

// The gulls of src/data/wildlife.ts. Each part is one instanced mesh (the
// sitting bird, the flying body, either wing), so the whole lot is four draw
// calls. A flier is the body plus two wings hinged at the shoulder and flapped
// about the body's long axis; a sitter switches to that rig when it takes off.

type Range = readonly [number, number];
const pick = (r: Range, u: number) => r[0] + (r[1] - r[0]) * u;

interface Part {
  mesh: THREE.InstancedMesh;
  /** The mesh's place inside its prop. */
  local: THREE.Matrix4;
}

interface Wings {
  flapping: boolean;
  /** Seconds left of this bout of flapping or gliding. */
  left: number;
  phase: number;
  /** Radians up from level. */
  angle: number;
}

/** Circles the flock's centre for as long as you're here. */
interface Wheeler {
  cx: number;
  cz: number;
  r: number;
  h: number;
  /** Angular speed, rad/s; the sign is the way round. */
  w: number;
  a0: number;
  seed: number;
  wings: Wings;
}

/** Sits on a perch till you come close. */
interface Sitter {
  perch: THREE.Vector3;
  yaw: number;
  turn: { from: number; to: number; t: number; next: number };
  state: "sit" | "off" | "away" | "back";
  /** Out along this (level, unit) from the perch; flown in reverse to come back. */
  dir: THREE.Vector3;
  side: THREE.Vector3;
  /** Seconds along the flight path. */
  s: number;
  wait: number;
  wings: Wings;
}

const T = GULLS.takeoff;
/** When it reaches cruising speed, and how far out it is by then. */
const CRUISE_AT = (T.cruise - T.speed) / T.accel;
const CRUISE_FROM = T.speed * CRUISE_AT + 0.5 * T.accel * CRUISE_AT * CRUISE_AT;
/** How far a circle's centre wanders, m. */
const DRIFT = 4;
/** The wing roots on the flying body. */
const SHOULDER = 0.04;
const SHOULDER_Y = 0.03;
const HIDDEN = new THREE.Matrix4().makeScale(0, 0, 0);
const ONE = new THREE.Vector3(1, 1, 1);
const UP = new THREE.Vector3(0, 1, 0);

const p0 = new THREE.Vector3();
const p1 = new THREE.Vector3();
const p2 = new THREE.Vector3();
const vel = new THREE.Vector3();
const euler = new THREE.Euler(0, 0, 0, "YXZ");
const quat = new THREE.Quaternion();
const body = new THREE.Matrix4();
const hinge = new THREE.Matrix4();
const mx = new THREE.Matrix4();
const inst = new THREE.Matrix4();

export class Gulls {
  readonly root = new THREE.Group();
  /** A gull calls from here (alarm: the laugh as it takes off). */
  onCall: ((at: THREE.Vector3, alarm: boolean) => void) | null = null;
  private readonly sitting: Part[];
  private readonly bodies: Part[];
  private readonly wingsL: Part[];
  private readonly wingsR: Part[];
  private readonly wheelers: Wheeler[] = [];
  private readonly sitters: Sitter[] = [];
  private readonly rand = rng(23);
  private time = 0;
  private callIn = 4;

  constructor(assets: Assets, level: Level, collider: StaticCollider) {
    this.root.name = "gulls";
    const r = this.rand;
    const perches = [...level.points].filter(([name]) => name.startsWith("perch")).map(([, at]) => at);
    const flock = GULLS.flock[level.id];
    const fliers = flock + perches.length;
    this.sitting = this.part(assets, "gull", Math.max(1, perches.length), true);
    this.bodies = this.part(assets, "gull_body", fliers, false);
    this.wingsL = this.part(assets, "gull_wing_l", fliers, false);
    this.wingsR = this.part(assets, "gull_wing_r", fliers, false);

    const centre = level.points.get("gulls") ?? middle(level);
    for (let i = 0; i < flock; i++) {
      // A circle that would clip the level (a tower, a mast, a cliff) is drawn
      // again; one that still does is lifted clear.
      let w = this.wheeler(centre);
      for (let tries = 0; tries < 9 && this.clips(w, collider); tries++) {
        if (tries < 6) w = this.wheeler(centre);
        else w.h += 7;
      }
      this.wheelers.push(w);
    }

    const ray = new THREE.Raycaster();
    const solid = this.solidMeshes(level.root);
    for (const at of perches) {
      const perch = at.clone();
      // Stand on what's actually drawn there, not on the marker.
      ray.set(p0.set(at.x, at.y + 0.6, at.z), p1.set(0, -1, 0));
      ray.far = 3;
      const hit = ray.intersectObjects(solid, false)[0];
      if (hit) perch.y = hit.point.y;
      const yaw = r() * Math.PI * 2;
      this.sitters.push({
        perch,
        yaw,
        turn: { from: yaw, to: yaw, t: 1, next: 2 + r() * 6 },
        state: "sit",
        dir: new THREE.Vector3(),
        side: new THREE.Vector3(),
        s: 0,
        wait: 0,
        wings: this.wings(),
      });
    }
    this.update(0, new THREE.Vector3(0, -1000, 0), -Infinity);
  }

  update(dt: number, viewer: THREE.Vector3, waterY: number): void {
    this.time += dt;
    const beat = GULLS.beat;
    this.wheelers.forEach((g, i) => {
      this.flap(g.wings, dt, beat);
      this.wheelerAt(g, this.time, p0);
      this.wheelerAt(g, this.time + 0.1, p1);
      vel.subVectors(p1, p0).divideScalar(0.1);
      const bank = THREE.MathUtils.clamp((g.r * g.w * Math.abs(g.w)) / 9.8, -0.6, 0.6);
      this.flier(i, p0, vel, bank, g.wings.angle);
    });
    const base = this.wheelers.length;
    this.sitters.forEach((g, i) => this.updateSitter(g, i, base + i, dt, viewer, waterY));
    for (const set of [this.sitting, this.bodies, this.wingsL, this.wingsR]) for (const p of set) p.mesh.instanceMatrix.needsUpdate = true;

    this.callIn -= dt;
    if (this.callIn <= 0) {
      this.callIn = pick(GULLS.callEvery, this.rand());
      const near = this.nearest(viewer);
      if (near && near.distanceTo(viewer) < GULLS.earshot) this.onCall?.(near, false);
    }
  }

  dispose(): void {
    for (const set of [this.sitting, this.bodies, this.wingsL, this.wingsR]) for (const p of set) p.mesh.dispose();
    this.root.removeFromParent();
  }

  // ------------------------------------------------------------- sitters

  private updateSitter(g: Sitter, i: number, slot: number, dt: number, viewer: THREE.Vector3, waterY: number): void {
    const r = this.rand;
    if (g.state === "sit") {
      const near = g.perch.distanceTo(viewer) < GULLS.shy;
      if (waterY > g.perch.y + 0.3) {
        // Already under when you got here: it's off somewhere else.
        g.state = "away";
        g.wait = pick(GULLS.away, r());
      } else if (near || waterY > g.perch.y - GULLS.wetFeet) {
        // The tide lifts them off a perch it reaches, as it does the real ones.
        this.setOff(g, viewer);
        if (near) this.onCall?.(g.perch, true);
      } else {
        // Now and then it shuffles round to face somewhere else.
        const t = g.turn;
        t.next -= dt;
        if (t.next <= 0) {
          t.from = g.yaw;
          t.to = g.yaw + (r() < 0.5 ? -1 : 1) * (0.4 + r() * 0.9);
          t.t = 0;
          t.next = 3 + r() * 7;
        }
        if (t.t < 1) {
          t.t = Math.min(1, t.t + dt / 0.3);
          const k = t.t * t.t * (3 - 2 * t.t);
          g.yaw = t.from + (t.to - t.from) * k;
        }
        quat.setFromAxisAngle(UP, g.yaw);
        body.compose(g.perch, quat, ONE);
        this.place(this.sitting, i, body);
        this.hideFlier(slot);
        return;
      }
    }
    this.place(this.sitting, i, null);
    if (g.state === "away") {
      g.wait -= dt;
      this.hideFlier(slot);
      if (g.wait <= 0 && g.perch.distanceTo(viewer) > GULLS.shy * 2.5 && waterY < g.perch.y - 2 * GULLS.wetFeet) {
        this.aim(g, viewer);
        g.state = "back";
        g.s = GULLS.gone;
      }
      return;
    }
    // Out along the path, or back down it.
    const out = g.state === "off";
    g.s += out ? dt : -dt;
    if (out && g.s >= GULLS.gone) {
      g.state = "away";
      g.wait = pick(GULLS.away, r());
      this.hideFlier(slot);
      return;
    }
    if (!out && g.s <= 0) {
      g.state = "sit";
      g.yaw = Math.atan2(-g.dir.x, -g.dir.z);
      g.turn.from = g.turn.to = g.yaw;
      this.hideFlier(slot);
      return;
    }
    // Hard flapping off the perch and into it; gliding bouts in between.
    const near = g.s < 2.5;
    this.flap(g.wings, dt, near ? GULLS.beat * 1.6 : GULLS.beat, near);
    this.pathAt(g, g.s, p0);
    this.pathAt(g, g.s + (out ? 0.1 : -0.1), p1);
    vel.subVectors(p1, p0).divideScalar(0.1);
    this.pathAt(g, g.s + (out ? 0.2 : -0.2), p2);
    const turn = Math.atan2(p2.x - p1.x, p2.z - p1.z) - Math.atan2(vel.x, vel.z);
    const bank = THREE.MathUtils.clamp(-Math.atan2(Math.sin(turn), Math.cos(turn)) * 4, -0.5, 0.5);
    this.flier(slot, p0, vel, bank, g.wings.angle);
  }

  private setOff(g: Sitter, viewer: THREE.Vector3): void {
    this.aim(g, viewer);
    g.state = "off";
    g.s = 0;
    g.wings.flapping = true;
    g.wings.left = 2.5;
  }

  /** Away from you and from the middle of the place: out to sea, as a rule. */
  private aim(g: Sitter, viewer: THREE.Vector3): void {
    const away = p0.subVectors(g.perch, viewer).setY(0).normalize();
    const out = p1.copy(g.perch).setY(0).normalize();
    g.dir.addVectors(away, out).setY(0);
    if (g.dir.lengthSq() < 1e-4) g.dir.set(1, 0, 0);
    g.dir.normalize().applyAxisAngle(UP, (this.rand() - 0.5) * 0.8);
    g.side.crossVectors(UP, g.dir);
  }

  private pathAt(g: Sitter, s: number, out: THREE.Vector3): THREE.Vector3 {
    const t = Math.max(0, s);
    const d = t < CRUISE_AT ? T.speed * t + 0.5 * T.accel * t * t : CRUISE_FROM + T.cruise * (t - CRUISE_AT);
    const lift = T.hop * (1 - Math.exp(-1.5 * t)) + T.climb * t;
    const sway = 2.5 * Math.sin(t * 0.45) * (1 - Math.exp(-0.5 * t));
    return out.copy(g.perch).addScaledVector(g.dir, d).addScaledVector(g.side, sway).setY(g.perch.y + lift);
  }

  // ------------------------------------------------------------- fliers

  private wheeler(centre: THREE.Vector3): Wheeler {
    const r = this.rand;
    const w: Wheeler = {
      cx: centre.x + (r() - 0.5) * 2 * GULLS.spread,
      cz: centre.z + (r() - 0.5) * 2 * GULLS.spread,
      r: pick(GULLS.radius, r()),
      h: pick(GULLS.height, r()),
      w: 0,
      a0: r() * Math.PI * 2,
      seed: r() * 100,
      wings: this.wings(),
    };
    w.w = (pick(GULLS.speed, r()) / w.r) * (r() < 0.5 ? -1 : 1);
    return w;
  }

  /** Round its circle, which breathes a little and drifts with the wind. */
  private wheelerAt(g: Wheeler, t: number, out: THREE.Vector3): THREE.Vector3 {
    const a = g.a0 + g.w * t;
    const r = g.r * (1 + 0.1 * Math.sin(t * 0.05 + g.seed));
    const cx = g.cx + DRIFT * Math.sin(t * 0.03 + g.seed);
    const cz = g.cz + DRIFT * Math.cos(t * 0.023 + g.seed * 1.3);
    return out.set(cx + Math.cos(a) * r, g.h + 1.5 * Math.sin(a * 2 + g.seed), cz + Math.sin(a) * r);
  }

  /** Samples a wheeler's circle (with its drift and breathing) against the level. */
  private clips(g: Wheeler, collider: StaticCollider): boolean {
    for (const dr of [-0.1 * g.r - DRIFT, 0, 0.1 * g.r + DRIFT]) {
      for (let k = 0; k < 24; k++) {
        const a = (k / 24) * Math.PI * 2;
        p0.set(g.cx + Math.cos(a) * (g.r + dr), g.h, g.cz + Math.sin(a) * (g.r + dr));
        if (collider.sphereHits(p0, 3)) return true;
      }
    }
    return false;
  }

  private flap(w: Wings, dt: number, beat: number, hard = false): void {
    w.left -= dt;
    if (w.left <= 0 && !hard) {
      w.flapping = !w.flapping;
      w.left = pick(w.flapping ? GULLS.flapBout : GULLS.glide, this.rand());
    }
    const flapping = w.flapping || hard;
    w.phase += dt * beat * Math.PI * 2;
    const target = flapping ? 0.12 + 0.7 * Math.sin(w.phase) : 0.1 + 0.03 * Math.sin(w.phase * 0.2);
    w.angle = damp(w.angle, target, 18, dt);
  }

  private wings(): Wings {
    return { flapping: this.rand() < 0.5, left: this.rand() * 3, phase: this.rand() * 6, angle: 0.1 };
  }

  /** Body along its velocity (nose up when climbing), banked into the turn, wings at `angle`. */
  private flier(slot: number, at: THREE.Vector3, v: THREE.Vector3, bank: number, angle: number): void {
    const flat = Math.hypot(v.x, v.z);
    euler.set(-Math.atan2(v.y, flat) * 0.7, Math.atan2(v.x, v.z), bank);
    quat.setFromEuler(euler);
    body.compose(at, quat, ONE);
    this.place(this.bodies, slot, body);
    this.place(this.wingsL, slot, mx.multiplyMatrices(body, hinge.makeTranslation(SHOULDER, SHOULDER_Y, 0)).multiply(hinge.makeRotationZ(angle)));
    this.place(this.wingsR, slot, mx.multiplyMatrices(body, hinge.makeTranslation(-SHOULDER, SHOULDER_Y, 0)).multiply(hinge.makeRotationZ(-angle)));
  }

  private hideFlier(slot: number): void {
    this.place(this.bodies, slot, null);
    this.place(this.wingsL, slot, null);
    this.place(this.wingsR, slot, null);
  }

  private place(parts: readonly Part[], i: number, m: THREE.Matrix4 | null): void {
    for (const p of parts) p.mesh.setMatrixAt(i, m ? inst.multiplyMatrices(m, p.local) : HIDDEN);
  }

  // ------------------------------------------------------------- setup

  private part(assets: Assets, name: string, count: number, shadows: boolean): Part[] {
    const src = assets.prop(name);
    if (!src) return [];
    src.updateWorldMatrix(true, true);
    const parts: Part[] = [];
    src.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      const mesh = new THREE.InstancedMesh(m.geometry, m.material, count);
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      mesh.name = `gull:${name}`;
      // They move every frame; one bounding sphere for the lot isn't worth keeping.
      mesh.frustumCulled = false;
      mesh.castShadow = shadows;
      this.root.add(mesh);
      parts.push({ mesh, local: m.matrixWorld.clone() });
    });
    return parts;
  }

  private solidMeshes(root: THREE.Object3D): THREE.Mesh[] {
    const out: THREE.Mesh[] = [];
    root.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh || !o.visible) return;
      const mats = Array.isArray(m.material) ? m.material : [m.material];
      if (mats.some((x) => x.visible)) out.push(m);
    });
    return out;
  }

  /** The closest gull you could see, flying or sitting. */
  private nearest(viewer: THREE.Vector3): THREE.Vector3 | null {
    let best: THREE.Vector3 | null = null;
    let bestD = Infinity;
    for (const g of this.wheelers) {
      const at = this.wheelerAt(g, this.time, p2);
      const d = at.distanceToSquared(viewer);
      if (d < bestD) {
        bestD = d;
        best = (best ?? new THREE.Vector3()).copy(at);
      }
    }
    for (const g of this.sitters) {
      if (g.state !== "sit") continue;
      const d = g.perch.distanceToSquared(viewer);
      if (d < bestD) {
        bestD = d;
        best = (best ?? new THREE.Vector3()).copy(g.perch);
      }
    }
    return best;
  }
}

/** The middle of the place, for the flock to circle: its gathering spots, else its spawn. */
function middle(level: Level): THREE.Vector3 {
  if (!level.nodes.length) return level.spawn.clone();
  const c = new THREE.Vector3();
  for (const n of level.nodes) c.add(n.position);
  return c.divideScalar(level.nodes.length);
}
