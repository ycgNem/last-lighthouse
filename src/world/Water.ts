import * as THREE from "three";
import { WATER_LOOK } from "../data/presentation";
import { TIDE } from "../data/tide";
import { OPEN_SEA, openSea, SHELF_SLOPE, type LevelHeights } from "./Heights";

// The sea: a plane whose Y is the tide, centred on the viewer. Gerstner swell
// in the vertex shader (calming in the shallows), and per pixel: the same
// waves' normals plus ripples (and rain rings) for sun glints, colour from the
// depth over the level's sea floor, and foam where it meets the shore. Lighting,
// shadows, fog and sky reflections come from MeshStandardMaterial.

const GRAVITY = 9.81;
/** Swell runs a little slower than deep-water dispersion says; it reads calmer. */
const SWELL_PACE = 0.75;
const RADIUS = 360;
const SEGMENTS = 168;

/** Grid lines bunch up near the centre: half-metre cells under you, ~12 m ones at the horizon. */
function gridCoord(i: number): number {
  const t = (i / SEGMENTS) * 2 - 1;
  const a = Math.abs(t);
  return Math.sign(t) * RADIUS * (0.12 * a + 0.88 * a * a * a);
}

function seaGeometry(): THREE.BufferGeometry {
  const n = SEGMENTS + 1;
  const pos = new Float32Array(n * n * 3);
  const nrm = new Float32Array(n * n * 3);
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const k = (j * n + i) * 3;
      pos[k] = gridCoord(i);
      pos[k + 2] = gridCoord(j);
      nrm[k + 1] = 1;
    }
  }
  const idx: number[] = [];
  for (let j = 0; j < SEGMENTS; j++) {
    for (let i = 0; i < SEGMENTS; i++) {
      const a = j * n + i;
      const b = a + 1;
      const c = a + n;
      const d = c + 1;
      idx.push(a, c, b, b, c, d);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("normal", new THREE.BufferAttribute(nrm, 3));
  g.setIndex(idx);
  g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), RADIUS * 1.5);
  return g;
}

const f = (v: number) => v.toFixed(5);

/** GLSL for the swell: displacement (vertex) and the slope it gives (fragment). */
function swellGlsl(): { disp: string; slope: string; crest: number } {
  let steepSum = 0;
  const disp: string[] = [];
  const slope: string[] = [];
  let crest = 0;
  WATER_LOOK.waves.forEach((w, i) => {
    const l = Math.hypot(w.dir[0], w.dir[1]);
    const dx = w.dir[0] / l;
    const dz = w.dir[1] / l;
    const k = (2 * Math.PI) / w.length;
    const omega = Math.sqrt(GRAVITY * k) * SWELL_PACE;
    // Gerstner's Q: steepness spread so crests sharpen but never loop over.
    const q = w.steep / (k * w.amp * WATER_LOOK.waves.length);
    steepSum += w.steep;
    crest += w.amp;
    const th = `(dot(vec2(${f(dx)}, ${f(dz)}), p) * ${f(k)} - uTime * ${f(omega)} + ${f(i * 1.7)})`;
    disp.push(`{ float th = ${th}; float c = cos(th); float s = sin(th);
      d.x += ${f(q * w.amp * dx)} * c; d.z += ${f(q * w.amp * dz)} * c; d.y += ${f(w.amp)} * s; }`);
    slope.push(`{ float th = ${th}; float c = cos(th); float s = sin(th);
      n.x -= ${f(dx * k * w.amp)} * c; n.z -= ${f(dz * k * w.amp)} * c; n.y -= ${f(q * k * w.amp)} * s; }`);
  });
  if (steepSum >= 1) console.warn("[water] wave steepness sums to ≥ 1; crests will loop");
  return { disp: disp.join("\n"), slope: slope.join("\n"), crest };
}

const COMMON = /* glsl */ `
uniform float uTime;
uniform float uWaterY;
uniform vec3 uViewer;
uniform sampler2D uHeights;
uniform vec4 uRect;
// Past the edge of the map the bottom keeps shelving away at the same slope as the margin.
float seaFloor(vec2 xz) {
  vec2 uv = (xz - uRect.xy) * uRect.zw;
  vec2 inside = clamp(uv, 0.0, 1.0);
  float beyond = length((uv - inside) / uRect.zw);
  return max(${f(OPEN_SEA)}, texture2D(uHeights, inside).r - ${f(SHELF_SLOPE)} * beyond);
}
// How much swell there is: less in the shallows, and none far off where the mesh is coarse.
float swellAt(vec2 xz, float depth) {
  float far = 1.0 - smoothstep(70.0, 150.0, distance(xz, uViewer.xz));
  return clamp(depth / ${f(WATER_LOOK.shoalDepth)}, 0.12, 1.0) * far;
}
`;

