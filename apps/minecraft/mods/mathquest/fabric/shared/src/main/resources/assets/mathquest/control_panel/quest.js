const questState = {
  status: null,
  dynamicCommandSuggestions: [],
  openCategoryDetails: new Set(),
};

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function refresh() {
  questState.status = await api('/api/quest/status');
  render();
}

function render() {
  const { quest, world, progress, onlinePlayers, paths } = questState.status;
  document.querySelector('#server-line').textContent =
    `${quest.active ? 'active' : 'inactive'} | ${paths.questConfig}`;
  renderRun(quest, progress, onlinePlayers);
  renderCommandRunner(quest);
  renderMilestones(quest, progress, world);
  renderCategories(progress);
  renderCues(quest);
  renderMechanics(quest);
}

function renderRun(quest, progress, players) {
  renderOnlinePlayers(players);
  const selectedOnline = document.querySelector('#online-player').value;
  const usingSelectedOnline = !quest.active && selectedOnline;
  let playerName = quest.learner.playerName || selectedOnline || 'WildPetal';
  if (usingSelectedOnline) playerName = selectedOnline;
  const storedRealName = quest.learner.realName || '';
  const realName = usingSelectedOnline ? realNameForPlayer(playerName) : (storedRealName || realNameForPlayer(playerName));
  document.querySelector('#learner-player').value = playerName;
  const realInput = document.querySelector('#learner-real');
  realInput.value = realName;
  realInput.dataset.auto = realName === realNameForPlayer(playerName) ? 'true' : 'false';
  document.querySelector('#try-number').value = quest.active ? (quest.tryNumber || 1) : (questState.status.nextTryNumber || 1);
  document.querySelector('#problems-per-quiz').value = quest.quiz.problemsPerQuiz || 7;
  document.querySelector('#green-ms').value = quest.quiz.fluencyMs || quest.quiz.greenMs || 2000;
  document.querySelector('#red-ms').value = quest.quiz.redMs || 7000;
  document.querySelector('#min-accuracy').value = quest.quiz.minAccuracy ?? 0.9;
  const backup = questState.status.latestBackup || {};
  const actionLog = (quest.actionLog || []).map(action => formatActionLogLine(action));
  const fallbackActionLines = (quest.lastActionResult || []).map(action => formatActionLogLine(action));
  const logLines = actionLog.length ? actionLog : fallbackActionLines;
  document.querySelector('#run-status').textContent = [
    `Run: ${quest.active ? 'active' : 'inactive'} | try ${quest.tryNumber || 0}`,
    `Current milestone: ${progress.currentMilestoneId}`,
    `Active SQLite: ${quest.activeSqlitePath || '(none)'}`,
    `Backup: ${backup.exists ? backup.path : '(none)'}`,
    `Setup versions: ${questState.status.paths.versionsDir}`,
    `Latest version: ${(questState.status.versions || [])[0]?.filename || '(none)'}`,
    ...logLines.slice(-30),
  ].join('\n');
}

function formatActionLogLine(action) {
  const stamp = action.time ? `${String(action.time).slice(11, 19)} ` : '';
  const source = action.source ? `[${action.source}] ` : '';
  const input = action.input ? ` | ${action.input}` : '';
  return `${stamp}${source}${action.ok ? 'ok' : 'fail'} ${action.type}: ${action.message}${input}`;
}

function renderCommandRunner(quest) {
  const list = document.querySelector('#command-suggestions');
  list.textContent = '';
  const suggestions = [...new Set([
    ...(questState.status.commandSuggestions || []),
    ...questState.dynamicCommandSuggestions,
  ])];
  for (const command of suggestions) {
    const opt = document.createElement('option');
    opt.value = command;
    list.append(opt);
  }
  const commandStatus = document.querySelector('#command-status');
  const commandResults = questState.status.commandResults || [];
  const result = questState.status.commandResult || questState.status.restoreResult;
  commandStatus.textContent = commandResults.length
    ? commandResults.map(formatActionLogLine).join('\n')
    : (result ? formatActionLogLine(result) : '');
}

function renderOnlinePlayers(players) {
  const select = document.querySelector('#online-player');
  const current = select.value;
  select.textContent = '';
  for (const player of players || []) {
    const opt = document.createElement('option');
    opt.value = player.playerName;
    opt.textContent = `${player.playerName} (${player.realName}) ${player.x}, ${player.y}, ${player.z}`;
    select.append(opt);
  }
  if (current) select.value = current;
  if (!select.value && select.options.length) {
    select.value = select.options[0].value;
  }
}

