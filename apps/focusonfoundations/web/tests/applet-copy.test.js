import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const webRoot = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..');

function runSync() {
  execFileSync(process.execPath, ['scripts/sync-applet-copy.js', '--applet', 'all'], { cwd: webRoot, stdio: 'pipe' });
}

test('copy markdown syncs to generated modules without drift', () => {
  const before = {
    logic: fs.readFileSync(path.join(webRoot, 'src/lib/logic-gates-copy.js'), 'utf8'),
    counting: fs.readFileSync(path.join(webRoot, 'src/lib/counting-creatures-copy.js'), 'utf8'),
  };
  runSync();
  const afterLogic = fs.readFileSync(path.join(webRoot, 'src/lib/logic-gates-copy.js'), 'utf8');
  const afterCounting = fs.readFileSync(path.join(webRoot, 'src/lib/counting-creatures-copy.js'), 'utf8');
  assert.equal(afterLogic, before.logic);
  assert.equal(afterCounting, before.counting);
});

test('logic gates copy has one screen per navigation dot', async () => {
  const { SCREENS, STEP_INTROS } = await import('../src/lib/logic-gates-copy.js');
  assert.equal(SCREENS.length, 21);
  assert.equal(STEP_INTROS.length, 21);
  assert.ok(SCREENS.every((s) => s.speak));
});

test('counting creatures copy has one screen per navigation dot', async () => {
  const { SCREENS, STEP_INTROS } = await import('../src/lib/counting-creatures-copy.js');
  assert.equal(SCREENS.length, 13);
  assert.equal(STEP_INTROS.length, 13);
  assert.ok(SCREENS.every((s) => s.speak));
});
