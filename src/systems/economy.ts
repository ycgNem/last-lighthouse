import { BALANCE } from "../data/balance";
import { ENEMIES } from "../data/enemies";
import { LOCATION_IDS, SKILL_IDS, type FlagId, type GearId, type ItemId, type LocationId, type ProjectId, type SkillId, type Yield } from "../data/ids";
import { GEAR, ITEMS, STARTING_GEAR } from "../data/items";
import { DEFAULT_STATIONS, PROJECTS, STAGES, type Requirements } from "../data/lighthouse";
import { LOCATIONS } from "../data/locations";
import { NODES } from "../data/nodes";
import { PACE } from "../data/pacing";
import { MAIN_QUEST, type QuestStep } from "../data/quests";
import { getRecipe, RECIPES, type RecipeDef } from "../data/recipes";
import { TIDE } from "../data/tide";
import { levelForXp } from "./skills";
import { readTide } from "./tide";

// The pacing simulation. Plays Chapter 1 the way a typical player would, on
// *expected* yields, against the real tide clock, skill gates and recipes: each
// time home, it does whatever the materials allow, then picks the trip (where,
// and at which tide, waiting for it if that's worth it) that gets the most of
// what's still needed per minute. `npm test` holds the result to the GDD's
// pacing targets (data/pacing.ts); `__ll.economy()` prints it in a dev build.

export type TideState = "low" | "high";

export interface Trip {
  location: LocationId;
  /** The tide when you arrive. */
  tide: TideState;
  /** Minutes since the new game when you set out. */
  start: number;
  /** Minutes away from home. */
  minutes: number;
  /** Minutes spent at home waiting for the tide first. */
  waited: number;
  haul: Partial<Record<ItemId, number>>;
  /** Satchel slots the haul fills, and how many there were. */
  slots: number;
  capacity: number;
  /** Story beats finished on the trip or at home straight after it. */
  beats: string[];
}

export interface ChapterPlan {
  trips: Trip[];
  /** Minutes since the new game when each story beat (main quest step id, or prepared gear) landed. */
  beats: Record<string, number>;
  /** Why the plan stopped short, if it did. */
  stalled?: string;
  /** Materials left over at the end. */
  leftover: Partial<Record<ItemId, number>>;
}

interface Sim {
  t: number;
  items: Map<ItemId, number>;
  xp: Record<SkillId, number>;
  gear: Set<GearId>;
  projects: Set<ProjectId>;
  stage: number;
  keyItems: Set<ItemId>;
  flags: Set<FlagId>;
  crafted: Record<string, number>;
}

const EPS = 1e-6;
const have = (s: Sim, item: ItemId) => s.items.get(item) ?? 0;
const add = (s: Sim, item: ItemId, qty: number) => s.items.set(item, have(s, item) + qty);
const level = (s: Sim, skill: SkillId) => levelForXp(s.xp[skill]);
const tideAt = (t: number): TideState => readTide(TIDE.newGameOffset + t, TIDE).state;
const expected = (y: Yield) => (y.min + y.max) / 2;

function fresh(): Sim {
  return {
    t: 0,
    items: new Map(),
    xp: Object.fromEntries(SKILL_IDS.map((k) => [k, 0])) as Record<SkillId, number>,
    gear: new Set(STARTING_GEAR),
    projects: new Set(),
    stage: 0,
    keyItems: new Set(),
    flags: new Set(),
    crafted: {},
  };
}

function clone(s: Sim): Sim {
  return { ...s, items: new Map(s.items), xp: { ...s.xp }, gear: new Set(s.gear), projects: new Set(s.projects), keyItems: new Set(s.keyItems), flags: new Set(s.flags), crafted: { ...s.crafted } };
}

const met = (s: Sim, req: Requirements) =>
  (req.items ?? []).every((st) => have(s, st.item) >= st.qty - EPS) &&
  (req.keyItems ?? []).every((k) => s.keyItems.has(k)) &&
  (req.projects ?? []).every((p) => s.projects.has(p)) &&
  (req.flags ?? []).every((f) => s.flags.has(f));

const stations = (s: Sim) => [...DEFAULT_STATIONS, ...[...s.projects].flatMap((p) => PROJECTS[p].unlocksStation ?? [])];

