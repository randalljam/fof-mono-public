// Deterministic "starting SQLite file" generator for the dragon playthrough
// apparatus. Simulates a baseline practice history consistent with the sim
// learner's tier baselines (easy fluent, medium partly fluent, hard weak) and
// writes a real per-person .sqlite via the REAL createTables/importSessionData,
// so the run starts at roughly 40-50% fluent — below the first in-game
// milestone (hatch at 60%) so a full playthrough crosses every milestone.
//
// CLI: node apps/math-quiz/simulation/dragon_seed.mjs --data-dir <dir>
//        [--folder playtest] [--user DragonSim] [--seed dragon-seed] [--blank]
import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { makeRng, sampleLognormal } from './adaptive_selector.mjs';
import { buildAdditionFacts } from '../engine/addition_segmentation.mjs';
import { DEFAULT_TIER_START, TIER_OF_CATEGORY } from './dragon_learner.mjs';
import { statusSnapshot } from './playthrough_report.mjs';
import { createAppContext } from '../tests/load_app.mjs';
import { loadSqlJs } from './sql_node.mjs';

// Behavior class per fact for the baseline: which facts start already fluent.
// Easy tier: all fluent. Medium tier: the small-operand half fluent, rest slow
// (yellow). Hard tier: all slow with frequent misses (red/gray).
// => green ≈ 19 (easy) + 4 (add-two hi<=5) + 2 (doubles 3+3, 4+4) = 25/55 ≈ 45%.
function baselineClassOf(fact) {
  const tier = TIER_OF_CATEGORY[fact.category];
  if (tier === 'easy') return 'fluent';
  if (tier === 'medium') {
    if (fact.category === 'add-two') return fact.hi <= 5 ? 'fluent' : 'slow';
    return fact.hi <= 4 ? 'fluent' : 'slow';   // doubles: 3+3, 4+4 fluent
  }
  return 'weak';
}
const BASELINE_MODELS = {
  fluent: { medianMs: 1400, sigma: 0.14, pCorrect: 0.97 },
  slow: { medianMs: DEFAULT_TIER_START.medium.medianMs, sigma: 0.16, pCorrect: DEFAULT_TIER_START.medium.accuracy },
  weak: { medianMs: DEFAULT_TIER_START.hard.medianMs, sigma: 0.18, pCorrect: DEFAULT_TIER_START.hard.accuracy },
};
const ATTEMPTS_PER_FACT = 3;

function stampFor(baseDate, sessionIdx) {
  return `${baseDate}_${String(9 + sessionIdx).padStart(2, '0')}0000`;
}

// Pure: baseline session JSONs (anchor-compatible shape) for the seed history.
export function buildSeedSessions({ seed = 'dragon-seed', user = 'DragonSim', baseDate = '2026-07-01' } = {}) {
  const rng = makeRng(seed);
  const facts = buildAdditionFacts();
  // One attempt per fact per session, sessions interleave all 55 facts.
  const sessions = [];
  for (let s = 0; s < ATTEMPTS_PER_FACT; s++) {
    const startTime = stampFor(baseDate, s);
    const problems = [];
    for (const fact of facts) {
      const model = BASELINE_MODELS[baselineClassOf(fact)];
      const isCorrect = rng() < model.pCorrect;
      const rt = sampleLognormal(rng, model.medianMs, model.sigma);
      const correctAnswer = fact.lo + fact.hi;
      const wrong = correctAnswer + (rng() < 0.5 && correctAnswer >= 1 ? -1 : 1);
      const ascending = rng() < 0.5;
      const [n1, n2] = ascending ? [fact.lo, fact.hi] : [fact.hi, fact.lo];
      problems.push({
        id: `${startTime}-${problems.length}`,
        fact_key: fact.key,
        problem_text: `${n1} + ${n2}`,
        correct_answer: correctAnswer,
        user_answer_string: isCorrect ? String(correctAnswer) : String(wrong),
        user_answer: isCorrect ? correctAnswer : wrong,
        is_correct: isCorrect,
        response_time_ms: rt,
        presented_at: Date.parse(`${baseDate}T09:00:00Z`) + s * 3600000 + problems.length * 8000,
        flags: [],
      });
    }
    const correct = problems.filter((p) => p.is_correct).length;
    const avg = Math.round(problems.reduce((sum, p) => sum + p.response_time_ms, 0) / problems.length);
    sessions.push({
      version: '1.1',
      user: { name: user },
      session: {
        id: `seed-${seed}-${s}`,
        start_time: startTime,
        end_time: `${baseDate}_${String(9 + s).padStart(2, '0')}2000`,
        settings: {
          preset: 'dragon-seed',
          note: 'mode:dragon-sim;seed-baseline',
          num_problems: problems.length,
          number_range: [0, 9],
          numbers_include: [],
          numbers_exclude: [],
          num_numbers: 2,
          operations: ['+'],
          source_folder: 'playtest',
          destination: 'source',
          test_description: 'simulated baseline seed',
        },
        summary: { total_problems: problems.length, correct_answers: correct, average_response_time_ms: avg },
        problems,
      },
    });
  }
  return sessions;
}

