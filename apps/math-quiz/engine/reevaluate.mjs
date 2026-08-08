// Re-process a captured run from its raw attempts — STATIC re-evaluation only.
// A captured .sqlite holds only raw data (the problems answered, in order, with
// times/correctness). Re-processing re-runs the fluency evaluation + mastery
// checks over those exact attempts — deterministic, no responder, no re-simulation.
// This is what we want when changing the evaluation algorithm/criteria and re-running
// old captures as fixed inputs. (Live re-simulation with an inferred learner model
// is intentionally NOT done here.)
// See 2026-06-15_assess-practice-modes-spec-and-plan.md (Part C / re-processing).
import { checkPredictiveMastery } from '../simulation/adaptive_selector.mjs';
import { findSlowEasyFacts } from './assess_flow.mjs';

const DEFAULT_PREDICTIVE = { predictive_min_coverage: 0.7, predictive_hard_min_coverage: 0, minAccuracy: 0.8 };

// Static re-evaluation over the recorded attempts.
// attempts: Map<key, [{ isCorrect, responseTime }]> (per-fact, in recorded order).
export function reevaluateState(factMatrix, attempts, fluencyFns, opts = {}) {
  const { params = DEFAULT_PREDICTIVE, fastMs = 2000, anomalyEasyThreshold = 3 } = opts;

  const perFactStatus = new Map();
  for (const [key] of factMatrix) {
    perFactStatus.set(key, fluencyFns.evaluateFluencyStatus(attempts.get(key) || []).status);
  }

  const sampled = new Set([...attempts.keys()].filter((k) => factMatrix.has(k)));
  const predictive = checkPredictiveMastery(sampled, factMatrix, attempts, null, params);

  // Static thorough: each fact must already have a fast+correct attempt (no resample).
  const needsWork = [];
  for (const [key] of factMatrix) {
    const a = attempts.get(key) || [];
    const ok = a.some((x) => x.isCorrect && x.responseTime <= fastMs);
    if (!ok) needsWork.push(key);
  }
  const slowEasy = findSlowEasyFacts(attempts, factMatrix, fastMs);
  const anomaly = anomalyEasyThreshold && slowEasy.length >= anomalyEasyThreshold ? { type: 'slow-on-easy', facts: slowEasy } : null;

  return { perFactStatus, predictive, thoroughStatic: { passes: needsWork.length === 0, needsWork }, anomaly };
}
