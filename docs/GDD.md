# The Last Lighthouse — Game Design Document

> First-person action RPG about restoring a lighthouse settlement in a drowned world.
> Three.js + TypeScript, single-player, runs in the browser, art made in Blender.

This doc is the source of truth for *what* the game is. Numbers live in `src/data/`
(the code is the source of truth for tuning); this doc explains *why*.

---

## 1. Pitch

Generations ago a supernatural flood swallowed the world. The survivors clustered
around great lighthouses whose light repels the creatures and the Gloom carried by
the sea. Most of those lights have gone out.

You arrive at **Lantern's Rest**, a small settlement under one of the last towers.
Its lamp is failing, its dock is broken, and the nearby islands have turned
dangerous. You become its new keeper — not a chosen hero, just a scavenger with a
battered bolt-caster, a fishing rod, a lantern and a small boat.

**Core fantasy:** every trip into danger builds somewhere worth coming home to.

**Key contrast:** *the sea gives temporary opportunity and danger; the lighthouse
gives permanent progress.* Every system should reinforce one side of that line.

### Pillars

1. **Home that visibly improves.** Every major upgrade changes the world you walk
   through — lit windows, a working forge, new faces, a longer beam.
2. **Readable, physical danger.** First-person combat where you can always see what
   is about to hit you and why it hit you.
3. **The tide is the level designer.** The same island plays differently at low and
   high tide. Both states are worth playing.
4. **One trip, several goals.** A single expedition advances food, gear, skills and
   the lighthouse at once.

### Tone

Warm lanterns, rain on rooftops, cooking fires and quiet fishing — against wrecked
ships, drowned streets, strange lights under the water and storms on the horizon.
Hopeful rebuilding, not relentless bleakness.

---

## 2. What changed from the original (top-down) pitch

The source prompt described a top-down RotMG-style game. This project is
**first-person 3D**. The design is adapted, not just re-skinned:

| Original (top-down) | This game (first-person) | Why |
|---|---|---|
| Space = dodge | **Shift = dash** (i-frames), **Space = jump** | Jumping matters on wreck decks and sandbars; Shift-dash is a familiar FPS idiom. |
| Projectile spreads read from above | Slow, large, emissive **sea-green orbs** with trails + positional audio, plus **threat pips** at screen edge for off-screen windups | You can't see behind you in first person. Readability needs sound and HUD help. |
| Tide shown as tiles flooding | **Water plane physically rises ~1.8 m**. Diegetic **tide poles** with painted bands, foam "tide lines" on surfaces that will flood | Height is the 3D language for tide. |
| High tide opens water routes | **Buoyant platforms** (crates, rafts, hull pieces) float up with the water and form new paths to upper decks | A mechanic that only works in 3D. |
| Map screen | **Chart table** in the lighthouse lamp room; the beam visibly sweeps across the fog on the chart | Keeps travel diegetic. |
| Light = flavour | **Keeper's Lantern** held in the left hand: your personal light, and a **Flare** (Q) that staggers enemies and burns away Gloom pockets | Darkness matters more in first person; the lantern is the lighthouse in miniature. |
| — | **The beam is visible from every destination** on the horizon | You always know where home is. Sanctuary as a landmark. |
| — | **Tide Lurker** enemy (new) that hunts in deep water at high tide | Gives high tide its own danger without making it unplayable. |

---

## 3. Goal hierarchy

**Immediate (minutes):** catch enough fish for food · salvage scrap for an upgrade ·
finish a settlement request · reach a wreck exposed by low tide · clear the crabs
guarding a cache.

**Session (several trips):** repair the forge · hit a skill milestone that unlocks a
recipe or node · upgrade the lighthouse · beat the island boss · relight a beacon.

**Campaign:** restore the coastal beacon network (3 outlying beacons + final storm
region), reach the source of the storm, calm the sea.

**Vertical slice (Chapter 1):** restore the home lighthouse enough to reach and
relight the **first outlying beacon (Saltmere Beacon)**. Relighting it is the
victory condition; play continues afterwards.

---

## 4. The lighthouse

The lighthouse is not an upgrade menu. It does four jobs:

