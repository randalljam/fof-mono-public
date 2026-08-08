// Visual practice engine tests - cold probe, teach/filler-spaced retrieval,
// cumulative successes, filler deck spacing, requeue,
// completion/closing filler, and SQLite metadata shape.
import test from 'node:test';
import assert from 'node:assert/strict';
import { buildFactMatrix, makeRng } from '../simulation/adaptive_selector.mjs';
import { parseTargets, parseFillerFacts } from '../engine/targeted_practice.mjs';
import { createVisualRun } from '../engine/visual_practice.mjs';

const FM = buildFactMatrix(['+', '-', '*'], [0, 10]);
const FAST = { isCorrect: true, responseTime: 900 };
const SLOW = { isCorrect: true, responseTime: 3500 };
const WRONG = { isCorrect: false, responseTime: 800 };
const PASS = { passed: true, responseTime: 800 };

function targets(...items) {
  return parseTargets(items).targets;
}

function fillers(...items) {
  return parseFillerFacts(items).facts;
}

function form(item) {
  return `${item.num1}${item.operation}${item.num2}`;
}

// --- cold probe + delayed confirmation ---

test('cold-probe fast-correct then delayed confirmation clears after fillers', () => {
  const run = createVisualRun({
    targets: targets('8+3'),
    factMatrix: FM,
    fillerFacts: fillers('1+1', '2+2', '3+3'),
    retrievalsToClear: 2,
    fillerGapMin: 2,
    fillerGapMax: 2,
    rng: makeRng('visual-cold'),
  });

  const cold = run.nextProblem();
  assert.equal(cold.role, 'cold-probe');
  assert.equal(cold.targetKey, '+|3|8');
  assert.equal(form(cold), '8+3');

  assert.deepEqual(run.record(cold, FAST), {
    needsTeach: false,
    cleared: null,
    sessionComplete: false,
  });
  assert.equal(run.progress().current.successes, 1);

  const f1 = run.nextProblem();
  const f2 = run.nextProblem();
  assert.equal(f1.role, 'filler');
  assert.equal(f2.role, 'filler');
  run.record(f1, FAST);
  run.record(f2, FAST);
  assert.equal(run.progress().current.successes, 1, 'filler responses do not credit the target');

  const delayed = run.nextProblem();
  assert.equal(delayed.role, 'delayed-retrieval');
  const result = run.record(delayed, FAST);
  assert.equal(result.cleared, '+|3|8');
  assert.equal(result.sessionComplete, true);
  assert.equal(run.isComplete(), true);
});

test('wrong cold probe returns needsTeach and records the cold-probe result', () => {
  const run = createVisualRun({ targets: targets('8+3'), factMatrix: FM, fillerFacts: [], rng: makeRng('wrong') });
  const cold = run.nextProblem();
  const result = run.record(cold, WRONG);
  assert.equal(result.needsTeach, true);
  assert.equal(result.cleared, null);
  assert.equal(run.progress().perTarget[0].coldProbe, 'wrong');
  assert.equal(run.progress().perTarget[0].successes, 0);
});

test('pass is treated as not correct, needs teach, and records pass', () => {
  const run = createVisualRun({ targets: targets('8+3'), factMatrix: FM, fillerFacts: [], rng: makeRng('pass') });
  const cold = run.nextProblem();
  const result = run.record(cold, PASS);
  assert.equal(result.needsTeach, true);
  assert.equal(result.cleared, null);
  assert.equal(run.progress().perTarget[0].coldProbe, 'pass');
  assert.equal(run.progress().perTarget[0].successes, 0);
});

test('slow-correct gives no credit and does not auto-teach', () => {
  const run = createVisualRun({ targets: targets('8+3'), factMatrix: FM, fillerFacts: [], fastMs: 2000, rng: makeRng('slow') });
  const cold = run.nextProblem();
  const result = run.record(cold, SLOW);
  assert.equal(result.needsTeach, false);
  assert.equal(result.cleared, null);
  assert.equal(run.progress().perTarget[0].coldProbe, 'slow-correct');
  assert.equal(run.progress().perTarget[0].successes, 0);
});

// --- teach + retrieval rules ---

