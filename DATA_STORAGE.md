# Stage 1–5 research data-storage design

## 1. Scope and decision status

This document describes the **implemented five-stage product’s output schema**:
profile selection, job selection, pre-outcome should-pass judgments, historical
outcomes, and perceived-fairness feedback. It is not the target framework’s schema.

The target working direction is to study how algorithmic fairness conditions or
outcome characteristics influence perceived fairness: assign a profile, present
competitors, generate/reveal screening outcomes using relevant attributes and the
designed fairness matrix/condition, then collect feedback. It excludes the current
pre-outcome judgment task. Methodological details remain provisional and undefined;
this document adds no target tables, measures or migration/deletion requirements.

X1/X2/Y1 are legacy research elements still recorded by the current product, not
active target variables. Existing method identifiers and survey answers do not by
themselves operationalize the target fairness condition or its future measurement.
Preserving existing records does not require retaining the previous research structure.

The interface creates **one case per session**. Judgment submission and result
retrieval are a single action. Results and feedback share a page; submitting feedback
ends the visit. Returning participants can resume an open visit or start a new one;
the latter closes the previous visit while preserving partial records. The schema
supports multiple cases per session, but the current interface does not expose this.

References: [FIVE_STAGE_FRAMEWORK.md](FIVE_STAGE_FRAMEWORK.md) describes current
product behavior separately from the target direction; [data-structure.md](data-structure.md)
defines current fictional input records. [README.md](README.md) covers setup.
`backend/storage.py` defines physical columns/keys, while `experiment.py` and
`fairness.py` enforce workflow and submitted-answer rules.

New profile snapshots include `protected_attributes.marital_status`; older snapshots
remain valid without it. The examples below retain the older snapshot shape. Source
`results.score` is not stored or exposed; historical inputs freeze only
`results.decision`. No database migration is required for these source additions.

### Current recording requirements (not target requirements)

- Stage 1: record profiles viewed, their order, review time per profile, refreshes
  or changes (x1), confirmed profile, and time to confirmation.
- Stage 2: record the displayed job(s), fixed or selected job, and visible review
  time. Only enabled selection yields an x2 choice and two unselected options.
- Stage 3: record six profiles, saved order/snapshots, should-pass judgments and review time.
- Stage 4: record historical-only inputs, method/final outcomes, revelation and shared-page timing.
- Stage 5: record rating, group opinions/reasons and individual comparisons/reasons.
- Do not calculate a best applicant, fairness verdict, or participant correctness.

### Confirmed demo choices

- A reusable opaque participant code links returning participants to the same ID.
- A participant may have multiple sessions; a session may contain multiple cases.
- Record required viewing history and submitted choices, not draft edits or every click.
- New cases sample Software Engineer profiles. Refresh is disabled by default;
  when enabled it excludes the current profile, with later repeats allowed.
  Cases without configuration retain their original all-applicant sampling.
- Use the confirmed profile's explicit `job_id` as its original job in this fictional
  demo. This is a demo substitution, not evidence of a real historical application.
- Default to the fixed Software Engineer job; enabled selection offers all three
  dataset jobs in saved shuffled order, without original-job or fit labels.
  Preserve original dataset text within the Chinese interface.
- Measure visible-page time. Hidden time and user-action waits are excluded;
  background timing-checkpoint requests currently leave the timer running.

### Implemented engineering choices and proposed exports

SQLite, UUIDs, table names, JSON snapshots, timestamps and constraints are implemented
storage choices, not additional research variables. Export layouts are suggestions;
export generation is not implemented.

## 2. Storage conventions

- Normal database transactions enable foreign keys. Schema migrations temporarily
  disable enforcement and check foreign-key integrity before committing.
- `TEXT`: strings, IDs, UTC timestamps, or serialized JSON as specified below.
- `INTEGER`: whole numbers, including nonnegative durations in milliseconds.
- UUIDs are generated UUID4 strings. Codes are separately generated, unique,
  reusable opaque strings; they contain no name, email, or demographic information.
- Timestamps use UTC ISO 8601, for example `2026-09-13T09:00:00.000Z`.
- Snapshot JSON columns contain objects; `group_selections_json` contains an array.
  Both are serialized text. Proposed exports can decode them rather than double-encode them.
- All fields are required and non-null unless marked nullable. `NULL` means not
  yet recorded/unavailable; zero means an observed or initialized zero count/time.
- Preparation/retrieval timestamps use server time; display/submission timestamps
  use browser-supplied UTC times validated by the backend. They
  are not substitutes for visible-page durations and need not differ by that duration.
- Store recorded time only: interrupted visits can have an incomplete duration.
  Never infer continuous attention from page visibility.

## 3. IDs and shared records

