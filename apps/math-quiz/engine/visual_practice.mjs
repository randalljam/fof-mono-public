// Visual practice - DOM-free strategy-supported retrieval engine.
//
// Drives a practice SESSION focused on 1-5 coach-chosen TARGET problems plus
// known-fact FILLER problems. Targets are worked SERIALLY, one at a time, in
// order. Each target starts with a cold probe; a teach visual is shown only by
// the UI, which reports that event via teachShown(). The engine then schedules
// delayed retrieval attempts spaced behind shuffled filler facts. Fast-correct
// retrieval successes are cumulative and are never lost; a target clears only
// when the required successes have been earned on a retrieval attempt. The
// legacy 'immediate-retrieval' role remains valid for old persisted data, but
// this engine no longer emits it. Consumed by the anchor page (DOM) and by tests
// via dependency injection, like
// engine/targeted_practice.mjs.
//
// History (newest first):
//   2026-07-25 - end right on the final clear (closing filler removed — it read
//                as "kept going" in live use); default filler gap 1-3.
//   2026-07-25 - initial visual-practice engine for strategy-supported,
//                spaced retrieval with teachShown() and closing-filler support.
import { makeRng, isHardFact } from '../simulation/adaptive_selector.mjs';
import { canonicalKey, expandOrientations } from './targeted_practice.mjs';

function factFromKey(key, factMatrix) {
  const f = factMatrix && factMatrix.get(key);
  if (f) {
    return {
      key,
      num1: f.num1,
      num2: f.num2,
      operation: f.operation,
      isHard: f.isHard ?? isHardFact(f.num1, f.num2),
    };
  }
  const [operation, a, b] = String(key).split('|');
  const num1 = parseInt(a, 10);
  const num2 = parseInt(b, 10);
  if (!operation || Number.isNaN(num1) || Number.isNaN(num2)) {
    throw new Error(`invalid canonical fact key: ${key}`);
  }
  return { key, num1, num2, operation, isHard: isHardFact(num1, num2) };
}

function targetFromInput(t, factMatrix) {
  if (typeof t === 'string') return factFromKey(t, factMatrix);
  const key = t.key || canonicalKey(t.num1, t.num2, t.operation);
  return { key, num1: t.num1, num2: t.num2, operation: t.operation, isHard: isHardFact(t.num1, t.num2) };
}

function fillerFromInput(f, factMatrix) {
  if (typeof f === 'string') {
    const item = factFromKey(f, factMatrix);
    return { key: item.key, num1: item.num1, num2: item.num2, operation: item.operation };
  }
  return { key: canonicalKey(f.num1, f.num2, f.operation), num1: f.num1, num2: f.num2, operation: f.operation };
}

