"""WU2 Practice/Review dual-channel evidence bridge tests (focused).

Covers the learner-owned orchestration over the structural CORE-consumption
boundary: practice labeling vs authentic evidence, the three CORE rating
channels with rating-rule/scheduler provenance, actual delegation through
the injected boundary, fail-closed pre-flight validation, and the
no-normative-claims surface.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.learner.normative import NormativeClaimsScanner
from app.learner.review_bridge import (
    PRACTICE_ACTIVITY_LIMITATION,
    PracticeActivityRecord,
    PracticeActivityStatus,
    Rating,
    RATING_ORDINALS,
    ReviewBridgeError,
    ReviewRequestRecord,
)
from app.practice.review_transfer import (
    BRIDGE_VERSION,
    PracticeReviewTransferOrchestrator,
)


UTC = timezone.utc
OCCURRED_AT = datetime(2026, 8, 12, 8, 30, 0, tzinfo=UTC)
REVIEWED_AT = datetime(2026, 8, 12, 8, 45, 0, tzinfo=UTC)


class CoreLikeError(Exception):
    """Mimics the CORE ``ReviewError`` shape (stable ``kind`` + message)."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


class FakeCoreReviewService:
    """Recording fake implementing the learner ``CoreReviewServicePort``."""

    rating_rule_version = "rating-rule-v1.0.0"

    def __init__(self, *, fail_kind: str | None = None) -> None:
        self.calls: list[tuple[str, object]] = []
        self.fail_kind = fail_kind
        self.identity = {
            "implementation": "py-fsrs",
            "library_version": "6.3.2",
            "algorithm": "FSRS",
            "parameters": {
                "w": [0.4, 0.6, 2.4, 5.8, 4.93, 0.94, 0.86, 0.01, 1.49,
                      0.14, 0.94, 2.18, 0.05, 0.34, 1.26, 0.29, 2.61],
                "enable_fuzz": False,
            },
        }

    def scheduler_identity(self) -> dict:
        return self.identity

    def record_practice_activity(self, activity: object) -> dict:
        self.calls.append(("record_practice_activity", activity))
        if self.fail_kind is not None:
            raise CoreLikeError(self.fail_kind, f"core rejected: {self.fail_kind}")
        return {
            "activity_id": getattr(activity, "activity_id", "PA000001"),
            "student_id": activity.student_id,  # type: ignore[attr-defined]
            "learning_item_id": activity.learning_item_id,  # type: ignore[attr-defined]
            "activity_type": activity.activity_type,  # type: ignore[attr-defined]
            "source": activity.source,  # type: ignore[attr-defined]
            "status": activity.status.value,  # type: ignore[attr-defined]
            "evidence_kind": activity.evidence_kind,  # type: ignore[attr-defined]
            "authentic_evidence_status": activity.authentic_evidence_status,  # type: ignore[attr-defined]
            "provenance": activity.provenance,  # type: ignore[attr-defined]
            "limitations": activity.limitations,  # type: ignore[attr-defined]
        }

    def record_review(self, **kwargs: object) -> dict:
        self.calls.append(("record_review", kwargs))
        if self.fail_kind is not None:
            raise CoreLikeError(self.fail_kind, f"core rejected: {self.fail_kind}")
        system = str(kwargs["system_provisional_rating"])
        learner = kwargs.get("learner_self_rating")
        learner_text = None if learner is None else str(learner)
        final = (
            learner_text
            if learner_text is not None
            and RATING_ORDINALS[Rating(learner_text)]
            < RATING_ORDINALS[Rating(system)]
            else system
        )
        return {
            "review_event_id": "RE000001",
            "student_id": kwargs["student_id"],
            "learning_item_id": kwargs["learning_item_id"],
            "practice_activity_id": kwargs.get("practice_activity_id"),
            "reviewed_at": kwargs["reviewed_at"].isoformat(),  # type: ignore[attr-defined]
            "system_provisional_rating": system,
            "learner_self_rating": learner_text,
            "final_scheduler_rating": final,
            "rating_rule_version": self.rating_rule_version,
            "scheduler_implementation": self.identity["implementation"],
            "scheduler_version": self.identity["library_version"],
            "scheduler_parameters": self.identity["parameters"],
            "authentic_evidence_status": kwargs["authentic_evidence_status"],
            "provenance": kwargs["provenance"],
        }


