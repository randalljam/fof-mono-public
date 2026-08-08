"""Parse and validate durable branch-lineage commit records."""

import re
import subprocess
import uuid
from datetime import datetime

LOG_RECORD_SEPARATOR = "\x1e"
LOG_FIELD_SEPARATOR = "\x00"
LOG_FORMAT = "%x1e%H%x00%P%x00%T%x00%cI%x00%B%x00"
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*): (.+)$")
SUBJECT_RE = re.compile(
    r"^chore\(repo\): record branch lineage "
    r"(at branch start|late) for (.+)$"
)
SUBJECT_PREFIX = "chore(repo): record branch lineage "
BASE_FIELDS_V1 = [
    "Record-Type",
    "Lineage-Type",
    "Created-By",
    "Branch",
    "Parent-Branch",
    "Fork-Commit",
    "Fork-Subject",
    "Branch-Purpose",
]
BASE_FIELDS_V2 = [
    "Record-Type",
    "Lineage-Type",
    "Lineage-ID",
    "Record-ID",
    "Relationship",
    "Update-Reason",
    "Created-By",
    "Branch",
    "Parent-Branch",
    "Fork-Commit",
    "Fork-Subject",
    "Branch-Purpose",
]
CONDITIONAL_FIELDS_V2 = [
    "Related-Work",
    "Supersedes-Record-ID",
    "Supersedes-Record-Commit",
    "Previous-Record-Commit",
    "Previous-Fork-Commit",
    "Evidence-Commit",
    "Evidence-Artifact",
    "Evidence-Artifact-Blob",
]
EVIDENCE_FIELDS = [
    "Evidence-Type",
    "Evidence",
    "Confidence",
    "Review-Status",
    "Reviewed-By",
    "Reviewed-At",
]
ALL_FIELDS = set(
    BASE_FIELDS_V1
    + BASE_FIELDS_V2
    + CONDITIONAL_FIELDS_V2
    + EVIDENCE_FIELDS
    + ["Related-Work", "Lineage-Version"]
)
LINEAGE_TYPES = {"branch-start", "recorded-late"}
RELATIONSHIPS = {"created-from", "rerooted-to"}
UPDATE_REASONS = {
    "initial",
    "late-migration",
    "correction",
    "reroot",
    "rebase",
    "history-rewrite",
}
CONFIDENCE_VALUES = {"high", "medium", "low"}
REVIEW_STATUSES = {"pending", "approved"}

### Message parsing
def error(code, message):
    return {"code": code, "message": message}
def canonical_uuid(value):
    try:
        parsed = uuid.UUID(value)
    except (AttributeError, ValueError):
        return False
    return str(parsed) == value and value == value.lower()
def valid_timestamp(value):
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return parsed.tzinfo is not None
def subject_identity(subject):
    match = SUBJECT_RE.fullmatch(subject or "")
    if not match:
        return None, None
    timing = "branch-start" if match.group(1) == "at branch start" else "recorded-late"
    return timing, match.group(2)
def loose_body_branch(message):
    matches = re.findall(r"^Branch:\s*(.+?)\s*$", message or "", re.MULTILINE)
    return matches[0] if len(matches) == 1 else None
def is_lineage_candidate(message):
    subject = (message or "").splitlines()[0] if message else ""
    return subject.startswith(SUBJECT_PREFIX) or bool(
        re.search(r"^Record-Type:\s*branch-lineage\s*$", message or "", re.MULTILINE)
    )
def candidate_applies(message, branch_name):
    subject = (message or "").splitlines()[0] if message else ""
    _, subject_branch = subject_identity(subject)
    body_branch = loose_body_branch(message)
    identities = [value for value in (subject_branch, body_branch) if value]
    if branch_name in identities:
        return True
    return not identities
def ordered_fields_for(version, lineage_type, fields):
    if version == "1":
        ordered = list(BASE_FIELDS_V1)
        if "Related-Work" in fields:
            ordered.append("Related-Work")
        if lineage_type == "recorded-late":
            ordered.extend(["Evidence-Type", "Evidence", "Confidence", "Review-Status"])
            if fields.get("Review-Status") == "approved":
                ordered.extend(["Reviewed-By", "Reviewed-At"])
        ordered.append("Lineage-Version")
        return ordered
    ordered = list(BASE_FIELDS_V2)
    for name in CONDITIONAL_FIELDS_V2:
        if name in fields:
            ordered.append(name)
    if lineage_type == "recorded-late":
        ordered.extend(["Evidence-Type", "Evidence", "Confidence", "Review-Status"])
        if fields.get("Review-Status") == "approved":
            ordered.extend(["Reviewed-By", "Reviewed-At"])
    ordered.append("Lineage-Version")
    return ordered
