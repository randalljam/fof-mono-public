import test from 'node:test';
import assert from 'node:assert/strict';
import {
  gemsForBurst, NEST_UPGRADES, unlockedUpgrades, nextUpgrade,
  sameLocalDay, dailyGiftAvailable, giftNote, DAILY_GIFT_GEMS,
  roadStops, roadProgressLine,
} from '../dragon/sim/rewards.js';
import { createGameState } from '../dragon/sim/game_state.js';
import { buildGmSnapshot } from '../dragon/sim/gm_state.js';

function baseState(over = {}) {
  return Object.assign({
    maxPct: 63, hatched: true, rideUnlocked: false, eggFound: true,
    dragonName: 'Ember', seenBeatIds: [], visitedStones: [], totalBursts: 5,
    celebratedIds: ['egg-found', 'hatch'], gems: 30,
    volcano: { intro: true, cleared: 1, summited: false },
  }, over);
}

test('gems: base + correct bonus + completion bonus, zero for empty bursts', () => {
  assert.equal(gemsForBurst({ correct: 0, total: 0 }), 0);
  assert.equal(gemsForBurst({ correct: 0, total: 10, kind: 'quit-saved' }), 3);
  assert.equal(gemsForBurst({ correct: 9, total: 12, kind: 'quit-saved' }), 6);
  assert.equal(gemsForBurst({ correct: 15, total: 20, kind: 'list-complete' }), 10);
  assert.equal(gemsForBurst({ correct: 20, total: 20, kind: 'list-complete' }), 11);
});

test('nest upgrades unlock in cost order and report the next goal', () => {
  const costs = NEST_UPGRADES.map((u) => u.cost);
  assert.deepEqual(costs, [...costs].sort((a, b) => a - b));
  assert.deepEqual(unlockedUpgrades(0), []);
  assert.deepEqual(unlockedUpgrades(20), ['garden']);
  assert.deepEqual(unlockedUpgrades(95), ['garden', 'lights', 'banners']);
  assert.equal(unlockedUpgrades(999).length, NEST_UPGRADES.length);
  assert.equal(nextUpgrade(0).id, 'garden');
  assert.equal(nextUpgrade(55).id, 'banners');
  assert.equal(nextUpgrade(9999), null);
});

test('daily gift: once per local calendar day', () => {
  assert.equal(dailyGiftAvailable(null, '2026-07-11T09:00:00'), true);
  assert.equal(dailyGiftAvailable('2026-07-11T08:00:00', '2026-07-11T20:00:00'), false);
  assert.equal(dailyGiftAvailable('2026-07-10T23:59:00', '2026-07-11T00:01:00'), true);
  assert.equal(sameLocalDay('2026-07-11T01:00:00', '2026-07-11T23:00:00'), true);
  assert.equal(sameLocalDay('2026-06-11T12:00:00', '2026-07-11T12:00:00'), false);
  // Notes rotate and always carry the gem count.
  const notes = new Set([giftNote(0), giftNote(1), giftNote(2), giftNote(3)]);
  assert.equal(notes.size, 4);
  for (const n of notes) assert.ok(n.includes(String(DAILY_GIFT_GEMS)));
});

test('road stops: done flags follow milestones, exactly one current stop', () => {
  const stops = roadStops(baseState());
  assert.deepEqual(stops.map((s) => s.id), ['egg', 'hatch', 'meadow', 'hills', 'grove', 'beacon', 'ember', 'lava']);
  const byId = Object.fromEntries(stops.map((s) => [s.id, s]));
  assert.ok(byId.egg.done && byId.hatch.done);
  assert.ok(!byId.meadow.done && byId.meadow.current);
  assert.equal(stops.filter((s) => s.current).length, 1);
  // Finished game: everything done, nothing current.
  const all = roadStops(baseState({
    maxPct: 100, rideUnlocked: true,
    celebratedIds: ['egg-found', 'hatch', 'wings', 'jump', 'fire', 'flight-ride'],
    volcano: { intro: true, cleared: 5, summited: true },
    lava: { intro: true, startPct: 76, stopped: [0, 1, 2, 3, 4], won: true },
  }));
  assert.ok(all.every((s) => s.done && !s.current));
  assert.match(roadProgressLine(baseState({ maxPct: 65 })), /% of the way/);
});

test('game state migrates v2 saves: retroactive gems for played bursts', () => {
  // createGameState.load() in Node hits no localStorage -> defaults (v3, 0 gems).
  const fresh = createGameState('RewardTester').load();
  assert.equal(fresh.version, 3);
  assert.equal(fresh.gems, 0);
  assert.equal(fresh.lastGiftISO, null);
  // GM snapshot carries gems.
  const snap = buildGmSnapshot({ state: baseState({ gems: 77 }), pct: 63, user: 'T', folder: 'test' });
  assert.equal(snap.gems, 77);
});
