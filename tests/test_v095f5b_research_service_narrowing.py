"""v0.9.5-F5B focused tests: ResearchDataService dependency narrowing.

Covers the three consumer-owned Ports, minimal-stub behavior for
ResearchDataService (collection, human/PII review, Export Job reads, export
generation), hasattr-removal contracts, app-composition wiring in both
construction paths, and the unchanged Router-owned best-effort
save_export_job boundary.
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.main import _build_full_app, _run_startup, create_app
from app.config import Settings
from app.database import Database
from app.infrastructure.sqlite.repositories.research import SQLiteResearchRepository
from app.infrastructure.sqlite.repositories.submission import SQLiteSubmissionRepository
from app.research.schemas import (
    ExportFilter,
    ExportFormat,
    ExportJob,
    HumanReviewCreate,
    HumanReviewDecision,
    HumanReviewTarget,
    PrivacyMode,
)
from app.research.service import (
    ResearchDataService,
    ResearchExportReadPort,
    ResearchReviewPort,
    ResearchSubmissionReadPort,
)
from tests.test_v095f2_service_narrowing import _restore_lifecycle, _snapshot_lifecycle


ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "f5b.db",
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


def _submission(student_id: str, essay_id: int, prompt: str = "P") -> dict:
    return {
        "essay_id": essay_id,
        "student_id": student_id,
        "writing_prompt": prompt,
        "genre": "argumentative essay",
        "draft_stage": "first draft",
        "timed": False,
        "time_limit_minutes": None,
        "tool_use": "none",
        "submitted_at": "2026-08-02T10:00:00+00:00",
        "revision_of_submission_id": None,
        "revision_group_id": None,
    }


class MinimalSubmissionReader:
    def __init__(self, submissions=None, bundles=None):
        self.all = list(submissions or [])
        self.bundles = dict(bundles or {})
        self.calls: list[str] = []

    def list_all_submissions(self):
        self.calls.append("list_all_submissions")
        return [dict(item) for item in self.all]

    def list_student_submissions(self, student_id: str):
        self.calls.append("list_student_submissions")
        return [dict(item) for item in self.all if item.get("student_id") == student_id]

    def get_submission_bundle(self, essay_id: int):
        self.calls.append("get_submission_bundle")
        return self.bundles.get(essay_id)


class MinimalReviewRepository:
    def __init__(self, reviews=None, pii_results=None):
        self.reviews = list(reviews or [])
        self.pii_results = list(pii_results or [])
        self.saved = []
        self.calls: list[str] = []
        self.save_exception: Exception | None = None

    def save_human_review(self, review) -> dict:
        self.calls.append("save_human_review")
        if self.save_exception is not None:
            raise self.save_exception
        self.saved.append(review)
        return review.model_dump(mode="json")

    def list_human_reviews(self, target_type: str | None = None, target_id: str | None = None):
        self.calls.append("list_human_reviews")
        return list(self.reviews)

    def apply_pii_review(self, submission_id: int, reviews: list):
        self.calls.append("apply_pii_review")
        if self.save_exception is not None:
            raise self.save_exception
        return list(self.pii_results)


class MinimalExportReader:
    def __init__(self, jobs=None):
        self.jobs = list(jobs or [])
        self.calls: list[str] = []

    def list_export_jobs(self):
        self.calls.append("list_export_jobs")
        return list(self.jobs)

    def get_export_job(self, export_id: str):
        self.calls.append("get_export_job")
        return next((job for job in self.jobs if job.get("export_id") == export_id), None)


def _service(submission=None, review=None, export=None) -> ResearchDataService:
    return ResearchDataService(
        submission_reader=submission or MinimalSubmissionReader(),
        review_repository=review or MinimalReviewRepository(),
        export_reader=export or MinimalExportReader(),
    )


def _job(*, formats=None, privacy_mode=PrivacyMode.PSEUDONYMIZED) -> ExportJob:
    return ExportJob(
        filter_spec=ExportFilter(),
        privacy_mode=privacy_mode,
        formats=formats or [ExportFormat.JSONL],
    )


class TestThreePorts:
    def test_exact_names_methods_and_source_signatures(self):
        assert _public_protocol_methods(ResearchSubmissionReadPort) == {
            "list_all_submissions",
            "list_student_submissions",
            "get_submission_bundle",
        }
        assert _public_protocol_methods(ResearchReviewPort) == {
            "save_human_review",
            "list_human_reviews",
            "apply_pii_review",
        }
        assert _public_protocol_methods(ResearchExportReadPort) == {
            "list_export_jobs",
            "get_export_job",
        }

        assert inspect.signature(ResearchSubmissionReadPort.list_all_submissions) == inspect.signature(
            SQLiteSubmissionRepository.list_all_submissions
        )
        assert inspect.signature(ResearchSubmissionReadPort.list_student_submissions) == inspect.signature(
            SQLiteSubmissionRepository.list_student_submissions
        )
        assert inspect.signature(ResearchSubmissionReadPort.get_submission_bundle) == inspect.signature(
            SQLiteSubmissionRepository.get_submission_bundle
        )
        assert inspect.signature(ResearchReviewPort.save_human_review) == inspect.signature(
            SQLiteResearchRepository.save_human_review
        )
        assert inspect.signature(ResearchReviewPort.list_human_reviews) == inspect.signature(
            SQLiteResearchRepository.list_human_reviews
        )
        assert inspect.signature(ResearchReviewPort.apply_pii_review) == inspect.signature(
            SQLiteResearchRepository.apply_pii_review
        )
        assert inspect.signature(ResearchExportReadPort.list_export_jobs) == inspect.signature(
            SQLiteResearchRepository.list_export_jobs
        )
        assert inspect.signature(ResearchExportReadPort.get_export_job) == inspect.signature(
            SQLiteResearchRepository.get_export_job
        )

    def test_concrete_repositories_and_facade_structurally_satisfy_ports(self, tmp_path):
        database = Database(tmp_path / "ports.db")
        submission = database._submission_repository
        research = database._research_repository

        assert isinstance(submission, ResearchSubmissionReadPort)
        assert isinstance(research, ResearchReviewPort)
        assert isinstance(research, ResearchExportReadPort)
        # The same repository instance satisfies both Research-owned Ports.
        assert isinstance(research, ResearchReviewPort) and isinstance(research, ResearchExportReadPort)


class TestServiceNarrowing:
    def test_minimal_stubs_are_sufficient_and_collection_preserves_call_order(self):
        submissions = [
            _submission("S001", 1),
            _submission("S001", 2),
            _submission("S002", 3),
        ]
        submission = MinimalSubmissionReader(submissions)
        service = _service(submission=submission)

        preview = service.preview(_job())

        assert submission.calls == [
            "list_all_submissions",
            "list_student_submissions",
            "list_student_submissions",
        ]
        assert preview["student_count"] == 2
        assert preview["essay_count"] == 3
        assert preview["included_count"] == 3
        assert preview["excluded_count"] == 0

    def test_scan_pii_missing_bundle_raises_and_performs_zero_review_writes(self):
        submission = MinimalSubmissionReader(bundles={})
        review = MinimalReviewRepository()
        service = _service(submission=submission, review=review)

        with pytest.raises(LookupError, match="Submission not found"):
            service.scan_pii(99)

        assert submission.calls == ["get_submission_bundle"]
        assert review.calls == []

    def test_scan_pii_with_bundle_returns_scanner_output(self):
        submission = MinimalSubmissionReader(bundles={1: {"essay_text": "Call me at 13800138000."}})
        service = _service(submission=submission)

        candidates = service.scan_pii(1)

        assert any(item["category"] == "phone" for item in candidates)

    def test_create_human_review_performs_exactly_one_repository_write(self):
        review = MinimalReviewRepository()
        service = _service(review=review)
        created = HumanReviewCreate(
            target_type=HumanReviewTarget.DIAGNOSIS, target_id="D001",
            reviewer_id="R001", decision=HumanReviewDecision.PARTIALLY_CORRECT,
            confidence="medium", reason_code="evidence_relevant_but_priority_too_high",
            comment="", guideline_version="human-review-v0.1",
        )

        result = service.create_human_review(created)

        assert review.calls == ["save_human_review"]
        assert len(review.saved) == 1
        assert review.saved[0].reviewer_id == "R001"
        assert result.target_id == "D001"

    def test_human_review_repository_exception_propagates(self):
        review = MinimalReviewRepository()
        review.save_exception = RuntimeError("review store failed")
        service = _service(review=review)
        created = HumanReviewCreate(
            target_type=HumanReviewTarget.EVIDENCE, target_id="E001",
            reviewer_id="R001", decision=HumanReviewDecision.INCORRECT,
            confidence="high", reason_code="offset_incorrect",
            comment="", guideline_version="human-review-v0.1",
        )

        with pytest.raises(RuntimeError, match="review store failed"):
            service.create_human_review(created)

        assert review.calls == ["save_human_review"]

    def test_get_human_reviews_routes_with_filters_and_returns_stub_output(self):
        review = MinimalReviewRepository(reviews=[{"review_id": "HR000001", "target_id": "D001"}])
        service = _service(review=review)

        result = service.get_human_reviews("diagnosis", "D001")

        assert review.calls == ["list_human_reviews"]
        assert result == [{"review_id": "HR000001", "target_id": "D001"}]

    def test_apply_pii_review_performs_one_bundle_read_and_one_repository_write(self):
        submission = MinimalSubmissionReader(bundles={7: {"essay_text": "Text."}})
        review = MinimalReviewRepository(pii_results=[{"pii_candidate_id": "PC000001"}])
        service = _service(submission=submission, review=review)

        result = service.apply_pii_review(7, [])

        assert submission.calls == ["get_submission_bundle"]
        assert review.calls == ["apply_pii_review"]
        assert result == [{"pii_candidate_id": "PC000001"}]

    def test_apply_pii_review_missing_bundle_performs_zero_repository_writes(self):
        submission = MinimalSubmissionReader(bundles={})
        review = MinimalReviewRepository()
        service = _service(submission=submission, review=review)

        with pytest.raises(LookupError, match="Submission not found"):
            service.apply_pii_review(99, [])

        assert submission.calls == ["get_submission_bundle"]
        assert review.calls == []

    def test_export_job_reads_retain_output_ordering_and_missing_behavior(self):
        jobs = [
            {"export_id": "EXP000002", "status": "completed"},
            {"export_id": "EXP000001", "status": "completed"},
        ]
        export = MinimalExportReader(jobs)
        service = _service(export=export)

        history = service.export_history()
        assert export.calls == ["list_export_jobs"]
        assert history == jobs

        status = service.export_status("EXP000001")
        assert export.calls == ["list_export_jobs", "get_export_job"]
        assert status == {"export_id": "EXP000001", "status": "completed"}

        unknown = service.export_status("NOPE")
        assert export.calls == ["list_export_jobs", "get_export_job", "get_export_job"]
        assert unknown == {"export_id": "NOPE", "status": "unknown"}

    def test_run_export_writes_expected_files_and_matches_preview(self, tmp_path, monkeypatch):
        import app.research.service as research_module
        submissions = [
            _submission("S001", 1, "Prompt A"),
            _submission("S001", 2, "Prompt B"),
        ]
        monkeypatch.setattr(research_module, "_EXPORT_BASE", str(tmp_path / "exports"))
        service = _service(submission=MinimalSubmissionReader(submissions))
        job = _job(formats=[ExportFormat.JSONL, ExportFormat.CSV], privacy_mode=PrivacyMode.INTERNAL_RESEARCH)

        preview = service.preview(job)
        result = service.run_export(job)

        assert preview["essay_count"] == 2
        assert result["record_counts"] == {"jsonl": 2, "csv": 2}
        records = [json.loads(line) for line in
                   Path(result["export_directory"]).joinpath("records.jsonl")
                   .read_text(encoding="utf-8").splitlines()]
        assert [r["record_id"] for r in records] == ["SUB-1", "SUB-2"]
        assert all(r["export_schema_version"] == "research-export-v0.1" for r in records)
        manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
        assert manifest["privacy_mode"] == "internal_research"
        assert result["status"] == "completed"

    def test_service_never_calls_save_export_job_or_discovery(self):
        source = (ROOT / "app/research/service.py").read_text(encoding="utf-8")
        assert "save_export_job" not in source
        assert "hasattr(" not in source
        assert "self.repo" not in source
        assert "app.database" not in source
        assert "SQLite" not in source
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
                "ResearchSubmissionReadPort", "ResearchReviewPort", "ResearchExportReadPort",
            }
            for annotation in annotations
        )


class TestComposition:
    def _assert_wiring(self, api: FastAPI) -> None:
        database = api.state.repository
        research = api.state.research
        assert research.submission_reader is database._submission_repository
        assert research.review_repository is database._research_repository
        assert research.export_reader is database._research_repository
        assert research.review_repository is research.export_reader
        assert research.submission_reader._connection_manager is database._connection_manager
        assert research.review_repository._connection_manager is database._connection_manager
        assert research.export_reader._connection_manager is database._connection_manager
        assert not isinstance(research, Database)

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

    def test_research_router_source_constructs_nothing_and_keeps_best_effort_write(self):
        source = (ROOT / "app/api/routers/research.py").read_text(encoding="utf-8")
        assert "get_research" in source
        assert "get_research_export_writer" in source
        assert "get_repository" not in source
        assert "save_export_job" in source
        assert "ResearchDataService(" not in source
        assert "app.research.service" not in source


class TestRouterBoundary:
    def _export_payload(self) -> dict:
        return {
            "filter_spec": {},
            "privacy_mode": "internal_research",
            "formats": ["jsonl"],
        }

    def test_export_run_router_attempts_save_export_job_and_preserves_response(self, tmp_path):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            payload = self._export_payload()
            created = client.post("/api/v1/submissions", json={
                "student_id": "F5B-EXP", "writing_prompt": "P",
                "genre": "argumentative essay", "draft_stage": "first draft",
                "timed": False, "tool_use": "none",
                "essay_text": "Research export router boundary test essay content.",
            })
            assert created.status_code == 201
            result = client.post("/api/v1/research/export/run", json=payload)
            assert result.status_code == 200
            body = result.json()
            assert body["status"] == "completed"
            assert body["export_directory"]
            repository = client.app.state.repository
            jobs = repository._research_repository.list_export_jobs()
            assert len(jobs) == 1
            assert jobs[0]["export_id"] == body["export_id"]
            history = client.get("/api/v1/research/export/history")
            assert history.status_code == 200
            assert history.json()[0]["export_id"] == body["export_id"]
            status = client.get(f"/api/v1/research/export/{body['export_id']}")
            assert status.status_code == 200
            assert status.json()["status"] == "completed"

    def test_export_run_best_effort_failure_preserves_completed_export(self, tmp_path):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            repository = client.app.state.repository

            def _boom(job: dict) -> dict:
                raise RuntimeError("audit row failed")

            repository._research_repository.save_export_job = _boom
            payload = self._export_payload()
            created = client.post("/api/v1/submissions", json={
                "student_id": "F5B-EXP2", "writing_prompt": "P",
                "genre": "argumentative essay", "draft_stage": "first draft",
                "timed": False, "tool_use": "none",
                "essay_text": "Best-effort audit row failure keeps the completed export.",
            })
            assert created.status_code == 201
            result = client.post("/api/v1/research/export/run", json=payload)
            assert result.status_code == 200
            body = result.json()
            assert body["status"] == "completed"
            assert len(repository._research_repository.list_export_jobs()) == 0
            # Without an audit row the manifest lookup is unknown -> 404 (unchanged behavior).
            manifest = client.get(f"/api/v1/research/export/{body['export_id']}/manifest")
            assert manifest.status_code == 404
            # The completed export files still exist on disk.
            assert Path(body["export_directory"]).joinpath("records.jsonl").exists()
            assert Path(body["export_directory"]).joinpath("manifest.json").exists()

    def test_export_endpoint_error_paths_unchanged(self, tmp_path):
        settings = _settings(tmp_path)
        with TestClient(create_app(settings)) as client:
            invalid = client.post("/api/v1/research/export/run", json={"privacy_mode": "bogus"})
            assert invalid.status_code == 422
            unknown = client.get("/api/v1/research/export/NOPE/manifest")
            assert unknown.status_code == 404
            assert client.get("/api/v1/research/export/NOPE").json() == {
                "export_id": "NOPE", "status": "unknown",
            }


class TestVerificationHelperSite:
    def test_capture_helper_uses_three_explicit_repositories(self):
        source = (ROOT / "verification/v0.9.5-e/capture_prechange_fresh_database.py").read_text(encoding="utf-8")
        assert "ResearchDataService(\n        submission_reader=database._submission_repository," in source
        assert "review_repository=database._research_repository," in source
        assert "export_reader=database._research_repository," in source
        assert "ResearchDataService(database)" not in source
