import test from 'node:test';
import assert from 'node:assert/strict';
import { createBurst } from '../dragon/sim/burst_session.js';

const items = [
  { key: '+|1|2', operation: '+', num1: 1, num2: 2, problemText: '1 + 2' },
  { key: '+|3|4', operation: '+', num1: 3, num2: 4, problemText: '3 + 4' },
];

test('createBurst advances through all problems', () => {
  const b = createBurst(items);
  assert.equal(b.current().problemText, '1 + 2');
  b.record(3, true, 450.7, Date.now(), '2026-07-02_120000');
  assert.equal(b.current().problemText, '3 + 4');
  b.record(7, true, 500.2, Date.now(), '2026-07-02_120000');
  assert.ok(b.done());
});

test('createBurst rounds response time ms', () => {
  const b = createBurst([items[0]]);
  b.record(3, true, 450.7, 1000, 't');
  const { entries } = b.progress();
  assert.equal(entries[0].response_time_ms, 451);
});

test('createBurst records incorrect and quit-partial entries', () => {
  const b = createBurst(items);
  b.record(2, false, 800, 1000, 't');
  const { entries, index } = b.progress();
  assert.equal(index, 1);
  assert.equal(entries[0].is_correct, false);
  assert.equal(entries[0].user_answer, 2);
});

test('createBurst records skip with empty answer and custom flags', () => {
  const b = createBurst([items[0]]);
  const flags = [{ reason: 'skip-noreason', label: 'Skip - no reason', timestamp: '2026-07-02T12:00:00.000Z', notes: '' }];
  b.record(null, false, 600, 1000, 't', flags);
  const { entries } = b.progress();
  assert.equal(entries[0].user_answer_string, '');
  assert.equal(entries[0].user_answer, null);
  assert.deepEqual(entries[0].flags, flags);
});

test('createBurst lastEntry and setFlags mutate prior attempt', () => {
  const b = createBurst(items);
  b.record(3, true, 400, 1000, 't');
  const prev = b.lastEntry();
  assert.equal(prev.fact_key, '+|1|2');
  const flags = [{ reason: 'distracted', label: 'Distracted', timestamp: '2026-07-02T12:00:00.000Z', notes: 'oops' }];
  b.setFlags(prev, flags);
  assert.deepEqual(b.lastEntry().flags, flags);
});

test('createBurst insertItem grows total and re-asks later', () => {
  const b = createBurst(items);
  b.record(3, true, 400, 1000, 't');
  assert.equal(b.current().problemText, '3 + 4');
  b.insertItem(items[0], 1);
  const { total } = b.progress();
  assert.equal(total, 3);
  b.record(7, true, 500, 1000, 't');
  assert.equal(b.current().problemText, '1 + 2');
});

test('createBurst skipCurrent inserts current without recording', () => {
  const b = createBurst(items);
  assert.equal(b.current().problemText, '1 + 2');
  b.skipCurrent(1);
  assert.equal(b.current().problemText, '3 + 4');
  const { entries, total } = b.progress();
  assert.equal(entries.length, 0);
  assert.equal(total, 3);
});
