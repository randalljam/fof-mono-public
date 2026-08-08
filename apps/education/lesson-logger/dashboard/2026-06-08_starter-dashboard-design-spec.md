file: apps/education/lesson-logger/dashboard/2026-06-08_starter-dashboard-design-spec.md
title: Lesson Logger Dashboard — Starter Design Spec
last-updated: 2026-06-08_1150
ai: Cursor - GPT-5.5
session: `lesson logger dashboard design intake`

This document is a starter design specification for the first private lesson-logger
dashboard. It captures the initial designer/operator intent and turns it into a focused
v1 build target for a coding agent or design agent.

**Spec format used:** lightweight **PRD + UX design spec**.

- The **PRD** portion defines the product goal, scope, user needs, data contract, and acceptance
  criteria.
- The **UX design spec** portion defines the information architecture, first-screen layout,
  interaction model, visual direction, and component requirements.
- This is intentionally not a full design system, Figma handoff, OpenAPI contract, or detailed
  engineering plan. It is a practical starter brief for an AI-built prototype.


## 1. Context
The lesson logger captures homeschool learning sessions from natural-language voice/text input,
primarily through Hermes on Telegram. Confirmed lesson entries are saved as JSON session files and
upserted into a SQLite database.

The dashboard's job is to help Randy and TL review how learning time is being spent. It should
start simple, private, and useful on phones. The dashboard should read from the existing lesson
entry schema and SQLite table. It must not require schema changes for v1.

Related source-of-truth files:

- `apps/education/lesson-logger/references/lesson-schema.md`
- `apps/education/lesson-logger/scripts/lessons_db.py`
- `apps/education/lesson-logger/dashboard/AGENTS.md`


## 2. Product Goal
The first dashboard should answer:

> How much lesson learning time did we do, by subject, over the selected time range?

The v1 emphasis is time, consistency, and coverage. It should not attempt to model mastery,
milestones, sentiment, or learning goals yet.


## 3. Primary Users
- **TL**: parent/designer, primary lesson logger and dashboard reviewer.
- **Randy**: parent/developer/operator, builds and operates the app, also reviews activity.

The interface should assume a family/private use case, not a public analytics product.


## 4. V1 Scope
### In scope
- Student-level dashboard, with the selected student as the primary organizing concept.
- Time spent by subject.
- Weekly view, defaulting to Monday-Sunday.
- Monthly view.
- School-year view, with the school year starting in August.
- Two private users, initially Randy and TL, using simple Basic Auth.
- A small user-preferences foundation so Randy and TL can later have different default
  dashboard views without redesigning the app.
- Total sessions, total minutes/hours, and subjects covered for the selected range.
- Subject bar chart for the selected range.
- Daily consistency view for the selected week.
- Curricula summary, shown as a secondary list grouped by subject.
- Secondary filters for student, subject, curricula, teacher, location, date range, and createdBy.
- Clean, modern, simple visual treatment that avoids showing too many controls at once.

### Out of scope for v1
- Mastery milestones.
- Sentiment tracking.
- AI recommendations for what to study next.
- Goal-setting and progress-against-goal workflows, except as a non-blocking future/nice-to-have
  note.
- Editing or deleting lesson entries from the dashboard.
- Public sharing.
- Multi-family or productized user management.
- Full account management, password reset, roles, or permissions beyond two private users.


## 5. Data Contract
The dashboard should treat the current lesson schema as read-only. The available fields are:

- `date`
- `time`
- `students`
- `teachers`
- `subject`
- `curricula`
- `duration`
- `location`
- `notes`
- `transcript`
- `createdBy`
- `createdAt`
- `extractorVersion`

For the SQLite table, these correspond to the `entries` columns in `lessons_db.py`, with list fields
stored as JSON text. The dashboard should be prepared to query `students` and `teachers` via
`json_each`.

