// C1 tests — the write-mode switch (JSON on/off gate).
import test from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_WRITE_MODE, isValidWriteMode, shouldWriteJson, shouldWriteSqlite, createSessionWriter } from '../engine/write_mode.mjs';

test('dev default is sqlite-only', () => {
  assert.equal(DEFAULT_WRITE_MODE, 'sqlite-only');
});

test('shouldWrite* truth table', () => {
  assert.equal(shouldWriteSqlite('sqlite-only'), true);
  assert.equal(shouldWriteJson('sqlite-only'), false);
  assert.equal(shouldWriteSqlite('json+sqlite'), true);
  assert.equal(shouldWriteJson('json+sqlite'), true);
  assert.equal(shouldWriteSqlite('json-only'), false);
  assert.equal(shouldWriteJson('json-only'), true);
  assert.equal(isValidWriteMode('nope'), false);
});

function spyWriter(mode) {
  const calls = { json: 0, sqlite: 0 };
  const writer = createSessionWriter({
    mode,
    writeJson: async () => { calls.json++; },
    writeSqlite: async () => { calls.sqlite++; },
  });
  return { writer, calls };
}

test('sqlite-only writes SQLite, no JSON (default dev behavior)', async () => {
  const { writer, calls } = spyWriter('sqlite-only');
  const out = await writer.writeSession({ session: { id: 's1' } }, 's1.json');
  assert.deepEqual(calls, { json: 0, sqlite: 1 });
  assert.deepEqual(out, { json: false, sqlite: true });
});

test('json+sqlite writes both', async () => {
  const { writer, calls } = spyWriter('json+sqlite');
  await writer.writeSession({ session: { id: 's1' } }, 's1.json');
  assert.deepEqual(calls, { json: 1, sqlite: 1 });
});

test('json-only writes JSON, no SQLite', async () => {
  const { writer, calls } = spyWriter('json-only');
  const out = await writer.writeSession({ session: { id: 's1' } }, 's1.json');
  assert.deepEqual(calls, { json: 1, sqlite: 0 });
  assert.deepEqual(out, { json: true, sqlite: false });
});

test('invalid write mode throws', () => {
  assert.throws(() => createSessionWriter({ mode: 'bogus' }), /Unknown write mode/);
});
