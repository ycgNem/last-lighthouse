import type { FlotsamId, Yield } from "./ids";

// The Rest's cove: what the sea brings in, and how the salvage hook pulls it
// out. Read by src/gather (the hook, the drift, the wrecks) and by the pacing
// simulation (src/systems/economy.ts), which holds these numbers to the GDD's
// pacing. Turning tides count as the water they're heading for.

export type Water = "low" | "rising" | "high" | "falling";

export interface FlotsamDef {
  name: string;
  /** What hooking it gives. */
  yields: Yield[];
  /** It reels in at the hook's speed divided by this: a log is a hard pull. */
  weight: number;
  /** How often this one drifts in, against the others, at low and at high water. */
  odds: { low: number; high: number };
  /** Model in props.glb. */
  model: string;
  /** How deep it floats: it grounds where the water is shallower than this. */
  draft: number;
  xp: number;
}

export const FLOTSAM: Record<FlotsamId, FlotsamDef> = {
  planks: { name: "Plank Bundle", yields: [{ item: "timber", min: 2, max: 3 }], weight: 1, odds: { low: 6, high: 7 }, model: "flot_planks", draft: 0.2, xp: 5 },
  drum: { name: "Oil Drum", yields: [{ item: "scrap", min: 2, max: 3 }], weight: 1.3, odds: { low: 4, high: 5 }, model: "flot_drum", draft: 0.45, xp: 6 },
  kelp_mat: { name: "Kelp Mat", yields: [{ item: "kelp", min: 2, max: 3 }], weight: 0.8, odds: { low: 4, high: 3 }, model: "flot_kelp", draft: 0.1, xp: 4 },
  bottles: { name: "Netted Bottles", yields: [{ item: "sea_glass", min: 1, max: 2 }], weight: 0.7, odds: { low: 3, high: 3 }, model: "flot_bottles", draft: 0.2, xp: 6 },
  barrel: { name: "Barrel", yields: [{ item: "timber", min: 1, max: 1 }, { item: "scrap", min: 1, max: 1 }, { item: "sea_glass", min: 0, max: 1 }], weight: 1.2, odds: { low: 2, high: 3 }, model: "flot_barrel", draft: 0.5, xp: 6 },
  log: { name: "Driftwood Log", yields: [{ item: "timber", min: 4, max: 5 }], weight: 2.5, odds: { low: 1, high: 2 }, model: "flot_log", draft: 0.6, xp: 8 },
  ship_crate: { name: "Ship's Crate", yields: [{ item: "brass", min: 1, max: 2 }, { item: "sea_glass", min: 1, max: 1 }, { item: "tidestone", min: 0, max: 1 }], weight: 1.6, odds: { low: 0, high: 1 }, model: "flot_crate", draft: 0.45, xp: 12 },
};

export const SALVAGE = {
  /** Seconds between pieces drifting in through the cove mouth. The flood brings the most. */
  driftEvery: { low: 16, rising: 9, high: 11, falling: 13 } satisfies Record<Water, number>,
  /** Most afloat in the cove at once; the sea holds the rest back. */
  maxAfloat: 6,
  /** Already afloat when you come home. */
  afloatOnArrival: 3,
  /** Metres a second along the drift lanes, slowest to fastest. */
  driftSpeed: [0.5, 0.8],
  /** Wander across the lane: metres either side, and seconds for one sway. */
  sway: { metres: 1.4, seconds: 11 },
  /** Riding the swell. */
  bob: { metres: 0.07, rate: 1.3, rollDeg: 6 },
  /** Most lying on the beach; past this, the next one in drifts back out. */
  beachMax: 10,
  /** Of what drifts in while you're away, the share you find washed up. */
  awayBeachShare: 0.4,
  /** The cove net (Net Loft): the share of the drift it holds while you're away, and the most it holds. */
  net: { share: 0.35, max: 8 },
  /** Drift rarer than this share doesn't count as a source: the guide won't send you to wait for it, and the validator won't count on it. */
  reliableShare: 0.05,
} as const;

export const HOOK = {
  /** The throw: metres a second off the hand, and the drop. */
  throwSpeed: 30,
  gravity: 16,
  /** Seconds between throws. */
  cooldown: 0.35,
  /** A target this far off the aim line, at its distance, still gets hooked. */
  assist: 1.4,
  /** Seconds a piece torn off a wreck takes to fly to you. */
  yankFlight: 0.45,
  /** A reeled piece lands in the satchel this close. */
  catchAt: 1.8,
  /** Salvaging level perks (SKILLS.salvaging's milestones say the same in words). */
  perks: {
    reel: [
      { level: 2, bonus: 0.15 },
      { level: 9, bonus: 0.35 },
    ],
    range: { level: 4, metres: 3 },
    /** Now and then a wreck gives up two pieces to one pull. */
    double: { level: 6, chance: 0.2 },
  },
} as const;
