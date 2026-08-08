// Cross-device handoff: one owner at a time, server checkpoint in dragon-sync/.
import { deviceType, transferTargetType, transferButtonLabel } from './device.js';
import { hydrateFromCheckpoint } from './sim/game_state.js';

const DEVICE_KEY = 'dragon-handoff-device-id';
const TOKEN_KEY_PREFIX = 'dragon-handoff-token::';
const REV_KEY_PREFIX = 'dragon-handoff-rev::';

function storageKey(prefix, folder, user) {
  return `${prefix}${folder}::${user}`;
}

export function getDeviceId() {
  try {
    let id = localStorage.getItem(DEVICE_KEY);
    if (!id) {
      id = (typeof crypto !== 'undefined' && crypto.randomUUID)
        ? crypto.randomUUID()
        : `dev-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      localStorage.setItem(DEVICE_KEY, id);
    }
    return id;
  } catch {
    return `ephemeral-${Date.now()}`;
  }
}

async function apiGet(folder, user, deviceId) {
  const q = new URLSearchParams({
    folder, user, deviceId, deviceType: deviceType(),
  });
  const r = await fetch(`/api/dragon-handoff?${q}`);
  return r.json();
}

async function apiPost(body) {
  const r = await fetch('/api/dragon-handoff', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return r.json();
}

export function createHandoffManager({ folder, user, onOwnershipLost, onStatusChange }) {
  const deviceId = getDeviceId();
  let ownerToken = null;
  let revision = 0;
  let isOwner = false;
  let inactiveReason = null;
  let checkpointTimer = null;
  let pollTimer = null;
  let buildCheckpoint = null;
  let pendingSave = false;

  function loadLocalTokens() {
    try {
      ownerToken = localStorage.getItem(storageKey(TOKEN_KEY_PREFIX, folder, user));
      const rev = localStorage.getItem(storageKey(REV_KEY_PREFIX, folder, user));
      revision = rev ? Number(rev) : 0;
    } catch {
      ownerToken = null;
      revision = 0;
    }
  }
  function persistLocalTokens() {
    try {
      if (ownerToken) localStorage.setItem(storageKey(TOKEN_KEY_PREFIX, folder, user), ownerToken);
      else localStorage.removeItem(storageKey(TOKEN_KEY_PREFIX, folder, user));
      localStorage.setItem(storageKey(REV_KEY_PREFIX, folder, user), String(revision || 0));
    } catch { /* private mode */ }
  }
  function notify() {
    if (onStatusChange) onStatusChange(getStatus());
  }
  function getStatus() {
    return {
      isOwner, inactiveReason, revision, deviceId, deviceType: deviceType(),
      transferLabel: transferButtonLabel(), transferTarget: transferTargetType(),
    };
  }
  function applyAuth(result) {
    if (result.ownerToken) ownerToken = result.ownerToken;
    if (result.revision != null) revision = result.revision;
    if (result.isOwner != null) isOwner = !!result.isOwner;
    persistLocalTokens();
  }
  async function fetchStatus() {
    const st = await apiGet(folder, user, deviceId);
    if (!st.ok) return st;
    isOwner = !!st.isOwner;
    revision = st.revision || revision;
    inactiveReason = st.inactiveReason || null;
    if (st.owner && st.owner.deviceId === deviceId && st.owner.token) {
      ownerToken = st.owner.token;
      persistLocalTokens();
    }
    notify();
    return st;
  }
  function hydrateFromServerCheckpoint(gs, localState, checkpoint) {
    if (!checkpoint || !checkpoint.gameState) {
      return {
        ok: true, state: localState, pose: null, pendingQuiz: null,
      };
    }
    const hydrated = hydrateFromCheckpoint(checkpoint.gameState, user);
    gs.save(hydrated);
    return {
      ok: true,
      state: hydrated,
      pose: checkpoint.pose || null,
      pendingQuiz: checkpoint.pendingQuiz || null,
    };
  }
  async function bootstrap(localState, gs, { handoffResume = false } = {}) {
    loadLocalTokens();
    const st = await fetchStatus();
    if (!st.ok) return { ok: false, error: st.error || 'handoff unavailable', state: localState };
    if (st.canClaim) {
      const claimed = await apiPost({
        action: 'claim', folder, user, deviceId, deviceType: deviceType(),
      });
      if (claimed.ok && claimed.checkpoint) {
        applyAuth(claimed);
        isOwner = true;
        inactiveReason = null;
        notify();
        const hydrated = hydrateFromServerCheckpoint(gs, localState, claimed.checkpoint);
        return Object.assign(hydrated, { claimed: true });
      }
    }
    if (!st.found) {
      const checkpoint = buildCheckpoint ? buildCheckpoint(localState) : { gameState: localState, pose: null, pendingQuiz: null };
      const init = await apiPost({
        action: 'initialize', folder, user, deviceId, deviceType: deviceType(), checkpoint,
      });
      if (init.ok) {
        applyAuth(init);
        isOwner = true;
        inactiveReason = null;
        notify();
        return { ok: true, state: localState, initialized: true };
      }
    }
    if (st.isOwner) {
      isOwner = true;
      inactiveReason = null;
      if (st.owner && st.owner.token) {
        ownerToken = st.owner.token;
        persistLocalTokens();
      }
      notify();
      // Always hydrate world state; Go-quiz only on explicit handoff resume
      // (ordinary hard refresh must not dump the player back onto Go!).
      const hydrated = hydrateFromServerCheckpoint(gs, localState, st.checkpoint);
      if (!handoffResume) hydrated.pendingQuiz = null;
      return Object.assign(hydrated, { owner: true });
    }
    inactiveReason = st.inactiveReason || 'other_device';
    isOwner = false;
    notify();
    return { ok: true, state: localState, inactive: true, reason: inactiveReason };
  }
  function scheduleCheckpoint() {
    pendingSave = true;
    if (checkpointTimer) return;
    checkpointTimer = setTimeout(flushCheckpoint, 800);
  }
  async function flushCheckpoint(explicitCheckpoint) {
    checkpointTimer = null;
    if (!isOwner || !ownerToken) return;
    if (!explicitCheckpoint && !pendingSave) return;
    if (!explicitCheckpoint && !buildCheckpoint) return;
    pendingSave = false;
    const checkpoint = explicitCheckpoint || buildCheckpoint();
    if (!checkpoint) return;
    const out = await apiPost({
      action: 'checkpoint', folder, user, deviceId, deviceType: deviceType(),
      ownerToken, revision, checkpoint,
    });
    if (out.ok) {
      applyAuth(out);
      notify();
    } else if (out.error && out.error.includes('stale')) {
      isOwner = false;
      inactiveReason = 'other_device';
      if (onOwnershipLost) onOwnershipLost(getStatus());
      notify();
    }
  }
  function cancelPendingFlush() {
    pendingSave = false;
    if (checkpointTimer) {
      clearTimeout(checkpointTimer);
      checkpointTimer = null;
    }
  }
  function attachCheckpoint(fn) {
    buildCheckpoint = fn;
  }
  function onLocalSave(state) {
    if (!isOwner) return;
    scheduleCheckpoint();
  }
  async function transfer(checkpoint) {
    if (!isOwner || !ownerToken) return { ok: false, error: 'not owner' };
    cancelPendingFlush();
    const out = await apiPost({
      action: 'transfer', folder, user, deviceId, deviceType: deviceType(),
      ownerToken, revision, checkpoint,
      targetDeviceType: transferTargetType(),
    });
    if (out.ok) {
      isOwner = false;
      ownerToken = null;
      revision = out.revision || revision;
      inactiveReason = 'transferred';
      persistLocalTokens();
      notify();
    }
    return out;
  }
  async function takeOver() {
    // Prefer claiming a pending transfer aimed at this device — that keeps the
    // sender's checkpoint (including pendingQuiz). Never upload this device's
    // local world over a quiz waiting on the server.
    const st = await fetchStatus();
    if (st.canClaim) {
      const claimed = await apiPost({
        action: 'claim', folder, user, deviceId, deviceType: deviceType(),
      });
      if (claimed.ok) {
        applyAuth(claimed);
        isOwner = true;
        inactiveReason = null;
        notify();
      }
      return claimed;
    }
    const out = await apiPost({
      action: 'takeover', folder, user, deviceId, deviceType: deviceType(),
      confirm: true,
      // omit checkpoint — keep whatever the server already has
    });
    if (out.ok) {
      applyAuth(out);
      isOwner = true;
      inactiveReason = null;
      notify();
    }
    return out;
  }
  function startPolling() {
    stopPolling();
    pollTimer = setInterval(async () => {
      if (!isOwner) return;
      const before = isOwner;
      await fetchStatus();
      if (before && !isOwner && onOwnershipLost) onOwnershipLost(getStatus());
    }, 5000);
  }
  /** While frozen on Transferred: watch for an incoming transfer aimed at us and auto-claim. */
  function startInactivePolling(onIncomingTransfer) {
    stopPolling();
    pollTimer = setInterval(async () => {
      const st = await fetchStatus();
      if (st && st.ok && (st.canClaim || st.isOwner)) {
        stopPolling();
        if (onIncomingTransfer) onIncomingTransfer(st);
      }
    }, 1500);
  }
  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }
  return {
    bootstrap, attachCheckpoint, onLocalSave, transfer, takeOver, fetchStatus,
    startPolling, startInactivePolling, stopPolling, flushCheckpoint, getStatus,
    isOwner: () => isOwner,
    inactiveReason: () => inactiveReason,
    transferLabel: transferButtonLabel,
  };
}

export function createHandoffOverlay() {
  let root = document.getElementById('handoff-overlay');
  if (!root) {
    root = document.createElement('div');
    root.id = 'handoff-overlay';
    root.className = 'handoff-overlay hidden';
    document.body.appendChild(root);
  }
  function showLoading(msg) {
    root.className = 'handoff-overlay';
    root.innerHTML = `<div class="handoff-card"><h2>Syncing…</h2><p>${msg || 'Loading your dragon game…'}</p></div>`;
  }
  function showInactive({ reason, transferLabel, onRefresh, onTakeOver }) {
    // Shown only on the device that sent a transfer (or lost ownership).
    // Incoming transfers auto-claim — they never need this card.
    root.className = 'handoff-overlay';
    const where = reason === 'transferred'
      ? (deviceType() === 'touch' ? 'your laptop' : 'your iPad or phone')
      : 'another device';
    root.innerHTML = `
      <div class="handoff-card">
        <h2>Transferred</h2>
        <p>This game moved to ${where}. When they transfer back, this screen picks it up automatically. Or tap Take over here to play on this device now.</p>
        <div class="handoff-actions">
          <!-- Kept for easy re-enable; hidden in CSS (.handoff-refresh-btn). -->
          <button type="button" class="hud-btn handoff-refresh-btn" id="handoff-refresh">Refresh status</button>
          <button type="button" class="hud-btn" id="handoff-takeover">Take over here</button>
        </div>
        <p class="handoff-hint">Normal play uses <strong>${typeof transferLabel === 'function' ? transferLabel() : transferLabel}</strong> from the device that owns the game.</p>
      </div>`;
    root.querySelector('#handoff-refresh').addEventListener('click', () => onRefresh && onRefresh());
    root.querySelector('#handoff-takeover').addEventListener('click', () => { onTakeOver && onTakeOver(); });
  }
  function hide() {
    root.classList.add('hidden');
    root.innerHTML = '';
  }
  return { showLoading, showInactive, hide, root };
}
