// Tests for the learner fluency-state files: spec shape, per-profile character,
// and that the committed *_start.json files are in sync with the generator.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { generateStartState } from '../simulation/generate_start_state.mjs';
import { PROFILE_01, PROFILE_02, PROFILE_03 } from '../simulation/profiles.mjs';
import { createAppContext } from './load_app.mjs';

function makeFluencyFns() {
  const ctx = createAppContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js']);
  return {
    evaluateFluencyStatus: (attempts) =>
      ctx.__evalJson(`evaluateFluencyStatus(${JSON.stringify(attempts)})`),
  };
}

const VALID_STATUSES = new Set(['green', 'yellow', 'red', 'gray', 'blue', 'nodata']);

function statusCounts(state) {
  const counts = {};
  for (const op of ['addition', 'subtraction', 'multiplication'])
    for (const f of Object.values(state[op])) counts[f.status] = (counts[f.status] || 0) + 1;
  return counts;
}

test('state file conforms to the spec shape', () => {
  const fns = makeFluencyFns();
  const state = generateStartState(PROFILE_02, fns);

  assert.equal(state.version, '2.0');
  assert.equal(state.schema, 'math-quiz/fluency-state');
  assert.ok(state.user?.name, 'user.name present');
  assert.ok(state.thresholds?.greenMs, 'thresholds present');
  for (const op of ['addition', 'subtraction', 'multiplication'])
    assert.ok(state[op] && typeof state[op] === 'object', `${op} object present`);

  for (const op of ['addition', 'subtraction', 'multiplication']) {
    for (const [key, f] of Object.entries(state[op])) {
      assert.equal(f.key, key, 'entry key matches map key');
      assert.ok(VALID_STATUSES.has(f.status), `valid status: ${f.status}`);
      assert.ok(typeof f.num1 === 'number' && typeof f.num2 === 'number', 'numeric operands');
      assert.ok(typeof f.accuracy === 'number', 'accuracy numeric');
      assert.ok(Array.isArray(f.statusHistory), 'statusHistory array');
      assert.equal(f.isPermanent, false, 'no blue/permanent at baseline');
    }
  }
});

test('status is consistent with the real fluency thresholds (green => fast & accurate)', () => {
  const fns = makeFluencyFns();
  const state = generateStartState(PROFILE_03, fns);
  for (const f of Object.values(state.addition)) {
    if (f.status === 'green') {
      assert.ok(f.accuracy >= 0.8, `green needs accuracy >=0.8, got ${f.accuracy}`);
      assert.ok(f.medianMs !== null && f.medianMs < state.thresholds.greenMs,
        `green needs median < ${state.thresholds.greenMs}, got ${f.medianMs}`);
    }
  }
});

test('addition-beginner starts weak: few green, addition-only scope', () => {
  const fns = makeFluencyFns();
  const state = generateStartState(PROFILE_01, fns);
  const c = statusCounts(state);

  assert.equal(Object.keys(state.subtraction).length, 0, 'subtraction out of scope');
  assert.equal(Object.keys(state.multiplication).length, 0, 'multiplication out of scope');
  assert.equal(Object.keys(state.addition).length, 55, 'full addition matrix');

  const green = c.green || 0;
  const weak = (c.gray || 0) + (c.red || 0) + (c.yellow || 0);
  assert.ok(green >= 3, `beginner should have a few green trivials, got ${green}`);
  assert.ok(weak > green, `beginner should be mostly non-green, weak=${weak} green=${green}`);
});

test('mixed-with-holes starts mostly green with detectable multiplication holes', () => {
  const fns = makeFluencyFns();
  const state = generateStartState(PROFILE_02, fns);

  // Addition is fully fluent at baseline.
  const addGreen = Object.values(state.addition).filter(f => f.status === 'green').length;
  assert.ok(addGreen >= 50, `addition should be ~all green, got ${addGreen}/55`);

  // ×6–9 holes should surface as gray/red.
  const holes = Object.values(state.multiplication).filter(f => f.num1 >= 6 || f.num2 >= 6);
  const weakHoles = holes.filter(f => f.status === 'gray' || f.status === 'red').length;
  assert.ok(weakHoles >= holes.length * 0.7,
    `>=70% of mult holes should be weak, got ${weakHoles}/${holes.length}`);
});

test('proficient-adult starts essentially all green across all operations', () => {
  const fns = makeFluencyFns();
  const state = generateStartState(PROFILE_03, fns);
  const c = statusCounts(state);
  const total = 165;
  assert.ok((c.green || 0) >= total - 2, `adult should be ~all green, got ${c.green}/${total}`);
  assert.ok(!c.blue, 'no permanent/blue at baseline');
});

test('committed *_start.json files are in sync with the generator', () => {
  const fns = makeFluencyFns();
  const dir = new URL('../learner_profiles/states/', import.meta.url);
  for (const profile of [PROFILE_01, PROFILE_02, PROFILE_03]) {
    const fresh = generateStartState(profile, fns);
    const committed = JSON.parse(readFileSync(new URL(`${profile.profile_id}_start.json`, dir), 'utf8'));
    assert.deepEqual(committed, fresh,
      `${profile.profile_id}_start.json is stale — re-run: node simulation/generate_start_state.mjs`);
  }
});
