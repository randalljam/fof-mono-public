#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import readline from 'node:readline/promises';
import { fileURLToPath } from 'node:url';

const EXPECTED_AWS_ACCOUNT = '[AWS-ACCOUNT-ID]';
const NO_CACHE = 'max-age=0,no-cache,no-store,must-revalidate';
const CACHEABLE = 'public,max-age=86400';
const RED = '\u001b[1;31m';
const RESET = '\u001b[0m';
const webRoot = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..');
const deployConfigPath = path.join(webRoot, 'deploy-config.json');

export function usage() {
  return [
    'Usage:',
    '  node scripts/deploy-static-page.js --source <directory> --slug <url-prefix> --allow <entry> [--allow <entry> ...] [--base-href </url-prefix/>] [--no-delete]',
    '',
    'Example:',
    '  node scripts/deploy-static-page.js --source dist/applets/counting-creatures --slug applets/counting-creatures --allow index.html --allow assets --base-href /applets/counting-creatures/',
    '',
    'Partial update (leave other remote keys under the slug untouched):',
    '  node scripts/deploy-static-page.js --source /path/to/page --slug bestiary --allow index.html --allow bestiary.css --allow bestiary.js --base-href /bestiary/ --no-delete',
    '',
    'The source entries are relative to --source and are uploaded beneath the production-only slug.',
    'Without --no-delete, remote keys under the slug that are not in the allowlist are reported as deletions.',
  ].join('\n');
}

export function validateSlug(value) {
  if (typeof value !== 'string' || value.length === 0) {
    throw new Error('--slug is required.');
  }
  if (
    value.startsWith('/') ||
    value.endsWith('/') ||
    value.includes('\\') ||
    value.includes('//') ||
    value.includes('?') ||
    value.includes('#')
  ) {
    throw new Error(`Unsafe slug "${value}". Use a relative URL prefix without leading/trailing slashes.`);
  }
  const segments = value.split('/');
  if (segments.some((segment) => !/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(segment))) {
    throw new Error(`Unsafe slug "${value}". Use lowercase letters, numbers, hyphens, and single slashes.`);
  }
  return value;
}

export function validateAllowEntry(value) {
  if (typeof value !== 'string' || value.length === 0) {
    throw new Error('Every --allow value must be a non-empty source-relative path.');
  }
  if (path.isAbsolute(value) || value.includes('\\')) {
    throw new Error(`Unsafe allowlist entry "${value}". Entries must be relative and use "/" separators.`);
  }
  const normalized = path.posix.normalize(value);
  if (
    normalized === '.' ||
    normalized === '..' ||
    normalized.startsWith('../') ||
    normalized !== value ||
    value.endsWith('/')
  ) {
    throw new Error(`Unsafe allowlist entry "${value}". Traversal and non-normalized paths are not allowed.`);
  }
  return value;
}

export function parseArgs(argv) {
  if (argv.includes('--help') || argv.includes('-h')) return { help: true };
  const parsed = { allow: [], noDelete: false };
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index];
    if (flag === '--no-delete') {
      parsed.noDelete = true;
      continue;
    }
    if (!['--source', '--slug', '--allow', '--base-href'].includes(flag)) {
      throw new Error(`Unknown argument "${flag}".\n${usage()}`);
    }
    const value = argv[index + 1];
    if (!value || value.startsWith('--')) {
      throw new Error(`${flag} requires a value.`);
    }
    index += 1;
    if (flag === '--allow') parsed.allow.push(validateAllowEntry(value));
    else if (flag === '--source') {
      if (parsed.source) throw new Error('--source may only be provided once.');
      parsed.source = value;
    } else if (flag === '--slug') {
      if (parsed.slug) throw new Error('--slug may only be provided once.');
      parsed.slug = validateSlug(value);
    } else {
      if (parsed.baseHref) throw new Error('--base-href may only be provided once.');
      parsed.baseHref = value;
    }
  }
  if (!parsed.source) throw new Error('--source is required.');
  if (!parsed.slug) throw new Error('--slug is required.');
  if (parsed.allow.length === 0) throw new Error('At least one explicit --allow entry is required.');
  if (parsed.baseHref && parsed.baseHref !== `/${parsed.slug}/`) {
    throw new Error(`--base-href must exactly match the deployed slug: /${parsed.slug}/`);
  }
  return parsed;
}

function isInside(parent, candidate) {
  const relative = path.relative(parent, candidate);
  return relative !== '..' && !relative.startsWith(`..${path.sep}`) && !path.isAbsolute(relative);
}

