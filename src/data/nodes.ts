import type { GearId, ItemId, NodeId, SkillId, TideReq, Yield } from "./ids";

export interface NodeDef {
  name: string;
  /** Prompt verb: "[E] Open Captain's Strongbox". Wreckage is hooked, so its verb is what the hook does. */
  verb: string;
  skill: SkillId | null;
  /** Skill level needed. Wreckage asks for none: the hook it needs is its only gate. */
  level: number;
  requiresGear?: GearId;
  tide: TideReq;
  /** Seconds of hold-E to open a container or take a key item. Fishing uses the bite minigame; wreckage is hooked. */
  gatherTime: number;
  /** What one use gives: for wreckage, each piece torn off. */
  yields: Yield[];
  xp: number;
  /** Uses per visit; for wreckage, the pieces it comes apart into. At home the cove's spots refill each low tide. */
  uses: number;
  /** Key items are given once ever and never respawn. */
  keyItem?: ItemId;
  kind: "wreckage" | "fish" | "container" | "key";
}

export const NODES: Record<NodeId, NodeDef> = {
  // Wreckage: every throw of the hook tears a piece off, which flies to you.
  driftwood: { name: "Driftwood", verb: "Hook", kind: "wreckage", skill: "salvaging", level: 1, tide: "any", gatherTime: 0, yields: [{ item: "timber", min: 1, max: 2 }], xp: 4, uses: 2 },
  scrap_pile: { name: "Scrap Pile", verb: "Hook", kind: "wreckage", skill: "salvaging", level: 1, tide: "any", gatherTime: 0, yields: [{ item: "scrap", min: 1, max: 2 }], xp: 5, uses: 2 },
  kelp_bed: { name: "Kelp Bed", verb: "Hook", kind: "wreckage", skill: "salvaging", level: 1, tide: "low", gatherTime: 0, yields: [{ item: "kelp", min: 1, max: 2 }], xp: 3, uses: 3 },
  reinforced_wreckage: { name: "Reinforced Wreckage", verb: "Hook", kind: "wreckage", skill: "salvaging", level: 1, requiresGear: "hook_iron", tide: "any", gatherTime: 0, yields: [{ item: "brass", min: 1, max: 1 }, { item: "scrap", min: 0, max: 1 }], xp: 9, uses: 3 },
  // The Rest's cove floor, bared at low water.
  sunken_boat: { name: "Sunken Boat", verb: "Hook", kind: "wreckage", skill: "salvaging", level: 1, tide: "low", gatherTime: 0, yields: [{ item: "timber", min: 1, max: 2 }], xp: 5, uses: 6 },
  old_pilings: { name: "Old Pilings", verb: "Hook", kind: "wreckage", skill: "salvaging", level: 1, tide: "low", gatherTime: 0, yields: [{ item: "timber", min: 1, max: 1 }, { item: "kelp", min: 0, max: 1 }], xp: 4, uses: 3 },
  boiler: { name: "Rusted Boiler", verb: "Hook", kind: "wreckage", skill: "salvaging", level: 1, tide: "low", gatherTime: 0, yields: [{ item: "scrap", min: 1, max: 2 }], xp: 6, uses: 5 },

  strongbox: { name: "Captain's Strongbox", verb: "Open", kind: "container", skill: null, level: 1, tide: "any", gatherTime: 0.8, yields: [{ item: "tidestone", min: 4, max: 4 }, { item: "brass", min: 3, max: 3 }], xp: 0, uses: 1 },
  fish_silverfin: { name: "Fishing Spot", verb: "Fish", kind: "fish", skill: "fishing", level: 1, requiresGear: "rod_basic", tide: "any", gatherTime: 0, yields: [{ item: "silverfin", min: 1, max: 1 }], xp: 10, uses: 6 },
  fish_glowgill: { name: "Glowgill Shoal", verb: "Fish", kind: "fish", skill: "fishing", level: 1, requiresGear: "rod_reinforced", tide: "high", gatherTime: 0, yields: [{ item: "glowgill", min: 1, max: 1 }], xp: 22, uses: 4 },
  lens_pedestal: { name: "Drowned Lens", verb: "Take", kind: "key", skill: null, level: 1, tide: "any", gatherTime: 0.8, yields: [], xp: 0, uses: 1, keyItem: "drowned_lens" },
};
