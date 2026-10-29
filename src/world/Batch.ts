import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

// Static batching: every mesh in a level that never moves, hides or changes
// material is merged with the others that share its material, so the whole
// set costs one draw call (twice, with the shadow pass) instead of one per
// prop and per material slot. The originals stay in the scene, hidden, so
// anything that reads their transforms (collision, focus rays) is unaffected.
// Home batches its finished buildings the same way once they stand.

export interface BatchResult {
  group: THREE.Group;
  /** Meshes merged away (now hidden). */
  merged: number;
  /** Draw calls (per pass) before and after. */
  before: number;
  after: number;
  /** Takes the batch away and shows the originals again. */
  dispose(): void;
}

const flip = new THREE.Matrix4();

/**
 * One merge bucket: everything with this material (or, given a finish, alike in
 * it, colours to be baked), these attributes and these shadow flags.
 */
function bucketKey(mesh: THREE.Mesh, finish: string | null = null): string {
  const g = mesh.geometry;
  const attrs = Object.keys(g.attributes)
    .filter((k) => finish === null || k !== "color")
    .sort()
    .map((k) => {
      const a = g.getAttribute(k);
      return `${k}:${a.itemSize}:${a.normalized ? 1 : 0}`;
    })
    .join(",");
  const mat = mesh.material as THREE.Material;
  return `${finish ?? mat.uuid}|${attrs}|${g.index ? "i" : "n"}|${mesh.castShadow ? 1 : 0}${mesh.receiveShadow ? 1 : 0}|${mesh.renderOrder}`;
}

/** Reverses triangle winding (a mirrored transform turns faces inside out). */
function flipWinding(g: THREE.BufferGeometry): void {
  if (g.index) {
    const idx = g.index.array;
    for (let i = 0; i < idx.length; i += 3) {
      const t = idx[i + 1]!;
      idx[i + 1] = idx[i + 2]!;
      idx[i + 2] = t;
    }
    g.index.needsUpdate = true;
    return;
  }
  for (const name of Object.keys(g.attributes)) {
    const a = g.getAttribute(name) as THREE.BufferAttribute;
    const n = a.itemSize;
    const arr = a.array;
    for (let v = 0; v + 2 < a.count; v += 3) {
      for (let k = 0; k < n; k++) {
        const i1 = (v + 1) * n + k;
        const i2 = (v + 2) * n + k;
        const t = arr[i1]!;
        arr[i1] = arr[i2]!;
        arr[i2] = t;
      }
    }
    a.needsUpdate = true;
  }
}

/**
 * The meshes under `root` a batch can take: visible leaves with one visible
 * material, not skinned, instanced or morphing. `keep(o)` holds back it and
 * everything under it. `drawn` counts every mesh drawn, leaf or not.
 */
function collect(root: THREE.Object3D, keep: (o: THREE.Object3D) => boolean): { meshes: THREE.Mesh[]; drawn: number } {
  const meshes: THREE.Mesh[] = [];
  let drawn = 0;
  const visit = (o: THREE.Object3D) => {
    if (!o.visible || keep(o)) return;
    const mesh = o as THREE.Mesh;
    if (mesh.isMesh && !(mesh as THREE.SkinnedMesh).isSkinnedMesh && !(mesh as THREE.InstancedMesh).isInstancedMesh && !mesh.morphTargetInfluences) {
      const mat = mesh.material;
      if (!Array.isArray(mat) && mat.visible) {
        drawn++;
        if (o.children.length === 0) meshes.push(mesh);
      }
    }
    for (const c of o.children) visit(c);
  };
  visit(root);
  return { meshes, drawn };
}

/** What batchMeshes() can take from under `root` (all of it, say a finished building). */
export function staticMeshes(root: THREE.Object3D): THREE.Mesh[] {
  return collect(root, () => false).meshes;
}

/**
 * Merges the static meshes under `root`. `keep(o)` returns true for anything
 * that must stay separate (it and everything under it): things that move,
 * hide, swap materials or are picked by the player. Only visible leaf meshes
 * with one visible material are merged; a bucket of one is left alone. Scenery
 * goes by finish, rough plain materials together, each colour baked into
 * vertex colours.
 */
