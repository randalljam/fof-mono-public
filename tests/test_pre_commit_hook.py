import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO_ROOT / "scripts" / "git" / "hooks" / "pre-commit"


def _run(repo, *args, check=True):
    return subprocess.run(
        args,
        cwd=repo,
        check=check,
        capture_output=True,
        text=True,
    )
def _init_repo(repo):
    _run(repo, "git", "init", "-q")
    _run(repo, "git", "config", "user.email", "test@example.com")
    _run(repo, "git", "config", "user.name", "Test User")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _run(repo, "git", "add", "README.md")
    _run(repo, "git", "commit", "-q", "-m", "base")
def test_hook_allows_blocked_type_already_tracked_by_merge_parent(tmp_path):
    _init_repo(tmp_path)
    _run(tmp_path, "git", "checkout", "-q", "-b", "incoming")
    (tmp_path / "tracked.png").write_bytes(b"already committed upstream")
    _run(tmp_path, "git", "add", "tracked.png")
    _run(tmp_path, "git", "commit", "-q", "-m", "add upstream asset")
    _run(tmp_path, "git", "checkout", "-q", "master")
    _run(tmp_path, "git", "merge", "--no-commit", "--no-ff", "incoming")

    result = _run(tmp_path, "bash", str(HOOK_PATH), check=False)

    assert result.returncode == 0, result.stderr
def test_hook_blocks_genuinely_new_binary(tmp_path):
    _init_repo(tmp_path)
    (tmp_path / "new.png").write_bytes(b"new local binary")
    _run(tmp_path, "git", "add", "new.png")

    result = _run(tmp_path, "bash", str(HOOK_PATH), check=False)

    assert result.returncode == 1
    assert "new.png" in result.stderr
