'use strict'

const { pathfinder } = require('mineflayer-pathfinder')
const { parseControllerCommand } = require('./controller-commands')
const {
  ActionCancelledError,
  GameActions,
  getPlayerEntity
} = require('./game-actions')

class CommandController {
  constructor (bot, {
    botName,
    controllerUsername,
    logger = console,
    actions = new GameActions(bot, { logger })
  }) {
    this.bot = bot
    this.botName = botName
    this.controllerUsername = controllerUsername
    this.logger = logger
    this.actions = actions
    this.mode = 'idle'
    this.signal = null
    this.task = null
    this.disposed = false
    this.onChat = this.onChat.bind(this)
    this.onSpawn = this.onSpawn.bind(this)

    bot.on('chat', this.onChat)
    bot.on('spawn', this.onSpawn)
  }

  onSpawn () {
    try {
      this.actions.configure()
      this.logger.info?.(
        `[controller] ready for commands from ${this.controllerUsername}; ` +
        `say "${this.botName} help" in game`
      )
    } catch (error) {
      this.logger.error?.(`[controller] setup failed: ${error.message}`)
    }
  }

  isAuthorized (username) {
    return String(username).toLowerCase() === this.controllerUsername.toLowerCase()
  }

  reply (message) {
    this.logger.info?.(`[controller] ${message}`)
    try {
      this.bot.chat(message)
    } catch (error) {
      this.logger.error?.(`[controller] could not send chat reply: ${error.message}`)
    }
  }

  cancelCurrent (announce = false) {
    if (this.signal) this.signal.cancelled = true
    this.signal = null
    this.mode = 'idle'
    this.actions.stop()
    if (announce) this.reply('Stopped.')
  }

  startFollowing () {
    const entity = getPlayerEntity(this.bot, this.controllerUsername)
    if (!entity) {
      this.reply(`I cannot see ${this.controllerUsername}. Move into my loaded area and try again.`)
      return
    }

    this.cancelCurrent(false)
    try {
      this.actions.follow(entity)
      this.mode = 'following'
      this.reply(`Following ${this.controllerUsername}. Say "${this.botName} stop" to stop me.`)
    } catch (error) {
      this.mode = 'idle'
      this.reply(`I could not start following: ${error.message}`)
    }
  }

  startCollecting (count) {
    if (!getPlayerEntity(this.bot, this.controllerUsername)) {
      this.reply(`I cannot see ${this.controllerUsername}. Stay nearby and try again.`)
      return
    }

    this.cancelCurrent(false)
    const signal = { cancelled: false }
    this.signal = signal
    this.mode = 'collecting_logs'
    this.reply(`Starting: collect ${count} logs, return, and drop them for ${this.controllerUsername}.`)

    this.task = this.actions.collectAndDeliver({
      count,
      controllerUsername: this.controllerUsername,
      signal,
      report: message => {
        if (!signal.cancelled && this.signal === signal) this.reply(message)
      }
    }).then(result => {
      if (!signal.cancelled && this.signal === signal) {
        this.signal = null
        this.mode = 'idle'
        this.reply(`Task complete: delivered ${result.delivered} logs to ${this.controllerUsername}.`)
      }
    }).catch(error => {
      if (error instanceof ActionCancelledError || signal.cancelled) return
      if (this.signal === signal) {
        this.signal = null
        this.mode = 'idle'
        this.actions.stop()
        this.reply(`Task failed: ${error.message}`)
      }
    })
  }

  onChat (username, message) {
    if (this.disposed || !this.isAuthorized(username)) return
    const command = parseControllerCommand(message, this.botName)
    if (!command) return

    if (command.type === 'help') {
      this.reply(
        `Commands: "${this.botName} follow me", "${this.botName} stop", or ` +
        `"${this.botName} chop 10 logs and bring them back to me".`
      )
      return
    }
    if (command.type === 'invalid') {
      this.reply(command.message)
      return
    }
    if (command.type === 'stop') {
      this.cancelCurrent(true)
      return
    }
    if (command.type === 'follow') {
      this.startFollowing()
      return
    }
    if (command.type === 'collect_logs') {
      this.startCollecting(command.count)
    }
  }

  dispose () {
    if (this.disposed) return
    this.disposed = true
    this.cancelCurrent(false)
    this.bot.removeListener('chat', this.onChat)
    this.bot.removeListener('spawn', this.onSpawn)
  }
}

function installCommandController (bot, config, dependencies = {}) {
  if (!config.controllerUsername) {
    return {
      enabled: false,
      dispose () {}
    }
  }

  bot.loadPlugin(dependencies.pathfinderPlugin || pathfinder)
  const actions = dependencies.actions || new GameActions(bot, {
    logger: dependencies.logger,
    goals: dependencies.goals,
    MovementsClass: dependencies.MovementsClass,
    timers: dependencies.timers,
    now: dependencies.now
  })
  const controller = new CommandController(bot, {
    botName: config.username,
    controllerUsername: config.controllerUsername,
    logger: dependencies.logger,
    actions
  })
  controller.enabled = true
  return controller
}

module.exports = {
  CommandController,
  installCommandController
}
