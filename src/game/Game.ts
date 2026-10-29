import { Horizon } from "../world/Horizon";
import { PROLOGUE, PROLOGUE_CARD_SECONDS } from "../data/story";
import { driftGives, sourcesOf, stillNeeded } from "../systems/guide";
import * as THREE from "three";
import { Sfx } from "../audio/Sfx";
import { Projectiles } from "../combat/Projectiles";
import { Assets, SHARED_MODELS } from "../core/Assets";
import { EventBus } from "../core/EventBus";
import { Input } from "../core/Input";
import { Loop } from "../core/Loop";
import { SaveSystem } from "../core/Save";
import { BALANCE } from "../data/balance";
import { ACTIONS, effectiveBindings, keyName, type Action } from "../data/controls";
import { PERF, POST, RAIN } from "../data/presentation";
import { ENEMIES } from "../data/enemies";
import { DECOR, DECOR_RULES } from "../data/decor";
import { DECOR_IDS, ENEMY_IDS, SKILL_IDS, type EnemyId, type FlagId, type FlotsamId, type GearId, type ItemId, type LocationId, type NpcId, type ProjectId, type SkillId, type StageIndex } from "../data/ids";
import { GEAR, ITEMS } from "../data/items";
import { PROJECTS, STAGES } from "../data/lighthouse";
import { LOCATIONS } from "../data/locations";
import { NODES } from "../data/nodes";
import { FLOTSAM } from "../data/salvage";
import { NPCS } from "../data/npcs";
import { getRecipe } from "../data/recipes";
import { SKILLS } from "../data/skills";
import { TIDE } from "../data/tide";
import { validateData } from "../data/validate";
import { Effects, FX_COLORS } from "../fx/Effects";
import { Post } from "../fx/Post";
import { Rain } from "../fx/Rain";
import { Loot } from "../fx/Loot";
import { Fishing } from "../gather/Fishing";
import { Flotsam, type Piece } from "../gather/Flotsam";
import { GatherNode } from "../gather/GatherNode";
import { Hook, type Hookable } from "../gather/Hook";
import { Wreck } from "../gather/Wreckage";
import { PlayerController } from "../player/PlayerController";
import { Viewmodel } from "../player/Viewmodel";
import { createNewGame, type GameState } from "../state/GameState";
import { craft } from "../systems/crafting";
import { decorAt, pickUpDecor, placeBlock, placeDecor, type PlaceBlock } from "../systems/decor";
import { addItem, applyDeathLoss, available, carried, depositAll, hasAll, removeAvailable, satchelCapacity, stored } from "../systems/inventory";
import { buildProgress, deliver, remaining } from "../systems/building";
import { advanceStage, isMet, maxHp, missingFor } from "../systems/progression";
import { awayCatch, hookStats, rollYields } from "../systems/salvage";
import { advanceQuest, currentStep, stepMaterials } from "../systems/quests";
import { addXp, skillLevel } from "../systems/skills";
import { AutoResolution } from "../systems/resolution";
import { readTide, tideEvents, type TideReading } from "../systems/tide";
import { Hud, type CompassMarker, type HudView, type KeyLabels } from "../ui/Hud";
import { Menus, type MenuKind } from "../ui/Menus";
import { HomeLevel } from "../world/home/HomeLevel";
import type { PieceBatch } from "../world/Batch";
import { buoyShadows, type Level, type LevelInteract } from "../world/Level";
import { GloomPocket } from "../world/Gloom";
import { Gulls } from "../world/Gulls";
import { LevelHeights } from "../world/Heights";
import { GlbLevel, loadLevel } from "../world/LevelLoader";
import { BeamRig, DistantLight, stageLook } from "../world/Lighthouse";
import { Sky } from "../world/Sky";
import { TIDE_UNIFORMS } from "../world/TideMaterial";
import { Water } from "../world/Water";
import type { GameContext } from "./Context";
import { Encounters } from "./Encounters";

// The game: owns the renderer, the current location and every runtime system,
// and runs the loop. Gameplay modules reach it through GameContext.

/** How you arrived somewhere, which decides where you appear. */
type Via = "resume" | "boat" | "path" | "defeat";

type Mode = "loading" | "title" | "paused" | "playing" | "menu" | "travel";

type Focus = { kind: "node"; node: GatherNode } | { kind: "interact"; it: LevelInteract };

interface Trip {
  gained: Map<ItemId, number>;
  xp: Partial<Record<SkillId, number>>;
  kills: number;
}

interface Transition {
  t: number;
  phase: "out" | "load" | "in";
  /** null: stay here and just move the player (the wreck's rope ladder). */
  to: LocationId | null;
  via: Via;
  move?: { position: THREE.Vector3; yaw: number };
  title: string;
  sub: string;
  color: string;
  outTime: number;
  hold: number;
  loaded: boolean;
}

/** The farthest anything can be targeted from (fishing spots). */
const FOCUS_RANGE = 10;
const UP = new THREE.Vector3(0, 1, 0);
const tmp = new THREE.Vector3();
const tmp2 = new THREE.Vector2();

const FREE_LOOK_NOTE =
  "This browser won't capture the mouse, so move it to look and hold it near the left or right edge to keep turning. " +
  `Open ${location.origin} in Chrome or Edge for full mouse capture.`;

/** Why a piece of decor can't go where you're looking. A shortfall in materials lists them instead. */
const BUILD_BLOCK: Record<Exclude<PlaceBlock, "cost">, string> = {
  bounds: "Only inside the village",
  slope: "Too steep here",
  water: "Too near the water",
  blocked: "Keep this clear",
  overlap: "Something's in the way",
  limit: "The Rest can't hold any more decor",
};

const CHAPTER_SUB = "Saltmere burns again. Lantern's Rest has a future, and the coast is yours to explore.";

const wrap = (a: number) => Math.atan2(Math.sin(a), Math.cos(a));
const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

export class Game implements GameContext {
  readonly bus = new EventBus();
  readonly renderer: THREE.WebGLRenderer;
  readonly scene = new THREE.Scene();
  readonly camera: THREE.PerspectiveCamera;
  readonly input: Input;
  readonly hud: Hud;
  readonly sfx = new Sfx();
  readonly assets = new Assets();
  readonly player = new PlayerController();
  readonly effects = new Effects();
  readonly loot = new Loot();
  readonly projectiles = new Projectiles();
  readonly saves = new SaveSystem(window.localStorage);
  state: GameState;
  level: Level;
  tide: TideReading;
  time = 0;

  private readonly menus: Menus;
  private readonly sky: Sky;
  private readonly post: Post;
  private readonly water = new Water();
  private readonly home = new HomeLevel();
  private readonly loop: Loop;
  private readonly ray = new THREE.Raycaster();
  /** The lantern in your hand lights the world too (the viewmodel has its own). */
  private readonly lantern = new THREE.PointLight(0xffc98a, 5, 14, 1.4);
  private viewmodel: Viewmodel | null = null;
  private fishing: Fishing | null = null;
  private hook: Hook | null = null;
  /** The cove's drift: home only. */
  private flotsam: Flotsam | null = null;
  /** Wreckage the hook tears at, here, and those built in pieces drawn merged. */
  private wrecks: Wreck[] = [];
  private wreckBatch: PieceBatch | null = null;
  /** Build mode at home (B): the piece in hand (an index into DECOR_IDS) and its turn. Null when not building. */
  private building: { index: number; yaw: number } | null = null;
  private lastDecor = 0;
  private encounters = new Encounters([]);
  private nodes: GatherNode[] = [];
  private distant: DistantLight | null = null;
  private beacon: BeamRig | null = null;
  /** The current level's sea floor and rain floor, for the water and rain shaders. */
  private heights: LevelHeights | null = null;
  private readonly rain = new Rain();
  private gloom: GloomPocket[] = [];

  private mode: Mode = "loading";
  private everStarted = false;
  /** Pointer lock has succeeded this session, so a later refusal is Chrome's post-Esc cooldown. */
  private lockWorked = false;
  private resetting = false;
  private transition: Transition | null = null;
  private trip: Trip | null = null;
  /** The drowned world on this location's horizon. */
  private horizon: Horizon | null = null;
  private gulls: Gulls | null = null;
  /** The prologue, while it's up: which card, and for how long. */
  private story: { i: number; t: number; shown: number } | null = null;
  /** The step whose materials we last announced as all in hand. */
  private readyTold: string | null = null;
  private pendingSummary: MenuKind | null = null;
  private flagsKey = "";

  /** What the HUD prompt says, and the key it names (interact unless said). */
  private prompt: { text: string; blocked: boolean; key?: Action } | null = null;
  private gatherNode: GatherNode | null = null;
  private gatherT = 0;
  private readonly fishFrom = new THREE.Vector3();
  private fireCooldown = 0;
  private eatT = 0;
  private healLeft = 0;
  private healRate = 0;
  private readonly buffs = { maxHp: 0, maxHpT: 0, dash: 0, dashT: 0 };
  private shake = 0;
  private floodWarn = 0;
  private autosave = 0;
  private readonly inside = new Set<number>();
  private readonly toldOnce = new Set<string>();
  private relight: { t: number } | null = null;
  private lastYaw = 0;
  private lastPitch = 0;
  /** Lantern Flare charge, 0..1 (1 = ready), and the flash of the last one (1 → 0). */
  private flareCharge = 1;
  private flareFlash = 0;
  /** Seconds spent inside a Gloom pocket, and the smoothed veils for the HUD. */
  private gloomT = 0;
  private gloomVeil = 0;
  private swimVeil = 0;
  /** Auto resolution: the share of pixels drawn, moved by the frame times (src/systems/resolution.ts). */
  private readonly autoRes = new AutoResolution();
  private renderScale = 1;