function craft(s: Sim, r: RecipeDef): boolean {
  if (!stations(s).includes(r.station) || level(s, r.skill) < r.level) return false;
  if (r.requiresGear && !s.gear.has(r.requiresGear)) return false;
  if (r.output.kind === "gear" && s.gear.has(r.output.gear)) return false;
  if (!r.inputs.every((st) => have(s, st.item) >= st.qty - EPS)) return false;
  for (const st of r.inputs) add(s, st.item, -st.qty);
  if (r.output.kind === "item") add(s, r.output.item, r.output.qty);
  else s.gear.add(r.output.gear);
  s.xp[r.skill] += r.xp;
  s.crafted[r.id] = (s.crafted[r.id] ?? 0) + 1;
  return true;
}

/** The recipe that makes an intermediate material (iron ingots from scrap). */
const makes = (item: ItemId) => RECIPES.find((r) => r.output.kind === "item" && r.output.item === item);

/** Makes a piece of gear, first smelting whatever intermediates it needs, if the raw materials are there. */
function craftGear(s: Sim, g: GearId): boolean {
  const r = RECIPES.find((x) => x.output.kind === "gear" && x.output.gear === g);
  if (!r || s.gear.has(g)) return false;
  const trial = clone(s);
  for (const st of r.inputs) {
    const sub = makes(st.item);
    while (sub && have(trial, st.item) < st.qty - EPS) if (!craft(trial, sub)) return false;
  }
  if (!craft(trial, r)) return false;
  Object.assign(s, trial);
  return true;
}

function isDone(s: Sim, step: QuestStep): boolean {
  const g = step.goal;
  switch (g.kind) {
    case "talk":
      return true; // Maren, at the start
    case "craft":
      return (s.crafted[g.recipe] ?? 0) >= g.qty;
    case "project":
      return s.projects.has(g.project);
    case "stage":
      return s.stage >= g.stage;
    case "keyItem":
      return s.keyItems.has(g.item) || s.stage >= 2;
    case "flag":
      return s.flags.has(g.flag);
  }
}

const prepared = (s: Sim) => PACE.prepared.every((g) => s.gear.has(g));

function advance(s: Sim, here: LocationId): boolean {
  const next = STAGES[s.stage + 1];
  if (!next || next.performedAt !== here || !met(s, next.requires)) return false;
  for (const st of next.requires.items ?? []) add(s, st.item, -st.qty);
  for (const k of next.consumesKeyItems) s.keyItems.delete(k);
  for (const k of next.grantsKeyItems) s.keyItems.add(k);
  if (next.xp) s.xp[next.xp.skill] += next.xp.amount;
  s.stage++;
  return true;
}

/** Everything that can be done at home with what's in storage. */
function atHome(s: Sim): void {
  for (let changed = true; changed; ) {
    changed = false;
    for (const step of MAIN_QUEST) {
      if (step.goal.kind !== "craft") continue;
      const r = getRecipe(step.goal.recipe);
      while (r && (s.crafted[r.id] ?? 0) < step.goal.qty && craft(s, r)) changed = true;
    }
    for (const p of Object.keys(PROJECTS) as ProjectId[]) {
      const def = PROJECTS[p];
      if (s.projects.has(p) || !met(s, def.requires)) continue;
      for (const st of def.requires.items ?? []) add(s, st.item, -st.qty);
      if (def.xp) s.xp[def.xp.skill] += def.xp.amount;
      s.projects.add(p);
      changed = true;
    }
    if (advance(s, "home")) changed = true;
    // The Guardian's coming: get the kit together.
    if (s.stage >= 2) for (const g of PACE.prepared) if (craftGear(s, g)) changed = true;
  }
}

/** Raw materials still needed for the rest of the chapter, crafted ones counted as what they're made of. */
function needs(s: Sim): Map<ItemId, number> {
  const want = new Map<ItemId, number>();
  const ask = (item: ItemId, qty: number) => {
    const r = makes(item);
    if (r && r.output.kind === "item") for (const st of r.inputs) ask(st.item, (qty / r.output.qty) * st.qty);
    else want.set(item, (want.get(item) ?? 0) + qty);
  };
  for (const step of MAIN_QUEST) {
    if (step.goal.kind !== "craft") continue;
    const r = getRecipe(step.goal.recipe);
    const left = step.goal.qty - (s.crafted[step.goal.recipe] ?? 0);
    if (r && left > 0) for (const st of r.inputs) ask(st.item, st.qty * left);
  }
  for (const p of Object.keys(PROJECTS) as ProjectId[]) if (!s.projects.has(p)) for (const st of PROJECTS[p].requires.items ?? []) ask(st.item, st.qty);
  for (const st of STAGES.slice(s.stage + 1)) for (const it of st.requires.items ?? []) ask(it.item, it.qty);
  for (const g of PACE.prepared) {
    const r = RECIPES.find((x) => x.output.kind === "gear" && x.output.gear === g);
    if (r && !s.gear.has(g)) for (const st of r.inputs) ask(st.item, st.qty);
  }
  for (const [item, qty] of want) want.set(item, Math.max(0, qty - have(s, item)));
  return want;
}

