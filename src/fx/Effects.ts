import * as THREE from "three";
import { softDot } from "./sprite";

// Cheap particles (one Points object) and expanding rings. Colour language:
// amber = player, sea-green = supernatural/enemy, white-gold = loot, white = water.

const CAP = 1500;

export const FX_COLORS = {
  amber: 0xffb347,
  seaGreen: 0x3dffb0,
  loot: 0xffe8a3,
  water: 0xdff3f0,
  blood: 0xc0503c,
  smoke: 0x8a8a8a,
} as const;

interface Ring {
  mesh: THREE.Mesh;
  t: number;
  dur: number;
  from: number;
  to: number;
  opacity: number;
}

export class Effects {
  readonly group = new THREE.Group();
  private readonly geo = new THREE.BufferGeometry();
  private readonly pos = new Float32Array(CAP * 3);
  private readonly col = new Float32Array(CAP * 3);
  private readonly base = new Float32Array(CAP * 3);
  private readonly vel = new Float32Array(CAP * 3);
  private readonly life = new Float32Array(CAP);
  private readonly maxLife = new Float32Array(CAP);
  private readonly grav = new Float32Array(CAP);
  private next = 0;
  private readonly rings: Ring[] = [];
  private readonly ringGeo = new THREE.RingGeometry(0.85, 1, 48);
  private readonly tmp = new THREE.Color();

  constructor() {
    this.geo.setAttribute("position", new THREE.BufferAttribute(this.pos, 3));
    this.geo.setAttribute("color", new THREE.BufferAttribute(this.col, 3));
    const points = new THREE.Points(
      this.geo,
      new THREE.PointsMaterial({ size: 0.16, map: softDot(), vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: false }),
    );
    points.frustumCulled = false;
    this.group.add(points);
    this.ringGeo.rotateX(-Math.PI / 2);
  }

  emit(at: THREE.Vector3, opts: { count: number; color: number; speed: number; life: number; gravity?: number; up?: number; spread?: number }): void {
    this.tmp.setHex(opts.color);
    for (let n = 0; n < opts.count; n++) {
      const i = this.next;
      this.next = (this.next + 1) % CAP;
      const s = opts.spread ?? 1;
      const dx = (Math.random() - 0.5) * 2 * s;
      const dy = Math.random() * (opts.up ?? 1);
      const dz = (Math.random() - 0.5) * 2 * s;
      const len = Math.hypot(dx, dy, dz) || 1;
      const v = opts.speed * (0.4 + Math.random() * 0.6);
      this.pos[i * 3] = at.x;
      this.pos[i * 3 + 1] = at.y;
      this.pos[i * 3 + 2] = at.z;
      this.vel[i * 3] = (dx / len) * v;
      this.vel[i * 3 + 1] = (dy / len) * v;
      this.vel[i * 3 + 2] = (dz / len) * v;
      this.base[i * 3] = this.tmp.r;
      this.base[i * 3 + 1] = this.tmp.g;
      this.base[i * 3 + 2] = this.tmp.b;
      this.maxLife[i] = this.life[i] = opts.life * (0.6 + Math.random() * 0.4);
      this.grav[i] = opts.gravity ?? 9;
    }
  }

