// Shared client SQLite I/O for the math-quiz pages (anchor + analysis): base64 <-> bytes
// and the dev-server "latest per-person DB" load, so both pages share one round-trip
// instead of re-implementing it. DOM-free and fetch-injectable for Node unit tests.
// Source of truth for accumulation is the dev server's per-person file (SPEC §8); the
// browser loads it via /api/latest-user-db (tools/dev_server.py) and treats it as a
// read-back of the canonical record.

export function bytesToBase64(bytes) {
  let bin = '';
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}
export function base64ToBytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

// Fetch the learner's most-recent per-person DB from the dev server ("Continue latest").
// Returns { ok, found, filename?, sessionCount?, bytes?, error? } and NEVER throws: a
// missing dev server (no sidecar), a network error, or a bad response all resolve to
// { ok:false, found:false, error } so callers can fall back to local/browser data.
// `fetchImpl` is injectable for tests; defaults to the global fetch.
// Pick which DB bytes to hydrate into IndexedDB after /api/latest-user-db.
// Prefer the local copy when it already has more sessions than the server
// response — that happens when a cached/stale latest-user-db would otherwise
// wipe a quiz that was saved in this browser but not yet visible to the fetch.
export function chooseHydrationBytes({ serverBytes, serverSessionCount, localBytes, localSessionCount } = {}) {
  const serverCount = Number(serverSessionCount) || 0;
  const localCount = Number(localSessionCount) || 0;
  if (!serverBytes) {
    if (!localBytes) return { bytes: null, source: 'none', sessionCount: 0 };
    return { bytes: localBytes, source: 'local', sessionCount: localCount };
  }
  if (localBytes && localCount > serverCount) {
    return { bytes: localBytes, source: 'local-newer', sessionCount: localCount };
  }
  return { bytes: serverBytes, source: 'server', sessionCount: serverCount };
}

export async function loadLatestUserDb({ fetchImpl, folder, user, file } = {}) {
  const doFetch = fetchImpl || (typeof fetch === 'function' ? fetch : null);
  if (!doFetch) return { ok: false, found: false, error: 'no fetch available' };
  if (!user) return { ok: false, found: false, error: 'user required' };
  let resp;
  try {
    let url = `/api/latest-user-db?folder=${encodeURIComponent(folder || 'real')}&user=${encodeURIComponent(user)}`;
    if (file) url += `&file=${encodeURIComponent(file)}`;
    // Bypass HTTP cache: without this, Continue after a hard refresh can hydrate a
    // pre-quiz snapshot and the fluency start% drops back to the previous value.
    resp = await doFetch(url, { cache: 'no-store' });
  } catch {
    return { ok: false, found: false, error: 'dev server unreachable' };   // no sidecar — fall back
  }
  if (!resp || !resp.ok) return { ok: false, found: false, error: `http ${resp && resp.status}` };
  let j;
  try { j = await resp.json(); } catch { return { ok: false, found: false, error: 'bad json' }; }
  if (!j || !j.ok) return { ok: false, found: false, error: (j && j.error) || 'server error' };
  if (!j.found) return { ok: true, found: false };
  return {
    ok: true, found: true, filename: j.filename, sessionCount: j.sessionCount,
    problemLists: Array.isArray(j.problemLists) ? j.problemLists : [],   // internal lists ("Use internal")
    targetedConfig: j.targetedConfig || null,                           // targeted-practice config (targets/filler/params)
    visualConfig: j.visualConfig || null,                               // visual-practice config (targets/filler/params)
    fluencyFeast: j.fluencyFeast || null,                               // saved Fluency-feast preset (count/session/mix)
    profile: (j.profile && typeof j.profile === 'object') ? j.profile : null,  // per-file profile flags (e.g. showFluencyPercent)
    quickPractice: (j.quickPractice && typeof j.quickPractice === 'object') ? j.quickPractice : {},  // auto-generated quick-quiz sets ({op: [items]})
    bytes: j.base64 ? base64ToBytes(j.base64) : null,
  };
}

// Count one user's sessions in a live sql.js Database (post-load confirmation / lock).
export function countSessions(db, user) {
  try {
    const res = db.exec('SELECT COUNT(*) FROM Sessions WHERE user_name = ?', [user]);
    return res.length ? res[0].values[0][0] : 0;
  } catch { return 0; }
}