```text
participants → sessions → cases
  case → stage1_profile_selection → stage1_profile_views
       → stage2_job_selection → stage2_job_options
       → stage3_competition_assessment → stage3_applicants
       → stage4_outcome_revelation → stage4_applicant_outcomes
       → stage5_fairness_feedback → stage5_applicant_comparisons
  stage4_historical_inputs → stage3_applicants (case_id + profile_id)
  stage4_applicant_outcomes → stage3_applicants (case_id + profile_id)
  stage5_applicant_comparisons → two stage4_applicant_outcomes (case + profile IDs)
```

### ID purposes

| ID | Purpose |
| --- | --- |
| `participant_id` | Stable research-participant identity across sessions; never an applicant ID. |
| `participant_code` | Reusable lookup code entered on return to recover the same participant identity. Treat it as a bearer code; omit it from routine analysis exports. |
| `session_id` | One visit/sitting. Reloading resumes the current session; a deliberate new visit creates another session under the same participant. |
| `case_id` | One distinct scenario/run instance inside a session, linking records across all five implemented stages. |
| `profile_id` | Existing fictional applicant identifier from `applicants.json`. |
| `job_id` | Existing job identifier from `jobs.json`; use this field, not digits parsed from profile IDs. |

A separate reusable `scenario_id` is not defined: the current references do not
define scenario templates. `case_id` distinguishes concrete runs. Code reuse links
records; it does not independently verify that the same human supplied the code.

### `participants`

| Field | SQLite type | Rule / meaning |
| --- | --- | --- |
| `participant_id` | TEXT | Primary key; UUID4. |
| `participant_code` | TEXT | Unique opaque code; normalize letter case on entry. |
| `created_at` | TEXT | Identity creation time. |

### `sessions`

| Field | SQLite type | Rule / meaning |
| --- | --- | --- |
| `session_id` | TEXT | Primary key; UUID4. |
| `participant_id` | TEXT | Foreign key → `participants.participant_id`. |
| `started_at` | TEXT | Visit creation time. |
| `ended_at` | TEXT, nullable | Explicitly recorded end of the sitting; unknown if the browser simply disappears. |

### `cases`

| Field | SQLite type | Rule / meaning |
| --- | --- | --- |
| `case_id` | TEXT | Primary key; UUID4. |
| `session_id` | TEXT | Foreign key → `sessions.session_id`. |
| `case_number` | INTEGER | Positive sequence within session; unique together with `session_id`. |
| `started_at` | TEXT | Case creation time. |
| `schema_version` | TEXT | Collection-version label; new cases use `configurable_entry_v1`. Existing labels are preserved, not rewritten to describe migrated physical tables. |
| `timing_policy` | TEXT | Initial value `visible_page`. |

No overall experiment-completion field is defined. Stage submission timestamps
describe completion of those stages only. Rows follow their recording lifecycle: Stage 3 and historical inputs are prepared
before review; Stage 4 final results appear after submission; Stage 5 starts on
acknowledgment of the survey-containing page.

### `case_configuration` — one immutable configuration snapshot per new case

| Field | SQLite type | Meaning |
| --- | --- | --- |
| `case_id` | TEXT PK/FK | References `cases.case_id`. |
| `profile_refresh_enabled` | INTEGER NOT NULL | Boolean 0/1; default configuration is 0. |
| `job_selection_enabled` | INTEGER NOT NULL | Boolean 0/1; default configuration is 0. |
| `assigned_profile_job_id` | TEXT NOT NULL | Source job reference; `job_001` (Software Engineer). |

New cases use `configurable_entry_v1`. These settings are copied from backend
configuration at case creation and remain fixed across restart/resume. Preserve
this table in research exports to distinguish assigned tasks from optional choices.
Older cases have no row and retain legacy sampling and controls; do not backfill
or rewrite them. Source JSON is unchanged.

Example (case ID must reference an existing new-version case):

```json
{"case_id":"30000000-0000-4000-8000-000000000005","profile_refresh_enabled":0,"job_selection_enabled":0,"assigned_profile_job_id":"job_001"}
```

Stage 1 and Stage 2 still use separate display acknowledgments and durations.
Disabled refresh gives one profile view and `refresh_count = 0`; `confirmed_at`
and `ended_by = confirm` record continuation with the assigned profile, not free
selection. Enabled refresh uses only Software Engineer profiles, with no immediate
repeat. Disabled job selection gives one `stage2_job_options` row (position 1);
`selected_job_id` becomes `job_001` on continuation. `submitted_at` is that
acknowledgment and `decision_duration_ms` measures job review, not choice time.
Enabled selection retains three shuffled options and the existing choice semantics.
The legacy field/table names remain for compatibility. Do not interpret fixed
assignment as an observation of a participant's preference. Stage 3–5 are unchanged.

The Stage 1–2 descriptions and historical examples below retain legacy selection
terminology; apply these configuration-dependent interpretations to new cases.

## 4. Stage 1 tables

### `stage1_profile_selection` — one row per case that reaches Stage 1

