import type { BindingOverrides } from "../data/controls";
import type { FlagId, GearId, ItemId, ItemStack, LocationId, NpcId, ProjectId, SkillId, StageIndex } from "../data/ids";
import { STARTING_GEAR } from "../data/items";
import { TIDE } from "../data/tide";

export const SAVE_VERSION = 1;

export interface Settings {
  sensitivity: number;
  fov: number;
  volume: number;
  screenShake: boolean;
  headBob: boolean;
  /** Glow round lamps, the beam and anything burning brighter than white. */
  bloom: boolean;
  rain: boolean;
  /** One switch for everything that moves the view on its own: shake, bob, dash kick, sway, flashes. */
  reducedMotion: boolean;
  /** Dark rims round pale enemy orbs, so they don't rely on colour. */
  contrastShots: boolean;
  /** Text for important sounds: horns, windups, chimes, roars, with the direction. */
  captions: boolean;
  bindings: BindingOverrides;
}

/** The entire save. Everything runtime-only is rebuilt from this. */
export interface GameState {
  version: typeof SAVE_VERSION;
  playSeconds: number;
  tide: { elapsed: number };
  location: LocationId;
  stage: StageIndex;
  projects: ProjectId[];
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
      rain: true,
      reducedMotion: false,
      contrastShots: false,
      captions: false,
      bindings: {},
    },
  };
}
