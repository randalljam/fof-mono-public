#!/usr/bin/env python3
"""
file: core/grant_cloud_s3_access.py
title: Grant a cloud coding agent scoped S3 access for one app (IaC)

WHAT THIS DOES
--------------
Provisions least-privilege AWS access to an S3 prefix for a cloud agent (Claude Code on
the web) that runs in an ephemeral VM and can't see your local files. Access is
**per application**: each app gets its OWN IAM user, access key, and app-prefixed env-var
names, so apps are isolated and rotate/revoke independently. Re-run it to add more prefixes
(or a write prefix) to the same app — the app's single key covers them all.

Per run it attaches one inline policy for one (prefix, access-level) pair:
  --access read       (default)  s3:ListBucket(prefix) + s3:GetObject       — read only
  --access readwrite             the above + s3:PutObject                   — read + write
  --allow-delete                 also s3:DeleteObject                       — OFF by default
No other services, no other prefixes.

This is the credentials half. A cloud agent ALSO needs network egress to S3 opened in the
Claude Code web environment (Step 3 below) — credentials alone are not enough.

READ vs WRITE — why READ is the default
---------------------------------------
Cloud-env credentials are more exposed than local ones (they live on a third-party platform
and are injected into sessions that run arbitrary agent code), and `[S3-BUCKET]` holds PII. So:
- Keep **read-only** on real-capture / PII prefixes (a leaked read key can't corrupt or delete).
- For agent outputs (simulation results, processed artifacts), grant **readwrite to a SEPARATE
  output prefix**, and prefer a **non-PII bucket** (`[S3-FILES-BUCKET]`) — never write into the PII
  capture prefix, and leave delete OFF. One per-app key with two prefix grants (read input,
  readwrite output) is simple and safe; separate keys only if a less-trusted reader needs the
  read key. Example:
    read  real captures:   .../grant... [S3-BUCKET]  math-quiz/test/anchor              # default read
    write agent outputs:   .../grant... [S3-FILES-BUCKET]  math-quiz/agent-runs --access readwrite

WHO RUNS IT
-----------
You, locally, with AWS credentials that can manage IAM (admin-ish). Uses the default boto3
chain (env / ~/.aws / SSO) — the creds behind `aws sts get-caller-identity`. No repo `.env`.

SAFE BY DEFAULT
---------------
Dry-run unless `--execute`. The access-key secret is shown ONCE on creation — copy it into
your local .env and the cloud environment; never paste it into a chat or commit it.


STEP-BY-STEP (math-quiz is the worked example)
==============================================

Step 0 — confirm your local AWS identity can manage IAM:
    aws sts get-caller-identity            # prints your account + user ARN

Step 1 — preview, then create the per-app user + policy + key (from the repo root):
    .venv/bin/python3 core/grant_cloud_s3_access.py math-quiz            # dry-run (prints plan)
    .venv/bin/python3 core/grant_cloud_s3_access.py math-quiz --execute  # create (read-only)

  Options:
    --bucket [S3-BUCKET]        S3 bucket (default: [S3-BUCKET])
    --app NAME                app id -> IAM user + env-var prefix (default: 1st path segment)
    --access read|readwrite   permission level (default: read)
    --allow-delete            also allow s3:DeleteObject (default: off)
    --region us-west-2        region for the egress hostnames it prints (default: us-west-2)
    --new-key                 force-mint a fresh access key (rotation)

  On first `--execute` for an app it prints an AccessKeyId + SecretAccessKey. COPY THEM NOW.
  The env-var names are derived from --app, e.g. app "math-quiz" -> MATH_QUIZ_S3_*.

Step 2 — save the credentials to your LOCAL .env (backup so you can re-enter them later).
         Append the three lines the script prints (app-prefixed names so they won't override
         your real/admin AWS creds on local runs — core/aws.py + tools/dev_server.py call
         load_dotenv(override=True)). The printed block has NO leading indentation, so you can
         paste it verbatim. Keep .env gitignored; never commit the secret. (The cloud VM does
         NOT read your laptop's .env — this is only a backup; the cloud copy is set in Step 3.)

Step 3 — paste the SAME block into the Claude Code cloud environment. In the macOS app,
         click the cloud icon, choose the environment, paste the three lines into the
         environment variables window, and save.
       * Network access: choose Custom (keep the default list so npm/PyPI work) and add the two
         hosts the script prints; or pick Full if only broad tiers are offered.
       * Click Save.

Step 4 — start a NEW cloud session, make sure this Cloud Environment is selected, and paste the
         verification prompt the script prints. It tells the agent to confirm the app-prefixed env
         vars are set and to list s3://<bucket>/<prefix>/, reporting success or the exact error (a
         "Host not in allowlist" error = egress still closed; AccessDenied = creds/policy issue).

ROTATION / TEARDOWN (manual, when you want):
    aws iam list-access-keys     --user-name claude-cloud-math-quiz-s3
    aws iam delete-access-key    --user-name claude-cloud-math-quiz-s3 --access-key-id <OLD_ID>
    aws iam delete-user-policy   --user-name claude-cloud-math-quiz-s3 --policy-name <policy>
    aws iam delete-user          --user-name claude-cloud-math-quiz-s3
"""

