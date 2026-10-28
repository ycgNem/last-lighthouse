import * as THREE from "three";
import type { Assets } from "../core/Assets";
import { ENEMY_IDS, NODE_IDS, type EnemyId, type LocationId, type NodeId, type TideReq } from "../data/ids";
import { StaticCollider } from "../physics/StaticCollider";
import type { Buoy, EnemyMarker, Level, LevelInteract, LevelUpdate, NodeMarker, Trigger } from "./Level";
import { updateBuoys } from "./Level";
import { patchTideMaterial } from "./TideMaterial";

// Turns a Blender-exported location (.glb) into a Level by reading the object
// naming conventions in docs/ART_PIPELINE.md.

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
  readonly points = new Map<string, THREE.Vector3>();
  /** Objects shown or hidden by progression (STATE_<flag>_<on|off>). */
  readonly stateObjects: { flag: string; on: boolean; object: THREE.Object3D }[] = [];
  private colMeshes: THREE.Mesh[] = [];

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
  }

  /**
   * Shows each STATE_<flag>_<on|off> object when the flag matches, and rebuilds
   * collision so a hidden gate stops blocking (and a shown bridge holds you).
   */
  applyFlags(flags: readonly string[]): void {
    if (!this.stateObjects.length) return;
    const hidden = new Set<THREE.Object3D>();
    for (const s of this.stateObjects) {
      s.object.visible = flags.includes(s.flag) === s.on;
      if (!s.object.visible) hidden.add(s.object);
    }
    const shown = (m: THREE.Object3D) => {
      for (let o: THREE.Object3D | null = m; o; o = o.parent) if (hidden.has(o)) return false;
      return true;
    };
    this.collider = new StaticCollider(this.colMeshes.filter(shown));
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
    // Geometry and materials are shared with the cached .glb; just detach.
    this.root.removeFromParent();
  }
}

export async function loadLevel(id: LocationId, assets: Assets): Promise<GlbLevel | null> {
  const scene = await assets.load(`locations/${id}.glb`);
  return scene ? new GlbLevel(id, scene) : null;
}
