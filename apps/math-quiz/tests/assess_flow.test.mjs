// C3 tests — anchor assess flow: fixed hard-first sequence, warm-up discard,
// glitch re-deliver-and-confirm, and the predictive-mastery conclusion.
import test from 'node:test';
import assert from 'node:assert/strict';
import { buildFactMatrix, makeRng } from '../simulation/adaptive_selector.mjs';
import { sampleResponse, buildSkillMap } from '../simulation/simulation.mjs';
import { PROFILE_01, PROFILE_03 } from '../simulation/profiles.mjs';
import { buildAssessSequence, createAssessRun, createThoroughRun, findSlowEasyFacts } from '../engine/assess_flow.mjs';
import { buildAnchorAdditionPlan } from '../engine/addition_segmentation.mjs';

const OPS = ['+', '-', '*'];
const PREDICTIVE = { predictive_min_coverage: 0.45, predictive_hard_min_coverage: 0.75, minAccuracy: 0.8 };

function drive(run, learner, guard = 4000) {
  let key, n = 0;
  while ((key = run.next()) !== null) {
    run.record(key, learner(key));
    if (run.isConcluded()) break;
    if (++n > guard) break;
  }
  return run.result();
}

test('buildAssessSequence puts hard facts first', () => {
  const fm = buildFactMatrix(OPS, [0, 9]);
  const seq = buildAssessSequence(fm);
  const firstEasyIdx = seq.findIndex(k => !fm.get(k).isHard);
  const lastHardIdx = seq.reduce((acc, k, i) => (fm.get(k).isHard ? i : acc), -1);
  assert.ok(lastHardIdx < firstEasyIdx, 'all hard facts precede the first easy fact');
  assert.equal(seq.length, fm.size);
});

test('fluent learner reaches predictive mastery on a partial sample', () => {
  const fm = buildFactMatrix(OPS, [0, 9]);
  const rng = makeRng('assess-fluent');
  const learner = () => sampleResponse(rng, 'fluent', PROFILE_03.response_model);
  const run = createAssessRun(fm, { predictiveParams: PREDICTIVE });
  const res = drive(run, learner);
  assert.equal(res.status, 'predictive-mastery');
  assert.ok(res.coverage >= 0.45, `coverage ${res.coverage}`);
  assert.ok(res.sampled < res.total, 'conclusion drawn from a partial sample');
});

test('warm-up problems are discarded from the judgment set', () => {
  const fm = buildFactMatrix(OPS, [0, 9]);
  const rng = makeRng('assess-warmup');
  const run = createAssessRun(fm, { warmupDiscard: 2, predictiveParams: PREDICTIVE });
  for (let i = 0; i < 5; i++) { const k = run.next(); run.record(k, sampleResponse(rng, 'fluent', PROFILE_03.response_model)); }
  const s = run.stats();
  assert.equal(s.warmup, 2);
  assert.ok(s.countedFacts <= 3, `counted ${s.countedFacts} excludes the 2 warm-up problems`);
});

test('isolated glitches are re-delivered, confirmed non-representative, and discarded', () => {
  const fm = buildFactMatrix(OPS, [0, 9]);
  const rng = makeRng('assess-glitch');
  const glitchy = new Set(['*|6|9', '*|7|8', '-|9|4']); // hard facts that "slip" once
  const seen = new Set();
  const learner = (key) => {
    if (glitchy.has(key) && !seen.has(key)) { seen.add(key); return { isCorrect: true, responseTime: 5000 }; } // slow slip
    return sampleResponse(rng, 'fluent', PROFILE_03.response_model);                                          // fast on recheck
  };
  const run = createAssessRun(fm, { predictiveParams: PREDICTIVE });
  const res = drive(run, learner);
  assert.equal(res.status, 'predictive-mastery', 'glitches must not block a true fluent conclusion');
  assert.ok(res.glitches >= 1, `at least one slip recognized as a glitch (got ${res.glitches})`);
});

