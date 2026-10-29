import * as THREE from "three";
import type { Assets } from "../../core/Assets";
import { rng } from "../../core/math";
import type { NpcId, ProjectId, StageIndex } from "../../data/ids";
import type { StageVisuals } from "../../data/lighthouse";
import { NPCS } from "../../data/npcs";
import { FAMILY_LOOKS, NPC_LOOKS } from "../../data/villagers";
import { StaticCollider } from "../../physics/StaticCollider";
import type { EnemyMarker, Level, LevelInteract, LevelUpdate, NodeMarker } from "../Level";
import { disposeObject } from "../Level";
import { batchStatic } from "../Batch";
import { Lighthouse } from "../Lighthouse";
import { headlandTop, wear, type Segment, type Worn } from "./Headland";
import { Villager } from "./Villager";

// Lantern's Rest, built in code and laid out per docs/LEVELS.md. The three
// expedition locations come from Blender; home stays in code because so much
// of it changes with progression (see applyProgress).
//
// The constructor builds a greybox that is also the collision. dress() then
// lays the Blender models over it (home.glb, props.glb; tools/blender/build/
// home.py) and hides the greybox, so the art never moves a collision surface.
// Without the models the greybox is still a playable home.

const CLIFF_TOP = 3;
const DOCK_Y = 2.7;
const DOCK_X = 6;
const RADIUS = 46;

/** Worn paths between the lighthouse, the square, the dock and the cliff path. */
const PATHS: readonly Segment[] = [
  [22, -15, 2, 0],
  [2, 0, 6, 44],
  [-4, 4, -40, 8],
];
/** Bare ground: the square, the lighthouse door, the forge apron, the dock head, the signpost. */
const WORN: readonly Worn[] = [
  { x: -1, z: 1, r: 6.5, k: 0.8 },
  { x: 22, z: -15.5, r: 3.2, k: 0.9 },
  { x: 12, z: 8.6, r: 3.6, k: 0.7 },
  { x: 6, z: 43.5, r: 2.6, k: 0.9 },
  { x: -40, z: 9, r: 3, k: 0.7 },
];
/** Cottages (x, z, yaw). Windows light in this order as the stage rises. */
const COTTAGES = [
  [-16, -6, 0.3],
  [-26, 10, -0.4],
  [-8, -24, 0.1],
  [-30, -14, 0.8],
  [-14, 22, -0.2],
] as const;
const COTTAGE_MODELS = ["HOME_cottage_a", "HOME_cottage_b", "HOME_cottage_c", "HOME_cottage_b", "HOME_cottage_a"];
const LANTERN_POSTS = [
  [16, -10],
  [6, -2],
  [4, 14],
  [5, 28],
  [7.8, 40],
  [-24, 6],
  [-38, 5],
] as const;
/** Dock planks missing until the dock project. */
const MISSING_PLANKS = [9, 10, 11, 18, 19];
/** Kept clear of grass tufts: buildings, the square, the dock head. */
const CLEAR: readonly [number, number, number][] = [
  [22, -20, 6.5],
  [0, 2, 5],
  [-4, -1, 2],
  [12, 6, 4.5],
  [6, 44, 3],
  [-41, 11, 2],
  ...COTTAGES.map(([x, z]) => [x, z, 4.6] as [number, number, number]),
];

const mat = (color: number, extra: THREE.MeshStandardMaterialParameters = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.85, ...extra });
const tmpViewer = new THREE.Vector3();

interface Piece {
  group: THREE.Object3D;
  parts: THREE.Mesh[];
}

export class HomeLevel implements Level {
  readonly id = "home" as const;
  readonly root = new THREE.Group();
  collider: StaticCollider;
  readonly spawn = new THREE.Vector3(22, CLIFF_TOP, -14.5);
  readonly spawnYaw = Math.atan2(22, -14.5);
  /** Where you step off the boat when coming home. */
  readonly dockSpawn = new THREE.Vector3(DOCK_X, DOCK_Y, 66);
  readonly dockYaw = 0;
  /** Where the cliff path from the shore arrives. */
  readonly pathSpawn = new THREE.Vector3(-38, CLIFF_TOP, 8);
  readonly pathYaw = -Math.PI / 2;
  readonly anchors: THREE.Vector3[] = [];
  readonly nodes: NodeMarker[] = [];
  readonly enemies: EnemyMarker[] = [];
  readonly interacts: LevelInteract[] = [];
  readonly triggers = [];
  readonly buoys = [];
  readonly gloom = [];
  readonly points = new Map<string, THREE.Vector3>();
  readonly lighthouse = new Lighthouse();

