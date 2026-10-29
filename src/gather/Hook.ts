import * as THREE from "three";
import { FLOTSAM, HOOK } from "../data/salvage";
import { FX_COLORS } from "../fx/Effects";
import type { GameContext } from "../game/Context";
import type { HookStats } from "../systems/salvage";
import type { Flotsam, Piece } from "./Flotsam";
import type { Wreck } from "./Wreckage";

// The salvage hook: a grapnel on a line, fired from the reel under the
// bolt-caster (right mouse anywhere, left too at home, where there's nothing
// to shoot). It flies out on an arc to whatever's under the crosshair, give or
// take HOOK.assist. Drift it bites, and reels in across the water until it's at
// your feet. A wreck it tears a piece off, which flies to you, and the hook
// comes back. A miss splashes down and the hook comes back.

export type Hookable = Piece | Wreck;

/** What's under the crosshair, for the prompt and the reticle. */
export interface HookAim {
  target: Hookable;
  /** ok: in reach and takeable. far: out of reach. blocked: see reason. */
  state: "ok" | "far" | "blocked";
  reason: string | null;
}

type Phase = "ready" | "out" | "reel" | "back";

/** Seconds the hook takes to come back after a yank or a miss. */
const BACK_TIME = 0.28;
const ROPE_POINTS = 16;
/** The line slips off a piece once you're this far past the hook's reach (you walked away). */
const SLIP = 8;
/** The grapnel out in the world, scaled up from its viewmodel so it reads at range. */
const GRAPNEL_SCALE = 3.2;
/** Seconds between the reel's clicks. */
const TICK = 0.09;

const tmp = new THREE.Vector3();
const tmp2 = new THREE.Vector3();
const DOWN = new THREE.Vector3(0, -1, 0);

export class Hook {
  aim: HookAim | null = null;
  private phase: Phase = "ready";
  private t = 0;
  private dur = 0;
  private arc = 0;
  private cooldown = 0;
  private target: Hookable | null = null;
  private readonly from = new THREE.Vector3();
  private readonly to = new THREE.Vector3();
  private readonly head = new THREE.Vector3();
  private readonly backFrom = new THREE.Vector3();
  private readonly rope: THREE.Line;
  private readonly ropePos: THREE.BufferAttribute;
  private grapnel: THREE.Object3D | null = null;
  private grapnelOf = "";
  private tick = 0;
  private readonly flights: { obj: THREE.Object3D; from: THREE.Vector3; t: number; spin: THREE.Vector3 }[] = [];

  constructor(private readonly ctx: GameContext) {
    this.ropePos = new THREE.BufferAttribute(new Float32Array(ROPE_POINTS * 3), 3);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", this.ropePos);
    this.rope = new THREE.Line(geo, new THREE.LineBasicMaterial({ color: 0xcdb98e }));
    this.rope.name = "hook_line";
    this.rope.frustumCulled = false;
    this.rope.visible = false;
    ctx.scene.add(this.rope);
  }

  /** Thrown, reeling or on its way back: the viewmodel's grapnel isn't at the muzzle. */
  get out(): boolean {
    return this.phase !== "ready";
  }

  /** Reeling something in. */
  get reeling(): boolean {
    return this.phase === "reel";
  }

  /** Drops everything (leaving a place). */
  reset(): void {
    if (this.phase === "reel" && this.target?.pull === "reel") this.target.state = "afloat";
    this.phase = "ready";
    this.target = null;
    this.aim = null;
    this.rope.visible = false;
    if (this.grapnel) this.grapnel.visible = false;
    for (const f of this.flights) f.obj.removeFromParent();
    this.flights.length = 0;
  }

  /**
   * `throwing`: the throw was pressed this frame. `muzzle`: where the line
   * leaves the bolt-caster, in world space. Returns true on a throw (the
   * viewmodel kicks).
   */
  update(dt: number, o: { targets: readonly Hookable[]; muzzle: THREE.Vector3; throwing: boolean; stats: HookStats; flotsam: Flotsam | null }): boolean {
    const ctx = this.ctx;
    this.cooldown = Math.max(0, this.cooldown - dt);
    this.dress(o.stats);
    this.aim = this.phase === "ready" ? this.pick(o.targets, o.stats.range) : null;
    let thrown = false;
    if (o.throwing && this.phase === "ready" && this.cooldown <= 0) {
      if (ctx.player.water === "swimming" || this.aim?.state === "blocked") ctx.sfx.denied();
      else {
        this.launch(o.muzzle, this.aim?.state === "ok" ? this.aim.target : null, o.stats.range);
        thrown = true;
      }
    }

    if (this.phase === "out") {
      this.t += dt;
      const k = Math.min(1, this.t / this.dur);
      this.head.copy(this.from).lerp(this.target ? this.target.at : this.to, k);
      this.head.y += this.arc * 4 * k * (1 - k);
      if (k >= 1) this.arrive(o.stats);
    } else if (this.phase === "reel") this.reel(dt, o.stats, o.flotsam);
    else if (this.phase === "back") {
      this.t += dt;
      const k = Math.min(1, this.t / BACK_TIME);
      this.head.copy(this.backFrom).lerp(o.muzzle, k * k);
      if (k >= 1) {
        this.phase = "ready";
        this.target = null;
      }
    }
    this.flyPieces(dt);
    this.draw(o.muzzle);
    return thrown;
  }

