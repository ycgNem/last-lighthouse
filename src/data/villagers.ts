import type { NpcId } from "./ids";

// What the people of Lantern's Rest look like: free low-poly characters from
// Polyfork (https://polyfork.dev), loaded from Polyfork's CDN when home is
// dressed. Their licence lets a game hotlink and ship them, but not
// redistribute the files, so they are not in this (public) repo. Offline,
// home keeps its simple placeholder figures. Where each stands, and which way
// they face, comes from the map (NPC_ and PLACE_family_ markers in locations/home.glb).

export const POLYFORK_CDN = "https://polyfork.dev/cdn/";

export interface VillagerLook {
  /** Polyfork asset id (https://polyfork.dev/asset/<id>). */
  asset: string;
  /** Held items to drop: they're authored for a walk and hang wrong at rest. */
  hide?: readonly ("lefthand" | "righthand")[];
}

export const NPC_LOOKS: Record<NpcId, VillagerLook> = {
  // The old keeper: grey hair, a shawl against the wind, by the lighthouse door.
  maren: { asset: "crossing-keeper-e13207", hide: ["righthand"] },
  // The cook at the hearth: headscarf, shawl and apron.
  odile: { asset: "townswoman-5aa87f" },
  // Dockhand and boatwright: shirt sleeves and rolled trousers, barefoot on the boards.
  tib: { asset: "hanga-roa-fisherman-e56812", hide: ["righthand"] },
  // The smith who came with the light, his sledgehammer on his shoulder.
  hesk: { asset: "platelayer-47dbe6" },
};

/**
 * The families who come home to the cottages (PROJECTS[].family), each at its
 * door. The Pells: Wenna with her case and her two. The Ashbys: old Ashby in
 * his fishing waders, Gran in her shawl, and their granddaughter.
 */
export const FAMILIES: readonly (readonly VillagerLook[])[] = [
  [{ asset: "passenger-ac425a" }, { asset: "trainspotter-ffd141" }, { asset: "village-child-bef09e" }],
  [{ asset: "fisherman-in-waders-6dc25e", hide: ["righthand"] }, { asset: "grandmother-in-a-rebozo-4d5190" }, { asset: "kite-kid-0a7d70", hide: ["righthand"] }],
];
