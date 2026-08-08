#!/usr/bin/env node
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const environment = process.argv[2];
const stackName = environment === 'production' ? 'FofSiteProduction' : 'FofSiteStaging';

if (!environment || !['staging', 'production'].includes(environment)) {
  console.error('Usage: node scripts/save-deploy-config.js <staging|production>');
  process.exit(1);
}

const webRoot = path.resolve(fileURLToPath(new URL('.', import.meta.url)), '..');
const configPath = path.join(webRoot, 'deploy-config.json');

function getOutput(key) {
  const command = `aws cloudformation describe-stacks --stack-name ${stackName} --query "Stacks[0].Outputs[?ExportName=='${key}'].OutputValue" --output text --region us-east-1`;
  return execSync(command, { encoding: 'utf8' }).trim();
}

const bucketName = getOutput(`fof-site-${environment}-bucket`);
const distributionId = getOutput(`fof-site-${environment}-distribution-id`);
const siteUrlsOutput = execSync(
  `aws cloudformation describe-stacks --stack-name ${stackName} --query "Stacks[0].Outputs[?OutputKey=='SiteUrls'].OutputValue" --output text --region us-east-1`,
  { encoding: 'utf8' }
).trim();

const existing = fs.existsSync(configPath) ? JSON.parse(fs.readFileSync(configPath, 'utf8')) : {};
existing[environment] = {
  bucketName,
  distributionId,
  siteUrls: siteUrlsOutput.split(',').map((value) => value.trim()).filter(Boolean),
  updatedAt: new Date().toISOString(),
};

fs.writeFileSync(configPath, `${JSON.stringify(existing, null, 2)}\n`);
console.log(`Saved deploy config for ${environment} to ${configPath}`);
