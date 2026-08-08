// Unit tests for the fluency-based problem-list generator (fluency_core.js).
// Pure logic: load math_utils.js + fluency_core.js into the vm; no DOM needed.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createAppContext } from './load_app.mjs';

const ctx = createAppContext(['math_utils.js', 'fluency_core.js']);
const ev = ctx.__eval;
const evJ = ctx.__evalJson;

// A deterministic LCG so generated lists are reproducible across runs/engines.
ev(`globalThis.makeRng = (seed) => { let s = seed >>> 0;
  return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / 4294967296; }; }`);

// Build N attempts on one fact (all same ms/correctness), with increasing timestamps.
function attemptsFor(text, { n = 5, ms = 900, correct = n, base = 1 } = {}) {
  const out = [];
  for (let i = 0; i < n; i++) {
    out.push({
      problem_text: text, is_correct: i < correct ? 1 : 0, response_time_ms: ms,
      start_time: `2026-06-${String(i + 1).padStart(2, '0')}_100000`, attempt_id: base + i
    });
  }
  return out;
}

test('enumerateFactUniverse covers ordered pairs and skips divide-by-zero', () => {
  assert.equal(ev(`enumerateFactUniverse([0,9], ['+']).length`), 100);   // 10×10 ordered
  assert.equal(ev(`enumerateFactUniverse([0,2], ['+']).length`), 9);     // 3×3
  assert.equal(ev(`enumerateFactUniverse([0,2], ['/']).length`), 6);     // b=0 dropped: 3×2
  assert.equal(ev(`enumerateFactUniverse([0,2], ['+','-']).length`), 18);// two ops
});

test('allocateCounts uses largest-remainder rounding and sums exactly to total', () => {
  // 25/50/25 of 10 -> exact 2.5/5/2.5; the leftover unit goes to the largest remainder.
  const a = evJ(`allocateCounts({ fluent: 0.25, almost: 0.5, 'needs-practice': 0.25 }, 10,
    { green: 5, yellow: 5, red: 5 }).counts`);
  assert.equal(a.green + a.yellow + a.red, 10);
  assert.equal(a.yellow, 5);
  assert.deepEqual(a, { green: 3, yellow: 5, red: 2 });
  // weights need not be fractions: 1/2/1 is the same as 25/50/25
  assert.deepEqual(evJ(`allocateCounts({ fluent: 1, almost: 2, 'needs-practice': 1 }, 10,
    { green: 5, yellow: 5, red: 5 }).counts`), { green: 3, yellow: 5, red: 2 });
});

test('allocateCounts drops empty-pool categories and reallocates their share', () => {
  // yellow has no facts -> its half is reallocated to green.
  assert.deepEqual(evJ(`allocateCounts({ fluent: 1, almost: 1 }, 10, { green: 3, yellow: 0 }).counts`),
    { green: 10 });
  // nothing allocatable -> dropped
  assert.equal(ev(`allocateCounts({ fluent: 1 }, 10, { green: 0 }).dropped`), true);
});

test('pickWithRepeats returns a distinct subset when the pool is big enough', () => {
  ev(`globalThis.r1 = makeRng(11)`);
  const p = evJ(`pickWithRepeats(['a','b','c','d','e'], 3, r1)`);
  assert.equal(p.length, 3);
  assert.equal(new Set(p).size, 3);                 // distinct
  assert.ok(p.every((x) => 'abcde'.includes(x)));
});

test('pickWithRepeats fills a shortfall with balanced randomized repeats', () => {
  ev(`globalThis.r2 = makeRng(11)`);
  const p = evJ(`pickWithRepeats(['a','b','c','d','e','f','g'], 10, r2)`);  // 7 facts -> 10 slots
  assert.equal(p.length, 10);
  assert.equal(new Set(p).size, 7);                 // every fact appears at least once
  const counts = {};
  p.forEach((x) => { counts[x] = (counts[x] || 0) + 1; });
  // balanced: each fact appears once or twice, exactly 3 of them twice (10 - 7 repeats)
  assert.ok(Object.values(counts).every((c) => c === 1 || c === 2));
  assert.equal(Object.values(counts).filter((c) => c === 2).length, 3);
});

