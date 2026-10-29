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
   (`SPAWN_`, `NODE_`, `COL_`…) instead of hard-coding positions. See
   `ART_PIPELINE.md`.
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
    Loop.ts               fixed-step update (60 Hz) + variable render
    EventBus.ts           typed pub/sub (GameEvents map)
    Input.ts              actions ↔ keys, pointer lock with a free-look fallback
    Save.ts               localStorage, schema version, migrations
    Assets.ts             glTF loading, shared models cloned by name
    math.ts               clamp, lerp, damp, smoothstep, rng
  data/                   ← all content & tuning (pure TS, no three)
    ids.ts items.ts recipes.ts skills.ts enemies.ts nodes.ts
    locations.ts lighthouse.ts quests.ts npcs.ts tide.ts balance.ts
    controls.ts           actions, default keys, rebinding rules
    presentation.ts       post, water and rain looks; shadow distance
    villagers.ts          which Polyfork character each NPC is
    pacing.ts             the pacing simulation's player and the GDD's targets
    validate.ts           integrity + reachability (softlock) checks
  state/GameState.ts      the save shape + createNewGame()
  systems/                ← pure logic (no three)
    tide.ts inventory.ts skills.ts crafting.ts progression.ts quests.ts
    economy.ts            plays the chapter on expected yields, trip by trip
  physics/StaticCollider.ts   merged BVH: capsule resolve, rays, ground height
  player/
    PlayerController.ts   movement, jump (coyote time), dash, water states, rescue
    Viewmodel.ts          first-person weapon, lantern and rod (own scene)
  world/
    Level.ts              the Level interface every location implements
    LevelLoader.ts        Blender .glb → GlbLevel (markers per ART_PIPELINE.md)
    Batch.ts              merges static scenery by material at load (draw calls)
    Heights.ts            per-level seabed and roof heights, baked from collision
    Gloom.ts              Gloom pockets: the cloud, the chill, burning off
    home/HomeLevel.ts     Lantern's Rest, laid out in code, changes with progress;
                          its buildings come from home.glb
    home/Headland.ts      the painted grass top; home/Villager.ts posed Polyfork people
    Lighthouse.ts         tower, beam rig, the distant beam seen from away
    Water.ts              Gerstner sea: depth colour, foam, glints, ripples, rain rings
    Sky.ts                sky dome, lights, fog, the environment map
    TideMaterial.ts       flood-warning glow for TIDE_ materials
  enemies/                Enemy base + BrineCrab, DrownedSpitter, LanternWisp,
                          TideLurker, WreckGuardian; procedural part animation
  combat/Projectiles.ts   pooled bolts, orbs and mortars
  gather/                 GatherNode (hold to gather), Fishing (cast, bite, catch)
  fx/                     Effects (particles, rings, cones), Loot (sparkles, pickups),
                          Post (bloom), Rain (GPU streaks), sprite (soft dot)
  audio/Sfx.ts            synthesised sounds, HRTF positional cues, ambience
  ui/
    Hud.ts hud.css        tide, objective, prompt, health, dash, compass, boss bar,
                          threat pips, toasts, banners, dialogue, fades
    Menus.ts menus.css    storage, stations, repairs, lighthouse, chart, journal,
                          settings, trip and defeat summaries
tests/                    vitest: systems, data/softlock, tide, exported levels,
                          the tide-trap sweep, the economy/pacing simulation
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
       │    └─ nodes (GatherNode[]), encounters (Encounters), buoys, triggers
       ├─ player, viewmodel, fishing, projectiles, effects, loot
       └─ beams: home lighthouse, the distant one, the relit beacon

update(dt = 1/60), while playing:
  tide clock → buffs → player → encounters → projectiles → loot → nodes
  → triggers → interaction (focus, gather, fish, talk, stations) → combat → food
render():
  camera → water/rain/gloom/tide uniforms → composer:
    world pass (HDR, MSAA) → bloom → viewmodel pass (after bloom, so the
    lantern doesn't flood the screen) → tone mapping + sRGB → HUD
```

Draw calls stay under 300 everywhere: `batchStatic()` merges every static mesh
that shares a material (the originals stay, hidden, so collision and focus rays
still see them), `collapseMaterials()` folds a rigid model's per-material split
into one vertex-coloured mesh, and only things near the player cast shadows.

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
