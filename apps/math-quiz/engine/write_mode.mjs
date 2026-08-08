// C1 — write-mode switch. Single gate all session output passes through, so one
// flag decides whether canonical session JSON is emitted, the SQLite store is
// written, or both. Dev default is 'sqlite-only' so dev runs don't spew test JSON.
// See 2026-06-15_assess-practice-modes-spec-and-plan.md §7 / Part C (C1).

export const WRITE_MODES = ['sqlite-only', 'json+sqlite', 'json-only'];
export const DEFAULT_WRITE_MODE = 'sqlite-only';

export function isValidWriteMode(mode) {
  return WRITE_MODES.includes(mode);
}

export function shouldWriteJson(mode) {
  return mode === 'json+sqlite' || mode === 'json-only';
}

export function shouldWriteSqlite(mode) {
  return mode === 'sqlite-only' || mode === 'json+sqlite';
}

// Build the single session-output gate. `writeJson` / `writeSqlite` are the sinks
// (e.g. download a file / ingest into the per-user store); either may be async.
// writeSession returns { json, sqlite } booleans reporting which sinks ran.
export function createSessionWriter({ mode = DEFAULT_WRITE_MODE, writeJson = null, writeSqlite = null } = {}) {
  if (!isValidWriteMode(mode)) throw new Error(`Unknown write mode: ${mode} (expected one of ${WRITE_MODES.join(', ')})`);
  return {
    mode,
    async writeSession(sessionJson, filename) {
      const out = { json: false, sqlite: false };
      if (shouldWriteSqlite(mode) && writeSqlite) { await writeSqlite(sessionJson, filename); out.sqlite = true; }
      if (shouldWriteJson(mode) && writeJson) { await writeJson(sessionJson, filename); out.json = true; }
      return out;
    },
  };
}