  /** A spray along `dir`, spread within `halfAngle` radians (the Lantern Flare). */
  cone(at: THREE.Vector3, dir: THREE.Vector3, halfAngle: number, color: number, count: number, speed: number, life: number): void {
    this.tmp.setHex(color);
    const side = Math.abs(dir.y) < 0.95 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0);
    const u = new THREE.Vector3().crossVectors(dir, side).normalize();
    const v = new THREE.Vector3().crossVectors(dir, u);
    const d = new THREE.Vector3();
    for (let n = 0; n < count; n++) {
      const i = this.next;
      this.next = (this.next + 1) % CAP;
      const a = Math.random() * Math.PI * 2;
      const r = Math.tan(halfAngle) * Math.sqrt(Math.random());
      d.copy(dir).addScaledVector(u, Math.cos(a) * r).addScaledVector(v, Math.sin(a) * r).normalize();
      const sp = speed * (0.5 + Math.random() * 0.5);
      this.pos[i * 3] = at.x;
      this.pos[i * 3 + 1] = at.y;
      this.pos[i * 3 + 2] = at.z;
      this.vel[i * 3] = d.x * sp;
      this.vel[i * 3 + 1] = d.y * sp;
      this.vel[i * 3 + 2] = d.z * sp;
      this.base[i * 3] = this.tmp.r;
      this.base[i * 3 + 1] = this.tmp.g;
      this.base[i * 3 + 2] = this.tmp.b;
      this.maxLife[i] = this.life[i] = life * (0.6 + Math.random() * 0.4);
      this.grav[i] = -0.6;
    }
  }

  sparks(at: THREE.Vector3, color: number, count = 12): void {
    this.emit(at, { count, color, speed: 6, life: 0.35, gravity: 12, up: 1.2 });
  }

  splash(at: THREE.Vector3, count = 18): void {
    this.emit(at, { count, color: FX_COLORS.water, speed: 4, life: 0.7, gravity: 14, up: 3, spread: 0.5 });
  }

  burst(at: THREE.Vector3, color: number, count = 30): void {
    this.emit(at, { count, color, speed: 7, life: 0.8, gravity: 4, up: 1 });
  }

  /** A ring, so its shader can be compiled before the first one. */
  samples(): THREE.Object3D[] {
    return [new THREE.Mesh(this.ringGeo, ringMaterial(0xffffff, 1))];
  }

  ring(at: THREE.Vector3, color: number, from: number, to: number, dur: number, opacity = 0.8): void {
    const mesh = new THREE.Mesh(this.ringGeo, ringMaterial(color, opacity));
    mesh.position.copy(at);
    mesh.scale.setScalar(from);
    this.group.add(mesh);
    this.rings.push({ mesh, t: 0, dur, from, to, opacity });
  }

  update(dt: number): void {
    for (let i = 0; i < CAP; i++) {
      if (this.life[i]! <= 0) {
        this.col[i * 3] = this.col[i * 3 + 1] = this.col[i * 3 + 2] = 0;
        continue;
      }
      this.life[i]! -= dt;
      this.vel[i * 3 + 1]! -= this.grav[i]! * dt;
      this.pos[i * 3]! += this.vel[i * 3]! * dt;
      this.pos[i * 3 + 1]! += this.vel[i * 3 + 1]! * dt;
      this.pos[i * 3 + 2]! += this.vel[i * 3 + 2]! * dt;
      const k = Math.max(0, this.life[i]! / this.maxLife[i]!);
      this.col[i * 3] = this.base[i * 3]! * k;
      this.col[i * 3 + 1] = this.base[i * 3 + 1]! * k;
      this.col[i * 3 + 2] = this.base[i * 3 + 2]! * k;
    }
    this.geo.attributes.position!.needsUpdate = true;
    this.geo.attributes.color!.needsUpdate = true;

    for (let i = this.rings.length - 1; i >= 0; i--) {
      const r = this.rings[i]!;
      r.t += dt;
      const k = Math.min(1, r.t / r.dur);
      r.mesh.scale.setScalar(r.from + (r.to - r.from) * k);
      (r.mesh.material as THREE.MeshBasicMaterial).opacity = r.opacity * (1 - k);
      if (k >= 1) {
        r.mesh.removeFromParent();
        (r.mesh.material as THREE.Material).dispose();
        this.rings.splice(i, 1);
      }
    }
  }

  clear(): void {
    this.life.fill(0);
    for (const r of this.rings) {
      r.mesh.removeFromParent();
      (r.mesh.material as THREE.Material).dispose();
    }
    this.rings.length = 0;
  }
}

function ringMaterial(color: number, opacity: number): THREE.MeshBasicMaterial {
  return new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
}
