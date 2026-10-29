import { FLOTSAM_IDS, type FlotsamId, type GearId, type ItemId, type ItemStack, type Yield } from "../data/ids";
import { GEAR } from "../data/items";
import { FLOTSAM, HOOK, SALVAGE, type Water } from "../data/salvage";
import { TIDE } from "../data/tide";
import type { GameState } from "../state/GameState";
import { fitsAll } from "./inventory";
import { bestGear } from "./progression";
import { skillLevel } from "./skills";
import { cycleLength, readTide } from "./tide";

// The cove's sums: how often the sea brings something in and what, what the
// hook can do, and what was waiting when you come home. Shared by the game
// (src/gather), the pacing simulation and the tests.

export type Rng = () => number;

/** Low and falling water bring in low-water drift; the flood and high water the rest. */
const oddsKey = (water: Water): "low" | "high" => (water === "low" || water === "falling" ? "low" : "high");

/** What drifts in next at this water, from a roll in [0, 1). */
export function flotsamFor(water: Water, roll: number): FlotsamId {
  const key = oddsKey(water);
  const total = FLOTSAM_IDS.reduce((n, id) => n + FLOTSAM[id].odds[key], 0);
  let r = roll * total;
  let last: FlotsamId = FLOTSAM_IDS[0];
  for (const id of FLOTSAM_IDS) {
    if (FLOTSAM[id].odds[key] <= 0) continue;
    last = id;
    r -= FLOTSAM[id].odds[key];
    if (r < 0) return id;
  }
  return last;
}

/** Whether something that gives these has anywhere to go: at least one of them would fit in the satchel. */
export function roomFor(state: GameState, yields: readonly Yield[]): boolean {
  return yields.some((y) => y.max > 0 && fitsAll(state, [{ item: y.item, qty: 1 }]));
}

/** Each yield rolled between its min and max. */
export function rollYields(yields: readonly Yield[], rng: Rng): ItemStack[] {
  const out: ItemStack[] = [];
  for (const y of yields) {
    const qty = y.min + Math.floor(rng() * (y.max - y.min + 1));
    if (qty > 0) out.push({ item: y.item, qty });
  }
  return out;
}

/** What one piece drifting in at this water gives, on average. */
export function expectedPiece(water: Water): Map<ItemId, number> {
  const key = oddsKey(water);
  const total = FLOTSAM_IDS.reduce((n, id) => n + FLOTSAM[id].odds[key], 0);
  const out = new Map<ItemId, number>();
  for (const id of FLOTSAM_IDS) {
    const share = FLOTSAM[id].odds[key] / total;
    for (const y of FLOTSAM[id].yields) out.set(y.item, (out.get(y.item) ?? 0) + (share * (y.min + y.max)) / 2);
  }
  return out;
}

/** Share of the drift at some water that's this kind. The validator counts only kinds common enough to rely on. */
export function flotsamShare(id: FlotsamId): number {
  return Math.max(...(["low", "high"] as const).map((k) => FLOTSAM[id].odds[k] / FLOTSAM_IDS.reduce((n, f) => n + FLOTSAM[f].odds[k], 0)));
}

export interface HookStats {
  gear: GearId | null;
  /** Metres it reaches. */
  range: number;
  /** Metres a second it reels a light piece in. */
  reel: number;
  /** Chance a wreck gives up two pieces to one pull. */
  double: number;
}

/** The best hook owned, with the salvaging perks on top. */
export function hookStats(state: GameState): HookStats {
  const gear = bestGear(state.gear, "hook");
  const level = skillLevel(state, "salvaging");
  const stats = gear ? GEAR[gear].stats : {};
  const P = HOOK.perks;
  const bonus = Math.max(0, ...P.reel.filter((r) => level >= r.level).map((r) => r.bonus));
  return {
    gear,
    range: (stats.hookRange ?? 0) + (level >= P.range.level ? P.range.metres : 0),
    reel: (stats.reelSpeed ?? 0) * (1 + bonus),
    double: level >= P.double.level ? P.double.chance : 0,
  };
}

/** Pieces drifting in, on average, between two times on the tide clock. */
export function driftBetween(from: number, to: number): number {
  let n = 0;
  for (let t = from; t < to; ) {
    const r = readTide(t, TIDE);
    const step = Math.max(1e-6, Math.min(r.phaseTimeLeft, to - t));
    n += step / SALVAGE.driftEvery[r.phase];
    t += step;
  }
  return n;
}

/**
 * What drifted in while you were away, between two times on the tide clock:
 * the cove net (once the Net Loft stands) holds some, some washes up on the
 * beach, the rest drifts back out. Added to what's already there, to the caps.
 */
export function awayCatch(state: GameState, from: number, to: number, rng: Rng): { beach: FlotsamId[]; net: FlotsamId[] } {
  const beach: FlotsamId[] = [];
  const net: FlotsamId[] = [];
  const hasNet = state.projects.includes("net_loft");
  let beachRoom = SALVAGE.beachMax - state.cove.beach.length;
  let netRoom = hasNet ? SALVAGE.net.max - state.cove.net.length : 0;
  for (let t = from; t < to && (beachRoom > 0 || netRoom > 0); ) {
    const water = readTide(t, TIDE).phase;
    t += SALVAGE.driftEvery[water];
    if (t > to) break;
    const piece = flotsamFor(water, rng());
    const r = rng();
    if (netRoom > 0 && r < SALVAGE.net.share) {
      net.push(piece);
      netRoom--;
    } else if (beachRoom > 0 && r < (hasNet ? SALVAGE.net.share : 0) + SALVAGE.awayBeachShare) {
      beach.push(piece);
      beachRoom--;
    }
  }
  return { beach, net };
}

/** Which low tide a time on the tide clock belongs to, counted from the new game: the wreck field restocks as each starts. */
export function lowTideIndex(elapsed: number): number {
  return Math.floor(elapsed / cycleLength(TIDE));
}

/** Pieces left on one of the cove's wrecks (`key`: its marker) this low tide. */
export function wreckLeft(state: GameState, key: string, full: number, elapsed: number): number {
  const w = state.cove.wrecks;
  return w.tide === lowTideIndex(elapsed) ? (w.left[key] ?? full) : full;
}

/** Tears pieces off one of the cove's wrecks. Returns how many are left. */
export function tearWreck(state: GameState, key: string, full: number, elapsed: number, pieces = 1): number {
  const tide = lowTideIndex(elapsed);
  const left = Math.max(0, wreckLeft(state, key, full, elapsed) - pieces);
  if (state.cove.wrecks.tide !== tide) state.cove.wrecks = { tide, left: {} };
  state.cove.wrecks.left[key] = left;
  return left;
}
