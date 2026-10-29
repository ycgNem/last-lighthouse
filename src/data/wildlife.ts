import type { LocationId } from "./ids";

// Gulls (src/world/Gulls.ts): a flock wheeling over each place, and a few sat
// on perches (FX_perch_* markers in the location scripts; home sets its own in
// code) that take off when you come close and drift back once you've gone.
// They're there to make the coast feel lived in; they never get in your way.

type Range = readonly [number, number];

export const GULLS = {
  /** How many wheel overhead at each place. */
  flock: { home: 7, shore: 8, wreck: 6, beacon: 5 } as Record<LocationId, number>,
  /** Circle radius (m) round the flock's centre: the FX_gulls marker, else the middle of the gathering spots. */
  radius: [10, 30] as Range,
  /** How far a circle's centre strays from the flock's, m. */
  spread: 14,
  /** Height over the sea, m. Raised where a circle would clip the level. */
  height: [16, 30] as Range,
  /** Air speed, m/s. */
  speed: [6, 8.5] as Range,
  /** Wing beats per second while flapping. */
  beat: 2.6,
  /** Seconds gliding, then seconds flapping, in turn. */
  glide: [2, 5] as Range,
  flapBout: [0.8, 2.2] as Range,
  /** How near you can get to a sitting gull before it goes, m. */
  shy: 7,
  /** Taking off: speed off the perch and how fast it builds to cruising (m/s, m/s²), the first jump up (m) and the climb after (m/s). */
  takeoff: { speed: 2.5, accel: 3, cruise: 9, hop: 3.5, climb: 1.2 },
  /** Seconds out to sea before it's lost in the haze. It comes back down the same path, reversed. */
  gone: 16,
  /** A sitter leaves once the water is this close under its feet (m), and comes back only when it's twice as far down. */
  wetFeet: 0.2,
  /** Seconds it stays away; it comes back only once you're well clear of its perch. */
  away: [25, 55] as Range,
  /** A gull within earshot calls every so often, s. */
  callEvery: [5, 13] as Range,
  earshot: 45,
} as const;