| Field | SQLite type | Rule / meaning |
| --- | --- | --- |
| `case_id` | TEXT | Primary key and foreign key → `cases.case_id`. |
| `started_at` | TEXT | First assigned profile displayed. |
| `confirmed_at` | TEXT, nullable | Participant confirms the current profile. |
| `refresh_count` | INTEGER | x1; starts at 0; excludes initial assignment and browser reloads. |
| `confirmed_profile_id` | TEXT, nullable | Confirmed applicant; source reference → `applicants.json.profile_id`. |
| `confirmation_duration_ms` | INTEGER, nullable | Final total visible review time across all views, from first display to confirmation. |

### `stage1_profile_views` — one row per profile presentation

| Field | SQLite type | Rule / meaning |
| --- | --- | --- |
| `case_id` | TEXT | Foreign key → `stage1_profile_selection.case_id`. |
| `view_number` | INTEGER | Positive, contiguous order starting at 1; primary key together with `case_id`. |
| `profile_id` | TEXT | Source applicant reference. |
| `displayed_profile_json` | TEXT (JSON object) | Exact participant-visible profile data; preserve nested qualifications and demographic fields. |
| `displayed_at` | TEXT | First display time for this view. |
| `ended_at` | TEXT, nullable | Time of refresh or confirmation. |
| `duration_ms` | INTEGER | Cumulative visible review time captured for this view; initialized to 0. |
| `ended_by` | TEXT, nullable | `refresh` or `confirm`; null while the view is open. |

The profile snapshot contains `job_related_attributes` and `protected_attributes`
as displayed. It excludes hidden fields such as `decision`, `job_id`, and provenance.
The external `profile_id` field supplies record linkage without displaying it.

Refreshing prepares another view, recorded when its display is acknowledged, even when a previously seen profile reappears.
Reloading the current view resumes that row. At confirmation, the confirmed profile
must equal the last view's profile; all views are closed and the final view ends by
`confirm`. `confirmation_duration_ms` equals the sum of view `duration_ms` values.
This total is a derived summary, not an additional measurement.

## 5. Stage 2 tables

### `stage2_job_selection` — one row per case that reaches Stage 2

| Field | SQLite type | Rule / meaning |
| --- | --- | --- |
| `case_id` | TEXT | Primary key and foreign key → `cases.case_id`. |
| `started_at` | TEXT | Job options first displayed. |
| `submitted_at` | TEXT, nullable | Participant explicitly confirms the job choice. |
| `original_job_id` | TEXT | Source job associated with the confirmed profile; stored internally, not labeled in the interface. |
| `selected_job_id` | TEXT, nullable | x2; must reference an offered job for this case. |
| `decision_duration_ms` | INTEGER | Cumulative visible job review/choice time; initialized to 0, final on submission. |

### `stage2_job_options` — one fixed-job row or three selectable-job rows

| Field | SQLite type | Rule / meaning |
| --- | --- | --- |
| `case_id` | TEXT | Foreign key → `stage2_job_selection.case_id`. |
| `display_position` | INTEGER | 1, 2, or 3; primary key together with `case_id`. |
| `job_id` | TEXT | Source job reference; unique within the case. |
| `displayed_job_json` | TEXT (JSON object) | Exact displayed `title` and `description`. |

Save option order once and retain it on reload. The original job appears exactly
once, alongside the other two jobs only when selection is enabled. In that mode,
the two unselected jobs are derived by excluding
`selected_job_id` from these rows; do not duplicate them in separate fields.
Draft selections before explicit confirmation are not research records in this design.

## 6. Integrity, persistence, and source preservation

- Insert related rows atomically. Stage 2 requires a confirmed Stage 1 record.
- Source IDs reference JSON data, not SQL tables; validate them in the backend.
  SQLite foreign keys enforce relationships between research tables.
- Freeze display content at preparation and persist it at the stage-specific recording
  point (display acknowledgment for Stages 1–2, group preparation for Stage 3); do not overwrite it
  when source datasets later change. Snapshots are display data, not modified source records.
- Never rewrite `jobs.json` or `applicants.json`. Preserve their field names,
  provenance `{}`, explicit links, and current per-job counts.
- Grouping applicants by source `pass`/`reject` remains a backend dataset operation;
  it is not a participant response or a fairness label.
- Counts and durations are nonnegative integers. `refresh_count` equals the number
  of view rows ending by `refresh`. Do not increment it for repeated HTTP requests.
- Give each mutating request a stable technical action ID and process retries
  idempotently within a transaction. An implementation receipt mechanism is not a
  research variable and is omitted from analysis exports. Reject stale-view actions.
- Checkpoint cumulative visible durations; merge them without adding the same
  checkpoint twice. Pause while hidden or awaiting a user-action request; background timing checkpoints
  do not pause the running timer.
- Retain partial records: an open profile view has no end fields; an unfinished job
  selection has no selected job/submission timestamp but retains offered jobs and time.
- A crash may lose time after the last successful checkpoint. Do not silently fill
  that gap with wall-clock time. Neither zero nor null should be recoded as rejection.
- Confirmation fields must be populated together. Reject later edits to confirmed
  records through the participant flow. Keep abandoned cases instead of reusing IDs.

## 7. Suggested database and export layout

