// Milestone Map (dependency-free)
// Reads milestones.md and renders a Minecraft-ish milestone grid + tooltip panel.
//
// How to edit milestones:
// - Open milestones.md
// - Change "Current Milestone:" to move the yellow highlight (AutoStatus: true).
// - Or set AutoStatus: false and set Status per milestone (done/current/next/locked).
//
// Running locally:
// - Use VS Code Live Server (or any local HTTP server). fetch() won't work on file://

const GRID_EL = document.getElementById('grid');
const TOOLTIP_EL = document.getElementById('tooltip');
const TT_TITLE = document.getElementById('tt-title');
const TT_XP_LINE = document.getElementById('tt-xp-line');
const TT_XP = document.getElementById('tt-xp');
const TT_OBJECTIVE = document.getElementById('tt-objective');
const TT_REWARDS = document.getElementById('tt-rewards');
const TT_NOTES = document.getElementById('tt-notes');
const TT_FOOTER = document.getElementById('tt-footer');

const PAGE_TITLE = document.getElementById('page-title');
const PAGE_SUBTITLE = document.getElementById('page-subtitle');
const GRID_TITLE = document.getElementById('grid-title');
const GRID_STATUS = document.getElementById('grid-status');

const RELOAD_BTN = document.getElementById('reload-btn');

let pinned = false;
let selectedBlockEl = null;

RELOAD_BTN.addEventListener('click', () => loadAndRender(true));
document.addEventListener('keydown', (e) => {
  if (e.key.toLowerCase() === 'r') loadAndRender(true);
  if (e.key === 'Escape') {
    pinned = false;
    if (selectedBlockEl) selectedBlockEl.classList.remove('selected');
    selectedBlockEl = null;
    setTooltip(null);
  }
});

