import * as THREE from "three";

// Every sound is synthesised with WebAudio, so the game needs no audio files
// yet. Enemy cues are positional (HRTF) because in first person you have to
// hear what's behind you. Real recordings can replace any of these later.

type Ambience = "home" | "shore" | "wreck" | "beacon" | "none";

export class Sfx {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private noiseBuf: AudioBuffer | null = null;
  private ambience: { kind: Ambience; nodes: AudioNode[]; gain: GainNode } | null = null;
  private volume = 0.8;
  private readonly fwd = new THREE.Vector3();

  /** Must be called from a user gesture (the start click). */
  resume(): void {
    if (!this.ctx) {
      this.ctx = new AudioContext();
      this.master = this.ctx.createGain();
      this.master.gain.value = this.volume;
      this.master.connect(this.ctx.destination);
      const len = this.ctx.sampleRate * 2;
      this.noiseBuf = this.ctx.createBuffer(1, len, this.ctx.sampleRate);
      const d = this.noiseBuf.getChannelData(0);
      for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    }
    void this.ctx.resume();
  }

  setVolume(v: number): void {
    this.volume = v;
    if (this.master) this.master.gain.value = v;
  }

  setListener(pos: THREE.Vector3, camera: THREE.Camera): void {
    const l = this.ctx?.listener;
    if (!l || !l.positionX) return;
    camera.getWorldDirection(this.fwd);
    const t = this.ctx!.currentTime;
    l.positionX.setValueAtTime(pos.x, t);
    l.positionY.setValueAtTime(pos.y, t);
    l.positionZ.setValueAtTime(pos.z, t);
    l.forwardX.setValueAtTime(this.fwd.x, t);
    l.forwardY.setValueAtTime(this.fwd.y, t);
    l.forwardZ.setValueAtTime(this.fwd.z, t);
    l.upX.setValueAtTime(0, t);
    l.upY.setValueAtTime(1, t);
    l.upZ.setValueAtTime(0, t);
  }

  private out(at?: THREE.Vector3): AudioNode | null {
    if (!this.ctx || !this.master) return null;
    if (!at) return this.master;
    const p = this.ctx.createPanner();
    p.panningModel = "HRTF";
    p.distanceModel = "inverse";
    p.refDistance = 4;
    p.rolloffFactor = 1.1;
    p.positionX.value = at.x;
    p.positionY.value = at.y;
    p.positionZ.value = at.z;
    p.connect(this.master);
    return p;
  }

  private tone(o: { type?: OscillatorType; f0: number; f1?: number; dur: number; gain: number; attack?: number; at?: THREE.Vector3; delay?: number; lowpass?: number }): void {
    const dest = this.out(o.at);
    if (!dest || !this.ctx) return;
    const t = this.ctx.currentTime + (o.delay ?? 0);
    const osc = this.ctx.createOscillator();
    osc.type = o.type ?? "sine";
    osc.frequency.setValueAtTime(o.f0, t);
    if (o.f1) osc.frequency.exponentialRampToValueAtTime(Math.max(1, o.f1), t + o.dur);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(o.gain, t + (o.attack ?? 0.005));
    g.gain.exponentialRampToValueAtTime(0.0001, t + o.dur);
    let node: AudioNode = osc;
    if (o.lowpass) {
      const f = this.ctx.createBiquadFilter();
      f.type = "lowpass";
      f.frequency.value = o.lowpass;
      osc.connect(f);
      node = f;
    }
    node.connect(g).connect(dest);
    osc.start(t);
    osc.stop(t + o.dur + 0.05);
  }

  private noise(o: { dur: number; gain: number; freq: number; type?: BiquadFilterType; q?: number; at?: THREE.Vector3; attack?: number; sweepTo?: number; delay?: number }): void {
    const dest = this.out(o.at);
    if (!dest || !this.ctx || !this.noiseBuf) return;
    const t = this.ctx.currentTime + (o.delay ?? 0);
    const src = this.ctx.createBufferSource();
    src.buffer = this.noiseBuf;
    src.loop = true;
    const f = this.ctx.createBiquadFilter();
    f.type = o.type ?? "bandpass";
    f.frequency.setValueAtTime(o.freq, t);
    if (o.sweepTo) f.frequency.exponentialRampToValueAtTime(o.sweepTo, t + o.dur);
    f.Q.value = o.q ?? 1;
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(o.gain, t + (o.attack ?? 0.01));
    g.gain.exponentialRampToValueAtTime(0.0001, t + o.dur);
    src.connect(f).connect(g).connect(dest);
    src.start(t, Math.random());
    src.stop(t + o.dur + 0.05);
  }

