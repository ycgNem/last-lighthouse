// The words that set the game up: the prologue a new keeper sees before
// they first take control, and the chapter's aim as the journal states it.

export interface StoryCard {
  title: string;
  text: string;
}

/** Shown once, on a new game, between "Click to begin" and the first step. Any key or click moves on; Esc skips. */
export const PROLOGUE: readonly StoryCard[] = [
  {
    title: "The Drowning",
    text: "Three generations ago the sea rose, and it never went back down. Towns, roads and fields lie under the water now. Something came up with it.",
  },
  {
    title: "The Lights",
    text: "The survivors gathered under the great lighthouses. The Gloom that rides the tide, and the drowned things that come with it, will not cross a lit beam.",
  },
  {
    title: "Lantern's Rest",
    text: "One by one the lights have gone out. This one is failing: its lamp gutters, its dock is broken, and the islands nearby have turned dangerous.",
  },
  {
    title: "The Keeper",
    text: "You rowed in through the fog with a battered bolt-caster, a fishing rod and a lantern. Not a hero. Just someone willing to go out there, and come back.",
  },
];

/** Seconds a prologue card stays up if nobody moves it on. */
export const PROLOGUE_CARD_SECONDS = 9;

export const CHAPTER_ONE = {
  title: "Chapter One: The First Light",
  aim: "Restore the lamp of Lantern's Rest until its beam reaches Saltmere, then carry its flame out and relight the beacon there.",
  /** The loop, in Maren's words. */
  creed: "The sea gives; the light keeps. Go out on the tide, bring back what it leaves, and build. Every trip makes the Rest stronger, and a stronger light reaches further.",
} as const;
