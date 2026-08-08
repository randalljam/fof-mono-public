// Pure generator: category pools partition the 55 addition facts; largest-remainder
// allocation sums exactly to count; generateMix honors the mix and is deterministic under
// an injected rng.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  GENERATOR_CATEGORIES, categoryPools, allocateCounts, generateMix, itemsToText,
} from '../engine/list_generator.mjs';

test('category pools partition the 55 unique addition facts', () => {
  const pools = categoryPools();
  const sizes = Object.fromEntries(GENERATOR_CATEGORIES.map((c) => [c.id, pools.get(c.id).length]));
  assert.deepEqual(sizes, { 'add-zero': 10, 'add-one': 9, 'add-two': 8, doubles: 7, 'tough-21': 15, 'sneaky-six': 6 });
  assert.equal(Object.values(sizes).reduce((a, b) => a + b, 0), 55);
});

test('sneaky-six pool is exactly the hardest six facts', () => {
  const keys = categoryPools().get('sneaky-six').map((f) => `${f.lo}+${f.hi}`).sort();
  assert.deepEqual(keys, ['6+7', '6+8', '6+9', '7+8', '7+9', '8+9'].sort());
});

test('allocateCounts splits by weight and sums to count (largest remainder)', () => {
  const ids = ['add-zero', 'doubles', 'sneaky-six'];
  const c = allocateCounts(10, { 'add-zero': 50, doubles: 50 }, ids);
  assert.equal(c['add-zero'] + c.doubles + c['sneaky-six'], 10);
  assert.equal(c['sneaky-six'], 0);              // zero weight -> nothing
  assert.deepEqual([c['add-zero'], c.doubles], [5, 5]);
});

test('allocateCounts with no weights splits evenly and still sums to count', () => {
  const ids = ['a', 'b', 'c'];
  const c = allocateCounts(10, {}, ids);
  assert.equal(c.a + c.b + c.c, 10);
  assert.deepEqual([c.a, c.b, c.c].sort(), [3, 3, 4]);   // even-ish
});

test('generateMix produces exactly count problems from the requested categories', () => {
  let s = 1;
  const rng = () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; };
  const items = generateMix({ count: 12, weights: { 'add-zero': 1, doubles: 1 }, rng });
  assert.equal(items.length, 12);
  assert.ok(items.every((it) => it.operation === '+'));
  assert.ok(items.every((it) => ['add-zero', 'doubles'].includes(it.category)));
  // add-zero facts have a 0 addend; doubles have equal addends.
  assert.ok(items.every((it) => it.category !== 'add-zero' || it.num1 === 0 || it.num2 === 0));
  assert.ok(items.every((it) => it.category !== 'doubles' || it.num1 === it.num2));
});

test('generateMix is deterministic for a given rng', () => {
  const mk = () => { let s = 7; return () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; }; };
  const a = generateMix({ count: 8, weights: { 'tough-21': 1 }, rng: mk() });
  const b = generateMix({ count: 8, weights: { 'tough-21': 1 }, rng: mk() });
  assert.deepEqual(itemsToText(a), itemsToText(b));
});

test('itemsToText renders one problem per line', () => {
  assert.equal(itemsToText([{ num1: 8, operation: '+', num2: 2 }, { problem_text: '3 + 4' }]), '8 + 2\n3 + 4');
});
