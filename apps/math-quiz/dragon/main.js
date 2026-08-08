import * as THREE from 'three';
import { createScene } from './world/scene.js';
import { createControls } from './world/controls.js';
import { createEnvironment } from './world/environment.js';
import { createAmbient } from './world/ambient.js';
import { createMountains } from './world/mountains.js';
import { createBoulders } from './world/boulders.js';
import { createLavaStreams } from './world/lava_streams.js';
import { createZoomieFx } from './world/zoomie_fx.js';
import { createHomestead } from './world/homestead.js';
import { createCritters } from './world/critters.js';
import { createJourney } from './world/journey.js';
import { createEgg } from './world/egg.js';
import { createDragon } from './world/dragon.js';
import { createCameraDirector } from './world/camera_director.js';
import { createEffects } from './world/effects.js';
import { createFlight } from './world/flight.js';
import {
  initLearner, effectivePct, isServerRequired,
  buildBurst, finishBurst, refreshAttempts,
} from './quiz_bridge.js';
import { createBurst } from './sim/burst_session.js';
import { createGameState, cloneLocalGameState, isPastHatch } from './sim/game_state.js';
import { applyCameraPose, captureCameraPose } from './sim/camera_pose.js';
import {
  gamePageUrl as buildGamePageUrl, pendingQuizForBoot, resolveBootEntry, shouldAutoResumeHandoff,
} from './sim/boot_entry.js';
import { fluencyFeedbackForResult } from './sim/fluency_feedback.js';
import { MILESTONES, resolveMilestones, animRepertoireFor, dragonFormFor } from './sim/milestones.js';
import { atSummit, TOTAL_BOULDERS } from './sim/volcano_quest.js';
import { TOTAL_STREAMS, isStreamStopped, lavaActive } from './sim/lava_quest.js';
import {
  gemsForBurst, unlockedUpgrades, NEST_UPGRADES,
  dailyGiftAvailable, giftNote, DAILY_GIFT_GEMS, SUMMIT_BONUS_GEMS, LAVA_WIN_GEMS,
} from './sim/rewards.js';
import {
  ensureStations, resolveStationQuiz, stationLabel, setSignText, signText,
  fountainTier, growTier, GROW_IDS, SIGN_IDS, MAX_LEVEL, STATIONS_INTRO,
} from './sim/stations.js';
import {
  ZOOMIE_INTERVAL_S, zoomiesEligible, ensureZoomies, zoomieAlertFor,
  zoomiesIntroText, resolveZoomieQuiz, ZOOMIE_GRADUATION,
} from './sim/zoomies.js';
import {
  resolveGrowthSpurtQuiz, growthCameraMul,
} from './sim/growth_spurt.js';
import { createNestStations } from './world/nest_stations.js';
import { createSignOverlay } from './ui/sign_overlay.js';
import { createMapOverlay } from './ui/map_overlay.js';
import {
  nextStoryBeat, markBeatSeen, journalEntries, quizReaction, stoneBeatFor, formatDragonName,
} from './sim/story.js';
import { buildGmSnapshot } from './sim/gm_state.js';
import { createQuizOverlay } from './ui/quiz_overlay.js';
import { createHud } from './ui/hud.js';
import { createStoryOverlay } from './ui/story_overlay.js';
import { createHowTo } from './ui/howto.js';
import { createAudioManager } from './audio/audio.js';
import { createHandoffManager, createHandoffOverlay, getDeviceId } from './handoff.js';
import { transferButtonLabel, deviceType } from './device.js';
import { syncWorldOnBoot, createWorldSync, worldProgressScore } from './world_sync.js';
import { loadDisplayNames, displayName, dataUser } from './display_names.js';

function qs() { return new URLSearchParams(window.location.search); }
// Kid1 is the real kid — her live tlkids file, every quiz saved, no clone/restart UI.
// Randy (and other testers) pick at "Who's playing?" on every hard refresh.
// Handoff Continue/claim reloads with ?resume=1&user=… so the picker is skipped once.
const REAL_USER = 'Kid1';
const DEV_SERVER_PORT = 8907;
const PICKABLE_USERS = [REAL_USER, 'Randy'];
const LAST_USER_KEY = 'dragon-last-user';
const LAST_FOLDER_KEY = 'dragon-last-folder';
function rememberedLearner() {
  try {
    return {
      user: localStorage.getItem(LAST_USER_KEY) || '',
      folder: localStorage.getItem(LAST_FOLDER_KEY) || 'tlkids',
    };
  } catch {
    return { user: '', folder: 'tlkids' };
  }
}
function rememberLearner(user, folder) {
  try {
    localStorage.setItem(LAST_USER_KEY, user);
    localStorage.setItem(LAST_FOLDER_KEY, folder || 'tlkids');
  } catch { /* private mode */ }
}
/** Strip sticky ?user= / ?resume= so the next hard refresh shows Who's playing. */
function clearBootQueryParams() {
  try {
    const url = new URL(window.location.href);
    url.searchParams.delete('user');
    url.searchParams.delete('resume');
    if (url.searchParams.get('folder') === 'tlkids') url.searchParams.delete('folder');
    const q = url.searchParams.toString();
    history.replaceState({}, '', `${url.pathname}${q ? `?${q}` : ''}`);
  } catch { /* ignore */ }
}
function gamePageUrl(user, folder, { resume = false } = {}) {
  return buildGamePageUrl({
    user, folder, resume,
    hostname: window.location.hostname || '127.0.0.1',
    port: window.location.port || String(DEV_SERVER_PORT),
    pathname: '/dragon/index.html',
  });
}
function reloadForLearner(user, folder) {
  // resume=1 is one-shot: Take over here / claim reload skips the picker once.
  window.location.href = gamePageUrl(user, folder, { resume: true });
}
async function peekHandoffStatus(folder, user) {
  try {
    const q = new URLSearchParams({
      folder, user, deviceId: getDeviceId(), deviceType: deviceType(),
    });
    const r = await fetch(`/api/dragon-handoff?${q}`);
    return await r.json();
  } catch {
    return { ok: false };
  }
}
function setLoading(msg) {
  const el = document.getElementById('loading-status');
  if (el) el.textContent = msg;
}
function hideLoading() {
  document.getElementById('loading-screen')?.classList.add('hidden');
}
function showLoading() {
  document.getElementById('loading-screen')?.classList.remove('hidden');
}
function showServerError(reason, { user, folder } = {}) {
  const title = document.getElementById('server-error-title');
  const detail = document.getElementById('server-error-detail');
  const urlEl = document.getElementById('server-error-url');
  if (reason === 'file') {
    if (title) title.textContent = 'Open through the game server';
    if (detail) detail.textContent = 'This page was opened from a file on your computer. The dragon game needs the dev server so it can load your math file and save quiz results.';
  } else if (reason === 'wrong-origin') {
    if (title) title.textContent = 'Wrong server';
    if (detail) detail.textContent = `This page is on port ${window.location.port || '(default)'}, but the game server runs on port ${DEV_SERVER_PORT}. Use the link below instead of Live Preview or "Open in Browser".`;
  } else {
    if (title) title.textContent = 'Need the game server';
    if (detail) detail.textContent = 'Start the dev server, then open the game at the link below.';
  }
  if (urlEl) urlEl.textContent = gamePageUrl(user || REAL_USER, folder || 'tlkids');
  document.getElementById('server-error')?.classList.remove('hidden');
  hideLoading();
}
function showPlayerPicker(names) {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.id = 'player-picker';
    overlay.innerHTML = `
      <div class="start-choice-inner">
        <h2>Who's playing?</h2>
        <p>Pick your name to load your dragon game.</p>
        <div class="start-choice-buttons">
          ${PICKABLE_USERS.map((u) => `<button type="button" data-user="${escapeHtml(u)}">${escapeHtml(displayName(u, names))}</button>`).join('')}
        </div>
      </div>`;
    document.body.appendChild(overlay);
    hideLoading();
    overlay.querySelectorAll('button[data-user]').forEach((btn) => {
      btn.addEventListener('click', () => {
        overlay.remove();
        showLoading();
        resolve(btn.dataset.user);
      });
    });
  });
}
function showToast(msg, ms = 3500) {
  const t = document.createElement('div');
  t.className = 'milestone-toast';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), ms);
}
function timestamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}
function milestoneById(id) { return MILESTONES.find((m) => m.id === id); }

