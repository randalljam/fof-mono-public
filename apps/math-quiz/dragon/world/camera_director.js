import * as THREE from 'three';

export function createCameraDirector(camera, controls) {
  let active = false;
  let restore = null;
  async function runSequence(steps) {
    if (active) return;
    active = true;
    if (controls && controls.isLocked) controls.unlock();
    restore = { pos: camera.position.clone(), rot: camera.rotation.clone() };
    for (const step of steps) {
      if (step.hold) await wait(step.hold);
      if (step.moveTo) await tweenCamera(camera, step.moveTo, step.duration || 1.5, step.lookAt);
      else if (step.lookAt) camera.lookAt(step.lookAt.x, step.lookAt.y, step.lookAt.z);
      if (step.onMid) await step.onMid();
    }
    if (restore) {
      camera.position.copy(restore.pos);
      camera.rotation.copy(restore.rot);
    }
    active = false;
  }
  function isActive() { return active; }
  return { runSequence, isActive };
}
function wait(ms) { return new Promise((r) => setTimeout(r, ms)); }
function tweenCamera(camera, target, duration, lookAt) {
  const start = camera.position.clone();
  const end = new THREE.Vector3(target.x ?? start.x, target.y ?? start.y, target.z ?? start.z);
  const startTime = performance.now();
  return new Promise((resolve) => {
    function tick() {
      const t = Math.min(1, (performance.now() - startTime) / (duration * 1000));
      camera.position.lerpVectors(start, end, easeInOut(t));
      if (lookAt) camera.lookAt(lookAt.x, lookAt.y, lookAt.z);
      if (t < 1) requestAnimationFrame(tick);
      else resolve();
    }
    tick();
  });
}
function easeInOut(t) { return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }
