import test from 'node:test';
import assert from 'node:assert/strict';
import {
  storyPhaseFor, nextStoryBeat, markBeatSeen, journalEntries,
  quizReaction, nextObjectiveFor, fillName, formatDragonName, PHASE_ORDER,
} from '../dragon/sim/story.js';
import { STORY_PHASES, QUIZ_REACTIONS, UNNAMED } from '../dragon/sim/story_content.js';

function baseState(over = {}) {
  return Object.assign({
    maxPct: 0, hatched: false, rideUnlocked: false, eggFound: true,
    dragonName: null, seenBeatIds: [], visitedStones: [], totalBursts: 0,
  }, over);
}

test('every phase has beats and extras with unique ids', () => {
  const ids = new Set();
  assert.deepEqual(STORY_PHASES.map((p) => p.id), PHASE_ORDER);
  for (const phase of STORY_PHASES) {
    assert.ok(phase.beats.length >= 2, `${phase.id} has ordered beats`);
    assert.ok(phase.extras.length >= 2, `${phase.id} has extras`);
    for (const b of [...phase.beats, ...phase.extras]) {
      assert.ok(b.id && b.title && b.text, `${b.id} complete`);
      assert.ok(!ids.has(b.id), `duplicate beat id ${b.id}`);
      ids.add(b.id);
    }
  }
});

test('phase follows hatch state and maxPct segments', () => {
  assert.equal(storyPhaseFor(baseState()), 'egg');
  assert.equal(storyPhaseFor(baseState({ maxPct: 59 })), 'egg');
  assert.equal(storyPhaseFor(baseState({ maxPct: 62, hatched: true })), 'hatchling');
  assert.equal(storyPhaseFor(baseState({ maxPct: 71, hatched: true })), 'meadow');
  assert.equal(storyPhaseFor(baseState({ maxPct: 84, hatched: true })), 'hills');
  assert.equal(storyPhaseFor(baseState({ maxPct: 93, hatched: true })), 'grove');
  assert.equal(storyPhaseFor(baseState({ maxPct: 100, hatched: true, rideUnlocked: true })), 'summit');
});

test('beats deliver in order, one per call, without repeats', () => {
  const state = baseState();
  const eggPhase = STORY_PHASES[0];
  for (const expected of eggPhase.beats) {
    const { beat } = nextStoryBeat(state);
    assert.equal(beat.id, expected.id);
    markBeatSeen(state, beat.id);
  }
  // Ordered beats exhausted -> extras, unseen first, still no repeats.
  const seenExtras = [];
  for (let i = 0; i < eggPhase.extras.length; i++) {
    const { beat, isRepeat } = nextStoryBeat(state);
    assert.equal(isRepeat, false);
    assert.ok(!seenExtras.includes(beat.id));
    seenExtras.push(beat.id);
    markBeatSeen(state, beat.id);
  }
  // Everything seen -> rotates extras deterministically by totalBursts.
  state.totalBursts = 3;
  const { beat: r1, isRepeat } = nextStoryBeat(state);
  assert.equal(isRepeat, true);
  assert.equal(r1.id, eggPhase.extras[3 % eggPhase.extras.length].id);
});

test('a fast climber still gets skipped key beats (naming) before new-phase beats', () => {
  const state = baseState({ maxPct: 72, hatched: true });   // jumped past hatchling fast
  const { beat } = nextStoryBeat(state);
  assert.equal(beat.id, STORY_PHASES[0].beats[0].id);   // earliest unseen ordered beat wins
  // Mark all egg + hatchling ordered beats seen except naming.
  for (const b of STORY_PHASES[0].beats) markBeatSeen(state, b.id);
  for (const b of STORY_PHASES[1].beats.slice(1)) markBeatSeen(state, b.id);
  const { beat: naming } = nextStoryBeat(state);
  assert.equal(naming.kind, 'name');
});

test('dragon names are title-cased in dialogue', () => {
  assert.equal(formatDragonName('pipa'), 'Pipa');
  assert.equal(formatDragonName('  sparkle  '), 'Sparkle');
  assert.equal(formatDragonName(''), null);
  assert.equal(fillName('{name} waves', 'pipa'), 'Pipa waves');
});

