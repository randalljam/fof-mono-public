import logging
import os
import sqlite3
import urllib.request

logger = logging.getLogger("sync_db")

DEFAULT_HERMES_DB_URL = "http://[FLY-APP-NAME].internal:8081/lesson-logger/lessons.db"
SYNC_TIMEOUT_SECONDS = 5
def sync_from_hermes():
    url = os.environ.get("HERMES_LESSON_DB_URL", DEFAULT_HERMES_DB_URL)
    dest = os.environ.get("LESSONS_DB", "/data/lessons.db")
    if not url:
        logger.info("Hermes DB sync not configured — using local DB")
        return False
    try:
        os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
        tmp = dest + ".downloading"
        logger.info(f"Syncing lessons DB from Hermes: {url}")
        _download_db(url, tmp)
        _validate_db(tmp)
        os.replace(tmp, dest)
        size = os.path.getsize(dest)
        logger.info(f"Synced {size:,} bytes from Hermes -> {dest}")
        return True
    except Exception as e:
        logger.warning(f"Hermes DB sync failed: {e}")
        if os.path.exists(dest + ".downloading"):
            os.remove(dest + ".downloading")
        return False
def _download_db(url, tmp):
    request = urllib.request.Request(url, headers={"Accept": "application/octet-stream"})
    with urllib.request.urlopen(request, timeout=SYNC_TIMEOUT_SECONDS) as response:
        status = getattr(response, "status", response.getcode())
        if status != 200:
            raise RuntimeError(f"unexpected HTTP status {status}")
        with open(tmp, "wb") as f:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
def _validate_db(path):
    if not os.path.exists(path) or os.path.getsize(path) <= 0:
        raise RuntimeError("downloaded DB is empty")
    conn = sqlite3.connect(path)
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise RuntimeError(f"downloaded DB failed integrity_check: {result}")
        table = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'entries'").fetchone()
        if not table:
            raise RuntimeError("downloaded DB missing entries table")
    finally:
        conn.close()