test('teachShown schedules fillers before the target returns as delayed retrieval', () => {
  const run = createVisualRun({
    targets: targets('8+3'),
    factMatrix: FM,
    fillerFacts: fillers('1+1', '2+2'),
    fillerGapMin: 2,
    fillerGapMax: 2,
    rng: makeRng('teach'),
  });
  const cold = run.nextProblem();
  run.record(cold, WRONG);
  run.teachShown(cold.targetKey);

  const f1 = run.nextProblem();
  const f2 = run.nextProblem();
  assert.equal(f1.role, 'filler');
  assert.equal(f2.role, 'filler');
  const delayed = run.nextProblem();
  assert.equal(delayed.role, 'delayed-retrieval');
  assert.equal(delayed.targetKey, '+|3|8');
  assert.equal(run.progress().perTarget[0].teachCount, 1);
});

test('teachShown with no filler still emits delayed retrieval, not immediate retrieval', () => {
  const run = createVisualRun({
    targets: targets('8+3'),
    factMatrix: FM,
    fillerFacts: [],
    retrievalsToClear: 1,
    rng: makeRng('immediate-no-clear'),
  });
  const cold = run.nextProblem();
  run.record(cold, WRONG);
  run.teachShown(cold.targetKey);

  const delayed = run.nextProblem();
  assert.equal(delayed.role, 'delayed-retrieval');
  const delayedResult = run.record(delayed, FAST);
  assert.equal(delayedResult.cleared, '+|3|8');
  assert.equal(delayedResult.sessionComplete, true);
});

test('successes are cumulative across a later wrong answer', () => {
  const run = createVisualRun({
    targets: targets('3+6'),
    factMatrix: FM,
    fillerFacts: [],
    retrievalsToClear: 2,
    rng: makeRng('cumulative'),
  });

  const cold = run.nextProblem();
  run.record(cold, FAST);
  assert.equal(run.progress().current.successes, 1);

  const delayedWrong = run.nextProblem();
  const wrongResult = run.record(delayedWrong, WRONG);
  assert.equal(wrongResult.needsTeach, true);
  assert.equal(run.progress().current.successes, 1);

  run.teachShown(delayedWrong.targetKey);
  const retry = run.nextProblem();
  assert.equal(retry.role, 'delayed-retrieval');
  assert.equal(run.record(retry, FAST).cleared, '+|3|6');
  assert.equal(run.progress().perTarget[0].successes, 2);
});

test('target orientation alternates across presentations', () => {
  const run = createVisualRun({
    targets: targets('3+6'),
    factMatrix: FM,
    fillerFacts: [],
    retrievalsToClear: 10,
    rng: makeRng('orient'),
  });
  const forms = [];
  for (let i = 0; i < 4; i++) {
    const p = run.nextProblem();
    forms.push(form(p));
    run.record(p, SLOW);
  }
  assert.deepEqual(forms, ['3+6', '6+3', '3+6', '6+3']);
});

// --- filler spacing, session end, empty pool, requeue ---

test('filler gap respects the configured inclusive min/max', () => {
  const run = createVisualRun({
    targets: targets('3+6'),
    factMatrix: FM,
    fillerFacts: fillers('1+1', '2+2', '3+3', '4+4', '5+5'),
    retrievalsToClear: 99,
    fillerGapMin: 2,
    fillerGapMax: 4,
    rng: makeRng('gap'),
  });

  let gap = 0;
  const gaps = [];
  for (let i = 0; i < 40; i++) {
    const p = run.nextProblem();
    if (p.role === 'filler') {
      gap++;
    } else {
      if (i > 0) gaps.push(gap);
      gap = 0;
      run.record(p, SLOW);
    }
  }
  assert.ok(gaps.length > 5);
  assert.ok(gaps.every((g) => g >= 2 && g <= 4), `gaps ${gaps} within [2,4]`);
});

test('session ends right on the last clear — no trailing questions', () => {
  const run = createVisualRun({
    targets: targets('4+4'),
    factMatrix: FM,
    fillerFacts: fillers('1+1', '2+2'),
    retrievalsToClear: 1,
    fillerGapMin: 0,
    fillerGapMax: 0,
    rng: makeRng('closing'),
  });
  const cold = run.nextProblem();
  const result = run.record(cold, FAST);
  assert.equal(result.cleared, '+|4|4');
  assert.equal(run.isComplete(), true);
  assert.equal(run.completionReason(), 'all-cleared');
  assert.equal(run.nextProblem(), null);
});

