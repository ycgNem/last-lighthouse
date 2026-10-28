import * as THREE from "three";
import { createEnemy, type Enemy } from "../enemies";
import { WreckGuardian } from "../enemies/WreckGuardian";
import type { EnemyId, TideReq } from "../data/ids";
import type { EnemyMarker } from "../world/Level";
import type { GameContext } from "./Context";

// Spawns a location's enemies from its ENEMY_ markers, per tide. Low-tide
// creatures slip away when the water rises (unless they're mid-attack) and the
// high-tide ones arrive. Anything you kill stays dead until your next visit.

const matches = (req: TideReq, state: "low" | "high") => req === "any" || req === state;

export class Encounters {
  readonly enemies: Enemy[] = [];
  private readonly live = new Map<number, Enemy>();
  private readonly killed = new Set<number>();
  private tideState: "low" | "high" | null = null;

  constructor(private readonly markers: readonly EnemyMarker[]) {}

  get boss(): WreckGuardian | null {
    return (this.enemies.find((e) => e instanceof WreckGuardian) as WreckGuardian | undefined) ?? null;
  }

  sync(ctx: GameContext): void {
    const state = ctx.tide.state;
    if (state === this.tideState) return;
    this.tideState = state;
    this.markers.forEach((m, i) => {
      const want = matches(m.tide, state) && !this.killed.has(i);
      const have = this.live.get(i);
      if (want && !have) this.spawn(i, ctx);
      if (!want && have) have.retreating = true;
    });
  }

  private spawn(i: number, ctx: GameContext): void {
    const m = this.markers[i]!;
    if (m.enemy === "wreck_guardian" && ctx.state.flags.includes("guardian_defeated")) {
      this.killed.add(i);
      return;
    }
    const e = this.create(m.enemy, m.position, ctx);
    if (e instanceof WreckGuardian) {
      const arena = ctx.level.points.get("arena");
      if (arena) e.setArena(arena);
    }
    this.live.set(i, e);
  }

  /** An extra enemy outside the tide schedule (ambushes). It never comes back. */
  spawnAt(enemy: EnemyId, at: THREE.Vector3, ctx: GameContext): Enemy {
    return this.create(enemy, at, ctx);
  }

  private create(enemy: EnemyId, at: THREE.Vector3, ctx: GameContext): Enemy {
    const e = createEnemy(enemy, at, ctx.assets);
    this.enemies.push(e);
    ctx.scene.add(e.root);
    return e;
  }

  update(dt: number, ctx: GameContext): void {
    for (const e of this.enemies) e.update(dt, ctx);
    for (const [i, e] of this.live) {
      if (e.alive && e.retreating && e.canLeave()) e.leave(ctx);
      if (!e.alive) this.killed.add(i);
      if (e.gone) this.live.delete(i);
    }
    for (let k = this.enemies.length - 1; k >= 0; k--) {
      const e = this.enemies[k]!;
      if (!e.gone) continue;
      e.dispose();
      this.enemies.splice(k, 1);
    }
    ctx.projectiles.targets = this.enemies;
  }

  /** Enemies currently winding up an attack, for the HUD's threat pips. */
  threats(): { position: THREE.Vector3; level: number }[] {
    return this.enemies.filter((e) => e.alive && e.threat > 0.05).map((e) => ({ position: e.center(), level: e.threat }));
  }

  clear(): void {
    for (const e of this.enemies) e.dispose();
    this.enemies.length = 0;
    this.live.clear();
  }
}
