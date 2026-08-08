import { saveAppletSession } from "./applet-session-store.js";

const FLUSH_URL = "http://localhost:8787/api/save-session";
const FLUSH_EVERY_EVENTS = 25;
let liveSession = null;
let lifecycleCleanup = null;

function hasWindow() {
  return typeof globalThis !== "undefined" && typeof globalThis.window !== "undefined";
}
function getWindow() {
  return hasWindow() ? globalThis.window : null;
}
function getDocument() {
  if (typeof globalThis !== "undefined" && globalThis.document) return globalThis.document;
  const win = getWindow();
  return win && win.document ? win.document : null;
}
function getNavigator() {
  if (typeof globalThis !== "undefined" && globalThis.navigator) return globalThis.navigator;
  const win = getWindow();
  return win && win.navigator ? win.navigator : null;
}
function getStorage() {
  try {
    const win = getWindow();
    return win && win.sessionStorage ? win.sessionStorage : globalThis.sessionStorage || null;
  } catch (e) {
    return null;
  }
}
function pad2(value) {
  return String(value).padStart(2, "0");
}
function formatDateParts(date) {
  const year = date.getFullYear();
  const month = pad2(date.getMonth() + 1);
  const day = pad2(date.getDate());
  const hour = pad2(date.getHours());
  const minute = pad2(date.getMinutes());
  const second = pad2(date.getSeconds());
  return {
    stamp: `${year}-${month}-${day}_${hour}${minute}${second}`,
    wallTime: `${year}-${month}-${day} ${hour}:${minute}:${second}`,
  };
}
function sanitizeToken(value, fallback) {
  const clean = String(value || "").replace(/[^a-zA-Z0-9_-]/g, "");
  return clean || fallback;
}
function queryUser() {
  try {
    const win = getWindow();
    const search = win && win.location ? win.location.search || "" : "";
    return sanitizeToken(new URLSearchParams(search).get("user"), "anon");
  } catch (e) {
    return "anon";
  }
}
function storageKey(applet) {
  return `applet-telemetry:${applet}`;
}
function cloneDetail(detail) {
  if (detail === undefined) return null;
  try {
    return JSON.parse(JSON.stringify(detail));
  } catch (e) {
    return String(detail);
  }
}
function readStoredSession(applet) {
  try {
    const storage = getStorage();
    if (!storage) return null;
    const raw = storage.getItem(storageKey(applet));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || parsed.applet !== applet || !Array.isArray(parsed.events)) return null;
    parsed.start_epoch_ms = Number(parsed.start_epoch_ms) || Date.now();
    parsed.last_t_ms = parsed.events.reduce((max, event) => Math.max(max, Number(event.t_ms) || 0), 0);
    return parsed;
  } catch (e) {
    return null;
  }
}
function persistSession() {
  if (!liveSession) return;
  try {
    const storage = getStorage();
    if (storage) storage.setItem(storageKey(liveSession.applet), JSON.stringify(liveSession));
  } catch (e) {}
}
function eventTimeMs() {
  if (!liveSession) return 0;
  const elapsed = Math.max(0, Math.round(Date.now() - liveSession.start_epoch_ms));
  const t = Math.max(elapsed, liveSession.last_t_ms || 0);
  liveSession.last_t_ms = t;
  return t;
}
function appendEvent(kind, fields, forcedTMs) {
  if (!liveSession) return null;
  try {
    const event = {
      t_ms: forcedTMs === undefined ? eventTimeMs() : forcedTMs,
      kind,
      step: fields && fields.step !== undefined ? fields.step : null,
      target: fields && fields.target !== undefined ? fields.target : null,
      detail: cloneDetail(fields ? fields.detail : null),
    };
    liveSession.events.push(event);
    liveSession.last_t_ms = Math.max(liveSession.last_t_ms || 0, event.t_ms);
    persistSession();
    if (liveSession.events.length > 0 && liveSession.events.length % FLUSH_EVERY_EVENTS === 0) flushTelemetry();
    return event;
  } catch (e) {
    return null;
  }
}
function buildPayload() {
  if (!liveSession) return null;
  return {
    applet: liveSession.applet,
    user: liveSession.user,
    session_id: liveSession.session_id,
    start_stamp: liveSession.start_stamp,
    start_wall_time: liveSession.start_wall_time,
    user_agent: liveSession.user_agent,
    events: liveSession.events,
  };
}
function installLifecycleFlush() {
  if (lifecycleCleanup) return;
  try {
    const win = getWindow();
    const doc = getDocument();
    if (!win || !doc || typeof win.addEventListener !== "function") return;
    const onVisibility = () => {
      try {
        if (doc.visibilityState === "hidden") flushTelemetry();
      } catch (e) {}
    };
    const onPageHide = () => flushTelemetry({ beacon: true });
    if (typeof doc.addEventListener === "function") doc.addEventListener("visibilitychange", onVisibility);
    win.addEventListener("pagehide", onPageHide);
    lifecycleCleanup = () => {
      try {
        if (typeof doc.removeEventListener === "function") doc.removeEventListener("visibilitychange", onVisibility);
        win.removeEventListener("pagehide", onPageHide);
      } catch (e) {}
    };
  } catch (e) {}
}
function textLabel(text) {
  const label = String(text || "").replace(/\s+/g, " ").trim();
  return label.length > 40 ? label.slice(0, 40) : label;
}
function nearestAriaLabel(target) {
  try {
    if (target && typeof target.closest === "function") {
      const labeled = target.closest("[aria-label]");
      const label = labeled && typeof labeled.getAttribute === "function" ? labeled.getAttribute("aria-label") : "";
      if (textLabel(label)) return textLabel(label);
    }
  } catch (e) {}
  try {
    let node = target && target.nodeType === 1 ? target : target && target.parentElement;
    while (node) {
      if (typeof node.getAttribute === "function") {
        const label = textLabel(node.getAttribute("aria-label"));
        if (label) return label;
      }
      node = node.parentElement;
    }
  } catch (e) {}
  return "";
}
function clickTargetLabel(target) {
  const aria = nearestAriaLabel(target);
  if (aria) return aria;
  const text = textLabel(target && target.textContent);
  if (text) return text;
  return target && target.tagName ? String(target.tagName).toLowerCase() : "unknown";
}
function rootStep(rootEl) {
  try {
    const value = rootEl && rootEl.dataset ? rootEl.dataset.telemetryStep : null;
    if (value === undefined || value === null || value === "") return null;
    const step = Number(value);
    return Number.isFinite(step) ? step : null;
  } catch (e) {
    return null;
  }
}

