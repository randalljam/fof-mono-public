// START OF FILE fluency_core.js
//
// Shared, DOM-free fluency logic — the single source of truth for the rubric and
// the roll-up rules used by BOTH the fluency tracker (math_fluency.js) and the
// analysis page (math_analysis.js), and by the DOM-free engine via dependency
// injection (engine/reevaluate.mjs).
//
// Loaded as a plain <script> after math_utils.js (which provides computeMedian,
// parseProblemText, getCanonicalProblemKey, ...). Everything here is declared
// with `function`/`var` so it attaches to the global object in both the browser
// (classic script scope shared across page scripts) and the Node vm test harness
// (tests/load_app.mjs) — `const`/`let` would NOT be visible across vm scripts.
//
// History (newest first):
//   2026-06-20 — extracted evaluateFluencyStatus + checkPermanentStatus + the
//                thresholds/colors/labels out of math_fluency.js; added the
//                roll-up helpers (severity, min/worst-of roll-up, addition
//                categorizer, easy/hard bucket).

var fluencyCoreInfo = `fluency_core.js - shared fluency rubric + roll-ups`;

// --- Rubric thresholds, colors, labels (moved verbatim from math_fluency.js) ---
var defaultFluencyThresholds = {
  windowSize: 5,
  minAccuracy: 0.8,
  greenMs: 2000,
  redMs: 4000,
  retentionSessions: 3
};

var fluencyStatusColors = {
  blue: '#1565c0',     // Permanent - dark blue (frozen/ice metaphor)
  green: '#2e7d32',    // Fluent - green
  yellow: '#f9a825',   // Almost fluent - yellow/amber
  red: '#c62828',      // Needs practice - red
  gray: '#616161',     // Incorrect/doesn't know (has data, below accuracy bar) - darker gray
  nodata: '#e0e0e0',   // No data (no attempts at all) - light gray
  flagged: '#ff9800'
};

var STATUS_LABELS = {
  blue: 'Permanent',
  green: 'Fluent',
  yellow: 'Almost Fluent',
  red: 'Needs Practice',
  gray: 'Incorrect',     // had attempts but fell below the accuracy bar (was "Missing")
  nodata: 'No Data'      // genuinely blank: no attempts on this fact at all
};

// --- Per-fact evaluation (moved verbatim from math_fluency.js) ---
function evaluateFluencyStatus(attempts, thresholds = defaultFluencyThresholds) {
  const windowSize = thresholds.windowSize || defaultFluencyThresholds.windowSize;
  const minAccuracy = thresholds.minAccuracy ?? defaultFluencyThresholds.minAccuracy;
  const greenMs = thresholds.greenMs || defaultFluencyThresholds.greenMs;
  const redMs = thresholds.redMs || defaultFluencyThresholds.redMs;

  // No attempts = no data (distinct from gray/incorrect, which HAS attempts)
  if (!attempts || !attempts.length) {
    return { status: 'nodata', accuracy: 0, medianMs: null, attemptsConsidered: 0, correctCount: 0 };
  }

  const windowAttempts = attempts.slice(-windowSize);
  const attemptsConsidered = windowAttempts.length;
  const correctAttempts = windowAttempts.filter(a => a.isCorrect);
  const correctCount = correctAttempts.length;
  const accuracy = attemptsConsidered ? correctCount / attemptsConsidered : 0;

  // Low accuracy = incorrect/doesn't know (gray) — has data but below the accuracy bar
  if (accuracy < minAccuracy || correctCount === 0) {
    return { status: 'gray', accuracy, medianMs: null, attemptsConsidered, correctCount };
  }

  const responseTimes = correctAttempts.map(a => a.responseTime).filter(t => typeof t === 'number');
  const medianMs = computeMedian(responseTimes);

  // Evaluate speed-based status (green/yellow/red)
  let status = 'nodata';
  if (medianMs !== null) {
    if (medianMs < greenMs) status = 'green';
    else if (medianMs < redMs) status = 'yellow';
    else status = 'red';
  }

  return { status, accuracy, medianMs, attemptsConsidered, correctCount };
}

