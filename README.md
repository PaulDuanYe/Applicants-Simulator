# Applicant research simulator — Stages 1–5

A Python Flask application with a Chinese participant interface. Participants choose
a profile and job, judge six applicants, view historical screening outcomes, and
submit perceived-fairness feedback. One Flask process serves both frontend and API.
Only the applicant perspective is implemented; no HR interface, objective fairness
verdict, scoring algorithm, or analytics/export pipeline is implemented.

## Current product versus target working direction

The five-stage flow below is the runnable product and previous research design, not
the intended final framework. The target working direction studies how algorithmic
fairness conditions or outcome characteristics influence perceived fairness: assign
a profile, present competitors for the same position, generate/reveal outcomes using
relevant attributes and the designed fairness matrix/condition, then collect feedback.
There is no pre-outcome prediction or independent should-pass task in that target.

This direction is not implemented or finalized. Matrix/algorithm definitions,
assignment rules, competitor counts, outcome quotas and feedback measures remain
unspecified. The current 6-person/3–3 setup and survey are not automatic target
requirements. Legacy X1/X2/Y1 behavior and records remain in the product, but are
excluded from the target framework; documentation changes do not remove them.
See [FIVE_STAGE_FRAMEWORK.md](FIVE_STAGE_FRAMEWORK.md) for the current behavior and
separate target description, and [AGENTS.md](../AGENTS.md) for shared project context.

## Start on Windows

One-time setup, from `Product/`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Use Python 3.10 or later. Then, from the repository root:

```powershell
.\Product\start.ps1
```

If Windows blocks scripts, this per-launch command does not change the saved policy:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Product\start.ps1
```

The PowerShell 5.1 launcher resolves paths from its own location, checks the existing
virtual environment and port 5000, starts Flask hidden, waits up to 15 seconds for
health, and opens the browser. Keep the launcher open; Ctrl+C stops only its child.
Separate stdout/stderr logs are in `startup-logs/`. Installation remains explicit.
Restart the backend after Python changes; refresh the page after frontend changes.

For manual startup from `Product/`:

```powershell
.\.venv\Scripts\python.exe backend/app.py
```

Open [the local simulator](http://127.0.0.1:5000/). On macOS/Linux use
`.venv/bin/python`. Flask binds to localhost with debug disabled. Do not open
`index.html` directly. `/static/` maps to `frontend/`, so no physical static folder
or separate frontend server is required.

## Start on macOS

Create a macOS environment from `Product/` (a copied Windows `.venv` will not work):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
```

From the repository root, run:

```bash
bash Product/start.command
```

For Finder double-click startup, first run `chmod +x Product/start.command`.
The macOS launcher is implemented and syntax-checked; execution on macOS remains
unverified in this project review. It resolves paths from its own location, checks port 5000 and Flask, starts
one backend for both the UI and API, waits up to 15 seconds, then opens the browser.
Keep Terminal open; Ctrl+C stops only its own backend. Logs go to `startup-logs/`.
If port 5000 is occupied, check for an existing server or macOS AirPlay Receiver;
the launcher does not change system settings or stop other processes.

## Researcher configuration

Edit [backend/config.py](backend/config.py), then restart the backend:

```python
PROFILE_REFRESH_ENABLED = False
JOB_SELECTION_ENABLED = False
```

These independent switches default off and are not participant controls. Refresh,
when enabled, samples another Software Engineer profile. Job selection, when enabled,
offers Software Engineer, Financial Analyst and Graphic Designer in saved shuffled
order. Both pages remain separate under every combination.

Settings are saved per case: restarting or editing configuration never changes an
existing case. Start a new session to use new settings. Older cases without a
configuration record retain their legacy behavior. Later stages remain unchanged;
this is an incremental transition, not the completed target research direction.

## Participant flow

1. Click “开始”; generate and save a participant code, or enter an existing code.
   Code creation alone does not start a session or research timing.
2. Start or resume participation. “重新开始” closes an open visit but keeps its records.
   The current interface creates one case per session.
3. Read your assigned Software Engineer profile, then its job description on a
   separate page. Optional researcher settings enable profile refresh and three-job
   selection. Continuing locks the profile/job.
