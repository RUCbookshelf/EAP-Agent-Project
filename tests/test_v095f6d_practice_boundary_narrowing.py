"""v0.9.5-F6D focused tests: Practice write-boundary narrowing.

Proves the three consumer-owned Practice Ports, PracticeService purity,
facade-owned app-state composition, the narrow Router dependency set, API
behavior parity, read-endpoint zero-write behavior, and the
Attempt-first/Evaluation-best-effort partial-commit failure matrix.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.main import _build_full_app, _run_startup, create_app
from app.database import Database
from app.practice.ports import (
    PracticeReadPort,
    PracticeSubmissionReadPort,
    PracticeWritePort,
)
from app.practice.service import PracticeService
from tests.test_v095f2_service_narrowing import _restore_lifecycle, _snapshot_lifecycle


ROOT = Path(__file__).resolve().parents[1]

REPETITION_ESSAY = (
    "People should protect the environment. People should recycle more. "
    "People should save water. People should plant trees. People should reduce waste. "
    "People should use public transport. People should teach children about nature. "
    "People should value clean air."
)


def _public_protocol_methods(protocol) -> set[str]:
    return {
        name for name, value in vars(protocol).items()
        if not name.startswith("_") and callable(value)
    }


def _settings(tmp_path):
    from app.config import Settings
    return Settings(
        database_path=tmp_path / "f6d.db", llm_provider="local", deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com", deepseek_model="deepseek-chat",
    )


def _seed_flow(client: TestClient) -> tuple[int, dict, dict]:
    submission = {
        "student_id": "F6D-S", "writing_prompt": "What actions matter for sustainability?",
        "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
        "tool_use": "none", "essay_text": REPETITION_ESSAY,
    }
    created = client.post("/api/v1/submissions", json=submission)
    assert created.status_code == 201, created.text
    payload = created.json()
    essay_id = payload["submission_id"]
    priority = next(
        item for item in payload["diagnosis"].get("improvement_priorities", [])
        if item.get("selection_status") == "selected_priority"
    )
    target = client.post("/api/v1/practice-targets", json={
        "student_id": "F6D-S", "source_submission_id": essay_id,
        "source_diagnosis_id": priority["diagnosis_id"],
        "target_code": "lexical_repetition_local",
        "target_label": priority["interpretation"],
        "gate_status": "selected",
    }).json()
    exercise = client.post(
        f"/api/v1/practice-targets/{target['practice_target_id']}/exercises",
        json={"source_text": REPETITION_ESSAY},
    ).json()
    return essay_id, target, exercise


def _row_counts(database: Database) -> dict[str, int]:
    with database.connect() as connection:
        return {
            "attempts": connection.execute(
                "SELECT COUNT(*) FROM exercise_attempts").fetchone()[0],
            "evaluations": connection.execute(
                "SELECT COUNT(*) FROM practice_evaluations").fetchone()[0],
            "targets": connection.execute(
                "SELECT COUNT(*) FROM practice_targets").fetchone()[0],
            "instances": connection.execute(
                "SELECT COUNT(*) FROM exercise_instances").fetchone()[0],
        }


class TestPortContracts:
    def test_exact_names_methods_and_source_signatures(self):
        from app.infrastructure.sqlite.repositories.practice import SQLitePracticeRepository
        from app.infrastructure.sqlite.repositories.submission import SQLiteSubmissionRepository

        assert _public_protocol_methods(PracticeSubmissionReadPort) == {
            "get_submission_bundle",
        }
        assert _public_protocol_methods(PracticeReadPort) == {
            "list_practice_targets", "get_practice_target", "list_exercise_instances",
            "get_exercise_instance", "list_exercise_attempts",
            "list_feedback_engagement_traces", "list_transfer_evidence_candidates",
        }
        assert _public_protocol_methods(PracticeWritePort) == {
            "save_practice_target", "save_exercise_instance",
            "save_exercise_attempt", "save_practice_evaluation",
            "update_practice_target_status",
        }
        assert _public_protocol_methods(PracticeReadPort) & _public_protocol_methods(
            PracticeWritePort) == set()

        def sig(cls, name):
            return inspect.signature(getattr(cls, name))

        assert sig(PracticeSubmissionReadPort, "get_submission_bundle") == sig(
            SQLiteSubmissionRepository, "get_submission_bundle")
        for name in _public_protocol_methods(PracticeReadPort):
            assert sig(PracticeReadPort, name) == sig(SQLitePracticeRepository, name), name
        for name in _public_protocol_methods(PracticeWritePort):
            assert sig(PracticeWritePort, name) == sig(SQLitePracticeRepository, name), name

    def test_concrete_repositories_and_facade_structurally_satisfy_ports(self, tmp_path):
        database = Database(tmp_path / "ports.db")
        database.initialize()
        assert isinstance(database._submission_repository, PracticeSubmissionReadPort)
        assert isinstance(database._practice_repository, PracticeReadPort)
        assert isinstance(database._practice_repository, PracticeWritePort)

    def test_port_module_has_no_broad_or_concrete_imports(self):
        source = (ROOT / "app/practice/ports.py").read_text(encoding="utf-8")
        assert "app.database" not in source
        assert "SQLite" not in source
        assert "fastapi" not in source
        assert "get_repository" not in source


class TestPracticeServicePurity:
    def test_constructor_has_no_repository_parameter_or_field(self):
        parameters = inspect.signature(PracticeService.__init__).parameters
        assert list(parameters) == ["self"]
        service = PracticeService()
        assert not hasattr(service, "repo")
        assert not hasattr(service, "repository")
        assert hasattr(service, "specs")

    def test_service_module_has_no_persistence_dependency(self):
        source = (ROOT / "app/practice/service.py").read_text(encoding="utf-8")
        assert "self.repo" not in source
        assert "self.repository" not in source
        assert "app.database" not in source
        assert "SQLite" not in source
        assert "hasattr(" not in source
        tree = ast.parse(source)
        init = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
        assert [*init.args.args, *init.args.kwonlyargs] == [] or all(
            argument.arg == "self" for argument in [*init.args.args, *init.args.kwonlyargs]
        )
        assert len([argument for argument in [*init.args.args, *init.args.kwonlyargs]
                    if argument.arg != "self"]) == 0

    def test_domain_methods_preserved(self):
        service = PracticeService()
        target = service.create_practice_target(
            "S001", 10, "D001", "lexical_repetition_local", "Label", gate_status="selected")
        assert target["status"] == "active"
        exercise = service.generate_exercise(target, "source text here.")
        assert exercise["exercise_type"] == "guided_sentence_rewrite"
        attempt = service.submit_attempt("EX000001", "S001", "A valid response.", 1)
        assert attempt["status"] == "submitted"
        invalid = service.submit_attempt("EX000001", "S001", "   ", 2)
        assert invalid["status"] == "invalid_input"
        evaluation = service.evaluate_attempt(attempt, target, "source text here.")
        assert evaluation["completion_status"] == "completed"


class TestAppStateIdentity:
    def _assert_wiring(self, api):
        database = api.state.repository
        assert api.state.practice_submission_reader is database._submission_repository
        assert api.state.practice_reader is database._practice_repository
        assert api.state.practice_writer is database._practice_repository
        assert api.state.practice_reader is api.state.practice_writer
        assert api.state.practice_student_reader is database._learner_repository
        assert not hasattr(api.state.practice_service, "repo")
        assert api.state.practice_submission_reader._connection_manager is database._connection_manager
        assert api.state.practice_reader._connection_manager is database._connection_manager
        assert api.state.practice_student_reader._connection_manager is database._connection_manager
        assert database._revision_repository._submission_reader is database._submission_repository
        assert database._revision_repository._analysis_reader is database._analysis_repository

    def test_build_full_app_wires_facade_owned_repositories(self, tmp_path):
        api = _build_full_app(_settings(tmp_path))
        self._assert_wiring(api)

    def test_run_startup_wires_facade_owned_repositories(self, tmp_path, monkeypatch):
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


class TestRouterContract:
    def test_router_has_no_broad_facade_dependency(self):
        source = (ROOT / "app/api/routers/practice.py").read_text(encoding="utf-8")
        assert "get_repository" not in source
        assert "request.app.state" not in source
        assert "repository._" not in source
        assert "PracticeService(" not in source
        assert "require_student(" in source

    def test_router_endpoint_function_names_preserved(self):
        source = (ROOT / "app/api/routers/practice.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        names = {
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
        }
        assert names == {
            "complete_practice_target", "create_exercise", "create_practice_target",
            "get_engagement_traces",
            "get_exercise_attempts", "get_exercises", "get_practice_targets",
            "get_practice_target_context", "get_transfer_evidence",
            "get_practice_target_evaluations",
            "submit_exercise_attempt",
        }

    def test_deps_accessors_use_app_state_without_facade(self):
        source = (ROOT / "app/api/deps.py").read_text(encoding="utf-8")
        for name in ("get_practice_submission_reader", "get_practice_reader",
                     "get_practice_writer", "get_practice_student_reader",
                     "get_practice_service",
                     "get_practice_target_completion_service"):
            assert f"def {name}(request: Request):" in source
            assert f"request.app.state.{name.replace('get_practice_', 'practice_')}" in source
        assert "app.state.repository" not in source.replace(
            "request.app.state.repository", "request.app.state.other")
        assert "get_repository" not in source.split("def get_practice_")[1]


class TestApiBehavior:
    def test_full_practice_flow_persists_one_attempt_and_one_evaluation(self, tmp_path):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            _, _, exercise = _seed_flow(client)
            attempt = client.post(
                f"/api/v1/exercises/{exercise['exercise_id']}/attempts",
                json={"student_id": "F6D-S", "response_text": "A valid response reducing repetition."},
            ).json()
            assert attempt["status"] == "submitted"
            assert attempt["evaluation"] is not None
            assert attempt["evaluation"]["evaluation_id"].startswith("PE")
            database = client.app.state.repository
            counts = _row_counts(database)
            assert counts["attempts"] == 1
            assert counts["evaluations"] == 1

    def test_invalid_input_attempt_performs_zero_writes(self, tmp_path):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            _, _, exercise = _seed_flow(client)
            database = client.app.state.repository
            before = _row_counts(database)
            response = client.post(
                f"/api/v1/exercises/{exercise['exercise_id']}/attempts",
                json={"student_id": "F6D-S", "response_text": "   "},
            )
            assert response.status_code == 200
            assert response.json()["status"] == "invalid_input"
            assert _row_counts(database) == before

    def test_missing_exercise_and_unknown_student_return_404(self, tmp_path):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            _seed_flow(client)
            missing = client.post(
                "/api/v1/exercises/EX999999/attempts",
                json={"student_id": "F6D-S", "response_text": "A response."},
            )
            assert missing.status_code == 404
            unknown = client.get("/api/v1/students/S999/practice-targets")
            assert unknown.status_code == 404

    def test_read_endpoints_perform_zero_writes(self, tmp_path, monkeypatch):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            _, _, exercise = _seed_flow(client)
            database = client.app.state.repository
            calls: list[str] = []
            for name in ("save_practice_target", "save_exercise_instance",
                         "save_exercise_attempt", "save_practice_evaluation",
                         "save_feedback_engagement_trace",
                         "save_within_task_response_candidate",
                         "save_transfer_evidence_candidate",
                         "save_practice_state_snapshot"):
                original = getattr(database._practice_repository, name)

                def wrapper(*args, _name=name, _original=original, **kwargs):
                    calls.append(_name)
                    return _original(*args, **kwargs)

                monkeypatch.setattr(database._practice_repository, name, wrapper)

            assert client.get("/api/v1/students/F6D-S/practice-targets").status_code == 200
            assert client.get(
                f"/api/v1/practice-targets/{exercise['practice_target_id']}/exercises"
            ).status_code == 200
            assert client.get(
                f"/api/v1/exercises/{exercise['exercise_id']}/attempts"
            ).status_code == 200
            assert client.get("/api/v1/students/F6D-S/engagement-traces").status_code == 200
            assert client.get("/api/v1/students/F6D-S/transfer-evidence").status_code == 200
            assert calls == []


class TestFailureMatrix:
    def _attempt(self, client, exercise_id):
        return client.post(
            f"/api/v1/exercises/{exercise_id}/attempts",
            json={"student_id": "F6D-S", "response_text": "A valid response reducing repetition."},
        )

    def test_failure_before_attempt_persistence_produces_zero_rows(self, tmp_path):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            _, _, exercise = _seed_flow(client)
            database = client.app.state.repository
            counts = _row_counts(database)
            response = client.post(
                f"/api/v1/exercises/{exercise['exercise_id']}/attempts",
                json={"student_id": "F6D-S", "response_text": "   "},
            )
            assert response.status_code == 200
            assert response.json()["status"] == "invalid_input"
            assert _row_counts(database) == counts

    def test_attempt_persistence_failure_prevents_evaluation(self, tmp_path, monkeypatch):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            _, _, exercise = _seed_flow(client)
            database = client.app.state.repository

            def boom(*args, **kwargs):
                raise RuntimeError("attempt write exploded")

            monkeypatch.setattr(database._practice_repository, "save_exercise_attempt", boom)
            with pytest.raises(RuntimeError, match="attempt write exploded"):
                self._attempt(client, exercise["exercise_id"])
            counts = _row_counts(database)
            assert counts["attempts"] == 0
            assert counts["evaluations"] == 0

    def test_evaluation_generation_failure_preserves_attempt(self, tmp_path, monkeypatch):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            _, _, exercise = _seed_flow(client)
            database = client.app.state.repository

            def boom(*args, **kwargs):
                raise RuntimeError("evaluation generation exploded")

            monkeypatch.setattr(
                client.app.state.practice_service, "evaluate_attempt", boom)
            response = self._attempt(client, exercise["exercise_id"])
            assert response.status_code == 200
            assert response.json()["evaluation"] is None
            counts = _row_counts(database)
            assert counts["attempts"] == 1
            assert counts["evaluations"] == 0

    def test_evaluation_persistence_failure_preserves_attempt(self, tmp_path, monkeypatch):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            _, _, exercise = _seed_flow(client)
            database = client.app.state.repository

            def boom(*args, **kwargs):
                raise RuntimeError("evaluation write exploded")

            monkeypatch.setattr(
                database._practice_repository, "save_practice_evaluation", boom)
            response = self._attempt(client, exercise["exercise_id"])
            assert response.status_code == 200
            assert response.json()["evaluation"] is None
            counts = _row_counts(database)
            assert counts["attempts"] == 1
            assert counts["evaluations"] == 0
            attempts = client.get(
                f"/api/v1/exercises/{exercise['exercise_id']}/attempts").json()
            assert len(attempts) == 1

    def test_full_success_writes_exactly_one_attempt_and_one_evaluation(self, tmp_path):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            _, _, exercise = _seed_flow(client)
            response = self._attempt(client, exercise["exercise_id"])
            assert response.status_code == 200
            assert response.json()["evaluation"] is not None
            counts = _row_counts(client.app.state.repository)
            assert counts["attempts"] == 1
            assert counts["evaluations"] == 1