export class Water {
  readonly mesh: THREE.Mesh;
  private readonly uniforms = {
    uTime: { value: 0 },
    uWaterY: { value: 0 },
    uViewer: { value: new THREE.Vector3() },
    uHeights: { value: null as THREE.Texture | null },
    uRect: { value: new THREE.Vector4() },
    uRain: { value: 0 },
  };
  private readonly cell = gridCoord(SEGMENTS / 2 + 1);
  private readonly fallback = openSea();

  constructor() {
    this.uniforms.uHeights.value = this.fallback.texture;
    this.uniforms.uRect.value.copy(this.fallback.rect);
    const swell = swellGlsl();
    const look = WATER_LOOK;
    const color = (hex: number) => new THREE.Color(hex);

    const mat = new THREE.MeshStandardMaterial({
      color: look.shallow,
      roughness: look.roughness,
      metalness: 0,
      transparent: true,
    });
    mat.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, this.uniforms, {
        uShallow: { value: color(look.shallow) },
        uDeep: { value: color(look.deep) },
        uFoam: { value: color(look.foam) },
      });
      shader.vertexShader = shader.vertexShader
        .replace(
          "#include <common>",
          `#include <common>
          ${COMMON}
          varying vec3 vSea;
          varying float vSwellH;`,
        )
        .replace(
          "#include <begin_vertex>",
          `vec3 transformed = vec3(position);
          {
            vec2 p = (modelMatrix * vec4(position, 1.0)).xz;
            float amt = swellAt(p, uWaterY - seaFloor(p));
            vec3 d = vec3(0.0);
            ${swell.disp}
            transformed += d * amt;
            vSea = vec3(p.x, d.y * amt, p.y);
            vSwellH = d.y * amt;
          }`,
        );

