import deutschManifest from '../corpus/corpus-deutsch.json' with { type: 'json' };
import fdaManifest from '../corpus/corpus-fda-town-halls.json' with { type: 'json' };
import sovereignManifest from '../corpus/corpus-sovereign-child.json' with { type: 'json' };
import pvEvacManifest from '../corpus/corpus-pv-evacuation.json' with { type: 'json' };

export const CORPUS_MANIFESTS = {
  deutsch: deutschManifest,
  'fda-town-halls': fdaManifest,
  'sovereign-child': sovereignManifest,
  'pv-evacuation': pvEvacManifest,
};

export const CORPUS_INDEX_REDIRECTS = {
  'deutsch-interviews-index': '/transcripts/deutsch/',
  'fl-fda-vth-index': '/transcripts/fda-town-halls/',
  'sov-child-transcripts-index': '/transcripts/sovereign-child/',
};

export const CORPORA = {
  deutsch: {
    key: 'deutsch',
    title: 'David Deutsch Interviews',
    indexPath: '/transcripts/deutsch/',
    demoPath: '/demos/deutsch/',
    viewerVariant: 'generic',
    introHtml: '<p>Source transcripts and extracted Q&amp;A for the David Deutsch interview corpus (top-stars subset).</p>',
    linkColumns: [
      { key: 'youtubeUrl', label: 'YouTube' },
      { key: 'spotifyUrl', label: 'Spotify' },
    ],
  },
  'fda-town-halls': {
    key: 'fda-town-halls',
    title: 'FDA COVID-19 Virtual Town Halls',
    indexPath: '/transcripts/fda-town-halls/',
    demoPath: '/demos/fda-town-halls/',
    viewerVariant: 'fda',
    introHtml: '<p>FDA Virtual Town Halls on COVID-19 Test Development — source index. <a href="https://www.fda.gov/medical-devices/coronavirus-covid-19-and-medical-devices/virtual-town-hall-series" target="_blank" rel="noopener">FDA website</a> — scroll down and select &quot;In Vitro Diagnostics&quot;, then scroll down for the COVID-19 Virtual Town Hall Series.</p>',
    linkColumns: [
      { key: 'youtubeUrl', label: 'YouTube' },
      { key: 'fdaPdfUrl', label: 'FDA PDF' },
      { key: 'fdaSlidesUrl', label: 'Slides' },
    ],
  },
  'sovereign-child': {
    key: 'sovereign-child',
    title: 'The Sovereign Child',
    indexPath: '/transcripts/sovereign-child/',
    demoPath: '/demos/sovereign-child/',
    viewerVariant: 'generic',
    introHtml: '<p>Interviews, podcasts, and book source material for <em>The Sovereign Child</em> by Dr Aaron Stupple.</p>',
    linkColumns: [
      { key: 'youtubeUrl', label: 'YouTube' },
      { key: 'spotifyUrl', label: 'Spotify' },
    ],
  },
  'pv-evacuation': {
    key: 'pv-evacuation',
    title: 'PV School Evacuation Preparedness',
    indexPath: '/transcripts/pv-evacuation/',
    demoPath: '/demos/pv-evacuation/',
    viewerVariant: 'van11y',
    introHtml: '<p>PVSD wildfire preparedness parent presentation transcripts (Van11y accordion rendering preserved from the legacy site).</p>',
    linkColumns: [
      { key: 'youtubeUrl', label: 'YouTube' },
      { key: 'presentationUrl', label: 'Presentation' },
    ],
  },
};

export function getCorpusList() {
  return Object.values(CORPORA);
}

export function getCorpusByKey(key) {
  return CORPORA[key] || null;
}

export function getCorpusItems(key) {
  return CORPUS_MANIFESTS[key] || [];
}

export function getCorpusItem(key, slug) {
  return getCorpusItems(key).find((item) => item.slug === slug) || null;
}
export function getItemLinks(corpus, item) {
  return [
    { label: 'Transcript and Q&A', href: item.newPath, external: false },
    ...corpus.linkColumns
      .map((col) => ({ label: col.label, href: item[col.key], external: true }))
      .filter((link) => link.href),
  ];
}

export function getAllCorpusItems() {
  return Object.entries(CORPUS_MANIFESTS).flatMap(([corpusKey, items]) =>
    items.map((item) => ({ ...item, corpusKey }))
  );
}

export function getRedirectStubs() {
  const itemRedirects = getAllCorpusItems().map((item) => ({
    oldPath: item.oldPath,
    newPath: item.newPath,
    prefix: item.oldPathPrefix,
    slug: item.slug,
  }));
  const indexRedirects = Object.entries(CORPUS_INDEX_REDIRECTS).map(([slug, newPath]) => ({
    oldPath: `/${slug}`,
    newPath,
    prefix: 'index',
    slug,
  }));
  return [...indexRedirects, ...itemRedirects];
}