export function startTelemetrySession({ applet }) {
  try {
    const appletName = sanitizeToken(applet, "applet");
    if (liveSession && liveSession.applet === appletName) return liveSession;
    const stored = readStoredSession(appletName);
    if (stored) {
      liveSession = stored;
      installLifecycleFlush();
      return liveSession;
    }
    const user = queryUser();
    const now = new Date();
    const parts = formatDateParts(now);
    const navigatorObj = getNavigator();
    liveSession = {
      applet: appletName,
      user,
      session_id: `${appletName}_${user}_${parts.stamp}`,
      start_stamp: parts.stamp,
      start_wall_time: parts.wallTime,
      start_epoch_ms: Date.now(),
      user_agent: navigatorObj && navigatorObj.userAgent ? navigatorObj.userAgent : "",
      events: [],
      last_t_ms: 0,
    };
    appendEvent("start", { detail: { applet: appletName } }, 0);
    installLifecycleFlush();
    return liveSession;
  } catch (e) {
    return null;
  }
}
export function logEvent(kind, { step, target, detail } = {}) {
  return appendEvent(kind, { step, target, detail });
}
export function logQuizRound(quiz, round, prompt, step) {
  return logEvent("quiz-round", { step, detail: { quiz, round, prompt } });
}
export function logQuizAttempt(quiz, round, prompt, given, isCorrect, step) {
  return logEvent("quiz-attempt", { step, detail: { quiz, round, prompt, given, isCorrect } });
}
export function attachClickCapture(rootEl) {
  try {
    if (!rootEl || typeof rootEl.addEventListener !== "function") return () => {};
    const onClick = (event) => {
      logEvent("click", {
        step: rootStep(rootEl),
        target: clickTargetLabel(event && event.target),
      });
    };
    rootEl.addEventListener("click", onClick, true);
    return () => {
      try {
        rootEl.removeEventListener("click", onClick, true);
      } catch (e) {}
    };
  } catch (e) {
    return () => {};
  }
}
export function flushTelemetry(options = {}) {
  try {
    if (!liveSession) return undefined;
    const payload = buildPayload();
    if (!payload) return undefined;
    // Durable persistence: signed-in sessions upsert to the user's account,
    // guest sessions to fofGuest.* (migrates on sign-up).
    try {
      saveAppletSession(payload.applet, payload).catch(() => {});
    } catch (e) {}
    // The localhost receiver only exists in local dev — POSTing to it from the
    // deployed site just sprays ERR_CONNECTION_REFUSED in visitors' consoles.
    const win = getWindow();
    const hostname = win && win.location ? win.location.hostname : "";
    if (hostname !== "localhost" && hostname !== "127.0.0.1") return undefined;
    const body = JSON.stringify(payload);
    const navigatorObj = getNavigator();
    if (options.beacon && navigatorObj && typeof navigatorObj.sendBeacon === "function" && typeof Blob !== "undefined") {
      navigatorObj.sendBeacon(FLUSH_URL, new Blob([body], { type: "application/json" }));
      return undefined;
    }
    const fetchFn = typeof globalThis.fetch === "function" ? globalThis.fetch : getWindow() && getWindow().fetch;
    if (typeof fetchFn !== "function") return undefined;
    return fetchFn(FLUSH_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
    }).catch(() => {});
  } catch (e) {
    return undefined;
  }
}
export const __testing = {
  formatDateParts,
  sanitizeToken,
  storageKey,
  clickTargetLabel,
  buildPayload,
  reset() {
    try {
      if (lifecycleCleanup) lifecycleCleanup();
    } catch (e) {}
    liveSession = null;
    lifecycleCleanup = null;
  },
};
