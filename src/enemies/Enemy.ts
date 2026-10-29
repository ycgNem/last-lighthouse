import * as THREE from "three";
import { uniqueMaterials } from "../core/Assets";
import { randInt } from "../core/math";
import type { EnemyDef } from "../data/enemies";
import type { EnemyId, ItemStack } from "../data/ids";
import type { HitResult, Hittable } from "../combat/Projectiles";
import type { GameContext } from "../game/Context";
import { FX_COLORS } from "../fx/Effects";
import { collapseMaterials } from "../world/Batch";

// Shared enemy behaviour: state timer, hit flash, telegraph glow, ground
// following, wall push-out, line of sight, loot and death. Subclasses only
// decide what to do (think) and how to look while doing it (animate).

export interface HitSphere {
  center: THREE.Vector3;
  radius: number;
  weak?: boolean;
}

const tmpA = new THREE.Vector3();
const tmpB = new THREE.Vector3();
const STILL = new THREE.Vector3();
const white = new THREE.Color(0xffffff);

export abstract class Enemy implements Hittable {
  readonly root = new THREE.Group();
  readonly model: THREE.Object3D;
  readonly home: THREE.Vector3;
  readonly velocity = new THREE.Vector3();
  hp: number;
  alive = true;
  /** Fully removed (death animation done, or left with the tide). */
  gone = false;
  state = "idle";
  stateTime = 0;
  cooldown = 0;
  /** 0..1 telegraph strength; drives the GLOW_ materials and HUD threat pips. */
  threat = 0;
  /** Asked to leave because the tide changed; leaves when not mid-attack. */
  retreating = false;
  /** Bosses show a health bar. */
  readonly boss: boolean = false;
  /** Seconds left reeling from a Lantern Flare. */
  dazzled = 0;
  protected engaged = false;
  private flash = 0;
  private deathT = 0;
  private readonly mats: { mat: THREE.MeshStandardMaterial; emissive: THREE.Color; intensity: number }[] = [];
  private readonly glows: THREE.MeshStandardMaterial[] = [];
  protected readonly radius: number;

  constructor(
    readonly id: EnemyId,
    readonly def: EnemyDef,
    model: THREE.Object3D,
    at: THREE.Vector3,
    radius: number,
  ) {
    this.model = model;
    this.radius = radius;
    this.hp = def.hp;
    this.home = at.clone();
    this.root.position.copy(at);
    this.root.rotation.y = Math.random() * Math.PI * 2;
    this.root.add(model);
    collapseMaterials(model, true);
    for (const mat of uniqueMaterials(model)) {
      this.mats.push({ mat, emissive: mat.emissive.clone(), intensity: mat.emissiveIntensity });
      if (mat.name.startsWith("GLOW_")) this.glows.push(mat);
    }
  }

  get position(): THREE.Vector3 {
    return this.root.position;
  }

  private shadowMeshes: THREE.Mesh[] | null = null;
  private shadowOn = true;

