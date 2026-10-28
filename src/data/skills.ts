import type { SkillId } from "./ids";

export const MAX_LEVEL = 10;

/** Total XP needed to *reach* each level. Index 0 = level 1. */
export const XP_TABLE: readonly number[] = [0, 40, 100, 190, 310, 470, 680, 940, 1260, 1650];

export interface Milestone {
  level: number;
  text: string;
}

export interface SkillDef {
  name: string;
  purpose: string;
  milestones: Milestone[];
}

export const SKILLS: Record<SkillId, SkillDef> = {
  fishing: {
    name: "Fishing",
    purpose: "Catches the ingredients that become healing food.",
    milestones: [
      { level: 1, text: "Catch Silverfin at any tide." },
      { level: 3, text: "Spot-reading: fishing spots show from 40 m." },
      { level: 4, text: "Catch Glowgill at high tide (needs Reinforced Rod)." },
      { level: 7, text: "Fish bite faster." },
      { level: 10, text: "Keeper's catch: occasional double catch." },
    ],
  },
  salvaging: {
    name: "Salvaging",
    purpose: "Recovers timber, metal and glass from the drowned world.",
    milestones: [
      { level: 1, text: "Salvage driftwood, scrap piles and kelp." },
      { level: 2, text: "Harvest sea-glass beds at low tide." },
      { level: 4, text: "Break down reinforced wreckage for brass." },
      { level: 6, text: "Open sealed caches." },
      { level: 9, text: "Salvage 30% faster." },
    ],
  },
  cooking: {
    name: "Cooking",
    purpose: "Turns your catch into expedition supplies.",
    milestones: [
      { level: 1, text: "Grilled Silverfin." },
      { level: 3, text: "Kelp-wrapped Fish." },
      { level: 5, text: "Crab Chowder (+20 max HP for 3 min)." },
      { level: 7, text: "Glowgill Stew (faster dash for 3 min)." },
    ],
  },
  smithing: {
    name: "Smithing",
    purpose: "Makes and improves your equipment at the forge.",
    milestones: [
      { level: 1, text: "Smelt iron ingots. Satchel Straps." },
      { level: 2, text: "Reinforced Rod." },
      { level: 4, text: "Bolt-caster Mk II." },
      { level: 6, text: "Tidebreaker Coat." },
      { level: 8, text: "Lamplighter." },
    ],
  },
  combat: {
    name: "Combat",
    purpose: "Modest growth: +5 max HP per level.",
    milestones: [
      { level: 5, text: "Second dash charge." },
      { level: 8, text: "Hold fire to charge a heavy bolt." },
    ],
  },
};