  private readonly M = {
    rock: mat(0x8d8a80, { flatShading: true }),
    stone: mat(0xc9c3b5),
    timber: mat(0x6b4f3a),
    timberLight: mat(0x8a6a4f),
    roof: mat(0x3d4a52),
    iron: mat(0x2b2f33, { metalness: 0.5, roughness: 0.6 }),
    seabed: mat(0x3a4a42),
    cliff: mat(0x7e7b73, { flatShading: true }),
    windowDark: mat(0x1a1f24, { roughness: 0.3 }),
    windowLit: new THREE.MeshStandardMaterial({ color: 0xffd08a, emissive: 0xffb347, emissiveIntensity: 1.6 }),
    ember: new THREE.MeshStandardMaterial({ color: 0x331a0a, emissive: 0xff7a1a, emissiveIntensity: 0 }),
    coals: new THREE.MeshStandardMaterial({ color: 0x331a0a, emissive: 0xff7a1a, emissiveIntensity: 1.4 }),
    lantern: new THREE.MeshStandardMaterial({ color: 0xffd08a, emissive: 0xffb347, emissiveIntensity: 2 }),
    invisible: new THREE.MeshBasicMaterial({ visible: false }),
  };
  /** Always-solid meshes. */
  private readonly solids: THREE.Mesh[] = [];
  private windows: THREE.Mesh[] = [];
  private readonly dockMissing: THREE.Mesh[] = [];
  private readonly planks: THREE.Mesh[] = [];
  private readonly piles: THREE.Mesh[] = [];
  private readonly npcBodies = new Map<NpcId, THREE.Mesh>();
  private readonly familyGroup = new THREE.Group();
  private readonly familyBodies: THREE.Mesh[] = [];
  /** People, once their models arrive from Polyfork's CDN. */
  private readonly villagers: { v: Villager; group: THREE.Object3D }[] = [];
  private readonly forgeGlow: THREE.PointLight;
  private readonly hearthLight: THREE.PointLight;
  private readonly boats: THREE.Group[] = [];
  private readonly smoke: THREE.Mesh[] = [];
  private readonly smokeFrom = new THREE.Vector3(-16 + 1.2, CLIFF_TOP + 6, -6 + 0.6);
  private readonly cliffSides: THREE.Mesh;
  private readonly rimRocks: { mesh: THREE.Mesh; size: number }[] = [];
  private readonly door: THREE.Mesh;
  private readonly hearth: Piece;
  private readonly chest: Piece;
  private readonly forge: Piece;
  private readonly cottages: Piece[] = [];
  private readonly tidePoles: Piece[] = [];
  private readonly posts: { piece: Piece; light: THREE.PointLight }[] = [];
  private readonly sign: Piece;
  /** Broken and repaired forge models, once dressed. */
  private forgeModels: [THREE.Object3D, THREE.Object3D] | null = null;
  private dressed = false;
  private dockFixed = false;
  private boatsVisible = 1;

