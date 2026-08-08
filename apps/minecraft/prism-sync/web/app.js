const WRITE_LOG = true;

const state = {
  config: null,
  rows: [],
  status: {},
  modsDetail: {},
  localMods: {},
  tooltipCache: {},
  reachability: {},
  selected: new Set(),
  computerEnabled: {},
  busy: false,
};

let modsOnlyTouched = false;

const STATUS_LABELS = {
  same_mods: "=",
  different_mods: "≠",
  missing: "✗",
  unreachable: "—",
  unknown: "·",
  unconfigured: "—",
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  return response.json();
}

function setMessage(text, isError = false) {
  const node = document.getElementById("status-message");
  node.textContent = text;
  node.style.color = isError ? "var(--bad)" : "var(--muted)";
}

function parseCsv(value) {
  return value.split(",").map((part) => part.trim()).filter(Boolean);
}

function matrixComputers() {
  return state.config.computers.filter((computer) => computer.role === "target");
}

function enabledTargetIds() {
  return state.config.computers
    .filter((computer) => computer.role === "target" && state.computerEnabled[computer.id])
    .map((computer) => computer.id);
}

function targetComputerIds() {
  return matrixComputers().map((computer) => computer.id);
}

function localRows() {
  return state.rows.filter((row) => row.section !== "remote_only");
}

function visibleRows() {
  const hidePatterns = parseCsv(document.getElementById("filter-hide").value);
  const hideActive = document.getElementById("filter-hide-active").checked;
  let rows = localRows();
  if (hideActive && hidePatterns.length) {
    rows = rows.filter((row) => {
      const name = row.name.toLowerCase();
      return !hidePatterns.some((pattern) => name.includes(pattern.toLowerCase()));
    });
  }
  return rows;
}

function pullableItems() {
  const items = [];
  for (const name of state.selected) {
    for (const computerId of enabledTargetIds()) {
      if ((state.status[name] || {})[computerId] !== "different_mods") {
        continue;
      }
      const diff = (state.modsDetail[name] || {})[computerId];
      const remoteOnly = diff ? (diff.remote_only || []) : [];
      if (!remoteOnly.length) {
        continue;
      }
      items.push({ instanceName: name, computerId, jars: remoteOnly });
    }
  }
  return items;
}

function pushPairs() {
  const pairs = [];
  for (const name of state.selected) {
    for (const computerId of enabledTargetIds()) {
      pairs.push({ name, computerId });
    }
  }
  return pairs;
}

function instanceExistsOnTarget(instanceName, computerId) {
  const status = (state.status[instanceName] || {})[computerId];
  return status === "same_mods" || status === "different_mods";
}

function shouldAutoCheckModsOnly() {
  return pushPairs().some((pair) => instanceExistsOnTarget(pair.name, pair.computerId));
}

function allPushPairsExistOnTarget() {
  const pairs = pushPairs();
  return pairs.length > 0 && pairs.every((pair) => instanceExistsOnTarget(pair.name, pair.computerId));
}

function refreshModsOnlyUi() {
  const modsOnly = document.getElementById("opt-mods-only");
  const syncIcons = document.getElementById("opt-sync-icons");
  const syncIconsLabel = syncIcons.closest("label");
  const iconsMuted = modsOnly.checked && allPushPairsExistOnTarget();
  syncIcons.disabled = iconsMuted;
  if (iconsMuted) {
    syncIcons.checked = false;
  }
  if (syncIconsLabel) {
    syncIconsLabel.style.opacity = iconsMuted ? "0.45" : "";
  }
}

function updateModsOnlyCheckbox() {
  if (!modsOnlyTouched) {
    document.getElementById("opt-mods-only").checked = shouldAutoCheckModsOnly();
  }
  refreshModsOnlyUi();
}

function resetModsOnlyAuto() {
  modsOnlyTouched = false;
  updateModsOnlyCheckbox();
}

function updateActionButtons() {
  document.getElementById("btn-sync").disabled = state.selected.size === 0 || enabledTargetIds().length === 0 || state.busy;
  document.getElementById("btn-pull").disabled = pullableItems().length === 0 || state.busy;
  updateModsOnlyCheckbox();
}