def parse_lineage_message(message):
    raw = (message or "").rstrip("\n")
    lines = raw.splitlines()
    problems = []
    subject = lines[0] if lines else ""
    timing, subject_branch = subject_identity(subject)
    if not timing:
        problems.append(error("subject-invalid", "Lineage subject is not exact."))
    if len(lines) < 3 or lines[1] != "":
        problems.append(error("body-separator-invalid", "Subject must be followed by one blank line."))
        body_lines = lines[1:]
    else:
        body_lines = lines[2:]
    if any(line == "" for line in body_lines):
        problems.append(error("body-blank-line", "Lineage fields cannot contain blank lines."))
    fields = {}
    field_names = []
    for line in body_lines:
        if not line:
            continue
        match = FIELD_RE.fullmatch(line)
        if not match:
            problems.append(error("field-syntax-invalid", "Malformed lineage field: " + line))
            continue
        name, value = match.groups()
        field_names.append(name)
        if name in fields:
            problems.append(error("field-duplicate", "Duplicate field: " + name))
            continue
        fields[name] = value
        if name not in ALL_FIELDS:
            problems.append(error("field-unknown", "Unknown field: " + name))
    version = fields.get("Lineage-Version")
    lineage_type = fields.get("Lineage-Type")
    if version in ("1", "2"):
        expected_order = ordered_fields_for(version, lineage_type, fields)
        if field_names != expected_order:
            problems.append(error(
                "field-order-invalid",
                "Fields must exactly match the canonical order for this record type.",
            ))
    if fields.get("Record-Type") != "branch-lineage":
        problems.append(error("record-type-invalid", "Record-Type must be branch-lineage."))
    if lineage_type not in LINEAGE_TYPES:
        problems.append(error("lineage-type-invalid", "Lineage-Type is unsupported."))
    if timing and lineage_type and timing != lineage_type:
        problems.append(error("subject-type-mismatch", "Subject and Lineage-Type disagree."))
    if subject_branch and fields.get("Branch") and subject_branch != fields["Branch"]:
        problems.append(error("subject-branch-mismatch", "Subject and Branch disagree."))
    if version != "1":
        if not canonical_uuid(fields.get("Lineage-ID")):
            problems.append(error("lineage-id-invalid", "Lineage-ID must be a lowercase canonical UUID."))
        if not canonical_uuid(fields.get("Record-ID")):
            problems.append(error("record-id-invalid", "Record-ID must be a lowercase canonical UUID."))
        if fields.get("Supersedes-Record-ID") and not canonical_uuid(fields["Supersedes-Record-ID"]):
            problems.append(error("supersedes-id-invalid", "Supersedes-Record-ID must be a lowercase canonical UUID."))
        if fields.get("Relationship") not in RELATIONSHIPS:
            problems.append(error("relationship-invalid", "Relationship is unsupported."))
        if fields.get("Update-Reason") not in UPDATE_REASONS:
            problems.append(error("update-reason-invalid", "Update-Reason is unsupported."))
    if version not in ("1", "2"):
        problems.append(error("version-unsupported", "Lineage-Version is unsupported."))
    for name in ("Created-By", "Branch", "Parent-Branch", "Fork-Subject", "Branch-Purpose"):
        if not fields.get(name):
            problems.append(error("field-required", name + " is required."))
    if fields.get("Branch") == fields.get("Parent-Branch") and fields.get("Branch"):
        problems.append(error("parent-self", "A branch cannot declare itself as parent."))
    if not FULL_SHA_RE.fullmatch(fields.get("Fork-Commit") or ""):
        problems.append(error("fork-sha-invalid", "Fork-Commit must be a full lowercase SHA."))
    for name in (
        "Supersedes-Record-Commit",
        "Previous-Record-Commit",
        "Previous-Fork-Commit",
        "Evidence-Commit",
        "Evidence-Artifact-Blob",
    ):
        if fields.get(name) and not FULL_SHA_RE.fullmatch(fields[name]):
            problems.append(error("full-sha-invalid", name + " must be a full lowercase SHA."))
    if lineage_type == "branch-start":
        if version == "2" and fields.get("Relationship") != "created-from":
            problems.append(error("branch-start-relationship", "Branch-start must use created-from."))
        if version == "2" and fields.get("Update-Reason") != "initial":
            problems.append(error("branch-start-reason", "Branch-start must use initial."))
    if lineage_type == "recorded-late":
        if fields.get("Confidence") not in CONFIDENCE_VALUES:
            problems.append(error("confidence-invalid", "Confidence is unsupported."))
        if fields.get("Review-Status") not in REVIEW_STATUSES:
            problems.append(error("review-status-invalid", "Review-Status is unsupported."))
        if fields.get("Review-Status") == "approved":
            if not fields.get("Reviewed-By"):
                problems.append(error("reviewer-required", "Approved records require Reviewed-By."))
            if not valid_timestamp(fields.get("Reviewed-At")):
                problems.append(error("reviewed-at-invalid", "Reviewed-At must be an ISO-8601 timestamp with timezone."))
    return {
        "subject": subject,
        "subject_branch": subject_branch,
        "subject_lineage_type": timing,
        "fields": fields,
        "field_names": field_names,
        "version": version,
        "errors": problems,
    }

