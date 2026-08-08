"""Correlate exchanges with git commits."""

import os
from datetime import datetime, timedelta

try:
    from apps.holodeck.turns import db
except ImportError:
    from turns import db

### Time and matching
def parse_time(value):
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None
def same_path(left, right):
    if not left or not right:
        return False
    return os.path.normpath(str(left)) == os.path.normpath(str(right))
def session_commit_compatible(session, commit):
    session_branch = session.get("branch")
    commit_branch = commit.get("branch")
    if session_branch and commit_branch:
        return session_branch == commit_branch
    return same_path(session.get("worktree"), commit.get("worktree"))
def session_last_time(session):
    return parse_time(session.get("last_activity")) or parse_time(session.get("started"))
def candidate_distance(commit_time, exchange):
    response_end = parse_time(exchange.get("response_end_ts"))
    user_time = parse_time(exchange.get("user_ts"))
    anchor = response_end or user_time
    if not anchor:
        return 999999999
    return abs((commit_time - anchor).total_seconds())

### Candidate selection
def exchange_window_end(session, exchanges, index):
    if index + 1 < len(exchanges):
        next_user = parse_time(exchanges[index + 1].get("user_ts"))
        if next_user:
            return next_user
    last_activity = session_last_time(session)
    if last_activity:
        return last_activity + timedelta(minutes=10)
    return None
def agent_window_candidate(session, exchanges, index, commit_time):
    exchange = exchanges[index]
    user_time = parse_time(exchange.get("user_ts"))
    window_end = exchange_window_end(session, exchanges, index)
    if user_time and window_end and user_time <= commit_time <= window_end:
        return {"exchange": exchange, "method": "agent-window", "confidence": 0.9}
    return None
def after_response_candidate(exchanges, index, commit_time):
    exchange = exchanges[index]
    response_end = parse_time(exchange.get("response_end_ts"))
    if not response_end:
        return None
    window_end = response_end + timedelta(minutes=45)
    if index + 1 < len(exchanges):
        next_user = parse_time(exchanges[index + 1].get("user_ts"))
        if next_user and next_user < window_end:
            window_end = next_user
    if response_end <= commit_time <= window_end:
        return {"exchange": exchange, "method": "after-response", "confidence": 0.6}
    return None
def candidates_for_session(session, exchanges, commit, commit_time):
    if not session_commit_compatible(session, commit):
        return []
    candidates = []
    for index, exchange in enumerate(exchanges):
        user_time = parse_time(exchange.get("user_ts"))
        if user_time and user_time > commit_time:
            continue
        agent = agent_window_candidate(session, exchanges, index, commit_time)
        if agent:
            candidates.append(agent)
            continue
        after = after_response_candidate(exchanges, index, commit_time)
        if after:
            candidates.append(after)
    if not candidates:
        return []
    candidates.sort(key=lambda item: parse_time(item["exchange"].get("user_ts")) or datetime.min.replace(tzinfo=commit_time.tzinfo), reverse=True)
    return [candidates[0]]
def choose_candidate(sessions_by_id, exchanges_by_session, commit):
    commit_time = parse_time(commit.get("committer_date"))
    if not commit_time:
        return None
    candidates = []
    for session_id, session in sessions_by_id.items():
        session_candidates = candidates_for_session(session, exchanges_by_session.get(session_id) or [], commit, commit_time)
        for candidate in session_candidates:
            candidate["distance"] = candidate_distance(commit_time, candidate["exchange"])
            candidates.append(candidate)
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item["distance"], -(parse_time(item["exchange"].get("user_ts")) or commit_time).timestamp()))
    return candidates[0]

### DB rebuild
def load_sessions(conn):
    return {row["id"]: dict(row) for row in conn.execute("SELECT * FROM sessions").fetchall()}
def load_exchanges_by_session(conn):
    grouped = {}
    rows = conn.execute("SELECT * FROM exchanges ORDER BY session_id, user_ts, idx").fetchall()
    for row in rows:
        grouped.setdefault(row["session_id"], []).append(dict(row))
    return grouped
def load_commits(conn):
    return [dict(row) for row in conn.execute("SELECT * FROM commits ORDER BY committer_date").fetchall()]
def rebuild_links(conn):
    sessions_by_id = load_sessions(conn)
    exchanges_by_session = load_exchanges_by_session(conn)
    commits = load_commits(conn)
    conn.execute("DELETE FROM links")
    count = 0
    for commit in commits:
        candidate = choose_candidate(sessions_by_id, exchanges_by_session, commit)
        if not candidate:
            continue
        db.upsert_link(conn, {
            "exchange_id": candidate["exchange"]["id"],
            "sha": commit["sha"],
            "method": candidate["method"],
            "confidence": candidate["confidence"],
        })
        count += 1
    return count
