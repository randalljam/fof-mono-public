// Story engine: DOM-free selection logic over sim/story_content.js, consumed by
// the browser game, the headless sim, and the unit tests. Beats are delivered
// one per burst-end: the phase's ordered beats first (in order), then its extras
// pool rotating (repeats allowed only after every extra has been seen).
import { STORY_PHASES, QUIZ_REACTIONS, STONE_BEATS, UNNAMED } from './story_content.js';

const PHASE_ORDER = ['egg', 'hatchling', 'meadow', 'hills', 'grove', 'summit'];

export function storyPhaseFor(state) {
  if (state.rideUnlocked) return 'summit';
  if (!state.hatched) return 'egg';
  const pct = state.maxPct || 0;
  if (pct >= 90) return 'grove';
  if (pct >= 80) return 'hills';
  if (pct >= 70) return 'meadow';
  return 'hatchling';
}
export function phaseById(id) {
  return STORY_PHASES.find((p) => p.id === id) || null;
}
export function formatDragonName(name) {
  const trimmed = String(name || '').trim();
  if (!trimmed) return null;
  return trimmed.replace(/\S+/g, (word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase());
}
export function fillName(text, dragonName) {
  return String(text).replaceAll('{name}', formatDragonName(dragonName) || UNNAMED);
}
// Next beat for the state: earliest unseen ordered beat across the current phase
// AND earlier phases (so a fast climber still gets key beats like naming), then
// the current phase's least-recently-available extra. Returns {beat, phase} with
// text already name-filled, or null when everything is exhausted.
export function nextStoryBeat(state) {
  const seen = new Set(state.seenBeatIds || []);
  const phaseId = storyPhaseFor(state);
  const idx = PHASE_ORDER.indexOf(phaseId);
  for (let i = 0; i <= idx; i++) {
    const phase = phaseById(PHASE_ORDER[i]);
    if (!phase) continue;
    for (const beat of phase.beats) {
      if (!seen.has(beat.id)) return decorate(beat, phase, state);
    }
  }
  const phase = phaseById(phaseId);
  if (!phase || !phase.extras.length) return null;
  const unseenExtras = phase.extras.filter((b) => !seen.has(b.id));
  if (unseenExtras.length) return decorate(unseenExtras[0], phase, state);
  // Every extra seen: rotate deterministically by total bursts so revisits vary.
  const i = (state.totalBursts || 0) % phase.extras.length;
  return decorate(phase.extras[i], phase, state, true);
}
function decorate(beat, phase, state, isRepeat = false) {
  return {
    beat: Object.assign({}, beat, { text: fillName(beat.text, state.dragonName) }),
    phase: { id: phase.id, title: phase.title },
    isRepeat,
  };
}
export function markBeatSeen(state, beatId) {
  if (!state.seenBeatIds) state.seenBeatIds = [];
  if (!state.seenBeatIds.includes(beatId)) state.seenBeatIds.push(beatId);
  return state;
}
// Journal: every seen beat in story order (phases, then beats/extras in-phase),
// with visited Story Stones collected under The Dragon Road at the end.
export function journalEntries(state) {
  const seen = new Set(state.seenBeatIds || []);
  const out = [];
  for (const pid of PHASE_ORDER) {
    const phase = phaseById(pid);
    for (const beat of [...phase.beats, ...phase.extras]) {
      if (seen.has(beat.id)) {
        out.push({
          id: beat.id, title: beat.title, phaseTitle: phase.title,
          text: fillName(beat.text, state.dragonName),
        });
      }
    }
  }
  for (const beat of Object.values(STONE_BEATS)) {
    if (seen.has(beat.id)) {
      out.push({
        id: beat.id, title: beat.title, phaseTitle: 'The Dragon Road',
        text: fillName(beat.text, state.dragonName),
      });
    }
  }
  return out;
}
// Post-quiz reaction line, tiered by score and rotated by burst count so the
// same tier does not repeat the same line back-to-back. Deterministic for tests.
export function quizReaction({ correct, total, totalBursts = 0, dragonName = null }) {
  if (!total) return null;
  const ratio = correct / total;
  const tier = ratio >= 1 ? 'perfect' : ratio >= 0.85 ? 'great' : ratio >= 0.6 ? 'good' : 'tough';
  const pool = QUIZ_REACTIONS[tier];
  const line = pool[totalBursts % pool.length];
  return fillName(line.replaceAll('{score}', `${correct} of ${total}`), dragonName);
}
// The single current objective, for the HUD and the Game Master page.
export function nextObjectiveFor(state) {
  if (!state.eggFound) return { id: 'find-egg', text: 'Walk to the nest and click the egg!' };
  const lava = state.lava;
  if (lava && lava.intro && !lava.won) {
    const cooled = (lava.stopped || []).length;
    if (cooled < 5) {
      return {
        id: 'lava-defense',
        text: `Hurry! Lava is flowing toward the nest — click a glowing stream and finish a quiz to cool it (${cooled} of 5 stopped).`,
      };
    }
    return { id: 'lava-defense-last', text: 'One lava stream left — cool it with a quiz before it reaches the nest!' };
  }
  // The volcano climb (once introduced) is the active challenge until summited.
  const v = state.volcano;
  if (v && v.intro && !v.summited) {
    if ((v.cleared || 0) < 5) {
      return {
        id: 'volcano-boulders',
        text: `Climb Mount Ember! Follow the orange sparkles north and smash the boulders with quizzes (${v.cleared || 0} of 5 smashed).`,
      };
    }
    return { id: 'volcano-summit', text: 'The path is clear — climb to the very TOP of Mount Ember!' };
  }
  const phase = storyPhaseFor(state);
  const name = formatDragonName(state.dragonName) || UNNAMED;
  const visited = new Set(state.visitedStones || []);
  if (phase === 'egg') return { id: 'feed-egg', text: 'Feed the egg with math quizzes — watch the bar fill toward the next surprise!' };
  if (phase === 'hatchling') {
    if (!state.dragonName) return { id: 'name-dragon', text: 'Your dragon needs a name!' };
    return { id: 'grow-hatchling', text: `Practice with ${name} — it keeps looking down the eastern trail…` };
  }
  if (phase === 'meadow' && !visited.has('meadow')) {
    return { id: 'visit-meadow', text: `Follow the sparkle trail east to the Butterfly Meadow with ${name} and click the Story Stone.` };
  }
  if (phase === 'hills' && !visited.has('hills')) {
    return { id: 'visit-hills', text: `A new trail climbs the Whispering Hills! Take ${name} up south to the hilltop Story Stone.` };
  }
  if (phase === 'grove' && !visited.has('grove')) {
    return { id: 'visit-grove', text: `The trail turns west into the Firefly Grove. Find the old beacon with ${name}.` };
  }
  if (phase === 'summit') return { id: 'ride', text: `Stand near ${name} and press E!` };
  return { id: 'practice', text: `Keep practicing with ${name} — something is waiting down the road…` };
}
// Story Stone beat for a journey stone visit, name-filled.
export function stoneBeatFor(stoneId, dragonName) {
  const beat = STONE_BEATS[stoneId];
  if (!beat) return null;
  return Object.assign({}, beat, { text: fillName(beat.text, dragonName) });
}
export { PHASE_ORDER };
