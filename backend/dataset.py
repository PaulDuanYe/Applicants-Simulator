"""Read-only loading and indexing of the current fictional demo dataset."""

import json
from dataclasses import dataclass
from pathlib import Path


class DatasetValidationError(ValueError):
    """A source file does not satisfy the documented demo schema."""


@dataclass
class Dataset:
    jobs_by_id: dict
    applicants_by_id: dict
    applicants_by_job_and_decision: dict


def _fields(record, schema, location):
    if type(record) is not dict:
        raise DatasetValidationError(f"{location}: expected an object")
    if set(record) != set(schema):
        missing = sorted(set(schema) - set(record))
        extra = sorted(set(record) - set(schema))
        raise DatasetValidationError(f"{location}: missing fields {missing}; unexpected fields {extra}")
    for key, expected in schema.items():
        if type(record[key]) is not expected:
            raise DatasetValidationError(f"{location}.{key}: expected {expected.__name__}")


def _read(path):
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise DatasetValidationError(f"{path}: cannot read JSON: {exc}") from exc
    if type(records) is not list:
        raise DatasetValidationError(f"{path}: expected a top-level array")
    return records


def load_dataset(data_dir=None):
    """Return original records indexed by ID and job/decision, without file writes.

    Default and relative directories resolve against Product, not the shell cwd.
    Indexes share records and must be treated as read-only by callers.
    """
    base = Path(__file__).resolve().parent.parent
    directory = Path(data_dir) if data_dir is not None else base
    if not directory.is_absolute():
        directory = base / directory
    jobs = _read(directory / "jobs.json")
    applicants = _read(directory / "applicants.json")
    jobs_by_id, applicants_by_id, grouped = {}, {}, {}
    for i, job in enumerate(jobs):
        location = f"jobs.json[{i}]"
        _fields(job, {"job_id": str, "title": str, "description": str, "provenance": dict}, location)
        if not job["job_id"] or job["job_id"] in jobs_by_id:
            raise DatasetValidationError(f"{location}.job_id: empty or duplicate identifier {job['job_id']!r}")
        if job["provenance"] != {}:
            raise DatasetValidationError(f"{location}.provenance: must be exactly {{}}")
        jobs_by_id[job["job_id"]] = job
        grouped[job["job_id"]] = {"pass": [], "reject": []}
    for i, applicant in enumerate(applicants):
        location = f"applicants.json[{i}]"
        _fields(applicant, {"profile_id": str, "job_id": str, "job_related_attributes": dict,
                           "protected_attributes": dict, "provenance": dict, "results": dict}, location)
        _fields(applicant["job_related_attributes"], {"education": str, "experience_years": int,
                                                     "skills": list}, f"{location}.job_related_attributes")
        _fields(applicant["protected_attributes"], {"gender": str, "age": int, "marital_status": str}, f"{location}.protected_attributes")
        _fields(applicant["results"], {"decision": str, "score": int}, f"{location}.results")
        if not 0 <= applicant["results"]["score"] <= 100:
            raise DatasetValidationError(f"{location}.results.score: expected integer from 0 to 100")
        if applicant["protected_attributes"]["marital_status"] not in ("未婚", "已婚", "离异", "丧偶"):
            raise DatasetValidationError(f"{location}.protected_attributes.marital_status: unsupported status")
        if any(type(skill) is not str for skill in applicant["job_related_attributes"]["skills"]):
            raise DatasetValidationError(f"{location}.job_related_attributes.skills: expected strings")
        if applicant["provenance"] != {}:
            raise DatasetValidationError(f"{location}.provenance: must be exactly {{}}")
        profile_id, job_id, decision = applicant["profile_id"], applicant["job_id"], applicant["results"]["decision"]
        if not profile_id or profile_id in applicants_by_id:
            raise DatasetValidationError(f"{location}.profile_id: empty or duplicate identifier {profile_id!r}")
        if job_id not in jobs_by_id:
            raise DatasetValidationError(f"{location}.job_id: unknown job {job_id!r}")
        if decision not in ("pass", "reject"):
            raise DatasetValidationError(f"{location}.results.decision: expected 'pass' or 'reject', got {decision!r}")
        applicants_by_id[profile_id] = applicant
        grouped[job_id][decision].append(applicant)
    if len(jobs) != 3 or len(applicants) != 50:
        raise DatasetValidationError(f"Current demo requires 3 jobs and 50 applicants; got {len(jobs)} and {len(applicants)}")
    for job_id, groups in grouped.items():
        expected_count = 15 if job_id == "job_001" else 5
        for decision, records in groups.items():
            if len(records) != expected_count:
                raise DatasetValidationError(f"{job_id}: expected {expected_count} {decision} applicants; got {len(records)}")
    return Dataset(jobs_by_id, applicants_by_id, grouped)