V1 should avoid implying that sentiment or mastery exists in the data. If those are shown anywhere,
they should be labeled as future work, not inferred silently.


## 6. Technical Decisions
### Recommended v1 stack
- **Backend / web server:** FastAPI.
- **Templates:** Jinja server-rendered pages.
- **Light interactivity:** HTMX where partial page updates are useful.
- **Styling:** Tailwind CSS with DaisyUI components.
- **Charts:** Chart.js.
- **Database:** read from the lesson logger SQLite DB; keep any dashboard-owned state separate from
  the lesson-entry schema.
- **Deployment target:** Fly.io as a separate dashboard app from Hermes.

Rationale: this stack keeps the first version close to Python and SQLite, avoids a full React/Next.js
or Svelte app for v1, and still allows a modern dashboard feel. It should be easy for AI coding
agents to generate and maintain.

### Authentication
- Use HTTP Basic Auth for v1.
- Support exactly two configured users at launch: Randy and TL.
- Store credentials in Fly secrets, never in git.
- The authenticated username becomes the dashboard user identity for preference lookup.
- This is private-family authentication, not a product-grade account system.

### User preferences
The app should include a minimal user-preferences foundation in v1, even if the first interface only
uses a few settings.

Initial preference candidates:

- Default student.
- Default time mode: Week, Month, or School Year.
- Last selected subject filter.
- Whether secondary filters are expanded or hidden.
- Optional future defaults for chart style or visible sections.

Implementation guidance:

- Do not change the lesson-entry schema or the `entries` table for preferences.
- Store preferences in dashboard-owned state, such as a separate `dashboard_state.sqlite` file or
  equivalent dashboard-only table/file on the dashboard app's Fly volume.
- Key preferences by Basic Auth username.
- It is acceptable for v1 to read preferences and use sane defaults before adding a polished
  "save my default view" UI.

### Editing posture
- V1 is read-only for lesson entries.
- Avoid architectural choices that would make future editing/deleting hard, but do not build those
  workflows yet.
- Recent lesson rows can later become detail/edit entry points.


## 7. Time Ranges
The dashboard should support three main time modes:

### Week
- Default view.
- Monday-Sunday calendar week.
- Shows daily consistency clearly.
- Best answer to: "What did we do this week?"

### Month
- Calendar month.
- Best answer to: "What has this month looked like so far?"
- Should preserve the same main metrics and subject breakdown as week view.

### Learning Year
- We are homeschooling, so we're going to use the term "learning year" instead of "school year."
- Learning year starts in September.
- For v1, define the learning year as Sept 1 through Aug 30.
- Best answer to: "What is the larger year-to-date pattern?"
- This can be simpler than week/month in the first build, but the concept should be present early
  so the app does not paint itself into a corner.


## 8. First Screen Information Architecture
The first screen should be organized from broad to detailed:

1. **Header / selector row**
   - Student selector, defaulting to the primary student in the data.
   - Time range toggle: Week, Month, School Year.
   - Current range label, e.g. "Week of Jun 8-14".
   - A compact "Filters" button for secondary controls.

2. **Summary cards**
   - Total learning time.
   - Number of sessions.
   - Subjects covered.
   - Average minutes per active day, if easy to compute.

3. **Subject time chart**
   - Bar chart by subject for the selected range.
   - Include standard subjects first: Math, Reading, Writing, Art, Science, Music.
   - Include custom subjects after standard subjects if present.

4. **Consistency view**
   - In week mode: daily bars or tiles for Monday-Sunday showing total minutes per day.
   - In month mode: compact calendar heatmap or grouped daily bars.
   - In school-year mode: month-by-month summary bars.

5. **Curricula / activity detail**
   - Secondary list grouped by subject.
   - Example: Math -> Beast Academy, Singapore Math, Khan Academy.
   - Show total time and session count per curricula when available.
   - Empty curricula should be grouped as "Not specified" or hidden behind an option, depending on
     what looks cleaner.

