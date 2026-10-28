import * as THREE from "three";
import type { GameContext } from "../game/Context";
import { FX_COLORS } from "../fx/Effects";
import { Enemy, type HitSphere } from "./Enemy";

// Saltmere's guardian: a colossus of fused hulls and chain that rises from the
// sea beside the beacon rock. Three attacks, all with long tells:
//  * Chain Sweep — the chain arm lifts and a glowing sector shows where it will
//    sweep. Jump over it or dash through it. Afterwards the heart lantern in
//    its chest is exposed for two seconds (double damage).
//  * Brine Mortar — vents glow, five globs are lobbed; a closing ring marks
//    each landing spot 1.2 s ahead.
//  * Undertow (below half health) — the sea drags you outward for three
//    seconds while it spits fans of orbs. Walk inward and strafe.
// Leave the arena and it sinks back and recovers a quarter of its health.

const SWEEP_ARC = THREE.MathUtils.degToRad(120);
const SWEEP_MIN = 4;
const SWEEP_MAX = 27;
const MORTAR_FLIGHT = 1.2;
const MORTAR_GRAVITY = 14;

type Attack = "sweep" | "mortar" | "undertow";

export class WreckGuardian extends Enemy {
  override readonly boss = true;
  awake = false;
  private rise = 0;
  private attack: Attack = "sweep";
  private lastAttack: Attack | null = null;
  private sweepDir = new THREE.Vector3();
  private sweepHit = false;
  private volleys = 0;
  private heartOpen = 0;
  private outside = 0;
  private healed = false;
  private readonly sector: THREE.Mesh;
  private readonly arena: THREE.Vector3;

  constructor(...args: ConstructorParameters<typeof Enemy>) {
    super(...args);
    this.root.rotation.y = 0;
    const geo = new THREE.RingGeometry(SWEEP_MIN, SWEEP_MAX, 48, 1, -SWEEP_ARC / 2, SWEEP_ARC).rotateX(-Math.PI / 2);
    this.sector = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: FX_COLORS.seaGreen, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
    this.sector.visible = false;
    this.arena = this.home.clone();
    this.model.position.y = -12;
  }

  /** Where the fight happens; set by the encounter from the level's FX_arena point. */
  setArena(center: THREE.Vector3): void {
    this.arena.copy(center);
  }

  get heartExposed(): boolean {
    return this.heartOpen > 0;
  }

  hitSpheres(): HitSphere[] {
    if (!this.awake || this.rise < 0.8) return [];
    const toWorld = (x: number, y: number, z: number) => this.model.localToWorld(new THREE.Vector3(x, y, z));
    const spheres: HitSphere[] = [
      { center: toWorld(0, 2.4, -0.2), radius: 2.3 },
      { center: toWorld(0, 4.8, -0.2), radius: 2.0 },
      { center: toWorld(0, 6.8, -0.2), radius: 1.3 },
    ];
    // The heart is checked first so a shot through it counts as a weak hit.
    if (this.heartOpen > 0) spheres.unshift({ center: toWorld(0, 3.4, 0.55), radius: 1.15, weak: true });
    return spheres;
  }

  protected override onHurt(): void {
    // Immovable.
  }

  override canLeave(): boolean {
    return false;
  }

  wake(ctx: GameContext): void {
    if (this.awake || !this.alive) return;
    this.awake = true;
    this.healed = false;
    this.setState("rising");
    ctx.sfx.roar(this.center());
    ctx.hud.banner("The Wreck Guardian rises", 3);
  }

  protected think(dt: number, ctx: GameContext): void {
    this.root.position.y = ctx.tide.waterY;
    if (!this.sector.parent) this.root.parent?.add(this.sector);
    this.heartOpen = Math.max(0, this.heartOpen - dt);
    const player = ctx.player;
    const toArena = new THREE.Vector3(this.arena.x - this.root.position.x, 0, this.arena.z - this.root.position.z).normalize();

    // Leaving the arena: it sinks and recovers.
    const inArena = Math.hypot(player.position.x - this.arena.x, player.position.z - this.arena.z) < 19;
    this.outside = inArena ? 0 : this.outside + dt;
    if (this.awake && this.outside > 3 && this.state !== "rising") {
      this.awake = false;
      this.threat = 0;
      this.sector.visible = false;
      if (!this.healed) {
        this.hp = Math.min(this.def.hp, this.hp + this.def.hp * 0.25);
        this.healed = true;
      }
      this.setState("sinking");
    }

    switch (this.state) {
      case "idle":
        break;
      case "sinking":
        this.rise = Math.max(0, this.rise - dt * 0.6);
        if (this.rise <= 0) this.setState("idle");
        break;
      case "rising":
        this.rise = Math.min(1, this.rise + dt / 3);
        this.face(toArena, 1, dt);
        if (this.stateTime % 0.3 < dt) ctx.effects.splash(this.root.position.clone().add(new THREE.Vector3((Math.random() - 0.5) * 6, 0, (Math.random() - 0.5) * 4)), 30);
        if (this.rise >= 1) {
          this.setState("pause");
          this.cooldown = 1;
        }
        break;
      case "pause": {
        const { dir } = this.toPlayer(ctx);
        this.face(dir, 0.6, dt);
        const phase2 = this.hp < this.def.hp * 0.5;
        if (this.stateTime > (phase2 ? 0.9 : 1.5) && this.ready()) this.chooseAttack(ctx, phase2);
        break;
      }
      case "windup":
        this.windup(dt, ctx);
        break;
      case "act":
        this.act(dt, ctx);
        break;
      case "recover": {
        this.threat = Math.max(0, this.threat - dt * 2);
        const rec = this.def.attacks.find((a) => a.id === this.attackId())!.recover;
        if (this.stateTime >= rec) this.setState("pause");
        break;
      }
    }
  }

