import { ENEMIES } from "../data/enemies";
import { FLOTSAM_IDS, type ItemId, type ItemStack, type LocationId } from "../data/ids";
import { LOCATIONS } from "../data/locations";
import { NODES } from "../data/nodes";
import { FLOTSAM, SALVAGE } from "../data/salvage";
import type { GameState } from "../state/GameState";
import { available } from "./inventory";
import { canTravelOffshore, hasGear, revealedLocations } from "./progression";
import { stepMaterials } from "./quests";
import { flotsamShare } from "./salvage";
import { skillLevel } from "./skills";

// Answers "where do I get this?" for the pinned objective: the places you can
// reach now whose drift, nodes (that your skills and gear can work) or enemies
// give it.

/** Whether the cove's drift brings `item` in often enough to wait for. */
export function driftGives(item: ItemId): boolean {
  return FLOTSAM_IDS.some((f) => flotsamShare(f) >= SALVAGE.reliableShare && FLOTSAM[f].yields.some((y) => y.item === item && y.max > 0));
}

/** Places that give `item` right now, in chart order (nearest first). */
export function sourcesOf(state: GameState, item: ItemId): LocationId[] {
  return revealedLocations(state).filter((l) => {
    if (l !== "home" && !canTravelOffshore(state)) return false;
    if (l === "home" && driftGives(item)) return true;
    const loc = LOCATIONS[l];
    const fromNodes = loc.nodes.some(({ node, needsProject }) => {
      const d = NODES[node];
      if (!d.yields.some((y) => y.item === item && y.max > 0)) return false;
      if (needsProject && !state.projects.includes(needsProject)) return false;
      if (d.kind !== "wreckage" && d.skill && skillLevel(state, d.skill) < d.level) return false;
      return !d.requiresGear || hasGear(state.gear, d.requiresGear);
    });
    return fromNodes || loc.enemies.some(({ enemy }) => ENEMIES[enemy].drops.some((y) => y.item === item && y.max > 0));
  });
}

/** What the current step still needs, beyond what's in the satchel and the chest. */
export function stillNeeded(state: GameState): ItemStack[] {
  return stepMaterials(state)
    .map((s) => ({ item: s.item, qty: s.qty - available(state, s.item) }))
    .filter((s) => s.qty > 0);
}
