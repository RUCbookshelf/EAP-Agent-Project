"""v0.9.7-B WU3 focused tests: idempotent target creation and reuse.

Covers the allocator repair (two/three-character prefixes), migration 13
(one-active-priority-key uniqueness), the create-or-reuse workflow, general
ownership validation, legacy compatibility, and WU3 scope guards. All
persistence runs on isolated databases with the local provider only.
"""

from __future__ import annotations

import json
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

os.environ.setdefault("LLM_PROVIDER", "local")

from fastapi.testclient import TestClient  # noqa: E402

from app.api.main import create_app  # noqa: E402
from app.config import Settings  # noqa: E402
from app.database import Database  # noqa: E402
from app.database.migrations import MIGRATIONS, rollback, upgrade  # noqa: E402
from app.models import EssaySubmission  # noqa: E402
from app.practice.mapping import (  # noqa: E402
    PriorityMappingError,
    PriorityPracticeMappingService,
)
from app.practice.schemas import (  # noqa: E402
    FeedbackEngagementTrace,
    PracticeStateSnapshot,
)
from app.practice.service import PracticeService  # noqa: E402
from app.practice.target_creation import PracticeTargetCreationService  # noqa: E402
from app.services import build_submission_service  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]

REPETITION_ESSAY = (
    "People should protect the environment. People should recycle more. "
    "People should save water. People should plant trees. People should reduce waste. "
    "People should use public transport. People should teach children about nature. "
    "People should value clean air."
)


def _settings(tmp_path) -> Settings:
    return Settings(
        database_path=tmp_path / "wu3.db", llm_provider="local", deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com", deepseek_model="deepseek-chat",
    )


@pytest.fixture()
def repo(tmp_path):
    db = Database(tmp_path / "wu3.db")
    db.initialize()
    return db


def _creation_service(repo) -> PracticeTargetCreationService:
    return PracticeTargetCreationService(
        submission_reader=repo._submission_repository,
        practice_reader=repo._practice_repository,
        practice_writer=repo._practice_repository,
        practice_service=PracticeService(),
    )


def _submission_service(repo):
    from app.config import load_settings

    return build_submission_service(
        load_settings(),
        system_repository=repo._system_repository,
        submission_repository=repo._submission_repository,
        analysis_repository=repo._analysis_repository,
        calibration_repository=repo._calf_repository,
        learner_repository=repo._learner_repository,
        configuration_repository=repo._configuration_repository,
        revision_repository=repo._revision_repository,
    )


def _essay(student_id: str = "WU3-S") -> EssaySubmission:
    return EssaySubmission(
        student_id=student_id,
        writing_prompt="What actions matter for sustainability?",
        genre="argumentative essay",
        draft_stage="first draft",
        timed=False,
        tool_use="none",
        essay_text=REPETITION_ESSAY,
    )


def _seed_submission(repo, student_id: str = "WU3-S") -> tuple[int, dict, int]:
    """Create one persisted submission; return (essay_id, record, priority_index)."""
    result = _submission_service(repo).submit(_essay(student_id), synthetic=True)
    record = repo._submission_repository.get_feedback_record(result.essay_id)
    priorities = json.loads(record["feedback_json"])["priority_feedback"]
    index = next(
        i for i, item in enumerate(priorities)
        if item.get("category") == "lexical_repetition"
    )
    return result.essay_id, record, index


def _contract(repo, essay_id: int, record: dict, index: int,
              student_id: str = "WU3-S"):
    return PriorityPracticeMappingService(repo._submission_repository).resolve_target_contract(
        student_id=student_id,
        source_submission_id=essay_id,
        source_priority_id=f"PRIO-{record['feedback_id']}-{index}",
    )


def _target_count(repo) -> int:
    with repo.connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM practice_targets").fetchone()[0]