```text
Product/
├── DATA_STORAGE.md
├── jobs.json                         # Existing, unchanged source
├── applicants.json                   # Existing, unchanged source
└── backend/outputs/
    ├── research.sqlite3              # Implemented research store
    └── exports/<UTC-export-time>/
        ├── participants.jsonl        # participant_code excluded by default
        ├── sessions.jsonl
        ├── cases.jsonl
        ├── stage1_profile_selection.jsonl
        ├── stage1_profile_views.jsonl
        ├── stage2_job_selection.jsonl
        └── stage2_job_options.jsonl
```

The database path is implemented; export paths remain proposed. Collected databases
and exports are excluded from source control.
Use one JSON object per line; preserve nulls and nested snapshots. Optional flat CSV
exports can supplement JSON Lines. SQLite is the source of truth; exports are derived.

The implemented database is created on the first participant API request. Export
generation remains unimplemented; the export layout above is a suggestion. Private
`technical_credentials`, `technical_receipts`, and `technical_case_state` tables
store hashed browser tokens, idempotent request receipts, and pending presentations
with writer ownership/revisions. Receipts can contain issued tokens for recovery;
never export these technical tables as research data. Research tables stay separate.
Stage 1–2 display rows follow browser acknowledgment. Stage 3 group rows and
Stage 4 historical inputs are prepared earlier; Stage 4 final results are persisted
at retrieval. Display timestamps are recorded separately; Stage 5 acknowledgment
creates the unanswered feedback row.
Checkpoint cadence is five seconds plus page-hiding and action submissions. Abrupt
termination can lose time since the last successful checkpoint; prolonged network
failures can extend that gap. A new page claim invalidates prior writers.

Python can use `sqlite3` and `pandas.read_sql_query`. Join relevant stage summary
tables on `case_id`, then cases → sessions → participants to build one row per case.
Keep profile views and job options in separate dataframes: joining both detail tables
directly would multiply rows and could inflate counts. Retain `participant_id` and
`session_id` in analysis outputs to distinguish repeated observations.

## 8. Example records

The following valid JSON represents decoded exports, not SQL insertion syntax.
IDs and timestamps are illustrative. This is a legacy/schema-capacity example,
not a sample of the current one-case-per-session UI. The completed Stage 1–2 example has one refresh,
28 seconds of profile review, and 15 seconds of job-choice time. The other cases have
been created but have no recorded stage displays yet; this does not imply completion.
Only Stage 1–2 tables are projected here; later-stage rows are omitted from this example.

```json
{
  "participants": [
    {"participant_id":"10000000-0000-4000-8000-000000000001","participant_code":"A7C1-82AF-19D0-EF32","created_at":"2026-09-13T09:00:00.000Z"},
    {"participant_id":"10000000-0000-4000-8000-000000000002","participant_code":"B4AD-63CF-20E1-AB45","created_at":"2026-09-13T11:00:00.000Z"}
  ],
  "sessions": [
    {"session_id":"20000000-0000-4000-8000-000000000001","participant_id":"10000000-0000-4000-8000-000000000001","started_at":"2026-09-13T09:00:00.000Z","ended_at":"2026-09-14T09:00:00.000Z"},
    {"session_id":"20000000-0000-4000-8000-000000000002","participant_id":"10000000-0000-4000-8000-000000000001","started_at":"2026-09-14T09:00:00.000Z","ended_at":null},
    {"session_id":"20000000-0000-4000-8000-000000000003","participant_id":"10000000-0000-4000-8000-000000000002","started_at":"2026-09-13T11:00:00.000Z","ended_at":null}
  ],
  "cases": [
    {"case_id":"30000000-0000-4000-8000-000000000001","session_id":"20000000-0000-4000-8000-000000000001","case_number":1,"started_at":"2026-09-13T09:00:00.000Z","schema_version":"stage1_2_v1","timing_policy":"visible_page"},
    {"case_id":"30000000-0000-4000-8000-000000000002","session_id":"20000000-0000-4000-8000-000000000001","case_number":2,"started_at":"2026-09-13T09:10:00.000Z","schema_version":"stage1_2_v1","timing_policy":"visible_page"},
    {"case_id":"30000000-0000-4000-8000-000000000003","session_id":"20000000-0000-4000-8000-000000000002","case_number":1,"started_at":"2026-09-14T09:00:00.000Z","schema_version":"stage1_2_v1","timing_policy":"visible_page"},
    {"case_id":"30000000-0000-4000-8000-000000000004","session_id":"20000000-0000-4000-8000-000000000003","case_number":1,"started_at":"2026-09-13T11:00:00.000Z","schema_version":"stage1_2_v1","timing_policy":"visible_page"}
  ],
  "stage1_profile_selection": [
    {"case_id":"30000000-0000-4000-8000-000000000001","started_at":"2026-09-13T09:00:01.000Z","confirmed_at":"2026-09-13T09:00:30.000Z","refresh_count":1,"confirmed_profile_id":"candidate_1001","confirmation_duration_ms":28000}
  ],
  "stage1_profile_views": [
    {"case_id":"30000000-0000-4000-8000-000000000001","view_number":1,"profile_id":"candidate_1002","displayed_profile_json":{"job_related_attributes":{"education":"数字媒体技术本科","experience_years":2,"skills":["HTML","CSS","JavaScript","网页交互开发"]},"protected_attributes":{"gender":"男性","age":25}},"displayed_at":"2026-09-13T09:00:01.000Z","ended_at":"2026-09-13T09:00:11.000Z","duration_ms":10000,"ended_by":"refresh"},
    {"case_id":"30000000-0000-4000-8000-000000000001","view_number":2,"profile_id":"candidate_1001","displayed_profile_json":{"job_related_attributes":{"education":"计算机科学本科","experience_years":3,"skills":["Python","SQL","FastAPI","PostgreSQL","后端接口开发"]},"protected_attributes":{"gender":"女性","age":26}},"displayed_at":"2026-09-13T09:00:12.000Z","ended_at":"2026-09-13T09:00:30.000Z","duration_ms":18000,"ended_by":"confirm"}
  ],
  "stage2_job_selection": [
    {"case_id":"30000000-0000-4000-8000-000000000001","started_at":"2026-09-13T09:00:31.000Z","submitted_at":"2026-09-13T09:00:46.000Z","original_job_id":"job_001","selected_job_id":"job_003","decision_duration_ms":15000}
  ],
  "stage2_job_options": [
    {"case_id":"30000000-0000-4000-8000-000000000001","display_position":1,"job_id":"job_002","displayed_job_json":{"title":"Financial Analyst","description":"分析财务报表、编制预算并评估经营成本，要求熟悉财务分析、会计基础和 Excel。"}},
    {"case_id":"30000000-0000-4000-8000-000000000001","display_position":2,"job_id":"job_003","displayed_job_json":{"title":"Graphic Designer","description":"设计品牌视觉和宣传材料，要求掌握排版、色彩搭配，并熟悉 Adobe Photoshop 和 Illustrator。"}},
    {"case_id":"30000000-0000-4000-8000-000000000001","display_position":3,"job_id":"job_001","displayed_job_json":{"title":"Software Engineer","description":"开发后端服务，要求熟悉 Python 和 SQL。"}}
  ]
}
```

