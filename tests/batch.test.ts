import * as THREE from "three";
import { describe, expect, it } from "vitest";
import { batchMeshes, batchStatic, instanceParts, mergePieces, staticMeshes } from "../src/world/Batch";

// Draw-call savings: scenery merges by finish, home merges its finished
// buildings by material (and must be able to undo that when another one
// stands), a place's wrecks draw merged with their pieces blanked as they tear
// off, and instanced props draw their rough plain materials as one
// vertex-coloured part.

const std = (name: string, color: number, roughness: number, metalness = 0, emissive = 0) =>
  Object.assign(new THREE.MeshStandardMaterial({ color, roughness, metalness, emissive, emissiveIntensity: emissive ? 2 : 1 }), { name });

function box(mat: THREE.Material, x: number, y = 0, z = 0): THREE.Mesh {
  const m = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), mat);
  m.position.set(x, y, z);
  return m;
}

describe("batchMeshes", () => {
  it("merges what shares a material, hides the originals, and shows them again on dispose", () => {
    const root = new THREE.Group();
    root.position.set(100, 0, 0);
    const stone = std("stone", 0x888888, 0.9);
    const glass = std("glass", 0xaaccff, 0.1);
    const building = new THREE.Group();
    const a = box(stone, 0);
    const b = box(stone, 5);
    const c = box(glass, 2);
    building.add(a, b, c);
    root.add(building);

    const batch = batchMeshes(root, staticMeshes(building), "plot_batch");
    expect(batch.group.children).toHaveLength(1);
    const merged = batch.group.children[0] as THREE.Mesh;
    expect(merged.material).toBe(stone);
    merged.geometry.computeBoundingBox();
    // In the root's own space: the boxes at x 0 and 5, not shifted by the root's 100.
    expect(merged.geometry.boundingBox!.min.x).toBeCloseTo(-0.5);
    expect(merged.geometry.boundingBox!.max.x).toBeCloseTo(5.5);
    expect([a.visible, b.visible, c.visible]).toEqual([false, false, true]);
    expect(a.userData.batched).toBe(true);

    batch.dispose();
    expect(batch.group.parent).toBeNull();
    expect([a.visible, b.visible, c.visible]).toEqual([true, true, true]);
    expect(a.userData.batched).toBeUndefined();
    // So batching again after another building stands takes the same meshes back.
    expect(staticMeshes(building)).toHaveLength(3);
  });
});

describe("batchStatic", () => {
  it("merges scenery by finish, rough plain materials together with their colours baked, and leaves patched materials whole", () => {
    const wood = std("wood", 0x8a6f52, 0.82);
    const stone = std("stone", 0x888888, 0.93);
    const iron = std("iron", 0x444444, 0.55, 0.6);
    const tide = std("TIDE_rock", 0x556655, 0.9);
    tide.onBeforeCompile = () => {};
    const root = new THREE.Group();
    const crate = box(wood, 12);
    crate.name = "NODE_crate";
    root.add(box(wood, 0), box(stone, 2), box(iron, 4), box(iron, 6), box(tide, 8), box(tide, 10), crate);

    const batch = batchStatic(root, (o) => o.name.startsWith("NODE_"));
    expect([batch.before, batch.after, batch.merged]).toEqual([6, 3, 6]);
    const meshes = batch.group.children as THREE.Mesh[];
    // The tide's flood glow is a patch on its own material, so that one is drawn as it is.
    expect(meshes.filter((m) => m.material === tide)).toHaveLength(1);
    const rough = meshes.find((m) => (m.material as THREE.Material).name.startsWith("wood"))!;
    expect((rough.material as THREE.MeshStandardMaterial).vertexColors).toBe(true);
    const pos = rough.geometry.getAttribute("position");
    const col = rough.geometry.getAttribute("color");
    for (let i = 0; i < pos.count; i++) expect(col.getX(i)).toBeCloseTo(pos.getX(i) > 1 ? stone.color.r : wood.color.r);
    expect(crate.visible).toBe(true);

    batch.dispose();
    expect(root.children.every((o) => o.visible)).toBe(true);
  });
});

