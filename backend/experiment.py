"""Stage 1–4 coordination. Outcomes stay private until explicitly requested."""
import hashlib
import json
import random
import secrets
import uuid
from datetime import datetime, timezone

if __package__:
    from .fairness import validate_feedback
else:
    from fairness import validate_feedback

if __package__:
    from .outcomes import generate_outcomes
    from .outcomes.rules import resolve_case_outcomes
else:
    from outcomes import generate_outcomes
    from outcomes.rules import resolve_case_outcomes


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


class ExperimentError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


def require(condition, message, status=400):
    if not condition:
        raise ExperimentError(message, status)


def text_field(data, key):
    value = data.get(key)
    require(isinstance(value, str) and 0 < len(value) <= 200, '信息不完整，请刷新页面后重试。')
    return value


def timestamp(data):
    value = text_field(data, 'at')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(parsed.tzinfo is not None, '未能保存时间，请刷新页面重试。')
        return parsed.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    except ValueError:
        raise ExperimentError('未能保存时间，请刷新页面重试。')


class Experiment:
    def __init__(self, dataset, storage, rng=None, settings=None):
        self.dataset, self.storage = dataset, storage
        self.settings = settings if settings is not None else {}
        self.rng = rng or random.SystemRandom()
        self.outcome_method = 'historical'

    def authenticate(self, db, token):
        row = db.execute('SELECT participant_id FROM technical_credentials WHERE token_hash=?',
                         (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        require(row is not None, '请重新输入参与代码。', 401)
        return row['participant_id']

    def hub(self, db, participant):
        person = db.execute('SELECT * FROM participants WHERE participant_id=?', (participant,)).fetchone()
        active = db.execute('SELECT s.session_id,c.case_id FROM sessions s JOIN cases c USING(session_id) '
                            'WHERE s.participant_id=? AND s.ended_at IS NULL ORDER BY s.started_at DESC LIMIT 1',
                            (participant,)).fetchone()
        return {'participant_id': participant, 'participant_code': person['participant_code'],
                'active': dict(active) if active else None}

    def me(self, token):
        with self.storage.transaction() as db:
            return self.hub(db, self.authenticate(db, token))

    def own_case(self, db, participant, case_id):
        row = db.execute('SELECT c.session_id,s.ended_at FROM cases c JOIN sessions s USING(session_id) '
                         'WHERE c.case_id=? AND s.participant_id=?', (case_id, participant)).fetchone()
        require(row is not None, '未找到你的参与记录，请重新输入参与代码。', 404)
        require(row['ended_at'] is None, '本次参与已结束，请返回首页。', 409)
        state = json.loads(db.execute('SELECT state_json FROM technical_case_state WHERE case_id=?',
                                    (case_id,)).fetchone()[0])
        configuration = db.execute('SELECT * FROM case_configuration WHERE case_id=?', (case_id,)).fetchone()
        if configuration:
            state['configuration'] = {key: configuration[key] for key in
                                      ('profile_refresh_enabled', 'job_selection_enabled', 'assigned_profile_job_id')}
        else:
            state.pop('configuration', None)
        return row['session_id'], state

    def save(self, db, case_id, state):
        db.execute('INSERT OR REPLACE INTO technical_case_state VALUES (?,?)', (case_id, encode(state)))

    def view(self, case_id, state):
        # Explicit allowlist: original-job linkage stays internal even before confirmation.
        result = {k: state[k] for k in ('phase', 'revision', 'presentation_id', 'ack', 'duration_ms')}
        result.update(case_id=case_id, profile=state['profile'])
        result.update({key: bool(state.get('configuration', {}).get(key, True)) for key in
                       ('profile_refresh_enabled', 'job_selection_enabled')})
        if state['phase'] == 'job':
            result['jobs'] = state['jobs']
        if state['phase'] == 'competition':
            result.update(applicants=state['applicants'], selected_job=state['selected_job'])
        if state['phase'] == 'outcomes':
            result.update(applicants=state['outcomes'], selected_job=state['selected_job'])
            result.update(survey_version='stage5_v1', survey_ack=state.get('survey_ack', False))
        return result

    def prepare_profile(self, state, exclude=None):
        job_id = state.get('configuration', {}).get('assigned_profile_job_id')
        ids = [p for p, record in self.dataset.applicants_by_id.items()
               if p != exclude and (job_id is None or record['job_id'] == job_id)]
        profile_id = self.rng.choice(ids)
        record = self.dataset.applicants_by_id[profile_id]
        state.update(profile_id=profile_id, original_job_id=record['job_id'],
                     profile={k: record[k] for k in ('job_related_attributes', 'protected_attributes')},
                     presentation_id=uid(), ack=False, duration_ms=0)

    def action(self, data, token):
        require(type(data) is dict, '未能读取提交内容，请刷新页面后重试。')
        action_id, op = text_field(data, 'action_id'), text_field(data, 'op')
        # An unguessable request ID is also the retry capability for first-time creation.
        try:
            uuid.UUID(action_id)
        except ValueError:
            raise ExperimentError('未能识别这次操作，请刷新页面后重试。')
        with self.storage.transaction() as db:
            participant = None if op in ('register', 'login') else self.authenticate(db, token)
            scope = participant or 'identity'
            receipt = db.execute('SELECT * FROM technical_receipts WHERE scope=? AND action_id=?',
                                 (scope, action_id)).fetchone()
            request_json = encode(data)
            if receipt:
                require(receipt['request_json'] == request_json, '页面操作发生冲突，请刷新后继续。', 409)
                return json.loads(receipt['response_json'])
            if op in ('register', 'login'):
                if op == 'register':
                    participant = uid()
                    while True:
                        code = secrets.token_hex(8).upper()
                        code = '-'.join(code[i:i+4] for i in range(0, 16, 4))
                        if not db.execute('SELECT 1 FROM participants WHERE participant_code=?', (code,)).fetchone():
                            break
                    db.execute('INSERT INTO participants VALUES (?,?,?)', (participant, code, now()))
                else:
                    code = text_field(data, 'code').strip().upper()
                    row = db.execute('SELECT participant_id FROM participants WHERE participant_code=?', (code,)).fetchone()
                    require(row is not None, '参与代码不存在，请检查后重试。', 404)
                    participant = row[0]
                credential = secrets.token_urlsafe(32)
                db.execute('INSERT INTO technical_credentials VALUES (?,?)',
                           (hashlib.sha256(credential.encode()).hexdigest(), participant))
                result = dict(self.hub(db, participant), token=credential)
            elif op == 'new_session':
                db.execute('UPDATE sessions SET ended_at=? WHERE participant_id=? AND ended_at IS NULL', (now(), participant))
                session_id, case_id = uid(), uid()
                db.execute('INSERT INTO sessions VALUES (?,?,?,NULL)', (session_id, participant, now()))
                db.execute('INSERT INTO cases VALUES (?,?,1,?,?,?)', (case_id, session_id, now(), 'configurable_entry_v1', 'visible_page'))
                state = dict(phase='profile', revision=0, owner=text_field(data, 'tab_id'), view_number=1)
                state['configuration'] = dict(
                    profile_refresh_enabled=bool(self.settings.get('PROFILE_REFRESH_ENABLED', False)),
                    job_selection_enabled=bool(self.settings.get('JOB_SELECTION_ENABLED', False)),
                    assigned_profile_job_id='job_001')
                db.execute('INSERT INTO case_configuration VALUES (?,?,?,?)',
                           (case_id, state['configuration']['profile_refresh_enabled'],
                            state['configuration']['job_selection_enabled'], 'job_001'))
                self.prepare_profile(state)
                self.save(db, case_id, state)
                result = self.view(case_id, state)
            else:
                case_id = text_field(data, 'case_id')
                session_id, state = self.own_case(db, participant, case_id)
                if op == 'claim':
                    if state['phase'] == 'saved':
                        self.prepare_competition(db, case_id, state)
                    if state['phase'] == 'judged':
                        self.prepare_outcomes(db, case_id, state)
                    state['owner'] = text_field(data, 'tab_id')
                    state['revision'] += 1
                else:
                    require(data.get('tab_id') == state['owner'] and type(data.get('revision')) is int
                            and data['revision'] == state['revision'], '你已在其他页面继续操作，请刷新当前页面。', 409)
                    if op == 'submit_fairness':
                        self.case_action(db, case_id, state, data, op)
                        db.execute('UPDATE sessions SET ended_at=? WHERE session_id=?', (now(), session_id))
                    elif op == 'end_session':
                        require(state['phase'] == 'outcomes', '请先查看筛选结果，再完成后续操作。', 409)
                        self.case_action(db, case_id, state, data, op)
                        db.execute('UPDATE sessions SET ended_at=? WHERE session_id=?', (now(), session_id))
                    else:
                        self.case_action(db, case_id, state, data, op)
                    state['revision'] += 1
                self.save(db, case_id, state)
                result = self.hub(db, participant) if op in ('end_session', 'submit_fairness') else self.view(case_id, state)
                if op == 'submit_fairness':
                    result['feedback_saved'] = True
            db.execute('INSERT INTO technical_receipts VALUES (?,?,?,?)',
                       (scope, action_id, request_json, encode(result)))
            return result

    def case_action(self, db, case_id, state, data, op):
        require(data.get('presentation_id') == state['presentation_id'], '页面内容已更新，请刷新后继续。', 409)
        if op == 'reveal_outcomes':
            require(state['phase'] in ('judged', 'outcomes'), '请先完成并提交六人的判断。', 409)
            return self.prepare_outcomes(db, case_id, state)
        if state['phase'] == 'outcomes':
            return self.outcome_action(db, case_id, state, data, op)
        require(state['phase'] in ('profile', 'job', 'competition'), '判断已提交，不能再修改。', 409)
        if state['phase'] == 'competition':
            return self.competition_action(db, case_id, state, data, op)
        if op == 'display':
            if not state['ack']:
                at = timestamp(data)
                if state['phase'] == 'profile':
                    db.execute('INSERT OR IGNORE INTO stage1_profile_selection (case_id,started_at) VALUES (?,?)', (case_id, at))
                    db.execute('INSERT INTO stage1_profile_views VALUES (?,?,?,?,?,NULL,0,NULL)',
                               (case_id, state['view_number'], state['profile_id'], encode(state['profile']), at))
                else:
                    db.execute('INSERT INTO stage2_job_selection VALUES (?,?,NULL,?,NULL,0)', (case_id, at, state['original_job_id']))
                    for position, job in enumerate(state['jobs'], 1):
                        db.execute('INSERT INTO stage2_job_options VALUES (?,?,?,?)',
                                   (case_id, position, job['job_id'], encode({k: job[k] for k in ('title', 'description')})))
                state['ack'] = True
            return
        require(state['ack'], '页面正在加载，请稍候。', 409)
        require(op in ('timing', 'refresh', 'confirm_profile', 'confirm_job'), '暂时无法完成这项操作，请刷新后重试。')
        duration = data.get('duration_ms')
        require(type(duration) is int and 0 <= duration <= 9007199254740991, '未能保存本次进度，请刷新页面重试。')
        state['duration_ms'] = max(state['duration_ms'], duration)
        if state['phase'] == 'profile':
            require(op in ('timing', 'refresh', 'confirm_profile'), '请先选择要使用的简历。', 409)
            require(op != 'refresh' or state.get('configuration', {}).get('profile_refresh_enabled', True),
                    '本次参与不能更换简历，请阅读后继续。', 409)
            db.execute('UPDATE stage1_profile_views SET duration_ms=? WHERE case_id=? AND view_number=?',
                       (state['duration_ms'], case_id, state['view_number']))
            if op == 'timing':
                return
            at = timestamp(data)
            reason = 'refresh' if op == 'refresh' else 'confirm'
            db.execute('UPDATE stage1_profile_views SET ended_at=?,ended_by=? WHERE case_id=? AND view_number=?',
                       (at, reason, case_id, state['view_number']))
            if op == 'refresh':
                db.execute('UPDATE stage1_profile_selection SET refresh_count=refresh_count+1 WHERE case_id=?', (case_id,))
                state['view_number'] += 1
                self.prepare_profile(state, exclude=state['profile_id'])
            else:
                total = db.execute('SELECT SUM(duration_ms) FROM stage1_profile_views WHERE case_id=?', (case_id,)).fetchone()[0]
                db.execute('UPDATE stage1_profile_selection SET confirmed_at=?,confirmed_profile_id=?,confirmation_duration_ms=? WHERE case_id=?',
                           (at, state['profile_id'], total, case_id))
                jobs = [{k: j[k] for k in ('job_id', 'title', 'description')} for j in self.dataset.jobs_by_id.values()]
                if not state.get('configuration', {}).get('job_selection_enabled', True):
                    jobs = [j for j in jobs if j['job_id'] == state['configuration']['assigned_profile_job_id']]
                self.rng.shuffle(jobs)
                state.update(phase='job', jobs=jobs, ack=False, presentation_id=uid(), duration_ms=0)
        else:
            require(op in ('timing', 'confirm_job'), '简历已确认，不能再更换。', 409)
            db.execute('UPDATE stage2_job_selection SET decision_duration_ms=? WHERE case_id=?', (state['duration_ms'], case_id))
            if op == 'confirm_job':
                job_id = text_field(data, 'job_id')
                require(job_id in [j['job_id'] for j in state['jobs']], '请选择已提供的岗位。')
                db.execute('UPDATE stage2_job_selection SET submitted_at=?,selected_job_id=? WHERE case_id=?',
                           (timestamp(data), job_id, case_id))
                self.prepare_competition(db, case_id, state)


    def prepare_competition(self, db, case_id, state):
        # Called inside the same transaction as job confirmation or legacy resume.
        existing = db.execute('SELECT * FROM stage3_competition_assessment WHERE case_id=?', (case_id,)).fetchone()
        if existing is None:
            choice = db.execute('SELECT * FROM stage2_job_selection WHERE case_id=?', (case_id,)).fetchone()
            require(choice is not None and choice['submitted_at'] is not None, '请先确认岗位。', 409)
            job_id = choice['selected_job_id']
            player = self.dataset.applicants_by_id.get(state['profile_id'])
            require(player is not None, '无法读取你选择的简历，请联系工作人员。', 409)
            alternative = job_id != choice['original_job_id']
            decision = 'reject' if alternative else player['results']['decision']
            groups = self.dataset.applicants_by_job_and_decision.get(job_id, {})
            competitors = []
            for outcome in ('pass', 'reject'):
                count = 3 - int(decision == outcome)
                pool = [p for p in groups.get(outcome, []) if p['profile_id'] != player['profile_id']]
                require(len(pool) >= count, '暂时无法加载六位申请者的资料，请联系工作人员。', 409)
                competitors.extend(self.rng.sample(pool, count))
            self.rng.shuffle(competitors)
            records = [(player, 'participant')] + [(p, 'competitor') for p in competitors]
            require(len({p['profile_id'] for p, _ in records}) == 6, '申请者资料加载失败，请联系工作人员。', 409)
            job = db.execute('SELECT displayed_job_json FROM stage2_job_options WHERE case_id=? AND job_id=?',
                             (case_id, job_id)).fetchone()
            require(job is not None, '岗位资料加载失败，请刷新后重试。', 409)
            db.execute('INSERT INTO stage3_competition_assessment (case_id,selected_job_id,displayed_job_json,prepared_at) VALUES (?,?,?,?)',
                       (case_id, job_id, job[0], now()))
            for position, (profile, role) in enumerate(records, 1):
                snapshot = state['profile'] if role == 'participant' else {
                    k: profile[k] for k in ('job_related_attributes', 'protected_attributes')}
                db.execute('INSERT INTO stage3_applicants VALUES (?,?,?,?,?,NULL)',
                           (case_id, position, profile['profile_id'], role, encode(snapshot)))
                # Freeze method-specific inputs without computing or recording common outcomes.
                db.execute('INSERT INTO stage4_historical_inputs VALUES (?,?,?)',
                           (case_id, profile['profile_id'], profile['results']['decision']))
            existing = db.execute('SELECT * FROM stage3_competition_assessment WHERE case_id=?', (case_id,)).fetchone()
        applicants = db.execute('SELECT display_position,profile_id,applicant_role,displayed_profile_json '
                                'FROM stage3_applicants WHERE case_id=? ORDER BY display_position', (case_id,)).fetchall()
        state.update(phase='judged' if existing['submitted_at'] else 'competition',
                     presentation_id=uid(), ack=existing['started_at'] is not None,
                     duration_ms=existing['judgment_duration_ms'],
                     selected_job=json.loads(existing['displayed_job_json']),
                     applicants=[dict(display_position=p['display_position'], profile_id=p['profile_id'],
                                      applicant_role=p['applicant_role'], profile=json.loads(p['displayed_profile_json'])) for p in applicants])

    def prepare_outcomes(self, db, case_id, state):
        assessment = db.execute('SELECT * FROM stage3_competition_assessment WHERE case_id=?', (case_id,)).fetchone()
        applicants = db.execute('SELECT * FROM stage3_applicants WHERE case_id=? ORDER BY display_position', (case_id,)).fetchall()
        require(assessment is not None and assessment['submitted_at'] is not None and len(applicants) == 6
                and all(a['participant_judgment'] in ('pass', 'reject') for a in applicants), '请先完成并提交六人的判断。', 409)
        saved = db.execute('SELECT * FROM stage4_outcome_revelation WHERE case_id=?', (case_id,)).fetchone()
        if saved is None:
            choice = db.execute('SELECT * FROM stage2_job_selection WHERE case_id=?', (case_id,)).fetchone()
            try:
                method_data = None
                if self.outcome_method == 'historical':
                    method_data = db.execute('SELECT * FROM stage4_historical_inputs WHERE case_id=?', (case_id,)).fetchall()
                method_results = generate_outcomes(self.outcome_method, applicants, method_data=method_data)
                results = resolve_case_outcomes(applicants, method_results, choice['selected_job_id'] != choice['original_job_id'])
            except (ValueError, NotImplementedError) as error:
                raise ExperimentError(str(error), 409) from error
            db.execute('INSERT INTO stage4_outcome_revelation (case_id,outcome_method,generated_at) VALUES (?,?,?)',
                       (case_id, self.outcome_method, now()))
            db.executemany('INSERT INTO stage4_applicant_outcomes VALUES (?,?,?,?,?)',
                           [(case_id, profile_id, final, self.outcome_method, rule) for profile_id, final, rule in results])
            saved = db.execute('SELECT * FROM stage4_outcome_revelation WHERE case_id=?', (case_id,)).fetchone()
        outcomes = {r['profile_id']: r for r in db.execute('SELECT * FROM stage4_applicant_outcomes WHERE case_id=?', (case_id,))}
        if state['phase'] != 'outcomes':
            state['presentation_id'] = uid()
        state.update(phase='outcomes', ack=saved['revealed_at'] is not None, duration_ms=saved['duration_ms'],
                     selected_job=json.loads(assessment['displayed_job_json']),
                     outcomes=[dict(display_position=a['display_position'], profile_id=a['profile_id'],
                                    applicant_role=a['applicant_role'], profile=json.loads(a['displayed_profile_json']),
                                    participant_judgment=a['participant_judgment'],
                                    revealed_decision=outcomes[a['profile_id']]['revealed_decision']) for a in applicants])

    def outcome_action(self, db, case_id, state, data, op):
        if op == 'display':
            if not state['ack']:
                db.execute('UPDATE stage4_outcome_revelation SET revealed_at=? WHERE case_id=? AND revealed_at IS NULL',
                           (timestamp(data), case_id))
                state['ack'] = True
            if data.get('survey_version') == 'stage5_v1':
                db.execute('INSERT OR IGNORE INTO stage5_fairness_feedback (case_id,started_at) VALUES (?,?)', (case_id, timestamp(data)))
                state['survey_ack'] = True
            return
        require(op in ('timing', 'end_session', 'submit_fairness'), '筛选结果已保存，不能修改。', 409)
        if op == 'end_session':
            require(not state.get('survey_ack'), '请先完成下方问题，再提交反馈。', 409)
        require(state['ack'], '页面正在加载，请稍候。', 409)
        duration = data.get('duration_ms')
        require(type(duration) is int and 0 <= duration <= 9007199254740991, '未能保存本次进度，请刷新页面重试。')
        state['duration_ms'] = max(state['duration_ms'], duration)
        db.execute('UPDATE stage4_outcome_revelation SET duration_ms=? WHERE case_id=?', (state['duration_ms'], case_id))
        if op == 'submit_fairness':
            require(state.get('survey_ack') and data.get('survey_version') == 'stage5_v1', '问卷正在加载，请稍候。', 409)
            saved = db.execute('SELECT submitted_at FROM stage5_fairness_feedback WHERE case_id=?', (case_id,)).fetchone()
            require(saved is not None and saved[0] is None, '反馈已经提交。', 409)
            outcomes = {r['profile_id']: r['revealed_decision'] for r in db.execute('SELECT * FROM stage4_applicant_outcomes WHERE case_id=?', (case_id,))}
            require(len(outcomes) == 6, '筛选结果加载不完整，请联系工作人员。', 409)
            try:
                rating, options, reason, other, choice, individual, pairs = validate_feedback(data, outcomes)
            except ValueError as error:
                raise ExperimentError(str(error)) from error
            db.execute('UPDATE stage5_fairness_feedback SET submitted_at=?,fairness_rating=?,group_selections_json=?,group_reason=?,other_group_view=?,individual_comparison=?,individual_reason=? WHERE case_id=?',
                       (timestamp(data), rating, encode(sorted(options)), reason, other, choice, individual, case_id))
            db.executemany('INSERT INTO stage5_applicant_comparisons VALUES (?,?,?,?,?)', [(case_id, i, *pair) for i, pair in enumerate(pairs, 1)])
        if op in ('end_session', 'submit_fairness'):
            db.execute('UPDATE stage4_outcome_revelation SET continued_at=? WHERE case_id=?', (timestamp(data), case_id))

    def competition_action(self, db, case_id, state, data, op):
        if op == 'display':
            if not state['ack']:
                db.execute('UPDATE stage3_competition_assessment SET started_at=? WHERE case_id=? AND started_at IS NULL',
                           (timestamp(data), case_id))
                state['ack'] = True
            return
        require(state['ack'], '页面正在加载，请稍候。', 409)
        require(op in ('timing', 'submit_judgments', 'submit_and_reveal'), '请完成六人的判断。', 409)
        duration = data.get('duration_ms')
        require(type(duration) is int and 0 <= duration <= 9007199254740991, '未能保存本次进度，请刷新页面重试。')
        if op in ('submit_judgments', 'submit_and_reveal'):
            judgments = data.get('judgments')
            require(type(judgments) is list and len(judgments) == 6, '请为六位申请者都选择通过或不通过。')
            mapping = {}
            for item in judgments:
                require(type(item) is dict, '未能保存判断，请刷新页面重试。')
                profile_id = text_field(item, 'profile_id')
                require(profile_id not in mapping and item.get('judgment') in ('pass', 'reject'), '未能保存判断，请检查是否为每人选择了通过或不通过。')
                mapping[profile_id] = item['judgment']
            require(set(mapping) == {a['profile_id'] for a in state['applicants']}, '申请者资料已更新，请刷新页面后重新选择。')
            require(sum(v == 'pass' for v in mapping.values()) == 3, '请选择三人通过、三人不通过。')
            for profile_id, judgment in mapping.items():
                db.execute('UPDATE stage3_applicants SET participant_judgment=? WHERE case_id=? AND profile_id=?',
                           (judgment, case_id, profile_id))
            db.execute('UPDATE stage3_competition_assessment SET submitted_at=? WHERE case_id=?', (timestamp(data), case_id))
            state['phase'] = 'judged'
        state['duration_ms'] = max(state['duration_ms'], duration)
        db.execute('UPDATE stage3_competition_assessment SET judgment_duration_ms=? WHERE case_id=?',
                   (state['duration_ms'], case_id))
        if op == 'submit_and_reveal':
            # One transaction finalizes predictions and retrieves outcomes. A failed
            # retrieval rolls back both, leaving the participant's draft retryable.
            self.prepare_outcomes(db, case_id, state)
