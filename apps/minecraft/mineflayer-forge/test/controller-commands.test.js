'use strict'

const assert = require('node:assert/strict')
const { test } = require('node:test')

const {
  MAX_LOGS_PER_TASK,
  parseControllerCommand
} = require('../src/controller-commands')

test('parses addressed follow, stop, and log collection commands', () => {
  assert.deepEqual(
    parseControllerCommand('SkulkScraper, follow me!', 'SkulkScraper'),
    { type: 'follow' }
  )
  assert.deepEqual(
    parseControllerCommand('skulkscraper stop following me', 'SkulkScraper'),
    { type: 'stop' }
  )
  assert.deepEqual(
    parseControllerCommand(
      'SkulkScraper chop 10 logs and bring them back to me',
      'SkulkScraper'
    ),
    { type: 'collect_logs', count: 10 }
  )
})

test('ignores chat that is not addressed to the bot', () => {
  assert.equal(parseControllerCommand('follow me', 'SkulkScraper'), null)
  assert.equal(parseControllerCommand('OtherBot follow me', 'SkulkScraper'), null)
})

test('bounds collection tasks and explains unsupported commands', () => {
  assert.deepEqual(
    parseControllerCommand(`SkulkScraper chop ${MAX_LOGS_PER_TASK + 1} logs`, 'SkulkScraper'),
    { type: 'invalid', message: `Log count must be between 1 and ${MAX_LOGS_PER_TASK}.` }
  )

  const invalid = parseControllerCommand('SkulkScraper fight the dragon', 'SkulkScraper')
  assert.equal(invalid.type, 'invalid')
  assert.match(invalid.message, /follow me/)
})
