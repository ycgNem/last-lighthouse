# Milestones — Chapter 1 vertical slice

Build in this order. Each milestone ends **playable** and with its acceptance
checks passing. Don't start the next one until the current one feels good —
especially M1: if moving and shooting isn't fun, nothing else will save it.

Status key: `[x]` done · `[~]` partly done (see note) · `[ ]` todo · `(B)` needs
Blender work · `(T)` has an automated test

**Where things stand (2026-10-28):** Chapter 1 is playable start to finish: home,
the shore, the wreck by either tide route, the beacon and the Guardian, the
relight and the chapter card. M1–M6 are done apart from the items marked below.
M7's automated checks are in: the tide-trap sweep, the pacing simulation and the
draw-call budget. What's left is people: three fresh playthroughs to confirm the
pacing, hand-playing every encounter at speed, plus the cinematic upgrade beats,
the chart's fog burning back, a beacon landing on the home chart and the debug
overlay.

**Feel and world pass (2026-10-28):** frame time down by roughly two-thirds at home
(shared villager skeletons, shader prewarm, change-only HUD writes), a semi-fixed
loop with no judder at high refresh, adaptive resolution with a Settings override;
the dash rebuilt (exact distance, no slide, air hold, input buffer) **(T)**; a
prologue and clearer guidance; the drowned world on every horizon; the shore and
home dressed; gulls; and a proper sea chart.

---

## M0 — Foundation ✅

- [x] Vite + TypeScript (`strict`) + Three.js pinned (`three@0.186.1`,
      `@types/three@0.186.0`)
- [x] Semi-fixed-timestep game loop, typed event bus, input with pointer lock (and a
      free-look fallback where the browser refuses it) + rebindable actions
- [x] Typed, data-driven definitions: items, recipes, skills, enemies, locations,
      lighthouse stages, projects, quests, NPCs, tide, balance
- [x] Data validator (references + progression reachability) **(T)**
- [x] Pure logic systems: tide clock, inventory/storage, skills/XP, crafting,
      lighthouse progression, quests, save/load with schema version **(T)**
- [x] Blender → glTF pipeline and naming conventions; `npm run build:art`

---

## M1 — Movement, camera, collision, combat feel ✅ (one item open)

- [x] Capsule vs BVH collision (`three-mesh-bvh`) against `COL_`/`col` meshes,
      sub-stepped so a dash can't tunnel; dynamic boxes for floating platforms
- [x] Camera: FOV slider, sensitivity, head-bob toggle, landing dip, dash FOV kick,
      screen shake (toggle)
- [x] Viewmodel: bolt-caster right hand, lantern left hand, sway, recoil, lowered
      at home and while fishing **(B)**
- [x] Projectile pool (player bolts, enemy orbs, lobbed mortars), swept hits
- [x] Bolt-caster Mk I / Mk II / Lamplighter: fire rate, spread, speed, pierce from
      gear stats; impact sparks *(no separate muzzle flash yet)*
- [x] Damage, i-frames, hit flash, knockback, red damage-direction arc, low-health
      vignette, hit markers (weak-point hits marked)
- [x] Threat pips for off-screen windups
- [x] Enemy base: state timer, telegraph glow (`GLOW_` materials), steering, line
      of sight, loot and death