test('selectAttemptsBySessions: all / recentN / sinceDate', () => {
  const a = [
    { session_id: 's1', start_time: '2026-06-01_100000', problem_text: '1 + 1' },
    { session_id: 's2', start_time: '2026-06-02_100000', problem_text: '2 + 2' },
    { session_id: 's3', start_time: '2026-06-03_100000', problem_text: '3 + 3' }
  ];
  const J = JSON.stringify(a);
  assert.equal(ev(`selectAttemptsBySessions(${J}, { mode: 'all' }).length`), 3);
  const recent = evJ(`selectAttemptsBySessions(${J}, { mode: 'recentN', n: 2 }).map((x) => x.session_id)`);
  assert.deepEqual([...recent].sort(), ['s2', 's3']);
  const since = evJ(`selectAttemptsBySessions(${J}, { mode: 'sinceDate', since: '2026-06-02' }).map((x) => x.session_id)`);
  assert.deepEqual([...since].sort(), ['s2', 's3']);   // s1 (June 1) excluded
});

test('generateFluencyProblemList: 100% missing draws the unseen facts and repeats to length', () => {
  // Universe [0,2] addition = 9 facts; observe 2 of them (green) so 7 are "missing" (nodata).
  const obs = [...attemptsFor('0 + 0', { base: 1 }), ...attemptsFor('1 + 1', { base: 10 })];
  ev(`globalThis.rngM = makeRng(123)`);
  const r = evJ(`generateFluencyProblemList({
    attempts: ${JSON.stringify(obs)}, numProblems: 10, distribution: { missing: 1 },
    numberRange: [0,2], operations: ['+'], rng: rngM })`);
  assert.equal(r.problems.length, 10);
  assert.equal(r.poolSizes.green, 2);
  assert.equal(r.poolSizes.nodata, 7);              // 9 universe - 2 observed
  assert.equal(r.counts.nodata, 10);
  assert.equal(r.repeats, 3);                       // 10 - 7, exactly as specified
  const uniq = new Set(r.problems);
  assert.equal(uniq.size, 7);                       // all 7 missing facts present
  assert.ok(!uniq.has('0 + 0') && !uniq.has('1 + 1'));   // the seen (green) facts are excluded
});

test('generateFluencyProblemList: honors a mixed distribution and classifies each pool', () => {
  // Universe [0,3] addition = 16 facts. Seed one fact into each status.
  const obs = [
    ...attemptsFor('0 + 0', { ms: 900, base: 1 }),                 // green (fast)
    ...attemptsFor('0 + 1', { ms: 900, base: 10 }),                // green (fast)
    ...attemptsFor('2 + 2', { ms: 3000, base: 20 }),               // yellow (mid)
    ...attemptsFor('3 + 3', { ms: 5000, base: 30 }),               // red (slow)
    ...attemptsFor('1 + 1', { ms: 900, correct: 2, base: 40 })     // gray/incorrect (40% accuracy)
  ];
  ev(`globalThis.rngX = makeRng(321)`);
  const r = evJ(`generateFluencyProblemList({
    attempts: ${JSON.stringify(obs)}, numProblems: 12,
    distribution: { fluent: 2, almost: 1, 'needs-practice': 1, incorrect: 1, missing: 1 },
    numberRange: [0,3], operations: ['+'], rng: rngX })`);
  // classification landed each seeded fact in the right pool
  assert.equal(r.statusByKey['0|+|0'], 'green');
  assert.equal(r.statusByKey['2|+|2'], 'yellow');
  assert.equal(r.statusByKey['3|+|3'], 'red');
  assert.equal(r.statusByKey['1|+|1'], 'gray');
  assert.equal(r.poolSizes.nodata, 11);             // 16 - 5 observed
  // 2/1/1/1/1 of 12 = 4/2/2/2/2 exactly
  assert.deepEqual(r.counts, { green: 4, yellow: 2, red: 2, gray: 2, nodata: 2 });
  assert.equal(r.problems.length, 12);
  // shortfall repeats: green 4-2, yellow 2-1, red 2-1, gray 2-1 = 5
  assert.equal(r.repeats, 5);
});

