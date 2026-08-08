export const PRIVACY_CONSENT_VERSION_DATE = '2024-12-17';
export const HASH_STORE_LOG_FILE_KEY = 'pii_user_hash_log_2024-12-17.csv';
export const JWT_STORAGE_KEY = 'jwtToken';
export const SHOW_EMAIL_LIST_SIGNUP = true;

export const DEMOS = {
  deutsch: {
    id: 'deutsch-demo_qrag',
    slug: 'deutsch',
    title: 'Deutsch Interviews',
    description: 'QRAG demo over David Deutsch interview corpus — explore ideas from decades of interviews.',
    submitButtonId: 'submitButton_deutsch-demo_qrag',
    containerId: 'container_deutsch-demo_qrag',
    displayType: 'quoted-qa-then-ai-answer',
    ragFunction: 'qragRouting, qragLLM',
    vector_index_name: 'deutsch-transcript-qrag-95f-20250923',
    route_dict_name: 'ROUTES_DICT_DEUTSCH_M1',
    large_context_filename: 'deutsch_large_context_v1.md',
    botTitle: 'QRAG demo over David Deutsch Interview Corpus',
    dateRange: { min: '1995-01-01', max: '2025-09-16', show: true },
    transcriptIndexPath: '/transcripts/deutsch/',
  },
  fdaTownHalls: {
    id: 'fda-townhalls-demo_qrag',
    slug: 'fda-town-halls',
    title: 'FDA COVID-19 Town Halls',
    description: 'QRAG demo over 100 FDA COVID-19 Diagnostics Virtual Town Halls.',
    submitButtonId: 'submitButton_fda-townhalls-demo_qrag',
    containerId: 'container_fda-townhalls-demo_qrag',
    displayType: 'quoted-qa-then-ai-answer',
    ragFunction: 'qragRouting, qragLLM',
    vector_index_name: 'fda-townhalls-qrag-100f-20250114',
    route_dict_name: 'ROUTES_DICT_FDA_TOWNHALLS_M1',
    large_context_filename: null,
    botTitle: 'QRAG demo over 100 FDA COVID-19 Diagnostics Virtual Town Halls',
    dateRange: { min: '2020-03-02', max: '2023-04-26', show: true },
    legacyPaths: ['/fda-town-halls-qrag-demo/', '/fda-town-halls-qrag-demo'],
    transcriptIndexPath: '/transcripts/fda-town-halls/',
  },
  pvEvacuation: {
    id: 'pv-evac-demo_qrag',
    slug: 'pv-evacuation',
    title: 'PV School Evacuation',
    description: 'QRAG demo over PVSD Evacuation Preparedness Meeting transcripts.',
    submitButtonId: 'submitButton_pv-evac-demo_qrag',
    containerId: 'container_pv-evac-demo_qrag',
    displayType: 'quoted-qa-then-ai-answer',
    ragFunction: 'qragRouting, qragLLM',
    vector_index_name: 'pv-evac-qrag-3f-20250202',
    route_dict_name: 'ROUTES_DICT_PV_EVAC_M1',
    large_context_filename: null,
    botTitle: 'QRAG demo over PVSD Evacuation Preparedness Meeting',
    dateRange: { min: '2023-09-20', max: '2024-10-23', show: true },
    transcriptIndexPath: '/transcripts/pv-evacuation/',
  },
  sovereignChild: {
    id: 'sovereign-child-demo_qrag',
    slug: 'sovereign-child',
    title: 'The Sovereign Child',
    description: 'QRAG demo over The Sovereign Child book by Dr Aaron Stupple.',
    submitButtonId: 'submitButton_sovereign-child-demo_qrag',
    containerId: 'container_sovereign-child-demo_qrag',
    displayType: 'quoted-qa-then-ai-answer',
    ragFunction: 'qragRouting, qragLLM',
    vector_index_name: 'sovereign-child-qrag-7f-20250805',
    route_dict_name: 'ROUTES_DICT_SOVEREIGN_CHILD_M1',
    large_context_filename: '2025-01-13_Book - The Sovereign Child by Dr Aaron Stupple.md',
    botTitle: 'QRAG demo over The Sovereign Child book',
    dateRange: { min: '2025-01-13', max: '2025-08-26', show: true },
    transcriptIndexPath: '/transcripts/sovereign-child/',
  },
};

export const buttonParamsMapping = Object.fromEntries(
  Object.values(DEMOS).map((demo) => [demo.submitButtonId, {
    displayType: demo.displayType,
    ragFunction: demo.ragFunction,
    vector_index_name: demo.vector_index_name,
    route_dict_name: demo.route_dict_name,
    large_context_filename: demo.large_context_filename,
    botTitle: demo.botTitle,
  }])
);

export function getDemoBySlug(slug) {
  return Object.values(DEMOS).find((demo) => demo.slug === slug);
}

export function getDemoList() {
  return Object.values(DEMOS);
}
