import * as THREE from "three";
import type { Assets } from "../core/Assets";
import { ENEMY_IDS, NODE_IDS, type EnemyId, type LocationId, type NodeId, type TideReq } from "../data/ids";
import { StaticCollider } from "../physics/StaticCollider";
import { batchStatic, collapseMaterials, type BatchResult } from "./Batch";
import type { Buoy, EnemyMarker, GloomMarker, Level, LevelInteract, LevelUpdate, NodeMarker, Trigger } from "./Level";
import { updateBuoys } from "./Level";
import { patchTideMaterial } from "./TideMaterial";

// Turns a Blender-exported location (.glb) into a Level by reading the object
// naming conventions in docs/ART_PIPELINE.md.

/**
 * Markers and anything the game moves, hides or lets you use: never merged into
 * the static batch. Home adds its plots (PLOT_), the places people and the
 * lighthouse stand (PLACE_, NPC_), decor keep-outs (CLEAR_) and the grass's
 * positions (SCATTER_).
 */
const LIVE = /^(NODE_|BUOY_|STATE_|INT_|TRIG_|COL_|ENEMY_|SPAWN_|ANCHOR_|FX_|GLOOM_|PLOT_|PLACE_|NPC_|CLEAR_|SCATTER_)/;
/** Stands in for something you use without being drawn (the lighthouse door): still a raycast target. */
const PROXY = new THREE.MeshBasicMaterial({ visible: false });

const isNode = (v: unknown): v is NodeId => typeof v === "string" && (NODE_IDS as readonly string[]).includes(v);
const isEnemy = (v: unknown): v is EnemyId => typeof v === "string" && (ENEMY_IDS as readonly string[]).includes(v);
const isTide = (v: unknown): v is TideReq => v === "low" || v === "high" || v === "any";

function meshesUnder(o: THREE.Object3D): THREE.Mesh[] {
  const out: THREE.Mesh[] = [];
  o.traverse((c) => {
    if ((c as THREE.Mesh).isMesh) out.push(c as THREE.Mesh);
  });
  return out;
}

export class GlbLevel implements Level {
  readonly root: THREE.Object3D;
  collider: StaticCollider;
  readonly spawns = new Map<string, { position: THREE.Vector3; yaw: number }>();
  readonly anchors: THREE.Vector3[] = [];
  readonly nodes: NodeMarker[] = [];
  readonly enemies: EnemyMarker[] = [];
  readonly interacts: LevelInteract[] = [];
  readonly triggers: Trigger[] = [];
  readonly buoys: Buoy[] = [];
  readonly gloom: GloomMarker[] = [];
  readonly points = new Map<string, THREE.Vector3>();
  /** Objects shown or hidden by progression (STATE_<flag>_<on|off>). */
  readonly stateObjects: { flag: string; on: boolean; object: THREE.Object3D }[] = [];
  private colMeshes: THREE.Mesh[] = [];
  /** The merged static scenery (see Batch.ts). */
  readonly batch: BatchResult;

