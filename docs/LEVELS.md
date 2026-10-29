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

Dangerous. A steam-sail ship driven up onto a reef, her stern against the islet
you land on. ≈ 140 × 100 m. Holds the **Drowned Lens**. Built by
`tools/blender/build/wreck.py`; coordinates are game space (x east, z south, y up).

```
                     north (−z): open sea, the home beam on the horizon
        ┌ stern castle ┬──────────── main deck (y 6) ────────────────┬─ bow ─┐
        │ CHART ROOM ◆ │ hatch ↓ (ramp in the hold)   funnel  masts   │ strongbox
        └──┬ broken ───┴─ fallen mizzen ── HULL BREACH (x −3 … 7) ───┴───────┘
   ┌───────┴──────┐ ↑ foot y 2.6     ↘ the cargo spill          reef flats
   │ ISLET        │ ▣▣▣ cargo jam      rock ribs, sand gullies,  (y 0.2 – 0.9)
 ⛵ gut  · camp   │ lagoon (−0.5)      tide pools · crabs            │
   │ crown y 3.3  │                    (a swim at high water)    old hulk's ribs
   │ crag, reef   ├─ tail ─┐                                     the Horn (y 6.2)
   │ beacon       │        └────── rampart: the reef's rim, dry at high water ─┘
   └──────────────┘
```

**Two routes to the lens — the tide decides which:**

| | **Low tide — "Through the Hold"** | **High tide — "Over the Rail"** |
|---|---|---|
| Path | Islet → down its tail → across the reef's ribs and gullies → the spill's planks into the **hull breach** → hold (floor 0.3 → 0.9) → ramp along the north wall → up through the deck hatch → chart room | Islet's ledge → the **cargo jam** (six crates, `BUOY_`, tops at 2.4) curving across the lagoon → onto the **fallen mizzen**'s foot (2.6) → up the mast to the deck → chart room |
| Why only then | At high tide the band of reef between the islet and the breach is a swim, and the current rescues you before you're across | At low tide the crates sit on the lagoon floor and the mast's foot is 2.6 m up: out of reach even with a dash-jump |
| Danger | Crabs on the reef, Spitters in the hold | Tide Lurkers in the lagoon, Wisps over the deck, the bow Spitter |
| Reward | **Reinforced plating** (brass) in the hold and at the breach | Strongbox on the bow deck, Glowgill off the stern |

- **The islet:** layered dark rock under thin turf, its crown about y 3.3 by the
  stern (never within jumping reach of the deck), rising south-west to a crag with
  the reef beacon on it. You land at the head of a gut on its west side, where the
  boat lies at both tides. An abandoned salvagers' camp on the crown: a lean-to, a
  cold fire, casks, a sheerlegs over the lagoon.
- **The reef:** rock ribs running south-east with sand, weed and tide pools between,
  bared at low water. Between the islet and the breach it stays low (a swim at high
  water); round that it rises to a belt you can wade at high water, up to the
  **rampart**, the reef's rim, dry at any tide, which climbs to a knoll, the Horn,
  in the south-east. Outside the rampart the reef drops straight to swimming depth;
  sea rocks and stacks stand off it. North of the ship is open sea.
- **The cargo spill** fans out of the breach across the reef: split crates, bales,
  barrels, coal, a smashed lifeboat, a yard and its rigging, the anchor and cable.
  An older wreck's ribs and keel lie on the reef's far side (the debris glows there).
- **Salvage** (hooked, in pieces, top first): spars along the spill and the reef,
  machinery by the breach, on the reef and two heaps on the deck, kelp in the tide
  pools, brass-strapped plating in the hold and outside the breach (the Iron Hook).
  Some can be hooked from the islet's ledge or the rail, out of the crabs' way.
- **Lens:** `NODE_lens_pedestal_00` in the chart room. Taking it triggers the
  ambush at `FX_ambush_lantern_wisp_1/2` and `FX_ambush_drowned_spitter_1`.
- **Ways down from the deck, any tide:** drop through the broken stern rail onto
  the islet, or (once you hold the lens) the **rope ladder** at the stern
  (`INT_rope_ladder` → `SPAWN_ladder`).
- **Anchors:** the islet (two), its tail, the rampart's west end, the Horn, and the
  bow's sand. None on the deck — a rescue there would skip both routes. Each is dry,
  or a wade, at high water.
- Lanterns burn in the hold and on the deck, at the camp and at the landing; the
  home beam shows on the northern horizon.
- **Gulls** on the snapped foremast, the main top, the capstan, the reef beacon, the
  sheerlegs and the old hulk; the flock wheels over the main mast (`FX_gulls`).
