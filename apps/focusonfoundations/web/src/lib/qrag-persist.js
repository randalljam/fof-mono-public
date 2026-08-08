// Saves QRAG exchanges to the signed-in user's account (phase 2 cutover step:
// signed-in users get chat history; guests are untouched). Uses the same
// no-bundle signed-in hint as the header so demo pages never load Amplify for
// anonymous visitors; the real client is imported only when a save happens.
export { isProbablySignedIn } from './auth-hint.js';
import { isProbablySignedIn } from './auth-hint.js';

export function buildChatEntry(demoId, question, response, at) {
  return {
    key: `chat-${at.replace(/[:.]/g, '-')}`,
    value: { demo: demoId, question, response, at },
  };
}

export async function saveQragChatIfSignedIn(demoId, question, response) {
  if (!isProbablySignedIn()) return false;
  try {
    const { saveUserData, isUserDataApiConfigured } = await import('./user-data.js');
    if (!isUserDataApiConfigured()) return false;
    const entry = buildChatEntry(demoId, question, response, new Date().toISOString());
    await saveUserData('qrag', entry.key, entry.value);
    return true;
  } catch (error) {
    // History is a bonus — never let it interfere with showing the answer.
    console.warn('QRAG chat save skipped:', error?.message || error);
    return false;
  }
}
