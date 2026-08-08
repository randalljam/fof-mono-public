// START OF FILE math_utils.js
// Shared utility functions for math quiz application

console.log('Math Utils JavaScript file loaded.');

// Color scales for heatmap visualization (light = fast, dark = slow)
const COLOR_SCALES = {
  blue: [
    [0, 'rgb(227, 242, 253)'],
    [0.5, 'rgb(100, 181, 246)'],
    [1, 'rgb(13, 71, 161)']
  ],
  purple: [
    [0, 'rgb(243, 229, 245)'],
    [0.5, 'rgb(186, 104, 200)'],
    [1, 'rgb(74, 20, 140)']
  ],
  orange: [
    [0, 'rgb(255, 243, 224)'],
    [0.5, 'rgb(255, 167, 38)'],
    [1, 'rgb(230, 81, 0)']
  ],
  classic: [
    [0, 'rgb(0, 255, 0)'],
    [0.5, 'rgb(255, 255, 0)'],
    [1, 'rgb(255, 0, 0)']
  ]
};

function useLocalMathQuizPages() {
  const hostname = window.location.hostname;
  return window.location.protocol === 'file:' ||
    hostname === 'localhost' ||
    hostname === '127.0.0.1';
}
function getMathQuizSessionStorageKeys() {
  const keys = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key.startsWith('math_session_') && key.endsWith('.json')) {
      keys.push(key);
    }
  }
  return keys;
}

/**
 * Create database tables for storing session data
 * @param {object} db - SQL.js database instance
 */
