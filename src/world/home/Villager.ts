import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { damp } from "../../core/math";
import { POLYFORK_CDN, type VillagerLook } from "../../data/villagers";

// One of home's people, from a Polyfork character (see src/data/villagers.ts).
// The files come in a T-pose. pose() brings the arms down by aiming each bone
// at a direction in character space, so it doesn't depend on how a rig's
// bones are oriented; a hand keeps its rest orientation, so whatever it holds
// still hangs the way it was made to. A character whose file describes a
// carry pose (the smith's hammer on his shoulder) uses that for the carrying
// arm. update() keeps them alive: breathing, a slow shift of weight, the head
// following you as you pass, and turning to face you when you talk.

const loader = new GLTFLoader();
const files = new Map<string, Promise<THREE.Group | null>>();

function fetchModel(asset: string): Promise<THREE.Group | null> {
  let p = files.get(asset);
  if (!p) {
    p = loader.loadAsync(`${POLYFORK_CDN}${asset}.glb`).then(
      (gltf) => gltf.scene,
      (err: unknown) => {
        console.warn(`[villagers] ${asset} could not be loaded; keeping the placeholder.`, err);
        return null;
      },
    );
    files.set(asset, p);
  }
  return p;
}

/**
 * A Polyfork character comes as several skinned parts (body, hair, coat…) and
 * the loader gives each part its own copy of the skeleton. three uploads every
 * copy's bones to the GPU each frame, and each upload stalls it: five villagers
 * cost three times as much as a whole level. Parts with the same skin share one
 * skeleton, and parts that also share a material and a place become one mesh.
 */
function consolidate(root: THREE.Object3D): void {
  root.updateMatrixWorld(true);
  const parts: THREE.SkinnedMesh[] = [];
  root.traverse((o) => {
    if ((o as THREE.SkinnedMesh).isSkinnedMesh && o.visible) parts.push(o as THREE.SkinnedMesh);
  });
  const skeletons: THREE.Skeleton[] = [];
  for (const m of parts) {
    const same = skeletons.find((s) => sameSkin(s, m.skeleton));
    if (same) m.skeleton = same;
    else skeletons.push(m.skeleton);
  }
  const groups = new Map<string, THREE.SkinnedMesh[]>();
  for (const m of parts) {
    const key = `${m.skeleton.uuid}/${(m.material as THREE.Material).uuid}`;
    const list = groups.get(key);
    if (list) list.push(m);
    else groups.set(key, [m]);
  }
  for (const [first, ...rest] of groups.values()) {
    if (!first) continue;
    const join = rest.filter((m) => sameMatrix(m.matrixWorld, first.matrixWorld) && sameMatrix(m.bindMatrix, first.bindMatrix));
    if (!join.length) continue;
    const merged = mergeGeometries([first.geometry, ...join.map((m) => m.geometry)]);
    if (!merged) continue;
    first.geometry = merged;
    for (const m of join) m.removeFromParent();
  }
}

function sameSkin(a: THREE.Skeleton, b: THREE.Skeleton): boolean {
  return a.bones.length === b.bones.length && a.bones.every((bone, i) => bone === b.bones[i] && a.boneInverses[i]!.equals(b.boneInverses[i]!));
}

function sameMatrix(a: THREE.Matrix4, b: THREE.Matrix4): boolean {
  return a.elements.every((v, i) => Math.abs(v - b.elements[i]!) < 1e-5);
}

interface CarryPose {
  shoulder: number[];
  arm: number[];
  foreArm: number[];
  hand: number[];
}

/** How far the head turns, and how near you must be before someone looks round or turns to you. */
const LOOK = { yaw: 1.05, pitch: 0.35, range: 9, faceRange: 3.6 };
const HEAD_HEIGHT = 1.5;
const DEG = Math.PI / 180;