### Git access
def run_git(repo_root, args, timeout=30):
    return subprocess.run(
        ["git", "-C", str(repo_root)] + args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
def git_value(repo_root, args):
    command = run_git(repo_root, args)
    if command.returncode != 0:
        return None
    return command.stdout.strip()
def full_sha(repo_root, value):
    return git_value(repo_root, ["rev-parse", "--verify", value + "^{commit}"])
def commit_exists(repo_root, sha):
    if not FULL_SHA_RE.fullmatch(sha or ""):
        return False
    return run_git(repo_root, ["cat-file", "-e", sha + "^{commit}"]).returncode == 0
def commit_subject(repo_root, sha):
    return git_value(repo_root, ["show", "-s", "--format=%s", sha])
def commit_date_iso(repo_root, sha):
    return git_value(repo_root, ["show", "-s", "--format=%cI", sha])
def commit_parents(repo_root, sha):
    value = git_value(repo_root, ["show", "-s", "--format=%P", sha])
    return value.split() if value is not None else []
def commit_tree(repo_root, sha):
    return git_value(repo_root, ["show", "-s", "--format=%T", sha])
def is_ancestor(repo_root, ancestor, descendant):
    return run_git(repo_root, ["merge-base", "--is-ancestor", ancestor, descendant]).returncode == 0
def first_parent_contains(repo_root, tip, sha):
    command = run_git(repo_root, ["rev-list", "--first-parent", tip])
    return command.returncode == 0 and sha in command.stdout.splitlines()
def parse_log(text):
    commits = []
    for raw in (text or "").split(LOG_RECORD_SEPARATOR):
        record = raw.lstrip("\n")
        if not record:
            continue
        parts = record.split(LOG_FIELD_SEPARATOR, 5)
        if len(parts) < 5:
            continue
        sha, parents, tree, date, message = parts[:5]
        commits.append({
            "commit": sha,
            "parents": parents.split(),
            "tree": tree,
            "date": date,
            "message": message.rstrip("\n"),
        })
    return commits
def first_parent_log(repo_root, tip):
    command = run_git(repo_root, ["log", "--first-parent", "--format=" + LOG_FORMAT, tip])
    if command.returncode != 0:
        return []
    return parse_log(command.stdout)
def ref_tips(repo_root, branch_name):
    local = full_sha(repo_root, "refs/heads/" + branch_name)
    remote = full_sha(repo_root, "refs/remotes/origin/" + branch_name)
    return local, remote
def resolved_branch_tip(repo_root, branch):
    name = branch.get("name")
    local = branch.get("local_tip")
    remote = branch.get("remote_tip")
    if local is None and branch.get("local"):
        local = full_sha(repo_root, "refs/heads/" + name)
    if remote is None and branch.get("remote"):
        remote = full_sha(repo_root, "refs/remotes/origin/" + name)
    if local and remote and local != remote:
        return None, local, remote
    tip = local or remote
    if not tip and branch.get("tip"):
        tip = full_sha(repo_root, branch["tip"])
    return tip, local, remote
def resolved_parent_tip(repo_root, parent_name):
    local, remote = ref_tips(repo_root, parent_name)
    if local and remote and local != remote:
        return None, "diverged"
    if not local and not remote:
        return None, "missing"
    return local or remote, None

### Validation
def normalize_record(parsed, commit):
    fields = parsed["fields"]
    version = parsed["version"]
    lineage_type = fields.get("Lineage-Type")
    relationship = fields.get("Relationship")
    update_reason = fields.get("Update-Reason")
    evidence_commit = fields.get("Evidence-Commit")
    if version == "1":
        relationship = (
            "rerooted-to"
            if fields.get("Evidence-Type") == "explicit-reroot-merge"
            else "created-from"
        )
        update_reason = "initial" if lineage_type == "branch-start" else "late-migration"
        if relationship == "rerooted-to":
            match = re.search(r"\b[0-9a-f]{40}\b", fields.get("Evidence") or "")
            evidence_commit = match.group(0) if match else None
    return {
        "commit": commit["commit"],
        "version": version,
        "lineage_type": lineage_type,
        "lineage_id": fields.get("Lineage-ID"),
        "record_id": fields.get("Record-ID"),
        "relationship": relationship,
        "update_reason": update_reason,
        "created_by": fields.get("Created-By"),
        "branch": fields.get("Branch"),
        "parent_branch": fields.get("Parent-Branch"),
        "fork_commit": fields.get("Fork-Commit"),
        "fork_subject": fields.get("Fork-Subject"),
        "branch_purpose": fields.get("Branch-Purpose"),
        "related_work": fields.get("Related-Work"),
        "supersedes_record_id": fields.get("Supersedes-Record-ID"),
        "supersedes_record_commit": fields.get("Supersedes-Record-Commit"),
        "previous_record_commit": fields.get("Previous-Record-Commit"),
        "previous_fork_commit": fields.get("Previous-Fork-Commit"),
        "evidence_commit": evidence_commit,
        "evidence_artifact": fields.get("Evidence-Artifact"),
        "evidence_artifact_blob": fields.get("Evidence-Artifact-Blob"),
        "evidence_type": fields.get("Evidence-Type"),
        "evidence": fields.get("Evidence"),
        "confidence": fields.get("Confidence"),
        "review_status": fields.get("Review-Status"),
        "reviewed_by": fields.get("Reviewed-By"),
        "reviewed_at": fields.get("Reviewed-At"),
        "date": commit.get("date"),
    }
def validate_empty_commit(repo_root, commit, problems):
    if len(commit["parents"]) != 1:
        problems.append(error("record-parent-count", "Lineage record must have exactly one Git parent."))
        return
    parent_tree = commit_tree(repo_root, commit["parents"][0])
    if not parent_tree or parent_tree != commit["tree"]:
        problems.append(error("record-not-empty", "Lineage record commit must not change the tree."))
def validate_fork(repo_root, record, tip, parent_tip, problems):
    fork = record.get("fork_commit")
    if not commit_exists(repo_root, fork):
        problems.append(error("fork-missing", "Fork-Commit does not resolve."))
        return
    actual_subject = commit_subject(repo_root, fork)
    if actual_subject != record.get("fork_subject"):
        problems.append(error("fork-subject-mismatch", "Fork-Subject does not match Git."))
    if not is_ancestor(repo_root, fork, tip):
        problems.append(error("fork-not-on-child", "Fork-Commit is not reachable from the branch tip."))
    if not first_parent_contains(repo_root, parent_tip, fork):
        problems.append(error("fork-not-on-parent", "Fork-Commit is not on the parent first-parent history."))
def validate_created_from(repo_root, record, tip, problems):
    fork = record.get("fork_commit")
    if not FULL_SHA_RE.fullmatch(fork or "") or not commit_exists(repo_root, fork):
        return
    command = run_git(repo_root, ["rev-list", "--first-parent", "--reverse", fork + ".." + tip])
    if command.returncode != 0 or not command.stdout.splitlines():
        problems.append(error("first-parent-root-missing", "No first-parent branch root follows Fork-Commit."))
        return
    first = command.stdout.splitlines()[0]
    parents = commit_parents(repo_root, first)
    if not parents or parents[0] != fork:
        problems.append(error("first-parent-root-mismatch", "Earliest child first-parent commit does not follow Fork-Commit."))
def validate_reroot(repo_root, record, tip, problems):
    evidence = record.get("evidence_commit")
    if not FULL_SHA_RE.fullmatch(evidence or "") or not commit_exists(repo_root, evidence):
        problems.append(error("evidence-commit-missing", "Reroot requires a resolvable full Evidence-Commit."))
        return
    if not first_parent_contains(repo_root, tip, evidence):
        problems.append(error("evidence-not-on-child", "Evidence-Commit is not on the child first-parent history."))
    parents = commit_parents(repo_root, evidence)
    if len(parents) < 2:
        problems.append(error("evidence-not-merge", "Evidence-Commit must be a merge."))
    elif parents[1] != record.get("fork_commit"):
        problems.append(error("evidence-second-parent", "Evidence-Commit second parent must equal Fork-Commit."))
def validate_branch_start(repo_root, record, commit, tip, problems):
    fork = record.get("fork_commit")
    if not FULL_SHA_RE.fullmatch(fork or "") or not commit_exists(repo_root, fork):
        return
    if len(commit["parents"]) == 1 and commit["parents"][0] != record.get("fork_commit"):
        problems.append(error("branch-start-parent", "Branch-start Git parent must equal Fork-Commit."))
    command = run_git(
        repo_root,
        ["rev-list", "--first-parent", "--reverse", fork + ".." + tip],
    )
    first = command.stdout.splitlines()[0] if command.returncode == 0 and command.stdout.splitlines() else None
    if first != commit["commit"]:
        problems.append(error("branch-start-not-first", "Branch-start must be the first unique commit."))
def parse_rewrite_map(text):
    lines = (text or "").splitlines()
    problems = []
    mappings = {}
    if not lines or lines[0] != "kind\told-sha\tnew-sha":
        return mappings, [error("rewrite-map-header", "Rewrite map header is invalid.")]
    rows = []
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) != 3:
            problems.append(error("rewrite-map-row", "Rewrite map row is malformed."))
            continue
        kind, old_sha, new_sha = parts
        if kind not in ("record", "fork"):
            problems.append(error("rewrite-map-kind", "Rewrite map kind is unsupported."))
        if not FULL_SHA_RE.fullmatch(old_sha) or not FULL_SHA_RE.fullmatch(new_sha):
            problems.append(error("rewrite-map-sha", "Rewrite map SHAs must be full lowercase hashes."))
        key = (kind, old_sha)
        if key in mappings:
            problems.append(error("rewrite-map-duplicate", "Rewrite map contains a duplicate key."))
        mappings[key] = new_sha
        rows.append((kind, old_sha, new_sha))
    if rows != sorted(rows, key=lambda row: (row[0], row[1])):
        problems.append(error("rewrite-map-order", "Rewrite map rows must be sorted by kind and old SHA."))
    return mappings, problems