4. Judge all six applicants: three pass and three reject. “确认并查看结果” saves
   judgments and retrieves outcomes in one transaction, then opens results directly.
5. On the shared results/survey page, review neutral mismatch labels, give a 1–10
   fairness rating, select overall opinions and explain them, and provide individual
   comparisons or explain no comparison/uncertainty. Each selected comparison has
   its own reason. “提交反馈，结束本次参与” saves feedback and ends the visit.

Historical inputs are fixed fictional dataset values, not verified hiring records.
An alternative-job choice automatically rejects the participant; final outcomes
still contain exactly three pass and three reject results. Other methods (`llm`,
`matrix`, `random_method`) explicitly raise not-implemented errors.

## Data and product documentation

- [DATA_STORAGE.md](DATA_STORAGE.md): current output schema, recording rules and
  legacy data compatibility; not a schema for the unimplemented target direction.
- [dataset-requirement.md](dataset-requirement.md): supplementary output/inventory
  reference. Its embedded old filenames and inventory snapshot may be stale; use
  the current files and DATA_STORAGE.md for the reviewed schema and links.
- [FIVE_STAGE_FRAMEWORK.md](FIVE_STAGE_FRAMEWORK.md): current five-stage product
  behavior/previous design and a separate provisional target direction.
- [data-structure.md](data-structure.md): **input** jobs/applicants schema, distinct from outputs.

Inputs are `jobs.json` and `applicants.json`: 3 jobs and 50 profiles: Software Engineer has
15 pass and 15 reject; each other job has 5 pass and 5 reject. All applicants have
marital status and nested `results.decision` / `results.score`. Scores remain source-only
illustrative values; marital status is displayed on profile cards. `backend.dataset.load_dataset()` validates and indexes them without
rewriting files. Relative data paths resolve against Product, not the shell directory.

Outputs persist in `backend/outputs/research.sqlite3`. Storage is initialized lazily
on the first participant API request, not by `/api/health`. Schema migrations preserve
observations and fail/roll back on inconsistent legacy data. In particular, Stage 3
has no outcome fields; Stage 4 historical inputs are separate; Stage 5 group choices
are in `stage5_fairness_feedback.group_selections_json`, not a separate table.
New case version is `configurable_entry_v1`; existing labels are preserved. Ended visits are not
reopened. Stop old backend processes before initializing an updated schema.

Do not include technical credentials or action receipts in research exports. Browser
drafts are local recovery state, not submitted research data. User-action waits pause the timer; background timing-checkpoint requests currently
do not. The combined results and survey duration is stored only in Stage 4; it is not survey-only time. Visible
page time does not measure attention, and abrupt closure may lose the last checkpoint.

## API and modules

`frontend/src/app.js` controls rendering and serialized requests. `backend/app.py`
serves `/`, `/static/*`, `GET /api/health`, `GET /api/me`, and `POST /api/action`.
`experiment.py` coordinates sampling, ownership, progression, timing and persistence;
`storage.py` owns the SQLite schema/migrations; `outcomes/` dispatches methods and
applies scenario rules; `fairness.py` validates opinions without interpreting fairness.

Current action operations: register, login, new_session, claim, display, timing,
refresh, confirm_profile, confirm_job, submit_and_reveal, submit_fairness.
Legacy submit_judgments/reveal_outcomes and end_session remain for compatibility;
the current UI uses combined judgment submission and final feedback submission.
Authenticated case actions include case/tab/revision/presentation identifiers and
an action UUID. Exact retries reuse the same body and UUID. Survey actions identify
survey_version=stage5_v1. Only the current tab may write a case.

## Verification

From `Product/`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
node frontend/tests/api.test.mjs
node frontend/tests/timing.test.mjs
node frontend/tests/views.test.mjs
```

Node.js is needed only for the JavaScript checks, not to run the simulator. Python
checks use temporary databases and cover source validation, participant isolation,
all stage transitions, 3/3 outcome balance, feedback validation, timing, retries,
restart recovery, authorization, and migration preservation/rollback. Browser checks
should also cover first-time and returning entry, mobile layout, keyboard interaction,
draft recovery and multi-pair feedback submission.
