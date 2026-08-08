import assert from 'node:assert/strict';
import test from 'node:test';
import {
  DEMOS,
  buttonParamsMapping,
  getDemoBySlug,
  getDemoList,
} from '../src/lib/demo-config.js';
import { validateAndSanitizeInput } from '../src/lib/validation.js';

test('demo list includes all four public demos', () => {
  assert.equal(getDemoList().length, 4);
  assert.ok(getDemoBySlug('deutsch'));
  assert.ok(getDemoBySlug('fda-town-halls'));
  assert.ok(getDemoBySlug('pv-evacuation'));
  assert.ok(getDemoBySlug('sovereign-child'));
});

test('deutsch demo preserves Webflow vector index and date range', () => {
  const demo = DEMOS.deutsch;
  assert.equal(demo.vector_index_name, 'deutsch-transcript-qrag-95f-20250923');
  assert.equal(demo.route_dict_name, 'ROUTES_DICT_DEUTSCH_M1');
  assert.equal(demo.dateRange.min, '1995-01-01');
  assert.equal(demo.dateRange.max, '2025-09-16');
});

test('button params mapping keys match submit button ids', () => {
  for (const demo of getDemoList()) {
    assert.ok(buttonParamsMapping[demo.submitButtonId]);
    assert.equal(buttonParamsMapping[demo.submitButtonId].vector_index_name, demo.vector_index_name);
  }
});

test('validateAndSanitizeInput rejects suspicious script tags', () => {
  const result = validateAndSanitizeInput('<script>alert(1)</script>', null, 'Question');
  assert.equal(result.success, false);
  assert.equal(result.suspicious, true);
});

test('validateAndSanitizeInput accepts normal questions', () => {
  const result = validateAndSanitizeInput('What is optimism?', null, 'Question');
  assert.equal(result.success, true);
  assert.equal(result.value, 'What is optimism?');
});
