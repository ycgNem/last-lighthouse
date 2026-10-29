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
Its lamp is failing, its forge is cold, its jetty is gone and most of its houses
stand empty. You become its new keeper — not a chosen hero, just a scavenger with
a battered bolt-caster, a salvage hook, a fishing rod and a lantern.

**Core fantasy:** the Rest is your base. The sea brings the drowned world's
wreckage into its cove; you hook it out and rebuild the place plot by plot, and
every trip into danger builds somewhere worth coming home to.

**Key contrast:** *the sea gives temporary opportunity and danger; the lighthouse
gives permanent progress.* Every system should reinforce one side of that line.

### Pillars

1. **Home is your base.** Every rebuild rises in front of you as you hand
   materials in, does something useful when it stands, and often brings someone
   home: lit windows, a working forge, new faces, a longer beam. What's left over
   you spend making the place yours.
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
| Walk over / hold a key on resource nodes | **Salvage hook** thrown at what you aim at: flotsam reels in across the water, wrecks give up a piece per pull | One physical verb that uses your aim and works at range. Holding E on scattered nodes wasn't readable or fun (playtest). |

---

## 3. Goal hierarchy

**Immediate (minutes):** hook what the flood brings into the cove · strip the wreck
field while the tide's out · hand in the last timber a rebuild needs · catch enough
fish for food · reach the Meridian's hull at low tide.

**Session (several trips):** rebuild the forge · bring a family home · hit a skill
milestone · forge the Iron Hook · upgrade the lighthouse · beat the island boss ·
relight a beacon.

**Campaign:** restore the coastal beacon network (3 outlying beacons + final storm
region), reach the source of the storm, calm the sea.

**Vertical slice (Chapter 1):** restore the home lighthouse enough to reach and
relight the **first outlying beacon (Saltmere Beacon)**. Relighting it is the
victory condition; play continues afterwards.

---

## 4. The lighthouse

The lighthouse and the village under it are not an upgrade menu. They do five jobs:

### A. Sanctuary
Lantern's Rest is always safe. No raids, no base destruction, no loss of stored
items. At home the bolt-caster doesn't fire: it's only the launcher for the hook
clamped under it, so LMB throws the hook as well as RMB.

### B. Navigation
The lens burns routes through the supernatural fog. Upgrading beam range reveals
new destinations on the **chart table**. When a destination is revealed, play a
short sequence: the beam swings out over the sea, fog parts along it, the chart's
fog layer burns back.

### C. Rebuilding the Rest
A stronger light draws survivors home, but they need somewhere to come home to.
The lamp's **stages** are the big steps; between them you rebuild the village
yourself, plot by plot.

| Stage | Name | Unlocks | Visible world change |
|---|---|---|---|
| 0 | **Failing Light** | — (the cove at home) | Flickering amber lamp, short beam, fog close in; the plots stand in ruins |
| 1 | **Restored Lamp** | Wreck of the Meridian | Steady white-gold beam with longer reach, **Hesk the smith arrives**; the Pell Cottage can be rebuilt |
| 2 | **Focused Lens** | Saltmere Beacon | Beam gains a sea-green focused core and sweeps to the horizon, fog pushed far back, a second boat at the jetty; the Ashby Cottage can be rebuilt |
| 3 | **First Beacon Relit** | Chapter complete; Saltmere becomes a safe landing point | A second, smaller beam is visible on the horizon from home; settlement holds a small celebration (lanterns strung, music at the hearth) |

**Plots.** Each ruin has a name board. Press E at it to hand in whatever you have
toward it, from the satchel and the chest, at any time and in any amount. The
building **rises as you go**, the finished model climbing out of the ground
behind scaffolding (the jetty instead grows out along its length, solid as far
as it reaches), with dust and hammering at each delivery. When it stands, the
scaffolding and the board go, a flourish plays, its perk applies, and whoever it
was for walks in. Costs live in `src/data/lighthouse.ts`.

| Plot | Once rebuilt |
|---|---|
| **Forge** | Smelt iron and smith gear: the Iron Hook, a better rod, a better bolt-caster. The first rebuild. |
| **Jetty** | Tib brings the boat in: expeditions leave from its end. Glowgill off the end at high water. |
| **Marsh Cottage** | Odile comes home and keeps the hearth. |
| **Pell Cottage** (Stage 1) | The Pells come home. |
| **Ashby Cottage** (Stage 2) | The Ashbys come home. |
| **Net Loft** (after the jetty) | Make the Brass Hook here; the cove net holds what drifts in while you're away. |
| **Smokehouse** (after the Marsh Cottage) | Smoked Silverfin: heals more. |

