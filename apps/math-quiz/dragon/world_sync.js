// Canonical world save: full gameState on the dev-server disk
// (_data/<folder>/dragon-world/<user>.json). Mirrors localStorage so another
// computer on the same LAN server loads the same gems / signs / nest.
import { hydrateFromCheckpoint } from './sim/game_state.js';

function worldProgressScore(state) {
  if (!state || typeof state !== 'object') return 0;
  const stations = state.stations || {};
  const signs = stations.signs || {};
  const levels = stations.levels || {};
  const signChars = Object.values(signs).reduce((n, v) => n + String(v || '').trim().length, 0);
  const levelSum = Object.values(levels).reduce((n, v) => n + (Number(v) || 0), 0);
  const volcano = state.volcano || {};
  const lava = state.lava || {};
  const stopped = Array.isArray(lava.stopped) ? lava.stopped.length : 0;
  return (
    (Number(state.gems) || 0)
    + (Number(state.totalBursts) || 0) * 3
    + Math.round(Number(state.maxPct) || 0)
    + signChars * 2
    + levelSum * 25
    + (Number(volcano.cleared) || 0) * 15
    + (volcano.summited ? 20 : 0)
    + stopped * 12
    + (state.dragonName ? 10 : 0)
    + (Array.isArray(state.seenBeatIds) ? state.seenBeatIds.length : 0)
  );
}
export async function fetchDragonWorld(folder, user) {
  try {
    const q = new URLSearchParams({ folder, user });
    const r = await fetch(`/api/dragon-world?${q}`);
    const j = await r.json();
    if (j && j.ok && j.found && j.gameState) return j.gameState;
  } catch { /* offline */ }
  return null;
}
export async function pushDragonWorld(folder, user, gameState) {
  try {
    const r = await fetch('/api/dragon-world', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder, user, gameState }),
    });
    return r.json();
  } catch {
    return { ok: false, error: 'unreachable' };
  }
}
// Pick the richer of localStorage vs server world file, hydrate through the
// normal migration path, and return { state, fromServer, pushed }.
export async function syncWorldOnBoot(folder, user, localState, gs) {
  const serverRaw = await fetchDragonWorld(folder, user);
  const localScore = worldProgressScore(localState);
  if (!serverRaw) {
    if (localScore > 0) await pushDragonWorld(folder, user, localState);
    return { state: localState, fromServer: false, pushed: localScore > 0 };
  }
  const serverState = hydrateFromCheckpoint(serverRaw, user);
  const serverScore = worldProgressScore(serverState);
  if (serverScore > localScore) {
    gs.save(serverState);
    return { state: serverState, fromServer: true, pushed: false };
  }
  if (localScore > serverScore) {
    await pushDragonWorld(folder, user, localState);
    return { state: localState, fromServer: false, pushed: true };
  }
  // Tie: keep local, still refresh the disk copy so timestamps stay current.
  await pushDragonWorld(folder, user, localState);
  return { state: localState, fromServer: false, pushed: true };
}
export function createWorldSync({ folder, user }) {
  let timer = null;
  let pending = null;
  function schedule(state) {
    pending = state;
    if (timer) return;
    timer = setTimeout(flush, 600);
  }
  async function flush() {
    timer = null;
    const state = pending;
    pending = null;
    if (!state) return;
    await pushDragonWorld(folder, user, state);
  }
  function cancel() {
    pending = null;
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  }
  return { schedule, flush, cancel };
}
export { worldProgressScore };
