import "./menus.css";
import type { ItemId, ItemStack, LocationId, ProjectId, SkillId, StationId } from "../data/ids";
import { LOCATION_IDS, SKILL_IDS } from "../data/ids";
import { GEAR, ITEMS } from "../data/items";
import { PROJECTS, STAGES, type Requirements } from "../data/lighthouse";
import { LOCATIONS } from "../data/locations";
import { RECIPES, type RecipeDef } from "../data/recipes";
import { MAX_LEVEL, SKILLS } from "../data/skills";
import type { GameState } from "../state/GameState";
import { craftBlock, type CraftBlock } from "../systems/crafting";
import { available, satchelCapacity, stored } from "../systems/inventory";
import { canTravelOffshore, isMet, missingFor, nextStage } from "../systems/progression";
import { levelForXp, levelProgress, skillLevel } from "../systems/skills";

// Full-screen panels opened from stations at home and from the journal.
// Plain DOM; every button carries a data-act attribute handled in one place.

export interface MenuHost {
  readonly state: GameState;
  craft(recipeId: string, times: number): void;
  repair(project: ProjectId): void;
  upgradeLighthouse(): void;
  depositAll(): void;
  store(slot: number): void;
  take(item: ItemId): void;
  travel(to: LocationId): void;
  settingsChanged(): void;
  resetSave(): void;
  closeMenu(): void;
  tideLine(): string;
}

export type MenuKind =
  | { kind: "storage" }
  | { kind: "station"; station: StationId }
  | { kind: "project"; project: ProjectId }
  | { kind: "lighthouse" }
  | { kind: "chart" }
  | { kind: "journal"; tab?: "satchel" | "skills" | "lighthouse" | "settings" }
  | { kind: "summary"; title: string; sub: string; gained: ItemStack[]; lost: ItemStack[]; xp: Partial<Record<SkillId, number>>; kills: number };

const BLOCK_TEXT: Record<CraftBlock, string> = {
  station: "Repair the forge first",
  level: "Skill too low",
  gear_required: "Needs the previous tier",
  already_owned: "Owned",
  materials: "Missing materials",
  satchel_full: "Satchel full",
};

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

export class Menus {
  private readonly root: HTMLDivElement;
  private readonly panel: HTMLDivElement;
  private current: MenuKind | null = null;
  private confirmStep = 0;

  constructor(
    parent: HTMLElement,
    private readonly host: MenuHost,
    private readonly click: () => void,
  ) {
    this.root = document.createElement("div");
    this.root.className = "menu hidden";
    this.panel = document.createElement("div");
    this.panel.className = "menu-panel";
    this.root.appendChild(this.panel);
    parent.appendChild(this.root);
    this.root.addEventListener("click", (e) => this.onClick(e));
    this.root.addEventListener("input", (e) => this.onInput(e));
  }

  get isOpen(): boolean {
    return this.current !== null;
  }

  get kind(): MenuKind["kind"] | null {
    return this.current?.kind ?? null;
  }

  open(m: MenuKind): void {
    this.current = m;
    this.confirmStep = 0;
    this.root.classList.remove("hidden");
    this.render();
  }

  close(): void {
    this.current = null;
    this.root.classList.add("hidden");
  }

  refresh(): void {
    if (this.current) this.render();
  }

  private render(): void {
    const m = this.current;
    if (!m) return;
    let body = "";
    switch (m.kind) {
      case "storage":
        body = this.storage();
        break;
      case "station":
        body = this.station(m.station);
        break;
      case "project":
        body = this.project(m.project);
        break;
      case "lighthouse":
        body = this.lighthouse();
        break;
      case "chart":
        body = this.chart();
        break;
      case "journal":
        body = this.journal(m.tab ?? "satchel");
        break;
      case "summary":
        body = this.summary(m);
        break;
    }
    const closeLabel = m.kind === "summary" ? "Continue" : "Close";
    this.panel.innerHTML = `${body}<div class="menu-foot"><span class="hint"><b>Esc</b> ${closeLabel.toLowerCase()}</span><button data-act="close" class="primary">${closeLabel}</button></div>`;
  }

