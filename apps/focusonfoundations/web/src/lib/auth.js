// Site auth library — thin wrapper around Amplify v6 modular auth backed by the
// FofAuth Cognito user pools. All account pages and the header widget go through
// this module; nothing else imports aws-amplify directly.
import { Amplify } from 'aws-amplify';
import {
  autoSignIn,
  confirmResetPassword,
  confirmSignIn,
  confirmSignUp,
  fetchAuthSession,
  fetchUserAttributes,
  getCurrentUser,
  resendSignUpCode,
  resetPassword,
  signIn,
  signInWithRedirect,
  signOut,
  signUp,
} from 'aws-amplify/auth';
import { Hub } from 'aws-amplify/utils';
import { AUTH_CONFIG, isAuthConfigured } from './auth-config.js';
import { clearGuestData, hasGuestData, listGuestEntries } from './guest-store.js';

let configured = false;
export function configureAuth() {
  if (configured || !isAuthConfigured()) return isAuthConfigured();
  const origin = window.location.origin;
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: AUTH_CONFIG.userPoolId,
        userPoolClientId: AUTH_CONFIG.userPoolClientId,
        loginWith: {
          email: true,
          oauth: {
            domain: AUTH_CONFIG.oauthDomain,
            scopes: ['openid', 'email', 'profile'],
            redirectSignIn: [`${origin}/account/callback/`],
            redirectSignOut: [`${origin}/`],
            responseType: 'code',
          },
        },
      },
    },
  });
  configured = true;
  return true;
}

export function availableSocialProviders() {
  return AUTH_CONFIG.socialProviders;
}

// --- Account creation and confirmation
export async function createAccount(email, password) {
  configureAuth();
  const result = await signUp({
    username: email,
    password,
    options: {
      userAttributes: { email },
      autoSignIn: true,
    },
  });
  return result.nextStep;
}
export async function confirmAccount(email, code) {
  configureAuth();
  const { nextStep } = await confirmSignUp({ username: email, confirmationCode: code });
  if (nextStep.signUpStep === 'COMPLETE_AUTO_SIGN_IN') {
    await autoSignIn();
    await runGuestMigration();
    return { signedIn: true };
  }
  return { signedIn: false };
}
export async function resendAccountCode(email) {
  configureAuth();
  await resendSignUpCode({ username: email });
}

// --- Sign in: password, emailed code, social
// If a different user is still signed in (stale session, shared computer),
// Amplify throws UserAlreadyAuthenticatedException — sign that session out and
// retry once instead of surfacing a confusing error.
async function signInClearingStaleSession(input) {
  try {
    return await signIn(input);
  } catch (error) {
    if (error?.name !== 'UserAlreadyAuthenticatedException') throw error;
    await signOut();
    clearPerUserUiCache();
    return signIn(input);
  }
}
export async function signInWithPassword(email, password) {
  configureAuth();
  const { isSignedIn, nextStep } = await signInClearingStaleSession({ username: email, password });
  if (isSignedIn) {
    clearPerUserUiCache();
    await runGuestMigration();
  }
  return { isSignedIn, nextStep };
}
export async function requestEmailCode(email) {
  configureAuth();
  const { nextStep } = await signInClearingStaleSession({
    username: email,
    options: { authFlowType: 'USER_AUTH', preferredChallenge: 'EMAIL_OTP' },
  });
  return nextStep;
}
export async function submitEmailCode(code) {
  configureAuth();
  const { isSignedIn } = await confirmSignIn({ challengeResponse: code });
  if (isSignedIn) {
    clearPerUserUiCache();
    await runGuestMigration();
  }
  return isSignedIn;
}
export async function signInWithProvider(provider) {
  configureAuth();
  await signInWithRedirect({ provider });
}

// --- Password reset
export async function requestPasswordReset(email) {
  configureAuth();
  const { nextStep } = await resetPassword({ username: email });
  return nextStep;
}
export async function completePasswordReset(email, code, newPassword) {
  configureAuth();
  await confirmResetPassword({ username: email, confirmationCode: code, newPassword });
}

// --- Session state
export async function getSessionInfo() {
  if (!configureAuth()) return { signedIn: false };
  try {
    const user = await getCurrentUser();
    let email = null;
    try {
      const attributes = await fetchUserAttributes();
      email = attributes.email || null;
    } catch {
      email = null;
    }
    return { signedIn: true, userId: user.userId, email };
  } catch {
    return { signedIn: false };
  }
}
export async function signOutUser() {
  configureAuth();
  await signOut();
  clearPerUserUiCache();
}
// Per-user UI caches (e.g. the family page's instant-render cache) must not
// leak across sign-out/sign-in on a shared browser.
function clearPerUserUiCache() {
  try {
    sessionStorage.removeItem('fofFamilyCache');
  } catch {
    // Storage may be unavailable; caches are best-effort anyway.
  }
}
export function onAuthChange(callback) {
  return Hub.listen('auth', ({ payload }) => callback(payload.event));
}
export async function getIdToken() {
  configureAuth();
  try {
    const session = await fetchAuthSession();
    return session.tokens?.idToken?.toString() || null;
  } catch {
    return null;
  }
}
async function runGuestMigration() {
  // Best-effort upload of fofGuest.* work into the new account's partition;
  // guest data is only cleared locally after the server confirms the write.
  try {
    if (!hasGuestData()) return;
    const { migrateGuestEntries } = await import('./user-data.js');
    await migrateGuestEntries(listGuestEntries());
    clearGuestData();
  } catch (error) {
    console.warn('Guest data migration deferred:', error?.message || error);
  }
}
