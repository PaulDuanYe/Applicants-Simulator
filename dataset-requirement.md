# Output dataset and product structure

This describes the current implemented Product application, verified from its source on 2026-09-14. It does not modify the schema or create new research variables. `data-structure.md` describes input JSON; this document describes collected outputs.

## 1. Product inventory

**Maintained product: 6 folders and 36 files**, excluding the Product root itself. Counts include this document, hidden `.gitignore`, source JSON, tests and documentation. Dependencies, Python caches, runtime outputs and logs are excluded.

**Local disk snapshot:** 162 folders and 1257 files beneath Product, including `.venv`, caches, outputs and logs. These totals change after installs/runs; they are not the project source size. No database contents were read for this inventory.

```text
Product/
  .gitignore
  FIVE_STAGE_FRAMEWORK.md
  README.md
  STAGE_1_2_DATA_STORAGE.md
  applicants.json
  backend/
    app.py
    dataset.py
    experiment.py
    fairness.py
    outcomes/
      __init__.py
      historical.py
      rules.py
    requirements.txt
    storage.py
    tests/
      test_app.py
      test_dataset.py
      test_experiment.py
      test_fairness.py
      test_storage_migration.py
  data-structure.md
  dataset.md
  frontend/
    index.html
    src/
      api.js
      app.js
      competition.js
      entry.js
      fairness.js
      outcomes.js
      timing.js
      views.js
    styles.css
    tests/
      api.test.mjs
      timing.test.mjs
  jobs.json
  start.command
  start.ps1
```

Generated/installed paths, excluded from the maintained tree:

- `.venv/`: Python interpreter and installed dependencies.
- `backend/outputs/`: persistent SQLite output, plus any SQLite sidecar files.
- `startup-logs/`: per-launch stdout/stderr logs.
- `__pycache__/` beneath Python folders: bytecode caches.

### File responsibilities

