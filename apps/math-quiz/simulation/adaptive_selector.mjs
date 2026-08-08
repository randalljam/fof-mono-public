// DOM-free adaptive problem selector for math quiz.
// Implements tiered selection: repair > consolidate > introduce > confirm
// with hard-fact weighting (max(num1,num2) >= 6 = hard).
// All randomness is seeded for deterministic tests.

export function hashSeed(str) {
  let h = 0;
  for (const c of str) h = (Math.imul(31, h) + c.charCodeAt(0)) | 0;
  return h >>> 0;
}

export function makeRng(seed) {
  let s = typeof seed === 'string' ? hashSeed(seed) : (seed >>> 0);
  return function () {
    s = (s + 0x6D2B79F5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = t + Math.imul(t ^ (t >>> 7), 61 | t) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function sampleLognormal(rng, median, sigma) {
  const mu = Math.log(median);
  const u1 = Math.max(rng(), 1e-10);
  const u2 = rng();
  const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
  return Math.min(Math.max(Math.round(Math.exp(mu + sigma * z)), 200), 30000);
}

export function isHardFact(num1, num2) {
  return Math.max(num1, num2) >= 6;
}

// Build canonical fact matrix. Returns Map<key, {num1,num2,operation,isHard,problemText}>.
// Commutative ops (+,*) use min|max canonical ordering.
// Subtraction restricted to num1 >= num2 (non-negative results).
export function buildFactMatrix(operations, numberRange = [0, 9]) {
  const [lo, hi] = numberRange;
  const facts = new Map();
  for (const op of operations) {
    for (let a = lo; a <= hi; a++) {
      for (let b = lo; b <= hi; b++) {
        if (op === '-' && a < b) continue;
        let n1 = a, n2 = b;
        if (op === '+' || op === '*') { n1 = Math.min(a, b); n2 = Math.max(a, b); }
        const key = `${op}|${n1}|${n2}`;
        if (!facts.has(key)) {
          facts.set(key, { num1: n1, num2: n2, operation: op, isHard: isHardFact(n1, n2), problemText: `${n1} ${op} ${n2}` });
        }
      }
    }
  }
  return facts;
}

// sessionState: { newFactsIntroduced, maxNewFacts, recentMissAt: Map<key,problemIndex>, problemIndex }
// perFactStatus: Map<key, 'nodata'|'gray'|'red'|'yellow'|'green'|'blue'>
// config: { hardWeight=3, rng }
export function selectNextFact(factMatrix, perFactStatus, sessionState, config) {
  const { hardWeight = 3, rng } = config;
  const { recentMissAt = new Map(), problemIndex = 0, newFactsIntroduced = 0, maxNewFacts = Infinity } = sessionState;

  const tiers = { repair: [], consolidate: [], introduce: [], confirm: [] };
  const capHit = newFactsIntroduced >= maxNewFacts;

  for (const [key, fact] of factMatrix) {
    const lastMiss = recentMissAt.get(key);
    if (lastMiss !== undefined && problemIndex - lastMiss < 3) continue; // spacing

    const status = perFactStatus.get(key) || 'nodata';
    const w = fact.isHard ? hardWeight : 1;

    if (status === 'nodata') {
      if (!capHit) { tiers.introduce.push({ item: key, weight: w }); }
      else { tiers.confirm.push({ item: key, weight: w * 0.1 }); } // very low priority
    } else if (status === 'red' || status === 'gray') {
      tiers.repair.push({ item: key, weight: w });
    } else if (status === 'yellow') {
      tiers.consolidate.push({ item: key, weight: w });
    } else {
      tiers.confirm.push({ item: key, weight: w * 0.3 });
    }
  }

  for (const tier of ['repair', 'consolidate', 'introduce', 'confirm']) {
    if (tiers[tier].length > 0) return weightedChoice(rng, tiers[tier]);
  }
  const all = [...factMatrix.keys()];
  return all[Math.floor(rng() * all.length)];
}

function weightedChoice(rng, candidates) {
  const total = candidates.reduce((s, c) => s + c.weight, 0);
  let r = rng() * total;
  for (const c of candidates) { r -= c.weight; if (r <= 0) return c.item; }
  return candidates[candidates.length - 1].item;
}

// Check predictive mastery.
// hardCoverageMode: 'fraction-sampled' (default) = hard_sampled/total_sampled
export function checkPredictiveMastery(sampledFacts, factMatrix, perFactAttempts, fluencyFns, params = {}) {
  const { predictive_min_coverage = 0.5, predictive_hard_min_coverage = 0.8, minAccuracy = 0.8 } = params;
  const total = factMatrix.size;
  const sampled = sampledFacts.size;
  const coverage = sampled / total;
  if (coverage < predictive_min_coverage) return { passes: false, reason: `coverage ${coverage.toFixed(2)} < ${predictive_min_coverage}` };

  let hardSampled = 0;
  for (const key of sampledFacts) {
    const fact = factMatrix.get(key);
    if (fact && fact.isHard) hardSampled++;
  }
  const hardFraction = sampled > 0 ? hardSampled / sampled : 0;
  if (hardFraction < predictive_hard_min_coverage) return { passes: false, reason: `hard fraction ${hardFraction.toFixed(2)} < ${predictive_hard_min_coverage}` };

  // Use aggregate accuracy across all sampled attempts (not per-fact status, which is too noisy)
  let totalAttempts = 0, totalCorrect = 0, totalFastCorrect = 0;
  const greenMs = 2000;
  for (const key of sampledFacts) {
    const attempts = perFactAttempts.get(key) || [];
    for (const a of attempts) {
      totalAttempts++;
      if (a.isCorrect) { totalCorrect++; if (a.responseTime <= greenMs) totalFastCorrect++; }
    }
  }
  const overallAccuracy = totalAttempts > 0 ? totalCorrect / totalAttempts : 0;
  if (overallAccuracy < minAccuracy) return { passes: false, reason: `overall accuracy ${overallAccuracy.toFixed(2)} < ${minAccuracy}` };
  const fastFraction = totalAttempts > 0 ? totalFastCorrect / totalAttempts : 0;
  if (fastFraction < minAccuracy) return { passes: false, reason: `fast-correct fraction ${fastFraction.toFixed(2)} < ${minAccuracy}` };
  return { passes: true, coverage, hardFraction };
}

export function checkThoroughMastery(factMatrix, perFactAttempts, masteryMs = 2000) {
  for (const [key] of factMatrix) {
    const attempts = perFactAttempts.get(key) || [];
    if (attempts.length === 0) return { passes: false, reason: `fact ${key} never attempted` };
    const { status } = { status: attempts.some(a => a.isCorrect && a.responseTime <= masteryMs) ? 'ok' : 'fail' };
    if (status !== 'ok') return { passes: false, reason: `fact ${key} never answered correctly within ${masteryMs}ms` };
  }
  return { passes: true };
}
