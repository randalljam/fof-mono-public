// Database-level tests using a real sql.js engine (requires `npm install` in
// this folder). Skipped automatically when node_modules is absent so the
// dependency-free vm tests still run standalone.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createAppContext } from './load_app.mjs';

let SQL = null;
try {
  const { readFileSync } = await import('node:fs');
  const initSqlJs = (await import('sql.js')).default;
  // Pass the wasm binary directly: sql.js 1.6.2's emscripten loader misdetects
  // modern Node (global fetch) and tries to fetch() a filesystem path
  const wasmBinary = readFileSync(new URL('./node_modules/sql.js/dist/sql-wasm.wasm', import.meta.url));
  SQL = await initSqlJs({ wasmBinary });
} catch {
  // sql.js not installed; tests below will be skipped
}
const dbTest = (name, fn) => test(name, { skip: SQL ? false : 'sql.js not installed (run npm install in apps/math-quiz/tests)' }, fn);

function makeSession({ id, name = 'Kid1', startTime = '2026-06-01_100000', problems }) {
  return {
    version: '1.1',
    user: { name },
    session: {
      id,
      start_time: startTime,
      end_time: startTime.replace('_10', '_11'),
      settings: {
        preset: 'custom', note: 'seed', num_problems: problems.length,
        number_range: [0, 9], numbers_include: [7], numbers_exclude: [], num_numbers: 2,
        operations: ['+', '-', '*']
      },
      summary: { total_problems: problems.length, correct_answers: problems.filter(p => p.is_correct).length, average_response_time_ms: 1500 },
      problems
    }
  };
}
const problem = (text, { correct = true, ms = 1500, flags = [] } = {}, idSuffix = '') => ({
  id: `id_${text.replace(/\s/g, '')}${idSuffix}`,
  problem_text: text,
  correct_answer: 8,
  user_answer_string: '8',
  user_answer: 8,
  is_correct: correct,
  response_time_ms: ms,
  flags
});

function freshDbContext(files) {
  const ctx = createAppContext(files);
  const db = new SQL.Database();
  ctx.__get('createTables')(db);
  return { ctx, db };
}
const count = (db, sql) => db.exec(sql)[0].values[0][0];

dbTest('importSessionData imports users, sessions, and attempts', () => {
  const { ctx, db } = freshDbContext(['math_utils.js']);
  const session = makeSession({ id: 's1', problems: [problem('5 + 3'), problem('5 - 3'), problem('5 &times; 3')] });
  ctx.__get('importSessionData')(db, session, 'file1.json');
  assert.equal(count(db, 'SELECT COUNT(*) FROM Users'), 1);
  assert.equal(count(db, 'SELECT COUNT(*) FROM Sessions'), 1);
  assert.equal(count(db, 'SELECT COUNT(*) FROM ProblemAttempts'), 3);
  // legacy &times; is normalized into the operation column
  assert.equal(count(db, `SELECT COUNT(*) FROM ProblemAttempts WHERE operation = '*'`), 1);
});

dbTest('createTables includes problem-list tables for per-user saved lists', () => {
  const { db } = freshDbContext(['math_utils.js']);
  const tables = db.exec(
    "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('ProblemLists','ProblemListItems') ORDER BY name"
  )[0].values.map((row) => row[0]);
  assert.deepEqual(tables, ['ProblemListItems', 'ProblemLists']);
  db.run(
    "INSERT INTO ProblemLists (user_name, list_order, list_name, added_at, source) VALUES ('Kid1', 1, 'List One', '2026-06-19T12:00:00', 'test')"
  );
  db.run(
    "INSERT INTO ProblemListItems (problem_list_id, item_order, problem_text, num1, operation, num2, category, notes) VALUES (1, 1, '8 + 2', 8, '+', 2, 'Add Two', 'turn-around')"
  );
  assert.equal(count(db, 'SELECT COUNT(*) FROM ProblemListItems'), 1);
});

