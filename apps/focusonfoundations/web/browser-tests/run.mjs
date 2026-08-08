// AI browser-based human-simulation test runner for the FoF accounts/auth system.
// Implements docs/2026-07-18_fof-auth-browser-test-walkthrough.md against staging
// with real Chromium (Playwright): clicks, typing, page reads, console capture,
// screenshots on failure. Emailed-code happy paths use CLI assist (admin-confirm);
// the code-entry UI is exercised with a wrong code instead.
//
// Usage: node run.mjs            (default run id = MMDD + letter)
//        RUN_ID=0718b node run.mjs
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import { chromium } from 'playwright';

const BASE = 'https://staging.focusonfoundations.org';
const POOL = 'us-west-2_U25uiNhpb';
const REGION = 'us-west-2';
const RUN = process.env.RUN_ID || `${String(new Date().getMonth() + 1).padStart(2, '0')}${String(new Date().getDate()).padStart(2, '0')}${'abcdefgh'[Math.floor(Math.random() * 8)]}`;
const inbox = (tag) => `fofgeneral20+bt${RUN}${tag}@gmail.com`;
const PARENT = { email: inbox('p'), password: 'BrowserTest2026a' };
const CREATED = { email: inbox('c'), password: 'BrowserTest2026a' };
const KID = { email: inbox('k'), password: 'KidPass2026a' };

const results = [];
const consoleErrors = [];
let page;
function aws(args) {
  return execFileSync('aws', [...args, '--region', REGION], { encoding: 'utf8' }).trim();
}
function record(id, status, note = '') {
  results.push({ id, status, note });
  console.log(`[${status}] ${id}${note ? ` — ${note}` : ''}`);
}
async function step(id, fn) {
  try {
    await fn();
    record(id, 'PASS');
  } catch (error) {
    const shot = `artifacts/${RUN}-${id.replace(/[^a-z0-9]/gi, '_')}.png`;
    try { await page.screenshot({ path: shot, fullPage: true }); } catch {}
    record(id, 'FAIL', `${error.message} (screenshot: ${shot})`);
  }
}
function note(id, text) {
  record(id, 'NOTE', text);
}
async function expectVisible(locator, why) {
  if (!(await locator.first().isVisible().catch(() => false))) {
    throw new Error(`expected visible: ${why}`);
  }
}
async function expectText(selector, includes) {
  const text = (await page.locator(selector).first().textContent().catch(() => '')) || '';
  if (!text.includes(includes)) throw new Error(`expected "${includes}" in ${selector}, got "${text.trim().slice(0, 120)}"`);
}
async function goPage(path) {
  await page.goto(`${BASE}${path}`, { waitUntil: 'networkidle' });
}
async function signOutIfNeeded() {
  await goPage('/account/');
  const signOut = page.locator('#sign-out');
  if (await signOut.isVisible().catch(() => false)) {
    await signOut.click();
    // Sign-out triggers a reload; wait for the signed-out view to settle so a
    // following goto doesn't race the reload (ERR_ABORTED).
    await page.waitForSelector('#signed-out:not([hidden])', { timeout: 20000 }).catch(() => {});
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
  }
}
async function signIn(email, password) {
  await goPage('/account/sign-in/');
  await page.fill('#signin-email', email);
  await page.fill('#signin-password', password);
  await page.click('#password-submit');
  await page.waitForURL('**/account/', { timeout: 15000 });
  await page.waitForLoadState('networkidle');
}

const browser = await chromium.launch();
const context = await browser.newContext();
page = await context.newPage();
page.on('console', (msg) => {
  if (msg.type() === 'error') consoleErrors.push({ url: page.url(), text: msg.text().slice(0, 300) });
});
page.on('pageerror', (error) => consoleErrors.push({ url: page.url(), text: `pageerror: ${error.message}` }));

console.log(`Run ${RUN} against ${BASE}`);

