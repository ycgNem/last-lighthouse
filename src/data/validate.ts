// Content checks. Run by `npm test` and at boot in dev.
//  1. Integrity: things the type system can't catch (duplicates, bad ranges, tells too short).
//  2. Reachability: starting from a new game and using only *guaranteed* sources
//     (yields with min > 0), can the chapter be finished? This is the softlock test.

import { ENEMIES } from "./enemies";
import { ENEMY_IDS, ITEM_IDS, LOCATION_IDS, NODE_IDS, SKILL_IDS, type FlagId, type GearId, type ItemId, type LocationId, type ProjectId, type SkillId } from "./ids";
import { GEAR, ITEMS, STARTING_GEAR } from "./items";
import { DEFAULT_STATIONS, PROJECTS, STAGES, type Requirements } from "./lighthouse";
import { LOCATIONS } from "./locations";
import { NODES } from "./nodes";
import { MAIN_QUEST } from "./quests";
import { RECIPES } from "./recipes";
import { MAX_LEVEL } from "./skills";

export function validateIntegrity(): string[] {
  const errors: string[] = [];

  const ids = new Set<string>();
  for (const r of RECIPES) {
    if (ids.has(r.id)) errors.push(`recipe "${r.id}" defined twice`);
    ids.add(r.id);
    if (r.inputs.length === 0) errors.push(`recipe "${r.id}" has no inputs`);
  }

  for (const id of ITEM_IDS) {
    const it = ITEMS[id];
    if (it.category === "food" && !it.food) errors.push(`food "${id}" has no food effect`);
    if (it.category === "key" && it.stack !== 1) errors.push(`key item "${id}" must stack to 1`);
  }

  for (const id of NODE_IDS) {
    const n = NODES[id];
    for (const y of n.yields) if (y.max < y.min) errors.push(`node "${id}" yield ${y.item} max < min`);
    if (n.keyItem && n.tide !== "any") errors.push(`key-item node "${id}" must be reachable at any tide`);
    if (n.kind === "fish" && !n.requiresGear) errors.push(`fishing node "${id}" must require a rod`);
  }

  for (const id of ENEMY_IDS) {
    for (const a of ENEMIES[id].attacks) {
      if (a.windup < 0.4) errors.push(`enemy "${id}" attack "${a.id}" windup ${a.windup}s < 0.4s readability minimum`);
    }
  }

  STAGES.forEach((s, i) => {
    if (s.index !== i) errors.push(`stage at position ${i} has index ${s.index}`);
  });

  for (const step of MAIN_QUEST) {
    if (step.goal.kind === "craft") {
      const recipe = step.goal.recipe;
      if (!RECIPES.some((r) => r.id === recipe)) errors.push(`quest "${step.id}" references unknown recipe "${recipe}"`);
    }
  }

  // Every key item needs exactly one source.
  for (const id of ITEM_IDS) {
    if (ITEMS[id].category !== "key") continue;
    const sources = NODE_IDS.filter((n) => NODES[n].keyItem === id).length + STAGES.filter((s) => s.grantsKeyItems.includes(id)).length;
    if (sources !== 1) errors.push(`key item "${id}" has ${sources} sources (expected 1)`);
  }

  for (const l of LOCATION_IDS) {
    const [near] = LOCATIONS[l].fog;
    if (!LOCATIONS[l].safe && near < 35) errors.push(`location "${l}" fog starts at ${near} m (< 35 m combat range)`);
  }

  return errors;
}

export interface ReachabilityReport {
  finalStage: number;
  projects: ProjectId[];
  gear: GearId[];
  blockedBy: string[];
}