### A. Sanctuary
Lantern's Rest is always safe. No raids, no base destruction, no loss of stored
items. On arrival the bolt-caster lowers automatically (viewmodel drops out of
frame) — a physical cue that you're home.

### B. Navigation
The lens burns routes through the supernatural fog. Upgrading beam range reveals
new destinations on the **chart table**. When a destination is revealed, play a
short sequence: the beam swings out over the sea, fog parts along it, the chart's
fog layer burns back.

### C. Settlement restoration
A stronger light attracts survivors. Every stage has a visible before/after:

| Stage | Name | Unlocks | Visible world change |
|---|---|---|---|
| 0 | **Failing Light** | Gullwash Shore | Flickering amber lamp, short beam, dark windows, broken dock (half the planks missing), cold forge, fog close in |
| 1 | **Restored Lamp** | Wreck of the Meridian | Steady white-gold beam with longer reach, dock rebuilt (boat moored at the end), 3 windows lit, smoke from Odile's chimney, **Hesk the smith arrives** |
| 2 | **Focused Lens** | Saltmere Beacon | Beam gains a sea-green focused core and sweeps to the horizon, fog pushed far back, most windows lit, a second boat, a survivor family by the new cottage, bunting on the dock |
| 3 | **First Beacon Relit** | Chapter complete; Saltmere becomes a safe landing point | A second, smaller beam is visible on the horizon from home; settlement holds a small celebration (lanterns strung, music at the hearth) |

Settlement **projects** (smaller, non-stage repairs) also flip buildings from
broken to repaired: the **Forge**, the **Dock**, the **Smokehouse** (optional).

### D. Regional progress
Relit beacons are permanent safe landing points and shortcuts, extending reach to
more dangerous regions. **No fuel chores, no decay.** Accomplishments are permanent.

---

## 5. Core loop

```
 PREPARE (home, <2 min)          TRAVEL (~10 s)            EXPEDITION (5–10 min)
 deposit · cook · smith    ──►   chart table → boat   ──►  gather · fight · explore
 pick objective · check tide     short sail cutscene       push on, or bank the haul?
        ▲                                                          │
        │                 RETURN (boat at landing point)          │
        └──── CONVERT: fish→food, scrap→gear, timber→dock,  ◄──────┘
              lens→lighthouse, xp→skills. SEE the change. Pick next goal.
```

Target feeling: *"I got what I came for — but now I'm one small trip away from the
next upgrade."*

---

## 6. Tide (signature mechanic)

Two readable states plus warned transitions. Default cycle **9 minutes**
(`src/data/tide.ts`): Low 4:00 → turning 0:30 → High 4:00 → turning 0:30. A **60 s
warning** precedes each turn.

### Low tide
- Exposes sandbars, tidal paths, wreck hull breaches and salvage beds.
- Safer gathering; shallow-water kelp and sea glass; optional caches.
- Crabs are out on the flats.

### High tide
- Floods low paths; **buoyant platforms** rise and connect upper routes.
- Stronger sea creatures (**Tide Lurkers**) patrol marked deep-water zones.
- Special fishing spots (**Glowgill**) and rare salvage on upper decks.
- Higher risk, better rewards. Never "wait for the timer".

### Fairness rules (hard requirements — see tests)
- HUD always shows current tide and time to next change.
- 60 s before a turn: horn sound, HUD banner, and **foam tide-lines glow** on every
  surface that will flood.