def _insert_target_row(repo, practice_target_id: str, student_id: str,
                       source_submission_id: int, priority_reference: str | None,
                       status: str = "active") -> None:
    target = PracticeService().create_practice_target(
        student_id=student_id, source_submission_id=source_submission_id,
        source_diagnosis_id="D001", target_code="lexical_repetition_local",
        target_label="Label", source_priority_id=priority_reference,
        evidence_ids=[], gate_status="selected",
    )
    target["status"] = status
    target["practice_target_id"] = practice_target_id
    with repo.connect() as conn:
        conn.execute(
            "INSERT INTO practice_targets VALUES (?,?,?,?,?,?,?,?,?)",
            (
                practice_target_id, student_id, source_submission_id, "D001",
                "lexical_repetition_local", "Label", status,
                "2026-01-01T00:00:00+00:00",
                json.dumps(target),
            ),
        )


class TestAllocator:
    def test_two_character_prefix_allocation(self, repo):
        svc = PracticeService()
        saved = []
        for i in range(3):
            target = svc.create_practice_target(
                f"S{i}", 10 + i, "D001", "lexical_repetition_local", f"Label{i}")
            saved.append(repo._practice_repository.save_practice_target(target))
        assert [t["practice_target_id"] for t in saved] == [
            "PT000001", "PT000002", "PT000003",
        ]

    def test_exercise_attempt_evaluation_prefixes(self, repo):
        svc = PracticeService()
        target = svc.create_practice_target(
            "S1", 10, "D001", "lexical_repetition_local", "Label")
        target = repo._practice_repository.save_practice_target(target)
        exercise = svc.generate_exercise(target, "Source text here.")
        exercise = repo._practice_repository.save_exercise_instance(exercise)
        assert exercise["exercise_id"] == "EX000001"
        second_exercise = svc.generate_exercise(target, "More source text.")
        assert repo._practice_repository.save_exercise_instance(
            second_exercise)["exercise_id"] == "EX000002"
        attempt = svc.submit_attempt(exercise["exercise_id"], "S1", "A valid response.", 1)
        attempt = repo._practice_repository.save_exercise_attempt(attempt)
        assert attempt["attempt_id"] == "EA000001"
        second_attempt = svc.submit_attempt(
            exercise["exercise_id"], "S1", "Another valid response.", 2)
        assert repo._practice_repository.save_exercise_attempt(
            second_attempt)["attempt_id"] == "EA000002"
        evaluation = svc.evaluate_attempt(attempt, target, "Source text here.")
        evaluation = repo._practice_repository.save_practice_evaluation(evaluation)
        assert evaluation["evaluation_id"] == "PE000001"
        assert repo._practice_repository.save_practice_evaluation(
            svc.evaluate_attempt(attempt, target, "Source text here.")
        )["evaluation_id"] == "PE000002"

    def test_three_character_prefix_allocation(self, repo):
        svc = PracticeService()
        first_trace = repo._practice_repository.save_feedback_engagement_trace(
            FeedbackEngagementTrace(
                student_id="S1", target_code="lexical_repetition_local"
            ).model_dump(mode="json"))
        second_trace = repo._practice_repository.save_feedback_engagement_trace(
            FeedbackEngagementTrace(
                student_id="S1", target_code="connective_overuse"
            ).model_dump(mode="json"))
        assert [first_trace["trace_id"], second_trace["trace_id"]] == [
            "FET000001", "FET000002",
        ]
        target = svc.create_practice_target(
            "S1", 10, "D001", "lexical_repetition_local", "Label")
        candidate = svc.evaluate_within_task_response("S1", target, 10, 11)
        first_response = repo._practice_repository.save_within_task_response_candidate(candidate)
        second_response = repo._practice_repository.save_within_task_response_candidate(candidate)
        assert [first_response["response_id"], second_response["response_id"]] == [
            "WTR000001", "WTR000002",
        ]
        first_snapshot = repo._practice_repository.save_practice_state_snapshot(
            PracticeStateSnapshot(student_id="S1").model_dump(mode="json"))
        second_snapshot = repo._practice_repository.save_practice_state_snapshot(
            PracticeStateSnapshot(student_id="S1").model_dump(mode="json"))
        assert [first_snapshot["practice_state_snapshot_id"],
                second_snapshot["practice_state_snapshot_id"]] == [
            "PSS000001", "PSS000002",
        ]

    def test_mixed_prefixes_allocate_independently(self, repo):
        svc = PracticeService()
        target = svc.create_practice_target(
            "S1", 10, "D001", "lexical_repetition_local", "Label")
        target = repo._practice_repository.save_practice_target(target)
        exercise = repo._practice_repository.save_exercise_instance(
            svc.generate_exercise(target, "Source text here."))
        trace = repo._practice_repository.save_feedback_engagement_trace(
            FeedbackEngagementTrace(
                student_id="S1", target_code="lexical_repetition_local"
            ).model_dump(mode="json"))
        assert target["practice_target_id"] == "PT000001"
        assert exercise["exercise_id"] == "EX000001"
        assert trace["trace_id"] == "FET000001"

    def test_empty_table_starts_at_one(self, repo):
        target = PracticeService().create_practice_target(
            "S1", 10, "D001", "lexical_repetition_local", "Label")
        assert repo._practice_repository.save_practice_target(
            target)["practice_target_id"] == "PT000001"

    def test_existing_maximum_is_respected(self, repo):
        _insert_target_row(repo, "PT000042", "SX", 1, None)
        target = PracticeService().create_practice_target(
            "S1", 10, "D001", "lexical_repetition_local", "Label")
        assert repo._practice_repository.save_practice_target(
            target)["practice_target_id"] == "PT000043"

    def test_repeated_creation_is_sequential(self, repo):
        svc = PracticeService()
        ids = []
        for i in range(5):
            target = svc.create_practice_target(
                f"S{i}", 10 + i, "D001", "lexical_repetition_local", f"Label{i}")
            ids.append(repo._practice_repository.save_practice_target(
                target)["practice_target_id"])
        assert ids == [f"PT{i:06d}" for i in range(1, 6)]

    def test_concurrent_creation_produces_unique_ids(self, repo):
        svc = PracticeService()
        targets = [
            svc.create_practice_target(
                f"S{i}", 10 + i, "D001", "lexical_repetition_local", f"Label{i}")
            for i in range(8)
        ]

        def _save(target):
            return repo._practice_repository.save_practice_target(target)

        with ThreadPoolExecutor(max_workers=4) as executor:
            saved = list(executor.map(_save, targets))
        ids = [t["practice_target_id"] for t in saved]
        assert len(ids) == len(set(ids)) == 8


