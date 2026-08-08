'use strict'

const {
  Movements,
  goals: defaultGoals
} = require('mineflayer-pathfinder')

const LOG_SEARCH_RADIUS = 48
const LOG_SEARCH_CANDIDATES = 256
const PATH_TIMEOUT_MS = 30_000
const RETURN_TIMEOUT_MS = 45_000
const PICKUP_TIMEOUT_MS = 8_000

class ActionCancelledError extends Error {
  constructor () {
    super('Action cancelled')
    this.name = 'ActionCancelledError'
  }
}

function isLogName (name) {
  return typeof name === 'string' && name.endsWith('_log')
}

function isLeavesName (name) {
  return typeof name === 'string' && name.endsWith('_leaves')
}

function positionKey (position) {
  return `${position.x},${position.y},${position.z}`
}

function distanceBetween (first, second) {
  const dx = first.x - second.x
  const dy = first.y - second.y
  const dz = first.z - second.z
  return Math.sqrt(dx * dx + dy * dy + dz * dz)
}

function snapshotLogCounts (items) {
  const counts = new Map()
  for (const item of items) {
    if (!isLogName(item.name)) continue
    const existing = counts.get(item.type) || {
      type: item.type,
      name: item.name,
      count: 0
    }
    existing.count += item.count
    counts.set(item.type, existing)
  }
  return counts
}

function countNewLogs (items, baseline) {
  const current = snapshotLogCounts(items)
  let count = 0
  for (const [type, entry] of current) {
    count += Math.max(0, entry.count - (baseline.get(type)?.count || 0))
  }
  return count
}

function totalLogs (items) {
  let count = 0
  for (const item of items) {
    if (isLogName(item.name)) count += item.count
  }
  return count
}

function findAxe (items) {
  return items.find(item => typeof item.name === 'string' && item.name.endsWith('_axe')) || null
}

function getPlayerEntity (bot, username) {
  const target = String(username).toLowerCase()
  for (const [name, player] of Object.entries(bot.players || {})) {
    if (name.toLowerCase() === target) return player?.entity || null
  }
  return null
}

function hasNearbyLeaves (bot, logPosition) {
  for (let dy = -1; dy <= 8; dy += 1) {
    for (let dx = -3; dx <= 3; dx += 1) {
      for (let dz = -3; dz <= 3; dz += 1) {
        const block = bot.blockAt(logPosition.offset(dx, dy, dz))
        if (block && isLeavesName(block.name)) return true
      }
    }
  }
  return false
}

class GameActions {
  constructor (bot, {
    logger = console,
    goals = defaultGoals,
    MovementsClass = Movements,
    timers = globalThis,
    now = Date.now
  } = {}) {
    this.bot = bot
    this.logger = logger
    this.goals = goals
    this.MovementsClass = MovementsClass
    this.timers = timers
    this.now = now
    this.movements = null
  }

  configure () {
    if (!this.bot.pathfinder || !this.bot.registry) {
      throw new Error('Pathfinder is not ready')
    }
    if (!this.movements) {
      this.movements = new this.MovementsClass(this.bot)
      this.movements.canDig = false
      this.movements.allow1by1towers = false
      this.movements.allowParkour = false
      this.movements.scafoldingBlocks = []
    }
    this.bot.pathfinder.setMovements(this.movements)
  }

  follow (entity) {
    this.configure()
    this.bot.pathfinder.setGoal(new this.goals.GoalFollow(entity, 2), true)
  }

  stop () {
    this.bot.pathfinder?.setGoal(null)
    if (this.bot.targetDigBlock && typeof this.bot.stopDigging === 'function') {
      try {
        this.bot.stopDigging()
      } catch (error) {
        this.logger.warn?.(`[actions] could not stop digging: ${error.message}`)
      }
    }
    this.bot.clearControlStates?.()
  }

  assertActive (signal) {
    if (signal.cancelled) throw new ActionCancelledError()
  }

  delay (milliseconds) {
    return new Promise(resolve => this.timers.setTimeout(resolve, milliseconds))
  }

  async withTimeout (promise, milliseconds, description, signal) {
    let timeout
    const timedOut = new Promise((resolve, reject) => {
      timeout = this.timers.setTimeout(() => {
        this.bot.pathfinder?.setGoal(null)
        reject(new Error(`${description} timed out`))
      }, milliseconds)
    })

    try {
      const result = await Promise.race([promise, timedOut])
      this.assertActive(signal)
      return result
    } finally {
      this.timers.clearTimeout(timeout)
    }
  }

  async waitUntil (predicate, milliseconds, signal, interval = 100) {
    const startedAt = this.now()
    while (this.now() - startedAt < milliseconds) {
      this.assertActive(signal)
      const value = predicate()
      if (value) return value
      await this.delay(interval)
    }
    this.assertActive(signal)
    return predicate() || null
  }

  findNaturalLog (excluded) {
    const ids = Object.values(this.bot.registry.blocksByName || {})
      .filter(block => isLogName(block.name))
      .map(block => block.id)

    const positions = this.bot.findBlocks({
      matching: ids,
      maxDistance: LOG_SEARCH_RADIUS,
      count: LOG_SEARCH_CANDIDATES
    })

    for (const position of positions) {
      if (excluded.has(positionKey(position))) continue
      const block = this.bot.blockAt(position)
      if (block && isLogName(block.name) && hasNearbyLeaves(this.bot, position)) {
        return block
      }
    }
    return null
  }

