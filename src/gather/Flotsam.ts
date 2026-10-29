import * as THREE from "three";
import { FLOTSAM_IDS, type FlotsamId } from "../data/ids";
import { FLOTSAM, SALVAGE } from "../data/salvage";
import { FX_COLORS } from "../fx/Effects";
import type { GameContext } from "../game/Context";
import { flotsamFor, rollYields, roomFor } from "../systems/salvage";
import { instanceParts } from "../world/Batch";

// What the sea brings into the Rest's cove. Pieces come in through the mouth
// along the FX_drift_ lanes in home.glb, more on the flood, swaying across
// their lane and riding the swell. Where the water's too shallow for one it
// grounds until the tide lifts it again; at the top of the beach it's stranded
// for good and lies there (the save's cove.beach) until you hook it or walk
// over it. Drawn instanced, one batch per kind.

export type DriftState = "afloat" | "aground" | "beached" | "hooked";

/** How close you walk to pick a grounded or stranded piece up. */
const PICKUP = 1.3;
/** Stranded once it grounds this near its lane's end: the top of the beach. */
const STRAND_NEAR = 7;
/** Seconds a stranded piece takes to settle into its place on the beach. */
const SETTLE = 1.2;

const tmpQ = new THREE.Quaternion();
const tmpE = new THREE.Euler();
const tmpM = new THREE.Matrix4();
const tmpM2 = new THREE.Matrix4();
const tmpV = new THREE.Vector3();
const ONE = new THREE.Vector3(1, 1, 1);

/** One piece of drift. The hook reels it in (src/gather/Hook.ts). */
export class Piece {
  readonly pull = "reel" as const;
  /** Where it is: the waterline at its middle. */
  readonly at = new THREE.Vector3();
  readonly radius: number;
  state: DriftState = "afloat";
  /** Riding the water (it bobs), rather than lying on the ground. */
  floating = true;
  /** Metres along its lane. */
  s: number;
  yaw = Math.random() * Math.PI * 2;
  /** Its place on the beach once stranded, and the settling into it. */
  slot = -1;
  private readonly settleFrom = new THREE.Vector3();
  private settle = 0;
  readonly speed: number;
  readonly phase = Math.random() * 100;

  constructor(
    readonly id: FlotsamId,
    readonly lane: number,
    s: number,
  ) {
    this.s = s;
    const [lo, hi] = SALVAGE.driftSpeed;
    this.speed = lo + Math.random() * (hi - lo);
    this.radius = id === "log" ? 1.6 : id === "kelp_mat" || id === "planks" ? 1.1 : 0.9;
  }

  get name(): string {
    return FLOTSAM[this.id].name;
  }

  /** Still there for the taking (not already on a line). */
  get live(): boolean {
    return this.state !== "hooked";
  }

  /** Nothing stops the hook taking drift but a full satchel. */
  blocked(ctx: GameContext): string | null {
    return roomFor(ctx.state, FLOTSAM[this.id].yields) ? null : "Satchel full: unload at the chest";
  }

  /** Strands it in a beach place, sliding there from where it grounded. */
  strandAt(slot: number, from: THREE.Vector3): void {
    this.state = "beached";
    this.floating = false;
    this.slot = slot;
    this.settleFrom.copy(from);
    this.settle = SETTLE;
  }

  /** Eases into its beach place while it settles. */
  settleInto(dt: number, to: THREE.Vector3): void {
    if (this.settle <= 0) {
      this.at.copy(to);
      return;
    }
    this.settle = Math.max(0, this.settle - dt);
    const k = 1 - this.settle / SETTLE;
    this.at.copy(this.settleFrom).lerp(to, k * k * (3 - 2 * k));
  }
}

interface Lane {
  points: THREE.Vector3[];
  /** Metres from the mouth to each point. */
  at: number[];
  length: number;
}

export class Flotsam {
  readonly root = new THREE.Group();
  readonly pieces: Piece[] = [];
  private readonly lanes: Lane[] = [];
  /** The beach's places for stranded pieces, and who lies in each. */
  private readonly strand: THREE.Vector3[] = [];
  private readonly taken: (Piece | null)[] = [];
  private readonly meshes = new Map<FlotsamId, { mesh: THREE.InstancedMesh; part: THREE.Matrix4 }[]>();
  private spawnIn = 2;

