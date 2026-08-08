// Lava defense quest logic: DOM/THREE-free math shared by world/lava_streams.js,
// main.js, and the unit tests.
//
// Mount Ember erupts — five lava streams race down parallel paths toward the nest.
// Each stream is cooled by finishing a quiz at its glowing tip. Progress pauses
// during quizzes and asymptotically slows near the nest so the lava never arrives.

import { VOLCANO, terrainHeightAt } from './volcano_quest.js';

export const TOTAL_STREAMS = 5;
export const MAX_PROGRESS = 0.96;
export const BASE_SPEED = 0.018;

// Parallel paths down the south face: slightly different azimuths, speeds, and
// starting offsets so the streams read as separate but converging threats.
export const STREAM_SPECS = [
  { az: -0.42, rate: 1.12, startBias: 0.0 },
  { az: -0.18, rate: 0.92, startBias: 0.012 },
  { az: 0.0, rate: 1.05, startBias: 0.006 },
  { az: 0.22, rate: 0.88, startBias: 0.018 },
  { az: 0.44, rate: 1.0, startBias: 0.024 },
];

export const NEST = { x: 0, z: -2 };

function clampProgress(p) {
  return Math.max(0, Math.min(MAX_PROGRESS, p));
}
export function initProgress(startPct, bias = 0) {
  const base = (startPct || 0) / 100;
  return clampProgress(base + bias);
}
export function advanceProgress(progress, rate, dt) {
  const p = clampProgress(progress);
  if (p >= MAX_PROGRESS) return MAX_PROGRESS;
  const room = 1 - p;
  const step = rate * BASE_SPEED * room * room * dt;
  return clampProgress(p + step);
}
export function advanceStreamProgress(progress, rate, dt, paused) {
  if (paused) return progress;
  return advanceProgress(progress, rate, dt);
}
// Point along stream k at normalized progress t (0 = crater rim, 1 = nest).
export function streamPath(k, t) {
  const spec = STREAM_SPECS[k] || STREAM_SPECS[0];
  const tt = Math.max(0, Math.min(1, t));
  const rimAz = spec.az;
  const rimX = VOLCANO.x + Math.sin(rimAz) * VOLCANO.topR * 0.85;
  const rimZ = VOLCANO.z + Math.cos(rimAz) * VOLCANO.topR * 0.85;
  const nestX = NEST.x + Math.sin(rimAz * 0.35) * 1.2;
  const nestZ = NEST.z + Math.cos(rimAz * 0.35) * 0.8;
  const x = rimX + (nestX - rimX) * tt;
  const z = rimZ + (nestZ - rimZ) * tt;
  return { x, z, y: terrainHeightAt(x, z) + 0.15 + tt * 0.08, progress: tt };
}
export function streamSpec(k) {
  return STREAM_SPECS[k] || STREAM_SPECS[0];
}
export function stoppedSet(stopped) {
  return new Set((stopped || []).map((n) => Number(n)));
}
export function isStreamStopped(stopped, k) {
  return stoppedSet(stopped).has(k);
}
export function activeCount(stopped) {
  return TOTAL_STREAMS - stoppedSet(stopped).size;
}
export function allStopped(stopped) {
  return activeCount(stopped) === 0;
}
export function lavaActive(lava) {
  return !!(lava && lava.intro && !lava.won);
}
export function buildStreamProgress(lava) {
  const startPct = lava && lava.startPct != null ? lava.startPct : 0;
  const stopped = stoppedSet(lava && lava.stopped);
  const out = [];
  for (let k = 0; k < TOTAL_STREAMS; k++) {
    const spec = streamSpec(k);
    out.push({
      k,
      stopped: stopped.has(k),
      progress: stopped.has(k) ? MAX_PROGRESS : initProgress(startPct, spec.startBias),
    });
  }
  return out;
}
