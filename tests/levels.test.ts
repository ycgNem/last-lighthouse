import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { ENEMY_IDS, NODE_IDS, NPC_IDS, PROJECT_IDS, type LocationId } from "../src/data/ids";
import { PROJECTS } from "../src/data/lighthouse";
import { LOCATIONS } from "../src/data/locations";
import { NPCS } from "../src/data/npcs";
import { TIDE } from "../src/data/tide";
import { FAMILIES } from "../src/data/villagers";
import { insideOutline } from "../src/systems/decor";

// Checks the exported Blender levels against what the game expects: the
// markers it reads (docs/ART_PIPELINE.md) and the counts in src/data/locations.ts,
// which the softlock simulation trusts. Reads the .glb's JSON chunk directly.

interface GltfNode {
  name?: string;
  extras?: Record<string, unknown>;
  /** Markers are top-level empties, so this is their world position (glTF is Y-up, like the game). */
  translation?: [number, number, number];
  children?: number[];
}

function nodesOf(id: LocationId): GltfNode[] {
  const buf = readFileSync(join(import.meta.dirname, "..", "public", "assets", "models", "locations", `${id}.glb`));
  expect(buf.toString("ascii", 0, 4)).toBe("glTF");
  const jsonLength = buf.readUInt32LE(12);
  expect(buf.toString("ascii", 16, 20)).toBe("JSON");
  const gltf = JSON.parse(buf.toString("utf8", 20, 20 + jsonLength)) as { nodes?: GltfNode[] };
  return gltf.nodes ?? [];
}

const named = (nodes: GltfNode[], prefix: string) => nodes.filter((n) => n.name?.startsWith(prefix));
const extra = (n: GltfNode, key: string) => n.extras?.[key];
const has = (nodes: GltfNode[], name: string) => nodes.some((n) => n.name === name);
const at = (nodes: GltfNode[], name: string) => nodes.find((n) => n.name === name)?.translation;
/** Everything under a node, however deep. */
const under = (nodes: GltfNode[], n: GltfNode): GltfNode[] => (n.children ?? []).flatMap((k) => [nodes[k]!, ...under(nodes, nodes[k]!)]);