test('empty filler pool uses gap 0 and still ends on the clear', () => {
  const run = createVisualRun({
    targets: targets('4+4'),
    factMatrix: FM,
    fillerFacts: [],
    retrievalsToClear: 1,
    fillerGapMin: 2,
    fillerGapMax: 4,
    rng: makeRng('empty'),
  });
  const cold = run.nextProblem();
  assert.equal(run.record(cold, FAST).cleared, '+|4|4');
  assert.equal(run.nextProblem(), null);
});

test('requeue re-asks an inserted problem after the requested gap', () => {
  const run = createVisualRun({
    targets: targets('3+6'),
    factMatrix: FM,
    fillerFacts: fillers('1+1', '2+2', '3+3'),
    retrievalsToClear: 99,
    fillerGapMin: 4,
    fillerGapMax: 4,
    rng: makeRng('requeue'),
  });
  run.nextProblem();
  const reItem = { key: '+|5|5', num1: 5, num2: 5, operation: '+', role: 'filler', targetKey: null };
  run.requeue(reItem, 2);

  const first = run.nextProblem();
  const second = run.nextProblem();
  assert.equal(first.role, 'filler');
  assert.equal(second.key, '+|5|5');
  assert.equal(second.role, 'filler');
});

test('filler pool preserves display orientation and excludes targets', () => {
  const run = createVisualRun({
    targets: targets('6+0'),
    factMatrix: FM,
    fillerFacts: fillers('0+6', '6+0', '2+1', '1+2'),
    rng: makeRng('filler-pool'),
  });
  assert.deepEqual(run.fillerPool.map(form), ['2+1', '1+2']);
});

// --- progress / metadata ---

test('progress and metadata expose visual-practice session shape', () => {
  const run = createVisualRun({
    targets: targets('3+6', '8+7'),
    factMatrix: FM,
    fillerFacts: fillers('1+1'),
    fastMs: 4000,
    retrievalsToClear: 3,
    rng: makeRng('shape'),
  });
  const cold = run.nextProblem();
  const response = run.record(cold, { isCorrect: true, responseTime: 4500 });
  assert.equal(response.needsTeach, false);
  run.teachShown(cold.targetKey);

  const progress = run.progress();
  assert.equal(progress.totalTargets, 2);
  assert.equal(progress.clearedTargets, 0);
  assert.equal(progress.fraction, 0);
  assert.equal(progress.retrievalsToClear, 3);
  assert.equal(progress.problemsPresented, 1);
  assert.equal(progress.current.key, '+|3|6');
  assert.equal(progress.current.index, 0);
  assert.equal(progress.current.successes, 0);
  assert.equal(progress.perTarget[0].coldProbe, 'slow-correct');
  assert.equal(progress.perTarget[0].teachCount, 1);

  const md = run.metadata();
  assert.equal(md.mode, 'visual-practice');
  assert.deepEqual(md.targets, ['+|3|6', '+|7|8']);
  assert.equal(md.targetCount, 2);
  assert.equal(md.fastMs, 4000);
  assert.equal(md.retrievalsToClear, 3);
  assert.deepEqual(md.cleared, []);
  assert.equal(md.complete, false);
  assert.equal(md.completionReason, null);
  assert.equal(md.currentTargetKey, '+|3|6');
  assert.equal(md.perTarget[0].coldProbe, 'slow-correct');
  assert.equal(md.perTarget[0].teachCount, 1);
  assert.equal(md.perTarget[0].retrievalSuccesses, 0);
  assert.equal(md.perTarget[0].attempts, 1);
  assert.equal(md.perTarget[0].requiredSuccesses, 3);
  assert.equal(md.perTarget[0].cleared, false);
});

test('createVisualRun validates target count', () => {
  assert.throws(() => createVisualRun({ targets: [], factMatrix: FM }), /at least one target/);
  const sixTargets = [
    { num1: 1, num2: 1, operation: '+' },
    { num1: 1, num2: 2, operation: '+' },
    { num1: 1, num2: 3, operation: '+' },
    { num1: 1, num2: 4, operation: '+' },
    { num1: 1, num2: 5, operation: '+' },
    { num1: 1, num2: 6, operation: '+' },
  ];
  assert.throws(
    () => createVisualRun({ targets: sixTargets, factMatrix: FM }),
    /at most five targets/,
  );
});
