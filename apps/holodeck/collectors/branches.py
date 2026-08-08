"""Collect git branch state."""

import json
import subprocess
import time
from datetime import datetime

try:
    from apps.holodeck.collectors import branch_lineage as branch_lineage_collector
    from apps.holodeck.collectors import worktrees as worktrees_collector
except ImportError:
    from collectors import branch_lineage as branch_lineage_collector
    from collectors import worktrees as worktrees_collector

BRANCH_COMMIT_RECORD_SEPARATOR = "\x1e"
BRANCH_COMMIT_FIELD_SEPARATOR = "\x00"
BRANCH_COMMIT_LOG_FORMAT = "%x1e%h%x00%an%x00%cI%x00%B%x00"
PR_LIST_TIMEOUT_S = 15
PR_LIST_ATTEMPTS = 3
PR_LIST_RETRY_WAIT_S = 5

### Parsing
def short_sha(value):
    if not value:
        return None
    return value[:7]
def normalize_ref_name(refname):
    if refname.startswith("refs/heads/"):
        return refname[len("refs/heads/"):], "local"
    if refname.startswith("refs/remotes/origin/"):
        name = refname[len("refs/remotes/origin/"):]
        if name == "HEAD":
            return None, None
        return name, "remote"
    return None, None
def parse_for_each_ref(text):
    branches = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f")
        if len(parts) != 5:
            continue
        refname, tip, subject, date, author = parts
        name, kind = normalize_ref_name(refname)
        if not name:
            continue
        existing = branches.setdefault(name, {
            "name": name,
            "tip": short_sha(tip),
            "subject": subject,
            "date": date,
            "author": author,
            "local": False,
            "remote": False,
            "local_tip": None,
            "remote_tip": None,
            "worktree": None,
            "ahead_main": 0,
            "behind_main": 0,
            "pr": None,
            "parent": None,
            "purpose": None,
            "title_bar": None,
        })
        existing[kind] = True
        existing[kind + "_tip"] = tip
        if kind == "local" or not existing.get("tip"):
            existing["tip"] = short_sha(tip)
            existing["subject"] = subject
            existing["date"] = date
            existing["author"] = author
    return list(branches.values())
def parse_left_right_counts(text):
    parts = text.strip().split()
    if len(parts) != 2:
        return 0, 0
    return int(parts[0]), int(parts[1])
def split_commit_message(message):
    message = (message or "").strip("\n")
    if not message:
        return "", ""
    lines = message.splitlines()
    subject = lines[0]
    body = "\n".join(lines[1:]).lstrip("\n")
    return subject, body
def parse_branch_commit_log(text):
    commits = []
    for raw_record in text.split(BRANCH_COMMIT_RECORD_SEPARATOR):
        record = raw_record.lstrip("\n")
        if not record:
            continue
        parts = record.split(BRANCH_COMMIT_FIELD_SEPARATOR, 4)
        if len(parts) < 4:
            continue
        sha, author, date, message = parts[:4]
        subject, body = split_commit_message(message)
        commits.append({"sha": sha, "author": author, "date": date, "subject": subject, "body": body})
    return commits
def parse_pr_json(text):
    prs = {}
    for item in json.loads(text or "[]"):
        name = item.get("headRefName")
        if not name:
            continue
        prs[name] = {
            "number": item.get("number"),
            "title": item.get("title"),
            "state": item.get("state"),
            "is_draft": bool(item.get("isDraft")),
            "url": item.get("url"),
            "updated_at": item.get("updatedAt"),
        }
    return prs

