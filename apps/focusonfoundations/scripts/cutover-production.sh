#!/usr/bin/env bash
# Production cutover helper — run only after staging validation and explicit approval.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEB="$ROOT/web"
INFRA="$ROOT/infra"

echo "=== Focus on Foundations production cutover checklist ==="
echo
echo "Pre-flight (manual):"
echo "  [ ] Staging validated at https://staging.focusonfoundations.org"
echo "  [ ] Local build reviewed (npm run build && npm run preview)"
echo "  [ ] DNS records exported from current provider (MX, SPF, DKIM, DMARC, TXT)"
echo "  [ ] Webflow site kept live for rollback"
echo "  [ ] TTL lowered at current DNS provider if possible"
echo
echo "AWS account:"
aws sts get-caller-identity
echo

read -r -p "Deploy production CDK stack if not already deployed? [y/N] " deploy_infra
if [[ "${deploy_infra,,}" == "y" ]]; then
  cd "$INFRA"
  export CDK_DEFAULT_ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
  export AWS_REGION=us-east-1
  npm run deploy:production
fi

read -r -p "Save production deploy config from CloudFormation outputs? [y/N] " save_config
if [[ "${save_config,,}" == "y" ]]; then
  node "$WEB/scripts/save-deploy-config.js" production
fi

read -r -p "Deploy production site content to S3 + invalidate CloudFront? [y/N] " deploy_content
if [[ "${deploy_content,,}" == "y" ]]; then
  cd "$WEB"
  npm run deploy:production
fi

echo
echo "DNS cutover (manual — choose one path):"
echo "  A) Route 53: set createDnsRecords=true on FofSiteProduction, redeploy CDK, update registrar NS"
echo "  B) External DNS: point apex/www records to CloudFront distribution domain"
echo
echo "Post-cutover validation:"
echo "  curl -I https://focusonfoundations.org/"
echo "  curl -I https://www.focusonfoundations.org/"
echo "  Test demo API calls from production origin (CORS)"
echo
echo "Rollback: revert DNS to Webflow or redeploy last good S3 build."
