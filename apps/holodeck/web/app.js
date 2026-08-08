const SAMPLE_MODE = new URLSearchParams(window.location.search).get("src") === "sample";
const SAMPLE_URL = new URL("sample-snapshot.json", import.meta.url);
const SAMPLE_STATE_URL = new URL("sample-state.json", import.meta.url);
const SAMPLE_TURNS_URL = new URL("sample-turns.json", import.meta.url);
const SAMPLE_TURN_STATUS_URL = new URL("sample-turn-status.json", import.meta.url);
const SAMPLE_AGENTS_URL = new URL("sample-agents.json", import.meta.url);
const PLATFORM_META = {
  claude: { label: "Claude", cls: "claude" },
  codex: { label: "Codex", cls: "codex" },
  cursor: { label: "Cursor", cls: "cursor" },
  "git-commit": { label: "git-commit", cls: "git-commit" },
};
const AI_INTERFACES = {
  cursor: { label: "Cursor IDE", cls: "cursor" },
  "claude-cli": { label: "Claude CLI", cls: "claude" },
  "claude-app": { label: "Claude App", cls: "claude" },
  "codex-cli": { label: "Codex CLI", cls: "codex" },
  "codex-app": { label: "Codex App", cls: "codex" },
};
const ENTRYPOINT_META = {
  cli: "CLI",
  app: "App",
  ide: "IDE",
  subagent: "Subagent",
};
const CLOUD_SOURCE_META = {
  "codex-cloud": {
    label: "Codex cloud",
    expired: "Codex cloud token expired — run `codex cloud list` or `codex login` to refresh.",
    absent: "Codex cloud token absent — run `codex login` to enable cloud transcripts.",
  },
  "claude-cloud": {
    label: "Claude cloud",
    expired: "Claude cloud needs a browser export — copy the Holodeck snippet, paste it in the DevTools console on https://claude.ai/code, save the download, then hit Refresh.",
    absent: "Claude cloud needs a browser export — copy the Holodeck snippet, paste it in the DevTools console on https://claude.ai/code, save the download, then hit Refresh.",
    blocked: "Claude cloud needs a browser export — copy the Holodeck snippet, paste it in the DevTools console on https://claude.ai/code, save the download, then hit Refresh.",
  },
};
const CLAUDE_EXPORT_SNIPPET_URL = new URL("claude-cloud-export-snippet.js", import.meta.url);
const PRIMARY_INTERFACE_OPTIONS = [
  ["", "—"],
  ["cursor", "Cursor IDE"],
  ["claude-cli", "Claude CLI"],
  ["claude-app", "Claude App"],
  ["codex-cli", "Codex CLI"],
  ["codex-app", "Codex App"],
];
// Keep the manually maintained selector available without showing it in every
// worktree card. Turn this on when the primary-interface workflow is revisited.
const SHOW_PRIMARY_AI_INTERFACE = false;
const KIND_LABELS = {
  fly: "Fly.io",
  chalice: "AWS Chalice",
  webflow: "Webflow",
  s3: "S3",
};
const TURN_KIND_META = {
  primary: { label: "primary", cls: "gold" },
  quick: { label: "quick", cls: "" },
  info: { label: "info", cls: "teal" },
};
const AGENT_STATE_META = {
  thinking: { label: "thinking", cls: "thinking" },
  "needs-you": { label: "needs you", cls: "needs-you" },
  done: { label: "done", cls: "done" },
  error: { label: "error", cls: "error" },
};
const STAGE_META = {
  "s0-experiment": { label: "s0-experiment", cls: "stage-s0" },
  "s1-dev": { label: "s1-dev", cls: "stage-s1" },
  "s2-deployed": { label: "s2-deployed", cls: "stage-s2" },
  "s3-real": { label: "s3-real", cls: "stage-s3" },
};
const SPEC_STAGE_META = {
  "readme-only": { label: "readme-only", cls: "spec-readme" },
  "openspec-single-spec": { label: "openspec-single-spec", cls: "spec-single" },
  "openspec-core": { label: "openspec-core", cls: "spec-core" },
  "openspec-strict": { label: "openspec-strict", cls: "spec-strict" },
};
const DONE_STATUS = ["none", "needs-review", "reviewed", "tested"];
const FILE_SUFFIXES = [".md", ".yaml", ".yml", ".json", ".txt", ".py", ".js", ".mjs", ".html", ".css", ".toml", ".sh"];
const AGENT_FILTER_PREF_KEY = "holodeck-agent-platforms";
const HIDDEN_AGENTS_PREF_KEY = "holodeck-hidden-agents";
const BRANCH_TIMELINE_SORT_PREF_KEY = "holodeck-branch-timeline-sort";
const BRANCH_VALIDATION_PREF_KEY = "holodeck-branch-validation-visible";
const AGENT_FILTER_KEYS = ["claude", "codex", "cursor"];
let branchTimelineEdgeObserver = null;
const state = {
  snapshot: null,
  agents: [],
  agentsGeneratedAt: null,
  agentPollInFlight: false,
  agentFilter: { claude: true, codex: true, cursor: true },
  hiddenAgents: readHiddenAgentsPreference(),
  branchTimelineSort: readBranchTimelineSortPreference(),
  branchValidationVisible: readBranchValidationPreference(),
  deckShowAll: false,
  turnStatus: [],
  userState: emptyUserState(),
  appFilter: { kind: "all", tag: "all", q: "" },
  sessionFilter: { platform: "all", q: "", machinery: false },
  observer: null,
  expandedWorktrees: new Set(),
  expandedApps: new Set(),
  draggingBranch: null,
  draggingNextStepId: null,
  draggingWorktreeStep: null,
  stateWarning: "",
  filePayload: null,
  colorRules: null,
  fileEditing: false,
  sessionDrawer: emptySessionDrawer(),
  sampleTurns: null,
  commitDrawer: { branch: "", commits: [], skip: 0, hasMore: false, loading: false },
  cloudStatus: null,
  cloudStatusDismissed: false,
  aiSyncStatus: null,
  aiSyncDismissed: false,
  aiSyncPollToken: 0,
  aiSyncDismissTimer: 0,
  refreshPollToken: 0,
  dismissedNotices: [],
  layerWarningDismissedKey: "",
  todoArchiveOpen: false,
  todoArchiveItems: null,
  todoArchiveLoading: false,
  todoArchiveError: "",
};
const ACTIVITY_PREF_KEY = "holodeck-show-latest-activity";
const AI_SYNC_AUTO_DISMISS_MS = 3000;
const ids = {
  status: "snapshot-status",
  timestamp: "snapshot-timestamp",
  aiSync: "ai-sync-status",
  sideTooltip: "side-snapshot-tooltip",
  refresh: "refresh-btn",
  cloudAuth: "cloud-auth-banner",
  warning: "warning-strip",
  error: "error-panel",
  deckSummary: "deck-summary",
  agentPlatformFilter: "agent-platform-filter",
  agentDeck: "agent-deck",
  agentDeckToggle: "agent-deck-toggle",
  universeStats: "universe-stats",
  universeParked: "universe-parked",
  universeBranches: "universe-branches",
  todoRoot: "todo-root",
  todoMode: "todo-mode",
  activity: "activity-feed",
  activityCard: "activity-card",
  activityToggle: "activity-toggle",
  worktrees: "worktree-cards",
  branchTimeline: "branch-timeline",
  branchTimelineStatus: "branch-timeline-status",
  branchTimelineLegend: "branch-timeline-legend",
  branchSortDate: "branch-sort-date",
  branchSortAlphabetical: "branch-sort-alphabetical",
  branchValidationToggle: "branch-validation-toggle",
  appFilters: "app-filterbar",
  apps: "app-cards",
  core: "core-table",
  specs: "spec-cards",
  skills: "skill-groups",
  sessionFilters: "session-filterbar",
  sessions: "sessions-table",
  deploy: "deploy-groups",
  drawer: "session-drawer",
  backdrop: "session-backdrop",
  drawerTool: "drawer-tool",
  drawerTitle: "drawer-title",
  drawerBody: "drawer-body",
  drawerClose: "drawer-close",
  drawerJumpEnd: "drawer-jump-end",
  fileDrawer: "file-drawer",
  fileBackdrop: "file-backdrop",
  fileDrawerStatus: "file-drawer-status",
  fileDrawerTitle: "file-drawer-title",
  fileDrawerBody: "file-drawer-body",
  fileDrawerClose: "file-drawer-close",
  commitDrawer: "commit-drawer",
  commitBackdrop: "commit-backdrop",
  commitDrawerStatus: "commit-drawer-status",
  commitDrawerTitle: "commit-drawer-title",
  commitDrawerBody: "commit-drawer-body",
  commitDrawerClose: "commit-drawer-close",
};
function byId(id) {
  return document.getElementById(id);
}
function clean(value) {
  if (value === null || value === undefined) return "";
  return String(value);
}
function hasValue(value) {
  return value !== null && value !== undefined && String(value).trim() !== "";
}
function arr(value) {
  return Array.isArray(value) ? value : [];
}
function obj(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}
function clear(node) {
  if (!node) return;
  while (node.firstChild) node.removeChild(node.firstChild);
}
function el(tagName, className, text) {
  const node = document.createElement(tagName);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}
