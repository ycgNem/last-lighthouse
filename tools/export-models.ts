// Exports every art/blender/**/*.blend to public/assets/models/**/*.glb.
// Skips files whose .glb is newer than the .blend unless --force is passed.
//   npm run export:models            (finds Blender: $BLENDER, PATH, Steam, Program Files)
//   npm run export:models -- --force

import { spawnSync } from "node:child_process";
import { existsSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { findBlender } from "./blender-path.ts";

const root = resolve(import.meta.dirname, "..");
const src = join(root, "art", "blender");
const out = join(root, "public", "assets", "models");
const script = join(root, "tools", "blender", "export_gltf.py");
const blender = findBlender() ?? "blender";
const force = process.argv.includes("--force");

function* blends(dir: string): Generator<string> {
  if (!existsSync(dir)) return;
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, entry.name);
    if (entry.isDirectory()) yield* blends(p);
    else if (entry.name.endsWith(".blend")) yield p;
  }
}

let exported = 0;
let failed = 0;
for (const file of blends(src)) {
  const target = join(out, relative(src, file)).replace(/\.blend$/, ".glb");
  if (!force && existsSync(target) && statSync(target).mtimeMs > statSync(file).mtimeMs) continue;
  console.log(`→ ${relative(root, file)}`);
  const res = spawnSync(blender, ["-b", file, "--python", script, "--", target], { stdio: "inherit" });
  if (res.status === 0) exported++;
  else {
    failed++;
    console.error(res.error ? `  could not run Blender (${res.error.message}). Set BLENDER to its path.` : `  Blender exited with ${res.status}`);
  }
}
console.log(`Exported ${exported}, failed ${failed}.`);
process.exit(failed ? 1 : 0);
