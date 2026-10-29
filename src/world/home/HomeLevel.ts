import * as THREE from "three";
import type { Assets } from "../../core/Assets";
import { NPC_IDS, PROJECT_IDS, type NpcId, type ProjectId } from "../../data/ids";
import { PROJECTS, STAGES } from "../../data/lighthouse";
import { NPCS } from "../../data/npcs";
import { FAMILIES, NPC_LOOKS, type VillagerLook } from "../../data/villagers";
import { StaticCollider } from "../../physics/StaticCollider";
import { TIDE } from "../../data/tide";
import type { GameState } from "../../state/GameState";
import { buildProgress } from "../../systems/building";
import { insideOutline, type PlaceWorld } from "../../systems/decor";
import { batchMeshes, staticMeshes, type BatchResult } from "../Batch";
import { findNamed, type Buoy, type EnemyMarker, type GloomMarker, type Level, type LevelInteract, type LevelUpdate, type NodeMarker, type Trigger } from "../Level";
import { GlbLevel } from "../LevelLoader";
import { Lighthouse } from "../Lighthouse";
import { DecorLayer } from "./Decor";
import { findPlots, STATION_TARGET, type Plot } from "./Plot";
import { Villager } from "./Villager";

// Lantern's Rest. The place itself is Blender's (tools/blender/build/home_map.py
// → locations/home.glb), read by LevelLoader like the expeditions; this layers
// the Rest's progress over it: the plots you rebuild (Plot.ts), who has come
// home, the lighthouse's beam, the boats at the jetty, lit windows and chimney
// smoke, all following the save (applyProgress).

export type HomeSpawn = "start" | "landing" | "jetty";

/** Where you stand before there's a map to stand on. */
const NOWHERE = { position: new THREE.Vector3(0, 20, 0), yaw: 0 };
/** How high the ground lies that the beam's spotlight sweeps: the quay and the lower terrace. */
const BEAM_GROUND = 4;
/** People stand in as these figures until their Polyfork models arrive. */
const PLACEHOLDER: Record<NpcId, number> = { maren: 0xb8b0a0, odile: 0x9c5a3c, tib: 0x4d6a7a, hesk: 0x6e4a36 };
const FAMILY_PLACEHOLDER = [0x7d6b8a, 0x8a7a5a, 0x5a7a6b] as const;
const BODY = new THREE.CapsuleGeometry(0.35, 1.1, 4, 8);
const SMALL_BODY = new THREE.CapsuleGeometry(0.3, 0.8, 4, 8);
const HEAD = new THREE.SphereGeometry(0.24, 12, 8);
const SKIN = new THREE.MeshStandardMaterial({ color: 0xd9b48f, roughness: 0.85 });
const HIDDEN = new THREE.MeshBasicMaterial({ visible: false });
/** What you aim at to work a station: a box against the building's front. */
const STATION = new THREE.BoxGeometry(1.6, 2, 1.4);
const PUFF = new THREE.SphereGeometry(0.5, 8, 6);
const PUFFS = 6;
const UP = new THREE.Vector3(0, 1, 0);

const tmpV = new THREE.Vector3();
const tmpS = new THREE.Vector3();
const tmpM = new THREE.Matrix4();
const tmpQ = new THREE.Quaternion();
const tmpE = new THREE.Euler();

function yawOf(o: THREE.Object3D): number {
  o.getWorldQuaternion(tmpQ);
  return tmpE.setFromQuaternion(tmpQ, "YXZ").y;
}

function swapMaterial(root: THREE.Object3D, name: string, to: THREE.Material): void {
  root.traverse((o) => {
    const m = o as THREE.Mesh;
    if (!m.isMesh) return;
    if (Array.isArray(m.material)) m.material = m.material.map((x) => (x.name === name ? to : x));
    else if (m.material.name === name) m.material = to;
  });
}

interface Person {
  group: THREE.Group;
  /** The placeholder's body; once the model arrives, an invisible capsule left behind as collision and the thing you talk to. */
  body: THREE.Mesh;
  parts: THREE.Mesh[];
  villager: Villager | null;
}

