import assert from 'node:assert/strict';
import test from 'node:test';

function makeFakeStorage() {
  const map = new Map();
  return {
    get length() {
      return map.size;
    },
    key(index) {
      return [...map.keys()][index] ?? null;
    },
    getItem(key) {
      return map.has(key) ? map.get(key) : null;
    },
    setItem(key, value) {
      map.set(key, String(value));
    },
    removeItem(key) {
      map.delete(key);
    },
  };
}

test('guest store round-trips values under the fofGuest namespace', async () => {
  const {
    setGuestItem, getGuestItem, guestKey, listGuestEntries, hasGuestData,
  } = await import('../src/lib/guest-store.js');
  const storage = makeFakeStorage();
  assert.equal(hasGuestData(storage), false);
  setGuestItem('qrag', 'chat-draft', { question: 'What is knowledge?' }, storage);
  setGuestItem('math-quiz', 'progress', { level: 3 }, storage);
  assert.equal(guestKey('qrag', 'chat-draft'), 'fofGuest.qrag.chat-draft');
  assert.deepEqual(getGuestItem('qrag', 'chat-draft', storage), { question: 'What is knowledge?' });
  assert.equal(hasGuestData(storage), true);
  const entries = listGuestEntries(storage);
  assert.equal(entries.length, 2);
  assert.deepEqual(
    entries.find((e) => e.app === 'math-quiz'),
    { app: 'math-quiz', key: 'progress', value: { level: 3 } }
  );
});

test('guest store ignores non-namespaced keys and clears only its own', async () => {
  const { setGuestItem, listGuestEntries, clearGuestData } = await import('../src/lib/guest-store.js');
  const storage = makeFakeStorage();
  storage.setItem('privacyConsent', 'yes');
  setGuestItem('qrag', 'chat', ['hello'], storage);
  assert.equal(listGuestEntries(storage).length, 1);
  clearGuestData(storage);
  assert.equal(listGuestEntries(storage).length, 0);
  assert.equal(storage.getItem('privacyConsent'), 'yes');
});

test('getGuestItem returns null for missing or corrupt values', async () => {
  const { getGuestItem } = await import('../src/lib/guest-store.js');
  const storage = makeFakeStorage();
  assert.equal(getGuestItem('qrag', 'missing', storage), null);
  storage.setItem('fofGuest.qrag.bad', '{not json');
  assert.equal(getGuestItem('qrag', 'bad', storage), null);
});

test('migration without a registered handler keeps guest data pending', async () => {
  const { setGuestItem, migrateGuestDataToAccount, listGuestEntries } = await import(
    '../src/lib/guest-store.js'
  );
  const storage = makeFakeStorage();
  setGuestItem('logic-gates', 'progress', { stage: 2 }, storage);
  const result = await migrateGuestDataToAccount('user-123', storage);
  assert.deepEqual(result, { migrated: 0, cleared: false, pending: 1 });
  assert.equal(listGuestEntries(storage).length, 1);
});

test('migration with a handler uploads entries then clears the namespace', async () => {
  const {
    setGuestItem, registerGuestMigration, migrateGuestDataToAccount, hasGuestData,
  } = await import('../src/lib/guest-store.js');
  const storage = makeFakeStorage();
  setGuestItem('counting-creatures', 'state', { creatures: 7 }, storage);
  const uploads = [];
  registerGuestMigration(async (userId, entries) => {
    uploads.push({ userId, entries });
  });
  const result = await migrateGuestDataToAccount('user-abc', storage);
  registerGuestMigration(null);
  assert.deepEqual(result, { migrated: 1, cleared: true });
  assert.equal(uploads.length, 1);
  assert.equal(uploads[0].userId, 'user-abc');
  assert.equal(uploads[0].entries[0].app, 'counting-creatures');
  assert.equal(hasGuestData(storage), false);
});
