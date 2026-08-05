"""v0.9.5-F4 focused tests: Reanalysis and Journey dependency narrowing.

Covers the four consumer Ports, minimal-stub behavior for both Services,
read-only/write-count contracts, app-composition wiring in both construction
paths, the Journey router dependency seam, and the authorized demo-script
composition exception.
"""

from __future__ import annotations

import ast
import inspect
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.main import _build_full_app, _run_startup, create_app
from app.config import Settings
from app.database import Database
from app.infrastructure.sqlite.repositories.analysis import SQLiteAnalysisRepository
from app.infrastructure.sqlite.repositories.learner import SQLiteLearnerRepository
from app.infrastructure.sqlite.repositories.practice import SQLitePracticeRepository
from app.infrastructure.sqlite.repositories.submission import SQLiteSubmissionRepository
from app.journey.service import (
    JourneyProjectionReadPort,
    JourneyService,
    JourneyStudentReadPort,
)
from app.models import AnalysisResult
from app.services.reanalysis import (
    AnalysisRunWritePort,
    ReanalysisService,
    SubmissionBundleReadPort,
)
from tests.test_v095f2_service_narrowing import _restore_lifecycle, _snapshot_lifecycle


ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "f4.db",
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
    )


def _public_protocol_methods(protocol) -> set[str]:
    return {
        name for name, value in vars(protocol).items()
        if not name.startswith("_") and callable(value)
    }


def _bundle_row() -> dict:
    return {
        "essay_id": 7,
        "student_id": "F4-REA",
        "writing_prompt": "What actions matter for sustainability?",
        "genre": "argumentative essay",
        "draft_stage": "first draft",
        "timed": False,
        "time_limit_minutes": None,
        "tool_use": "none",
        "essay_text": "People should protect the environment. People should recycle more. "
                      "People should save water.",
        "submitted_at": datetime(2026, 8, 2, tzinfo=timezone.utc),
        "revision_of_submission_id": None,
        "writing_started_at": None,
        "writing_submitted_at": None,
        "active_writing_duration_seconds": None,
        "timing_source": "unknown",
        "timing_quality": "unavailable",
        "unexplained_interruption": False,
    }


class MinimalSubmissionReader:
    def __init__(self, row):
        self.row = row
        self.reads = 0

    def get_submission_bundle(self, essay_id: int):
        self.reads += 1
        return None if self.row is None else dict(self.row)


class MinimalAnalysisWriter:
    def __init__(self):
        self.saves = 0
        self.saved: list[AnalysisResult] = []

    def save_analysis_run(self, essay_id: int, analysis: AnalysisResult) -> AnalysisResult:
        self.saves += 1
        self.saved.append(analysis)
        return analysis


class MinimalAnalyzer:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.calls = 0

    def analyze(self, text: str, *, writing_prompt: str = "", draft_stage: str | None = None,
                tool_use: str | None = None) -> AnalysisResult:
        self.calls += 1
        if self.fail:
            raise RuntimeError("analyzer exploded")
        return AnalysisResult(
            metrics={"word_count": 24},
            analysis_version="f4-analyzer-v0.1",
            limitations="",
            analyzer_id="basic",
            analyzer_version="f4-analyzer-v0.1",
            configuration_version="config-v0.9.0",
        )


class MinimalStudentReader:
    def __init__(self, learner):
        self.learner = learner
        self.calls = []

    def get_student(self, student_id: str):
        self.calls.append("get_student")
        return self.learner


