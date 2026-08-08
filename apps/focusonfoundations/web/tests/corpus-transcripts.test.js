import test from 'node:test';
import assert from 'node:assert/strict';
import {
  CORPUS_MANIFESTS,
  getCorpusByKey,
  getCorpusItem,
  getItemLinks,
  getAllCorpusItems,
  getRedirectStubs,
} from '../src/lib/corpus-config.js';
import { applyToggleLevel, wireTranscriptViewer } from '../src/lib/transcript-viewer.js';

class FakeButton {
  constructor(textContent) {
    this.textContent = textContent;
    this.listeners = {};
    this.style = {};
  }
  addEventListener(event, callback) {
    this.listeners[event] = callback;
  }
  click() {
    this.listeners.click?.();
  }
}
class FakeControlPanel {
  constructor() {
    this.style = {};
  }
  querySelectorAll() {
    return [];
  }
}
class FakeContainer {
  constructor() {
    this._innerHTML = '';
    this.style = {};
    this.button = null;
    this.controlPanel = null;
  }
  set innerHTML(value) {
    this._innerHTML = value;
    const buttonMatch = value.match(/<button[^>]*id="toggleDocButton"[^>]*>(.*?)<\/button>/s);
    this.button = buttonMatch ? new FakeButton(buttonMatch[1].trim()) : null;
    this.controlPanel = value.includes('control-panel') ? new FakeControlPanel() : null;
  }
  get innerHTML() {
    return this._innerHTML;
  }
  querySelector(selector) {
    if (selector === '#toggleDocButton') return this.button;
    if (selector === '.control-panel') return this.controlPanel;
    if (selector === 'h4') return null;
    return null;
  }
  querySelectorAll() {
    return [];
  }
}

test('corpus manifests have expected item counts', () => {
  assert.equal(CORPUS_MANIFESTS.deutsch.length, 95);
  assert.equal(CORPUS_MANIFESTS['fda-town-halls'].length, 100);
  assert.equal(CORPUS_MANIFESTS['sovereign-child'].length, 8);
  assert.equal(CORPUS_MANIFESTS['pv-evacuation'].length, 3);
});

test('corpus manifest items include required S3 or markdown fields', () => {
  for (const item of getAllCorpusItems()) {
    assert.ok(item.slug);
    assert.ok(item.newPath.startsWith('/transcripts/'));
    assert.ok(item.oldPath.startsWith('/'));
    if (item.viewerVariant === 'van11y') {
      assert.ok(item.markdownFile, `missing markdownFile for ${item.slug}`);
    } else {
      assert.ok(item.transcriptHtmlUrl.includes('fofpublic'), item.slug);
      assert.ok(item.qaHtmlUrl.includes('fofpublic'), item.slug);
    }
  }
});

test('redirect stubs cover all legacy item paths plus index pages', () => {
  const stubs = getRedirectStubs();
  const itemCount = getAllCorpusItems().length;
  assert.equal(stubs.length, itemCount + 3);
  const oldPaths = new Set(stubs.map((s) => s.oldPath));
  for (const item of getAllCorpusItems()) {
    assert.ok(oldPaths.has(item.oldPath), `missing redirect for ${item.oldPath}`);
  }
  assert.ok(oldPaths.has('/deutsch-interviews-index'));
  assert.ok(oldPaths.has('/fl-fda-vth-index'));
  assert.ok(oldPaths.has('/sov-child-transcripts-index'));
});

test('Deutsch index model includes transcript, YouTube, and Spotify links when available', () => {
  const corpus = getCorpusByKey('deutsch');
  const item = CORPUS_MANIFESTS.deutsch.find((entry) => entry.youtubeUrl && entry.spotifyUrl);
  assert.ok(item, 'expected at least one Deutsch item with both YouTube and Spotify links');
  const links = getItemLinks(corpus, item);
  assert.deepEqual(links.map((link) => link.label), ['Transcript and Q&A', 'YouTube', 'Spotify']);
  assert.equal(links[0].href, item.newPath);
});

