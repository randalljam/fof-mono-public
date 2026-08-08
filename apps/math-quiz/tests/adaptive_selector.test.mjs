// Tests for SC1 (adaptive selector unit tests) and SC6 (hard preference)
import test from 'node:test';
import assert from 'node:assert/strict';
import { buildFactMatrix, makeRng, sampleLognormal, isHardFact, selectNextFact } from '../simulation/adaptive_selector.mjs';

test('isHardFact: hard iff max(num1,num2) >= 6', () => {
  assert.equal(isHardFact(0, 5), false);
  assert.equal(isHardFact(5, 5), false);
  assert.equal(isHardFact(6, 0), true);
  assert.equal(isHardFact(3, 7), true);
  assert.equal(isHardFact(9, 9), true);
});

test('buildFactMatrix: addition produces 55 canonical facts (0-9)', () => {
  const m = buildFactMatrix(['+']);
  assert.equal(m.size, 55);
  assert.ok(m.has('+|0|0'));
  assert.ok(m.has('+|0|9'));
  assert.ok(m.has('+|9|9'));
  assert.ok(!m.has('+|9|0')); // canonicalized to +|0|9
});

test('buildFactMatrix: subtraction produces 55 non-negative facts', () => {
  const m = buildFactMatrix(['-']);
  assert.equal(m.size, 55);
  assert.ok(m.has('-|0|0'));
  assert.ok(m.has('-|9|0'));
  assert.ok(!m.has('-|0|9')); // excluded (negative result)
});

test('buildFactMatrix: multiplication produces 55 canonical facts', () => {
  const m = buildFactMatrix(['*']);
  assert.equal(m.size, 55);
});

test('buildFactMatrix: three operations produce 165 facts', () => {
  const m = buildFactMatrix(['+', '-', '*']);
  assert.equal(m.size, 165);
});

test('buildFactMatrix: hard facts have max operand >= 6', () => {
  const m = buildFactMatrix(['+']);
  for (const [key, fact] of m) {
    const expectedHard = Math.max(fact.num1, fact.num2) >= 6;
    assert.equal(fact.isHard, expectedHard, `${key} hardness wrong`);
  }
});

test('makeRng: deterministic from same seed', () => {
  const r1 = makeRng('test');
  const r2 = makeRng('test');
  assert.equal(r1(), r2());
  assert.equal(r1(), r2());
  assert.equal(r1(), r2());
});

test('makeRng: different seeds produce different sequences', () => {
  const r1 = makeRng('seed-a');
  const r2 = makeRng('seed-b');
  const vals1 = [r1(), r1(), r1(), r1()];
  const vals2 = [r2(), r2(), r2(), r2()];
  assert.notDeepEqual(vals1, vals2);
});

test('sampleLognormal: values are within clamped range', () => {
  const rng = makeRng('ln-test');
  for (let i = 0; i < 100; i++) {
    const v = sampleLognormal(rng, 1500, 0.4);
    assert.ok(v >= 200 && v <= 30000, `out of range: ${v}`);
  }
});

test('SC1: selectNextFact respects tier priority (repair > consolidate > introduce > confirm)', () => {
  const m = buildFactMatrix(['+'], [0, 2]); // small matrix: +|0|0, +|0|1, +|0|2, +|1|1, +|1|2, +|2|2
  const rng = makeRng('tier-test');

  // Mark one fact as red (should be selected via repair tier)
  const perFactStatus = new Map();
  for (const key of m.keys()) perFactStatus.set(key, 'green');
  perFactStatus.set('+|0|0', 'red');

  const sessionState = { newFactsIntroduced: 0, maxNewFacts: 5, recentMissAt: new Map(), problemIndex: 0 };
  const chosen = selectNextFact(m, perFactStatus, sessionState, { hardWeight: 3, rng });
  assert.equal(chosen, '+|0|0', 'repair tier fact should be chosen');
});

test('SC1: selectNextFact introduces nodata facts before confirming green ones', () => {
  const m = buildFactMatrix(['+'], [0, 1]); // +|0|0, +|0|1, +|1|1
  const rng = makeRng('intro-test');

  const perFactStatus = new Map([
    ['+|0|0', 'green'],
    ['+|0|1', 'green'],
    ['+|1|1', 'nodata'],  // one unknown
  ]);
  const sessionState = { newFactsIntroduced: 0, maxNewFacts: 5, recentMissAt: new Map(), problemIndex: 0 };
  const chosen = selectNextFact(m, perFactStatus, sessionState, { hardWeight: 3, rng });
  assert.equal(chosen, '+|1|1', 'nodata fact in introduce tier should beat green in confirm');
});

