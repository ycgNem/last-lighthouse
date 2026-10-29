/**
 * Each frame the simulation advances by exactly the time that passed, in equal
 * steps of at most 1/60 s (so a dash can't tunnel through a wall and a slow
 * frame can't blow up the physics), and then the frame is drawn. Advancing by
 * the real frame time keeps motion smooth at any refresh rate: a fixed 60 Hz
 * step drawn on a 144 Hz screen shows the same position two or three frames
 * running, and the view judders however fast the game renders.
 */
export class Loop {
  readonly maxStep = 1 / 60;
  private last = 0;
  private raf = 0;

  constructor(
    private readonly update: (dt: number) => void,
    private readonly render: (frameDt: number) => void,
  ) {}

  start(): void {
    this.last = performance.now();
    const frame = (now: number) => {
      // Clamp so a background tab doesn't simulate minutes at once.
      const frameDt = Math.min((now - this.last) / 1000, 0.25);
      this.last = now;
      const steps = Math.max(1, Math.ceil(frameDt / this.maxStep - 1e-6));
      for (let i = 0; i < steps; i++) this.update(frameDt / steps);
      this.render(frameDt);
      this.raf = requestAnimationFrame(frame);
    };
    this.raf = requestAnimationFrame(frame);
  }

  stop(): void {
    cancelAnimationFrame(this.raf);
  }
}