// Tester start choice (any user except the real kid): continue your own game, or
// clone the real kid's math file + browser game state over yours (boulders, signs,
// nest projects, story). Her file and her save are never touched.
// Resolves 'continue' | 'cloned'.
function showStartChoice(user, folder, names) {
  const realLabel = displayName(REAL_USER, names);
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.id = 'start-choice';
    const safeUser = escapeHtml(displayName(user, names));
    overlay.innerHTML = `
      <div class="start-choice-inner">
        <h2>Playing as ${safeUser}</h2>
        <p>Continue your own game, or copy ${escapeHtml(realLabel)}'s math file and dragon world onto yours.</p>
        <div class="start-choice-buttons">
          <button id="sc-continue">Continue my game</button>
          <button id="sc-clone">Clone ${escapeHtml(realLabel)}'s game</button>
        </div>
        <p id="sc-status" class="start-choice-status"></p>
      </div>`;
    document.body.appendChild(overlay);
    const status = overlay.querySelector('#sc-status');
    overlay.querySelector('#sc-continue').addEventListener('click', () => {
      overlay.remove();
      resolve('continue');
    });
    overlay.querySelector('#sc-clone').addEventListener('click', async () => {
      const sure = window.confirm(
        `This replaces ${displayName(user, names)}'s math file and dragon game save with copies of ${realLabel}'s `
        + `(fluency, boulders, signs, nest projects, story). ${realLabel}'s file and game `
        + `are not touched. Continue?`);
      if (!sure) return;
      status.textContent = 'Cloning…';
      try {
        const resp = await fetch('/api/clone-user-file', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ folder, sourceUser: REAL_USER, targetUser: user }),
        });
        const j = await resp.json();
        if (!j || !j.ok) {
          status.textContent = `Clone failed: ${(j && j.error) || 'server error'}`;
          return;
        }
        cloneLocalGameState(dataUser(REAL_USER, names), user);
        overlay.remove();
        resolve('cloned');
      } catch {
        status.textContent = 'Clone failed — is the game server running? (python3 tools/dev_server.py)';
      }
    });
  });
}

