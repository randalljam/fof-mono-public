// Playwright config for the dragon-game FULL browser playthrough — deliberately
// separate from the default e2e suite (playwright.config.mjs): this is a long
// (~10-25 min) apparatus run against the real dev server (dragon needs the
// /api/latest-user-db + /api/save-run pipeline), not a CI-style test.
// Run: cd apps/math-quiz/tests && npm run test:playthrough
import { defineConfig } from '@playwright/test';
import { existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const testsDir = path.dirname(fileURLToPath(import.meta.url));
const appDir = path.dirname(testsDir);
// Server data sandbox: gitignored, wiped + re-seeded by the spec. NEVER tlkids.
export const SERVER_DATA_DIR = path.join(appDir, 'dragon', 'playtests', 'runs', 'browser-server-data');
export const PLAYTHROUGH_PORT = 8935;

async function resolveExecutablePath() {
  if (process.env.PLAYWRIGHT_CHROMIUM_PATH) return process.env.PLAYWRIGHT_CHROMIUM_PATH;
  try {
    const { chromium } = await import('playwright-core');
    const p = chromium.executablePath();
    if (p && existsSync(p)) return p;
  } catch { /* fall through */ }
  if (process.platform === 'linux') {
    const sparticuz = (await import('@sparticuz/chromium')).default;
    return await sparticuz.executablePath();
  }
  throw new Error('No Chromium found: run `npx playwright install chromium` or set PLAYWRIGHT_CHROMIUM_PATH');
}

const executablePath = await resolveExecutablePath();
mkdirSync(SERVER_DATA_DIR, { recursive: true });

export default defineConfig({
  testDir: './e2e_playthrough',
  timeout: 45 * 60_000,          // one full game arc in a single test
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: `http://127.0.0.1:${PLAYTHROUGH_PORT}`,
    viewport: { width: 1280, height: 800 },
    launchOptions: {
      executablePath,
      args: ['--no-sandbox', '--disable-dev-shm-usage'],
    },
  },
  webServer: {
    command: 'python3 ../tools/dev_server.py',
    cwd: testsDir,
    url: `http://127.0.0.1:${PLAYTHROUGH_PORT}/api/data-folders`,
    reuseExistingServer: false,
    timeout: 20_000,
    env: {
      ANCHOR_PORT: String(PLAYTHROUGH_PORT),
      ANCHOR_BIND: '127.0.0.1',
      ANCHOR_DATA_DIR: SERVER_DATA_DIR,
      ANCHOR_BACKUP_DIR: path.join(SERVER_DATA_DIR, '_backup'),
      ANCHOR_S3_DISABLE: '1',
      ANCHOR_PREVENT_SLEEP: '0',
    },
  },
});
