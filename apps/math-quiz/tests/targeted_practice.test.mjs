// Targeted fluency practice engine tests — parsing, canonical (orientation-
// insensitive) keys, filler pool, SERIAL streaming (one target at a time + filler
// by percent), fast-correct streak graduation (record reports it), progress.current
// for the rings, requeue, ends-only-on-all-graduated, and SQLite metadata.
// See docs/2026-06-23_targeted-fluency-practice-todos.md.
import test from 'node:test';
import assert from 'node:assert/strict';
import { buildFactMatrix, makeRng } from '../simulation/adaptive_selector.mjs';
import {
  canonicalKey,
  expandOrientations,
  parseTargetSpec,
  factToText,
  parseTargets,
  parseFillerFacts,
  nearbyReviewFacts,
  createTargetedRun,
} from '../engine/targeted_practice.mjs';

const FM = buildFactMatrix(['+', '-', '*'], [0, 9]);
const FAST = { isCorrect: true, responseTime: 900 };
const SLOW = { isCorrect: true, responseTime: 3500 };
const WRONG = { isCorrect: false, responseTime: 800 };

// Drive the target `key` to graduation by recording fast answers; returns the
// graduated key reported by record() on the final one.
function graduate(run, key, n) {
  let g = null;
  for (let i = 0; i < n; i++) g = run.record({ key, role: 'target' }, FAST).graduated;
  return g;
}

// --- canonical key + orientations ---

test('canonicalKey collapses both orientations for commutative ops', () => {
  assert.equal(canonicalKey(3, 6, '+'), '+|3|6');
  assert.equal(canonicalKey(6, 3, '+'), '+|3|6');
  assert.equal(canonicalKey(7, 8, '*'), '*|7|8');
});

test('canonicalKey keeps order for non-commutative subtraction', () => {
  assert.equal(canonicalKey(9, 4, '-'), '-|9|4');
  assert.equal(canonicalKey(4, 9, '-'), '-|4|9');
});

test('expandOrientations gives both forms, but one for doubles / subtraction', () => {
  assert.equal(expandOrientations(3, 6, '+').length, 2);
  assert.equal(expandOrientations(4, 4, '+').length, 1);
  assert.equal(expandOrientations(9, 4, '-').length, 1);
});

// --- parsing ---

test('parseTargetSpec accepts/drops whitespace and ×/x, rejects garbage', () => {
  assert.equal(parseTargetSpec('3+6').key, '+|3|6');
  assert.equal(parseTargetSpec(' 3 + 6 ').key, '+|3|6');
  assert.equal(parseTargetSpec('8x7').key, '*|7|8');
  assert.equal(parseTargetSpec('hello'), null);
});

test('factToText is the normalized whitespace-free form', () => {
  assert.equal(factToText(parseTargetSpec(' 3 + 6 ')), '3+6');
  assert.equal(factToText(parseTargetSpec('6+0')), '6+0');
});

test('parseTargets dedups the complement, caps at 5', () => {
  const { targets, errors } = parseTargets(['3+6', '6+3', '8+7', '', 'nope', '2+2']);
  assert.deepEqual(targets.map((t) => t.key), ['+|3|6', '+|7|8', '+|2|2']);
  assert.deepEqual(errors, ['nope']);
  const five = parseTargets(['6+3', '6+8', '4+9', '3+7', '3+4', '1+1']);
  assert.equal(five.targets.length, 5);
});

test('parseFillerFacts keeps orientation and does NOT dedup', () => {
  const { facts, errors } = parseFillerFacts(['6+0', '0+6', '', '3+3', 'oops']);
  assert.deepEqual(facts.map(factToText), ['6+0', '0+6', '3+3']);
  assert.deepEqual(errors, ['oops']);
});

test('nearbyReviewFacts excludes targets, stays same-operation, prefers shared operand', () => {
  const review = nearbyReviewFacts(['+|3|6'], FM, { limit: 8 });
  assert.ok(!review.includes('+|3|6'));
  assert.ok(review.every((k) => k.startsWith('+|')));
  assert.equal(review.length, 8);
});

// --- serial streaming ---

test('nextProblem presents ONLY the current target among target items (serial)', () => {
  const { targets } = parseTargets(['3+6', '8+7']);
  const run = createTargetedRun({ targets, factMatrix: FM, percentTarget: 100, rng: makeRng('s') });
  // percentTarget 100 -> every problem is the current target; target2 never shows until target1 graduates
  for (let i = 0; i < 8; i++) {
    const p = run.nextProblem();
    assert.equal(p.key, '+|3|6', 'only target 1 is presented before it graduates');
  }
});

