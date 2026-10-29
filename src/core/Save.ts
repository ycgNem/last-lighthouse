import { createNewGame, SAVE_VERSION, type GameState } from "../state/GameState";
import { advanceQuest } from "../systems/quests";

const KEY = "last-lighthouse.save";

/** Minimal storage interface so tests can pass an in-memory map. */
export interface KeyValueStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

type Migration = (raw: Record<string, unknown>) => Record<string, unknown>;

/** MIGRATIONS[n] upgrades a version-n save to version n+1. */
const MIGRATIONS: Record<number, Migration> = {
  // The Rest becomes the base: Gullwash Shore is gone (its materials drift into
  // the cove now), the dock is the jetty, and everyone carries a salvage hook.
  1: (raw) => {
    const out: Record<string, unknown> = { ...raw, version: 2 };
    if (raw.location === "shore") out.location = "home";
    const stage = typeof raw.stage === "number" ? raw.stage : 0;
    const projects = (Array.isArray(raw.projects) ? (raw.projects as string[]) : []).map((p) => (p === "dock" ? "jetty" : p));
    // Odile cooked at the hearth from the start before; a save past the lamp keeps her.
    if (stage >= 1 && !projects.includes("cottage_1")) projects.push("cottage_1");
    out.projects = projects;
    const gear = Array.isArray(raw.gear) ? (raw.gear as string[]) : [];
    if (!gear.includes("hook_rope")) out.gear = [...gear, "hook_rope"];
    // The steps changed: start from the first and walk past what's done (at
    // load, below), counting the old foraging as the hook's first lesson.
    const quest = (typeof raw.quest === "object" && raw.quest !== null ? raw.quest : {}) as Record<string, unknown>;
    out.salvaged = typeof quest.step === "number" && quest.step > 0 ? 6 : 0;
    out.quest = { ...quest, step: 0 };
    return out;
  },
};

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
  // Fill any fields added since the save was written with new-game defaults
  // (settings one level down too, so a new option doesn't wipe the old ones).
  const fresh = createNewGame();
  const state = { ...fresh, ...raw, version: SAVE_VERSION } as GameState;
  const settings = typeof raw.settings === "object" && raw.settings !== null ? (raw.settings as Partial<GameState["settings"]>) : {};
  state.settings = { ...fresh.settings, ...settings, bindings: { ...(settings.bindings ?? {}) } };
  const cove = typeof raw.cove === "object" && raw.cove !== null ? (raw.cove as Partial<GameState["cove"]>) : {};
  state.cove = { ...fresh.cove, ...cove };
  // Quietly past any step already done (a migrated save starts from the first).
  advanceQuest(state);
  return state;
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
