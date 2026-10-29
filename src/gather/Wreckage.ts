import * as THREE from "three";
import { GEAR } from "../data/items";
import type { NodeId } from "../data/ids";
import { NODES, type NodeDef } from "../data/nodes";
import { FX_COLORS } from "../fx/Effects";
import type { GameContext } from "../game/Context";
import { hasGear } from "../systems/progression";
import { rollYields, roomFor, tearWreck, wreckLeft } from "../systems/salvage";
import { mergePieces, type PieceBatch } from "../world/Batch";
import type { NodeMarker } from "../world/Level";

// Wreckage the hook tears at: the cove's wreck field at home (bared at low
// water, and whole again every low tide) and the drift and scrap aboard the
// Meridian. Every pull tears a piece off and throws it to you. A wreck built in
// pieces (its *_piece_<n> children, tools/blender/build/props.py) loses them
// top first, down to its bones; one made in one piece shrinks as it goes, and
// is gone once it's spent. Wrecks in pieces are drawn merged, all of a place's
// together (Wreck.drawMerged()), so tearing a piece off only blanks its
// triangles.

const PIECE = /_piece_(\d+)$/;
const tmpV = new THREE.Vector3();

export class Wreck {
  readonly pull = "yank" as const;
  readonly def: NodeDef;
  readonly object: THREE.Object3D;
  /** Where the hook bites: high on the wreck. */
  readonly at = new THREE.Vector3();
  readonly radius: number;
  /** Something left to tear off. */
  live = true;
  private readonly pieces: THREE.Object3D[] = [];
  /** The place's wrecks drawn merged, and which one this is in it. */
  private batch: PieceBatch | null = null;
  private slot = -1;
  /** Its key in the save's cove.wrecks: home's wrecks keep count across visits, and restock with the tide. */
  private readonly key: string;
  private left: number;
  private shown = -1;
  private fade = 1;
  private readonly scale0: THREE.Vector3;
  private glintT = Math.random() * 3;
  private readonly owned: boolean;
  private shadowMeshes: THREE.Mesh[] | null = null;
  private shadowOn = true;

