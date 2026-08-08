import assert from 'node:assert/strict';
import test from 'node:test';

test('parseProviders splits and trims a comma list', async () => {
  const { parseProviders } = await import('../src/lib/auth-config.js');
  assert.deepEqual(parseProviders('Google, Facebook'), ['Google', 'Facebook']);
  assert.deepEqual(parseProviders(''), []);
  assert.deepEqual(parseProviders(null), []);
  assert.deepEqual(parseProviders('Google,,'), ['Google']);
});

test('isAuthConfigured is false for placeholder or missing ids', async () => {
  const { isAuthConfigured } = await import('../src/lib/auth-config.js');
  assert.equal(
    isAuthConfigured({ userPoolId: 'PENDING_DEPLOY', userPoolClientId: 'PENDING_DEPLOY' }),
    false
  );
  assert.equal(isAuthConfigured({ userPoolId: '', userPoolClientId: '' }), false);
  assert.equal(
    isAuthConfigured({ userPoolId: 'us-west-2_AbCdEfGhI', userPoolClientId: 'PENDING_DEPLOY' }),
    false
  );
});

test('isAuthConfigured is true for real-looking ids', async () => {
  const { isAuthConfigured } = await import('../src/lib/auth-config.js');
  assert.equal(
    isAuthConfigured({
      userPoolId: 'us-west-2_AbCdEfGhI',
      userPoolClientId: '1234567890abcdefghijklmnop',
    }),
    true
  );
});

test('selectAuthEnv maps production hostnames to production, all else to staging', async () => {
  const { selectAuthEnv } = await import('../src/lib/auth-config.js');
  assert.equal(selectAuthEnv('focusonfoundations.org'), 'production');
  assert.equal(selectAuthEnv('www.focusonfoundations.org'), 'production');
  assert.equal(selectAuthEnv('staging.focusonfoundations.org'), 'staging');
  assert.equal(selectAuthEnv('localhost'), 'staging');
  assert.equal(selectAuthEnv(''), 'staging');
});

test('non-browser default resolves to the deployed staging pool', async () => {
  const { AUTH_CONFIG, isAuthConfigured } = await import('../src/lib/auth-config.js');
  assert.equal(AUTH_CONFIG.authEnv, 'staging');
  assert.equal(isAuthConfigured(AUTH_CONFIG), true);
  assert.match(AUTH_CONFIG.userPoolId, /^us-west-2_/);
  assert.deepEqual(AUTH_CONFIG.socialProviders, []);
});