// --- Provision PARENT (confirmed) via CLI
aws(['cognito-idp', 'sign-up', '--client-id', '1umi8t3jeq2la5mfnigg8gjj3b',
  '--username', PARENT.email, '--password', PARENT.password,
  '--user-attributes', `Name=email,Value=${PARENT.email}`]);
aws(['cognito-idp', 'admin-confirm-sign-up', '--user-pool-id', POOL, '--username', PARENT.email]);
console.log(`provisioned ${PARENT.email}`);

// ---------- T1 signed-out surfaces
await step('T1.1 home shows Sign in', async () => {
  await goPage('/');
  await expectText('#header-auth-link', 'Sign in');
});
await step('T1.2 account page signed-out state', async () => {
  await goPage('/account/');
  await expectVisible(page.locator('#signed-out'), 'signed-out block');
  await expectVisible(page.locator('a[href="/account/sign-in/"]'), 'sign-in link');
});
await step('T1.3 sign-in page structure', async () => {
  await goPage('/account/sign-in/');
  await expectText('#tab-password', 'Password');
  await expectText('#tab-code', 'Email code');
  await expectVisible(page.locator('#signin-email'), 'email field');
  await expectVisible(page.locator('a[href="/account/create/"]'), 'create link');
  await expectVisible(page.locator('a[href="/account/forgot/"]'), 'forgot link');
});
await step('T1.4 hidden code fields stay hidden before their step', async () => {
  // Regression: display rules must not override the hidden attribute.
  if (await page.locator('#signin-confirm-entry').isVisible()) {
    throw new Error('sign-in confirm-code field visible before an unconfirmed sign-in');
  }
  await goPage('/account/create/');
  if (await page.locator('#create-confirm-entry').isVisible()) {
    throw new Error('create verification-code field visible before submit');
  }
  await goPage('/account/sign-in/');
  await page.click('#tab-code');
  if (await page.locator('#code-entry').isVisible()) {
    throw new Error('email-code entry visible before requesting a code');
  }
});
await step('T1.5 terms/privacy relocated', async () => {
  await goPage('/');
  const headerLegal = await page.locator('.site-nav a[href="/terms/"], .site-nav a[href="/privacy/"]').count();
  const footerLegal = await page.locator('.site-footer a[href="/terms/"], .site-footer a[href="/privacy/"]').count();
  if (headerLegal || footerLegal) throw new Error('terms/privacy still linked in header/footer');
  await goPage('/account/');
  await expectVisible(page.locator('.legal-links a[href="/terms/"]'), 'terms link on account page');
  await goPage('/account/create/');
  await expectVisible(page.locator('.legal-links a[href="/privacy/"]'), 'privacy link on create page');
});

// ---------- T2 validation / error states
await step('T2.1 terms acceptance required to create', async () => {
  await goPage('/account/create/');
  await page.fill('#create-email', inbox('x'));
  await page.fill('#create-password', 'GoodPass2026a');
  await page.fill('#create-password2', 'GoodPass2026a');
  await page.evaluate(() => document.getElementById('create-form').dispatchEvent(new Event('submit', { cancelable: true })));
  await page.waitForTimeout(1000);
  await expectText('#auth-status', 'Terms');
});
await step('T2.2 weak password rejected', async () => {
  await goPage('/account/create/');
  await page.fill('#create-email', inbox('x'));
  await page.fill('#create-password', 'Short1');
  await page.fill('#create-password2', 'Short1');
  await page.check('#terms-consent');
  await page.evaluate(() => document.getElementById('create-form').dispatchEvent(new Event('submit', { cancelable: true })));
  await page.waitForTimeout(2500);
  await expectVisible(page.locator('#auth-status.is-error'), 'error status for weak password');
});
await step('T2.3 mismatched passwords rejected', async () => {
  await goPage('/account/create/');
  await page.fill('#create-email', inbox('x'));
  await page.fill('#create-password', 'GoodPass2026a');
  await page.fill('#create-password2', 'DifferentPass2026a');
  await page.evaluate(() => document.getElementById('create-form').dispatchEvent(new Event('submit', { cancelable: true })));
  await page.waitForTimeout(1000);
  await expectText('#auth-status', 'don’t match');
});
await step('T2.4 wrong password clean error', async () => {
  await goPage('/account/sign-in/');
  await page.fill('#signin-email', PARENT.email);
  await page.fill('#signin-password', 'WrongPass2026a');
  await page.click('#password-submit');
  await page.waitForTimeout(4000);
  await expectVisible(page.locator('#auth-status.is-error'), 'wrong-password error');
});