  /** What the crosshair is on: the best target within HOOK.assist of the aim line, in sight. */
  private pick(targets: readonly Hookable[], range: number): HookAim | null {
    const ctx = this.ctx;
    const eye = ctx.player.eye;
    const dir = ctx.player.aim();
    let best: Hookable | null = null;
    let bestScore = Infinity;
    for (const h of targets) {
      if (!h.live) continue;
      tmp.copy(h.at).sub(eye);
      const along = tmp.dot(dir);
      if (along < 1) continue;
      const off = Math.sqrt(Math.max(0, tmp.lengthSq() - along * along));
      const reach = h.radius + HOOK.assist;
      if (off > reach) continue;
      // Nearest to the aim line first; distance breaks ties.
      const score = off / reach + along * 0.004;
      if (score >= bestScore) continue;
      if (ctx.level.collider.blocked(eye, tmp2.copy(h.at).setY(h.at.y + 0.3))) continue;
      best = h;
      bestScore = score;
    }
    if (!best) return null;
    if (best.at.distanceTo(eye) > range) return { target: best, state: "far", reason: "Out of reach" };
    const why = best.blocked(ctx);
    return why ? { target: best, state: "blocked", reason: why } : { target: best, state: "ok", reason: null };
  }

  /** Off it goes: to a target, or along the aim to wherever it comes down. */
  private launch(muzzle: THREE.Vector3, target: Hookable | null, range: number): void {
    const ctx = this.ctx;
    this.from.copy(muzzle);
    this.target = target;
    if (target) this.to.copy(target.at);
    else {
      const eye = ctx.player.eye;
      const dir = ctx.player.aim();
      const hit = ctx.level.collider.raycast(eye, dir, range);
      let reach = hit ? hit.distance : range;
      // Over the water, it comes down where the aim meets the sea.
      const wy = ctx.tide.waterY;
      if (dir.y < -0.01 && eye.y > wy) reach = Math.min(reach, (wy - eye.y) / dir.y);
      this.to.copy(eye).addScaledVector(dir, reach);
      if (!hit && reach >= range) {
        const ground = ctx.level.collider.groundHeight(this.to.x, this.to.z, this.to.y + 1, 60);
        this.to.y = Math.max(wy, ground);
      }
    }
    const dist = this.from.distanceTo(this.to);
    this.dur = Math.max(0.12, dist / HOOK.throwSpeed);
    this.arc = Math.min(2.6, dist * 0.09);
    this.head.copy(this.from);
    this.phase = "out";
    this.t = 0;
    this.cooldown = HOOK.cooldown;
    ctx.sfx.hookThrow();
  }

  private arrive(stats: HookStats): void {
    const ctx = this.ctx;
    const t = this.target;
    if (t && t.live && !t.blocked(ctx)) {
      if (t.pull === "reel") {
        t.state = "hooked";
        this.phase = "reel";
        this.tick = 0;
        ctx.sfx.hookBite(t.at);
        if (t.floating) ctx.effects.splash(t.at, 10);
        return;
      }
      const pieces = t.yank(ctx, Math.random() < stats.double ? 2 : 1);
      for (const obj of pieces) {
        ctx.scene.add(obj);
        this.flights.push({ obj, from: obj.position.clone(), t: 0, spin: new THREE.Vector3(Math.random() * 6 - 3, Math.random() * 6 - 3, Math.random() * 6 - 3) });
      }
      ctx.sfx.hookCrack(t.at);
      ctx.effects.burst(t.at, FX_COLORS.smoke, 16);
      this.back();
      return;
    }
    // A miss, or what it was thrown at went first.
    if (this.head.y <= ctx.tide.waterY + 0.15) {
      ctx.effects.splash(this.head, 14);
      ctx.sfx.splash(this.head);
    } else {
      ctx.effects.burst(this.head, FX_COLORS.smoke, 8);
      ctx.sfx.hookThud(this.head);
    }
    this.back();
  }

  private back(): void {
    this.phase = "back";
    this.t = 0;
    this.backFrom.copy(this.head);
  }

