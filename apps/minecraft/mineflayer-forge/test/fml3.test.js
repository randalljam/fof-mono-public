'use strict'

const assert = require('node:assert/strict')
const { EventEmitter } = require('node:events')
const { test } = require('node:test')

const {
  DISCRIMINATORS,
  FML3_HOST_MARKER,
  HANDSHAKE_CHANNEL,
  LOGIN_WRAPPER_CHANNEL,
  buildLoginWrapper,
  installFml3,
  parseLoginWrapper,
  parseModListReply,
  writeString,
  writeVarInt
} = require('../src/fml3')

function buildServerModData () {
  return Buffer.concat([
    Buffer.from([DISCRIMINATORS.S2C_MOD_DATA]),
    writeVarInt(1),
    writeString('iceandfire'),
    writeString('Ice and Fire'),
    writeString('2.1.13')
  ])
}

function buildServerModList () {
  return Buffer.concat([
    Buffer.from([DISCRIMINATORS.S2C_MOD_LIST]),
    writeVarInt(2),
    writeString('forge'),
    writeString('iceandfire'),
    writeVarInt(3),
    writeString('fml:handshake'),
    writeString('FML3'),
    writeString('iceandfire:main'),
    writeString('1'),
    writeString('modernfix:ingredient_sync'),
    writeString('1'),
    writeVarInt(1),
    writeString('minecraft:entity_type'),
    writeVarInt(0)
  ])
}

class FakeClient extends EventEmitter {
  constructor () {
    super()
    this.writes = []
    this.tagHost = ''
  }

  write (name, packet) {
    this.writes.push({ name, packet })
  }
}

const quietLogger = {
  info () {},
  warn () {},
  error () {}
}

test('installs the FML3 host marker and replaces the vanilla login fallback', () => {
  const client = new FakeClient()
  let vanillaFallbackCalled = false
  client.on('login_plugin_request', () => { vanillaFallbackCalled = true })

  const state = installFml3(client, { logger: quietLogger })

  assert.equal(client.tagHost, FML3_HOST_MARKER)
  assert.equal(client.listenerCount('login_plugin_request'), 1)
  assert.equal(installFml3(client, { logger: quietLogger }), state)

  client.emit('login_plugin_request', {
    messageId: 1,
    channel: 'example:unknown',
    data: Buffer.alloc(0)
  })
  assert.equal(vanillaFallbackCalled, false)
  assert.deepEqual(client.writes, [{
    name: 'login_plugin_response',
    packet: { messageId: 1 }
  }])
})

test('records Forge mod data without replying to its no-response packet', () => {
  const client = new FakeClient()
  const state = installFml3(client, { logger: quietLogger })

  client.emit('login_plugin_request', {
    messageId: 3,
    channel: LOGIN_WRAPPER_CHANNEL,
    data: buildLoginWrapper(HANDSHAKE_CHANNEL, buildServerModData())
  })

  assert.equal(state.modData.get('iceandfire').displayName, 'Ice and Fire')
  assert.equal(state.modData.get('iceandfire').version, '2.1.13')
  assert.equal(client.writes.length, 0)
})

test('advertises only implemented client mods while accepting required channels', () => {
  const client = new FakeClient()
  const state = installFml3(client, { logger: quietLogger })
  let emittedModList
  client.on('fml3:mod_list', value => { emittedModList = value })

  client.emit('login_plugin_request', {
    messageId: 7,
    channel: LOGIN_WRAPPER_CHANNEL,
    data: buildLoginWrapper(HANDSHAKE_CHANNEL, buildServerModList())
  })

  assert.equal(client.writes.length, 1)
  const write = client.writes[0]
  assert.equal(write.name, 'login_plugin_response')
  assert.equal(write.packet.messageId, 7)

  const wrapper = parseLoginWrapper(write.packet.data)
  assert.equal(wrapper.targetChannel, HANDSHAKE_CHANNEL)
  const reply = parseModListReply(wrapper.payload)
  assert.deepEqual(reply.mods, ['minecraft', 'forge'])
  assert.deepEqual([...reply.channels], [
    ['fml:handshake', 'FML3'],
    ['iceandfire:main', '1']
  ])
  assert.equal(state.channels.has('modernfix:ingredient_sync'), true)
  assert.equal(state.clientChannels.has('modernfix:ingredient_sync'), false)
  assert.equal(reply.registries.size, 0)
  assert.equal(state.registries[0], 'minecraft:entity_type')
  assert.deepEqual(emittedModList.mods, state.mods)
  assert.deepEqual([...emittedModList.channels], [...state.channels])
})

test('acknowledges Forge registry and config synchronization packets', () => {
  const client = new FakeClient()
  installFml3(client, { logger: quietLogger })

  for (const [messageId, discriminator] of [
    [11, DISCRIMINATORS.S2C_REGISTRY],
    [12, DISCRIMINATORS.S2C_CONFIG_DATA]
  ]) {
    client.emit('login_plugin_request', {
      messageId,
      channel: LOGIN_WRAPPER_CHANNEL,
      data: buildLoginWrapper(HANDSHAKE_CHANNEL, Buffer.from([discriminator]))
    })
  }

  assert.equal(client.writes.length, 2)
  for (const [index, expectedMessageId] of [11, 12].entries()) {
    const write = client.writes[index]
    assert.equal(write.packet.messageId, expectedMessageId)
    const wrapper = parseLoginWrapper(write.packet.data)
    assert.equal(wrapper.targetChannel, HANDSHAKE_CHANNEL)
    assert.deepEqual(wrapper.payload, Buffer.from([DISCRIMINATORS.C2S_ACKNOWLEDGE]))
  }
})

test('rejects truncated wrapper data instead of reading beyond the packet', () => {
  assert.throws(
    () => parseLoginWrapper(Buffer.from([0x0d, 0x66, 0x6d, 0x6c])),
    /Truncated Forge payload/
  )
})
