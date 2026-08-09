"""Practice provenance record tests (activity-only; ADR-03 fields)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.learner.evidence import EvidenceAdmissionStatus
from app.learner.practice_provenance import (
    PRACTICE_ACTIVITY_LIMITATION,
    PracticeActivityStatus,
    PracticeProvenanceRecord,
    validate_practice_provenance,
)


def record(**overrides) -> PracticeProvenanceRecord:
    values = {
        "record_id": "PP000001",
        "student_id": "S001",
        "practice_target_id": "PT000001",
        "exercise_id": "EX000001",
        "exercise_version": "exercise-v0.9.0",
        "attempt_id": "EA000001",
        "evaluation_id": "PE000001",
        "evaluator_version": "practice-evaluator-v0.9.0",
        "activity_status": PracticeActivityStatus.COMPLETED,
        "occurred_at": datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc),
        "policy_version": "feedback-policy-v0.1.0",
        "config_version": "config-v0.9.0",
    }
    values.update(overrides)
    return PracticeProvenanceRecord(**values)


class TestPracticeRecordTyping:
    def test_record_carries_adr03_provenance_fields(self) -> None:
        item = record()
        assert item.actor == "learner"
        assert item.source == "practice_attempt"
        assert item.policy_version == "feedback-policy-v0.1.0"
        assert item.admission_status == EvidenceAdmissionStatus.ADMISSIBLE

    def test_outcome_claim_is_structurally_none(self) -> None:
        assert record().outcome_claim == "none"

    def test_outcome_claim_cannot_be_anything_else(self) -> None:
        with pytest.raises(ValidationError):
            record(outcome_claim="mastery")

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            record(unexpected=True)


class TestPracticeValidation:
    def test_complete_record_validates(self) -> None:
        result = validate_practice_provenance(record())
        assert result.complete
        assert result.missing == []
        assert result.violations == []
        assert any("activity-only" in finding for finding in result.findings)

    def test_missing_fields_fail_closed(self) -> None:
        result = validate_practice_provenance(
            record().model_copy(update={"practice_target_id": "", "exercise_version": ""}),
        )
        assert not result.complete
        assert set(result.missing) == {"practice_target_id", "exercise_version"}

    def test_measurement_contract_keeps_activity_semantics_until_validated(self) -> None:
        result = validate_practice_provenance(
            record(measurement_contract="validated-measurement-v0.0.0"),
        )
        assert any("measurement contract" in finding for finding in result.findings)

    def test_default_limitation_is_activity_only(self) -> None:
        assert PRACTICE_ACTIVITY_LIMITATION in record().limitations
        assert "mastery" in PRACTICE_ACTIVITY_LIMITATION  # prohibition statement
        # The limitation string itself is prohibition context and must scan
        # clean in documentation mode and produce no violation on the record.
        from app.learner.normative import NormativeClaimsScanner

        scanner = NormativeClaimsScanner()
        assert scanner.scan_text(PRACTICE_ACTIVITY_LIMITATION, documentation=True) == []
        assert scanner.scan_pydantic(record(), documentation=True) == []
