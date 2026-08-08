## ADDED Requirements
### Requirement: Kid Landing and Setup
The system SHALL provide a kid-facing anchor landing page and an operator setup path for choosing a learner and practice mode.

#### Scenario: Default landing opens
- **WHEN** a user opens `anchor.html` without `?setup=1`
- **THEN** the system shows the kid landing with quick-pick learner buttons and keeps the full setup hidden.

#### Scenario: Operator setup opens
- **WHEN** a user opens `anchor.html?setup=1` or selects the Other setup path
- **THEN** the system shows the full setup controls, learner picker, source-folder controls, and problem-list editor.

#### Scenario: Known learner is picked
- **WHEN** the user picks a known learner from the kid landing
- **THEN** the system loads that learner's current file information and presents available practice choices including targeted practice, problem lists, Fluency feast, and quick quizzes.

### Requirement: Learner File Lifecycle
The system SHALL use per-learner SQLite files as the active local store for the anchor flow when the math-quiz dev server is available.

#### Scenario: Continue latest loads an existing learner
- **WHEN** the anchor page requests `/api/latest-user-db` for a learner with a source file
- **THEN** the system returns the latest matching SQLite file bytes with file metadata, problem lists, targeted config, Fluency feast preset, profile, and quick-practice sets.

#### Scenario: Continue latest has no source file
- **WHEN** the user tries to continue a learner who has no source file
- **THEN** the system blocks starting that Continue run and reports that a new file must be started first.

#### Scenario: Run is saved
- **WHEN** a finished or quit-and-save anchor run posts to `/api/save-run`
- **THEN** the system writes the single-session archive, accumulates or creates the learner file, updates quick-practice rows for source saves, and reports the saved target file.

### Requirement: Canonical Session Data
The system SHALL record arithmetic attempts in canonical SQLite/session shapes using raw attempts as the source of truth.

#### Scenario: A session is imported
- **WHEN** canonical session JSON is imported into SQLite
- **THEN** the system creates or reuses the user and session rows, skips duplicate session imports, and writes problem attempts with canonical operands, operation, correctness, response time, flags, and presented time.

#### Scenario: Problem text uses display symbols
- **WHEN** stored or imported problem text contains legacy display symbols such as `×`, `÷`, or HTML entities
- **THEN** the system normalizes them to canonical operation symbols for parsing and analysis.

#### Scenario: Targeted metadata is present
- **WHEN** a targeted-practice session includes targeted metadata
- **THEN** the system stores the targeted session, target, and attempt-role records alongside the generic session and attempt rows.

### Requirement: Anchor Quiz Runs
The system SHALL run arithmetic practice on `anchor.html` with keypad entry, optional warm-up, Go-gated timing, feedback, flags, and save/abandon outcomes.

#### Scenario: Auto mode run starts
- **WHEN** the user starts the default auto-problem anchor mode
- **THEN** the system runs warm-up when enabled, waits for the Go gate before timing the first problem, presents the selected operation plan, and auto-submits answers when the entered digit count matches the answer.

#### Scenario: Wrong or skipped answer occurs
- **WHEN** a learner enters a wrong answer or chooses the skip/flag action
- **THEN** the system pauses on the correction flow, shows the correct answer when applicable, allows flagging, and can continue or insert a later re-ask.

#### Scenario: Run is abandoned
- **WHEN** the learner chooses Quit and abandon
- **THEN** the system ends the run without saving the session.

### Requirement: Fluency Computation
The system SHALL compute fluency and fluency percentages from raw attempt history rather than persisted evaluation rows.

#### Scenario: Fact status is evaluated
- **WHEN** attempts exist for a fact
- **THEN** the system evaluates the recent window for accuracy and median correct response time against the current thresholds.

#### Scenario: Full-universe percentage is shown
- **WHEN** the app reports the learner's fluency percentage
- **THEN** the system computes the percent of the configured fact universe that is fluent, excluding flagged attempts when requested.

#### Scenario: Thresholds change
- **WHEN** fluency threshold controls or profile thresholds are changed
- **THEN** the system recomputes fluency from the stored attempts using the new rubric values.

### Requirement: Fluency-Generated Problem Lists
The system SHALL generate Fluency feast and by-fluency problem lists from the learner's current fluency state.

#### Scenario: Fluency feast is requested
- **WHEN** a learner chooses Fluency feast from the kid modal
- **THEN** the system generates a list from the learner's attempts, saved preset or default mix, and current thresholds, then inserts it as the next internal problem list.

#### Scenario: Generated list needs repeats
- **WHEN** the requested list length exceeds the available facts in one or more status pools
- **THEN** the system balances repeats within the repeat cap, backfills from other pools when needed, and avoids adjacent duplicate problems.

### Requirement: Targeted Practice
The system SHALL provide targeted practice for coach-chosen facts with persisted configuration and cumulative fast-correct graduation.

#### Scenario: Targeted practice starts
- **WHEN** the user selects Targeted practice with valid targets
- **THEN** the system works targets serially, mixes the current target with filler according to the configured percentage, and records the run as practice.