  // ------------------------------------------------------------ helpers

  private req(r: Requirements): string {
    const s = this.host.state;
    const rows: string[] = [];
    for (const i of r.items ?? []) {
      const have = available(s, i.item);
      rows.push(`<li class="${have >= i.qty ? "ok" : ""}">${ITEMS[i.item].name}<span>${Math.min(have, i.qty)}/${i.qty}</span></li>`);
    }
    for (const k of r.keyItems ?? []) rows.push(`<li class="${s.keyItems.includes(k) ? "ok" : ""}">${ITEMS[k].name}<span>${s.keyItems.includes(k) ? "✓" : "—"}</span></li>`);
    for (const p of r.projects ?? []) rows.push(`<li class="${s.projects.includes(p) ? "ok" : ""}">${PROJECTS[p].name}<span>${s.projects.includes(p) ? "✓" : "—"}</span></li>`);
    for (const f of r.flags ?? []) rows.push(`<li class="${s.flags.includes(f) ? "ok" : ""}">${f === "guardian_defeated" ? "Defeat the Wreck Guardian" : f}<span>${s.flags.includes(f) ? "✓" : "—"}</span></li>`);
    return `<ul class="req">${rows.join("")}</ul>`;
  }

  // ------------------------------------------------------------- panels

  private storage(): string {
    const s = this.host.state;
    const cap = satchelCapacity(s);
    const satchel = s.satchel
      .map((st, i) => (st ? `<li>${ITEMS[st.item].name}<span>×${st.qty}</span><button data-act="store" data-slot="${i}">Store</button></li>` : ""))
      .join("");
    const keys = s.keyItems.map((k) => `<li class="key">${ITEMS[k].name}<span>key item</span></li>`).join("");
    const storedRows = (Object.keys(s.storage) as ItemId[])
      .filter((k) => (s.storage[k] ?? 0) > 0)
      .sort((a, b) => ITEMS[a].category.localeCompare(ITEMS[b].category) || ITEMS[a].name.localeCompare(ITEMS[b].name))
      .map((k) => `<li>${ITEMS[k].name}<span>×${stored(s, k)}</span><button data-act="take" data-item="${k}">Take</button></li>`)
      .join("");
    return `<h2>Storage chest</h2><p class="lede">Stored things are safe. Carried things are at risk out there.</p>
      <div class="cols">
        <section><h3>Satchel <small>${s.satchel.filter(Boolean).length}/${cap} slots</small></h3>
          <button data-act="deposit" class="wide">Deposit all <small>(keeps food)</small></button>
          <ul class="rows">${satchel || `<li class="empty">Empty</li>`}${keys}</ul></section>
        <section><h3>Stored</h3><ul class="rows">${storedRows || `<li class="empty">Nothing yet</li>`}</ul></section>
      </div>`;
  }

  private station(station: StationId): string {
    const s = this.host.state;
    const skill: SkillId = station === "hearth" ? "cooking" : "smithing";
    const title = station === "hearth" ? "Hearth" : "Forge";
    const cards = RECIPES.filter((r) => r.station === station)
      .map((r) => this.recipeCard(r))
      .join("");
    return `<h2>${title} <small>${SKILLS[skill].name} ${skillLevel(s, skill)}</small></h2>
      <p class="lede">${station === "hearth" ? "Cook what you caught. Food heals; the best of it does more." : "Smelt scrap into ingots, then make something worth carrying."} Uses your satchel and the storage chest.</p>
      <div class="cards">${cards}</div>`;
  }

