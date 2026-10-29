import { PERF } from "../data/presentation";

// The automatic resolution (Settings → Resolution: Auto). It watches frame
// times while you play. After a run of slow frames it tries drawing fewer
// pixels, and keeps that only if frames really got quicker: a 50 Hz screen, a
// browser holding the game to 30 fps (Chrome's energy saver) or a busy CPU
// isn't helped by a blurrier picture, so those go straight back up. With room
// to spare it climbs back, half a step at a time.

const R = PERF.resolution;

export class AutoResolution {
  /** Share of the full resolution being drawn. */
  scale = 1;
  /** Smoothed frame time, s. */
  private avg = 1 / 60;
  private slow = 0;
  private quick = 0;
  /** Seconds before it may climb again after a step down that helped. */
  private hold = 0;
  private nextHold: number = R.holdAfterDrop;
  /** Seconds before it may try stepping down again after a step that didn't help. */
  private retry = 0;
  private nextRetry: number = R.retryAfter;
  private trial: { from: number; before: number; t: number } | null = null;

  /** One frame's time while playing. Returns the new scale when it changes. */
  frame(dt: number): number | null {
    // A hitch, or a tab coming back from the background: not the GPU.
    if (dt > 0.1) return null;
    this.avg += (dt - this.avg) * 0.05;
    this.hold = Math.max(0, this.hold - dt);
    this.retry = Math.max(0, this.retry - dt);
    this.slow = this.avg > R.slowFrame ? this.slow + dt : 0;
    this.quick = this.avg < R.fastFrame ? this.quick + dt : 0;
    if (this.trial) {
      this.trial.t += dt;
      if (this.trial.t < R.judge) return null;
      const { from, before } = this.trial;
      this.trial = null;
      this.slow = this.quick = 0;
      if (this.avg < before * (1 - R.gain)) {
        // It helped. Don't climb straight back into the slowdown; wait longer each time it recurs.
        this.hold = this.nextHold;
        this.nextHold = Math.min(this.nextHold * 2, R.maxHold);
        return null;
      }
      this.retry = this.nextRetry;
      this.nextRetry = Math.min(this.nextRetry * 2, R.maxHold);
      return this.set(from);
    }
    if (this.slow > R.react && this.scale > R.min && this.retry === 0) {
      this.trial = { from: this.scale, before: this.avg, t: 0 };
      this.slow = 0;
      return this.set(Math.max(R.min, this.scale - R.step));
    }
    if (this.quick > R.settle && this.hold === 0 && this.scale < 1) {
      this.quick = 0;
      return this.set(Math.min(1, this.scale + R.step / 2));
    }
    return null;
  }

  /** Carry on from this scale (the fixed one, when Settings goes back to Auto). */
  startFrom(scale: number): void {
    this.scale = scale;
    this.trial = null;
    this.slow = this.quick = 0;
  }

  private set(scale: number): number {
    this.scale = Math.round(scale * 100) / 100;
    return this.scale;
  }
}
