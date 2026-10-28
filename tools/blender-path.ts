// Finds a Blender executable for the build scripts: $BLENDER, then `blender`
// on PATH, then the usual install folders (Steam, blender.org installer).
// The scripts always run Blender headless (-b), so they never touch a
// Blender window you have open for something else.

import { spawnSync } from "node:child_process";
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";

function candidates(): string[] {
  const out: string[] = [];
  if (process.env.BLENDER) out.push(process.env.BLENDER);
  out.push("blender");
  if (process.platform === "win32") {
    const pf = [process.env["ProgramFiles"], process.env["ProgramFiles(x86)"]].filter((p): p is string => !!p);
    for (const base of pf) {
      out.push(join(base, "Steam", "steamapps", "common", "Blender", "blender.exe"));
      const foundation = join(base, "Blender Foundation");
      if (existsSync(foundation)) {
        // Newest version first: "Blender 5.2" sorts after "Blender 4.5".
        for (const dir of readdirSync(foundation).sort().reverse()) out.push(join(foundation, dir, "blender.exe"));
      }
    }
  } else if (process.platform === "darwin") {
    out.push("/Applications/Blender.app/Contents/MacOS/Blender");
  } else {
    out.push("/usr/bin/blender", "/snap/bin/blender", join(process.env.HOME ?? "", ".steam/steam/steamapps/common/Blender/blender"));
  }
  return out;
}

export function findBlender(): string | null {
  for (const c of candidates()) {
    if (c.includes("/") || c.includes("\\")) {
      if (existsSync(c)) return c;
    } else if (spawnSync(c, ["--version"], { stdio: "ignore" }).status === 0) return c;
  }
  return null;
}
