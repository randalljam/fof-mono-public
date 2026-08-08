#!/usr/bin/env node
'use strict'

const { loadConfig } = require('./config')
const { runBot } = require('./lifecycle')

const HELP = `Usage: npm run bot -- [options]

Options:
  --host HOST                 Server host (default: 127.0.0.1)
  --port PORT                 Server port (default: 25565)
  --version VERSION           Minecraft version (default: 1.20.1)
  --username NAME             Offline name or Microsoft profile identifier
  --controller NAME           Only player allowed to issue in-game bot commands
  --auth MODE                 offline (default) or microsoft
  --profiles-folder PATH      Microsoft authentication cache directory
  --smoke-timeout-ms MS       Disconnect after this many ms; 0 disables it
  -h, --help                  Show this help
`

async function main () {
  const config = loadConfig()
  if (config.help) {
    process.stdout.write(HELP)
    return
  }

  const session = runBot(config)
  const handleSignal = (signal) => session.stop(signal.toLowerCase())
  const onSigint = () => handleSignal('SIGINT')
  const onSigterm = () => handleSignal('SIGTERM')
  process.once('SIGINT', onSigint)
  process.once('SIGTERM', onSigterm)

  const result = await session.done
  process.removeListener('SIGINT', onSigint)
  process.removeListener('SIGTERM', onSigterm)

  if (
    result.hadError ||
    result.wasKicked ||
    (result.stopCause === 'smoke-timeout' && !result.spawned)
  ) {
    process.exitCode = 1
  }
}

if (require.main === module) {
  main().catch((error) => {
    console.error(`[bot] fatal: ${error.stack || error.message}`)
    process.exitCode = 1
  })
}

module.exports = { HELP, main }