import argparse
import json
import sys
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:  # dry-run / policy preview needs no AWS SDK; --execute does
    boto3 = None
    class ClientError(Exception):
        pass

DEFAULT_BUCKET = "[S3-BUCKET]"
DEFAULT_REGION = "us-west-2"

### Helpers: naming derived from the app + prefix
def _normalize(prefix):
    """Strip surrounding slashes/space so 'math-quiz', '/math-quiz/', 'math-quiz/' all match."""
    return prefix.strip().strip("/")
def app_from_prefix(prefix):
    """Default app id = first path segment of the prefix (e.g. 'math-quiz/test' -> 'math-quiz')."""
    return _normalize(prefix).split("/")[0]
def env_prefix(app):
    """Env-var prefix for an app: 'math-quiz' -> 'MATH_QUIZ'."""
    return app.upper().replace("-", "_").replace("/", "_")
def user_name_for(app):
    """Per-app IAM user name: 'math-quiz' -> 'claude-cloud-math-quiz-s3'."""
    return f"claude-cloud-{app}-s3"
def env_names(app):
    """Return (key_id_name, secret_name) — app-prefixed so they don't clobber admin creds."""
    p = env_prefix(app)
    return (f"{p}_S3_ACCESS_KEY_ID", f"{p}_S3_SECRET_ACCESS_KEY")
def policy_name_for(bucket, prefix, access, allow_delete):
    """Inline-policy name for this (bucket, prefix, access) grant (IAM-safe chars only)."""
    slug = _normalize(prefix).replace("/", "-")
    suffix = "-del" if allow_delete else ""
    return f"s3-{access}-{bucket}-{slug}{suffix}"

### Policy construction
def build_policy(bucket, prefix, access, allow_delete):
    """Least-privilege policy: List+Get always; +Put for readwrite; +Delete only if opted in."""
    prefix = _normalize(prefix)
    object_actions = ["s3:GetObject"]
    if access == "readwrite":
        object_actions.append("s3:PutObject")
    if allow_delete:
        object_actions.append("s3:DeleteObject")
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ListPrefix",
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": f"arn:aws:s3:::{bucket}",
                "Condition": {"StringLike": {"s3:prefix": [prefix, f"{prefix}/*"]}},
            },
            {
                "Sid": "ObjectActions",
                "Effect": "Allow",
                "Action": object_actions,
                "Resource": f"arn:aws:s3:::{bucket}/{prefix}/*",
            },
        ],
    }

