import * as THREE from "three";

// The headland's grass top: one flat, vertex-coloured disc with the worn
// paths, the square and the doorsteps painted in, so there are no decal
// strips to float or flicker. HomeLevel's cylinder stays the collision; this
// is only the look.

export type Segment = readonly [number, number, number, number];

/** A worn patch: centre, radius, strength 0..1. */
export interface Worn {
  x: number;
  z: number;
  r: number;
  k: number;
}

const GRASS_DARK = new THREE.Color(0x4c5c3a);
const GRASS_LIGHT = new THREE.Color(0x6a794a);
const DRY = new THREE.Color(0x868052);
const DIRT = new THREE.Color(0x857760);
const GRAVEL = new THREE.Color(0x9b907a);

function hash(x: number, z: number): number {
  let h = Math.imul(x | 0, 374761393) + Math.imul(z | 0, 668265263);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

/** Smooth value noise in [0, 1]. */
export function noise2(x: number, z: number): number {
  const ix = Math.floor(x);
  const iz = Math.floor(z);
  const fx = x - ix;
  const fz = z - iz;
  const ux = fx * fx * (3 - 2 * fx);
  const uz = fz * fz * (3 - 2 * fz);
  const a = hash(ix, iz);
  const b = hash(ix + 1, iz);
  const c = hash(ix, iz + 1);
  const d = hash(ix + 1, iz + 1);
  return a + (b - a) * ux + (c - a) * uz + (a - b - c + d) * ux * uz;
}

function fbm(x: number, z: number): number {
  return noise2(x, z) * 0.6 + noise2(x * 2.1 + 17, z * 2.1) * 0.3 + noise2(x * 4.3, z * 4.3 + 5) * 0.1;
}

const smooth = (e0: number, e1: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
};

/** Distance from (px, pz) to a segment. */
export function segmentDistance(px: number, pz: number, [ax, az, bx, bz]: Segment): number {
  const dx = bx - ax;
  const dz = bz - az;
  const len2 = dx * dx + dz * dz;
  const t = len2 === 0 ? 0 : Math.min(1, Math.max(0, ((px - ax) * dx + (pz - az) * dz) / len2));
  return Math.hypot(px - (ax + t * dx), pz - (az + t * dz));
}

/** How worn the ground is at (x, z): 1 on a path's crown, 0 on open grass. */
export function wear(x: number, z: number, paths: readonly Segment[], worn: readonly Worn[]): number {
  const wobble = (noise2(x * 0.7, z * 0.7) - 0.5) * 0.7;
  let k = 0;
  for (const s of paths) k = Math.max(k, smooth(1.75, 0.85, segmentDistance(x, z, s) + wobble));
  for (const w of worn) k = Math.max(k, w.k * smooth(w.r, w.r * 0.45, Math.hypot(x - w.x, z - w.z) + wobble));
  return k;
}

export function headlandTop(radius: number, y: number, paths: readonly Segment[], worn: readonly Worn[]): THREE.Mesh {
  // Rings a metre apart, all with the same number of segments (about a metre at the rim).
  const rings = Math.round(radius);
  const segs = 256;
  const pos: number[] = [];
  const col: number[] = [];
  const c = new THREE.Color();
  const g = new THREE.Color();
  const vertex = (x: number, z: number) => {
    const n = fbm(x * 0.11, z * 0.11);
    const n2 = fbm(x * 0.43 + 7, z * 0.43);
    g.copy(GRASS_DARK).lerp(GRASS_LIGHT, n).lerp(DRY, smooth(0.62, 0.82, n2) * 0.55);
    const r = Math.hypot(x, z);
    g.multiplyScalar(1 - smooth(radius - 3, radius, r) * 0.12);
    c.copy(DIRT).lerp(GRAVEL, n2);
    g.lerp(c, wear(x, z, paths, worn));
    pos.push(x, y, z);
    col.push(g.r, g.g, g.b);
  };
  vertex(0, 0);
  for (let k = 1; k <= rings; k++) {
    const r = (radius * k) / rings;
    for (let i = 0; i < segs; i++) {
      const a = (i / segs) * Math.PI * 2;
      vertex(Math.cos(a) * r, Math.sin(a) * r);
    }
  }
  const idx: number[] = [];
  const at = (k: number, i: number) => 1 + (k - 1) * segs + (i % segs);
  for (let i = 0; i < segs; i++) idx.push(0, at(1, i + 1), at(1, i));
  for (let k = 1; k < rings; k++) {
    for (let i = 0; i < segs; i++) {
      idx.push(at(k, i), at(k, i + 1), at(k + 1, i + 1));
      idx.push(at(k, i), at(k + 1, i + 1), at(k + 1, i));
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
  geo.setIndex(idx);
  geo.computeVertexNormals();
  const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 }));
  mesh.receiveShadow = true;
  mesh.name = "headland_top";
  return mesh;
}
