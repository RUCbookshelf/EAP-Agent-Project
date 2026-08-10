"""v0.9.5-G focused tests: Database facade contraction.

Proves the evidence-supported retained surface (connect, initialize), the
84-method removal ledger, `SQLiteRepository` alias removal, zero production
`Depends(get_repository)` usage, the API Port contracts, facade-owned
app-state composition, and preserved Router behavior through the narrow
Ports.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.main import _build_full_app, _run_startup, create_app
from app.api.ports import (
    AnalysisRunReadPort,
    CalfReadPort,
    ResearchExportWritePort,
    RevisionGroupLookupPort,
    StudentLearnerReadPort,
    StudentLookupPort,
    StudentSubmissionListPort,
    SubmissionBundleReadPort,
    SubmissionCalibrationReadPort,
    SystemMigrationPort,
)
from app.database import Database
from tests.test_v095f2_service_narrowing import _restore_lifecycle, _snapshot_lifecycle


ROOT = Path(__file__).resolve().parents[1]
RETAINED = {"connect", "initialize"}
ROUTERS = (
    "analysis", "calf", "research", "revisions", "students", "submissions", "system",
)


def _settings(tmp_path):
    from app.config import Settings
    return Settings(
        database_path=tmp_path / "g.db", llm_provider="local", deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com", deepseek_model="deepseek-chat",
    )


def _public_protocol_methods(protocol) -> set[str]:
    return {
        name for name, value in vars(protocol).items()
        if not name.startswith("_") and callable(value)
    }


class TestFacadeSurface:
    def test_final_public_surface_is_evidence_supported(self):
        tree = ast.parse(
            (ROOT / "app/database/repository.py").read_text(encoding="utf-8"))
        facade = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "Database")
        public = {
            node.name for node in facade.body
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
        }
        assert public == RETAINED
        assert not any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "__getattr__"
            for node in ast.walk(facade)
        )
        assert not any(
            isinstance(node, ast.FunctionDef) and node.name.startswith("get_")
            and node.name not in RETAINED
            for node in facade.body
        )

    def test_facade_still_owns_one_connection_manager_and_graph(self, tmp_path):
        database = Database(tmp_path / "graph.db")
        assert database._connection_manager is not None
        assert database._system_repository._connection_manager is database._connection_manager
        assert database._submission_repository._connection_manager is database._connection_manager
        assert database._analysis_repository._connection_manager is database._connection_manager
        assert database._calf_repository._connection_manager is database._connection_manager
        assert database._revision_repository._connection_manager is database._connection_manager
        assert database._learner_repository._connection_manager is database._connection_manager
        assert database._practice_repository._connection_manager is database._connection_manager
        assert database._research_repository._connection_manager is database._connection_manager
        assert database._configuration_repository._connection_manager is database._connection_manager

    def test_removal_ledger_covers_all_84_methods_and_owners(self):
        ledger = json.loads(
            (ROOT / "verification/v0.9.5-g/removal_ledger.json").read_text(encoding="utf-8"))
        removed = ledger["removed"]
        assert len(removed) == 84
        owners = {entry["aggregate_owner"] for entry in removed}
        assert owners == {
            "system", "submission", "analysis", "calf", "learner", "revision",
            "configuration", "practice", "research",
        }
        inventory = json.loads(
            (ROOT / "verification/v0.9.5-g/before_after_facade_inventory.json")
            .read_text(encoding="utf-8"))
        assert inventory["before_public_method_count"] == 86
        assert inventory["after_public_method_count"] == 2
        assert set(inventory["retained"]) == RETAINED


class TestAliasRemoval:
    def test_sqlite_repository_alias_is_removed(self):
        init = (ROOT / "app/database/__init__.py").read_text(encoding="utf-8")
        assert "SQLiteRepository" not in init
        with pytest.raises(ImportError):
            from app.database import SQLiteRepository  # noqa: F401

    def test_no_internal_sqlite_repository_import_remains(self):
        for base in ("app", "scripts", "tests", "verification"):
            for path in (ROOT / base).rglob("*.py"):
                if "__pycache__" in path.parts or "冲突" in path.name:
                    continue
                if path.name == "repository.py" and "app/database" in str(path):
                    continue
                if path == Path(__file__).resolve():
                    continue
                if "build_database_facade.py" in path.name:
                    # Historical E-era generator that emits the legacy alias text
                    # for evidence generation; not an active import.
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                assert "SQLiteRepository" not in text, f"{path.relative_to(ROOT)}"


class TestRouterDependencyElimination:
    def test_zero_depends_get_repository_in_production(self):
        deps = (ROOT / "app/api/deps.py").read_text(encoding="utf-8")
        assert "get_repository" not in deps
        for name in ROUTERS:
            source = (ROOT / f"app/api/routers/{name}.py").read_text(encoding="utf-8")
            assert "get_repository" not in source, name
            assert "Depends(get_repository)" not in source, name
            assert "app.state.repository" not in source, name
            assert "repository._" not in source, name

    def test_api_ports_exact_method_sets(self):
        assert _public_protocol_methods(SubmissionBundleReadPort) == {"get_submission_bundle"}
        assert _public_protocol_methods(StudentLookupPort) == {"get_student"}
        assert _public_protocol_methods(AnalysisRunReadPort) == {"list_analysis_runs"}
        assert _public_protocol_methods(CalfReadPort) == {
            "list_analysis_units", "list_error_annotations",
        }
        assert _public_protocol_methods(ResearchExportWritePort) == {"save_export_job"}
        assert _public_protocol_methods(StudentSubmissionListPort) == {"list_student_submissions"}
        assert _public_protocol_methods(RevisionGroupLookupPort) == {
            "get_revision_group_for_submission",
        }
        assert _public_protocol_methods(StudentLearnerReadPort) == {
            "list_student_history", "list_history_evidence", "list_learner_profile_snapshots",
        }
        assert _public_protocol_methods(SubmissionCalibrationReadPort) == {
            "get_diagnostic_calibration",
        }
        assert _public_protocol_methods(SystemMigrationPort) == {"migration_version"}

    def test_concrete_repositories_satisfy_api_ports(self, tmp_path):
        database = Database(tmp_path / "ports.db")
        database.initialize()
        assert isinstance(database._submission_repository, SubmissionBundleReadPort)
        assert isinstance(database._learner_repository, StudentLookupPort)
        assert isinstance(database._analysis_repository, AnalysisRunReadPort)
        assert isinstance(database._calf_repository, CalfReadPort)
        assert isinstance(database._research_repository, ResearchExportWritePort)
        assert isinstance(database._submission_repository, StudentSubmissionListPort)
        assert isinstance(database._revision_repository, RevisionGroupLookupPort)
        assert isinstance(database._learner_repository, StudentLearnerReadPort)
        assert isinstance(database._calf_repository, SubmissionCalibrationReadPort)
        assert isinstance(database._system_repository, SystemMigrationPort)


class TestAppStateIdentity:
    def _assert_wiring(self, api):
        database = api.state.repository
        assert api.state.submission_bundle_reader is database._submission_repository
        assert api.state.student_lookup is database._learner_repository
        assert api.state.analysis_runs_reader is database._analysis_repository
        assert api.state.calf_reader is database._calf_repository
        assert api.state.research_export_writer is database._research_repository
        assert api.state.student_submission_list is database._submission_repository
        assert api.state.revision_group_lookup is database._revision_repository
        assert api.state.student_learner_reader is database._learner_repository
        assert api.state.submission_calibration_reader is database._calf_repository
        assert api.state.system_migration_reader is database._system_repository
        assert api.state.submission_bundle_reader._connection_manager is database._connection_manager
        assert api.state.student_lookup._connection_manager is database._connection_manager
        assert api.state.calf_reader._connection_manager is database._connection_manager
        assert database._revision_repository._submission_reader is database._submission_repository
        assert database._revision_repository._analysis_reader is database._analysis_repository

    def test_build_full_app_wires_facade_owned_readers(self, tmp_path):
        api = _build_full_app(_settings(tmp_path))
        self._assert_wiring(api)

    def test_run_startup_wires_facade_owned_readers(self, tmp_path, monkeypatch):
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


class TestMigratedRouterBehavior:
    def test_version_endpoint_reports_migration_via_system_port(self, tmp_path):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            response = client.get("/api/v1/system/version")
            assert response.status_code == 200
            assert response.json()["database_migration_version"] == 14

    def test_student_and_history_endpoints_use_narrow_readers(self, tmp_path):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            created = client.post("/api/v1/submissions", json={
                "student_id": "G-S", "writing_prompt": "What actions matter for sustainability?",
                "genre": "argumentative essay", "draft_stage": "first draft",
                "timed": False, "tool_use": "none",
                "essay_text": "People should protect the environment. People should recycle more.",
            })
            assert created.status_code == 201
            student = client.get("/api/v1/students/G-S")
            assert student.status_code == 200
            history = client.get("/api/v1/students/G-S/history")
            assert history.status_code == 200
            assert len(history.json()["submissions"]) == 1
            unknown = client.get("/api/v1/students/S999")
            assert unknown.status_code == 404
            analyses = client.get(
                f"/api/v1/submissions/{created.json()['submission_id']}/analyses")
            assert analyses.status_code == 200
            assert len(analyses.json()["analysis_runs"]) == 1

    def test_research_export_best_effort_block_preserved(self, tmp_path):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            payload = {
                "filter_spec": {},
                "privacy_mode": "internal_research",
                "formats": ["jsonl"],
            }
            response = client.post("/api/v1/research/export/run", json=payload)
            assert response.status_code == 200
            assert "export_id" in response.json()

    def test_revision_student_candidates_route_through_narrow_readers(self, tmp_path):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            client.post("/api/v1/submissions", json={
                "student_id": "G-R", "writing_prompt": "P",
                "genre": "argumentative essay", "draft_stage": "first draft",
                "timed": False, "tool_use": "none",
                "essay_text": "Students should protect public parks because green space matters.",
            })
            candidates = client.get("/api/v1/students/G-R/revision-candidates")
            assert candidates.status_code == 200
            assert len(candidates.json()["candidates"]) == 1