test('generateFluencyProblemList: warns and returns empty when a sole category has no facts', () => {
  // Universe [0,1] = 4 facts, all observed green; ask for 100% incorrect (empty pool).
  const obs = [
    ...attemptsFor('0 + 0', { base: 1 }), ...attemptsFor('0 + 1', { base: 10 }),
    ...attemptsFor('1 + 0', { base: 20 }), ...attemptsFor('1 + 1', { base: 30 })
  ];
  const r = evJ(`generateFluencyProblemList({
    attempts: ${JSON.stringify(obs)}, numProblems: 6, distribution: { incorrect: 1 },
    numberRange: [0,1], operations: ['+'], rng: makeRng(1) })`);
  assert.equal(r.problems.length, 0);
  assert.ok(r.warnings.length >= 1);
});

test('generateFluencyProblemList: excludeFlagged drops flagged attempts from classification', () => {
  // '0 + 0' has 3 fast-correct attempts (green) but they are all flagged; with excludeFlagged
  // the fact has no usable attempts, so it falls back to "missing" (nodata) instead of green.
  const flagged = [
    { problem_text: '0 + 0', is_correct: 1, response_time_ms: 900, start_time: '2026-06-01_10', attempt_id: 1, flags: [{ reason: 'distracted' }] },
    { problem_text: '0 + 0', is_correct: 1, response_time_ms: 900, start_time: '2026-06-02_10', attempt_id: 2, flags_json: '[{"reason":"stall"}]' },
    { problem_text: '0 + 0', is_correct: 1, response_time_ms: 900, start_time: '2026-06-03_10', attempt_id: 3, flags: [{ reason: 'na' }] },
  ];
  const J = JSON.stringify(flagged);
  // without the filter: green (the fast-correct attempts count)
  assert.equal(evJ(`generateFluencyProblemList({ attempts: ${J}, numProblems: 1, distribution: { fluent: 1 },
    numberRange: [0,0], operations: ['+'], rng: makeRng(1) })`).statusByKey['0|+|0'], 'green');
  // with the filter: the flagged attempts are dropped -> nodata (and no green pool to draw from)
  const r = evJ(`generateFluencyProblemList({ attempts: ${J}, numProblems: 1, distribution: { fluent: 1 },
    excludeFlagged: true, numberRange: [0,0], operations: ['+'], rng: makeRng(1) })`);
  assert.equal(r.statusByKey['0|+|0'], 'nodata');
  assert.equal(r.poolSizes.green, 0);
});

test('generateFluencyProblemList: an empty category reallocates its share to the rest', () => {
  // Universe [0,1] addition = 4 facts, all fluent (fast-correct). Ask 50% fluent / 50% missing;
  // "missing" has 0 facts, so its half reallocates to fluent -> all 8 slots come out fluent.
  const obs = [
    ...attemptsFor('0 + 0', { base: 1 }), ...attemptsFor('0 + 1', { base: 10 }),
    ...attemptsFor('1 + 0', { base: 20 }), ...attemptsFor('1 + 1', { base: 30 }),
  ];
  const r = evJ(`generateFluencyProblemList({ attempts: ${JSON.stringify(obs)}, numProblems: 8,
    distribution: { fluent: 50, missing: 50 }, numberRange: [0,1], operations: ['+'], rng: makeRng(1) })`);
  assert.equal(r.poolSizes.nodata, 0);          // "missing" is empty
  assert.equal(r.counts.green, 8);              // its 50% reallocated entirely to fluent
  assert.equal(r.counts.nodata, undefined);     // dropped, no slots
  assert.equal(r.problems.length, 8);
});

test('generateFluencyProblemList: zero length yields an empty list', () => {
  const r = evJ(`generateFluencyProblemList({ attempts: [], numProblems: 0,
    distribution: { missing: 1 }, numberRange: [0,2], operations: ['+'], rng: makeRng(1) })`);
  assert.deepEqual(r.problems, []);
});

test('fluencyPercent: empty attempts -> 0%', () => {
  assert.equal(ev(`fluencyPercent([], defaultFluencyThresholds, { numberRange: [0,9], operations: ['+'] })`), 0);
});

test('fluencyPercent: one fully fluent fact over the 100-fact addition universe -> 1%', () => {
  const obs = attemptsFor('3 + 4', { n: 5, ms: 900, correct: 5 });   // fast + correct => green
  assert.equal(
    evJ(`fluencyPercent(${JSON.stringify(obs)}, defaultFluencyThresholds, { numberRange: [0,9], operations: ['+'] })`),
    1);
});