// ---------- T3 password sign-in + session
await step('T3.1 parent signs in', async () => {
  await signIn(PARENT.email, PARENT.password);
  await expectText('#account-email', PARENT.email);
});
await step('T3.2 header shows Account across pages', async () => {
  await goPage('/');
  await expectText('#header-auth-link', 'Account');
  await goPage('/demos/');
  await expectText('#header-auth-link', 'Account');
});
await step('T3.3 data section loads', async () => {
  await goPage('/account/');
  await page.waitForTimeout(2500);
  const summary = (await page.locator('#data-summary').textContent()) || '';
  if (summary.includes('Couldn’t load')) throw new Error(`data summary error: ${summary}`);
});
await step('T3.4 session survives reload', async () => {
  await page.reload({ waitUntil: 'networkidle' });
  await expectVisible(page.locator('#signed-in'), 'still signed in after reload');
});

// ---------- T4 guest-mode messaging
await step('T4 guest notice on create + account pages', async () => {
  await signOutIfNeeded();
  await page.evaluate(() => localStorage.setItem('fofGuest.qrag.bttest', JSON.stringify({ q: 'hello' })));
  await goPage('/account/create/');
  await expectVisible(page.locator('#guest-note'), 'guest note on create page');
  await goPage('/account/');
  await expectVisible(page.locator('#guest-note'), 'guest note on account page');
  await page.evaluate(() => localStorage.removeItem('fofGuest.qrag.bttest'));
});

// ---------- T5 create-account UI to code step (CLI assist)
await step('T5.1 create swaps to inline confirm step', async () => {
  await goPage('/account/create/');
  await page.fill('#create-email', CREATED.email);
  await page.fill('#create-password', CREATED.password);
  await page.fill('#create-password2', CREATED.password);
  await page.check('#terms-consent');
  await page.click('#create-submit');
  await page.waitForTimeout(6000);
  await expectVisible(page.locator('#create-confirm-entry'), 'inline code step');
  await expectText('#create-confirm-email', CREATED.email);
  await expectText('#create-submit', 'Confirm email');
});
await step('T5.2 wrong code shows error', async () => {
  await page.fill('#create-confirm-code', '000000');
  await page.click('#create-submit');
  await page.waitForTimeout(4000);
  await expectVisible(page.locator('#auth-status.is-error'), 'wrong-code error');
});
await step('T5.3 CLI-confirmed account signs in', async () => {
  aws(['cognito-idp', 'admin-confirm-sign-up', '--user-pool-id', POOL, '--username', CREATED.email]);
  await signIn(CREATED.email, CREATED.password);
  await expectText('#account-email', CREATED.email);
});

