export interface TideConfig {
  /** Seconds at low water. */
  low: number;
  /** Seconds the water takes to rise or fall. */
  turn: number;
  /** Seconds at high water. */
  high: number;
  /** Warning lead time before each turn starts. */
  warning: number;
  /** Water Y in metres. */
  lowLevel: number;
  highLevel: number;
  /** Where a new save starts in the cycle, so the first trip sees a turn. */
  newGameOffset: number;
}

export const TIDE: TideConfig = {
  low: 240,
  turn: 30,
  high: 240,
  warning: 60,
  lowLevel: 0,
  highLevel: 1.8,
  // 1:00 into low tide: the first warning comes after two minutes of play,
  // about one minute into the first trip to the shore (GDD §12).
  newGameOffset: 60,
};

/** Depth thresholds (water surface minus feet height), metres. */
export const WATER_DEPTH = {
  wade: 0.5,
  swim: 1.1,
  /** Seconds swimming before the current carries you to an anchor. */
  rescueAfter: 6,
} as const;
