// C3 — anchor assess flow: fast fluency demonstration. Delivers a fixed,
// hard-first sequence; discards a warm-up; applies the re-deliver-and-confirm
// glitch rule; concludes via the REAL predictive-mastery check (reused from the
// selector). Designed to conclude "totally fluent" in a partial sample while
// tolerating isolated slips, and to surface weak facts for a non-fluent learner.
// See 2026-06-15_assess-practice-modes-spec-and-plan.md §5 / Part C (C3).
import { checkPredictiveMastery } from '../simulation/adaptive_selector.mjs';

function shuffleInPlace(arr, rng) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

// Fixed hard-first ordering: all hard facts, then easy. Optional within-group
// shuffle (seeded) — off by default (the locked starter is the fixed sequence).
export function buildAssessSequence(factMatrix, { rng = null } = {}) {
  const hard = [], easy = [];
  for (const [key, fact] of factMatrix) (fact.isHard ? hard : easy).push(key);
  if (rng) { shuffleInPlace(hard, rng); shuffleInPlace(easy, rng); }
  return [...hard, ...easy];
}

// Realism guardrail signal: EASY facts (not hard) that came back slow/wrong with
// no fast+correct attempt. A real learner struggles on hard facts, not easy ones,
// so several slow easy facts usually mean a glitch / distraction / not-serious
// input — a reason to suggest ending the session, not a fluency result.
export function findSlowEasyFacts(attempts, factMatrix, fastMs = 2000) {
  const out = [];
  for (const [key, list] of attempts) {
    const fact = factMatrix.get(key);
    if (!fact || fact.isHard || !list.length) continue;
    if (!list.some((a) => a.isCorrect && a.responseTime <= fastMs)) out.push(key);
  }
  return out;
}