export class HomeLevel implements Level {
  readonly id = "home" as const;
  readonly root = new THREE.Group();
  collider = new StaticCollider([]);
  readonly anchors: THREE.Vector3[] = [];
  readonly nodes: NodeMarker[] = [];
  readonly enemies: EnemyMarker[] = [];
  readonly interacts: LevelInteract[] = [];
  readonly triggers: Trigger[] = [];
  /** The boats in at the jetty: none until it stands. */
  buoys: Buoy[] = [];
  readonly gloom: GloomMarker[] = [];
  readonly points = new Map<string, THREE.Vector3>();
  readonly lighthouse = new Lighthouse();
  readonly plots = new Map<ProjectId, Plot>();
  /** Where decor may go (the FX_decor_ outline, x and z) and the circles kept clear of it (CLEAR_). */
  readonly decorBounds: [number, number][] = [];
  readonly keepClear: { x: number; z: number; r: number }[] = [];

  /** What you've placed round the Rest (build mode). */
  decor: DecorLayer | null = null;
  private level: GlbLevel | null = null;
  /** The ground alone (the terrain), for standing decor on: nothing placed or built counts. */
  private ground: StaticCollider | null = null;
  private readonly npcs = new Map<NpcId, Person>();
  private readonly families: Person[][] = [];
  /** Everyone above, in one list. */
  private residents: Person[] = [];
  private boats: Buoy[] = [];
  /** Each station's target, shown once its plot stands. */
  private readonly stations = new Map<ProjectId, THREE.Mesh>();
  /** The buildings that stand, merged by material, and which ones those are. */
  private plotBatch: BatchResult | null = null;
  private batchedPlots = "";
  private readonly coals = new THREE.MeshStandardMaterial({ color: 0x331a0a, emissive: 0xff7a1a, emissiveIntensity: 1.4 });
  private readonly ember = new THREE.MeshStandardMaterial({ color: 0x331a0a, emissive: 0xff7a1a, emissiveIntensity: 0 });
  private readonly windowLit = new THREE.MeshStandardMaterial({ color: 0xffd08a, emissive: 0xffb347, emissiveIntensity: 1.6 });
  private readonly hearthLight = new THREE.PointLight(0xff9a40, 25, 14, 1.6);
  private readonly forgeGlow = new THREE.PointLight(0xff7a1a, 0, 10, 1.8);
  private smoke: THREE.InstancedMesh | null = null;
  /** Chimneys with a fire lit under them. */
  private chimneys: THREE.Vector3[] = [];
  /** What the collider was last built from: rebuilding it is a merge and a BVH, so only when this changes. */
  private colliderKey = "";
  private decorVersion = 0;

  get spawn(): THREE.Vector3 {
    return this.spawnFor("start").position;
  }

  get spawnYaw(): number {
    return this.spawnFor("start").yaw;
  }

  /** start: by the lighthouse door. landing: the beach. jetty: off the boat. */
  spawnFor(name: HomeSpawn): { position: THREE.Vector3; yaw: number } {
    return this.level?.spawns.get(name) ?? this.level?.spawns.get("start") ?? NOWHERE;
  }

  /** Loads the map and sets the Rest up on it. False if home.glb couldn't be loaded. */
  async load(assets: Assets): Promise<boolean> {
    if (this.level) return true;
    const scene = await assets.load("locations/home.glb");
    if (!scene) return false;
    const level = new GlbLevel("home", scene);
    this.level = level;
    this.root.name = "home";
    this.root.add(level.root);
    this.root.updateMatrixWorld(true);
    this.anchors.push(...level.anchors);
    this.nodes.push(...level.nodes);
    this.interacts.push(...level.interacts);
    for (const [name, at] of level.points) this.points.set(name, at);
    this.boats = [...level.buoys].sort((a, b) => a.object.name.localeCompare(b.object.name));
    for (let k = 0; level.points.has(`decor_${k}`); k++) {
      const p = level.points.get(`decor_${k}`)!;
      this.decorBounds.push([p.x, p.z]);
    }

    let grass: THREE.Mesh | null = null;
    level.root.traverse((o) => {
      if (o.name === "terrain" && (o as THREE.Mesh).isMesh) this.ground = new StaticCollider([o as THREE.Mesh]);
      if (o.name.startsWith("CLEAR_") && typeof o.userData.radius === "number") {
        o.getWorldPosition(tmpV);
        this.keepClear.push({ x: tmpV.x, z: tmpV.z, r: o.userData.radius as number });
      } else if (o.name === "SCATTER_grass" && (o as THREE.Mesh).isMesh) grass = o as THREE.Mesh;
    });
    if (grass) this.grass(assets, grass);

    this.placeLighthouse(level.root);
    for (const [id, plot] of findPlots(level.root)) this.plots.set(id, plot);
    this.fires(level.root);
    this.people(level.root);

    const chimneys = [...this.plots.values()].filter((p) => p.smoke).length;
    if (chimneys) {
      const smoke = new THREE.InstancedMesh(PUFF, new THREE.MeshBasicMaterial({ color: 0xb8b8b8, transparent: true, opacity: 0.25, depthWrite: false }), chimneys * PUFFS);
      smoke.name = "chimney_smoke";
      smoke.count = 0;
      smoke.frustumCulled = false;
      this.root.add(smoke);
      this.smoke = smoke;
    }
    this.residents = [...this.npcs.values(), ...this.families.flat()];
    this.decor = new DecorLayer(assets);
    this.root.add(this.decor.root);
    return true;
  }

