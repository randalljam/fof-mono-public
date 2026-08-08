// START OF FILE math_fluency.js

var fileInfo = `math_fluency.js - Fluency Tracker (Refactored)`;
console.log('Fluency Tracker JavaScript file loaded. ', fileInfo);

// Shared utility functions are now in math_utils.js

let db;
let sqlJs = null;   // the initialized SQL.js module, for loading .sqlite files later
let fluencyDatasets = {
  addition: { current: {}, previous: {}, combined: {} },
  subtraction: { current: {}, previous: {}, combined: {} },
  multiplication: { current: {}, previous: {}, combined: {} }
};

// Raw attempts (with flags + session start_time) for the current user selection —
// the input to the shared app-wide fluencyPercent metric (fluency_core.js).
let rawFluencyAttempts = [];

// defaultFluencyThresholds, fluencyStatusColors, STATUS_LABELS,
// evaluateFluencyStatus, and checkPermanentStatus now live in fluency_core.js
// (shared with the analysis page + the engine). fluency_core.js must load before
// this file.

// Manual overrides storage
const MANUAL_OVERRIDES_KEY = 'math_fluency_manual_overrides';

function getCurrentDatetimeFileFriendly() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  return `${year}-${month}-${day}_${hours}${minutes}${seconds}`;
}

function loadManualOverrides(username) {
  try {
    const stored = localStorage.getItem(MANUAL_OVERRIDES_KEY);
    if (!stored) return {};
    const all = JSON.parse(stored);
    return all[username] || {};
  } catch (e) {
    console.error('Error loading manual overrides:', e);
    return {};
  }
}

function saveManualOverride(username, problemKey, status, reason = '', calculatedStatus = null) {
  try {
    const stored = localStorage.getItem(MANUAL_OVERRIDES_KEY);
    const all = stored ? JSON.parse(stored) : {};
    if (!all[username]) all[username] = {};
    
    if (status === null) {
      // Remove override
      delete all[username][problemKey];
    } else {
      // Set override
      all[username][problemKey] = {
        status,
        timestamp: getCurrentDatetimeFileFriendly(),
        reason,
        calculatedStatus
      };
    }
    
    localStorage.setItem(MANUAL_OVERRIDES_KEY, JSON.stringify(all));
    return true;
  } catch (e) {
    console.error('Error saving manual override:', e);
    return false;
  }
}

function getManualOverride(username, problemKey) {
  const overrides = loadManualOverrides(username);
  return overrides[problemKey] || null;
}

function clearManualOverrides(username) {
  try {
    const stored = localStorage.getItem(MANUAL_OVERRIDES_KEY);
    if (!stored) return;
    const all = JSON.parse(stored);
    delete all[username];
    localStorage.setItem(MANUAL_OVERRIDES_KEY, JSON.stringify(all));
    return true;
  } catch (e) {
    console.error('Error clearing manual overrides:', e);
    return false;
  }
}

// Problem list visibility state
const problemListVisibility = {
  addition: true,
  subtraction: true,
  multiplication: true
};

// Toggle problem list visibility
function toggleProblemList(operation) {
  const content = document.getElementById(`${operation}-problems`);
  const btn = document.getElementById(`${operation}-toggle-btn`);
  
  if (content && btn) {
    problemListVisibility[operation] = !problemListVisibility[operation];
    if (problemListVisibility[operation]) {
      content.classList.remove('hidden');
      btn.textContent = 'Hide';
    } else {
      content.classList.add('hidden');
      btn.textContent = 'Show';
    }
  }
}

// Make toggleProblemList globally available
window.toggleProblemList = toggleProblemList;

// Normalize commutative problems (for + and *)
function normalizeCommutativeProblem(num1, num2, operation) {
  if (operation === '+' || operation === '*') {
    return [Math.min(num1, num2), Math.max(num1, num2)];
  }
  return [num1, num2];
}

// Get canonical key for a problem (handles commutativity)
function getCanonicalProblemKey(num1, num2, operation) {
  const [n1, n2] = normalizeCommutativeProblem(num1, num2, operation);
  return `${operation}|${n1}|${n2}`;
}

// Test SQL.js initialization
console.log("Initializing SQL.js...");
const sqlJsUrl = 'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.6.2/sql-wasm.js';

const sqlScript = document.createElement('script');
sqlScript.src = sqlJsUrl;
sqlScript.onload = function() {
  console.log("SQL.js script loaded successfully.");
  loadPlotly();
};
sqlScript.onerror = function() {
  console.error("Failed to load SQL.js script.");
  alert('Failed to load SQL.js. Please check your internet connection and try again.');
};
document.head.appendChild(sqlScript);

function loadPlotly() {
  console.log("Loading Plotly...");
  const plotlyScript = document.createElement('script');
  // Pinned: this is the version the retired plotly-latest alias resolves to
  plotlyScript.src = "https://cdn.plot.ly/plotly-1.58.5.min.js";
  plotlyScript.onload = function() {
    console.log("Plotly loaded successfully");
    initializeDatabase();
  };
  plotlyScript.onerror = function() {
    console.error("Failed to load Plotly");
    alert('Failed to load Plotly. Please check your internet connection and try again.');
  };
  document.head.appendChild(plotlyScript);
}

function initializeDatabase() {
  if (db) return;
  initSqlJs({ locateFile: file => 'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.6.2/' + file }).then(async SQL => {
    sqlJs = SQL;
    // Prefer the per-person SQLite the analysis page has loaded (shared working
    // DB in IndexedDB) so "whatever is loaded in analysis" shows here too.
    // Otherwise build from the legacy session JSON in localStorage.
    let workingBytes = null;
    if (typeof loadSharedWorkingDb === 'function') {
      try { workingBytes = await loadSharedWorkingDb(); } catch (e) { workingBytes = null; }
    }
    if (workingBytes) {
      db = new SQL.Database(new Uint8Array(workingBytes));
      createTables(db);   // ensure aux tables (e.g. ProblemLists) exist — CREATE IF NOT EXISTS
      console.log('Loaded shared per-person SQLite (from the analysis page)');
    } else {
      db = new SQL.Database();
      createTables(db);
      importJsonDataToDb(db);
      console.log('Database created from session JSON');
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => setupFluencyPage(db));
    } else {
      setupFluencyPage(db);
    }
  }).catch(error => {
    console.error('Error initializing SQL.js:', error.message);
    alert('Failed to initialize SQL.js.');
  });
}

function populateUsernameDropdown(db) {
  const userSelect = document.getElementById('fluency-user');
  if (!userSelect) return;
  
  userSelect.innerHTML = '<option value="all">All Users</option>';
  
  const query = "SELECT DISTINCT user_name FROM Sessions ORDER BY user_name";
  try {
    const stmt = db.prepare(query);
    while (stmt.step()) {
      const row = stmt.getAsObject();
      const option = document.createElement('option');
      option.value = row.user_name;
      option.textContent = row.user_name;
      userSelect.appendChild(option);
    }
    stmt.free();
  } catch (error) {
    console.error('Error populating username dropdown:', error);
  }
}

// evaluateFluencyStatus + checkPermanentStatus moved to fluency_core.js.