6. **Recent lessons**
   - Small list of recent entries in the selected range.
   - Show date, subject, duration, curricula if present, and a short notes snippet.
   - This helps users trust the aggregate charts.


## 9. Filters And Facets
The dashboard should keep the default interface clean. Filters should be secondary, likely in a
drawer, popover, or collapsible panel.

Essential filters:

- Student.
- Date range / time mode.
- Subject.

Secondary filters:

- Curricula.
- Teacher.
- Location.
- Created by.

Design rule: the user should not have to choose a teacher, curricula, or location to get value from
the dashboard. Those should help with deeper exploration but should not dominate the page.


## 10. Visual Direction
The dashboard should feel clean, modern, design-forward, and lightweight. It should lean more toward
a polished admin dashboard than a family notebook.

Design qualities:
- Mobile-friendly first, with a pleasant desktop layout.
- Low visual clutter.
- Rounded cards and clear spacing.
- Calm but modern color palette, with subjects color-coded consistently.
- Large readable numbers for summary metrics.
- Charts that are understandable without configuration.
- Controls hidden until needed.

Avoid:
- Dense analytics-product UI.
- Large filter panels visible by default.
- Too many chart types at once.
- Overstating what the data can prove.


## 11. Suggested Components
### `DashboardHeader`
- Shows student, time mode, date range label, and filters button.
- Should also expose the current signed-in user in a subtle way, e.g. small account label or menu.

### `SummaryCards`
- Four cards: total time, sessions, subjects covered, average active-day minutes.

### `SubjectTimeChart`
- Main chart for minutes by subject.
- Should support week, month, and school-year ranges.

### `ConsistencyChart`
- Week: seven-day bar/tile view.
- Month: daily mini-bars or calendar heatmap.
- School year: monthly bars.

### `CurriculaBreakdown`
- Grouped list by subject.
- Shows curricula name, total minutes, and session count.

### `RecentLessonsList`
- Shows recent matching entries with enough detail to audit the rollups.

### `FilterDrawer`
- Holds secondary filters.
- Should be easy to ignore.

### `UserPreferences`
- Small dashboard-owned persistence layer keyed by authenticated username.
- Should support separate Randy/TL defaults even if the first UI for saving preferences is
  minimal.


## 12. Nice-To-Have Future Ideas
These should not block v1:

- Parent-configured time expectations, such as target minutes per day or week.
- Visual comparison against those targets.
- Home vs away summary, based on `location`.
- "What might need more attention?" prompts generated from time patterns.
- Mastery/milestone integration from a future separate app.
- Resource/curricula integration from a future separate app.
- Sentiment/engagement tracking once the schema intentionally supports it.
- A polished "save this as my default dashboard" control.
- Entry editing/deleting from the recent lessons list.


## 13. Acceptance Criteria For Starter Prototype
A first useful prototype is complete when:

- It can load a fixture SQLite database.
- It protects the app with Basic Auth using two configured users.
- It can identify the authenticated user and apply user-specific defaults.
- It defaults to a student-level weekly view.
- It shows total time, total sessions, and subjects covered for the selected week.
- It shows minutes by subject for the selected range.
- It shows learning consistency across the selected week.
- It can switch between Week, Month, and School Year.
- It has secondary filters without making the first screen feel busy.
- It shows a curricula summary when curricula data exists.
- It shows recent lesson entries so users can connect charts back to records.
- It does not display fake mastery or sentiment metrics as if they are real captured data.


## 14. Open Design Questions
- Should the subject chart use fixed colors by subject from the start?
- Should "school year" be August 1-July 31, or should that become a configurable setting later?
- Should empty curricula be visible as "Not specified" or omitted from the default list?
- Should the dashboard include a simple "active days this week" metric?
- Should the recent lessons list be visible on mobile by default, or tucked below the main charts?
- Should the first saved preference be just default time mode/student, or should filters be saved too?
