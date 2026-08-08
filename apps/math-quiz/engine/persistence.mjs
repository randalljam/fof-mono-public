// C2 — persistence adapters for the per-user SQLite store. The store computes
// in-memory (sql.js) for speed; an adapter persists the exported bytes between
// visits. Two implementations share one async contract:
//   load(username)        -> Promise<Uint8Array|null>
//   save(username, bytes) -> Promise<void>
// See 2026-06-15_assess-practice-modes-spec-and-plan.md §7a / Part C (C2).

// In-memory adapter (tests, and a fallback). Keeps bytes in a Map.
export function createMemoryPersistence(initial = {}) {
  const store = new Map(Object.entries(initial));
  return {
    async load(username) { return store.has(username) ? store.get(username) : null; },
    async save(username, bytes) { store.set(username, bytes); },
    has(username) { return store.has(username); },
  };
}

// Browser adapter: stores DB bytes keyed by username in IndexedDB. This is the
// seamless local-persistence path (no server, no auth). Not exercised in Node
// tests (no indexedDB) — the memory adapter proves the same contract, and the
// store's export/import round-trip proves byte fidelity.
export function createIndexedDbPersistence({ dbName = 'mathQuizUserStores', storeName = 'sqlite' } = {}) {
  function openIdb() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(dbName, 1);
      req.onupgradeneeded = () => req.result.createObjectStore(storeName);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  return {
    async load(username) {
      const idb = await openIdb();
      return new Promise((resolve, reject) => {
        const req = idb.transaction(storeName, 'readonly').objectStore(storeName).get(username);
        req.onsuccess = () => resolve(req.result ? new Uint8Array(req.result) : null);
        req.onerror = () => reject(req.error);
      });
    },
    async save(username, bytes) {
      const idb = await openIdb();
      return new Promise((resolve, reject) => {
        const tx = idb.transaction(storeName, 'readwrite');
        tx.objectStore(storeName).put(bytes, username);
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      });
    },
  };
}
