import test from 'node:test';
import assert from 'node:assert/strict';
import {
  TEACH_TRIGGERS,
  teachableProblem,
  showLightbulbOnRender,
  autoTeachOnWrong,
  showLightbulbInFlagPanel,
} from '../engine/teach_policy.mjs';

function withTriggers(patch, fn) {
  const saved = { ...TEACH_TRIGGERS };
  Object.assign(TEACH_TRIGGERS, patch);
  try { fn(); } finally { Object.assign(TEACH_TRIGGERS, saved); }
}

test('teachableProblem accepts only 0-10 integer addition facts with sum <= 20', () => {
  assert.equal(teachableProblem({ operation: '+', num1: 0, num2: 10 }), true);
  assert.equal(teachableProblem({ operation: '+', num1: 10, num2: 10 }), true);
  assert.equal(teachableProblem({ operation: '*', num1: 3, num2: 4 }), false);
  assert.equal(teachableProblem({ operation: '-', num1: 7, num2: 2 }), false);
  assert.equal(teachableProblem({ operation: '+', num1: -1, num2: 3 }), false);
  assert.equal(teachableProblem({ operation: '+', num1: 11, num2: 3 }), false);
  assert.equal(teachableProblem({ operation: '+', num1: 10, num2: 11 }), false);
  assert.equal(teachableProblem({ operation: '+', num1: 9.5, num2: 1 }), false);
  assert.equal(teachableProblem({ operation: '+', num1: 9, num2: 1.5 }), false);
  assert.equal(teachableProblem(null), false);
});

test('trigger helpers follow TEACH_TRIGGERS gates', () => {
  const item = { operation: '+', num1: 8, num2: 3 };
  assert.equal(showLightbulbOnRender(item), true);
  assert.equal(autoTeachOnWrong(item), true);
  assert.equal(showLightbulbInFlagPanel(item), true);

  withTriggers({ lightbulbAlways: false }, () => {
    assert.equal(showLightbulbOnRender(item), false);
    assert.equal(autoTeachOnWrong(item), true);
    assert.equal(showLightbulbInFlagPanel(item), true);
  });
  withTriggers({ autoShowOnWrong: false }, () => {
    assert.equal(showLightbulbOnRender(item), true);
    assert.equal(autoTeachOnWrong(item), false);
    assert.equal(showLightbulbInFlagPanel(item), true);
  });
  withTriggers({ lightbulbInFlagPanel: false }, () => {
    assert.equal(showLightbulbOnRender(item), true);
    assert.equal(autoTeachOnWrong(item), true);
    assert.equal(showLightbulbInFlagPanel(item), false);
  });
});

test('trigger helpers stay false for non-teachable problems even when enabled', () => {
  const item = { operation: '*', num1: 3, num2: 4 };
  assert.equal(showLightbulbOnRender(item), false);
  assert.equal(autoTeachOnWrong(item), false);
  assert.equal(showLightbulbInFlagPanel(item), false);
});