  constructor(container: HTMLElement, hudRoot: HTMLElement) {
    const saved = this.saves.load();
    this.state = saved ?? createNewGame();
    // A first game follows the system's reduced-motion preference.
    if (!saved && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) this.state.settings.reducedMotion = true;

    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2) * (this.state.settings.renderScale || 1));
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = POST.exposure;
    // Plots rise out of the ground under a clipping plane (src/world/home/Plot.ts).
    this.renderer.localClippingEnabled = true;
    container.appendChild(this.renderer.domElement);

    this.camera = new THREE.PerspectiveCamera(this.state.settings.fov, window.innerWidth / window.innerHeight, 0.05, 1200);
    this.camera.rotation.order = "YXZ";
    this.camera.add(this.lantern);
    this.lantern.position.set(-0.35, -0.25, -0.2);
    this.scene.add(this.camera);

    this.sky = new Sky(this.scene);
    this.scene.environment = this.sky.environment(this.renderer);
    this.scene.environmentIntensity = POST.environment;
    this.post = new Post(this.renderer, this.scene, this.camera);
    this.scene.add(this.water.mesh, this.rain.mesh, this.effects.group, this.loot.group, this.projectiles.group, this.home.root);
    this.level = this.home;
    this.tide = readTide(this.state.tide.elapsed, TIDE);

    this.input = new Input(this.renderer.domElement);
    this.hud = new Hud(hudRoot);
    this.menus = new Menus(
      hudRoot,
      {
        state: this.state,
        craft: (id, times) => this.craftRecipe(id, times),
        build: (p) => this.build(p),
        upgradeLighthouse: () => this.upgradeLighthouse(),
        depositAll: () => this.deposit(),
        store: (slot) => this.storeSlot(slot),
        take: (item) => this.takeItem(item),
        travel: (to) => this.setOut(to),
        settingsChanged: () => this.applySettings(),
        resetSave: () => this.resetSave(),
        closeMenu: () => this.closeMenu(),
        tideLine: () => this.tideLine(),
        captureKey: (done) => this.input.capture(done),
      },
      () => this.sfx.ui(),
    );
    this.hud.setOverlay("title", "Loading…");
    this.hud.onOverlayClick(() => void this.begin());
    document.addEventListener("pointerlockchange", () => {
      if (this.input.locked) this.lockWorked = true;
      else if (this.mode === "playing" && this.input.lookMode === "captured") this.pause();
    });
    window.addEventListener("blur", () => {
      if (this.mode === "playing") this.pause();
    });
    window.addEventListener("resize", () => this.onResize());

    this.player.onRescued = (to) => {
      this.hud.toast("The current drags you back to solid ground.", "warn");
      this.effects.splash(to, 20);
    };
    this.player.onDash = () => this.sfx.dash();
    this.sfx.onCaption = (text, at) => this.caption(text, at);
    this.player.onJump = () => this.sfx.jump();
    this.player.onLand = (speed) => {
      if (speed < 7) return;
      this.sfx.land();
      this.addShake(Math.min(0.35, speed * 0.025));
    };
    this.player.spawn(this.home.spawn, this.home.spawnYaw);
    this.player.maxHp = this.player.hp = this.maxHpNow();
    this.applySettings(false);

    this.wireEvents();
    this.refreshWorld();

    if (import.meta.env.DEV) {
      const errors = validateData();
      if (errors.length) console.warn("[data] validation failed:\n" + errors.join("\n"));
      this.exposeDebug();
    }

    this.loop = new Loop(
      (dt) => this.update(dt),
      (frameDt) => this.render(frameDt),
    );
  }

  start(): void {
    this.loop.start();
    void this.boot();
  }

  /** Loads the shared models, then the saved location, then waits for the first click. */
  private async boot(): Promise<void> {
    await this.assets.preload(SHARED_MODELS);
    if (!(await this.home.load(this.assets))) {
      this.hud.setOverlay("title", "Lantern's Rest couldn't be loaded. Check your connection and reload the page.");
      return;
    }
    this.viewmodel = new Viewmodel(this.assets);
    this.viewmodel.scene.environment = this.scene.environment;
    this.viewmodel.scene.environmentIntensity = POST.environment;
    this.post.setOverlay(this.viewmodel.scene, this.viewmodel.camera);
    this.viewmodel.equip(this.state.gear);
    this.fishing = new Fishing(this);
    this.hook = new Hook(this);
    await this.enter(this.state.location, "resume");
    this.setMode("title");
  }

  // ------------------------------------------------------------- modes

  /** Overlay click: start or resume. Falls back to free look where the browser blocks pointer lock. */
  private async begin(): Promise<void> {
    if (this.mode !== "title" && this.mode !== "paused") return;
    this.sfx.resume();
    this.sfx.setAmbience(this.state.location);
    this.setMode("playing");
    // A new keeper hears how the world got this way before taking a step.
    if (this.state.playSeconds === 0 && this.state.quest.step === 0 && !this.story) this.story = { i: 0, t: 0, shown: -1 };
    const locked = await this.input.requestLock();
    // The player may have opened a menu or paused while the browser decided.
    if ((this.mode as Mode) !== "playing") return;
    if (locked) {
      this.input.lookMode = "captured";
      return;
    }
    if (this.lockWorked) {
      // Chrome refuses to re-lock for about a second after Esc. The browser is fine; ask again.
      this.setMode("paused", "Click again to resume");
      return;
    }
    if (this.input.lookMode !== "free") {
      this.input.lookMode = "free";
      this.hud.setOverlayNote(FREE_LOOK_NOTE);
      this.hud.toast("Move the mouse to look. Hold it near the left or right edge to keep turning.", "info", 6);
    }
  }

  private pause(): void {
    this.setMode("paused");
    this.save();
  }

  /** Only "playing" runs the gameplay clocks (tide, autosave); everything else is frozen behind a card. */
  private setMode(mode: Mode, prompt?: string): void {
    this.mode = mode;
    this.input.active = mode === "playing";
    if (mode === "playing") this.everStarted = true;
    this.hud.setOverlay(mode === "title" || mode === "loading" ? "title" : mode === "paused" ? "paused" : "hidden", prompt ?? (mode === "loading" ? "Loading…" : undefined));
    this.hud.setCrosshair(mode === "playing");
    if (!this.everStarted && mode === "paused") this.hud.setOverlay("title");
  }

  private openMenu(m: MenuKind): void {
    this.gatherT = 0;
    this.gatherNode = null;
    this.setMode("menu");
    this.menus.open(m);
    if (this.input.locked) document.exitPointerLock();
  }

  private closeMenu(): void {
    if (!this.menus.isOpen) return;
    this.menus.close();
    this.setMode("playing");
    this.relock();
  }

  /** Re-captures the mouse after a menu. Works from a click; from Esc the browser says no, so ask for one. */
  private relock(): void {
    if (this.input.lookMode !== "captured" || this.input.locked) return;
    void this.input.requestLock().then((ok) => {
      if (!ok && this.mode === "playing") this.setMode("paused", "Click to resume");
    });
  }

  // ------------------------------------------------------------ update

  private update(dt: number): void {
    this.time += dt;
    switch (this.mode) {
      case "playing":
        if (this.input.pressed("pause")) {
          if (this.hud.dialogueOpen) this.closeDialogue();
          else this.pause();
        } else if (this.input.pressed("journal") && !this.relight && !this.story) this.openMenu({ kind: "journal" });
        else this.updatePlaying(dt);
        break;
      case "menu":
        if (this.input.pressed("pause") || (this.input.pressed("journal") && this.menus.kind === "journal")) this.closeMenu();
        break;
      case "travel":
        this.updateTransition(dt);
        break;
      default:
        break;
    }
    // Cosmetic time (waves, beams, boats, buoys, particles) keeps running behind cards.
    const warn = this.tide.phase === "rising" ? 1 : this.tide.warning && this.tide.nextTurn === "rising" ? 0.7 : 0;
    this.floodWarn = THREE.MathUtils.damp(this.floodWarn, warn, 2, dt);
    this.level.update({ time: this.time, dt, waterY: this.tide.waterY, floodWarning: this.floodWarn, viewer: this.player.position });
    this.gulls?.update(dt, this.player.position, this.tide.waterY);
    this.distant?.rig.update(dt);
    this.beacon?.update(dt);
    this.effects.update(dt);
    const vh = this.renderer.getDrawingBufferSize(tmp2).y;
    for (const g of this.gloom) g.update(dt, this.time, vh);
    this.flareFlash = Math.max(0, this.flareFlash - dt / BALANCE.flare.flash);
    this.input.endStep();
  }

  private updatePlaying(dt: number): void {
    if (this.story) {
      this.updateStory(dt);
      return;
    }
    const s = this.state;
    s.playSeconds += dt;
    s.tide.elapsed += dt;
    if (import.meta.env.DEV && this.input.pressed("debugTide")) s.tide.elapsed += 60;
    this.updateTide();
    this.updateBuffs(dt);

    const p = this.player;
    p.maxHp = this.maxHpNow();
    p.hp = Math.min(p.hp, p.maxHp);
    p.update(dt, this.input, {
      collider: this.level.collider,
      dynamics: this.level.buoys,
      waterY: this.tide.waterY,
      anchors: this.level.anchors,
      sensitivity: s.settings.sensitivity,
      dashCharges: this.dashMax(),
      dashCooldownMul: this.buffs.dashT > 0 ? 1 - this.buffs.dash : 1,
      speedMul: this.eatT > 0 ? 0.5 : 1,
      rooted: this.relight !== null,
    });

    this.encounters.sync(this);
    this.encounters.update(dt, this);
    this.projectiles.update(dt, this);
    this.loot.update(dt, this);
    for (const n of this.nodes) n.update(dt, this);
    const salvaged = s.salvaged;
    for (const w of this.wrecks) w.update(dt, this);
    this.flotsam?.update(dt, this);
    if (this.input.pressed("build")) this.toggleBuild();
    if (this.building) this.updateBuild();
    else this.updateHook(dt);
    // Hooked or picked up: a salvage step may be done.
    if (s.salvaged !== salvaged) this.afterAction(false);
    this.shadowLod();
    this.updateTriggers();
    if (!this.building) this.updateInteraction(dt);
    if (this.mode !== "playing") return;
    this.updateCombat(dt);
    this.updateFlare(dt);
    this.updateGloom(dt);
    this.updateFood(dt);
    this.updateRelight(dt);

    if (p.hp <= 0) {
      this.defeat();
      return;
    }
    this.autosave += dt;
    if (this.autosave >= BALANCE.save.autosaveSecondsAtHome) this.save();
  }

  private updateTide(): void {
    const next = readTide(this.state.tide.elapsed, TIDE);
    for (const e of tideEvents(this.tide, next)) {
      if (e.type === "warning") this.bus.emit("tide:warning", { turn: e.turn, secondsLeft: next.phaseTimeLeft });
      else if (e.type === "turnStarted") this.bus.emit("tide:turnStarted", { phase: e.phase });
      else this.bus.emit("tide:settled", { state: e.state });
    }
    this.tide = next;
  }

  private updateTriggers(): void {
    const probe = tmp.copy(this.player.position).add(new THREE.Vector3(0, 0.9, 0));
    this.level.triggers.forEach((t, i) => {
      const now = t.box.containsPoint(probe);
      if (now && !this.inside.has(i)) {
        this.inside.add(i);
        this.onTrigger(t.event);
      } else if (!now) this.inside.delete(i);
    });
  }

  private onTrigger(event: string): void {
    if (event === "boss") {
      const boss = this.encounters.boss;
      if (boss && boss.alive && !boss.awake) boss.wake(this);
    } else if (event.startsWith("toast:")) {
      const key = `${this.state.location}:${event}`;
      if (this.toldOnce.has(key)) return;
      this.toldOnce.add(key);
      this.hud.toast(event.slice(6), "info", 5);
    }
  }

  // ------------------------------------------------------- interaction

  private updateInteraction(dt: number): void {
    this.prompt = null;
    const fishing = this.fishing;
    if (fishing?.active) {
      this.gatherNode = null;
      const moved = this.player.position.distanceTo(this.fishFrom) > 2.5;
      const early = fishing.phase !== "bite" && this.input.pressed("interact");
      if (moved || early || this.player.water === "swimming" || this.input.pressed("fire")) {
        fishing.stop();
        this.hud.toast("You reel in the line.", "info", 1.6);
        return;
      }
      this.prompt = fishing.phase === "bite" ? { text: "Reel in!", blocked: false } : { text: fishing.prompt(), blocked: true };
      fishing.update(dt, this, this.viewmodel!.rodTip(this.camera));
      if (!fishing.active) this.afterAction(false);
      return;
    }

    if (this.hud.dialogueOpen) {
      if (this.input.pressed("interact")) {
        this.hud.advanceDialogue();
        if (!this.hud.dialogueOpen) this.afterAction();
      }
      return;
    }

    const focus = this.findFocus();
    if (focus?.kind !== "node" || focus.node !== this.gatherNode) {
      this.gatherNode = null;
      this.gatherT = 0;
    }
    if (!focus) {
      this.hookPrompt();
      return;
    }

    if (focus.kind === "interact") {
      const info = this.interactInfo(focus.it);
      this.prompt = { text: info.label, blocked: info.blocked };
      if (!this.input.pressed("interact")) return;
      if (info.blocked) this.sfx.denied();
      else this.useInteract(focus.it);
      return;
    }

    const node = focus.node;
    const blocked = node.blocked(this);
    if (blocked) {
      this.prompt = { text: blocked, blocked: true };
      if (this.input.pressed("interact")) this.sfx.denied();
      return;
    }
    this.prompt = { text: node.label(this), blocked: false };
    const hold = node.holdTime(this);
    if (hold <= 0) {
      if (this.input.pressed("interact")) {
        this.fishFrom.copy(this.player.position);
        this.fishing?.start(node, this);
      }
      return;
    }
    if (!this.input.held("interact")) {
      this.gatherNode = null;
      this.gatherT = 0;
      return;
    }
    this.gatherNode = node;
    this.gatherT += dt;
    if (this.gatherT >= hold) {
      this.gatherNode = null;
      this.gatherT = 0;
      node.complete(this);
      this.afterAction(false);
    }
  }

  /** What the crosshair is on, with a little help at close range. */
  private findFocus(): Focus | null {
    const targets = new Map<THREE.Object3D, Focus>();
    for (const it of this.level.interacts) if (shown(it.object)) targets.set(it.object, { kind: "interact", it });
    for (const node of this.nodes) if (node.available || node.def.kind === "key") targets.set(node.object, { kind: "node", node });
    if (!targets.size) return null;

    const eye = this.player.eye;
    const dir = this.player.aim();
    this.ray.set(eye, dir);
    this.ray.far = FOCUS_RANGE;
    for (const hit of this.ray.intersectObjects([...targets.keys()], true)) {
      let f: Focus | undefined;
      for (let o: THREE.Object3D | null = hit.object; o && !f; o = o.parent) f = targets.get(o);
      if (!f) continue;
      if (hit.distance > (f.kind === "node" ? f.node.range : f.it.range)) break;
      const wall = this.level.collider.raycast(eye, dir, hit.distance);
      if (wall && wall.distance < hit.distance - 0.35) break;
      return f;
    }

    // Nothing under the crosshair: the nearest thing right in front of you.
    const flat = new THREE.Vector3(dir.x, 0, dir.z).normalize();
    let best: Focus | null = null;
    let bestD = 2.4;
    for (const [obj, f] of targets) {
      if (f.kind === "node" && f.node.def.kind === "fish") continue;
      obj.getWorldPosition(tmp).sub(this.player.position).setY(0);
      const d = tmp.length();
      if (d >= bestD || (d > 0.3 && tmp.divideScalar(d).dot(flat) < 0.75)) continue;
      best = f;
      bestD = d;
    }
    return best;
  }

  private interactInfo(it: LevelInteract): { label: string; blocked: boolean } {
    const s = this.state;
    const ok = (label: string) => ({ label, blocked: false });
    const no = (label: string) => ({ label, blocked: true });
    if (it.id.startsWith("npc:")) return ok(`Talk to ${NPCS[it.id.slice(4) as NpcId].name}`);
    if (it.id.startsWith("plot:")) {
      const id = it.id.slice(5) as ProjectId;
      const p = buildProgress(s, id);
      return ok(p > 0 ? `${PROJECTS[id].name}: ${Math.floor(p * 100)}% rebuilt` : `${PROJECTS[id].ruin}: rebuild it`);
    }
    switch (it.id) {
      case "lamp":
        return ok("The lighthouse lamp");
      case "hearth":
        return ok("Cook at the hearth");
      case "storage":
        return ok("Open the storage chest");
      case "forge":
        return ok("Work the forge");
      case "net_loft":
        return ok("Work in the net loft");
      case "smokehouse":
        return ok("Smoke your catch");
      case "boat":
        return ok("Take the boat");
      case "rope_ladder": {
        // Only from the deck: at the bottom you're already where it goes.
        const bottom = this.level instanceof GlbLevel ? this.level.spawnFor("ladder").position.y : 0;
        return this.player.position.y > bottom + 2 ? ok("Climb down the rope ladder") : no("A rope ladder hangs from the stern rail");
      }
      case "beacon":
        if (s.stage >= 3) return no("Saltmere Beacon burns");
        if (!s.flags.includes("guardian_defeated")) return no("The lamp is cold. Something guards the rock.");
        if (!s.keyItems.includes("lighthouse_ember")) return no("The lamp is cold. Bring the Lighthouse Ember.");
        return ok("Relight Saltmere Beacon");
      default:
        return ok(it.id);
    }
  }

  private useInteract(it: LevelInteract): void {
    if (it.id.startsWith("npc:")) {
      this.talk(it.id.slice(4) as NpcId);
      return;
    }
    if (it.id.startsWith("plot:")) {
      this.openMenu({ kind: "project", project: it.id.slice(5) as ProjectId });
      return;
    }
    switch (it.id) {
      case "lamp":
        this.openMenu({ kind: "lighthouse" });
        break;
      case "hearth":
        this.openMenu({ kind: "station", station: "hearth" });
        break;
      case "storage":
        this.openMenu({ kind: "storage" });
        break;
      case "forge":
      case "net_loft":
      case "smokehouse":
        this.openMenu({ kind: "station", station: it.id });
        break;
      case "boat":
        this.openMenu({ kind: "chart" });
        break;
      case "rope_ladder":
        this.climbLadder();
        break;
      case "beacon":
        this.relightBeacon();
        break;
    }
  }

  private talk(npc: NpcId): void {
    const def = NPCS[npc];
    const step = currentStep(this.state);
    const lines = (step && def.lines[step.id]) || def.lines.default || ["…"];
    this.hud.showDialogue(def.name, lines);
    this.sfx.ui();
    if (!this.state.quest.talked.includes(npc)) this.state.quest.talked.push(npc);
    if (npc === "maren" && !this.state.flags.includes("met_maren")) this.state.flags.push("met_maren");
  }

  private closeDialogue(): void {
    this.hud.closeDialogue();
    this.afterAction();
  }

  private climbLadder(): void {
    const level = this.level;
    if (!(level instanceof GlbLevel)) return;
    const to = level.spawnFor("ladder");
    this.beginTransition({ to: null, via: "path", move: to, title: "", sub: "", color: "#05090c", outTime: 0.35, hold: 0.2 });
  }

  // ------------------------------------------------------- salvage hook

  /** The hook: right mouse anywhere, and left too where there's nothing to shoot. */
  private updateHook(dt: number): void {
    const hook = this.hook;
    if (!hook || !this.viewmodel) return;
    const free = !this.hud.dialogueOpen && !this.fishing?.active && !this.relight;
    const safe = LOCATIONS[this.state.location].safe;
    const throwing = free && (this.input.pressed("hook") || (safe && this.input.pressed("fire")));
    const targets: Hookable[] = [...(this.flotsam?.pieces ?? []), ...this.wrecks];
    const thrown = hook.update(dt, { targets, muzzle: this.viewmodel.muzzle(this.camera), throwing, stats: hookStats(this.state), flotsam: this.flotsam });
    if (thrown) this.viewmodel.kick();
    this.viewmodel.setHookOut(hook.out);
  }

  /** With nothing to interact with, the prompt says what the hook would do. */
  private hookPrompt(): void {
    const aim = this.hook?.aim;
    if (!aim) return;
    const key: Action = LOCATIONS[this.state.location].safe ? "fire" : "hook";
    this.prompt = aim.state === "ok" ? { text: `Hook the ${aim.target.name}`, blocked: false, key } : { text: aim.reason ?? "", blocked: true };
  }

  private reticle(): HudView["reticle"] {
    const hook = this.hook;
    if (!hook || this.building) return null;
    if (hook.reeling) return "reel";
    const aim = hook.aim;
    return aim ? (aim.state === "ok" ? "hook" : aim.state) : null;
  }

  /**
   * Home again: what the sea brought while you were away. Some washed up on
   * the beach (the save's cove.beach, which Flotsam lays out), and once the
   * Net Loft stands the cove net held some, hauled straight into the chest.
   * Returns a line for the homecoming, or "".
   */
  private homecoming(): string {
    const s = this.state;
    if (s.leftHomeAt === null) return "";
    const caught = awayCatch(s, s.leftHomeAt, s.tide.elapsed, Math.random);
    s.leftHomeAt = null;
    s.cove.beach.push(...caught.beach);
    s.cove.net.push(...caught.net);
    const netted = s.cove.net.length;
    for (const id of s.cove.net) for (const st of rollYields(FLOTSAM[id].yields, Math.random)) s.storage[st.item] = stored(s, st.item) + st.qty;
    s.cove.net = [];
    const lines: string[] = [];
    if (netted) lines.push(`The cove net held ${netted} piece${netted === 1 ? "" : "s"}: they're in the chest.`);
    if (caught.beach.length) lines.push(`The tide left ${caught.beach.length} on the beach.`);
    return lines.join(" ");
  }

  // ------------------------------------------------------------ building

  /** B at home: in and out of build mode. */
  private toggleBuild(): void {
    if (this.building) {
      this.lastDecor = this.building.index;
      this.building = null;
      this.home.decor?.showGhost(null);
      return;
    }
    if (this.level !== this.home || this.hud.dialogueOpen || this.fishing?.active || this.relight || !this.home.decor) {
      this.sfx.denied();
      return;
    }
    this.hook?.reset();
    this.viewmodel?.setHookOut(false);
    this.building = { index: this.lastDecor, yaw: 0 };
    this.sfx.ui();
  }

  /** The ghost follows the crosshair; place, turn, choose, or pick a piece back up for a full refund. */
  private updateBuild(): void {
    const b = this.building!;
    const home = this.home;
    const decor = home.decor!;
    const input = this.input;
    DECOR_IDS.forEach((_, i) => {
      if (input.pressedKey(`Digit${i + 1}`)) b.index = i;
    });
    const wheel = input.consumeWheel();
    if (wheel) b.index = (b.index + Math.sign(wheel) + DECOR_IDS.length) % DECOR_IDS.length;
    if (input.pressed("rotate")) b.yaw = (b.yaw + DECOR_RULES.turnStep) % (Math.PI * 2);
    const kind = DECOR_IDS[b.index]!;
    this.prompt = null;

    const eye = this.player.eye;
    const dir = this.player.aim();
    const hit = this.level.collider.raycast(eye, dir, DECOR_RULES.reach);
    const ground = home.groundRay(eye, dir, DECOR_RULES.reach);
    // Something standing in the way of the ground: a piece you placed, or a wall.
    if (hit && (!ground || hit.distance < ground.distance - 0.3)) {
      decor.showGhost(kind);
      const pick = decorAt(this.state, hit.point.x, hit.point.z, 0.3);
      if (pick < 0) {
        this.prompt = { text: "Look at open ground", blocked: true };
        return;
      }
      const piece = this.state.decor[pick]!;
      this.prompt = { text: `Pick up the ${DECOR[piece.kind].name} (all it cost comes back)`, blocked: false, key: "hook" };
      if (input.pressed("hook")) {
        pickUpDecor(this.state, pick);
        this.sfx.pickup();
        this.effects.burst(hit.point, FX_COLORS.smoke, 12);
        this.afterAction();
      }
      return;
    }
    if (!ground) {
      decor.showGhost(kind);
      this.prompt = { text: "Look at open ground, nearer", blocked: true };
      return;
    }
    const world = home.placeWorld([{ x: this.player.position.x, z: this.player.position.z, r: 0.6 }]);
    const at = ground.point;
    const block = placeBlock(this.state, world, kind, at.x, at.z, b.yaw);
    decor.showGhost(kind, new THREE.Vector3(at.x, home.groundY(at.x, at.z) ?? at.y, at.z), b.yaw, block === null);
    if (block === "cost") this.prompt = { text: `Needs ${DECOR[kind].cost.map((c) => `${c.qty} ${ITEMS[c.item].name}`).join(", ")}`, blocked: true };
    else if (block) this.prompt = { text: BUILD_BLOCK[block], blocked: true };
    else this.prompt = { text: `Place the ${DECOR[kind].name}`, blocked: false, key: "fire" };
    if (!input.pressed("fire")) return;
    if (placeDecor(this.state, world, kind, at.x, at.z, b.yaw)) {
      this.sfx.denied();
      return;
    }
    this.sfx.craft();
    this.effects.burst(at.clone().add(new THREE.Vector3(0, 0.4, 0)), FX_COLORS.smoke, 16);
    this.afterAction();
  }

  // ------------------------------------------------------------ combat

  private updateCombat(dt: number): void {
    this.fireCooldown = Math.max(0, this.fireCooldown - dt);
    if (LOCATIONS[this.state.location].safe || this.relight || this.hud.dialogueOpen || this.fishing?.active) return;
    if (!this.input.held("fire") || this.fireCooldown > 0) return;
    const stats = GEAR[this.weapon()].stats;
    this.fireCooldown = 1 / (stats.fireRate ?? 3);
    const dir = this.player.aim();
    const spread = Math.tan(THREE.MathUtils.degToRad(stats.spreadDeg ?? 1));
    const right = new THREE.Vector3().crossVectors(dir, UP).normalize();
    const up = new THREE.Vector3().crossVectors(right, dir);
    dir
      .addScaledVector(right, (Math.random() * 2 - 1) * spread)
      .addScaledVector(up, (Math.random() * 2 - 1) * spread)
      .normalize();
    this.projectiles.firePlayer(this.player.eye.addScaledVector(dir, 0.3), dir, stats.boltSpeed ?? 55, stats.boltDamage ?? 10, stats.pierce ?? 0);
    this.viewmodel?.kick();
    this.sfx.fire();
  }

  /** Only creatures, loot and what floats near you cast shadows (PERF.shadowNear). */
  private shadowLod(): void {
    const p = this.player.position;
    const near = PERF.shadowNear * PERF.shadowNear;
    for (const e of this.encounters.enemies) e.castShadows(e.position.distanceToSquared(p) < near);
    for (const n of this.nodes) n.castShadows(n.position.distanceToSquared(p) < near);
    for (const w of this.wrecks) w.castShadows(w.at.distanceToSquared(p) < near);
    buoyShadows(this.level.buoys, p, near);
  }

  /** Q: the Keeper's Lantern flares. Enemies in the cone reel; Gloom pockets in reach burn away. */
  private updateFlare(dt: number): void {
    const f = BALANCE.flare;
    if (this.flareCharge < 1) {
      this.flareCharge = Math.min(1, this.flareCharge + dt / f.cooldown);
      if (this.flareCharge >= 1) this.sfx.flareReady();
    }
    if (!this.input.pressed("flare") || this.hud.dialogueOpen || this.fishing?.active || this.relight) return;
    if (this.flareCharge < 1) {
      this.sfx.denied();
      return;
    }
    this.flareCharge = 0;
    this.flareFlash = 1;
    const eye = this.player.eye;
    const dir = this.player.aim();
    const half = THREE.MathUtils.degToRad(f.coneDeg);
    this.sfx.flare();
    this.viewmodel?.flare();
    const from = eye.clone().addScaledVector(dir, 1.4);
    this.effects.cone(from, dir, half, FX_COLORS.amber, 110, 18, 0.6);
    this.effects.cone(from, dir, half * 0.6, FX_COLORS.loot, 40, 24, 0.45);

    let immune = false;
    for (const e of this.encounters.enemies) {
      if (!e.alive) continue;
      const c = e.center();
      const to = c.clone().sub(eye);
      const d = to.length();
      if (d > f.range || (d > 1.5 && to.divideScalar(d).dot(dir) < Math.cos(half))) continue;
      if (this.level.collider.blocked(eye, c)) continue;
      if (!e.dazzle(this) && e.boss) immune = true;
    }
    if (immune) this.tellOnce("flare:boss", "The Guardian is far too vast to be dazzled.");

    for (const g of this.gloom) {
      if (!g.active) continue;
      const to = g.center.clone().setY(g.center.y + 1).sub(eye);
      const d = to.length();
      // Close enough to fill with light, or in the cone (widened by the pocket's own size) and in reach.
      const near = d < g.radius + f.gloomRadius;
      const seen = d - g.radius < f.range && to.divideScalar(d).dot(dir) > Math.cos(half + Math.atan2(g.radius, d));
      if (!(near || seen) || !g.dispel()) continue;
      const at = g.center.clone().setY(g.center.y + 1);
      this.sfx.gloomBurn(at);
      this.effects.burst(at, FX_COLORS.amber, 70);
      this.effects.emit(at, { count: 40, color: FX_COLORS.loot, speed: 3, life: 1.4, gravity: -1.5, up: 2, spread: g.radius * 0.4 });
      this.tellOnce("gloom:burnt", "The Gloom burns away.");
    }
  }

  /** Inside a Gloom pocket the cold slowly wears you down (never below a floor) until a Flare burns it off. */
  private updateGloom(dt: number): void {
    let depth = 0;
    for (const g of this.gloom) depth = Math.max(depth, g.depthAt(this.player.position));
    this.gloomT = depth > 0.02 ? this.gloomT + dt : 0;
    const gl = BALANCE.gloom;
    if (this.gloomT > 0 && this.gloomT <= dt) this.tellOnce("gloom:enter", `The Gloom. It's cold in here. Flare your lantern (${this.keyLabel("flare")}) to burn it away.`);
    if (this.gloomT > gl.grace && this.player.hp > gl.floorHp) {
      this.player.hp = Math.max(gl.floorHp, this.player.hp - gl.drainPerSecond * (0.5 + depth) * dt);
    }
  }

  /** Is this spot under a Gloom pocket (gathering waits until it's burnt off)? */
  shrouded(at: THREE.Vector3): boolean {
    return this.gloom.some((g) => g.covers(at));
  }

  keyLabel(action: Action): string {
    return keyName(this.input.bindings[action][0] ?? "?");
  }

  private tellOnce(key: string, text: string): void {
    const k = `${this.state.location}:${key}`;
    if (this.toldOnce.has(k)) return;
    this.toldOnce.add(k);
    this.hud.toast(text, "info", 5);
  }

  /** Captions setting: the sound's text, and which side it came from. */
  private caption(text: string, at?: THREE.Vector3): void {
    if (!this.state.settings.captions || this.mode === "loading") return;
    let side: "left" | "right" | "behind" | null = null;
    if (at && at.distanceTo(this.player.position) > 2.5) {
      const a = this.screenAngle(at);
      side = Math.abs(a) > 2.2 ? "behind" : a < -0.5 ? "left" : a > 0.5 ? "right" : null;
    }
    this.hud.caption(text, side);
  }

  private weapon(): GearId {
    let best: GearId = "boltcaster_mk1";
    for (const g of this.state.gear) if (GEAR[g].slot === "weapon" && GEAR[g].tier > GEAR[best].tier) best = g;
    return best;
  }

  private dashMax(): number {
    return skillLevel(this.state, "combat") >= 5 ? 2 : 1;
  }

  private maxHpNow(): number {
    return maxHp(this.state) + (this.buffs.maxHpT > 0 ? this.buffs.maxHp : 0);
  }

  private addShake(amount: number): void {
    this.shake = Math.min(1, this.shake + amount);
  }

  /** Screen angle of a world point, for HUD arcs and pips: 0 ahead, positive clockwise (to the right). */
  private screenAngle(at: THREE.Vector3): number {
    const dx = at.x - this.player.position.x;
    const dz = at.z - this.player.position.z;
    return -wrap(Math.atan2(-dx, -dz) - this.player.yaw);
  }

  hurtPlayer(amount: number, from: THREE.Vector3 | null): void {
    const p = this.player;
    if (this.mode !== "playing" || p.invulnerable > 0 || p.hp <= 0) return;
    p.hp -= amount;
    p.invulnerable = 0.2;
    this.sfx.hurt();
    this.addShake(Math.min(0.6, 0.15 + amount * 0.02));
    const far = from !== null && Math.hypot(from.x - p.position.x, from.z - p.position.z) > 0.2;
    this.hud.damageFrom(from && far ? this.screenAngle(from) : null);
    this.bus.emit("player:damaged", { amount, fromDirection: from ? { x: from.x - p.position.x, z: from.z - p.position.z } : null });
  }

  private defeat(): void {
    const lost = applyDeathLoss(this.state);
    this.bus.emit("player:defeated", { lost });
    this.pendingSummary = {
      kind: "summary",
      title: "The tide carries you home",
      sub: lost.length
        ? "You wake on the shingle below the lighthouse. Some of what you carried is gone. Everything in the chest is safe."
        : "You wake on the shingle below the lighthouse. Nothing was lost.",
      gained: [],
      lost,
      xp: this.trip?.xp ?? {},
      kills: this.trip?.kills ?? 0,
    };
    this.trip = null;
    this.sfx.hurt();
    this.beginTransition({ to: "home", via: "defeat", title: "The tide carries you home", sub: "", color: "#0b1d26", outTime: 1.4, hold: 1.2 });
  }

  // -------------------------------------------------------------- food

  private foodChoices(): ItemId[] {
    const out: ItemId[] = [];
    for (const st of this.state.satchel) if (st && ITEMS[st.item].food && !out.includes(st.item)) out.push(st.item);
    return out;
  }

  private currentFood(): ItemId | null {
    const choices = this.foodChoices();
    const pick = this.state.foodSlot;
    return pick && choices.includes(pick) ? pick : (choices[0] ?? null);
  }

  private updateFood(dt: number): void {
    this.eatT = Math.max(0, this.eatT - dt);
    if (this.healLeft > 0) {
      const h = Math.min(this.healLeft, this.healRate * dt);
      this.player.hp = Math.min(this.player.maxHp, this.player.hp + h);
      this.healLeft -= h;
    }
    if (this.input.pressed("cycleFood")) {
      const choices = this.foodChoices();
      const cur = this.currentFood();
      if (choices.length > 1 && cur) {
        this.state.foodSlot = choices[(choices.indexOf(cur) + 1) % choices.length]!;
        this.sfx.ui();
      } else if (!choices.length) this.hud.toast("No food packed. Cook at the hearth.", "info");
    }
    if (this.input.pressed("eat")) this.eat();
  }

  private eat(): void {
    const item = this.currentFood();
    if (!item) {
      this.hud.toast("No food packed. Cook at the hearth.", "info");
      this.sfx.denied();
      return;
    }
    if (this.eatT > 0) return;
    const food = ITEMS[item].food!;
    if (this.player.hp >= this.player.maxHp && !food.buff) {
      this.hud.toast("You're not hurt.", "info", 1.4);
      return;
    }
    removeAvailable(this.state, item, 1);
    this.state.foodSlot = item;
    this.eatT = BALANCE.player.eatSeconds;
    this.healLeft += food.heal;
    this.healRate = Math.max(this.healRate, food.heal);
    this.sfx.eat();
    if (food.buff?.kind === "max_hp") {
      this.buffs.maxHp = food.buff.amount;
      this.buffs.maxHpT = food.buff.seconds;
      this.hud.toast(`+${food.buff.amount} max health for ${Math.round(food.buff.seconds / 60)} minutes`, "milestone", 3);
    } else if (food.buff?.kind === "dash_cooldown") {
      this.buffs.dash = food.buff.amount;
      this.buffs.dashT = food.buff.seconds;
      this.hud.toast(`Quicker dashes for ${Math.round(food.buff.seconds / 60)} minutes`, "milestone", 3);
    }
  }

  private updateBuffs(dt: number): void {
    const b = this.buffs;
    if (b.maxHpT > 0) {
      b.maxHpT -= dt;
      if (b.maxHpT <= 0) this.hud.toast("The chowder's warmth fades.", "info");
    }
    if (b.dashT > 0) {
      b.dashT -= dt;
      if (b.dashT <= 0) this.hud.toast("Your legs feel heavy again.", "info");
    }
  }

  // ------------------------------------------------------------ travel

  /** "Set out" on the chart. The click lets us grab the mouse now; the fade takes a while. */
  private setOut(to: LocationId): void {
    this.menus.close();
    this.setMode("playing");
    this.relock();
    this.travel(to, "boat");
  }

  private travel(to: LocationId, via: Via): void {
    const sub = to === "home" ? "You row home under the beam." : "You row out past the breakers.";
    this.beginTransition({ to, via, title: LOCATIONS[to].name, sub, color: "#05090c", outTime: 0.7, hold: 0.9 });
  }

  private beginTransition(o: Omit<Transition, "t" | "phase" | "loaded">): void {
    this.fishing?.stop();
    this.gatherNode = null;
    this.gatherT = 0;
    this.hud.closeDialogue();
    this.transition = { ...o, t: 0, phase: "out", loaded: false };
    this.setMode("travel");
  }

  private updateTransition(dt: number): void {
    const tr = this.transition;
    if (!tr) return;
    tr.t += dt;
    if (tr.phase === "out") {
      const k = Math.min(1, tr.t / tr.outTime);
      const card = k > 0.6;
      this.hud.fade(k, tr.color, card ? tr.title : "", card ? tr.sub : "");
      if (k < 1) return;
      tr.phase = "load";
      tr.t = 0;
      if (tr.to === null) {
        if (tr.move) this.player.spawn(tr.move.position, tr.move.yaw);
        tr.loaded = true;
      } else {
        this.enter(tr.to, tr.via).then(
          () => (tr.loaded = true),
          (err: unknown) => {
            console.error("[travel] failed to enter", tr.to, err);
            tr.loaded = true;
          },
        );
      }
    } else if (tr.phase === "load") {
      if (tr.loaded && tr.t >= tr.hold) {
        tr.phase = "in";
        tr.t = 0;
      }
    } else {
      const k = Math.min(1, tr.t / 0.9);
      this.hud.fade(1 - k, tr.color, tr.title, tr.sub);
      if (k < 1) return;
      this.hud.fade(0);
      this.transition = null;
      this.setMode("playing");
      if (this.pendingSummary) {
        const m = this.pendingSummary;
        this.pendingSummary = null;
        this.openMenu(m);
      } else if (this.input.lookMode === "captured" && !this.input.locked) this.setMode("paused", "Click to resume");
    }
  }

  /** Swaps the world to `to` and puts the player where `via` says. */
  private async enter(to: LocationId, via: Via): Promise<void> {
    this.unloadLevel();
    let level: Level = this.home;
    if (to !== "home") {
      const loaded = await loadLevel(to, this.assets);
      if (loaded) level = loaded;
      else this.hud.toast(`${LOCATIONS[to].name} hasn't been built yet. Back home for now.`, "warn", 5);
    }
    this.level = level;
    this.state.location = level.id;
    this.scene.add(level.root);
    this.horizon = new Horizon(this.assets, level.id);
    this.scene.add(this.horizon.root);
    this.gulls = new Gulls(this.assets, level, level.collider);
    this.gulls.onCall = (at, alarm) => this.sfx.gull(at, alarm);
    this.scene.add(this.gulls.root);
    this.flagsKey = "";
    this.refreshWorld();
    this.heights = new LevelHeights(level.collider);
    this.water.setHeights(this.heights);
    this.rain.setHeights(this.heights);

    let at = level.spawn;
    let yaw = level.spawnYaw;
    if (level === this.home) {
      // Off the boat at the jetty; washed up on the beach; otherwise by the lighthouse door.
      const jetty = this.state.projects.includes("jetty");
      const sp = this.home.spawnFor(via === "boat" && jetty ? "jetty" : via === "boat" || via === "defeat" ? "landing" : "start");
      [at, yaw] = [sp.position, sp.yaw];
    } else if (level instanceof GlbLevel && via === "path") {
      const sp = level.spawnFor("path");
      [at, yaw] = [sp.position, sp.yaw];
    }
    this.player.spawn(at, yaw);
    this.lastYaw = yaw;
    this.lastPitch = 0;

    this.gloom = level.gloom.map((m) => new GloomPocket(m.position, m.radius));
    for (const g of this.gloom) this.scene.add(g.root);
    this.gloomT = 0;
    // Wreckage is the hook's; everything else (crates, fishing, the lens) is E's.
    this.nodes = level.nodes.filter((m) => NODES[m.node].kind !== "wreckage").map((m) => new GatherNode(m.node, m, this));
    this.wrecks = level.nodes.filter((m) => NODES[m.node].kind === "wreckage").map((m) => new Wreck(m.node, m, this, level === this.home));
    this.wreckBatch = Wreck.drawMerged(this.wrecks, this.scene);
    this.flotsam = level === this.home ? new Flotsam(this, level.points) : null;
    this.encounters = new Encounters(level.enemies);
    this.encounters.sync(this);
    this.inside.clear();

    const homeLight = level.points.get("home_light");
    if (homeLight) {
      this.distant = new DistantLight(homeLight, STAGES[this.state.stage]!.visuals);
      this.scene.add(this.distant.rig.pivot);
    }
    this.placeBeacon(this.state.flags.includes("chapter1_complete"));

    if (level === this.home) {
      this.player.hp = this.maxHpNow();
      const news = this.homecoming();
      this.flotsam?.arrive(this);
      const t = this.trip;
      if (t && via !== "defeat" && (t.gained.size || t.kills || Object.keys(t.xp).length)) {
        const gained = [...t.gained].map(([item, qty]) => ({ item, qty }));
        const unbanked = this.state.satchel.some((st) => st && ITEMS[st.item].category !== "food");
        const step = currentStep(this.state);
        const ready = step && stepMaterials(this.state).length > 0 && stillNeeded(this.state).length === 0 ? step.title : null;
        const bank = unbanked ? "Put your haul in the storage chest to keep it safe." : "The light is still burning.";
        this.pendingSummary = {
          kind: "summary",
          title: "Home again",
          sub: [news, ready ? `You have everything for ${ready}. ${bank}` : bank].filter(Boolean).join(" "),
          gained,
          lost: [],
          xp: t.xp,
          kills: t.kills,
        };
      } else if (news) this.hud.toast(news, "milestone", 6);
      this.trip = null;
    } else {
      if (!this.trip) this.trip = { gained: new Map(), xp: {}, kills: 0 };
      // The cove keeps catching drift while you're out (homecoming()).
      this.state.leftHomeAt ??= this.state.tide.elapsed;
    }

    if (this.everStarted) this.sfx.setAmbience(level.id);
    this.bus.emit("travel:arrived", { location: level.id });
    this.save();
    await this.prewarm();
  }

  /**
   * Compiles every shader the place can show while the travel card is still up.
   * Otherwise each new material, and every lit material whenever the number of
   * lights changes, compiles the first time it's drawn: a long frame mid-play.
   */
  private async prewarm(): Promise<void> {
    this.camera.position.copy(this.player.eye);
    const extras = new THREE.Group();
    extras.add(...this.projectiles.samples(), ...this.loot.samples(), ...this.effects.samples());
    this.scene.add(extras);
    try {
      await this.renderer.compileAsync(this.scene, this.camera);
      if (this.viewmodel) await this.renderer.compileAsync(this.viewmodel.scene, this.viewmodel.camera);
    } catch (err: unknown) {
      console.warn("[prewarm] shaders will compile on first use instead.", err);
    } finally {
      extras.removeFromParent();
    }
  }

  private unloadLevel(): void {
    this.fishing?.stop();
    for (const n of this.nodes) n.dispose();
    this.nodes = [];
    for (const w of this.wrecks) w.dispose();
    this.wrecks = [];
    this.wreckBatch?.dispose();
    this.wreckBatch = null;
    this.flotsam?.dispose();
    this.flotsam = null;
    this.hook?.reset();
    this.building = null;
    this.home.decor?.showGhost(null);
    this.encounters.clear();
    this.projectiles.clear();
    this.loot.clear();
    this.effects.clear();
    this.prompt = null;
    this.relight = null;
    this.hud.closeDialogue();
    if (this.level === this.home) this.home.root.removeFromParent();
    else this.level.dispose();
    this.distant?.rig.pivot.removeFromParent();
    this.distant = null;
    this.beacon?.pivot.removeFromParent();
    this.beacon = null;
    this.horizon?.dispose();
    this.horizon = null;
    this.gulls?.dispose();
    this.gulls = null;
    this.water.setHeights(null);
    this.rain.setHeights(null);
    this.heights?.dispose();
    this.heights = null;
    for (const g of this.gloom) g.dispose();
    this.gloom = [];
  }

  // ----------------------------------------------- stations and menus

  private craftRecipe(id: string, times: number): void {
    const r = getRecipe(id);
    if (!r) return;
    let made = 0;
    this.tracked(() => {
      for (let i = 0; i < times && craft(this.state, r).ok; i++) made++;
    });
    if (!made) {
      this.sfx.denied();
      return;
    }
    this.sfx.craft();
    if (r.output.kind === "gear") this.hud.toast(`New gear: ${GEAR[r.output.gear].name}`, "milestone");
    else this.hud.toast(`+${r.output.qty * made} ${ITEMS[r.output.item].name}`, "gain");
    this.afterAction();
  }

  /** "Add materials" at a plot: whatever you have toward it goes in, and it rises that much further. */
  private build(p: ProjectId): void {
    const d = this.tracked(() => deliver(this.state, p));
    if (!d.given.length) {
      this.sfx.denied();
      return;
    }
    this.afterAction();
    const plot = this.home.plots.get(p);
    this.sfx.craft();
    if (plot) this.effects.burst(plot.workPoint(), FX_COLORS.smoke, 36);
    if (!d.finished) {
      this.hud.toast(`${PROJECTS[p].name}: ${Math.floor(buildProgress(this.state, p) * 100)}% rebuilt`, "info");
      return;
    }
    this.sfx.upgrade();
    this.closeMenu();
    this.hud.banner(`${PROJECTS[p].name}\n${PROJECTS[p].perk}`, 6);
    if (plot) this.effects.burst(plot.centre().add(new THREE.Vector3(0, 1, 0)), FX_COLORS.amber, 60);
  }

  private upgradeLighthouse(): void {
    const done = this.tracked(() => advanceStage(this.state, "home"));
    if (!done) {
      this.sfx.denied();
      return;
    }
    this.sfx.upgrade();
    this.closeMenu();
    this.bus.emit("lighthouse:stage", { stage: done.index });
    this.afterAction();
  }

  private deposit(): void {
    const moved = depositAll(this.state);
    if (moved.length) {
      this.sfx.pickup();
      this.bus.emit("items:deposited", { stacks: moved });
    }
    this.afterAction();
  }

  private storeSlot(slot: number): void {
    const st = this.state.satchel[slot];
    if (!st) return;
    this.state.storage[st.item] = stored(this.state, st.item) + st.qty;
    this.state.satchel[slot] = null;
    this.afterAction();
  }

  private takeItem(item: ItemId): void {
    const have = stored(this.state, item);
    if (have <= 0) return;
    const fit = addItem(this.state, item, have);
    if (fit <= 0) {
      this.hud.toast("Satchel full.", "warn");
      this.sfx.denied();
      return;
    }
    this.state.storage[item] = have - fit;
    this.afterAction();
  }

  private applySettings(save = true): void {
    const st = this.state.settings;
    this.sfx.setVolume(st.volume);
    this.post.setBloom(st.bloom);
    this.projectiles.setContrast(st.contrastShots);
    this.hud.setReducedMotion(st.reducedMotion);
    this.input.setBindings(st.bindings);
    const labels = {} as KeyLabels;
    for (const a of ACTIONS) labels[a] = keyName(effectiveBindings(st.bindings)[a][0]!);
    this.hud.setKeys(labels);
    if (save) this.save();
  }

  private resetSave(): void {
    this.resetting = true;
    this.saves.reset();
    location.reload();
  }

  private tideLine(): string {
    const t = this.tide;
    const left = fmt(t.phaseTimeLeft);
    switch (t.phase) {
      case "low":
        return `Low tide. The water rises in ${left}. The flats and the wreck's hull are open.`;
      case "rising":
        return `The tide is rising. High water in ${left}.`;
      case "high":
        return `High tide. The water falls in ${left}. The high-water creatures are out.`;
      case "falling":
        return `The tide is falling. Low water in ${left}.`;
    }
  }

  // ----------------------------------------------- the beacon (chapter end)

  private relightBeacon(): void {
    const done = this.tracked(() => advanceStage(this.state, "beacon"));
    if (!done) {
      this.sfx.denied();
      return;
    }
    if (!this.state.flags.includes("chapter1_complete")) this.state.flags.push("chapter1_complete");
    this.relight = { t: 0 };
    this.lightBeacon();
    this.sfx.upgrade();
    this.sfx.horn();
    this.addShake(0.4);
    this.bus.emit("lighthouse:stage", { stage: done.index });
    this.afterAction();
  }

  /**
   * The outlying beacon's lamp and beam go in when you arrive, dark until it's
   * relit: adding their lights at the relight would make every material in view
   * recompile at the very moment the beam fires.
   */
  private placeBeacon(lit: boolean): void {
    const at = this.level.points.get("beacon_lamp");
    if (!at) return;
    this.beacon = new BeamRig({ lights: true, lampRadius: 1.2 });
    this.beacon.pivot.position.copy(at);
    const look = stageLook(STAGES[3]!.visuals);
    this.beacon.setLook(lit ? look : { ...look, intensity: 0 });
    this.scene.add(this.beacon.pivot);
  }

  private lightBeacon(): void {
    const at = this.level.points.get("beacon_lamp");
    if (!at || !this.beacon) return;
    this.beacon.setLook(stageLook(STAGES[3]!.visuals));
    this.effects.burst(at, FX_COLORS.amber, 140);
    this.effects.ring(at.clone(), FX_COLORS.amber, 0.5, 14, 1.4, 0.8);
  }

  private updateRelight(dt: number): void {
    const r = this.relight;
    if (!r) return;
    r.t += dt;
    if (r.t < 2.5) return;
    if (r.t < 9) {
      this.hud.fade(Math.min(0.82, (r.t - 2.5) * 0.6), "#05090c", "Chapter One complete", CHAPTER_SUB);
      return;
    }
    const k = Math.min(1, (r.t - 9) / 1.2);
    this.hud.fade(0.82 * (1 - k), "#05090c", "Chapter One complete", CHAPTER_SUB);
    if (k >= 1) {
      this.hud.fade(0);
      this.relight = null;
    }
  }

  // ------------------------------------------------- GameContext helpers

  give(item: ItemId, qty: number, from?: THREE.Vector3): number {
    const def = ITEMS[item];
    const fit = addItem(this.state, item, qty);
    if (fit > 0) {
      this.hud.toast(`+${fit} ${def.name}`, def.category === "key" ? "milestone" : "gain");
      if (this.trip && def.category !== "key") this.trip.gained.set(item, (this.trip.gained.get(item) ?? 0) + fit);
      if (from) this.loot.burst(from, fit);
      this.sfx.pickup();
      this.bus.emit("items:gained", { stacks: [{ item, qty: fit }] });
      this.checkReady();
    }
    if (fit < qty) this.hud.toast(`Satchel full: ${qty - fit} ${def.name} left behind`, "warn");
    return fit;
  }

  xp(skill: SkillId, amount: number): void {
    this.tracked(() => addXp(this.state, skill, amount));
    if (this.trip) this.trip.xp[skill] = (this.trip.xp[skill] ?? 0) + amount;
    this.bus.emit("skill:xp", { skill, amount });
  }

  /** Runs `fn` and announces any skill levels it crossed. */
  private tracked<T>(fn: () => T): T {
    const before = SKILL_IDS.map((k) => skillLevel(this.state, k));
    const out = fn();
    SKILL_IDS.forEach((k, i) => {
      const was = before[i]!;
      const now = skillLevel(this.state, k);
      if (now <= was) return;
      const unlocked = SKILLS[k].milestones.filter((m) => m.level > was && m.level <= now).map((m) => m.text);
      this.bus.emit("skill:levelUp", { skill: k, level: now, unlocked });
    });
    return out;
  }

  /** After anything that changes progress: quest steps, world state, menus, save. */
  private afterAction(save = true): void {
    const done = advanceQuest(this.state);
    for (const step of done) this.hud.toast(`Task complete: ${step.title}`, "milestone");
    const next = currentStep(this.state);
    if (done.length && next) this.hud.toast(`New task: ${next.title}`, "info", 4);
    this.refreshWorld();
    this.menus.refresh();
    if (save) this.save();
  }

  /** Push progression into the world: home's plots, people, boats and beam; level gates; gear. */
  private refreshWorld(): void {
    const s = this.state;
    const visuals = STAGES[s.stage]!.visuals;
    const fog = LOCATIONS[s.location].fog;
    if (this.level === this.home) {
      this.home.applyProgress(s);
      this.sky.setFog(fog[0], visuals.fogFar);
    } else this.sky.setFog(fog[0], fog[1]);
    const key = s.flags.join();
    if (this.level instanceof GlbLevel && key !== this.flagsKey) {
      this.flagsKey = key;
      this.level.applyFlags(s.flags);
    }
    const hasLens = s.keyItems.includes("drowned_lens") || s.stage >= 2;
    for (const it of this.level.interacts) if (it.id === "rope_ladder") it.object.visible = hasLens;
    this.viewmodel?.equip(s.gear);
  }

  private save(): void {
    if (this.resetting) return;
    this.autosave = 0;
    this.saves.write(this.state);
  }

  // ------------------------------------------------------------ events

  private wireEvents(): void {
    this.bus.on("tide:warning", (e) => {
      this.hud.banner(e.turn === "rising" ? "The tide is turning\nThe water rises in a minute." : "The tide is turning\nThe water falls in a minute.", 5);
      this.sfx.horn();
    });
    this.bus.on("tide:turnStarted", (e) => {
      if (e.phase === "rising" && !LOCATIONS[this.state.location].safe) this.hud.toast("The water is rising. Get off the flats.", "warn", 4);
    });
    this.bus.on("tide:settled", (e) => this.hud.toast(e.state === "high" ? "High tide." : "Low tide. The flats are open.", "info"));
    this.bus.on("skill:levelUp", (e) => {
      this.hud.toast(`${SKILLS[e.skill].name} ${e.level}${e.unlocked.length ? ": " + e.unlocked.join(" ") : ""}`, "milestone", 5);
      this.sfx.levelUp();
    });
    this.bus.on("lighthouse:stage", (e) => {
      const s = STAGES[e.stage];
      if (s) this.hud.banner(`${s.name}\n${s.description}`, 6);
    });
    this.bus.on("enemy:killed", (e) => {
      if (this.trip) this.trip.kills++;
      if (!e.boss) return;
      this.hud.banner("The Wreck Guardian sinks\nThe way to the beacon is open.", 6);
      this.afterAction();
    });
    this.bus.on("node:keyItem", (e) => {
      if (e.item !== "drowned_lens") return;
      this.hud.banner("The Drowned Lens\nThe hull groans. Something stirs in the water.", 5);
      this.sfx.boom(e.at);
      this.addShake(0.5);
      // FX_ambush_<enemy id>_<n> points in the level say who comes for you.
      for (const [name, at] of this.level.points) {
        const id = /^ambush_(.+)_\d+$/.exec(name)?.[1];
        if (id && (ENEMY_IDS as readonly string[]).includes(id)) this.encounters.spawnAt(id as EnemyId, at, this);
      }
      this.afterAction();
    });
  }

  // ------------------------------------------------------------ render

  private render(frameDt: number): void {
    this.adaptResolution(frameDt);
    const p = this.player;
    const st = this.state.settings;
    const calm = st.reducedMotion;
    const eye = p.eye;
    if (!st.headBob || calm) eye.y -= p.bobOffset;
    if (calm) eye.y += p.landKick * 0.08;
    this.camera.position.copy(eye);
    let jx = 0;
    let jy = 0;
    if (this.shake > 0) {
      this.shake = Math.max(0, this.shake - frameDt * 2.2);
      if (st.screenShake && !calm) {
        const k = this.shake * this.shake * 0.06;
        jx = (Math.random() - 0.5) * k;
        jy = (Math.random() - 0.5) * k;
      }
    }
    // A dash widens the view and leans a touch into a sideways one.
    this.camera.rotation.set(p.pitch + jx, p.yaw + jy, calm ? 0 : -p.dashSide * 0.035);
    this.camera.fov = st.fov + (calm ? 0 : p.dashKick * 6);
    this.camera.updateProjectionMatrix();

    const rain = this.rainLevel();
    this.water.follow(eye.x, eye.z);
    this.water.update(this.time, this.tide.waterY, eye, rain);
    this.rain.update(this.time, eye, rain, this.tide.waterY);
    const covered = (this.heights?.rainFloor(eye.x, eye.z) ?? -Infinity) > eye.y + 0.2;
    this.sfx.setRain(rain, covered);
    this.swimVeil = THREE.MathUtils.damp(this.swimVeil, p.water === "swimming" ? 1 : 0, 5, frameDt);
    let gloom = 0;
    for (const g of this.gloom) gloom = Math.max(gloom, g.depthAt(p.position));
    this.gloomVeil = THREE.MathUtils.damp(this.gloomVeil, Math.min(1, gloom * 1.6), 3, frameDt);
    this.sfx.setMuffle(Math.max(this.swimVeil * 0.45, this.gloomVeil * 0.55));
    this.sky.sun.target.position.set(eye.x, 0, eye.z);
    this.sky.sun.position.set(eye.x - 60, 40, eye.z - 80);
    TIDE_UNIFORMS.uTideWaterY.value = this.tide.waterY;
    TIDE_UNIFORMS.uTideHighY.value = TIDE.highLevel;
    TIDE_UNIFORMS.uTideWarn.value = this.floodWarn;
    TIDE_UNIFORMS.uTideTime.value = this.time;
    this.sfx.setListener(eye, this.camera);

    const flicker = Math.sin(this.time * 13) * 0.5 + Math.sin(this.time * 31) * 0.5;
    // The Flare: the lantern blazes and throws its light much further for a moment.
    const flash = this.flareFlash * this.flareFlash * (calm ? 0.35 : 1);
    this.lantern.intensity = 5 + flicker * 0.5 + flash * 70;
    this.lantern.distance = 14 + flash * 18;
    if (this.viewmodel) {
      const k = 0.0022 * st.sensitivity;
      const dYaw = wrap(p.yaw - this.lastYaw);
      const dPitch = p.pitch - this.lastPitch;
      this.lastYaw = p.yaw;
      this.lastPitch = p.pitch;
      this.viewmodel.update(frameDt, {
        mouseDX: -dYaw / k,
        mouseDY: -dPitch / k,
        speed: Math.hypot(p.velocity.x, p.velocity.z),
        lowered: this.relight !== null,
        fishing: this.fishing?.active ?? false,
        aspect: this.camera.aspect,
        time: this.time,
        lanternFlicker: flicker,
        calm,
      });
    }
    this.post.render(frameDt);

    this.hud.render(this.hudView(), frameDt);
  }

  /** 0..1 how hard it's raining here and now: each place has its own weather, and showers come and go. */
  private rainLevel(): number {
    if (!this.state.settings.rain || this.mode === "loading") return 0;
    const [p1, p2] = RAIN.period;
    const t = this.time;
    const w = THREE.MathUtils.clamp(0.5 + 0.35 * Math.sin((t * Math.PI * 2) / p1) + 0.15 * Math.sin((t * Math.PI * 2) / p2 + 1.3), 0, 1);
    const [lo, hi] = RAIN.swing;
    return LOCATIONS[this.state.location].rain * (lo + (hi - lo) * w);
  }

  private hudView(): HudView {
    const s = this.state;
    const p = this.player;
    const step = currentStep(s);
    const loc = LOCATIONS[s.location];
    const food = this.currentFood();
    const boss = this.encounters.boss;
    let haul: number | null = null;
    if (this.trip) {
      haul = 0;
      for (const q of this.trip.gained.values()) haul += q;
    }
    const playing = this.mode === "playing";
    return {
      tide: this.tide,
      objective: step ? { title: step.title, hint: step.hint } : null,
      checklist: stepMaterials(s).map((x) => {
        const have = available(s, x.item);
        return have < x.qty ? { ...x, have, where: this.whereToFind(x.item) } : { ...x, have };
      }),
      hp: p.hp,
      maxHp: p.maxHp,
      dashCharges: p.dashCharges,
      dashMax: this.dashMax(),
      dashRecharge: p.dashRechargeFraction,
      prompt: playing ? (this.prompt?.text ?? null) : null,
      promptBlocked: this.prompt?.blocked ?? false,
      ...(this.prompt?.key ? { promptKey: this.prompt.key } : {}),
      reticle: playing ? this.reticle() : null,
      build: this.building
        ? {
            slots: DECOR_IDS.map((id) => ({ name: DECOR[id].name, cost: DECOR[id].cost.map((c) => `${c.qty} ${ITEMS[c.item].name}`).join(" · "), afford: hasAll(this.state, DECOR[id].cost) })),
            selected: this.building.index,
          }
        : null,
      locationName: loc.name,
      safe: loc.safe,
      food: food ? { name: ITEMS[food].name, count: carried(s, food) } : null,
      satchel: { used: s.satchel.filter(Boolean).length, cap: satchelCapacity(s) },
      haul,
      gather: this.gatherNode ? Math.min(1, this.gatherT / Math.max(0.01, this.gatherNode.holdTime(this))) : null,
      compass: this.mode === "loading" ? null : { yaw: p.yaw, markers: this.compassMarkers() },
      boss: boss && boss.alive && boss.awake ? { name: ENEMIES.wreck_guardian.name, frac: boss.hp / boss.def.hp, exposed: boss.heartExposed } : null,
      threats: this.encounters
        .threats()
        .map((t) => ({ angle: this.screenAngle(t.position), level: t.level }))
        .filter((t) => Math.abs(t.angle) > 0.55),
      flare: this.flareCharge,
      gloom: this.gloomVeil * 0.85,
      swim: this.swimVeil * 0.9,
    };
  }

  private compassMarkers(): CompassMarker[] {
    const out: CompassMarker[] = [];
    const p = this.player.position;
    const add = (at: THREE.Vector3 | undefined, label: string, kind: CompassMarker["kind"]) => {
      if (!at) return;
      const dx = at.x - p.x;
      const dz = at.z - p.z;
      const dist = Math.hypot(dx, dz);
      if (dist > 2) out.push({ yaw: Math.atan2(-dx, -dz), label, kind, dist });
    };
    const where = (id: string) => {
      const it = this.level.interacts.find((i) => i.id === id);
      return it && shown(it.object) ? it.object.getWorldPosition(new THREE.Vector3()) : undefined;
    };
    if (this.level !== this.home) {
      add(where("boat"), "Boat", "landing");
    }
    const obj = this.objective();
    if (obj) add(obj.at, obj.label, "objective");
    return out;
  }

  /** Where the current quest step points, if it's in this location. */
  private objective(): { at: THREE.Vector3; label: string } | null {
    const s = this.state;
    const step = currentStep(s);
    if (!step) return null;
    const find = (id: string) => this.level.interacts.find((i) => i.id === id)?.object.getWorldPosition(new THREE.Vector3());
    const pt = (at: THREE.Vector3 | undefined, label: string) => (at ? { at, label } : null);
    const here = s.location;
    const g = step.goal;
    if (g.kind === "talk") return here === "home" ? pt(find(`npc:${g.npc}`), NPCS[g.npc].name) : null;
    if (step.id === "feed") {
      if (here !== "home") return null;
      if (available(s, "silverfin") >= 1) return pt(find("hearth"), "Hearth");
      const spot = this.nodes.find((n) => n.kind === "fish_silverfin" && n.available);
      return spot ? pt(spot.position, "Fishing spot") : null;
    }
    if (g.kind === "salvage") return here === "home" ? this.cove() : null;
    if (g.kind === "project" || g.kind === "stage") {
      if (g.kind === "stage" && STAGES[g.stage]!.performedAt === "beacon") {
        if (here === "beacon") return s.flags.includes("guardian_defeated") ? pt(find("beacon"), "Beacon") : pt(this.level.points.get("arena"), "Beacon rock");
        return here === "home" ? pt(find("boat"), "Boat") : null;
      }
      if (here !== "home") return stillNeeded(s).length === 0 ? this.wayHome() : (this.nearestSource() ?? this.wayHome());
      // A plot takes whatever you have toward it, so it's where to go while you have any.
      if (g.kind === "project") {
        if (remaining(s, g.project).some((st) => available(s, st.item) > 0)) return pt(find(`plot:${g.project}`), PROJECTS[g.project].name);
      } else if (isMet(missingFor(s, STAGES[g.stage]!.requires))) return pt(find("lamp"), "Lighthouse");
      return this.wayOut();
    }
    if (g.kind === "keyItem") {
      if (here === "wreck") {
        const lens = this.nodes.find((n) => n.def.keyItem === g.item && n.available);
        return lens ? pt(lens.position, "Chart room") : null;
      }
      return here === "home" ? pt(find("boat"), "Boat") : null;
    }
    return null;
  }

  /** Out on a trip: the nearest node that still gives something the step needs. */
  private nearestSource(): { at: THREE.Vector3; label: string } | null {
    const want = new Set(stillNeeded(this.state).map((s) => s.item));
    if (!want.size) return null;
    let best: { at: THREE.Vector3; label: string } | null = null;
    let bestD = Infinity;
    const consider = (at: THREE.Vector3, label: string, ok: boolean, gives: readonly { item: ItemId }[]) => {
      if (!ok || !gives.some((y) => want.has(y.item))) return;
      const d = at.distanceToSquared(this.player.position);
      if (d < bestD) [best, bestD] = [{ at, label }, d];
    };
    for (const n of this.nodes) consider(n.position, n.def.name, n.obtainable(this), n.def.yields);
    for (const w of this.wrecks) consider(w.at, w.name, w.obtainable(this), w.def.yields);
    return best;
  }

  /** The way back from a trip: the boat. */
  private wayHome(): { at: THREE.Vector3; label: string } | null {
    const it = this.level.interacts.find((i) => i.id === "boat");
    return it && shown(it.object) ? { at: it.object.getWorldPosition(new THREE.Vector3()), label: "Home" } : null;
  }

  /** The nearest drift you could take, or the beach it comes in on. */
  private cove(): { at: THREE.Vector3; label: string } {
    let best: Piece | null = null;
    let bestD = Infinity;
    for (const p of this.flotsam?.pieces ?? []) {
      const d = p.at.distanceToSquared(this.player.position);
      if (p.live && d < bestD) [best, bestD] = [p, d];
    }
    return best ? { at: best.at, label: best.name } : { at: this.home.spawnFor("landing").position, label: "The cove" };
  }

  /** At home with materials still to find: the cove if the drift brings them, else the boat toward the nearest place that has them. */
  private wayOut(): { at: THREE.Vector3; label: string } | null {
    const missing = stillNeeded(this.state)[0];
    if (!missing) return null;
    const from = sourcesOf(this.state, missing.item);
    if (from.includes("home")) return this.cove();
    const to = from[0];
    if (!to) return null;
    const it = this.level.interacts.find((i) => i.id === "boat");
    return it && shown(it.object) ? { at: it.object.getWorldPosition(new THREE.Vector3()), label: LOCATIONS[to].name } : null;
  }

  /** Where to look for an item the step still needs: the cove, "here", or the nearest place that has it. */
  private whereToFind(item: ItemId): string | undefined {
    const from = sourcesOf(this.state, item);
    if (this.state.location === "home" && driftGives(item)) return "the cove";
    if (from.includes(this.state.location)) return "here";
    const to = from[0];
    return to ? LOCATIONS[to].name : undefined;
  }

  /** Says so the moment you're carrying everything the current step needs (once per step). */
  private checkReady(): void {
    const step = currentStep(this.state);
    if (!step || this.readyTold === step.id || this.state.location === "home") return;
    if (!stepMaterials(this.state).length || stillNeeded(this.state).length) return;
    this.readyTold = step.id;
    this.hud.toast(`You have everything for ${step.title}. Take it home.`, "milestone", 6);
  }

  /** The prologue on a new game: one card at a time; a click or a key moves it on. */
  private updateStory(dt: number): void {
    const st = this.story!;
    st.t += dt;
    this.input.consumeMouse();
    const i = this.input;
    const next = st.t > 0.6 && (i.pressed("fire") || i.pressed("jump") || i.pressed("interact") || i.pressed("dash"));
    if (next || st.t > PROLOGUE_CARD_SECONDS) {
      st.i++;
      st.t = 0;
    }
    const card = PROLOGUE[st.i];
    if (!card) {
      this.story = null;
      this.hud.story(null);
      return;
    }
    if (st.shown !== st.i) {
      st.shown = st.i;
      this.hud.story(card, st.i, PROLOGUE.length);
    }
  }

  private onResize(): void {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.post.setSize(window.innerWidth, window.innerHeight);
  }

  /**
   * Draws fewer pixels when frames run slow and creeps back up when there's
   * room (Auto), or holds the share the player picked. Only normal play counts:
   * menus, cards and loading hitches say nothing about the frame rate.
   */
  private adaptResolution(frameDt: number): void {
    const fixed = this.state.settings.renderScale;
    if (fixed > 0) {
      this.setRenderScale(fixed);
      this.autoRes.startFrom(fixed);
      return;
    }
    if (this.mode !== "playing") return;
    const next = this.autoRes.frame(frameDt);
    if (next !== null) this.setRenderScale(next);
  }

  private setRenderScale(scale: number): void {
    if (Math.abs(scale - this.renderScale) < 1e-3) return;
    this.renderScale = scale;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2) * scale);
    this.post.setSize(window.innerWidth, window.innerHeight);
  }

  // ------------------------------------------------------------- debug

  /** Dev-only console helpers, e.g. __ll.give("timber", 20), __ll.go("wreck"), __ll.stage(2). */
  private exposeDebug(): void {
    const api = {
      game: this,
      give: (item: ItemId, qty = 10) => {
        addItem(this.state, item, qty);
        this.afterAction();
      },
      gear: (g: GearId) => {
        if (!this.state.gear.includes(g)) this.state.gear.push(g);
        this.afterAction();
      },
      xp: (skill: SkillId, amount = 500) => this.xp(skill, amount),
      stage: (n: StageIndex) => {
        this.state.stage = n;
        this.afterAction();
      },
      flag: (f: FlagId) => {
        if (!this.state.flags.includes(f)) this.state.flags.push(f);
        this.afterAction();
      },
      project: (p: ProjectId) => {
        if (!this.state.projects.includes(p)) this.state.projects.push(p);
        this.afterAction();
      },
      tide: (seconds: number) => (this.state.tide.elapsed += seconds),
      go: (to: LocationId, via: Via = "boat") => this.travel(to, via),
      heal: () => (this.player.hp = this.player.maxHp),
      /** Tops up what a plot still needs and hands it in: it rises and stands. */
      build: (p: ProjectId) => {
        for (const st of remaining(this.state, p)) this.state.storage[st.item] = stored(this.state, st.item) + st.qty;
        this.build(p);
      },
      /** A piece of drift partway in through the cove mouth. */
      flotsam: (id: FlotsamId = "planks") => this.flotsam?.spawn(id, undefined, 30, this.tide.waterY) ?? null,
      tp: (x: number, y: number, z: number) => this.player.spawn(new THREE.Vector3(x, y, z), this.player.yaw),
      where: () => ({ x: +this.player.position.x.toFixed(2), y: +this.player.position.y.toFixed(2), z: +this.player.position.z.toFixed(2), yaw: +this.player.yaw.toFixed(3), mode: this.mode }),
      killAll: () => {
        for (const e of [...this.encounters.enemies]) e.hurt(99999, new THREE.Vector3(), false, this);
      },
      reset: () => this.resetSave(),
      /** The pacing simulation's run through the chapter, trip by trip (loaded on demand). */
      economy: async () => {
        const { describePlan, planChapter } = await import("../systems/economy");
        console.log(describePlan(planChapter()));
      },
    };
    (window as unknown as { __ll: typeof api }).__ll = api;
  }
}

/** Visible all the way up its parent chain (hidden NPCs, ladders, gated objects). */
function shown(o: THREE.Object3D): boolean {
  for (let p: THREE.Object3D | null = o; p; p = p.parent) if (!p.visible) return false;
  return true;
}
