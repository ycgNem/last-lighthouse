import { BALANCE } from "../data/balance";
import { ENEMIES } from "../data/enemies";
import { LOCATION_IDS, SKILL_IDS, type FlagId, type GearId, type ItemId, type LocationId, type ProjectId, type SkillId, type Yield } from "../data/ids";
import { GEAR, ITEMS, STARTING_GEAR } from "../data/items";
import { DEFAULT_STATIONS, PROJECTS, STAGES, type Requirements } from "../data/lighthouse";
import { LOCATIONS } from "../data/locations";
import { NODES, type NodeDef } from "../data/nodes";
import { PACE } from "../data/pacing";
import { MAIN_QUEST, type QuestStep } from "../data/quests";
import { getRecipe, RECIPES, type RecipeDef } from "../data/recipes";
import { SALVAGE, type Water } from "../data/salvage";
import { TIDE } from "../data/tide";
import { hasGear } from "./progression";
import { expectedPiece, lowTideIndex } from "./salvage";
import { levelForXp } from "./skills";
import { readTide } from "./tide";

// The pacing simulation. Plays Chapter 1 the way a typical player would,
// following the pinned objective, on *expected* yields against the real tide
// clock and recipes. At home it hooks whatever the tide brings into the cove,
// works the wreck field and the fishing spots when they have something it
// needs, and rebuilds as soon as the materials are in. It sets out on an
// expedition when one gets more of what the objective needs per minute than
// the cove does, and finds the beach stocked when it comes back. `npm test`
// holds the result to the GDD's pacing targets (data/pacing.ts);
// `__ll.economy()` prints it in a dev build.

export type TideState = "low" | "high";

/** A stretch at home, or an expedition. */
export interface Leg {
  /** "home" for a stretch at the Rest, else where the expedition went. */
  location: LocationId;
  /** The tide when it started (when you arrived, for an expedition). */
  tide: TideState;
  /** Minutes since the new game when it started (when you set out, for an expedition). */
  start: number;
  minutes: number;
  /** Minutes spent at home waiting for the tide before setting out. */
  waited: number;
  haul: Partial<Record<ItemId, number>>;
  /** Back home after an expedition: what had washed up on the beach and into the net meanwhile. */
  found: Partial<Record<ItemId, number>>;
  /** Satchel slots an expedition's haul fills, and how many there were. */
  slots: number;
  capacity: number;
  /** Story beats finished during it (or at home straight after an expedition), and when, in minutes. */
  beats: string[];
  beatTimes: number[];
}

export interface ChapterPlan {
  legs: Leg[];
  /** Minutes since the new game when each story beat (main quest step id, or a tool or prepared gear made) landed. */
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
  salvaged: number;
  /** The low tide the cove's spots were stocked for, and the uses left on each (LOCATIONS.home.nodes order). */
  cove: { tide: number; left: number[] };
}

const EPS = 1e-6;
const HOME_SPOTS = LOCATIONS.home.nodes;
const have = (s: Sim, item: ItemId) => s.items.get(item) ?? 0;
const add = (s: Sim, item: ItemId, qty: number) => s.items.set(item, have(s, item) + qty);
const level = (s: Sim, skill: SkillId) => levelForXp(s.xp[skill]);
/** The tide clock at a time since the new game. */
const clock = (t: number) => TIDE.newGameOffset + t;
const tideAt = (t: number): TideState => readTide(clock(t), TIDE).state;
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
    salvaged: 0,
    cove: { tide: -1, left: [] },
  };
}

function clone(s: Sim): Sim {
  return { ...s, items: new Map(s.items), xp: { ...s.xp }, gear: new Set(s.gear), projects: new Set(s.projects), keyItems: new Set(s.keyItems), flags: new Set(s.flags), crafted: { ...s.crafted }, cove: { tide: s.cove.tide, left: [...s.cove.left] } };
}

