# Architecture

TypeScript (`strict`), Three.js, Vite. No backend, no framework for the HUD (plain
DOM + CSS). Only add a dependency when it clearly earns its place.

## Principles

1. **Game logic is pure and testable.** Tide, inventory, skills, crafting,
   progression, death rules and save migration take plain data in and return plain
   data out. They never import `three`. Vitest covers them.
2. **Content is data.** Items, recipes, enemies, nodes, stages, quests and tuning
   live in `src/data/*.ts` as typed `const` tables. `validateData()` checks
   references and progression reachability on every test run and in dev at boot.
3. **Levels come from Blender.** The game reads named objects in each `.glb`
   (`SPAWN_`, `NODE_`, `COL_`, home's `PLOT_` and `FX_drift_`…) instead of
   hard-coding positions, home included. See `ART_PIPELINE.md`.
4. **Systems talk through the event bus**, not by reaching into each other.
   (`bus.emit("skill:levelUp", …)` → HUD toast, audio sting, quest check.)
5. **One `GameState`** object is the whole save. Runtime-only objects (meshes,
   enemies) are rebuilt from it.

## Folder layout

```
src/
  main.ts                 boot: finds #app and #hud, starts the Game
  game/
    Game.ts               owns renderer, scene, systems and the current level;
                          modes (title, playing, paused, menu, travel), travel,
                          interaction, combat, food, death, the chapter ending
    Context.ts            GameContext: what gameplay modules may reach
    Encounters.ts         spawns a level's enemies per tide, ambushes, boss lookup
  core/
    Loop.ts               semi-fixed update (equal steps of at most 1/60 s that
                          add up to the frame) + one render per frame
    EventBus.ts           typed pub/sub (GameEvents map)
    Input.ts              actions ↔ keys, pointer lock with a free-look fallback
    Save.ts               localStorage, schema version, migrations
    Assets.ts             glTF loading, shared models cloned by name
    math.ts               clamp, lerp, damp, smoothstep, rng
  data/                   ← all content & tuning (pure TS, no three)
    ids.ts items.ts recipes.ts skills.ts enemies.ts nodes.ts
    locations.ts lighthouse.ts quests.ts npcs.ts tide.ts balance.ts
    controls.ts           actions, default keys, rebinding rules
    presentation.ts       post, water and rain looks; shadow distance; the
                          adaptive resolution's thresholds (PERF)
    story.ts              the prologue cards and the chapter's aim and creed
    scenery.ts            which horizon pieces stand where, per location
    wildlife.ts           gulls: flock sizes, flight, how shy they are
    chart.ts              the journal's sea chart: coast, islands, the drowned
                          town, dead lights, routes, soundings
    villagers.ts          which Polyfork character each NPC is
    salvage.ts            the cove: flotsam kinds, the drift by tide, the hook,
                          the beach and the net while you're away
    decor.ts              build mode's pieces: cost, footprint, solid, lit
    pacing.ts             the pacing simulation's player and the GDD's targets
    validate.ts           integrity + reachability (softlock) checks
  state/GameState.ts      the save shape + createNewGame()
  systems/                ← pure logic (no three)
    tide.ts inventory.ts skills.ts crafting.ts progression.ts quests.ts
    salvage.ts            drift rolls, the wreck field's pieces per tide, what
                          drifts in while you're away, hook stats by gear and skill
    building.ts           a plot's partial delivery (satchel and chest), progress
    decor.ts              where a piece may stand, its cost and its refund
    economy.ts            plays the chapter on expected yields, trip by trip
    guide.ts              where the materials you still need can be found now
    resolution.ts         the auto resolution: steps down on slow frames, and
                          keeps a step only if frames really got quicker
  physics/StaticCollider.ts   merged BVH: capsule resolve, rays, ground height
  player/
    PlayerController.ts   movement, jump (coyote time), dash, water states, rescue
    Viewmodel.ts          first-person weapon (the hook's reel and grapnel on it),
                          lantern and rod (own scene)
  world/
    Level.ts              the Level interface every location implements
    LevelLoader.ts        Blender .glb → GlbLevel (markers per ART_PIPELINE.md)
    Batch.ts              merges static scenery by material at load, and home's
                          buildings once they stand; instanced props' parts (draw calls)
    Heights.ts            per-level seabed and roof heights, baked from collision
    Gloom.ts              Gloom pockets: the cloud, the chill, burning off
    home/HomeLevel.ts     Lantern's Rest: locations/home.glb (a GlbLevel) with
                          progression layered over it: plots, people, boats, fires
    home/Plot.ts          a plot's ruin, its building rising behind scaffolding
                          (a clipping plane; the jetty grows a deck), its board
    home/Decor.ts         placed decor, instanced per kind; build mode's ghost
    home/Villager.ts      posed Polyfork people
    Lighthouse.ts         tower, beam rig, the distant beam seen from away
    Water.ts              Gerstner sea: depth colour, foam, glints, ripples, rain rings
    Sky.ts                sky dome, lights, fog, the environment map
    TideMaterial.ts       flood-warning glow for TIDE_ materials
    Horizon.ts            the drowned world on the horizon, one static batch
    Gulls.ts              wheeling flocks and shy perched gulls, all instanced
  enemies/                Enemy base + BrineCrab, DrownedSpitter, LanternWisp,
                          TideLurker, WreckGuardian; procedural part animation
  combat/Projectiles.ts   pooled bolts, orbs and mortars
  gather/                 Hook (throw, reel, yank; the line), Flotsam (the drift:
                          lanes, sway, beaching, pickup), Wreckage (pieces off
                          per pull, drawn merged, restock), GatherNode (crates, key items,
                          fishing spots), Fishing (cast, bite, catch)
  fx/                     Effects (particles, rings, cones), Loot (sparkles, pickups),
                          Post (bloom), Rain (GPU streaks), sprite (soft dot)
  audio/Sfx.ts            synthesised sounds, HRTF positional cues, ambience
  ui/
    Hud.ts hud.css        tide, objective, prompt, health, dash, compass, boss bar,
                          threat pips, the hook's reticle, build mode's hotbar,
                          toasts, banners, dialogue, fades
    Menus.ts menus.css    storage, stations, plots, lighthouse, chart, journal,
                          settings, trip and defeat summaries
    chart.ts              draws the sea chart as one SVG
tests/                    vitest: systems, data/softlock, tide, exported levels,
                          the tide-trap sweep (home's plots in every state),
                          building, decor, the economy/pacing simulation
tools/
  build-art.ts            runs tools/blender/build/*.py in headless Blender
  export-models.ts        exports hand-edited .blend files
  blender-path.ts         finds Blender (BLENDER, PATH, Steam, blender.org)
  blender/                Python (Blender's API requires it): lib/kit.py, build/*.py
art/blender/              .blend sources (not shipped)
public/assets/models/     exported .glb (shipped)
```

## Runtime flow

```
main.ts
  └─ Game  (implements GameContext)
       ├─ state: GameState            loaded from Save or createNewGame()
       ├─ bus, input, hud, menus, sfx, assets
       ├─ level: HomeLevel | GlbLevel  swapped by enter() during a travel fade
       │    └─ nodes (GatherNode[]), wrecks (Wreck[]), flotsam (home), encounters,
       │       buoys, triggers
       ├─ player, viewmodel, hook, fishing, projectiles, effects, loot
       └─ beams: home lighthouse, the distant one, the relit beacon

update(dt ≤ 1/60, several per frame on a slow one), while playing:
  tide clock → buffs → player → encounters → projectiles → loot → nodes
  → wrecks, flotsam → the hook (or build mode, at home) → triggers
  → interaction (focus, open, fish, talk, stations, plots) → combat → food
render():
  camera → water/rain/gloom/tide uniforms → composer:
    world pass (HDR, MSAA) → bloom → viewmodel pass (after bloom, so the
    lantern doesn't flood the screen) → tone mapping + sRGB → HUD
```

Frame time: villagers share one skeleton per person and merge parts that share
one (each skeleton is a bone texture uploaded every frame, and those uploads
stall the GPU), every shader a place can show is compiled during the travel fade
(`prewarm()`), and on a GPU-bound screen the resolution steps down until the
frame rate holds, then creeps back up (`src/systems/resolution.ts`, tuned by
`PERF.resolution`; Settings can fix it). A step that doesn't make frames quicker
(a 50 Hz screen, a 30 fps cap, a busy CPU) is undone.

Draw calls stay under 300 everywhere: `batchStatic()` merges every static mesh
alike in finish, colours baked into vertex colours (the originals stay, hidden,
so collision and focus rays still see them), `collapseMaterials()` folds a
rigid model's per-material split into one vertex-coloured mesh, and only things
near the player cast shadows (creatures, loot, what floats). A place's wrecks
built in pieces draw merged (`mergePieces()`): each wreck's triangles lie
together, its pieces first in the order they go, and tearing pieces off
collapses theirs to a point in the index (a restock writes them back). Home
merges its finished buildings by material each time one stands
(`batchMeshes()`), and instanced props (decor, drift) draw their rough plain
materials as one part (`instanceParts()`). The Meridian peaks at about 275 (low
water, the ambush, all thirteen enemies about you); with every plot built, 50
decor pieces, the drift in and both families home, the Rest is at about
175–200 (a ruin and its board cost more than a finished building: with two
plots in ruins it was at about 275 before scenery merged by finish).

## Key decisions

| Decision | Choice | Why |
|---|---|---|
| Physics | **No physics engine.** Kinematic capsule vs static BVH (`three-mesh-bvh`) | Character controllers are easier to make feel good by hand; no rigid bodies needed |
| Projectiles | Pooled spheres, sphere-vs-capsule / sphere-vs-BVH | Cheap, reliable, readable |
| UI | DOM overlay | Text, layout and accessibility for free; Three only renders the world |
| Save | `localStorage` JSON, `version` + migrations | Simple, inspectable |
| Tide | Deterministic clock from `state.tide.elapsed` | Same result after save/load; easy to test |
| Assets | glTF binary (`.glb`) with Draco off by default | Fast iteration; turn on compression in M7 if size matters |
| Randomness | Seeded RNG for loot rolls | Reproducible tests |

## Events (initial)

See `src/core/EventBus.ts` → `GameEvents`. Add events there; the type system will
then check every emit and subscriber.
