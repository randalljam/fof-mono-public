// Pure problem-list helpers: replicate/shuffle expansion, internal-item normalization,
// and base-item extraction. DOM-free; rng injected for deterministic shuffles.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  shuffleWith, expandProblemListItems, normalizeInternalItem, internalListBaseItems,
} from '../engine/problem_list.mjs';

const ITEMS = [
  { num1: 8, operation: '+', num2: 2 },
  { num1: 3, operation: '+', num2: 4 },
];

test('expand with replicates=1 keeps order and tags keys/indices', () => {
  const { reps, sequence } = expandProblemListItems(ITEMS, { replicates: 1 });
  assert.equal(reps, 1);
  assert.equal(sequence.length, 2);
  assert.deepEqual(sequence.map((s) => s.key), ['+|8|2|0', '+|3|4|1']);
  assert.deepEqual(sequence.map((s) => s.listReplicate), [1, 1]);
  assert.deepEqual(sequence.map((s) => s.listIndex), [0, 1]);
});

test('expand replicates the base set and clamps to maxReplicates', () => {
  assert.equal(expandProblemListItems(ITEMS, { replicates: 3 }).sequence.length, 6);
  assert.equal(expandProblemListItems(ITEMS, { replicates: 99, maxReplicates: 4 }).reps, 4);
  assert.equal(expandProblemListItems(ITEMS, { replicates: 0 }).reps, 1);   // floor at 1
});

test('randomize uses the injected rng and preserves the multiset of keys', () => {
  const rng = () => 0;   // deterministic: every swap targets index 0
  const { sequence } = expandProblemListItems(ITEMS, { replicates: 2, randomize: true, rng });
  assert.equal(sequence.length, 4);
  assert.deepEqual(
    sequence.map((s) => s.key).sort(),
    ['+|3|4|1', '+|3|4|3', '+|8|2|0', '+|8|2|2'].sort(),
  );
});

test('shuffleWith does not mutate the input array', () => {
  const src = [1, 2, 3];
  const out = shuffleWith(src, () => 0);
  assert.deepEqual(src, [1, 2, 3]);
  assert.equal(out.length, 3);
});

test('normalizeInternalItem prefers stored nums', () => {
  assert.deepEqual(
    normalizeInternalItem({ num1: 8, operation: '+', num2: 2, category: 'Add Two' }),
    { num1: 8, num2: 2, operation: '+', category: 'Add Two' },
  );
});

test('normalizeInternalItem falls back to parsing problem_text', () => {
  const parseLine = (t) => { const [a, , b] = t.split(' '); return { num1: Number(a), operation: '*', num2: Number(b) }; };
  const out = normalizeInternalItem({ num1: null, operation: null, num2: null, problem_text: '6 x 7' }, parseLine);
  assert.deepEqual(out, { num1: 6, num2: 7, operation: '*', category: 'problem-list' });
});

test('normalizeInternalItem returns null when unparseable', () => {
  assert.equal(normalizeInternalItem({ problem_text: 'not a problem' }, () => null), null);
  assert.equal(normalizeInternalItem(null), null);
});

test('internalListBaseItems drops bad items and throws when none usable', () => {
  const list = { list_name: 'A', items: [{ num1: 8, operation: '+', num2: 2 }, { problem_text: 'junk' }] };
  assert.deepEqual(internalListBaseItems(list, () => null), [{ num1: 8, num2: 2, operation: '+', category: 'problem-list' }]);
  assert.throws(() => internalListBaseItems({ list_name: 'Empty', items: [] }, () => null), /no usable problems/);
});