def activity(**overrides) -> PracticeActivityRecord:
    values = {
        "activity_id": "PA-PENDING",
        "student_id": "S001",
        "learning_item_id": "LI000001",
        "activity_type": "guided_sentence_rewrite",
        "status": PracticeActivityStatus.COMPLETED,
        "occurred_at": OCCURRED_AT,
    }
    values.update(overrides)
    return PracticeActivityRecord(**values)


def review(**overrides) -> ReviewRequestRecord:
    values = {
        "student_id": "S001",
        "learning_item_id": "LI000001",
        "reviewed_at": REVIEWED_AT,
        "system_provisional_rating": Rating.AGAIN,
        "learner_self_rating": Rating.GOOD,
    }
    values.update(overrides)
    return ReviewRequestRecord(**values)


class TestPracticeActivityLabeling:
    def test_activity_is_structurally_practice(self) -> None:
        item = activity()
        assert item.evidence_kind == "practice"
        assert item.source == "practice"

    def test_evidence_kind_cannot_be_authentic(self) -> None:
        with pytest.raises(ValidationError):
            activity(evidence_kind="authentic")

    def test_authentic_evidence_defaults_to_insufficient(self) -> None:
        assert activity().authentic_evidence_status == "insufficient"

    def test_authentic_evidence_present_must_be_explicit(self) -> None:
        assert activity(authentic_evidence_status="present").authentic_evidence_status == "present"
        with pytest.raises(ValidationError):
            activity(authentic_evidence_status="confirmed")

    def test_activity_status_is_activity_only_vocabulary(self) -> None:
        with pytest.raises(ValidationError):
            activity(status="mastered")

    def test_record_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            activity(unexpected=True)


