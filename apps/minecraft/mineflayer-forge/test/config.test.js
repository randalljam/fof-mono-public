'use strict'

const assert = require('node:assert/strict')
const path = require('node:path')
const test = require('node:test')

const { APP_ROOT, DEFAULTS, loadConfig } = require('../src/config')

test('uses Forge 1.20.1 localhost defaults and safe offline auth', () => {
  const config = loadConfig({ argv: [], env: {} })

  assert.deepEqual(config, {
    host: '127.0.0.1',
    port: 25565,
    version: '1.20.1',
    username: 'MineflayerBot',
    controllerUsername: null,
    auth: 'offline',
    profilesFolder: path.join(APP_ROOT, '.profiles'),
    smokeTimeoutMs: 0,
    pingTimeoutMs: 5000,
    help: false
  })
  assert.equal(DEFAULTS.auth, 'offline')
})

test('reads environment values and lets command-line values win', () => {
  const config = loadConfig({
    env: {
      MINEFLAYER_HOST: 'server.example',
      MINEFLAYER_PORT: '25570',
      MINEFLAYER_VERSION: '1.20.1',
      MINEFLAYER_USERNAME: 'CachedAccount',
      MINEFLAYER_CONTROLLER: 'FamilyPlayer',
      MINEFLAYER_AUTH: 'microsoft',
      MINEFLAYER_PROFILES_FOLDER: './private-cache',
      MINEFLAYER_SMOKE_TIMEOUT_MS: '9000',
      MINEFLAYER_PING_TIMEOUT_MS: '4000'
    },
    argv: ['--host=127.0.0.2', '--port', '25571', '--smoke-timeout-ms', '250']
  })

  assert.equal(config.host, '127.0.0.2')
  assert.equal(config.port, 25571)
  assert.equal(config.auth, 'microsoft')
  assert.equal(config.username, 'CachedAccount')
  assert.equal(config.controllerUsername, 'FamilyPlayer')
  assert.equal(config.profilesFolder, path.resolve('./private-cache'))
  assert.equal(config.smokeTimeoutMs, 250)
  assert.equal(config.pingTimeoutMs, 4000)
})

test('rejects unsafe or malformed configuration explicitly', () => {
  assert.throws(
    () => loadConfig({ argv: ['--auth', 'auto'], env: {} }),
    /auth must be either "offline" or "microsoft"/
  )
  assert.throws(
    () => loadConfig({ argv: ['--port', '70000'], env: {} }),
    /port must be between 1 and 65535/
  )
  assert.throws(
    () => loadConfig({ argv: ['--smoke-timeout-ms', '-1'], env: {} }),
    /smoke timeout must be an integer/
  )
  assert.throws(
    () => loadConfig({ argv: ['--unknown', 'value'], env: {} }),
    /Unknown argument/
  )
  assert.throws(
    () => loadConfig({ argv: ['--controller', 'not a java name'], env: {} }),
    /controller must be a valid Minecraft Java username/
  )
  assert.throws(
    () => loadConfig({
      argv: ['--username', 'SkulkScraper', '--controller', 'skulkscraper'],
      env: {}
    }),
    /controller must be different/
  )
})