class TestMigration13:
    def _index_names(self, repo) -> set[str]:
        with repo.connect() as conn:
            return {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'")
            }

    def test_fresh_database_has_priority_key_index(self, repo):
        assert "ux_practice_targets_active_priority_key" in self._index_names(repo)

    def test_database_constraint_rejects_duplicate_active_key(self, repo):
        essay_id, record, index = _seed_submission(repo)
        _creation_service(repo).create_or_reuse_priority_target(
            _contract(repo, essay_id, record, index))
        reference = f"PRIO-{record['feedback_id']}-{index}"
        with repo.connect() as conn:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO practice_targets VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        "PT000099", "WU3-S", essay_id, "D001",
                        "lexical_repetition_local", "Label", "active",
                        "2026-01-01T00:00:00+00:00",
                        json.dumps({"source_priority_id": reference}),
                    ),
                )

    def test_database_constraint_allows_inactive_null_and_other_student(self, repo):
        essay_id, record, index = _seed_submission(repo)
        reference = f"PRIO-{record['feedback_id']}-{index}"
        _insert_target_row(repo, "PT000001", "WU3-S", essay_id, reference, status="active")
        _insert_target_row(repo, "PT000002", "WU3-S", essay_id, reference, status="inactive")
        _insert_target_row(repo, "PT000003", "WU3-S", essay_id, None, status="active")
        _insert_target_row(repo, "PT000004", "OTHER", essay_id, reference, status="active")
        with repo.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM practice_targets").fetchone()[0]
        assert count == 4

    def test_migration_preserves_existing_rows_and_rolls_back_non_destructively(self, tmp_path):
        path = tmp_path / "v12.db"
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        for version in range(1, 13):
            MIGRATIONS[version][1](connection)
            connection.execute(f"PRAGMA user_version={version}")
        connection.execute(
            "INSERT INTO practice_targets VALUES (?,?,?,?,?,?,?,?,?)",
            (
                "PT000001", "LEGACY", 1, "D001", "lexical_repetition_local",
                "Label", "active", "2026-01-01T00:00:00+00:00",
                json.dumps({"source_priority_id": "PRIO-18"}),
            ),
        )
        connection.commit()
        assert upgrade(connection) == 14
        row = connection.execute(
            "SELECT target_json FROM practice_targets WHERE practice_target_id='PT000001'"
        ).fetchone()
        assert json.loads(row[0])["source_priority_id"] == "PRIO-18"
        assert rollback(connection, 13) == 13
        assert rollback(connection, 12) == 12
        names = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='index'")
        }
        assert "ux_practice_targets_active_priority_key" not in names
        assert connection.execute(
            "SELECT COUNT(*) FROM practice_targets").fetchone()[0] == 1
        assert upgrade(connection) == 14
        connection.close()


