import json
import subprocess
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from apps.holodeck.server import HOLODECK_DIR, WEB_DIR, app

client = TestClient(app)
REQUIRED_WORKTREE_FIELDS = ("path", "name", "branch", "title_bar", "cursor_open")
REQUIRED_APP_JS_SYMBOLS = (
    "function loadCloudStatus(",
    "function renderCloudStatusBanner(",
    "function basename(",
    "function cursorFocusControl(",
    "function requestCursorFocus(",
    "function worktreeCard(",
    "function worktreeTitleBarColors(",
    "function colorFromDisplayRules(",
    "function worktreeFolderName(",
    "function isDetachedBranch(",
    "function worktreeKey(",
    "function renderWorktrees(",
    "function sortWorktrees(",
    "function renderAgentDeck(",
    "function renderUniverse(",
    "function lineageAccepted(",
    "function lineageStatusText(",
    "function lineageEvidenceText(",
    "function lineageDeclaredParent(",
    "function acceptedLineageParentName(",
    "function branchAssignedColors(",
    "function branchAssignedColor(",
    "function deterministicBranchFallback(",
    "function deterministicBranchFallbackForeground(",
    "function branchTimelineColor(",
    "function branchTimelineGroups(",
    "function branchTimelineTimeRange(",
    "function branchTimelineDateRatio(",
    "function buildBranchTimelineModel(",
    "function paintBranchGroupEdges(",
    "function paintBranchTimelineEdges(",
    "function renderBranchTimeline(",
    "function branchValidationDetails(",
    "function loadAgents(",
    "function agentProjectLabel(",
    "function slugMatchesProjectIdentity(",
    "function projectLabelFromSlug(",
    "function dedupeAgentDeck(",
    "function normalizeAgentTitle(",
    "function clampedTextBlock(",
    "function sessionDisplayTitle(",
    "function setSessionDrawerTitle(",
    "async function refreshSessionTitleSurfaces(",
    "async function promoteWorktreeStep(",
    "const AGENT_STATE_META",
    "function worktreePromptText(",
    "agent-hide-btn",
    "holodeck-hidden-agents",
)

### Static assets
def test_web_static_assets_exist():
    for name in ("index.html", "app.js", "style.css", "favicon.svg", "sample-snapshot.json", "sample-state.json"):
        assert (WEB_DIR / name).is_file(), "missing web asset: " + name
    assert (HOLODECK_DIR / "worktree-colors.yaml").is_file()
