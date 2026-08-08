'use strict'

const { installFml3 } = require('./fml3')
const { FORGE_CUSTOM_PACKETS, installForgePacketAdapters } = require('./forge-packets')
const { installCommandController } = require('./command-controller')

const SHUTDOWN_GRACE_MS = 1000

function display (value) {
  if (value instanceof Error) return value.stack || value.message
  if (typeof value === 'string') return value

  try {
    return JSON.stringify(value)
  } catch (_) {
    return String(value)
  }
}

function runBot (config, dependencies = {}) {
  const createBot = dependencies.createBot || require('mineflayer').createBot
  const timers = dependencies.timers || globalThis
  const logger = dependencies.logger || console
  const installForgeHandshake = dependencies.installForgeHandshake || installFml3
  const installPacketAdapters = dependencies.installForgePacketAdapters || installForgePacketAdapters
  const installController = dependencies.installCommandController || installCommandController
  const shutdownGraceMs = dependencies.shutdownGraceMs ?? SHUTDOWN_GRACE_MS

  const botOptions = {
    host: config.host,
    port: config.port,
    version: config.version,
    username: config.username,
    auth: config.auth,
    customPackets: FORGE_CUSTOM_PACKETS
  }
  if (config.auth === 'microsoft') {
    botOptions.profilesFolder = config.profilesFolder
  }

  logger.info(
    `[bot] connecting to ${config.host}:${config.port} ` +
    `(Minecraft ${config.version}, auth=${config.auth})`
  )
  if (config.controllerUsername) {
    logger.info(`[bot] command mode: accepting addressed chat only from ${config.controllerUsername}`)
  } else {
    logger.info('[bot] stationary mode: no controller configured')
  }

  const bot = createBot(botOptions)
  installPacketAdapters(bot._client)
  installForgeHandshake(bot._client, { logger })
  const commandController = installController(bot, config, { logger, timers })
  let ended = false
  let stopping = false
  let spawned = false
  let hadError = false
  let wasKicked = false
  let stopCause = null
  let smokeTimer = null
  let shutdownTimer = null
  let resolveDone

  const done = new Promise((resolve) => {
    resolveDone = resolve
  })

  function clearTimer (timer) {
    if (timer !== null) timers.clearTimeout(timer)
  }

  function finish (reason) {
    if (ended) return
    ended = true
    commandController.dispose()
    clearTimer(smokeTimer)
    clearTimer(shutdownTimer)
    logger.info(`[bot] connection ended${reason ? `: ${display(reason)}` : ''}`)
    resolveDone({
      spawned,
      hadError,
      wasKicked,
      stopCause,
      endReason: reason
    })
  }

  function forceClose (cause) {
    if (ended) return
    logger.warn(`[bot] graceful disconnect timed out; closing the client (${cause})`)
    try {
      bot.end(`Client closing: ${cause}`)
      const socket = bot._client && bot._client.socket
      if (socket && !socket.destroyed) socket.destroy()
    } catch (error) {
      hadError = true
      logger.error(`[bot] client close failed: ${display(error)}`)
    }
  }

  function stop (cause = 'requested') {
    if (ended || stopping) return
    stopping = true
    stopCause = cause
    clearTimer(smokeTimer)
    logger.info(`[bot] disconnect requested (${cause})`)
    commandController.dispose()

    try {
      bot.quit(`Client stopping: ${cause}`)
    } catch (error) {
      hadError = true
      logger.error(`[bot] graceful disconnect failed: ${display(error)}`)
      forceClose(cause)
    }

    if (!ended) {
      shutdownTimer = timers.setTimeout(() => forceClose(cause), shutdownGraceMs)
    }
  }

  bot.once('login', () => {
    logger.info(`[bot] login accepted as ${bot.username || config.username}`)
  })
  bot.once('spawn', () => {
    spawned = true
    logger.info(
      config.controllerUsername
        ? `[bot] spawned; commands enabled for ${config.controllerUsername}`
        : '[bot] spawned; remaining stationary'
    )
  })
  bot.on('kicked', (reason, loggedIn) => {
    wasKicked = true
    logger.error(`[bot] kicked (loggedIn=${Boolean(loggedIn)}): ${display(reason)}`)
  })
  bot.on('error', (error) => {
    hadError = true
    logger.error(`[bot] error: ${display(error)}`)
  })
  bot.once('end', finish)

  if (config.smokeTimeoutMs > 0) {
    logger.info(`[bot] smoke timeout armed for ${config.smokeTimeoutMs} ms`)
    smokeTimer = timers.setTimeout(
      () => stop('smoke-timeout'),
      config.smokeTimeoutMs
    )
  }

  return { bot, commandController, done, stop }
}

module.exports = {
  SHUTDOWN_GRACE_MS,
  runBot
}
