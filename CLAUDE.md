# The Last Lighthouse

First-person action RPG (Three.js + TypeScript strict + Vite) about restoring a
lighthouse settlement in a drowned world. Art is made in Blender.

## Read first

- `docs/GDD.md` — what the game is and why. Design decisions live here.
- `docs/MILESTONES.md` — **the build order**. Work on the current milestone only;
  tick boxes as you finish them.
- `docs/LEVELS.md` — layouts, tide heights, encounter placement.
- `docs/ARCHITECTURE.md` — code structure and rules.
- `docs/ART_PIPELINE.md` — Blender naming conventions the game depends on.

## Commands

| | |
|---|---|
| `npm run dev` | dev server at http://localhost:5173 |
| `npm run check` | typecheck |
| `npm test` | unit tests + content validation (softlock check) |
| `npm run build` | typecheck + production build |
| `npm run build:art` | regenerate the art from `tools/blender/build/*.py` (headless Blender; finds Steam/blender.org installs or `BLENDER=<path>`) |
| `npm run export:models` | export hand-edited `art/blender/**/*.blend` → `public/assets/models/**/*.glb` |

Run `npm run check && npm test` before calling any change done.

Pushing to `main` deploys to https://ycgnem.github.io/last-lighthouse/ (the
workflow runs the tests and the build first). Asset URLs must go through
`import.meta.env.BASE_URL`, because the site lives under a subpath.

## Rules

- TypeScript only, `strict` on. The single exception is `tools/blender/**/*.py`
  (Blender's API is Python).
- `three` and `@types/three` are pinned to matching versions — bump them together.
- **Tuning and content go in `src/data/`**, never as magic numbers in systems.
  After changing data, `npm test` must still pass (it proves Chapter 1 is
  finishable from guaranteed drops).
- `src/systems/` and `src/data/` never import `three` — keep them testable in Node.
- Fairness rules from GDD §6 are hard requirements: no instant deaths, no
  permanent tide traps, landing points reachable at both tides, enemy windups
  ≥ 0.4 s (the validator checks the last one).
- No backend, multiplayer, currencies, hunger, durability or fuel chores.
- Level layout comes from Blender markers (`SPAWN_`, `NODE_`, `COL_`…), not
  hard-coded positions. The exception is home (`src/world/home/HomeLevel.ts`),
  built in code because progression changes so much of it.
- Use Blender headless only (`blender -b`, what `npm run build:art` does). Never
  drive a live Blender window: the user may have one open for another project.
- After changing a level script, `npm test` checks its markers and its node/enemy
  counts against `src/data/locations.ts`, and sweeps it for tide traps and
  unreachable nodes (`tests/tide-sweep.test.ts`). After changing yields or costs,
  `tests/economy.test.ts` checks the chapter's pacing.

## Dev helpers

In the dev build: **T** skips the tide forward 60 s. Console (`__ll`): `give("timber", 20)`,
`gear("rod_reinforced")`, `xp("combat", 500)`, `stage(1)`, `flag("guardian_defeated")`,
`project("dock")`, `tide(120)`, `go("wreck")`, `tp(x, y, z)`, `where()`, `heal()`,
`killAll()`, `reset()`, `economy()` (prints the pacing simulation's trips). `__ll.game` is the live `Game`.

The Claude app's browser pane doesn't fire animation frames while hidden. To test
there, drive the loop yourself: call `__ll.game.update(1 / 60)` in a loop, then
`__ll.game.render(1 / 60)`.
