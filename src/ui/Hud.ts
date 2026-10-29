import "./hud.css";
import type { Action } from "../data/controls";
import type { ItemStack } from "../data/ids";
import { ITEMS } from "../data/items";
import type { TideReading } from "../systems/tide";

export interface CompassMarker {
  /** World yaw of the marker relative to north (radians, same convention as the player yaw). */
  yaw: number;
  label: string;
  dist?: number;
  kind: "landing" | "home" | "objective";
}

export interface HudView {
  tide: TideReading;
  objective: { title: string; hint: string } | null;
  /** What the step needs; `where` names a place to find what's still missing. */
  checklist: (ItemStack & { have: number; where?: string })[];
  hp: number;
  maxHp: number;
  dashCharges: number;
  dashMax: number;
  dashRecharge: number;
  prompt: string | null;
  promptBlocked: boolean;
  locationName: string;
  safe: boolean;
  food: { name: string; count: number } | null;
  satchel: { used: number; cap: number };
  haul: number | null;
  gather: number | null;
  compass: { yaw: number; markers: CompassMarker[] } | null;
  boss: { name: string; frac: number; exposed: boolean } | null;
  threats: { angle: number; level: number }[];
  /** The Lantern Flare's charge: 1 = ready. */
  flare: number;
  /** 0..1 how deep in a Gloom pocket you stand. */
  gloom: number;
  /** 0..1 how much you're in the water (chin-deep when swimming). */
  swim: number;
}

/** What the HUD calls each key (the player can rebind them). */
export type KeyLabels = Record<Action, string>;

const el = <K extends keyof HTMLElementTagNameMap>(tag: K, cls: string, parent: HTMLElement, html = ""): HTMLElementTagNameMap[K] => {
  const e = document.createElement(tag);
  e.className = cls;
  e.innerHTML = html;
  parent.appendChild(e);
  return e;
};

const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

const PHASE_LABEL = { low: "Low tide", rising: "Tide rising", high: "High tide", falling: "Tide falling" } as const;

export class Hud {
  private readonly overlay: HTMLDivElement;
  private readonly overlayGo: HTMLParagraphElement;
  private readonly overlayNote: HTMLParagraphElement;
  private readonly objTitle: HTMLDivElement;
  private readonly objHint: HTMLDivElement;
  private readonly objList: HTMLUListElement;
  private readonly tideBox: HTMLDivElement;
  private readonly tideLabel: HTMLDivElement;
  private readonly tideTime: HTMLDivElement;
  private readonly tideFill: HTMLDivElement;
  private readonly bannerEl: HTMLDivElement;
  private readonly promptEl: HTMLDivElement;
  private readonly toasts: HTMLDivElement;
  private readonly hpFill: HTMLDivElement;
  private readonly hpText: HTMLDivElement;
  private readonly dash: HTMLDivElement;
  private readonly place: HTMLDivElement;
  private readonly foodEl: HTMLDivElement;
  private readonly bagEl: HTMLDivElement;
  private readonly dlg: HTMLDivElement;
  private readonly dlgName: HTMLDivElement;
  private readonly dlgText: HTMLDivElement;
  private readonly crosshair: HTMLDivElement;
  private readonly hitEl: HTMLDivElement;
  private readonly ring: SVGCircleElement;
  private readonly ringWrap: HTMLDivElement;
  private readonly pips: HTMLDivElement;
  private readonly hurtArc: HTMLDivElement;
  private readonly vignette: HTMLDivElement;
  private readonly bossEl: HTMLDivElement;
  private readonly bossName: HTMLDivElement;
  private readonly bossFill: HTMLDivElement;
  private readonly compass: HTMLDivElement;
  private readonly compassTrack: HTMLDivElement;
  private readonly fadeEl: HTMLDivElement;
  private readonly cardTitle: HTMLDivElement;
  private readonly cardSub: HTMLDivElement;
  private readonly storyEl: HTMLDivElement;
  private readonly flareEl: HTMLDivElement;
  private readonly gloomVeil: HTMLDivElement;
  private readonly swimVeil: HTMLDivElement;
  private readonly captionsEl: HTMLDivElement;
  private readonly dlgMore: HTMLDivElement;
  private readonly controls: HTMLDivElement;
  private keys: KeyLabels | null = null;
  private flareWas = 1;
  private dlgLines: string[] = [];
  private bannerTimer = 0;
  private hitTimer = 0;
  private hurtTimer = 0;
  private lastPrompt = "";

