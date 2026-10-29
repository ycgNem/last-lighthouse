import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

// Static batching: every mesh in a level that never moves, hides or changes
// material is merged with the others that share its material, so the whole
// set costs one draw call (twice, with the shadow pass) instead of one per
// prop and per material slot. The originals stay in the scene, hidden, so
// anything that reads their transforms (collision, focus rays) is unaffected.

export interface BatchResult {
  group: THREE.Group;
  /** Meshes merged away (now hidden). */
  merged: number;
  /** Draw calls (per pass) before and after. */
  before: number;
  after: number;
  dispose(): void;
}

const flip = new THREE.Matrix4();

/** One merge bucket: everything with this material, these attributes and these shadow flags. */
function bucketKey(mesh: THREE.Mesh): string {
  const g = mesh.geometry;
  const attrs = Object.keys(g.attributes)
    .sort()
    .map((k) => {
      const a = g.getAttribute(k);
      return `${k}:${a.itemSize}:${a.normalized ? 1 : 0}`;
    })
    .join(",");
  const mat = mesh.material as THREE.Material;
  return `${mat.uuid}|${attrs}|${g.index ? "i" : "n"}|${mesh.castShadow ? 1 : 0}${mesh.receiveShadow ? 1 : 0}|${mesh.renderOrder}`;
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
 * Merges the static meshes under `root`. `keep(o)` returns true for anything
 * that must stay separate (it and everything under it): things that move,
 * hide, swap materials or are picked by the player. Only visible leaf meshes
 * with one visible material are merged; a bucket of one is left alone.
 */
export function batchStatic(root: THREE.Object3D, keep: (o: THREE.Object3D) => boolean): BatchResult {
  root.updateMatrixWorld(true);
  const toRoot = root.matrixWorld.clone().invert();
  const buckets = new Map<string, THREE.Mesh[]>();
  let before = 0;

  const visit = (o: THREE.Object3D) => {
    if (!o.visible || keep(o)) return;
    const mesh = o as THREE.Mesh;
    if (mesh.isMesh && !(mesh as THREE.SkinnedMesh).isSkinnedMesh && !(mesh as THREE.InstancedMesh).isInstancedMesh && !mesh.morphTargetInfluences) {
      const mat = mesh.material;
      if (!Array.isArray(mat) && mat.visible) {
        before++;
        if (o.children.length === 0) {
          const key = bucketKey(mesh);
          const list = buckets.get(key);
          if (list) list.push(mesh);
          else buckets.set(key, [mesh]);
        }
      }
    }
    for (const c of o.children) visit(c);
  };
  visit(root);

  const group = new THREE.Group();
  group.name = "static_batch";
  const made: THREE.BufferGeometry[] = [];
  let merged = 0;
  let after = before;
  for (const meshes of buckets.values()) {
    if (meshes.length < 2) continue;
    const parts: THREE.BufferGeometry[] = [];
    for (const m of meshes) {
      const g = m.geometry.clone();
      const mx = flip.multiplyMatrices(toRoot, m.matrixWorld);
      g.applyMatrix4(mx);
      if (mx.determinant() < 0) flipWinding(g);
      // Only what every material here reads: groups and morphs would break the merge.
      g.clearGroups();
      parts.push(g);
    }
    const geo = mergeGeometries(parts, false);
    for (const p of parts) p.dispose();
    if (!geo) continue;
    const first = meshes[0]!;
    const batch = new THREE.Mesh(geo, first.material);
    batch.castShadow = first.castShadow;
    batch.receiveShadow = first.receiveShadow;
    batch.renderOrder = first.renderOrder;
    batch.name = `batch_${(first.material as THREE.Material).name || "material"}`;
    group.add(batch);
    made.push(geo);
    for (const m of meshes) m.visible = false;
    merged += meshes.length;
    after -= meshes.length - 1;
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

/**
 * A Blender object with several materials arrives as a group of meshes, one per
 * material, each its own draw call. For rigid parts that's wasteful: this merges
 * a group's meshes that share a finish (roughness, metal or not) into one, with
 * each material's colour baked into vertex colours. Named animated parts stay
 * where they are; only the material split under each one is undone.
 */
export function collapseMaterials(root: THREE.Object3D): void {
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
      const key = finishKey(c.material as THREE.Material);
      if (!key) continue;
      const attrs = Object.keys(c.geometry.attributes).filter((k) => k !== "color").sort().join(",");
      const k = `${key}|${attrs}|${c.geometry.index ? "i" : "n"}`;
      const list = buckets.get(k);
      if (list) list.push(c);
      else buckets.set(k, [c]);
    }
    for (const meshes of buckets.values()) {
      if (meshes.length < 2) continue;
      const parts = meshes.map((m) => {
        const geo = m.geometry.clone();
        geo.applyMatrix4(m.matrix);
        geo.clearGroups();
        const tint = (m.material as THREE.MeshStandardMaterial).color;
        const n = geo.getAttribute("position").count;
        const had = geo.getAttribute("color") as THREE.BufferAttribute | undefined;
        const useOld = had && (m.material as THREE.MeshStandardMaterial).vertexColors;
        const col = new Float32Array(n * 3);
        for (let i = 0; i < n; i++) {
          const r = useOld ? had.getX(i) : 1;
          const gg = useOld ? had.getY(i) : 1;
          const b = useOld ? had.getZ(i) : 1;
          col[i * 3] = r * tint.r;
          col[i * 3 + 1] = gg * tint.g;
          col[i * 3 + 2] = b * tint.b;
        }
        geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
        return geo;
      });
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
