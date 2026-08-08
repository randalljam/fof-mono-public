import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {
  addHtmlBaseHref,
  assertKeyInsidePrefix,
  classifyDiff,
  confirmationPhrase,
  contentHeaders,
  inventoryLocalFiles,
  localFilesToObjects,
  parseArgs,
  remoteObjectMatches,
  validateAllowEntry,
  validateSlug,
} from '../scripts/deploy-static-page.js';

function digest(contents) {
  const buffer = Buffer.from(contents);
  return {
    sha256Hex: createHash('sha256').update(buffer).digest('hex'),
    sha256Base64: createHash('sha256').update(buffer).digest('base64'),
    md5Hex: createHash('md5').update(buffer).digest('hex'),
  };
}

function localObject(key, contents) {
  return { key, relativePath: key.split('/').at(-1), ...digest(contents) };
}

test('parseArgs requires source, a safe slug, explicit allowlist entries, and a matching optional base href', () => {
  assert.deepEqual(
    parseArgs([
      '--source', 'dist/page',
      '--slug', 'applets/my-page',
      '--allow', 'index.html',
      '--allow', 'assets',
      '--base-href', '/applets/my-page/',
      '--no-delete',
    ]),
    {
      source: 'dist/page',
      slug: 'applets/my-page',
      allow: ['index.html', 'assets'],
      baseHref: '/applets/my-page/',
      noDelete: true,
    },
  );
  assert.equal(parseArgs(['--source', 'dist', '--slug', 'page', '--allow', 'index.html']).noDelete, false);
  assert.throws(() => parseArgs(['--source', 'dist', '--slug', 'page']), /At least one explicit --allow/);
  assert.throws(() => parseArgs(['--slug', 'page', '--allow', 'index.html']), /--source is required/);
  assert.throws(() => parseArgs(['--source', 'dist', '--allow', 'index.html']), /--slug is required/);
  assert.throws(() => parseArgs(['--source', 'dist', '--slug', 'page', '--allow', 'x', '--staging', 'yes']), /Unknown argument/);
  assert.throws(
    () => parseArgs(['--source', 'dist', '--slug', 'page', '--allow', 'index.html', '--base-href', '/other/']),
    /must exactly match/,
  );
});

test('slug validation rejects ambiguous or escaping URL prefixes', () => {
  assert.equal(validateSlug('applets/counting-creatures'), 'applets/counting-creatures');
  for (const unsafe of [
    '',
    '/',
    '/applets/page',
    'applets/page/',
    'applets//page',
    'applets/../page',
    'applets\\page',
    'applets/Page',
    'applets/page?draft=1',
    'applets/page#section',
  ]) {
    assert.throws(() => validateSlug(unsafe));
  }
  assert.equal(confirmationPhrase('applets/page'), 'DEPLOY applets/page TO PRODUCTION');
});

test('allowlist validation rejects absolute, traversal, and non-normalized entries', () => {
  assert.equal(validateAllowEntry('assets/app.js'), 'assets/app.js');
  for (const unsafe of ['', '.', '..', '../outside', 'assets/../index.html', '/tmp/file', 'assets/', 'assets\\app.js']) {
    assert.throws(() => validateAllowEntry(unsafe));
  }
});

test('local inventory recursively includes only allowlisted regular files', (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'fof-page-deploy-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  fs.mkdirSync(path.join(root, 'assets'));
  fs.writeFileSync(path.join(root, 'index.html'), '<h1>Page</h1>');
  fs.writeFileSync(path.join(root, 'assets', 'app.js'), 'console.log("page");');
  fs.writeFileSync(path.join(root, 'not-allowed.txt'), 'secret');

  const files = inventoryLocalFiles(root, ['index.html', 'assets']);

  assert.deepEqual(files.map((file) => file.relativePath), ['assets/app.js', 'index.html']);
  assert.equal(files[0].sha256Hex, digest('console.log("page");').sha256Hex);
  assert.deepEqual(
    localFilesToObjects(files, 'applets/page').map((file) => file.key),
    ['applets/page/assets/app.js', 'applets/page/index.html'],
  );
});

test('base href adaptation changes only deployed index contents and leaves source untouched', (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'fof-page-deploy-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const sourceHtml = '<!doctype html><html><head><title>Page</title></head><body></body></html>';
  fs.writeFileSync(path.join(root, 'index.html'), sourceHtml);
  const files = inventoryLocalFiles(root, ['index.html']);

  const adapted = addHtmlBaseHref(files, '/bestiary/');

  assert.match(adapted[0].uploadContents.toString(), /<head>\n  <base href="\/bestiary\/">/);
  assert.notEqual(adapted[0].sha256Hex, files[0].sha256Hex);
  assert.equal(fs.readFileSync(path.join(root, 'index.html'), 'utf8'), sourceHtml);
  assert.throws(
    () => addHtmlBaseHref([{ ...files[0], relativePath: 'page.html' }], '/bestiary/'),
    /requires an allowlisted index.html/,
  );
});