  private recipeCard(r: RecipeDef): string {
    const s = this.host.state;
    const block = craftBlock(s, r);
    const out = r.output.kind === "item" ? ITEMS[r.output.item] : GEAR[r.output.gear];
    const name = r.output.kind === "item" ? `${out.name}${r.output.qty > 1 ? ` ×${r.output.qty}` : ""}` : out.name;
    const food = r.output.kind === "item" ? ITEMS[r.output.item].food : undefined;
    const benefit = food ? `Heals ${food.heal}${food.buff ? (food.buff.kind === "max_hp" ? `, +${food.buff.amount} max HP for 3 min` : ", faster dash for 3 min") : ""}` : out.description;
    const inputs = r.inputs.map((i) => {
      const have = available(s, i.item);
      return `<li class="${have >= i.qty ? "ok" : ""}">${ITEMS[i.item].name}<span>${have}/${i.qty}</span></li>`;
    });
    const lvl = skillLevel(s, r.skill);
    const locked = lvl < r.level;
    const repeat = r.output.kind === "item";
    const disabled = block ? "disabled" : "";
    return `<article class="card ${locked ? "locked" : ""} ${block === "already_owned" ? "owned" : ""}">
      <header><strong>${esc(name)}</strong><span class="lvl">${SKILLS[r.skill].name} ${r.level}</span></header>
      <p>${esc(benefit)}</p>
      <ul class="req">${inputs.join("")}</ul>
      <footer>${block ? `<em>${BLOCK_TEXT[block]}</em>` : `<em>+${r.xp} XP</em>`}
        ${repeat ? `<button data-act="craft" data-recipe="${r.id}" data-times="5" ${disabled}>×5</button>` : ""}
        <button data-act="craft" data-recipe="${r.id}" data-times="1" class="primary" ${disabled}>${r.output.kind === "gear" ? "Make" : "Craft"}</button></footer>
    </article>`;
  }

  private project(id: ProjectId): string {
    const def = PROJECTS[id];
    const ok = isMet(missingFor(this.host.state, def.requires));
    return `<h2>${def.name}</h2><p class="lede">${def.description}</p>${this.req(def.requires)}
      <button data-act="repair" data-project="${id}" class="primary wide" ${ok ? "" : "disabled"}>${ok ? "Repair" : "Gather what's missing"}</button>`;
  }

  private lighthouse(): string {
    const s = this.host.state;
    const next = nextStage(s);
    const track = STAGES.map((st) => `<li class="${st.index <= s.stage ? "done" : st === next ? "next" : ""}"><span>${st.index <= s.stage ? "✓" : st.index}</span>${st.name}</li>`).join("");
    let card = `<p class="lede">The light is as strong as it gets this chapter.</p>`;
    if (next) {
      const ok = isMet(missingFor(s, next.requires));
      const here = next.performedAt === "home";
      const reveals = next.reveals.map((l) => LOCATIONS[l].name).join(", ");
      card = `<div class="stage-card"><h3>${next.name}</h3><p>${next.description}</p>${this.req(next.requires)}
        ${reveals ? `<p class="reveal">Reveals on the chart: <strong>${reveals}</strong></p>` : ""}
        ${here ? `<button data-act="upgrade" class="primary wide" ${ok ? "" : "disabled"}>${ok ? "Upgrade the lighthouse" : "Gather what's missing"}</button>` : `<p class="reveal">This happens at <strong>${LOCATIONS[next.performedAt].name}</strong>.</p>`}</div>`;
    }
    return `<h2>The Lighthouse <small>${STAGES[s.stage]!.name}</small></h2><ol class="track">${track}</ol>${card}`;
  }

