import * as THREE from "three";

// Diegetic flood warning: while the tide is about to rise, every surface that
// will go under (between the water and the high-tide line) glows with a faint
// pulsing foam colour. Applied to Blender materials whose name starts TIDE_.

export const TIDE_UNIFORMS = {
  uTideWaterY: { value: 0 },
  uTideHighY: { value: 1.8 },
  uTideWarn: { value: 0 },
  uTideTime: { value: 0 },
};

const patched = new WeakSet<THREE.Material>();

export function patchTideMaterial(mat: THREE.Material): void {
  if (patched.has(mat)) return;
  patched.add(mat);
  mat.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, TIDE_UNIFORMS);
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nvarying float vTideY;")
      .replace("#include <project_vertex>", "#include <project_vertex>\nvTideY = (modelMatrix * vec4(transformed, 1.0)).y;");
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        "#include <common>\nvarying float vTideY;\nuniform float uTideWaterY; uniform float uTideHighY; uniform float uTideWarn; uniform float uTideTime;",
      )
      .replace(
        "#include <emissivemap_fragment>",
        `#include <emissivemap_fragment>
        float tideBand = step(uTideWaterY + 0.03, vTideY) * (1.0 - smoothstep(uTideHighY - 0.05, uTideHighY + 0.05, vTideY));
        float tidePulse = 0.55 + 0.45 * sin(uTideTime * 3.0 - vTideY * 5.0);
        totalEmissiveRadiance += vec3(0.32, 0.8, 0.7) * tideBand * uTideWarn * tidePulse * 0.35;`,
      );
  };
  mat.needsUpdate = true;
}
