#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Focus on Foundations tooling check ==="
echo "Node: $(node --version)"
echo "npm: $(npm --version)"

if command -v aws >/dev/null 2>&1; then
  echo "AWS CLI: $(aws --version)"
  echo "AWS identity:"
  aws sts get-caller-identity || true
else
  echo "AWS CLI: not installed"
  echo "Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
fi

if [[ -d "$ROOT/infra/node_modules/.bin/cdk" || -f "$ROOT/infra/node_modules/.bin/cdk" ]]; then
  echo "CDK (local): $($ROOT/infra/node_modules/.bin/cdk --version)"
else
  echo "CDK (local): run 'npm install' in apps/focusonfoundations/infra"
fi

echo "Done."
