import type { GearId } from "../data/ids";
import { GEAR } from "../data/items";
import type { RecipeDef } from "../data/recipes";
import type { GameState } from "../state/GameState";
import { addItem, hasAll, removeAll } from "./inventory";
import { stationsAvailable } from "./progression";
import { addXp, skillLevel, type XpResult } from "./skills";

export type CraftBlock = "station" | "level" | "gear_required" | "already_owned" | "materials" | "satchel_full";

export function craftBlock(state: GameState, r: RecipeDef): CraftBlock | null {
  if (!stationsAvailable(state).includes(r.station)) return "station";
  if (skillLevel(state, r.skill) < r.level) return "level";
  if (r.requiresGear && !state.gear.includes(r.requiresGear)) return "gear_required";
  if (r.output.kind === "gear" && ownsGearAtOrAbove(state, r.output.gear)) return "already_owned";
  if (!hasAll(state, r.inputs)) return "materials";
  return null;
}

function ownsGearAtOrAbove(state: GameState, gear: GearId): boolean {
  const def = GEAR[gear];
  return state.gear.some((g) => g === gear || (GEAR[g].slot === def.slot && GEAR[g].tier > def.tier));
}

export interface CraftResult {
  ok: boolean;
  block: CraftBlock | null;
  xp?: XpResult;
}

export function craft(state: GameState, r: RecipeDef): CraftResult {
  const block = craftBlock(state, r);
  if (block) return { ok: false, block };
  removeAll(state, r.inputs);
  if (r.output.kind === "item") {
    // Crafted output goes to storage when the satchel is full — crafting only happens at home.
    const fit = addItem(state, r.output.item, r.output.qty);
    const overflow = r.output.qty - fit;
    if (overflow > 0) state.storage[r.output.item] = (state.storage[r.output.item] ?? 0) + overflow;
  } else {
    state.gear.push(r.output.gear);
  }
  state.quest.crafted[r.id] = (state.quest.crafted[r.id] ?? 0) + 1;
  return { ok: true, block: null, xp: addXp(state, r.skill, r.xp) };
}