      shader.fragmentShader = shader.fragmentShader
        .replace(
          "#include <common>",
          `#include <common>
          ${COMMON}
          uniform float uRain;
          uniform vec3 uShallow;
          uniform vec3 uDeep;
          uniform vec3 uFoam;
          varying vec3 vSea;
          varying float vSwellH;
          float hash12(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
          float vnoise(vec2 p) {
            vec2 i = floor(p); vec2 u = fract(p); u = u * u * (3.0 - 2.0 * u);
            return mix(mix(hash12(i), hash12(i + vec2(1.0, 0.0)), u.x), mix(hash12(i + vec2(0.0, 1.0)), hash12(i + vec2(1.0, 1.0)), u.x), u.y);
          }
          // Small ripples as a sum of short sines in six directions: cheap, and crisp enough to glint.
          // Each fades out once it's too fine for the pixels it covers, so the distance doesn't shimmer.
          vec2 ripples(vec2 p, float t, float footprint) {
            vec2 g = vec2(0.0);
            float s = ${f(look.ripples.scale)};
            for (int i = 0; i < 6; i++) {
              float a = float(i) * 2.399 + 0.6;
              vec2 dir = vec2(cos(a), sin(a));
              float k = s * (2.6 + float(i) * 1.15);
              float th = dot(dir, p) * k - t * ${f(look.ripples.speed)} * sqrt(k * 9.81) + float(i) * 4.1;
              float fade = smoothstep(3.0, 6.0, 6.2832 / k / footprint);
              g += dir * cos(th) * (0.9 / (1.0 + float(i) * 0.45)) * fade;
            }
            return g * ${f(look.ripples.strength)} / 6.0;
          }
          // Expanding rings where raindrops land, one per jittered 0.8 m cell, two offset layers.
          vec2 rainRings(vec2 p, float t) {
            vec2 g = vec2(0.0);
            for (int layer = 0; layer < 2; layer++) {
              vec2 q = p / 0.8 + float(layer) * vec2(0.37, 0.61);
              vec2 cell = floor(q);
              vec2 fp = fract(q) - 0.5;
              float h = hash12(cell + float(layer) * 17.0);
              vec2 c = (vec2(hash12(cell + 3.1), hash12(cell + 9.7)) - 0.5) * 0.45;
              float ph = fract(t * 0.85 + h);
              vec2 d = fp - c;
              float r = length(d);
              float x = (r - ph * 0.5) * 28.0;
              float ring = sin(x) * exp(-x * x * 0.08) * (1.0 - ph) * step(r, 0.5);
              g += d / max(r, 1e-3) * ring;
            }
            return g * 0.35;
          }`,
        )
        .replace(
          "#include <color_fragment>",
          `#include <color_fragment>
          vec2 seaP = vSea.xz;
          float seaDepth = uWaterY + vSwellH - seaFloor(seaP);
          float foamN = vnoise(seaP * 1.7 + uTime * vec2(0.11, 0.07)) * 0.6 + vnoise(seaP * 4.3 - uTime * vec2(0.05, 0.13)) * 0.4;
          // Foam: a fringe along the shore that breathes with the noise, and a little on the biggest crests.
          float shore = 1.0 - smoothstep(0.0, ${f(look.foamDepth)}, seaDepth);
          float seaFoam = smoothstep(0.42, 0.7, shore * (0.55 + 0.9 * foamN));
          seaFoam = max(seaFoam, smoothstep(0.72, 1.0, vSwellH / ${f(swell.crest)}) * smoothstep(0.45, 0.8, foamN) * 0.7);
          diffuseColor.rgb = mix(uShallow, uDeep, smoothstep(0.0, ${f(look.depthRange)}, seaDepth));
          diffuseColor.rgb = mix(diffuseColor.rgb, uFoam, seaFoam);
          diffuseColor.a = mix(mix(${f(look.alpha[0])}, ${f(look.alpha[1])}, smoothstep(0.0, 2.5, seaDepth)), 1.0, seaFoam);
          // Meet the sand softly instead of with a hard line.
          diffuseColor.a *= smoothstep(-0.03, 0.08, seaDepth);`,
        )
        .replace(
          "#include <roughnessmap_fragment>",
          `#include <roughnessmap_fragment>
          roughnessFactor = mix(roughnessFactor, 0.75, seaFoam);`,
        )
        .replace(
          "#include <normal_fragment_maps>",
          `#include <normal_fragment_maps>
          {
            float amt = swellAt(seaP, uWaterY - seaFloor(seaP));
            vec3 n = vec3(0.0, 1.0, 0.0);
            vec2 p = seaP;
            ${swell.slope.replace(/n\.(x|z) -= /g, "n.$1 -= amt * ").replace(/n\.y -= /g, "n.y -= amt * ")}
            float footprint = max(length(fwidth(seaP)), 1e-4);
            vec2 rip = ripples(seaP, uTime, footprint) * (0.35 + 0.65 * smoothstep(0.0, 1.5, seaDepth));
            rip += rainRings(seaP, uTime) * uRain * (1.0 - smoothstep(0.03, 0.08, footprint));
            n.xz -= rip;
            n = normalize(n);
            normal = normalize((viewMatrix * vec4(n, 0.0)).xyz);
          }`,
        );
    };

    this.mesh = new THREE.Mesh(seaGeometry(), mat);
    this.mesh.receiveShadow = true;
    this.mesh.frustumCulled = false;
    this.mesh.name = "water";
    this.uniforms.uWaterY.value = TIDE.lowLevel;
  }

  /** The level's sea floor (null: open sea everywhere). */
  setHeights(h: LevelHeights | null): void {
    this.uniforms.uHeights.value = h ? h.texture : this.fallback.texture;
    this.uniforms.uRect.value.copy(h ? h.rect : this.fallback.rect);
  }

  update(time: number, waterY: number, viewer: THREE.Vector3, rain: number): void {
    this.uniforms.uTime.value = time;
    this.uniforms.uWaterY.value = waterY;
    this.uniforms.uViewer.value.copy(viewer);
    this.uniforms.uRain.value = rain;
    this.mesh.position.y = waterY;
  }

  /** Keeps the plane centred on the viewer, snapped to its finest cells so the swell doesn't swim. */
  follow(x: number, z: number): void {
    this.mesh.position.x = Math.round(x / this.cell) * this.cell;
    this.mesh.position.z = Math.round(z / this.cell) * this.cell;
  }
}