function realNameForPlayer(playerName) {
  const clean = String(playerName || '').trim();
  if (!clean) return '';
  const online = (questState.status?.onlinePlayers || []).find(p => p.playerName.toLowerCase() === clean.toLowerCase());
  if (online && online.realName) return online.realName;
  const mapped = questState.status?.playerRealNames?.[clean.toLowerCase()];
  return mapped || clean;
}

function setLearnerPlayer(playerName, realName = '') {
  const clean = String(playerName || '').trim();
  if (!clean) return;
  document.querySelector('#learner-player').value = clean;
  const realInput = document.querySelector('#learner-real');
  realInput.value = String(realName || realNameForPlayer(clean) || clean).trim();
  realInput.dataset.auto = 'true';
}

function maybeAutoFillRealName() {
  const playerName = document.querySelector('#learner-player').value.trim();
  if (!playerName) return;
  const realInput = document.querySelector('#learner-real');
  if (realInput.dataset.auto === 'false' && realInput.value.trim()) return;
  realInput.value = realNameForPlayer(playerName);
  realInput.dataset.auto = 'true';
}

function renderMilestones(quest, progress, world) {
  const wrap = document.querySelector('#milestones-list');
  wrap.textContent = '';
  const progressById = new Map((progress.milestones || []).map(m => [m.id, m]));
  for (const [index, m] of (quest.milestones || []).entries()) {
    const merged = progressById.get(m.id) || m;
    const loc = (world.locations || {})[m.id] || {};
    const card = document.createElement('article');
    card.className = `milestone-card ${merged.status || 'locked'}`;
    card.dataset.milestoneId = m.id;
    card.innerHTML = `
      <div class="quest-card-head">
        <span class="milestone-order">M${index + 1}</span>
        <input class="milestone-name" value="${escapeAttr(m.name || m.id)}">
        <select class="milestone-status">
          ${option('active', merged.status)}${option('locked', merged.status)}${option('completed', merged.status)}
        </select>
      </div>
      <div class="entry-grid">
        <label>Location name <input class="milestone-location-label" value="${escapeAttr(loc.label || m.name || m.id)}"></label>
        <label class="wide">Coordinates <input class="milestone-coords" value="${escapeAttr(coordsString(loc))}" placeholder="x y z"></label>
      </div>
      <label>Story text <textarea class="milestone-story">${escapeHtml(m.storyText || '')}</textarea></label>
      <label>Exit rule <input class="milestone-exit" value="${escapeAttr(m.exitRule || '')}"></label>
      <label>Audio path <input class="milestone-audio" value="${escapeAttr(m.audioPath || '')}"></label>
      <label>Music path <input class="milestone-music" value="${escapeAttr(m.musicPath || '')}"></label>
      <label>Start actions <textarea class="milestone-start-actions" placeholder="one action per line">${escapeHtml(actionText(m.startActions))}</textarea></label>
      <label>End actions <textarea class="milestone-end-actions" placeholder="one action per line">${escapeHtml(actionText(m.endActions))}</textarea></label>
    `;
    const setCurrent = document.createElement('button');
    setCurrent.textContent = 'Set Current';
    setCurrent.onclick = () => questAction('set-current-milestone', { milestoneId: m.id });
    const runStart = document.createElement('button');
    runStart.textContent = 'Run Start';
    runStart.onclick = () => questAction('run-milestone-actions', { milestoneId: m.id, phase: 'start' });
    const runEnd = document.createElement('button');
    runEnd.textContent = 'Run End';
    runEnd.onclick = () => questAction('run-milestone-actions', { milestoneId: m.id, phase: 'end' });
    const actions = document.createElement('div');
    actions.className = 'plan-actions';
    actions.append(setCurrent, runStart, runEnd);
    card.append(actions);
    wrap.append(card);
  }
}