const met = (s: Sim, req: Requirements) =>
  (req.items ?? []).every((st) => have(s, st.item) >= st.qty - EPS) &&
  (req.keyItems ?? []).every((k) => s.keyItems.has(k)) &&
  (req.projects ?? []).every((p) => s.projects.has(p)) &&
  (req.flags ?? []).every((f) => s.flags.has(f)) &&
  (req.stage === undefined || s.stage >= req.stage);

const stations = (s: Sim) => [...DEFAULT_STATIONS, ...[...s.projects].flatMap((p) => PROJECTS[p].unlocksStation ?? [])];

function craft(s: Sim, r: RecipeDef): boolean {
  if (!stations(s).includes(r.station) || level(s, r.skill) < r.level) return false;
  if (r.requiresGear && !s.gear.has(r.requiresGear)) return false;
  if (r.output.kind === "gear" && hasGear(s.gear, r.output.gear)) return false;
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
const recipeFor = (g: GearId) => RECIPES.find((x) => x.output.kind === "gear" && x.output.gear === g);

/** Makes a piece of gear, first smelting whatever intermediates it needs, if the raw materials are there. */
function craftGear(s: Sim, g: GearId): boolean {
  const r = recipeFor(g);
  if (!r || hasGear(s.gear, g)) return false;
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
    case "salvage":
      return s.salvaged >= g.qty - EPS;
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

/** The pinned objective: the first step not done. */
const current = (s: Sim) => MAIN_QUEST.find((step) => !isDone(s, step));
const stepsDone = (s: Sim) => MAIN_QUEST.filter((step) => isDone(s, step)).length;
const prepared = (s: Sim) => PACE.prepared.every((g) => hasGear(s.gear, g));

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

/** At home: does what the objective asks as soon as it can, and makes the tools the trips ahead need. */
function settle(s: Sim): void {
  for (let changed = true; changed; ) {
    changed = false;
    const g = current(s)?.goal;
    if (g?.kind === "project" && met(s, PROJECTS[g.project].requires)) {
      const def = PROJECTS[g.project];
      for (const st of def.requires.items ?? []) add(s, st.item, -st.qty);
      if (def.xp) s.xp[def.xp.skill] += def.xp.amount;
      s.projects.add(g.project);
      changed = true;
    } else if (g?.kind === "craft") {
      const r = getRecipe(g.recipe);
      while (r && (s.crafted[r.id] ?? 0) < g.qty && craft(s, r)) changed = true;
    } else if (g?.kind === "stage" && advance(s, "home")) changed = true;
    if (s.stage >= 1) for (const t of PACE.tools) if (craftGear(s, t)) changed = true;
    // The Guardian's coming: get the kit together.
    if (s.stage >= 2) for (const p of PACE.prepared) if (craftGear(s, p)) changed = true;
  }
}

/**
 * Raw materials the objective (and the tools and kit due) still needs, crafted
 * ones counted as what they're made of; `ahead`, everything the rest of the
 * chapter needs.
 */
function needs(s: Sim, ahead = false): Map<ItemId, number> {
  const want = new Map<ItemId, number>();
  const ask = (item: ItemId, qty: number) => {
    const r = makes(item);
    if (r && r.output.kind === "item") for (const st of r.inputs) ask(st.item, (qty / r.output.qty) * st.qty);
    else want.set(item, (want.get(item) ?? 0) + qty);
  };
  for (const step of ahead ? MAIN_QUEST.filter((st) => !isDone(s, st)) : [current(s)]) {
    const g = step?.goal;
    if (g?.kind === "craft") {
      const r = getRecipe(g.recipe);
      const left = g.qty - (s.crafted[g.recipe] ?? 0);
      if (r && left > 0) for (const st of r.inputs) ask(st.item, st.qty * left);
    } else if (g?.kind === "project") {
      for (const st of PROJECTS[g.project].requires.items ?? []) ask(st.item, st.qty);
    } else if (g?.kind === "stage") {
      for (const st of STAGES[g.stage]?.requires.items ?? []) ask(st.item, st.qty);
    }
  }
  const kit: GearId[] = ahead ? [...PACE.tools, ...PACE.prepared] : [...(s.stage >= 1 ? PACE.tools : []), ...(s.stage >= 2 ? PACE.prepared : [])];
  for (const k of kit) if (!hasGear(s.gear, k)) for (const st of recipeFor(k)?.inputs ?? []) ask(st.item, st.qty);
  for (const [item, qty] of want) want.set(item, Math.max(0, qty - have(s, item)));
  return want;
}

function reachable(s: Sim, l: LocationId): boolean {
  if (l === "home" || LOCATIONS[l].revealedAtStage > s.stage) return false;
  return [...s.projects].some((p) => PROJECTS[p].unlocksOffshore);
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

/** Seconds one use of a node takes. */
const workTime = (node: NodeDef) =>
  (node.kind === "fish" ? PACE.perCatch : node.kind === "wreckage" ? PACE.perYank : node.gatherTime) + PACE.perNode / node.uses;

/** Whether a node can be worked with what you have, at this tide. */
const workable = (s: Sim, node: NodeDef, tide: TideState) =>
  (node.tide === "any" || node.tide === tide) &&
  (!node.requiresGear || hasGear(s.gear, node.requiresGear)) &&
  (node.kind === "wreckage" || !node.skill || level(s, node.skill) >= node.level);

/** Drift pieces coming in between two times since the new game, by the water they came in at. */
function drift(from: number, to: number): Map<Water, number> {
  const out = new Map<Water, number>();
  for (let t = clock(from); t < clock(to); ) {
    const r = readTide(t, TIDE);
    const step = Math.max(EPS, Math.min(r.phaseTimeLeft, clock(to) - t));
    out.set(r.phase, (out.get(r.phase) ?? 0) + step / SALVAGE.driftEvery[r.phase]);
    t += step;
  }
  return out;
}

/** A stint at home: the cove's spots first while they have something needed, and everything that drifts in meanwhile. */
function homeStint(s: Sim, seconds: number): Map<ItemId, number> {
  const haul = new Map<ItemId, number>();
  const gain = (item: ItemId, qty: number) => {
    add(s, item, qty);
    haul.set(item, (haul.get(item) ?? 0) + qty);
  };
  const low = lowTideIndex(clock(s.t));
  if (s.cove.tide !== low) s.cove = { tide: low, left: HOME_SPOTS.map((n) => n.count * NODES[n.node].uses) };
  const want = needs(s);
  const tide = tideAt(s.t);
  let busy = 0;
  HOME_SPOTS.forEach((n, i) => {
    const d = NODES[n.node];
    if ((n.needsProject && !s.projects.has(n.needsProject)) || !workable(s, d, tide)) return;
    while (s.cove.left[i]! > 0 && busy < seconds && d.yields.some((y) => (want.get(y.item) ?? 0) > EPS)) {
      busy += workTime(d);
      for (const y of d.yields) {
        gain(y.item, expected(y));
        want.set(y.item, (want.get(y.item) ?? 0) - expected(y));
      }
      if (d.skill) s.xp[d.skill] += d.xp;
      if (d.kind === "wreckage") s.salvaged++;
      s.cove.left[i]!--;
    }
  });
  // What drifts in gets hooked, or waits on the beach till you're free.
  for (const [water, pieces] of drift(s.t, s.t + seconds)) catchDrift(s, water, pieces * PACE.coveShare, gain);
  s.t += seconds;
  return haul;
}

function catchDrift(s: Sim, water: Water, pieces: number, gain: (item: ItemId, qty: number) => void): void {
  for (const [item, qty] of expectedPiece(water)) gain(item, qty * pieces);
  s.salvaged += pieces;
}

/** Home again (or for the first time): what's afloat in the cove, and after an expedition what drifted in meanwhile and washed up on the beach, or into the net. */
function cameHome(s: Sim, left: number | null): Map<ItemId, number> {
  const found = new Map<ItemId, number>();
  const gain = (item: ItemId, qty: number) => {
    add(s, item, qty);
    found.set(item, (found.get(item) ?? 0) + qty);
  };
  catchDrift(s, readTide(clock(s.t), TIDE).phase, SALVAGE.afloatOnArrival, gain);
  if (left === null) return found;
  const pieces = drift(left, s.t);
  const total = [...pieces.values()].reduce((a, b) => a + b, 0);
  const kept = Math.min(SALVAGE.beachMax, total * SALVAGE.awayBeachShare) + (s.projects.has("net_loft") ? Math.min(SALVAGE.net.max, total * SALVAGE.net.share) : 0);
  for (const [water, n] of pieces) catchDrift(s, water, total > 0 ? (n * kept) / total : 0, gain);
  return found;
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
  // Out here you hook what the rest of the chapter needs and leave the rest.
  const wanted = needs(s, true);
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
      if (nodesLeft[i]! <= 0 || !workable(s, d, tide)) return;
      if (d.keyItem ? s.keyItems.has(d.keyItem) : !d.yields.some((y) => (wanted.get(y.item) ?? 0) > EPS)) return;
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
      const d = NODES[L.nodes[p.i]!.node];
      t += workTime(d);
      for (const y of d.yields) {
        gain(y.item, expected(y));
        wanted.set(y.item, (wanted.get(y.item) ?? 0) - expected(y));
      }
      if (d.skill) s.xp[d.skill] += d.xp;
      if (d.keyItem) s.keyItems.add(d.keyItem);
      nodesLeft[p.i]!--;
    }
  }
  // A stage performed out here (relighting Saltmere).
  advance(s, loc);
  return { leave: t + PACE.explore[loc] + (first ? PACE.firstVisit[loc] : 0), haul };
}

/** What a stint or a trip did for the objective: the share of each outstanding need it covered, and anything it finished. */
function worth(before: Sim, after: Sim, haul: Map<ItemId, number>): number {
  let v = 0;
  for (const [item, need] of needs(before)) if (need > EPS) v += Math.min(haul.get(item) ?? 0, need) / need;
  const g = current(before)?.goal;
  if (g?.kind === "salvage") v += Math.min(1, (after.salvaged - before.salvaged) / g.qty);
  for (const k of after.keyItems) if (!before.keyItems.has(k)) v += 1;
  for (const f of after.flags) if (!before.flags.has(f)) v += 1;
  return v + (after.stage - before.stage) + (stepsDone(after) - stepsDone(before));
}

/** The first time at or after `from` when leaving gets you there at the tide you want. */
function departure(from: number, tide: TideState): number {
  for (let t = from; t < from + 2 * (TIDE.low + TIDE.high + 2 * TIDE.turn); t += 5) if (tideAt(t + PACE.travel) === tide) return t;
  return from;
}

const slotsFor = (haul: Map<ItemId, number>) => [...haul].reduce((n, [item, qty]) => n + Math.ceil(qty / ITEMS[item].stack - EPS), 0);
const round = (m: Map<ItemId, number>) => Object.fromEntries([...m].filter(([, v]) => v > EPS).map(([k, v]) => [k, Math.round(v * 10) / 10]));

export function planChapter(): ChapterPlan {
  const s = fresh();
  const plan: ChapterPlan = { legs: [], beats: {}, leftover: {} };
  const minutes = (t: number) => Math.round((t / 60) * 10) / 10;
  const landed = (leg: Leg): void => {
    const out: string[] = [];
    for (const step of MAIN_QUEST) if (!(step.id in plan.beats) && isDone(s, step)) out.push(step.id);
    for (const g of [...PACE.tools, ...PACE.prepared]) if (!(g in plan.beats) && s.gear.has(g)) out.push(g);
    for (const b of out) {
      plan.beats[b] = minutes(s.t);
      leg.beats.push(b);
      leg.beatTimes.push(minutes(s.t));
    }
    s.t += out.length * PACE.perBeat;
  };
  const newLeg = (location: LocationId, start: number): Leg => ({ location, tide: tideAt(start), start: minutes(start), minutes: 0, waited: 0, haul: {}, found: {}, slots: 0, capacity: 0, beats: [], beatTimes: [] });

  const visited = new Set<LocationId>();
  let home: Leg | null = newLeg("home", 0);
  let homeHaul = new Map<ItemId, number>();
  const closeHome = () => {
    if (!home) return;
    home.minutes = minutes(s.t) - home.start;
    home.haul = round(homeHaul);
    plan.legs.push(home);
    home = null;
    homeHaul = new Map();
  };

  s.t = PACE.intro;
  landed(home);
  s.t += PACE.firstCove;
  for (const [item, qty] of cameHome(s, null)) homeHaul.set(item, qty);
  const last = STAGES[STAGES.length - 1]!.index;
  for (let n = 0; n < 2000 && s.stage < last; n++) {
    const stint = clone(s);
    const stintHaul = homeStint(stint, PACE.stint);
    const homeRate = worth(s, stint, stintHaul) / PACE.stint;

    let best: { loc: LocationId; tide: TideState; depart: number; rate: number } | null = null;
    for (const loc of LOCATION_IDS) {
      if (!reachable(s, loc)) continue;
      for (const tide of ["low", "high"] as const) {
        const trial = clone(s);
        const depart = departure(s.t + PACE.prepare, tide);
        const { leave, haul } = visit(trial, loc, depart + PACE.travel, !visited.has(loc));
        const rate = worth(s, trial, haul) / (leave + PACE.travel - s.t);
        if (rate > EPS && (!best || rate > best.rate)) best = { loc, tide, depart, rate };
      }
    }

    if (best && best.rate > homeRate) {
      closeHome();
      const trip = newLeg(best.loc, best.depart);
      trip.tide = best.tide;
      trip.waited = minutes(best.depart - (s.t + PACE.prepare));
      trip.capacity = BALANCE.inventory.baseSlots + [...s.gear].reduce((k, g) => k + (GEAR[g].stats.satchelSlots ?? 0), 0);
      const { leave, haul } = visit(s, best.loc, best.depart + PACE.travel, !visited.has(best.loc));
      visited.add(best.loc);
      s.t = leave + PACE.travel;
      trip.haul = round(haul);
      trip.slots = slotsFor(haul);
      trip.found = round(cameHome(s, best.depart));
      settle(s);
      landed(trip);
      trip.minutes = minutes(s.t) - trip.start;
      plan.legs.push(trip);
      continue;
    }
    if (homeRate <= EPS) {
      plan.stalled = `nothing worth doing at stage ${s.stage}, on "${current(s)?.id}": still need ${[...needs(s)].filter(([, q]) => q > EPS).map(([i, q]) => `${q.toFixed(1)} ${i}`).join(", ") || "nothing material"}`;
      break;
    }
    home ??= newLeg("home", s.t);
    for (const [item, qty] of homeStint(s, PACE.stint)) homeHaul.set(item, (homeHaul.get(item) ?? 0) + qty);
    settle(s);
    landed(home);
  }
  closeHome();
  for (const [k, v] of s.items) if (v > EPS) plan.leftover[k] = Math.round(v * 10) / 10;
  return plan;
}

/** The plan as a few lines of text, for test failures and the dev console. */
export function describePlan(plan: ChapterPlan): string {
  const list = (r: Partial<Record<ItemId, number>>) =>
    Object.entries(r)
      .map(([k, v]) => `${v} ${k}`)
      .join(", ");
  const lines = plan.legs.map((l, i) => {
    const beats = l.beats.length ? `  -> ${l.beats.map((b, j) => `${b} @${l.beatTimes[j]!.toFixed(1)}`).join(", ")}` : "";
    if (l.location === "home") return `${i + 1}. ${l.start.toFixed(1)} min home ${l.minutes.toFixed(1)} min: ${list(l.haul)}${beats}`;
    const found = Object.keys(l.found).length ? ` [beach: ${list(l.found)}]` : "";
    return `${i + 1}. ${l.start.toFixed(1)} min ${l.location} (${l.tide}${l.waited > 0 ? `, waited ${l.waited.toFixed(1)}` : ""}) ${l.minutes.toFixed(1)} min, ${l.slots}/${l.capacity} slots: ${list(l.haul)}${found}${beats}`;
  });
  if (plan.stalled) lines.push(`stalled: ${plan.stalled}`);
  return lines.join("\n");
}