Participant ending `0001` has two sessions and three cases. Two of those cases share
the first session. Participant ending `0002` has a different session and case. Every
stage row in this example links to case ending `0001`, and therefore to the first
session and first participant. Reusing an applicant profile in another case never
merges the research participants.

## 9. Coverage checklist

| Requirement | Stored representation |
| --- | --- |
| Viewed profiles and order | `stage1_profile_views.profile_id`, `view_number`, snapshots |
| Review time for each profile | `stage1_profile_views.duration_ms` |
| Refreshes / x1 | `refresh_count`, supported by `ended_by = refresh` rows |
| Final profile | `confirmed_profile_id` |
| Time to confirmation | `confirmation_duration_ms`, plus first-display and confirmation timestamps |
| Selected job / x2 | `selected_job_id` |
| Both unselected jobs and characteristics | Three option rows and snapshots, excluding selected job |
| Job-decision time | `decision_duration_ms` |
| Six-person opinions / legacy y1 | Stage 3 applicant judgments, snapshots, order and timing |
| Historical inputs and revealed results | Separate Stage 4 method-specific/common tables |
| Shared results/survey time | Stage 4 `duration_ms`; not survey-only time |
| Fairness feedback | Stage 5 feedback, embedded selection JSON and comparison pairs |
| Cross-stage linkage | Shared `case_id` |
| Repeated participation | Cases → sessions → stable `participant_id` |
| Incomplete participation | Retained partial rows, null submission fields, accumulated recorded durations |


## 10. Stage 3 — applicant review and should-pass judgments only

Stage 3 records the six profiles actually offered for review, their order, the
selected-job snapshot, the participant's submitted opinions, and review timing.
It does not store source decisions, generated outcomes, case decisions, generation
methods, or rule explanations. Those are not properties of participant judgments.

### `stage3_competition_assessment`

| Field | SQLite type | Meaning |
| --- | --- | --- |
| `case_id` | TEXT PK/FK | References `cases.case_id`. |
| `selected_job_id` | TEXT NOT NULL | Confirmed Stage 2 job. |
| `displayed_job_json` | TEXT/JSON NOT NULL | Saved selected-job title and description. |
| `prepared_at` | TEXT NOT NULL | UTC time the review group was prepared. |
| `started_at` | TEXT nullable | First browser acknowledgment of review display. |
| `submitted_at` | TEXT nullable | Final submission of all six judgments. |
| `judgment_duration_ms` | INTEGER NOT NULL | Cumulative visible review milliseconds; initially zero. |

### `stage3_applicants`

