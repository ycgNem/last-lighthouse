import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { ENEMY_IDS, NODE_IDS, type LocationId } from "../src/data/ids";
import { LOCATIONS } from "../src/data/locations";
import { TIDE } from "../src/data/tide";

// Checks the exported Blender levels against what the game expects: the
// markers it reads (docs/ART_PIPELINE.md) and the counts in src/data/locations.ts,
// which the softlock simulation trusts. Reads the .glb's JSON chunk directly.

interface GltfNode {
  name?: string;
  extras?: Record<string, unknown>;
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

const REMOTE = (Object.keys(LOCATIONS) as LocationId[]).filter((l) => l !== "home");

describe.each(REMOTE)("level %s", (id) => {
  const nodes = nodesOf(id);

  it("has a landing, a boat, anchors and the home light", () => {
    expect(has(nodes, "SPAWN_landing")).toBe(true);
    expect(nodes.some((n) => extra(n, "interact") === "boat")).toBe(true);
    expect(named(nodes, "ANCHOR_").length).toBeGreaterThanOrEqual(2);
    expect(has(nodes, "FX_home_light")).toBe(true);
  });

  it("tags every marker with valid ids", () => {
    for (const n of named(nodes, "NODE_")) expect(NODE_IDS, n.name).toContain(extra(n, "node"));
    for (const n of named(nodes, "ENEMY_")) {
      expect(ENEMY_IDS, n.name).toContain(extra(n, "enemy"));
      expect(["low", "high", "any"], n.name).toContain(extra(n, "tide"));
    }
    for (const n of named(nodes, "TRIG_")) expect(typeof extra(n, "event"), n.name).toBe("string");
    for (const n of named(nodes, "INT_")) expect(typeof extra(n, "interact"), n.name).toBe("string");
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
  it("shore: the cliff path both ways", () => {
    const nodes = nodesOf("shore");
    expect(has(nodes, "SPAWN_path")).toBe(true);
    expect(nodes.some((n) => extra(n, "interact") === "path_home")).toBe(true);
  });

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
});
