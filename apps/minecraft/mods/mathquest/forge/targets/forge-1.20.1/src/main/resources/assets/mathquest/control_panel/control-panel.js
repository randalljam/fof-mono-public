const state = {
  status: null,
  selectedPlayers: JSON.parse(localStorage.getItem('mq.selectedPlayers') || '[]'),
  galleryOpen: false,
  rewardGroupsOpen: false,
  rewardGroupsDirty: false,
  lastMobSpawns: {},
  globalDirty: false,
  globalSaveTimer: null,
  rewardGroupsSaveTimer: null,
  playerDirty: new Set(),
  playerSaveTimers: {},
  playersMounted: false,
};
const defaults = ['rjcomp', 'treasurehunterm', 'pumajockey', 'wildpetal'];
async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}
async function refresh() {
  try {
    state.status = await api('/api/status');
    render();
  } catch (err) {
    document.querySelector('#server-line').textContent = `Disconnected: ${err.message}`;
  }
}
function render(options = {}) {
  const s = state.status;
  setupItemAutocomplete();
  setupRewardItemAutocomplete();
  setupMobAutocomplete();
  document.querySelector('#server-line').textContent =
    `${s.onlinePlayers.length} online | ${s.config.controlPanelUrl}`;
  renderGlobalControls();
  if (options.forcePlayers || !state.playersMounted) {
    renderPlayers(true);
  } else if (canRebuildPlayerCards()) {
    renderPlayers(false);
  } else {
    updatePlayerLiveFields();
  }
  if (!galleryEditorHasFocus()) renderGallery();
  if (!rewardGroupsEditorHasFocus() && !state.rewardGroupsDirty) renderRewardGroups();
}
function renderGlobalControls() {
  if (globalEditorHasFocus() || state.globalDirty) return;
  const s = state.status;
  document.querySelector('#quiz-mode').value = s.config.quizMode;
  document.querySelector('#allow-multiple').checked = s.config.npcAllowMultipleNerds;
  document.querySelector('#despawn-seconds').value = s.config.npcDespawnSeconds;
  document.querySelector('#evaluator-code').value = s.config.writtenColumnEvaluatorCode || 'paper';
}
function canRebuildPlayerCards() {
  return !playerEditorHasFocus() && state.playerDirty.size === 0;
}
function renderPlayers(force = false) {
  if (!force && !canRebuildPlayerCards()) {
    updatePlayerLiveFields();
    return;
  }
  const wrap = document.querySelector('#players');
  const tpl = document.querySelector('#player-card-template');
  wrap.textContent = '';
  state.playerDirty.clear();
  const selected = currentSelection();
  for (let i = 0; i < 4; i++) {
    const key = selected[i] || defaults[i];
    const card = tpl.content.firstElementChild.cloneNode(true);
    const player = state.status.players.find(p => p.key === key) || state.status.players[i];
    wireCard(card, player, i);
    wrap.append(card);
  }
  state.playersMounted = true;
}
function updatePlayerLiveFields() {
  for (const card of document.querySelectorAll('#players .player-card')) {
    const key = card.dataset.playerKey;
    const player = state.status.players.find(p => p.key === key);
    if (!player) continue;
    updatePlayerStateBadge(card, player);
    updateTpCreditBalance(card, player);
    card.querySelector('.status').textContent = statusText(player);
  }
}
function tpCreditState(player) {
  const credits = player.tpCredits || {};
  return {
    earningEnabled: credits.earningEnabled === true,
    creditsPerQuiz: Math.max(1, Number(credits.creditsPerQuiz) || 1),
    balance: Math.max(0, Number(credits.balance) || 0),
    rewardChoice: credits.rewardChoice || 'teleport',
  };
}
function updateTpCreditBalance(card, player) {
  const balance = card.querySelector('.tp-credit-balance');
  if (balance) balance.textContent = `TP credits: ${tpCreditState(player).balance}`;
}
function markPlayerDirty(key) {
  state.playerDirty.add(key);
}
function clearPlayerDirty(key) {
  state.playerDirty.delete(key);
}
function markGlobalDirty() {
  state.globalDirty = true;
}
function scheduleGlobalAutosave() {
  markGlobalDirty();
  clearTimeout(state.globalSaveTimer);
  const delay = globalEditorHasFocus() ? 600 : 0;
  state.globalSaveTimer = setTimeout(() => {
    saveGlobal({ blur: false }).catch(err => {
      document.querySelector('#server-line').textContent = `Global autosave failed: ${err.message}`;
    });
  }, delay);
}
function markRewardGroupsDirty() {
  state.rewardGroupsDirty = true;
  clearTimeout(state.rewardGroupsSaveTimer);
  const delay = rewardGroupsEditorHasFocus() ? 800 : 0;
  state.rewardGroupsSaveTimer = setTimeout(() => {
    saveRewardGroups({ blur: false }).catch(err => {
      document.querySelector('#server-line').textContent = `Reward groups autosave failed: ${err.message}`;
    });
  }, delay);
}
function wireDirtyTracking(card, player) {
  for (const selector of [
    '.real-name', '.operation', '.quiz-type', '.quiz-source', '.range', '.problems',
    '.tp-credit-earning', '.tp-credits-per-quiz', '.tp-credit-reward-choice',
    '.reward-count', '.reward-item', '.fluency-reward-count', '.fluency-reward-item',
    '.radius', '.npc-select', '.lock',
  ]) {
    const input = card.querySelector(selector);
    if (!input) continue;
    const autosave = () => {
      markPlayerDirty(player.key);
      schedulePlayerAutosave(card, player);
    };
    input.addEventListener('input', autosave);
    input.addEventListener('change', autosave);
  }
}
function currentSelection() {
  const selected = state.selectedPlayers.length ? state.selectedPlayers : defaults;
  return [...selected, ...defaults].slice(0, 4);
}
function wireCard(card, player, index) {
  card.dataset.playerKey = player.key;
  const select = card.querySelector('.player-select');
  for (const p of state.status.players) {
    const opt = document.createElement('option');
    opt.value = p.key;
    opt.textContent = p.playerName;
    select.append(opt);
  }
  select.value = player.key;
  select.onchange = () => {
    const next = currentSelection();
    next[index] = select.value;
    state.selectedPlayers = next;
    localStorage.setItem('mq.selectedPlayers', JSON.stringify(next));
    renderPlayers(true);
  };
  card.querySelector('.real-name').value = player.realName || '';
  updatePlayerStateBadge(card, player);
  const tpCredits = tpCreditState(player);
  updateTpCreditBalance(card, player);
  card.querySelector('.tp-credit-earning').checked = tpCredits.earningEnabled;
  card.querySelector('.tp-credits-per-quiz').value = tpCredits.creditsPerQuiz;
  const tpRewardChoice = card.querySelector('.tp-credit-reward-choice');
  tpRewardChoice.value = [...tpRewardChoice.options].some(option => option.value === tpCredits.rewardChoice)
    ? tpCredits.rewardChoice
    : 'teleport';
  card.querySelector('.operation').value = player.params.operation;
  card.querySelector('.quiz-type').value = player.params.quizType || 'standard_arithmetic';
  card.querySelector('.quiz-source').value = player.params.internalQuizSource || (
    player.params.useInternalProblemList ? 'internal_problem_list' : 'internal_quick_quiz'
  );
  card.querySelector('.range').value = `${player.params.minNumber}-${player.params.maxNumber}`;
  card.querySelector('.problems').value = player.params.problemsPerQuiz;
  wireInternalProblemToggle(card);
  card.querySelector('.radius').value = state.status.config.npcSpawnRadiusBlocks;
  const rewardItem = card.querySelector('.reward-item');
  rewardItem.value = displayRewardFieldValue(player.rewardGroup, player.reward.item);
  wireRewardFieldAutocomplete(rewardItem);
  card.querySelector('.reward-count').value = player.reward.count;
  const fluencyRewardItem = card.querySelector('.fluency-reward-item');
  fluencyRewardItem.value = displayRewardFieldValue(
    player.fluencyRewardGroup,
    (player.fluencyReward || player.reward).item
  );
  wireRewardFieldAutocomplete(fluencyRewardItem);
  card.querySelector('.fluency-reward-count').value = (player.fluencyReward || player.reward).count;
  const npcSelect = card.querySelector('.npc-select');
  for (const npc of state.status.npcs) {
    const opt = document.createElement('option');
    opt.value = npc.id;
    opt.textContent = npc.name;
    npcSelect.append(opt);
  }
  npcSelect.value = player.npcId || 'wandering_nerd';
  card.querySelector('.lock').checked = player.npcLocked !== false;
  card.querySelector('.spawn').onclick = () => spawnNpc(card, player);
  card.querySelector('.open').onclick = () => openQuiz(card, player);
  card.querySelector('.vanish').onclick = () => vanish(card, player);
  card.querySelector('.status').textContent = statusText(player);
  wireMobTools(card, player);
  applyQuestPlayerLock(card, player);
  wireDirtyTracking(card, player);
}
function isPlayerInQuest(player) {
  return Boolean(player && player.quest && player.quest.active);
}
function updatePlayerStateBadge(card, player) {
  const online = card.querySelector('.online-state');
  const inQuest = isPlayerInQuest(player);
  online.textContent = `${player.online ? 'Online' : 'Offline'}${inQuest ? ' · In quest' : ''}`;
  online.classList.toggle('online', player.online);
  online.classList.toggle('offline', !player.online);
  online.classList.toggle('quest-active', inQuest);
}
function applyQuestPlayerLock(card, player) {
  const locked = isPlayerInQuest(player);
  for (const selector of ['.operation', '.quiz-type', '.quiz-source', '.range', '.problems']) {
    const input = card.querySelector(selector);
    if (!input) continue;
    input.disabled = locked || input.disabled;
    const label = input.closest('label');
    if (label) {
      label.classList.toggle('quest-disabled', locked);
    }
  }
  const open = card.querySelector('.open');
  if (open) open.textContent = locked ? 'Open Quest Quiz' : 'Open Quiz';
}
function statusText(player) {
  const active = player.activeNerds || [];
  const last = player.lastNpcState;
  const lines = [];
  if (isPlayerInQuest(player)) {
    lines.push(`Quest: ${player.quest.currentMilestoneName || player.quest.currentMilestoneId || 'active'}`);
  }
  lines.push(active.length ? `${active.length} active NPC${active.length === 1 ? '' : 's'}` : 'No active NPC');
  if (active.some(n => n.clicked)) lines.push('Clicked: yes');
  else if (last && last.lastClickedAtMillis) lines.push(`Last clicked: ${timeAgo(last.lastClickedAtMillis)}`);
  else lines.push('Clicked: no');
  if (last && last.lastSpawnedAtMillis) lines.push(`Last spawn: ${timeAgo(last.lastSpawnedAtMillis)}`);
  return lines.join('\n');
}
function payload(card, player) {
  const out = {
    playerName: player.playerName,
    npcId: card.querySelector('.npc-select').value,
    locked: card.querySelector('.lock').checked,
    radius: Number(card.querySelector('.radius').value || state.status.config.npcSpawnRadiusBlocks),
    realName: card.querySelector('.real-name').value.trim() || player.realName || player.playerName,
    rewardItem: rewardFieldPayload(card.querySelector('.reward-item').value),
    rewardCount: Number(card.querySelector('.reward-count').value || 1),
    fluencyRewardItem: rewardFieldPayload(card.querySelector('.fluency-reward-item').value),
    fluencyRewardCount: Number(card.querySelector('.fluency-reward-count').value || 1),
  };
  if (!isPlayerInQuest(player)) {
    Object.assign(out, {
      quizType: card.querySelector('.quiz-type').value,
      internalQuizSource: card.querySelector('.quiz-source').value,
      useInternalProblemList: card.querySelector('.quiz-source').value === 'internal_problem_list',
      operation: card.querySelector('.operation').value,
      ...rangePayload(card.querySelector('.range').value, player),
      problemsPerQuiz: Number(card.querySelector('.problems').value || player.params.problemsPerQuiz || 5),
    });
  }
  return out;
}
function schedulePlayerAutosave(card, player) {
  clearTimeout(state.playerSaveTimers[player.key]);
  const delay = card.contains(document.activeElement) ? 600 : 0;
  state.playerSaveTimers[player.key] = setTimeout(() => {
    savePlayer(card, player, { blur: false, refresh: false }).catch(err => {
      const status = card.querySelector('.status');
      if (status) status.textContent = `Autosave failed: ${err.message}`;
    });
  }, delay);
}
async function savePlayer(card, player, options = {}) {
  if (options.blur !== false) blurActive();
  const radius = Number(card.querySelector('.radius').value || state.status.config.npcSpawnRadiusBlocks);
  const body = {
    npcSpawnRadiusBlocks: radius,
    playerRewards: { [player.key]: {
      item: rewardFieldPayload(card.querySelector('.reward-item').value),
      count: Number(card.querySelector('.reward-count').value || 1),
    } },
    playerFluencyRewards: { [player.key]: {
      item: rewardFieldPayload(card.querySelector('.fluency-reward-item').value),
      count: Number(card.querySelector('.fluency-reward-count').value || 1),
    } },
    playerRealNames: { [player.key]: card.querySelector('.real-name').value.trim() || player.realName || player.playerName },
    playerNpcSelections: { [player.key]: card.querySelector('.npc-select').value },
    playerNpcLocks: { [player.key]: card.querySelector('.lock').checked },
    playerTpCreditEarningEnabled: { [player.key]: card.querySelector('.tp-credit-earning').checked },
    playerTpCreditsPerQuiz: { [player.key]: Number(card.querySelector('.tp-credits-per-quiz').value || 1) },
    playerTpCreditRewardChoices: { [player.key]: card.querySelector('.tp-credit-reward-choice').value || 'teleport' },
  };
  if (!isPlayerInQuest(player)) {
    Object.assign(body, {
      playerQuizTypes: { [player.key]: card.querySelector('.quiz-type').value },
      playerInternalQuizSources: { [player.key]: card.querySelector('.quiz-source').value },
      playerUseInternalProblemLists: { [player.key]: card.querySelector('.quiz-source').value === 'internal_problem_list' },
      playerPresets: { [player.key]: {
        operation: card.querySelector('.operation').value,
        ...rangePayload(card.querySelector('.range').value, player),
        problemsPerQuiz: Number(card.querySelector('.problems').value || player.params.problemsPerQuiz || 5),
      } },
    });
  }
  const result = await api('/api/config', { method: 'POST', body: JSON.stringify(body) });
  clearPlayerDirty(player.key);
  if (result.status) state.status = result.status;
  if (options.refresh === false) {
    updatePlayerLiveFields();
  } else {
    await refresh();
  }
}
function wireInternalProblemToggle(card) {
  const source = card.querySelector('.quiz-source');
  source.onchange = () => updateInternalProblemControls(card);
  updateInternalProblemControls(card);
}
function updateInternalProblemControls(card) {
  const key = card.dataset.playerKey;
  const player = state.status.players.find(p => p.key === key);
  const questLocked = isPlayerInQuest(player);
  const source = card.querySelector('.quiz-source').value;
  const disabled = {
    '.operation': questLocked || source === 'internal_problem_list' || source === 'internal_fluency_feast',
    '.range': questLocked || source === 'internal_problem_list' || source === 'internal_quick_quiz' || source === 'internal_fluency_feast',
    '.problems': questLocked || source === 'internal_problem_list' || source === 'internal_quick_quiz' || source === 'internal_fluency_feast',
    '.quiz-type': questLocked,
    '.quiz-source': questLocked,
  };
  for (const selector of Object.keys(disabled)) {
    const input = card.querySelector(selector);
    if (!input) continue;
    input.disabled = disabled[selector];
    const label = input.closest('label');
    if (label) label.classList.toggle('internal-disabled', disabled[selector]);
  }
}
function rangePayload(text, player) {
  const match = String(text || '').trim().match(/^(-?\d+)\s*(?:-|,|\.\.)\s*(-?\d+)$/);
  if (!match) return {
    minNumber: player.params.minNumber,
    maxNumber: player.params.maxNumber,
  };
  return {
    minNumber: Number(match[1]),
    maxNumber: Number(match[2]),
  };
}
function setupRewardItemAutocomplete() {
  const list = document.querySelector('#reward-item-list');
  const groupList = document.querySelector('#reward-group-list');
  if (!list || !groupList || !state.status) return;
  const signature = (state.status.rewardGroups || []).map(group => group.name).join('|');
  if (list.dataset.rewardSignature === signature) return;
  list.textContent = '';
  groupList.textContent = '';
  for (const group of state.status.rewardGroups || []) {
    const groupOpt = document.createElement('option');
    groupOpt.value = group.name;
    groupList.append(groupOpt);
    const combinedOpt = document.createElement('option');
    combinedOpt.value = group.name;
    list.append(combinedOpt);
  }
  for (const item of window.MATHQUEST_ITEM_IDS || []) {
    const opt = document.createElement('option');
    opt.value = item;
    list.append(opt);
  }
  list.dataset.rewardSignature = signature;
}
function setupItemAutocomplete() {
  const list = document.querySelector('#item-list');
  if (!list || list.dataset.ready) return;
  for (const item of window.MATHQUEST_ITEM_IDS || []) {
    const opt = document.createElement('option');
    opt.value = item;
    list.append(opt);
  }
  list.dataset.ready = 'true';
}
function setupMobAutocomplete() {
  const list = document.querySelector('#mob-list');
  if (!list || list.dataset.ready) return;
  for (const mob of window.MATHQUEST_MOB_IDS || []) {
    const opt = document.createElement('option');
    opt.value = mob;
    list.append(opt);
  }
  list.dataset.ready = 'true';
}
function wireItemAutocomplete(input) {
  input.onkeydown = event => {
    if (event.key !== 'Tab') return;
    const match = firstItemMatch(input.value);
    if (!match) return;
    event.preventDefault();
    input.value = match;
    input.dispatchEvent(new Event('input', { bubbles: true }));
  };
}
function wireRewardFieldAutocomplete(input) {
  input.onkeydown = event => {
    if (event.key === 'Tab' || event.key === 'Enter') {
      const groupMatch = firstRewardFieldMatch(input.value);
      if (groupMatch) {
        event.preventDefault();
        input.value = groupMatch;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return;
      }
    }
    if (event.key !== 'Tab') return;
    const match = firstItemMatch(rewardFieldRaw(input.value));
    if (!match) return;
    event.preventDefault();
    input.value = match;
    input.dispatchEvent(new Event('input', { bubbles: true }));
  };
  input.onblur = () => formatRewardFieldDisplay(input);
}
function firstRewardFieldMatch(value) {
  const raw = rewardFieldRaw(value);
  if (!raw) return null;
  const group = knownRewardGroupName(raw);
  if (group) return displayRewardFieldValue(group, null);
  return firstItemMatch(raw);
}
function knownRewardGroupName(raw) {
  const needle = rewardFieldRaw(raw).toLowerCase().replace(/[-\s]+/g, '_');
  if (!needle) return null;
  for (const [key, displayName] of knownRewardGroupNames()) {
    if (key === needle) return displayName;
  }
  return null;
}
function knownRewardGroupNames() {
  const names = new Map();
  for (const group of state.status?.rewardGroups || []) {
    const key = String(group.name || '').toLowerCase().replace(/[-\s]+/g, '_');
    if (key) names.set(key, group.name);
  }
  if (state.rewardGroupsDirty) {
    for (const card of document.querySelectorAll('.reward-group-card')) {
      const displayName = card.querySelector('.group-name')?.value.trim();
      const key = String(displayName || '').toLowerCase().replace(/[-\s]+/g, '_');
      if (key) names.set(key, displayName);
    }
  }
  return names;
}
function formatRewardFieldDisplay(input) {
  const group = knownRewardGroupName(input.value);
  if (group) input.value = displayRewardFieldValue(group, null);
}
function displayRewardFieldValue(groupName, item) {
  if (groupName) return `${groupName} (group)`;
  return displayItemId(item);
}
function rewardFieldRaw(value) {
  return String(value || '').trim().replace(/\s*\(group\)\s*$/i, '').trim();
}
function rewardFieldPayload(value) {
  return itemSearchValue(rewardFieldRaw(value));
}
function wireMobTools(card, player) {
  const settings = mobSettings(player.key);
  const mobInput = card.querySelector('.mob-id');
  mobInput.value = settings.mobId;
  wireMobAutocomplete(mobInput);
  card.querySelector('.mob-count').value = settings.count;
  card.querySelector('.mob-radius').value = settings.radius;
  card.querySelector('.spawn-mobs').onclick = () => spawnMobs(card, player);
  card.querySelector('.mob-status').textContent = state.lastMobSpawns[player.key] || '';
}
function mobSettings(key) {
  try {
    return {
      mobId: 'zombie',
      count: 10,
      radius: 20,
      ...JSON.parse(localStorage.getItem(`mq.mob.${key}`) || '{}'),
    };
  } catch {
    return { mobId: 'zombie', count: 10, radius: 20 };
  }
}
function saveMobSettings(key, settings) {
  localStorage.setItem(`mq.mob.${key}`, JSON.stringify(settings));
}
function wireMobAutocomplete(input) {
  input.onkeydown = event => {
    if (event.key !== 'Tab') return;
    const match = firstMobMatch(input.value);
    if (!match) return;
    event.preventDefault();
    input.value = match;
    input.dispatchEvent(new Event('input', { bubbles: true }));
  };
}
function firstMobMatch(value) {
  const needle = mobSearchValue(value);
  if (!needle) return null;
  const mobs = window.MATHQUEST_MOB_IDS || [];
  return mobs.find(mob => mob.startsWith(needle)) || mobs.find(mob => mob.includes(needle)) || null;
}
function mobPayload(value) {
  return mobSearchValue(value);
}
function mobSearchValue(value) {
  return displayItemId(value).toLowerCase().replace(/[-\s]+/g, '_').replace(/[^a-z0-9_:]/g, '');
}
function firstItemMatch(value) {
  const needle = itemSearchValue(value);
  if (!needle) return null;
  const items = window.MATHQUEST_ITEM_IDS || [];
  return items.find(item => item.startsWith(needle)) || items.find(item => item.includes(needle)) || null;
}
function displayItemId(value) {
  return String(value || '').trim().replace(/^minecraft:/i, '');
}
function itemPayload(value) {
  return itemSearchValue(value);
}
function itemSearchValue(value) {
  return displayItemId(value).toLowerCase().replace(/[-\s]+/g, '_').replace(/[^a-z0-9_:]/g, '');
}
async function spawnNpc(card, player) {
  blurActive();
  await api('/api/spawn', { method: 'POST', body: JSON.stringify(payload(card, player)) });
  clearPlayerDirty(player.key);
  await refresh();
}
async function openQuiz(card, player) {
  blurActive();
  await api('/api/open', { method: 'POST', body: JSON.stringify(payload(card, player)) });
  clearPlayerDirty(player.key);
  await refresh();
}
async function vanish(card, player) {
  blurActive();
  await api('/api/vanish', { method: 'POST', body: JSON.stringify({ playerName: player.playerName }) });
  await refresh();
}
async function spawnMobs(card, player) {
  blurActive();
  const settings = {
    mobId: mobPayload(card.querySelector('.mob-id').value) || 'zombie',
    count: Number(card.querySelector('.mob-count').value || 10),
    radius: Number(card.querySelector('.mob-radius').value || 20),
  };
  saveMobSettings(player.key, settings);
  const result = await api('/api/spawn-mobs', {
    method: 'POST',
    body: JSON.stringify({
      playerName: player.playerName,
      mobId: settings.mobId,
      count: settings.count,
      radius: settings.radius,
    }),
  });
  const mobName = displayItemId(result.mobId || settings.mobId);
  state.lastMobSpawns[player.key] = result.ok
    ? `Spawned ${result.spawned}/${result.requested} ${mobName} within ${result.radius} blocks`
    : `Spawn failed: ${result.error || 'unknown error'}`;
  state.status = result.status || await api('/api/status');
  render();
}
async function saveGlobal(options = {}) {
  if (options.blur !== false) blurActive();
  await api('/api/config', {
    method: 'POST',
    body: JSON.stringify({
      quizMode: document.querySelector('#quiz-mode').value,
      npcAllowMultipleNerds: document.querySelector('#allow-multiple').checked,
      npcDespawnSeconds: Number(document.querySelector('#despawn-seconds').value || 120),
      writtenColumnEvaluatorCode: document.querySelector('#evaluator-code').value.trim() || 'paper',
    }),
  });
  state.globalDirty = false;
  await refresh();
}
function renderGallery() {
  const body = document.querySelector('#gallery-body');
  body.classList.toggle('open', state.galleryOpen);
  body.textContent = '';
  for (const npc of state.status.npcs) {
    const div = document.createElement('div');
    div.className = 'npc-card';
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 192;
    div.append(canvas);
    const h = document.createElement('h3');
    h.textContent = npc.name;
    div.append(h);
    const p = document.createElement('p');
    p.textContent = npc.name;
    div.append(p);
    const lines = document.createElement('div');
    lines.className = 'dialogue-lines';
    for (const line of npc.dialogueLines || []) {
      const row = document.createElement('textarea');
      row.value = line;
      row.rows = 2;
      lines.append(row);
    }
    div.append(lines);
    const save = document.createElement('button');
    save.textContent = 'Save dialogue';
    save.onclick = () => saveNpcDialogue(npc.id, div);
    div.append(save);
    body.append(div);
    drawNpcPreview(canvas, npc.textureUrl);
  }
}
async function saveNpcDialogue(npcId, card) {
  const lines = [...card.querySelectorAll('textarea')]
    .map(t => t.value.replace(/\s+/g, ' ').trim())
    .filter(Boolean);
  blurActive();
  state.status = (await api('/api/config', {
    method: 'POST',
    body: JSON.stringify({ npcDialogues: { [npcId]: lines } }),
  })).status;
  render();
}
function clearRewardGroupsDirty() {
  state.rewardGroupsDirty = false;
}
function renderRewardGroups() {
  const body = document.querySelector('#reward-groups-body');
  const list = document.querySelector('#reward-groups-list');
  if (!body || !list) return;
  body.classList.toggle('open', state.rewardGroupsOpen);
  list.textContent = '';
  for (const group of state.status.rewardGroups || []) {
    list.append(buildRewardGroupCard(group));
  }
}
function buildRewardGroupCard(group) {
  const card = document.createElement('div');
  card.className = 'reward-group-card';
  const head = document.createElement('div');
  head.className = 'reward-group-head';
  const nameLabel = document.createElement('label');
  nameLabel.textContent = 'Group name';
  const nameInput = document.createElement('input');
  nameInput.className = 'group-name';
  nameInput.value = group.name || '';
  nameLabel.append(nameInput);
  const modeLabel = document.createElement('label');
  modeLabel.textContent = 'Mode';
  const modeSelect = document.createElement('select');
  modeSelect.className = 'group-mode';
  for (const [value, label] of [
    ['all', 'Give all'],
    ['random', 'Give one at random'],
    ['choose', 'Let player choose one'],
  ]) {
    const opt = document.createElement('option');
    opt.value = value;
    opt.textContent = label;
    modeSelect.append(opt);
  }
  modeSelect.value = group.mode || 'all';
  modeLabel.append(modeSelect);
  const removeGroup = document.createElement('button');
  removeGroup.type = 'button';
  removeGroup.textContent = 'Delete';
  removeGroup.onclick = () => {
    card.remove();
    markRewardGroupsDirty();
  };
  head.append(nameLabel, modeLabel, removeGroup);
  card.append(head);
  const entries = document.createElement('div');
  entries.className = 'reward-group-entries';
  for (const entry of group.entries || []) {
    entries.append(buildRewardGroupEntryRow(entry));
  }
  card.append(entries);
  const addEntry = document.createElement('button');
  addEntry.type = 'button';
  addEntry.textContent = 'Add item';
  addEntry.onclick = () => {
    entries.append(buildRewardGroupEntryRow({ item: 'diamond', count: 1 }));
    markRewardGroupsDirty();
  };
  for (const input of [nameInput, modeSelect]) {
    input.addEventListener('input', markRewardGroupsDirty);
    input.addEventListener('change', markRewardGroupsDirty);
  }
  card.append(addEntry);
  return card;
}
function buildRewardGroupEntryRow(entry) {
  const row = document.createElement('div');
  row.className = 'reward-group-entry';
  const itemInput = document.createElement('input');
  itemInput.className = 'entry-item';
  itemInput.setAttribute('list', 'item-list');
  itemInput.value = displayItemId(entry.item || 'diamond');
  wireItemAutocomplete(itemInput);
  const countInput = document.createElement('input');
  countInput.className = 'entry-count';
  countInput.type = 'number';
  countInput.min = '1';
  countInput.max = '64';
  countInput.value = entry.count || 1;
  const remove = document.createElement('button');
  remove.type = 'button';
  remove.textContent = 'Remove';
  remove.onclick = () => {
    row.remove();
    markRewardGroupsDirty();
  };
  for (const input of [itemInput, countInput]) {
    input.addEventListener('input', markRewardGroupsDirty);
    input.addEventListener('change', markRewardGroupsDirty);
  }
  row.append(itemInput, countInput, remove);
  return row;
}
function collectRewardGroupsPayload() {
  const payload = {};
  for (const card of document.querySelectorAll('.reward-group-card')) {
    const name = card.querySelector('.group-name').value.trim().toLowerCase().replace(/[-\s]+/g, '_');
    if (!name) continue;
    const entries = [...card.querySelectorAll('.reward-group-entry')].map(row => ({
      item: itemPayload(row.querySelector('.entry-item').value),
      count: Number(row.querySelector('.entry-count').value || 1),
    })).filter(entry => entry.item);
    if (!entries.length) continue;
    payload[name] = {
      mode: card.querySelector('.group-mode').value,
      entries,
    };
  }
  return payload;
}
async function saveRewardGroups(options = {}) {
  if (options.blur !== false) blurActive();
  await api('/api/config', {
    method: 'POST',
    body: JSON.stringify({ rewardGroups: collectRewardGroupsPayload() }),
  });
  clearRewardGroupsDirty();
  await refresh();
}
function galleryEditorHasFocus() {
  return Boolean(document.activeElement && document.activeElement.closest && document.activeElement.closest('.dialogue-lines'));
}
function rewardGroupsEditorHasFocus() {
  return Boolean(document.activeElement && document.activeElement.closest && document.activeElement.closest('.reward-groups'));
}
function playerEditorHasFocus() {
  return Boolean(document.activeElement && document.activeElement.closest && document.activeElement.closest('.player-card'));
}
function globalEditorHasFocus() {
  return Boolean(document.activeElement && document.activeElement.closest && document.activeElement.closest('.global-controls'));
}
function blurActive() {
  const active = document.activeElement;
  if (active && active.blur) active.blur();
}
function drawNpcPreview(canvas, url) {
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = false;
  const img = new Image();
  img.onload = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#ece8dc';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawPart(ctx, img, 8, 8, 8, 10, 48, 14, 32, 40);
    drawPart(ctx, img, 20, 20, 8, 12, 48, 56, 32, 48);
    drawPart(ctx, img, 44, 20, 4, 12, 32, 58, 16, 48);
    drawPart(ctx, img, 44, 20, 4, 12, 80, 58, 16, 48);
    drawPart(ctx, img, 4, 20, 4, 12, 48, 104, 16, 48);
    drawPart(ctx, img, 4, 20, 4, 12, 64, 104, 16, 48);
  };
  img.src = url;
}
function drawPart(ctx, img, sx, sy, sw, sh, dx, dy, dw, dh) {
  ctx.drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh);
}
function timeAgo(ms) {
  const seconds = Math.max(0, Math.round((Date.now() - ms) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  return `${minutes}m ago`;
}
for (const selector of ['#quiz-mode', '#allow-multiple', '#despawn-seconds', '#evaluator-code']) {
  const input = document.querySelector(selector);
  if (!input) continue;
  input.addEventListener('input', scheduleGlobalAutosave);
  input.addEventListener('change', scheduleGlobalAutosave);
}
document.querySelector('#vanish-all').onclick = async () => {
  await api('/api/vanish', { method: 'POST', body: '{}' });
  await refresh();
};
document.querySelector('#gallery-toggle').onclick = () => {
  state.galleryOpen = !state.galleryOpen;
  renderGallery();
};
document.querySelector('#reward-groups-toggle').onclick = () => {
  state.rewardGroupsOpen = !state.rewardGroupsOpen;
  renderRewardGroups();
};
document.querySelector('#add-reward-group').onclick = () => {
  state.rewardGroupsOpen = true;
  document.querySelector('#reward-groups-body').classList.add('open');
  document.querySelector('#reward-groups-list').append(buildRewardGroupCard({
    name: 'new_group',
    mode: 'random',
    entries: [{ item: 'minecraft:diamond', count: 1 }],
  }));
  markRewardGroupsDirty();
};
refresh();
setInterval(refresh, 2500);
