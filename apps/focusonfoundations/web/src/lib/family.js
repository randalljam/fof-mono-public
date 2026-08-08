// Client for family accounts: guardian/child relations, per-app entitlements,
// and the guardian-consent child-account flow. All calls go through the
// JWT-authorized user-data API; the server re-checks roles on every request.
import { callUserDataApi } from './user-data.js';

export const COPPA_CONSENT_VERSION = '2026-07-18';
export const GUARDIAN_CONSENT_TEXT =
  'I am this child’s parent or legal guardian. I consent to Focus on Foundations ' +
  'creating this account and storing the child’s learning activity (app progress and ' +
  'session data) under our family account. I can review this data and can delete the ' +
  'account and all its data at any time from this page.';

// Mirrors the server's entitlement resolution for UI decisions only —
// authorization always happens server-side.
export function resolveEntitlement(profile, app) {
  const entitlements = profile?.entitlements || {};
  return entitlements[app] || entitlements['*'] || { analysis: false, analysisScope: 'own' };
}

export async function getProfile() {
  const data = await callUserDataApi('GET', '/user/profile');
  return data.profile;
}
export async function updateProfile(attrs) {
  const data = await callUserDataApi('PUT', '/user/profile', attrs);
  return data.profile;
}
export async function getFamily() {
  const data = await callUserDataApi('GET', '/family');
  return data.family;
}
export async function createFamily(name) {
  const data = await callUserDataApi('POST', '/family', { name });
  return data.familyId;
}
export async function createGuardianInvite({ email, message, ccSelf } = {}) {
  return callUserDataApi('POST', '/family/invites', { email, message, ccSelf });
}
export async function joinFamily(code) {
  return callUserDataApi('POST', '/family/join', { code });
}
export async function addChildAccount({ email, displayName, password, consentAgreed }) {
  return callUserDataApi('POST', '/family/children', {
    email,
    displayName,
    password,
    consent: { agreed: consentAgreed === true, version: COPPA_CONSENT_VERSION },
  });
}
export async function getMemberData(sub, app) {
  const query = app ? `?app=${encodeURIComponent(app)}` : '';
  return callUserDataApi('GET', `/family/member/${encodeURIComponent(sub)}/data${query}`);
}
export async function setChildEntitlements(sub, entitlements) {
  const data = await callUserDataApi('PUT', `/family/member/${encodeURIComponent(sub)}/entitlements`, { entitlements });
  return data.profile;
}
export async function deleteChildAccount(sub) {
  return callUserDataApi('DELETE', `/family/member/${encodeURIComponent(sub)}`, { deleteAccount: true });
}
export async function leaveFamily(ownSub) {
  return callUserDataApi('DELETE', `/family/member/${encodeURIComponent(ownSub)}`, {});
}
