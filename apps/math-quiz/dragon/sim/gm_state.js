// Game Master snapshot builder: everything the parent dashboard shows, derived
// from the game state + live fluency. DOM-free so the tests (and sim) can run
// it in Node; main.js POSTs the result to /api/dragon-state.
import { storyPhaseFor, nextObjectiveFor, phaseById } from './story.js';
import { getNextMilestone, progressToNext } from './milestones.js';

export function buildGmSnapshot({ state, pct, user, folder }) {
  const phaseId = storyPhaseFor(state);
  const phase = phaseById(phaseId);
  const objective = nextObjectiveFor(state);
  const nextMilestone = getNextMilestone(state.maxPct || 0);
  const { frac } = progressToNext(state.maxPct || 0);
  return {
    user,
    folder,
    dragonName: state.dragonName || null,
    // The parent sees real fluency numbers; the kid HUD deliberately never does.
    pct: Math.round((pct || 0) * 10) / 10,
    maxPct: Math.round((state.maxPct || 0) * 10) / 10,
    segmentFrac: Math.round(frac * 100) / 100,
    nextMilestone: nextMilestone
      ? { id: nextMilestone.id, title: nextMilestone.title, pct: nextMilestone.pct }
      : null,
    phase: phaseId,
    phaseTitle: phase ? phase.title : phaseId,
    objective,
    hatched: !!state.hatched,
    rideUnlocked: !!state.rideUnlocked,
    eggFound: !!state.eggFound,
    totalBursts: state.totalBursts || 0,
    lastPlayedISO: state.lastPlayedISO || null,
    celebratedIds: (state.celebratedIds || []).slice(),
    visitedStones: (state.visitedStones || []).slice(),
    gems: state.gems || 0,
    volcano: state.volcano
      ? { intro: !!state.volcano.intro, cleared: state.volcano.cleared || 0, summited: !!state.volcano.summited }
      : null,
    lava: state.lava
      ? {
        intro: !!state.lava.intro,
        startPct: state.lava.startPct,
        stopped: (state.lava.stopped || []).slice(),
        won: !!state.lava.won,
      }
      : null,
    zoomies: state.zoomies
      ? { intro: !!state.zoomies.intro, calmed: state.zoomies.calmed || 0, alerts: state.zoomies.alerts || 0, graduated: !!state.zoomies.graduated }
      : null,
    growthSpurt: state.growthSpurt
      ? { shown: state.growthSpurt.shown || 0 }
      : null,
    stations: state.stations
      ? { signs: Object.assign({}, state.stations.signs), levels: Object.assign({}, state.stations.levels) }
      : null,
    scrollsCollected: (state.seenBeatIds || []).length,
    recentBursts: (state.recentBursts || []).slice(),
    clientTs: new Date().toISOString(),
  };
}
