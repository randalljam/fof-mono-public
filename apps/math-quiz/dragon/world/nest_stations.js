import * as THREE from 'three';

// Nest quiz stations, world side: two writable wooden signs (canvas-texture
// text the player paints after a quiz) plus the level-up looks for the nest
// and the ring of trees. Which station is at which level lives in
// sim/stations.js; this module only builds and reveals the visuals.
// (The third grow station — the fountain — is homestead.js's, via setFountainLevel.)

function makeSignBoard() {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext('2d');
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  function draw(text) {
    ctx.fillStyle = '#f0dfb6';
    ctx.fillRect(0, 0, 512, 256);
    ctx.strokeStyle = '#8d6e63';
    ctx.lineWidth = 14;
    ctx.strokeRect(7, 7, 498, 242);
    ctx.fillStyle = '#4e342e';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const words = String(text || '').split(' ').filter(Boolean);
    if (!words.length) {
      // Blank sign: a faint dashed line + pencil, inviting the first quiz.
      ctx.strokeStyle = '#c9b58a';
      ctx.lineWidth = 4;
      ctx.setLineDash([14, 10]);
      ctx.strokeRect(60, 80, 392, 96);
      ctx.setLineDash([]);
      ctx.font = '64px sans-serif';
      ctx.fillText('✏️', 256, 130);
      texture.needsUpdate = true;
      return;
    }
    // Wrap into up to 3 lines; shrink the font for long messages.
    const lines = [];
    let line = '';
    for (const w of words) {
      const next = line ? `${line} ${w}` : w;
      if (next.length > 14 && line) { lines.push(line); line = w; } else line = next;
    }
    lines.push(line);
    const size = lines.length >= 3 ? 52 : lines.length === 2 ? 62 : 72;
    ctx.font = `bold ${size}px "Comic Sans MS", "Chalkboard SE", sans-serif`;
    const startY = 128 - (lines.length - 1) * (size * 0.62);
    lines.forEach((l, i) => ctx.fillText(l, 256, startY + i * size * 1.24, 470));
    texture.needsUpdate = true;
  }
  draw('');
  return { texture, draw };
}
function buildSign() {
  const sign = new THREE.Group();
  const wood = new THREE.MeshStandardMaterial({ color: 0x795548, roughness: 1 });
  const post = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.12, 1.5, 6), wood);
  post.position.y = 0.75;
  post.castShadow = true;
  const board = new THREE.Mesh(new THREE.BoxGeometry(1.7, 0.95, 0.09), wood);
  board.position.y = 1.65;
  board.castShadow = true;
  const { texture, draw } = makeSignBoard();
  const face = new THREE.Mesh(
    new THREE.PlaneGeometry(1.58, 0.83),
    new THREE.MeshStandardMaterial({ map: texture, roughness: 0.9 })
  );
  face.position.set(0, 1.65, 0.055);
  sign.add(post, board, face);
  return { group: sign, draw };
}

