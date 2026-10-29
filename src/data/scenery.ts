import type { LocationId } from "./ids";

// The drowned world on each location's horizon: set pieces from scenery.glb
// (tools/blender/build/scenery.py) stood in the sea past where you can go. They
// face the location's centre unless `radial`, which points a line piece (the
// telegraph poles) straight out to sea from its first post. Keep them inside
// the fog (src/data/locations.ts: 140–220 m) and out of the line to the home
// beam, which every location shows on its horizon.

export const SCENE_PIECES = ["house_row", "spire", "poles", "stack", "dead_light", "masts", "windmill", "headland", "buoy"] as const;
export type ScenePiece = (typeof SCENE_PIECES)[number];

export interface HorizonPiece {
  piece: ScenePiece;
  x: number;
  z: number;
  scale?: number;
  /** Extra turn (radians) after facing in. */
  turn?: number;
  /** The piece's +x runs out to sea from (x, z) instead of it facing in. */
  radial?: boolean;
}

export const HORIZON: Record<LocationId, readonly HorizonPiece[]> = {
  home: [
    { piece: "spire", x: -30, z: -150 },
    { piece: "house_row", x: 42, z: -128 },
    { piece: "poles", x: 72, z: -62, radial: true },
    { piece: "dead_light", x: 160, z: -110 },
    { piece: "stack", x: 125, z: 15 },
    { piece: "stack", x: -118, z: -78, scale: 0.8, turn: 1.4 },
    { piece: "headland", x: -170, z: 20 },
    { piece: "masts", x: -62, z: 140, turn: 0.5 },
    { piece: "windmill", x: 96, z: 112 },
    { piece: "buoy", x: 30, z: 104 },
  ],
  shore: [
    { piece: "house_row", x: -18, z: -118 },
    { piece: "spire", x: 26, z: -136 },
    { piece: "poles", x: -40, z: -78, radial: true },
    { piece: "dead_light", x: 112, z: -118 },
    { piece: "masts", x: 92, z: -58, turn: 0.6 },
    { piece: "stack", x: -108, z: -52 },
    { piece: "stack", x: 118, z: 40, scale: 0.75, turn: 1.3 },
    { piece: "headland", x: -122, z: 4 },
    { piece: "windmill", x: 108, z: 2 },
    { piece: "buoy", x: 30, z: -72 },
    { piece: "buoy", x: 62, z: 74, scale: 0.9 },
  ],
  wreck: [
    { piece: "house_row", x: 25, z: 100 },
    { piece: "spire", x: -38, z: 112 },
    { piece: "poles", x: 70, z: 74, radial: true },
    { piece: "stack", x: 108, z: 5 },
    { piece: "stack", x: 100, z: 56, scale: 0.7, turn: 2 },
    { piece: "dead_light", x: 96, z: -86 },
    { piece: "masts", x: -104, z: 16, turn: 0.4 },
    { piece: "headland", x: -96, z: 86 },
    { piece: "windmill", x: 40, z: -106 },
    { piece: "buoy", x: -80, z: -40 },
  ],
  beacon: [
    { piece: "house_row", x: 116, z: -46 },
    { piece: "poles", x: 100, z: 40, radial: true },
    { piece: "spire", x: 40, z: -116 },
    { piece: "dead_light", x: -96, z: -96 },
    { piece: "stack", x: -106, z: -20 },
    { piece: "masts", x: 30, z: 100, turn: 1.2 },
    { piece: "headland", x: 132, z: 86 },
    { piece: "windmill", x: -10, z: 116 },
    { piece: "buoy", x: 70, z: 56 },
  ],
};
