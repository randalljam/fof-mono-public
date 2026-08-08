// Smoke test for the headless dragon playthrough loop: a few capped bursts
// against the in-memory transport (no dev server), proving the plumbing —
// seed -> feast burst -> answers -> dragon session JSON -> import -> fluency
// recompute -> high-water/milestone bookkeeping -> event stream. The full
// server-backed run is the CLI (see dragon/playtests/README.md).
import test from 'node:test';
import assert from 'node:assert/strict';
import { createSimLearner } from '../simulation/dragon_learner.mjs';
import { buildSeedSessions } from '../simulation/dragon_seed.mjs';
import {
  createAppFns, createMemoryTransport, runPlaythrough, buildBurstProblems,
  buildDragonSessionJson,
} from '../simulation/dragon_playthrough.mjs';

let SQL = null;
try {
  const { readFileSync } = await import('node:fs');
  const initSqlJs = (await import('sql.js')).default;
  const wasmBinary = readFileSync(new URL('./node_modules/sql.js/dist/sql-wasm.wasm', import.meta.url));
  SQL = await initSqlJs({ wasmBinary });
} catch { /* optional dep */ }

const fns = createAppFns();

function seedBytes(user) {
  const db = new SQL.Database();
  fns.createTables(db);
  for (const s of buildSeedSessions({ seed: 'smoke-seed', user })) {
    fns.importSessionData(db, s, `seed_${s.session.start_time}.sqlite`);
  }
  const bytes = db.export();
  db.close();
  return bytes;
}

test('buildDragonSessionJson matches the dragon-feast session shape', () => {
  const json = buildDragonSessionJson({
    user: 'T', folder: 'playtest',
    problems: [{
      id: 'x-0', fact_key: '+|1|2', problem_text: '1 + 2', correct_answer: 3,
      user_answer_string: '3', user_answer: 3, is_correct: true,
      response_time_ms: 700, presented_at: 1, flags: [],
    }],
    kind: 'list-complete', startTime: '2026-07-03_100000', endTime: '2026-07-03_100100',
  });
  assert.equal(json.version, '1.1');
  assert.equal(json.session.settings.preset, 'dragon-feast');
  assert.equal(json.session.settings.note, 'mode:dragon;outcome:list-complete');
  assert.deepEqual(json.session.settings.number_range, [0, 9]);
  assert.equal(json.session.summary.correct_answers, 1);
});

test('buildBurstProblems: feast list from attempts, clamped fallback when blank', () => {
  const fallback = buildBurstProblems({ fns, attempts: [], feastPreset: null, thresholds: fns.thresholds, rngSeed: 'x', fallbackRng: Math.random });
  assert.ok(fallback.length >= 10 && fallback.length <= 20);
  for (const p of fallback) assert.match(p, /^\d \+ \d$/);
  const attempts = [];
  for (let i = 0; i < 5; i++) attempts.push({ problem_text: '7 + 8', is_correct: 0, response_time_ms: 6000, flags_json: null, session_id: 's1', start_time: '2026-07-01_090000', attempt_id: i });
  const feast = buildBurstProblems({ fns, attempts, feastPreset: null, thresholds: fns.thresholds, rngSeed: 'x', fallbackRng: Math.random });
  // Preset count (20) + two easy-start warm-ups.
  assert.ok(feast.length >= 12 && feast.length <= 22);
  const sumOf = (text) => {
    const m = String(text).match(/^(\d)\s*\+\s*(\d)$/);
    return m ? Number(m[1]) + Number(m[2]) : NaN;
  };
  assert.ok(sumOf(feast[0]) < 10, `easy-start first should be single-digit sum, got ${feast[0]}`);
  assert.ok(Number.isFinite(sumOf(feast[1])), `easy-start second should be addition, got ${feast[1]}`);
});

