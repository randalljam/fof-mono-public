import * as THREE from 'three';

// Ambient world life, built entirely from primitives (The-Aviator-style: groups
// of flat-shaded simple meshes + micro-animation). One update(delta) drives all
// of it. The mountains + Mount Ember moved to world/mountains.js when they
// became climbable quest terrain.
const PALETTE = {
  cloud: 0xffffff, trunk: 0x5c4033, rockA: 0x9e9e9e, rockB: 0x757575,
  flame: 0xff9800, flameCore: 0xffeb3b,
  petal: [0xff6b9d, 0xffd54f, 0xba68c8, 0xff8a65, 0x4fc3f7],
  butterfly: [0xffb74d, 0xf06292, 0x9575cd, 0x4dd0e1],
  firefly: 0xfff176, water: 0x4fc3f7, lily: 0x66bb6a, bird: 0x455a64,
};

export function createAmbient(scene, { nestPos = new THREE.Vector3(0, 0, -2) } = {}) {
  const root = new THREE.Group();
  scene.add(root);
  const animated = [];   // { update(delta, t) }

  // --- Drifting clouds (clusters of flattened spheres) ---
  const clouds = new THREE.Group();
  const cloudMat = new THREE.MeshStandardMaterial({ color: PALETTE.cloud, roughness: 1, flatShading: true });
  const cloudList = [];
  for (let i = 0; i < 7; i++) {
    const cloud = new THREE.Group();
    const blobs = 3 + (i % 3);
    for (let b = 0; b < blobs; b++) {
      const blob = new THREE.Mesh(new THREE.SphereGeometry(1.6 + (b % 2), 7, 5), cloudMat);
      blob.position.set(b * 1.7 - blobs * 0.8, (b % 2) * 0.5, ((b * 13) % 3) - 1);
      blob.scale.y = 0.55;
      cloud.add(blob);
    }
    cloud.position.set(-60 + i * 18, 20 + (i % 3) * 5, -50 + ((i * 29) % 90));
    cloud.userData.speed = 0.8 + (i % 3) * 0.35;
    clouds.add(cloud);
    cloudList.push(cloud);
  }
  animated.push({
    update: (delta) => {
      for (const c of cloudList) {
        c.position.x += c.userData.speed * delta;
        if (c.position.x > 75) c.position.x = -75;
      }
    },
  });
  root.add(clouds);

  // --- Birds circling high ---
  const birds = new THREE.Group();
  const birdList = [];
  for (let i = 0; i < 3; i++) {
    const bird = new THREE.Group();
    const mat = new THREE.MeshBasicMaterial({ color: PALETTE.bird, side: THREE.DoubleSide });
    const wingL = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.28), mat);
    wingL.position.x = -0.42;
    const wingR = wingL.clone();
    wingR.position.x = 0.42;
    bird.add(wingL, wingR);
    bird.userData = { wings: [wingL, wingR], radius: 16 + i * 7, speed: 0.14 + i * 0.05, phase: i * 2.1, height: 16 + i * 3 };
    birds.add(bird);
    birdList.push(bird);
  }
  animated.push({
    update: (delta, t) => {
      for (const b of birdList) {
        const { radius, speed, phase, height, wings } = b.userData;
        const a = t * speed + phase;
        b.position.set(Math.cos(a) * radius, height + Math.sin(t * 0.7 + phase) * 1.2, Math.sin(a) * radius - 10);
        b.rotation.y = -a;
        const flap = Math.sin(t * 7 + phase) * 0.7;
        wings[0].rotation.z = flap;
        wings[1].rotation.z = -flap;
      }
    },
  });
  root.add(birds);

  // --- Rocks, flowers, mushrooms scattered around the clearing ---
  const scatter = new THREE.Group();
  const rockGeo = new THREE.DodecahedronGeometry(0.4);
  for (let i = 0; i < 10; i++) {
    const rock = new THREE.Mesh(
      rockGeo,
      new THREE.MeshStandardMaterial({ color: i % 2 ? PALETTE.rockA : PALETTE.rockB, roughness: 1, flatShading: true })
    );
    const a = (i / 10) * Math.PI * 2 + 0.7;
    const r = 6 + ((i * 11) % 9);
    rock.position.set(Math.cos(a) * r, 0.14, Math.sin(a) * r - 2);
    rock.scale.setScalar(0.5 + ((i * 7) % 4) * 0.3);
    rock.castShadow = true;
    scatter.add(rock);
  }
  const stemMat = new THREE.MeshStandardMaterial({ color: 0x388e3c, roughness: 1 });
  const flowerSpots = [];
  for (let i = 0; i < 22; i++) {
    const flower = new THREE.Group();
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.03, 0.4, 4), stemMat);
    stem.position.y = 0.2;
    const head = new THREE.Mesh(
      new THREE.SphereGeometry(0.09, 6, 5),
      new THREE.MeshStandardMaterial({ color: PALETTE.petal[i % PALETTE.petal.length], roughness: 0.7 })
    );
    head.position.y = 0.44;
    flower.add(stem, head);
    const a = (i / 22) * Math.PI * 2 + 1.4;
    const r = 4 + ((i * 13) % 10);
    flower.position.set(Math.cos(a) * r, 0, Math.sin(a) * r - 2);
    flower.userData.phase = i;
    scatter.add(flower);
    flowerSpots.push(flower.position.clone());
    animated.push({ update: (delta, t) => { flower.rotation.z = Math.sin(t * 1.3 + flower.userData.phase) * 0.06; } });
  }
  for (let i = 0; i < 6; i++) {
    const mush = new THREE.Group();
    const stalk = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.09, 0.22, 6),
      new THREE.MeshStandardMaterial({ color: 0xfff3e0, roughness: 0.9 }));
    stalk.position.y = 0.11;
    const cap = new THREE.Mesh(new THREE.SphereGeometry(0.16, 8, 5, 0, Math.PI * 2, 0, Math.PI / 2),
      new THREE.MeshStandardMaterial({ color: 0xe53935, roughness: 0.8 }));
    cap.position.y = 0.2;
    mush.add(stalk, cap);
    const a = i * 2.2 + 0.4;
    mush.position.set(Math.cos(a) * (9 + i), 0, Math.sin(a) * (9 + i) - 3);
    scatter.add(mush);
  }
  root.add(scatter);

  // --- Pond with a lily pad, near the nest clearing ---
  const pond = new THREE.Group();
  const water = new THREE.Mesh(
    new THREE.CircleGeometry(2.4, 20),
    new THREE.MeshStandardMaterial({ color: PALETTE.water, roughness: 0.15, metalness: 0.1, transparent: true, opacity: 0.9 })
  );
  water.rotation.x = -Math.PI / 2;
  water.position.y = 0.02;
  const lily = new THREE.Mesh(
    new THREE.CircleGeometry(0.35, 8),
    new THREE.MeshStandardMaterial({ color: PALETTE.lily, roughness: 0.8, side: THREE.DoubleSide })
  );
  lily.rotation.x = -Math.PI / 2;
  lily.position.set(0.8, 0.04, 0.4);
  pond.add(water, lily);
  pond.position.set(6.5, 0, 2.5);
  animated.push({ update: (delta, t) => { lily.position.x = 0.8 + Math.sin(t * 0.5) * 0.25; } });
  root.add(pond);

  // --- Campfire by the nest (flicker light + flames + smoke) ---
  const campfire = new THREE.Group();
  const logMat = new THREE.MeshStandardMaterial({ color: PALETTE.trunk, roughness: 1 });
  for (let i = 0; i < 3; i++) {
    const log = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 1.1, 6), logMat);
    log.rotation.z = Math.PI / 2;
    log.rotation.y = (i / 3) * Math.PI;
    log.position.y = 0.1;
    campfire.add(log);
  }
  const flames = [];
  for (let i = 0; i < 3; i++) {
    const flame = new THREE.Mesh(
      new THREE.ConeGeometry(0.16 - i * 0.04, 0.5 - i * 0.1, 6),
      new THREE.MeshBasicMaterial({ color: i === 2 ? PALETTE.flameCore : PALETTE.flame, transparent: true, opacity: 0.9 })
    );
    flame.position.y = 0.35 + i * 0.08;
    campfire.add(flame);
    flames.push(flame);
  }
  const fireLight = new THREE.PointLight(0xffab40, 1.1, 9, 2);
  fireLight.position.y = 0.7;
  campfire.add(fireLight);
  campfire.position.set(nestPos.x - 4, 0, nestPos.z + 3);
  animated.push({
    update: (delta, t) => {
      for (let i = 0; i < flames.length; i++) {
        const s = 1 + Math.sin(t * (9 + i * 3) + i) * 0.18;
        flames[i].scale.set(s, 1 + Math.sin(t * (7 + i * 2)) * 0.22, s);
      }
      fireLight.intensity = 1.0 + Math.sin(t * 11) * 0.18 + Math.sin(t * 23) * 0.1;
    },
  });
  root.add(campfire);

  // --- Butterflies (wander between flowers; a burst more in the meadow) ---
  const butterflies = new THREE.Group();
  const butterflyList = [];
  function addButterfly(center, range, colorIdx) {
    const b = new THREE.Group();
    const mat = new THREE.MeshBasicMaterial({ color: PALETTE.butterfly[colorIdx % PALETTE.butterfly.length], side: THREE.DoubleSide });
    const wingL = new THREE.Mesh(new THREE.PlaneGeometry(0.16, 0.22), mat);
    wingL.position.x = -0.08;
    const wingR = wingL.clone();
    wingR.position.x = 0.08;
    b.add(wingL, wingR);
    b.userData = { wings: [wingL, wingR], center, range, phase: Math.random() * 9, speed: 0.5 + Math.random() * 0.4 };
    butterflies.add(b);
    butterflyList.push(b);
  }
  for (let i = 0; i < 5; i++) {
    addButterfly(flowerSpots[i * 4] || new THREE.Vector3(2, 0, 2), 2.5, i);
  }
  animated.push({
    update: (delta, t) => {
      for (const b of butterflyList) {
        const { center, range, phase, speed, wings } = b.userData;
        const a = t * speed + phase;
        b.position.set(
          center.x + Math.sin(a) * range + Math.sin(a * 2.3) * 0.5,
          0.7 + Math.sin(a * 1.7) * 0.35,
          center.z + Math.cos(a * 0.8) * range
        );
        b.rotation.y = a;
        const flap = Math.sin(t * 16 + phase) * 1.0;
        wings[0].rotation.y = flap;
        wings[1].rotation.y = -flap;
      }
    },
  });
  root.add(butterflies);

  // --- Fireflies (grove; hidden until unlocked) ---
  const fireflies = new THREE.Group();
  fireflies.visible = false;
  const fireflyList = [];
  const fireflyMat = new THREE.MeshBasicMaterial({ color: PALETTE.firefly, transparent: true });
  for (let i = 0; i < 12; i++) {
    const f = new THREE.Mesh(new THREE.SphereGeometry(0.05, 5, 4), fireflyMat.clone());
    f.userData.phase = i * 1.7;
    fireflies.add(f);
    fireflyList.push(f);
  }
  fireflies.position.set(-14, 0, -12);   // over the grove
  animated.push({
    update: (delta, t) => {
      if (!fireflies.visible) return;
      for (const f of fireflyList) {
        const p = f.userData.phase;
        f.position.set(
          Math.sin(t * 0.4 + p) * 4.5,
          0.6 + Math.sin(t * 0.9 + p * 2) * 0.8 + 0.8,
          Math.cos(t * 0.5 + p * 1.3) * 4.5
        );
        f.material.opacity = 0.35 + (Math.sin(t * 2.2 + p * 3) + 1) * 0.32;
      }
    },
  });
  root.add(fireflies);

  // --- Gentle sparkle motes rising around the nest (pre-hatch wonder) ---
  const motes = new THREE.Group();
  const moteList = [];
  const moteMat = new THREE.MeshBasicMaterial({ color: 0xffe082, transparent: true });
  for (let i = 0; i < 8; i++) {
    const m = new THREE.Mesh(new THREE.SphereGeometry(0.035, 5, 4), moteMat.clone());
    m.userData.phase = i / 8;
    motes.add(m);
    moteList.push(m);
  }
  motes.position.copy(nestPos);
  animated.push({
    update: (delta, t) => {
      if (!motes.visible) return;
      for (const m of moteList) {
        const p = ((t * 0.1) + m.userData.phase) % 1;
        const a = m.userData.phase * Math.PI * 2 + t * 0.3;
        m.position.set(Math.cos(a) * 1.4, 0.5 + p * 2.2, Math.sin(a) * 1.4);
        m.material.opacity = 0.75 * Math.sin(p * Math.PI);
      }
    },
  });
  root.add(motes);

  function update(delta) {
    const t = performance.now() * 0.001;
    for (const a of animated) a.update(delta, t);
  }
  // Milestone-driven reveals.
  function showFireflies() { fireflies.visible = true; }
  function setEggMotes(on) { motes.visible = on; }
  return { root, update, showFireflies, setEggMotes, flowerSpots };
}
