# AutoLearner Specification

## Purpose
AutoLearner is a local Flask web app that helps a student practice the PreCalc Test 1 study guide through an interactive study guide and a mastery-based AI practice loop. The app presents one concept exercise at a time, collects a think-aloud recording and optional photo of written work, assesses the attempt with transcript, pacing, and work evidence, and repeats only unmastered concepts until all concepts meet the mastery threshold.

This single `app` capability is the early-phase baseline for the whole application. Split it into narrower capabilities later only when this file becomes too large or different behavior areas need independent change control.

## Workflows
### Workflow: Student studies the guide
Open `/guide` -> browse the interactive study guide -> tick mastery checkboxes (state stays in the browser).
Exercises requirements: Interactive Study Guide.

### Workflow: Student practices a concept
Get next scheduled item -> read the exercise -> record think-aloud (optional photo of written work) -> submit -> receive assessment with mastery score and pacing feedback -> continue to next item.
Exercises requirements: Practice Session State, Mastery Scheduling, Exercise Selection, Attempt Submission, Think-Aloud Assessment, Pacing Analysis, Service Mode Visibility.

### Workflow: Student repeats unmastered concepts
Finish a round -> next round schedules only concepts below the mastery threshold -> targeted exercises are generated from the student's latest gaps -> practice completes when every concept is mastered.
Exercises requirements: Mastery Scheduling, Targeted Repeat Exercises, Exercise Selection.

### Workflow: Student asks to be taught
Request "teach me" for a concept -> receive a lesson with key points and optional audio narration.
Exercises requirements: Teach-Me Lesson.

### Workflow: Student reviews a past attempt
Request review for a concept with a recorded attempt -> see the exercise, assessment, and links to the audio recording and work photo.
Exercises requirements: Attempt Review Media.

### Workflow: Student resets practice
Request a reset -> a fresh session replaces the old one with a new summary, next item, and service modes.
Exercises requirements: Practice Session State, Service Mode Visibility.

## Requirements
### Requirement: Interactive Study Guide
The system SHALL serve an interactive study guide for the PreCalc Test 1 material.

#### Scenario: Student opens the study guide
- **WHEN** a student opens `/guide`
- **THEN** the system displays the study guide page.

#### Scenario: Study guide remains browser-local
- **WHEN** a student uses study guide UI features such as mastery checkboxes
- **THEN** the system stores that study-guide interaction state in the browser rather than requiring backend persistence.

### Requirement: Practice Session State
The system SHALL maintain a practice session with a unique session id, unit name, current round, per-concept state, and attempt log.

#### Scenario: First state request creates a session
- **WHEN** the API receives a state request and no prior session exists in the data directory
- **THEN** the system creates and persists a new session before returning the summary and next item.

#### Scenario: Student resets the practice session
- **WHEN** the API receives a reset request
- **THEN** the system creates a fresh session and returns the new summary, next item, and service modes.

### Requirement: Mastery Scheduling
The system SHALL schedule practice by concept mastery, using the configured mastery threshold.

#### Scenario: Round one covers every concept
- **WHEN** a new session begins
- **THEN** the system schedules each concept from the concept catalog once in round one.

#### Scenario: Later rounds target unmastered concepts
- **WHEN** round one is complete and one or more concepts have latest mastery scores below the threshold
- **THEN** the system advances to the next round and schedules only concepts that are not yet mastered.

#### Scenario: Practice completes when every concept is mastered
- **WHEN** every concept has a latest mastery score greater than or equal to the threshold
- **THEN** the next scheduled item reports that practice is done.

### Requirement: Exercise Selection
The system SHALL choose exercises from seed and generated exercises while avoiding immediate reuse when possible.

#### Scenario: Unused seed exercise exists
- **WHEN** a concept has unused seed exercises and no unused generated exercise
- **THEN** the system selects an unused seed exercise for that concept.

#### Scenario: Generated targeted exercise exists
- **WHEN** a repeat-round concept has an unused generated targeted exercise
- **THEN** the system prefers that generated exercise over seed exercises.

#### Scenario: Exercises are exhausted
- **WHEN** all seed and generated exercises for a concept have been used
- **THEN** the system recycles an available exercise rather than blocking practice.

### Requirement: Attempt Submission
The system SHALL require a valid concept, valid exercise, and think-aloud audio recording before assessing an attempt.

#### Scenario: Unknown concept is submitted
- **WHEN** the API receives an attempt for a concept id not present in the concept catalog
- **THEN** the system rejects the request with a validation error.

