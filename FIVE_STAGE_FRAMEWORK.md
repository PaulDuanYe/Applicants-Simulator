# Current Five-Stage Product and Target Working Direction

## Status and scope

This file primarily describes the **current implemented product and previous research
design**, not the authoritative specification of the future product or final methodology.
The five-stage description remains useful for understanding existing behavior and data.
It is not the product direction now being pursued. Current behavior, target direction,
and legacy research elements must not be conflated.

## Target working direction — not yet implemented

Study how **algorithmic fairness conditions or outcome characteristics influence
participants’ perceived fairness**. The intended flow is:

1. Assign a randomly generated or selected applicant profile.
2. Present other applicants competing for the same position.
3. Generate and reveal screening outcomes using relevant applicant attributes and
   the designed fairness matrix or condition, before asking for participant judgment.
4. Collect perceived-fairness feedback after the outcome is shown.

The target has no pre-outcome prediction or independent should-pass judgment task.
Profile-refresh behavior, participant job choice and pre-outcome judgments are not
required research components of this direction. Existing functionality and historical
records remain intact until implementation changes are explicitly authorized.

This is a working direction, not a finalized protocol. Matrix definitions, algorithms,
assignment procedures, competitor counts, outcome quotas, attributes and feedback
measures remain unresolved. Do not automatically retain the current six-person/3–3
arrangement, alternative-job rejection rule, or survey instrument as target requirements.

### Transition from the previous research design

X1, X2 and Y1 are legacy elements retained in the current implementation, excluded
from the target framework. The target’s two central concepts are similar to the
former X3 and Y2 concepts, but are not identical operational definitions or measures.
In particular, a stored generation-method identifier does not define a fairness
condition. The target uses descriptive concepts rather than those variable labels.

## Current product: purpose and legacy variable labels

The main purpose of this framework is to study the factors that influence people's **perceived fairness** in hiring scenarios from the applicant's perspective.

The current product collects two distinct kinds of participant response:

1. **Pre-outcome should-pass judgment (legacy y1):** participants indicate who should pass screening. This is not a prediction of actual outcomes, an algorithmic output, or an established measure of perceived fairness.
2. **Survey after reviewing the outcomes (y2):** participants complete a perceived-fairness survey after seeing the application outcomes.

The previous design uses these labels; they describe existing records, not required target variables:

| Variable | Meaning | Role in the framework |
| --- | --- | --- |
| **x1** | Number of times a participant refreshes or changes the assigned profile | Previously hypothesized to relate to acceptance of profiles; not an established interpretation |
| **x2** | Job option selected by the participant | Previously hypothesized to relate to understanding of profile/job requirements; not an established interpretation |
| **x3** | Method or algorithm used to generate the application outcomes | An outcome-generation factor that may influence the final perceived-fairness survey |
| **y1** | Participant judgments of who should pass among six applicants | May be affected by x1 and x2 |
| **y2** | Perceived-fairness survey after reviewing the outcomes | May be affected by x3, x1, x2 and y1 |

The displayed outcome is part of the framework and one of the factors that may influence perceived fairness. Historical authenticity and objective fairness are not requirements for the outcome. Outcomes may come from historical records, an AI method, another algorithm or a random mechanism, and may be biased or unbiased. The framework does not prescribe an objectively fair or unfair answer for participants.

## Transitional entry configuration

Both switches live in `backend/config.py` and are snapshotted per new case in
`case_configuration`. Restart the server after edits; only new cases use changed
settings. Existing cases and historical records are preserved. The current
should-pass assessment, historical outcomes and questionnaire remain operational.
This incremental change does not implement the broader target without pre-outcome
judgments or settle its methodology.

## Stage 1: Profile review — optional refresh / legacy x1

New cases uniformly receive a Software Engineer (`job_001`) profile. Stage 1 and
Stage 2 remain separate pages. `PROFILE_REFRESH_ENABLED` defaults to false; when
enabled, refresh samples another Software Engineer profile, excluding the current
one. Later repeats remain possible. Continuing locks the profile. Legacy cases
without saved configuration retain their original all-applicant sampling behavior.

**x1** is the number of profile refreshes or changes. Its proposed relationship to acceptance of less competitive profiles was a working hypothesis in the previous design, not an established measure.

The current product records:

- Which profiles participants view and the order in which they view them.
- How long they spend reviewing each profile.
- How many times they refresh or change the profile.
- Which profile they ultimately select.
- How long it takes them to click the confirmation button.

When refresh is disabled, these records capture assigned-profile review, not search
behavior or a free profile choice.

## Stage 2: Job review or selection — legacy x2

By default, `JOB_SELECTION_ENABLED` is false: participants read only the Software
Engineer description and continue. When enabled, participants see three job opportunities. The previous design intended different levels of match, but the current product computes no match rating:

