// Tests for the single-digit addition segmentation + curated anchor plan.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  categorizeAddition, isSneakySix, buildAdditionFacts, buildAdditionCategories,
  buildAnchorAdditionPlan, ADDITION_CATEGORIES, EASY_CATEGORIES,
} from '../engine/addition_segmentation.mjs';

test('the five categories partition all 55 facts with no overlap', () => {
  const facts = buildAdditionFacts();
  assert.equal(facts.length, 55);
  // each fact lands in exactly one category
  for (const f of facts) assert.ok(ADDITION_CATEGORIES.includes(f.category));
  const cats = buildAdditionCategories();
  const counts = Object.fromEntries([...cats].map(([c, list]) => [c, list.length]));
  assert.deepEqual(counts, { 'add-zero': 10, 'add-one': 9, 'add-two': 8, doubles: 7, 'tough-21': 21 });
  // sum == 55, and the union has no duplicate keys
  const allKeys = [...cats.values()].flat().map((f) => f.key);
  assert.equal(allKeys.length, 55);
  assert.equal(new Set(allKeys).size, 55);
});

test('categorization is by smaller addend (with doubles/tough split at >=3)', () => {
  assert.equal(categorizeAddition(0, 9), 'add-zero');
  assert.equal(categorizeAddition(1, 8), 'add-one');
  assert.equal(categorizeAddition(2, 7), 'add-two');
  assert.equal(categorizeAddition(4, 4), 'doubles');
  assert.equal(categorizeAddition(2, 2), 'add-two');   // 2+2 absorbed into add-two, not doubles
  assert.equal(categorizeAddition(6, 9), 'tough-21');
});

test('Sneaky Six = exactly the six tough facts with both addends >= 6', () => {
  const sneaky = buildAdditionFacts().filter((f) => f.sneaky);
  assert.deepEqual(sneaky.map((f) => f.key).sort(), ['+|6|7', '+|6|8', '+|6|9', '+|7|8', '+|7|9', '+|8|9']);
  for (const f of sneaky) assert.equal(f.category, 'tough-21'); // subset of tough-21
  assert.equal(isSneakySix(9, 8), true);
  assert.equal(isSneakySix(5, 9), false);
  assert.equal(isSneakySix(7, 7), false); // double, not sneaky
});

test('anchor plan: every tough fact once, Sneaky Six both ways, all doubles, >= half of each easy set', () => {
  const plan = buildAnchorAdditionPlan({ seed: 'test-seed' });
  const cats = buildAdditionCategories();

  // Tough 21: every fact present at least once.
  const toughKeys = new Set(cats.get('tough-21').map((f) => f.key));
  const planToughKeys = new Set(plan.filter((it) => it.category === 'tough-21').map((it) => it.key));
  assert.equal(planToughKeys.size, toughKeys.size, 'all 21 tough facts covered');

  // Sneaky Six: both orientations.
  for (const f of cats.get('tough-21').filter((f) => f.sneaky)) {
    const orientations = new Set(plan.filter((it) => it.key === f.key).map((it) => it.orientation));
    assert.ok(orientations.has('ascending') && orientations.has('complement'), `${f.key} in both orientations`);
  }

  // Doubles: all 7.
  assert.equal(new Set(plan.filter((it) => it.category === 'doubles').map((it) => it.key)).size, 7);

  // Easy: at least half of each of add-zero/one/two.
  for (const cat of EASY_CATEGORIES) {
    const total = cats.get(cat).length;
    const covered = new Set(plan.filter((it) => it.category === cat).map((it) => it.key)).size;
    assert.ok(covered >= Math.ceil(total / 2), `${cat}: covered ${covered} >= half of ${total}`);
  }
});

test('easy-first order puts easy categories before hard (and hard-first the reverse)', () => {
  const isHardCat = (c) => c === 'tough-21' || c === 'doubles';
  const meanHardPos = (plan) => {
    const idx = plan.map((it, i) => [it, i]).filter(([it]) => isHardCat(it.category)).map(([, i]) => i);
    return idx.reduce((s, i) => s + i, 0) / idx.length;
  };
  const meanEasyPos = (plan) => {
    const idx = plan.map((it, i) => [it, i]).filter(([it]) => !isHardCat(it.category)).map(([, i]) => i);
    return idx.reduce((s, i) => s + i, 0) / idx.length;
  };
  const ef = buildAnchorAdditionPlan({ seed: 'order-test', order: 'easy-first' });
  const hf = buildAnchorAdditionPlan({ seed: 'order-test', order: 'hard-first' });
  assert.ok(meanEasyPos(ef) < meanHardPos(ef), 'easy-first: easy facts earlier');
  assert.ok(meanHardPos(hf) < meanEasyPos(hf), 'hard-first: hard facts earlier');
});

test('anchor plan jumps around (no marching) and emphasizes hard facts early', () => {
  const plan = buildAnchorAdditionPlan({ seed: 'test-seed' });

  // No "8+1, 8+2, 8+3" marching: never 3 in a row with same first operand AND increasing second.
  for (let i = 0; i + 2 < plan.length; i++) {
    const a = plan[i], b = plan[i + 1], c = plan[i + 2];
    const marching = a.num1 === b.num1 && b.num1 === c.num1 && a.num2 < b.num2 && b.num2 < c.num2;
    assert.ok(!marching, `marching run at ${i}: ${a.num1}+${a.num2}, ${b.num1}+${b.num2}, ${c.num1}+${c.num2}`);
  }

  // Hard emphasized early: mean position of hard (tough/doubles) < mean of easy.
  const isHardCat = (c) => c === 'tough-21' || c === 'doubles';
  const meanPos = (pred) => {
    const idx = plan.map((it, i) => [it, i]).filter(([it]) => pred(it.category)).map(([, i]) => i);
    return idx.reduce((s, i) => s + i, 0) / idx.length;
  };
  assert.ok(meanPos((c) => isHardCat(c)) < meanPos((c) => !isHardCat(c)), 'hard facts come earlier on average');
});
