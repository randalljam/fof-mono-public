# Delta: iteration-3-cycle-tracker

## ADDED Requirements

### Requirement: Dev-Cycle Tracker
The system SHALL track a manually set dev-cycle state per worktree branch (submission harness, submission time, AI-responded flag) and render it on worktree cards and as an overview rollup.
#### Scenario: Submission is recorded
- **WHEN** the user picks Cursor, Claude CLI, Claude app, Codex CLI, or Codex app in a card's Submitted-via pulldown
- **THEN** the client persists submitted_via with a current submitted_at timestamp and ai_responded false, and the card shows "waiting for AI response" with compact elapsed time and an AI-responded checkbox.
#### Scenario: Response is confirmed
- **WHEN** the user checks AI responded
- **THEN** the state persists and the line shows AI responded with elapsed time.
#### Scenario: Overview rollup
- **WHEN** worktrees have submitted_at set
- **THEN** the overview Status panel lists them newest-first with worktree-colored name chips, harness pill, and waiting/responded state; active worktrees without cycle state appear as dim hints.
#### Scenario: Invalid harness value
- **WHEN** a client sends a submitted_via value outside the allowed set
- **THEN** the server rejects it with a validation error.

### Requirement: Branch Parent Information
The system SHALL report each branch's parent (ledger-recorded or assumed main) with a fork-base commit.
#### Scenario: Ledger parent exists
- **WHEN** the branch-map ledger records a parent for a branch
- **THEN** the branch entry reports that parent with source "ledger" and the recorded or computed fork base.
#### Scenario: No ledger entry
- **WHEN** a branch has no ledger entry
- **THEN** the branch entry reports parent "main" with source "assumed" and the merge-base fork point, and main itself has no parent.

### Requirement: Branch Commits API
The system SHALL serve paged full commit messages for branches present in the snapshot.
#### Scenario: Commits are paged
- **WHEN** a client requests `GET /api/branch-commits` for a known branch with skip and limit
- **THEN** the system resolves the local or origin ref and returns commits with sha, author, date, subject, and full body, plus a has-more flag.
#### Scenario: Unknown branch
- **WHEN** the requested branch is not in the snapshot's branches layer
- **THEN** the system returns not-found without invoking git on the input.

### Requirement: Branches Section
The dashboard SHALL render branches as their own numbered section with parent and tip-commit columns, worktree-colored branch names, and a commits drawer.
#### Scenario: Branch is inspected
- **WHEN** the user clicks a branch name in the table
- **THEN** a right-side drawer lists the last 20 full commit messages with timestamps and a Load more button while more exist.
#### Scenario: Worktree card links to branch
- **WHEN** the user clicks the branch name inside a worktree card
- **THEN** the page scrolls to that branch's row in the Branches section and highlights it briefly.

## MODIFIED Requirements

### Requirement: Dashboard Overview
The overview panels are Status (dev-cycle rollup, half width) and Latest activity (half width); the needs-attention and next-steps panels are removed from the overview while the next-steps API and stored data remain.

### Requirement: Interactive Worktree Cards
Card expansion toggles only from the title bar or chevron; the editable next-step/just-done/review fields are replaced by the dev-cycle tracker; cards list the last three matching sessions with hover tooltips showing the session's last user message and click-through to the session drawer; the in-card branch name links to the Branches section.

### Requirement: Dashboard Entity Views
Sections are numbered 00 Overview, 01 Worktrees, 02 Branches, 03 Apps, 04 Core, 05 Skills, 06 Specs, 07 AI Sessions, 08 Deploy; each section's descriptive lede renders as a heading tooltip instead of body text.