  constructor(root: HTMLElement) {
    root.classList.add("hud");

    this.swimVeil = el("div", "swim-veil", root);
    this.gloomVeil = el("div", "gloom-veil", root);
    this.vignette = el("div", "vignette", root);
    this.hurtArc = el("div", "hurt-arc", root);

    const obj = el("div", "objective", root);
    el("div", "eyebrow", obj, "Keeper's task");
    this.objTitle = el("div", "obj-title", obj);
    this.objHint = el("div", "obj-hint", obj);
    this.objList = el("ul", "obj-list", obj);

    this.tideBox = el("div", "tide", root);
    this.tideLabel = el("div", "tide-label", this.tideBox);
    this.tideTime = el("div", "tide-time", this.tideBox);
    const gauge = el("div", "tide-gauge", this.tideBox);
    this.tideFill = el("div", "tide-fill", gauge);
    this.place = el("div", "place", root);

    this.compass = el("div", "compass", root);
    this.compassTrack = el("div", "compass-track", this.compass);

    this.bossEl = el("div", "boss hidden", root);
    this.bossName = el("div", "boss-name", this.bossEl);
    const bar = el("div", "boss-bar", this.bossEl);
    this.bossFill = el("div", "boss-fill", bar);

    this.bannerEl = el("div", "banner", root);
    this.crosshair = el("div", "crosshair", root);
    this.hitEl = el("div", "hitmark", root);
    this.ringWrap = el("div", "gather-ring hidden", root);
    this.ringWrap.innerHTML = `<svg viewBox="0 0 48 48"><circle cx="24" cy="24" r="20" class="track"/><circle cx="24" cy="24" r="20" class="fill"/></svg>`;
    this.ring = this.ringWrap.querySelector<SVGCircleElement>("circle.fill")!;
    this.pips = el("div", "pips", root);
    this.promptEl = el("div", "prompt", root);
    this.toasts = el("div", "toasts", root);

    const vitals = el("div", "vitals", root);
    const hp = el("div", "hp", vitals);
    this.hpFill = el("div", "hp-fill", hp);
    this.hpText = el("div", "hp-text", hp);
    this.dash = el("div", "dash", vitals);
    this.flareEl = el("div", "flare-chip", vitals);
    this.foodEl = el("div", "food", root);
    this.bagEl = el("div", "bag", root);

    this.dlg = el("div", "dialogue", root);
    this.dlgName = el("div", "dlg-name", this.dlg);
    this.dlgText = el("div", "dlg-text", this.dlg);
    this.dlgMore = el("div", "dlg-more", this.dlg, "<b>E</b> continue");
    this.captionsEl = el("div", "captions", root);

    this.fadeEl = el("div", "fade", root);
    this.cardTitle = el("div", "card-title", this.fadeEl);
    this.cardSub = el("div", "card-sub", this.fadeEl);

    this.storyEl = el("div", "story hidden", root);

    this.overlay = el("div", "overlay", root);
    this.overlay.innerHTML = `
      <div class="card">
        <h1>The Last Lighthouse</h1>
        <p class="sub">The sea took the world. The last lights hold it back, and this one is failing.</p>
        <div class="controls"></div>
        <p class="go">Loading…</p>
        <p class="note hidden"></p>
      </div>`;
    this.overlayGo = this.overlay.querySelector<HTMLParagraphElement>(".go")!;
    this.overlayNote = this.overlay.querySelector<HTMLParagraphElement>(".note")!;
    this.controls = this.overlay.querySelector<HTMLDivElement>(".controls")!;
  }

  /** Key names for every hint on screen; call again after a rebind. */
  setKeys(k: KeyLabels): void {
    this.keys = k;
    this.lastPrompt = "";
    this.dlgMore.innerHTML = `<b>${esc(k.interact)}</b> continue`;
    const wasd = [k.forward, k.left, k.back, k.right];
    const move = wasd.every((x) => x.length === 1) ? wasd.join("") : wasd.join(" ");
    const rows: [string, string][] = [
      [move, "move"],
      ["Mouse", "look"],
      [k.jump, "jump"],
      [k.dash, "dash"],
      [k.interact, "interact"],
      [k.fire, "fire"],
      [k.flare, "lantern flare"],
      [k.eat, "eat"],
      [k.cycleFood, "next food"],
      [k.journal, "journal"],
      [k.pause, "pause"],
    ];
    this.controls.innerHTML = rows.map(([key, what]) => `<span><b>${esc(key)}</b> ${what}</span>`).join("");
  }

