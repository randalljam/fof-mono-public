#!/usr/bin/env node
import { execSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ensureAppletAudio } from './applet-audio.js';

const environment = process.argv[2];
if (!environment || !['staging', 'production'].includes(environment)) {
  console.error('Usage: node scripts/deploy.js <staging|production>');
  process.exit(1);
}

const webRoot = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..');
const deployConfigPath = path.join(webRoot, 'deploy-config.json');
const distDir = path.join(webRoot, 'dist');

function run(command, options = {}) {
  console.log(`\n> ${command}`);
  execSync(command, { stdio: 'inherit', cwd: webRoot, ...options });
}

function requireAws() {
  const result = spawnSync('aws', ['--version'], { encoding: 'utf8' });
  if (result.status !== 0) {
    console.error('AWS CLI is required. Install AWS CLI v2 and configure credentials before deploying.');
    process.exit(1);
  }
}

function loadDeployConfig() {
  if (!fs.existsSync(deployConfigPath)) {
    console.error(`Missing ${deployConfigPath}.`);
    console.error('Deploy infrastructure first, then save stack outputs:');
    console.error('  cd ../infra && npm run deploy:staging');
    console.error('  node scripts/save-deploy-config.js staging');
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(deployConfigPath, 'utf8'))[environment];
}

requireAws();
ensureAppletAudio({ pull: true });
run('npm run build');

const config = loadDeployConfig();
if (!config?.bucketName || !config?.distributionId) {
  console.error(`Deploy config for ${environment} is incomplete.`);
  process.exit(1);
}

console.log(`\nDeploy target (${environment}):`);
console.log(`  Bucket: ${config.bucketName}`);
console.log(`  CloudFront distribution: ${config.distributionId}`);

run(`aws s3 sync dist/ s3://${config.bucketName}/ --delete --exclude "*" --include "*.html" --cache-control "max-age=0,no-cache,no-store,must-revalidate"`);
run(`aws s3 sync dist/ s3://${config.bucketName}/ --delete --exclude "*.html" --cache-control "public,max-age=31536000,immutable"`);
run(`aws cloudfront create-invalidation --distribution-id ${config.distributionId} --paths "/*"`);

console.log(`\nDeploy complete for ${environment}.`);
if (config.siteUrls?.length) {
  console.log(`Validate: ${config.siteUrls.join(', ')}`);
}
