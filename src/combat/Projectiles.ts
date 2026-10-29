import * as THREE from "three";
import type { GameContext } from "../game/Context";
import { FX_COLORS } from "../fx/Effects";

// Pooled projectiles. Player bolts are fast amber streaks; enemy orbs are slow,
// large, sea-green and haloed so they're readable against water and sky.

export interface HitResult {
  point: THREE.Vector3;
  weak: boolean;
}

/** Anything a bolt can hit (enemies). */
export interface Hittable {
  readonly alive: boolean;
  /** Intersection of the segment a→b (swept by `radius`) with the target. */
  hitTest(a: THREE.Vector3, b: THREE.Vector3, radius: number): HitResult | null;
  hurt(amount: number, dir: THREE.Vector3, weak: boolean, ctx: GameContext): void;
}

type Kind = "bolt" | "orb" | "mortar";

interface Shot {
  kind: Kind;
  active: boolean;
  pos: THREE.Vector3;
  prev: THREE.Vector3;
  vel: THREE.Vector3;
  radius: number;
  damage: number;
  life: number;
  gravity: number;
  pierce: number;
  hits: Set<Hittable>;
  mesh: THREE.Object3D;
  /** Mortars: blast radius on landing. */
  blast: number;
}

const boltGeo = new THREE.CylinderGeometry(0.035, 0.035, 0.9, 6).rotateX(Math.PI / 2);
const orbGeo = new THREE.SphereGeometry(1, 14, 10);
const UP = new THREE.Vector3(0, 0, 1);
const tmp = new THREE.Vector3();
const dir = new THREE.Vector3();

