#!/usr/bin/env bash
# Deploy staging content after local review.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Staging deploy ==="
aws sts get-caller-identity

read -r -p "Deploy staging CDK stack (if needed)? [y/N] " deploy_infra
if [[ "${deploy_infra,,}" == "y" ]]; then
  cd "$ROOT/infra"
  export CDK_DEFAULT_ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
  export AWS_REGION=us-east-1
  npm run deploy:staging -c hostedZoneId=REPLACE_WITH_ZONE_ID
fi

read -r -p "Save staging deploy config? [y/N] " save_config
if [[ "${save_config,,}" == "y" ]]; then
  node "$ROOT/web/scripts/save-deploy-config.js" staging
fi

cd "$ROOT/web"
npm run deploy:staging

echo "Validate: https://staging.focusonfoundations.org"