// Check if a problem has achieved "permanent" (blue) status
// Requires being fluent (green) for N consecutive sessions
function checkPermanentStatus(statusHistory, permanentSessionsThreshold = 5) {
  if (!statusHistory || statusHistory.length < permanentSessionsThreshold) {
    return false;
  }

  // Get last N sessions' status for this problem
  const recentStatuses = statusHistory.slice(-permanentSessionsThreshold);

  // All must be 'green' to achieve permanent (blue)
  return recentStatuses.every(s => s === 'green');
}

// --- Roll-up helpers (new) ---

// Severity order, best -> worst. The roll-up takes the WORST present (the
// "minimum" rule): a group is blue only if every fact is blue; one green makes
// it green; any yellow makes it yellow; any red makes it red; any gray/incorrect
// makes it gray. `nodata` is ignored (not yet observed).
var FLUENCY_SEVERITY = ['blue', 'green', 'yellow', 'red', 'gray'];

function fluencyRollupStatus(statuses) {
  let worstIdx = -1;
  for (const s of statuses || []) {
    const idx = FLUENCY_SEVERITY.indexOf(s);
    if (idx > worstIdx) worstIdx = idx;
  }
  return worstIdx < 0 ? 'nodata' : FLUENCY_SEVERITY[worstIdx];
}

// Count how many facts sit at each status (for chip tooltips / breakdowns).
function fluencyStatusBreakdown(statuses) {
  const counts = { blue: 0, green: 0, yellow: 0, red: 0, gray: 0, nodata: 0 };
  for (const s of statuses || []) {
    if (counts[s] === undefined) counts[s] = 0;
    counts[s]++;
  }
  return counts;
}

// Single-digit addition categorization (numbers form). Mirrors the text-based
// problemCategory() on the analysis page: doubles win over the hardest-six test.
var FLUENCY_CATEGORY_ORDER = ['add-zero', 'add-one', 'add-two', 'doubles', 'tough-21', 'hardest-six'];
var FLUENCY_CATEGORY_LABELS = {
  'add-zero': 'Add 0', 'add-one': 'Add 1', 'add-two': 'Add 2',
  'doubles': 'Doubles', 'tough-21': 'Tough 21', 'hardest-six': 'Hardest 6'
};

function additionCategoryOf(num1, num2) {
  const lo = Math.min(num1, num2), hi = Math.max(num1, num2);
  if (lo === 0) return 'add-zero';
  if (lo === 1) return 'add-one';
  if (lo === 2) return 'add-two';
  if (lo === hi) return 'doubles';
  if (lo >= 6) return 'hardest-six';   // both addends >= 6, unequal
  return 'tough-21';                    // lo in 3..5, unequal
}

// The broad "0-5 vs 6-9" split one level up from the categories: a fact is
// "6-9" (hard) iff it involves a 6..9 operand, else "0-5" (easy).
function easyHardBucket(num1, num2) {
  return Math.max(num1, num2) >= 6 ? '6-9' : '0-5';
}

// ============================================================================
// Fluency-based problem-list generation
// ----------------------------------------------------------------------------
// Build a practice list of arbitrary length with an arbitrary target mix across
// the fluency categories (fluent / almost / needs-practice / incorrect / missing),
// drawn from a learner's attempts over a chosen set of sessions. Pure + DOM-free so
// it is unit-testable; the analysis page wraps it with a thin control/db reader
// (generateProblemListFromControls in math_analysis.js).
//
// Status vocabulary (matches the analysis heatmap the operator reads):
//   green=fluent, yellow=almost, red=needs-practice, gray=incorrect (has data,
//   below the accuracy bar), nodata=missing (no attempts on this fact at all).
// ============================================================================

// Friendly distribution keys -> internal status codes. Callers may use either the
// status code (green/yellow/red/gray/nodata) or a friendly label.
var FLUENCY_STATUS_ALIASES = {
  fluent: 'green', green: 'green',
  almost: 'yellow', 'almost-fluent': 'yellow', yellow: 'yellow',
  'needs-practice': 'red', needspractice: 'red', red: 'red',
  incorrect: 'gray', gray: 'gray', grey: 'gray',
  missing: 'nodata', nodata: 'nodata', 'no-data': 'nodata',
  // a single window can't establish "permanent"; treat blue/permanent as fluent if asked.
  permanent: 'green', blue: 'green'
};
function normalizeStatusKey(key) {
  if (key == null) return null;
  const k = String(key).trim();
  return FLUENCY_STATUS_ALIASES[k] || FLUENCY_STATUS_ALIASES[k.toLowerCase()] || null;
}