dbTest('importSessionData stores targeted-practice session metadata', () => {
  const { ctx, db } = freshDbContext(['math_utils.js']);
  const p1 = {
    ...problem('3 + 6', { ms: 1200 }),
    targeted_practice: { role: 'target', target_key: '+|3|6', current_target_key: '+|3|6', target_order: 1, fast_correct: true }
  };
  const p2 = {
    ...problem('1 + 1', { ms: 900 }, '_filler'),
    targeted_practice: { role: 'filler', target_key: null, current_target_key: '+|3|6', target_order: null, fast_correct: false }
  };
  const session = makeSession({ id: 'targeted-1', problems: [p1, p2] });
  session.session.settings.preset = 'anchor-targeted';
  session.session.settings.note = 'mode:targeted-practice;outcome:targeted-partial';
  session.session.settings.targeted_practice_metadata = {
    mode: 'targeted-practice',
    targets: ['+|3|6'],
    targetCount: 1,
    fillerPoolSize: 1,
    percentTarget: 50,
    graduationStreak: 3,
    fastMs: 2000,
    problemsPresented: 2,
    graduated: [],
    complete: false,
    completionReason: null,
    currentTargetKey: '+|3|6',
    activeTargets: ['+|3|6'],
    perTarget: [{ key: '+|3|6', streak: 1, graduated: false, graduationStreak: 3, attempts: 1, fastCorrect: 1 }]
  };
  ctx.__get('importSessionData')(db, session, 'targeted.sqlite');
  assert.equal(db.exec("SELECT session_type FROM Sessions WHERE session_id='targeted-1'")[0].values[0][0], 'targeted-practice');
  assert.equal(count(db, 'SELECT COUNT(*) FROM TargetedPracticeSessions'), 1);
  assert.equal(count(db, 'SELECT COUNT(*) FROM TargetedPracticeTargets'), 1);
  assert.equal(count(db, 'SELECT COUNT(*) FROM TargetedPracticeAttemptRoles'), 2);
  const targetRow = db.exec('SELECT target_key, fast_correct, attempts, graduated FROM TargetedPracticeTargets')[0].values[0];
  assert.deepEqual(targetRow, ['+|3|6', 1, 1, 0]);
  const roleRows = db.exec('SELECT role, current_target_key, fast_correct FROM TargetedPracticeAttemptRoles ORDER BY attempt_index')[0].values;
  assert.deepEqual(roleRows, [['target', '+|3|6', 1], ['filler', '+|3|6', 0]]);
});