class TestIdempotency:
    def test_first_creation_then_repeated_request_reuses_same_target(self, repo):
        essay_id, record, index = _seed_submission(repo)
        service = _creation_service(repo)
        contract = _contract(repo, essay_id, record, index)
        first = service.create_or_reuse_priority_target(contract)
        second = service.create_or_reuse_priority_target(contract)
        assert first["practice_target_id"] == second["practice_target_id"]
        assert first["source_priority_id"] == f"PRIO-{record['feedback_id']}-{index}"
        assert first["status"] == "active"
        assert _target_count(repo) == 1

    def test_repeated_api_requests_return_the_same_target(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            essay_id, record, index = self._seed_api(client)
            payload = {
                "student_id": "WU3-S", "source_submission_id": essay_id,
                "source_priority_id": f"PRIO-{record['feedback_id']}-{index}",
            }
            first = client.post("/api/v1/practice-targets", json=payload)
            second = client.post("/api/v1/practice-targets", json=payload)
            third = client.post("/api/v1/practice-targets", json=payload)
            assert first.status_code == second.status_code == third.status_code == 200
            target_ids = {
                first.json()["practice_target_id"],
                second.json()["practice_target_id"],
                third.json()["practice_target_id"],
            }
            assert len(target_ids) == 1
            with client.app.state.repository.connect() as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM practice_targets").fetchone()[0]
            assert count == 1

    def test_concurrent_creation_of_the_same_key_yields_one_target(self, repo):
        essay_id, record, index = _seed_submission(repo)
        service = _creation_service(repo)
        contract = _contract(repo, essay_id, record, index)

        def _call(_):
            return service.create_or_reuse_priority_target(contract)

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(_call, range(6)))
        target_ids = {result["practice_target_id"] for result in results}
        assert len(target_ids) == 1
        assert _target_count(repo) == 1

    def test_same_category_different_student_creates_separate_targets(self, repo):
        essay_a, record_a, index_a = _seed_submission(repo, "WU3-S")
        essay_b, record_b, index_b = _seed_submission(repo, "WU3-T")
        service = _creation_service(repo)
        target_a = service.create_or_reuse_priority_target(
            _contract(repo, essay_a, record_a, index_a, "WU3-S"))
        target_b = service.create_or_reuse_priority_target(
            _contract(repo, essay_b, record_b, index_b, "WU3-T"))
        assert target_a["practice_target_id"] != target_b["practice_target_id"]
        assert _target_count(repo) == 2

    def test_same_student_different_submission_creates_separate_targets(self, repo):
        essay_a, record_a, index_a = _seed_submission(repo)
        essay_b, record_b, index_b = _seed_submission(repo)
        service = _creation_service(repo)
        target_a = service.create_or_reuse_priority_target(
            _contract(repo, essay_a, record_a, index_a))
        target_b = service.create_or_reuse_priority_target(
            _contract(repo, essay_b, record_b, index_b))
        assert target_a["practice_target_id"] != target_b["practice_target_id"]
        assert _target_count(repo) == 2

    def test_reuse_does_not_change_the_existing_record(self, repo):
        essay_id, record, index = _seed_submission(repo)
        service = _creation_service(repo)
        contract = _contract(repo, essay_id, record, index)
        first = service.create_or_reuse_priority_target(contract)
        with repo.connect() as conn:
            row = conn.execute(
                "SELECT target_json FROM practice_targets WHERE practice_target_id=?",
                (first["practice_target_id"],),
            ).fetchone()
        before = row[0]
        service.create_or_reuse_priority_target(contract)
        with repo.connect() as conn:
            row = conn.execute(
                "SELECT target_json FROM practice_targets WHERE practice_target_id=?",
                (first["practice_target_id"],),
            ).fetchone()
        assert row[0] == before

    def _seed_api(self, client) -> tuple[int, dict, int]:
        response = client.post("/api/v1/submissions", json={
            "student_id": "WU3-S", "writing_prompt": "What actions matter for sustainability?",
            "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
            "tool_use": "none", "essay_text": REPETITION_ESSAY,
        })
        assert response.status_code == 201, response.text
        essay_id = response.json()["submission_id"]
        record = client.app.state.repository._submission_repository.get_feedback_record(essay_id)
        priorities = json.loads(record["feedback_json"])["priority_feedback"]
        index = next(
            i for i, item in enumerate(priorities)
            if item.get("category") == "lexical_repetition"
        )
        return essay_id, record, index