| File | Component and responsibility |
| --- | --- |
| [.gitignore](.gitignore) | Shared — excludes environment, Python caches, startup logs and runtime outputs. |
| [FIVE_STAGE_FRAMEWORK.md](FIVE_STAGE_FRAMEWORK.md) | Shared — five-stage research framework and variable meanings. |
| [README.md](README.md) | Shared — current installation, workflow, API overview and verification guide. |
| [STAGE_1_2_DATA_STORAGE.md](STAGE_1_2_DATA_STORAGE.md) | Shared — detailed recording design and revision history for Stages 1–5. |
| [applicants.json](applicants.json) | Backend input — 50 fictional applicant records; read by dataset.load_dataset(). |
| [backend/app.py](backend/app.py) | Backend — create_app(); Flask routes, source validation, lazy experiment/storage initialization, JSON errors. |
| [backend/dataset.py](backend/dataset.py) | Backend — Dataset, DatasetValidationError, load_dataset(); read/validate/index source files by ID and job/decision. |
| [backend/experiment.py](backend/experiment.py) | Backend — Experiment.action()/me(), authentication, case ownership/view, profile/group preparation, stage actions and timing; uses dataset, Storage, outcomes and fairness. |
| [backend/fairness.py](backend/fairness.py) | Backend — validate_feedback(); validates rating, group selections, text and applicant pairs; called by experiment.py. |
| [backend/outcomes/__init__.py](backend/outcomes/__init__.py) | Backend — generate_outcomes() dispatch; historical works, other known methods fail explicitly. |
| [backend/outcomes/historical.py](backend/outcomes/historical.py) | Backend — generate_historical(); validates and returns frozen historical inputs by profile ID. |
| [backend/outcomes/rules.py](backend/outcomes/rules.py) | Backend — resolve_case_outcomes(); separate alternative-job override and six-person/3–3 checks. |
| [backend/requirements.txt](backend/requirements.txt) | Backend setup — Flask dependency for pip. |
| [backend/storage.py](backend/storage.py) | Backend — SCHEMA, Storage, transaction(), legacy migrations; SQLite constraints and atomic writes. |
| [backend/tests/test_app.py](backend/tests/test_app.py) | Backend verification — Flask page/assets/health and source initialization. |
| [backend/tests/test_dataset.py](backend/tests/test_dataset.py) | Backend verification — source schema, counts, grouping and source preservation. |
| [backend/tests/test_experiment.py](backend/tests/test_experiment.py) | Backend verification — identities, stages 1–4, retries, ownership, outcomes and persistence. |
| [backend/tests/test_fairness.py](backend/tests/test_fairness.py) | Backend verification — Stage 5 validation/submission, permissions and group-selection merge. |
| [backend/tests/test_storage_migration.py](backend/tests/test_storage_migration.py) | Backend verification — legacy schema conversion, preserved observations and rollback. |
| [data-structure.md](data-structure.md) | Shared — input dataset fields and conventions. |
| [dataset.md](dataset.md) | Shared — current output schema and product inventory (this document). |
| [frontend/index.html](frontend/index.html) | Frontend — document shell, screen/status/recovery containers; loads CSS and app.js. |
| [frontend/src/api.js](frontend/src/api.js) | Frontend — request(), ApiError, getHealth(); authenticated JSON HTTP, timeout and error handling. |
| [frontend/src/app.js](frontend/src/app.js) | Frontend — controller: identity/session recovery, state rendering, serialized actions, pending retries, busy controls and display/timing acknowledgments. |
| [frontend/src/competition.js](frontend/src/competition.js) | Frontend — renderCompetition(), judgmentsReady(); six judgments, 3/3 selection check and local draft recovery. |
| [frontend/src/entry.js](frontend/src/entry.js) | Frontend — intro(), codeEntry(); first-time/returning participant entry and code selection. |
| [frontend/src/fairness.js](frontend/src/fairness.js) | Frontend — renderFairness(); rating, group choices, dynamic comparison pairs, reasons, draft storage and submit payload. |
| [frontend/src/outcomes.js](frontend/src/outcomes.js) | Frontend — renderOutcomes(); saved job/profiles, predictions versus outcomes, mismatch labels; calls renderFairness(). |
| [frontend/src/timing.js](frontend/src/timing.js) | Frontend — VisibleTimer; monotonic cumulative visible duration and pause/resume/reset. |
| [frontend/src/views.js](frontend/src/views.js) | Frontend — element(), button(), profileCard(), renderProfile(), renderJobs(); safe text rendering and stage 1–2 UI. |
| [frontend/styles.css](frontend/styles.css) | Frontend — responsive layout, cards, typography, form hierarchy and focus/selection states. |
| [frontend/tests/api.test.mjs](frontend/tests/api.test.mjs) | Frontend verification — requests, credentials, JSON, keepalive and failures (Node). |
| [frontend/tests/timing.test.mjs](frontend/tests/timing.test.mjs) | Frontend verification — visibility, pauses and restored timing baseline (Node). |
| [jobs.json](jobs.json) | Backend input — three job records; read by dataset.load_dataset(). |
| [start.command](start.command) | Shared macOS launcher — checks the macOS environment and port, starts Flask, opens the browser, records logs and cleans up its child process. |
| [start.ps1](start.ps1) | Shared launcher — validates environment, starts Flask, opens browser, reports logs, cleans up its child process. |

## 2. Output format and identity

The current schema has **17 tables: 14 research tables and 3 technical tables**. SQLite output is `backend/outputs/research.sqlite3`, initialized on the first participant API request. `/api/health` checks source loading and does not initialize research storage. JSON/CSV exports are not automatically generated.

IDs: participant_id identifies a reusable research participant; participant_code recovers that identity. A session_id identifies a visit, and case_id identifies a scenario within it. profile_id and job_id refer to fictional source records, not research participants. New participant/session/case IDs are UUID strings. Composite IDs identify repeated views, positions and comparison pairs.

```text
participant → sessions → cases
  case → Stage 1 summary → profile views
       → Stage 2 selection → offered jobs
       → Stage 3 assessment → six applicant judgments
       → Stage 4 historical inputs (linked to Stage 3 applicants)
       → Stage 4 revelation → six final outcomes
       → Stage 5 feedback (group selections embedded) → comparison pairs
```

TEXT timestamps use UTC ISO 8601 (typically milliseconds and Z). Durations are nonnegative INTEGER milliseconds. Source/group preparation and retrieval use server time; display/submission events use validated browser timestamps. NULL means absent/not completed, not zero. Internal results use pass/reject; participant labels are 通过/不通过. Screening pass is not a job offer.

Snapshots use TEXT containing JSON: profile snapshots contain job_related_attributes (education, experience_years, skills) and protected_attributes (gender, age, marital_status; older snapshots may omit marital_status); job snapshots contain title and description. Source results (decisions and scores), source job metadata and provenance are not in displayed profile snapshots.

