import test from 'node:test';
import assert from 'node:assert/strict';
import { createAppContext } from './load_app.mjs';

const ctx = createAppContext(['math_utils.js', 'math_quiz.js']);
const ev = ctx.__eval;
const evJ = ctx.__evalJson;

function setSettings(overrides) {
  ev(`settings = Object.assign({
    num_problems: 5, number_range: [0, 5], numbers_include: [], numbers_exclude: [],
    num_numbers: 2, operations: ['+'], problem_list: []
  }, ${JSON.stringify(overrides)})`);
}

test('generateProblem records canonical problemText and display entities separately', () => {
  setSettings({ number_range: [2, 2], operations: ['*'] });
  const p = ev('generateProblem()');
  assert.equal(p.problemText, '2 * 2');
  assert.equal(p.displayProblem, '2 &times; 2');
  assert.equal(p.speakableProblem, '2 times 2');
  assert.equal(p.correctAnswer, 4);
});

test('generateProblem division and subtraction answers', () => {
  setSettings({ number_range: [3, 3], operations: ['/'] });
  assert.equal(ev('generateProblem()').correctAnswer, 1);
  setSettings({ number_range: [4, 4], operations: ['-'] });
  const p = ev('generateProblem()');
  assert.equal(p.problemText, '4 - 4');
  assert.equal(p.correctAnswer, 0);
});

test('generateProblem throws on an empty number pool', () => {
  setSettings({ number_range: [0, 1], numbers_exclude: [0, 1] });
  assert.throws(() => ev('generateProblem()'), /No available numbers/);
  // numbers_include alone cannot fill a two-number problem
  setSettings({ number_range: [0, 1], numbers_exclude: [0, 1], numbers_include: [5] });
  assert.throws(() => ev('generateProblem()'), /No available numbers/);
});

test('buildProblemFromExpression parses text problems with mixed symbols', () => {
  const add = ev(`buildProblemFromExpression('3 + 4')`);
  assert.equal(add.correctAnswer, 7);
  assert.equal(add.normalizedExpression, '3 + 4');
  const mult = ev(`buildProblemFromExpression('6 x 7')`);
  assert.equal(mult.normalizedExpression, '6 * 7');
  assert.equal(mult.correctAnswer, 42);
  assert.equal(mult.displayProblem, '6 &times; 7');
  const div = ev(`buildProblemFromExpression('8 ÷ 2')`);
  assert.equal(div.correctAnswer, 4);
  assert.equal(ev(`buildProblemFromExpression('5 / 0')`).correctAnswer, Infinity);
  assert.throws(() => ev(`buildProblemFromExpression('hello world')`), /Could not parse/);
});

test('parseProblemListContent reads markdown bullets, plain lines, and JSON', () => {
  assert.equal(ev(`parseProblemListContent('- 3 + 4\\n- 5 + 6\\n', 'list.md')`).length, 2);
  assert.equal(ev(`parseProblemListContent('3 + 4\\n5 + 6\\n7 + 8\\n', 'list.txt')`).length, 3);
  assert.equal(ev(`parseProblemListContent('["3 + 4", "5 + 6"]', 'list.json')`).length, 2);
  assert.equal(ev(`parseProblemListContent('{"problems": [{"problem": "3 + 4"}]}', 'list.json')`).length, 1);
  assert.throws(() => ev(`parseProblemListContent('', 'list.md')`), /No valid problems/);
  assert.throws(() => ev(`parseProblemListContent('not json', 'list.json')`), /Invalid JSON/);
});

test('buildProblemFromSessionEntry keeps grading consistent with session data', () => {
  const p = ev(`buildProblemFromSessionEntry({ problem_text: '5 &times; 3', correct_answer: 15 }, 0)`);
  assert.equal(p.correctAnswer, 15);
  assert.equal(p.normalizedExpression, '5 * 3');
  // null correct_answer (serialized Infinity) falls back to the expression-derived value
  const divZero = ev(`buildProblemFromSessionEntry({ problem_text: '5 &divide; 0', correct_answer: null }, 0)`);
  assert.equal(divZero.correctAnswer, Infinity);
  // string answers are coerced to numbers
  const str = ev(`buildProblemFromSessionEntry({ problem_text: '5 + 3', correct_answer: '8' }, 0)`);
  assert.equal(str.correctAnswer, 8);
  assert.equal(ev(`buildProblemFromSessionEntry({ note: 'no text here' }, 0)`), null);
});

test('convertSpelledOutNumberToNumeral converts speech transcripts', () => {
  assert.equal(ev(`convertSpelledOutNumberToNumeral('seven')`), '7');
  assert.equal(ev(`convertSpelledOutNumberToNumeral('twenty one')`), '21');
  assert.equal(ev(`convertSpelledOutNumberToNumeral('one hundred and five')`), '105');
  assert.equal(ev(`convertSpelledOutNumberToNumeral('42')`), '42');
});

test('formatNumber trims trailing zeros', () => {
  assert.equal(ev('formatNumber(2.5)'), '2.5');
  assert.equal(ev('formatNumber(3)'), '3');
  assert.equal(ev('formatNumber(0.125)'), '0.125');
  assert.equal(ev('formatNumber(2.0)'), '2');
});

test('calculateTotalTestTime formats minutes:seconds', () => {
  assert.equal(ev(`calculateTotalTestTime('2024-10-11_100000', '2024-10-11_100130')`), '1:30');
  assert.equal(ev(`calculateTotalTestTime('2024-10-11_100000', '2024-10-11_100007')`), '0:07');
});

test('parseNumberList and parseOperations sanitize custom settings input', () => {
  assert.deepEqual(evJ(`parseNumberList('1, 2, x, 9')`), [1, 2, 9]);
  assert.deepEqual(evJ(`parseOperations('+ * bogus')`), ['+', '*']);
  assert.deepEqual(evJ(`parseOperations('')`), ['+']);
});
