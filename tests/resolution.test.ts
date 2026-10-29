import { describe, expect, it } from "vitest";
import { PERF } from "../src/data/presentation";
import { AutoResolution } from "../src/systems/resolution";

/** Plays `seconds` of frames whose time depends on the scale; returns the share of that time spent at full resolution. */
function play(a: AutoResolution, seconds: number, frameTime: (scale: number) => number): number {
  let full = 0;
  for (let t = 0; t < seconds; ) {
    const dt = frameTime(a.scale);
    if (a.scale === 1) full += dt;
    a.frame(dt);
    t += dt;
  }
  return full / seconds;
}

/** A GPU-bound frame: its time goes with the pixels drawn, never quicker than a 60 Hz screen. */
const gpuBound = (atFull: number) => (scale: number) => Math.max(1 / 60, atFull * scale * scale);

describe("auto resolution", () => {
  it("draws fewer pixels when the GPU is what's slow, until the frame rate holds", () => {
    const a = new AutoResolution();
    play(a, 30, gpuBound(0.024));
    expect(a.scale).toBeLessThan(1);
    expect(gpuBound(0.024)(a.scale)).toBeLessThan(PERF.resolution.slowFrame);
  });

  it("climbs back to full once the load goes", () => {
    const a = new AutoResolution();
    play(a, 20, gpuBound(0.024));
    expect(a.scale).toBeLessThan(1);
    play(a, 120, () => 1 / 60);
    expect(a.scale).toBe(1);
  });

  it("stays sharp on a 50 Hz screen and under a 30 fps cap, where fewer pixels don't help", () => {
    for (const fps of [50, 30]) {
      const a = new AutoResolution();
      // Brief trials, each undone, and further and further apart.
      expect(play(a, 180, () => 1 / fps)).toBeGreaterThan(0.95);
      expect(a.scale === 1 || a.scale === 1 - PERF.resolution.step).toBe(true);
    }
  });

  it("ignores hitches and a tab coming back from the background", () => {
    const a = new AutoResolution();
    for (let i = 0; i < 20; i++) {
      a.frame(0.25);
      play(a, 1, () => 1 / 60);
    }
    expect(a.scale).toBe(1);
  });
});