  findNearbyItemDrop (position) {
    return this.bot.nearestEntity(entity => {
      return entity &&
        entity.name === 'item' &&
        entity.isValid !== false &&
        entity.position &&
        distanceBetween(entity.position, position) <= 6
    })
  }

  async navigateToLog (block, signal) {
    const goal = new this.goals.GoalLookAtBlock(block.position, this.bot.world)
    await this.withTimeout(
      this.bot.pathfinder.goto(goal),
      PATH_TIMEOUT_MS,
      `Path to log at ${positionKey(block.position)}`,
      signal
    )
  }

  async collectDrop (blockPosition, previousLogCount, signal) {
    if (totalLogs(this.bot.inventory.items()) > previousLogCount) return

    const drop = await this.waitUntil(() => {
      if (totalLogs(this.bot.inventory.items()) > previousLogCount) return { pickedUp: true }
      return this.findNearbyItemDrop(blockPosition)
    }, 3_000, signal)

    if (drop && !drop.pickedUp) {
      await this.withTimeout(
        this.bot.pathfinder.goto(new this.goals.GoalFollow(drop, 0)),
        PATH_TIMEOUT_MS,
        'Path to dropped log',
        signal
      )
    }

    const pickedUp = await this.waitUntil(
      () => totalLogs(this.bot.inventory.items()) > previousLogCount,
      PICKUP_TIMEOUT_MS,
      signal
    )
    if (!pickedUp) throw new Error('A chopped log was not picked up')
  }

  async returnToPlayer (controllerUsername, signal) {
    const entity = getPlayerEntity(this.bot, controllerUsername)
    if (!entity) throw new Error(`I cannot see ${controllerUsername}`)
    if (distanceBetween(this.bot.entity.position, entity.position) <= 3) return entity

    this.bot.pathfinder.setGoal(new this.goals.GoalFollow(entity, 2), true)
    const reached = await this.waitUntil(() => {
      const current = getPlayerEntity(this.bot, controllerUsername)
      if (!current) return null
      return distanceBetween(this.bot.entity.position, current.position) <= 3 ? current : null
    }, RETURN_TIMEOUT_MS, signal, 250)
    this.bot.pathfinder.setGoal(null)
    if (!reached) throw new Error(`Could not return to ${controllerUsername}`)
    return reached
  }

  async deliverLogs (baseline, requestedCount, controllerEntity, signal) {
    this.assertActive(signal)
    const current = snapshotLogCounts(this.bot.inventory.items())
    let remaining = requestedCount

    await this.bot.lookAt(controllerEntity.position.offset(0, 1.4, 0), true)
    for (const [type, entry] of current) {
      const available = Math.max(0, entry.count - (baseline.get(type)?.count || 0))
      const quantity = Math.min(remaining, available)
      if (quantity === 0) continue
      await this.bot.toss(type, null, quantity)
      remaining -= quantity
      this.assertActive(signal)
      if (remaining === 0) break
    }

    if (remaining !== 0) {
      throw new Error(`Only ${requestedCount - remaining}/${requestedCount} logs were available to deliver`)
    }
  }

  async collectAndDeliver ({ count, controllerUsername, signal, report = () => {} }) {
    this.configure()
    const baseline = snapshotLogCounts(this.bot.inventory.items())
    const excluded = new Set()
    const maximumAttempts = count * 3 + 10
    let attempts = 0
    let lastReported = 0

    while (countNewLogs(this.bot.inventory.items(), baseline) < count) {
      this.assertActive(signal)
      if (attempts >= maximumAttempts) {
        throw new Error(`Could not collect ${count} logs after ${maximumAttempts} attempts`)
      }

      const axe = findAxe(this.bot.inventory.items())
      if (!axe) throw new Error('I need an axe in my inventory before I can chop logs')

      const block = this.findNaturalLog(excluded)
      if (!block) {
        throw new Error(`I could not find a natural tree within ${LOG_SEARCH_RADIUS} blocks`)
      }

      const key = positionKey(block.position)
      const previousLogCount = totalLogs(this.bot.inventory.items())
      attempts += 1

      try {
        await this.navigateToLog(block, signal)
        const currentBlock = this.bot.blockAt(block.position)
        if (!currentBlock || !isLogName(currentBlock.name)) {
          excluded.add(key)
          continue
        }

        await this.bot.equip(axe, 'hand')
        this.assertActive(signal)
        await this.bot.dig(currentBlock, true)
        this.assertActive(signal)
        await this.collectDrop(currentBlock.position, previousLogCount, signal)
      } catch (error) {
        this.assertActive(signal)
        excluded.add(key)
        this.logger.warn?.(`[actions] skipping log ${key}: ${error.message}`)
        continue
      }

      const collected = Math.min(count, countNewLogs(this.bot.inventory.items(), baseline))
      if (collected === count || collected - lastReported >= 5) {
        lastReported = collected
        report(`Collected ${collected}/${count} logs.`)
      }
    }

    report(`Collected ${count} logs. Returning to ${controllerUsername}.`)
    const controllerEntity = await this.returnToPlayer(controllerUsername, signal)
    report(`Back at ${controllerUsername}. Dropping ${count} logs now.`)
    await this.deliverLogs(baseline, count, controllerEntity, signal)
    this.stop()
    return { collected: count, delivered: count }
  }
}

module.exports = {
  ActionCancelledError,
  GameActions,
  LOG_SEARCH_RADIUS,
  countNewLogs,
  distanceBetween,
  findAxe,
  getPlayerEntity,
  hasNearbyLeaves,
  isLeavesName,
  isLogName,
  snapshotLogCounts,
  totalLogs
}
