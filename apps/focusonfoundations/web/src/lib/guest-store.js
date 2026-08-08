// Guest-mode storage: unauthenticated work lives in localStorage under the
// fofGuest. namespace so it survives the browser session and can migrate into
// an account at sign-up ("you won't lose what you do here"). Storage is
// injectable for tests; browser code uses the default window.localStorage.
const NAMESPACE = 'fofGuest.';

export const GUEST_NOTICE =
  'You are in guest mode — your work is saved locally in this browser. ' +
  'If you decide to create an account, you won’t lose what you do here.';

function defaultStorage() {
  return typeof localStorage !== 'undefined' ? localStorage : null;
}
export function guestKey(app, key) {
  return `${NAMESPACE}${app}.${key}`;
}
export function setGuestItem(app, key, value, storage = defaultStorage()) {
  if (!storage) return false;
  storage.setItem(guestKey(app, key), JSON.stringify(value));
  return true;
}
export function getGuestItem(app, key, storage = defaultStorage()) {
  if (!storage) return null;
  const raw = storage.getItem(guestKey(app, key));
  if (raw === null) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}
export function removeGuestItem(app, key, storage = defaultStorage()) {
  if (!storage) return;
  storage.removeItem(guestKey(app, key));
}
export function listGuestEntries(storage = defaultStorage()) {
  if (!storage) return [];
  const entries = [];
  for (let i = 0; i < storage.length; i += 1) {
    const storageKey = storage.key(i);
    if (!storageKey || !storageKey.startsWith(NAMESPACE)) continue;
    const [app, ...rest] = storageKey.slice(NAMESPACE.length).split('.');
    let value = null;
    try {
      value = JSON.parse(storage.getItem(storageKey));
    } catch {
      value = null;
    }
    entries.push({ app, key: rest.join('.'), value });
  }
  return entries;
}
export function hasGuestData(storage = defaultStorage()) {
  return listGuestEntries(storage).length > 0;
}
export function clearGuestData(storage = defaultStorage()) {
  if (!storage) return;
  const doomed = [];
  for (let i = 0; i < storage.length; i += 1) {
    const storageKey = storage.key(i);
    if (storageKey && storageKey.startsWith(NAMESPACE)) doomed.push(storageKey);
  }
  doomed.forEach((storageKey) => storage.removeItem(storageKey));
}

// Migration hook: runs once after the first sign-in following account creation.
// Phase 1 registers no uploader (there is no user-data API yet), so guest data
// simply stays local — nothing is lost. Phase 2 registers an uploader that
// writes entries to the user's DynamoDB partition, then clears the namespace.
let migrationHandler = null;
export function registerGuestMigration(handler) {
  migrationHandler = handler;
}
export async function migrateGuestDataToAccount(userId, storage = defaultStorage()) {
  const entries = listGuestEntries(storage);
  if (!entries.length) return { migrated: 0, cleared: false };
  if (!migrationHandler) return { migrated: 0, cleared: false, pending: entries.length };
  await migrationHandler(userId, entries);
  clearGuestData(storage);
  return { migrated: entries.length, cleared: true };
}
