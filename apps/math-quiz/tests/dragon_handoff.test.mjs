import test from 'node:test';
import assert from 'node:assert/strict';
import { hydrateFromCheckpoint } from '../dragon/sim/game_state.js';
import { createBurst } from '../dragon/sim/burst_session.js';
import { deviceType, transferTargetType, transferButtonLabel, isTouchDevice } from '../dragon/device.js';
import {
  applyCameraPose,
  buggyApplyPoseToEulerXyz,
  buggyCapturePoseFromEulerXyz,
  captureCameraPose,
  quaternionFromYawPitch,
  rollFromQuaternion,
  yawPitchFromQuaternion,
} from '../dragon/sim/camera_pose.js';
import {
  brokenResolveBootEntry,
  gamePageUrl,
  pendingQuizForBoot,
  resolveBootEntry,
  shouldAutoResumeHandoff,
} from '../dragon/sim/boot_entry.js';

function fakeCamera(yaw, pitch) {
  const q = quaternionFromYawPitch(yaw, pitch);
  return {
    position: { x: 1, y: 1.6, z: 4, set(x, y, z) { this.x = x; this.y = y; this.z = z; } },
    quaternion: { x: q.x, y: q.y, z: q.z, w: q.w, set(x, y, z, w) { this.x = x; this.y = y; this.z = z; this.w = w; } },
    rotation: { order: 'XYZ', x: 0, y: 0, z: 0, set(x, y, z) { this.x = x; this.y = y; this.z = z; } },
  };
}

test('hydrateFromCheckpoint migrates server gameState like local load', () => {
  const s = hydrateFromCheckpoint({
    version: 2, learner: 'Kid1', totalBursts: 4, eggFound: true,
    celebratedIds: ['egg-found'], volcano: { intro: true, cleared: 1, summited: false },
  }, 'Kid1');
  assert.equal(s.version, 3);
  assert.equal(s.learner, 'Kid1');
  assert.ok(s.gems >= 24);
  assert.equal(s.volcano.cleared, 1);
});

test('burst allItems preserves exact problem list for handoff resume', () => {
  const items = [
    { key: 'a', operation: '+', num1: 2, num2: 3, problemText: '2 + 3' },
    { key: 'b', operation: '+', num1: 4, num2: 5, problemText: '4 + 5' },
  ];
  const burst = createBurst(items);
  assert.deepEqual(burst.allItems(), items);
});

test('device helpers classify touch vs desktop transfer targets', () => {
  assert.ok(['desktop', 'touch'].includes(deviceType()));
  assert.notEqual(deviceType(), transferTargetType());
  assert.match(transferButtonLabel(), /Transfer to/);
  assert.equal(typeof isTouchDevice(), 'boolean');
});

// Regression: handoff used camera.rotation.x/y (default XYZ Euler) while look
// uses YXZ quaternions. Saving+restoring that way injects roll (~tilted world)
// and the bad pose then travels desktop ↔ iPad on every transfer.
test('handoff pose round-trip keeps roll near zero (no tilted camera)', () => {
  const yaw = 0.85;
  const pitch = -0.42;
  const cam = fakeCamera(yaw, pitch);
  assert.ok(Math.abs(rollFromQuaternion(cam.quaternion)) < 1e-9);

  const pose = captureCameraPose(cam);
  assert.ok(Math.abs(pose.yaw - yaw) < 1e-9);
  assert.ok(Math.abs(pose.pitch - pitch) < 1e-9);

  const dest = fakeCamera(0, 0);
  applyCameraPose(dest, pose);
  assert.ok(Math.abs(rollFromQuaternion(dest.quaternion)) < 1e-6, 'restored pose must not add roll');
  const back = yawPitchFromQuaternion(dest.quaternion);
  assert.ok(Math.abs(back.yaw - yaw) < 1e-6);
  assert.ok(Math.abs(back.pitch - pitch) < 1e-6);
});