test('Deutsch transcript viewer loads transcript and folded Q&A HTML', async () => {
  const item = getCorpusItem('deutsch', '2018-03-14-dirac-prize-talk');
  const transcriptHtml = `
    <header>
      <h3>2018-03-14_Dirac Prize Talk_vrb-topstars.md</h3>
      <button id="toggleDocButton">View Q&A</button>
    </header>
    <h3 id="transcript">transcript</h3>
    <p><strong>David Deutsch:</strong> The laws of physics permit universality.</p>
  `;
  const qaHtml = `
    <header>
      <h3>Extracted Question and Answer</h3>
      <button id="toggleDocButton">View Transcript</button>
    </header>
    <details>
      <summary>QA Block 1-5</summary>
      <p>QUESTION 1: What is the relationship between universal Turing machine and the laws of physics?</p>
      <p>ANSWER: It is about physical universality.</p>
    </details>
  `;
  const originalFetch = global.fetch;
  global.fetch = async (url) => ({
    ok: true,
    text: async () => (url === item.transcriptHtmlUrl ? transcriptHtml : qaHtml),
  });
  const transcriptContainer = new FakeContainer();
  const qaContainer = new FakeContainer();
  qaContainer.style.display = 'none';
  const root = {
    querySelector(selector) {
      if (selector === '[data-transcript-container]') return transcriptContainer;
      if (selector === '[data-qa-container]') return qaContainer;
      return null;
    },
  };
  try {
    await wireTranscriptViewer(root, {
      transcriptUrl: item.transcriptHtmlUrl,
      qaUrl: item.qaHtmlUrl,
      variant: 'generic',
    });
    assert.match(transcriptContainer.innerHTML, /2018-03-14_Dirac Prize Talk_vrb-topstars\.md/);
    assert.match(transcriptContainer.innerHTML, /The laws of physics permit universality/);
    assert.equal(transcriptContainer.querySelector('#toggleDocButton').textContent, 'View Q&A');
    transcriptContainer.querySelector('#toggleDocButton').click();
    assert.equal(transcriptContainer.style.display, 'none');
    assert.equal(qaContainer.style.display, 'block');
    assert.match(qaContainer.innerHTML, /<details>/);
    assert.match(qaContainer.innerHTML, /QUESTION 1:/);
  } finally {
    global.fetch = originalFetch;
  }
});

test('applyToggleLevel opens and collapses flat documents', () => {
  const details = [
    { open: false, setAttribute() { this.open = true; }, removeAttribute() { this.open = false; } },
    { open: false, setAttribute() { this.open = true; }, removeAttribute() { this.open = false; } },
  ];
  const root = {
    querySelectorAll(selector) {
      if (selector === 'details') return details;
      if (selector === 'details[open]') return details.filter((d) => d.open);
      return [];
    },
  };
  applyToggleLevel(root, 'all', 'generic', false);
  assert.ok(details.every((d) => d.open));
  applyToggleLevel(root, 'collapse', 'generic', false);
  assert.ok(details.every((d) => !d.open));
});

test('applyToggleLevel handles nested FDA-style sections', () => {
  function makeDetail(parent) {
    return {
      tagName: 'DETAILS',
      parentElement: parent,
      open: false,
      setAttribute() { this.open = true; },
      removeAttribute() { this.open = false; },
      hasAttribute(name) { return name === 'open' && this.open; },
    };
  }
  const answer = makeDetail(null);
  const question = makeDetail(null);
  const section = makeDetail(null);
  const wrapper = { tagName: 'DIV' };
  section.parentElement = wrapper;
  question.parentElement = section;
  answer.parentElement = question;
  const root = {
    querySelectorAll(selector) {
      if (selector === 'details') return [section, question, answer];
      return [];
    },
  };
  applyToggleLevel(root, 'questions', 'fda', true);
  assert.ok(section.open);
  assert.ok(!question.open);
  assert.ok(!answer.open);
  applyToggleLevel(root, 'all', 'fda', true);
  assert.ok(section.open && question.open && answer.open);
});