function escapeHtml(s){
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

// Optional inline color tokens: "{gold}text"
function renderColoredLine(line){
  const m = line.match(/^\{(red|green|gold|aqua)\}(.*)$/i);
  if (!m) return `<span>${escapeHtml(line)}</span>`;
  const cls = `c-${m[1].toLowerCase()}`;
  return `<span class="${cls}">${escapeHtml(m[2].trim())}</span>`;
}

// Very small markdown-ish renderer for a *subset* we need in tooltips.
function renderSection(title, content){
  if (!content) return '';
  const safeTitle = escapeHtml(title);
  // content can be string or array
  if (Array.isArray(content)){
    const lis = content.map(li => `<li>${renderColoredLine(li)}</li>`).join('');
    return `<h3>${safeTitle}</h3><ul>${lis}</ul>`;
  }
  return `<h3>${safeTitle}</h3><div>${escapeHtml(content)}</div>`;
}

function formatNumber(n){
  if (n === null || n === undefined || n === '') return '';
  const num = Number(String(n).replaceAll(',', '').trim());
  if (Number.isFinite(num)) return num.toLocaleString();
  return String(n);
}

/**
 * Parse a constrained markdown file.
 *
 * Expected structure:
 * # Current Status
 * - Title: ...
 * - Subtitle: ...
 * - Grid: 9x6
 * - Current Milestone: 3
 * - AutoStatus: true
 *
 * # Levels
 * ## 1 — Name the Sheet
 * - Position: 1,1
 * - Status: done
 * - Required XP: 0
 * - Objective: ...
 * - Rewards:
 *   - {green}+1 Focus Token
 *   - ...
 * - Notes:
 *   - ...
 */
function parseMilestonesMarkdown(mdText){
  const lines = mdText.replaceAll('\r\n','\n').split('\n');
  const data = {
    meta: {},
    milestones: []
  };

  let section = null; // 'meta' | 'levels' | null
  let current = null;
  let pendingList = null; // {target:'meta'|'milestone', key:'Rewards'}

  function startList(target, key){
    pendingList = { target, key };
    if (target === 'meta'){
      if (!Array.isArray(data.meta[key])) data.meta[key] = [];
    } else if (current){
      if (!Array.isArray(current[key])) current[key] = [];
    }
  }

  function pushToList(value){
    if (!pendingList) return;
    const { target, key } = pendingList;
    if (target === 'meta'){
      data.meta[key].push(value);
    } else if (current){
      current[key].push(value);
    }
  }

  function stopList(){
    pendingList = null;
  }

  function parseKeyValue(line){
    // - Key: Value
    // - **Key:** Value
    const m = line.match(/^-+\s*(?:\*\*)?([^:*]+?)(?:\*\*)?\s*:\s*(.*)$/);
    if (!m) return null;
    return { key: m[1].trim(), value: m[2].trim() };
  }

  for (let i=0; i<lines.length; i++){
    const raw = lines[i];
    const line = raw.trimRight();

    // Section headers
    if (line.match(/^#\s+/)){
      stopList();
      const h = line.replace(/^#\s+/, '').trim().toLowerCase();
      if (h === 'current status') section = 'meta';
      else if (h === 'levels') section = 'levels';
      else section = null;
      continue;
    }

    // Milestone headers
    if (section === 'levels' && line.match(/^##\s+/)){
      stopList();
      const header = line.replace(/^##\s+/, '').trim();
      // Extract numeric id at the beginning if present
      const idMatch = header.match(/^(\d+)\s*(?:[-—:]\s*)?(.*)$/);
      const id = idMatch ? Number(idMatch[1]) : null;
      const title = idMatch ? idMatch[2].trim() : header;
      current = {
        id,
        title: title || `Milestone ${id ?? ''}`.trim(),
      };
      data.milestones.push(current);
      continue;
    }

    // List items inside a list block:
    if (pendingList && raw.match(/^\s{2,}-\s+/)){
      const item = raw.replace(/^\s{2,}-\s+/, '').trim();
      if (item) pushToList(item);
      continue;
    }

    // Blank line ends pending list
    if (pendingList && line.trim() === ''){
      stopList();
      continue;
    }

    // Key-values under meta or milestones
    if (section === 'meta' || section === 'levels'){
      const kv = parseKeyValue(line.trim());
      if (kv){
        stopList();
        const key = kv.key;
        const value = kv.value;

        const target = (section === 'meta') ? data.meta : current;
        if (!target) continue;

        if (value === ''){
          // Start a list
          startList(section === 'meta' ? 'meta' : 'milestone', key);
        } else {
          target[key] = value;
        }
      }
    }
  }

  // Normalize meta
  // Grid: 9x6
  if (typeof data.meta['Grid'] === 'string'){
    const m = data.meta['Grid'].toLowerCase().match(/(\d+)\s*[x×]\s*(\d+)/);
    if (m){
      data.meta._gridCols = Number(m[1]);
      data.meta._gridRows = Number(m[2]);
    }
  }
  data.meta._gridCols ||= 9;
  data.meta._gridRows ||= 6;

  // Current Milestone
  if (typeof data.meta['Current Milestone'] === 'string'){
    const cm = Number(data.meta['Current Milestone']);
    if (Number.isFinite(cm)) data.meta._current = cm;
  }

  // AutoStatus
  if (typeof data.meta['AutoStatus'] === 'string'){
    data.meta._autoStatus = ['true','yes','1','on'].includes(data.meta['AutoStatus'].toLowerCase());
  } else {
    data.meta._autoStatus = true;
  }

  // Normalize milestones
  for (const m of data.milestones){
    // Position "r,c"
    const posStr = m['Position'] || m['Pos'] || m['position'];
    if (typeof posStr === 'string'){
      const pm = posStr.match(/(\d+)\s*,\s*(\d+)/);
      if (pm){
        m._row = Number(pm[1]);
        m._col = Number(pm[2]);
      }
    }
    // Required XP
    if (typeof m['Required XP'] === 'string'){
      m._requiredXp = m['Required XP'];
    }

    // Status
    if (typeof m['Status'] === 'string'){
      m._status = m['Status'].trim().toLowerCase();
    }
  }

  return data;
}

function inferStatus(meta, milestone){
  // If explicitly set and AutoStatus off, keep it.
  if (!meta._autoStatus && milestone._status) return milestone._status;

  const cm = meta._current;
  if (!Number.isFinite(cm)){
    // fallback: if status exists use it, else locked
    return milestone._status || 'locked';
  }
  if (!Number.isFinite(milestone.id)) return 'locked';

  if (milestone.id < cm) return 'done';
  if (milestone.id === cm) return 'current';
  if (milestone.id === cm + 1) return 'next';
  return 'locked';
}

function statusFooter(status){
  switch(status){
    case 'locked':
      return `<span class="c-red">You can't claim this reward yet!</span>`;
    case 'done':
      return `<span class="c-green">Completed.</span>`;
    case 'current':
      return `<span class="c-gold">In progress…</span>`;
    case 'next':
      return `<span class="c-gold">Next up!</span>`;
    default:
      return '';
  }
}

function setTooltip(milestone){
  if (!milestone){
    TT_TITLE.textContent = 'Hover a milestone';
    TT_XP_LINE.style.display = 'none';
    TT_OBJECTIVE.innerHTML = '';
    TT_REWARDS.innerHTML = '';
    TT_NOTES.innerHTML = '';
    TT_FOOTER.innerHTML = '';
    return;
  }

  const status = milestone._renderStatus || milestone._status || 'locked';
  const title = milestone.id ? `Milestone ${milestone.id} — ${milestone.title}` : milestone.title;

  TT_TITLE.textContent = title;

  if (milestone._requiredXp){
    TT_XP.textContent = formatNumber(milestone._requiredXp);
    TT_XP_LINE.style.display = '';
  } else {
    TT_XP_LINE.style.display = 'none';
  }

  TT_OBJECTIVE.innerHTML = renderSection('Objective', milestone['Objective']);
  TT_REWARDS.innerHTML = renderSection('Rewards', milestone['Rewards']);
  TT_NOTES.innerHTML = renderSection('Notes', milestone['Notes']);

  TT_FOOTER.innerHTML = statusFooter(status);
}

function clearSelected(){
  if (selectedBlockEl) selectedBlockEl.classList.remove('selected');
  selectedBlockEl = null;
}

function selectBlock(el){
  clearSelected();
  selectedBlockEl = el;
  el.classList.add('selected');
}

// Define the path connections for Museum-style snake pattern
// Each entry: [fromMilestone, toMilestone, direction from 'from']
const PATH_CONNECTIONS = [
  [1, 2, 'up'],
  [2, 3, 'up'],
  [3, 4, 'right'],
  [4, 5, 'right'],
  [5, 6, 'down'],
  [6, 7, 'down'],
  [7, 8, 'down'],   // goes down-left
  [8, 9, 'right'],
  [9, 10, 'right'],
  [10, 11, 'up'],   // jumps up to next section
  [11, 12, 'up'],
  [12, 13, 'up'],
  [13, 14, 'right'],
  [14, 15, 'right'],
  [15, 16, 'down'],
  [16, 17, 'down'],
  [17, 18, 'down'],
  [18, 19, 'right'],
  [19, 20, 'right'],
  [20, 21, 'up'],
  [21, 22, 'up'],
  [22, 23, 'up'],
];

function buildGrid(meta, milestones){
  const cols = meta._gridCols || 9;
  const rows = meta._gridRows || 6;

  GRID_EL.innerHTML = '';
  GRID_EL.style.gridTemplateColumns = `repeat(${cols}, 56px)`;
  GRID_EL.style.gridTemplateRows = `repeat(${rows}, 56px)`;

  // Build a map of milestone id -> milestone for path lookup
  const milestoneById = new Map();
  for (const m of milestones) {
    if (m.id) milestoneById.set(m.id, m);
  }

  // Create slots first (background)
  const slots = new Map(); // key "r,c" -> slotEl
  for (let r=1; r<=rows; r++){
    for (let c=1; c<=cols; c++){
      const slot = document.createElement('div');
      slot.className = 'slot';
      slot.dataset.row = String(r);
      slot.dataset.col = String(c);
      const key = `${r},${c}`;
      slots.set(key, slot);
      GRID_EL.appendChild(slot);
    }
  }

  // Place milestones
  for (const m of milestones){
    if (!m._row || !m._col) continue;
    const key = `${m._row},${m._col}`;
    const slot = slots.get(key);
    if (!slot) continue;

    const status = inferStatus(meta, m);
    m._renderStatus = status;

    const block = document.createElement('button');
    block.className = `block status-${status}`;
    block.type = 'button';
    block.title = `Milestone ${m.id || ''}`.trim();
    block.setAttribute('aria-label', block.title);

    // Number (positioned in bottom-right via CSS)
    const num = document.createElement('span');
    num.className = 'num';
    num.textContent = m.id ? String(m.id) : '';
    block.appendChild(num);

    // Hover/focus updates tooltip unless pinned
    const show = () => {
      if (pinned) return;
      selectBlock(block);
      setTooltip(m);
    };

    block.addEventListener('mouseenter', show);
    block.addEventListener('focus', show);

    // Click pins/unpins tooltip (works for touch too)
    block.addEventListener('click', () => {
      const willPin = !(pinned && selectedBlockEl === block);
      pinned = willPin;
      selectBlock(block);
      setTooltip(m);
    });

    // Locked milestones still show tooltip; just disable "feel"
    if (status === 'locked'){
      block.classList.add('status-locked');
    }

    slot.appendChild(block);

    // Auto-select current milestone initially
    if (status === 'current' && !selectedBlockEl){
      selectBlock(block);
      setTooltip(m);
    }
  }

  // If nothing selected, show first milestone
  if (!selectedBlockEl && milestones.length){
    const first = milestones.find(m => m._row && m._col) || milestones[0];
    setTooltip(first || null);
  }
}

function updateHeader(meta, milestones){
  const title = meta['Title'] || 'Milestones';
  const subtitle = meta['Subtitle'] || '';
  PAGE_TITLE.textContent = title;
  PAGE_SUBTITLE.textContent = subtitle;

  GRID_TITLE.textContent = meta['Grid Title'] || 'Milestone Map';

  const cm = meta._current;
  if (Number.isFinite(cm)){
    GRID_STATUS.textContent = `Current: ${cm} / ${milestones.length}`;
  } else {
    GRID_STATUS.textContent = `${milestones.length} milestones`;
  }
}

// Calculate and fix the tooltip height based on the tallest milestone content
function fixTooltipHeight(meta, milestones){
  // Reset any previous fixed height
  TOOLTIP_EL.style.height = 'auto';
  TOOLTIP_EL.style.minHeight = 'auto';
  
  let maxHeight = 0;
  
  // Temporarily render each milestone and measure its height
  for (const m of milestones){
    // Set status for rendering
    m._renderStatus = inferStatus(meta, m);
    
    // Render this milestone's content
    setTooltip(m);
    
    // Measure the height
    const height = TOOLTIP_EL.scrollHeight;
    if (height > maxHeight){
      maxHeight = height;
    }
  }
  
  // Add a small buffer and set as fixed height
  if (maxHeight > 0){
    TOOLTIP_EL.style.height = `${maxHeight}px`;
    TOOLTIP_EL.style.minHeight = `${maxHeight}px`;
  }
}

async function loadAndRender(bustCache=false){
  try{
    pinned = false;
    clearSelected();

    const url = bustCache ? `milestones.md?v=${Date.now()}` : 'milestones.md';
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Could not load milestones.md (HTTP ${res.status}).`);
    const text = await res.text();

    const data = parseMilestonesMarkdown(text);
    updateHeader(data.meta, data.milestones);
    
    // Calculate and fix tooltip height before building grid
    fixTooltipHeight(data.meta, data.milestones);
    
    buildGrid(data.meta, data.milestones);

  }catch(err){
    console.error(err);
    TT_TITLE.textContent = 'Could not load milestones.md';
    TT_XP_LINE.style.display = 'none';
    TT_OBJECTIVE.innerHTML = `<div>${escapeHtml(String(err))}</div>`;
    TT_REWARDS.innerHTML = '';
    TT_NOTES.innerHTML = '';
    TT_FOOTER.innerHTML = `<span class="c-red">Tip: run with VS Code Live Server (fetch won't work on file://).</span>`;
  }
}

// Initial load
loadAndRender(false);
