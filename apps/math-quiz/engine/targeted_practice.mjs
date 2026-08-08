// Targeted fluency practice — DOM-free engine.
//
// Drives a practice SESSION focused on 1-5 coach-chosen TARGET problems plus
// FILLER problems (from a stored "target filler" list). Targets are worked
// SERIALLY, one at a time, in order: only the current (first not-yet-graduated)
// target is mixed in with filler. There is NO burst — problems stream one at a
// time, each either the current target or a random filler chosen by a
// percent-target ratio. A target "graduates" after `graduationStreak` CUMULATIVE
// fast-correct answers — rings are never lost, so a slow or wrong answer keeps the
// rings already earned; when it graduates, the next target becomes current. The
// whole run is ONE SQLite session; it ends only when every target has graduated
// (Quit & save at any time stores the partial session). Consumed by the anchor
// page (DOM) and by tests via dependency injection, like engine/assess_flow.mjs.
//
// History (newest first):
//   2026-06-23 — cumulative fast-correct: `graduationStreak` counts TOTAL
//                fast-correct answers (no longer in-a-row); rings are never lost.
//   2026-06-23 — serial targets + streaming nextProblem() (removed bursts);
//                record() reports graduations; progress().current drives the
//                target-rings graphic; requeue() for Flag-previous "insert".
//   2026-06-23 — 1-5 targets, filler pool, percent-target, no max-bursts.
//   2026-06-23 — initial targeted-practice engine.
import { buildFactMatrix, makeRng, isHardFact } from '../simulation/adaptive_selector.mjs';

// Operations whose two operands commute, so `3 + 6` and `6 + 3` are one problem.
const COMMUTATIVE_OPS = new Set(['+', '*']);

// Canonical, orientation-insensitive key for a problem — matches buildFactMatrix:
// commutative ops sort the operands (`+|3|6`), others keep order (`-|9|4`).
export function canonicalKey(num1, num2, operation) {
  let n1 = num1, n2 = num2;
  if (COMMUTATIVE_OPS.has(operation)) { n1 = Math.min(num1, num2); n2 = Math.max(num1, num2); }
  return `${operation}|${n1}|${n2}`;
}

// The 1-2 display orientations of a target. Doubles (3+3) and non-commutative
// problems have a single orientation; other commutative problems have both.
export function expandOrientations(num1, num2, operation) {
  const a = { num1, num2, operation };
  if (!COMMUTATIVE_OPS.has(operation) || num1 === num2) return [a];
  return [a, { num1: num2, num2: num1, operation }];
}

// Parse one typed problem spec ("3+6", "3 + 6", "8x7", "8*7", "9-4") into
// { num1, num2, operation, key } or null. Whitespace around the operator is
// accepted; ×/÷ normalize to *,/; orientation is preserved (6+0 stays 6+0).
export function parseTargetSpec(text) {
  if (text == null) return null;
  const cleaned = String(text)
    .replace(/×|x|X/g, '*')
    .replace(/÷/g, '/')
    .replace(/−/g, '-')
    .trim();
  const m = cleaned.match(/^(\d+)\s*([+\-*/])\s*(\d+)$/);
  if (!m) return null;
  const num1 = parseInt(m[1], 10);
  const num2 = parseInt(m[3], 10);
  const operation = m[2];
  if (Number.isNaN(num1) || Number.isNaN(num2)) return null;
  return { num1, num2, operation, key: canonicalKey(num1, num2, operation) };
}

// The normalized, whitespace-free display form of a parsed problem ("3+6").
export function factToText(spec) {
  return `${spec.num1}${spec.operation}${spec.num2}`;
}

// Parse up to `max` typed target strings, deduping by canonical key (so the same
// problem typed twice, in either orientation, collapses to one target). Returns
// { targets, errors }: targets keep first-typed orientation.
export function parseTargets(inputs, { max = 5 } = {}) {
  const targets = [];
  const errors = [];
  const seen = new Set();
  for (const raw of inputs || []) {
    if (raw == null || String(raw).trim() === '') continue;
    const spec = parseTargetSpec(raw);
    if (!spec) { errors.push(String(raw)); continue; }
    if (seen.has(spec.key)) continue;
    seen.add(spec.key);
    targets.push(spec);
    if (targets.length >= max) break;
  }
  return { targets, errors };
}