  private chart(): string {
    const s = this.host.state;
    const offshore = canTravelOffshore(s);
    // A little sea chart: the beam's reach is a lit circle, everything past it is fog.
    const pos: Record<LocationId, [number, number]> = { home: [70, 150], shore: [150, 95], wreck: [255, 165], beacon: [360, 70] };
    const reach = [120, 215, 330, 330][s.stage] ?? 330;
    const dots = LOCATION_IDS.filter((l) => l !== "home")
      .map((l) => {
        const [x, y] = pos[l];
        const seen = LOCATIONS[l].revealedAtStage <= s.stage;
        const here = l === s.location ? " here" : "";
        return `<g class="${seen ? "seen" : "fog"}${here}"><circle cx="${x}" cy="${y}" r="${seen ? 9 : 6}"/><text x="${x}" y="${y - 15}">${seen ? LOCATIONS[l].name : "?"}</text></g>`;
      })
      .join("");
    const svg = `<svg class="chart-svg" viewBox="0 0 420 220">
      <defs><radialGradient id="lit"><stop offset="0" stop-color="#ffe7b0" stop-opacity="0.28"/><stop offset="1" stop-color="#ffe7b0" stop-opacity="0"/></radialGradient></defs>
      <rect width="420" height="220" class="sea"/>
      <circle cx="70" cy="150" r="${reach}" fill="url(#lit)"/>
      <circle cx="70" cy="150" r="7" class="home"/><text x="70" y="178" class="home-label">Lantern's Rest</text>
      ${dots}</svg>`;
    const rows = LOCATION_IDS.filter((l) => l !== s.location)
      .map((l) => {
        const d = LOCATIONS[l];
        if (l === "home") return `<li><div><strong>${d.name}</strong><p>Row home. Whatever you carry is safe once it's in the chest.</p></div><button data-act="travel" data-to="home" class="primary">Row home</button></li>`;
        if (d.revealedAtStage > s.stage) return `<li class="fog"><div><strong>Fog</strong><p>The beam can't reach this far yet.</p></div></li>`;
        const boat = l === "shore" || offshore;
        return `<li><div><strong>${d.name}</strong><p>${d.blurb}</p></div>${boat ? `<button data-act="travel" data-to="${l}" class="primary">Set out</button>` : `<em>Mend the dock first</em>`}</li>`;
      })
      .join("");
    return `<h2>Sea chart</h2><p class="lede">${this.host.tideLine()}</p>${svg}<ul class="dest">${rows}</ul>`;
  }

  private journal(tab: "satchel" | "skills" | "lighthouse" | "settings"): string {
    const tabs = (["satchel", "skills", "lighthouse", "settings"] as const)
      .map((t) => `<button data-act="tab" data-tab="${t}" class="${t === tab ? "on" : ""}">${t[0]!.toUpperCase() + t.slice(1)}</button>`)
      .join("");
    let body = "";
    const s = this.host.state;
    if (tab === "satchel") {
      const rows = s.satchel.map((st) => (st ? `<li>${ITEMS[st.item].name}<span>×${st.qty}</span></li>` : "")).join("");
      const keys = s.keyItems.map((k) => `<li class="key">${ITEMS[k].name}<span>${ITEMS[k].description}</span></li>`).join("");
      const gear = s.gear.map((g) => `<li>${GEAR[g].name}<span>${GEAR[g].description}</span></li>`).join("");
      body = `<div class="cols"><section><h3>Satchel <small>${s.satchel.filter(Boolean).length}/${satchelCapacity(s)}</small></h3><ul class="rows">${rows || `<li class="empty">Empty</li>`}${keys}</ul></section>
        <section><h3>Gear</h3><ul class="rows gear">${gear}</ul></section></div>`;
    } else if (tab === "skills") {
      body = `<div class="skills">${SKILL_IDS.map((id) => {
        const xp = s.skillXp[id];
        const lvl = levelForXp(xp);
        const next = SKILLS[id].milestones.find((m) => m.level > lvl);
        return `<div class="skill"><header><strong>${SKILLS[id].name}</strong><span>${lvl}${lvl >= MAX_LEVEL ? " (max)" : ""}</span></header>
          <div class="xp"><i style="width:${(levelProgress(xp) * 100).toFixed(1)}%"></i></div>
          <p>${SKILLS[id].purpose}</p>${next ? `<p class="next">Level ${next.level}: ${next.text}</p>` : ""}</div>`;
      }).join("")}</div>`;
    } else if (tab === "lighthouse") {
      body = this.lighthouse();
    } else {
      const st = s.settings;
      const confirm =
        this.confirmStep === 0
          ? `<button data-act="reset1" class="danger">Reset save…</button>`
          : this.confirmStep === 1
            ? `<p class="warn">This deletes your keeper, the lighthouse's progress and everything stored.</p><button data-act="reset2" class="danger">Yes, reset</button> <button data-act="reset0">Cancel</button>`
            : `<p class="warn">Really delete everything? This can't be undone.</p><button data-act="reset3" class="danger">Delete my save</button> <button data-act="reset0">Cancel</button>`;
      body = `<div class="settings">
        <label>Mouse sensitivity <input type="range" min="0.3" max="2.5" step="0.05" value="${st.sensitivity}" data-set="sensitivity"><output>${st.sensitivity.toFixed(2)}</output></label>
        <label>Field of view <input type="range" min="60" max="100" step="1" value="${st.fov}" data-set="fov"><output>${st.fov}°</output></label>
        <label>Volume <input type="range" min="0" max="1" step="0.05" value="${st.volume}" data-set="volume"><output>${Math.round(st.volume * 100)}%</output></label>
        <label class="check"><input type="checkbox" data-set="screenShake" ${st.screenShake ? "checked" : ""}> Screen shake</label>
        <label class="check"><input type="checkbox" data-set="headBob" ${st.headBob ? "checked" : ""}> Head bob</label>
        <div class="reset">${confirm}</div></div>`;
    }
    return `<h2>Keeper's journal</h2><nav class="tabs">${tabs}</nav>${body}`;
  }