function prepareFluencyDatasets(db, thresholds, username = 'all') {
  const operations = ['+', '-', '*'];
  const operationNames = { '+': 'addition', '-': 'subtraction', '*': 'multiplication' };
  
  // Reset datasets
  fluencyDatasets = {
    addition: { current: {}, previous: {}, combined: {}, metadata: {} },
    subtraction: { current: {}, previous: {}, combined: {}, metadata: {} },
    multiplication: { current: {}, previous: {}, combined: {}, metadata: {} }
  };

  let query = `
    SELECT
      Sessions.session_id as session_id,
      Sessions.start_time as start_time,
      Sessions.end_time as end_time,
      ProblemAttempts.problem_text as problem_text,
      ProblemAttempts.num1 as num1,
      ProblemAttempts.num2 as num2,
      ProblemAttempts.operation as operation,
      ProblemAttempts.correct_answer as correct_answer,
      ProblemAttempts.user_answer as user_answer,
      ProblemAttempts.is_correct as is_correct,
      ProblemAttempts.response_time_ms as response_time_ms
    FROM ProblemAttempts
    INNER JOIN Sessions ON ProblemAttempts.session_id = Sessions.session_id
    WHERE 1=1${sessionTypeExclusionSql(db, 'Sessions')}
  `;
  
  if (username !== 'all') {
    query += ` AND Sessions.user_name = ?`;
  }

  // Track attempts by canonical problem key
  const problemAttempts = {};
  const attemptsBySession = {};
  let latestSessionId = null;
  let latestSessionEnd = null;

  try {
    const stmt = db.prepare(query);
    if (username !== 'all') stmt.bind([username]);
    
    while (stmt.step()) {
      const row = stmt.getAsObject();
      const parsed = parseProblemText(row.problem_text || '');
      const num1 = (typeof row.num1 === 'number' && Number.isFinite(row.num1)) ? row.num1 : parsed.num1;
      const num2 = (typeof row.num2 === 'number' && Number.isFinite(row.num2)) ? row.num2 : parsed.num2;
      const operation = row.operation || parsed.operation;
      
      if (num1 === null || num2 === null || !operation) continue;
      if (!operations.includes(operation)) continue;
      
      // Use canonical key for commutative operations
      const problemKey = getCanonicalProblemKey(num1, num2, operation);
      const [canonNum1, canonNum2] = normalizeCommutativeProblem(num1, num2, operation);
      
      const timestamp = parseSessionTimestamp(row.end_time) || parseSessionTimestamp(row.start_time) || new Date();
      
      if (!problemAttempts[problemKey]) {
        problemAttempts[problemKey] = {
          operation,
          num1: canonNum1,
          num2: canonNum2,
          attempts: [],
          lastSessionId: null,
          lastSessionTimestamp: null
        };
      }
      
      const attempt = {
        sessionId: row.session_id,
        timestamp,
        responseTime: typeof row.response_time_ms === 'number' ? row.response_time_ms : null,
        isCorrect: row.is_correct === 1 || row.is_correct === true
      };
      
      problemAttempts[problemKey].attempts.push(attempt);
      
      if (!problemAttempts[problemKey].lastSessionTimestamp || timestamp > problemAttempts[problemKey].lastSessionTimestamp) {
        problemAttempts[problemKey].lastSessionId = row.session_id;
        problemAttempts[problemKey].lastSessionTimestamp = timestamp;
      }

      if (!attemptsBySession[row.session_id]) {
        attemptsBySession[row.session_id] = { endTime: timestamp, attempts: {} };
      }
      if (!attemptsBySession[row.session_id].attempts[problemKey]) {
        attemptsBySession[row.session_id].attempts[problemKey] = [];
      }
      attemptsBySession[row.session_id].attempts[problemKey].push(attempt);

      if (!latestSessionEnd || (timestamp && timestamp > latestSessionEnd)) {
        latestSessionEnd = timestamp;
        latestSessionId = row.session_id;
      }
    }
    stmt.free();
  } catch (error) {
    console.error('Error preparing fluency datasets:', error);
    return;
  }

  // Build session order for retention tracking
  const orderedSessions = [];
  const sessionRecencyMap = {};
  try {
    let sessionOrderQuery = 'SELECT session_id, end_time FROM Sessions';
    if (username !== 'all') sessionOrderQuery += ` WHERE user_name = ?`;
    sessionOrderQuery += ' ORDER BY end_time DESC';
    
    const sessionStmt = db.prepare(sessionOrderQuery);
    if (username !== 'all') sessionStmt.bind([username]);
    while (sessionStmt.step()) {
      orderedSessions.push(sessionStmt.getAsObject().session_id);
    }
    sessionStmt.free();
    orderedSessions.forEach((sid, idx) => { sessionRecencyMap[sid] = idx; });
  } catch (error) {
    console.warn('Error building session order:', error);
  }
  
  const totalSessions = orderedSessions.length;
  const retentionThreshold = thresholds.retentionSessions || 3;
  const permanentThreshold = thresholds.permanentSessions || 5;

  // Sort attempts and build datasets
  Object.values(problemAttempts).forEach(problem => {
    problem.attempts.sort((a, b) => (a.timestamp?.getTime() || 0) - (b.timestamp?.getTime() || 0));
  });

  // Build status history per session for each problem (for permanent status check)
  // We need to evaluate status for each session the problem appeared in
  const problemStatusHistory = {};
  
  // Get ordered session IDs (oldest first for history tracking)
  const sessionsOldestFirst = [...orderedSessions].reverse();
  
  sessionsOldestFirst.forEach(sessionId => {
  Object.entries(problemAttempts).forEach(([key, problem]) => {
      if (attemptsBySession[sessionId]?.attempts[key]) {
        const sessionAttempts = attemptsBySession[sessionId].attempts[key];
        const sessionMetrics = evaluateFluencyStatus(sessionAttempts, thresholds);
        
        if (!problemStatusHistory[key]) {
          problemStatusHistory[key] = [];
        }
        problemStatusHistory[key].push(sessionMetrics.status);
      }
    });
  });

  // Process each problem into operation-specific datasets
  Object.entries(problemAttempts).forEach(([key, problem]) => {
    const opName = operationNames[problem.operation];
    if (!opName) return;
    
    const previousMetrics = evaluateFluencyStatus(problem.attempts, thresholds);
    
    const currentAttempts = latestSessionId && attemptsBySession[latestSessionId]?.attempts[key]
      ? attemptsBySession[latestSessionId].attempts[key]
      : [];
    const currentMetrics = evaluateFluencyStatus(currentAttempts, thresholds);

    // Calculate sessions since last practice
    const lastSessionId = problem.lastSessionId;
    const sessionsSinceLastPractice = lastSessionId && sessionRecencyMap[lastSessionId] !== undefined
      ? sessionRecencyMap[lastSessionId]
      : totalSessions;
    const needsRecheck = sessionsSinceLastPractice >= retentionThreshold;

    // Check for permanent (blue) status
    const statusHistory = problemStatusHistory[key] || [];
    const isPermanent = checkPermanentStatus(statusHistory, permanentThreshold);

    const baseData = {
      key,
      operation: problem.operation,
      num1: problem.num1,
      num2: problem.num2,
      attemptCount: problem.attempts.length,
      lastAttemptAt: problem.attempts.length ? problem.attempts[problem.attempts.length - 1].timestamp : null,
      sessionsSinceLastPractice,
      needsRecheck,
      statusHistory,
      isPermanent
    };

    // Get manual override (apply to all datasets if exists)
    const overrideUsername = username === 'all' ? 'default' : username;
    const manualOverride = getManualOverride(overrideUsername, key);
    
    // Helper function to apply the calculated status (e.g. the green->blue
    // permanent upgrade) and any manual override to a problem object
    function applyOverrideToProblem(problemObj, calculatedStatus) {
      problemObj.calculatedStatus = calculatedStatus;
      if (manualOverride) {
        problemObj.status = manualOverride.status;
        problemObj.manualOverride = true;
        problemObj.overrideReason = manualOverride.reason;
        problemObj.overrideTimestamp = manualOverride.timestamp;
      } else {
        problemObj.status = calculatedStatus;
        problemObj.manualOverride = false;
      }
      return problemObj;
    }
    
    // Create previous object and apply override
    const previousData = applyOverrideToProblem({ ...baseData, ...previousMetrics }, previousMetrics.status);
    
    // Create current object and apply override
    const currentData = applyOverrideToProblem({
      ...baseData, 
      ...currentMetrics,
      attemptCount: currentAttempts.length,
      lastAttemptAt: currentAttempts.length ? currentAttempts[currentAttempts.length - 1].timestamp : null
    }, currentMetrics.status);
    
    // Combined uses latest if available, else historical
    let combinedCalculatedStatus = currentAttempts.length && currentMetrics.status !== 'nodata'
      ? currentMetrics.status
      : previousMetrics.status;
    
    // Upgrade green → blue if permanent (before override)
    if (combinedCalculatedStatus === 'green' && isPermanent) {
      combinedCalculatedStatus = 'blue';
    }
    
    const combined = currentAttempts.length && currentMetrics.status !== 'nodata'
      ? { ...currentData }
      : { ...previousData };
    combined.needsRecheck = needsRecheck;
    combined.sessionsSinceLastPractice = sessionsSinceLastPractice;
    
    // Apply override to combined (override takes precedence over permanent upgrade)
    applyOverrideToProblem(combined, combinedCalculatedStatus);
    
    fluencyDatasets[opName].previous[key] = previousData;
    fluencyDatasets[opName].current[key] = currentData;
    fluencyDatasets[opName].combined[key] = combined;
  });

  // Store metadata
  ['addition', 'subtraction', 'multiplication'].forEach(op => {
    fluencyDatasets[op].metadata = {
      latestSessionId,
      thresholds,
      totalSessions
  };
  });
  
  console.log('Fluency datasets prepared', fluencyDatasets);
}