function shuffleWith(rng, arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function normalizedGapBounds(min, max) {
  const minNum = Number(min);
  const maxNum = Number(max);
  const lo = Math.max(0, Math.floor(Number.isFinite(minNum) ? minNum : 0));
  const hi = Math.max(lo, Math.floor(Number.isFinite(maxNum) ? maxNum : lo));
  return [lo, hi];
}

// Create a visual-practice run controller (serial, streaming).
//
// options:
//   targets           - parsed target specs ({num1,num2,operation[,key]}) or
//                       canonical key strings. 1-5, worked in order. Required.
//   factMatrix        - fact matrix (buildFactMatrix). Key expansion helper.
//   fillerFacts       - known filler pool: display problems or canonical keys.
//                       Display-problem orientation is preserved; targets are
//                       never filler. With no filler list, target spacing is 0.
//   fastMs            - "fast" ceiling; <= this AND correct earns a success.
//   retrievalsToClear - cumulative fast-correct successes required to clear.
//   fillerGapMin/Max  - random filler count between target trials.
//   rng               - seeded RNG (default seeded).
export function createVisualRun(options = {}) {
  const {
    targets: rawTargets = [],
    factMatrix = null,
    fillerFacts = null,
    fastMs = 2000,
    retrievalsToClear = 2,
    fillerGapMin = 1,
    fillerGapMax = 3,
    rng = makeRng('visual-practice'),
  } = options;

  const targets = [];
  const seenTargets = new Set();
  for (const raw of rawTargets) {
    const t = targetFromInput(raw, factMatrix);
    if (seenTargets.has(t.key)) continue;
    seenTargets.add(t.key);
    targets.push(t);
  }
  if (targets.length === 0) throw new Error('createVisualRun requires at least one target');
  if (targets.length > 5) throw new Error('createVisualRun accepts at most five targets');

  const clearGoal = Math.max(1, Math.floor(retrievalsToClear));
  const [gapMin, gapMax] = normalizedGapBounds(fillerGapMin, fillerGapMax);
  const targetKeys = targets.map((t) => t.key);
  const targetByKey = new Map(targets.map((t) => [t.key, t]));
  const stateByKey = new Map(targets.map((t) => [t.key, {
    key: t.key,
    presentations: 0,
    attempts: 0,
    successes: 0,
    lastSuccessRole: null,
    coldProbe: null,
    teachCount: 0,
    cleared: false,
  }]));

  // Filler pool of display items {key,num1,num2,operation}, excluding any whose
  // canonical key matches a target (a target is never filler).
  const fillerPool = (fillerFacts || [])
    .map((f) => fillerFromInput(f, factMatrix))
    .filter((f) => !targetByKey.has(f.key));

  // Filler "deck": shuffled copy of the pool, reshuffled only when exhausted.
  let deck = shuffleWith(rng, fillerPool);
  let deckIdx = 0;
  const drawFiller = () => {
    if (fillerPool.length === 0) return null;
    if (deckIdx >= deck.length) { deck = shuffleWith(rng, fillerPool); deckIdx = 0; }
    return { ...deck[deckIdx++], role: 'filler', targetKey: null };
  };
  const randomFillerGap = () => {
    if (fillerPool.length === 0) return 0;
    return gapMin + Math.floor(rng() * (gapMax - gapMin + 1));
  };

  const cleared = new Set();
  const redeliver = [];           // [{ item, dueAt }] - Flag-previous "insert" re-asks
  let orientationFlip = 0;
  let presentedCount = 0;
  let fillerRemaining = 0;

  const currentTargetKey = () => targetKeys.find((k) => !stateByKey.get(k).cleared) || null;
  function isComplete() { return cleared.size === targetKeys.length; }
  function completionReason() { return isComplete() ? 'all-cleared' : null; }

  // Display item for a target trial, alternating orientation across
  // presentations so both 3+6 and 6+3 are practiced when the fact commutes.
  const targetItem = (key, role) => {
    const t = targetByKey.get(key);
    const s = stateByKey.get(key);
    const orients = expandOrientations(t.num1, t.num2, t.operation);
    const o = orients[orientationFlip % orients.length];
    orientationFlip++;
    s.presentations++;
    return { key, num1: o.num1, num2: o.num2, operation: o.operation, role, targetKey: key };
  };

  const present = (item) => {
    if (!item) return null;
    presentedCount++;
    return item;
  };

  // The next problem to present, or null once every target has cleared — the
  // session ends right on the final clear (no trailing questions).
  function nextProblem() {
    if (isComplete()) return null;

    const nextOrdinal = presentedCount + 1;
    const dueIdx = redeliver.findIndex((r) => r.dueAt <= nextOrdinal);
    if (dueIdx !== -1) return present(redeliver.splice(dueIdx, 1)[0].item);

    if (fillerRemaining > 0) {
      const f = drawFiller();
      if (f) { fillerRemaining--; return present(f); }
      fillerRemaining = 0;
    }

    const key = currentTargetKey();
    if (!key) return null;
    const state = stateByKey.get(key);
    const role = state.presentations === 0 ? 'cold-probe' : 'delayed-retrieval';
    fillerRemaining = randomFillerGap();
    return present(targetItem(key, role));
  }

  // Re-ask a problem ~gap problems later (Flag-previous "Continue & insert").
  function requeue(item, gap = 5) {
    if (!item || !item.key) return;
    const delay = Math.max(0, Math.floor(gap));
    redeliver.push({ item: { ...item }, dueAt: presentedCount + delay });
  }

  function teachShown(targetKey) {
    const state = stateByKey.get(targetKey);
    if (!state || state.cleared) return;
    if (targetKey !== currentTargetKey()) return;
    state.teachCount++;
    fillerRemaining = fillerPool.length > 0 ? Math.max(1, randomFillerGap()) : 0;
  }

  function coldProbeResult({ fast, correct, passed }) {
    if (fast) return 'fast-correct';
    if (correct) return 'slow-correct';
    if (passed) return 'pass';
    return 'wrong';
  }

  // Record a response. Returns { needsTeach, cleared, sessionComplete } so the UI
  // can offer a teach visual and celebrate exactly when a target clears. Filler
  // responses are ignored. A pass is not correct; slow-correct earns no credit.
  function record(item, resp = {}) {
    const key = item && (item.targetKey || item.key);
    const state = key && stateByKey.get(key);
    if (!state) return { needsTeach: false, cleared: null, sessionComplete: isComplete() };

    state.attempts++;
    const passed = !!resp.passed;
    const correct = !passed && !!resp.isCorrect;
    const fast = correct && typeof resp.responseTime === 'number' && resp.responseTime <= fastMs;
    const role = item.role || (state.coldProbe == null ? 'cold-probe' : 'delayed-retrieval');
    let needsTeach = false;
    let clearedKey = null;

    if (role === 'cold-probe' && state.coldProbe == null) {
      state.coldProbe = coldProbeResult({ fast, correct, passed });
    }

    if (fast) {
      state.successes++;
      state.lastSuccessRole = role;
    } else if (passed || !correct) {
      needsTeach = true;
    }

    if (fast && !state.cleared && state.successes >= clearGoal && role !== 'immediate-retrieval') {
      state.cleared = true;
      cleared.add(key);
      clearedKey = key;
      if (isComplete()) fillerRemaining = 0;
    }

    return { needsTeach, cleared: clearedKey, sessionComplete: isComplete() };
  }

  function progress() {
    const curKey = currentTargetKey();
    const curT = curKey ? targetByKey.get(curKey) : null;
    return {
      totalTargets: targetKeys.length,
      clearedTargets: cleared.size,
      fraction: targetKeys.length ? cleared.size / targetKeys.length : 0,
      retrievalsToClear: clearGoal,
      problemsPresented: presentedCount,
      current: curT ? {
        key: curKey,
        num1: curT.num1,
        num2: curT.num2,
        operation: curT.operation,
        index: targetKeys.indexOf(curKey),
        successes: stateByKey.get(curKey).successes,
        retrievalsToClear: clearGoal,
      } : null,
      perTarget: targets.map((t) => {
        const s = stateByKey.get(t.key);
        return {
          key: t.key,
          num1: t.num1,
          num2: t.num2,
          operation: t.operation,
          successes: s.successes,
          cleared: s.cleared,
          coldProbe: s.coldProbe,
          teachCount: s.teachCount,
        };
      }),
    };
  }

  function metadata() {
    const curKey = currentTargetKey();
    return {
      mode: 'visual-practice',
      targets: targetKeys,
      targetCount: targetKeys.length,
      fastMs,
      retrievalsToClear: clearGoal,
      problemsPresented: presentedCount,
      cleared: targetKeys.filter((k) => stateByKey.get(k).cleared),
      complete: isComplete(),
      completionReason: completionReason(),
      currentTargetKey: curKey,
      perTarget: targets.map((t) => {
        const s = stateByKey.get(t.key);
        return {
          key: t.key,
          num1: t.num1,
          num2: t.num2,
          operation: t.operation,
          coldProbe: s.coldProbe,
          teachCount: s.teachCount,
          retrievalSuccesses: s.successes,
          attempts: s.attempts,
          requiredSuccesses: clearGoal,
          cleared: s.cleared,
        };
      }),
    };
  }

  return {
    targets,
    fillerPool,
    nextProblem,
    requeue,
    record,
    teachShown,
    progress,
    metadata,
    isComplete,
    completionReason,
    currentTargetKey,
  };
}
