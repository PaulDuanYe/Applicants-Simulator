import json
import os
from pathlib import Path
import tempfile
import unittest

from backend.dataset import DatasetValidationError, load_dataset

SOURCE = Path(__file__).resolve().parents[2]


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.jobs = json.loads((SOURCE / "jobs.json").read_text(encoding="utf-8"))
        self.applicants = json.loads((SOURCE / "applicants.json").read_text(encoding="utf-8"))

    def write_fixture(self):
        for name, records in (("jobs", self.jobs), ("applicants", self.applicants)):
            (self.directory / f"{name}.json").write_text(json.dumps(records), encoding="utf-8")

    def test_grouping_order_and_source_preservation(self):
        before = {name: (SOURCE / name).read_bytes() for name in ("jobs.json", "applicants.json")}
        dataset = load_dataset()
        seen = []
        for job_id, groups in dataset.applicants_by_job_and_decision.items():
            for decision, records in groups.items():
                expected = [p for p in self.applicants if p["job_id"] == job_id and p["results"]["decision"] == decision]
                self.assertEqual(records, expected)
                self.assertEqual(len(records), 15 if job_id == "job_001" else 5)
                for record in records:
                    self.assertIs(record, dataset.applicants_by_id[record["profile_id"]])
                    seen.append(record["profile_id"])
        self.assertEqual(len(seen), 50)
        self.assertEqual(len(set(seen)), 50)
        for name, contents in before.items():
            self.assertEqual((SOURCE / name).read_bytes(), contents)

    def test_paths_independent_of_working_directory(self):
        original = Path.cwd()
        try:
            os.chdir(self.directory)
            for directory in (None, ".", SOURCE):
                self.assertEqual(len(load_dataset(directory).jobs_by_id), 3)
        finally:
            os.chdir(original)

    def test_invalid_records(self):
        cases = [
            (lambda: self.jobs[0].pop("title"), "missing fields"),
            (lambda: self.jobs[0].update(title=4), "title: expected str"),
            (lambda: self.jobs[1].update(job_id=self.jobs[0]["job_id"]), "duplicate identifier"),
            (lambda: self.applicants[1].update(profile_id=self.applicants[0]["profile_id"]), "duplicate identifier"),
            (lambda: self.applicants[0].update(job_id="missing"), "unknown job"),
            (lambda: self.applicants[0]["results"].update(decision="fail"), "expected 'pass' or 'reject'"),
            (lambda: self.applicants[0].update(provenance={"source": "test"}), "provenance"),
            (lambda: self.jobs[0].update(provenance={"source": "test"}), "provenance"),
            (lambda: self.applicants[0]["protected_attributes"].update(age=True), "age: expected int"),
            (lambda: self.applicants[0]["job_related_attributes"].update(skills=[3]), "skills: expected strings"),
            (lambda: self.applicants[0]["job_related_attributes"].pop("education"), "missing fields"),
            (lambda: self.applicants[0]["results"].update(decision="reject"), "expected 15 pass"),
            (lambda: self.applicants.pop(), "3 jobs and 50 applicants"),
            (lambda: self.jobs.append(dict(self.jobs[0], job_id="extra")), "3 jobs and 50 applicants"),
        ]
        cases.extend([
            (lambda: self.applicants[0]["results"].update(score=True), "score: expected int"),
            (lambda: self.applicants[0]["results"].update(score=80.5), "score: expected int"),
            (lambda: self.applicants[0]["results"].update(score=-1), "score: expected integer from 0 to 100"),
            (lambda: self.applicants[0]["results"].update(score=101), "score: expected integer from 0 to 100"),
            (lambda: self.applicants[0]["results"].pop("score"), "missing fields"),
            (lambda: self.applicants[0].update(decision="pass"), "unexpected fields"),
            (lambda: self.applicants[0]["protected_attributes"].pop("marital_status"), "missing fields"),
            (lambda: self.applicants[0]["protected_attributes"].update(marital_status="unknown"), "unsupported status"),
        ])
        original_jobs = json.dumps(self.jobs)
        original_applicants = json.dumps(self.applicants)
        for mutate, message in cases:
            with self.subTest(message=message):
                self.jobs = json.loads(original_jobs)
                self.applicants = json.loads(original_applicants)
                mutate()
                self.write_fixture()
                with self.assertRaisesRegex(DatasetValidationError, message):
                    load_dataset(self.directory)

    def test_missing_malformed_and_non_array_files(self):
        with self.assertRaisesRegex(DatasetValidationError, "jobs.json: cannot read JSON"):
            load_dataset(self.directory)
        for content, message in (("{", "cannot read JSON"), ("{}", "top-level array")):
            (self.directory / "jobs.json").write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(DatasetValidationError, message):
                load_dataset(self.directory)
