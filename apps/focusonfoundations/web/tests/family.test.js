import assert from 'node:assert/strict';
import test from 'node:test';

test('resolveEntitlement prefers app-specific over default, denies when absent', async () => {
  const { resolveEntitlement } = await import('../src/lib/family.js');
  const profile = {
    entitlements: {
      '*': { analysis: false, analysisScope: 'own' },
      'math-quiz': { analysis: true, analysisScope: 'own' },
    },
  };
  assert.equal(resolveEntitlement(profile, 'math-quiz').analysis, true);
  assert.equal(resolveEntitlement(profile, 'logic-gates').analysis, false);
  assert.deepEqual(resolveEntitlement(null, 'anything'), { analysis: false, analysisScope: 'own' });
  assert.deepEqual(resolveEntitlement({}, 'anything'), { analysis: false, analysisScope: 'own' });
});

test('guardian consent text states guardianship, data storage, review, and deletion rights', async () => {
  const { GUARDIAN_CONSENT_TEXT, COPPA_CONSENT_VERSION } = await import('../src/lib/family.js');
  for (const required of ['parent or legal guardian', 'consent', 'learning activity', 'review', 'delete']) {
    assert.ok(GUARDIAN_CONSENT_TEXT.includes(required), `consent text must mention "${required}"`);
  }
  assert.match(COPPA_CONSENT_VERSION, /^\d{4}-\d{2}-\d{2}$/);
});