// options:
//   fastMs           - "fluent" response ceiling (default 2000 == greenMs)
//   warmupDiscard    - leading responses excluded from judgment (default 2)
//   redeliverSpacing - problems to wait before re-delivering a deviating fact (default 5)
//   predictiveParams - passed to checkPredictiveMastery
//   truncateOnMastery- conclude (and stop) as soon as predictive mastery fires
//                      (default true). Set false to administer a full curated
//                      `sequence` and judge at the end.
//   sequence         - custom ordered presentations: fact keys, or display items
//                      { key, num1, num2 } (e.g. the addition anchor plan). When
//                      omitted, a hard-first sequence is built from the matrix.
//   rng              - if set, shuffles within hard/easy groups (default sequence)
export function createAssessRun(factMatrix, options = {}) {
  const {
    fastMs = 2000,
    warmupDiscard = 2,
    redeliverSpacing = 5, // problems to wait before re-asking a slow/missed fact
    predictiveParams = {},
    truncateOnMastery = true,
    sequence = null,
    rng = null,
    anomalyEasyThreshold = 3, // >= this many slow easy facts trips the guardrail (0 = off)
    autoRedeliver = true,     // auto re-ask slow/glitchy facts (off for fixed problem lists)
  } = options;

  // Normalize each entry to a display item { key, num1, num2, operation }.
  const toItem = (entry) => {
    if (typeof entry === 'string') {
      const f = factMatrix.get(entry) || {};
      return { key: entry, num1: f.num1, num2: f.num2, operation: f.operation };
    }
    return entry;
  };
  const items = (sequence || buildAssessSequence(factMatrix, { rng })).map(toItem);

  let pos = 0;
  let presented = 0;
  let recorded = 0;
  let warmupCount = 0;
  let lastPresented = null;     // { item, isRecheck }
  let currentItemRef = null;
  let conclusion = null;

  const counted = new Map();    // key -> [{ isCorrect, responseTime }] (judgment set)
  const pending = new Map();    // key -> held deviation awaiting re-delivery
  const redeliver = [];         // [{ item, dueAt }]
  const glitches = [];          // discarded (non-representative) deviations
  const confirmedWeak = new Set();
  const allResponses = new Map(); // key -> [resp] every post-warmup response (for the guardrail)

  const isFast = (r) => r.isCorrect && r.responseTime <= fastMs;
  const pushCounted = (key, resp) => {
    const a = counted.get(key) || [];
    a.push({ isCorrect: resp.isCorrect, responseTime: resp.responseTime });
    counted.set(key, a);
  };

  const predictive = () => checkPredictiveMastery(new Set(counted.keys()), factMatrix, counted, null, predictiveParams);
  const masteryResult = (r) => ({
    status: 'predictive-mastery',
    decision: 'offer-continue-or-stop',
    coverage: r.coverage,
    hardFraction: r.hardFraction,
    sampled: counted.size,
    total: factMatrix.size,
    presented,
    glitches: glitches.length,
  });

  function maybeConclude() {
    if (!truncateOnMastery) return;
    const r = predictive();
    if (r.passes) conclusion = masteryResult(r);
  }

  // Returns the next fact key to present, or null when concluded/exhausted.
  function next() {
    if (conclusion) return null;
    let item = null, isRecheck = false;
    const dueIdx = redeliver.findIndex((r) => r.dueAt <= presented);
    if (dueIdx !== -1) { item = redeliver.splice(dueIdx, 1)[0].item; isRecheck = true; }
    else if (pos < items.length) { item = items[pos++]; }
    else if (redeliver.length > 0) { item = redeliver.shift().item; isRecheck = true; } // flush rechecks
    else return null;
    presented++;
    lastPresented = { item, isRecheck };
    currentItemRef = item;
    return item.key;
  }

  // Record the learner's response to the most recently presented fact.
  // opts.noRecheck: count a slow/wrong answer immediately as a confirmed weakness
  // instead of auto-scheduling a glitch re-ask (the UI's correction flow controls
  // re-asks manually via insert()).
  function record(key, resp, opts = {}) {
    if (conclusion) return;
    recorded++;
    const isRecheck = !!(lastPresented && lastPresented.item.key === key && lastPresented.isRecheck);
    const item = lastPresented ? lastPresented.item : { key };
    lastPresented = null;

    if (recorded <= warmupDiscard) { warmupCount++; return; } // warm-up: not judged
    const all = allResponses.get(key) || []; all.push({ isCorrect: resp.isCorrect, responseTime: resp.responseTime }); allResponses.set(key, all);

    const fast = isFast(resp);
    if (isRecheck) {
      pending.delete(key);
      if (fast) glitches.push(key);             // earlier slip confirmed non-representative
      else confirmedWeak.add(key);              // confirmed real weakness
      pushCounted(key, resp);
    } else if (fast) {
      pushCounted(key, resp);
    } else if (opts.noRecheck) {
      confirmedWeak.add(key);                   // UI correction flow: count it now, no auto re-ask
      pushCounted(key, resp);
    } else if (!autoRedeliver) {
      pushCounted(key, resp);                   // fixed list: count the (slow) attempt, never auto re-ask
    } else {
      pending.set(key, resp);                   // hold deviation, re-ask later (spaced) to check for a glitch
      redeliver.push({ item, dueAt: presented + redeliverSpacing });
    }
    maybeConclude();
  }

  // Re-ask the current fact `gap` problems from now (or flushed at the end). Used by
  // the UI's "Continue & insert"; reuses the same redeliver queue as glitch re-asks.
  function insert(gap = 5) { insertItem(currentItemRef, gap); }
  // Re-ask a SPECIFIC fact (not necessarily the current one) — used by "Flag previous &
  // insert", which re-inserts the previously-answered fact while a newer one is on screen.
  function insertItem(item, gap = 5) {
    if (item) redeliver.push({ item, dueAt: presented + gap });
  }

  // Realism guardrail: trips when too many EASY facts are coming back slow/wrong.
  function anomaly() {
    if (!anomalyEasyThreshold) return null;
    const facts = findSlowEasyFacts(allResponses, factMatrix, fastMs);
    return facts.length >= anomalyEasyThreshold ? { type: 'slow-on-easy', facts } : null;
  }

  function stats() {
    return {
      presented, recorded, warmup: warmupCount,
      countedFacts: counted.size, pending: pending.size,
      glitches: glitches.length, confirmedWeak: confirmedWeak.size,
      slowEasy: findSlowEasyFacts(allResponses, factMatrix, fastMs).length,
    };
  }

  // Facts not yet in the judgment set — the "continue to 100% coverage" remainder.
  function remaining() {
    return [...factMatrix.keys()].filter((k) => !counted.has(k));
  }

  // Reorder the not-yet-presented base items by rankFn (lower first). Used to
  // switch a hard-first run to easy-first mid-stream (auto-revert).
  function reorderRemaining(rankFn) {
    const tail = items.slice(pos);
    tail.sort((a, b) => rankFn(a) - rankFn(b));
    items.splice(pos, tail.length, ...tail);
  }

  // Final outcome. Computes predictive mastery here too, so a full curated run
  // (truncateOnMastery=false) still concludes "fluent" at the end when earned.
  function result() {
    if (conclusion) return conclusion;
    const r = predictive();
    if (r.passes) return masteryResult(r);
    for (const key of pending.keys()) confirmedWeak.add(key); // unresolved holds count as weak
    return {
      status: confirmedWeak.size > 0 ? 'weak-facts-found' : 'incomplete',
      decision: 'continue-assessing-or-practice',
      confirmedWeak: [...confirmedWeak],
      coverage: counted.size / factMatrix.size,
      sampled: counted.size,
      total: factMatrix.size,
      presented,
      glitches: glitches.length,
    };
  }

  const currentItem = () => currentItemRef;
  return { sequence: items, next, record, insert, insertItem, stats, remaining, reorderRemaining, result, currentItem, anomaly, isConcluded: () => !!conclusion };
}

