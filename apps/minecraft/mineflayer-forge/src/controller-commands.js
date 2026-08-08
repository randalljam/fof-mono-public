'use strict'

const MAX_LOGS_PER_TASK = 64

function normalize (value) {
  return String(value)
    .trim()
    .toLowerCase()
    .replace(/[,:;.!?]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function parseControllerCommand (message, botName) {
  const normalizedMessage = normalize(message)
  const normalizedName = normalize(botName)
  if (!normalizedName || !normalizedMessage.startsWith(`${normalizedName} `)) return null

  const instruction = normalizedMessage.slice(normalizedName.length + 1)

  if (instruction === 'help') return { type: 'help' }
  if (instruction === 'follow me') return { type: 'follow' }
  if (['stop', 'stop following me', 'stop follow'].includes(instruction)) {
    return { type: 'stop' }
  }

  const collectMatch = instruction.match(
    /^(?:chop|collect|get) (\d+) logs?(?: and (?:bring|deliver) (?:them )?(?:back )?to me)?$/
  )
  if (collectMatch) {
    const count = Number(collectMatch[1])
    if (!Number.isSafeInteger(count) || count < 1 || count > MAX_LOGS_PER_TASK) {
      return {
        type: 'invalid',
        message: `Log count must be between 1 and ${MAX_LOGS_PER_TASK}.`
      }
    }
    return { type: 'collect_logs', count }
  }

  return {
    type: 'invalid',
    message: `Try "${botName} follow me", "${botName} stop", or ` +
      `"${botName} chop 10 logs and bring them back to me".`
  }
}

module.exports = {
  MAX_LOGS_PER_TASK,
  normalize,
  parseControllerCommand
}
