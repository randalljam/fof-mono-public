// Shared, collapsible problem-list EDITOR panel for the anchor + analysis pages. Renders the
// learner's internal problem lists as cards left-to-right in queue order, each with an editable
// textarea (one "a + b" per line), reorder (left/right), rename, retain toggle, and delete --
// all auto-saving to the per-person file via the dev server (POST /api/problem-lists). Plus a
// generator that builds a new list from a count + a percentage mix of categories.
//
// Server-authoritative + keyed by folder+user, so edits land on the SAME file "Use internal"
// runs and the next quiz appends to. Needs the dev server (tools/dev_server.py) reachable; on
// the analysis page that means opening via "Load for analysis" (?folder=&user=). DOM-driven.
import { GENERATOR_CATEGORIES, generateMix, itemsToText } from './list_generator.mjs';

const SAVE_DEBOUNCE_MS = 700;
const DEFAULT_WEIGHTS = { 'add-zero': 10, 'add-one': 10, 'add-two': 10, doubles: 15, 'tough-21': 35, 'sneaky-six': 20 };

function injectStyles() {
  if (document.getElementById('plp-styles')) return;
  const css = `
  .plp-module { border:1px solid #ddd; border-radius:8px; background:#fff; margin:10px 0; }
  .plp-header { display:flex; align-items:center; gap:8px; padding:8px 12px; cursor:pointer; user-select:none; background:#f8f9fa; border-radius:8px 8px 0 0; }
  .plp-header h3 { margin:0; font-size:15px; font-weight:600; }
  .plp-header .plp-sub { color:#777; font-weight:400; font-size:12px; }
  .plp-toggle { color:#666; transition:transform .2s ease; flex-shrink:0; }
  .plp-module.plp-open .plp-toggle { transform:rotate(90deg); }
  .plp-body { padding:10px 12px; border-top:1px solid #eee; }
  .plp-module:not(.plp-open) .plp-body { display:none; }
  .plp-toolbar { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:8px; }
  .plp-btn { font-size:13px; padding:5px 10px; border:1px solid #cfd6de; background:#fff; border-radius:5px; cursor:pointer; color:#333; }
  .plp-btn:hover { background:#eef2f7; }
  .plp-btn.plp-active { background:#1565c0; color:#fff; border-color:#1565c0; }
  .plp-btn[disabled] { opacity:.5; cursor:not-allowed; }
  .plp-status { font-size:12px; color:#777; }
  .plp-note { font-size:12px; color:#b45309; margin:4px 0; }
  .plp-cards { display:flex; gap:10px; overflow-x:auto; padding:4px 2px 8px; align-items:stretch; }
  .plp-card { flex:0 0 230px; display:flex; flex-direction:column; border:1px solid #d8dde3; border-radius:8px; background:#fbfcfe; padding:8px; }
  .plp-card-top { display:flex; align-items:center; gap:4px; margin-bottom:6px; }
  .plp-order { font-weight:700; color:#1565c0; font-size:13px; }
  .plp-name { flex:1; min-width:0; font-size:13px; padding:3px 6px; border:1px solid #c9d2db; border-radius:4px; }
  .plp-iconbtn { border:1px solid #cfd6de; background:#fff; border-radius:4px; cursor:pointer; font-size:12px; line-height:1; padding:3px 5px; }
  .plp-iconbtn:hover { background:#eef2f7; }
  .plp-iconbtn[disabled] { opacity:.35; cursor:not-allowed; }
  .plp-meta { display:flex; align-items:center; justify-content:space-between; font-size:11px; color:#667; margin-bottom:4px; }
  .plp-text { width:100%; box-sizing:border-box; min-height:150px; resize:vertical; font-family:ui-monospace,Menlo,Consolas,monospace; font-size:13px; padding:6px; border:1px solid #c9d2db; border-radius:4px; }
  .plp-card-status { font-size:11px; min-height:14px; margin-top:3px; }
  .plp-card-status.ok { color:#2e7d32; }
  .plp-card-status.err { color:#c62828; }
  .plp-generator { border:1px dashed #c9d2db; border-radius:6px; padding:8px 10px; margin-bottom:8px; background:#fcfdff; }
  .plp-gen-cats { display:flex; flex-wrap:wrap; gap:6px 14px; margin:6px 0; }
  .plp-gen-cats label { font-size:12px; display:inline-flex; align-items:center; gap:4px; }
  .plp-gen-cats input { width:48px; padding:2px 4px; border:1px solid #c9d2db; border-radius:4px; font-size:12px; }
  .plp-gen-row { display:flex; align-items:center; gap:10px; flex-wrap:wrap; font-size:13px; }
  .plp-gen-row input[type=number] { width:64px; padding:3px 5px; border:1px solid #c9d2db; border-radius:4px; }
  .plp-gen-row input[type=text] { padding:3px 6px; border:1px solid #c9d2db; border-radius:4px; }
  .plp-gen-avail { color:#667; font-size:11px; }
  .plp-gen-sumwarn { color:#c62828; font-size:12px; font-weight:600; border:1px solid #c62828; border-radius:4px; padding:1px 6px; background:#fdecea; }
  .hidden { display:none; }
  `;
  const style = document.createElement('style');
  style.id = 'plp-styles';
  style.textContent = css;
  document.head.appendChild(style);
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k === 'html') node.innerHTML = v;
    else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined && v !== false) node.setAttribute(k, v === true ? '' : v);
  }
  for (const c of [].concat(children)) if (c) node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  return node;
}

