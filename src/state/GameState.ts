import type { BindingOverrides } from "../data/controls";
import type { DecorId, FlagId, FlotsamId, GearId, ItemId, ItemStack, LocationId, NpcId, ProjectId, SkillId, StageIndex } from "../data/ids";
import { STARTING_GEAR } from "../data/items";
import { TIDE } from "../data/tide";

export const SAVE_VERSION = 2;

export interface Settings {
  sensitivity: number;
  fov: number;
  volume: number;
  screenShake: boolean;
  headBob: boolean;
  /** Glow round lamps, the beam and anything burning brighter than white. */
  bloom: boolean;
  /** Share of the screen's pixels drawn, 0.5..1; 0 = automatic (drops when frames run slow). */
  renderScale: number;
  rain: boolean;
  /** One switch for everything that moves the view on its own: shake, bob, dash kick, sway, flashes. */
  reducedMotion: boolean;
  /** Dark rims round pale enemy orbs, so they don't rely on colour. */
  contrastShots: boolean;
  /** Text for important sounds: horns, windups, chimes, roars, with the direction. */
  captions: boolean;
  bindings: BindingOverrides;
}

/** A piece of decor placed round the Rest. */
export interface PlacedDecor {
  kind: DecorId;
  x: number;
  z: number;
  yaw: number;
}

/** The entire save. Everything runtime-only is rebuilt from this. */
export interface GameState {
  version: typeof SAVE_VERSION;
  playSeconds: number;
  tide: { elapsed: number };
  location: LocationId;
  stage: StageIndex;
  /** Rebuilt plots. */
  projects: ProjectId[];
  /** Materials handed in to plots still going up. */
  build: Partial<Record<ProjectId, Partial<Record<ItemId, number>>>>;
  decor: PlacedDecor[];
  /** Pieces ever hooked out of the sea. */
  salvaged: number;
  cove: {
    /** Washed up on the beach, waiting to be picked up. */
    beach: FlotsamId[];
    /** Caught in the cove net (Net Loft) while you were away. */
    net: FlotsamId[];
    /** The low tide the wreck field was last stocked for (count since the new game), and the pieces left on each wreck. */
    wrecks: { tide: number; left: Record<string, number> };
  };
  /** Tide clock when you last set out from the Rest, for what drifts in while you're away. Null at home. */
  leftHomeAt: number | null;
  flags: FlagId[];
  skillXp: Record<SkillId, number>;
  gear: GearId[];
  /** Fixed-length slot array; null = empty slot. */
  satchel: (ItemStack | null)[];
  keyItems: ItemId[];
  storage: Partial<Record<ItemId, number>>;
  quest: { step: number; crafted: Record<string, number>; talked: NpcId[] };
  trackedItem: ItemId | null;
  foodSlot: ItemId | null;
  settings: Settings;
}

export function createNewGame(): GameState {
  return {
    version: SAVE_VERSION,
    playSeconds: 0,
    tide: { elapsed: TIDE.newGameOffset },
    location: "home",
    stage: 0,
    projects: [],
    build: {},
    decor: [],
    salvaged: 0,
    cove: { beach: [], net: [], wrecks: { tide: -1, left: {} } },
    leftHomeAt: null,
    flags: [],
    skillXp: { fishing: 0, salvaging: 0, cooking: 0, smithing: 0, combat: 0 },
    gear: [...STARTING_GEAR],
    satchel: [],
    keyItems: [],
    storage: {},
    quest: { step: 0, crafted: {}, talked: [] },
    trackedItem: null,
    foodSlot: null,
    settings: {
      sensitivity: 1,
      fov: 75,
      volume: 0.8,
      screenShake: true,
      headBob: true,
      bloom: true,
      renderScale: 0,
      rain: true,
      reducedMotion: false,
      contrastShots: false,
      captions: false,
      bindings: {},
    },
  };
}
