import * as THREE from "three";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { OutputPass } from "three/examples/jsm/postprocessing/OutputPass.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { PERF, POST } from "../data/presentation";

// The frame: the world, its bloom, then the hands drawn over it (depth cleared,
// so they never clip into walls), then tone mapping and sRGB in one place.
// Everything before the last pass is linear HDR in a multisampled half-float
// target, so bloom only catches what's genuinely brighter than white: lamps,
// the beam, windup glows, bolts and orbs, the sun glinting off the sea.

// Half floats overflow to Infinity past 65504. A glossy highlight right next to
// a lamp gets there, and the bloom blur would then smear NaN over the whole
// frame, so every built-in material's output is capped far below that (and far
// above anything that needs to glow).
const HDR_CAP = 64;
const OPAQUE = "gl_FragColor = vec4( outgoingLight, diffuseColor.a );";
if (THREE.ShaderChunk.opaque_fragment.includes(OPAQUE)) {
  THREE.ShaderChunk.opaque_fragment = THREE.ShaderChunk.opaque_fragment.replace(OPAQUE, `gl_FragColor = vec4( min( outgoingLight, vec3( ${HDR_CAP.toFixed(1)} ) ), diffuseColor.a );`);
}

export class Post {
  private readonly composer: EffectComposer;
  private readonly hands: RenderPass;
  private readonly bloom: UnrealBloomPass;

  constructor(
    private readonly renderer: THREE.WebGLRenderer,
    scene: THREE.Scene,
    camera: THREE.Camera,
  ) {
    const size = renderer.getDrawingBufferSize(new THREE.Vector2());
    const target = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType, samples: 4 });
    target.texture.name = "Post.frame";
    this.composer = new EffectComposer(renderer, target);
    this.composer.addPass(new RenderPass(scene, camera));
    const b = POST.bloom;
    this.bloom = new UnrealBloomPass(new THREE.Vector2(size.x, size.y), b.strength, b.radius, b.threshold);
    // One NaN pixel going into the blur would black out the whole screen: drop it.
    const hp = this.bloom.materialHighPassFilter;
    hp.fragmentShader = hp.fragmentShader.replace(
      "vec4 texel = texture2D( tDiffuse, vUv );",
      "vec4 texel = texture2D( tDiffuse, vUv ); if ( any( isnan( texel ) ) || any( isinf( texel ) ) ) texel = vec4( 0.0 );",
    );
    this.composer.addPass(this.bloom);
    // The hands go on after the bloom: the lantern a foot from your face would
    // otherwise haze over half the screen.
    this.hands = new RenderPass(new THREE.Scene(), camera);
    this.hands.clear = false;
    this.hands.clearDepth = true;
    this.hands.enabled = false;
    this.composer.addPass(this.hands);
    this.composer.addPass(new OutputPass());
    const css = renderer.getSize(new THREE.Vector2());
    this.setSize(css.x, css.y);
  }

  /** The first-person hands: their own scene and camera, drawn last. */
  setOverlay(scene: THREE.Scene, camera: THREE.Camera): void {
    this.hands.scene = scene;
    this.hands.camera = camera;
    this.hands.enabled = true;
  }

  setBloom(on: boolean): void {
    this.bloom.enabled = on;
  }

  /** CSS pixels; the composer applies the renderer's pixel ratio. */
  setSize(width: number, height: number): void {
    const ratio = this.renderer.getPixelRatio();
    const samples = width * height * ratio * ratio > PERF.msaa4UpTo ? 2 : 4;
    for (const rt of [this.composer.renderTarget1, this.composer.renderTarget2]) {
      if (rt.samples === samples) continue;
      // A target's sample count is fixed when it's created: drop it and it's remade on next use.
      rt.samples = samples;
      rt.dispose();
    }
    this.composer.setPixelRatio(ratio);
    this.composer.setSize(width, height);
  }

  render(dt: number): void {
    this.composer.render(dt);
  }
}