function parseFluencyNumberRange(value) {
  if (!value || value === 'all') return null;
  const [start, end] = value.split('-').map(Number);
  if (Number.isNaN(start) || Number.isNaN(end)) return null;
  return { start: Math.min(start, end), end: Math.max(start, end) };
}

function getFluencySettings() {
  const userSelect = document.getElementById('fluency-user');
  const numberRangeSelect = document.getElementById('fluency-number-range');
  const windowSizeInput = document.getElementById('fluency-window-size');
  const minAccuracyInput = document.getElementById('fluency-min-accuracy');
  const greenThresholdInput = document.getElementById('fluency-green-ms');
  const redThresholdInput = document.getElementById('fluency-red-ms');
  const retentionSessionsInput = document.getElementById('fluency-retention-sessions');
  const permanentSessionsInput = document.getElementById('fluency-permanent-sessions');

  return {
    username: userSelect?.value || 'all',
    numberRange: parseFluencyNumberRange(numberRangeSelect?.value),
    windowSize: parseInt(windowSizeInput?.value, 10) || 5,
    minAccuracy: (parseFloat(minAccuracyInput?.value) || 80) / 100,
    greenMs: parseInt(greenThresholdInput?.value, 10) || 2000,
    redMs: parseInt(redThresholdInput?.value, 10) || 4000,
    retentionSessions: parseInt(retentionSessionsInput?.value, 10) || 3,
    permanentSessions: parseInt(permanentSessionsInput?.value, 10) || 5
  };
}

function filterProblems(dataset, settings) {
  if (!dataset) return [];
  return Object.values(dataset).filter(problem => {
    if (!problem) return false;
    if (settings.numberRange) {
      const { start, end } = settings.numberRange;
      if (problem.num1 < start || problem.num1 > end) return false;
      if (problem.num2 < start || problem.num2 > end) return false;
    }
    return true;
  });
}

function getStatusColor(status) {
  return fluencyStatusColors[status] || fluencyStatusColors.gray;
}

// Pull the user's raw attempts (problem text, correctness, time, flags, session order)
// straight from the DB. This feeds fluencyPercent — the app-wide fluency number shared
// with the anchor end-of-quiz readout, the Fluency feast, and the analysis page.
// Visual-practice sessions are excluded (same rule as every other fluency feed).
function collectRawFluencyAttempts(db, username) {
  let query = `
    SELECT ProblemAttempts.problem_text, ProblemAttempts.is_correct,
           ProblemAttempts.response_time_ms, ProblemAttempts.flags_json,
           ProblemAttempts.attempt_id, ProblemAttempts.session_id,
           Sessions.start_time
    FROM ProblemAttempts
    INNER JOIN Sessions ON ProblemAttempts.session_id = Sessions.session_id
    WHERE 1=1${sessionTypeExclusionSql(db, 'Sessions')}
  `;
  if (username !== 'all') query += ' AND Sessions.user_name = ?';
  query += ' ORDER BY Sessions.start_time, ProblemAttempts.attempt_id';
  const out = [];
  try {
    const stmt = db.prepare(query);
    if (username !== 'all') stmt.bind([username]);
    while (stmt.step()) out.push(stmt.getAsObject());
    stmt.free();
  } catch (error) {
    console.error('Error collecting raw attempts for fluency percent:', error);
  }
  return out;
}

// The single app-wide fluency % for one operation: share of the FULL fact universe
// (default 0-9 grid) that is fluent, via the shared fluencyPercent rubric. Uses the
// page's rubric controls so parameter changes (window, accuracy, ms thresholds) are
// reflected immediately. This intentionally replaces the old attempted-facts-only %.
function universeFluencyPercent(operation, settings) {
  if (typeof fluencyPercent !== 'function') return 0;
  const opSymbol = { addition: '+', subtraction: '-', multiplication: '*' }[operation];
  if (!opSymbol) return 0;
  const thresholds = {
    windowSize: settings.windowSize,
    minAccuracy: settings.minAccuracy,
    greenMs: settings.greenMs,
    redMs: settings.redMs
  };
  const numberRange = settings.numberRange
    ? [settings.numberRange.start, settings.numberRange.end]
    : [0, 9];
  return fluencyPercent(rawFluencyAttempts, thresholds, {
    numberRange, operations: [opSymbol], excludeFlagged: true
  });
}

