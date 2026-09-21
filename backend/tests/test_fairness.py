import unittest
import json
import sqlite3
from contextlib import closing
from backend.storage import Storage
import test_experiment
from backend.fairness import validate_feedback
from backend.app import create_app


class FairnessTests(unittest.TestCase):
    def setUp(self):
        self.flow = f = test_experiment.ExperimentTests()
        f.setUp(); self.addCleanup(f.temp.cleanup)
        f.setup_competition(); f.post(f.payload('display'))
        judgments = [dict(profile_id=a['profile_id'], judgment='pass' if i < 3 else 'reject') for i, a in enumerate(f.state['applicants'])]
        f.post(f.payload('submit_and_reveal', judgments=judgments))
        self.outcomes = {a['profile_id']: a['revealed_decision'] for a in f.state['applicants']}
        rejected = [k for k, v in self.outcomes.items() if v == 'reject']
        passed = [k for k, v in self.outcomes.items() if v == 'pass']
        self.answer = dict(fairness_rating=7, group_selections=['age_discrimination', 'other'],
            group_reason=' 我的理由 ', other_group_view='其他看法', individual_comparison='yes',
            comparisons=[dict(rejected_profile_id=r, passed_profile_id=p, reason='比较理由')
                         for r, p in [(rejected[0], passed[0]), (rejected[0], passed[1]), (rejected[1], passed[0])]])

    def test_display_submit_retry_and_unchanged_research(self):
        f = self.flow
        before = f.rows('stage3_applicants'); outcomes = f.rows('stage4_applicant_outcomes')
        f.post(f.payload('submit_fairness', survey_version='stage5_v1', **self.answer), 409)
        f.post(f.payload('display'))
        revealed = f.rows('stage4_outcome_revelation')[0]['revealed_at']
        f.post(f.payload('timing', duration_ms=100))
        f.app = create_app(db_path=f.path); f.client = f.app.test_client()
        f.post(f.payload('claim'))
        self.assertFalse(f.state['survey_ack'])
        f.post(f.payload('display', survey_version='stage5_v1', at='2026-09-15T09:00:00Z'))
        self.assertEqual(f.rows('stage4_outcome_revelation')[0]['revealed_at'], revealed)
        self.assertIsNone(f.rows('stage5_fairness_feedback')[0]['fairness_rating'])
        f.post(f.payload('end_session'), 409)
        action = f.payload('submit_fairness', survey_version='stage5_v1', duration_ms=500, **self.answer)
        result = f.post(action); self.assertTrue(result['feedback_saved']); self.assertEqual(f.post(action), result)
        self.assertEqual(len(f.rows('stage5_applicant_comparisons')), 3)
        self.assertEqual(f.rows('stage5_fairness_feedback')[0]['group_reason'], '我的理由')
        self.assertEqual(json.loads(f.rows('stage5_fairness_feedback')[0]['group_selections_json']), sorted(self.answer['group_selections']))
        self.assertEqual(f.rows('stage4_outcome_revelation')[0]['duration_ms'], 500)
        self.assertEqual(f.rows('stage3_applicants'), before); self.assertEqual(f.rows('stage4_applicant_outcomes'), outcomes)
        f.post(f.payload('submit_fairness', survey_version='stage5_v1', **self.answer), 409)

    def test_validation(self):
        bad = [dict(fairness_rating=v) for v in [0, 11, True, 2.5]]
        bad += [dict(group_selections=v) for v in [[], ['none', 'other'], ['unsure', 'none'], ['other', 'other'], ['unknown']]]
        bad += [dict(group_reason='  '), dict(other_group_view=''), dict(group_reason='x'*5001),
                dict(comparisons=[]), dict(comparisons=self.answer['comparisons']*2),
                dict(comparisons=[dict(self.answer['comparisons'][0], rejected_profile_id='outside-case')]),
                dict(comparisons=[dict(self.answer['comparisons'][0], reason=' ')])]
        for extra in bad:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                validate_feedback(dict(self.answer, **extra), self.outcomes)
        for choice in ['no', 'unsure']:
            answer = dict(self.answer, individual_comparison=choice, individual_reason='原因', group_selections=['none'])
            result = validate_feedback(answer, self.outcomes)
            self.assertIsNone(result[3]); self.assertEqual(result[-1], [])

    def test_group_selection_merge_preserves_answers_and_unfinished_null(self):
        f = self.flow
        f.post(f.payload('display', survey_version='stage5_v1'))
        f.post(f.payload('submit_fairness', survey_version='stage5_v1', **self.answer))
        before = f.rows('stage5_fairness_feedback')[0]
        with closing(sqlite3.connect(f.path)) as db:
            db.execute('CREATE TABLE stage5_group_selections (case_id TEXT, option_code TEXT, PRIMARY KEY(case_id,option_code))')
            db.executemany('INSERT INTO stage5_group_selections VALUES (?,?)', [(before['case_id'], o) for o in self.answer['group_selections']])
            db.execute('ALTER TABLE stage5_fairness_feedback DROP COLUMN group_selections_json')
            db.commit()
        Storage(f.path); Storage(f.path)
        self.assertEqual(f.rows('stage5_fairness_feedback')[0], before)
        with closing(sqlite3.connect(f.path)) as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='stage5_group_selections'").fetchone())
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_stale_and_unauthorized_submission(self):
        f = self.flow
        f.post(f.payload('display', survey_version='stage5_v1'))
        action = f.payload('submit_fairness', survey_version='stage5_v1', **self.answer)
        f.post(f.payload('claim', tab_id='new-tab')); f.post(action, 409)
        f.register(); f.post(action, 404)
        self.assertIsNone(f.rows('stage5_fairness_feedback')[0]['submitted_at'])