def safe_artifact_path(value):
    return bool(value) and not value.startswith("/") and ".." not in value.split("/")
def validate_rewrite_evidence(repo_root, record, all_candidates, problems):
    path = record.get("evidence_artifact")
    blob = record.get("evidence_artifact_blob")
    commit = record.get("commit")
    if not safe_artifact_path(path):
        problems.append(error("evidence-artifact-path", "Evidence-Artifact must be a safe repo-relative path."))
        return
    actual_blob = git_value(repo_root, ["rev-parse", commit + ":" + path])
    if not actual_blob or actual_blob != blob or not FULL_SHA_RE.fullmatch(blob or ""):
        problems.append(error("evidence-artifact-blob", "Evidence artifact blob does not match the record."))
        return
    command = run_git(repo_root, ["show", commit + ":" + path])
    if command.returncode != 0:
        problems.append(error("evidence-artifact-missing", "Evidence artifact is not tracked in the record tree."))
        return
    mappings, map_problems = parse_rewrite_map(command.stdout)
    problems.extend(map_problems)
    old_record = record.get("previous_record_commit")
    old_fork = record.get("previous_fork_commit")
    new_record = mappings.get(("record", old_record))
    new_fork = mappings.get(("fork", old_fork))
    if new_fork != record.get("fork_commit"):
        problems.append(error("rewrite-fork-mapping", "Rewrite map does not connect the old and current fork."))
    recreated = next(
        (
            candidate for candidate in all_candidates
            if candidate["commit"]["commit"] == new_record
        ),
        None,
    )
    if not recreated:
        problems.append(error("rewrite-record-mapping", "Rewrite map target record is not on first-parent history."))
        return
    parsed = recreated["parsed"]
    if parsed["fields"].get("Record-ID") != record.get("supersedes_record_id"):
        problems.append(error("rewrite-record-id", "Recreated record does not carry the superseded Record-ID."))