// Continue-to-100% / certification pass, WITH glitch tolerance. A fact is "clean"
// once it has a correct attempt within fastMs. Facts that aren't clean yet (never
// tested, or only slow/wrong so far) are re-asked; a slow/wrong answer is
// re-queued up to maxRetries more times — a momentary slip (e.g. switching
// keyboard/mouse) gets another clean shot — before the fact is reported as
// needing work. This is what makes "Continue to 100%" robust to input glitches.
export function createThoroughRun(factMatrix, options = {}) {
  const { fastMs = 2000, priorAttempts = new Map(), maxRetries = 2 } = options;
  const attempts = new Map();
  for (const [k, list] of priorAttempts) attempts.set(k, [...list]);
  const isClean = (k) => (attempts.get(k) || []).some((a) => a.isCorrect && a.responseTime <= fastMs);

  const queue = [];
  for (const [key] of factMatrix) if (!isClean(key)) queue.push(key);
  const retries = new Map();
  const needsWork = new Set();
  let current = null;

  function next() {
    while (queue.length) { const k = queue.shift(); if (!isClean(k)) { current = k; return k; } }
    current = null;
    return null;
  }
  function record(key, resp) {
    const list = attempts.get(key) || [];
    list.push({ isCorrect: resp.isCorrect, responseTime: resp.responseTime });
    attempts.set(key, list);
    if (isClean(key)) { needsWork.delete(key); return; }
    const r = retries.get(key) || 0;
    if (r < maxRetries) { retries.set(key, r + 1); queue.push(key); } // momentary slip — try once more
    else needsWork.add(key);                                          // genuinely correct-but-slow
  }
  function result() {
    const bestMs = (k) => {
      const c = (attempts.get(k) || []).filter((a) => a.isCorrect).map((a) => a.responseTime);
      return c.length ? Math.min(...c) : null;
    };
    return {
      passes: needsWork.size === 0,
      needsWork: [...needsWork].map((k) => ({ key: k, bestMs: bestMs(k) })),
      certified: [...factMatrix.keys()].filter(isClean).length,
      total: factMatrix.size,
    };
  }
  return { next, record, result, current: () => current };
}