class TestOneActiveTarget:
    def test_existing_active_target_is_reused(self, repo):
        essay_id, record, index = _seed_submission(repo)
        service = _creation_service(repo)
        contract = _contract(repo, essay_id, record, index)
        first = service.create_or_reuse_priority_target(contract)
        second = service.create_or_reuse_priority_target(contract)
        assert second["practice_target_id"] == first["practice_target_id"]
        assert second["status"] == "active"
        assert _target_count(repo) == 1

    def test_existing_non_active_target_is_reused_without_new_creation(self, repo):
        essay_id, record, index = _seed_submission(repo)
        reference = f"PRIO-{record['feedback_id']}-{index}"
        _insert_target_row(repo, "PT000001", "WU3-S", essay_id, reference, status="inactive")
        service = _creation_service(repo)
        contract = _contract(repo, essay_id, record, index)
        result = service.create_or_reuse_priority_target(contract)
        assert result["practice_target_id"] == "PT000001"
        assert result["status"] == "inactive"
        assert _target_count(repo) == 1

    def test_stale_target_is_reused_without_new_creation(self, repo):
        essay_id, record, index = _seed_submission(repo)
        reference = f"PRIO-{record['feedback_id']}-{index}"
        _insert_target_row(
            repo, "PT000001", "WU3-S", essay_id, reference, status="practice_not_available")
        service = _creation_service(repo)
        result = service.create_or_reuse_priority_target(
            _contract(repo, essay_id, record, index))
        assert result["practice_target_id"] == "PT000001"
        assert _target_count(repo) == 1


