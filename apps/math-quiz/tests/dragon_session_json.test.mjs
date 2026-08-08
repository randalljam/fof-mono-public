import test from 'node:test';
import assert from 'node:assert/strict';
import { createAppContext } from './load_app.mjs';

const ctx = createAppContext(['math_utils.js', 'fluency_core.js']);
globalThis.createTables = ctx.__get('createTables');
globalThis.importSessionData = ctx.__get('importSessionData');
globalThis.deleteSessionFromDb = ctx.__get('deleteSessionFromDb');
globalThis.parseProblemText = ctx.__get('parseProblemText');
globalThis.fluencyPercent = ctx.__get('fluencyPercent');
globalThis.defaultFluencyThresholds = ctx.__get('defaultFluencyThresholds');
globalThis.generateFluencyProblemList = ctx.__get('generateFluencyProblemList');
globalThis.pickFluencyFeastEasyStart = ctx.__get('pickFluencyFeastEasyStart');
globalThis.initSqlJs = async () => ({
  Database: class {
    exec() { return []; }
    close() {}
  },
});

let SQL = null;
try {
  const { readFileSync } = await import('node:fs');
  const initSqlJs = (await import('sql.js')).default;
  const wasmBinary = readFileSync(new URL('./node_modules/sql.js/dist/sql-wasm.wasm', import.meta.url));
  SQL = await initSqlJs({ wasmBinary });
} catch { /* optional */ }

const { buildSessionJson, buildBurst, initLearner } = await import('../dragon/quiz_bridge.js');

test('buildSessionJson matches anchor-compatible shape', () => {
  const problems = [{
    id: 't-0', fact_key: '+|1|2', problem_text: '1 + 2', correct_answer: 3,
    user_answer_string: '3', user_answer: 3, is_correct: true, response_time_ms: 500,
    presented_at: 1000, flags: [],
  }];
  const json = buildSessionJson({
    user: 'DragonDev', folder: 'test', problems, kind: 'list-complete', startTime: '2026-07-02_120000',
  });
  assert.equal(json.version, '1.1');
  assert.equal(json.user.name, 'DragonDev');
  assert.equal(json.session.settings.preset, 'dragon-feast');
  assert.ok(json.session.settings.note.includes('mode:dragon'));
  assert.deepEqual(json.session.settings.number_range, [0, 9]);
  assert.deepEqual(json.session.settings.operations, ['+']);
  assert.equal(json.session.problems.length, 1);
});

test('importSessionData accepts dragon session JSON', { skip: SQL ? false : 'sql.js not installed' }, () => {
  const json = buildSessionJson({
    user: 'T', folder: 'test',
    problems: [{ id: 'a', fact_key: '+|0|0', problem_text: '0 + 0', correct_answer: 0,
      user_answer_string: '0', user_answer: 0, is_correct: true, response_time_ms: 400,
      presented_at: 1, flags: [] }],
    kind: 'list-complete', startTime: '2026-07-02_120000',
  });
  const db = new SQL.Database();
  createTables(db);
  importSessionData(db, json, 'test.sqlite');
  const res = db.exec("SELECT COUNT(*) FROM ProblemAttempts");
  assert.equal(res[0].values[0][0], 1);
  db.close();
});

test('buildSessionJson preserves problem flags for import', { skip: SQL ? false : 'sql.js not installed' }, () => {
  const flags = [{ reason: 'distracted', label: 'Distracted', timestamp: '2026-07-02T12:00:00.000Z', notes: 'tired' }];
  const json = buildSessionJson({
    user: 'T', folder: 'test',
    problems: [{ id: 'a', fact_key: '+|1|2', problem_text: '1 + 2', correct_answer: 3,
      user_answer_string: '', user_answer: null, is_correct: false, response_time_ms: 900,
      presented_at: 1, flags }],
    kind: 'quit-saved', startTime: '2026-07-02_120000',
  });
  assert.deepEqual(json.session.problems[0].flags, flags);
  const db = new SQL.Database();
  createTables(db);
  importSessionData(db, json, 'test.sqlite');
  const res = db.exec("SELECT flags_json FROM ProblemAttempts");
  assert.ok(res[0].values[0][0]);
  assert.ok(res[0].values[0][0].includes('distracted'));
  db.close();
});

test('blank-slate buildBurst fallback yields 10-20 addition facts', async () => {
  globalThis.fetch = async () => ({ ok: true, json: async () => ({ ok: true, found: false }) });
  await initLearner({ folder: 'test', user: 'NewKid' });
  const { problems } = buildBurst();
  assert.ok(problems.length >= 10 && problems.length <= 20);
  for (const p of problems) {
    assert.match(p, /^\d \+ \d$/);
  }
});

test('buildBurst with history prepends two easy-start warm-ups', async () => {
  const attempts = [];
  for (let i = 0; i < 5; i++) {
    attempts.push({
      problem_text: '1 + 2', is_correct: 1, response_time_ms: 900,
      flags_json: null, session_id: 's1', start_time: '2026-07-01_090000', attempt_id: i,
    });
    attempts.push({
      problem_text: '1 + 9', is_correct: 1, response_time_ms: 900,
      flags_json: null, session_id: 's1', start_time: '2026-07-01_090000', attempt_id: 10 + i,
    });
  }
  globalThis.fetch = async () => ({
    ok: true,
    json: async () => ({
      ok: true, found: true, filename: 'math-flu_EasyKid.sqlite',
      bytesBase64: '', profile: null, fluencyFeast: null,
    }),
  });
  // Bypass sql.js load path: seed learner state after init of a blank file.
  await initLearner({ folder: 'test', user: 'EasyKid' });
  const { getLearnerState } = await import('../dragon/quiz_bridge.js');
  const st = getLearnerState();
  st.attempts = attempts;
  st.found = true;
  const { problems } = buildBurst();
  assert.equal(problems.length, 22); // 20 feast + 2 easy-start
  const sumOf = (text) => {
    const m = String(text).match(/^(\d)\s*\+\s*(\d)$/);
    return m ? Number(m[1]) + Number(m[2]) : NaN;
  };
  assert.ok(sumOf(problems[0]) < 10, `first should be single-digit sum, got ${problems[0]}`);
  assert.ok(sumOf(problems[1]) >= 10, `second should be two-digit sum, got ${problems[1]}`);
});
