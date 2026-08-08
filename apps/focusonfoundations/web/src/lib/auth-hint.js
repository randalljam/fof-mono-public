// Cheap "is someone signed in?" check without loading the Amplify bundle:
// Amplify records the last authenticated user in localStorage under the app
// client's key. Used by the header, QRAG persistence, and app-storage libs to
// decide whether account features apply before importing any heavy auth code.
import { AUTH_CONFIG, isAuthConfigured } from './auth-config.js';

export function isProbablySignedIn(storage = typeof localStorage !== 'undefined' ? localStorage : null) {
  if (!storage || !isAuthConfigured()) return false;
  return Boolean(
    storage.getItem(`CognitoIdentityServiceProvider.${AUTH_CONFIG.userPoolClientId}.LastAuthUser`)
  );
}