const tmpV = new THREE.Vector3();
const tmpV2 = new THREE.Vector3();
const tmpQ = new THREE.Quaternion();
const tmpQ2 = new THREE.Quaternion();
const tmpE = new THREE.Euler();
const Y = new THREE.Vector3(0, 1, 0);
const X = new THREE.Vector3(1, 0, 0);
const Z = new THREE.Vector3(0, 0, 1);

export class Villager {
  /** Goes in the NPC's group, at its feet. */
  readonly object: THREE.Group;
  private readonly bones = new Map<string, THREE.Object3D>();
  /** Posed local rotations, and each animated bone's parent orientation in character space. */
  private readonly base = new Map<string, THREE.Quaternion>();
  private readonly parentQ = new Map<string, THREE.Quaternion>();
  private readonly t0 = Math.random() * 100;
  private headYaw = 0;
  private headPitch = 0;
  private bodyYaw: number;

  /** `yaw`: which way they face at rest (0 faces +Z), from their marker in the map. */
  static async load(look: VillagerLook, yaw: number): Promise<Villager | null> {
    const scene = await fetchModel(look.asset);
    return scene ? new Villager(scene, look, yaw) : null;
  }

  private constructor(
    scene: THREE.Group,
    look: VillagerLook,
    private readonly restYaw: number,
  ) {
    this.object = scene;
    for (const side of look.hide ?? []) {
      const held = scene.getObjectByName(`attach-${side}-mesh`);
      if (held) held.visible = false;
    }
    consolidate(scene);
    scene.traverse((o) => {
      if ((o as THREE.Bone).isBone) this.bones.set(o.name, o);
      const m = o as THREE.Mesh;
      if (m.isMesh) m.castShadow = m.receiveShadow = true;
    });
    const proportions = scene.getObjectByName("character")?.userData.proportions as { carry?: string; carryPose?: CarryPose } | undefined;
    this.pose(proportions?.carry ?? null, proportions?.carryPose ?? null);
    // Bounds for culling, taken in the pose (the file's are for the T-pose), with
    // room for breathing and the head turning.
    scene.traverse((o) => {
      const m = o as THREE.SkinnedMesh;
      if (!m.isSkinnedMesh) return;
      m.computeBoundingSphere();
      if (m.boundingSphere) m.boundingSphere.radius += 0.3;
    });
    this.bodyYaw = restYaw;
    scene.rotation.y = restYaw;
  }

  private pose(carry: string | null, carryPose: CarryPose | null): void {
    const root = this.object;
    root.rotation.set(0, 0, 0);
    root.updateMatrixWorld(true);
    for (const side of ["Left", "Right"] as const) {
      const s = side === "Left" ? 1 : -1;
      const hand = this.bones.get(`${side}Hand`);
      const handRest = hand ? hand.getWorldQuaternion(new THREE.Quaternion()) : null;
      if (carryPose && carry === side.toLowerCase()) {
        this.setEuler(`${side}Shoulder`, carryPose.shoulder);
        this.setEuler(`${side}Arm`, carryPose.arm);
        this.setEuler(`${side}ForeArm`, carryPose.foreArm);
        this.setEuler(`${side}Hand`, carryPose.hand);
        continue;
      }
      this.aim(`${side}Arm`, `${side}ForeArm`, tmpV.set(0.2 * s, -1, 0.06));
      this.aim(`${side}ForeArm`, `${side}Hand`, tmpV.set(0.07 * s, -1, 0.3));
      if (hand && handRest) {
        root.updateMatrixWorld(true);
        hand.quaternion.copy(hand.parent!.getWorldQuaternion(tmpQ).invert().multiply(handRest));
      }
    }
    root.updateMatrixWorld(true);
    for (const [name, bone] of this.bones) this.base.set(name, bone.quaternion.clone());
    for (const name of ["Hips", "Spine2", "Neck", "Head"]) {
      const bone = this.bones.get(name);
      if (bone?.parent) this.parentQ.set(name, bone.parent.getWorldQuaternion(new THREE.Quaternion()));
    }
  }

