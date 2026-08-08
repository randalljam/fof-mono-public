import { MILESTONES } from './milestones.js';

const HATCH_MILESTONE = MILESTONES.find((m) => m.id === 'hatch');
const HATCH_PCT = HATCH_MILESTONE ? HATCH_MILESTONE.pct : 60;

export function gameStateKey(learner) {
  return `dragon-game::${learner}`;
}
// Copy sourceUser's browser save onto targetUser's key (boulders, signs, gems,
// story, etc.). Used by "Clone Kid1" so the tester inherits her world progress,
// not just her math file. Returns true when a source save was found and written;
// false when the target key was cleared (no source save / parse error).
export function cloneLocalGameState(sourceUser, targetUser) {
  if (!sourceUser || !targetUser || sourceUser === targetUser) return false;
  const sourceKey = gameStateKey(sourceUser);
  const targetKey = gameStateKey(targetUser);
  try {
    const raw = localStorage.getItem(sourceKey);
    if (!raw) {
      localStorage.removeItem(targetKey);
      return false;
    }
    const data = JSON.parse(raw);
    data.learner = targetUser;
    localStorage.setItem(targetKey, JSON.stringify(data));
    return true;
  } catch {
    localStorage.removeItem(targetKey);
    return false;
  }
}
// True when any saved signal shows the dragon already emerged — used to skip the
// hatch cutscene on reload and keep hatched / celebratedIds in sync.
export function isPastHatch(state) {
  return !!(
    state.hatched
    || (state.celebratedIds || []).includes('hatch')
    || state.dragonName
    || (state.seenBeatIds || []).includes('hatch-name')
  );
}
// True when fluency has already crossed the hatch threshold (e.g. anchor sessions
// or a cloned math file) even if browser game progress was wiped or never saved.
export function fluencyPastHatch(state) {
  return (state.maxPct || 0) >= HATCH_PCT;
}
export function createGameState(learner, { legacyLearner } = {}) {
  const key = gameStateKey(learner);
  function load() {
    try {
      let raw = localStorage.getItem(key);
      if (!raw && legacyLearner && legacyLearner !== learner) {
        raw = localStorage.getItem(gameStateKey(legacyLearner));
      }
      if (!raw) return defaultState(learner);
      const data = JSON.parse(raw);
      return migrate(Object.assign(defaultState(learner), data));
    } catch {
      return defaultState(learner);
    }
  }
  // v1 -> v2: the milestone ladder changed (hatch moved from "first burst" to the
  // 60% milestone; old ids like first-steps/meadow no longer exist). Keep progress
  // numbers, drop milestone bookkeeping — the celebration queue re-derives every
  // earned milestone from maxPct and reveals them one per burst.
  function migrate(state) {
    if (state.version < 2) {
      state.version = 2;
      state.celebratedIds = state.celebratedIds.includes('egg-found') || state.eggFound ? ['egg-found'] : [];
      state.unlockedIds = [...state.celebratedIds];
      state.celebrationQueue = [];
      state.hatched = false;
      state.rideUnlocked = false;
    }
    // v2 -> v3: Dragon Gems arrive. Grant retroactive gems for bursts already
    // played so an existing save starts with a partly-grown nest, not zero.
    if (state.version < 3) {
      state.version = 3;
      state.gems = (state.totalBursts || 0) * 6;
      state.lastGiftISO = null;
      state.giftsOpened = 0;
    }
    return state;
  }
  function save(state) {
    localStorage.setItem(key, JSON.stringify(state));
  }
  function defaultState(name) {
    return {
      version: 3,
      learner: name,
      maxPct: 0,
      unlockedIds: [],
      celebratedIds: [],
      hatched: false,
      rideUnlocked: false,
      totalBursts: 0,
      lastPlayedISO: null,
      muted: false,
      eggFound: false,
      celebrationQueue: [],
      // Story/journey/GM additions (additive — Object.assign backfills old saves).
      dragonName: null,
      seenBeatIds: [],
      visitedStones: [],
      recentBursts: [],
      // Volcano climb challenge (additive — Object.assign backfills old saves):
      // intro shown at login, boulders smashed by finished quizzes, summit flag.
      volcano: { intro: false, cleared: 0, summited: false },
      // Lava defense (additive): five streams race toward the nest; each cooled
      // by a finished quiz. startPct snapshots fluency once at intro.
      lava: { intro: false, startPct: null, stopped: [], won: false },
      // Dragon Gems: lifetime total (never spent) — nest upgrades key off it.
      gems: 0,
      lastGiftISO: null,
      giftsOpened: 0,
      // Nest quiz stations (additive): sign words + grow levels + intro letter
      // flag; sim/stations.js ensureStations backfills the nested keys.
      stations: { signs: {}, levels: {}, intro: false },
      // Pipa zoomies (additive): intro letter, calm count, alerts, graduation.
      zoomies: { intro: false, calmed: 0, alerts: 0, graduated: false },
      // Growth spurt (additive): post-90% size-up letters after finished quizzes.
      growthSpurt: { shown: 0 },
    };
  }
  function updateHighWater(state, pct) {
    if (pct > state.maxPct) state.maxPct = pct;
    return state;
  }
  function markCelebrated(state, id) {
    if (!state.celebratedIds.includes(id)) state.celebratedIds.push(id);
    if (!state.unlockedIds.includes(id)) state.unlockedIds.push(id);
    state.celebrationQueue = state.celebrationQueue.filter((x) => x !== id);
    return state;
  }
  function queueCelebrations(state, ids) {
    for (const id of ids) {
      if (!state.celebratedIds.includes(id) && !state.celebrationQueue.includes(id)) {
        state.celebrationQueue.push(id);
      }
    }
    return state;
  }
  function popCelebration(state) {
    if (!state.celebrationQueue.length) return null;
    return state.celebrationQueue.shift();
  }
  // Rolling feed of the last 20 bursts for the Game Master activity view.
  function pushRecentBurst(state, entry) {
    if (!state.recentBursts) state.recentBursts = [];
    state.recentBursts.push(entry);
    if (state.recentBursts.length > 20) state.recentBursts = state.recentBursts.slice(-20);
    return state;
  }
  // One-time hatch: sync saved signals, or restore silently when fluency already
  // earned the hatch (clone / anchor catch-up) so the cutscene plays only when
  // the player crosses 60% during a live burst.
  function reconcileHatchState(state) {
    if (isPastHatch(state) || fluencyPastHatch(state)) {
      state.hatched = true;
      if (fluencyPastHatch(state)) {
        state.eggFound = true;
        markCelebrated(state, 'egg-found');
      }
      markCelebrated(state, 'hatch');
    }
    return state;
  }
  return {
    load, save, updateHighWater, markCelebrated, queueCelebrations, popCelebration,
    pushRecentBurst, reconcileHatchState, key,
  };
}
// Apply a server checkpoint's gameState through the same migration path as
// localStorage load — used by cross-device handoff hydration.
export function hydrateFromCheckpoint(rawState, learner) {
  function defaultState(name) {
    return {
      version: 3,
      learner: name,
      maxPct: 0,
      unlockedIds: [],
      celebratedIds: [],
      hatched: false,
      rideUnlocked: false,
      totalBursts: 0,
      lastPlayedISO: null,
      muted: false,
      eggFound: false,
      celebrationQueue: [],
      dragonName: null,
      seenBeatIds: [],
      visitedStones: [],
      recentBursts: [],
      volcano: { intro: false, cleared: 0, summited: false },
      lava: { intro: false, startPct: null, stopped: [], won: false },
      gems: 0,
      lastGiftISO: null,
      giftsOpened: 0,
      stations: { signs: {}, levels: {}, intro: false },
      // Pipa zoomies (additive): intro letter, calm count, alerts, graduation.
      zoomies: { intro: false, calmed: 0, alerts: 0, graduated: false },
      // Growth spurt (additive): post-90% size-up letters after finished quizzes.
      growthSpurt: { shown: 0 },
    };
  }
  function migrate(state) {
    if (state.version < 2) {
      state.version = 2;
      state.celebratedIds = state.celebratedIds.includes('egg-found') || state.eggFound ? ['egg-found'] : [];
      state.unlockedIds = [...state.celebratedIds];
      state.celebrationQueue = [];
      state.hatched = false;
      state.rideUnlocked = false;
    }
    if (state.version < 3) {
      state.version = 3;
      state.gems = (state.totalBursts || 0) * 6;
      state.lastGiftISO = null;
      state.giftsOpened = 0;
    }
    return state;
  }
  try {
    const data = typeof rawState === 'string' ? JSON.parse(rawState) : rawState;
    return migrate(Object.assign(defaultState(learner), data || {}));
  } catch {
    return defaultState(learner);
  }
}