// calculateFluencyPercentage (fluent / attempted facts) was removed 2026-07-03: the page
// now shows the app-wide fluencyPercent (fluency_core.js) — fluent share of the FULL fact
// universe — so one number is used everywhere (anchor, feast, analysis, dragon game).
function renderFluencyPercentage(operation, settings) {
  const percentage = universeFluencyPercent(operation, settings);

  const percentEl = document.getElementById(`${operation}-percentage`);
  const progressEl = document.getElementById(`${operation}-progress`);

  if (percentEl) {
    percentEl.textContent = `${percentage}%`;
    percentEl.className = 'fluency-percentage-value';
    if (percentage >= 80) percentEl.classList.add('high');
    else if (percentage >= 50) percentEl.classList.add('medium');
    else percentEl.classList.add('low');
  }

  if (progressEl) {
    progressEl.style.width = `${percentage}%`;
    progressEl.className = 'fluency-progress-fill';
    if (percentage >= 80) progressEl.classList.add('high');
    else if (percentage >= 50) progressEl.classList.add('medium');
    else progressEl.classList.add('low');
  }
}

function renderFluencyMap(problems, elementId, operation) {
  const container = document.getElementById(elementId);
  if (!container) return;

  if (!problems.length) {
    container.innerHTML = '<div class="no-data-message">No data available</div>';
    if (typeof Plotly !== 'undefined') Plotly.purge(container);
    return;
  }

  if (typeof Plotly === 'undefined') {
    console.warn('Plotly not available');
    return;
  }

  const xValues = problems.map(p => p.num2);
  const yValues = problems.map(p => p.num1);
  
  const hoverTexts = problems.map(p => {
    const medianText = typeof p.medianMs === 'number' ? `${Math.round(p.medianMs)} ms` : 'n/a';
    const accuracyText = typeof p.accuracy === 'number' ? `${Math.round(p.accuracy * 100)}%` : 'n/a';
    const statusLabel = STATUS_LABELS[p.status] || p.status;
    const overrideText = p.manualOverride ? ' (Manual Override)' : '';
    const recheckText = p.needsRecheck ? '<br>⏰ Needs re-check' : '';
    return `${p.num1} ${p.operation} ${p.num2}<br>Status: ${statusLabel}${overrideText}<br>Median: ${medianText}<br>Accuracy: ${accuracyText}${recheckText}<br>Click to edit`;
  });

  // Use status colors for all operations
  const markerColors = problems.map(p => getStatusColor(p.status));

  const markerLineColors = problems.map(p => p.needsRecheck ? '#1565c0' : '#333');
  const markerLineWidths = problems.map(p => p.needsRecheck ? 3 : 1);

  const trace = {
    x: xValues,
    y: yValues,
    text: hoverTexts,
    mode: 'markers',
    type: 'scatter',
    hoverinfo: 'text',
    marker: {
      color: markerColors,
      size: 20,
      line: { color: markerLineColors, width: markerLineWidths }
    }
  };

  const layout = {
    xaxis: { title: 'Second Number', dtick: 1 },
    yaxis: { title: 'First Number', dtick: 1 },
    margin: { l: 50, r: 20, t: 20, b: 50 },
    hovermode: 'closest',
    height: 300
  };

  container.innerHTML = '';
  Plotly.newPlot(container, [trace], layout, { displayModeBar: false, responsive: true }).then(() => {
    // Set up click handler for manual status editing
    container.on('plotly_click', (data) => {
      const pointIndex = data.points[0].pointNumber;
      const problem = problems[pointIndex];
      
      if (problem) {
        // Get operation name from element ID (e.g., "addition-current" -> "addition")
        const operation = elementId.replace('-current', '').replace('-previous', '');
        showStatusEditDialog(problem, operation);
      }
    });
  });
}

function renderSummaryStats(operation, combinedProblems) {
  const container = document.getElementById(`${operation}-stats`);
  if (!container) return;

  const statusCounts = { blue: 0, green: 0, yellow: 0, red: 0, gray: 0, nodata: 0 };
  let recheckCount = 0;
  
  combinedProblems.forEach(p => {
    statusCounts[p.status] = (statusCounts[p.status] || 0) + 1;
    if (p.needsRecheck) recheckCount++;
  });

    container.innerHTML = `
    <div class="stat-item">
      <div class="stat-value" style="color: ${fluencyStatusColors.blue}">${statusCounts.blue}</div>
      <div class="stat-label">Permanent</div>
    </div>
    <div class="stat-item">
      <div class="stat-value" style="color: ${fluencyStatusColors.green}">${statusCounts.green}</div>
      <div class="stat-label">Fluent</div>
    </div>
    <div class="stat-item">
      <div class="stat-value" style="color: ${fluencyStatusColors.yellow}">${statusCounts.yellow}</div>
      <div class="stat-label">Almost</div>
    </div>
    <div class="stat-item">
      <div class="stat-value" style="color: ${fluencyStatusColors.red}">${statusCounts.red}</div>
      <div class="stat-label">Slow</div>
    </div>
    <div class="stat-item">
      <div class="stat-value" style="color: ${fluencyStatusColors.gray}">${statusCounts.gray}</div>
      <div class="stat-label">Incorrect</div>
    </div>
    <div class="stat-item">
      <div class="stat-value" style="color: #1565c0">${recheckCount}</div>
      <div class="stat-label">Need Re-check</div>
    </div>
    <div class="stat-item">
      <div class="stat-value">${combinedProblems.length}</div>
      <div class="stat-label">Total Problems</div>
      </div>
    `;
}

function renderProblemList(operation, combinedProblems) {
  const grid = document.getElementById(`${operation}-problem-grid`);
  if (!grid) return;

  // Get problems needing work: gray (incorrect), red, yellow, or needs recheck
  const problemsNeedingWork = combinedProblems.filter(p => 
    p.status === 'gray' || p.status === 'red' || p.status === 'yellow' || p.needsRecheck
  );

  // Sort: gray (incorrect) first, then red, then yellow, then recheck-only
  problemsNeedingWork.sort((a, b) => {
    const priority = { gray: 0, red: 1, yellow: 2 };
    const aPriority = priority[a.status] ?? (a.needsRecheck ? 3 : 4);
    const bPriority = priority[b.status] ?? (b.needsRecheck ? 3 : 4);
    return aPriority - bPriority;
  });

  if (problemsNeedingWork.length === 0) {
    grid.innerHTML = '<div class="no-data-message">All problems are fluent! 🎉</div>';
    return;
  }

  grid.innerHTML = problemsNeedingWork.map(p => {
    let className = 'problem-item';
    if (p.status === 'gray') className += ' gray';
    else if (p.status === 'red') className += ' red';
    else if (p.status === 'yellow') className += ' yellow';
    else if (p.needsRecheck) className += ' recheck';
    if (p.manualOverride) className += ' manual-override';
    
    const symbol = p.operation === '*' ? '×' : p.operation;
    const statusLabel = STATUS_LABELS[p.status] || p.status;
    return `<div class="${className} problem-item-clickable" 
            data-key="${p.key}" 
            data-operation="${operation}"
            style="cursor: pointer;"
            title="Status: ${statusLabel}${p.needsRecheck ? ' (needs re-check)' : ''} - Click to edit">${p.num1} ${symbol} ${p.num2}${p.manualOverride ? ' <span class="override-indicator">⭐</span>' : ''}</div>`;
  }).join('');
}