  constructor(ctx: GameContext, points: ReadonlyMap<string, THREE.Vector3>) {
    this.root.name = "flotsam";
    for (let l = 0; points.has(`drift_${l}_0`); l++) {
      const pts: THREE.Vector3[] = [];
      for (let k = 0; points.has(`drift_${l}_${k}`); k++) pts.push(points.get(`drift_${l}_${k}`)!.clone().setY(0));
      const at = [0];
      for (let k = 1; k < pts.length; k++) at.push(at[k - 1]! + pts[k]!.distanceTo(pts[k - 1]!));
      this.lanes.push({ points: pts, at, length: at[at.length - 1]! });
    }
    for (let k = 0; points.has(`strand_${k}`); k++) {
      this.strand.push(points.get(`strand_${k}`)!.clone());
      this.taken.push(null);
    }
    if (!this.lanes.length) return;
    const cap = SALVAGE.maxAfloat + SALVAGE.beachMax + 4;
    for (const id of FLOTSAM_IDS) {
      const src = ctx.assets.prop(FLOTSAM[id].model);
      if (!src) continue;
      const parts: { mesh: THREE.InstancedMesh; part: THREE.Matrix4 }[] = [];
      for (const p of instanceParts(src)) {
        const mesh = new THREE.InstancedMesh(p.geometry, p.material, cap);
        mesh.count = 0;
        mesh.castShadow = mesh.receiveShadow = true;
        // They move every frame, so a bounding sphere would always be stale.
        mesh.frustumCulled = false;
        mesh.name = `flotsam_${id}`;
        this.root.add(mesh);
        parts.push({ mesh, part: p.matrix });
      }
      this.meshes.set(id, parts);
    }
    ctx.scene.add(this.root);
  }

  /** The cove has drift lanes (only home does). */
  get active(): boolean {
    return this.lanes.length > 0;
  }

  /** Lays the cove out as you arrive: what the tide left on the beach (the save), and a few pieces already on their way in. */
  arrive(ctx: GameContext): void {
    if (!this.active) return;
    for (const id of ctx.state.cove.beach) {
      const slot = this.taken.indexOf(null);
      if (slot < 0) break;
      const p = new Piece(id, 0, 0);
      p.strandAt(slot, this.strand[slot]!);
      p.at.copy(this.strand[slot]!);
      this.taken[slot] = p;
      this.pieces.push(p);
    }
    for (let i = 0; i < SALVAGE.afloatOnArrival; i++) {
      const lane = Math.floor(Math.random() * this.lanes.length);
      this.spawn(flotsamFor(ctx.tide.phase, Math.random()), lane, this.lanes[lane]!.length * (0.15 + Math.random() * 0.5), ctx.tide.waterY);
    }
  }

  /** A new piece in through the mouth, or `s` metres along its lane (dev: __ll.flotsam()). */
  spawn(id: FlotsamId, lane = Math.floor(Math.random() * this.lanes.length), s = 0, waterY = 0): Piece | null {
    if (!this.lanes[lane]) return null;
    const p = new Piece(id, lane, s);
    this.place(p, 0);
    p.at.y = waterY;
    this.pieces.push(p);
    return p;
  }

  /** Pieces in the water or the shallows, not yet stranded. */
  get adrift(): number {
    let n = 0;
    for (const p of this.pieces) if (p.state !== "beached") n++;
    return n;
  }

  update(dt: number, ctx: GameContext): void {
    if (!this.active) return;
    this.spawnIn -= dt;
    if (this.spawnIn <= 0) {
      this.spawnIn = SALVAGE.driftEvery[ctx.tide.phase] * (0.75 + Math.random() * 0.5);
      if (this.adrift < SALVAGE.maxAfloat) this.spawn(flotsamFor(ctx.tide.phase, Math.random()), undefined, 0, ctx.tide.waterY);
    }
    const waterY = ctx.tide.waterY;
    const player = ctx.player.position;
    for (const p of [...this.pieces]) {
      if (p.state === "beached") p.settleInto(dt, this.strand[p.slot]!);
      else if (p.state !== "hooked") this.drift(p, dt, ctx);
      // Walk over what's lying out of the water, or wade to what's floating, and it's yours.
      if (p.state === "hooked" || ctx.player.water === "swimming") continue;
      const dx = p.at.x - player.x;
      const dz = p.at.z - player.z;
      if (dx * dx + dz * dz < PICKUP * PICKUP && Math.abs(p.at.y - player.y) < 1.6 && !p.blocked(ctx)) this.take(p, ctx);
    }
    this.draw(ctx.time, waterY);
  }

  /** Along its lane while there's water enough to float it; grounded where there isn't. */
  private drift(p: Piece, dt: number, ctx: GameContext): void {
    const lane = this.lanes[p.lane]!;
    const floor = this.ground(ctx, p.at.x, p.at.z);
    const draft = FLOTSAM[p.id].draft;
    if (ctx.tide.waterY - floor >= draft) {
      p.state = "afloat";
      p.floating = true;
      p.s = Math.min(lane.length, p.s + p.speed * dt);
      this.place(p, ctx.time);
      p.at.y = ctx.tide.waterY;
      return;
    }
    if (p.state === "afloat" && lane.length - p.s < STRAND_NEAR) {
      this.strandPiece(ctx, p);
      return;
    }
    // On the flats: it waits there for the tide.
    p.state = "aground";
    p.floating = false;
    p.at.y = floor + draft * 0.5;
  }

