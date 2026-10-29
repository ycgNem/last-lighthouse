import type { GearId, LocationId } from "./ids";

/**
 * How long a typical player takes over things, for the pacing simulation
 * (src/systems/economy.ts). Seconds. Rough figures from the GDD's loop (§5),
 * the first-session script (§12) and walking each level; change them when a
 * playtest says otherwise, not to make a test pass.
 */
export const PACE = {
  /** Waking up and talking to Maren. */
  intro: 60,
  /** Getting down to the cove the first time and finding your feet with the hook. */
  firstCove: 45,
  /**
   * Share of what drifts in while you're home that a typical player ends up
   * with: some goes back out while you're up at the plots with the beach
   * full, some you never get round to.
   */
  coveShare: 0.85,
  /** At home before an expedition: bank the haul, cook, smith, check the chart (GDD §5: under 2 min). */
  prepare: 75,
  /** One way: the boat out from the jetty. */
  travel: 12,
  /** A location's overhead on top of the work: the walk in from the landing, looking about, the walk back. */
  explore: { home: 0, wreck: 120, beacon: 60 } satisfies Record<LocationId, number>,
  /** Extra the first time: finding your way round. */
  firstVisit: { home: 0, wreck: 120, beacon: 60 } satisfies Record<LocationId, number>,
  /** Each story beat: carrying the last of it up, the building rising, the banner, a word with whoever came home. */
  perBeat: 25,
  /** Walking from one node to the next (shared between a node's uses). */
  perNode: 6,
  /** One throw at a wreck: aim, the hook bites, the piece flies back. */
  perYank: 2,
  /** One fish: cast, wait for the bite, reel in. */
  perCatch: 8,
  /** Each enemy, on top of the shooting: closing in, dodging windups. */
  perFight: 7,
  /** Share of bolts that land. */
  accuracy: 0.6,
  /** The Guardian, start to finish, for a prepared player (GDD §11: 3–4 minutes). */
  boss: 210,
  /** Tools a typical player makes as soon as an expedition needs them. */
  tools: ["hook_iron"] satisfies GearId[],
  /** What a prepared player has made before facing the Guardian. */
  prepared: ["boltcaster_mk2"] satisfies GearId[],
  /** Home stints are simulated this long at a time, s. */
  stint: 30,
} as const;

/** What the pacing simulation has to show (GDD §5 and §12, MILESTONES M4). */
export const PACING = {
  /** Minutes from a new game to the first rebuild, the forge: the base pays back from the start. */
  firstBuildMinutes: [2.5, 6],
  /** Minutes from a new game to Stage 1 (M4: "a fresh save reaches Stage 1 in 15–25 min"). */
  stage1Minutes: [15, 25],
  /** Longest stretch at home without a story beat, minutes. */
  homeMinutesPerBeat: 7,
  /** Minutes away from home on an expedition. GDD §5 says 5–10; a quick top-up run can come in a little under. */
  tripMinutes: [4, 10],
  /** Most trips from one story beat to the next: "one small trip away from the next upgrade". */
  tripsPerBeat: 2,
} as const;