export function batchStatic(root: THREE.Object3D, keep: (o: THREE.Object3D) => boolean): BatchResult {
  const { meshes, drawn } = collect(root, keep);
  return batchMeshes(root, meshes, "static_batch", drawn, true);
}

/** A material the game patches (the tide's flood glow) keeps its own draw. */
const patched = (m: THREE.Material) => Object.prototype.hasOwnProperty.call(m, "onBeforeCompile");

/**
 * Merges `meshes` (from staticMeshes(), or batchStatic()'s own pick) that share
 * a material into one mesh each, in `root`'s space, under `root`; with
 * `byFinish`, those alike in finish (see mergeKey()) too, as vertex colours.
 */
export function batchMeshes(root: THREE.Object3D, meshes: readonly THREE.Mesh[], name: string, before = meshes.length, byFinish = false): BatchResult {
  root.updateMatrixWorld(true);
  const toRoot = root.matrixWorld.clone().invert();
  const buckets = new Map<string, { baking: boolean; bucket: THREE.Mesh[] }>();
  for (const mesh of meshes) {
    const mat = mesh.material as THREE.Material;
    const fin = byFinish && !patched(mat) ? mergeKey(mat) : null;
    const key = bucketKey(mesh, fin);
    const list = buckets.get(key);
    if (list) list.bucket.push(mesh);
    else buckets.set(key, { baking: fin !== null, bucket: [mesh] });
  }

  const group = new THREE.Group();
  group.name = name;
  const made: THREE.BufferGeometry[] = [];
  const cloned: THREE.Material[] = [];
  const hidden: THREE.Mesh[] = [];
  let merged = 0;
  let after = before;
  for (const { baking, bucket } of buckets.values()) {
    if (bucket.length < 2) continue;
    const first = bucket[0]!;
    const parts: THREE.BufferGeometry[] = [];
    for (const m of bucket) {
      const mx = flip.multiplyMatrices(toRoot, m.matrixWorld);
      if (baking) {
        parts.push(baked(m, mx));
        continue;
      }
      const g = m.geometry.clone();
      g.applyMatrix4(mx);
      if (mx.determinant() < 0) flipWinding(g);
      // Only what every material here reads: groups and morphs would break the merge.
      g.clearGroups();
      parts.push(g);
    }
    const geo = mergeGeometries(parts, false);
    for (const p of parts) p.dispose();
    if (!geo) continue;
    let mat = first.material as THREE.Material;
    if (baking) {
      const own = (mat as THREE.MeshStandardMaterial).clone();
      own.color.setRGB(1, 1, 1);
      own.vertexColors = true;
      own.name = `${own.name}+${bucket.length - 1}`;
      cloned.push(own);
      mat = own;
    }
    const batch = new THREE.Mesh(geo, mat);
    batch.castShadow = first.castShadow;
    batch.receiveShadow = first.receiveShadow;
    batch.renderOrder = first.renderOrder;
    batch.name = `batch_${mat.name || "material"}`;
    group.add(batch);
    made.push(geo);
    for (const m of bucket) {
      m.visible = false;
      // Hidden only because the batch draws it: still there for collision (GlbLevel.rebuildCollider).
      m.userData.batched = true;
      hidden.push(m);
    }
    merged += bucket.length;
    after -= bucket.length - 1;
  }
  root.add(group);
  return {
    group,
    merged,
    before,
    after,
    dispose: () => {
      group.removeFromParent();
      for (const g of made) g.dispose();
      for (const m of cloned) m.dispose();
      for (const m of hidden) {
        m.visible = true;
        delete m.userData.batched;
      }
    },
  };
}

/** Materials that can share one draw: plain, opaque, unlit-by-emission, and alike in finish. */
function finishKey(mat: THREE.Material): string | null {
  const m = mat as THREE.MeshStandardMaterial;
  if (!m.isMeshStandardMaterial || m.map || m.normalMap || m.emissiveMap || m.transparent || m.name.startsWith("GLOW_")) return null;
  if (m.emissive.getHex() !== 0 && m.emissiveIntensity > 0) return null;
  return `${Math.round(m.roughness * 5)}|${m.metalness >= 0.5 ? 1 : 0}|${m.side}|${m.flatShading ? 1 : 0}`;
}

