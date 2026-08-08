// Pure problem-list sequence helpers shared by the anchor page's file-list and
// "Use internal" paths. DOM-free, fetch-free, and rng-injectable so the expansion
// (replicate -> optional shuffle -> per-item key/index) is unit-testable in Node.
// The internal-list items come from the dev server (engine/sqlite_io loadLatestUserDb
// -> problemLists), stored by tools/problem_list_store.py.

const VALID_OPS = ['+', '-', '*'];

// Fisher-Yates shuffle with an injectable rng (defaults to Math.random).
export function shuffleWith(items, rng) {
  const out = [...items];
  const rand = typeof rng === 'function' ? rng : Math.random;
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

// Expand base items into the run sequence: `replicates` copies (clamped 1..maxReplicates),
// each item tagged with a stable key + listReplicate/listIndex, optionally shuffled. Returns
// { reps, sequence }. Used by both the .txt file path and the internal-list path so they
// share one definition of replicate/randomize behavior.
export function expandProblemListItems(baseItems, { replicates = 1, randomize = false, maxReplicates = 4, rng } = {}) {
  const reps = Math.max(1, Math.min(maxReplicates, Number(replicates) || 1));
  const base = baseItems || [];
  const expanded = [];
  for (let rep = 0; rep < reps; rep++) {
    for (let i = 0; i < base.length; i++) {
      const it = base[i];
      expanded.push({
        ...it,
        key: `${it.operation}|${it.num1}|${it.num2}|${rep * base.length + i}`,
        listReplicate: rep + 1,
        listIndex: i,
      });
    }
  }
  return { reps, sequence: randomize ? shuffleWith(expanded, rng) : expanded };
}

// Coerce one stored internal-list item into a runnable { num1, operation, num2, category }.
// Prefers the stored numeric columns; falls back to parsing problem_text via `parseLine`
// (the page's parser) when they're absent. Returns null if it can't be made runnable.
export function normalizeInternalItem(item, parseLine) {
  if (!item) return null;
  let { num1, operation, num2 } = item;
  if (!Number.isFinite(num1) || !Number.isFinite(num2) || !VALID_OPS.includes(operation)) {
    let parsed = null;
    try { parsed = typeof parseLine === 'function' ? parseLine(item.problem_text) : null; } catch { parsed = null; }
    if (!parsed) return null;
    ({ num1, operation, num2 } = parsed);
  }
  if (!Number.isFinite(num1) || !Number.isFinite(num2) || !VALID_OPS.includes(operation)) return null;
  return { num1, num2, operation, category: item.category || 'problem-list' };
}

// Turn a stored internal list (with .items) into the runnable base items, dropping any
// that can't be parsed. Throws when nothing usable remains so the caller can surface it.
export function internalListBaseItems(list, parseLine) {
  const items = ((list && list.items) || []).map((it) => normalizeInternalItem(it, parseLine)).filter(Boolean);
  if (!items.length) throw new Error(`Internal list "${(list && list.list_name) || ''}" has no usable problems.`);
  return items;
}
