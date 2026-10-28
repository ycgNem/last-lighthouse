import { describe, expect, it } from "vitest";
import { TIDE } from "../src/data/tide";
import { cycleLength, readTide, tideEvents } from "../src/systems/tide";

describe("tide clock", () => {
  it("cycles low → rising → high → falling", () => {
    expect(readTide(0, TIDE).phase).toBe("low");
    expect(readTide(TIDE.low + 1, TIDE).phase).toBe("rising");
    expect(readTide(TIDE.low + TIDE.turn + 1, TIDE).phase).toBe("high");
    expect(readTide(TIDE.low + TIDE.turn + TIDE.high + 1, TIDE).phase).toBe("falling");
    expect(readTide(cycleLength(TIDE) + 1, TIDE).phase).toBe("low");
  });

  it("maps level to water height", () => {
    expect(readTide(0, TIDE).waterY).toBe(TIDE.lowLevel);
    expect(readTide(TIDE.low + TIDE.turn + 5, TIDE).waterY).toBe(TIDE.highLevel);
  });

  it("is continuous through a turn (no water jumps)", () => {
    let prev = readTide(0, TIDE).waterY;
    for (let t = 0; t < cycleLength(TIDE) * 2; t += 1 / 60) {
      const y = readTide(t, TIDE).waterY;
      expect(Math.abs(y - prev)).toBeLessThan(0.01);
      prev = y;
    }
  });

  it("warns once, `warning` seconds before each turn", () => {
    const warnings: number[] = [];
    let prev = readTide(0, TIDE);
    for (let t = 0; t < cycleLength(TIDE); t += 0.5) {
      const next = readTide(t, TIDE);
      for (const e of tideEvents(prev, next)) if (e.type === "warning") warnings.push(t);
      prev = next;
    }
    expect(warnings).toEqual([TIDE.low - TIDE.warning, TIDE.low + TIDE.turn + TIDE.high - TIDE.warning]);
  });

  it("a new game's first warning arrives early in the first trip", () => {
    const first = readTide(TIDE.newGameOffset, TIDE);
    expect(first.phase).toBe("low");
    expect(first.warning).toBe(false);
    const secondsToWarning = first.phaseTimeLeft - TIDE.warning;
    expect(secondsToWarning).toBeGreaterThanOrEqual(60);
    expect(secondsToWarning).toBeLessThanOrEqual(180);
  });
});
