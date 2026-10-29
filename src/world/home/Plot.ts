import * as THREE from "three";
import { PROJECT_IDS, type ProjectId } from "../../data/ids";
import { findNamed } from "../Level";

// A plot in Lantern's Rest you rebuild (src/systems/building.ts), from locations/home.glb's
// PLOT_<id> empty and its children <id>_ruin, <id>_built and <id>_board. The
// ruin stands until the first materials go in. Then the finished building
// rises out of the ground behind scaffolding as the rest arrive: a clipping
// plane climbs the model (the jetty instead grows out along its length, solid
// only as far as it reaches). Once it stands, the scaffolding and the board go.

const TIMBER = new THREE.MeshStandardMaterial({ color: 0x8a6f52, roughness: 0.9 });
const POLE = new THREE.CylinderGeometry(0.055, 0.065, 1, 6).translate(0, 0.5, 0);
const BOARD = new THREE.BoxGeometry(1, 0.05, 0.28);
const BOX = new THREE.BoxGeometry(1, 1, 1);
const PROXY = new THREE.MeshBasicMaterial({ visible: false });
/** How far the scaffolding stands off the walls, how high a lift is and how far apart the poles go. */
const OFF = 0.55;
const LIFT = 1.25;
const BAY = 2.4;

/** A station's target, what you aim at to work it: where it sits off the built model's station mark, and how near you need to be. */
export const STATION_TARGET = { at: new THREE.Vector3(0, 1, -1), range: 3.6 } as const;

const isProject = (v: unknown): v is ProjectId => typeof v === "string" && (PROJECT_IDS as readonly string[]).includes(v);

/** Every PLOT_ under a level's root, keyed by project. */
export function findPlots(root: THREE.Object3D): Map<ProjectId, Plot> {
  const out = new Map<ProjectId, Plot>();
  root.traverse((o) => {
    if (o.name.startsWith("PLOT_") && isProject(o.userData.plot)) out.set(o.userData.plot, new Plot(o.userData.plot, o));
  });
  return out;
}

const underCol = (m: THREE.Object3D, top: THREE.Object3D) => {
  for (let p: THREE.Object3D | null = m; p && p !== top; p = p.parent) if (p.name.startsWith("COL_")) return true;
  return false;
};

export class Plot {
  readonly ruin: THREE.Object3D;
  readonly built: THREE.Object3D;
  readonly board: THREE.Object3D | null;
  /** Where the finished building is worked from (its "station" empty), if it has one. */
  readonly station: THREE.Object3D | null;
  /** The finished building's chimney, if it has one. */
  readonly smoke: THREE.Object3D | null;
  /** Its window panes. */
  readonly windows: THREE.Mesh[] = [];
  /** The jetty grows along its length; everything else grows up. */
  private readonly lengthwise: boolean;
  /** The finished model's bounds, and each of its collision boxes, in the plot's own space. */
  private readonly bounds = new THREE.Box3();
  private readonly colBounds: THREE.Box3[] = [];
  private readonly builtCols = new Set<THREE.Mesh>();
  private readonly plane = new THREE.Plane();
  /** While it rises: each mesh's own materials, and the clipped copies drawn instead. */
  private readonly shared = new Map<THREE.Mesh, THREE.Material | THREE.Material[]>();
  private clones: THREE.Material[] = [];
  private scaffold: THREE.Group | null = null;
  /** While a lengthwise plot grows: its collision, as far as it reaches. */
  private deck: THREE.Group | null = null;
  private shown = -1;

