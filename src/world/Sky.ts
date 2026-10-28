import * as THREE from "three";

/** Dusk sky dome, lights and fog. Warm low sun against a cold sea. */
export class Sky {
  readonly group = new THREE.Group();
  readonly sun: THREE.DirectionalLight;
  readonly fog: THREE.Fog;

  constructor(scene: THREE.Scene) {
    const horizon = new THREE.Color(0x6f7f86);
    this.fog = new THREE.Fog(horizon, 45, 220);
    scene.fog = this.fog;
    scene.background = horizon;

    const dome = new THREE.Mesh(
      new THREE.SphereGeometry(500, 32, 16),
      new THREE.ShaderMaterial({
        side: THREE.BackSide,
        depthWrite: false,
        uniforms: {
          top: { value: new THREE.Color(0x1b2a3a) },
          mid: { value: horizon },
          glow: { value: new THREE.Color(0xd99a5b) },
          sunDir: { value: new THREE.Vector3(-0.6, 0.12, -0.8).normalize() },
        },
        vertexShader: `varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
        fragmentShader: `uniform vec3 top; uniform vec3 mid; uniform vec3 glow; uniform vec3 sunDir; varying vec3 vDir;
          void main(){
            float h = clamp(vDir.y, 0.0, 1.0);
            vec3 c = mix(mid, top, pow(h, 0.6));
            float s = max(dot(vDir, sunDir), 0.0);
            c += glow * (pow(s, 6.0) * 0.6 + pow(s, 64.0) * 0.8) * (1.0 - h);
            gl_FragColor = vec4(c, 1.0);
          }`,
      }),
    );
    dome.renderOrder = -1;
    this.group.add(dome);

    this.group.add(new THREE.HemisphereLight(0x9fb4c0, 0x2a2420, 0.9));

    this.sun = new THREE.DirectionalLight(0xffc591, 1.6);
    this.sun.position.set(-60, 40, -80);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    const cam = this.sun.shadow.camera;
    cam.left = -70;
    cam.right = 70;
    cam.top = 70;
    cam.bottom = -70;
    cam.far = 250;
    this.sun.shadow.bias = -0.0005;
    this.group.add(this.sun);
    this.group.add(this.sun.target);

    scene.add(this.group);
  }

  setFog(near: number, far: number): void {
    this.fog.near = near;
    this.fog.far = far;
  }
}
