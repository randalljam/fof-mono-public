'use strict'

const path = require('node:path')

const APP_ROOT = path.resolve(__dirname, '..')

const DEFAULTS = Object.freeze({
  host: '127.0.0.1',
  port: 25565,
  version: '1.20.1',
  username: 'MineflayerBot',
  controllerUsername: '',
  auth: 'offline',
  profilesFolder: path.join(APP_ROOT, '.profiles'),
  smokeTimeoutMs: 0,
  pingTimeoutMs: 5000
})

const FLAG_NAMES = Object.freeze({
  '--host': 'host',
  '--port': 'port',
  '--version': 'version',
  '--username': 'username',
  '--controller': 'controllerUsername',
  '--auth': 'auth',
  '--profiles-folder': 'profilesFolder',
  '--smoke-timeout-ms': 'smokeTimeoutMs',
  '--ping-timeout-ms': 'pingTimeoutMs'
})

function parseArgs (argv) {
  const values = {}

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]
    if (argument === '--help' || argument === '-h') {
      values.help = true
      continue
    }

    const equalsIndex = argument.indexOf('=')
    const flag = equalsIndex === -1 ? argument : argument.slice(0, equalsIndex)
    const key = FLAG_NAMES[flag]
    if (!key) {
      throw new Error(`Unknown argument: ${argument}`)
    }

    let value
    if (equalsIndex === -1) {
      index += 1
      value = argv[index]
      if (value === undefined || value.startsWith('--')) {
        throw new Error(`Missing value for ${flag}`)
      }
    } else {
      value = argument.slice(equalsIndex + 1)
      if (value === '') {
        throw new Error(`Missing value for ${flag}`)
      }
    }
    values[key] = value
  }

  return values
}

function readValue (cliValues, env, key, envName) {
  if (cliValues[key] !== undefined) return cliValues[key]
  if (env[envName] !== undefined && env[envName] !== '') return env[envName]
  return DEFAULTS[key]
}

function parseInteger (value, label, minimum, maximum) {
  const text = String(value)
  if (!/^\d+$/.test(text)) {
    throw new Error(`${label} must be an integer`)
  }

  const parsed = Number(text)
  if (!Number.isSafeInteger(parsed) || parsed < minimum || parsed > maximum) {
    throw new Error(`${label} must be between ${minimum} and ${maximum}`)
  }
  return parsed
}

function requireText (value, label) {
  const text = String(value).trim()
  if (text === '') throw new Error(`${label} must not be empty`)
  return text
}

function loadConfig ({ argv = process.argv.slice(2), env = process.env } = {}) {
  const cliValues = parseArgs(argv)
  const auth = requireText(
    readValue(cliValues, env, 'auth', 'MINEFLAYER_AUTH'),
    'auth'
  ).toLowerCase()

  if (!['offline', 'microsoft'].includes(auth)) {
    throw new Error('auth must be either "offline" or "microsoft"')
  }

  const username = requireText(
    readValue(cliValues, env, 'username', 'MINEFLAYER_USERNAME'),
    'username'
  )
  const controllerValue = String(
    readValue(cliValues, env, 'controllerUsername', 'MINEFLAYER_CONTROLLER')
  ).trim()
  const controllerUsername = controllerValue === '' ? null : controllerValue
  if (controllerUsername && !/^[A-Za-z0-9_]{1,16}$/.test(controllerUsername)) {
    throw new Error('controller must be a valid Minecraft Java username')
  }
  if (controllerUsername && controllerUsername.toLowerCase() === username.toLowerCase()) {
    throw new Error('controller must be different from the bot username')
  }

  return Object.freeze({
    host: requireText(readValue(cliValues, env, 'host', 'MINEFLAYER_HOST'), 'host'),
    port: parseInteger(
      readValue(cliValues, env, 'port', 'MINEFLAYER_PORT'),
      'port',
      1,
      65535
    ),
    version: requireText(
      readValue(cliValues, env, 'version', 'MINEFLAYER_VERSION'),
      'version'
    ),
    username,
    controllerUsername,
    auth,
    profilesFolder: path.resolve(requireText(
      readValue(cliValues, env, 'profilesFolder', 'MINEFLAYER_PROFILES_FOLDER'),
      'profiles folder'
    )),
    smokeTimeoutMs: parseInteger(
      readValue(cliValues, env, 'smokeTimeoutMs', 'MINEFLAYER_SMOKE_TIMEOUT_MS'),
      'smoke timeout',
      0,
      86_400_000
    ),
    pingTimeoutMs: parseInteger(
      readValue(cliValues, env, 'pingTimeoutMs', 'MINEFLAYER_PING_TIMEOUT_MS'),
      'ping timeout',
      1,
      120_000
    ),
    help: cliValues.help === true
  })
}

module.exports = {
  APP_ROOT,
  DEFAULTS,
  loadConfig,
  parseArgs
}
