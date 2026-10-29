import type { FlagId, ItemId, ItemStack, LocationId, NpcId, ProjectId, SkillId, StageIndex, StationId } from "./ids";

export interface Requirements {
  items?: ItemStack[];
  keyItems?: ItemId[];
  projects?: ProjectId[];
  flags?: FlagId[];
  /** Lighthouse stage reached. */
  stage?: StageIndex;
}

/** What a stage looks like in the world. Read by the home location each frame. */
export interface StageVisuals {
  beamColor: number;
  beamLength: number;
  beamIntensity: number;
  /** 0 = steady, 1 = badly flickering. */
  flicker: number;
  fogFar: number;
  /** Boats moored at the jetty once it stands. */
  boats: number;
}

export interface StageDef {
  index: StageIndex;
  name: string;
  description: string;
  requires: Requirements;
  /** Where the upgrade is performed. */
  performedAt: LocationId;
  reveals: LocationId[];
  grantsKeyItems: ItemId[];
  consumesKeyItems: ItemId[];
  npcArrivals: NpcId[];
  xp?: { skill: SkillId; amount: number };
  visuals: StageVisuals;
}

export const STAGES: readonly StageDef[] = [
  {
    index: 0,
    name: "Failing Light",
    description: "The lamp gutters. Nothing past the point is safe to reach.",
    requires: {},
    performedAt: "home",
    reveals: [],
    grantsKeyItems: [],
    consumesKeyItems: [],
    npcArrivals: [],
    visuals: { beamColor: 0xffb347, beamLength: 40, beamIntensity: 0.35, flicker: 0.8, fogFar: 160, boats: 1 },
  },
  {
    index: 1,
    name: "Restored Lamp",
    description: "Repair the lamp housing. A steady beam reaches the Meridian.",
    requires: { items: [{ item: "scrap", qty: 14 }, { item: "sea_glass", qty: 10 }, { item: "timber", qty: 8 }], projects: ["forge", "jetty", "cottage_1"] },
    performedAt: "home",
    reveals: ["wreck"],
    grantsKeyItems: [],
    consumesKeyItems: [],
    npcArrivals: ["hesk"],
    xp: { skill: "smithing", amount: 60 },
    visuals: { beamColor: 0xfff1c9, beamLength: 90, beamIntensity: 0.7, flicker: 0.05, fogFar: 230, boats: 1 },
  },
  {
    index: 2,
    name: "Focused Lens",
    description: "Seat the Drowned Lens. The beam burns a path to Saltmere.",
    requires: { keyItems: ["drowned_lens"], items: [{ item: "brass", qty: 8 }, { item: "tidestone", qty: 5 }] },
    performedAt: "home",
    reveals: ["beacon"],
    grantsKeyItems: ["lighthouse_ember"],
    consumesKeyItems: ["drowned_lens"],
    npcArrivals: [],
    xp: { skill: "smithing", amount: 90 },
    visuals: { beamColor: 0xe9fff4, beamLength: 160, beamIntensity: 1.0, flicker: 0, fogFar: 320, boats: 2 },
  },
  {
    index: 3,
    name: "First Beacon Relit",
    description: "Saltmere burns again. The coast remembers what light looks like.",
    requires: { flags: ["guardian_defeated"], keyItems: ["lighthouse_ember"] },
    performedAt: "beacon",
    reveals: [],
    grantsKeyItems: [],
    consumesKeyItems: ["lighthouse_ember"],
    npcArrivals: [],
    visuals: { beamColor: 0xe9fff4, beamLength: 170, beamIntensity: 1.0, flicker: 0, fogFar: 380, boats: 2 },
  },
];

