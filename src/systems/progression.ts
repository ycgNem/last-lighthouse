import { BALANCE } from "../data/balance";
import { LOCATION_IDS, type GearId, type LocationId, type NpcId, type StageIndex, type StationId } from "../data/ids";
import { GEAR, type GearSlot } from "../data/items";
import { DEFAULT_STATIONS, PROJECTS, STAGES, type Requirements, type StageDef } from "../data/lighthouse";
import { LOCATIONS } from "../data/locations";
import { NPCS } from "../data/npcs";
import type { GameState } from "../state/GameState";
import { addItem, available, removeAll } from "./inventory";
import { addXp, skillLevel } from "./skills";

export interface Missing {
  items: { item: string; need: number; have: number }[];
  keyItems: string[];
  projects: string[];
  flags: string[];
  /** The lighthouse stage still to reach, if any. */
  stage: StageIndex | null;
}

export function missingFor(state: GameState, req: Requirements): Missing {
  return {
    items: (req.items ?? []).filter((s) => available(state, s.item) < s.qty).map((s) => ({ item: s.item, need: s.qty, have: available(state, s.item) })),
    keyItems: (req.keyItems ?? []).filter((k) => !state.keyItems.includes(k)),
    projects: (req.projects ?? []).filter((p) => !state.projects.includes(p)),
    flags: (req.flags ?? []).filter((f) => !state.flags.includes(f)),
    stage: req.stage !== undefined && state.stage < req.stage ? req.stage : null,
  };
}

export function isMet(m: Missing): boolean {
  return m.items.length + m.keyItems.length + m.projects.length + m.flags.length === 0 && m.stage === null;
}

/** Owns this gear, or better in the same slot. */
export function hasGear(owned: Iterable<GearId>, need: GearId): boolean {
  for (const g of owned) if (g === need || (GEAR[g].slot === GEAR[need].slot && GEAR[g].tier > GEAR[need].tier)) return true;
  return false;
}

/** The best gear owned for a slot, or null. */
export function bestGear(owned: Iterable<GearId>, slot: GearSlot): GearId | null {
  let best: GearId | null = null;
  for (const g of owned) if (GEAR[g].slot === slot && (!best || GEAR[g].tier > GEAR[best].tier)) best = g;
  return best;
}

/** Whether someone has come home to the Rest yet. */
export function isHome(state: GameState, id: NpcId): boolean {
  const a = NPCS[id].arrives;
  return "stage" in a ? state.stage >= a.stage : state.projects.includes(a.project);
}

export function nextStage(state: GameState): StageDef | undefined {
  return STAGES[state.stage + 1];
}

export function stationsAvailable(state: GameState): StationId[] {
  const out = [...DEFAULT_STATIONS];
  for (const p of state.projects) {
    const st = PROJECTS[p].unlocksStation;
    if (st) out.push(st);
  }
  return out;
}

export function canTravelOffshore(state: GameState): boolean {
  return state.projects.some((p) => PROJECTS[p].unlocksOffshore);
}

export function revealedLocations(state: GameState): LocationId[] {
  return LOCATION_IDS.filter((id) => LOCATIONS[id].revealedAtStage <= state.stage);
}

export function maxHp(state: GameState): number {
  let hp = BALANCE.player.baseHp + (skillLevel(state, "combat") - 1) * BALANCE.player.hpPerCombatLevel;
  for (const g of state.gear) hp += GEAR[g].stats.maxHp ?? 0;
  return hp;
}

/** Performs the next lighthouse stage if requirements are met at `here`. */
export function advanceStage(state: GameState, here: LocationId): StageDef | undefined {
  const next = nextStage(state);
  if (!next || next.performedAt !== here) return undefined;
  if (!isMet(missingFor(state, next.requires))) return undefined;
  removeAll(state, next.requires.items ?? []);
  state.keyItems = state.keyItems.filter((k) => !next.consumesKeyItems.includes(k));
  for (const k of next.grantsKeyItems) addItem(state, k, 1);
  if (next.xp) addXp(state, next.xp.skill, next.xp.amount);
  state.stage = next.index as StageIndex;
  return next;
}
