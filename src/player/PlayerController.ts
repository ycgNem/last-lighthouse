import * as THREE from "three";
import { BALANCE } from "../data/balance";
import { WATER_DEPTH } from "../data/tide";
import { clamp, damp } from "../core/math";
import type { Input } from "../core/Input";
import type { DynamicBox, StaticCollider } from "../physics/StaticCollider";

export interface PlayerEnv {
  collider: StaticCollider;
  /** Buoyant platforms; you can stand on them and they carry you. */
  dynamics: readonly DynamicBox[];
  waterY: number;
  /** Safe ground for the anti-trap current. */
  anchors: readonly THREE.Vector3[];
  sensitivity: number;
  dashCharges: number;
  dashCooldownMul: number;
  /** Movement multiplier (eating slows you). */
  speedMul: number;
  /** No walking or dashing (fishing, menus). Gravity still applies. */
  rooted: boolean;
}

export type WaterState = "dry" | "wading" | "swimming";

const P = BALANCE.player;
const D = P.dash;
export const BODY_HEIGHT = 1.8;
/** Radians per second with the cursor at the very edge (free-look fallback only). */
const EDGE_TURN_RATE = 2.2;
/** Jump still works this long after walking off an edge. */
const COYOTE_TIME = 0.12;

const segment = new THREE.Line3();
const delta = new THREE.Vector3();
const normal = new THREE.Vector3();
const DOWN = new THREE.Vector3(0, -1, 0);
const probe = new THREE.Vector3();

/** Metres a dash has covered `t` seconds in: its speed falls in a straight line from `peak` to `exit`. */
function dashCovered(t: number, peak: number, exit: number): number {
  return peak * t + ((exit - peak) * t * t) / (2 * D.duration);
}

export class PlayerController {
  /** Feet position. */
  readonly position = new THREE.Vector3();
  readonly velocity = new THREE.Vector3();
  yaw = 0;
  pitch = 0;
  onGround = false;
  water: WaterState = "dry";
  hp = 100;
  maxHp = 100;

  dashCharges = 1;
  private dashRecharge = 0;
  private dashCooldown: number = D.cooldown;
  /** Seconds into the current dash, or -1 when not dashing. */
  private dashT = -1;
  private dashBuffer = 0;
  private dashGrounded = false;
  private readonly dashDir = new THREE.Vector3();
  invulnerable = 0;
  private swimTime = 0;
  private sinceGround = 0;
  private bobPhase = 0;
  bobOffset = 0;
  /** 0..1 through a dash and easing off after; the camera widens with it. */
  dashKick = 0;
  /** -1..1, how far the current dash goes to the right (+) or left; the camera leans into it. */
  dashSide = 0;
  /** 0..1, decays after landing; the camera dips. */
  landKick = 0;

  onRescued: ((to: THREE.Vector3) => void) | null = null;
  onDash: (() => void) | null = null;
  onJump: (() => void) | null = null;
  onLand: ((speed: number) => void) | null = null;

  spawn(at: THREE.Vector3, yaw = 0): void {
    this.position.copy(at);
    this.velocity.set(0, 0, 0);
    this.yaw = yaw;
    this.pitch = 0;
    this.swimTime = 0;
    this.dashT = -1;
  }

  get eye(): THREE.Vector3 {
    return new THREE.Vector3(this.position.x, this.position.y + P.eyeHeight + this.bobOffset - this.landKick * 0.08, this.position.z);
  }

  /** Centre of the body, for enemy aiming and hit tests. */
  get chest(): THREE.Vector3 {
    return new THREE.Vector3(this.position.x, this.position.y + 1.2, this.position.z);
  }

  forward(out = new THREE.Vector3()): THREE.Vector3 {
    return out.set(-Math.sin(this.yaw), 0, -Math.cos(this.yaw));
  }

  /** Full 3D aim direction from the camera. */
  aim(out = new THREE.Vector3()): THREE.Vector3 {
    const c = Math.cos(this.pitch);
    return out.set(-Math.sin(this.yaw) * c, Math.sin(this.pitch), -Math.cos(this.yaw) * c);
  }

  /** Distance from a point to the player's capsule axis (for hit tests). */
  distanceToBody(p: THREE.Vector3): number {
    const y = clamp(p.y, this.position.y + P.radius, this.position.y + BODY_HEIGHT - P.radius);
    return Math.hypot(p.x - this.position.x, p.y - y, p.z - this.position.z);
  }