  /** The tower stands at PLACE_lighthouse, its beam's sweep aimed down at the quay. */
  private placeLighthouse(map: THREE.Object3D): void {
    const place = map.getObjectByName("PLACE_lighthouse");
    if (!place) return;
    const group = this.lighthouse.group;
    place.getWorldPosition(group.position);
    group.rotation.y = yawOf(place);
    const tower = place.children.find((c) => c.name.startsWith("lighthouse"));
    if (tower) {
      tower.removeFromParent();
      tower.position.set(0, 0, 0);
      tower.rotation.set(0, 0, 0);
      tower.scale.set(1, 1, 1);
      this.lighthouse.dress(tower);
    }
    this.root.add(group);
    group.updateMatrixWorld(true);
    this.lighthouse.rig.setGroundDrop(this.lighthouse.rig.pivot.getWorldPosition(tmpV).y - BEAM_GROUND);
  }

  /** The hearth's coals and light, the forge's firebox and glow, and the stations you work (and the jetty's berth) once their plots stand. */
  private fires(map: THREE.Object3D): void {
    const hearth = map.getObjectByName("INT_hearth");
    if (hearth) {
      swapMaterial(hearth, "EMBER", this.coals);
      hearth.getWorldPosition(this.hearthLight.position);
      this.hearthLight.position.y += 1.2;
      this.root.add(this.hearthLight);
    }
    const forge = this.plots.get("forge");
    if (forge) {
      swapMaterial(forge.root, "EMBER", this.ember);
      const mouth = findNamed(forge.built, "mouth");
      const at = mouth ? new THREE.Box3().setFromObject(mouth).getCenter(new THREE.Vector3()) : forge.centre();
      // Out in front of the firebox, toward where you stand to work it.
      if (forge.station) at.lerp(forge.station.getWorldPosition(tmpV).setY(at.y), 0.35);
      this.forgeGlow.position.copy(at);
      this.root.add(this.forgeGlow);
    }
    for (const plot of this.plots.values()) {
      // The jetty's mark faces the berth: the boat lies low at low water, so the berth is what you aim at.
      const def = PROJECTS[plot.id];
      const id = def.unlocksStation ?? (def.unlocksOffshore ? "boat" : null);
      if (!id || !plot.station) continue;
      const target = new THREE.Mesh(STATION, HIDDEN);
      target.name = `station_${id}`;
      target.position.copy(STATION_TARGET.at);
      target.visible = false;
      plot.station.add(target);
      this.stations.set(plot.id, target);
      this.interacts.push({ id, object: target, range: STATION_TARGET.range });
    }
  }

  /** Everyone at their NPC_ marker, and the families at PLACE_family_ ones by their doors. */
  private people(map: THREE.Object3D): void {
    for (const id of NPC_IDS) {
      const marker = map.getObjectByName(NPCS[id].marker);
      if (!marker) continue;
      const p = this.person(marker, PLACEHOLDER[id], false, NPC_LOOKS[id]);
      this.npcs.set(id, p);
      this.interacts.push({ id: `npc:${id}`, object: p.group, range: 3.2 });
    }
    FAMILIES.forEach((looks, f) => {
      const members: Person[] = [];
      looks.forEach((look, i) => {
        const marker = map.getObjectByName(`PLACE_family_${f}_${i}`);
        if (marker) members.push(this.person(marker, FAMILY_PLACEHOLDER[i % FAMILY_PLACEHOLDER.length]!, i > 0, look));
      });
      this.families.push(members);
    });
  }

