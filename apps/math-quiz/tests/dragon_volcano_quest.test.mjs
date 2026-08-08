import test from 'node:test';
import assert from 'node:assert/strict';
import {
  VOLCANO, TOTAL_BOULDERS, ringMountainSpecs, terrainHeightAt,
  BOULDER_STAGES, boulderPos, blockRadius, atSummit, trailTarget,
} from '../dragon/sim/volcano_quest.js';
import { nextObjectiveFor } from '../dragon/sim/story.js';
import { buildGmSnapshot } from '../dragon/sim/gm_state.js';
import { createGameState } from '../dragon/sim/game_state.js';

function questState(over = {}) {
  return Object.assign({
    maxPct: 65, hatched: true, rideUnlocked: false, eggFound: true,
    dragonName: 'Ember', seenBeatIds: [], visitedStones: [], totalBursts: 3,
    volcano: { intro: true, cleared: 0, summited: false },
  }, over);
}

test('terrain: volcano plateau, slope, and flat ground', () => {
  assert.equal(terrainHeightAt(VOLCANO.x, VOLCANO.z), VOLCANO.height);
  // Anywhere on the plateau is full height; the base edge is ground level.
  assert.equal(terrainHeightAt(VOLCANO.x + VOLCANO.topR - 0.1, VOLCANO.z), VOLCANO.height);
  assert.equal(terrainHeightAt(VOLCANO.x + VOLCANO.baseR, VOLCANO.z), 0);
  // Slope height decreases monotonically walking away from the axis.
  let prev = VOLCANO.height + 1;
  for (let d = VOLCANO.topR; d <= VOLCANO.baseR; d += 1) {
    const h = terrainHeightAt(VOLCANO.x, VOLCANO.z + d);
    assert.ok(h < prev, `height decreasing at d=${d}`);
    prev = h;
  }
  // The nest clearing stays flat.
  assert.equal(terrainHeightAt(0, -2), 0);
  assert.equal(terrainHeightAt(5, 5), 0);
});

test('terrain: every ring mountain is climbable at its center', () => {
  const specs = ringMountainSpecs();
  assert.equal(specs.length, 12);
  for (const m of specs) {
    const h = terrainHeightAt(m.x, m.z);
    assert.ok(h > 5, `peak at (${m.x.toFixed(0)}, ${m.z.toFixed(0)}) has height ${h}`);
    assert.equal(terrainHeightAt(m.x + m.radius + 1, m.z) >= 0, true);
  }
});

test('boulders: five stages march up the south face toward the summit', () => {
  assert.equal(BOULDER_STAGES.length, TOTAL_BOULDERS);
  let prevD = Infinity;
  let prevH = -1;
  for (let k = 0; k < TOTAL_BOULDERS; k++) {
    const p = boulderPos(k);
    const d = Math.hypot(p.x - VOLCANO.x, p.z - VOLCANO.z);
    assert.ok(d < prevD, `stage ${k} closer to the summit axis`);
    assert.ok(d > VOLCANO.topR, `stage ${k} below the plateau`);
    assert.ok(d < VOLCANO.baseR, `stage ${k} on the mountain`);
    assert.ok(p.y > prevH, `stage ${k} higher up the slope`);
    assert.ok(p.z > VOLCANO.z, `stage ${k} on the south (nest-facing) side`);
    prevD = d;
    prevH = p.y;
  }
});

test('block radius gates the climb stage by stage, then opens', () => {
  for (let cleared = 0; cleared < TOTAL_BOULDERS; cleared++) {
    const r = blockRadius(cleared);
    const next = boulderPos(cleared);
    const nextD = Math.hypot(next.x - VOLCANO.x, next.z - VOLCANO.z);
    assert.ok(r > nextD, `blocked just outside boulder ${cleared}`);
    assert.ok(r - nextD < 6, `boulder ${cleared} still within interact range from the gate`);
  }
  assert.equal(blockRadius(TOTAL_BOULDERS), null);
  // While anything is uncleared, the summit is out of reach.
  assert.ok(blockRadius(TOTAL_BOULDERS - 1) > VOLCANO.topR + 0.8);
});

test('atSummit is true on the plateau, false on the slope and at the nest', () => {
  assert.ok(atSummit(VOLCANO.x, VOLCANO.z));
  assert.ok(atSummit(VOLCANO.x + 2, VOLCANO.z + 2));
  assert.ok(!atSummit(VOLCANO.x, VOLCANO.z + VOLCANO.baseR - 2));
  assert.ok(!atSummit(0, -2));
});

test('trail targets the next boulder, then the summit', () => {
  const first = trailTarget(0);
  const b0 = boulderPos(0);
  assert.deepEqual({ x: first.x, z: first.z }, { x: b0.x, z: b0.z });
  const last = trailTarget(TOTAL_BOULDERS);
  assert.equal(last.x, VOLCANO.x);
  assert.equal(last.z, VOLCANO.z);
});

test('objective: volcano challenge takes over until summited', () => {
  const active = nextObjectiveFor(questState({ volcano: { intro: true, cleared: 2, summited: false } }));
  assert.equal(active.id, 'volcano-boulders');
  assert.match(active.text, /2 of 5/);
  const open = nextObjectiveFor(questState({ volcano: { intro: true, cleared: 5, summited: false } }));
  assert.equal(open.id, 'volcano-summit');
  // Summited (or not yet introduced) falls back to the normal story objectives.
  const done = nextObjectiveFor(questState({ volcano: { intro: true, cleared: 5, summited: true } }));
  assert.notEqual(done.id, 'volcano-boulders');
  const preIntro = nextObjectiveFor(questState({ volcano: { intro: false, cleared: 0, summited: false } }));
  assert.notEqual(preIntro.id, 'volcano-boulders');
  // States without the volcano key (old saves, tests) behave as before.
  const legacy = nextObjectiveFor(questState({ volcano: undefined }));
  assert.ok(legacy.id && legacy.id !== 'volcano-boulders');
});

test('game state default includes the volcano challenge; GM snapshot carries it', () => {
  const gs = createGameState('VolcanoTester');
  const state = gs.load();   // no localStorage in node -> defaults
  assert.deepEqual(state.volcano, { intro: false, cleared: 0, summited: false });
  const snap = buildGmSnapshot({ state: questState({ volcano: { intro: true, cleared: 3, summited: false } }), pct: 66, user: 'T', folder: 'test' });
  assert.deepEqual(snap.volcano, { intro: true, cleared: 3, summited: false });
  assert.equal(snap.objective.id, 'volcano-boulders');
});