## 3. Table and field reference

The tables below list physical SQLite types and keys. “Required” follows declared NOT NULL plus logical primary-key requirements; API checks additionally enforce valid values and completed-stage consistency. FK targets are listed after each table.

### `participants`

One reusable research identity. participant_code is unique; participant_id is a UUID.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `participant_id` | TEXT | PK 1 | — | Research identity link. |
| `participant_code` | TEXT | Required | — | Reusable participant-entered code; not a profile ID. |
| `created_at` | TEXT | Required | — | Server creation time. |
### `sessions`

Many visits per participant. NULL ended_at means open; starting a new visit closes the previous open one.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `session_id` | TEXT | PK 1 | — | Visit identity link. |
| `participant_id` | TEXT | Required | — | Research identity link. |
| `started_at` | TEXT | Required | — | Stage/session start as described above. |
| `ended_at` | TEXT | Nullable | — | End time; NULL while unfinished. |

Foreign keys: `participant_id` → `participants.primary key` (FK group 0).

### `cases`

Scenario instances within a session; unique (session_id,case_number), case_number > 0. Current UI creates one per session. New schema_version=stage1_5_v1, timing_policy=visible_page.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `case_id` | TEXT | PK 1 | — | Scenario link across stages. |
| `session_id` | TEXT | Required | — | Visit identity link. |
| `case_number` | INTEGER | Required | — | Position of case within visit. |
| `started_at` | TEXT | Required | — | Stage/session start as described above. |
| `schema_version` | TEXT | Required | — | Collection-version label, preserved for old cases. |
| `timing_policy` | TEXT | Required | — | visible_page. |

Foreign keys: `session_id` → `sessions.primary key` (FK group 0).

### `stage1_profile_selection`

One summary per case reaching acknowledged Stage 1. refresh_count is x1; confirmation duration sums all recorded profile-view durations.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `case_id` | TEXT | PK 1 | — | Scenario link across stages. |
| `started_at` | TEXT | Required | — | Stage/session start as described above. |
| `confirmed_at` | TEXT | Nullable | — | Profile confirmation time. |
| `refresh_count` | INTEGER | Required | 0 | Number of profile refreshes (x1). |
| `confirmed_profile_id` | TEXT | Nullable | — | Chosen source applicant. |
| `confirmation_duration_ms` | INTEGER | Nullable | — | Sum of profile review durations at confirmation. |

Foreign keys: `case_id` → `cases.primary key` (FK group 0).

### `stage1_profile_views`

One row per actually acknowledged view. view_number starts at 1; refresh creates the next number only on display. ended_by is refresh/confirm. Reload does not increment x1.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `case_id` | TEXT | PK 1 | — | Scenario link across stages. |
| `view_number` | INTEGER | PK 2 | — | Profile display sequence. |
| `profile_id` | TEXT | Required | — | Source applicant identifier. |
| `displayed_profile_json` | TEXT | Required | — | Displayed qualifications/demographic JSON snapshot. |
| `displayed_at` | TEXT | Required | — | Browser display acknowledgment time. |
| `ended_at` | TEXT | Nullable | — | End time; NULL while unfinished. |
| `duration_ms` | INTEGER | Required | — | Cumulative visible milliseconds; see stage timing definition. |
| `ended_by` | TEXT | Nullable | — | refresh or confirm. |

Foreign keys: `case_id` → `stage1_profile_selection.primary key` (FK group 0).

### `stage2_job_selection`

One acknowledged job-selection record per case. selected_job_id is x2; NULL until confirmed.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `case_id` | TEXT | PK 1 | — | Scenario link across stages. |
| `started_at` | TEXT | Required | — | Stage/session start as described above. |
| `submitted_at` | TEXT | Nullable | — | Final submission time; NULL until submitted. |
| `original_job_id` | TEXT | Required | — | Selected profile original job. |
| `selected_job_id` | TEXT | Nullable | — | Confirmed job selection (x2). |
| `decision_duration_ms` | INTEGER | Required | — | Visible job-choice duration. |

Foreign keys: `case_id` → `cases.primary key` (FK group 0).

### `stage2_job_options`

