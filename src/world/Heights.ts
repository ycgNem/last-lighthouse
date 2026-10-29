import * as THREE from "three";
import { TIDE } from "../data/tide";
import type { StaticCollider } from "../physics/StaticCollider";

// Two heights for every half-metre of a level, sampled from its collision
// once when it loads, for the shaders: the sea floor (the water's depth colour,
// shore foam and how much the waves calm in the shallows) and the first surface
// rain would hit (so it stops at roofs and decks instead of falling through).

const CELL = 0.5;
const MAX_CELLS = 512;
const MARGIN = 8;
/** Open sea: off the map, or nothing under the water at all. */
export const OPEN_SEA = -12;
/** Under a rock or a cliff: no water shows here anyway. */
const UNDER_LAND = 10;
const NO_ROOF = -100;
/** Past the edge of a level's modelled sea floor, the bottom shelves away this steeply. */
export const SHELF_SLOPE = 0.18;

const UP = new THREE.Vector3(0, 1, 0);
const from = new THREE.Vector3();

export class LevelHeights {
  /** R: sea floor, G: rain floor. Half floats, linearly filtered. */
  readonly texture: THREE.DataTexture;
  /** (minX, minZ, 1/width, 1/depth): world XZ → texture UV is (xz - rect.xy) * rect.zw. */
  readonly rect = new THREE.Vector4();
  private readonly data: Uint16Array;
  private readonly w: number;
  private readonly h: number;

  constructor(collider: StaticCollider) {
    const geo = collider.geometry;
    const box = new THREE.Box3(new THREE.Vector3(-40, 0, -40), new THREE.Vector3(40, 0, 40));
    if (geo) {
      geo.computeBoundingBox();
      box.copy(geo.boundingBox!);
    }
    box.expandByVector(new THREE.Vector3(MARGIN, 0, MARGIN));
    const sizeX = box.max.x - box.min.x;
    const sizeZ = box.max.z - box.min.z;
    this.w = Math.min(MAX_CELLS, Math.ceil(sizeX / CELL));
    this.h = Math.min(MAX_CELLS, Math.ceil(sizeZ / CELL));
    this.rect.set(box.min.x, box.min.z, 1 / sizeX, 1 / sizeZ);

    // Rays for the sea floor start above the highest wave of the highest tide.
    const seaTop = TIDE.highLevel + 1.5;
    const w = this.w;
    const h = this.h;
    const floor = new Float32Array(w * h);
    const roof = new Float32Array(w * h);
    for (let j = 0; j < h; j++) {
      const z = box.min.z + ((j + 0.5) / h) * sizeZ;
      for (let i = 0; i < w; i++) {
        const x = box.min.x + ((i + 0.5) / w) * sizeX;
        let y = collider.groundHeight(x, z, seaTop, 40);
        if (y === -Infinity) {
          // Nothing below: open water, unless we started inside a rock or a cliff.
          from.set(x, seaTop, z);
          y = collider.raycast(from, UP, 60) ? UNDER_LAND : NaN;
        }
        floor[j * w + i] = y;
        const r = collider.groundHeight(x, z, 80, 200);
        roof[j * w + i] = r === -Infinity ? NO_ROOF : r;
      }
    }
    shelve(floor, w, h, (sizeX / w + sizeZ / h) / 2);

    this.data = new Uint16Array(w * h * 2);
    const toHalf = THREE.DataUtils.toHalfFloat;
    for (let k = 0; k < w * h; k++) {
      this.data[k * 2] = toHalf(floor[k]!);
      this.data[k * 2 + 1] = toHalf(roof[k]!);
    }
    this.texture = new THREE.DataTexture(this.data, this.w, this.h, THREE.RGFormat, THREE.HalfFloatType);
    this.texture.magFilter = THREE.LinearFilter;
    this.texture.minFilter = THREE.LinearFilter;
    this.texture.wrapS = this.texture.wrapT = THREE.ClampToEdgeWrapping;
    this.texture.needsUpdate = true;
  }

  /** Where rain stops at (x, z): the roof, deck or ground, or far below if nothing's there. */
  rainFloor(x: number, z: number): number {
    const i = Math.floor((x - this.rect.x) * this.rect.z * this.w);
    const j = Math.floor((z - this.rect.y) * this.rect.w * this.h);
    if (i < 0 || j < 0 || i >= this.w || j >= this.h) return NO_ROOF;
    return THREE.DataUtils.fromHalfFloat(this.data[(j * this.w + i) * 2 + 1]!);
  }

  dispose(): void {
    this.texture.dispose();
  }
}

/**
 * Fills the open-water cells (NaN) so the bottom shelves away from the nearest
 * modelled sea floor instead of dropping off a cliff at the edge of it (which
 * would draw a hard line in the water's colour). Two-pass chamfer distance;
 * rock and cliff cells don't spread.
 */
function shelve(floor: Float32Array, w: number, h: number, cell: number): void {
  const out = new Float32Array(floor.length);
  for (let k = 0; k < floor.length; k++) {
    const v = floor[k]!;
    out[k] = Number.isNaN(v) ? -Infinity : v === UNDER_LAND ? -Infinity : v;
  }
  const diag = cell * Math.SQRT2;
  const relax = (k: number, n: number, d: number) => {
    const v = out[n]! - SHELF_SLOPE * d;
    if (v > out[k]!) out[k] = v;
  };
  for (let j = 0; j < h; j++) {
    for (let i = 0; i < w; i++) {
      const k = j * w + i;
      if (!Number.isNaN(floor[k]!)) continue;
      if (i > 0) relax(k, k - 1, cell);
      if (j > 0) relax(k, k - w, cell);
      if (i > 0 && j > 0) relax(k, k - w - 1, diag);
      if (i < w - 1 && j > 0) relax(k, k - w + 1, diag);
    }
  }
  for (let j = h - 1; j >= 0; j--) {
    for (let i = w - 1; i >= 0; i--) {
      const k = j * w + i;
      if (!Number.isNaN(floor[k]!)) continue;
      if (i < w - 1) relax(k, k + 1, cell);
      if (j < h - 1) relax(k, k + w, cell);
      if (i < w - 1 && j < h - 1) relax(k, k + w + 1, diag);
      if (i > 0 && j < h - 1) relax(k, k + w - 1, diag);
    }
  }
  for (let k = 0; k < floor.length; k++) {
    if (Number.isNaN(floor[k]!)) floor[k] = Math.max(OPEN_SEA, out[k]!);
  }
}

/** A stand-in before any level is loaded: open sea everywhere, no roofs. */
export function openSea(): { texture: THREE.DataTexture; rect: THREE.Vector4 } {
  const half = THREE.DataUtils.toHalfFloat;
  const tex = new THREE.DataTexture(new Uint16Array([half(OPEN_SEA), half(NO_ROOF)]), 1, 1, THREE.RGFormat, THREE.HalfFloatType);
  tex.needsUpdate = true;
  return { texture: tex, rect: new THREE.Vector4(-1e5, -1e5, 1e-9, 1e-9) };
}
