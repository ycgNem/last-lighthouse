import type { GearId, ItemId, NodeId, SkillId, TideReq, Yield } from "./ids";

export interface NodeDef {
  name: string;
  /** Prompt verb: "[E] Salvage Driftwood". */
  verb: string;
  skill: SkillId | null;
  level: number;
  requiresGear?: GearId;
  tide: TideReq;
  /** Seconds of hold-to-gather. Fishing nodes use the bite minigame instead. */
  gatherTime: number;
  yields: Yield[];
  xp: number;
  /** How many times it can be gathered per visit. */
  uses: number;
  /** Key items are given once ever and never respawn. */
  keyItem?: ItemId;
  kind: "gather" | "fish" | "container" | "key";
}

export const NODES: Record<NodeId, NodeDef> = {
  driftwood: { name: "Driftwood", verb: "Salvage", kind: "gather", skill: "salvaging", level: 1, tide: "any", gatherTime: 0.9, yields: [{ item: "timber", min: 2, max: 3 }], xp: 8, uses: 1 },
  scrap_pile: { name: "Scrap Pile", verb: "Salvage", kind: "gather", skill: "salvaging", level: 1, tide: "any", gatherTime: 1.1, yields: [{ item: "scrap", min: 2, max: 3 }], xp: 10, uses: 1 },
  kelp_bed: { name: "Kelp Bed", verb: "Harvest", kind: "gather", skill: "salvaging", level: 1, tide: "low", gatherTime: 0.7, yields: [{ item: "kelp", min: 2, max: 3 }], xp: 6, uses: 2 },
  glass_bed: { name: "Sea-glass Bed", verb: "Sift", kind: "gather", skill: "salvaging", level: 2, tide: "low", gatherTime: 1.0, yields: [{ item: "sea_glass", min: 1, max: 2 }], xp: 12, uses: 2 },
  reinforced_wreckage: { name: "Reinforced Wreckage", verb: "Break down", kind: "gather", skill: "salvaging", level: 4, tide: "any", gatherTime: 1.4, yields: [{ item: "brass", min: 2, max: 3 }, { item: "scrap", min: 1, max: 2 }], xp: 25, uses: 1 },
  supply_crate: { name: "Supply Crate", verb: "Open", kind: "container", skill: null, level: 1, tide: "any", gatherTime: 0.6, yields: [{ item: "tidestone", min: 1, max: 1 }, { item: "timber", min: 1, max: 2 }], xp: 0, uses: 1 },
  sealed_cache: { name: "Sealed Cache", verb: "Pry open", kind: "container", skill: "salvaging", level: 6, tide: "any", gatherTime: 1.5, yields: [{ item: "tidestone", min: 2, max: 2 }, { item: "brass", min: 2, max: 2 }, { item: "sea_glass", min: 2, max: 2 }], xp: 40, uses: 1 },
  strongbox: { name: "Captain's Strongbox", verb: "Open", kind: "container", skill: null, level: 1, tide: "any", gatherTime: 0.8, yields: [{ item: "tidestone", min: 4, max: 4 }, { item: "brass", min: 3, max: 3 }], xp: 0, uses: 1 },
  fish_silverfin: { name: "Fishing Spot", verb: "Fish", kind: "fish", skill: "fishing", level: 1, requiresGear: "rod_basic", tide: "any", gatherTime: 0, yields: [{ item: "silverfin", min: 1, max: 1 }], xp: 10, uses: 6 },
  fish_glowgill: { name: "Glowgill Shoal", verb: "Fish", kind: "fish", skill: "fishing", level: 4, requiresGear: "rod_reinforced", tide: "high", gatherTime: 0, yields: [{ item: "glowgill", min: 1, max: 1 }], xp: 22, uses: 4 },
  lens_pedestal: { name: "Drowned Lens", verb: "Take", kind: "key", skill: null, level: 1, tide: "any", gatherTime: 0.8, yields: [], xp: 0, uses: 1, keyItem: "drowned_lens" },
};
