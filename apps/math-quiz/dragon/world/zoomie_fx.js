import * as THREE from 'three';

const RUN_RADIUS = 2.0;
const RUN_SPEED = 2.6;
const BANK = 0.3;
const CHASE_SPEED = 24; // 2x player moveSpeed
const CATCH_RADIUS = 3.5;
const CHASE_MAX_S = 20;
const FIRST_LEG_MIN_R = 45;
const FIRST_LEG_MAX_R = 55;
const WORLD_TARGET_R = 55;
const NEST_OVERSHOOT = 10;
const TARGET_EPS = 0.5;
const VOLCANO_X = 0;
const VOLCANO_Z = -92;
const VOLCANO_SAFE_R = 26;
const VORTEX_COUNT = 36;
const DUST_COUNT = 8;
const PHASE_CHASE = 'chase';
const PHASE_TORNADO = 'tornado';

export function createZoomieFx(scene) {
  const group = new THREE.Group();
  const center = new THREE.Vector3();
  const current = new THREE.Vector3();
  const tangent = new THREE.Vector3();
  const lookTarget = new THREE.Vector3();
  const chaseTarget = new THREE.Vector3();
  const chaseDir = new THREE.Vector3();
  const toTarget = new THREE.Vector3();
  const candidateA = new THREE.Vector3();
  const candidateB = new THREE.Vector3();
  const candidateC = new THREE.Vector3();
  let sphereGeo = null;
  let coneGeo = null;
  let dustGeo = null;
  const colors = [0xfff9c4, 0xe1f5fe, 0xd7ccc8, 0xffffff];
  let dragonRoot = null;
  let active = false;
  let disposed = true;
  let angle = 0;
  let startY = 0;
  let runRadius = 0;
  let spinT = 0;
  let phase = PHASE_TORNADO;
  let chaseT = 0;
  let chaseLeg = 0;
  let playerPosFn = null;
  let heightAtFn = null;
  let nestX = 0;
  let nestZ = -2;
  const vortex = [];
  const dust = [];
  scene.add(group);
  group.visible = false;
  function buildParticles() {
    if (vortex.length || dust.length) return;
    sphereGeo = new THREE.SphereGeometry(0.045, 6, 5);
    coneGeo = new THREE.ConeGeometry(0.055, 0.16, 5);
    dustGeo = new THREE.SphereGeometry(0.07, 6, 4);
    disposed = false;
    for (let i = 0; i < VORTEX_COUNT; i++) {
      const mat = new THREE.MeshBasicMaterial({
        color: colors[i % colors.length], transparent: true, opacity: 0.82, depthWrite: false,
      });
      const mesh = new THREE.Mesh(i % 5 === 0 ? coneGeo : sphereGeo, mat);
      mesh.userData.phase = (i / VORTEX_COUNT) * Math.PI * 2;
      mesh.userData.rise = (i * 0.618) % 1;
      mesh.userData.speed = 0.28 + (i % 7) * 0.015;
      mesh.userData.scale = 0.7 + (i % 4) * 0.12;
      group.add(mesh);
      vortex.push(mesh);
    }
    for (let i = 0; i < DUST_COUNT; i++) {
      const mat = new THREE.MeshBasicMaterial({
        color: 0xd7ccc8, transparent: true, opacity: 0.38, depthWrite: false,
      });
      const mesh = new THREE.Mesh(dustGeo, mat);
      mesh.userData.phase = (i / DUST_COUNT) * Math.PI * 2;
      mesh.userData.rise = (i * 0.37) % 1;
      group.add(mesh);
      dust.push(mesh);
    }
  }
  function disposeParticles() {
    for (const mesh of [...vortex, ...dust]) {
      group.remove(mesh);
      mesh.material.dispose();
    }
    vortex.length = 0;
    dust.length = 0;
    if (!disposed) {
      sphereGeo.dispose();
      coneGeo.dispose();
      dustGeo.dispose();
      sphereGeo = null;
      coneGeo = null;
      dustGeo = null;
      disposed = true;
    }
  }
  function outsideVolcano(x, z) {
    return Math.hypot(x - VOLCANO_X, z - VOLCANO_Z) >= VOLCANO_SAFE_R;
  }
  function randomTarget(out, minR, maxR) {
    for (let i = 0; i < 40; i++) {
      const a = Math.random() * Math.PI * 2;
      const r = minR ? minR + Math.random() * (maxR - minR) : Math.sqrt(Math.random()) * maxR;
      out.set(Math.cos(a) * r, 0, Math.sin(a) * r);
      if (outsideVolcano(out.x, out.z)) return;
    }
    out.set(maxR, 0, 0);
  }
  function groundY(x, z) {
    const y = heightAtFn ? heightAtFn(x, z) : startY;
    return Number.isFinite(y) ? y : startY;
  }
  function applyChaseGround() {
    dragonRoot.position.y = groundY(dragonRoot.position.x, dragonRoot.position.z);
  }
  function faceChaseLeg() {
    lookTarget.copy(dragonRoot.position).add(chaseDir);
    lookTarget.y = dragonRoot.position.y;
    dragonRoot.lookAt(lookTarget);
    dragonRoot.rotation.z = 0;
  }
  function setChaseDir() {
    chaseDir.set(chaseTarget.x - dragonRoot.position.x, 0, chaseTarget.z - dragonRoot.position.z);
    if (chaseDir.lengthSq() < 0.0001) chaseDir.set(1, 0, 0);
    else chaseDir.normalize();
    faceChaseLeg();
  }
  function awayTarget() {
    const p = playerPosFn ? playerPosFn() : null;
    const px = p && Number.isFinite(p.x) ? p.x : dragonRoot.position.x;
    const pz = p && Number.isFinite(p.z) ? p.z : dragonRoot.position.z;
    let bestD = -1;
    randomTarget(candidateA, 0, WORLD_TARGET_R);
    let dx = candidateA.x - px;
    let dz = candidateA.z - pz;
    bestD = dx * dx + dz * dz;
    chaseTarget.copy(candidateA);
    randomTarget(candidateB, 0, WORLD_TARGET_R);
    dx = candidateB.x - px;
    dz = candidateB.z - pz;
    let d = dx * dx + dz * dz;
    if (d > bestD) {
      bestD = d;
      chaseTarget.copy(candidateB);
    }
    randomTarget(candidateC, 0, WORLD_TARGET_R);
    dx = candidateC.x - px;
    dz = candidateC.z - pz;
    d = dx * dx + dz * dz;
    if (d > bestD) {
      chaseTarget.copy(candidateC);
    }
  }
  function startChaseLeg() {
    chaseLeg += 1;
    if (chaseLeg === 1) {
      randomTarget(chaseTarget, FIRST_LEG_MIN_R, FIRST_LEG_MAX_R);
    } else if (chaseLeg === 2) {
      toTarget.set(nestX - dragonRoot.position.x, 0, nestZ - dragonRoot.position.z);
      if (toTarget.lengthSq() < 0.0001) toTarget.set(1, 0, 0);
      else toTarget.normalize();
      chaseTarget.set(nestX + toTarget.x * NEST_OVERSHOOT, 0, nestZ + toTarget.z * NEST_OVERSHOOT);
      if (!outsideVolcano(chaseTarget.x, chaseTarget.z)) randomTarget(chaseTarget, 0, WORLD_TARGET_R);
    } else {
      awayTarget();
    }
    setChaseDir();
  }
  function caughtPlayer() {
    if (!playerPosFn) return false;
    const p = playerPosFn();
    if (!p) return false;
    const dx = dragonRoot.position.x - p.x;
    const dy = dragonRoot.position.y - p.y;
    const dz = dragonRoot.position.z - p.z;
    return dx * dx + dy * dy + dz * dz <= CATCH_RADIUS * CATCH_RADIUS;
  }
  function beginTornado() {
    phase = PHASE_TORNADO;
    center.copy(dragonRoot.position);
    startY = dragonRoot.position.y;
    angle = 0;
    runRadius = 0;
  }
  function updateChase(delta) {
    applyChaseGround();
    if (caughtPlayer()) { beginTornado(); return; }
    chaseT += delta;
    if (chaseT >= CHASE_MAX_S) { beginTornado(); return; }
    let remaining = delta * CHASE_SPEED;
    let turns = 0;
    while (remaining > 0 && turns < 8) {
      toTarget.set(chaseTarget.x - dragonRoot.position.x, 0, chaseTarget.z - dragonRoot.position.z);
      const dist = Math.hypot(toTarget.x, toTarget.z);
      if (dist <= TARGET_EPS) {
        startChaseLeg();
        turns += 1;
        continue;
      }
      const step = Math.min(remaining, dist);
      const s = step / dist;
      dragonRoot.position.x += toTarget.x * s;
      dragonRoot.position.z += toTarget.z * s;
      applyChaseGround();
      remaining -= step;
      if (step >= dist) {
        startChaseLeg();
        turns += 1;
      } else {
        remaining = 0;
      }
    }
    faceChaseLeg();
    if (caughtPlayer()) beginTornado();
  }
  function updateTornado(delta) {
    angle += delta * RUN_SPEED;
    runRadius = Math.min(RUN_RADIUS, runRadius + delta * 6);
    current.set(
      center.x + Math.cos(angle) * runRadius,
      startY,
      center.z + Math.sin(angle) * runRadius
    );
    dragonRoot.position.copy(current);
    tangent.set(-Math.sin(angle), 0, Math.cos(angle));
    lookTarget.copy(current).add(tangent);
    dragonRoot.lookAt(lookTarget);
    dragonRoot.rotateZ(BANK);
  }
  function start(root, opts = {}) {
    if (!root) return;
    opts = opts || {};
    dragonRoot = root;
    startY = root.position.y;
    angle = 0;
    runRadius = 0;
    spinT = 0;
    phase = PHASE_CHASE;
    chaseT = 0;
    chaseLeg = 0;
    playerPosFn = typeof opts.playerPos === 'function' ? opts.playerPos : null;
    heightAtFn = typeof opts.heightAt === 'function' ? opts.heightAt : null;
    nestX = opts.nest && Number.isFinite(opts.nest.x) ? opts.nest.x : 0;
    nestZ = opts.nest && Number.isFinite(opts.nest.z) ? opts.nest.z : -2;
    applyChaseGround();
    startChaseLeg();
    buildParticles();
    group.visible = true;
    active = true;
  }
  function stop() {
    if (dragonRoot) dragonRoot.rotation.set(0, dragonRoot.rotation.y, 0);
    active = false;
    dragonRoot = null;
    group.visible = false;
    playerPosFn = null;
    heightAtFn = null;
    disposeParticles();
  }
  function update(delta, { paused = false } = {}) {
    if (!active || !dragonRoot) return;
    const fxDelta = delta * (paused ? 0.18 : 1);
    spinT += fxDelta;
    if (!paused) {
      if (phase === PHASE_CHASE) updateChase(delta);
      else updateTornado(delta);
    }
    current.copy(dragonRoot.position);
    for (const mesh of vortex) {
      const u = mesh.userData;
      const h = ((u.rise + spinT * u.speed) % 1) * 1.6;
      const r = 0.4 + (h / 1.6) * 0.8;
      const a = u.phase + spinT * 5.2 + h * 1.8;
      mesh.position.set(current.x + Math.cos(a) * r, current.y + h, current.z + Math.sin(a) * r);
      mesh.rotation.y = -a;
      mesh.rotation.z += fxDelta * 3;
      mesh.scale.setScalar(u.scale * (0.65 + h * 0.18));
      mesh.material.opacity += ((paused ? 0.34 : 0.82) - mesh.material.opacity) * Math.min(1, delta * 5);
    }
    for (const mesh of dust) {
      const u = mesh.userData;
      const cycle = (u.rise + spinT * 0.55) % 1;
      const r = 0.5 + cycle * 1.0;
      const a = u.phase + spinT * 3.2;
      mesh.position.set(current.x + Math.cos(a) * r, current.y + 0.05 + cycle * 0.18, current.z + Math.sin(a) * r);
      mesh.scale.setScalar(1.2 - cycle * 0.7);
      mesh.material.opacity = (paused ? 0.12 : 0.34) * (1 - cycle);
    }
  }
  return { start, stop, isActive: () => active, update };
}
