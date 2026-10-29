import { readFileSync } from "node:fs";
import { join } from "node:path";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { describe, expect, it } from "vitest";
import { BALANCE } from "../src/data/balance";
import type { LocationId } from "../src/data/ids";
import { LOCATIONS } from "../src/data/locations";
import { NODES } from "../src/data/nodes";
import { TIDE, WATER_DEPTH } from "../src/data/tide";
import { GlbLevel } from "../src/world/LevelLoader";

// The "never trapped by the tide" sweep (GDD §6). Every spot you can stand on
// in each level is sampled on a 1 m grid, then joined to its neighbours the way
// the player moves: walk or jump up to a metre, drop any height, never through
// a wall, swim (feet under the surface, no jumping, only onto an edge below
// your middle), and after a few seconds of swimming get carried to the nearest
// anchor. Anywhere you can get to at some tide must lead back to the landing at
// low tide *and* at high tide, in every state progression leaves the level in.
// Buoyant crates, the rope ladder and long jumps are left out, so the check is
// pessimistic about getting home.

const CELL = 1;
/** A step you can always make: a standing jump clears about 1.08 m. */
const CLIMB = 1.0;
/** Swimming, you can only drag yourself onto an edge below your middle. */
const SWIM_CLIMB = BALANCE.player.radius;
const HEADROOM = 1.8;
const EYE = BALANCE.player.eyeHeight;
/** Rays round each column's centre, inside the player's radius: a crack between two slabs is not a hole. */
const FOOT = [
  [0, 0],
  [0.25, 0],
  [-0.25, 0],
  [0, 0.25],
  [0, -0.25],
] as const;
const DOWN = new THREE.Vector3(0, -1, 0);

interface Spot {
  x: number;
  y: number;
  z: number;
  col: number;
}

async function loadLevel(id: LocationId): Promise<GlbLevel> {
  const buf = readFileSync(join(import.meta.dirname, "..", "public", "assets", "models", "locations", `${id}.glb`));
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const gltf = await new GLTFLoader().parseAsync(ab, "");
  return new GlbLevel(id, gltf.scene);
}

