import assert from 'node:assert/strict';
import test from 'node:test';
import { generateDropdownContent } from '../src/lib/qrag-ui.js';

const samplePayload = {
  content: {
    route_preamble: 'Route preamble text',
    quoted_qa: 'QUESTION 1\nAnswer excerpt one',
    ai_answer: 'The meaning of life is 42.',
    user_question: 'What is the meaning of life?',
  },
};

test('quoted-qa-then-ai-answer puts AI answer block before excerpts', () => {
  const html = generateDropdownContent(samplePayload, 'quoted-qa-then-ai-answer');
  const aiIndex = html.indexOf('accordion-dropdown-text-ai-answer');
  const preambleIndex = html.indexOf('Route preamble text');
  const excerptIndex = html.indexOf('Answer excerpt one');
  assert.ok(aiIndex !== -1, 'expected AI answer block');
  assert.ok(aiIndex < preambleIndex, 'AI answer should precede route preamble');
  assert.ok(aiIndex < excerptIndex, 'AI answer should precede quoted excerpts');
});

test('waiting placeholder uses waiting class and appears first', () => {
  const waitingPayload = {
    content: {
      ...samplePayload.content,
      ai_answer: 'WAITING FOR AI ANSWER - using high quality reasoning model so it may take 30-60 seconds...',
    },
  };
  const html = generateDropdownContent(waitingPayload, 'quoted-qa-then-ai-answer');
  const waitingIndex = html.indexOf('accordion-dropdown-text-waiting');
  const excerptIndex = html.indexOf('Answer excerpt one');
  assert.ok(waitingIndex !== -1, 'expected waiting block');
  assert.ok(waitingIndex < excerptIndex, 'waiting block should precede quoted excerpts');
});