def validate_v2_conditions(record, predecessor, problems):
    reason = record.get("update_reason")
    supersedes_id = record.get("supersedes_record_id")
    supersedes_commit = record.get("supersedes_record_commit")
    if supersedes_id and supersedes_commit:
        problems.append(error("supersession-exclusive", "Use exactly one supersession field."))
    requires_predecessor = reason in {"correction", "reroot", "rebase", "history-rewrite"}
    if requires_predecessor and not predecessor:
        problems.append(error("predecessor-missing", "This update reason requires a predecessor record."))
        return
    if not requires_predecessor and (supersedes_id or supersedes_commit):
        problems.append(error("supersession-unexpected", "This update reason cannot supersede a predecessor."))
    if reason == "initial" and record.get("lineage_type") != "branch-start":
        problems.append(error("initial-not-start", "Update-Reason initial requires branch-start."))
    if reason != "initial" and record.get("lineage_type") == "branch-start":
        problems.append(error("start-reason-invalid", "Branch-start requires Update-Reason initial."))
    if reason == "late-migration" and predecessor:
        problems.append(error("late-migration-has-predecessor", "Late migration must be the first lineage record."))
    if reason == "reroot" and record.get("relationship") != "rerooted-to":
        problems.append(error("reroot-relationship", "Reroot update requires Relationship rerooted-to."))
    if reason == "reroot" and record.get("evidence_type") != "explicit-reroot-merge":
        problems.append(error("reroot-evidence-type", "Reroot updates require explicit-reroot-merge evidence."))
    if reason in {"rebase", "history-rewrite"}:
        for name, value in (
            ("Previous-Record-Commit", record.get("previous_record_commit")),
            ("Previous-Fork-Commit", record.get("previous_fork_commit")),
            ("Evidence-Artifact", record.get("evidence_artifact")),
            ("Evidence-Artifact-Blob", record.get("evidence_artifact_blob")),
        ):
            if not value:
                problems.append(error("rewrite-field-required", name + " is required."))
        expected_evidence = "rebase-map" if reason == "rebase" else "history-rewrite-map"
        if record.get("evidence_type") != expected_evidence:
            problems.append(error("rewrite-evidence-type", "Rewrite evidence type does not match Update-Reason."))
    if record.get("relationship") == "rerooted-to" and not record.get("evidence_commit"):
        problems.append(error("evidence-commit-required", "Rerooted relationships require Evidence-Commit."))
    if not predecessor:
        return
    predecessor_fields = predecessor["parsed"]["fields"]
    predecessor_version = predecessor["parsed"]["version"]
    if predecessor_version == "2":
        if supersedes_id != predecessor_fields.get("Record-ID"):
            problems.append(error("supersedes-id-mismatch", "Supersedes-Record-ID does not identify the predecessor."))
        if record.get("lineage_id") != predecessor_fields.get("Lineage-ID"):
            problems.append(error("lineage-id-mismatch", "A v2 update must reuse the predecessor Lineage-ID."))
    elif predecessor_version == "1":
        if supersedes_commit != predecessor["commit"]["commit"]:
            problems.append(error("supersedes-commit-mismatch", "Supersedes-Record-Commit does not identify the v1 predecessor."))
    old_fork = predecessor_fields.get("Fork-Commit")
    if old_fork and old_fork != record.get("fork_commit") and record.get("previous_fork_commit") != old_fork:
        problems.append(error("previous-fork-required", "Changed forks require Previous-Fork-Commit."))
