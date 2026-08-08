import assert from 'node:assert/strict';
import test from 'node:test';

test('buildUserDataRequest builds authorized JSON requests', async () => {
  const { buildUserDataRequest } = await import('../src/lib/user-data.js');
  const put = buildUserDataRequest('https://api.example.com', 'tok123', 'PUT', '/user/data/qrag/chat-1', { value: { a: 1 } });
  assert.equal(put.url, 'https://api.example.com/user/data/qrag/chat-1');
  assert.equal(put.options.method, 'PUT');
  assert.equal(put.options.headers.Authorization, 'Bearer tok123');
  assert.equal(put.options.headers['Content-Type'], 'application/json');
  assert.deepEqual(JSON.parse(put.options.body), { value: { a: 1 } });

  const get = buildUserDataRequest('https://api.example.com', 'tok123', 'GET', '/user/data');
  assert.equal(get.options.body, undefined);
  assert.equal(get.options.headers['Content-Type'], undefined);
});

test('isUserDataApiConfigured is false for placeholder and true for real urls', async () => {
  const { isUserDataApiConfigured } = await import('../src/lib/user-data.js');
  assert.equal(isUserDataApiConfigured({ userDataApiUrl: 'PENDING_DEPLOY' }), false);
  assert.equal(isUserDataApiConfigured({ userDataApiUrl: '' }), false);
  assert.equal(isUserDataApiConfigured({ userDataApiUrl: 'https://x.execute-api.us-west-2.amazonaws.com' }), true);
});

test('buildChatEntry produces a valid key and self-describing value', async () => {
  const { buildChatEntry } = await import('../src/lib/qrag-persist.js');
  const entry = buildChatEntry('submitBot_deutsch', 'What is knowledge?', { answer: '42' }, '2026-07-17T12:34:56.789Z');
  assert.equal(entry.key, 'chat-2026-07-17T12-34-56-789Z');
  assert.match(entry.key, /^[a-z0-9][a-z0-9_.-]{0,63}$/i);
  assert.deepEqual(entry.value, {
    demo: 'submitBot_deutsch',
    question: 'What is knowledge?',
    response: { answer: '42' },
    at: '2026-07-17T12:34:56.789Z',
  });
});

test('isProbablySignedIn reads the Cognito localStorage marker', async () => {
  const { isProbablySignedIn } = await import('../src/lib/qrag-persist.js');
  const { AUTH_CONFIG } = await import('../src/lib/auth-config.js');
  const fake = new Map();
  const storage = { getItem: (k) => (fake.has(k) ? fake.get(k) : null) };
  assert.equal(isProbablySignedIn(storage), false);
  fake.set(`CognitoIdentityServiceProvider.${AUTH_CONFIG.userPoolClientId}.LastAuthUser`, 'user-1');
  assert.equal(isProbablySignedIn(storage), true);
  assert.equal(isProbablySignedIn(null), false);
});
