import type { GearId, ItemId, ItemStack, SkillId, StationId } from "./ids";

export type RecipeOutput = { kind: "item"; item: ItemId; qty: number } | { kind: "gear"; gear: GearId };

export interface RecipeDef {
  id: string;
  station: StationId;
  skill: SkillId;
  level: number;
  inputs: ItemStack[];
  output: RecipeOutput;
  xp: number;
  /** Gear that must already be owned (e.g. Mk II before Lamplighter). */
  requiresGear?: GearId;
}

export const RECIPES: readonly RecipeDef[] = [
  // Hearth: always available.
  { id: "grilled_silverfin", station: "hearth", skill: "cooking", level: 1, inputs: [{ item: "silverfin", qty: 1 }], output: { kind: "item", item: "grilled_silverfin", qty: 1 }, xp: 10 },
  { id: "kelp_wrap", station: "hearth", skill: "cooking", level: 3, inputs: [{ item: "silverfin", qty: 1 }, { item: "kelp", qty: 1 }], output: { kind: "item", item: "kelp_wrap", qty: 1 }, xp: 18 },
  { id: "crab_chowder", station: "hearth", skill: "cooking", level: 5, inputs: [{ item: "crab_meat", qty: 2 }, { item: "kelp", qty: 1 }], output: { kind: "item", item: "crab_chowder", qty: 1 }, xp: 30 },
  { id: "glowgill_stew", station: "hearth", skill: "cooking", level: 7, inputs: [{ item: "glowgill", qty: 1 }, { item: "crab_meat", qty: 1 }], output: { kind: "item", item: "glowgill_stew", qty: 1 }, xp: 40 },

  // Smokehouse.
  { id: "smoked_silverfin", station: "smokehouse", skill: "cooking", level: 1, inputs: [{ item: "silverfin", qty: 1 }], output: { kind: "item", item: "smoked_silverfin", qty: 1 }, xp: 12 },

  // Forge.
  { id: "iron_ingot", station: "forge", skill: "smithing", level: 1, inputs: [{ item: "scrap", qty: 2 }], output: { kind: "item", item: "iron_ingot", qty: 1 }, xp: 12 },
  { id: "hook_iron", station: "forge", skill: "smithing", level: 1, inputs: [{ item: "iron_ingot", qty: 3 }, { item: "kelp", qty: 2 }], output: { kind: "gear", gear: "hook_iron" }, xp: 30 },
  { id: "satchel_straps", station: "forge", skill: "smithing", level: 1, inputs: [{ item: "kelp", qty: 6 }, { item: "iron_ingot", qty: 2 }], output: { kind: "gear", gear: "satchel_straps" }, xp: 30 },
  { id: "rod_reinforced", station: "forge", skill: "smithing", level: 2, inputs: [{ item: "timber", qty: 4 }, { item: "iron_ingot", qty: 3 }], output: { kind: "gear", gear: "rod_reinforced" }, xp: 40 },
  { id: "boltcaster_mk2", station: "forge", skill: "smithing", level: 4, inputs: [{ item: "iron_ingot", qty: 6 }, { item: "brass", qty: 4 }, { item: "tidestone", qty: 3 }], output: { kind: "gear", gear: "boltcaster_mk2" }, xp: 80 },
  { id: "tidebreaker_coat", station: "forge", skill: "smithing", level: 6, inputs: [{ item: "iron_ingot", qty: 5 }, { item: "kelp", qty: 8 }, { item: "tidestone", qty: 4 }], output: { kind: "gear", gear: "tidebreaker_coat" }, xp: 100 },
  { id: "lamplighter", station: "forge", skill: "smithing", level: 8, inputs: [{ item: "brass", qty: 8 }, { item: "tidestone", qty: 8 }, { item: "sea_glass", qty: 4 }], output: { kind: "gear", gear: "lamplighter" }, xp: 150, requiresGear: "boltcaster_mk2" },

  // Net loft.
  { id: "hook_brass", station: "net_loft", skill: "salvaging", level: 3, inputs: [{ item: "brass", qty: 4 }, { item: "kelp", qty: 6 }, { item: "iron_ingot", qty: 2 }], output: { kind: "gear", gear: "hook_brass" }, xp: 60, requiresGear: "hook_iron" },
];

export function getRecipe(id: string): RecipeDef | undefined {
  return RECIPES.find((r) => r.id === id);
}
