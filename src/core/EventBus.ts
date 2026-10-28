import type * as THREE from "three";
import type { EnemyId, ItemId, ItemStack, LocationId, SkillId, StageIndex } from "../data/ids";
import type { TidePhase } from "../systems/tide";

/** Every event in the game. Add here and the compiler checks emitters and listeners. */
export interface GameEvents {
  "tide:warning": { turn: "rising" | "falling"; secondsLeft: number };
  "tide:turnStarted": { phase: TidePhase };
  "tide:settled": { state: "low" | "high" };
  "items:gained": { stacks: ItemStack[] };
  "items:deposited": { stacks: ItemStack[] };
  "skill:xp": { skill: SkillId; amount: number };
  "skill:levelUp": { skill: SkillId; level: number; unlocked: string[] };
  "lighthouse:stage": { stage: StageIndex };
  "player:damaged": { amount: number; fromDirection: { x: number; z: number } | null };
  "player:defeated": { lost: ItemStack[] };
  "player:dash": Record<string, never>;
  "travel:arrived": { location: LocationId };
  "enemy:killed": { enemy: EnemyId; boss: boolean };
  "node:keyItem": { item: ItemId; at: THREE.Vector3 };
  "toast": { text: string; kind?: "info" | "gain" | "warn" | "milestone" };
  "save:written": Record<string, never>;
}

type Handler<T> = (payload: T) => void;

export class EventBus<E extends object = GameEvents> {
  private handlers = new Map<keyof E, Set<Handler<never>>>();

  on<K extends keyof E>(type: K, fn: Handler<E[K]>): () => void {
    let set = this.handlers.get(type);
    if (!set) {
      set = new Set();
      this.handlers.set(type, set);
    }
    set.add(fn as Handler<never>);
    return () => set.delete(fn as Handler<never>);
  }

  emit<K extends keyof E>(type: K, payload: E[K]): void {
    const set = this.handlers.get(type);
    if (!set) return;
    for (const fn of set) (fn as Handler<E[K]>)(payload);
  }
}
