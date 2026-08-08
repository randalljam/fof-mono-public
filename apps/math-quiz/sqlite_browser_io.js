// START OF FILE sqlite_browser_io.js
//
// Shared browser-side SQLite "working DB" helpers (IndexedDB). The analysis page
// is the canonical writer of this store (a loaded per-person .sqlite, retained
// across reloads); other pages — the fluency tracker — READ it so they show
// "whatever is loaded in analysis", and WRITE it when they load a file too, so
// the two pages stay in sync on the same per-person file.
//
// Plain <script> (no module): declared with var/function so the names attach to
// the global object. The analysis page still keeps its own private copy of these
// for now; the IndexedDB name/store/key match, so the stores are interchangeable.
//
// History (newest first):
//   2026-06-20 — added so the fluency tracker can load the same per-person
//                .sqlite the analysis page uses (shared File management).

var SHARED_WORKING_DB_IDB = { name: 'mathAnalysisWorkingDb', store: 'kv', key: 'current' };

function sharedWorkingDbOpen() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(SHARED_WORKING_DB_IDB.name, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(SHARED_WORKING_DB_IDB.store);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

// Returns the stored bytes (Uint8Array) for the current working DB, or null.
async function loadSharedWorkingDb() {
  try {
    const idb = await sharedWorkingDbOpen();
    const bytes = await new Promise((resolve, reject) => {
      const tx = idb.transaction(SHARED_WORKING_DB_IDB.store, 'readonly');
      const rq = tx.objectStore(SHARED_WORKING_DB_IDB.store).get(SHARED_WORKING_DB_IDB.key);
      rq.onsuccess = () => resolve(rq.result || null);
      rq.onerror = () => reject(rq.error);
    });
    idb.close();
    return bytes || null;
  } catch (e) { return null; }
}

// Persists the working DB bytes (so the analysis page picks up the same file).
async function saveSharedWorkingDb(bytes) {
  try {
    const idb = await sharedWorkingDbOpen();
    await new Promise((resolve, reject) => {
      const tx = idb.transaction(SHARED_WORKING_DB_IDB.store, 'readwrite');
      tx.objectStore(SHARED_WORKING_DB_IDB.store).put(bytes, SHARED_WORKING_DB_IDB.key);
      tx.oncomplete = resolve; tx.onerror = () => reject(tx.error);
    });
    idb.close();
  } catch (e) { console.warn('Could not persist shared working DB:', e); }
}