class TestRatingChannelsAndProvenance:
    def test_both_input_rating_channels_forwarded_separately(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        orchestrator.record_review(review())
        kwargs = fake.calls[0][1]
        assert isinstance(kwargs, dict)
        assert kwargs["system_provisional_rating"] == Rating.AGAIN.value
        assert kwargs["learner_self_rating"] == Rating.GOOD.value
        # No averaging or reinterpretation: the channels stay distinct and
        # the bridge never computes or emits a final rating itself.
        assert "final_scheduler_rating" not in kwargs

    def test_learner_self_rating_optional(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        orchestrator.record_review(review(learner_self_rating=None))
        kwargs = fake.calls[0][1]
        assert isinstance(kwargs, dict)
        assert kwargs["learner_self_rating"] is None

    def test_rating_rule_and_scheduler_provenance_carried(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        result = orchestrator.record_review(review())
        kwargs = fake.calls[0][1]
        assert isinstance(kwargs, dict)
        provenance = kwargs["provenance"]
        assert isinstance(provenance, dict)
        assert provenance["rating_rule_version"] == "rating-rule-v1.0.0"
        assert provenance["scheduler_implementation"] == "py-fsrs"
        assert provenance["scheduler_version"] == "6.3.2"
        assert provenance["scheduler_parameters"] == fake.identity["parameters"]
        assert provenance["bridge_version"] == BRIDGE_VERSION
        # The returned event carries all three channels from the CORE side.
        assert result["system_provisional_rating"] == "again"
        assert result["learner_self_rating"] == "good"
        assert result["final_scheduler_rating"] == "again"

    def test_provenance_is_deterministic(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        first = orchestrator.record_review(review())
        second = orchestrator.record_review(review())
        assert first["provenance"] == second["provenance"]


class TestCoreServiceDelegation:
    def test_activity_recorded_through_injected_boundary(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        result = orchestrator.record_practice_activity(activity())
        assert fake.calls[0][0] == "record_practice_activity"
        assert result["evidence_kind"] == "practice"

    def test_review_recorded_through_injected_boundary(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        orchestrator.record_review(review())
        assert fake.calls[0][0] == "record_review"

    def test_review_only_when_explicitly_requested(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        orchestrator.record_practice_activity(activity())
        assert [call[0] for call in fake.calls] == ["record_practice_activity"]


class TestFailClosedPreflight:
    def test_missing_core_service_blocks_activity(self) -> None:
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=None)
        with pytest.raises(ReviewBridgeError) as excinfo:
            orchestrator.record_practice_activity(activity())
        assert excinfo.value.kind == "core_review_service_missing"

    def test_missing_core_service_blocks_review(self) -> None:
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=None)
        with pytest.raises(ReviewBridgeError) as excinfo:
            orchestrator.record_review(review())
        assert excinfo.value.kind == "core_review_service_missing"

    def test_naive_datetime_fails_closed(self) -> None:
        with pytest.raises(ValidationError):
            activity(occurred_at=datetime(2026, 8, 12, 8, 30))
        with pytest.raises(ValidationError):
            review(reviewed_at=datetime(2026, 8, 12, 8, 45))

    def test_non_utc_datetime_fails_closed(self) -> None:
        with pytest.raises(ValidationError):
            activity(occurred_at=datetime(2026, 8, 12, 16, 30, tzinfo=timezone(timedelta(hours=8))))
        with pytest.raises(ValidationError):
            review(reviewed_at=datetime(2026, 8, 12, 16, 45, tzinfo=timezone(timedelta(hours=8))))

    def test_mutated_non_utc_time_fails_closed_before_call(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        record = review()
        record.reviewed_at = datetime(2026, 8, 12, 8, 45)  # naive after construction
        with pytest.raises(ReviewBridgeError) as excinfo:
            orchestrator.record_review(record)
        assert excinfo.value.kind == "invalid_reviewed_at"
        assert fake.calls == []

    def test_invalid_rating_fails_closed(self) -> None:
        with pytest.raises(ValidationError):
            review(system_provisional_rating="excellent")
        with pytest.raises(ValidationError):
            review(learner_self_rating="good-enough")

    def test_invalid_authentic_evidence_status_fails_closed(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        record = review()
        record.authentic_evidence_status = "confirmed"  # type: ignore[assignment]
        with pytest.raises(ReviewBridgeError) as excinfo:
            orchestrator.record_review(record)
        assert excinfo.value.kind == "invalid_authentic_evidence_status"
        assert fake.calls == []

    def test_malformed_non_json_provenance_fails_closed(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        with pytest.raises(ReviewBridgeError) as excinfo:
            orchestrator.record_review(
                review(provenance={"observed_at": OCCURRED_AT})
            )
        assert excinfo.value.kind == "malformed_provenance"
        assert fake.calls == []

    def test_provenance_cannot_override_bridge_fields(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        with pytest.raises(ReviewBridgeError) as excinfo:
            orchestrator.record_review(
                review(provenance={"rating_rule_version": "tampered"})
            )
        assert excinfo.value.kind == "malformed_provenance"
        assert fake.calls == []

    def test_activity_provenance_cannot_override_channel_fields(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        with pytest.raises(ReviewBridgeError) as excinfo:
            orchestrator.record_practice_activity(
                activity(provenance={"evidence_channel": "authentic"})
            )
        assert excinfo.value.kind == "malformed_provenance"
        assert fake.calls == []


class TestCoreRejectionsPropagate:
    @pytest.mark.parametrize(
        "kind",
        [
            "learning_item_not_found",
            "learning_item_owner_mismatch",
            "practice_activity_already_exists",
        ],
    )
    def test_activity_core_rejections_fail_closed(self, kind: str) -> None:
        fake = FakeCoreReviewService(fail_kind=kind)
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        with pytest.raises(CoreLikeError) as excinfo:
            orchestrator.record_practice_activity(activity())
        assert excinfo.value.kind == kind

    @pytest.mark.parametrize(
        "kind",
        [
            "learning_item_not_found",
            "learning_item_owner_mismatch",
            "practice_activity_not_found",
            "practice_activity_owner_mismatch",
            "review_event_already_exists",
        ],
    )
    def test_review_core_rejections_fail_closed(self, kind: str) -> None:
        fake = FakeCoreReviewService(fail_kind=kind)
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        with pytest.raises(CoreLikeError) as excinfo:
            orchestrator.record_review(review())
        assert excinfo.value.kind == kind

    def test_missing_scheduler_identity_fails_closed(self) -> None:
        fake = FakeCoreReviewService()
        fake.identity = None
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        with pytest.raises(ReviewBridgeError) as excinfo:
            orchestrator.record_review(review())
        assert excinfo.value.kind == "invalid_scheduler_identity"
        assert fake.calls == []

    def test_incomplete_scheduler_identity_fails_closed(self) -> None:
        fake = FakeCoreReviewService()
        fake.identity = {"implementation": "py-fsrs"}
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        with pytest.raises(ReviewBridgeError) as excinfo:
            orchestrator.record_review(review())
        assert excinfo.value.kind == "invalid_scheduler_identity"
        assert fake.calls == []

    def test_missing_rating_rule_version_fails_closed(self) -> None:
        fake = FakeCoreReviewService()
        fake.rating_rule_version = ""
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        with pytest.raises(ReviewBridgeError) as excinfo:
            orchestrator.record_review(review())
        assert excinfo.value.kind == "invalid_rating_rule_version"
        assert fake.calls == []


class TestEvidenceChannelsSeparate:
    def test_activity_payload_carries_practice_channel_markers(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        orchestrator.record_practice_activity(activity())
        payload = fake.calls[0][1]
        assert payload.evidence_kind == "practice"  # type: ignore[attr-defined]
        provenance = payload.provenance  # type: ignore[attr-defined]
        assert provenance["evidence_channel"] == "practice"
        assert provenance["authentic_evidence_channel"] == "separate"
        assert provenance["bridge"] == "learner_practice_review_bridge"

    def test_practice_completion_never_claims_transfer(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        result = orchestrator.record_practice_activity(activity())
        assert any(
            "does not imply authentic writing transfer" in str(limit)
            for limit in result["limitations"]
        )
        assert PRACTICE_ACTIVITY_LIMITATION in result["limitations"]

    def test_review_authentic_status_forwarded_without_implying_transfer(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        result = orchestrator.record_review(
            review(authentic_evidence_status="present")
        )
        assert result["authentic_evidence_status"] == "present"
        provenance = result["provenance"]
        assert provenance["evidence_channel"] == "practice"
        assert provenance["authentic_evidence_channel"] == "separate"


class TestNoNormativeLanguage:
    def test_records_scan_clean_in_documentation_mode(self) -> None:
        scanner = NormativeClaimsScanner()
        assert scanner.scan_pydantic(activity(), documentation=True) == []
        assert scanner.scan_pydantic(review(), documentation=True) == []

    def test_emitted_activity_payload_only_prohibits_in_limitations(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        orchestrator.record_practice_activity(activity())
        payload = fake.calls[0][1]
        violations = NormativeClaimsScanner().scan_mapping(
            payload.model_dump(mode="json"), documentation=False  # type: ignore[attr-defined]
        )
        assert all(
            violation.location == "limitations"
            or violation.location.startswith("limitations[")
            for violation in violations
        )

    def test_emitted_review_payload_only_prohibits_in_limitations(self) -> None:
        fake = FakeCoreReviewService()
        orchestrator = PracticeReviewTransferOrchestrator(core_review_service=fake)
        orchestrator.record_review(review())
        kwargs = fake.calls[0][1]
        assert isinstance(kwargs, dict)
        violations = NormativeClaimsScanner().scan_mapping(
            kwargs, documentation=False
        )
        assert violations == []
