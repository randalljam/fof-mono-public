// Read raw data out of a per-run SQLite DB and (later) guarantee "raw-only" copies
// for re-processing. The per-run DB already stores ONLY raw data — Users, Sessions,
// ProblemAttempts (every trial: text, answer, correct?, response_time_ms, flags),
// and ModeEvents. The fluency *evaluation* (per-fact status, mastery verdict) is
// NOT persisted; it is recomputed from these raw attempts. So re-processing a file
// means: load the raw attempts and re-run the evaluation/flow over them.
// See 2026-06-15_assess-practice-modes-spec-and-plan.md (Part C / re-processing).

// Canonical fluency key: commutative (+,*) ordered min|max; subtraction as-is.
export function canonicalKey(operation, num1, num2) {
  if (operation === '+' || operation === '*') return `${operation}|${Math.min(num1, num2)}|${Math.max(num1, num2)}`;
  return `${operation}|${num1}|${num2}`;
}

// Load raw attempts grouped by canonical fact key, in recorded order.
// Returns Map<key, [{ isCorrect, responseTime, num1, num2, operation }]>.
export function loadRawAttempts(db) {
  const m = new Map();
  const res = db.exec(
    'SELECT num1, num2, operation, is_correct, response_time_ms FROM ProblemAttempts ORDER BY attempt_id'
  );
  if (!res.length) return m;
  for (const [num1, num2, operation, isCorrect, rt] of res[0].values) {
    if (num1 === null || num2 === null || !operation) continue; // skip unparseable legacy rows
    const key = canonicalKey(operation, num1, num2);
    const list = m.get(key) || [];
    list.push({ isCorrect: !!isCorrect, responseTime: rt, num1, num2, operation });
    m.set(key, list);
  }
  return m;
}

// Load the full ordered list of trials exactly as administered (one row per
// problem, in the order they were given — ProblemAttempts.attempt_id is a
// monotonic insert order). Use this when order across facts matters; use
// loadRawAttempts when you only need per-fact attempts for evaluation.
export function loadOrderedProblems(db) {
  const out = [];
  const res = db.exec(
    'SELECT num1, num2, operation, user_answer, is_correct, response_time_ms FROM ProblemAttempts ORDER BY attempt_id'
  );
  if (!res.length) return out;
  for (const [num1, num2, operation, userAnswer, isCorrect, rt] of res[0].values) {
    out.push({
      key: (num1 !== null && num2 !== null && operation) ? canonicalKey(operation, num1, num2) : null,
      num1, num2, operation, userAnswer, isCorrect: !!isCorrect, responseTime: rt,
    });
  }
  return out;
}

// Tables that hold raw input (kept) vs. derived evaluation (dropped on a raw copy).
// Today there are no persisted evaluation tables; this is the future-proof guard
// for when a fluency-snapshot table is added — so re-processing always starts from
// raw data and re-derives everything.
export const RAW_TABLES = ['Users', 'Sessions', 'ProblemAttempts', 'ModeEvents'];
export const EVALUATION_TABLES = ['FluencySnapshots']; // not created yet

export function stripEvaluation(db) {
  const dropped = [];
  for (const t of EVALUATION_TABLES) {
    try { db.run(`DROP TABLE IF EXISTS ${t}`); dropped.push(t); } catch { /* ignore */ }
  }
  return dropped;
}
