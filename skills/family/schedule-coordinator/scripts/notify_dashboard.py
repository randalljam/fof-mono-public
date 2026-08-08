#!/usr/bin/env python3
# Best-effort: tell the lesson-logger dashboard to re-pull from Hermes after a
# schedule edit, so the Family Schedule view updates live.
#
# The dashboard's /internal/sync endpoint pulls BOTH the lessons DB and the
# schedule markdown, so this reuses the same endpoint + credentials the lesson
# logger already uses. It is a no-op (exit 0) when no sync URL is configured —
# e.g. in local dev or any environment without the dashboard.
#
# Config (env vars), generic names preferred, lesson-logger names as fallback:
#   DASH_SYNC_URL      | LESSON_DASH_SYNC_URL       (required to do anything)
#   DASH_SYNC_USER     | LESSON_DASH_SYNC_USER      (optional Basic Auth user)
#   DASH_SYNC_PASSWORD | LESSON_DASH_SYNC_PASSWORD  (optional Basic Auth password)
#   DASH_SYNC_TIMEOUT  | LESSON_DASH_SYNC_TIMEOUT   (optional, seconds; default 10)
import base64
import os
import sys
import urllib.request

def _env(*names, default=None):
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return default
def main():
    url = _env("DASH_SYNC_URL", "LESSON_DASH_SYNC_URL")
    if not url:
        print("dashboard sync not configured (no DASH_SYNC_URL) — skipping")
        return 0
    req = urllib.request.Request(url, data=b"", method="POST")
    user = _env("DASH_SYNC_USER", "LESSON_DASH_SYNC_USER")
    password = _env("DASH_SYNC_PASSWORD", "LESSON_DASH_SYNC_PASSWORD")
    if user and password:
        token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        req.add_header("Authorization", f"Basic {token}")
    timeout = float(_env("DASH_SYNC_TIMEOUT", "LESSON_DASH_SYNC_TIMEOUT", default="10"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = getattr(response, "status", response.getcode())
            if 200 <= status < 300:
                print("dashboard sync requested")
                return 0
            # /internal/sync may return 503 if the lessons DB sync failed even
            # though the schedule was refreshed — treat as a soft warning.
            print(f"dashboard sync request returned HTTP {status}", file=sys.stderr)
            return 0
    except Exception as exc:
        print(f"dashboard sync request failed: {exc}", file=sys.stderr)
        return 0
if __name__ == "__main__":
    sys.exit(main())
