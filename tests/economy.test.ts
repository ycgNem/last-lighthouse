import { describe, expect, it } from "vitest";
import { PACING } from "../src/data/pacing";
import { MAIN_QUEST } from "../src/data/quests";
import { describePlan, planChapter } from "../src/systems/economy";

// The economy pass (MILESTONES M7): a typical player's trips through Chapter 1
// on expected yields, held to the GDD's pacing. When one of these fails the
// message carries the whole plan, trip by trip: change the content, or the
// assumptions in data/pacing.ts if a playtest says they're wrong.

const plan = planChapter();
const story = describePlan(plan);

describe("economy: a typical player's Chapter 1", () => {
  it("finishes the chapter, every beat in story order", () => {
    expect(plan.stalled, story).toBeUndefined();
    const times = MAIN_QUEST.map((s) => plan.beats[s.id]);
    expect(times.every((t) => t !== undefined), story).toBe(true);
    for (let i = 1; i < times.length; i++) expect(times[i]!, `${MAIN_QUEST[i]!.id} before ${MAIN_QUEST[i - 1]!.id}\n${story}`).toBeGreaterThanOrEqual(times[i - 1]!);
  });

  it("restores the lamp in 15–25 minutes, on the second or third shore run (GDD §12, M4)", () => {
    const at = plan.beats.lamp ?? Infinity;
    const [lo, hi] = PACING.stage1Minutes;
    expect(at, story).toBeGreaterThanOrEqual(lo);
    expect(at, story).toBeLessThanOrEqual(hi);
    const runs = plan.trips.filter((t) => t.location === "shore" && t.start < at).length;
    expect(runs, story).toBeGreaterThanOrEqual(PACING.stage1ShoreRuns[0]);
    expect(runs, story).toBeLessThanOrEqual(PACING.stage1ShoreRuns[1]);
  });

  it("keeps every expedition the length of one (GDD §5)", () => {
    const [lo, hi] = PACING.tripMinutes;
    for (const t of plan.trips) {
      expect(t.minutes, story).toBeGreaterThanOrEqual(lo);
      expect(t.minutes, story).toBeLessThanOrEqual(hi);
    }
  });

  it("is never more than a couple of trips from the next story beat", () => {
    let since = 0;
    for (const t of plan.trips) {
      since = t.beats.length ? 0 : since + 1;
      expect(since, story).toBeLessThan(PACING.tripsPerBeat);
    }
  });

  it("fits every haul in the satchel", () => {
    for (const t of plan.trips) expect(t.slots, story).toBeLessThanOrEqual(t.capacity);
  });
});