#### Scenario: Target progresses
- **WHEN** the learner answers the current target correctly within the configured fast threshold
- **THEN** the system fills one cumulative target ring without removing earned rings for later slow or wrong answers.

#### Scenario: Targeted settings are edited
- **WHEN** targets, filler, params, or reward image paths are changed for an existing learner file
- **THEN** the system saves those settings to the learner's SQLite file through the targeted-config API.

### Requirement: Problem Lists and Quick Quizzes
The system SHALL support stored internal problem lists and auto-generated quick-practice sets from learner SQLite files.

#### Scenario: Internal list is used
- **WHEN** a learner chooses Use internal
- **THEN** the system runs the first stored problem list in queue order and reports it as the consumed list on save.

#### Scenario: Internal lists are edited
- **WHEN** the problem-list editor creates, renames, reorders, edits, or deletes lists
- **THEN** the system persists the change to the learner file through the dev server and preserves contiguous list order.

#### Scenario: Quick quiz is selected
- **WHEN** the kid modal quick-quiz button for an operation is enabled and selected
- **THEN** the system launches that operation's stored seven-problem quick-practice set.

### Requirement: Analysis Dashboard
The system SHALL analyze loaded SQLite data through heatmaps, filters, per-attempt lists, fluency ratings, and editable file-backed settings.

#### Scenario: SQLite file is loaded
- **WHEN** a user loads a per-learner SQLite file or opens analysis with `?folder=&user=`
- **THEN** the system imports that file into the working database, locks to the single learner when applicable, and persists the working database across reloads.

#### Scenario: Heatmap is rendered
- **WHEN** filters, category checkboxes, sequence windows, aggregation mode, or cell metric are changed
- **THEN** the system renders the response-time or fluency heatmap from matching attempts and updates the attempt list.

#### Scenario: Flag or profile edits are saved
- **WHEN** a user edits attempt flags or saves fluency threshold settings for a loaded file
- **THEN** the system updates the working database and posts profile changes to the dev server when a file context is available.

### Requirement: Fluency Tracker Dashboard
The system SHALL provide a fluency tracker page that summarizes per-operation fluency and supports manual status overrides.

#### Scenario: Tracker loads data
- **WHEN** the fluency tracker initializes from local session data, a shared working SQLite database, or a loaded SQLite file
- **THEN** the system computes current, previous, and combined fluency datasets for addition, subtraction, and multiplication.

#### Scenario: Manual status override is saved
- **WHEN** a user edits a fact status and reason in the tracker
- **THEN** the system stores the manual override by user and applies it in the tracker display.

#### Scenario: Problem list is generated from tracker state
- **WHEN** a user generates a problem list from fluency status percentages
- **THEN** the system creates quiz-compatible problem entries and can send them into the legacy quiz flow.

### Requirement: Legacy Quiz Flow
The system SHALL keep the original `math_quiz.html` configurable quiz flow available with browser-local session JSON and downloads.

#### Scenario: Preset or custom quiz runs
- **WHEN** a user starts a preset, custom, uploaded-list, or session-json quiz in `math_quiz.html`
- **THEN** the system presents generated or supplied arithmetic problems, records attempts, and shows feedback for correct, incorrect, overridden, flagged, and "I don't know" answers.

#### Scenario: Session completes or ends early
- **WHEN** the quiz reaches its planned length or the user ends it early
- **THEN** the system summarizes the session, saves browser-local JSON, and offers per-session or all-session downloads.

#### Scenario: Speech and audio options are used
- **WHEN** read-aloud or automatic speech recognition is enabled in the legacy quiz
- **THEN** the system uses browser speech/audio capabilities when available while retaining typed entry.

### Requirement: Dragon Fluency Game
The system SHALL provide a Three.js dragon game that wraps the math-quiz fluency engine and saves quiz bursts through the same dev-server pipeline.

#### Scenario: Game opens without required server
- **WHEN** the dragon game is opened from `file://` or a non-math-quiz server
- **THEN** the system shows a server-required message with the expected dev-server URL.

#### Scenario: Quiz burst completes
- **WHEN** a dragon game burst is completed
- **THEN** the system builds anchor-compatible session JSON, saves it through `/api/save-run`, refreshes fluency from the learner file, and updates high-water progress.

#### Scenario: Milestone is earned
- **WHEN** the learner's high-water fluency crosses a dragon milestone
- **THEN** the system queues the earned reveal, updates the dragon/world state, and stores game progress in browser localStorage for that learner.

### Requirement: Dragon Story and Game Master
The system SHALL provide story progression and a parent Game Master dashboard synchronized through local dev-server JSON endpoints.

#### Scenario: Story progresses after a burst
- **WHEN** a dragon quiz burst ends
- **THEN** the system shows a story sequence with a quiz reaction, the next unseen story beat, and any unread Game Master letters.

#### Scenario: Parent dashboard polls state
- **WHEN** the Game Master page polls `/api/dragon-state`
- **THEN** the system returns the latest saved snapshot including real fluency percent, objective, story progress, recent bursts, and milestone state.

#### Scenario: Parent sends a letter
- **WHEN** the Game Master page posts a message
- **THEN** the system stores it under the learner's local dragon GM data and the game can display it after a later quiz burst.
