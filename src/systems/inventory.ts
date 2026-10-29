import { BALANCE } from "../data/balance";
import type { ItemId, ItemStack } from "../data/ids";
import { GEAR, ITEMS } from "../data/items";
import type { GameState } from "../state/GameState";

export function satchelCapacity(state: GameState): number {
  let slots: number = BALANCE.inventory.baseSlots;
  for (const g of state.gear) slots += GEAR[g].stats.satchelSlots ?? 0;
  return slots;
}

export function carried(state: GameState, item: ItemId): number {
  if (ITEMS[item].category === "key") return state.keyItems.includes(item) ? 1 : 0;
  let n = 0;
  for (const s of state.satchel) if (s?.item === item) n += s.qty;
  return n;
}

export function stored(state: GameState, item: ItemId): number {
  return state.storage[item] ?? 0;
}

/** What crafting and upgrades at home can draw on: satchel + storage. */
export function available(state: GameState, item: ItemId): number {
  return carried(state, item) + stored(state, item);
}

/** Adds to the satchel. Key items go to the key pouch. Returns how many fit. */
export function addItem(state: GameState, item: ItemId, qty: number): number {
  const def = ITEMS[item];
  if (def.category === "key") {
    if (!state.keyItems.includes(item)) state.keyItems.push(item);
    return 1;
  }
  let left = qty;
  for (const s of state.satchel) {
    if (left === 0) break;
    if (s && s.item === item && s.qty < def.stack) {
      const take = Math.min(def.stack - s.qty, left);
      s.qty += take;
      left -= take;
    }
  }
  const cap = satchelCapacity(state);
  while (left > 0) {
    const empty = state.satchel.indexOf(null);
    const slot = empty >= 0 ? empty : state.satchel.length < cap ? state.satchel.length : -1;
    if (slot < 0) break;
    const take = Math.min(def.stack, left);
    state.satchel[slot] = { item, qty: take };
    left -= take;
  }
  return qty - left;
}

/** Removes from satchel first, then storage. Caller checks availability first. */
export function removeAvailable(state: GameState, item: ItemId, qty: number): void {
  if (ITEMS[item].category === "key") {
    state.keyItems = state.keyItems.filter((k) => k !== item);
    return;
  }
  let left = qty;
  for (let i = state.satchel.length - 1; i >= 0 && left > 0; i--) {
    const s = state.satchel[i];
    if (!s || s.item !== item) continue;
    const take = Math.min(s.qty, left);
    s.qty -= take;
    left -= take;
    if (s.qty === 0) state.satchel[i] = null;
  }
  if (left > 0) {
    const have = stored(state, item);
    state.storage[item] = Math.max(0, have - left);
  }
}

/** Whether all of these would fit in the satchel as it is. */
export function fitsAll(state: GameState, stacks: readonly ItemStack[]): boolean {
  const trial: GameState = { ...state, satchel: state.satchel.map((s) => s && { ...s }), keyItems: [...state.keyItems] };
  return stacks.every((s) => addItem(trial, s.item, s.qty) === s.qty);
}

export function hasAll(state: GameState, stacks: readonly ItemStack[]): boolean {
  return stacks.every((s) => available(state, s.item) >= s.qty);
}

export function removeAll(state: GameState, stacks: readonly ItemStack[]): void {
  for (const s of stacks) removeAvailable(state, s.item, s.qty);
}

/** Moves every non-food satchel stack into storage. Food stays packed for the next trip. */
export function depositAll(state: GameState): ItemStack[] {
  const moved: ItemStack[] = [];
  state.satchel.forEach((s, i) => {
    if (!s || ITEMS[s.item].category === "food") return;
    state.storage[s.item] = stored(state, s.item) + s.qty;
    moved.push({ ...s });
    state.satchel[i] = null;
  });
  return moved;
}

/**
 * Defeat: lose a fraction of each unbanked stack (rounded down), always keeping
 * at least one. Key items, gear and storage are never touched.
 */
export function applyDeathLoss(state: GameState): ItemStack[] {
  const lost: ItemStack[] = [];
  for (const s of state.satchel) {
    if (!s) continue;
    const lose = Math.min(Math.floor(s.qty * BALANCE.inventory.deathLoss), s.qty - 1);
    if (lose <= 0) continue;
    s.qty -= lose;
    lost.push({ item: s.item, qty: lose });
  }
  return lost;
}