  /** Turns a bone (in character space, about its joint) so it points from its joint to its child along dir. */
  private aim(name: string, child: string, dir: THREE.Vector3): void {
    const bone = this.bones.get(name);
    const next = this.bones.get(child);
    if (!bone?.parent || !next) return;
    this.object.updateMatrixWorld(true);
    const cur = next.getWorldPosition(tmpV2).sub(bone.getWorldPosition(new THREE.Vector3())).normalize();
    const r = tmpQ2.setFromUnitVectors(cur, dir.clone().normalize());
    const pq = bone.parent.getWorldQuaternion(new THREE.Quaternion());
    bone.quaternion.premultiply(pq).premultiply(r).premultiply(pq.invert());
  }

  private setEuler(name: string, deg: number[]): void {
    const bone = this.bones.get(name);
    if (!bone) return;
    bone.quaternion.multiply(tmpQ.setFromEuler(tmpE.set((deg[0] ?? 0) * DEG, (deg[1] ?? 0) * DEG, (deg[2] ?? 0) * DEG)));
  }

  /** base · (parent⁻¹ · r · parent): rotates a posed bone by r, given in character space. */
  private turn(name: string, r: THREE.Quaternion): void {
    const bone = this.bones.get(name);
    const base = this.base.get(name);
    const pq = this.parentQ.get(name);
    if (!bone || !base || !pq) return;
    bone.quaternion.copy(pq).invert().multiply(r).multiply(pq).multiply(base);
  }

  /** viewer: the player's position in the villager's parent space (the NPC group). */
  update(dt: number, time: number, viewer: THREE.Vector3 | null): void {
    const t = time + this.t0;
    let lookYaw = 0;
    let lookPitch = 0;
    let faceYaw = this.restYaw;
    if (viewer) {
      const dx = viewer.x - this.object.position.x;
      const dz = viewer.z - this.object.position.z;
      const d = Math.hypot(dx, dz);
      if (d < LOOK.faceRange) faceYaw = Math.atan2(dx, dz);
      if (d < LOOK.range) {
        const rel = Math.atan2(Math.sin(Math.atan2(dx, dz) - this.bodyYaw), Math.cos(Math.atan2(dx, dz) - this.bodyYaw));
        if (Math.abs(rel) < LOOK.yaw * 1.6) {
          lookYaw = THREE.MathUtils.clamp(rel, -LOOK.yaw, LOOK.yaw);
          lookPitch = THREE.MathUtils.clamp(Math.atan2(viewer.y + 1.6 - HEAD_HEIGHT - this.object.position.y, d), -LOOK.pitch, LOOK.pitch);
        }
      }
    }
    const turnBy = Math.atan2(Math.sin(faceYaw - this.bodyYaw), Math.cos(faceYaw - this.bodyYaw));
    this.bodyYaw += turnBy * (1 - Math.exp(-2.5 * dt));
    this.object.rotation.y = this.bodyYaw;
    this.headYaw = damp(this.headYaw, lookYaw, 4, dt);
    this.headPitch = damp(this.headPitch, lookPitch, 4, dt);

    // Breath lifts the chest; weight drifts from foot to foot.
    this.turn("Spine2", tmpQ.setFromAxisAngle(X, Math.sin(t * 1.7) * 0.02));
    this.turn("Hips", tmpQ.setFromAxisAngle(Z, Math.sin(t * 0.45) * 0.02).multiply(tmpQ2.setFromAxisAngle(Y, Math.sin(t * 0.31) * 0.03)));
    // Looking: the neck takes some of it, the head the rest. Up is a negative turn about X.
    const look = (k: number) => tmpQ.setFromAxisAngle(Y, this.headYaw * k).multiply(tmpQ2.setFromAxisAngle(X, -this.headPitch * k));
    this.turn("Neck", look(0.4));
    this.turn("Head", look(0.6));
  }
}
