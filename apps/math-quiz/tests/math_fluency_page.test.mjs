import test from 'node:test';
import assert from 'node:assert/strict';
import { createAppContext } from './load_app.mjs';

const ctx = createAppContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js']);
const ev = ctx.__eval;
const evJ = ctx.__evalJson;

test('getCanonicalProblemKey normalizes commutative operations only', () => {
  assert.equal(ev(`getCanonicalProblemKey(4, 3, '+')`), '+|3|4');
  assert.equal(ev(`getCanonicalProblemKey(3, 4, '+')`), '+|3|4');
  assert.equal(ev(`getCanonicalProblemKey(4, 3, '*')`), '*|3|4');
  assert.equal(ev(`getCanonicalProblemKey(4, 3, '-')`), '-|4|3');
});

test('evaluateFluencyStatus classifies green/yellow/red/gray/nodata', () => {
  const attempts = (n, ms, correct = true) =>
    JSON.stringify(Array.from({ length: n }, () => ({ isCorrect: correct, responseTime: ms })));
  assert.equal(ev(`evaluateFluencyStatus([]).status`), 'nodata');
  assert.equal(ev(`evaluateFluencyStatus(${attempts(5, 1000)}).status`), 'green');
  assert.equal(ev(`evaluateFluencyStatus(${attempts(5, 3000)}).status`), 'yellow');
  assert.equal(ev(`evaluateFluencyStatus(${attempts(5, 5000)}).status`), 'red');
  assert.equal(ev(`evaluateFluencyStatus(${attempts(5, 1000, false)}).status`), 'gray');
});

test('evaluateFluencyStatus only considers the rolling window', () => {
  // 10 slow attempts followed by 5 fast ones; window of 5 sees only the fast ones
  const mixed = JSON.stringify([
    ...Array.from({ length: 10 }, () => ({ isCorrect: true, responseTime: 9000 })),
    ...Array.from({ length: 5 }, () => ({ isCorrect: true, responseTime: 900 }))
  ]);
  const result = ev(`evaluateFluencyStatus(${mixed}, { windowSize: 5, minAccuracy: 0.8, greenMs: 2000, redMs: 4000 })`);
  assert.equal(result.status, 'green');
  assert.equal(result.attemptsConsidered, 5);
});

test('checkPermanentStatus requires N consecutive green sessions', () => {
  assert.equal(ev(`checkPermanentStatus(['green','green','green','green','green'], 5)`), true);
  assert.equal(ev(`checkPermanentStatus(['green','green','green','green'], 5)`), false);
  assert.equal(ev(`checkPermanentStatus(['green','yellow','green','green','green'], 5)`), false);
  assert.equal(ev(`checkPermanentStatus(['yellow','green','green','green'], 3)`), true);
});

test('universeFluencyPercent uses the shared full-universe fluencyPercent metric', () => {
  // One fully fluent addition fact over the 100-fact 0-9 universe -> 1%
  ev(`rawFluencyAttempts = Array.from({ length: 5 }, (_, i) => ({
    problem_text: '2 + 3', is_correct: 1, response_time_ms: 900,
    start_time: '2026-06-01_100000', attempt_id: i + 1, session_id: 's1'
  }))`);
  const settings = `{ numberRange: null, windowSize: 5, minAccuracy: 0.8, greenMs: 2000, redMs: 4000 }`;
  assert.equal(ev(`universeFluencyPercent('addition', ${settings})`), 1);
  // Same attempts scored against a [0,3] sub-universe (16 facts) -> 6%
  const ranged = `{ numberRange: { start: 0, end: 3 }, windowSize: 5, minAccuracy: 0.8, greenMs: 2000, redMs: 4000 }`;
  assert.equal(ev(`universeFluencyPercent('addition', ${ranged})`), 6);
  // No multiplication attempts -> 0%
  assert.equal(ev(`universeFluencyPercent('multiplication', ${settings})`), 0);
  ev(`rawFluencyAttempts = []`);
});

test('convertFluencyProblemToQuizFormat produces quiz-compatible problems', () => {
  const p = ev(`convertFluencyProblemToQuizFormat({ num1: 3, num2: 4, operation: '*' })`);
  assert.equal(p.normalizedExpression, '3 * 4');
  assert.equal(p.displayProblem, '3 × 4');
  assert.equal(p.speakableProblem, '3 times 4');
  assert.equal(p.correctAnswer, 12);
  assert.equal(p.problemId, '*|3|4');
});

test('filterProblemsByRange keeps problems inside the inclusive range', () => {
  const problems = JSON.stringify({
    'a': { num1: 2, num2: 3 },
    'b': { num1: 0, num2: 12 },
    'c': { num1: 9, num2: 9 }
  });
  const keys = evJ(`Object.keys(filterProblemsByRange(${problems}, '0-9'))`);
  assert.deepEqual(keys, ['a', 'c']);
  assert.equal(ev(`Object.keys(filterProblemsByRange(${problems}, 'all')).length`), 3);
});

test('generateProblemListFromFluency samples by status percentages', () => {
  ev(`fluencyDatasets = { addition: { combined: {
    '+|1|1': { num1: 1, num2: 1, operation: '+', status: 'red' },
    '+|1|2': { num1: 1, num2: 2, operation: '+', status: 'red' },
    '+|1|3': { num1: 1, num2: 3, operation: '+', status: 'red' },
    '+|2|2': { num1: 2, num2: 2, operation: '+', status: 'green' },
    '+|2|3': { num1: 2, num2: 3, operation: '+', status: 'green' }
  } } }`);
  const list = ev(`generateProblemListFromFluency('addition', '0-9', 3,
    { blue: 0, green: 0, yellow: 0, red: 100, gray: 0 })`);
  assert.equal(list.length, 3);
  for (const problem of list) {
    assert.match(problem.normalizedExpression, /^1 \+ [123]$/);
  }
});

test('saveManualOverride and getManualOverride round-trip per user', () => {
  assert.equal(ev(`saveManualOverride('Kid1', '+|3|4', 'green', 'knows it', 'yellow')`), true);
  const override = ev(`getManualOverride('Kid1', '+|3|4')`);
  assert.equal(override.status, 'green');
  assert.equal(override.calculatedStatus, 'yellow');
  assert.equal(ev(`getManualOverride('randy', '+|3|4')`), null);
  ev(`saveManualOverride('Kid1', '+|3|4', null)`);
  assert.equal(ev(`getManualOverride('Kid1', '+|3|4')`), null);
});