function renderCategories(progress) {
  const wrap = document.querySelector('#category-list');
  wrap.textContent = '';
  for (const cat of progress.categories || []) {
    const row = document.createElement('div');
    row.className = 'quest-row compact';
    row.innerHTML = `
      <div class="quest-row-title">${escapeHtml(cat.name)}</div>
      <div>${cat.fluentCount}/${cat.canonicalCount} fluent</div>
      <div>${cat.attempts} attempts</div>
      <details data-category-id="${escapeAttr(cat.id || cat.name)}"><summary>Facts</summary><div class="fact-grid"></div></details>
    `;
    const details = row.querySelector('details');
    const categoryId = String(cat.id || cat.name);
    details.open = questState.openCategoryDetails.has(categoryId);
    details.addEventListener('toggle', () => {
      if (details.open) questState.openCategoryDetails.add(categoryId);
      else questState.openCategoryDetails.delete(categoryId);
    });
    const facts = row.querySelector('.fact-grid');
    for (const fact of cat.facts || []) {
      const item = document.createElement('div');
      item.className = fact.fluent ? 'fact fluent' : 'fact';
      const streak = fact.maxFastCorrectStreak ?? fact.fastCorrect ?? 0;
      item.textContent = `${fact.fact}: ${fact.fastCorrect} fast, ${streak} streak / ${fact.attempts}`;
      facts.append(item);
    }
    wrap.append(row);
  }
}

function renderCues(quest) {
  const wrap = document.querySelector('#cue-list');
  wrap.textContent = '';
  for (const cue of quest.contentCues || []) {
    const row = document.createElement('div');
    row.className = 'quest-row cue-row';
    row.dataset.cueId = cue.id;
    row.innerHTML = `
      <label>ID <input class="cue-id" value="${escapeAttr(cue.id || '')}"></label>
      <label>Delivery <input class="cue-delivery" value="${escapeAttr(cue.delivery || 'chat')}"></label>
      <label class="full">Text <textarea class="cue-text">${escapeHtml(cue.text || '')}</textarea></label>
      <label>Audio path <input class="cue-audio" value="${escapeAttr(cue.audioPath || '')}"></label>
      <label>Music path <input class="cue-music" value="${escapeAttr(cue.musicPath || '')}"></label>
    `;
    wrap.append(row);
  }
}

function renderMechanics(quest) {
  const wrap = document.querySelector('#mechanic-list');
  wrap.textContent = '';
  for (const mechanic of quest.mechanics || []) {
    const card = document.createElement('article');
    card.className = 'mechanic-card';
    card.dataset.mechanicId = mechanic.id;
    card.innerHTML = `
      <div class="quest-card-head">
        <input class="mechanic-label" value="${escapeAttr(mechanic.label || mechanic.id)}">
        <select class="mechanic-status">
          ${option('dormant', mechanic.status)}${option('ready', mechanic.status)}${option('quiz_opened_by_gm', mechanic.status)}${option('cleared', mechanic.status)}
        </select>
      </div>
      <div class="entry-grid">
        <label>ID <input class="mechanic-id" value="${escapeAttr(mechanic.id || '')}"></label>
        <label>Type <input class="mechanic-type" value="${escapeAttr(mechanic.type || 'combat_quiz_gate')}"></label>
        <label>Location <input class="mechanic-location" value="${escapeAttr(mechanic.locationId || '')}"></label>
        <label>Entity/block <input class="mechanic-entity" value="${escapeAttr(mechanic.entityOrBlock || '')}"></label>
        <label>Success mode <input class="mechanic-success" value="${escapeAttr(mechanic.successMode || 'mastery_loop')}"></label>
        <label>Respawn sec <input class="mechanic-respawn" type="number" min="0" value="${mechanic.respawnDelaySeconds ?? 45}"></label>
      </div>
    `;
    const actions = document.createElement('div');
    actions.className = 'plan-actions';
    actions.append(
      mechanicButton('Open Quiz', 'open-mechanic-quiz', mechanic.id),
      mechanicButton('Force Clear', 'force-complete-mechanic', mechanic.id),
      mechanicButton('Respawn', 'force-respawn-mechanic', mechanic.id),
    );
    card.append(actions);
    wrap.append(card);
  }
}

function mechanicButton(label, action, mechanicId) {
  const btn = document.createElement('button');
  btn.textContent = label;
  btn.onclick = () => questAction(action, { mechanicId });
  return btn;
}

function coordsString(loc) {
  if (!loc || loc.x === undefined || loc.y === undefined || loc.z === undefined) return '';
  return `${loc.x} ${loc.y} ${loc.z}`;
}

function actionText(lines) {
  return Array.isArray(lines) ? lines.join('\n') : '';
}

function parseActionLines(value) {
  return String(value || '').split(/\r?\n/).map(line => line.trim()).filter(Boolean);
}