// Does an attempt carry any flag? Works for both attempt shapes: a parsed `flags`
// array (analysis page rows) or a raw `flags_json` string (anchor/SQLite rows).
function attemptHasFlags(a) {
  if (a == null) return false;
  if (Array.isArray(a.flags)) return a.flags.length > 0;
  const fj = a.flags_json;
  if (fj == null || fj === '' || fj === '[]' || fj === 'null') return false;
  try { const v = JSON.parse(fj); return Array.isArray(v) ? v.length > 0 : !!v; } catch (e) { return true; }
}

// Fisher-Yates shuffle in place. rng() must return [0,1); defaults to Math.random.
// Injectable so tests are deterministic.
function shuffleInPlace(arr, rng) {
  const r = rng || Math.random;
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(r() * (i + 1));
    const t = arr[i]; arr[i] = arr[j]; arr[j] = t;
  }
  return arr;
}

// Restrict attempts to a chosen set of sessions. selection:
//   { mode: 'all' }                      -> every attempt (default)
//   { mode: 'recentN', n }               -> attempts from the N most-recent sessions
//   { mode: 'sinceDate', since }         -> attempts whose session start_time >= since
// `since` is compared lexicographically against the canonical 'YYYY-MM-DD_HHMMSS'
// start_time, so a 'YYYY-MM-DD' prefix works (zero-padded, date-ordered).
function selectAttemptsBySessions(attempts, selection) {
  const list = (attempts || []).slice();
  if (!selection || !selection.mode || selection.mode === 'all') return list;
  const sidOf = (a) => (a.session_id != null ? a.session_id : String(a.start_time || ''));
  if (selection.mode === 'sinceDate') {
    const since = String(selection.since || '');
    return list.filter((a) => String(a.start_time || '') >= since);
  }
  if (selection.mode === 'recentN') {
    const n = Math.max(1, Math.floor(selection.n || 1));
    const startOf = {};
    for (const a of list) {
      const sid = sidOf(a);
      if (!(sid in startOf)) startOf[sid] = String(a.start_time || '');
    }
    const ranked = Object.keys(startOf).sort((x, y) => startOf[y].localeCompare(startOf[x]));
    const keep = new Set(ranked.slice(0, n));
    return list.filter((a) => keep.has(sidOf(a)));
  }
  return list;
}

// Group attempts by ordered fact key ('num1|op|num2') and evaluate each via the
// shared rubric. Recency-sorted so the rolling window sees the most recent attempts.
// Optionally clipped to [lo,hi]. Returns { key: <evaluateFluencyStatus result> }.
// (computeFluencyByCellKey on the analysis page delegates here.)
function classifyFactsByStatus(attempts, thresholds, opts) {
  const out = {};
  if (typeof evaluateFluencyStatus !== 'function') return out;
  const range = opts && opts.numberRange;
  const lo = range ? range[0] : -Infinity;
  const hi = range ? range[1] : Infinity;
  const groups = {};
  (attempts || []).forEach((p) => {
    const { num1, operation, num2 } = parseProblemText(p.problem_text);
    if (num1 === null || num2 === null || operation === null) return;
    if (num1 < lo || num1 > hi || num2 < lo || num2 > hi) return;
    const key = `${num1}|${operation}|${num2}`;
    (groups[key] || (groups[key] = [])).push(p);
  });
  for (const key in groups) {
    const arr = groups[key].slice().sort((a, b) =>
      String(a.start_time || '').localeCompare(String(b.start_time || '')) ||
      ((a.attempt_id || 0) - (b.attempt_id || 0)));
    const factAttempts = arr.map((p) => ({
      isCorrect: p.is_correct === 1 || p.is_correct === true,
      responseTime: p.response_time_ms
    }));
    out[key] = evaluateFluencyStatus(factAttempts, thresholds);
  }
  return out;
}

