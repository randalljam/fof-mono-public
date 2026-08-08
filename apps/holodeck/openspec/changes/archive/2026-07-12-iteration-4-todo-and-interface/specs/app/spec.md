# Delta: iteration-4-todo-and-interface

## ADDED Requirements

### Requirement: Global To-Do List
The system SHALL provide a manual to-do queue on the overview with persistent ordering and a dated markdown archive.
#### Scenario: Items are managed
- **WHEN** the user adds, checks, or drag-reorders to-do items
- **THEN** the changes persist through the next-steps and next-steps-order APIs and the list renders in stored order.
#### Scenario: Item is archived
- **WHEN** the user archives an item
- **THEN** it is removed from state and appended to `apps/holodeck/data/todo-archive.md` under a `## YYYY-MM-DD` heading with added/archived times, and it no longer renders.

### Requirement: Worktree Next-Step Checklist
The system SHALL store a per-worktree checklist of next steps and render it on the card with a free-text entry that converts each entry into a checkbox item.
#### Scenario: Step is added
- **WHEN** the user types in the card's next-step input and presses Enter
- **THEN** the text becomes the newest checkbox item, the input clears for another entry, and the validated list persists via the worktree state API.

## MODIFIED Requirements

### Requirement: Dev-Cycle Tracker
Renamed concern: the pulldown is "Primary AI interface" (`primary_interface`, same harness enum) meaning the main harness currently used in that worktree; legacy `submitted_via` values migrate on state normalization; the waiting-for-AI-response line and AI-responded checkbox are removed. The overview Status panel lists active worktrees ordered by latest session recency with worktree-colored name chip, interface pill, first unchecked next step, and latest session relative time.

### Requirement: Interactive Worktree Cards
The ACTIVE/INACTIVE badge is itself the toggle; inactive state (not Cursor-open state) drives card dimming; toggling inactive stamps `deactivated_at` and the card moves immediately to the top of the inactive group, which sorts by deactivated_at descending after all active cards.

### Requirement: Session Detail API
Message text is served untruncated (the 200-message cap remains).

### Requirement: Dashboard Local Interactions
The session drawer header includes a jump-to-end button below the close button that scrolls to the final message.
