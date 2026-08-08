import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { createAppContext } from '../tests/load_app.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';

const repoRoot = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const bridgeScript = path.join(repoRoot, 'tools/fluency_feast_bridge.mjs');

function runBridge(request) {
  const result = spawnSync('node', [bridgeScript], {
    input: JSON.stringify(request),
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  const line = result.stdout.trim().split('\n').pop();
  return JSON.parse(line);
}

test('fluency feast bridge generate matches direct fluency_core call', () => {
  const ctx = createAppContext(['math_utils.js', 'fluency_core.js']);
  const attempts = [{
    problem_text: '1 + 1',
    is_correct: 1,
    response_time_ms: 500,
    start_time: '2026-06-01_120000',
    session_id: 's1',
    attempt_id: 1,
  }];
  const thresholds = { greenMs: 2000, redMs: 4000, windowSize: 5, minAccuracy: 0.8 };
  const feast = { count: 5, session: { mode: 'all' }, mix: { missing: 100 } };
  const rngSequence = [0.11, 0.22, 0.33, 0.44, 0.55, 0.66, 0.77, 0.88, 0.99];
  const direct = ctx.__evalJson(`(() => {
    const seq = ${JSON.stringify(rngSequence)};
    let idx = 0;
    const rng = () => seq[idx++ % seq.length];
    return generateFluencyProblemList({
      attempts: ${JSON.stringify(attempts)},
      numProblems: ${feast.count},
      distribution: { missing: 100 },
      thresholds: ${JSON.stringify(thresholds)},
      sessionSelection: { mode: 'all' },
      numberRange: [0, 9],
      operations: ['+'],
      excludeFlagged: true,
      rng,
    });
  })()`);
  const bridged = runBridge({
    command: 'generate',
    attempts,
    feast,
    thresholds,
    numberRange: [0, 9],
    operations: ['+'],
    rngSequence,
  });
  assert.equal(bridged.ok, true);
  assert.deepEqual(bridged.problems, direct.problems);
});

test('fluency feast bridge percent matches direct fluency_core call', () => {
  const ctx = createAppContext(['math_utils.js', 'fluency_core.js']);
  const attempts = [{
    problem_text: '0 + 0',
    is_correct: 1,
    response_time_ms: 400,
    start_time: '2026-06-01_120000',
    session_id: 's1',
    attempt_id: 1,
  }];
  const thresholds = { greenMs: 2000, redMs: 4000, windowSize: 5, minAccuracy: 0.8 };
  const direct = ctx.__eval(`fluencyPercent(${JSON.stringify(attempts)}, ${JSON.stringify(thresholds)}, { numberRange: [0, 9], operations: ['+'], excludeFlagged: true })`);
  const bridged = runBridge({
    command: 'percent',
    attempts,
    thresholds,
    numberRange: [0, 9],
    operations: ['+'],
  });
  assert.equal(bridged.ok, true);
  assert.equal(bridged.percent, direct);
});
