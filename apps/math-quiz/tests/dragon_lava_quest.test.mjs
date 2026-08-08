import test from 'node:test';
import assert from 'node:assert/strict';
import {
  TOTAL_STREAMS, MAX_PROGRESS, BASE_SPEED, STREAM_SPECS,
  initProgress, advanceProgress, advanceStreamProgress, streamPath,
  allStopped, activeCount, lavaActive, buildStreamProgress, isStreamStopped,
} from '../dragon/sim/lava_quest.js';
import { nextObjectiveFor } from '../dragon/sim/story.js';
import { buildGmSnapshot } from '../dragon/sim/gm_state.js';

function lavaState(over = {}) {
  return Object.assign({
    intro: true, startPct: 76, stopped: [], won: false,
  }, over);
}

test('initProgress: startPct 76 lands streams past mid-path, below nest cap', () => {
  for (let k = 0; k < TOTAL_STREAMS; k++) {
    const spec = STREAM_SPECS[k];
    const p = initProgress(76, spec.startBias);
    assert.ok(p > 0.74, `stream ${k} starts above 74%`);
    assert.ok(p < MAX_PROGRESS, `stream ${k} stays below cap`);
    const tip = streamPath(k, p);
    assert.ok(tip.y >= 0, `stream ${k} tip has terrain height`);
  }
});

test('advanceProgress: slows near cap and never reaches 1.0', () => {
  let p = 0.9;
  for (let i = 0; i < 5000; i++) p = advanceProgress(p, 1.0, 1);
  assert.equal(p, MAX_PROGRESS);
  assert.ok(p < 1);
  const slowStart = advanceProgress(0.94, 1.0, 0.1);
  const fastStart = advanceProgress(0.5, 1.0, 0.1);
  assert.ok(slowStart - 0.94 < fastStart - 0.5, 'progress slows as streams approach the nest');
});

test('advanceStreamProgress: paused is a no-op', () => {
  const before = 0.76;
  assert.equal(advanceStreamProgress(before, 1.0, 2.0, true), before);
  assert.ok(advanceStreamProgress(before, 1.0, 2.0, false) > before);
});

test('streams: five specs with staggered biases and different rates', () => {
  assert.equal(STREAM_SPECS.length, TOTAL_STREAMS);
  const biases = STREAM_SPECS.map((s) => s.startBias);
  assert.equal(new Set(biases).size, TOTAL_STREAMS, 'each stream has a unique start bias');
  const rates = STREAM_SPECS.map((s) => s.rate);
  assert.ok(Math.min(...rates) < 1 && Math.max(...rates) > 1, 'rates spread around 1.0');
});

test('stop helpers: allStopped when five cooled', () => {
  assert.equal(activeCount([]), TOTAL_STREAMS);
  assert.equal(activeCount([0, 1, 2]), 2);
  assert.ok(!allStopped([0, 1, 2, 3]));
  assert.ok(allStopped([0, 1, 2, 3, 4]));
  assert.ok(isStreamStopped([0, 2], 0));
  assert.ok(!isStreamStopped([0, 2], 1));
});

test('buildStreamProgress: stopped streams marked, active use startPct', () => {
  const rows = buildStreamProgress(lavaState({ stopped: [1, 3] }));
  assert.equal(rows.length, TOTAL_STREAMS);
  assert.ok(rows[1].stopped);
  assert.ok(rows[3].stopped);
  assert.ok(!rows[0].stopped);
  assert.ok(rows[0].progress > 0.75);
});

test('lavaActive: intro without win is active', () => {
  assert.ok(lavaActive({ intro: true, won: false }));
  assert.ok(!lavaActive({ intro: true, won: true }));
  assert.ok(!lavaActive(null));
});

test('nextObjectiveFor prefers lava over volcano climb', () => {
  const state = {
    eggFound: true, maxPct: 76, hatched: true, dragonName: 'Pipa',
    visitedStones: [], volcano: { intro: true, cleared: 2, summited: false },
    lava: { intro: true, startPct: 76, stopped: [0, 1], won: false },
  };
  const obj = nextObjectiveFor(state);
  assert.equal(obj.id, 'lava-defense');
  assert.match(obj.text, /2 of 5/);
});

test('GM snapshot includes lava summary', () => {
  const snap = buildGmSnapshot({
    state: {
      maxPct: 76, hatched: true, eggFound: true, dragonName: 'Pipa',
      seenBeatIds: [], visitedStones: [], totalBursts: 5,
      celebratedIds: ['egg-found', 'hatch'], recentBursts: [],
      volcano: { intro: true, cleared: 0, summited: false },
      lava: { intro: true, startPct: 76, stopped: [0], won: false },
    },
    pct: 76, user: 'Kid1', folder: 'tlkids',
  });
  assert.equal(snap.lava.startPct, 76);
  assert.deepEqual(snap.lava.stopped, [0]);
  assert.equal(snap.lava.won, false);
  assert.equal(snap.objective.id, 'lava-defense');
});

test('advanceProgress uses BASE_SPEED constant', () => {
  assert.ok(BASE_SPEED > 0);
  const step = advanceProgress(0.5, 1.0, 1.0) - 0.5;
  assert.ok(step > 0 && step < 0.05);
});