test('a genuinely non-fluent learner does NOT trip mastery and surfaces weak facts', () => {
  const fm = buildFactMatrix(OPS, [0, 9]);
  const rng = makeRng('assess-weak');
  const skillMap = buildSkillMap(fm, PROFILE_01.initial_state); // mostly 'unknown' across sub/mult
  const learner = (key) => sampleResponse(rng, skillMap.get(key) || 'unknown', PROFILE_01.response_model);
  const run = createAssessRun(fm, { predictiveParams: PREDICTIVE });
  const res = drive(run, learner);
  assert.notEqual(res.status, 'predictive-mastery');
  assert.ok(res.confirmedWeak.length > 0, 'weak facts are surfaced for targeting');
});

// The live anchor (addition) path: a curated segmentation plan administered in
// full (truncateOnMastery:false), with a custom display orientation per item.
const ADDITION_PREDICTIVE = { predictive_min_coverage: 0.7, predictive_hard_min_coverage: 0, minAccuracy: 0.8 };

test('curated addition plan: fluent learner runs the full plan and concludes fluent', () => {
  const fm = buildFactMatrix(['+'], [0, 9]);
  const plan = buildAnchorAdditionPlan({ seed: 'flow-fluent' });
  const rng = makeRng('flow-fluent-resp');
  const run = createAssessRun(fm, { sequence: plan, predictiveParams: ADDITION_PREDICTIVE, truncateOnMastery: false });

  let key, n = 0, sawComplement = false;
  while ((key = run.next()) !== null) {
    const item = run.currentItem();
    assert.equal(item.key, key, 'currentItem matches the presented key');
    if (item.num1 > item.num2) sawComplement = true; // complement orientation displayed
    run.record(key, sampleResponse(rng, 'fluent', PROFILE_03.response_model));
    if (++n > 500) break;
  }
  const res = run.result();
  assert.equal(res.status, 'predictive-mastery');
  assert.ok(res.coverage >= 0.7, `coverage ${res.coverage}`);
  assert.ok(sawComplement, 'plan presents some facts in complement (reversed) orientation');
});

test('curated addition plan: non-fluent learner concludes weak with facts to practice', () => {
  const fm = buildFactMatrix(['+'], [0, 9]);
  const plan = buildAnchorAdditionPlan({ seed: 'flow-weak' });
  const rng = makeRng('flow-weak-resp');
  const skillMap = buildSkillMap(fm, PROFILE_01.initial_state);
  const run = createAssessRun(fm, { sequence: plan, predictiveParams: ADDITION_PREDICTIVE, truncateOnMastery: false });
  const res = drive(run, (key) => sampleResponse(rng, skillMap.get(key) || 'unknown', PROFILE_01.response_model));
  assert.notEqual(res.status, 'predictive-mastery');
  assert.ok(res.confirmedWeak.length > 0);
});

// Continue-to-100% (thorough) run — must be glitch-tolerant. Regression for
// TL's run: a fully-correct learner failed 100% because one fact (0+2) was
// answered at 2017 ms (17 ms over) with no chance to re-demonstrate.
test('thorough run re-asks a slow-only fact and certifies it on a fast retry', () => {
  const fm = buildFactMatrix(['+'], [0, 9]);
  const prior = new Map();
  for (const [k] of fm) prior.set(k, [{ isCorrect: true, responseTime: 1200 }]); // all fast...
  prior.set('+|0|2', [{ isCorrect: true, responseTime: 2017 }]);                  // ...except 0+2 (TL)
  const tr = createThoroughRun(fm, { fastMs: 2000, priorAttempts: prior });
  assert.equal(tr.next(), '+|0|2', 'only the not-yet-fast fact is re-asked');
  tr.record('+|0|2', { isCorrect: true, responseTime: 1300 });                    // clean retry
  assert.equal(tr.next(), null);
  assert.equal(tr.result().passes, true);
});

test('thorough run flags a fact that stays slow even after retries', () => {
  const fm = buildFactMatrix(['+'], [0, 9]);
  const prior = new Map();
  for (const [k] of fm) prior.set(k, [{ isCorrect: true, responseTime: 1200 }]);
  prior.set('+|3|9', [{ isCorrect: true, responseTime: 3000 }]);
  const tr = createThoroughRun(fm, { fastMs: 2000, priorAttempts: prior, maxRetries: 2 });
  let key, guard = 0;
  while ((key = tr.next()) !== null) { tr.record(key, { isCorrect: true, responseTime: 3000 }); if (++guard > 12) break; }
  const r = tr.result();
  assert.equal(r.passes, false);
  assert.deepEqual(r.needsWork.map((w) => w.key), ['+|3|9']);
});

