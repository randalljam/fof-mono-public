import test from 'node:test';
import assert from 'node:assert/strict';
import { createAppContext } from './load_app.mjs';

const ctx = createAppContext(['math_utils.js']);
const ev = ctx.__eval;
const evJ = ctx.__evalJson;

test('normalizeOperationSymbols converts display symbols to canonical', () => {
  assert.equal(ev(`normalizeOperationSymbols('5 &times; 3')`), '5 * 3');
  assert.equal(ev(`normalizeOperationSymbols('5 × 3')`), '5 * 3');
  assert.equal(ev(`normalizeOperationSymbols('6 &divide; 2')`), '6 / 2');
  assert.equal(ev(`normalizeOperationSymbols('6 ÷ 2')`), '6 / 2');
  assert.equal(ev(`normalizeOperationSymbols('5 + 3')`), '5 + 3');
  assert.equal(ev(`normalizeOperationSymbols('  5   +  3 ')`), '5 + 3');
  assert.equal(ev(`normalizeOperationSymbols(null)`), '');
});

test('formatProblemTextForDisplay converts canonical to display symbols', () => {
  assert.equal(ev(`formatProblemTextForDisplay('5 * 3')`), '5 × 3');
  assert.equal(ev(`formatProblemTextForDisplay('6 / 2')`), '6 ÷ 2');
  assert.equal(ev(`formatProblemTextForDisplay('5 &times; 3')`), '5 × 3');
  assert.equal(ev(`formatProblemTextForDisplay('5 - 3')`), '5 - 3');
});

test('parseProblemText parses canonical and legacy display forms', () => {
  assert.deepEqual(evJ(`parseProblemText('5 + 3')`), { num1: 5, operation: '+', num2: 3 });
  assert.deepEqual(evJ(`parseProblemText('5 - 3')`), { num1: 5, operation: '-', num2: 3 });
  assert.deepEqual(evJ(`parseProblemText('5 &times; 3')`), { num1: 5, operation: '*', num2: 3 });
  assert.deepEqual(evJ(`parseProblemText('5 × 3')`), { num1: 5, operation: '*', num2: 3 });
  assert.deepEqual(evJ(`parseProblemText('8 &divide; 2')`), { num1: 8, operation: '/', num2: 2 });
  assert.deepEqual(evJ(`parseProblemText('-3 + 4')`), { num1: -3, operation: '+', num2: 4 });
  assert.deepEqual(evJ(`parseProblemText('not a problem at all')`), { num1: null, operation: null, num2: null });
});

test('escapeHtml escapes markup-significant characters', () => {
  assert.equal(ev(`escapeHtml('<script>"x" & \\'y\\'</script>')`),
    '&lt;script&gt;&quot;x&quot; &amp; &#39;y&#39;&lt;/script&gt;');
  assert.equal(ev(`escapeHtml(null)`), '');
  assert.equal(ev(`escapeHtml(42)`), '42');
});

test('computeMedian handles empty, odd, and even inputs', () => {
  assert.equal(ev(`computeMedian([])`), null);
  assert.equal(ev(`computeMedian([7])`), 7);
  assert.equal(ev(`computeMedian([1, 2])`), 1.5);
  assert.equal(ev(`computeMedian([3, 1, 2])`), 2);
});

test('parseSessionTimestamp parses session format and rejects junk', () => {
  const d = ev(`parseSessionTimestamp('2024-10-11_104410')`);
  assert.equal(d.getFullYear(), 2024);
  assert.equal(d.getMonth(), 9);
  assert.equal(d.getDate(), 11);
  assert.equal(d.getHours(), 10);
  assert.equal(d.getMinutes(), 44);
  assert.equal(d.getSeconds(), 10);
  assert.equal(ev(`parseSessionTimestamp('garbage')`), null);
  assert.equal(ev(`parseSessionTimestamp(null)`), null);
});

test('extractSessionStampFromFilename ignores mixed prefixes', () => {
  assert.equal(ev(`extractSessionStampFromFilename('math-flu_Izzy_2026-07-28_104340.sqlite')`), '2026-07-28_104340');
  assert.equal(ev(`extractSessionStampFromFilename('math-quest_K1_2026-06-19_143000.sqlite')`), '2026-06-19_143000');
  assert.equal(ev(`extractSessionStampFromFilename('mathquest_Izzy_2026-07-27_171219.sqlite')`), '2026-07-27_171219');
  assert.equal(ev(`extractSessionStampFromFilename('anchor_K1_2026-06-17_080000.sqlite')`), '2026-06-17_080000');
  assert.equal(ev(`extractSessionStampFromFilename('no-stamp.sqlite')`), null);
  assert.equal(ev(`extractSessionStampFromFilename(null)`), null);
});

test('sessionRecencyKey prefers filename stamp over start_time', () => {
  assert.equal(
    ev(`sessionRecencyKey('mathquest_Izzy_2026-07-27_171219.sqlite', '2020-01-01_000000')`),
    '2026-07-27_171219'
  );
  assert.equal(ev(`sessionRecencyKey('plain.json', '2026-06-01_100000')`), '2026-06-01_100000');
});