  constructor(
    readonly id: ProjectId,
    readonly root: THREE.Object3D,
  ) {
    this.ruin = root.children.find((c) => c.name.startsWith(`${id}_ruin`)) ?? new THREE.Group();
    this.built = root.children.find((c) => c.name.startsWith(`${id}_built`)) ?? new THREE.Group();
    this.board = root.children.find((c) => c.name.startsWith(`${id}_board`)) ?? null;
    this.lengthwise = id === "jetty";
    this.smoke = findNamed(this.built, "smoke");
    this.station = findNamed(this.built, "station");
    root.updateMatrixWorld(true);
    const toPlot = new THREE.Matrix4().copy(root.matrixWorld).invert();
    const mx = new THREE.Matrix4();
    this.built.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      m.geometry.computeBoundingBox();
      const box = m.geometry.boundingBox!.clone().applyMatrix4(mx.multiplyMatrices(toPlot, m.matrixWorld));
      if (underCol(m, this.built)) {
        this.builtCols.add(m);
        this.colBounds.push(box);
        return;
      }
      if (m.name.startsWith("window")) this.windows.push(m);
      this.bounds.union(box);
    });
  }

  /**
   * Shows the plot at `progress`: 0 the ruin, 1 the finished building, and
   * anything between the building rising behind its scaffolding.
   */
  set(progress: number): void {
    const p = THREE.MathUtils.clamp(progress, 0, 1);
    if (p === this.shown) return;
    this.shown = p;
    const rising = p > 0 && p < 1;
    this.ruin.visible = p === 0;
    this.built.visible = p > 0;
    if (this.board) this.board.visible = p < 1;
    this.clip(rising ? p : null);
    this.scaffold?.removeFromParent();
    this.scaffold = rising && !this.lengthwise ? this.makeScaffold(p) : null;
    if (this.scaffold) this.root.add(this.scaffold);
    this.deck?.removeFromParent();
    this.deck = rising && this.lengthwise ? this.makeDeck(p) : null;
    if (this.deck) this.root.add(this.deck);
  }

  /** How far the building has risen: 0..1. */
  get progress(): number {
    return Math.max(0, this.shown);
  }

  get done(): boolean {
    return this.shown >= 1;
  }

  /** While a lengthwise plot grows, its finished collision stays out (colliders() stands in for it). */
  skipsCollider(m: THREE.Mesh): boolean {
    return this.deck !== null && this.builtCols.has(m);
  }

  /** Collision of its own beyond the model's: the growing jetty. */
  colliders(): THREE.Mesh[] {
    return (this.deck?.children ?? []) as THREE.Mesh[];
  }

  /** The top of the work so far, in world space: where the dust flies when materials go in. */
  workPoint(out = new THREE.Vector3()): THREE.Vector3 {
    const b = this.bounds;
    const p = this.progress;
    if (this.lengthwise) out.set(0, 0.3, b.min.z + (b.max.z - b.min.z) * Math.max(0.1, p));
    else out.set((b.min.x + b.max.x) / 2, this.base + (b.max.y - this.base) * Math.max(0.15, p), (b.min.z + b.max.z) / 2);
    return this.root.localToWorld(out);
  }

  /** Where it rises from: its foot, not the footings it sinks into the ground. */
  private get base(): number {
    return Math.max(this.bounds.min.y, -0.3);
  }

  /** The middle of the finished building, in world space. */
  centre(out = new THREE.Vector3()): THREE.Vector3 {
    return this.root.localToWorld(this.bounds.getCenter(out));
  }

  /** Clips the finished model at `p` of its height (or length), or lifts the clip. */
  private clip(p: number | null): void {
    if (p === null) {
      for (const [m, mat] of this.shared) m.material = mat;
      this.shared.clear();
      for (const c of this.clones) c.dispose();
      this.clones = [];
      return;
    }
    const b = this.bounds;
    const normal = new THREE.Vector3();
    const point = new THREE.Vector3();
    // three clips whatever lies on the plane's negative side.
    if (this.lengthwise) {
      normal.set(0, 0, -1).transformDirection(this.root.matrixWorld);
      point.set(0, 0, b.min.z + (b.max.z - b.min.z) * p);
    } else {
      normal.set(0, -1, 0);
      point.set(0, this.base + (b.max.y - this.base) * p, 0);
    }
    this.plane.setFromNormalAndCoplanarPoint(normal, this.root.localToWorld(point));
    if (this.shared.size) return;
    this.built.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh || this.builtCols.has(m)) return;
      this.shared.set(m, m.material);
      const own = (mat: THREE.Material) => {
        const c = mat.clone();
        c.clippingPlanes = [this.plane];
        c.clipShadows = true;
        // Cut open, a wall would show its hollow inside: drawn, its back faces read as solid stone.
        c.side = THREE.DoubleSide;
        this.clones.push(c);
        return c;
      };
      m.material = Array.isArray(m.material) ? m.material.map(own) : own(m.material);
    });
  }

  /** Poles round the walls and boards at each lift, up to just above the work. */
  private makeScaffold(p: number): THREE.Group {
    const g = new THREE.Group();
    g.name = "scaffold";
    const b = this.bounds;
    const x0 = b.min.x - OFF;
    const x1 = b.max.x + OFF;
    const z0 = b.min.z - OFF;
    const z1 = b.max.z + OFF;
    const base = this.base;
    const top = base + (b.max.y - base) * p + 1.1;
    const add = (geo: THREE.BufferGeometry, x: number, y: number, z: number, sx: number, sy: number, sz: number, yaw = 0) => {
      const m = new THREE.Mesh(geo, TIMBER);
      m.position.set(x, y, z);
      m.scale.set(sx, sy, sz);
      m.rotation.y = yaw;
      m.castShadow = m.receiveShadow = true;
      g.add(m);
    };
    const along = (a: number, c: number) => {
      const n = Math.max(2, Math.round((c - a) / BAY) + 1);
      return Array.from({ length: n }, (_, i) => a + ((c - a) * i) / (n - 1));
    };
    for (const x of along(x0, x1)) for (const z of [z0, z1]) add(POLE, x, base - 0.2, z, 1, top - base + 0.6, 1);
    for (const z of along(z0, z1).slice(1, -1)) for (const x of [x0, x1]) add(POLE, x, base - 0.2, z, 1, top - base + 0.6, 1);
    for (let y = base + LIFT; y < top; y += LIFT) {
      add(BOARD, (x0 + x1) / 2, y, z0, x1 - x0, 1, 1);
      add(BOARD, (x0 + x1) / 2, y, z1, x1 - x0, 1, 1);
      add(BOARD, x0, y, (z0 + z1) / 2, z1 - z0, 1, 1, Math.PI / 2);
      add(BOARD, x1, y, (z0 + z1) / 2, z1 - z0, 1, 1, Math.PI / 2);
    }
    return g;
  }

  /** The finished collision, cut off where the build has reached. */
  private makeDeck(p: number): THREE.Group {
    const g = new THREE.Group();
    g.name = "deck_growing";
    const cut = this.bounds.min.z + (this.bounds.max.z - this.bounds.min.z) * p;
    for (const b of this.colBounds) {
      if (b.min.z >= cut) continue;
      const z1 = Math.min(b.max.z, cut);
      const m = new THREE.Mesh(BOX, PROXY);
      m.position.set((b.min.x + b.max.x) / 2, (b.min.y + b.max.y) / 2, (b.min.z + z1) / 2);
      m.scale.set(b.max.x - b.min.x, b.max.y - b.min.y, z1 - b.min.z);
      g.add(m);
    }
    return g;
  }
}
