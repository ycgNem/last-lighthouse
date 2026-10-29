import { describe, expect, it } from "vitest";
import { PACING } from "../src/data/pacing";
import { MAIN_QUEST } from "../src/data/quests";
import { describePlan, planChapter } from "../src/systems/economy";

// The economy pass (MILESTONES M7): a typical player's Chapter 1, hooking the
// cove's drift and rebuilding the Rest, then out on expeditions, on expected
// yields and held to the GDD's pacing. When one of these fails the message
// carries the whole plan, leg by leg: change the content, or the assumptions
// in data/pacing.ts if a playtest says they're wrong.

const plan = planChapter();
const story = describePlan(plan);
const trips = plan.legs.filter((l) => l.location !== "home");
const home = plan.legs.filter((l) => l.location === "home");

describe("economy: a typical player's Chapter 1", () => {
  it("finishes the chapter, every beat in story order", () => {
    expect(plan.stalled, story).toBeUndefined();
    const times = MAIN_QUEST.map((s) => plan.beats[s.id]);
    expect(times.every((t) => t !== undefined), story).toBe(true);
    for (let i = 1; i < times.length; i++) expect(times[i]!, `${MAIN_QUEST[i]!.id} before ${MAIN_QUEST[i - 1]!.id}\n${story}`).toBeGreaterThanOrEqual(times[i - 1]!);
  });

  it("rebuilds the forge within the first few minutes", () => {
    const at = plan.beats.forge ?? Infinity;
    const [lo, hi] = PACING.firstBuildMinutes;
    expect(at, story).toBeGreaterThanOrEqual(lo);
    expect(at, story).toBeLessThanOrEqual(hi);
  });

  it("restores the lamp in 15–25 minutes, all of it from the cove (GDD §12, M4)", () => {
    const at = plan.beats.lamp ?? Infinity;
    const [lo, hi] = PACING.stage1Minutes;
    expect(at, story).toBeGreaterThanOrEqual(lo);
    expect(at, story).toBeLessThanOrEqual(hi);
    expect(trips.filter((t) => t.start < at), story).toEqual([]);
  });

  it("never spends long at home without something new standing", () => {
    for (const leg of home) {
      const marks = [leg.start, ...leg.beatTimes, leg.start + leg.minutes];
      for (let i = 1; i < marks.length; i++) expect(marks[i]! - marks[i - 1]!, story).toBeLessThanOrEqual(PACING.homeMinutesPerBeat);
    }
  });

  it("keeps every expedition the length of one (GDD §5)", () => {
    const [lo, hi] = PACING.tripMinutes;
    expect(trips.length, story).toBeGreaterThan(0);
    for (const t of trips) {
      expect(t.minutes, story).toBeGreaterThanOrEqual(lo);
      expect(t.minutes, story).toBeLessThanOrEqual(hi);
    }
  });

  it("is never more than a couple of trips from the next story beat", () => {
    let since = 0;
    for (const t of trips) {
      since = t.beats.length ? 0 : since + 1;
      expect(since, story).toBeLessThan(PACING.tripsPerBeat);
    }
  });

  it("fits every haul in the satchel", () => {
    for (const t of trips) expect(t.slots, story).toBeLessThanOrEqual(t.capacity);
  });
});
