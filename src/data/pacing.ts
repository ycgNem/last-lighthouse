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
  /** At home between trips: bank the haul, cook, smith, check the chart (GDD §5: under 2 min). */
  prepare: 75,
  /** One way: the cliff path down to the shore, or the boat out. */
  travel: 12,
  /** A location's overhead on top of the work: the walk in from the landing, looking about, the walk back. */
  explore: { home: 0, shore: 70, wreck: 120, beacon: 60 } satisfies Record<LocationId, number>,
  /** Extra the first time: finding your way round (GDD §12 has the first shore run at 6 minutes). */
  firstVisit: { home: 0, shore: 90, wreck: 120, beacon: 60 } satisfies Record<LocationId, number>,
  /** Each story beat: the upgrade banner, the world changing, a word with whoever's there. */
  perBeat: 20,
  /** Walking from one node to the next (shared between a node's uses). */
  perNode: 6,
  /** One fish: cast, wait for the bite, reel in. */
  perCatch: 8,
  /** Each enemy, on top of the shooting: closing in, dodging windups. */
  perFight: 7,
  /** Share of bolts that land. */
  accuracy: 0.6,
  /** The Guardian, start to finish, for a prepared player (GDD §11: 3–4 minutes). */
  boss: 210,
  /** What a prepared player has made before facing the Guardian. */
  prepared: ["boltcaster_mk2"] satisfies GearId[],
} as const;

/** What the pacing simulation has to show (GDD §5 and §12, MILESTONES M4). */
export const PACING = {
  /** Minutes from a new game to Stage 1 (M4: "a fresh save reaches Stage 1 in 15–25 min"). */
  stage1Minutes: [15, 25],
  /** Shore runs up to Stage 1 (GDD §12: "Restore the Lamp reachable on run 2–3"). */
  stage1ShoreRuns: [2, 3],
  /** Minutes away from home on an expedition. GDD §5 says 5–10; a quick top-up run can come in a little under. */
  tripMinutes: [4, 10],
  /** Most trips from one story beat to the next: "one small trip away from the next upgrade". */
  tripsPerBeat: 2,
} as const;
