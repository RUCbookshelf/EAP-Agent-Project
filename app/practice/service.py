# Practice service — target creation, exercise generation, attempts, evaluation, traces, transfer
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.practice.schemas import (
    AttemptStatus, CompletionStatus, ExerciseAttempt, ExerciseInstance, ExerciseType,
    FeedbackEngagementTrace, PracticeEvaluation, PracticeStateSnapshot, PracticeTarget,
    PracticeTargetStatus, TargetActionStatus, TraceStatus, TransferEvidenceCandidate,
    TransferObservedStatus, WithinTaskResponseCandidate, EvaluationMethod,
    default_exercise_specifications,
)


class PracticeService:
    """Conservative practice-target and exercise management. No mastery, no scoring, no causal claims."""

    def __init__(self, repository):
        self.repo = repository
        self.specs = default_exercise_specifications()

    def create_practice_target(self, student_id: str, source_submission_id: int,
                                source_diagnosis_id: str, target_code: str, target_label: str,
                                source_priority_id: str | None = None,
                                evidence_ids: list[str] | None = None,
                                gate_status: str = "selected") -> dict[str, Any]:
        if gate_status not in ("selected",):
            return {"status": "practice_not_available",
                    "reason": f"Diagnosis gate status '{gate_status}' is not eligible for practice."}
        target = PracticeTarget(
            student_id=student_id, source_submission_id=source_submission_id,
            source_diagnosis_id=source_diagnosis_id, source_priority_id=source_priority_id,
            target_code=target_code, target_label=target_label,
                   evidence_ids=evidence_ids or [], diagnostic_gate_status=gate_status,
           )
        result = target.model_dump(mode="json")
        if result.get("practice_target_id") is None:
            result["practice_target_id"] = ""
        return result

    def generate_exercise(self, practice_target: dict[str, Any],
                          source_text: str, lang: str = "en") -> dict[str, Any]:
        target_code = practice_target.get("target_code", "")
        exercise_type = None
        for et, spec in self.specs.items():
            if target_code in spec.supported_target_codes:
                exercise_type = ExerciseType(et)
                break
        if exercise_type is None:
            return {"status": "practice_not_available",
                    "reason": f"Target code '{target_code}' is not supported by any exercise specification."}
        spec = self.specs[exercise_type.value]
        instructions = spec.learner_instructions.get(lang, spec.learner_instructions.get("en", ""))
        instance = ExerciseInstance(
               practice_target_id=practice_target.get("practice_target_id", ""),
               student_id=practice_target.get("student_id", ""),
            source_submission_id=practice_target.get("source_submission_id", 0),
            exercise_type=exercise_type,
            instructions=instructions,
            source_text=source_text[:500],
            target_evidence_ids=practice_target.get("evidence_ids", []),
            constraints=["Retain original meaning.", "Do not add unsupported content."],
            generation_provider="deterministic_template",
            limitations=spec.limitations,
        )
        return instance.model_dump(mode="json")

    def submit_attempt(self, exercise_id: str, student_id: str,
                       response_text: str, attempt_number: int = 1) -> dict[str, Any]:
        if not response_text or len(response_text.strip()) < 3:
            attempt = ExerciseAttempt(
                exercise_id=exercise_id, student_id=student_id, attempt_number=attempt_number,
                response_text=response_text or "", status=AttemptStatus.INVALID_INPUT,
            )
            return attempt.model_dump(mode="json")
        attempt = ExerciseAttempt(
            exercise_id=exercise_id, student_id=student_id, attempt_number=attempt_number,
            response_text=response_text, status=AttemptStatus.SUBMITTED,
        )
        return attempt.model_dump(mode="json")

    def evaluate_attempt(self, attempt: dict[str, Any], practice_target: dict[str, Any],
                         source_text: str = "") -> dict[str, Any]:
        response_text = attempt.get("response_text", "")
        target_code = practice_target.get("target_code", "")
        if attempt.get("status") == AttemptStatus.INVALID_INPUT.value:
            evaluation = PracticeEvaluation(
                attempt_id=attempt.get("attempt_id", ""), practice_target_id=practice_target.get("practice_target_id", ""),
                completion_status=CompletionStatus.INVALID,
                target_action_status=TargetActionStatus.NOT_APPLICABLE,
                confidence="low",
                limitations=["Invalid input cannot be evaluated."],
            )
            return evaluation.model_dump(mode="json")
        completion = CompletionStatus.COMPLETED
        action = TargetActionStatus.INCONCLUSIVE
        if "lexical_repetition" in target_code and source_text:
            words = source_text.lower().split()
            response_words = response_text.lower().split()
            source_counts = {w: words.count(w) for w in set(words)}
            response_counts = {w: response_words.count(w) for w in set(response_words)}
            max_source = max(source_counts.values()) if source_counts else 0
            max_response = max(response_counts.values()) if response_counts else 0
            if max_response < max_source:
                action = TargetActionStatus.CANDIDATE_DETECTED
            else:
                action = TargetActionStatus.CANDIDATE_NOT_DETECTED
        evaluation = PracticeEvaluation(
            attempt_id=attempt.get("attempt_id", ""), practice_target_id=practice_target.get("practice_target_id", ""),
            completion_status=completion, target_action_status=action,
            evidence=[f"Response length: {len(response_text)} characters"],
            confidence="medium",
            limitations=["Observable evidence is task-specific and does not prove mastery or learning."],
        )
        return evaluation.model_dump(mode="json")

    def create_engagement_trace(self, student_id: str, target_code: str,
                                practice_target_id: str | None = None) -> dict[str, Any]:
        trace = FeedbackEngagementTrace(
            student_id=student_id, target_code=target_code,
            practice_target_id=practice_target_id,
            status=TraceStatus.TARGET_IDENTIFIED,
        )
        return trace.model_dump(mode="json")

    def evaluate_within_task_response(self, student_id: str, practice_target: dict[str, Any],
                                      source_submission_id: int, later_submission_id: int,
                                      revision_group_id: str | None = None,
                                      major_rewrite: bool = False) -> dict[str, Any]:
        if major_rewrite:
            status = "major_rewrite_limits_attribution"
        else:
            status = "response_candidate_detected"
        candidate = WithinTaskResponseCandidate(
            student_id=student_id, practice_target_id=practice_target.get("practice_target_id", ""),
            source_submission_id=source_submission_id, later_submission_id=later_submission_id,
            revision_group_id=revision_group_id,
            target_code=practice_target.get("target_code", ""),
            observed_status=status,
            limitations=["Within-task revision response is a candidate, not proof that feedback caused the change."],
        )
        return candidate.model_dump(mode="json")

    def evaluate_transfer_evidence(self, student_id: str, practice_target: dict[str, Any],
                                   source_submission_id: int, later_submission_id: int,
                                   task_comparability: str = "comparable") -> dict[str, Any]:
        if task_comparability != "comparable":
            observed = TransferObservedStatus.NOT_COMPARABLE
        else:
            observed = TransferObservedStatus.NONRECURRENCE_SIGNAL
        candidate = TransferEvidenceCandidate(
            student_id=student_id, practice_target_id=practice_target.get("practice_target_id", ""),
            source_submission_id=source_submission_id, later_submission_id=later_submission_id,
            task_comparability=task_comparability,
            target_code=practice_target.get("target_code", ""),
            observed_status=observed,
            limitations=["One later observation is not proof of stable transfer. The observation does not establish that practice caused the later pattern."],
        )
        return candidate.model_dump(mode="json")

    def create_practice_state_snapshot(self, student_id: str, current_targets: list[dict] | None = None) -> dict[str, Any]:
        snapshot = PracticeStateSnapshot(
            student_id=student_id,
            current_targets=current_targets or [],
            limitations=["Practice state is descriptive and does not imply proficiency or mastery."],
        )
        return snapshot.model_dump(mode="json")