### IAM provisioning
def ensure_user(iam, user_name, app):
    """Create the per-app IAM user if absent. Returns 'created' or 'exists'."""
    try:
        iam.create_user(UserName=user_name,
                        Tags=[{"Key": "purpose", "Value": "cloud-agent-s3"}, {"Key": "app", "Value": app}])
        return "created"
    except ClientError as e:
        if e.response["Error"]["Code"] == "EntityAlreadyExists":
            return "exists"
        raise
def put_prefix_policy(iam, user_name, bucket, prefix, access, allow_delete):
    """Attach/refresh the inline policy for this (prefix, access) grant. Returns the policy name."""
    name = policy_name_for(bucket, prefix, access, allow_delete)
    iam.put_user_policy(UserName=user_name, PolicyName=name,
                        PolicyDocument=json.dumps(build_policy(bucket, prefix, access, allow_delete)))
    return name
def ensure_access_key(iam, user_name, force_new=False):
    """Return (key_id, secret_or_None, note). Mints a key only if none exists or force_new.

    AWS never returns an existing key's secret, so for an already-keyed user we report the id
    and a note (no secret). With force_new we mint a second key for rotation."""
    existing = iam.list_access_keys(UserName=user_name)["AccessKeyMetadata"]
    if existing and not force_new:
        ids = ", ".join(k["AccessKeyId"] for k in existing)
        return (existing[0]["AccessKeyId"], None,
                f"user already has access key(s): {ids}. Secret is not retrievable; reuse the "
                f"one already stored in the cloud env, or pass --new-key to rotate.")
    if len(existing) >= 2:
        return (existing[0]["AccessKeyId"], None,
                "user already has the AWS max of 2 access keys; delete one before --new-key "
                f"(aws iam delete-access-key --user-name {user_name} --access-key-id <OLD_ID>).")
    key = iam.create_access_key(UserName=user_name)["AccessKey"]
    return (key["AccessKeyId"], key["SecretAccessKey"], "new access key created — copy the secret now.")

### Output: the remaining manual steps, with real values filled in
def verify_prompt(app, bucket, prefix):
    """Return the prompt to paste into a fresh cloud session so the agent verifies access."""
    key_name, secret_name = env_names(app)
    return (
f"""Verify the cloud agent's AWS S3 access for the {app} app (provisioned by
core/grant_cloud_s3_access.py). Steps:
1. Confirm the env vars {key_name} and {secret_name} are present (do NOT print the secret value).
2. Build a boto3 S3 client using those creds (aws_access_key_id / aws_secret_access_key, and
   region_name from AWS_DEFAULT_REGION) and list s3://{bucket}/{prefix}/ (list_objects_v2).
3. Report the outcome: a listing (even if empty) = success. If it fails, give the exact error —
   a "Host not in allowlist" error means S3 network egress isn't open on this environment yet;
   an AccessDenied / auth error means the credentials or IAM policy need a look.
See that module's Step 4 for context.""")
def print_next_steps(app, bucket, prefix, region, access, key_id, secret, note):
    """Print the .env + cloud-env + egress + verify steps with this run's concrete values."""
    key_name, secret_name = env_names(app)
    secret_line = secret if secret else "<use the secret you saved when the key was created>"
    bar = "=" * 74
    print("\n" + bar)
    print(f"GRANTED: {access} on s3://{bucket}/{prefix}/*  to IAM user {user_name_for(app)}")
    print(bar)
    print("\n[Step 2] Save to your LOCAL .env (backup). [Step 3] Paste the SAME block into the cloud")
    print("environment. App-prefixed so it won't clobber admin creds. Copy the 3 lines below as-is:\n")
    print(f"{key_name}={key_id}")
    print(f"{secret_name}={secret_line}")
    print(f"AWS_DEFAULT_REGION={region}")
    if secret:
        print("\n^ secret shown ONCE. Copy it now; do NOT paste it into chat or commit it.")
    print(f"(note: {note})")
    print("\n[Step 3] Claude Code cloud environment:")
    print("In the macOS app, click the cloud icon, choose the environment, paste the block above")
    print("into the environment variables window, and save. Then set Network access to Custom")
    print("(keep the default list) and add these hosts as Allowed domains (or pick Full):\n")
    print(f"s3.{region}.amazonaws.com")
    print(f"{bucket}.s3.{region}.amazonaws.com")
    print("\n[Step 4] Start a NEW cloud session, make sure this Cloud Environment is selected, and")
    print("paste this prompt to verify access:\n")
    print(verify_prompt(app, bucket, prefix))
    print("\n" + bar + "\n")

