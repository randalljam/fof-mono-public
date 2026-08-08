import * as THREE from 'three';
import {
  VOLCANO, TOTAL_BOULDERS, boulderPos, blockRadius, trailTarget, terrainHeightAt,
} from '../sim/volcano_quest.js';

// The volcano-climb blockades: five boulder clusters up Mount Ember's south
// face. Each is an interactable — main.js starts a quiz on click and calls
// clearNext() when the quiz is finished, which crumbles the lowest cluster.
// A sparkle trail (same language as the journey stones) marches from the nest
// to the next boulder, then to the summit.
export function createBoulders(scene, { nestPos = new THREE.Vector3(0, 0, -2) } = {}) {
  const root = new THREE.Group();
  scene.add(root);
  const rockMat = new THREE.MeshStandardMaterial({ color: 0xa89e93, roughness: 1, flatShading: true });
  const mossMat = new THREE.MeshStandardMaterial({ color: 0x8ba071, roughness: 1, flatShading: true });
  const stages = [];
  for (let k = 0; k < TOTAL_BOULDERS; k++) {
    const p = boulderPos(k);
    const group = new THREE.Group();
    const big = new THREE.Mesh(new THREE.DodecahedronGeometry(1.35), k % 2 ? mossMat : rockMat);
    big.position.y = 0.9;
    big.rotation.set(k * 0.7, k * 1.3, k * 0.4);
    big.castShadow = true;
    group.add(big);
    for (let r = 0; r < 3; r++) {
      const side = new THREE.Mesh(new THREE.DodecahedronGeometry(0.55 + (r % 2) * 0.25), r % 2 ? rockMat : mossMat);
      const a = (r / 3) * Math.PI * 2 + k;
      side.position.set(Math.cos(a) * 1.5, 0.35, Math.sin(a) * 1.5);
      side.rotation.set(r * 0.9 + k, r * 0.5, r * 1.2);
      side.castShadow = true;
      group.add(side);
    }
    group.position.set(p.x, p.y, p.z);
    root.add(group);
    stages.push({ k, group, dying: 0 });
  }

  // Sparkle trail: nest -> next boulder -> summit, hugging the terrain.
  const trail = { dots: [], on: false };
  const dotMat = new THREE.MeshBasicMaterial({ color: 0xffb74d, transparent: true });
  for (let i = 0; i < 40; i++) {
    const dot = new THREE.Mesh(new THREE.SphereGeometry(0.09, 5, 4), dotMat.clone());
    dot.visible = false;
    dot.userData.frac = i / 40;
    root.add(dot);
    trail.dots.push(dot);
  }

  let cleared = 0;
  function labelFor(k) {
    return `A boulder blocks the path! Do a quiz to smash it (${k + 1} of ${TOTAL_BOULDERS})`;
  }
  function sync(state) {
    const v = state.volcano || {};
    cleared = Math.max(0, Math.min(TOTAL_BOULDERS, v.cleared || 0));
    for (const s of stages) {
      if (s.k < cleared && !s.dying) s.group.visible = false;
    }
    trail.on = !!v.intro && !v.summited;
    for (const d of trail.dots) d.visible = trail.on;
  }
  // Crumble the lowest uncleared boulder; returns its position for effects.
  function clearNext() {
    if (cleared >= TOTAL_BOULDERS) return null;
    const s = stages[cleared];
    cleared += 1;
    s.dying = 1;
    return s.group.position.clone().add(new THREE.Vector3(0, 1, 0));
  }
  function nextStage() { return cleared < TOTAL_BOULDERS ? cleared : null; }
  function currentBlockRadius() { return blockRadius(cleared); }
  function interactables() {
    return stages.map((s) => ({ k: s.k, mesh: s.group, label: labelFor(s.k) }));
  }
  function update(delta) {
    const t = performance.now() * 0.001;
    for (const s of stages) {
      if (!s.dying || !s.group.visible) continue;
      s.dying = Math.min(1.6, s.dying + delta * 2.2);
      const sc = Math.max(0.001, 1 - (s.dying - 1) * 1.8);
      if (s.dying > 1) s.group.scale.setScalar(sc);
      s.group.rotation.y += delta * 3;
      if (sc <= 0.02) { s.group.visible = false; s.dying = 0; s.group.scale.setScalar(1); }
    }
    if (!trail.on) return;
    const to = trailTarget(cleared);
    const from = nestPos;
    for (const dot of trail.dots) {
      const march = ((t * 0.05) + dot.userData.frac) % 1;
      const x = from.x + (to.x - from.x) * march;
      const z = from.z + (to.z - from.z) * march;
      dot.position.set(x, terrainHeightAt(x, z) + 0.3 + Math.sin(march * 40) * 0.12, z);
      dot.material.opacity = 0.85 * Math.sin(march * Math.PI);
    }
  }
  return {
    root, sync, clearNext, nextStage, interactables, update,
    blockRadius: currentBlockRadius,
    volcanoCenter: new THREE.Vector3(VOLCANO.x, 0, VOLCANO.z),
  };
}
