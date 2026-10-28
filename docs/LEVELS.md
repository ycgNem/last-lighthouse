# Level Design — Chapter 1

Units: **1 unit = 1 metre**, +Y up, Blender +Z up (the glTF exporter converts).
Player eye height 1.65 m, capsule radius 0.35 m, jump apex ~1.1 m, dash 6 m.

**Tide heights (all locations):** low water `y = 0.0`, high water `y = 1.8`.
Design every surface against these bands:

| Band | Height | Meaning |
|---|---|---|
| Always dry | `y ≥ 2.4` | Safe at all tides. Landing points, anchors, home. |
| Tidal | `0.2 ≤ y < 1.8` | Walkable at low tide, flooded at high tide. Paint foam tide-line decals here. |
| Wading | water depth 0.5–1.1 m | Move speed ×0.6, can shoot. |
| Swimming | water depth > 1.1 m | Speed ×0.45, can't shoot, can dash; after 6 s the current carries you to the nearest `ANCHOR_*`. |

Every location is a single `.glb` exported from `art/blender/locations/<id>.blend`
with the object-naming rules in `ART_PIPELINE.md` (`COL_`, `SPAWN_`, `NODE_`,
`ANCHOR_`, `BUOY_`, `TRIG_`…). The game reads those empties to place gameplay.

---

## Lantern's Rest (home) — `home`

Compact (≈ 90 × 70 m) rocky headland. **No enemies. Tide is cosmetic here** — the
water rises and falls against the sea wall but never reaches a walkable surface.

```
            N
   ┌────────────────────────────┐
   │   cliffs          LIGHTHOUSE│   lamp room (top): CHART TABLE, Maren
   │        ╭──────╮   ( tower ) │
   │ cottage│square│    stair    │
   │  (S2)  │HEARTH│──── path ───┤
   │ Odile's│ chest│  FORGE      │
   │ house  ╰──┬───╯  (broken→)  │
   │           │ slope           │
   │  boat shed│                 │
   │      ═════╪═══ DOCK ═══►BOAT│  dock: broken → repaired (stage gate)
   └────────────────────────────┘
            S (open sea)
```

- **Player spawn / respawn:** keeper's cot inside the lighthouse base (`SPAWN_player`).
- **Cliff path** down to Gullwash Shore (`TRIG_to_shore`, west edge): walkable from
  the very start. The boat is for *offshore* destinations once the dock is mended.
- **Lighthouse:** 28 m tower. Spiral stair is a single ramp collider. Lamp room has
  the **chart table** (`NODE_chart`) and lamp housing (`NODE_lamp`) — both
  interactables. Beam pivot `FX_beam_pivot` at y ≈ 27.
- **Hearth** (`NODE_hearth`) and **storage chest** (`NODE_storage`) in the square —
  within 10 m of each other so preparation is quick.
- **Forge** (`NODE_forge`): two variants, `forge_broken` / `forge_repaired`
  (state swap via `STATE_` naming).
- **Dock:** `dock_broken` (gaps you can't cross; the boat is pulled up on the
  shingle) / `dock_repaired` (boat at the end). `NODE_boat` = departure.
- **NPC marks:** `NPC_maren` (lamp room), `NPC_tib` (dock), `NPC_odile` (hearth),
  `NPC_hesk` (forge, appears at stage 1), `NPC_family` (cottage, stage 2).
- **Windows:** window meshes named `WIN_s0`, `WIN_s1`, `WIN_s2` — emissive turned
  on when stage ≥ suffix.
- Lighting: warm. Amber point lights at the hearth, lanterns along the path.

---

## Gullwash Shore — `shore`

Tutorial, safe-ish. ≈ 120 × 80 m. **Teaches:** movement, gathering, fishing, one
enemy type, a tide change.

```
   open sea (deep)                      CACHE ISLET (y 2.6)
                        ~~~~~~ sandbar (y 0.6) ~~~~~~  ◇ sealed cache
   GLOWGILL ROCKS (y 2.5)         tide pools (kelp, glass)
     ↑ fishing at high tide only
   ───────────── wet sand flats (y 0.3–1.2) ─────────────
     driftwood   scrap pile   crab flats (3–4 Brine Crabs)
   ───────────── dry beach & dunes (y 2.4–4) ────────────
     LANDING JETTY (y 3.0) ⚓  fishing spot (Silverfin)  ANCHOR_dunes
```

- **Landing:** `SPAWN_landing` on the jetty, always dry.
- **Low tide:** flats and **sandbar** exposed → walk to the cache islet (sealed
  cache needs Salvage 6 — a visible "come back later" goal; also 2 Tidestone in a
  plain crate there for everyone). Kelp beds and sea-glass beds on the flats.
- **High tide:** flats flood to wading/swim depth. Sandbar gone; islet unreachable
  except by swimming (allowed, with the current-rescue rule). **Glowgill rocks**
  fishing spot becomes active. Crabs retreat to the dunes edge (2 crabs, more
  aggressive).
- **Retreat route:** dunes ridge connects every part of the beach to the jetty
  above tide level.
- **Anchors:** `ANCHOR_dunes_w`, `ANCHOR_dunes_e`, `ANCHOR_islet`.
- **Nodes (respawn per visit):** 6 driftwood, 3 scrap piles, 4 kelp beds (low),
  3 sea-glass beds (low, Salvage 2), 1 Silverfin spot (any tide), 1 Glowgill spot
  (high, Fishing 4).
- **First tide change:** a new save's tide clock starts 1:00 into low tide, so the
  first warning fires after two minutes of play (about one minute into the first
  Gullwash trip) and the water starts rising a minute later. The tide clock only
  runs while playing, never behind the title or pause card.

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
- **Anchors:** landing, causeway, arena east, arena north.

---

## Encounter tuning targets

| Location | Enemies per visit | Expected time | Expected haul (common mats) |
|---|---|---|---|
| Shore | 3–4 crabs | 4–7 min | 18–30 |
| Wreck | ~4 crabs, 3 spitters, 3 wisps, 2 lurkers (high) | 7–10 min | 25–40 + brass |
| Beacon | 2 spitters, 2 wisps, boss | 5–8 min | boss chest |
