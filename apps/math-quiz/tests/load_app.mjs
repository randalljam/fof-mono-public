// Loads the math-quiz browser scripts into a Node vm context with DOM stubs
// so the pure logic can be unit-tested without a browser.
// Each page gets its own context (the page scripts share top-level names).
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import vm from 'node:vm';
import crypto from 'node:crypto';

const appDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

function makeStubElement() {
  return {
    style: {},
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    addEventListener() {},
    removeEventListener() {},
    appendChild() {},
    setAttribute() {},
    getAttribute() { return null; },
    remove() {},
    focus() {},
    click() {},
    innerHTML: '',
    textContent: '',
    value: '',
    disabled: false
  };
}

export function createAppContext(files) {
  // Elements registered by tests via context.__setElement(id, el)
  const elements = new Map();
  const documentStub = {
    readyState: 'complete',
    head: { appendChild() {} },
    body: { appendChild() {}, removeChild() {}, addEventListener() {} },
    documentElement: {},
    createElement: () => makeStubElement(),
    getElementById: (id) => elements.get(id) || null,
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener() {}
  };
  const storage = new Map();
  const localStorageStub = {
    get length() { return storage.size; },
    key: (i) => Array.from(storage.keys())[i] ?? null,
    getItem: (k) => (storage.has(k) ? storage.get(k) : null),
    setItem: (k, v) => storage.set(k, String(v)),
    removeItem: (k) => storage.delete(k),
    clear: () => storage.clear()
  };
  const context = {
    console,
    document: documentStub,
    localStorage: localStorageStub,
    window: {
      location: { hostname: 'localhost', protocol: 'http:', pathname: '/math_quiz.html', origin: 'http://localhost' },
      innerWidth: 1280,
      devicePixelRatio: 1,
      localStorage: localStorageStub
    },
    alert() {},
    confirm() { return true; },
    setTimeout,
    clearTimeout,
    // md5 normally comes from the blueimp CDN script
    md5: (text) => crypto.createHash('md5').update(String(text)).digest('hex'),
    __setElement: (id, el) => elements.set(id, el),
    __makeStubElement: makeStubElement
  };
  vm.createContext(context);
  for (const file of files) {
    const code = readFileSync(path.join(appDir, file), 'utf8');
    vm.runInContext(code, context, { filename: file });
  }
  // Evaluate an expression (or call a function) inside the app context
  context.__eval = (expression) => vm.runInContext(expression, context);
  // Retrieve a binding (e.g. a function) from the context so it can be called
  // with host objects such as a real sql.js database
  context.__get = (name) => vm.runInContext(name, context);
  // Same, but JSON-roundtripped: vm values come from another realm, so their
  // prototypes fail assert.deepEqual without normalization
  context.__evalJson = (expression) => {
    const value = vm.runInContext(expression, context);
    return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
  };
  return context;
}
