// Session persistence for the education applets (logic gates, counting
// creatures, ...). Signed-in users' sessions go to their account via the
// user-data API; guests fall back to the fofGuest.* local store, which already
// migrates into a new account on sign-up. This replaces applet-telemetry's
// dev-only localhost flush endpoint — when the applet branch lands, point its
// flush at saveAppletSession(applet, session).
import { isProbablySignedIn } from './auth-hint.js';
import { setGuestItem } from './guest-store.js';

export function sessionKeyFor(session, at = new Date()) {
  // Stable per session (applet-telemetry's session_id or start stamp), so
  // repeated flushes of a live session upsert one entry instead of piling up.
  const stamp = String(session?.session_id || session?.stamp || session?.start_stamp || at.toISOString())
    .replace(/[^a-zA-Z0-9_.-]/g, '-');
  return `session-${stamp}`.slice(0, 64);
}

export async function saveAppletSession(applet, session, { storage, signedIn = isProbablySignedIn() } = {}) {
  const key = sessionKeyFor(session);
  if (signedIn) {
    const { saveUserData } = await import('./user-data.js');
    await saveUserData(applet, key, session);
    return { stored: 'account', key };
  }
  setGuestItem(applet, key, session, ...(storage ? [storage] : []));
  return { stored: 'guest', key };
}