class TestOwnershipValidation:
    def test_legacy_cross_student_rejected(self, repo):
        essay_id, _, _ = _seed_submission(repo)
        service = _creation_service(repo)
        with pytest.raises(PriorityMappingError) as exc:
            service.create_legacy_target(
                student_id="INTRUDER", source_submission_id=essay_id,
                source_diagnosis_id="D001", target_code="lexical_repetition_local",
                target_label="Label",
            )
        assert exc.value.kind == "cross_student"
        assert _target_count(repo) == 0

    def test_legacy_missing_submission_rejected(self, repo):
        service = _creation_service(repo)
        with pytest.raises(PriorityMappingError) as exc:
            service.create_legacy_target(
                student_id="WU3-S", source_submission_id=999999,
                source_diagnosis_id="D001", target_code="lexical_repetition_local",
                target_label="Label",
            )
        assert exc.value.kind == "source_not_found"
        assert _target_count(repo) == 0

    def test_legacy_unrelated_diagnosis_rejected(self, repo):
        essay_id, _, _ = _seed_submission(repo)
        service = _creation_service(repo)
        with pytest.raises(PriorityMappingError) as exc:
            service.create_legacy_target(
                student_id="WU3-S", source_submission_id=essay_id,
                source_diagnosis_id="D099", target_code="lexical_repetition_local",
                target_label="Label",
            )
        assert exc.value.kind == "unresolved_priority"
        assert _target_count(repo) == 0

    def test_legacy_evidence_ids_rejected(self, repo):
        essay_id, _, _ = _seed_submission(repo)
        service = _creation_service(repo)
        with pytest.raises(PriorityMappingError) as exc:
            service.create_legacy_target(
                student_id="WU3-S", source_submission_id=essay_id,
                source_diagnosis_id="D001", target_code="lexical_repetition_local",
                target_label="Label", evidence_ids=["client-evidence"],
            )
        assert exc.value.kind == "invalid_evidence"
        assert _target_count(repo) == 0

    def test_api_legacy_cross_student_returns_403(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            response = client.post("/api/v1/submissions", json={
                "student_id": "WU3-S", "writing_prompt": "What actions matter for sustainability?",
                "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
                "tool_use": "none", "essay_text": REPETITION_ESSAY,
            })
            essay_id = response.json()["submission_id"]
            diagnosis = response.json()["diagnosis"]
            priority = next(
                item for item in diagnosis.get("improvement_priorities", [])
                if item.get("selection_status") == "selected_priority"
            )
            result = client.post("/api/v1/practice-targets", json={
                "student_id": "INTRUDER", "source_submission_id": essay_id,
                "source_diagnosis_id": priority["diagnosis_id"],
                "target_code": "lexical_repetition_local",
                "target_label": priority["interpretation"],
                "gate_status": "selected",
            })
            assert result.status_code == 403
            with client.app.state.repository.connect() as conn:
                count = conn.execute("SELECT COUNT(*) FROM practice_targets").fetchone()[0]
            assert count == 0

    def test_api_legacy_missing_submission_returns_404(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            result = client.post("/api/v1/practice-targets", json={
                "student_id": "WU3-S", "source_submission_id": 999999,
                "source_diagnosis_id": "D001", "target_code": "lexical_repetition_local",
                "target_label": "Label", "gate_status": "selected",
            })
            assert result.status_code == 404

    def test_api_cross_submission_reuse_is_rejected(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            first_essay, record, index = self._seed_api(client)
            reference = f"PRIO-{record['feedback_id']}-{index}"
            created = client.post("/api/v1/practice-targets", json={
                "student_id": "WU3-S", "source_submission_id": first_essay,
                "source_priority_id": reference,
            })
            assert created.status_code == 200
            second_essay, _, _ = self._seed_api(client)
            reused = client.post("/api/v1/practice-targets", json={
                "student_id": "WU3-S", "source_submission_id": second_essay,
                "source_priority_id": reference,
            })
            assert reused.status_code == 422
            with client.app.state.repository.connect() as conn:
                count = conn.execute("SELECT COUNT(*) FROM practice_targets").fetchone()[0]
            assert count == 1

    def _seed_api(self, client) -> tuple[int, dict, int]:
        response = client.post("/api/v1/submissions", json={
            "student_id": "WU3-S", "writing_prompt": "What actions matter for sustainability?",
            "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
            "tool_use": "none", "essay_text": REPETITION_ESSAY,
        })
        assert response.status_code == 201, response.text
        essay_id = response.json()["submission_id"]
        record = client.app.state.repository._submission_repository.get_feedback_record(essay_id)
        priorities = json.loads(record["feedback_json"])["priority_feedback"]
        index = next(
            i for i, item in enumerate(priorities)
            if item.get("category") == "lexical_repetition"
        )
        return essay_id, record, index


class TestLegacyCompatibility:
    def test_legacy_creation_and_retrieval_still_work(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            response = client.post("/api/v1/submissions", json={
                "student_id": "WU3-L", "writing_prompt": "What actions matter for sustainability?",
                "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
                "tool_use": "none", "essay_text": REPETITION_ESSAY,
            })
            essay_id = response.json()["submission_id"]
            diagnosis = response.json()["diagnosis"]
            priority = next(
                item for item in diagnosis.get("improvement_priorities", [])
                if item.get("selection_status") == "selected_priority"
            )
            result = client.post("/api/v1/practice-targets", json={
                "student_id": "WU3-L", "source_submission_id": essay_id,
                "source_diagnosis_id": priority["diagnosis_id"],
                "target_code": "lexical_repetition_local",
                "target_label": priority["interpretation"],
                "gate_status": "selected",
            })
            assert result.status_code == 200, result.text
            target = result.json()
            assert target["source_priority_id"] is None
            listed = client.get("/api/v1/students/WU3-L/practice-targets").json()
            assert listed[0]["practice_target_id"] == target["practice_target_id"]

    def test_practice_flow_attempts_evaluations_and_journey_intact(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            response = client.post("/api/v1/submissions", json={
                "student_id": "WU3-L", "writing_prompt": "What actions matter for sustainability?",
                "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
                "tool_use": "none", "essay_text": REPETITION_ESSAY,
            })
            essay_id = response.json()["submission_id"]
            diagnosis = response.json()["diagnosis"]
            priority = next(
                item for item in diagnosis.get("improvement_priorities", [])
                if item.get("selection_status") == "selected_priority"
            )
            target = client.post("/api/v1/practice-targets", json={
                "student_id": "WU3-L", "source_submission_id": essay_id,
                "source_diagnosis_id": priority["diagnosis_id"],
                "target_code": "lexical_repetition_local",
                "target_label": priority["interpretation"],
                "gate_status": "selected",
            }).json()
            exercise = client.post(
                f"/api/v1/practice-targets/{target['practice_target_id']}/exercises",
                json={"source_text": REPETITION_ESSAY},
            ).json()
            attempt = client.post(
                f"/api/v1/exercises/{exercise['exercise_id']}/attempts",
                json={"student_id": "WU3-L",
                      "response_text": "A valid response reducing repetition."},
            ).json()
            assert attempt["status"] == "submitted"
            assert attempt["evaluation"] is not None
            journey = client.get("/api/v1/students/WU3-L/journey")
            assert journey.status_code == 200
            assert "practice_available" in {
                event["event_type"] for event in journey.json()["events"]
            }


class TestScopeGuards:
    def test_no_ui_auto_creation(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            client.post("/api/v1/submissions", json={
                "student_id": "WU3-G", "writing_prompt": "What actions matter for sustainability?",
                "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
                "tool_use": "none", "essay_text": REPETITION_ESSAY,
            })
            targets = client.get("/api/v1/students/WU3-G/practice-targets").json()
            assert targets == []

    def test_creation_and_reuse_do_not_mark_completed(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            response = client.post("/api/v1/submissions", json={
                "student_id": "WU3-G", "writing_prompt": "What actions matter for sustainability?",
                "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
                "tool_use": "none", "essay_text": REPETITION_ESSAY,
            })
            essay_id = response.json()["submission_id"]
            record = client.app.state.repository._submission_repository.get_feedback_record(essay_id)
            priorities = json.loads(record["feedback_json"])["priority_feedback"]
            index = next(
                i for i, item in enumerate(priorities)
                if item.get("category") == "lexical_repetition"
            )
            payload = {
                "student_id": "WU3-G", "source_submission_id": essay_id,
                "source_priority_id": f"PRIO-{record['feedback_id']}-{index}",
            }
            first = client.post("/api/v1/practice-targets", json=payload)
            second = client.post("/api/v1/practice-targets", json=payload)
            assert first.json()["status"] == "active"
            assert second.json()["status"] == "active"

    def test_evaluation_behavior_unchanged(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            response = client.post("/api/v1/submissions", json={
                "student_id": "WU3-G", "writing_prompt": "What actions matter for sustainability?",
                "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
                "tool_use": "none", "essay_text": REPETITION_ESSAY,
            })
            essay_id = response.json()["submission_id"]
            diagnosis = response.json()["diagnosis"]
            priority = next(
                item for item in diagnosis.get("improvement_priorities", [])
                if item.get("selection_status") == "selected_priority"
            )
            target = client.post("/api/v1/practice-targets", json={
                "student_id": "WU3-G", "source_submission_id": essay_id,
                "source_diagnosis_id": priority["diagnosis_id"],
                "target_code": "lexical_repetition_local",
                "target_label": priority["interpretation"],
                "gate_status": "selected",
            }).json()
            exercise = client.post(
                f"/api/v1/practice-targets/{target['practice_target_id']}/exercises",
                json={"source_text": REPETITION_ESSAY},
            ).json()
            attempt = client.post(
                f"/api/v1/exercises/{exercise['exercise_id']}/attempts",
                json={"student_id": "WU3-G",
                      "response_text": "A valid response reducing repetition."},
            ).json()
            assert attempt["evaluation"]["evaluation_id"].startswith("PE")
            text = " ".join(attempt["evaluation"].get("limitations", [])).lower()
            assert "mastered" not in text
            assert "proficient" not in text