function reachable(s: Sim, l: LocationId): boolean {
  if (l === "home" || LOCATIONS[l].revealedAtStage > s.stage) return false;
  return l === "shore" || [...s.projects].some((p) => PROJECTS[p].unlocksOffshore);
}

/** Damage per second with the best bolt-caster owned. */
function dps(s: Sim): number {
  let best = 0;
  for (const g of s.gear) {
    const st = GEAR[g].stats;
    if (GEAR[g].slot === "weapon") best = Math.max(best, (st.boltDamage ?? 0) * (st.fireRate ?? 0));
  }
  return best * PACE.accuracy;
}

/** One visit, from arriving at the landing to leaving it. Changes `s`; returns when you leave and what you got. */
function visit(s: Sim, loc: LocationId, arrive: number, first: boolean): { leave: number; haul: Map<ItemId, number> } {
  const L = LOCATIONS[loc];
  const haul = new Map<ItemId, number>();
  const gain = (item: ItemId, qty: number) => {
    add(s, item, qty);
    haul.set(item, (haul.get(item) ?? 0) + qty);
  };
  const nodesLeft = L.nodes.map((n) => n.count * NODES[n.node].uses);
  const foesLeft = L.enemies.map((e) => e.count);
  let t = arrive;
  for (;;) {
    const tide = tideAt(t);
    // What can be done now; things only this tide allows come first, since they won't wait.
    let pick: { foe: boolean; i: number } | null = null;
    let pickBound = false;
    const offer = (foe: boolean, i: number, bound: boolean) => {
      if (!pick || (bound && !pickBound)) {
        pick = { foe, i };
        pickBound = bound;
      }
    };
    L.enemies.forEach((e, i) => {
      const def = ENEMIES[e.enemy];
      if (foesLeft[i]! <= 0 || (e.tide !== "any" && e.tide !== tide)) return;
      // The Guardian: fought once, and only when ready for it.
      if (def.grantsFlag && (s.flags.has(def.grantsFlag) || !prepared(s))) return;
      offer(true, i, e.tide !== "any");
    });
    L.nodes.forEach((n, i) => {
      const d = NODES[n.node];
      if (nodesLeft[i]! <= 0 || (d.tide !== "any" && d.tide !== tide)) return;
      if ((d.skill && level(s, d.skill) < d.level) || (d.requiresGear && !s.gear.has(d.requiresGear))) return;
      if (d.keyItem && s.keyItems.has(d.keyItem)) return;
      offer(false, i, d.tide !== "any");
    });
    const p = pick as { foe: boolean; i: number } | null;
    if (!p) break;
    if (p.foe) {
      const e = L.enemies[p.i]!;
      const def = ENEMIES[e.enemy];
      t += def.grantsFlag ? PACE.boss : PACE.perFight + def.hp / dps(s);
      for (const y of def.drops) gain(y.item, expected(y));
      s.xp.combat += def.combatXp;
      if (def.grantsFlag) s.flags.add(def.grantsFlag);
      foesLeft[p.i]!--;
    } else {
      const n = L.nodes[p.i]!;
      const d = NODES[n.node];
      t += (d.kind === "fish" ? PACE.perCatch : d.gatherTime) + PACE.perNode / d.uses;
      for (const y of d.yields) gain(y.item, expected(y));
      if (d.skill) s.xp[d.skill] += d.xp;
      if (d.keyItem) s.keyItems.add(d.keyItem);
      nodesLeft[p.i]!--;
    }
  }
  // A stage performed out here (relighting Saltmere).
  advance(s, loc);
  return { leave: t + PACE.explore[loc] + (first ? PACE.firstVisit[loc] : 0), haul };
}