function parseCoords(value) {
  const parts = String(value || '').trim().split(/\s+/).filter(Boolean);
  if (parts.length !== 3) return null;
  const nums = parts.map(Number);
  if (nums.some(n => !Number.isFinite(n))) return null;
  return { x: Math.round(nums[0]), y: Math.round(nums[1]), z: Math.round(nums[2]) };
}

function commitFromDom() {
  const quest = structuredClone(questState.status.quest);
  const world = structuredClone(questState.status.world);
  const playerName = document.querySelector('#learner-player').value.trim() || 'WildPetal';
  quest.learner.playerName = playerName;
  quest.learner.realName = document.querySelector('#learner-real').value.trim() || realNameForPlayer(playerName);
  quest.quiz.problemsPerQuiz = Number(document.querySelector('#problems-per-quiz').value || 7);
  quest.quiz.fluencyMs = Number(document.querySelector('#green-ms').value || 2000);
  quest.quiz.greenMs = quest.quiz.fluencyMs;
  quest.quiz.redMs = Number(document.querySelector('#red-ms').value || 7000);
  quest.quiz.minAccuracy = Number(document.querySelector('#min-accuracy').value || 0.9);

  world.locations = {};
  quest.milestones = [...document.querySelectorAll('.milestone-card')].map(card => {
    const id = card.dataset.milestoneId;
    const existing = questState.status.world?.locations?.[id] || {};
    const coords = parseCoords(card.querySelector('.milestone-coords').value);
    const loc = {
      label: card.querySelector('.milestone-location-label').value.trim(),
      dimension: existing.dimension || 'minecraft:overworld',
    };
    if (coords) Object.assign(loc, coords);
    world.locations[id] = loc;
    if (id === 'm1_cave_start' && coords) {
      world.spawn = { ...loc };
    }
    return {
      id,
      name: card.querySelector('.milestone-name').value.trim(),
      status: card.querySelector('.milestone-status').value,
      storyText: card.querySelector('.milestone-story').value.trim(),
      exitRule: card.querySelector('.milestone-exit').value.trim(),
      audioPath: card.querySelector('.milestone-audio').value.trim(),
      musicPath: card.querySelector('.milestone-music').value.trim(),
      startActions: parseActionLines(card.querySelector('.milestone-start-actions').value),
      endActions: parseActionLines(card.querySelector('.milestone-end-actions').value),
    };
  });
  quest.contentCues = [...document.querySelectorAll('.cue-row')].map(row => ({
    id: row.querySelector('.cue-id').value.trim(),
    delivery: row.querySelector('.cue-delivery').value.trim(),
    text: row.querySelector('.cue-text').value.trim(),
    audioPath: row.querySelector('.cue-audio').value.trim(),
    musicPath: row.querySelector('.cue-music').value.trim(),
  })).filter(cue => cue.id);
  quest.mechanics = [...document.querySelectorAll('.mechanic-card')].map(card => ({
    id: card.querySelector('.mechanic-id').value.trim(),
    label: card.querySelector('.mechanic-label').value.trim(),
    type: card.querySelector('.mechanic-type').value.trim(),
    locationId: card.querySelector('.mechanic-location').value.trim(),
    entityOrBlock: card.querySelector('.mechanic-entity').value.trim(),
    successMode: card.querySelector('.mechanic-success').value.trim(),
    status: card.querySelector('.mechanic-status').value,
    respawnDelaySeconds: Number(card.querySelector('.mechanic-respawn').value || 0),
  })).filter(m => m.id);
  return { quest, world };
}

