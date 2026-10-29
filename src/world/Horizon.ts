import * as THREE from "three";
import type { Assets } from "../core/Assets";
import type { LocationId } from "../data/ids";
import { HORIZON } from "../data/scenery";
import { batchStatic, type BatchResult } from "./Batch";

/**
 * The drowned world round a location (src/data/scenery.ts): rooftops, a spire,
 * a telegraph line walking out to sea, stacks, a dead light, all far past where
 * you can go. One static batch with no shadows (they're well outside the shadow
 * camera), so the whole horizon costs a draw call per material.
 */
export class Horizon {
  readonly root = new THREE.Group();
  private readonly batch: BatchResult;

  constructor(assets: Assets, id: LocationId) {
    this.root.name = "horizon";
    for (const p of HORIZON[id]) {
      const piece = assets.clone("scenery.glb", `SCENE_${p.piece}`);
      if (!piece) continue;
      const len = Math.hypot(p.x, p.z) || 1;
      // Facing in: local +z toward the centre. Radial: local +x out to sea.
      const yaw = p.radial ? Math.atan2(-p.z / len, p.x / len) : Math.atan2(-p.x, -p.z);
      piece.position.set(p.x, 0, p.z);
      piece.rotation.y = yaw + (p.turn ?? 0);
      piece.scale.setScalar(p.scale ?? 1);
      piece.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m.isMesh) m.castShadow = m.receiveShadow = false;
      });
      this.root.add(piece);
    }
    this.batch = batchStatic(this.root, () => false);
  }

  dispose(): void {
    this.batch.dispose();
    this.root.removeFromParent();
  }
}
