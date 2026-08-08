import { loadLatestUserDb, bytesToBase64 } from '../engine/sqlite_io.mjs';
import { openUserStore } from '../engine/user_store.mjs';
import { createMemoryPersistence } from '../engine/persistence.mjs';

const RANGE = [0, 9];
const OPERATIONS = ['+'];
const FLUENCY_FEAST_PRESET = {
  count: 20,
  sessionSelection: { mode: 'all' },
  mix: { missing: 40, incorrect: 40, almost: 10, 'needs-practice': 10, fluent: 0 },
};
// Same as anchor kid Fluency feast: prepend two easy warm-ups (fluent add-0/1/2/doubles:
// single-digit sum, then two-digit). Default on; blank-slate fallback list is unchanged.
const FLUENCY_FEAST_EASY_START = true;
const ATTEMPTS_SQL = `SELECT pa.problem_text AS problem_text, pa.is_correct AS is_correct, pa.response_time_ms AS response_time_ms,
              pa.attempt_id AS attempt_id, pa.session_id AS session_id, pa.flags_json AS flags_json, s.start_time AS start_time
       FROM ProblemAttempts pa JOIN Sessions s ON pa.session_id = s.session_id
       WHERE s.user_name = ? ORDER BY s.start_time, pa.attempt_id`;

let SQL = null;
let state = null;
// forceNew only when the learner has NO existing file (blank slate). An existing
// file — Kid1's real one especially — must always be continued, never forked.
let forceNewNextSave = false;