class MinimalProjectionReader:
    def __init__(self, **lists):
        self.lists = lists
        self.calls = []

    def list_essays_by_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_essays_by_student")
        return list(self.lists.get("essays", []))

    def list_analysis_runs_for_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_analysis_runs_for_student")
        return list(self.lists.get("analyses", []))

    def list_feedback_records_for_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_feedback_records_for_student")
        return list(self.lists.get("feedbacks", []))

    def list_practice_targets(self, student_id: str) -> list[dict]:
        self.calls.append("list_practice_targets")
        return list(self.lists.get("targets", []))

    def list_exercise_instances(self, practice_target_id=None, student_id=None) -> list[dict]:
        self.calls.append("list_exercise_instances")
        return list(self.lists.get("exercises", []))

    def list_exercise_attempts_by_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_exercise_attempts_by_student")
        return list(self.lists.get("attempts", []))

    def list_practice_evaluations_by_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_practice_evaluations_by_student")
        return list(self.lists.get("evaluations", []))

    def list_within_task_responses(self, student_id: str) -> list[dict]:
        self.calls.append("list_within_task_responses")
        return list(self.lists.get("responses", []))

    def list_transfer_evidence_candidates(self, student_id: str) -> list[dict]:
        self.calls.append("list_transfer_evidence_candidates")
        return list(self.lists.get("transfers", []))


def _populated_lists() -> dict:
    return {
        "essays": [{
            "essay_id": 1, "student_id": "JSTUB", "writing_prompt": "p",
            "genre": "argumentative essay", "draft_stage": "first draft",
            "timed": False, "tool_use": "none",
            "submitted_at": "2026-08-01T10:00:00+00:00",
            "revision_of_submission_id": None, "revision_group_id": None,
        }],
        "analyses": [{
            "essay_id": 1, "analysis_run_id": "AR000001",
            "analyzer_id": "basic", "analyzer_version": "spacy-analyzer-v0.8.0",
            "configuration_version": "config-v0.9.0",
            "created_at": "2026-08-01T10:01:00+00:00",
        }],
        "feedbacks": [{
            "essay_id": 1, "feedback_id": "FB000001",
            "provider_name": "local_demo", "success_status": "success",
            "created_at": "2026-08-01T10:02:00+00:00",
            "feedback_json": {"priority_feedback": [{"id": "P1"}]},
        }],
        "targets": [{
            "practice_target_id": "PT000001", "source_submission_id": 1,
            "target_code": "lexical_repetition_local", "status": "pending",
            "created_at": "2026-08-01T10:03:00+00:00",
        }],
        "exercises": [{
            "exercise_id": "EX000001", "practice_target_id": "PT000001",
            "student_id": "JSTUB", "exercise_type": "sentence_rewrite",
            "created_at": "2026-08-01T10:03:30+00:00",
        }],
        "attempts": [{
            "attempt_id": "AT000001", "exercise_id": "EX000001",
            "created_at": "2026-08-01T10:04:00+00:00",
            "attempt_number": 1, "status": "submitted",
        }],
        "evaluations": [{
            "evaluation_id": "PE000001", "practice_target_id": "PT000001",
            "created_at": "2026-08-01T10:05:00+00:00",
            "completion_status": "completed", "target_action_status": "addressed",
        }],
        "responses": [{
            "response_id": "WTR000001", "observed_status": "major_rewrite",
            "revision_group_id": "RG000001", "later_submission_id": 2,
            "created_at": "2026-08-01T10:06:00+00:00",
            "target_code": "lexical_repetition_local", "comparison_version": "v0.9.0",
        }],
        "transfers": [{
            "transfer_evidence_id": "TE000001", "observed_status": "addressed",
            "later_submission_id": 3, "created_at": "2026-08-01T10:07:00+00:00",
            "task_comparability": "comparable", "target_code": "lexical_repetition_local",
        }],
    }