// Build the seed DB bytes + a start-state summary using the real app code.
export async function buildSeedDb({ seed, user = 'DragonSim', baseDate } = {}) {
  const SQL = await loadSqlJs();
  const ctx = createAppContext(['math_utils.js', 'fluency_core.js']);
  const createTables = ctx.__get('createTables');
  const importSessionData = ctx.__get('importSessionData');
  const fluencyPercent = ctx.__get('fluencyPercent');
  const thresholds = ctx.__evalJson('defaultFluencyThresholds');

  const sessions = buildSeedSessions({ seed, user, baseDate });
  const db = new SQL.Database();
  createTables(db);
  for (const s of sessions) importSessionData(db, s, `seed_${s.session.start_time}.sqlite`);
  const res = db.exec(
    `SELECT pa.problem_text AS problem_text, pa.is_correct AS is_correct,
            pa.response_time_ms AS response_time_ms, pa.flags_json AS flags_json
     FROM ProblemAttempts pa JOIN Sessions s ON pa.session_id = s.session_id
     WHERE s.user_name = ? ORDER BY s.start_time, pa.attempt_id`, [user]);
  const rows = res.length
    ? res[0].values.map((row) => {
      const o = {};
      res[0].columns.forEach((c, i) => { o[c] = row[i]; });
      return o;
    })
    : [];
  const startPct = fluencyPercent(rows, thresholds, { numberRange: [0, 9], operations: ['+'], excludeFlagged: true });
  const snapshot = statusSnapshot(rows, (attempts, t) => ctx.__evalJson(
    `evaluateFluencyStatus(${JSON.stringify(attempts)}, ${JSON.stringify(t)})`), thresholds);
  const bytes = db.export();
  db.close();
  return { bytes, startPct, byCategory: snapshot.byCategory, greenCount: snapshot.greenCount, sessions: sessions.length };
}

// Write the seed file into <dataDir>/<folder>/ using the multi-session naming
// (math-flu_<user>_<date>.sqlite) so the dev server Continue-appends to it.
export async function writeSeedDb({ dataDir, folder = 'playtest', user = 'DragonSim', seed, baseDate = '2026-07-01' } = {}) {
  if (!dataDir) throw new Error('writeSeedDb requires dataDir');
  const built = await buildSeedDb({ seed, user, baseDate });
  const dir = join(dataDir, folder);
  mkdirSync(dir, { recursive: true });
  const filename = `math-flu_${user}_${baseDate}.sqlite`;
  writeFileSync(join(dir, filename), Buffer.from(built.bytes));
  return { filename, path: join(dir, filename), ...built };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const args = process.argv.slice(2);
  const opt = (name, dflt) => {
    const i = args.indexOf(`--${name}`);
    return i >= 0 ? args[i + 1] : dflt;
  };
  const dataDir = opt('data-dir', null);
  if (!dataDir) { console.error('Usage: node dragon_seed.mjs --data-dir <dir> [--folder playtest] [--user DragonSim] [--seed dragon-seed]'); process.exit(1); }
  const out = await writeSeedDb({
    dataDir,
    folder: opt('folder', 'playtest'),
    user: opt('user', 'DragonSim'),
    seed: opt('seed', 'dragon-seed'),
    baseDate: opt('base-date', '2026-07-01'),
  });
  console.log(`Seed written: ${out.path}`);
  console.log(`Start fluency: ${Math.round(out.startPct)}% (${out.greenCount}/55 green) over ${out.sessions} baseline sessions`);
  for (const [cat, b] of Object.entries(out.byCategory)) {
    console.log(`  ${cat}: green ${b.green}/${b.total}, yellow ${b.yellow}, red ${b.red}, gray ${b.gray}`);
  }
}
