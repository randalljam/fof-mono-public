"""Derive Randy-facing AI session labels."""

QUALIFIER_LABELS = {
    "high": "High",
    "fast": "Fast",
    "max": "K2",
    "1m": "1M",
}
TOOL_FALLBACKS = {
    "cursor": "Cursor",
    "claude-code": "Claude Code",
    "claude-cloud": "Claude Cloud",
    "codex": "Codex",
    "codex-cloud": "Codex Cloud",
}
PLATFORM_FALLBACKS = {
    "cursor": "Cursor",
    "claude": "Claude",
    "codex": "Codex",
}
LEGACY_TOOL_PLATFORM = {
    "claude-code": "claude",
    "claude-cloud": "claude",
    "codex": "codex",
    "codex-cloud": "codex",
    "cursor": "cursor",
}
LEGACY_CLOUD_TOOLS = {"claude-cloud", "codex-cloud"}
DELEGATED_NOTE = "fable5-w-codex"
DELEGATED_INTERFACE = "Codex CLI (" + DELEGATED_NOTE + ")"
OPERATOR_ORIGIN = "operator"
DELEGATED_ORIGIN = "delegated"
DELEGATED_PREAMBLE_PREFIXES = (
    "You are the implementation executor",
    "You are the implementation",
)
DELEGATED_PREAMBLE_MARKER = "Do not commit or push."
PLUGIN_COMPANION_ORIGINATORS = {
    "plugin companion",
    "plugin-companion",
    "plugin_companion",
}
### Formatting
def title_token(token):
    if not token:
        return token
    lowered = str(token).lower()
    if lowered == "gpt":
        return "GPT"
    if lowered == "ios":
        return "iOS"
    return lowered[:1].upper() + lowered[1:]
def unique_append(values, value):
    if value and value not in values:
        values.append(value)
def model_tokens(value):
    return [token for token in str(value or "").replace("_", "-").split("-") if token]
def pretty_model_with_qualifiers(raw_model, qualifier_tokens=None):
    tokens = model_tokens(raw_model)
    words = []
    qualifiers = []
    for token in tokens:
        lowered = token.lower()
        if lowered in QUALIFIER_LABELS:
            unique_append(qualifiers, QUALIFIER_LABELS[lowered])
            continue
        words.append(title_token(token))
    for token in qualifier_tokens or []:
        lowered = str(token or "").lower()
        unique_append(qualifiers, QUALIFIER_LABELS.get(lowered, title_token(lowered)))
    model = " ".join(words).strip()
    if qualifiers:
        model = (model + " " + " ".join(qualifiers)).strip()
    return model or None
def pretty_claude_model(raw_model):
    value = str(raw_model or "").strip()
    if not value:
        return None
    if value.startswith("claude-"):
        value = value[len("claude-"):]
    value = value.replace("_", "-")
    collapsed = []
    tokens = [token for token in value.split("-") if token]
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.isdigit() and index + 1 < len(tokens) and tokens[index + 1].isdigit():
            collapsed.append(token + "." + tokens[index + 1])
            index += 2
            continue
        collapsed.append(token)
        index += 1
    return " ".join(title_token(token) for token in collapsed).strip() or None
def pretty_codex_model(raw_model):
    return pretty_model_with_qualifiers(raw_model)
def truthy(value):
    if value is True:
        return True
    if value is False or value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
def platform_from_legacy(tool):
    value = str(tool or "").strip()
    return LEGACY_TOOL_PLATFORM.get(value, value if value in PLATFORM_FALLBACKS else None)
def session_platform(session):
    platform = session.get("platform")
    if platform in LEGACY_TOOL_PLATFORM:
        return LEGACY_TOOL_PLATFORM[platform]
    if platform in PLATFORM_FALLBACKS:
        return platform
    return platform_from_legacy(session.get("tool"))
def session_host(session):
    host = session.get("host")
    if host in ("local", "cloud"):
        return host
    tool = session.get("tool") or session.get("platform")
    return "cloud" if tool in LEGACY_CLOUD_TOOLS else "local"
