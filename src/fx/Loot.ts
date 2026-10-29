import * as THREE from "three";
import type { ItemStack } from "../data/ids";
import { ITEMS } from "../data/items";
import type { GameContext } from "../game/Context";
import { FX_COLORS } from "./Effects";

// Loot is white-gold, never sea-green. Two kinds:
//  * sparkles: purely visual, fly from a gathered node into the player
//  * pickups: dropped by enemies; magnetise and collect when you walk near

interface Sparkle {
  mesh: THREE.Mesh;
  from: THREE.Vector3;
  ctrl: THREE.Vector3;
  t: number;
  dur: number;
}

interface Pickup {
  mesh: THREE.Group;
  stack: ItemStack;
  vel: THREE.Vector3;
  t: number;
  settled: boolean;
  magnet: boolean;
}

const sparkleGeo = new THREE.OctahedronGeometry(0.07, 0);
const pickupGeo = new THREE.OctahedronGeometry(0.16, 0);
const haloGeo = new THREE.SphereGeometry(0.32, 10, 8);

export class Loot {
  readonly group = new THREE.Group();
  private readonly sparkles: Sparkle[] = [];
  private readonly pickups: Pickup[] = [];
  // Over-bright so they glow (and bloom) through the tone mapping.
  private readonly sparkMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(FX_COLORS.loot).multiplyScalar(2) });
  private readonly pickMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(0xffe08a).multiplyScalar(2) });
  private readonly keyMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(0xffffff).multiplyScalar(2.4) });
  private readonly haloMat = new THREE.MeshBasicMaterial({ color: 0xffd27a, transparent: true, opacity: 0.25, depthWrite: false, blending: THREE.AdditiveBlending });

  /** Visual only: `count` sparkles arc from `from` into the player. */
  burst(from: THREE.Vector3, count: number): void {
    for (let i = 0; i < Math.min(count, 12); i++) {
      const mesh = new THREE.Mesh(sparkleGeo, this.sparkMat);
      mesh.position.copy(from);
      const ctrl = from.clone().add(new THREE.Vector3((Math.random() - 0.5) * 2, 1.5 + Math.random(), (Math.random() - 0.5) * 2));
      this.group.add(mesh);
      this.sparkles.push({ mesh, from: from.clone(), ctrl, t: -i * 0.04, dur: 0.45 + Math.random() * 0.15 });
    }
  }

  /** Physical pickups that pop out of `at`. */
  drop(at: THREE.Vector3, stacks: readonly ItemStack[]): void {
    for (const s of stacks) {
      if (s.qty <= 0) continue;
      const key = ITEMS[s.item].category === "key";
      const g = new THREE.Group();
      g.add(new THREE.Mesh(pickupGeo, key ? this.keyMat : this.pickMat), new THREE.Mesh(haloGeo, this.haloMat));
      if (key) g.scale.setScalar(1.6);
      g.position.copy(at).add(new THREE.Vector3(0, 0.6, 0));
      this.group.add(g);
      const a = Math.random() * Math.PI * 2;
      this.pickups.push({ mesh: g, stack: { ...s }, vel: new THREE.Vector3(Math.cos(a) * 2.2, 4.5, Math.sin(a) * 2.2), t: 0, settled: false, magnet: false });
    }
  }

  update(dt: number, ctx: GameContext): void {
    const chest = ctx.player.chest;
    for (let i = this.sparkles.length - 1; i >= 0; i--) {
      const s = this.sparkles[i]!;
      s.t += dt;
      const k = Math.max(0, Math.min(1, s.t / s.dur));
      // Quadratic bezier from the node, over the control point, into the chest.
      const a = s.from.clone().lerp(s.ctrl, k);
      const b = s.ctrl.clone().lerp(chest, k);
      s.mesh.position.copy(a.lerp(b, k));
      s.mesh.rotation.y += dt * 8;
      if (k >= 1) {
        s.mesh.removeFromParent();
        this.sparkles.splice(i, 1);
      }
    }

    for (let i = this.pickups.length - 1; i >= 0; i--) {
      const p = this.pickups[i]!;
      p.t += dt;
      const pos = p.mesh.position;
      const d = pos.distanceTo(chest);
      if (p.t > 0.5 && d < 5) p.magnet = true;
      if (p.magnet) {
        const to = chest.clone().sub(pos);
        pos.addScaledVector(to.normalize(), Math.min(d, (6 + p.t * 4) * dt));
        if (d < 0.7) {
          const fit = ctx.give(p.stack.item, p.stack.qty);
          if (fit < p.stack.qty) {
            // Satchel full: leave the rest where it is.
            p.stack.qty -= fit;
            p.magnet = false;
            p.t = -2;
            continue;
          }
          p.mesh.removeFromParent();
          this.pickups.splice(i, 1);
        }
        continue;
      }
      if (!p.settled) {
        p.vel.y -= 14 * dt;
        pos.addScaledVector(p.vel, dt);
        const ground = ctx.level.collider.groundHeight(pos.x, pos.z, pos.y + 1) + 0.35;
        const floor = Math.max(ground, ctx.tide.waterY + 0.3);
        if (pos.y <= floor && p.vel.y < 0) {
          pos.y = floor;
          p.settled = true;
        }
      } else {
        pos.y += Math.sin(p.t * 3) * 0.003;
      }
      p.mesh.rotation.y += dt * 2;
    }
  }

  clear(): void {
    for (const s of this.sparkles) s.mesh.removeFromParent();
    for (const p of this.pickups) p.mesh.removeFromParent();
    this.sparkles.length = 0;
    this.pickups.length = 0;
  }
}
