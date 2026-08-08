import subprocess
import uuid

import pytest

from apps.holodeck.collectors.branch_lineage import (
    apply_global_validation,
    collect_branch_lineage,
    parse_lineage_message,
    parse_rewrite_map,
)

REVIEWED_AT = "2026-07-30T09:48:16-07:00"
CREATED_BY = "Codex Subagent (fable5-w-codex) - GPT 5.6 Sol xhigh"

### Helpers
def git(repo, *args, input_text=None):
    command = subprocess.run(
        ["git", "-C", str(repo)] + list(args),
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert command.returncode == 0, command.stderr
    return command.stdout.strip()
def init_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Lineage Test")
    git(repo, "config", "user.email", "lineage@example.com")
    (repo / "root.txt").write_text("root\n", encoding="utf-8")
    git(repo, "add", "root.txt")
    git(repo, "commit", "-m", "root")
    return repo, git(repo, "rev-parse", "HEAD")
def new_id():
    return str(uuid.uuid4())
def commit_message(subject, fields):
    return subject + "\n\n" + "\n".join(name + ": " + value for name, value in fields) + "\n"
def commit_empty(repo, message):
    git(repo, "commit", "--allow-empty", "-F", "-", input_text=message)
    return git(repo, "rev-parse", "HEAD")
def commit_file(repo, name, text, subject):
    (repo / name).write_text(text, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-m", subject)
    return git(repo, "rev-parse", "HEAD")
def branch(repo, name, start="HEAD"):
    git(repo, "switch", "-c", name, start)
def branch_row(name, local=True, remote=False):
    return {"name": name, "local": local, "remote": remote}
def v1_start_fields(branch_name, parent, fork, fork_subject="root"):
    return [
        ("Record-Type", "branch-lineage"),
        ("Lineage-Type", "branch-start"),
        ("Created-By", CREATED_BY),
        ("Branch", branch_name),
        ("Parent-Branch", parent),
        ("Fork-Commit", fork),
        ("Fork-Subject", fork_subject),
        ("Branch-Purpose", "Exercise durable lineage."),
        ("Lineage-Version", "1"),
    ]
def v1_late_fields(branch_name, parent, fork, evidence_type="first-parent-root"):
    return [
        ("Record-Type", "branch-lineage"),
        ("Lineage-Type", "recorded-late"),
        ("Created-By", CREATED_BY),
        ("Branch", branch_name),
        ("Parent-Branch", parent),
        ("Fork-Commit", fork),
        ("Fork-Subject", git_subject_placeholder(fork)),
        ("Branch-Purpose", "Exercise durable lineage."),
        ("Evidence-Type", evidence_type),
        ("Evidence", "Git first-parent evidence validates the declared fork."),
        ("Confidence", "high"),
        ("Review-Status", "approved"),
        ("Reviewed-By", "Randy True"),
        ("Reviewed-At", REVIEWED_AT),
        ("Lineage-Version", "1"),
    ]
def git_subject_placeholder(_fork):
    return "root"
def v2_fields(
    branch_name,
    parent,
    fork,
    lineage_type="recorded-late",
    lineage_id=None,
    record_id=None,
    relationship="created-from",
    update_reason="late-migration",
    extras=None,
    review_status="approved",
):
    fields = [
        ("Record-Type", "branch-lineage"),
        ("Lineage-Type", lineage_type),
        ("Lineage-ID", lineage_id or new_id()),
        ("Record-ID", record_id or new_id()),
        ("Relationship", relationship),
        ("Update-Reason", update_reason),
        ("Created-By", CREATED_BY),
        ("Branch", branch_name),
        ("Parent-Branch", parent),
        ("Fork-Commit", fork),
        ("Fork-Subject", "root"),
        ("Branch-Purpose", "Exercise durable lineage."),
    ]
    fields.extend(extras or [])
    if lineage_type == "recorded-late":
        evidence_type = {
            "reroot": "explicit-reroot-merge",
            "rebase": "rebase-map",
            "history-rewrite": "history-rewrite-map",
        }.get(update_reason, "first-parent-root")
        fields.extend([
            ("Evidence-Type", evidence_type),
            ("Evidence", "Git evidence validates the declared fork."),
            ("Confidence", "high"),
            ("Review-Status", review_status),
        ])
        if review_status == "approved":
            fields.extend([
                ("Reviewed-By", "Randy True"),
                ("Reviewed-At", REVIEWED_AT),
            ])
    fields.append(("Lineage-Version", "2"))
    return fields
def subject(branch_name, lineage_type="recorded-late"):
    if lineage_type == "branch-start":
        return "chore(repo): record branch lineage at branch start for " + branch_name
    return "chore(repo): record branch lineage late for " + branch_name
def codes(result):
    return {item["code"] for item in result["errors"]}

### Strict message parsing
def test_parse_v2_branch_start_message():
    fields = v2_fields(
        "feature/example",
        "main",
        "a" * 40,
        lineage_type="branch-start",
        relationship="created-from",
        update_reason="initial",
    )
    parsed = parse_lineage_message(commit_message(subject("feature/example", "branch-start"), fields))
    assert parsed["errors"] == []
    assert parsed["version"] == "2"
def test_parse_rejects_subject_body_disagreement_duplicates_unknowns_and_order():
    fields = v2_fields("feature/body", "main", "a" * 40)
    fields.insert(3, ("Record-ID", new_id()))
    fields.insert(-1, ("Mystery", "value"))
    fields[4], fields[5] = fields[5], fields[4]
    parsed = parse_lineage_message(commit_message(subject("feature/subject"), fields))
    assert {
        "field-duplicate",
        "field-unknown",
        "field-order-invalid",
        "subject-branch-mismatch",
    }.issubset({item["code"] for item in parsed["errors"]})
def test_parse_marks_unknown_version_and_invalid_enums():
    fields = v2_fields("feature/example", "main", "a" * 40)
    fields[1] = ("Lineage-Type", "eventually")
    fields[4] = ("Relationship", "guessed-from")
    fields[5] = ("Update-Reason", "magic")
    fields[-1] = ("Lineage-Version", "3")
    parsed = parse_lineage_message(commit_message(subject("feature/example"), fields))
    assert {
        "version-unsupported",
        "lineage-type-invalid",
        "relationship-invalid",
        "update-reason-invalid",
    }.issubset({item["code"] for item in parsed["errors"]})
def test_parse_rewrite_map_enforces_header_hashes_uniqueness_and_order():
    good = (
        "kind\told-sha\tnew-sha\n"
        "fork\t" + "1" * 40 + "\t" + "2" * 40 + "\n"
        "record\t" + "3" * 40 + "\t" + "4" * 40 + "\n"
    )
    mappings, problems = parse_rewrite_map(good)
    assert problems == []
    assert mappings[("fork", "1" * 40)] == "2" * 40
    bad = (
        "kind\told-sha\tnew-sha\n"
        "record\t" + "3" * 40 + "\t" + "4" * 40 + "\n"
        "fork\t" + "1" * 40 + "\t" + "2" * 40 + "\n"
        "fork\t" + "1" * 40 + "\tbad\n"
    )
    _, problems = parse_rewrite_map(bad)
    assert {"rewrite-map-order", "rewrite-map-duplicate", "rewrite-map-sha"}.issubset(
        {item["code"] for item in problems}
    )

### Git-backed validation
def test_v1_branch_start_is_structurally_verified(tmp_path):
    repo, fork = init_repo(tmp_path)
    branch(repo, "feature/start")
    message = commit_message(
        subject("feature/start", "branch-start"),
        v1_start_fields("feature/start", "main", fork),
    )
    record_commit = commit_empty(repo, message)
    result = collect_branch_lineage(repo, branch_row("feature/start"))
    assert result["status"] == "structurally-verified"
    assert result["authoritative"] is True
    assert result["record"]["commit"] == record_commit
    assert result["record"]["relationship"] == "created-from"
    assert result["fork_date"] == git(repo, "show", "-s", "--format=%cI", fork)
def test_v1_recorded_late_is_evidence_validated(tmp_path):
    repo, fork = init_repo(tmp_path)
    expected_fork_date = git(repo, "show", "-s", "--format=%cI", fork)
    branch(repo, "feature/late")
    commit_empty(repo, "feat: child work\n")
    fields = v1_late_fields("feature/late", "main", fork)
    commit_empty(repo, commit_message(subject("feature/late"), fields))
    result = collect_branch_lineage(repo, branch_row("feature/late"))
    assert result["status"] == "evidence-validated"
    assert result["record"]["update_reason"] == "late-migration"
    assert result["fork_date"] == expected_fork_date
    assert result["record"]["date"] == git(
        repo, "show", "-s", "--format=%cI", result["record"]["commit"]
    )
def test_v2_branch_start_is_structurally_verified(tmp_path):
    repo, fork = init_repo(tmp_path)
    branch(repo, "feature/v2-start")
    fields = v2_fields(
        "feature/v2-start",
        "main",
        fork,
        lineage_type="branch-start",
        relationship="created-from",
        update_reason="initial",
    )
    commit_empty(repo, commit_message(subject("feature/v2-start", "branch-start"), fields))
    result = collect_branch_lineage(repo, branch_row("feature/v2-start"))
    assert result["status"] == "structurally-verified"
    assert result["record"]["lineage_id"]
    assert result["record"]["record_id"]
def test_newest_invalid_record_blocks_valid_fallback(tmp_path):
    repo, fork = init_repo(tmp_path)
    branch(repo, "feature/newest")
    commit_empty(repo, "feat: child work\n")
    commit_empty(
        repo,
        commit_message(
            subject("feature/newest"),
            v1_late_fields("feature/newest", "main", fork),
        ),
    )
    bad_fields = v2_fields(
        "feature/newest",
        "main",
        fork,
        update_reason="correction",
        extras=[("Supersedes-Record-Commit", "f" * 40)],
    )
    bad_fields[9] = ("Fork-Commit", "bad")
    newest = commit_empty(repo, commit_message(subject("feature/newest"), bad_fields))
    result = collect_branch_lineage(repo, branch_row("feature/newest"))
    assert result["record"]["commit"] == newest
    assert result["status"] == "invalid"
    assert "fork-sha-invalid" in codes(result)
def test_pending_record_is_visible_but_not_authoritative(tmp_path):
    repo, fork = init_repo(tmp_path)
    branch(repo, "feature/pending")
    commit_empty(repo, "feat: child work\n")
    fields = v2_fields(
        "feature/pending",
        "main",
        fork,
        review_status="pending",
    )
    commit_empty(repo, commit_message(subject("feature/pending"), fields))
    result = collect_branch_lineage(repo, branch_row("feature/pending"))
    assert result["status"] == "pending"
    assert result["authoritative"] is False
    assert result["parent_branch"] == "main"
    assert result["fork_date"] is None
def test_main_is_an_undated_root(tmp_path):
    repo, _ = init_repo(tmp_path)
    result = collect_branch_lineage(repo, branch_row("main"))
    assert result["status"] == "root"
    assert result["authoritative"] is True
    assert result["fork_date"] is None
def test_stacked_child_ignores_inherited_parent_record(tmp_path):
    repo, fork = init_repo(tmp_path)
    branch(repo, "feature/parent")
    fields = v2_fields(
        "feature/parent",
        "main",
        fork,
        lineage_type="branch-start",
        relationship="created-from",
        update_reason="initial",
    )
    commit_empty(repo, commit_message(subject("feature/parent", "branch-start"), fields))
    branch(repo, "feature/child")
    commit_empty(repo, "feat: child work\n")
    result = collect_branch_lineage(repo, branch_row("feature/child"))
    assert result["status"] == "missing"
    assert result["record"] is None
def test_v2_correction_can_supersede_v1_and_establish_ids(tmp_path):
    repo, fork = init_repo(tmp_path)
    branch(repo, "feature/correction")
    commit_empty(repo, "feat: child work\n")
    v1_commit = commit_empty(
        repo,
        commit_message(
            subject("feature/correction"),
            v1_late_fields("feature/correction", "main", fork),
        ),
    )
    fields = v2_fields(
        "feature/correction",
        "main",
        fork,
        update_reason="correction",
        extras=[("Supersedes-Record-Commit", v1_commit)],
    )
    commit_empty(repo, commit_message(subject("feature/correction"), fields))
    result = collect_branch_lineage(repo, branch_row("feature/correction"))
    assert result["status"] == "evidence-validated"
    assert result["record"]["supersedes_record_commit"] == v1_commit
    assert len(result["history"]) == 2
def test_bad_supersession_link_is_invalid_without_fallback(tmp_path):
    repo, fork = init_repo(tmp_path)
    branch(repo, "feature/bad-link")
    commit_empty(repo, "feat: child work\n")
    commit_empty(
        repo,
        commit_message(
            subject("feature/bad-link"),
            v1_late_fields("feature/bad-link", "main", fork),
        ),
    )
    fields = v2_fields(
        "feature/bad-link",
        "main",
        fork,
        update_reason="correction",
        extras=[("Supersedes-Record-Commit", "e" * 40)],
    )
    commit_empty(repo, commit_message(subject("feature/bad-link"), fields))
    result = collect_branch_lineage(repo, branch_row("feature/bad-link"))
    assert result["status"] == "invalid"
    assert "supersedes-commit-mismatch" in codes(result)
def test_selected_record_rejects_duplicate_id_and_supersession_cycle(tmp_path):
    repo, fork = init_repo(tmp_path)
    branch(repo, "feature/cycle")
    commit_empty(repo, "feat: child work\n")
    lineage_id = new_id()
    record_id = new_id()
    first_fields = v2_fields(
        "feature/cycle",
        "main",
        fork,
        lineage_id=lineage_id,
        record_id=record_id,
        update_reason="correction",
        extras=[("Supersedes-Record-ID", record_id)],
    )
    commit_empty(repo, commit_message(subject("feature/cycle"), first_fields))
    second_fields = v2_fields(
        "feature/cycle",
        "main",
        fork,
        lineage_id=lineage_id,
        record_id=record_id,
        update_reason="correction",
        extras=[("Supersedes-Record-ID", record_id)],
    )
    commit_empty(repo, commit_message(subject("feature/cycle"), second_fields))
    result = collect_branch_lineage(repo, branch_row("feature/cycle"))
    assert result["status"] == "invalid"
    assert {"record-id-duplicate-history", "supersession-cycle"}.issubset(codes(result))
def test_explicit_merge_reroot_validates_evidence_commit(tmp_path):
    repo, fork = init_repo(tmp_path)
    branch(repo, "feature/parent")
    parent_tip = commit_empty(repo, "feat: parent\n")
    git(repo, "switch", "main")
    branch(repo, "feature/reroot")
    commit_empty(repo, "feat: original child\n")
    git(repo, "merge", "--no-ff", "-m", "reroot merge", "feature/parent")
    evidence_commit = git(repo, "rev-parse", "HEAD")
    assert git(repo, "rev-parse", evidence_commit + "^2") == parent_tip
    v1_fields = v1_late_fields(
        "feature/reroot",
        "feature/parent",
        parent_tip,
        evidence_type="explicit-reroot-merge",
    )
    v1_fields[6] = ("Fork-Subject", "feat: parent")
    v1_fields[9] = (
        "Evidence",
        "Merge " + evidence_commit + " proves the explicit reroot.",
    )
    v1_commit = commit_empty(repo, commit_message(subject("feature/reroot"), v1_fields))
    result = collect_branch_lineage(repo, branch_row("feature/reroot"))
    assert result["status"] == "evidence-validated"
    assert result["record"]["relationship"] == "rerooted-to"
    assert result["record"]["evidence_commit"] == evidence_commit
    v2_fields_for_reroot = v2_fields(
        "feature/reroot",
        "feature/parent",
        parent_tip,
        relationship="rerooted-to",
        update_reason="reroot",
        extras=[
            ("Supersedes-Record-Commit", v1_commit),
            ("Evidence-Commit", evidence_commit),
        ],
    )
    v2_fields_for_reroot[10] = ("Fork-Subject", "feat: parent")
    commit_empty(repo, commit_message(subject("feature/reroot"), v2_fields_for_reroot))
    result = collect_branch_lineage(repo, branch_row("feature/reroot"))
    assert result["status"] == "evidence-validated"
    assert result["record"]["version"] == "2"
    assert result["record"]["update_reason"] == "reroot"
def test_nonempty_and_merge_lineage_commits_are_invalid(tmp_path):
    repo, fork = init_repo(tmp_path)
    branch(repo, "feature/nonempty")
    fields = v1_start_fields("feature/nonempty", "main", fork)
    message = commit_message(subject("feature/nonempty", "branch-start"), fields)
    (repo / "changed.txt").write_text("changed\n", encoding="utf-8")
    git(repo, "add", "changed.txt")
    git(repo, "commit", "-F", "-", input_text=message)
    result = collect_branch_lineage(repo, branch_row("feature/nonempty"))
    assert result["status"] == "invalid"
    assert "record-not-empty" in codes(result)
    git(repo, "switch", "main")
    branch(repo, "feature/other")
    commit_empty(repo, "feat: other\n")
    git(repo, "switch", "feature/nonempty")
    git(repo, "merge", "--no-ff", "-m", "merge other", "feature/other")
    merge_fields = v1_late_fields("feature/nonempty", "main", fork)
    merge_message = commit_message(subject("feature/nonempty"), merge_fields)
    git(repo, "commit", "--allow-empty", "--amend", "-F", "-", input_text=merge_message)
    result = collect_branch_lineage(repo, branch_row("feature/nonempty"))
    assert result["status"] == "invalid"
    assert "record-parent-count" in codes(result)
def test_malformed_missing_fork_is_visible_without_crashing(tmp_path):
    repo, _ = init_repo(tmp_path)
    branch(repo, "feature/malformed")
    fields = v1_start_fields("feature/malformed", "main", "a" * 40)
    fields.pop(5)
    commit_empty(repo, commit_message(subject("feature/malformed", "branch-start"), fields))
    result = collect_branch_lineage(repo, branch_row("feature/malformed"))
    assert result["status"] == "invalid"
    assert {"field-order-invalid", "fork-sha-invalid"}.issubset(codes(result))
def test_missing_and_diverged_refs_are_explicit_states(tmp_path):
    repo, fork = init_repo(tmp_path)
    branch(repo, "feature/missing-parent")
    commit_empty(repo, "feat: child work\n")
    fields = v1_late_fields("feature/missing-parent", "feature/gone", fork)
    commit_empty(repo, commit_message(subject("feature/missing-parent"), fields))
    missing = collect_branch_lineage(repo, branch_row("feature/missing-parent"))
    assert missing["status"] == "parent-ref-missing"
    diverged = collect_branch_lineage(
        repo,
        {
            "name": "feature/missing-parent",
            "local_tip": git(repo, "rev-parse", "HEAD"),
            "remote_tip": "f" * 40,
        },
    )
    assert diverged["status"] == "ref-diverged"
def test_global_validation_marks_cycles_and_duplicate_ids():
    shared_id = new_id()
    results = {
        "feature/a": {
            "status": "evidence-validated",
            "authoritative": True,
            "parent_branch": "feature/b",
            "fork_date": "2026-07-30T00:00:00-07:00",
            "record": {"record_id": shared_id, "lineage_id": new_id()},
            "errors": [],
        },
        "feature/b": {
            "status": "evidence-validated",
            "authoritative": True,
            "parent_branch": "feature/a",
            "fork_date": "2026-07-30T00:00:00-07:00",
            "record": {"record_id": shared_id, "lineage_id": new_id()},
            "errors": [],
        },
    }
    apply_global_validation(results)
    for result in results.values():
        assert result["status"] == "invalid"
        assert result["fork_date"] is None
        assert {"parent-cycle", "record-id-duplicate"}.issubset(codes(result))
@pytest.mark.parametrize("reason", ["rebase", "history-rewrite"])
def test_rewrite_map_validates_stable_record_id(tmp_path, reason):
    repo, fork = init_repo(tmp_path)
    branch(repo, "feature/rewrite")
    commit_empty(repo, "feat: child work\n")
    lineage_id = new_id()
    predecessor_id = new_id()
    predecessor_fields = v2_fields(
        "feature/rewrite",
        "main",
        fork,
        lineage_id=lineage_id,
        record_id=predecessor_id,
    )
    predecessor = commit_empty(
        repo,
        commit_message(subject("feature/rewrite"), predecessor_fields),
    )
    old_record = "1" * 40
    old_fork = "2" * 40
    map_text = (
        "kind\told-sha\tnew-sha\n"
        "fork\t" + old_fork + "\t" + fork + "\n"
        "record\t" + old_record + "\t" + predecessor + "\n"
    )
    commit_file(repo, "rewrite-map.tsv", map_text, "docs: add rewrite map")
    blob = git(repo, "rev-parse", "HEAD:rewrite-map.tsv")
    extras = [
        ("Supersedes-Record-ID", predecessor_id),
        ("Previous-Record-Commit", old_record),
        ("Previous-Fork-Commit", old_fork),
        ("Evidence-Artifact", "rewrite-map.tsv"),
        ("Evidence-Artifact-Blob", blob),
    ]
    fields = v2_fields(
        "feature/rewrite",
        "main",
        fork,
        lineage_id=lineage_id,
        update_reason=reason,
        extras=extras,
    )
    commit_empty(repo, commit_message(subject("feature/rewrite"), fields))
    result = collect_branch_lineage(repo, branch_row("feature/rewrite"))
    assert result["status"] == "evidence-validated"
    assert result["record"]["supersedes_record_id"] == predecessor_id
