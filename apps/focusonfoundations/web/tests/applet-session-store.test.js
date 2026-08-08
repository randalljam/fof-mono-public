import assert from 'node:assert/strict';
import test from 'node:test';

function makeFakeStorage() {
  const map = new Map();
  return {
    get length() { return map.size; },
    key(index) { return [...map.keys()][index] ?? null; },
    getItem(key) { return map.has(key) ? map.get(key) : null; },
    setItem(key, value) { map.set(key, String(value)); },
    removeItem(key) { map.delete(key); },
  };
}

test('sessionKeyFor uses the session stamp, sanitized to a valid name', async () => {
  const { sessionKeyFor } = await import('../src/lib/applet-session-store.js');
  assert.equal(
    sessionKeyFor({ session_id: 'logic-gates_anon_2026-07-12_101530', start_stamp: 'x' }),
    'session-logic-gates_anon_2026-07-12_101530'
  );
  assert.equal(sessionKeyFor({ stamp: '2026-07-17_183000' }), 'session-2026-07-17_183000');
  assert.equal(sessionKeyFor({ start_stamp: '2026-07-17_090000' }), 'session-2026-07-17_090000');
  assert.equal(sessionKeyFor({ stamp: 'a b/c:d' }), 'session-a-b-c-d');
  const fallback = sessionKeyFor({}, new Date('2026-07-17T18:30:00.000Z'));
  assert.equal(fallback, 'session-2026-07-17T18-30-00.000Z');
  assert.match(fallback, /^[a-z0-9][a-z0-9_.-]{0,63}$/i);
});

test('signed-out sessions go to the guest store for later migration', async () => {
  const { saveAppletSession } = await import('../src/lib/applet-session-store.js');
  const { getGuestItem } = await import('../src/lib/guest-store.js');
  const storage = makeFakeStorage();
  const session = { stamp: '2026-07-17_120000', applet: 'logic-gates', events: [{ type: 'start' }] };
  const result = await saveAppletSession('logic-gates', session, { storage, signedIn: false });
  assert.equal(result.stored, 'guest');
  assert.equal(result.key, 'session-2026-07-17_120000');
  assert.deepEqual(getGuestItem('logic-gates', result.key, storage), session);
});
