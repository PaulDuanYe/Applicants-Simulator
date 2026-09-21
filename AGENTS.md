# Project Context

## Purpose and target working direction

- This project is **not a game**. It is a design-science-based research framework for studying how people understand and behave with respect to fairness in human-resource decision-making scenarios.
- The intended paper venue is ACM FAccT. The framework should support research on fairness in a sociotechnical hiring context rather than teach participants a predetermined definition of fairness.
- Current research and development focus exclusively on the employee/applicant side: how affected people understand and behave with respect to fairness in hiring-decision scenarios.
- The HR/recruiter side is deprioritized and paused. It is out of scope for current design and research work and must not be treated as under parallel development.
- The HR-side framework has not been permanently removed or rejected. It may eventually be abandoned, but that decision remains unresolved.

The target working direction studies **algorithmic fairness conditions or outcome
characteristics → participants’ perceived fairness**. Assign a profile, present
competing applicants for the same position, generate/reveal outcomes using relevant
attributes and the designed fairness matrix/condition, then collect feedback. There
is no pre-outcome prediction or independent should-pass task in the target flow.
This direction is not implemented or finalized. Do not invent the matrix, algorithm,
assignment rules, competitor count, outcome quota, or feedback instrument; ask before
formalizing unresolved methodology. Do not use numbered research-variable labels
for the target direction.

## Current implementation and legacy elements

- `Product/` currently implements the previous five-stage flow: Software Engineer profile review,
  job review/selection, six-applicant should-pass judgments, historical result revelation,
  and perceived-fairness feedback. The last two share a page; judgment submission
  and result retrieval are one action.
- New cases use `configurable_entry_v1`: `backend/config.py` switches independently
  enable refresh and job selection (both default off). Values are saved in
  `case_configuration`; existing cases retain their saved settings or legacy behavior.
  Profile and job remain separate pages. Refresh stays within Software Engineer;
  enabled job selection offers all three jobs. Later stages are unchanged.
- X1 (refresh count), X2 (job choice), and Y1 (participant pre-outcome should-pass
  judgment, not prediction or algorithm output) remain implemented and recorded,
  but are excluded from the target framework. Earlier interpretations of refresh
  count and job choice are hypotheses from the previous design.
- Only `historical` works: fixed fictional dataset values, with the current
  alternative-job rejection rule and three-pass/three-reject balance. `llm`,
  `matrix`, and `random_method` are unimplemented extension points. The method
  identifier does not operationalize the target fairness condition.
- The five stages describe the current product, not its intended destination or a
  finalized protocol. Do not carry current demo restrictions into the target by
  default. A direction change does not authorize deleting code, fields or records.

## Architecture and development conventions

- Python Flask serves the API and `Product/frontend/` via `/static/`; the frontend
  is vanilla JavaScript. One backend process serves both; Windows/macOS launchers
  are documented in the README. macOS execution has not yet been verified here.
- Backend coordination handles sampling, stage progression, ownership, validation,
  transactions and exact-request retries; the frontend handles rendering, local
  drafts, serialized actions and visible-page timing.
- SQLite output is `Product/backend/outputs/research.sqlite3`, initialized on the
  first participant API request. Participant → sessions → cases link stage records;
  the current UI creates one case per session. Preserve incomplete observations.
- Stage 3 stores profiles/judgments only. Historical-only inputs and common results
  are separate Stage 4 tables. Stage 5 group choices are embedded JSON in feedback;
  comparison pairs have a separate table. Results/survey share Stage 4 duration.
- Preserve source JSON and existing research records; use `pass`/`reject` internally.
  Keep credentials, receipts and browser drafts out of research exports. Source
  schema is in `data-structure.md`; output schema is in `DATA_STORAGE.md`.
- Existing tests run from `Product/`: `.venv/Scripts/python.exe -m unittest discover
  -s backend/tests -v` (macOS: `.venv/bin/python`); Node checks cover API and timing.
  Analytics/export tooling is not implemented. Future work is a direction, not a
  fully specified implementation backlog.

## Existing terminology and constraints

- **Group fairness:** earlier project shorthand concerns outcome distribution across demographic groups; it is not an operational definition for the target matrix.
- **Individual fairness:** whether similar individuals are treated similarly; the target similarity criteria remain unspecified.
- **Job-relevant attributes:** candidate information such as education, experience, and skills.
- **Sensitive attributes:** demographic or personal information that may be subject to bias, including examples discussed in the project such as gender, age, marital/family status, and region. The final set is unresolved.
- “Disparity,” “bias,” and “unfairness” must not be treated as interchangeable: observed selection patterns are the research data and are not, by themselves, an automatic verdict on an individual decision.

## Continuing project constraints

- Do not define an objectively fair or ideal hiring decision.
- Do not assign applicants an objective score, rank candidates against a system-defined best applicant, or evaluate participants against a predefined correct answer.
- Current fictional profiles contain job-relevant attributes plus gender, age and marital status. This implemented dataset does not settle the target attribute set or establish a matched-profile requirement.
- Develop the applicant perspective: applicants/interviewees experience or evaluate hiring decisions as affected people.
- Prior dual-role plans involving HR participants, aggregation of HR decisions, or direct HR-versus-applicant comparisons are paused and are not active requirements.
- Separate research measurement from any educational or debriefing content. Do not prime participants with a preferred fairness answer during measurement.

## Important constraints

- Do not reintroduce the abandoned “game” framing, hidden scoring system, “system best” candidate, or automated fair/unfair verdicts.
- Do not undertake HR-side design or implementation unless a later explicit project decision reactivates it.
- Do not describe the HR side as permanently abandoned; its long-term status is unresolved.
- Do not treat exploratory questions, example attributes, interface ideas, or prior brainstorming as settled study requirements.
- Do not invent new fairness constructs, categories, measures, or terminology without an explicit project decision.
- Exact study protocol, final sensitive attributes, operational measures, and analysis plan remain unresolved unless a later project document or user decision settles them.

## Repository guide

- [FIVE_STAGE_FRAMEWORK.md](Product/FIVE_STAGE_FRAMEWORK.md): current five-stage
  behavior/previous design, with a separate provisional target-direction section;
  not an authoritative future-product specification.
- [README.md](Product/README.md): setup, current workflow and verification commands.
- [DATA_STORAGE.md](Product/DATA_STORAGE.md): current output schema and recording rules.
- [data-structure.md](Product/data-structure.md): existing input JSON schema.
- [dataset-requirement.md](Product/dataset-requirement.md): supplementary product
  inventory/output reference; some filenames/version notes may lag the current files.
- `hr.docx`: entirely outdated historical material, not current requirements.
- `kh demo/mini/`: legacy prototypes (`flow-new.html`, `flow.html`, `flow-ideal.html`,
  `app.js`, `style.css`, `index.html`); preserve as artifacts, not active specifications.
