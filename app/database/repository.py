from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core import LearnerProfileSnapshot
from app.models import AnalysisResult, DiagnosisResult, EssaySubmission, HistoryResult, ProviderResult
from app.revision import RevisionGroup, RevisionSnapshot
from app.configuration import ConfigurationCreate, ConfigurationPayload, ConfigurationVersion, configuration_hash
from app.calibration import DiagnosticCalibrationResult
from app.calf import ErrorAnnotation
from app.infrastructure.sqlite import ClosingConnection, SQLiteConnectionManager
from app.infrastructure.sqlite.repositories import (
    SQLiteAnalysisRepository,
    SQLiteCalfRepository,
    SQLiteConfigurationRepository,
    SQLiteLearnerRepository,
    SQLitePracticeRepository,
    SQLiteResearchRepository,
    SQLiteRevisionRepository,
    SQLiteSubmissionRepository,
    SQLiteSystemRepository,
)


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS students (
    student_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    is_synthetic INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS essays (
    essay_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL REFERENCES students(student_id),
    writing_prompt TEXT NOT NULL,
    genre TEXT NOT NULL,
    draft_stage TEXT NOT NULL,
    timed INTEGER NOT NULL,
    time_limit_minutes INTEGER,
    tool_use TEXT NOT NULL,
    essay_text TEXT NOT NULL,
    submitted_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    essay_id INTEGER NOT NULL REFERENCES essays(essay_id),
    metrics_json TEXT NOT NULL,
    analysis_version TEXT NOT NULL,
    limitations TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS diagnoses (
    diagnosis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    essay_id INTEGER NOT NULL UNIQUE REFERENCES essays(essay_id),
    diagnosis_json TEXT NOT NULL,
    diagnosis_version TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS feedback_records (
    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
    essay_id INTEGER NOT NULL UNIQUE REFERENCES essays(essay_id),
    feedback_json TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    success_status TEXT NOT NULL,
    fallback_reason TEXT,
    prompt_version TEXT NOT NULL,
    analysis_version TEXT NOT NULL,
    system_template_hash TEXT NOT NULL DEFAULT '',
    user_template_hash TEXT NOT NULL DEFAULT '',
    rendered_prompt_hash TEXT NOT NULL DEFAULT '',
    schema_version TEXT NOT NULL DEFAULT '',
    temperature REAL NOT NULL DEFAULT 0.0,
    request_time TEXT,
    response_time TEXT,
    validation_status TEXT NOT NULL DEFAULT 'not_run',
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS exercises (
    exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    essay_id INTEGER NOT NULL REFERENCES essays(essay_id),
    diagnosis_id TEXT NOT NULL DEFAULT '',
    diagnosis_category TEXT NOT NULL,
    exercise_type TEXT NOT NULL,
    exercise_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS learner_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL REFERENCES students(student_id),
    essay_id INTEGER NOT NULL UNIQUE REFERENCES essays(essay_id),
    history_summary TEXT NOT NULL,
    comparable_count INTEGER NOT NULL,
    comparability_status TEXT NOT NULL DEFAULT 'insufficient_history',
    history_evidence_json TEXT NOT NULL DEFAULT '[]',
    limitations_json TEXT NOT NULL DEFAULT '[]',
    comparability_reasons_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS llm_call_records (
    call_id INTEGER PRIMARY KEY AUTOINCREMENT,
    essay_id INTEGER NOT NULL REFERENCES essays(essay_id),
    prompt_version TEXT NOT NULL,
    system_template_hash TEXT NOT NULL,
    user_template_hash TEXT NOT NULL,
    rendered_prompt_hash TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    temperature REAL NOT NULL,
    request_time TEXT NOT NULL,
    response_time TEXT NOT NULL,
    success_status TEXT NOT NULL,
    validation_status TEXT NOT NULL,
    retry_count INTEGER NOT NULL,
    fallback_reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS system_versions (
    component TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._connection_manager = SQLiteConnectionManager(self.path)
        self._system_repository = SQLiteSystemRepository(self._connection_manager)
        self._configuration_repository = SQLiteConfigurationRepository(self._connection_manager)
        self._analysis_repository = SQLiteAnalysisRepository(self._connection_manager)
        self._calf_repository = SQLiteCalfRepository(self._connection_manager)
        self._submission_repository = SQLiteSubmissionRepository(
            self._connection_manager, SQLiteRevisionRepository.normalize_revision_stage
        )
        self._revision_repository = SQLiteRevisionRepository(
            self._connection_manager, self._submission_repository
        )
        self._learner_repository = SQLiteLearnerRepository(
            self._connection_manager, self._analysis_repository, self._calf_repository,
            SQLiteRevisionRepository.normalize_revision_stage,
        )
        self._practice_repository = SQLitePracticeRepository(self._connection_manager)
        self._research_repository = SQLiteResearchRepository(self._connection_manager)

    def connect(self) -> sqlite3.Connection:
        return self._system_repository.connect()

    def initialize(self) -> None:
        return self._system_repository.initialize()

    @staticmethod
    def _add_column_if_missing(connection: sqlite3.Connection, table: str,
                                   column: str, definition: str) -> None:
            columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            if column not in columns:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _migrate_v0_1_to_v0_1_1(self, connection: sqlite3.Connection) -> None:
            additions = {
                "essays": {"time_limit_minutes": "INTEGER"},
                "feedback_records": {
                    "system_template_hash": "TEXT NOT NULL DEFAULT ''",
                    "user_template_hash": "TEXT NOT NULL DEFAULT ''",
                    "rendered_prompt_hash": "TEXT NOT NULL DEFAULT ''",
                    "schema_version": "TEXT NOT NULL DEFAULT ''",
                    "temperature": "REAL NOT NULL DEFAULT 0.0",
                    "request_time": "TEXT",
                    "response_time": "TEXT",
                    "validation_status": "TEXT NOT NULL DEFAULT 'not_run'",
                    "retry_count": "INTEGER NOT NULL DEFAULT 0",
                },
                "exercises": {"diagnosis_id": "TEXT NOT NULL DEFAULT ''"},
                "learner_history": {
                    "comparability_status": "TEXT NOT NULL DEFAULT 'insufficient_history'",
                    "history_evidence_json": "TEXT NOT NULL DEFAULT '[]'",
                    "limitations_json": "TEXT NOT NULL DEFAULT '[]'",
                    "comparability_reasons_json": "TEXT NOT NULL DEFAULT '[]'",
                },
            }
            for table, columns in additions.items():
                for column, definition in columns.items():
                    self._add_column_if_missing(connection, table, column, definition)

    def record_versions(self, versions: dict[str, str]) -> None:
        return self._system_repository.record_versions(versions)

    def save_essay(self, submission: EssaySubmission, *, synthetic: bool=False) -> int:
        return self._submission_repository.save_essay(submission, synthetic=synthetic)

    def save_analysis(self, essay_id: int, analysis: AnalysisResult) -> None:
        return self._analysis_repository.save_analysis(essay_id, analysis)

    def save_analysis_run(self, essay_id: int, analysis: AnalysisResult) -> AnalysisResult:
        return self._analysis_repository.save_analysis_run(essay_id, analysis)

    def list_analysis_runs(self, essay_id: int) -> list[dict[str, Any]]:
        return self._analysis_repository.list_analysis_runs(essay_id)

    def get_latest_analysis_run(self, essay_id: int) -> dict[str, Any] | None:
        return self._analysis_repository.get_latest_analysis_run(essay_id)

    def get_analysis_run(self, analysis_run_id: str) -> dict[str, Any] | None:
        return self._analysis_repository.get_analysis_run(analysis_run_id)

    def get_metric_results(self, analysis_run_id: str) -> list[dict[str, Any]]:
        return self._analysis_repository.get_metric_results(analysis_run_id)

    def get_analysis_artifact(self, analysis_run_id: str) -> dict[str, Any] | None:
        return self._analysis_repository.get_analysis_artifact(analysis_run_id)

    def save_diagnosis(self, essay_id: int, diagnosis: DiagnosisResult) -> None:
        return self._analysis_repository.save_diagnosis(essay_id, diagnosis)

    def save_diagnostic_calibration(self, essay_id: int, calibration: DiagnosticCalibrationResult) -> DiagnosticCalibrationResult:
        return self._calf_repository.save_diagnostic_calibration(essay_id, calibration)

    def get_diagnostic_calibration(self, essay_id: int) -> DiagnosticCalibrationResult | None:
        return self._calf_repository.get_diagnostic_calibration(essay_id)

    def save_feedback(self, essay_id: int, result: ProviderResult, analysis_version: str) -> None:
        return self._submission_repository.save_feedback(essay_id, result, analysis_version)

    def save_history(self, student_id: str, essay_id: int, history: HistoryResult) -> None:
        return self._submission_repository.save_history(student_id, essay_id, history)

    def prior_records(self, submission: EssaySubmission) -> list[dict[str, Any]]:
        return self._submission_repository.prior_records(submission)

    def counts(self) -> dict[str, int]:
        return self._system_repository.counts()

    def get_feedback_record(self, essay_id: int) -> dict[str, Any] | None:
        return self._submission_repository.get_feedback_record(essay_id)

    def get_llm_calls(self, essay_id: int) -> list[dict[str, Any]]:
        return self._submission_repository.get_llm_calls(essay_id)

    def get_history_record(self, essay_id: int) -> dict[str, Any] | None:
        return self._submission_repository.get_history_record(essay_id)

    def ping(self) -> bool:
        return self._system_repository.ping()

    def migration_version(self) -> int:
        return self._system_repository.migration_version()

    @contextmanager
    def transaction(self):
        with self._system_repository.transaction() as connection:
            yield connection

    def get_student(self, student_id: str) -> dict[str, Any] | None:
        return self._learner_repository.get_student(student_id)

    def list_all_students(self):
        return self._learner_repository.list_all_students()

    def list_all_submissions(self):
        return self._submission_repository.list_all_submissions()

    def get_submission_bundle(self, essay_id: int) -> dict[str, Any] | None:
        return self._submission_repository.get_submission_bundle(essay_id)

    def list_student_submissions(self, student_id: str) -> list[dict[str, Any]]:
        return self._submission_repository.list_student_submissions(student_id)

    def list_analysis_units(self, submission_id: int, analysis_run_id: str | None=None) -> list[dict[str, Any]]:
        return self._calf_repository.list_analysis_units(submission_id, analysis_run_id)

    def save_error_annotations(self, submission_id: int, annotations: list[ErrorAnnotation]) -> list[ErrorAnnotation]:
        return self._calf_repository.save_error_annotations(submission_id, annotations)

    def list_error_annotations(self, submission_id: int) -> list[ErrorAnnotation]:
        return self._calf_repository.list_error_annotations(submission_id)

    def list_student_history(self, student_id: str) -> list[dict[str, Any]]:
        return self._learner_repository.list_student_history(student_id)

    def get_exercises(self, essay_id: int) -> list[dict[str, Any]]:
        return self._submission_repository.get_exercises(essay_id)

    def get_latest_learner_profile(self, student_id: str) -> dict[str, Any] | None:
        return self._learner_repository.get_latest_learner_profile(student_id)

    def save_learner_profile_snapshot(self, snapshot: LearnerProfileSnapshot) -> LearnerProfileSnapshot:
        return self._learner_repository.save_learner_profile_snapshot(snapshot)

    def list_history_evidence(self, student_id: str) -> list[dict[str, Any]]:
        return self._learner_repository.list_history_evidence(student_id)

    def list_learner_profile_snapshots(self, student_id: str) -> list[dict[str, Any]]:
        return self._learner_repository.list_learner_profile_snapshots(student_id)

    def list_longitudinal_records(self, student_id: str) -> list[dict[str, Any]]:
        return self._learner_repository.list_longitudinal_records(student_id)

    def get_system_versions(self) -> dict[str, str]:
        return self._system_repository.get_system_versions()

    @staticmethod
    def normalize_revision_stage(value: str) -> str:
        return SQLiteRevisionRepository.normalize_revision_stage(value)

    def create_revision_group(self, source_submission_id: int) -> RevisionGroup:
        return self._revision_repository.create_revision_group(source_submission_id)

    def link_revision(self, source_submission_id: int, target_submission_id: int, revision_group_id: str) -> None:
        return self._revision_repository.link_revision(source_submission_id, target_submission_id, revision_group_id)

    def get_revision_group(self, revision_group_id: str) -> RevisionGroup | None:
        return self._revision_repository.get_revision_group(revision_group_id)

    def get_revision_group_for_submission(self, submission_id: int) -> RevisionGroup | None:
        return self._revision_repository.get_revision_group_for_submission(submission_id)

    def list_revision_candidates(self, submission_id: int) -> list[dict[str, Any]]:
        return self._revision_repository.list_revision_candidates(submission_id)

    def save_revision_snapshot(self, snapshot: RevisionSnapshot) -> RevisionSnapshot:
        return self._revision_repository.save_revision_snapshot(snapshot)

    def list_revision_snapshots(self, revision_group_id: str) -> list[dict[str, Any]]:
        return self._revision_repository.list_revision_snapshots(revision_group_id)

    def get_latest_revision_snapshot(self, revision_group_id: str) -> dict[str, Any] | None:
        return self._revision_repository.get_latest_revision_snapshot(revision_group_id)

    def list_configurations(self) -> list[ConfigurationVersion]:
        return self._configuration_repository.list_configurations()

    def get_configuration(self, configuration_id_or_version: str) -> ConfigurationVersion | None:
        return self._configuration_repository.get_configuration(configuration_id_or_version)

    def get_active_configuration(self) -> ConfigurationVersion:
        return self._configuration_repository.get_active_configuration()

    def create_configuration(self, request: ConfigurationCreate, parent_version: str | None) -> ConfigurationVersion:
        return self._configuration_repository.create_configuration(request, parent_version)

    def set_configuration_validation(self, configuration_id: str, *, passed: bool, errors: list[str], actor: str) -> ConfigurationVersion:
        return self._configuration_repository.set_configuration_validation(configuration_id, passed=passed, errors=errors, actor=actor)

    def activate_configuration(self, configuration_id: str, *, actor: str, reason: str, action: str='activate') -> ConfigurationVersion:
        return self._configuration_repository.activate_configuration(configuration_id, actor=actor, reason=reason, action=action)

    def list_configuration_audit(self, configuration_id: str | None=None) -> list[dict[str, Any]]:
        return self._configuration_repository.list_configuration_audit(configuration_id)

    def list_visualization_records(self, student_id: str) -> list[dict[str, Any]]:
        return self._learner_repository.list_visualization_records(student_id)

    def save_practice_target(self, target: dict) -> dict:
        return self._practice_repository.save_practice_target(target)

    def list_practice_targets(self, student_id: str) -> list[dict]:
        return self._practice_repository.list_practice_targets(student_id)

    def get_practice_target(self, pid: str) -> dict | None:
        return self._practice_repository.get_practice_target(pid)

    def save_exercise_instance(self, instance: dict) -> dict:
        return self._practice_repository.save_exercise_instance(instance)

    def list_exercise_instances(self, practice_target_id=None, student_id=None) -> list[dict]:
        return self._practice_repository.list_exercise_instances(practice_target_id, student_id)

    def get_exercise_instance(self, eid: str) -> dict | None:
        return self._practice_repository.get_exercise_instance(eid)

    def save_exercise_attempt(self, attempt: dict) -> dict:
        return self._practice_repository.save_exercise_attempt(attempt)

    def list_exercise_attempts(self, exercise_id: str) -> list[dict]:
        return self._practice_repository.list_exercise_attempts(exercise_id)

    def save_practice_evaluation(self, evaluation: dict) -> dict:
        return self._practice_repository.save_practice_evaluation(evaluation)

    def list_practice_evaluations(self, attempt_id=None, practice_target_id=None) -> list[dict]:
        return self._practice_repository.list_practice_evaluations(attempt_id, practice_target_id)

    def list_practice_evaluations_by_student(self, student_id: str) -> list[dict]:
        return self._practice_repository.list_practice_evaluations_by_student(student_id)

    def list_essays_by_student(self, student_id: str) -> list[dict]:
        return self._practice_repository.list_essays_by_student(student_id)

    def list_analysis_runs_for_student(self, student_id: str) -> list[dict]:
        return self._practice_repository.list_analysis_runs_for_student(student_id)

    def list_feedback_records_for_student(self, student_id: str) -> list[dict]:
        return self._practice_repository.list_feedback_records_for_student(student_id)

    def list_exercise_attempts_by_student(self, student_id: str) -> list[dict]:
        return self._practice_repository.list_exercise_attempts_by_student(student_id)

    def save_feedback_engagement_trace(self, trace: dict) -> dict:
        return self._practice_repository.save_feedback_engagement_trace(trace)

    def list_feedback_engagement_traces(self, student_id: str) -> list[dict]:
        return self._practice_repository.list_feedback_engagement_traces(student_id)

    def save_within_task_response_candidate(self, candidate: dict) -> dict:
        return self._practice_repository.save_within_task_response_candidate(candidate)

    def list_within_task_responses(self, student_id: str) -> list[dict]:
        return self._practice_repository.list_within_task_responses(student_id)

    def save_transfer_evidence_candidate(self, candidate: dict) -> dict:
        return self._practice_repository.save_transfer_evidence_candidate(candidate)

    def list_transfer_evidence_candidates(self, student_id: str) -> list[dict]:
        return self._practice_repository.list_transfer_evidence_candidates(student_id)

    def save_practice_state_snapshot(self, snapshot: dict) -> dict:
        return self._practice_repository.save_practice_state_snapshot(snapshot)

    def list_practice_state_snapshots(self, student_id: str) -> list[dict]:
        return self._practice_repository.list_practice_state_snapshots(student_id)

    def save_human_review(self, review) -> dict:
        return self._research_repository.save_human_review(review)

    def list_human_reviews(self, target_type: str | None=None, target_id: str | None=None) -> list[dict]:
        return self._research_repository.list_human_reviews(target_type, target_id)

    def apply_pii_review(self, submission_id: int, reviews: list) -> list[dict]:
        return self._research_repository.apply_pii_review(submission_id, reviews)

    def save_export_job(self, job: dict) -> dict:
        return self._research_repository.save_export_job(job)

    def list_export_jobs(self) -> list[dict]:
        return self._research_repository.list_export_jobs()

    def get_export_job(self, export_id: str) -> dict | None:
        return self._research_repository.get_export_job(export_id)


SQLiteRepository = Database
