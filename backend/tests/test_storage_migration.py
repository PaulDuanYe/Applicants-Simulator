"""Exercise old-schema conversion with real linked experiment records."""
import sqlite3
import unittest
from contextlib import closing

from backend.storage import Storage
import test_experiment


class MigrationTests(unittest.TestCase):
    def legacy_fixture(self, revealed=False, ended=False):
        flow = test_experiment.ExperimentTests()
        flow.setUp()
        self.addCleanup(flow.temp.cleanup)
        flow.setup_competition(alternative=True)
        flow.post(flow.payload('display'))
        if revealed:
            judgments = [dict(profile_id=a['profile_id'], judgment='pass' if i < 3 else 'reject')
                         for i, a in enumerate(flow.state['applicants'])]
            flow.post(flow.payload('submit_judgments', judgments=judgments))
            flow.post(flow.payload('reveal_outcomes'))
            flow.post(flow.payload('display'))
            if ended:
                flow.post(flow.payload('end_session', duration_ms=321))
        with closing(sqlite3.connect(flow.path)) as db:
            db.executescript('''
                CREATE TABLE legacy3 (
                  case_id TEXT NOT NULL REFERENCES stage3_competition_assessment,
                  display_position INTEGER NOT NULL, profile_id TEXT NOT NULL,
                  applicant_role TEXT NOT NULL, displayed_profile_json TEXT NOT NULL,
                  source_decision TEXT NOT NULL, case_decision TEXT NOT NULL,
                  decision_basis TEXT NOT NULL, participant_judgment TEXT,
                  PRIMARY KEY(case_id,display_position), UNIQUE(case_id,profile_id));
                INSERT INTO legacy3 SELECT a.case_id,a.display_position,a.profile_id,
                  a.applicant_role,a.displayed_profile_json,h.source_decision,
                  CASE WHEN a.applicant_role='participant' THEN 'reject' ELSE h.source_decision END,
                  CASE WHEN a.applicant_role='participant' THEN 'alternative_job_rejection' ELSE 'source_decision' END,
                  a.participant_judgment FROM stage3_applicants a JOIN stage4_historical_inputs h USING(case_id,profile_id);
                CREATE TABLE legacy4 (
                  case_id TEXT NOT NULL REFERENCES stage4_outcome_revelation, profile_id TEXT NOT NULL,
                  method_decision TEXT NOT NULL, revealed_decision TEXT NOT NULL, decision_basis TEXT NOT NULL,
                  PRIMARY KEY(case_id,profile_id),
                  FOREIGN KEY(case_id,profile_id) REFERENCES stage3_applicants(case_id,profile_id));
                INSERT INTO legacy4 SELECT o.case_id,o.profile_id,h.source_decision,o.revealed_decision,
                  COALESCE(o.applied_rule,'source_decision') FROM stage4_applicant_outcomes o
                  JOIN stage4_historical_inputs h USING(case_id,profile_id);
                DROP TABLE stage4_applicant_outcomes;
                DROP TABLE stage4_historical_inputs;
                DROP TABLE stage3_applicants;
                ALTER TABLE legacy3 RENAME TO stage3_applicants;
                ALTER TABLE legacy4 RENAME TO stage4_applicant_outcomes;
                UPDATE cases SET schema_version='stage1_4_v1';
            ''')
        return flow

    def test_open_revealed_and_ended_records_survive_migration(self):
        for revealed, ended in [(False, False), (True, False), (True, True)]:
            with self.subTest(revealed=revealed, ended=ended):
                flow = self.legacy_fixture(revealed, ended)
                unchanged = {table: flow.rows(table) for table in (
                    'sessions', 'cases', 'stage3_competition_assessment',
                    'stage4_outcome_revelation', 'technical_receipts', 'technical_case_state')}
                before = flow.rows('stage3_applicants')
                Storage(flow.path)
                Storage(flow.path)  # Migration is safe to repeat.
                for table, rows in unchanged.items():
                    self.assertEqual(flow.rows(table), rows)
                for old, current in zip(before, flow.rows('stage3_applicants')):
                    self.assertEqual(current, {k: v for k, v in old.items()
                        if k not in ('source_decision', 'case_decision', 'decision_basis')})
                self.assertEqual(len(flow.rows('stage4_historical_inputs')), 6)
                for row in flow.rows('stage4_applicant_outcomes'):
                    self.assertEqual(row['decision_basis'], 'historical')
                with closing(sqlite3.connect(flow.path)) as db:
                    self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
                if not revealed:
                    flow.post(flow.payload('claim'))
                    judgments = [dict(profile_id=a['profile_id'], judgment='pass' if i < 3 else 'reject')
                                 for i, a in enumerate(flow.state['applicants'])]
                    flow.post(flow.payload('submit_judgments', judgments=judgments))
                    flow.post(flow.payload('reveal_outcomes'))
                    self.assertEqual(sum(a['revealed_decision'] == 'pass' for a in flow.state['applicants']), 3)

    def test_invalid_legacy_values_roll_back_without_dropping_fields(self):
        flow = self.legacy_fixture()
        with closing(sqlite3.connect(flow.path)) as db:
            db.execute("UPDATE stage3_applicants SET case_decision='pass' WHERE applicant_role='participant'")
            db.commit()
        before = flow.rows('stage3_applicants')
        with self.assertRaisesRegex(ValueError, 'migration rolled back'):
            Storage(flow.path)
        self.assertEqual(flow.rows('stage3_applicants'), before)

    def test_failure_after_input_copy_rolls_back_all_schema_changes(self):
        flow = self.legacy_fixture(revealed=True)
        with closing(sqlite3.connect(flow.path)) as db:
            db.execute("UPDATE stage4_applicant_outcomes SET method_decision='reject'")
            db.commit()
        before = flow.rows('stage4_applicant_outcomes')
        with self.assertRaisesRegex(ValueError, 'migration rolled back'):
            Storage(flow.path)
        self.assertEqual(flow.rows('stage4_applicant_outcomes'), before)
        with closing(sqlite3.connect(flow.path)) as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='stage4_historical_inputs'").fetchone())