test('thorough run covers never-attempted facts to reach 100%', () => {
  const fm = buildFactMatrix(['+'], [0, 9]);
  const tr = createThoroughRun(fm, { fastMs: 2000, priorAttempts: new Map() });
  let key, n = 0;
  while ((key = tr.next()) !== null) { tr.record(key, { isCorrect: true, responseTime: 1000 }); if (++n > 200) break; }
  const r = tr.result();
  assert.equal(r.passes, true);
  assert.equal(r.certified, fm.size);
});

test('reorderRemaining re-sorts only the not-yet-presented items (HF -> EF revert)', () => {
  const fm = buildFactMatrix(['+'], [0, 9]);
  // items carry a category so we can sort by it
  const seq = [
    { key: '+|8|9', num1: 8, num2: 9, operation: '+', category: 'tough-21' },
    { key: '+|0|1', num1: 0, num2: 1, operation: '+', category: 'add-zero' },
    { key: '+|7|8', num1: 7, num2: 8, operation: '+', category: 'tough-21' },
    { key: '+|1|2', num1: 1, num2: 2, operation: '+', category: 'add-one' },
  ];
  const run = createAssessRun(fm, { sequence: seq, warmupDiscard: 0, truncateOnMastery: false });
  assert.equal(run.next(), '+|8|9');                 // present the first item
  const RANK = { 'add-zero': 0, 'add-one': 1, 'tough-21': 4 };
  run.reorderRemaining((it) => (RANK[it.category] ?? 5));
  assert.equal(run.next(), '+|0|1');                 // remaining now easy-first
  assert.equal(run.next(), '+|1|2');
  assert.equal(run.next(), '+|7|8');
});

test('a deviating fact is re-asked later, spaced by redeliverSpacing (not right away)', () => {
  const fm = buildFactMatrix(['+'], [0, 9]);
  const keys = [...fm.keys()].slice(0, 8);
  const run = createAssessRun(fm, { sequence: keys, warmupDiscard: 0, truncateOnMastery: false, redeliverSpacing: 5 });
  const k0 = run.next();
  run.record(k0, { isCorrect: true, responseTime: 3000 }); // slow → re-ask, but spaced out
  const between = [];
  for (let i = 0; i < 5; i++) between.push(run.next());
  assert.ok(!between.includes(k0), 'not re-asked within the next 5 problems');
  assert.equal(run.next(), k0, 're-asked after ~5 intervening problems');
});

// UI correction flow: record(noRecheck) counts the miss immediately (no auto
// re-ask), and the controller drives the re-ask itself via insert(gap).
test('record(noRecheck) counts a miss now and does NOT auto re-ask it', () => {
  const fm = buildFactMatrix(['+'], [0, 9]);
  const keys = [...fm.keys()].slice(0, 8);
  const run = createAssessRun(fm, { sequence: keys, warmupDiscard: 0, truncateOnMastery: false, redeliverSpacing: 5 });
  const k0 = run.next();
  run.record(k0, { isCorrect: false, responseTime: 3000 }, { noRecheck: true }); // miss, controller-managed
  const between = [];
  for (let i = 0; i < 6; i++) { const k = run.next(); if (k === null) break; between.push(k); }
  assert.ok(!between.includes(k0), 'noRecheck miss is not auto-redelivered');
  assert.equal(run.stats().confirmedWeak, 1, 'the miss is counted as a confirmed weakness right away');
});

test('insert(gap) re-asks the current fact gap problems later (Continue & insert)', () => {
  const fm = buildFactMatrix(['+'], [0, 9]);
  const keys = [...fm.keys()].slice(0, 10);
  const run = createAssessRun(fm, { sequence: keys, warmupDiscard: 0, truncateOnMastery: false });
  const k0 = run.next();
  run.record(k0, { isCorrect: false, responseTime: 3000 }, { noRecheck: true });
  run.insert(5);                                       // re-ask 5 problems from now
  const between = [];
  for (let i = 0; i < 5; i++) between.push(run.next());
  assert.ok(!between.includes(k0), 'not re-asked within the next 5 problems');
  assert.equal(run.next(), k0, 're-asked after ~5 intervening problems');
});

