import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

// Loads the Blender exports in public/assets/models. Shared files (props,
// enemies, viewmodels) are preloaded once and cloned by object name.

export const SHARED_MODELS = ["props.glb", "enemies.glb", "viewmodels.glb"] as const;

export class Assets {
  private readonly loader = new GLTFLoader();
  private readonly files = new Map<string, Promise<THREE.Group | null>>();
  private readonly ready = new Map<string, THREE.Group>();

  /** Loads (once) and returns the file's scene, or null if it's missing. */
  load(path: string): Promise<THREE.Group | null> {
    let p = this.files.get(path);
    if (!p) {
      p = this.loader.loadAsync(`${import.meta.env.BASE_URL}assets/models/${path}`).then(
        (gltf) => {
          gltf.scene.traverse((o) => {
            const m = o as THREE.Mesh;
            if (m.isMesh) m.castShadow = m.receiveShadow = true;
          });
          this.ready.set(path, gltf.scene);
          return gltf.scene;
        },
        (err: unknown) => {
          console.warn(`[assets] ${path} could not be loaded; using placeholders.`, err);
          return null;
        },
      );
      this.files.set(path, p);
    }
    return p;
  }

  async preload(paths: readonly string[]): Promise<void> {
    await Promise.all(paths.map((p) => this.load(p)));
  }

  /** Deep clone of a named top-level object from a loaded file (shares geometry and materials). */
  clone(path: string, name: string): THREE.Object3D | null {
    const src = this.ready.get(path)?.getObjectByName(name);
    if (!src) return null;
    const c = src.clone(true);
    c.position.set(0, 0, 0);
    c.rotation.set(0, 0, 0);
    c.scale.set(1, 1, 1);
    return c;
  }

  prop(name: string): THREE.Object3D | null {
    return this.clone("props.glb", `PROP_${name}`);
  }
}

/** Gives every mesh under `root` its own material copies (for per-instance flashes and glows). */
export function uniqueMaterials(root: THREE.Object3D): THREE.MeshStandardMaterial[] {
  const out: THREE.MeshStandardMaterial[] = [];
  root.traverse((o) => {
    const m = o as THREE.Mesh;
    if (!m.isMesh) return;
    if (Array.isArray(m.material)) {
      m.material = m.material.map((mat) => mat.clone());
      out.push(...(m.material as THREE.MeshStandardMaterial[]));
    } else {
      m.material = m.material.clone();
      out.push(m.material as THREE.MeshStandardMaterial);
    }
  });
  return out;
}