export function inventoryLocalFiles(sourceDirectory, allowEntries) {
  const source = path.resolve(sourceDirectory);
  const sourceStat = fs.lstatSync(source);
  if (sourceStat.isSymbolicLink()) throw new Error(`Source directory may not be a symlink: ${source}`);
  if (!sourceStat.isDirectory()) throw new Error(`Source is not a directory: ${source}`);
  const sourceReal = fs.realpathSync(source);
  const files = new Map();

  function rejectSymlinkComponents(candidate) {
    const relative = path.relative(source, candidate);
    let current = source;
    for (const segment of relative.split(path.sep).filter(Boolean)) {
      current = path.join(current, segment);
      if (fs.lstatSync(current).isSymbolicLink()) {
        throw new Error(`Symlinks are not allowed in deploy sources: ${current}`);
      }
    }
  }

  function visit(candidate) {
    if (!isInside(source, candidate)) {
      throw new Error(`Allowlisted path escapes the source directory: ${candidate}`);
    }
    const stat = fs.lstatSync(candidate);
    if (stat.isSymbolicLink()) throw new Error(`Symlinks are not allowed in deploy sources: ${candidate}`);
    if (stat.isDirectory()) {
      for (const entry of fs.readdirSync(candidate, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
        visit(path.join(candidate, entry.name));
      }
      return;
    }
    if (!stat.isFile()) throw new Error(`Only regular files and directories may be allowlisted: ${candidate}`);
    const real = fs.realpathSync(candidate);
    if (!isInside(sourceReal, real)) throw new Error(`Source file escapes the source directory: ${candidate}`);
    const relativePath = path.relative(source, candidate).split(path.sep).join('/');
    const contents = fs.readFileSync(candidate);
    files.set(relativePath, {
      absolutePath: candidate,
      relativePath,
      size: stat.size,
      sha256Hex: createHash('sha256').update(contents).digest('hex'),
      sha256Base64: createHash('sha256').update(contents).digest('base64'),
      md5Hex: createHash('md5').update(contents).digest('hex'),
    });
  }

  for (const entry of allowEntries) {
    validateAllowEntry(entry);
    const candidate = path.resolve(source, ...entry.split('/'));
    if (!isInside(source, candidate)) throw new Error(`Allowlisted path escapes the source directory: ${entry}`);
    rejectSymlinkComponents(candidate);
    visit(candidate);
  }
  if (files.size === 0) throw new Error('The allowlist contains no files to deploy.');
  return [...files.values()].sort((a, b) => a.relativePath.localeCompare(b.relativePath));
}

export function keyPrefixForSlug(slug) {
  return `${validateSlug(slug)}/`;
}

export function assertKeyInsidePrefix(key, prefix) {
  if (
    typeof key !== 'string' ||
    !key.startsWith(prefix) ||
    key.includes('\\') ||
    key.split('/').includes('..')
  ) {
    throw new Error(`DEPLOY SCOPE INVARIANT VIOLATION: key "${key}" is outside prefix "${prefix}"`);
  }
}

export function localFilesToObjects(localFiles, slug) {
  const prefix = keyPrefixForSlug(slug);
  return localFiles.map((file) => {
    const key = `${prefix}${file.relativePath}`;
    assertKeyInsidePrefix(key, prefix);
    return { ...file, key };
  });
}

export function addHtmlBaseHref(localFiles, baseHref) {
  if (!baseHref) return localFiles;
  const index = localFiles.find((file) => file.relativePath === 'index.html');
  if (!index) throw new Error('--base-href requires an allowlisted index.html.');
  const html = fs.readFileSync(index.absolutePath, 'utf8');
  if (/<base\s/i.test(html)) throw new Error('index.html already contains a <base> element.');
  if (!/<head(?:\s[^>]*)?>/i.test(html)) throw new Error('index.html has no <head> element for --base-href.');
  const transformed = Buffer.from(html.replace(/<head(\s[^>]*)?>/i, (match) => `${match}\n  <base href="${baseHref}">`));
  const replacement = {
    ...index,
    size: transformed.length,
    sha256Hex: createHash('sha256').update(transformed).digest('hex'),
    sha256Base64: createHash('sha256').update(transformed).digest('base64'),
    md5Hex: createHash('md5').update(transformed).digest('hex'),
    uploadContents: transformed,
  };
  return localFiles.map((file) => file === index ? replacement : file);
}

function validSha256Hex(value) {
  return typeof value === 'string' && /^[a-f0-9]{64}$/i.test(value);
}

function checksumBase64ToHex(value) {
  if (typeof value !== 'string') return null;
  try {
    const decoded = Buffer.from(value, 'base64');
    return decoded.length === 32 ? decoded.toString('hex') : null;
  } catch {
    return null;
  }
}

export function remoteObjectMatches(local, remote) {
  const checksumHex = checksumBase64ToHex(remote.checksumSHA256);
  if (checksumHex) return checksumHex === local.sha256Hex;
  const metadataSha256 = remote.metadata?.sha256;
  if (validSha256Hex(metadataSha256)) return metadataSha256.toLowerCase() === local.sha256Hex;
  const etag = typeof remote.etag === 'string' ? remote.etag.replace(/^"|"$/g, '') : '';
  if (/^[a-f0-9]{32}$/i.test(etag)) return etag.toLowerCase() === local.md5Hex;
  return false;
}

export function classifyDiff(localObjects, remoteObjects, prefix, options = {}) {
  const localByKey = new Map();
  const remoteByKey = new Map();
  for (const object of localObjects) {
    assertKeyInsidePrefix(object.key, prefix);
    localByKey.set(object.key, object);
  }
  for (const object of remoteObjects) {
    assertKeyInsidePrefix(object.key, prefix);
    remoteByKey.set(object.key, object);
  }
  const diff = { additions: [], changes: [], deletions: [], unchanged: [], keptRemote: [] };
  for (const [key, local] of localByKey) {
    const remote = remoteByKey.get(key);
    if (!remote) diff.additions.push(local);
    else if (remoteObjectMatches(local, remote)) diff.unchanged.push(local);
    else diff.changes.push(local);
  }
  for (const [key, remote] of remoteByKey) {
    if (localByKey.has(key)) continue;
    if (options.noDelete) diff.keptRemote.push(remote);
    else diff.deletions.push(remote);
  }
  for (const values of Object.values(diff)) values.sort((a, b) => a.key.localeCompare(b.key));
  return diff;
}

export function contentHeaders(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  const contentTypes = {
    '.css': 'text/css; charset=utf-8',
    '.gif': 'image/gif',
    '.html': 'text/html; charset=utf-8',
    '.ico': 'image/x-icon',
    '.jpeg': 'image/jpeg',
    '.jpg': 'image/jpeg',
    '.js': 'text/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.mjs': 'text/javascript; charset=utf-8',
    '.mp3': 'audio/mpeg',
    '.ogg': 'audio/ogg',
    '.png': 'image/png',
    '.svg': 'image/svg+xml',
    '.txt': 'text/plain; charset=utf-8',
    '.wasm': 'application/wasm',
    '.wav': 'audio/wav',
    '.webp': 'image/webp',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.xml': 'application/xml; charset=utf-8',
  };
  return {
    contentType: contentTypes[extension] ?? 'application/octet-stream',
    cacheControl: ['.html', '.css', '.js', '.mjs', '.json'].includes(extension) ? NO_CACHE : CACHEABLE,
  };
}

function runAws(args) {
  const result = spawnSync('aws', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  if (result.error) throw new Error(`Unable to run AWS CLI: ${result.error.message}`);
  if (result.status !== 0) {
    throw new Error(`AWS CLI failed: aws ${args.join(' ')}\n${result.stderr.trim()}`);
  }
  return result.stdout.trim();
}

function runAwsJson(args) {
  const output = runAws([...args, '--output', 'json']);
  return output ? JSON.parse(output) : {};
}

function loadProductionConfig() {
  const config = JSON.parse(fs.readFileSync(deployConfigPath, 'utf8')).production;
  if (!config?.bucketName || !config?.distributionId) {
    throw new Error('Production deploy-config.json entry is incomplete.');
  }
  return config;
}

function verifyAwsAccount() {
  const identity = runAwsJson(['sts', 'get-caller-identity']);
  if (identity.Account !== EXPECTED_AWS_ACCOUNT) {
    throw new Error(`Wrong AWS account ${identity.Account ?? '(unknown)'}; expected ${EXPECTED_AWS_ACCOUNT}.`);
  }
}

function inventoryRemoteObjects(bucket, prefix, options = {}) {
  const listing = runAwsJson(['s3api', 'list-objects-v2', '--bucket', bucket, '--prefix', prefix]);
  const matchKeys = options.matchKeys instanceof Set ? options.matchKeys : null;
  return (listing.Contents ?? []).map((listed) => {
    assertKeyInsidePrefix(listed.Key, prefix);
    // For --no-delete partial updates, only checksum the allowlisted keys we may upload.
    if (matchKeys && !matchKeys.has(listed.Key)) {
      return { key: listed.Key, etag: listed.ETag };
    }
    const head = runAwsJson([
      's3api',
      'head-object',
      '--bucket',
      bucket,
      '--key',
      listed.Key,
      '--checksum-mode',
      'ENABLED',
    ]);
    return {
      key: listed.Key,
      checksumSHA256: head.ChecksumSHA256,
      metadata: head.Metadata ?? {},
      etag: head.ETag ?? listed.ETag,
    };
  });
}

export function confirmationPhrase(slug) {
  return `DEPLOY ${validateSlug(slug)} TO PRODUCTION`;
}

function printReport(diff, bucket, prefix, options = {}) {
  console.log(`\nProduction target: s3://${bucket}/${prefix}`);
  if (options.noDelete) {
    console.log('Mode: --no-delete (remote keys outside the allowlist are left untouched)');
  }
  for (const [label, values] of Object.entries(diff)) {
    if (label === 'keptRemote' && values.length === 0) continue;
    const heading = label === 'keptRemote' ? 'KEPT REMOTE (not in allowlist; not deleted)' : label.toUpperCase();
    console.log(`\n${heading} (${values.length})`);
    if (label === 'keptRemote' && values.length > 20) {
      for (const object of values.slice(0, 10)) console.log(`  ${object.key}`);
      console.log(`  ... and ${values.length - 10} more`);
    } else {
      for (const object of values) console.log(`  ${object.key}`);
    }
  }
}

async function confirmProduction(slug) {
  const phrase = confirmationPhrase(slug);
  console.log(`\n${RED}PRODUCTION DEPLOY: uploads and scoped deletions will modify the live site.${RESET}`);
  console.log(`Type exactly: ${phrase}`);
  const prompt = readline.createInterface({ input: process.stdin, output: process.stdout });
  const answer = await prompt.question('Confirmation: ');
  prompt.close();
  if (answer !== phrase) throw new Error('Confirmation did not match. No production changes were made.');
}

function uploadObject(bucket, object, prefix) {
  assertKeyInsidePrefix(object.key, prefix);
  const headers = contentHeaders(object.relativePath);
  let bodyPath = object.absolutePath;
  let temporaryDirectory;
  try {
    if (object.uploadContents) {
      temporaryDirectory = fs.mkdtempSync(path.join(os.tmpdir(), 'fof-static-page-'));
      bodyPath = path.join(temporaryDirectory, path.basename(object.relativePath));
      fs.writeFileSync(bodyPath, object.uploadContents);
    }
    runAws([
      's3api',
      'put-object',
      '--bucket',
      bucket,
      '--key',
      object.key,
      '--body',
      bodyPath,
      '--content-type',
      headers.contentType,
      '--cache-control',
      headers.cacheControl,
      '--checksum-algorithm',
      'SHA256',
      '--checksum-sha256',
      object.sha256Base64,
      '--metadata',
      `sha256=${object.sha256Hex}`,
    ]);
  } finally {
    if (temporaryDirectory) fs.rmSync(temporaryDirectory, { recursive: true, force: true });
  }
}

function deleteObject(bucket, object, prefix) {
  assertKeyInsidePrefix(object.key, prefix);
  runAws(['s3api', 'delete-object', '--bucket', bucket, '--key', object.key]);
}

export async function main(argv = process.argv.slice(2)) {
  const options = parseArgs(argv);
  if (options.help) {
    console.log(usage());
    return;
  }
  const localFiles = addHtmlBaseHref(
    inventoryLocalFiles(options.source, options.allow),
    options.baseHref,
  );
  const localObjects = localFilesToObjects(localFiles, options.slug);
  const prefix = keyPrefixForSlug(options.slug);
  const config = loadProductionConfig();
  verifyAwsAccount();
  const remoteObjects = inventoryRemoteObjects(
    config.bucketName,
    prefix,
    options.noDelete ? { matchKeys: new Set(localObjects.map((object) => object.key)) } : {},
  );
  const diff = classifyDiff(localObjects, remoteObjects, prefix, { noDelete: options.noDelete });
  printReport(diff, config.bucketName, prefix, { noDelete: options.noDelete });
  if (diff.additions.length + diff.changes.length + diff.deletions.length === 0) {
    console.log('\nNo production changes are needed.');
    return;
  }
  if (diff.deletions.length > 0 && options.noDelete) {
    throw new Error('Internal error: --no-delete still produced deletions.');
  }
  await confirmProduction(options.slug);
  for (const object of [...diff.additions, ...diff.changes]) {
    uploadObject(config.bucketName, object, prefix);
  }
  for (const object of diff.deletions) deleteObject(config.bucketName, object, prefix);
  runAws([
    'cloudfront',
    'create-invalidation',
    '--distribution-id',
    config.distributionId,
    '--paths',
    `/${options.slug}`,
    `/${options.slug}/*`,
  ]);
  console.log('\nScoped production deploy complete.');
}

function printAbort(error) {
  const invariant = error instanceof Error && error.message.includes('DEPLOY SCOPE INVARIANT VIOLATION');
  const prefix = invariant ? `${RED}ABORT: DEPLOY SCOPE INVARIANT VIOLATED. NOTHING WAS DEPLOYED.${RESET}\n` : '';
  console.error(`${prefix}${error instanceof Error ? error.message : error}`);
}

const isDirectRun = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isDirectRun) {
  main().catch((error) => {
    printAbort(error);
    process.exitCode = 1;
  });
}