- **Gloom:** the chart room (`GLOOM_chart_room`, r 3.2) hangs over the lens, and
  the hold (`GLOOM_hold`, r 3.0) over its wreckage: flare before you loot.

---

## Saltmere Beacon — `beacon`

The finale. ≈ 130 × 110 m: a sea stack with the beacon on it, the old landing
stage at its foot, a breakwater out to the headland where you land. Built by
`tools/blender/build/beacon.py`.

```
                north (−z): the stack, sheer to deep water, its summit y 17
              ┌─────────────────── STACK ───────────────────┐
              │  TOWER on a shoulder cut into it (y 7),      │ INT_beacon at the door,
              │  walled into the rock, parapet over the sea  │ beam at FX_beacon_lamp
              └────────────┤ stair in a cleft ├──────────────┘
                           │ rubble until the Guardian falls
  west rocks ▲▲   ┌────────┴──────────────────┐
  (a ridge you    │ OLD LANDING STAGE (y 3)   │ ← GATE ← BREAKWATER (y 2.8) ←── LANDING
   can climb)     │ compass rose, FX_arena    │  wisps   parapet on its north     quay, gut ⛵
                  │ sheds · crane · blocks    │          spitters on skerries    boathouse
                  └──── broken sea wall ──────┘
                      ⟳ WRECK GUARDIAN rises (z 18.5)
                           ⌒ sea arch (z 33)
```

- **The landing:** a rock headland with a gut cut into it from the east; the boat
  lies in the gut at any tide, beside a quay with landing steps down to the water,
  bollards, a post crane and lamp posts. A roofless boathouse with a crow-stepped
  gable stands at the gut's head, its slip running down into the water.
- **The breakwater:** a mole of dressed blocks on a rubble mound and a chain of
  skerries, its walk at y 2.8 (it never floods), from the landing to the gate. A
  parapet along its north side, broken in places, is cover from the north Spitter;
  the Spitters stand on skerries either side, out of reach. Along both faces the
  water is swimming depth, so a fall off it ends in the sea.
- **Gate:** the arch stands on a coursed stone footing built out from the stage's
  edge, whose sill carries the floor through to the breakwater (the rock drops away
  steeply under it).
- **The arena** is the old landing stage: worn rock and flagstones round the
  compass rose at y 3, walkable out to 15 m from `FX_arena`. North, the stack's
  foot; west, rocks rising to a ridge you can climb; south, a broken sea wall over
  deep water; east, the gate. Cover stands about 8 m out on the diagonals: two
  roofless store sheds (north-east and north-west, their doors away from the sea),
  the stage's fallen crane (south-west: its pedestal, girder jib and winch) and a
  stack of dressed blocks with a capstan (south-east). Bollards and broken lamp
  posts stand round the rim.
- **Boss trigger:** `TRIG_boss` covers the arena; entering wakes the Guardian.
  You can always retreat down the breakwater; 19 m from the arena centre it sinks
  and heals 25%, and walking back in wakes it again.
- **The sea arch** stands in deep water about 33 m south, framing the Guardian as
  you look out from the arena.
- **The stack:** layered rock, sheer to deep water on the west, north and east,
  its summit rising behind and west of the tower, clear of the beam's line to
  home. The tower's platform (y 7) is a shoulder cut into its south face, walled
  on three sides, with a parapet along its edge over the sea. None of them can be
  climbed, so the stack's top is out of reach.
- **The stair** climbs a stone-faced cleft from the arena's north edge to the
  platform. Rubble (`STATE_guardian_defeated_off`) blocks its foot until the
  Guardian falls, and it's the only way up (the tide sweep checks both).
- **After the fight:** the rubble disappears, and `STATE_guardian_defeated_on`
  (braziers at the stair's foot) appears.
- **Relight:** `INT_beacon` with the Ember → Stage 3 → chapter card;
  `STATE_chapter1_complete_on` lights lanterns along the breakwater.
- **Tide:** only the water round the rock changes. Low water bares shelves under
  the stack, the skerries and weed; the arena, the breakwater and the quay never
  flood. Shelves lie only under cliffs you can't climb down, and slope off into
  swimming depth: dropped onto from walkable rock, a shelf and a ragged cliff foot
  make a pocket the tide sweep can't walk out of.
- **Gloom:** two pockets on the breakwater (`GLOOM_breakwater_0/1`, r 2.6) between
  the Spitters' skerries: flare through them, dazzling whoever's spitting.
- **Anchors:** the landing, the breakwater, and the arena's east, north and west.
- **Gulls** on the quay's bollards and the crane's jib, so they go up as you land;
  on the sheds, the standing lamp posts and the arch; the flock wheels round the
  tower (`FX_gulls`).

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
