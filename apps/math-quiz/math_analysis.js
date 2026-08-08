// 🚀 WEBFLOW MISSION: BEAM THIS ENTIRE FILE TO SETTINGS CUSTOM CODE BODY 🚀

// START OF FILE math_analysis.js
// sql-wasm.js and sql-wasm.wasm (from sql.js)

var fileInfo = `${window.location.pathname.split('/').pop()} 10-13 1059 plotHeatmap changes on 902 for mobile`;
// Log when the script is loaded
console.log('Math Analysis JavaScript file loaded. ', fileInfo);

// Shared utility functions are now in math_utils.js

let db;
// The sql.js module, stashed at init so we can open uploaded .sqlite files later.
let SQLModule = null;

// Single-digit addition categories (mirrors engine/addition_segmentation.mjs +
// single_digit_addition_categorization.md). Hardest 6 is split out of Tough 21
// here so it can be isolated; 'other' = non-addition problems.
const SEQ_CATEGORY_RANK = {
  'add-zero': 0, 'add-one': 1, 'add-two': 2, 'doubles': 3,
  'tough-21': 4, 'hardest-six': 5, 'other': 6
};
// Stepper state: the ordered+filtered population and the visible [start,end) window.
const seqState = { population: [], fluencyPopulation: [], window: { start: 0, end: 0 }, sig: null };
// Structural query cache: category/ordering toggles refilter this without re-querying SQLite.
const seqSourceData = { filteredProblems: null, fluencyFilteredProblems: null, structural: null };
// The heatmap cell the user clicked into (focus the list on one problem). null = no focus.
let focusedCell = null;

// Top controls whose selections are remembered across reloads (localStorage).
const PERSISTED_CONTROL_IDS = [
  'username-selection', 'session-selection', 'n-sessions', 'operation-filter',
  'number-range', 'min-response-time-threshold', 'max-response-time-threshold',
  'duplicate-aggregation', 'color-scale-selector', 'seq-ordering', 'metric-mode',
  'fluency-threshold', 'fluency-window', 'fluency-min-accuracy', 'fluency-red-threshold'
];
// Subset reset by "Reset all to default" (NOT session/operation/flag/user).
const CONTROL_DEFAULTS = {
  'number-range': '0-9', 'min-response-time-threshold': '2000',
  'max-response-time-threshold': '10000', 'duplicate-aggregation': 'average',
  'color-scale-selector': 'classic', 'metric-mode': 'response-time',
  'fluency-threshold': '2000', 'fluency-window': '5', 'fluency-min-accuracy': '80',
  'fluency-red-threshold': '4000'
};
const CONTROLS_STORAGE_KEY = 'math_analysis_controls';

const FLAG_REASON_LABELS = {
  'skip-noreason': 'Skip - no reason',
  lightbulb: '💡 Show ten-frames',
  distracted: 'Distracted',
  interrupted: 'Interrupted',
  error: 'Input Error',
  stall: 'Stall',
  dontknow: "I Don't Know",
  other: 'Other'
};
const FLAG_FILTER_STORAGE_KEY = 'math_analysis_flag_filter';
const SORT_PREFERENCE_KEY = 'math_analysis_sort_preference';
let currentSortMode = 'order';

// Badge positioning constants for heatmap annotations
const BADGE_XSHIFT_DESKTOP = -20;
const BADGE_XSHIFT_MOBILE = -14;
const BADGE_YSHIFT_DESKTOP = 20;
const BADGE_YSHIFT_MOBILE = 14;

// Test SQL.js initialization and functionality
console.log("Initializing SQL.js...");
const sqlJsUrl = 'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.6.2/sql-wasm.js';
console.log(`Loading SQL.js from: ${sqlJsUrl}`);

// Load SQL.js dynamically
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

// Function to load Plotly
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

// The rest of your existing code goes here, wrapped in a function
function initializeDatabase() {
  // Load the SQLite database
  if (typeof db === 'undefined') {
    initSqlJs({ locateFile: file => 'https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.6.2/' + file }).then(async SQL => {
      SQLModule = SQL;            // keep a handle for opening uploaded .sqlite files
      // Restore a previously loaded SQLite working DB (retained across reloads).
      const persisted = await loadWorkingDb();
      db = persisted ? new SQL.Database(persisted) : new SQL.Database();
      sqliteLoaded = !!persisted;
      createTables(db);                 // idempotent
      // SQLite-only: data comes from a loaded per-person .sqlite (legacy JSON import retired).
      console.log('Database created');
      
      // Add this: Log the number of rows in the ProblemAttempts table
      const stmt = db.prepare("SELECT COUNT(*) AS count FROM ProblemAttempts");
      let attemptCount = 0;
      if (stmt.step()) {
        attemptCount = stmt.getAsObject().count;
      }
      console.log('Number of rows in ProblemAttempts:', attemptCount);
      stmt.free();

      // Wait for DOM to be fully loaded before populating controls
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
          populateControls(db);
          loadLatestForUrlParams();   // ?folder=&user= -> auto-load that person's latest file
        });
      } else {
        populateControls(db);
        loadLatestForUrlParams();
      }
    }).catch(error => {
      console.error('Error initializing SQL.js:', error.message);
      alert('Failed to initialize SQL.js. Please check the console for more information.');
    });
  } else {
    console.log('Database already initialized');
  }
}

// createTables, importJsonDataToDb, and importSessionData are now in math_utils.js

// Add this function to handle navigation back to the quiz
function goBackToQuiz() {
  let targetUrl;
  
  if (useLocalMathQuizPages()) {
      targetUrl = 'math_quiz.html';
  } else {
      // Hosted on focusonfoundations.org
      targetUrl = 'https://www.focusonfoundations.org/math-quiz';
  }
  
  window.location.href = targetUrl;
}

function setupFlagFiltering(db) {
  const flagFilter = document.getElementById('flag-filter');
  if (!flagFilter) {
    return;
  }

  const storedValue = localStorage.getItem(FLAG_FILTER_STORAGE_KEY);
  if (storedValue && Array.from(flagFilter.options).some(option => option.value === storedValue)) {
    flagFilter.value = storedValue;
  } else {
    // Default to 'exclude-flagged' if no stored preference
    flagFilter.value = 'exclude-flagged';
  }

  const applyState = () => {
    flagFilter.classList.toggle('is-active', flagFilter.value !== 'all');
    localStorage.setItem(FLAG_FILTER_STORAGE_KEY, flagFilter.value);
  };

  flagFilter.addEventListener('change', () => {
    applyState();
    generateHeatmap(db);
  });

  applyState();
}

function parseFlags(flagsSource) {
  if (!flagsSource) {
    return [];
  }
  if (Array.isArray(flagsSource)) {
    return flagsSource.filter(flag => flag && typeof flag === 'object');
  }
  try {
    const parsed = JSON.parse(flagsSource);
    return Array.isArray(parsed) ? parsed.filter(flag => flag && typeof flag === 'object') : [];
  } catch (error) {
    console.warn('Unable to parse flags payload:', error);
    return [];
  }
}

function setupCollapsibleSection(sectionId, toggleId) {
  const section = document.getElementById(sectionId);
  const toggle = document.getElementById(toggleId);
  if (!section || !toggle) return;
  function setExpanded(expanded) {
    section.classList.toggle('expanded', expanded);
    section.classList.toggle('collapsed', !expanded);
    toggle.setAttribute('aria-expanded', String(expanded));
    setTimeout(() => { if (typeof relayoutHeatmapSize === 'function') relayoutHeatmapSize(); }, 320);
  }
  toggle.addEventListener('click', () => setExpanded(section.classList.contains('collapsed')));
  toggle.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setExpanded(section.classList.contains('collapsed'));
    }
  });
}
function setupSessionDataCollapsible() {
  setupCollapsibleSection('file-upload-section', 'file-upload-toggle');
  setupCollapsibleSection('session-selection-section', 'session-selection-toggle');
}
function setupProblemListToggle() {
  const toggleBtn = document.getElementById('toggle-problem-list');
  const listWrapper = document.querySelector('.problem-list-wrapper');
  
  if (toggleBtn && listWrapper) {
    // Helper function to resize the heatmap
    function resizeHeatmap() {
      const heatmapElement = document.getElementById('heatmap');
      if (heatmapElement && typeof Plotly !== 'undefined') {
        relayoutHeatmapSize();
      }
    }

    toggleBtn.addEventListener('click', function() {
      const isExpanded = this.getAttribute('aria-expanded') === 'true';
      this.setAttribute('aria-expanded', !isExpanded);
      listWrapper.classList.toggle('collapsed');
      // List DOM is skipped while collapsed; materialize it when opening.
      if (!isExpanded && window.currentFilteredProblems) {
        renderProblemList(window.currentFilteredProblems);
      }

      // Use both transitionend event AND a timeout fallback
      let resized = false;
      
      // Listen for transition end
      const onTransitionEnd = (e) => {
        if (e.propertyName === 'width' && !resized) {
          resized = true;
          resizeHeatmap();
          listWrapper.removeEventListener('transitionend', onTransitionEnd);
        }
      };
      listWrapper.addEventListener('transitionend', onTransitionEnd);
      
      // Fallback timeout in case transitionend doesn't fire
      setTimeout(() => {
        if (!resized) {
          resized = true;
          resizeHeatmap();
          listWrapper.removeEventListener('transitionend', onTransitionEnd);
        }
      }, 400);
    });
  }
  
  // Setup sort controls
  setupSortControls();
}

function setupSortControls() {
  const sortBtns = document.querySelectorAll('.sort-btn');
  
  // Restore saved sort preference
  const savedSort = localStorage.getItem(SORT_PREFERENCE_KEY);
  if (savedSort) {
    currentSortMode = savedSort;
    sortBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.sort === currentSortMode);
    });
  }
  
  sortBtns.forEach(btn => {
    btn.addEventListener('click', function() {
      currentSortMode = this.dataset.sort;
      localStorage.setItem(SORT_PREFERENCE_KEY, currentSortMode);
      
      // Update active state
      sortBtns.forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      
      // Re-render list with new sort
      renderProblemList(window.currentFilteredProblems);
    });
  });
}

function sortProblems(problems, sortMode) {
  if (!problems || problems.length === 0) return problems;
  
  const sorted = [...problems];
  
  switch (sortMode) {
    case 'time-desc':
      sorted.sort((a, b) => (b.response_time_ms || 0) - (a.response_time_ms || 0));
      break;
    case 'time-asc':
      sorted.sort((a, b) => (a.response_time_ms || 0) - (b.response_time_ms || 0));
      break;
    case 'correct':
      sorted.sort((a, b) => (b.is_correct ? 1 : 0) - (a.is_correct ? 1 : 0));
      break;
    case 'incorrect':
      sorted.sort((a, b) => (a.is_correct ? 1 : 0) - (b.is_correct ? 1 : 0));
      break;
    case 'flagged':
      sorted.sort((a, b) => {
        const aHasFlag = a.flags && a.flags.length > 0 ? 1 : 0;
        const bHasFlag = b.flags && b.flags.length > 0 ? 1 : 0;
        return bHasFlag - aHasFlag;
      });
      break;
    case 'order':
    default:
      // Keep original order (chronological)
      break;
  }
  
  return sorted;
}

function filterProblemsByFlags(problems) {
  const flagFilter = document.getElementById('flag-filter');
  if (!flagFilter) {
    return problems;
  }

  const filterValue = flagFilter.value;
  switch (filterValue) {
    case 'unflagged':
    case 'exclude-flagged':
      return problems.filter(problem => !problem.flags || problem.flags.length === 0);
    case 'flagged-distracted':
      return problems.filter(problem => problem.flags && problem.flags.some(flag => flag.reason === 'distracted'));
    case 'flagged-interrupted':
      return problems.filter(problem => problem.flags && problem.flags.some(flag => flag.reason === 'interrupted'));
    case 'flagged-error':
      return problems.filter(problem => problem.flags && problem.flags.some(flag => flag.reason === 'error'));
    case 'flagged-stall':
      return problems.filter(problem => problem.flags && problem.flags.some(flag => flag.reason === 'stall'));
    case 'flagged-dontknow':
      return problems.filter(problem => problem.flags && problem.flags.some(flag => flag.reason === 'dontknow'));
    case 'flagged-other':
      return problems.filter(problem => problem.flags && problem.flags.some(flag => flag.reason === 'other'));
    case 'all':
    default:
      return problems;
  }
}