function westCoastTimestamp() {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Los_Angeles",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZoneName: "short",
  }).formatToParts(new Date());
  const pick = (type) => (parts.find((part) => part.type === type) || {}).value || "";
  return pick("year") + "-" + pick("month") + "-" + pick("day") + " " + pick("hour") + ":" + pick("minute") + ":" + pick("second") + " " + pick("timeZoneName");
}

function renderExcludeChips() {
  const container = document.getElementById("exclude-chips");
  container.innerHTML = "";
  for (const label of state.config.rsync_exclude_labels) {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = label;
    container.appendChild(chip);
  }
}

function tooltipCacheKey(instanceName, computerId) {
  return instanceName + "\0" + computerId;
}

function instanceTooltipKey(instanceName) {
  return "local:" + instanceName;
}

function instanceModsTooltip(instanceName) {
  if (!Object.prototype.hasOwnProperty.call(state.localMods, instanceName)) {
    return "";
  }
  const jars = state.localMods[instanceName] || [];
  const lines = ["mods/ on host4:"];
  if (!jars.length) {
    lines.push("  (none)");
  } else {
    for (const jar of jars) {
      lines.push("  " + jar);
    }
  }
  return lines.join("\n");
}

function rebuildTooltipCache() {
  state.tooltipCache = {};
  for (const row of localRows()) {
    const localTip = instanceModsTooltip(row.name);
    if (localTip) {
      state.tooltipCache[instanceTooltipKey(row.name)] = localTip;
    }
    for (const computer of matrixComputers()) {
      const status = cellStatus(row.name, computer);
      const text = cellModsTooltip(row.name, computer, status);
      if (text) {
        state.tooltipCache[tooltipCacheKey(row.name, computer.id)] = text;
      }
    }
  }
}

function positionModsTooltip(event) {
  const node = document.getElementById("mods-tooltip");
  if (node.hidden) {
    return;
  }
  const offset = 12;
  let x = event.clientX + offset;
  let y = event.clientY + offset;
  node.style.left = x + "px";
  node.style.top = y + "px";
  const rect = node.getBoundingClientRect();
  if (rect.right > window.innerWidth - 8) {
    x = event.clientX - rect.width - offset;
    node.style.left = Math.max(8, x) + "px";
  }
  if (rect.bottom > window.innerHeight - 8) {
    y = event.clientY - rect.height - offset;
    node.style.top = Math.max(8, y) + "px";
  }
}

function showModsTooltip(text, event) {
  const node = document.getElementById("mods-tooltip");
  node.textContent = text;
  node.hidden = false;
  positionModsTooltip(event);
}

function hideModsTooltip() {
  document.getElementById("mods-tooltip").hidden = true;
}

function bindCellTooltip(span, text) {
  span.classList.add("has-tooltip");
  span.addEventListener("mouseenter", (event) => showModsTooltip(text, event));
  span.addEventListener("mousemove", positionModsTooltip);
  span.addEventListener("mouseleave", hideModsTooltip);
}

function renderMatrixHead() {
  const head = document.getElementById("matrix-head");
  head.innerHTML = "";
  const row = document.createElement("tr");

  const instanceTh = document.createElement("th");
  instanceTh.className = "instance-col";
  instanceTh.textContent = "Instance";
  row.appendChild(instanceTh);

  for (const computer of matrixComputers()) {
    const th = document.createElement("th");
    th.dataset.computerId = computer.id;
    if (!state.computerEnabled[computer.id]) {
      th.classList.add("col-disabled");
    }

    const wrap = document.createElement("div");
    wrap.className = "computer-toggle";

    const title = document.createElement("strong");
    title.textContent = computer.label || computer.name;
    wrap.appendChild(title);

    const toggleLabel = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = !!state.computerEnabled[computer.id];
    checkbox.addEventListener("change", () => {
      state.computerEnabled[computer.id] = checkbox.checked;
      resetModsOnlyAuto();
      renderMatrix();
      updateActionButtons();
    });
    toggleLabel.appendChild(checkbox);
    wrap.appendChild(toggleLabel);

    const reach = document.createElement("div");
    reach.className = "reachability " + (state.reachability[computer.id] || "unknown");
    reach.dataset.reachId = computer.id;
    reach.textContent = formatReachability(state.reachability[computer.id]);
    wrap.appendChild(reach);

    th.appendChild(wrap);
    row.appendChild(th);
  }

  head.appendChild(row);
}