describe.each(Object.keys(LOCATIONS) as LocationId[])("level %s", (id) => {
  const nodes = nodesOf(id);

  it("has a landing, a boat and anchors, and away from home a sight of its light", () => {
    expect(has(nodes, "SPAWN_landing")).toBe(true);
    expect(nodes.some((n) => extra(n, "interact") === "boat")).toBe(true);
    expect(named(nodes, "ANCHOR_").length).toBeGreaterThanOrEqual(2);
    expect(has(nodes, "FX_home_light")).toBe(id !== "home");
  });

  it("tags every marker with valid ids", () => {
    for (const n of named(nodes, "NODE_")) expect(NODE_IDS, n.name).toContain(extra(n, "node"));
    for (const n of named(nodes, "ENEMY_")) {
      expect(ENEMY_IDS, n.name).toContain(extra(n, "enemy"));
      expect(["low", "high", "any"], n.name).toContain(extra(n, "tide"));
    }
    for (const n of named(nodes, "TRIG_")) expect(typeof extra(n, "event"), n.name).toBe("string");
    for (const n of named(nodes, "INT_")) expect(typeof extra(n, "interact"), n.name).toBe("string");
    for (const n of named(nodes, "PLOT_")) expect(PROJECT_IDS, n.name).toContain(extra(n, "plot"));
    for (const n of named(nodes, "FX_ambush_")) expect(ENEMY_IDS, n.name).toContain(/^FX_ambush_(.+)_\d+$/.exec(n.name!)?.[1]);
  });

  it("has buoys that float freely through the whole tide", () => {
    for (const n of named(nodes, "BUOY_")) {
      const float = Number(extra(n, "float") ?? -0.45);
      const min = Number(extra(n, "min"));
      const max = Number(extra(n, "max"));
      expect(min, n.name).toBeLessThan(max);
      // Reaches its full floating height at high water (rests on its min at low).
      expect(max + 1e-6, n.name).toBeGreaterThanOrEqual(TIDE.highLevel + float);
    }
  });

  it("has its Gloom pockets, each with a radius, none over an anchor or the landing", () => {
    const gloom = named(nodes, "GLOOM_");
    expect(gloom.length).toBe(LOCATIONS[id].gloom);
    const pos = (n: GltfNode) => n.translation ?? [0, 0, 0];
    for (const g of gloom) {
      const r = Number(extra(g, "radius"));
      expect(r, g.name).toBeGreaterThan(1);
      expect(r, g.name).toBeLessThan(6);
      // The rescue current and the landing must never put you in the Gloom.
      for (const n of [...named(nodes, "ANCHOR_"), ...named(nodes, "SPAWN_")]) {
        const [gx, , gz] = pos(g);
        const [nx, , nz] = pos(n);
        expect(Math.hypot(gx - nx, gz - nz), `${g.name} vs ${n.name}`).toBeGreaterThan(r + 0.5);
      }
    }
  });

  it("matches the node and enemy counts in the location data", () => {
    const count = (list: { key: string }[]) => list.reduce<Record<string, number>>((m, x) => ((m[x.key] = (m[x.key] ?? 0) + 1), m), {});
    const levelNodes = count(named(nodes, "NODE_").map((n) => ({ key: String(extra(n, "node")) })));
    const dataNodes: Record<string, number> = {};
    for (const s of LOCATIONS[id].nodes) dataNodes[s.node] = (dataNodes[s.node] ?? 0) + s.count;
    expect(levelNodes).toEqual(dataNodes);

    const levelEnemies = count(named(nodes, "ENEMY_").map((n) => ({ key: `${String(extra(n, "enemy"))}/${String(extra(n, "tide"))}` })));
    const dataEnemies: Record<string, number> = {};
    for (const s of LOCATIONS[id].enemies) dataEnemies[`${s.enemy}/${s.tide}`] = (dataEnemies[`${s.enemy}/${s.tide}`] ?? 0) + s.count;
    expect(levelEnemies).toEqual(dataEnemies);
  });
});

