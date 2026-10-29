import type { NpcId, ProjectId, StageIndex } from "./ids";

export interface NpcDef {
  name: string;
  role: string;
  /** When they're at the Rest: once the lighthouse reaches a stage, or once their plot is rebuilt. */
  arrives: { stage: StageIndex } | { project: ProjectId };
  /** Marker in locations/home.glb. */
  marker: string;
  /** Lines keyed by the main-quest step id they apply to; "default" is the fallback. */
  lines: Record<string, string[]>;
}

export const NPCS: Record<NpcId, NpcDef> = {
  maren: {
    name: "Maren Holt",
    role: "The old keeper",
    arrives: { stage: 0 },
    marker: "NPC_maren",
    lines: {
      wake: [
        "So you're the one who rowed in through the fog. Good. My hands won't do the stairs much longer.",
        "The lamp is failing. While it burns, nothing from the sea comes ashore. When it dies, so do we.",
        "Look at the place. Forge cold, jetty gone, the cottages open to the sky. Everyone who could leave, left.",
        "But the sea gives, keeper. Every tide brings the drowned world into our cove: planks, drums, whole crates. Hook it out, carry it up, and we build. A stronger lamp reaches further, and shows you more of the coast.",
        "Mind the tide. The flood brings in the most; low water bares the old wrecks on the cove floor. The horn sounds a minute before it turns.",
        "Take your hook down to the cove and see what the sea's brought us.",
      ],
      salvage: ["Throw at the drift and pull. Anything you miss washes up on the sand, so nothing's lost."],
      forge: ["The forge first. Scrap for the hood, timber for the frame. Hand it in at the plot as you get it, and you'll see it go up."],
      jetty: ["Tib's been sleeping in his boat off the point since the jetty went. Give him somewhere to tie up and he'll come in."],
      cottage: ["The Marsh place, by the well. Put a roof on it and Odile will come home. She could always make a meal out of nothing."],
      lamp: ["The housing's cracked through. Scrap for the frame, sea glass for the panes, timber for the gallery. Bring it up here."],
      lens: ["That beam just touched something out there — a ship's hull. The Meridian. Her captain kept a spare lens. Find it."],
      focus: ["Seat the lens and the light will reach Saltmere. Take an ember of our flame when it does. Beacons remember their keepers."],
      default: ["Keep the light, keeper. It keeps us.", "Every house you raise is a family that can come back."],
    },
  },
  tib: {
    name: "Tobias \"Tib\" Calder",
    role: "Dockhand and boatwright",
    arrives: { project: "jetty" },
    marker: "NPC_tib",
    lines: {
      cottage: ["Twelve years I've tied up to rocks. Feels strange, boards under my feet. Boat's yours when the light shows us where to go."],
      lamp: ["Nothing out there worth the row until that beam reaches further. Fix the lamp and I'll take you wherever it points."],
      default: ["Tide's turning soon. Check the poles before you go — the painted bands don't lie.", "The flood tide brings the good stuff in. Ask anyone who ever beachcombed."],
    },
  },
  odile: {
    name: "Odile Marsh",
    role: "Cook at the hearth",
    arrives: { project: "cottage_1" },
    marker: "NPC_odile",
    lines: {
      feed: ["A roof over my head again. I'll keep this place fed, then. Three silverfin off the rocks, that's all I ask. Grill them yourself, the hearth's warm."],
      default: ["Eat before you go. Nobody fights well hungry.", "Build the smokehouse and I'll teach you to cure a fish properly."],
    },
  },
  hesk: {
    name: "Hesk",
    role: "Smith, arrived with the light",
    arrives: { stage: 1 },
    marker: "NPC_hesk",
    lines: {
      default: ["Saw your beam from the drowned town. Haven't seen a steady light in years. That forge of yours — mind if I share it?", "Plain rope won't bite reinforced plating. Make an Iron Hook before you go after the Meridian's brass."],
    },
  },
};
