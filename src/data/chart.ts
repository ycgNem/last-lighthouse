import type { LocationId } from "./ids";

// The sea chart in the journal (src/ui/chart.ts draws it). Coordinates are on
// a 480 x 270 chart, north up: the mainland to the north-west, Lantern's Rest
// on its headland, the drowned town up the coast, the beached Meridian to the
// east and Saltmere's light far out to the north-east. Past the beam's reach
// everything is fog.

type Pt = readonly [number, number];

export const CHART = {
  size: [480, 270] as Pt,
  at: { home: [92, 188], wreck: [292, 198], beacon: [408, 82] } as Record<LocationId, Pt>,
  /** The beam's reach on the chart at each lighthouse stage. */
  reach: [140, 250, 380, 380] as readonly number[],
  /** The mainland's coast, north edge to south edge; the land lies west of it. */
  coast: [
    [236, -6], [230, 14], [224, 30], [213, 44], [203, 58], [196, 74], [186, 86], [178, 96], [167, 101], [155, 107],
    [144, 118], [134, 131], [122, 143], [113, 152], [108, 162], [107, 172], [104, 183], [99, 193], [90, 198], [81, 194],
    [77, 185], [70, 186], [59, 194], [48, 207], [38, 223], [27, 240], [17, 258], [12, 276],
  ] as readonly Pt[],
  /** Islands, each a closed outline. */
  islands: [
    // Saltmere.
    [[397, 75], [405, 69], [416, 71], [422, 79], [420, 90], [410, 96], [400, 93], [395, 85]],
    // The bank the Meridian ran onto.
    [[279, 197], [289, 191], [302, 193], [307, 200], [297, 206], [284, 205]],
    // Skerries and outliers.
    [[328, 146], [336, 142], [342, 148], [336, 154], [329, 152]],
    [[356, 214], [366, 208], [376, 213], [372, 222], [360, 222]],
    [[441, 138], [449, 134], [455, 141], [448, 147]],
    [[262, 34], [272, 30], [279, 37], [270, 43]],
  ] as readonly (readonly Pt[])[],
  /** Boat routes from the Rest's jetty: a control point for each curve. */
  routes: { wreck: [190, 232], beacon: [300, 178] } as Partial<Record<LocationId, Pt>>,
  /** Rocks awash. */
  rocks: [[248, 122], [252, 126], [312, 176], [318, 182], [384, 120], [226, 232], [232, 236], [140, 210]] as readonly Pt[],
  /** The drowned town up the coast: its streets and roofs show through at low water. */
  drowned: {
    origin: [214, 134] as Pt,
    /** Turn of the street grid, radians. */
    turn: -0.35,
    streets: [
      [[-22, -12], [40, -12]],
      [[-18, 0], [44, 0]],
      [[-14, 12], [36, 12]],
      [[-8, -20], [-8, 20]],
      [[8, -22], [8, 22]],
      [[24, -18], [24, 18]],
    ] as readonly (readonly Pt[])[],
    roofs: [[-16, -7], [-2, -7], [14, -7], [30, -7], [-12, 5], [2, 6], [16, 5], [32, 5], [-4, 17], [14, 17], [0, -16], [18, -16]] as readonly Pt[],
    spire: [31, -16] as Pt,
  },
  /** The telegraph line walking out to sea from the drowned town. */
  poles: [[182, 88], [194, 84], [206, 80], [218, 77], [230, 74], [242, 71], [254, 69]] as readonly Pt[],
  /** Lights that went out. Never visited this chapter; they wait in the fog. */
  deadLights: [[462, 168], [336, 24], [468, 40], [238, 252]] as readonly Pt[],
  /** Depths in fathoms, as a chart would have them. */
  soundings: [
    [132, 170, "3"], [150, 148, "5"], [206, 176, "9"], [244, 204, "12"], [266, 100, "8"], [318, 118, "17"], [348, 178, "21"],
    [204, 232, "14"], [124, 226, "6"], [380, 140, "26"], [440, 110, "19"], [300, 62, "15"], [180, 150, "7"], [260, 160, "11"],
  ] as readonly (readonly [number, number, string])[],
  rose: [440, 230] as Pt,
} as const;