  /** Stops the HUD's own animations (pulses, slides) for the reduced-motion setting. */
  setReducedMotion(on: boolean): void {
    this.overlay.parentElement?.classList.toggle("reduced-motion", on);
  }

  onOverlayClick(fn: () => void): void {
    this.overlay.addEventListener("click", fn);
  }

  /** Title card before the first start, pause card after; `prompt` overrides the call to action. */
  setOverlay(mode: "title" | "paused" | "hidden", prompt?: string): void {
    this.overlay.classList.toggle("hidden", mode === "hidden");
    this.overlayGo.textContent = prompt ?? (mode === "paused" ? "Paused — click to resume" : "Click to begin");
  }

  /** A standing explanation under the controls, e.g. why the mouse isn't captured. */
  setOverlayNote(text: string | null): void {
    this.overlayNote.textContent = text ?? "";
    this.overlayNote.classList.toggle("hidden", !text);
  }

  render(v: HudView, dt: number): void {
    text(this.objTitle, v.objective?.title ?? "Chapter complete");
    text(this.objHint, v.objective?.hint ?? "Saltmere burns again. The coast is yours to explore.");
    html(
      this.objList,
      v.checklist
        .map((c) => {
          const met = c.have >= c.qty;
          return `<li class="${met ? "met" : ""}">${ITEMS[c.item].name}${!met && c.where ? `<small>${esc(c.where)}</small>` : ""}<span>${Math.min(c.have, c.qty)}/${c.qty}</span></li>`;
        })
        .join(""),
    );

    const t = v.tide;
    text(this.tideLabel, PHASE_LABEL[t.phase]);
    const verb = t.phase === "rising" || t.phase === "falling" ? "Settles in" : t.nextTurn === "rising" ? "Rises in" : "Falls in";
    text(this.tideTime, `${verb} ${fmt(t.phaseTimeLeft)}`);
    css(this.tideFill, "height", `${(8 + t.level * 84).toFixed(1)}%`);
    this.tideBox.classList.toggle("warn", t.warning);

    text(this.place, v.locationName + (v.safe ? " · safe" : ""));
    this.place.classList.toggle("safe", v.safe);

    const prompt = v.prompt ? (v.promptBlocked ? esc(v.prompt) : `<b>${esc(this.keys?.interact ?? "E")}</b> ${esc(v.prompt)}`) : "";
    if (prompt !== this.lastPrompt) {
      this.promptEl.innerHTML = prompt;
      this.lastPrompt = prompt;
    }
    this.promptEl.classList.toggle("hidden", !v.prompt || this.dlgLines.length > 0);
    this.promptEl.classList.toggle("blocked", v.promptBlocked);

    const frac = Math.max(0, v.hp / v.maxHp);
    css(this.hpFill, "width", `${(frac * 100).toFixed(1)}%`);
    text(this.hpText, `${Math.ceil(Math.max(0, v.hp))} / ${v.maxHp}`);
    html(
      this.dash,
      Array.from({ length: v.dashMax }, (_, i) =>
        i < v.dashCharges ? `<i class="on"></i>` : i === v.dashCharges ? `<i style="--k:${v.dashRecharge.toFixed(2)}"></i>` : "<i></i>",
      ).join(""),
    );
    css(this.vignette, "opacity", Math.max(frac < 0.3 ? (0.3 - frac) * 2 : 0, this.hurtTimer * 1.6).toFixed(3));
    css(this.gloomVeil, "opacity", v.gloom.toFixed(3));
    css(this.swimVeil, "opacity", v.swim.toFixed(3));

    const ready = v.flare >= 1;
    html(this.flareEl, `<b>${esc(this.keys?.flare ?? "Q")}</b><i style="--k:${Math.min(1, v.flare).toFixed(2)}"></i>`);
    this.flareEl.classList.toggle("ready", ready);
    if (ready && this.flareWas < 1) {
      // Restart the "it's back" flash.
      this.flareEl.classList.remove("ping");
      void this.flareEl.offsetWidth;
      this.flareEl.classList.add("ping");
    }
    this.flareWas = v.flare;

    html(this.foodEl, v.food ? `<b>${esc(this.keys?.eat ?? "F")}</b> ${v.food.name} <span>×${v.food.count}</span>` : `<span class="dim">No food packed</span>`);
    html(this.bagEl, `Satchel ${v.satchel.used}/${v.satchel.cap}${v.haul !== null ? ` · <span>Haul ${v.haul}</span>` : ""}`);
    this.bagEl.classList.toggle("full", v.satchel.used >= v.satchel.cap);

    if (v.gather !== null) {
      this.ringWrap.classList.remove("hidden");
      css(this.ring, "strokeDashoffset", (125.7 * (1 - v.gather)).toFixed(1));
    } else this.ringWrap.classList.add("hidden");

    if (v.boss) {
      this.bossEl.classList.remove("hidden");
      text(this.bossName, v.boss.exposed ? `${v.boss.name} — heart exposed!` : v.boss.name);
      css(this.bossFill, "width", `${(Math.max(0, v.boss.frac) * 100).toFixed(1)}%`);
      this.bossEl.classList.toggle("exposed", v.boss.exposed);
    } else this.bossEl.classList.add("hidden");

    html(this.pips, v.threats.map((p) => `<i style="transform: rotate(${p.angle.toFixed(3)}rad) translateY(-150px); opacity:${(0.4 + p.level * 0.6).toFixed(2)}"></i>`).join(""));

    if (v.compass) {
      this.compass.classList.remove("hidden");
      const toPx = (yaw: number) => {
        let d = v.compass!.yaw - yaw;
        d = Math.atan2(Math.sin(d), Math.cos(d));
        return d;
      };
      const items: string[] = [];
      for (const [label, yaw] of [
        ["N", 0],
        ["W", Math.PI / 2],
        ["S", Math.PI],
        ["E", -Math.PI / 2],
      ] as const) {
        const d = toPx(yaw);
        if (Math.abs(d) < 1.6) items.push(`<span class="dir" style="left:${(50 + (d / 1.6) * 50).toFixed(2)}%">${label}</span>`);
      }
      for (const m of v.compass.markers) {
        const d = toPx(m.yaw);
        const clamped = Math.max(-1.55, Math.min(1.55, d));
        items.push(`<span class="mk ${m.kind}${Math.abs(d) > 1.55 ? " edge" : ""}" style="left:${(50 + (clamped / 1.6) * 50).toFixed(2)}%">${esc(m.label)}${m.dist !== undefined ? `<em>${Math.round(m.dist)} m</em>` : ""}</span>`);
      }
      html(this.compassTrack, items.join(""));
    } else this.compass.classList.add("hidden");

    if (this.bannerTimer > 0) {
      this.bannerTimer -= dt;
      if (this.bannerTimer <= 0) this.bannerEl.classList.remove("show");
    }
    if (this.hitTimer > 0) {
      this.hitTimer -= dt;
      if (this.hitTimer <= 0) this.hitEl.className = "hitmark";
    }
    if (this.hurtTimer > 0) {
      this.hurtTimer = Math.max(0, this.hurtTimer - dt);
      this.hurtArc.style.opacity = String(Math.min(1, this.hurtTimer * 2));
    }
  }