test('SC1: selectNextFact applies spacing — recently missed fact not re-selected immediately', () => {
  const m = buildFactMatrix(['+'], [0, 1]);
  const rng = makeRng('spacing-test');
  const perFactStatus = new Map([
    ['+|0|0', 'red'],
    ['+|0|1', 'red'],
    ['+|1|1', 'red'],
  ]);
  // +|0|0 was missed at problem index 0; we're at index 1 => spacing blocks it
  const recentMissAt = new Map([['+|0|0', 0]]);
  const sessionState = { newFactsIntroduced: 0, maxNewFacts: 10, recentMissAt, problemIndex: 1 };
  const chosen = selectNextFact(m, perFactStatus, sessionState, { hardWeight: 3, rng });
  assert.notEqual(chosen, '+|0|0', 'recently missed fact should be spaced out');
});

test('SC6: hard facts receive >= hard_weight (3x) presentations vs easy for uniform fluent learner', () => {
  // Use a matrix where all facts start as nodata (no cap) and learner is uniformly fluent
  const m = buildFactMatrix(['+']); // 55 facts (34 hard, 21 easy)
  const rng = makeRng('sc6-hard-pref');
  const perFactStatus = new Map();
  for (const key of m.keys()) perFactStatus.set(key, 'nodata');

  const presentations = new Map();
  const totalProblems = 500;
  let newFacts = 0;

  for (let p = 0; p < totalProblems; p++) {
    const sessionState = { newFactsIntroduced: 0, maxNewFacts: Infinity, recentMissAt: new Map(), problemIndex: p };
    const chosen = selectNextFact(m, perFactStatus, sessionState, { hardWeight: 3, rng });
    presentations.set(chosen, (presentations.get(chosen) || 0) + 1);
    // Keep as nodata so introduce tier keeps working
  }

  let hardTotal = 0, easyTotal = 0, hardFacts = 0, easyFacts = 0;
  for (const [key, count] of presentations) {
    const fact = m.get(key);
    if (fact.isHard) { hardTotal += count; hardFacts++; }
    else { easyTotal += count; easyFacts++; }
  }

  const hardAvg = hardFacts > 0 ? hardTotal / hardFacts : 0;
  const easyAvg = easyFacts > 0 ? easyTotal / easyFacts : 1;
  const ratio = hardAvg / easyAvg;

  assert.ok(ratio >= 2.5, `hard/easy presentation ratio ${ratio.toFixed(2)} should be >= 2.5 (hard_weight=3)`);
});

test('SC6: hard-fact coverage exceeds easy-fact coverage in a partial sample', () => {
  const m = buildFactMatrix(['+', '-', '*']); // 165 facts
  const rng = makeRng('sc6-coverage');
  const perFactStatus = new Map();
  for (const key of m.keys()) perFactStatus.set(key, 'nodata');

  const seen = new Set();
  const totalProblems = 80;

  for (let p = 0; p < totalProblems; p++) {
    const sessionState = { newFactsIntroduced: 0, maxNewFacts: Infinity, recentMissAt: new Map(), problemIndex: p };
    const chosen = selectNextFact(m, perFactStatus, sessionState, { hardWeight: 3, rng });
    seen.add(chosen);
  }

  let hardSeen = 0, easySeen = 0, hardTotal = 0, easyTotal = 0;
  for (const [key, fact] of m) {
    if (fact.isHard) { hardTotal++; if (seen.has(key)) hardSeen++; }
    else { easyTotal++; if (seen.has(key)) easySeen++; }
  }

  const hardCov = hardSeen / hardTotal;
  const easyCov = easySeen / easyTotal;
  assert.ok(hardCov > easyCov, `hard coverage ${hardCov.toFixed(2)} should exceed easy coverage ${easyCov.toFixed(2)}`);

  const hardFraction = hardSeen / seen.size;
  assert.ok(hardFraction >= 0.75, `hard fraction of sampled ${hardFraction.toFixed(2)} should be >= 0.75`);
});