function updateFilteredCount(filterValue) {
  const countElement = document.getElementById('filtered-count');
  if (!countElement) {
    return;
  }

  const totalProblems = window.lastTotalProblems || 0;
  const filteredProblems = window.lastFilteredProblems || 0;

  let message = '';
  switch (filterValue) {
    case 'exclude-flagged':
      message = `Excluding flagged ${totalProblems - filteredProblems}/${totalProblems}`;
      break;
    case 'unflagged':
      message = `Showing unflagged ${filteredProblems}/${totalProblems}`;
      break;
    case 'flagged-distracted':
    case 'flagged-interrupted':
    case 'flagged-error':
    case 'flagged-stall':
    case 'flagged-dontknow':
    case 'flagged-other': {
      const reasonKey = filterValue.replace('flagged-', '');
      const label = FLAG_REASON_LABELS[reasonKey] || reasonKey;
      message = `Showing ${label.toLowerCase()} ${filteredProblems}/${totalProblems}`;
      break;
    }
    default:
      message = '';
  }

  if (filterValue !== 'all' && totalProblems === 0) {
    message = 'No data loaded';
  }

  if (message && totalProblems > 0) {
    countElement.textContent = message;
    countElement.style.display = 'inline';
  } else if (filterValue !== 'all' && totalProblems > 0 && filteredProblems === 0) {
    countElement.textContent = 'No attempts match the current filter';
    countElement.style.display = 'inline';
  } else {
    countElement.textContent = '';
    countElement.style.display = 'none';
  }
}

