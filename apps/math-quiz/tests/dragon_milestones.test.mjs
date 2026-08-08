import test from 'node:test';
import assert from 'node:assert/strict';
import {
  MILESTONES, resolveMilestones, getNextMilestone, foreshadowFor, progressToNext, animRepertoireFor,
  dragonFormFor,
} from '../dragon/sim/milestones.js';
import { createGameState, cloneLocalGameState, isPastHatch, fluencyPastHatch } from '../dragon/sim/game_state.js';

test('ladder is 5 surprises every 10% from 60 to 100', () => {
  const pctIds = MILESTONES.filter((m) => m.id !== 'egg-found').map((m) => [m.id, m.pct]);
  assert.deepEqual(pctIds, [
    ['hatch', 60], ['wings', 70], ['jump', 80], ['fire', 90], ['flight-ride', 100],
  ]);
});

test('resolveMilestones queues earned, uncelebrated milestones in order', () => {
  const q = resolveMilestones(75, ['egg-found', 'hatch']);
  assert.deepEqual(q.map((m) => m.id), ['wings']);
  const q2 = resolveMilestones(75, ['egg-found']);
  assert.deepEqual(q2.map((m) => m.id), ['hatch', 'wings']);
});

test('resolveMilestones does not re-queue celebrated milestones', () => {
  const q = resolveMilestones(80, ['egg-found', 'hatch', 'wings', 'jump']);
  assert.equal(q.length, 0);
});

test('dragonFormFor maps life stages to milestone celebrations', () => {
  assert.equal(dragonFormFor(['egg-found', 'hatch']), 'baby');
  assert.equal(dragonFormFor(['egg-found', 'hatch', 'wings']), 'juvenile');
  assert.equal(dragonFormFor(['egg-found', 'hatch', 'wings', 'jump']), 'adult');
  assert.equal(dragonFormFor(['egg-found', 'hatch', 'wings', 'jump', 'fire', 'flight-ride']), 'adult');
});

test('animRepertoireFor is empty before hatch', () => {
  assert.deepEqual(animRepertoireFor([]), []);
  assert.deepEqual(animRepertoireFor(['egg-found']), []);
  assert.deepEqual(animRepertoireFor(['egg-found', 'wings', 'jump', 'fire', 'flight-ride']), []);
});

test('animRepertoireFor adds play after hatch', () => {
  assert.deepEqual(animRepertoireFor(['egg-found', 'hatch']), ['play']);
});

test('animRepertoireFor grows cumulatively without fly', () => {
  assert.deepEqual(animRepertoireFor(['egg-found', 'hatch', 'wings']), ['play', 'wing-stretch']);
  assert.deepEqual(animRepertoireFor(['egg-found', 'hatch', 'wings', 'jump']), ['play', 'wing-stretch', 'jump']);
  const full = animRepertoireFor(['egg-found', 'hatch', 'wings', 'jump', 'fire', 'flight-ride']);
  assert.deepEqual(full, ['play', 'wing-stretch', 'jump', 'fire']);
  assert.ok(!full.includes('fly'));
});

test('hatch waits for 60%', () => {
  assert.equal(resolveMilestones(59, ['egg-found']).length, 0);
  assert.deepEqual(resolveMilestones(60, ['egg-found']).map((m) => m.id), ['hatch']);
});

test('100% unlock includes flight-ride once', () => {
  const q = resolveMilestones(100, ['egg-found', 'hatch', 'wings', 'jump', 'fire']);
  assert.deepEqual(q.map((m) => m.id), ['flight-ride']);
});

test('getNextMilestone returns the next pct milestone', () => {
  assert.equal(getNextMilestone(0).id, 'hatch');
  assert.equal(getNextMilestone(28).id, 'hatch');
  assert.equal(getNextMilestone(60).id, 'wings');
  assert.equal(getNextMilestone(95).id, 'flight-ride');
  assert.equal(getNextMilestone(100), null);
});