  toast(text: string, kind: "info" | "gain" | "warn" | "milestone" = "info", seconds?: number): void {
    // Merge repeated gain toasts ("+2 Timber" then "+3 Timber" → "+5 Timber").
    if (kind === "gain") {
      const last = this.toasts.lastElementChild as HTMLDivElement | null;
      const m = /^\+(\d+) (.+)$/.exec(text);
      const lm = last && !last.classList.contains("out") ? /^\+(\d+) (.+)$/.exec(last.textContent ?? "") : null;
      if (m && lm && lm[2] === m[2] && last?.classList.contains("gain")) {
        last.textContent = `+${Number(lm[1]) + Number(m[1])} ${m[2]}`;
        return;
      }
    }
    const t = el("div", `toast ${kind}`, this.toasts);
    t.textContent = text;
    const ms = (seconds ?? (kind === "milestone" ? 4.2 : 2.6)) * 1000;
    setTimeout(() => t.classList.add("out"), ms);
    setTimeout(() => t.remove(), ms + 600);
    while (this.toasts.children.length > 6) this.toasts.firstElementChild?.remove();
  }

  /**
   * A caption for a sound, with an arrow for where it came from (null: all
   * around, or no direction). Repeats within a moment merge into "×2".
   */
  caption(text: string, side: "left" | "right" | "behind" | null): void {
    const label = side === "left" ? `◀ ${text}` : side === "right" ? `${text} ▶` : side === "behind" ? `${text} ▼` : text;
    const last = this.captionsEl.lastElementChild as HTMLDivElement | null;
    if (last && last.dataset.label === label && !last.classList.contains("out")) {
      const n = Number(last.dataset.n ?? "1") + 1;
      last.dataset.n = String(n);
      last.textContent = `${label} ×${n}`;
      clearTimeout(Number(last.dataset.timer));
      last.dataset.timer = String(this.expire(last));
      return;
    }
    const line = el("div", "caption", this.captionsEl);
    line.dataset.label = label;
    line.textContent = label;
    line.dataset.timer = String(this.expire(line));
    while (this.captionsEl.children.length > 4) this.captionsEl.firstElementChild?.remove();
  }