  update(dt: number, input: Input, env: PlayerEnv): void {
    const m = input.consumeMouse();
    const k = 0.0022 * env.sensitivity;
    this.yaw -= m.dx * k;
    this.yaw -= input.edgeTurn() * EDGE_TURN_RATE * env.sensitivity * dt;
    this.pitch = clamp(this.pitch - m.dy * k, -1.5, 1.5);

    // Wish direction in world space.
    const fwd = this.forward();
    const right = new THREE.Vector3(-fwd.z, 0, fwd.x);
    const wish = new THREE.Vector3();
    if (!env.rooted) {
      if (input.held("forward")) wish.add(fwd);
      if (input.held("back")) wish.sub(fwd);
      if (input.held("right")) wish.add(right);
      if (input.held("left")) wish.sub(right);
      if (wish.lengthSq() > 0) wish.normalize();
      this.updateDash(dt, input, env, wish, fwd);
    } else {
      this.dashT = -1;
    }

    const depth = env.waterY - this.position.y;
    this.water = depth > WATER_DEPTH.swim ? "swimming" : depth > WATER_DEPTH.wade ? "wading" : "dry";
    const waterMul = this.water === "swimming" ? P.swimSpeedMul : this.water === "wading" ? P.wadeSpeedMul : 1;

    const dashing = this.dashT >= 0;
    if (dashing) {
      // Fast off the mark, easing to walking pace by the end: exactly `distance`
      // whatever the frame rate, then straight back to walking with no slide.
      const exit = P.walkSpeed * waterMul * env.speedMul;
      const peak = (2 * D.distance) / D.duration - exit;
      const a = this.dashT;
      const b = Math.min(a + dt, D.duration);
      const speed = dt > 0 ? (dashCovered(b, peak, exit) - dashCovered(a, peak, exit) + exit * (a + dt - b)) / dt : peak;
      this.velocity.x = this.dashDir.x * speed;
      this.velocity.z = this.dashDir.z * speed;
      const u = b / D.duration;
      this.dashKick = damp(this.dashKick, 1 - u * 0.5, 25, dt);
      this.dashT = a + dt >= D.duration ? -1 : a + dt;
    } else {
      const control = this.onGround || this.water !== "dry" ? 1 : P.airControl;
      const target = wish.multiplyScalar(P.walkSpeed * waterMul * env.speedMul);
      const a = P.accel * control * dt;
      this.velocity.x += clamp(target.x - this.velocity.x, -a, a);
      this.velocity.z += clamp(target.z - this.velocity.z, -a, a);
    }

    // Vertical.
    this.sinceGround = this.onGround ? 0 : this.sinceGround + dt;
    if (this.water === "swimming") {
      const targetY = env.waterY - WATER_DEPTH.swimFeet;
      this.velocity.y = damp(this.velocity.y, (targetY - this.position.y) * 3, 6, dt);
      this.swimTime += dt;
    } else {
      this.swimTime = 0;
      if (!env.rooted && input.pressed("jump") && this.sinceGround < COYOTE_TIME && this.velocity.y <= 0.1) {
        this.velocity.y = P.jumpSpeed;
        this.sinceGround = COYOTE_TIME;
        this.onJump?.();
      }
      // A dash holds you nearly level instead of dropping (rising still slows as normal).
      this.velocity.y -= P.gravity * (dashing && this.velocity.y <= 0 ? D.fallHold : 1) * dt;
    }

    const fallSpeed = -this.velocity.y;
    const wasGrounded = this.onGround;
    this.moveAndCollide(dt, env);
    if (dashing && this.dashGrounded && !this.onGround && this.velocity.y <= 0) this.stickToGround(env);
    if (!wasGrounded && this.onGround && fallSpeed > 4) {
      this.landKick = clamp(fallSpeed / 14, 0.2, 1);
      this.onLand?.(fallSpeed);
    }

    // Anti-trap: never leave the player stuck in deep water or falling forever.
    if (this.swimTime > WATER_DEPTH.rescueAfter || this.position.y < -40) this.rescue(env.anchors);

    // Head bob.
    const planar = Math.hypot(this.velocity.x, this.velocity.z);
    if (this.onGround && planar > 0.5 && !dashing) {
      this.bobPhase += dt * planar * 1.9;
      this.bobOffset = Math.sin(this.bobPhase * 2) * 0.035;
    } else {
      this.bobOffset = damp(this.bobOffset, 0, 10, dt);
    }

    this.invulnerable = Math.max(0, this.invulnerable - dt);
    if (!dashing) this.dashKick = damp(this.dashKick, 0, 7, dt);
    this.dashSide = this.dashDir.dot(normal.set(Math.cos(this.yaw), 0, -Math.sin(this.yaw))) * this.dashKick;
    this.landKick = damp(this.landKick, 0, 9, dt);
  }

  /** Keeps a dash along the ground on it going downhill, rather than launching off the slope. */
  private stickToGround(env: PlayerEnv): void {
    const p = this.position;
    const hit = env.collider.raycast(probe.set(p.x, p.y + 0.3, p.z), DOWN, 0.3 + D.stick);
    if (!hit || (hit.face?.normal.y ?? 0) < 0.5) return;
    p.y = hit.point.y;
    this.velocity.y = 0;
    this.onGround = true;
  }

