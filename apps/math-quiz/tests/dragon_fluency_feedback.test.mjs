import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SHOW_FLUENCY_FEEDBACK,
  fluencyFeedbackMessage,
  fluencyFeedbackForResult,
} from '../dragon/sim/fluency_feedback.js';

test('SHOW_FLUENCY_FEEDBACK defaults on', () => {
  assert.equal(SHOW_FLUENCY_FEEDBACK, true);
});

test('fluencyFeedbackMessage: improved', () => {
  assert.equal(
    fluencyFeedbackMessage(86, 87),
    'Great — you improved from 86% to 87%! Great job!',
  );
});

test('fluencyFeedbackMessage: holding steady', () => {
  assert.equal(fluencyFeedbackMessage(87, 87), 'Holding steady at 87%.');
});

test('fluencyFeedbackMessage: went down', () => {
  assert.equal(
    fluencyFeedbackMessage(87, 85),
    'Something happened — your fluency went down from 87% to 85%.',
  );
});

test('fluencyFeedbackForResult respects saved + toggle', () => {
  const improved = { saved: true, initialPct: 86, newPct: 87 };
  assert.equal(
    fluencyFeedbackForResult(improved, true),
    'Great — you improved from 86% to 87%! Great job!',
  );
  assert.equal(fluencyFeedbackForResult(improved, false), null);
  assert.equal(fluencyFeedbackForResult({ saved: false, initialPct: 86, newPct: 87 }, true), null);
  assert.equal(fluencyFeedbackForResult(null, true), null);
});
