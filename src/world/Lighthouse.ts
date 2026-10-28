import * as THREE from "three";
import type { StageVisuals } from "../data/lighthouse";

// The beam is the most important visual in the game: it's the sanctuary, the
// navigation and the progress bar all at once. BeamRig is the rotating lamp and
// its two cones; Lighthouse wraps it in the home tower. The same rig is the
// distant home light seen from expeditions and the Saltmere beacon.

const TOWER_HEIGHT = 24;

function beamMaterial(): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
    // No fog: the beam reads through the sea fog from far away, which is the point.
    fog: false,
    uniforms: { color: { value: new THREE.Color(0xfff1c9) }, intensity: { value: 1 } },
    // CylinderGeometry uv.y is 1 at the tip (the lamp) and 0 at the far end.
    vertexShader: `varying vec2 vUv; varying vec3 vN; varying vec3 vView;
      void main(){ vUv = uv; vec4 mv = modelViewMatrix * vec4(position,1.0);
      vN = normalize(normalMatrix * normal); vView = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `uniform vec3 color; uniform float intensity; varying vec2 vUv; varying vec3 vN; varying vec3 vView;
      void main(){
        float along = vUv.y;
        float edge = pow(abs(dot(vN, vView)), 1.5);
        float a = pow(along, 1.6) * edge * 0.55 * intensity;
        gl_FragColor = vec4(color * a, a);
      }`,
  });
}

let coneGeo: THREE.CylinderGeometry | null = null;
function beamGeometry(): THREE.CylinderGeometry {
  if (!coneGeo) {
    coneGeo = new THREE.CylinderGeometry(0.0, 1, 1, 32, 1, true);
    coneGeo.translate(0, -0.5, 0);
    coneGeo.rotateZ(Math.PI); // tip at origin, opening toward +Y
  }
  return coneGeo;
}

export interface BeamLook {
  color: number;
  length: number;
  intensity: number;
  /** 0 = steady, 1 = badly flickering. */
  flicker: number;
}

export class BeamRig {
  readonly pivot = new THREE.Group();
  private readonly lamp: THREE.Mesh;
  private readonly beams: THREE.Mesh[] = [];
  private readonly mat = beamMaterial();
  private readonly spot: THREE.SpotLight | null;
  private readonly point: THREE.PointLight | null;
  private look: BeamLook = { color: 0xfff1c9, length: 40, intensity: 0, flicker: 0 };
  private t = 0;
  /** Radians per second. */
  spin = 0.45;

  constructor(opts: { lights: boolean; lampRadius?: number; groundDrop?: number }) {
    this.lamp = new THREE.Mesh(new THREE.SphereGeometry(opts.lampRadius ?? 0.7, 16, 12), new THREE.MeshBasicMaterial({ color: 0xfff1c9, fog: false }));
    this.pivot.add(this.lamp);
    for (const dir of [1, -1]) {
      const beam = new THREE.Mesh(beamGeometry(), this.mat);
      beam.rotation.z = (-Math.PI / 2) * dir; // lay along ±X
      beam.renderOrder = 2;
      beam.frustumCulled = false;
      this.beams.push(beam);
      this.pivot.add(beam);
    }
    if (opts.lights) {
      this.point = new THREE.PointLight(0xffd59a, 30, 40, 1.5);
      this.pivot.add(this.point);
      this.spot = new THREE.SpotLight(0xfff1c9, 400, 120, 0.12, 0.6, 1.2);
      this.spot.target.position.set(60, -(opts.groundDrop ?? TOWER_HEIGHT), 0);
      this.pivot.add(this.spot, this.spot.target);
    } else {
      this.spot = null;
      this.point = null;
    }
    this.setLook(this.look);
  }

  setLook(look: BeamLook): void {
    this.look = look;
    this.mat.uniforms.color!.value.setHex(look.color);
    (this.lamp.material as THREE.MeshBasicMaterial).color.setHex(look.color);
    this.lamp.visible = look.intensity > 0;
    if (this.spot) {
      this.spot.color.setHex(look.color);
      this.spot.distance = look.length * 1.4;
    }
    const radius = look.length * 0.09;
    for (const b of this.beams) {
      b.scale.set(radius, look.length, radius);
      b.visible = look.intensity > 0;
    }
  }

  update(dt: number): void {
    this.pivot.rotation.y += this.spin * dt;
    this.t += dt;
    // A failing lamp dips irregularly; a restored one is steady.
    const n = Math.sin(this.t * 13.1) * Math.sin(this.t * 7.3 + 1.2) * Math.sin(this.t * 2.1);
    const k = this.look.intensity * (1 - this.look.flicker * Math.max(0, n) * 0.9);
    this.mat.uniforms.intensity!.value = k;
    if (this.spot) this.spot.intensity = 400 * k;
    if (this.point) this.point.intensity = this.look.intensity > 0 ? 30 * (0.4 + k) : 0;
  }
}

export function stageLook(v: StageVisuals): BeamLook {
  return { color: v.beamColor, length: v.beamLength, intensity: v.beamIntensity, flicker: v.flicker };
}

/** The home tower with its beam. */
export class Lighthouse {
  readonly group = new THREE.Group();
  readonly rig = new BeamRig({ lights: true });

  constructor() {
    const stone = new THREE.MeshStandardMaterial({ color: 0xc9c3b5, roughness: 0.9 });
    const band = new THREE.MeshStandardMaterial({ color: 0x7a2e2a, roughness: 0.8 });
    const iron = new THREE.MeshStandardMaterial({ color: 0x2b2f33, roughness: 0.6, metalness: 0.6 });

    const tower = new THREE.Mesh(new THREE.CylinderGeometry(2.6, 3.8, TOWER_HEIGHT, 24), stone);
    tower.position.y = TOWER_HEIGHT / 2;
    tower.castShadow = tower.receiveShadow = true;
    this.group.add(tower);

    for (const y of [7, 15]) {
      const ring = new THREE.Mesh(new THREE.CylinderGeometry(3.45 - y * 0.045, 3.5 - y * 0.045, 1.6, 24), band);
      ring.position.y = y;
      this.group.add(ring);
    }

    const gallery = new THREE.Mesh(new THREE.CylinderGeometry(3.8, 3.8, 0.4, 24), iron);
    gallery.position.y = TOWER_HEIGHT + 0.2;
    this.group.add(gallery);

    const glass = new THREE.Mesh(
      new THREE.CylinderGeometry(2.1, 2.1, 3, 12, 1, true),
      new THREE.MeshStandardMaterial({ color: 0xfff1c9, emissive: 0xffb347, emissiveIntensity: 0.4, transparent: true, opacity: 0.35, side: THREE.DoubleSide }),
    );
    glass.position.y = TOWER_HEIGHT + 1.9;
    this.group.add(glass);

    const roof = new THREE.Mesh(new THREE.ConeGeometry(2.6, 2.2, 12), iron);
    roof.position.y = TOWER_HEIGHT + 4.5;
    roof.castShadow = true;
    this.group.add(roof);

    this.rig.pivot.position.y = TOWER_HEIGHT + 1.9;
    this.group.add(this.rig.pivot);
  }

  applyStage(v: StageVisuals): void {
    this.rig.setLook(stageLook(v));
  }

  update(dt: number): void {
    this.rig.update(dt);
  }
}

/** Lantern's Rest as seen from an expedition: just the light on the horizon. */
export class DistantLight {
  readonly rig = new BeamRig({ lights: false, lampRadius: 1.6 });

  constructor(at: THREE.Vector3, v: StageVisuals) {
    this.rig.pivot.position.set(at.x, 28, at.z);
    this.rig.setLook({ ...stageLook(v), length: v.beamLength * 1.5, intensity: Math.max(0.5, v.beamIntensity) });
  }
}