/** finishKey(), with every rough plain material (wood, stone, cloth, sand, rust) as one: they read alike at that roughness. */
function mergeKey(mat: THREE.Material): string | null {
  const fin = finishKey(mat);
  const m = mat as THREE.MeshStandardMaterial;
  return fin !== null && m.metalness < 0.5 && m.roughness >= 0.75 ? `rough|${m.side}|${m.flatShading ? 1 : 0}` : fin;
}

/** A colour-baked copy of `m`'s geometry in its template's space (see collapseMaterials()). */
function baked(m: THREE.Mesh, matrix: THREE.Matrix4): THREE.BufferGeometry {
  const geo = m.geometry.clone();
  geo.applyMatrix4(matrix);
  if (matrix.determinant() < 0) flipWinding(geo);
  geo.clearGroups();
  const tint = (m.material as THREE.MeshStandardMaterial).color;
  const n = geo.getAttribute("position").count;
  const had = geo.getAttribute("color") as THREE.BufferAttribute | undefined;
  const useOld = had && (m.material as THREE.MeshStandardMaterial).vertexColors;
  const col = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    col[i * 3] = (useOld ? had.getX(i) : 1) * tint.r;
    col[i * 3 + 1] = (useOld ? had.getY(i) : 1) * tint.g;
    col[i * 3 + 2] = (useOld ? had.getZ(i) : 1) * tint.b;
  }
  geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
  return geo;
}

/** One instanced part of a prop: its geometry and material, and where it sits in the prop. */
export interface InstancePart {
  geometry: THREE.BufferGeometry;
  material: THREE.Material | THREE.Material[];
  matrix: THREE.Matrix4;
}

/**
 * A prop drawn instanced (decor, drift), as few parts as its finishes allow:
 * one instanced mesh is a draw call for every copy, so each part saved counts
 * twice (with the shadow pass). Rough plain materials (wood, stone, cloth,
 * sand, rust) read alike at that roughness and go into one part, their colours
 * baked into vertex colours; metal, smooth and glowing ones keep their own.
 */
export function instanceParts(src: THREE.Object3D): InstancePart[] {
  src.updateWorldMatrix(true, true);
  const out: InstancePart[] = [];
  const buckets = new Map<string, THREE.Mesh[]>();
  src.traverse((o) => {
    const m = o as THREE.Mesh;
    if (!m.isMesh) return;
    const mat = m.material;
    const fin = Array.isArray(mat) ? null : mergeKey(mat);
    if (fin === null) {
      out.push({ geometry: m.geometry, material: mat, matrix: m.matrixWorld.clone() });
      return;
    }
    const attrs = Object.keys(m.geometry.attributes).filter((k) => k !== "color").sort().join(",");
    const key = `${fin}|${attrs}|${m.geometry.index ? "i" : "n"}`;
    const list = buckets.get(key);
    if (list) list.push(m);
    else buckets.set(key, [m]);
  });
  for (const meshes of buckets.values()) {
    const first = meshes[0]!;
    const parts = meshes.length > 1 ? meshes.map((m) => baked(m, m.matrixWorld)) : [];
    const geo = parts.length ? mergeGeometries(parts, false) : null;
    for (const g of parts) g.dispose();
    if (!geo) {
      for (const m of meshes) out.push({ geometry: m.geometry, material: m.material, matrix: m.matrixWorld.clone() });
      continue;
    }
    const mat = (first.material as THREE.MeshStandardMaterial).clone();
    mat.color.setRGB(1, 1, 1);
    mat.vertexColors = true;
    mat.name = `${mat.name}+${meshes.length - 1}`;
    out.push({ geometry: geo, material: mat, matrix: new THREE.Matrix4() });
  }
  return out;
}

