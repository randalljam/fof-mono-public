// Shared client SQLite I/O: base64 round-trip and the dev-server latest-DB load
// (fetch injected; no DOM, no sql.js needed). countSessions is covered against a real
// sql.js engine when installed, else skipped.
import test from 'node:test';
import assert from 'node:assert/strict';
import { bytesToBase64, base64ToBytes, loadLatestUserDb, countSessions, chooseHydrationBytes } from '../engine/sqlite_io.mjs';

function stubResp(obj, { ok = true, status = 200 } = {}) {
  return { ok, status, json: async () => obj };
}

test('base64 <-> bytes round-trips arbitrary bytes', () => {
  const src = new Uint8Array([0, 1, 2, 127, 128, 255, 65, 0, 200]);
  const back = base64ToBytes(bytesToBase64(src));
  assert.deepEqual([...back], [...src]);
});

test('chooseHydrationBytes prefers local when it has more sessions than the server', () => {
  const server = new Uint8Array([1]);
  const local = new Uint8Array([2]);
  const stale = chooseHydrationBytes({
    serverBytes: server, serverSessionCount: 89,
    localBytes: local, localSessionCount: 90,
  });
  assert.equal(stale.source, 'local-newer');
  assert.equal(stale.sessionCount, 90);
  assert.equal(stale.bytes, local);

  const fresh = chooseHydrationBytes({
    serverBytes: server, serverSessionCount: 91,
    localBytes: local, localSessionCount: 90,
  });
  assert.equal(fresh.source, 'server');
  assert.equal(fresh.bytes, server);

  const emptyLocal = chooseHydrationBytes({
    serverBytes: server, serverSessionCount: 3,
    localBytes: null, localSessionCount: 0,
  });
  assert.equal(emptyLocal.source, 'server');
});

test('loadLatestUserDb returns decoded bytes + metadata when found', async () => {
  const bytes = new Uint8Array([83, 81, 76, 105, 116, 101, 9, 9]);
  let calledUrl = null;
  let calledInit = null;
  const fetchImpl = async (url, init) => {
    calledUrl = url;
    calledInit = init;
    return stubResp({ ok: true, found: true, filename: 'math-flu_K1_2026-06-12.sqlite', sessionCount: 4, base64: bytesToBase64(bytes) });
  };
  const r = await loadLatestUserDb({ fetchImpl, folder: 'real', user: 'Kid1' });
  assert.equal(r.ok, true);
  assert.equal(r.found, true);
  assert.equal(r.filename, 'math-flu_K1_2026-06-12.sqlite');
  assert.equal(r.sessionCount, 4);
  assert.deepEqual([...r.bytes], [...bytes]);
  assert.match(calledUrl, /folder=real&user=Kid1/);
  assert.equal(calledInit && calledInit.cache, 'no-store');
});

test('loadLatestUserDb passes through internal problemLists (defaulting to [])', async () => {
  const lists = [{ problem_list_id: 7, list_order: 1, list_name: 'A', retain: 0, items: [] }];
  const withLists = await loadLatestUserDb({
    fetchImpl: async () => stubResp({ ok: true, found: true, filename: 'f.sqlite', sessionCount: 1, problemLists: lists, base64: '' }),
    folder: 'real', user: 'K2',
  });
  assert.deepEqual(withLists.problemLists, lists);
  const without = await loadLatestUserDb({
    fetchImpl: async () => stubResp({ ok: true, found: true, filename: 'f.sqlite', sessionCount: 1, base64: '' }),
    folder: 'real', user: 'K2',
  });
  assert.deepEqual(without.problemLists, []);   // older server / no lists -> empty array
});

test('loadLatestUserDb reports found:false (new user) without bytes', async () => {
  const fetchImpl = async () => stubResp({ ok: true, found: false });
  const r = await loadLatestUserDb({ fetchImpl, folder: 'real', user: 'NewKid' });
  assert.equal(r.ok, true);
  assert.equal(r.found, false);
  assert.equal(r.bytes, undefined);
});

test('loadLatestUserDb degrades to found:false when the dev server is unreachable', async () => {
  const fetchImpl = async () => { throw new Error('ECONNREFUSED'); };
  const r = await loadLatestUserDb({ fetchImpl, folder: 'real', user: 'Kid1' });
  assert.equal(r.ok, false);
  assert.equal(r.found, false);
  assert.ok(r.error);
});

test('loadLatestUserDb requires a user', async () => {
  const r = await loadLatestUserDb({ fetchImpl: async () => stubResp({}), folder: 'real', user: '' });
  assert.equal(r.found, false);
});

// countSessions against a real engine (skipped when sql.js is absent).
let SQL = null;
try {
  const { readFileSync } = await import('node:fs');
  const initSqlJs = (await import('sql.js')).default;
  const wasmBinary = readFileSync(new URL('./node_modules/sql.js/dist/sql-wasm.wasm', import.meta.url));
  SQL = await initSqlJs({ wasmBinary });
} catch { /* sql.js not installed */ }
const dbTest = (name, fn) => test(name, { skip: SQL ? false : 'sql.js not installed (run npm install in apps/math-quiz/tests)' }, fn);

dbTest('countSessions counts only the named user', () => {
  const db = new SQL.Database();
  db.run('CREATE TABLE Sessions (session_id TEXT, user_name TEXT)');
  db.run("INSERT INTO Sessions VALUES ('a','Kid1'),('b','Kid1'),('c','Randy')");
  assert.equal(countSessions(db, 'Kid1'), 2);
  assert.equal(countSessions(db, 'Randy'), 1);
  assert.equal(countSessions(db, 'Nobody'), 0);
  db.close();
});
