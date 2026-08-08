#!/usr/bin/env bash
# Code-only Lambda prod update: replace app.py in the live deployment package and upload.
# Leaves env vars, API Gateway, and function config unchanged.
set -euo pipefail

REGION="${AWS_REGION:-us-west-2}"
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SNAPSHOT_ROOT="${REPO_ROOT}/tmp/cors-prod-snapshots"

usage() {
  echo "Usage: $0 <function-name> <repo-app-py-path>"
  echo "Example: $0 hash-store-prod web-shared/aws_chalice/hash-store/app.py"
  exit 1
}

[[ $# -eq 2 ]] || usage

FUNCTION_NAME="$1"
REPO_APP_PY="${REPO_ROOT}/$2"

if [[ ! -f "$REPO_APP_PY" ]]; then
  echo "Repo app.py not found: $REPO_APP_PY"
  exit 1
fi

if [[ -z "${SNAPSHOT_DIR:-}" ]]; then
  SNAPSHOT_DIR="${SNAPSHOT_ROOT}/$(date +%Y-%m-%d_%H%M%S)"
fi
mkdir -p "$SNAPSHOT_DIR"

echo "=== Lambda code-only update: $FUNCTION_NAME ==="
echo "Region: $REGION"
echo "Snapshot dir: $SNAPSHOT_DIR"
echo "Repo app.py: $2"

aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION" \
  > "$SNAPSHOT_DIR/${FUNCTION_NAME}.config.json"

ORIG_ZIP="$SNAPSHOT_DIR/${FUNCTION_NAME}.orig.zip"
PATCHED_ZIP="$SNAPSHOT_DIR/${FUNCTION_NAME}.patched.zip"
WORK_DIR="$SNAPSHOT_DIR/${FUNCTION_NAME}.work"

CODE_URL="$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" --query 'Code.Location' --output text)"
curl -sL "$CODE_URL" -o "$ORIG_ZIP"

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
unzip -q -o "$ORIG_ZIP" -d "$WORK_DIR"

if [[ ! -f "$WORK_DIR/app.py" ]]; then
  echo "ERROR: app.py not found at zip root for $FUNCTION_NAME"
  exit 1
fi

echo "--- diff deployed app.py vs repo (before patch) ---"
diff -u "$WORK_DIR/app.py" "$REPO_APP_PY" | head -60 || true

cp "$REPO_APP_PY" "$WORK_DIR/app.py"

(
  cd "$WORK_DIR"
  zip -q -r "$PATCHED_ZIP" .
)

echo "Uploading patched package via S3..."
S3_BUCKET="${LAMBDA_DEPLOY_S3_BUCKET:-[S3-FILES-BUCKET]}"
S3_KEY="tmp/lambda-code-deploy/${FUNCTION_NAME}-$(date +%Y%m%d_%H%M%S).zip"
export AWS_MAX_ATTEMPTS=3
export AWS_RETRY_MODE=standard
for attempt in 1 2 3; do
  if aws s3 cp "$PATCHED_ZIP" "s3://${S3_BUCKET}/${S3_KEY}" --region "$REGION" \
    && aws lambda update-function-code \
      --function-name "$FUNCTION_NAME" \
      --region "$REGION" \
      --s3-bucket "$S3_BUCKET" \
      --s3-key "$S3_KEY" \
      > "$SNAPSHOT_DIR/${FUNCTION_NAME}.update-result.json"; then
    echo "Uploaded s3://${S3_BUCKET}/${S3_KEY}"
    break
  fi
  if [[ "$attempt" -eq 3 ]]; then
    echo "ERROR: update-function-code via S3 failed after 3 attempts"
    exit 1
  fi
  echo "Upload attempt $attempt failed; retrying in 10s..."
  sleep 10
done

aws lambda wait function-updated \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION"

echo "Done: $FUNCTION_NAME updated. Rollback: aws lambda update-function-code --function-name $FUNCTION_NAME --region $REGION --zip-file fileb://${ORIG_ZIP}"
