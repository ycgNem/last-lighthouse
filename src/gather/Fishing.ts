import * as THREE from "three";
import type { GameContext } from "../game/Context";
import { skillLevel } from "../systems/skills";
import type { GatherNode } from "./GatherNode";

// Cast, wait for the splash, press E inside the window. No bar-watching.

export type FishPhase = "cast" | "wait" | "bite" | "done";

export class Fishing {
  node: GatherNode | null = null;
  phase: FishPhase = "done";
  private t = 0;
  private waitFor = 0;
  private readonly bobber: THREE.Object3D;
  private readonly line: THREE.Line;
  private readonly from = new THREE.Vector3();

  constructor(ctx: GameContext) {
    this.bobber = ctx.assets.clone("viewmodels.glb", "VM_bobber") ?? new THREE.Mesh(new THREE.SphereGeometry(0.07, 8, 6), new THREE.MeshStandardMaterial({ color: 0xb03a2e }));
    this.bobber.visible = false;
    this.line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]), new THREE.LineBasicMaterial({ color: 0xdddddd, transparent: true, opacity: 0.6 }));
    this.line.visible = false;
    this.line.frustumCulled = false;
    ctx.scene.add(this.bobber, this.line);
  }

  get active(): boolean {
    return this.node !== null;
  }

  start(node: GatherNode, ctx: GameContext): void {
    this.node = node;
    this.phase = "cast";
    this.t = 0;
    const fast = skillLevel(ctx.state, "fishing") >= 7 ? 0.6 : 1;
    this.waitFor = (1.4 + Math.random() * 2.4) * fast;
    this.bobber.visible = true;
    this.line.visible = true;
    ctx.sfx.splash(node.position);
  }

  stop(): void {
    this.node = null;
    this.phase = "done";
    this.bobber.visible = false;
    this.line.visible = false;
  }

  /** Text for the HUD prompt while fishing. */
  prompt(): string {
    if (this.phase === "bite") return "Bite! Press E";
    if (this.phase === "wait") return "Waiting for a bite…";
    return "Casting…";
  }

  update(dt: number, ctx: GameContext, rodTip: THREE.Vector3): void {
    const node = this.node;
    if (!node) return;
    this.t += dt;
    const spot = node.position.clone().setY(ctx.tide.waterY);
    const tip = rodTip;
    if (this.phase === "cast") {
      const k = Math.min(1, this.t / 0.5);
      this.bobber.position.copy(tip).lerp(spot, k).add(new THREE.Vector3(0, Math.sin(k * Math.PI) * 2, 0));
      if (k >= 1) {
        this.phase = "wait";
        this.t = 0;
        ctx.effects.splash(spot, 6);
      }
    } else if (this.phase === "wait") {
      this.bobber.position.copy(spot).add(new THREE.Vector3(0, Math.sin(ctx.time * 3) * 0.02, 0));
      if (this.t >= this.waitFor) {
        this.phase = "bite";
        this.t = 0;
        ctx.effects.splash(spot, 22);
        ctx.sfx.fishBite();
      }
    } else if (this.phase === "bite") {
      this.bobber.position.copy(spot).add(new THREE.Vector3(0, -0.1 + Math.sin(ctx.time * 30) * 0.05, 0));
      const window = node.kind === "fish_glowgill" ? 0.8 : 1.1;
      if (ctx.input.pressed("interact")) {
        node.complete(ctx);
        ctx.effects.splash(spot, 14);
        this.stop();
        return;
      }
      if (this.t > window) {
        ctx.hud.toast("It got away.", "info");
        this.stop();
        return;
      }
    }
    this.from.copy(tip);
    const pos = this.line.geometry.attributes.position as THREE.BufferAttribute;
    pos.setXYZ(0, this.from.x, this.from.y, this.from.z);
    pos.setXYZ(1, this.bobber.position.x, this.bobber.position.y, this.bobber.position.z);
    pos.needsUpdate = true;
  }
}
