import type { FlagId, ItemId, NpcId, ProjectId, StageIndex } from "./ids";

export type QuestGoal =
  | { kind: "talk"; npc: NpcId }
  | { kind: "craft"; recipe: string; qty: number }
  | { kind: "project"; project: ProjectId }
  | { kind: "stage"; stage: StageIndex }
  | { kind: "keyItem"; item: ItemId }
  | { kind: "flag"; flag: FlagId };

export interface QuestStep {
  id: string;
  title: string;
  /** One line shown under the pinned objective. */
  hint: string;
  goal: QuestGoal;
}

/** Chapter 1 main quest, in order. See GDD §12. */
export const MAIN_QUEST: readonly QuestStep[] = [
  { id: "wake", title: "Wake the Keeper", hint: "Talk to Maren by the lighthouse door.", goal: { kind: "talk", npc: "maren" } },
  { id: "feed", title: "Feed the Rest", hint: "Fish 3 Silverfin at Gullwash Shore and grill them at the hearth.", goal: { kind: "craft", recipe: "grilled_silverfin", qty: 3 } },
  { id: "forge", title: "Rekindle the Forge", hint: "Bring 8 Scrap and 6 Timber to the forge.", goal: { kind: "project", project: "forge" } },
  { id: "dock", title: "Mend the Dock", hint: "Tib needs 12 Timber and 4 Kelp for rope.", goal: { kind: "project", project: "dock" } },
  { id: "lamp", title: "Restore the Lamp", hint: "Repair the lamp housing: 10 Scrap, 6 Sea Glass, 6 Timber.", goal: { kind: "stage", stage: 1 } },
  { id: "lens", title: "The Drowned Lens", hint: "Recover the lens from the Meridian's chart room.", goal: { kind: "keyItem", item: "drowned_lens" } },
  { id: "focus", title: "Focus the Light", hint: "Seat the lens: 8 Brass, 5 Tidestone.", goal: { kind: "stage", stage: 2 } },
  { id: "relight", title: "Relight Saltmere", hint: "Defeat what guards Saltmere Beacon and carry the Ember to its lamp.", goal: { kind: "stage", stage: 3 } },
];