  // --------------------------------------------------------------- player

  fire(): void {
    this.tone({ type: "square", f0: 880, f1: 220, dur: 0.12, gain: 0.08, lowpass: 2400 });
    this.noise({ dur: 0.08, gain: 0.12, freq: 3000, type: "highpass" });
  }
  dash(): void {
    this.noise({ dur: 0.25, gain: 0.15, freq: 600, sweepTo: 2400, q: 0.8 });
  }
  jump(): void {
    this.noise({ dur: 0.08, gain: 0.05, freq: 800, type: "lowpass" });
  }
  land(): void {
    this.noise({ dur: 0.12, gain: 0.12, freq: 300, type: "lowpass" });
  }
  hurt(): void {
    this.tone({ type: "sawtooth", f0: 220, f1: 90, dur: 0.25, gain: 0.12, lowpass: 900 });
    this.noise({ dur: 0.15, gain: 0.15, freq: 500, type: "lowpass" });
  }
  eat(): void {
    for (let i = 0; i < 3; i++) this.noise({ dur: 0.06, gain: 0.06, freq: 1200 + i * 200, delay: i * 0.12 });
  }
  heal(): void {
    this.tone({ f0: 523, dur: 0.3, gain: 0.05 });
    this.tone({ f0: 784, dur: 0.4, gain: 0.04, delay: 0.08 });
  }

  // ---------------------------------------------------------------- combat

  hitEnemy(at: THREE.Vector3, weak = false): void {
    this.tone({ type: "triangle", f0: weak ? 1400 : 900, f1: 300, dur: 0.08, gain: 0.12, at });
    this.noise({ dur: 0.06, gain: 0.1, freq: 2500, at });
  }
  enemyDie(at: THREE.Vector3): void {
    this.noise({ dur: 0.5, gain: 0.2, freq: 400, sweepTo: 120, at });
    this.tone({ type: "sine", f0: 300, f1: 60, dur: 0.5, gain: 0.08, at });
  }
  /** Rising tone during an attack windup: the most important cue in combat. */
  windup(at: THREE.Vector3, dur: number, pitch = 1): void {
    this.tone({ type: "triangle", f0: 180 * pitch, f1: 520 * pitch, dur, gain: 0.09, attack: dur * 0.6, at });
  }
  orb(at: THREE.Vector3): void {
    this.tone({ type: "sine", f0: 320, f1: 160, dur: 0.3, gain: 0.08, at });
    this.noise({ dur: 0.25, gain: 0.08, freq: 700, at });
  }
  impact(at: THREE.Vector3): void {
    this.noise({ dur: 0.1, gain: 0.08, freq: 1800, at });
  }
  crabClick(at: THREE.Vector3): void {
    for (let i = 0; i < 2; i++) this.noise({ dur: 0.03, gain: 0.12, freq: 3500, q: 6, at, delay: i * 0.07 });
  }
  blink(at: THREE.Vector3): void {
    this.tone({ type: "sine", f0: 1200, f1: 2400, dur: 0.2, gain: 0.06, at });
  }
  bite(at: THREE.Vector3): void {
    this.noise({ dur: 0.2, gain: 0.25, freq: 250, type: "lowpass", at });
    this.tone({ type: "square", f0: 90, f1: 50, dur: 0.2, gain: 0.08, at });
  }
  bubbles(at: THREE.Vector3): void {
    for (let i = 0; i < 4; i++) this.tone({ f0: 400 + Math.random() * 500, f1: 900, dur: 0.06, gain: 0.03, at, delay: i * 0.08 });
  }
  roar(at: THREE.Vector3): void {
    this.tone({ type: "sawtooth", f0: 70, f1: 40, dur: 1.4, gain: 0.25, attack: 0.3, at, lowpass: 400 });
    this.noise({ dur: 1.4, gain: 0.25, freq: 200, type: "lowpass", attack: 0.3, at });
  }
  boom(at: THREE.Vector3): void {
    this.noise({ dur: 0.6, gain: 0.3, freq: 180, type: "lowpass", at });
    this.tone({ type: "sine", f0: 90, f1: 35, dur: 0.6, gain: 0.2, at });
  }
  chain(at: THREE.Vector3): void {
    for (let i = 0; i < 6; i++) this.noise({ dur: 0.05, gain: 0.08, freq: 2800 + Math.random() * 1500, q: 5, at, delay: i * 0.06 });
  }

