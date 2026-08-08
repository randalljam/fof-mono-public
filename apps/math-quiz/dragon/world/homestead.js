import * as THREE from 'three';

// The growing homestead: nest upgrades that appear as lifetime Dragon Gems
// accumulate (sim/rewards.js decides WHICH are unlocked; this module only
// builds and reveals them). Same primitive flat-shaded language as the rest
// of the world, positioned around the nest at (0, 0, -2).
export function createHomestead(scene, { nestPos = new THREE.Vector3(0, 0, -2) } = {}) {
  const root = new THREE.Group();
  root.position.copy(nestPos);
  scene.add(root);
  const groups = new Map();
  const animated = [];

  // --- garden: a ring of bright flowers + little hedges ---
  const garden = new THREE.Group();
  const gardenColors = [0xff6b9d, 0xffd54f, 0x4fc3f7, 0xba68c8, 0xff8a65, 0xaed581];
  const stemMat = new THREE.MeshStandardMaterial({ color: 0x388e3c, roughness: 1 });
  for (let i = 0; i < 14; i++) {
    const a = (i / 14) * Math.PI * 2;
    const r = 3.6 + (i % 2) * 0.3;
    const flower = new THREE.Group();
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.035, 0.5, 4), stemMat);
    stem.position.y = 0.25;
    const head = new THREE.Mesh(
      new THREE.SphereGeometry(0.12, 6, 5),
      new THREE.MeshStandardMaterial({ color: gardenColors[i % gardenColors.length], roughness: 0.7 })
    );
    head.position.y = 0.55;
    flower.add(stem, head);
    flower.position.set(Math.cos(a) * r, 0, Math.sin(a) * r);
    garden.add(flower);
  }
  const hedgeMat = new THREE.MeshStandardMaterial({ color: 0x4a7c40, roughness: 1, flatShading: true });
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * Math.PI * 2 + 0.5;
    const hedge = new THREE.Mesh(new THREE.SphereGeometry(0.42, 7, 5), hedgeMat);
    hedge.scale.y = 0.7;
    hedge.position.set(Math.cos(a) * 4.4, 0.25, Math.sin(a) * 4.4);
    garden.add(hedge);
  }
  groups.set('garden', garden);

  // --- lights: lantern posts with warm glowing bulbs (one shared light) ---
  const lights = new THREE.Group();
  const postMat = new THREE.MeshStandardMaterial({ color: 0x6d4c41, roughness: 1 });
  const bulbMat = new THREE.MeshBasicMaterial({ color: 0xffe082 });
  const bulbs = [];
  const postAngles = [0.4, 1.9, 3.6, 5.1];
  for (const a of postAngles) {
    const post = new THREE.Group();
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.09, 2.1, 6), postMat);
    pole.position.y = 1.05;
    const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.14, 7, 5), bulbMat.clone());
    bulb.position.y = 2.15;
    post.add(pole, bulb);
    post.position.set(Math.cos(a) * 5.2, 0, Math.sin(a) * 5.2);
    lights.add(post);
    bulbs.push(bulb);
  }
  const lanternGlow = new THREE.PointLight(0xffd180, 0.7, 14, 2);
  lanternGlow.position.set(0, 2.4, 0);
  lights.add(lanternGlow);
  animated.push((delta, t) => {
    for (let i = 0; i < bulbs.length; i++) {
      const s = 1 + Math.sin(t * 2.4 + i * 1.7) * 0.14;
      bulbs[i].scale.setScalar(s);
    }
    lanternGlow.intensity = 0.65 + Math.sin(t * 1.8) * 0.1;
  });
  groups.set('lights', lights);

  // --- banners: strings of flags between the lantern posts ---
  const banners = new THREE.Group();
  const flagColors = [0xef5350, 0xffca28, 0x66bb6a, 0x42a5f5, 0xab47bc];
  const flagList = [];
  for (let s = 0; s < postAngles.length; s++) {
    const a1 = postAngles[s];
    const a2 = postAngles[(s + 1) % postAngles.length];
    const p1 = new THREE.Vector3(Math.cos(a1) * 5.2, 2.1, Math.sin(a1) * 5.2);
    const p2 = new THREE.Vector3(Math.cos(a2) * 5.2, 2.1, Math.sin(a2) * 5.2);
    for (let f = 1; f <= 4; f++) {
      const frac = f / 5;
      const flag = new THREE.Mesh(
        new THREE.ConeGeometry(0.14, 0.34, 3),
        new THREE.MeshBasicMaterial({ color: flagColors[(s * 4 + f) % flagColors.length], side: THREE.DoubleSide })
      );
      flag.rotation.x = Math.PI;   // point down like a pennant
      flag.position.lerpVectors(p1, p2, frac);
      flag.position.y = 2.05 - Math.sin(frac * Math.PI) * 0.25;   // string sag
      flag.userData.phase = s * 4 + f;
      banners.add(flag);
      flagList.push(flag);
    }
  }
  animated.push((delta, t) => {
    for (const f of flagList) f.rotation.z = Math.sin(t * 2.2 + f.userData.phase) * 0.18;
  });
  groups.set('banners', banners);

  // --- fountain: basin + bobbing water column + rim drops ---
  // The fountain is ALSO a nest quiz station: setFountainLevel(tier) drives its
  // look — 0 dry cracked basin, 1 running water (the gem reveal), 2 second
  // tier, 3 rainbow arch. Visibility stays with syncUpgrades/gem logic; the
  // station code in main.js force-shows it so the dry basin is findable.
  const fountain = new THREE.Group();
  const basinMat = new THREE.MeshStandardMaterial({ color: 0x90a4ae, roughness: 0.9, flatShading: true });
  const basin = new THREE.Mesh(new THREE.CylinderGeometry(1.1, 1.25, 0.45, 10), basinMat);
  basin.position.y = 0.22;
  const pool = new THREE.Mesh(
    new THREE.CircleGeometry(0.95, 12),
    new THREE.MeshStandardMaterial({ color: 0x4fc3f7, roughness: 0.15 })
  );
  pool.rotation.x = -Math.PI / 2;
  pool.position.y = 0.46;
  const jet = new THREE.Mesh(
    new THREE.CylinderGeometry(0.09, 0.16, 1.0, 6),
    new THREE.MeshStandardMaterial({ color: 0x81d4fa, roughness: 0.2, transparent: true, opacity: 0.85 })
  );
  jet.position.y = 0.95;
  const drops = [];
  for (let i = 0; i < 5; i++) {
    const d = new THREE.Mesh(new THREE.SphereGeometry(0.05, 5, 4),
      new THREE.MeshBasicMaterial({ color: 0xb3e5fc, transparent: true, opacity: 0.9 }));
    d.userData.phase = i / 5;
    fountain.add(d);
    drops.push(d);
  }
  // Tier 0 extras: cracks + a tuft of weeds so "dry old fountain" reads at a glance.
  const dryBits = new THREE.Group();
  const crackMat = new THREE.MeshBasicMaterial({ color: 0x546e7a });
  for (const [a, len] of [[0.4, 0.5], [2.3, 0.4], [4.4, 0.55]]) {
    const crack = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.3, len), crackMat);
    crack.position.set(Math.cos(a) * 1.15, 0.3, Math.sin(a) * 1.15);
    crack.rotation.y = -a;
    dryBits.add(crack);
  }
  const weedMat = new THREE.MeshStandardMaterial({ color: 0x8d9d4f, roughness: 1, side: THREE.DoubleSide });
  for (let i = 0; i < 3; i++) {
    const weed = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.4, 4), weedMat);
    weed.position.set(0.3 - i * 0.3, 0.6, 0.2 * (i - 1));
    weed.rotation.z = (i - 1) * 0.25;
    dryBits.add(weed);
  }
  fountain.add(dryBits);
  // Tier 2 extras: a smaller upper basin with its own little jet.
  const upperTier = new THREE.Group();
  const upperBasin = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.6, 0.3, 8), basinMat);
  upperBasin.position.y = 1.15;
  const upperPool = new THREE.Mesh(
    new THREE.CircleGeometry(0.42, 10),
    new THREE.MeshStandardMaterial({ color: 0x4fc3f7, roughness: 0.15 })
  );
  upperPool.rotation.x = -Math.PI / 2;
  upperPool.position.y = 1.31;
  const column = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.18, 0.75, 6), basinMat);
  column.position.y = 0.75;
  upperTier.add(upperBasin, upperPool, column);
  fountain.add(upperTier);
  // Tier 3 extras: a rainbow arching over the water.
  const rainbow = new THREE.Group();
  const rainbowColors = [0xef5350, 0xffca28, 0x66bb6a, 0x42a5f5];
  rainbowColors.forEach((c, i) => {
    const arc = new THREE.Mesh(
      new THREE.TorusGeometry(1.45 + i * 0.09, 0.045, 6, 24, Math.PI),
      new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0.75 })
    );
    arc.position.y = 0.5;
    rainbow.add(arc);
  });
  fountain.add(rainbow);
  let fountainLevel = 1;
  function setFountainLevel(tier) {
    fountainLevel = tier;
    const wet = tier >= 1;
    pool.visible = jet.visible = wet;
    for (const d of drops) d.visible = wet;
    dryBits.visible = tier === 0;
    basinMat.color.setHex(tier === 0 ? 0x8d8d84 : 0x90a4ae);
    upperTier.visible = tier >= 2;
    jet.position.y = tier >= 2 ? 1.75 : 0.95;
    jet.scale.setScalar(tier >= 2 ? 0.8 : 1);
    rainbow.visible = tier >= 3;
  }
  setFountainLevel(1);
  fountain.add(basin, pool, jet);
  fountain.position.set(6.2, 0, -3.5);
  animated.push((delta, t) => {
    jet.scale.y = (fountainLevel >= 2 ? 0.8 : 1) * (1 + Math.sin(t * 5) * 0.18);
    const topY = fountainLevel >= 2 ? 2.2 : 1.5;
    for (const d of drops) {
      const p = ((t * 0.5) + d.userData.phase) % 1;
      const a = d.userData.phase * Math.PI * 2 + t * 0.4;
      d.position.set(Math.cos(a) * 0.5 * p, topY - p * p * 1.0, Math.sin(a) * 0.5 * p);
      d.material.opacity = 0.9 * (1 - p * 0.6);
    }
  });
  groups.set('fountain', fountain);

  // --- statue: a golden dragon on a plinth, the 200-gem trophy ---
  const statue = new THREE.Group();
  const goldMat = new THREE.MeshStandardMaterial({
    color: 0xffc107, roughness: 0.35, metalness: 0.6,
    emissive: 0xff8f00, emissiveIntensity: 0.12, flatShading: true,
  });
  const plinth = new THREE.Mesh(
    new THREE.CylinderGeometry(0.7, 0.85, 0.6, 8),
    new THREE.MeshStandardMaterial({ color: 0x9e9e9e, roughness: 1, flatShading: true })
  );
  plinth.position.y = 0.3;
  const body = new THREE.Mesh(new THREE.ConeGeometry(0.42, 1.1, 7), goldMat);
  body.position.y = 1.15;
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.24, 7, 6), goldMat);
  head.position.set(0, 1.8, 0.12);
  const snout = new THREE.Mesh(new THREE.ConeGeometry(0.11, 0.3, 6), goldMat);
  snout.rotation.x = Math.PI / 2;
  snout.position.set(0, 1.76, 0.38);
  for (const side of [-1, 1]) {
    const wing = new THREE.Mesh(new THREE.PlaneGeometry(0.55, 0.8), goldMat);
    wing.position.set(side * 0.42, 1.35, -0.08);
    wing.rotation.y = side * 0.7;
    statue.add(wing);
  }
  statue.add(plinth, body, head, snout);
  statue.position.set(-6.2, 0, -4.5);
  animated.push((delta, t) => {
    goldMat.emissiveIntensity = 0.12 + (Math.sin(t * 1.5) + 1) * 0.05;
  });
  groups.set('statue', statue);

  for (const g of groups.values()) {
    g.visible = false;
    g.traverse((n) => { if (n.isMesh) n.castShadow = true; });
    root.add(g);
  }

  // The fountain doubles as a quiz station, so it must be findable (as a dry
  // basin) before its gem reveal. Kept out of syncUpgrades so gem crossings
  // still sparkle the others correctly.
  function showFountain() { fountain.visible = true; }

  // Reveal every upgrade in `ids`; returns the group positions of NEWLY shown
  // ones so the caller can sparkle them.
  function syncUpgrades(ids) {
    const revealed = [];
    for (const id of ids || []) {
      const g = groups.get(id);
      if (g && !g.visible) {
        g.visible = true;
        revealed.push(g.position.clone().add(root.position).add(new THREE.Vector3(0, 1, 0)));
      }
    }
    return revealed;
  }
  function update(delta) {
    const t = performance.now() * 0.001;
    for (const fn of animated) fn(delta, t);
  }
  return { root, syncUpgrades, update, setFountainLevel, showFountain, fountainGroup: fountain };
}