test('fluencyPercent: all four facts fluent over a [0,1] universe -> 100%', () => {
  const obs = [
    ...attemptsFor('0 + 0', { base: 1 }), ...attemptsFor('0 + 1', { base: 10 }),
    ...attemptsFor('1 + 0', { base: 20 }), ...attemptsFor('1 + 1', { base: 30 }),
  ];
  assert.equal(
    evJ(`fluencyPercent(${JSON.stringify(obs)}, defaultFluencyThresholds, { numberRange: [0,1], operations: ['+'] })`),
    100);
});

test('fluencyPercent: excludeFlagged drops flagged attempts so the fact is not counted fluent', () => {
  // 5 fast-correct attempts that are all flagged -> with excludeFlagged they vanish -> 0% of [0,1].
  const flagged = attemptsFor('0 + 0', { n: 5, ms: 900, correct: 5 }).map((a) => ({ ...a, flags_json: JSON.stringify(['guess']) }));
  assert.equal(
    evJ(`fluencyPercent(${JSON.stringify(flagged)}, defaultFluencyThresholds, { numberRange: [0,1], operations: ['+'], excludeFlagged: true })`),
    0);
  // Without excludeFlagged the same attempts count -> 1 of 4 facts -> 25%.
  assert.equal(
    evJ(`fluencyPercent(${JSON.stringify(flagged)}, defaultFluencyThresholds, { numberRange: [0,1], operations: ['+'] })`),
    25);
});

test('maxRepeatsForList: 20->3, 10->2, small floors at 1', () => {
  assert.equal(ev(`maxRepeatsForList(20)`), 3);
  assert.equal(ev(`maxRepeatsForList(10)`), 2);
  assert.equal(ev(`maxRepeatsForList(5)`), 1);
  assert.equal(ev(`maxRepeatsForList(0)`), 1);
});

test('generation caps how many times one problem repeats (3 in 20, 2 in 10)', () => {
  // A 2-fact universe ([0,0] and [0,1] are both add-zero) with no attempts -> all missing.
  const mk = (n) => evJ(`generateFluencyProblemList({ attempts: [], numProblems: ${n},
    distribution: { missing: 100 }, numberRange: [0,1], operations: ['+'], rng: makeRng(7) }).problems`);
  for (const [n, cap] of [[20, 3], [10, 2]]) {
    const counts = {};
    for (const p of mk(n)) counts[p] = (counts[p] || 0) + 1;
    for (const k in counts) assert.ok(counts[k] <= cap, `${k} appeared ${counts[k]}x in a ${n}-list (cap ${cap})`);
  }
});

test('generation never repeats the same problem back-to-back', () => {
  const probs = evJ(`generateFluencyProblemList({ attempts: [], numProblems: 20,
    distribution: { missing: 100 }, numberRange: [0,2], operations: ['+'], rng: makeRng(3) }).problems`);
  for (let i = 1; i < probs.length; i++) assert.notEqual(probs[i], probs[i - 1], `adjacent dup at ${i}: ${probs[i]}`);
});

test('generation biases toward the easier categories first (only add-0 facts for a small list)', () => {
  // No attempts -> the whole 0-9 addition universe is "missing". Asking for a small list should
  // draw the easiest category (add-zero: one operand is 0) before any harder fact.
  const probs = evJ(`generateFluencyProblemList({ attempts: [], numProblems: 6,
    distribution: { missing: 100 }, numberRange: [0,9], operations: ['+'], rng: makeRng(11) }).problems`);
  assert.equal(probs.length, 6);
  for (const p of probs) {
    const [a, , b] = p.split(' ');
    assert.ok(Number(a) === 0 || Number(b) === 0, `expected an add-0 fact, got "${p}"`);
  }
});

test('arrangeNoAdjacentDup: even a heavily-repeated value is spread out', () => {
  // 3 of "A" and 1 each of B,C,D in a 6-list -> a valid no-adjacent order must exist.
  const out = evJ(`arrangeNoAdjacentDup(['A','A','A','B','C','D'], makeRng(2))`);
  assert.equal(out.length, 6);
  for (let i = 1; i < out.length; i++) assert.notEqual(out[i], out[i - 1]);
});