  private person(marker: THREE.Object3D, color: number, small: boolean, look: VillagerLook): Person {
    const group = new THREE.Group();
    group.name = marker.name.toLowerCase();
    marker.getWorldPosition(group.position);
    const body = new THREE.Mesh(small ? SMALL_BODY : BODY, new THREE.MeshStandardMaterial({ color, roughness: 0.85 }));
    body.position.y = small ? 0.75 : 0.9;
    const head = new THREE.Mesh(HEAD, SKIN);
    head.position.y = small ? 1.45 : 1.85;
    if (small) head.scale.setScalar(0.85);
    for (const m of [body, head]) m.castShadow = true;
    group.add(body, head);
    group.visible = false;
    this.root.add(group);
    const p: Person = { group, body, parts: [body, head], villager: null };
    void Villager.load(look, yawOf(marker)).then((v) => {
      if (!v) return;
      for (const m of p.parts) {
        m.material = HIDDEN;
        m.castShadow = false;
      }
      group.add(v.object);
      p.villager = v;
    });
    return p;
  }

  /**
   * Grass on the open turf, instanced from the dune grass prop. SCATTER_grass
   * holds one triangle per tuft: its root, a corner 0.1 m straight above it, and
   * a corner out along the tuft's turn, 0.1 m per unit of scale.
   */
  private grass(assets: Assets, scatter: THREE.Mesh): void {
    const src = assets.prop("dune_grass");
    if (!src) return;
    const geo = scatter.geometry;
    const pos = geo.getAttribute("position");
    const index = geo.index;
    const tris = (index ? index.count : pos.count) / 3;
    scatter.updateWorldMatrix(true, false);
    const c: THREE.Vector3[] = [new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()];
    const corner = (k: number) => c[k % 3]!;
    const scale = new THREE.Vector3();
    const mats: THREE.Matrix4[] = [];
    for (let t = 0; t < tris; t++) {
      for (let k = 0; k < 3; k++) corner(k).fromBufferAttribute(pos, index ? index.getX(t * 3 + k) : t * 3 + k).applyMatrix4(scatter.matrixWorld);
      // The two corners nearest in plan are the root and the one above it.
      let pair = 0;
      let near = Infinity;
      for (let k = 0; k < 3; k++) {
        const d = Math.hypot(corner(k).x - corner(k + 1).x, corner(k).z - corner(k + 1).z);
        if (d < near) [near, pair] = [d, k];
      }
      const a = corner(pair);
      const b = corner(pair + 1);
      const out = corner(pair + 2);
      const at = a.y < b.y ? a : b;
      const dx = out.x - at.x;
      const dz = out.z - at.z;
      const s = Math.hypot(dx, dz) / 0.1;
      const yaw = Math.atan2(dx, dz);
      tmpQ.setFromAxisAngle(UP, yaw);
      mats.push(new THREE.Matrix4().compose(at, tmpQ, scale.set(s, s * (0.8 + 0.4 * Math.abs(Math.sin(yaw * 3.7))), s)));
    }
    src.updateWorldMatrix(true, true);
    src.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      const inst = new THREE.InstancedMesh(m.geometry, m.material, mats.length);
      mats.forEach((mx, i) => inst.setMatrixAt(i, tmpM.multiplyMatrices(mx, m.matrixWorld)));
      inst.receiveShadow = true;
      inst.name = "grass";
      this.root.add(inst);
    });
  }

  /** Where a look along `dir` meets the ground itself (through anything built or placed on it), within `far`. */
  groundRay(from: THREE.Vector3, dir: THREE.Vector3, far: number): THREE.Intersection | null {
    return this.ground?.raycast(from, dir, far) ?? null;
  }

  /** Height of the ground under a point, or null off the map. */
  groundY(x: number, z: number): number | null {
    const y = this.ground?.groundHeight(x, z, 40, 80) ?? -Infinity;
    return y === -Infinity ? null : y;
  }

  /** What decor placement needs to know about the Rest (src/systems/decor.ts). `clear`: more circles to keep free, like where you stand. */
  placeWorld(clear: readonly { x: number; z: number; r: number }[] = []): PlaceWorld {
    return {
      inBounds: (x, z) => insideOutline(this.decorBounds, x, z),
      groundY: (x, z) => this.groundY(x, z),
      keepClear: [...this.keepClear, ...clear],
      highWater: TIDE.highLevel,
    };
  }

  /** Makes the Rest match the save: each plot's rebuild, who's home, the boats, the fires and the beam. */
  applyProgress(state: GameState): void {
    const visuals = STAGES[state.stage]!.visuals;
    this.chimneys = [];
    for (const [id, plot] of this.plots) {
      plot.set(buildProgress(state, id));
      if (plot.done) {
        // People live there again.
        for (const w of plot.windows) w.material = this.windowLit;
        if (plot.smoke) this.chimneys.push(plot.smoke.getWorldPosition(new THREE.Vector3()));
      }
      const target = this.stations.get(id);
      if (target) target.visible = plot.done;
    }
    this.batchPlots();
    const forgeLit = this.plots.get("forge")?.done ?? false;
    this.ember.emissiveIntensity = forgeLit ? 2.2 : 0;
    this.forgeGlow.intensity = forgeLit ? 14 : 0;

    for (const [id, p] of this.npcs) {
      const a = NPCS[id].arrives;
      p.group.visible = "stage" in a ? state.stage >= a.stage : state.projects.includes(a.project);
    }
    this.families.forEach((members, f) => {
      const home = PROJECT_IDS.some((id) => PROJECTS[id].family === f && state.projects.includes(id));
      for (const m of members) m.group.visible = home;
    });

    const moored = state.projects.includes("jetty") ? visuals.boats : 0;
    this.boats.forEach((b, i) => (b.object.visible = i < moored));
    this.buoys = this.boats.filter((b) => b.object.visible);
    this.lighthouse.applyStage(visuals);
    if (this.decor?.sync(state.decor, (x, z) => this.groundY(x, z) ?? 0)) this.decorVersion++;
    this.rebuildCollider();
  }

  /** A building that stands never changes again, so they're drawn together: a call per material, not one per part. */
  private batchPlots(): void {
    const level = this.level;
    if (!level) return;
    const done = [...this.plots.values()].filter((p) => p.done);
    const key = done.map((p) => p.id).join();
    if (key === this.batchedPlots) return;
    this.batchedPlots = key;
    this.plotBatch?.dispose();
    this.plotBatch = batchMeshes(level.root, done.flatMap((p) => staticMeshes(p.built)), "plot_batch");
  }

  /** Collision for what stands now: the map, the plots as far as they've risen, and whoever's home. */
  private rebuildCollider(): void {
    const level = this.level;
    if (!level) return;
    const people = this.residents.filter((p) => p.group.visible);
    const plots = [...this.plots.values()];
    const key = `${plots.map((p) => p.progress.toFixed(3)).join()}|${people.map((p) => p.group.name).join()}|${this.decorVersion}`;
    if (key === this.colliderKey) return;
    this.colliderKey = key;
    level.rebuildCollider(
      [...people.map((p) => p.body), ...plots.flatMap((p) => p.colliders()), ...(this.decor?.colliders ?? [])],
      (m) => plots.some((p) => p.skipsCollider(m)),
    );
    this.collider = level.collider;
  }

  update(u: LevelUpdate): void {
    this.level?.update(u);
    this.lighthouse.update(u.dt);
    this.decor?.update(u.dt, u.viewer, u.time);
    for (const p of this.residents) {
      if (!p.villager || !p.group.visible) continue;
      p.villager.update(u.dt, u.time, p.group.worldToLocal(tmpV.copy(u.viewer)));
    }
    const flicker = Math.sin(u.time * 9) * 3 + Math.sin(u.time * 23) * 2;
    this.hearthLight.intensity = 22 + flicker;
    this.coals.emissiveIntensity = 1.4 + flicker * 0.06;
    // Smoke from every chimney with a fire under it.
    const smoke = this.smoke;
    if (!smoke) return;
    let n = 0;
    this.chimneys.forEach((from, k) => {
      for (let i = 0; i < PUFFS; i++) {
        const t = (u.time * 0.25 + i / PUFFS + k * 0.37) % 1;
        const s = 0.6 + t * 1.6;
        tmpV.set(from.x + t * 1.5, from.y + t * 5, from.z + t * 0.8);
        smoke.setMatrixAt(n++, tmpM.compose(tmpV, tmpQ.identity(), tmpS.set(s, s, s)));
      }
    });
    smoke.count = n;
    smoke.instanceMatrix.needsUpdate = true;
  }

  dispose(): void {
    this.level?.dispose();
    this.root.removeFromParent();
  }
}
