"""v0.9.7-B WU2 focused tests: priority-to-practice mapping and provenance.

Covers the stable priority reference, the production category mapping, the
validated target creation contract, ownership/source validation, API
forwarding and persistence, legacy compatibility, and WU2 scope guards.
All persistence runs on isolated databases with the local provider only.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("LLM_PROVIDER", "local")

from fastapi.testclient import TestClient  # noqa: E402

from app.api.main import create_app  # noqa: E402
from app.config import Settings  # noqa: E402
from app.practice.mapping import (  # noqa: E402
    CATEGORY_LABELS,
    TARGET_CODE_MAP,
    PriorityMappingError,
    PriorityPracticeMappingService,
    PriorityTargetContract,
    build_stable_priority_reference,
    build_target_contract,
    map_category_to_target_code,
    normalize_category,
    parse_stable_priority_reference,
    target_label_for_category,
)
from app.practice.schemas import PracticeTarget  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]

REPETITION_ESSAY = (
    "People should protect the environment. People should recycle more. "
    "People should save water. People should plant trees. People should reduce waste. "
    "People should use public transport. People should teach children about nature. "
    "People should value clean air."
)


def _settings(tmp_path) -> Settings:
    return Settings(
        database_path=tmp_path / "wu2.db", llm_provider="local", deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com", deepseek_model="deepseek-chat",
    )


def _priority_item(category: str = "lexical_repetition", diagnosis_id: str = "D002") -> dict:
    return {
        "diagnosis_id": diagnosis_id,
        "category": category,
        "evidence_quote": "People should protect the environment.",
        "explanation": "The pattern may indicate that the targeted feature is worth reviewing.",
        "revision_guidance": "Revise one sentence at a time and preserve the intended meaning.",
    }


def _diagnosis(category: str = "lexical_repetition", diagnosis_id: str = "D002") -> dict:
    return {
        "strengths": [
            {"diagnosis_id": "D001", "category": "task_engagement", "kind": "strength"},
        ],
        "improvement_priorities": [
            {
                "diagnosis_id": diagnosis_id,
                "category": category,
                "selection_status": "selected_priority",
                "kind": "improvement",
            },
        ],
    }


def _bundle(**overrides) -> dict:
    bundle = {
        "essay_id": 10,
        "student_id": "S001",
        "essay_text": REPETITION_ESSAY,
        "feedback_id": 7,
        "feedback": {"priority_feedback": [_priority_item()]},
        "diagnosis": _diagnosis(),
        "diagnosis_version": "prototype-diagnosis-v0.1.1",
        "prompt_version": "feedback-prompt-v0.7.1",
        "schema_version": "feedback-schema-v0.7.1",
    }
    bundle.update(overrides)
    return bundle


class _FakeSubmissionReader:
    def __init__(self, bundle):
        self.bundle = bundle

    def get_submission_bundle(self, essay_id: int):
        return self.bundle


class TestStablePriorityReference:
    def test_same_record_and_index_produce_same_reference(self):
        first = build_stable_priority_reference(7, 0)
        second = build_stable_priority_reference(7, 0)
        assert first == second == "PRIO-7-0"

    def test_different_indexes_produce_different_references(self):
        assert build_stable_priority_reference(7, 0) != build_stable_priority_reference(7, 1)

    def test_different_feedback_records_produce_different_references(self):
        assert build_stable_priority_reference(7, 0) != build_stable_priority_reference(8, 0)

    def test_index_convention_is_zero_based(self):
        assert parse_stable_priority_reference("PRIO-7-0") == (7, 0)
        assert parse_stable_priority_reference("PRIO-7-1") == (7, 1)
        assert build_stable_priority_reference(7, 0) == "PRIO-7-0"

    def test_negative_index_and_nonpositive_feedback_id_rejected(self):
        for feedback_id, index in ((0, 0), (-1, 0), (7, -1)):
            with pytest.raises(PriorityMappingError) as exc:
                build_stable_priority_reference(feedback_id, index)
            assert exc.value.kind == "invalid_reference"

    @pytest.mark.parametrize("reference", [
        "", "PRIO", "PRIO-", "PRIO-18", "PRIO-x-0", "PRIO-7-x",
        "PRIO-7-0-1", "7-0", "PRIO-0-0", "PRIO-7-", "PRIO--1-0",
        None, 42, ["PRIO-7-0"],
    ])
    def test_malformed_references_rejected(self, reference):
        with pytest.raises(PriorityMappingError) as exc:
            parse_stable_priority_reference(reference)
        assert exc.value.kind == "invalid_reference"

    def test_legacy_demo_reference_rejected(self):
        with pytest.raises(PriorityMappingError) as exc:
            parse_stable_priority_reference("PRIO-18")
        assert exc.value.kind == "invalid_reference"


class TestCategoryMapping:
    def test_every_supported_category_maps_deterministically(self):
        assert TARGET_CODE_MAP == {
            "lexical_repetition": "lexical_repetition_local",
            "connective_use": "connective_overuse",
            "sentence_length_pattern": "long_sentence",
        }
        for category, target_code in TARGET_CODE_MAP.items():
            assert map_category_to_target_code(category) == target_code
            assert target_label_for_category(category) == CATEGORY_LABELS[category]
            assert CATEGORY_LABELS[category]

    def test_normalization_is_explicit_and_conservative(self):
        assert normalize_category("  Lexical_Repetition  ") == "lexical_repetition"
        assert map_category_to_target_code("  LEXICAL_REPETITION  ") == "lexical_repetition_local"
        assert map_category_to_target_code("Connective_Use") == "connective_overuse"
        assert normalize_category(" Sentence Length Pattern ") == "sentence length pattern"

    @pytest.mark.parametrize("category", [
        "essay_length", "task_engagement", "targeted_review", "made_up_category",
        "lexical_repetition_typo", "sentence-length-pattern",
    ])
    def test_unknown_category_rejected(self, category):
        with pytest.raises(PriorityMappingError) as exc:
            map_category_to_target_code(category)
        assert exc.value.kind == "unsupported_category"

    @pytest.mark.parametrize("category", ["", "   "])
    def test_blank_category_rejected(self, category):
        with pytest.raises(PriorityMappingError) as exc:
            map_category_to_target_code(category)
        assert exc.value.kind == "unsupported_category"

    @pytest.mark.parametrize("category", [None, 123, ["lexical_repetition"]])
    def test_malformed_category_rejected(self, category):
        with pytest.raises(PriorityMappingError) as exc:
            map_category_to_target_code(category)
        assert exc.value.kind == "unsupported_category"

    def test_demo_imports_production_mapping(self):
        source = (ROOT / "scripts" / "demo_journey.py").read_text(encoding="utf-8")
        assert "from app.practice.mapping import TARGET_CODE_MAP" in source
        assert "TARGET_CODE_MAP = {" not in source


class TestMappingContract:
    def test_valid_priority_produces_expected_contract(self):
        contract = build_target_contract(
            _bundle(), student_id="S001", feedback_id=7, priority_index=0)
        assert isinstance(contract, PriorityTargetContract)
        assert contract.student_id == "S001"
        assert contract.source_submission_id == 10
        assert contract.source_diagnosis_id == "D002"
        assert contract.source_priority_id == "PRIO-7-0"
        assert contract.target_code == "lexical_repetition_local"
        assert contract.target_label == "Reduce lexical repetition"
        assert contract.evidence_ids == ["7"]
        assert contract.diagnostic_gate_status == "selected"
        assert contract.diagnostic_version == "prototype-diagnosis-v0.1.1"
        assert contract.configuration_version == "config-v0.9.0"

    def test_authoritative_values_loaded_from_persistence(self):
        item = _priority_item()
        contract = build_target_contract(
            _bundle(), student_id="S001", feedback_id=7, priority_index=0)
        context = contract.priority_context
        assert context.feedback_id == 7
        assert context.priority_index == 0
        assert context.category == "lexical_repetition"
        assert context.evidence_quote == item["evidence_quote"]
        assert context.explanation == item["explanation"]
        assert context.revision_guidance == item["revision_guidance"]
        assert context.prompt_version == "feedback-prompt-v0.7.1"
        assert context.schema_version == "feedback-schema-v0.7.1"
        assert context.diagnosis_version == "prototype-diagnosis-v0.1.1"
        assert context.label_key == "student_feedback_category_lexical_repetition"

    def test_supported_evidence_provenance_is_preserved(self):
        contract = build_target_contract(
            _bundle(), student_id="S001", feedback_id=7, priority_index=0)
        assert contract.evidence_ids == [str(7)]
        assert contract.priority_context.evidence_quote

    def test_each_supported_category_produces_supported_target_code(self):
        for category in TARGET_CODE_MAP:
            bundle = _bundle(feedback={"priority_feedback": [_priority_item(category)]},
                             diagnosis=_diagnosis(category))
            contract = build_target_contract(
                bundle, student_id="S001", feedback_id=7, priority_index=0)
            assert contract.target_code == TARGET_CODE_MAP[category]

    def test_contract_fits_existing_practice_target_schema(self):
        contract = build_target_contract(
            _bundle(), student_id="S001", feedback_id=7, priority_index=0)
        payload = contract.model_dump(mode="json")
        payload.pop("priority_context")
        target = PracticeTarget(**payload)
        assert target.source_priority_id == "PRIO-7-0"
        assert target.evidence_ids == ["7"]

    def test_service_resolves_through_persisted_bundle(self):
        service = PriorityPracticeMappingService(_FakeSubmissionReader(_bundle()))
        contract = service.resolve_target_contract(
            student_id="S001", source_submission_id=10, source_priority_id="PRIO-7-0")
        assert contract.target_code == "lexical_repetition_local"
        assert contract.priority_context.evidence_quote

    def test_service_rejects_fabricated_reference(self):
        service = PriorityPracticeMappingService(_FakeSubmissionReader(_bundle()))
        with pytest.raises(PriorityMappingError) as exc:
            service.resolve_target_contract(
                student_id="S001", source_submission_id=10, source_priority_id="PRIO-99-0")
        assert exc.value.kind == "unresolved_priority"

    def test_service_missing_bundle_fails_safely(self):
        service = PriorityPracticeMappingService(_FakeSubmissionReader(None))
        with pytest.raises(PriorityMappingError) as exc:
            service.resolve_target_contract(
                student_id="S001", source_submission_id=999, source_priority_id="PRIO-7-0")
        assert exc.value.kind == "source_not_found"


class TestOwnershipAndSourceValidation:
    def test_cross_student_rejected(self):
        with pytest.raises(PriorityMappingError) as exc:
            build_target_contract(
                _bundle(student_id="S002"), student_id="S001", feedback_id=7, priority_index=0)
        assert exc.value.kind == "cross_student"

    def test_mismatched_feedback_record_rejected(self):
        with pytest.raises(PriorityMappingError) as exc:
            build_target_contract(
                _bundle(), student_id="S001", feedback_id=8, priority_index=0)
        assert exc.value.kind == "unresolved_priority"

    def test_stale_priority_index_rejected(self):
        with pytest.raises(PriorityMappingError) as exc:
            build_target_contract(
                _bundle(), student_id="S001", feedback_id=7, priority_index=1)
        assert exc.value.kind == "unresolved_priority"

    def test_missing_feedback_record_rejected(self):
        with pytest.raises(PriorityMappingError) as exc:
            build_target_contract(
                _bundle(feedback_id=None), student_id="S001", feedback_id=7, priority_index=0)
        assert exc.value.kind == "source_not_found"

    def test_missing_feedback_structure_rejected(self):
        with pytest.raises(PriorityMappingError) as exc:
            build_target_contract(
                _bundle(feedback=None), student_id="S001", feedback_id=7, priority_index=0)
        assert exc.value.kind == "malformed_priority"

    def test_missing_diagnosis_rejected(self):
        with pytest.raises(PriorityMappingError) as exc:
            build_target_contract(
                _bundle(diagnosis=None), student_id="S001", feedback_id=7, priority_index=0)
        assert exc.value.kind == "source_not_found"

    def test_malformed_priority_list_rejected(self):
        with pytest.raises(PriorityMappingError) as exc:
            build_target_contract(
                _bundle(feedback={"priority_feedback": "not-a-list"}),
                student_id="S001", feedback_id=7, priority_index=0)
        assert exc.value.kind == "malformed_priority"

    @pytest.mark.parametrize("field", [
        "diagnosis_id", "category", "evidence_quote", "explanation", "revision_guidance",
    ])
    def test_malformed_priority_item_rejected(self, field):
        item = _priority_item()
        item.pop(field)
        with pytest.raises(PriorityMappingError) as exc:
            build_target_contract(
                _bundle(feedback={"priority_feedback": [item]}),
                student_id="S001", feedback_id=7, priority_index=0)
        assert exc.value.kind == "malformed_priority"

    def test_unrelated_diagnosis_rejected(self):
        item = _priority_item(diagnosis_id="D099")
        with pytest.raises(PriorityMappingError) as exc:
            build_target_contract(
                _bundle(feedback={"priority_feedback": [item]}),
                student_id="S001", feedback_id=7, priority_index=0)
        assert exc.value.kind == "unresolved_priority"

    def test_category_conflicts_with_diagnosis_rejected(self):
        bundle = _bundle(feedback={"priority_feedback": [_priority_item("connective_use")]})
        with pytest.raises(PriorityMappingError) as exc:
            build_target_contract(bundle, student_id="S001", feedback_id=7, priority_index=0)
        assert exc.value.kind == "unresolved_priority"


class TestApiForwardingAndPersistence:
    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def _seed(self, client) -> tuple[int, dict]:
        response = client.post("/api/v1/submissions", json={
            "student_id": "WU2-S", "writing_prompt": "What actions matter for sustainability?",
            "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
            "tool_use": "none", "essay_text": REPETITION_ESSAY,
        })
        assert response.status_code == 201, response.text
        essay_id = response.json()["submission_id"]
        record = client.app.state.repository._submission_repository.get_feedback_record(essay_id)
        assert record is not None
        return essay_id, record

    def _priority_index(self, record: dict, category: str) -> int:
        priorities = json.loads(record["feedback_json"])["priority_feedback"]
        matches = [i for i, item in enumerate(priorities) if item.get("category") == category]
        assert matches, f"category {category} not present in persisted priorities"
        return matches[0]

    def _rewrite_priority(self, client, essay_id: int, category: str,
                          diagnosis_id: str = "D002") -> None:
        repository = client.app.state.repository
        record = repository._submission_repository.get_feedback_record(essay_id)
        feedback = json.loads(record["feedback_json"])
        feedback["priority_feedback"] = [_priority_item(category, diagnosis_id)]
        with repository.connect() as conn:
            conn.execute(
                "UPDATE feedback_records SET feedback_json=? WHERE essay_id=?",
                (json.dumps(feedback), essay_id),
            )
            conn.execute(
                "UPDATE diagnoses SET diagnosis_json=? WHERE essay_id=?",
                (json.dumps(_diagnosis(category, diagnosis_id)), essay_id),
            )

    def _target_count(self, client) -> int:
        with client.app.state.repository.connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM practice_targets").fetchone()[0]

    def test_provenance_reaches_persistence_and_retrieval(self, client):
        essay_id, record = self._seed(client)
        index = self._priority_index(record, "lexical_repetition")
        reference = f"PRIO-{record['feedback_id']}-{index}"
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU2-S", "source_submission_id": essay_id,
            "source_priority_id": reference,
        })
        assert response.status_code == 200, response.text
        target = response.json()
        assert target["source_priority_id"] == reference
        assert target["evidence_ids"] == [str(record["feedback_id"])]
        assert target["source_submission_id"] == essay_id
        persisted_priorities = json.loads(record["feedback_json"])["priority_feedback"]
        assert target["source_diagnosis_id"] == persisted_priorities[index]["diagnosis_id"]
        assert target["target_code"] == "lexical_repetition_local"
        assert "priority_context" not in target
        with client.app.state.repository.connect() as conn:
            row = conn.execute(
                "SELECT target_json FROM practice_targets WHERE practice_target_id=?",
                (target["practice_target_id"],),
            ).fetchone()
        persisted = json.loads(row[0])
        assert persisted["source_priority_id"] == reference
        assert persisted["evidence_ids"] == [str(record["feedback_id"])]
        listed = client.get("/api/v1/students/WU2-S/practice-targets").json()
        assert listed[0]["source_priority_id"] == reference
        assert listed[0]["evidence_ids"] == [str(record["feedback_id"])]

    @pytest.mark.parametrize("category,target_code", [
        ("lexical_repetition", "lexical_repetition_local"),
        ("connective_use", "connective_overuse"),
        ("sentence_length_pattern", "long_sentence"),
    ])
    def test_every_supported_category_creates_mapped_target(self, client, category, target_code):
        essay_id, record = self._seed(client)
        self._rewrite_priority(client, essay_id, category)
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU2-S", "source_submission_id": essay_id,
            "source_priority_id": f"PRIO-{record['feedback_id']}-0",
        })
        assert response.status_code == 200, response.text
        assert response.json()["target_code"] == target_code

    def test_unmapped_category_fails_safely_with_zero_writes(self, client):
        essay_id, record = self._seed(client)
        self._rewrite_priority(client, essay_id, "essay_length")
        before = self._target_count(client)
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU2-S", "source_submission_id": essay_id,
            "source_priority_id": f"PRIO-{record['feedback_id']}-0",
        })
        assert response.status_code == 422
        assert self._target_count(client) == before

    def test_malformed_reference_returns_422(self, client):
        essay_id, _ = self._seed(client)
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU2-S", "source_submission_id": essay_id,
            "source_priority_id": "PRIO-18",
        })
        assert response.status_code == 422

    def test_fabricated_feedback_id_returns_422(self, client):
        essay_id, record = self._seed(client)
        fabricated = record["feedback_id"] + 1000
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU2-S", "source_submission_id": essay_id,
            "source_priority_id": f"PRIO-{fabricated}-0",
        })
        assert response.status_code == 422

    def test_out_of_range_index_returns_422(self, client):
        essay_id, record = self._seed(client)
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU2-S", "source_submission_id": essay_id,
            "source_priority_id": f"PRIO-{record['feedback_id']}-99",
        })
        assert response.status_code == 422

    def test_cross_student_reference_returns_403(self, client):
        essay_id, record = self._seed(client)
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "OTHER-LEARNER", "source_submission_id": essay_id,
            "source_priority_id": f"PRIO-{record['feedback_id']}-0",
        })
        assert response.status_code == 403

    def test_missing_submission_returns_404(self, client):
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU2-S", "source_submission_id": 999999,
            "source_priority_id": "PRIO-7-0",
        })
        assert response.status_code == 404

    def test_conflicting_target_code_returns_422(self, client):
        essay_id, record = self._seed(client)
        index = self._priority_index(record, "lexical_repetition")
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU2-S", "source_submission_id": essay_id,
            "source_priority_id": f"PRIO-{record['feedback_id']}-{index}",
            "target_code": "connective_overuse",
        })
        assert response.status_code == 422

    def test_conflicting_evidence_ids_return_422(self, client):
        essay_id, record = self._seed(client)
        index = self._priority_index(record, "lexical_repetition")
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU2-S", "source_submission_id": essay_id,
            "source_priority_id": f"PRIO-{record['feedback_id']}-{index}",
            "evidence_ids": ["fabricated-evidence"],
        })
        assert response.status_code == 422

    def test_client_priority_content_cannot_override_persistence(self, client):
        essay_id, record = self._seed(client)
        index = self._priority_index(record, "lexical_repetition")
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU2-S", "source_submission_id": essay_id,
            "source_priority_id": f"PRIO-{record['feedback_id']}-{index}",
            "category": "essay_length",
            "explanation": "client-supplied explanation",
            "evidence_quote": "client-supplied quote",
            "revision_guidance": "client-supplied guidance",
        })
        assert response.status_code == 200, response.text
        target = response.json()
        assert target["target_code"] == "lexical_repetition_local"
        assert target["source_priority_id"] == f"PRIO-{record['feedback_id']}-{index}"

    def test_validation_failure_produces_zero_writes(self, client):
        essay_id, record = self._seed(client)
        before = self._target_count(client)
        failing_payloads = [
            {"student_id": "WU2-S", "source_submission_id": essay_id,
             "source_priority_id": "PRIO-18"},
            {"student_id": "OTHER-LEARNER", "source_submission_id": essay_id,
             "source_priority_id": f"PRIO-{record['feedback_id']}-0"},
            {"student_id": "WU2-S", "source_submission_id": essay_id,
             "source_priority_id": f"PRIO-{record['feedback_id']}-99"},
        ]
        for payload in failing_payloads:
            response = client.post("/api/v1/practice-targets", json=payload)
            assert response.status_code in (403, 422)
        assert self._target_count(client) == before


class TestLegacyCompatibility:
    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def _seed(self, client) -> tuple[int, dict]:
        response = client.post("/api/v1/submissions", json={
            "student_id": "WU2-L", "writing_prompt": "What actions matter for sustainability?",
            "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
            "tool_use": "none", "essay_text": REPETITION_ESSAY,
        })
        assert response.status_code == 201, response.text
        essay_id = response.json()["submission_id"]
        diagnosis = response.json()["diagnosis"]
        priority = next(
            item for item in diagnosis.get("improvement_priorities", [])
            if item.get("selection_status") == "selected_priority"
        )
        return essay_id, priority

    def test_legacy_target_creation_without_provenance_works(self, client):
        essay_id, priority = self._seed(client)
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU2-L", "source_submission_id": essay_id,
            "source_diagnosis_id": priority["diagnosis_id"],
            "target_code": "lexical_repetition_local",
            "target_label": priority["interpretation"],
            "gate_status": "selected",
        })
        assert response.status_code == 200, response.text
        target = response.json()
        assert target["source_priority_id"] is None
        assert target["evidence_ids"] == []

    def test_legacy_evidence_ids_are_forwarded(self, client):
        essay_id, priority = self._seed(client)
        response = client.post("/api/v1/practice-targets", json={
            "student_id": "WU2-L", "source_submission_id": essay_id,
            "source_diagnosis_id": priority["diagnosis_id"],
            "target_code": "lexical_repetition_local",
            "target_label": priority["interpretation"],
            "evidence_ids": ["repeated_content_words"],
            "gate_status": "selected",
        })
        assert response.status_code == 200, response.text
        assert response.json()["evidence_ids"] == ["repeated_content_words"]

    def test_practice_flow_and_journey_remain_intact(self, client):
        essay_id, priority = self._seed(client)
        target = client.post("/api/v1/practice-targets", json={
            "student_id": "WU2-L", "source_submission_id": essay_id,
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
            json={"student_id": "WU2-L",
                  "response_text": "A valid response reducing repetition."},
        ).json()
        assert attempt["status"] == "submitted"
        assert attempt["evaluation"] is not None
        journey = client.get("/api/v1/students/WU2-L/journey")
        assert journey.status_code == 200
        assert "practice_available" in {
            event["event_type"] for event in journey.json()["events"]
        }


class TestScopeGuards:
    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_submission_does_not_auto_create_target(self, client):
        client.post("/api/v1/submissions", json={
            "student_id": "WU2-G", "writing_prompt": "What actions matter for sustainability?",
            "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
            "tool_use": "none", "essay_text": REPETITION_ESSAY,
        })
        targets = client.get("/api/v1/students/WU2-G/practice-targets").json()
        assert targets == []

    def test_target_creation_does_not_mark_completed(self, client):
        response = client.post("/api/v1/submissions", json={
            "student_id": "WU2-G", "writing_prompt": "What actions matter for sustainability?",
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
        target = client.post("/api/v1/practice-targets", json={
            "student_id": "WU2-G", "source_submission_id": essay_id,
            "source_priority_id": f"PRIO-{record['feedback_id']}-{index}",
        }).json()
        assert target["status"] == "active"

    def test_no_duplicate_prevention_in_wu2(self, client):
        response = client.post("/api/v1/submissions", json={
            "student_id": "WU2-G", "writing_prompt": "What actions matter for sustainability?",
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
            "student_id": "WU2-G", "source_submission_id": essay_id,
            "source_priority_id": f"PRIO-{record['feedback_id']}-{index}",
        }
        first = client.post("/api/v1/practice-targets", json=payload)
        second = client.post("/api/v1/practice-targets", json=payload)
        assert first.status_code == 200 and second.status_code == 200
        assert first.json()["practice_target_id"] != second.json()["practice_target_id"]
        with client.app.state.repository.connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM practice_targets").fetchone()[0]
        assert count == 2
