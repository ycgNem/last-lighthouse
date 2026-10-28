import * as THREE from "three";
import { rng } from "../../core/math";
import type { NpcId, ProjectId, StageIndex } from "../../data/ids";
import type { StageVisuals } from "../../data/lighthouse";
import { NPCS } from "../../data/npcs";
import { StaticCollider } from "../../physics/StaticCollider";
import type { EnemyMarker, Level, LevelInteract, LevelUpdate, NodeMarker } from "../Level";
import { disposeObject } from "../Level";
import { Lighthouse } from "../Lighthouse";

// Lantern's Rest, built in code and laid out per docs/LEVELS.md. The three
// expedition locations come from Blender; home stays procedural for now
// because so much of it changes with progression (see applyProgress).

const CLIFF_TOP = 3;
const DOCK_Y = 2.7;
const DOCK_X = 6;

const mat = (color: number, extra: THREE.MeshStandardMaterialParameters = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.85, ...extra });

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
  readonly points = new Map<string, THREE.Vector3>();
  readonly lighthouse = new Lighthouse();

  private readonly M = {
    grass: mat(0x5b6b47),
    path: mat(0x8a7d62),
    rock: mat(0x8d8a80, { flatShading: true }),
    stone: mat(0xc9c3b5),
    timber: mat(0x6b4f3a),
    timberLight: mat(0x8a6a4f),
    roof: mat(0x3d4a52),
    iron: mat(0x2b2f33, { metalness: 0.5, roughness: 0.6 }),
    seabed: mat(0x3a4a42),
    windowDark: mat(0x1a1f24, { roughness: 0.3 }),
    windowLit: new THREE.MeshStandardMaterial({ color: 0xffd08a, emissive: 0xffb347, emissiveIntensity: 1.6 }),
    ember: new THREE.MeshStandardMaterial({ color: 0x331a0a, emissive: 0xff7a1a, emissiveIntensity: 0 }),
    lantern: new THREE.MeshStandardMaterial({ color: 0xffd08a, emissive: 0xffb347, emissiveIntensity: 2 }),
    invisible: new THREE.MeshBasicMaterial({ visible: false }),
  };
  /** Always-solid meshes. */
  private readonly solids: THREE.Mesh[] = [];
  private readonly windows: THREE.Mesh[] = [];
  private readonly dockMissing: THREE.Mesh[] = [];
  private readonly npcBodies = new Map<NpcId, THREE.Mesh>();
  private readonly familyGroup = new THREE.Group();
  private readonly forgeGlow: THREE.PointLight;
  private readonly hearthLight: THREE.PointLight;
  private readonly boats: THREE.Group[] = [];
  private readonly smoke: THREE.Mesh[] = [];
  private dockFixed = false;
  private boatsVisible = 1;

  constructor() {
    const r = rng(7);
    const M = this.M;
    this.root.name = "home";

    // Headland: always-dry rock (top y=3 > 2.4 dry band).
    const headland = new THREE.Mesh(new THREE.CylinderGeometry(46, 52, 12, 64), M.grass);
    headland.position.y = CLIFF_TOP - 6;
    this.add(headland, true);

    const seabed = new THREE.Mesh(new THREE.PlaneGeometry(700, 700), M.seabed);
    seabed.rotation.x = -Math.PI / 2;
    seabed.position.y = -5;
    this.add(seabed, true);

    // Worn paths between the lighthouse, the square, the dock and the cliff path.
    for (const [x1, z1, x2, z2] of [
      [22, -15, 2, 0],
      [2, 0, 6, 44],
      [-4, 4, -40, 8],
    ] as const) {
      const len = Math.hypot(x2 - x1, z2 - z1);
      const p = new THREE.Mesh(new THREE.PlaneGeometry(2.6, len), M.path);
      p.rotation.x = -Math.PI / 2;
      p.rotation.z = Math.atan2(x2 - x1, z2 - z1);
      p.position.set((x1 + x2) / 2, CLIFF_TOP + 0.02, (z1 + z2) / 2);
      p.receiveShadow = true;
      this.root.add(p);
    }

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
    }

    // Lighthouse.
    this.lighthouse.group.position.set(22, CLIFF_TOP, -20);
    this.root.add(this.lighthouse.group);
    this.solidCylinder(22, -20, 3.8, CLIFF_TOP, 30);
    const door = new THREE.Mesh(new THREE.BoxGeometry(1.4, 2.4, 0.3), M.timber);
    door.position.set(22, CLIFF_TOP + 1.2, -16.25);
    this.root.add(door);
    this.interacts.push({ id: "lamp", object: door, range: 3.6 });

    // Square: hearth + storage within 10 m (quick prep).
    const hearth = new THREE.Group();
    for (let i = 0; i < 9; i++) {
      const a = (i / 9) * Math.PI * 2;
      const s = new THREE.Mesh(new THREE.DodecahedronGeometry(0.35, 0), M.rock);
      s.position.set(Math.cos(a) * 0.9, 0.2, Math.sin(a) * 0.9);
      hearth.add(s);
    }
    const coals = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.7, 0.15, 12), new THREE.MeshStandardMaterial({ color: 0x331a0a, emissive: 0xff7a1a, emissiveIntensity: 1.4 }));
    coals.position.y = 0.1;
    hearth.add(coals);
    hearth.position.set(0, CLIFF_TOP, 2);
    this.root.add(hearth);
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
    this.interacts.push({ id: "storage", object: chest, range: 3.6 });

    // Cottages, two windows each. Windows light in order as the stage rises.
    const cottages: [number, number, number][] = [
      [-16, -6, 0.3],
      [-26, 10, -0.4],
      [-8, -24, 0.1],
      [-30, -14, 0.8],
      [-14, 22, -0.2],
    ];
    for (const [x, z, rot] of cottages) this.cottage(x, z, rot);

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
      if ([9, 10, 11, 18, 19].includes(i)) this.dockMissing.push(plank);
      else this.solids.push(plank);
    }
    for (let i = 0; i < 8; i++) {
      for (const side of [-1.4, 1.4]) {
        const pile = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.22, 8, 8), M.timber);
        pile.position.set(DOCK_X + side, DOCK_Y - 4, 46 + i * 4);
        this.root.add(pile);
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
    this.tidePole(DOCK_X - 3, 52);
    this.tidePole(DOCK_X + 4, 62);

    // Lantern posts along the paths.
    for (const [x, z] of [
      [16, -10],
      [6, -2],
      [4, 14],
      [5, 28],
      [7.8, 40],
      [-24, 6],
      [-38, 5],
    ] as const) {
      this.lanternPost(x, z);
    }

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

  private add(mesh: THREE.Mesh, solid: boolean): void {
    mesh.castShadow = mesh.receiveShadow = true;
    this.root.add(mesh);
    if (solid) this.solids.push(mesh);
  }

  /** Invisible collision cylinder (lighthouse, hearth ring, posts). */
  private solidCylinder(x: number, z: number, r: number, y0: number, y1: number): void {
    const c = new THREE.Mesh(new THREE.CylinderGeometry(r, r, y1 - y0, 12), this.M.invisible);
    c.position.set(x, (y0 + y1) / 2, z);
    this.root.add(c);
    this.solids.push(c);
  }

  private cottage(x: number, z: number, rot: number): void {
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
    for (const wx of [-1.9, 1.9]) {
      const w = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 1), M.windowDark);
      w.position.set(wx, 1.9, 2.51);
      g.add(w);
      this.windows.push(w);
    }
    g.position.set(x, CLIFF_TOP, z);
    g.rotation.y = rot;
    g.traverse((o) => (o.castShadow = o.receiveShadow = true));
    this.root.add(g);
    this.solids.push(body);
  }

  private tidePole(x: number, z: number): void {
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 8, 8), this.M.timber);
    pole.position.set(x, -0.5, z);
    this.root.add(pole);
    for (const [y, c] of [
      [0, 0xe8e4da],
      [0.9, 0xe0b040],
      [1.8, 0xb03a2e],
    ] as const) {
      const band = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.18, 8), mat(c));
      band.position.set(x, y, z);
      this.root.add(band);
    }
  }

  private lanternPost(x: number, z: number): void {
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 2.4, 6), this.M.iron);
    post.position.set(x, CLIFF_TOP + 1.2, z);
    const lamp = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.4, 0.3), this.M.lantern);
    lamp.position.set(x, CLIFF_TOP + 2.5, z);
    this.root.add(post, lamp);
    this.solids.push(post);
    const light = new THREE.PointLight(0xffb347, 6, 9, 1.8);
    light.position.copy(lamp.position);
    this.root.add(light);
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
    this.hearthLight.intensity = 22 + Math.sin(u.time * 9) * 3 + Math.sin(u.time * 23) * 2;
    // Chimney smoke above the first cottage.
    this.smoke.forEach((s, i) => {
      const t = (u.time * 0.25 + i / this.smoke.length) % 1;
      s.position.set(-16 + 1.2 + t * 1.5, CLIFF_TOP + 6 + t * 5, -6 + 0.6 + t * 0.8);
      s.scale.setScalar(0.6 + t * 1.6);
    });
  }

  dispose(): void {
    disposeObject(this.root);
  }
}