test('progressToNext measures within the current segment', () => {
  const a = progressToNext(30);
  assert.equal(a.next.id, 'hatch');
  assert.equal(a.frac, 0.5);   // 30 of the 0-60 segment
  const b = progressToNext(65);
  assert.equal(b.next.id, 'wings');
  assert.equal(b.frac, 0.5);   // halfway through 60-70
  const c = progressToNext(100);
  assert.equal(c.next, null);
  assert.equal(c.frac, 1);
});

test('foreshadow never names hatching, flying, or riding', () => {
  for (const pct of [0, 28, 59, 60, 75, 85, 95]) {
    const text = foreshadowFor(pct).toLowerCase();
    assert.ok(!text.includes('hatch'), `pct ${pct} leaked hatch`);
    assert.ok(!text.includes('fly'), `pct ${pct} leaked fly`);
    assert.ok(!text.includes('ride'), `pct ${pct} leaked ride`);
  }
});

test('game_state high-water maxPct never decreases', () => {
  const gs = createGameState('TestKid');
  const mem = new Map();
  globalThis.localStorage = {
    getItem: (k) => mem.get(k) || null,
    setItem: (k, v) => mem.set(k, v),
  };
  let s = gs.load();
  gs.updateHighWater(s, 55);
  gs.save(s);
  s = gs.load();
  gs.updateHighWater(s, 50);
  assert.equal(s.maxPct, 55);
});

test('v1 saves migrate: old milestone ids dropped, hatch re-earned from maxPct', () => {
  const gs = createGameState('Migrator');
  const mem = new Map();
  globalThis.localStorage = { getItem: (k) => mem.get(k) || null, setItem: (k, v) => mem.set(k, v) };
  mem.set(gs.key, JSON.stringify({
    version: 1, learner: 'Migrator', maxPct: 28, totalBursts: 3, eggFound: true,
    hatched: true, celebratedIds: ['egg-found', 'hatch', 'first-steps'], rideUnlocked: false,
  }));
  const s = gs.load();
  assert.equal(s.version, 3);       // v1 -> v2 (milestone reset) -> v3 (gems)
  assert.equal(s.maxPct, 28);
  assert.equal(s.totalBursts, 3);
  assert.equal(s.gems, 18);         // retroactive: 6 gems per already-played burst
  assert.equal(s.hatched, false);   // 28% < 60% — the egg is back until she earns the hatch
  assert.deepEqual(s.celebratedIds, ['egg-found']);
  assert.equal(resolveMilestones(s.maxPct, s.celebratedIds).length, 0);
});

test('celebration queue pops one at a time', () => {
  const gs = createGameState('Q');
  const mem = new Map();
  globalThis.localStorage = { getItem: (k) => mem.get(k) || null, setItem: (k, v) => mem.set(k, v) };
  let s = gs.load();
  gs.queueCelebrations(s, ['a', 'b', 'c']);
  assert.equal(gs.popCelebration(s), 'a');
  assert.equal(gs.popCelebration(s), 'b');
  assert.equal(gs.popCelebration(s), 'c');
  assert.equal(gs.popCelebration(s), null);
});

test('isPastHatch is false for a fresh egg-phase save', () => {
  const gs = createGameState('Fresh');
  const mem = new Map();
  globalThis.localStorage = { getItem: (k) => mem.get(k) || null, setItem: (k, v) => mem.set(k, v) };
  const s = gs.load();
  s.eggFound = true;
  s.maxPct = 62;
  assert.equal(isPastHatch(s), false);
});

test('isPastHatch is true when dragon is named or hatch milestone celebrated', () => {
  assert.equal(isPastHatch({ hatched: false, celebratedIds: ['egg-found', 'hatch'] }), true);
  assert.equal(isPastHatch({ hatched: true, celebratedIds: ['egg-found'] }), true);
  assert.equal(isPastHatch({ hatched: false, dragonName: 'Pipa', celebratedIds: ['egg-found'] }), true);
  assert.equal(isPastHatch({ hatched: false, seenBeatIds: ['hatch-name'], celebratedIds: ['egg-found'] }), true);
});

