// Ten-frame renderer tests - side-by-side teach states (setup, setup-answer,
// result), larger-first orientation, exact dot counts by frame/color, and
// edge-case coverage.
import test from 'node:test';
import assert from 'node:assert/strict';
import { tenFrameTeachStates } from '../engine/ten_frame.mjs';

const CYAN = '#00acc1';
const GOLD = '#daa520';

function circleTags(svg) {
  return svg.match(/<circle\b[^>]*>/g) || [];
}

function countDots(svg, frame, fill) {
  return circleTags(svg).filter((tag) => (
    tag.includes(`data-frame="${frame}"`) && tag.includes(`fill="${fill}"`)
  )).length;
}

function counts(svg) {
  return {
    firstCyan: countDots(svg, 'first', CYAN),
    firstGold: countDots(svg, 'first', GOLD),
    secondCyan: countDots(svg, 'second', CYAN),
    secondGold: countDots(svg, 'second', GOLD),
  };
}

function assertStates(num1, num2, expected) {
  const result = tenFrameTeachStates(num1, num2);
  assert.equal(result.larger, expected.larger);
  assert.equal(result.smaller, expected.smaller);
  assert.equal(result.sum, expected.sum);
  assert.match(result.setupSvg, /data-state="setup"/);
  assert.match(result.setupAnswerSvg, /data-state="setup-answer"/);
  assert.match(result.resultSvg, /data-state="result"/);
  assert.deepEqual(counts(result.setupSvg), expected.setup);
  // The answer variant is the same frames/dots with "= sum" added to the equation row.
  assert.deepEqual(counts(result.setupAnswerSvg), expected.setup);
  assert.deepEqual(counts(result.resultSvg), expected.result);
  assert.doesNotMatch(result.setupSvg, /data-sum=/);
  assert.match(result.setupAnswerSvg, new RegExp(`data-sum="${expected.sum}"[^>]*>= ${expected.sum}</text>`));
  assert.match(result.resultSvg, new RegExp(`data-sum="${expected.sum}"[^>]*>= ${expected.sum}</text>`));
  return result;
}

test('8+6 crosses ten with moved goldenrod dots in the first frame', () => {
  const r = assertStates(8, 6, {
    larger: 8,
    smaller: 6,
    sum: 14,
    setup: { firstCyan: 8, firstGold: 0, secondCyan: 0, secondGold: 6 },
    result: { firstCyan: 8, firstGold: 2, secondCyan: 0, secondGold: 4 },
  });
  // The result equation row reads "10 + 4 = 14" (ten made in the first frame).
  assert.match(r.resultSvg, />10<\/text>/);
  assert.match(r.resultSvg, />4<\/text>/);
});

test('3+8 renders larger-first as 8+3', () => {
  assertStates(3, 8, {
    larger: 8,
    smaller: 3,
    sum: 11,
    setup: { firstCyan: 8, firstGold: 0, secondCyan: 0, secondGold: 3 },
    result: { firstCyan: 8, firstGold: 2, secondCyan: 0, secondGold: 1 },
  });
});

test('sum <= 10 combines both colors into one result frame', () => {
  assertStates(3, 4, {
    larger: 4,
    smaller: 3,
    sum: 7,
    setup: { firstCyan: 4, firstGold: 0, secondCyan: 0, secondGold: 3 },
    result: { firstCyan: 4, firstGold: 3, secondCyan: 0, secondGold: 0 },
  });
});

test('9+9 keeps two distinct colors for equal addends', () => {
  assertStates(9, 9, {
    larger: 9,
    smaller: 9,
    sum: 18,
    setup: { firstCyan: 9, firstGold: 0, secondCyan: 0, secondGold: 9 },
    result: { firstCyan: 9, firstGold: 1, secondCyan: 0, secondGold: 8 },
  });
});

test('0+5 promotes the nonzero addend to the first cyan frame', () => {
  assertStates(0, 5, {
    larger: 5,
    smaller: 0,
    sum: 5,
    setup: { firstCyan: 5, firstGold: 0, secondCyan: 0, secondGold: 0 },
    result: { firstCyan: 5, firstGold: 0, secondCyan: 0, secondGold: 0 },
  });
});

test('invalid addends throw range errors', () => {
  assert.throws(() => tenFrameTeachStates(-1, 3), RangeError);
  assert.throws(() => tenFrameTeachStates(11, 3), RangeError);
  assert.throws(() => tenFrameTeachStates(2.5, 3), RangeError);
});
