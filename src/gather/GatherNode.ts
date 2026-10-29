import * as THREE from "three";
import { randInt } from "../core/math";
import { GEAR, ITEMS } from "../data/items";
import type { NodeId } from "../data/ids";
import { NODES, type NodeDef } from "../data/nodes";
import { SKILLS } from "../data/skills";
import type { GameContext } from "../game/Context";
import { FX_COLORS } from "../fx/Effects";
import { satchelCapacity } from "../systems/inventory";
import { skillLevel } from "../systems/skills";
import { collapseMaterials } from "../world/Batch";
import type { NodeMarker } from "../world/Level";

// A gatherable spot in the world: driftwood, scrap, kelp, glass, caches,
// fishing spots and the Drowned Lens. Gathering is quick: a short hold with a
// ring on the HUD, a pop, and the haul flies into you.

const rippleGeo = new THREE.RingGeometry(0.7, 0.85, 32).rotateX(-Math.PI / 2);

function makeRipple(): THREE.Group {
  const g = new THREE.Group();
  for (let i = 0; i < 3; i++) {
    const m = new THREE.Mesh(rippleGeo, new THREE.MeshBasicMaterial({ color: 0xe8fbff, transparent: true, opacity: 0.5, depthWrite: false }));
    m.userData.phase = i / 3;
    g.add(m);
  }
  // An invisible disc so the crosshair can target the spot.
  const hit = new THREE.Mesh(new THREE.CircleGeometry(1.6, 16).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ visible: false }));
  g.add(hit);
  return g;
}

export class GatherNode {
  readonly def: NodeDef;
  readonly object: THREE.Object3D;
  readonly position: THREE.Vector3;
  usesLeft: number;
  private fade = 1;
  private glintT = Math.random() * 3;
  readonly range: number;
  /** True when this node added its object to the scene itself (not part of the level). */
  private readonly owned: boolean;