// Every ordered fact key for the given operations within [lo,hi]. Ordered
// (num1|op|num2) to match the analysis heatmap cells — 3+4 and 4+3 are distinct
// facts. Divide-by-zero is skipped.
function enumerateFactUniverse(numberRange, operations) {
  const lo = numberRange ? numberRange[0] : 0;
  const hi = numberRange ? numberRange[1] : 9;
  const ops = (operations && operations.length) ? operations : ['+'];
  const keys = [];
  for (const op of ops) {
    for (let a = lo; a <= hi; a++) {
      for (let b = lo; b <= hi; b++) {
        if (op === '/' && b === 0) continue;
        keys.push(`${a}|${op}|${b}`);
      }
    }
  }
  return keys;
}

// Segmentation category of a fact key (addition categories; 'other' for non-+).
function factCategoryOfKey(key) {
  const parts = String(key).split('|');
  const num1 = Number(parts[0]), op = parts[1], num2 = Number(parts[2]);
  if (op !== '+' || !Number.isFinite(num1) || !Number.isFinite(num2)) return 'other';
  return additionCategoryOf(num1, num2);
}
function factKeyToProblemText(key) {
  const parts = String(key).split('|');
  return `${parts[0]} ${parts[1]} ${parts[2]}`;
}

// Turn a target distribution (weights keyed by status) + a total into integer
// per-status counts that sum EXACTLY to `total`:
//   - weights are normalized by their sum (25/50/25 == 1/2/1)
//   - largest-remainder (Hamilton) rounding makes the integers total exactly
//   - a status whose pool is empty is dropped and its share reallocated to the rest
//     (you can't even repeat a category with zero facts)
// Returns { counts: {status:n}, dropped: bool } (dropped when nothing is allocatable).
function allocateCounts(distribution, total, poolSizes) {
  const wanted = {};
  let sumW = 0;
  for (const rawKey in (distribution || {})) {
    const status = normalizeStatusKey(rawKey);
    if (!status) continue;
    const w = Number(distribution[rawKey]);
    if (!(w > 0)) continue;
    if (poolSizes && (poolSizes[status] || 0) === 0) continue;   // no facts -> drop + reallocate
    wanted[status] = (wanted[status] || 0) + w;
    sumW += w;
  }
  const counts = {};
  if (sumW <= 0 || total <= 0) return { counts, dropped: true };
  const remainders = [];
  let assigned = 0;
  for (const status in wanted) {
    const exact = (wanted[status] / sumW) * total;
    const base = Math.floor(exact);
    counts[status] = base;
    assigned += base;
    remainders.push({ status, frac: exact - base });
  }
  let leftover = total - assigned;
  remainders.sort((a, b) => b.frac - a.frac);
  for (let i = 0; leftover > 0 && remainders.length; i++, leftover--) {
    counts[remainders[i % remainders.length].status] += 1;
  }
  return { counts, dropped: false };
}

// Choose `n` fact keys from `pool`. With enough uniques, returns a random distinct
// subset. With fewer (the shortfall case), every fact is used floor(n/pool) times and
// a random subset gets one extra — "balanced repeats", so repeats = n - pool exactly.
// The result is shuffled.
function pickWithRepeats(pool, n, rng) {
  const r = rng || Math.random;
  const src = (pool || []).slice();
  if (n <= 0 || src.length === 0) return [];
  if (src.length >= n) return shuffleInPlace(src, r).slice(0, n);
  const picked = [];
  const fullCycles = Math.floor(n / src.length);
  for (let c = 0; c < fullCycles; c++) picked.push(...src);
  const remainder = n - picked.length;
  if (remainder > 0) picked.push(...shuffleInPlace(src.slice(), r).slice(0, remainder));
  return shuffleInPlace(picked, r);
}

