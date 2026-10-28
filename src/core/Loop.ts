/**
 * Fixed-step simulation (deterministic movement, collisions, tide) with
 * variable-rate rendering. `alpha` is how far we are into the next step.
 */
export class Loop {
  readonly step = 1 / 60;
  private acc = 0;
  private last = 0;
  private raf = 0;

  constructor(
    private readonly update: (dt: number) => void,
    private readonly render: (alpha: number, frameDt: number) => void,
  ) {}

  start(): void {
    this.last = performance.now();
    const frame = (now: number) => {
      // Clamp so a background tab doesn't simulate minutes at once.
      const frameDt = Math.min((now - this.last) / 1000, 0.25);
      this.last = now;
      this.acc += frameDt;
      while (this.acc >= this.step) {
        this.update(this.step);
        this.acc -= this.step;
      }
      this.render(this.acc / this.step, frameDt);
      this.raf = requestAnimationFrame(frame);
    };
    this.raf = requestAnimationFrame(frame);
  }

  stop(): void {
    cancelAnimationFrame(this.raf);
  }
}