Three acknowledged options, positions 1–3, unique (case_id,job_id). Snapshot contains title and description.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `case_id` | TEXT | PK 1 | — | Scenario link across stages. |
| `display_position` | INTEGER | PK 2 | — | Saved display order. |
| `job_id` | TEXT | Required | — | Source job identifier. |
| `displayed_job_json` | TEXT | Required | — | JSON title/description snapshot. |

Foreign keys: `case_id` → `stage2_job_selection.primary key` (FK group 0).

### `stage3_competition_assessment`

One prepared six-person group. prepared_at is preparation, started_at is display acknowledgment; submitted_at finalizes all judgments.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `case_id` | TEXT | PK 1 | — | Scenario link across stages. |
| `selected_job_id` | TEXT | Required | — | Confirmed job selection (x2). |
| `displayed_job_json` | TEXT | Required | — | JSON title/description snapshot. |
| `prepared_at` | TEXT | Required | — | Server group-preparation time. |
| `started_at` | TEXT | Nullable | — | Stage/session start as described above. |
| `submitted_at` | TEXT | Nullable | — | Final submission time; NULL until submitted. |
| `judgment_duration_ms` | INTEGER | Required | 0 | Visible six-applicant review duration. |

Foreign keys: `case_id` → `cases.primary key` (FK group 0).

### `stage3_applicants`

Six rows: participant at position 1 and five competitors at positions 2–6. Unique (case_id,profile_id). participant_judgment (y1) is NULL until all six commit; current protocol requires 3 pass/3 reject judgments. No outcome fields live here.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `case_id` | TEXT | PK 1 | — | Scenario link across stages. |
| `display_position` | INTEGER | PK 2 | — | Saved display order. |
| `profile_id` | TEXT | Required | — | Source applicant identifier. |
| `applicant_role` | TEXT | Required | — | participant or competitor. |
| `displayed_profile_json` | TEXT | Required | — | Displayed qualifications/demographic JSON snapshot. |
| `participant_judgment` | TEXT | Nullable | — | Submitted pass/reject opinion. |

Foreign keys: `case_id` → `stage3_competition_assessment.primary key` (FK group 0).

### `stage4_historical_inputs`

Historical-only frozen input per case/profile. Captured alongside group preparation for reproducibility; source_decision is pass/reject for the original job. Not a generated result or evidence of display.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `case_id` | TEXT | PK 1 | — | Scenario link across stages. |
| `profile_id` | TEXT | PK 2 | — | Source applicant identifier. |
| `source_decision` | TEXT | Required | — | Historical-only frozen pass/reject input. |

Foreign keys: `case_id` → `stage3_applicants.case_id` (FK group 0); `profile_id` → `stage3_applicants.profile_id` (FK group 0).

### `stage4_outcome_revelation`

One retrieved result set. outcome_method is x3 (historical only implemented). generated_at is retrieval, revealed_at is first display acknowledgment. duration_ms is combined results-and-survey visible time; continued_at finalizes review.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `case_id` | TEXT | PK 1 | — | Scenario link across stages. |
| `outcome_method` | TEXT | Required | — | Method used for this case. |
| `generated_at` | TEXT | Required | — | Server retrieval/persistence time. |
| `revealed_at` | TEXT | Nullable | — | First acknowledged result display. |
| `continued_at` | TEXT | Nullable | — | Explicit result-review completion. |
| `duration_ms` | INTEGER | Required | 0 | Cumulative visible milliseconds; see stage timing definition. |

Foreign keys: `case_id` → `stage3_competition_assessment.primary key` (FK group 0).

### `stage4_applicant_outcomes`

Six final results. revealed_decision is pass/reject. decision_basis names historical/llm/matrix/random_method (currently historical), never source_decision. applied_rule is NULL or alternative_job_rejection. Composite FK (case_id,profile_id) references Stage 3.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `case_id` | TEXT | PK 1 | — | Scenario link across stages. |
| `profile_id` | TEXT | PK 2 | — | Source applicant identifier. |
| `revealed_decision` | TEXT | Required | — | Final pass/reject outcome. |
| `decision_basis` | TEXT | Required | — | Method identifier. |
| `applied_rule` | TEXT | Nullable | — | NULL or alternative_job_rejection. |

Foreign keys: `case_id` → `stage3_applicants.case_id` (FK group 0); `profile_id` → `stage3_applicants.profile_id` (FK group 0); `case_id` → `stage4_outcome_revelation.primary key` (FK group 1).

