import type { DecorId, ItemStack } from "./ids";

// What you can place round the Rest in build mode (B). Costs come out of the
// satchel and the chest; picking a piece back up refunds all of it.

export interface DecorDef {
  name: string;
  cost: ItemStack[];
  /** Footprint in metres, across (x) and deep (z) before turning: kept clear of everything else. */
  size: [number, number];
  /** Collider height, when it's solid. */
  height: number;
  solid: boolean;
  /** The light it gives off: colour, strength, reach in metres, and height above the ground. */
  light?: { color: number; intensity: number; distance: number; y: number };
  /** Model in props.glb. */
  model: string;
}

export const DECOR: Record<DecorId, DecorDef> = {
  lantern: { name: "Lantern Post", cost: [{ item: "timber", qty: 2 }, { item: "scrap", qty: 1 }, { item: "sea_glass", qty: 1 }], size: [0.5, 0.5], height: 2.4, solid: true, light: { color: 0xffc27a, intensity: 5, distance: 9, y: 2.15 }, model: "lantern_post" },
  brazier: { name: "Brazier", cost: [{ item: "scrap", qty: 3 }, { item: "timber", qty: 1 }], size: [0.8, 0.8], height: 1, solid: true, light: { color: 0xff9a4a, intensity: 6, distance: 8, y: 1.1 }, model: "decor_brazier" },
  fence: { name: "Fence", cost: [{ item: "timber", qty: 2 }], size: [2.4, 0.3], height: 1.1, solid: true, model: "decor_fence" },
  bench: { name: "Bench", cost: [{ item: "timber", qty: 3 }], size: [1.8, 0.6], height: 0.95, solid: true, model: "decor_bench" },
  planter: { name: "Herb Planter", cost: [{ item: "timber", qty: 2 }, { item: "kelp", qty: 2 }], size: [1.2, 0.6], height: 0.6, solid: true, model: "decor_planter" },
  barrels: { name: "Barrels", cost: [{ item: "timber", qty: 2 }, { item: "scrap", qty: 1 }], size: [1.4, 1], height: 1.3, solid: true, model: "decor_barrels" },
  crates: { name: "Crates", cost: [{ item: "timber", qty: 3 }], size: [1.4, 1.1], height: 1.2, solid: true, model: "decor_crates" },
  bunting: { name: "Bunting Pole", cost: [{ item: "timber", qty: 1 }, { item: "kelp", qty: 2 }], size: [1.2, 0.5], height: 3.3, solid: true, model: "decor_bunting" },
  net_rack: { name: "Net Rack", cost: [{ item: "timber", qty: 2 }, { item: "kelp", qty: 3 }], size: [2.4, 0.7], height: 1.8, solid: true, model: "decor_net_rack" },
};

export const DECOR_RULES = {
  /** How far in front of you the piece goes. */
  reach: 9,
  /** Steepest ground a piece stands on: rise over run across its footprint. */
  maxSlope: 0.3,
  /** Its lowest corner must stand this far above high water. */
  aboveHighWater: 0.25,
  /** Kept between a piece and the next. */
  gap: 0.1,
  /** Most pieces placed: each solid one is a box in the collider. */
  max: 80,
  /** Lit pieces nearest you that cast real light; the rest just glow. */
  maxLights: 4,
  /** Radians per press of R. */
  turnStep: Math.PI / 8,
} as const;