### Orchestration
def grant_cloud_s3_access(prefix, bucket=DEFAULT_BUCKET, region=DEFAULT_REGION, app=None,
                          access="read", allow_delete=False, new_key=False, execute=False):
    """Create/refresh one scoped grant for an app. Dry-run unless execute=True."""
    prefix = _normalize(prefix)
    if not prefix:
        sys.exit("A prefix is required, e.g.: grant_cloud_s3_access.py math-quiz")
    if access not in ("read", "readwrite"):
        sys.exit("--access must be 'read' or 'readwrite'")
    app = app or app_from_prefix(prefix)
    user = user_name_for(app)
    key_name, secret_name = env_names(app)
    policy = build_policy(bucket, prefix, access, allow_delete)
    print(f"Plan: app '{app}' (IAM user '{user}', env vars {key_name} / {secret_name}) gets "
          f"{access}{' +delete' if allow_delete else ''} on s3://{bucket}/{prefix}/* "
          f"(policy '{policy_name_for(bucket, prefix, access, allow_delete)}').")
    print("Policy document:\n" + json.dumps(policy, indent=2))
    if not execute:
        print("\nDRY-RUN — nothing created. Re-run with --execute to apply, then follow the printed "
              "Steps 2-4. (See this file's docstring for the full procedure.)")
        return
    if boto3 is None:
        sys.exit("boto3 is required for --execute. Run inside the repo venv: "
                 ".venv/bin/python3 core/grant_cloud_s3_access.py ... --execute")
    iam = boto3.client("iam")
    try:
        print(f"User '{user}': {ensure_user(iam, user, app)}.")
        pname = put_prefix_policy(iam, user, bucket, prefix, access, allow_delete)
        print(f"Inline policy '{pname}': attached/updated.")
        key_id, secret, note = ensure_access_key(iam, user, force_new=new_key)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        sys.exit(f"AWS error ({code}): {e.response['Error']['Message']}\n"
                 "Your local identity needs IAM permissions (CreateUser/PutUserPolicy/CreateAccessKey).")
    print_next_steps(app, bucket, prefix, region, access, key_id, secret, note)

### CLI
def _main():
    p = argparse.ArgumentParser(
        description="Grant a cloud agent scoped S3 access for one app (least-privilege, per-app IAM). "
                    "Dry-run unless --execute. See the file docstring for the full step-by-step.")
    p.add_argument("prefix", help="prefix under the bucket to grant on, e.g. math-quiz or math-quiz/agent-runs")
    p.add_argument("--bucket", default=DEFAULT_BUCKET, help=f"S3 bucket (default {DEFAULT_BUCKET})")
    p.add_argument("--app", default=None, help="app id -> IAM user + env prefix (default: 1st path segment)")
    p.add_argument("--access", default="read", choices=["read", "readwrite"], help="permission level (default read)")
    p.add_argument("--allow-delete", action="store_true", help="also allow s3:DeleteObject (default off)")
    p.add_argument("--region", default=DEFAULT_REGION, help=f"region for egress hosts (default {DEFAULT_REGION})")
    p.add_argument("--new-key", action="store_true", help="force-mint a fresh access key (rotation)")
    p.add_argument("--execute", action="store_true", help="actually create resources (default is dry-run)")
    a = p.parse_args()
    grant_cloud_s3_access(a.prefix, bucket=a.bucket, region=a.region, app=a.app, access=a.access,
                          allow_delete=a.allow_delete, new_key=a.new_key, execute=a.execute)
if __name__ == "__main__":
    _main()
