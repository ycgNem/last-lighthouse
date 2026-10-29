import type { ItemId, ItemStack, ProjectId } from "../data/ids";
import { PROJECTS } from "../data/lighthouse";
import type { GameState } from "../state/GameState";
import { available, removeAvailable } from "./inventory";
import { isMet, missingFor } from "./progression";
import { addXp, type XpResult } from "./skills";

// Rebuilding the Rest's plots. Materials go in whenever you have them, a few
// at a time, from the satchel first and then the chest; the plot stands once
// the last of them is in.

/** Whether the plot takes materials yet: everything it needs but the materials holds. */
export function plotOpen(state: GameState, id: ProjectId): boolean {
  if (state.projects.includes(id)) return false;
  return isMet(missingFor(state, { ...PROJECTS[id].requires, items: [] }));
}

export function delivered(state: GameState, id: ProjectId, item: ItemId): number {
  return state.build[id]?.[item] ?? 0;
}

/** Materials still to hand in. */
export function remaining(state: GameState, id: ProjectId): ItemStack[] {
  if (state.projects.includes(id)) return [];
  return (PROJECTS[id].requires.items ?? []).map((s) => ({ item: s.item, qty: s.qty - delivered(state, id, s.item) })).filter((s) => s.qty > 0);
}

/** Share of the materials handed in, 0..1; 1 once it stands. */
export function buildProgress(state: GameState, id: ProjectId): number {
  if (state.projects.includes(id)) return 1;
  const items = PROJECTS[id].requires.items ?? [];
  const total = items.reduce((n, s) => n + s.qty, 0);
  return total > 0 ? items.reduce((n, s) => n + Math.min(s.qty, delivered(state, id, s.item)), 0) / total : 0;
}

export interface Delivery {
  /** What went in this time. */
  given: ItemStack[];
  /** The plot stands now. */
  finished: boolean;
  xp?: XpResult;
}

/** Hands in what the plot still needs that you have, satchel first, and finishes it when it's all in. */
export function deliver(state: GameState, id: ProjectId): Delivery {
  if (!plotOpen(state, id)) return { given: [], finished: false };
  const given: ItemStack[] = [];
  const got = (state.build[id] ??= {});
  for (const s of remaining(state, id)) {
    const qty = Math.min(s.qty, available(state, s.item));
    if (qty <= 0) continue;
    removeAvailable(state, s.item, qty);
    got[s.item] = (got[s.item] ?? 0) + qty;
    given.push({ item: s.item, qty });
  }
  if (remaining(state, id).length > 0) return { given, finished: false };
  delete state.build[id];
  state.projects.push(id);
  const xp = PROJECTS[id].xp;
  return { given, finished: true, ...(xp ? { xp: addXp(state, xp.skill, xp.amount) } : {}) };
}

/** All at once or not at all (the dev console and the tests). */
export function completeProject(state: GameState, id: ProjectId): boolean {
  if (!plotOpen(state, id) || !remaining(state, id).every((s) => available(state, s.item) >= s.qty)) return false;
  return deliver(state, id).finished;
}