  private expire(line: HTMLElement): number {
    return window.setTimeout(() => {
      line.classList.add("out");
      setTimeout(() => line.remove(), 400);
    }, 2600);
  }

  banner(text: string, seconds = 4): void {
    this.bannerEl.textContent = text;
    this.bannerEl.classList.add("show");
    this.bannerTimer = seconds;
  }

  hitMarker(weak: boolean): void {
    this.hitEl.className = `hitmark show${weak ? " weak" : ""}`;
    this.hitTimer = 0.12;
  }

  /** Red arc pointing toward whatever hit you; `angle` is relative to where you face (0 = ahead). */
  damageFrom(angle: number | null): void {
    this.hurtTimer = 0.6;
    this.hurtArc.style.transform = `translate(-50%, -50%) rotate(${angle ?? 0}rad)`;
    this.hurtArc.classList.toggle("omni", angle === null);
  }

  /** Full-screen fade with an optional title card (travel, defeat). */
  fade(opacity: number, color = "#05090c", title = "", sub = ""): void {
    this.fadeEl.style.background = color;
    this.fadeEl.style.opacity = String(opacity);
    this.cardTitle.textContent = title;
    this.cardSub.textContent = sub;
  }

  /** A prologue card over a darkened screen (null hides it). */
  story(card: { title: string; text: string } | null, index = 0, total = 0): void {
    if (!card) {
      if (this.storyEl.classList.contains("hidden") || this.storyEl.classList.contains("out")) return;
      // Fade the last card away, then take it out of the way.
      this.storyEl.classList.add("out");
      window.setTimeout(() => {
        if (this.storyEl.classList.contains("out")) this.storyEl.classList.add("hidden");
      }, 900);
      return;
    }
    const roman = ["I", "II", "III", "IV", "V", "VI"][index] ?? String(index + 1);
    const go = esc(this.keys?.jump ?? "Space");
    html(
      this.storyEl,
      `<div class="story-card" data-i="${index}"><div class="story-kicker">${roman} · ${esc(card.title)}</div><p>${esc(card.text)}</p>
        <div class="story-go">Click or press <b>${go}</b> ${index + 1 < total ? "to continue" : "to begin"}</div></div>`,
    );
    this.storyEl.classList.remove("hidden", "out");
  }

  get dialogueOpen(): boolean {
    return this.dlgLines.length > 0;
  }

  showDialogue(name: string, lines: string[]): void {
    this.dlgLines = [...lines];
    this.dlgName.textContent = name;
    this.advanceDialogue(true);
  }

  /** Shows the next line; closes when out of lines. */
  advanceDialogue(first = false): void {
    if (!first) this.dlgLines.shift();
    const line = this.dlgLines[0];
    this.dlg.classList.toggle("show", line !== undefined);
    if (line !== undefined) this.dlgText.textContent = line;
  }

  closeDialogue(): void {
    this.dlgLines = [];
    this.dlg.classList.remove("show");
  }

  setCrosshair(visible: boolean): void {
    this.crosshair.classList.toggle("hidden", !visible);
  }
}

// The HUD redraws every frame. Rewriting the same text or markup still costs the
// browser a style and layout pass, so these write only what actually changed.
const written = new WeakMap<HTMLElement, string>();

function html(el: HTMLElement, value: string): void {
  if (written.get(el) === value) return;
  written.set(el, value);
  el.innerHTML = value;
}

function text(el: HTMLElement, value: string): void {
  if (written.get(el) === value) return;
  written.set(el, value);
  el.textContent = value;
}

const styled = new WeakMap<HTMLElement | SVGElement, Map<string, string>>();

function css(el: HTMLElement | SVGElement, prop: "height" | "width" | "opacity" | "strokeDashoffset", value: string): void {
  let seen = styled.get(el);
  if (!seen) styled.set(el, (seen = new Map()));
  if (seen.get(prop) === value) return;
  seen.set(prop, value);
  el.style[prop] = value;
}