- [x] Brine Crab and Drowned Spitter **(B)**
- [x] Player death → "The tide carries you home"
- [ ] Debug overlay (`` ` `` key). For now the dev console has `__ll` helpers.

**Accept:** dash reliably avoids a lunge and an orb fan; no stuck-on-geometry in a
5-minute playtest; 60 fps on a mid laptop with 20 enemies + 150 orbs.
*Movement and routes are verified by scripted walks; a hand playtest at full
speed and a perf check are still to do.*

---

## M2 — Gullwash Shore: gathering and meaningful tide ✅

- [x] Location loader: `<id>.glb` → spawns, anchors, nodes, enemies, buoys,
      triggers, interacts, named points, state objects, warm lights, collider
- [x] **Gullwash Shore** **(B)**: dunes, flats, sandbar to the islet, rocky spit,
      jetty, cliff path home
- [x] Gather: crosshair focus with close-range help, prompt (says why when you
      can't), hold-to-gather ring, burst, sparkles into the satchel, merged toasts
- [x] Fishing: cast, bobber, bite splash and sound, timing window, catch; move or
      fire to reel in
- [x] Tide drives wading/swimming, node availability, enemy sets per tide (low-tide
      crabs slip away when the water rises unless mid-attack)
- [x] Tide warning: horn, banner, foam glow on `TIDE_` surfaces **(B)**
- [x] Anti-trap: swim timer → the current carries you to the nearest `ANCHOR_`
- [x] Haul counter while away; skill XP and level-up toasts
- [ ] Automated "never trapped" sweep over walkable sample points at every tide

**Accept:** a shore trip yields 18–30 materials in ~5 min; the sandbar route
appears/disappears with the tide; standing anywhere at any tide change never
traps or kills the player.

---

## M3 — Home, inventory, crafting, saving ✅

- [x] Travel: chart (lit radius grows with the beam, fog hides the rest), boat with
      a fade and location card, cliff path to the shore, row home from anywhere
- [x] Return summary ("Home again": haul, XP, creatures driven off)
- [x] Storage chest: deposit all (keeps food), store a slot, take a stack
- [x] Hearth and forge menus: inputs owned/needed, benefit, unlock level, ×1/×5
- [x] Food: F eats (heals over a second, slows you briefly), Z cycles; chowder
      and stew buffs
- [x] Death: lose 40% of each unbanked stack (keep ≥ 1), keep key items and
      storage; loss summary **(T)**
- [x] Autosave (actions, travel, every 60 s) + journal settings (sensitivity, FOV,
      volume, shake, head bob, reset with two confirmations)
- [x] NPCs Maren / Odile / Tib / Hesk with per-quest-step lines
- [x] Pinned objective with a materials checklist that counts what's still needed
      **(T)**

**Accept:** quit mid-expedition and reload → you're back at that location's
landing with what you carried; reset wipes everything after two confirms; death
loses exactly the specified amounts.

---

## M4 — Lighthouse upgrades and visible world change ✅ (two items open)

- [x] Settlement projects: forge (glow, embers) and dock (missing planks appear)
- [~] Stage 0 → 1 (Restored Lamp): requirements panel, upgrade, banner, world
      change. *The cinematic (camera pull-out, windows lighting one by one) isn't
      built.*
- [~] Chart reveal: newly reachable places appear on the chart. *No animated
      fog burn-back yet.*
- [x] Stage-driven world: windows, chimney smoke, NPC arrivals, family at stage 2,
      boats, fog distance, beam colour/length/flicker, all from `lighthouse.ts`
- [x] Quest steps 1–5 end to end (verified in the running game)

**Accept:** a fresh save reaches Stage 1 in 15–25 min of normal play (playtest +
economy test **(T)**); every visible change listed in GDD §4C is present.

---

## M5 — The Meridian, Saltmere Beacon, boss, victory ✅ (one item open)

- [x] **Wreck of the Meridian** **(B)**, both tide routes (see LEVELS.md); the
      tide gates each one (checked: at low tide the mast foot is out of reach even
      with a dash-jump; at high tide the hold means a rescue-length swim)
- [x] Floating cargo crates (`BUOY_*`) ride the water; you can stand on them
- [x] Lantern Wisp and Tide Lurker **(B)**
- [x] Drowned Lens pickup → ambush (2 Wisps + 1 Spitter) → rope-ladder exit
- [x] Stage 2 (Focused Lens) + the Lighthouse Ember
- [x] **Saltmere Beacon** **(B)** and the **Wreck Guardian**: chain sweep (jump or
      dash it, then the heart is exposed), brine mortars with closing rings,
      undertow below half health; leave the arena and it sinks and heals 25%
- [x] Rubble blocks the stair until the Guardian falls; braziers light
- [x] Relight → Stage 3 → "Chapter One complete" card; causeway lanterns; free
      play continues
- [ ] A beacon landing on the home chart after the chapter

**Accept:** lens reachable at both tides (verified by scripted walks; level
markers **(T)**); boss beatable by a prepared player in 3–4 min; chapter
completion saves and survives reload.

---

## M6 — Presentation, audio, quality of life

- [x] Water shader pass: depth colour from each level's seabed (baked from its
      collision at load), shoreline foam, specular glints, Gerstner swells that
      calm in the shallows, ripples and rain rings; underwater tint and muffled
      sound when swimming
- [x] Rain (GPU streaks in a box that travels with the camera, so nothing pops
      in; roofs keep it off), with a rain bed in the audio; fog per location
- [x] Post: HDR bloom on emissives and the beam (the hands are drawn after it, so
      the lantern doesn't flood the screen); damage vignette
- [x] Audio (synthesised, no files): ambience per location, positional enemy
      cues, tide horn, UI, craft and upgrade sounds. *No music stingers.*
- [x] **Lantern Flare** (Q): staggers enemies in a cone (each its own time, the
      Guardian immune), dispels Gloom pockets (`GLOOM_` markers: they shroud the
      loot inside and chill you, never below 15 HP) **(B)**
- [x] Compass strip: landing, path home, quest objective
- [x] Accessibility: rebinding UI (keys swap, Esc cancels), high-contrast enemy
      shots (pale cores, dark rims), reduced motion (follows the OS on a new
      save), sound captions with direction; NPC lines were already text
- [x] Premise up front: a four-card prologue on a new game, Maren's lines on the
      loop and the tide, the chapter's aim and creed in the journal
- [x] Guidance: materials name where they come from; the compass points to the
      nearest source, then home; "Take it home" once you have everything
- [x] A living coast **(B)**: the drowned world on every horizon, the shore's old
      road, lamps, wreck and croft, the village's walls, garden, well, washing,
      nets and memorial, gulls that wheel overhead and take off as you approach
- [x] Sea chart: coast and shoals, the drowned town, routes, soundings, the beam
      sweeping its reach, dead lights waiting in the fog

---

## M7 — Balance and ship check

- [~] Economy pass: the simulation plays the chapter on expected yields against
      the tide clock (Stage 1 at 16 min on the second shore run, the whole
      chapter in about 35 min over four trips of 6–9 min) **(T)**. *The three
      fresh playthroughs are still to do.*
- [x] Performance: under 300 draw calls everywhere, every enemy alive (static
      scenery merged by material at load, rigid models folded to vertex colour,
      shadows only from what's near; the wreck peaks at 296). No image textures
      at all, so the texture budget is just the render targets. Scatter is merged
      rather than instanced, which is what the draw-call budget needed.
      Frame time: one skeleton per villager (bone-texture uploads stalled the
      GPU), shaders compiled during the travel fade, and an adaptive resolution
      (Settings → Resolution; Auto by default) for GPU-bound screens.
- [ ] Final checklist (from the original brief):
  - [x] The player cannot become trapped by the tide (rescue current, level
        design, and a sweep of every level at both tides in every progression
        state; it also proves every node and interactable can be reached) **(T)**
  - [x] Materials and recipes allow progression without a softlock **(T)**
  - [x] Death and saving work consistently **(T)**
  - [x] The first lighthouse upgrade can actually be completed
  - [x] The boss and first beacon can be reached and finished
- [x] README: how to run, controls, what's implemented, known limitations

---

## Later chapters (not in the slice)

Beacons 2 and 3 (a drowned town at the river mouth; a kelp-forest reef), new skill
tiers 11–20, a second weapon (harpoon), the storm region and final threat.
