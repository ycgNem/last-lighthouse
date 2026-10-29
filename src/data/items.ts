import type { GearId, ItemId } from "./ids";

export type ItemCategory = "material" | "catch" | "food" | "key";

export interface FoodEffect {
  heal: number;
  /** Optional timed buff, kept to one or two kinds on purpose. */
  buff?: { kind: "dash_cooldown" | "max_hp"; amount: number; seconds: number };
}

export interface ItemDef {
  name: string;
  category: ItemCategory;
  stack: number;
  description: string;
  food?: FoodEffect;
}

export const ITEMS: Record<ItemId, ItemDef> = {
  timber: { name: "Timber", category: "material", stack: 20, description: "Salt-hardened planks from the drift. Jetties, roofs, rods." },
  scrap: { name: "Scrap Metal", category: "material", stack: 20, description: "Rusted fittings from the old world. Smelt it at the forge." },
  brass: { name: "Brass Fittings", category: "material", stack: 20, description: "Ship's brass. Doesn't rust; the lens mounts need it." },
  sea_glass: { name: "Sea Glass", category: "material", stack: 20, description: "Bottles and panes the sea has tumbled smooth. Windows and the lamp housing." },
  kelp: { name: "Kelp", category: "material", stack: 20, description: "Tough ribbon kelp. Rope, nets, straps and supper." },
  tidestone: { name: "Tidestone", category: "material", stack: 20, description: "A sea-green shard left behind when a creature of the Gloom dies." },
  iron_ingot: { name: "Iron Ingot", category: "material", stack: 20, description: "Smelted scrap. Everything at the forge starts here." },

  silverfin: { name: "Silverfin", category: "catch", stack: 20, description: "A common cove fish. Grill it, or smoke it." },
  glowgill: { name: "Glowgill", category: "catch", stack: 20, description: "Rises only at high tide. Faintly warm to the touch." },
  crab_meat: { name: "Crab Meat", category: "catch", stack: 20, description: "From Brine Crabs. Sweeter than it has any right to be." },

  grilled_silverfin: { name: "Grilled Silverfin", category: "food", stack: 10, description: "Simple and dependable.", food: { heal: 30 } },
  smoked_silverfin: { name: "Smoked Silverfin", category: "food", stack: 20, description: "Cured in the smokehouse. Heals more, and packs flat.", food: { heal: 45 } },
  kelp_wrap: { name: "Kelp-wrapped Fish", category: "food", stack: 10, description: "Steamed in kelp. Heals well.", food: { heal: 50 } },
  crab_chowder: { name: "Crab Chowder", category: "food", stack: 10, description: "Thick, hot, restorative.", food: { heal: 80, buff: { kind: "max_hp", amount: 20, seconds: 180 } } },
  glowgill_stew: { name: "Glowgill Stew", category: "food", stack: 10, description: "You feel quick on your feet.", food: { heal: 60, buff: { kind: "dash_cooldown", amount: 0.25, seconds: 180 } } },

  drowned_lens: { name: "Drowned Lens", category: "key", stack: 1, description: "A lighthouse lens element, recovered from the Meridian's chart room." },
  lighthouse_ember: { name: "Lighthouse Ember", category: "key", stack: 1, description: "A coal of the home lamp's flame, carried in a brass cage. It will light Saltmere." },
};

export type GearSlot = "weapon" | "hook" | "rod" | "satchel" | "armor";

export interface GearDef {
  name: string;
  slot: GearSlot;
  description: string;
  /** Higher tier replaces lower tier in the same slot. */
  tier: number;
  stats: Partial<{
    boltDamage: number;
    fireRate: number;
    boltSpeed: number;
    spreadDeg: number;
    pierce: number;
    satchelSlots: number;
    maxHp: number;
    /** Metres the salvage hook reaches. */
    hookRange: number;
    /** Metres a second it reels a light piece in. */
    reelSpeed: number;
  }>;
}

export const GEAR: Record<GearId, GearDef> = {
  boltcaster_mk1: { name: "Keeper's Bolt-caster", slot: "weapon", tier: 1, description: "Battered, reliable.", stats: { boltDamage: 10, fireRate: 3, boltSpeed: 55, spreadDeg: 1.2 } },
  boltcaster_mk2: { name: "Bolt-caster Mk II", slot: "weapon", tier: 2, description: "Brass-sleeved barrel. Hits harder, flies truer.", stats: { boltDamage: 15, fireRate: 3.4, boltSpeed: 70, spreadDeg: 0.6 } },
  lamplighter: { name: "Lamplighter", slot: "weapon", tier: 3, description: "Bolts pierce one target and leave a burst of light.", stats: { boltDamage: 19, fireRate: 3.6, boltSpeed: 80, spreadDeg: 0.4, pierce: 1 } },
  hook_rope: { name: "Rope Hook", slot: "hook", tier: 1, description: "A grapnel on kelp rope. Pulls in flotsam and tears at wrecks.", stats: { hookRange: 16, reelSpeed: 6 } },
  hook_iron: { name: "Iron Hook", slot: "hook", tier: 2, description: "Forged tines on a longer line. Bites through reinforced plating for its brass.", stats: { hookRange: 20, reelSpeed: 7.5 } },
  hook_brass: { name: "Brass Hook", slot: "hook", tier: 3, description: "Net-loft line on a brass reel. Reaches the cove mouth, and reels like a winch.", stats: { hookRange: 26, reelSpeed: 9.5 } },
  rod_basic: { name: "Driftwood Rod", slot: "rod", tier: 1, description: "Catches Silverfin.", stats: {} },
  rod_reinforced: { name: "Reinforced Rod", slot: "rod", tier: 2, description: "Strong enough for Glowgill.", stats: {} },
  satchel_straps: { name: "Satchel Straps", slot: "satchel", tier: 2, description: "+4 satchel slots.", stats: { satchelSlots: 4 } },
  tidebreaker_coat: { name: "Tidebreaker Coat", slot: "armor", tier: 1, description: "Kelp-oiled leather over iron plates. +25 max HP.", stats: { maxHp: 25 } },
};

export const STARTING_GEAR: readonly GearId[] = ["boltcaster_mk1", "hook_rope", "rod_basic"];