async function boot() {
  const container = document.getElementById('game-container');
  if (!container || !window.WebGLRenderingContext) {
    setLoading('This browser does not support WebGL.');
    return;
  }
  if (window.location.protocol === 'file:') {
    showServerError('file');
    return;
  }
  const displayNames = await loadDisplayNames();
  const dn = (userId) => displayName(userId, displayNames);
  const du = (userId) => dataUser(userId, displayNames);
  const remembered = rememberedLearner();
  const bootEntry = resolveBootEntry({
    urlUser: qs().get('user') || '',
    urlFolder: qs().get('folder') || '',
    urlResume: qs().get('resume') || '',
    rememberedUser: remembered.user,
    rememberedFolder: remembered.folder,
  });
  let folder = bootEntry.folder;
  let user = bootEntry.user;
  let handoffResume = bootEntry.handoffResume;
  if (bootEntry.needsPlayerPicker) {
    user = await showPlayerPicker(displayNames);
  }
  rememberLearner(user, folder);
  // Do not sticky-write ?user= into the address bar — that skipped the picker
  // on the next hard refresh. Drop resume/user now that boot consumed them.
  clearBootQueryParams();
  let justCloned = false;
  // Skip continue/clone only for an explicit handoff resume, or when a transfer
  // is waiting to claim (same learner, frozen world / Go quiz).
  const handoffPeek = await peekHandoffStatus(folder, user);
  const canClaimTransfer = !!(handoffPeek && handoffPeek.ok && handoffPeek.canClaim);
  const skipStartChoice = handoffResume || canClaimTransfer;
  if (user !== REAL_USER && !skipStartChoice) {
    justCloned = (await showStartChoice(user, folder, displayNames)) === 'cloned';
  }
  setLoading(`Loading ${dn(user)}…`);
  await initLearner({ folder, user, dataUser: du(user) });
  if (isServerRequired()) {
    const wrongPort = window.location.port && window.location.port !== String(DEV_SERVER_PORT);
    showServerError(wrongPort ? 'wrong-origin' : 'unreachable', { user, folder });
    return;
  }
  const gs = createGameState(user, { legacyLearner: du(user) });
  let state = gs.load();
  gs.updateHighWater(state, effectivePct());
  gs.reconcileHatchState(state);
  ensureStations(state);
  ensureZoomies(state);
  gs.save(state);

  const handoffOverlay = createHandoffOverlay();
  handoffOverlay.showLoading('Syncing your game…');
  // Canonical disk mirror of localStorage (gems/signs/nest) — runs before handoff
  // so a blank browser on another computer still loads her world from the server.
  const worldBoot = await syncWorldOnBoot(folder, user, state, gs);
  state = worldBoot.state;
  gs.updateHighWater(state, effectivePct());
  gs.reconcileHatchState(state);
  ensureStations(state);
  ensureZoomies(state);
  gs.save(state);
  const worldSync = createWorldSync({ folder, user });

  const handoff = createHandoffManager({
    folder, user,
    onOwnershipLost: () => { if (typeof enterInactiveMode === 'function') enterInactiveMode('other_device'); },
  });
  const bootHandoff = await handoff.bootstrap(state, gs, {
    handoffResume: handoffResume || canClaimTransfer,
  });
  if (bootHandoff.state) state = bootHandoff.state;
  // Handoff hydrate must not clobber a richer canonical world save (or vice versa).
  if (worldProgressScore(worldBoot.state) > worldProgressScore(state)) {
    state = worldBoot.state;
  }
  // File fluency is source of truth — bump maxPct after checkpoint hydrate so a
  // stale handoff/world blob cannot leave the progress bar one quiz behind.
  await refreshAttempts();
  gs.updateHighWater(state, effectivePct());
  gs.reconcileHatchState(state);
  ensureStations(state);
  ensureZoomies(state);
  gs.save(state);
  const savedHandoffPose = (handoffResume || bootHandoff.claimed) ? (bootHandoff.pose || null) : null;
  const savedHandoffQuiz = pendingQuizForBoot({
    pendingQuiz: bootHandoff.pendingQuiz || null,
    claimed: !!bootHandoff.claimed,
    handoffResume: handoffResume || !!bootHandoff.claimed,
  });
  // Keep the Go-gate quiz attached to checkpoints until the overlay is restored,
  // so an early world autosave cannot drop it from the server blob.
  let heldHandoffQuiz = savedHandoffQuiz;
  let inactiveMode = !!bootHandoff.inactive;
  handoffOverlay.hide();
  const _gsSave = gs.save.bind(gs);
  gs.save = (s) => {
    _gsSave(s);
    worldSync.schedule(s);   // always mirror full world to disk (any device)
    if (handoff.isOwner()) handoff.onLocalSave(s);
  };
  let controlsEnabled = true;
  let inQuiz = false;
  let pendingBoulder = false;
  let pendingLava = null;
  let pendingStation = null;
  let pendingZoomie = false;
  let zoomieActive = false;
  let zoomieTimer = ZOOMIE_INTERVAL_S;
  let summitCelebrating = false;
  let quiz = null;

  const audio = createAudioManager();
  await Promise.all([
    audio.load('correct', 'assets/audio/confirmation_001.ogg'),
    audio.load('wrong-soft', 'assets/audio/drop_001.ogg'),
    audio.load('click', 'assets/audio/click1.ogg'),
  ]);
  const muteBtn = document.createElement('button');
  muteBtn.id = 'mute-btn';
  muteBtn.textContent = state.muted ? '🔇' : '🔊';
  muteBtn.addEventListener('click', async () => {
    await audio.unlock();
    state.muted = !state.muted;
    audio.setMuted(state.muted);
    muteBtn.textContent = state.muted ? '🔇' : '🔊';
    gs.save(state);
  });
  document.body.appendChild(muteBtn);
  audio.setMuted(state.muted);

  setLoading('Building world…');
  const world = createScene(container);
  const env = createEnvironment(world.scene);
  env.showGates();
  const mountains = createMountains(world.scene);
  const ambient = createAmbient(world.scene, { nestPos: env.nest.position });
  const journey = createJourney(world.scene, { nestPos: env.nest.position });
  const boulders = createBoulders(world.scene, { nestPos: env.nest.position });
  const lavaStreams = createLavaStreams(world.scene, { nestPos: env.nest.position });
  const zoomieFx = createZoomieFx(world.scene);
  const homestead = createHomestead(world.scene, { nestPos: env.nest.position });
  const critters = createCritters(world.scene, { nestPos: env.nest.position });
  const nestStations = createNestStations(world.scene, {
    nestGroup: env.nest, trees: env.trees, nestPos: env.nest.position,
  });
  const signOverlay = createSignOverlay();
  // Daily gift: a balloon crate by the nest, once per calendar day. Opening it
  // is a click like everything else — gems, sparkles, and a rotating note.
  // (Built here, before interactable registration; handlers run post-boot.)
  const gift = new THREE.Group();
  {
    const crate = new THREE.Mesh(
      new THREE.BoxGeometry(0.9, 0.7, 0.9),
      new THREE.MeshStandardMaterial({ color: 0xd7a86e, roughness: 1 })
    );
    crate.position.y = 0.35;
    crate.castShadow = true;
    const lid = new THREE.Mesh(
      new THREE.BoxGeometry(1.0, 0.14, 1.0),
      new THREE.MeshStandardMaterial({ color: 0xb98a54, roughness: 1 })
    );
    lid.position.y = 0.75;
    gift.add(crate, lid);
    const balloonColors = [0xef5350, 0x42a5f5, 0xffca28];
    balloonColors.forEach((c, i) => {
      const b = new THREE.Mesh(
        new THREE.SphereGeometry(0.3, 8, 6),
        new THREE.MeshStandardMaterial({ color: c, roughness: 0.4 })
      );
      b.position.set((i - 1) * 0.45, 2.1 + (i % 2) * 0.3, (i % 2) * 0.3 - 0.15);
      b.scale.y = 1.15;
      gift.add(b);
      const string = new THREE.Mesh(
        new THREE.CylinderGeometry(0.012, 0.012, 1.35, 3),
        new THREE.MeshBasicMaterial({ color: 0xeeeeee })
      );
      string.position.set(b.position.x * 0.7, 1.35, b.position.z * 0.7);
      gift.add(string);
    });
    gift.position.set(4.2, 0, 2.2);
    world.scene.add(gift);
  }
  function refreshGiftVisibility() {
    gift.visible = state.eggFound && dailyGiftAvailable(state.lastGiftISO, new Date().toISOString());
  }
  function openDailyGift() {
    state.lastGiftISO = new Date().toISOString();
    state.giftsOpened = (state.giftsOpened || 0) + 1;
    gs.save(state);
    refreshGiftVisibility();
    effects.burstSparkles(gift.position.clone().add(new THREE.Vector3(0, 1, 0)), 0x81d4fa, 30);
    audio.play('milestone');
    showToast(`🎁 ${giftNote(state.giftsOpened - 1)}`, 6000);
    awardGems(DAILY_GIFT_GEMS);
    postGmState();
  }
  const egg = createEgg(world.scene, env.nest);
  // Egg build-up: cracks + faster pulse as the (hidden) hatch at 60% nears.
  function syncEggVisuals() {
    const pct = state.maxPct || 0;
    egg.setCrackStage(pct >= 55 ? 3 : pct >= 45 ? 2 : pct >= 30 ? 1 : 0);
    egg.setHatchCloseness(pct / 60);
    ambient.setEggMotes(!state.hatched);
  }
  const dragon = await createDragon(world.scene);
  // The nest base cylinder tops out at y=0.4 — spawn ON it, not inside it
  // (a baby-scaled dragon at y=0 is entirely buried in the nest mesh).
  const NEST_TOP_Y = 0.42;
  dragon.getRoot().position.set(env.nest.position.x, NEST_TOP_Y, env.nest.position.z);
  dragon.setForm(dragonFormFor(state.celebratedIds));
  dragon.setGrowthScale(state.maxPct || effectivePct());
  if (state.hatched) { egg.hide(); dragon.show(); dragon.playState('idle'); }
  const effects = createEffects(world.scene);
  const player = createControls(world.camera, world.renderer.domElement, { heightAt: mountains.heightAt });
  player.camera.position.set(2, 1.6, 4);
  const director = createCameraDirector(world.camera, player.controls);
  const flight = createFlight({
    camera: world.camera,
    dragon,
    heightAt: mountains.heightAt,
    nestPos: env.nest.position,
    nestTopY: NEST_TOP_Y,
    onDismount: () => {
      player.setFlightMode(false);
      player.setEnabled(true);
      player.beginFall();
      showToast('You jumped off! Press E near your dragon to fly again.');
    },
  });
  const howto = createHowTo();
  const story = createStoryOverlay({
    onName: (name) => {
      state.dragonName = formatDragonName(name);
      gs.save(state);
      hud.refresh();
      showToast(`${state.dragonName}! What a perfect name.`, 3500);
    },
  });
  const map = createMapOverlay();
  let enterInactiveMode = null;
  let doHandoffTransfer = null;
  function canTransferHandoff() {
    if (inactiveMode || !handoff.isOwner()) return false;
    // Quiz Go gate: allow transfer even though world controls are disabled.
    if (inQuiz && quiz && quiz.isAtGoGate()) return true;
    if (inQuiz) return false;
    if (director.isActive() || flight.isRiding() || summitCelebrating) return false;
    if (story.isOpen() || signOverlay.isOpen()) return false;
    return controlsEnabled;
  }
  function buildHandoffCheckpoint(currentState) {
    // YXZ yaw/pitch from quaternion — never camera.rotation.x/y (XYZ roll bug).
    const pose = player.camera ? captureCameraPose(player.camera) : null;
    let pendingQuiz = null;
    if (inQuiz && quiz && quiz.isAtGoGate()) {
      pendingQuiz = Object.assign({}, quiz.getPendingSnapshot(), {
        pendingBoulder, pendingLava, pendingStation, pendingZoomie,
      });
    } else if (heldHandoffQuiz) {
      pendingQuiz = heldHandoffQuiz;
    }
    return { gameState: currentState, pose, pendingQuiz };
  }
  function applyHandoffPose(pose) {
    if (!pose || !player) return;
    applyCameraPose(player.camera, pose);
  }
  enterInactiveMode = async (reason) => {
    inactiveMode = true;
    controlsEnabled = false;
    player.setEnabled(false);
    if (inQuiz && quiz) quiz.hide();
    inQuiz = false;
    const resumeHere = () => reloadForLearner(user, folder);
    const claimAndResume = async () => {
      handoffOverlay.showLoading('Picking up your game…');
      // Claim pending transfer (keeps quiz) or steal ownership without wiping
      // the server checkpoint. Never upload this device's empty local world.
      await handoff.takeOver();
      resumeHere();
    };
    const st = await handoff.fetchStatus();
    // Destination of a transfer: auto-claim — no Take over button.
    if (shouldAutoResumeHandoff(st)) {
      await claimAndResume();
      return;
    }
    // Source device (just transferred away): frozen card + poll so a transfer
    // back auto-resumes without tapping anything.
    handoffOverlay.showInactive({
      reason: st.inactiveReason || reason,
      transferLabel: transferButtonLabel(),
      onRefresh: async () => {
        handoffOverlay.showLoading('Checking for your game…');
        const again = await handoff.fetchStatus();
        if (again.canClaim || again.isOwner) await claimAndResume();
        else enterInactiveMode(again.inactiveReason || reason);
      },
      onTakeOver: claimAndResume,
    });
    handoff.startInactivePolling(async () => {
      await claimAndResume();
    });
  };
  doHandoffTransfer = async (pendingSnap) => {
    if (!canTransferHandoff()) return;
    // Refresh from the learner file before shipping the checkpoint so the
    // receiving device's progress bar matches disk fluency immediately.
    await refreshAttempts();
    gs.updateHighWater(state, effectivePct());
    gs.save(state);
    if (hud) hud.refresh();
    const cp = buildHandoffCheckpoint(state);
    const snap = pendingSnap || (quiz && quiz.isAtGoGate() ? quiz.getPendingSnapshot() : null);
    if (snap && Array.isArray(snap.items) && snap.items.length) {
      cp.pendingQuiz = {
        items: snap.items.map((item) => Object.assign({}, item)),
        atGoGate: true,
        pendingBoulder: !!pendingBoulder,
        pendingLava,
        pendingStation,
        pendingZoomie: !!pendingZoomie,
      };
    }
    const out = await handoff.transfer(cp);
    if (out.ok) {
      enterInactiveMode('transferred');
    } else {
      showToast(out.error || 'Could not transfer — try again.');
    }
  };
  const transferFn = () => doHandoffTransfer();
  transferFn.label = () => transferButtonLabel();
  const hud = createHud({
    getMaxPct: () => state.maxPct,
    getState: () => state,
    onHelp: () => howto.show(),
    onJournal: () => story.showJournal(journalEntries(state), state.dragonName),
    onMap: () => { if (!story.isOpen()) map.show(state); },
    onTransfer: transferFn,
    canTransfer: canTransferHandoff,
  });
  handoff.attachCheckpoint(() => buildHandoffCheckpoint(state));
  if (savedHandoffPose) applyHandoffPose(savedHandoffPose);

  // Dragon Gems: lifetime total; nest upgrades reveal themselves as it grows.
  function awardGems(n) {
    if (!n) return;
    const before = unlockedUpgrades(state.gems);
    state.gems = (state.gems || 0) + n;
    const after = unlockedUpgrades(state.gems);
    gs.save(state);
    hud.refresh();
    const revealedPos = homestead.syncUpgrades(after);
    const fresh = after.filter((id) => !before.includes(id));
    for (const id of fresh) {
      const u = NEST_UPGRADES.find((x) => x.id === id);
      if (u) showToast(u.reveal, 5000);
    }
    if (fresh.length) {
      effects.confetti();
      audio.play('milestone');
      for (const p of revealedPos) effects.burstSparkles(p, 0xffd54f, 28);
    }
    // Gems can raise the fountain's tier (the 140-gem reveal counts as tier 1).
    homestead.setFountainLevel(fountainTier(state));
    refreshStationLabels();
  }

  // Nest quiz stations: interact labels + world visuals derived from state.stations.
  const stationTargets = [];   // [{ id, obj }] — every registered clickable per station
  function refreshStationLabels() {
    for (const { id, obj } of stationTargets) obj.userData.interactLabel = stationLabel(state, id);
  }
  function syncStationVisuals() {
    homestead.showFountain();
    homestead.setFountainLevel(fountainTier(state));
    nestStations.applyLevels({ nest: growTier(state, 'nest'), trees: growTier(state, 'trees') });
    for (const id of SIGN_IDS) nestStations.setSignText(id, signText(state, id));
    refreshStationLabels();
  }

  // Game Master sync (best-effort — the game never depends on it): snapshots
  // out to the parent dashboard, letters back in through the story overlay.
  async function postGmState() {
    try {
      await fetch('/api/dragon-state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder, user, state: buildGmSnapshot({ state, pct: effectivePct(), user, folder }) }),
      });
    } catch { /* offline is fine */ }
  }
  let zoomieLineOverrides = null;
  let growthSpurtLineOverrides = null;
  async function refreshZoomieLines() {
    try {
      const r = await fetch(`/api/dragon-zoomies?folder=${encodeURIComponent(folder)}&user=${encodeURIComponent(user)}`);
      const o = await r.json();
      if (o && o.ok) zoomieLineOverrides = o.bands || null;
    } catch { /* offline: keep defaults */ }
  }
  async function refreshGrowthSpurtLines() {
    try {
      const r = await fetch(`/api/dragon-growth-spurt?folder=${encodeURIComponent(folder)}&user=${encodeURIComponent(user)}`);
      const o = await r.json();
      if (o && o.ok) growthSpurtLineOverrides = o.bands || null;
    } catch { /* offline: keep defaults */ }
  }
  async function fetchUnreadGmMessages() {
    try {
      const r = await fetch(`/api/dragon-messages?folder=${encodeURIComponent(folder)}&user=${encodeURIComponent(user)}&unread=1`);
      const j = await r.json();
      return (j && j.ok && j.messages) || [];
    } catch {
      return [];
    }
  }
  async function markGmMessagesRead(ids) {
    if (!ids.length) return;
    try {
      await fetch('/api/dragon-messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder, user, action: 'mark-read', ids }),
      });
    } catch { /* retried next poll */ }
  }

  let followDragon = false;
  let followMoving = false;
  let fireOnInteract = false;
  let jumpUnlocked = false;

  function syncDragonRepertoire() {
    dragon.setRepertoire(animRepertoireFor(state.celebratedIds));
  }
  function applyWorldChange(change) {
    if (change === 'follow') followDragon = true;
    if (change === 'wings') {
      dragon.setForm('juvenile');
      dragon.setGrowthScale(state.maxPct);
      env.unlockArea('meadow');
    }
    if (change === 'jump') {
      dragon.setForm('adult');
      dragon.setGrowthScale(state.maxPct);
      jumpUnlocked = true;
      env.unlockArea('hills');
      updateDragonLabel();
    }
    if (change === 'fire') { fireOnInteract = true; env.unlockArea('grove'); ambient.showFireflies(); updateDragonLabel(); }
    if (change === 'flight') {
      state.rideUnlocked = true;
      journey.lightBeacon();
      gs.save(state);
    }
    journey.refresh(state);
    syncDragonRepertoire();
  }
  function restoreHatchedVisuals() {
    egg.hide();
    dragon.show();
    dragon.playState('idle');
    if (!followDragon) {
      followDragon = true;
      applyWorldChange('follow');
    }
    syncDragonRepertoire();
    syncEggVisuals();
    registerDragonInteract();
    hud.refresh();
  }
  async function celebrateMilestone(id) {
    const m = milestoneById(id);
    if (!m) return;
    if (id === 'hatch') {
      if (isPastHatch(state)) {
        gs.reconcileHatchState(state);
        restoreHatchedVisuals();
        gs.save(state);
        return;
      }
      await playHatchCutscene();
      return;
    }
    controlsEnabled = false;
    player.setEnabled(false);
    effects.confetti();
    audio.play('milestone');
    showToast(m.revealText, 4000);
    if (m.dragonAnim) dragon.playState(m.dragonAnim);
    applyWorldChange(m.worldChange);
    let showZoomieGraduation = false;
    if (id === 'fire') {
      zoomieFx.stop();
      zoomieActive = false;
      pendingZoomie = false;
      ensureZoomies(state);
      if (!state.zoomies.graduated) {
        state.zoomies.graduated = true;
        showZoomieGraduation = true;
        gs.save(state);
      }
      effects.burstSparkles(dragon.headPosition(), 0xff7043, 24);
    }
    gs.markCelebrated(state, id);
    gs.save(state);
    hud.refresh();
    if (id === 'flight-ride') {
      await flight.playFlightCinematic(director, env.nest.position);
    }
    await director.runSequence([{ hold: 600 }]);
    if (showZoomieGraduation) {
      await story.showSequence([{
        kind: 'gm-message',
        from: formatDragonName(state.dragonName) || 'Pipa',
        text: ZOOMIE_GRADUATION,
      }]);
    }
    controlsEnabled = true;
    player.setEnabled(true);
  }
  // One reveal per burst-end (plan: queue crossings, celebrate one at a time so
  // every session has something to look forward to).
  async function processCelebrationQueue() {
    const pending = resolveMilestones(state.maxPct, state.celebratedIds);
    gs.queueCelebrations(state, pending.map((m) => m.id));
    const id = gs.popCelebration(state);
    gs.save(state);
    if (id) await celebrateMilestone(id);
  }
  async function playHatchCutscene() {
    controlsEnabled = false;
    player.setEnabled(false);
    const nest = env.nest.position;
    const eggEye = { x: nest.x, y: 1.2, z: nest.z };
    await director.runSequence([
      { moveTo: { x: nest.x, y: 2.2, z: nest.z + 4 }, lookAt: eggEye, duration: 1.2 },
      {
        lookAt: eggEye,
        onMid: async () => {
          await egg.playHatch(async () => {
            const flash = document.createElement('div');
            flash.style.cssText = 'position:fixed;inset:0;background:#fff;z-index:999;opacity:1;transition:opacity 0.6s';
            document.body.appendChild(flash);
            setTimeout(() => { flash.style.opacity = '0'; setTimeout(() => flash.remove(), 600); }, 100);
          });
          dragon.show();
          dragon.playOnce('hatch');
          audio.play('hatch');
          effects.confetti();
        },
      },
      { hold: 2800, lookAt: eggEye },
    ]);
    state.hatched = true;
    gs.markCelebrated(state, 'hatch');
    syncDragonRepertoire();
    applyWorldChange('follow');
    syncEggVisuals();
    gs.save(state);
    registerDragonInteract();
    hud.refresh();
    showToast('Your dragon hatched! Take good care of it.', 4500);
    controlsEnabled = true;
    player.setEnabled(true);
  }
  // After every burst: save, celebrate any milestone (cutscene first, so the
  // story beat that follows reflects the new phase), then the story sequence —
  // a reaction to the quiz plus the next scroll of the ongoing story.
  async function handleBurstEnd(kind, problems) {
    inQuiz = false;
    controlsEnabled = true;
    player.setEnabled(true);
    const wasBoulder = pendingBoulder;
    pendingBoulder = false;
    const wasLava = pendingLava;
    pendingLava = null;
    const wasStation = pendingStation;
    pendingStation = null;
    const wasZoomie = pendingZoomie;
    pendingZoomie = false;
    if (kind === 'quit-abandoned') {
      if (wasZoomie) {
        const r = resolveZoomieQuiz(state, kind, effectivePct(), formatDragonName(state.dragonName), zoomieLineOverrides);
        showToast(r.text, 4000);
        gs.save(state);
        return;
      }
      showToast('Session abandoned — nothing saved.');
      return;
    }
    if (!problems.length) {
      if (wasZoomie) {
        const r = resolveZoomieQuiz(state, kind, effectivePct(), formatDragonName(state.dragonName), zoomieLineOverrides);
        showToast(r.text, 4000);
        gs.save(state);
        return;
      }
      showToast('No problems answered — nothing saved. Try again any time!');
      return;
    }
    refreshZoomieLines();
    refreshGrowthSpurtLines();
    const result = await finishBurst(problems, kind);
    state.totalBursts += 1;
    state.lastPlayedISO = new Date().toISOString();
    const correct = problems.filter((p) => p.is_correct).length;
    // Re-read the learner file after save — finishBurst already refreshed once,
    // but a second pass catches any append lag so the progress bar cannot stay
    // a quiz behind the on-disk fluency %.
    if (result.saved) {
      await refreshAttempts();
      const livePct = effectivePct();
      result.newPct = livePct;
      gs.updateHighWater(state, livePct);
      if (state.hatched) {
        dragon.setForm(dragonFormFor(state.celebratedIds));
        dragon.setGrowthScale(state.maxPct);
      }
      syncEggVisuals();
      gs.pushRecentBurst(state, {
        ts: state.lastPlayedISO, correct, total: problems.length,
        pctBefore: Math.round(result.initialPct), pctAfter: Math.round(livePct),
      });
    } else {
      showToast('Could not save — is the game server running?');
    }
    gs.save(state);
    hud.refresh();
    const fluencyLine = fluencyFeedbackForResult(result);
    if (fluencyLine) showToast(fluencyLine, 5000);
    const earned = gemsForBurst({ correct, total: problems.length, kind });
    if (earned) {
      awardGems(earned);
      // Don't let the gems toast immediately replace the fluency readout.
      if (fluencyLine) setTimeout(() => showToast(`💎 +${earned} Dragon Gems!`, 3000), 5200);
      else showToast(`💎 +${earned} Dragon Gems!`, 3000);
    }
    if (wasBoulder) resolveBoulderBurst(kind);
    if (wasLava != null) resolveLavaBurst(wasLava, kind);
    if (wasStation) await resolveStationBurst(wasStation, kind);
    let zoomieStoryLine = null;
    if (wasZoomie) {
      const r = resolveZoomieQuiz(state, kind, effectivePct(), formatDragonName(state.dragonName), zoomieLineOverrides);
      if (r.calmed) {
        zoomieFx.stop();
        zoomieActive = false;
        zoomieTimer = ZOOMIE_INTERVAL_S;
        dragon.playState('idle');
        effects.burstSparkles(dragon.getRoot().position.clone().add(new THREE.Vector3(0, 0.6, 0)), 0x81d4fa, 26);
        audio.play('milestone');
        updateDragonLabel();
        gs.save(state);
        zoomieStoryLine = r.text;
      } else {
        showToast(r.text, 4000);
        gs.save(state);
      }
    }
    const hadFlightRide = state.celebratedIds.includes('flight-ride');
    await processCelebrationQueue();
    // The quiz that crosses 90% celebrates fire + graduation in the queue above;
    // the staged "almost there" calm line would read stale after it — drop it.
    if (zoomieStoryLine && state.celebratedIds.includes('fire')) zoomieStoryLine = null;
    let growthStoryLine = null;
    if (kind === 'list-complete') {
      const gr = resolveGrowthSpurtQuiz(
        state, kind, effectivePct(), formatDragonName(state.dragonName), growthSpurtLineOverrides,
      );
      if (gr.shown) {
        growthStoryLine = gr.text;
        gs.save(state);
      }
    }
    // The quiz that crosses 100% celebrates flight-ride — skip the growth letter.
    if (growthStoryLine && !hadFlightRide && state.celebratedIds.includes('flight-ride')) {
      growthStoryLine = null;
    }
    await showBurstStory(correct, problems.length, zoomieStoryLine || growthStoryLine);
    postGmState();
    if (handoff.isOwner() && !inactiveMode) {
      await quiz.showHandoffOffer({
        label: transferButtonLabel(),
        onTransfer: () => doHandoffTransfer(),
      });
    }
  }
  // A finished quiz smashes the lowest boulder — no performance requirement,
  // finishing the burst is the whole deal. Quitting early leaves it standing.
  function resolveBoulderBurst(kind) {
    if (kind !== 'list-complete') {
      showToast('The boulder wobbled… finish a whole quiz to smash it!');
      return;
    }
    const pos = boulders.clearNext();
    if (!pos) return;
    state.volcano.cleared = Math.min(TOTAL_BOULDERS, (state.volcano.cleared || 0) + 1);
    gs.save(state);
    effects.burstSparkles(pos, 0xff8a65, 30);
    effects.confetti();
    audio.play('milestone');
    showToast(state.volcano.cleared >= TOTAL_BOULDERS
      ? '💥 KA-BOOM! The last boulder is gone — race to the TOP of Mount Ember! 🌋'
      : `💥 KA-BOOM! Boulder smashed — ${state.volcano.cleared} of ${TOTAL_BOULDERS}! Keep climbing!`, 4500);
    hud.refresh();
  }
  // A finished quiz cools one lava stream — finish the burst or the lava keeps
  // flowing. All five cooled wins the chapter; lava never reaches the nest.
  function resolveLavaBurst(k, kind) {
    if (kind !== 'list-complete') {
      showToast('The lava kept flowing… finish a whole quiz to cool it!');
      return;
    }
    if (!state.lava) state.lava = { intro: true, startPct: null, stopped: [], won: false };
    if (isStreamStopped(state.lava.stopped, k)) return;
    const pos = lavaStreams.stopStream(k);
    if (!state.lava.stopped.includes(k)) state.lava.stopped.push(k);
    gs.save(state);
    if (pos) effects.burstSparkles(pos, 0x90caf9, 30);
    audio.play('milestone');
    const cooled = state.lava.stopped.length;
    if (cooled >= TOTAL_STREAMS) {
      state.lava.won = true;
      gs.save(state);
      lavaStreams.sync(state);
      effects.confetti();
      showToast(`The nest is safe! All ${TOTAL_STREAMS} lava streams cooled!`, 5000);
      awardGems(LAVA_WIN_GEMS);
      controlsEnabled = false;
      player.setEnabled(false);
      const name = formatDragonName(state.dragonName);
      story.showSequence([{
        kind: 'gm-message',
        from: 'Mama Dragon',
        text: `You did it, brave Keeper${name ? ` — you and ${name}` : ''}! Mount Ember rumbled, but your quiz-power cooled every stream before the lava could touch the nest. I am so proud. Rest a moment… then keep practicing — the road home is still waiting. — Mama D.`,
      }]).then(() => {
        controlsEnabled = true;
        player.setEnabled(true);
        hud.refresh();
        postGmState();
      });
    } else {
      showToast(`Stream cooled! ${cooled} of ${TOTAL_STREAMS} lava paths safe — hurry with the rest!`, 4500);
      hud.refresh();
    }
  }
  // A finished quiz at a nest station: signs open the writing dialog (rewrite
  // any time), grow stations level up once. Quitting early changes nothing.
  async function resolveStationBurst(stationId, kind) {
    const r = resolveStationQuiz(state, stationId, kind);
    if (!r.ok) {
      if (r.reason === 'incomplete') showToast('Almost! Finish a whole quiz to work on your nest project.');
      return;
    }
    if (r.kind === 'sign') {
      controlsEnabled = false;
      player.setEnabled(false);
      const text = await signOverlay.ask({
        current: signText(state, stationId),
        dragonName: formatDragonName(state.dragonName) || '',
        user: dn(user),
      });
      controlsEnabled = true;
      player.setEnabled(true);
      if (text != null) {
        setSignText(state, stationId, text);
        gs.save(state);
        nestStations.setSignText(stationId, signText(state, stationId));
        effects.burstSparkles(nestStations.signPosition(stationId), 0xffd54f, 26);
        audio.play('milestone');
        showToast('🪧 Your sign is painted!', 3000);
      }
    } else {
      gs.save(state);
      syncStationVisuals();
      effects.confetti();
      audio.play('milestone');
      const sparklePos = stationId === 'fountain'
        ? homestead.root.position.clone().add(homestead.fountainGroup.position).add(new THREE.Vector3(0, 1.2, 0))
        : nestStations.stationPosition(stationId);
      effects.burstSparkles(sparklePos, stationId === 'fountain' ? 0x81d4fa : 0xffd54f, 30);
      showToast(r.reveal, 5000);
    }
    refreshStationLabels();
    postGmState();
  }
  async function showBurstStory(correct, total, zoomieLine = null) {
    const items = [];
    if (zoomieLine) {
      items.push({
        kind: 'gm-message',
        from: formatDragonName(state.dragonName) || 'Pipa',
        text: zoomieLine,
      });
    }
    const reaction = quizReaction({
      correct, total, totalBursts: state.totalBursts, dragonName: state.dragonName,
    });
    if (reaction) items.push({ kind: 'reaction', text: reaction });
    const next = nextStoryBeat(state);
    if (next && !next.isRepeat) {
      items.push({ kind: 'beat', beat: next.beat, phase: next.phase });
      markBeatSeen(state, next.beat.id);
      gs.save(state);
    } else if (next) {
      items.push({ kind: 'beat', beat: next.beat, phase: next.phase });
    }
    const letters = await fetchUnreadGmMessages();
    for (const m of letters) {
      items.push({ kind: 'gm-message', from: m.from, text: m.text });
    }
    if (!items.length) return;
    controlsEnabled = false;
    player.setEnabled(false);
    await story.showSequence(items);
    controlsEnabled = true;
    player.setEnabled(true);
    markGmMessagesRead(letters.map((m) => m.id));
    hud.refresh();
  }
  quiz = createQuizOverlay({
    onComplete: handleBurstEnd,
    onQuit: handleBurstEnd,
    onCorrect: (streak) => {
      audio.play('correct');
      const n = streak >= 3 ? 20 : 8;
      effects.burstSparkles(dragon.getRoot().position.clone().add(new THREE.Vector3(0, 0.6, 0)), 0xa5d6a7, n);
      if (streak === 5) effects.confetti();
    },
    onWrong: () => audio.play('wrong-soft'),
    canTransfer: canTransferHandoff,
    onTransfer: {
      label: () => transferButtonLabel(),
      fn: async (snap) => { await doHandoffTransfer(snap); },
    },
  });
  async function startPractice() {
    await audio.unlock();
    audio.play('click');
    const { items } = buildBurst();
    if (!items.length) { showToast('No problems to practice yet.'); return false; }
    inQuiz = true;
    controlsEnabled = false;
    player.setEnabled(false);
    quiz.start(createBurst(items), timestamp());
    return true;
  }

  // Restore persisted unlocks BEFORE registering interactables so labels are right.
  if (state.hatched || state.celebratedIds.includes('hatch')) followDragon = true;
  if (state.celebratedIds.includes('wings')) env.unlockArea('meadow');
  if (state.celebratedIds.includes('jump')) { jumpUnlocked = true; env.unlockArea('hills'); }
  if (state.celebratedIds.includes('fire')) { fireOnInteract = true; env.unlockArea('grove'); ambient.showFireflies(); }
  if (state.hatched || state.celebratedIds.includes('hatch')) {
    dragon.setForm(dragonFormFor(state.celebratedIds));
    dragon.setGrowthScale(state.maxPct);
  }
  syncEggVisuals();
  journey.refresh(state);
  boulders.sync(state);
  lavaStreams.sync(state);
  lavaStreams.restoreProgressFromSave(state.lava);
  homestead.syncUpgrades(unlockedUpgrades(state.gems));
  syncDragonRepertoire();

  player.registerInteractable(egg.mesh, 'egg',
    state.eggFound ? 'Click to feed the egg (math!)' : 'Click to discover the egg');
  for (const s of journey.interactables()) {
    player.registerInteractable(s.mesh, `stone-${s.id}`, s.label);
  }
  for (const b of boulders.interactables()) {
    player.registerInteractable(b.mesh, `boulder-${b.k}`, b.label);
  }
  for (const s of lavaStreams.interactables()) {
    player.registerInteractable(s.mesh, `lava-${s.k}`, s.label);
  }
  player.registerInteractable(gift, 'gift', '🎁 Open your daily gift!');
  refreshGiftVisibility();
  // Nest quiz stations: the two signs, the fountain, the nest, and every tree
  // in the home ring answer to a quiz (labels refresh as they grow).
  for (const { id, group } of nestStations.signGroups()) {
    player.registerInteractable(group, `station-${id}`, stationLabel(state, id));
    stationTargets.push({ id, obj: group });
  }
  player.registerInteractable(homestead.fountainGroup, 'station-fountain', stationLabel(state, 'fountain'));
  stationTargets.push({ id: 'fountain', obj: homestead.fountainGroup });
  player.registerInteractable(env.nest, 'station-nest', stationLabel(state, 'nest'));
  stationTargets.push({ id: 'nest', obj: env.nest });
  for (const tree of env.trees) {
    player.registerInteractable(tree, 'station-trees', stationLabel(state, 'trees'));
    stationTargets.push({ id: 'trees', obj: tree });
  }
  syncStationVisuals();
  async function visitStone(stoneId) {
    const beat = stoneBeatFor(stoneId, state.dragonName);
    journey.markVisited(state, stoneId);
    markBeatSeen(state, beat ? beat.id : `stone-${stoneId}`);
    gs.save(state);
    effects.burstSparkles(journey.stonePosition(stoneId), 0x4dd0e1, 26);
    audio.play('milestone');
    hud.refresh();
    postGmState();
    if (beat) {
      controlsEnabled = false;
      player.setEnabled(false);
      await story.showSequence([{ kind: 'beat', beat, phase: { id: 'journey', title: 'The Dragon Road' } }]);
      controlsEnabled = true;
      player.setEnabled(true);
    }
  }
  function updateDragonLabel() {
    const name = formatDragonName(state.dragonName) || 'your dragon';
    dragon.getRoot().userData.interactLabel = zoomieActive
      ? `🌀 Click ${name} to stop the zoomie!`
      : fireOnInteract
      ? 'Click to practice (fire!)'
      : 'Click to practice math';
  }
  function registerDragonInteract() {
    player.registerInteractable(dragon.getRoot(), 'dragon', 'Click to practice math');
    updateDragonLabel();
  }
  if (state.hatched) registerDragonInteract();

  player.setInteractHandler(async (obj) => {
    await audio.unlock();
    const id = obj.userData.interactId || '';
    if (id === 'gift') {
      if (gift.visible) openDailyGift();
      return;
    }
    if (id.startsWith('station-')) {
      const stationId = id.slice('station-'.length);
      if (inQuiz) return;
      if (!state.eggFound) { showToast('Find the dragon egg first — then the nest projects open up!'); return; }
      if (GROW_IDS.includes(stationId) && growTier(state, stationId) >= MAX_LEVEL) {
        showToast(stationLabel(state, stationId));
        return;
      }
      pendingStation = (await startPractice()) ? stationId : null;
      return;
    }
    if (id.startsWith('lava-')) {
      const k = Number(id.slice('lava-'.length));
      if (inQuiz || !lavaStreams.isStreamActive(k)) return;
      pendingLava = k;
      const ok = await startPractice();
      if (!ok) pendingLava = null;
      return;
    }
    if (id.startsWith('boulder-')) {
      // Always smash bottom-up: whichever cluster was clicked, the quiz clears
      // the lowest one still standing (the only one the climb gate allows near).
      if (boulders.nextStage() == null || inQuiz) return;
      pendingBoulder = !!(await startPractice());
      return;
    }
    if (id.startsWith('stone-')) {
      const stoneId = id.slice('stone-'.length);
      if (!(state.visitedStones || []).includes(stoneId)) await visitStone(stoneId);
      return;
    }
    if (obj.userData.interactId === 'dragon') {
      if (flight.isRiding()) return;
      if (zoomieActive) {
        pendingZoomie = !!(await startPractice());
        return;
      }
      if (fireOnInteract) {
        effects.burstSparkles(dragon.headPosition(), 0xff7043, 20);
      }
      dragon.playState(jumpUnlocked ? 'jump' : 'play');
      startPractice();
      return;
    }
    if (obj.userData.interactId !== 'egg') return;
    if (!state.eggFound) {
      state.eggFound = true;
      gs.markCelebrated(state, 'egg-found');
      // The story hook: Mama Dragon's first letter is waiting under the egg
      // (shown beneath the how-to, revealed when the how-to closes).
      const first = nextStoryBeat(state);
      if (first) {
        markBeatSeen(state, first.beat.id);
        story.showSequence([{ kind: 'beat', beat: first.beat, phase: first.phase }]);
      }
      gs.save(state);
      howto.show();
      showToast('You found a dragon egg! Feed it with math quizzes and see what happens…');
      egg.mesh.userData.interactLabel = 'Click to feed the egg (math!)';
      hud.refresh();
      return;
    }
    startPractice();
  });

  // Companion play: F pets the dragon (hearts + wiggle), 1-4 perform whatever
  // tricks the milestone repertoire has unlocked. Near-the-dragon only.
  const TRICK_KEYS = { Digit1: 'play', Digit2: 'wing-stretch', Digit3: 'jump', Digit4: 'fire' };
  let lastPetAt = 0;
  window.addEventListener('keydown', (e) => {
    if (!state.hatched || inQuiz || director.isActive() || flight.isRiding() || !controlsEnabled) return;
    const root = dragon.getRoot();
    if (world.camera.position.distanceTo(root.position) > 7) return;
    if (e.code === 'KeyF') {
      const now = performance.now();
      if (now - lastPetAt < 1500) return;
      lastPetAt = now;
      dragon.playState('play');
      effects.burstSparkles(root.position.clone().add(new THREE.Vector3(0, 1.1, 0)), 0xff6b9d, 16);
      audio.play('correct');
      showToast(`${formatDragonName(state.dragonName) || 'Your dragon'} loves that! 💕`, 1800);
      return;
    }
    const trick = TRICK_KEYS[e.code];
    if (trick && animRepertoireFor(state.celebratedIds).includes(trick)) {
      dragon.playState(trick);
      if (trick === 'fire') effects.burstSparkles(dragon.headPosition(), 0xff7043, 22);
      if (trick === 'jump') effects.burstSparkles(root.position.clone().add(new THREE.Vector3(0, 0.4, 0)), 0xa5d6a7, 14);
    }
  });

  // Riding: E toggles mount/dismount here so dismount never remounts on the same keypress.
  window.addEventListener('keydown', (e) => {
    if (e.code !== 'KeyE' || !state.rideUnlocked) return;
    if (inQuiz || director.isActive()) return;
    if (flight.isRiding()) {
      flight.dismount();
      return;
    }
    const root = dragon.getRoot();
    const followMul = growthCameraMul(root.scale.x || 1);
    const d = world.camera.position.distanceTo(root.position);
    if (d < 8 * followMul) {
      player.setFlightMode(true);
      flight.mount();
    }
  });
  const flightWasRiding = { value: false };

  // Volcano gate + summit. Uncleared boulders clamp how close to Mount Ember's
  // summit axis the player (or the ridden dragon) can get: pushed back out to
  // the block radius, which on a cone means "no higher than the next boulder."
  function clampOutsideVolcano(pos, minR) {
    const dx = pos.x - boulders.volcanoCenter.x;
    const dz = pos.z - boulders.volcanoCenter.z;
    const d = Math.hypot(dx, dz);
    if (d >= minR || d === 0) return;
    const s = minR / d;
    pos.x = boulders.volcanoCenter.x + dx * s;
    pos.z = boulders.volcanoCenter.z + dz * s;
  }
  async function celebrateSummit() {
    summitCelebrating = true;
    state.volcano.summited = true;
    gs.save(state);
    boulders.sync(state);
    effects.confetti();
    audio.play('milestone');
    controlsEnabled = false;
    player.setEnabled(false);
    const name = formatDragonName(state.dragonName);
    await story.showSequence([{
      kind: 'beat',
      phase: { id: 'volcano', title: 'The Volcano Challenge' },
      beat: {
        id: 'volcano-summit',
        title: 'Top of Mount Ember!',
        text: `YOU DID IT! You${name ? ` and ${name}` : ''} climbed all the way to the top of Mount Ember! The lava pool bubbles a warm hello, and far below the whole valley looks tiny. From somewhere in the clouds comes a happy roar: "That's my brave little climber!" 🌋`,
      },
    }]);
    controlsEnabled = true;
    player.setEnabled(true);
    showToast(`💎 +${SUMMIT_BONUS_GEMS} gems for the bravest climb ever!`, 5000);
    awardGems(SUMMIT_BONUS_GEMS);
    hud.refresh();
    postGmState();
  }

  async function restoreHandoffQuiz(pending) {
    if (!pending || !pending.items || !pending.items.length) return false;
    pendingBoulder = !!pending.pendingBoulder;
    pendingLava = pending.pendingLava != null ? pending.pendingLava : null;
    pendingStation = pending.pendingStation || null;
    pendingZoomie = !!pending.pendingZoomie;
    inQuiz = true;
    controlsEnabled = false;
    player.setEnabled(false);
    const ok = !!quiz.startFromPending(pending);
    if (ok) heldHandoffQuiz = null;
    return ok;
  }
  const resumedQuiz = savedHandoffQuiz ? await restoreHandoffQuiz(savedHandoffQuiz) : false;
  if (inactiveMode) enterInactiveMode(bootHandoff.reason || 'other_device');
  else handoff.startPolling();
  hideLoading();
  hud.refresh();
  let lastTransferOk = canTransferHandoff();
  function refreshTransferIfChanged() {
    const ok = canTransferHandoff();
    if (ok !== lastTransferOk) {
      lastTransferOk = ok;
      hud.refresh();
    }
  }
  // Resuming a transferred quiz: stay on Go! — skip login letters / celebrations
  // that would cover or interrupt the keypad handoff.
  if (!resumedQuiz) {
    if (justCloned) showToast(`Cloned ${dn(REAL_USER)}'s math file and dragon world — you're caught up with her!`, 5000);
    if (state.rideUnlocked) flight.showInvitePrompt();
    // Login mini-challenge: lava defense begins on the next login after the egg
    // is found; snapshot fluency once so streams always restart from that point.
    if (state.eggFound && !state.lava.intro) {
      if (!state.lava) state.lava = { intro: false, startPct: null, stopped: [], won: false };
      state.lava.intro = true;
      state.lava.startPct = Math.round(effectivePct());
      gs.save(state);
      lavaStreams.sync(state);
      hud.refresh();
      story.showSequence([{
        kind: 'gm-message',
        from: 'Mama Dragon',
        text: 'Keeper — HURRY! Mount Ember is erupting! Five rivers of lava are sliding down the mountain toward your nest. Click each glowing stream and finish a quiz to cool it — stop the lava before it gets to the nest! I believe in you. — Mama D.',
      }]).finally(() => hud.refresh());
    } else if (state.eggFound && !state.volcano.intro) {
      state.volcano.intro = true;
      gs.save(state);
      boulders.sync(state);
      hud.refresh();
      story.showSequence([{
        kind: 'gm-message',
        from: 'Mama Dragon',
        text: 'My little Keeper — I have a DARE for you! Climb Mount Ember, the smoking volcano far to the north. Rockslides have blocked the dragon road with FIVE giant boulders, and only quiz-power can smash them. Follow the orange sparkle trail, do a quiz at every boulder, and climb to the very top — something special is waiting where the smoke touches the sky! — Mama D.',
      }]).finally(() => hud.refresh());
    } else if (state.eggFound && !state.stations.intro) {
      // Nest-projects intro: Mama Dragon points out the signs + growable spots.
      state.stations.intro = true;
      gs.save(state);
      story.showSequence([{ kind: 'gm-message', from: 'Mama Dragon', text: STATIONS_INTRO }]).finally(() => hud.refresh());
    } else if (lavaActive(state.lava)) {
      showToast(`Lava defense: ${(state.lava.stopped || []).length} of ${TOTAL_STREAMS} streams cooled — hurry!`, 5000);
    } else if (state.volcano.intro && !state.volcano.summited) {
      showToast(`🌋 Mount Ember challenge: ${state.volcano.cleared || 0} of ${TOTAL_BOULDERS} boulders smashed — follow the orange sparkles!`, 5000);
    }
    if (state.hatched) {
      setTimeout(() => showToast(`💡 Stand near ${formatDragonName(state.dragonName) || 'your dragon'}: F = pet, 1-4 = tricks!`, 6000), 4500);
    }
    // Catch-up: fluency may have risen outside the game (anchor sessions) or via the
    // dev override — reveal ONE pending milestone (including the hatch) shortly after load.
    if (state.eggFound) setTimeout(() => { processCelebrationQueue(); }, 1500);
    postGmState();
    // Letters that arrived while away are waiting at the door.
    if (state.eggFound) {
      fetchUnreadGmMessages().then(async (letters) => {
        if (!letters.length || story.isOpen() || inQuiz) return;
        await story.showSequence(letters.map((m) => ({ kind: 'gm-message', from: m.from, text: m.text })));
        markGmMessagesRead(letters.map((m) => m.id));
        hud.refresh();
      });
    }
  } else {
    postGmState();
  }
  refreshZoomieLines();
  refreshGrowthSpurtLines();
  console.log('[dragon] ready', { user, pct: effectivePct(), maxPct: state.maxPct });

  const animate = () => {
    requestAnimationFrame(animate);
    const delta = world.clock.getDelta();
    egg.update(delta);
    dragon.update(delta);
    ambient.update(delta);
    mountains.update(delta);
    boulders.update(delta);
    lavaStreams.update(delta, { paused: inQuiz });
    zoomieFx.update(delta, { paused: inQuiz || story.isOpen() || director.isActive() });
    homestead.update(delta);
    nestStations.update(delta);
    critters.update(delta);
    if (gift.visible) gift.position.y = Math.sin(performance.now() * 0.0015) * 0.08;
    journey.update(delta);
    effects.update(delta);
    flight.update(delta);
    if (flightWasRiding.value && !flight.isRiding()) player.setEnabled(true);
    flightWasRiding.value = flight.isRiding();
    if (zoomiesEligible(state) && state.hatched && !zoomieActive && !inQuiz && controlsEnabled
      && !director.isActive() && !flight.isRiding() && !story.isOpen() && !inactiveMode
      && handoff.isOwner() && document.visibilityState === 'visible') {
      zoomieTimer -= delta;
      if (zoomieTimer <= 0) {
        ensureZoomies(state);
        if (!state.zoomies.intro) {
          state.zoomies.intro = true;
          gs.save(state);
          zoomieTimer = ZOOMIE_INTERVAL_S;
          story.showSequence([{
            kind: 'gm-message',
            from: 'Mama Dragon',
            text: zoomiesIntroText(formatDragonName(state.dragonName)),
          }]).finally(() => hud.refresh());
          return;
        }
        zoomieActive = true;
        zoomieFx.start(dragon.getRoot(), {
          playerPos: () => player.camera.position,
          heightAt: mountains.heightAt,
          nest: env.nest.position,
        });
        dragon.playState('walk');
        showToast(zoomieAlertFor(state.zoomies.alerts, formatDragonName(state.dragonName)), 4500);
        state.zoomies.alerts += 1;
        gs.save(state);
        audio.play('click');
        updateDragonLabel();
      }
    }
    if (followDragon && state.hatched && !flight.isRiding() && !flight.isDescending()
      && !director.isActive() && !zoomieActive) {
      const root = dragon.getRoot();
      const followMul = growthCameraMul(root.scale.x || 1);
      const target = new THREE.Vector3(
        player.camera.position.x - 1.5 * followMul, 0,
        player.camera.position.z - 1.5 * followMul,
      );
      const dist = root.position.distanceTo(target);
      if (dist > 2.5 * followMul) {
        root.position.lerp(target, Math.min(1, delta * 1.5));
        // Stand on the nest surface while inside it, on the terrain outside
        // (the dragon climbs the mountains right along with the player).
        const nestDist = Math.hypot(root.position.x - env.nest.position.x, root.position.z - env.nest.position.z);
        root.position.y = nestDist < 2.8 ? NEST_TOP_Y : mountains.heightAt(root.position.x, root.position.z);
        root.lookAt(player.camera.position.x, 0, player.camera.position.z);
        if (!followMoving) { dragon.playState('walk'); followMoving = true; }
      } else if (followMoving) {
        dragon.playState('idle');
        followMoving = false;
      }
    }
    const playerActive = controlsEnabled && !inQuiz && !director.isActive() && !flight.isRiding();
    refreshTransferIfChanged();
    player.update(delta, playerActive);
    const br = boulders.blockRadius();
    if (br != null) {
      clampOutsideVolcano(player.camera.position, br);
      if (flight.isRiding()) clampOutsideVolcano(dragon.getRoot().position, br);
    } else if (state.volcano.intro && !state.volcano.summited && !summitCelebrating
      && playerActive && atSummit(player.camera.position.x, player.camera.position.z)) {
      celebrateSummit();
    }
    world.renderer.render(world.scene, world.camera);
  };
  animate();
}

boot().catch((e) => {
  console.error(e);
  setLoading('Something went wrong loading the game.');
});
