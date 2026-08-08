## About this file
### Benign patterns suppressed by pii_sweep.py — substring match against the matched text or the file path; a leading '=' makes it an exact match against the matched text only.
### Keep personal terms OUT of this tracked file; those go in local-only docs/personal/pii-terms.md.

## Placeholders, examples, and decided-public values
noreply@anthropic.com
example.com
example.test
user@example
127.0.0.1
0.0.0.0
localhost
AKIAIOSFODNN7EXAMPLE
123456789012
000000000000
__CT_TOKEN__
__WVM_TOKEN__
[REMOVED-JWT]
YOUR_API_KEY
codex-secret
555-01
git@github.com
contact@focusonfoundations.org
accounts@focusonfoundations.org
randy@focusonfoundations.org
randy@floodlamp.bio
fofgeneral-service-account
host1.local
host2.local
host3.local

## Redacted/template ARN forms left after publish-time replacement
[AWS-ACCOUNT-ID]
ACCOUNT_ID
account-id
{account_id}
your-bucket
arn:aws:logs:*
arn:aws:s3:::{bucket}
arn:aws:s3:::deepgram-presigned-url-example
arn:aws:lambda:REGION
arn:aws:iam::$(aws
arn:aws:iam::...
arn:aws:lambda:*
arn:aws:ses:us-west-2:${this.account}
arn:aws:execute-api:{region}
arn:aws:apigateway:REGION
[S3-BUCKET]
=arn:aws:iam::
=arn:aws:lambda:

## Test fixtures confirmed non-real (RT 2026-07-31)
KidPass2026a
BrowserTest2026a

## Fake/test emails and code expressions
Example.com
you+kidname@gmail.com
user.name+tag@domain.co.uk
really.long.domain.co.uk
string_vrb@dq.md
incrementspodcast@gmail.com
USERS_HMAC_SECRET_KEY
jwtToken

## Public-record and fixture street addresses
123 Main St
4091 Jefferson Ave

## Version numbers and reserved/public IPs that match the ipv4 pattern
192.168.1.1
8.8.8.8
10.0.0.1
127.0.0.2
192.0.2.
3.49.1.0
15.20.0.130
15.19.0.120
1.8.2.1
10.26.7.9
198.202.211.1
190.189.66.144

## Public-record source paths and test fixtures (path match — suppresses all categories)
tests/test_manual_files/
docs/packages/
web-shared/md_to_html_dev/
web-shared/test_front-end_validation_inputs.js
skills/family/schedule-coordinator/references/
apps/deutsch/deutsch-graph/graph/nodes/
skills/repo-ops/public-snapshot/scripts/
skills/repo-public/public-snapshot/scripts/