export function createNestStations(scene, { nestGroup, trees, nestPos = new THREE.Vector3(0, 0, -2) } = {}) {
  const animated = [];

  // --- signs: one by the meadow path, one by the grove path, facing the nest ---
  // Both sit outside the lantern ring and off the dirt-path lines; keep them
  // away from the spawn point (2, 1.6, 4) so they never block the first walk
  // to the egg (the e2e sweep found the original spot occluding it).
  const signs = new Map();
  const SIGN_SPOTS = {
    'sign-welcome': nestPos.clone().add(new THREE.Vector3(5.0, 0, -1.0)),
    'sign-dragon': nestPos.clone().add(new THREE.Vector3(-4.6, 0, -3.2)),
  };
  for (const [id, pos] of Object.entries(SIGN_SPOTS)) {
    const { group, draw } = buildSign();
    group.position.copy(pos);
    group.lookAt(nestPos.x, 0, nestPos.z);
    scene.add(group);
    signs.set(id, { group, draw, pos });
  }
  function setSignText(id, text) {
    const s = signs.get(id);
    if (s) s.draw(text);
  }
  function signGroups() {
    return [...signs.entries()].map(([id, s]) => ({ id, group: s.group }));
  }
  function signPosition(id) {
    const s = signs.get(id);
    return s ? s.pos.clone().add(new THREE.Vector3(0, 1.6, 0)) : nestPos.clone();
  }

  // --- nest levels: 1 cushions + fresh straw, 2 canopy, 3 golden straw + orbs ---
  const nestLevels = [];
  {
    const l1 = new THREE.Group();
    const cushionColors = [0xef9a9a, 0x90caf9, 0xfff59d, 0xa5d6a7];
    cushionColors.forEach((c, i) => {
      const cushion = new THREE.Mesh(
        new THREE.SphereGeometry(0.32, 8, 6),
        new THREE.MeshStandardMaterial({ color: c, roughness: 0.9 })
      );
      cushion.scale.y = 0.55;
      const a = (i / cushionColors.length) * Math.PI * 2 + 0.6;
      cushion.position.set(Math.cos(a) * 1.25, 0.5, Math.sin(a) * 1.25);
      cushion.castShadow = true;
      l1.add(cushion);
    });
    const freshStraw = new THREE.Mesh(
      new THREE.TorusGeometry(2.05, 0.13, 8, 24),
      new THREE.MeshStandardMaterial({ color: 0xdec26b, roughness: 1 })
    );
    freshStraw.rotation.x = Math.PI / 2;
    freshStraw.position.y = 0.42;
    l1.add(freshStraw);
    nestLevels.push(l1);

    const l2 = new THREE.Group();
    const poleMat = new THREE.MeshStandardMaterial({ color: 0x6d4c41, roughness: 1 });
    for (let i = 0; i < 4; i++) {
      const a = (i / 4) * Math.PI * 2 + Math.PI / 4;
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 2.9, 6), poleMat);
      pole.position.set(Math.cos(a) * 2.5, 1.45, Math.sin(a) * 2.5);
      l2.add(pole);
    }
    const roof = new THREE.Mesh(
      new THREE.ConeGeometry(3.5, 1.3, 4),
      new THREE.MeshStandardMaterial({ color: 0xff8a65, roughness: 0.9, flatShading: true, side: THREE.DoubleSide })
    );
    roof.position.y = 3.4;
    roof.rotation.y = Math.PI / 4;
    l2.add(roof);
    nestLevels.push(l2);

    const l3 = new THREE.Group();
    const goldStraw = new THREE.Mesh(
      new THREE.TorusGeometry(1.8, 0.16, 8, 24),
      new THREE.MeshStandardMaterial({
        color: 0xffd54f, roughness: 0.5, emissive: 0xff8f00, emissiveIntensity: 0.18,
      })
    );
    goldStraw.rotation.x = Math.PI / 2;
    goldStraw.position.y = 0.5;
    l3.add(goldStraw);
    const orbs = [];
    for (let i = 0; i < 6; i++) {
      const orb = new THREE.Mesh(
        new THREE.SphereGeometry(0.09, 7, 5),
        new THREE.MeshBasicMaterial({ color: 0xfff59d })
      );
      orb.userData.phase = (i / 6) * Math.PI * 2;
      l3.add(orb);
      orbs.push(orb);
    }
    animated.push((delta, t) => {
      for (const o of orbs) {
        const a = o.userData.phase + t * 0.5;
        o.position.set(Math.cos(a) * 2.3, 1.2 + Math.sin(t * 1.6 + o.userData.phase) * 0.3, Math.sin(a) * 2.3);
      }
    });
    nestLevels.push(l3);
    for (const g of nestLevels) {
      g.visible = false;
      nestGroup.add(g);
    }
  }

  // --- tree levels: 1 blossoms, 2 fruit + taller trees, 3 hanging lanterns ---
  const treeLevels = [[], [], []];
  {
    const blossomMat = new THREE.MeshStandardMaterial({ color: 0xf48fb1, roughness: 0.7 });
    const fruitMat = new THREE.MeshStandardMaterial({ color: 0xffb74d, roughness: 0.6 });
    const lanternMat = new THREE.MeshBasicMaterial({ color: 0xffe082 });
    (trees || []).forEach((tree, ti) => {
      const l1 = new THREE.Group();
      for (let i = 0; i < 4; i++) {
        const b = new THREE.Mesh(new THREE.SphereGeometry(0.14, 6, 5), blossomMat);
        const a = (i / 4) * Math.PI * 2 + ti;
        const y = 2.4 + (i % 3) * 0.55;
        const r = 1.15 * (1 - (y - 2.0) / 3.2);
        b.position.set(Math.cos(a) * r, y, Math.sin(a) * r);
        l1.add(b);
      }
      const l2 = new THREE.Group();
      for (let i = 0; i < 3; i++) {
        const f = new THREE.Mesh(new THREE.SphereGeometry(0.16, 6, 5), fruitMat);
        const a = (i / 3) * Math.PI * 2 + ti * 1.3 + 0.7;
        const y = 2.2 + (i % 2) * 0.6;
        const r = 1.1 * (1 - (y - 2.0) / 3.2);
        f.position.set(Math.cos(a) * r, y, Math.sin(a) * r);
        l2.add(f);
      }
      const l3 = new THREE.Group();
      const string = new THREE.Mesh(
        new THREE.CylinderGeometry(0.015, 0.015, 0.5, 3),
        new THREE.MeshBasicMaterial({ color: 0xbcaaa4 })
      );
      string.position.set(0.75, 2.35, 0);
      const lantern = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.3, 0.22), lanternMat);
      lantern.position.set(0.75, 2.0, 0);
      l3.add(string, lantern);
      l3.rotation.y = ti * 0.9;
      tree.add(l1, l2, l3);
      treeLevels[0].push(l1);
      treeLevels[1].push(l2);
      treeLevels[2].push(l3);
    });
  }
  function applyLevels({ nest = 0, trees: treeLevel = 0 } = {}) {
    nestLevels.forEach((g, i) => { g.visible = nest >= i + 1; });
    treeLevels.forEach((groupsAtLevel, i) => {
      for (const g of groupsAtLevel) g.visible = treeLevel >= i + 1;
    });
    // Level 2 trees stand taller (scale once, idempotent).
    for (const tree of trees || []) {
      const target = treeLevel >= 2 ? 1.12 : 1;
      tree.scale.setScalar(target);
    }
  }
  applyLevels({});
  function stationPosition(id) {
    if (id === 'nest') return nestPos.clone().add(new THREE.Vector3(0, 1.2, 0));
    if (id === 'trees' && trees && trees.length) {
      return trees[0].position.clone().add(new THREE.Vector3(0, 3, 0));
    }
    return signPosition(id);
  }
  function update(delta) {
    const t = performance.now() * 0.001;
    for (const fn of animated) fn(delta, t);
  }
  return { setSignText, signGroups, signPosition, applyLevels, stationPosition, update };
}
