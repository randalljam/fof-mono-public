// Load sql.js in Node from the tests/ package (the only npm-managed folder in
// this app). Used by the dragon playthrough apparatus; fails with a clear
// message when tests/node_modules is absent.
import { readFileSync } from 'node:fs';

let cached = null;
export async function loadSqlJs() {
  if (cached) return cached;
  try {
    const mod = await import('../tests/node_modules/sql.js/dist/sql-wasm.js');
    const initSqlJs = mod.default;
    const wasmBinary = readFileSync(new URL('../tests/node_modules/sql.js/dist/sql-wasm.wasm', import.meta.url));
    cached = await initSqlJs({ wasmBinary });
    return cached;
  } catch (e) {
    throw new Error(`sql.js unavailable — run \`npm install\` in apps/math-quiz/tests first (${e.message})`);
  }
}