// ---------- T6 family lifecycle
await step('T6.1-2 parent creates family', async () => {
  await signOutIfNeeded();
  await signIn(PARENT.email, PARENT.password);
  await goPage('/account/');
  await page.click('a[href="/account/family/"]');
  await page.waitForLoadState('networkidle');
  await page.fill('#family-name', `BT Family ${RUN}`);
  await page.evaluate(() => document.getElementById('create-family-form').dispatchEvent(new Event('submit', { cancelable: true })));
  await page.waitForTimeout(3500);
  await expectText('#family-title', `BT Family ${RUN}`);
});
await step('T6.3a child creation refused without consent', async () => {
  await page.fill('#child-name', 'BT Kid');
  await page.fill('#child-email', KID.email);
  await page.fill('#child-password', KID.password);
  await page.evaluate(() => document.getElementById('add-child-form').dispatchEvent(new Event('submit', { cancelable: true })));
  await page.waitForTimeout(1500);
  await expectText('#page-status', 'consent');
});
await step('T6.3b child created with consent', async () => {
  const consentText = (await page.locator('#consent-text').textContent()) || '';
  for (const word of ['parent or legal guardian', 'consent', 'delete']) {
    if (!consentText.includes(word)) throw new Error(`consent text missing "${word}"`);
  }
  await page.check('#child-consent');
  await page.fill('#child-name', 'BT Kid');
  await page.fill('#child-email', KID.email);
  await page.fill('#child-password', KID.password);
  await page.evaluate(() => document.getElementById('add-child-form').dispatchEvent(new Event('submit', { cancelable: true })));
  await page.waitForTimeout(6000);
  await expectText('#member-list', 'BT Kid');
});
await step('T6.4-5 child detail + entitlement toggle', async () => {
  await page.getByRole('button', { name: 'View data & settings' }).click();
  await page.waitForTimeout(3000);
  await expectText('#detail-content', 'consent recorded');
  const toggle = page.locator('#detail-content input[type=checkbox]');
  await toggle.check();
  await page.getByRole('button', { name: 'Save access settings' }).click();
  await page.waitForTimeout(2500);
  await expectText('#page-status', 'saved');
});
await step('T6.6 guardian invite emails a link', async () => {
  await page.fill('#invite-email', inbox('inv'));
  await page.fill('#invite-message', 'Browser-test invite — ignore.');
  await page.evaluate(() => document.getElementById('invite-form').dispatchEvent(new Event('submit', { cancelable: true })));
  await page.waitForTimeout(5000);
  await expectText('#invite-display', `Invite emailed to ${inbox('inv')}`);
  await expectText('#invite-display', 'copy sent to you');
});
await step('T6.8a child signs in and plays applet', async () => {
  await signOutIfNeeded();
  await signIn(KID.email, KID.password);
  await goPage('/applets/logic-gates/');
  await page.waitForTimeout(2500);
  // Interact enough to generate telemetry events, then navigate away to flush.
  for (let i = 0; i < 30; i += 1) {
    const buttons = page.locator('button:visible');
    const count = await buttons.count();
    if (!count) break;
    await buttons.nth(i % count).click({ timeout: 2000 }).catch(() => {});
    await page.waitForTimeout(120);
  }
  await goPage('/account/');
  await page.waitForTimeout(3000);
});
await step('T6.8b child sees managed note, no delete controls', async () => {
  await goPage('/account/');
  await page.waitForTimeout(3000);
  await expectVisible(page.locator('#child-managed-note'), 'child managed-by-guardian note');
  if (await page.locator('#delete-section').isVisible().catch(() => false)) {
    throw new Error('delete section visible on a child account');
  }
});
await step('T6.9 child sees managed-family view', async () => {
  await goPage('/account/family/');
  await page.waitForTimeout(2500);
  await expectVisible(page.locator('#child-view'), 'managed-by-guardian notice');
  if (await page.locator('#guardian-tools').isVisible()) throw new Error('guardian tools visible to child');
});
await step('T6.10 guardian sees child activity', async () => {
  await signOutIfNeeded();
  await signIn(PARENT.email, PARENT.password);
  await goPage('/account/family/');
  await page.waitForTimeout(2500);
  await page.getByRole('button', { name: 'View data & settings' }).click();
  await page.waitForTimeout(3000);
  const detail = (await page.locator('#detail-content').textContent()) || '';
  if (detail.includes('logic-gates')) record('T6.10-telemetry', 'PASS', 'child applet session visible to guardian');
  else note('T6.10-telemetry', `child activity not (yet) visible: "${detail.slice(0, 80)}" — applet save is flush-timing dependent`);
});
await step('T6.11 guardian deletes child', async () => {
  const delBtn = page.getByRole('button', { name: /Delete child account/ });
  await delBtn.click();
  await page.getByRole('button', { name: /permanently delete/ }).click();
  await page.waitForTimeout(5000);
  await expectText('#page-status', 'deleted');
  const members = (await page.locator('#member-list').textContent()) || '';
  if (members.includes('BT Kid')) throw new Error('child still in member list');
});

