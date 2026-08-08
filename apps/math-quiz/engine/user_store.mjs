// C2/C4 — per-user SQLite store. One DB per user holds all their history. It
// reuses the app's REAL schema and import/fluency code (injected, since those
// are browser globals, not ES modules) rather than a parallel model, and adds a
// ModeEvents table (C4) plus persistence + export/import (C2).
// See 2026-06-15_assess-practice-modes-spec-and-plan.md §7 / Part C.

export const MODES = ['assess', 'practice'];
export const DEFAULT_THRESHOLDS = {
  windowSize: 5, minAccuracy: 0.8, greenMs: 2000, redMs: 4000,
  retentionSessions: 3, permanentSessions: 5,
};

function ensureModeEventsTable(db) {
  db.run(`
    CREATE TABLE IF NOT EXISTS ModeEvents (
      event_id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_name TEXT,
      session_id TEXT NULL,
      from_mode TEXT NULL,
      to_mode TEXT,
      trigger TEXT,
      timestamp TEXT
    );
  `);
}

// Warm-up keypad-practice entries — kept SEPARATE from ProblemAttempts (these are
// not arithmetic problems; they record how the learner did entering numbers).
function ensureWarmupTable(db) {
  db.run(`
    CREATE TABLE IF NOT EXISTS WarmupAttempts (
      warmup_id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_name TEXT,
      session_id TEXT NULL,
      round INTEGER,
      target INTEGER,
      entered TEXT,
      is_correct INTEGER,
      response_time_ms INTEGER,
      timestamp TEXT
    );
  `);
}

// deps (injected real app functions):
//   SQL           - sql.js module ({ Database })
//   createTables  - (db) => void               [math_utils.js]
//   importSession - (db, sessionJson, file) => void   [importSessionData]
//   deleteSession - (db, sessionId) => void     [deleteSessionFromDb] (optional)
//   deriveFluency - (db, thresholds, username) => fluencyDatasets  [wraps prepareFluencyDatasets]
// config: { username, deps, persistence?, thresholds? }
export async function openUserStore(config) {
  const { username, deps, persistence = null, thresholds = DEFAULT_THRESHOLDS } = config;
  if (!username) throw new Error('openUserStore requires a username');
  const { SQL, createTables, importSession, deleteSession, deriveFluency } = deps;

  let bytes = null;
  if (persistence) bytes = await persistence.load(username);
  const db = bytes ? new SQL.Database(bytes) : new SQL.Database();
  createTables(db);          // idempotent (CREATE TABLE IF NOT EXISTS)
  ensureModeEventsTable(db);

  const scalar = (sql, params = []) => {
    const stmt = db.prepare(sql);
    if (params.length) stmt.bind(params);
    stmt.step();
    const v = stmt.get()[0];
    stmt.free();
    return v;
  };

  return {
    username,
    db,
    // Ingest one canonical session-JSON object (the format importSessionData and
    // the Minecraft mod both produce). Dedup/normalization is the real code's job.
    ingest(sessionJson, filename) {
      const fname = filename || `session_${sessionJson?.session?.id || 'unknown'}.json`;
      importSession(db, sessionJson, fname);
    },
    deleteSession(sessionId) {
      if (deleteSession) deleteSession(db, sessionId);
    },
    // Warm-up keypad-practice entries (separate from ProblemAttempts).
    // entries: [{ round, target, entered, isCorrect, responseTime, timestamp? }]
    recordWarmup(entries, sessionId = null) {
      if (!entries || !entries.length) return;
      ensureWarmupTable(db);
      for (const e of entries) {
        db.run(
          'INSERT INTO WarmupAttempts (user_name, session_id, round, target, entered, is_correct, response_time_ms, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
          [username, sessionId, e.round ?? null, e.target ?? null, e.entered === null || e.entered === undefined ? '' : String(e.entered),
            e.isCorrect ? 1 : 0, e.responseTime == null ? null : Math.round(e.responseTime), e.timestamp || new Date().toISOString()]
        );
      }
    },
    warmupCount() {
      try {
        const r = db.exec('SELECT count(*) FROM WarmupAttempts WHERE user_name = ?', [username]);
        return r.length ? r[0].values[0][0] : 0;
      } catch { return 0; } // table not created until a warm-up is recorded
    },
    // C4 — log an assess/practice transition.
    logModeEvent({ from = null, to, trigger = '', sessionId = null, timestamp = null }) {
      if (!MODES.includes(to)) throw new Error(`Unknown mode: ${to}`);
      db.run(
        'INSERT INTO ModeEvents (user_name, session_id, from_mode, to_mode, trigger, timestamp) VALUES (?, ?, ?, ?, ?, ?)',
        [username, sessionId, from, to, trigger, timestamp || new Date().toISOString()]
      );
    },
    getModeEvents() {
      const res = db.exec('SELECT from_mode, to_mode, trigger, timestamp FROM ModeEvents WHERE user_name = ? ORDER BY event_id', [username]);
      if (!res.length) return [];
      return res[0].values.map(([from_mode, to_mode, trigger, timestamp]) => ({ from: from_mode, to: to_mode, trigger, timestamp }));
    },
    currentMode() {
      const res = db.exec('SELECT to_mode FROM ModeEvents WHERE user_name = ? ORDER BY event_id DESC LIMIT 1', [username]);
      return res.length ? res[0].values[0][0] : null;
    },
    // Derive per-fact fluency from the DB via the REAL fluency code.
    getFluency(overrideThresholds) {
      return deriveFluency(db, overrideThresholds || thresholds, username);
    },
    sessionCount() { return scalar('SELECT COUNT(*) FROM Sessions WHERE user_name = ?', [username]); },
    attemptCount() {
      return scalar('SELECT COUNT(*) FROM ProblemAttempts pa JOIN Sessions s ON pa.session_id = s.session_id WHERE s.user_name = ?', [username]);
    },
    // Manual export/import + IndexedDB persistence both ride on these bytes.
    exportBytes() { return db.export(); },
    async save() { if (persistence) await persistence.save(username, db.export()); },
    close() { if (typeof db.close === 'function') db.close(); },
  };
}
