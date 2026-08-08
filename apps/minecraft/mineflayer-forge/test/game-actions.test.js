'use strict'

const assert = require('node:assert/strict')
const test = require('node:test')

const {
  GameActions,
  countNewLogs,
  findAxe,
  isLeavesName,
  isLogName,
  snapshotLogCounts
} = require('../src/game-actions')

class Position {
  constructor (x, y, z) {
    this.x = x
    this.y = y
    this.z = z
  }

  offset (x, y, z) {
    return new Position(this.x + x, this.y + y, this.z + z)
  }
}

class FakeMovements {
  constructor () {
    this.canDig = true
    this.allow1by1towers = true
    this.allowParkour = true
    this.scafoldingBlocks = [1]
  }
}

class GoalFollow {
  constructor (entity, range) {
    this.entity = entity
    this.range = range
  }
}

class GoalLookAtBlock {
  constructor (position) {
    this.position = position
  }
}

function createCollectionBot () {
  const logPositions = Array.from({ length: 10 }, (_, index) => new Position(index + 4, 64, 0))
  const remainingLogs = new Map(logPositions.map(position => [
    `${position.x},${position.y},${position.z}`,
    position
  ]))
  let logCount = 0
  const bot = {
    registry: {
      blocksByName: {
        oak_log: { id: 1, name: 'oak_log' }
      }
    },
    world: {},
    entity: { position: new Position(0, 64, 0) },
    players: {
      FamilyPlayer: { entity: { position: new Position(1, 64, 1) } }
    },
    pathfinder: {
      movements: null,
      goals: [],
      setMovements (movements) { this.movements = movements },
      setGoal (goal, dynamic) { this.goals.push({ goal, dynamic }) },
      async goto (goal) { this.goals.push({ goal, dynamic: false }) }
    },
    inventory: {
      items () {
        const items = [{ type: 100, name: 'iron_axe', count: 1 }]
        if (logCount > 0) items.push({ type: 1, name: 'oak_log', count: logCount })
        return items
      }
    },
    findBlocks () {
      return [...remainingLogs.values()]
    },
    blockAt (position) {
      const key = `${position.x},${position.y},${position.z}`
      if (remainingLogs.has(key)) {
        return { type: 1, name: 'oak_log', position: remainingLogs.get(key) }
      }
      const leafForTree = logPositions.some(log => {
        return position.x === log.x && position.y === log.y + 4 && position.z === log.z
      })
      return leafForTree
        ? { type: 2, name: 'oak_leaves', position }
        : { type: 0, name: 'air', position }
    },
    nearestEntity () { return null },
    async equip (item) { this.equipped = item },
    async dig (block) {
      remainingLogs.delete(`${block.position.x},${block.position.y},${block.position.z}`)
      logCount += 1
    },
    async lookAt (position) { this.lookedAt = position },
    async toss (type, metadata, count) {
      assert.equal(type, 1)
      assert.equal(metadata, null)
      logCount -= count
      this.tossed = (this.tossed || 0) + count
    },
    clearControlStates () {}
  }
  return bot
}

test('classifies raw logs, leaves, axes, and new inventory logs', () => {
  assert.equal(isLogName('oak_log'), true)
  assert.equal(isLogName('oak_planks'), false)
  assert.equal(isLeavesName('cherry_leaves'), true)
  assert.equal(isLeavesName('azalea'), false)
  assert.equal(findAxe([
    { name: 'diamond_pickaxe' },
    { name: 'iron_axe' }
  ]).name, 'iron_axe')

  const baseline = snapshotLogCounts([{ type: 1, name: 'oak_log', count: 3 }])
  assert.equal(countNewLogs([
    { type: 1, name: 'oak_log', count: 5 },
    { type: 2, name: 'birch_log', count: 4 }
  ], baseline), 6)
})

test('collects exactly ten natural logs and delivers them to the controller', async () => {
  const bot = createCollectionBot()
  const reports = []
  const actions = new GameActions(bot, {
    logger: { warn () {} },
    goals: { GoalFollow, GoalLookAtBlock },
    MovementsClass: FakeMovements
  })

  const result = await actions.collectAndDeliver({
    count: 10,
    controllerUsername: 'FamilyPlayer',
    signal: { cancelled: false },
    report: message => reports.push(message)
  })

  assert.deepEqual(result, { collected: 10, delivered: 10 })
  assert.equal(bot.tossed, 10)
  assert.equal(bot.inventory.items().filter(item => isLogName(item.name)).length, 0)
  assert.equal(bot.pathfinder.movements.canDig, false)
  assert.equal(bot.pathfinder.movements.allow1by1towers, false)
  assert.equal(bot.pathfinder.movements.allowParkour, false)
  assert.deepEqual(bot.pathfinder.movements.scafoldingBlocks, [])
  assert.match(reports.at(-1), /Dropping 10 logs/)
})
