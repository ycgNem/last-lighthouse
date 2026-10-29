import * as THREE from "three";
import type { Assets } from "../../core/Assets";
import { DECOR, DECOR_RULES } from "../../data/decor";
import { DECOR_IDS, type DecorId } from "../../data/ids";
import type { PlacedDecor } from "../../state/GameState";
import { instanceParts } from "../Batch";

// The decor you've placed round the Rest (build mode, B; src/systems/decor.ts
// says where a piece may go). Every piece is drawn instanced with the rest of
// its kind; a solid one is also a box in home's collider, and the lit ones
// nearest you cast real light while the rest just glow. While you build, a
// ghost of the piece you're holding follows the crosshair: green where it can
// go, red where it can't.

const BOX = new THREE.BoxGeometry(1, 1, 1);
const HIDDEN = new THREE.MeshBasicMaterial({ visible: false });
const GHOST_OK = new THREE.MeshBasicMaterial({ color: 0x7be08f, transparent: true, opacity: 0.45, depthWrite: false });
const GHOST_NO = new THREE.MeshBasicMaterial({ color: 0xe0705c, transparent: true, opacity: 0.45, depthWrite: false });
/** Seconds between choosing which lit pieces get the real lights. */
const LIGHT_EVERY = 0.4;

const tmpM = new THREE.Matrix4();
const tmpM2 = new THREE.Matrix4();
const tmpQ = new THREE.Quaternion();
const tmpV = new THREE.Vector3();
const UP = new THREE.Vector3(0, 1, 0);
const ONE = new THREE.Vector3(1, 1, 1);

interface Placed {
  piece: PlacedDecor;
  y: number;
}

export class DecorLayer {
  readonly root = new THREE.Group();
  /** One box per solid piece, for the collider. */
  readonly colliders: THREE.Mesh[] = [];
  private readonly meshes = new Map<DecorId, { mesh: THREE.InstancedMesh; part: THREE.Matrix4 }[]>();
  private readonly ghosts = new Map<DecorId, THREE.Object3D>();
  private ghost: THREE.Object3D | null = null;
  private placed: Placed[] = [];
  private readonly lights: THREE.PointLight[] = [];
  private lightT = 0;
  /** The save's decor, as last drawn. */
  private key = "";

  constructor(private readonly assets: Assets) {
    this.root.name = "decor";
    for (const id of DECOR_IDS) {
      const src = assets.prop(DECOR[id].model);
      if (!src) continue;
      const parts: { mesh: THREE.InstancedMesh; part: THREE.Matrix4 }[] = [];
      for (const p of instanceParts(src)) {
        const mesh = new THREE.InstancedMesh(p.geometry, p.material, DECOR_RULES.max);
        mesh.count = 0;
        mesh.castShadow = mesh.receiveShadow = true;
        mesh.name = `decor_${id}`;
        this.root.add(mesh);
        parts.push({ mesh, part: p.matrix });
      }
      this.meshes.set(id, parts);
    }
  }

  /** Draws the save's decor, standing each piece on `groundY`. True if anything changed (the collider needs rebuilding). */
  sync(decor: readonly PlacedDecor[], groundY: (x: number, z: number) => number): boolean {
    const key = JSON.stringify(decor);
    if (key === this.key) return false;
    this.key = key;
    this.placed = decor.map((piece) => ({ piece, y: groundY(piece.x, piece.z) }));
    const counts = new Map<DecorId, number>();
    for (const { piece, y } of this.placed) {
      const parts = this.meshes.get(piece.kind);
      if (!parts) continue;
      const n = counts.get(piece.kind) ?? 0;
      counts.set(piece.kind, n + 1);
      tmpM.compose(tmpV.set(piece.x, y, piece.z), tmpQ.setFromAxisAngle(UP, piece.yaw), ONE);
      for (const { mesh, part } of parts) mesh.setMatrixAt(n, tmpM2.multiplyMatrices(tmpM, part));
    }
    for (const [id, parts] of this.meshes) {
      for (const { mesh } of parts) {
        mesh.count = counts.get(id) ?? 0;
        mesh.instanceMatrix.needsUpdate = true;
        mesh.computeBoundingSphere();
      }
    }
    this.colliders.length = 0;
    for (const { piece, y } of this.placed) {
      const def = DECOR[piece.kind];
      if (!def.solid) continue;
      const box = new THREE.Mesh(BOX, HIDDEN);
      box.position.set(piece.x, y + def.height / 2, piece.z);
      box.rotation.y = piece.yaw;
      box.scale.set(def.size[0], def.height, def.size[1]);
      box.updateMatrixWorld(true);
      this.colliders.push(box);
    }
    // The lights go in with the first lit piece: adding lights recompiles every lit material once.
    const lit = this.placed.some(({ piece }) => DECOR[piece.kind].light);
    if (lit && !this.lights.length) {
      for (let i = 0; i < DECOR_RULES.maxLights; i++) {
        const light = new THREE.PointLight(0xffc27a, 0, 9, 1.8);
        this.lights.push(light);
        this.root.add(light);
      }
    }
    this.lightT = 0;
    return true;
  }

  /** The nearest lit pieces get the real lights. */
  update(dt: number, viewer: THREE.Vector3, time: number): void {
    if (!this.lights.length) return;
    this.lightT -= dt;
    if (this.lightT <= 0) {
      this.lightT = LIGHT_EVERY;
      const lit = this.placed.filter(({ piece }) => DECOR[piece.kind].light).sort((a, b) => Math.hypot(a.piece.x - viewer.x, a.piece.z - viewer.z) - Math.hypot(b.piece.x - viewer.x, b.piece.z - viewer.z));
      this.lights.forEach((light, i) => {
        const p = lit[i];
        const l = p ? DECOR[p.piece.kind].light : undefined;
        if (!p || !l) {
          light.intensity = 0;
          light.userData.base = 0;
          return;
        }
        light.color.setHex(l.color);
        light.distance = l.distance;
        light.position.set(p.piece.x, p.y + l.y, p.piece.z);
        light.userData.base = l.intensity;
      });
    }
    // A little flicker, each its own.
    this.lights.forEach((light, i) => {
      const base = (light.userData.base as number | undefined) ?? 0;
      light.intensity = base * (1 + Math.sin(time * 11 + i * 2.1) * 0.06 + Math.sin(time * 23 + i) * 0.04);
    });
  }

  /** The piece you're holding, where it would go, green if it can and red if it can't; null hides it. */
  showGhost(kind: DecorId | null, at?: THREE.Vector3, yaw = 0, ok = false): void {
    const next = kind ? this.ghostOf(kind) : null;
    if (this.ghost && this.ghost !== next) this.ghost.visible = false;
    this.ghost = next;
    if (!next || !at) {
      if (next) next.visible = false;
      return;
    }
    next.visible = true;
    next.position.copy(at);
    next.rotation.y = yaw;
    const mat = ok ? GHOST_OK : GHOST_NO;
    next.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh) m.material = mat;
    });
  }

  private ghostOf(kind: DecorId): THREE.Object3D | null {
    let g = this.ghosts.get(kind);
    if (g) return g;
    g = this.assets.prop(DECOR[kind].model) ?? undefined;
    if (!g) return null;
    g.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      m.castShadow = m.receiveShadow = false;
      m.renderOrder = 3;
    });
    g.visible = false;
    this.root.add(g);
    this.ghosts.set(kind, g);
    return g;
  }
}
