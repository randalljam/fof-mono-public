// Simulation harness: runs a learner profile through the adaptive selector,
// emits canonical session JSON, and evaluates fluency using the real app functions.
import { buildFactMatrix, makeRng, sampleLognormal, selectNextFact,
         checkPredictiveMastery, checkThoroughMastery } from './adaptive_selector.mjs';
import { createAppContext } from '../tests/load_app.mjs';
import { randomUUID } from 'node:crypto';

function loadFluencyFns() {
  const ctx = createAppContext(['math_utils.js', 'fluency_core.js', 'math_fluency.js']);
  return {
    evaluateFluencyStatus: (attempts, thresholds) =>
      ctx.__evalJson(`evaluateFluencyStatus(${JSON.stringify(attempts)}${thresholds ? ', ' + JSON.stringify(thresholds) : ''})`),
    checkPermanentStatus: (history, n) =>
      ctx.__eval(`checkPermanentStatus(${JSON.stringify(history)}, ${n ?? 5})`),
    importSessionData: ctx.__get('importSessionData'),
    createTables: ctx.__get('createTables'),
  };
}

// Parse the yaml block out of a profile markdown file
export function parseProfileYaml(markdown) {
  const match = markdown.match(/```yaml\n([\s\S]*?)```/);
  if (!match) throw new Error('No yaml block found in profile markdown');
  return parseSimpleYaml(match[1]);
}

function parseSimpleYaml(text) {
  // Very minimal YAML parser for the profile structure (no full YAML needed)
  const obj = {};
  const lines = text.split('\n');
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trimEnd();
    if (!trimmed || trimmed.startsWith('#')) { i++; continue; }

    const kvMatch = trimmed.match(/^(\s*)(\w[\w_-]*):\s*(.*)$/);
    if (!kvMatch) { i++; continue; }
    const [, indent, key, rawVal] = kvMatch;
    if (indent === '') {
      const val = parseScalar(rawVal);
      if (val !== undefined) { obj[key] = val; i++; }
      else {
        // Multi-line: collect child lines
        const [child, consumed] = parseBlock(lines, i + 1, 0);
        obj[key] = child;
        i += consumed + 1;
      }
    } else { i++; } // nested lines handled by parseBlock
  }
  return obj;
}

function parseScalar(raw) {
  const s = raw.replace(/#.*$/, '').trim().replace(/^["']|["']$/g, '');
  if (!s) return undefined;
  if (s === 'true') return true;
  if (s === 'false') return false;
  if (s.startsWith('[') && s.endsWith(']')) {
    const inner = s.slice(1, -1).split(',').map(x => parseScalar(x.trim())).filter(x => x !== undefined);
    return inner;
  }
  const n = Number(s);
  return isNaN(n) ? s : n;
}

function parseBlock(lines, start, parentIndent) {
  const result = {};
  const arr = [];
  let isArr = false;
  let i = start;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trimEnd();
    if (!trimmed || trimmed.trimStart().startsWith('#')) { i++; continue; }
    const indentLen = trimmed.length - trimmed.trimStart().length;
    if (indentLen <= parentIndent) break;

    const stripped = trimmed.trimStart();
    if (stripped.startsWith('- ')) {
      isArr = true;
      const val = stripped.slice(2).replace(/#.*$/, '').trim();
      const parsed = parseScalar(val);
      arr.push(parsed !== undefined ? parsed : val);
      i++;
    } else {
      const m = stripped.match(/^(\w[\w_-]*):\s*(.*)$/);
      if (!m) { i++; continue; }
      const [, key, rawVal] = m;
      const val = parseScalar(rawVal);
      if (val !== undefined) { result[key] = val; i++; }
      else {
        const [child, consumed] = parseBlock(lines, i + 1, indentLen);
        result[key] = child;
        i += consumed + 1;
      }
    }
  }
  return [isArr ? arr : result, i - start];
}

// Build initial skill map from profile initial_state
export function buildSkillMap(factMatrix, initialState) {
  const skills = new Map();
  for (const [key] of factMatrix) skills.set(key, initialState.default || 'unknown');

  const overrides = initialState.overrides || [];
  for (const [key, fact] of factMatrix) {
    for (const override of overrides) {
      if (matchesFact(fact, key, override.facts)) {
        skills.set(key, override.level);
      }
    }
  }
  return skills;
}

function matchesFact(fact, key, expr) {
  if (!expr) return false;
  try {
    const { num1, num2, operation } = fact;
    const js = expr
      .replace(/doubles up to (\d+)\+\1/g, 'operation === "+" && num1 === num2 && num1 <= $1')
      .replace(/sum\s*<=\s*(\d+)/g, '(num1 + num2) <= $1')
      .replace(/(\w+)\s+in\s+(\d+)\.\.(\d+)/g, '($1 >= $2 && $1 <= $3)')
      .replace(/(\w+)\s*==\s*'([^']*)'/g, '$1 === "$2"')
      .replace(/\band\b/g, '&&')
      .replace(/\bor\b/g, '||');
    return new Function('num1', 'num2', 'operation', `return !!(${js})`)(num1, num2, operation);
  } catch { return false; }
}