  /** Shadow LOD: only creatures near you cast (bosses always do). */
  castShadows(on: boolean): void {
    if (this.boss || on === this.shadowOn) return;
    this.shadowOn = on;
    if (!this.shadowMeshes) {
      this.shadowMeshes = [];
      this.root.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m.isMesh && m.castShadow) this.shadowMeshes!.push(m);
      });
    }
    for (const m of this.shadowMeshes) m.castShadow = on;
  }

  part(name: string): THREE.Object3D | undefined {
    return this.model.getObjectByName(name);
  }

  abstract hitSpheres(): HitSphere[];
  protected abstract think(dt: number, ctx: GameContext): void;
  protected abstract animate(dt: number, ctx: GameContext): void;

  setState(s: string): void {
    this.state = s;
    this.stateTime = 0;
  }

  update(dt: number, ctx: GameContext): void {
    if (!this.alive) {
      this.deathT += dt;
      this.dying(dt, ctx);
      return;
    }
    this.stateTime += dt;
    this.cooldown = Math.max(0, this.cooldown - dt);
    if (this.dazzled > 0) {
      this.dazzled -= dt;
      this.threat = 0;
      this.reel(dt, ctx);
      if (this.dazzled <= 0) this.recoverFromFlare();
    } else this.think(dt, ctx);
    this.animate(dt, ctx);
    this.applyLook(dt, ctx.time);
  }

  /**
   * The Lantern Flare's light: cancels whatever it was winding up and leaves it
   * reeling for `def.flareStagger` seconds. False if it shrugs the light off.
   */
  dazzle(ctx: GameContext): boolean {
    if (!this.alive || this.def.flareStagger <= 0 || !this.canBeDazzled()) return false;
    this.dazzled = this.def.flareStagger;
    this.threat = 0;
    this.engaged = true;
    this.setState("dazzled");
    ctx.effects.sparks(this.center(), 0xffe2a8, 10);
    return true;
  }

  /** Whether the light can reach it right now (a Lurker under the water can't be dazzled). */
  protected canBeDazzled(): boolean {
    return true;
  }

  /** What reeling looks like: by default it stops dead and shudders. */
  protected reel(dt: number, ctx: GameContext): void {
    this.walk(dt, ctx, STILL, 0, 12);
    this.model.rotation.z = Math.sin(this.stateTime * 31) * 0.08 * Math.min(1, this.dazzled);
  }

  protected recoverFromFlare(): void {
    this.dazzled = 0;
    this.model.rotation.z = 0;
    this.cooldown = Math.max(this.cooldown, 0.5);
    this.setState("chase");
  }

  private applyLook(dt: number, time: number): void {
    this.flash = Math.max(0, this.flash - dt);
    const pulse = 0.85 + 0.15 * Math.sin(time * 6);
    for (const g of this.glows) g.emissiveIntensity = (1 + this.threat * 5) * pulse;
    for (const m of this.mats) {
      if (this.flash > 0) {
        m.mat.emissive.copy(white);
        m.mat.emissiveIntensity = 1.6;
      } else if (!m.mat.name.startsWith("GLOW_")) {
        m.mat.emissive.copy(m.emissive);
        m.mat.emissiveIntensity = m.intensity;
      } else {
        m.mat.emissive.copy(m.emissive);
      }
    }
  }

  // ------------------------------------------------------------------ hits

  hitTest(a: THREE.Vector3, b: THREE.Vector3, radius: number): HitResult | null {
    if (!this.alive) return null;
    const ab = tmpA.subVectors(b, a);
    const len2 = ab.lengthSq();
    let best: HitResult | null = null;
    let bestT = Infinity;
    for (const s of this.hitSpheres()) {
      const t = len2 > 0 ? THREE.MathUtils.clamp(tmpB.subVectors(s.center, a).dot(ab) / len2, 0, 1) : 0;
      const p = a.clone().addScaledVector(ab, t);
      if (p.distanceTo(s.center) < s.radius + radius && t < bestT) {
        bestT = t;
        best = { point: p, weak: !!s.weak };
      }
    }
    return best;
  }

  hurt(amount: number, dir: THREE.Vector3, weak: boolean, ctx: GameContext): void {
    if (!this.alive) return;
    this.hp -= weak ? amount * 2 : amount;
    this.flash = 0.09;
    this.engaged = true;
    this.onHurt(dir, ctx);
    if (this.hp <= 0) this.die(ctx);
  }

  /** Knockback and aggro; bosses override to ignore knockback. */
  protected onHurt(dir: THREE.Vector3, _ctx: GameContext): void {
    this.velocity.x += dir.x * 2.5;
    this.velocity.z += dir.z * 2.5;
  }

  protected die(ctx: GameContext): void {
    this.alive = false;
    this.threat = 0;
    const at = this.center();
    ctx.effects.burst(at, FX_COLORS.seaGreen, 40);
    ctx.effects.sparks(at, 0xffffff, 12);
    ctx.sfx.enemyDie(at);
    const drops: ItemStack[] = [];
    for (const d of this.def.drops) {
      const qty = randInt(Math.random, d.min, d.max);
      if (qty > 0) drops.push({ item: d.item, qty });
    }
    ctx.loot.drop(at, drops);
    ctx.xp("combat", this.def.combatXp);
    if (this.def.grantsFlag && !ctx.state.flags.includes(this.def.grantsFlag)) ctx.state.flags.push(this.def.grantsFlag);
    ctx.bus.emit("enemy:killed", { enemy: this.id, boss: this.boss });
  }

  /** Death animation: sink and shrink. */
  protected dying(dt: number, _ctx: GameContext): void {
    const k = Math.min(1, this.deathT / 0.7);
    this.model.scale.setScalar(1 - k * 0.9);
    this.model.rotation.z += dt * 4;
    this.root.position.y -= dt * 0.8;
    if (k >= 1) this.gone = true;
  }

  // --------------------------------------------------------------- helpers

  center(): THREE.Vector3 {
    return this.root.position.clone().add(new THREE.Vector3(0, this.radius, 0));
  }

  /** Flat vector and distance to the player. */
  toPlayer(ctx: GameContext): { dir: THREE.Vector3; dist: number } {
    const d = new THREE.Vector3(ctx.player.position.x - this.root.position.x, 0, ctx.player.position.z - this.root.position.z);
    const dist = d.length();
    return { dir: dist > 1e-4 ? d.divideScalar(dist) : d.set(0, 0, 1), dist };
  }

  seesPlayer(ctx: GameContext, from?: THREE.Vector3): boolean {
    return !ctx.level.collider.blocked(from ?? this.center(), ctx.player.chest);
  }

  /** Turns toward a flat direction at `rate` rad/s. */
  face(dir: THREE.Vector3, rate: number, dt: number): void {
    const target = Math.atan2(dir.x, dir.z);
    let d = target - this.root.rotation.y;
    d = Math.atan2(Math.sin(d), Math.cos(d));
    this.root.rotation.y += THREE.MathUtils.clamp(d, -rate * dt, rate * dt);
  }

  get facing(): THREE.Vector3 {
    return new THREE.Vector3(Math.sin(this.root.rotation.y), 0, Math.cos(this.root.rotation.y));
  }

  /** Moves along the ground with friction, sliding off walls. */
  protected walk(dt: number, ctx: GameContext, wish: THREE.Vector3, speed: number, accel = 20): void {
    const a = accel * dt;
    this.velocity.x += THREE.MathUtils.clamp(wish.x * speed - this.velocity.x, -a, a);
    this.velocity.z += THREE.MathUtils.clamp(wish.z * speed - this.velocity.z, -a, a);
    const p = this.root.position;
    p.x += this.velocity.x * dt;
    p.z += this.velocity.z * dt;
    const c = tmpA.set(p.x, p.y + this.radius + 0.1, p.z);
    if (ctx.level.collider.pushSphere(c, this.radius)) {
      p.x = c.x;
      p.z = c.z;
    }
    const g = ctx.level.collider.groundHeight(p.x, p.z, p.y + 1.5, 6);
    if (g > -Infinity) p.y = THREE.MathUtils.damp(p.y, g, 20, dt);
  }

  /** True when the enemy may start a new attack (not leaving, cooled down). */
  protected ready(): boolean {
    return !this.retreating && this.cooldown <= 0;
  }

  /** Called by the encounter when the tide sends this enemy away. */
  canLeave(): boolean {
    return this.state === "idle" || this.state === "chase" || this.state === "wander" || this.state === "dazzled";
  }

  leave(ctx: GameContext): void {
    ctx.effects.splash(this.center(), 16);
    this.gone = true;
  }

  /** Removes everything this enemy added to the scene. */
  dispose(): void {
    this.root.removeFromParent();
  }
}
