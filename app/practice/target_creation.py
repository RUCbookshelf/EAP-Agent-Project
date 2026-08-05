"""Idempotent, ownership-validated Practice target creation (v0.9.7-B WU3).

Consumes the WU2 mapping contract and completes the creation layer:

    Validated PriorityTargetContract
        -> lookup existing target by logical key
        -> reuse when present
        -> otherwise create and persist

Logical uniqueness key (frozen): (student_id, source_submission_id,
source_priority_id). At most one target per key and at most one ACTIVE
target per key; the database-level partial unique index (migration 13) is
the concurrency backstop, and a concurrent duplicate insert is recovered by
re-reading the existing row.

The legacy path (no priority reference) validates ownership and the evidence
boundary but has no idempotency key; client-supplied evidence IDs are never
trusted on any creation path.

Streamlit-free; business rules live here, not in the router; persistence
stays behind the existing practice ports.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.practice.mapping import (
    PriorityMappingError,
    PriorityTargetContract,
    diagnosis_contains_id,
)
from app.practice.ports import (
    PracticeReadPort,
    PracticeSubmissionReadPort,
    PracticeWritePort,
)
from app.practice.service import PracticeService


class PracticeTargetCreationService:
    """Create-or-reuse Practice targets with full ownership validation."""

    def __init__(
        self,
        submission_reader: PracticeSubmissionReadPort,
        practice_reader: PracticeReadPort,
        practice_writer: PracticeWritePort,
        practice_service: PracticeService,
    ):
        self._submission_reader = submission_reader
        self._practice_reader = practice_reader
        self._practice_writer = practice_writer
        self._practice_service = practice_service

    def create_or_reuse_priority_target(
        self, contract: PriorityTargetContract
    ) -> dict[str, Any]:
        """Idempotent create-or-reuse for one validated priority contract.

        An existing target for the key (any status) is returned unchanged.
        A concurrent duplicate insert is resolved by re-reading the existing
        row. Returns the persisted target dict (new or reused).
        """
        existing = self._find_by_key(
            contract.student_id,
            contract.source_submission_id,
            contract.source_priority_id,
        )
        if existing is not None:
            return existing
        target = self._practice_service.create_practice_target(
            student_id=contract.student_id,
            source_submission_id=contract.source_submission_id,
            source_diagnosis_id=contract.source_diagnosis_id,
            target_code=contract.target_code,
            target_label=contract.target_label,
            source_priority_id=contract.source_priority_id,
            evidence_ids=contract.evidence_ids,
            gate_status=contract.diagnostic_gate_status,
        )
        try:
            return self._practice_writer.save_practice_target(target)
        except sqlite3.IntegrityError:
            existing = self._find_by_key(
                contract.student_id,
                contract.source_submission_id,
                contract.source_priority_id,
            )
            if existing is not None:
                return existing
            raise

    def create_legacy_target(
        self,
        *,
        student_id: str,
        source_submission_id: int,
        source_diagnosis_id: str,
        target_code: str,
        target_label: str,
        evidence_ids: list[str] | None = None,
        gate_status: str = "selected",
    ) -> dict[str, Any]:
        """Ownership-validated creation without priority provenance.

        Validation completes before any write:
        - the source submission must exist and belong to the learner;
        - the source diagnosis must belong to the source submission;
        - client-supplied evidence IDs are rejected on the legacy path
          (evidence requires a validated priority reference).
        """
        bundle = self._submission_reader.get_submission_bundle(source_submission_id)
        if bundle is None:
            raise PriorityMappingError("source_not_found", "Source submission not found.")
        if bundle.get("student_id") != student_id:
            raise PriorityMappingError(
                "cross_student",
                "Source submission does not belong to the requested learner.",
            )
        if evidence_ids:
            raise PriorityMappingError(
                "invalid_evidence",
                "Client-supplied evidence_ids require a validated priority reference.",
            )
        diagnosis = bundle.get("diagnosis")
        if not isinstance(diagnosis, dict) or not diagnosis_contains_id(
            diagnosis, source_diagnosis_id
        ):
            raise PriorityMappingError(
                "unresolved_priority",
                "The source diagnosis does not belong to the source submission.",
            )
        target = self._practice_service.create_practice_target(
            student_id=student_id,
            source_submission_id=source_submission_id,
            source_diagnosis_id=source_diagnosis_id,
            target_code=target_code,
            target_label=target_label,
            source_priority_id=None,
            evidence_ids=[],
            gate_status=gate_status,
        )
        if target.get("status") == "practice_not_available":
            return target
        return self._practice_writer.save_practice_target(target)

    def _find_by_key(
        self,
        student_id: str,
        source_submission_id: int,
        source_priority_id: str,
    ) -> dict[str, Any] | None:
        """Student-scoped lookup by the logical uniqueness key."""
        for target in self._practice_reader.list_practice_targets(student_id):
            if (
                target.get("source_submission_id") == source_submission_id
                and target.get("source_priority_id") == source_priority_id
            ):
                return target
        return None
