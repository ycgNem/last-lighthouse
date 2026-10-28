import * as THREE from "three";
import { MeshBVH } from "three-mesh-bvh";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

// All static level collision for one location, merged into a single world-space
// BVH. Built from Blender COL_ meshes (and meshes tagged `col`), or from the
// greybox meshes at home.

const box = new THREE.Box3();
const triPoint = new THREE.Vector3();
const capsulePoint = new THREE.Vector3();
const pushDir = new THREE.Vector3();
const ray = new THREE.Ray();
const hitInfo = { point: new THREE.Vector3(), distance: 0, faceIndex: 0 };
const DOWN = new THREE.Vector3(0, -1, 0);

export class StaticCollider {
  private readonly bvh: MeshBVH | null;
  /** Debug/inspection only. */
  readonly geometry: THREE.BufferGeometry | null;

  constructor(meshes: readonly THREE.Mesh[]) {
    const parts: THREE.BufferGeometry[] = [];
    for (const m of meshes) {
      m.updateWorldMatrix(true, false);
      const src = m.geometry.index ? m.geometry.toNonIndexed() : m.geometry.clone();
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", src.getAttribute("position").clone());
      g.applyMatrix4(m.matrixWorld);
      parts.push(g);
    }
    this.geometry = parts.length ? mergeGeometries(parts, false) : null;
    this.bvh = this.geometry ? new MeshBVH(this.geometry) : null;
  }

  /**
   * Pushes a capsule (segment + radius, world space) out of the level, in place.
   * The caller compares the segment before and after to get the push.
   */
  resolveCapsule(segment: THREE.Line3, radius: number): void {
    if (!this.bvh) return;
    box.makeEmpty();
    box.expandByPoint(segment.start);
    box.expandByPoint(segment.end);
    box.min.addScalar(-radius);
    box.max.addScalar(radius);
    this.bvh.shapecast({
      intersectsBounds: (b) => b.intersectsBox(box),
      intersectsTriangle: (tri) => {
        const d = tri.closestPointToSegment(segment, triPoint, capsulePoint);
        if (d >= radius) return;
        pushDir.subVectors(capsulePoint, triPoint);
        if (pushDir.lengthSq() < 1e-10) tri.getNormal(pushDir);
        pushDir.normalize();
        const depth = radius - d;
        segment.start.addScaledVector(pushDir, depth);
        segment.end.addScaledVector(pushDir, depth);
      },
    });
  }

  /** First hit along a ray, or null. `dir` must be normalised. */
  raycast(origin: THREE.Vector3, dir: THREE.Vector3, far: number): THREE.Intersection | null {
    if (!this.bvh) return null;
    ray.origin.copy(origin);
    ray.direction.copy(dir);
    return this.bvh.raycastFirst(ray, THREE.DoubleSide, 0, far);
  }

  /** Height of the first surface below (x, fromY, z), or -Infinity. */
  groundHeight(x: number, z: number, fromY: number, maxDrop = 80): number {
    const hit = this.raycast(new THREE.Vector3(x, fromY, z), DOWN, maxDrop);
    return hit ? hit.point.y : -Infinity;
  }

  /** True if the straight line from a to b is blocked by level geometry. */
  blocked(a: THREE.Vector3, b: THREE.Vector3): boolean {
    const dir = new THREE.Vector3().subVectors(b, a);
    const len = dir.length();
    if (len < 1e-4) return false;
    return this.raycast(a, dir.divideScalar(len), len) !== null;
  }

  /** Moves a sphere's centre out of the level. Returns true if it was touching. */
  pushSphere(center: THREE.Vector3, radius: number): boolean {
    if (!this.bvh) return false;
    const hit = this.bvh.closestPointToPoint(center, hitInfo, 0, radius);
    if (!hit || hit.distance >= radius) return false;
    pushDir.subVectors(center, hit.point);
    if (pushDir.lengthSq() < 1e-10) pushDir.set(0, 1, 0);
    center.addScaledVector(pushDir.normalize(), radius - hit.distance);
    return true;
  }

  sphereHits(center: THREE.Vector3, radius: number): boolean {
    return this.bvh ? this.bvh.intersectsSphere(new THREE.Sphere(center, radius)) : false;
  }
}

/** A moving box the player can stand on (buoyant crates and rafts). */
export interface DynamicBox {
  box: THREE.Box3;
}
