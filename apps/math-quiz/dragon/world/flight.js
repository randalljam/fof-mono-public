import * as THREE from 'three';

// Rideable flight: pointer-lock mouse look (via controls.js flight mode), WASD move
// relative to view (W/S forward/back, A/D strafe), Space/Shift up/down, E dismount
// (handled in main.js so mount and dismount never fire on the same keypress).
export function createFlight({ camera, dragon, onDismount, heightAt, nestPos, nestTopY }) {
  let riding = false;
  let descending = false;
  let brainTour = false; // H toggles the silly inside-the-head camera
  let cinematicRunning = false;
  const keys = { forward: false, backward: false, left: false, right: false, up: false, down: false };
  const forward = new THREE.Vector3();
  const right = new THREE.Vector3();
  const up = new THREE.Vector3(0, 1, 0);
  const WORLD_LIMIT = 72;
  const MIN_Y = 1.4;
  const MAX_Y = 40;
  function floorY(x, z) {
    if (nestPos && nestTopY != null) {
      const nestDist = Math.hypot(x - nestPos.x, z - nestPos.z);
      if (nestDist < 2.8) return nestTopY;
    }
    return heightAt ? heightAt(x, z) : 0;
  }
  function onKey(e, down) {
    if (!riding) return;
    if (e.code === 'KeyW') keys.forward = down;
    if (e.code === 'KeyS') keys.backward = down;
    if (e.code === 'KeyA') keys.left = down;
    if (e.code === 'KeyD') keys.right = down;
    if (e.code === 'Space') { keys.up = down; e.preventDefault(); }
    if (e.code === 'ShiftLeft' || e.code === 'ShiftRight') keys.down = down;
    if (down && e.code === 'KeyH') {
      brainTour = !brainTour;
      placeRideCamera(dragon.getRoot(), horizontalBasis());
    }
  }
  window.addEventListener('keydown', (e) => onKey(e, true));
  window.addEventListener('keyup', (e) => onKey(e, false));
  async function playFlightCinematic(director, nestPos) {
    cinematicRunning = true;
    dragon.playState('fly');
    await director.runSequence([
      { moveTo: { x: nestPos.x, y: 4, z: nestPos.z + 6 }, duration: 2 },
      { hold: 1200, onMid: async () => showInvite() },
      { moveTo: { x: nestPos.x, y: 2, z: nestPos.z + 2 }, duration: 1.5 },
    ]);
    cinematicRunning = false;
    if (!riding) dragon.playState('idle');
  }
  function showInvite() {
    if (document.getElementById('ride-invite')) return;
    const el = document.createElement('div');
    el.className = 'milestone-toast';
    el.textContent = 'Your dragon lowers a wing — press E to climb on!';
    el.id = 'ride-invite';
    document.body.appendChild(el);
  }
  function placeRideCamera(root, fwd) {
    const scale = root.scale.x || 1;
    let saddleForward;
    let saddleHeight;
    if (brainTour) {
      // Funny: sit inside the head (the bug-turned-feature).
      saddleForward = 0.15 * scale;
      saddleHeight = 0.55 * scale;
    } else {
      // Normal: on the back, behind the head so wings + head are visible (not insides).
      saddleForward = -0.35 * scale;
      saddleHeight = 0.7 * scale;
    }
    camera.position.set(
      root.position.x + fwd.x * saddleForward,
      root.position.y + saddleHeight,
      root.position.z + fwd.z * saddleForward,
    );
  }
  function mount() {
    if (riding) return;
    riding = true;
    descending = false;
    brainTour = false;
    document.getElementById('ride-invite')?.remove();
    dragon.playState('fly');
    placeRideCamera(dragon.getRoot(), horizontalBasis());
  }
  function dismount() {
    if (!riding) return;
    riding = false;
    brainTour = false;
    keys.forward = false;
    keys.backward = false;
    keys.left = false;
    keys.right = false;
    keys.up = false;
    keys.down = false;
    descending = true;
    dragon.playState('fly');
    if (onDismount) onDismount();
  }
  function isRiding() { return riding; }
  function isDescending() { return descending; }
  function horizontalBasis() {
    camera.getWorldDirection(forward);
    forward.y = 0;
    if (forward.lengthSq() < 1e-8) forward.set(0, 0, -1);
    else forward.normalize();
    right.crossVectors(forward, up).normalize();
    return forward;
  }
  function update(delta) {
    const root = dragon.getRoot();
    if (descending) {
      const targetY = floorY(root.position.x, root.position.z);
      root.position.y = THREE.MathUtils.lerp(root.position.y, targetY, Math.min(1, delta * 2.5));
      if (Math.abs(root.position.y - targetY) < 0.08) {
        root.position.y = targetY;
        descending = false;
        dragon.playState('idle');
      }
      return;
    }
    if (cinematicRunning || !riding) return;
    const speed = 11;
    const climbSpeed = 7;
    const fwd = horizontalBasis();
    if (keys.forward) root.position.addScaledVector(fwd, speed * delta);
    if (keys.backward) root.position.addScaledVector(fwd, -speed * delta);
    if (keys.left) root.position.addScaledVector(right, -speed * delta);
    if (keys.right) root.position.addScaledVector(right, speed * delta);
    if (keys.up) root.position.y += climbSpeed * delta;
    if (keys.down) root.position.y -= climbSpeed * delta;
    root.position.y = Math.max(MIN_Y, Math.min(MAX_Y, root.position.y));
    root.position.x = Math.max(-WORLD_LIMIT, Math.min(WORLD_LIMIT, root.position.x));
    root.position.z = Math.max(-WORLD_LIMIT, Math.min(WORLD_LIMIT, root.position.z));
    root.rotation.y = Math.atan2(fwd.x, fwd.z);
    placeRideCamera(root, fwd);
  }
  return {
    playFlightCinematic, mount, dismount, isRiding, isDescending, update, showInvitePrompt: showInvite,
  };
}
