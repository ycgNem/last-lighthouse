import type { FlagId, ItemId, ItemStack, LocationId, NpcId, ProjectId, SkillId, StageIndex, StationId } from "./ids";

export interface Requirements {
  items?: ItemStack[];
  keyItems?: ItemId[];
  projects?: ProjectId[];
  flags?: FlagId[];
}

/** What a stage looks like in the world. Read by the home location each frame. */
export interface StageVisuals {
  beamColor: number;
  beamLength: number;
  beamIntensity: number;
  /** 0 = steady, 1 = badly flickering. */
  flicker: number;
  fogFar: number;
  windowsLit: number;
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
    description: "The lamp gutters. Only the nearby shore is safe to reach.",
    requires: {},
    performedAt: "home",
    reveals: ["shore"],
    grantsKeyItems: [],
    consumesKeyItems: [],
    npcArrivals: [],
    visuals: { beamColor: 0xffb347, beamLength: 40, beamIntensity: 0.35, flicker: 0.8, fogFar: 160, windowsLit: 0, boats: 1 },
  },
  {
    index: 1,
    name: "Restored Lamp",
    description: "Repair the lamp housing. A steady beam reaches the Meridian.",
    requires: { items: [{ item: "scrap", qty: 10 }, { item: "sea_glass", qty: 6 }, { item: "timber", qty: 6 }], projects: ["forge", "dock"] },
    performedAt: "home",
    reveals: ["wreck"],
    grantsKeyItems: [],
    consumesKeyItems: [],
    npcArrivals: ["hesk"],
    xp: { skill: "smithing", amount: 60 },
    visuals: { beamColor: 0xfff1c9, beamLength: 90, beamIntensity: 0.7, flicker: 0.05, fogFar: 230, windowsLit: 3, boats: 1 },
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
    visuals: { beamColor: 0xe9fff4, beamLength: 160, beamIntensity: 1.0, flicker: 0, fogFar: 320, windowsLit: 7, boats: 2 },
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
    visuals: { beamColor: 0xe9fff4, beamLength: 170, beamIntensity: 1.0, flicker: 0, fogFar: 380, windowsLit: 10, boats: 2 },
  },
];

export interface ProjectDef {
  name: string;
  description: string;
  requires: Requirements;
  unlocksStation?: StationId;
  /** The dock gates offshore travel; the shore is reachable by walking the cliff path. */
  unlocksOffshore?: boolean;
  xp?: { skill: SkillId; amount: number };
}

export const PROJECTS: Record<ProjectId, ProjectDef> = {
  forge: {
    name: "Rekindle the Forge",
    description: "Patch the bellows and chimney so metal can be worked again.",
    requires: { items: [{ item: "scrap", qty: 8 }, { item: "timber", qty: 6 }] },
    unlocksStation: "forge",
    xp: { skill: "smithing", amount: 25 },
  },
  dock: {
    name: "Mend the Dock",
    description: "New planks and kelp rope. The boat can reach open water.",
    requires: { items: [{ item: "timber", qty: 12 }, { item: "kelp", qty: 4 }] },
    unlocksOffshore: true,
    xp: { skill: "salvaging", amount: 30 },
  },
};

/** Stations available before any project. */
export const DEFAULT_STATIONS: readonly StationId[] = ["hearth"];