  private attackId(): string {
    return this.attack === "sweep" ? "chain_sweep" : this.attack === "mortar" ? "brine_mortar" : "undertow";
  }

  private chooseAttack(ctx: GameContext, phase2: boolean): void {
    const options: Attack[] = phase2 ? ["sweep", "mortar", "undertow"] : ["sweep", "mortar"];
    const pick = options.filter((a) => a !== this.lastAttack);
    this.attack = pick[Math.floor(Math.random() * pick.length)] ?? "sweep";
    this.lastAttack = this.attack;
    const atk = this.def.attacks.find((a) => a.id === this.attackId())!;
    this.setState("windup");
    if (this.attack === "sweep") {
      this.sweepDir.copy(this.toPlayer(ctx).dir);
      this.sector.position.copy(this.root.position).setY(this.arena.y + 0.08);
      this.sector.rotation.y = Math.atan2(this.sweepDir.x, this.sweepDir.z) - Math.PI / 2;
      this.sector.visible = true;
      ctx.sfx.chain(this.center());
    } else if (this.attack === "undertow") {
      ctx.sfx.roar(this.center());
    }
    ctx.sfx.windup(this.center(), atk.windup, 0.5);
  }

  private windup(dt: number, ctx: GameContext): void {
    const atk = this.def.attacks.find((a) => a.id === this.attackId())!;
    const k = Math.min(1, this.stateTime / atk.windup);
    this.threat = k;
    if (this.attack === "sweep") {
      (this.sector.material as THREE.MeshBasicMaterial).opacity = 0.1 + k * 0.3;
      this.face(this.sweepDir, 1.5, dt);
    } else {
      this.face(this.toPlayer(ctx).dir, 1.2, dt);
    }
    if (this.attack === "undertow" && this.stateTime % 0.2 < dt) {
      ctx.effects.splash(this.arena.clone().add(new THREE.Vector3((Math.random() - 0.5) * 30, 0, (Math.random() - 0.5) * 30)).setY(ctx.tide.waterY), 12);
    }
    if (k >= 1) {
      this.setState("act");
      this.sweepHit = false;
      this.volleys = 0;
      if (this.attack === "mortar") this.fireMortars(ctx);
    }
  }

  private act(dt: number, ctx: GameContext): void {
    const player = ctx.player;
    if (this.attack === "sweep") {
      const dur = 0.5;
      (this.sector.material as THREE.MeshBasicMaterial).opacity = 0.55 * (1 - this.stateTime / dur);
      if (!this.sweepHit && this.stateTime > dur * 0.3) {
        const rel = new THREE.Vector3().subVectors(player.position, this.root.position).setY(0);
        const d = rel.length();
        const angle = rel.angleTo(this.sweepDir);
        const ground = ctx.level.collider.groundHeight(player.position.x, player.position.z, player.position.y + 0.5);
        const airborne = player.position.y - ground > 0.55;
        if (d > SWEEP_MIN && d < SWEEP_MAX && angle < SWEEP_ARC / 2 && !airborne && player.invulnerable <= 0) {
          this.sweepHit = true;
          ctx.hurtPlayer(this.def.attacks[0]!.damage, this.center());
          player.velocity.addScaledVector(rel.normalize(), 6);
        }
        ctx.sfx.chain(this.center());
      }
      if (this.stateTime >= dur) {
        this.sector.visible = false;
        this.heartOpen = 2.2;
        ctx.hud.toast("Its heart is exposed!", "milestone", 2);
        this.setState("recover");
      }
    } else if (this.attack === "mortar") {
      if (this.stateTime > 0.4) this.setState("recover");
    } else {
      // Undertow: drag the player away from the arena centre while spitting fans.
      const out = new THREE.Vector3(player.position.x - this.arena.x, 0, player.position.z - this.arena.z);
      if (out.lengthSq() > 0.01) player.velocity.addScaledVector(out.normalize(), 9 * dt);
      if (this.stateTime >= this.volleys * 1.0 && this.volleys < 3) {
        this.volleys++;
        this.fan(ctx);
      }
      if (this.stateTime >= 3) this.setState("recover");
    }
  }

