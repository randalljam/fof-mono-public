import * as THREE from 'three';

// The journey layer: after the hatch, each milestone opens the next leg of the
// "dragon road" home — a sparkle trail from the nest to a Story Stone in the
// newly-unlocked area. Clicking the stone (with the dragon along) plays that
// leg's story and marks it visited. The grove leg carries the old beacon that
// the finale lights.
const STONES = [
  { id: 'meadow', label: 'Story Stone (click!)', pos: new THREE.Vector3(16, 0, -6), unlock: 'wings' },
  { id: 'hills', label: 'Story Stone (click!)', pos: new THREE.Vector3(3, 0, 13), unlock: 'jump' },
  { id: 'grove', label: 'Story Stone (click!)', pos: new THREE.Vector3(-15, 0, -9), unlock: 'fire' },
];

export function createJourney(scene, { nestPos = new THREE.Vector3(0, 0, -2) } = {}) {
  const root = new THREE.Group();
  scene.add(root);
  const stones = new Map();
  const runeMat = () => new THREE.MeshStandardMaterial({
    color: 0x78909c, roughness: 0.9, flatShading: true,
    emissive: 0x4dd0e1, emissiveIntensity: 0.0,
  });
  for (const spec of STONES) {
    const group = new THREE.Group();
    const mat = runeMat();
    const slab = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.6, 1.5, 5), mat);
    slab.position.y = 0.75;
    slab.rotation.y = 0.4;
    slab.castShadow = true;
    const rune = new THREE.Mesh(
      new THREE.TorusGeometry(0.16, 0.045, 6, 12),
      new THREE.MeshBasicMaterial({ color: 0x4dd0e1, transparent: true, opacity: 0.0 })
    );
    rune.position.set(0, 1.05, 0.28);
    group.add(slab, rune);
    group.position.copy(spec.pos);
    group.visible = false;
    root.add(group);
    stones.set(spec.id, { spec, group, mat, rune, visited: false, active: false });
  }

  // Sparkle trail from the nest to the active stone: dots marching outward.
  const trail = { dots: [], target: null };
  const dotMat = new THREE.MeshBasicMaterial({ color: 0xffe082, transparent: true });
  for (let i = 0; i < 14; i++) {
    const dot = new THREE.Mesh(new THREE.SphereGeometry(0.07, 5, 4), dotMat.clone());
    dot.visible = false;
    dot.userData.frac = i / 14;
    root.add(dot);
    trail.dots.push(dot);
  }
  function setTrailTarget(stoneId) {
    trail.target = stoneId ? stones.get(stoneId) : null;
    for (const d of trail.dots) d.visible = !!trail.target;
  }

  // The old beacon (grove): a pillar with a bowl, cold until the finale.
  const beacon = new THREE.Group();
  const pillar = new THREE.Mesh(
    new THREE.CylinderGeometry(0.35, 0.5, 2.6, 6),
    new THREE.MeshStandardMaterial({ color: 0x6d6d6d, roughness: 1, flatShading: true })
  );
  pillar.position.y = 1.3;
  pillar.castShadow = true;
  const bowl = new THREE.Mesh(
    new THREE.CylinderGeometry(0.55, 0.35, 0.35, 8),
    new THREE.MeshStandardMaterial({ color: 0x5a5a5a, roughness: 1, flatShading: true })
  );
  bowl.position.y = 2.75;
  beacon.add(pillar, bowl);
  const beaconFlames = [];
  for (let i = 0; i < 2; i++) {
    const flame = new THREE.Mesh(
      new THREE.ConeGeometry(0.3 - i * 0.12, 0.9 - i * 0.25, 6),
      new THREE.MeshBasicMaterial({ color: i ? 0xffeb3b : 0xff9800, transparent: true, opacity: 0.95 })
    );
    flame.position.y = 3.3 + i * 0.1;
    flame.visible = false;
    beacon.add(flame);
    beaconFlames.push(flame);
  }
  const beaconLight = new THREE.PointLight(0xffab40, 0, 16, 2);
  beaconLight.position.y = 3.4;
  beacon.add(beaconLight);
  beacon.position.set(-13, 0, -15);
  beacon.visible = false;
  root.add(beacon);
  let beaconLit = false;
  function showBeacon() { beacon.visible = true; }
  function lightBeacon() {
    beaconLit = true;
    beacon.visible = true;
    for (const f of beaconFlames) f.visible = true;
    beaconLight.intensity = 2.2;
  }

  // Reveal stones for unlocked milestones; aim the trail at the current target.
  function refresh(state) {
    const celebrated = new Set(state.celebratedIds || []);
    const visited = new Set(state.visitedStones || []);
    let target = null;
    for (const [id, s] of stones) {
      const unlocked = celebrated.has(s.spec.unlock);
      s.group.visible = unlocked;
      s.visited = visited.has(id);
      s.active = unlocked && !s.visited;
      s.rune.material.opacity = s.visited ? 0.25 : unlocked ? 0.85 : 0;
      if (!target && s.active) target = id;
    }
    if (celebrated.has('fire')) showBeacon();
    if (state.rideUnlocked) lightBeacon();
    setTrailTarget(target);
  }
  function markVisited(state, stoneId) {
    if (!state.visitedStones) state.visitedStones = [];
    if (!state.visitedStones.includes(stoneId)) state.visitedStones.push(stoneId);
    refresh(state);
    return state;
  }
  function interactables() {
    return Array.from(stones.values()).map((s) => ({ id: s.spec.id, mesh: s.group, label: s.spec.label }));
  }
  function stonePosition(stoneId) {
    const s = stones.get(stoneId);
    return s ? s.group.position.clone().add(new THREE.Vector3(0, 1.1, 0)) : null;
  }
  function update(delta) {
    const t = performance.now() * 0.001;
    for (const s of stones.values()) {
      if (!s.group.visible) continue;
      s.mat.emissiveIntensity = s.active ? 0.35 + (Math.sin(t * 2.4) + 1) * 0.25 : s.visited ? 0.05 : 0;
      s.rune.rotation.z = t * (s.active ? 0.8 : 0.1);
    }
    if (trail.target) {
      const from = nestPos;
      const to = trail.target.group.position;
      for (const dot of trail.dots) {
        const march = ((t * 0.12) + dot.userData.frac) % 1;
        dot.position.set(
          from.x + (to.x - from.x) * march,
          0.25 + Math.sin(march * Math.PI) * 0.35 + (to.y > 0 ? to.y * march : 0),
          from.z + (to.z - from.z) * march
        );
        dot.material.opacity = 0.85 * Math.sin(march * Math.PI);
      }
    }
    if (beaconLit) {
      for (let i = 0; i < beaconFlames.length; i++) {
        const s = 1 + Math.sin(t * (8 + i * 3)) * 0.2;
        beaconFlames[i].scale.set(s, 1 + Math.sin(t * 6 + i) * 0.25, s);
      }
      beaconLight.intensity = 2.0 + Math.sin(t * 9) * 0.4;
    }
  }
  return { root, refresh, markVisited, interactables, stonePosition, lightBeacon, update, STONES };
}