def linked_predecessor(selected, candidates):
    fields = selected["parsed"]["fields"]
    current_branch = fields.get("Branch")
    older = candidates[candidates.index(selected) + 1:]
    applicable = [
        candidate for candidate in older
        if candidate["parsed"]["fields"].get("Branch") == current_branch
    ]
    if applicable:
        return applicable[0]
    supersedes_id = fields.get("Supersedes-Record-ID")
    if supersedes_id:
        return next(
            (
                candidate for candidate in older
                if candidate["parsed"]["fields"].get("Record-ID") == supersedes_id
            ),
            None,
        )
    supersedes_commit = fields.get("Supersedes-Record-Commit")
    if supersedes_commit:
        return next(
            (
                candidate for candidate in older
                if candidate["commit"]["commit"] == supersedes_commit
            ),
            None,
        )
    return None
def selected_supersession_cycle(selected, candidates):
    selected_id = selected["parsed"]["fields"].get("Record-ID")
    if not selected_id:
        return False
    edges = {}
    for candidate in candidates:
        fields = candidate["parsed"]["fields"]
        record_id = fields.get("Record-ID")
        target_id = fields.get("Supersedes-Record-ID")
        if record_id and target_id:
            edges[record_id] = target_id
    seen = set()
    current = selected_id
    while current in edges:
        if current in seen:
            return current == selected_id
        seen.add(current)
        current = edges[current]
    return False