  constructor(
    readonly node: NodeId,
    marker: NodeMarker,
    ctx: GameContext,
    /** Home's wrecks: their count lives in the save. */
    private readonly persists: boolean,
  ) {
    this.def = NODES[node];
    this.owned = !marker.object;
    const obj = marker.object ?? ctx.assets.prop(node) ?? new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.6, 1.2), new THREE.MeshStandardMaterial({ color: 0x6a5642 }));
    if (this.owned) {
      obj.position.copy(marker.position);
      obj.rotation.y = marker.yaw;
      ctx.scene.add(obj);
    }
    this.object = obj;
    this.key = obj.name || `${node}@${marker.position.x.toFixed(1)},${marker.position.z.toFixed(1)}`;
    // Copies Blender places come numbered on the end ("boat_piece_2001"), and a
    // piece's own meshes are named after it too ("boat_piece_2"): the outermost
    // match is the piece, and the numbers still sort in order.
    const found: [number, THREE.Object3D][] = [];
    const collect = (o: THREE.Object3D) => {
      const m = PIECE.exec(o.name);
      if (m && o !== obj) found.push([Number(m[1]), o]);
      else for (const c of o.children) collect(c);
    };
    collect(obj);
    this.pieces = found.sort((a, b) => a[0] - b[0]).map(([, o]) => o);
    obj.updateWorldMatrix(true, true);
    const box = new THREE.Box3().setFromObject(obj);
    box.getCenter(this.at);
    this.at.y = Math.max(this.at.y, box.max.y - 0.35);
    this.radius = THREE.MathUtils.clamp(box.getSize(tmpV).length() / 2.5, 0.8, 2.2);
    this.scale0 = obj.scale.clone();
    this.left = this.def.uses;
    this.refresh(ctx);
  }

  /**
   * Draws a place's wrecks built in pieces merged, a few calls for all of them
   * (see mergePieces()), with the merged meshes in `scene`. Dispose the batch
   * with the wrecks.
   */
  static drawMerged(wrecks: readonly Wreck[], scene: THREE.Object3D): PieceBatch {
    const inPieces = wrecks.filter((w) => w.pieces.length);
    // The batch hides what it merged mesh by mesh; a piece hidden whole would hide what it couldn't.
    for (const w of inPieces) for (const p of w.pieces) p.visible = true;
    const batch = mergePieces(inPieces.map((w) => ({ root: w.object, pieces: w.pieces })));
    for (const m of batch.meshes) scene.add(m);
    inPieces.forEach((w, i) => {
      w.batch = batch;
      w.slot = i;
      batch.setGone(i, w.hidden(w.shown));
    });
    return batch;
  }

  get name(): string {
    return this.def.name;
  }

  /** Pieces left on it now: home's from the save (whole again each low tide), elsewhere this visit's. */
  leftNow(ctx: GameContext): number {
    return this.persists ? wreckLeft(ctx.state, this.key, this.def.uses, ctx.state.tide.elapsed) : this.left;
  }

  /** The tide and your hook allow it (a full satchel aside). */
  obtainable(ctx: GameContext): boolean {
    return this.live && this.reason(ctx, false) === null;
  }

  /** Why the hook can't tear at it now, or null. */
  blocked(ctx: GameContext): string | null {
    return this.reason(ctx, true);
  }

  private reason(ctx: GameContext, satchel: boolean): string | null {
    const d = this.def;
    if (d.tide === "low" && ctx.tide.state === "high") return `${d.name}: underwater until low tide`;
    if (d.tide === "high" && ctx.tide.state === "low") return `${d.name}: only bared at high tide`;
    if (d.requiresGear && !hasGear(ctx.state.gear, d.requiresGear)) return `${d.name}: needs the ${GEAR[d.requiresGear].name}`;
    if (ctx.shrouded(this.at)) return `${d.name}: shrouded in Gloom. Flare your lantern (${ctx.keyLabel("flare")})`;
    if (satchel && !roomFor(ctx.state, d.yields)) return this.persists ? "Satchel full: unload at the chest" : "Satchel full: head home to unload";
    return null;
  }

  /**
   * The hook tears `count` pieces off and you get what they hold. Returns
   * copies of the pieces it took, where they were, to throw at you.
   */
  yank(ctx: GameContext, count: number): THREE.Object3D[] {
    const before = this.leftNow(ctx);
    const n = Math.min(count, before);
    if (n <= 0) return [];
    const after = this.persists ? tearWreck(ctx.state, this.key, this.def.uses, ctx.state.tide.elapsed, n) : (this.left = before - n);
    const from = this.at.clone();
    for (let i = 0; i < n; i++) for (const st of rollYields(this.def.yields, Math.random)) ctx.give(st.item, st.qty, from);
    if (this.def.xp) ctx.xp("salvaging", this.def.xp * n);
    ctx.state.salvaged += n;
    const flying: THREE.Object3D[] = [];
    for (let k = this.hidden(before); k < this.hidden(after); k++) {
      const piece = this.pieces[k];
      if (!piece) continue;
      // The piece itself is hidden (the merged mesh draws it): show its copy.
      const copy = piece.clone();
      copy.traverse((o) => (o.visible = true));
      piece.matrixWorld.decompose(copy.position, copy.quaternion, copy.scale);
      flying.push(copy);
    }
    this.refresh(ctx);
    return flying;
  }

  /** How many of its pieces are gone with `left` pulls to go. */
  private hidden(left: number): number {
    return Math.round(this.pieces.length * (1 - left / this.def.uses));
  }

  /** Shows what's left of it: pieces gone top first, or the whole thing shrunk. */
  private refresh(ctx: GameContext): void {
    const left = this.leftNow(ctx);
    if (left === this.shown) return;
    const restocked = this.shown >= 0 && left > this.shown;
    this.shown = left;
    this.live = left > 0;
    if (this.pieces.length) {
      const gone = this.hidden(left);
      if (this.batch) this.batch.setGone(this.slot, gone);
      else this.pieces.forEach((p, k) => (p.visible = k >= gone));
    } else if (left > 0) {
      this.object.visible = true;
      this.fade = 1;
      this.object.scale.copy(this.scale0).multiplyScalar(0.5 + (0.5 * left) / this.def.uses);
    }
    if (restocked) ctx.effects.emit(this.at, { count: 10, color: FX_COLORS.water, speed: 1.2, life: 0.8, gravity: 2, spread: this.radius });
  }

  /** Shadow LOD, as for gather nodes. */
  castShadows(on: boolean): void {
    if (on === this.shadowOn) return;
    this.shadowOn = on;
    if (!this.shadowMeshes) {
      this.shadowMeshes = [];
      this.object.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m.isMesh && m.castShadow) this.shadowMeshes!.push(m);
      });
    }
    for (const m of this.shadowMeshes) m.castShadow = on;
  }

  update(dt: number, ctx: GameContext): void {
    this.refresh(ctx);
    // A wreck in one piece sinks away once it's spent.
    if (!this.pieces.length && this.shown <= 0 && this.fade > 0) {
      this.fade = Math.max(0, this.fade - dt * 2.5);
      this.object.scale.copy(this.scale0).multiplyScalar(Math.max(0.001, this.fade * 0.5));
      if (this.fade === 0) this.object.visible = false;
      return;
    }
    // A glint marks what the hook can take.
    if (!this.live) return;
    this.glintT -= dt;
    if (this.glintT > 0) return;
    this.glintT = 1.8 + Math.random() * 1.6;
    if (this.at.distanceTo(ctx.player.position) < 34 && this.blocked(ctx) === null) {
      ctx.effects.emit(tmpV.copy(this.at).add(new THREE.Vector3(0, 0.3, 0)), { count: 3, color: FX_COLORS.loot, speed: 0.6, life: 0.9, gravity: -0.5, spread: 0.4 });
    }
  }

  dispose(): void {
    if (this.owned) this.object.removeFromParent();
  }
}
