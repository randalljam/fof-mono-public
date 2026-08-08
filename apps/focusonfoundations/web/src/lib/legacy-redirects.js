import { getAllCorpusItems, CORPUS_INDEX_REDIRECTS } from './corpus-config.js';

const PREFIX_MAP = {
  '/deutsch-transcripts': 'deutsch-transcripts',
  '/fda-c19-townhalls': 'fda-c19-townhalls',
  '/sovereign-child-index': 'sovereign-child-index',
  '/sovereign-child': 'sovereign-child',
  '/pv-evac-docs': 'pv-evac-docs',
};

export function getItemRedirectsForPrefix(oldPathPrefix) {
  return getAllCorpusItems()
    .filter((item) => item.oldPathPrefix === oldPathPrefix)
    .map((item) => ({
      slug: item.slug,
      target: item.newPath,
    }));
}

export function getRedirectRouteId(oldPathPrefix) {
  return PREFIX_MAP[oldPathPrefix];
}

export { CORPUS_INDEX_REDIRECTS };