  private headWorld(): THREE.Vector3 {
    return this.model.localToWorld(new THREE.Vector3(0, 6.8, 0.6));
  }

  private fan(ctx: GameContext): void {
    const atk = this.def.attacks.find((a) => a.id === "undertow")!;
    const p = atk.projectile!;
    const from = this.headWorld();
    const aim = ctx.player.chest.sub(from).normalize();
    for (let i = 0; i < p.count; i++) {
      const a = THREE.MathUtils.degToRad(-p.spreadDeg / 2 + (p.spreadDeg * i) / (p.count - 1));
      const d = aim.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), a);
      ctx.projectiles.fireEnemy(from, d.multiplyScalar(p.speed), p.radius, atk.damage);
    }
    ctx.sfx.orb(from);
  }

  private fireMortars(ctx: GameContext): void {
    const atk = this.def.attacks.find((a) => a.id === "brine_mortar")!;
    const p = atk.projectile!;
    const arm = this.part("arm_r");
    const from = arm ? arm.localToWorld(new THREE.Vector3(4.3, 0, 0)) : this.headWorld();
    for (let i = 0; i < p.count; i++) {
      const target = ctx.player.position.clone();
      if (i > 0) target.add(new THREE.Vector3((Math.random() - 0.5) * 12, 0, (Math.random() - 0.5) * 12));
      const g = ctx.level.collider.groundHeight(target.x, target.z, target.y + 6, 20);
      target.y = g > -Infinity ? g : ctx.tide.waterY;
      const t = MORTAR_FLIGHT + i * 0.12;
      const vel = target.clone().sub(from).divideScalar(t);
      vel.y += 0.5 * MORTAR_GRAVITY * t;
      ctx.projectiles.fireEnemy(from, vel, p.radius, atk.damage, { gravity: MORTAR_GRAVITY, life: t + 1, blast: 1.9 });
      // Closing ring: lands when the ring reaches its smallest size.
      ctx.effects.ring(target.clone().setY(target.y + 0.08), FX_COLORS.seaGreen, 3.2, 1.9, t, 0.75);
    }
    ctx.sfx.boom(from);
  }

  protected animate(dt: number, ctx: GameContext): void {
    this.model.position.y = -12 + 12 * this.rise;
    const k = this.state === "windup" ? this.threat : 0;
    const armL = this.part("arm_l");
    if (armL) {
      if (this.attack === "sweep" && this.state === "windup") armL.rotation.z = -k * 0.9;
      else if (this.attack === "sweep" && this.state === "act") armL.rotation.y = Math.sin((this.stateTime / 0.5) * Math.PI) * 1.4 - 0.7;
      else {
        armL.rotation.z = THREE.MathUtils.damp(armL.rotation.z, Math.sin(ctx.time * 0.7) * 0.1, 4, dt);
        armL.rotation.y = THREE.MathUtils.damp(armL.rotation.y, 0, 4, dt);
      }
    }
    const armR = this.part("arm_r");
    if (armR) armR.rotation.z = this.attack === "mortar" && this.state === "windup" ? k * 0.8 : THREE.MathUtils.damp(armR.rotation.z, 0, 4, dt);
    const heart = this.part("heart");
    if (heart) heart.scale.setScalar(this.heartOpen > 0 ? 1.25 + Math.sin(ctx.time * 12) * 0.08 : 0.85);
    this.model.rotation.z = Math.sin(ctx.time * 0.4) * 0.02;
    if (this.heartOpen > 0) this.threat = Math.max(this.threat, 0.6);
  }

  override dispose(): void {
    this.sector.removeFromParent();
    super.dispose();
  }

  protected override dying(dt: number, ctx: GameContext): void {
    this.sector.visible = false;
    this.rise = Math.max(0, this.rise - dt * 0.35);
    this.model.position.y = -12 + 12 * this.rise;
    this.model.rotation.z += dt * 0.15;
    if (Math.random() < dt * 8) ctx.effects.splash(this.root.position.clone().add(new THREE.Vector3((Math.random() - 0.5) * 8, 0, (Math.random() - 0.5) * 6)), 24);
    if (this.rise <= 0) {
      this.sector.removeFromParent();
      this.gone = true;
    }
  }
}