  constructor(
    readonly id: LocationId,
    source: THREE.Object3D,
  ) {
    this.root = source.clone(true);
    this.root.updateMatrixWorld(true);
    const col: THREE.Mesh[] = [];
    const lights: THREE.Object3D[] = [];
    const world = new THREE.Vector3();
    const quat = new THREE.Quaternion();
    const euler = new THREE.Euler();

    this.root.traverse((o) => {
      const name = o.name;
      const data = o.userData as Record<string, unknown>;
      o.getWorldPosition(world);
      const yaw = () => {
        o.getWorldQuaternion(quat);
        return euler.setFromQuaternion(quat, "YXZ").y;
      };

      const mesh = o as THREE.Mesh;
      if (mesh.isMesh) {
        const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        for (const m of mats) if (m.name.startsWith("TIDE_")) patchTideMaterial(m);
      }

      if (name.startsWith("COL_")) {
        col.push(...meshesUnder(o));
        o.visible = false;
      } else if (name.startsWith("SCATTER_")) {
        o.visible = false;
      } else if (data.proxy) {
        for (const m of meshesUnder(o)) m.material = PROXY;
      } else if (data.col) {
        col.push(...meshesUnder(o));
      }
      if (name.startsWith("SPAWN_")) this.spawns.set(name.slice(6), { position: world.clone(), yaw: yaw() });
      else if (name.startsWith("ANCHOR_")) this.anchors.push(world.clone());
      else if (name.startsWith("NODE_") && isNode(data.node)) {
        this.nodes.push({ node: data.node, position: world.clone(), yaw: yaw(), object: meshesUnder(o).length ? o : undefined });
      } else if (name.startsWith("ENEMY_") && isEnemy(data.enemy)) {
        this.enemies.push({ enemy: data.enemy, position: world.clone(), tide: isTide(data.tide) ? data.tide : "any" });
      } else if (name.startsWith("TRIG_") && typeof data.event === "string") {
        this.triggers.push({ event: data.event, box: new THREE.Box3().setFromObject(o) });
        o.visible = false;
      } else if (name.startsWith("BUOY_")) {
        const local = new THREE.Box3();
        for (const m of meshesUnder(o)) {
          m.geometry.computeBoundingBox();
          const bb = m.geometry.boundingBox!.clone();
          if (m !== o) bb.applyMatrix4(m.matrix);
          local.union(bb);
        }
        this.buoys.push({
          object: o,
          local,
          box: new THREE.Box3(),
          float: typeof data.float === "number" ? data.float : -0.45,
          min: typeof data.min === "number" ? data.min : -10,
          max: typeof data.max === "number" ? data.max : 10,
          phase: this.buoys.length * 1.7,
        });
      } else if (name.startsWith("GLOOM_")) {
        this.gloom.push({ position: world.clone(), radius: typeof data.radius === "number" ? data.radius : 4 });
      } else if (name.startsWith("FX_")) {
        this.points.set(name.slice(3), world.clone());
      } else if (name.startsWith("STATE_")) {
        const m = /^STATE_(.+)_(on|off)$/.exec(name);
        if (m) this.stateObjects.push({ flag: m[1]!, on: m[2] === "on", object: o });
      }
      // INT_ objects, and anything else with an interact property (a floating BUOY_boat).
      if (typeof data.interact === "string") this.interacts.push({ id: data.interact, object: o, range: typeof data.range === "number" ? data.range : 4 });
      if (data.light === "warm") lights.push(o);
    });

    for (const o of lights) {
      const light = new THREE.PointLight(0xffb347, 7, 10, 1.8);
      const off = Array.isArray(o.userData.light_offset) ? (o.userData.light_offset as number[]) : [0.5, 1.9, 0];
      light.position.set(off[0] ?? 0, off[1] ?? 0, off[2] ?? 0);
      o.add(light);
    }

    this.colMeshes = col;
    this.collider = new StaticCollider(col);
    this.batch = batchStatic(this.root, (o) => LIVE.test(o.name) || typeof o.userData.interact === "string");
    // What can't be merged with the scenery (crates, boats, gates, ladders) still moves as one
    // piece, so its material split can go (home's plots only by finish: see collapseMaterials()).
    for (const o of [...this.root.children]) if (LIVE.test(o.name) && !o.name.startsWith("COL_")) collapseMaterials(o, !o.name.startsWith("PLOT_"));
  }

  /**
   * Shows each STATE_<flag>_<on|off> object when the flag matches, and rebuilds
   * collision so a hidden gate stops blocking (and a shown bridge holds you).
   */
  applyFlags(flags: readonly string[]): void {
    if (!this.stateObjects.length) return;
    for (const s of this.stateObjects) s.object.visible = flags.includes(s.flag) === s.on;
    this.rebuildCollider();
  }

  /**
   * Collision from every COL_ mesh that's shown, parents and all, less whatever
   * `skip` turns away, plus `extra` meshes: people, placed decor. A COL_ object
   * is always hidden and a batched mesh is drawn by the batch, so neither counts
   * as hidden.
   */
  rebuildCollider(extra: readonly THREE.Mesh[] = [], skip?: (m: THREE.Mesh) => boolean): void {
    const shown = (m: THREE.Mesh) => {
      for (let o: THREE.Object3D | null = m; o; o = o.parent) if (!o.visible && !o.name.startsWith("COL_") && !o.userData.batched) return false;
      return !skip?.(m);
    };
    this.collider = new StaticCollider([...this.colMeshes.filter(shown), ...extra]);
  }

  /** A named SPAWN_ point, falling back to the landing. */
  spawnFor(name: string): { position: THREE.Vector3; yaw: number } {
    return this.spawns.get(name) ?? { position: this.spawn, yaw: this.spawnYaw };
  }

  get spawn(): THREE.Vector3 {
    return (this.spawns.get("landing") ?? this.spawns.values().next().value)?.position ?? new THREE.Vector3(0, 5, 0);
  }

  get spawnYaw(): number {
    return (this.spawns.get("landing") ?? this.spawns.values().next().value)?.yaw ?? 0;
  }

  update(u: LevelUpdate): void {
    if (this.buoys.length) updateBuoys(this.buoys, u.waterY, u.time);
  }

  dispose(): void {
    // Geometry and materials are shared with the cached .glb; only the merged batch is ours.
    this.batch.dispose();
    this.root.removeFromParent();
  }
}

export async function loadLevel(id: LocationId, assets: Assets): Promise<GlbLevel | null> {
  const scene = await assets.load(`locations/${id}.glb`);
  return scene ? new GlbLevel(id, scene) : null;
}