- **Nothing kills instantly.** Deep water puts you in *wading* (slower) then
  *swimming* (slow, can't shoot, can still dash on the surface).
- **No permanent traps.** Every flood zone has an authored **safe anchor**. If you
  stay in deep water for 6 s, a current gently carries you to the nearest anchor
  (screen-edge vignette + whoosh, no damage).
- **The landing point is reachable at both tides**, always.
- **The main quest never depends on a narrow window.** The Drowned Lens is
  reachable at either tide via different routes.

---

## 7. Combat

Responsive and readable, not stat trading. Difficulty comes from positioning,
patterns and knowing when to retreat — not health sponges.

### Controls
| Action | Default |
|---|---|
| Move | WASD |
| Look / aim | Mouse (pointer lock) |
| Fire bolt-caster | LMB |
| Dash (i-frames) | Shift |
| Jump | Space |
| Interact / gather / reel | E |
| Eat quick-slot food | F |
| Cycle food | Z |
| Lantern Flare | Q |
| Journal / inventory | Tab |
| Pause / settings | Esc |

### Player
- 100 HP base (+5 per Combat level).
- **Lantern Flare (Q):** a 15 m cone of light (42° either side of where you look),
  9 s cooldown. Every enemy it reaches (not through walls) staggers for its own
  time (Wisps longest, the Guardian not at all: it's too vast to dazzle), and
  every Gloom pocket the cone touches, or that you're within 4 m of, burns away
  until your next visit.
- **Gloom pockets** (`GLOOM_` markers) hang over loot in the dark places: the
  nodes inside are shrouded (no gathering) and standing in one chills you after
  1.2 s, 4 HP a second, but never below 15 HP. Flare them.
- **Dash:** 6 m burst in move direction (forward if idle), 0.28 s invulnerable,
  1.2 s cooldown. Combat 5 grants a second charge.
- **Eating:** 0.6 s animation, can move at half speed while eating. Heals over 1 s.
- No stamina, no ammo, no durability.

### Keeper's Bolt-caster
Amber bolts, fast projectile (not hitscan), ~3 shots/s, small spread at Mk I.
Upgrades (Smithing): Mk II (more damage, faster bolt, tighter spread),
Mk III "Lamplighter" (bolts pierce one target and leave a brief light burst).
Combat 8: hold LMB to charge a heavy bolt.

### Readability rules
- Every enemy attack has a **windup ≥ 0.4 s** with a visual (glow/pose) **and** an
  audio cue.
- Enemy projectiles are **sea-green, emissive, slow (8–14 m/s), large (≥0.35 m)**,
  with trails. Player bolts are **amber**. Loot is **white/gold sparkle** — never
  sea-green.
- **Threat pips:** a small arc at the screen edge pointing to any enemy winding up
  outside your view.
- **Damage direction indicator** when hit.
- Hit feedback: enemy flashes white, small knockback, crisp hit sound, damage
  numbers optional (settings).
- Restrained screen shake (off by default above a tiny amount; toggle in settings).

### Enemies

| Enemy | Where | Behaviour | Counterplay |
|---|---|---|---|
| **Brine Crab** | Shore, Wreck | Scuttles sideways toward you, rears up (0.6 s, claws glow), lunges 5 m in a straight line, then is stuck briefly | Dash sideways; punish the recovery |
| **Drowned Spitter** | Wreck, Beacon | Stationary-ish, waterlogged corpse in kelp. Inhales (0.7 s, throat glows), fires a slow fan of 3–5 orbs | Strafe through the gaps, use cover |
| **Lantern Wisp** | Wreck (dark areas), Beacon | Floats, blinks to a new position, then fires 2 aimed shots with a charge glow. Weak to light | Track the blink sound; a Flare stuns it for 3.5 s |
| **Tide Lurker** *(new)* | Deep water at high tide | Shown by a moving ripple + bubbles. If you're swimming or at the edge, it surfaces (0.8 s), bites | Stay out of marked deep zones or get out fast |
| **Wreck Guardian** (boss) | Saltmere Beacon | A colossus of fused hulls and chain rising from the water around the beacon rock. See §11 | Positioning around a generous ring arena |

---

## 8. Skills & crafting

Five skills, levels **1–10**, explicit milestones. Unlocks over percentages.
Full tables live in `src/data/skills.ts`.

| Skill | Purpose in loop | Key milestones |
|---|---|---|
| **Fishing** | Food ingredients | 1 Silverfin · 3 spot-reading (fishing spots show from 40 m) · 4 Glowgill (high tide spots, needs Reinforced Rod) · 7 quicker bites · 10 Keeper's catch (rare double) |
| **Salvaging** | Timber, scrap, brass, sea glass, relics | 1 driftwood & scrap piles · 2 sea-glass beds · 4 **reinforced wreckage** (brass) · 6 sealed caches · 9 faster salvage |
| **Cooking** | Healing food | 1 Grilled Silverfin · 3 Kelp-wrapped Fish · 5 Crab Chowder · 7 Glowgill Stew |
| **Smithing** | Gear | 1 smelt Iron Ingots, Satchel Straps (+4 slots) · 2 Reinforced Rod · 4 Bolt-caster Mk II · 6 Tidebreaker Coat · 8 Lamplighter (Mk III) |
| **Combat** | Modest character growth | +5 HP/level · 5 second dash charge · 8 charged shot |

Gathering is **quick**: a 0.6–1.5 s hold with a radial progress ring, a satisfying
pop, and materials that fly into you. Fishing is a short timing game: cast → bobber
→ bite splash + sound → press E within the window (0.8 s, wider for Silverfin).

Crafting UI shows required vs owned materials, the item's benefit, any unlock
requirement, and a single clear **Craft** button.

### Resources (kept deliberately small)

| Id | Name | Source | Used for |
|---|---|---|---|
| `timber` | Timber | Driftwood, wreck planks | Dock, buildings, rod |
| `scrap` | Scrap Metal | Scrap piles, crab drops | Smithing, lamp |
| `brass` | Brass Fittings | Reinforced wreckage (Salvage 4), captain's strongbox | Mk II, lens mount |
| `iron_ingot` | Iron Ingot | Smelted at the forge (2 Scrap → 1) — the repeatable Smithing XP source | All smithed gear |
| `sea_glass` | Sea Glass | Low-tide glass beds | Lamp housing, lantern |
| `kelp` | Kelp | Low-tide kelp beds | Cooking, straps |
| `tidestone` | Tidestone | Every defeated enemy, caches | Weapon upgrades, lens |
| `silverfin` | Silverfin | Fishing (any tide) | Cooking |
| `glowgill` | Glowgill | Fishing at high tide, Fishing 4 | Cooking |
| `crab_meat` | Crab Meat | Brine Crabs | Cooking |

Quest items (never lost, don't take satchel slots): `drowned_lens`,
`lighthouse_ember`.

---

## 9. Inventory, death, saving

- **Satchel:** 12 slots (16 with Satchel Straps), stacks of 20 (food 10). Quest
  items live in a separate key-item pouch.
- **Storage chest** at home: unlimited. **Deposit All** is one key.
- Carried materials are **at risk**; stored ones are safe.
- **Defeat:** fade to white, *"The tide carries you home"*, wake in the keeper's
  cot. Lose **40% of each unbanked common stack** (rounded down, min keep 1 of any
  stack). Keep skills, gear, quest items, upgrades. A summary shows what was lost.
- Pickups: a soft chime and a small toast (`+3 Timber`) bottom-right, batched.
- **Saving:** local (`localStorage`), versioned schema with migrations. Autosave on
  deposit, craft, upgrade, travel, and every 60 s at home. **Reset** in settings
  needs two confirmations.

---

## 10. HUD — questions the UI must answer at a glance

| Question | Answer on screen |
|---|---|
| What am I doing next? | **Pinned objective** top-left (main quest), plus one **tracked resource goal** under it ("Timber 7/12") |
| What do I need for the next lighthouse upgrade? | Journal → Lighthouse tab, and the tracked goal |
| What did I gain on this trip? | **Haul** counter on HUD while away; return summary screen when you dock |
| What is the tide doing? | **Tide dial** top-right: state, countdown, a little water-level gauge; banner on warning |
| Can I safely return home? | Compass strip shows the **landing point** icon and distance; the beam on the horizon |

Health bottom-left as a lantern-glass gauge; dash pips next to it; food quick-slot
bottom-centre.

---

## 11. Content — Chapter 1

See `docs/LEVELS.md` for layouts, tide behaviour and encounter placement.

1. **Lantern's Rest** (home, safe) — lighthouse with lamp room + chart table,
   dock and boat, storage chest, hearth (cooking), forge (broken → repaired),
   NPCs Maren, Tib, Odile (+Hesk at stage 1).
2. **Gullwash Shore** (safe-ish, tutorial) — driftwood, scrap, kelp, sea glass,
   Silverfin; Brine Crabs; a sandbar to a cache islet at low tide; Glowgill rocks at
   high tide.
3. **Wreck of the Meridian** (dangerous) — Crabs, Spitters, Wisps, Lurkers; brass
   salvage; two tide routes to the **Drowned Lens**.
4. **Saltmere Beacon** (finale) — short causeway approach, the **Wreck Guardian**
   boss, the beacon and its relighting sequence.

### Wreck Guardian (boss)
Ring arena on the beacon rock's base (~30 m diameter), water all around. Three
attacks, each with long tells:
- **Chain Sweep** — raises a chain-arm (1.0 s, chain glows), sweeps a 120° arc at
  ground level. *Jump or dash through.*
- **Brine Mortar** — vents glow, lobs 5 orbs; impact rings appear on the ground
  1.2 s before landing. *Step out of rings.*
- **Undertow** (phase 2, <50% HP) — water rises at the arena edge and pulls you
  outward for 3 s while Spitter-orbs fan from its maw. *Move inward, strafe.*
Weak point: the sea-green **heart lantern** in its chest, exposed after each
Chain Sweep for 2 s (double damage). ~3–4 minutes for a prepared player.

### Relighting sequence
After the boss sinks: climb the beacon stair, interact with the cold lamp, place
the **Lighthouse Ember**. Camera holds; flame catches; the lens turns; a beam fires
toward Lantern's Rest and home's beam answers. Fog rolls back across the sea.
Title card: **"Chapter One — The First Light."** Saltmere becomes a landing point.

---

## 12. Chapter 1 quest flow (main objectives)

1. **Wake the Keeper** — talk to Maren in the lamp room.
2. **Feed the Rest** — fish 3 Silverfin at Gullwash, cook them at the hearth.
   *(Teaches travel, fishing, cooking.)*
3. **Rekindle the Forge** — bring 8 Scrap + 6 Timber. *(Teaches salvage, combat.)*
4. **Mend the Dock** — 12 Timber + 4 Kelp (rope). *(First visible repair.)*
5. **Restore the Lamp** — 10 Scrap + 6 Sea Glass + 6 Timber → **Stage 1**. The beam
   reveals the Meridian.
6. **The Drowned Lens** — recover it from the Meridian.
7. **Focus the Light** — Lens + 8 Brass + 5 Tidestone → **Stage 2**. Beam reveals
   Saltmere; receive the **Lighthouse Ember**.
8. **Relight Saltmere** — defeat the Wreck Guardian, place the Ember → **Stage 3**.

Settlement requests (optional, repeatable-ish): Odile wants cooked food for the
survivors; Tib wants timber for a second boat; Hesk wants brass for his tools.
Rewards are recipes, XP and small material bundles — **no currency**.

### First-session pacing (15–20 min)
Talk to Maren (1 min) → Gullwash: gather, fight 2–3 crabs, fish (6 min) → a tide
change happens mid-trip (cycle starts 3 min before the first turn) → return, cook,
repair the forge (3 min) → second Gullwash run for timber/kelp → dock repaired
(visible) → Restore the Lamp reachable on run 2–3 → Meridian revealed.

---

## 13. Presentation

- Palette: deep blue/teal water, warm amber sanctuary light, weathered timber, pale
  stone, sea-green supernatural accents. See `docs/ART_PIPELINE.md`.
- Gentle wave motion, rotating beam with volumetric-ish cone, light rain and
  distance fog that **never** obscures combat range (fog starts ≥ 35 m).
- Safe spaces are warm and lit; danger is cold, green-tinged, darker.
- Audio: rain loop, surf, gulls, creaking timber, hearth crackle; combat cues per
  enemy; tide horn; upgrade fanfare. WebAudio, positional for enemy cues.

---

## 14. Out of scope for the slice

Multiplayer · sailing simulation · procedural worlds · NPC schedules · hunger ·
durability · offline decay · fuel chores · currencies · more than one weapon type
until combat feels good.