| Field | SQLite type | Meaning |
| --- | --- | --- |
| `case_id` | TEXT NOT NULL/FK | Parent assessment; part of primary key. |
| `display_position` | INTEGER NOT NULL | 1–6; primary key with case ID. |
| `profile_id` | TEXT NOT NULL | Dataset applicant ID; unique with case ID. |
| `applicant_role` | TEXT NOT NULL | `participant` or `competitor`. |
| `displayed_profile_json` | TEXT/JSON NOT NULL | Frozen qualifications and demographic content shown. |
| `participant_judgment` | TEXT nullable | Submitted `pass` / `reject` opinion (y1), not an actual outcome. |

Position 1 is the participant; positions 2–6 are the competitors in saved order.
All six judgments commit atomically, with three `pass` and three `reject` required
by the current interface. Before submission all database judgments are NULL. Local
unsent drafts remain browser session data, not research observations. Display
acknowledgment, visible timing, revisions, retries and tab ownership are unchanged.
No actual outcome is included in the Stage 3 participant response.

Example projection (all rows share a case ID and each also stores its snapshot):

| display_position | profile_id | applicant_role | participant_judgment |
| --- | --- | --- | --- |
| 1 | profile-A | participant | pass |
| 2 | profile-B | competitor | reject |
| 3 | profile-C | competitor | pass |
| 4 | profile-D | competitor | reject |
| 5 | profile-E | competitor | pass |
| 6 | profile-F | competitor | reject |

## 11. Stage 4 — common outcomes and method-specific inputs

### Separation and lifecycle

The common contract is a final screening outcome per applicant, the method used,
any separately applied scenario rule, and revelation/review timing. It does not
require every method to supply a historical source value or intermediate decision.
Only `historical` is implemented. The dataset contains fictional fixed demo results;
these are not verified hiring records or objectively fair decisions.

**Engineering choice:** preserve the existing balanced historical sampling behavior.
When selecting the review group, freeze only the historical method's source inputs
in its dedicated Stage 4 table. Do not create common result or revelation rows yet.
This keeps results reproducible if the dataset changes between review and revelation.
Input availability is not outcome generation, presentation, or participant exposure.
The historical input capture shares the group-preparation transaction; its preparation
time can be linked through the Stage 3 assessment's `prepared_at`.

For the original job, historical source decisions are used unchanged. For an
alternative job, the participant is rejected by the separate scenario rule. Sampling
still provides two pass/three reject competitors for a passing original-job participant,
and three pass/two reject competitors otherwise. Final Stage 4 outcomes must be
exactly three `pass` and three `reject`, including the participant. No final case
outcome is saved during Stage 3, and no `case_decision` field remains.

### Common table: `stage4_outcome_revelation`

| Field | SQLite type | Meaning |
| --- | --- | --- |
| `case_id` | TEXT PK/FK | References `stage3_competition_assessment.case_id`. |
| `outcome_method` | TEXT NOT NULL | Backend-selected method: currently `historical` (previous-design method label, not a target fairness-condition definition). |
| `generated_at` | TEXT NOT NULL | UTC server retrieval and persistence time. |
| `revealed_at` | TEXT nullable | First browser acknowledgment of actual results display. |
| `continued_at` | TEXT nullable | Explicit completion of results review by ending the visit. |
| `duration_ms` | INTEGER NOT NULL | Nonnegative cumulative visible review milliseconds, initially zero. |

### Common table: `stage4_applicant_outcomes`

| Field | SQLite type | Meaning |
| --- | --- | --- |
| `case_id` | TEXT NOT NULL/FK | Parent revelation, part of composite primary key. |
| `profile_id` | TEXT NOT NULL | Other part of primary key; matching Stage 3 applicant. |
| `revealed_decision` | TEXT NOT NULL | Final `pass` / `reject` after any scenario rule. |
| `decision_basis` | TEXT NOT NULL | Method identifier: `historical`, `llm`, `matrix`, or `random_method`; currently always `historical`. |
| `applied_rule` | TEXT nullable | `alternative_job_rejection` when applied; NULL means no scenario override. |

Composite FK `(case_id, profile_id)` references `stage3_applicants(case_id, profile_id)`.
`decision_basis` names the generation method; it never contains `source_decision`.
A rule override does not rename the method. The per-applicant method matches the
parent `outcome_method`; the coordinator writes both atomically. There is no generic
`method_decision` field: intermediate data belongs to the method that needs it.

### Historical-only table: `stage4_historical_inputs`

| Field | SQLite type | Meaning |
| --- | --- | --- |
| `case_id` | TEXT NOT NULL | Part of composite primary key. |
| `profile_id` | TEXT NOT NULL | Part of composite primary key. |
| `source_decision` | TEXT NOT NULL | Frozen dataset `pass` / `reject` for this profile's original job. |

Composite FK `(case_id, profile_id)` references the Stage 3 applicant. This table
can exist before a revelation parent exists because it stores inputs, not outputs.
Exactly six input rows are captured for the current historical case. No source
job field or full dataset copy is needed: Stage 2 preserves the original/selected
job references, and Stage 3 holds the displayed profile content. Retrieval reads
these inputs, never mutable dataset values. Historical's pre-rule result is precisely
this source value, so storing it again as a method result would be redundant.

