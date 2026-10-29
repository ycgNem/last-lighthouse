import * as THREE from "three";
import type { GameContext } from "../game/Context";
import { FX_COLORS } from "../fx/Effects";
import { Enemy, type HitSphere } from "./Enemy";

// A drowned lantern possessed by the Gloom. Floats, blinks to a new spot
// around you (listen for the chime), brightens for half a second, then fires
// two aimed shots. Weak, but slippery.

const FLOAT = 2.4;

export class LanternWisp extends Enemy {
  private bob = Math.random() * 10;
  private shotsLeft = 0;
  private blinkTo = new THREE.Vector3();

  hitSpheres(): HitSphere[] {
    if (this.state === "blinkOut" || this.state === "blinkIn") return [];
    const c = this.root.position;
    return [{ center: new THREE.Vector3(c.x, c.y, c.z), radius: 0.5 }];
  }

  override center(): THREE.Vector3 {
    return this.root.position.clone();
  }

  protected override onHurt(dir: THREE.Vector3): void {
    this.velocity.addScaledVector(dir, 1.5);
  }

  private hover(dt: number, ctx: GameContext): void {
    const p = this.root.position;
    const g = ctx.level.collider.groundHeight(p.x, p.z, p.y + 2, 20);
    const base = Math.max(g, ctx.tide.waterY);
    p.y = THREE.MathUtils.damp(p.y, base + FLOAT + Math.sin(this.bob * 1.7) * 0.25, 4, dt);
    p.x += this.velocity.x * dt;
    p.z += this.velocity.z * dt;
    this.velocity.multiplyScalar(Math.exp(-3 * dt));
  }

  private pickBlink(ctx: GameContext): boolean {
    for (let i = 0; i < 8; i++) {
      const a = Math.random() * Math.PI * 2;
      const r = 8 + Math.random() * 4;
      const c = ctx.player.position.clone().add(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r));
      if (c.distanceTo(this.home) > 22) continue;
      const g = ctx.level.collider.groundHeight(c.x, c.z, c.y + 8, 20);
      if (g === -Infinity) continue;
      c.y = Math.max(g, ctx.tide.waterY) + FLOAT;
      if (ctx.level.collider.blocked(c, ctx.player.chest)) continue;
      this.blinkTo.copy(c);
      return true;
    }
    return false;
  }

  protected think(dt: number, ctx: GameContext): void {
    this.bob += dt;
    const { dir, dist } = this.toPlayer(ctx);
    const atk = this.def.attacks[0]!;
    const sees = dist < this.def.aggroRange && this.seesPlayer(ctx);
    if (sees) this.engaged = true;
    if (this.state !== "blinkOut" && this.state !== "blinkIn") this.hover(dt, ctx);

    switch (this.state) {
      case "idle":
      case "chase": {
        if (!this.engaged || this.retreating) break;
        this.face(dir, 4, dt);
        if (this.ready()) {
          if (sees && dist < this.def.aggroRange) {
            this.setState("windup");
            ctx.sfx.windup(this.center(), atk.windup, 2);
          } else if (this.pickBlink(ctx)) {
            this.setState("blinkOut");
            ctx.sfx.blink(this.center());
          }
        }
        if (dist > this.def.aggroRange * 1.8) this.engaged = false;
        break;
      }
      case "windup": {
        this.face(dir, 6, dt);
        this.threat = Math.min(1, this.stateTime / atk.windup);
        if (this.stateTime >= atk.windup) {
          this.shotsLeft = atk.projectile!.count;
          this.setState("fire");
        }
        break;
      }
      case "fire": {
        if (this.shotsLeft > 0 && this.stateTime >= (atk.projectile!.count - this.shotsLeft) * 0.16) {
          this.shoot(ctx);
          this.shotsLeft--;
        }
        if (this.shotsLeft === 0) this.setState("recover");
        break;
      }
      case "recover": {
        this.threat = Math.max(0, this.threat - dt * 3);
        if (this.stateTime >= atk.recover) {
          this.cooldown = 0.6 + Math.random() * 0.8;
          if (this.pickBlink(ctx)) {
            this.setState("blinkOut");
            ctx.sfx.blink(this.center());
          } else this.setState("chase");
        }
        break;
      }
      case "blinkOut": {
        this.model.scale.setScalar(Math.max(0.01, 1 - this.stateTime / 0.18));
        if (this.stateTime >= 0.18) {
          ctx.effects.burst(this.center(), FX_COLORS.seaGreen, 12);
          this.root.position.copy(this.blinkTo);
          ctx.effects.burst(this.center(), FX_COLORS.seaGreen, 12);
          this.setState("blinkIn");
        }
        break;
      }
      case "blinkIn": {
        this.model.scale.setScalar(Math.min(1, this.stateTime / 0.2));
        if (this.stateTime >= 0.2) {
          this.model.scale.setScalar(1);
          this.cooldown = 0.5;
          this.setState("chase");
        }
        break;
      }
    }
  }

  private shoot(ctx: GameContext): void {
    const atk = this.def.attacks[0]!;
    const p = atk.projectile!;
    const from = this.center();
    // Lead the player slightly so strafing in a straight line isn't free.
    const target = ctx.player.chest.addScaledVector(ctx.player.velocity, 0.25);
    const d = target.sub(from).normalize();
    d.applyAxisAngle(new THREE.Vector3(0, 1, 0), THREE.MathUtils.degToRad((Math.random() - 0.5) * p.spreadDeg));
    ctx.projectiles.fireEnemy(from, d.multiplyScalar(p.speed), p.radius, atk.damage);
    ctx.sfx.orb(from);
  }

  /** Weak to light: the Flare snuffs its glow and it sinks, wobbling, until it gathers itself. */
  protected override reel(dt: number, ctx: GameContext): void {
    this.model.scale.setScalar(1);
    const p = this.root.position;
    const g = ctx.level.collider.groundHeight(p.x, p.z, p.y + 2, 20);
    const base = Math.max(g, ctx.tide.waterY);
    p.y = THREE.MathUtils.damp(p.y, base + FLOAT * 0.45, 2.5, dt);
    this.velocity.multiplyScalar(Math.exp(-4 * dt));
    p.x += this.velocity.x * dt;
    p.z += this.velocity.z * dt;
    this.model.rotation.z = Math.sin(this.stateTime * 9) * 0.25;
  }

  protected animate(dt: number, _ctx: GameContext): void {
    const cage = this.part("cage");
    if (cage) cage.rotation.y += dt * (this.dazzled > 0 ? 0.15 : 0.8 + this.threat * 4);
    for (let i = 0; i < 4; i++) {
      const t = this.part(`tendril_${i}`);
      if (t) {
        t.rotation.x = Math.sin(this.bob * 3 + i) * 0.3;
        t.rotation.z = Math.cos(this.bob * 2.4 + i * 1.3) * 0.3;
      }
    }
    const core = this.part("core");
    if (core) core.scale.setScalar(1 + this.threat * 0.5);
  }

  protected override dying(dt: number, ctx: GameContext): void {
    this.root.position.y -= dt * 3;
    super.dying(dt, ctx);
  }
}
