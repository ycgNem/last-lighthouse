import * as THREE from "three";
import type { GameContext } from "../game/Context";
import { FX_COLORS } from "../fx/Effects";
import { Enemy, type HitSphere } from "./Enemy";

// Scuttles sideways toward you, rears up with glowing claws (0.6 s) while a
// strip on the ground shows exactly where it will go, lunges 5 m in a straight
// line, then is stuck for a moment. Dash sideways; punish the recovery.

const LUNGE_SPEED = 17;
const stripGeo = new THREE.PlaneGeometry(1.1, 5.4).rotateX(-Math.PI / 2).translate(0, 0.08, 3.1);

export class BrineCrab extends Enemy {
  private readonly lungeDir = new THREE.Vector3();
  private lungeHit = false;
  private strafe = Math.random() < 0.5 ? -1 : 1;
  private phase = Math.random() * 10;
  private readonly strip: THREE.Mesh;
  private wanderTarget = new THREE.Vector3();

  constructor(...args: ConstructorParameters<typeof Enemy>) {
    super(...args);
    this.strip = new THREE.Mesh(
      stripGeo,
      new THREE.MeshBasicMaterial({ color: FX_COLORS.seaGreen, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending }),
    );
    this.root.add(this.strip);
    this.wanderTarget.copy(this.home);
  }

  hitSpheres(): HitSphere[] {
    const p = this.root.position;
    return [{ center: new THREE.Vector3(p.x, p.y + 0.5, p.z), radius: 0.75 }];
  }

  protected think(dt: number, ctx: GameContext): void {
    const { dir, dist } = this.toPlayer(ctx);
    const def = this.def.attacks[0]!;
    const fromHome = this.root.position.distanceTo(this.home);

    switch (this.state) {
      case "idle":
      case "wander": {
        if (this.position.distanceTo(this.wanderTarget) < 1 || this.stateTime > 5) {
          const a = Math.random() * Math.PI * 2;
          this.wanderTarget.copy(this.home).add(new THREE.Vector3(Math.cos(a) * 3, 0, Math.sin(a) * 3));
          this.setState("wander");
        }
        const w = this.wanderTarget.clone().sub(this.position).setY(0);
        this.walk(dt, ctx, w.lengthSq() > 0.5 ? w.normalize() : w.set(0, 0, 0), 1.2);
        if (w.lengthSq() > 0.01) this.face(w, 3, dt);
        if (!this.retreating && ((dist < this.def.aggroRange && this.seesPlayer(ctx)) || this.engaged)) {
          this.setState("chase");
          ctx.sfx.crabClick(this.center());
        }
        break;
      }
      case "chase": {
        if (fromHome > 24 || this.retreating) {
          this.engaged = false;
          this.walk(dt, ctx, this.home.clone().sub(this.position).setY(0).normalize(), this.def.moveSpeed);
          if (fromHome < 3) this.setState("idle");
          break;
        }
        // Crabs approach at an angle, weaving side to side.
        const side = new THREE.Vector3(-dir.z, 0, dir.x).multiplyScalar(this.strafe * 0.6 * Math.sin(this.stateTime * 1.7));
        const wish = dir.clone().multiplyScalar(dist > this.def.keepDistance ? 1 : -0.3).add(side).normalize();
        this.walk(dt, ctx, wish, this.def.moveSpeed);
        this.face(dir, 6, dt);
        if (dist < 6.5 && this.ready() && this.seesPlayer(ctx)) {
          this.setState("windup");
          ctx.sfx.windup(this.center(), def.windup, 1.4);
        }
        if (dist > this.def.aggroRange * 1.6 && !this.engaged) this.setState("idle");
        break;
      }
      case "windup": {
        this.walk(dt, ctx, new THREE.Vector3(), 0, 30);
        // Track the player for most of the windup, then commit.
        if (this.stateTime < def.windup * 0.75) {
          this.face(dir, 5, dt);
          this.lungeDir.copy(this.facing);
        }
        this.threat = Math.min(1, this.stateTime / def.windup);
        if (this.stateTime >= def.windup) {
          this.setState("lunge");
          this.lungeHit = false;
          ctx.sfx.crabClick(this.center());
        }
        break;
      }
      case "lunge": {
        this.threat = 1;
        this.velocity.copy(this.lungeDir).multiplyScalar(LUNGE_SPEED);
        this.walk(dt, ctx, this.lungeDir, LUNGE_SPEED, 200);
        const p = ctx.player;
        if (!this.lungeHit && p.distanceToBody(this.center()) < 1.05) {
          this.lungeHit = true;
          ctx.hurtPlayer(def.damage, this.center());
        }
        if (this.stateTime >= 5 / LUNGE_SPEED) {
          this.setState("recover");
          this.velocity.set(0, 0, 0);
          ctx.effects.splash(this.position, 8);
        }
        break;
      }
      case "recover": {
        this.threat = 0;
        this.walk(dt, ctx, new THREE.Vector3(), 0, 30);
        if (this.stateTime >= def.recover) {
          this.cooldown = 0.8 + Math.random() * 0.6;
          this.strafe = -this.strafe;
          this.setState("chase");
        }
        break;
      }
    }
    if (this.state !== "windup" && this.state !== "lunge") this.threat = Math.max(0, this.threat - dt * 4);
  }

  protected animate(dt: number, ctx: GameContext): void {
    this.phase += dt;
    const moving = Math.min(1, Math.hypot(this.velocity.x, this.velocity.z) / 2.5);
    const t = this.phase * 14;
    for (let i = 0; i < 3; i++) {
      for (const [s, sign] of [["l", -1], ["r", 1]] as const) {
        const leg = this.part(`leg_${s}${i}`);
        if (!leg) continue;
        const ph = t + i * 2.1 + (sign > 0 ? Math.PI : 0);
        leg.rotation.x = Math.sin(ph) * 0.4 * moving;
        leg.rotation.z = sign * Math.max(0, Math.cos(ph)) * 0.25 * moving;
      }
    }
    const rear = this.state === "windup" ? Math.min(1, this.stateTime / this.def.attacks[0]!.windup) : this.state === "lunge" ? 0.6 : 0;
    const stuck = this.state === "recover" ? 1 : 0;
    for (const [name, sign] of [["claw_l", -1], ["claw_r", 1]] as const) {
      const claw = this.part(name);
      if (!claw) continue;
      claw.rotation.x = -rear * 0.9 + stuck * 0.35;
      claw.rotation.y = sign * (0.15 + Math.sin(ctx.time * 5 + sign) * 0.08 * (1 - rear));
    }
    this.model.rotation.x = -rear * 0.35 + stuck * 0.1;
    this.model.position.y = Math.abs(Math.sin(t * 0.5)) * 0.04 * moving;
    (this.strip.material as THREE.MeshBasicMaterial).opacity = this.state === "windup" ? 0.12 + rear * 0.35 : 0;
    this.strip.visible = this.state === "windup";
    // Point the strip along the committed lunge, independent of small turns.
    this.strip.rotation.y = this.state === "windup" ? Math.atan2(this.lungeDir.x, this.lungeDir.z) - this.root.rotation.y : 0;
  }
}
