import * as THREE from "three";
import type { Assets } from "../core/Assets";
import { damp } from "../core/math";
import { collapseMaterials } from "../world/Batch";
import type { GearId } from "../data/ids";
import { bestGear } from "../systems/progression";
import { findNamed } from "../world/Level";

// First-person hands: bolt-caster on the right, the keeper's lantern on the
// left, the rod when fishing. Rendered in its own pass over the world so it
// never clips into walls. The salvage hook's reel clamps under the
// bolt-caster's stock and its grapnel sits loaded at the muzzle, so the
// bolt-caster stays up even at home, where it's only the hook's launcher.

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
  /** The hook's reel and grapnel per tier (rope, iron, brass), and the ones on the bolt-caster now. */
  private readonly reels = new Map<string, THREE.Object3D>();
  private readonly grapnels = new Map<string, THREE.Object3D>();
  private reel: THREE.Object3D | null = null;
  private grapnel: THREE.Object3D | null = null;
  private hookOut = false;
  private readonly lanternLight = new THREE.PointLight(0xffc98a, 1.2, 2.5, 1.5);
  private sway = new THREE.Vector2();
  private recoil = 0;
  private lower = 0;
  private bob = 0;
  private fishing = 0;
  /** 1 at the moment of a Lantern Flare: the lantern thrusts forward and blazes. */
  private flareKick = 0;

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
    for (const tier of ["rope", "iron", "brass"]) {
      const reel = assets.clone("viewmodels.glb", `VM_reel_${tier}`);
      const grapnel = assets.clone("viewmodels.glb", `VM_grapnel_${tier}`);
      if (reel) this.reels.set(tier, reel);
      if (grapnel) this.grapnels.set(tier, grapnel);
    }
    for (const m of [...this.weapons.values(), ...this.rods.values(), ...this.reels.values(), ...this.grapnels.values(), this.lantern]) collapseMaterials(m);
    this.scene.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh) m.frustumCulled = false;
    });
  }

  /** Shows the best weapon, hook and rod the player owns. */
  equip(gear: readonly GearId[]): void {
    const weapon = gear.includes("lamplighter") ? "VM_lamplighter" : gear.includes("boltcaster_mk2") ? "VM_boltcaster_mk2" : "VM_boltcaster_mk1";
    if (weapon !== this.weaponId && this.weapons.has(weapon)) {
      this.weapon.removeFromParent();
      this.weapon = this.weapons.get(weapon)!;
      this.scene.add(this.weapon);
      this.weaponId = weapon;
    }
    // The best hook's reel under the stock, its grapnel loaded at the muzzle.
    const tier = bestGear(gear, "hook")?.replace("hook_", "") ?? null;
    this.reel?.removeFromParent();
    this.grapnel?.removeFromParent();
    this.reel = tier ? (this.reels.get(tier) ?? null) : null;
    this.grapnel = tier ? (this.grapnels.get(tier) ?? null) : null;
    if (this.reel) (findNamed(this.weapon, "reel") ?? this.weapon).add(this.reel);
    if (this.grapnel) {
      (findNamed(this.weapon, "muzzle") ?? this.weapon).add(this.grapnel);
      this.grapnel.visible = !this.hookOut;
    }
    const rodId = gear.includes("rod_reinforced") ? "VM_rod_reinforced" : "VM_rod_basic";
    for (const r of this.rods.values()) r.visible = false;
    this.rod = this.rods.get(rodId) ?? null;
  }

  kick(): void {
    this.recoil = Math.min(1.4, this.recoil + 1);
  }

  flare(): void {
    this.flareKick = 1;
  }

  /** The grapnel's off the muzzle while the hook's out. */
  setHookOut(out: boolean): void {
    this.hookOut = out;
    if (this.grapnel) this.grapnel.visible = !out;
  }

  /** World-space position of the bolt-caster's muzzle (where the hook's line leaves). */
  muzzle(camera: THREE.Camera): THREE.Vector3 {
    const at = findNamed(this.weapon, "muzzle");
    const local = at ? at.getWorldPosition(new THREE.Vector3()) : new THREE.Vector3(0.22, -0.16, -0.75);
    return local.applyMatrix4(camera.matrixWorld);
  }

  /** World-space position of the rod tip (for the fishing line). */
  rodTip(camera: THREE.Camera): THREE.Vector3 {
    const tip = this.rod?.getObjectByName("tip");
    const local = tip ? tip.getWorldPosition(new THREE.Vector3()) : new THREE.Vector3(0.2, 0.3, -1.4);
    // The viewmodel camera sits at the origin looking down -Z, like the world camera; map across.
    return local.applyMatrix4(camera.matrixWorld);
  }

  /** `lowered`: the bolt-caster put away (the chapter's end). `calm`: the reduced-motion setting (no sway or bob, a gentler flare). */
  update(dt: number, o: { mouseDX: number; mouseDY: number; speed: number; lowered: boolean; fishing: boolean; aspect: number; time: number; lanternFlicker: number; calm: boolean }): void {
    this.camera.aspect = o.aspect;
    this.camera.updateProjectionMatrix();
    this.sway.x = damp(this.sway.x, THREE.MathUtils.clamp(-o.mouseDX * 0.0009, -0.06, 0.06), 10, dt);
    this.sway.y = damp(this.sway.y, THREE.MathUtils.clamp(o.mouseDY * 0.0009, -0.06, 0.06), 10, dt);
    this.recoil = damp(this.recoil, 0, 14, dt);
    this.lower = damp(this.lower, o.lowered || o.fishing ? 1 : 0, 6, dt);
    this.fishing = damp(this.fishing, o.fishing ? 1 : 0, 8, dt);
    this.flareKick = damp(this.flareKick, 0, 5, dt);
    this.bob += dt * o.speed * 1.9;
    const motion = o.calm ? 0 : 1;
    if (o.calm) this.sway.set(0, 0);
    const bx = Math.sin(this.bob) * 0.008 * Math.min(1, o.speed / 5) * motion;
    const by = Math.abs(Math.cos(this.bob)) * 0.01 * Math.min(1, o.speed / 5) * motion;

    const w = this.weapon;
    w.position.copy(WEAPON_POS).add(new THREE.Vector3(this.sway.x + bx, this.sway.y - by - this.lower * 0.32, this.recoil * 0.06));
    w.rotation.set(this.recoil * 0.12 - this.lower * 0.6, this.sway.x * 2, -this.lower * 0.2);

    const fk = this.flareKick * (o.calm ? 0.4 : 1);
    this.lantern.position.copy(LANTERN_POS).add(new THREE.Vector3(this.sway.x * 0.8 - bx + fk * 0.06, this.sway.y * 0.8 - by + fk * 0.07, -fk * 0.12));
    this.lantern.rotation.set(-fk * 0.35, 0, Math.sin(o.time * 1.7) * 0.06 * motion + this.sway.x * 1.5);
    this.lanternLight.position.copy(this.lantern.position).add(new THREE.Vector3(0.05, 0.02, 0.1));
    this.lanternLight.intensity = 1.0 + o.lanternFlicker * 0.3 + this.flareKick * 6;

    if (this.rod) {
      this.rod.visible = this.fishing > 0.02;
      this.rod.position.copy(ROD_POS).add(new THREE.Vector3(0, (1 - this.fishing) * -0.4, 0));
      this.rod.rotation.set(0.55 * this.fishing + Math.sin(o.time * 2) * 0.01, -0.1, 0);
    }
  }
}
