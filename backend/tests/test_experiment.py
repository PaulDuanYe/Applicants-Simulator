import json
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import Mock

from backend.app import create_app


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'research.sqlite3'
        self.app = create_app(db_path=self.path)
        self.app.config.update(PROFILE_REFRESH_ENABLED=True, JOB_SELECTION_ENABLED=True)
        self.client = self.app.test_client()
        self.token = ''
        self.tab = 'first-tab'
        self.state = None

    def payload(self, op, **extra):
        body = dict(op=op, action_id=str(uuid.uuid4()), tab_id=self.tab,
                    at='2026-09-13T09:00:00.000Z')
        if self.state:
            body.update(case_id=self.state['case_id'], revision=self.state['revision'],
                        presentation_id=self.state['presentation_id'], duration_ms=0)
        body.update(extra)
        return body

    def post(self, body, status=200, token=None):
        response = self.client.post('/api/action', json=body,
                                    headers={'Authorization': 'Bearer ' + (self.token if token is None else token)})
        self.assertEqual(response.status_code, status, response.get_data(as_text=True))
        if status == 200:
            result = response.json
            for private in ('results', 'score'):
                self.assertNotIn('"' + private + '"', json.dumps(result))
            if 'token' in result:
                self.token = result['token']
            if 'case_id' in result:
                self.state = result
            return result
        return response.json

    def register(self):
        return self.post(self.payload('register'))

    def begin(self):
        self.register()
        return self.post(self.payload('new_session'))

    def rows(self, table):
        with self.app.extensions['experiment'].storage.transaction() as db:
            return [dict(r) for r in db.execute(f'SELECT * FROM {table}')]

    def test_full_flow_snapshots_counts_and_private_data(self):
        self.begin()
        self.assertEqual(self.rows('stage1_profile_views'), [])
        self.post(self.payload('display'))
        first = self.rows('stage1_profile_views')[0]
        refresh = self.payload('refresh', duration_ms=1200)
        next_view = self.post(refresh)
        self.assertEqual(self.post(refresh), next_view)
        self.post(self.payload('display'))
        views = self.rows('stage1_profile_views')
        self.assertNotEqual(first['profile_id'], views[1]['profile_id'])
        self.post(self.payload('confirm_profile', duration_ms=2300))
        self.assertEqual(self.rows('stage2_job_options'), [])
        jobs = self.state['jobs']
        self.post(self.payload('display'))
        self.assertEqual({j['job_id'] for j in jobs}, {'job_001', 'job_002', 'job_003'})
        self.post(self.payload('confirm_job', job_id=jobs[0]['job_id'], duration_ms=5000))
        s1 = self.rows('stage1_profile_selection')[0]
        self.assertEqual(s1['refresh_count'], 1)
        self.assertEqual(s1['confirmation_duration_ms'], 3500)
        self.assertEqual(s1['confirmed_profile_id'], views[1]['profile_id'])
        self.assertEqual(json.loads(views[1]['displayed_profile_json']), self.state['profile'])
        s2 = self.rows('stage2_job_selection')[0]
        self.assertEqual(s2['decision_duration_ms'], 5000)
        self.assertEqual(s2['selected_job_id'], jobs[0]['job_id'])
        options = self.rows('stage2_job_options')
        self.assertEqual([o['job_id'] for o in options], [j['job_id'] for j in jobs])
        for option, job in zip(options, jobs):
            self.assertEqual(json.loads(option['displayed_job_json']), {k: job[k] for k in ('title', 'description')})
        for key in ('decision', 'results', 'score', 'original_job_id', 'profile_id', 'provenance'):
            self.assertNotIn('"' + key + '"', json.dumps(next_view))
        self.post(self.payload('confirm_profile'), 409)
        self.post(self.payload('end_session'), 409)
        self.post(self.payload('display'))
        self.post(self.payload('submit_judgments', judgments=[dict(profile_id=a['profile_id'], judgment='pass' if i < 3 else 'reject') for i,a in enumerate(self.state['applicants'])]))
        self.post(self.payload('reveal_outcomes'))
        self.post(self.payload('display'))
        ended = self.post(self.payload('end_session'))
        self.assertIsNone(ended['active'])

    def test_identity_retry_and_session_repetition(self):
        registration = self.payload('register')
        person = self.post(registration)
        self.assertEqual(self.post(registration), person)
        first_session_action = self.payload('new_session')
        first = self.post(first_session_action)
        self.assertEqual(self.post(first_session_action), first)
        self.post(self.payload('display'))
        self.post(self.payload('timing', duration_ms=777))
        login = self.post(self.payload('login', code=person['participant_code'].lower()))
        self.assertEqual(login['participant_id'], person['participant_id'])
        self.post(self.payload('claim'))
        self.assertEqual(self.state['duration_ms'], 777)
        second = self.post(self.payload('new_session'))
        self.assertNotEqual(first['case_id'], second['case_id'])
        self.assertEqual(len(self.rows('participants')), 1)
        self.assertEqual(len(self.rows('sessions')), 2)
        self.assertIsNotNone(self.rows('sessions')[0]['ended_at'])
        self.assertEqual([c['case_number'] for c in self.rows('cases')], [1, 1])
        self.assertEqual(self.rows('stage1_profile_views')[0]['duration_ms'], 777)

    def test_restart_resume_and_duplicate_checkpoint(self):
        self.begin()
        self.post(self.payload('display'))
        checkpoint = self.payload('timing', duration_ms=400)
        self.post(checkpoint)
        self.post(checkpoint)
        self.post(self.payload('timing', duration_ms=200))
        self.assertEqual(self.rows('stage1_profile_views')[0]['duration_ms'], 400)
        self.app = create_app(db_path=self.path)
        self.client = self.app.test_client()
        self.post(self.payload('claim', tab_id='reload'))
        self.tab = 'reload'
        self.assertEqual(self.state['duration_ms'], 400)
        self.post(self.payload('display'))
        self.assertEqual(len(self.rows('stage1_profile_views')), 1)
        self.post(self.payload('confirm_profile', duration_ms=600))
        jobs = self.state['jobs']
        self.post(self.payload('display'))
        self.post(self.payload('claim', tab_id='another-reload'))
        self.assertEqual(self.state['jobs'], jobs)

    def test_ownership_and_stale_tabs(self):
        self.begin()
        self.post(self.payload('display'))
        stale = self.payload('refresh', duration_ms=10)
        self.post(self.payload('claim', tab_id='other-tab'))
        self.post(stale, 409)
        owner_token = self.token
        owner_state = self.state
        self.state = None
        other = self.register()
        self.state = owner_state
        self.post(self.payload('claim'), 404)
        self.assertEqual(len(self.rows('participants')), 2)
        self.assertNotEqual(owner_token, other['token'])
        self.post(self.payload('claim'), 401, token='bad-token')

    def test_validation_and_atomic_rollback(self):
        self.begin()
        self.post(self.payload('refresh'), 409)
        self.post(self.payload('display'))
        for duration in (-1, True, 1.5, '4'):
            self.post(self.payload('timing', duration_ms=duration), 400)
        self.post(self.payload('confirm_job', job_id='job_001'), 409)
        self.post(self.payload('confirm_profile', duration_ms=12))
        self.post(self.payload('display'))
        self.post(self.payload('confirm_job', job_id='unknown', duration_ms=10000), 400)
        self.assertEqual(self.rows('stage2_job_selection')[0]['decision_duration_ms'], 0)
        changed = self.payload('timing', duration_ms=5)
        self.post(changed)
        changed['duration_ms'] = 8
        self.post(changed, 409)

    def test_sampling_pool_ignores_screening_and_excludes_only_current(self):
        self.begin()
        engine = self.app.extensions['experiment']
        sampler = Mock()
        sampler.choice.side_effect = lambda values: values[0]
        engine.rng = sampler
        probe = {}
        engine.prepare_profile(probe)
        self.assertEqual(set(sampler.choice.call_args.args[0]), set(engine.dataset.applicants_by_id))
        previous = probe['profile_id']
        engine.prepare_profile(probe, previous)
        choices = sampler.choice.call_args.args[0]
        self.assertEqual(len(choices), 49)
        self.assertNotIn(previous, choices)


    def setup_competition(self, outcome='pass', alternative=False):
        self.app.config.update(PROFILE_REFRESH_ENABLED=True, JOB_SELECTION_ENABLED=True)
        self.register()
        engine = self.app.extensions['experiment']
        profile = next(p for p in engine.dataset.applicants_by_id.values() if p['results']['decision'] == outcome)
        import random
        engine.rng = random.Random(42)
        from unittest.mock import patch
        with patch.object(engine.rng, 'choice', return_value=profile['profile_id']):
            self.post(self.payload('new_session'))
        self.post(self.payload('display'))
        self.post(self.payload('confirm_profile', duration_ms=100))
        self.post(self.payload('display'))
        job_id = next(j for j in engine.dataset.jobs_by_id if j != profile['job_id']) if alternative else profile['job_id']
        action = self.payload('confirm_job', job_id=job_id, duration_ms=200)
        result = self.post(action)
        self.assertEqual(self.post(action), result)
        return profile, job_id

    def test_competition_three_branches_and_hidden_results(self):
        for outcome, alternative in [('pass', False), ('reject', False), ('pass', True)]:
            with self.subTest(outcome=outcome, alternative=alternative):
                profile, job_id = self.setup_competition(outcome, alternative)
                rows = [r for r in self.rows('stage3_applicants') if r['case_id'] == self.state['case_id']]
                self.assertEqual(len(rows), 6)
                self.assertEqual(len({r['profile_id'] for r in rows}), 6)
                self.assertTrue(all('case_decision' not in r and 'source_decision' not in r and 'decision_basis' not in r for r in rows))
                self.assertEqual(rows[0]['profile_id'], profile['profile_id'])
                self.assertFalse(any(r['case_id'] == self.state['case_id'] for r in self.rows('stage4_applicant_outcomes')))
                for row in rows[1:]:
                    self.assertEqual(self.app.extensions['dataset'].applicants_by_id[row['profile_id']]['job_id'], job_id)
                for forbidden in ('source_decision', 'case_decision', 'decision_basis', 'participant_judgment'):
                    self.assertNotIn(forbidden, json.dumps(self.state))
                self.assertIsNone(self.rows('stage3_competition_assessment')[-1]['started_at'])
                self.post(self.payload('display'))
                stale = self.payload('timing', duration_ms=50)
                before = self.state['applicants']
                self.app = create_app(db_path=self.path); self.client = self.app.test_client()
                self.post(self.payload('claim', tab_id='new-writer'))
                self.tab = 'new-writer'
                self.assertEqual(before, self.state['applicants'])
                self.post(stale, 409)

    def test_competition_judgment_validation_and_idempotence(self):
        self.setup_competition()
        self.post(self.payload('display'))
        valid = [dict(profile_id=a['profile_id'], judgment='pass' if i<3 else 'reject') for i,a in enumerate(self.state['applicants'])]
        invalids = [valid[:5], valid[:5]+[valid[0]],
                    [dict(x, judgment='pass') for x in valid],
                    [dict(valid[0], profile_id='unknown')]+valid[1:],
                    [dict(valid[0], judgment='fail')]+valid[1:]]
        for invalid in invalids:
            self.post(self.payload('submit_judgments', judgments=invalid, duration_ms=100), 400)
        self.assertTrue(all(r['participant_judgment'] is None for r in self.rows('stage3_applicants')))
        checkpoint = self.payload('timing', duration_ms=500)
        self.post(checkpoint); self.post(checkpoint)
        submit = self.payload('submit_judgments', judgments=valid, duration_ms=700)
        result = self.post(submit)
        self.assertEqual(self.post(submit), result)
        self.assertEqual(result['phase'], 'judged')
        self.assertEqual(self.rows('stage3_competition_assessment')[0]['judgment_duration_ms'], 700)
        self.assertEqual(sum(r['participant_judgment']=='pass' for r in self.rows('stage3_applicants')),3)
        self.post(self.payload('submit_judgments', judgments=valid),409)

    def test_legacy_saved_case_upgrade_and_ended_session_preservation(self):
        self.setup_competition()
        engine = self.app.extensions['experiment']
        with engine.storage.transaction() as db:
            case_id = self.state['case_id']
            db.execute('DELETE FROM stage4_historical_inputs WHERE case_id=?',(case_id,))
            db.execute('DELETE FROM stage3_applicants WHERE case_id=?',(case_id,))
            db.execute('DELETE FROM stage3_competition_assessment WHERE case_id=?',(case_id,))
            state = json.loads(db.execute('SELECT state_json FROM technical_case_state WHERE case_id=?',(case_id,)).fetchone()[0])
            state['phase']='saved'
            engine.save(db,case_id,state)
            db.execute("UPDATE cases SET schema_version='stage1_2_v1' WHERE case_id=?",(case_id,))
        self.post(self.payload('claim'))
        self.assertEqual(self.state['phase'],'competition')
        self.assertEqual(len(self.rows('stage3_applicants')),6)
        self.assertEqual(self.rows('cases')[0]['schema_version'],'stage1_2_v1')
        with engine.storage.transaction() as db:
            db.execute("UPDATE sessions SET ended_at='2026-09-13T10:00:00Z'")
        self.post(self.payload('claim'),409)

    def test_insufficient_competitor_pool_rolls_back(self):
        self.begin(); self.post(self.payload('display')); self.post(self.payload('confirm_profile')); self.post(self.payload('display'))
        engine=self.app.extensions['experiment']
        job_id=self.state['jobs'][0]['job_id']
        engine.dataset.applicants_by_job_and_decision[job_id]={'pass':[], 'reject':[]}
        self.post(self.payload('confirm_job',job_id=job_id),409)
        self.assertIsNone(self.rows('stage2_job_selection')[0]['submitted_at'])
        self.assertEqual(self.rows('stage3_applicants'),[])

    def test_historical_revelation_branches_persistence_and_timing(self):
        for outcome, alternative in [('pass', False), ('reject', False), ('pass', True), ('reject', True)]:
            with self.subTest(outcome=outcome, alternative=alternative):
                self.setup_competition(outcome, alternative)
                case_id = self.state['case_id']
                self.post(self.payload('reveal_outcomes'), 409)
                self.post(self.payload('display'))
                public = self.state['applicants']
                judgments = [dict(profile_id=a['profile_id'], judgment='pass' if i < 3 else 'reject') for i, a in enumerate(public)]
                self.post(self.payload('submit_judgments', judgments=judgments))
                self.assertNotIn('applicants', self.state)
                self.assertFalse(any(r['case_id'] == case_id for r in self.rows('stage4_outcome_revelation')))
                self.post(self.payload('end_session'), 409)
                # Even changed in-memory dataset decisions cannot alter saved historical retrieval.
                for p in self.app.extensions['dataset'].applicants_by_id.values():
                    p['results']['decision'] = 'reject' if p['results']['decision'] == 'pass' else 'pass'
                reveal = self.payload('reveal_outcomes')
                result = self.post(reveal)
                self.assertEqual(self.post(reveal), result)
                self.assertEqual([a['profile_id'] for a in result['applicants']], [a['profile_id'] for a in public])
                self.assertEqual(sum(a['revealed_decision'] == 'pass' for a in result['applicants']), 3)
                self.assertEqual([a['participant_judgment'] for a in result['applicants']], [j['judgment'] for j in judgments])
                stored = [r for r in self.rows('stage4_applicant_outcomes') if r['case_id'] == case_id]
                source = [r for r in self.rows('stage3_applicants') if r['case_id'] == case_id]
                self.assertEqual(len(stored), 6)
                for row in source:
                    actual = next(r for r in stored if r['profile_id'] == row['profile_id'])
                    historical = next(r for r in self.rows('stage4_historical_inputs') if r['case_id'] == case_id and r['profile_id'] == row['profile_id'])
                    override = alternative and row['applicant_role'] == 'participant'
                    self.assertEqual(actual['revealed_decision'], 'reject' if override else historical['source_decision'])
                    self.assertEqual(actual['decision_basis'], 'historical')
                    self.assertEqual(actual['applied_rule'], 'alternative_job_rejection' if override else None)
                    self.assertNotIn('method_decision', actual)
                self.assertIsNone(self.rows('stage4_outcome_revelation')[-1]['revealed_at'])
                self.post(self.payload('end_session'), 409)
                self.post(self.payload('display'))
                first = self.rows('stage4_outcome_revelation')[-1]['revealed_at']
                self.post(self.payload('display', at='2026-09-14T10:00:00Z'))
                self.assertEqual(self.rows('stage4_outcome_revelation')[-1]['revealed_at'], first)
                self.post(self.payload('timing', duration_ms=500))
                stale = self.payload('timing', duration_ms=999)
                self.app = create_app(db_path=self.path); self.client = self.app.test_client()
                self.post(self.payload('claim'))
                self.post(stale, 409)
                self.assertEqual(self.state['applicants'], result['applicants'])
                self.assertEqual(self.state['duration_ms'], 500)
                self.post(self.payload('reveal_outcomes'))
                self.assertEqual([r for r in self.rows('stage4_applicant_outcomes') if r['case_id'] == case_id], stored)
                ending = self.payload('end_session', duration_ms=800)
                self.assertIsNone(self.post(ending)['active'])
                self.post(ending)
                final = self.rows('stage4_outcome_revelation')[-1]
                self.assertEqual(final['duration_ms'], 800)
                self.assertIsNotNone(final['continued_at'])

    def test_outcome_methods_and_rule_validation(self):
        from backend.outcomes import generate_outcomes
        from backend.outcomes.rules import resolve_case_outcomes
        for method in ('llm', 'matrix', 'random_method'):
            with self.assertRaises(NotImplementedError):
                generate_outcomes(method, [])
        with self.assertRaises(ValueError):
            generate_outcomes('unknown', [])
        self.setup_competition()
        records = self.rows('stage3_applicants')
        with self.assertRaisesRegex(ValueError, 'snapshots are required'):
            generate_outcomes('historical', records)
        with self.assertRaisesRegex(ValueError, 'do not match'):
            generate_outcomes('historical', records, method_data=[])
        results = generate_outcomes('historical', records, method_data=self.rows('stage4_historical_inputs'))
        results[records[0]['profile_id']] = 'reject'
        with self.assertRaises(ValueError):
            resolve_case_outcomes(records, results, False)

    def test_revelation_authorization_and_failed_method_is_atomic(self):
        self.setup_competition()
        self.post(self.payload('display'))
        judgments = [dict(profile_id=a['profile_id'], judgment='pass' if i < 3 else 'reject')
                     for i, a in enumerate(self.state['applicants'])]
        self.post(self.payload('submit_judgments', judgments=judgments))
        engine = self.app.extensions['experiment']
        engine.outcome_method = 'matrix'
        self.post(self.payload('reveal_outcomes'), 409)
        self.assertEqual(self.rows('stage4_outcome_revelation'), [])
        self.assertEqual(self.rows('stage4_applicant_outcomes'), [])
        engine.outcome_method = 'historical'
        owner_token = self.token
        self.register()
        self.post(self.payload('reveal_outcomes'), 404)
        self.token = owner_token
        stale = self.payload('reveal_outcomes')
        self.post(self.payload('claim'))
        self.post(stale, 409)
        self.post(self.payload('reveal_outcomes'))
        self.assertEqual(len(self.rows('stage4_applicant_outcomes')), 6)

    def test_combined_submission_validation_rollback_retry_and_lock(self):
        self.setup_competition(alternative=True)
        self.post(self.payload('display'))
        judgments = [dict(profile_id=a['profile_id'], judgment='pass' if i < 3 else 'reject')
                     for i, a in enumerate(self.state['applicants'])]
        self.post(self.payload('submit_and_reveal', judgments=judgments[:5]), 400)
        engine = self.app.extensions['experiment']
        engine.outcome_method = 'matrix'
        action = self.payload('submit_and_reveal', judgments=judgments, duration_ms=1234)
        self.post(action, 409)
        self.assertTrue(all(a['participant_judgment'] is None for a in self.rows('stage3_applicants')))
        self.assertIsNone(self.rows('stage3_competition_assessment')[0]['submitted_at'])
        self.assertEqual(self.rows('stage4_applicant_outcomes'), [])
        engine.outcome_method = 'historical'
        result = self.post(action)
        self.assertEqual(result['phase'], 'outcomes')
        self.assertEqual(self.post(action), result)
        self.assertEqual(self.rows('stage3_competition_assessment')[0]['judgment_duration_ms'], 1234)
        self.assertEqual([a['participant_judgment'] for a in result['applicants']], [j['judgment'] for j in judgments])
        self.assertEqual(sum(a['revealed_decision'] == 'pass' for a in result['applicants']), 3)
        self.assertIsNone(self.rows('stage4_outcome_revelation')[0]['revealed_at'])
        self.post(self.payload('submit_and_reveal', judgments=judgments), 409)
        self.post(self.payload('submit_judgments', judgments=judgments), 409)
        self.post(self.payload('display'))
        self.assertIsNotNone(self.rows('stage4_outcome_revelation')[0]['revealed_at'])
        self.app = create_app(db_path=self.path); self.client = self.app.test_client()
        self.post(self.payload('claim'))
        self.assertEqual(self.state['applicants'], result['applicants'])
