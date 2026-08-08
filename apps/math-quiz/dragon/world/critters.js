import * as THREE from 'three';

// Small wildlife that makes the valley feel alive: bunnies that hop and pause
// around the clearing, and dandelion puffs drifting on the breeze. Purely
// decorative — no interactions, one update(delta) like ambient.js.
export function createCritters(scene, { nestPos = new THREE.Vector3(0, 0, -2) } = {}) {
  const root = new THREE.Group();
  scene.add(root);
  const animated = [];

  function buildBunny(color) {
    const bunny = new THREE.Group();
    const furMat = new THREE.MeshStandardMaterial({ color, roughness: 0.9, flatShading: true });
    const body = new THREE.Mesh(new THREE.SphereGeometry(0.22, 7, 6), furMat);
    body.scale.set(1, 0.85, 1.25);
    body.position.y = 0.2;
    const bunnyHead = new THREE.Mesh(new THREE.SphereGeometry(0.14, 7, 6), furMat);
    bunnyHead.position.set(0, 0.38, 0.2);
    const tail = new THREE.Mesh(new THREE.SphereGeometry(0.07, 5, 4),
      new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 1 }));
    tail.position.set(0, 0.22, -0.26);
    bunny.add(body, bunnyHead, tail);
    for (const side of [-1, 1]) {
      const ear = new THREE.Mesh(new THREE.ConeGeometry(0.05, 0.26, 5), furMat);
      ear.position.set(side * 0.06, 0.58, 0.16);
      ear.rotation.z = side * -0.15;
      bunny.add(ear);
    }
    bunny.traverse((n) => { if (n.isMesh) n.castShadow = true; });
    return bunny;
  }
  // Each bunny wanders its own loop: hop bursts (parabolic arcs along the
  // path) separated by still "nibbling" pauses.
  const bunnySpecs = [
    { color: 0xbcaaa4, cx: nestPos.x + 9, cz: nestPos.z + 7, r: 3.5, speed: 0.16, phase: 0 },
    { color: 0xefebe9, cx: nestPos.x - 8, cz: nestPos.z + 5, r: 2.8, speed: 0.2, phase: 2.4 },
    { color: 0x8d6e63, cx: nestPos.x + 12, cz: nestPos.z - 7, r: 4.2, speed: 0.13, phase: 4.4 },
  ];
  for (const spec of bunnySpecs) {
    const bunny = buildBunny(spec.color);
    root.add(bunny);
    animated.push((delta, t) => {
      const cycle = t * spec.speed + spec.phase;
      const a = cycle % (Math.PI * 2);
      // hopGate: ~60% of the time hopping, 40% paused mid-loop.
      const hopGate = (Math.sin(cycle * 3.1) + 1) / 2;
      const hop = hopGate > 0.4 ? Math.abs(Math.sin(t * 6 + spec.phase)) * 0.22 : 0;
      const x = spec.cx + Math.cos(a) * spec.r;
      const z = spec.cz + Math.sin(a) * spec.r;
      bunny.position.set(x, hop, z);
      bunny.rotation.y = -a + Math.PI / 2;   // face along the path
    });
  }

  // Dandelion puffs: soft white motes drifting in slow spirals near the nest.
  const puffMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true });
  for (let i = 0; i < 7; i++) {
    const puff = new THREE.Mesh(new THREE.SphereGeometry(0.05, 5, 4), puffMat.clone());
    puff.userData.phase = i * 1.3;
    root.add(puff);
    animated.push((delta, t) => {
      const p = puff.userData.phase;
      puff.position.set(
        nestPos.x + Math.sin(t * 0.11 + p) * 11,
        0.8 + Math.sin(t * 0.5 + p * 2) * 0.5 + ((t * 0.07 + p) % 1) * 1.2,
        nestPos.z + Math.cos(t * 0.13 + p * 1.4) * 9
      );
      puff.material.opacity = 0.35 + (Math.sin(t * 0.9 + p) + 1) * 0.2;
    });
  }

  function update(delta) {
    const t = performance.now() * 0.001;
    for (const fn of animated) fn(delta, t);
  }
  return { root, update };
}
