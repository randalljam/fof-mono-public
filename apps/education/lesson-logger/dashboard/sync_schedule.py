import logging
import os
import urllib.request

logger = logging.getLogger("sync_schedule")

DEFAULT_SCHEDULE_BASE_URL = "http://[FLY-APP-NAME].internal:8081/family-schedule"
DEFAULT_SCHEDULE_DIR = "/data/schedule"
SYNC_TIMEOUT_SECONDS = 5
# Remote route filename -> local filename written under SCHEDULE_DIR.
SCHEDULE_FILES = {
    "current-week.md": "current-week.md",
    "next-week.md": "next-week.md",
    "horizon.md": "horizon.md",
}
def sync_schedule_from_hermes():
    """Pull the family-schedule markdown files from Hermes over Fly private networking.

    Each file is fetched independently. A missing file on Hermes (HTTP 404 — e.g. the
    current or next week hasn't been created yet) is not an error: the cached copy is left in
    place. Returns True if at least one file was refreshed."""
    base_url = os.environ.get("HERMES_SCHEDULE_BASE_URL", DEFAULT_SCHEDULE_BASE_URL)
    dest_dir = os.environ.get("SCHEDULE_DIR", DEFAULT_SCHEDULE_DIR)
    if not base_url:
        logger.info("Hermes schedule sync not configured — using local files")
        return False
    try:
        os.makedirs(dest_dir, exist_ok=True)
    except OSError as e:
        logger.warning(
            f"Schedule sync cannot create cache directory {dest_dir}: {e}")
        return False
    refreshed = 0
    for remote_name, local_name in SCHEDULE_FILES.items():
        url = f"{base_url.rstrip('/')}/{remote_name}"
        dest = os.path.join(dest_dir, local_name)
        try:
            content = _download(url)
            tmp = dest + ".downloading"
            with open(tmp, "wb") as f:
                f.write(content)
            os.replace(tmp, dest)
            logger.info(f"Synced {len(content):,} bytes from Hermes -> {dest}")
            refreshed += 1
        except FileNotFoundOnHermes:
            logger.info(f"Schedule file not yet on Hermes (404): {url} — keeping cached copy")
        except Exception as e:
            logger.warning(f"Schedule sync failed for {url}: {e}")
            if os.path.exists(dest + ".downloading"):
                os.remove(dest + ".downloading")
    return refreshed > 0
class FileNotFoundOnHermes(Exception):
    pass
def _download(url):
    request = urllib.request.Request(url, headers={"Accept": "text/markdown"})
    try:
        with urllib.request.urlopen(request, timeout=SYNC_TIMEOUT_SECONDS) as response:
            status = getattr(response, "status", response.getcode())
            if status != 200:
                raise RuntimeError(f"unexpected HTTP status {status}")
            return response.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise FileNotFoundOnHermes(url)
        raise