// Parse the filler list (one problem per line / entry). Filler problems KEEP their
// exact orientation (6+0 and 0+6 are distinct) and are NOT deduped; only blanks
// are skipped. Returns { facts, errors }.
export function parseFillerFacts(inputs) {
  const facts = [];
  const errors = [];
  for (const raw of inputs || []) {
    if (raw == null || String(raw).trim() === '') continue;
    const spec = parseTargetSpec(raw);
    if (!spec) { errors.push(String(raw)); continue; }
    facts.push(spec);
  }
  return { facts, errors };
}

// "Nearby review" fallback for when no filler list is provided: same-operation
// problems that share an operand with a target, nearest-first. Returns canonical keys.
export function nearbyReviewFacts(targetKeys, factMatrix, { limit = 12 } = {}) {
  const targetSet = new Set(targetKeys);
  const targets = [];
  for (const k of targetKeys) {
    const f = factMatrix.get(k);
    if (f) targets.push(f);
  }
  const ops = new Set(targets.map((t) => t.operation));
  const scored = [];
  for (const [key, fact] of factMatrix) {
    if (targetSet.has(key)) continue;
    if (!ops.has(fact.operation)) continue;
    let best = Infinity;
    let sharesOperand = false;
    for (const t of targets) {
      if (t.operation !== fact.operation) continue;
      const tOps = [t.num1, t.num2];
      const fOps = [fact.num1, fact.num2];
      if (fOps.some((o) => tOps.includes(o))) sharesOperand = true;
      const d = Math.min(Math.abs(fact.num1 - t.num1) + Math.abs(fact.num2 - t.num2),
                         Math.abs(fact.num1 - t.num2) + Math.abs(fact.num2 - t.num1));
      if (d < best) best = d;
    }
    scored.push({ key, sharesOperand, distance: best });
  }
  scored.sort((a, b) => (Number(b.sharesOperand) - Number(a.sharesOperand)) || (a.distance - b.distance) || (a.key < b.key ? -1 : 1));
  return scored.slice(0, limit).map((s) => s.key);
}