### `stage5_fairness_feedback`

One acknowledged survey per case. Unsubmitted answer fields stay NULL. fairness_rating is integer 1–10. group_selections_json is a sorted JSON array of codes; group_reason required. other_group_view required only for other. individual_comparison=yes/no/unsure; individual_reason required for no/unsure, NULL for yes.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `case_id` | TEXT | PK 1 | — | Scenario link across stages. |
| `started_at` | TEXT | Required | — | Stage/session start as described above. |
| `submitted_at` | TEXT | Nullable | — | Final submission time; NULL until submitted. |
| `fairness_rating` | INTEGER | Nullable | — | 1–10 fairness response. |
| `group_selections_json` | TEXT | Nullable | — | JSON array of selected group-opinion codes. |
| `group_reason` | TEXT | Nullable | — | Explanation for group opinion. |
| `other_group_view` | TEXT | Nullable | — | Conditional other-option explanation. |
| `individual_comparison` | TEXT | Nullable | — | yes/no/unsure. |
| `individual_reason` | TEXT | Nullable | — | Reason for no/unsure. |

Foreign keys: `case_id` → `stage4_outcome_revelation.primary key` (FK group 0).

### `stage5_applicant_comparisons`

0 rows for no/unsure; 1–9 for yes. Unique pair per case; one applicant may appear in several distinct pairs. Both composite profile FKs reference Stage 4 results. Backend requires rejected_profile_id to be reject and passed_profile_id to be pass. Each reason is required.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `case_id` | TEXT | PK 1 | — | Scenario link across stages. |
| `comparison_number` | INTEGER | PK 2 | — | Submitted comparison sequence. |
| `rejected_profile_id` | TEXT | Required | — | Unsuccessful applicant considered more suitable. |
| `passed_profile_id` | TEXT | Required | — | Successful applicant used for comparison. |
| `reason` | TEXT | Required | — | Reason for this pair. |

Foreign keys: `case_id` → `stage4_applicant_outcomes.case_id` (FK group 0); `passed_profile_id` → `stage4_applicant_outcomes.profile_id` (FK group 0); `case_id` → `stage4_applicant_outcomes.case_id` (FK group 1); `rejected_profile_id` → `stage4_applicant_outcomes.profile_id` (FK group 1); `case_id` → `stage5_fairness_feedback.primary key` (FK group 2).

### `technical_credentials`

Private authentication token hashes linked to participants. Exclude from research exports.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `token_hash` | TEXT | PK 1 | — | SHA-256 browser credential hash. |
| `participant_id` | TEXT | Required | — | Research identity link. |

Foreign keys: `participant_id` → `participants.primary key` (FK group 0).

### `technical_receipts`

Private persistent exact-request retry records keyed by scope/action_id; identity receipts can contain credentials. Exclude the entire table from research exports.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `scope` | TEXT | PK 1 | — | Receipt identity or participant scope. |
| `action_id` | TEXT | PK 2 | — | UUID idempotency key. |
| `request_json` | TEXT | Required | — | Exact original action JSON. |
| `response_json` | TEXT | Required | — | Saved response JSON, potentially credential-bearing. |
### `technical_case_state`

Private JSON runtime state: stage/phase, revision, writer tab, presentation, acknowledgment flags, timing baseline and prepared display data. Not an additional research observation.

| Field | Type | Required / key | Default | Meaning |
| --- | --- | --- | --- | --- |
| `case_id` | TEXT | PK 1 | — | Scenario link across stages. |
| `state_json` | TEXT | Required | — | Private runtime JSON state. |

Foreign keys: `case_id` → `cases.primary key` (FK group 0).

## 4. Stage 5 selections and examples

`group_selections_json` contains one or more unique codes, stored in sorted order.
The order is not a preference/ranking. Codes: age_discrimination,
gender_discrimination, experience_overemphasis, education_overemphasis,
skills_overemphasis, other, none, unsure. none and unsure are each exclusive of all
other choices. These are participant opinions, never system findings. The old
stage5_group_selections table is merged into feedback during initialization and removed.

Text answers are trimmed and limited to 5,000 characters; required answers cannot be
blank. For individual_comparison=yes there are 1–9 distinct reject/pass pairs with
separate reasons. For no/unsure, comparison rows are absent and individual_reason is
required. Hidden branch values are discarded. All answers commit together.

