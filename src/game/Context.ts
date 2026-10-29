import type * as THREE from "three";
import type { Assets } from "../core/Assets";
import type { EventBus } from "../core/EventBus";
import type { Input } from "../core/Input";
import type { Action } from "../data/controls";
import type { ItemId, SkillId } from "../data/ids";
import type { PlayerController } from "../player/PlayerController";
import type { GameState } from "../state/GameState";
import type { TideReading } from "../systems/tide";
import type { Hud } from "../ui/Hud";
import type { Sfx } from "../audio/Sfx";
import type { Effects } from "../fx/Effects";
import type { Loot } from "../fx/Loot";
import type { Projectiles } from "../combat/Projectiles";
import type { Level } from "../world/Level";

/** What gameplay systems can reach. The Game implements it. */
export interface GameContext {
  readonly state: GameState;
  readonly bus: EventBus;
  readonly input: Input;
  readonly hud: Hud;
  readonly sfx: Sfx;
  readonly assets: Assets;
  readonly scene: THREE.Scene;
  readonly camera: THREE.PerspectiveCamera;
  readonly player: PlayerController;
  readonly effects: Effects;
  readonly loot: Loot;
  readonly projectiles: Projectiles;
  readonly level: Level;
  readonly tide: TideReading;
  readonly time: number;
  /** Adds items to the satchel with feedback. Returns how many fit. */
  give(item: ItemId, qty: number, from?: THREE.Vector3): number;
  xp(skill: SkillId, amount: number): void;
  hurtPlayer(amount: number, from: THREE.Vector3 | null): void;
  /** True where a Gloom pocket hangs (nothing there can be gathered until a Flare burns it off). */
  shrouded(at: THREE.Vector3): boolean;
  /** The key the player has bound to an action, for prompts ("Q"). */
  keyLabel(action: Action): string;
}
