import type { EnemyId, LocationId, NodeId, ProjectId, StageIndex, TideReq } from "./ids";

export interface NodeSpawn {
  node: NodeId;
  count: number;
  /** Only there once this plot is rebuilt (a fishing spot off the jetty's end). */
  needsProject?: ProjectId;
}

export interface EnemySpawn {
  enemy: EnemyId;
  count: number;
  tide: TideReq;
}

export interface LocationDef {
  name: string;
  blurb: string;
  /** Lighthouse stage that reveals it on the chart. */
  revealedAtStage: StageIndex;
  safe: boolean;
  model: string;
  /**
   * Node and enemy counts. In M2+ the actual positions come from NODE_/ENEMY_
   * markers in the .glb; these counts are the design target and what the
   * validator uses for reachability.
   */
  nodes: NodeSpawn[];
  enemies: EnemySpawn[];
  /** Fog start / end in metres. Fog never starts closer than combat range. */
  fog: [number, number];
  /** 0..1 how hard it rains here at the peak of a shower. */
  rain: number;
  /** GLOOM_ pockets in the .glb (the level test checks the count). */
  gloom: number;
}

export const LOCATIONS: Record<LocationId, LocationDef> = {
  home: {
    name: "Lantern's Rest",
    blurb: "Home. The light keeps the Gloom away, and the tide brings the drowned world into the cove.",
    revealedAtStage: 0,
    safe: true,
    model: "locations/home.glb",
    // The cove's fishing and its wreck field; what drifts in is in data/salvage.ts.
    nodes: [
      { node: "fish_silverfin", count: 1 },
      { node: "fish_glowgill", count: 1, needsProject: "jetty" },
      { node: "sunken_boat", count: 1 },
      { node: "old_pilings", count: 2 },
      { node: "boiler", count: 1 },
    ],
    enemies: [],
    fog: [60, 220],
    rain: 0.35,
    gloom: 0,
  },
  wreck: {
    name: "Wreck of the Meridian",
    blurb: "A steamship driven onto a reef. Low tide bares the way into her hull; high tide floats her cargo up to the rail.",
    revealedAtStage: 1,
    safe: false,
    model: "locations/wreck.glb",
    nodes: [
      { node: "driftwood", count: 4 },
      { node: "scrap_pile", count: 4 },
      { node: "reinforced_wreckage", count: 4 },
      { node: "kelp_bed", count: 2 },
      { node: "strongbox", count: 1 },
      { node: "fish_glowgill", count: 1 },
      { node: "lens_pedestal", count: 1 },
    ],
    enemies: [
      { enemy: "brine_crab", count: 4, tide: "low" },
      { enemy: "drowned_spitter", count: 3, tide: "any" },
      { enemy: "lantern_wisp", count: 3, tide: "any" },
      { enemy: "tide_lurker", count: 2, tide: "high" },
    ],
    fog: [40, 140],
    rain: 0.75,
    gloom: 2,
  },
  beacon: {
    name: "Saltmere Beacon",
    blurb: "The first of the outlying lights, on a sea stack above an old landing stage. Something vast sleeps in the water below it.",
    revealedAtStage: 2,
    safe: false,
    model: "locations/beacon.glb",
    nodes: [],
    enemies: [
      { enemy: "drowned_spitter", count: 2, tide: "any" },
      { enemy: "lantern_wisp", count: 2, tide: "any" },
      { enemy: "wreck_guardian", count: 1, tide: "any" },
    ],
    fog: [40, 150],
    rain: 0.9,
    gloom: 2,
  },
};
