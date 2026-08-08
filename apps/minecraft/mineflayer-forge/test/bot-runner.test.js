'use strict'

const assert = require('node:assert/strict')
const { EventEmitter } = require('node:events')
const test = require('node:test')

const { FORGE_CUSTOM_PACKETS } = require('../src/forge-packets')
const { runBot } = require('../src/lifecycle')

class FakeTimers {
  constructor () {
    this.nextId = 1
    this.scheduled = new Map()
  }

  setTimeout (callback, delay) {
    const id = this.nextId++
    this.scheduled.set(id, { callback, delay })
    return id
  }

  clearTimeout (id) {
    this.scheduled.delete(id)
  }

  runDelay (delay) {
    const match = [...this.scheduled.entries()].find(([, timer]) => timer.delay === delay)
    assert.ok(match, `expected a timer with delay ${delay}`)
    const [id, timer] = match
    this.scheduled.delete(id)
    timer.callback()
  }
}

class FakeBot extends EventEmitter {
  constructor () {
    super()
    this.username = 'TestBot'
    this.quitCalls = []
    this.endCalls = []
  }

  quit (reason) {
    this.quitCalls.push(reason)
  }

  end (reason) {
    this.endCalls.push(reason)
    this.emit('end', reason)
  }
}

function silentLogger () {
  return { info () {}, warn () {}, error () {} }
}

function disabledController () {
  return { dispose () {} }
}

test('finite smoke timeout disconnects and force-closes without a real network', async () => {
  const timers = new FakeTimers()
  const bot = new FakeBot()
  let receivedOptions
  const config = {
    host: '127.0.0.1',
    port: 25565,
    version: '1.20.1',
    username: 'TestBot',
    auth: 'offline',
    profilesFolder: '/must/not/be/used',
    smokeTimeoutMs: 25
  }

  const session = runBot(config, {
    createBot: (options) => {
      receivedOptions = options
      return bot
    },
    installForgePacketAdapters () {},
    installForgeHandshake () {},
    installCommandController: disabledController,
    timers,
    logger: silentLogger(),
    shutdownGraceMs: 10
  })

  assert.deepEqual(receivedOptions, {
    host: '127.0.0.1',
    port: 25565,
    version: '1.20.1',
    username: 'TestBot',
    auth: 'offline',
    customPackets: FORGE_CUSTOM_PACKETS
  })
  assert.equal(bot.quitCalls.length, 0)

  timers.runDelay(25)
  assert.deepEqual(bot.quitCalls, ['Client stopping: smoke-timeout'])

  timers.runDelay(10)
  const result = await session.done

  assert.deepEqual(bot.endCalls, ['Client closing: smoke-timeout'])
  assert.equal(result.stopCause, 'smoke-timeout')
  assert.equal(result.spawned, false)
  assert.equal(result.hadError, false)
  assert.equal(timers.scheduled.size, 0)
})

test('Microsoft auth is the only mode that receives the private profiles path', () => {
  const timers = new FakeTimers()
  const bot = new FakeBot()
  let receivedOptions

  const session = runBot({
    host: '127.0.0.1',
    port: 25565,
    version: '1.20.1',
    username: 'AccountAlias',
    auth: 'microsoft',
    profilesFolder: '/private/profiles',
    smokeTimeoutMs: 0
  }, {
    createBot: (options) => {
      receivedOptions = options
      return bot
    },
    installForgePacketAdapters () {},
    installForgeHandshake () {},
    installCommandController: disabledController,
    timers,
    logger: silentLogger()
  })

  assert.equal(receivedOptions.profilesFolder, '/private/profiles')
  assert.equal(timers.scheduled.size, 0)
  session.stop('test-cleanup')
  bot.emit('end', 'test complete')
})