function formatReachability(value) {
  if (!value || value === "unknown") return "unknown";
  if (value === "online") return "online";
  if (value === "offline") return "offline";
  if (value === "unconfigured") return "offline";
  if (value === "checking") return "checking…";
  return value;
}

function renderMatrixBody() {
  const body = document.getElementById("matrix-body");
  body.innerHTML = "";

  for (const row of visibleRows()) {
    const tr = document.createElement("tr");
    tr.dataset.instance = row.name;
    if (state.selected.has(row.name)) {
      tr.classList.add("selected");
    }

    tr.addEventListener("click", (event) => {
      if (event.target.type === "checkbox") {
        return;
      }
      toggleRowSelection(row.name);
      loadRowStatus(row.name);
    });

    const instanceTd = document.createElement("td");
    instanceTd.className = "instance-col";
    const cell = document.createElement("div");
    cell.className = "instance-cell";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = state.selected.has(row.name);
    checkbox.addEventListener("click", (event) => event.stopPropagation());
    checkbox.addEventListener("change", () => toggleRowSelection(row.name, checkbox.checked));
    cell.appendChild(checkbox);

    const img = document.createElement("img");
    img.src = "/api/icon/" + encodeURIComponent(row.name);
    img.alt = "";
    cell.appendChild(img);

    const name = document.createElement("span");
    name.className = "instance-name";
    name.textContent = row.display_name || row.name;
    const localTip = state.tooltipCache[instanceTooltipKey(row.name)];
    if (localTip) {
      bindCellTooltip(name, localTip);
    }
    cell.appendChild(name);

    instanceTd.appendChild(cell);
    tr.appendChild(instanceTd);

    for (const computer of matrixComputers()) {
      const td = document.createElement("td");
      if (!state.computerEnabled[computer.id]) {
        td.classList.add("col-disabled");
      }
      const status = cellStatus(row.name, computer);
      const span = document.createElement("span");
      span.className = "cell-state " + status;
      span.textContent = cellLabel(status);
      const tip = state.tooltipCache[tooltipCacheKey(row.name, computer.id)];
      if (tip) {
        bindCellTooltip(span, tip);
      }
      td.appendChild(span);
      tr.appendChild(td);
    }

    body.appendChild(tr);
  }
}

function cellStatus(instanceName, computer) {
  const reach = state.reachability[computer.id];
  if (reach === "offline" || reach === "unconfigured") {
    return reach === "offline" ? "unreachable" : "unconfigured";
  }
  return (state.status[instanceName] || {})[computer.id] || "unknown";
}

function cellLabel(status) {
  return STATUS_LABELS[status] || status;
}

function cellModsTooltip(instanceName, computer, status) {
  if (status !== "different_mods") {
    return "";
  }
  const diff = (state.modsDetail[instanceName] || {})[computer.id];
  if (!diff) {
    return "Different mod .jar filenames in mods/";
  }
  const remoteLabel = computer.label || computer.name || "target";
  const lines = [];
  const localOnly = diff.local_only || [];
  const remoteOnly = diff.remote_only || [];
  if (localOnly.length) {
    lines.push("Only on host4:");
    for (const name of localOnly) {
      lines.push("  " + name);
    }
  }
  if (remoteOnly.length) {
    lines.push("Only on " + remoteLabel + ":");
    for (const name of remoteOnly) {
      lines.push("  " + name);
    }
  }
  return lines.join("\n");
}

function renderMatrix() {
  rebuildTooltipCache();
  renderMatrixHead();
  renderMatrixBody();
}