test('beat text fills the dragon name once set', () => {
  const state = baseState({ maxPct: 62, hatched: true, dragonName: 'Sparkle' });
  for (const b of STORY_PHASES[0].beats) markBeatSeen(state, b.id);
  markBeatSeen(state, 'hatch-name');
  const { beat } = nextStoryBeat(state);
  assert.ok(!beat.text.includes('{name}'));
  assert.ok(beat.text.includes('Sparkle'));
  assert.equal(fillName('{name} waves', null), `${UNNAMED} waves`);
});

test('journal returns seen beats in story order with filled names', () => {
  const state = baseState({ dragonName: 'Pip' });
  markBeatSeen(state, 'egg-hum');
  markBeatSeen(state, 'egg-letter-1');
  const j = journalEntries(state);
  assert.deepEqual(j.map((e) => e.id), ['egg-letter-1', 'egg-hum']);
  assert.ok(j.every((e) => e.phaseTitle && e.title && !e.text.includes('{name}')));
});

test('quiz reactions tier by score and rotate by burst count', () => {
  const perfect = quizReaction({ correct: 20, total: 20, totalBursts: 0 });
  assert.ok(perfect.includes('20 of 20'));
  const again = quizReaction({ correct: 20, total: 20, totalBursts: 1 });
  assert.notEqual(perfect, again);
  const tough = quizReaction({ correct: 5, total: 20, totalBursts: 0, dragonName: 'Zip' });
  assert.equal(tough, QUIZ_REACTIONS.tough[0].replaceAll('{score}', '5 of 20').replaceAll('{name}', 'Zip'));
  assert.equal(quizReaction({ correct: 0, total: 0 }), null);
});

test('reactions never leak the flight/ride surprise', () => {
  for (const pool of Object.values(QUIZ_REACTIONS)) {
    for (const line of pool) {
      const t = line.toLowerCase();
      assert.ok(!t.includes('fly') && !t.includes('ride'), `leaked: ${line}`);
    }
  }
});

test('objectives track the journey: feed egg -> name -> visit stones -> ride', () => {
  assert.equal(nextObjectiveFor(baseState({ eggFound: false })).id, 'find-egg');
  assert.equal(nextObjectiveFor(baseState()).id, 'feed-egg');
  assert.equal(nextObjectiveFor(baseState({ maxPct: 62, hatched: true })).id, 'name-dragon');
  assert.equal(nextObjectiveFor(baseState({ maxPct: 62, hatched: true, dragonName: 'Pip' })).id, 'grow-hatchling');
  assert.equal(nextObjectiveFor(baseState({ maxPct: 72, hatched: true, dragonName: 'Pip' })).id, 'visit-meadow');
  assert.equal(nextObjectiveFor(baseState({ maxPct: 72, hatched: true, dragonName: 'Pip', visitedStones: ['meadow'] })).id, 'practice');
  assert.equal(nextObjectiveFor(baseState({ maxPct: 84, hatched: true, dragonName: 'Pip', visitedStones: ['meadow'] })).id, 'visit-hills');
  assert.equal(nextObjectiveFor(baseState({ maxPct: 93, hatched: true, dragonName: 'Pip', visitedStones: ['meadow', 'hills'] })).id, 'visit-grove');
  assert.equal(nextObjectiveFor(baseState({ maxPct: 100, hatched: true, rideUnlocked: true, dragonName: 'Pip' })).id, 'ride');
});

test('egg-phase beats and objectives never name the hatch', () => {
  const eggPhase = STORY_PHASES[0];
  for (const b of [...eggPhase.beats, ...eggPhase.extras]) {
    assert.ok(!b.text.toLowerCase().includes('hatch'), `egg beat ${b.id} leaked hatch`);
  }
  assert.ok(!nextObjectiveFor(baseState()).text.toLowerCase().includes('hatch'));
});

test('recentBursts feed keeps a rolling window of 20', async () => {
  const { createGameState } = await import('../dragon/sim/game_state.js');
  const gs = createGameState('Feed');
  const mem = new Map();
  globalThis.localStorage = { getItem: (k) => mem.get(k) || null, setItem: (k, v) => mem.set(k, v) };
  const s = gs.load();
  assert.deepEqual(s.recentBursts, []);
  for (let i = 0; i < 25; i++) gs.pushRecentBurst(s, { n: i });
  assert.equal(s.recentBursts.length, 20);
  assert.equal(s.recentBursts[0].n, 5);
  assert.equal(s.recentBursts[19].n, 24);
});
