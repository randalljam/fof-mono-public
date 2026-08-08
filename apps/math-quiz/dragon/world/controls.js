import * as THREE from 'three';
import { PointerLockControls } from 'three/addons/controls/PointerLockControls.js';
import { isTouchDevice } from '../device.js';

export { isTouchDevice };

export function createControls(camera, domElement, { heightAt } = {}) {
  const groundAt = heightAt || (() => 0);
  const touchMode = isTouchDevice();
  const controls = new PointerLockControls(camera, domElement);
  const velocity = new THREE.Vector3();
  const direction = new THREE.Vector3();
  const keys = { forward: false, backward: false, left: false, right: false };
  let canJump = true;
  const playerHeight = 1.6;
  let verticalVelocity = 0;
  const gravity = 28;
  const jumpSpeed = 9;
  const moveSpeed = 12;
  const lookSensitivity = 0.0032;
  const raycaster = new THREE.Raycaster();
  const interactables = [];
  let onInteract = null;
  let lockAllowed = true;
  let playActive = true;
  const lookEuler = new THREE.Euler(0, 0, 0, 'YXZ');

  const crosshair = document.createElement('div');
  crosshair.id = 'crosshair';
  document.body.appendChild(crosshair);
  const prompt = document.createElement('div');
  prompt.id = 'interact-prompt';
  prompt.className = 'hidden';
  prompt.textContent = 'Click to interact';
  document.body.appendChild(prompt);

  let highlighted = null;
  let touchRoot = null;
  let moveKnob = null;
  let lookKnob = null;
  let jumpBtn = null;
  let interactBtn = null;
  let moveTouchId = null;
  let lookTouchId = null;
  const moveOrigin = { x: 0, y: 0 };
  const lookOrigin = { x: 0, y: 0 };
  const moveStick = { x: 0, y: 0 };
  const maxStickRadius = 48;

  function isDriving() {
    return touchMode ? (playActive && lockAllowed) : controls.isLocked;
  }
  function tryJump() {
    if (!canJump || !isDriving()) return;
    verticalVelocity = jumpSpeed;
    canJump = false;
  }
  function applyLookDelta(dx, dy) {
    lookEuler.setFromQuaternion(camera.quaternion);
    lookEuler.y -= dx * lookSensitivity;
    lookEuler.x -= dy * lookSensitivity;
    const limit = Math.PI / 2 - 0.05;
    lookEuler.x = Math.max(-limit, Math.min(limit, lookEuler.x));
    camera.quaternion.setFromEuler(lookEuler);
  }
  function setStickVisual(knob, nx, ny) {
    if (!knob) return;
    knob.style.transform = `translate(calc(-50% + ${nx * maxStickRadius}px), calc(-50% + ${ny * maxStickRadius}px))`;
  }
  function resetStickVisual(knob) {
    if (!knob) return;
    knob.style.transform = 'translate(-50%, -50%)';
  }
  function syncMoveKeysFromStick() {
    const dead = 0.18;
    keys.forward = moveStick.y < -dead;
    keys.backward = moveStick.y > dead;
    keys.left = moveStick.x < -dead;
    keys.right = moveStick.x > dead;
  }
  function clearMoveStick() {
    moveStick.x = 0;
    moveStick.y = 0;
    moveTouchId = null;
    resetStickVisual(moveKnob);
    syncMoveKeysFromStick();
  }
  function clearLookStick() {
    lookTouchId = null;
    resetStickVisual(lookKnob);
  }
  function bindPad(el, onStart, onMove, onEnd) {
    el.addEventListener('touchstart', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const t = e.changedTouches[0];
      if (t) onStart(t);
    }, { passive: false });
    el.addEventListener('touchmove', (e) => {
      e.preventDefault();
      e.stopPropagation();
      for (const t of e.changedTouches) onMove(t);
    }, { passive: false });
    el.addEventListener('touchend', (e) => {
      e.preventDefault();
      e.stopPropagation();
      for (const t of e.changedTouches) onEnd(t);
    }, { passive: false });
    el.addEventListener('touchcancel', (e) => {
      for (const t of e.changedTouches) onEnd(t);
    }, { passive: false });
  }
  function buildTouchUi() {
    touchRoot = document.createElement('div');
    touchRoot.id = 'touch-controls';
    touchRoot.innerHTML = `
      <div class="touch-left">
        <div class="touch-pad touch-look" id="touch-look">
          <div class="touch-pad-ring"></div>
          <div class="touch-pad-knob" id="touch-look-knob"></div>
          <div class="touch-pad-label">Look</div>
        </div>
        <div class="touch-actions">
          <button type="button" class="touch-btn touch-jump" id="touch-jump">Jump</button>
          <button type="button" class="touch-btn touch-interact hidden" id="touch-interact">Tap</button>
        </div>
      </div>
      <div class="touch-pad touch-move" id="touch-move">
        <div class="touch-pad-ring"></div>
        <div class="touch-pad-knob" id="touch-move-knob"></div>
        <div class="touch-pad-label">Move</div>
      </div>`;
    document.body.appendChild(touchRoot);
    document.body.classList.add('touch-mode');
    moveKnob = touchRoot.querySelector('#touch-move-knob');
    lookKnob = touchRoot.querySelector('#touch-look-knob');
    jumpBtn = touchRoot.querySelector('#touch-jump');
    interactBtn = touchRoot.querySelector('#touch-interact');
    const movePad = touchRoot.querySelector('#touch-move');
    const lookPad = touchRoot.querySelector('#touch-look');

    bindPad(movePad,
      (t) => {
        if (moveTouchId != null) return;
        moveTouchId = t.identifier;
        const rect = movePad.getBoundingClientRect();
        moveOrigin.x = rect.left + rect.width / 2;
        moveOrigin.y = rect.top + rect.height / 2;
        const dx = t.clientX - moveOrigin.x;
        const dy = t.clientY - moveOrigin.y;
        const len = Math.hypot(dx, dy) || 1;
        const scale = Math.min(1, len / maxStickRadius);
        moveStick.x = (dx / len) * scale;
        moveStick.y = (dy / len) * scale;
        setStickVisual(moveKnob, moveStick.x, moveStick.y);
        syncMoveKeysFromStick();
      },
      (t) => {
        if (t.identifier !== moveTouchId) return;
        const dx = t.clientX - moveOrigin.x;
        const dy = t.clientY - moveOrigin.y;
        const len = Math.hypot(dx, dy) || 1;
        const scale = Math.min(1, len / maxStickRadius);
        moveStick.x = (dx / len) * scale;
        moveStick.y = (dy / len) * scale;
        setStickVisual(moveKnob, moveStick.x, moveStick.y);
        syncMoveKeysFromStick();
      },
      (t) => {
        if (t.identifier === moveTouchId) clearMoveStick();
      });

    bindPad(lookPad,
      (t) => {
        if (lookTouchId != null) return;
        lookTouchId = t.identifier;
        lookOrigin.x = t.clientX;
        lookOrigin.y = t.clientY;
        setStickVisual(lookKnob, 0, 0);
      },
      (t) => {
        if (t.identifier !== lookTouchId) return;
        const dx = t.clientX - lookOrigin.x;
        const dy = t.clientY - lookOrigin.y;
        lookOrigin.x = t.clientX;
        lookOrigin.y = t.clientY;
        applyLookDelta(dx, dy);
        const vx = Math.max(-1, Math.min(1, dx / 18));
        const vy = Math.max(-1, Math.min(1, dy / 18));
        setStickVisual(lookKnob, vx, vy);
      },
      (t) => {
        if (t.identifier === lookTouchId) clearLookStick();
      });

    const pressJump = (e) => {
      e.preventDefault();
      e.stopPropagation();
      tryJump();
    };
    jumpBtn.addEventListener('touchstart', pressJump, { passive: false });
    jumpBtn.addEventListener('click', pressJump);
    const pressInteract = (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (highlighted && onInteract) onInteract(highlighted);
    };
    interactBtn.addEventListener('touchstart', pressInteract, { passive: false });
    interactBtn.addEventListener('click', pressInteract);
  }
  function setTouchUiVisible(on) {
    if (!touchRoot) return;
    touchRoot.classList.toggle('hidden', !on);
  }

  function onKeyDown(e) {
    if (e.code === 'KeyW') keys.forward = true;
    if (e.code === 'KeyS') keys.backward = true;
    if (e.code === 'KeyA') keys.left = true;
    if (e.code === 'KeyD') keys.right = true;
    if (e.code === 'Space') { tryJump(); e.preventDefault(); }
  }
  function onKeyUp(e) {
    if (e.code === 'KeyW') keys.forward = false;
    if (e.code === 'KeyS') keys.backward = false;
    if (e.code === 'KeyA') keys.left = false;
    if (e.code === 'KeyD') keys.right = false;
  }
  window.addEventListener('keydown', onKeyDown);
  window.addEventListener('keyup', onKeyUp);

  if (touchMode) {
    buildTouchUi();
    // Prevent the page from scrolling while a finger is on the game canvas.
    domElement.style.touchAction = 'none';
  } else {
    domElement.addEventListener('click', () => {
      if (!controls.isLocked) {
        if (lockAllowed) controls.lock();
      } else if (highlighted && onInteract) onInteract(highlighted);
    });
  }

  function registerInteractable(mesh, id, label) {
    mesh.userData.interactId = id;
    mesh.userData.interactLabel = label || 'Click to interact';
    interactables.push(mesh);
  }
  // Raycast recursively (interactables may be Groups) and resolve the hit back up
  // to the registered ancestor; skip hits inside invisible subtrees (three's
  // raycaster does not check visibility itself).
  function pickInteractable() {
    raycaster.setFromCamera(new THREE.Vector2(0, 0), camera);
    const hits = raycaster.intersectObjects(interactables, true);
    for (const h of hits) {
      if (h.distance > 6) break;
      let vis = true;
      for (let t = h.object; t; t = t.parent) {
        if (t.visible === false) { vis = false; break; }
      }
      if (!vis) continue;
      let o = h.object;
      while (o && !o.userData.interactId) o = o.parent;
      if (o && o.userData.interactId) return o;
    }
    return null;
  }
  function update(delta, enabled) {
    playActive = !!enabled;
    setTouchUiVisible(touchMode && enabled && lockAllowed && !flightMode);
    if (flightMode) {
      highlighted = null;
      if (interactBtn) interactBtn.classList.add('hidden');
      prompt.textContent = 'WASD to fly · Space/Shift up/down · E to dismount · H brain tour';
      prompt.classList.remove('hidden');
      return;
    }
    if (!enabled) {
      highlighted = null;
      prompt.classList.add('hidden');
      if (interactBtn) interactBtn.classList.add('hidden');
      if (touchMode) clearMoveStick();
      return;
    }
    highlighted = null;
    if (isDriving()) {
      direction.set(0, 0, 0);
      if (keys.forward) direction.z -= 1;
      if (keys.backward) direction.z += 1;
      if (keys.left) direction.x -= 1;
      if (keys.right) direction.x += 1;
      direction.normalize();
      velocity.x = direction.x * moveSpeed * delta;
      velocity.z = direction.z * moveSpeed * delta;
      controls.moveRight(velocity.x);
      controls.moveForward(-velocity.z);
      verticalVelocity -= gravity * delta;
      camera.position.y += verticalVelocity * delta;
      // The floor follows the terrain (mountains are climbable): snap up when
      // walking uphill, fall with gravity when walking off an edge.
      const floorY = groundAt(camera.position.x, camera.position.z) + playerHeight;
      if (camera.position.y < floorY) {
        camera.position.y = floorY;
        verticalVelocity = 0;
        canJump = true;
      }
      highlighted = pickInteractable();
      if (highlighted) {
        const label = highlighted.userData.interactLabel || 'Tap to interact';
        prompt.textContent = touchMode ? label.replace(/^Click/, 'Tap') : label;
        prompt.classList.remove('hidden');
        if (interactBtn) {
          interactBtn.classList.remove('hidden');
          interactBtn.textContent = 'Tap';
        }
      } else {
        prompt.classList.add('hidden');
        if (interactBtn) interactBtn.classList.add('hidden');
      }
    } else if (!touchMode) {
      prompt.textContent = 'Click to look around (WASD to move)';
      prompt.classList.remove('hidden');
      if (interactBtn) interactBtn.classList.add('hidden');
    } else {
      prompt.classList.add('hidden');
      if (interactBtn) interactBtn.classList.add('hidden');
    }
  }
  let flightMode = false;
  function setFlightMode(on) {
    flightMode = !!on;
    if (flightMode) {
      lockAllowed = true;
      playActive = true;
      prompt.textContent = 'WASD to fly · Space/Shift up/down · E to dismount · H brain tour';
      prompt.classList.remove('hidden');
      if (!touchMode && !controls.isLocked) controls.lock();
      if (touchMode) setTouchUiVisible(false);
      return;
    }
    prompt.classList.add('hidden');
  }
  function setEnabled(on) {
    lockAllowed = on;
    if (!on && !flightMode && controls.isLocked) controls.unlock();
    if (!on && touchMode) {
      clearMoveStick();
      clearLookStick();
    }
    setTouchUiVisible(touchMode && on && playActive);
  }
  function beginFall() {
    canJump = false;
    verticalVelocity = 0;
  }
  return {
    controls, update, registerInteractable,
    setInteractHandler: (fn) => { onInteract = fn; },
    setEnabled, setFlightMode, beginFall, isFlightMode: () => flightMode, camera, touchMode,
  };
}