function renderOperationSection(operation, settings) {
  const opData = fluencyDatasets[operation];
  if (!opData) return;

  const currentProblems = filterProblems(opData.current, settings);
  const previousProblems = filterProblems(opData.previous, settings);
  const combinedProblems = filterProblems(opData.combined, settings);

  renderFluencyPercentage(operation, settings);
  renderFluencyMap(currentProblems, `${operation}-current`, operation);
  renderFluencyMap(previousProblems, `${operation}-previous`, operation);
  renderSummaryStats(operation, combinedProblems);
  renderProblemList(operation, combinedProblems);
}

function refreshFluencySection(db) {
  if (!db) {
    console.warn('Database not initialized');
    return;
  }
  
  const settings = getFluencySettings();
  const thresholds = {
    windowSize: settings.windowSize,
    minAccuracy: settings.minAccuracy,
    greenMs: settings.greenMs,
    redMs: settings.redMs,
    retentionSessions: settings.retentionSessions,
    permanentSessions: settings.permanentSessions
  };
  
  prepareFluencyDatasets(db, thresholds, settings.username);
  rawFluencyAttempts = collectRawFluencyAttempts(db, settings.username);

  renderFluencyOverview(settings);
  renderOperationSection('addition', settings);
  renderOperationSection('subtraction', settings);
  renderOperationSection('multiplication', settings);
}

// High-level roll-up dashboard (the page's landing view): per operation, the
// operation-level rating + % fluent, the broad 0-5 vs 6-9 split, and (for
// addition) the categories — each via the shared min/worst-of roll-up rule.
function renderFluencyOverview(settings) {
  const container = document.getElementById('fluency-overview');
  if (!container || typeof fluencyRollupStatus !== 'function') return;

  const ops = [
    { key: 'addition', label: '➕ Addition', hasCats: true },
    { key: 'subtraction', label: '➖ Subtraction', hasCats: false },
    { key: 'multiplication', label: '✖️ Multiplication', hasCats: false }
  ];
  const dot = (status) => `<span class="fo-dot" style="background:${fluencyStatusColors[status] || '#ccc'}"></span>`;
  const chip = (label, status, title) =>
    `<span class="fo-chip" title="${title || ''}">${dot(status)}<span style="font-weight:600">${label}</span>` +
    `<span style="color:${fluencyStatusColors[status] || '#888'};font-weight:600">${STATUS_LABELS[status] || status}</span></span>`;
  const titleOf = (facts) => {
    const b = fluencyStatusBreakdown(facts.map(f => f.status));
    return `${b.blue} permanent · ${b.green} fluent · ${b.yellow} almost · ${b.red} needs practice · ${b.gray} incorrect · ${b.nodata} no data`;
  };

  container.innerHTML = ops.map(op => {
    const facts = (typeof filterProblems === 'function')
      ? filterProblems(fluencyDatasets[op.key].combined, settings)
      : Object.values(fluencyDatasets[op.key]?.combined || {});
    const observed = facts.filter(f => f.status && f.status !== 'nodata');
    if (!observed.length) {
      return `<div class="fo-card"><div class="fo-head"><h3 class="fo-title">${op.label}</h3></div>` +
        `<div class="fo-note">No data yet.</div></div>`;
    }
    const opStatus = fluencyRollupStatus(observed.map(f => f.status));
    const pct = universeFluencyPercent(op.key, settings);

    const easy = observed.filter(f => Math.max(f.num1, f.num2) <= 5);
    const hard = observed.filter(f => Math.max(f.num1, f.num2) >= 6);
    let rangeChips = '';
    if (easy.length) rangeChips += chip('0–5', fluencyRollupStatus(easy.map(f => f.status)), titleOf(easy));
    if (hard.length) rangeChips += chip('6–9', fluencyRollupStatus(hard.map(f => f.status)), titleOf(hard));

    let catBlock;
    if (op.hasCats) {
      let catChips = '';
      FLUENCY_CATEGORY_ORDER.forEach(cat => {
        const inCat = observed.filter(f => additionCategoryOf(f.num1, f.num2) === cat);
        if (inCat.length) catChips += chip(FLUENCY_CATEGORY_LABELS[cat], fluencyRollupStatus(inCat.map(f => f.status)), titleOf(inCat));
      });
      catBlock = `<div class="fo-row"><div class="fo-row-label">By category</div><div class="fo-chips">${catChips}</div></div>`;
    } else {
      catBlock = `<div class="fo-row"><div class="fo-row-label">By category</div>` +
        `<div class="fo-note">Categories for ${op.key} not defined yet.</div></div>`;
    }

    return `<div class="fo-card">
      <div class="fo-head">
        <h3 class="fo-title">${op.label}</h3>
        <span class="fo-op-status">${dot(opStatus)}` +
        `<span style="color:${fluencyStatusColors[opStatus]};font-weight:700">${STATUS_LABELS[opStatus] || opStatus}</span>` +
        `<span class="fo-pct" style="color:${fluencyStatusColors[opStatus]}">${pct}%</span></span>
      </div>
      <div class="fo-row"><div class="fo-row-label">By range</div><div class="fo-chips">${rangeChips}</div></div>
      ${catBlock}
    </div>`;
  }).join('');
}

function setupFluencyControls(db) {
  const applyButton = document.getElementById('fluency-apply');
  const changeHandler = () => refreshFluencySection(db);

  if (applyButton) applyButton.addEventListener('click', changeHandler);
  
  ['fluency-user', 'fluency-number-range'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', changeHandler);
  });
  
  ['fluency-window-size', 'fluency-min-accuracy', 'fluency-green-ms', 'fluency-red-ms', 'fluency-retention-sessions', 'fluency-permanent-sessions'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('change', changeHandler);
  });
}

function goBackToQuiz() {
  window.location.href = useLocalMathQuizPages() ? 'math_quiz.html' : 'https://www.focusonfoundations.org/math-quiz';
}

function goToAnalysis() {
  window.location.href = useLocalMathQuizPages() ? 'math_analysis.html' : 'https://www.focusonfoundations.org/math-analysis';
}

function setupFileLoading(db) {
  const fileInput = document.getElementById('session-file-input');
  const loadBtn = document.getElementById('load-files-btn');
  const statusDiv = document.getElementById('file-status');
  
  if (!fileInput || !loadBtn || !statusDiv) return;

  loadBtn.addEventListener('click', () => {
    const files = fileInput.files;
    if (files.length === 0) {
      statusDiv.textContent = 'Please select at least one JSON file.';
      statusDiv.style.color = 'red';
      return;
    }
    
    loadSessionFiles(files, db, statusDiv, () => {
      populateUsernameDropdown(db);
      refreshFluencySection(db);
    });
  });
}

function setupSessionManagement(db) {
  const downloadAllBtn = document.getElementById('download-all-sessions-fluency');
  const clearAllBtn = document.getElementById('clear-all-sessions-fluency');
  
  if (downloadAllBtn) downloadAllBtn.addEventListener('click', downloadAllSessionsData);

  if (clearAllBtn) {
  clearAllBtn.addEventListener('click', () => {
    if (confirm("Are you sure? This will erase all session data and refresh the page.")) {
      clearAllSessions();
      location.reload();
    }
  });
}

  updateSessionCount();
}

