import * as THREE from "three";
import { describe, expect, it } from "vitest";
import { batchMeshes, instanceParts, staticMeshes } from "../src/world/Batch";

// Draw-call savings: home merges its finished buildings by material (and must
// be able to undo that when another one stands), and instanced props draw
// their rough plain materials as one vertex-coloured part.

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
