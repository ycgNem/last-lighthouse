import * as THREE from "three";
import type { Assets } from "../core/Assets";
import { damp } from "../core/math";
import type { GearId } from "../data/ids";

// First-person hands: bolt-caster on the right, the keeper's lantern on the
// left, the rod when fishing. Rendered in its own pass over the world so it
// never clips into walls. At home the bolt-caster lowers out of view.

const WEAPON_POS = new THREE.Vector3(0.22, -0.2, -0.42);
const LANTERN_POS = new THREE.Vector3(-0.26, -0.21, -0.44);
const ROD_POS = new THREE.Vector3(0.2, -0.26, -0.35);

function fallbackGun(): THREE.Object3D {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.09, 0.5), new THREE.MeshStandardMaterial({ color: 0x6b4f3a }));
  body.position.z = -0.15;
  const glow = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.03, 0.12), new THREE.MeshBasicMaterial({ color: 0xffc46b }));
  glow.position.set(0, 0.06, -0.08);
  g.add(body, glow);
  return g;
}

export class Viewmodel {
  readonly scene = new THREE.Scene();
  readonly camera = new THREE.PerspectiveCamera(62, 1, 0.01, 10);
  private readonly weapons = new Map<string, THREE.Object3D>();
  private weapon: THREE.Object3D;
  private weaponId = "";
  private readonly lantern: THREE.Object3D;
  private readonly rods = new Map<string, THREE.Object3D>();
  private rod: THREE.Object3D | null = null;
  private readonly lanternLight = new THREE.PointLight(0xffc98a, 1.2, 2.5, 1.5);
  private sway = new THREE.Vector2();
  private recoil = 0;
  private lower = 0;
  private bob = 0;
  private fishing = 0;

  constructor(assets: Assets) {
    this.scene.add(new THREE.HemisphereLight(0xbfd0d8, 0x2a2420, 1.4));
    const key = new THREE.DirectionalLight(0xffd6a8, 1.4);
    key.position.set(-1, 2, 1);
    this.scene.add(key, this.lanternLight);

    for (const id of ["VM_boltcaster_mk1", "VM_boltcaster_mk2", "VM_lamplighter"]) {
      const m = assets.clone("viewmodels.glb", id);
      if (m) this.weapons.set(id, m);
    }
    this.weapon = this.weapons.get("VM_boltcaster_mk1") ?? fallbackGun();
    this.scene.add(this.weapon);
    for (const id of ["VM_rod_basic", "VM_rod_reinforced"]) {
      const m = assets.clone("viewmodels.glb", id);
      if (m) {
        m.visible = false;
        this.rods.set(id, m);
        this.scene.add(m);
      }
    }
    this.lantern = assets.clone("viewmodels.glb", "VM_lantern") ?? new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.06, 0.16, 8), new THREE.MeshBasicMaterial({ color: 0xffd08a }));
    this.scene.add(this.lantern);
    this.scene.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh) m.frustumCulled = false;
    });
  }

  /** Shows the best weapon and rod the player owns. */
  equip(gear: readonly GearId[]): void {
    const weapon = gear.includes("lamplighter") ? "VM_lamplighter" : gear.includes("boltcaster_mk2") ? "VM_boltcaster_mk2" : "VM_boltcaster_mk1";
    if (weapon !== this.weaponId && this.weapons.has(weapon)) {
      this.weapon.removeFromParent();
      this.weapon = this.weapons.get(weapon)!;
      this.scene.add(this.weapon);
      this.weaponId = weapon;
    }
    const rodId = gear.includes("rod_reinforced") ? "VM_rod_reinforced" : "VM_rod_basic";
    for (const r of this.rods.values()) r.visible = false;
    this.rod = this.rods.get(rodId) ?? null;
  }

  kick(): void {
    this.recoil = Math.min(1.4, this.recoil + 1);
  }

  /** World-space position of the rod tip (for the fishing line). */
  rodTip(camera: THREE.Camera): THREE.Vector3 {
    const tip = this.rod?.getObjectByName("tip");
    const local = tip ? tip.getWorldPosition(new THREE.Vector3()) : new THREE.Vector3(0.2, 0.3, -1.4);
    // The viewmodel camera sits at the origin looking down -Z, like the world camera; map across.
    return local.applyMatrix4(camera.matrixWorld);
  }

  update(dt: number, o: { mouseDX: number; mouseDY: number; speed: number; safe: boolean; fishing: boolean; aspect: number; time: number; lanternFlicker: number }): void {
    this.camera.aspect = o.aspect;
    this.camera.updateProjectionMatrix();
    this.sway.x = damp(this.sway.x, THREE.MathUtils.clamp(-o.mouseDX * 0.0009, -0.06, 0.06), 10, dt);
    this.sway.y = damp(this.sway.y, THREE.MathUtils.clamp(o.mouseDY * 0.0009, -0.06, 0.06), 10, dt);
    this.recoil = damp(this.recoil, 0, 14, dt);
    this.lower = damp(this.lower, o.safe || o.fishing ? 1 : 0, 6, dt);
    this.fishing = damp(this.fishing, o.fishing ? 1 : 0, 8, dt);
    this.bob += dt * o.speed * 1.9;
    const bx = Math.sin(this.bob) * 0.008 * Math.min(1, o.speed / 5);
    const by = Math.abs(Math.cos(this.bob)) * 0.01 * Math.min(1, o.speed / 5);

    const w = this.weapon;
    w.position.copy(WEAPON_POS).add(new THREE.Vector3(this.sway.x + bx, this.sway.y - by - this.lower * 0.32, this.recoil * 0.06));
    w.rotation.set(this.recoil * 0.12 - this.lower * 0.6, this.sway.x * 2, -this.lower * 0.2);

    this.lantern.position.copy(LANTERN_POS).add(new THREE.Vector3(this.sway.x * 0.8 - bx, this.sway.y * 0.8 - by, 0));
    this.lantern.rotation.set(0, 0, Math.sin(o.time * 1.7) * 0.06 + this.sway.x * 1.5);
    this.lanternLight.position.copy(this.lantern.position).add(new THREE.Vector3(0.05, 0.02, 0.1));
    this.lanternLight.intensity = 1.0 + o.lanternFlicker * 0.3;

    if (this.rod) {
      this.rod.visible = this.fishing > 0.02;
      this.rod.position.copy(ROD_POS).add(new THREE.Vector3(0, (1 - this.fishing) * -0.4, 0));
      this.rod.rotation.set(0.55 * this.fishing + Math.sin(o.time * 2) * 0.01, -0.1, 0);
    }
  }
}
