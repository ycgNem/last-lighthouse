import * as THREE from "three";
import type { EnemyId, LocationId, NodeId, TideReq } from "../data/ids";
import type { DynamicBox, StaticCollider } from "../physics/StaticCollider";

// What a location looks like to the rest of the game, whether it was built in
// code (home greybox) or loaded from a Blender .glb (LevelLoader).

export interface NodeMarker {
  node: NodeId;
  position: THREE.Vector3;
  yaw: number;
  /** The prop placed in Blender, if the marker is a mesh rather than an empty. */
  object?: THREE.Object3D;
}

export interface EnemyMarker {
  enemy: EnemyId;
  position: THREE.Vector3;
  tide: TideReq;
}

/** Static interactables: stations, NPCs, boats, ladders, the beacon lamp. */
export interface LevelInteract {
  /** e.g. "storage", "hearth", "forge", "lamp", "boat", "plot:forge", "npc:maren", "rope_ladder", "beacon". */
  id: string;
  object: THREE.Object3D;
  /** Interaction reach in metres. */
  range: number;
}

/** A Gloom pocket from a GLOOM_ empty: where it hangs and how far it spreads. */
export interface GloomMarker {
  position: THREE.Vector3;
  radius: number;
}

export interface Trigger {
  event: string;
  box: THREE.Box3;
}

export interface Buoy extends DynamicBox {
  object: THREE.Object3D;
  /** Box in the object's local space; re-applied every frame. */
  local: THREE.Box3;
  /** Height of the object's origin above the water surface while floating. */
  float: number;
  min: number;
  max: number;
  phase: number;
  /** Shadow LOD (buoyShadows()): whether it casts now, and its meshes that do. */
  shadows?: boolean;
  casters?: THREE.Mesh[];
}

export interface LevelUpdate {
  time: number;
  dt: number;
  waterY: number;
  /** 0..1 strength of the flood warning glow on tidal surfaces. */
  floodWarning: number;
  /** Where the player stands (people at home look round at you). */
  viewer: THREE.Vector3;
}

export interface Level {
  readonly id: LocationId;
  readonly root: THREE.Object3D;
  collider: StaticCollider;
  readonly spawn: THREE.Vector3;
  readonly spawnYaw: number;
  readonly anchors: THREE.Vector3[];
  readonly nodes: NodeMarker[];
  readonly enemies: EnemyMarker[];
  readonly interacts: LevelInteract[];
  readonly triggers: Trigger[];
  readonly buoys: Buoy[];
  readonly gloom: GloomMarker[];
  /** Named points from FX_<name> empties (e.g. "arena", "home_light", "beacon_lamp"). */
  readonly points: Map<string, THREE.Vector3>;
  update(u: LevelUpdate): void;
  dispose(): void;
}

/** Applies buoyancy: each buoy floats on the water, clamped to its range. */
export function updateBuoys(buoys: readonly Buoy[], waterY: number, time: number): void {
  for (const b of buoys) {
    const bob = Math.sin(time * 1.1 + b.phase) * 0.04;
    b.object.position.y = THREE.MathUtils.clamp(waterY + b.float + bob, b.min, b.max);
    b.object.updateMatrixWorld(true);
    b.box.copy(b.local).applyMatrix4(b.object.matrixWorld);
  }
}

/** Only buoys within `near` (squared) of `p` cast shadows, as for creatures and loot. */
export function buoyShadows(buoys: readonly Buoy[], p: THREE.Vector3, near: number): void {
  for (const b of buoys) {
    const on = b.object.position.distanceToSquared(p) < near;
    if (on === (b.shadows ?? true)) continue;
    b.shadows = on;
    if (!b.casters) {
      const casters: THREE.Mesh[] = [];
      b.object.traverse((o) => {
        if ((o as THREE.Mesh).isMesh && o.castShadow) casters.push(o as THREE.Mesh);
      });
      b.casters = casters;
    }
    for (const m of b.casters) m.castShadow = on;
  }
}

/** The first object under `root`, itself included, whose name starts with `prefix` (Blender numbers the copies it places: "smoke001"). */
export function findNamed(root: THREE.Object3D, prefix: string): THREE.Object3D | null {
  if (root.name.startsWith(prefix)) return root;
  for (const c of root.children) {
    const found = findNamed(c, prefix);
    if (found) return found;
  }
  return null;
}

export function disposeObject(root: THREE.Object3D): void {
  root.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (mesh.isMesh) {
      mesh.geometry.dispose();
      const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      for (const m of mats) m.dispose();
    }
  });
  root.removeFromParent();
}
