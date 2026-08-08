import { defineConfig } from '@playwright/test';
import { existsSync } from 'node:fs';

// Resolve a Chromium binary. Preference order:
// 1. PLAYWRIGHT_CHROMIUM_PATH env var (manual override)
// 2. A browser installed via `npx playwright install chromium`
// 3. The npm-packaged @sparticuz/chromium binary (linux x64 only — used in
//    sandboxed/CI environments where Playwright's browser CDN is blocked)
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
const slowMo = Number.parseInt(process.env.PLAYWRIGHT_SLOW_MO_MS || '0', 10);

export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  fullyParallel: true,
  workers: 3,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list']],
  use: {
    // Dedicated e2e port — deliberately NOT 8907 (dev_server.py's default ANCHOR_PORT). With
    // reuseExistingServer, a dev_server left running on 8907 would be reused instead of the
    // hermetic static server below; its /api/latest-user-db answers (200 {found:false}) make
    // Continue-mode Start block ("No file… to continue"), which a plain http.server avoids by
    // 404ing. A separate port keeps the suite hermetic regardless of what's on 8907.
    baseURL: 'http://127.0.0.1:8917',
    launchOptions: {
      executablePath,
      slowMo: Number.isFinite(slowMo) ? slowMo : 0,
      args: ['--no-sandbox', '--disable-dev-shm-usage']
    }
  },
  webServer: {
    // Serve apps/math-quiz statically; the app is plain HTML/JS with no build step
    command: 'python3 -m http.server 8917 --bind 127.0.0.1 --directory ..',
    url: 'http://127.0.0.1:8917/math_quiz.html',
    reuseExistingServer: true,
    timeout: 15_000
  }
});
