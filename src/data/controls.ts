// The player's actions and their keys: `KeyboardEvent.code` values, plus
// "Mouse0"/"Mouse2" for buttons. The first key of each action is the one the
// journal lets you rebind; the others are fixed alternates (arrow keys).

export const ACTIONS = [
  "forward",
  "back",
  "left",
  "right",
  "jump",
  "dash",
  "fire",
  "interact",
  "eat",
  "cycleFood",
  "flare",
  "journal",
  "pause",
  "debugTide",
] as const;
export type Action = (typeof ACTIONS)[number];

export const DEFAULT_BINDINGS: Record<Action, readonly string[]> = {
  forward: ["KeyW", "ArrowUp"],
  back: ["KeyS", "ArrowDown"],
  left: ["KeyA", "ArrowLeft"],
  right: ["KeyD", "ArrowRight"],
  jump: ["Space"],
  dash: ["ShiftLeft", "ShiftRight"],
  fire: ["Mouse0"],
  interact: ["KeyE"],
  eat: ["KeyF"],
  cycleFood: ["KeyZ"],
  flare: ["KeyQ"],
  journal: ["Tab"],
  pause: ["Escape"],
  debugTide: ["KeyT"],
};

/** What the journal lists, in order. Esc always pauses and cancels, so it isn't here. */
export const REBINDABLE: readonly { action: Action; label: string }[] = [
  { action: "forward", label: "Move forward" },
  { action: "back", label: "Move back" },
  { action: "left", label: "Strafe left" },
  { action: "right", label: "Strafe right" },
  { action: "jump", label: "Jump" },
  { action: "dash", label: "Dash" },
  { action: "fire", label: "Fire" },
  { action: "interact", label: "Interact, gather, reel" },
  { action: "flare", label: "Lantern Flare" },
  { action: "eat", label: "Eat" },
  { action: "cycleFood", label: "Next food" },
  { action: "journal", label: "Journal" },
];

/** Keys that can't be bound to anything (Esc is pause and cancel). */
export const RESERVED_KEYS: readonly string[] = ["Escape"];

/** The player's rebinds: the new first key per action. */
export type BindingOverrides = Partial<Record<Action, string>>;

/**
 * The keys each action answers to. An alternate that another action now uses
 * as its main key is dropped, so one key never does two things.
 */
export function effectiveBindings(overrides: BindingOverrides): Record<Action, string[]> {
  const main = {} as Record<Action, string>;
  for (const a of ACTIONS) main[a] = overrides[a] ?? DEFAULT_BINDINGS[a][0]!;
  const taken = new Set(Object.values(main));
  const out = {} as Record<Action, string[]>;
  for (const a of ACTIONS) out[a] = [main[a], ...DEFAULT_BINDINGS[a].slice(1).filter((k) => !taken.has(k))];
  return out;
}

/**
 * Binds `code` as the main key of `action`. If another action had it as its
 * main key, the two swap, so nothing is left unbound.
 */
export function rebind(overrides: BindingOverrides, action: Action, code: string): BindingOverrides {
  if (RESERVED_KEYS.includes(code)) return overrides;
  const current = effectiveBindings(overrides);
  const next: BindingOverrides = { ...overrides, [action]: code };
  for (const other of ACTIONS) {
    if (other !== action && current[other][0] === code) next[other] = current[action][0];
  }
  // Drop overrides that are back to the default, so a reset save stays tidy.
  for (const a of ACTIONS) if (next[a] === DEFAULT_BINDINGS[a][0]) delete next[a];
  return next;
}

const NAMED: Record<string, string> = {
  Space: "Space",
  ShiftLeft: "Shift",
  ShiftRight: "R Shift",
  ControlLeft: "Ctrl",
  ControlRight: "R Ctrl",
  AltLeft: "Alt",
  AltRight: "R Alt",
  Tab: "Tab",
  Escape: "Esc",
  Enter: "Enter",
  Backspace: "Backspace",
  CapsLock: "Caps",
  ArrowUp: "↑",
  ArrowDown: "↓",
  ArrowLeft: "←",
  ArrowRight: "→",
  Backquote: "`",
  Minus: "-",
  Equal: "=",
  BracketLeft: "[",
  BracketRight: "]",
  Backslash: "\\",
  Semicolon: ";",
  Quote: "'",
  Comma: ",",
  Period: ".",
  Slash: "/",
  Mouse0: "LMB",
  Mouse1: "MMB",
  Mouse2: "RMB",
  Mouse3: "Mouse 4",
  Mouse4: "Mouse 5",
};

/** Short label for a key code: "KeyQ" → "Q", "ShiftLeft" → "Shift", "Mouse0" → "LMB". */
export function keyName(code: string): string {
  if (NAMED[code]) return NAMED[code];
  const m = /^(?:Key|Digit|Numpad)(.+)$/.exec(code);
  return m ? m[1]! : code;
}
