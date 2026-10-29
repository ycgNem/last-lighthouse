import type { EnemyId, FlagId, Yield } from "./ids";

export type EnemyBehaviour = "lunger" | "spitter" | "blinker" | "ambusher" | "boss";

export interface AttackDef {
  id: string;
  /** Telegraph time. Readability rule: never under 0.4 s. */
  windup: number;
  recover: number;
  damage: number;
  /** Projectile attacks only. */
  projectile?: { count: number; spreadDeg: number; speed: number; radius: number };
  /** Melee / lunge reach in metres. */
  reach?: number;
}

export interface EnemyDef {
  name: string;
  behaviour: EnemyBehaviour;
  hp: number;
  moveSpeed: number;
  aggroRange: number;
  /** Preferred distance from the player. */
  keepDistance: number;
  attacks: AttackDef[];
  drops: Yield[];
  combatXp: number;
  model: string;
  grantsFlag?: FlagId;
  /** Seconds the Lantern Flare staggers it (cancels a windup). 0: immune. */
  flareStagger: number;
}

export const ENEMIES: Record<EnemyId, EnemyDef> = {
  brine_crab: {
    name: "Brine Crab",
    behaviour: "lunger",
    hp: 30,
    moveSpeed: 3.2,
    aggroRange: 16,
    keepDistance: 4,
    attacks: [{ id: "lunge", windup: 0.6, recover: 0.9, damage: 12, reach: 5 }],
    drops: [
      { item: "crab_meat", min: 1, max: 1 },
      { item: "tidestone", min: 1, max: 1 },
      { item: "scrap", min: 0, max: 1 },
    ],
    combatXp: 12,
    model: "enemies/brine_crab.glb",
    flareStagger: 1.4,
  },
  drowned_spitter: {
    name: "Drowned Spitter",
    behaviour: "spitter",
    hp: 45,
    moveSpeed: 1.2,
    aggroRange: 24,
    keepDistance: 12,
    attacks: [{ id: "fan", windup: 0.7, recover: 1.2, damage: 10, projectile: { count: 5, spreadDeg: 40, speed: 9, radius: 0.4 } }],
    drops: [
      { item: "tidestone", min: 1, max: 1 },
      { item: "kelp", min: 1, max: 2 },
    ],
    combatXp: 18,
    model: "enemies/drowned_spitter.glb",
    flareStagger: 1.6,
  },
  lantern_wisp: {
    name: "Lantern Wisp",
    behaviour: "blinker",
    hp: 25,
    moveSpeed: 4,
    aggroRange: 22,
    keepDistance: 10,
    attacks: [{ id: "aimed_pair", windup: 0.5, recover: 0.8, damage: 9, projectile: { count: 2, spreadDeg: 4, speed: 14, radius: 0.35 } }],
    drops: [
      { item: "tidestone", min: 1, max: 1 },
      { item: "sea_glass", min: 0, max: 1 },
    ],
    combatXp: 16,
    model: "enemies/lantern_wisp.glb",
    // Weak to light (GDD §7): long enough to shoot it down.
    flareStagger: 3.5,
  },
  tide_lurker: {
    name: "Tide Lurker",
    behaviour: "ambusher",
    hp: 60,
    moveSpeed: 5,
    aggroRange: 14,
    keepDistance: 0,
    attacks: [{ id: "surface_bite", windup: 0.8, recover: 1.5, damage: 18, reach: 2.5 }],
    drops: [
      { item: "tidestone", min: 2, max: 2 },
      { item: "glowgill", min: 0, max: 1 },
    ],
    combatXp: 26,
    model: "enemies/tide_lurker.glb",
    // Dives away from the light.
    flareStagger: 1.2,
  },
  wreck_guardian: {
    name: "Wreck Guardian",
    behaviour: "boss",
    hp: 900,
    moveSpeed: 0,
    aggroRange: 40,
    keepDistance: 0,
    attacks: [
      { id: "chain_sweep", windup: 1.0, recover: 2.0, damage: 22, reach: 16 },
      { id: "brine_mortar", windup: 1.2, recover: 1.0, damage: 16, projectile: { count: 5, spreadDeg: 360, speed: 10, radius: 0.6 } },
      { id: "undertow", windup: 1.0, recover: 1.5, damage: 8, projectile: { count: 7, spreadDeg: 70, speed: 9, radius: 0.45 } },
    ],
    drops: [
      { item: "tidestone", min: 10, max: 10 },
      { item: "brass", min: 6, max: 6 },
    ],
    combatXp: 300,
    model: "enemies/wreck_guardian.glb",
    // Far too vast.
    flareStagger: 0,
    grantsFlag: "guardian_defeated",
  },
};
