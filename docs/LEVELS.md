# Level Design — Chapter 1

Units: **1 unit = 1 metre**, +Y up, Blender +Z up (the glTF exporter converts).
Player eye height 1.65 m, capsule radius 0.35 m, jump apex ~1.1 m, dash 6 m.

**Tide heights (all locations):** low water `y = 0.0`, high water `y = 1.8`.
Design every surface against these bands:

| Band | Height | Meaning |
|---|---|---|
| Always dry | `y ≥ 2.4` | Safe at all tides. Landing points, anchors, home's terraces. |
| Tidal | `0.2 ≤ y < 1.8` | Walkable at low tide, flooded at high tide. Paint foam tide-line decals here. |
| Wading | water depth 0.5–1.1 m | Move speed ×0.6, can shoot. |
| Swimming | water depth > 1.1 m | Speed ×0.45, can't shoot, can dash; after 6 s the current carries you to the nearest `ANCHOR_*`. |

Every location is a single `.glb` exported from `art/blender/locations/<id>.blend`
with the object-naming rules in `ART_PIPELINE.md` (`COL_`, `SPAWN_`, `NODE_`,
`ANCHOR_`, `BUOY_`, `TRIG_`, `GLOOM_`, home's `PLOT_` and `FX_drift_`…). The game
reads those empties to place gameplay. `tests/tide-sweep.test.ts` proves each
level can't trap you: from anywhere you can reach, at either tide, there's a way
back to the landing (at home, with the plots in ruins, rising and rebuilt).

---

## Lantern's Rest (home) — `home`

The player's base. ≈ 100 × 130 m with the arms. **No enemies, but the tide is
real here:** the cove has a beach, flats and a wreck field the water covers and
uncovers, so home is swept for tide traps like everywhere else. Built by
`tools/blender/build/home_map.py`; `src/world/home/HomeLevel.ts` only layers
progression over it (the plots rising, who's home, the boats). Game space: x east,
z south, y up; the cove opens south.

```
                               N (−z)
      fields · washing · memorial               ┌─ KNOLL (y 12.5) ──┐
   cottage_3        cottage_2   garden          │ LIGHTHOUSE ⌂ start │ lamp, Maren
   (Ashby)          (Pell)   cottage_1 (Marsh)  └──── path ↙ ───────┘
        FORGE ── SQUARE (y 7): hearth, chest, well
                     │ ramp ↓ (from the bastion)
 W    NET LOFT ── QUAY (y 4): Tib's boat on trestles ── SMOKEHOUSE          E
 ARM        west steps ↓        │ slipway ↓        jetty steps ↓           ARM
   │  ──────── BEACH (dry above y 1.8) ──── landing ⚓ ──── JETTY ║          │
   │  shelf ↓ · fishing ledge · rock pool (Silverfin)          ║ boats      │
   │        pilings · sunken boat · boiler  (bared at low tide)  ║ Glowgill  │
    ╲              flats (low tide)                                        ╱
      ╲__ west arm's tip              stacks ◆◆            east arm's tip _╱
                    ↑ the drift comes in through the mouth (SSE)
                               S (+z)
```

- **Spawns:** `SPAWN_start` at the lighthouse door (a new game, a loaded save);
  `SPAWN_landing` on the beach by the jetty (back by boat before the jetty
  stands, and after a defeat; where the tide sweep starts); `SPAWN_jetty` at the
  jetty's end (back by boat once it stands).
- **Terraces:** the village at y 7 (the square on a bastion over the quay, a
  parapet round it), the quay at y 4, the beach under the quay's sea wall, dry down
  to the high-water line at z ≈ 27. The knoll path climbs the knoll's south flank
  from the village. Retaining walls are mortared stone with a collision box behind
  each face.
- **Plots** (`PLOT_<project>`, see `ART_PIPELINE.md`): the forge on the square's
  west side, the Marsh, Pell and Ashby cottages round the village, the net loft
  and smokehouse on the quay, the jetty along the cove's east side. Each has its
  ruin, its finished building and a name board (`interact: plot:<id>`). The boat
  ties up on the east side of the jetty's T-head; the jetty's `station` mark
  faces the berth, so "Take the boat" is there at any tide (at low water the
  boat lies 2.7 m below the deck).
- **People:** `NPC_maren` by the lighthouse, `NPC_tib` at the jetty's foot,
  `NPC_odile` at the hearth, `NPC_hesk` by the forge; `PLACE_family_0_*` and
  `PLACE_family_1_*` by the Pell and Ashby doors.
- **The cove's salvage:** five drift lanes (`FX_drift_<lane>_<k>`) from beyond the
  mouth to the tideline, where up to ten pieces lie washed up (`FX_strand_<n>`,
  all above high water). The wreck field (`NODE_sunken_boat_00`,
  `NODE_old_pilings_00/01`, `NODE_boiler_00`, 17 pieces in all) is bared at low
  tide and whole again at every ebb.
- **Fishing:** Silverfin in the rock pool off the fishing ledge under the west arm
  (any tide); Glowgill off the jetty's end at high water, once it stands.
- **Decor:** `FX_decor_<n>` outlines the village where build mode places pieces;
  `CLEAR_<n>` circles (with a `radius`) keep the plots, doors, paths, stations and
  people clear.
- **The coast:** off the cove, the village's cliffs, the knoll and the arms'
  seaward flanks run steep all the way down to a flat sea floor at y −3, swimming
  depth at low water, so nothing out there is a shelf in the tide's reach. Sea
  rocks stand off the cliffs, stretched up clear of high water and kept 1.8 m
  from the shore, so you can neither climb onto one from the water nor drop onto
  one from above. The stacks at the mouth stand in scour holes.
- **Anchors:** the square, the quay, both ends of the beach, the fishing ledge,
  both arms and both arm tips, and the knoll.
- **Lighting:** warm. The hearth, the forge once it's lit, lamp posts on the
  square, the ramp's foot, the slipway, the jetty steps and the knoll path.
- **Gulls** on the lamp posts, the memorial, the field walls, the boat on its
  trestles, the quay's bollards and the wall over the quay (`FX_perch_<n>`),
  wheeling over the beach (`FX_gulls`).
- **First tide change:** a new save starts with high water just in, the cove full
  of drift for the first lesson with the hook; the ebb bares the wreck field about
  when the forge goes up. The tide clock only runs while playing, never behind the
  title or pause card.

---

## Wreck of the Meridian — `wreck`

Dangerous. A steam-sail ship beached on a reef. ≈ 140 × 100 m. Holds the
**Drowned Lens**. Built by `tools/blender/build/wreck.py`; coordinates are game
space (x east, z south, y up).

```
                 north (−z)
   ┌─ stern castle ─┬──────────── main deck (y 6) ─────────────────────┬─ bow ─┐
   │ CHART ROOM ◆   │ hatch ↓ (hold ramp)   funnel   mast   foremast    │ strongbox
   │  x −34 … −25   │                                                   │  x 34–42
   └──┬─ broken ────┴──── mast notch ──────── HULL BREACH (x −3 … 7) ───┴───────┘
      │ rail ↓            ↑ fallen mast (foot y 2.6)    ↑ planks into the hold
   ┌──┴──────────┐  ▣▣▣▣▣▣ crates (BUOY_)          reef flats (y 0.2 – 1.0)
   │ LANDING     │  lagoon (floor −0.5)               crabs · debris field (wisps)
   │ shelf y 2.8 │
   └─────────────┘  rocky slope down to the flats
   ⛵ boat (west)
```

**Two routes to the lens — the tide decides which:**

| | **Low tide — "Through the Hold"** | **High tide — "Over the Rail"** |
|---|---|---|
| Path | Shelf → slope → reef flats → **hull breach** → hold (floor 0.3 → 0.9) → ramp along the north wall → up through the deck hatch → chart room | Shelf → **six cargo crates** floating across the lagoon (tops at 2.4) → onto the **fallen mast**'s foot (2.6) → up the mast to the deck → chart room |
| Why only then | At high tide the flats and hold are 1.5 m deep: ~24 m of swimming, so the current rescues you first | At low tide the crates sit on the lagoon floor and the mast's foot is 2.6 m up: out of reach even with a dash-jump |
| Danger | Crabs on the flats, Spitters in the hold | Tide Lurkers in the lagoon, Wisps over the deck, the bow Spitter |
| Reward | **Reinforced wreckage** (brass) along the hold | Strongbox on the bow deck, Glowgill off the stern |

- **Lens:** `NODE_lens_pedestal_00` in the chart room. Taking it triggers the
  ambush at `FX_ambush_lantern_wisp_1/2` and `FX_ambush_drowned_spitter_1`.
- **Ways down from the deck, any tide:** drop through the broken stern rail onto
  the shelf, or (once you hold the lens) the **rope ladder** at the stern
  (`INT_rope_ladder` → `SPAWN_ladder`).
- **Anchors:** shelf, slope, flats, bow sand. None on the deck — a rescue there
  would skip both routes.
- Two lanterns burn in the hold; the home beam shows on the northern horizon.
- **Gulls** on the snapped foremast, the main top and the capstan; the flock
  wheels over the main mast (`FX_gulls`).
- **Gloom:** the chart room (`GLOOM_chart_room`, r 3.2) hangs over the lens, and
  the hold (`GLOOM_hold`, r 3.0) over its wreckage: flare before you loot.

---

## Saltmere Beacon — `beacon`

Compact finale. ≈ 100 × 80 m around a rock stack. Built by
`tools/blender/build/beacon.py`.

```
                        TOWER (platform y 7) — INT_beacon at the door, beam at FX_beacon_lamp
                          ↑ stair ramp (walled; rubble until the Guardian falls)
          ┌──── RING ARENA (y 3, r 15, FX_arena) ────┐
   sea    │ standing stones · 4 cover pillars        │ ← GATE (wisps ×2) ← CAUSEWAY (y 2.8) ← LANDING (y 3) ⛵
          └──────────────────────────────────────────┘        spitters on rocks either side
                      ⟳ WRECK GUARDIAN rises from the sea (south, z 18.5)
```

- **Tide** only changes how high the water sits around the stack. The arena,
  causeway and landing never flood.
- **Boss trigger:** `TRIG_boss` covers the arena; entering wakes the Guardian.
  You can always retreat down the causeway; 19 m from the arena centre it sinks
  and heals 25%, and walking back in wakes it again.
- **After the fight:** `STATE_guardian_defeated_off` (rubble across the stair)
  disappears, `STATE_guardian_defeated_on` (braziers) appears.
- **Relight:** `INT_beacon` with the Ember → Stage 3 → chapter card;
  `STATE_chapter1_complete_on` lights lanterns along the causeway.
- **Gate:** the arch stands on a coursed stone footing built out from the arena's
  edge, whose sill carries the floor through to the first causeway stone (the
  rock drops away steeply under it).
- **Gloom:** two pockets on the causeway (`GLOOM_causeway_0/1`, r 2.6) between the
  Spitters' rocks: flare through them, dazzling whoever's spitting.
- **Anchors:** landing, causeway, arena east, arena north.
- **Gulls** on the two quay bollards and the quay edge, so they go up as you land;
  the flock wheels round the tower (`FX_gulls`).

---

## Every horizon

Past the playable edge each place has the drowned world on its horizon
(`src/data/scenery.ts`, models in `scenery.glb`): roofs and a church spire
standing in the sea, telegraph poles walking out from the shore, sea stacks, a
lighthouse that went dark, a wreck's masts, a windmill, a far headland. Pieces sit
90–170 m out, inside the fog, and never in line with the home beam.

## Encounter tuning targets

| Location | Enemies per visit | Expected time | Expected haul (common mats) |
|---|---|---|---|
| Home (the cove) | none | as long as you like | a piece of drift every 9–16 s by the tide (the flood brings the most); 17 wreck pieces per ebb |
| Wreck | ~4 crabs, 3 spitters, 3 wisps, 2 lurkers (high) | 7–10 min | 25–40 + brass |
| Beacon | 2 spitters, 2 wisps, boss | 5–8 min | boss chest |

What the pacing simulation (`tests/economy.test.ts`) gets for a player who
hooks what's needed on the way, on average rolls:

| Stretch | Time | Haul |
|---|---|---|
| Home, a new game to Stage 1 | 17 min | 73 timber, 39 scrap, 23 kelp, 14 sea glass, 2 brass |
| Wreck | 8.5 min | 14 brass, 16 scrap, 14 tidestone, 4.5 kelp; back home, 15 timber, 8 scrap, 5 kelp and 4 sea glass on the beach |
| Beacon | 7 min, with the Guardian | 14 tidestone, 6 brass |

The forge stands about 5 minutes in, Stage 1 at about 16 (`src/data/pacing.ts`
holds both). Timber is plentiful by design: what isn't rebuilt goes into decor.