  private summary(m: Extract<MenuKind, { kind: "summary" }>): string {
    const list = (stacks: ItemStack[], sign: string) => stacks.map((s) => `<li>${ITEMS[s.item].name}<span>${sign}${s.qty}</span></li>`).join("");
    const xp = (Object.entries(m.xp) as [SkillId, number][]).filter(([, v]) => v > 0).map(([k, v]) => `<li>${SKILLS[k].name}<span>+${v} XP</span></li>`).join("");
    return `<h2>${m.title}</h2><p class="lede">${m.sub}</p><div class="cols">
      <section><h3>${m.lost.length ? "Lost" : "This trip"}</h3><ul class="rows">${m.lost.length ? list(m.lost, "−") : list(m.gained, "+") || `<li class="empty">Nothing this time</li>`}</ul></section>
      <section><h3>Experience</h3><ul class="rows">${xp || `<li class="empty">—</li>`}${m.kills ? `<li>Creatures driven off<span>${m.kills}</span></li>` : ""}</ul></section></div>`;
  }

  // -------------------------------------------------------------- input

  private onClick(e: MouseEvent): void {
    const btn = (e.target as HTMLElement).closest<HTMLButtonElement>("button[data-act]");
    if (!btn || btn.disabled) return;
    this.click();
    const d = btn.dataset;
    switch (d.act) {
      case "close":
        this.host.closeMenu();
        return;
      case "craft":
        this.host.craft(d.recipe!, Number(d.times));
        break;
      case "repair":
        this.host.repair(d.project as ProjectId);
        break;
      case "upgrade":
        this.host.upgradeLighthouse();
        break;
      case "deposit":
        this.host.depositAll();
        break;
      case "store":
        this.host.store(Number(d.slot));
        break;
      case "take":
        this.host.take(d.item as ItemId);
        break;
      case "travel":
        this.host.travel(d.to as LocationId);
        return;
      case "tab":
        this.current = { kind: "journal", tab: d.tab as "satchel" };
        this.confirmStep = 0;
        break;
      case "reset0":
        this.confirmStep = 0;
        break;
      case "reset1":
        this.confirmStep = 1;
        break;
      case "reset2":
        this.confirmStep = 2;
        break;
      case "reset3":
        this.host.resetSave();
        return;
    }
    this.render();
  }

  private onInput(e: Event): void {
    const input = e.target as HTMLInputElement;
    const key = input.dataset.set as keyof GameState["settings"] | undefined;
    if (!key) return;
    const st = this.host.state.settings;
    if (input.type === "checkbox") (st[key] as boolean) = input.checked;
    else (st[key] as number) = Number(input.value);
    const out = input.parentElement?.querySelector("output");
    if (out) out.textContent = key === "fov" ? `${st.fov}°` : key === "volume" ? `${Math.round(st.volume * 100)}%` : st.sensitivity.toFixed(2);
    this.host.settingsChanged();
  }
}
