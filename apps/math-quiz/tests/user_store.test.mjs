// C2/C4 tests — per-user SQLite store: ingest, fluency derivation, mode events,
// persistence round-trip, manual export/import, and Minecraft-format parity.
// Uses a real sql.js engine + the real app functions loaded into a vm context.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createAppContext } from './load_app.mjs';
import { openUserStore } from '../engine/user_store.mjs';
import { createMemoryPersistence } from '../engine/persistence.mjs';

let SQL = null;
try {
  const { readFileSync } = await import('node:fs');
  const initSqlJs = (await import('sql.js')).default;
  const wasmBinary = readFileSync(new URL('./node_modules/sql.js/dist/sql-wasm.wasm', import.meta.url));
  SQL = await initSqlJs({ wasmBinary });
} catch {
  // sql.js not installed; tests skipped
}
const dbTest = (name, fn) => test(name, { skip: SQL ? false : 'sql.js not installed (run npm install in apps/math-quiz/tests)' }, fn);

function makeDeps(ctx) {
  return {
    SQL,
    createTables: ctx.__get('createTables'),
    importSession: ctx.__get('importSessionData'),
    deleteSession: ctx.__get('deleteSessionFromDb'),
    deriveFluency: (db, thr, user) => { ctx.__get('prepareFluencyDatasets')(db, thr, user); return ctx.__evalJson('fluencyDatasets'); },
  };
}

// Fast/correct addition session; '+|2|3' appears twice so it computes green.
function fluentAdditionSession(id, name = 'Mia') {
  const probs = [['2 + 3', 5], ['2 + 3', 5], ['4 + 1', 5], ['0 + 6', 6]].map(([text, ans], i) => ({
    id: `${id}-${i}`, problem_text: text, correct_answer: ans,
    user_answer_string: String(ans), user_answer: ans, is_correct: true, response_time_ms: 900, flags: [],
  }));
  return {
    version: '1.1', user: { name },
    session: {
      id, start_time: '2026-06-01_100000', end_time: '2026-06-01_101000',
      settings: { num_problems: probs.length, number_range: [0, 9], numbers_include: [], numbers_exclude: [], num_numbers: 2, operations: ['+'] },
      summary: { total_problems: probs.length, correct_answers: probs.length, average_response_time_ms: 900 },
      problems: probs,
    },
  };
}

dbTest('ingest writes sessions/attempts; counts reflect the user', async () => {
  const ctx = createAppContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js']);
  const store = await openUserStore({ username: 'Mia', deps: makeDeps(ctx) });
  store.ingest(fluentAdditionSession('s1'), 's1.json');
  assert.equal(store.sessionCount(), 1);
  assert.equal(store.attemptCount(), 4);
});

dbTest('getFluency derives green for a fast/correct repeated fact', async () => {
  const ctx = createAppContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js']);
  const store = await openUserStore({ username: 'Mia', deps: makeDeps(ctx) });
  store.ingest(fluentAdditionSession('s1'), 's1.json');
  const f = store.getFluency();
  assert.equal(f.addition.combined['+|2|3'].status, 'green');
});

dbTest('mode events: log assess/practice transitions and read current mode', async () => {
  const ctx = createAppContext(['math_utils.js']);
  const store = await openUserStore({ username: 'Mia', deps: makeDeps(ctx) });
  store.logModeEvent({ to: 'assess', trigger: 'session-start' });
  store.logModeEvent({ from: 'assess', to: 'practice', trigger: 'deviation-cluster' });
  const ev = store.getModeEvents();
  assert.equal(ev.length, 2);
  assert.equal(ev[1].from, 'assess');
  assert.equal(store.currentMode(), 'practice');
  assert.throws(() => store.logModeEvent({ to: 'bogus' }), /Unknown mode/);
});

dbTest('persistence: save then reopen restores all data + fluency', async () => {
  const persistence = createMemoryPersistence();
  const s1 = await openUserStore({ username: 'Mia', deps: makeDeps(createAppContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js'])), persistence });
  s1.ingest(fluentAdditionSession('s1'), 's1.json');
  s1.logModeEvent({ to: 'assess', trigger: 'session-start' });
  await s1.save();

  const s2 = await openUserStore({ username: 'Mia', deps: makeDeps(createAppContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js'])), persistence });
  assert.equal(s2.sessionCount(), 1);
  assert.equal(s2.attemptCount(), 4);
  assert.equal(s2.currentMode(), 'assess');
  assert.equal(s2.getFluency().addition.combined['+|2|3'].status, 'green');
});

dbTest('exportBytes round-trips through a fresh store (manual file path)', async () => {
  const s1 = await openUserStore({ username: 'Mia', deps: makeDeps(createAppContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js'])) });
  s1.ingest(fluentAdditionSession('s1'), 's1.json');
  const bytes = s1.exportBytes();
  // simulate downloading the .sqlite file and re-opening it elsewhere
  const persistence = createMemoryPersistence({ Mia: bytes });
  const s2 = await openUserStore({ username: 'Mia', deps: makeDeps(createAppContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js'])), persistence });
  assert.equal(s2.sessionCount(), 1);
  assert.equal(s2.attemptCount(), 4);
});

dbTest('warm-up entries are stored separately from problems (WarmupAttempts)', async () => {
  const ctx = createAppContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js']);
  const store = await openUserStore({ username: 'Mia', deps: makeDeps(ctx) });
  store.ingest(fluentAdditionSession('s1'), 's1.json');     // arithmetic problems
  assert.equal(store.warmupCount(), 0);                     // none yet
  store.recordWarmup([
    { round: 1, target: 12, entered: 12, isCorrect: true, responseTime: 1500 },
    { round: 1, target: 12, entered: 13, isCorrect: false, responseTime: 900 }, // a wrong try is kept too
    { round: 1, target: 3, entered: 3, isCorrect: true, responseTime: 700 },
  ], 's1');
  assert.equal(store.warmupCount(), 3);
  // they don't pollute the arithmetic problem count
  assert.equal(store.attemptCount(), 4);
  const rows = store.db.exec("SELECT target, is_correct FROM WarmupAttempts WHERE user_name='Mia' ORDER BY warmup_id")[0].values;
  assert.deepEqual(rows, [[12, 1], [12, 0], [3, 1]]);
});

dbTest('a Minecraft-format session ingests identically (shared JSON format)', async () => {
  const ctx = createAppContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js']);
  const store = await openUserStore({ username: 'Mia', deps: makeDeps(ctx) });
  const mc = fluentAdditionSession('mc1');
  mc.session.settings.note = 'source:minecraft-mathquest'; // different producer, identical shape
  store.ingest(mc, 'mc1.json');
  assert.equal(store.attemptCount(), 4);
  assert.equal(store.getFluency().addition.combined['+|2|3'].status, 'green');
});
