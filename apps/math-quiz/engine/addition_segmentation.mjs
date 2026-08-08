// Single-digit addition segmentation + curated anchor sampling plan.
// Source of truth: single_digit_addition_segmentation.md.
//
// The five MAIN categories partition the 55 unique facts (commutative, counted
// once) with NO overlap, keyed by the smaller addend:
//   add-zero (min 0, 10) · add-one (min 1, 9) · add-two (min 2, 8) ·
//   doubles (min>=3 & equal, 7) · tough-21 (min>=3 & unequal, 21)   => 55
// "Sneaky Six" is a NAMED SUBSET of tough-21 (both addends >=6), not a 6th bucket.
//
// Orientation terms (per request): a fact has two ORIENTATIONS —
//   ascending  = lower addend first  (e.g. 3 + 4)
//   complement = reversed/higher first (e.g. 4 + 3)
// Doubles are symmetric (the two orientations coincide).
import { makeRng } from '../simulation/adaptive_selector.mjs';

export const ADDITION_CATEGORIES = ['add-zero', 'add-one', 'add-two', 'doubles', 'tough-21'];
export const EASY_CATEGORIES = ['add-zero', 'add-one', 'add-two'];

export function categorizeAddition(a, b) {
  const lo = Math.min(a, b), hi = Math.max(a, b);
  if (lo === 0) return 'add-zero';
  if (lo === 1) return 'add-one';
  if (lo === 2) return 'add-two';
  if (lo === hi) return 'doubles';
  return 'tough-21';
}

// Sneaky Six: both addends >= 6 and not a double — 6+7, 6+8, 6+9, 7+8, 7+9, 8+9.
export function isSneakySix(a, b) {
  const lo = Math.min(a, b), hi = Math.max(a, b);
  return lo >= 6 && hi > lo;
}

// All 55 unique addition facts as {lo, hi, key, category, sneaky}.
export function buildAdditionFacts() {
  const facts = [];
  for (let lo = 0; lo <= 9; lo++) {
    for (let hi = lo; hi <= 9; hi++) {
      facts.push({ lo, hi, key: `+|${lo}|${hi}`, category: categorizeAddition(lo, hi), sneaky: isSneakySix(lo, hi) });
    }
  }
  return facts;
}

export function buildAdditionCategories() {
  const map = new Map(ADDITION_CATEGORIES.map((c) => [c, []]));
  for (const f of buildAdditionFacts()) map.get(f.category).push(f);
  return map;
}

export function ascending(fact) { return { num1: fact.lo, num2: fact.hi }; }
export function complement(fact) { return { num1: fact.hi, num2: fact.lo }; }

function presentation(fact, orientation) {
  const o = orientation === 'complement' ? complement(fact) : ascending(fact);
  return { key: fact.key, operation: '+', num1: o.num1, num2: o.num2, category: fact.category, orientation, sneaky: fact.sneaky };
}

function shuffleInPlace(arr, rng) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

// Build the curated anchor sampling plan for single-digit addition:
//   - Tough 21: every fact at least once (Sneaky Six in BOTH orientations).
//   - Doubles: all 7.
//   - Easy (add-zero/one/two): sample at least `easyFraction` of each (default half).
// Items are then interleaved with hard categories emphasized early (jittered rank),
// so the run "jumps around" instead of marching 8+1, 8+2, 8+3, ...
// `order`: 'hard-first' (default — demonstrate fluency fast) or 'easy-first'
// (gentler ramp for a learner; easy categories lead, Sneaky Six last).
export function buildAnchorAdditionPlan({ seed = 'anchor-addition', easyFraction = 0.5, order = 'hard-first' } = {}) {
  const rng = makeRng(seed);
  const cats = buildAdditionCategories();
  const items = [];

  for (const f of cats.get('tough-21')) {
    if (f.sneaky) { items.push(presentation(f, 'ascending')); items.push(presentation(f, 'complement')); }
    else { items.push(presentation(f, rng() < 0.5 ? 'ascending' : 'complement')); }
  }
  for (const f of cats.get('doubles')) items.push(presentation(f, 'ascending'));
  for (const cat of EASY_CATEGORIES) {
    const pool = shuffleInPlace([...cats.get(cat)], rng);
    const take = Math.ceil(pool.length * easyFraction);
    for (const f of pool.slice(0, take)) items.push(presentation(f, rng() < 0.5 ? 'ascending' : 'complement'));
  }

  // Emphasize hard (or easy) early; jitter so categories interleave rather than block.
  const HARD_FIRST = { 'tough-21': 0, doubles: 1.2, 'add-two': 2.0, 'add-one': 2.2, 'add-zero': 2.4 };
  const EASY_FIRST = { 'add-zero': 0, 'add-one': 0.2, 'add-two': 0.4, doubles: 1.2, 'tough-21': 2.0 };
  const rank = order === 'easy-first' ? EASY_FIRST : HARD_FIRST;
  const sneakyShift = order === 'easy-first' ? 0.5 : -0.5; // Sneaky Six last in EF, first in HF
  return items
    .map((it) => ({ it, w: rank[it.category] + (it.sneaky ? sneakyShift : 0) + rng() * 1.5 }))
    .sort((a, b) => a.w - b.w)
    .map((x) => x.it);
}