export function mountProblemListPanel(opts) {
  const { container, getContext, devBase = '', startOpen = false, title = 'Problem Lists', onChange = null,
    generateFluency = null } = opts;
  injectStyles();
  const state = { lists: [], folder: null, user: null, found: false, error: null, timers: new Map() };

  const toggle = el('span', { class: 'plp-toggle', text: '▶' });
  const sub = el('span', { class: 'plp-sub' });
  const header = el('div', { class: 'plp-header', role: 'button', tabindex: '0' }, [toggle, el('h3', {}, [title + ' ', sub])]);
  const status = el('span', { class: 'plp-status' });
  const newBtn = el('button', { class: 'plp-btn', 'data-plp': 'new', type: 'button', text: '+ Manual list' });
  const genCatBtn = el('button', { class: 'plp-btn', 'data-plp': 'gen-cat', type: 'button', text: 'Generate by category' });
  const genFluBtn = el('button', { class: 'plp-btn', 'data-plp': 'gen-flu', type: 'button', text: 'Generate by fluency' });
  if (!generateFluency) genFluBtn.classList.add('hidden');   // host didn't provide a fluency source
  const toolbar = el('div', { class: 'plp-toolbar' }, [newBtn, genCatBtn, genFluBtn, status]);
  const generator = buildGenerator();
  const note = el('div', { class: 'plp-note hidden' });
  const cards = el('div', { class: 'plp-cards', 'data-plp': 'cards' });
  const body = el('div', { class: 'plp-body' }, [toolbar, generator.root, note, cards]);
  const module = el('div', { class: 'plp-module' + (startOpen ? ' plp-open' : '') }, [header, body]);
  container.appendChild(module);

  function setOpen(open) {
    module.classList.toggle('plp-open', open);
    if (open) refresh();   // load when first opened so the header count is fresh
  }
  header.addEventListener('click', () => setOpen(!module.classList.contains('plp-open')));
  header.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setOpen(!module.classList.contains('plp-open')); } });
  if (startOpen) refresh();   // opened by default — load now so the lists show without a click

  newBtn.addEventListener('click', () => mutate({ action: 'create', listName: 'Manual list' }));
  genCatBtn.addEventListener('click', () => generator.toggle('category'));
  genFluBtn.addEventListener('click', () => generator.toggle('fluency'));

  async function api(payload) {
    const ctx = getContext ? getContext() : { folder: state.folder, user: state.user };
    if (!ctx || !ctx.folder || !ctx.user) return { ok: false, error: 'no-context' };
    const r = await fetch(`${devBase}/api/problem-lists`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      // ctx.file targets the exact file selected by either the analysis or anchor page.
      body: JSON.stringify({ folder: ctx.folder, user: ctx.user, file: ctx.file, ...payload }),
    });
    return r.json();
  }
  // A structural mutation (create/delete/reorder/retain/generate): apply, then re-render.
  async function mutate(payload, statusEl = status) {
    statusEl.textContent = 'Saving…';
    let j;
    try { j = await api(payload); } catch (e) { statusEl.textContent = `Save failed: ${e.message}`; return null; }
    if (!j.ok) { statusEl.textContent = j.message || `Save failed: ${j.error || 'unknown error'}`; return j; }
    state.lists = j.problemLists || [];
    state.found = true;
    statusEl.textContent = `Saved · ${state.lists.length} list${state.lists.length === 1 ? '' : 's'}.`;
    render();
    notifyChange();
    return j;
  }
  // Create a generated list, then (if atFront) move it to position #1 so it runs next.
  // retain=true keeps it after use (editor default); false removes it once run (Fluency feast).
  async function addGeneratedList(text, listName, atFront, statusEl, retain = true) {
    const beforeIds = new Set(state.lists.map((l) => l.problem_list_id));
    const j = await mutate({ action: 'create', listName, text, retain }, statusEl);
    if (!j || !j.ok) return false;
    if (atFront) {
      const created = state.lists.find((l) => !beforeIds.has(l.problem_list_id));
      if (created) {
        const rest = state.lists.filter((l) => l.problem_list_id !== created.problem_list_id).map((l) => l.problem_list_id);
        await mutate({ action: 'reorder', order: [created.problem_list_id, ...rest] }, statusEl);
      }
    }
    return true;
  }
  // Let the host page react to list changes (e.g. enable/disable the anchor "Use internal" option).
  function notifyChange() { if (onChange) { try { onChange(state.lists, getContext ? getContext() : null); } catch { /* ignore */ } } }

  async function refresh() {
    const ctx = getContext ? getContext() : null;
    state.folder = ctx && ctx.folder;
    state.user = ctx && ctx.user;
    state.file = ctx && ctx.file;
    if (!state.folder || !state.user) { state.found = false; state.error = 'no-context'; render(); return; }
    try {
      const fileQ = state.file ? `&file=${encodeURIComponent(state.file)}` : '';
      const r = await fetch(`${devBase}/api/problem-lists?folder=${encodeURIComponent(state.folder)}&user=${encodeURIComponent(state.user)}${fileQ}`);
      const j = await r.json();
      state.error = j.ok ? null : (j.error || 'error');
      state.found = !!j.found;
      state.lists = j.problemLists || [];
    } catch (e) {
      state.error = 'unreachable';
      state.lists = [];
      state.found = false;
    }
    render();
  }

  function render() {
    sub.textContent = state.lists.length ? `(${state.lists.length})` : '';
    cards.innerHTML = '';
    const ctx = getContext ? getContext() : null;
    const haveCtx = !!(ctx && ctx.folder && ctx.user);
    const canEdit = haveCtx && state.error == null && state.found;
    newBtn.disabled = !canEdit;
    genCatBtn.disabled = !canEdit;
    genFluBtn.disabled = !canEdit;
    note.classList.add('hidden');
    if (!haveCtx) return showNote('Pick a learner (and source folder) to edit their problem lists.');
    if (state.error === 'unreachable') return showNote('Dev server not reachable — problem-list editing needs tools/dev_server.py running.');
    if (state.error && state.error !== 'no-context') return showNote(`Could not load lists: ${state.error}`);
    if (!state.found) return showNote(`No file yet for "${state.user}" in "${state.folder}". Run a quiz (or Start New) to create one, then add lists.`);
    if (!state.lists.length) showNote('No problem lists yet — use “+ Manual list”, “Generate by category”, or “Generate by fluency”.');
    state.lists.forEach((list, i) => cards.appendChild(buildCard(list, i)));
    // Open to show each list in full by default (resizable down from there).
    cards.querySelectorAll('.plp-text').forEach(autosize);
  }
  // Grow a card's textarea to fit its content so the whole list shows without scrolling.
  function autosize(ta) { ta.style.height = 'auto'; ta.style.height = Math.max(ta.scrollHeight + 2, 150) + 'px'; }
  function showNote(text) { note.textContent = text; note.classList.remove('hidden'); }

  function buildCard(list, index) {
    const id = list.problem_list_id;
    const order = el('span', { class: 'plp-order', text: `#${list.list_order}` });
    const name = el('input', { class: 'plp-name', 'data-plp': 'name', value: list.list_name || '', title: 'List name' });
    const left = el('button', { class: 'plp-iconbtn', 'data-plp': 'left', type: 'button', text: '◀', title: 'Move earlier' });
    const right = el('button', { class: 'plp-iconbtn', 'data-plp': 'right', type: 'button', text: '▶', title: 'Move later' });
    const del = el('button', { class: 'plp-iconbtn', 'data-plp': 'delete', type: 'button', text: '🗑', title: 'Delete list' });
    left.disabled = index === 0;
    right.disabled = index === state.lists.length - 1;
    const top = el('div', { class: 'plp-card-top' }, [order, name, left, right, del]);
    const retain = el('input', { type: 'checkbox', 'data-plp': 'retain' });
    retain.checked = !!Number(list.retain);
    const used = list.times_used ? ` · used ${list.times_used}×` : '';
    const meta = el('div', { class: 'plp-meta' }, [
      el('label', {}, [retain, ' keep after use']),
      el('span', { text: `${list.item_count != null ? list.item_count : (list.items ? list.items.length : 0)} probs${used}` }),
    ]);
    const text = el('textarea', { class: 'plp-text', 'data-plp': 'text', spellcheck: 'false' });
    text.value = itemsToText(list.items || []);
    const cardStatus = el('div', { class: 'plp-card-status' });
    const card = el('div', { class: 'plp-card', 'data-plp': 'card', 'data-id': String(id) }, [top, meta, text, cardStatus]);

    // Auto-save: textarea (debounced + flush on blur), name (debounced), retain/reorder/delete (immediate).
    const scheduleItems = () => debounce(id, () => saveItems(id, text.value, cardStatus));
    text.addEventListener('input', () => { autosize(text); scheduleItems(); });
    text.addEventListener('blur', () => { flush(id); saveItems(id, text.value, cardStatus); });
    name.addEventListener('input', () => debounce('name-' + id, () => mutate({ action: 'rename', problemListId: id, listName: name.value }, cardStatus)));
    retain.addEventListener('change', () => mutate({ action: 'set-retain', problemListId: id, retain: retain.checked }, cardStatus));
    del.addEventListener('click', () => { if (window.confirm(`Delete list "${list.list_name}"? This removes it from the file.`)) mutate({ action: 'delete', problemListId: id }, status); });
    left.addEventListener('click', () => move(index, -1));
    right.addEventListener('click', () => move(index, 1));
    return card;
  }

  async function saveItems(id, textValue, cardStatus) {
    cardStatus.className = 'plp-card-status';
    cardStatus.textContent = 'Saving…';
    let j;
    try { j = await api({ action: 'save-items', problemListId: id, text: textValue }); }
    catch (e) { cardStatus.className = 'plp-card-status err'; cardStatus.textContent = `Save failed: ${e.message}`; return; }
    if (!j.ok) { cardStatus.className = 'plp-card-status err'; cardStatus.textContent = j.error === 'unknown-action' ? 'Save failed.' : `Couldn’t save: ${j.error}`; return; }
    state.lists = j.problemLists || state.lists;   // keep model fresh WITHOUT re-rendering (preserve focus)
    const m = state.lists.find((l) => l.problem_list_id === id);
    cardStatus.className = 'plp-card-status ok';
    cardStatus.textContent = `Saved ✓ (${m ? m.item_count : '?'} problems)`;
    notifyChange();
  }
  function move(index, delta) {
    const target = index + delta;
    if (target < 0 || target >= state.lists.length) return;
    const order = state.lists.map((l) => l.problem_list_id);
    [order[index], order[target]] = [order[target], order[index]];
    mutate({ action: 'reorder', order });
  }
  function debounce(key, fn) {
    clearTimeout(state.timers.get(key));
    state.timers.set(key, setTimeout(fn, SAVE_DEBOUNCE_MS));
  }
  function flush(id) { clearTimeout(state.timers.get(id)); state.timers.delete(id); }

  // ----- generator drawer: "Generate by category" + "Generate by fluency" share one
  // drawer (mode-switched by the toolbar buttons) and one "Add generated problem list"
  // action. Adds the result as a new list named "Category"/"Fluency", at the front when
  // "Add ends next" is checked (else appended). -----
  function buildGenerator() {
    // by-category form (addition taxonomy %s)
    const catCount = el('input', { type: 'number', 'data-plp': 'gen-count', value: '20', min: '1', max: '500' });
    const catInputs = GENERATOR_CATEGORIES.map((c) => {
      const input = el('input', { type: 'number', 'data-plp': 'gen-weight', 'data-cat': c.id, value: String(DEFAULT_WEIGHTS[c.id] ?? 0), min: '0' });
      return { c, input, label: el('label', {}, [c.label + ' ', input, ' %']) };
    });
    const catForm = el('div', { 'data-plp': 'gen-cat-form' }, [
      el('div', { html: '<strong>Generate by category</strong> — size + addition-category mix (relative %).' }),
      el('div', { class: 'plp-gen-cats' }, catInputs.map((x) => x.label)),
      el('div', { class: 'plp-gen-row' }, [el('label', {}, ['Count ', catCount])]),
    ]);

    // by-fluency form (fluency-status %s drawn from this learner's history)
    const STATUS_OF = { fluent: 'green', almost: 'yellow', 'needs-practice': 'red', incorrect: 'gray', missing: 'nodata' };
    const fluCount = el('input', { type: 'number', 'data-plp': 'genf-count', value: '20', min: '1', max: '500' });
    const fluPct = (id, label, val) => {
      const input = el('input', { type: 'number', 'data-plp': 'genf-pct', 'data-flu': id, value: String(val), min: '0', max: '100' });
      const avail = el('span', { class: 'plp-gen-avail', 'data-plp': `genf-avail-${id}` });   // "(n)" facts in this category
      return { id, input, avail, label: el('label', {}, [label + ' ', input, ' % ', avail]) };
    };
    const fluInputs = [
      fluPct('fluent', 'Fluent', 0), fluPct('almost', 'Almost', 10), fluPct('needs-practice', 'Needs practice', 10),
      fluPct('incorrect', 'Incorrect', 40), fluPct('missing', 'Missing', 40),
    ];
    const fluSumWarn = el('span', { class: 'plp-gen-sumwarn hidden', 'data-plp': 'genf-sumwarn' });
    const saveFeastBtn = el('button', { class: 'plp-btn', 'data-plp': 'genf-save-preset', type: 'button', text: 'Save as feast preset' });
    const feastStatus = el('span', { class: 'plp-status', 'data-plp': 'genf-preset-status' });
    const fluSessions = el('select', { 'data-plp': 'genf-sessions' }, [
      el('option', { value: 'all', text: 'All sessions' }),
      el('option', { value: 'recentN', text: 'Last N sessions' }),
      el('option', { value: 'sinceDate', text: 'Since date' }),
    ]);
    const fluN = el('input', { type: 'number', 'data-plp': 'genf-n', value: '3', min: '1', max: '99' });
    const fluSince = el('input', { type: 'date', 'data-plp': 'genf-since' });
    const fluNWrap = el('label', { class: 'hidden' }, ['N ', fluN]);
    const fluSinceWrap = el('label', { class: 'hidden' }, ['Since ', fluSince]);
    fluSessions.addEventListener('change', () => {
      fluNWrap.classList.toggle('hidden', fluSessions.value !== 'recentN');
      fluSinceWrap.classList.toggle('hidden', fluSessions.value !== 'sinceDate');
    });
    const fluForm = el('div', { 'data-plp': 'gen-flu-form', class: 'hidden' }, [
      el('div', { html: '<strong>Generate by fluency</strong> — size + fluency-category mix from this learner’s history. The (n) after each is how many facts are in that category (flagged answers excluded). The five must total 100%.' }),
      el('div', { class: 'plp-gen-cats' }, fluInputs.map((x) => x.label)),
      el('div', { class: 'plp-gen-row' }, [el('label', {}, ['Count ', fluCount]), el('label', {}, ['Sessions ', fluSessions]), fluNWrap, fluSinceWrap, fluSumWarn]),
      el('div', { class: 'plp-gen-row', style: 'margin-top:6px' }, [
        saveFeastBtn,
        el('span', { class: 'plp-gen-avail', text: '— the kid’s one-click "Fluency feast" uses this' }),
        feastStatus,
      ]),
    ]);

    // shared footer: position + add
    const posSelect = el('select', { 'data-plp': 'gen-position', title: 'Where the generated list goes in the queue' }, [
      el('option', { value: 'first', selected: true, text: 'Add as first' }),
      el('option', { value: 'end', text: 'Add to end' }),
    ]);
    const addBtn = el('button', { class: 'plp-btn', 'data-plp': 'gen-add', type: 'button', text: 'Add generated problem list' });
    const genStatus = el('span', { class: 'plp-status', 'data-plp': 'gen-status' });
    const footer = el('div', { class: 'plp-gen-row', style: 'margin-top:8px' }, [
      el('label', {}, ['Position ', posSelect]),
      addBtn, genStatus,
    ]);

    let mode = 'category';
    const root = el('div', { class: 'plp-generator hidden' }, [catForm, fluForm, footer]);

    function currentSessionSelection() {
      return fluSessions.value === 'recentN' ? { mode: 'recentN', n: Number(fluN.value) || 1 }
        : fluSessions.value === 'sinceDate' ? { mode: 'sinceDate', since: fluSince.value || '' }
          : { mode: 'all' };
    }
    function fluencySum() { return fluInputs.reduce((s, x) => s + (Number(x.input.value) || 0), 0); }
    // The five fluency %s must total 100; otherwise warn + block Add (fluency mode only).
    function validateFluency() {
      const sum = fluencySum();
      const ok = sum === 100;
      fluSumWarn.textContent = ok ? '' : `Must total 100% (now ${sum}%)`;
      fluSumWarn.classList.toggle('hidden', ok);
      addBtn.disabled = (mode === 'fluency') && !ok;
      saveFeastBtn.disabled = !ok;   // the preset save needs a valid 100% mix too
    }
    // Save the current form (count / sessions / mix) as this file's Fluency-feast preset.
    // silent=true is the first-open auto-write (no status chatter).
    async function saveFeastPreset(silent) {
      const ctx = getContext ? getContext() : null;
      if (!ctx || !ctx.folder || !ctx.user) { if (!silent) feastStatus.textContent = 'Pick a learner first.'; return; }
      if (fluencySum() !== 100) { if (!silent) validateFluency(); return; }
      const mix = {};
      for (const { id, input } of fluInputs) mix[id] = Number(input.value) || 0;
      if (!silent) feastStatus.textContent = 'Saving…';
      let j;
      try {
        const r = await fetch(`${devBase}/api/fluency-feast-config`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ folder: ctx.folder, user: ctx.user, file: ctx.file,
            count: Number(fluCount.value) || 0, session: currentSessionSelection(), mix }),
        });
        j = await r.json();
      } catch (e) { if (!silent) feastStatus.textContent = `Save failed: ${e.message}`; return; }
      if (!silent) feastStatus.textContent = (j && j.ok) ? 'Saved feast preset ✓' : `Save failed: ${(j && (j.message || j.error)) || 'error'}`;
    }
    saveFeastBtn.addEventListener('click', () => saveFeastPreset(false));
    // Put a saved preset's values into the form.
    function applyPresetToForm(preset) {
      if (!preset) return;
      if (preset.count) fluCount.value = String(preset.count);
      const s = preset.session || {};
      if (s.mode) {
        fluSessions.value = s.mode;
        fluNWrap.classList.toggle('hidden', s.mode !== 'recentN');
        fluSinceWrap.classList.toggle('hidden', s.mode !== 'sinceDate');
        if (s.n) fluN.value = String(s.n);
        if (s.since) fluSince.value = s.since;
      }
      if (preset.mix) for (const { id, input } of fluInputs) if (preset.mix[id] != null) input.value = String(preset.mix[id]);
      validateFluency();
    }
    // On opening the by-fluency form, prefill from the file's saved preset (so generation uses
    // the in-file parameters); the first time (none saved) write the current defaults to the file.
    let feastLoadedFor = null;
    async function loadFeastPreset() {
      const ctx = getContext ? getContext() : null;
      if (!ctx || !ctx.folder || !ctx.user) return;
      const key = `${ctx.folder}|${ctx.user}|${ctx.file || ''}`;
      if (feastLoadedFor === key) return;        // already synced this file
      feastLoadedFor = key;
      let preset = null;
      try {
        const fileQ = ctx.file ? `&file=${encodeURIComponent(ctx.file)}` : '';
        const j = await (await fetch(`${devBase}/api/fluency-feast-config?folder=${encodeURIComponent(ctx.folder)}&user=${encodeURIComponent(ctx.user)}${fileQ}`)).json();
        preset = (j && j.ok && j.fluencyFeast) ? j.fluencyFeast : null;
      } catch (e) { feastLoadedFor = null; return; }   // transient failure — allow a later retry
      if (preset && preset.count) { applyPresetToForm(preset); updateFluencyCounts(); }
      else { saveFeastPreset(true); }            // first open: persist the defaults now in the form
    }
    // Show how many facts sit in each fluency category (pool sizes from a no-op generate).
    async function updateFluencyCounts() {
      if (mode !== 'fluency' || !generateFluency) return;
      let res = null;
      try { res = await generateFluency({ numProblems: 0, distribution: {}, sessionSelection: currentSessionSelection() }); } catch (e) { res = null; }
      const pools = (res && res.poolSizes) || {};
      for (const { id, avail } of fluInputs) {
        const n = pools[STATUS_OF[id]];
        avail.textContent = (n == null) ? '' : `(${n})`;
      }
    }
    // Entering 100 in one category zeroes the rest; any edit re-validates the total.
    fluInputs.forEach(({ input }) => input.addEventListener('input', () => {
      if ((Number(input.value) || 0) === 100) {
        for (const other of fluInputs) if (other.input !== input) other.input.value = '0';
      }
      validateFluency();
    }));
    fluSessions.addEventListener('change', updateFluencyCounts);
    fluN.addEventListener('input', updateFluencyCounts);
    fluSince.addEventListener('input', updateFluencyCounts);

    function toggle(which) {
      const visible = !root.classList.contains('hidden');
      if (visible && mode === which) { root.classList.add('hidden'); genCatBtn.classList.remove('plp-active'); genFluBtn.classList.remove('plp-active'); return; }
      mode = which;
      root.classList.remove('hidden');
      catForm.classList.toggle('hidden', which !== 'category');
      fluForm.classList.toggle('hidden', which !== 'fluency');
      genCatBtn.classList.toggle('plp-active', which === 'category');
      genFluBtn.classList.toggle('plp-active', which === 'fluency');
      addBtn.disabled = false;
      if (which === 'fluency') { validateFluency(); updateFluencyCounts(); loadFeastPreset(); }
    }

    addBtn.addEventListener('click', async () => {
      if (mode === 'category') {
        const weights = {};
        for (const { c, input } of catInputs) weights[c.id] = Number(input.value) || 0;
        const items = generateMix({ count: Number(catCount.value) || 0, weights });
        if (!items.length) { genStatus.textContent = 'Set a count and at least one category %.'; return; }
        await addGeneratedList(itemsToText(items), 'Category', posSelect.value === 'first', genStatus);
        return;
      }
      // fluency mode
      if (!generateFluency) { genStatus.textContent = 'Fluency generation is not available here.'; return; }
      if (fluencySum() !== 100) { validateFluency(); return; }   // guard (button is also disabled)
      const distribution = {};
      for (const { id, input } of fluInputs) distribution[id] = Number(input.value) || 0;
      let res;
      genStatus.textContent = 'Generating…';
      try { res = await generateFluency({ numProblems: Number(fluCount.value) || 0, distribution, sessionSelection: currentSessionSelection() }); }
      catch (e) { genStatus.textContent = `Could not generate: ${e.message}`; return; }
      if (!res) { genStatus.textContent = 'Load this learner’s data first.'; return; }
      if (!res.problems || !res.problems.length) { genStatus.textContent = (res.warnings && res.warnings[0]) || 'No problems for that mix.'; return; }
      await addGeneratedList(res.problems.join('\n'), 'Fluency', posSelect.value === 'first', genStatus);
      if (res.warnings && res.warnings.length) genStatus.textContent += ' · ' + res.warnings.join(' ');
    });

    return { root, toggle };
  }

  // Programmatic create (e.g. anchor's "Fluency feast"): add a generated list, optionally at the
  // front and without retain, then refresh. Returns true on success.
  async function addGenerated(text, listName, atFront, retain) {
    return addGeneratedList(text, listName, !!atFront, status, retain);
  }
  const apiObj = { refresh, setOpen, element: module, addGenerated };
  container.__plp = apiObj;
  return apiObj;
}