### Method extension contract

`generate_outcomes(method, applicants, method_data=...)` accepts neutral Stage 3
applicant records and a separate method-owned input object. It returns a mapping
from each profile ID to `pass` / `reject`. The historical handler validates and reads
its dedicated input rows. The common resolver applies scenario rules and checks
six unique results and the required 3/3 balance, without historical field access.

The dispatcher recognizes `llm`, `matrix`, and `random_method` but raises explicit
not-implemented errors. Later handlers can have their own input/metadata tables,
linked by case ID and optionally profile ID, and their own preparation/persistence
logic. No speculative fields, empty method tables, or metadata requirements are
created for these methods. Their sampling and protocol details are not defined here.

### Linked historical override example

Use the six illustrative Stage 3 records above for `case-alt-01`. These identifiers
are illustrative, not seed records. All parent participant/session/case records and
Stage 2 selection must exist before these records can be inserted.

| profile_id | historical input: source_decision | common: revealed_decision | common: decision_basis | common: applied_rule |
| --- | --- | --- | --- | --- |
| profile-A | pass | reject | historical | alternative_job_rejection |
| profile-B | pass | pass | historical | NULL |
| profile-C | pass | pass | historical | NULL |
| profile-D | pass | pass | historical | NULL |
| profile-E | reject | reject | historical | NULL |
| profile-F | reject | reject | historical | NULL |

These are joined projections of two tables, not one wide record. Historical inputs
have four passes here; the final common outcomes have three. Judgments remain
independent, with no correctness or fairness score.

```json
{"case_id":"case-alt-01","outcome_method":"historical","generated_at":"2026-09-14T09:00:00.000Z","revealed_at":"2026-09-14T09:00:00.300Z","continued_at":"2026-09-14T09:00:12.500Z","duration_ms":12000}
```

### Visibility, timing and storage

Before submission, only review data is exposed. The single “确认并查看结果” action validates and finalizes all six judgments and
retrieves outcomes in one authenticated, current-owner transaction. There is no
intermediate confirmation screen. If retrieval fails, the transaction rolls back
and the browser retains its draft for retry. Successful submission locks the
judgments and displays results immediately; all six rows and the parent commit
atomically. Retries/reloads reuse them. Results display the same job, profile order,
submitted judgments, and final outcomes. Raw historical inputs and rule metadata
remain private research data.

`generated_at` records retrieval; `revealed_at` remains NULL until browser display
acknowledgment. The existing monotonic visible-page timer uses five-second, hide,
and final checkpoints with cumulative MAX merging, excluding hidden time and user-action
waits; background timing-checkpoint requests keep the timer running. Abrupt termination can lose time since the last successful checkpoint.
Ending a visit records final duration, `continued_at`, and session ending atomically.
Starting another visit instead preserves unfinished records and NULL completion.

SQLite remains `backend/outputs/research.sqlite3`. Suggested research exports include
the Stage 3 tables, common Stage 4 tables, and `stage4_historical_inputs.jsonl` only
for historical data. Export tooling remains unimplemented. Exclude technical
credentials/receipts. Join participant judgments to outcomes by BOTH case and profile ID,
then cases → sessions → participants. Historical inputs can be joined optionally;
other methods will not need historical rows. Aggregate detail rows before joining
other one-to-many tables to avoid inflating participant/session counts.

### Existing-database migration

On storage initialization, legacy tables are rebuilt in one SQLite transaction.
Historical sources are extracted into the dedicated input table; old derived case
values are validated against source values and the saved Stage 2 rule before removal.
Existing revealed outcomes become common results with `decision_basis=historical`
and a separate nullable `applied_rule`. Redundant `method_decision` is removed only
after verifying agreement with the historical input. Inconsistent legacy records
cause rollback with an error, not automatic repair. Foreign keys are checked before
commit, and repeated initialization does not rerun the conversion.

Profiles, judgments, timestamps, session endings, technical retries, and existing
case version labels are preserved. Ended sessions remain ended. New cases use
`configurable_entry_v1`; old labels describe their original collection version, not the current
physical schema. Stop the old Flask process before restarting with this revision.
One case per session remains the interface restriction. Stage 5 is defined in section 12.

The combined `/api/action` operation is `submit_and_reveal`; Stage 3 fields and
measurement meanings are unchanged. Stage 3 submission timing is saved before the
result-review timer resets. `revealed_at` still requires browser display acknowledgment.
Legacy `submit_judgments` and `reveal_outcomes` actions remain compatible with saved
retry receipts. Resuming an old submitted visit retrieves results automatically.

## 12. Stage 5 — perceived fairness on the results page

The results and survey share one page. Differences between submitted judgments
and revealed outcomes receive a neutral label; they are not scored as incorrect or
unfair. Participants supply a required 1–10 rating, group-level selections plus a
reason, and individual comparisons or a reason for no comparison/uncertainty.

