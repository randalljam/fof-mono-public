'use strict'

const { loadConfig } = require('./config')

const HELP = `Usage: npm run ping -- [options]

Options:
  --host HOST                 Server host (default: 127.0.0.1)
  --port PORT                 Server port (default: 25565)
  --version VERSION           Minecraft version (default: 1.20.1)
  --ping-timeout-ms MS        Fail after this many ms (default: 5000)
  -h, --help                  Show this help
`

async function pingServer (config, dependencies = {}) {
  const ping = dependencies.ping || require('minecraft-protocol').ping
  return ping({
    host: config.host,
    port: config.port,
    version: config.version,
    closeTimeout: config.pingTimeoutMs,
    noPongTimeout: Math.min(config.pingTimeoutMs, 5000)
  })
}

async function main () {
  const config = loadConfig()
  if (config.help) {
    process.stdout.write(HELP)
    return
  }

  console.error(
    `[ping] requesting Minecraft status from ${config.host}:${config.port} ` +
    `(protocol ${config.version})`
  )
  const status = await pingServer(config)
  process.stdout.write(`${JSON.stringify(status, null, 2)}\n`)
}

if (require.main === module) {
  main().catch((error) => {
    console.error(`[ping] failed: ${error.stack || error.message}`)
    process.exitCode = 1
  })
}

module.exports = { HELP, main, pingServer }
