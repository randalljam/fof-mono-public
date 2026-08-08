'use strict'

const assert = require('node:assert/strict')
const { EventEmitter } = require('node:events')
const { test } = require('node:test')

const {
  FORGE_CUSTOM_PACKETS,
  installForgePacketAdapters
} = require('../src/forge-packets')

test('treats Forge recipe and command declarations as opaque 1.20 payloads', () => {
  const types = FORGE_CUSTOM_PACKETS['1.20'].play.toClient.types
  assert.equal(types.packet_declare_recipes, 'restBuffer')
  assert.equal(types.packet_declare_commands, 'restBuffer')
})

test('supplies a safe empty command tree to minecraft-protocol listeners', () => {
  const client = new EventEmitter()
  let observed
  client.on('declare_commands', packet => { observed = packet })

  installForgePacketAdapters(client)
  installForgePacketAdapters(client)
  client.emit('declare_commands', Buffer.from([0x01, 0x02]))

  assert.deepEqual(observed.nodes, [{ children: [] }])
  assert.equal(observed.rootIndex, 0)
  assert.equal(client.listenerCount('declare_commands'), 2)
})
