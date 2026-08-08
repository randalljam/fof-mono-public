// Local-only learner aliases: canonical code id -> on-disk name (also the UI label).
// dragon/data/display_names.json is gitignored; the dev server auto-creates it from
// display_names.example.json on first use when missing.
let cache = null;
export async function loadDisplayNames() {
  if (cache) return cache;
  try {
    const r = await fetch('/api/dragon-display-names');
    const j = await r.json();
    cache = (j && j.ok && j.names) ? j.names : {};
  } catch {
    cache = {};
  }
  return cache;
}
/** Friendly label for screens (and on-disk name when it differs from the code id). */
export function displayName(userId, names) {
  if (!userId) return '';
  const map = names || cache || {};
  return map[userId] || userId;
}
/** Name used in local SQLite / dragon save files. Same map as displayName. */
export function dataUser(userId, names) {
  return displayName(userId, names);
}
