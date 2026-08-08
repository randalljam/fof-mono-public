'use strict'

const opaquePayload = 'restBuffer'
const INSTALLED = Symbol('fof.forgePacketAdapters.installed')

// Forge extends both payloads with registry-driven types that vanilla
// minecraft-data cannot decode. They are nonessential to stationary bot
// operation, so consume them atomically instead of partially decoding them.
const FORGE_CUSTOM_PACKETS = Object.freeze({
  '1.20': {
    play: {
      toClient: {
        types: {
          packet_declare_recipes: opaquePayload,
          packet_declare_commands: opaquePayload
        }
      }
    }
  }
})

function installForgePacketAdapters (client) {
  if (!client || typeof client.prependListener !== 'function') {
    throw new TypeError('A minecraft-protocol client is required')
  }
  if (client[INSTALLED]) return

  // minecraft-protocol's secure-chat helper walks the command tree. Give it
  // a valid empty tree after the Forge-specific bytes have been consumed.
  client.prependListener('declare_commands', packet => {
    if (!Buffer.isBuffer(packet)) return
    packet.nodes = [{ children: [] }]
    packet.rootIndex = 0
  })

  client[INSTALLED] = true
}

module.exports = {
  FORGE_CUSTOM_PACKETS,
  installForgePacketAdapters
}