// System cap (not learner-configurable): how many times one problem may appear in a list.
// Tuned so a 20-list allows 3 and a 10-list allows 2 (ceil(0.15·n), floored at 1).
var REPEAT_CAP_FRACTION = 0.15;
function maxRepeatsForList(numProblems) {
  return Math.max(1, Math.ceil(REPEAT_CAP_FRACTION * (numProblems || 0)));
}
// Difficulty rank of a fact key by its addition category (add-zero easiest … hardest-six),
// so generation can bias toward the easier categories. Unknown -> ranked last.
function factDifficultyRank(key) {
  const idx = FLUENCY_CATEGORY_ORDER.indexOf(factCategoryOfKey(key));
  return idx < 0 ? FLUENCY_CATEGORY_ORDER.length : idx;
}
// Draw `n` keys from `pool`, biased to the easier categories first and capped at
// `maxRepeats` copies of any one fact. Facts are grouped by difficulty (easiest first,
// shuffled within a group) then taken round-robin: each fact is used once before any is
// repeated, so for n <= pool size only the easiest facts appear (the bias), and for
// n > pool size repeats spread evenly up to the cap. Returns fewer than `n` only when the
// cap makes `n` unreachable (pool too small). Optional `usedCounts` is a shared Map
// (fact key -> times already placed in the list) so backfill respects the global cap.
function pickEasierFirst(pool, n, maxRepeats, rng, usedCounts) {
  const r = rng || Math.random;
  if (n <= 0 || !pool || !pool.length) return [];
  const cap = Math.max(1, maxRepeats || 1);
  const groups = new Map();
  for (const k of pool) {
    const rank = factDifficultyRank(k);
    if (!groups.has(rank)) groups.set(rank, []);
    groups.get(rank).push(k);
  }
  const ordered = [];
  for (const rank of [...groups.keys()].sort((a, b) => a - b)) ordered.push(...shuffleInPlace(groups.get(rank).slice(), r));
  const used = usedCounts || new Map();
  const out = [];
  let progressed = true;
  while (out.length < n && progressed) {
    progressed = false;
    for (const k of ordered) {
      if (out.length >= n) break;
      const u = used.get(k) || 0;
      if (u >= cap) continue;
      out.push(k); used.set(k, u + 1); progressed = true;
    }
  }
  return out;
}
// When a category can't fill its allocated slots (repeat cap on a tiny pool), spill the
// remainder into other pools in this order (almost -> needs-practice -> missing -> fluent).
var BACKFILL_STATUS_ORDER = ['yellow', 'red', 'nodata', 'green'];
function backfillDrawnKeys(drawnKeys, shortfall, pools, maxRepeats, rng) {
  if (shortfall <= 0 || !drawnKeys) return 0;
  const used = new Map();
  for (const k of drawnKeys) used.set(k, (used.get(k) || 0) + 1);
  let need = shortfall;
  for (const status of BACKFILL_STATUS_ORDER) {
    if (need <= 0) break;
    const pool = pools[status] || [];
    const picked = pickEasierFirst(pool, need, maxRepeats, rng, used);
    drawnKeys.push(...picked);
    need -= picked.length;
  }
  return need;
}
// Arrange a multiset of problems into a presentation order with NO identical problem
// twice in a row. Primary path is "reshuffle the random order until it's clean"; the
// even/odd spread fallback guarantees a valid order whenever one exists (max count
// <= ceil(n/2), always true under the repeat cap).
function hasAdjacentDup(arr) {
  for (let i = 1; i < arr.length; i++) if (arr[i] === arr[i - 1]) return true;
  return false;
}
function arrangeNoAdjacentDup(arr, rng) {
  const r = rng || Math.random;
  if (!arr || arr.length < 2) return (arr || []).slice();
  for (let attempt = 0; attempt < 30; attempt++) {
    const a = shuffleInPlace(arr.slice(), r);
    if (!hasAdjacentDup(a)) return a;
  }
  const counts = new Map();
  for (const x of arr) counts.set(x, (counts.get(x) || 0) + 1);
  const items = shuffleInPlace([...counts.keys()], r).sort((a, b) => counts.get(b) - counts.get(a));
  const res = new Array(arr.length);
  let idx = 0;
  for (const item of items) {
    for (let c = counts.get(item); c > 0; c--) { res[idx] = item; idx += 2; if (idx >= arr.length) idx = 1; }
  }
  return res;
}

