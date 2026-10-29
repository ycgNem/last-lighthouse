import * as THREE from "three";
import { RAIN } from "../data/presentation";
import { openSea, type LevelHeights } from "../world/Heights";

// Rain, entirely on the GPU: a fixed set of streaks whose positions are a
// function of time, wrapped into a box that travels with the camera. A drop
// that falls out of the bottom re-enters at the top, high above and mostly out
// of view, and streaks stop at the first surface (roofs and decks included)
// using the level's rain-floor map. Intensity just shows more or fewer of them.

const vertexShader = /* glsl */ `
uniform float uTime;
uniform vec3 uCenter;
uniform float uIntensity;
uniform float uWaterY;
uniform sampler2D uHeights;
uniform vec4 uRect;
attribute vec4 seed;
attribute vec2 corner;
varying float vFade;
varying float vAlong;
#include <fog_pars_vertex>

const float AREA = ${RAIN.area.toFixed(2)};
const float HEIGHT = ${RAIN.height.toFixed(2)};
const float SPEED = ${RAIN.speed.toFixed(2)};
const vec2 WIND = vec2(${RAIN.wind[0].toFixed(2)}, ${RAIN.wind[1].toFixed(2)});

float rainFloor(vec2 xz) {
  vec2 uv = (xz - uRect.xy) * uRect.zw;
  if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) return -100.0;
  return texture2D(uHeights, uv).g;
}

void main() {
  // seed: x, z in the box (0..1), phase (0..1), and the threshold intensity must pass.
  float fall = uTime * SPEED / HEIGHT + seed.z;
  float y01 = 1.0 - fract(fall);
  vec2 drift = WIND * (uTime + seed.z * HEIGHT / SPEED);
  vec2 xz = mod(seed.xy * AREA + drift - uCenter.xz + 0.5 * AREA, AREA) - 0.5 * AREA + uCenter.xz;
  vec3 head = vec3(xz.x, uCenter.y - HEIGHT * 0.4 + y01 * HEIGHT, xz.y);
  vec3 vel = normalize(vec3(WIND.x, -SPEED, WIND.y));

  // A camera-facing ribbon from the head back up along the velocity.
  vec3 toCam = normalize(cameraPosition - head);
  vec3 side = normalize(cross(vel, toCam)) * ${RAIN.width.toFixed(4)};
  vec3 p = head - vel * ${RAIN.streak.toFixed(3)} * corner.y + side * corner.x;
  vAlong = corner.y;

  float d = distance(head.xz, uCenter.xz);
  float shown = step(seed.w, uIntensity)
    * step(rainFloor(head.xz), head.y)
    * step(uWaterY, head.y)
    * (1.0 - smoothstep(AREA * 0.32, AREA * 0.5, d))
    * smoothstep(0.6, 2.0, distance(head, cameraPosition));
  vFade = shown;
  vec4 mvPosition = viewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mvPosition;
  // Hidden drops collapse to nothing so they cost no fill.
  if (shown <= 0.0) gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
  #include <fog_vertex>
}
`;

const fragmentShader = /* glsl */ `
uniform vec3 uColor;
uniform float uOpacity;
varying float vFade;
varying float vAlong;
#include <fog_pars_fragment>
void main() {
  // Brightest at the head, fading up the tail.
  float a = uOpacity * vFade * (1.0 - vAlong * 0.85);
  gl_FragColor = vec4(uColor, a);
  #include <fog_fragment>
}
`;

export class Rain {
  readonly mesh: THREE.Mesh;
  private readonly uniforms: Record<string, THREE.IUniform>;
  private readonly fallback = openSea();

  constructor() {
    const n = RAIN.drops;
    const seed = new Float32Array(n * 4 * 4);
    const corner = new Float32Array(n * 4 * 2);
    const index = new Uint32Array(n * 6);
    for (let i = 0; i < n; i++) {
      const s = [Math.random(), Math.random(), Math.random(), Math.random()];
      for (let v = 0; v < 4; v++) {
        seed.set(s, (i * 4 + v) * 4);
        corner.set([v % 2 === 0 ? -1 : 1, v < 2 ? 0 : 1], (i * 4 + v) * 2);
      }
      const b = i * 4;
      index.set([b, b + 2, b + 1, b + 1, b + 2, b + 3], i * 6);
    }
    const geo = new THREE.BufferGeometry();
    // Positions are made in the shader; this attribute only sets the vertex count.
    geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(n * 4 * 3), 3));
    geo.setAttribute("seed", new THREE.BufferAttribute(seed, 4));
    geo.setAttribute("corner", new THREE.BufferAttribute(corner, 2));
    geo.setIndex(new THREE.BufferAttribute(index, 1));

    this.uniforms = THREE.UniformsUtils.merge([
      THREE.UniformsLib.fog,
      {
        uTime: { value: 0 },
        uCenter: { value: new THREE.Vector3() },
        uIntensity: { value: 0 },
        uWaterY: { value: 0 },
        uHeights: { value: this.fallback.texture },
        uRect: { value: this.fallback.rect.clone() },
        uColor: { value: new THREE.Color(RAIN.color) },
        uOpacity: { value: RAIN.opacity },
      },
    ]);
    const mat = new THREE.ShaderMaterial({
      uniforms: this.uniforms,
      vertexShader,
      fragmentShader,
      transparent: true,
      depthWrite: false,
      fog: true,
      side: THREE.DoubleSide,
    });
    this.mesh = new THREE.Mesh(geo, mat);
    this.mesh.frustumCulled = false;
    this.mesh.renderOrder = 2;
    this.mesh.name = "rain";
  }

  setHeights(h: LevelHeights | null): void {
    this.uniforms.uHeights!.value = h ? h.texture : this.fallback.texture;
    (this.uniforms.uRect!.value as THREE.Vector4).copy(h ? h.rect : this.fallback.rect);
  }

  /** `intensity` 0..1: the fraction of streaks shown. */
  update(time: number, center: THREE.Vector3, intensity: number, waterY: number): void {
    this.uniforms.uTime!.value = time;
    (this.uniforms.uCenter!.value as THREE.Vector3).copy(center);
    this.uniforms.uIntensity!.value = intensity;
    this.uniforms.uWaterY!.value = waterY;
    this.mesh.visible = intensity > 0.001;
  }
}