class TestFourPorts:
    def test_exact_names_methods_and_source_signatures(self):
        assert _public_protocol_methods(SubmissionBundleReadPort) == {"get_submission_bundle"}
        assert _public_protocol_methods(AnalysisRunWritePort) == {"save_analysis_run"}
        assert _public_protocol_methods(JourneyStudentReadPort) == {"get_student"}
        assert _public_protocol_methods(JourneyProjectionReadPort) == {
            "list_essays_by_student",
            "list_analysis_runs_for_student",
            "list_feedback_records_for_student",
            "list_practice_targets",
            "list_exercise_instances",
            "list_exercise_attempts_by_student",
            "list_practice_evaluations_by_student",
            "list_within_task_responses",
            "list_transfer_evidence_candidates",
        }

        assert inspect.signature(SubmissionBundleReadPort.get_submission_bundle) == inspect.signature(
            SQLiteSubmissionRepository.get_submission_bundle
        )
        assert inspect.signature(AnalysisRunWritePort.save_analysis_run) == inspect.signature(
            SQLiteAnalysisRepository.save_analysis_run
        )
        assert inspect.signature(JourneyStudentReadPort.get_student) == inspect.signature(
            SQLiteLearnerRepository.get_student
        )
        practice_methods = {
            "list_essays_by_student": SQLitePracticeRepository.list_essays_by_student,
            "list_analysis_runs_for_student": SQLitePracticeRepository.list_analysis_runs_for_student,
            "list_feedback_records_for_student": SQLitePracticeRepository.list_feedback_records_for_student,
            "list_practice_targets": SQLitePracticeRepository.list_practice_targets,
            "list_exercise_instances": SQLitePracticeRepository.list_exercise_instances,
            "list_exercise_attempts_by_student": SQLitePracticeRepository.list_exercise_attempts_by_student,
            "list_practice_evaluations_by_student": SQLitePracticeRepository.list_practice_evaluations_by_student,
            "list_within_task_responses": SQLitePracticeRepository.list_within_task_responses,
            "list_transfer_evidence_candidates": SQLitePracticeRepository.list_transfer_evidence_candidates,
        }
        for name in _public_protocol_methods(JourneyProjectionReadPort):
            assert inspect.signature(getattr(JourneyProjectionReadPort, name)) == inspect.signature(
                practice_methods[name]
            )

    def test_concrete_repositories_and_facade_structurally_satisfy_ports(self, tmp_path):
        database = Database(tmp_path / "ports.db")
        submission = database._submission_repository
        analysis = database._analysis_repository
        learner = database._learner_repository
        practice = database._practice_repository

        assert isinstance(submission, SubmissionBundleReadPort)
        assert isinstance(analysis, AnalysisRunWritePort)
        assert isinstance(learner, JourneyStudentReadPort)
        assert isinstance(practice, JourneyProjectionReadPort)


class TestReanalysisNarrowing:
    def test_success_performs_one_read_one_save_in_order(self):
        reader = MinimalSubmissionReader(_bundle_row())
        writer = MinimalAnalysisWriter()
        analyzer = MinimalAnalyzer()
        service = ReanalysisService(reader, writer, analyzer)

        result = service.run(7)

        assert reader.reads == 1
        assert analyzer.calls == 1
        assert writer.saves == 1
        assert writer.saved[0] is result
        assert result.metrics["word_count"] == 24
        assert any(item["metric_id"] == "writing_output_rate_wpm"
                   for item in result.metric_results)

    def test_missing_bundle_performs_zero_writes(self):
        reader = MinimalSubmissionReader(None)
        writer = MinimalAnalysisWriter()
        analyzer = MinimalAnalyzer()
        service = ReanalysisService(reader, writer, analyzer)

        with pytest.raises(LookupError, match="Submission not found."):
            service.run(99)

        assert reader.reads == 1
        assert analyzer.calls == 0
        assert writer.saves == 0

    def test_analyzer_failure_performs_zero_writes(self):
        reader = MinimalSubmissionReader(_bundle_row())
        writer = MinimalAnalysisWriter()
        analyzer = MinimalAnalyzer(fail=True)
        service = ReanalysisService(reader, writer, analyzer)

        with pytest.raises(RuntimeError, match="analyzer exploded"):
            service.run(7)

        assert reader.reads == 1
        assert analyzer.calls == 1
        assert writer.saves == 0

    def test_service_module_has_no_broad_imports_or_field(self):
        source = (ROOT / "app/services/reanalysis.py").read_text(encoding="utf-8")
        assert "app.database" not in source
        assert "SQLite" not in source
        assert "ReanalysisRepository" not in source
        assert "self.repository" not in source
        assert "hasattr(" not in source