#### Scenario: Unknown exercise is submitted
- **WHEN** the API receives an attempt for an exercise id not associated with the selected concept or generated exercises
- **THEN** the system rejects the request with a validation error.

#### Scenario: Audio is missing
- **WHEN** the API receives an attempt without an audio recording
- **THEN** the system rejects the request and tells the student to record the think-aloud first.

#### Scenario: Valid attempt is submitted
- **WHEN** the API receives a valid concept id, valid exercise id, think-aloud audio, and optional photo
- **THEN** the system stores the uploaded media, assesses the attempt, records the attempt in session state, persists the session, and returns the assessment, updated summary, next item, service modes, and media review links.

### Requirement: Think-Aloud Assessment
The system SHALL assess each submitted attempt using the student's transcript, pacing data, selected exercise, concept context, optional work photo, and prior gaps.

#### Scenario: Live transcription is configured
- **WHEN** a real Deepgram API key is available
- **THEN** the system transcribes the audio with word-level timestamps and marks transcription mode as `deepgram`.

#### Scenario: Live transcription is unavailable
- **WHEN** no real Deepgram API key is available or transcription fails
- **THEN** the system uses a clearly labeled mock transcript so local practice remains end-to-end runnable.

#### Scenario: LLM assessment succeeds
- **WHEN** an Anthropic or OpenAI assessment call returns structured assessment data
- **THEN** the system records correctness, correctness notes, mastery score, reasoning quality, pacing assessment, confusion flags, gaps, strengths, overall assessment, recommendation, pacing metrics, transcript, and mode.

#### Scenario: LLM assessment is unavailable
- **WHEN** no configured assessment provider can return structured assessment data
- **THEN** the system returns a clearly labeled mock assessment rather than failing the practice loop.

### Requirement: Pacing Analysis
The system SHALL compute pacing evidence from word-level transcript timing.

#### Scenario: Word timestamps are available
- **WHEN** a transcript includes word start and end times
- **THEN** the system computes pacing metrics including word count, pause count, longest pause, time to first word, filler count, and timeline evidence.

#### Scenario: Transcript timing is missing or malformed
- **WHEN** transcript timing data is absent or malformed
- **THEN** the system returns empty or zero pacing metrics without crashing the assessment flow.

### Requirement: Targeted Repeat Exercises
The system SHALL generate targeted exercises for repeat-round concepts based on the student's latest gaps when no unused generated exercise is available.

#### Scenario: Repeat round needs a targeted exercise
- **WHEN** a concept is scheduled after round one and has no unused generated exercise
- **THEN** the system asks the pipeline to generate targeted exercises from the concept and prior gaps, stores them in the session, and schedules the generated exercise.

#### Scenario: Targeted generation is unavailable
- **WHEN** live generation cannot produce targeted exercises
- **THEN** the system provides clearly labeled mock generated exercises so the repeat-round flow remains testable.

### Requirement: Teach-Me Lesson
The system SHALL provide a "teach me" lesson for a selected concept using current gaps, optional confusion text, and optional exercise context.

#### Scenario: Student requests a lesson for a valid concept
- **WHEN** the API receives a teach-me request with a valid concept id
- **THEN** the system returns a lesson with title, lesson HTML, key points, audio script, mode, and optional audio URL.

#### Scenario: Student requests a lesson for an unknown concept
- **WHEN** the API receives a teach-me request with an unknown concept id
- **THEN** the system rejects the request with a validation error.

#### Scenario: TTS is unavailable
- **WHEN** lesson text-to-speech cannot be generated
- **THEN** the system still returns the lesson content with a null audio URL.

### Requirement: Attempt Review Media
The system SHALL provide review data and media URLs for prior attempts in the active session.

#### Scenario: Prior attempt exists
- **WHEN** the API receives an attempt review request for a concept with a recorded attempt
- **THEN** the system returns the concept, exercise, attempt, assessment, audio URL, and image URL when available.

#### Scenario: Prior attempt does not exist
- **WHEN** the API receives an attempt review request for a concept with no matching recorded attempt
- **THEN** the system returns a not-found error.

#### Scenario: Upload is outside the active session
- **WHEN** the API receives an upload request for a session id other than the active session
- **THEN** the system returns a not-found error.

### Requirement: Service Mode Visibility
The system SHALL report whether transcription, assessment, and text-to-speech are using live providers or mock fallbacks.

#### Scenario: State is requested
- **WHEN** the API returns current state
- **THEN** the response includes service modes for transcription, assessment, and text-to-speech.

#### Scenario: Submit completes
- **WHEN** an attempt submission completes
- **THEN** the response includes the transcription and assessment modes used for that attempt.