export function sampleResponse(rng, skill, responseModel) {
  const model = responseModel[skill] || responseModel['fluent'];
  const pCorrect = model.p_correct;
  const isCorrect = rng() < pCorrect;
  const { median, sigma } = model.rt_ms;
  const responseTime = sampleLognormal(rng, median, sigma);
  return { isCorrect, responseTime };
}

// Advance skill level with the learning model (uses total correct counter)
function applyLearning(learningModel, skill, isCorrect, learnerState, key) {
  if (learningModel.type === 'static') return skill;
  const levels = ['unknown', 'emerging', 'fluent'];
  const promoteAfter = learningModel.promote_after || 4;
  const regressAfter = learningModel.regress_after || 2;

  if (!learnerState.correctCounts) learnerState.correctCounts = new Map();
  if (!learnerState.wrongStreak) learnerState.wrongStreak = new Map();

  if (isCorrect) {
    const c = (learnerState.correctCounts.get(key) || 0) + 1;
    learnerState.correctCounts.set(key, c);
    learnerState.wrongStreak.set(key, 0);
    if (c >= promoteAfter) {
      learnerState.correctCounts.set(key, 0);
      const idx = levels.indexOf(skill);
      return idx < levels.length - 1 ? levels[idx + 1] : skill;
    }
  } else {
    const w = (learnerState.wrongStreak.get(key) || 0) + 1;
    learnerState.wrongStreak.set(key, w);
    if (w >= regressAfter) {
      learnerState.wrongStreak.set(key, 0);
      const idx = levels.indexOf(skill);
      if (idx > 0) {
        learnerState.correctCounts.set(key, 0); // reset count on actual level-down
        return levels[idx - 1];
      }
      // already at lowest level — don't reset correct count (prevents oscillation)
    }
  }
  return skill;
}