The Lamp's Stage 1 needs the forge, the jetty and the Marsh Cottage standing; the
net loft, the smokehouse and the other two cottages are optional, with real perks.

### D. Making it yours
**Build mode (B)** turns the spare timber, scrap, kelp and glass into decor:
lantern posts and braziers (lit), fences, benches, herb planters, barrels,
crates, bunting and net racks. A green ghost of the piece follows the crosshair
(red where it can't go); LMB places it and takes its cost, R turns it, RMB picks
one back up for everything it cost, and the wheel or the number keys choose.
Pieces go inside the village on gentle ground above high water, clear of the
plots, doors, paths and each other (`src/systems/decor.ts`). They're saved,
drawn instanced per kind and solid where they should be.

### E. Regional progress
Relit beacons are permanent safe landing points and shortcuts, extending reach to
more dangerous regions. **No fuel chores, no decay.** Accomplishments are permanent.

---

## 5. Core loop

Two loops, both centred on the Rest.

**At home (most of Chapter 1's first stretch).** The tide brings the drowned
world's wreckage in through the cove mouth. Hook it out, carry it up, hand it in
at a plot and watch the building rise; build what it unlocks; spend the spare on
decor. The tide sets the rhythm: the flood brings the most drift (and the rarer
ship's crates); low water bares the cove's wreck field.

```
 THE COVE (salvage)              THE PLOTS (rebuild)          WHAT IT GIVES
 hook flotsam as it drifts  ──►  E at the board: hand in ──►  a station, a perk,
 in · strip the wreck field      any amount, see it rise      someone home · decor
 at low water · fish the rocks         ▲                             │
        ▲                              └──── next plot, next stage ◄─┘
        └── the tide turns: more drift on the flood, the wreck field at the ebb
```

**Expeditions (once the jetty stands and the beam reveals somewhere).** For what
the cove can't give: brass from reinforced plating (Iron Hook), the Drowned Lens,
the boss.

```
 PREPARE (home, <2 min)          TRAVEL (~10 s)            EXPEDITION (5–10 min)
 deposit · cook · smith    ──►   chart table → boat   ──►  salvage · fight · explore
 pick objective · check tide     short sail cutscene       push on, or bank the haul?
        ▲                                                          │
        │            RETURN (the boat ties up at the jetty)       │
        └── CONVERT: fish→food, scrap→gear, timber→rebuilds, ◄─────┘
            lens→lighthouse, xp→skills. The cove kept drifting
            while you were gone: the beach (and the net) hold it.
```

Target feeling: *"I got what I came for — but now I'm one small trip away from the
next upgrade."*

---

## 6. Tide (signature mechanic)

Two readable states plus warned transitions. Default cycle **9 minutes**
(`src/data/tide.ts`): Low 4:00 → turning 0:30 → High 4:00 → turning 0:30. A **60 s
warning** precedes each turn.

### Low tide
- Exposes tidal paths, wreck hull breaches and the Meridian's low salvage.
- At home it bares the cove's **wreck field** (a sunken fishing boat, old pilings,
  a rusted boiler), whole again at every ebb; the drift slows.
- Crabs are out on the flats.

### High tide
- Floods low paths; **buoyant platforms** rise and connect upper routes.
- Stronger sea creatures (**Tide Lurkers**) patrol marked deep-water zones.
- Special fishing spots (**Glowgill**) and rare salvage on upper decks.
- At home the flood brings the most drift into the cove, and now and then a
  sealed ship's crate (brass).
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
- **Home too.** The tide matters in the Rest's cove, so the Rest is swept like
  every other level, with its plots in ruins, rising and rebuilt. Off the cove
  the coast goes straight down to swimming depth, so a fall off the outside
  always ends with the current bringing you in.

---

## 7. Combat

Responsive and readable, not stat trading. Difficulty comes from positioning,
patterns and knowing when to retreat — not health sponges.

### Controls
| Action | Default |
|---|---|
| Move | WASD |
| Look / aim | Mouse (pointer lock) |
| Fire bolt-caster | LMB (at home, it throws the hook) |
| Salvage hook | RMB |
| Dash (i-frames) | Shift |
| Jump | Space |
| Interact / open / fish / hand in at a plot | E |
| Build mode (at home) · turn the piece | B · R |
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
- **Dash:** exactly 6 m in 0.22 s in the move direction (forward if idle), fast
  off the mark and easing into a walk at the end, so it never slides. 0.3 s
  invulnerable, 1.2 s cooldown; a press up to 0.15 s early still fires. In the air
  it holds its height (a dash-jump carries), and on the ground it hugs slopes and
  steps down instead of launching off them. Combat 5 grants a second charge.
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
| **Brine Crab** | Wreck | Scuttles sideways toward you, rears up (0.6 s, claws glow), lunges 5 m in a straight line, then is stuck briefly | Dash sideways; punish the recovery |
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
| **Fishing** | Food ingredients | 1 Silverfin at any tide, Glowgill at high water with a Reinforced Rod · 3 spot-reading (fishing spots show from 40 m) · 7 quicker bites · 10 Keeper's catch (rare double) |
| **Salvaging** | Timber, scrap, kelp, sea glass, brass | 1 hook drift and tear at wrecks · 2 reel 15% faster · 4 throw 3 m further · 6 the odd double pull on a wreck · 9 reel 35% faster |
| **Cooking** | Healing food | 1 Grilled Silverfin (Smoked at the smokehouse) · 3 Kelp-wrapped Fish · 5 Crab Chowder · 7 Glowgill Stew |
| **Smithing** | Gear | 1 smelt Iron Ingots, the Iron Hook, Satchel Straps (+4 slots) · 2 Reinforced Rod · 4 Bolt-caster Mk II · 6 Tidebreaker Coat · 8 Lamplighter (Mk III) |
| **Combat** | Modest character growth | +5 HP/level · 5 second dash charge · 8 charged shot |

Skill levels speed you up; they don't lock materials away. The one gate on
salvage is a hook you can see: reinforced plating needs the **Iron Hook**.

### The salvage hook
A grapnel on a line, fired from the reel under the bolt-caster (RMB anywhere;
LMB too at home). The crosshair shows what it would take: in reach, out of
reach, or blocked and why (the tide, the hook, the Gloom, a full satchel).

- **Flotsam** drifts in through the cove mouth along the drift lanes, bobbing:
  plank bundles (timber), oil drums (scrap), kelp mats, netted bottles (sea
  glass), barrels (a mix), driftwood logs (lots of timber, a hard pull) and, on
  the flood, a sealed ship's crate (brass). Hook one and it reels across the
  water to you and into the satchel; heavy pieces reel slower. A miss splashes
  down and the hook comes back.
- **Wreckage** (the cove's wreck field, the Meridian's driftwood, scrap piles,
  kelp beds and reinforced plating) gives up a piece per pull, torn off and
  flung to you; it comes apart top first, down to its bones. The cove's wrecks
  are whole again at every low tide.
- **The beach.** What you miss washes up on the tideline; walk over it or hook it.
  Coming home, whatever drifted in while you were away is lying there (and in the
  cove net, once the net loft stands).
- **Tiers** are gear: the Rope Hook (16 m) to start, the Iron Hook (20 m, from the
  forge), the Brass Hook (26 m, from the net loft). Each reels faster.

Fishing is a short timing game: cast → bobber → bite splash + sound → press E
within the window (0.8 s, wider for Silverfin).

Crafting UI shows required vs owned materials, the item's benefit, any unlock
requirement, and a single clear **Craft** button.

### Resources (kept deliberately small)

| Id | Name | Source | Used for |
|---|---|---|---|
| `timber` | Timber | Plank bundles, logs and barrels in the drift; the sunken boat and pilings; the Meridian's driftwood | Rebuilds, decor, rod |
| `scrap` | Scrap Metal | Oil drums and barrels in the drift; the boiler; the Meridian's scrap piles; crabs | Smithing, rebuilds, lamp |
| `brass` | Brass Fittings | The Meridian's reinforced plating (Iron Hook); ship's crates on the flood; the captain's strongbox | Mk II, Brass Hook, lens mount |
| `iron_ingot` | Iron Ingot | Smelted at the forge (2 Scrap → 1) — the repeatable Smithing XP source | All smithed gear |
| `sea_glass` | Sea Glass | Netted bottles, barrels and crates in the drift | Lamp housing, cottages, lanterns |
| `kelp` | Kelp | Kelp mats in the drift; the old pilings; the Meridian's kelp beds | Cooking, rope, straps |
| `tidestone` | Tidestone | Every defeated enemy, now and then a ship's crate | Weapon upgrades, lens |
| `silverfin` | Silverfin | Fishing off the cove's rocks (any tide) | Cooking |
| `glowgill` | Glowgill | Fishing at high tide (off the jetty's end, and the Meridian), Reinforced Rod | Cooking |
| `crab_meat` | Crab Meat | Brine Crabs | Cooking |

Quest items (never lost, don't take satchel slots): `drowned_lens`,
`lighthouse_ember`.

---

## 9. Inventory, death, saving

- **Satchel:** 12 slots (16 with Satchel Straps), stacks of 20 (food 10). Quest
  items live in a separate key-item pouch.
- **Storage chest** at home: unlimited. **Deposit All** is one key. Rebuilds and
  decor draw on the satchel and the chest together.
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
| What am I doing next? | **Pinned objective** top-left (main quest), plus one **tracked resource goal** under it ("Timber 7/12"). Each short material names where it comes from; the compass points to the nearest place that has what you still need, then home once you have it all (with a "Take it home" toast) |
| Why am I here at all? | A four-card **prologue** on a new game (the sea rose; the lights hold back the Gloom; this one is failing; you're its new keeper); Maren's first lines spell out the loop; the journal's Lighthouse tab states the chapter's aim |
| What do I need for the next lighthouse upgrade? | Journal → Lighthouse tab, and the tracked goal |
| What did I gain on this trip? | **Haul** counter on HUD while away; return summary screen when you're home, with what drifted in meanwhile |
| Can the hook take that? | The **crosshair** rings what you aim at: in reach, out of reach, or blocked, with the reason under it |
| What is the tide doing? | **Tide dial** top-right: state, countdown, a little water-level gauge; banner on warning |
| Can I safely return home? | Compass strip shows the **landing point** icon and distance; the beam on the horizon |

Health bottom-left as a lantern-glass gauge; dash pips next to it; food quick-slot
bottom-centre.

---

## 11. Content — Chapter 1

See `docs/LEVELS.md` for layouts, tide behaviour and encounter placement.

1. **Lantern's Rest** (home, safe) — the lighthouse on its knoll (lamp room and
   chart table), the village terrace (square, hearth, storage chest, the forge
   and three cottage plots), the quay below it (net loft and smokehouse plots)
   and the cove: a beach, the jetty plot, the low-tide wreck field, fishing off
   the rocks, and the drift coming in between two rock arms. Maren is there from
   the start; Tib comes with the jetty, Odile with her cottage, Hesk at Stage 1,
   the Pells and the Ashbys with theirs.
2. **Wreck of the Meridian** (dangerous) — Crabs, Spitters, Wisps, Lurkers; wreckage
   to hook, brass behind reinforced plating (Iron Hook); two tide routes to the
   **Drowned Lens**. The first fight, about 15–20 minutes in.
3. **Saltmere Beacon** (finale) — short causeway approach, the **Wreck Guardian**
   boss, the beacon and its relighting sequence.

Home stays a sanctuary, so there's no fighting until the Meridian; the next pass
reworks the Meridian's and Saltmere's maps around the hook.

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

1. **Wake the Keeper** — talk to Maren by the lighthouse door.
2. **The Sea Gives** — hook 6 pieces of what the tide brings into the cove.
   *(Teaches the hook.)*
3. **Rebuild the Forge** — 8 Scrap + 6 Timber, handed in as you get it. *(The
   first rebuild, a few minutes in.)*
4. **Rebuild the Jetty** — 18 Timber + 6 Kelp. Tib brings the boat in.
5. **Bring Them Home** — rebuild the Marsh Cottage; Odile comes home.
6. **Feed the Rest** — fish 3 Silverfin off the rocks and grill them at the hearth.
7. **Restore the Lamp** — 14 Scrap + 10 Sea Glass + 8 Timber, with the forge, the
   jetty and the Marsh Cottage standing → **Stage 1**. The beam reveals the
   Meridian; Hesk arrives.
8. **The Drowned Lens** — recover it from the Meridian.
9. **Focus the Light** — Lens + 8 Brass + 5 Tidestone → **Stage 2**. Beam reveals
   Saltmere; receive the **Lighthouse Ember**.
10. **Relight Saltmere** — defeat the Wreck Guardian, place the Ember → **Stage 3**.

Optional, with real perks: the Net Loft (the Brass Hook, the cove net), the
Smokehouse (smoked fish), the Pell and Ashby cottages (families home) and decor.
Rewards are perks, people, XP and the look of the place — **no currency**.

### First-session pacing (15–20 min)
The pacing simulation (`src/systems/economy.ts`, held to `src/data/pacing.ts` by
`tests/economy.test.ts`) plays it like this: Maren (1 min) → the cove: the hook,
the first 6 pieces (3 min) → the forge stands (about 5 min) → the jetty (6) →
Odile's cottage (9) → fish and grill (10) → the lamp, Stage 1 (about 16 min) →
the boat to the Meridian. A new game starts with high water just in, the cove
full of drift for the first lesson; the ebb bares the wreck field about when the
forge goes up (`TIDE.newGameOffset`).

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
until combat feels good · free-form building of walls and houses (decor pieces
only; the buildings are the plots).
