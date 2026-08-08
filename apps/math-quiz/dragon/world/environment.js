import * as THREE from 'three';

export function createEnvironment(scene) {
  const root = new THREE.Group();
  scene.add(root);
  const nest = new THREE.Group();
  nest.position.set(0, 0, -2);
  const nestBase = new THREE.Mesh(
    new THREE.CylinderGeometry(2.2, 2.6, 0.4, 16),
    new THREE.MeshStandardMaterial({ color: 0x8b6914, roughness: 0.95 })
  );
  nestBase.position.y = 0.2;
  nestBase.receiveShadow = true;
  nest.add(nestBase);
  const straw = new THREE.Mesh(
    new THREE.TorusGeometry(1.8, 0.15, 8, 24),
    new THREE.MeshStandardMaterial({ color: 0xc4a035, roughness: 1 })
  );
  straw.rotation.x = Math.PI / 2;
  straw.position.y = 0.35;
  nest.add(straw);
  root.add(nest);
  const trees = [];
  for (let i = 0; i < 8; i++) {
    const tree = new THREE.Group();
    const trunk = new THREE.Mesh(
      new THREE.CylinderGeometry(0.25, 0.35, 2.5, 6),
      new THREE.MeshStandardMaterial({ color: 0x5c4033 })
    );
    trunk.position.y = 1.25;
    trunk.castShadow = true;
    const leaves = new THREE.Mesh(
      new THREE.ConeGeometry(1.4, 3, 8),
      new THREE.MeshStandardMaterial({ color: 0x2d6a3e })
    );
    leaves.position.y = 3.2;
    leaves.castShadow = true;
    tree.add(trunk, leaves);
    const angle = (i / 8) * Math.PI * 2;
    tree.position.set(Math.cos(angle) * 14, 0, Math.sin(angle) * 14 - 4);
    root.add(tree);
    trees.push(tree);
  }
  // Locked-area gates: little wooden arches with a hanging sign (replaced the
  // old solid slabs, which read as rendering glitches).
  function buildGateArch(rotationY = 0) {
    const gate = new THREE.Group();
    const wood = new THREE.MeshStandardMaterial({ color: 0x795548, roughness: 1 });
    for (const x of [-1.6, 1.6]) {
      const post = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.18, 2.6, 6), wood);
      post.position.set(x, 1.3, 0);
      post.castShadow = true;
      gate.add(post);
    }
    const beam = new THREE.Mesh(new THREE.BoxGeometry(3.9, 0.24, 0.24), wood);
    beam.position.y = 2.55;
    gate.add(beam);
    const sign = new THREE.Mesh(
      new THREE.BoxGeometry(1.1, 0.7, 0.08),
      new THREE.MeshStandardMaterial({ color: 0xd7ccc8, roughness: 0.9 })
    );
    sign.position.y = 1.9;
    gate.add(sign);
    gate.rotation.y = rotationY;
    return gate;
  }
  const meadowGate = buildGateArch(Math.PI / 2);
  meadowGate.position.set(8, 0, -6);
  meadowGate.name = 'meadow-gate';
  meadowGate.visible = false;
  root.add(meadowGate);
  const meadow = new THREE.Group();
  meadow.name = 'meadow-area';
  meadow.visible = false;
  meadow.position.set(14, 0, -8);
  const meadowGround = new THREE.Mesh(
    new THREE.CircleGeometry(8, 24),
    new THREE.MeshStandardMaterial({ color: 0x7cb342 })
  );
  meadowGround.rotation.x = -Math.PI / 2;
  meadowGround.receiveShadow = true;
  meadow.add(meadowGround);
  // A meadow should look like one: flower drifts + grass tufts.
  const petalColors = [0xff6b9d, 0xffd54f, 0xba68c8, 0xff8a65, 0x4fc3f7, 0xfff176];
  const meadowStemMat = new THREE.MeshStandardMaterial({ color: 0x388e3c, roughness: 1 });
  for (let i = 0; i < 26; i++) {
    const flower = new THREE.Group();
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.03, 0.45, 4), meadowStemMat);
    stem.position.y = 0.22;
    const head = new THREE.Mesh(
      new THREE.SphereGeometry(0.1, 6, 5),
      new THREE.MeshStandardMaterial({ color: petalColors[i % petalColors.length], roughness: 0.7 })
    );
    head.position.y = 0.5;
    flower.add(stem, head);
    const a = (i / 26) * Math.PI * 2;
    const r = 1.5 + ((i * 17) % 11) * 0.55;
    flower.position.set(Math.cos(a) * r, 0.01, Math.sin(a) * r);
    meadow.add(flower);
  }
  const tuftMat = new THREE.MeshStandardMaterial({ color: 0x9ccc65, roughness: 1, side: THREE.DoubleSide });
  for (let i = 0; i < 14; i++) {
    const tuft = new THREE.Mesh(new THREE.ConeGeometry(0.09, 0.5, 4), tuftMat);
    const a = (i / 14) * Math.PI * 2 + 0.9;
    const r = 2.5 + ((i * 23) % 9) * 0.5;
    tuft.position.set(Math.cos(a) * r, 0.25, Math.sin(a) * r);
    tuft.rotation.z = ((i * 7) % 5 - 2) * 0.08;
    meadow.add(tuft);
  }
  root.add(meadow);
  const groveGate = buildGateArch(Math.PI / 2);
  groveGate.position.set(-8, 0, -10);
  groveGate.name = 'grove-gate';
  groveGate.visible = false;
  root.add(groveGate);
  const grove = new THREE.Group();
  grove.name = 'grove-area';
  grove.visible = false;
  grove.position.set(-14, 0, -12);
  const grovePool = new THREE.Mesh(
    new THREE.CircleGeometry(4, 20),
    new THREE.MeshStandardMaterial({ color: 0x4fc3f7, roughness: 0.2, metalness: 0.1 })
  );
  grovePool.rotation.x = -Math.PI / 2;
  grovePool.position.y = 0.02;
  grove.add(grovePool);
  // The grove is older and darker: a ring of deep-green trees + glow mushrooms.
  const groveTrunkMat = new THREE.MeshStandardMaterial({ color: 0x4e342e, roughness: 1 });
  const groveLeafMat = new THREE.MeshStandardMaterial({ color: 0x1b5e20, roughness: 1, flatShading: true });
  for (let i = 0; i < 7; i++) {
    const tree = new THREE.Group();
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.42, 3.2, 6), groveTrunkMat);
    trunk.position.y = 1.6;
    trunk.castShadow = true;
    const leaves = new THREE.Mesh(new THREE.ConeGeometry(1.7, 3.6, 7), groveLeafMat);
    leaves.position.y = 4.2;
    leaves.castShadow = true;
    tree.add(trunk, leaves);
    const a = (i / 7) * Math.PI * 2 + 0.3;
    tree.position.set(Math.cos(a) * 6.5, 0, Math.sin(a) * 6.5);
    grove.add(tree);
  }
  const glowCapMat = new THREE.MeshStandardMaterial({ color: 0x80deea, emissive: 0x26c6da, emissiveIntensity: 0.7, roughness: 0.6 });
  for (let i = 0; i < 5; i++) {
    const mush = new THREE.Group();
    const stalk = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.08, 0.2, 5),
      new THREE.MeshStandardMaterial({ color: 0xe0f7fa, roughness: 0.9 }));
    stalk.position.y = 0.1;
    const cap = new THREE.Mesh(new THREE.SphereGeometry(0.14, 7, 5, 0, Math.PI * 2, 0, Math.PI / 2), glowCapMat);
    cap.position.y = 0.18;
    mush.add(stalk, cap);
    const a = i * 1.5 + 0.8;
    mush.position.set(Math.cos(a) * 5, 0, Math.sin(a) * 5);
    grove.add(mush);
  }
  root.add(grove);
  // Whispering Hills (south): grassy mounds + stepping stones, opened by the
  // 80% "jump" milestone — somewhere to hop with the new super-jumps.
  const hills = new THREE.Group();
  hills.name = 'hills-area';
  hills.visible = false;
  hills.position.set(3, 0, 16);
  const moundMat = new THREE.MeshStandardMaterial({ color: 0x6a9c50, roughness: 1, flatShading: true });
  const moundSpecs = [
    { x: 0, z: 0, r: 4.5, h: 2.2 }, { x: -5, z: 2, r: 3, h: 1.4 }, { x: 5, z: 3, r: 3.5, h: 1.7 },
  ];
  for (const m of moundSpecs) {
    const mound = new THREE.Mesh(new THREE.SphereGeometry(m.r, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2), moundMat);
    mound.scale.y = m.h / m.r;
    mound.position.set(m.x, 0, m.z);
    mound.receiveShadow = true;
    mound.castShadow = true;
    hills.add(mound);
  }
  const stepMat = new THREE.MeshStandardMaterial({ color: 0xbdbdbd, roughness: 1, flatShading: true });
  for (let i = 0; i < 5; i++) {
    const step = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.6, 0.25, 6), stepMat);
    step.position.set(-1.5 + i * 0.8, 0.12 + i * 0.05, -4 + i * 0.9);
    hills.add(step);
  }
  root.add(hills);
  const hillsGate = buildGateArch(0);
  hillsGate.position.set(2, 0, 9);
  hillsGate.name = 'hills-gate';
  hillsGate.visible = false;
  root.add(hillsGate);
  // Dirt paths: stepping-patch trails from the nest toward each gate and the
  // volcano trailhead, so the world reads as a place with roads to follow.
  const pathMat = new THREE.MeshStandardMaterial({ color: 0xc9a46b, roughness: 1 });
  function buildPath(from, to, gap = 1.6) {
    const dir = new THREE.Vector3().subVectors(to, from);
    const len = dir.length();
    dir.normalize();
    const steps = Math.floor(len / gap);
    for (let i = 1; i <= steps; i++) {
      const patch = new THREE.Mesh(new THREE.CircleGeometry(0.34 + (i % 3) * 0.08, 7), pathMat);
      patch.rotation.x = -Math.PI / 2;
      const p = from.clone().addScaledVector(dir, i * gap);
      // small deterministic wobble so the trail meanders
      patch.position.set(p.x + Math.sin(i * 2.1) * 0.35, 0.015, p.z + Math.cos(i * 1.7) * 0.35);
      patch.receiveShadow = true;
      root.add(patch);
    }
  }
  const nestEdge = new THREE.Vector3(0, 0, -2);
  buildPath(nestEdge.clone().add(new THREE.Vector3(2.5, 0, -1)), new THREE.Vector3(8, 0, -6));    // meadow gate
  buildPath(nestEdge.clone().add(new THREE.Vector3(-2.5, 0, -1.5)), new THREE.Vector3(-8, 0, -10)); // grove gate
  buildPath(nestEdge.clone().add(new THREE.Vector3(0.5, 0, 2.5)), new THREE.Vector3(2, 0, 9));    // hills gate
  buildPath(nestEdge.clone().add(new THREE.Vector3(-0.5, 0, -3)), new THREE.Vector3(0, 0, -26));  // volcano trailhead
  function unlockArea(name) {
    if (name === 'meadow') { meadow.visible = true; meadowGate.visible = false; }
    if (name === 'grove') { grove.visible = true; groveGate.visible = false; }
    if (name === 'hills') { hills.visible = true; hillsGate.visible = false; }
  }
  function showGates() {
    meadowGate.visible = true;
    groveGate.visible = true;
    hillsGate.visible = true;
  }
  return { root, nest, trees, meadow, grove, hills, unlockArea, showGates };
}
