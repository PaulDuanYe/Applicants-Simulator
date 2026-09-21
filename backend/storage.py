"""SQLite research records plus private retry/presentation state."""
import sqlite3
import json
from contextlib import closing, contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS participants (
 participant_id TEXT PRIMARY KEY, participant_code TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
 session_id TEXT PRIMARY KEY, participant_id TEXT NOT NULL REFERENCES participants,
 started_at TEXT NOT NULL, ended_at TEXT);
CREATE TABLE IF NOT EXISTS cases (
 case_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions,
 case_number INTEGER NOT NULL CHECK(case_number > 0), started_at TEXT NOT NULL,
 schema_version TEXT NOT NULL, timing_policy TEXT NOT NULL, UNIQUE(session_id,case_number));
CREATE TABLE IF NOT EXISTS stage1_profile_selection (
 case_id TEXT PRIMARY KEY REFERENCES cases, started_at TEXT NOT NULL, confirmed_at TEXT,
 refresh_count INTEGER NOT NULL DEFAULT 0 CHECK(refresh_count >= 0), confirmed_profile_id TEXT,
 confirmation_duration_ms INTEGER CHECK(confirmation_duration_ms >= 0));
CREATE TABLE IF NOT EXISTS case_configuration (
 case_id TEXT PRIMARY KEY REFERENCES cases,
 profile_refresh_enabled INTEGER NOT NULL CHECK(profile_refresh_enabled IN (0,1)),
 job_selection_enabled INTEGER NOT NULL CHECK(job_selection_enabled IN (0,1)),
 assigned_profile_job_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stage1_profile_views (
 case_id TEXT NOT NULL REFERENCES stage1_profile_selection, view_number INTEGER NOT NULL CHECK(view_number > 0),
 profile_id TEXT NOT NULL, displayed_profile_json TEXT NOT NULL,
 displayed_at TEXT NOT NULL, ended_at TEXT, duration_ms INTEGER NOT NULL CHECK(duration_ms >= 0),
 ended_by TEXT CHECK(ended_by IN ('refresh','confirm')), PRIMARY KEY(case_id,view_number));
CREATE TABLE IF NOT EXISTS stage2_job_selection (
 case_id TEXT PRIMARY KEY REFERENCES cases, started_at TEXT NOT NULL, submitted_at TEXT,
 original_job_id TEXT NOT NULL, selected_job_id TEXT, decision_duration_ms INTEGER NOT NULL CHECK(decision_duration_ms >= 0));
CREATE TABLE IF NOT EXISTS stage2_job_options (
 case_id TEXT NOT NULL REFERENCES stage2_job_selection, display_position INTEGER NOT NULL CHECK(display_position BETWEEN 1 AND 3),
 job_id TEXT NOT NULL, displayed_job_json TEXT NOT NULL,
 PRIMARY KEY(case_id,display_position), UNIQUE(case_id,job_id));
CREATE TABLE IF NOT EXISTS stage3_competition_assessment (
 case_id TEXT PRIMARY KEY REFERENCES cases, selected_job_id TEXT NOT NULL,
 displayed_job_json TEXT NOT NULL, prepared_at TEXT NOT NULL, started_at TEXT,
 submitted_at TEXT, judgment_duration_ms INTEGER NOT NULL DEFAULT 0 CHECK(judgment_duration_ms >= 0));
CREATE TABLE IF NOT EXISTS stage3_applicants (
 case_id TEXT NOT NULL REFERENCES stage3_competition_assessment,
 display_position INTEGER NOT NULL CHECK(display_position BETWEEN 1 AND 6), profile_id TEXT NOT NULL,
 applicant_role TEXT NOT NULL CHECK(applicant_role IN ('participant','competitor')),
 displayed_profile_json TEXT NOT NULL,
 participant_judgment TEXT CHECK(participant_judgment IN ('pass','reject')),
 PRIMARY KEY(case_id,display_position), UNIQUE(case_id,profile_id));
CREATE TABLE IF NOT EXISTS stage4_historical_inputs (
 case_id TEXT NOT NULL, profile_id TEXT NOT NULL,
 source_decision TEXT NOT NULL CHECK(source_decision IN ('pass','reject')),
 PRIMARY KEY(case_id,profile_id),
 FOREIGN KEY(case_id,profile_id) REFERENCES stage3_applicants(case_id,profile_id));
CREATE TABLE IF NOT EXISTS stage4_outcome_revelation (
 case_id TEXT PRIMARY KEY REFERENCES stage3_competition_assessment,
 outcome_method TEXT NOT NULL, generated_at TEXT NOT NULL, revealed_at TEXT, continued_at TEXT,
 duration_ms INTEGER NOT NULL DEFAULT 0 CHECK(duration_ms >= 0));
CREATE TABLE IF NOT EXISTS stage4_applicant_outcomes (
 case_id TEXT NOT NULL REFERENCES stage4_outcome_revelation, profile_id TEXT NOT NULL,
 revealed_decision TEXT NOT NULL CHECK(revealed_decision IN ('pass','reject')),
 decision_basis TEXT NOT NULL CHECK(decision_basis IN ('historical','llm','matrix','random_method')),
 applied_rule TEXT CHECK(applied_rule = 'alternative_job_rejection'),
 PRIMARY KEY(case_id,profile_id),
 FOREIGN KEY(case_id,profile_id) REFERENCES stage3_applicants(case_id,profile_id));
CREATE TABLE IF NOT EXISTS technical_credentials (
 token_hash TEXT PRIMARY KEY, participant_id TEXT NOT NULL REFERENCES participants);
CREATE TABLE IF NOT EXISTS technical_receipts (
 scope TEXT NOT NULL, action_id TEXT NOT NULL, request_json TEXT NOT NULL, response_json TEXT NOT NULL,
 PRIMARY KEY(scope,action_id));
CREATE TABLE IF NOT EXISTS technical_case_state (
 case_id TEXT PRIMARY KEY REFERENCES cases, state_json TEXT NOT NULL);
"""

SCHEMA += """
CREATE TABLE IF NOT EXISTS stage5_fairness_feedback (
 case_id TEXT PRIMARY KEY REFERENCES stage4_outcome_revelation,
 started_at TEXT NOT NULL, submitted_at TEXT,
 fairness_rating INTEGER CHECK(fairness_rating BETWEEN 1 AND 10),
 group_selections_json TEXT, group_reason TEXT, other_group_view TEXT,
 individual_comparison TEXT CHECK(individual_comparison IN ('yes','no','unsure')), individual_reason TEXT);
CREATE TABLE IF NOT EXISTS stage5_applicant_comparisons (
 case_id TEXT NOT NULL REFERENCES stage5_fairness_feedback,
 comparison_number INTEGER NOT NULL CHECK(comparison_number BETWEEN 1 AND 9),
 rejected_profile_id TEXT NOT NULL, passed_profile_id TEXT NOT NULL, reason TEXT NOT NULL,
 PRIMARY KEY(case_id,comparison_number), UNIQUE(case_id,rejected_profile_id,passed_profile_id),
 FOREIGN KEY(case_id,rejected_profile_id) REFERENCES stage4_applicant_outcomes(case_id,profile_id),
 FOREIGN KEY(case_id,passed_profile_id) REFERENCES stage4_applicant_outcomes(case_id,profile_id));
"""


class Storage:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=10)) as db:
            # Rebuild the legacy tables atomically; FK checks run before commit.
            db.execute('PRAGMA foreign_keys = OFF')
            db.execute('BEGIN IMMEDIATE')
            try:
                self._migrate(db)
                for statement in SCHEMA.split(';'):
                    if statement.strip():
                        db.execute(statement)
                self._merge_group_selections(db)
                if db.execute('PRAGMA foreign_key_check').fetchone():
                    raise ValueError('Storage migration failed: invalid research record linkage.')
                db.commit()
            except Exception:
                db.rollback()
                raise

    @staticmethod
    def _merge_group_selections(db):
        columns = {r[1] for r in db.execute('PRAGMA table_info(stage5_fairness_feedback)')}
        if 'group_selections_json' not in columns:
            db.execute('ALTER TABLE stage5_fairness_feedback ADD COLUMN group_selections_json TEXT')
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='stage5_group_selections'").fetchone():
            return
        if db.execute('SELECT 1 FROM stage5_group_selections g LEFT JOIN stage5_fairness_feedback f USING(case_id) WHERE f.case_id IS NULL').fetchone():
            raise ValueError('Cannot merge group selections: missing feedback parent.')
        for case_id, submitted, existing in db.execute('SELECT case_id,submitted_at,group_selections_json FROM stage5_fairness_feedback').fetchall():
            options = [r[0] for r in db.execute('SELECT option_code FROM stage5_group_selections WHERE case_id=? ORDER BY option_code', (case_id,))]
            if existing is not None and json.loads(existing) != options:
                raise ValueError('Conflicting group selections; migration rolled back.')
            # Preserve unfinished NULL answers. Selection order was not recorded by the old table.
            if options or submitted is not None:
                db.execute('UPDATE stage5_fairness_feedback SET group_selections_json=? WHERE case_id=?', (json.dumps(options, separators=(',', ':')), case_id))
        db.execute('DROP TABLE stage5_group_selections')

    @staticmethod
    def _migrate(db):
        columns = {r[1] for r in db.execute('PRAGMA table_info(stage3_applicants)')}
        if 'source_decision' not in columns:
            return
        # Refuse to discard inconsistent legacy values; never repair observations.
        invalid = db.execute("""SELECT 1 FROM stage3_applicants a
            JOIN stage2_job_selection j USING(case_id)
            WHERE a.case_decision != CASE WHEN a.applicant_role='participant'
              AND j.selected_job_id != j.original_job_id THEN 'reject' ELSE a.source_decision END
            OR a.decision_basis != CASE WHEN a.applicant_role='participant'
              AND j.selected_job_id != j.original_job_id THEN 'alternative_job_rejection' ELSE 'source_decision' END
            LIMIT 1""").fetchone()
        if invalid:
            raise ValueError('Legacy outcome rules are inconsistent; migration rolled back.')
        statements = {s.strip().split()[5]: s for s in SCHEMA.split(';') if s.strip()}
        db.execute(statements['stage4_historical_inputs'])
        db.execute('INSERT INTO stage4_historical_inputs SELECT case_id,profile_id,source_decision FROM stage3_applicants')
        old_outcomes = {r[1] for r in db.execute('PRAGMA table_info(stage4_applicant_outcomes)')}
        if old_outcomes:
            invalid = db.execute('''SELECT 1 FROM stage4_applicant_outcomes o
                JOIN stage3_applicants a USING(case_id,profile_id)
                JOIN stage4_outcome_revelation r USING(case_id)
                WHERE o.method_decision != a.source_decision OR o.revealed_decision != a.case_decision
                OR o.decision_basis != a.decision_basis OR r.outcome_method != 'historical' LIMIT 1''').fetchone()
            if invalid:
                raise ValueError('Legacy historical results are inconsistent; migration rolled back.')
            db.execute(statements['stage4_applicant_outcomes'].replace('EXISTS stage4_applicant_outcomes', 'EXISTS stage4_applicant_outcomes_new'))
            db.execute("""INSERT INTO stage4_applicant_outcomes_new
                SELECT case_id,profile_id,revealed_decision,'historical',
                CASE WHEN decision_basis='alternative_job_rejection' THEN decision_basis ELSE NULL END
                FROM stage4_applicant_outcomes""")
            db.execute('DROP TABLE stage4_applicant_outcomes')
            db.execute('ALTER TABLE stage4_applicant_outcomes_new RENAME TO stage4_applicant_outcomes')
        db.execute(statements['stage3_applicants'].replace('EXISTS stage3_applicants', 'EXISTS stage3_applicants_new'))
        db.execute('''INSERT INTO stage3_applicants_new SELECT case_id,display_position,profile_id,
            applicant_role,displayed_profile_json,participant_judgment FROM stage3_applicants''')
        db.execute('DROP TABLE stage3_applicants')
        db.execute('ALTER TABLE stage3_applicants_new RENAME TO stage3_applicants')

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
