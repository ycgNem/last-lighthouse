import { describe, expect, it } from "vitest";
import { PROJECTS } from "../src/data/lighthouse";
import { createNewGame } from "../src/state/GameState";
import { buildProgress, completeProject, deliver, plotOpen, remaining } from "../src/systems/building";
import { addItem, carried, stored } from "../src/systems/inventory";
import { isHome } from "../src/systems/progression";

describe("rebuilding the Rest", () => {
  it("takes materials a few at a time, satchel first, then the chest", () => {
    const s = createNewGame();
    addItem(s, "scrap", 3);
    s.storage.scrap = 2;
    const first = deliver(s, "forge");
    expect(first.given).toEqual([{ item: "scrap", qty: 5 }]);
    expect(first.finished).toBe(false);
    expect(carried(s, "scrap")).toBe(0);
    expect(stored(s, "scrap")).toBe(0);
    expect(remaining(s, "forge")).toEqual([
      { item: "scrap", qty: 3 },
      { item: "timber", qty: 6 },
    ]);
    expect(buildProgress(s, "forge")).toBeCloseTo(5 / 14);
  });

  it("never takes more than the plot still needs, and stands once the last is in", () => {
    const s = createNewGame();
    addItem(s, "scrap", 20);
    addItem(s, "timber", 20);
    const done = deliver(s, "forge");
    expect(done.finished).toBe(true);
    expect(done.xp?.skill).toBe("smithing");
    expect(carried(s, "scrap")).toBe(12);
    expect(carried(s, "timber")).toBe(14);
    expect(s.projects).toContain("forge");
    expect(s.build.forge).toBeUndefined();
    expect(buildProgress(s, "forge")).toBe(1);
    expect(deliver(s, "forge").given).toEqual([]);
  });

  it("keeps a plot closed until what it builds on stands", () => {
    const s = createNewGame();
    expect(plotOpen(s, "net_loft")).toBe(false); // after the jetty
    expect(plotOpen(s, "cottage_2")).toBe(false); // once the lamp is restored
    addItem(s, "timber", 20);
    expect(deliver(s, "net_loft").given).toEqual([]);
    s.projects.push("jetty");
    expect(plotOpen(s, "net_loft")).toBe(true);
    s.stage = 1;
    expect(plotOpen(s, "cottage_2")).toBe(true);
  });

  it("completes all at once or not at all (the dev console)", () => {
    const s = createNewGame();
    addItem(s, "timber", PROJECTS.jetty.requires.items![0]!.qty);
    expect(completeProject(s, "jetty")).toBe(false);
    expect(s.build.jetty).toBeUndefined();
    addItem(s, "kelp", 6);
    expect(completeProject(s, "jetty")).toBe(true);
  });

  it("brings people home as their plots stand", () => {
    const s = createNewGame();
    expect(isHome(s, "maren")).toBe(true);
    expect(isHome(s, "tib")).toBe(false);
    expect(isHome(s, "odile")).toBe(false);
    s.projects.push("jetty", "cottage_1");
    expect(isHome(s, "tib")).toBe(true);
    expect(isHome(s, "odile")).toBe(true);
    expect(isHome(s, "hesk")).toBe(false);
    s.stage = 1;
    expect(isHome(s, "hesk")).toBe(true);
  });
});