export async function ensureSql() {
  if (SQL) return SQL;
  if (typeof initSqlJs !== 'function') throw new Error('sql.js not loaded');
  SQL = await initSqlJs({ locateFile: (f) => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.6.2/${f}` });
  return SQL;
}
function storeDeps() {
  return {
    SQL,
    createTables: globalThis.createTables,
    importSession: globalThis.importSessionData,
    deleteSession: globalThis.deleteSessionFromDb,
    deriveFluency: null,
  };
}
function rowsFromExec(db, sql, params) {
  const res = db.exec(sql, params);
  if (!res.length) return [];
  return res[0].values.map((row) => {
    const o = {};
    res[0].columns.forEach((c, i) => { o[c] = row[i]; });
    return o;
  });
}
function thresholdsFromProfile(profile) {
  const t = profile && profile.thresholds;
  if (t && typeof t === 'object') return Object.assign({}, defaultFluencyThresholds, t);
  return defaultFluencyThresholds;
}
function queryAttempts(db, username) {
  return rowsFromExec(db, ATTEMPTS_SQL, [username]);
}
function computePct(attempts, thresholds) {
  if (typeof fluencyPercent !== 'function') return 0;
  return fluencyPercent(attempts, thresholds, { numberRange: RANGE, operations: OPERATIONS, excludeFlagged: true });
}
function shuffle(arr, rng = Math.random) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}
function fallbackProblemList(count) {
  const problems = [];
  for (let a = 0; a <= 9; a++) {
    for (let b = a; b <= 9; b++) problems.push(`${a} + ${b}`);
  }
  return shuffle(problems).slice(0, Math.max(10, Math.min(20, count)));
}
function canonicalKey(operation, num1, num2) {
  if (operation === '+' || operation === '*') return `${operation}|${Math.min(num1, num2)}|${Math.max(num1, num2)}`;
  return `${operation}|${num1}|${num2}`;
}
function parseProblemToItem(text) {
  const parsed = parseProblemText(text);
  const key = canonicalKey(parsed.operation, parsed.num1, parsed.num2);
  return { key, operation: parsed.operation, num1: parsed.num1, num2: parsed.num2, problemText: text };
}
function answerFor(op, n1, n2) {
  if (op === '+') return n1 + n2;
  if (op === '-') return n1 - n2;
  if (op === '*') return n1 * n2;
  if (op === '/') return n2 ? n1 / n2 : Infinity;
  return null;
}
function timestamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

export async function initLearner({ folder = 'test', user = 'DragonDev', dataUser: fileUserIn } = {}) {
  await ensureSql();
  const fileUser = fileUserIn || user;
  const load = await loadLatestUserDb({ folder, user: fileUser });
  if (!load.ok) {
    state = { folder, user, fileUser, found: false, filename: null, db: null, attempts: [], pct: 0, thresholds: defaultFluencyThresholds, feastPreset: FLUENCY_FEAST_PRESET, profile: null, serverOk: false };
    return state;
  }
  if (!load.found || !load.bytes) {
    state = { folder, user, fileUser, found: false, filename: null, attempts: [], pct: 0, thresholds: defaultFluencyThresholds, feastPreset: load.fluencyFeast || FLUENCY_FEAST_PRESET, profile: load.profile, serverOk: true };
    forceNewNextSave = true;   // no file yet — first save starts a fresh lineage
    return state;
  }
  const db = new SQL.Database(load.bytes);
  const attempts = queryAttempts(db, fileUser);
  const thresholds = thresholdsFromProfile(load.profile);
  const pct = computePct(attempts, thresholds);
  state = {
    folder, user, fileUser, found: true, filename: load.filename, attempts, pct,
    thresholds, feastPreset: load.fluencyFeast || FLUENCY_FEAST_PRESET, profile: load.profile, serverOk: true,
  };
  forceNewNextSave = false;    // existing file — always Continue, never fork
  db.close();
  return state;
}
export function getLearnerState() { return state; }
export function currentPct() {
  if (!state) return 0;
  return computePct(state.attempts || [], state.thresholds);
}
export function getDevPctOverride() {
  if (!state || state.folder === 'tlkids') return null;
  const qs = new URLSearchParams(window.location.search);
  const raw = qs.get('pct');
  if (raw == null || raw === '') return null;
  const n = Number(raw);
  return Number.isFinite(n) ? Math.max(0, Math.min(100, Math.round(n))) : null;
}
export function effectivePct() {
  const override = getDevPctOverride();
  if (override != null) return override;
  return currentPct();
}
export async function refreshAttempts() {
  if (!state || !state.serverOk) return;
  const load = await loadLatestUserDb({ folder: state.folder, user: state.fileUser || state.user });
  if (load.found && load.bytes) {
    const db = new SQL.Database(load.bytes);
    state.attempts = queryAttempts(db, state.fileUser || state.user);
    state.filename = load.filename;
    state.pct = computePct(state.attempts, state.thresholds);
    db.close();
  }
}
export function buildBurst() {
  if (!state) return { problems: [], items: [] };
  const saved = state.feastPreset || FLUENCY_FEAST_PRESET;
  const count = Math.max(10, Math.min(20, (saved.count || FLUENCY_FEAST_PRESET.count)));
  const sessionSelection = (saved.session && saved.session.mode)
    ? { mode: saved.session.mode, n: saved.session.n, since: saved.session.since }
    : FLUENCY_FEAST_PRESET.sessionSelection;
  const mix = saved.mix || FLUENCY_FEAST_PRESET.mix;
  let problems = [];
  if (state.attempts && state.attempts.length && typeof generateFluencyProblemList === 'function') {
    const feastOpts = {
      attempts: state.attempts, sessionSelection,
      numberRange: RANGE, operations: OPERATIONS, excludeFlagged: true, thresholds: state.thresholds,
    };
    const res = generateFluencyProblemList({
      ...feastOpts, numProblems: count, distribution: mix,
    });
    problems = (res && res.problems) ? res.problems : [];
    if (problems.length && FLUENCY_FEAST_EASY_START && typeof pickFluencyFeastEasyStart === 'function') {
      const easy = pickFluencyFeastEasyStart(feastOpts);
      if (easy && easy.problems && easy.problems.length === 2) problems = easy.problems.concat(problems);
    }
  }
  if (!problems.length) problems = fallbackProblemList(count);
  const items = problems.map(parseProblemToItem);
  return { problems, items, count: items.length };
}
export function buildSessionJson({ user, folder, problems, kind, startTime }) {
  const correct = problems.filter((p) => p.is_correct).length;
  const avg = problems.length ? Math.round(problems.reduce((s, p) => s + p.response_time_ms, 0) / problems.length) : 0;
  const end = timestamp();
  return {
    version: '1.1',
    user: { name: user },
    session: {
      id: (crypto.randomUUID && crypto.randomUUID()) || `${startTime}-${Math.random().toString(16).slice(2)}`,
      start_time: startTime,
      end_time: end,
      settings: {
        preset: 'dragon-feast',
        note: `mode:dragon;outcome:${kind}`,
        num_problems: problems.length,
        number_range: RANGE,
        numbers_include: [],
        numbers_exclude: [],
        num_numbers: 2,
        operations: OPERATIONS,
        source_folder: folder,
        destination: 'source',
        test_description: '',
      },
      summary: { total_problems: problems.length, correct_answers: correct, average_response_time_ms: avg },
      problems,
    },
  };
}
export function problemEntryFromItem(item, userValue, isCorrect, rt, shownAtWall, idx, startTime) {
  return {
    id: `${startTime}-${idx}`,
    fact_key: item.key,
    problem_text: item.problemText || `${item.num1} ${item.operation} ${item.num2}`,
    correct_answer: answerFor(item.operation, item.num1, item.num2),
    user_answer_string: userValue === null ? '' : String(userValue),
    user_answer: userValue,
    is_correct: isCorrect,
    response_time_ms: Math.round(rt),
    presented_at: shownAtWall,
    flags: [],
  };
}
export async function finishBurst(problems, kind) {
  if (!state) return { saved: false, newPct: 0, error: 'no learner' };
  if (!problems || !problems.length) {
    const pct = currentPct();
    return { saved: false, newPct: pct, initialPct: pct, error: 'no problems answered' };
  }
  const startTime = timestamp();
  const fileUser = state.fileUser || state.user;
  const sessionJson = buildSessionJson({ user: fileUser, folder: state.folder, problems, kind, startTime });
  const initialPct = currentPct();
  const runStore = await openUserStore({
    username: `math-flu_${fileUser}_${startTime}`,
    deps: storeDeps(),
    persistence: createMemoryPersistence(),
  });
  runStore.ingest(sessionJson, `math-flu_${fileUser}_${startTime}.sqlite`);
  const bytes = runStore.exportBytes();
  runStore.close();
  let saved = false;
  let serverResp = null;
  try {
    const resp = await fetch('/api/save-run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sourceFolder: state.folder,
        destination: 'source',
        name: fileUser,
        stamp: startTime,
        testDescription: '',
        forceNew: forceNewNextSave,
        base64: bytesToBase64(bytes),
      }),
    });
    serverResp = await resp.json();
    saved = !!(serverResp && serverResp.ok);
    if (saved) { forceNewNextSave = false; state.found = true; }
  } catch (e) {
    return { saved: false, newPct: initialPct, error: String(e.message || e) };
  }
  if (saved) await refreshAttempts();
  const newPct = currentPct();
  return { saved, newPct, initialPct, serverResp };
}
export function isServerRequired() {
  return !state || !state.serverOk;
}
export { RANGE, OPERATIONS, answerFor, parseProblemToItem };