export class Projectiles {
  readonly group = new THREE.Group();
  /** Enemies, refreshed by the world each frame. */
  targets: Hittable[] = [];
  private readonly shots: Shot[] = [];
  // Brighter than white on purpose: bolts and orbs are light sources, so they keep their colour
  // through the tone mapping and pick up a bloom halo.
  private readonly boltMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(0xffc46b).multiplyScalar(2.6) });
  private readonly orbMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(FX_COLORS.seaGreen).multiplyScalar(1.6) });
  private readonly haloMat = new THREE.MeshBasicMaterial({ color: FX_COLORS.seaGreen, transparent: true, opacity: 0.28, depthWrite: false, blending: THREE.AdditiveBlending });
  /**
   * High-contrast shots: a pale body inside a dark rim, so an orb reads by its outline and
   * value, not just its hue. The body stays below the bloom threshold, or the glow would wash
   * the rim out.
   */
  private readonly rimMat = new THREE.MeshBasicMaterial({ color: 0x05090c, side: THREE.BackSide });
  private readonly orbFlatMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(FX_COLORS.seaGreen).lerp(new THREE.Color(0xffffff), 0.35) });
  private contrast = false;

  private take(kind: Kind): Shot {
    let s = this.shots.find((x) => !x.active && x.kind === kind);
    if (!s) {
      let mesh: THREE.Object3D;
      if (kind === "bolt") mesh = new THREE.Mesh(boltGeo, this.boltMat);
      else {
        mesh = new THREE.Group();
        const body = new THREE.Mesh(orbGeo, this.orbMat);
        body.name = "body";
        mesh.add(body);
        const halo = new THREE.Mesh(orbGeo, this.haloMat);
        halo.scale.setScalar(1.8);
        halo.name = "halo";
        mesh.add(halo);
        const rim = new THREE.Mesh(orbGeo, this.rimMat);
        rim.scale.setScalar(1.3);
        rim.name = "rim";
        mesh.add(rim);
        this.applyContrast(mesh);
      }
      s = { kind, active: false, pos: new THREE.Vector3(), prev: new THREE.Vector3(), vel: new THREE.Vector3(), radius: 0, damage: 0, life: 0, gravity: 0, pierce: 0, hits: new Set(), mesh, blast: 0 };
      this.shots.push(s);
    }
    s.active = true;
    s.hits.clear();
    s.mesh.visible = true;
    this.group.add(s.mesh);
    return s;
  }

  setContrast(on: boolean): void {
    this.contrast = on;
    for (const s of this.shots) if (s.kind !== "bolt") this.applyContrast(s.mesh);
  }

  private applyContrast(mesh: THREE.Object3D): void {
    for (const c of mesh.children) {
      if (c.name === "halo") c.visible = !this.contrast;
      else if (c.name === "rim") c.visible = this.contrast;
      else if (c.name === "body") (c as THREE.Mesh).material = this.contrast ? this.orbFlatMat : this.orbMat;
    }
  }

  firePlayer(origin: THREE.Vector3, direction: THREE.Vector3, speed: number, damage: number, pierce: number): void {
    const s = this.take("bolt");
    s.pos.copy(origin);
    s.prev.copy(origin);
    s.vel.copy(direction).multiplyScalar(speed);
    s.radius = 0.06;
    s.damage = damage;
    s.life = 1.6;
    s.gravity = 0;
    s.pierce = pierce;
    s.mesh.position.copy(origin);
    s.mesh.quaternion.setFromUnitVectors(UP, direction);
  }

  fireEnemy(origin: THREE.Vector3, vel: THREE.Vector3, radius: number, damage: number, opts: { gravity?: number; life?: number; blast?: number } = {}): void {
    const kind: Kind = opts.blast ? "mortar" : "orb";
    const s = this.take(kind);
    s.pos.copy(origin);
    s.prev.copy(origin);
    s.vel.copy(vel);
    s.radius = radius;
    s.damage = damage;
    s.life = opts.life ?? 5;
    s.gravity = opts.gravity ?? 0;
    s.pierce = 0;
    s.blast = opts.blast ?? 0;
    s.mesh.position.copy(origin);
    s.mesh.scale.setScalar(radius);
  }

  update(dt: number, ctx: GameContext): void {
    for (const s of this.shots) {
      if (!s.active) continue;
      s.life -= dt;
      if (s.life <= 0) {
        this.kill(s);
        continue;
      }
      s.prev.copy(s.pos);
      s.vel.y -= s.gravity * dt;
      s.pos.addScaledVector(s.vel, dt);
      s.mesh.position.copy(s.pos);
      if (s.kind === "bolt") s.mesh.quaternion.setFromUnitVectors(UP, dir.copy(s.vel).normalize());

      // Level geometry.
      dir.subVectors(s.pos, s.prev);
      const len = dir.length();
      const wall = len > 1e-6 ? ctx.level.collider.raycast(s.prev, dir.divideScalar(len), len + s.radius * 0.5) : null;

      if (s.kind === "bolt") {
        for (const t of this.targets) {
          if (!t.alive || s.hits.has(t)) continue;
          const hit = t.hitTest(s.prev, s.pos, s.radius);
          if (!hit) continue;
          if (wall && wall.point.distanceTo(s.prev) < hit.point.distanceTo(s.prev)) continue;
          s.hits.add(t);
          t.hurt(s.damage, tmp.copy(s.vel).normalize(), hit.weak, ctx);
          ctx.effects.sparks(hit.point, hit.weak ? 0xffffff : FX_COLORS.amber, hit.weak ? 18 : 10);
          ctx.hud.hitMarker(hit.weak);
          ctx.sfx.hitEnemy(hit.point, hit.weak);
          if (--s.pierce < 0) {
            this.kill(s);
            break;
          }
        }
        if (!s.active) continue;
        if (wall) {
          ctx.effects.sparks(wall.point, FX_COLORS.amber, 8);
          this.kill(s);
        }
        continue;
      }

      // Enemy orbs and mortars.
      const p = ctx.player;
      if (s.kind === "orb" && p.invulnerable <= 0 && Math.min(p.distanceToBody(s.pos), p.distanceToBody(s.prev)) < s.radius + 0.35) {
        ctx.hurtPlayer(s.damage, s.prev.clone());
        ctx.effects.burst(s.pos, FX_COLORS.seaGreen, 16);
        this.kill(s);
        continue;
      }
      const inWater = s.pos.y < ctx.tide.waterY - 0.1;
      if (wall || inWater) {
        const at = wall ? wall.point : s.pos;
        if (s.kind === "mortar") {
          ctx.effects.burst(at, FX_COLORS.seaGreen, 40);
          ctx.effects.ring(at.clone().setY(at.y + 0.1), FX_COLORS.seaGreen, 0.3, s.blast, 0.35);
          ctx.sfx.boom(at);
          if (p.invulnerable <= 0 && p.distanceToBody(at) < s.blast) ctx.hurtPlayer(s.damage, at.clone());
        } else {
          ctx.effects.burst(at, FX_COLORS.seaGreen, 10);
        }
        if (inWater) ctx.effects.splash(at, 10);
        this.kill(s);
      }
    }
  }

  private kill(s: Shot): void {
    s.active = false;
    s.mesh.visible = false;
    s.mesh.removeFromParent();
  }

  clear(): void {
    for (const s of this.shots) if (s.active) this.kill(s);
  }
}