test('capped in-memory playthrough: fluency rises, events are coherent', { skip: SQL ? false : 'sql.js not installed' }, async () => {
  const user = 'SmokeKid';
  const learner = createSimLearner({ seed: 'smoke-learner' });
  const transport = createMemoryTransport({ SQL, fns, user, seedBytes: seedBytes(user) });
  const { events, state, bursts, finalPct } = await runPlaythrough({
    SQL, fns, transport, learner, user, folder: 'playtest', maxBursts: 4, seed: 'smoke',
  });
  assert.equal(bursts, 4);
  const runStart = events.find((e) => e.type === 'run-start');
  const burstEnds = events.filter((e) => e.type === 'burst-end');
  assert.equal(burstEnds.length, 4);
  assert.ok(runStart.meta.startPct > 20 && runStart.meta.startPct < 60, `seed start ${runStart.meta.startPct}`);
  assert.ok(finalPct >= runStart.meta.startPct, 'fluency should not drop over a few bursts');
  for (const b of burstEnds) {
    // Preset count clamped 10–20, plus two easy-start warm-ups when history exists.
    assert.ok(b.total >= 12 && b.total <= 22);
    assert.ok(b.correct >= 0 && b.correct <= b.total);
    assert.ok(b.byCategory['tough-21'].total === 21);
  }
  const problems = events.filter((e) => e.type === 'problem');
  assert.equal(problems.length, burstEnds.reduce((s, b) => s + b.total, 0));
  assert.equal(state.totalBursts, 4);
  assert.ok(!state.rideUnlocked, 'four bursts cannot reach 100%');
});

test('full in-memory arc reaches 100% and celebrates every milestone once', { skip: SQL ? false : 'sql.js not installed' }, async () => {
  const user = 'SmokeArc';
  const learner = createSimLearner({ seed: 'smoke-arc' });
  const transport = createMemoryTransport({ SQL, fns, user, seedBytes: seedBytes(user) });
  const { events, state, finalPct } = await runPlaythrough({
    SQL, fns, transport, learner, user, folder: 'playtest', maxBursts: 80, seed: 'smoke-arc',
  });
  assert.equal(Math.round(finalPct), 100);
  assert.ok(state.rideUnlocked);
  assert.ok(state.hatched);
  const milestoneIds = events.filter((e) => e.type === 'milestone').map((m) => m.id);
  assert.deepEqual(milestoneIds, ['hatch', 'wings', 'jump', 'fire', 'flight-ride']);
  // One reveal per burst-end at most (the game's celebration cadence).
  const byBurst = new Map();
  for (const m of events.filter((e) => e.type === 'milestone')) {
    byBurst.set(m.burst, (byBurst.get(m.burst) || 0) + 1);
  }
  for (const [b, n] of byBurst) assert.equal(n, 1, `burst ${b} revealed ${n} milestones`);
  // Story arc: the first letter opens the game, every burst delivers a beat
  // (one each), no non-repeat beat repeats, and the dragon gets named.
  const storyBeats = events.filter((e) => e.type === 'story-beat');
  assert.equal(storyBeats[0].id, 'egg-letter-1');
  assert.equal(storyBeats[0].burst, 0);
  const perBurst = new Map();
  for (const b of storyBeats) perBurst.set(b.burst, (perBurst.get(b.burst) || 0) + 1);
  for (const [b, n] of perBurst) assert.equal(n, 1, `burst ${b} got ${n} beats`);
  const freshIds = storyBeats.filter((b) => !b.isRepeat).map((b) => b.id);
  assert.equal(new Set(freshIds).size, freshIds.length, 'fresh beats never repeat');
  assert.ok(freshIds.includes('hatch-name'));
  assert.equal(state.dragonName, 'SimSpark');
  // The run stops at 100%, but continued practice must reach the finale beat
  // (earlier-phase beats queue ahead of it for fast climbers).
  const { nextStoryBeat, markBeatSeen } = await import('../dragon/sim/story.js');
  let sawFinale = state.seenBeatIds.includes('summit-beacon-lit');
  for (let i = 0; !sawFinale && i < 40; i++) {
    const n = nextStoryBeat(state);
    if (!n) break;
    if (!n.isRepeat) markBeatSeen(state, n.beat.id);
    sawFinale = n.beat.id === 'summit-beacon-lit';
  }
  assert.ok(sawFinale, 'continued practice reaches the beacon finale');
  // Every burst also gets a reaction line.
  const reactions = events.filter((e) => e.type === 'story-reaction');
  assert.equal(reactions.length, events.filter((e) => e.type === 'burst-end').length);
});
