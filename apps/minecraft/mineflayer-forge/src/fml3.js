'use strict'

const FML3_HOST_MARKER = '\0FML3\0'
const LOGIN_WRAPPER_CHANNEL = 'fml:loginwrapper'
const HANDSHAKE_CHANNEL = 'fml:handshake'
const DEFAULT_CLIENT_MODS = Object.freeze(['minecraft', 'forge'])
const DEFAULT_UNSUPPORTED_CHANNELS = Object.freeze([
  // ModernFix rewrites vanilla recipe ingredient serialization when this
  // optional capability is present. Mineflayer uses the vanilla wire format.
  'modernfix:ingredient_sync'
])

const DISCRIMINATORS = Object.freeze({
  S2C_MOD_LIST: 1,
  C2S_MOD_LIST_REPLY: 2,
  S2C_REGISTRY: 3,
  S2C_CONFIG_DATA: 4,
  S2C_MOD_DATA: 5,
  S2C_CHANNEL_MISMATCH: 6,
  C2S_ACKNOWLEDGE: 99
})

const INSTALLED = Symbol('fof.fml3.installed')

class BufferReader {
  constructor (buffer) {
    if (!Buffer.isBuffer(buffer)) throw new TypeError('Expected a Buffer')
    this.buffer = buffer
    this.offset = 0
  }

  get remaining () {
    return this.buffer.length - this.offset
  }

  readUnsignedByte () {
    this.ensure(1)
    return this.buffer[this.offset++]
  }

  readBoolean () {
    return this.readUnsignedByte() !== 0
  }

  readVarInt () {
    let result = 0
    let shift = 0

    for (let byteIndex = 0; byteIndex < 5; byteIndex += 1) {
      const byte = this.readUnsignedByte()
      result |= (byte & 0x7f) << shift
      if ((byte & 0x80) === 0) return result >>> 0
      shift += 7
    }

    throw new Error('VarInt exceeds five bytes')
  }

  readString (maximumBytes = 32767) {
    const byteLength = this.readVarInt()
    if (byteLength > maximumBytes) {
      throw new Error(`String length ${byteLength} exceeds ${maximumBytes}`)
    }
    const data = this.readBytes(byteLength)
    return data.toString('utf8')
  }

  readBytes (length) {
    if (!Number.isSafeInteger(length) || length < 0) {
      throw new Error(`Invalid buffer length: ${length}`)
    }
    this.ensure(length)
    const value = this.buffer.subarray(this.offset, this.offset + length)
    this.offset += length
    return value
  }

  ensure (length) {
    if (this.remaining < length) {
      throw new Error(`Truncated Forge payload: need ${length} bytes, have ${this.remaining}`)
    }
  }
}

function writeVarInt (value) {
  if (!Number.isSafeInteger(value) || value < 0 || value > 0x7fffffff) {
    throw new Error(`Invalid VarInt value: ${value}`)
  }

  const bytes = []
  let remaining = value
  do {
    let byte = remaining & 0x7f
    remaining >>>= 7
    if (remaining !== 0) byte |= 0x80
    bytes.push(byte)
  } while (remaining !== 0)
  return Buffer.from(bytes)
}

function writeString (value) {
  const data = Buffer.from(String(value), 'utf8')
  return Buffer.concat([writeVarInt(data.length), data])
}

function parseLoginWrapper (data) {
  const reader = new BufferReader(data)
  const targetChannel = reader.readString(32767)
  const payloadLength = reader.readVarInt()
  const payload = reader.readBytes(payloadLength)
  if (reader.remaining !== 0) {
    throw new Error(`Forge login wrapper has ${reader.remaining} trailing bytes`)
  }
  return { targetChannel, payload }
}

function buildLoginWrapper (targetChannel, payload) {
  return Buffer.concat([
    writeString(targetChannel),
    writeVarInt(payload.length),
    payload
  ])
}

function readStringList (reader) {
  const count = reader.readVarInt()
  const values = []
  for (let index = 0; index < count; index += 1) {
    values.push(reader.readString(0x100 * 4))
  }
  return values
}

function readChannelMap (reader) {
  const count = reader.readVarInt()
  const values = new Map()
  for (let index = 0; index < count; index += 1) {
    values.set(reader.readString(32767), reader.readString(0x100 * 4))
  }
  return values
}

function parseModData (payload) {
  const reader = new BufferReader(payload)
  const discriminator = reader.readUnsignedByte()
  if (discriminator !== DISCRIMINATORS.S2C_MOD_DATA) {
    throw new Error(`Expected S2C mod-data discriminator, received ${discriminator}`)
  }

  const count = reader.readVarInt()
  const mods = new Map()
  for (let index = 0; index < count; index += 1) {
    const modId = reader.readString(0x100 * 4)
    const displayName = reader.readString(0x100 * 4)
    const version = reader.readString(0x100 * 4)
    mods.set(modId, { displayName, version })
  }
  return mods
}

function parseModList (payload) {
  const reader = new BufferReader(payload)
  const discriminator = reader.readUnsignedByte()
  if (discriminator !== DISCRIMINATORS.S2C_MOD_LIST) {
    throw new Error(`Expected S2C mod-list discriminator, received ${discriminator}`)
  }

  const mods = readStringList(reader)
  const channels = readChannelMap(reader)
  const registries = readStringList(reader)
  const dataPackRegistries = readStringList(reader)

  if (reader.remaining !== 0) {
    throw new Error(`Forge mod-list payload has ${reader.remaining} trailing bytes`)
  }

  return { mods, channels, registries, dataPackRegistries }
}