def test_app_js_parses_as_es_module():
    source = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    for status in (
        "structurally-verified",
        "evidence-validated",
        "pending",
        "invalid",
        "unsupported",
        "missing",
        "parent-ref-missing",
        "ref-diverged",
    ):
        assert status in source
    result = subprocess.run(
        ["node", "--input-type=module", "--check"],
        input=source,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
def test_app_js_exports_required_dashboard_symbols():
    source = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    missing = [symbol for symbol in REQUIRED_APP_JS_SYMBOLS if symbol not in source]
    assert not missing, "app.js missing symbols: " + ", ".join(missing)
    assert "slugs[0]" not in source
    assert "dedupeAgentDeck(sortedAgents(state.agents).filter(agentPlatformVisible))" in source
    assert "lineage.authoritative === true" in source
    assert 'detailItem("lineage state", lineageStatusText(lineage))' in source
    assert "lineage_parity" not in source
    assert "`declared parent ${declaredParent}; no accepted edge`" in source
def test_lineage_helpers_never_accept_pending_invalid_or_missing_parent():
    source = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    start = source.index("function lineageAccepted(")
    end = source.index("function deterministicBranchFallback(", start)
    helpers = source[start:end]
    script = """
function clean(value) { return String(value == null ? "" : value).trim(); }
function obj(value) { return value && typeof value === "object" && !Array.isArray(value) ? value : {}; }
function arr(value) { return Array.isArray(value) ? value : []; }
function hasValue(value) { return value !== null && value !== undefined && clean(value) !== ""; }
""" + helpers + """
const accepted = {lineage: {status: "evidence-validated", authoritative: true, parent_branch: "feature/parent"}};
if (!lineageAccepted(accepted)) throw new Error("accepted lineage was rejected");
if (acceptedLineageParentName(accepted) !== "feature/parent") throw new Error("accepted parent missing");
for (const status of ["pending", "invalid", "unsupported", "missing", "parent-ref-missing", "ref-diverged"]) {
  const branch = {lineage: {status, authoritative: false, parent_branch: "feature/declared"}};
  if (lineageAccepted(branch)) throw new Error(status + " was accepted");
  if (acceptedLineageParentName(branch) !== "") throw new Error(status + " exposed accepted parent");
  if (lineageDeclaredParent(branch) !== "feature/declared") throw new Error(status + " hid diagnostics");
}
"""
    result = subprocess.run(
        ["node", "--input-type=module"],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_branch_timeline_model_orders_groups_without_inventing_parent_edges():
    source = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    start = source.index("function deterministicBranchHue(")
    end = source.index("function lineageEvidenceText(", start)
    helpers = source[start:end]
    script = """
function clean(value) { return String(value == null ? "" : value).trim(); }
function obj(value) { return value && typeof value === "object" && !Array.isArray(value) ? value : {}; }
function arr(value) { return Array.isArray(value) ? value : []; }
function parseDate(value) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}
function lineageAccepted(branchValue) {
  const lineage = obj(obj(branchValue).lineage);
  return lineage.authoritative === true && ["structurally-verified", "evidence-validated"].includes(clean(lineage.status));
}
function lineageDeclaredParent(branchValue) {
  return clean(obj(obj(branchValue).lineage).parent_branch).replace(/^origin\\//, "");
}
function acceptedLineageParentName(branchValue) {
  return lineageAccepted(branchValue) ? lineageDeclaredParent(branchValue) : "";
}
function branchColorRules() {
  return {foreground: "#fefefe", rules: []};
}
function branchAssignedColors(name) {
  return name === "main" ? {background: "#068102", foreground: "#f0f0f0"} : null;
}
""" + helpers + """
const branches = [
  {name: "main", lineage: {status: "root", authoritative: true}, date: "2026-07-01T08:00:00Z"},
  // Tip activity (date) drives Activity sort; fork_date still drives the rail.
  // alpha-child tip is newest in its group, so the alpha group sorts above beta
  // even though beta has the newest fork_date.
  {name: "feature/alpha", date: "2026-07-29T10:00:00Z", lineage: {status: "evidence-validated", authoritative: true, parent_branch: "main", fork_date: "2026-06-01T08:00:00Z"}},
  {name: "feature/alpha-child", date: "2026-07-30T16:00:00Z", lineage: {status: "structurally-verified", authoritative: true, parent_branch: "feature/alpha", fork_date: "2026-07-10T08:00:00Z"}},
  {name: "feature/beta", date: "2026-07-30T14:00:00Z", lineage: {status: "evidence-validated", authoritative: true, parent_branch: "main", fork_date: "2026-07-20T08:00:00Z"}},
  {name: "feature/gamma", date: "2026-07-30T12:00:00Z", lineage: {status: "evidence-validated", authoritative: true, parent_branch: "main", fork_date: "2026-07-05T08:00:00Z"}},
  {name: "feature/pending", lineage: {status: "pending", authoritative: false, parent_branch: "main"}},
  {name: "feature/missing", lineage: {status: "missing", authoritative: false}},
  {name: "feature/orphan", lineage: {status: "evidence-validated", authoritative: true, parent_branch: "feature/not-open"}},
  {name: "<img src=x onerror=alert(1)>", lineage: {status: "invalid", authoritative: false, parent_branch: "main"}},
];
const model = buildBranchTimelineModel(branches, "date");
const edges = model.edges.map((edge) => `${edge.parent}->${edge.child}`).join(",");
if (edges !== "main->feature/alpha,feature/alpha->feature/alpha-child,main->feature/beta,main->feature/gamma") throw new Error("edges: " + edges);
if (model.parentByName.has("feature/pending")) throw new Error("pending edge accepted");
if (model.parentByName.has("feature/orphan")) throw new Error("missing parent edge accepted");
if (!model.unlinkedRoots.includes("feature/pending") || !model.unlinkedRoots.includes("feature/missing")) throw new Error("unaccepted branches hidden");
if (!model.unlinkedRoots.includes("feature/orphan")) throw new Error("orphan hidden");
if (!model.byName.has("<img src=x onerror=alert(1)>")) throw new Error("branch label changed");
const dateOrder = model.timelineRows.map((row) => row.name).join(",");
if (dateOrder !== "feature/alpha-child,feature/alpha,feature/beta,feature/gamma,main") throw new Error("date order: " + dateOrder);
const dateGroups = model.linkedGroups.map((group) => group.rows.map((row) => row.name).join(">")).join("|");
if (dateGroups !== "feature/alpha-child>feature/alpha|feature/beta|feature/gamma") throw new Error("date groups: " + dateGroups);
if (model.activityByName.get("feature/alpha") !== Date.parse("2026-07-30T16:00:00Z")) throw new Error("group activity should use newest tip in subtree");
if (branchTimelineDateRatio(model.timeRange.maxTime, model.timeRange) !== 0) throw new Error("newest date ratio");
if (branchTimelineDateRatio(model.timeRange.minTime, model.timeRange) !== 1) throw new Error("oldest date ratio");
const alphaModel = buildBranchTimelineModel(branches, "alphabetical");
const alphaOrder = alphaModel.timelineRows.map((row) => row.name).join(",");
if (alphaOrder !== "feature/alpha-child,feature/alpha,feature/beta,feature/gamma,main") throw new Error("alpha order: " + alphaOrder);
if (alphaModel.timelineRows.find((row) => row.name === "feature/alpha-child").depth !== 2) throw new Error("nested depth lost");
const mainColor = branchTimelineColor(branches[0]);
if (mainColor.background !== "#068102" || mainColor.foreground !== "#f0f0f0" || mainColor.source !== "configured") throw new Error("main color");
const fallbackA = branchTimelineColor(branches[2]);
const fallbackB = branchTimelineColor(branches[3]);
if (fallbackA.source !== "deterministic-fallback") throw new Error("fallback source");
if (!["#0d1117", "#ffffff"].includes(fallbackA.foreground)) throw new Error("fallback foreground policy");
if (fallbackA.background !== branchTimelineColor(branches[2]).background) throw new Error("fallback unstable");
if (fallbackA.background === fallbackB.background) throw new Error("fallbacks not distinct");
if (deterministicBranchFallbackForeground("feature/knowledge-base") !== "#0d1117") throw new Error("light fallback contrast");
const cyclic = buildBranchTimelineModel([
  {name: "feature/a", lineage: {status: "evidence-validated", authoritative: true, parent_branch: "feature/b"}},
  {name: "feature/b", lineage: {status: "evidence-validated", authoritative: true, parent_branch: "feature/a"}},
], "date");
if (cyclic.edges.length !== 0 || cyclic.cycleNames.size !== 2) throw new Error("cycle accepted");
"""
    result = subprocess.run(
        ["node", "--input-type=module"],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_branch_timeline_renderer_uses_safe_dom_construction():
    source = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "style.css").read_text(encoding="utf-8")
    start = source.index("function renderBranchTimeline(")
    end = source.index("function branchRowId(", start)
    renderer = source[start:end]
    assert "innerHTML" not in renderer
    assert "fillWrapLabel(nameNode, name)" in renderer
    assert "card.dataset.branch = name" in renderer
    assert "openCommitDrawer(name)" in renderer
    assert "bindBranchTimelineEdges(layout, model)" in renderer
    assert "branch-group-layout" in source
    assert "branch-edge-layer" in source
    assert "branch-parent-edge" in source
    assert "branch-date-edge" in source
    assert "function paintBranchGroupEdges(" in source
    assert "function paintBranchTimelineEdges(" in source
    assert "L ${parentLeft} ${cardY} L ${parentLeft} ${parentTop}" in source
    assert 'item.setAttribute("role", "treeitem")' in renderer
    assert "details.hidden = !state.branchValidationVisible" in renderer
    assert "append(facts, timeNode(branch.date, \"—\"), driftText(branch));" in renderer
    assert 'el("span", "drift-text", driftText(branch))' not in renderer
    assert ".branch-timeline-card{" in styles
    assert ".branch-group-layout{" in styles
    assert ".branch-time-rail{" in styles
    assert ".branch-parent-edge{" in styles
    assert ".branch-date-edge{" in styles
    assert ".branch-groups{display:grid;gap:0;min-width:0}" in styles
    assert ".branch-group{min-width:0;margin:0;" in styles
    assert ".branch-timeline-list{list-style:none;margin:0;padding:0;min-width:0;position:relative;z-index:1}" in styles


def test_primary_ai_interface_control_can_be_hidden_without_removing_its_state():
    source = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    assert "const SHOW_PRIMARY_AI_INTERFACE = false;" in source
    controls_start = source.index("function worktreeControls(")
    controls = source[controls_start:controls_start + 500]
    assert "if (SHOW_PRIMARY_AI_INTERFACE)" in controls
    assert 'labeledControl("Primary AI interface", primaryInterfaceSelect(branch, entry))' in controls


def test_active_worktree_cards_do_not_show_a_park_control():
    source = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    card_start = source.index("function worktreeCard(")
    card = source[card_start:card_start + 5000]
    assert "append(title, branchButton, activeToggleButton(key, entry.active))" not in card
    assert "append(title, branchButton);" in card
def _worktree_color_background(rule_id):
    doc = yaml.safe_load((HOLODECK_DIR / "worktree-colors.yaml").read_text(encoding="utf-8")) or {}
    for rule in doc.get("rules") or []:
        if isinstance(rule, dict) and rule.get("id") == rule_id and rule.get("background"):
            return rule["background"]
    raise AssertionError("missing worktree-colors.yaml rule id: " + rule_id)
def test_worktree_title_bar_colors_prefer_folder_yaml_over_stale_snapshot():
    """Regression: deutsch/dragon-baby must not keep Minecraft-red from a stale title_bar."""
    source = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    color_fn_start = source.index("function worktreeTitleBarColors(")
    color_fn = source[color_fn_start:color_fn_start + 900]
    assert "worktreeFolderName(wt)" in color_fn
    assert "colorFromDisplayRules(folder, branch)" in color_fn
    folder_rank = color_fn.index("colorFromDisplayRules(folder, branch)")
    stale_rank = color_fn.index("wt && wt.title_bar")
    assert folder_rank < stale_rank, "folder YAML colors must win over snapshot title_bar"
    assert "isDetachedBranch(branch)" in color_fn
    assert "Single source of truth: apps/holodeck/worktree-colors.yaml" in source
    assert '{ id: "deutsch", name_contains: "deutsch", background:' not in source
    colors_doc = yaml.safe_load((HOLODECK_DIR / "worktree-colors.yaml").read_text(encoding="utf-8")) or {}
    expected_deutsch = _worktree_color_background("deutsch")
    expected_dragon = _worktree_color_background("dragon-baby")
    expected_minecraft = _worktree_color_background("minecraft")
    script = f"""
function clean(value) {{ return String(value == null ? "" : value).trim(); }}
function obj(value) {{ return value && typeof value === "object" && !Array.isArray(value) ? value : {{}}; }}
function arr(value) {{ return Array.isArray(value) ? value : []; }}
function basename(path) {{
  const value = clean(path).replace(/\\/+$/, "");
  const parts = value.split("/");
  return parts[parts.length - 1] || value;
}}
const state = {{
  colorRules: {json.dumps(colors_doc)},
  snapshot: null,
}};
function branchColorRules() {{ return state.colorRules; }}
function normalizeColorToken(value) {{ return clean(value).toLowerCase(); }}
function colorRulesMatch(displayName, branchName, rule) {{
  const name = normalizeColorToken(displayName);
  const branch = normalizeColorToken(branchName);
  if (rule.name_exact && name !== normalizeColorToken(rule.name_exact)) return false;
  if (rule.branch && branch !== normalizeColorToken(rule.branch)) return false;
  if (rule.name_contains && !name.includes(normalizeColorToken(rule.name_contains))) return false;
  for (const token of arr(rule.name_contains_all)) {{
    if (!name.includes(normalizeColorToken(token))) return false;
  }}
  return true;
}}
function isDetachedBranch(branch) {{
  const value = clean(branch);
  return !value || value === "detached";
}}
function worktreeFolderName(wt) {{
  if (isDetachedBranch(wt && wt.branch)) return basename(wt && wt.path) || clean(wt && wt.name) || "worktree";
  return clean(wt.name) || basename(wt.path) || "worktree";
}}
function colorFromDisplayRules(displayName, branchName) {{
  const name = clean(displayName);
  if (!name) return null;
  const rules = branchColorRules();
  const bare = clean(branchName);
  for (const rule of arr(rules.rules)) {{
    if (!colorRulesMatch(name, bare, rule)) continue;
    const background = clean(rule.background);
    if (!background) continue;
    return {{
      background,
      foreground: clean(rule.foreground) || clean(rules.foreground) || "#ffffff",
    }};
  }}
  return null;
}}
function worktreeTitleBarColors(wt) {{
  const folder = worktreeFolderName(wt);
  const branch = clean(wt && wt.branch);
  const fromFolder = colorFromDisplayRules(folder, branch);
  if (fromFolder) return fromFolder;
  if (!isDetachedBranch(branch)) {{
    const fromName = colorFromDisplayRules(clean(wt && wt.name) || folder, branch);
    if (fromName) return fromName;
  }}
  const bar = obj(wt && wt.title_bar);
  return {{
    background: clean(bar.background) || "#245f99",
    foreground: clean(bar.foreground) || "#ffffff",
  }};
}}
const staleDeutsch = {{
  path: "/Users/me/Code/deutsch",
  branch: "detached",
  name: "codex-feature-minecraft-mod-build-local",
  title_bar: {{ background: "#800000", foreground: "#ffffff" }},
}};
const staleDragon = {{
  path: "/Users/me/Code/dragon-baby",
  branch: "detached",
  name: "codex-feature-minecraft-mod-build-local",
  title_bar: {{ background: "#800000", foreground: "#ffffff" }},
}};
const minecraft = {{
  path: "/Users/me/Code/minecraft",
  branch: "detached",
  name: "codex-feature-minecraft-mod-build-local",
  title_bar: {{ background: "#800000", foreground: "#ffffff" }},
}};
const deutschColors = worktreeTitleBarColors(staleDeutsch);
const dragonColors = worktreeTitleBarColors(staleDragon);
const minecraftColors = worktreeTitleBarColors(minecraft);
if (deutschColors.background !== {json.dumps(expected_deutsch)}) throw new Error("deutsch: " + deutschColors.background);
if (dragonColors.background !== {json.dumps(expected_dragon)}) throw new Error("dragon-baby: " + dragonColors.background);
if (minecraftColors.background !== {json.dumps(expected_minecraft)}) throw new Error("minecraft: " + minecraftColors.background);
if (worktreeFolderName(staleDeutsch) !== "deutsch") throw new Error("folder deutsch");
if (worktreeFolderName(staleDragon) !== "dragon-baby") throw new Error("folder dragon-baby");
console.log("ok");
"""
    result = subprocess.run(["node", "--input-type=module", "-e", script], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "ok" in result.stdout
def test_branch_timeline_uses_exact_assigned_background_and_foreground():
    source = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    start = source.index("function branchColorRules(")
    end = source.index("function shortBranchName(", start)
    helpers = source[start:end]
    script = r"""
function clean(value) { return String(value == null ? "" : value).trim(); }
function obj(value) { return value && typeof value === "object" && !Array.isArray(value) ? value : {}; }
function arr(value) { return Array.isArray(value) ? value : []; }
const branches = [
  {name: "feature/snapshot", title_bar: {background: "#abcdef", foreground: "#010203"}},
  {name: "feature/rule", title_bar: null},
];
const worktrees = [
  {branch: "feature/stellar", title_bar: {background: "#22ae96", foreground: "#102030"}},
];
const state = {
  snapshot: {
    layer_meta: {
      branches: {
        color_rules: {
          foreground: "#ffffff",
          rules: [
            {id: "rule", branch: "feature/rule", background: "#445566", foreground: "#ddeeff"},
          ],
        },
      },
    },
  },
  colorRules: null,
};
function getLayer(name) { return name === "branches" ? branches : []; }
function worktreeForBranch(name) { return worktrees.find((item) => item.branch === name) || null; }
function worktreeTitleBarColors(wt) { return wt.title_bar; }
function readableBranchColor(value) { return value; }
""" + helpers + r"""
const stellar = branchAssignedColors("feature/stellar");
if (stellar.background !== "#22ae96" || stellar.foreground !== "#102030") throw new Error("worktree colors changed");
const snapshot = branchAssignedColors("feature/snapshot");
if (snapshot.background !== "#abcdef" || snapshot.foreground !== "#010203") throw new Error("snapshot colors changed");
const rule = branchAssignedColors("feature/rule");
if (rule.background !== "#445566" || rule.foreground !== "#ddeeff") throw new Error("rule colors changed");
if (branchAssignedColor("feature/stellar") !== "#22ae96") throw new Error("background compatibility changed");
"""
    result = subprocess.run(
        ["node", "--input-type=module"],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    parser_start = source.index("function parseWorktreeColorsYaml(")
    parser_end = source.index("async function loadColorRules(", parser_start)
    parser_script = r"""
function clean(value) { return String(value == null ? "" : value).trim(); }
""" + source[parser_start:parser_end] + r"""
const parsed = parseWorktreeColorsYaml(`
foreground: "#112233"
rules:
  - id: stellar
    name_contains: stellar-transcriber
    background: "#22ae96"
    foreground: "#102030"
`);
if (parsed.foreground !== "#112233") throw new Error("global foreground");
if (parsed.rules[0].background !== "#22ae96") throw new Error("background");
if (parsed.rules[0].foreground !== "#102030") throw new Error("rule foreground");
"""
    parser_result = subprocess.run(
        ["node", "--input-type=module"],
        input=parser_script,
        text=True,
        capture_output=True,
        check=False,
    )
    assert parser_result.returncode == 0, parser_result.stderr or parser_result.stdout
    renderer_start = source.index("function branchTimelineRow(")
    renderer = source[renderer_start:source.index("function branchRowId(", renderer_start)]
    assert "header.style.background = colors.background;" in renderer
    assert "header.style.color = colors.foreground;" in renderer
    styles = (WEB_DIR / "style.css").read_text(encoding="utf-8")
    assert ".branch-timeline-name{" in styles
    assert "background:transparent;color:inherit" in styles
def test_session_display_title_prefers_renamed_session_name():
    source = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    assert "function sessionDisplayTitle(session)" in source
    assert "function setSessionDrawerTitle(session)" in source
    assert "async function refreshSessionTitleSurfaces()" in source
    assert "setSessionDrawerTitle(state.sessionDrawer.session)" in source
    assert "await refreshSessionTitleSurfaces()" in source
    assert "latestPrimaryTurnTitle" not in source
    assert "byId(ids.drawerTitle).textContent = title;" not in source
    poll_start = source.index("async function pollAgentSurfaces()")
    poll_fn = source[poll_start:poll_start + 900]
    assert "renderSessions()" in poll_fn
    assert "setSessionDrawerTitle(state.sessionDrawer.session)" in poll_fn
    load_turns_start = source.index("async function loadSessionTurns(")
    load_turns_fn = source[load_turns_start:load_turns_start + 1200]
    assert "setSessionDrawerTitle(state.sessionDrawer.session)" in load_turns_fn
    assert "latest_primary_digest_title" not in load_turns_fn
    title_fn_start = source.index("function sessionDisplayTitle(session)")
    title_fn = source[title_fn_start:title_fn_start + 700]
    session_name_rank = title_fn.index("session.ai_title || session.title")
    turn_status_rank = title_fn.index("status.turn_title")
    assert session_name_rank < turn_status_rank, "session title must win over turn-status/digest titles"
    script = r"""
function clean(value) { return String(value == null ? "" : value).trim(); }
function trunc(value, limit) {
  const text = clean(value);
  if (text.length <= limit) return text;
  return text.slice(0, Math.max(0, limit - 3)) + "...";
}
function obj(value) { return value && typeof value === "object" && !Array.isArray(value) ? value : {}; }
const state = { turnStatus: [{ session_id: "cursor:abc", turn_title: "branch map and holodeck" }] };
function sessionIdCandidates(session) {
  const id = clean(session && session.id);
  const values = [clean(session && session.session_id), id];
  if (id && !id.startsWith("cursor:")) values.push(`cursor:${id}`);
  return new Set(values.filter(Boolean));
}
function sessionMatchesStatus(session, statusValue) {
  const status = obj(statusValue);
  const statusSessionId = clean(status.session_id || status.session || status.session_key);
  return Boolean(statusSessionId && sessionIdCandidates(session).has(statusSessionId));
}
function turnStatusForSession(session) {
  return state.turnStatus.find((status) => sessionMatchesStatus(session, status)) || null;
}
function sessionDisplayTitle(session) {
  const status = turnStatusForSession(session);
  const digest = obj(session && session.digest);
  return clean(session && (session.ai_title || session.title)) ||
    clean(status && (status.turn_title || status.title || status.digest_title)) ||
    clean(session && (session.latest_primary_digest_title || session.latest_turn_title || session.turn_title || session.digest_title)) ||
    clean(digest.title) ||
    trunc(clean(session && session.first_user), 100) ||
    "Untitled session";
}
function listTitle(session) { return sessionDisplayTitle(session); }
function drawerTitle(session) { return sessionDisplayTitle(session); }
const renamed = {
  id: "abc",
  session_id: "cursor:abc",
  title: "branch map deprecation",
  digest: { title: "stale digest title" },
  latest_primary_digest_title: "stale primary digest",
  first_user: "old first user text",
};
const list = listTitle(renamed);
const drawer = drawerTitle(renamed);
if (list !== "branch map deprecation") throw new Error("list title: " + list);
if (drawer !== "branch map deprecation") throw new Error("drawer title: " + drawer);
if (list !== drawer) throw new Error("list/drawer mismatch: " + list + " vs " + drawer);
const untitled = { id: "abc", session_id: "cursor:abc", first_user: "fallback user text" };
if (sessionDisplayTitle(untitled) !== "branch map and holodeck") throw new Error("fallback turn status");
console.log("ok");
"""
    result = subprocess.run(["node", "--input-type=module", "-e", script], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "ok" in result.stdout
def test_agent_deck_label_and_dedupe_helpers():
    script = r"""
function clean(value) { return String(value == null ? "" : value).trim(); }
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
function agentProjectLabel(wt) {
  const folder = clean(wt.name);
  const slugs = (wt.apps_touched || []).map(clean).filter(Boolean);
  const identity = `${clean(wt.branch)} ${folder}`.toLowerCase();
  const named = slugs.find((slug) => slugMatchesProjectIdentity(slug, identity));
  return named ? projectLabelFromSlug(named) : folder;
}
function normalizeAgentTitle(title) { return clean(title).replace(/^\(\d+\)\s+/, ""); }
function dedupe(agents) {
  const seen = new Set();
  const result = [];
  for (const agent of agents) {
    const key = [agent.platform, agent.worktree, normalizeAgentTitle(agent.title).toLowerCase()].join("\0");
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(agent);
  }
  return result;
}
const stellar = { name: "stellar-transcriber", branch: "diarz-landscape", apps_touched: ["autolearner", "holodeck", "transcription/stellar-transcriber", "voice-router"] };
const stale = { name: "stellar-transcriber", branch: "diarz-landscape", apps_touched: ["autolearner", "holodeck", "voice-router"] };
const holodeck = { name: "feature-holodeck-start", branch: "holodeck/swing-v2", apps_touched: ["autolearner", "holodeck", "mac"] };
if (agentProjectLabel(stellar) !== "stellar-transcriber") throw new Error("nested slug: " + agentProjectLabel(stellar));
if (agentProjectLabel(stale) !== "stellar-transcriber") throw new Error("folder fallback: " + agentProjectLabel(stale));
if (agentProjectLabel(holodeck) !== "holodeck") throw new Error("branch slug: " + agentProjectLabel(holodeck));
if (normalizeAgentTitle("(1) Claude Code session review") !== "Claude Code session review") throw new Error("title normalize");
const kept = dedupe([
  { platform: "cursor", worktree: "/repo/stellar", title: "(1) Claude Code session review" },
  { platform: "cursor", worktree: "/repo/stellar", title: "Claude Code session review" },
  { platform: "claude", worktree: "/repo/stellar", title: "Claude Code session review" },
]);
if (kept.length !== 2) throw new Error("dedupe count " + kept.length);
if (kept[0].title !== "(1) Claude Code session review") throw new Error("keep newest first");
console.log("ok");
"""
    result = subprocess.run(["node", "--input-type=module", "-e", script], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "ok" in result.stdout
def test_cursor_focus_request_is_fixed_and_allowlisted():
    source = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    assert 'fetch("/api/focus"' in source
    assert '"X-Holodeck-Action": "focus"' in source
    assert 'body: JSON.stringify({ target: "cursor", matcher: { worktree_path:' in source
    assert "if (!wtIsCursorOpen(wt)) return null" in source
    assert 'button("go to window", "pill open cursor-focus-button")' in source
    old_cursor_label = '"open ' + 'in Cursor"'
    old_closed_label = '"not ' + 'open"'
    assert old_cursor_label not in source
    assert old_closed_label not in source
    assert 'const titleToggle = button("", "worktree-title-toggle")' in source
    assert 'titleBar.setAttribute("role", "button")' not in source
    assert 'titleBar.addEventListener("click"' not in source
    assert 'requestError.stale = failure.stale === true' in source
    assert 'focusButton.classList.remove("open")' in source
    assert 'statusNode.hidden = true' in source
def test_index_html_references_dashboard_assets():
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    assert 'href="style.css"' in html or "style.css" in html
    assert "app.js" in html
    assert 'rel="icon"' in html
    assert "favicon.svg" in html
    assert 'id="active-ai"' in html
    assert 'id="todos"' in html
    old_deck_id = 'id="' + 'deck"'
    assert old_deck_id not in html
    assert 'id="agent-deck"' in html
    assert 'id="universe-parked"' in html
    assert 'id="universe-branches"' in html
    assert 'id="universe-apps"' in html
    assert 'id="worktree-cards"' in html
    assert 'href="#branches">Branches</a>' in html
    assert 'id="branches"' in html
    assert 'id="branch-timeline-status"' in html
    assert 'id="branch-timeline-legend"' in html
    assert 'id="branch-timeline"' in html
    assert 'id="branch-sort-date"' in html
    assert ">Activity</button>" in html
    assert 'id="branch-sort-alphabetical"' in html
    assert 'id="branch-validation-toggle"' in html
    assert 'aria-controls="branch-timeline"' in html
    assert 'title="Lineage groups stay together' in html
    assert '<p class="sec-lede">' not in html.split('id="branches"', 1)[1].split('id="core"', 1)[0]
    assert "Branches — List" not in html
    assert "Branches — Graph" not in html
    assert 'id="refresh-btn"' in html
    assert 'id="cloud-auth-banner"' in html
    assert 'id="overview"' not in html
    assert 'id="worktrees"' not in html
    assert 'id="apps"' not in html
def test_get_favicon_returns_svg():
    response = client.get("/favicon.svg")
    assert response.status_code == 200
    assert "svg" in response.headers.get("content-type", "")
    assert b"<svg" in response.content
    assert b"#58a6ff" in response.content
def test_sample_snapshot_parses_and_has_worktree_card_fields():
    data = json.loads((WEB_DIR / "sample-snapshot.json").read_text(encoding="utf-8"))
    worktrees = data.get("layers", {}).get("worktrees") or []
    assert worktrees, "sample snapshot needs at least one worktree"
    for worktree in worktrees:
        for field in REQUIRED_WORKTREE_FIELDS:
            assert field in worktree, f"sample worktree missing {field}: {worktree.get('path')}"
        title_bar = worktree.get("title_bar") or {}
        assert title_bar.get("background")
        assert title_bar.get("foreground")
    sessions = data.get("layers", {}).get("sessions") or []
    assert sessions, "sample snapshot needs AI sessions"
    for session in sessions:
        assert "tool" not in session
        assert session.get("platform") in ("claude", "codex", "cursor")
        assert session.get("entrypoint") in ("cli", "app", "subagent")
        assert session.get("host") in ("local", "cloud")
    branches = data.get("layers", {}).get("branches") or []
    by_name = {branch.get("name"): branch for branch in branches}
    assert by_name["main"]["title_bar"]["background"] == "#068102"
    assert by_name["feature/holodeck-commits"]["title_bar"]["background"] == "#2696d3"
    assert by_name["feature/minecraft-mod-build-local"]["title_bar"]["background"] == "#800000"
    assert all("title_bar" in branch for branch in branches)
    statuses = {branch.get("lineage", {}).get("status") for branch in branches}
    assert {
        "root",
        "structurally-verified",
        "evidence-validated",
        "pending",
        "invalid",
        "missing",
        "parent-ref-missing",
        "ref-diverged",
    }.issubset(statuses)
    accepted = {"structurally-verified", "evidence-validated"}
    for branch in branches:
        lineage = branch.get("lineage") or {}
        status = lineage.get("status")
        if status in accepted:
            assert lineage.get("authoritative") is True
            assert lineage.get("fork_date")
            assert branch.get("parent", {}).get("name") == lineage.get("parent_branch")
        elif status != "root":
            assert lineage.get("authoritative") is False
            assert lineage.get("fork_date") is None
            assert branch.get("parent") is None
        else:
            assert lineage.get("fork_date") is None
        fork = lineage.get("fork_commit")
        if fork:
            assert len(fork) == 40
        record = lineage.get("record") or {}
        if record.get("commit"):
            assert len(record["commit"]) == 40
    assert {
        (branch.get("lineage", {}).get("record") or {}).get("version")
        for branch in branches
    } >= {"1", "2"}

### HTTP smoke
def test_get_index_returns_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Holodeck" in response.text or "worktree-cards" in response.text
def test_get_static_app_js_returns_javascript():
    response = client.get("/static/app.js")
    assert response.status_code == 200
    assert "javascript" in response.headers.get("content-type", "")
    assert "function renderWorktrees" in response.text
def test_get_api_state_returns_normalized_document():
    response = client.get("/api/state")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload.get("worktrees"), dict)
    assert isinstance(payload.get("next_steps"), list)
def test_get_api_agents_returns_document(monkeypatch):
    import apps.holodeck.server as holodeck_server

    def fake_list_agent_status(conn, hours=48, limit=16, now=None):
        return []

    monkeypatch.setattr(holodeck_server.turns_db, "list_agent_status", fake_list_agent_status)
    response = client.get("/api/agents")
    assert response.status_code in (200,)
    payload = response.json()
    assert isinstance(payload.get("agents"), list)
def test_post_api_refresh_unknown_layer_returns_400():
    response = client.post("/api/refresh", json={"layers": ["not-a-layer"]})
    assert response.status_code == 400
    assert "unknown layer" in response.json().get("detail", "")