async function saveAll() {
  const payload = commitFromDom();
  questState.status = await api('/api/quest/save', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  render();
}

async function startRun() {
  await saveAll();
  const playerName = document.querySelector('#learner-player').value.trim() || 'WildPetal';
  const body = {
    playerName,
    realName: document.querySelector('#learner-real').value.trim() || realNameForPlayer(playerName),
    tryNumber: Number(document.querySelector('#try-number').value || 1),
  };
  questState.status = await api('/api/quest/start', {
    method: 'POST',
    body: JSON.stringify(body),
  });
  render();
}

async function continueRun() {
  await questAction('continue-run');
}

async function runImmediateCommand() {
  const command = document.querySelector('#immediate-command').value.trim();
  if (!command) return;
  await questAction('run-command', { command });
}

async function updateCommandSuggestions() {
  const command = document.querySelector('#immediate-command').value.trim();
  try {
    const response = await api('/api/quest/command-suggestions', {
      method: 'POST',
      body: JSON.stringify({ command }),
    });
    questState.dynamicCommandSuggestions = response.suggestions || [];
    renderCommandRunner(questState.status.quest);
  } catch {
    questState.dynamicCommandSuggestions = [];
  }
}

function firstCommandSuggestion() {
  const current = document.querySelector('#immediate-command').value.trim();
  const suggestions = [...new Set([
    ...(questState.dynamicCommandSuggestions || []),
    ...(questState.status?.commandSuggestions || []),
  ])];
  return suggestions.find(value => value && value !== current) || '';
}

async function restorePlayer() {
  await questAction('restore-player');
}

async function questAction(action, extra = {}) {
  await saveAll();
  questState.status = await api('/api/quest/action', {
    method: 'POST',
    body: JSON.stringify({ action, ...extra }),
  });
  render();
}

async function saveVersion() {
  await saveAll();
  const label = window.prompt('Version label', 'setup') || 'setup';
  questState.status = await api('/api/quest/action', {
    method: 'POST',
    body: JSON.stringify({ action: 'save-version', label }),
  });
  render();
}

async function openQuestQuiz() {
  await questAction('run-command', { command: 'start_quiz' });
}

function addCue() {
  questState.status.quest.contentCues.push({
    id: `cue_${Date.now()}`,
    delivery: 'chat',
    text: '',
    audioPath: '',
    musicPath: '',
  });
  renderCues(questState.status.quest);
}

function addMechanic() {
  questState.status.quest.mechanics.push({
    id: `mechanic_${Date.now()}`,
    label: 'New Mechanic',
    type: 'explore_button_gate',
    locationId: 'm1_cave_start',
    entityOrBlock: 'minecraft:stone_button',
    successMode: 'mastery_loop',
    status: 'dormant',
    respawnDelaySeconds: 45,
  });
  renderMechanics(questState.status.quest);
}

function option(value, selected) {
  return `<option value="${value}" ${value === selected ? 'selected' : ''}>${value.replaceAll('_', ' ')}</option>`;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[ch]));
}

function escapeAttr(value) {
  return escapeHtml(value);
}

document.querySelector('#refresh').onclick = refresh;
document.querySelector('#save-all').onclick = saveAll;
document.querySelector('#save-version').onclick = saveVersion;
document.querySelector('#continue-run').onclick = continueRun;
document.querySelector('#start-run').onclick = startRun;
document.querySelector('#reset-run').onclick = () => questAction('reset');
document.querySelector('#clear-run-log').onclick = () => questAction('clear-log');
document.querySelector('#restore-player').onclick = restorePlayer;
document.querySelector('#run-command').onclick = runImmediateCommand;
document.querySelector('#advance-milestone').onclick = () => questAction('advance-milestone');
document.querySelector('#open-quiz').onclick = openQuestQuiz;
document.querySelector('#add-cue').onclick = addCue;
document.querySelector('#add-mechanic').onclick = addMechanic;
document.querySelector('#learner-player').onchange = maybeAutoFillRealName;
document.querySelector('#learner-real').oninput = () => {
  document.querySelector('#learner-real').dataset.auto = 'false';
};
document.querySelector('#online-player').onchange = () => {
  const selected = document.querySelector('#online-player').value;
  const player = (questState.status?.onlinePlayers || []).find(p => p.playerName === selected);
  if (player) setLearnerPlayer(player.playerName, player.realName);
};
document.querySelector('#immediate-command').addEventListener('keydown', event => {
  if (event.key === 'Enter') runImmediateCommand();
  if (event.key === 'Tab') {
    const suggestion = firstCommandSuggestion();
    if (suggestion) {
      event.preventDefault();
      document.querySelector('#immediate-command').value = suggestion;
      updateCommandSuggestions();
    }
  }
});
document.querySelector('#immediate-command').addEventListener('input', updateCommandSuggestions);
for (const btn of document.querySelectorAll('.command-preset')) {
  btn.addEventListener('click', () => {
    document.querySelector('#immediate-command').value = btn.dataset.command || '';
    updateCommandSuggestions();
  });
}

refresh().catch(err => {
  document.querySelector('#server-line').textContent = `Error: ${err.message}`;
});

setInterval(() => {
  if (document.hidden) return;
  const tag = document.activeElement?.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
  refresh().catch(() => {});
}, 4000);
