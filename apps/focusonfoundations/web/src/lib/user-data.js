// Client for the user-data API (API Gateway HTTP API + Cognito JWT authorizer).
// The signed-in user's ID token authorizes every call; the server scopes all
// reads/writes to that user's partition. auth.js is imported lazily so this
// module stays cheap to load (and unit-testable) without the Amplify bundle.
import { AUTH_CONFIG } from './auth-config.js';

const PLACEHOLDER = 'PENDING_DEPLOY';

export function isUserDataApiConfigured(config = AUTH_CONFIG) {
  return Boolean(config.userDataApiUrl) && config.userDataApiUrl !== PLACEHOLDER;
}

// Pure request builder, unit-tested without network or Amplify.
export function buildUserDataRequest(baseUrl, token, method, path, body) {
  return {
    url: `${baseUrl}${path}`,
    options: {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    },
  };
}

export async function callUserDataApi(method, path, body) {
  return callApi(method, path, body);
}

async function callApi(method, path, body) {
  if (!isUserDataApiConfigured()) {
    throw new Error('User-data API is not configured for this environment.');
  }
  const { getIdToken } = await import('./auth.js');
  const token = await getIdToken();
  if (!token) {
    throw new Error('Not signed in.');
  }
  const { url, options } = buildUserDataRequest(AUTH_CONFIG.userDataApiUrl, token, method, path, body);
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `User-data API error (${response.status})`);
  }
  return data;
}

export async function listUserData(app) {
  const query = app ? `?app=${encodeURIComponent(app)}` : '';
  const data = await callApi('GET', `/user/data${query}`);
  return data.entries;
}
export async function saveUserData(app, key, value) {
  const data = await callApi('PUT', `/user/data/${encodeURIComponent(app)}/${encodeURIComponent(key)}`, { value });
  return data.saved;
}
export async function deleteUserData(app, key) {
  await callApi('DELETE', `/user/data/${encodeURIComponent(app)}/${encodeURIComponent(key)}`);
}
export async function migrateGuestEntries(entries) {
  const payload = entries.map(({ app, key, value }) => ({ app, key, value }));
  return callApi('POST', '/user/migrate', { entries: payload });
}
export async function deleteAccount() {
  return callApi('DELETE', '/user/account');
}
