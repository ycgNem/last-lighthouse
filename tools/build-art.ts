// Rebuilds the game's art from the scripts in tools/blender/build. Each script
// writes its .blend (art/blender/...) and exports the .glb the game loads.
//   npm run build:art                 everything, in dependency order
//   npm run build:art -- wreck beacon only those
// Blender runs headless, one script at a time, a second or two each.

import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { findBlender } from "./blender-path.ts";

const root = resolve(import.meta.dirname, "..");
// Home and the locations append props from props.blend, so props comes first.
const ORDER = ["props", "enemies", "viewmodels", "home", "scenery", "shore", "wreck", "beacon"];

const blender = findBlender();
if (!blender) {
  console.error("Couldn't find Blender. Install it, or set BLENDER to blender.exe's full path.");
  process.exit(1);
}

const asked = process.argv.slice(2).filter((a) => !a.startsWith("-"));
const names = asked.length ? asked : ORDER;
let failed = 0;
for (const name of names) {
  const script = join(root, "tools", "blender", "build", `${name}.py`);
  if (!existsSync(script)) {
    console.error(`✗ ${name}: no tools/blender/build/${name}.py`);
    failed++;
    continue;
  }
  const t0 = Date.now();
  const res = spawnSync(blender, ["-b", "--factory-startup", "--python-exit-code", "1", "--python", script], { encoding: "utf8" });
  const log = `${res.stdout ?? ""}${res.stderr ?? ""}`;
  const ok = res.status === 0 && !/Traceback|Error:/.test(log);
  for (const line of log.split(/\r?\n/)) if (/^\[(build|export|check)\]|Traceback|Error/.test(line)) console.log(`  ${line}`);
  console.log(`${ok ? "✓" : "✗"} ${name} (${((Date.now() - t0) / 1000).toFixed(1)} s)`);
  if (!ok) {
    failed++;
    if (!/Traceback/.test(log)) console.log(log.slice(-2000));
  }
}
process.exit(failed ? 1 : 0);