function makeSessionTimestamp(baseMs, offsetMs = 0) {
  const d = new Date(baseMs + offsetMs);
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}_${String(d.getHours()).padStart(2,'0')}${String(d.getMinutes()).padStart(2,'0')}${String(d.getSeconds()).padStart(2,'0')}`;
}

// Run one profile's simulation (or one named run from a multi-run profile).
// Returns { perFactAttempts, perFactStatusHistory, perFactPresentations, sessions, sampledFacts }
export function runSimulation(profile, runOverrides = {}, fluencyFns = null) {
  const fns = fluencyFns || loadFluencyFns();
  const operations = profile.operations || ['+'];
  const numberRange = profile.number_range || [0, 9];
  const factMatrix = buildFactMatrix(operations, numberRange);

  const schedule = { ...profile.schedule, ...runOverrides.schedule };
  const sessions = typeof schedule.sessions === 'number' ? schedule.sessions : 1;
  const probRange = schedule.problems_per_session;
  const getProblems = (rng) => {
    if (probRange === 'full-matrix') return factMatrix.size * 3; // 3x ensures all facts visited despite hard-weighting
    if (Array.isArray(probRange)) return Math.floor(rng() * (probRange[1] - probRange[0] + 1)) + probRange[0];
    return probRange;
  };

  const learningModel = profile.learning_model || { type: 'static' };
  const responseModel = profile.response_model || {};
  const maxNewFacts = learningModel.max_new_facts_per_session || Infinity;
  const seed = `${profile.profile_id}-${runOverrides.name || 'default'}`;
  const rng = makeRng(seed);

  const skillMap = buildSkillMap(factMatrix, profile.initial_state || { default: 'fluent' });
  const learnerState = {};

  // Tracking across sessions
  const perFactAttempts = new Map();  // key -> [{isCorrect, responseTime}]
  const perFactStatusHistory = new Map(); // key -> [status per session it appeared]
  const perFactPresentations = new Map(); // key -> total presentation count
  const sampledFacts = new Set();
  const emittedSessions = [];
  const baseMs = new Date('2026-01-01').getTime();

  for (let s = 0; s < sessions; s++) {
    const nProblems = getProblems(rng);
    const sessionId = randomUUID();
    const startTime = makeSessionTimestamp(baseMs, s * 3600000);
    const perFactStatus = new Map();

    for (const [key] of factMatrix) {
      const attempts = perFactAttempts.get(key) || [];
      const result = fns.evaluateFluencyStatus(attempts);
      perFactStatus.set(key, result.status);
    }

    const sessionProblems = [];
    const recentMissAt = new Map();
    let newFactsIntroduced = 0;

    for (let p = 0; p < nProblems; p++) {
      const sessionState = { newFactsIntroduced, maxNewFacts, recentMissAt, problemIndex: p };
      const key = selectNextFact(factMatrix, perFactStatus, sessionState, { hardWeight: 3, rng });
      const fact = factMatrix.get(key);

      const skill = skillMap.get(key) || 'unknown';
      const { isCorrect, responseTime } = sampleResponse(rng, skill, responseModel);

      if ((perFactStatus.get(key) || 'nodata') === 'nodata') newFactsIntroduced++;

      const attempts = perFactAttempts.get(key) || [];
      attempts.push({ isCorrect, responseTime });
      perFactAttempts.set(key, attempts);
      perFactPresentations.set(key, (perFactPresentations.get(key) || 0) + 1);
      sampledFacts.add(key);

      // Update within-session status estimate
      const updatedResult = fns.evaluateFluencyStatus(attempts);
      perFactStatus.set(key, updatedResult.status);

      if (!isCorrect) recentMissAt.set(key, p);

      // Apply learning model
      const newSkill = applyLearning(learningModel, skill, isCorrect, learnerState, key);
      skillMap.set(key, newSkill);

      const problemText = fact.problemText;
      let correctAnswer;
      if (fact.operation === '+') correctAnswer = fact.num1 + fact.num2;
      else if (fact.operation === '-') correctAnswer = fact.num1 - fact.num2;
      else if (fact.operation === '*') correctAnswer = fact.num1 * fact.num2;
      else correctAnswer = 0;

      sessionProblems.push({
        id: `${sessionId}-${p}`,
        problem_text: problemText,
        correct_answer: correctAnswer,
        user_answer_string: isCorrect ? String(correctAnswer) : String(correctAnswer + 1),
        user_answer: isCorrect ? correctAnswer : correctAnswer + 1,
        is_correct: isCorrect,
        response_time_ms: responseTime,
        flags: []
      });
    }

    // Update per-fact status history for this session
    for (const key of sampledFacts) {
      const attempts = perFactAttempts.get(key) || [];
      const sessionAttempts = attempts.slice(-(nProblems + 5)); // approximate; status from full history
      const result = fns.evaluateFluencyStatus(attempts);
      const history = perFactStatusHistory.get(key) || [];
      history.push(result.status);
      perFactStatusHistory.set(key, history);
    }

    const totalCorrect = sessionProblems.filter(p => p.is_correct).length;
    const avgRt = sessionProblems.length > 0
      ? Math.round(sessionProblems.reduce((s, p) => s + p.response_time_ms, 0) / sessionProblems.length)
      : 0;

    const sessionJson = {
      version: '1.1',
      user: { name: profile.display_name || profile.profile_id },
      session: {
        id: sessionId,
        start_time: startTime,
        end_time: makeSessionTimestamp(baseMs, s * 3600000 + 1800000),
        settings: {
          preset: 'adaptive', note: `profile:${profile.profile_id}`,
          num_problems: sessionProblems.length,
          number_range: numberRange,
          numbers_include: [], numbers_exclude: [],
          num_numbers: 2,
          operations,
        },
        summary: { total_problems: sessionProblems.length, correct_answers: totalCorrect, average_response_time_ms: avgRt },
        problems: sessionProblems,
      }
    };
    emittedSessions.push(sessionJson);
  }

  // Final fluency state from the real fluency functions
  const finalStatus = new Map();
  const isBlue = new Map();
  for (const [key] of factMatrix) {
    const attempts = perFactAttempts.get(key) || [];
    const { status } = fns.evaluateFluencyStatus(attempts);
    const history = perFactStatusHistory.get(key) || [];
    const permanent = fns.checkPermanentStatus(history, 5);
    finalStatus.set(key, permanent ? 'blue' : status);
    isBlue.set(key, permanent);
  }

  return { perFactAttempts, perFactStatusHistory, perFactPresentations, sessions: emittedSessions, sampledFacts, finalStatus, factMatrix, fluencyFns: fns };
}

export { buildFactMatrix, checkPredictiveMastery, checkThoroughMastery };
