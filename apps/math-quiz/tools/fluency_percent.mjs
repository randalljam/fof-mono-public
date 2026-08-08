#!/usr/bin/env node
/**
 * Print overall fluency % for a learner from a math-quiz .sqlite file.
 * Uses fluency_core.js fluencyPercent — the same full-universe metric as the
 * anchor end-of-quiz readout, the kid "Fluency feast" generator, the analysis
 * page's "Current fluency percentage", and the fluency-tracker cards.
 * Visual-practice sessions are included (same rule as every other fluency feed).
 *
 * Usage:
 *   node tools/fluency_percent.mjs <db.sqlite> <user> [--op +] [--range 0-9] [--json]
 *
 * Example:
 *   node tools/fluency_percent.mjs _data/tlkids/math-flu_K1_2026-06-17.sqlite Kid1
 */
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createAppContext } from '../tests/load_app.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const appDir = path.dirname(__dirname);
const testsDir = path.join(appDir, 'tests');
const require = createRequire(path.join(testsDir, 'package.json'));

function usage() {
  console.error('Usage: node tools/fluency_percent.mjs <db.sqlite> <user> [--op +] [--range 0-9] [--json]');
  process.exit(2);
}

function parseArgs(argv) {
  if (argv.length < 2) usage();
  const dbPath = path.resolve(argv[0]);
  const user = argv[1];
  let op = '+';
  let range = [0, 9];
  let json = false;
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--json') json = true;
    else if (a === '--op' && argv[i + 1]) op = argv[++i];
    else if (a === '--range' && argv[i + 1]) {
      const m = /^(\d+)-(\d+)$/.exec(argv[++i]);
      if (!m) usage();
      range = [Number(m[1]), Number(m[2])];
    } else usage();
  }
  return { dbPath, user, op, range, json };
}

function loadThresholds(db, defaultFluencyThresholds, user) {
  try {
    const stmt = db.prepare(
      'SELECT green_ms, red_ms, window_size, min_accuracy FROM Profile WHERE user_name = ?'
    );
    stmt.bind([user]);
    if (!stmt.step()) {
      stmt.free();
      return defaultFluencyThresholds;
    }
    const row = stmt.get();
    stmt.free();
    const [greenMs, redMs, windowSize, minAccuracy] = row;
    return { ...defaultFluencyThresholds, greenMs, redMs, windowSize, minAccuracy };
  } catch {
    return defaultFluencyThresholds;
  }
}

function loadAttempts(db, user, sessionTypeExclusionSql) {
  const exclusion = typeof sessionTypeExclusionSql === 'function'
    ? sessionTypeExclusionSql(db, 's')
    : '';
  const stmt = db.prepare(`
    SELECT pa.problem_text, pa.is_correct, pa.response_time_ms, pa.flags_json,
           s.start_time, pa.attempt_id, pa.session_id
    FROM ProblemAttempts pa
    INNER JOIN Sessions s ON s.session_id = pa.session_id
    WHERE s.user_name = ?${exclusion}
    ORDER BY s.start_time, pa.attempt_id
  `);
  stmt.bind([user]);
  const attempts = [];
  while (stmt.step()) {
    const v = stmt.get();
    attempts.push({
      problem_text: v[0],
      is_correct: v[1],
      response_time_ms: v[2],
      flags_json: v[3],
      start_time: v[4],
      attempt_id: v[5],
      session_id: v[6],
    });
  }
  stmt.free();
  return attempts;
}

async function main() {
  const { dbPath, user, op, range, json } = parseArgs(process.argv.slice(2));
  const ctx = createAppContext(['math_utils.js', 'fluency_core.js']);
  const fluencyPercent = ctx.__get('fluencyPercent');
  const classifyFactsByStatus = ctx.__get('classifyFactsByStatus');
  const defaultFluencyThresholds = ctx.__get('defaultFluencyThresholds');
  const attemptHasFlags = ctx.__get('attemptHasFlags');
  const enumerateFactUniverse = ctx.__get('enumerateFactUniverse');
  const sessionTypeExclusionSql = ctx.__get('sessionTypeExclusionSql');

  const initSqlJs = require('sql.js');
  const wasmBinary = readFileSync(require.resolve('sql.js/dist/sql-wasm.wasm'));
  const SQL = await initSqlJs({ wasmBinary });
  const db = new SQL.Database(readFileSync(dbPath));

  const attempts = loadAttempts(db, user, sessionTypeExclusionSql);
  const thresholds = loadThresholds(db, defaultFluencyThresholds, user);
  const options = { numberRange: range, operations: [op], excludeFlagged: true };
  const pct = fluencyPercent(attempts, thresholds, options);

  const selected = attempts.filter((a) => !attemptHasFlags(a));
  const observed = classifyFactsByStatus(selected, thresholds, { numberRange: range });
  const breakdown = { green: 0, yellow: 0, red: 0, gray: 0, blue: 0, nodata: 0 };
  for (const key of enumerateFactUniverse(range, [op])) {
    const st = (observed[key] && observed[key].status) || 'nodata';
    breakdown[st] = (breakdown[st] || 0) + 1;
  }
  const fluent = (breakdown.green || 0) + (breakdown.blue || 0);
  const universe = enumerateFactUniverse(range, [op]).length;
  const out = {
    user,
    file: path.basename(dbPath),
    operation: op,
    numberRange: range,
    fluencyPercent: pct,
    fluent,
    universe,
    attempts: attempts.length,
    breakdown,
    thresholds: {
      greenMs: thresholds.greenMs,
      redMs: thresholds.redMs,
      windowSize: thresholds.windowSize,
      minAccuracy: thresholds.minAccuracy,
    },
  };

  if (json) {
    console.log(JSON.stringify(out, null, 2));
    return;
  }
  console.log(`${user}: ${pct}% fluent (${fluent}/${universe} facts, op ${op}, range ${range[0]}–${range[1]})`);
  console.log(`  ${breakdown.green} fluent · ${breakdown.yellow} almost · ${breakdown.red} needs practice · ${breakdown.gray} incorrect · ${breakdown.nodata} no data`);
  console.log(`  ${attempts.length} attempts in ${path.basename(dbPath)}`);
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