function append(parent, ...children) {
  children.flat().forEach((child) => {
    if (child) parent.appendChild(child);
  });
  return parent;
}
function textNode(text) {
  return document.createTextNode(clean(text));
}
function link(label, href, className) {
  if (!hasValue(label)) return null;
  const node = el("a", className || "", label);
  node.href = href || "#";
  return node;
}
function button(label, className) {
  const node = el("button", className || "", label);
  node.type = "button";
  return node;
}
function fillWrapLabel(node, label) {
  clear(node);
  const text = String(label ?? "");
  const parts = text.split(/([\/\-])/);
  parts.forEach((part, index) => {
    if (!part) return;
    node.appendChild(document.createTextNode(part));
    if ((part === "/" || part === "-") && index < parts.length - 1) {
      node.appendChild(document.createElement("wbr"));
    }
  });
  return node;
}
function chip(text, extraClass) {
  if (!hasValue(text)) return null;
  return el("span", `pill${extraClass ? ` ${extraClass}` : ""}`, text);
}
function tag(text) {
  if (!hasValue(text)) return null;
  return el("span", "tag", text);
}
function dot(colorClass) {
  return el("span", `dot ${colorClass || ""}`);
}
function safeId(value) {
  return clean(value).toLowerCase().replace(/[^a-z0-9_-]+/g, "-").replace(/^-+|-+$/g, "") || "item";
}
function isDetachedBranch(branch) {
  const value = clean(branch);
  return !value || value === "detached";
}
function worktreeKey(wt) {
  const branch = clean(wt && wt.branch);
  if (isDetachedBranch(branch)) return basename(wt && wt.path) || "detached";
  return branch;
}
function worktreeFolderName(wt) {
  if (isDetachedBranch(wt && wt.branch)) return basename(wt && wt.path) || clean(wt && wt.name) || "worktree";
  return clean(wt.name) || basename(wt.path) || "worktree";
}
function colorFromDisplayRules(displayName, branchName) {
  const name = clean(displayName);
  if (!name) return null;
  const rules = branchColorRules();
  const bare = clean(branchName);
  for (const rule of arr(rules.rules)) {
    if (!colorRulesMatch(name, bare, rule)) continue;
    const background = clean(rule.background);
    if (!background) continue;
    return {
      background,
      foreground: clean(rule.foreground) || clean(rules.foreground) || "#ffffff",
    };
  }
  return null;
}
function worktreeTitleBarColors(wt) {
  // Prefer worktree-colors.yaml matched to the folder identity. Snapshot title_bar can
  // stay stale (or wrong) after a leftover minecraft workspace renamed/painted a parked card.
  const folder = worktreeFolderName(wt);
  const branch = clean(wt && wt.branch);
  const fromFolder = colorFromDisplayRules(folder, branch);
  if (fromFolder) return fromFolder;
  if (!isDetachedBranch(branch)) {
    const fromName = colorFromDisplayRules(clean(wt && wt.name) || folder, branch);
    if (fromName) return fromName;
  }
  const bar = obj(wt && wt.title_bar);
  return {
    background: clean(bar.background) || "#245f99",
    foreground: clean(bar.foreground) || "#ffffff",
  };
}
function worktreeColorButton(wt, className) {
  const colors = worktreeTitleBarColors(wt);
  const node = button(worktreeFolderName(wt), className || "worktree-color-chip");
  node.style.background = colors.background;
  node.style.color = colors.foreground;
  node.style.borderColor = colors.background;
  node.title = clean(wt.branch) ? `branch: ${clean(wt.branch)}` : worktreeFolderName(wt);
  return node;
}
function worktreeColorChip(wt, className) {
  const colors = worktreeTitleBarColors(wt);
  const node = el("span", className || "worktree-color-chip", worktreeFolderName(wt));
  node.style.background = colors.background;
  node.style.color = colors.foreground;
  node.style.borderColor = colors.background;
  node.title = clean(wt && wt.branch) ? `branch: ${clean(wt.branch)}` : worktreeFolderName(wt);
  return node;
}
function worktreeBranchTextColor(wt) {
  return clean(worktreeTitleBarColors(wt).background) || "";
}
function branchColorRules() {
  const meta = obj(state.snapshot && state.snapshot.layer_meta && state.snapshot.layer_meta.branches);
  if (meta.color_rules && arr(meta.color_rules.rules).length) return meta.color_rules;
  return state.colorRules || { foreground: "#ffffff", rules: [] };
}
function normalizeColorToken(value) {
  return clean(value).toLowerCase();
}
function colorRulesMatch(displayName, branchName, rule) {
  const name = normalizeColorToken(displayName);
  const branch = normalizeColorToken(branchName);
  const exact = rule.name_exact;
  if (exact && name !== normalizeColorToken(exact)) return false;
  if (rule.branch && branch !== normalizeColorToken(rule.branch)) return false;
  if (rule.name_contains && !name.includes(normalizeColorToken(rule.name_contains))) return false;
  for (const token of arr(rule.name_contains_all)) {
    if (!name.includes(normalizeColorToken(token))) return false;
  }
  return true;
}
function colorFromBranchRules(branchName) {
  const bare = clean(branchName).replace(/^origin\//, "");
  if (!bare) return null;
  const rules = branchColorRules();
  const list = arr(rules.rules);
  for (const display of [bare, bare.replace(/\//g, "-")]) {
    for (const rule of list) {
      if (!colorRulesMatch(display, bare, rule)) continue;
      if (clean(rule.background)) {
        return {
          background: clean(rule.background),
          foreground: clean(rule.foreground) || clean(rules.foreground) || "#ffffff",
        };
      }
    }
  }
  if (normalizeColorToken(bare) === "main") {
    for (const rule of list) {
      if (normalizeColorToken(rule.branch) === "main" && clean(rule.background)) {
        return {
          background: clean(rule.background),
          foreground: clean(rule.foreground) || clean(rules.foreground) || "#ffffff",
        };
      }
    }
  }
  return null;
}
function branchAssignedColors(branchName) {
  const name = clean(branchName).replace(/^origin\//, "");
  if (!name) return null;
  const wt = worktreeForBranch(name);
  if (wt) {
    const fromWt = worktreeTitleBarColors(wt);
    if (clean(fromWt.background)) return fromWt;
  }
  const branch = getLayer("branches").find((item) => clean(item.name) === name);
  const fromBranch = obj(branch && branch.title_bar);
  if (clean(fromBranch.background)) {
    return {
      background: clean(fromBranch.background),
      foreground: clean(fromBranch.foreground) || clean(branchColorRules().foreground) || "#ffffff",
    };
  }
  return colorFromBranchRules(name);
}
function branchAssignedColor(branchName) {
  return clean(obj(branchAssignedColors(branchName)).background);
}
function branchColorForName(branchName) {
  const assigned = branchAssignedColor(branchName);
  return assigned ? readableBranchColor(assigned) : "";
}
function shortBranchName(branch) {
  return clean(branch).replace(/^(feature|fix|refactor|cleanup|hotfix|release|use|import|export)\//, "") || "branch";
}
function branchIdentityPill(branch, wt, extraClass) {
  if (!hasValue(branch)) return null;
  const node = chip(shortBranchName(branch), `branch-identity${extraClass ? ` ${extraClass}` : ""}`);
  applyBranchIdentityStyles(node, wt);
  node.title = clean(branch);
  return node;
}
function branchIdentityButton(branch, wt, extraClass) {
  if (!hasValue(branch)) return null;
  const node = button(shortBranchName(branch), `pill branch-identity${extraClass ? ` ${extraClass}` : ""}`);
  applyBranchIdentityStyles(node, wt);
  node.title = clean(branch);
  return node;
}
function applyBranchIdentityStyles(node, wt) {
  if (wt) {
    const color = worktreeTitleBarColors(wt).background;
    node.style.color = color;
    node.style.borderColor = color;
    const bg = hexToRgba(color, 0.12);
    if (bg) node.style.background = bg;
  }
  return node;
}
function hexToRgba(value, alpha) {
  const match = clean(value).match(/^#([0-9a-f]{6})$/i);
  if (!match) return "";
  const n = Number.parseInt(match[1], 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${Number(alpha) || 0})`;
}
function wtIsCursorOpen(wt) {
  return wt.cursor_open === true;
}
function basename(path) {
  const value = clean(path).replace(/\/+$/, "");
  if (!value) return "";
  return value.split("/").pop() || value;
}
function dirname(path) {
  const value = clean(path).replace(/\/+$/, "");
  const parts = value.split("/");
  parts.pop();
  return parts.join("/");
}
function joinPath(base, suffix) {
  return `${clean(base).replace(/\/+$/, "")}/${clean(suffix).replace(/^\/+/, "")}`;
}
function trunc(text, limit) {
  const value = clean(text).trim();
  if (value.length <= limit) return value;
  return `${value.slice(0, Math.max(0, limit - 1))}…`;
}
function norm(text) {
  return clean(text).toLowerCase();
}
function parseDate(value) {
  if (!hasValue(value)) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}
function relativeTime(value) {
  const date = parseDate(value);
  if (!date) return "";
  const diffMs = Date.now() - date.getTime();
  const future = diffMs < -30000;
  const absSec = Math.max(0, Math.abs(diffMs) / 1000);
  if (absSec < 60) return future ? "in 0m" : "0m ago";
  const units = [
    ["y", 31536000],
    ["mo", 2592000],
    ["d", 86400],
    ["h", 3600],
    ["m", 60],
  ];
  const found = units.find(([, seconds]) => absSec >= seconds) || ["m", 60];
  const valueOut = Math.floor(absSec / found[1]);
  return future ? `in ${valueOut}${found[0]}` : `${valueOut}${found[0]} ago`;
}
function localTimestamp(value) {
  const date = parseDate(value);
  if (!date) return clean(value);
  const pad = (number) => String(number).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
function localDateOnly(value) {
  const date = parseDate(value);
  if (!date) {
    const text = clean(value);
    return text.length >= 10 ? text.slice(0, 10) : text;
  }
  const pad = (number) => String(number).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}
function timeNode(value, fallback) {
  const span = el("span", "", relativeTime(value) || fallback || "");
  if (hasValue(value)) span.title = localTimestamp(value) || clean(value);
  return span;
}
function asCount(value) {
  return Number.isFinite(Number(value)) ? Number(value) : 0;
}
function getLayers() {
  return obj(state.snapshot && state.snapshot.layers);
}
function getLayer(name) {
  return arr(getLayers()[name]);
}
const LAYER_LABELS = {
  worktrees: "Worktrees",
  branches: "Branches",
  apps: "Apps",
  core: "Core",
  skills: "Skills",
  specs: "Specs",
  sessions: "AI Sessions",
  deploy: "Deploy",
  state: "State",
};
function layerLabel(name) {
  const key = clean(name);
  return LAYER_LABELS[key] || key || "Refresh";
}
function getLayerErrors() {
  return Object.entries(obj(state.snapshot && state.snapshot.layer_meta))
    .filter(([, meta]) => hasValue(obj(meta).error))
    .map(([name, meta]) => ({ name, error: clean(obj(meta).error) }));
}
function formatLayerError(item) {
  const name = clean(item && item.name);
  let error = clean(item && item.error);
  const lowered = error.toLowerCase();
  if (lowered.includes("timed out after") && (lowered.includes("gh") || lowered.includes("pr list") || lowered.includes("pull-request"))) {
    error = "PR data may be stale — GitHub pull-request lookup timed out. Branch names and commits from this refresh should still be current; PR badges may be from an earlier successful fetch.";
  } else if (lowered.includes("rate limit") || lowered.includes("api rate limit already exceeded")) {
    error = "PR data unavailable — GitHub API rate limit hit. Branch names and commits from this refresh are current; PR badges can't update until the limit resets (often a few hours).";
  } else if (lowered.includes("command '[") && lowered.includes("timed out")) {
    error = `A refresh helper timed out. ${error}`;
  }
  return { name, label: layerLabel(name), error };
}
function layerWarningKey(errors) {
  return errors.map((item) => `${item.name}:${item.error}`).join("|");
}
function layerNoticeItems() {
  return getLayerErrors().map(formatLayerError).filter((item) => hasValue(item.error)).map((item) => ({
    key: `layer:${item.name}`,
    text: `${item.label}: ${item.error}`,
    tone: "error",
  }));
}
function emptyUserState() {
  return { updated_at: null, next_steps: [], worktrees: {} };
}
function emptySessionDrawer() {
  return {
    session: null,
    key: "",
    turns: null,
    turnsLoading: false,
    turnsError: "",
    subagents: null,
    subagentsOpen: false,
    subagentsFetched: false,
    subagentsLoading: false,
    subagentsError: "",
    messages: null,
    messagesLoading: false,
    messagesError: "",
    digesting: new Set(),
    digestErrors: {},
  };
}
function defaultAgentFilter() {
  return { claude: true, codex: true, cursor: true };
}
function readAgentFilterPreference() {
  const fallback = defaultAgentFilter();
  try {
    const parsed = JSON.parse(window.localStorage.getItem(AGENT_FILTER_PREF_KEY) || "");
    return AGENT_FILTER_KEYS.reduce((memo, key) => {
      memo[key] = parsed && parsed[key] === false ? false : true;
      return memo;
    }, fallback);
  } catch (error) {
    return fallback;
  }
}
function persistAgentFilterPreference() {
  try {
    window.localStorage.setItem(AGENT_FILTER_PREF_KEY, JSON.stringify(state.agentFilter));
  } catch (error) {}
}
function readHiddenAgentsPreference() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(HIDDEN_AGENTS_PREF_KEY) || "[]");
    return new Set(arr(parsed).map(clean).filter(Boolean));
  } catch (error) {
    return new Set();
  }
}
function persistHiddenAgentsPreference() {
  try {
    window.localStorage.setItem(HIDDEN_AGENTS_PREF_KEY, JSON.stringify([...state.hiddenAgents]));
  } catch (error) {}
}
function readBranchTimelineSortPreference() {
  try {
    return window.localStorage.getItem(BRANCH_TIMELINE_SORT_PREF_KEY) === "alphabetical"
      ? "alphabetical"
      : "date";
  } catch (error) {
    return "date";
  }
}
function readBranchValidationPreference() {
  try {
    return window.localStorage.getItem(BRANCH_VALIDATION_PREF_KEY) === "true";
  } catch (error) {
    return false;
  }
}
function setBranchTimelineSort(mode) {
  state.branchTimelineSort = mode === "alphabetical" ? "alphabetical" : "date";
  try {
    window.localStorage.setItem(BRANCH_TIMELINE_SORT_PREF_KEY, state.branchTimelineSort);
  } catch (error) {}
  renderBranches();
}
function setBranchValidationVisible(visible) {
  state.branchValidationVisible = visible === true;
  try {
    window.localStorage.setItem(BRANCH_VALIDATION_PREF_KEY, String(state.branchValidationVisible));
  } catch (error) {}
  renderBranches();
}
function updateBranchTimelineControls() {
  const dateButton = byId(ids.branchSortDate);
  const alphabeticalButton = byId(ids.branchSortAlphabetical);
  const validationButton = byId(ids.branchValidationToggle);
  if (dateButton) dateButton.setAttribute("aria-pressed", String(state.branchTimelineSort === "date"));
  if (alphabeticalButton) {
    alphabeticalButton.setAttribute("aria-pressed", String(state.branchTimelineSort === "alphabetical"));
  }
  if (validationButton) {
    validationButton.setAttribute("aria-expanded", String(state.branchValidationVisible));
    validationButton.textContent = state.branchValidationVisible
      ? "Hide validation details"
      : "Show validation details";
  }
}
function agentExchangeId(agent) {
  return clean(agent && agent.exchange_id);
}
function agentIsHidden(agent) {
  const id = agentExchangeId(agent);
  return id ? state.hiddenAgents.has(id) : false;
}
function pruneHiddenAgents(agents) {
  const fetched = new Set(arr(agents).map(agentExchangeId).filter(Boolean));
  let changed = false;
  [...state.hiddenAgents].forEach((id) => {
    if (!fetched.has(id)) {
      state.hiddenAgents.delete(id);
      changed = true;
    }
  });
  if (changed) persistHiddenAgentsPreference();
}
function normalizeStepItem(item) {
  const entry = obj(item);
  return {
    id: clean(entry.id),
    text: clean(entry.text),
    done: entry.done === true,
    created_at: clean(entry.created_at),
    source: hasValue(entry.source) ? clean(entry.source) : null,
  };
}
function normalizeStepList(value) {
  return arr(value).map(normalizeStepItem).filter((item) => hasValue(item.id));
}
function normalizeUserState(value) {
  const data = obj(value);
  return {
    updated_at: data.updated_at || null,
    next_steps: normalizeStepList(data.next_steps),
    worktrees: obj(data.worktrees),
  };
}
function normalizeTurnStatus(value) {
  const data = obj(value);
  const rows = Array.isArray(value) ? value : arr(data.statuses || data.items || data.worktrees || data.rows);
  return rows.map((row) => obj(row)).filter((row) => Object.keys(row).length);
}
function worktreeState(branch) {
  const entry = obj(state.userState.worktrees[branch]);
  const primaryInterface = clean(entry.primary_interface);
  return {
    active: entry.active !== false,
    order: Number.isFinite(Number(entry.order)) ? Number(entry.order) : null,
    deactivated_at: hasValue(entry.deactivated_at) ? clean(entry.deactivated_at) : null,
    next_step: hasValue(entry.next_step) ? clean(entry.next_step) : "",
    last_done: hasValue(entry.last_done) ? clean(entry.last_done) : "",
    last_done_status: DONE_STATUS.includes(clean(entry.last_done_status)) ? clean(entry.last_done_status) : "none",
    notes: hasValue(entry.notes) ? clean(entry.notes) : "",
    primary_interface: AI_INTERFACES[primaryInterface] ? primaryInterface : null,
    steps: normalizeStepList(entry.steps),
  };
}
function setLocalWorktreeState(branch, patch) {
  state.userState.worktrees[branch] = { ...obj(state.userState.worktrees[branch]), ...patch };
}
function clientId(prefix) {
  const base = window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID().replace(/-/g, "") : `${Date.now().toString(16)}${Math.random().toString(16).slice(2)}`;
  return `${prefix || "item"}-${base.slice(0, 12)}`;
}
function newStep(text) {
  return { id: clientId("step"), text: clean(text).trim(), done: false, created_at: new Date().toISOString() };
}
async function copyText(text) {
  const value = clean(text);
  if (!value) return;
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const area = el("textarea");
  area.value = value;
  area.style.position = "fixed";
  area.style.left = "-9999px";
  document.body.appendChild(area);
  area.focus();
  area.select();
  document.execCommand("copy");
  area.remove();
}
function copyButton(value, label) {
  if (!hasValue(value)) return null;
  const btn = button(label || "copy", "copy-btn");
  btn.addEventListener("click", async (event) => {
    event.preventDefault();
    event.stopPropagation();
    const original = btn.textContent;
    try {
      await copyText(value);
      btn.textContent = "copied";
    } catch (error) {
      btn.textContent = "failed";
    }
    window.setTimeout(() => {
      btn.textContent = original;
    }, 950);
  });
  return btn;
}
function commandBlock(command, label) {
  if (!hasValue(command)) return null;
  const block = el("div", "cmd-block");
  const code = el("code", "", command);
  append(block, code, copyButton(command, label || "copy"));
  return block;
}
function tableCell(...children) {
  const td = el("td");
  append(td, children);
  return td;
}
function tableRow(cells, className) {
  const tr = el("tr", className || "");
  cells.forEach((cell) => tr.appendChild(cell));
  return tr;
}
function emptyState(text) {
  return el("div", "empty", text);
}
function init() {
  state.agentFilter = readAgentFilterPreference();
  byId(ids.refresh).addEventListener("click", refreshSnapshot);
  byId(ids.drawerClose).addEventListener("click", closeSessionDrawer);
  byId(ids.drawerJumpEnd).addEventListener("click", scrollSessionDrawerToEnd);
  byId(ids.backdrop).addEventListener("click", closeSessionDrawer);
  byId(ids.fileDrawerClose).addEventListener("click", closeFileDrawer);
  byId(ids.fileBackdrop).addEventListener("click", closeFileDrawer);
  byId(ids.commitDrawerClose).addEventListener("click", closeCommitDrawer);
  byId(ids.commitBackdrop).addEventListener("click", closeCommitDrawer);
  byId(ids.activityToggle).addEventListener("click", () => setActivityVisible(!activityVisible()));
  byId(ids.branchSortDate).addEventListener("click", () => setBranchTimelineSort("date"));
  byId(ids.branchSortAlphabetical).addEventListener("click", () => setBranchTimelineSort("alphabetical"));
  byId(ids.branchValidationToggle).addEventListener("click", () => {
    setBranchValidationVisible(!state.branchValidationVisible);
  });
  updateBranchTimelineControls();
  applyActivityVisibility();
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeSessionDrawer();
      closeFileDrawer();
      closeCommitDrawer();
    }
  });
  if (SAMPLE_MODE) {
    const btn = byId(ids.refresh);
    btn.textContent = "Sample data";
    btn.disabled = true;
    btn.title = "Refresh is disabled in sample mode";
  }
  bindSideSnapshotTooltip();
  if (!SAMPLE_MODE) {
    loadCloudStatus();
    adoptRunningRefresh();
  }
  loadSnapshot();
  startAgentPolling();
}
async function fetchJson(url, options) {
  const response = await fetch(url, options || { cache: "no-store" });
  if (!response.ok) {
    let body = "";
    try {
      body = await response.text();
    } catch (error) {
      body = "";
    }
    throw new Error(`Request failed (${response.status})${body ? `: ${body}` : ""}`);
  }
  return response.json();
}
async function loadCloudStatus() {
  if (SAMPLE_MODE) return;
  try {
    state.cloudStatus = await fetchJson("/api/cloud-status", { cache: "no-store" });
  } catch (error) {
    state.cloudStatus = { sources: [] };
  }
  renderCloudStatusBanner();
}
async function loadAgents() {
  try {
    const payload = await fetchJson(SAMPLE_MODE ? SAMPLE_AGENTS_URL : "/api/agents?hours=72&limit=32", { cache: "no-store" });
    state.agents = arr(payload && payload.agents).map((agent) => obj(agent));
    state.agentsGeneratedAt = clean(payload && payload.generated_at) || null;
    pruneHiddenAgents(state.agents);
  } catch (error) {
    state.agents = [];
    state.agentsGeneratedAt = null;
  }
  return state.agents;
}
async function loadTurnStatus() {
  const payload = await fetchJson(SAMPLE_MODE ? SAMPLE_TURN_STATUS_URL : "/api/turns/status", { cache: "no-store" });
  state.turnStatus = normalizeTurnStatus(payload);
  return state.turnStatus;
}
function activeInputInActiveWork() {
  const active = document.activeElement;
  return active && active.closest && active.closest("#active") && ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName);
}
function startAgentPolling() {
  if (SAMPLE_MODE) return;
  window.setInterval(pollAgentSurfaces, 60000);
}
async function pollAgentSurfaces() {
  if (state.agentPollInFlight) return;
  state.agentPollInFlight = true;
  try {
    await Promise.all([
      loadAgents(),
      loadTurnStatus().catch(() => {
        state.turnStatus = [];
        return [];
      }),
    ]);
    if (activeInputInActiveWork()) return;
    renderAgentDeck();
    renderWorktreeLivePanels();
    renderSessions();
    if (state.sessionDrawer && state.sessionDrawer.session) {
      setSessionDrawerTitle(state.sessionDrawer.session);
    }
  } finally {
    state.agentPollInFlight = false;
  }
}
function normalizeCloudSource(value) {
  const source = obj(value);
  return {
    key: clean(source.key),
    state: clean(source.state),
    detail: clean(source.detail),
  };
}
function cloudSourceMessage(source) {
  const meta = CLOUD_SOURCE_META[source.key] || { label: source.key || "Cloud auth" };
  if (hasValue(source.detail)) return source.detail;
  if (source.state === "expired") return meta.expired || `${meta.label} expired.`;
  if (source.state === "absent") return meta.absent || `${meta.label} is not configured.`;
  if (source.state === "blocked") return meta.blocked || meta.absent || `${meta.label} needs a browser export.`;
  return "";
}
function cloudSourceNeedsAttention(source) {
  return source.state === "expired" || source.state === "absent" || source.state === "blocked";
}
function cloudSourceIsCodexAlarm(source) {
  return source.key === "codex-cloud" && source.state === "expired";
}
async function copyClaudeExportSnippet(buttonNode) {
  const original = buttonNode.textContent;
  try {
    const response = await fetch(CLAUDE_EXPORT_SNIPPET_URL, { cache: "no-store" });
    if (!response.ok) throw new Error("snippet fetch failed");
    await copyText(await response.text());
    buttonNode.textContent = "copied";
  } catch (error) {
    buttonNode.textContent = "failed";
  }
  window.setTimeout(() => {
    buttonNode.textContent = original;
  }, 1200);
}
function renderCloudStatusBanner() {
  const banner = byId(ids.cloudAuth);
  if (!banner) return;
  clear(banner);
  banner.className = "cloud-auth-banner hidden";
  if (SAMPLE_MODE || state.cloudStatusDismissed) return;
  const sources = arr(obj(state.cloudStatus).sources).map(normalizeCloudSource).filter((source) => hasValue(source.key));
  const attention = sources.filter(cloudSourceNeedsAttention);
  if (!attention.length) return;
  const subtle = !attention.some(cloudSourceIsCodexAlarm);
  const messages = attention.map(cloudSourceMessage).filter(hasValue);
  if (!messages.length) return;
  const needsClaudeExport = attention.some((source) => source.key === "claude-cloud");
  banner.className = `cloud-auth-banner${subtle ? " subtle" : ""}`;
  const body = el("div", "cloud-auth-banner-body");
  append(body, el("strong", "", subtle ? "Cloud sync" : "Cloud auth attention"));
  messages.forEach((message, index) => {
    if (index) append(body, textNode(" "));
    append(body, el("span", "cloud-auth-item", message));
  });
  const actions = el("div", "cloud-auth-actions");
  if (needsClaudeExport) {
    const copySnippet = button("Copy Claude export snippet", "copy-btn");
    copySnippet.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      copyClaudeExportSnippet(copySnippet);
    });
    append(actions, copySnippet);
  }
  const dismiss = button("Dismiss", "copy-btn");
  dismiss.addEventListener("click", () => {
    rememberDismissedNotice("cloud", messages.join(" "), "error");
    state.cloudStatusDismissed = true;
    renderCloudStatusBanner();
  });
  append(actions, dismiss);
  append(banner, body, actions);
}
function normalizeAiSyncStatus(value) {
  const data = obj(value);
  return {
    ok: data.ok === true ? true : data.ok === false ? false : null,
    status: clean(data.status),
    running: data.running === true,
    message: clean(data.message),
    downloads_moved: asCount(data.downloads_moved || obj(data.downloads).moved),
    downloads: obj(data.downloads),
    turns: obj(data.turns),
    s3: obj(data.s3),
    already_running: data.already_running === true,
  };
}
function aiSyncErrorText(sync) {
  const downloads = obj(sync.downloads);
  const turns = obj(sync.turns);
  const s3 = obj(sync.s3);
  if (hasValue(downloads.error)) return `AI sessions sync error: ${downloads.error}`;
  if (turns.ok === false || hasValue(turns.error)) return `AI sessions turns error: ${clean(turns.error) || "rebuild failed"}`;
  if (s3.ok === false || hasValue(s3.error)) return `AI sessions S3 error: ${clean(s3.error) || trunc(clean(s3.tail), 160) || "sync failed"}`;
  return clean(sync.message) || "AI sessions sync error.";
}
function aiSyncResultText(syncValue) {
  const sync = normalizeAiSyncStatus(syncValue);
  if (sync.running) return sync.already_running ? "AI sessions already syncing." : sync.message === "AI sessions still syncing." ? sync.message : "AI sessions syncing.";
  if (sync.ok === true) {
    const codex = asCount(sync.turns.cloud_tasks);
    const imported = sync.downloads_moved;
    const s3Mark = obj(sync.s3).ok === true ? "S3 ✓" : "S3 skipped";
    return `AI sessions synced — ${codex} codex cloud, imported ${imported} claude export${imported === 1 ? "" : "s"}, ${s3Mark}`;
  }
  if (sync.ok === false || sync.status === "error") return aiSyncErrorText(sync);
  return clean(sync.message);
}
function noticeToneForSync(sync) {
  if (sync.ok === true) return "success";
  if (sync.ok === false || sync.status === "error") return "error";
  return "";
}
function rememberDismissedNotice(key, text, tone) {
  const message = clean(text);
  if (!hasValue(message)) return;
  const next = arr(state.dismissedNotices).filter((item) => item.key !== key);
  next.push({ key, text: message, tone: clean(tone) });
  state.dismissedNotices = next;
  renderSideSnapshotTooltip();
}
function clearDismissedNotices() {
  state.dismissedNotices = [];
  renderSideSnapshotTooltip();
}
function clearAiSyncDismissTimer() {
  if (state.aiSyncDismissTimer) {
    window.clearTimeout(state.aiSyncDismissTimer);
    state.aiSyncDismissTimer = 0;
  }
}
function dismissAiSyncNotice() {
  clearAiSyncDismissTimer();
  if (!state.aiSyncDismissed && state.aiSyncStatus) {
    const sync = normalizeAiSyncStatus(state.aiSyncStatus);
    rememberDismissedNotice("ai-sync", aiSyncResultText(sync), noticeToneForSync(sync));
  }
  state.aiSyncDismissed = true;
  renderAiSyncStatus();
}
function scheduleAiSyncAutoDismiss() {
  if (state.aiSyncDismissTimer) return;
  state.aiSyncDismissTimer = window.setTimeout(() => {
    state.aiSyncDismissTimer = 0;
    dismissAiSyncNotice();
  }, AI_SYNC_AUTO_DISMISS_MS);
}
function sideSnapshotTooltipNode() {
  const tip = byId(ids.sideTooltip);
  if (!tip) return null;
  if (tip.parentElement !== document.body) document.body.appendChild(tip);
  return tip;
}
function placeSideSnapshotTooltip() {
  const box = document.querySelector(".side-snapshot");
  const tip = sideSnapshotTooltipNode();
  if (!box || !tip || !tip.classList.contains("has-content")) return;
  const rect = box.getBoundingClientRect();
  const margin = 10;
  tip.style.visibility = "hidden";
  tip.classList.add("visible");
  const tipWidth = tip.offsetWidth || 320;
  const tipHeight = tip.offsetHeight || 40;
  let left = rect.right + margin;
  if (left + tipWidth > window.innerWidth - margin) left = Math.max(margin, rect.left);
  let top = rect.top;
  if (top + tipHeight > window.innerHeight - margin) top = Math.max(margin, window.innerHeight - tipHeight - margin);
  tip.style.left = `${Math.round(left)}px`;
  tip.style.top = `${Math.round(top)}px`;
  tip.style.visibility = "";
}
function hideSideSnapshotTooltip() {
  const tip = sideSnapshotTooltipNode();
  if (!tip) return;
  tip.classList.remove("visible");
}
function bindSideSnapshotTooltip() {
  const box = document.querySelector(".side-snapshot");
  if (!box || box.dataset.tooltipBound === "1") return;
  box.dataset.tooltipBound = "1";
  sideSnapshotTooltipNode();
  box.addEventListener("mouseenter", placeSideSnapshotTooltip);
  box.addEventListener("mouseleave", hideSideSnapshotTooltip);
  window.addEventListener("scroll", () => {
    const tip = byId(ids.sideTooltip);
    if (tip && tip.classList.contains("visible")) placeSideSnapshotTooltip();
  }, true);
}
function mergeTooltipNotices() {
  const byKey = new Map();
  layerNoticeItems().forEach((item) => byKey.set(item.key, item));
  arr(state.dismissedNotices).forEach((item) => {
    if (!hasValue(item.text)) return;
    const key = clean(item.key) || `dismissed:${item.text}`;
    if (!byKey.has(key)) byKey.set(key, { key, text: item.text, tone: clean(item.tone) });
  });
  return [...byKey.values()];
}
function renderSideSnapshotTooltip() {
  const node = sideSnapshotTooltipNode();
  const box = document.querySelector(".side-snapshot");
  if (!node) return;
  const wasVisible = node.classList.contains("visible");
  clear(node);
  const notices = mergeTooltipNotices();
  if (box) {
    box.classList.toggle("has-notices", notices.length > 0);
    box.title = notices.length ? "Hover for refresh notes" : "";
  }
  if (!notices.length) {
    node.className = "side-snapshot-tooltip hidden";
    node.style.left = "";
    node.style.top = "";
    return;
  }
  node.className = `side-snapshot-tooltip has-content${wasVisible ? " visible" : ""}`;
  notices.forEach((item) => {
    append(node, el("div", `notice-line${item.tone ? ` ${item.tone}` : ""}`, item.text));
  });
  if (wasVisible) placeSideSnapshotTooltip();
}
function renderAiSyncStatus() {
  const node = byId(ids.aiSync);
  if (!node) return;
  clear(node);
  node.className = "ai-sync-status hidden";
  if (SAMPLE_MODE || state.aiSyncDismissed || !state.aiSyncStatus) {
    if (state.aiSyncDismissed) clearAiSyncDismissTimer();
    return;
  }
  const sync = normalizeAiSyncStatus(state.aiSyncStatus);
  const text = aiSyncResultText(sync);
  if (!hasValue(text)) return;
  const tone = noticeToneForSync(sync);
  node.className = `ai-sync-status${sync.running ? " running" : ""}${tone === "success" ? " success" : ""}${tone === "error" ? " error" : ""}`;
  const body = el("span", "ai-sync-status-body", text);
  append(node, body);
  if (!sync.running) {
    const dismiss = button("Dismiss", "copy-btn");
    dismiss.addEventListener("click", dismissAiSyncNotice);
    append(node, dismiss);
    scheduleAiSyncAutoDismiss();
  } else {
    clearAiSyncDismissTimer();
  }
}
async function refreshSessionTitleSurfaces() {
  await loadTurnStatus().catch(() => {
    state.turnStatus = [];
    return [];
  });
  await loadAgents().catch(() => {
    state.agents = [];
    return [];
  });
  renderSessions();
  renderAgentDeck();
  renderWorktreeLivePanels();
  if (state.sessionDrawer && state.sessionDrawer.session) {
    setSessionDrawerTitle(state.sessionDrawer.session);
  }
}
async function pollAiSyncStatus() {
  if (SAMPLE_MODE) return;
  const token = state.aiSyncPollToken + 1;
  state.aiSyncPollToken = token;
  let attempts = 0;
  const poll = async () => {
    if (token !== state.aiSyncPollToken) return;
    attempts += 1;
    try {
      state.aiSyncStatus = await fetchJson("/api/ai-sync-status", { cache: "no-store" });
      renderAiSyncStatus();
      if (!normalizeAiSyncStatus(state.aiSyncStatus).running) {
        await refreshSessionTitleSurfaces();
        return;
      }
    } catch (error) {
      state.aiSyncStatus = { ok: false, status: "error", message: clean(error.message) };
      renderAiSyncStatus();
      return;
    }
    if (attempts >= 20) {
      state.aiSyncStatus = { ...obj(state.aiSyncStatus), running: true, message: "AI sessions still syncing." };
      renderAiSyncStatus();
      return;
    }
    window.setTimeout(poll, 3000);
  };
  window.setTimeout(poll, 3000);
}
async function loadSnapshot() {
  setStatus("loading");
  state.stateWarning = "";
  try {
    const snapshotPromise = fetchJson(SAMPLE_MODE ? SAMPLE_URL : "/api/snapshot", { cache: "no-store" });
    const statePromise = fetchJson(SAMPLE_MODE ? SAMPLE_STATE_URL : "/api/state", { cache: "no-store" }).catch((error) => {
      state.stateWarning = `State API unavailable: ${clean(error.message)}`;
      return emptyUserState();
    });
    const turnStatusPromise = loadTurnStatus().catch((error) => {
      state.stateWarning = [state.stateWarning, `Turn status API unavailable: ${clean(error.message)}`].filter(Boolean).join("; ");
      return [];
    });
    const agentsPromise = loadAgents();
    const colorRulesPromise = loadColorRules();
    const [snapshot, userState, turnStatus] = await Promise.all([snapshotPromise, statePromise, turnStatusPromise, agentsPromise, colorRulesPromise]);
    if (snapshot && snapshot.error) throw new Error(clean(snapshot.error));
    state.snapshot = snapshot || {};
    state.userState = normalizeUserState(userState);
    state.turnStatus = normalizeTurnStatus(turnStatus);
    hideError();
    renderAll();
  } catch (error) {
    state.snapshot = null;
    state.agents = [];
    state.agentsGeneratedAt = null;
    state.turnStatus = [];
    state.userState = emptyUserState();
    renderLoadError(error);
  }
}
function setRefreshButtonBusy(busy) {
  const btn = byId(ids.refresh);
  if (!btn || SAMPLE_MODE) return;
  btn.disabled = Boolean(busy);
  btn.classList.toggle("loading", Boolean(busy));
  btn.textContent = busy ? "Refreshing" : "Refresh";
}
function sleepMs(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
async function refreshIsRunning() {
  const status = await fetchJson("/api/refresh/status", { cache: "no-store" });
  return Boolean(status && status.running);
}
async function waitForRefreshIdle() {
  const token = state.refreshPollToken + 1;
  state.refreshPollToken = token;
  setRefreshButtonBusy(true);
  let attempts = 0;
  while (token === state.refreshPollToken) {
    try {
      if (!(await refreshIsRunning())) return token === state.refreshPollToken;
    } catch (error) {
      if (token === state.refreshPollToken) setRefreshButtonBusy(false);
      throw error;
    }
    attempts += 1;
    if (attempts >= 200) {
      if (token === state.refreshPollToken) setRefreshButtonBusy(false);
      throw new Error("Refresh is still running.");
    }
    await sleepMs(1500);
  }
  return false;
}
async function adoptRunningRefresh() {
  if (SAMPLE_MODE) return;
  let releaseButton = false;
  try {
    if (!(await refreshIsRunning())) return;
    hideError();
    releaseButton = true;
    const finished = await waitForRefreshIdle();
    if (!finished) {
      releaseButton = false;
      return;
    }
    await loadSnapshot();
    loadCloudStatus();
  } catch (error) {
    showError("Refresh failed.", clean(error.message));
  } finally {
    if (releaseButton) setRefreshButtonBusy(false);
  }
}
async function refreshSnapshot() {
  if (SAMPLE_MODE) return;
  if (byId(ids.refresh).disabled && byId(ids.refresh).classList.contains("loading")) return;
  setRefreshButtonBusy(true);
  hideError();
  let releaseButton = true;
  try {
    const response = await fetch("/api/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch (error) {
      payload = { stdout_tail: await response.text() };
    }
    if (response.status === 409) {
      const finished = await waitForRefreshIdle();
      if (!finished) {
        releaseButton = false;
        return;
      }
      await loadSnapshot();
      loadCloudStatus();
      return;
    }
    if (!response.ok || !payload || payload.ok === false) {
      showError("Refresh failed.", clean(payload && (payload.detail || payload.stdout_tail)) || `HTTP ${response.status}`);
      return;
    }
    clearAiSyncDismissTimer();
    clearDismissedNotices();
    state.aiSyncDismissed = false;
    state.cloudStatusDismissed = false;
    state.layerWarningDismissedKey = "";
    state.aiSyncStatus = normalizeAiSyncStatus(payload.ai_sync || { running: true, message: "AI sessions syncing." });
    renderAiSyncStatus();
    if (state.aiSyncStatus.running) pollAiSyncStatus();
    await loadSnapshot();
    loadCloudStatus();
  } catch (error) {
    showError("Refresh failed.", clean(error.message));
  } finally {
    if (releaseButton) setRefreshButtonBusy(false);
  }
}
function setStatus(text, timestamp) {
  byId(ids.status).textContent = clean(text);
  const stamp = byId(ids.timestamp);
  if (!stamp) return;
  stamp.textContent = clean(timestamp);
  stamp.classList.toggle("hidden", !hasValue(timestamp));
}
function showError(title, detail) {
  const panel = byId(ids.error);
  clear(panel);
  panel.classList.remove("hidden");
  append(panel, el("h3", "", title), el("p", "", detail));
}
function hideError() {
  const panel = byId(ids.error);
  clear(panel);
  panel.classList.add("hidden");
}
function renderLoadError(error) {
  setStatus("unavailable");
  const warning = byId(ids.warning);
  warning.classList.add("hidden");
  clear(warning);
  const panel = byId(ids.error);
  clear(panel);
  panel.classList.remove("hidden");
  append(
    panel,
    el("h3", "", "Snapshot missing"),
    el("p", "", clean(error && error.message) || "The snapshot API is unavailable."),
    el("p", "", "Run the collector, then start the FastAPI server:"),
    commandBlock(".venv/bin/python3 apps/holodeck/collect.py && .venv/bin/uvicorn apps.holodeck.server:app --host 127.0.0.1 --port 8790", "copy")
  );
}
function renderAll() {
  renderTopStatus();
  renderAiSyncStatus();
  renderSideSnapshotTooltip();
  renderAgentDeck();
  renderTodoPanel();
  renderWorktrees();
  renderUniverse();
  renderSessions();
  renderBranches();
  renderCoreTable();
  renderSkills();
  renderSpecs();
  renderDeploy();
  setupNavObserver();
}
function renderTopStatus() {
  const generated = clean(state.snapshot && state.snapshot.generated_at);
  if (generated) setStatus(relativeTime(generated) || "ready", localTimestamp(generated));
  else setStatus("ready");
  const warning = byId(ids.warning);
  clear(warning);
  warning.className = "warning-strip hidden";
  const errors = getLayerErrors().map(formatLayerError);
  if (state.stateWarning) errors.push({ name: "state", label: layerLabel("state"), error: state.stateWarning });
  renderSideSnapshotTooltip();
  if (!errors.length) return;
  const key = layerWarningKey(errors);
  if (state.layerWarningDismissedKey && state.layerWarningDismissedKey === key) return;
  warning.className = "warning-strip";
  const body = el("div", "warning-strip-body");
  append(body, el("strong", "", "Refresh notes"));
  const warningText = errors.map((item) => `${item.label || layerLabel(item.name)}: ${item.error}`).join(" ");
  errors.forEach((item) => {
    append(body, el("span", "warning-strip-item", `${item.label || layerLabel(item.name)}: ${item.error}`));
  });
  const dismiss = button("Dismiss", "copy-btn");
  dismiss.addEventListener("click", () => {
    rememberDismissedNotice("layer-warning", warningText, "error");
    state.layerWarningDismissedKey = key;
    renderTopStatus();
  });
  append(warning, body, dismiss);
}
function renderAgentDeck() {
  const root = byId(ids.agentDeck);
  const summary = byId(ids.deckSummary);
  const filters = byId(ids.agentPlatformFilter);
  const toggleRoot = byId(ids.agentDeckToggle);
  clear(root);
  clear(summary);
  clear(filters);
  clear(toggleRoot);
  const platformAgents = dedupeAgentDeck(sortedAgents(state.agents).filter(agentPlatformVisible));
  renderAgentPlatformFilters(filters, platformAgents);
  const agents = platformAgents.filter((agent) => !agentIsHidden(agent));
  renderDeckSummary(summary, agents);
  if (!agents.length) {
    root.appendChild(emptyState("No recent agent sessions."));
    return;
  }
  const visibleAgents = state.deckShowAll ? agents : agents.slice(0, 9);
  visibleAgents.forEach((agent) => root.appendChild(agentTile(agent)));
  if (agents.length > 9) {
    const toggle = button(state.deckShowAll ? "show fewer" : `show all (${agents.length})`, "copy-btn deck-show-all");
    toggle.addEventListener("click", () => {
      state.deckShowAll = !state.deckShowAll;
      renderAgentDeck();
    });
    toggleRoot.appendChild(toggle);
  }
}
function renderAgentPlatformFilters(root, platformAgents) {
  if (!root) return;
  AGENT_FILTER_KEYS.forEach((key) => {
    const label = el("label", "agent-platform-option");
    const input = el("input");
    input.type = "checkbox";
    input.checked = state.agentFilter[key] !== false;
    input.addEventListener("change", () => {
      state.agentFilter[key] = input.checked;
      state.deckShowAll = false;
      persistAgentFilterPreference();
      renderAgentDeck();
    });
    append(label, input, el("span", "", platformMeta(key).label));
    root.appendChild(label);
  });
  const hiddenCount = arr(platformAgents).filter(agentIsHidden).length;
  if (hiddenCount > 0) {
    const showHidden = button(`show hidden (${hiddenCount})`, "copy-btn agent-show-hidden-btn");
    showHidden.addEventListener("click", () => {
      arr(state.agents).map(agentExchangeId).filter(Boolean).forEach((id) => state.hiddenAgents.delete(id));
      persistHiddenAgentsPreference();
      renderAgentDeck();
    });
    root.appendChild(showHidden);
  }
}
function agentPlatformVisible(agent) {
  const platform = clean(agent && agent.platform);
  if (!AGENT_FILTER_KEYS.includes(platform)) return true;
  return state.agentFilter[platform] !== false;
}
function renderDeckSummary(root, agents) {
  const counts = { thinking: 0, "needs-you": 0, error: 0, done: 0 };
  arr(agents).forEach((agent) => {
    const key = AGENT_STATE_META[clean(agent.state)] ? clean(agent.state) : "done";
    counts[key] = (counts[key] || 0) + 1;
  });
  const items = ["thinking", "needs-you", "error", "done"].filter((key) => counts[key] > 0);
  if (!items.length) {
    root.appendChild(el("span", "muted", state.agentsGeneratedAt ? `updated ${relativeTime(state.agentsGeneratedAt)}` : "no recent agents"));
    return;
  }
  items.forEach((key, index) => {
    const meta = AGENT_STATE_META[key];
    if (index) root.appendChild(el("span", "deck-summary-sep", "·"));
    append(root, dot(`agent-${meta.cls}`), el("span", "", `${counts[key]} ${meta.label}`));
  });
}
function sortedAgents(agents) {
  const priority = { "needs-you": 0, error: 1, thinking: 2, done: 3 };
  return arr(agents).slice().sort((a, b) => {
    const stateA = AGENT_STATE_META[clean(a.state)] ? clean(a.state) : "done";
    const stateB = AGENT_STATE_META[clean(b.state)] ? clean(b.state) : "done";
    if (priority[stateA] !== priority[stateB]) return priority[stateA] - priority[stateB];
    const dateA = parseDate(a.last_activity);
    const dateB = parseDate(b.last_activity);
    return (dateB ? dateB.getTime() : 0) - (dateA ? dateA.getTime() : 0);
  });
}
function normalizeAgentTitle(title) {
  return clean(title).replace(/^\(\d+\)\s+/, "");
}
function agentDeckDedupeKey(agent) {
  const platform = clean(agent && agent.platform);
  const worktree = clean(agent && agent.worktree);
  const branch = clean(agent && agent.branch);
  return [platform, worktree || branch, normalizeAgentTitle(agentTitle(agent)).toLowerCase()].join("\0");
}
function dedupeAgentDeck(agents) {
  const seen = new Set();
  const result = [];
  arr(agents).forEach((agent) => {
    const key = agentDeckDedupeKey(agent);
    if (!key || seen.has(key)) return;
    seen.add(key);
    result.push(agent);
  });
  return result;
}
function agentStateMeta(agent) {
  const stateValue = clean(agent && agent.state);
  return AGENT_STATE_META[stateValue] || { label: stateValue || "done", cls: "done" };
}
function slugMatchesProjectIdentity(slug, identity) {
  const lower = clean(slug).toLowerCase();
  if (!lower || !identity) return false;
  if (identity.includes(lower)) return true;
  const leaf = lower.includes("/") ? lower.split("/").pop() : lower;
  return Boolean(leaf) && identity.includes(leaf);
}
function projectLabelFromSlug(slug) {
  const value = clean(slug);
  if (!value.includes("/")) return value;
  return value.split("/").pop() || value;
}
function agentProjectLabel(agent, wt) {
  if (wt) {
    const folder = worktreeFolderName(wt);
    const slugs = arr(wt.apps_touched).map(clean).filter(Boolean);
    const identity = `${clean(wt.branch)} ${folder}`.toLowerCase();
    const named = slugs.find((slug) => slugMatchesProjectIdentity(slug, identity));
    // Matching app slug wins; otherwise the worktree folder — never an unrelated apps_touched[0].
    return named ? projectLabelFromSlug(named) : folder;
  }
  return basename(agent && agent.worktree) || platformMeta(clean(agent && agent.platform)).label;
}
function agentTile(agentValue) {
  const agent = obj(agentValue);
  const meta = agentStateMeta(agent);
  const wt = matchedWorktreeForAgent(agent);
  const session = sessionForAgent(agent);
  const tile = button("", `agent-tile ${meta.cls}`);
  tile.setAttribute("aria-label", `Open ${agentTitle(agent)}`);
  const bar = el("div", "agent-tile-bar");
  const barLabel = el("span", "agent-tile-bar-label", agentProjectLabel(agent, wt));
  const hide = el("span", "agent-hide-btn", "×");
  hide.tabIndex = 0;
  hide.setAttribute("role", "button");
  hide.setAttribute("aria-label", "Hide this card");
  hide.title = "Hide this card (show hidden restores it)";
  const hideAgent = (event) => {
    event.preventDefault();
    event.stopPropagation();
    const id = agentExchangeId(agent);
    if (!id) return;
    state.hiddenAgents.add(id);
    persistHiddenAgentsPreference();
    renderAgentDeck();
  };
  hide.addEventListener("click", hideAgent);
  hide.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") hideAgent(event);
  });
  const colors = wt ? worktreeTitleBarColors(wt) : { background: "#0b1220", foreground: "#cde3ff" };
  bar.style.background = colors.background;
  bar.style.color = colors.foreground;
  append(bar, barLabel, hide);
  const top = el("div", "state-row");
  append(top, dot(`agent-${meta.cls}`), el("span", "", meta.label), el("span", "tile-elapsed", relativeTime(agent.since) || relativeTime(agent.last_activity) || "time unknown"));
  const title = el("div", "tile-title", agentTitle(agent));
  const bottom = el("div", "tile-meta");
  const platform = platformMeta(clean(agent.platform));
  append(bottom, chip(platform.label, platform.cls), branchIdentityPill(agent.branch, wt), sessionContextTags(agent));
  if (hasValue(agent.session_label)) bottom.appendChild(el("span", "tile-session-label", agent.session_label));
  tile.addEventListener("click", () => openSession(session));
  tile.addEventListener("mouseenter", () => showTurnStatusTooltip(tile, { title: agentTitle(agent), recap: clean(agent.recap) || clean(agent.user_preview) }));
  tile.addEventListener("mouseleave", hideSessionTooltip);
  tile.addEventListener("focus", () => showTurnStatusTooltip(tile, { title: agentTitle(agent), recap: clean(agent.recap) || clean(agent.user_preview) }));
  tile.addEventListener("blur", hideSessionTooltip);
  append(tile, bar, top, title, bottom);
  if (wt && wtIsCursorOpen(wt)) tile.appendChild(agentCursorFocusButton(wt));
  return tile;
}
function agentTitle(agent) {
  const raw = clean(agent && agent.turn_title) || clean(agent && agent.recap) || clean(agent && agent.user_preview) || clean(agent && agent.session_label) || "Untitled agent turn";
  return normalizeAgentTitle(raw) || raw;
}
function agentCursorFocusButton(wt) {
  const focus = el("span", "agent-focus-btn", "⌖");
  focus.tabIndex = 0;
  focus.setAttribute("role", "button");
  focus.setAttribute("aria-label", `Go to the open Cursor window for ${worktreeFolderName(wt)}`);
  focus.title = `Go to the open Cursor window for ${worktreeFolderName(wt)}`;
  const run = async (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (focus.getAttribute("aria-disabled") === "true") return;
    const original = focus.textContent;
    focus.setAttribute("aria-disabled", "true");
    focus.textContent = "…";
    try {
      await requestCursorFocus(wt.path);
      focus.textContent = "✓";
      focus.title = "focused";
      window.setTimeout(() => {
        if (!focus.isConnected) return;
        focus.removeAttribute("aria-disabled");
        focus.textContent = original;
        focus.title = `Go to the open Cursor window for ${worktreeFolderName(wt)}`;
      }, 1200);
    } catch (error) {
      if (error.stale === true) focus.setAttribute("aria-disabled", "true");
      else focus.removeAttribute("aria-disabled");
      focus.textContent = "!";
      focus.title = clean(error.message) || cursorFocusFailure({}, 0).message;
    }
  };
  focus.addEventListener("click", run);
  focus.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") run(event);
  });
  return focus;
}
function matchedWorktreeForAgent(agent) {
  const path = clean(agent && agent.worktree);
  const branch = clean(agent && agent.branch);
  const worktrees = getLayer("worktrees");
  if (path) {
    const byPath = worktrees.find((wt) => clean(wt.path) === path);
    if (byPath) return byPath;
  }
  if (!branch || isDetachedBranch(branch)) return null;
  const byBranch = worktrees.filter((wt) => clean(wt.branch) === branch);
  return byBranch.length === 1 ? byBranch[0] : null;
}
function sessionForAgent(agentValue) {
  const agent = obj(agentValue);
  const agentId = clean(agent.session_id);
  const agentSuffix = agentId.includes(":") ? agentId.split(":").slice(1).join(":") : agentId;
  const match = getLayer("sessions").find((session) => {
    const candidates = sessionIdCandidates(session);
    if (candidates.has(agentId)) return true;
    return [...candidates].some((candidate) => candidate === agentSuffix || candidate.endsWith(`:${agentSuffix}`) || agentId.endsWith(`:${candidate}`));
  });
  if (match) return match;
  const source = inferSessionSource(agentId, agent.session_label);
  const id = source.prefix && agentId.startsWith(`${source.prefix}:`) ? agentId.slice(source.prefix.length + 1) : agentId;
  return {
    platform: clean(agent.platform) || source.platform,
    entrypoint: clean(agent.entrypoint) || source.entrypoint,
    host: clean(agent.host) || source.host,
    remote_control: agent.remote_control === true,
    id,
    session_id: agentId,
    origin: "operator",
    label: clean(agent.session_label) || platformMeta(clean(agent.platform) || source.platform).label,
    latest_primary_digest_title: agentTitle(agent),
    first_user: clean(agent.user_preview) || clean(agent.recap),
    last_user: clean(agent.user_preview),
    project: clean(agent.worktree),
    worktree: clean(agent.worktree),
    branch: clean(agent.branch),
    last_activity: clean(agent.last_activity) || clean(agent.since),
    started: clean(agent.started) || clean(agent.since),
    messages: null,
  };
}
function renderUniverse() {
  const worktrees = getLayer("worktrees");
  const branches = getLayer("branches");
  const sessions = getLayer("sessions");
  renderUniverseStats(worktrees, branches, getLayer("apps"), sessions, getLayer("specs"));
  renderParkedWorktrees(worktrees, branches, sessions);
  renderBranchesWithoutCheckout(branches, worktrees);
  renderAppFilters();
  renderAppCards();
  renderLatestActivity(worktrees, sessions);
}
function renderUniverseStats(worktrees, branches, apps, sessions, specs) {
  const root = byId(ids.universeStats);
  clear(root);
  const activeCount = arr(worktrees).filter((wt) => worktreeState(worktreeKey(wt)).active).length;
  const parkedCount = arr(worktrees).length - activeCount;
  const stats = [
    { label: "Active", value: activeCount, target: "active" },
    { label: "Parked", value: parkedCount, target: "universe-parked" },
    { label: "Branches", value: arr(branches).length, target: "branches" },
    { label: "Apps", value: arr(apps).length, target: "universe-apps" },
    { label: "AI sessions", value: arr(sessions).length, target: "sessions" },
    { label: "Specs", value: arr(specs).length, target: "specs" },
  ];
  stats.forEach((item) => {
    const card = button("", "stat");
    card.addEventListener("click", () => scrollToId(item.target));
    append(card, el("div", "num", item.value), el("div", "lbl", item.label));
    root.appendChild(card);
  });
}
function renderParkedWorktrees(worktrees, branches, sessions) {
  const root = byId(ids.universeParked);
  clear(root);
  const branchPrs = new Map(arr(branches).map((branch) => [clean(branch.name), branch.pr]));
  const parked = sortWorktrees(worktrees).filter((wt) => !worktreeState(worktreeKey(wt)).active);
  if (!parked.length) {
    root.appendChild(emptyState("Nothing parked."));
    return;
  }
  parked.forEach((wt) => root.appendChild(parkedWorktreeRow(wt, branchPrs.get(clean(wt.branch)), sessions)));
}
function parkedWorktreeRow(wt, pr, sessions) {
  const key = worktreeKey(wt);
  const branch = clean(wt.branch) || key;
  const row = el("div", "universe-row parked-worktree-row");
  row.id = parkedWorktreeRowId(key);
  const main = el("div", "universe-main");
  const leftOff = latestWorktreeContext(wt, sessions);
  append(main, el("div", "universe-title", worktreeFolderName(wt)), branchIdentityPill(branch, wt));
  append(main, el("div", "universe-sub", leftOff.title ? `left off: ${leftOff.title}` : "left off: no matching session"));
  const meta = el("div", "universe-meta");
  const commit = obj(wt.last_commit);
  append(meta, hasValue(leftOff.when) ? timeNode(leftOff.when, "") : null, commitSummaryButton(branch, commit), dirtyBadges(wt), prPill(pr));
  const actions = el("div", "universe-actions");
  const activate = button("activate", "copy-btn prompt-copy");
  activate.disabled = SAMPLE_MODE;
  activate.addEventListener("click", () => saveWorktreeField(key, { active: true, deactivated_at: null }, true));
  append(actions, activate, wtIsCursorOpen(wt) ? cursorFocusControl(wt, worktreeFolderName(wt), `${row.id}-cursor-focus-status`) : null);
  append(row, worktreeColorChip(wt), main, meta, actions);
  return row;
}
function latestWorktreeContext(wt, sessions) {
  const status = latestTurnStatusForWorktree(wt);
  if (status) return { title: status.title, when: status.since, session: sessionForTurnStatus(status) };
  const session = latestSessionForWorktree(clean(wt.path), sessions, clean(wt.branch));
  if (session) return { title: sessionDisplayTitle(session), when: session.last_activity, session };
  const agent = agentsForWorktree(wt)[0];
  if (agent) return { title: agentTitle(agent), when: clean(agent.last_activity) || clean(agent.since), session: sessionForAgent(agent) };
  return { title: "", when: "", session: null };
}
function dirtyBadges(wt) {
  const row = el("span", "universe-badges");
  if (asCount(wt.dirty) > 0) row.appendChild(chip(`${asCount(wt.dirty)} dirty`, "gold"));
  if (asCount(wt.untracked) > 0) row.appendChild(chip(`${asCount(wt.untracked)} untracked`, "gold"));
  if (asCount(wt.unpushed) > 0) row.appendChild(chip(`${asCount(wt.unpushed)} unpushed`, "gold"));
  return row.childNodes.length ? row : null;
}
function commitSummaryButton(branch, commit) {
  if (!hasValue(commit && commit.subject)) return null;
  const node = button(`${clean(commit.subject)}${hasValue(commit.date) ? ` · ${relativeTime(commit.date)}` : ""}`, "mono-link universe-commit");
  node.addEventListener("click", () => openCommitDrawer(branch));
  return node;
}
function parkedWorktreeRowId(branch) {
  return `parked-${safeId(branch)}`;
}
function renderBranchesWithoutCheckout(branches, worktrees) {
  const root = byId(ids.universeBranches);
  clear(root);
  const checkedOut = new Set(arr(worktrees).map((wt) => clean(wt.branch)).filter(Boolean));
  const rows = arr(branches).filter((branch) => {
    const name = clean(branch.name);
    if (!name || name === "main") return false;
    if (checkedOut.has(name)) return false;
    return !hasValue(branch.worktree);
  });
  const heading = root.previousElementSibling;
  if (!rows.length) {
    root.classList.add("hidden");
    if (heading && heading.matches("h3.sub")) heading.classList.add("hidden");
    return;
  }
  root.classList.remove("hidden");
  if (heading && heading.matches("h3.sub")) heading.classList.remove("hidden");
  rows.forEach((branch) => root.appendChild(branchWithoutCheckoutRow(branch)));
}
function branchWithoutCheckoutRow(branchValue) {
  const branch = obj(branchValue);
  const name = clean(branch.name) || "branch";
  const row = el("div", "universe-row branch-universe-row");
  const main = el("div", "universe-main");
  const branchButton = branchNameButton(name);
  append(main, branchButton, el("div", "universe-sub", clean(branch.subject) || clean(branch.tip) || "No commit subject"));
  const meta = el("div", "universe-meta");
  append(meta, timeNode(branch.date, "—"), driftPills(branch), prPill(branch.pr));
  const actions = el("div", "universe-actions");
  append(actions, promptCopyButton(worktreePromptText("branch", name), "⧉ worktree prompt"));
  append(row, el("span", "universe-ledger-chip mono", shortBranchName(name)), main, meta, actions);
  return row;
}
function promptCopyButton(value, label) {
  const node = copyButton(value, label);
  if (node) node.classList.add("prompt-copy");
  return node;
}
function worktreePromptText(kind, value) {
  if (kind === "app") {
    const slug = safeId(value);
    return `Use skill skills/repo-ops/create-worktree/README.md to create a worktree for a new branch feature/${slug}-<topic> (replace <topic>) based on origin/main, for work on apps/${slug}/.`;
  }
  return `Use skill skills/repo-ops/create-worktree/README.md to create a worktree for existing branch ${clean(value)}.`;
}
function worktreeForBranch(branch) {
  const value = clean(branch);
  if (isDetachedBranch(value)) return null;
  return getLayer("worktrees").find((wt) => clean(wt.branch) === value) || null;
}
function todoSourceChip(source) {
  const branch = clean(source);
  if (!branch) return null;
  const wt = worktreeForBranch(branch);
  const node = chip(wt ? agentProjectLabel({}, wt) : shortBranchName(branch), "todo-source branch-identity");
  applyBranchIdentityStyles(node, wt);
  node.title = branch;
  return node;
}
function renderTodoPanel() {
  const root = byId(ids.todoRoot);
  const mode = byId(ids.todoMode);
  clear(root);
  if (mode) mode.textContent = SAMPLE_MODE ? "sample read-only" : "";
  const form = el("form", "next-step-form");
  const input = el("input", "text-input");
  input.type = "text";
  input.placeholder = "Add a to-do";
  input.disabled = SAMPLE_MODE;
  const add = button("Add", "action-btn");
  add.type = "submit";
  add.disabled = SAMPLE_MODE;
  append(form, input, add);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    addNextStep(input.value);
    input.value = "";
  });
  const list = el("div", "next-steps-list todo-list");
  const steps = normalizeStepList(state.userState.next_steps);
  if (!steps.length) {
    list.appendChild(emptyState("No to-do items."));
  } else {
    steps.forEach((item) => list.appendChild(todoItem(item)));
  }
  bindTodoListDrag(list);
  append(root, form, list, todoArchiveSection());
}
function todoArchiveSection() {
  const wrap = el("div", "todo-archive");
  const open = state.todoArchiveOpen;
  const toggle = button("", "todo-archive-toggle");
  toggle.type = "button";
  toggle.setAttribute("aria-expanded", open ? "true" : "false");
  append(toggle, el("span", "todo-archive-arrow", open ? "▾" : "▸"), textNode("Archived"));
  toggle.addEventListener("click", () => {
    state.todoArchiveOpen = !state.todoArchiveOpen;
    if (state.todoArchiveOpen) {
      loadTodoArchive();
      return;
    }
    renderTodoPanel();
  });
  append(wrap, toggle);
  if (!open) return wrap;
  const list = el("div", "todo-archive-list");
  if (state.todoArchiveItems === null) {
    list.appendChild(emptyState("Loading archived to-dos..."));
  } else if (state.todoArchiveError) {
    list.appendChild(el("div", "callout red", state.todoArchiveError));
  } else {
    const items = arr(state.todoArchiveItems);
    if (!items.length) {
      list.appendChild(emptyState("No archived to-dos."));
    } else {
      items.forEach((item) => list.appendChild(todoArchiveItem(item)));
    }
  }
  append(wrap, list);
  return wrap;
}
function todoArchiveItem(item) {
  const row = el("div", `todo-archive-item${item.done ? " done" : ""}`);
  const text = el("div", "todo-archive-text", clean(item.text) || "(untitled)");
  const metaBits = [];
  if (hasValue(item.archived_date)) metaBits.push(clean(item.archived_date));
  if (hasValue(item.archived_time)) metaBits.push(clean(item.archived_time));
  const meta = el("div", "todo-archive-meta small muted", metaBits.join(" · "));
  append(row, text, meta);
  return row;
}
async function loadTodoArchive() {
  if (SAMPLE_MODE) {
    state.todoArchiveItems = [];
    state.todoArchiveError = "";
    state.todoArchiveLoading = false;
    renderTodoPanel();
    return;
  }
  if (state.todoArchiveLoading) return;
  state.todoArchiveLoading = true;
  state.todoArchiveError = "";
  renderTodoPanel();
  try {
    const payload = await fetchJson("/api/next-steps-archive", { cache: "no-store" });
    state.todoArchiveItems = arr(payload && payload.items);
    state.todoArchiveError = "";
  } catch (error) {
    state.todoArchiveItems = [];
    state.todoArchiveError = clean(error.message) || "Could not load archived to-dos.";
  } finally {
    state.todoArchiveLoading = false;
    renderTodoPanel();
  }
}
function todoItem(item) {
  const row = el("div", `next-step-item todo-item${item.done ? " done" : ""}`);
  row.dataset.id = item.id;
  row.draggable = false;
  addNextStepDragHandlers(row, item.id);
  const grip = button("⠿", "drag-mini");
  grip.title = SAMPLE_MODE ? "Sample mode" : "Drag to reorder";
  grip.disabled = SAMPLE_MODE;
  if (!SAMPLE_MODE) {
    grip.addEventListener("mousedown", () => {
      row.draggable = true;
    });
  }
  const check = el("input", "next-step-check");
  check.type = "checkbox";
  check.checked = item.done;
  check.disabled = SAMPLE_MODE;
  check.addEventListener("change", () => updateNextStep(item.id, { done: check.checked }));
  const text = el("input", "next-step-text next-step-text-input");
  text.type = "text";
  text.value = item.text;
  text.disabled = SAMPLE_MODE;
  text.setAttribute("aria-label", "Edit to-do");
  const saveText = () => {
    const value = text.value.trim();
    if (!value) {
      text.value = item.text;
      return;
    }
    if (value !== item.text) updateNextStep(item.id, { text: value });
  };
  text.addEventListener("blur", saveText);
  text.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      text.blur();
    }
    if (event.key === "Escape") {
      text.value = item.text;
      text.blur();
    }
  });
  const source = todoSourceChip(item.source);
  const archive = button("archive", "copy-btn archive-btn");
  archive.disabled = SAMPLE_MODE;
  archive.addEventListener("click", () => archiveNextStep(item.id));
  append(row, grip, check, text, source, archive);
  return row;
}
async function addNextStep(text) {
  const value = clean(text).trim();
  if (!value || SAMPLE_MODE) return;
  try {
    const item = await fetchJson("/api/next-steps", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: value }),
    });
    state.userState.next_steps.unshift(normalizeStepItem(item));
    renderTodoPanel();
  } catch (error) {
    showError("Could not add to-do.", clean(error.message));
    reloadStateOnly();
  }
}
async function updateNextStep(stepId, patch) {
  if (SAMPLE_MODE) return;
  const id = clean(stepId);
  state.userState.next_steps = state.userState.next_steps.map((item) => item.id === id ? normalizeStepItem({ ...item, ...patch }) : item);
  renderTodoPanel();
  try {
    const updated = await fetchJson(`/api/next-steps/${encodeURIComponent(id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    state.userState.next_steps = state.userState.next_steps.map((item) => item.id === id ? normalizeStepItem(updated) : item);
    renderTodoPanel();
  } catch (error) {
    showError("Could not update to-do.", clean(error.message));
    reloadStateOnly();
  }
}
async function archiveNextStep(stepId) {
  if (SAMPLE_MODE) return;
  const id = clean(stepId);
  try {
    await fetchJson(`/api/next-steps/${encodeURIComponent(id)}/archive`, { method: "POST" });
    state.userState.next_steps = state.userState.next_steps.filter((item) => item.id !== id);
    if (state.todoArchiveOpen) {
      state.todoArchiveItems = null;
      renderTodoPanel();
      loadTodoArchive();
    } else {
      state.todoArchiveItems = null;
      renderTodoPanel();
    }
  } catch (error) {
    showError("Could not archive to-do.", clean(error.message));
    reloadStateOnly();
  }
}
function addNextStepDragHandlers(row, stepId) {
  if (SAMPLE_MODE) return;
  row.addEventListener("dragstart", (event) => {
    if (!row.draggable) {
      event.preventDefault();
      return;
    }
    state.draggingNextStepId = stepId;
    event.dataTransfer.effectAllowed = "move";
    try {
      event.dataTransfer.setData("text/plain", stepId);
    } catch (error) {
      // Ignore browsers that reject setData during dragstart.
    }
    row.classList.add("dragging");
  });
  row.addEventListener("dragend", () => {
    state.draggingNextStepId = null;
    row.classList.remove("dragging");
    row.draggable = false;
  });
}
function bindTodoListDrag(list) {
  if (SAMPLE_MODE) return;
  list.addEventListener("dragover", (event) => {
    if (!state.draggingNextStepId) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  });
  list.addEventListener("drop", (event) => {
    event.preventDefault();
    const source = state.draggingNextStepId;
    if (!source) return;
    reorderNextStepsToIndex(source, todoDropInsertIndex(list, event.clientY, source));
  });
}
function todoDropInsertIndex(list, clientY, sourceId) {
  const rows = [...list.querySelectorAll(".todo-item")].filter((row) => row.dataset.id !== sourceId);
  for (let i = 0; i < rows.length; i += 1) {
    const rect = rows[i].getBoundingClientRect();
    if (clientY < rect.top + rect.height / 2) return i;
  }
  return rows.length;
}
function reorderNextStepsToIndex(source, insertIndex) {
  const current = normalizeStepList(state.userState.next_steps).map((item) => item.id);
  const order = current.filter((id) => id !== source);
  const index = Math.max(0, Math.min(Number(insertIndex) || 0, order.length));
  order.splice(index, 0, source);
  if (current.join("\0") === order.join("\0")) return;
  persistNextStepOrder(order);
}
async function persistNextStepOrder(order) {
  const orderSet = new Set(order);
  const byIdMap = new Map(normalizeStepList(state.userState.next_steps).map((item) => [item.id, item]));
  const reordered = order.map((id) => byIdMap.get(id)).filter(Boolean);
  normalizeStepList(state.userState.next_steps).forEach((item) => {
    if (!orderSet.has(item.id)) reordered.push(item);
  });
  state.userState.next_steps = reordered;
  renderTodoPanel();
  if (SAMPLE_MODE) return;
  try {
    const updated = await fetchJson("/api/next-steps-order", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order }),
    });
    const list = Array.isArray(updated) ? updated : arr(updated && updated.next_steps);
    state.userState.next_steps = normalizeStepList(list);
    renderTodoPanel();
  } catch (error) {
    showError("Could not persist to-do order.", clean(error.message));
    reloadStateOnly();
  }
}
function activityVisible() {
  try {
    return window.localStorage.getItem(ACTIVITY_PREF_KEY) === "1";
  } catch (error) {
    return false;
  }
}
function setActivityVisible(visible) {
  try {
    window.localStorage.setItem(ACTIVITY_PREF_KEY, visible ? "1" : "0");
  } catch (error) {}
  applyActivityVisibility();
}
function applyActivityVisibility() {
  const visible = activityVisible();
  const card = byId(ids.activityCard);
  const toggle = byId(ids.activityToggle);
  if (card) card.classList.toggle("hidden", !visible);
  if (toggle) toggle.textContent = visible ? "Hide activity" : "Show activity";
}
function turnStatusRowData(statusValue, worktrees) {
  const status = obj(statusValue);
  const branch = clean(status.branch || status.checked_out_branch || status.worktree_branch || status.ref);
  const path = clean(status.worktree_path || status.worktree || status.path);
  const name = clean(status.worktree_name || status.name);
  const wt = arr(worktrees).find((item) => {
    return clean(item.path) === path || clean(item.branch) === branch || worktreeFolderName(item) === name;
  }) || null;
  const resolvedBranch = branch || clean(wt && wt.branch) || basename(path);
  const since = clean(status.since || status.response_end_ts || status.user_ts || status.last_activity);
  const entry = worktreeState(resolvedBranch);
  return {
    raw: status,
    wt,
    branch: resolvedBranch,
    path,
    name: name || (wt ? worktreeFolderName(wt) : basename(path) || shortBranchName(resolvedBranch)),
    entry,
    date: parseDate(since),
    since,
    session_id: clean(status.session_id || status.session || status.session_key),
    exchange_id: clean(status.exchange_id || status.id),
    session_label: clean(status.session_label || status.label),
    state: clean(status.state) === "waiting-on-ai" ? "waiting-on-ai" : "your-turn",
    title: turnStatusTitle(status),
    recap: turnStatusRecap(status),
  };
}
function turnStatusTitle(status) {
  const digest = obj(status && status.digest);
  return clean(status && (status.turn_title || status.title || status.digest_title)) || clean(digest.title) || trunc(clean(status && (status.user_preview || status.last_user_preview)), 90) || "Untitled turn";
}
function turnStatusRecap(status) {
  const digest = obj(status && status.digest);
  return clean(status && (status.recap || status.digest_recap || status.last_user_preview || status.user_preview)) || clean(digest.recap) || "";
}
function turnStateBadge(value) {
  const waiting = clean(value) === "waiting-on-ai";
  return el("span", `turn-state-badge ${waiting ? "thinking" : "done"}`, waiting ? "THINKING" : "DONE");
}
function showTurnStatusTooltip(anchor, rowData) {
  hideSessionTooltip();
  const tooltip = el("div", "session-tooltip");
  append(
    tooltip,
    el("div", "session-tooltip-title", rowData.title),
    el("div", "session-tooltip-preview", rowData.recap || "No recap available.")
  );
  document.body.appendChild(tooltip);
  placeTooltip(anchor, tooltip);
}
function primaryInterfaceMeta(value) {
  return AI_INTERFACES[clean(value)] || null;
}
function primaryInterfacePill(value) {
  const meta = primaryInterfaceMeta(value);
  return meta ? chip(meta.label, meta.cls) : el("span", "status-placeholder", "");
}
function legacyToolPlatform(value) {
  const key = clean(value);
  if (key === "claude-code" || key === "claude-cloud") return "claude";
  if (key === "codex-cloud") return "codex";
  if (key === "codex" || key === "cursor") return key;
  return "";
}
function sessionPlatform(session) {
  const data = obj(session);
  const value = clean(data.platform);
  if (PLATFORM_META[value]) return value;
  return legacyToolPlatform(data.tool);
}
function sessionHost(session) {
  const data = obj(session);
  const host = clean(data.host);
  if (host === "cloud" || host === "local") return host;
  const tool = clean(data.tool);
  return tool === "claude-cloud" || tool === "codex-cloud" ? "cloud" : "local";
}
function sessionRemoteControl(session) {
  const value = obj(session).remote_control;
  return value === true || value === 1 || clean(value).toLowerCase() === "true";
}
function platformMeta(value) {
  return PLATFORM_META[clean(value)] || { label: clean(value) || "Session", cls: "" };
}
function entrypointMeta(session) {
  const data = obj(session);
  const platform = sessionPlatform(data);
  let key = clean(data.entrypoint);
  if (key === "claude-desktop" || key === "codex-desktop" || key === "codex-vscode" || key === "cursor") key = "app";
  if (key === "codex-cli") key = "cli";
  if (key === "codex-subagent") key = "subagent";
  if (platform === "cursor" && key === "app") key = "ide";
  const label = ENTRYPOINT_META[key];
  if (!label) return key ? { label: key, cls: platformMeta(platform).cls } : null;
  return { label: `${platformMeta(platform).label} ${label}`, cls: platformMeta(platform).cls };
}
function entrypointPill(session) {
  const meta = entrypointMeta(session);
  return meta ? chip(meta.label, meta.cls) : null;
}
function sessionContextTags(session) {
  const tags = [];
  if (sessionHost(session) === "cloud") tags.push(tag("cloud"));
  if (sessionRemoteControl(session)) {
    const node = tag("RC");
    if (hasValue(obj(session).bridge_session_id)) node.title = clean(obj(session).bridge_session_id);
    tags.push(node);
  }
  return tags;
}
function renderLatestActivity(worktrees, sessions) {
  const root = byId(ids.activity);
  clear(root);
  const items = arr(sessions).map((session) => {
    const match = matchSessionWorktree(session, worktrees);
    const platform = platformMeta(sessionPlatform(session));
    return {
      date: parseDate(session.last_activity),
      label: match ? clean(match.branch) : basename(session.project) || basename(session.worktree) || "unmatched",
      worktree: match,
      platform,
      snippet: sessionDisplayTitle(session),
      when: session.last_activity,
    };
  }).filter((item) => item.date);
  arr(worktrees).forEach((wt) => {
    const commit = obj(wt.last_commit);
    const date = parseDate(commit.date);
    if (!date) return;
    items.push({
      date,
      label: worktreeFolderName(wt),
      worktree: wt,
      platform: platformMeta("git-commit"),
      snippet: clean(commit.subject) || "Last commit",
      when: commit.date,
    });
  });
  items.sort((a, b) => b.date.getTime() - a.date.getTime());
  if (!items.length) {
    root.appendChild(emptyState("No recent activity found."));
    return;
  }
  items.slice(0, 8).forEach((item) => {
    const row = el("div", "activity-item worktree-activity");
    const target = item.worktree ? worktreeTargetId(worktreeKey(item.worktree)) : "sessions";
    const name = button(item.label, "mono-link");
    name.addEventListener("click", () => scrollToId(target));
    append(row, name, chip(item.platform.label, item.platform.cls), el("span", "activity-snippet", item.snippet), timeNode(item.when));
    root.appendChild(row);
  });
}
function renderWorktrees() {
  const worktrees = sortWorktrees(getLayer("worktrees")).filter((wt) => worktreeState(worktreeKey(wt)).active);
  const branches = getLayer("branches");
  const sessions = getLayer("sessions");
  const prByBranch = new Map(branches.map((branch) => [clean(branch.name), branch.pr]));
  const root = byId(ids.worktrees);
  clear(root);
  if (!worktrees.length) {
    root.appendChild(emptyState("No active worktrees."));
  } else {
    worktrees.forEach((wt) => root.appendChild(worktreeCard(wt, prByBranch.get(clean(wt.branch)), sessions)));
  }
}
function renderWorktreeLivePanels() {
  sortWorktrees(getLayer("worktrees"))
    .filter((wt) => worktreeState(worktreeKey(wt)).active)
    .forEach((wt) => {
      const branch = worktreeKey(wt);
      const root = byId(worktreeLivePanelId(branch));
      if (!root) return;
      clear(root);
      append(root, worktreeStatusLine(wt), agentLightsRow(wt));
    });
}
function renderBranches() {
  renderBranchTimeline(getLayer("branches"));
}
function sortWorktrees(worktrees) {
  return [...worktrees].sort((a, b) => {
    const branchA = worktreeKey(a);
    const branchB = worktreeKey(b);
    const stateA = worktreeState(branchA);
    const stateB = worktreeState(branchB);
    if (stateA.active !== stateB.active) return stateA.active ? -1 : 1;
    if (stateA.active) {
      const orderA = stateA.order === null ? Number.MAX_SAFE_INTEGER : stateA.order;
      const orderB = stateB.order === null ? Number.MAX_SAFE_INTEGER : stateB.order;
      if (orderA !== orderB) return orderA - orderB;
      return worktreeRecency(b) - worktreeRecency(a) || worktreeFolderName(a).localeCompare(worktreeFolderName(b));
    }
    const deactivatedA = parseDate(stateA.deactivated_at);
    const deactivatedB = parseDate(stateB.deactivated_at);
    return (deactivatedB ? deactivatedB.getTime() : 0) - (deactivatedA ? deactivatedA.getTime() : 0) || worktreeRecency(b) - worktreeRecency(a) || worktreeFolderName(a).localeCompare(worktreeFolderName(b));
  });
}
function worktreeRecency(wt) {
  const latest = latestSessionForWorktree(clean(wt.path), getLayer("sessions"), clean(wt.branch));
  const sessionDate = parseDate(latest && latest.last_activity);
  const commitDate = parseDate(obj(wt.last_commit).date);
  return Math.max(sessionDate ? sessionDate.getTime() : 0, commitDate ? commitDate.getTime() : 0);
}
function branchNameButton(name, wt) {
  const node = button("", "branch-name-link b");
  fillWrapLabel(node, name);
  const color = branchColorForName(name) || (wt ? readableBranchColor(worktreeBranchTextColor(wt)) : "");
  if (color) node.style.color = color;
  node.addEventListener("click", () => openCommitDrawer(name));
  return node;
}
function readableBranchColor(color) {
  const value = clean(color);
  const match = value.match(/^#([0-9a-f]{6})$/i);
  if (!match) return value;
  const n = Number.parseInt(match[1], 16);
  const r0 = (n >> 16) & 255;
  const g0 = (n >> 8) & 255;
  const b0 = n & 255;
  const luminanceOf = (rr, gg, bb) => (0.2126 * rr + 0.7152 * gg + 0.0722 * bb) / 255;
  if (luminanceOf(r0, g0, b0) >= 0.28) return value;
  // Lighten dark YAML colors just enough to stay readable on the dark table background.
  let mix = 0.4;
  let r = r0;
  let g = g0;
  let b = b0;
  while (luminanceOf(r, g, b) < 0.42 && mix <= 0.75) {
    r = Math.round(r0 + (255 - r0) * mix);
    g = Math.round(g0 + (255 - g0) * mix);
    b = Math.round(b0 + (255 - b0) * mix);
    mix += 0.1;
  }
  return `#${[r, g, b].map((part) => part.toString(16).padStart(2, "0")).join("")}`;
}
function parseWorktreeColorsYaml(text) {
  const source = String(text || "");
  const foregroundMatch = source.match(/^foreground:\s*["']?([^"'\n]+)/m);
  const rules = [];
  const chunks = source.split(/\n\s*-\s*id:\s*/).slice(1);
  chunks.forEach((chunk) => {
    const id = clean((chunk.match(/^([^\s\n]+)/) || [])[1]);
    const background = clean((chunk.match(/background:\s*["']([^"']+)["']/) || [])[1]);
    if (!background) return;
    const foreground = clean((chunk.match(/(?:^|\n)\s*foreground:\s*["']([^"']+)["']/) || [])[1]);
    const nameContains = clean((chunk.match(/name_contains:\s*([^\s\n]+)/) || [])[1]);
    const nameExact = clean((chunk.match(/name_exact:\s*([^\s\n]+)/) || [])[1]);
    const branch = clean((chunk.match(/^\s*branch:\s*([^\s\n]+)/m) || [])[1]);
    const allRaw = clean((chunk.match(/name_contains_all:\s*\[([^\]]+)\]/) || [])[1]);
    const rule = { id, background };
    if (foreground) rule.foreground = foreground;
    if (nameContains) rule.name_contains = nameContains;
    if (nameExact) rule.name_exact = nameExact;
    if (branch) rule.branch = branch;
    if (allRaw) rule.name_contains_all = allRaw.split(",").map((part) => clean(part)).filter(Boolean);
    rules.push(rule);
  });
  return {
    foreground: clean(foregroundMatch && foregroundMatch[1]) || "#ffffff",
    rules,
  };
}
async function loadColorRules() {
  // Single source of truth: apps/holodeck/worktree-colors.yaml (never hardcode the rule list).
  const candidates = ["/api/file?path=apps/holodeck/worktree-colors.yaml"];
  if (SAMPLE_MODE) candidates.push("../worktree-colors.yaml");
  for (const url of candidates) {
    try {
      let text = "";
      if (url.startsWith("/api/")) {
        const payload = await fetchJson(url, { cache: "no-store" });
        text = payload && payload.content;
      } else {
        const response = await fetch(url, { cache: "no-store" });
        if (!response.ok) continue;
        text = await response.text();
      }
      const parsed = parseWorktreeColorsYaml(text);
      if (arr(parsed.rules).length) {
        state.colorRules = parsed;
        return state.colorRules;
      }
    } catch (_error) {
      // try next candidate
    }
  }
  state.colorRules = state.colorRules || { foreground: "#ffffff", rules: [] };
  return state.colorRules;
}
function lineageAccepted(branchValue) {
  const lineage = obj(obj(branchValue).lineage);
  return lineage.authoritative === true && ["structurally-verified", "evidence-validated"].includes(clean(lineage.status));
}
function lineageStatusText(lineageValue) {
  const status = clean(obj(lineageValue).status);
  const labels = {
    root: "root",
    "structurally-verified": "structurally verified",
    "evidence-validated": "evidence validated",
    pending: "pending review",
    invalid: "invalid record",
    unsupported: "unsupported record",
    missing: "missing lineage record",
    "parent-ref-missing": "parent ref missing",
    "ref-diverged": "local/remote refs diverged",
  };
  return labels[status] || status || "missing lineage record";
}
function lineageDeclaredParent(branchValue) {
  return clean(obj(obj(branchValue).lineage).parent_branch).replace(/^origin\//, "");
}
function acceptedLineageParentName(branchValue) {
  return lineageAccepted(branchValue) ? lineageDeclaredParent(branchValue) : "";
}
function deterministicBranchHue(branchName) {
  const text = clean(branchName);
  let hash = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) % 360;
}
function deterministicBranchFallback(branchName) {
  return `hsl(${deterministicBranchHue(branchName)} 68% 58%)`;
}
function deterministicBranchFallbackForeground(branchName) {
  const hue = deterministicBranchHue(branchName);
  const saturation = 0.68;
  const lightness = 0.58;
  const amplitude = saturation * Math.min(lightness, 1 - lightness);
  const channel = (offset) => {
    const sector = (offset + hue / 30) % 12;
    return lightness - amplitude * Math.max(-1, Math.min(sector - 3, 9 - sector, 1));
  };
  const linear = (value) => (
    value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
  );
  const luminance = 0.2126 * linear(channel(0))
    + 0.7152 * linear(channel(8))
    + 0.0722 * linear(channel(4));
  return luminance > 0.19 ? "#0d1117" : "#ffffff";
}
function branchTimelineColor(branchValue) {
  const branch = obj(branchValue);
  const name = clean(branch.name);
  const assigned = branchAssignedColors(name);
  return {
    background: clean(obj(assigned).background) || deterministicBranchFallback(name),
    foreground: assigned
      ? clean(obj(assigned).foreground) || clean(branchColorRules().foreground) || "#ffffff"
      : deterministicBranchFallbackForeground(name),
    source: assigned ? "configured" : "deterministic-fallback",
  };
}
function compareBranchNames(left, right) {
  return left.localeCompare(right);
}
function branchTimelineCycleNames(parentByName) {
  const cycles = new Set();
  for (const start of parentByName.keys()) {
    const path = [];
    const position = new Map();
    let current = start;
    while (parentByName.has(current)) {
      if (position.has(current)) {
        path.slice(position.get(current)).forEach((name) => cycles.add(name));
        break;
      }
      position.set(current, path.length);
      path.push(current);
      current = parentByName.get(current);
    }
  }
  return cycles;
}
function branchForkTime(branchValue) {
  const date = parseDate(obj(obj(branchValue).lineage).fork_date);
  return date ? date.getTime() : 0;
}
function branchTipTime(branchValue) {
  const date = parseDate(obj(branchValue).date);
  return date ? date.getTime() : 0;
}
function branchTimelineGroups(rows) {
  const groups = [];
  let current = null;
  arr(rows).forEach((row) => {
    const rootGroup = clean(row.root_group) || clean(row.name);
    if (!current || current.root_group !== rootGroup) {
      current = { root_group: rootGroup, rows: [] };
      groups.push(current);
    }
    current.rows.push(row);
  });
  return groups;
}
function branchTimelineTimeRange(byName, rows) {
  let minTime = Number.POSITIVE_INFINITY;
  let maxTime = Number.NEGATIVE_INFINITY;
  arr(rows).forEach((row) => {
    const time = branchForkTime(byName.get(row.name));
    if (!time) return;
    minTime = Math.min(minTime, time);
    maxTime = Math.max(maxTime, time);
  });
  if (!Number.isFinite(minTime) || !Number.isFinite(maxTime)) {
    return { minTime: 0, maxTime: 0, span: 0 };
  }
  return { minTime, maxTime, span: Math.max(0, maxTime - minTime) };
}
function branchTimelineDateRatio(time, range) {
  if (!time || !range || !range.span) return time ? 0 : 1;
  return Math.min(1, Math.max(0, (range.maxTime - time) / range.span));
}
function buildBranchTimelineModel(branchValues, sortMode) {
  const byName = new Map();
  arr(branchValues).forEach((branchValue) => {
    const branch = obj(branchValue);
    const name = clean(branch.name);
    if (name && !byName.has(name)) byName.set(name, branch);
  });
  const names = [...byName.keys()].sort(compareBranchNames);
  const parentByName = new Map();
  names.forEach((name) => {
    const branch = byName.get(name);
    const parent = acceptedLineageParentName(branch);
    if (parent && parent !== name && byName.has(parent)) parentByName.set(name, parent);
  });
  const cycleNames = branchTimelineCycleNames(parentByName);
  cycleNames.forEach((name) => parentByName.delete(name));
  const childrenByName = new Map(names.map((name) => [name, []]));
  parentByName.forEach((parent, child) => childrenByName.get(parent).push(child));
  // Activity sort uses the newest tip commit date in each lineage subtree
  // (the card "X hours ago" value), not the group's fork_date rail times.
  const activityByName = new Map();
  const subtreeActivity = (name) => {
    if (activityByName.has(name)) return activityByName.get(name);
    let latest = branchTipTime(byName.get(name));
    for (const child of childrenByName.get(name) || []) {
      latest = Math.max(latest, subtreeActivity(child));
    }
    activityByName.set(name, latest);
    return latest;
  };
  names.forEach(subtreeActivity);
  const byActivity = (left, right) => (
    activityByName.get(right) - activityByName.get(left)
    || branchTipTime(byName.get(right)) - branchTipTime(byName.get(left))
    || branchForkTime(byName.get(right)) - branchForkTime(byName.get(left))
    || compareBranchNames(left, right)
  );
  const orderedChildren = (parent) => {
    const children = [...(childrenByName.get(parent) || [])];
    if (sortMode === "alphabetical" && parent === "main") {
      return children.sort(compareBranchNames);
    }
    return children.sort(byActivity);
  };
  // Keep each parent→child chain contiguous (children above parent) in both sort modes.
  const flatten = (name, depth, rootGroup, rows) => {
    orderedChildren(name).forEach((child) => flatten(child, depth + 1, rootGroup, rows));
    rows.push({ name, depth, root_group: rootGroup });
  };
  const timelineRows = [];
  const rootGroups = byName.has("main") ? orderedChildren("main") : [];
  rootGroups.forEach((name) => flatten(name, 1, name, timelineRows));
  if (byName.has("main")) timelineRows.push({ name: "main", depth: 0, root_group: "main" });
  const unlinkedRoots = names
    .filter((name) => name !== "main" && !parentByName.has(name))
    .sort(sortMode === "alphabetical" ? compareBranchNames : byActivity);
  const unlinkedRows = [];
  unlinkedRoots.forEach((name) => flatten(name, 0, name, unlinkedRows));
  const edges = [...parentByName.entries()]
    .map(([child, parent]) => ({ parent, child }))
    .sort((left, right) => compareBranchNames(left.child, right.child));
  const linkedGroups = branchTimelineGroups(timelineRows.filter((row) => row.name !== "main"));
  const timeRange = branchTimelineTimeRange(byName, [...timelineRows, ...unlinkedRows]);
  return {
    byName,
    childrenByName,
    parentByName,
    edges,
    cycleNames,
    activityByName,
    rootGroups,
    timelineRows,
    linkedGroups,
    unlinkedRoots,
    unlinkedRows,
    unlinkedGroups: branchTimelineGroups(unlinkedRows),
    timeRange,
  };
}
function lineageEvidenceText(lineageValue) {
  const lineage = obj(lineageValue);
  const record = obj(lineage.record);
  const errors = arr(lineage.errors).map((item) => clean(obj(item).message)).filter(Boolean);
  const parts = [];
  if (hasValue(record.evidence_type)) parts.push(clean(record.evidence_type).replaceAll("-", " "));
  if (hasValue(record.evidence)) parts.push(clean(record.evidence));
  if (errors.length) parts.push(errors.join("; "));
  return parts.join(" · ");
}
function forkDateLabel(branchValue) {
  const value = clean(obj(obj(branchValue).lineage).fork_date);
  const match = value.match(/^(\d{4}-\d{2}-\d{2})/);
  return match ? match[1] : "";
}
function svgEl(name, attrs) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(obj(attrs)).forEach(([key, value]) => {
    if (value == null || value === false) return;
    node.setAttribute(key, String(value));
  });
  return node;
}
function disconnectBranchTimelineEdges() {
  if (!branchTimelineEdgeObserver) return;
  branchTimelineEdgeObserver.disconnect();
  branchTimelineEdgeObserver = null;
}
function branchTimelineAnchorY(layoutRect, cardRect) {
  return cardRect.top + (cardRect.height / 2) - layoutRect.top;
}
function branchTimelineMarkerDefs(prefix) {
  const defs = svgEl("defs");
  const parentMarker = svgEl("marker", {
    id: `${prefix}-parent-arrow`,
    markerWidth: "8",
    markerHeight: "8",
    refX: "6",
    refY: "3",
    orient: "auto",
    markerUnits: "strokeWidth",
  });
  parentMarker.appendChild(svgEl("path", { d: "M0,0 L6,3 L0,6 Z", fill: "#8aa4c0" }));
  const dateMarker = svgEl("marker", {
    id: `${prefix}-date-arrow`,
    markerWidth: "7",
    markerHeight: "7",
    refX: "5",
    refY: "3",
    orient: "auto",
    markerUnits: "strokeWidth",
  });
  dateMarker.appendChild(svgEl("path", { d: "M0,0 L5,3 L0,6 Z", fill: "#5f7a96" }));
  append(defs, parentMarker, dateMarker);
  return defs;
}
function paintBranchGroupEdges(groupNode, model) {
  if (!groupNode || !groupNode.isConnected) return;
  const svg = groupNode.querySelector(".branch-edge-layer");
  const rail = groupNode.querySelector(".branch-time-rail");
  if (!svg || !rail) return;
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  const layoutRect = groupNode.getBoundingClientRect();
  const railRect = rail.getBoundingClientRect();
  const width = Math.max(1, groupNode.clientWidth);
  const height = Math.max(1, groupNode.clientHeight);
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  const markerPrefix = `branch-edge-${safeId(groupNode.dataset.rootGroup || "group")}`;
  svg.appendChild(branchTimelineMarkerDefs(markerPrefix));
  const railX = Math.max(18, Math.min(railRect.width - 28, 70));
  const padTop = 10;
  const padBottom = 10;
  const usable = Math.max(1, height - padTop - padBottom);
  const dateYForTime = (time) => {
    if (!time) return padTop + usable;
    return padTop + (usable * branchTimelineDateRatio(time, model.timeRange));
  };
  const cardNodes = new Map();
  groupNode.querySelectorAll(".branch-timeline-card[data-branch]").forEach((card) => {
    cardNodes.set(clean(card.dataset.branch), card);
  });
  const ticks = svgEl("g", { class: "branch-date-ticks", "aria-hidden": "true" });
  const parentLines = svgEl("g", { class: "branch-parent-edges", "aria-hidden": "true" });
  const dateLines = svgEl("g", { class: "branch-date-edges", "aria-hidden": "true" });
  append(svg, ticks, dateLines, parentLines);
  ticks.appendChild(svgEl("line", {
    class: "branch-time-axis-line",
    x1: railX,
    y1: padTop,
    x2: railX,
    y2: padTop + usable,
  }));
  const seenDates = new Set();
  cardNodes.forEach((card, name) => {
    const branch = model.byName.get(name);
    const date = forkDateLabel(branch);
    const cardRect = card.getBoundingClientRect();
    const cardY = branchTimelineAnchorY(layoutRect, cardRect);
    const cardLeft = cardRect.left - layoutRect.left;
    if (date) {
      const targetY = dateYForTime(branchForkTime(branch));
      const tickKey = `${date}:${Math.round(targetY)}`;
      if (!seenDates.has(tickKey)) {
        seenDates.add(tickKey);
        ticks.appendChild(svgEl("circle", {
          class: "branch-date-tick",
          cx: railX,
          cy: targetY,
          r: 3.2,
        }));
        const label = svgEl("text", {
          class: "branch-date-tick-label",
          x: Math.max(2, railX - 8),
          y: targetY + 3,
          "text-anchor": "end",
        });
        label.textContent = date;
        ticks.appendChild(label);
      }
      dateLines.appendChild(svgEl("path", {
        class: "branch-date-edge",
        d: `M ${cardLeft - 1} ${cardY} L ${railX + 4} ${targetY}`,
        fill: "none",
        "marker-end": `url(#${markerPrefix}-date-arrow)`,
      }));
    }
    if (name === "main") {
      ticks.appendChild(svgEl("circle", {
        class: "branch-date-tick root",
        cx: railX,
        cy: cardY,
        r: 3.2,
      }));
      const rootLabel = svgEl("text", {
        class: "branch-date-tick-label",
        x: Math.max(2, railX - 8),
        y: cardY + 3,
        "text-anchor": "end",
      });
      rootLabel.textContent = "root";
      ticks.appendChild(rootLabel);
      return;
    }
    const parent = model.parentByName.get(name);
    const parentCard = parent ? cardNodes.get(parent) : null;
    if (!parentCard) return;
    const parentRect = parentCard.getBoundingClientRect();
    const parentLeft = parentRect.left - layoutRect.left;
    const parentTop = parentRect.top - layoutRect.top;
    // L-shaped parent edge: left out of child, then down onto the parent's top-left corner.
    parentLines.appendChild(svgEl("path", {
      class: "branch-parent-edge",
      d: `M ${cardLeft - 1} ${cardY} L ${parentLeft} ${cardY} L ${parentLeft} ${parentTop}`,
      fill: "none",
      "marker-end": `url(#${markerPrefix}-parent-arrow)`,
    }));
  });
}
function paintBranchTimelineEdges(layout, model) {
  if (!layout || !layout.isConnected) return;
  layout.querySelectorAll(".branch-group-layout").forEach((groupNode) => {
    paintBranchGroupEdges(groupNode, model);
  });
}
function bindBranchTimelineEdges(layout, model) {
  disconnectBranchTimelineEdges();
  const paint = () => paintBranchTimelineEdges(layout, model);
  requestAnimationFrame(() => requestAnimationFrame(paint));
  if (typeof ResizeObserver === "function") {
    branchTimelineEdgeObserver = new ResizeObserver(paint);
    branchTimelineEdgeObserver.observe(layout);
    layout.querySelectorAll(".branch-group-layout").forEach((groupNode) => {
      branchTimelineEdgeObserver.observe(groupNode);
    });
  }
}
function renderBranchTimelineGroup(group, model, unlinked) {
  const section = el("section", `branch-group${unlinked ? " unlinked" : ""}`);
  section.dataset.rootGroup = clean(group.root_group);
  const layout = el("div", "branch-group-layout");
  layout.dataset.rootGroup = clean(group.root_group);
  const rail = el("div", "branch-time-rail");
  rail.setAttribute("aria-hidden", "true");
  const list = el("ol", `branch-timeline-list${unlinked ? " unlinked-list" : ""}`);
  list.setAttribute("role", "tree");
  list.setAttribute("aria-label", unlinked
    ? `Unlinked branch group ${clean(group.root_group)}`
    : `Branch lineage group ${clean(group.root_group)}`);
  arr(group.rows).forEach((row) => list.appendChild(branchTimelineRow(row, model, unlinked)));
  const svg = svgEl("svg", {
    class: "branch-edge-layer",
    "aria-hidden": "true",
  });
  append(layout, rail, list, svg);
  section.appendChild(layout);
  return section;
}
function renderBranchTimeline(branches) {
  const root = byId(ids.branchTimeline);
  const status = byId(ids.branchTimelineStatus);
  const legend = byId(ids.branchTimelineLegend);
  disconnectBranchTimelineEdges();
  clear(root);
  clear(legend);
  updateBranchTimelineControls();
  const model = buildBranchTimelineModel(branches, state.branchTimelineSort);
  if (!model.byName.size) {
    status.textContent = "No branches found.";
    root.appendChild(emptyState("No branch timeline is available."));
    return;
  }
  let fallbackCount = 0;
  model.byName.forEach((branch) => {
    if (branchTimelineColor(branch).source === "deterministic-fallback") fallbackCount += 1;
  });
  const sortLabel = state.branchTimelineSort === "alphabetical"
    ? "first-level groups alphabetical"
    : "newest tip activity in group first";
  status.textContent = `${model.byName.size} branches · ${model.edges.length} authoritative edges · ${model.linkedGroups.length} lineage groups · ${model.unlinkedRoots.length} unlinked groups · ${fallbackCount} fallback colors · ${sortLabel}`;
  append(
    legend,
    branchTimelineLegendItem("parent → child L-edge", "edge"),
    branchTimelineLegendItem("fork-date → group timeline", "date-edge"),
    branchTimelineLegendItem("configured worktree color", "configured"),
    branchTimelineLegendItem("deterministic fallback", "fallback"),
    branchTimelineLegendItem("unaccepted or orphaned", "unlinked"),
  );
  const layout = el("div", "branch-timeline-layout");
  const groups = el("div", "branch-groups");
  groups.setAttribute("role", "presentation");
  model.linkedGroups.forEach((group) => groups.appendChild(renderBranchTimelineGroup(group, model, false)));
  if (model.byName.has("main")) {
    const mainGroup = {
      root_group: "main",
      rows: [{ name: "main", depth: 0, root_group: "main" }],
    };
    groups.appendChild(renderBranchTimelineGroup(mainGroup, model, false));
  }
  if (model.unlinkedGroups.length) {
    const unlinked = el("section", "branch-unlinked");
    append(
      unlinked,
      el("h3", "sub", "Unlinked declarations"),
      el("p", "sec-lede", "No connection to main is drawn unless the selected lineage record is accepted."),
    );
    const unlinkedGroups = el("div", "branch-groups unlinked-groups");
    model.unlinkedGroups.forEach((group) => unlinkedGroups.appendChild(renderBranchTimelineGroup(group, model, true)));
    unlinked.appendChild(unlinkedGroups);
    groups.appendChild(unlinked);
  }
  append(layout, groups);
  append(root, layout);
  bindBranchTimelineEdges(layout, model);
}
function branchTimelineLegendItem(label, kind) {
  const item = el("span", "branch-timeline-legend-item");
  const marker = el("span", `branch-timeline-legend-marker ${kind}`);
  marker.setAttribute("aria-hidden", "true");
  append(item, marker, textNode(label));
  return item;
}
function branchValidationDetails(lineageValue) {
  const lineage = obj(lineageValue);
  const record = obj(lineage.record);
  const details = el("div", "branch-validation-details");
  details.hidden = !state.branchValidationVisible;
  const context = [
    clean(record.lineage_type),
    clean(record.relationship),
    clean(record.update_reason),
  ].filter(Boolean).join(" · ");
  const fork = clean(lineage.fork_commit);
  const recordCommit = clean(record.commit);
  const evidence = lineageEvidenceText(lineage);
  append(
    details,
    el("span", `parent-state ${safeId(clean(lineage.status) || "missing")}`, lineageStatusText(lineage)),
    context ? el("span", "muted small lineage-context", context) : null,
    fork ? el("span", "muted small", `fork ${shortSha(fork)} · ${clean(lineage.fork_subject)}`) : null,
    recordCommit ? el("span", "muted small", `record ${shortSha(recordCommit)} · review ${clean(record.review_status) || "unknown"}`) : null,
    evidence ? el("span", "muted small lineage-error", evidence) : null,
  );
  return details;
}
function branchTimelineRow(row, model, unlinked) {
  const name = clean(row.name);
  const branch = model.byName.get(name);
  const lineage = obj(branch.lineage);
  const status = clean(lineage.status) || "missing";
  const acceptedParent = model.parentByName.get(name) || "";
  const declaredParent = lineageDeclaredParent(branch);
  const colors = branchTimelineColor(branch);
  const item = el("li", `branch-timeline-row${unlinked ? " unlinked" : ""}`);
  item.id = branchRowId(name);
  item.style.setProperty("--branch-depth", String(row.depth));
  item.setAttribute("role", "treeitem");
  item.setAttribute("aria-level", String(row.depth + 1));
  const date = forkDateLabel(branch);
  const isRoot = status === "root";
  const isUnlinked = !isRoot && !acceptedParent;
  const relationship = acceptedParent
    ? `accepted parent ${acceptedParent}`
    : isRoot
      ? "repository root"
      : declaredParent
        ? `declared parent ${declaredParent}; no accepted edge`
        : "no accepted parent declaration";
  const card = el("article", `branch-timeline-card status-${safeId(status)}${isUnlinked ? " unlinked" : ""}`);
  card.dataset.branch = name;
  card.dataset.colorSource = colors.source;
  if (date) card.dataset.forkDate = date;
  card.style.setProperty("--branch-color", colors.background);
  card.setAttribute("aria-label", `${name}; ${lineageStatusText(lineage)}; ${relationship}${date ? `; forked ${date}` : ""}`);
  const header = el("div", "branch-timeline-header");
  header.style.background = colors.background;
  header.style.color = colors.foreground;
  const nameNode = button("", "branch-timeline-name");
  fillWrapLabel(nameNode, name);
  nameNode.title = `Open commits for ${name}`;
  nameNode.addEventListener("click", () => openCommitDrawer(name));
  header.appendChild(nameNode);
  const body = el("div", "branch-timeline-body");
  const hierarchy = el("div", "branch-timeline-hierarchy");
  const relationshipNode = el("span", "branch-timeline-relationship", relationship);
  if (isUnlinked) relationshipNode.classList.add("unlinked");
  const forkNode = date
    ? el("span", "branch-fork-date-inline muted small mono", `fork ${date}`)
    : (isRoot ? el("span", "branch-fork-date-inline muted small mono", "root") : null);
  append(hierarchy, relationshipNode, forkNode, branchValidationDetails(lineage));
  const metadata = el("div", "branch-timeline-metadata");
  const tip = el("div", "branch-tip");
  const tipSha = clean(branch.tip);
  const tipMeta = [tipSha ? shortSha(tipSha) : "", clean(branch.author)]
    .filter(Boolean)
    .join(" · ");
  append(
    tip,
    el("span", "branch-tip-subject", clean(branch.subject) || tipSha || "No commit subject"),
    tipMeta ? el("span", "muted small mono", tipMeta) : null,
  );
  const facts = el("div", "branch-timeline-facts");
  append(facts, timeNode(branch.date, "—"), driftText(branch));
  const wt = worktreeForBranch(name);
  if (wt) {
    const wtNode = button(worktreeFolderName(wt), "linklike scope");
    wtNode.addEventListener("click", () => scrollToId(worktreeTargetId(worktreeKey(wt))));
    facts.appendChild(wtNode);
  }
  append(facts, prPill(branch.pr));
  append(metadata, tip, facts);
  append(body, hierarchy, metadata);
  append(card, header, body);
  item.appendChild(card);
  return item;
}
function branchRowId(branch) {
  return `branch-${safeId(branch)}`;
}
function openCommitDrawer(branch) {
  const name = clean(branch);
  const drawer = byId(ids.commitDrawer);
  byId(ids.commitBackdrop).classList.remove("hidden");
  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
  byId(ids.commitDrawerTitle).textContent = name || "Branch";
  state.commitDrawer = { branch: name, commits: [], skip: 0, hasMore: false, loading: false };
  if (SAMPLE_MODE) {
    byId(ids.commitDrawerStatus).textContent = "sample read-only";
    const body = byId(ids.commitDrawerBody);
    clear(body);
    append(body, el("div", "callout", "Sample mode does not fetch branch commits from the live API."));
    return;
  }
  byId(ids.commitDrawerStatus).textContent = "loading commits";
  clear(byId(ids.commitDrawerBody));
  byId(ids.commitDrawerBody).appendChild(emptyState("Loading commits..."));
  loadBranchCommits();
}
function closeCommitDrawer() {
  byId(ids.commitBackdrop).classList.add("hidden");
  byId(ids.commitDrawer).classList.remove("open");
  byId(ids.commitDrawer).setAttribute("aria-hidden", "true");
}
async function loadBranchCommits() {
  if (SAMPLE_MODE || state.commitDrawer.loading || !hasValue(state.commitDrawer.branch)) return;
  state.commitDrawer.loading = true;
  renderCommitDrawer();
  const branch = state.commitDrawer.branch;
  const skip = state.commitDrawer.skip;
  try {
    const payload = await fetchJson(`/api/branch-commits?branch=${encodeURIComponent(branch)}&skip=${skip}&limit=20`, { cache: "no-store" });
    const commits = arr(payload && payload.commits);
    state.commitDrawer.commits = state.commitDrawer.commits.concat(commits);
    state.commitDrawer.skip = state.commitDrawer.commits.length;
    state.commitDrawer.hasMore = payload && payload.has_more === true;
    byId(ids.commitDrawerStatus).textContent = `${state.commitDrawer.commits.length} commit${state.commitDrawer.commits.length === 1 ? "" : "s"}`;
  } catch (error) {
    byId(ids.commitDrawerStatus).textContent = "error";
    state.commitDrawer.error = clean(error.message) || "Unable to load commits.";
  } finally {
    state.commitDrawer.loading = false;
    renderCommitDrawer();
  }
}
function renderCommitDrawer() {
  const body = byId(ids.commitDrawerBody);
  clear(body);
  if (state.commitDrawer.error) {
    body.appendChild(el("div", "callout red", state.commitDrawer.error));
    return;
  }
  if (!state.commitDrawer.commits.length) {
    body.appendChild(emptyState(state.commitDrawer.loading ? "Loading commits..." : "No commits found."));
  } else {
    const list = el("div", "commit-list");
    state.commitDrawer.commits.forEach((commit) => list.appendChild(commitItem(commit)));
    body.appendChild(list);
  }
  if (state.commitDrawer.hasMore || state.commitDrawer.loading) {
    const loadMore = button(state.commitDrawer.loading ? "Loading" : "Load more", "action-btn");
    loadMore.disabled = state.commitDrawer.loading;
    loadMore.addEventListener("click", loadBranchCommits);
    body.appendChild(loadMore);
  }
}
function commitItem(commitValue) {
  const commit = obj(commitValue);
  const item = el("div", "commit-item");
  const meta = el("div", "commit-meta");
  append(meta, el("span", "mono muted", clean(commit.sha) || "commit"), hasValue(commit.date) ? textNode(" · ") : null, timeNode(commit.date, ""));
  const subject = el("div", "commit-subject", clean(commit.subject) || "(no subject)");
  const body = clean(commit.body);
  append(item, meta, subject);
  if (body) item.appendChild(el("div", "commit-body", body));
  return item;
}
function cursorFocusFailure(payloadValue, status) {
  const payload = obj(payloadValue);
  const error = obj(payload.error);
  const detail = obj(payload.detail);
  const source = Object.keys(error).length ? error : Object.keys(detail).length ? detail : payload;
  const code = clean(source.code || payload.code).toLowerCase();
  const serverMessage = clean(source.message || (typeof payload.detail === "string" ? payload.detail : payload.message));
  if (["permission_required", "permission_denied", "accessibility_denied", "automation_denied"].includes(code)) {
    return {
      kind: "permission",
      message: "Permission needed: allow the app running Holodeck in System Settings › Privacy & Security › Accessibility and Automation, then retry.",
    };
  }
  if (["app_not_running", "cursor_not_running"].includes(code)) {
    return { kind: "error", stale: true, message: "Cursor is not running. Start Cursor with this worktree, refresh Holodeck, and retry." };
  }
  if (["target_not_found", "not_found", "cursor_window_not_found"].includes(code) || status === 404) {
    return { kind: "error", stale: true, message: "That Cursor window is no longer open. Refresh Holodeck to update its live status." };
  }
  if (["ambiguous_match", "multiple_matches"].includes(code)) {
    return { kind: "error", message: "More than one Cursor window matched this worktree. Give its folder or workspace a unique title, then retry." };
  }
  if (["focus_busy", "busy"].includes(code)) {
    return { kind: "error", message: "Another focus request is already running. Try again in a moment." };
  }
  if (["automation_timeout", "timeout"].includes(code) || status === 504) {
    return { kind: "error", message: "Cursor did not respond in time. Retry the focus action." };
  }
  if (["unsupported_platform", "unsupported_target"].includes(code) || status === 501) {
    return { kind: "error", message: "Window focusing is available only when Holodeck is running on macOS." };
  }
  return { kind: "error", message: serverMessage || "Holodeck could not focus that Cursor window. Retry or refresh the snapshot." };
}
async function requestCursorFocus(worktreePath) {
  let response;
  try {
    response = await fetch("/api/focus", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Holodeck-Action": "focus",
      },
      body: JSON.stringify({ target: "cursor", matcher: { worktree_path: clean(worktreePath) } }),
    });
  } catch (error) {
    const requestError = new Error("Holodeck could not reach the local focus service. Retry after confirming the server is running.");
    requestError.kind = "error";
    throw requestError;
  }
  let payload = {};
  try {
    payload = await response.json();
  } catch (error) {
    payload = {};
  }
  if (!response.ok || payload.ok !== true) {
    const failure = cursorFocusFailure(payload, response.status);
    const requestError = new Error(failure.message);
    requestError.kind = failure.kind;
    requestError.stale = failure.stale === true;
    throw requestError;
  }
  return payload;
}
function cursorFocusControl(wt, folder, statusId) {
  if (!wtIsCursorOpen(wt)) return null;
  if (SAMPLE_MODE) return chip("go to window", "open");
  const wrap = el("div", "cursor-focus-control");
  const focusButton = button("go to window", "pill open cursor-focus-button");
  const statusNode = el("span", "cursor-focus-status");
  statusNode.id = statusId;
  statusNode.setAttribute("role", "status");
  statusNode.setAttribute("aria-live", "polite");
  statusNode.hidden = true;
  focusButton.setAttribute("aria-label", `Go to the open Cursor window for ${folder}`);
  focusButton.setAttribute("aria-describedby", statusId);
  focusButton.title = `Go to the open Cursor window for ${folder}`;
  focusButton.addEventListener("click", async () => {
    focusButton.disabled = true;
    focusButton.setAttribute("aria-busy", "true");
    focusButton.textContent = "focusing…";
    statusNode.className = "cursor-focus-status pending";
    statusNode.textContent = `Focusing Cursor window for ${folder}…`;
    statusNode.hidden = false;
    try {
      await requestCursorFocus(wt.path);
      focusButton.textContent = "focused";
      focusButton.removeAttribute("aria-busy");
      statusNode.className = "cursor-focus-status success";
      statusNode.textContent = `Cursor window for ${folder} focused.`;
      window.setTimeout(() => {
        if (!focusButton.isConnected) return;
        focusButton.disabled = false;
        focusButton.removeAttribute("aria-busy");
        focusButton.textContent = "go to window";
        statusNode.hidden = true;
        statusNode.textContent = "";
        statusNode.className = "cursor-focus-status";
      }, 1400);
    } catch (error) {
      focusButton.disabled = error.stale === true;
      focusButton.removeAttribute("aria-busy");
      focusButton.textContent = "go to window";
      if (error.stale === true) {
        focusButton.classList.remove("open");
        focusButton.setAttribute("aria-label", `Cursor window for ${folder} is unavailable`);
      }
      statusNode.className = `cursor-focus-status ${error.kind === "permission" ? "permission" : "error"}`;
      statusNode.textContent = clean(error.message) || "Holodeck could not focus that Cursor window.";
    }
  });
  append(wrap, focusButton, statusNode);
  return wrap;
}
function worktreeCard(wt, pr, sessions) {
  const key = worktreeKey(wt);
  const branch = clean(wt.branch) || "detached";
  const folder = worktreeFolderName(wt);
  const entry = worktreeState(key);
  const expanded = state.expandedWorktrees.has(key);
  const colors = worktreeTitleBarColors(wt);
  const cursorOpen = wtIsCursorOpen(wt);
  const card = el("article", `card worktree-card collapsible${expanded ? " expanded" : ""}${entry.active ? "" : " inactive"}${cursorOpen ? " cursor-open" : " cursor-closed"}`);
  card.id = worktreeCardId(key);
  card.draggable = !SAMPLE_MODE && entry.active;
  addDragHandlers(card, key, entry.active);
  const titleBar = el("div", "worktree-title-bar");
  titleBar.style.background = colors.background;
  titleBar.style.color = colors.foreground;
  const body = el("div", "worktree-card-body");
  const titleToggle = button("", "worktree-title-toggle");
  titleToggle.setAttribute("aria-expanded", expanded ? "true" : "false");
  titleToggle.setAttribute("aria-label", `${expanded ? "Collapse" : "Expand"} worktree ${folder}`);
  titleToggle.addEventListener("click", () => toggleWorktree(key));
  titleToggle.appendChild(el("span", "worktree-folder-name", folder));
  append(titleBar, titleToggle, cursorFocusControl(wt, folder, `${card.id}-cursor-focus-status`));
  const head = el("div", "card-head");
  const handle = button("⠿", "drag-handle");
  handle.title = SAMPLE_MODE ? "Sample mode" : "Drag to reorder active worktrees";
  handle.disabled = SAMPLE_MODE || !entry.active;
  const title = el("h3");
  const branchButton = branchIdentityButton(branch, wt, "link-pill");
  if (branchButton) branchButton.addEventListener("click", () => scrollToId(branchRowId(branch)));
  // The detached marker comes from the branch identity itself; do not add a
  // separate Park control to every card.
  append(title, branchButton);
  const tools = el("div", "card-tools");
  const top = button("top", "copy-btn move-top");
  top.disabled = SAMPLE_MODE || !entry.active;
  top.addEventListener("click", () => moveWorktreeToTop(key));
  const chevron = button(expanded ? "⌃" : "⌄", "chevron");
  chevron.setAttribute("aria-label", expanded ? "Collapse worktree" : "Expand worktree");
  chevron.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleWorktree(key);
  });
  append(tools, top, chevron);
  append(head, handle, title, tools);
  const summary = worktreeControls(key, entry);
  const appChips = worktreeAppChips(wt, false);
  const sessionRows = worktreeSessionRows(wt, sessions);
  append(body, worktreeLivePanel(wt), head, summary, sessionRows, appChips.childNodes.length ? appChips : null);
  if (expanded) append(body, worktreeExpanded(wt, pr, sessions, entry));
  append(card, titleBar, body);
  return card;
}
function worktreeLivePanel(wt) {
  const branch = worktreeKey(wt);
  const panel = el("div", "worktree-live-panel");
  panel.id = worktreeLivePanelId(branch);
  append(panel, worktreeStatusLine(wt), agentLightsRow(wt));
  return panel;
}
function worktreeLivePanelId(branch) {
  return `worktree-live-${safeId(branch)}`;
}
function worktreeStatusLine(wt) {
  const rowData = latestTurnStatusForWorktree(wt);
  if (!rowData) return el("div", "worktree-status-line quiet", "No recent turn status");
  const line = button("", `worktree-status-line ${turnStateClass(rowData.state)}`);
  const title = el("span", "turn-title", rowData.title);
  append(line, turnStateBadge(rowData.state), title, el("span", "turn-elapsed", relativeTime(rowData.since) || "time unknown"));
  if (hasValue(rowData.session_label)) line.appendChild(el("span", "turn-session-label", rowData.session_label));
  line.addEventListener("click", () => openSession(sessionForTurnStatus(rowData)));
  line.addEventListener("mouseenter", () => showTurnStatusTooltip(line, rowData));
  line.addEventListener("mouseleave", hideSessionTooltip);
  line.addEventListener("focus", () => showTurnStatusTooltip(line, rowData));
  line.addEventListener("blur", hideSessionTooltip);
  return line;
}
function latestTurnStatusForWorktree(wt) {
  const key = worktreeKey(wt);
  const branch = clean(wt.branch);
  return normalizeTurnStatus(state.turnStatus)
    .filter((status) => clean(status.origin || "operator") !== "delegated")
    .map((status) => turnStatusRowData(status, getLayer("worktrees")))
    .filter((row) => clean(row.path) === clean(wt.path) || (row.wt && clean(row.wt.path) === clean(wt.path)) || (!isDetachedBranch(branch) && clean(row.branch) === branch) || clean(row.branch) === key)
    .sort((a, b) => (b.date ? b.date.getTime() : 0) - (a.date ? a.date.getTime() : 0))[0] || null;
}
function turnStateClass(value) {
  return clean(value) === "waiting-on-ai" ? "thinking" : "done";
}
function agentLightsRow(wt) {
  const row = el("div", "agent-lights-row");
  const agents = agentsForWorktree(wt);
  if (!agents.length) {
    row.appendChild(el("span", "small muted", "No agent lights"));
    return row;
  }
  agents.forEach((agent) => {
    const meta = agentStateMeta(agent);
    const light = button("", `agent-light ${meta.cls}`);
    light.setAttribute("aria-label", `Open ${agentTitle(agent)}`);
    light.title = agentTitle(agent);
    light.addEventListener("click", () => openSession(sessionForAgent(agent)));
    light.addEventListener("mouseenter", () => showTurnStatusTooltip(light, { title: agentTitle(agent), recap: clean(agent.recap) || clean(agent.user_preview) }));
    light.addEventListener("mouseleave", hideSessionTooltip);
    light.addEventListener("focus", () => showTurnStatusTooltip(light, { title: agentTitle(agent), recap: clean(agent.recap) || clean(agent.user_preview) }));
    light.addEventListener("blur", hideSessionTooltip);
    row.appendChild(light);
  });
  return row;
}
function agentsForWorktree(wt) {
  const branch = clean(wt.branch);
  const path = clean(wt.path);
  return sortedAgents(state.agents).filter((agent) => clean(agent.worktree) === path || (!isDetachedBranch(branch) && clean(agent.branch) === branch));
}
function worktreeExpanded(wt, pr, sessions, entry) {
  const key = worktreeKey(wt);
  const branch = clean(wt.branch) || "detached";
  const box = el("div", "expanded-body");
  const pathRow = el("div", "path-copy");
  append(pathRow, el("div", "path", clean(wt.path) || "path unavailable"), copyButton(wt.path, "copy path"));
  const badges = el("div", "badge-row");
  append(badges, driftPills(wt));
  if (wt.is_current) append(badges, chip("current", "teal"));
  if (wt.missing) append(badges, chip("missing", "closed"));
  if (asCount(wt.dirty) > 0) append(badges, chip(`${asCount(wt.dirty)} dirty`, "gold"));
  if (asCount(wt.untracked) > 0) append(badges, chip(`${asCount(wt.untracked)} untracked`, "gold"));
  if (asCount(wt.unpushed) > 0) append(badges, chip(`${asCount(wt.unpushed)} unpushed`, "gold"));
  append(badges, prPill(pr));
  const commit = obj(wt.last_commit);
  const commitNode = el("p", "desc");
  append(commitNode, textNode(clean(commit.subject) || "No commit subject"), hasValue(commit.date) ? textNode(" · ") : null, timeNode(commit.date, ""));
  const match = branchEntry(branch);
  const lineage = obj(match && match.lineage);
  const record = obj(lineage.record);
  const acceptedParent = match && lineageAccepted(match) ? acceptedLineageParentName(match) : "—";
  const declaredParent = lineageDeclaredParent(match);
  const review = clean(record.review_status)
    ? [clean(record.review_status), clean(record.reviewed_by), clean(record.reviewed_at)].filter(Boolean).join(" · ")
    : "—";
  const validation = arr(lineage.errors)
    .map((item) => clean(obj(item).message))
    .filter(Boolean)
    .join("; ") || "none";
  const detailNode = el("div", "detail-grid");
  append(
    detailNode,
    detailItem("upstream", wt.upstream || "—"),
    detailItem("accepted parent", acceptedParent),
    detailItem("declared parent", declaredParent || "—"),
    detailItem("lineage state", lineageStatusText(lineage)),
    detailItem("record type", clean(record.lineage_type) || "—"),
    detailItem("relationship / update", [clean(record.relationship), clean(record.update_reason)].filter(Boolean).join(" / ") || "—"),
    detailItem("review", review),
    detailItem("fork commit", clean(lineage.fork_commit) || "—"),
    detailItem("fork subject", clean(lineage.fork_subject) || "—"),
    detailItem("record commit", clean(record.commit) || "—"),
    detailItem("lineage ID", clean(record.lineage_id) || "v1 / none"),
    detailItem("record ID", clean(record.record_id) || "v1 / none"),
    detailItem("evidence", lineageEvidenceText(lineage) || "—"),
    detailItem("validation", validation),
    detailItem("purpose", clean(lineage.branch_purpose) || "—")
  );
  const notes = el("textarea", "notes-area");
  notes.placeholder = "Notes";
  notes.value = entry.notes;
  notes.disabled = SAMPLE_MODE;
  notes.addEventListener("blur", () => saveWorktreeField(key, { notes: notes.value.trim() || null }, false));
  const linkedApps = worktreeAppChips(wt, true);
  append(
    box,
    pathRow,
    badges,
    commitNode,
    detailNode,
    linkedApps.childNodes.length ? labeledBlock("Apps touched", linkedApps) : null,
    labeledBlock("Notes", notes)
  );
  return box;
}
function worktreeControls(branch, entry) {
  const tracker = el("div", "cycle-tracker worktree-controls");
  if (SHOW_PRIMARY_AI_INTERFACE) {
    tracker.appendChild(labeledControl("Primary AI interface", primaryInterfaceSelect(branch, entry)));
  }
  tracker.appendChild(worktreeStepsControl(branch, entry.steps));
  return tracker;
}
function primaryInterfaceSelect(branch, entry) {
  const select = el("select", "state-select primary-interface-select");
  PRIMARY_INTERFACE_OPTIONS.forEach(([value, label]) => {
    const option = el("option", "", label);
    option.value = value;
    option.selected = clean(entry.primary_interface) === value;
    select.appendChild(option);
  });
  select.disabled = SAMPLE_MODE;
  select.addEventListener("change", () => {
    const value = clean(select.value);
    saveWorktreeField(branch, { primary_interface: value || null }, "active-inline");
  });
  return select;
}
function worktreeStepsControl(branch, steps) {
  const wrap = el("div", "worktree-steps");
  const input = el("input", "state-input next-step-field");
  input.type = "text";
  input.placeholder = "Add to-do";
  input.disabled = SAMPLE_MODE;
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      addWorktreeStep(branch, input.value);
      input.value = "";
    }
    if (event.key === "Escape") {
      input.value = "";
      input.blur();
    }
  });
  const list = el("div", "worktree-step-list");
  const normalized = normalizeStepList(steps);
  if (!normalized.length) {
    list.appendChild(el("div", "small muted", "No to-dos"));
  } else {
    normalized.forEach((item) => list.appendChild(worktreeStepItem(branch, item)));
  }
  append(wrap, labeledControl("to-do", input), list);
  return wrap;
}
function worktreeStepItem(branch, item) {
  const row = el("div", `next-step-item worktree-step-item${item.done ? " done" : ""}`);
  row.dataset.id = item.id;
  row.draggable = !SAMPLE_MODE;
  addWorktreeStepDragHandlers(row, branch, item.id);
  const grip = button("⠿", "drag-mini");
  grip.title = SAMPLE_MODE ? "Sample mode" : "Drag to reorder";
  grip.disabled = SAMPLE_MODE;
  const check = el("input", "next-step-check");
  check.type = "checkbox";
  check.checked = item.done;
  check.disabled = SAMPLE_MODE;
  check.addEventListener("change", () => updateWorktreeStep(branch, item.id, { done: check.checked }));
  const text = el("input", "next-step-text next-step-text-input");
  text.type = "text";
  text.value = item.text;
  text.disabled = SAMPLE_MODE;
  text.setAttribute("aria-label", "Edit to-do");
  const saveText = () => {
    const value = text.value.trim();
    if (!value) {
      text.value = item.text;
      return;
    }
    if (value !== item.text) updateWorktreeStep(branch, item.id, { text: value });
  };
  text.addEventListener("blur", saveText);
  text.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      text.blur();
    }
    if (event.key === "Escape") {
      text.value = item.text;
      text.blur();
    }
  });
  const promote = button("↑", "mini-delete promote-step");
  promote.disabled = SAMPLE_MODE;
  promote.title = "Move to global To-do";
  promote.setAttribute("aria-label", "Move to global To-do");
  promote.addEventListener("click", () => promoteWorktreeStep(branch, item));
  const remove = button("×", "mini-delete");
  remove.disabled = SAMPLE_MODE;
  remove.setAttribute("aria-label", "Delete to-do");
  remove.addEventListener("click", () => deleteWorktreeStep(branch, item.id));
  append(row, grip, check, text, promote, remove);
  return row;
}
function currentWorktreeSteps(branch) {
  return normalizeStepList(obj(state.userState.worktrees[branch]).steps);
}
function saveWorktreeSteps(branch, steps) {
  return saveWorktreeField(branch, { steps: normalizeStepList(steps) }, true);
}
function addWorktreeStep(branch, text) {
  const value = clean(text).trim();
  if (!value || SAMPLE_MODE) return;
  saveWorktreeSteps(branch, [newStep(value), ...currentWorktreeSteps(branch)]);
}
function updateWorktreeStep(branch, stepId, patch) {
  if (SAMPLE_MODE) return;
  const id = clean(stepId);
  const steps = currentWorktreeSteps(branch).map((item) => item.id === id ? normalizeStepItem({ ...item, ...patch }) : item);
  saveWorktreeSteps(branch, steps);
}
function deleteWorktreeStep(branch, stepId) {
  if (SAMPLE_MODE) return;
  const id = clean(stepId);
  saveWorktreeSteps(branch, currentWorktreeSteps(branch).filter((item) => item.id !== id));
}
function addWorktreeStepDragHandlers(row, branch, stepId) {
  if (SAMPLE_MODE) return;
  row.addEventListener("dragstart", (event) => {
    state.draggingWorktreeStep = { branch, id: stepId };
    event.dataTransfer.effectAllowed = "move";
    row.classList.add("dragging");
  });
  row.addEventListener("dragend", () => {
    state.draggingWorktreeStep = null;
    row.classList.remove("dragging");
  });
  row.addEventListener("dragover", (event) => {
    const dragging = state.draggingWorktreeStep;
    if (!dragging || dragging.branch !== branch || dragging.id === stepId) return;
    event.preventDefault();
  });
  row.addEventListener("drop", (event) => {
    event.preventDefault();
    const dragging = state.draggingWorktreeStep;
    if (!dragging || dragging.branch !== branch || dragging.id === stepId) return;
    reorderWorktreeSteps(branch, dragging.id, stepId);
  });
}
function reorderWorktreeSteps(branch, source, target) {
  const steps = currentWorktreeSteps(branch);
  const moving = steps.find((item) => item.id === source);
  if (!moving) return;
  const reordered = steps.filter((item) => item.id !== source);
  const index = Math.max(0, reordered.findIndex((item) => item.id === target));
  reordered.splice(index, 0, moving);
  saveWorktreeSteps(branch, reordered);
}
async function promoteWorktreeStep(branch, itemValue) {
  if (SAMPLE_MODE) return;
  const item = normalizeStepItem(itemValue);
  if (!hasValue(item.text)) return;
  const existingIds = normalizeStepList(state.userState.next_steps).map((step) => step.id);
  try {
    const created = normalizeStepItem(await fetchJson("/api/next-steps", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: item.text, source: clean(branch) || null }),
    }));
    state.userState.next_steps = [created, ...normalizeStepList(state.userState.next_steps).filter((step) => step.id !== created.id)];
    const updated = await fetchJson("/api/next-steps-order", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order: [created.id, ...existingIds] }),
    });
    const list = Array.isArray(updated) ? updated : arr(updated && updated.next_steps);
    state.userState.next_steps = normalizeStepList(list);
    await saveWorktreeSteps(branch, currentWorktreeSteps(branch).filter((step) => step.id !== item.id));
    renderTodoPanel();
    renderWorktrees();
  } catch (error) {
    showError("Could not move to-do.", clean(error.message));
    reloadStateOnly();
  }
}
function worktreeSessionRows(wt, sessions) {
  const recent = recentSessionsForWorktree(clean(wt.path), sessions, 3, clean(wt.branch));
  const list = el("div", "worktree-session-list");
  if (!recent.length) {
    list.appendChild(el("div", "small muted", "No matching recent sessions"));
    return list;
  }
  recent.forEach((session) => {
    const platform = platformMeta(sessionPlatform(session));
    const row = button("", "worktree-session-row");
    const toolName = el("span", "session-tool-name", sessionDisplayTitle(session));
    toolName.addEventListener("mouseenter", () => showSessionTooltip(toolName, session));
    toolName.addEventListener("mouseleave", hideSessionTooltip);
    toolName.addEventListener("focus", () => showSessionTooltip(toolName, session));
    toolName.addEventListener("blur", hideSessionTooltip);
    append(row, dot(platform.cls), toolName, sessionHost(session) === "cloud" ? tag("cloud") : null, sessionRemoteControl(session) ? tag("RC") : null, timeNode(session.last_activity, "—"));
    row.addEventListener("click", () => openSession(session));
    list.appendChild(row);
  });
  return list;
}
function labeledBlock(label, child) {
  const block = el("div", "detail-block");
  append(block, el("div", "detail-label", label), child);
  return block;
}
function labeledControl(label, control) {
  const wrapper = el("label", "field-stack");
  append(wrapper, el("span", "field-label", label), control);
  return wrapper;
}
function detailItem(label, value) {
  const item = el("div", "detail-item");
  append(item, el("div", "detail-label", label), el("div", "detail-value", value));
  return item;
}
function branchEntry(branch) {
  return getLayer("branches").find((item) => clean(item.name) === clean(branch)) || null;
}
function stateField(branch, field, value, placeholder, className) {
  const input = el("input", `state-input ${className || ""}`);
  input.type = "text";
  input.value = clean(value);
  input.placeholder = placeholder;
  input.disabled = SAMPLE_MODE;
  input.addEventListener("click", (event) => event.stopPropagation());
  const save = () => {
    const next = input.value.trim();
    const current = clean(value);
    if (next === current) return;
    const patch = {};
    patch[field] = next || null;
    saveWorktreeField(branch, patch, true);
  };
  input.addEventListener("blur", save);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      input.blur();
    }
    if (event.key === "Escape") {
      input.value = clean(value);
      input.blur();
    }
  });
  return input;
}
function statusSelect(branch, value) {
  const select = el("select", `state-select review-status ${safeId(value)}`);
  DONE_STATUS.forEach((status) => {
    const option = el("option", "", status);
    option.value = status;
    option.selected = status === value;
    select.appendChild(option);
  });
  select.disabled = SAMPLE_MODE;
  select.addEventListener("click", (event) => event.stopPropagation());
  select.addEventListener("change", () => saveWorktreeField(branch, { last_done_status: select.value }, true));
  return select;
}
function activeToggleButton(branch, active) {
  const nextActive = !active;
  const btn = button(active ? "PARK" : "ACTIVATE", `pill active-toggle ${active ? "gold" : "teal"}`);
  btn.disabled = SAMPLE_MODE;
  btn.setAttribute("aria-pressed", active ? "true" : "false");
  btn.title = active ? "Park this worktree" : "Activate this worktree";
  btn.setAttribute("aria-label", `${active ? "Park" : "Activate"} ${branch}`);
  btn.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    saveWorktreeField(branch, { active: nextActive, deactivated_at: nextActive ? null : new Date().toISOString() }, true);
  });
  return btn;
}
async function saveWorktreeField(branch, patch, rerender) {
  if (SAMPLE_MODE) return;
  setLocalWorktreeState(branch, patch);
  if (rerender) rerenderStateSurfaces(rerender);
  try {
    const updated = await fetchJson(`/api/state/worktree/${encodeURIComponent(branch)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    state.userState.worktrees[branch] = updated;
    if (rerender) rerenderStateSurfaces(rerender);
  } catch (error) {
    showError(`Could not save ${branch}.`, clean(error.message));
    await reloadStateOnly();
  }
}
// scope "active-inline" avoids replacing worktree cards while controls inside them have focus.
// Any rerender restores the window scroll so wholesale DOM swaps don't jump the page.
function rerenderStateSurfaces(scope) {
  const scrollY = window.scrollY;
  renderTodoPanel();
  renderAgentDeck();
  if (scope === "active-inline") {
    renderUniverse();
  } else {
    renderWorktrees();
    renderBranches();
    renderUniverse();
  }
  window.scrollTo(0, scrollY);
}
async function reloadStateOnly() {
  if (SAMPLE_MODE) return;
  try {
    state.userState = normalizeUserState(await fetchJson("/api/state", { cache: "no-store" }));
    rerenderStateSurfaces();
  } catch (error) {
    showError("Could not reload state.", clean(error.message));
  }
}
function addDragHandlers(card, branch, active) {
  if (SAMPLE_MODE || !active) return;
  card.addEventListener("dragstart", (event) => {
    state.draggingBranch = branch;
    event.dataTransfer.effectAllowed = "move";
    card.classList.add("dragging");
  });
  card.addEventListener("dragend", () => {
    state.draggingBranch = null;
    card.classList.remove("dragging");
  });
  card.addEventListener("dragover", (event) => {
    if (!state.draggingBranch || state.draggingBranch === branch) return;
    event.preventDefault();
  });
  card.addEventListener("drop", (event) => {
    event.preventDefault();
    if (!state.draggingBranch || state.draggingBranch === branch) return;
    reorderWorktrees(state.draggingBranch, branch);
  });
}
function activeBranchOrder() {
  return sortWorktrees(getLayer("worktrees")).filter((wt) => worktreeState(worktreeKey(wt)).active).map((wt) => worktreeKey(wt));
}
function reorderWorktrees(source, target) {
  const order = activeBranchOrder().filter((branch) => branch !== source);
  const index = Math.max(0, order.indexOf(target));
  order.splice(index, 0, source);
  persistWorktreeOrder(order);
}
function moveWorktreeToTop(branch) {
  const order = activeBranchOrder().filter((item) => item !== branch);
  order.unshift(branch);
  persistWorktreeOrder(order);
}
async function persistWorktreeOrder(order) {
  order.forEach((branch, index) => setLocalWorktreeState(branch, { order: index }));
  getLayer("worktrees").forEach((wt) => {
    const branch = worktreeKey(wt);
    if (!order.includes(branch)) setLocalWorktreeState(branch, { order: null });
  });
  renderWorktrees();
  if (SAMPLE_MODE) return;
  try {
    const updated = await fetchJson("/api/state/worktree-order", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order }),
    });
    state.userState.worktrees = updated;
    renderWorktrees();
  } catch (error) {
    showError("Could not persist worktree order.", clean(error.message));
    reloadStateOnly();
  }
}
function toggleWorktree(branch) {
  if (state.expandedWorktrees.has(branch)) state.expandedWorktrees.delete(branch);
  else state.expandedWorktrees.add(branch);
  renderWorktrees();
  const id = worktreeCardId(branch);
  // Re-render replaces the DOM node; wait a frame so expand/collapse layout settles, then pin the card to the top.
  requestAnimationFrame(() => {
    requestAnimationFrame(() => scrollToId(id, "auto"));
  });
}
function worktreeCardId(branch) {
  return `worktree-${safeId(branch)}`;
}
function worktreeTargetId(branch) {
  return worktreeState(branch).active ? worktreeCardId(branch) : parkedWorktreeRowId(branch);
}
function worktreeAppChips(wt, linked) {
  const row = el("div", "tag-row app-chip-row");
  arr(wt.apps_touched).forEach((slug) => {
    const label = clean(slug);
    if (!label) return;
    if (linked) {
      const node = button(label, "pill link-pill");
      node.addEventListener("click", () => scrollToId(appCardId(label)));
      row.appendChild(node);
    } else {
      row.appendChild(chip(label, "gold"));
    }
  });
  return row;
}
function driftPills(item) {
  const nodes = [];
  const ahead = asCount(item.ahead_main);
  const behind = asCount(item.behind_main);
  if (ahead) nodes.push(chip(`ahead ${ahead}`, "gold"));
  if (behind) nodes.push(chip(`behind ${behind}`, "violet"));
  if (!ahead && !behind) nodes.push(chip("even", "teal"));
  return nodes;
}
function driftText(item) {
  const ahead = asCount(item.ahead_main);
  const behind = asCount(item.behind_main);
  if (!ahead && !behind) return el("span", "drift-text", "even");
  return el("span", "drift-text", `+${ahead} / -${behind}`);
}
function prPill(prValue) {
  const pr = obj(prValue);
  if (!hasValue(pr.state) && !hasValue(pr.number)) return null;
  const stateText = pr.is_draft ? "DRAFT" : clean(pr.state) || "PR";
  const cls = pr.is_draft ? "draft" : clean(pr.state).toLowerCase();
  const label = hasValue(pr.number) ? `${stateText} #${pr.number}` : stateText;
  if (hasValue(pr.url)) {
    const node = link(label, pr.url, `pill ${cls}`);
    node.target = "_blank";
    node.rel = "noreferrer";
    return node;
  }
  return chip(label, cls);
}
function latestSessionForWorktree(path, sessions, branch) {
  return recentSessionsForWorktree(path, sessions, 1, branch)[0] || null;
}
function recentSessionsForWorktree(path, sessions, limit, branch) {
  return arr(sessions)
    .filter((session) => {
      if (clean(session.worktree) === path) return true;
      if (!hasValue(branch) || isDetachedBranch(branch)) return false;
      return clean(session.branch) === clean(branch);
    })
    .map((session) => ({ session, date: parseDate(session.last_activity) }))
    .filter((item) => item.date)
    .sort((a, b) => b.date.getTime() - a.date.getTime())
    .slice(0, limit)
    .map((item) => item.session);
}
function matchSessionWorktree(session, worktrees) {
  return arr(worktrees).find((wt) => {
    if (clean(wt.path) === clean(session.worktree)) return true;
    const branch = clean(session.branch);
    if (isDetachedBranch(branch) || isDetachedBranch(wt.branch)) return false;
    return clean(wt.branch) === branch;
  }) || null;
}
function renderAppFilters() {
  const apps = getLayer("apps");
  const kinds = [...new Set(apps.map((app) => clean(app.kind) || "scripts").filter(Boolean))].sort();
  const tags = [...new Set(apps.flatMap((app) => arr(app.tags).map(clean)).filter(Boolean))].sort();
  const bar = byId(ids.appFilters);
  clear(bar);
  append(bar, filterButton("All", "all", state.appFilter.kind === "all" && state.appFilter.tag === "all", () => {
    state.appFilter.kind = "all";
    state.appFilter.tag = "all";
    renderUniverse();
  }));
  kinds.forEach((kind) => {
    append(bar, filterButton(kind, "kind", state.appFilter.kind === kind, () => {
      state.appFilter.kind = kind;
      state.appFilter.tag = "all";
      renderUniverse();
    }));
  });
  tags.forEach((tagValue) => {
    append(bar, filterButton(`#${tagValue}`, "tag", state.appFilter.tag === tagValue, () => {
      state.appFilter.kind = "all";
      state.appFilter.tag = tagValue;
      renderUniverse();
    }));
  });
  const search = el("input", "search");
  search.type = "search";
  search.placeholder = "Search apps";
  search.value = state.appFilter.q;
  search.addEventListener("input", () => {
    state.appFilter.q = search.value;
    renderAppCards();
  });
  bar.appendChild(search);
}
function filterButton(label, mode, active, handler) {
  const btn = button(label, `fbtn${active ? " active" : ""}`);
  btn.dataset.mode = mode;
  btn.addEventListener("click", handler);
  return btn;
}
function renderAppCards() {
  const root = byId(ids.apps);
  clear(root);
  const apps = getLayer("apps");
  const collisions = portCollisions(apps);
  const q = norm(state.appFilter.q);
  const filtered = apps.filter((app) => {
    if (state.appFilter.kind !== "all" && clean(app.kind || "scripts") !== state.appFilter.kind) return false;
    if (state.appFilter.tag !== "all" && !arr(app.tags).map(clean).includes(state.appFilter.tag)) return false;
    if (!q) return true;
    return norm([app.name, app.purpose, app.slug].map(clean).join(" ")).includes(q);
  });
  if (!filtered.length) {
    root.appendChild(emptyState("No apps match the current filters."));
    return;
  }
  filtered.forEach((app) => root.appendChild(appCard(app, collisions)));
}
function appCard(app, collisions) {
  const slug = clean(app.slug) || clean(app.name) || "app";
  const expanded = state.expandedApps.has(slug);
  const card = el("article", `card app-card collapsible${expanded ? " expanded" : ""}${app.registered === false ? " unregistered" : ""}`);
  card.id = appCardId(slug);
  card.addEventListener("click", (event) => {
    if (event.target.closest("button,a,input,textarea,select,label")) return;
    toggleApp(slug);
  });
  const head = el("div", "card-head");
  const title = el("h3");
  append(title, textNode(clean(app.name) || slug), chip(clean(app.kind) || "scripts", "teal"), stagePill(app.stage), specStagePill(app.spec_stage));
  const chevron = button(expanded ? "⌃" : "⌄", "chevron");
  chevron.setAttribute("aria-label", expanded ? "Collapse app" : "Expand app");
  chevron.addEventListener("click", () => toggleApp(slug));
  append(head, title, chevron);
  const touched = appWorktreeChips(slug);
  const flags = appFlags(app);
  const prompt = touched.childNodes.length ? null : promptCopyButton(worktreePromptText("app", slug), "⧉ new worktree prompt");
  append(card, head, touched.childNodes.length ? touched : null, prompt, flags.childNodes.length ? flags : null);
  if (expanded) append(card, appExpanded(app, collisions));
  return card;
}
function appExpanded(app, collisions) {
  const box = el("div", "expanded-body");
  const slug = clean(app.slug) || clean(app.name) || "app";
  const portRow = el("div", "badge-row");
  if (hasValue(app.port)) {
    const cls = collisions.has(clean(app.port)) ? "pink" : "gold";
    append(portRow, chip(`port ${app.port}`, cls));
  }
  if (hasValue(app.local_url)) {
    const local = link(app.local_url, app.local_url);
    local.target = "_blank";
    local.rel = "noreferrer";
    append(portRow, local);
  }
  const deployRow = el("div", "badge-row");
  arr(app.deploy).forEach((deploy) => {
    const item = obj(deploy);
    append(deployRow, chip(clean(item.target) || clean(item.kind) || clean(item.name), ""));
  });
  const activity = el("div", "small muted");
  const commits = asCount(app.commits_30d);
  append(activity, textNode(`${commits} commit${commits === 1 ? "" : "s"} in 30d`));
  if (hasValue(app.last_commit_date)) append(activity, textNode(" · last "), timeNode(app.last_commit_date));
  const tags = el("div", "tag-row");
  arr(app.tags).forEach((value) => append(tags, tag(value)));
  append(
    box,
    hasValue(app.purpose) ? el("p", "desc", app.purpose) : null,
    tags.childNodes.length ? tags : null,
    commandBlock(app.dev_command, "copy dev"),
    commandBlock(app.test_command, "copy test"),
    portRow.childNodes.length ? portRow : null,
    deployRow.childNodes.length ? deployRow : null,
    hasValue(app.notes) ? el("div", "note", app.notes) : null,
    activity,
    registryBlock(),
    appOpenSpecBlock(slug, app)
  );
  return box;
}
function registryBlock() {
  const repoRoot = clean(state.snapshot && state.snapshot.repo_root);
  const path = repoRoot ? joinPath(repoRoot, "apps/holodeck/registry.yaml") : "apps/holodeck/registry.yaml";
  return labeledBlock("Registry", fileLink("apps/holodeck/registry.yaml", path, "file-row"));
}
function appOpenSpecBlock(slug, app) {
  const stores = getLayer("specs").filter((spec) => specMatchesApp(spec, slug, app));
  if (!stores.length) return null;
  const block = el("div", "openspec-block");
  append(block, el("h4", "", "OpenSpec"));
  stores.forEach((spec) => {
    const store = el("div", "openspec-store");
    append(store, el("div", "small muted", basename(spec.store_path) || clean(spec.app) || "store"));
    arr(spec.spec_files).forEach((file) => {
      append(store, fileLink(`${clean(file.domain) || "spec"} spec`, file.path, "file-row"));
    });
    arr(spec.changes).forEach((change) => append(store, changeBlock(change)));
    const archived = arr(spec.archived);
    if (archived.length) {
      const details = el("details");
      append(details, el("summary", "", `${archived.length} archived`));
      archived.forEach((item) => append(details, archivedLink(item)));
      store.appendChild(details);
    }
    block.appendChild(store);
  });
  return block;
}
function appFlags(app) {
  const flags = el("div", "flag-row");
  if (app.has_readme === false) append(flags, chip("no-readme ⚠", "gold"));
  if (app.has_tests === false) append(flags, chip("no-tests", "violet"));
  if (app.openspec === true) append(flags, chip("openspec ✓", "teal"));
  if (app.registered === false) append(flags, chip("unregistered", "draft"));
  return flags;
}
function appWorktreeChips(slug) {
  const row = el("div", "tag-row worktree-chip-row");
  getLayer("worktrees").forEach((wt) => {
    if (!arr(wt.apps_touched).map(clean).includes(clean(slug))) return;
    const key = worktreeKey(wt);
    const folder = worktreeFolderName(wt);
    const node = button(folder, "pill link-pill");
    node.addEventListener("click", () => scrollToId(worktreeTargetId(key)));
    row.appendChild(node);
  });
  return row;
}
function appCardId(slug) {
  return `app-${safeId(slug)}`;
}
function toggleApp(slug) {
  if (state.expandedApps.has(slug)) state.expandedApps.delete(slug);
  else state.expandedApps.add(slug);
  renderAppCards();
}
function stagePill(stage) {
  const meta = STAGE_META[clean(stage)];
  return meta ? chip(meta.label, meta.cls) : null;
}
function specStagePill(stage) {
  const meta = SPEC_STAGE_META[clean(stage)];
  return meta ? chip(meta.label, meta.cls) : null;
}
function linkedSpecStagePill(stage, target) {
  const meta = SPEC_STAGE_META[clean(stage)];
  if (!meta) return null;
  const node = button(meta.label, `pill ${meta.cls} link-pill`);
  node.addEventListener("click", () => scrollToId(target));
  return node;
}
function portCollisions(apps) {
  const counts = new Map();
  apps.forEach((app) => {
    if (!hasValue(app.port)) return;
    const key = clean(app.port);
    counts.set(key, (counts.get(key) || 0) + 1);
  });
  return new Set([...counts.entries()].filter(([, count]) => count > 1).map(([port]) => port));
}
function renderCoreTable() {
  const tbody = byId(ids.core);
  clear(tbody);
  const modules = getLayer("core");
  if (!modules.length) {
    tbody.appendChild(tableRow([tableCell(emptyState("No core modules found.")), tableCell(), tableCell(), tableCell()]));
    return;
  }
  modules.forEach((module) => {
    tbody.appendChild(tableRow([
      tableCell(el("span", "b", clean(module.module) || "module")),
      tableCell(clean(module.description) ? textNode(module.description) : textNode("—")),
      tableCell(textNode(asCount(module.commits_30d))),
      tableCell(timeNode(module.last_commit_date, "—")),
    ]));
  });
}
function renderSpecs() {
  const root = byId(ids.specs);
  clear(root);
  const specs = getLayer("specs");
  if (!specs.length) {
    const card = el("div", "card static-card");
    append(card, emptyState("No OpenSpec stores found."));
    root.appendChild(card);
    return;
  }
  specs.forEach((spec) => root.appendChild(specCard(spec)));
}
function specCard(spec) {
  const card = el("article", "card spec-card");
  const app = appForSpec(spec);
  const title = el("h3");
  const appTarget = appCardId(clean(app && app.slug) || clean(spec.app));
  const appButton = button(clean(app && app.name) || clean(spec.app) || "spec store", "title-link");
  appButton.addEventListener("click", () => scrollToId(appTarget));
  append(title, appButton, linkedSpecStagePill(app && app.spec_stage, appTarget));
  const chips = el("div", "tag-row");
  const branch = clean(spec.branch);
  if (branch) {
    const branchChip = button(branch, "pill link-pill");
    branchChip.addEventListener("click", () => scrollToId(worktreeTargetId(branch)));
    chips.appendChild(branchChip);
  }
  append(chips, el("span", "muted small", basename(spec.worktree) || "worktree"));
  append(card, title, chips);
  const files = arr(spec.spec_files);
  if (files.length) {
    const list = el("div", "file-list");
    files.forEach((file) => list.appendChild(fileLink(`${clean(file.domain) || "spec"} spec`, file.path, "file-row")));
    append(card, labeledBlock("Spec files", list));
  }
  const changes = arr(spec.changes);
  if (!changes.length) append(card, emptyState("No active changes."));
  changes.forEach((change) => append(card, changeBlock(change)));
  const archived = arr(spec.archived);
  if (archived.length) {
    const details = el("details");
    const summary = el("summary", "", `${archived.length} archived change${archived.length === 1 ? "" : "s"}`);
    append(details, summary);
    archived.forEach((item) => append(details, archivedLink(item)));
    card.appendChild(details);
  }
  return card;
}
function changeBlock(change) {
  const block = el("div", "change-block");
  const total = asCount(change.tasks_total);
  const done = asCount(change.tasks_done);
  const pct = total ? Math.max(0, Math.min(100, Math.round((done / total) * 100))) : 0;
  const head = el("div", "row space");
  append(head, el("strong", "", clean(change.name) || "change"), chip(`${done}/${total}`, "teal"));
  const wrap = el("div", "progress-wrap");
  const fill = el("div", "progress-fill");
  fill.style.width = `${pct}%`;
  wrap.appendChild(fill);
  const artifacts = el("div", "tag-row");
  arr(change.artifacts).forEach((artifact) => {
    const path = artifactPath(change, artifact);
    if (path) append(artifacts, fileLink(artifact, path, "pill link-pill"));
    else append(artifacts, el("span", "muted small", clean(artifact)));
  });
  append(block, head, wrap, artifacts);
  return block;
}
function artifactPath(change, artifact) {
  const base = clean(change.path);
  const name = clean(artifact);
  if (!base || !name) return "";
  if (FILE_SUFFIXES.some((suffix) => name.endsWith(suffix))) return joinPath(base, name);
  if (name === "proposal" || name === "design" || name === "tasks") return joinPath(base, `${name}.md`);
  if (name.startsWith("specs/")) return joinPath(base, `${name.replace(/\/+$/, "")}/spec.md`);
  return joinPath(base, `${name}.md`);
}
function archivedLink(item) {
  const path = clean(item.path) ? joinPath(item.path, "proposal.md") : "";
  const label = `${clean(item.name) || "archived"}${hasValue(item.date) ? ` · ${item.date}` : ""}`;
  return path ? fileLink(label, path, "file-row") : el("div", "small muted", label);
}
function appForSpec(spec) {
  return getLayer("apps").find((app) => specMatchesApp(spec, clean(app.slug), app)) || null;
}
function specMatchesApp(spec, slug, app) {
  const specApp = norm(spec.app);
  return specApp === norm(slug) || specApp === norm(app && app.name) || specApp === norm(basename(app && app.path));
}
function renderSkills() {
  const root = byId(ids.skills);
  clear(root);
  const skills = getLayer("skills");
  if (!skills.length) {
    root.appendChild(emptyState("No skills found."));
    return;
  }
  const groups = new Map();
  skills.forEach((skill) => {
    const category = clean(skill.category) || "uncategorized";
    groups.set(category, [...(groups.get(category) || []), skill]);
  });
  [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).forEach(([category, list]) => {
    const group = el("div", "card static-card");
    const head = el("div", "group-head");
    append(head, el("h3", "", category), chip(`${list.length}`, ""));
    const items = el("div", "skill-list");
    list.sort((a, b) => clean(a.name).localeCompare(clean(b.name))).forEach((skill) => {
      const item = el("div", "skill-item");
      const row = el("div", "row space");
      append(row, el("span", "b", clean(skill.name) || "skill"), chip(clean(skill.source) || "source", sourceClass(skill.source)));
      append(item, row, hasValue(skill.description) ? el("div", "desc", skill.description) : null);
      items.appendChild(item);
    });
    append(group, head, items);
    root.appendChild(group);
  });
}
function sourceClass(source) {
  const value = clean(source);
  if (value === "shared") return "teal";
  if (value === "claude-skill") return "gold";
  if (value === "claude-command") return "violet";
  if (value === "hermes") return "pink";
  return "";
}
function renderSessions() {
  renderSessionFilters();
  renderSessionRows();
}
function renderSessionFilters() {
  const bar = byId(ids.sessionFilters);
  clear(bar);
  const choices = [
    ["all", "All"],
    ["claude", "Claude"],
    ["codex", "Codex"],
    ["cursor", "Cursor"],
  ];
  choices.forEach(([platform, label]) => {
    append(bar, filterButton(label, "platform", state.sessionFilter.platform === platform, () => {
      state.sessionFilter.platform = platform;
      renderSessionRows();
      renderSessionFilterActive();
    }));
  });
  append(bar, filterButton("machinery", "machinery", state.sessionFilter.machinery, () => {
    state.sessionFilter.machinery = !state.sessionFilter.machinery;
    renderSessionRows();
    renderSessionFilterActive();
  }));
  const search = el("input", "search");
  search.type = "search";
  search.placeholder = "Search AI sessions";
  search.value = state.sessionFilter.q;
  search.addEventListener("input", () => {
    state.sessionFilter.q = search.value;
    renderSessionRows();
  });
  bar.appendChild(search);
}
function renderSessionFilterActive() {
  byId(ids.sessionFilters).querySelectorAll(".fbtn").forEach((filter) => {
    const label = clean(filter.textContent).toLowerCase();
    const active = label === "machinery" ? state.sessionFilter.machinery : state.sessionFilter.platform === "all" ? label === "all" : norm(platformMeta(state.sessionFilter.platform).label) === label;
    filter.classList.toggle("active", active);
  });
}
function renderSessionRows() {
  const tbody = byId(ids.sessions);
  clear(tbody);
  const q = norm(state.sessionFilter.q);
  const sessions = getLayer("sessions").filter((session) => {
    if (!state.sessionFilter.machinery && sessionOrigin(session) === "delegated") return false;
    if (state.sessionFilter.platform !== "all" && sessionPlatform(session) !== state.sessionFilter.platform) return false;
    if (!q) return true;
    return norm([session.label, sessionDisplayTitle(session), session.first_user, session.branch].map(clean).join(" ")).includes(q);
  });
  if (!sessions.length) {
    tbody.appendChild(tableRow([tableCell(emptyState("No sessions match the current filters.")), tableCell(), tableCell(), tableCell()]));
    return;
  }
  sessions.forEach((session) => {
    const platform = platformMeta(sessionPlatform(session));
    const origin = sessionOrigin(session);
    const match = matchSessionWorktree(session, getLayer("worktrees"));
    const sessionCell = el("div", "session-cell");
    const titleLine = el("div", "session-title-line");
    append(titleLine, dot(platform.cls), el("span", "session-title-main", sessionDisplayTitle(session)));
    if (origin === "delegated") titleLine.appendChild(tag("delegated"));
    append(titleLine, sessionContextTags(session));
    const labelLine = el("div", "session-subline");
    append(labelLine, textNode(sessionDisplayLabel(session)));
    const entrypoint = entrypointPill(session);
    if (entrypoint) labelLine.appendChild(entrypoint);
    append(sessionCell, titleLine, labelLine);
    const worktreeCell = sessionWorktreeBranchCell(session, match);
    const when = el("div", "time-pair");
    append(when, timeNode(session.last_activity, "—"), hasValue(session.last_activity) ? el("span", "mono muted", localTimestamp(session.last_activity)) : null);
    const tr = tableRow([
      tableCell(sessionCell),
      tableCell(worktreeCell),
      tableCell(hasValue(session.exchanges) ? textNode(session.exchanges) : (hasValue(session.messages) ? textNode(session.messages) : textNode("—"))),
      tableCell(when),
    ], `session-row${origin === "delegated" ? " delegated" : ""}`);
    tr.id = sessionRowId(session);
    tr.tabIndex = 0;
    tr.addEventListener("click", () => openSession(session));
    tr.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openSession(session);
      }
    });
    tbody.appendChild(tr);
  });
}
function sessionWorktreeBranchCell(session, wt) {
  if (!wt) return el("span", "scope muted", basename(session.project) || basename(session.worktree) || "—");
  const branch = clean(session.branch) || clean(wt.branch);
  return branchIdentityPill(branch, wt, "session-branch") || el("span", "scope muted", worktreeFolderName(wt));
}
function sessionOrigin(session) {
  return clean(session && session.origin) === "delegated" ? "delegated" : "operator";
}
function sessionDisplayLabel(session) {
  return clean(session && session.label) || platformMeta(sessionPlatform(session)).label;
}
function sessionDisplayTitle(session) {
  // Prefer the platform chat/session name (e.g. Cursor rename) so list and drawer stay aligned.
  // Digest / turn-status titles are fallbacks only when the session itself has no name.
  const status = turnStatusForSession(session);
  const digest = obj(session && session.digest);
  return clean(session && (session.ai_title || session.title)) ||
    clean(status && (status.turn_title || status.title || status.digest_title)) ||
    clean(session && (session.latest_primary_digest_title || session.latest_turn_title || session.turn_title || session.digest_title)) ||
    clean(digest.title) ||
    trunc(clean(session && session.first_user), 100) ||
    "Untitled session";
}
function setSessionDrawerTitle(session) {
  const node = byId(ids.drawerTitle);
  if (!node) return;
  node.textContent = sessionDisplayTitle(session);
}
function sessionKey(session) {
  const prefix = sessionIdPrefix(session);
  const id = clean(session && session.id);
  if (!prefix || !id) return `${prefix}:${id}`;
  return id.startsWith(`${prefix}:`) ? id : `${prefix}:${id}`;
}
function sessionRowId(session) {
  return `session-${safeId(sessionKey(session))}`;
}
function sessionIdCandidates(session) {
  const prefix = sessionIdPrefix(session);
  const id = clean(session && session.id);
  const values = [clean(session && session.session_id), id];
  if (prefix && id && !id.startsWith(`${prefix}:`)) values.push(`${prefix}:${id}`);
  return new Set(values.filter(Boolean));
}
function sessionMatchesExchange(session, exchange) {
  const ids = sessionIdCandidates(session);
  return ids.has(clean(exchange && exchange.session_id));
}
function sessionMatchesStatus(session, statusValue) {
  const status = obj(statusValue);
  const statusSessionId = clean(status.session_id || status.session || status.session_key);
  if (statusSessionId && sessionIdCandidates(session).has(statusSessionId)) return true;
  const statusId = clean(status.session_id || status.id);
  if (statusId && sessionIdCandidates(session).has(statusId)) return true;
  return false;
}
function turnStatusForSession(session) {
  return normalizeTurnStatus(state.turnStatus).find((status) => sessionMatchesStatus(session, status)) || null;
}
function sessionForTurnStatus(rowData) {
  const status = obj(rowData && rowData.raw);
  const match = getLayer("sessions").find((session) => sessionMatchesStatus(session, status));
  if (match) return match;
  const sessionId = clean(rowData && rowData.session_id) || clean(status.session_id) || "turn-status-session";
  const source = inferSessionSource(sessionId, rowData && rowData.session_label);
  const id = source.prefix && sessionId.startsWith(`${source.prefix}:`) ? sessionId.slice(source.prefix.length + 1) : sessionId;
  return {
    platform: source.platform,
    entrypoint: source.entrypoint,
    host: source.host,
    remote_control: false,
    bridge_session_id: null,
    id,
    session_id: sessionId,
    origin: "operator",
    label: clean(rowData && rowData.session_label) || platformMeta(source.platform).label,
    latest_primary_digest_title: clean(rowData && rowData.title),
    first_user: clean(status.user_preview || status.last_user_preview || rowData && rowData.recap),
    last_user: clean(status.last_user_preview || status.user_preview),
    project: clean(status.project || rowData && rowData.path),
    worktree: clean(status.worktree_path || status.worktree || rowData && rowData.path),
    branch: clean(rowData && rowData.branch),
    last_activity: clean(rowData && rowData.since),
    started: clean(status.user_ts || rowData && rowData.since),
    messages: null,
  };
}
function sessionIdPrefix(session) {
  const id = clean(session && session.id);
  for (const prefix of ["claude-code", "claude-cloud", "codex", "codex-cloud", "cursor"]) {
    if (id.startsWith(`${prefix}:`)) return prefix;
  }
  const platform = sessionPlatform(session);
  const host = sessionHost(session);
  if (platform === "claude") return host === "cloud" ? "claude-cloud" : "claude-code";
  if (platform === "codex") return host === "cloud" ? "codex-cloud" : "codex";
  if (platform === "cursor") return "cursor";
  return "";
}
function inferSessionSource(sessionId, label) {
  const prefix = clean(sessionId).split(":")[0];
  if (prefix === "claude-code") return { prefix, platform: "claude", host: "local", entrypoint: "cli" };
  if (prefix === "claude-cloud") return { prefix, platform: "claude", host: "cloud", entrypoint: "app" };
  if (prefix === "codex-cloud") return { prefix, platform: "codex", host: "cloud", entrypoint: "app" };
  if (prefix === "codex") return { prefix, platform: "codex", host: "local", entrypoint: "cli" };
  if (prefix === "cursor") return { prefix, platform: "cursor", host: "local", entrypoint: "app" };
  const value = norm(label);
  if (value.includes("cursor")) return { prefix: "cursor", platform: "cursor", host: "local", entrypoint: "app" };
  if (value.includes("codex")) return { prefix: "codex", platform: "codex", host: value.includes("cloud") ? "cloud" : "local", entrypoint: value.includes("app") ? "app" : "cli" };
  return { prefix: "claude-code", platform: "claude", host: value.includes("cloud") ? "cloud" : "local", entrypoint: value.includes("app") ? "app" : "cli" };
}
function sessionLabelPill(session, clickable) {
  const platform = platformMeta(sessionPlatform(session));
  const label = sessionDisplayLabel(session);
  if (!clickable) return chip(label, platform.cls);
  const node = button(label, `pill ${platform.cls} link-pill session-label-pill`);
  node.title = sessionDisplayTitle(session);
  node.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    openSession(session);
  });
  return node;
}
function showSessionTooltip(anchor, session) {
  hideSessionTooltip();
  const tooltip = el("div", "session-tooltip");
  const title = sessionDisplayTitle(session);
  const preview = trunc(clean(session.last_user) || clean(session.first_user) || "No user message preview.", 400);
  append(tooltip, el("div", "session-tooltip-title", title), el("div", "session-tooltip-preview", preview));
  document.body.appendChild(tooltip);
  placeTooltip(anchor, tooltip);
}
function placeTooltip(anchor, tooltip) {
  const rect = anchor.getBoundingClientRect();
  const margin = 12;
  const top = Math.min(window.innerHeight - tooltip.offsetHeight - margin, rect.bottom + 8);
  const left = Math.min(window.innerWidth - tooltip.offsetWidth - margin, Math.max(margin, rect.left));
  tooltip.style.top = `${Math.max(margin, top)}px`;
  tooltip.style.left = `${left}px`;
}
function hideSessionTooltip() {
  document.querySelectorAll(".session-tooltip").forEach((node) => node.remove());
}
function openSession(session) {
  hideSessionTooltip();
  const drawer = byId(ids.drawer);
  const backdrop = byId(ids.backdrop);
  const platform = platformMeta(sessionPlatform(session));
  const key = sessionKey(session);
  state.sessionDrawer = emptySessionDrawer();
  state.sessionDrawer.session = session;
  state.sessionDrawer.key = key;
  state.sessionDrawer.turnsLoading = true;
  state.sessionDrawer.messagesLoading = true;
  const drawerTool = byId(ids.drawerTool);
  clear(drawerTool);
  append(drawerTool, dot(platform.cls), textNode(sessionDisplayLabel(session)));
  if (sessionOrigin(session) === "delegated") drawerTool.appendChild(tag("delegated"));
  append(drawerTool, sessionContextTags(session));
  const entrypoint = entrypointPill(session);
  if (entrypoint) drawerTool.appendChild(entrypoint);
  setSessionDrawerTitle(session);
  backdrop.classList.remove("hidden");
  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
  renderSessionDrawer();
  loadSessionTurns(session, key);
  loadSessionMessages(session, key);
}
function closeSessionDrawer() {
  byId(ids.backdrop).classList.add("hidden");
  byId(ids.drawer).classList.remove("open");
  byId(ids.drawer).setAttribute("aria-hidden", "true");
  state.sessionDrawer = emptySessionDrawer();
}
function scrollSessionDrawerToEnd() {
  const body = byId(ids.drawerBody);
  body.scrollTo({ top: body.scrollHeight, behavior: "smooth" });
}
function renderSessionDrawer() {
  const body = byId(ids.drawerBody);
  clear(body);
  if (!state.sessionDrawer.session) {
    body.appendChild(emptyState("No session selected."));
    return;
  }
  append(body, renderTurnsView(), renderSubagentsDetails(), renderRawMessagesDetails());
}
function renderTurnsView() {
  const drawer = state.sessionDrawer;
  const panel = el("section", "turns-view");
  const head = el("div", "turns-head");
  const count = arr(drawer.turns).length;
  const status = drawer.turnsLoading ? "loading" : drawer.turnsError ? "error" : `${count} turn${count === 1 ? "" : "s"}`;
  append(head, el("h3", "", "Turns"), el("span", "small muted", status));
  panel.appendChild(head);
  if (drawer.turnsError) {
    panel.appendChild(el("div", "callout red", drawer.turnsError));
    return panel;
  }
  if (drawer.turnsLoading && drawer.turns === null) {
    panel.appendChild(emptyState("Loading turns..."));
    return panel;
  }
  const turns = arr(drawer.turns);
  if (!turns.length) {
    panel.appendChild(emptyState("No turns found for this session."));
    return panel;
  }
  const list = el("div", "exchange-list");
  turns.forEach((exchange) => list.appendChild(exchangeCard(exchange)));
  panel.appendChild(list);
  return panel;
}
function renderRawMessagesDetails() {
  const drawer = state.sessionDrawer;
  const messages = arr(drawer.messages);
  const details = el("details", "raw-messages-details");
  details.appendChild(el("summary", "", `All messages${messages.length ? ` (${messages.length})` : ""}`));
  if (drawer.messagesError) {
    details.appendChild(el("div", "callout red", drawer.messagesError));
    return details;
  }
  if (drawer.messagesLoading && drawer.messages === null) {
    details.appendChild(emptyState("Loading messages..."));
    return details;
  }
  if (!messages.length) {
    details.appendChild(emptyState("No messages available for this session."));
    return details;
  }
  details.appendChild(messageList(messages));
  return details;
}
function sessionSubagentCount(session) {
  if (!session || !Object.prototype.hasOwnProperty.call(session, "subagent_count")) return null;
  return asCount(session.subagent_count);
}
function renderSubagentsDetails() {
  const drawer = state.sessionDrawer;
  const session = drawer.session;
  if (!session || sessionOrigin(session) !== "operator") return null;
  const count = sessionSubagentCount(session);
  const subagents = arr(drawer.subagents);
  if (count === 0 && !drawer.subagentsFetched) return null;
  if (drawer.subagentsFetched && !drawer.subagentsLoading && !drawer.subagentsError && !subagents.length) return null;
  const details = el("details", "subagents-details");
  if (drawer.subagentsOpen) details.open = true;
  const displayCount = drawer.subagentsFetched ? subagents.length : count;
  details.appendChild(el("summary", "", displayCount === null ? "Subagents" : `Subagents (${displayCount})`));
  if (drawer.subagentsError) {
    details.appendChild(el("div", "callout red", drawer.subagentsError));
  } else if (drawer.subagentsLoading && drawer.subagents === null) {
    details.appendChild(emptyState("Loading subagents..."));
  } else if (subagents.length) {
    const list = el("div", "subagent-list");
    subagents.forEach((subagent) => list.appendChild(subagentCard(subagent)));
    details.appendChild(list);
  } else {
    details.appendChild(emptyState("No subagents found for this session."));
  }
  details.addEventListener("toggle", () => {
    state.sessionDrawer.subagentsOpen = details.open;
    if (details.open) loadSessionSubagents(session, drawer.key);
  });
  return details;
}
function subagentCard(subagentValue) {
  const subagent = obj(subagentValue);
  const item = el("article", "subagent-card");
  const head = el("div", "subagent-head");
  append(head, el("div", "subagent-label", clean(subagent.label) || "Codex subagent"), timeNode(subagent.started || subagent.last_activity, "—"));
  append(item, head);
  if (hasValue(subagent.instruction)) item.appendChild(el("p", "subagent-instruction muted", subagent.instruction));
  if (hasValue(subagent.recap)) item.appendChild(el("p", "subagent-recap", subagent.recap));
  if (!hasValue(subagent.instruction) && !hasValue(subagent.recap)) item.appendChild(emptyState("No exchange text available."));
  return item;
}
async function loadSessionSubagents(session, requestKey) {
  const drawer = state.sessionDrawer;
  if (drawer.key !== requestKey || drawer.subagentsFetched || drawer.subagentsLoading) return;
  drawer.subagentsLoading = true;
  drawer.subagentsError = "";
  renderSessionDrawer();
  try {
    const payload = SAMPLE_MODE ? { subagents: [] } : await fetchJson(`/api/turns/subagents?session=${encodeURIComponent(sessionKey(session))}`, { cache: "no-store" });
    if (state.sessionDrawer.key !== requestKey) return;
    const subagents = arr(payload && payload.subagents);
    state.sessionDrawer.subagents = subagents;
    state.sessionDrawer.subagentsFetched = true;
    state.sessionDrawer.session = { ...state.sessionDrawer.session, subagent_count: subagents.length };
    state.sessionDrawer.subagentsError = "";
  } catch (error) {
    if (state.sessionDrawer.key !== requestKey) return;
    state.sessionDrawer.subagentsError = clean(error.message) || "Unable to load subagents.";
  } finally {
    if (state.sessionDrawer.key === requestKey) {
      state.sessionDrawer.subagentsLoading = false;
      renderSessionDrawer();
    }
  }
}
async function loadSessionTurns(session, requestKey) {
  if (state.sessionDrawer.key === requestKey) {
    state.sessionDrawer.turnsLoading = true;
    state.sessionDrawer.turnsError = "";
    renderSessionDrawer();
  }
  try {
    let payload;
    if (SAMPLE_MODE) {
      payload = await sampleTurnsPayload();
    } else {
      payload = await fetchJson(turnsListUrl(session), { cache: "no-store" });
    }
    if (state.sessionDrawer.key !== requestKey) return;
    state.sessionDrawer.turns = arr(payload && payload.exchanges).filter((exchange) => sessionMatchesExchange(session, exchange));
    // Keep drawer header on sessionDisplayTitle so it cannot drift from the AI Sessions list.
    setSessionDrawerTitle(state.sessionDrawer.session);
    state.sessionDrawer.turnsError = "";
  } catch (error) {
    if (state.sessionDrawer.key !== requestKey) return;
    state.sessionDrawer.turnsError = clean(error.message) || "Unable to load turns.";
  } finally {
    if (state.sessionDrawer.key === requestKey) {
      state.sessionDrawer.turnsLoading = false;
      renderSessionDrawer();
    }
  }
}
function turnsListUrl(session) {
  const params = new URLSearchParams();
  if (hasValue(session && session.branch)) params.set("branch", clean(session.branch));
  if (sessionOrigin(session) === "delegated") params.set("include", "delegated");
  params.set("limit", "80");
  return `/api/turns?${params.toString()}`;
}
async function sampleTurnsPayload() {
  if (state.sampleTurns) return state.sampleTurns;
  state.sampleTurns = await fetchJson(SAMPLE_TURNS_URL, { cache: "no-store" });
  return state.sampleTurns;
}
function exchangeCard(exchangeValue) {
  const exchange = obj(exchangeValue);
  const id = clean(exchange.id);
  const item = el("article", "exchange-card");
  item.id = `exchange-${safeId(id)}`;
  item.dataset.exchangeId = id;
  const head = el("div", "exchange-head");
  const meta = el("div", "row");
  append(meta, turnKindPill(exchange.kind), timeNode(exchange.user_ts, "—"));
  if (clean(exchange.origin) === "delegated") meta.appendChild(tag("delegated"));
  const title = el("div", "exchange-title-block");
  append(title, el("div", "exchange-title", exchangeDisplayTitle(exchange)), hasValue(id) ? el("span", "exchange-id mono muted", id) : null);
  append(head, meta, title);
  append(item, head);
  if (exchangeHasDigest(exchange)) item.appendChild(exchangeDigestBlock(exchange));
  else item.appendChild(missingDigestBlock(exchange));
  const commits = exchangeCommitsBlock(exchange);
  if (commits) item.appendChild(commits);
  item.appendChild(fullResponseDetails(exchange));
  return item;
}
function turnKindPill(kind) {
  const key = clean(kind) || "quick";
  const meta = TURN_KIND_META[key] || { label: key, cls: "" };
  return chip(meta.label, meta.cls);
}
function exchangeHasDigest(exchange) {
  const digest = obj(exchange && exchange.digest);
  return (exchange && exchange.has_digest === true) || hasValue(digest.title) || arr(digest.asked).length > 0 || arr(digest.notes).length > 0 || hasValue(digest.recap);
}
function exchangeDisplayTitle(exchange) {
  const digest = obj(exchange && exchange.digest);
  return clean(exchange && (exchange.title || exchange.turn_title || exchange.digest_title)) || clean(digest.title) || trunc(clean(exchange && exchange.user_preview), 90) || "Turn";
}
function exchangeDigestBlock(exchange) {
  const digest = obj(exchange.digest);
  const block = el("div", "exchange-digest");
  if (hasValue(digest.title)) block.appendChild(el("div", "digest-title", digest.title));
  append(block, digestList("Asked", digest.asked), digestList("Notes", digest.notes));
  if (hasValue(digest.recap)) block.appendChild(el("p", "exchange-recap", digest.recap));
  return block;
}
function digestList(label, values) {
  const items = arr(values).map(clean).filter(Boolean);
  if (!items.length) return null;
  const block = el("div", "digest-list");
  const list = el("ul");
  items.forEach((item) => list.appendChild(el("li", "", item)));
  append(block, el("div", "detail-label", label), list);
  return block;
}
function missingDigestBlock(exchange) {
  const id = clean(exchange.id);
  const digesting = state.sessionDrawer.digesting.has(id);
  const block = el("div", "exchange-digest missing");
  const row = el("div", "row space");
  append(row, el("span", "muted", "No digest yet."));
  const summarize = button(digesting ? "Summarizing" : "Summarize", "action-btn summarize-btn");
  summarize.disabled = digesting || SAMPLE_MODE || !hasValue(id);
  summarize.classList.toggle("loading", digesting);
  summarize.title = SAMPLE_MODE ? "Sample mode does not call the live digest API." : "Generate a digest for this exchange.";
  summarize.addEventListener("click", () => summarizeExchange(id));
  append(row, summarize);
  append(block, row);
  if (hasValue(exchange.user_preview)) block.appendChild(el("p", "exchange-preview", exchange.user_preview));
  const error = clean(state.sessionDrawer.digestErrors[id]);
  if (error) block.appendChild(el("div", "callout red", error));
  return block;
}
async function summarizeExchange(exchangeId) {
  const id = clean(exchangeId);
  const drawer = state.sessionDrawer;
  const key = drawer.key;
  if (!id || SAMPLE_MODE || drawer.digesting.has(id)) return;
  drawer.digesting.add(id);
  delete drawer.digestErrors[id];
  renderSessionDrawer();
  try {
    await fetchJson(`/api/turns/digest/${encodeURIComponent(id)}`, { method: "POST" });
    if (state.sessionDrawer.key === key) await loadSessionTurns(drawer.session, key);
  } catch (error) {
    if (state.sessionDrawer.key === key) {
      state.sessionDrawer.digestErrors[id] = clean(error.message) || "Unable to generate digest.";
    }
  } finally {
    if (state.sessionDrawer.key === key) {
      state.sessionDrawer.digesting.delete(id);
      renderSessionDrawer();
    }
  }
}
function exchangeCommitsBlock(exchange) {
  const commits = arr(exchange && exchange.commits);
  if (!commits.length) return null;
  const block = el("div", "linked-commits");
  append(block, el("div", "detail-label", "Linked commits"));
  commits.forEach((commitValue) => {
    const commit = obj(commitValue);
    const row = el("div", "linked-commit");
    append(row, el("span", "commit-sha", shortSha(commit.sha)), el("span", "commit-subject", clean(commit.subject) || "(no subject)"));
    if (commit.is_agent_commit === true || asCount(commit.is_agent_commit) === 1) row.appendChild(chip("agent", "gold"));
    block.appendChild(row);
  });
  return block;
}
function shortSha(value) {
  const sha = clean(value);
  return sha.length > 7 ? sha.slice(0, 7) : sha || "commit";
}
function fullResponseDetails(exchange) {
  const details = el("details", "exchange-full-response");
  const body = el("div", "exchange-full-body");
  details.appendChild(el("summary", "", "Full response"));
  details.appendChild(body);
  details.addEventListener("toggle", () => {
    if (!details.open || body.dataset.loaded === "true" || body.dataset.loading === "true") return;
    loadExchangeDetail(exchange, body);
  });
  return details;
}
async function loadExchangeDetail(exchange, target) {
  const id = clean(exchange && exchange.id);
  target.dataset.loading = "true";
  clear(target);
  target.appendChild(emptyState("Loading full response..."));
  try {
    const payload = SAMPLE_MODE ? await sampleExchangeDetail(id, exchange) : await fetchJson(`/api/turns/exchange/${encodeURIComponent(id)}`, { cache: "no-store" });
    clear(target);
    target.appendChild(exchangeDetailMessages(payload, exchange));
    target.dataset.loaded = "true";
  } catch (error) {
    clear(target);
    target.appendChild(el("div", "callout red", clean(error.message) || "Unable to load full response."));
  } finally {
    target.dataset.loading = "false";
  }
}
async function sampleExchangeDetail(id, fallback) {
  const payload = await sampleTurnsPayload();
  const detail = obj(obj(payload.exchange_details)[id]);
  if (Object.keys(detail).length) return detail;
  return fallback || {};
}
function exchangeDetailMessages(payloadValue, fallbackValue) {
  const payload = obj(payloadValue);
  const fallback = obj(fallbackValue);
  const userText = clean(payload.user_text) || clean(fallback.user_text) || clean(fallback.user_preview);
  const responseText = clean(payload.response_text) || clean(fallback.response_text);
  const finalText = clean(payload.response_final_text) || responseText;
  const responseTs = payload.response_end_ts || fallback.response_end_ts;
  const userTs = payload.user_ts || fallback.user_ts;
  if (!finalText && !responseText) {
    const messages = [];
    if (userText) messages.push({ role: "user", text: userText, ts: userTs });
    return messages.length ? messageList(messages) : emptyState("No full response text available.");
  }
  const list = el("div", "exchange-detail-messages");
  if (finalText) {
    list.appendChild(clampedTextBlock("Final response", finalText, responseTs));
    if (hasValue(payload.response_recap)) list.appendChild(el("div", "exchange-recap-line", `✻ recap: ${clean(payload.response_recap)}`));
  }
  if (responseText && responseText.trim() !== finalText.trim()) {
    list.appendChild(clampedTextBlock("Full response", responseText, responseTs));
  }
  if (userText) list.appendChild(clampedTextBlock("User message", userText, userTs));
  return list.childNodes.length ? list : emptyState("No full response text available.");
}
function clampedTextBlock(label, text, ts) {
  const block = el("div", "clamped-text-block");
  const head = el("div", "clamped-text-head");
  const toggle = button("▸", "clamp-toggle");
  const body = el("div", "clamped-text collapsed", clean(text));
  toggle.setAttribute("aria-expanded", "false");
  const setExpanded = (expanded) => {
    toggle.textContent = expanded ? "▾" : "▸";
    toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
    body.classList.toggle("collapsed", !expanded);
    body.classList.toggle("expanded", expanded);
  };
  const toggleExpanded = (event) => {
    event.preventDefault();
    setExpanded(toggle.getAttribute("aria-expanded") !== "true");
  };
  toggle.addEventListener("click", toggleExpanded);
  // Clicking the clamped preview expands it; collapsing needs the caret so text
  // selection in the expanded state doesn't snap the block shut.
  body.addEventListener("click", (event) => {
    if (toggle.getAttribute("aria-expanded") !== "true") toggleExpanded(event);
  });
  append(head, toggle, el("span", "clamped-text-label", label), hasValue(ts) ? timeNode(ts, clean(ts)) : null);
  append(block, head, body);
  return block;
}
async function loadSessionMessages(session, requestKey) {
  try {
    let payload;
    if (SAMPLE_MODE) {
      payload = { messages: sampleMessages(session) };
    } else if (sessionHost(session) === "cloud" || !hasValue(session.source_path)) {
      payload = { messages: [] };
    } else {
      const platform = sessionPlatform(session);
      if (!hasValue(platform) || !hasValue(session.id)) throw new Error("Session is missing a platform or id.");
      payload = await fetchJson(`/api/sessions/${encodeURIComponent(platform)}/${encodeURIComponent(session.id)}`, { cache: "no-store" });
    }
    if (state.sessionDrawer.key !== requestKey) return;
    state.sessionDrawer.messages = arr(payload && payload.messages);
    state.sessionDrawer.messagesError = "";
  } catch (error) {
    if (state.sessionDrawer.key !== requestKey) return;
    state.sessionDrawer.messagesError = clean(error.message) || "Unable to load session messages.";
  } finally {
    if (state.sessionDrawer.key === requestKey) {
      state.sessionDrawer.messagesLoading = false;
      renderSessionDrawer();
    }
  }
}
function sampleMessages(session) {
  return [
    { role: "user", text: clean(session.first_user) || "What is the current state of this work?", ts: session.started || session.last_activity },
    { role: "assistant", text: `Reviewed ${clean(session.branch) || basename(session.project) || "the project"} and updated the relevant plan or code path.`, ts: session.last_activity },
    { role: "user", text: clean(session.last_user) || "Continue with the next verification step.", ts: session.last_activity },
  ];
}
function renderSessionMessages(messages) {
  const body = byId(ids.drawerBody);
  clear(body);
  if (!messages.length) {
    body.appendChild(emptyState("No messages available for this session."));
    return;
  }
  body.appendChild(messageList(messages));
}
function messageList(messages) {
  const list = el("div", "message-list");
  arr(messages).forEach((message) => list.appendChild(messageNode(message)));
  return list;
}
function messageNode(message) {
  const role = clean(message.role) || "message";
  const roleClass = role === "user" ? "user" : role === "recap" ? "recap" : "assistant";
  const item = el("div", `message ${roleClass}`);
  const roleLine = el("div", "role");
  append(roleLine, textNode(role === "recap" ? `✻ ${role}` : role), hasValue(message.ts) ? textNode(` · ${relativeTime(message.ts) || clean(message.ts)}`) : null);
  if (hasValue(message.ts)) roleLine.title = localTimestamp(message.ts) || clean(message.ts);
  append(item, roleLine, el("div", "text", clean(message.text)));
  return item;
}
function fileLink(label, path, className) {
  const node = button(label, className || "file-link");
  node.disabled = !hasValue(path);
  node.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    openFile(path);
  });
  return node;
}
async function openFile(path) {
  const drawer = byId(ids.fileDrawer);
  byId(ids.fileBackdrop).classList.remove("hidden");
  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
  byId(ids.fileDrawerTitle).textContent = basename(path) || "File";
  byId(ids.fileDrawerStatus).textContent = "loading";
  clear(byId(ids.fileDrawerBody));
  byId(ids.fileDrawerBody).appendChild(emptyState("Loading file..."));
  state.fileEditing = false;
  try {
    const payload = SAMPLE_MODE ? sampleFilePayload(path) : await fetchJson(`/api/file?path=${encodeURIComponent(path)}`, { cache: "no-store" });
    state.filePayload = payload;
    renderFileDrawer();
  } catch (error) {
    byId(ids.fileDrawerStatus).textContent = "error";
    clear(byId(ids.fileDrawerBody));
    byId(ids.fileDrawerBody).appendChild(el("div", "callout red", clean(error.message) || "Unable to load file."));
  }
}
function closeFileDrawer() {
  byId(ids.fileBackdrop).classList.add("hidden");
  byId(ids.fileDrawer).classList.remove("open");
  byId(ids.fileDrawer).setAttribute("aria-hidden", "true");
  state.fileEditing = false;
}
function renderFileDrawer(message) {
  const payload = obj(state.filePayload);
  const path = clean(payload.path);
  const body = byId(ids.fileDrawerBody);
  clear(body);
  byId(ids.fileDrawerTitle).textContent = basename(path) || "File";
  byId(ids.fileDrawerStatus).textContent = SAMPLE_MODE ? "sample read-only" : isClientWritable(path) ? "editable" : "read-only";
  const head = el("div", "file-meta");
  append(head, el("div", "path", path || "path unavailable"), copyButton(path, "copy path"));
  const actions = el("div", "row");
  if (payload.truncated === true) append(actions, chip("truncated", "gold"));
  if (message) append(actions, el("span", "small muted", message));
  const canEdit = !SAMPLE_MODE && isClientWritable(path);
  if (canEdit) {
    const edit = button(state.fileEditing ? "Cancel" : "Edit", "action-btn");
    edit.addEventListener("click", () => {
      state.fileEditing = !state.fileEditing;
      renderFileDrawer();
    });
    actions.appendChild(edit);
  }
  append(body, head, actions);
  if (state.fileEditing && canEdit) {
    const area = el("textarea", "file-editor");
    area.value = clean(payload.content);
    const save = button("Save", "action-btn");
    save.addEventListener("click", () => saveFile(path, area.value));
    append(body, area, save);
    return;
  }
  body.appendChild(el("pre", "file-pre", clean(payload.content)));
}
async function saveFile(path, content) {
  try {
    await fetchJson("/api/file", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, content }),
    });
    state.filePayload = { ...obj(state.filePayload), content };
    state.fileEditing = false;
    renderFileDrawer("saved");
  } catch (error) {
    renderFileDrawer(`save failed: ${clean(error.message)}`);
  }
}
function isClientWritable(path) {
  const value = clean(path);
  return (value.includes("/openspec/") && (value.endsWith(".md") || value.endsWith("config.yaml"))) || value.endsWith("apps/holodeck/registry.yaml") || value.endsWith("apps/holodeck/worktree-colors.yaml");
}
function sampleFilePayload(path) {
  const value = clean(path);
  let content = `# ${basename(value) || "sample"}\n\nSample mode renders file links without calling the live API.\n\nPath:\n${value}\n`;
  if (value.endsWith("registry.yaml")) {
    content = "apps:\n  holodeck:\n    stage: s1-dev\n    spec_stage: openspec-core\n";
  } else if (value.endsWith("proposal.md")) {
    content = "# Proposal\n\nAdd interactive state, worktree cards, and editable OpenSpec file surfaces.\n";
  } else if (value.endsWith("tasks.md")) {
    content = "# Tasks\n\n- [x] Model state API usage\n- [ ] Verify live file writes\n";
  } else if (value.endsWith("spec.md")) {
    content = "# app Specification\n\n## Requirements\n\n### Requirement: Dashboard interactivity\nThe page persists work-management state through the API.\n";
  }
  return { path: value, content, truncated: false };
}
function renderDeploy() {
  const root = byId(ids.deploy);
  clear(root);
  const deploys = getLayer("deploy");
  if (!deploys.length) {
    root.appendChild(emptyState("No deploy entries found."));
    return;
  }
  const groups = new Map();
  deploys.forEach((entry) => {
    const kind = clean(entry.kind) || clean(entry.surface) || "other";
    groups.set(kind, [...(groups.get(kind) || []), entry]);
  });
  const order = ["fly", "chalice", "webflow", "s3"];
  [...groups.entries()].sort(([a], [b]) => {
    const ai = order.indexOf(a);
    const bi = order.indexOf(b);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi) || a.localeCompare(b);
  }).forEach(([kind, list]) => {
    const group = el("div", "card static-card");
    const head = el("div", "group-head");
    append(head, el("h3", "", KIND_LABELS[kind] || kind), chip(`${list.length}`, ""));
    const items = el("div", "deploy-list");
    list.forEach((entry) => items.appendChild(deployItem(entry)));
    append(group, head, items);
    root.appendChild(group);
  });
}
function deployItem(entry) {
  const item = el("div", "deploy-item");
  const top = el("div", "row space");
  append(top, el("span", "b", clean(entry.name) || clean(entry.surface) || "deploy"), chip(clean(entry.surface) || clean(entry.kind), ""));
  const meta = el("div", "badge-row");
  if (hasValue(entry.app_slug)) append(meta, link(`app: ${entry.app_slug}`, `#${appCardId(entry.app_slug)}`, "pill"));
  if (hasValue(entry.url)) {
    const url = link(entry.url, entry.url);
    url.target = "_blank";
    url.rel = "noreferrer";
    append(meta, url);
  }
  const config = hasValue(entry.config_path) ? el("div", "scope", entry.config_path) : null;
  const last = hasValue(entry.last_deploy) ? el("div", "small muted") : null;
  if (last) append(last, textNode("last deploy "), timeNode(entry.last_deploy));
  append(item, top, meta.childNodes.length ? meta : null, commandBlock(entry.command, "copy command"), config, last);
  return item;
}
function scrollToId(id, behavior) {
  const node = byId(id);
  if (!node) return;
  node.scrollIntoView({ behavior: behavior || "smooth", block: "start" });
  node.classList.add("pulse");
  window.setTimeout(() => node.classList.remove("pulse"), 900);
}
function setupNavObserver() {
  if (state.observer) state.observer.disconnect();
  const links = [...document.querySelectorAll("nav.side a.navlink")];
  const byHash = new Map(links.map((node) => [node.getAttribute("href"), node]));
  state.observer = new IntersectionObserver((entries) => {
    const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    links.forEach((node) => node.classList.remove("active"));
    const active = byHash.get(`#${visible.target.id}`);
    if (active) active.classList.add("active");
  }, { rootMargin: "-22% 0px -66% 0px", threshold: [0, 0.2, 0.6] });
  document.querySelectorAll("main section[id]").forEach((section) => state.observer.observe(section));
}
init();