describe("mergePieces", () => {
  it("draws a place's wrecks merged by finish, and tears pieces off (and puts them back) by blanking their triangles", () => {
    const wood = std("wood", 0x8a6f52, 0.82);
    const cloth = std("cloth", 0x334455, 0.96);
    const iron = std("iron", 0x444444, 0.55, 0.6);
    const lamp = std("lamp", 0xffffff, 0.85, 0, 0xffb347);
    const hull = new THREE.Group();
    hull.position.set(10, 0, 0);
    const first = new THREE.Group();
    first.add(box(wood, 0, 2), box(iron, 1, 2));
    const second = new THREE.Group();
    second.add(box(wood, 0, 4), box(lamp, 0, 5));
    // Out of order under the wreck: the order given is what counts.
    hull.add(box(wood, 0), second, first);
    const raft = new THREE.Group();
    raft.position.set(-10, 0, 0);
    const plank = box(wood, 0, 1);
    raft.add(box(cloth, 0), plank);

    const batch = mergePieces([
      { root: hull, pieces: [first, second] },
      { root: raft, pieces: [plank] },
    ]);
    // Rough plain wood and cloth together, and iron; the glowing lamp keeps its own material.
    expect(batch.meshes).toHaveLength(2);
    const rough = batch.meshes.find((m) => (m.material as THREE.Material).name.startsWith("wood"))!;
    const metal = batch.meshes.find((m) => (m.material as THREE.Material).name.startsWith("iron"))!;
    expect((rough.material as THREE.MeshStandardMaterial).vertexColors).toBe(true);
    expect(rough.geometry.getAttribute("color").getX(0)).toBeCloseTo(wood.color.r);
    // In world space: both wrecks, 10 m either side.
    rough.geometry.computeBoundingBox();
    expect(rough.geometry.boundingBox!.min.x).toBeCloseTo(-10.5);
    expect(rough.geometry.boundingBox!.max.x).toBeCloseTo(10.5);
    // The originals are hidden, all but what couldn't merge.
    const shown = (root: THREE.Object3D) => {
      const out: string[] = [];
      root.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m.isMesh && m.visible) out.push((m.material as THREE.Material).name);
      });
      return out;
    };
    expect([...shown(hull), ...shown(raft)]).toEqual(["lamp"]);

    // Triangles still drawn (a torn piece's collapse to a point); a box is 12.
    const drawn = (m: THREE.Mesh) => {
      const a = m.geometry.index!.array;
      let n = 0;
      for (let i = 0; i < a.length; i += 3) if (a[i] !== a[i + 1] || a[i] !== a[i + 2]) n++;
      return n;
    };
    expect([drawn(rough), drawn(metal)]).toEqual([60, 12]);
    batch.setGone(0, 1);
    expect([drawn(rough), drawn(metal)]).toEqual([48, 0]);
    expect(rough.geometry.index!.updateRanges.length).toBeGreaterThan(0);
    batch.setGone(0, 2);
    expect(drawn(rough)).toBe(36);
    expect(shown(hull)).toEqual([]);
    // The other wreck is its own: its plank goes, its bones stay.
    batch.setGone(1, 1);
    expect(drawn(rough)).toBe(24);
    // A restock puts them back as they were.
    batch.setGone(0, 0);
    batch.setGone(1, 0);
    expect([drawn(rough), drawn(metal)]).toEqual([60, 12]);
    expect(shown(hull)).toEqual(["lamp"]);

    const scene = new THREE.Scene();
    scene.add(...batch.meshes);
    batch.dispose();
    expect(scene.children).toHaveLength(0);
  });
});

describe("instanceParts", () => {
  it("draws rough plain materials as one part and keeps metal and glowing ones apart", () => {
    const wood = std("wood", 0x8a6f52, 0.82);
    const cloth = std("cloth", 0x334455, 0.96);
    const iron = std("iron", 0x444444, 0.55, 0.6);
    const lamp = std("lamp", 0xffffff, 0.85, 0, 0xffb347);
    const src = new THREE.Group();
    src.add(box(wood, 0), box(cloth, 0, 2), box(iron, 3), box(lamp, 0, 0, 4));

    const parts = instanceParts(src);
    expect(parts).toHaveLength(3);
    const rough = parts.find((p) => (p.material as THREE.Material).name === "wood+1")!;
    expect(rough).toBeDefined();
    expect(parts.some((p) => p.material === iron)).toBe(true);
    expect(parts.some((p) => p.material === lamp)).toBe(true);

    const mat = rough.material as THREE.MeshStandardMaterial;
    expect(mat.vertexColors).toBe(true);
    expect(mat.color.getHex()).toBe(0xffffff);
    // Each box keeps its own colour and place: the cloth one 2 m up.
    const pos = rough.geometry.getAttribute("position");
    const col = rough.geometry.getAttribute("color");
    const woodTint = wood.color;
    const clothTint = cloth.color;
    for (let i = 0; i < pos.count; i++) {
      const tint = pos.getY(i) > 1 ? clothTint : woodTint;
      expect(col.getX(i)).toBeCloseTo(tint.r);
      expect(col.getZ(i)).toBeCloseTo(tint.b);
    }
    expect(rough.matrix.equals(new THREE.Matrix4())).toBe(true);
  });
});
