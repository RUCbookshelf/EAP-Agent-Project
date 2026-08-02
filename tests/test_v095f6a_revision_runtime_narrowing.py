"""v0.9.5-F6A focused tests: RevisionService runtime repository narrowing.

Proves that every active construction path supplies the existing
facade-owned SQLiteRevisionRepository instance (never the broad Database
facade), that the Submission factory, AdminReanalysisService, and
FeedbackPipeline use the narrowed runtime repository, and that Revision
behavior and the three-sequential-commit relationship workflow are
preserved, including commit-1/commit-2 visibility on later-call failures.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.main import _build_full_app, _run_startup, create_app
from app.config import Settings
from app.database import Database
from app.feedback.service import FeedbackPipeline
from app.models import EssaySubmission
from app.services import build_submission_service
from app.services.admin_reanalysis import AdminReanalysisService
from app.services.revision import RevisionService
from tests.test_v095f2_service_narrowing import _restore_lifecycle, _snapshot_lifecycle


ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "f6a.db",
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
    )


def _submission(student_id: str, prompt: str = "P", *, stage: str = "first draft") -> EssaySubmission:
    return EssaySubmission(
        student_id=student_id,
        writing_prompt=prompt,
        genre="argumentative essay",
        draft_stage=stage,
        timed=False,
        tool_use="none",
        essay_text="Students should protect public parks because green space matters for communities.",
        submitted_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )


def _seed_first(tmp_path: Path, db: Database) -> int:
    """Submit one essay with no revision relationship; returns its essay_id."""
    submission_service = build_submission_service(
        _settings(tmp_path), db, revision_repository=db._revision_repository,
    )
    return submission_service.submit(_submission("F6A-S"), synthetic=True).essay_id


def _submit_plain(tmp_path: Path, db: Database, *, stage: str = "first draft") -> int:
    """Submit an essay for the seeded student with no revision relationship."""
    submission_service = build_submission_service(
        _settings(tmp_path), db, revision_repository=db._revision_repository,
    )
    return submission_service.submit(
        _submission("F6A-S", "P", stage=stage), synthetic=True,
    ).essay_id


class TestRuntimeIdentity:
    def _assert_wiring(self, api: FastAPI) -> None:
        database = api.state.repository
        revisions = api.state.revisions
        assert revisions.repository is database._revision_repository
        assert not isinstance(revisions.repository, Database)
        assert revisions.repository._connection_manager is database._connection_manager
        assert revisions.repository._submission_reader is database._submission_repository
        assert revisions.repository._analysis_reader is database._analysis_repository
        assert api.state.submission_service.revision_service.repository is database._revision_repository
        assert api.state.admin_reanalysis.revisions.repository is database._revision_repository

    def test_build_full_app_wires_facade_owned_revision_repository(self, tmp_path):
        api = _build_full_app(_settings(tmp_path))
        self._assert_wiring(api)

    def test_run_startup_wires_facade_owned_revision_repository(self, tmp_path, monkeypatch):
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

    def test_factory_builds_submission_service_with_facade_owned_revision_repository(self, tmp_path):
        database = Database(tmp_path / "factory.db")
        database.initialize()
        service = build_submission_service(
            _settings(tmp_path), database,
            revision_repository=database._revision_repository,
        )
        assert service.revision_service.repository is database._revision_repository
        assert not isinstance(service.revision_service.repository, Database)

    def test_admin_reanalysis_embedded_revision_composition(self, tmp_path):
        database = Database(tmp_path / "admin.db")
        database.initialize()
        settings = _settings(tmp_path)
        submission_service = build_submission_service(
            settings, database, revision_repository=database._revision_repository,
        )
        admin = AdminReanalysisService(
            database, settings, None, submission_service,
            revision_repository=database._revision_repository,
        )
        assert admin.revisions.repository is database._revision_repository
        assert not isinstance(admin.revisions.repository, Database)
        assert admin.repository is database

    def test_feedback_pipeline_uses_facade_owned_revision_repository(self, tmp_path):
        database = Database(tmp_path / "pipeline.db")
        settings = _settings(tmp_path)
        pipeline = FeedbackPipeline(settings, database=database)
        assert pipeline._service.revision_service.repository is database._revision_repository
        assert not isinstance(pipeline._service.revision_service.repository, Database)


class TestRuntimeContracts:
    def test_revision_service_module_unchanged_and_contract_preserved(self):
        source = (ROOT / "app/services/revision.py").read_text(encoding="utf-8")
        assert "app.database" not in source
        assert "SQLite" not in source
        assert "hasattr(" not in source
        signature = inspect.signature(RevisionService.__init__)
        assert "RevisionRepository" in str(signature.parameters["repository"].annotation)

    def test_no_new_revision_port_and_central_protocol_unchanged(self):
        protocols = (ROOT / "app/repositories/protocols.py").read_text(encoding="utf-8")
        assert "RevisionServicePort" not in protocols
        assert "RevisionRuntimePort" not in protocols
        assert "RevisionReadWritePort" not in protocols
        source = (ROOT / "app/services/revision.py").read_text(encoding="utf-8")
        assert "Protocol" not in source

    def test_no_active_construction_uses_the_broad_facade(self):
        for rel in ("app/api/main.py", "app/services/factory.py", "app/services/admin_reanalysis.py"):
            source = (ROOT / rel).read_text(encoding="utf-8")
            assert "RevisionService(repository)" not in source
            assert "RevisionService(self.database)" not in source
        pipeline = (ROOT / "app/feedback/service.py").read_text(encoding="utf-8")
        assert "RevisionService(self.database._revision_repository)" in pipeline


class TestRevisionBehavior:
    def test_relationship_flow_and_api_paths_via_narrowed_runtime(self, tmp_path):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            first = client.post("/api/v1/submissions", json={
                "student_id": "F6A-API", "writing_prompt": "P",
                "genre": "argumentative essay", "draft_stage": "first draft",
                "timed": False, "tool_use": "none",
                "essay_text": "Students should protect public parks because green space matters.",
            })
            assert first.status_code == 201
            second = client.post("/api/v1/submissions", json={
                "student_id": "F6A-API", "writing_prompt": "P",
                "genre": "argumentative essay", "draft_stage": "revised draft",
                "timed": False, "tool_use": "none",
                "essay_text": "Students should protect public parks because green space matters for everyone.",
            })
            assert second.status_code == 201
            repository = client.app.state.repository
            assert client.app.state.revisions.repository is repository._revision_repository
            created = client.post("/api/v1/revisions", json={
                "source_submission_id": first.json()["submission_id"],
                "target_submission_id": second.json()["submission_id"],
            })
            assert created.status_code == 201
            group_id = created.json()["group"]["revision_group_id"]
            assert client.get(f"/api/v1/revisions/{group_id}").status_code == 200
            assert client.get(f"/api/v1/revisions/{group_id}/trajectory").status_code == 200
            assert client.get(f"/api/v1/revisions/{group_id}/comparison").status_code == 200

    def test_candidates_and_snapshot_reads_via_narrowed_runtime(self, tmp_path):
        database = Database(tmp_path / "behavior.db")
        database.initialize()
        first = _seed_first(tmp_path, database)
        second = _submit_plain(tmp_path, database)
        revisions = RevisionService(database._revision_repository)
        snapshot = revisions.create_relationship(first, second)
        assert snapshot.target_submission_id == second
        candidates = revisions.candidates(first)
        assert candidates and all(item["essay_id"] != first for item in candidates)
        group = revisions.group(snapshot.revision_group_id)
        assert group.member_submission_ids == [first, second]
        assert revisions.latest(snapshot.revision_group_id).target_submission_id == second
        assert len(revisions.history(snapshot.revision_group_id)) == 1


class TestTransactionFailureSemantics:
    def test_successful_creation_preserves_three_call_order(self, tmp_path, monkeypatch):
        database = Database(tmp_path / "tx-ok.db")
        database.initialize()
        first = _seed_first(tmp_path, database)
        second = _submit_plain(tmp_path, database, stage="revised draft")
        rev_repo = database._revision_repository
        calls: list[str] = []
        originals = {
            "create_revision_group": rev_repo.create_revision_group,
            "link_revision": rev_repo.link_revision,
            "save_revision_snapshot": rev_repo.save_revision_snapshot,
        }

        def rec(name):
            def wrapper(*args, **kwargs):
                calls.append(name)
                return originals[name](*args, **kwargs)
            return wrapper

        for name, original in originals.items():
            monkeypatch.setattr(rev_repo, name, rec(name))

        snapshot = RevisionService(database._revision_repository).create_relationship(first, second)

        assert calls == ["create_revision_group", "link_revision", "save_revision_snapshot"]
        assert snapshot.target_submission_id == second
        with database.connect() as connection:
            assert connection.execute("SELECT COUNT(*) FROM revision_groups").fetchone()[0] == 1
            assert connection.execute("SELECT COUNT(*) FROM revision_snapshots").fetchone()[0] == 1

    def test_commit_1_remains_visible_when_link_revision_fails(self, tmp_path, monkeypatch):
        database = Database(tmp_path / "tx-fail2.db")
        database.initialize()
        first = _seed_first(tmp_path, database)
        second = _submit_plain(tmp_path, database, stage="revised draft")
        rev_repo = database._revision_repository

        def boom_link(*args, **kwargs):
            raise RuntimeError("link exploded")

        monkeypatch.setattr(rev_repo, "link_revision", boom_link)

        with pytest.raises(RuntimeError, match="link exploded"):
            RevisionService(database._revision_repository).create_relationship(first, second)

        with database.connect() as connection:
            groups = connection.execute("SELECT revision_group_id FROM revision_groups").fetchall()
            snapshots = connection.execute("SELECT revision_group_id FROM revision_snapshots").fetchall()
            source = connection.execute(
                "SELECT revision_group_id FROM essays WHERE essay_id=?", (first,)
            ).fetchone()
            target = connection.execute(
                "SELECT revision_group_id, revision_of_submission_id, revision_sequence FROM essays WHERE essay_id=?",
                (second,),
            ).fetchone()
        assert len(groups) == 1
        assert len(snapshots) == 0
        assert source["revision_group_id"] is not None
        assert target["revision_group_id"] is None
        assert target["revision_of_submission_id"] is None

    def test_commits_1_and_2_remain_visible_when_save_snapshot_fails(self, tmp_path, monkeypatch):
        database = Database(tmp_path / "tx-fail3.db")
        database.initialize()
        first = _seed_first(tmp_path, database)
        second = _submit_plain(tmp_path, database, stage="revised draft")
        rev_repo = database._revision_repository

        def boom_save(*args, **kwargs):
            raise RuntimeError("snapshot exploded")

        monkeypatch.setattr(rev_repo, "save_revision_snapshot", boom_save)

        with pytest.raises(RuntimeError, match="snapshot exploded"):
            RevisionService(database._revision_repository).create_relationship(first, second)

        with database.connect() as connection:
            groups = connection.execute("SELECT revision_group_id FROM revision_groups").fetchall()
            snapshots = connection.execute("SELECT revision_group_id FROM revision_snapshots").fetchall()
            target = connection.execute(
                "SELECT revision_group_id, revision_of_submission_id, revision_sequence FROM essays WHERE essay_id=?",
                (second,),
            ).fetchone()
        assert len(groups) == 1
        assert len(snapshots) == 0
        assert target["revision_group_id"] is not None
        assert target["revision_of_submission_id"] == first
        assert target["revision_sequence"] == 2

    def test_essay_updates_remain_inside_revision_repository_methods(self):
        source = (ROOT / "app/infrastructure/sqlite/repositories/revision.py").read_text(encoding="utf-8")
        assert "UPDATE essays" in source.split("def link_revision")[1].split("def get_revision_group")[0]
