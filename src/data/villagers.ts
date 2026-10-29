import type { NpcId } from "./ids";

// What the people of Lantern's Rest look like: free low-poly characters from
// Polyfork (https://polyfork.dev), loaded from Polyfork's CDN when home is
// dressed. Their licence lets a game hotlink and ship them, but not
// redistribute the files, so they are not in this (public) repo. Offline,
// home keeps its simple placeholder figures.

export const POLYFORK_CDN = "https://polyfork.dev/cdn/";

export interface VillagerLook {
  /** Polyfork asset id (https://polyfork.dev/asset/<id>). */
  asset: string;
  /** Held items to drop: they're authored for a walk and hang wrong at rest. */
  hide?: readonly ("lefthand" | "righthand")[];
  /** Facing at rest, radians (0 faces +Z). */
  yaw: number;
}

export const NPC_LOOKS: Record<NpcId, VillagerLook> = {
  // The old keeper: grey hair, a shawl against the wind, by the lighthouse door.
  maren: { asset: "crossing-keeper-e13207", hide: ["righthand"], yaw: -0.84 },
  // The cook at the hearth: headscarf, shawl and apron.
  odile: { asset: "townswoman-5aa87f", yaw: 2.46 },
  // Dockhand and boatwright: shirt sleeves and rolled trousers, barefoot on the boards.
  tib: { asset: "hanga-roa-fisherman-e56812", hide: ["righthand"], yaw: Math.PI - 0.05 },
  // The smith who came with the light, his sledgehammer on his shoulder.
  hesk: { asset: "platelayer-47dbe6", yaw: -2.09 },
};

/** The survivor family that arrives at stage 2: a mother with her case, two children. */
export const FAMILY_LOOKS: readonly VillagerLook[] = [
  { asset: "passenger-ac425a", yaw: -2.78 },
  { asset: "trainspotter-ffd141", yaw: -2.3 },
  { asset: "village-child-bef09e", yaw: 2.6 },
];