// The wall-clock label for one attempt row. Prefer the per-attempt `presented_at` (the
// time the problem was SHOWN, down to the second) so repeats of the same fact show their
// own times; fall back to the coarser session start only when presented_at is missing.
function formatAttemptTimestamp(problem) {
  const fmt = (d) => `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
  const presented = problem.presented_at ? new Date(problem.presented_at) : null;
  if (presented && !isNaN(presented)) return fmt(presented);
  const sDate = parseSessionTimestamp(problem.start_time);
  return sDate ? fmt(sDate) : (problem.presented_at || problem.start_time || '');
}

function isProblemListExpanded() {
  const toggle = document.getElementById('toggle-problem-list');
  if (toggle) return toggle.getAttribute('aria-expanded') === 'true';
  const wrapper = document.querySelector('.problem-list-wrapper');
  return !!(wrapper && !wrapper.classList.contains('collapsed'));
}
function renderProblemList(problems) {
  const listContainer = document.getElementById('problem-list-items');
  if (!listContainer) return;

  if (!problems || problems.length === 0) {
    listContainer.innerHTML = '<div class="problem-list-empty">No problems to display</div>';
    return;
  }
  
  // Apply sorting
  const sortedProblems = sortProblems(problems, currentSortMode);
  
  // Calculate max response time for bar scaling
  const maxResponseTime = Math.max(...sortedProblems.map(p => p.response_time_ms || 0));
  // O(1) lookup — indexOf inside the map was O(n²) over the full attempt list.
  const indexByProblem = new Map(problems.map((p, i) => [p, i]));

  listContainer.innerHTML = sortedProblems.map((problem, index) => {
    // Index into the unsorted master array — saveProblemFlags reads from
    // window.currentFilteredProblems, so the sorted position must not be used
    const originalIndex = indexByProblem.has(problem) ? indexByProblem.get(problem) : index;
    const isCorrect = problem.is_correct;
    const statusClass = isCorrect ? 'status-correct' : 'status-incorrect';
    const statusText = isCorrect ? '✓ Correct' : '✗ Incorrect';
    
    const flagInfo = problem.flags && problem.flags.length > 0
      ? problem.flags.map(flag => {
          const comment = flag.notes ? ` <span class="flag-comment">"${escapeHtml(flag.notes)}"</span>` : '';
          return `<span class="flag-indicator-list">⚠️</span>${escapeHtml(flag.label)}${comment}`;
        }).join('')
      : '';
    
    // Response time with bar visualization
    const responseTime = problem.response_time_ms || 0;
    const responseTimeFormatted = responseTime ? `${(responseTime / 1000).toFixed(2)}s` : 'N/A';
    const barWidth = maxResponseTime > 0 ? (responseTime / maxResponseTime) * 100 : 0;
    
    // Color code based on response time (assuming 3s is fast, 6s is medium, 9s+ is slow)
    let barClass = 'fast';
    if (responseTime > 6000) barClass = 'slow';
    else if (responseTime > 3000) barClass = 'medium';
    
    const timeDisplay = responseTime 
      ? `<div class="time-display">
           <span class="time-value">${responseTimeFormatted}</span>
           <div class="time-bar-container">
             <div class="time-bar ${barClass}" style="width: ${barWidth}%"></div>
           </div>
         </div>`
      : 'N/A';
    
    const timestamp = problem.timestamp 
      ? new Date(problem.timestamp).toLocaleTimeString()
      : '';
    
    // Check if this is an "I don't know" submission
    const hasDontKnowFlag = problem.flags && problem.flags.some(flag => flag.reason === 'dontknow');
    const displayAnswer = hasDontKnowFlag ? "I Don't Know" : escapeHtml(problem.user_answer_string || 'N/A');
    
    // Build flag editing UI (collapsible)
    const problemFlags = problem.flags || [];
    const flagReasons = ['skip-noreason', 'distracted', 'interrupted', 'error', 'stall', 'dontknow', 'other'];
    const currentFlags = problemFlags.map(f => f.reason);
    const currentNotes = problemFlags.length > 0 ? (problemFlags[0].notes || '') : '';
    
    const flagEditUI = `
      <button class="flag-edit-toggle" onclick="toggleFlagEdit(this)">Edit Flags ▼</button>
      <div class="flag-edit-section" data-problem-id="${problem.problem_id || index}">
        <div class="flag-checkboxes">
          ${flagReasons.map(reason => `
            <label class="flag-checkbox-label">
              <input type="checkbox" value="${reason}" ${currentFlags.includes(reason) ? 'checked' : ''}>
              ${FLAG_REASON_LABELS[reason]}
            </label>
          `).join('')}
        </div>
        <input type="text" class="flag-comment-input" placeholder="Comment (optional)" value="${escapeHtml(currentNotes)}">
        <button class="flag-save-btn" onclick="saveProblemFlags(this, ${originalIndex})">Save Flags</button>
      </div>
    `;
    
    // When the attempt was presented — the per-problem wall-clock time (down to the second),
    // not the session start (so repeated facts each show their own time).
    const sessionLabel = formatAttemptTimestamp(problem);
    const isFocused = focusedCell && cellMatchesProblem(problem, focusedCell);

    return `
      <div class="problem-item${isFocused ? ' focused' : ''}" data-problem-index="${originalIndex}">
        <div class="problem-header">
          <span class="problem-text">${formatProblemTextForDisplay(problem.problem_text)}</span>
          <span class="problem-status ${statusClass}">${statusText}</span>
        </div>
        ${sessionLabel ? `<div class="problem-session">📅 ${escapeHtml(sessionLabel)}</div>` : ''}
        <div class="problem-details">
          Answer: ${displayAnswer} | Correct: ${problem.correct_answer} | Time: ${timeDisplay}
        </div>
        ${flagInfo ? `<div class="problem-flag-info">Flag: ${flagInfo}</div>` : ''}
        ${flagEditUI}
        <div class="problem-meta">
          ${problem.username ? `Student: ${escapeHtml(problem.username)}` : ''}
          ${timestamp ? ` | ${timestamp}` : ''}
        </div>
      </div>
    `;
  }).join('');
}

function toggleFlagEdit(button) {
  const problemItem = button.closest('.problem-item');
  const editSection = problemItem.querySelector('.flag-edit-section');
  
  if (editSection) {
    const isExpanded = editSection.classList.contains('expanded');
    editSection.classList.toggle('expanded');
    button.textContent = isExpanded ? 'Edit Flags ▼' : 'Edit Flags ▲';
  }
}

function saveProblemFlags(button, problemIndex) {
  const problemItem = button.closest('.problem-item');
  const checkboxes = problemItem.querySelectorAll('.flag-checkboxes input[type="checkbox"]:checked');
  const commentInput = problemItem.querySelector('.flag-comment-input');
  const comment = commentInput ? commentInput.value.trim() : '';
  
  // Get checked flag reasons
  const selectedFlags = Array.from(checkboxes).map(cb => cb.value);
  
  // Update the problem in currentFilteredProblems
  if (window.currentFilteredProblems && window.currentFilteredProblems[problemIndex]) {
    const problem = window.currentFilteredProblems[problemIndex];
    
    // Rebuild flags array
    problem.flags = selectedFlags.map(reason => ({
      reason: reason,
      label: FLAG_REASON_LABELS[reason] || reason,
      timestamp: new Date().toISOString(),
      notes: comment
    }));
    
    // Update database
    if (db && problem.session_id && problem.problem_id) {
      const flagsJson = problem.flags.length > 0 ? JSON.stringify(problem.flags) : null;
      db.run(`
        UPDATE ProblemAttempts
        SET flags_json = ?
        WHERE session_id = ? AND problem_id = ?
      `, [flagsJson, problem.session_id, problem.problem_id]);
      persistWorkingDb();   // retain flag edits across reloads (IndexedDB working DB)
      autoSaveToFile();     // and write them back to the loaded file (if a handle is held)
    }
    
    // Visual feedback
    button.textContent = 'Saved!';
    button.classList.add('saved');
    setTimeout(() => {
      button.textContent = 'Save Flags';
      button.classList.remove('saved');
    }, 2000);
    
    // Re-render to show updated flags in the display section
    renderProblemList(window.currentFilteredProblems);
  }
}

// Make functions globally available
window.toggleFlagEdit = toggleFlagEdit;
window.saveProblemFlags = saveProblemFlags;
window.__analysisDb = () => db;   // exposed for e2e assertions on the working DB

function populateControls(db) {
  console.log('Populating controls');

  // Add event listener for the "Go Back to Quiz" button
  const goBackButton = document.getElementById('go-back-to-quiz');
  if (goBackButton) {
    goBackButton.addEventListener('click', goBackToQuiz);
  } else {
    console.error('Could not find go-back-to-quiz button');
  }

  // Populate username dropdown
  populateUsernameDropdown(db);

  const sessionSelection = document.getElementById('session-selection');
  const nSessionsLabel = document.getElementById('n-sessions-label');

  if (!sessionSelection || !nSessionsLabel) {
    console.error('Could not find session-selection or n-sessions-label elements');
    return;
  }

  // Mode select (All / Last / Last N) presets the checkbox list; checks drive the query.
  sessionSelection.addEventListener('change', () => {
    updateNSessionsVisibility();
    syncSessionChecklistToMode();
    generateHeatmap(db);
  });

  // Add event listener for username selection
  const usernameSelection = document.getElementById('username-selection');
  if (!usernameSelection) {
    console.error('Could not find username-selection element');
    return;
  }
  usernameSelection.addEventListener('change', () => {
    populateSessionChecklist(db);
    generateHeatmap(db);
  });

  // Update min threshold value display and generate heatmap
  const minResponseTimeThreshold = document.getElementById('min-response-time-threshold');
  const minThresholdValue = document.getElementById('min-threshold-value');
  
  if (!minResponseTimeThreshold || !minThresholdValue) {
    console.error('Could not find min-response-time-threshold or min-threshold-value elements');
    return;
  }

  // Set initial min threshold value display
  minThresholdValue.textContent = minResponseTimeThreshold.value;
  
  minResponseTimeThreshold.addEventListener('input', () => {
    minThresholdValue.textContent = minResponseTimeThreshold.value;
    generateHeatmap(db);
  });

  // Update max threshold value display and generate heatmap
  const maxResponseTimeThreshold = document.getElementById('max-response-time-threshold');
  const maxThresholdValue = document.getElementById('max-threshold-value');
  
  if (!maxResponseTimeThreshold || !maxThresholdValue) {
    console.error('Could not find max-response-time-threshold or max-threshold-value elements');
    return;
  }

  // Set initial max threshold value display
  maxThresholdValue.textContent = maxResponseTimeThreshold.value;
  
  maxResponseTimeThreshold.addEventListener('input', () => {
    maxThresholdValue.textContent = maxResponseTimeThreshold.value;
    generateHeatmap(db);
  });

  // Add event listeners to other controls
  const nSessions = document.getElementById('n-sessions');
  const operationFilter = document.getElementById('operation-filter');
  const numberRange = document.getElementById('number-range');
  
  if (!nSessions || !operationFilter || !numberRange) {
    console.error('Could not find one or more control elements');
    return;
  }

  nSessions.addEventListener('change', () => {
    if (sessionSelection.value === 'lastN') syncSessionChecklistToMode();
    generateHeatmap(db);
  });
  operationFilter.addEventListener('change', () => generateHeatmap(db));
  numberRange.addEventListener('change', () => generateHeatmap(db));
  
  // Add event listener for duplicate aggregation dropdown
  const duplicateAggregation = document.getElementById('duplicate-aggregation');
  if (duplicateAggregation) {
    duplicateAggregation.addEventListener('change', () => generateHeatmap(db));
  }
  
  // Add event listener for color scale selector
  const colorScaleSelector = document.getElementById('color-scale-selector');
  if (colorScaleSelector) {
    colorScaleSelector.addEventListener('change', () => generateHeatmap(db));
  }

  // Fluency view: cell-metric toggle (response time <-> fluency rating) and the
  // fluency overlay (color the cell borders by fluency rating while the fill
  // still shows response time, so you can see both at once).
  const metricMode = document.getElementById('metric-mode');
  if (metricMode) metricMode.addEventListener('change', () => generateHeatmap(db));
  const fluencyOverlay = document.getElementById('fluency-overlay');
  if (fluencyOverlay) {
    fluencyOverlay.addEventListener('change', () => { saveControls(); generateHeatmap(db); });
  }
  setupFluencyRubricControls(db);

  console.log('Controls populated successfully');
  
  // Add this line at the end of the function:
  setupSqliteLoading(db);
  const revertBtn = document.getElementById('revert-changes');
  if (revertBtn) revertBtn.addEventListener('click', revertChanges);
  setupSequenceControls(db);
  setupFlagFiltering(db);
  setupProblemListToggle();
  setupSessionDataCollapsible();
  if (!window._analysisHeatmapResizeBound) {
    window._analysisHeatmapResizeBound = true;
    window.addEventListener('resize', () => {
      if (typeof relayoutHeatmapSize === 'function') relayoutHeatmapSize();
    });
  }

  // If a SQLite working DB was restored, lock the user + reflect its sessions.
  applyUserLock();
  populateSessionChecklist(db, { skipSync: true });

  // Setup navigation to fluency tracker
  const goToFluencyBtn = document.getElementById('go-to-fluency');
  if (goToFluencyBtn) {
    goToFluencyBtn.addEventListener('click', () => {
      const targetUrl = useLocalMathQuizPages() ? 'math_fluency.html' : 'https://www.focusonfoundations.org/math-fluency';
      window.location.href = targetUrl;
    });
  }

  // Persist top-control selections (incl. color scale) across reloads, and wire reset.
  PERSISTED_CONTROL_IDS.forEach((id) => {
    const el = document.getElementById(id);
    if (el) { el.addEventListener('change', saveControls); el.addEventListener('input', saveControls); }
  });
  document.querySelectorAll('#seq-category-checkboxes input[type="checkbox"][data-cat]')
    .forEach((cb) => cb.addEventListener('change', saveControls));
  const resetBtn = document.getElementById('reset-controls');
  if (resetBtn) resetBtn.addEventListener('click', () => resetControlsToDefault(db));

  // Restore previously-chosen selections (after checklist + lock are in place).
  const restored = restoreControls();
  syncThresholdLabels();
  updateNSessionsVisibility();
  applyRestoredSessionChecks(restored);
  updateSessionSelectedCount();

  // Generate heatmap on page load
  generateHeatmap(db);
}

function populateUsernameDropdown(db) {
  const usernameSelection = document.getElementById('username-selection');
  if (!usernameSelection) {
    console.error('Could not find username-selection element');
    return;
  }

  const query = "SELECT DISTINCT user_name FROM Sessions ORDER BY user_name";
  try {
    const stmt = db.prepare(query);
    while (stmt.step()) {
      const row = stmt.getAsObject();
      const option = document.createElement('option');
      option.value = row.user_name;
      option.textContent = row.user_name;
      usernameSelection.appendChild(option);
    }
    stmt.free();
  } catch (error) {
    console.error('Error populating username dropdown:', error);
  }
}

function updateNSessionsVisibility() {
  const sessionSelection = document.getElementById('session-selection');
  const nSessionsLabel = document.getElementById('n-sessions-label');
  if (!sessionSelection || !nSessionsLabel) return;
  nSessionsLabel.style.display = sessionSelection.value === 'lastN' ? 'inline-block' : 'none';
}

function listSessionsNewestFirst(db, username) {
  let query = 'SELECT session_id, session_filename, start_time FROM Sessions';
  const params = [];
  if (username && username !== 'all') {
    query += ' WHERE user_name = ?';
    params.push(username);
  }
  const rows = [];
  try {
    const stmt = db.prepare(query);
    if (params.length > 0) stmt.bind(params);
    while (stmt.step()) rows.push(stmt.getAsObject());
    stmt.free();
  } catch (error) {
    console.error('Error listing sessions:', error);
    return [];
  }
  rows.sort((a, b) => {
    const kb = sessionRecencyKey(b.session_filename, b.start_time);
    const ka = sessionRecencyKey(a.session_filename, a.start_time);
    return kb < ka ? -1 : kb > ka ? 1 : String(b.session_id).localeCompare(String(a.session_id));
  });
  return rows;
}

function getCheckedSessionIds() {
  const ids = [];
  document.querySelectorAll('#session-checklist input[type="checkbox"]').forEach((cb) => {
    if (cb.checked && cb.value) ids.push(cb.value);
  });
  return ids;
}

function updateSessionSelectedCount() {
  const el = document.getElementById('session-selected-count');
  if (!el) return;
  const boxes = document.querySelectorAll('#session-checklist input[type="checkbox"]');
  const checked = getCheckedSessionIds().length;
  if (!boxes.length) {
    el.textContent = '';
    return;
  }
  el.textContent = `(${checked} of ${boxes.length})`;
}

function syncSessionChecklistToMode() {
  const modeEl = document.getElementById('session-selection');
  const nEl = document.getElementById('n-sessions');
  if (!modeEl) return;
  const mode = modeEl.value;
  const nRaw = nEl ? parseInt(nEl.value, 10) : 1;
  const n = Number.isFinite(nRaw) && nRaw > 0 ? Math.floor(nRaw) : 1;
  const boxes = document.querySelectorAll('#session-checklist input[type="checkbox"]');
  boxes.forEach((cb, i) => {
    if (mode === 'all') cb.checked = true;
    else if (mode === 'last') cb.checked = i === 0;
    else if (mode === 'lastN') cb.checked = i < n;
    else cb.checked = false;
  });
  updateSessionSelectedCount();
}

function applyCheckedSessionIds(selectedIds) {
  const wanted = new Set(selectedIds || []);
  document.querySelectorAll('#session-checklist input[type="checkbox"]').forEach((cb) => {
    cb.checked = wanted.has(cb.value);
  });
  updateSessionSelectedCount();
}

function applyRestoredSessionChecks(restored) {
  if (restored && Array.isArray(restored.__selectedSessionIds) && restored.__selectedSessionIds.length) {
    const available = new Set(
      [...document.querySelectorAll('#session-checklist input[type="checkbox"]')].map((cb) => cb.value)
    );
    const keep = restored.__selectedSessionIds.filter((id) => available.has(id));
    if (keep.length) {
      applyCheckedSessionIds(keep);
      return;
    }
  }
  syncSessionChecklistToMode();
}

function populateSessionChecklist(db, options = {}) {
  const list = document.getElementById('session-checklist');
  const usernameSelection = document.getElementById('username-selection');
  if (!list || !usernameSelection) {
    console.error('Could not find session-checklist or username-selection element');
    return;
  }
  const selectedUsername = usernameSelection.value;
  const sessions = listSessionsNewestFirst(db, selectedUsername);
  list.innerHTML = '';
  if (!sessions.length) {
    list.innerHTML = '<div class="session-checklist-empty">No sessions loaded.</div>';
    updateSessionSelectedCount();
    return;
  }
  sessions.forEach((row) => {
    const label = document.createElement('label');
    label.className = 'session-checklist-item';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = row.session_id;
    cb.dataset.filename = row.session_filename || '';
    const text = document.createElement('span');
    text.className = 'session-label';
    text.textContent = row.session_filename || row.session_id;
    label.appendChild(cb);
    label.appendChild(text);
    list.appendChild(label);
    cb.addEventListener('change', () => {
      updateSessionSelectedCount();
      saveControls();
      generateHeatmap(db);
    });
  });
  if (!options.skipSync) syncSessionChecklistToMode();
  else updateSessionSelectedCount();
}

function clearSeqSourceData() {
  seqSourceData.filteredProblems = null;
  seqSourceData.fluencyFilteredProblems = null;
  seqSourceData.structural = null;
}
// Category / ordering changes: refilter the cached structural result and redraw.
// Does NOT re-query SQLite or recompute the app-wide fluency % readout.
function refreshSequenceView() {
  if (!seqSourceData.filteredProblems || !seqSourceData.structural) return;
  buildSequencePopulation(
    seqSourceData.filteredProblems,
    seqSourceData.structural,
    seqSourceData.fluencyFilteredProblems
  );
  renderVisible();
}
function generateHeatmap(db) {
  // Retrieve the "structural" selections that define the population of attempts.
  const username = document.getElementById('username-selection').value;
  const sessionMode = document.getElementById('session-selection').value;
  const nSessions = parseInt(document.getElementById('n-sessions').value);
  const selectedSessionIds = getCheckedSessionIds();
  const operationFilter = document.getElementById('operation-filter').value;

  // Always refresh the app-wide fluency readout (full history, not the view filters).
  updateCurrentFluencyPercentage(db, username);

  // Heatmap uses the checkbox selection (mode / Last N only presets those checks).
  const problemsData = queryDatabase(db, username, selectedSessionIds, nSessions, operationFilter);
  const flagFilter = document.getElementById('flag-filter');
  const filterValue = flagFilter ? flagFilter.value : 'all';

  window.lastTotalProblems = problemsData.length;

  if (problemsData.length === 0) {
    clearSeqSourceData();
    updateFilteredCount(filterValue);
    resetSequenceUI('No data available for the selected options.');
    purgeHeatmap('No data available for the selected options.');
    renderProblemList([]);
    return;
  }

  const filteredProblems = filterProblemsByFlags(problemsData);
  // Same flag-filtered set is the fluency source (was a duplicate identical query).
  const fluencyFilteredProblems = filteredProblems;
  window.lastFilteredProblems = filteredProblems.length;
  updateFilteredCount(filterValue);

  if (filteredProblems.length === 0) {
    clearSeqSourceData();
    resetSequenceUI('No attempts match the current flag filter.');
    purgeHeatmap('No attempts match the current flag filter.');
    renderProblemList([]);
    return;
  }

  const structural = {
    username,
    sessionSelection: selectedSessionIds,
    sessionMode,
    nSessions,
    operationFilter,
    filterValue
  };
  seqSourceData.filteredProblems = filteredProblems;
  seqSourceData.fluencyFilteredProblems = fluencyFilteredProblems;
  seqSourceData.structural = structural;

  // Build the ordered + category-filtered population and (re)size the stepper,
  // then render only the attempts inside the current [start, end) window.
  buildSequencePopulation(filteredProblems, structural, fluencyFilteredProblems);
  renderVisible({ relayout: true });
}

// Clear the heatmap and show a centered message.
function purgeHeatmap(message) {
  const heatmapElement = document.getElementById('heatmap');
  if (!heatmapElement) return;
  if (typeof Plotly !== 'undefined') Plotly.purge(heatmapElement);
  heatmapElement.innerHTML = `<div style="text-align:center; padding: 24px; color: #777;">${escapeHtml(message)}</div>`;
}

// Categorize a problem from its text. Addition uses the single-digit
// categorization (Hardest 6 split out of Tough 21); everything else is 'other'.
function problemCategory(problemText) {
  const { num1, operation, num2 } = parseProblemText(problemText);
  if (operation !== '+' || num1 === null || num2 === null) return 'other';
  const lo = Math.min(num1, num2), hi = Math.max(num1, num2);
  if (lo === 0) return 'add-zero';
  if (lo === 1) return 'add-one';
  if (lo === 2) return 'add-two';
  if (lo === hi) return 'doubles';
  if (lo >= 6) return 'hardest-six';   // both addends >= 6, unequal
  return 'tough-21';                    // lo in 3..5, unequal
}

// Which category checkboxes are currently checked (Set of category keys).
function getCheckedCategories() {
  const checked = new Set();
  document.querySelectorAll('#seq-category-checkboxes input[type="checkbox"][data-cat]').forEach((cb) => {
    if (cb.checked) checked.add(cb.dataset.cat);
  });
  return checked;
}

function getSeqOrdering() {
  const el = document.getElementById('seq-ordering');
  return el && el.value === 'difficulty' ? 'difficulty' : 'answer';
}

// Build the ordered, category-filtered population. Resets the window to the full
// range when the structural selection changes; otherwise clamps the existing window.
function buildSequencePopulation(filteredProblems, structural, fluencyFilteredProblems) {
  const ordering = getSeqOrdering();
  const checked = getCheckedCategories();

  const build = (list) => {
    // Base order = the order she answered them (start_time, then attempt_id).
    const base = (list || []).slice().sort((a, b) =>
      String(a.start_time || '').localeCompare(String(b.start_time || '')) ||
      ((a.attempt_id || 0) - (b.attempt_id || 0)));
    base.forEach((p, i) => { p._answerIndex = i; p._cat = problemCategory(p.problem_text); });
    const pop = base.filter((p) => checked.has(p._cat));
    if (ordering === 'difficulty') {
      pop.sort((a, b) => (SEQ_CATEGORY_RANK[a._cat] - SEQ_CATEGORY_RANK[b._cat]) || (a._answerIndex - b._answerIndex));
    }
    return pop;
  };

  const pop = build(filteredProblems);
  const fluencyPop = build(fluencyFilteredProblems || filteredProblems);

  const sig = JSON.stringify([
    structural.username, structural.sessionSelection, structural.nSessions,
    structural.operationFilter, structural.filterValue, [...checked].sort(), ordering
  ]);
  if (sig !== seqState.sig) {
    seqState.sig = sig;
    seqState.window = { start: 0, end: pop.length };   // show everything by default
  } else {
    seqState.window.start = Math.min(seqState.window.start, pop.length);
    seqState.window.end = Math.min(seqState.window.end, pop.length);
  }
  seqState.population = pop;
  seqState.fluencyPopulation = fluencyPop;
  updateSequenceSlider(pop.length);
}

// Render only the attempts inside the current window through the existing pipeline.
function renderVisible(options = {}) {
  const { population } = seqState;
  const w = seqState.window;
  const visible = population.slice(w.start, w.end);
  updateSequenceLabels();

  // The heatmap shows the whole visible window; the LIST narrows to the focused
  // cell (if any). Flag editing reads window.currentFilteredProblems, so that
  // must match what the list renders.
  if (focusedCell && !visible.some((p) => cellMatchesProblem(p, focusedCell))) {
    focusedCell = null;   // focused cell isn't in view anymore
  }
  const listProblems = focusedCell ? visible.filter((p) => cellMatchesProblem(p, focusedCell)) : visible;
  window.currentFilteredProblems = listProblems;
  updateFocusBar();

  // Always render the grid (even with no problems shown) so the heatmap stays in
  // place at the same size; processData([]) yields an empty (all-null) grid.
  const numberRange = document.getElementById('number-range').value.split('-').map(Number);
  const minResponseTimeThreshold = parseInt(document.getElementById('min-response-time-threshold').value);
  const maxResponseTimeThreshold = parseInt(document.getElementById('max-response-time-threshold').value);
  const aggregationMethod = document.getElementById('duplicate-aggregation')?.value || 'average';
  const colorScaleName = document.getElementById('color-scale-selector')?.value || 'classic';
  const operationFilter = document.getElementById('operation-filter').value;

  const metricMode = document.getElementById('metric-mode')?.value || 'response-time';
  const fluencyOverlay = !!document.getElementById('fluency-overlay')?.checked;

  // Fluency is evaluated over the whole in-scope population (all selected
  // sessions / operation / flags), not just the stepped-through window, so the
  // rating reflects everything observed. Restricted to the heatmap number range.
  const fluencyByKey = computeFluencyByCellKey(seqState.fluencyPopulation || seqState.population, numberRange);

  const heatmapData = processData(visible, numberRange, minResponseTimeThreshold, aggregationMethod, fluencyByKey);
  plotHeatmap(heatmapData, numberRange, operationFilter, minResponseTimeThreshold, maxResponseTimeThreshold, aggregationMethod, colorScaleName, focusedCell, metricMode, fluencyOverlay);
  renderFluencyRollup(fluencyByKey, operationFilter, metricMode, fluencyOverlay);
  // Problem-list HTML for thousands of rows is expensive; skip while collapsed.
  if (isProblemListExpanded()) {
    renderProblemList(listProblems);
  }
  if (options.relayout) {
    setTimeout(() => relayoutHeatmapSize(), 60);
  }
}

// Show/hide the "focused on N + M" bar above the problem list.
function updateFocusBar() {
  const bar = document.getElementById('problem-focus-bar');
  if (!bar) return;
  if (focusedCell) {
    bar.style.display = 'block';
    bar.innerHTML = `Focused on <strong>${focusedCell.num1} + ${focusedCell.num2}</strong> — ` +
      `<a href="#" onclick="clearAnalysisFocus(); return false;">show all</a>`;
  } else {
    bar.style.display = 'none';
    bar.innerHTML = '';
  }
}

// Point the two range thumbs at 0..n and reflect the current window.
function updateSequenceSlider(n) {
  const startEl = document.getElementById('seq-start');
  const endEl = document.getElementById('seq-end');
  if (!startEl || !endEl) return;
  startEl.max = String(n);
  endEl.max = String(n);
  startEl.value = String(seqState.window.start);
  endEl.value = String(seqState.window.end);
  updateSequenceLabels();
}

function updateSequenceLabels() {
  const n = seqState.population.length;
  const w = seqState.window;
  const fill = document.getElementById('seq-fill');
  if (fill) {
    const pct = (v) => (n > 0 ? (v / n) * 100 : 0);
    fill.style.left = pct(w.start) + '%';
    fill.style.width = Math.max(0, pct(w.end) - pct(w.start)) + '%';
  }
  const label = document.getElementById('seq-label');
  const sub = document.getElementById('seq-sublabel');
  const shown = Math.max(0, w.end - w.start);
  const ordering = getSeqOrdering() === 'difficulty' ? 'difficulty order' : 'answer order';
  if (label) label.textContent = `Showing ${shown} of ${n} problems (${ordering}).`;
  if (sub) {
    if (n === 0) { sub.textContent = ''; }
    else if (shown === 0) { sub.textContent = 'Slide the right handle to the right to reveal problems one by one.'; }
    else { sub.textContent = `Positions ${w.start + 1}–${w.end} of the ${ordering} sequence.`; }
  }
}

function resetSequenceUI(message) {
  seqState.population = [];
  seqState.fluencyPopulation = [];
  seqState.window = { start: 0, end: 0 };
  seqState.sig = null;
  const startEl = document.getElementById('seq-start');
  const endEl = document.getElementById('seq-end');
  if (startEl) { startEl.max = '0'; startEl.value = '0'; }
  if (endEl) { endEl.max = '0'; endEl.value = '0'; }
  const fill = document.getElementById('seq-fill');
  if (fill) { fill.style.left = '0%'; fill.style.width = '0%'; }
  const label = document.getElementById('seq-label');
  const sub = document.getElementById('seq-sublabel');
  if (label) label.textContent = message || 'No data loaded.';
  if (sub) sub.textContent = '';
}

function queryDatabase(db, username, sessionSelection, nSessions, operationFilter, options = {}) {
  // Build the SQL query
  let query = `
    SELECT ProblemAttempts.*, Sessions.start_time
    FROM ProblemAttempts
    JOIN Sessions ON ProblemAttempts.session_id = Sessions.session_id
  `;
  const conditions = [];
  const params = [];
  const sessionTypeExclusion = options.excludeVisualPractice ? sessionTypeExclusionSql(db, 'Sessions') : '';

  // Username selection
  if (username !== 'all') {
    conditions.push('Sessions.user_name = ?');
    params.push(username);
  }

  // Session selection: checkbox id list, last/lastN presets, a single id, or all.
  if (Array.isArray(sessionSelection)) {
    if (sessionSelection.length === 0) return [];
    conditions.push(`ProblemAttempts.session_id IN (${sessionSelection.map(() => '?').join(',')})`);
    params.push(...sessionSelection);
  } else if (sessionSelection === 'last' || sessionSelection === 'lastN') {
    const sessionIds = getLastNSessionIds(db, sessionSelection === 'last' ? 1 : nSessions, username);
    if (sessionIds.length === 0) return [];
    conditions.push(`ProblemAttempts.session_id IN (${sessionIds.map(() => '?').join(',')})`);
    params.push(...sessionIds);
  } else if (sessionSelection !== 'all') {
    // Individual session selected
    conditions.push('ProblemAttempts.session_id = ?');
    params.push(sessionSelection);
  }

  // Operation filtering happens after the query (parsed from problem_text below)

  if (conditions.length > 0) {
    query += ' WHERE ' + conditions.join(' AND ');
  } else if (sessionTypeExclusion) {
    query += ' WHERE 1=1';
  }
  query += sessionTypeExclusion;

  query += ' ORDER BY Sessions.start_time';

  // Execute the query
  const stmt = db.prepare(query);
  if (params.length > 0) stmt.bind(params);
  const problemsData = [];
  while (stmt.step()) {
    const row = stmt.getAsObject();
    row.flags = parseFlags(row.flags_json);
    problemsData.push(row);
  }
  stmt.free();

  // Add this: Log the number of problems and their response times
  console.log('Number of problems retrieved:', problemsData.length);
  // RETAIN console.log('Response times:', problemsData.map(p => p.response_time_ms));

  // Filter by operation if needed
  if (operationFilter !== 'all') {
    return problemsData.filter(problem => {
      const { operation } = parseProblemText(problem.problem_text);
      if (operationFilter === 'addsub') {
        return operation === '+' || operation === '-';
      } else if (operationFilter === 'muldiv') {
        return operation === '*' || operation === '/';
      } else {
        return operation === operationFilter;
      }
    });
  }

  return problemsData;
}

function getLastNSessionIds(db, n, username) {
  const limit = Number.isFinite(n) && n > 0 ? Math.floor(n) : 1;
  return listSessionsNewestFirst(db, username)
    .slice(0, limit)
    .map((row) => row.session_id);
}

// parseProblemText, parseSessionTimestamp, and computeMedian are now in math_utils.js

function processData(problemsData, numberRange, minResponseTimeThreshold, aggregationMethod = 'average', fluencyByKey = null) {
  // Filter out problems without num1 or num2
  problemsData = problemsData.filter(problem => {
    const { num1, num2 } = parseProblemText(problem.problem_text);
    return num1 !== null && num2 !== null;
  });

  const num1Range = Array.from({ length: numberRange[1] - numberRange[0] + 1 }, (_, i) => i + numberRange[0]);
  const num2Range = Array.from({ length: numberRange[1] - numberRange[0] + 1 }, (_, i) => i + numberRange[0]);

  // Initialize the data grid
  const dataGrid = [];
  for (let i = 0; i < num1Range.length; i++) {
    dataGrid[i] = [];
    for (let j = 0; j < num2Range.length; j++) {
      dataGrid[i][j] = {
        responseTimes: [],
        attemptCount: 0,
        displayedTime: null,
        averageResponseTime: null,
        incorrect: false,
        equation: `${num1Range[i]} ? ${num2Range[j]}`,
        hasFlag: false,
        flagReasons: [],
        fluencyStatus: 'nodata',
        fluencyMedianMs: null,
        fluencyAccuracy: null
      };
    }
  }

  // Organize data by num1 and num2
  const dataMap = {};
  problemsData.forEach(problem => {
    const { num1, operation, num2 } = parseProblemText(problem.problem_text);
    if (num1 === null || num2 === null || operation === null) return;

    // Use | as the delimiter: '-' collides with the subtraction operator and negative numbers
    const key = `${num1}|${operation}|${num2}`;
    if (!dataMap[key]) {
      dataMap[key] = [];
    }
    dataMap[key].push(problem);
  });

  // Calculate response times and store all data
  for (const key in dataMap) {
    const [num1Str, operation, num2Str] = key.split('|');
    const num1 = parseInt(num1Str);
    const num2 = parseInt(num2Str);
    const problems = dataMap[key];

    const responseTimes = problems.map(p => p.response_time_ms);
    const averageResponseTime = calculateAverage(responseTimes);
    const displayedTime = calculateAggregatedTime(responseTimes, aggregationMethod);
    const incorrect = problems.some(p => p.is_correct === 0);
    const flagReasons = [];
    problems.forEach(problem => {
      const flags = Array.isArray(problem.flags) ? problem.flags : [];
      flags.forEach(flag => {
        if (flag && flag.reason && !flagReasons.includes(flag.reason)) {
          flagReasons.push(flag.reason);
        }
      });
    });

    const i = num1 - numberRange[0];
    const j = num2 - numberRange[0];
    if (i >= 0 && j >= 0 && i < dataGrid.length && j < dataGrid[i].length) {
      dataGrid[i][j].responseTimes = responseTimes;
      dataGrid[i][j].attemptCount = problems.length;
      dataGrid[i][j].displayedTime = displayedTime;
      dataGrid[i][j].averageResponseTime = averageResponseTime;
      dataGrid[i][j].incorrect = incorrect;
      dataGrid[i][j].equation = formatProblemTextForDisplay(`${num1} ${operation} ${num2}`);
      dataGrid[i][j].hasFlag = flagReasons.length > 0;
      dataGrid[i][j].flagReasons = flagReasons;
      if (fluencyByKey) {
        const f = fluencyByKey[key];
        dataGrid[i][j].fluencyStatus = f ? f.status : 'nodata';
        dataGrid[i][j].fluencyMedianMs = f ? f.medianMs : null;
        dataGrid[i][j].fluencyAccuracy = f ? f.accuracy : null;
      }
    }
  }

  // Add this: Log the number of problems after filtering
  console.log('Number of problems after filtering:', problemsData.length);

  // Add this: Log the final data grid
  // RETAIN console.log('Final data grid:', dataGrid);

  return dataGrid;
}

// Hardened 2026-06-16 (Claude Code cloud session): average only over finite numbers. A
// null / undefined / NaN entry (e.g. a stored attempt with a missing response_time_ms) is
// dropped from BOTH the numerator and the denominator instead of being coerced to 0, which
// would silently pull the average down. Parallel to the SQLite combiner's session_summary
// fix (tools/combine_sqlite.py). Pure hardening: for all-numeric input the result is
// unchanged, and an empty (or all-non-finite) input still returns null as before.
function calculateAverage(values) {
  const nums = values.filter((v) => Number.isFinite(v));
  if (nums.length === 0) return null;
  const sum = nums.reduce((a, b) => a + b, 0);
  return sum / nums.length;
}

function calculateAggregatedTime(times, method) {
  if (!times || times.length === 0) return null;
  switch (method) {
    case 'first':
      return times[0];
    case 'last':
      return times[times.length - 1];
    case 'min':
      return Math.min(...times);
    case 'max':
      return Math.max(...times);
    case 'average':
    default:
      return times.reduce((a, b) => a + b, 0) / times.length;
  }
}

// Smallest value the Max Scale slider may take. A max of 0 (or a max at or
// below the min) makes Plotly ignore the manual range and autoscale to the
// data, which looked like the whole scale "jumping" when the slider hit the
// bottom. Clamp so the range is always valid and increasing.
const MIN_HEATMAP_MAX_MS = 100;
function getHeatmapPlotHeight() {
  const heatmapEl = document.getElementById('heatmap');
  const wrapper = heatmapEl && heatmapEl.closest('.heatmap-wrapper');
  const width = (wrapper && wrapper.clientWidth) || (heatmapEl && heatmapEl.clientWidth) || 700;
  const isMobile = window.innerWidth <= 1024;
  const aspect = isMobile ? 0.5 : 0.36;
  const aspectHeight = Math.max(160, Math.round(width * aspect));
  const seqEl = document.getElementById('sequence-controls');
  const seqReserve = seqEl ? seqEl.offsetHeight + 10 : 110;
  if (heatmapEl) {
    const top = heatmapEl.getBoundingClientRect().top;
    if (top > 0 && top < window.innerHeight) {
      const available = window.innerHeight - top - seqReserve - 8;
      if (available > 160) return Math.min(aspectHeight, Math.round(available));
    }
  }
  return aspectHeight;
}
function relayoutHeatmapSize() {
  const heatmapElement = document.getElementById('heatmap');
  if (!heatmapElement || typeof Plotly === 'undefined') return;
  const height = getHeatmapPlotHeight();
  Plotly.relayout(heatmapElement, { height: height, autosize: true });
}
function clampHeatmapScale(minThreshold, maxThreshold) {
  const zmin = Number.isFinite(minThreshold) ? Math.max(0, minThreshold) : 0;
  let zmax = Number.isFinite(maxThreshold) ? maxThreshold : MIN_HEATMAP_MAX_MS;
  zmax = Math.max(zmax, MIN_HEATMAP_MAX_MS);
  if (zmax <= zmin) zmax = zmin + MIN_HEATMAP_MAX_MS;
  return { zmin, zmax };
}

// --- Fluency view helpers (shared rubric comes from fluency_core.js) ---

// Discrete 5-band colorscale for the fluency heatmap. With zmin=-0.5, zmax=4.5
// each integer z (0..4) lands in the center of its band.
const FLUENCY_HEATMAP_SCALE = [
  [0.0, '#616161'], [0.2, '#616161'],   // gray  (z=0)
  [0.2, '#c62828'], [0.4, '#c62828'],   // red   (z=1)
  [0.4, '#f9a825'], [0.6, '#f9a825'],   // yellow(z=2)
  [0.6, '#2e7d32'], [0.8, '#2e7d32'],   // green (z=3)
  [0.8, '#1565c0'], [1.0, '#1565c0']    // blue  (z=4)
];
const FLUENCY_STATUS_Z = { gray: 0, red: 1, yellow: 2, green: 3, blue: 4 };
function fluencyStatusToZ(status) {
  return (status && FLUENCY_STATUS_Z[status] !== undefined) ? FLUENCY_STATUS_Z[status] : null;
}
// White text reads better on the dark fills; black on yellow.
function fluencyTextColor(status) {
  return (status === 'yellow' || !status || status === 'nodata') ? 'black' : '#ffffff';
}

// Read fluency rubric parameters from the analysis-page controls (falls back to
// defaultFluencyThresholds from fluency_core.js when a control is missing).
function getFluencyThresholdsFromControls() {
  const defs = (typeof defaultFluencyThresholds !== 'undefined') ? defaultFluencyThresholds : {
    windowSize: 5, minAccuracy: 0.8, greenMs: 2000, redMs: 4000
  };
  const greenMs = parseInt(document.getElementById('fluency-threshold')?.value) || defs.greenMs;
  const redMs = parseInt(document.getElementById('fluency-red-threshold')?.value) || defs.redMs;
  const windowSize = parseInt(document.getElementById('fluency-window')?.value) || defs.windowSize;
  let minAccPct = parseFloat(document.getElementById('fluency-min-accuracy')?.value);
  if (Number.isNaN(minAccPct)) minAccPct = defs.minAccuracy * 100;
  minAccPct = Math.min(100, Math.max(0, minAccPct));
  return { greenMs, redMs, windowSize, minAccuracy: minAccPct / 100 };
}
function setupFluencyRubricControls(db) {
  const refresh = () => { syncThresholdLabels(); generateHeatmap(db); };
  ['fluency-threshold', 'fluency-window', 'fluency-red-threshold'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', refresh);
  });
  const minAcc = document.getElementById('fluency-min-accuracy');
  if (minAcc) {
    minAcc.addEventListener('input', refresh);
    minAcc.addEventListener('change', refresh);
  }
  const saveBtn = document.getElementById('fluency-thresholds-save');
  if (saveBtn) saveBtn.addEventListener('click', saveFluencyThresholdsToFile);
  const restoreBtn = document.getElementById('fluency-thresholds-restore');
  if (restoreBtn) restoreBtn.addEventListener('click', restoreFluencyThresholdsToDefault);
}
// Set the four fluency-rubric controls from a thresholds object {greenMs, redMs, windowSize,
// minAccuracy} (minAccuracy a 0-1 fraction or already a percent), sync the labels, and persist.
function setFluencyControlsFromThresholds(th) {
  if (!th) return;
  const set = (id, val) => { const el = document.getElementById(id); if (el && val != null) el.value = String(val); };
  if (th.greenMs != null) set('fluency-threshold', Math.round(th.greenMs));
  if (th.redMs != null) set('fluency-red-threshold', Math.round(th.redMs));
  if (th.windowSize != null) set('fluency-window', Math.round(th.windowSize));
  if (th.minAccuracy != null) set('fluency-min-accuracy', Math.round(th.minAccuracy <= 1 ? th.minAccuracy * 100 : th.minAccuracy));
  syncThresholdLabels();
  saveControls();
}
function _fluencyThresholdsStatus(text, color) {
  const el = document.getElementById('fluency-thresholds-status');
  if (el) { el.textContent = text || ''; el.style.color = color || '#555'; }
}
// "Save to loaded file": write the four rubric parameters into the loaded learner's profile in
// the file they're viewing (the same file the editor / anchor read), so the end-of-quiz % and
// generate-by-fluency use them.
async function saveFluencyThresholdsToFile() {
  const ctx = window.__analysisEditorCtx;
  if (!ctx || !ctx.user || ctx.user === 'all') {
    _fluencyThresholdsStatus('Load a learner file first (with the dev server running).', '#b45309');
    return;
  }
  const thresholds = getFluencyThresholdsFromControls();
  try {
    const r = await fetch('/api/profile', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder: ctx.folder, user: ctx.user, file: ctx.file, thresholds }),
    });
    const j = await r.json();
    if (j && j.ok) _fluencyThresholdsStatus(`Saved to ${j.relativePath || j.file || 'the file'}.`, 'green');
    else _fluencyThresholdsStatus((j && (j.message || j.error)) || 'Save failed.', 'red');
  } catch (e) {
    _fluencyThresholdsStatus('Dev server not reachable — could not save.', 'red');
  }
}
// "Restore defaults": reset the four rubric controls to the system-wide defaults and re-render.
// Does not write to the file (the operator can Save afterwards to persist).
function restoreFluencyThresholdsToDefault() {
  const defs = (typeof defaultFluencyThresholds !== 'undefined') ? defaultFluencyThresholds
    : { greenMs: 2000, redMs: 4000, windowSize: 5, minAccuracy: 0.8 };
  setFluencyControlsFromThresholds(defs);
  generateHeatmap(db);
  _fluencyThresholdsStatus('Restored system defaults (not saved).', '#555');
}
// On load, prefill the rubric controls from the loaded file's saved profile so the operator
// sees (and the heatmap uses) that learner's saved parameters. Falls back silently to the
// current/persisted controls when the dev server isn't reachable.
async function prefillFluencyThresholdsFromProfile(ctx) {
  if (!ctx || !ctx.user || ctx.user === 'all') return;
  try {
    let url = `/api/profile?folder=${encodeURIComponent(ctx.folder)}&user=${encodeURIComponent(ctx.user)}`;
    if (ctx.file) url += `&file=${encodeURIComponent(ctx.file)}`;
    const j = await (await fetch(url)).json();
    if (j && j.ok && j.profile && j.profile.thresholds) {
      setFluencyControlsFromThresholds(j.profile.thresholds);
      generateHeatmap(db);
    }
  } catch (e) { /* dev server not reachable — keep the current controls */ }
}
// The single app-wide fluency number (same as the anchor end-of-quiz readout, the kid
// Fluency feast, the fluency-tracker cards, and the dragon game): % of the full 0-9
// addition universe the learner is fluent at, via the shared fluencyPercent rubric
// (fluency_core.js). Computed over the learner's FULL history including visual-practice
// sessions (not the page's session/operation filters), with the rubric parameters from
// the page controls so parameter changes show here too.
function updateCurrentFluencyPercentage(db, username) {
  const el = document.getElementById('current-fluency-percentage');
  if (!el) return;
  if (!db || typeof fluencyPercent !== 'function') {
    el.textContent = 'Current fluency percentage: --%';
    return;
  }
  const attempts = queryDatabase(db, username, 'all', 0, 'all');
  const pct = fluencyPercent(attempts, getFluencyThresholdsFromControls(), {
    numberRange: [0, 9], operations: ['+'], excludeFlagged: true
  });
  el.textContent = `Current fluency percentage: ${pct}%`;
}

// Evaluate the fluency rating for each grid cell (raw num1|op|num2 key) from the
// in-scope attempts, via the shared rubric. Recency-sorted so the rolling window
// sees the most recent attempts. Restricted to the heatmap number range.
function computeFluencyByCellKey(problems, numberRange) {
  if (typeof classifyFactsByStatus !== 'function') return {};
  // Rubric params come from the page controls; the grouping/evaluation is the shared
  // core (also used by the problem-list generator) so the two never drift.
  return classifyFactsByStatus(problems, getFluencyThresholdsFromControls(), { numberRange });
}

// Map the analysis-page operation-filter value to the concrete operation set the
// problem-list generator enumerates over.
function operationsForFilter(filterValue) {
  switch (filterValue) {
    case 'addsub': return ['+', '-'];
    case 'muldiv': return ['*', '/'];
    case 'all': return ['+', '-', '*', '/'];
    default: return [filterValue];
  }
}

// DOM wrapper around generateFluencyProblemList (fluency_core.js): build a problem
// list from the currently-loaded analysis DB + page controls. Rubric thresholds,
// number range, and operation filter come from the page; the list shape (length,
// distribution, session selection, optional category filter, rng) is passed in.
// Returns the generator result, or null if no DB is loaded.
//   mqGenerateProblemList({ numProblems: 10, distribution: { almost: 0.5, 'needs-practice': 0.25, fluent: 0.25 } })
//   mqGenerateProblemList({ numProblems: 10, distribution: { missing: 1 }, sessionSelection: { mode: 'recentN', n: 3 } })
function generateProblemListFromControls(spec) {
  const s = spec || {};
  const getDb = (typeof window !== 'undefined') ? window.__analysisDb : null;
  const db = typeof getDb === 'function' ? getDb() : null;
  if (!db) { console.warn('generateProblemListFromControls: no analysis DB loaded'); return null; }
  const username = document.getElementById('username-selection')?.value || 'all';
  const operationFilter = document.getElementById('operation-filter')?.value || '+';
  const rangeEl = document.getElementById('number-range');
  const numberRange = (rangeEl && rangeEl.value ? rangeEl.value : '0-9').split('-').map(Number);
  // Pull every attempt for the learner; the generator applies the session selection itself.
  const attempts = queryDatabase(db, username, 'all', 0, 'all', { excludeVisualPractice: true });
  return generateFluencyProblemList({
    attempts,
    numProblems: s.numProblems,
    distribution: s.distribution,
    thresholds: getFluencyThresholdsFromControls(),
    sessionSelection: s.sessionSelection || { mode: 'all' },
    numberRange,
    operations: s.operations || operationsForFilter(operationFilter),
    categories: s.categories,
    excludeFlagged: true,   // generation never lets a flagged answer color a fact's fluency
    rng: s.rng
  });
}
// Exposed for the shared problem-list editor's "Generate by fluency" action (and console use).
if (typeof window !== 'undefined') window.mqGenerateProblemList = generateProblemListFromControls;

// Roll-up strip above the heatmap: operation level, the broad 0-5 vs 6-9 split,
// and (for addition) the category level — each via the min/worst-of rule. Shown
// only in the fluency view or when the overlay is on.
function renderFluencyRollup(fluencyByKey, operationFilter, metricMode, showOverlay) {
  const el = document.getElementById('fluency-rollup');
  if (!el) return;
  const active = (metricMode === 'fluency' || showOverlay) && typeof fluencyRollupStatus === 'function';
  if (!active) { el.style.display = 'none'; el.innerHTML = ''; return; }

  const facts = [];
  for (const key in fluencyByKey) {
    const st = fluencyByKey[key] && fluencyByKey[key].status;
    if (!st || st === 'nodata') continue;
    const [n1, op, n2] = key.split('|');
    facts.push({ num1: +n1, op, num2: +n2, status: st });
  }
  if (!facts.length) { el.style.display = 'none'; el.innerHTML = ''; return; }

  const chip = (label, status, title) => {
    const color = fluencyStatusColors[status] || '#999';
    const lbl = STATUS_LABELS[status] || status;
    return `<span title="${title || ''}" style="display:inline-flex;align-items:center;gap:5px;padding:2px 8px;border:1px solid #e0e0e0;border-radius:999px;background:#fff;">`
      + `<span style="width:11px;height:11px;border-radius:50%;background:${color};border:1px solid rgba(0,0,0,.15);"></span>`
      + `<span style="font-weight:600;">${label}</span>`
      + `<span style="color:${color};font-weight:600;">${lbl}</span></span>`;
  };
  const group = (title, inner) => inner
    ? `<span style="display:inline-flex;align-items:center;gap:6px;flex-wrap:wrap;">`
      + `<span style="color:#666;font-size:11px;text-transform:uppercase;letter-spacing:.04em;">${title}</span>${inner}</span>`
    : '';
  const rollOf = (arr) => fluencyRollupStatus(arr.map((f) => f.status));
  const titleOf = (arr) => {
    const b = fluencyStatusBreakdown(arr.map((f) => f.status));
    return `${b.blue} permanent · ${b.green} fluent · ${b.yellow} almost · ${b.red} needs practice · ${b.gray} incorrect`;
  };

  let html = group('Operation', chip('All facts', rollOf(facts), titleOf(facts)));

  const easy = facts.filter((f) => Math.max(f.num1, f.num2) <= 5);
  const hard = facts.filter((f) => Math.max(f.num1, f.num2) >= 6);
  let split = '';
  if (easy.length) split += chip('0–5', rollOf(easy), titleOf(easy));
  if (hard.length) split += chip('6–9', rollOf(hard), titleOf(hard));
  html += group('By range', split);

  const addFacts = facts.filter((f) => f.op === '+');
  if (addFacts.length) {
    let cats = '';
    FLUENCY_CATEGORY_ORDER.forEach((cat) => {
      const inCat = addFacts.filter((f) => additionCategoryOf(f.num1, f.num2) === cat);
      if (inCat.length) cats += chip(FLUENCY_CATEGORY_LABELS[cat], rollOf(inCat), titleOf(inCat));
    });
    html += group('By category (addition)', cats);
  }

  el.innerHTML = html;
  el.style.cssText = 'display:flex;flex-wrap:wrap;gap:14px 18px;align-items:center;margin:0 0 10px;padding:8px 12px;background:#fafafa;border:1px solid #e6e6e6;border-radius:8px;font-size:12px;';
}

function plotHeatmap(dataGrid, numberRange, operationFilter, minResponseTimeThreshold, maxResponseTimeThreshold, aggregationMethod = 'average', colorScaleName = 'classic', focus = null, metricMode = 'response-time', showOverlay = false) {
  const fluencyMode = metricMode === 'fluency' && typeof fluencyStatusToZ === 'function';
  const numLabels = Array.from({ length: numberRange[1] - numberRange[0] + 1 }, (_, i) => i + numberRange[0]);
  const zData = dataGrid.map(row => row.map(cell => {
    if (fluencyMode) return fluencyStatusToZ(cell.fluencyStatus);
    if (cell.displayedTime === null) return null;
    return cell.displayedTime;
  }));
  const textData = dataGrid.map(row => row.map(cell => cell.equation));

  // Log data range
  const allValues = zData.flat().filter(val => val !== null);
  console.log('Data range:', Math.min(...allValues), 'to', Math.max(...allValues));

  const isMobile = window.innerWidth <= 767;

  // Color scale: fluency mode uses the discrete 5-band rubric scale; otherwise
  // the response-time gradient (light = fast, dark = slow).
  let customColorScale, zmin, zmax;
  if (fluencyMode) {
    customColorScale = FLUENCY_HEATMAP_SCALE;
    zmin = -0.5; zmax = 4.5;
  } else {
    customColorScale = COLOR_SCALES[colorScaleName] || COLOR_SCALES.classic;
    ({ zmin, zmax } = clampHeatmapScale(minResponseTimeThreshold, maxResponseTimeThreshold));
  }

  // Build hover text (fluency rating, or response time + attempt count).
  const hoverTextData = dataGrid.map(row => row.map(cell => {
    if (fluencyMode) {
      if (!cell.fluencyStatus || cell.fluencyStatus === 'nodata') return '';
      const label = (typeof STATUS_LABELS !== 'undefined' && STATUS_LABELS[cell.fluencyStatus]) || cell.fluencyStatus;
      const med = cell.fluencyMedianMs != null ? `<br>Median: ${Math.round(cell.fluencyMedianMs)} ms` : '';
      const acc = cell.fluencyAccuracy != null ? `<br>Accuracy: ${Math.round(cell.fluencyAccuracy * 100)}%` : '';
      const att = cell.attemptCount ? `<br>Attempts: ${cell.attemptCount}` : '';
      return `${cell.equation}<br>Fluency: ${label}${med}${acc}${att}`;
    }
    if (cell.displayedTime === null) return '';
    const attemptInfo = cell.attemptCount > 1 ? `<br>Attempts: ${cell.attemptCount} (${aggregationMethod})` : '';
    return `${cell.equation}<br>Time: ${Math.round(cell.displayedTime)} ms${attemptInfo}`;
  }));

  const data = [{
    x: numLabels,
    y: numLabels,
    z: zData,
    text: hoverTextData,
    type: 'heatmap',
    colorscale: customColorScale,
    zmin: zmin,
    zmax: zmax,
    hoverinfo: 'text',
    colorbar: fluencyMode ? {
      title: { text: 'Fluency', font: { size: isMobile ? 10 : 11 } },
      tickmode: 'array', tickvals: [0, 1, 2, 3, 4],
      ticktext: ['Incorrect', 'Needs practice', 'Almost', 'Fluent', 'Permanent'],
      tickfont: { size: isMobile ? 8 : 9 }
    } : {
      title: { text: 'Time (ms)', font: { size: isMobile ? 10 : 11 } },
      tickfont: { size: isMobile ? 9 : 10 }
    }
  }];

  // Highlight the focused cell (click-to-focus). Computed as a layout shape below
  // so it frames the whole colored cell, not just the equation text.

  // Add annotations
  const annotations = [];
  for (let i = 0; i < dataGrid.length; i++) {
    for (let j = 0; j < dataGrid[i].length; j++) {
      const cell = dataGrid[i][j];
      const x = numLabels[j];
      const y = numLabels[i];
      if (cell.displayedTime !== null) {
        // Main equation annotation
        annotations.push({
          x: x,
          y: y,
          text: cell.equation,
          showarrow: false,
          font: {
            color: fluencyMode ? fluencyTextColor(cell.fluencyStatus) : (cell.incorrect ? '#CC0000' : 'black'),
            size: isMobile ? 10 : 14,
            weight: 'bold'
          }
        });
        
        // Attempt count badge (top-left corner) when there are duplicates
        if (cell.attemptCount > 1) {
          annotations.push({
            x: x,
            y: y,
            text: cell.attemptCount.toString(),
            showarrow: false,
            xshift: isMobile ? BADGE_XSHIFT_MOBILE : BADGE_XSHIFT_DESKTOP,
            yshift: isMobile ? BADGE_YSHIFT_MOBILE : BADGE_YSHIFT_DESKTOP,
            font: {
              size: isMobile ? 8 : 11,
              color: '#ffffff'
            },
            bgcolor: '#1565c0',
            borderpad: isMobile ? 2 : 3
          });
        }
        
        // Flag indicator (bottom-right corner)
        if (cell.hasFlag) {
          annotations.push({
            x: x,
            y: y,
            text: '⚠️',
            showarrow: false,
            xshift: isMobile ? 10 : 16,
            yshift: isMobile ? -10 : -16,
            font: {
              size: isMobile ? 10 : 12,
              color: '#f39c12'
            }
          });
        }
      }
    }
  }

  // Generate title based on aggregation method
  const aggregationTitles = {
    'average': 'Average Response Times',
    'first': 'First Attempt Response Times',
    'last': 'Last Attempt Response Times',
    'min': 'Fastest (Min) Response Times',
    'max': 'Slowest (Max) Response Times'
  };
  const titleText = fluencyMode ? 'Fluency rating' : (aggregationTitles[aggregationMethod] || 'Response Times');

  const layout = {
    height: getHeatmapPlotHeight(),
    title: {
      text: titleText,
      font: { size: isMobile ? 12 : 13 }
    },
    xaxis: {
      title: {
        text: 'Second Number (num2)',
        font: { size: isMobile ? 10 : 11 }
      },
      type: 'category',
      tickfont: { size: isMobile ? 10 : 14 }
    },
    yaxis: {
      title: {
        text: 'First Number (num1)',
        font: { size: isMobile ? 10 : 11 }
      },
      type: 'category',
      tickfont: { size: isMobile ? 10 : 14 }
    },
    annotations: annotations,
    margin: {
      l: 42,
      r: 42,
      b: isMobile ? 70 : 42,
      t: 32,
      pad: 2
    },
    autosize: true
  };

  // Cell outlines: the fluency overlay (per-cell rating borders, response-time
  // mode only — redundant when the fill already shows fluency) plus the focused
  // cell frame. On a category axis, numeric shape coords are the 0-based category
  // indices, so ±0.5 spans one cell.
  const shapes = [];
  if (showOverlay && !fluencyMode && typeof fluencyStatusColors !== 'undefined') {
    for (let i = 0; i < dataGrid.length; i++) {
      for (let j = 0; j < dataGrid[i].length; j++) {
        const st = dataGrid[i][j].fluencyStatus;
        if (!st || st === 'nodata') continue;
        shapes.push({
          type: 'rect', xref: 'x', yref: 'y',
          x0: j - 0.46, x1: j + 0.46, y0: i - 0.46, y1: i + 0.46,
          line: { color: fluencyStatusColors[st] || '#333', width: 3 }, fillcolor: 'rgba(0,0,0,0)'
        });
      }
    }
  }
  if (focus) {
    const fi = numLabels.indexOf(focus.num1);   // row (num1 / y)
    const fj = numLabels.indexOf(focus.num2);   // col (num2 / x)
    if (fi >= 0 && fj >= 0) {
      shapes.push({
        type: 'rect', xref: 'x', yref: 'y',
        x0: fj - 0.5, x1: fj + 0.5, y0: fi - 0.5, y1: fi + 0.5,
        line: { color: '#111', width: 3 }, fillcolor: 'rgba(0,0,0,0)'
      });
    }
  }
  if (shapes.length) layout.shapes = shapes;

  const config = {
    responsive: true,
    displayModeBar: false
  };

  // Prefer react (in-place update) over newPlot (full tear-down) on subsequent draws.
  try {
    const gd = document.getElementById('heatmap');
    const canReact = gd && Array.isArray(gd.data) && gd.data.length > 0 && typeof Plotly.react === 'function';
    if (canReact) {
      Plotly.react(gd, data, layout, config);
    } else {
      Plotly.newPlot('heatmap', data, layout, config);
    }
    console.log('Heatmap plotted successfully');
    // Click a cell -> focus the problem list on that problem.
    const plotEl = document.getElementById('heatmap');
    if (plotEl && typeof plotEl.on === 'function') {
      if (typeof plotEl.removeAllListeners === 'function') plotEl.removeAllListeners('plotly_click');
      plotEl.on('plotly_click', (ev) => {
        const pt = ev && ev.points && ev.points[0];
        if (!pt) return;
        const num2 = Number(pt.x), num1 = Number(pt.y);
        if (Number.isFinite(num1) && Number.isFinite(num2)) onCellClick(num1, num2);
      });
    }
  } catch (error) {
    console.error('Error plotting heatmap:', error);
  }
}

// Add file loading functionality

// Drop all session data from the live analysis DB (Users/Sessions/ProblemAttempts).
function clearAnalysisDbData(db) {
  db.run('DELETE FROM ProblemAttempts');
  db.run('DELETE FROM Sessions');
  db.run('DELETE FROM Users');
}

// Replace the live analysis DB with an uploaded .sqlite (anchor's one-DB-per-person
// format). Any prior sessions (including legacy JSON imports) are cleared first.
// Returns { sessions, attempts }.
function importSqliteIntoDb(db, bytes) {
  if (!SQLModule) throw new Error('SQL.js is not ready yet');
  clearAnalysisDbData(db);
  const uploaded = new SQLModule.Database(bytes);
  let sessions = 0, attempts = 0;
  try {
    // Users (table may be absent in some files)
    try {
      const u = uploaded.prepare('SELECT name FROM Users');
      while (u.step()) db.run('INSERT OR IGNORE INTO Users (name) VALUES (?)', [u.getAsObject().name]);
      u.free();
    } catch (e) { /* no Users table — fine */ }

    const sessionIds = new Set();
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
      sessionIds.add(r.session_id);
      sessions++;
    }
    s.free();

    // ProblemAttempts for the loaded sessions, in answer order (ROWID preserves it).
    const pa = uploaded.prepare('SELECT * FROM ProblemAttempts ORDER BY ROWID');
    while (pa.step()) {
      const r = pa.getAsObject();
      if (!sessionIds.has(r.session_id)) continue;
      db.run(`INSERT OR IGNORE INTO ProblemAttempts (
          session_id, problem_id, problem_text, num1, num2, operation,
          correct_answer, user_answer_string, user_answer, is_correct, response_time_ms, flags_json, presented_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`, [
        r.session_id, r.problem_id ?? null, r.problem_text ?? null, r.num1 ?? null, r.num2 ?? null,
        r.operation ?? null, r.correct_answer ?? null, r.user_answer_string ?? null, r.user_answer ?? null,
        r.is_correct ?? null, r.response_time_ms ?? null, r.flags_json ?? null, r.presented_at ?? null
      ]);
      attempts++;
    }
    pa.free();
  } finally {
    if (typeof uploaded.close === 'function') uploaded.close();
  }
  return { sessions, attempts };
}

// Reset the user dropdown to just "All Users" then repopulate (avoids dupes on
// repeated imports), preserving the current selection when still valid.
function refreshUserDropdown(db) {
  const sel = document.getElementById('username-selection');
  if (!sel) return;
  const current = sel.value;
  sel.innerHTML = '<option value="all">All Users</option>';
  populateUsernameDropdown(db);
  if ([...sel.options].some((o) => o.value === current)) sel.value = current;
}

// ---------------------------------------------------------------------------
// Working-DB persistence (IndexedDB): retain a loaded SQLite across reloads, so
// the analysis page behaves like a live per-person working file. We persist the
// whole in-memory DB and restore it on start; legacy localStorage JSON is still
// folded in (idempotently) after restore.
// ---------------------------------------------------------------------------
const WORKING_DB_IDB = { name: 'mathAnalysisWorkingDb', store: 'kv', key: 'current' };
let sqliteLoaded = false;   // true once a .sqlite has been imported (gates the one-user lock)
let loadedSqliteFilename = null;   // name of the last-loaded .sqlite (to preserve its date on save)
let loadedFileHandle = null;       // FileSystemFileHandle when loaded via the picker (enables auto-save)
let loadedBackupBytes = null;      // snapshot of the file as loaded, for "Revert changes"

function idbOpen() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(WORKING_DB_IDB.name, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(WORKING_DB_IDB.store);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
async function saveWorkingDb(bytes) {
  try {
    const idb = await idbOpen();
    await new Promise((resolve, reject) => {
      const tx = idb.transaction(WORKING_DB_IDB.store, 'readwrite');
      tx.objectStore(WORKING_DB_IDB.store).put(bytes, WORKING_DB_IDB.key);
      tx.oncomplete = resolve; tx.onerror = () => reject(tx.error);
    });
    idb.close();
  } catch (e) { console.warn('Could not persist working DB:', e); }
}
async function loadWorkingDb() {
  try {
    const idb = await idbOpen();
    const bytes = await new Promise((resolve, reject) => {
      const tx = idb.transaction(WORKING_DB_IDB.store, 'readonly');
      const rq = tx.objectStore(WORKING_DB_IDB.store).get(WORKING_DB_IDB.key);
      rq.onsuccess = () => resolve(rq.result || null);
      rq.onerror = () => reject(rq.error);
    });
    idb.close();
    return bytes || null;
  } catch (e) { return null; }
}
async function clearWorkingDb() {
  try {
    const idb = await idbOpen();
    await new Promise((resolve) => {
      const tx = idb.transaction(WORKING_DB_IDB.store, 'readwrite');
      tx.objectStore(WORKING_DB_IDB.store).delete(WORKING_DB_IDB.key);
      tx.oncomplete = resolve; tx.onerror = resolve;
    });
    idb.close();
  } catch (e) { /* ignore */ }
}

// Backup of the file AS LOADED, for "Revert changes" (kept in the same IDB store under a
// separate key so it survives reloads).
const BACKUP_KEY = 'backup';
async function saveBackupDb(bytes) {
  try {
    const idb = await idbOpen();
    await new Promise((resolve, reject) => {
      const tx = idb.transaction(WORKING_DB_IDB.store, 'readwrite');
      tx.objectStore(WORKING_DB_IDB.store).put(bytes, BACKUP_KEY);
      tx.oncomplete = resolve; tx.onerror = () => reject(tx.error);
    });
    idb.close();
  } catch (e) { console.warn('Could not save backup:', e); }
}
async function loadBackupDb() {
  try {
    const idb = await idbOpen();
    const bytes = await new Promise((resolve, reject) => {
      const tx = idb.transaction(WORKING_DB_IDB.store, 'readonly');
      const rq = tx.objectStore(WORKING_DB_IDB.store).get(BACKUP_KEY);
      rq.onsuccess = () => resolve(rq.result || null);
      rq.onerror = () => reject(rq.error);
    });
    idb.close();
    return bytes || null;
  } catch (e) { return null; }
}
// Fire-and-forget snapshot of the current DB after any mutation.
function persistWorkingDb() { if (db) saveWorkingDb(db.export()); }

// Auto-save the working DB back to the loaded file via its File System Access handle. The
// first write prompts once for permission. No handle (loaded via the fallback input, or an
// unsupported browser) -> edits stay in the browser only (no file write-back).
async function autoSaveToFile() {
  if (!loadedFileHandle || !db) return;
  try {
    const writable = await loadedFileHandle.createWritable();
    await writable.write(db.export());
    await writable.close();
  } catch (e) {
    console.warn('Auto-save to file failed:', e);
    const status = document.getElementById('sqlite-status');
    if (status) { status.textContent = `Could not auto-save to the file: ${e.message}`; status.style.color = '#c62828'; }
  }
}

// Revert to the file as loaded (the backup snapshot), discarding flag edits. Restores the
// working DB + (when a handle is held) writes the original back to the file.
async function revertChanges() {
  if (!sqliteLoaded) { alert('No file is loaded to revert.'); return; }
  if (!window.confirm('Revert changes? This discards your flag edits and restores the file as it was loaded.')) return;
  const backup = loadedBackupBytes || await loadBackupDb();
  if (!backup) { alert('No backup is available to revert to.'); return; }
  const status = document.getElementById('sqlite-status');
  try {
    focusedCell = null;
    importSqliteIntoDb(db, backup);
    sqliteLoaded = true;
    persistWorkingDb();
    await autoSaveToFile();   // write the restored copy back to the file (if a handle is held)
    refreshUserDropdown(db);
    applyUserLock();
    populateSessionChecklist(db);
    generateHeatmap(db);
    if (status) { status.textContent = 'Reverted to the file as loaded.'; status.style.color = '#666'; }
  } catch (e) {
    console.error('Revert failed:', e);
    if (status) { status.textContent = `Revert failed: ${e.message}`; status.style.color = '#c62828'; }
  }
}

// A per-person SQLite is one user — lock the user selector to that user once a
// .sqlite is loaded (so the dropdowns and heatmap stay scoped to that person).
function applyUserLock() {
  const sel = document.getElementById('username-selection');
  if (!sel || !db) return;
  let users = [];
  try {
    const r = db.exec('SELECT DISTINCT user_name FROM Sessions WHERE user_name IS NOT NULL');
    users = r.length ? r[0].values.map((v) => v[0]).filter((u) => u != null) : [];
  } catch (e) { users = []; }
  if (sqliteLoaded && users.length === 1) {
    sel.value = users[0];
    sel.disabled = true;
    sel.title = 'Locked: this SQLite holds a single person.';
  } else {
    sel.disabled = false;
    sel.title = '';
  }
}

// ---------------------------------------------------------------------------
// Control persistence: remember the top selections (incl. color scale) across
// reloads, plus a "Reset all to default" that only touches the render controls.
// ---------------------------------------------------------------------------
function saveControls() {
  const state = {};
  for (const id of PERSISTED_CONTROL_IDS) {
    const el = document.getElementById(id);
    if (el && !el.disabled) state[id] = el.value;   // skip the locked user select
  }
  const cats = [];
  document.querySelectorAll('#seq-category-checkboxes input[type="checkbox"][data-cat]')
    .forEach((cb) => { if (cb.checked) cats.push(cb.dataset.cat); });
  state.__categories = cats;
  const overlay = document.getElementById('fluency-overlay');
  state.__fluencyOverlay = !!(overlay && overlay.checked);
  state.__selectedSessionIds = getCheckedSessionIds();
  try { localStorage.setItem(CONTROLS_STORAGE_KEY, JSON.stringify(state)); } catch (e) { /* ignore */ }
}
function restoreControls() {
  let state;
  try { state = JSON.parse(localStorage.getItem(CONTROLS_STORAGE_KEY) || 'null'); } catch (e) { state = null; }
  if (!state) return null;
  for (const id of PERSISTED_CONTROL_IDS) {
    const el = document.getElementById(id);
    if (!el || state[id] == null || el.disabled) continue;
    // Only set if the option exists (dynamic selects: user may differ).
    if (el.tagName === 'SELECT') {
      if ([...el.options].some((o) => o.value === state[id])) el.value = state[id];
    } else {
      el.value = state[id];
    }
  }
  if (Array.isArray(state.__categories)) {
    document.querySelectorAll('#seq-category-checkboxes input[type="checkbox"][data-cat]')
      .forEach((cb) => { cb.checked = state.__categories.includes(cb.dataset.cat); });
  }
  const overlay = document.getElementById('fluency-overlay');
  if (overlay && typeof state.__fluencyOverlay === 'boolean') overlay.checked = state.__fluencyOverlay;
  syncThresholdLabels();
  return state;
}
function syncThresholdLabels() {
  const min = document.getElementById('min-response-time-threshold');
  const max = document.getElementById('max-response-time-threshold');
  const minV = document.getElementById('min-threshold-value');
  const maxV = document.getElementById('max-threshold-value');
  if (min && minV) minV.textContent = min.value;
  if (max && maxV) maxV.textContent = max.value;
  const flu = document.getElementById('fluency-threshold');
  const fluV = document.getElementById('fluency-threshold-value');
  if (flu && fluV) fluV.textContent = flu.value;
  const fluWin = document.getElementById('fluency-window');
  const fluWinV = document.getElementById('fluency-window-value');
  if (fluWin && fluWinV) fluWinV.textContent = fluWin.value;
  const fluRed = document.getElementById('fluency-red-threshold');
  const fluRedV = document.getElementById('fluency-red-threshold-value');
  if (fluRed && fluRedV) fluRedV.textContent = fluRed.value;
}
function resetControlsToDefault(db) {
  for (const [id, val] of Object.entries(CONTROL_DEFAULTS)) {
    const el = document.getElementById(id);
    if (el) el.value = val;
  }
  const overlay = document.getElementById('fluency-overlay');
  if (overlay) overlay.checked = false;
  syncThresholdLabels();
  saveControls();
  generateHeatmap(db);   // session/operation/flag/user are intentionally untouched
}

// ---------------------------------------------------------------------------
// Click-to-focus: clicking a heatmap cell opens the list filtered to that one
// problem and highlights the cell.
// ---------------------------------------------------------------------------
function cellMatchesProblem(problem, cell) {
  if (!cell) return false;
  const { num1, num2 } = parseProblemText(problem.problem_text);
  return num1 === cell.num1 && num2 === cell.num2;
}
function expandProblemList() {
  const toggle = document.getElementById('toggle-problem-list');
  const wrapper = document.querySelector('.problem-list-wrapper');
  if (wrapper && wrapper.classList.contains('collapsed')) {
    wrapper.classList.remove('collapsed');
    if (toggle) toggle.setAttribute('aria-expanded', 'true');
    setTimeout(() => { if (typeof relayoutHeatmapSize === 'function') relayoutHeatmapSize(); }, 350);
  }
}
function onCellClick(num1, num2) {
  if (focusedCell && focusedCell.num1 === num1 && focusedCell.num2 === num2) {
    focusedCell = null;            // clicking the same cell again clears the focus
  } else {
    focusedCell = { num1, num2 };
    expandProblemList();
  }
  // List may have just been expanded — relayout after the width transition.
  renderVisible({ relayout: true });
}
function clearFocus() { focusedCell = null; renderVisible(); }
window.clearAnalysisFocus = clearFocus;   // used by the "show all" link in the focus bar

const SQLITE_PICKER_TYPES = [{
  description: 'SQLite database',
  accept: {
    'application/x-sqlite3': ['.sqlite', '.db', '.sqlite3'],
    'application/octet-stream': ['.sqlite', '.db', '.sqlite3'],
  },
}];

// Load .sqlite bytes into the working view. `handle` (FileSystemFileHandle) is kept when
// present so flag edits can auto-save back to the same file (otherwise null).
async function loadSqliteIntoView(bytes, filename, handle) {
  const status = document.getElementById('sqlite-status');
  const setStatus = (text, color) => { if (status) { status.textContent = text; status.style.color = color; } };
  if (!SQLModule || !db) { setStatus('SQL.js is still loading — try again in a moment.', 'red'); return; }
  setStatus(`Loading ${filename}…`, 'blue');
  try {
    focusedCell = null;
    const res = importSqliteIntoDb(db, bytes);
    sqliteLoaded = true;
    loadedSqliteFilename = filename;
    loadedFileHandle = handle || null;
    loadedBackupBytes = bytes;       // snapshot the file as loaded (for Revert)
    saveBackupDb(bytes);             // backup survives reloads
    persistWorkingDb();              // retain across reloads
    refreshUserDropdown(db);
    applyUserLock();                 // lock to this one person
    resolveEditorContext(filename);  // find this file's dev-server folder so the editor can save lists
    populateSessionChecklist(db);
    generateHeatmap(db);
    setStatus(`Loaded ${filename}: ${res.sessions} session(s), ${res.attempts} attempt(s). Previous sessions were cleared.`,
      res.sessions ? 'green' : '#b45309');
  } catch (e) {
    console.error('SQLite import failed:', e);
    setStatus(`Could not read ${filename}: ${e.message}`, 'red');
  }
}

// After a local .sqlite load there's no ?folder=&user= context, so the problem-list editor
// can't reach the dev server. Ask the server which on-disk copy to target when the same
// basename exists in multiple folders (tlkids vs an old test-trial copy), publish it as
// window.__analysisEditorCtx, and refresh the editor so it enables + saves there.
async function resolveEditorContext(loadedFilename) {
  window.__analysisEditorCtx = null;
  const user = (document.getElementById('username-selection')?.value || '').trim();
  const refreshPanel = () => { if (window.__analysisListPanel) window.__analysisListPanel.refresh(); };
  if (!user || user === 'all') { refreshPanel(); return; }
  try {
    let url = `/api/resolve-editor-target?user=${encodeURIComponent(user)}`;
    if (loadedFilename) url += `&file=${encodeURIComponent(loadedFilename)}`;
    const j = await (await fetch(url)).json();
    if (j && j.ok && j.found) {
      window.__analysisEditorCtx = { folder: j.folder, user: j.user, file: j.file, relativePath: j.relativePath };
      await prefillFluencyThresholdsFromProfile(window.__analysisEditorCtx);
    }
  } catch (e) { /* dev server not reachable — editor stays in its "pick a learner" state */ }
  refreshPanel();
}
function base64ToBytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

// Opened with ?folder=&user= (the anchor "Load for analysis" button)? Auto-load that
// person's latest file from the dev server so you land straight on the data.
async function loadLatestForUrlParams() {
  const params = new URLSearchParams(window.location.search);
  const folder = params.get('folder');
  const user = params.get('user');
  const file = params.get('file');
  const subfolder = params.get('subfolder');
  if (!folder || !user) return;
  const status = document.getElementById('sqlite-status');
  const note = (text) => { if (status) { status.textContent = text; status.style.color = '#b45309'; } };
  try {
    let url = `/api/latest-user-db?folder=${encodeURIComponent(folder)}&user=${encodeURIComponent(user)}`;
    if (file) url += `&file=${encodeURIComponent(file)}`;
    if (subfolder) url += `&subfolder=${encodeURIComponent(subfolder)}`;
    const r = await fetch(url);
    if (!r.ok) { note(`Could not load ${user}'s latest file (dev server returned ${r.status}).`); return; }
    const j = await r.json();
    if (!j.ok || !j.found) { note(`No file found for "${user}" in "${folder}".`); return; }
    await loadSqliteIntoView(base64ToBytes(j.base64), j.filename, null);
  } catch (e) {
    note(`Could not reach the dev server to load ${user}'s file.`);
  }
}

