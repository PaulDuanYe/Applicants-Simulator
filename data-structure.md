# Job and applicant data structure

## Files and relationship

The demo stores three job descriptions in [jobs.json](jobs.json) and 50 fictional applicant profiles in [applicants.json](applicants.json). Each file contains a top-level JSON array of objects.

An applicant's `job_id` references the matching job's `job_id`. This is a one-to-many relationship: Software Engineer has 30 applicants and each other job has 10 applicants, and each applicant record refers to one job. Job descriptions are stored separately rather than repeated inside applicant records.

## Job fields

| Field | JSON type | Meaning |
| --- | --- | --- |
| `job_id` | string | Unique job identifier used to link applicants to a job. |
| `title` | string | Job title. |
| `description` | string | Description of the work and required qualifications. |
| `provenance` | object | Empty placeholder; must remain exactly `{}`. |

## Applicant fields

| Field | JSON type | Meaning |
| --- | --- | --- |
| `profile_id` | string | Unique applicant profile identifier. |
| `job_id` | string | Identifier of the job this applicant is applying for; matches an entry in `jobs.json`. |
| `job_related_attributes` | object | Groups the applicant's job-related qualifications. |
| `job_related_attributes.education` | string | Educational background, including qualification and field of study. |
| `job_related_attributes.experience_years` | number (integer in this dataset) | Years of work experience. |
| `job_related_attributes.skills` | array of strings | Skills, tools, and areas of practical experience. |
| `protected_attributes` | object | Groups demographic information separately from job-related qualifications. |
| `protected_attributes.gender` | string | Gender recorded for the fictional applicant. |
| `protected_attributes.age` | number (integer in this dataset) | Age in years. |
| `provenance` | object | Empty placeholder; must remain exactly `{}`. |
| `protected_attributes.marital_status` | string | Fictional marital status: `未婚`, `已婚`, `离异` or `丧偶`. |
| `results` | object | Stored fictional screening outcome and illustrative score. |
| `results.score` | integer | Fixed illustrative value from 0–100; source data only. |
| `results.decision` | string | Initial CV screening outcome: `pass` or `reject`. |

The dotted field names in the table describe nesting; they are not literal JSON keys. For example, `education` is inside `job_related_attributes`.

Gender, age and marital status are the demographic fields used in this demo. They do not establish the final attribute set for the research framework.

## Identifiers and current counts

For the three current jobs, the first digit after `candidate_` corresponds to the job number without leading zeros. The remaining three digits identify applicants `001` through `030` for Software Engineer and `001` through `010` for each other job. Use the explicit `job_id` field to associate records.

| Job ID | Job title | Applicant ID range | Applicants | Pass | Reject |
| --- | --- | --- | --- | --- | --- |
| `job_001` | Software Engineer | `candidate_1001`–`candidate_1030` | 30 | 15 | 15 |
| `job_002` | Financial Analyst | `candidate_2001`–`candidate_2010` | 10 | 5 | 5 |
| `job_003` | Graphic Designer | `candidate_3001`–`candidate_3010` | 10 | 5 | 5 |
| Total | | | 50 | 25 | 25 |

These counts describe the current demo dataset.

## Matching record example

The following job object is copied from `jobs.json`:

```json
{
  "job_id": "job_001",
  "title": "Software Engineer",
  "description": "开发后端服务，要求熟悉 Python 和 SQL。",
  "provenance": {}
}
```

The following applicant object is copied from `applicants.json` and references that job through `job_id`:

```json
{
  "profile_id": "candidate_1001",
  "job_id": "job_001",
  "job_related_attributes": {
    "education": "计算机科学本科",
    "experience_years": 3,
    "skills": ["Python", "SQL", "FastAPI", "PostgreSQL", "后端接口开发"]
  },
  "protected_attributes": {
    "gender": "女性",
    "age": 26,
    "marital_status": "未婚"
  },
  "provenance": {},
  "results": {
    "decision": "pass",
    "score": 80
  }
}
```

Each example shows one array element. The source files wrap their records in arrays.

## Screening outcomes

- `pass`: The applicant passes initial CV screening and proceeds to the next stage; this is not a final hiring decision.
- `reject`: The applicant is screened out at initial CV screening.

The demo requires 15 outcomes of each kind for Software Engineer and five of each kind for each other job. Screening decisions must be based on `job_related_attributes` and fit with the referenced job description. `protected_attributes` must not be used as a screening basis.

The files store outcomes; they do not encode a screening algorithm or decision rationale. These demo outcomes are not objective fairness judgments or an objective scoring system, and they do not define a correct answer for research participants.

## Data consistency

When handling this demo data, preserve the field names and nested structure, keep identifiers unique, and ensure every applicant's `job_id` matches a stored job. Keep qualifications separate from demographic information and retain the counts in the table above. Every `provenance` value must remain exactly `{}`.

Scores are fixed fictional values: passing applicants generally have higher scores, with overlapping ranges and no decision threshold. Scores do not determine outcomes, ranking or participant correctness, and are not exposed in participant APIs or persisted in research records. Marital status is assigned independently of outcomes and displayed on profile cards; older saved profiles may omit it. These additions do not establish the target study’s fairness methodology.