/** One wreck for mergePieces(): its root, and the pieces it loses, in order. */
export interface PieceSet {
  root: THREE.Object3D;
  pieces: readonly THREE.Object3D[];
}

/** Wrecks drawn merged (see mergePieces()). */
export interface PieceBatch {
  /** One vertex-coloured mesh per finish, in world space: add them to the scene. */
  readonly meshes: THREE.Mesh[];
  /** Shows wreck `w` with its first `gone` pieces torn off (or put back). */
  setGone(w: number, gone: number): void;
  dispose(): void;
}

/** One merged mesh, and where each wreck lies in its index: offs.get(w)![k] is where piece k starts, [pieces] where the bones do. */
interface PieceSlice {
  mesh: THREE.Mesh;
  index: THREE.BufferAttribute;
  orig: Uint16Array | Uint32Array;
  offs: Map<number, number[]>;
}

/** `geo`, indexed if it wasn't (a merged wreck tears pieces off through its index). */
function indexed(geo: THREE.BufferGeometry): THREE.BufferGeometry {
  if (!geo.index) geo.setIndex([...Array(geo.getAttribute("position").count).keys()]);
  return geo;
}

/**
 * Merges several wrecks built in pieces into one vertex-coloured mesh per finish
 * (rough plain materials together, as for instanced props), in world space, so
 * a whole wreck field draws in a few calls however many wrecks and pieces it
 * has. In each merged mesh a wreck's triangles lie together, its pieces first in
 * the order they go and its bones last: tearing pieces off collapses their
 * triangles to a point, and a restock writes them back. The originals stay where
 * they were, hidden: clone a piece to show it on its own. Meshes that can't
 * merge (glowing, see-through, several materials) are left be, and go with
 * their piece.
 */
export function mergePieces(wrecks: readonly PieceSet[]): PieceBatch {
  type Entry = { mesh: THREE.Mesh; w: number; k: number };
  const buckets = new Map<string, Entry[]>();
  const loose: Entry[] = [];
  wrecks.forEach(({ root, pieces }, w) => {
    root.updateWorldMatrix(true, true);
    const owner = new Map<THREE.Object3D, number>();
    pieces.forEach((p, k) => p.traverse((o) => owner.set(o, k)));
    root.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      const e = { mesh: m, w, k: owner.get(m) ?? pieces.length };
      const fin = Array.isArray(m.material) ? null : mergeKey(m.material);
      if (!fin) {
        if (e.k < pieces.length) loose.push(e);
        return;
      }
      // Shadow flags aren't in the key: the shadow LOD may have turned them off on a wreck at home.
      const attrs = Object.keys(m.geometry.attributes).filter((a) => a !== "color").sort().join(",");
      const key = `${fin}|${attrs}`;
      const list = buckets.get(key);
      if (list) list.push(e);
      else buckets.set(key, [e]);
    });
  });
  const slices: PieceSlice[] = [];
  for (const list of buckets.values()) {
    // Stable, so each piece keeps the order its meshes came in.
    list.sort((a, b) => a.w - b.w || a.k - b.k);
    const parts = list.map((e) => indexed(baked(e.mesh, e.mesh.matrixWorld)));
    const offs = new Map<number, number[]>();
    let at = 0;
    for (let i = 0; i < list.length; ) {
      const w = list[i]!.w;
      const o: number[] = [];
      for (let k = 0; k <= wrecks[w]!.pieces.length; k++) {
        while (i < list.length && list[i]!.w === w && list[i]!.k < k) at += parts[i++]!.index!.count;
        o.push(at);
      }
      while (i < list.length && list[i]!.w === w) at += parts[i++]!.index!.count;
      offs.set(w, o);
    }
    const geo = mergeGeometries(parts, false);
    for (const p of parts) p.dispose();
    if (!geo?.index) {
      for (const e of list) if (e.k < wrecks[e.w]!.pieces.length) loose.push(e);
      continue;
    }
    const first = list[0]!.mesh;
    const mat = (first.material as THREE.MeshStandardMaterial).clone();
    mat.color.setRGB(1, 1, 1);
    mat.vertexColors = true;
    mat.name = `${mat.name}+${list.length - 1}`;
    const mesh = new THREE.Mesh(geo, mat);
    mesh.name = `wrecks_merged_${slices.length}`;
    mesh.castShadow = mesh.receiveShadow = true;
    for (const e of list) e.mesh.visible = false;
    slices.push({ mesh, index: geo.index, orig: (geo.index.array as Uint16Array | Uint32Array).slice(), offs });
  }
  return {
    meshes: slices.map((s) => s.mesh),
    setGone(w, gone) {
      for (const s of slices) {
        const o = s.offs.get(w);
        if (!o) continue;
        const from = o[0]!;
        const end = o[o.length - 1]!;
        const cut = o[THREE.MathUtils.clamp(gone, 0, o.length - 1)]!;
        if (end === from) continue;
        const arr = s.index.array as Uint16Array | Uint32Array;
        arr.fill(s.orig[from]!, from, cut);
        arr.set(s.orig.subarray(cut, end), cut);
        s.index.addUpdateRange(from, end - from);
        s.index.needsUpdate = true;
      }
      for (const e of loose) if (e.w === w) e.mesh.visible = e.k >= gone;
    },
    dispose() {
      for (const s of slices) {
        s.mesh.removeFromParent();
        s.mesh.geometry.dispose();
        (s.mesh.material as THREE.Material).dispose();
      }
    },
  };
}

