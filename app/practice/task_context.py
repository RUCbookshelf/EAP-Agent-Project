"""Focused Practice task-context resolution (v0.9.7-B WU4).

Read-only, learner-owned task-context contract for one persisted Practice
target. A priority-derived target re-resolves its exact priority from
persistence through ``source_priority_id`` (WU2 machinery); a legacy target
uses its existing path without fabricated priority context. No attempt write
and no target-status change ever happens here.
"""

from __future__ import annotations

import json
from typing import Any

from app.practice.mapping import (
    PriorityMappingError,
    build_target_contract,
    parse_stable_priority_reference,
)
from app.practice.ports import PracticeReadPort, PracticeSubmissionReadPort


class PracticeTaskContextService:
    """Resolve the focused task context for one learner-owned target."""

    def __init__(
        self,
        submission_reader: PracticeSubmissionReadPort,
        practice_reader: PracticeReadPort,
    ):
        self._submission_reader = submission_reader
        self._practice_reader = practice_reader

    def resolve_target_context(
        self, *, student_id: str, practice_target_id: str
    ) -> dict[str, Any]:
        """Resolve the task context; raises PriorityMappingError for
        not-found (404) and cross-student (403) conditions and returns a
        controlled ``context_status: unavailable`` payload for provenance
        that no longer resolves safely."""
        try:
            target = self._practice_reader.get_practice_target(practice_target_id)
        except json.JSONDecodeError:
            raise PriorityMappingError(
                "malformed_priority", "Stored target record is malformed."
            ) from None
        if target is None:
            raise PriorityMappingError("source_not_found", "Practice target not found.")
        if target.get("student_id") != student_id:
            raise PriorityMappingError(
                "cross_student",
                "Practice target does not belong to the requested learner.",
            )
        reference = target.get("source_priority_id")
        if reference:
            return self._resolve_priority_context(target, reference, student_id)
        return self._resolve_legacy_context(target, student_id)

    def _resolve_priority_context(
        self, target: dict[str, Any], reference: str, student_id: str
    ) -> dict[str, Any]:
        try:
            feedback_id, priority_index = parse_stable_priority_reference(reference)
        except PriorityMappingError:
            return self._unavailable(target, "malformed_provenance")
        bundle = self._submission_reader.get_submission_bundle(
            int(target.get("source_submission_id") or 0)
        )
        if bundle is None:
            return self._unavailable(target, "missing_feedback")
        if bundle.get("student_id") != student_id:
            raise PriorityMappingError(
                "cross_student",
                "Source submission does not belong to the requested learner.",
            )
        try:
            contract = build_target_contract(
                bundle,
                student_id=student_id,
                feedback_id=feedback_id,
                priority_index=priority_index,
            )
        except PriorityMappingError as exc:
            return self._unavailable(target, exc.kind)
        if contract.target_code != target.get("target_code"):
            return self._unavailable(target, "target_code_mismatch")
        context = contract.priority_context
        return {
            "context_status": "priority",
            "practice_target_id": target.get("practice_target_id"),
            "student_id": target.get("student_id"),
            "source_submission_id": target.get("source_submission_id"),
            "source_diagnosis_id": target.get("source_diagnosis_id"),
            "source_priority_id": reference,
            "target_code": target.get("target_code"),
            "target_label": target.get("target_label"),
            "status": target.get("status"),
            "priority_context": context.model_dump(mode="json"),
            "source_writing_text": bundle.get("essay_text") or "",
        }

    def _resolve_legacy_context(
        self, target: dict[str, Any], student_id: str
    ) -> dict[str, Any]:
        bundle = self._submission_reader.get_submission_bundle(
            int(target.get("source_submission_id") or 0)
        )
        if bundle is None:
            return self._unavailable(target, "missing_feedback")
        if bundle.get("student_id") != student_id:
            raise PriorityMappingError(
                "cross_student",
                "Source submission does not belong to the requested learner.",
            )
        return {
            "context_status": "legacy",
            "practice_target_id": target.get("practice_target_id"),
            "student_id": target.get("student_id"),
            "source_submission_id": target.get("source_submission_id"),
            "source_diagnosis_id": target.get("source_diagnosis_id"),
            "source_priority_id": None,
            "target_code": target.get("target_code"),
            "target_label": target.get("target_label"),
            "status": target.get("status"),
            "priority_context": None,
            "source_writing_text": bundle.get("essay_text") or "",
        }

    @staticmethod
    def _unavailable(target: dict[str, Any], reason: str) -> dict[str, Any]:
        return {
            "context_status": "unavailable",
            "reason": reason,
            "practice_target_id": target.get("practice_target_id"),
            "student_id": target.get("student_id"),
            "source_submission_id": target.get("source_submission_id"),
            "source_priority_id": target.get("source_priority_id"),
            "target_code": target.get("target_code"),
            "target_label": target.get("target_label"),
            "status": target.get("status"),
            "priority_context": None,
            "source_writing_text": "",
        }