function downloadFluencyData() {
  const data = {
    version: "2.0",
    lastUpdated: new Date().toISOString(),
    addition: fluencyDatasets.addition?.combined || {},
    subtraction: fluencyDatasets.subtraction?.combined || {},
    multiplication: fluencyDatasets.multiplication?.combined || {}
  };
  
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data, null, 2));
  const a = document.createElement('a');
  a.href = dataStr;
  a.download = `fluency_data_${new Date().toISOString().slice(0,10)}.json`;
  a.click();
}

// Foldable "File management" header (same pattern as the analysis page).
function setupFluencyFileCollapsible() {
  const section = document.getElementById('file-upload-section');
  const toggle = document.getElementById('file-upload-toggle');
  if (!section || !toggle) return;
  const setExpanded = (expanded) => {
    section.classList.toggle('expanded', expanded);
    section.classList.toggle('collapsed', !expanded);
    toggle.setAttribute('aria-expanded', String(expanded));
  };
  toggle.addEventListener('click', () => setExpanded(section.classList.contains('collapsed')));
  toggle.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpanded(section.classList.contains('collapsed')); }
  });
}

// Load a per-person .sqlite into the EXISTING db object (clear + copy, so the
// db reference held by the control handlers stays valid), mirroring the analysis
// page's importSqliteIntoDb.
function loadSqliteBytesIntoFluencyDb(bytes) {
  if (!sqlJs) throw new Error('SQL.js is not ready yet');
  const uploaded = new sqlJs.Database(new Uint8Array(bytes));
  try {
    db.run('DELETE FROM ProblemAttempts');
    db.run('DELETE FROM Sessions');
    db.run('DELETE FROM Users');
    try {
      const u = uploaded.prepare('SELECT name FROM Users');
      while (u.step()) db.run('INSERT OR IGNORE INTO Users (name) VALUES (?)', [u.getAsObject().name]);
      u.free();
    } catch (e) { /* no Users table — fine */ }
    const s = uploaded.prepare('SELECT * FROM Sessions');
    while (s.step()) {
      const r = s.getAsObject();
      if (!r.session_id) continue;
      db.run(`INSERT OR IGNORE INTO Sessions (
          session_id, session_filename, user_name, start_time, end_time, num_problems,
          number_range_start, number_range_end, numbers_include, numbers_exclude,
          num_numbers, operations, total_problems, correct_answers, average_response_time_ms,
          session_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, [
        r.session_id, r.session_filename ?? null, r.user_name ?? null, r.start_time ?? null,
        r.end_time ?? null, r.num_problems ?? null, r.number_range_start ?? null, r.number_range_end ?? null,
        r.numbers_include ?? null, r.numbers_exclude ?? null, r.num_numbers ?? null, r.operations ?? null,
        r.total_problems ?? null, r.correct_answers ?? null, r.average_response_time_ms ?? null,
        r.session_type ?? null
      ]);
    }
    s.free();
    const pa = uploaded.prepare('SELECT * FROM ProblemAttempts ORDER BY ROWID');
    while (pa.step()) {
      const r = pa.getAsObject();
      db.run(`INSERT OR IGNORE INTO ProblemAttempts (
          session_id, problem_id, problem_text, num1, num2, operation,
          correct_answer, user_answer_string, user_answer, is_correct, response_time_ms, flags_json, presented_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, [
        r.session_id, r.problem_id ?? null, r.problem_text ?? null, r.num1 ?? null, r.num2 ?? null,
        r.operation ?? null, r.correct_answer ?? null, r.user_answer_string ?? null, r.user_answer ?? null,
        r.is_correct ?? null, r.response_time_ms ?? null, r.flags_json ?? null, r.presented_at ?? null
      ]);
    }
    pa.free();
  } finally {
    if (typeof uploaded.close === 'function') uploaded.close();
  }
}

// "Choose and load file": load a per-person .sqlite into the tracker and share it
// with the analysis page (same IndexedDB working DB).
function setupFluencyFileManagement() {
  const input = document.getElementById('sqlite-file-input');
  const chooseBtn = document.getElementById('choose-load-file');
  const status = document.getElementById('sqlite-status');
  if (!input || !chooseBtn || !status) return;

  const loadBytes = async (bytes, name) => {
    if (!sqlJs) { status.textContent = 'Still loading the SQLite engine — try again in a moment.'; status.style.color = '#c62828'; return; }
    try {
      const u8 = new Uint8Array(bytes);
      loadSqliteBytesIntoFluencyDb(u8);
      if (typeof saveSharedWorkingDb === 'function') await saveSharedWorkingDb(db.export());
      refreshFluencySection(db);
      let sessions = 0;
      try { const r = db.exec('SELECT count(*) FROM Sessions'); sessions = (r[0] && r[0].values[0][0]) || 0; } catch (e) { /* ignore */ }
      status.textContent = `Loaded ${name || 'file'} (${sessions} session${sessions === 1 ? '' : 's'}). Shared with the analysis page.`;
      status.style.color = '#2e7d32';
    } catch (e) {
      console.error('Load .sqlite failed:', e);
      status.textContent = `Could not load that file: ${e.message}`;
      status.style.color = '#c62828';
    }
  };

  input.addEventListener('change', async () => {
    const file = input.files && input.files[0];
    if (!file) return;
    await loadBytes(await file.arrayBuffer(), file.name);
    input.value = '';   // allow re-choosing the same file
  });
  chooseBtn.addEventListener('click', async () => {
    if (!window.showOpenFilePicker) { input.click(); return; }
    try {
      const [handle] = await window.showOpenFilePicker({
        types: [{ description: 'SQLite database', accept: { 'application/octet-stream': ['.sqlite', '.db', '.sqlite3'] } }]
      });
      const file = await handle.getFile();
      await loadBytes(await file.arrayBuffer(), file.name);
    } catch (e) {
      if (e && e.name === 'AbortError') return;   // user cancelled the picker
      input.click();
    }
  });
}

function setupFluencyPage(db) {
  const goBackBtn = document.getElementById('go-back-to-quiz');
  const goToAnalysisBtn = document.getElementById('go-to-analysis');
  const downloadFluencyBtn = document.getElementById('download-fluency-data');
  
  if (goBackBtn) goBackBtn.addEventListener('click', goBackToQuiz);
  if (goToAnalysisBtn) goToAnalysisBtn.addEventListener('click', goToAnalysis);
  if (downloadFluencyBtn) downloadFluencyBtn.addEventListener('click', downloadFluencyData);

  setupFluencyFileCollapsible();
  setupFluencyFileManagement();
  setupFluencyControls(db);
  setupStatusEditEventDelegation();
  refreshFluencySection(db);
  
  console.log('Fluency page setup complete');
  
  // Setup problem list generator
  setupProblemListGenerator();
}

// Filter problems by number range
function filterProblemsByRange(problems, rangeValue) {
  if (!rangeValue || rangeValue === 'all') {
    return problems;
  }
  
  const [start, end] = rangeValue.split('-').map(Number);
  if (isNaN(start) || isNaN(end)) return problems;
  
  const filtered = {};
  Object.entries(problems).forEach(([key, p]) => {
    if (p.num1 >= start && p.num1 <= end && 
        p.num2 >= start && p.num2 <= end) {
      filtered[key] = p;
    }
  });
  return filtered;
}

// Convert fluency problem to quiz format
function convertFluencyProblemToQuizFormat(fluencyProblem) {
  const { num1, num2, operation } = fluencyProblem;
  
  const baseProblem = `${num1} ${operation} ${num2}`;
  const displayProblem = baseProblem
    .replace(/\*/g, '×')
    .replace(/\//g, '÷');
  const speakableProblem = baseProblem
    .replace(/\*/g, 'times')
    .replace(/\//g, 'divided by');
  
  let correctAnswer;
  switch (operation) {
    case '+': correctAnswer = num1 + num2; break;
    case '-': correctAnswer = num1 - num2; break;
    case '*': correctAnswer = num1 * num2; break;
    case '/': correctAnswer = num2 !== 0 ? num1 / num2 : (num1 === 0 ? NaN : Infinity); break;
    default: correctAnswer = null;
  }
  
  return {
    rawExpression: baseProblem,
    normalizedExpression: baseProblem,
    displayProblem,
    speakableProblem,
    correctAnswer,
    problemId: getCanonicalProblemKey(num1, num2, operation)
  };
}

// Generate problem list from fluency data
function generateProblemListFromFluency(operation, numberRange, totalProblems, percentages) {
  // Get fluency data for the selected operation
  const opData = fluencyDatasets[operation];
  if (!opData || !opData.combined) {
    throw new Error(`No fluency data available for ${operation}`);
  }
  
  // Filter problems by number range
  const filteredProblems = filterProblemsByRange(opData.combined, numberRange);
  
  // Group problems by status
  const problemsByStatus = {
    blue: [],
    green: [],
    yellow: [],
    red: [],
    gray: []
  };
  
  Object.values(filteredProblems).forEach(problem => {
    const status = problem.status;
    if (problemsByStatus[status]) {
      problemsByStatus[status].push(problem);
    }
  });
  
  // Calculate target counts for each status
  const targetCounts = {};
  let remainingProblems = totalProblems;
  
  ['blue', 'green', 'yellow', 'red', 'gray'].forEach(status => {
    const pct = percentages[status] || 0;
    const available = problemsByStatus[status].length;
    
    if (pct > 0 && available > 0) {
      const targetFromPct = Math.round((pct / 100) * totalProblems);
      targetCounts[status] = Math.min(targetFromPct, available, remainingProblems);
      remainingProblems -= targetCounts[status];
    } else {
      targetCounts[status] = 0;
    }
  });
  
  // Handle rounding errors - distribute remaining to largest category with space
  if (remainingProblems > 0) {
    const categoriesWithSpace = ['blue', 'green', 'yellow', 'red', 'gray'].filter(
      status => problemsByStatus[status].length > targetCounts[status]
    );
    if (categoriesWithSpace.length > 0) {
      // Distribute to category with most available
      const largestCategory = categoriesWithSpace.reduce((max, status) => 
        problemsByStatus[status].length > problemsByStatus[max].length ? status : max
      );
      targetCounts[largestCategory] += remainingProblems;
    }
  }
  
  // Sample problems from each category
  const selectedProblems = [];
  
  ['blue', 'green', 'yellow', 'red', 'gray'].forEach(status => {
    const count = targetCounts[status];
    const available = problemsByStatus[status];
    
    if (count > 0 && available.length > 0) {
      // Shuffle and take first N (simple random sampling)
      const shuffled = [...available].sort(() => Math.random() - 0.5);
      const sampled = shuffled.slice(0, count);
      selectedProblems.push(...sampled);
    }
  });
  
  // Shuffle final list to mix categories
  const finalList = selectedProblems.sort(() => Math.random() - 0.5);
  
  // Convert to quiz problem format
  return finalList.map(problem => convertFluencyProblemToQuizFormat(problem));
}

// Setup problem list generator UI and handlers
function setupProblemListGenerator() {
  const generateBtn = document.getElementById('generate-problem-list-btn');
  const modal = document.getElementById('problem-list-generator-modal');
  const cancelBtn = document.getElementById('gen-cancel');
  const downloadBtn = document.getElementById('gen-download');
  const useInQuizBtn = document.getElementById('gen-use-in-quiz');
  
  if (!generateBtn || !modal) return;
  
  // Percentage inputs with validation
  const pctInputs = ['blue', 'green', 'yellow', 'red', 'gray'].map(s => 
    document.getElementById(`gen-pct-${s}`)
  );
  
  // Update percentage total on input
  pctInputs.forEach(input => {
    if (input) {
      input.addEventListener('input', () => {
        const total = pctInputs.reduce((sum, inp) => sum + (parseInt(inp?.value) || 0), 0);
        const totalSpan = document.getElementById('gen-percentage-total');
        if (totalSpan) totalSpan.textContent = total;
        
        // Update preview
        updateGeneratorPreview();
      });
    }
  });
  
  // Update preview when operation or range changes
  const operationSelect = document.getElementById('gen-operation');
  const rangeSelect = document.getElementById('gen-number-range');
  if (operationSelect) operationSelect.addEventListener('change', updateGeneratorPreview);
  if (rangeSelect) rangeSelect.addEventListener('change', updateGeneratorPreview);
  
  // Open modal
  generateBtn.addEventListener('click', () => {
    if (!fluencyDatasets || Object.keys(fluencyDatasets).length === 0) {
      alert('Please load and apply fluency data first.');
      return;
    }
    modal.classList.remove('hidden');
    updateGeneratorPreview();
  });
  
  // Close modal
  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  }
  
  // Download JSON
  if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
      const problemList = generateProblemList();
      if (!problemList || problemList.length === 0) return;
      
      const json = JSON.stringify(problemList, null, 2);
      const blob = new Blob([json], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `problem_list_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      alert(`Downloaded ${problemList.length} problems!`);
    });
  }
  
  // Use in quiz (navigate to quiz page with data)
  if (useInQuizBtn) {
    useInQuizBtn.addEventListener('click', () => {
      const problemList = generateProblemList();
      if (!problemList || problemList.length === 0) return;
      
      // Store in localStorage for quiz to pick up
      localStorage.setItem('generatedProblemList', JSON.stringify(problemList));
      localStorage.setItem('generatedProblemListMetadata', JSON.stringify({
        source: 'fluency-tracker',
        generatedAt: new Date().toISOString(),
        operation: operationSelect?.value || 'addition',
        totalProblems: problemList.length
      }));
      
      // Navigate to quiz page
      const targetUrl = useLocalMathQuizPages() ? 'math_quiz.html' : 'https://www.focusonfoundations.org/math-quiz';
      window.location.href = targetUrl;
    });
  }
  
  function generateProblemList() {
    const operation = operationSelect?.value || 'addition';
    const numberRange = rangeSelect?.value || '0-9';
    const totalProblemsInput = document.getElementById('gen-total-problems');
    const totalProblems = parseInt(totalProblemsInput?.value) || 20;
    
    const percentages = {
      blue: parseInt(document.getElementById('gen-pct-blue')?.value) || 0,
      green: parseInt(document.getElementById('gen-pct-green')?.value) || 0,
      yellow: parseInt(document.getElementById('gen-pct-yellow')?.value) || 0,
      red: parseInt(document.getElementById('gen-pct-red')?.value) || 0,
      gray: parseInt(document.getElementById('gen-pct-gray')?.value) || 0
    };
    
    const totalPct = Object.values(percentages).reduce((a, b) => a + b, 0);
    if (totalPct !== 100) {
      alert(`Percentages must total 100% (currently ${totalPct}%).`);
      return null;
    }
    
    try {
      return generateProblemListFromFluency(operation, numberRange, totalProblems, percentages);
    } catch (error) {
      alert(`Error generating problem list: ${error.message}`);
      return null;
    }
  }
  
  function updateGeneratorPreview() {
    const operation = operationSelect?.value || 'addition';
    const numberRange = rangeSelect?.value || '0-9';
    const opData = fluencyDatasets[operation];
    
    const previewDiv = document.getElementById('gen-preview');
    if (!previewDiv) return;
    
    if (!opData || !opData.combined) {
      previewDiv.innerHTML = '<p>No data available. Please apply fluency settings first.</p>';
      return;
    }
    
    const filtered = filterProblemsByRange(opData.combined, numberRange);
    const byStatus = { blue: 0, green: 0, yellow: 0, red: 0, gray: 0 };
    Object.values(filtered).forEach(p => {
      if (byStatus.hasOwnProperty(p.status)) byStatus[p.status]++;
    });
    
    const total = Object.values(byStatus).reduce((a, b) => a + b, 0);
    
    const preview = `
      <p><strong>Available Problems:</strong></p>
      <ul style="font-size: 12px;">
        <li>Blue: ${byStatus.blue}</li>
        <li>Green: ${byStatus.green}</li>
        <li>Yellow: ${byStatus.yellow}</li>
        <li>Red: ${byStatus.red}</li>
        <li>Gray: ${byStatus.gray}</li>
        <li><strong>Total: ${total}</strong></li>
      </ul>
    `;
    previewDiv.innerHTML = preview;
  }
}

// Status Edit Dialog Functions
function showStatusEditDialog(problem, operation) {
  const currentStatus = problem.status;
  const calculatedStatus = problem.calculatedStatus || problem.status;
  const currentReason = problem.overrideReason || '';
  const settings = getFluencySettings();
  const username = settings.username;
  const isManual = problem.manualOverride || false;
  
  const dialog = document.createElement('div');
  dialog.className = 'status-edit-dialog';
  dialog.innerHTML = `
    <div class="dialog-overlay"></div>
    <div class="dialog-content">
      <h3>Edit Fluency Status</h3>
      <p class="problem-display">${problem.num1} ${problem.operation} ${problem.num2}</p>
      
      ${isManual ? `
        <div class="info-banner manual-override">
          ⭐ This problem has a manual override
        </div>
      ` : ''}
      
      <div class="recommendation-section">
        <label>System Recommendation:</label>
        <div class="status-badge ${calculatedStatus}">
          ${STATUS_LABELS[calculatedStatus] || calculatedStatus}
        </div>
        <div class="recommendation-details">
          <small>
            Accuracy: ${Math.round((problem.accuracy || 0) * 100)}%<br>
            ${problem.medianMs ? `Median Time: ${Math.round(problem.medianMs)} ms` : 'No time data'}
          </small>
        </div>
      </div>
      
      <label>Manual Status:</label>
      <select id="edit-status" class="status-select">
        <option value="blue" ${currentStatus === 'blue' ? 'selected' : ''}>Blue (Permanent)</option>
        <option value="green" ${currentStatus === 'green' ? 'selected' : ''}>Green (Fluent)</option>
        <option value="yellow" ${currentStatus === 'yellow' ? 'selected' : ''}>Yellow (Almost Fluent)</option>
        <option value="red" ${currentStatus === 'red' ? 'selected' : ''}>Red (Needs Practice)</option>
        <option value="gray" ${currentStatus === 'gray' ? 'selected' : ''}>Gray (Incorrect)</option>
        <option value="null">Remove Override (Use Auto)</option>
      </select>
      
      <label>Reason (optional):</label>
      <textarea id="edit-reason" placeholder="e.g., Student knows this but was distracted during session">${escapeHtml(currentReason)}</textarea>
      
      <div class="dialog-actions">
        <button class="btn-cancel" data-action="cancel-edit">Cancel</button>
        <button class="btn-save" data-action="save-edit" data-problem-key="${problem.key}" data-operation="${operation}">Save</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(dialog);
}

function showStatusEditDialogFromList(problemKey, operation) {
  const opData = fluencyDatasets[operation];
  if (!opData || !opData.combined[problemKey]) return;
  const problem = opData.combined[problemKey];
  showStatusEditDialog(problem, operation);
}

function saveStatusEdit(problemKey, operation) {
  const statusSelect = document.getElementById('edit-status');
  const reasonInput = document.getElementById('edit-reason');
  const settings = getFluencySettings();
  const username = settings.username;
  const opData = fluencyDatasets[operation];
  const problem = opData.combined[problemKey];
  
  if (!problem) {
    alert('Problem not found.');
    return;
  }
  
  const newStatus = statusSelect.value === 'null' ? null : statusSelect.value;
  const reason = reasonInput.value.trim();
  const calculatedStatus = problem.calculatedStatus || problem.status;
  
  const overrideUsername = username === 'all' ? 'default' : username;
  if (saveManualOverride(overrideUsername, problemKey, newStatus, reason, calculatedStatus)) {
    closeStatusEditDialog();
    refreshFluencySection(db); // Refresh display
  } else {
    alert('Error saving override. Please try again.');
  }
}

function closeStatusEditDialog() {
  const dialog = document.querySelector('.status-edit-dialog');
  if (dialog) dialog.remove();
}

function clearAllOverrides() {
  const settings = getFluencySettings();
  const username = settings.username;
  const overrideUsername = username === 'all' ? 'default' : username;
  
  if (confirm(`Clear all manual overrides for ${username === 'all' ? 'all users' : username}? This cannot be undone.`)) {
    if (clearManualOverrides(overrideUsername)) {
  refreshFluencySection(db);
      alert('All overrides cleared.');
    } else {
      alert('Error clearing overrides.');
    }
  }
}

// Event delegation for status edit dialogs and problem list clicks
function setupStatusEditEventDelegation() {
  // Handle clicks on problem items in the problem list
  document.addEventListener('click', (e) => {
    const problemItem = e.target.closest('.problem-item-clickable');
    if (problemItem) {
      const problemKey = problemItem.dataset.key;
      const operation = problemItem.dataset.operation;
      if (problemKey && operation) {
        showStatusEditDialogFromList(problemKey, operation);
      }
    }
    
    // Handle dialog button clicks
    if (e.target.matches('[data-action="cancel-edit"]')) {
      closeStatusEditDialog();
    } else if (e.target.matches('[data-action="save-edit"]')) {
      const problemKey = e.target.dataset.problemKey;
      const operation = e.target.dataset.operation;
      if (problemKey && operation) {
        saveStatusEdit(problemKey, operation);
      }
    }
  });
  
  // Handle clear overrides button
  const clearOverridesBtn = document.getElementById('clear-overrides');
  if (clearOverridesBtn) {
    clearOverridesBtn.addEventListener('click', clearAllOverrides);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM fully loaded');
});
