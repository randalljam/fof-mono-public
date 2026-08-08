// Unit tests for the shared fluency engine (fluency_core.js): the per-fact
// rubric (relocated from math_fluency.js) and the new roll-up helpers used by
// both the tracker overview and the analysis fluency view.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createAppContext } from './load_app.mjs';

const ctx = createAppContext(['math_utils.js', 'fluency_core.js']);
const ev = ctx.__eval;
const evJ = ctx.__evalJson;

test('evaluateFluencyStatus is available from the shared module', () => {
  const attempts = (n, ms, correct = true) =>
    JSON.stringify(Array.from({ length: n }, () => ({ isCorrect: correct, responseTime: ms })));
  assert.equal(ev(`evaluateFluencyStatus([]).status`), 'nodata');
  assert.equal(ev(`evaluateFluencyStatus(${attempts(5, 1000)}).status`), 'green');
  assert.equal(ev(`evaluateFluencyStatus(${attempts(5, 3000)}).status`), 'yellow');
  assert.equal(ev(`evaluateFluencyStatus(${attempts(5, 5000)}).status`), 'red');
  assert.equal(ev(`evaluateFluencyStatus(${attempts(5, 1000, false)}).status`), 'gray');
});

test('checkPermanentStatus requires N consecutive green sessions', () => {
  assert.equal(ev(`checkPermanentStatus(['green','green','green','green','green'], 5)`), true);
  assert.equal(ev(`checkPermanentStatus(['green','green','green','green'], 5)`), false);
  assert.equal(ev(`checkPermanentStatus(['green','yellow','green','green','green'], 5)`), false);
});

test('fluencyRollupStatus takes the worst (minimum) present status', () => {
  // all blue -> blue
  assert.equal(ev(`fluencyRollupStatus(['blue','blue','blue'])`), 'blue');
  // some blue + some green -> green (the user's rule)
  assert.equal(ev(`fluencyRollupStatus(['blue','green','blue'])`), 'green');
  // any yellow drags it to yellow
  assert.equal(ev(`fluencyRollupStatus(['blue','green','yellow'])`), 'yellow');
  // any red
  assert.equal(ev(`fluencyRollupStatus(['green','red','blue'])`), 'red');
  // gray dominates everything
  assert.equal(ev(`fluencyRollupStatus(['blue','green','gray'])`), 'gray');
  // nodata is ignored; empty -> nodata
  assert.equal(ev(`fluencyRollupStatus(['green','nodata','green'])`), 'green');
  assert.equal(ev(`fluencyRollupStatus([])`), 'nodata');
  assert.equal(ev(`fluencyRollupStatus(['nodata','nodata'])`), 'nodata');
});

test('fluencyStatusBreakdown counts each status', () => {
  assert.deepEqual(
    evJ(`fluencyStatusBreakdown(['green','green','red','blue','nodata'])`),
    { blue: 1, green: 2, yellow: 0, red: 1, gray: 0, nodata: 1 }
  );
});

test('additionCategoryOf matches the analysis page categorization', () => {
  assert.equal(ev(`additionCategoryOf(0, 7)`), 'add-zero');
  assert.equal(ev(`additionCategoryOf(1, 9)`), 'add-one');
  assert.equal(ev(`additionCategoryOf(2, 5)`), 'add-two');
  assert.equal(ev(`additionCategoryOf(7, 7)`), 'doubles');     // double wins over hardest-six
  assert.equal(ev(`additionCategoryOf(6, 6)`), 'doubles');
  assert.equal(ev(`additionCategoryOf(8, 9)`), 'hardest-six'); // both >= 6, unequal
  assert.equal(ev(`additionCategoryOf(3, 7)`), 'tough-21');    // lo in 3..5, unequal
});

test('easyHardBucket splits on a 6..9 operand', () => {
  assert.equal(ev(`easyHardBucket(5, 5)`), '0-5');
  assert.equal(ev(`easyHardBucket(2, 6)`), '6-9');
  assert.equal(ev(`easyHardBucket(9, 1)`), '6-9');
});