function toggleRowSelection(name, forceValue) {
  const next = typeof forceValue === "boolean" ? forceValue : !state.selected.has(name);
  if (next) {
    state.selected.add(name);
  } else {
    state.selected.delete(name);
  }
  rebuildTooltipCache();
  renderMatrixBody();
  resetModsOnlyAuto();
  updateActionButtons();
}

async function loadConfigAndInstances() {
  state.config = await api("/api/config");
  for (const computer of state.config.computers) {
    if (computer.role === "target") {
      state.computerEnabled[computer.id] = computer.enabled;
    }
  }
  document.getElementById("filter-hide").value = (state.config.instance_filters.excludes || []).join(", ");
  document.getElementById("filter-hide-active").checked = false;
  renderExcludeChips();
  await reloadInstances();
}

async function reloadInstances() {
  const payload = await api("/api/instances?includes=&excludes=");
  state.rows = payload.instances.map((row) => ({ ...row, section: "local" }));
  state.localMods = payload.local_mods || {};
  renderMatrix();
  updateActionButtons();
}

async function refreshReachability() {
  setMessage("Checking reachability…");
  for (const computer of matrixComputers()) {
    state.reachability[computer.id] = "checking";
  }
  renderMatrixHead();
  const payload = await api("/api/reachability", {
    method: "POST",
    body: JSON.stringify({ computer_ids: targetComputerIds() }),
  });
  state.reachability = payload.reachability;
}

async function checkAllStatus() {
  const instanceNames = localRows().map((row) => row.name);
  const payload = await api("/api/status", {
    method: "POST",
    body: JSON.stringify({
      computer_ids: targetComputerIds(),
      instance_names: instanceNames,
    }),
  });
  state.rows = payload.rows.filter((row) => row.section !== "remote_only");
  state.status = payload.status;
  state.modsDetail = payload.mods_detail || {};
  state.localMods = payload.local_mods || state.localMods;
  state.reachability = payload.reachability || state.reachability;
}

async function refreshAndCheckStatus() {
  state.busy = true;
  updateActionButtons();
  setMessage("Refreshing…");
  try {
    await refreshReachability();
    setMessage("Checking instance status…");
    await checkAllStatus();
    setMessage("Refresh complete. " + westCoastTimestamp());
  } catch (err) {
    setMessage(err.message, true);
  } finally {
    state.busy = false;
    resetModsOnlyAuto();
    renderMatrix();
    updateActionButtons();
  }
}

async function loadRowStatus(instanceName) {
  setMessage("Checking " + instanceName + "…");
  try {
    const payload = await api("/api/status/instance", {
      method: "POST",
      body: JSON.stringify({
        instance_name: instanceName,
        computer_ids: targetComputerIds(),
      }),
    });
    state.status[instanceName] = payload.status;
    state.modsDetail[instanceName] = payload.mods_detail || {};
    if (payload.reachability) {
      state.reachability = { ...state.reachability, ...payload.reachability };
    }
    renderMatrix();
    setMessage("Updated status for " + instanceName + ".");
  } catch (err) {
    setMessage(err.message, true);
  }
}

function existingUpdateLines(instanceNames, computerIds) {
  const lines = [];
  for (const name of instanceNames) {
    for (const computerId of computerIds) {
      const status = (state.status[name] || {})[computerId];
      if (status !== "same_mods" && status !== "different_mods") {
        continue;
      }
      const computer = state.config.computers.find((row) => row.id === computerId);
      const label = computer ? (computer.label || computer.name) : computerId;
      lines.push(label + ": " + name);
    }
  }
  return lines;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function isPreviewAddLine(line) {
  return /^<f\+/.test(line.trimStart());
}

function isPreviewDeleteLine(line) {
  return /^\*deleting\b/.test(line.trimStart());
}

function renderSyncPreview(node, text) {
  node.innerHTML = text.split("\n").map((line) => {
    const escaped = escapeHtml(line);
    if (isPreviewAddLine(line)) {
      return `<span class="preview-add-line">${escaped}</span>`;
    }
    if (isPreviewDeleteLine(line)) {
      return `<span class="preview-delete-line">${escaped}</span>`;
    }
    return escaped;
  }).join("\n");
}

async function confirmUpdatePrompt(instanceNames, computerIds) {
  if (!document.getElementById("opt-prompt-update").checked) {
    return true;
  }
  const lines = existingUpdateLines(instanceNames, computerIds);
  if (!lines.length) {
    return true;
  }
  document.getElementById("update-prompt-text").textContent =
    "These instances already exist on target Macs and will be updated:\n\n" + lines.join("\n");
  const dialog = document.getElementById("update-prompt-dialog");
  dialog.returnValue = "cancel";
  dialog.showModal();
  const result = await new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue), { once: true });
  });
  return result === "confirm";
}