dbTest('importSessionData stores visual-practice metadata and includes it in fluency feeds', () => {
  const { ctx, db } = freshDbContext(['math_utils.js']);
  const p1 = {
    ...problem('8 + 3', { ms: 4200 }, '_cold'),
    fact_key: '+|8|3',
    visual_practice: { trial_role: 'cold-probe', target_key: '+|8|3', visual_shown: false, passed: false }
  };
  const p2 = {
    ...problem('1 + 1', { ms: 900 }, '_filler'),
    fact_key: '+|1|1',
    visual_practice: { trial_role: 'filler', target_key: null, visual_shown: false, passed: false }
  };
  const p3 = {
    ...problem('8 + 3', { ms: 1200 }, '_delayed'),
    fact_key: '+|8|3',
    visual_practice: { trial_role: 'delayed-retrieval', target_key: '+|8|3', visual_shown: true, passed: true }
  };
  const visualSession = makeSession({ id: 'visual-1', problems: [p1, p2, p3] });
  // Legacy JSON may predate the explicit session_type field; the visual preset must
  // still classify the session as visual-practice.
  visualSession.session.settings.preset = 'anchor-visual';
  visualSession.session.settings.note = 'mode:visual-practice;outcome:visual-complete';
  visualSession.session.settings.visual_practice_metadata = {
    mode: 'visual-practice',
    targets: ['+|8|3'],
    targetCount: 1,
    fastMs: 2000,
    retrievalsToClear: 2,
    hesitationMs: 6000,
    problemsPresented: 3,
    cleared: ['+|8|3'],
    complete: true,
    completionReason: 'all-cleared',
    perTarget: [{
      key: '+|8|3',
      num1: 8,
      num2: 3,
      operation: '+',
      coldProbe: 'slow-correct',
      teachCount: 1,
      retrievalSuccesses: 2,
      attempts: 3,
      requiredSuccesses: 2,
      cleared: true
    }]
  };
  const legacySession = makeSession({
    id: 'legacy-1',
    startTime: '2026-06-02_100000',
    problems: [problem('2 + 3', { ms: 900 }, '_legacy')]
  });
  const importSessionData = ctx.__get('importSessionData');
  importSessionData(db, visualSession, 'visual.sqlite');
  importSessionData(db, legacySession, 'legacy.sqlite');
  importSessionData(db, visualSession, 'visual-again.sqlite');

  assert.equal(db.exec("SELECT session_type FROM Sessions WHERE session_id='visual-1'")[0].values[0][0], 'visual-practice');
  assert.equal(db.exec("SELECT session_type FROM Sessions WHERE session_id='legacy-1'")[0].values[0][0], null);
  assert.equal(count(db, 'SELECT COUNT(*) FROM Sessions'), 2);
  assert.equal(count(db, 'SELECT COUNT(*) FROM ProblemAttempts'), 4);
  assert.equal(count(db, 'SELECT COUNT(*) FROM VisualPracticeSessions'), 1);
  assert.equal(count(db, 'SELECT COUNT(*) FROM VisualPracticeTargets'), 1);
  assert.equal(count(db, 'SELECT COUNT(*) FROM VisualPracticeAttemptRoles'), 3);

  const sessionRow = db.exec(
    'SELECT outcome, complete, completion_reason, target_count, cleared_count, fast_ms, retrievals_to_clear, hesitation_ms, problems_presented, targets_json, cleared_json FROM VisualPracticeSessions'
  )[0].values[0];
  assert.deepEqual(sessionRow, [
    'visual-complete', 1, 'all-cleared', 1, 1, 2000, 2, 6000, 3, '["+|8|3"]', '["+|8|3"]'
  ]);
  const targetRow = db.exec(
    'SELECT target_key, problem_text, num1, num2, operation, cold_probe_result, teach_count, retrieval_successes, attempts, required_successes, cleared FROM VisualPracticeTargets'
  )[0].values[0];
  assert.deepEqual(targetRow, ['+|8|3', '8 + 3', 8, 3, '+', 'slow-correct', 1, 2, 3, 2, 1]);
  const roleRows = db.exec(
    'SELECT trial_role, target_key, visual_shown, passed FROM VisualPracticeAttemptRoles ORDER BY attempt_index'
  )[0].values;
  assert.deepEqual(roleRows, [
    ['cold-probe', '+|8|3', 0, 0],
    ['filler', null, 0, 0],
    ['delayed-retrieval', '+|8|3', 1, 1]
  ]);

  const exclusionSql = ctx.__get('sessionTypeExclusionSql')(db, 's');
  assert.equal(exclusionSql, '');
  const fluencyRows = db.exec(`
    SELECT pa.problem_text
    FROM ProblemAttempts pa
    JOIN Sessions s ON pa.session_id = s.session_id
    WHERE s.user_name = 'Kid1'${exclusionSql}
    ORDER BY pa.attempt_id
  `)[0].values.map((row) => row[0]);
  assert.deepEqual(fluencyRows, ['8 + 3', '1 + 1', '8 + 3', '2 + 3']);
});

dbTest('importSessionData stores per-problem presented_at (null when absent)', () => {
  const { ctx, db } = freshDbContext(['math_utils.js']);
  const ts = '2026-06-18T19:30:05.123Z';
  const withTs = { ...problem('5 + 3'), presented_at: ts };
  const withoutTs = problem('5 - 3'); // older capture: no presented_at
  ctx.__get('importSessionData')(db, makeSession({ id: 's1', problems: [withTs, withoutTs] }), 'file1.json');
  const stmt = db.prepare('SELECT problem_text, presented_at FROM ProblemAttempts ORDER BY ROWID');
  const rows = [];
  while (stmt.step()) rows.push(stmt.getAsObject());
  stmt.free();
  assert.equal(rows[0].presented_at, ts);   // stored verbatim when present
  assert.equal(rows[1].presented_at, null); // null when the field is absent
});

dbTest('re-importing the same session does not duplicate attempts (P3 regression)', () => {
  const { ctx, db } = freshDbContext(['math_utils.js']);
  const session = makeSession({ id: 's1', problems: [problem('5 + 3'), problem('5 - 3')] });
  const importSessionData = ctx.__get('importSessionData');
  importSessionData(db, session, 'file1.json');
  importSessionData(db, session, 'file1_MODIFIED.json');
  importSessionData(db, session, 'file1 (1).json');
  assert.equal(count(db, 'SELECT COUNT(*) FROM Sessions'), 1);
  assert.equal(count(db, 'SELECT COUNT(*) FROM ProblemAttempts'), 2);
});

