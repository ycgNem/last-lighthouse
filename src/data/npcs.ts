import type { NpcId, StageIndex } from "./ids";

export interface NpcDef {
  name: string;
  role: string;
  appearsAtStage: StageIndex;
  /** Marker in home.glb. */
  marker: string;
  /** Lines keyed by the main-quest step id they apply to; "default" is the fallback. */
  lines: Record<string, string[]>;
}

export const NPCS: Record<NpcId, NpcDef> = {
  maren: {
    name: "Maren Holt",
    role: "The old keeper",
    appearsAtStage: 0,
    marker: "NPC_maren",
    lines: {
      wake: [
        "So you're the one who rowed in through the fog. Good. My hands won't do the stairs much longer.",
        "The lamp is failing. While it burns, nothing from the sea comes ashore. When it dies, so do we.",
        "Start small. Odile has a hearth and no fish. Gullwash Shore is just down the cliff path.",
      ],
      lamp: ["The housing's cracked through. Scrap for the frame, sea glass for the panes, timber for the gallery. Bring it up here."],
      lens: ["That beam just touched something out there — a ship's hull. The Meridian. Her captain kept a spare lens. Find it."],
      focus: ["Seat the lens and the light will reach Saltmere. Take an ember of our flame when it does. Beacons remember their keepers."],
      default: ["Keep the light, keeper. It keeps us."],
    },
  },
  tib: {
    name: "Tobias \"Tib\" Calder",
    role: "Dockhand and boatwright",
    appearsAtStage: 0,
    marker: "NPC_tib",
    lines: {
      dock: ["Boat's fine. The dock's the problem — half the planks went in the last storm. Twelve timber and some kelp for rope and we're sailing."],
      default: ["Tide's turning soon. Check the poles before you go — the painted bands don't lie."],
    },
  },
  odile: {
    name: "Odile Marsh",
    role: "Cook at the hearth",
    appearsAtStage: 0,
    marker: "NPC_odile",
    lines: {
      feed: ["Three silverfin, that's all I ask. Grill them yourself, the hearth's warm. You'll want food in your pack out there."],
      default: ["Eat before you go. Nobody fights well hungry."],
    },
  },
  hesk: {
    name: "Hesk",
    role: "Smith, arrived with the light",
    appearsAtStage: 1,
    marker: "NPC_hesk",
    lines: {
      default: ["Saw your beam from the drowned town. Haven't seen a steady light in years. That forge of yours — mind if I share it?"],
    },
  },
};
