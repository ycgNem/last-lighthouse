import * as THREE from "three";
import type { GameContext } from "../game/Context";
import { FX_COLORS } from "../fx/Effects";
import { Enemy, type HitSphere } from "./Enemy";

// High tide only. Under the surface it's just a moving wake and bubbles. If
// you're in the water (or right at its edge) it closes in, surfaces with a
// rising tone and a widening ring (0.8 s), and bites. Only hittable while up.
// Counterplay: stay out of marked deep water, or get out fast.

const SUBMERGED = -3.2;

export class TideLurker extends Enemy {
  private rise = 0;
  private bubbleT = 0;
  private bitten = false;

  hitSpheres(): HitSphere[] {
    if (this.rise < 0.6) return [];
    const p = this.root.position;
    return [{ center: new THREE.Vector3(p.x, p.y + this.model.position.y + 0.4, p.z), radius: 1.0 }];
  }

  override center(): THREE.Vector3 {
    return this.root.position.clone().add(new THREE.Vector3(0, this.model.position.y + 0.4, 0));
  }

  protected override onHurt(): void {
    // Too heavy to knock back.
  }

  private deepEnough(x: number, z: number, ctx: GameContext): boolean {
    const g = ctx.level.collider.groundHeight(x, z, ctx.tide.waterY + 2, 30);
    return g < ctx.tide.waterY - 1.2;
  }

  private swimToward(target: THREE.Vector3, speed: number, dt: number, ctx: GameContext): void {
    const p = this.root.position;
    const d = new THREE.Vector3(target.x - p.x, 0, target.z - p.z);
    if (d.lengthSq() < 0.01) return;
    d.normalize();
    const nx = p.x + d.x * speed * dt;
    const nz = p.z + d.z * speed * dt;
    if (this.deepEnough(nx, nz, ctx) && Math.hypot(nx - this.home.x, nz - this.home.z) < 14) {
      p.x = nx;
      p.z = nz;
    }
    this.face(d, 4, dt);
  }

  protected think(dt: number, ctx: GameContext): void {
    this.root.position.y = ctx.tide.waterY;
    const { dist } = this.toPlayer(ctx);
    const atk = this.def.attacks[0]!;
    const player = ctx.player;
    // Prey: anyone in the water, or standing right at the edge near the lurker.
    const prey = !this.retreating && dist < this.def.aggroRange && (player.water !== "dry" || dist < 3.2);

    switch (this.state) {
      case "idle":
      case "chase": {
        this.rise = Math.max(0, this.rise - dt * 2);
        if (prey) {
          this.swimToward(player.position, this.def.moveSpeed, dt, ctx);
          if (dist < 2.6 && this.ready()) {
            this.setState("windup");
            this.bitten = false;
            ctx.sfx.windup(this.center(), atk.windup, 0.6);
            ctx.effects.ring(this.root.position.clone().setY(ctx.tide.waterY + 0.05), FX_COLORS.seaGreen, 0.5, 2.6, atk.windup, 0.6);
          }
        } else {
          const t = ctx.time * 0.3 + this.home.x;
          this.swimToward(this.home.clone().add(new THREE.Vector3(Math.cos(t) * 5, 0, Math.sin(t) * 5)), 1.5, dt, ctx);
        }
        this.bubbleT -= dt;
        if (this.bubbleT <= 0) {
          this.bubbleT = prey ? 0.25 : 0.8;
          const b = this.root.position.clone().setY(ctx.tide.waterY + 0.05);
          ctx.effects.emit(b, { count: prey ? 6 : 3, color: 0xcfe8e2, speed: 1.2, life: 0.6, gravity: -1, up: 1, spread: 0.6 });
          if (prey) ctx.sfx.bubbles(b);
        }
        break;
      }
      case "windup": {
        this.face(this.toPlayer(ctx).dir, 6, dt);
        this.threat = Math.min(1, this.stateTime / atk.windup);
        this.rise = Math.min(1, this.stateTime / atk.windup);
        if (this.stateTime >= atk.windup) {
          this.setState("bite");
          ctx.sfx.bite(this.center());
          ctx.effects.splash(this.center(), 24);
        }
        break;
      }
      case "bite": {
        this.threat = 1;
        if (!this.bitten && this.stateTime > 0.08) {
          this.bitten = true;
          if (player.distanceToBody(this.center().add(this.facing.multiplyScalar(1.2))) < atk.reach!) ctx.hurtPlayer(atk.damage, this.center());
        }
        if (this.stateTime > 0.3) this.setState("recover");
        break;
      }
      case "recover": {
        this.threat = 0;
        if (this.stateTime >= atk.recover) {
          this.cooldown = 1.5;
          this.setState("chase");
        }
        break;
      }
    }
  }

  /** Only while it's up: the light catches it at the surface. */
  protected override canBeDazzled(): boolean {
    return this.rise >= 0.6 || this.state === "bite" || this.state === "recover";
  }

  /** It dives away from the light. */
  protected override reel(dt: number, ctx: GameContext): void {
    this.root.position.y = ctx.tide.waterY;
    this.rise = Math.max(0, this.rise - dt * 2.5);
  }

  protected animate(_dt: number, ctx: GameContext): void {
    const up = this.state === "bite" || this.state === "recover" ? 1 : this.rise;
    this.model.position.y = SUBMERGED + (0.2 - SUBMERGED) * up;
    this.model.visible = up > 0.05;
    const jaw = this.part("jaw");
    if (jaw) jaw.rotation.x = this.state === "windup" ? this.threat * 0.7 : this.state === "bite" ? 0.1 : 0.35;
    void ctx;
  }

  override canLeave(): boolean {
    return this.state !== "windup" && this.state !== "bite";
  }
}
