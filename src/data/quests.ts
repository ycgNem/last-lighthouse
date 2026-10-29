import type { FlagId, ItemId, NpcId, ProjectId, StageIndex } from "./ids";

export type QuestGoal =
  | { kind: "talk"; npc: NpcId }
  /** Pieces hooked out of the sea, drift or wreck. */
  | { kind: "salvage"; qty: number }
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

/** Chapter 1 main quest, in order. See GDD §12. The objective's checklist lists the materials, so hints don't. */
export const MAIN_QUEST: readonly QuestStep[] = [
  { id: "wake", title: "Wake the Keeper", hint: "Talk to Maren by the lighthouse door.", goal: { kind: "talk", npc: "maren" } },
  { id: "salvage", title: "The Sea Gives", hint: "Go down to the cove and hook what the tide brings in.", goal: { kind: "salvage", qty: 6 } },
  { id: "forge", title: "Rebuild the Forge", hint: "Hand materials in at the old forge as you get them.", goal: { kind: "project", project: "forge" } },
  { id: "jetty", title: "Rebuild the Jetty", hint: "Give Tib somewhere to tie up, and he'll bring the boat in.", goal: { kind: "project", project: "jetty" } },
  { id: "cottage", title: "Bring Them Home", hint: "Put the roof back on the Marsh place, and Odile can come home.", goal: { kind: "project", project: "cottage_1" } },
  { id: "feed", title: "Feed the Rest", hint: "Fish 3 Silverfin off the rocks and grill them at the hearth.", goal: { kind: "craft", recipe: "grilled_silverfin", qty: 3 } },
  { id: "lamp", title: "Restore the Lamp", hint: "Repair the lamp housing at the top of the lighthouse.", goal: { kind: "stage", stage: 1 } },
  { id: "lens", title: "The Drowned Lens", hint: "Take the boat to the Meridian and recover the lens from her chart room.", goal: { kind: "keyItem", item: "drowned_lens" } },
  { id: "focus", title: "Focus the Light", hint: "Seat the lens in the lamp.", goal: { kind: "stage", stage: 2 } },
  { id: "relight", title: "Relight Saltmere", hint: "Defeat what guards Saltmere Beacon and carry the Ember to its lamp.", goal: { kind: "stage", stage: 3 } },
];
