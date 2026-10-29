import { describe, expect, it } from "vitest";
import { FLOTSAM_IDS, type FlotsamId } from "../src/data/ids";
import { FLOTSAM, SALVAGE } from "../src/data/salvage";
import { TIDE } from "../src/data/tide";
import { createNewGame } from "../src/state/GameState";
import { awayCatch, driftBetween, flotsamFor, hookStats, rollYields, tearWreck, wreckLeft } from "../src/systems/salvage";
import { cycleLength } from "../src/systems/tide";

/** A repeatable stand-in for Math.random. */
function rng(seed = 7): () => number {
  let a = seed;
  return () => {
    a = (a * 1664525 + 1013904223) >>> 0;
    return a / 2 ** 32;
  };
}

describe("the cove's drift", () => {
  it("brings in every kind at its odds, and no ship's crates at low water", () => {
    const count = (water: "low" | "high") => {
      const seen = new Map<FlotsamId, number>();
      for (let i = 0; i < 1000; i++) {
        const f = flotsamFor(water, (i + 0.5) / 1000);
        seen.set(f, (seen.get(f) ?? 0) + 1);
      }
      return seen;
    };
    const high = count("high");
    const low = count("low");
    for (const id of FLOTSAM_IDS) expect(high.get(id) ?? 0, id).toBeGreaterThan(0);
    expect(low.get("ship_crate") ?? 0).toBe(0);
    expect(high.get("planks")!).toBeGreaterThan(high.get("log")!);
    // The top of the roll never lands on a kind that can't drift in.
    expect(flotsamFor("low", 1 - 1e-9)).not.toBe("ship_crate");
  });

  it("rolls each piece within its yields, never empty", () => {
    const r = rng();
    for (const id of FLOTSAM_IDS) {
      for (let i = 0; i < 50; i++) {
        const got = rollYields(FLOTSAM[id].yields, r);
        expect(got.length, id).toBeGreaterThan(0);
        for (const g of got) {
          const y = FLOTSAM[id].yields.find((x) => x.item === g.item)!;
          expect(g.qty).toBeGreaterThanOrEqual(Math.max(1, y.min));
          expect(g.qty).toBeLessThanOrEqual(y.max);
        }
      }
    }
  });

  it("brings in the most on the flood and at high water", () => {
    const len = cycleLength(TIDE);
    const low = driftBetween(0, TIDE.low);
    const high = driftBetween(TIDE.low + TIDE.turn, TIDE.low + TIDE.turn + TIDE.high);
    expect(high).toBeGreaterThan(low);
    expect(driftBetween(0, len)).toBeCloseTo(TIDE.low / SALVAGE.driftEvery.low + TIDE.turn / SALVAGE.driftEvery.rising + TIDE.high / SALVAGE.driftEvery.high + TIDE.turn / SALVAGE.driftEvery.falling);
  });
});

describe("the hook", () => {
  it("reaches further and reels faster with each tier and with salvaging", () => {
    const s = createNewGame();
    const rope = hookStats(s);
    expect(rope.gear).toBe("hook_rope");
    s.gear.push("hook_iron");
    const iron = hookStats(s);
    expect(iron.gear).toBe("hook_iron");
    expect(iron.range).toBeGreaterThan(rope.range);
    expect(iron.reel).toBeGreaterThan(rope.reel);
    s.skillXp.salvaging = 10_000;
    const master = hookStats(s);
    expect(master.range).toBeGreaterThan(iron.range);
    expect(master.reel).toBeGreaterThan(iron.reel);
    expect(master.double).toBeGreaterThan(0);
  });
});

describe("coming home", () => {
  it("finds the beach stocked, to its cap, and the net too once the Net Loft stands", () => {
    const s = createNewGame();
    const long = awayCatch(s, 0, 3600, rng());
    expect(long.beach.length).toBe(SALVAGE.beachMax);
    expect(long.net).toEqual([]);
    s.projects.push("net_loft");
    const netted = awayCatch(s, 0, 3600, rng());
    expect(netted.net.length).toBe(SALVAGE.net.max);
    expect(netted.beach.length).toBe(SALVAGE.beachMax);
    expect(awayCatch(s, 0, 5, rng())).toEqual({ beach: [], net: [] });
    // What's already lying there counts toward the cap.
    s.cove.beach = Array(SALVAGE.beachMax - 2).fill("planks");
    expect(awayCatch(s, 0, 3600, rng()).beach.length).toBe(2);
  });

  it("strips a wreck for the rest of the low tide, and restocks it for the next", () => {
    const s = createNewGame();
    const len = cycleLength(TIDE);
    expect(wreckLeft(s, "boat", 6, 10)).toBe(6);
    expect(tearWreck(s, "boat", 6, 10, 2)).toBe(4);
    expect(tearWreck(s, "boat", 6, 100, 5)).toBe(0);
    expect(wreckLeft(s, "boat", 6, 200)).toBe(0);
    expect(wreckLeft(s, "pilings", 3, 200)).toBe(3);
    // Still the same tide's cycle at high water; the next low brings it back.
    expect(wreckLeft(s, "boat", 6, len - 1)).toBe(0);
    expect(wreckLeft(s, "boat", 6, len + 1)).toBe(6);
  });
});
