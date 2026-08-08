// Game Master dashboard: the parent's phone view of the dragon game. Polls the
// dev server for the game's state snapshot + message history, and sends letters
// that show up in the game's story overlay after the child's next quiz.
// Open (same Wi-Fi): http://<laptop-lan-ip>:8907/dragon/gm.html
import { formatDragonName } from './sim/story.js';
import { ZOOMIE_BANDS, ZOOMIE_INTERVAL_S, zoomieBandFor } from './sim/zoomies.js';
import {
  GROWTH_SPURT_BANDS, growthSpurtBandFor, growthSpurtPhaseActive, zoomiesPhaseActive,
} from './sim/growth_spurt.js';
import { loadDisplayNames, displayName } from './display_names.js';

const qs = new URLSearchParams(window.location.search);
const FOLDER = qs.get('folder') || 'tlkids';
const USER = qs.get('user') || 'Kid1';
const POLL_MS = 5000;
let learnerLabel = USER;

// Parent-facing milestone names (the kid-facing ladder hides the 100% surprise).
const MILESTONE_LABELS = {
  hatch: 'Hatch (60%)', wings: 'Juvenile dragon (70%)', jump: 'Grown-up dragon (80%)',
  fire: 'Fire Breath (90%)', 'flight-ride': 'Flight + the Ride (100% — the surprise)',
};
const ROAD_STOPS = [
  { key: 'nest', icon: '🥚', label: 'Nest', done: (s) => !!s.eggFound },
  { key: 'hatched', icon: '🐣', label: 'Hatched', done: (s) => !!s.hatched },
  { key: 'meadow', icon: '🦋', label: 'Meadow', done: (s) => s.visitedStones.includes('meadow') },
  { key: 'hills', icon: '⛰️', label: 'Hills', done: (s) => s.visitedStones.includes('hills') },
  { key: 'grove', icon: '🔥', label: 'Grove', done: (s) => s.visitedStones.includes('grove') },
  { key: 'ride', icon: '🐉', label: 'The Ride', done: (s) => !!s.rideUnlocked },
];
const QUICK_PHRASES = [
  'I am SO proud of you! 💜',
  'Your dragon is lucky to have you!',
  'One more quiz and then snack time?',
  'Mama Dragon told me you are doing great!',
  'Wow — look at that progress bar go!',
];
const ZOOMIE_BAND_KEYS = Object.keys(ZOOMIE_BANDS).map(Number).sort((a, b) => a - b);
const GROWTH_SPURT_BAND_KEYS = Object.keys(GROWTH_SPURT_BANDS).map(Number).sort((a, b) => a - b);
const DIALOGUE_MODULE_IDS = new Set(['growth-spurt', 'zoomies']);
const REVEAL_STORAGE_KEY = 'gm-reveal-dialogue';
const moduleNodes = new Map();
let latestState = null;
const MODULES = [
  {
    id: 'growth-spurt',
    icon: '📏',
    title: 'Growth Spurt',
    description: 'From 91% to 100%: every fluency point makes Pipa 50% bigger than her grown-up size (91% = 1.5×, 100% = 6×). Each finished quiz shows one funny growth letter from the band below — cycling if she stays at the same percent. The zoomies are over; this is the BIG growth phase before the flight surprise.',
    renderStatus: renderGrowthSpurtStatus,
    renderEditor: renderGrowthSpurtEditor,
  },
  {
    id: 'zoomies',
    icon: '🌀',
    title: 'Zoomies',
    description: `From 80% to 90%: every ${ZOOMIE_INTERVAL_S} seconds of calm play Pipa gets a zoomie — she darts around the world in straight lines at twice your speed. Catch up to her (or wait 20 seconds) and she settles into a spinning tornado; click her and FINISH a quiz to calm her. Each calmed zoomie shows one of the messages below — 3+ per fluency percent, cycling if she stays at the same percent. A one-time Mama Dragon letter introduces it; at 90% the fire milestone ends the zoomies with a graduation speech.`,
    renderStatus: renderZoomiesStatus,
    renderEditor: renderZoomieEditor,
  },
  {
    id: 'lava',
    icon: '🔥',
    title: 'Lava defense',
    description: 'Mount Ember erupts on a login; five lava streams race for the nest, each cooled by a finished quiz.',
    renderStatus: renderLavaStatus,
  },
  {
    id: 'volcano',
    icon: '🌋',
    title: 'Mount Ember climb',
    description: 'Five boulders block the volcano road; a quiz smashes each, summit celebration at the top.',
    renderStatus: renderVolcanoStatus,
  },
  {
    id: 'stations',
    icon: '🪧',
    title: 'Nest projects',
    description: 'Two writable signs plus fountain/nest/trees that grow one level per finished quiz.',
    renderStatus: renderStationsStatus,
  },
];

