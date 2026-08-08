const state = {
  status: null,
  plan: JSON.parse(localStorage.getItem('mq.mobPlan') || '[]'),
  history: JSON.parse(localStorage.getItem('mq.mobHistory') || '[]'),
  mapTarget: { offsetX: 0, offsetZ: 0 },
  terrainMap: null,
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
  state.status = await api('/api/status');
  render();
}
async function refreshStatusOnly() {
  state.status = await api('/api/status');
  renderStatusLine();
  renderLocationControls();
}
function render() {
  setupMobAutocomplete();
  setupTerrainMap();
  renderStatusLine();
  renderLocationControls();
  renderPlan();
  renderHistory();
  drawMap();
}
function renderStatusLine() {
  document.querySelector('#server-line').textContent =
    `${state.status.onlinePlayers.length} online | seed ${state.status.worldSeed} | ${state.status.config.controlPanelUrl}mob-spawn.html`;
}
function renderLocationControls() {
  const source = document.querySelector('#player-source');
  const currentPlayer = source.value;
  source.textContent = '';
  for (const player of state.status.playerLocations || []) {
    const opt = document.createElement('option');
    opt.value = player.playerName;
    opt.textContent = `${player.playerName} (${player.x}, ${player.y}, ${player.z})`;
    source.append(opt);
  }
  if (currentPlayer) source.value = currentPlayer;
  const dimension = document.querySelector('#dimension');
  const currentDimension = dimension.value;
  dimension.textContent = '';
  const dimensions = [...new Set([
    'minecraft:overworld',
    'minecraft:the_nether',
    'minecraft:the_end',
    ...(state.status.playerLocations || []).map(p => p.dimension),
  ])];
  for (const dim of dimensions) {
    const opt = document.createElement('option');
    opt.value = dim;
    opt.textContent = dim.replace(/^minecraft:/, '');
    dimension.append(opt);
  }
  if (currentDimension) dimension.value = currentDimension;
  if (!document.querySelector('#center-x').value && state.status.playerLocations && state.status.playerLocations.length) {
    capturePlayerLocation();
  }
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
  for (const input of document.querySelectorAll('#mob-id, #kill-mob-id')) {
    wireMobAutocomplete(input);
  }
}
function setupTerrainMap() {
  if (state.terrainMap) return;
  state.terrainMap = new MathQuestTerrainMap({
    canvas: document.querySelector('#mob-map'),
    getView: mapView,
    onViewChange: view => {
      document.querySelector('#center-x').value = view.x;
      document.querySelector('#center-z').value = view.z;
      document.querySelector('#view-radius').value = view.radius;
      document.querySelector('#dimension').value = view.dimension;
      drawMap();
    },
    onClickWorld: world => {
      const center = currentCenter();
      state.mapTarget = {
        offsetX: Math.round(world.x - center.x),
        offsetZ: Math.round(world.z - center.z),
      };
      document.querySelector('#offset-x').value = state.mapTarget.offsetX;
      document.querySelector('#offset-z').value = state.mapTarget.offsetZ;
      drawMap();
    },
    drawOverlay: drawMapOverlay,
  });
}
function wireMobAutocomplete(input) {
  input.onkeydown = event => {
    if (event.key !== 'Tab') return;
    const match = firstMobMatch(input.value);
    if (!match) return;
    event.preventDefault();
    input.value = match;
  };
}
function firstMobMatch(value) {
  const needle = normalizeId(value);
  if (!needle) return null;
  const mobs = window.MATHQUEST_MOB_IDS || [];
  return mobs.find(mob => mob.startsWith(needle)) || mobs.find(mob => mob.includes(needle)) || null;
}
async function captureFreshPlayerLocation() {
  await refreshStatusOnly();
  capturePlayerLocation();
}
function capturePlayerLocation() {
  const name = document.querySelector('#player-source').value;
  const player = (state.status.playerLocations || []).find(p => p.playerName === name) || (state.status.playerLocations || [])[0];
  if (!player) return;
  document.querySelector('#center-x').value = player.x;
  document.querySelector('#center-y').value = player.y;
  document.querySelector('#center-z').value = player.z;
  document.querySelector('#dimension').value = player.dimension;
  state.mapTarget = { offsetX: 0, offsetZ: 0 };
  drawMap();
}
function currentCenter() {
  return {
    x: Number(document.querySelector('#center-x').value || 0),
    y: Number(document.querySelector('#center-y').value || 64),
    z: Number(document.querySelector('#center-z').value || 0),
    dimension: document.querySelector('#dimension').value || 'minecraft:overworld',
  };
}
function mapView() {
  const center = currentCenter();
  return {
    x: center.x,
    z: center.z,
    radius: Number(document.querySelector('#view-radius').value || 64),
    dimension: center.dimension,
  };
}
function builderEntry() {
  const center = currentCenter();
  const offsetX = Number(document.querySelector('#offset-x').value || 0);
  const offsetZ = Number(document.querySelector('#offset-z').value || 0);
  const targetYRaw = document.querySelector('#target-y').value;
  return {
    id: `${Date.now()}-${Math.round(Math.random() * 100000)}`,
    mobId: normalizeId(document.querySelector('#mob-id').value) || 'zombie',
    shape: document.querySelector('#shape').value,
    count: Number(document.querySelector('#count').value || 1),
    radius: Number(document.querySelector('#radius').value || 1),
    lineLength: Number(document.querySelector('#line-length').value || 1),
    angleDeg: Number(document.querySelector('#angle').value || 0),
    x: center.x + offsetX,
    y: targetYRaw === '' ? center.y : Number(targetYRaw),
    z: center.z + offsetZ,
    offsetX,
    offsetZ,
  };
}
function normalizeId(value) {
  return String(value || '').trim().replace(/^minecraft:/i, '').toLowerCase().replace(/[-\s]+/g, '_').replace(/[^a-z0-9_:]/g, '');
}
function addEntry() {
  state.plan.push(builderEntry());
  savePlan();
  render();
}
function savePlan() {
  localStorage.setItem('mq.mobPlan', JSON.stringify(state.plan));
}
function saveHistory() {
  localStorage.setItem('mq.mobHistory', JSON.stringify(state.history.slice(0, 10)));
}
function renderPlan() {
  const wrap = document.querySelector('#plan-list');
  wrap.textContent = '';
  if (!state.plan.length) {
    const empty = document.createElement('p');
    empty.textContent = 'No queued entries.';
    wrap.append(empty);
    return;
  }
  for (const entry of state.plan) {
    const card = document.createElement('div');
    card.className = 'plan-card';
    const h = document.createElement('h3');
    h.textContent = `${entry.count} ${entry.mobId} | ${shapeName(entry.shape)}`;
    const meta = document.createElement('div');
    meta.className = 'plan-meta';
    meta.textContent = `Target ${entry.x}, ${entry.y}, ${entry.z} | radius ${entry.radius} | line ${entry.lineLength} @ ${entry.angleDeg} deg`;
    const actions = document.createElement('div');
    actions.className = 'plan-actions';
    const spawn = document.createElement('button');
    spawn.textContent = 'Spawn';
    spawn.onclick = () => spawnEntries([entry], false);
    const dup = document.createElement('button');
    dup.textContent = 'Duplicate';
    dup.onclick = () => {
      state.plan.push({ ...entry, id: `${Date.now()}-${Math.round(Math.random() * 100000)}` });
      savePlan();
      render();
    };
    const remove = document.createElement('button');
    remove.textContent = 'Remove';
    remove.onclick = () => {
      state.plan = state.plan.filter(e => e.id !== entry.id);
      savePlan();
      render();
    };
    actions.append(spawn, dup, remove);
    card.append(h, meta, actions);
    wrap.append(card);
  }
}
function renderHistory() {
  const wrap = document.querySelector('#history-list');
  wrap.textContent = '';
  for (const run of state.history.slice(0, 6)) {
    const card = document.createElement('div');
    card.className = 'history-card';
    const p = document.createElement('div');
    p.textContent = `${run.label} | ${run.spawned}/${run.requested} spawned`;
    const again = document.createElement('button');
    again.textContent = 'Queue Again';
    again.onclick = () => {
      state.plan.push(...run.entries.map(e => ({ ...e, id: `${Date.now()}-${Math.round(Math.random() * 100000)}` })));
      savePlan();
      render();
    };
    card.append(p, again);
    wrap.append(card);
  }
}
function shapeName(shape) {
  return {
    circle: 'circle fill',
    rim: 'circle rim',
    line: 'line',
    point: 'point',
  }[shape] || shape;
}
async function spawnEntries(entries, keepQueue) {
  const payload = {
    dimension: currentCenter().dimension,
    entries: entries.map(({ id, offsetX, offsetZ, ...rest }) => rest),
  };
  const result = await api('/api/spawn-mob-plan', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  const label = entries.map(e => `${e.count} ${e.mobId}`).join(', ');
  document.querySelector('#entry-log').textContent = result.ok
    ? `Spawned ${result.spawned}/${result.requested}: ${label}`
    : `Spawn failed: ${result.error || 'unknown error'}`;
  state.history.unshift({
    label,
    spawned: result.spawned || 0,
    requested: result.requested || 0,
    entries,
  });
  state.history = state.history.slice(0, 10);
  saveHistory();
  if (!keepQueue) {
    const ids = new Set(entries.map(e => e.id));
    state.plan = state.plan.filter(e => !ids.has(e.id));
    savePlan();
  }
  render();
}
async function killArea() {
  const center = currentCenter();
  const result = await api('/api/kill-mob-area', {
    method: 'POST',
    body: JSON.stringify({
      dimension: center.dimension,
      mobId: normalizeId(document.querySelector('#kill-mob-id').value) || 'zombie',
      shape: document.querySelector('#kill-shape').value,
      x: center.x,
      y: center.y,
      z: center.z,
      radius: Number(document.querySelector('#kill-radius').value || 30),
    }),
  });
  document.querySelector('#kill-log').textContent = result.ok
    ? `Killed ${result.removed} ${result.mobId.replace(/^minecraft:/, '')} in ${result.shape} radius ${result.radius}`
    : `Kill failed: ${result.error || 'unknown error'}`;
}
function drawMap() {
  if (!state.terrainMap) return;
  state.terrainMap.setView(mapView());
}
function drawMapOverlay(ctx, map) {
  for (const entry of [...state.plan, builderEntry()]) {
    drawEntryPreview(ctx, map, entry, entry.id ? '#6b3f8f' : '#a45c16');
  }
  ctx.fillStyle = '#a45c16';
  const center = currentCenter();
  const target = map.worldToScreen(center.x + state.mapTarget.offsetX, center.z + state.mapTarget.offsetZ);
  ctx.beginPath();
  ctx.arc(target.x, target.y, 5, 0, Math.PI * 2);
  ctx.fill();
}
function drawEntryPreview(ctx, map, entry, color) {
  const center = map.worldToScreen(entry.x, entry.z);
  const edge = map.worldToScreen(entry.x + entry.radius, entry.z);
  const r = Math.max(3, Math.abs(edge.x - center.x));
  ctx.strokeStyle = color;
  ctx.fillStyle = `${color}22`;
  ctx.lineWidth = 2;
  if (entry.shape === 'line') {
    const p1 = map.worldToScreen(entry.x, entry.z);
    const p2 = map.worldToScreen(entry.x + entry.lineLength, entry.z);
    const len = Math.abs(p2.x - p1.x);
    const a = entry.angleDeg * Math.PI / 180;
    ctx.beginPath();
    ctx.moveTo(center.x - Math.cos(a) * len / 2, center.y - Math.sin(a) * len / 2);
    ctx.lineTo(center.x + Math.cos(a) * len / 2, center.y + Math.sin(a) * len / 2);
    ctx.stroke();
  } else if (entry.shape === 'point') {
    ctx.beginPath();
    ctx.arc(center.x, center.y, 5, 0, Math.PI * 2);
    ctx.fill();
  } else {
    ctx.beginPath();
    ctx.arc(center.x, center.y, r, 0, Math.PI * 2);
    if (entry.shape === 'circle') ctx.fill();
    ctx.stroke();
  }
}
document.querySelector('#refresh').onclick = refresh;
document.querySelector('#capture-player').onclick = captureFreshPlayerLocation;
document.querySelector('#player-source').onchange = captureFreshPlayerLocation;
document.querySelector('#use-map-target').onclick = () => {
  document.querySelector('#offset-x').value = state.mapTarget.offsetX;
  document.querySelector('#offset-z').value = state.mapTarget.offsetZ;
  drawMap();
};
document.querySelector('#add-entry').onclick = addEntry;
document.querySelector('#spawn-entry').onclick = () => spawnEntries([builderEntry()], true);
document.querySelector('#spawn-all').onclick = () => spawnEntries([...state.plan], false);
document.querySelector('#clear-plan').onclick = () => {
  state.plan = [];
  savePlan();
  render();
};
document.querySelector('#clear-history').onclick = () => {
  state.history = [];
  saveHistory();
  render();
};
document.querySelector('#kill-area').onclick = killArea;
for (const id of ['shape', 'count', 'radius', 'line-length', 'angle', 'offset-x', 'offset-z', 'view-radius', 'center-x', 'center-y', 'center-z']) {
  document.querySelector(`#${id}`).oninput = drawMap;
}
refresh().catch(err => {
  document.querySelector('#server-line').textContent = `Disconnected: ${err.message}`;
});