/** Fixed-point simulation over guaranteed sources only. */
export function simulateProgression(): ReachabilityReport {
  let stage = 0;
  const projects = new Set<ProjectId>();
  const gear = new Set<GearId>(STARTING_GEAR);
  const flags = new Set<FlagId>();
  const keyItems = new Set<ItemId>();
  const items = new Set<ItemId>();
  const skillCap: Record<SkillId, number> = Object.fromEntries(SKILL_IDS.map((s) => [s, 1])) as Record<SkillId, number>;

  const offshore = () => [...projects].some((p) => PROJECTS[p].unlocksOffshore);
  const reachable = (l: LocationId) => LOCATIONS[l].revealedAtStage <= stage && (l === "home" || l === "shore" || offshore());
  const stations = () => [...DEFAULT_STATIONS, ...[...projects].flatMap((p) => PROJECTS[p].unlocksStation ?? [])];
  const met = (req: Requirements) =>
    (req.items ?? []).every((s) => items.has(s.item)) &&
    (req.keyItems ?? []).every((k) => keyItems.has(k)) &&
    (req.projects ?? []).every((p) => projects.has(p)) &&
    (req.flags ?? []).every((f) => flags.has(f));

  let changed = true;
  while (changed) {
    changed = false;
    const mark = <T>(set: Set<T>, v: T) => {
      if (!set.has(v)) {
        set.add(v);
        changed = true;
      }
    };
    const raiseSkill = (s: SkillId) => {
      // Every XP source is repeatable, so one accessible source means the skill can be maxed.
      if (skillCap[s] < MAX_LEVEL) {
        skillCap[s] = MAX_LEVEL;
        changed = true;
      }
    };

    for (const l of LOCATION_IDS.filter(reachable)) {
      for (const { node } of LOCATIONS[l].nodes) {
        const n = NODES[node];
        if (n.skill && skillCap[n.skill] < n.level) continue;
        if (n.requiresGear && !gear.has(n.requiresGear)) continue;
        for (const y of n.yields) if (y.min > 0) mark(items, y.item);
        if (n.keyItem) mark(keyItems, n.keyItem);
        if (n.skill && n.xp > 0) raiseSkill(n.skill);
      }
      for (const { enemy } of LOCATIONS[l].enemies) {
        const e = ENEMIES[enemy];
        for (const y of e.drops) if (y.min > 0) mark(items, y.item);
        if (e.grantsFlag) mark(flags, e.grantsFlag);
        raiseSkill("combat");
      }
    }

    for (const r of RECIPES) {
      if (!stations().includes(r.station) || skillCap[r.skill] < r.level) continue;
      if (r.requiresGear && !gear.has(r.requiresGear)) continue;
      if (!r.inputs.every((s) => items.has(s.item))) continue;
      if (r.output.kind === "item") mark(items, r.output.item);
      else mark(gear, r.output.gear);
      raiseSkill(r.skill);
    }

    for (const p of Object.keys(PROJECTS) as ProjectId[]) {
      if (met(PROJECTS[p].requires)) mark(projects, p);
    }

    const next = STAGES[stage + 1];
    if (next && met(next.requires) && reachable(next.performedAt)) {
      stage++;
      for (const k of next.grantsKeyItems) keyItems.add(k);
      changed = true;
    }
  }

  const blockedBy: string[] = [];
  const next = STAGES[stage + 1];
  if (next) {
    for (const s of next.requires.items ?? []) if (!items.has(s.item)) blockedBy.push(`item:${s.item}`);
    for (const k of next.requires.keyItems ?? []) if (!keyItems.has(k)) blockedBy.push(`key:${k}`);
    for (const p of next.requires.projects ?? []) if (!projects.has(p)) blockedBy.push(`project:${p}`);
    for (const f of next.requires.flags ?? []) if (!flags.has(f)) blockedBy.push(`flag:${f}`);
    if (!reachable(next.performedAt)) blockedBy.push(`location:${next.performedAt}`);
  }

  // Every gear piece should be craftable eventually, or it's dead content.
  for (const g of Object.keys(GEAR) as GearId[]) if (!gear.has(g)) blockedBy.push(`gear-unreachable:${g}`);

  return { finalStage: stage, projects: [...projects], gear: [...gear], blockedBy };
}

export function validateData(): string[] {
  const errors = validateIntegrity();
  const report = simulateProgression();
  const last = STAGES[STAGES.length - 1]?.index ?? 0;
  if (report.finalStage < last) errors.push(`progression softlock at stage ${report.finalStage}: ${report.blockedBy.join(", ")}`);
  for (const b of report.blockedBy.filter((b) => b.startsWith("gear-unreachable"))) errors.push(b);
  return errors;
}