function createTables(db) {
  db.run(`
    CREATE TABLE IF NOT EXISTS Users (
      name TEXT PRIMARY KEY
    );
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS Sessions (
      session_id TEXT PRIMARY KEY,
      session_filename TEXT,
      user_name TEXT,
      start_time TEXT,
      end_time TEXT,
      num_problems INTEGER,
      number_range_start INTEGER,
      number_range_end INTEGER,
      numbers_include TEXT,
      numbers_exclude TEXT,
      num_numbers INTEGER,
      operations TEXT,
      total_problems INTEGER,
      correct_answers INTEGER,
      average_response_time_ms INTEGER,
      session_type TEXT,
      FOREIGN KEY (user_name) REFERENCES Users(name)
    );
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS ProblemAttempts (
      attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id TEXT,
      problem_id TEXT,
      problem_text TEXT,
      num1 INTEGER NULL,
      num2 INTEGER NULL,
      operation TEXT NULL,
      correct_answer REAL,
      user_answer_string TEXT,
      user_answer REAL,
      is_correct INTEGER,
      response_time_ms INTEGER,
      flags_json TEXT,
      presented_at TEXT,
      FOREIGN KEY (session_id) REFERENCES Sessions(session_id)
    );
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS TargetedPracticeSessions (
      session_id TEXT PRIMARY KEY,
      user_name TEXT,
      outcome TEXT,
      complete INTEGER,
      completion_reason TEXT,
      target_count INTEGER,
      graduated_count INTEGER,
      current_target_key TEXT,
      graduation_streak INTEGER,
      fast_ms INTEGER,
      percent_target INTEGER,
      filler_pool_size INTEGER,
      problems_presented INTEGER,
      targets_json TEXT,
      graduated_json TEXT,
      metadata_json TEXT,
      inferred INTEGER NOT NULL DEFAULT 0,
      inference_notes TEXT,
      FOREIGN KEY (session_id) REFERENCES Sessions(session_id),
      FOREIGN KEY (user_name) REFERENCES Users(name)
    );
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS TargetedPracticeTargets (
      session_id TEXT,
      target_order INTEGER,
      target_key TEXT,
      problem_text TEXT,
      num1 INTEGER NULL,
      num2 INTEGER NULL,
      operation TEXT NULL,
      graduated INTEGER,
      fast_correct INTEGER,
      attempts INTEGER,
      required_fast_correct INTEGER,
      final_streak INTEGER,
      inferred INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY (session_id, target_key),
      FOREIGN KEY (session_id) REFERENCES TargetedPracticeSessions(session_id)
    );
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS TargetedPracticeAttemptRoles (
      session_id TEXT,
      problem_id TEXT,
      attempt_index INTEGER,
      problem_text TEXT,
      fact_key TEXT,
      role TEXT,
      target_key TEXT,
      current_target_key TEXT,
      target_order INTEGER NULL,
      fast_correct INTEGER,
      inferred INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY (session_id, problem_id),
      FOREIGN KEY (session_id) REFERENCES TargetedPracticeSessions(session_id)
    );
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS VisualPracticeSessions (
      session_id TEXT PRIMARY KEY,
      user_name TEXT,
      outcome TEXT,
      complete INTEGER,
      completion_reason TEXT,
      target_count INTEGER,
      cleared_count INTEGER,
      fast_ms INTEGER,
      retrievals_to_clear INTEGER,
      hesitation_ms INTEGER,
      problems_presented INTEGER,
      targets_json TEXT,
      cleared_json TEXT,
      metadata_json TEXT,
      FOREIGN KEY (session_id) REFERENCES Sessions(session_id),
      FOREIGN KEY (user_name) REFERENCES Users(name)
    );
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS VisualPracticeTargets (
      session_id TEXT,
      target_order INTEGER,
      target_key TEXT,
      problem_text TEXT,
      num1 INTEGER NULL,
      num2 INTEGER NULL,
      operation TEXT NULL,
      cold_probe_result TEXT,
      teach_count INTEGER,
      retrieval_successes INTEGER,
      attempts INTEGER,
      required_successes INTEGER,
      cleared INTEGER,
      PRIMARY KEY (session_id, target_key),
      FOREIGN KEY (session_id) REFERENCES VisualPracticeSessions(session_id)
    );
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS VisualPracticeAttemptRoles (
      session_id TEXT,
      problem_id TEXT,
      attempt_index INTEGER,
      problem_text TEXT,
      fact_key TEXT,
      trial_role TEXT,
      target_key TEXT,
      visual_shown INTEGER,
      passed INTEGER,
      PRIMARY KEY (session_id, problem_id),
      FOREIGN KEY (session_id) REFERENCES VisualPracticeSessions(session_id)
    );
  `);
  
  db.run(`
    CREATE TABLE IF NOT EXISTS ProblemLists (
      problem_list_id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_name TEXT NOT NULL,
      list_order INTEGER NOT NULL DEFAULT 0,
      list_name TEXT NOT NULL,
      added_at TEXT NOT NULL,
      source TEXT,
      retain INTEGER NOT NULL DEFAULT 1,
      times_used INTEGER NOT NULL DEFAULT 0,
      last_used_at TEXT,
      FOREIGN KEY (user_name) REFERENCES Users(name)
    );
  `);
  
  db.run(`
    CREATE INDEX IF NOT EXISTS idx_problem_lists_user_order
    ON ProblemLists (user_name, list_order, problem_list_id);
  `);
  
  db.run(`
    CREATE TABLE IF NOT EXISTS ProblemListItems (
      problem_list_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
      problem_list_id INTEGER NOT NULL,
      item_order INTEGER NOT NULL,
      problem_text TEXT NOT NULL,
      num1 INTEGER NULL,
      operation TEXT NULL,
      num2 INTEGER NULL,
      category TEXT,
      notes TEXT,
      FOREIGN KEY (problem_list_id) REFERENCES ProblemLists(problem_list_id)
    );
  `);
  
  db.run(`
    CREATE INDEX IF NOT EXISTS idx_problem_list_items_list_order
    ON ProblemListItems (problem_list_id, item_order);
  `);
  
  // Add flags_json column if it doesn't exist (for existing databases)
  try {
    db.run('ALTER TABLE ProblemAttempts ADD COLUMN flags_json TEXT');
  } catch (e) {
    // Column already exists, ignore error
  }
  
  // Add presented_at column if it doesn't exist (for existing databases)
  try {
    db.run('ALTER TABLE ProblemAttempts ADD COLUMN presented_at TEXT');
  } catch (e) {
    // Column already exists, ignore error
  }

  try {
    db.run('ALTER TABLE Sessions ADD COLUMN session_type TEXT');
  } catch (e) {
    // Column already exists, ignore error
  }
  
  try {
    db.run('ALTER TABLE ProblemLists ADD COLUMN list_order INTEGER NOT NULL DEFAULT 0');
  } catch (e) {
    // Column already exists, ignore error
  }
  
  try {
    db.run('ALTER TABLE ProblemLists ADD COLUMN source TEXT');
  } catch (e) {
    // Column already exists, ignore error
  }
  
  try {
    db.run('ALTER TABLE ProblemLists ADD COLUMN added_at TEXT');
  } catch (e) {
    // Column already exists, ignore error
  }

  // retain defaults to 1 (keep): a used list stays unless explicitly marked to consume.
  try {
    db.run('ALTER TABLE ProblemLists ADD COLUMN retain INTEGER NOT NULL DEFAULT 1');
  } catch (e) {
    // Column already exists, ignore error
  }

  try {
    db.run('ALTER TABLE ProblemLists ADD COLUMN times_used INTEGER NOT NULL DEFAULT 0');
  } catch (e) {
    // Column already exists, ignore error
  }

  try {
    db.run('ALTER TABLE ProblemLists ADD COLUMN last_used_at TEXT');
  } catch (e) {
    // Column already exists, ignore error
  }

  try {
    db.run('ALTER TABLE ProblemListItems ADD COLUMN category TEXT');
  } catch (e) {
    // Column already exists, ignore error
  }
  
  try {
    db.run('ALTER TABLE ProblemListItems ADD COLUMN notes TEXT');
  } catch (e) {
    // Column already exists, ignore error
  }
}
function parseSessionOutcome(settings) {
  const note = String((settings && settings.note) || '');
  const m = note.match(/(?:^|;)outcome:([^;]+)/);
  return m ? m[1] : null;
}
function sessionTypeFromSettings(settings) {
  if (settings && settings.session_type) return settings.session_type;
  const preset = settings && settings.preset;
  if (preset === 'anchor-targeted') return 'targeted-practice';
  if (preset === 'anchor-visual') return 'visual-practice';
  if (preset === 'anchor-problem-list') return 'problem-list';
  if (preset === 'anchor') return 'assess';
  return null;
}
// Kept for call-site compatibility. Visual-practice attempts count toward fluency
// (same as assess / list / targeted / dragon), so this returns no filter.
function sessionTypeExclusionSql(db, alias) {
  return '';
}
function problemTextFromKey(key) {
  const parts = String(key || '').split('|');
  if (parts.length !== 3) return null;
  return `${parts[1]} ${parts[0]} ${parts[2]}`;
}
function importTargetedPracticeMetadata(db, sessionId, name, settings, problems) {
  const meta = settings && settings.targeted_practice_metadata;
  if (!meta || meta.mode !== 'targeted-practice') return;
  const targets = Array.isArray(meta.targets) ? meta.targets : [];
  const graduated = Array.isArray(meta.graduated) ? meta.graduated : [];
  const current = meta.current || null;
  db.run(`
    INSERT OR REPLACE INTO TargetedPracticeSessions (
      session_id, user_name, outcome, complete, completion_reason, target_count,
      graduated_count, current_target_key, graduation_streak, fast_ms, percent_target,
      filler_pool_size, problems_presented, targets_json, graduated_json, metadata_json,
      inferred, inference_notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL)
  `, [
    sessionId,
    name,
    parseSessionOutcome(settings),
    meta.complete ? 1 : 0,
    meta.completionReason || null,
    meta.targetCount == null ? targets.length : meta.targetCount,
    graduated.length,
    current && current.key ? current.key : (meta.currentTargetKey || null),
    meta.graduationStreak == null ? null : meta.graduationStreak,
    meta.fastMs == null ? null : meta.fastMs,
    meta.percentTarget == null ? null : meta.percentTarget,
    meta.fillerPoolSize == null ? null : meta.fillerPoolSize,
    meta.problemsPresented == null ? (problems || []).length : meta.problemsPresented,
    JSON.stringify(targets),
    JSON.stringify(graduated),
    JSON.stringify(meta)
  ]);
  const perTarget = Array.isArray(meta.perTarget) ? meta.perTarget : [];
  perTarget.forEach((target, index) => {
    const parsed = target.key ? parseProblemText(problemTextFromKey(target.key)) : { num1: null, operation: null, num2: null };
    db.run(`
      INSERT OR REPLACE INTO TargetedPracticeTargets (
        session_id, target_order, target_key, problem_text, num1, num2, operation,
        graduated, fast_correct, attempts, required_fast_correct, final_streak, inferred
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    `, [
      sessionId,
      index + 1,
      target.key || null,
      problemTextFromKey(target.key),
      parsed.num1,
      parsed.num2,
      parsed.operation,
      target.graduated ? 1 : 0,
      target.fastCorrect == null ? null : target.fastCorrect,
      target.attempts == null ? null : target.attempts,
      target.graduationStreak == null ? meta.graduationStreak : target.graduationStreak,
      target.streak == null ? target.fastCorrect : target.streak
    ]);
  });
  (problems || []).forEach((problem, index) => {
    const targeted = problem.targeted_practice;
    if (!targeted) return;
    db.run(`
      INSERT OR REPLACE INTO TargetedPracticeAttemptRoles (
        session_id, problem_id, attempt_index, problem_text, fact_key, role,
        target_key, current_target_key, target_order, fast_correct, inferred
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    `, [
      sessionId,
      problem.id,
      index + 1,
      problem.problem_text,
      problem.fact_key || null,
      targeted.role || null,
      targeted.target_key || null,
      targeted.current_target_key || null,
      targeted.target_order == null ? null : targeted.target_order,
      targeted.fast_correct ? 1 : 0
    ]);
  });
}
function importVisualPracticeMetadata(db, sessionId, name, settings, problems) {
  const meta = settings && settings.visual_practice_metadata;
  if (!meta || meta.mode !== 'visual-practice') return;
  const targets = Array.isArray(meta.targets) ? meta.targets : [];
  const cleared = Array.isArray(meta.cleared) ? meta.cleared : [];
  db.run(`
    INSERT OR REPLACE INTO VisualPracticeSessions (
      session_id, user_name, outcome, complete, completion_reason, target_count,
      cleared_count, fast_ms, retrievals_to_clear, hesitation_ms, problems_presented,
      targets_json, cleared_json, metadata_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `, [
    sessionId,
    name,
    parseSessionOutcome(settings),
    meta.complete ? 1 : 0,
    meta.completionReason || null,
    meta.targetCount == null ? targets.length : meta.targetCount,
    cleared.length,
    meta.fastMs == null ? null : meta.fastMs,
    meta.retrievalsToClear == null ? null : meta.retrievalsToClear,
    meta.hesitationMs == null ? null : meta.hesitationMs,
    meta.problemsPresented == null ? (problems || []).length : meta.problemsPresented,
    JSON.stringify(targets),
    JSON.stringify(cleared),
    JSON.stringify(meta)
  ]);
  const perTarget = Array.isArray(meta.perTarget) ? meta.perTarget : [];
  perTarget.forEach((target, index) => {
    const problemText = problemTextFromKey(target.key);
    const parsed = problemText ? parseProblemText(problemText) : { num1: null, operation: null, num2: null };
    db.run(`
      INSERT OR REPLACE INTO VisualPracticeTargets (
        session_id, target_order, target_key, problem_text, num1, num2, operation,
        cold_probe_result, teach_count, retrieval_successes, attempts, required_successes, cleared
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [
      sessionId,
      index + 1,
      target.key || null,
      problemText,
      target.num1 == null ? parsed.num1 : target.num1,
      target.num2 == null ? parsed.num2 : target.num2,
      target.operation || parsed.operation,
      target.coldProbe || null,
      target.teachCount == null ? null : target.teachCount,
      target.retrievalSuccesses == null ? null : target.retrievalSuccesses,
      target.attempts == null ? null : target.attempts,
      target.requiredSuccesses == null ? null : target.requiredSuccesses,
      target.cleared ? 1 : 0
    ]);
  });
  (problems || []).forEach((problem, index) => {
    const visual = problem.visual_practice;
    if (!visual) return;
    db.run(`
      INSERT OR REPLACE INTO VisualPracticeAttemptRoles (
        session_id, problem_id, attempt_index, problem_text, fact_key, trial_role,
        target_key, visual_shown, passed
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [
      sessionId,
      problem.id,
      index + 1,
      problem.problem_text,
      problem.fact_key || null,
      visual.trial_role || null,
      visual.target_key || null,
      visual.visual_shown ? 1 : 0,
      visual.passed ? 1 : 0
    ]);
  });
}

/**
 * Escape a value for safe interpolation into HTML markup/attributes
 * @param {*} value - Value to escape (coerced to string; null/undefined -> '')
 * @returns {string} HTML-escaped string
 */
function escapeHtml(value) {
  return String(value === null || value === undefined ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Normalize display operation symbols to canonical forms (* / -)
 * Handles legacy session data that stored "&times;", "×", "&divide;", "÷"
 * @param {string} problemText - Problem text in any symbol form
 * @returns {string} Normalized text like "5 * 3"
 */
function normalizeOperationSymbols(problemText) {
  if (typeof problemText !== 'string') return '';
  return problemText
    .replace(/&times;/g, '*')
    .replace(/×/g, '*')
    .replace(/&divide;/g, '/')
    .replace(/÷/g, '/')
    .replace(/−/g, '-')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Convert canonical problem text to display form (× ÷)
 * @param {string} problemText - Problem text in any symbol form
 * @returns {string} Display text like "5 × 3"
 */
function formatProblemTextForDisplay(problemText) {
  return normalizeOperationSymbols(problemText)
    .replace(/\*/g, '×')
    .replace(/\//g, '÷');
}

/**
 * Parse problem text into components
 * @param {string} problemText - Problem text like "5 + 3" (legacy display
 * symbols such as "5 &times; 3" or "5 × 3" are normalized first)
 * @returns {object} Object with num1, operation, num2
 */
function parseProblemText(problemText) {
  const parts = normalizeOperationSymbols(problemText).split(' ');
  if (parts.length === 3) {
    const parsedNum1 = parseInt(parts[0], 10);
    const parsedNum2 = parseInt(parts[2], 10);
    const num1 = Number.isFinite(parsedNum1) ? parsedNum1 : null;
    const operation = parts[1];
    const num2 = Number.isFinite(parsedNum2) ? parsedNum2 : null;
    return { num1, operation, num2 };
  } else {
    return { num1: null, operation: null, num2: null };
  }
}

/**
 * Check whether a session is already present in the database
 * @param {object} db - SQL.js database instance
 * @param {string} sessionId - Session UUID
 * @returns {boolean} True if a Sessions row exists
 */
function sessionExistsInDb(db, sessionId) {
  const stmt = db.prepare('SELECT 1 FROM Sessions WHERE session_id = ?');
  stmt.bind([sessionId]);
  const exists = stmt.step();
  stmt.free();
  return exists;
}

/**
 * Remove a session and its problem attempts from the database
 * @param {object} db - SQL.js database instance
 * @param {string} sessionId - Session UUID
 */
function deleteSessionFromDb(db, sessionId) {
  db.run('DELETE FROM VisualPracticeAttemptRoles WHERE session_id = ?', [sessionId]);
  db.run('DELETE FROM VisualPracticeTargets WHERE session_id = ?', [sessionId]);
  db.run('DELETE FROM VisualPracticeSessions WHERE session_id = ?', [sessionId]);
  db.run('DELETE FROM TargetedPracticeAttemptRoles WHERE session_id = ?', [sessionId]);
  db.run('DELETE FROM TargetedPracticeTargets WHERE session_id = ?', [sessionId]);
  db.run('DELETE FROM TargetedPracticeSessions WHERE session_id = ?', [sessionId]);
  db.run('DELETE FROM ProblemAttempts WHERE session_id = ?', [sessionId]);
  db.run('DELETE FROM Sessions WHERE session_id = ?', [sessionId]);
}

/**
 * Import session data into the database. Skips sessions already imported —
 * ProblemAttempts has no unique constraint, so re-importing the same session
 * (e.g. the original file plus a *_MODIFIED export) would duplicate attempts.
 * @param {object} db - SQL.js database instance
 * @param {object} data - Session data object
 * @param {string} filename - Source filename
 */
function importSessionData(db, data, filename) {
  const userData = data.user;
  const name = userData.name || 'Unknown';

  const sessionData = data.session;
  if (!sessionData.id) {
    console.error(`Session ID missing in file: ${filename}`);
    return;
  }

  const sessionId = sessionData.id;
  if (sessionExistsInDb(db, sessionId)) {
    console.log(`Session ${sessionId} already imported; skipping ${filename}`);
    return;
  }

  db.run('INSERT OR IGNORE INTO Users (name) VALUES (?)', [name]);

  const startTime = sessionData.start_time;
  const endTime = sessionData.end_time;
  const settings = sessionData.settings || {};
  const summary = sessionData.summary || {};
  const sessionType = sessionTypeFromSettings(settings);

  db.run(`
    INSERT OR IGNORE INTO Sessions (
      session_id, session_filename, user_name, start_time, end_time, num_problems,
      number_range_start, number_range_end, numbers_include, numbers_exclude,
      num_numbers, operations, total_problems, correct_answers, average_response_time_ms,
      session_type
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `, [
    sessionId, filename, name, startTime, endTime,
    settings.num_problems,
    settings.number_range ? settings.number_range[0] : null,
    settings.number_range ? settings.number_range[1] : null,
    JSON.stringify(settings.numbers_include || []),
    JSON.stringify(settings.numbers_exclude || []),
    settings.num_numbers,
    JSON.stringify(settings.operations || []),
    summary.total_problems,
    summary.correct_answers,
    summary.average_response_time_ms,
    sessionType
  ]);

  importTargetedPracticeMetadata(db, sessionId, name, settings, sessionData.problems || []);
  importVisualPracticeMetadata(db, sessionId, name, settings, sessionData.problems || []);

  for (const problem of (sessionData.problems || [])) {
    const { num1, operation, num2 } = parseProblemText(problem.problem_text);
    const flagsJson = problem.flags && Array.isArray(problem.flags) && problem.flags.length > 0
      ? JSON.stringify(problem.flags)
      : null;

    db.run(`
      INSERT OR IGNORE INTO ProblemAttempts (
        session_id, problem_id, problem_text, num1, num2, operation,
        correct_answer, user_answer_string, user_answer, is_correct, response_time_ms, flags_json, presented_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [
      sessionId,
      problem.id,
      problem.problem_text,
      num1,
      num2,
      operation,
      problem.correct_answer,
      problem.user_answer_string,
      problem.user_answer,
      problem.is_correct ? 1 : 0,
      problem.response_time_ms,
      flagsJson,
      problem.presented_at || null
    ]);
  }
}

/**
 * Import all session JSON data from localStorage into database
 * @param {object} db - SQL.js database instance
 */
function importJsonDataToDb(db) {
  let importedCount = 0;
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key.startsWith('math_session_') && key.endsWith('.json')) {
      try {
        const jsonData = JSON.parse(localStorage.getItem(key));
        importSessionData(db, jsonData, key);
        importedCount++;
      } catch (error) {
        console.error(`Skipping corrupted session entry ${key}:`, error);
      }
    }
  }
  console.log(`Imported ${importedCount} session file(s) from localStorage for this page origin (${window.location.origin})`);
}

/**
 * Parse session timestamp string into Date object
 * @param {string} timestamp - Timestamp string like "2024-10-11_104410"
 * @returns {Date|null} Parsed Date or null if invalid
 */
function parseSessionTimestamp(timestamp) {
  if (!timestamp || typeof timestamp !== 'string') {
    return null;
  }
  const [datePart, timePart] = timestamp.split('_');
  if (!timePart) {
    const parsed = Date.parse(timestamp);
    return Number.isNaN(parsed) ? null : new Date(parsed);
  }
  const [year, month, day] = datePart.split('-').map(Number);
  const hours = Number(timePart.substring(0, 2));
  const minutes = Number(timePart.substring(2, 4));
  const seconds = Number(timePart.substring(4, 6));
  if ([year, month, day].some(isNaN) || [hours, minutes, seconds].some(isNaN)) {
    return null;
  }
  return new Date(year, month - 1, day, hours, minutes, seconds);
}

/**
 * Extract YYYY-MM-DD_HHMMSS from a session filename so mixed prefixes
 * (math-flu_, math-quest_, mathquest_, anchor_) sort by real recency.
 * @param {string} filename
 * @returns {string|null}
 */
function extractSessionStampFromFilename(filename) {
  if (!filename || typeof filename !== 'string') return null;
  const match = filename.match(/(\d{4}-\d{2}-\d{2}_\d{6})/);
  return match ? match[1] : null;
}

/**
 * Sort key for session recency: filename stamp, else Sessions.start_time, else ''.
 * Higher / lexicographically greater = more recent for YYYY-MM-DD_HHMMSS stamps.
 */
function sessionRecencyKey(filename, startTime) {
  return extractSessionStampFromFilename(filename) || startTime || '';
}

/**
 * Compute median of an array of numbers
 * @param {number[]} values - Array of numbers
 * @returns {number|null} Median value or null if empty
 */
function computeMedian(values) {
  if (!values.length) {
    return null;
  }
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
}

/**
 * Update session count display element
 */
function updateSessionCount() {
  const sessionCountDiv = document.getElementById('session-count');
  if (!sessionCountDiv) return;
  
  const sessionFiles = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key.startsWith('math_session_') && key.endsWith('.json')) {
      sessionFiles.push(key);
    }
  }
  
  sessionCountDiv.textContent = `Current sessions in storage: ${sessionFiles.length}`;
}

/**
 * Load session files from file input
 * @param {FileList} files - Files to load
 * @param {object} db - SQL.js database instance
 * @param {HTMLElement} statusDiv - Status display element
 * @param {Function} onComplete - Callback when loading completes (receives loadedCount, errorCount)
 */
function loadSessionFiles(files, db, statusDiv, onComplete) {
  let loadedCount = 0;
  let errorCount = 0;
  const totalFiles = files.length;
  
  statusDiv.textContent = `Loading ${totalFiles} file(s)...`;
  statusDiv.style.color = 'blue';
  
  Array.from(files).forEach((file, index) => {
    const reader = new FileReader();
    
    reader.onload = function(e) {
      try {
        const jsonData = JSON.parse(e.target.result);
        
        if (!jsonData.session || !jsonData.user) {
          throw new Error('Invalid session file format');
        }

        // Re-uploading an existing session replaces it (e.g. a *_MODIFIED export)
        if (jsonData.session.id) {
          deleteSessionFromDb(db, jsonData.session.id);
        }
        importSessionData(db, jsonData, file.name);
        // Store under the canonical session key so renamed or *_MODIFIED files
        // overwrite the original entry instead of duplicating the session
        const storageKey = jsonData.session.start_time
          ? `math_session_${jsonData.user.name || 'Unknown'}_${jsonData.session.start_time}.json`
          : file.name;
        try {
          localStorage.setItem(storageKey, JSON.stringify(jsonData, null, 2));
        } catch (storageError) {
          console.warn(`Could not persist ${storageKey} to localStorage:`, storageError);
        }

        loadedCount++;
        if (loadedCount + errorCount === totalFiles) {
          statusDiv.textContent = `Loaded ${loadedCount} file(s)${errorCount > 0 ? `, ${errorCount} error(s)` : ''}. Refreshing...`;
          statusDiv.style.color = 'green';
          updateSessionCount();
          if (onComplete) onComplete(loadedCount, errorCount);
        }
      } catch (error) {
        console.error(`Error loading file ${file.name}:`, error);
        errorCount++;
        if (loadedCount + errorCount === totalFiles) {
          statusDiv.textContent = `Loaded ${loadedCount} file(s)${errorCount > 0 ? `, ${errorCount} error(s)` : ''}.`;
          statusDiv.style.color = errorCount > 0 ? 'red' : 'green';
          updateSessionCount();
          if (loadedCount > 0 && onComplete) onComplete(loadedCount, errorCount);
        }
      }
    };
    
    reader.onerror = function() {
      console.error(`Error reading file ${file.name}`);
      errorCount++;
      if (loadedCount + errorCount === totalFiles) {
        statusDiv.textContent = `Loaded ${loadedCount} file(s), ${errorCount} error(s).`;
        statusDiv.style.color = 'red';
        updateSessionCount();
        if (loadedCount > 0 && onComplete) onComplete(loadedCount, errorCount);
      }
    };
    
    reader.readAsText(file);
  });
}

// END OF FILE math_utils.js
