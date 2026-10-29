// Look-and-feel tuning: the post-processing, the sea and the weather.
// Colours are sRGB hex like everywhere else; the renderers convert them.

export const POST = {
  /** Applied once, at the end of the frame (ACES filmic). */
  exposure: 1.05,
  /**
   * Bloom works on the linear HDR frame, so only things brighter than white
   * glow: lamps, the beam, windup glows, bolts and orbs, sun glints on the sea.
   */
  bloom: { strength: 0.45, radius: 0.35, threshold: 1.0 },
  /** Light from the sky dome on every surface; it's what makes brass and iron read as metal. */
  environment: 0.45,
  /** The hemisphere fill drops by this much to make room for the sky light. */
  hemisphere: 0.7,
} as const;

/** Frame budget levers (M7: under 300 draw calls, render targets around 200 MB at most). */
export const PERF = {
  /**
   * Creatures and loot props only cast shadows this close to you. Beyond it the
   * shadow is a few texels anyway, and each one is another draw call.
   */
  shadowNear: 20,
  /**
   * Pixels in the frame up to which it gets 4× MSAA; above it, 2×. The frame is
   * half-float, so 4× costs about 115 MB at 1080p and over 300 MB on a 1440p or
   * retina screen, where the pixels are small enough that 2× looks much the same.
   */
  msaa4UpTo: 2_100_000,
} as const;

export interface WaveDef {
  /** Direction of travel on the XZ plane (normalised by the shader). */
  dir: readonly [number, number];
  /** Metres between crests. Keep ≥ 6 m: shorter waves alias on the mesh. */
  length: number;
  /** Crest height in metres. */
  amp: number;
  /** 0..1 Gerstner sharpness (0 = sine). The sum over waves must stay < 1. */
  steep: number;
}

export const WATER_LOOK = {
  shallow: 0x3c9a96,
  deep: 0x0d3a4c,
  foam: 0xe4f4f0,
  /** Metres of water over which the colour goes from shallow to deep. */
  depthRange: 4,
  /** Foam fringe along the shore, in metres of depth. */
  foamDepth: 0.45,
  /** Opacity in the shallows and in deep water (you see the sand through the first). */
  alpha: [0.55, 0.94] as const,
  /** Rough is matte; the sea is glossy enough for the sun to glint off every ripple. */
  roughness: 0.07,
  /** Geometric waves. Swell periods follow deep-water dispersion (speed from length). */
  waves: [
    { dir: [1.0, 0.3], length: 19, amp: 0.13, steep: 0.32 },
    { dir: [-0.35, 1.0], length: 11, amp: 0.08, steep: 0.28 },
    { dir: [0.7, -0.75], length: 7.5, amp: 0.045, steep: 0.22 },
    { dir: [-1.0, -0.15], length: 6, amp: 0.03, steep: 0.12 },
  ] satisfies readonly WaveDef[],
  /** Small ripples, per pixel only: they make the glints. */
  ripples: { scale: 1.3, strength: 0.32, speed: 0.6 },
  /** Waves die down over this depth (metres) as they reach the shore. */
  shoalDepth: 2.2,
  /** Tint while swimming (the camera's at the waterline). */
  swimTint: "rgba(18, 74, 84, 0.42)",
} as const;

export const RAIN = {
  /** Streaks at full intensity. */
  drops: 6000,
  /** The box of rain kept round the camera: width and height, metres. */
  area: 34,
  height: 22,
  /** Metres per second, and the sideways push of the wind. */
  speed: 17,
  wind: [2.2, 0.8] as const,
  /** Length and width of a streak, metres. */
  streak: 0.5,
  width: 0.012,
  color: 0xb9c8cf,
  opacity: 0.27,
  /** Showers come and go: intensity swings between these fractions of a place's base. */
  swing: [0.45, 1] as const,
  /** Seconds for a full shower cycle (two sines, so it never quite repeats). */
  period: [97, 41] as const,
} as const;