Illustrative submitted feedback projection (IDs and text below are examples, not real
participant data; omitted columns remain as defined in the full field table):

```json
{
  "case_id": "00000000-0000-4000-8000-000000000001",
  "fairness_rating": 6,
  "group_selections_json": "[\"experience_overemphasis\",\"other\"]",
  "group_reason": "我认为经验在这次结果中占的比重太大。",
  "other_group_view": "我也关注技能与岗位要求是否对应。",
  "individual_comparison": "yes",
  "individual_reason": null
}
```

For this same case, comparison 1 may reference rejected profile R and passed profile
P with its own reason; comparison 2 may reference R and another passed profile Q.
R/P/Q must already be actual Stage 4 profile IDs with matching reject/pass results.
The same source profile can occur in other cases, so always join using case_id too.

## 5. Execution, recording and recovery

1. Frontend index → app controller → entry UI → api.request → Flask /api/action.
   Register/login establish identity; new_session creates the visit and one case.
2. Profile preparation selects a source record; display acknowledgment records the
   actual view. Refresh closes it, increments x1, and prepares another. Confirmation
   locks the profile and saves total viewing duration.
3. Job options are shuffled once; acknowledgment records their saved order/content.
   Job confirmation saves x2 and prepares the six-person group. Historical source
   inputs are frozen in the Stage 4-specific input table, never Stage 3 fields.
4. Stage 3 display starts group-review timing. submit_and_reveal validates/saves all
   judgments, calls generate_outcomes(historical, applicants, method_data=inputs),
   then resolves the alternative-job rule and checks final 3/3 balance. It creates
   Stage 4 results atomically. Results are not sent before this action succeeds.
5. Results render with the same snapshots/order and judgments. display with
   survey_version=stage5_v1 sets first revealed_at (only if absent) and first survey
   started_at. Presence below the fold does not prove the participant read it.
6. submit_fairness validates and stores feedback/group JSON/pairs, saves shared-page
   duration and continued_at, and ends the session atomically. No Stage 5 duplicate
   duration exists. Old result-only clients retain limited end_session compatibility.

The current participant calls use submit_and_reveal and submit_fairness; legacy
submit_judgments/reveal_outcomes remain for stored retry compatibility. claim resumes
and makes the new tab the sole writer. All writes validate ownership/revision and
use transactions; exact action receipts prevent duplicate observations.

Visible timing pauses for hidden pages and action waits, checkpoints every five
seconds and on hiding, and merges cumulative values rather than adding retries.
Abrupt termination may lose the last unacknowledged interval. Page visibility is not
attention. Starting a new visit keeps partial old records; closing a browser does
not itself mean a completed session. Ended sessions remain ended.

Browser localStorage retains identity credentials; sessionStorage retains pending
requests and profile-judgment/survey drafts. Drafts are not submitted research data.
Technical receipt payloads can contain tokens and answers: exclude entire technical
tables from research exports. Read-only analysis should target research tables.

## 6. Reading outputs in Python

From Product/, after research.sqlite3 has been created:

```python
from pathlib import Path
from contextlib import closing
import json
import sqlite3

path = Path("backend/outputs/research.sqlite3").resolve()
with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
    db.row_factory = sqlite3.Row
    rows = db.execute("""
        SELECT p.participant_id, s.session_id, f.*
        FROM stage5_fairness_feedback f
        JOIN cases c USING(case_id)
        JOIN sessions s USING(session_id)
        JOIN participants p USING(participant_id)
        WHERE f.submitted_at IS NOT NULL
    """).fetchall()
    feedback = [dict(row) for row in rows]
    for row in feedback:
        row["group_selections"] = json.loads(row["group_selections_json"])
```

Predictions and outcomes: join stage3_applicants to stage4_applicant_outcomes on
BOTH case_id and profile_id. Historical inputs are optional method-specific joins.
Compare applicant pairs through the two corresponding Stage 4 aliases. Aggregate
one-to-many views/pairs before joining case-level ratings, or ratings will be counted
multiple times. This is an access example, not a prescribed analysis methodology.

The schema above is read from backend/storage.py. That module is authoritative for
physical columns; experiment.py and fairness.py enforce lifecycle and submission
rules. Changes to existing schema are transactional and foreign-key checked; legacy
inconsistencies trigger rollback rather than silent repair. Backups, exports and
analytics remain separate operational tasks, not automatic features of this demo.