### Gathering
def run_git(repo_root, args, timeout=15):
    return subprocess.run(
        ["git", "-C", str(repo_root)] + args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
def ref_for_branch(branch):
    if branch.get("local"):
        return "refs/heads/" + branch["name"]
    return "refs/remotes/origin/" + branch["name"]
def commit_date_iso(repo_root, sha):
    if not sha:
        return None
    command = run_git(repo_root, ["log", "-1", "--format=%cI", sha])
    if command.returncode != 0:
        return None
    return command.stdout.strip() or None
def parent_info(repo_root, name, fork_base, fork_date=None):
    return {
        "name": name,
        "fork_base": fork_base,
        "fork_base_date": fork_date or commit_date_iso(repo_root, fork_base),
    }
def lineage_parent_projection(repo_root, lineage):
    """Project only authoritative lineage into the compatibility parent field."""
    lineage = lineage or {}
    if not lineage.get("authoritative") or lineage.get("status") == "root":
        return None
    parent = lineage.get("parent_branch")
    fork = lineage.get("fork_commit")
    if not parent or not fork:
        return None
    result = parent_info(repo_root, parent, short_sha(fork), lineage.get("fork_date"))
    result.update({
        "status": lineage.get("status"),
        "source": "branch-lineage",
        "fork_commit": fork,
    })
    return result
def resolve_branch_ref(repo_root, branch_name):
    for ref in ("refs/heads/" + branch_name, "refs/remotes/origin/" + branch_name):
        command = run_git(repo_root, ["rev-parse", "--verify", "--quiet", ref])
        if command.returncode == 0 and command.stdout.strip():
            return ref
    return None
def load_branch_commits(repo_root, ref, skip, limit):
    command = run_git(repo_root, ["log", ref, "--skip=" + str(skip), "-n", str(limit + 1), "--format=" + BRANCH_COMMIT_LOG_FORMAT], timeout=20)
    if command.returncode != 0:
        raise RuntimeError(command.stderr.strip() or "git log failed")
    return parse_branch_commit_log(command.stdout)
GITHUB_PR_RATE_LIMIT_NOTE = (
    "PR data unavailable — GitHub API rate limit hit. "
    "Branch names and commits from this refresh are current; PR badges can't update until the limit resets (often a few hours)."
)
def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")
def parse_iso_datetime(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return parsed
def human_age(iso_value, now=None):
    then = parse_iso_datetime(iso_value)
    if then is None:
        return None
    current = now or datetime.now().astimezone()
    seconds = max(0, int((current - then).total_seconds()))
    if seconds < 60:
        return "0m ago"
    units = (("y", 31536000), ("mo", 2592000), ("d", 86400), ("h", 3600), ("m", 60))
    for label, size in units:
        if seconds >= size:
            return f"{seconds // size}{label} ago"
    return "0m ago"
def format_stamp(iso_value):
    then = parse_iso_datetime(iso_value)
    if then is None:
        return str(iso_value or "").strip() or None
    return then.astimezone().strftime("%Y-%m-%d %H:%M")
def previous_pr_map(previous_branches):
    mapped = {}
    for branch in previous_branches or []:
        name = branch.get("name")
        if name and branch.get("pr"):
            mapped[name] = branch.get("pr")
    return mapped
def pr_stale_note(cause, previous_pr_fetched_at=None, attempts=PR_LIST_ATTEMPTS):
    cause_text = str(cause or "").strip().lower()
    if "rate limit" in cause_text or "api rate limit" in cause_text:
        base = GITHUB_PR_RATE_LIMIT_NOTE
    elif "timed out" in cause_text or "timeout" in cause_text:
        base = (
            f"PR data is stale — GitHub pull-request lookup timed out after {attempts} tries. "
            "Branch names and commits from this refresh are current."
        )
    else:
        detail = str(cause or "").strip() or "lookup failed"
        if detail.lower().startswith("gh pr list failed:"):
            detail = detail.split(":", 1)[1].strip() or detail
        base = (
            f"PR data unavailable — GitHub pull-request lookup failed ({detail}). "
            "Branch names and commits from this refresh are current."
        )
    if previous_pr_fetched_at:
        age = human_age(previous_pr_fetched_at) or "earlier"
        stamp = format_stamp(previous_pr_fetched_at) or previous_pr_fetched_at
        return f"{base} PR badges last updated {age} ({stamp})."
    return base + " No earlier PR badges were available to keep."
def pr_list_error_note(message, previous_pr_fetched_at=None, attempts=PR_LIST_ATTEMPTS):
    return pr_stale_note(message, previous_pr_fetched_at=previous_pr_fetched_at, attempts=attempts)
def run_pr_list(repo_root, timeout=PR_LIST_TIMEOUT_S, runner=subprocess.run):
    return runner(
        ["gh", "pr", "list", "--state", "all", "--limit", "60", "--json", "number,title,state,isDraft,headRefName,url,updatedAt"],
        cwd=str(repo_root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
def load_prs(repo_root, attempts=PR_LIST_ATTEMPTS, timeout=PR_LIST_TIMEOUT_S, sleep_fn=time.sleep, runner=subprocess.run):
    last_error = "gh pr list failed"
    for attempt in range(1, max(1, attempts) + 1):
        try:
            command = run_pr_list(repo_root, timeout=timeout, runner=runner)
        except subprocess.TimeoutExpired:
            last_error = f"timed out after {timeout} seconds"
            if attempt < attempts:
                sleep_fn(PR_LIST_RETRY_WAIT_S)
            continue
        if command.returncode != 0:
            last_error = command.stderr.strip() or command.stdout.strip() or "gh pr list failed"
            if attempt < attempts:
                sleep_fn(PR_LIST_RETRY_WAIT_S)
            continue
        try:
            return parse_pr_json(command.stdout), None
        except Exception as exc:
            last_error = "gh pr list parse failed: " + str(exc)
            if attempt < attempts:
                sleep_fn(PR_LIST_RETRY_WAIT_S)
            continue
    return {}, last_error
def worktree_map(worktrees):
    mapped = {}
    for worktree in worktrees or []:
        branch = worktree.get("branch")
        if branch and branch != "detached":
            mapped[branch] = worktree.get("path")
    return mapped
def collect_branches(repo_root, worktrees=None, previous_branches=None, previous_meta=None):
    fmt = "%(refname)\x1f%(objectname)\x1f%(subject)\x1f%(committerdate:iso-strict)\x1f%(authorname)"
    command = run_git(repo_root, ["for-each-ref", "--format=" + fmt, "refs/heads", "refs/remotes/origin"])
    if command.returncode != 0:
        raise RuntimeError(command.stderr.strip() or "git for-each-ref failed")
    branches = parse_for_each_ref(command.stdout)
    wt_map = worktree_map(worktrees)
    prior_meta = previous_meta or {}
    prior_pr_fetched_at = prior_meta.get("pr_fetched_at")
    prs, pr_error = load_prs(repo_root)
    note = None
    pr_fetched_at = now_iso()
    if pr_error:
        prs = previous_pr_map(previous_branches)
        pr_fetched_at = prior_pr_fetched_at
        note = pr_stale_note(pr_error, previous_pr_fetched_at=prior_pr_fetched_at)
    color_rules = worktrees_collector.load_worktree_color_rules(repo_root)
    for branch in branches:
        counts = run_git(repo_root, ["rev-list", "--left-right", "--count", "origin/main..." + ref_for_branch(branch)])
        if counts.returncode == 0:
            branch["behind_main"], branch["ahead_main"] = parse_left_right_counts(counts.stdout)
        branch["worktree"] = wt_map.get(branch["name"])
        branch["pr"] = prs.get(branch["name"])
        branch["title_bar"] = worktrees_collector.title_bar_for_branch(branch["name"], worktrees, color_rules)
    lineage_map = branch_lineage_collector.collect_lineage_map(repo_root, branches)
    for branch in branches:
        name = branch["name"]
        branch["lineage"] = lineage_map.get(name)
        branch["parent"] = lineage_parent_projection(repo_root, branch["lineage"])
        branch["purpose"] = (
            branch["lineage"].get("branch_purpose")
            if branch["lineage"] and branch["lineage"].get("authoritative")
            else None
        )
    branches.sort(key=lambda item: (item.get("date") or "", item["name"]), reverse=True)
    return branches, note, {"pr_fetched_at": pr_fetched_at, "color_rules": color_rules}