test('buggy XYZ euler pose path introduces roll (documents the tilt bug)', () => {
  const yaw = 0.85;
  const pitch = -0.42;
  const cam = fakeCamera(yaw, pitch);
  // Sync default-order Euler from the look quaternion the way Object3D does
  // (decompose with XYZ) — this is what the old capture accidentally read.
  const q = cam.quaternion;
  const sinrCosp = 2 * (q.w * q.x + q.y * q.z);
  const cosrCosp = 1 - 2 * (q.x * q.x + q.y * q.y);
  cam.rotation.order = 'XYZ';
  cam.rotation.x = Math.atan2(sinrCosp, cosrCosp);
  const sinp = 2 * (q.w * q.y - q.z * q.x);
  cam.rotation.y = Math.abs(sinp) >= 1 ? Math.sign(sinp) * Math.PI / 2 : Math.asin(sinp);
  const sinyCosp = 2 * (q.w * q.z + q.x * q.y);
  const cosyCosp = 1 - 2 * (q.y * q.y + q.z * q.z);
  cam.rotation.z = Math.atan2(sinyCosp, cosyCosp);

  const badPose = buggyCapturePoseFromEulerXyz(cam);
  const dest = fakeCamera(0, 0);
  buggyApplyPoseToEulerXyz(dest, badPose);
  // Rebuild quaternion from the XYZ euler the buggy apply wrote.
  const { x, y, z } = dest.rotation;
  const c1 = Math.cos(x / 2); const c2 = Math.cos(y / 2); const c3 = Math.cos(z / 2);
  const s1 = Math.sin(x / 2); const s2 = Math.sin(y / 2); const s3 = Math.sin(z / 2);
  dest.quaternion.set(
    s1 * c2 * c3 + c1 * s2 * s3,
    c1 * s2 * c3 - s1 * c2 * s3,
    c1 * c2 * s3 + s1 * s2 * c3,
    c1 * c2 * c3 - s1 * s2 * s3,
  );
  const roll = Math.abs(rollFromQuaternion(dest.quaternion));
  assert.ok(roll > 0.15, `expected noticeable roll from XYZ bug, got ${roll}`);
});

// --- Boot entry / hard-refresh picker (red→green regression) ---
// Sticky localStorage + ?user= + syncLearnerUrl skipped "Who's playing?" and
// could reopen a Go quiz on every hard refresh. Handoff resume must be explicit.

test('broken sticky learner skips player picker (documents the regression)', () => {
  const broken = brokenResolveBootEntry({
    urlUser: '',
    rememberedUser: 'Randy',
    rememberedFolder: 'tlkids',
  });
  assert.equal(broken.needsPlayerPicker, false);
  assert.equal(broken.user, 'Randy');
});

test('hard refresh always needs Who\'s playing even with remembered or ?user=', () => {
  assert.equal(resolveBootEntry({
    urlUser: '',
    rememberedUser: 'Randy',
  }).needsPlayerPicker, true);

  assert.equal(resolveBootEntry({
    urlUser: 'Randy',
    rememberedUser: 'Randy',
  }).needsPlayerPicker, true);

  assert.equal(resolveBootEntry({
    urlUser: 'Randy',
    urlResume: '',
    rememberedUser: 'Kid1',
  }).user, '');
});

test('explicit handoff resume skips picker and keeps the learner', () => {
  const entry = resolveBootEntry({
    urlUser: 'Randy',
    urlResume: '1',
    rememberedUser: 'Kid1',
  });
  assert.equal(entry.needsPlayerPicker, false);
  assert.equal(entry.handoffResume, true);
  assert.equal(entry.user, 'Randy');
});

test('pending Go quiz restores only on claim or handoff resume', () => {
  const quiz = { items: [{ key: '1+1' }], atGoGate: true };
  assert.equal(pendingQuizForBoot({ pendingQuiz: quiz, claimed: false, handoffResume: false }), null);
  assert.equal(pendingQuizForBoot({ pendingQuiz: quiz, claimed: true, handoffResume: false }), quiz);
  assert.equal(pendingQuizForBoot({ pendingQuiz: quiz, claimed: false, handoffResume: true }), quiz);
  assert.equal(pendingQuizForBoot({ pendingQuiz: null, claimed: true, handoffResume: true }), null);
});

test('handoff reload URL includes resume=1 so the next hard refresh can drop it', () => {
  const url = gamePageUrl({ user: 'Randy', resume: true, hostname: '10.0.0.1', port: '8907' });
  assert.match(url, /user=Randy/);
  assert.match(url, /resume=1/);
  const cold = gamePageUrl({ user: '', resume: false, hostname: '10.0.0.1', port: '8907' });
  assert.equal(cold, 'http://10.0.0.1:8907/dragon/index.html');
});

test('incoming transfer auto-resumes; source device keeps Transferred card', () => {
  assert.equal(shouldAutoResumeHandoff({ canClaim: true, isOwner: false }), true);
  assert.equal(shouldAutoResumeHandoff({ canClaim: false, isOwner: true }), true);
  assert.equal(shouldAutoResumeHandoff({ canClaim: false, isOwner: false }), false);
});
