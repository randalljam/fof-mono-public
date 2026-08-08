// Account sync for education apps that keep their data as an in-browser SQLite
// database (sql.js / SQLite-WASM), like math quiz's IndexedDB "working DB".
// The whole database file is the unit of sync: push after local saves, pull on
// startup. Integration recipe (math-quiz shape):
//
//   const sync = createSqliteSync('math-quiz', 'working.sqlite');
//   // startup: prefer the account copy when it's newer than the local one
//   const remote = await sync.pull();                 // Uint8Array | null
//   if (remote) db = new SQL.Database(remote);
//   // after each local persist:
//   await sync.push(db.export());                     // Uint8Array
//
// All functions require a signed-in session (the user-data API rejects
// otherwise); call isProbablySignedIn() first to keep guests offline-only.
import { downloadUserFile, listUserFiles, uploadUserFile } from './user-files.js';
export { isProbablySignedIn } from './auth-hint.js';

export function createSqliteSync(app, name) {
  return {
    /** Latest account copy of the database file, or null if none saved yet. */
    pull: () => downloadUserFile(app, name),
    /** Save the database file (Uint8Array from db.export()) to the account. */
    push: (bytes) => uploadUserFile(app, name, bytes),
    /** {size, updatedAt} of the account copy without downloading it, or null. */
    remoteInfo: async () => {
      const files = await listUserFiles(app);
      return files.find((file) => file.name === name) || null;
    },
  };
}