test('autoRedeliver:false never auto re-asks a slow answer (a fixed list stays its length)', () => {
  const fm = buildFactMatrix(['+'], [0, 9]);
  const keys = [...fm.keys()].slice(0, 6);
  const run = createAssessRun(fm, { sequence: keys, warmupDiscard: 0, truncateOnMastery: false, autoRedeliver: false });
  let presented = 0;
  while (run.next() !== null) {
    presented++;
    if (presented > 50) throw new Error('runaway: slow answers were re-asked');
    run.record(run.currentItem().key, { isCorrect: true, responseTime: 5000 }); // correct but SLOW (> fastMs)
  }
  assert.equal(presented, keys.length); // exactly the list length — no glitch re-asks
});

test('default (autoRedeliver:true) DOES re-ask a slow answer (auto mode keeps glitch tolerance)', () => {
  const fm = buildFactMatrix(['+'], [0, 9]);
  const keys = [...fm.keys()].slice(0, 6);
  const run = createAssessRun(fm, { sequence: keys, warmupDiscard: 0, truncateOnMastery: false });
  let presented = 0;
  while (run.next() !== null) {
    presented++;
    if (presented > 50) break;
    run.record(run.currentItem().key, { isCorrect: true, responseTime: 5000 });
  }
  assert.ok(presented > keys.length, 'slow answers are re-asked, so more than the base length is presented');
});

test('insertItem re-asks a SPECIFIC (previous) fact, not the current one (Flag previous & insert)', () => {
  const fm = buildFactMatrix(['+'], [0, 9]);
  const keys = [...fm.keys()].slice(0, 10);
  const run = createAssessRun(fm, { sequence: keys, warmupDiscard: 0, truncateOnMastery: false });
  const prevKey = run.next();                           // problem N-1
  run.record(prevKey, { isCorrect: true, responseTime: 900 });
  const curKey = run.next();                            // problem N now on screen
  // Flag previous & insert: re-ask N-1 in 5, while N stays current.
  run.insertItem({ key: prevKey, ...fm.get(prevKey) }, 5);
  run.record(curKey, { isCorrect: true, responseTime: 900 });
  const seen = [];
  for (let i = 0; i < 5; i++) seen.push(run.next());
  assert.ok(!seen.includes(prevKey), 'previous fact not re-asked within the gap');
  assert.equal(run.next(), prevKey, 'previous fact re-asked after the gap');
});

// Realism guardrail: slow on multiple EASY facts trips an anomaly.
test('guardrail: findSlowEasyFacts flags easy facts with no fast+correct attempt', () => {
  const fm = buildFactMatrix(['+'], [0, 9]);
  const attempts = new Map([
    ['+|0|2', [{ isCorrect: true, responseTime: 4000 }]],  // easy, slow
    ['+|1|3', [{ isCorrect: false, responseTime: 1000 }]], // easy, wrong
    ['+|8|9', [{ isCorrect: true, responseTime: 4000 }]],  // HARD, slow — not counted
    ['+|2|4', [{ isCorrect: true, responseTime: 1200 }]],  // easy, fine
  ]);
  assert.deepEqual(findSlowEasyFacts(attempts, fm, 2000).sort(), ['+|0|2', '+|1|3']);
});

test('guardrail: run anomaly() trips after several slow easy facts', () => {
  const fm = buildFactMatrix(['+'], [0, 5]); // all easy (max <= 5)
  const seq = ['+|0|2', '+|1|3', '+|2|4', '+|0|5'];
  const run = createAssessRun(fm, { sequence: seq, warmupDiscard: 0, truncateOnMastery: false, anomalyEasyThreshold: 3 });
  assert.equal(run.anomaly(), null);
  let key, n = 0;
  while ((key = run.next()) !== null) { run.record(key, { isCorrect: true, responseTime: 4000 }); if (++n >= 3) break; } // 3 slow easy
  const a = run.anomaly();
  assert.ok(a && a.type === 'slow-on-easy');
  assert.equal(a.facts.length, 3);
});