/**
 * A Blender object with several materials arrives as a group of meshes, one per
 * material, each its own draw call. For rigid parts that's wasteful: this merges
 * a group's meshes that share a finish (roughness, metal or not) into one, with
 * each material's colour baked into vertex colours. Named animated parts stay
 * where they are; only the material split under each one is undone. With
 * `rough`, rough plain materials go together too, as for instanced props: not
 * for home's buildings, which are merged by material once they stand and need
 * to keep theirs shared.
 */
export function collapseMaterials(root: THREE.Object3D, rough = false): void {
  const groups: THREE.Object3D[] = [];
  root.traverse((o) => {
    if ((o as THREE.Mesh).isMesh || o.children.length < 2) return;
    const kids = o.children as THREE.Mesh[];
    if (!kids.every((c) => c.isMesh && c.children.length === 0 && !Array.isArray(c.material))) return;
    // Only the per-material split of one Blender object: the glTF loader names those
    // "Mesh", "Mesh_1", "Mesh_2"… and each has a different material. Sibling parts that
    // animate (legs, tendrils) have names of their own or share a material, and stay apart.
    const base = new Set(kids.map((c) => c.name.replace(/_\d+$/, "")));
    const mats = new Set(kids.map((c) => (c.material as THREE.Material).name));
    if (base.size === 1 && mats.size === kids.length) groups.push(o);
  });
  const white = new THREE.Color(1, 1, 1);
  for (const g of groups) {
    const buckets = new Map<string, THREE.Mesh[]>();
    for (const c of g.children as THREE.Mesh[]) {
      const key = (rough ? mergeKey : finishKey)(c.material as THREE.Material);
      if (!key) continue;
      const attrs = Object.keys(c.geometry.attributes).filter((k) => k !== "color").sort().join(",");
      const k = `${key}|${attrs}|${c.geometry.index ? "i" : "n"}`;
      const list = buckets.get(k);
      if (list) list.push(c);
      else buckets.set(k, [c]);
    }
    for (const meshes of buckets.values()) {
      if (meshes.length < 2) continue;
      const parts = meshes.map((m) => baked(m, m.matrix));
      const geo = mergeGeometries(parts, false);
      for (const p of parts) p.dispose();
      if (!geo) continue;
      const first = meshes[0]!;
      const mat = (first.material as THREE.MeshStandardMaterial).clone();
      mat.color.copy(white);
      mat.vertexColors = true;
      mat.name = `${mat.name}+${meshes.length - 1}`;
      const merged = new THREE.Mesh(geo, mat);
      merged.name = first.name;
      merged.castShadow = first.castShadow;
      merged.receiveShadow = first.receiveShadow;
      for (const m of meshes) g.remove(m);
      g.add(merged);
    }
  }
}