async function syncSelected() {
  const instanceNames = [...state.selected];
  const computerIds = enabledTargetIds();
  if (!instanceNames.length || !computerIds.length) {
    return;
  }
  if (!(await confirmUpdatePrompt(instanceNames, computerIds))) {
    setMessage("Push cancelled.");
    return;
  }
  const modsOnly = document.getElementById("opt-mods-only").checked;
  state.busy = true;
  updateActionButtons();
  setMessage("Building push preview…");
  try {
    const previewPayload = await api("/api/sync/preview", {
      method: "POST",
      body: JSON.stringify({
        instance_names: instanceNames,
        computer_ids: computerIds,
        update_existing: true,
        sync_icons: document.getElementById("opt-sync-icons").checked,
        mods_only: modsOnly,
        write_log: WRITE_LOG,
      }),
    });
    renderSyncPreview(document.getElementById("sync-preview-text"), previewPayload.preview);
    const dialog = document.getElementById("sync-dialog");
    dialog.returnValue = "cancel";
    dialog.showModal();
    const result = await new Promise((resolve) => {
      dialog.addEventListener("close", () => resolve(dialog.returnValue), { once: true });
    });
    if (result !== "confirm") {
      setMessage("Push cancelled.");
      return;
    }
    setMessage("Running push…");
    await api("/api/sync/apply", {
      method: "POST",
      body: JSON.stringify({
        instance_names: instanceNames,
        computer_ids: computerIds,
        update_existing: true,
        sync_icons: document.getElementById("opt-sync-icons").checked,
        mods_only: modsOnly,
        write_log: WRITE_LOG,
      }),
    });
    setMessage("Push complete. Restart Prism on target Macs.");
    await refreshAndCheckStatus();
  } catch (err) {
    setMessage(err.message, true);
  } finally {
    state.busy = false;
    updateActionButtons();
  }
}

function bindModsOnlyToggle() {
  const modsOnly = document.getElementById("opt-mods-only");
  modsOnly.addEventListener("change", () => {
    modsOnlyTouched = true;
    refreshModsOnlyUi();
  });
  refreshModsOnlyUi();
}

async function pullSelected() {
  const instanceNames = [...state.selected];
  const computerIds = enabledTargetIds();
  const items = pullableItems();
  if (!instanceNames.length || !computerIds.length || !items.length) {
    return;
  }
  state.busy = true;
  updateActionButtons();
  setMessage("Pulling mod jars…");
  try {
    const payload = await api("/api/pull/apply", {
      method: "POST",
      body: JSON.stringify({
        instance_names: instanceNames,
        computer_ids: computerIds,
      }),
    });
    await refreshReachability();
    await checkAllStatus();
    renderMatrix();
    setMessage("Pull complete.\n" + payload.result + "\nRefresh complete. " + westCoastTimestamp());
  } catch (err) {
    setMessage(err.message, true);
  } finally {
    state.busy = false;
    updateActionButtons();
  }
}

function bindEvents() {
  document.getElementById("btn-refresh").addEventListener("click", refreshAndCheckStatus);
  document.getElementById("btn-sync").addEventListener("click", syncSelected);
  document.getElementById("btn-pull").addEventListener("click", pullSelected);
  document.getElementById("filter-hide").addEventListener("change", renderMatrixBody);
  document.getElementById("filter-hide-active").addEventListener("change", renderMatrixBody);
  bindModsOnlyToggle();
}

async function init() {
  bindEvents();
  await loadConfigAndInstances();
  await refreshAndCheckStatus();
}

init();