dbTest('deleteSessionFromDb allows a replacing re-import', () => {
  const { ctx, db } = freshDbContext(['math_utils.js']);
  const importSessionData = ctx.__get('importSessionData');
  importSessionData(db, makeSession({ id: 's1', problems: [problem('5 + 3')] }), 'a.json');
  ctx.__get('deleteSessionFromDb')(db, 's1');
  importSessionData(db, makeSession({ id: 's1', problems: [problem('5 + 3'), problem('2 + 2')] }), 'a_v2.json');
  assert.equal(count(db, 'SELECT COUNT(*) FROM Sessions'), 1);
  assert.equal(count(db, 'SELECT COUNT(*) FROM ProblemAttempts'), 2);
});

dbTest('prepareFluencyDatasets includes legacy-format multiplication (P1 regression)', () => {
  const { ctx, db } = freshDbContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js']);
  const problems = [
    problem('2 + 3', { ms: 900 }),
    problem('5 &times; 3', { ms: 1200 }),
    problem('5 × 4', { ms: 5000 }),
    problem('4 - 1', { ms: 1000 })
  ];
  ctx.__get('importSessionData')(db, makeSession({ id: 's1', problems }), 'a.json');
  ctx.__get('prepareFluencyDatasets')(db, { windowSize: 5, minAccuracy: 0.8, greenMs: 2000, redMs: 4000, retentionSessions: 3 }, 'all');
  const datasets = ctx.__evalJson('fluencyDatasets');
  assert.deepEqual(Object.keys(datasets.multiplication.combined).sort(), ['*|3|5', '*|4|5']);
  assert.equal(datasets.multiplication.combined['*|3|5'].status, 'green');
  assert.equal(datasets.multiplication.combined['*|4|5'].status, 'red');
  assert.deepEqual(Object.keys(datasets.addition.combined), ['+|2|3']);
  // non-commutative: operands keep their original order in the key
  assert.deepEqual(Object.keys(datasets.subtraction.combined), ['-|4|1']);
});

dbTest('prepareFluencyDatasets upgrades consistent greens to permanent blue', () => {
  const { ctx, db } = freshDbContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js']);
  const importSessionData = ctx.__get('importSessionData');
  importSessionData(db, makeSession({ id: 's1', problems: [problem('2 + 3', { ms: 900 })] }), 'a.json');
  importSessionData(db, makeSession({ id: 's2', startTime: '2026-06-02_100000', problems: [problem('2 + 3', { ms: 800 }, '_b')] }), 'b.json');
  const thresholds = { windowSize: 5, minAccuracy: 0.8, greenMs: 2000, redMs: 4000, retentionSessions: 3, permanentSessions: 2 };
  ctx.__get('prepareFluencyDatasets')(db, thresholds, 'all');
  assert.equal(ctx.__eval(`fluencyDatasets.addition.combined['+|2|3'].status`), 'blue');
  // with a higher threshold the same data stays green
  ctx.__get('prepareFluencyDatasets')(db, { ...thresholds, permanentSessions: 5 }, 'all');
  assert.equal(ctx.__eval(`fluencyDatasets.addition.combined['+|2|3'].status`), 'green');
});

dbTest('prepareFluencyDatasets filters by username with bound parameters', () => {
  const { ctx, db } = freshDbContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js']);
  const importSessionData = ctx.__get('importSessionData');
  importSessionData(db, makeSession({ id: 's1', name: "O'Brien", problems: [problem('2 + 3')] }), 'a.json');
  importSessionData(db, makeSession({ id: 's2', name: 'Kid1', startTime: '2026-06-02_100000', problems: [problem('4 + 4')] }), 'b.json');
  ctx.__get('prepareFluencyDatasets')(db, { windowSize: 5, minAccuracy: 0.8, greenMs: 2000, redMs: 4000, retentionSessions: 3 }, "O'Brien");
  const datasets = ctx.__evalJson('fluencyDatasets');
  assert.deepEqual(Object.keys(datasets.addition.combined), ['+|2|3']);
});