function sweep(level: GlbLevel) {
  const col = level.collider;
  const box = col.geometry!.boundingBox ?? (col.geometry!.computeBoundingBox(), col.geometry!.boundingBox!);
  const nx = Math.ceil((box.max.x - box.min.x) / CELL);
  const nz = Math.ceil((box.max.z - box.min.z) / CELL);
  const spots: Spot[] = [];
  const columns: number[][] = Array.from({ length: nx * nz }, () => []);
  const from = new THREE.Vector3();
  /** Flat faces seen first from the open sky that point down: collision wound inside out. */
  const inverted: string[] = [];

  // Every flat surface in each column with room to stand under whatever's above it.
  for (let j = 0; j < nz; j++) {
    for (let i = 0; i < nx; i++) {
      const x = box.min.x + (i + 0.5) * CELL;
      const z = box.min.z + (j + 0.5) * CELL;
      const found: number[] = [];
      for (const [ox, oz] of FOOT) {
        let top = box.max.y + 5;
        let ceiling = Infinity;
        for (let layer = 0; layer < 8; layer++) {
          const hit = col.raycast(from.set(x + ox, top, z + oz), DOWN, top - box.min.y + 1);
          if (!hit) break;
          const ny = hit.face?.normal.y ?? 0;
          if (layer === 0 && ny < -0.65 && inverted.length < 8) inverted.push(`(${hit.point.x.toFixed(1)}, ${hit.point.y.toFixed(2)}, ${hit.point.z.toFixed(1)})`);
          // Floors face up; the undersides of things (and the bottoms of solids, from inside) don't.
          if (ny > 0.65 && ceiling - hit.point.y >= HEADROOM) found.push(hit.point.y);
          ceiling = hit.point.y;
          top = hit.point.y - 0.05;
        }
      }
      // Rays that land within a hand's breadth of each other found the same surface.
      found.sort((p, q) => q - p);
      let last = Infinity;
      for (const y of found) {
        if (last - y < 0.3) continue;
        columns[j * nx + i]!.push(spots.length);
        spots.push({ x, y, z, col: j * nx + i });
        last = y;
      }
    }
  }

  const nearest = (p: THREE.Vector3) => {
    let best = -1;
    let bestD = Infinity;
    for (let k = 0; k < spots.length; k++) {
      const s = spots[k]!;
      const d = (s.x - p.x) ** 2 + (s.y - p.y) ** 2 * 4 + (s.z - p.z) ** 2;
      if (d < bestD) {
        bestD = d;
        best = k;
      }
    }
    return best;
  };

  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  const clear = (s: Spot, t: Spot, h: number) => !col.blocked(a.set(s.x, h + 0.5, s.z), b.set(t.x, h + 0.5, t.z)) && !col.blocked(a.set(s.x, h + 1.5, s.z), b.set(t.x, h + 1.5, t.z));

  /** Where you can get to in one move from each spot, with the water at `waterY`. */
  const edges = (waterY: number): number[][] => {
    const anchors = level.anchors.map((p) => nearest(p));
    const out: number[][] = spots.map(() => []);
    spots.forEach((s, k) => {
      const swimming = waterY - s.y > WATER_DEPTH.swim;
      const feet = swimming ? Math.max(s.y, waterY - WATER_DEPTH.swimFeet) : s.y;
      const reach = feet + (swimming ? SWIM_CLIMB : CLIMB);
      const ci = s.col % nx;
      const cj = Math.floor(s.col / nx);
      for (let dj = -1; dj <= 1; dj++) {
        for (let di = -1; di <= 1; di++) {
          if (!di && !dj) continue;
          const i = ci + di;
          const j = cj + dj;
          if (i < 0 || j < 0 || i >= nx || j >= nz) continue;
          // You land on the highest surface you can reach in the next column.
          let land = -1;
          for (const n of columns[j * nx + i]!) if (spots[n]!.y <= reach && (land < 0 || spots[n]!.y > spots[land]!.y)) land = n;
          if (land < 0) continue;
          if (clear(s, spots[land]!, Math.max(feet, spots[land]!.y))) out[k]!.push(land);
        }
      }
      if (swimming) {
        // The current carries you to the nearest anchor (PlayerController.rescue).
        let best = -1;
        let bestD = Infinity;
        level.anchors.forEach((p, ai) => {
          const d = (p.x - s.x) ** 2 + (p.y - feet) ** 2 + (p.z - s.z) ** 2;
          if (d < bestD) {
            bestD = d;
            best = anchors[ai]!;
          }
        });
        if (best >= 0) out[k]!.push(best);
      }
    });
    return out;
  };

  const flood = (start: number, adj: number[][]) => {
    const seen = new Uint8Array(spots.length);
    const queue = [start];
    seen[start] = 1;
    while (queue.length) {
      const k = queue.pop()!;
      for (const n of adj[k]!) if (!seen[n]) (seen[n] = 1), queue.push(n);
    }
    return seen;
  };
  const reverse = (adj: number[][]) => {
    const r: number[][] = spots.map(() => []);
    adj.forEach((list, k) => list.forEach((n) => r[n]!.push(k)));
    return r;
  };

  const landing = nearest(level.spawnFor("landing").position);
  const low = edges(TIDE.lowLevel);
  const high = edges(TIDE.highLevel);
  // Anywhere you can get to, given time for the tide to turn.
  const reachable = flood(landing, low.map((l, k) => [...l, ...high[k]!]));
  const trapped = (adj: number[][]) => {
    const home = flood(landing, reverse(adj));
    const out: Spot[] = [];
    for (let k = 0; k < spots.length; k++) if (reachable[k] && !home[k]) out.push(spots[k]!);
    return out;
  };
  const fmt = (list: Spot[]) => list.slice(0, 8).map((s) => `(${s.x.toFixed(1)}, ${s.y.toFixed(2)}, ${s.z.toFixed(1)})`);
  /** True if you can stand somewhere you reach with `p` within `range` of your eyes. */
  const within = (p: THREE.Vector3, range: number) => spots.some((s, k) => reachable[k] && Math.hypot(s.x - p.x, s.y + EYE - p.y, s.z - p.z) <= range);
  return {
    inverted,
    spots: spots.length,
    reachable: reachable.reduce((n, v) => n + v, 0),
    trappedLow: fmt(trapped(low)),
    trappedHigh: fmt(trapped(high)),
    within,
  };
}

/** Every combination of the progression flags the level shows or hides things for. */
function flagSets(level: GlbLevel): string[][] {
  const flags = [...new Set(level.stateObjects.map((s) => s.flag))];
  return Array.from({ length: 2 ** flags.length }, (_, m) => flags.filter((_, i) => m & (1 << i)));
}

const REMOTE = (Object.keys(LOCATIONS) as LocationId[]).filter((l) => l !== "home");

describe.each(REMOTE)("tide sweep: %s", (id) => {
  it("every spot you can reach leads back to the landing at low and at high tide", async () => {
    const level = await loadLevel(id);
    for (const flags of flagSets(level)) {
      level.applyFlags(flags);
      const r = sweep(level);
      const when = flags.length ? ` (${flags.join(", ")})` : "";
      expect(r.inverted, `collision wound inside out (floors must face up)${when}`).toEqual([]);
      expect(r.reachable, `the landing should open onto most of the level${when}`).toBeGreaterThan(r.spots * 0.3);
      expect(r.trappedLow, `stuck at low tide${when}`).toEqual([]);
      expect(r.trappedHigh, `stuck at high tide${when}`).toEqual([]);
    }
  }, 60_000);

  it("every gathering node and interactable can be reached once progression opens the way", async () => {
    const level = await loadLevel(id);
    level.applyFlags([...new Set(level.stateObjects.map((s) => s.flag))]);
    const r = sweep(level);
    const missed: string[] = [];
    // GatherNode's reach: fishing spots are cast to from up to 10 m, everything else is within arm's length.
    for (const n of level.nodes) if (!r.within(n.position, NODES[n.node].kind === "fish" ? 10 : 3.4 + 0.6)) missed.push(n.node);
    const at = new THREE.Vector3();
    for (const it of level.interacts) if (!r.within(it.object.getWorldPosition(at), it.range + 0.6)) missed.push(it.id);
    expect(missed).toEqual([]);
  }, 60_000);
});
