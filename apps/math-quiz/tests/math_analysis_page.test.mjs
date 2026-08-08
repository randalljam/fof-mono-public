import test from 'node:test';
import assert from 'node:assert/strict';
import { createAppContext } from './load_app.mjs';

const ctx = createAppContext(['math_utils.js', 'fluency_core.js', 'math_analysis.js']);
const ev = ctx.__eval;
const evJ = ctx.__evalJson;

test('calculateAggregatedTime supports all aggregation methods', () => {
  assert.equal(ev(`calculateAggregatedTime([100, 200, 600], 'average')`), 300);
  assert.equal(ev(`calculateAggregatedTime([100, 200, 600], 'first')`), 100);
  assert.equal(ev(`calculateAggregatedTime([100, 200, 600], 'last')`), 600);
  assert.equal(ev(`calculateAggregatedTime([100, 200, 600], 'min')`), 100);
  assert.equal(ev(`calculateAggregatedTime([100, 200, 600], 'max')`), 600);
  assert.equal(ev(`calculateAggregatedTime([], 'average')`), null);
});

test('parseFlags tolerates strings, arrays, and junk', () => {
  assert.deepEqual(evJ(`parseFlags(null)`), []);
  assert.deepEqual(evJ(`parseFlags('[{"reason":"stall"}]')`), [{ reason: 'stall' }]);
  assert.deepEqual(evJ(`parseFlags([{ reason: 'other' }, null])`), [{ reason: 'other' }]);
  assert.deepEqual(evJ(`parseFlags('not json')`), []);
});

test('formatAttemptTimestamp shows the per-attempt presented_at (to the second), not the session start', () => {
  // Two attempts of the same fact in one session have the SAME start_time but DIFFERENT
  // presented_at — their labels must differ (the bug: all showed the session start time).
  const a = ev(`formatAttemptTimestamp({ presented_at: '2026-06-21T17:32:34.067Z', start_time: '2026-06-21_103126' })`);
  const b = ev(`formatAttemptTimestamp({ presented_at: '2026-06-21T17:34:48.035Z', start_time: '2026-06-21_103126' })`);
  const sessionOnly = ev(`formatAttemptTimestamp({ start_time: '2026-06-21_103126' })`);
  assert.notEqual(a, b);                       // per-attempt times differ
  assert.notEqual(a, sessionOnly);             // presented_at wins over the session start
  assert.match(a, /\d{1,2}:\d{2}:\d{2}/);      // includes seconds
  assert.match(sessionOnly, /\d{1,2}:\d{2}:\d{2}/);  // fallback to session start still has seconds
});

test('sortProblems orders by time, correctness, and flags without mutating input', () => {
  ev(`__problems = [
    { problem_text: 'a', response_time_ms: 500, is_correct: true, flags: [] },
    { problem_text: 'b', response_time_ms: 1500, is_correct: false, flags: [{ reason: 'stall' }] },
    { problem_text: 'c', response_time_ms: 1000, is_correct: true, flags: [] }
  ]`);
  assert.deepEqual(evJ(`sortProblems(__problems, 'time-desc').map(p => p.problem_text)`), ['b', 'c', 'a']);
  assert.deepEqual(evJ(`sortProblems(__problems, 'time-asc').map(p => p.problem_text)`), ['a', 'c', 'b']);
  assert.equal(ev(`sortProblems(__problems, 'incorrect')[0].problem_text`), 'b');
  assert.equal(ev(`sortProblems(__problems, 'flagged')[0].problem_text`), 'b');
  // original order untouched
  assert.deepEqual(evJ(`__problems.map(p => p.problem_text)`), ['a', 'b', 'c']);
});

test('processData populates subtraction cells (regression: "-" delimiter collision)', () => {
  const problems = JSON.stringify([
    { problem_text: '5 - 3', response_time_ms: 1200, is_correct: 1, flags: [] }
  ]);
  const grid = ev(`processData(${problems}, [0, 9], 0, 'average')`);
  const cell = grid[5][3];
  assert.equal(cell.attemptCount, 1);
  assert.equal(cell.displayedTime, 1200);
  assert.equal(cell.equation, '5 - 3');
});

test('processData aggregates legacy multiplication entities and duplicates', () => {
  const problems = JSON.stringify([
    { problem_text: '5 &times; 3', response_time_ms: 1000, is_correct: 1, flags: [] },
    { problem_text: '5 × 3', response_time_ms: 3000, is_correct: 0, flags: [{ reason: 'stall' }] }
  ]);
  const grid = ev(`processData(${problems}, [0, 9], 0, 'average')`);
  const cell = grid[5][3];
  assert.equal(cell.attemptCount, 2);
  assert.equal(cell.displayedTime, 2000);
  assert.equal(cell.incorrect, true);
  assert.equal(cell.hasFlag, true);
  assert.equal(cell.equation, '5 × 3');
});