test('graduating the current target advances to the next target', () => {
  const { targets } = parseTargets(['3+6', '8+7']);
  const run = createTargetedRun({ targets, factMatrix: FM, percentTarget: 100, graduationStreak: 3, rng: makeRng('adv') });
  assert.equal(run.currentTargetKey(), '+|3|6');
  const g = graduate(run, '+|3|6', 3);
  assert.equal(g, '+|3|6', 'record reports the graduation');
  assert.equal(run.currentTargetKey(), '+|7|8', 'current advances to target 2');
  assert.equal(run.nextProblem().key, '+|7|8');
});

test('with no filler pool, every problem is the target', () => {
  const { targets } = parseTargets(['3+6']);
  const run = createTargetedRun({ targets, fillerFacts: [], percentTarget: 30, rng: makeRng('nf') });
  for (let i = 0; i < 6; i++) assert.equal(run.nextProblem().role, 'target');
});

test('target tries are separated by >=1 filler; percent 50 -> exactly 1 between (T,F,T,F,...)', () => {
  const { targets } = parseTargets(['3+6']);
  const { facts } = parseFillerFacts(['1+1', '2+2', '0+5']);
  const run = createTargetedRun({ targets, factMatrix: FM, fillerFacts: facts, percentTarget: 50, rng: makeRng('sp') });
  const roles = [];
  for (let i = 0; i < 8; i++) roles.push(run.nextProblem().role);
  assert.deepEqual(roles, ['target', 'filler', 'target', 'filler', 'target', 'filler', 'target', 'filler']);
  // never two targets back-to-back
  for (let i = 1; i < roles.length; i++) assert.ok(!(roles[i] === 'target' && roles[i - 1] === 'target'));
});

test('lower percent -> a larger (random) gap of filler between tries', () => {
  const { targets } = parseTargets(['3+6']);
  const { facts } = parseFillerFacts(['1+1', '2+2', '0+5', '4+4', '5+5']);
  const run = createTargetedRun({ targets, factMatrix: FM, fillerFacts: facts, percentTarget: 25, rng: makeRng('gp') });
  // percent 25 -> spacing round(75/25)=3, so each gap between targets is 1..3 filler
  let gap = 0; const gaps = [];
  for (let i = 0; i < 40; i++) {
    const p = run.nextProblem();
    if (p.role === 'target') { if (i > 0) gaps.push(gap); gap = 0; } else gap++;
  }
  assert.ok(gaps.length > 3);
  assert.ok(gaps.every((g) => g >= 1 && g <= 3), `gaps ${gaps} within [1,3]`);
});

test('filler is drawn as a shuffled deck: the pool is exhausted before any repeat', () => {
  const { targets } = parseTargets(['3+6']);
  const { facts } = parseFillerFacts(['6+0', '0+6', '8+0', '3+3']);  // 4 distinct filler
  const run = createTargetedRun({ targets, factMatrix: FM, fillerFacts: facts, percentTarget: 25, rng: makeRng('dk') });
  const seen = [];
  while (seen.length < 4) { const p = run.nextProblem(); if (p.role === 'filler') seen.push(`${p.num1}+${p.num2}`); }
  assert.deepEqual([...seen].sort(), ['0+6', '3+3', '6+0', '8+0']);   // all 4, no repeat within the deck
});

test('target items alternate orientation across presentations', () => {
  const { targets } = parseTargets(['3+6']);
  const run = createTargetedRun({ targets, factMatrix: FM, percentTarget: 100, rng: makeRng('o') });
  const forms = new Set();
  for (let i = 0; i < 4; i++) { const p = run.nextProblem(); forms.add(`${p.num1}+${p.num2}`); }
  assert.ok(forms.has('3+6') && forms.has('6+3'));
});

// --- graduation (cumulative; rings are never lost) ---

test('a target graduates after N fast-correct (cumulative, not in a row)', () => {
  const { targets } = parseTargets(['3+6']);
  const run = createTargetedRun({ targets, factMatrix: FM, graduationStreak: 3, rng: makeRng('g') });
  const t = { key: '+|3|6', role: 'target' };
  run.record(t, FAST);
  run.record(t, FAST);
  assert.equal(run.progress().current.streak, 2);
  const g = run.record(t, FAST).graduated;
  assert.equal(g, '+|3|6');
  assert.ok(run.isComplete());
});

