import { describe, expect, it } from "vitest";
import { simulateProgression, validateIntegrity, validateData } from "../src/data/validate";

describe("content data", () => {
  it("has no integrity errors", () => {
    expect(validateIntegrity()).toEqual([]);
  });

  it("can finish Chapter 1 from guaranteed sources only (no softlock, no rare-drop gates)", () => {
    const report = simulateProgression();
    expect(report.blockedBy).toEqual([]);
    expect(report.finalStage).toBe(3);
  });

  it("passes full validation", () => {
    expect(validateData()).toEqual([]);
  });
});