class TestJourneyNarrowing:
    def test_minimal_stubs_sufficient_and_only_nine_methods_requested(self):
        student = MinimalStudentReader({"student_id": "JSTUB"})
        projections = MinimalProjectionReader(**_populated_lists())
        service = JourneyService(student, projections)

        result = service.get_journey("JSTUB")

        assert result["learner_found"] is True
        assert student.calls == ["get_student"]
        assert set(projections.calls) == {
            "list_essays_by_student",
            "list_analysis_runs_for_student",
            "list_feedback_records_for_student",
            "list_practice_targets",
            "list_exercise_instances",
            "list_exercise_attempts_by_student",
            "list_practice_evaluations_by_student",
            "list_within_task_responses",
            "list_transfer_evidence_candidates",
        }

    def test_student_not_found_unchanged_and_zero_other_reads(self):
        student = MinimalStudentReader(None)
        projections = MinimalProjectionReader()
        service = JourneyService(student, projections)

        with pytest.raises(LookupError, match="Student not found."):
            service.get_journey("NOPE")

        assert student.calls == ["get_student"]
        assert projections.calls == []

    def test_empty_journey_output_unchanged(self):
        student = MinimalStudentReader({"student_id": "EMPTY"})
        projections = MinimalProjectionReader()
        result = JourneyService(student, projections).get_journey("EMPTY")

        assert result == {
            "student_id": "EMPTY",
            "learner_found": True,
            "counts": {
                "submissions": 0,
                "analysis_runs": 0,
                "feedback_records": 0,
                "selected_priorities": 0,
                "practice_targets": 0,
                "exercise_attempts": 0,
                "practice_evaluations": 0,
                "within_task_responses": 0,
                "transfer_evidence_candidates": 0,
            },
            "events": [],
            "derived_states": [],
            "state": "no_submissions",
            "cycles": [],
            "cycles_version": "journey-cycle-v0.9.7-c",
        }

    def test_populated_journey_output_order_ids_and_derived_status_unchanged(self):
        student = MinimalStudentReader({"student_id": "JSTUB"})
        projections = MinimalProjectionReader(**_populated_lists())
        result = JourneyService(student, projections).get_journey("JSTUB")

        assert result["counts"] == {
            "submissions": 1,
            "analysis_runs": 1,
            "feedback_records": 1,
            "selected_priorities": 1,
            "practice_targets": 1,
            "exercise_attempts": 1,
            "practice_evaluations": 1,
            "within_task_responses": 1,
            "transfer_evidence_candidates": 1,
        }
        assert result["state"] == "journey_events"
        event_types = [event["event_type"] for event in result["events"]]
        assert event_types == [
            "writing_submitted",
            "analysis_completed",
            "feedback_available",
            "feedback_priority_available",
            "practice_available",
            "exercise_attempted",
            "practice_evaluation_recorded",
            "within_task_response_observed",
            "later_task_evidence",
        ]
        by_type = {event["event_type"]: event for event in result["events"]}
        assert by_type["writing_submitted"]["source_record_id"] == "1"
        assert by_type["analysis_completed"]["source_record_id"] == "AR000001"
        assert by_type["feedback_available"]["source_record_id"] == "FB000001"
        assert by_type["practice_available"]["source_record_id"] == "PT000001"
        assert by_type["exercise_attempted"]["source_record_id"] == "AT000001"
        assert by_type["practice_evaluation_recorded"]["source_record_id"] == "PE000001"
        assert by_type["within_task_response_observed"]["source_record_id"] == "WTR000001"
        assert by_type["later_task_evidence"]["source_record_id"] == "TE000001"
        assert by_type["feedback_priority_available"]["research_detail"]["priority_count"] == 1
        assert by_type["writing_submitted"]["occurred_at"] == "2026-08-01T10:00:00.000000+00:00"
        assert len(result["events"]) == len({e["deduplication_key"] for e in result["events"]})

    def test_service_module_has_no_broad_import_any_repository_or_repo_field(self):
        source = (ROOT / "app/journey/service.py").read_text(encoding="utf-8")
        assert "app.database" not in source
        assert "SQLite" not in source
        assert "self.repo" not in source
        assert "hasattr(" not in source
        tree = ast.parse(source)
        init = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
        annotations = [
            arg.annotation
            for arg in [*init.args.args, *init.args.kwonlyargs]
            if arg.annotation is not None
        ]
        assert all(
            isinstance(annotation, ast.Name) and annotation.id in {
                "JourneyStudentReadPort", "JourneyProjectionReadPort",
            }
            for annotation in annotations
        )