// Overall fluency as an integer percent: the share of the fact universe (default
// single-digit addition, 0-9) the learner is fluent at (green/blue), classified via the
// shared rubric over their attempts. Used for the start-vs-end readout on the anchor page.
function fluencyPercent(attempts, thresholds, options) {
  const opts = options || {};
  const numberRange = opts.numberRange || [0, 9];
  const operations = (opts.operations && opts.operations.length) ? opts.operations : ['+'];
  const universe = enumerateFactUniverse(numberRange, operations);
  if (!universe.length) return 0;
  let selected = attempts || [];
  if (opts.excludeFlagged) selected = selected.filter((a) => !attemptHasFlags(a));
  const observed = classifyFactsByStatus(selected, thresholds || defaultFluencyThresholds, { numberRange });
  let fluent = 0;
  for (const key of universe) {
    const st = observed[key] && observed[key].status;
    if (st === 'green' || st === 'blue') fluent++;
  }
  return Math.round((fluent / universe.length) * 100);
}

// MAIN ENTRY. Build a problem list from a learner's attempts.
// options: {
//   attempts,                  // flat attempts [{problem_text, is_correct, response_time_ms, start_time, attempt_id, session_id}]
//   numProblems,               // desired list length
//   distribution,              // weights by status, e.g. { almost:0.5, 'needs-practice':0.25, fluent:0.25 }
//   thresholds,                // { greenMs, redMs, windowSize, minAccuracy } (defaults to defaultFluencyThresholds)
//   sessionSelection,          // { mode:'all'|'recentN'|'sinceDate', n, since } (default all)
//   numberRange,               // [lo,hi] (default [0,9])
//   operations,                // ['+'] default
//   categories,                // optional addition-segmentation filter (Set/array of category keys)
//   excludeFlagged,            // when true, flagged attempts are dropped before classification
//   rng                        // optional () => [0,1) for deterministic output
// }
// Returns { problems:[text], statusByKey, counts, requested, poolSizes, repeats, warnings }.
function generateFluencyProblemList(options) {
  const opts = options || {};
  const numProblems = Math.max(0, Math.floor(opts.numProblems || 0));
  const thresholds = opts.thresholds || defaultFluencyThresholds;
  const numberRange = opts.numberRange || [0, 9];
  const operations = (opts.operations && opts.operations.length) ? opts.operations : ['+'];
  const rng = opts.rng || Math.random;
  const distribution = opts.distribution || { green: 1, yellow: 1, red: 1, gray: 1 };
  const warnings = [];

  // 1) session selection (and, for generation, drop flagged attempts so a flagged answer
  //    never colors a fact's fluency) then 2) classify observed facts over the universe
  let selected = selectAttemptsBySessions(opts.attempts, opts.sessionSelection);
  if (opts.excludeFlagged) selected = selected.filter((a) => !attemptHasFlags(a));
  const observed = classifyFactsByStatus(selected, thresholds, { numberRange });
  let universe = enumerateFactUniverse(numberRange, operations);
  if (opts.categories && (Array.isArray(opts.categories) ? opts.categories.length : opts.categories.size)) {
    const wanted = new Set(Array.isArray(opts.categories) ? opts.categories : Array.from(opts.categories));
    universe = universe.filter((k) => wanted.has(factCategoryOfKey(k)));
  }

  const statusByKey = {};
  const pools = { green: [], yellow: [], red: [], gray: [], nodata: [] };
  for (const key of universe) {
    const status = (observed[key] && observed[key].status) || 'nodata';   // unobserved = missing
    statusByKey[key] = status;
    (pools[status] || (pools[status] = [])).push(key);
  }
  const poolSizes = {};
  for (const s in pools) poolSizes[s] = pools[s].length;

  // 3) distribution -> integer counts
  const alloc = allocateCounts(distribution, numProblems, poolSizes);
  if (alloc.dropped) {
    warnings.push('No facts available for any requested category in the selected sessions/range.');
    return { problems: [], statusByKey, counts: {}, requested: distribution, poolSizes, repeats: 0, warnings };
  }
  // note any requested category dropped for an empty pool (its share was reallocated)
  for (const rawKey in distribution) {
    const status = normalizeStatusKey(rawKey);
    if (status && Number(distribution[rawKey]) > 0 && (poolSizes[status] || 0) === 0) {
      warnings.push(`No "${rawKey}" facts available; its share was reallocated to the other categories.`);
    }
  }

  // 4) draw each status' facts: bias to the easier categories first and cap how many times
  //    any one problem repeats (system rule); 5) backfill any shortfall from other pools;
  //    6) order so none repeats back-to-back.
  const counts = alloc.counts;
  const maxRepeats = maxRepeatsForList(numProblems);
  const drawnKeys = [];
  for (const status in counts) {
    const need = counts[status];
    const pool = pools[status] || [];
    const drawn = pickEasierFirst(pool, need, maxRepeats, rng);
    if (drawn.length < need) warnings.push(`Only ${drawn.length} of ${need} "${status}" slots filled — the ${maxRepeats}× repeat cap limits a ${pool.length}-fact pool.`);
    drawnKeys.push(...drawn);
  }
  const shortfall = numProblems - drawnKeys.length;
  if (shortfall > 0) {
    const stillShort = backfillDrawnKeys(drawnKeys, shortfall, pools, maxRepeats, rng);
    if (stillShort > 0) warnings.push(`Could only fill ${numProblems - stillShort} of ${numProblems} slots after backfill.`);
  }
  const repeats = drawnKeys.length - new Set(drawnKeys).size;
  const arranged = arrangeNoAdjacentDup(drawnKeys.map(factKeyToProblemText), rng);
  return { problems: arranged, statusByKey, counts, requested: distribution, poolSizes, repeats, maxRepeats, warnings };
}