test('a slow or wrong TARGET answer does NOT lose earned rings (no reset)', () => {
  const { targets } = parseTargets(['3+6']);
  const run = createTargetedRun({ targets, factMatrix: FM, graduationStreak: 3, rng: makeRng('r') });
  const t = { key: '+|3|6', role: 'target' };
  run.record(t, FAST);
  run.record(t, SLOW);                       // slow — keeps the ring
  assert.equal(run.progress().current.streak, 1);
  run.record(t, WRONG);                      // wrong — still keeps it
  assert.equal(run.progress().current.streak, 1);
  run.record(t, FAST);
  run.record(t, FAST);                       // two more fast-correct -> 3 total -> graduate
  assert.ok(run.isComplete());
});

// --- progress.current (rings) ---

test('progress.current reflects the active target + its streak, and clears when done', () => {
  const { targets } = parseTargets(['3+6', '8+7']);
  const run = createTargetedRun({ targets, factMatrix: FM, graduationStreak: 2, rng: makeRng('p') });
  let cur = run.progress().current;
  assert.equal(cur.key, '+|3|6');
  assert.equal(cur.index, 0);
  assert.equal(cur.streak, 0);
  assert.equal(cur.graduationStreak, 2);
  graduate(run, '+|3|6', 2);
  assert.equal(run.progress().current.key, '+|7|8');   // advanced
  graduate(run, '+|7|8', 2);
  assert.equal(run.progress().current, null);          // all done
  assert.ok(run.isComplete());
});

// --- requeue (Flag-previous insert) ---

test('requeue re-asks a problem within a few problems', () => {
  const { targets } = parseTargets(['3+6']);
  const run = createTargetedRun({ targets, factMatrix: FM, percentTarget: 100, rng: makeRng('q') });
  run.nextProblem();
  const reItem = { key: '+|5|5', num1: 5, num2: 5, operation: '+', role: 'filler' };
  run.requeue(reItem, 2);
  const seen = [];
  for (let i = 0; i < 4; i++) seen.push(run.nextProblem().key);
  assert.ok(seen.includes('+|5|5'), 'the requeued problem reappears');
});

// --- completion / metadata ---

test('the run ends only when ALL targets graduate (no problem cap)', () => {
  const { targets } = parseTargets(['8+7']);
  const run = createTargetedRun({ targets, factMatrix: FM, graduationStreak: 3, rng: makeRng('c') });
  for (let i = 0; i < 20; i++) { run.nextProblem(); run.record({ key: '+|7|8', role: 'target' }, SLOW); }
  assert.equal(run.isComplete(), false);
  graduate(run, '+|7|8', 3);
  assert.ok(run.isComplete());
  assert.equal(run.completionReason(), 'all-graduated');
  assert.equal(run.nextProblem(), null);
});

test('metadata captures targets, params, and per-target tallies (no burst fields)', () => {
  const { targets } = parseTargets(['3+6', '8+7']);
  const run = createTargetedRun({ targets, factMatrix: FM, percentTarget: 30, graduationStreak: 5, fastMs: 4000, rng: makeRng('m') });
  run.nextProblem();
  run.record({ key: '+|3|6', role: 'target' }, FAST);
  const md = run.metadata();
  assert.equal(md.mode, 'targeted-practice');
  assert.deepEqual(md.targets, ['+|3|6', '+|7|8']);
  assert.equal(md.percentTarget, 30);
  assert.equal(md.graduationStreak, 5);
  assert.equal(md.fastMs, 4000);
  assert.equal(md.burstSize, undefined);
  assert.equal(md.maxBursts, undefined);
  assert.equal(md.problemsPresented, 1);
  const t36 = md.perTarget.find((p) => p.key === '+|3|6');
  assert.equal(t36.attempts, 1);
  assert.equal(t36.fastCorrect, 1);
});

test('createTargetedRun throws with no targets', () => {
  assert.throws(() => createTargetedRun({ targets: [], factMatrix: FM }), /at least one target/);
});

test('a full run graduates all targets by driving real problems', () => {
  const { targets } = parseTargets(['8+7', '3+6']);
  const run = createTargetedRun({ targets, factMatrix: FM, percentTarget: 60, graduationStreak: 3, rng: makeRng('drive') });
  let guard = 0, item;
  while ((item = run.nextProblem()) !== null && guard++ < 200) {
    run.record(item, item.role === 'target' ? FAST : SLOW);
  }
  assert.ok(run.isComplete());
  assert.equal(run.progress().graduatedTargets, 2);
});