// Create a targeted-practice run controller (serial, streaming).
//
// options:
//   targets          - parsed target specs ({num1,num2,operation[,key]}) or
//                      canonical key strings. 1-5, worked in order. Required.
//   factMatrix       - fact matrix (buildFactMatrix). Fallback filler + key expand.
//   fillerFacts      - the filler pool: display problems ({num1,num2,operation}) or
//                      canonical key strings (orientation preserved). When empty,
//                      falls back to nearbyReviewFacts.
//   percentTarget    - % of problems that are the current target (default 50); the
//                      rest are random filler. 1-100.
//   graduationStreak - consecutive fast-correct answers to graduate a target (default 3).
//   fastMs           - "fast" ceiling; <= this AND correct counts toward a streak (default 2000).
//   rng              - seeded RNG (default seeded).
export function createTargetedRun(options = {}) {
  const {
    targets: rawTargets = [],
    factMatrix = null,
    fillerFacts = null,
    percentTarget = 50,
    graduationStreak = 3,
    fastMs = 2000,
    rng = makeRng('targeted-practice'),
  } = options;

  const targetRatio = Math.min(1, Math.max(0, percentTarget / 100));

  const targets = rawTargets.map((t) => {
    if (typeof t === 'string') {
      const f = factMatrix && factMatrix.get(t);
      const [operation, a, b] = t.split('|');
      const num1 = f ? f.num1 : parseInt(a, 10);
      const num2 = f ? f.num2 : parseInt(b, 10);
      return { key: t, num1, num2, operation: f ? f.operation : operation, isHard: isHardFact(num1, num2) };
    }
    const key = t.key || canonicalKey(t.num1, t.num2, t.operation);
    return { key, num1: t.num1, num2: t.num2, operation: t.operation, isHard: isHardFact(t.num1, t.num2) };
  });
  if (targets.length === 0) throw new Error('createTargetedRun requires at least one target');

  const targetKeys = targets.map((t) => t.key);
  const targetByKey = new Map(targets.map((t) => [t.key, t]));

  // Filler pool of display items {key,num1,num2,operation}, excluding any whose
  // canonical key matches a target (a target is never filler).
  const toFillerItem = (f) => {
    if (typeof f === 'string') {
      const fm = factMatrix && factMatrix.get(f);
      const [operation, a, b] = f.split('|');
      const num1 = fm ? fm.num1 : parseInt(a, 10);
      const num2 = fm ? fm.num2 : parseInt(b, 10);
      return { key: f, num1, num2, operation: fm ? fm.operation : operation };
    }
    return { key: canonicalKey(f.num1, f.num2, f.operation), num1: f.num1, num2: f.num2, operation: f.operation };
  };
  // Filler is strictly the configured "target filler" list (a target is never filler).
  // With no filler list, every problem is the current target (the percent has nothing
  // to draw from). nearbyReviewFacts stays available for callers that want it.
  const fillerPool = (fillerFacts || []).map(toFillerItem).filter((f) => !targetByKey.has(f.key));

  const streak = new Map(targetKeys.map((k) => [k, 0]));
  const graduated = new Set();
  const attemptCount = new Map(targetKeys.map((k) => [k, 0]));
  const fastCorrectCount = new Map(targetKeys.map((k) => [k, 0]));
  const redeliver = [];           // [{ item, dueAt }] — Flag-previous "insert" re-asks
  let orientationFlip = 0;
  let presentedCount = 0;
  let fillerRemaining = 0;        // filler problems still to deal before the next target try

  // Filler "deck": a shuffled copy of the pool we draw off the top, reshuffling when
  // exhausted — even coverage, no RNG repeats (vs. independent random picks).
  const shuffle = (arr) => {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
    return a;
  };
  let deck = shuffle(fillerPool);
  let deckIdx = 0;
  const drawFiller = () => {
    if (fillerPool.length === 0) return null;
    if (deckIdx >= deck.length) { deck = shuffle(fillerPool); deckIdx = 0; }
    return { ...deck[deckIdx++], role: 'filler' };
  };
  // Filler problems between target tries, from the percent: round((100-p)/p), >= 1 so there
  // is ALWAYS at least one other problem between tries (0 when no filler / p>=100).
  const fillerSpacing = () => {
    if (fillerPool.length === 0 || percentTarget >= 100) return 0;
    return Math.max(1, Math.round((100 - percentTarget) / percentTarget));
  };

  const activeTargets = () => targetKeys.filter((k) => !graduated.has(k));
  const currentTargetKey = () => activeTargets()[0] || null;

  // Display item for the current target, alternating orientation each use so both
  // 3+6 and 6+3 are practiced (doubles / non-commutative collapse to one).
  const targetItem = (key) => {
    const t = targetByKey.get(key);
    const orients = expandOrientations(t.num1, t.num2, t.operation);
    const o = orients[orientationFlip % orients.length];
    orientationFlip++;
    return { key, num1: o.num1, num2: o.num2, operation: o.operation, role: 'target' };
  };

  function isComplete() { return graduated.size === targetKeys.length; }
  function completionReason() { return isComplete() ? 'all-graduated' : null; }

  // The next problem to present, or null when every target has graduated. Honors due
  // Flag-previous re-asks first; otherwise deals `gap` filler between each target try
  // (gap = random in [1, fillerSpacing]) so a target never repeats back-to-back.
  function nextProblem() {
    if (isComplete()) return null;
    presentedCount++;
    const dueIdx = redeliver.findIndex((r) => r.dueAt <= presentedCount);
    if (dueIdx !== -1) return redeliver.splice(dueIdx, 1)[0].item;
    if (fillerRemaining > 0) {
      const f = drawFiller();
      if (f) { fillerRemaining--; return f; }
      fillerRemaining = 0;               // pool somehow empty — fall through to the target
    }
    const item = targetItem(currentTargetKey());
    const spacing = fillerSpacing();
    fillerRemaining = spacing > 0 ? 1 + Math.floor(rng() * spacing) : 0;   // random in [1, spacing]
    return item;
  }

  // Re-ask a problem ~gap problems later (Flag-previous "Continue & insert").
  function requeue(item, gap = 5) {
    if (item && item.key) redeliver.push({ item: { ...item }, dueAt: presentedCount + gap });
  }

  // Record a response. Returns { graduated: <key|null> } so the UI can celebrate
  // exactly when a target hits the bar. Only TARGET responses count; filler is
  // ignored. Both orientations advance the same count (canonical key). Progress is
  // CUMULATIVE — fast-correct answers add a ring; a slow/wrong answer never removes
  // one (the learner keeps every ring earned). Graduates at `graduationStreak`
  // total fast-correct (no longer "in a row").
  function record(item, resp) {
    const key = item && item.key;
    if (!key || !targetByKey.has(key)) return { graduated: null };
    attemptCount.set(key, (attemptCount.get(key) || 0) + 1);
    const fast = !!resp && resp.isCorrect && typeof resp.responseTime === 'number' && resp.responseTime <= fastMs;
    let graduatedKey = null;
    if (fast) {
      fastCorrectCount.set(key, (fastCorrectCount.get(key) || 0) + 1);
      const s = (streak.get(key) || 0) + 1;
      streak.set(key, s);
      if (s >= graduationStreak && !graduated.has(key)) { graduated.add(key); graduatedKey = key; fillerRemaining = 0; }
    }
    // else: a slow or wrong answer does nothing — rings already earned are kept.
    return { graduated: graduatedKey };
  }

  // Live progress; `current` drives the target-rings graphic (which problem is
  // active and how many fast-correct earned so far — cumulative, `streak` field).
  function progress() {
    const curKey = currentTargetKey();
    const curT = curKey ? targetByKey.get(curKey) : null;
    return {
      totalTargets: targetKeys.length,
      graduatedTargets: graduated.size,
      fraction: targetKeys.length ? graduated.size / targetKeys.length : 0,
      graduationStreak,
      problemsPresented: presentedCount,
      current: curT ? {
        key: curKey, num1: curT.num1, num2: curT.num2, operation: curT.operation,
        index: targetKeys.indexOf(curKey), streak: streak.get(curKey) || 0, graduationStreak,
      } : null,
      perTarget: targets.map((t) => ({
        key: t.key, num1: t.num1, num2: t.num2, operation: t.operation,
        streak: streak.get(t.key) || 0, graduated: graduated.has(t.key), graduationStreak,
      })),
    };
  }

  // Metadata persisted into the SQLite session (SPEC §6/§8).
  function metadata() {
    const curKey = currentTargetKey();
    return {
      mode: 'targeted-practice',
      targets: targetKeys,
      targetCount: targetKeys.length,
      fillerPoolSize: fillerPool.length,
      percentTarget,
      graduationStreak,
      fastMs,
      problemsPresented: presentedCount,
      graduated: [...graduated],
      complete: isComplete(),
      completionReason: completionReason(),
      currentTargetKey: curKey,
      activeTargets: activeTargets(),
      perTarget: targets.map((t) => ({
        key: t.key, streak: streak.get(t.key) || 0, graduated: graduated.has(t.key),
        attempts: attemptCount.get(t.key) || 0, fastCorrect: fastCorrectCount.get(t.key) || 0,
      })),
    };
  }

  return {
    targets,
    fillerPool,
    nextProblem,
    requeue,
    record,
    progress,
    metadata,
    isComplete,
    completionReason,
    activeTargets,
    currentTargetKey,
  };
}