def history_summary(candidate):
    parsed = candidate["parsed"]
    fields = parsed["fields"]
    return {
        "commit": candidate["commit"]["commit"],
        "version": parsed["version"],
        "branch": fields.get("Branch"),
        "lineage_type": fields.get("Lineage-Type"),
        "relationship": fields.get("Relationship"),
        "update_reason": fields.get("Update-Reason"),
        "lineage_id": fields.get("Lineage-ID"),
        "record_id": fields.get("Record-ID"),
        "review_status": fields.get("Review-Status"),
        "parse_valid": not parsed["errors"],
    }
def base_result(status, authoritative=False):
    return {
        "status": status,
        "authoritative": authoritative,
        "branch": None,
        "parent_branch": None,
        "fork_commit": None,
        "fork_date": None,
        "fork_subject": None,
        "branch_purpose": None,
        "record": None,
        "errors": [],
        "history": [],
    }
def collect_branch_lineage(repo_root, branch):
    name = branch.get("name")
    if name == "main":
        result = base_result("root", True)
        result["branch"] = "main"
        return result
    tip, local_tip, remote_tip = resolved_branch_tip(repo_root, branch)
    if local_tip and remote_tip and local_tip != remote_tip:
        result = base_result("ref-diverged")
        result["branch"] = name
        result["errors"] = [error("ref-diverged", "Local and origin branch tips differ.")]
        return result
    if not tip:
        result = base_result("missing")
        result["branch"] = name
        result["errors"] = [error("branch-ref-missing", "Branch tip does not resolve.")]
        return result
    commits = first_parent_log(repo_root, tip)
    candidates = []
    for commit in commits:
        if not is_lineage_candidate(commit["message"]):
            continue
        parsed = parse_lineage_message(commit["message"])
        candidates.append({"commit": commit, "parsed": parsed})
    selected = next(
        (
            candidate for candidate in candidates
            if candidate_applies(candidate["commit"]["message"], name)
        ),
        None,
    )
    if not selected:
        result = base_result("missing")
        result["branch"] = name
        result["history"] = [history_summary(candidate) for candidate in candidates]
        return result
    parsed = selected["parsed"]
    record = normalize_record(parsed, selected["commit"])
    applicable_history = [
        candidate for candidate in candidates
        if candidate["parsed"]["fields"].get("Branch") == name or candidate is selected
    ]
    result = base_result("invalid")
    result.update({
        "branch": name,
        "parent_branch": record.get("parent_branch"),
        "fork_commit": record.get("fork_commit"),
        "fork_subject": record.get("fork_subject"),
        "branch_purpose": record.get("branch_purpose"),
        "record": record,
        "history": [history_summary(candidate) for candidate in applicable_history],
    })
    problems = list(parsed["errors"])
    if record.get("branch") != name:
        problems.append(error("branch-mismatch", "Record Branch does not match the ref being collected."))
    validate_empty_commit(repo_root, selected["commit"], problems)
    if parsed["version"] not in ("1", "2"):
        result["status"] = "unsupported"
        result["errors"] = problems
        return result
    parent_tip, parent_problem = resolved_parent_tip(repo_root, record.get("parent_branch") or "")
    if parent_problem == "missing":
        result["status"] = "parent-ref-missing"
        problems.append(error("parent-ref-missing", "Declared parent ref does not exist."))
        result["errors"] = problems
        return result
    if parent_problem == "diverged":
        result["status"] = "ref-diverged"
        problems.append(error("parent-ref-diverged", "Declared parent local and origin refs differ."))
        result["errors"] = problems
        return result
    validate_fork(repo_root, record, tip, parent_tip, problems)
    predecessor = linked_predecessor(selected, candidates)
    if parsed["version"] == "2":
        validate_v2_conditions(record, predecessor, problems)
        selected_record_id = record.get("record_id")
        same_ids = [
            candidate for candidate in candidates
            if candidate["parsed"]["fields"].get("Record-ID") == selected_record_id
        ]
        if selected_record_id and len(same_ids) > 1:
            problems.append(error("record-id-duplicate-history", "Record-ID is duplicated on first-parent history."))
        if selected_supersession_cycle(selected, candidates):
            problems.append(error("supersession-cycle", "Supersession links form a cycle through the selected record."))
    if record.get("lineage_type") == "branch-start":
        validate_branch_start(repo_root, record, selected["commit"], tip, problems)
    elif record.get("relationship") == "rerooted-to":
        validate_reroot(repo_root, record, tip, problems)
    else:
        validate_created_from(repo_root, record, tip, problems)
    if record.get("update_reason") in {"rebase", "history-rewrite"}:
        validate_rewrite_evidence(repo_root, record, candidates, problems)
    result["errors"] = problems
    if problems:
        result["status"] = "invalid"
    elif record.get("review_status") == "pending":
        result["status"] = "pending"
    elif record.get("lineage_type") == "branch-start":
        result["status"] = "structurally-verified"
        result["authoritative"] = True
    else:
        result["status"] = "evidence-validated"
        result["authoritative"] = True
    if result["authoritative"] and result["status"] != "root":
        result["fork_date"] = commit_date_iso(repo_root, record.get("fork_commit"))
    return result
