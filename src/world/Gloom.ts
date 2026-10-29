import * as THREE from "three";
import { FX_COLORS } from "../fx/Effects";
import { softDot } from "../fx/sprite";

// A Gloom pocket: a patch of the sea's darkness hanging over the ground, soft
// and slowly turning, with sea-green motes inside. It shrouds whatever it sits
// on until the Lantern Flare burns it away (then it stays gone until you next
// visit). Placed in Blender as GLOOM_<n> empties with a `radius` property.

const SMOKE = 90;
const MOTES = 26;
const BURN_TIME = 1.3;

const vertexShader = /* glsl */ `
uniform float uTime;
uniform float uBurn;
uniform float uScale;
attribute vec4 orbit;
attribute float size;
attribute float shade;
varying float vAlpha;
varying float vShade;
#include <fog_pars_vertex>
void main() {
  // orbit: radius, angle, height, spin speed. The cloud turns slowly and breathes.
  float a = orbit.y + uTime * orbit.w;
  float r = orbit.x * (1.0 + uBurn * 1.8);
  // Each wisp drifts up a little and thins out, then sinks back and thickens: the cloud breathes.
  float breath = 0.5 + 0.5 * sin(uTime * 0.45 + orbit.y * 5.0);
  vec3 p = vec3(cos(a) * r, orbit.z + breath * 0.35 + uBurn * 1.5, sin(a) * r);
  vec4 mvPosition = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mvPosition;
  float dist = -mvPosition.z;
  // Puffs right in front of the camera fade (and shrink to nothing) so standing inside costs no fill.
  float near = smoothstep(0.8, 2.6, dist);
  vAlpha = near * (1.0 - uBurn) * (0.45 + 0.55 * (1.0 - breath));
  vShade = shade;
  gl_PointSize = min(size * uScale / max(dist, 0.1), uScale * 0.45) * step(0.01, vAlpha);
  #include <fog_vertex>
}
`;

const fragmentShader = /* glsl */ `
uniform sampler2D uMap;
uniform vec3 uColor;
uniform float uOpacity;
varying float vAlpha;
varying float vShade;
#include <fog_pars_fragment>
void main() {
  float a = texture2D(uMap, gl_PointCoord).a * uOpacity * vAlpha;
  if (a < 0.004) discard;
  // A faint sea-green light deep in the darker wisps: something lives in there.
  vec3 c = mix(uColor * vShade, vec3(0.05, 0.32, 0.22), 0.25 * (1.0 - vShade));
  gl_FragColor = vec4(c, a);
  #include <fog_fragment>
}
`;

export class GloomPocket {
  readonly root = new THREE.Group();
  /** 0 = thick, rising to 1 as a Flare burns it off. */
  burn = 0;
  private burning = false;
  private readonly smoke: THREE.Points;
  private readonly motes: THREE.Points;
  private readonly uniforms: Record<string, THREE.IUniform>;
  private readonly moteMat: THREE.PointsMaterial;

  constructor(
    readonly center: THREE.Vector3,
    readonly radius: number,
  ) {
    this.root.position.copy(center);
    const orbit = new Float32Array(SMOKE * 4);
    const size = new Float32Array(SMOKE);
    const shade = new Float32Array(SMOKE);
    for (let i = 0; i < SMOKE; i++) {
      // Low and dense in the middle, thin and ragged at the edge, like mist settling into a hollow.
      const k = Math.sqrt(Math.random());
      const r = radius * k * 0.95;
      const lift = 0.15 + Math.random() * radius * 0.38 * (1 - k * 0.6);
      orbit.set([r, Math.random() * Math.PI * 2, lift, (Math.random() < 0.5 ? -1 : 1) * (0.04 + Math.random() * 0.1)], i * 4);
      size[i] = radius * (0.45 + Math.random() * 0.75) * (1.15 - k * 0.4);
      shade[i] = 0.55 + Math.random() * 0.9;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(SMOKE * 3), 3));
    geo.setAttribute("orbit", new THREE.BufferAttribute(orbit, 4));
    geo.setAttribute("size", new THREE.BufferAttribute(size, 1));
    geo.setAttribute("shade", new THREE.BufferAttribute(shade, 1));
    this.uniforms = THREE.UniformsUtils.merge([
      THREE.UniformsLib.fog,
      {
        uTime: { value: 0 },
        uBurn: { value: 0 },
        uScale: { value: 400 },
        uColor: { value: new THREE.Color(0x132028) },
        uOpacity: { value: 0.3 },
      },
    ]);
    this.uniforms.uMap = { value: softDot() };
    this.smoke = new THREE.Points(
      geo,
      new THREE.ShaderMaterial({ uniforms: this.uniforms, vertexShader, fragmentShader, transparent: true, depthWrite: false, fog: true }),
    );
    this.smoke.frustumCulled = false;
    this.smoke.renderOrder = 1;

    const mp = new Float32Array(MOTES * 3);
    for (let i = 0; i < MOTES; i++) {
      const a = Math.random() * Math.PI * 2;
      const r = Math.sqrt(Math.random()) * radius * 0.8;
      mp.set([Math.cos(a) * r, 0.3 + Math.random() * radius * 0.6, Math.sin(a) * r], i * 3);
    }
    const mg = new THREE.BufferGeometry();
    mg.setAttribute("position", new THREE.BufferAttribute(mp, 3));
    this.moteMat = new THREE.PointsMaterial({ color: FX_COLORS.seaGreen, map: softDot(), size: 0.14, transparent: true, opacity: 0.9, depthWrite: false, blending: THREE.AdditiveBlending });
    this.motes = new THREE.Points(mg, this.moteMat);
    this.root.add(this.smoke, this.motes);
  }

  /** Still there to shroud things and chill you. */
  get active(): boolean {
    return !this.burning;
  }

  /** 0..1: how far inside you are (1 at the heart). */
  depthAt(p: THREE.Vector3): number {
    if (!this.active) return 0;
    const dx = p.x - this.center.x;
    const dz = p.z - this.center.z;
    const dy = p.y - this.center.y;
    if (dy < -2 || dy > this.radius + 2) return 0;
    return THREE.MathUtils.clamp(1 - Math.hypot(dx, dz) / this.radius, 0, 1);
  }

  covers(p: THREE.Vector3): boolean {
    return this.active && Math.hypot(p.x - this.center.x, p.z - this.center.z) < this.radius && Math.abs(p.y - this.center.y) < this.radius + 2;
  }

  /** Starts burning off; true if it was still there. */
  dispel(): boolean {
    if (this.burning) return false;
    this.burning = true;
    return true;
  }

  update(dt: number, time: number, viewportHeight: number): void {
    if (this.burning) this.burn = Math.min(1, this.burn + dt / BURN_TIME);
    this.uniforms.uTime!.value = time;
    this.uniforms.uBurn!.value = this.burn;
    // Point sizes are in pixels: scale with the screen so the cloud looks the same at any size.
    this.uniforms.uScale!.value = viewportHeight;
    this.moteMat.opacity = 0.9 * (1 - this.burn);
    this.motes.rotation.y = time * 0.15;
    this.motes.position.y = Math.sin(time * 0.9) * 0.1 + this.burn * 1.5;
    this.root.visible = this.burn < 1;
  }

  dispose(): void {
    this.root.removeFromParent();
    this.smoke.geometry.dispose();
    (this.smoke.material as THREE.Material).dispose();
    this.motes.geometry.dispose();
    this.moteMat.dispose();
  }
}
