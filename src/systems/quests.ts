import type { ItemStack } from "../data/ids";
import { PROJECTS, STAGES } from "../data/lighthouse";
import { MAIN_QUEST, type QuestStep } from "../data/quests";
import { getRecipe } from "../data/recipes";
import type { GameState } from "../state/GameState";

export function currentStep(state: GameState): QuestStep | undefined {
  return MAIN_QUEST[state.quest.step];
}

export function isStepDone(state: GameState, step: QuestStep): boolean {
  const g = step.goal;
  switch (g.kind) {
    case "talk":
      return state.quest.talked.includes(g.npc);
    case "craft":
      return (state.quest.crafted[g.recipe] ?? 0) >= g.qty;
    case "project":
      return state.projects.includes(g.project);
    case "stage":
      return state.stage >= g.stage;
    case "keyItem":
      // Key items can be consumed by a later stage, which still counts.
      return state.keyItems.includes(g.item) || state.stage >= 2;
    case "flag":
      return state.flags.includes(g.flag);
  }
}

/** Advances past every finished step. Returns the steps completed now. */
export function advanceQuest(state: GameState): QuestStep[] {
  const done: QuestStep[] = [];
  for (let step = currentStep(state); step && isStepDone(state, step); step = currentStep(state)) {
    done.push(step);
    state.quest.step++;
  }
  return done;
}

/** Materials the current step needs, for the pinned objective's checklist. */
export function stepMaterials(state: GameState): ItemStack[] {
  const step = currentStep(state);
  if (!step) return [];
  const g = step.goal;
  if (g.kind === "project") return PROJECTS[g.project].requires.items ?? [];
  if (g.kind === "stage") return STAGES[g.stage]?.requires.items ?? [];
  if (g.kind === "craft") {
    // Only what's still needed: two meals cooked of three leaves one meal's worth.
    const r = getRecipe(g.recipe);
    const left = Math.max(0, g.qty - (state.quest.crafted[g.recipe] ?? 0));
    return r && left ? r.inputs.map((s) => ({ item: s.item, qty: s.qty * left })) : [];
  }
  return [];
}