describe("level specifics", () => {
  it("wreck: the lens, the ladder and the ambush", () => {
    const nodes = nodesOf("wreck");
    expect(named(nodes, "NODE_").some((n) => extra(n, "node") === "lens_pedestal")).toBe(true);
    expect(nodes.some((n) => extra(n, "interact") === "rope_ladder")).toBe(true);
    expect(has(nodes, "SPAWN_ladder")).toBe(true);
    expect(named(nodes, "FX_ambush_").length).toBeGreaterThanOrEqual(2);
    expect(named(nodes, "BUOY_crate").length).toBeGreaterThanOrEqual(3);
  });

  it("beacon: the arena, the Guardian, the gate and the lamp", () => {
    const nodes = nodesOf("beacon");
    expect(named(nodes, "TRIG_").some((n) => extra(n, "event") === "boss")).toBe(true);
    expect(named(nodes, "ENEMY_").some((n) => extra(n, "enemy") === "wreck_guardian")).toBe(true);
    for (const name of ["FX_arena", "FX_beacon_lamp", "STATE_guardian_defeated_off", "STATE_guardian_defeated_on"]) expect(has(nodes, name), name).toBe(true);
    expect(nodes.some((n) => extra(n, "interact") === "beacon")).toBe(true);
  });

  it("home: where you wake and come ashore, all above high water, and the lighthouse, hearth, chest and lamp", () => {
    const nodes = nodesOf("home");
    for (const name of ["SPAWN_start", "SPAWN_landing", "SPAWN_jetty"]) expect(at(nodes, name)?.[1], name).toBeGreaterThan(TIDE.highLevel);
    expect(has(nodes, "PLACE_lighthouse")).toBe(true);
    for (const id of ["lamp", "hearth", "storage"]) expect(nodes.some((n) => extra(n, "interact") === id), id).toBe(true);
  });

  it("home: a plot for every project, with its ruin, the building, a board to rebuild it at and its station", () => {
    const nodes = nodesOf("home");
    for (const id of PROJECT_IDS) {
      const plot = nodes.find((n) => n.name === `PLOT_${id}`);
      expect(plot, id).toBeDefined();
      const part = (name: string) => (plot!.children ?? []).map((k) => nodes[k]!).find((n) => n.name?.startsWith(`${id}_${name}`));
      expect(part("ruin"), `${id}_ruin`).toBeDefined();
      expect(part("built"), `${id}_built`).toBeDefined();
      expect(part("board") && extra(part("board")!, "interact"), `${id}_board`).toBe(`plot:${id}`);
      // src/world/home/Plot.ts finds where you work it by name.
      if (PROJECTS[id].unlocksStation || PROJECTS[id].unlocksOffshore) expect(under(nodes, part("built")!).some((n) => n.name?.startsWith("station")), `${id}'s station`).toBe(true);
    }
  });

  it("home: a place for everyone who comes home", () => {
    const nodes = nodesOf("home");
    for (const id of NPC_IDS) expect(has(nodes, NPCS[id].marker), id).toBe(true);
    FAMILIES.forEach((family, f) => family.forEach((_, i) => expect(has(nodes, `PLACE_family_${f}_${i}`), `family ${f}, ${i}`).toBe(true)));
  });

  it("home: the drift comes in toward the beach, and what washes up lies above high water", () => {
    const nodes = nodesOf("home");
    const [lx, , lz] = at(nodes, "SPAWN_landing")!;
    const fromBeach = ([x, , z]: [number, number, number]) => Math.hypot(x - lx, z - lz);
    let lanes = 0;
    for (; has(nodes, `FX_drift_${lanes}_0`); lanes++) {
      const lane: [number, number, number][] = [];
      for (let k = 0; at(nodes, `FX_drift_${lanes}_${k}`); k++) lane.push(at(nodes, `FX_drift_${lanes}_${k}`)!);
      expect(lane.length, `lane ${lanes}`).toBeGreaterThanOrEqual(3);
      expect(fromBeach(lane[0]!), `lane ${lanes}`).toBeGreaterThan(fromBeach(lane.at(-1)!) + 20);
    }
    expect(lanes).toBeGreaterThanOrEqual(3);
    const strand = named(nodes, "FX_strand_");
    expect(strand.length).toBeGreaterThanOrEqual(6);
    for (const n of strand) expect(n.translation?.[1], n.name).toBeGreaterThan(TIDE.highLevel);
  });

  it("home: the village outline takes in the square and every plot but none of the open sea, and the clearings have a size", () => {
    const nodes = nodesOf("home");
    const outline: [number, number][] = [];
    for (let k = 0; at(nodes, `FX_decor_${k}`); k++) outline.push([at(nodes, `FX_decor_${k}`)![0], at(nodes, `FX_decor_${k}`)![2]]);
    expect(outline.length).toBeGreaterThanOrEqual(3);
    const inside = (name: string) => {
      const [x, , z] = at(nodes, name)!;
      return insideOutline(outline, x, z);
    };
    for (const n of [...named(nodes, "PLOT_"), ...named(nodes, "INT_")]) expect(inside(n.name!), n.name).toBe(true);
    for (const n of named(nodes, "FX_drift_").filter((n) => n.name!.endsWith("_0"))) expect(inside(n.name!), n.name).toBe(false);
    const clear = named(nodes, "CLEAR_");
    expect(clear.length).toBeGreaterThan(0);
    for (const n of clear) expect(Number(extra(n, "radius")), n.name).toBeGreaterThan(0);
  });
});