test('filterProblemsByFlags respects the dropdown value', () => {
  ev(`__flagged = [
    { problem_text: 'a', flags: [] },
    { problem_text: 'b', flags: [{ reason: 'distracted' }] },
    { problem_text: 'c', flags: [{ reason: 'stall' }] }
  ]`);
  // No dropdown registered -> unchanged
  assert.equal(ev(`filterProblemsByFlags(__flagged).length`), 3);
  const flagFilter = ctx.__makeStubElement();
  flagFilter.value = 'exclude-flagged';
  ctx.__setElement('flag-filter', flagFilter);
  assert.deepEqual(evJ(`filterProblemsByFlags(__flagged).map(p => p.problem_text)`), ['a']);
  flagFilter.value = 'flagged-stall';
  assert.deepEqual(evJ(`filterProblemsByFlags(__flagged).map(p => p.problem_text)`), ['c']);
  flagFilter.value = 'all';
  assert.equal(ev(`filterProblemsByFlags(__flagged).length`), 3);
});

test('calculateAverage handles empty input', () => {
  assert.equal(ev(`calculateAverage([])`), null);
  assert.equal(ev(`calculateAverage([2, 4])`), 3);
});

test('calculateAverage excludes non-finite values (2026-06-16 hardening)', () => {
  // null / undefined / NaN are dropped from numerator AND denominator, not counted as 0.
  assert.equal(ev(`calculateAverage([100, 300, null])`), 200);   // not (100+300+0)/3 == 133
  assert.equal(ev(`calculateAverage([100, undefined, 300])`), 200);
  assert.equal(ev(`calculateAverage([NaN, 100, 300])`), 200);
  // all non-finite -> null, same contract as empty input
  assert.equal(ev(`calculateAverage([null, undefined, NaN])`), null);
});

test('computeFluencyByCellKey rates each cell with the shared rubric, recency-windowed and range-clipped', () => {
  const problems = JSON.stringify([
    { problem_text: '2 + 3', response_time_ms: 900, is_correct: 1, start_time: '2026-06-01_10', attempt_id: 1 },
    { problem_text: '2 + 3', response_time_ms: 1000, is_correct: 1, start_time: '2026-06-02_10', attempt_id: 2 },
    { problem_text: '8 + 9', response_time_ms: 5000, is_correct: 1, start_time: '2026-06-01_10', attempt_id: 3 },
    { problem_text: '7 + 9', response_time_ms: 1200, is_correct: 0, start_time: '2026-06-01_10', attempt_id: 4 },
    { problem_text: '2 + 13', response_time_ms: 900, is_correct: 1, start_time: '2026-06-01_10', attempt_id: 5 } // out of 0-9 range
  ]);
  const statuses = evJ(`(() => {
    const m = computeFluencyByCellKey(${problems}, [0, 9]);
    const o = {}; for (const k in m) o[k] = m[k].status; return o;
  })()`);
  assert.deepEqual(statuses, { '2|+|3': 'green', '8|+|9': 'red', '7|+|9': 'gray' });
});

test('processData attaches per-cell fluency status when a map is supplied', () => {
  const problems = JSON.stringify([
    { problem_text: '2 + 3', response_time_ms: 900, is_correct: 1, flags: [] }
  ]);
  const grid = ev(`processData(${problems}, [0, 9], 0, 'average', { '2|+|3': { status: 'blue', medianMs: 900, accuracy: 1 } })`);
  assert.equal(grid[2][3].fluencyStatus, 'blue');
  // cells with no fluency entry stay 'nodata'
  assert.equal(grid[4][4].fluencyStatus, 'nodata');
});

test('clampHeatmapScale keeps a valid increasing range (M19: max-slider floor)', () => {
  // normal case passes through untouched
  assert.deepEqual(evJ(`clampHeatmapScale(2000, 10000)`), { zmin: 2000, zmax: 10000 });
  // max at/below the floor is raised to 100 instead of collapsing to 0 (the
  // value that made Plotly autoscale and the scale appear to "jump")
  assert.deepEqual(evJ(`clampHeatmapScale(0, 0)`), { zmin: 0, zmax: 100 });
  // max below min would invert the range; bump it above min instead
  assert.deepEqual(evJ(`clampHeatmapScale(2000, 100)`), { zmin: 2000, zmax: 2100 });
  // non-numeric inputs fall back to a safe default range
  assert.deepEqual(evJ(`clampHeatmapScale(NaN, NaN)`), { zmin: 0, zmax: 100 });
});

// Register a control with a string value, the way the analysis page reads sliders/inputs.
function setControl(id, value) {
  const el = ctx.__makeStubElement();
  el.value = value;
  ctx.__setElement(id, el);
}

