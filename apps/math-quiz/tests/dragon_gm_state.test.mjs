import test from 'node:test';
import assert from 'node:assert/strict';
import { buildGmSnapshot } from '../dragon/sim/gm_state.js';

function state(over = {}) {
  return Object.assign({
    maxPct: 0, hatched: false, rideUnlocked: false, eggFound: true,
    dragonName: null, seenBeatIds: [], visitedStones: [], totalBursts: 0,
    celebratedIds: ['egg-found'], recentBursts: [], lastPlayedISO: null,
  }, over);
}

test('snapshot carries real fluency + kid-hidden details for the parent', () => {
  const snap = buildGmSnapshot({
    state: state({ maxPct: 64.26, hatched: true, dragonName: 'Sparkle', totalBursts: 9,
      seenBeatIds: ['egg-letter-1', 'egg-hum'], celebratedIds: ['egg-found', 'hatch'],
      recentBursts: [{ ts: 'x', correct: 18, total: 20, pctBefore: 60, pctAfter: 64 }] }),
    pct: 62.51, user: 'Kid1', folder: 'tlkids',
  });
  assert.equal(snap.user, 'Kid1');
  assert.equal(snap.folder, 'tlkids');
  assert.equal(snap.dragonName, 'Sparkle');
  assert.equal(snap.pct, 62.5);           // real percent, rounded to 0.1
  assert.equal(snap.maxPct, 64.3);
  assert.equal(snap.phase, 'hatchling');
  assert.equal(snap.nextMilestone.id, 'wings');
  assert.equal(snap.nextMilestone.pct, 70);
  assert.ok(snap.segmentFrac > 0.3 && snap.segmentFrac < 0.5);   // 64.26 within 60-70
  assert.equal(snap.objective.id, 'grow-hatchling');   // named hatchling keeps practicing
  assert.equal(snap.scrollsCollected, 2);
  assert.equal(snap.totalBursts, 9);
  assert.equal(snap.recentBursts.length, 1);
  assert.ok(snap.clientTs);
});

test('snapshot objective matches the story objective ladder', () => {
  const egg = buildGmSnapshot({ state: state(), pct: 30, user: 'I', folder: 'f' });
  assert.equal(egg.objective.id, 'feed-egg');
  assert.equal(egg.phase, 'egg');
  const unnamed = buildGmSnapshot({ state: state({ maxPct: 62, hatched: true }), pct: 62, user: 'I', folder: 'f' });
  assert.equal(unnamed.objective.id, 'name-dragon');
  const done = buildGmSnapshot({
    state: state({ maxPct: 100, hatched: true, rideUnlocked: true, dragonName: 'Pip' }),
    pct: 100, user: 'I', folder: 'f',
  });
  assert.equal(done.objective.id, 'ride');
  assert.equal(done.nextMilestone, null);
  assert.equal(done.phase, 'summit');
});

test('snapshot never mutates the game state', () => {
  const s = state({ celebratedIds: ['egg-found'], visitedStones: ['meadow'] });
  const snap = buildGmSnapshot({ state: s, pct: 50, user: 'I', folder: 'f' });
  snap.celebratedIds.push('X');
  snap.visitedStones.push('Y');
  snap.recentBursts.push({});
  assert.deepEqual(s.celebratedIds, ['egg-found']);
  assert.deepEqual(s.visitedStones, ['meadow']);
  assert.deepEqual(s.recentBursts, []);
});