test('generateFluencyProblemList: backfills shortfall when repeat cap limits a tiny pool', () => {
  // Mimics an advanced learner: one gray fact, plenty of yellow/red/nodata. Default feast mix
  // asks for 40% gray (8 slots) but only 3 can come from the 1-fact pool at the 3× cap.
  const obs = [
    ...attemptsFor('0 + 0', { ms: 900, base: 1 }),
    ...attemptsFor('0 + 1', { ms: 900, base: 10 }),
    ...attemptsFor('2 + 2', { ms: 3000, base: 20 }),
    ...attemptsFor('3 + 3', { ms: 5000, base: 30 }),
    ...attemptsFor('7 + 5', { ms: 900, correct: 2, base: 40 }),   // sole gray fact
  ];
  ev(`globalThis.rngBf = makeRng(99)`);
  const r = evJ(`generateFluencyProblemList({
    attempts: ${JSON.stringify(obs)}, numProblems: 20,
    distribution: { fluent: 0, almost: 10, 'needs-practice': 10, incorrect: 40, missing: 40 },
    numberRange: [0,9], operations: ['+'], excludeFlagged: true, rng: rngBf })`);
  assert.equal(r.poolSizes.gray, 1);
  assert.equal(r.problems.length, 20);
  assert.ok(r.warnings.some((w) => w.includes('gray')));
  const counts = {};
  for (const p of r.problems) counts[p] = (counts[p] || 0) + 1;
  assert.ok(counts['7 + 5'] <= 3, 'gray fact still respects repeat cap');
});

function sumOfProblem(text) {
  const [a, , b] = text.split(' ');
  return Number(a) + Number(b);
}
function categoryOfProblem(text) {
  return ev(`additionCategoryOf(${Number(text.split(' ')[0])}, ${Number(text.split(' ')[2])})`);
}

test('pickFluencyFeastEasyStart: fluent single-digit then fluent two-digit from easy categories', () => {
  const obs = [
    ...attemptsFor('1 + 2', { ms: 900, base: 1 }),     // add-one, sum 3
    ...attemptsFor('1 + 9', { ms: 900, base: 10 }),    // add-one, sum 10
    ...attemptsFor('5 + 5', { ms: 900, base: 20 }),    // doubles, sum 10
  ];
  const r = evJ(`pickFluencyFeastEasyStart({ attempts: ${JSON.stringify(obs)},
    excludeFlagged: true, numberRange: [0,9], rng: makeRng(3) })`);
  assert.equal(r.problems.length, 2);
  assert.equal(r.mode, 'ideal');
  assert.ok(sumOfProblem(r.problems[0]) < 10, `first should be single-digit sum, got ${r.problems[0]}`);
  assert.ok(sumOfProblem(r.problems[1]) >= 10, `second should be two-digit sum, got ${r.problems[1]}`);
  for (const p of r.problems) {
    assert.ok(['add-zero', 'add-one', 'add-two', 'doubles'].includes(categoryOfProblem(p)), p);
  }
});

test('pickFluencyFeastEasyStart: falls back to a second fluent single-digit when no two-digit fluent', () => {
  const obs = [
    ...attemptsFor('0 + 3', { ms: 900, base: 1 }),
    ...attemptsFor('2 + 2', { ms: 900, base: 10 }),
  ];
  const r = evJ(`pickFluencyFeastEasyStart({ attempts: ${JSON.stringify(obs)},
    excludeFlagged: true, numberRange: [0,9], rng: makeRng(5) })`);
  assert.equal(r.mode, 'partial');
  assert.ok(sumOfProblem(r.problems[0]) < 10);
  assert.ok(sumOfProblem(r.problems[1]) < 10);
  assert.notEqual(r.problems[0], r.problems[1]);
});

test('pickFluencyFeastEasyStart: no fluent matches -> two random easy-category problems', () => {
  const obs = [
    ...attemptsFor('7 + 8', { ms: 900, base: 1 }),   // tough/hard — not in easy categories
  ];
  const r = evJ(`pickFluencyFeastEasyStart({ attempts: ${JSON.stringify(obs)},
    excludeFlagged: true, numberRange: [0,9], rng: makeRng(7) })`);
  assert.equal(r.mode, 'fallback');
  assert.equal(r.problems.length, 2);
  for (const p of r.problems) {
    assert.ok(['add-zero', 'add-one', 'add-two', 'doubles'].includes(categoryOfProblem(p)), p);
  }
});