test('local inventory rejects symlinks even when they point inside source', (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'fof-page-deploy-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  fs.mkdirSync(path.join(root, 'real'));
  fs.writeFileSync(path.join(root, 'target.txt'), 'target');
  fs.writeFileSync(path.join(root, 'real', 'nested.txt'), 'nested');
  fs.symlinkSync(path.join(root, 'target.txt'), path.join(root, 'linked.txt'));
  fs.symlinkSync(path.join(root, 'real'), path.join(root, 'linked-directory'));

  assert.throws(() => inventoryLocalFiles(root, ['linked.txt']), /Symlinks are not allowed/);
  assert.throws(() => inventoryLocalFiles(root, ['linked-directory/nested.txt']), /Symlinks are not allowed/);
});

test('prefix invariant allows its marker and rejects sibling or traversal keys', () => {
  assert.doesNotThrow(() => assertKeyInsidePrefix('applets/page/index.html', 'applets/page/'));
  assert.doesNotThrow(() => assertKeyInsidePrefix('applets/page/', 'applets/page/'));
  assert.throws(() => assertKeyInsidePrefix('applets/page-other/index.html', 'applets/page/'), /INVARIANT/);
  assert.throws(() => assertKeyInsidePrefix('applets/page/../other.html', 'applets/page/'), /INVARIANT/);
});

test('remote matching prefers SHA256 checksum, then metadata, then non-multipart ETag', () => {
  const local = localObject('applets/page/index.html', 'same');
  assert.equal(remoteObjectMatches(local, { checksumSHA256: local.sha256Base64 }), true);
  assert.equal(
    remoteObjectMatches(local, { checksumSHA256: digest('different').sha256Base64, metadata: { sha256: local.sha256Hex } }),
    false,
  );
  assert.equal(remoteObjectMatches(local, { metadata: { sha256: local.sha256Hex } }), true);
  assert.equal(remoteObjectMatches(local, { etag: `"${local.md5Hex}"` }), true);
  assert.equal(remoteObjectMatches(local, { etag: `"${local.md5Hex}-2"` }), false);
  assert.equal(remoteObjectMatches(local, {}), false);
});

test('diff classifies additions, content changes, deletions, and unchanged files', () => {
  const prefix = 'applets/page/';
  const added = localObject(`${prefix}added.js`, 'added');
  const changed = localObject(`${prefix}changed.css`, 'new');
  const unchanged = localObject(`${prefix}index.html`, 'same');
  const remote = [
    { key: changed.key, checksumSHA256: digest('old').sha256Base64 },
    { key: unchanged.key, metadata: { sha256: unchanged.sha256Hex } },
    { key: `${prefix}stale.png`, etag: '"0123456789abcdef0123456789abcdef"' },
  ];

  const diff = classifyDiff([added, changed, unchanged], remote, prefix);

  assert.deepEqual(diff.additions.map((item) => item.key), [added.key]);
  assert.deepEqual(diff.changes.map((item) => item.key), [changed.key]);
  assert.deepEqual(diff.deletions.map((item) => item.key), [`${prefix}stale.png`]);
  assert.deepEqual(diff.unchanged.map((item) => item.key), [unchanged.key]);
  assert.deepEqual(diff.keptRemote, []);
});

test('no-delete keeps remote extras instead of deleting them', () => {
  const prefix = 'bestiary/';
  const local = localObject(`${prefix}index.html`, 'new');
  const remote = [
    { key: local.key, checksumSHA256: digest('old').sha256Base64 },
    { key: `${prefix}assets/pages/materials_0.png`, etag: '"0123456789abcdef0123456789abcdef"' },
    { key: `${prefix}bestiary-manifest.json`, etag: '"fedcba9876543210fedcba9876543210"' },
  ];

  const diff = classifyDiff([local], remote, prefix, { noDelete: true });

  assert.deepEqual(diff.changes.map((item) => item.key), [local.key]);
  assert.deepEqual(diff.deletions, []);
  assert.deepEqual(
    diff.keptRemote.map((item) => item.key),
    [`${prefix}assets/pages/materials_0.png`, `${prefix}bestiary-manifest.json`],
  );
});

test('diff aborts if either inventory contains an out-of-prefix key', () => {
  const local = localObject('applets/page/index.html', 'same');
  assert.throws(
    () => classifyDiff([local], [{ key: 'applets/other/index.html' }], 'applets/page/'),
    /DEPLOY SCOPE INVARIANT VIOLATION/,
  );
});

test('content headers keep executable and data files fresh while caching PNGs', () => {
  assert.deepEqual(contentHeaders('index.html'), {
    contentType: 'text/html; charset=utf-8',
    cacheControl: 'max-age=0,no-cache,no-store,must-revalidate',
  });
  for (const file of ['style.css', 'app.js', 'module.mjs', 'manifest.json']) {
    assert.equal(contentHeaders(file).cacheControl, 'max-age=0,no-cache,no-store,must-revalidate');
  }
  assert.deepEqual(contentHeaders('image.png'), {
    contentType: 'image/png',
    cacheControl: 'public,max-age=86400',
  });
});
