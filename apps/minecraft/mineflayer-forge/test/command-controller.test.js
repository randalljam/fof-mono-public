'use strict'

const assert = require('node:assert/strict')
const { EventEmitter } = require('node:events')
const { test } = require('node:test')

const { installCommandController } = require('../src/command-controller')

class FakeBot extends EventEmitter {
  constructor () {
    super()
    this.players = {
      FamilyPlayer: { entity: { position: { x: 1, y: 64, z: 1 } } },
      Stranger: { entity: { position: { x: 2, y: 64, z: 2 } } }
    }
    this.chatMessages = []
    this.loadedPlugins = []
  }

  chat (message) {
    this.chatMessages.push(message)
  }

  loadPlugin (plugin) {
    this.loadedPlugins.push(plugin)
  }
}

function createActions () {
  return {
    configured: 0,
    followed: [],
    stopped: 0,
    collected: [],
    configure () { this.configured += 1 },
    follow (entity) { this.followed.push(entity) },
    stop () { this.stopped += 1 },
    async collectAndDeliver (options) {
      this.collected.push(options)
      options.report(`Collected ${options.count}/${options.count} logs.`)
      return { collected: options.count, delivered: options.count }
    }
  }
}

test('accepts follow and stop only from the configured controller', () => {
  const bot = new FakeBot()
  const actions = createActions()
  const controller = installCommandController(bot, {
    username: 'SkulkScraper',
    controllerUsername: 'FamilyPlayer'
  }, {
    actions,
    logger: { info () {}, warn () {}, error () {} },
    pathfinderPlugin () {}
  })

  bot.emit('spawn')
  bot.emit('chat', 'Stranger', 'SkulkScraper follow me')
  assert.equal(actions.followed.length, 0)

  bot.emit('chat', 'FamilyPlayer', 'SkulkScraper follow me')
  assert.equal(actions.followed.length, 1)
  assert.equal(controller.mode, 'following')
  assert.match(bot.chatMessages.at(-1), /Following FamilyPlayer/)

  bot.emit('chat', 'FamilyPlayer', 'SkulkScraper stop')
  assert.equal(controller.mode, 'idle')
  assert.match(bot.chatMessages.at(-1), /Stopped/)
  assert.equal(actions.configured, 1)
})

test('dispatches the ten-log task and reports completion', async () => {
  const bot = new FakeBot()
  const actions = createActions()
  const controller = installCommandController(bot, {
    username: 'SkulkScraper',
    controllerUsername: 'FamilyPlayer'
  }, {
    actions,
    logger: { info () {}, warn () {}, error () {} },
    pathfinderPlugin () {}
  })

  bot.emit('chat', 'FamilyPlayer', 'SkulkScraper chop 10 logs and bring them back to me')
  await controller.task

  assert.equal(actions.collected.length, 1)
  assert.equal(actions.collected[0].count, 10)
  assert.equal(actions.collected[0].controllerUsername, 'FamilyPlayer')
  assert.equal(controller.mode, 'idle')
  assert.match(bot.chatMessages.at(-1), /delivered 10 logs/)
})

test('does not load pathfinding when no controller is configured', () => {
  const bot = new FakeBot()
  const controller = installCommandController(bot, {
    username: 'SkulkScraper',
    controllerUsername: null
  })

  assert.equal(controller.enabled, false)
  assert.equal(bot.loadedPlugins.length, 0)
})