function setupSqliteLoading(db) {
  const input = document.getElementById('sqlite-file-input');
  const chooseBtn = document.getElementById('choose-load-file');
  const status = document.getElementById('sqlite-status');
  if (!input || !chooseBtn || !status) {
    console.error('setupSqliteLoading: missing #sqlite-file-input, #choose-load-file, or #sqlite-status — file load is disabled. Hard-refresh if the button looks new but does nothing.');
    return;
  }

  // Auto-load as soon as a file is chosen via the (fallback / test) file input.
  input.addEventListener('change', async () => {
    const file = input.files && input.files[0];
    if (!file) return;
    const buf = await file.arrayBuffer();
    await loadSqliteIntoView(new Uint8Array(buf), file.name, null);
    input.value = '';   // allow re-choosing the same file
  });

  // "Refresh loaded file": re-read the file currently in view without re-picking it — handy
  // after the dev server writes to it (e.g. a generated list). Re-reads the File System Access
  // handle when we have one, else re-fetches the ?folder=&user= file from the dev server.
  const refreshBtn = document.getElementById('refresh-loaded-file');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      if (loadedFileHandle && loadedFileHandle.getFile) {
        try {
          const file = await loadedFileHandle.getFile();
          await loadSqliteIntoView(new Uint8Array(await file.arrayBuffer()), file.name, loadedFileHandle);
          return;
        } catch (e) { /* fall through to the dev-server / hint path */ }
      }
      const params = new URLSearchParams(window.location.search);
      if (params.get('folder') && params.get('user')) { await loadLatestForUrlParams(); return; }
      if (status) { status.textContent = 'No file to refresh yet — use "Choose and load file".'; status.style.color = '#b45309'; }
    });
  }

  // "Choose and load file": prefer the File System Access picker (gives a writable handle
  // for auto-save); fall back to the plain file input where it's unavailable or fails.
  chooseBtn.addEventListener('click', async () => {
    if (!window.showOpenFilePicker) {
      input.click();
      return;
    }
    try {
      const [handle] = await window.showOpenFilePicker({ types: SQLITE_PICKER_TYPES });
      const file = await handle.getFile();
      const buf = await file.arrayBuffer();
      await loadSqliteIntoView(new Uint8Array(buf), file.name, handle);
    } catch (e) {
      if (e && e.name === 'AbortError') return;   // user cancelled the picker
      console.warn('showOpenFilePicker failed, falling back to file input:', e);
      input.click();
    }
  });
}

