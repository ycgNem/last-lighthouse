import * as THREE from "three";
import type { GameContext } from "../game/Context";
import { Enemy, type HitSphere } from "./Enemy";

// Barely moves. Inhales (0.7 s, throat swells and glows, rising tone), then
// spits a slow fan of five orbs. Strafe through the gaps or break line of sight.

export class DrownedSpitter extends Enemy {
  private sway = Math.random() * 10;

  hitSpheres(): HitSphere[] {
    const p = this.root.position;
    return [
      { center: new THREE.Vector3(p.x, p.y + 0.9, p.z), radius: 0.55 },
      { center: new THREE.Vector3(p.x, p.y + 1.7, p.z), radius: 0.45 },
    ];
  }

  private throatWorld(): THREE.Vector3 {
    const t = this.part("throat");
    return t ? t.getWorldPosition(new THREE.Vector3()) : this.root.position.clone().add(new THREE.Vector3(0, 1.4, 0));
  }

  protected think(dt: number, ctx: GameContext): void {
    const { dir, dist } = this.toPlayer(ctx);
    const atk = this.def.attacks[0]!;
    const sees = dist < this.def.aggroRange && this.seesPlayer(ctx, this.throatWorld());
    if (sees) this.engaged = true;

    switch (this.state) {
      case "idle":
      case "chase": {
        if (this.engaged && !this.retreating) {
          this.face(dir, 2.2, dt);
          // Shuffle to keep its distance.
          const want = dist < this.def.keepDistance - 3 ? -1 : dist > this.def.keepDistance + 6 ? 1 : 0;
          this.walk(dt, ctx, dir.clone().multiplyScalar(want), this.def.moveSpeed, 4);
          if (sees && this.ready()) {
            this.setState("windup");
            ctx.sfx.windup(this.throatWorld(), atk.windup, 0.8);
          }
          if (dist > this.def.aggroRange * 1.5) this.engaged = false;
        } else {
          this.walk(dt, ctx, new THREE.Vector3(), 0, 4);
        }
        break;
      }
      case "windup": {
        this.face(dir, 2.5, dt);
        this.threat = Math.min(1, this.stateTime / atk.windup);
        if (this.stateTime >= atk.windup) {
          this.fire(ctx);
          this.setState("recover");
        }
        break;
      }
      case "recover": {
        this.threat = Math.max(0, this.threat - dt * 3);
        if (this.stateTime >= atk.recover) {
          this.cooldown = 0.8 + Math.random() * 1.2;
          this.setState("chase");
        }
        break;
      }
    }
  }

  private fire(ctx: GameContext): void {
    const atk = this.def.attacks[0]!;
    const p = atk.projectile!;
    const from = this.throatWorld();
    const aim = ctx.player.chest.sub(from).normalize();
    const flat = new THREE.Vector3(aim.x, 0, aim.z).normalize();
    const pitch = Math.asin(THREE.MathUtils.clamp(aim.y, -0.6, 0.6));
    for (let i = 0; i < p.count; i++) {
      const a = THREE.MathUtils.degToRad(-p.spreadDeg / 2 + (p.spreadDeg * i) / (p.count - 1));
      const d = flat.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), a);
      d.y = Math.tan(pitch);
      ctx.projectiles.fireEnemy(from, d.normalize().multiplyScalar(p.speed), p.radius, atk.damage);
    }
    ctx.sfx.orb(from);
  }

  protected animate(dt: number, _ctx: GameContext): void {
    this.sway += dt;
    const k = this.state === "windup" ? this.threat : 0;
    this.model.rotation.z = Math.sin(this.sway * 0.9) * 0.05;
    const head = this.part("head");
    if (head) head.rotation.x = -k * 0.55 + Math.sin(this.sway * 1.3) * 0.05;
    const throat = this.part("throat");
    if (throat) throat.scale.setScalar(1 + k * 0.7);
    for (const [name, s] of [["arm_l", -1], ["arm_r", 1]] as const) {
      const arm = this.part(name);
      if (arm) {
        arm.rotation.x = Math.sin(this.sway * 1.1 + s) * 0.12 - k * 0.4;
        arm.rotation.z = s * (0.1 + k * 0.5);
      }
    }
  }
}