class TestComposition:
    def _assert_wiring(self, api: FastAPI) -> None:
        database = api.state.repository
        reanalysis = api.state.reanalysis
        journey = api.state.journey_service
        assert reanalysis.submission_reader is database._submission_repository
        assert reanalysis.analysis_writer is database._analysis_repository
        assert journey.student_reader is database._learner_repository
        assert journey.projection_reader is database._practice_repository
        assert reanalysis.submission_reader._connection_manager is database._connection_manager
        assert reanalysis.analysis_writer._connection_manager is database._connection_manager
        assert journey.student_reader._connection_manager is database._connection_manager
        assert journey.projection_reader._connection_manager is database._connection_manager
        assert not isinstance(journey, Database)

    def test_build_full_app_wires_extracted_repositories(self, tmp_path):
        api = _build_full_app(_settings(tmp_path))
        self._assert_wiring(api)

    def test_run_startup_wires_extracted_repositories(self, tmp_path, monkeypatch):
        saved = _snapshot_lifecycle()
        try:
            monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
            monkeypatch.delenv("DATABASE_URL", raising=False)
            monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "startup.db"))
            monkeypatch.setenv("LLM_PROVIDER", "local")
            api = FastAPI()
            _run_startup(api)
            self._assert_wiring(api)
        finally:
            _restore_lifecycle(saved)

    def test_journey_router_source_uses_service_dependency_only(self):
        source = (ROOT / "app/api/routers/journey.py").read_text(encoding="utf-8")
        assert "get_journey_service" in source
        assert "get_repository" not in source
        assert "JourneyService(" not in source
        assert "app.journey.service" not in source

    def test_journey_endpoint_200_and_404_via_app_state(self, tmp_path):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            assert client.get("/api/v1/students/S999/journey").status_code == 404
            payload = {
                "student_id": "JAPI", "writing_prompt": "What actions matter for sustainability?",
                "genre": "argumentative essay", "draft_stage": "first draft",
                "timed": False, "tool_use": "none",
                "essay_text": "People should protect the environment. People should recycle more. "
                              "People should save water. People should plant trees. "
                              "People should reduce waste.",
            }
            created = client.post("/api/v1/submissions", json=payload)
            assert created.status_code == 201
            journey = client.get("/api/v1/students/JAPI/journey")
            assert journey.status_code == 200
            assert journey.json()["learner_found"] is True
            assert journey.json()["events"]


class TestDemoScriptException:
    def test_both_construction_sites_use_explicit_repositories(self):
        source = (ROOT / "scripts/demo_journey.py").read_text(encoding="utf-8")
        assert source.count("JourneyService(") == 2
        # Three explicit learner-repository references: the two JourneyService
        # constructions plus the F6C build_submission_service factory call.
        assert source.count("repository._learner_repository") == 4
        assert source.count("repository._practice_repository") == 8
        assert "JourneyService(repository)" not in source
        assert "JourneyService(repository).get_journey" not in source
