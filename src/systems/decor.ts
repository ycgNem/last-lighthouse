import { DECOR, DECOR_RULES } from "../data/decor";
import type { DecorId, ItemStack } from "../data/ids";
import type { GameState, PlacedDecor } from "../state/GameState";
import { addItem, hasAll, removeAll } from "./inventory";

// Placing decor round the Rest: where a piece may stand, what it costs, and
// picking it back up for everything it cost. The level answers the questions
// about the ground through PlaceWorld, so this stays testable without three.

export interface PlaceWorld {
  /** Inside the village, where building is allowed. */
  inBounds(x: number, z: number): boolean;
  /** Ground height under a point, or null off the map. */
  groundY(x: number, z: number): number | null;
  /** Circles kept clear: plots, doors, paths, stations, people. */
  keepClear: readonly { x: number; z: number; r: number }[];
  highWater: number;
}

export type PlaceBlock = "bounds" | "slope" | "water" | "blocked" | "overlap" | "limit" | "cost";

/** The footprint's corners, turned and moved into place. */
export function footprint(kind: DecorId, x: number, z: number, yaw: number, grow = 0): [number, number][] {
  const [w, d] = DECOR[kind].size;
  const hx = w / 2 + grow;
  const hz = d / 2 + grow;
  const c = Math.cos(yaw);
  const s = Math.sin(yaw);
  // three.js rotation.y: local (lx, lz) lands at (lx·cos + lz·sin, −lx·sin + lz·cos).
  return ([[-hx, -hz], [hx, -hz], [hx, hz], [-hx, hz]] as const).map(([lx, lz]) => [x + lx * c + lz * s, z - lx * s + lz * c]);
}

/** Even-odd test: is (x, z) inside the outline (the village's, from home.glb's FX_decor_ points)? */
export function insideOutline(poly: readonly (readonly [number, number])[], x: number, z: number): boolean {
  let hit = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, zi] = poly[i]!;
    const [xj, zj] = poly[j]!;
    if (zi > z !== zj > z && x < ((xj - xi) * (z - zi)) / (zj - zi) + xi) hit = !hit;
  }
  return hit;
}

/** Separating-axis test for two convex outlines. */
function overlaps(a: [number, number][], b: [number, number][]): boolean {
  for (const poly of [a, b]) {
    for (let i = 0; i < poly.length; i++) {
      const [x1, z1] = poly[i]!;
      const [x2, z2] = poly[(i + 1) % poly.length]!;
      const nx = z1 - z2;
      const nz = x2 - x1;
      const project = (p: [number, number][]) => p.map(([x, z]) => x * nx + z * nz);
      const pa = project(a);
      const pb = project(b);
      if (Math.max(...pa) < Math.min(...pb) || Math.max(...pb) < Math.min(...pa)) return false;
    }
  }
  return true;
}

function touchesCircle(poly: [number, number][], cx: number, cz: number, r: number): boolean {
  // Inside, or within r of an edge.
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, zi] = poly[i]!;
    const [xj, zj] = poly[j]!;
    if (zi > cz !== zj > cz && cx < ((xj - xi) * (cz - zi)) / (zj - zi) + xi) inside = !inside;
    const ex = xj - xi;
    const ez = zj - zi;
    const t = Math.max(0, Math.min(1, ((cx - xi) * ex + (cz - zi) * ez) / (ex * ex + ez * ez)));
    if (Math.hypot(xi + ex * t - cx, zi + ez * t - cz) < r) return true;
  }
  return inside;
}

/** Why a piece can't go here, or null if it can. Doesn't look at the cost: see placeBlock. */
export function siteBlock(decor: readonly PlacedDecor[], world: PlaceWorld, kind: DecorId, x: number, z: number, yaw: number): PlaceBlock | null {
  const corners = footprint(kind, x, z, yaw);
  const pts: [number, number][] = [...corners, [x, z]];
  if (!pts.every(([px, pz]) => world.inBounds(px, pz))) return "bounds";
  const ys = pts.map(([px, pz]) => world.groundY(px, pz));
  if (ys.some((y) => y === null)) return "bounds";
  const heights = ys as number[];
  const [w, d] = DECOR[kind].size;
  if ((Math.max(...heights) - Math.min(...heights)) / Math.max(1, Math.hypot(w, d)) > DECOR_RULES.maxSlope) return "slope";
  if (Math.min(...heights) < world.highWater + DECOR_RULES.aboveHighWater) return "water";
  if (world.keepClear.some((c) => touchesCircle(corners, c.x, c.z, c.r))) return "blocked";
  const grown = footprint(kind, x, z, yaw, DECOR_RULES.gap / 2);
  if (decor.some((p) => overlaps(grown, footprint(p.kind, p.x, p.z, p.yaw, DECOR_RULES.gap / 2)))) return "overlap";
  return null;
}

/** Why the piece can't be placed here now, or null if it can. */
export function placeBlock(state: GameState, world: PlaceWorld, kind: DecorId, x: number, z: number, yaw: number): PlaceBlock | null {
  if (state.decor.length >= DECOR_RULES.max) return "limit";
  return siteBlock(state.decor, world, kind, x, z, yaw) ?? (hasAll(state, DECOR[kind].cost) ? null : "cost");
}

/** Places a piece, paying for it. Returns what stopped it, or null once it's down. */
export function placeDecor(state: GameState, world: PlaceWorld, kind: DecorId, x: number, z: number, yaw: number): PlaceBlock | null {
  const block = placeBlock(state, world, kind, x, z, yaw);
  if (block) return block;
  removeAll(state, DECOR[kind].cost);
  state.decor.push({ kind, x, z, yaw });
  return null;
}

/** The placed piece whose footprint is nearest a point (within `reach` of its outline), or -1. */
export function decorAt(state: GameState, x: number, z: number, reach = 0.3): number {
  let best = -1;
  let bestD = Infinity;
  state.decor.forEach((p, i) => {
    if (!touchesCircle(footprint(p.kind, p.x, p.z, p.yaw), x, z, reach)) return;
    const d = Math.hypot(p.x - x, p.z - z);
    if (d < bestD) {
      best = i;
      bestD = d;
    }
  });
  return best;
}

/** Picks a piece back up: everything it cost goes back in the satchel, or the chest when that's full. */
export function pickUpDecor(state: GameState, index: number): ItemStack[] {
  const piece = state.decor[index];
  if (!piece) return [];
  state.decor.splice(index, 1);
  for (const s of DECOR[piece.kind].cost) {
    const over = s.qty - addItem(state, s.item, s.qty);
    if (over > 0) state.storage[s.item] = (state.storage[s.item] ?? 0) + over;
  }
  return DECOR[piece.kind].cost.map((s) => ({ ...s }));
}