  private updateDash(dt: number, input: Input, env: PlayerEnv, wish: THREE.Vector3, fwd: THREE.Vector3): void {
    this.dashCharges = Math.min(this.dashCharges, env.dashCharges);
    this.dashCooldown = D.cooldown * env.dashCooldownMul;
    if (this.dashCharges < env.dashCharges) {
      this.dashRecharge += dt;
      if (this.dashRecharge >= this.dashCooldown) {
        this.dashCharges++;
        this.dashRecharge = 0;
      }
    }
    // A press a moment early (mid-dash, or just before a charge returns) still counts.
    this.dashBuffer = input.pressed("dash") ? D.buffer : Math.max(0, this.dashBuffer - dt);
    if (this.dashBuffer > 0 && this.dashCharges > 0 && this.dashT < 0) {
      this.dashBuffer = 0;
      this.dashCharges--;
      this.dashT = 0;
      this.invulnerable = Math.max(this.invulnerable, D.iframes);
      this.dashDir.copy(wish.lengthSq() > 0 ? wish : fwd);
      this.dashGrounded = this.onGround;
      // Dashing out of a fall levels you out.
      if (this.velocity.y < 0) this.velocity.y = 0;
      this.onDash?.();
    }
  }

  /** 0..1 progress of the dash recharge, for the HUD. */
  get dashRechargeFraction(): number {
    return this.dashRecharge / this.dashCooldown;
  }

  private moveAndCollide(dt: number, env: PlayerEnv): void {
    // Sub-step so a dash (~33 m/s) can't tunnel through thin walls.
    const travel = this.velocity.length() * dt;
    const steps = Math.max(1, Math.ceil(travel / 0.3));
    const sdt = dt / steps;
    const r = P.radius;
    this.onGround = false;
    for (let i = 0; i < steps; i++) {
      this.position.addScaledVector(this.velocity, sdt);

      segment.start.set(this.position.x, this.position.y + r, this.position.z);
      segment.end.set(this.position.x, this.position.y + BODY_HEIGHT - r, this.position.z);
      env.collider.resolveCapsule(segment, r);
      delta.set(segment.start.x - this.position.x, segment.start.y - r - this.position.y, segment.start.z - this.position.z);

      // Pushed up more than gravity pulled us down this step: we're standing on something.
      const grounded = delta.y > Math.abs(sdt * this.velocity.y * 0.25) && delta.y > 0;
      this.position.add(delta);
      if (grounded) {
        this.onGround = true;
        if (this.velocity.y < 0) this.velocity.y = 0;
      } else if (delta.lengthSq() > 1e-10) {
        // Slide along whatever we hit instead of sticking to it.
        normal.copy(delta).normalize();
        const into = this.velocity.dot(normal);
        if (into < 0) this.velocity.addScaledVector(normal, -into);
      }

      this.resolveDynamics(env.dynamics);
    }
  }

  private resolveDynamics(dynamics: readonly DynamicBox[]): void {
    const r = P.radius;
    for (const { box: b } of dynamics) {
      const p = this.position;
      if (p.x < b.min.x - r || p.x > b.max.x + r || p.z < b.min.z - r || p.z > b.max.z + r) continue;
      const top = b.max.y;
      const overTop = p.x > b.min.x - 0.15 && p.x < b.max.x + 0.15 && p.z > b.min.z - 0.15 && p.z < b.max.z + 0.15;
      if (overTop && p.y >= top - 0.45 && p.y <= top + 0.12 && this.velocity.y <= 0.5) {
        p.y = top;
        if (this.velocity.y < 0) this.velocity.y = 0;
        this.onGround = true;
        continue;
      }
      if (p.y + BODY_HEIGHT < b.min.y || p.y > top - 0.45) continue;
      // Side contact: push out along the shallowest axis.
      const pushes = [b.max.x + r - p.x, p.x - (b.min.x - r), b.max.z + r - p.z, p.z - (b.min.z - r)];
      const i = pushes.indexOf(Math.min(...pushes));
      if (i === 0) p.x = b.max.x + r;
      else if (i === 1) p.x = b.min.x - r;
      else if (i === 2) p.z = b.max.z + r;
      else p.z = b.min.z - r;
    }
  }

  private rescue(anchors: readonly THREE.Vector3[]): void {
    let best: THREE.Vector3 | undefined;
    let bestD = Infinity;
    for (const a of anchors) {
      const d = a.distanceToSquared(this.position);
      if (d < bestD) {
        bestD = d;
        best = a;
      }
    }
    if (!best) return;
    this.position.copy(best);
    this.velocity.set(0, 0, 0);
    this.swimTime = 0;
    this.onRescued?.(best);
  }
}