### Research tables

`stage5_fairness_feedback` has one row per displayed survey:

| Field | Type | Meaning |
| --- | --- | --- |
| case_id | TEXT PK/FK | References stage4_outcome_revelation; links through case/session/participant. |
| started_at | TEXT NOT NULL | First browser acknowledgment of the page containing survey version stage5_v1; not proof of reading below the fold. |
| submitted_at | TEXT nullable | UTC final feedback submission. |
| fairness_rating | INTEGER nullable | Participant rating 1–10; no default answer. |
| group_selections_json | TEXT/JSON nullable | Array of selected option codes, for example ["age_discrimination", "other"]. NULL before submission. |
| group_reason | TEXT nullable | Required overall-distribution explanation after submission. |
| other_group_view | TEXT nullable | Required only when other is selected; otherwise NULL. |
| individual_comparison | TEXT nullable | yes, no, or unsure. |
| individual_reason | TEXT nullable | Required for no/unsure; NULL for yes. |

All answer fields remain NULL before final submission. `group_selections_json`
is a nullable TEXT/JSON array in `stage5_fairness_feedback`. It stores the selected
option codes in sorted order; this order has no research meaning. Codes:
`age_discrimination`, `gender_discrimination`, `experience_overemphasis`,
`education_overemphasis`, `skills_overemphasis`, `other`, `none`, `unsure`.
They are participant opinions, not automated findings. Select at least one;
none/unsure are each exclusive of all other choices.

`stage5_applicant_comparisons` contains:

| Field | Type | Meaning |
| --- | --- | --- |
| case_id | TEXT FK | Parent feedback row. |
| comparison_number | INTEGER | 1–9; primary key with case_id, submitted order. |
| rejected_profile_id | TEXT | The participant considers this unsuccessful applicant more suitable. |
| passed_profile_id | TEXT | Successful applicant used as the comparison. |
| reason | TEXT | Required explanation for this specific pair. |

Each profile reference has a composite foreign key with case_id to
stage4_applicant_outcomes. The pair is unique within a case. Backend checks actual
reject/pass membership. Repeated use of an applicant across different pairs is
allowed. Choosing yes requires 1–9 distinct pairs; no/unsure stores no pair rows.
Text is trimmed, required where applicable, and limited to 5,000 characters each.
Hidden branches are discarded at submission, not recorded as observations.

Example projection: for case-alt-01 from section 11, a feedback row can have rating
6, group selection skills_overemphasis, group_reason describing the participant's
reasoning, individual_comparison yes, and NULL individual_reason. Comparison rows
(1, profile-A, profile-B, reason for this pair) and (2, profile-A, profile-C, another
reason) share this case ID. This is a one-to-many relation; ratings must not be
counted multiple times when joining comparisons. No source/outcome fields are copied.

### API, timing and recovery

`submit_fairness` extends `/api/action` with fairness_rating, group_selections,
group_reason, other_group_view, individual_comparison, individual_reason, and
comparisons (objects containing rejected_profile_id, passed_profile_id, reason).
Use existing case/tab/revision/presentation/action identifiers and cumulative
visible duration, plus survey_version=stage5_v1. A matching display acknowledgment
first creates the unanswered feedback row and sets technical survey_ack; earlier
result-only display acknowledgment does not count as survey presentation.

Submission atomically writes answers and comparisons, finalizes Stage 4 shared-page
duration/continued_at, and ends the session. Existing authenticated action receipts
make retries idempotent; unauthorized, stale or post-finalization edits are rejected.
The response includes feedback_saved=true. Legacy end_session is retained only for
older clients that have not acknowledged the survey; the new UI only submits feedback.

Stage 4 duration_ms is the combined visible results-and-survey page duration, not
pure survey time. Stage 5 has no duplicate duration. Existing revealed_at and duration
are retained on old open cases; started_at is new when their survey first appears.
Drafts use research_fairness_<case_id> in tab sessionStorage, survive reload and request
failure, and are removed after success. They are not research records. Existing
five-second/hide/final checkpoints and abrupt-termination limits continue to apply.

Tables are added to backend/outputs/research.sqlite3; completed old visits are not
reopened or backfilled. New cases use configurable_entry_v1; prior case labels stay unchanged.
Suggested exports add one file per Stage 5 table and exclude technical credentials,
receipts and browser drafts. This document is now named `DATA_STORAGE.md`; earlier links to `STAGE_1_2_DATA_STORAGE.md` are obsolete.

Stage 5 storage simplification: overall selections are now stored inside the feedback
row, not a separate table. Initialization transactionally merges legacy
stage5_group_selections rows into group_selections_json and drops the old table.
Existing choices and all other feedback fields are preserved; unanswered records
remain NULL. The API still accepts group_selections as an array. In Python, use
json.loads(row["group_selections_json"]) for submitted feedback. Stage 5 now has
two research tables: stage5_fairness_feedback and stage5_applicant_comparisons.