test('updateCurrentFluencyPercentage writes the app-wide full-universe %', () => {
  const el = ctx.__makeStubElement();
  el.textContent = '';
  ctx.__setElement('current-fluency-percentage', el);
  setControl('fluency-threshold', '2000');
  setControl('fluency-red-threshold', '4000');
  setControl('fluency-window', '5');
  setControl('fluency-min-accuracy', '80');
  // Stub queryDatabase to return five fast-correct attempts of one fact -> 1 of 100.
  ev(`queryDatabase = () => Array.from({ length: 5 }, (_, i) => ({
    problem_text: '2 + 3', is_correct: 1, response_time_ms: 900,
    start_time: '2026-06-01_100000', attempt_id: i + 1, session_id: 's1', flags: []
  }))`);
  ev(`updateCurrentFluencyPercentage({}, 'Kid1')`);
  assert.equal(el.textContent, 'Current fluency percentage: 1%');
  ev(`updateCurrentFluencyPercentage(null, 'Kid1')`);
  assert.equal(el.textContent, 'Current fluency percentage: --%');
});

test('getFluencyThresholdsFromControls reads the page rubric controls (and clamps accuracy 0-100)', () => {
  setControl('fluency-threshold', '1500');     // green bar
  setControl('fluency-red-threshold', '3000'); // red bar (no longer hard-wired to 2× green)
  setControl('fluency-window', '3');           // rolling window
  setControl('fluency-min-accuracy', '90');    // % -> fraction
  assert.deepEqual(evJ(`getFluencyThresholdsFromControls()`),
    { greenMs: 1500, redMs: 3000, windowSize: 3, minAccuracy: 0.9 });
  // accuracy is clamped to [0, 100] then divided to a fraction
  setControl('fluency-min-accuracy', '150');
  assert.equal(ev(`getFluencyThresholdsFromControls().minAccuracy`), 1);
  setControl('fluency-min-accuracy', '-10');
  assert.equal(ev(`getFluencyThresholdsFromControls().minAccuracy`), 0);
});

test('computeFluencyByCellKey honors the analysis-page rubric controls (threshold, min-accuracy, window)', () => {
  const status = (problems, key) => evJ(
    `(() => computeFluencyByCellKey(${JSON.stringify(problems)}, [0, 9])['${key}'].status)()`);

  // Green/red bars: a fact at a 1800 ms median is green under the 2000 default but flips to
  // red once both bars drop below it (1800 >= red 1500).
  const at1800 = [
    { problem_text: '4 + 4', response_time_ms: 1800, is_correct: 1, start_time: '2026-06-01_10', attempt_id: 1 },
    { problem_text: '4 + 4', response_time_ms: 1800, is_correct: 1, start_time: '2026-06-02_10', attempt_id: 2 }
  ];
  setControl('fluency-threshold', '2000'); setControl('fluency-red-threshold', '4000');
  setControl('fluency-window', '5'); setControl('fluency-min-accuracy', '80');
  assert.equal(status(at1800, '4|+|4'), 'green');
  setControl('fluency-threshold', '1000'); setControl('fluency-red-threshold', '1500');
  assert.equal(status(at1800, '4|+|4'), 'red');

  // Min-accuracy: 1 correct + 1 wrong = 50% accuracy reads gray under the 80% default, but
  // counts (green, median 1000 ms) once the bar drops to 40%.
  const half = [
    { problem_text: '5 + 5', response_time_ms: 1000, is_correct: 1, start_time: '2026-06-01_10', attempt_id: 3 },
    { problem_text: '5 + 5', response_time_ms: 1000, is_correct: 0, start_time: '2026-06-02_10', attempt_id: 4 }
  ];
  setControl('fluency-threshold', '2000'); setControl('fluency-red-threshold', '4000');
  setControl('fluency-min-accuracy', '80');
  assert.equal(status(half, '5|+|5'), 'gray');
  setControl('fluency-min-accuracy', '40');
  assert.equal(status(half, '5|+|5'), 'green');

  // Rolling window: two old slow-correct (3000 ms) + a recent fast-correct (900 ms). The full
  // window medians to 3000 (yellow); a window of 1 sees only the recent 900 ms (green).
  const recencyMix = [
    { problem_text: '6 + 3', response_time_ms: 3000, is_correct: 1, start_time: '2026-06-01_10', attempt_id: 5 },
    { problem_text: '6 + 3', response_time_ms: 3000, is_correct: 1, start_time: '2026-06-02_10', attempt_id: 6 },
    { problem_text: '6 + 3', response_time_ms: 900,  is_correct: 1, start_time: '2026-06-03_10', attempt_id: 7 }
  ];
  setControl('fluency-min-accuracy', '80');
  setControl('fluency-window', '5');
  assert.equal(status(recencyMix, '6|+|3'), 'yellow');
  setControl('fluency-window', '1');
  assert.equal(status(recencyMix, '6|+|3'), 'green');
});