  /** Hauls the piece on the line toward you: across the water, over the sand, and up into your hands. */
  private reel(dt: number, stats: HookStats, flotsam: Flotsam | null): void {
    const ctx = this.ctx;
    const p = this.target;
    if (!p || p.pull !== "reel" || p.state !== "hooked" || !flotsam) {
      this.back();
      return;
    }
    const me = ctx.player.position;
    const dx = me.x - p.at.x;
    const dz = me.z - p.at.z;
    const dist = Math.hypot(dx, dz);
    if (dist < HOOK.catchAt) {
      flotsam.take(p, ctx);
      this.phase = "ready";
      this.target = null;
      return;
    }
    if (dist > stats.range + SLIP) {
      flotsam.release(p, ctx);
      ctx.hud.toast("The line slipped.", "info", 2);
      this.back();
      return;
    }
    const step = Math.min(dist - HOOK.catchAt * 0.9, (stats.reel / FLOTSAM[p.id].weight) * dt);
    p.at.x += (dx / dist) * step;
    p.at.z += (dz / dist) * step;
    p.yaw = THREE.MathUtils.lerp(p.yaw, Math.atan2(dx, dz), Math.min(1, dt * 2));
    // On the water, or dragged over the sand; the last few metres, up off the ground toward you.
    const draft = FLOTSAM[p.id].draft;
    const floor = flotsam.ground(ctx, p.at.x, p.at.z);
    p.floating = ctx.tide.waterY - floor >= draft;
    const surface = p.floating ? ctx.tide.waterY : floor + draft * 0.5;
    const lift = THREE.MathUtils.smoothstep(4 - dist, 0, 2.5);
    p.at.y = THREE.MathUtils.lerp(surface, Math.max(surface, me.y + 0.7), lift);
    this.head.copy(p.at).setY(p.at.y + 0.25);
    this.tick -= dt;
    if (this.tick <= 0) {
      this.tick = TICK;
      ctx.sfx.reelTick();
    }
  }

  /** Torn-off pieces fly to you, tumbling, and are gone into the satchel. */
  private flyPieces(dt: number): void {
    const me = this.ctx.player.eye;
    me.y -= 0.6;
    for (let i = this.flights.length - 1; i >= 0; i--) {
      const f = this.flights[i]!;
      f.t += dt / HOOK.yankFlight;
      const k = Math.min(1, f.t);
      f.obj.position.lerpVectors(f.from, me, k * k);
      f.obj.position.y += 1.4 * 4 * k * (1 - k);
      f.obj.rotation.x += f.spin.x * dt;
      f.obj.rotation.y += f.spin.y * dt;
      f.obj.rotation.z += f.spin.z * dt;
      f.obj.scale.multiplyScalar(1 - dt * 1.2);
      if (k >= 1) {
        f.obj.removeFromParent();
        this.flights.splice(i, 1);
      }
    }
  }

  /** The grapnel for the best hook you own. */
  private dress(stats: HookStats): void {
    const tier = stats.gear?.replace("hook_", "") ?? "rope";
    if (tier === this.grapnelOf) return;
    this.grapnelOf = tier;
    this.grapnel?.removeFromParent();
    this.grapnel = this.ctx.assets.clone("viewmodels.glb", `VM_grapnel_${tier}`);
    if (!this.grapnel) return;
    this.grapnel.scale.setScalar(GRAPNEL_SCALE);
    this.grapnel.visible = false;
    this.grapnel.traverse((o) => (o.castShadow = true));
    this.ctx.scene.add(this.grapnel);
  }

  /** The line from the muzzle to the grapnel: slack in flight, taut on a catch. */
  private draw(muzzle: THREE.Vector3): void {
    const shown = this.phase !== "ready";
    this.rope.visible = shown;
    if (this.grapnel) this.grapnel.visible = shown;
    if (!shown) return;
    const dist = muzzle.distanceTo(this.head);
    const slack = this.phase === "reel" ? 0.015 : this.phase === "out" ? 0.06 * (1 - Math.min(1, this.t / this.dur)) + 0.02 : 0.05;
    for (let i = 0; i < ROPE_POINTS; i++) {
      const u = i / (ROPE_POINTS - 1);
      tmp.copy(muzzle).lerp(this.head, u).addScaledVector(DOWN, slack * dist * 4 * u * (1 - u));
      this.ropePos.setXYZ(i, tmp.x, tmp.y, tmp.z);
    }
    this.ropePos.needsUpdate = true;
    const g = this.grapnel;
    if (!g) return;
    g.position.copy(this.head);
    // Its tines (-Z) lead the way out; on a catch it hangs from the line toward you.
    if (this.phase === "out") g.lookAt(tmp.copy(this.head).sub(this.from).negate().add(this.head));
    else g.lookAt(tmp.copy(muzzle));
  }
}
