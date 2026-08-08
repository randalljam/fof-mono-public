// Pure problem-list GENERATOR for the editor's "Generate" tool: build a list of N addition
// problems from a percentage mix of categories. DOM-free + rng-injectable so the allocation
// and sampling are deterministic under test. Built on the addition taxonomy (0-9, 55 unique
// facts) from addition_segmentation.mjs, with the "Sneaky Six" (hardest 6) split out of
// tough-21 into its own selectable category.
import { buildAdditionFacts, categorizeAddition, isSneakySix } from './addition_segmentation.mjs';

// The selectable generator categories (ids match the analysis page's seq buckets where they
// overlap). They partition the 55 facts: 10 + 9 + 8 + 7 + 15 + 6 = 55.
export const GENERATOR_CATEGORIES = [
  { id: 'add-zero', label: 'Add 0' },
  { id: 'add-one', label: 'Add 1' },
  { id: 'add-two', label: 'Add 2' },
  { id: 'doubles', label: 'Doubles' },
  { id: 'tough-21', label: 'Tough (rest)' },
  { id: 'sneaky-six', label: 'Hardest 6' },
];
const CATEGORY_IDS = GENERATOR_CATEGORIES.map((c) => c.id);

// Sneaky Six (both addends >= 6, not a double) is split out of tough-21 into its own bucket.
function generatorCategory(lo, hi) {
  if (isSneakySix(lo, hi)) return 'sneaky-six';
  return categorizeAddition(lo, hi);
}

// Map of category id -> array of facts {lo, hi}. Only addition (0-9) for now.
export function categoryPools() {
  const pools = new Map(CATEGORY_IDS.map((id) => [id, []]));
  for (const f of buildAdditionFacts()) pools.get(generatorCategory(f.lo, f.hi)).push(f);
  return pools;
}

// Allocate `count` slots across category ids by weight using largest-remainder, so the parts
// sum to exactly `count`. With no positive weights, splits evenly across `ids`.
export function allocateCounts(count, weights, ids) {
  const n = Math.max(0, Math.floor(Number(count) || 0));
  const w = (id) => Math.max(0, Number((weights || {})[id]) || 0);
  const total = ids.reduce((s, id) => s + w(id), 0);
  const counts = Object.fromEntries(ids.map((id) => [id, 0]));
  if (n === 0 || ids.length === 0) return counts;
  if (total <= 0) {                          // even split
    const base = Math.floor(n / ids.length);
    ids.forEach((id) => { counts[id] = base; });
    let rem = n - base * ids.length;
    for (let i = 0; i < rem; i++) counts[ids[i]]++;
    return counts;
  }
  const exact = ids.map((id) => ({ id, e: (w(id) / total) * n }));
  let assigned = 0;
  for (const r of exact) { counts[r.id] = Math.floor(r.e); assigned += counts[r.id]; }
  let rem = n - assigned;                     // hand out the remainder by largest fraction
  exact.map((r) => ({ id: r.id, frac: r.e - Math.floor(r.e) }))
    .sort((a, b) => b.frac - a.frac)
    .forEach((r) => { if (rem > 0) { counts[r.id]++; rem--; } });
  return counts;
}

function shuffle(arr, rng) {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

// Build a list of `count` problems mixed across categories by `weights` (id -> relative
// percent/weight). Each slot draws a random fact from its category's pool (repeats allowed
// when the count exceeds the pool), in a random or fixed orientation, then the whole list is
// shuffled. Returns [{num1, operation:'+', num2, category, problem_text}].
export function generateMix({ count = 20, weights = {}, rng = Math.random, orientation = 'random' } = {}) {
  const pools = categoryPools();
  const ids = CATEGORY_IDS.filter((id) => (pools.get(id) || []).length > 0);
  const counts = allocateCounts(count, weights, ids);
  const out = [];
  for (const id of ids) {
    const pool = pools.get(id) || [];
    for (let i = 0; i < (counts[id] || 0); i++) {
      const f = pool[Math.floor(rng() * pool.length)];
      const flip = orientation === 'complement' || (orientation === 'random' && rng() < 0.5);
      const num1 = flip ? f.hi : f.lo;
      const num2 = flip ? f.lo : f.hi;
      out.push({ num1, operation: '+', num2, category: id, problem_text: `${num1} + ${num2}` });
    }
  }
  return shuffle(out, rng);
}

// Render generated/parsed items to editor textarea text (one "a + b" per line).
export function itemsToText(items) {
  return (items || []).map((it) => it.problem_text || `${it.num1} ${it.operation || '+'} ${it.num2}`).join('\n');
}
