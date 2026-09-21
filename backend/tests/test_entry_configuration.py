import unittest
from unittest.mock import Mock

from backend.app import create_app
import test_experiment


class EntryConfigurationTests(unittest.TestCase):
    def flow(self, refresh=False, jobs=False):
        f = test_experiment.ExperimentTests()
        f.setUp()
        self.addCleanup(f.temp.cleanup)
        f.app.config.update(PROFILE_REFRESH_ENABLED=refresh, JOB_SELECTION_ENABLED=jobs)
        f.begin()
        return f

    def test_all_combinations_through_feedback(self):
        for refresh in (False, True):
            for jobs in (False, True):
                with self.subTest(refresh=refresh, jobs=jobs):
                    f = self.flow(refresh, jobs)
                    self.assertEqual(f.state['profile_refresh_enabled'], refresh)
                    self.assertEqual(f.state['job_selection_enabled'], jobs)
                    self.assertEqual(f.rows('cases')[0]['schema_version'], 'configurable_entry_v1')
                    f.post(f.payload('display'))
                    first = f.rows('stage1_profile_views')[0]['profile_id']
                    self.assertEqual(f.app.extensions['dataset'].applicants_by_id[first]['job_id'], 'job_001')
                    if refresh:
                        request = f.payload('refresh', duration_ms=100)
                        result = f.post(request)
                        self.assertEqual(f.post(request), result)
                        f.post(f.payload('display'))
                        second = f.rows('stage1_profile_views')[-1]['profile_id']
                        self.assertNotEqual(first, second)
                        self.assertEqual(f.app.extensions['dataset'].applicants_by_id[second]['job_id'], 'job_001')
                    else:
                        f.post(f.payload('refresh', profile_refresh_enabled=True), 409)
                    f.post(f.payload('confirm_profile', duration_ms=250))
                    self.assertEqual(len(f.state['jobs']), 3 if jobs else 1)
                    f.post(f.payload('display'))
                    if not jobs:
                        f.post(f.payload('confirm_job', job_id='job_002', job_selection_enabled=True), 400)
                    choice = 'job_002' if jobs else 'job_001'
                    action = f.payload('confirm_job', job_id=choice, duration_ms=400)
                    result = f.post(action)
                    self.assertEqual(f.post(action), result)
                    self.assertEqual(f.rows('stage1_profile_selection')[0]['refresh_count'], int(refresh))
                    self.assertEqual(f.rows('stage2_job_selection')[0]['decision_duration_ms'], 400)
                    self.assertEqual(len(f.rows('stage2_job_options')), 3 if jobs else 1)
                    f.post(f.payload('display'))
                    judgments = [dict(profile_id=a['profile_id'], judgment='pass' if i < 3 else 'reject')
                                 for i, a in enumerate(f.state['applicants'])]
                    f.post(f.payload('submit_and_reveal', judgments=judgments))
                    self.assertEqual(sum(a['revealed_decision'] == 'pass' for a in f.state['applicants']), 3)
                    f.post(f.payload('display', survey_version='stage5_v1'))
                    result = f.post(f.payload('submit_fairness', survey_version='stage5_v1',
                        fairness_rating=5, group_selections=['unsure'], group_reason='暂时无法判断',
                        individual_comparison='unsure', individual_reason='需要更多信息', comparisons=[]))
                    self.assertTrue(result['feedback_saved'])

    def test_saved_flags_and_profile_survive_restart(self):
        f = self.flow()
        f.post(f.payload('display'))
        profile = f.state['profile']
        f.post(f.payload('timing', duration_ms=123))
        f.app = create_app(db_path=f.path)
        f.app.config.update(PROFILE_REFRESH_ENABLED=True, JOB_SELECTION_ENABLED=True)
        f.client = f.app.test_client()
        f.post(f.payload('claim'))
        self.assertEqual(f.state['profile'], profile)
        self.assertEqual(f.state['duration_ms'], 123)
        self.assertFalse(f.state['profile_refresh_enabled'])
        self.assertFalse(f.state['job_selection_enabled'])
        f.post(f.payload('new_session'))
        self.assertTrue(f.state['profile_refresh_enabled'])
        self.assertTrue(f.state['job_selection_enabled'])

    def test_pool_and_legacy_case(self):
        f = self.flow(True, True)
        engine = f.app.extensions['experiment']
        sampler = Mock()
        sampler.choice.side_effect = lambda values: values[0]
        engine.rng = sampler
        probe = {'configuration': {'assigned_profile_job_id': 'job_001'}}
        engine.prepare_profile(probe)
        expected = {p['profile_id'] for p in engine.dataset.applicants_by_id.values() if p['job_id'] == 'job_001'}
        self.assertEqual(set(sampler.choice.call_args.args[0]), expected)
        old = probe['profile_id']
        engine.prepare_profile(probe, old)
        self.assertEqual(set(sampler.choice.call_args.args[0]), expected - {old})
        with engine.storage.transaction() as db:
            db.execute('DELETE FROM case_configuration WHERE case_id=?', (f.state['case_id'],))
            db.execute("UPDATE cases SET schema_version='stage1_5_v1'")
        f.app.config.update(PROFILE_REFRESH_ENABLED=False, JOB_SELECTION_ENABLED=False)
        f.post(f.payload('claim'))
        f.post(f.payload('display'))
        legacy_profile = f.rows('stage1_profile_views')[-1]['profile_id']
        f.post(f.payload('refresh'))
        self.assertEqual(set(sampler.choice.call_args.args[0]), set(engine.dataset.applicants_by_id) - {legacy_profile})
        f.post(f.payload('display'))
        f.post(f.payload('confirm_profile'))
        self.assertEqual(len(f.state['jobs']), 3)
        self.assertEqual(f.rows('cases')[0]['schema_version'], 'stage1_5_v1')