  // ------------------------------------------------------------- world, ui

  splash(at?: THREE.Vector3): void {
    this.noise({ dur: 0.35, gain: 0.15, freq: 1400, sweepTo: 500, at });
  }
  gather(): void {
    this.noise({ dur: 0.07, gain: 0.08, freq: 1500 });
  }
  pickup(): void {
    this.tone({ f0: 988, dur: 0.12, gain: 0.05 });
    this.tone({ f0: 1319, dur: 0.18, gain: 0.04, delay: 0.06 });
  }
  levelUp(): void {
    [523, 659, 784, 1047].forEach((f, i) => this.tone({ type: "triangle", f0: f, dur: 0.35, gain: 0.07, delay: i * 0.09 }));
  }
  craft(): void {
    this.tone({ type: "square", f0: 660, f1: 640, dur: 0.06, gain: 0.05, lowpass: 3000 });
    this.tone({ type: "square", f0: 660, f1: 640, dur: 0.06, gain: 0.05, lowpass: 3000, delay: 0.14 });
    this.tone({ f0: 880, dur: 0.3, gain: 0.05, delay: 0.26 });
  }
  upgrade(): void {
    [392, 523, 659, 784, 1047].forEach((f, i) => this.tone({ type: "triangle", f0: f, dur: 0.9, gain: 0.07, delay: i * 0.16, attack: 0.05 }));
  }
  horn(): void {
    this.tone({ type: "sawtooth", f0: 98, dur: 2.2, gain: 0.12, attack: 0.4, lowpass: 600 });
    this.tone({ type: "sawtooth", f0: 147, dur: 2.2, gain: 0.07, attack: 0.4, lowpass: 600 });
  }
  ui(): void {
    this.tone({ f0: 660, dur: 0.05, gain: 0.03 });
  }
  denied(): void {
    this.tone({ type: "square", f0: 160, dur: 0.12, gain: 0.04, lowpass: 800 });
  }
  fishBite(): void {
    this.splash();
    this.tone({ f0: 1200, f1: 900, dur: 0.15, gain: 0.06 });
  }

  /** Looping background bed: surf and wind everywhere, a hearth at home. */
  setAmbience(kind: Ambience): void {
    if (!this.ctx || !this.master || !this.noiseBuf) return;
    if (this.ambience?.kind === kind) return;
    const now = this.ctx.currentTime;
    if (this.ambience) {
      const old = this.ambience;
      old.gain.gain.setTargetAtTime(0, now, 0.6);
      setTimeout(() => old.nodes.forEach((n) => n.disconnect()), 3000);
    }
    if (kind === "none") {
      this.ambience = null;
      return;
    }
    const gain = this.ctx.createGain();
    gain.gain.value = 0;
    gain.gain.setTargetAtTime(1, now, 1.2);
    gain.connect(this.master);
    const nodes: AudioNode[] = [gain];
    const bed = (freq: number, type: BiquadFilterType, level: number, lfoHz: number) => {
      const src = this.ctx!.createBufferSource();
      src.buffer = this.noiseBuf;
      src.loop = true;
      const f = this.ctx!.createBiquadFilter();
      f.type = type;
      f.frequency.value = freq;
      const g = this.ctx!.createGain();
      g.gain.value = level;
      const lfo = this.ctx!.createOscillator();
      lfo.frequency.value = lfoHz;
      const lfoGain = this.ctx!.createGain();
      lfoGain.gain.value = level * 0.7;
      lfo.connect(lfoGain).connect(g.gain);
      src.connect(f).connect(g).connect(gain);
      src.start(0, Math.random() * 2);
      lfo.start();
      nodes.push(src, f, g, lfo, lfoGain);
    };
    bed(500, "lowpass", 0.06, 0.09); // surf
    bed(1600, "bandpass", 0.015, 0.05); // wind
    if (kind === "home") bed(2500, "highpass", 0.008, 7); // hearth crackle
    if (kind === "wreck") bed(140, "lowpass", 0.05, 0.03); // hull groan
    this.ambience = { kind, nodes, gain };
  }
}
