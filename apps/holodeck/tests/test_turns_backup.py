"""Turns DB backup / restore helpers."""

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from apps.holodeck.turns import backup

PACIFIC = ZoneInfo("America/Los_Angeles")

def test_backup_and_restore_turns_db(tmp_path):
    db_path = tmp_path / "turns.db"
    db_path.write_bytes(b"good-state-v1")
    t0 = datetime(2026, 7, 28, 6, 0, 0, tzinfo=PACIFIC)
    first = backup.backup_turns_db(db_path, reason="unit-test first", when=t0)
    assert first is not None
    assert first.exists()
    assert first.parent == tmp_path / "backups"
    assert first.name == "turns_2026-07-28_060000.db"
    assert (Path(str(first) + ".reason.txt")).read_text(encoding="utf-8").strip() == "unit-test first"
    db_path.write_bytes(b"broken-state")
    second = backup.backup_turns_db(db_path, reason="unit-test second", when=t0 + timedelta(seconds=1))
    assert second != first
    restored = backup.restore_turns_db(first, db_path)
    assert restored == db_path
    assert db_path.read_bytes() == b"good-state-v1"
    assert backup.latest_backup(db_path) is not None
def test_prune_keeps_newest_backups(tmp_path):
    db_path = tmp_path / "turns.db"
    t0 = datetime(2026, 7, 28, 6, 0, 0, tzinfo=PACIFIC)
    for index in range(5):
        db_path.write_bytes(f"v{index}".encode())
        backup.backup_turns_db(db_path, keep=3, when=t0 + timedelta(seconds=index))
    items = backup.list_backups(db_path)
    assert len(items) == 3
    assert [item.name for item in items] == [
        "turns_2026-07-28_060004.db",
        "turns_2026-07-28_060003.db",
        "turns_2026-07-28_060002.db",
    ]