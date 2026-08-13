"""Learner-owned Practice/Review transfer orchestration (WU2).

Records practice activity evidence and, when explicitly requested with valid
UTC time and valid inputs, review evidence through the injected CORE review
service. The dual channels stay separate (practice evidence vs authentic
writing application evidence), the three CORE rating channels are forwarded
separately, and the CORE rating-rule version plus scheduler
identity/version/parameters are carried explicitly in provenance.

Fail-closed: missing CORE service, missing durable LearningItem, ownership
mismatch, invalid rating, invalid authentic-evidence status, malformed
provenance, or non-UTC time all prevent any write. Failures raised inside
the injected CORE service propagate unchanged with their CORE stable kind;
LEARNER never re-implements CORE checks.
"""

from __future__ import annotations

from datetime import timezone
from typing import Any

from app.learner.review_bridge import (
    ACTIVITY_RESERVED_PROVENANCE_KEYS,
    BRIDGE_SOURCE,
    BRIDGE_VERSION,
    RESERVED_PROVENANCE_KEYS,
    CoreReviewServicePort,
    PracticeActivityRecord,
    ReviewBridgeError,
    ReviewRequestRecord,
    ensure_json_safe,
    validate_provenance,
)

__all__ = ["BRIDGE_VERSION", "PracticeReviewTransferOrchestrator"]


def _as_json(value: Any) -> dict[str, Any]:
    """Normalize the injected service result to a JSON-safe dict."""
    if value is None:
        raise ReviewBridgeError(
            "invalid_core_service_response",
            "the injected CORE service returned no record.",
        )
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return dict(value)


def _identity_fields(identity: Any) -> tuple[str, str, dict[str, Any]]:
    """Extract scheduler implementation/version/parameters structurally."""
    if identity is None:
        raise ReviewBridgeError(
            "invalid_scheduler_identity",
            "the injected CORE service returned no scheduler identity.",
        )
    if isinstance(identity, dict):
        implementation = identity.get("implementation")
        library_version = identity.get("library_version")
        parameters = identity.get("parameters")
    else:
        implementation = getattr(identity, "implementation", None)
        library_version = getattr(identity, "library_version", None)
        parameters = getattr(identity, "parameters", None)
    if (
        not isinstance(implementation, str)
        or not implementation
        or not isinstance(library_version, str)
        or not library_version
        or not isinstance(parameters, dict)
    ):
        raise ReviewBridgeError(
            "invalid_scheduler_identity",
            "the injected CORE service returned an incomplete scheduler "
            "identity; provenance cannot be reconstructed.",
        )
    return implementation, library_version, parameters


class PracticeReviewTransferOrchestrator:
    """Learner-owned orchestration over the injected CORE review service."""

    def __init__(
        self,
        *,
        core_review_service: CoreReviewServicePort | None = None,
    ) -> None:
        self._core = core_review_service

    def _require_core(self, operation: str) -> CoreReviewServicePort:
        if self._core is None:
            raise ReviewBridgeError(
                "core_review_service_missing",
                f"cannot record {operation}: no CORE review service is "
                "injected; integration must provide it before any write.",
            )
        return self._core

    @staticmethod
    def _require_utc(value: Any, *, name: str) -> None:
        """Runtime re-check (records are mutable after construction)."""
        if value is None:
            return
        if (
            value.tzinfo is None
            or value.utcoffset() != timezone.utc.utcoffset(None)
        ):
            raise ReviewBridgeError(
                f"invalid_{name}",
                f"{name} must be timezone-aware and set to UTC.",
            )

    @staticmethod
    def _require_authentic_status(value: str) -> None:
        if value not in ("insufficient", "present"):
            raise ReviewBridgeError(
                "invalid_authentic_evidence_status",
                "authentic_evidence_status must be 'insufficient' or "
                f"'present', got {value!r}.",
            )

    def record_practice_activity(
        self, activity: PracticeActivityRecord
    ) -> dict[str, Any]:
        """Record one practice activity through the injected CORE service.

        The activity is always labeled ``evidence_kind="practice"`` and its
        provenance marks the authentic-writing channel as separate. No
        review is implied or triggered by this call.
        """
        core = self._require_core("a practice activity")
        self._require_utc(activity.occurred_at, name="occurred_at")
        self._require_utc(activity.completed_at, name="completed_at")
        self._require_authentic_status(activity.authentic_evidence_status)
        validate_provenance(
            activity.provenance,
            reserved=ACTIVITY_RESERVED_PROVENANCE_KEYS,
        )
        provenance = {
            **activity.provenance,
            "bridge": BRIDGE_SOURCE,
            "bridge_version": BRIDGE_VERSION,
            "evidence_channel": "practice",
            "authentic_evidence_channel": "separate",
        }
        ensure_json_safe(provenance)
        payload = activity.model_copy(update={"provenance": provenance})
        return _as_json(core.record_practice_activity(payload))

    def record_review(self, request: ReviewRequestRecord) -> dict[str, Any]:
        """Record one review through the injected CORE service when requested.

        The system provisional and learner self rating channels are forwarded
        separately (never averaged or reinterpreted); the CORE versioned
        rating rule resolves the final scheduler rating. Provenance carries
        the CORE rating-rule version and the scheduler
        implementation/version/parameters for deterministic reconstruction.
        """
        core = self._require_core("a review event")
        self._require_utc(request.reviewed_at, name="reviewed_at")
        self._require_authentic_status(request.authentic_evidence_status)
        validate_provenance(
            request.provenance, reserved=RESERVED_PROVENANCE_KEYS
        )

        rule_version = getattr(core, "rating_rule_version", None)
        if not isinstance(rule_version, str) or not rule_version:
            raise ReviewBridgeError(
                "invalid_rating_rule_version",
                "the injected CORE service provided no rating-rule version.",
            )
        implementation, library_version, parameters = _identity_fields(
            core.scheduler_identity()
        )
        provenance = {
            **request.provenance,
            "bridge": BRIDGE_SOURCE,
            "bridge_version": BRIDGE_VERSION,
            "evidence_channel": "practice",
            "authentic_evidence_channel": "separate",
            "rating_rule_version": rule_version,
            "scheduler_implementation": implementation,
            "scheduler_version": library_version,
            "scheduler_parameters": parameters,
        }
        ensure_json_safe(provenance)
        return _as_json(
            core.record_review(
                student_id=request.student_id,
                learning_item_id=request.learning_item_id,
                practice_activity_id=request.practice_activity_id,
                reviewed_at=request.reviewed_at,
                system_provisional_rating=request.system_provisional_rating.value,
                learner_self_rating=(
                    request.learner_self_rating.value
                    if request.learner_self_rating is not None
                    else None
                ),
                authentic_evidence_status=request.authentic_evidence_status,
                provenance=provenance,
            )
        )
