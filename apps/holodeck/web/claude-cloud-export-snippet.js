/* Holodeck Claude cloud export — paste into the DevTools console on https://claude.ai/code while logged in.
 * Downloads holodeck-claude-cloud-export.json into ~/Downloads. Then return to Holodeck and hit Refresh.
 */
(async () => {
  const API = "https://claude.ai";
  const VERSION = "2023-06-01";
  const STATUSES = ["active", "paused", "completed"];
  const SESSION_LIMIT = 40;
  const EVENT_PAGE_LIMIT = 500;
  const EVENT_PAGE_CAP = 20;
  const EVENT_COUNT_CAP = 10000;
  const headers = { "anthropic-version": VERSION };
  async function apiGet(path) {
    const response = await fetch(API + path, { credentials: "include", headers });
    if (!response.ok) {
      throw new Error(path + " → HTTP " + response.status + (response.status === 403 ? " (Cloudflare/login — stay on claude.ai/code and retry)" : ""));
    }
    return response.json();
  }
  function listSessions(payload) {
    if (Array.isArray(payload)) return payload.filter((item) => item && typeof item === "object");
    if (payload && typeof payload === "object") {
      const values = payload.data || payload.sessions || payload.items || [];
      return Array.isArray(values) ? values.filter((item) => item && typeof item === "object") : [];
    }
    return [];
  }
  async function fetchEvents(sessionId) {
    const events = [];
    let cursor = null;
    for (let page = 0; page < EVENT_PAGE_CAP; page += 1) {
      let path = "/v1/code/sessions/" + encodeURIComponent(sessionId) + "/events?limit=" + EVENT_PAGE_LIMIT + "&sort_order=asc";
      if (cursor) path += "&cursor=" + encodeURIComponent(cursor);
      const payload = await apiGet(path);
      const pageEvents = Array.isArray(payload) ? payload : (payload && payload.data) || [];
      for (const event of pageEvents) {
        if (event && typeof event === "object") events.push(event);
      }
      cursor = payload && typeof payload === "object" ? payload.next_cursor : null;
      if (events.length >= EVENT_COUNT_CAP || !cursor) break;
    }
    return events.slice(0, EVENT_COUNT_CAP);
  }
  console.log("[holodeck] listing Claude Code cloud sessions…");
  const params = new URLSearchParams();
  params.set("limit", String(SESSION_LIMIT));
  for (const status of STATUSES) params.append("statuses", status);
  const summaries = listSessions(await apiGet("/v1/code/sessions?" + params.toString())).slice(0, SESSION_LIMIT);
  if (!summaries.length) throw new Error("No sessions returned. Confirm you are logged into claude.ai/code.");
  const sessions = [];
  for (let index = 0; index < summaries.length; index += 1) {
    const summary = summaries[index];
    const sid = summary.id || summary.session_id;
    if (!sid) continue;
    console.log("[holodeck] " + (index + 1) + "/" + summaries.length + " " + sid);
    const detail = await apiGet("/v1/code/sessions/" + encodeURIComponent(sid));
    const events = await fetchEvents(sid);
    sessions.push({ summary, detail, events });
  }
  const blob = new Blob([JSON.stringify({ sessions }, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "holodeck-claude-cloud-export.json";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  console.log("[holodeck] downloaded holodeck-claude-cloud-export.json (" + sessions.length + " sessions). Return to Holodeck and hit Refresh.");
})().catch((error) => {
  console.error("[holodeck] Claude cloud export failed:", error);
});