  /** Where it rides on its lane: along it, swaying across it. */
  private place(p: Piece, time: number): void {
    const lane = this.lanes[p.lane]!;
    let k = 1;
    while (k < lane.points.length - 1 && lane.at[k]! < p.s) k++;
    const a = lane.points[k - 1]!;
    const b = lane.points[k]!;
    const t = THREE.MathUtils.clamp((p.s - lane.at[k - 1]!) / Math.max(1e-6, lane.at[k]! - lane.at[k - 1]!), 0, 1);
    const dx = b.x - a.x;
    const dz = b.z - a.z;
    const len = Math.hypot(dx, dz) || 1;
    // The sway dies away toward the beach, so pieces strand where their lane ends.
    const sway = Math.sin(((time + p.phase) / SALVAGE.sway.seconds) * Math.PI * 2) * SALVAGE.sway.metres * Math.min(1, (lane.length - p.s) / 10);
    p.at.x = a.x + dx * t + (-dz / len) * sway;
    p.at.z = a.z + dz * t + (dx / len) * sway;
    p.yaw += Math.sin(time * 0.3 + p.phase) * 0.002;
  }

  private strandPiece(ctx: GameContext, p: Piece): void {
    let best = -1;
    let bestD = Infinity;
    this.taken.forEach((who, k) => {
      if (who) return;
      const d = this.strand[k]!.distanceToSquared(p.at);
      if (d < bestD) [best, bestD] = [k, d];
    });
    if (best < 0) {
      // The beach is full: the sea takes it back out.
      this.remove(p);
      return;
    }
    this.taken[best] = p;
    p.strandAt(best, p.at);
    ctx.state.cove.beach.push(p.id);
  }

  /** Ground or sea floor under a point. */
  ground(ctx: GameContext, x: number, z: number): number {
    const y = ctx.level.collider.groundHeight(x, z, ctx.tide.waterY + 6, 40);
    return y === -Infinity ? -12 : y;
  }

  /** Hooked out or picked up: what it gives goes in the satchel. */
  take(p: Piece, ctx: GameContext): void {
    const def = FLOTSAM[p.id];
    const from = p.at.clone().add(new THREE.Vector3(0, 0.4, 0));
    for (const st of rollYields(def.yields, Math.random)) ctx.give(st.item, st.qty, from);
    ctx.xp("salvaging", def.xp);
    ctx.state.salvaged++;
    if (p.state === "beached" || p.slot >= 0) {
      const i = ctx.state.cove.beach.indexOf(p.id);
      if (i >= 0) ctx.state.cove.beach.splice(i, 1);
    }
    if (p.floating) ctx.effects.splash(from, 8);
    else ctx.effects.burst(from, FX_COLORS.smoke, 10);
    this.remove(p);
  }

  /** The line slipped: a piece in the water drifts on from the nearest point of its lane; one on the sand lies where it is. */
  release(p: Piece, ctx: GameContext): void {
    if (p.slot >= 0) {
      p.state = "beached";
      return;
    }
    const lane = this.lanes[p.lane];
    if (!lane) return;
    let best = p.s;
    let bestD = Infinity;
    for (let k = 1; k < lane.points.length; k++) {
      const a = lane.points[k - 1]!;
      const b = lane.points[k]!;
      const seg = lane.at[k]! - lane.at[k - 1]!;
      const t = THREE.MathUtils.clamp(((p.at.x - a.x) * (b.x - a.x) + (p.at.z - a.z) * (b.z - a.z)) / Math.max(1e-6, seg * seg), 0, 1);
      const d = Math.hypot(a.x + (b.x - a.x) * t - p.at.x, a.z + (b.z - a.z) * t - p.at.z);
      if (d < bestD) [best, bestD] = [lane.at[k - 1]! + seg * t, d];
    }
    p.s = best;
    p.state = "aground";
    this.drift(p, 0, ctx);
  }

  private remove(p: Piece): void {
    if (p.slot >= 0 && this.taken[p.slot] === p) this.taken[p.slot] = null;
    const i = this.pieces.indexOf(p);
    if (i >= 0) this.pieces.splice(i, 1);
  }

  private draw(time: number, waterY: number): void {
    const counts = new Map<FlotsamId, number>();
    const b = SALVAGE.bob;
    for (const p of this.pieces) {
      const parts = this.meshes.get(p.id);
      if (!parts?.length) continue;
      const n = counts.get(p.id) ?? 0;
      if (n >= parts[0]!.mesh.instanceMatrix.count) continue;
      counts.set(p.id, n + 1);
      const swell = p.floating && p.at.y <= waterY + 0.05;
      const bob = swell ? Math.sin(time * b.rate + p.phase) * b.metres : 0;
      const roll = swell ? THREE.MathUtils.degToRad(b.rollDeg) * Math.sin(time * b.rate * 0.8 + p.phase * 1.7) : 0.08 * Math.sin(p.phase);
      tmpQ.setFromEuler(tmpE.set(roll * 0.6, p.yaw, roll, "YXZ"));
      tmpM.compose(tmpV.set(p.at.x, p.at.y + bob, p.at.z), tmpQ, ONE);
      for (const { mesh, part } of parts) mesh.setMatrixAt(n, tmpM2.multiplyMatrices(tmpM, part));
    }
    for (const [id, parts] of this.meshes) {
      const n = counts.get(id) ?? 0;
      for (const { mesh } of parts) {
        mesh.count = n;
        mesh.instanceMatrix.needsUpdate = true;
      }
    }
  }

  dispose(): void {
    this.root.removeFromParent();
    this.pieces.length = 0;
  }
}