test('reconcileHatchState syncs hatched and celebratedIds without re-queuing hatch', () => {
  const gs = createGameState('Kid1');
  const mem = new Map();
  globalThis.localStorage = { getItem: (k) => mem.get(k) || null, setItem: (k, v) => mem.set(k, v) };
  let s = gs.load();
  s.eggFound = true;
  s.maxPct = 64;
  s.hatched = true;
  s.dragonName = 'Pipa';
  s.celebratedIds = ['egg-found'];
  gs.reconcileHatchState(s);
  assert.equal(s.hatched, true);
  assert.ok(s.celebratedIds.includes('hatch'));
  assert.equal(resolveMilestones(s.maxPct, s.celebratedIds).map((m) => m.id).length, 0);
});

test('reconcileHatchState silently hatches when fluency is already past 60%', () => {
  const gs = createGameState('NewKid');
  const mem = new Map();
  globalThis.localStorage = { getItem: (k) => mem.get(k) || null, setItem: (k, v) => mem.set(k, v) };
  let s = gs.load();
  s.maxPct = 62;
  gs.reconcileHatchState(s);
  assert.equal(s.hatched, true);
  assert.equal(s.eggFound, true);
  assert.ok(s.celebratedIds.includes('egg-found'));
  assert.ok(s.celebratedIds.includes('hatch'));
  assert.equal(resolveMilestones(s.maxPct, s.celebratedIds).map((m) => m.id).length, 0);
});

test('fluencyPastHatch is false below 60% and true at or above', () => {
  assert.equal(fluencyPastHatch({ maxPct: 59 }), false);
  assert.equal(fluencyPastHatch({ maxPct: 60 }), true);
  assert.equal(fluencyPastHatch({ maxPct: 72 }), true);
});

test('cloneLocalGameState copies volcano and stations onto the target key', () => {
  const mem = new Map();
  globalThis.localStorage = {
    getItem: (k) => mem.get(k) || null,
    setItem: (k, v) => mem.set(k, v),
    removeItem: (k) => mem.delete(k),
  };
  const Kid1 = createGameState('Kid1');
  const k1State = Kid1.load();
  k1State.volcano = { intro: true, cleared: 3, summited: false };
  k1State.stations = { signs: { 'sign-welcome': 'HI' }, levels: { nest: 2 }, intro: true };
  k1State.learner = 'Kid1';
  Kid1.save(k1State);

  assert.equal(cloneLocalGameState('Kid1', 'Randy'), true);
  const randy = createGameState('Randy').load();
  assert.equal(randy.learner, 'Randy');
  assert.equal(randy.volcano.cleared, 3);
  assert.equal(randy.stations.signs['sign-welcome'], 'HI');
  assert.equal(randy.stations.levels.nest, 2);
  // Source save untouched
  assert.equal(createGameState('Kid1').load().learner, 'Kid1');
});

test('cloneLocalGameState clears target when source has no save', () => {
  const mem = new Map();
  globalThis.localStorage = {
    getItem: (k) => mem.get(k) || null,
    setItem: (k, v) => mem.set(k, v),
    removeItem: (k) => mem.delete(k),
  };
  const randy = createGameState('Randy');
  const s = randy.load();
  s.volcano = { intro: true, cleared: 5, summited: true };
  randy.save(s);
  assert.equal(cloneLocalGameState('Kid1', 'Randy'), false);
  assert.equal(mem.has(randy.key), false);
});

test('clone-style fresh save with copied fluency restores hatched dragon without hatch queued', () => {
  const gs = createGameState('Randy');
  const mem = new Map();
  globalThis.localStorage = { getItem: (k) => mem.get(k) || null, setItem: (k, v) => mem.set(k, v) };
  mem.delete(gs.key);
  let s = gs.load();
  gs.updateHighWater(s, 64.2);
  gs.reconcileHatchState(s);
  assert.equal(s.hatched, true);
  assert.equal(s.eggFound, true);
  assert.ok(!resolveMilestones(s.maxPct, s.celebratedIds).some((m) => m.id === 'hatch'));
});