1. The original job linked to the assigned fictional profile in the dataset.
2. One of the other two dataset jobs.
3. The remaining dataset job.

For example, a participant with a software engineer profile could see **Software Engineer**, **Financial Analyst** and **Graphic Designer** as the three options.

**x2** is the selected job. Its proposed relationship to understanding of the profile and job requirements was a working hypothesis in the previous design.

The product records the fixed or selected job, displayed job snapshots, and visible
review time. Disabled selection has one option and no unselected jobs; its duration
is review time, not choice time.

With job selection enabled, the demo offers all three jobs once in a saved shuffled order, with no original-job or fit labels. Once confirmed, profile and job choices cannot be edited. The job choice has two consequences for the following stages:

- It determines the applicant pool from which the five competitors are selected in Stage 3.
- It determines whether Stage 4 uses the selected outcome-generation method or automatically rejects the participant's assigned candidate.

## Stage 3: Competition Assessment — y1

After job confirmation, the current product prepares six fictional applicants: the
participant and five distinct competitors sampled from the selected job’s pool,
excluding the participant’s profile. The participant appears first; competitor
order is shuffled once and retained. All apply in the context of the selected job.

The participant answers who **should pass screening**, selecting three `pass` and
three `reject` judgments. These participant opinions are recorded as legacy **y1**,
with review timing; they are not predictions of who will actually pass or receive an
offer. Stage 3 stores no outcome-generation fields or automated fairness verdict.

“确认并查看结果” validates and saves the six judgments and retrieves Stage 4 results
in one transaction, then displays results directly. Judgments are locked after
submission. This pre-outcome task is legacy functionality, not part of the target flow.

## Stage 4: Outcome Revelation — x3

Participants are shown screening outcomes for themselves and the same five competitors in the saved order. `pass` means passing screening, not receiving a job offer.

**x3** is the method or algorithm used to generate application outcomes. The current dispatcher recognizes four method identifiers:

1. **Historical (`historical`) — implemented:** fixed fictional dataset decisions, frozen in method-specific Stage 4 input records at group preparation. These are not independently verified hiring records.
2. **Large language model (`llm`) — unimplemented extension point.**
3. **Matrix-restricted algorithm (`matrix`) — unimplemented extension point; no target fairness matrix is defined by this placeholder.**
4. **Random (`random_method`) — unimplemented extension point.**

Unimplemented methods raise explicit errors; participants do not choose a method. The current backend uses `historical`. The participant's Stage 2 job choice determines the current outcome branch:

| Stage 2 choice | Stage 4 outcome rule for the participant's assigned candidate |
| --- | --- |
| Original job | Use the selected outcome-generation method |
| Either alternative job | Automatically classify the assigned candidate as rejected |

Automatic rejection for an alternative job is a current demo rule, not a confirmed target requirement. It does not itself determine competitors’ outcomes; rejecting the participant does not imply that any particular competitor passes.

Group sampling and rule resolution preserve exactly three pass and three reject outcomes across all six applicants. This is separate from the 3/3 participant-judgment constraint. The outcome provides the context for the current survey in Stage 5. It does not need to be a historical hiring record or an objectively fair decision.

## Stage 5: Fairness Evaluation — y2

The current results and feedback share a page. Participants see their saved judgments
alongside results, with neutral mismatch labels, then provide:

- A required 1–10 overall fairness rating.
- Overall-distribution opinions (including age/gender discrimination or excessive
  emphasis on experience/education/skills, other, none or unsure), with reasons.
- Whether they consider an unsuccessful applicant more suitable than a successful
  one. A “yes” response supports 1–9 distinct applicant pairs, each with its own
  reason; “no” and “unsure” require an explanation instead.

These responses are legacy **y2** records in the current implementation; the target
feedback design remains unresolved. Submission saves feedback and ends the visit.
No correctness score or automated fairness verdict is generated.

## Current recording and implementation boundaries

Participants can reuse their code across visits. The UI creates one case per session;
starting a new visit preserves partial earlier records. Profile viewing history,
refreshes, job choices, judgments, results and feedback remain linked in SQLite.
See [DATA_STORAGE.md](DATA_STORAGE.md) for fields and lifecycle, and
[README.md](README.md) for setup and implemented interfaces.

Timing measures visible-page duration, not attention. User-action waits and hidden
time are excluded; background timing-checkpoint waits currently keep the timer
running. Stages 4 and 5 share one duration in the Stage 4 record; there is no separate
survey-only duration. Preparation, retrieval and browser display acknowledgment
are distinct events. These are current implementation facts, not a finalized study
protocol. Analytics and export generation remain unimplemented.
