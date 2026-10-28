import type { TideConfig } from "../data/tide";

export type TidePhase = "low" | "rising" | "high" | "falling";

export interface TideReading {
  phase: TidePhase;
  /** 0 = low water, 1 = high water. */
  level: number;
  waterY: number;
  /** Seconds until the next phase starts. */
  phaseTimeLeft: number;
  /** True during the warning window before rising/falling starts. */
  warning: boolean;
  /** Which way the next turn goes, for HUD copy ("Tide rising in 0:42"). */
  nextTurn: "rising" | "falling";
  /** Coarse state for gameplay rules: rising counts as low, falling as high. */
  state: "low" | "high";
}

export function cycleLength(cfg: TideConfig): number {
  return cfg.low + cfg.turn + cfg.high + cfg.turn;
}

function smooth(t: number): number {
  return t * t * (3 - 2 * t);
}

/** Pure function of elapsed time, so save/load and tests are deterministic. */
export function readTide(elapsed: number, cfg: TideConfig): TideReading {
  const len = cycleLength(cfg);
  const t = ((elapsed % len) + len) % len;
  const a = cfg.low;
  const b = a + cfg.turn;
  const c = b + cfg.high;

  let phase: TidePhase;
  let level: number;
  let phaseTimeLeft: number;
  if (t < a) {
    phase = "low";
    level = 0;
    phaseTimeLeft = a - t;
  } else if (t < b) {
    phase = "rising";
    level = smooth((t - a) / cfg.turn);
    phaseTimeLeft = b - t;
  } else if (t < c) {
    phase = "high";
    level = 1;
    phaseTimeLeft = c - t;
  } else {
    phase = "falling";
    level = 1 - smooth((t - c) / cfg.turn);
    phaseTimeLeft = len - t;
  }

  const stable = phase === "low" || phase === "high";
  return {
    phase,
    level,
    waterY: cfg.lowLevel + (cfg.highLevel - cfg.lowLevel) * level,
    phaseTimeLeft,
    warning: stable && phaseTimeLeft <= cfg.warning,
    nextTurn: phase === "low" || phase === "falling" ? "rising" : "falling",
    state: phase === "low" || phase === "rising" ? "low" : "high",
  };
}

export type TideEvent = { type: "warning"; turn: "rising" | "falling" } | { type: "turnStarted"; phase: TidePhase } | { type: "settled"; state: "low" | "high" };

/** Events that happened between two readings (call once per tick). */
export function tideEvents(prev: TideReading, next: TideReading): TideEvent[] {
  const out: TideEvent[] = [];
  if (!prev.warning && next.warning) out.push({ type: "warning", turn: next.nextTurn });
  if (prev.phase !== next.phase) {
    if (next.phase === "rising" || next.phase === "falling") out.push({ type: "turnStarted", phase: next.phase });
    else out.push({ type: "settled", state: next.phase });
  }
  return out;
}
