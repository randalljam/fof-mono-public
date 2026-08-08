// Generates an app-aligned "starting" learner fluency-state file for a profile.
// A baseline diagnostic is simulated: each in-scope fact gets a few attempts sampled
// from the learner's latent skill, then scored by the REAL evaluateFluencyStatus, so
// the emitted status/accuracy/medianMs are guaranteed consistent with the app's logic.
// See learner_profiles/states/README.md for the file spec.
import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { buildFactMatrix, makeRng } from './adaptive_selector.mjs';
import { buildSkillMap, sampleResponse } from './simulation.mjs';
import { PROFILES } from './profiles.mjs';
import { createAppContext } from '../tests/load_app.mjs';

const OP_NAMES = { '+': 'addition', '-': 'subtraction', '*': 'multiplication' };

export const DEFAULT_STATE_THRESHOLDS = {
  windowSize: 5, minAccuracy: 0.8, greenMs: 2000, redMs: 4000,
  retentionSessions: 3, permanentSessions: 5,
};

function loadFluencyFns() {
  const ctx = createAppContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js']);
  return {
    evaluateFluencyStatus: (attempts) =>
      ctx.__evalJson(`evaluateFluencyStatus(${JSON.stringify(attempts)})`),
  };
}

function round(n, places = 3) {
  if (typeof n !== 'number' || !Number.isFinite(n)) return n;
  const f = 10 ** places;
  return Math.round(n * f) / f;
}

// Build the app-aligned fluency-state object for one profile's baseline.
export function generateStartState(profile, fluencyFns, opts = {}) {
  const attemptsPerFact = opts.attemptsPerFact ?? 5; // == windowSize; tolerates one slip
  const seed = opts.seed ?? `${profile.profile_id}-baseline`;
  const generatedAt = opts.generatedAt ?? '2026-06-14';
  const rng = makeRng(seed);

  const operations = profile.operations || ['+'];
  const numberRange = profile.number_range || [0, 9];
  const factMatrix = buildFactMatrix(operations, numberRange);
  const skillMap = buildSkillMap(factMatrix, profile.initial_state || { default: 'fluent' });
  const responseModel = profile.response_model || {};

  const byOp = { addition: {}, subtraction: {}, multiplication: {} };
  for (const [key, fact] of factMatrix) {
    const skill = skillMap.get(key) || 'unknown';
    const attempts = [];
    for (let i = 0; i < attemptsPerFact; i++) attempts.push(sampleResponse(rng, skill, responseModel));
    const m = fluencyFns.evaluateFluencyStatus(attempts);
    byOp[OP_NAMES[fact.operation]][key] = {
      key,
      operation: fact.operation,
      num1: fact.num1,
      num2: fact.num2,
      status: m.status,
      calculatedStatus: m.status,
      accuracy: round(m.accuracy),
      medianMs: m.medianMs,
      attemptCount: attempts.length,
      attemptsConsidered: m.attemptsConsidered,
      correctCount: m.correctCount,
      statusHistory: [m.status],
      isPermanent: false,
      needsRecheck: false,
      manualOverride: false,
    };
  }

  return {
    version: '2.0',
    schema: 'math-quiz/fluency-state',
    user: { name: profile.display_name || profile.profile_id },
    profile_id: profile.profile_id,
    source: 'baseline-snapshot',
    generated_at: generatedAt,
    seed,
    thresholds: DEFAULT_STATE_THRESHOLDS,
    addition: byOp.addition,
    subtraction: byOp.subtraction,
    multiplication: byOp.multiplication,
  };
}

// CLI: regenerate the committed example state files.
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const fns = loadFluencyFns();
  const outDir = join(dirname(fileURLToPath(import.meta.url)), '..', 'learner_profiles', 'states');
  mkdirSync(outDir, { recursive: true });
  for (const profile of PROFILES) {
    const state = generateStartState(profile, fns);
    const file = join(outDir, `${profile.profile_id}_start.json`);
    writeFileSync(file, JSON.stringify(state, null, 2) + '\n');
    const counts = {};
    for (const op of ['addition', 'subtraction', 'multiplication'])
      for (const f of Object.values(state[op])) counts[f.status] = (counts[f.status] || 0) + 1;
    console.log(`${profile.profile_id}_start.json`, counts);
  }
}