def cycle_nodes(results):
    edges = {
        name: value.get("parent_branch")
        for name, value in results.items()
        if value.get("record") and value.get("parent_branch")
    }
    found = set()
    for start in edges:
        positions = {}
        path = []
        current = start
        while current in edges:
            if current in positions:
                found.update(path[positions[current]:])
                break
            if current in found:
                break
            positions[current] = len(path)
            path.append(current)
            current = edges[current]
    return found
def apply_global_validation(results):
    record_ids = {}
    lineage_ids = {}
    for branch_name, result in results.items():
        record = result.get("record") or {}
        record_id = record.get("record_id")
        lineage_id = record.get("lineage_id")
        if record_id:
            record_ids.setdefault(record_id, []).append(branch_name)
        if lineage_id:
            lineage_ids.setdefault(lineage_id, []).append(branch_name)
    duplicate_records = {
        branch for names in record_ids.values() if len(set(names)) > 1 for branch in names
    }
    duplicate_lineages = {
        branch for names in lineage_ids.values() if len(set(names)) > 1 for branch in names
    }
    cycles = cycle_nodes(results)
    for branch_name, result in results.items():
        added = []
        if branch_name in duplicate_records:
            added.append(error("record-id-duplicate", "Record-ID is selected by multiple open branches."))
        if branch_name in duplicate_lineages:
            added.append(error("lineage-id-conflict", "Lineage-ID is selected by multiple open branches."))
        if branch_name in cycles:
            added.append(error("parent-cycle", "Declared parent relationships form a cycle."))
        if added:
            result["errors"].extend(added)
            result["status"] = "invalid"
            result["authoritative"] = False
            result["fork_date"] = None
    return results
def collect_lineage_map(repo_root, branches):
    results = {
        branch["name"]: collect_branch_lineage(repo_root, branch)
        for branch in branches
        if branch.get("name")
    }
    return apply_global_validation(results)
