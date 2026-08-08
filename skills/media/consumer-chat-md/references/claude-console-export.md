file: skills/media/consumer-chat-md/references/claude-console-export.md
title: Claude.ai consumer chat browser export

Use this when you want **selected Claude.ai web/iPhone chats** (not Claude Code sessions).

## Steps

1. Open [claude.ai](https://claude.ai) in a desktop browser and sign in.
2. Open DevTools → **Console**.
3. Paste the snippet below and press Enter.
4. When prompted, enter a **title substring** (case-insensitive) or exact conversation UUID. Leave blank to export the 5 most recent chats.
5. The browser downloads `holodeck-claude-chat-<timestamp>.json` to `~/Downloads`.
6. Convert with the skill CLI:

```bash
.venv/bin/python3 skills/media/consumer-chat-md/scripts/consumer_chat_md.py \
  --claude-json ~/Downloads/holodeck-claude-chat-*.json \
  --select 'speech recognition' \
  --out-dir "$FOF_MONO_LOCAL_FILES_ROOT/consumer-chats"
```

## Console snippet

```javascript
(async () => {
  const filter = prompt("Title substring or conversation UUID (blank = 5 most recent):")?.trim() || "";
  const orgResp = await fetch("https://claude.ai/api/organizations", { credentials: "include" });
  if (!orgResp.ok) throw new Error("organizations HTTP " + orgResp.status);
  const orgs = await orgResp.json();
  const orgId = (Array.isArray(orgs) ? orgs[0]?.uuid : orgs?.uuid) || orgs?.[0]?.id;
  if (!orgId) throw new Error("Could not resolve Claude organization id");
  const listResp = await fetch(`https://claude.ai/api/organizations/${orgId}/chat_conversations`, { credentials: "include" });
  if (!listResp.ok) throw new Error("chat_conversations HTTP " + listResp.status);
  const listed = await listResp.json();
  const rows = Array.isArray(listed) ? listed : (listed.conversations || listed.data || []);
  let picks = rows;
  if (filter) {
    const lower = filter.toLowerCase();
    picks = rows.filter((row) => {
      const id = String(row.uuid || row.id || "");
      const title = String(row.name || row.title || row.summary || "");
      return id === filter || title.toLowerCase().includes(lower);
    });
  } else {
    picks = rows.slice(0, 5);
  }
  if (!picks.length) throw new Error("No conversations matched filter: " + filter);
  const conversations = [];
  for (const row of picks) {
    const id = row.uuid || row.id;
    const detailResp = await fetch(
      `https://claude.ai/api/organizations/${orgId}/chat_conversations/${id}?tree=True&rendering_mode=messages&render_all_tools=true`,
      { credentials: "include" }
    );
    if (!detailResp.ok) throw new Error("detail HTTP " + detailResp.status + " for " + id);
    const detail = await detailResp.json();
    const chatMessages = detail.chat_messages || detail.messages || [];
    const messages = [];
    const byUuid = Object.fromEntries(chatMessages.filter((m) => m.uuid).map((m) => [m.uuid, m]));
    const children = {};
    const roots = [];
    for (const msg of chatMessages) {
      if (msg.parent_uuid && byUuid[msg.parent_uuid]) {
        (children[msg.parent_uuid] ||= []).push(msg);
      } else {
        roots.push(msg);
      }
    }
    const textFrom = (node) => {
      const value = node.text ?? node.content;
      if (typeof value === "string") return value.trim();
      if (Array.isArray(value)) {
        return value.map((part) => (typeof part === "string" ? part : part?.text || "")).join("\n\n").trim();
      }
      return "";
    };
    const roleFrom = (sender) => ((sender || "").toLowerCase() === "human" ? "user" : "assistant");
    const walk = (node) => {
      const text = textFrom(node);
      if (text) messages.push({ role: roleFrom(node.sender), text, ts: node.created_at || null });
      for (const child of (children[node.uuid] || []).sort((a, b) => (a.created_at || "").localeCompare(b.created_at || ""))) {
        walk(child);
      }
    };
    for (const root of roots.sort((a, b) => (a.created_at || "").localeCompare(b.created_at || ""))) walk(root);
    conversations.push({
      id,
      title: row.name || row.title || detail.name || detail.title || "Untitled chat",
      source_url: `https://claude.ai/chat/${id}`,
      date: (row.created_at || row.updated_at || detail.created_at || "").slice(0, 10) || null,
      messages,
    });
  }
  const payload = {
    source: "claude",
    exported_at: new Date().toISOString(),
    conversations,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `holodeck-claude-chat-${stamp}.json`;
  a.click();
  console.log(`Exported ${conversations.length} conversation(s)`);
})();
```

## Notes

- **WIP:** this manual console path is the current stand-in. Automatic fetch via Holodeck's Playwright Claude profile (same cookie, different API) is intended but not built — see the skill README.
- This uses Claude's **consumer chat** API (`chat_conversations`), not Claude Code cloud (`/v1/code/sessions`).
- Auth is your logged-in browser session (`credentials: "include"`). No cookie paste required for this snippet.
- Holodeck's coding-session collectors and `turns.db` do **not** ingest these exports.
