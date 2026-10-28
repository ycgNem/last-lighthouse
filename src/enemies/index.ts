import * as THREE from "three";
import type { Assets } from "../core/Assets";
import { ENEMIES } from "../data/enemies";
import type { EnemyId } from "../data/ids";
import { BrineCrab } from "./BrineCrab";
import { DrownedSpitter } from "./DrownedSpitter";
import type { Enemy } from "./Enemy";
import { LanternWisp } from "./LanternWisp";
import { TideLurker } from "./TideLurker";
import { WreckGuardian } from "./WreckGuardian";

/** Placeholder if enemies.glb is missing: a coloured blob of the right size. */
function placeholder(color: number, size: number): THREE.Object3D {
  const m = new THREE.Mesh(new THREE.SphereGeometry(size, 12, 8), new THREE.MeshStandardMaterial({ color }));
  m.position.y = size;
  const g = new THREE.Group();
  g.add(m);
  return g;
}

export function createEnemy(id: EnemyId, at: THREE.Vector3, assets: Assets): Enemy {
  const def = ENEMIES[id];
  const model = assets.clone("enemies.glb", `MODEL_${id}`);
  switch (id) {
    case "brine_crab":
      return new BrineCrab(id, def, model ?? placeholder(0x8a3b2a, 0.5), at, 0.6);
    case "drowned_spitter":
      return new DrownedSpitter(id, def, model ?? placeholder(0x4f5e57, 0.8), at, 0.9);
    case "lantern_wisp":
      return new LanternWisp(id, def, model ?? placeholder(0x3dffb0, 0.4), at, 0.5);
    case "tide_lurker":
      return new TideLurker(id, def, model ?? placeholder(0x1f2b33, 0.9), at, 1.0);
    case "wreck_guardian":
      return new WreckGuardian(id, def, model ?? placeholder(0x33281f, 3), at, 3);
  }
}

export type { Enemy };
