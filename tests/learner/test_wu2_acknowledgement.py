"""WU2 positive longitudinal acknowledgement tests (RETRY-2 Worker C).

Covers: positive acknowledgement with consent and complete provenance;
no-consent; missing evidence; missing provenance/version; invalid status;
normative/causal text; cross-student source; duplicate/conflict; malformed
payloads. Every failure path asserts NO write to the append-only store and
NO acknowledgement return.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.routers.acknowledgement import get_acknowledgement_service, router
from app.learner.acknowledgement import (
    AcknowledgementError,
    AcknowledgementEvidencePort,
    AcknowledgementService,
    AcknowledgementStorePort,
)
from app.learner.acknowledgement_contracts import (
    ACKNOWLEDGEMENT_CONSENT_SCOPE,
    ACKNOWLEDGEMENT_LIMITATION,
    AcknowledgementRecord,
    AcknowledgementRequest,
    AcknowledgementSourceKind,
    LearnerConsent,
)
from app.learner.evidence import (
    EvidenceAdmissionStatus,
    ExposureClass,
    ObservedEvidence,
    ProvenanceChain,
)
from app.learner.practice_provenance import (
    PracticeActivityStatus,
    PracticeProvenanceRecord,
)
from app.models.schemas import HistoryEvidence
from app.shared.vocabularies import EpistemicStatus, EvidenceStatus


NOW = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
LEARNER = "S001"
OTHER = "S002"


def utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


# ---------------------------------------------------------------------------
# Test doubles (in-memory; production ships only the Protocol ports)
# ---------------------------------------------------------------------------


class InMemoryAcknowledgementStore:
    """Append-only store double: no update/overwrite/delete surface."""

    def __init__(self) -> None:
        self._records: list[AcknowledgementRecord] = []

    def append(self, record: AcknowledgementRecord) -> None:
        if self.get(record.acknowledgement_id) is not None:
            raise ValueError("append-only store rejects duplicate id")
        self._records.append(record)

    def get(self, acknowledgement_id: str) -> AcknowledgementRecord | None:
        for record in self._records:
            if record.acknowledgement_id == acknowledgement_id:
                return record
        return None

    def list_for_learner(self, learner_id: str) -> list[AcknowledgementRecord]:
        return [
            record for record in self._records if record.learner_id == learner_id
        ]


class InMemoryEvidencePort:
    """Learner-scoped evidence lookup double."""

    def __init__(self) -> None:
        self._owner: dict[str, str] = {}
        self._records: dict[str, Any] = {}

    def add(self, learner_id: str, source_id: str, record: Any) -> None:
        self._owner[source_id] = learner_id
        self._records[source_id] = record

    def owner_of(self, source_id: str) -> str | None:
        return self._owner.get(source_id)

    def get_record(self, learner_id: str, source_id: str) -> Any | None:
        if self.owner_of(source_id) != learner_id:
            return None
        return self._records.get(source_id)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_provenance(**overrides: Any) -> ProvenanceChain:
    values: dict[str, Any] = {
        "source_package": "learner-submissions-v1",
        "manifest_hash": "M-001",
        "processing_version": "analysis-v0.9.0",
    }
    values.update(overrides)
    return ProvenanceChain(**values)


def make_consent(**overrides: Any) -> LearnerConsent:
    values: dict[str, Any] = {
        "granted": True,
        "revoked": False,
        "scope": ACKNOWLEDGEMENT_CONSENT_SCOPE,
        "consent_version": "learner-consent-v0.1.0",
        "granted_at": utc("2026-08-10T08:00:00+00:00"),
        "learner_id": LEARNER,
    }
    values.update(overrides)
    return LearnerConsent(**values)


def make_evidence(
    evidence_id: str = "E-101",
    *,
    admission: EvidenceAdmissionStatus = EvidenceAdmissionStatus.ADMISSIBLE,
    epistemic: EpistemicStatus = EpistemicStatus.OBSERVED_DESCRIPTIVE,
    exposure: ExposureClass = ExposureClass.RESEARCH_ONLY,
) -> ObservedEvidence:
    return ObservedEvidence(
        evidence_id=evidence_id,
        source_event_id=f"SEV-{evidence_id}",
        evidence_type="surface_metric",
        observed_at=utc("2026-08-01T09:00:00+00:00"),
        admission_status=admission,
        admission_reason=None if admission == EvidenceAdmissionStatus.ADMISSIBLE else "test",
        epistemic_status=epistemic,
        exposure_class=exposure,
        provenance=make_provenance(),
        value={"metric": "connective_count", "count": 4},
    )


def make_practice(
    record_id: str = "PR-101",
    *,
    admission: EvidenceAdmissionStatus = EvidenceAdmissionStatus.ADMISSIBLE,
    evaluation_id: str | None = "EV-1",
    activity_status: PracticeActivityStatus = PracticeActivityStatus.COMPLETED,
) -> PracticeProvenanceRecord:
    return PracticeProvenanceRecord(
        record_id=record_id,
        student_id=LEARNER,
        practice_target_id="PT-1",
        exercise_id="EX-1",
        exercise_version="exercise-v0.9.0",
        attempt_id="A-1",
        evaluation_id=evaluation_id,
        evaluator_version="evaluator-v0.9.0",
        activity_status=activity_status,
        occurred_at=utc("2026-08-02T09:00:00+00:00"),
        policy_version="feedback-policy-v0.1.0",
        admission_status=admission,
        admission_reason=None if admission == EvidenceAdmissionStatus.ADMISSIBLE else "test",
    )


def make_history_signal() -> HistoryEvidence:
    return HistoryEvidence(
        history_evidence_id="H001",
        evidence_type="metric_change",
        description=(
            "Descriptive surface-metric comparison of two eligible submissions."
        ),
        supporting_submission_ids=["E000001", "E000002"],
        comparable_submission_count=2,
        confidence="low",
        limitation=(
            "This evidence does not establish language-ability improvement, "
            "decline, mastery, or regression."
        ),
    )


CLEAN_TEXT = (
    "Connective use appeared in 3 of 5 eligible submissions across the "
    "observed span; this is descriptive observed evidence only."
)


def make_request(**overrides: Any) -> AcknowledgementRequest:
    values: dict[str, Any] = {
        "learner_id": LEARNER,
        "source_kind": AcknowledgementSourceKind.OBSERVED_EVIDENCE,
        "source_evidence_ids": ["E-101"],
        "evidence_status": EvidenceStatus.VERIFIED,
        "provenance": make_provenance(),
        "policy_version": "feedback-policy-v0.1.0",
        "record_version": "acknowledgement-record-v0.1.0",
        "acknowledgement_text": CLEAN_TEXT,
        "consent": make_consent(),
        "observed_span_start": utc("2026-08-01T00:00:00+00:00"),
        "observed_span_end": utc("2026-08-11T00:00:00+00:00"),
    }
    values.update(overrides)
    return AcknowledgementRequest(**values)


def seed_port() -> InMemoryEvidencePort:
    port = InMemoryEvidencePort()
    port.add(LEARNER, "E-101", make_evidence())
    port.add(LEARNER, "PR-101", make_practice())
    port.add(LEARNER, "H-101", make_history_signal())
    return port


def build_service(
    store: InMemoryAcknowledgementStore | None = None,
    port: InMemoryEvidencePort | None = None,
    **kwargs: Any,
) -> AcknowledgementService:
    return AcknowledgementService(
        store or InMemoryAcknowledgementStore(),
        evidence_port=port if port is not None else seed_port(),
        now=lambda: NOW,
        **kwargs,
    )


def assert_no_write(store: InMemoryAcknowledgementStore) -> None:
    assert store.list_for_learner(LEARNER) == []
    assert store.list_for_learner(OTHER) == []


# ---------------------------------------------------------------------------
# Contract typing
# ---------------------------------------------------------------------------


class TestRequestTyping:
    def test_request_requires_nonempty_evidence_ids(self) -> None:
        with pytest.raises(ValidationError):
            make_request(source_evidence_ids=[])

    def test_request_rejects_blank_evidence_ids(self) -> None:
        with pytest.raises(ValidationError):
            make_request(source_evidence_ids=["  ", "E-101"])

    def test_request_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            make_request(unexpected=True)

    def test_request_rejects_blank_acknowledgement_text(self) -> None:
        with pytest.raises(ValidationError):
            make_request(acknowledgement_text="   ")

    def test_request_rejects_missing_record_version(self) -> None:
        with pytest.raises(ValidationError):
            make_request(record_version="")

    def test_request_rejects_non_descriptive_epistemic_status(self) -> None:
        with pytest.raises(ValidationError):
            make_request(epistemic_status=EpistemicStatus.GATED_INFERENCE)

    def test_request_rejects_inverted_span(self) -> None:
        with pytest.raises(ValidationError):
            make_request(
                observed_span_start=utc("2026-08-11T00:00:00+00:00"),
                observed_span_end=utc("2026-08-01T00:00:00+00:00"),
            )

    def test_consent_requires_scope_and_version(self) -> None:
        with pytest.raises(ValidationError):
            make_consent(scope="")
        with pytest.raises(ValidationError):
            make_consent(consent_version="")

    def test_record_outcome_claim_locked_to_none(self) -> None:
        record = AcknowledgementRecord(
            acknowledgement_id="ACK-test",
            learner_id=LEARNER,
            source_kind=AcknowledgementSourceKind.OBSERVED_EVIDENCE,
            source_evidence_ids=["E-101"],
            evidence_status=EvidenceStatus.VERIFIED,
            provenance=make_provenance(),
            record_version="acknowledgement-record-v0.1.0",
            acknowledgement_text=CLEAN_TEXT,
            consent=make_consent(),
        )
        assert record.outcome_claim == "none"
        with pytest.raises(ValidationError):
            AcknowledgementRecord(
                **{
                    **record.model_dump(mode="python"),
                    "outcome_claim": "mastery",
                }
            )


# ---------------------------------------------------------------------------
# Consent fail-closed (no write)
# ---------------------------------------------------------------------------


class TestConsentFailClosed:
    def test_missing_consent_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request(consent=None))
        assert exc_info.value.kind == "consent_missing"
        assert_no_write(store)

    def test_denied_consent_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request(consent=make_consent(granted=False)))
        assert exc_info.value.kind == "consent_denied"
        assert_no_write(store)

    def test_revoked_consent_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request(consent=make_consent(revoked=True)))
        assert exc_info.value.kind == "consent_revoked"
        assert_no_write(store)

    def test_wrong_consent_scope_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(
                make_request(consent=make_consent(scope="research_consent"))
            )
        assert exc_info.value.kind == "consent_scope_mismatch"
        assert_no_write(store)

    def test_cross_student_consent_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(
                make_request(consent=make_consent(learner_id=OTHER))
            )
        assert exc_info.value.kind == "consent_learner_mismatch"
        assert_no_write(store)

    def test_future_consent_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(
                make_request(
                    consent=make_consent(
                        granted_at=utc("2026-08-13T00:00:00+00:00")
                    )
                )
            )
        assert exc_info.value.kind == "consent_invalid"
        assert_no_write(store)

    def test_missing_evidence_port_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = AcknowledgementService(
            store, evidence_port=None, now=lambda: NOW,
        )
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request())
        assert exc_info.value.kind == "evidence_unavailable"
        assert_no_write(store)


# ---------------------------------------------------------------------------
# Evidence / provenance / version / status fail-closed (no write)
# ---------------------------------------------------------------------------


class TestEvidenceSourceFailClosed:
    def test_unknown_evidence_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request(source_evidence_ids=["E-NOPE"]))
        assert exc_info.value.kind == "evidence_not_found"
        assert_no_write(store)

    def test_cross_student_evidence_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(
                make_request(
                    learner_id=OTHER,
                    consent=make_consent(learner_id=OTHER),
                )
            )
        assert exc_info.value.kind == "cross_student"
        assert_no_write(store)

    def test_missing_provenance_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request(provenance=None))
        assert exc_info.value.kind == "missing_provenance"
        assert_no_write(store)

    def test_missing_policy_model_config_versions_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(
                make_request(policy_version=None, model_version=None, config_version=None)
            )
        assert exc_info.value.kind == "missing_version"
        assert_no_write(store)

    def test_invalid_evidence_status_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        for status in (
            EvidenceStatus.INSUFFICIENT,
            EvidenceStatus.SUPPRESSED,
            EvidenceStatus.UNAVAILABLE,
            EvidenceStatus.CANDIDATE,
            EvidenceStatus.LEGACY,
            EvidenceStatus.UNRESOLVED,
            EvidenceStatus.NOT_APPLICABLE,
        ):
            with pytest.raises(AcknowledgementError) as exc_info:
                service.acknowledge(make_request(evidence_status=status))
            assert exc_info.value.kind == "invalid_evidence_status"
            assert_no_write(store)

    def test_invalid_source_kind_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        for kind in (
            AcknowledgementSourceKind.SOURCE_EVENT,
            AcknowledgementSourceKind.DIAGNOSTIC_INFERENCE,
            AcknowledgementSourceKind.FEEDBACK_RECOMMENDATION,
            AcknowledgementSourceKind.OUTCOME_CLAIM,
        ):
            with pytest.raises(AcknowledgementError) as exc_info:
                service.acknowledge(make_request(source_kind=kind))
            assert exc_info.value.kind == "invalid_source_kind"
            assert_no_write(store)

    def test_evidence_invalid_admission_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        port = InMemoryEvidencePort()
        port.add(
            LEARNER,
            "E-101",
            make_evidence(admission=EvidenceAdmissionStatus.INVALID),
        )
        service = build_service(store=store, port=port)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request())
        assert exc_info.value.kind == "invalid_source_record"
        assert_no_write(store)

    def test_evidence_limited_admission_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        port = InMemoryEvidencePort()
        port.add(
            LEARNER,
            "E-101",
            make_evidence(admission=EvidenceAdmissionStatus.LIMITED),
        )
        service = build_service(store=store, port=port)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request())
        assert exc_info.value.kind == "invalid_source_record"
        assert_no_write(store)

    def test_gated_inference_evidence_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        port = InMemoryEvidencePort()
        port.add(
            LEARNER,
            "E-101",
            make_evidence(epistemic=EpistemicStatus.GATED_INFERENCE),
        )
        service = build_service(store=store, port=port)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request())
        assert exc_info.value.kind == "invalid_source_record"
        assert_no_write(store)

    def test_unavailable_exposure_evidence_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        port = InMemoryEvidencePort()
        port.add(
            LEARNER,
            "E-101",
            make_evidence(exposure=ExposureClass.UNAVAILABLE),
        )
        service = build_service(store=store, port=port)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request())
        assert exc_info.value.kind == "invalid_source_record"
        assert_no_write(store)

    def test_practice_result_requires_evaluation(self) -> None:
        store = InMemoryAcknowledgementStore()
        port = InMemoryEvidencePort()
        port.add(LEARNER, "PR-101", make_practice(evaluation_id=None))
        service = build_service(store=store, port=port)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(
                make_request(
                    source_kind=AcknowledgementSourceKind.PRACTICE_RESULT,
                    source_evidence_ids=["PR-101"],
                )
            )
        assert exc_info.value.kind == "invalid_source_record"
        assert_no_write(store)

    def test_practice_invalid_admission_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        port = InMemoryEvidencePort()
        port.add(
            LEARNER,
            "PR-101",
            make_practice(admission=EvidenceAdmissionStatus.INVALID),
        )
        service = build_service(store=store, port=port)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(
                make_request(
                    source_kind=AcknowledgementSourceKind.PRACTICE_ACTIVITY,
                    source_evidence_ids=["PR-101"],
                )
            )
        assert exc_info.value.kind == "invalid_source_record"
        assert_no_write(store)


# ---------------------------------------------------------------------------
# Normative / causal text fail-closed (no write)
# ---------------------------------------------------------------------------


class TestTextSafetyFailClosed:
    def test_normative_mastery_text_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(
                make_request(
                    acknowledgement_text="You have achieved mastery of connectives."
                )
            )
        assert exc_info.value.kind == "normative_language"
        assert_no_write(store)

    def test_proficiency_text_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(
                make_request(
                    acknowledgement_text="This implies advanced proficiency."
                )
            )
        assert exc_info.value.kind == "normative_language"
        assert_no_write(store)

    def test_causal_improved_text_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(
                make_request(
                    acknowledgement_text="Your connective use improved across submissions."
                )
            )
        assert exc_info.value.kind == "causal_language"
        assert_no_write(store)

    def test_causal_transfer_attribution_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(
                make_request(
                    acknowledgement_text="Practice led to transfer into later writing."
                )
            )
        assert exc_info.value.kind == "causal_language"
        assert_no_write(store)


# ---------------------------------------------------------------------------
# Positive path and append-only store behavior
# ---------------------------------------------------------------------------


class TestPositiveAcknowledgement:
    def test_positive_acknowledgement_appends_and_returns(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        result = service.acknowledge(make_request())
        assert result.acknowledged is True
        record = result.record
        assert record.learner_id == LEARNER
        assert record.source_kind == AcknowledgementSourceKind.OBSERVED_EVIDENCE
        assert record.source_evidence_ids == ["E-101"]
        assert record.evidence_status == EvidenceStatus.VERIFIED
        assert record.epistemic_status == EpistemicStatus.OBSERVED_DESCRIPTIVE
        assert record.outcome_claim == "none"
        assert record.recorded_at == NOW
        assert record.consent.granted is True
        assert ACKNOWLEDGEMENT_LIMITATION in record.limitations
        assert record.acknowledgement_id.startswith("ACK-")
        assert store.get(record.acknowledgement_id) is not None
        assert len(store.list_for_learner(LEARNER)) == 1

    def test_positive_practice_activity_acknowledgement(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        result = service.acknowledge(
            make_request(
                source_kind=AcknowledgementSourceKind.PRACTICE_ACTIVITY,
                source_evidence_ids=["PR-101"],
            )
        )
        assert result.record.source_kind == AcknowledgementSourceKind.PRACTICE_ACTIVITY
        assert len(store.list_for_learner(LEARNER)) == 1

    def test_positive_practice_result_acknowledgement(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        result = service.acknowledge(
            make_request(
                source_kind=AcknowledgementSourceKind.PRACTICE_RESULT,
                source_evidence_ids=["PR-101"],
            )
        )
        assert result.record.source_kind == AcknowledgementSourceKind.PRACTICE_RESULT
        assert len(store.list_for_learner(LEARNER)) == 1

    def test_positive_history_signal_acknowledgement(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        result = service.acknowledge(
            make_request(
                source_kind=AcknowledgementSourceKind.HISTORY_SIGNAL,
                source_evidence_ids=["H-101"],
                acknowledgement_text=(
                    "A descriptive metric comparison between two eligible "
                    "submissions was recorded; observed evidence only."
                ),
            )
        )
        assert result.record.source_kind == AcknowledgementSourceKind.HISTORY_SIGNAL
        assert len(store.list_for_learner(LEARNER)) == 1

    def test_acknowledgement_id_is_deterministic(self) -> None:
        first = build_service().acknowledge(make_request()).record.acknowledgement_id
        second = build_service().acknowledge(make_request()).record.acknowledgement_id
        assert first == second

    def test_list_for_learner_is_learner_scoped(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        service.acknowledge(make_request())
        assert len(service.list_for_learner(LEARNER)) == 1
        assert service.list_for_learner(OTHER) == []

    def test_duplicate_acknowledgement_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        service.acknowledge(make_request())
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(make_request())
        assert exc_info.value.kind == "duplicate_acknowledgement"
        assert len(store.list_for_learner(LEARNER)) == 1

    def test_conflicting_acknowledgement_id_fails_closed(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        service.acknowledge(make_request(acknowledgement_id="ACK-fixed"))
        with pytest.raises(AcknowledgementError) as exc_info:
            service.acknowledge(
                make_request(
                    acknowledgement_id="ACK-fixed",
                    acknowledgement_text=(
                        "A different descriptive sentence about the same evidence."
                    ),
                )
            )
        assert exc_info.value.kind == "conflict"
        assert len(store.list_for_learner(LEARNER)) == 1


# ---------------------------------------------------------------------------
# Router (isolated app; service resolved from request.app.state)
# ---------------------------------------------------------------------------


def build_client(
    service: AcknowledgementService | None = None,
) -> tuple[TestClient, InMemoryAcknowledgementStore]:
    store = InMemoryAcknowledgementStore()
    app = FastAPI()
    app.include_router(router)
    app.state.acknowledgement_service = service or build_service(store=store)
    return TestClient(app), store


def payload(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "learner_id": LEARNER,
        "source_kind": "observed_evidence",
        "source_evidence_ids": ["E-101"],
        "evidence_status": "verified",
        "provenance": make_provenance().model_dump(mode="json"),
        "policy_version": "feedback-policy-v0.1.0",
        "record_version": "acknowledgement-record-v0.1.0",
        "acknowledgement_text": CLEAN_TEXT,
        "consent": make_consent().model_dump(mode="json"),
        "observed_span_start": "2026-08-01T00:00:00+00:00",
        "observed_span_end": "2026-08-11T00:00:00+00:00",
    }
    values.update(overrides)
    return values


class TestAcknowledgementRouter:
    def test_router_positive_post(self) -> None:
        client, store = build_client()
        response = client.post(f"/api/v1/students/{LEARNER}/acknowledgements", json=payload())
        assert response.status_code == 200
        body = response.json()
        assert body["acknowledged"] is True
        assert body["record"]["learner_id"] == LEARNER
        assert body["record"]["evidence_status"] == "verified"
        assert len(store.list_for_learner(LEARNER)) == 1

    def test_router_no_consent_returns_403_and_no_write(self) -> None:
        client, store = build_client()
        body = payload()
        body.pop("consent")
        response = client.post(f"/api/v1/students/{LEARNER}/acknowledgements", json=body)
        assert response.status_code == 403
        assert_no_write(store)

    def test_router_cross_student_returns_403_and_no_write(self) -> None:
        client, store = build_client()
        response = client.post(
            f"/api/v1/students/{OTHER}/acknowledgements",
            json=payload(learner_id=OTHER, consent=make_consent(learner_id=OTHER).model_dump(mode="json")),
        )
        assert response.status_code == 403
        assert_no_write(store)

    def test_router_unknown_evidence_returns_404_and_no_write(self) -> None:
        client, store = build_client()
        response = client.post(
            f"/api/v1/students/{LEARNER}/acknowledgements",
            json=payload(source_evidence_ids=["E-NOPE"]),
        )
        assert response.status_code == 404
        assert_no_write(store)

    def test_router_duplicate_returns_409_and_single_write(self) -> None:
        client, store = build_client()
        first = client.post(
            f"/api/v1/students/{LEARNER}/acknowledgements", json=payload()
        )
        assert first.status_code == 200
        second = client.post(
            f"/api/v1/students/{LEARNER}/acknowledgements", json=payload()
        )
        assert second.status_code == 409
        assert len(store.list_for_learner(LEARNER)) == 1

    def test_router_malformed_payload_returns_422_and_no_write(self) -> None:
        client, store = build_client()
        response = client.post(
            f"/api/v1/students/{LEARNER}/acknowledgements",
            json=payload(unexpected_key=True),
        )
        assert response.status_code == 422
        assert_no_write(store)

    def test_router_learner_path_conflict_returns_422(self) -> None:
        client, store = build_client()
        response = client.post(
            f"/api/v1/students/{OTHER}/acknowledgements", json=payload()
        )
        assert response.status_code == 422
        assert_no_write(store)

    def test_router_list_returns_items(self) -> None:
        client, store = build_client()
        client.post(f"/api/v1/students/{LEARNER}/acknowledgements", json=payload())
        response = client.get(f"/api/v1/students/{LEARNER}/acknowledgements")
        assert response.status_code == 200
        body = response.json()
        assert body["learner_id"] == LEARNER
        assert len(body["items"]) == 1
        empty = client.get(f"/api/v1/students/{OTHER}/acknowledgements")
        assert empty.json()["items"] == []

    def test_router_missing_service_returns_503(self) -> None:
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        response = client.post(
            f"/api/v1/students/{LEARNER}/acknowledgements", json=payload()
        )
        assert response.status_code == 503

    def test_router_dependency_reads_app_state(self) -> None:
        store = InMemoryAcknowledgementStore()
        service = build_service(store=store)
        app = FastAPI()
        app.include_router(router)
        app.state.acknowledgement_service = service
        client = TestClient(app)
        assert client.post(
            f"/api/v1/students/{LEARNER}/acknowledgements", json=payload()
        ).status_code == 200
        assert get_acknowledgement_service is not None

    def test_router_paths_are_stable_and_additive(self) -> None:
        paths = {route.path for route in router.routes}
        assert {
            "/api/v1/students/{student_id}/acknowledgements",
        } <= paths