// Wire the sequence stepper: the dual-range slider re-renders the visible window
// without rebuilding the population; category/ordering changes rebuild it.
function setupSequenceControls(db) {
  // Collapsible "Step through the session" box (folded by default; same header style as the editor).
  const seqWrap = document.getElementById('sequence-controls');
  const seqHeader = document.getElementById('seq-header');
  if (seqWrap && seqHeader) {
    const toggleSeq = () => {
      const open = seqWrap.classList.toggle('seq-open');
      seqHeader.setAttribute('aria-expanded', open ? 'true' : 'false');
    };
    seqHeader.addEventListener('click', toggleSeq);
    seqHeader.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleSeq(); } });
  }
  const startEl = document.getElementById('seq-start');
  const endEl = document.getElementById('seq-end');
  if (startEl && endEl) {
    const apply = (movingStart) => {
      let s = parseInt(startEl.value) || 0;
      let e = parseInt(endEl.value) || 0;
      if (movingStart && s > e) { s = e; startEl.value = String(s); }
      if (!movingStart && e < s) { e = s; endEl.value = String(e); }
      seqState.window.start = s;
      seqState.window.end = e;
      renderVisible();
    };
    startEl.addEventListener('input', () => apply(true));
    endEl.addEventListener('input', () => apply(false));
  }

  const ordering = document.getElementById('seq-ordering');
  if (ordering) ordering.addEventListener('change', () => refreshSequenceView());

  document.querySelectorAll('#seq-category-checkboxes input[type="checkbox"][data-cat]')
    .forEach((cb) => cb.addEventListener('change', () => refreshSequenceView()));

  const allBtn = document.getElementById('seq-cat-all');
  const noneBtn = document.getElementById('seq-cat-none');
  if (allBtn) allBtn.addEventListener('click', () => { setAllCategories(true); refreshSequenceView(); });
  if (noneBtn) noneBtn.addEventListener('click', () => { setAllCategories(false); refreshSequenceView(); });
}

function setAllCategories(checked) {
  document.querySelectorAll('#seq-category-checkboxes input[type="checkbox"][data-cat]')
    .forEach((cb) => { cb.checked = checked; });
}

// Add session management functionality (reusing functions from math_quiz.js)
// updateSessionCount is now in math_utils.js

// Start the analysis
document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM fully loaded and parsed');
  // Any initialization code that needs to run after the DOM is ready
});
