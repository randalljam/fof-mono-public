// Unit tests for the simulated dragon-playthrough learner: tier mapping,
// deterministic seeding, monotone speedup, and — most importantly — that the
// three tiers reach GREEN (under the REAL fluency rubric) in easy -> medium ->
// hard order when practiced uniformly.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createAppContext } from './load_app.mjs';
import {
  createSimLearner, tierForProblem, parseAdditionProblem,
  TIER_OF_CATEGORY, DEFAULT_TIER_START,
} from '../simulation/dragon_learner.mjs';
import { statusSnapshot, medianRtByTier, buildReportMarkdown, CATEGORY_SIZES } from '../simulation/playthrough_report.mjs';

const ctx = createAppContext(['math_utils.js', 'fluency_core.js']);
const evaluateFluencyStatus = (attempts, thresholds) => ctx.__evalJson(
  `evaluateFluencyStatus(${JSON.stringify(attempts)}${thresholds ? ', ' + JSON.stringify(thresholds) : ''})`);
const thresholds = ctx.__evalJson('defaultFluencyThresholds');

test('tier mapping follows the segmentation categories', () => {
  assert.equal(tierForProblem('0 + 7'), 'easy');     // add-zero
  assert.equal(tierForProblem('1 + 4'), 'easy');     // add-one
  assert.equal(tierForProblem('2 + 8'), 'medium');   // add-two
  assert.equal(tierForProblem('6 + 6'), 'medium');   // doubles
  assert.equal(tierForProblem('7 + 8'), 'hard');     // tough-21
  assert.equal(TIER_OF_CATEGORY['tough-21'], 'hard');
  assert.deepEqual(parseAdditionProblem('9 + 3'), { num1: 9, num2: 3, key: '+|3|9', category: 'tough-21' });
});

test('same seed reproduces the identical run; different seeds diverge', () => {
  const run = (seed) => {
    const l = createSimLearner({ seed });
    return Array.from({ length: 30 }, () => l.answer('7 + 8'));
  };
  assert.deepEqual(run('alpha'), run('alpha'));
  const a = run('alpha').map((x) => x.rtMs).join(',');
  const b = run('beta').map((x) => x.rtMs).join(',');
  assert.notEqual(a, b);
});

test('median RT shrinks by the configured rate per exposure, down to the floor', () => {
  const l = createSimLearner({ seed: 's', ratePerExposure: 0.10 });
  const start = l.peek('7 + 9').medianMs;
  assert.equal(start, DEFAULT_TIER_START.hard.medianMs);
  l.answer('7 + 9');
  assert.ok(Math.abs(l.peek('7 + 9').medianMs - start * 0.9) < 1e-9);
  for (let i = 0; i < 60; i++) l.answer('7 + 9');
  assert.equal(l.peek('7 + 9').medianMs, l.params.floorMs);
  // Exposure on one fact does not affect another fact in the same tier.
  assert.equal(l.peek('6 + 8').medianMs, DEFAULT_TIER_START.hard.medianMs);
});

test('correct answers really are correct; wrong answers are near misses', () => {
  const l = createSimLearner({ seed: 'answers' });
  let sawWrong = false;
  for (let i = 0; i < 200; i++) {
    const a = l.answer('6 + 9');
    if (a.isCorrect) assert.equal(a.userAnswer, 15);
    else {
      sawWrong = true;
      assert.notEqual(a.userAnswer, 15);
      assert.ok(Math.abs(a.userAnswer - 15) <= 2);
      assert.ok(a.userAnswer >= 0);
    }
  }
  assert.ok(sawWrong, 'hard tier at start accuracy 0.62 must produce misses in 200 tries');
});

test('tiers reach green under the REAL rubric in easy -> medium -> hard order', () => {
  const l = createSimLearner({ seed: 'ordering' });
  const facts = { easy: '1 + 6', medium: '2 + 7', hard: '8 + 9' };
  const history = { easy: [], medium: [], hard: [] };
  const greenAt = {};
  for (let round = 1; round <= 40; round++) {
    for (const [tier, text] of Object.entries(facts)) {
      const a = l.answer(text);
      history[tier].push({ isCorrect: a.isCorrect, responseTime: a.rtMs });
      const { status } = evaluateFluencyStatus(history[tier], thresholds);
      if (status === 'green' && greenAt[tier] === undefined) greenAt[tier] = round;
    }
  }
  assert.ok(greenAt.easy !== undefined && greenAt.medium !== undefined && greenAt.hard !== undefined,
    `all tiers must go green within 40 uniform exposures (got ${JSON.stringify(greenAt)})`);
  assert.ok(greenAt.easy <= greenAt.medium, `easy (${greenAt.easy}) before medium (${greenAt.medium})`);
  assert.ok(greenAt.medium < greenAt.hard, `medium (${greenAt.medium}) before hard (${greenAt.hard})`);
});

test('statusSnapshot buckets facts by category with the real evaluator', () => {
  const rows = [];
  for (let i = 0; i < 5; i++) {
    rows.push({ problem_text: '0 + 3', is_correct: 1, response_time_ms: 1000, flags_json: null });
    rows.push({ problem_text: '7 + 8', is_correct: 0, response_time_ms: 6000, flags_json: null });
  }
  const snap = statusSnapshot(rows, evaluateFluencyStatus, thresholds);
  assert.equal(snap.totalFacts, 55);
  assert.equal(snap.byCategory['add-zero'].green, 1);
  assert.equal(snap.byCategory['add-zero'].nodata, 9);
  assert.equal(snap.byCategory['tough-21'].gray, 1);
  assert.equal(snap.greenCount, 1);
  assert.equal(CATEGORY_SIZES['tough-21'], 21);
});

test('medianRtByTier and report rendering work over a small event stream', () => {
  const med = medianRtByTier([
    { tier: 'easy', rtMs: 1000 }, { tier: 'easy', rtMs: 2000 },
    { tier: 'hard', rtMs: 5000 },
  ]);
  assert.equal(med.easy, 1500);
  assert.equal(med.hard, 5000);
  assert.equal(med.medium, null);
  const events = [
    { type: 'run-start', meta: { user: 'T', folder: 'playtest', seed: 's', learnerParams: {}, tierStart: {} } },
    { type: 'seed', filename: 'f.sqlite', startPct: 40, greenCount: 22, byCategory: {} },
    {
      type: 'burst-end', burst: 1, pctBefore: 40, pctAfter: 45, correct: 18, total: 20,
      medianRtByTier: med, servedByCategory: { 'add-two': 10, 'tough-21': 10 }, byCategory: {},
    },
    { type: 'milestone', id: 'hatch', title: 'Hatch!', thresholdPct: 60, burst: 1, maxPct: 61 },
    { type: 'run-end', bursts: 1, finalPct: 45, maxPct: 61, rideUnlocked: false },
  ];
  const md = buildReportMarkdown(events, { mode: 'unit-test' });
  assert.ok(md.includes('## Burst-by-burst'));
  assert.ok(md.includes('40% → 45%'));
  assert.ok(md.includes('Hatch!'));
  assert.ok(md.includes('## Game changes discovered'));
});