/** Value of a trip: the share of each outstanding need it covers, plus anything the story needs from out there. */
function worth(before: Sim, after: Sim, haul: Map<ItemId, number>): number {
  let v = 0;
  for (const [item, need] of needs(before)) if (need > EPS) v += Math.min(haul.get(item) ?? 0, need) / need;
  for (const k of after.keyItems) if (!before.keyItems.has(k)) v += 1;
  for (const f of after.flags) if (!before.flags.has(f)) v += 1;
  return v + (after.stage - before.stage);
}

/** The first time at or after `from` when leaving gets you there at the tide you want. */
function departure(from: number, tide: TideState): number {
  for (let t = from; t < from + 2 * (TIDE.low + TIDE.high + 2 * TIDE.turn); t += 5) if (tideAt(t + PACE.travel) === tide) return t;
  return from;
}

const slotsFor = (haul: Map<ItemId, number>) => [...haul].reduce((n, [item, qty]) => n + Math.ceil(qty / ITEMS[item].stack - EPS), 0);

export function planChapter(): ChapterPlan {
  const s = fresh();
  const plan: ChapterPlan = { trips: [], beats: {}, leftover: {} };
  const minutes = (t: number) => Math.round((t / 60) * 10) / 10;
  const landed = (): string[] => {
    const out: string[] = [];
    for (const step of MAIN_QUEST) if (!(step.id in plan.beats) && isDone(s, step)) out.push(step.id);
    for (const g of PACE.prepared) if (!(g in plan.beats) && s.gear.has(g)) out.push(g);
    for (const b of out) plan.beats[b] = minutes(s.t);
    return out;
  };

  const visited = new Set<LocationId>();
  s.t = PACE.intro;
  atHome(s);
  landed();
  const last = STAGES[STAGES.length - 1]!.index;
  for (let n = 0; n < 40 && s.stage < last; n++) {
    let best: { loc: LocationId; tide: TideState; depart: number; rate: number; value: number } | null = null;
    for (const loc of LOCATION_IDS) {
      if (!reachable(s, loc)) continue;
      for (const tide of ["low", "high"] as const) {
        const trial = clone(s);
        const depart = departure(s.t + PACE.prepare, tide);
        const { leave, haul } = visit(trial, loc, depart + PACE.travel, !visited.has(loc));
        const value = worth(s, trial, haul);
        const rate = value / (leave + PACE.travel - s.t);
        if (value > EPS && (!best || rate > best.rate)) best = { loc, tide, depart, rate, value };
      }
    }
    if (!best) {
      plan.stalled = `nothing left worth a trip at stage ${s.stage}: still need ${[...needs(s)].filter(([, q]) => q > EPS).map(([i, q]) => `${q.toFixed(1)} ${i}`).join(", ")}`;
      break;
    }
    const capacity = BALANCE.inventory.baseSlots + [...s.gear].reduce((k, g) => k + (GEAR[g].stats.satchelSlots ?? 0), 0);
    const { leave, haul } = visit(s, best.loc, best.depart + PACE.travel, !visited.has(best.loc));
    visited.add(best.loc);
    const waited = best.depart - (s.t + PACE.prepare);
    const start = best.depart;
    s.t = leave + PACE.travel;
    const beats = landed();
    atHome(s);
    beats.push(...landed());
    s.t += beats.length * PACE.perBeat;
    plan.trips.push({
      location: best.loc,
      tide: best.tide,
      start: minutes(start),
      minutes: minutes(s.t - start),
      waited: minutes(waited),
      haul: Object.fromEntries([...haul].map(([k, v]) => [k, Math.round(v * 10) / 10])),
      slots: slotsFor(haul),
      capacity,
      beats,
    });
  }
  for (const [k, v] of s.items) if (v > EPS) plan.leftover[k] = Math.round(v * 10) / 10;
  return plan;
}

/** The plan as a few lines of text, for test failures and the dev console. */
export function describePlan(plan: ChapterPlan): string {
  const lines = plan.trips.map((t, i) => {
    const haul = Object.entries(t.haul)
      .map(([k, v]) => `${v} ${k}`)
      .join(", ");
    return `${i + 1}. ${t.start.toFixed(1)} min ${t.location} (${t.tide}${t.waited > 0 ? `, waited ${t.waited.toFixed(1)}` : ""}) ${t.minutes.toFixed(1)} min, ${t.slots}/${t.capacity} slots: ${haul}${t.beats.length ? `  -> ${t.beats.join(", ")}` : ""}`;
  });
  if (plan.stalled) lines.push(`stalled: ${plan.stalled}`);
  return lines.join("\n");
}