  constructor(
    readonly kind: NodeId,
    marker: NodeMarker,
    ctx: GameContext,
  ) {
    this.def = NODES[kind];
    this.usesLeft = this.def.uses;
    this.position = marker.position.clone();
    this.owned = this.def.kind === "fish" || !marker.object;
    if (this.def.kind === "fish") {
      this.object = makeRipple();
      this.object.position.copy(this.position);
      ctx.scene.add(this.object);
      this.range = 10;
    } else {
      const obj = marker.object ?? ctx.assets.prop(kind === "lens_pedestal" ? "lens_pedestal" : kind) ?? new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.6, 0.8), new THREE.MeshStandardMaterial({ color: 0x8a6a4f }));
      if (!marker.object) {
        obj.position.copy(this.position);
        obj.rotation.y = marker.yaw;
        ctx.scene.add(obj);
      }
      collapseMaterials(obj);
      this.object = obj;
      this.range = 3.4;
    }
    if (this.def.keyItem && (ctx.state.keyItems.includes(this.def.keyItem) || ctx.state.stage >= 2)) this.deplete(true);
  }

  get available(): boolean {
    return this.usesLeft > 0;
  }

  private shadowMeshes: THREE.Mesh[] | null = null;
  private shadowOn = true;

  /** Shadow LOD: props far from you stop casting. */
  castShadows(on: boolean): void {
    if (on === this.shadowOn || this.def.kind === "fish") return;
    this.shadowOn = on;
    if (!this.shadowMeshes) {
      this.shadowMeshes = [];
      this.object.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m.isMesh && m.castShadow) this.shadowMeshes!.push(m);
      });
    }
    for (const m of this.shadowMeshes) m.castShadow = on;
  }

  /** Why it can't be gathered right now, or null. */
  blocked(ctx: GameContext): string | null {
    const d = this.def;
    if (this.usesLeft <= 0) return d.keyItem ? "The pedestal is empty" : null;
    if (d.tide === "low" && ctx.tide.state === "high") return `${d.name}: underwater until low tide`;
    if (d.tide === "high" && ctx.tide.state === "low") return `${d.name}: only rises at high tide`;
    if (d.skill && skillLevel(ctx.state, d.skill) < d.level) return `${d.name}: needs ${SKILLS[d.skill].name} ${d.level}`;
    if (d.requiresGear && !ctx.state.gear.some((g) => g === d.requiresGear || (GEAR[g].slot === GEAR[d.requiresGear!].slot && GEAR[g].tier > GEAR[d.requiresGear!].tier))) {
      return `${d.name}: needs a ${GEAR[d.requiresGear].name}`;
    }
    if (ctx.shrouded(this.position)) return `${d.name}: shrouded in Gloom. Flare your lantern (${ctx.keyLabel("flare")})`;
    if (ctx.player.water === "swimming") return "Can't do that while swimming";
    if (!d.keyItem && d.yields.length && !this.hasRoom(ctx)) return "Satchel full: head home to unload";
    return null;
  }

  private hasRoom(ctx: GameContext): boolean {
    const s = ctx.state;
    if (s.satchel.filter(Boolean).length < satchelCapacity(s)) return true;
    return this.def.yields.some((y) => s.satchel.some((st) => st && st.item === y.item && st.qty < ITEMS[y.item].stack));
  }

  label(ctx: GameContext): string {
    return this.blocked(ctx) ?? `${this.def.verb} ${this.def.name}`;
  }

  /** Seconds of hold-to-gather (0 for instant use, e.g. fishing). */
  holdTime(ctx: GameContext): number {
    if (this.def.kind === "fish") return 0;
    const fast = this.def.skill === "salvaging" && skillLevel(ctx.state, "salvaging") >= 9 ? 0.7 : 1;
    return this.def.gatherTime * fast;
  }

  /** Gives the yields, XP and feedback, then uses up one gather. */
  complete(ctx: GameContext): void {
    const d = this.def;
    const at = this.object.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, 0.5, 0));
    if (d.keyItem) {
      ctx.give(d.keyItem, 1, at);
      ctx.bus.emit("node:keyItem", { item: d.keyItem, at });
    }
    for (const y of d.yields) {
      const qty = randInt(Math.random, y.min, y.max);
      if (qty > 0) ctx.give(y.item, qty, at);
    }
    if (d.skill && d.xp) ctx.xp(d.skill, d.xp);
    ctx.effects.burst(at, FX_COLORS.loot, 14);
    ctx.sfx.gather();
    this.usesLeft--;
    if (this.usesLeft <= 0) this.deplete(false);
  }

  private deplete(immediate: boolean): void {
    this.usesLeft = 0;
    // A key node's stand stays; the piece tagged `part` (the lens on its pedestal) is what you took.
    if (this.def.kind === "key") this.object.traverse((o) => (o.visible = o.visible && o.userData.part === undefined));
    if (immediate) {
      this.fade = 0;
      if (this.def.kind !== "key") this.object.visible = false;
    }
  }

  update(dt: number, ctx: GameContext): void {
    if (this.def.kind === "fish") {
      this.object.position.y = ctx.tide.waterY + 0.04;
      const active = this.usesLeft > 0 && this.blocked(ctx) === null;
      const spot = skillLevel(ctx.state, "fishing") >= 3 ? 40 : 18;
      const near = 1 - THREE.MathUtils.smoothstep(this.object.position.distanceTo(ctx.player.position), spot * 0.6, spot);
      for (const c of this.object.children) {
        const mesh = c as THREE.Mesh;
        if (mesh.userData.phase === undefined) continue;
        const k = (ctx.time * 0.5 + (mesh.userData.phase as number)) % 1;
        mesh.scale.setScalar(0.6 + k * 1.6);
        (mesh.material as THREE.MeshBasicMaterial).opacity = (1 - k) * 0.55 * (active ? 1 : 0.15) * near;
      }
      return;
    }
    if (this.usesLeft <= 0 && this.fade > 0 && this.def.kind !== "key") {
      this.fade = Math.max(0, this.fade - dt * 2.5);
      this.object.scale.setScalar(Math.max(0.001, this.fade));
      if (this.fade === 0) this.object.visible = false;
      return;
    }
    // A small white-gold glint marks things you can gather.
    if (this.usesLeft > 0 && this.def.kind !== "key") {
      this.glintT -= dt;
      if (this.glintT <= 0) {
        this.glintT = 1.6 + Math.random() * 1.4;
        if (this.blocked(ctx) === null && this.object.position.distanceTo(ctx.player.position) < 30) {
          ctx.effects.emit(this.object.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, 0.6, 0)), { count: 3, color: FX_COLORS.loot, speed: 0.6, life: 0.9, gravity: -0.5, spread: 0.3 });
        }
      }
    }
  }

  dispose(): void {
    if (this.owned) this.object.removeFromParent();
  }
}
