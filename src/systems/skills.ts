import type { SkillId } from "../data/ids";
import { MAX_LEVEL, SKILLS, XP_TABLE, type Milestone } from "../data/skills";
import type { GameState } from "../state/GameState";

export function levelForXp(xp: number): number {
  let level = 1;
  for (let i = 0; i < XP_TABLE.length; i++) {
    if (xp >= (XP_TABLE[i] ?? Infinity)) level = i + 1;
  }
  return Math.min(level, MAX_LEVEL);
}

export function skillLevel(state: GameState, skill: SkillId): number {
  return levelForXp(state.skillXp[skill]);
}

/** Progress 0..1 toward the next level (1 at max level). */
export function levelProgress(xp: number): number {
  const level = levelForXp(xp);
  if (level >= MAX_LEVEL) return 1;
  const from = XP_TABLE[level - 1] ?? 0;
  const to = XP_TABLE[level] ?? from;
  return (xp - from) / (to - from);
}

export interface XpResult {
  skill: SkillId;
  oldLevel: number;
  newLevel: number;
  /** Milestones crossed by this gain, for the level-up toast. */
  unlocked: Milestone[];
}

export function addXp(state: GameState, skill: SkillId, amount: number): XpResult {
  const oldLevel = skillLevel(state, skill);
  state.skillXp[skill] += Math.max(0, amount);
  const newLevel = skillLevel(state, skill);
  const unlocked = SKILLS[skill].milestones.filter((m) => m.level > oldLevel && m.level <= newLevel);
  return { skill, oldLevel, newLevel, unlocked };
}
