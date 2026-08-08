# from Claude Code app - NOT IMPLEMENTED

## Lifecycle rules (clean up the leftover noncurrent versions)
Do this once per bucket, for [S3-FILES-BUCKET] and [S3-BUCKET]:

S3 console → open the bucket → Management tab → Lifecycle rules → Create lifecycle rule.
Rule name: expire-noncurrent-versions.
Choose a rule scope: select "Apply to all objects in the bucket" and tick the acknowledgment box.
Under Lifecycle rule actions, check these two:
☑ Permanently delete noncurrent versions of objects
☑ Delete expired object delete markers or incomplete multipart uploads
For "Permanently delete noncurrent versions" → Days after objects become noncurrent:
[S3-FILES-BUCKET] → 30
[S3-BUCKET] → 7 (tighter, since it's PII)
Leave "Number of newer noncurrent versions to retain" blank.
Tick Delete expired object delete markers and Delete incomplete multipart uploads (7 days).
Create rule. Repeat for the other bucket.
This reclaims the ~6.5 GB of old corpus-tools/data/... versions in [S3-FILES-BUCKET] and ages out the deleted PII versions in [S3-BUCKET], while keeping a short rollback window during this transition.