const $ = (id) => document.getElementById(id);
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}
function row(label, value) {
  const div = el('div', 'row');
  div.appendChild(el('span', 'k', label));
  div.appendChild(el('span', null, value));
  return div;
}
function yesNo(value) { return value ? 'yes' : 'no'; }
function fmtWhen(iso) {
  if (!iso) return '–';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const mins = Math.round((Date.now() - d.getTime()) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  if (mins < 60 * 24) return `${Math.round(mins / 60)} h ago`;
  return d.toLocaleDateString();
}

async function fetchJson(url, options) {
  const r = await fetch(url, options);
  return r.json();
}
function renderState(out) {
  const fresh = $('freshness');
  if (!out.found) {
    fresh.textContent = 'game not seen yet';
    $('objective').textContent = `Waiting for ${learnerLabel}'s game to check in — start the dragon game once and this page comes alive.`;
    renderModules(null);
    return;
  }
  const s = out.state || {};
  latestState = s;
  fresh.textContent = `updated ${fmtWhen(out.updatedAt)}`;
  const dragonName = formatDragonName(s.dragonName);
  $('page-title').textContent = `🐉 ${dragonName ? `${dragonName} — ` : ''}${learnerLabel}'s Game Master`;
  $('pct').textContent = s.pct != null ? s.pct : '–';
  $('pct-bar').style.width = `${Math.max(0, Math.min(100, s.pct || 0))}%`;
  $('max-pct').textContent = `${s.maxPct != null ? s.maxPct : '–'} %`;
  $('next-milestone').textContent = s.nextMilestone
    ? (MILESTONE_LABELS[s.nextMilestone.id] || `${s.nextMilestone.title} (${s.nextMilestone.pct}%)`)
    : 'All done! 🎉';
  $('seg').textContent = s.segmentFrac != null ? `${Math.round(s.segmentFrac * 100)} %` : '–';
  $('bursts').textContent = s.totalBursts != null ? s.totalBursts : '–';
  $('last-played').textContent = fmtWhen(s.lastPlayedISO);
  $('objective').textContent = s.objective ? `★ ${s.objective.text}` : '–';
  $('phase').textContent = s.phaseTitle || s.phase || '–';
  $('scrolls').textContent = s.scrollsCollected != null ? `${s.scrollsCollected} 📜` : '–';
  const road = $('road');
  road.innerHTML = '';
  for (const stop of ROAD_STOPS) {
    const div = el('div', `stop${stop.done(Object.assign({ visitedStones: [] }, s)) ? ' done' : ''}`);
    div.appendChild(el('span', null, stop.icon));
    div.appendChild(el('span', 'lbl', stop.label));
    road.appendChild(div);
  }
  const feed = $('feed');
  feed.innerHTML = '';
  const bursts = (s.recentBursts || []).slice().reverse();
  if (!bursts.length) {
    feed.appendChild(el('div', 'empty', 'No quizzes yet.'));
  }
  for (const b of bursts) {
    const item = el('div', 'feed-item');
    item.appendChild(el('span', 'when', fmtWhen(b.ts)));
    const gain = (b.pctAfter || 0) - (b.pctBefore || 0);
    item.appendChild(el('span', null,
      `Quiz: ${b.correct}/${b.total} correct · ${b.pctBefore}% → ${b.pctAfter}%${gain > 0 ? ' 📈' : ''}`));
    feed.appendChild(item);
  }
  const celebrated = (s.celebratedIds || []).filter((id) => id !== 'egg-found');
  if (celebrated.length) {
    const item = el('div', 'feed-item milestone');
    item.appendChild(el('span', null, `Milestones: ${celebrated.map((id) => MILESTONE_LABELS[id] || id).join(' · ')}`));
    feed.appendChild(item);
  }
  renderModules(s);
}
function renderMessages(out) {
  const list = $('msg-list');
  list.innerHTML = '';
  const messages = (out.messages || []).slice().reverse();
  if (!messages.length) {
    list.appendChild(el('div', 'empty', 'No letters yet — send the first one!'));
    return;
  }
  for (const m of messages) {
    const div = el('div', `msg${m.read ? '' : ' unread'}`);
    div.appendChild(el('div', null, m.text));
    div.appendChild(el('div', 'meta', `${m.from} · ${fmtWhen(m.ts)} · ${m.read ? 'read in game ✓' : 'waiting to be read…'}`));
    list.appendChild(div);
  }
}
function activeDialogueModuleId(state) {
  if (!state) return null;
  if (growthSpurtPhaseActive(state)) return 'growth-spurt';
  if (zoomiesPhaseActive(state)) return 'zoomies';
  return null;
}
function getRevealDialogueId() {
  try { return sessionStorage.getItem(REVEAL_STORAGE_KEY) || ''; } catch { return ''; }
}
function setRevealDialogueId(id) {
  try {
    if (id) sessionStorage.setItem(REVEAL_STORAGE_KEY, id);
    else sessionStorage.removeItem(REVEAL_STORAGE_KEY);
  } catch { /* ignore */ }
}
function updateDialogueModuleVisibility(state) {
  const active = activeDialogueModuleId(state);
  const reveal = getRevealDialogueId();
  for (const id of DIALOGUE_MODULE_IDS) {
    const wrap = document.querySelector(`[data-module-id="${id}"]`);
    if (!wrap) continue;
    wrap.style.display = (id === active || id === reveal) ? '' : 'none';
  }
  const btn = $('dialogue-reveal-btn');
  if (!btn) return;
  if (!active) {
    btn.style.display = 'none';
    return;
  }
  btn.style.display = '';
  const other = active === 'growth-spurt' ? 'zoomies' : 'growth-spurt';
  const otherLabel = other === 'zoomies' ? 'Zoomies' : 'Growth Spurt';
  btn.textContent = reveal === other ? `Hide ${otherLabel} messages` : `Show finished ${otherLabel} messages`;
}
function buildModuleShells() {
  const root = $('modules');
  if (!root || moduleNodes.size) return;
  root.innerHTML = '';
  const revealRow = el('div', 'dialogue-reveal-row');
  const revealBtn = el('button', 'dialogue-reveal-btn', 'Show finished Zoomies messages');
  revealBtn.type = 'button';
  revealBtn.id = 'dialogue-reveal-btn';
  revealBtn.style.display = 'none';
  revealBtn.addEventListener('click', () => {
    const active = activeDialogueModuleId(latestState);
    const reveal = getRevealDialogueId();
    const other = active === 'growth-spurt' ? 'zoomies' : 'growth-spurt';
    setRevealDialogueId(reveal === other ? '' : other);
    updateDialogueModuleVisibility(latestState);
  });
  revealRow.appendChild(revealBtn);
  root.appendChild(revealRow);
  for (const mod of MODULES) {
    const wrap = el('div', 'module');
    wrap.dataset.moduleId = mod.id;
    if (DIALOGUE_MODULE_IDS.has(mod.id)) wrap.dataset.dialogueModule = '1';
    const title = el('div', 'mod-title');
    title.appendChild(el('span', 'mod-icon', mod.icon));
    title.appendChild(el('span', null, mod.title));
    wrap.appendChild(title);
    wrap.appendChild(el('div', 'mod-desc', mod.description));
    const status = el('div', 'mod-status');
    const editor = el('div', 'mod-editor');
    wrap.appendChild(status);
    wrap.appendChild(editor);
    root.appendChild(wrap);
    moduleNodes.set(mod.id, { status, editor });
    if (mod.renderEditor) mod.renderEditor(editor);
  }
  updateDialogueModuleVisibility(latestState);
}
function renderModules(state) {
  latestState = state;
  if (!moduleNodes.size) return;
  for (const mod of MODULES) {
    const nodes = moduleNodes.get(mod.id);
    nodes.status.innerHTML = '';
    mod.renderStatus(state, nodes.status);
  }
  updateDialogueModuleVisibility(state);
}
function updateZoomieBandMarkers(state) {
  const band = state && state.pct != null ? String(zoomieBandFor(state.pct)) : '';
  document.querySelectorAll('[data-zoomie-band]').forEach((node) => {
    node.classList.toggle('current', node.dataset.zoomieBand === band);
  });
}
function updateGrowthSpurtBandMarkers(state) {
  const band = state && state.pct != null ? String(growthSpurtBandFor(state.pct)) : '';
  document.querySelectorAll('[data-growth-band]').forEach((node) => {
    node.classList.toggle('current', node.dataset.growthBand === band);
  });
}
function renderGrowthSpurtStatus(s, container) {
  if (!s) {
    container.appendChild(el('div', 'empty', 'Waiting for the game to check in.'));
    updateGrowthSpurtBandMarkers(null);
    return;
  }
  const celebrated = new Set(s.celebratedIds || []);
  const active = celebrated.has('fire');
  const status = active ? 'Active — she\'s growing!' : 'Starts at 91% (after fire breath at 90%)';
  const g = s.growthSpurt || {};
  container.appendChild(row('Status', status));
  container.appendChild(row('Current message band', s.pct != null ? `${growthSpurtBandFor(s.pct)}%` : '–'));
  container.appendChild(row('Growth letters shown', g.shown != null ? g.shown : 0));
  updateGrowthSpurtBandMarkers(s);
}
async function renderGrowthSpurtEditor(container, initialBands = null, message = '') {
  container.innerHTML = '';
  let bands = initialBands;
  let loadError = '';
  if (bands == null) {
    container.appendChild(el('div', 'empty', 'Loading growth spurt messages…'));
    try {
      const out = await fetchJson(`/api/dragon-growth-spurt?folder=${encodeURIComponent(FOLDER)}&user=${encodeURIComponent(USER)}`);
      bands = (out && out.ok && out.bands) || {};
    } catch {
      bands = {};
      loadError = 'Could not load saved edits — showing original lines.';
    }
    container.innerHTML = '';
  }
  bands = bands && typeof bands === 'object' ? bands : {};
  for (const band of GROWTH_SPURT_BAND_KEYS) {
    const bandEl = el('div', 'zoomie-band');
    bandEl.dataset.growthBand = String(band);
    const title = el('div', 'zoomie-band-title');
    title.appendChild(el('span', null, `${band}%`));
    title.appendChild(el('span', 'current-band', "← she's here"));
    bandEl.appendChild(title);
    const linesBox = el('div', 'zoomie-lines');
    const override = Array.isArray(bands[String(band)]) && bands[String(band)].length ? bands[String(band)] : null;
    for (const line of override || GROWTH_SPURT_BANDS[band]) appendZoomieLine(linesBox, line);
    bandEl.appendChild(linesBox);
    const add = el('button', 'mod-add', '+ Add message');
    add.type = 'button';
    add.addEventListener('click', () => appendZoomieLine(linesBox).focus());
    bandEl.appendChild(add);
    container.appendChild(bandEl);
  }
  container.appendChild(el('div', 'mod-hint', "Empty a band to restore Pipa's original lines."));
  const save = el('button', 'mod-save', 'Save all growth spurt messages 💾');
  save.type = 'button';
  container.appendChild(save);
  const saveStatus = el('div', 'mod-save-status', message || loadError);
  container.appendChild(saveStatus);
  save.addEventListener('click', async () => {
    const payloadBands = {};
    container.querySelectorAll('[data-growth-band]').forEach((bandEl) => {
      const lines = Array.from(bandEl.querySelectorAll('textarea')).map((ta) => ta.value.trim()).filter(Boolean);
      if (lines.length) payloadBands[bandEl.dataset.growthBand] = lines;
    });
    save.disabled = true;
    saveStatus.textContent = 'Saving…';
    try {
      const out = await fetchJson('/api/dragon-growth-spurt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder: FOLDER, user: USER, bands: payloadBands }),
      });
      if (out && out.ok) {
        await renderGrowthSpurtEditor(container, out.bands || {}, 'Saved ✓');
      } else {
        saveStatus.textContent = `Save failed: ${(out && out.error) || 'server error'}`;
        save.disabled = false;
      }
    } catch {
      saveStatus.textContent = 'Save failed — server unreachable.';
      save.disabled = false;
    }
  });
  updateGrowthSpurtBandMarkers(latestState);
}
function renderZoomiesStatus(s, container) {
  if (!s) {
    container.appendChild(el('div', 'empty', 'Waiting for the game to check in.'));
    updateZoomieBandMarkers(null);
    return;
  }
  const celebrated = new Set(s.celebratedIds || []);
  const active = celebrated.has('jump') && !celebrated.has('fire');
  const status = active ? 'Active' : celebrated.has('fire') ? 'Finished — she grew up 🔥' : 'Starts at 80%';
  const z = s.zoomies || {};
  container.appendChild(row('Status', status));
  container.appendChild(row('Current message band', s.pct != null ? `${zoomieBandFor(s.pct)}%` : '–'));
  container.appendChild(row('Zoomies calmed', z.calmed != null ? z.calmed : 0));
  container.appendChild(row('Zoomies so far', z.alerts != null ? z.alerts : 0));
  container.appendChild(row('Intro letter shown', yesNo(z.intro)));
  container.appendChild(row('Graduated', yesNo(z.graduated)));
  updateZoomieBandMarkers(s);
}
function appendZoomieLine(parent, text = '') {
  const ta = el('textarea');
  ta.maxLength = 400;
  ta.value = text;
  parent.appendChild(ta);
  return ta;
}
async function renderZoomieEditor(container, initialBands = null, message = '') {
  container.innerHTML = '';
  let bands = initialBands;
  let loadError = '';
  if (bands == null) {
    container.appendChild(el('div', 'empty', 'Loading zoomie messages…'));
    try {
      const out = await fetchJson(`/api/dragon-zoomies?folder=${encodeURIComponent(FOLDER)}&user=${encodeURIComponent(USER)}`);
      bands = (out && out.ok && out.bands) || {};
    } catch {
      bands = {};
      loadError = 'Could not load saved edits — showing original lines.';
    }
    container.innerHTML = '';
  }
  bands = bands && typeof bands === 'object' ? bands : {};
  for (const band of ZOOMIE_BAND_KEYS) {
    const bandEl = el('div', 'zoomie-band');
    bandEl.dataset.zoomieBand = String(band);
    const title = el('div', 'zoomie-band-title');
    title.appendChild(el('span', null, `${band}%`));
    title.appendChild(el('span', 'current-band', "← she's here"));
    bandEl.appendChild(title);
    const linesBox = el('div', 'zoomie-lines');
    const override = Array.isArray(bands[String(band)]) && bands[String(band)].length ? bands[String(band)] : null;
    for (const line of override || ZOOMIE_BANDS[band]) appendZoomieLine(linesBox, line);
    bandEl.appendChild(linesBox);
    const add = el('button', 'mod-add', '+ Add message');
    add.type = 'button';
    add.addEventListener('click', () => appendZoomieLine(linesBox).focus());
    bandEl.appendChild(add);
    container.appendChild(bandEl);
  }
  container.appendChild(el('div', 'mod-hint', "Empty a band to restore Pipa's original lines."));
  const save = el('button', 'mod-save', 'Save all zoomie messages 💾');
  save.type = 'button';
  container.appendChild(save);
  const saveStatus = el('div', 'mod-save-status', message || loadError);
  container.appendChild(saveStatus);
  save.addEventListener('click', async () => {
    const payloadBands = {};
    container.querySelectorAll('.zoomie-band').forEach((bandEl) => {
      const lines = Array.from(bandEl.querySelectorAll('textarea')).map((ta) => ta.value.trim()).filter(Boolean);
      if (lines.length) payloadBands[bandEl.dataset.zoomieBand] = lines;
    });
    save.disabled = true;
    saveStatus.textContent = 'Saving…';
    try {
      const out = await fetchJson('/api/dragon-zoomies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder: FOLDER, user: USER, bands: payloadBands }),
      });
      if (out && out.ok) {
        await renderZoomieEditor(container, out.bands || {}, 'Saved ✓');
      } else {
        saveStatus.textContent = `Save failed: ${(out && out.error) || 'server error'}`;
        save.disabled = false;
      }
    } catch {
      saveStatus.textContent = 'Save failed — server unreachable.';
      save.disabled = false;
    }
  });
  updateZoomieBandMarkers(latestState);
}
function renderLavaStatus(s, container) {
  if (!s) {
    container.appendChild(el('div', 'empty', 'Waiting for the game to check in.'));
    return;
  }
  const lava = s.lava || {};
  if (!lava.intro) {
    container.appendChild(el('div', 'empty', 'Not started yet.'));
    return;
  }
  container.appendChild(row('Streams cooled', `${(lava.stopped || []).length}/5`));
  container.appendChild(row('Won', yesNo(lava.won)));
}
function renderVolcanoStatus(s, container) {
  if (!s) {
    container.appendChild(el('div', 'empty', 'Waiting for the game to check in.'));
    return;
  }
  const volcano = s.volcano || {};
  if (!volcano.intro) {
    container.appendChild(el('div', 'empty', 'Not started yet.'));
    return;
  }
  container.appendChild(row('Boulders smashed', `${volcano.cleared || 0}/5`));
  container.appendChild(row('Summited', yesNo(volcano.summited)));
}
function renderStationsStatus(s, container) {
  if (!s) {
    container.appendChild(el('div', 'empty', 'Waiting for the game to check in.'));
    return;
  }
  if (!s.stations) {
    container.appendChild(el('div', 'empty', 'Not started yet.'));
    return;
  }
  const signs = s.stations.signs || {};
  const levels = s.stations.levels || {};
  container.appendChild(row('Meadow sign', signs['sign-welcome'] || 'blank'));
  container.appendChild(row('Dragon sign', signs['sign-dragon'] || 'blank'));
  container.appendChild(row('Fountain', `${levels.fountain || 0}/3`));
  container.appendChild(row('Nest', `${levels.nest || 0}/3`));
  container.appendChild(row('Trees', `${levels.trees || 0}/3`));
}
async function poll() {
  try {
    const [stateOut, msgOut] = await Promise.all([
      fetchJson(`/api/dragon-state?folder=${encodeURIComponent(FOLDER)}&user=${encodeURIComponent(USER)}`),
      fetchJson(`/api/dragon-messages?folder=${encodeURIComponent(FOLDER)}&user=${encodeURIComponent(USER)}`),
    ]);
    if (stateOut && stateOut.ok) renderState(stateOut);
    if (msgOut && msgOut.ok) renderMessages(msgOut);
    $('status-line').textContent = `Watching ${learnerLabel} (${FOLDER}) · refreshes every ${POLL_MS / 1000}s`;
  } catch {
    $('freshness').textContent = 'server unreachable';
    $('status-line').textContent = 'Is the dev server running? python3 tools/dev_server.py';
  }
}
async function sendMessage() {
  const text = $('msg-text').value.trim();
  if (!text) return;
  const btn = $('msg-send');
  btn.disabled = true;
  try {
    const out = await fetchJson('/api/dragon-messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder: FOLDER, user: USER, action: 'send', text, from: $('msg-from').value.trim() }),
    });
    if (out && out.ok) {
      $('msg-text').value = '';
      await poll();
    } else {
      $('status-line').textContent = `Send failed: ${(out && out.error) || 'server error'}`;
    }
  } catch {
    $('status-line').textContent = 'Send failed — server unreachable.';
  } finally {
    btn.disabled = false;
  }
}
for (const phrase of QUICK_PHRASES) {
  const b = el('button', null, phrase);
  b.addEventListener('click', () => { $('msg-text').value = phrase; });
  $('quick-phrases').appendChild(b);
}
$('msg-send').addEventListener('click', sendMessage);
loadDisplayNames().then((names) => {
  learnerLabel = displayName(USER, names);
  buildModuleShells();
  poll();
  setInterval(poll, POLL_MS);
});