def normalized_entrypoint(platform, entrypoint=None, tool=None, originator=None, source=None, thread_source=None):
    value = str(entrypoint or "").strip()
    if tool in LEGACY_CLOUD_TOOLS:
        return "app"
    if platform == "cursor":
        return "app"
    if platform == "claude":
        if value in ("app", "claude-desktop"):
            return "app"
        return "cli"
    if platform == "codex":
        if value in ("subagent", "codex-subagent") or thread_source == "subagent" or isinstance(source, dict):
            return "subagent"
        if value in ("cli", "codex-cli") or source in ("exec", "cli") or originator in ("codex_exec", "codex-tui", "Claude Code"):
            return "cli"
        if value in ("app", "codex-desktop", "codex-vscode") or originator in ("Codex Desktop", "codex_work_desktop"):
            return "app"
        return "app"
    if value in ("cli", "app", "subagent"):
        return value
    return None
def session_entrypoint(session):
    return normalized_entrypoint(
        session_platform(session),
        session.get("entrypoint"),
        tool=session.get("tool") or session.get("platform"),
        originator=session.get("originator"),
        source=session.get("source"),
        thread_source=session.get("thread_source"),
    )
def normalize_session_schema(session):
    legacy_tool = session.pop("tool", None)
    legacy_platform = session.get("platform")
    legacy_source = legacy_tool or legacy_platform
    platform = session_platform({**session, "tool": legacy_tool})
    session["platform"] = platform
    session["entrypoint"] = normalized_entrypoint(
        platform,
        session.get("entrypoint"),
        tool=legacy_source,
        originator=session.get("originator"),
        source=session.get("source"),
        thread_source=session.get("thread_source"),
    )
    session["host"] = session_host({**session, "tool": legacy_source})
    session["remote_control"] = truthy(session.get("remote_control"))
    session["bridge_session_id"] = session.get("bridge_session_id") or None
    return session
def platform_title(platform):
    return PLATFORM_FALLBACKS.get(platform, title_token(platform) if platform else "AI Session")
def entrypoint_title(entrypoint, platform=None):
    if platform == "cursor" and entrypoint == "app":
        return "IDE"
    if entrypoint == "cli":
        return "CLI"
    if entrypoint == "app":
        return "App"
    if entrypoint == "subagent":
        return "Subagent"
    return title_token(entrypoint) if entrypoint else "Session"
def fallback_label(platform):
    return PLATFORM_FALLBACKS.get(platform, TOOL_FALLBACKS.get(platform, str(platform or "AI Session")))
def interface_with_qualifiers(base, session):
    interface = base
    if session_host(session) == "cloud":
        interface += " (Cloud)"
    if truthy(session.get("remote_control")):
        interface += " (Remote Control)"
    return interface
def session_interface(session, delegated=False):
    platform = session_platform(session)
    entrypoint = session_entrypoint(session)
    base = platform_title(platform) + " " + entrypoint_title(entrypoint, platform=platform)
    if delegated and platform == "codex" and entrypoint in ("cli", "subagent"):
        base += " (" + DELEGATED_NOTE + ")"
    return interface_with_qualifiers(base, session)
def looks_delegated(text):
    value = str(text or "").lstrip()
    if not value:
        return False
    for prefix in DELEGATED_PREAMBLE_PREFIXES:
        if value.startswith(prefix):
            return True
    return DELEGATED_PREAMBLE_MARKER in value[:400]
def codex_originator_is_delegated(originator):
    value = str(originator or "").strip()
    if value == "Claude Code":
        return True
    normalized = value.lower().replace(" ", "-")
    compact = value.lower().replace(" ", "_")
    return value.lower() in PLUGIN_COMPANION_ORIGINATORS or normalized in PLUGIN_COMPANION_ORIGINATORS or compact in PLUGIN_COMPANION_ORIGINATORS
def session_label_maps_to_delegated(session):
    values = [
        session.get("label"),
        session.get("interface"),
    ]
    return any(DELEGATED_INTERFACE in str(value or "") for value in values)
