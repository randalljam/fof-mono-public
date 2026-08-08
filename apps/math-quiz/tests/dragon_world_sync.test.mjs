import test from 'node:test';
import assert from 'node:assert/strict';
import { worldProgressScore } from '../dragon/world_sync.js';

test('worldProgressScore ranks painted nest above blank wipe', () => {
  const rich = {
    gems: 208,
    dragonName: 'pipa',
    totalBursts: 19,
    maxPct: 87,
    stations: {
      signs: { 'sign-welcome': "Pipa's Dragon Valley", 'sign-dragon': 'tickle' },
      levels: { fountain: 2, nest: 0, trees: 1 },
    },
    volcano: { cleared: 5, summited: true },
  };
  const wiped = {
    gems: 5,
    dragonName: null,
    totalBursts: 0,
    maxPct: 0,
    stations: {
      signs: { 'sign-welcome': '', 'sign-dragon': '' },
      levels: { fountain: 0, nest: 0, trees: 0 },
    },
    volcano: { cleared: 0, summited: false },
  };
  assert.ok(worldProgressScore(rich) > worldProgressScore(wiped));
  assert.ok(worldProgressScore(rich) > 30);
});

test('worldProgressScore prefers higher fluency when the rest ties', () => {
  const base = {
    gems: 10,
    totalBursts: 5,
    dragonName: 'pipa',
    stations: { signs: {}, levels: {} },
    volcano: { cleared: 0, summited: false },
    lava: { stopped: [] },
    seenBeatIds: [],
  };
  assert.ok(worldProgressScore({ ...base, maxPct: 87 }) > worldProgressScore({ ...base, maxPct: 86 }));
});