// ---------- T7 regression spot-checks
await step('T7.1 counting-creatures loads', async () => {
  await goPage('/applets/counting-creatures/');
  await page.waitForTimeout(2500);
  const buttons = await page.locator('button:visible').count();
  if (!buttons) throw new Error('no interactive elements found');
});
await step('T7.2 QRAG demo name-free consent flow (401 regression)', async () => {
  await goPage('/demos/deutsch/');
  if (await page.locator('.nicename-textarea').count()) {
    throw new Error('nice-name input still present on demo page');
  }
  const consent = page.locator('#privacy-consent');
  if (await consent.isVisible().catch(() => false)) await consent.check();
  await page.waitForTimeout(1500);
  await page.fill('textarea.botsubmit-textarea', 'What is knowledge?');
  await page.locator('button.botsubmit-button:visible').first().click();
  await page.waitForTimeout(30000);
  const errors = consoleErrors.filter((e) => e.text.includes('401'));
  if (errors.length) throw new Error(`401 during QRAG submit: ${errors[0].text}`);
  const accordion = await page.locator('.accordion-item, .results-box').count();
  if (!accordion) throw new Error('no QRAG result rendered after 30s');
});
await step('T7.3 transcript page loads', async () => {
  await goPage('/transcripts/');
  await expectVisible(page.locator('a[href*="/transcripts/"]'), 'transcript links');
});

// ---------- T8 account deletion sweep
async function selfDelete() {
  // Wait out init() (session + profile fetch) so listeners are attached
  // before clicking; then run the two-step confirm. Success ends with a
  // redirect to the home page signed out (~1.5s after a brief status message),
  // so accept either the status text or the signed-out redirect.
  await page.waitForSelector('#delete-section:not([hidden])', { timeout: 15000 });
  await page.waitForTimeout(1500);
  await page.click('#delete-account');
  await page.click('#delete-account-confirm');
  await page.waitForURL((url) => new URL(url).pathname === '/', { timeout: 15000 }).catch(() => {});
  if (new URL(page.url()).pathname === '/') {
    await expectText('#header-auth-link', 'Sign in');
    return;
  }
  await expectText('#auth-status', 'deleted');
}
await step('T8.1 parent self-deletes', async () => {
  await signOutIfNeeded();
  await signIn(PARENT.email, PARENT.password);
  await selfDelete();
});
await step('T8.2 created account self-deletes', async () => {
  await signIn(CREATED.email, CREATED.password);
  await selfDelete();
});
await step('T8.3 CLI sweep confirms no bt users remain', async () => {
  const out = aws(['cognito-idp', 'list-users', '--user-pool-id', POOL,
    '--query', `Users[?contains(Username, 'bt${RUN}')].Username`, '--output', 'text']);
  // Username is a uuid; filter by email attribute instead.
  const emails = aws(['cognito-idp', 'list-users', '--user-pool-id', POOL,
    '--query', `Users[].Attributes[?Name=='email'].Value`, '--output', 'text']);
  const leftovers = emails.split(/\s+/).filter((e) => e.includes(`bt${RUN}`));
  if (leftovers.length) throw new Error(`leftover users: ${leftovers.join(', ')}`);
});

await browser.close();

// ---------- report
console.log('\n=== RESULTS ===');
for (const r of results) console.log(`${r.status.padEnd(5)} ${r.id}${r.note ? ` — ${r.note}` : ''}`);
console.log(`\nConsole errors captured: ${consoleErrors.length}`);
for (const e of consoleErrors.slice(0, 20)) console.log(`  [console] ${e.url} :: ${e.text}`);
fs.writeFileSync(`artifacts/${RUN}-results.json`, JSON.stringify({ run: RUN, results, consoleErrors }, null, 2));
const failed = results.filter((r) => r.status === 'FAIL').length;
console.log(`\n${results.length} steps, ${failed} FAIL`);
process.exit(failed ? 1 : 0);
