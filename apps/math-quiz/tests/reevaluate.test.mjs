// Re-processing tests: load raw attempts from a captured DB and re-run the
// evaluation. Includes the "level 2" workflow the design calls for — edit a
// recorded response time and confirm the re-processed verdict behaves correctly.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createAppContext } from './load_app.mjs';
import { buildFactMatrix } from '../simulation/adaptive_selector.mjs';
import { loadRawAttempts, loadOrderedProblems, canonicalKey, stripEvaluation } from '../engine/db_io.mjs';
import { reevaluateState } from '../engine/reevaluate.mjs';

let SQL = null;
try {
  const { readFileSync } = await import('node:fs');
  const initSqlJs = (await import('sql.js')).default;
  const wasmBinary = readFileSync(new URL('./node_modules/sql.js/dist/sql-wasm.wasm', import.meta.url));
  SQL = await initSqlJs({ wasmBinary });
} catch { /* sql.js absent */ }
const dbTest = (name, fn) => test(name, { skip: SQL ? false : 'sql.js not installed' }, fn);

function makeFluencyFns() {
  const ctx = createAppContext(['math_utils.js', 'fluency_core.js']);
  return { evaluateFluencyStatus: (attempts) => ctx.__evalJson(`evaluateFluencyStatus(${JSON.stringify(attempts)})`) };
}
const fns = makeFluencyFns();
const ADD = buildFactMatrix(['+'], [0, 9]);
const allFast = () => { const m = new Map(); for (const [k] of ADD) m.set(k, [{ isCorrect: true, responseTime: 1200 }]); return m; };

test('static re-evaluation: a fully fast/correct run reads as fluent + certifiable', () => {
  const r = reevaluateState(ADD, allFast(), fns);
  assert.equal(r.predictive.passes, true);
  assert.equal(r.thoroughStatic.passes, true);
  assert.equal(r.perFactStatus.get('+|8|9'), 'green');
});

test('editing a recorded time to >2s changes the STATIC verdict (re-evaluation reflects the edit)', () => {
  const attempts = allFast();
  attempts.set('+|0|2', [{ isCorrect: true, responseTime: 2100 }]); // edit one recorded time
  const r = reevaluateState(ADD, attempts, fns);
  assert.equal(r.thoroughStatic.passes, false);                      // re-evaluation picks up the change
  assert.deepEqual(r.thoroughStatic.needsWork, ['+|0|2']);
  assert.equal(r.predictive.passes, true, 'predictive is robust to one slow fact');
});

test('static re-evaluation flags the slow-on-easy anomaly (guardrail visible to evaluators)', () => {
  const attempts = allFast();
  for (const k of ['+|0|2', '+|1|3', '+|2|4']) attempts.set(k, [{ isCorrect: true, responseTime: 4000 }]); // 3 easy facts slow
  const r = reevaluateState(ADD, attempts, fns);
  assert.ok(r.anomaly && r.anomaly.type === 'slow-on-easy');
  assert.equal(r.anomaly.facts.length, 3);
});

dbTest('loadRawAttempts reads recorded trials from a real captured DB; re-eval matches', () => {
  const ctx = createAppContext(['math_utils.js']);
  const db = new SQL.Database();
  ctx.__get('createTables')(db);
  const probs = [['2 + 3', 5, 1200], ['9 + 8', 17, 1400], ['9 + 8', 17, 1500]].map(([text, ans, ms], i) => ({
    id: `p${i}`, problem_text: text, correct_answer: ans, user_answer_string: String(ans), user_answer: ans,
    is_correct: true, response_time_ms: ms, flags: [],
  }));
  const session = {
    version: '1.1', user: { name: 'Cap' },
    session: { id: 's1', start_time: '2026-06-15_080000', end_time: '2026-06-15_080200',
      settings: { num_problems: probs.length, number_range: [0, 9], numbers_include: [], numbers_exclude: [], num_numbers: 2, operations: ['+'] },
      summary: { total_problems: probs.length, correct_answers: probs.length, average_response_time_ms: 1366 }, problems: probs },
  };
  ctx.__get('importSessionData')(db, session, 's1.json');

  const attempts = loadRawAttempts(db);
  assert.deepEqual([...attempts.keys()].sort(), ['+|2|3', '+|8|9']);
  assert.equal(attempts.get('+|8|9').length, 2);             // both 9+8 trials grouped under canonical key
  assert.equal(attempts.get('+|2|3')[0].responseTime, 1200);

  // raw problems are available exactly as administered, in order
  const ordered = loadOrderedProblems(db);
  assert.deepEqual(ordered.map((p) => p.key), ['+|2|3', '+|8|9', '+|8|9']);
  assert.deepEqual(ordered.map((p) => p.responseTime), [1200, 1400, 1500]);

  // raw-only guarantee: stripEvaluation leaves the core raw tables intact
  stripEvaluation(db);
  for (const t of ['Users', 'Sessions', 'ProblemAttempts']) {
    const c = db.exec(`SELECT count(*) FROM sqlite_master WHERE type='table' AND name='${t}'`)[0].values[0][0];
    assert.equal(c, 1, `${t} retained`);
  }
  assert.equal(canonicalKey('+', 9, 8), '+|8|9');
});