// Easy warm-up categories for Fluency feast: add-zero / add-one / add-two / doubles.
var FLUENCY_FEAST_EASY_START_CATEGORIES = ['add-zero', 'add-one', 'add-two', 'doubles'];
function factKeySum(key) {
  const parts = String(key).split('|');
  return Number(parts[0]) + Number(parts[2]);
}
function pickRandomFactKey(pool, rng) {
  if (!pool || !pool.length) return null;
  return pool[Math.floor((rng || Math.random)() * pool.length)];
}
// Two easy warm-up problems for Fluency feast:
//   1) fluent fact from easy categories with a single-digit sum (< 10)
//   2) fluent fact from easy categories with a two-digit sum (>= 10)
// Fallbacks: if no fluent two-digit, use another fluent single-digit; if still short,
// randomly pick the missing slots from the easy categories (any fluency status).
// Returns { problems:[text,text], keys:[key,key], mode:'ideal'|'partial'|'fallback' }.
function pickFluencyFeastEasyStart(options) {
  const opts = options || {};
  const thresholds = opts.thresholds || defaultFluencyThresholds;
  const numberRange = opts.numberRange || [0, 9];
  const rng = opts.rng || Math.random;
  let selected = selectAttemptsBySessions(opts.attempts, opts.sessionSelection);
  if (opts.excludeFlagged) selected = selected.filter((a) => !attemptHasFlags(a));
  const observed = classifyFactsByStatus(selected, thresholds, { numberRange });
  const easyKeys = enumerateFactUniverse(numberRange, ['+']).filter((k) =>
    FLUENCY_FEAST_EASY_START_CATEGORIES.indexOf(factCategoryOfKey(k)) >= 0);
  const isFluent = (k) => {
    const st = observed[k] && observed[k].status;
    return st === 'green' || st === 'blue';
  };
  const fluentSingle = easyKeys.filter((k) => isFluent(k) && factKeySum(k) < 10);
  const fluentDouble = easyKeys.filter((k) => isFluent(k) && factKeySum(k) >= 10);
  let first = pickRandomFactKey(fluentSingle, rng);
  let second = null;
  if (first && fluentDouble.length) second = pickRandomFactKey(fluentDouble, rng);
  else if (first) {
    const rest = fluentSingle.filter((k) => k !== first);
    if (rest.length) second = pickRandomFactKey(rest, rng);
  }
  let mode = (first && second)
    ? (fluentDouble.length ? 'ideal' : 'partial')
    : 'fallback';
  if (!first || !second) {
    const used = new Set([first, second].filter(Boolean));
    const fill = shuffleInPlace(easyKeys.filter((k) => !used.has(k)).slice(), rng);
    if (!first) first = fill.shift() || pickRandomFactKey(easyKeys, rng);
    if (!second) second = fill.shift() || pickRandomFactKey(easyKeys.filter((k) => k !== first), rng) || first;
    mode = 'fallback';
  }
  const keys = [first, second];
  return { problems: keys.map(factKeyToProblemText), keys, mode };
}
