import { clamp } from "./math";

export type Action =
  | "forward"
  | "back"
  | "left"
  | "right"
  | "jump"
  | "dash"
  | "fire"
  | "interact"
  | "eat"
  | "cycleFood"
  | "flare"
  | "journal"
  | "pause"
  | "debugTide";

/** `KeyboardEvent.code` values, plus "Mouse0"/"Mouse2" for buttons. */
export const DEFAULT_BINDINGS: Record<Action, string[]> = {
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

/**
 * "captured": pointer lock, the normal FPS mouse.
 * "free": fallback for browsers that refuse pointer lock (embedded previews).
 * The cursor stays visible, moving it looks around, and holding it near the
 * left or right edge keeps turning.
 */
export type LookMode = "captured" | "free";

/** Fraction of the window width on each side that turns the view in free look. */
const EDGE_ZONE = 0.1;
/** Per-event cap in free look, so re-entering the window can't snap the view. */
const MAX_FREE_DELTA = 120;

export class Input {
  private down = new Set<string>();
  private pressedThisStep = new Set<string>();
  private mouseDX = 0;
  private mouseDY = 0;
  private cursorX = 0;
  private cursorInside = false;
  private skipNextMove = true;
  /** Set by the game while playing. Mouse look and clicks are ignored otherwise. */
  active = false;
  lookMode: LookMode = "captured";
  bindings: Record<Action, string[]> = structuredClone(DEFAULT_BINDINGS);

  constructor(private readonly target: HTMLElement) {
    window.addEventListener("keydown", (e) => {
      if (e.code === "Tab") e.preventDefault();
      if (!e.repeat) this.press(e.code);
    });
    window.addEventListener("keyup", (e) => this.down.delete(e.code));
    window.addEventListener("mousedown", (e) => {
      if (this.active) this.press(`Mouse${e.button}`);
    });
    window.addEventListener("mouseup", (e) => this.down.delete(`Mouse${e.button}`));
    window.addEventListener("mousemove", (e) => this.onMouseMove(e));
    const page = document.documentElement;
    page.addEventListener("mouseleave", () => (this.cursorInside = false));
    page.addEventListener("mouseenter", () => {
      this.cursorInside = true;
      this.skipNextMove = true;
    });
    window.addEventListener("blur", () => this.down.clear());
  }

  get locked(): boolean {
    return document.pointerLockElement === this.target;
  }

  /**
   * Asks for pointer lock. Resolves false instead of throwing when the browser
   * refuses: embedded previews block it outright, and Chrome refuses for about
   * a second after the player presses Esc. Call it from a click handler.
   */
  requestLock(): Promise<boolean> {
    if (this.locked) return Promise.resolve(true);
    return new Promise((resolve) => {
      let settled = false;
      const done = (ok: boolean) => {
        if (settled) return;
        settled = true;
        document.removeEventListener("pointerlockchange", onChange);
        document.removeEventListener("pointerlockerror", onError);
        clearTimeout(timer);
        resolve(ok);
      };
      const onChange = () => {
        if (this.locked) done(true);
      };
      const onError = () => done(false);
      const timer = setTimeout(() => done(this.locked), 1500);
      document.addEventListener("pointerlockchange", onChange);
      document.addEventListener("pointerlockerror", onError);
      try {
        // Modern browsers return a promise; older ones report failure via pointerlockerror.
        const request: unknown = this.target.requestPointerLock();
        if (request instanceof Promise) request.catch(() => done(false));
      } catch {
        done(false);
      }
    });
  }

  private onMouseMove(e: MouseEvent): void {
    this.cursorX = e.clientX;
    this.cursorInside = true;
    if (!this.active) return;
    if (this.locked) {
      this.mouseDX += e.movementX;
      this.mouseDY += e.movementY;
    } else if (this.lookMode === "free") {
      if (this.skipNextMove) {
        this.skipNextMove = false;
        return;
      }
      this.mouseDX += clamp(e.movementX, -MAX_FREE_DELTA, MAX_FREE_DELTA);
      this.mouseDY += clamp(e.movementY, -MAX_FREE_DELTA, MAX_FREE_DELTA);
    }
  }

  private press(code: string): void {
    this.down.add(code);
    this.pressedThisStep.add(code);
  }

  held(a: Action): boolean {
    return this.bindings[a].some((c) => this.down.has(c));
  }

  /** True once per physical press, for the fixed step that consumes it. */
  pressed(a: Action): boolean {
    return this.bindings[a].some((c) => this.pressedThisStep.has(c));
  }

  /** Mouse movement since last call, in pixels. */
  consumeMouse(): { dx: number; dy: number } {
    const out = { dx: this.mouseDX, dy: this.mouseDY };
    this.mouseDX = 0;
    this.mouseDY = 0;
    return out;
  }

  /** Free look only: -1..1 for how deep the cursor sits in the left/right edge zone. */
  edgeTurn(): number {
    if (!this.active || this.lookMode !== "free" || this.locked || !this.cursorInside) return 0;
    const x = this.cursorX / window.innerWidth;
    if (x < EDGE_ZONE) return -(1 - x / EDGE_ZONE);
    if (x > 1 - EDGE_ZONE) return (x - (1 - EDGE_ZONE)) / EDGE_ZONE;
    return 0;
  }

  /** Call at the end of each fixed step. */
  endStep(): void {
    this.pressedThisStep.clear();
  }
}
