import assert from 'node:assert/strict';
import test, { afterEach } from 'node:test';
import {
  startTelemetrySession,
  logEvent,
  logQuizRound,
  logQuizAttempt,
  attachClickCapture,
  __testing,
} from '../src/lib/applet-telemetry.js';

const originalDescriptors = new Map();
const originalDateNow = Date.now;

function setGlobal(name, value) {
  if (!originalDescriptors.has(name)) {
    originalDescriptors.set(name, Object.getOwnPropertyDescriptor(globalThis, name));
  }
  Object.defineProperty(globalThis, name, { value, writable: true, configurable: true });
}
function restoreGlobals() {
  for (const [name, descriptor] of originalDescriptors.entries()) {
    if (descriptor) Object.defineProperty(globalThis, name, descriptor);
    else delete globalThis[name];
  }
  originalDescriptors.clear();
  Date.now = originalDateNow;
}
function fakeStorage() {
  const map = new Map();
  return {
    getItem(key) {
      return map.has(key) ? map.get(key) : null;
    },
    setItem(key, value) {
      map.set(key, String(value));
    },
    removeItem(key) {
      map.delete(key);
    },
    key(index) {
      return [...map.keys()][index] || null;
    },
    get length() {
      return map.size;
    },
    dump() {
      return Object.fromEntries(map.entries());
    },
  };
}
function setupBrowser(search = '') {
  const storage = fakeStorage();
  const documentListeners = new Map();
  const windowListeners = new Map();
  const doc = {
    visibilityState: 'visible',
    addEventListener(type, handler) {
      documentListeners.set(type, handler);
    },
    removeEventListener(type, handler) {
      if (documentListeners.get(type) === handler) documentListeners.delete(type);
    },
  };
  const nav = { userAgent: 'test-agent' };
  const win = {
    location: { search, hostname: 'localhost' },
    sessionStorage: storage,
    navigator: nav,
    document: doc,
    addEventListener(type, handler) {
      windowListeners.set(type, handler);
    },
    removeEventListener(type, handler) {
      if (windowListeners.get(type) === handler) windowListeners.delete(type);
    },
  };
  setGlobal('window', win);
  setGlobal('document', doc);
  setGlobal('navigator', nav);
  setGlobal('sessionStorage', storage);
  return { storage, doc, documentListeners, windowListeners };
}

afterEach(() => {
  __testing.reset();
  restoreGlobals();
});

test('formats local stamps for filenames and wall times', () => {
  const parts = __testing.formatDateParts(new Date(2026, 6, 11, 9, 8, 7));
  assert.equal(parts.stamp, '2026-07-11_090807');
  assert.equal(parts.wallTime, '2026-07-11 09:08:07');
});

test('sanitizes query user and defaults missing user to anon', () => {
  setupBrowser('?user=Kid1!');
  let session = startTelemetrySession({ applet: 'logic-gates' });
  assert.equal(session.user, 'Kid1');

  __testing.reset();
  setupBrowser('');
  session = startTelemetrySession({ applet: 'logic-gates' });
  assert.equal(session.user, 'anon');
});

test('builds the expected session id shape', () => {
  setupBrowser('?user=Randy');
  const session = startTelemetrySession({ applet: 'logic-gates' });
  assert.match(session.session_id, /^logic-gates_Randy_\d{4}-\d{2}-\d{2}_\d{6}$/);
});

test('event t_ms values are monotonic', () => {
  setupBrowser('?user=Kid1');
  let now = 1000;
  Date.now = () => now;
  startTelemetrySession({ applet: 'logic-gates' });
  now = 1012;
  const first = logEvent('toggle', { step: 1 });
  now = 1008;
  const second = logEvent('toggle', { step: 1 });
  assert.equal(first.t_ms, 12);
  assert.equal(second.t_ms, 12);
});

test('persists the session buffer to sessionStorage on every mutation', () => {
  const { storage } = setupBrowser('?user=Kid1');
  startTelemetrySession({ applet: 'logic-gates' });
  logEvent('toggle', { step: 2, target: 'A', detail: { inputs: [1, 0] } });
  const stored = JSON.parse(storage.getItem('applet-telemetry:logic-gates'));
  assert.equal(stored.user, 'Kid1');
  assert.equal(stored.events.length, 2);
  assert.equal(stored.events[1].kind, 'toggle');
  assert.deepEqual(stored.events[1].detail, { inputs: [1, 0] });
});

test('builds the flush payload shape with quiz helpers', () => {
  setupBrowser('?user=Kid1');
  startTelemetrySession({ applet: 'logic-gates' });
  logQuizRound('AND', 0, '10', 8);
  logQuizAttempt('AND', 0, '10', '1', false, 8);
  const payload = __testing.buildPayload();
  assert.equal(payload.applet, 'logic-gates');
  assert.equal(payload.user, 'Kid1');
  assert.match(payload.session_id, /^logic-gates_K1_/);
  assert.equal(payload.user_agent, 'test-agent');
  assert.equal(payload.events.at(-1).kind, 'quiz-attempt');
  assert.deepEqual(payload.events.at(-1).detail, {
    quiz: 'AND',
    round: 0,
    prompt: '10',
    given: '1',
    isCorrect: false,
  });
});

test('flushes automatically every 25 buffered events', () => {
  setupBrowser('?user=Kid1');
  const calls = [];
  setGlobal('fetch', (url, options) => {
    calls.push({ url, options });
    return Promise.resolve({ ok: true });
  });
  startTelemetrySession({ applet: 'logic-gates' });
  for (let i = 0; i < 24; i++) {
    logEvent('click', { step: 0, target: `button ${i}` });
  }
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'http://localhost:8787/api/save-session');
  assert.equal(JSON.parse(calls[0].options.body).events.length, 25);
});

test('click capture uses aria-label, text, and tag labels', () => {
  setupBrowser('?user=Kid1');
  startTelemetrySession({ applet: 'logic-gates' });
  assert.equal(__testing.clickTargetLabel({
    closest() {
      return { getAttribute: () => 'light on' };
    },
    textContent: 'ignored',
    tagName: 'BUTTON',
  }), 'light on');
  assert.equal(__testing.clickTargetLabel({
    closest() {
      return null;
    },
    textContent: '  a long label with    spacing  ',
    tagName: 'BUTTON',
  }), 'a long label with spacing');
  assert.equal(__testing.clickTargetLabel({
    closest() {
      return null;
    },
    textContent: '',
    tagName: 'RECT',
  }), 'rect');
});

test('attachClickCapture logs clicks with the root step', () => {
  setupBrowser('?user=Kid1');
  startTelemetrySession({ applet: 'logic-gates' });
  let handler = null;
  const root = {
    dataset: { telemetryStep: '3' },
    addEventListener(type, nextHandler, options) {
      assert.equal(type, 'click');
      assert.equal(options, true);
      handler = nextHandler;
    },
    removeEventListener() {},
  };
  const detach = attachClickCapture(root);
  handler({ target: { closest: () => null, textContent: 'Next', tagName: 'BUTTON' } });
  detach();
  const event = __testing.buildPayload().events.at(-1);
  assert.equal(event.kind, 'click');
  assert.equal(event.step, 3);
  assert.equal(event.target, 'Next');
});