dbTest('queryDatabase operation filter matches legacy multiplication rows (P1 regression)', () => {
  const { ctx, db } = freshDbContext(['math_utils.js', 'math_analysis.js']);
  const problems = [problem('2 + 3'), problem('5 &times; 3'), problem('6 - 2'), problem('8 &divide; 2')];
  ctx.__get('importSessionData')(db, makeSession({ id: 's1', problems }), 'a.json');
  const queryDatabase = ctx.__get('queryDatabase');
  assert.equal(queryDatabase(db, 'all', 'all', 1, '*').length, 1);
  assert.equal(queryDatabase(db, 'all', 'all', 1, 'muldiv').length, 2);
  assert.equal(queryDatabase(db, 'all', 'all', 1, '-').length, 1);
  assert.equal(queryDatabase(db, 'all', 'all', 1, 'all').length, 4);
});

dbTest('queryDatabase handles usernames containing quotes (P6 regression)', () => {
  const { ctx, db } = freshDbContext(['math_utils.js', 'math_analysis.js']);
  ctx.__get('importSessionData')(db, makeSession({ id: 's1', name: "O'Brien", problems: [problem('2 + 3')] }), 'a.json');
  const rows = ctx.__get('queryDatabase')(db, "O'Brien", 'all', 1, 'all');
  assert.equal(rows.length, 1);
});

dbTest('getLastNSessionIds returns most recent sessions, 1 for "last"', () => {
  const { ctx, db } = freshDbContext(['math_utils.js', 'math_analysis.js']);
  const importSessionData = ctx.__get('importSessionData');
  for (let i = 1; i <= 3; i++) {
    importSessionData(db, makeSession({ id: `s${i}`, startTime: `2026-06-0${i}_100000`, problems: [problem('2 + 3', {}, `_${i}`)] }), `f${i}.json`);
  }
  const getLastNSessionIds = ctx.__get('getLastNSessionIds');
  assert.deepEqual(JSON.parse(JSON.stringify(getLastNSessionIds(db, 2, 'all'))), ['s3', 's2']);
  assert.deepEqual(JSON.parse(JSON.stringify(getLastNSessionIds(db, 1, 'all'))), ['s3']);
  assert.deepEqual(JSON.parse(JSON.stringify(getLastNSessionIds(db, NaN, 'all'))), ['s3']);
});

dbTest('getLastNSessionIds sorts by filename stamp across math-flu / mathquest prefixes', () => {
  const { ctx, db } = freshDbContext(['math_utils.js', 'math_analysis.js']);
  const importSessionData = ctx.__get('importSessionData');
  // Alphabetically math-flu_* sorts before mathquest_*, so ORDER BY filename would put
  // the older math-flu session first. Recency must use the embedded stamp instead.
  importSessionData(
    db,
    makeSession({ id: 'older', startTime: '2026-07-20_100000', problems: [problem('2 + 3', {}, '_a')] }),
    'math-flu_Izzy_2026-07-20_100000.sqlite'
  );
  importSessionData(
    db,
    makeSession({ id: 'newer', startTime: '2026-07-27_171219', problems: [problem('2 + 3', {}, '_b')] }),
    'mathquest_Izzy_2026-07-27_171219.sqlite'
  );
  importSessionData(
    db,
    makeSession({ id: 'mid', startTime: '2026-07-25_090000', problems: [problem('2 + 3', {}, '_c')] }),
    'math-flu_Izzy_2026-07-25_090000.sqlite'
  );
  const getLastNSessionIds = ctx.__get('getLastNSessionIds');
  assert.deepEqual(JSON.parse(JSON.stringify(getLastNSessionIds(db, 2, 'all'))), ['newer', 'mid']);
  assert.deepEqual(JSON.parse(JSON.stringify(getLastNSessionIds(db, 1, 'all'))), ['newer']);
});

dbTest('queryDatabase accepts an explicit session-id array from the checkbox picker', () => {
  const { ctx, db } = freshDbContext(['math_utils.js', 'math_analysis.js']);
  const importSessionData = ctx.__get('importSessionData');
  importSessionData(db, makeSession({ id: 's1', startTime: '2026-06-01_100000', problems: [problem('2 + 3', {}, '_1')] }), 'a.json');
  importSessionData(db, makeSession({ id: 's2', startTime: '2026-06-02_100000', problems: [problem('4 + 4', {}, '_2')] }), 'b.json');
  const queryDatabase = ctx.__get('queryDatabase');
  assert.equal(queryDatabase(db, 'all', ['s2'], 1, 'all').length, 1);
  assert.equal(queryDatabase(db, 'all', ['s1', 's2'], 1, 'all').length, 2);
  assert.equal(queryDatabase(db, 'all', [], 1, 'all').length, 0);
});