function buildModListReply ({ mods = DEFAULT_CLIENT_MODS, channels }) {
  const chunks = [
    Buffer.from([DISCRIMINATORS.C2S_MOD_LIST_REPLY]),
    writeVarInt(mods.length)
  ]

  for (const modId of mods) chunks.push(writeString(modId))

  chunks.push(writeVarInt(channels.size))
  for (const [channel, version] of channels) {
    chunks.push(writeString(channel), writeString(version))
  }

  // Forge 47.4.2 accepts an empty client registry-hash map. Registry snapshots
  // arrive in later S2C packets and are acknowledged independently.
  chunks.push(writeVarInt(0))
  return Buffer.concat(chunks)
}

function parseModListReply (payload) {
  const reader = new BufferReader(payload)
  const discriminator = reader.readUnsignedByte()
  if (discriminator !== DISCRIMINATORS.C2S_MOD_LIST_REPLY) {
    throw new Error(`Expected C2S mod-list discriminator, received ${discriminator}`)
  }
  const mods = readStringList(reader)
  const channels = readChannelMap(reader)
  const registries = readChannelMap(reader)
  if (reader.remaining !== 0) {
    throw new Error(`Forge client mod-list payload has ${reader.remaining} trailing bytes`)
  }
  return { mods, channels, registries }
}

function installFml3 (client, {
  logger = console,
  clientMods = DEFAULT_CLIENT_MODS,
  unsupportedChannels = DEFAULT_UNSUPPORTED_CHANNELS
} = {}) {
  if (!client || typeof client.on !== 'function' || typeof client.write !== 'function') {
    throw new TypeError('A minecraft-protocol client is required')
  }
  if (client[INSTALLED]) return client[INSTALLED]

  const state = {
    modData: new Map(),
    mods: [],
    channels: new Map(),
    registries: [],
    dataPackRegistries: [],
    clientMods: [...clientMods],
    clientChannels: new Map(),
    unsupportedChannels: new Set(unsupportedChannels),
    requestsHandled: 0
  }

  const existingTag = client.tagHost || ''
  if (!existingTag.includes(FML3_HOST_MARKER)) {
    client.tagHost = `${existingTag}${FML3_HOST_MARKER}`
  }

  // minecraft-protocol installs a vanilla fallback which immediately rejects
  // every login plugin request. Replace it before the socket can emit connect.
  client.removeAllListeners('login_plugin_request')
  client.on('login_plugin_request', packet => {
    if (packet.channel !== LOGIN_WRAPPER_CHANNEL) {
      client.write('login_plugin_response', { messageId: packet.messageId })
      return
    }

    try {
      const wrapper = parseLoginWrapper(packet.data)
      if (wrapper.targetChannel !== HANDSHAKE_CHANNEL || wrapper.payload.length === 0) {
        logger.warn?.(`[fml3] unsupported login payload target: ${wrapper.targetChannel}`)
        client.write('login_plugin_response', { messageId: packet.messageId })
        return
      }

      const discriminator = wrapper.payload[0]
      state.requestsHandled += 1

      if (discriminator === DISCRIMINATORS.S2C_MOD_DATA) {
        state.modData = parseModData(wrapper.payload)
        logger.info?.(`[fml3] server advertised ${state.modData.size} mod records`)
        return
      }

      if (discriminator === DISCRIMINATORS.S2C_MOD_LIST) {
        const modList = parseModList(wrapper.payload)
        Object.assign(state, modList)
        state.clientChannels = new Map(
          [...modList.channels].filter(([channel]) => !state.unsupportedChannels.has(channel))
        )
        const reply = buildLoginWrapper(
          HANDSHAKE_CHANNEL,
          buildModListReply({ mods: state.clientMods, channels: state.clientChannels })
        )
        client.write('login_plugin_response', {
          messageId: packet.messageId,
          data: reply
        })
        logger.info?.(
          `[fml3] accepted ${modList.mods.length} mods, advertised ` +
          `${state.clientChannels.size}/${modList.channels.size} channels, ` +
          `${modList.registries.length} synced registries`
        )
        client.emit('fml3:mod_list', modList)
        return
      }

      if (
        discriminator === DISCRIMINATORS.S2C_REGISTRY ||
        discriminator === DISCRIMINATORS.S2C_CONFIG_DATA
      ) {
        const acknowledgement = buildLoginWrapper(
          HANDSHAKE_CHANNEL,
          Buffer.from([DISCRIMINATORS.C2S_ACKNOWLEDGE])
        )
        client.write('login_plugin_response', {
          messageId: packet.messageId,
          data: acknowledgement
        })
        return
      }

      if (discriminator === DISCRIMINATORS.S2C_CHANNEL_MISMATCH) {
        logger.error?.('[fml3] Forge reported a mod-channel mismatch')
        return
      }

      logger.warn?.(`[fml3] unsupported handshake discriminator: ${discriminator}`)
      client.write('login_plugin_response', { messageId: packet.messageId })
    } catch (error) {
      logger.error?.(`[fml3] invalid login payload: ${error.message}`)
      client.emit('error', error)
      client.write('login_plugin_response', { messageId: packet.messageId })
    }
  })

  client[INSTALLED] = state
  return state
}

module.exports = {
  DEFAULT_CLIENT_MODS,
  DEFAULT_UNSUPPORTED_CHANNELS,
  DISCRIMINATORS,
  FML3_HOST_MARKER,
  HANDSHAKE_CHANNEL,
  LOGIN_WRAPPER_CHANNEL,
  BufferReader,
  buildLoginWrapper,
  buildModListReply,
  installFml3,
  parseLoginWrapper,
  parseModData,
  parseModList,
  parseModListReply,
  writeString,
  writeVarInt
}
