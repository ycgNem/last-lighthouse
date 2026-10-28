// Every content id in the game. Tables in src/data are keyed by these unions,
// so a typo in a recipe or location is a compile error, not a runtime bug.

export const ITEM_IDS = [
  "timber",
  "scrap",
  "brass",
  "sea_glass",
  "kelp",
  "tidestone",
  "iron_ingot",
  "silverfin",
  "glowgill",
  "crab_meat",
  "grilled_silverfin",
  "kelp_wrap",
  "crab_chowder",
  "glowgill_stew",
  "drowned_lens",
  "lighthouse_ember",
] as const;
export type ItemId = (typeof ITEM_IDS)[number];

export const GEAR_IDS = [
  "boltcaster_mk1",
  "boltcaster_mk2",
  "lamplighter",
  "rod_basic",
  "rod_reinforced",
  "satchel_straps",
  "tidebreaker_coat",
] as const;
export type GearId = (typeof GEAR_IDS)[number];

export const SKILL_IDS = ["fishing", "salvaging", "cooking", "smithing", "combat"] as const;
export type SkillId = (typeof SKILL_IDS)[number];

export const NODE_IDS = [
  "driftwood",
  "scrap_pile",
  "kelp_bed",
  "glass_bed",
  "reinforced_wreckage",
  "supply_crate",
  "sealed_cache",
  "strongbox",
  "fish_silverfin",
  "fish_glowgill",
  "lens_pedestal",
] as const;
export type NodeId = (typeof NODE_IDS)[number];

export const ENEMY_IDS = [
  "brine_crab",
  "drowned_spitter",
  "lantern_wisp",
  "tide_lurker",
  "wreck_guardian",
] as const;
export type EnemyId = (typeof ENEMY_IDS)[number];

export const LOCATION_IDS = ["home", "shore", "wreck", "beacon"] as const;
export type LocationId = (typeof LOCATION_IDS)[number];

export const PROJECT_IDS = ["forge", "dock"] as const;
export type ProjectId = (typeof PROJECT_IDS)[number];

export const STATION_IDS = ["hearth", "forge"] as const;
export type StationId = (typeof STATION_IDS)[number];

export const NPC_IDS = ["maren", "tib", "odile", "hesk"] as const;
export type NpcId = (typeof NPC_IDS)[number];

export const FLAG_IDS = ["met_maren", "guardian_defeated", "chapter1_complete"] as const;
export type FlagId = (typeof FLAG_IDS)[number];

/** Lighthouse stage index: 0 Failing Light … 3 First Beacon Relit. */
export type StageIndex = 0 | 1 | 2 | 3;

export type TideReq = "low" | "high" | "any";

export interface ItemStack {
  item: ItemId;
  qty: number;
}

/** A yield roll. `min > 0` means it's a guaranteed source (the validator cares). */
export interface Yield {
  item: ItemId;
  min: number;
  max: number;
}
