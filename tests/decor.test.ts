import { describe, expect, it } from "vitest";
import { DECOR, DECOR_RULES } from "../src/data/decor";
import { createNewGame } from "../src/state/GameState";
import { decorAt, footprint, pickUpDecor, placeBlock, placeDecor, type PlaceWorld } from "../src/systems/decor";
import { available } from "../src/systems/inventory";

// A flat village 40 m square at 5 m up, a slope to the east, the sea to the
// south, and a plot kept clear in the middle.
const world: PlaceWorld = {
  inBounds: (x, z) => Math.abs(x) <= 20 && Math.abs(z) <= 20,
  groundY: (x, z) => (z > 15 ? 1 : x > 12 ? 5 + (x - 12) * 1.5 : 5),
  keepClear: [{ x: 0, z: 0, r: 3 }],
  highWater: 1.8,
};

function rich() {
  const s = createNewGame();
  for (const item of ["timber", "scrap", "kelp", "sea_glass"] as const) s.storage[item] = 200;
  return s;
}

describe("decorating the Rest", () => {
  it("turns a footprint the way three.js turns the model", () => {
    const [w, d] = DECOR.fence.size;
    const flat = footprint("fence", 0, 0, 0);
    expect(Math.max(...flat.map((p) => p[0]))).toBeCloseTo(w / 2);
    const turned = footprint("fence", 0, 0, Math.PI / 2);
    // A quarter turn swings the long side onto z.
    expect(Math.max(...turned.map((p) => p[1]))).toBeCloseTo(w / 2);
    expect(Math.max(...turned.map((p) => p[0]))).toBeCloseTo(d / 2);
  });

  it("goes down on open, level ground above the tide, and costs what it says", () => {
    const s = rich();
    const timber = available(s, "timber");
    expect(placeDecor(s, world, "bench", 8, -8, 0.3)).toBeNull();
    expect(s.decor).toHaveLength(1);
    expect(available(s, "timber")).toBe(timber - 3);
  });

  it("refuses the edge of the village, slopes, the shore, plots and other pieces", () => {
    const s = rich();
    expect(placeBlock(s, world, "bench", 19.8, 0, 0)).toBe("bounds");
    expect(placeBlock(s, world, "bench", 16, 0, 0)).toBe("slope");
    expect(placeBlock(s, world, "bench", 0, 17, 0)).toBe("water");
    expect(placeBlock(s, world, "bench", 2, 2, 0)).toBe("blocked");
    expect(placeDecor(s, world, "crates", 8, 8, 0)).toBeNull();
    expect(placeBlock(s, world, "barrels", 8.5, 8.5, 0)).toBe("overlap");
    expect(placeBlock(s, world, "barrels", 11, 8, 0)).toBeNull();
  });

  it("refuses when you can't pay, or the Rest is full", () => {
    const s = createNewGame();
    expect(placeBlock(s, world, "lantern", 8, 8, 0)).toBe("cost");
    const full = rich();
    full.decor = Array.from({ length: DECOR_RULES.max }, (_, i) => ({ kind: "fence" as const, x: -15 + (i % 10) * 3, z: -15 + Math.floor(i / 10) * 1, yaw: 0 }));
    expect(placeBlock(full, world, "lantern", 8, 8, 0)).toBe("limit");
  });

  it("picks back up for everything it cost", () => {
    const s = rich();
    const before = { timber: available(s, "timber"), scrap: available(s, "scrap"), glass: available(s, "sea_glass") };
    expect(placeDecor(s, world, "lantern", -8, 8, 0)).toBeNull();
    const i = decorAt(s, -8.1, 8.1);
    expect(i).toBe(0);
    expect(pickUpDecor(s, i)).toEqual(DECOR.lantern.cost);
    expect(s.decor).toHaveLength(0);
    expect({ timber: available(s, "timber"), scrap: available(s, "scrap"), glass: available(s, "sea_glass") }).toEqual(before);
    expect(decorAt(s, -8, 8)).toBe(-1);
  });
});