export interface ProjectDef {
  name: string;
  /** The board on the plot while it's a ruin. */
  ruin: string;
  description: string;
  /** What it does for you once it stands, one line on the build panel. */
  perk: string;
  /**
   * Materials are handed in a few at a time, whenever you have them; the rest
   * (an earlier rebuild, a lighthouse stage) must hold before the plot takes any.
   */
  requires: Requirements;
  unlocksStation?: StationId;
  /** The boat moors here: expeditions leave from it. */
  unlocksOffshore?: boolean;
  /** The family that moves in (FAMILIES in villagers.ts). Named people say when they arrive in npcs.ts. */
  family?: number;
  xp?: { skill: SkillId; amount: number };
}

export const PROJECTS: Record<ProjectId, ProjectDef> = {
  forge: {
    name: "The Forge",
    ruin: "The old forge",
    description: "A new hood and bellows, and the anvil back on its block.",
    perk: "Smelt iron and smith gear: the Iron Hook, a better rod, a better bolt-caster.",
    requires: { items: [{ item: "scrap", qty: 8 }, { item: "timber", qty: 6 }] },
    unlocksStation: "forge",
    xp: { skill: "smithing", amount: 25 },
  },
  jetty: {
    name: "The Jetty",
    ruin: "Where the jetty stood",
    description: "Pilings driven into the cove floor, a plank deck and kelp-rope fenders.",
    perk: "Tib brings the boat in: expeditions leave from the jetty. Fish off the end at high water.",
    requires: { items: [{ item: "timber", qty: 18 }, { item: "kelp", qty: 6 }] },
    unlocksOffshore: true,
    xp: { skill: "salvaging", amount: 30 },
  },
  cottage_1: {
    name: "Marsh Cottage",
    ruin: "The Marsh place",
    description: "A roof, a door, and glass in the windows again.",
    perk: "Odile comes home and keeps the hearth.",
    requires: { items: [{ item: "timber", qty: 16 }, { item: "scrap", qty: 8 }, { item: "sea_glass", qty: 4 }] },
    xp: { skill: "salvaging", amount: 30 },
  },
  cottage_2: {
    name: "Pell Cottage",
    ruin: "The Pell place",
    description: "Rafters, slates and a chimney that draws.",
    perk: "The Pells come home: Wenna and her two.",
    requires: { items: [{ item: "timber", qty: 18 }, { item: "scrap", qty: 8 }, { item: "sea_glass", qty: 6 }], stage: 1 },
    family: 0,
    xp: { skill: "salvaging", amount: 40 },
  },
  cottage_3: {
    name: "Ashby Cottage",
    ruin: "The Ashby place",
    description: "The biggest house in the Rest, and the worst hit.",
    perk: "The Ashbys come home.",
    requires: { items: [{ item: "timber", qty: 22 }, { item: "scrap", qty: 10 }, { item: "sea_glass", qty: 8 }, { item: "brass", qty: 2 }], stage: 2 },
    family: 1,
    xp: { skill: "salvaging", amount: 50 },
  },
  net_loft: {
    name: "The Net Loft",
    ruin: "The old net loft",
    description: "A loft to hang and mend nets in, and a net across the cove.",
    perk: "Make the Brass Hook here. The cove net holds what drifts in while you're away.",
    requires: { items: [{ item: "timber", qty: 12 }, { item: "kelp", qty: 10 }, { item: "scrap", qty: 4 }], projects: ["jetty"] },
    unlocksStation: "net_loft",
    xp: { skill: "salvaging", amount: 40 },
  },
  smokehouse: {
    name: "The Smokehouse",
    ruin: "The old smokehouse",
    description: "Racks, a firebox and a roof that keeps the smoke in.",
    perk: "Smoke your catch: Smoked Silverfin heals more, and packs flat.",
    requires: { items: [{ item: "timber", qty: 10 }, { item: "scrap", qty: 4 }], projects: ["cottage_1"] },
    unlocksStation: "smokehouse",
    xp: { skill: "cooking", amount: 30 },
  },
};

/** Stations available before any project. */
export const DEFAULT_STATIONS: readonly StationId[] = ["hearth"];
