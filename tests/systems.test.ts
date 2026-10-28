import { describe, expect, it } from "vitest";
import { deserialize, SaveSystem, serialize, type KeyValueStore } from "../src/core/Save";
import { getRecipe } from "../src/data/recipes";
import { createNewGame } from "../src/state/GameState";
import { craft, craftBlock } from "../src/systems/crafting";
import { addItem, applyDeathLoss, available, carried, depositAll, satchelCapacity, stored } from "../src/systems/inventory";
import { advanceStage, completeProject, revealedLocations } from "../src/systems/progression";
import { advanceQuest, currentStep, stepMaterials } from "../src/systems/quests";
import { addXp, levelForXp } from "../src/systems/skills";

describe("inventory", () => {
  it("stacks, respects capacity and reports overflow", () => {
    const s = createNewGame();
    expect(addItem(s, "timber", 45)).toBe(45);
    expect(s.satchel.filter(Boolean)).toHaveLength(3); // 20 + 20 + 5
    const cap = satchelCapacity(s);
    expect(addItem(s, "scrap", 20 * cap)).toBe(20 * (cap - 3));
  });

  it("deposit-all banks materials but keeps food packed", () => {
    const s = createNewGame();
    addItem(s, "timber", 7);
    addItem(s, "grilled_silverfin", 3);
    depositAll(s);
    expect(stored(s, "timber")).toBe(7);
    expect(carried(s, "timber")).toBe(0);
    expect(carried(s, "grilled_silverfin")).toBe(3);
  });

  it("death loses 40% of each unbanked stack, keeps storage and key items", () => {
    const s = createNewGame();
    addItem(s, "timber", 10);
    addItem(s, "scrap", 1);
    addItem(s, "drowned_lens", 1);
    s.storage.brass = 5;
    const lost = applyDeathLoss(s);
    expect(lost).toEqual([{ item: "timber", qty: 4 }]);
    expect(carried(s, "timber")).toBe(6);
    expect(carried(s, "scrap")).toBe(1);
    expect(s.keyItems).toContain("drowned_lens");
    expect(stored(s, "brass")).toBe(5);
  });
});

describe("skills", () => {
  it("levels follow the XP table", () => {
    expect(levelForXp(0)).toBe(1);
    expect(levelForXp(39)).toBe(1);
    expect(levelForXp(40)).toBe(2);
    expect(levelForXp(99999)).toBe(10);
  });

  it("reports milestones crossed", () => {
    const s = createNewGame();
    const r = addXp(s, "salvaging", 200);
    expect(r.newLevel).toBe(4);
    expect(r.unlocked.map((m) => m.level)).toEqual([2, 4]);
  });
});

describe("crafting and progression", () => {
  it("forge recipes need the forge project", () => {
    const s = createNewGame();
    addItem(s, "scrap", 10);
    expect(craftBlock(s, getRecipe("iron_ingot")!)).toBe("station");
    addItem(s, "timber", 6);
    expect(completeProject(s, "forge")).toBe(true);
    expect(craftBlock(s, getRecipe("iron_ingot")!)).toBeNull();
  });

  it("cooking draws from storage too and counts for the quest", () => {
    const s = createNewGame();
    s.storage.silverfin = 3;
    for (let i = 0; i < 3; i++) expect(craft(s, getRecipe("grilled_silverfin")!).ok).toBe(true);
    expect(s.quest.crafted.grilled_silverfin).toBe(3);
    expect(available(s, "grilled_silverfin")).toBe(3);
  });

  it("can't craft gear you already own or outclass", () => {
    const s = createNewGame();
    s.gear.push("lamplighter");
    s.projects.push("forge");
    s.skillXp.smithing = 10_000;
    expect(craftBlock(s, getRecipe("boltcaster_mk2")!)).toBe("already_owned");
  });

  it("the main quest walks from new game to Stage 2 with the right inputs", () => {
    const s = createNewGame();
    const give = (item: Parameters<typeof addItem>[1], qty: number) => (s.storage[item] = (s.storage[item] ?? 0) + qty);

    s.quest.talked.push("maren");
    give("silverfin", 3);
    for (let i = 0; i < 3; i++) craft(s, getRecipe("grilled_silverfin")!);
    give("scrap", 8 + 10);
    give("timber", 6 + 12 + 6);
    give("kelp", 4);
    give("sea_glass", 6);
    expect(completeProject(s, "forge")).toBe(true);
    expect(completeProject(s, "dock")).toBe(true);
    expect(advanceStage(s, "home")?.name).toBe("Restored Lamp");
    expect(revealedLocations(s)).toContain("wreck");

    addItem(s, "drowned_lens", 1);
    give("brass", 8);
    give("tidestone", 5);
    expect(advanceStage(s, "beacon")).toBeUndefined(); // wrong place
    expect(advanceStage(s, "home")?.name).toBe("Focused Lens");
    expect(s.keyItems).toEqual(["lighthouse_ember"]);

    advanceQuest(s);
    expect(currentStep(s)?.id).toBe("relight");

    s.flags.push("guardian_defeated");
    expect(advanceStage(s, "beacon")?.name).toBe("First Beacon Relit");
    advanceQuest(s);
    expect(currentStep(s)).toBeUndefined();
  });

  it("the objective checklist counts only what's still needed", () => {
    const s = createNewGame();
    s.quest.talked.push("maren");
    advanceQuest(s);
    expect(currentStep(s)?.id).toBe("feed");
    expect(stepMaterials(s)).toEqual([{ item: "silverfin", qty: 3 }]);
    s.storage.silverfin = 2;
    craft(s, getRecipe("grilled_silverfin")!);
    craft(s, getRecipe("grilled_silverfin")!);
    expect(stepMaterials(s)).toEqual([{ item: "silverfin", qty: 1 }]);
  });
});

describe("save", () => {
  const memory = (): KeyValueStore => {
    const m = new Map<string, string>();
    return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => void m.set(k, v), removeItem: (k) => void m.delete(k) };
  };

  it("round-trips the whole state", () => {
    const s = createNewGame();
    addItem(s, "timber", 12);
    s.stage = 1;
    expect(deserialize(serialize(s))).toEqual(s);
  });

  it("fills fields missing from older saves", () => {
    const s = createNewGame();
    const raw = JSON.parse(serialize(s)) as Record<string, unknown>;
    delete raw.settings;
    expect(deserialize(JSON.stringify(raw)).settings.fov).toBe(75);
  });

  it("reset clears the save", () => {
    const store = memory();
    const saves = new SaveSystem(store);
    saves.write(createNewGame());
    expect(saves.load()).not.toBeNull();
    saves.reset();
    expect(saves.load()).toBeNull();
  });
});
