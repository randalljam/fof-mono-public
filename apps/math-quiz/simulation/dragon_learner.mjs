// Simulated learner for the dragon-game full-playthrough apparatus.
//
// Groups the 55 addition facts into three difficulty tiers built from the real
// segmentation categories (engine/addition_segmentation.mjs):
//   easy   = add-zero + add-one   (19 facts — near-fluent from the start)
//   medium = add-two + doubles    (15 facts — accurate but slow at first)
//   hard   = tough-21             (21 facts — slow and error-prone at first)
//
// The learner gets FASTER with exposure: each time it answers a fact, that
// fact's median response time shrinks by `ratePerExposure` (default 10%) and
// its accuracy climbs by `accuracyGainPerExposure`, until floors/ceilings.
// Because tier baselines are staggered (easy already under the 2000 ms green
// threshold, medium ~3400 ms, hard ~6200 ms), one shared rate makes the tiers
// cross into fluency in order easy -> medium -> hard, which is the desired
// "masters the easy categories first" progression.
//
// All randomness is seeded (deterministic runs). DOM-free; shared verbatim by
// the headless playthrough harness and the Playwright browser driver.
import { makeRng, sampleLognormal } from './adaptive_selector.mjs';
import { categorizeAddition } from '../engine/addition_segmentation.mjs';

export const TIER_OF_CATEGORY = {
  'add-zero': 'easy',
  'add-one': 'easy',
  'add-two': 'medium',
  doubles: 'medium',
  'tough-21': 'hard',
};
export const TIERS = ['easy', 'medium', 'hard'];
// Starting per-tier behavior (before any in-game exposure). RT medians straddle
// the app thresholds (greenMs 2000 / redMs 4000) so the seed file starts with
// easy green, medium yellow, hard red/gray under the real fluency rubric.
export const DEFAULT_TIER_START = {
  easy: { medianMs: 1500, accuracy: 0.96 },
  medium: { medianMs: 3400, accuracy: 0.82 },
  hard: { medianMs: 6200, accuracy: 0.62 },
};
export const DEFAULT_LEARNER_PARAMS = {
  ratePerExposure: 0.10,          // "gets X% faster" per exposure to a fact
  accuracyGainPerExposure: 0.05,
  floorMs: 950,                   // fastest plausible kid recall
  maxAccuracy: 0.98,
  sigma: 0.16,                    // lognormal RT spread
};

export function parseAdditionProblem(problemText) {
  const m = String(problemText).match(/(-?\d+)\s*\+\s*(-?\d+)/);
  if (!m) return null;
  const num1 = Number(m[1]);
  const num2 = Number(m[2]);
  const lo = Math.min(num1, num2);
  const hi = Math.max(num1, num2);
  return { num1, num2, key: `+|${lo}|${hi}`, category: categorizeAddition(num1, num2) };
}
export function tierForProblem(problemText) {
  const parsed = parseAdditionProblem(problemText);
  return parsed ? TIER_OF_CATEGORY[parsed.category] : null;
}

// createSimLearner({ seed, ratePerExposure, accuracyGainPerExposure, floorMs,
//                    maxAccuracy, sigma, tierStart })
// -> { answer(problemText), peek(problemText), exposuresOf(key), snapshot(), params }
export function createSimLearner(options = {}) {
  const params = Object.assign({}, DEFAULT_LEARNER_PARAMS, options);
  const tierStart = Object.assign({}, DEFAULT_TIER_START, options.tierStart || {});
  const rng = makeRng(options.seed || 'dragon-sim-learner');
  const exposures = new Map();   // canonical fact key -> attempt count so far

  function factState(problemText) {
    const parsed = parseAdditionProblem(problemText);
    if (!parsed) throw new Error(`Not an addition problem: ${problemText}`);
    const tier = TIER_OF_CATEGORY[parsed.category];
    const start = tierStart[tier];
    const n = exposures.get(parsed.key) || 0;
    const medianMs = Math.max(params.floorMs, start.medianMs * Math.pow(1 - params.ratePerExposure, n));
    const accuracy = Math.min(params.maxAccuracy, start.accuracy + params.accuracyGainPerExposure * n);
    return { parsed, tier, exposure: n, medianMs, accuracy };
  }
  // Deterministic center (no sampling) — for tests/reporting.
  function peek(problemText) {
    const { parsed, tier, exposure, medianMs, accuracy } = factState(problemText);
    return { key: parsed.key, category: parsed.category, tier, exposure, medianMs, accuracy };
  }
  function answer(problemText) {
    const { parsed, tier, exposure, medianMs, accuracy } = factState(problemText);
    const correctAnswer = parsed.num1 + parsed.num2;
    const isCorrect = rng() < accuracy;
    let userAnswer = correctAnswer;
    if (!isCorrect) {
      // Realistic near-miss: off by one (or two), never negative.
      const delta = rng() < 0.75 ? 1 : 2;
      userAnswer = correctAnswer + (rng() < 0.5 && correctAnswer - delta >= 0 ? -delta : delta);
    }
    const rtMs = sampleLognormal(rng, medianMs, params.sigma);
    exposures.set(parsed.key, exposure + 1);
    return {
      problemText,
      key: parsed.key,
      category: parsed.category,
      tier,
      exposure,
      correctAnswer,
      userAnswer,
      userAnswerString: String(userAnswer),
      isCorrect,
      rtMs,
    };
  }
  function exposuresOf(key) { return exposures.get(key) || 0; }
  // Per-tier progress summary for logging/reports.
  function snapshot() {
    const byTier = {};
    for (const t of TIERS) byTier[t] = { facts: 0, exposures: 0, minMedianMs: null, maxMedianMs: null };
    for (const [key, n] of exposures) {
      const [, lo, hi] = key.split('|');
      const category = categorizeAddition(Number(lo), Number(hi));
      const tier = TIER_OF_CATEGORY[category];
      const start = tierStart[tier];
      const medianMs = Math.max(params.floorMs, start.medianMs * Math.pow(1 - params.ratePerExposure, n));
      const s = byTier[tier];
      s.facts += 1;
      s.exposures += n;
      s.minMedianMs = s.minMedianMs === null ? medianMs : Math.min(s.minMedianMs, medianMs);
      s.maxMedianMs = s.maxMedianMs === null ? medianMs : Math.max(s.maxMedianMs, medianMs);
    }
    return byTier;
  }
  return { answer, peek, exposuresOf, snapshot, params, tierStart };
}
