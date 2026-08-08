#!/usr/bin/env node
// Shared helpers for gitignored applet TTS clips (S3-backed via [S3-FILES-BUCKET]).
import fs from 'node:fs';
import path from 'node:path';
import { execSync, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

export const S3_BUCKET = '[S3-FILES-BUCKET]';
export const S3_AUDIO_PREFIX = 'apps/focusonfoundations/web/public/audio/';
export const REQUIRED_APPLETS = ['counting-creatures', 'logic-gates'];

const webRoot = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..');
export const localAudioRoot = path.join(webRoot, 'public', 'audio');

export function localAppletDir(applet) {
  return path.join(localAudioRoot, applet);
}

export function countMp3s(dir) {
  if (!fs.existsSync(dir)) return 0;
  return fs.readdirSync(dir).filter((name) => name.endsWith('.mp3')).length;
}

export function missingApplets() {
  return REQUIRED_APPLETS.filter((applet) => countMp3s(localAppletDir(applet)) === 0);
}

export function requireAws() {
  const result = spawnSync('aws', ['--version'], { encoding: 'utf8' });
  if (result.status !== 0) {
    console.error('AWS CLI is required. Install AWS CLI v2 and configure credentials.');
    process.exit(1);
  }
}

export function pullAppletAudio() {
  requireAws();
  fs.mkdirSync(localAudioRoot, { recursive: true });
  const s3Uri = `s3://${S3_BUCKET}/${S3_AUDIO_PREFIX}`;
  const cmd = `aws s3 sync ${s3Uri} ${localAudioRoot}/ --exclude "*" --include "*.mp3"`;
  console.log(`\n> ${cmd}`);
  execSync(cmd, { stdio: 'inherit', cwd: webRoot });
}

export function ensureAppletAudio({ pull = false } = {}) {
  const missing = missingApplets();
  if (missing.length === 0) return;
  if (pull) {
    console.log(`Applet audio missing locally (${missing.join(', ')}); pulling from s3://${S3_BUCKET}/...`);
    pullAppletAudio();
    const stillMissing = missingApplets();
    if (stillMissing.length === 0) return;
    missing.splice(0, missing.length, ...stillMissing);
  }
  console.error('Applet TTS mp3s are missing under public/audio/.');
  console.error(`Missing or empty: ${missing.join(', ')}`);
  console.error('Run from apps/focusonfoundations/web:  npm run audio:pull');
  console.error('Or regenerate:  OPENAI_API_KEY=... node scripts/generate-tts.js --applet <name>');
  process.exit(1);
}