  constructor() {
    const r = rng(7);
    const M = this.M;
    this.root.name = "home";

    // Headland: always-dry rock (top y=3 > 2.4 dry band). The solid cylinder is
    // collision only; the painted grass top and the cliff faces are what you see.
    const headland = new THREE.Mesh(new THREE.CylinderGeometry(RADIUS, 52, 12, 64), M.invisible);
    headland.position.y = CLIFF_TOP - 6;
    this.root.add(headland);
    this.solids.push(headland);
    this.cliffSides = new THREE.Mesh(new THREE.CylinderGeometry(RADIUS, 52, 12, 64, 1, true), M.cliff);
    this.cliffSides.position.y = CLIFF_TOP - 6;
    this.cliffSides.receiveShadow = true;
    this.root.add(this.cliffSides);
    this.root.add(headlandTop(RADIUS, CLIFF_TOP, PATHS, WORN));

    const seabed = new THREE.Mesh(new THREE.PlaneGeometry(700, 700), M.seabed);
    seabed.rotation.x = -Math.PI / 2;
    seabed.position.y = -5;
    this.add(seabed, true);

    // Cliff rocks around the rim (kept clear of the dock mouth and the cliff path).
    for (let i = 0; i < 70; i++) {
      const a = r() * Math.PI * 2;
      const d = 44 + r() * 7;
      const s = 1.5 + r() * 3.5;
      const rock = new THREE.Mesh(new THREE.DodecahedronGeometry(s, 0), M.rock);
      rock.position.set(Math.cos(a) * d, CLIFF_TOP - 2 - r() * 4, Math.sin(a) * d);
      rock.rotation.set(r() * 3, r() * 3, r() * 3);
      if (Math.abs(rock.position.x - DOCK_X) < 5 && rock.position.z > 30) continue;
      if (rock.position.x < -30 && Math.abs(rock.position.z - 8) < 6) continue;
      rock.castShadow = rock.receiveShadow = true;
      this.root.add(rock);
      this.rimRocks.push({ mesh: rock, size: s });
    }

    // Lighthouse.
    this.lighthouse.group.position.set(22, CLIFF_TOP, -20);
    this.root.add(this.lighthouse.group);
    this.solidCylinder(22, -20, 3.8, CLIFF_TOP, 30);
    this.door = new THREE.Mesh(new THREE.BoxGeometry(1.4, 2.4, 0.3), M.timber);
    this.door.position.set(22, CLIFF_TOP + 1.2, -16.25);
    this.root.add(this.door);
    this.interacts.push({ id: "lamp", object: this.door, range: 3.6 });

    // Square: hearth + storage within 10 m (quick prep).
    const hearth = new THREE.Group();
    const hearthParts: THREE.Mesh[] = [];
    for (let i = 0; i < 9; i++) {
      const a = (i / 9) * Math.PI * 2;
      const s = new THREE.Mesh(new THREE.DodecahedronGeometry(0.35, 0), M.rock);
      s.position.set(Math.cos(a) * 0.9, 0.2, Math.sin(a) * 0.9);
      hearth.add(s);
      hearthParts.push(s);
    }
    const coals = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.7, 0.15, 12), M.coals);
    coals.position.y = 0.1;
    hearth.add(coals);
    hearthParts.push(coals);
    hearth.position.set(0, CLIFF_TOP, 2);
    this.root.add(hearth);
    this.hearth = { group: hearth, parts: hearthParts };
    this.solidCylinder(0, 2, 1.1, CLIFF_TOP, CLIFF_TOP + 0.6);
    this.hearthLight = new THREE.PointLight(0xff9a40, 25, 14, 1.6);
    this.hearthLight.position.set(0, CLIFF_TOP + 1.2, 2);
    this.root.add(this.hearthLight);
    this.interacts.push({ id: "hearth", object: coals, range: 3.6 });

    const chest = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.8, 0.8), M.timberLight);
    chest.position.set(-4, CLIFF_TOP + 0.4, -1);
    this.add(chest, true);
    const lid = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.12, 0.9), M.timber);
    lid.position.set(-4, CLIFF_TOP + 0.86, -1);
    this.root.add(lid);
    this.chest = { group: this.root, parts: [chest, lid] };
    this.interacts.push({ id: "storage", object: chest, range: 3.6 });

    // Cottages, two windows each.
    for (const [x, z, rot] of COTTAGES) this.cottages.push(this.cottage(x, z, rot));

    // Forge (broken → repaired).
    const forge = new THREE.Group();
    const base = new THREE.Mesh(new THREE.BoxGeometry(4, 2.2, 3), M.stone);
    base.position.y = 1.1;
    const chimney = new THREE.Mesh(new THREE.BoxGeometry(1, 3, 1), M.stone);
    chimney.position.set(1.2, 3.5, 0.6);
    const mouth = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.9, 0.1), M.ember);
    mouth.position.set(0, 0.9, 1.52);
    const anvil = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.5, 0.4), M.iron);
    anvil.position.set(-2.6, 0.55, 2.2);
    forge.add(base, chimney, mouth, anvil);
    forge.position.set(12, CLIFF_TOP, 6);
    forge.traverse((o) => (o.castShadow = o.receiveShadow = true));
    this.root.add(forge);
    this.solids.push(base);
    this.forge = { group: forge, parts: [base, chimney, mouth, anvil] };
    this.forgeGlow = new THREE.PointLight(0xff7a1a, 0, 10, 1.8);
    this.forgeGlow.position.set(12, CLIFF_TOP + 1, 8.2);
    this.root.add(this.forgeGlow);
    this.interacts.push({ id: "forge", object: mouth, range: 3.6 });

    // Dock (DOCK_Y > 1.8 high water, so it never floods). Starts at the cliff
    // edge, 0.3 m below the grass: a step down, not a ramp.
    for (let i = 0; i < 30; i++) {
      const plank = new THREE.Mesh(new THREE.BoxGeometry(3, 0.15, 0.95), i % 3 === 0 ? M.timberLight : M.timber);
      plank.position.set(DOCK_X, DOCK_Y - 0.075, 45 + i);
      plank.castShadow = plank.receiveShadow = true;
      this.root.add(plank);
      this.planks.push(plank);
      if (MISSING_PLANKS.includes(i)) this.dockMissing.push(plank);
      else this.solids.push(plank);
    }
    for (let i = 0; i < 8; i++) {
      for (const side of [-1.4, 1.4]) {
        const pile = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.22, 8, 8), M.timber);
        pile.position.set(DOCK_X + side, DOCK_Y - 4, 46 + i * 4);
        this.root.add(pile);
        this.piles.push(pile);
      }
    }

    for (let i = 0; i < 2; i++) {
      const boat = this.makeBoat();
      boat.position.set(DOCK_X + 3.2 - i * 6.4, 0, 70 - i * 6);
      this.boats.push(boat);
      this.root.add(boat);
    }
    this.interacts.push({ id: "boat", object: this.boats[0]!, range: 4.5 });

    // Tide poles beside the dock: bands at low (white), mid (yellow), high (red).
    this.tidePoles.push(this.tidePole(DOCK_X - 3, 52), this.tidePole(DOCK_X + 4, 62));

    // Lantern posts along the paths.
    for (const [x, z] of LANTERN_POSTS) this.posts.push(this.lanternPost(x, z));

    // Cliff path down to Gullwash Shore: a signpost at the west edge.
    const sign = new THREE.Group();
    const post = new THREE.Mesh(new THREE.BoxGeometry(0.2, 2.2, 0.2), M.timber);
    post.position.y = 1.1;
    const board = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.45, 0.08), M.timberLight);
    board.position.set(-0.5, 1.8, 0);
    sign.add(post, board);
    sign.position.set(-41, CLIFF_TOP, 11);
    sign.rotation.y = Math.PI / 2;
    sign.traverse((o) => (o.castShadow = true));
    this.root.add(sign);
    this.sign = { group: sign, parts: [post, board] };
    this.solidCylinder(-41, 11, 0.2, CLIFF_TOP, CLIFF_TOP + 2.2);
    this.interacts.push({ id: "path_shore", object: sign, range: 3.6 });

    // NPCs (placeholder capsules). Hesk arrives with the Restored Lamp.
    this.npc("maren", 0xb8b0a0, 19.5, -15.5);
    this.npc("odile", 0x9c5a3c, -1.8, 4.2);
    this.npc("tib", 0x4d6a7a, 3.6, 42.5);
    this.npc("hesk", 0x6e4a36, 15.5, 9.5);

    // A survivor family by the new cottage (stage 2), not interactive.
    for (const [x, z, h, c] of [
      [-12.5, 26, 1.1, 0x7d6b8a],
      [-11.2, 26.6, 0.8, 0x8a7a5a],
      [-13.6, 26.9, 1.0, 0x5a7a6b],
    ] as const) {
      const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.3, h, 4, 8), mat(c));
      body.position.set(x, CLIFF_TOP + h / 2 + 0.3, z);
      body.castShadow = true;
      this.familyGroup.add(body);
      this.familyBodies.push(body);
    }
    this.root.add(this.familyGroup);

    // Chimney smoke over Odile's cottage once the lamp is restored.
    const smokeMat = new THREE.MeshBasicMaterial({ color: 0xb8b8b8, transparent: true, opacity: 0.25, depthWrite: false });
    for (let i = 0; i < 6; i++) {
      const puff = new THREE.Mesh(new THREE.SphereGeometry(0.5, 8, 6), smokeMat);
      puff.visible = false;
      this.smoke.push(puff);
      this.root.add(puff);
    }

    // Safe anchors on the cliff top for the anti-trap current.
    this.anchors.push(new THREE.Vector3(DOCK_X, DOCK_Y, 45), new THREE.Vector3(-30, CLIFF_TOP, 30), new THREE.Vector3(-35, CLIFF_TOP, -20), new THREE.Vector3(32, CLIFF_TOP, 10));

    this.collider = this.buildCollider();
  }

  /**
   * Lays the Blender models over the greybox: home.glb's buildings, dock, boats,
   * cliff and rocks, props.glb's posts, sign, tide poles and grass. Each greybox
   * part keeps its place as collision (and as the raycast target for its
   * interaction) but stops drawing. COL_ boxes in the models become solid.
   */
  dress(assets: Assets): void {
    if (this.dressed) return;
    this.dressed = true;
    const home = (name: string) => assets.clone("home.glb", name);

    const tower = home("HOME_lighthouse");
    if (tower) {
      this.lighthouse.dress(tower);
      this.hide(this.door);
    }

    const cliff = home("HOME_cliff");
    if (cliff) {
      this.root.add(cliff);
      this.cliffSides.visible = false;
    }
    this.rimRocks.forEach(({ mesh, size }, i) => {
      const rock = home(`HOME_rock_${i % 6}`);
      if (!rock) return;
      rock.position.copy(mesh.position);
      rock.rotation.y = mesh.rotation.y * 2.1;
      rock.scale.setScalar(size * 1.05);
      this.root.add(rock);
      mesh.visible = false;
    });

    const hearth = home("HOME_hearth");
    if (hearth) {
      this.hide(...this.hearth.parts);
      this.hearth.group.add(hearth);
      this.swapMaterial(hearth, "EMBER", this.M.coals);
      this.takeCollision(hearth);
    }
    const chest = home("HOME_chest");
    if (chest) {
      this.hide(...this.chest.parts);
      chest.position.set(-4, CLIFF_TOP, -1);
      this.root.add(chest);
    }

    const panes: THREE.Mesh[] = [];
    this.cottages.forEach((c, i) => {
      const model = home(COTTAGE_MODELS[i % COTTAGE_MODELS.length]!);
      if (!model) return;
      this.hide(...c.parts);
      c.group.add(model);
      this.takeCollision(model);
      const mine: THREE.Mesh[] = [];
      model.traverse((o) => {
        if (o.name.startsWith("window") && (o as THREE.Mesh).isMesh) mine.push(o as THREE.Mesh);
      });
      mine.sort((a, b) => a.position.x - b.position.x);
      panes.push(...mine);
      if (i === 0) model.getObjectByName("smoke")?.getWorldPosition(this.smokeFrom);
    });
    if (panes.length === this.windows.length) this.windows = panes;

    const forgeOn = home("HOME_forge");
    const forgeOff = home("HOME_forge_broken");
    if (forgeOn && forgeOff) {
      this.hide(...this.forge.parts);
      for (const f of [forgeOn, forgeOff]) {
        this.swapMaterial(f, "EMBER", this.M.ember);
        this.forge.group.add(f);
      }
      this.takeCollision(forgeOn);
      this.takeCollision(forgeOff, false);
      this.forgeModels = [forgeOff, forgeOn];
    }

    this.planks.forEach((p, i) => {
      const board = home(MISSING_PLANKS.includes(i) ? "HOME_dock_plank_new" : `HOME_dock_plank_${i % 3}`);
      if (!board) return;
      this.hide(p);
      board.rotation.y = (i % 2) * Math.PI;
      p.add(board);
    });
    const frame = home("HOME_dock_frame");
    if (frame) {
      frame.position.x = DOCK_X;
      this.root.add(frame);
      for (const pile of this.piles) pile.visible = false;
    }
    for (const b of this.boats) {
      const boat = home("HOME_sailboat");
      if (!boat) break;
      for (const c of [...b.children]) if ((c as THREE.Mesh).isMesh) this.hide(c as THREE.Mesh);
      b.add(boat);
    }

    for (const t of this.tidePoles) {
      const pole = assets.prop("tide_pole");
      if (!pole) break;
      for (const m of t.parts) m.visible = false;
      pole.position.set(t.parts[0]!.position.x, 0, t.parts[0]!.position.z);
      this.root.add(pole);
    }
    this.posts.forEach(({ piece, light }, i) => {
      const post = assets.prop("lantern_post");
      if (!post) return;
      const [stem, lamp] = piece.parts as [THREE.Mesh, THREE.Mesh];
      this.hide(stem);
      lamp.visible = false;
      const yaw = (i * 2.3) % (Math.PI * 2);
      post.position.set(stem.position.x, CLIFF_TOP, stem.position.z);
      post.rotation.y = yaw;
      this.root.add(post);
      // The prop's lantern hangs 0.5 m out along its arm, 1.9 m up.
      light.position.set(stem.position.x + Math.cos(yaw) * 0.5, CLIFF_TOP + 1.9, stem.position.z - Math.sin(yaw) * 0.5);
    });
    const sign = assets.prop("signpost");
    if (sign) {
      this.hide(...this.sign.parts);
      this.sign.group.add(sign);
    }
    this.scatterGrass(assets);
    this.loadVillagers();

    this.root.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh && m.material !== this.M.invisible) m.castShadow = m.receiveShadow = true;
    });
    this.collider = this.buildCollider();

    // Everything progression or time touches stays separate; the rest of the village is merged.
    const live = new Set<THREE.Object3D>([...this.windows, ...this.dockMissing, ...this.boats, ...this.smoke, this.familyGroup, this.lighthouse.group, this.door]);
    if (this.forgeModels) for (const f of this.forgeModels) live.add(f);
    for (const body of this.npcBodies.values()) live.add(body.parent!);
    for (const it of this.interacts) live.add(it.object);
    batchStatic(this.root, (o) => live.has(o));
  }

  private add(mesh: THREE.Mesh, solid: boolean): void {
    mesh.castShadow = mesh.receiveShadow = true;
    this.root.add(mesh);
    if (solid) this.solids.push(mesh);
  }

  /** Stops a greybox mesh drawing (and casting shadows); it stays collision and a raycast target. */
  private hide(...meshes: THREE.Mesh[]): void {
    for (const m of meshes) {
      m.material = this.M.invisible;
      m.castShadow = m.receiveShadow = false;
    }
  }

  private swapMaterial(root: THREE.Object3D, name: string, to: THREE.Material): void {
    root.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      if (Array.isArray(m.material)) m.material = m.material.map((x) => (x.name === name ? to : x));
      else if (m.material.name === name) m.material = to;
    });
  }

  /** A model's COL_ boxes stop drawing; with solid, they join the collision. */
  private takeCollision(model: THREE.Object3D, solid = true): void {
    model.traverse((o) => {
      if (!o.name.startsWith("COL_")) return;
      o.traverse((c) => {
        const m = c as THREE.Mesh;
        if (!m.isMesh) return;
        this.hide(m);
        if (solid) this.solids.push(m);
      });
    });
  }

  /**
   * Swaps the placeholder figures for Polyfork villagers as they arrive from the
   * CDN (src/data/villagers.ts). A capsule stays behind, invisible, as the
   * NPC's collision and the target you talk to.
   */
  private loadVillagers(): void {
    for (const [id, body] of this.npcBodies) {
      const group = body.parent!;
      void Villager.load(NPC_LOOKS[id]).then((v) => {
        if (!v) return;
        for (const c of group.children) if ((c as THREE.Mesh).isMesh) this.hide(c as THREE.Mesh);
        group.add(v.object);
        this.villagers.push({ v, group });
      });
    }
    FAMILY_LOOKS.forEach((look, i) => {
      const body = this.familyBodies[i];
      if (!body) return;
      void Villager.load(look).then((v) => {
        if (!v) return;
        this.hide(body);
        const spot = new THREE.Group();
        spot.position.set(body.position.x, CLIFF_TOP, body.position.z);
        spot.add(v.object);
        this.familyGroup.add(spot);
        this.villagers.push({ v, group: spot });
      });
    });
  }

  /** Grass tufts on the open turf (instanced), thicker and taller toward the cliff edge. */
  private scatterGrass(assets: Assets): void {
    const src = assets.prop("dune_grass");
    if (!src) return;
    const r = rng(11);
    const mats: THREE.Matrix4[] = [];
    const q = new THREE.Quaternion();
    const e = new THREE.Euler();
    for (let tries = 0; tries < 1400 && mats.length < 320; tries++) {
      const a = r() * Math.PI * 2;
      const d = Math.sqrt(r()) * (RADIUS - 1);
      const x = Math.cos(a) * d;
      const z = Math.sin(a) * d;
      if (CLEAR.some(([cx, cz, cr]) => Math.hypot(x - cx, z - cz) < cr)) continue;
      if (wear(x, z, PATHS, WORN) > 0.15) continue;
      const edge = Math.max(0, (d - 36) / 10);
      if (r() > 0.35 + edge * 0.65) continue;
      const s = 0.35 + r() * 0.3 + edge * 0.5;
      q.setFromEuler(e.set(0, r() * Math.PI * 2, 0));
      mats.push(new THREE.Matrix4().compose(new THREE.Vector3(x, CLIFF_TOP, z), q, new THREE.Vector3(s, s * (0.8 + r() * 0.4), s)));
    }
    src.updateWorldMatrix(true, true);
    src.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      const inst = new THREE.InstancedMesh(m.geometry, m.material, mats.length);
      mats.forEach((mx, i) => inst.setMatrixAt(i, mx.clone().multiply(m.matrixWorld)));
      inst.receiveShadow = true;
      inst.name = "grass";
      this.root.add(inst);
    });
  }

  /** Invisible collision cylinder (lighthouse, hearth ring, posts). */
  private solidCylinder(x: number, z: number, r: number, y0: number, y1: number): void {
    const c = new THREE.Mesh(new THREE.CylinderGeometry(r, r, y1 - y0, 12), this.M.invisible);
    c.position.set(x, (y0 + y1) / 2, z);
    this.root.add(c);
    this.solids.push(c);
  }

  private cottage(x: number, z: number, rot: number): Piece {
    const M = this.M;
    const g = new THREE.Group();
    const body = new THREE.Mesh(new THREE.BoxGeometry(6, 3.2, 5), M.stone);
    body.position.y = 1.6;
    const roof = new THREE.Mesh(new THREE.ConeGeometry(4.9, 2.4, 4), M.roof);
    roof.position.y = 4.4;
    roof.rotation.y = Math.PI / 4;
    const door = new THREE.Mesh(new THREE.PlaneGeometry(1, 1.9), M.timber);
    door.position.set(0, 0.95, 2.51);
    g.add(body, roof, door);
    const parts = [body, roof, door];
    for (const wx of [-1.9, 1.9]) {
      const w = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 1), M.windowDark);
      w.position.set(wx, 1.9, 2.51);
      g.add(w);
      this.windows.push(w);
      parts.push(w);
    }
    g.position.set(x, CLIFF_TOP, z);
    g.rotation.y = rot;
    g.traverse((o) => (o.castShadow = o.receiveShadow = true));
    this.root.add(g);
    this.solids.push(body);
    return { group: g, parts };
  }

  private tidePole(x: number, z: number): Piece {
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 8, 8), this.M.timber);
    pole.position.set(x, -0.5, z);
    this.root.add(pole);
    const parts = [pole];
    for (const [y, c] of [
      [0, 0xe8e4da],
      [0.9, 0xe0b040],
      [1.8, 0xb03a2e],
    ] as const) {
      const band = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.18, 8), mat(c));
      band.position.set(x, y, z);
      this.root.add(band);
      parts.push(band);
    }
    return { group: this.root, parts };
  }

  private lanternPost(x: number, z: number): { piece: Piece; light: THREE.PointLight } {
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 2.4, 6), this.M.iron);
    post.position.set(x, CLIFF_TOP + 1.2, z);
    const lamp = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.4, 0.3), this.M.lantern);
    lamp.position.set(x, CLIFF_TOP + 2.5, z);
    this.root.add(post, lamp);
    this.solids.push(post);
    const light = new THREE.PointLight(0xffb347, 6, 9, 1.8);
    light.position.copy(lamp.position);
    this.root.add(light);
    return { piece: { group: this.root, parts: [post, lamp] }, light };
  }

  private npc(id: NpcId, color: number, x: number, z: number): void {
    const g = new THREE.Group();
    const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.35, 1.1, 4, 8), mat(color));
    body.position.y = 0.9;
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.24, 12, 8), mat(0xd9b48f));
    head.position.y = 1.85;
    g.add(body, head);
    g.position.set(x, CLIFF_TOP, z);
    g.traverse((o) => (o.castShadow = true));
    this.root.add(g);
    this.npcBodies.set(id, body);
    this.interacts.push({ id: `npc:${id}`, object: g, range: 3.2 });
  }

  private makeBoat(): THREE.Group {
    const M = this.M;
    const g = new THREE.Group();
    const hull = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.7, 5), M.timber);
    hull.position.y = 0.2;
    const bow = new THREE.Mesh(new THREE.ConeGeometry(0.9, 1.6, 4), M.timber);
    bow.rotation.x = Math.PI / 2;
    bow.rotation.y = Math.PI / 4;
    bow.position.set(0, 0.2, 3.3);
    const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 4, 6), M.timberLight);
    mast.position.y = 2.2;
    g.add(hull, bow, mast);
    g.traverse((o) => (o.castShadow = true));
    return g;
  }

  private buildCollider(): StaticCollider {
    const meshes = [...this.solids];
    if (this.dockFixed) meshes.push(...this.dockMissing);
    for (const body of this.npcBodies.values()) if (body.parent?.visible) meshes.push(body);
    return new StaticCollider(meshes);
  }

  /** Make the world match progression: windows, forge, dock, residents, boats, beam. */
  applyProgress(visuals: StageVisuals, projects: readonly ProjectId[], stage: StageIndex): void {
    const M = this.M;
    this.windows.forEach((w, i) => (w.material = i < visuals.windowsLit ? M.windowLit : M.windowDark));
    const forgeLit = projects.includes("forge");
    M.ember.emissiveIntensity = forgeLit ? 2.2 : 0;
    this.forgeGlow.intensity = forgeLit ? 14 : 0;
    if (this.forgeModels) {
      this.forgeModels[0].visible = !forgeLit;
      this.forgeModels[1].visible = forgeLit;
    }
    this.dockFixed = projects.includes("dock");
    for (const p of this.dockMissing) p.visible = this.dockFixed;
    for (const [id, body] of this.npcBodies) {
      const g = body.parent!;
      g.visible = NPCS[id].appearsAtStage <= stage;
    }
    for (const it of this.interacts) {
      if (it.id.startsWith("npc:")) it.object.visible = this.npcBodies.get(it.id.slice(4) as NpcId)?.parent?.visible ?? true;
    }
    this.familyGroup.visible = stage >= 2;
    this.boatsVisible = visuals.boats;
    this.boats.forEach((b, i) => (b.visible = i < this.boatsVisible));
    for (const s of this.smoke) s.visible = stage >= 1;
    this.lighthouse.applyStage(visuals);
    this.collider = this.buildCollider();
  }

  update(u: LevelUpdate): void {
    this.lighthouse.update(u.dt);
    this.boats.forEach((b, i) => {
      b.position.y = u.waterY + Math.sin(u.time * 1.3 + i) * 0.08;
      b.rotation.z = Math.sin(u.time * 0.9 + i * 2) * 0.04;
    });
    for (const { v, group } of this.villagers) {
      if (!group.visible || !group.parent?.visible) continue;
      v.update(u.dt, u.time, group.worldToLocal(tmpViewer.copy(u.viewer)));
    }
    const flicker = Math.sin(u.time * 9) * 3 + Math.sin(u.time * 23) * 2;
    this.hearthLight.intensity = 22 + flicker;
    this.M.coals.emissiveIntensity = 1.4 + flicker * 0.06;
    // Chimney smoke above Odile's cottage.
    const from = this.smokeFrom;
    this.smoke.forEach((s, i) => {
      const t = (u.time * 0.25 + i / this.smoke.length) % 1;
      s.position.set(from.x + t * 1.5, from.y + t * 5, from.z + t * 0.8);
      s.scale.setScalar(0.6 + t * 1.6);
    });
  }

  dispose(): void {
    disposeObject(this.root);
  }
}
