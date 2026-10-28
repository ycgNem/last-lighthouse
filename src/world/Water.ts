import * as THREE from "three";

// Animated ocean: a big plane whose Y is the tide level, with a few summed
// sine waves in the vertex shader. M6 upgrades this to Gerstner waves, depth
// colour and shoreline foam.

const WAVES = [
  // dirX, dirZ, wavelength, amplitude, speed
  [1.0, 0.3, 14, 0.12, 1.1],
  [-0.4, 1.0, 9, 0.08, 1.4],
  [0.7, -0.8, 5, 0.04, 2.0],
  [-1.0, -0.2, 3.2, 0.02, 2.6],
] as const;

const glslWaves = WAVES.map(([dx, dz, len, amp, spd]) => {
  const l = Math.hypot(dx, dz);
  const k = ((2 * Math.PI) / len).toFixed(4);
  return `{ vec2 d = vec2(${(dx / l).toFixed(4)}, ${(dz / l).toFixed(4)}); float ph = dot(d, p) * ${k} + uTime * ${spd.toFixed(3)};
    h += ${amp.toFixed(4)} * sin(ph); g += d * ${amp.toFixed(4)} * ${k} * cos(ph); }`;
}).join("\n");

export class Water {
  readonly mesh: THREE.Mesh;
  private readonly uniforms = { uTime: { value: 0 } };
  private readonly cell: number;

  constructor(size = 700, segments = 220) {
    this.cell = size / segments;
    const geo = new THREE.PlaneGeometry(size, size, segments, segments);
    geo.rotateX(-Math.PI / 2);

    const mat = new THREE.MeshStandardMaterial({
      color: 0x1f6f78,
      roughness: 0.18,
      metalness: 0.05,
      transparent: true,
      opacity: 0.93,
    });
    mat.onBeforeCompile = (shader) => {
      shader.uniforms.uTime = this.uniforms.uTime;
      shader.vertexShader = shader.vertexShader
        .replace(
          "#include <common>",
          `#include <common>
          uniform float uTime;
          float waveH; vec2 waveG;`,
        )
        .replace(
          "#include <beginnormal_vertex>",
          `vec2 p = (modelMatrix * vec4(position, 1.0)).xz;
          float h = 0.0; vec2 g = vec2(0.0);
          ${glslWaves}
          waveH = h; waveG = g;
          vec3 objectNormal = normalize(vec3(-g.x, 1.0, -g.y));
          #ifdef USE_TANGENT
            vec3 objectTangent = vec3(tangent.xyz);
          #endif`,
        )
        .replace(
          "#include <begin_vertex>",
          `vec3 transformed = vec3(position);
          transformed.y += waveH;`,
        );
    };

    this.mesh = new THREE.Mesh(geo, mat);
    this.mesh.receiveShadow = true;
    this.mesh.name = "water";
  }

  update(time: number, waterY: number): void {
    this.uniforms.uTime.value = time;
    this.mesh.position.y = waterY;
  }

  /** Keeps the plane centred on the viewer. Snaps to whole grid cells so waves don't swim. */
  follow(x: number, z: number): void {
    this.mesh.position.x = Math.round(x / this.cell) * this.cell;
    this.mesh.position.z = Math.round(z / this.cell) * this.cell;
  }
}
