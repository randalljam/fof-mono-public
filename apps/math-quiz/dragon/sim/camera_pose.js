// FPS look pose for Dragon Baby handoff. Look uses YXZ (yaw/pitch, zero roll),
// matching world/controls.js. Never read/write camera.rotation.x/y under the
// default XYZ order — that injects roll and tilts the world ~45°.

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

/** Yaw (y) + pitch (x) from a quaternion, YXZ order (roll discarded). */
export function yawPitchFromQuaternion(q) {
  const { x, y, z, w } = q;
  const pitch = Math.asin(clamp(2 * (w * x - y * z), -1, 1));
  const yaw = Math.atan2(2 * (w * y + z * x), 1 - 2 * (x * x + y * y));
  return { yaw, pitch };
}

/** Quaternion for yaw/pitch with roll forced to 0 (YXZ). */
export function quaternionFromYawPitch(yaw, pitch) {
  const x = pitch || 0;
  const y = yaw || 0;
  const c1 = Math.cos(x / 2);
  const c2 = Math.cos(y / 2);
  const s1 = Math.sin(x / 2);
  const s2 = Math.sin(y / 2);
  return {
    x: s1 * c2,
    y: c1 * s2,
    z: -s1 * s2,
    w: c1 * c2,
  };
}

/** Roll (z) from a quaternion in YXZ order — should stay ~0 for FPS look. */
export function rollFromQuaternion(q) {
  const { x, y, z, w } = q;
  return Math.atan2(2 * (w * z + x * y), 1 - 2 * (x * x + z * z));
}

export function captureCameraPose(camera) {
  if (!camera || !camera.position || !camera.quaternion) return null;
  const { yaw, pitch } = yawPitchFromQuaternion(camera.quaternion);
  return {
    x: camera.position.x,
    y: camera.position.y,
    z: camera.position.z,
    yaw,
    pitch,
  };
}

export function applyCameraPose(camera, pose) {
  if (!camera || !pose) return;
  const pos = camera.position;
  if (pos && typeof pos.set === 'function') {
    pos.set(pose.x || 0, pose.y == null ? 1.6 : pose.y, pose.z || 0);
  }
  const q = quaternionFromYawPitch(pose.yaw || 0, pose.pitch || 0);
  if (camera.quaternion && typeof camera.quaternion.set === 'function') {
    camera.quaternion.set(q.x, q.y, q.z, q.w);
  }
  // Keep Euler in sync with look convention so later reads aren't XYZ-skewed.
  if (camera.rotation) {
    camera.rotation.order = 'YXZ';
    if (typeof camera.rotation.set === 'function') {
      camera.rotation.set(pose.pitch || 0, pose.yaw || 0, 0);
    } else {
      camera.rotation.x = pose.pitch || 0;
      camera.rotation.y = pose.yaw || 0;
      camera.rotation.z = 0;
    }
  }
}

/**
 * Old (buggy) path: read/write Object3D Euler under default XYZ order.
 * Kept for the regression test — do not use in the game.
 */
export function buggyCapturePoseFromEulerXyz(camera) {
  return {
    x: camera.position.x,
    y: camera.position.y,
    z: camera.position.z,
    yaw: camera.rotation.y,
    pitch: camera.rotation.x,
  };
}
export function buggyApplyPoseToEulerXyz(camera, pose) {
  camera.position.x = pose.x || 0;
  camera.position.y = pose.y == null ? 1.6 : pose.y;
  camera.position.z = pose.z || 0;
  camera.rotation.order = 'XYZ';
  camera.rotation.y = pose.yaw || 0;
  camera.rotation.x = pose.pitch || 0;
}
