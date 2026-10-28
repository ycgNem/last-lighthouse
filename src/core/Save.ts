import { createNewGame, SAVE_VERSION, type GameState } from "../state/GameState";

const KEY = "last-lighthouse.save";

/** Minimal storage interface so tests can pass an in-memory map. */
export interface KeyValueStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

type Migration = (raw: Record<string, unknown>) => Record<string, unknown>;

/** MIGRATIONS[n] upgrades a version-n save to version n+1. */
const MIGRATIONS: Record<number, Migration> = {};

export function serialize(state: GameState): string {
  return JSON.stringify(state);
}

export function deserialize(json: string): GameState {
  let raw = JSON.parse(json) as Record<string, unknown>;
  let version = typeof raw.version === "number" ? raw.version : 0;
  if (version > SAVE_VERSION) throw new Error(`Save is from a newer version (${version})`);
  while (version < SAVE_VERSION) {
    const m = MIGRATIONS[version];
    if (!m) throw new Error(`No migration from save version ${version}`);
    raw = m(raw);
    version++;
  }
  // Fill any fields added since the save was written with new-game defaults.
  return { ...createNewGame(), ...raw, version: SAVE_VERSION } as GameState;
}

export class SaveSystem {
  constructor(private readonly store: KeyValueStore) {}

  load(): GameState | null {
    const json = this.store.getItem(KEY);
    if (!json) return null;
    try {
      return deserialize(json);
    } catch (err) {
      console.error("Save could not be loaded; keeping it untouched.", err);
      return null;
    }
  }

  write(state: GameState): void {
    this.store.setItem(KEY, serialize(state));
  }

  /** Callers must confirm with the player twice before calling this. */
  reset(): void {
    this.store.removeItem(KEY);
  }
}