def first_user_hint(session):
    return session.get("_first_user_text") or session.get("first_user") or session.get("last_user")
def codex_originator_is_operator_cli(originator, source=None):
    # Interactive Codex CLI (TUI) is Randy operating the CLI directly — not fable machinery.
    return str(originator or "").strip() == "codex-tui" or source == "cli"
def codex_session_is_delegated(session):
    # Codex subagents and non-interactive exec / Claude Code launches are machinery.
    # Interactive Codex CLI (codex-tui) is operator-facing and stays visible in AI Sessions.
    if session_platform(session) != "codex":
        return False
    entrypoint = session_entrypoint(session)
    if entrypoint == "subagent":
        return True
    if codex_originator_is_operator_cli(session.get("originator"), session.get("source")):
        return looks_delegated(first_user_hint(session))
    if entrypoint == "cli":
        return True
    return (
        codex_originator_is_delegated(session.get("originator"))
        or looks_delegated(first_user_hint(session))
        or session_label_maps_to_delegated(session)
    )
def derive_session_origin(session):
    platform = session_platform(session)
    if platform in ("cursor", "claude"):
        return OPERATOR_ORIGIN
    if platform == "codex":
        # Always recompute for Codex so a stale delegated flag cannot stick after
        # an interactive TUI session is correctly classified as operator CLI.
        return DELEGATED_ORIGIN if codex_session_is_delegated(session) else OPERATOR_ORIGIN
    existing = session.get("origin")
    if existing in (OPERATOR_ORIGIN, DELEGATED_ORIGIN):
        return existing
    return OPERATOR_ORIGIN

### Cursor
def cursor_selected_qualifiers(selected_models):
    qualifiers = []
    for selected in selected_models or []:
        parameters = selected.get("parameters") or []
        if isinstance(parameters, dict):
            parameters = [parameters]
        for parameter in parameters:
            param_id = str(parameter.get("id") or "").lower()
            if param_id in QUALIFIER_LABELS and truthy(parameter.get("value")):
                unique_append(qualifiers, param_id)
    return qualifiers
def cursor_label_parts(session):
    config = session.get("model_config") or {}
    raw_model = session.get("raw_model") or config.get("modelName")
    qualifiers = cursor_selected_qualifiers(session.get("selected_models"))
    if truthy(config.get("maxMode")):
        unique_append(qualifiers, "max")
    model = pretty_model_with_qualifiers(raw_model, qualifiers)
    interface = session_interface(session)
    if model and session.get("unified_mode") == "plan":
        model += " (.plan.md)"
    return interface, model
def cursor_label(session):
    interface, model = cursor_label_parts(session)
    if not model:
        return fallback_label("cursor"), None, interface
    return interface + " - " + model, model, interface

### Claude Code
def claude_label(session):
    model = pretty_claude_model(session.get("raw_model") or session.get("model"))
    interface = session_interface(session)
    if not model:
        return fallback_label("claude"), None, interface
    return interface + " - " + model, model, interface

### Codex
def codex_interface(session):
    return session_interface(session, delegated=codex_session_is_delegated(session))
def codex_label(session):
    model = pretty_codex_model(session.get("raw_model") or session.get("model"))
    effort = session.get("effort")
    interface = codex_interface(session)
    if not model:
        return fallback_label("codex"), None, interface
    display_model = model
    if effort:
        display_model = display_model + " " + str(effort)
    return interface + " - " + display_model, display_model, interface

### Public API
def derive_session_label(session):
    session = dict(session)
    normalize_session_schema(session)
    platform = session.get("platform")
    if platform == "cursor":
        return cursor_label(session)
    if platform == "claude":
        return claude_label(session)
    if platform == "codex":
        return codex_label(session)
    return fallback_label(platform), None, fallback_label(platform)
def apply_session_label(session):
    normalize_session_schema(session)
    label, model, interface = derive_session_label(session)
    session["label"] = label
    session["model"] = model
    session["interface"] = interface
    session["origin"] = derive_session_origin(session)
    session.pop("_first_user_text", None)
    return session
