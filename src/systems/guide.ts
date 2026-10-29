import { ENEMIES } from "../data/enemies";
import type { ItemId, ItemStack, LocationId } from "../data/ids";
import { GEAR } from "../data/items";
import { LOCATIONS } from "../data/locations";
import { NODES } from "../data/nodes";
import type { GameState } from "../state/GameState";
import { available } from "./inventory";
import { canTravelOffshore, revealedLocations } from "./progression";
import { stepMaterials } from "./quests";
import { skillLevel } from "./skills";

// Answers "where do I get this?" for the pinned objective: the places you can
// reach now whose nodes (that your skills and gear can work) or enemies give it.

/** Places that give `item` right now, in chart order (nearest first). */
export function sourcesOf(state: GameState, item: ItemId): LocationId[] {
  return revealedLocations(state).filter((l) => {
    if (l !== "shore" && l !== "home" && !canTravelOffshore(state)) return false;
    const loc = LOCATIONS[l];
    const fromNodes = loc.nodes.some(({ node }) => {
      const d = NODES[node];
      if (!d.yields.some((y) => y.item === item && y.max > 0)) return false;
      if (d.skill && skillLevel(state, d.skill) < d.level) return false;
      if (d.requiresGear && !state.gear.some((g) => g === d.requiresGear || (GEAR[g].slot === GEAR[d.requiresGear!].slot && GEAR[g].tier > GEAR[d.requiresGear!].tier))) return false;
      return true;
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
