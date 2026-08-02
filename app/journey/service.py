"""Learning Journey service — conservative, read-time event derivation.

Every Journey event is derived from an authoritative persisted source record
(essay, analysis run, feedback record, practice target, exercise attempt,
practice evaluation, within-task response candidate, or transfer evidence
candidate). Nothing is written by this service, no event is created by page
rendering, navigation, locale switching, or refresh, and no unsupported
learning claim is produced.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

EVENT_VERSION = "journey-event-v0.9.3-c"

# Event types (stable identifiers; localization keys in locales/*.json)
EVENT_WRITING_SUBMITTED = "writing_submitted"
EVENT_REVISION_SUBMITTED = "revision_submitted"
EVENT_ANALYSIS_COMPLETED = "analysis_completed"
EVENT_FEEDBACK_AVAILABLE = "feedback_available"
EVENT_FEEDBACK_PRIORITY_AVAILABLE = "feedback_priority_available"
EVENT_FEEDBACK_WITHOUT_PRIORITY = "feedback_without_priority"
EVENT_INSUFFICIENT_EVIDENCE = "insufficient_evidence"
EVENT_PRACTICE_AVAILABLE = "practice_available"
EVENT_EXERCISE_ATTEMPTED = "exercise_attempted"
EVENT_PRACTICE_EVALUATION_RECORDED = "practice_evaluation_recorded"
EVENT_WITHIN_TASK_RESPONSE_OBSERVED = "within_task_response_observed"
EVENT_LATER_TASK_EVIDENCE = "later_task_evidence"

CONFIRMED_RECORD = "confirmed_record"
DERIVED_STATE = "derived_state"

# Natural journey stage order for stable secondary sorting.
EVENT_STAGE_ORDER = {
    EVENT_WRITING_SUBMITTED: 10,
    EVENT_REVISION_SUBMITTED: 10,
    EVENT_INSUFFICIENT_EVIDENCE: 20,
    EVENT_ANALYSIS_COMPLETED: 30,
    EVENT_FEEDBACK_AVAILABLE: 40,
    EVENT_FEEDBACK_PRIORITY_AVAILABLE: 50,
    EVENT_FEEDBACK_WITHOUT_PRIORITY: 50,
    EVENT_PRACTICE_AVAILABLE: 60,
    EVENT_EXERCISE_ATTEMPTED: 70,
    EVENT_PRACTICE_EVALUATION_RECORDED: 80,
    EVENT_WITHIN_TASK_RESPONSE_OBSERVED: 90,
    EVENT_LATER_TASK_EVIDENCE: 100,
}


class JourneyEvent(BaseModel):
    """A single conservative Learning Journey event."""

    model_config = ConfigDict(extra="forbid")

    event_type: str
    title_key: str
    description_key: str
    description_params: dict[str, Any] = {}
    source_record_type: str
    source_record_id: str
    learner_id: str
    task_id: str | None = None
    submission_id: int | None = None
    occurred_at: str
    event_version: str = EVENT_VERSION
    evidence_status: str = CONFIRMED_RECORD
    limitations: list[str] = []
    deduplication_key: str
    student_visible: bool = True
    research_detail: dict[str, Any] = {}


def _normalize_timestamp(value: str | None) -> str:
    """Return a UTC ISO-8601 sortable timestamp for mixed stored formats."""
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _fb_priority_count(feedback_record: dict[str, Any]) -> int:
    raw = feedback_record.get("feedback_json") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            raw = {}
    priorities = raw.get("priority_feedback") or []
    return len(priorities) if isinstance(priorities, list) else 0


@runtime_checkable
class JourneyStudentReadPort(Protocol):
    """Student lookup contract for JourneyService (Learner-owned)."""

    def get_student(self, student_id: str) -> dict[str, Any] | None: ...


@runtime_checkable
class JourneyProjectionReadPort(Protocol):
    """Practice-owned Journey projection contract for JourneyService."""

    def list_essays_by_student(self, student_id: str) -> list[dict]: ...
    def list_analysis_runs_for_student(self, student_id: str) -> list[dict]: ...
    def list_feedback_records_for_student(self, student_id: str) -> list[dict]: ...
    def list_practice_targets(self, student_id: str) -> list[dict]: ...
    def list_exercise_attempts_by_student(self, student_id: str) -> list[dict]: ...
    def list_practice_evaluations_by_student(self, student_id: str) -> list[dict]: ...
    def list_within_task_responses(self, student_id: str) -> list[dict]: ...
    def list_transfer_evidence_candidates(self, student_id: str) -> list[dict]: ...


class JourneyService:
    """Derive the Learning Journey for one learner from persisted records."""

    def __init__(
        self,
        student_reader: JourneyStudentReadPort,
        projection_reader: JourneyProjectionReadPort,
    ) -> None:
        self.student_reader = student_reader
        self.projection_reader = projection_reader

    def get_journey(self, student_id: str) -> dict[str, Any]:
        learner = self.student_reader.get_student(student_id)
        if learner is None:
            raise LookupError("Student not found.")

        essays = self.projection_reader.list_essays_by_student(student_id)
        analyses = {
            int(run.get("essay_id")): run
            for run in self.projection_reader.list_analysis_runs_for_student(student_id)
        }
        feedbacks = {
            int(rec.get("essay_id")): rec
            for rec in self.projection_reader.list_feedback_records_for_student(student_id)
        }
        targets = self.projection_reader.list_practice_targets(student_id)
        attempts = self.projection_reader.list_exercise_attempts_by_student(student_id)
        evaluations = self.projection_reader.list_practice_evaluations_by_student(student_id)
        responses = self.projection_reader.list_within_task_responses(student_id)
        transfers = self.projection_reader.list_transfer_evidence_candidates(student_id)

        events: list[JourneyEvent] = []

        for essay in essays:
            essay_id = int(essay.get("essay_id") or 0)
            submitted_at = _normalize_timestamp(essay.get("submitted_at"))
            revision_of = essay.get("revision_of_submission_id")
            is_revision = revision_of is not None
            task_id = essay.get("revision_group_id") or f"essay-{essay_id}"
            if is_revision:
                events.append(JourneyEvent(
                    event_type=EVENT_REVISION_SUBMITTED,
                    title_key="journey_event_revision_submitted",
                    description_key="journey_event_revision_submitted_desc",
                    description_params={"source": revision_of},
                    source_record_type="essay",
                    source_record_id=str(essay_id),
                    learner_id=student_id,
                    task_id=task_id,
                    submission_id=essay_id,
                    occurred_at=submitted_at,
                    limitations=["A revision record is a submitted draft, not evidence of learning."],
                    deduplication_key=f"{EVENT_REVISION_SUBMITTED}:essay:{essay_id}",
                    research_detail={"revision_of_submission_id": revision_of, "revision_sequence": essay.get("revision_sequence")},
                ))
            else:
                events.append(JourneyEvent(
                    event_type=EVENT_WRITING_SUBMITTED,
                    title_key="journey_event_writing_submitted",
                    description_key="journey_event_writing_submitted_desc",
                    description_params={},
                    source_record_type="essay",
                    source_record_id=str(essay_id),
                    learner_id=student_id,
                    task_id=task_id,
                    submission_id=essay_id,
                    occurred_at=submitted_at,
                    limitations=["A submission is a system record; it does not imply engagement quality."],
                    deduplication_key=f"{EVENT_WRITING_SUBMITTED}:essay:{essay_id}",
                    research_detail={"draft_stage": essay.get("draft_stage"), "genre": essay.get("genre")},
                ))

            run = analyses.get(essay_id)
            if run is not None:
                events.append(JourneyEvent(
                    event_type=EVENT_ANALYSIS_COMPLETED,
                    title_key="journey_event_analysis_completed",
                    description_key="journey_event_analysis_completed_desc",
                    description_params={"submission": essay_id},
                    source_record_type="analysis_run",
                    source_record_id=str(run.get("analysis_run_id") or ""),
                    learner_id=student_id,
                    task_id=task_id,
                    submission_id=essay_id,
                    occurred_at=_normalize_timestamp(run.get("created_at")),
                    limitations=["Analysis is descriptive and not a proficiency assessment."],
                    deduplication_key=f"{EVENT_ANALYSIS_COMPLETED}:analysis_run:{run.get('analysis_run_id')}",
                    research_detail={
                        "analyzer_id": run.get("analyzer_id"),
                        "analyzer_version": run.get("analyzer_version"),
                        "configuration_version": run.get("configuration_version"),
                    },
                ))
            else:
                events.append(JourneyEvent(
                    event_type=EVENT_INSUFFICIENT_EVIDENCE,
                    title_key="journey_event_insufficient_evidence",
                    description_key="journey_event_insufficient_evidence_desc",
                    description_params={"submission": essay_id},
                    source_record_type="essay",
                    source_record_id=str(essay_id),
                    learner_id=student_id,
                    task_id=task_id,
                    submission_id=essay_id,
                    occurred_at=submitted_at,
                    evidence_status=DERIVED_STATE,
                    limitations=["No analysis record exists; no learning-process claim is possible for this submission."],
                    deduplication_key=f"{EVENT_INSUFFICIENT_EVIDENCE}:essay:{essay_id}",
                ))

            feedback = feedbacks.get(essay_id)
            if feedback is not None:
                fb_created = _normalize_timestamp(feedback.get("created_at"))
                events.append(JourneyEvent(
                    event_type=EVENT_FEEDBACK_AVAILABLE,
                    title_key="journey_event_feedback_available",
                    description_key="journey_event_feedback_available_desc",
                    description_params={"submission": essay_id},
                    source_record_type="feedback_record",
                    source_record_id=str(feedback.get("feedback_id") or ""),
                    learner_id=student_id,
                    task_id=task_id,
                    submission_id=essay_id,
                    occurred_at=fb_created,
                    limitations=["Feedback uses prototype heuristics and is not educationally validated."],
                    deduplication_key=f"{EVENT_FEEDBACK_AVAILABLE}:feedback_record:{feedback.get('feedback_id')}",
                    research_detail={"provider_name": feedback.get("provider_name"), "success_status": feedback.get("success_status")},
                ))
                priority_count = _fb_priority_count(feedback)
                if priority_count > 0:
                    events.append(JourneyEvent(
                        event_type=EVENT_FEEDBACK_PRIORITY_AVAILABLE,
                        title_key="journey_event_feedback_priority_available",
                        description_key="journey_event_feedback_priority_available_desc",
                        description_params={"submission": essay_id, "count": priority_count},
                        source_record_type="feedback_record",
                        source_record_id=str(feedback.get("feedback_id") or ""),
                        learner_id=student_id,
                        task_id=task_id,
                        submission_id=essay_id,
                        occurred_at=fb_created,
                        limitations=["A selected priority is an evidence-supported review target, not a diagnosis of ability."],
                        deduplication_key=f"{EVENT_FEEDBACK_PRIORITY_AVAILABLE}:feedback_record:{feedback.get('feedback_id')}",
                        research_detail={"priority_count": priority_count},
                    ))
                else:
                    events.append(JourneyEvent(
                        event_type=EVENT_FEEDBACK_WITHOUT_PRIORITY,
                        title_key="journey_event_feedback_without_priority",
                        description_key="journey_event_feedback_without_priority_desc",
                        description_params={"submission": essay_id},
                        source_record_type="feedback_record",
                        source_record_id=str(feedback.get("feedback_id") or ""),
                        learner_id=student_id,
                        task_id=task_id,
                        submission_id=essay_id,
                        occurred_at=fb_created,
                        evidence_status=DERIVED_STATE,
                        limitations=["No eligible priority passed the conservative Diagnostic Gate for this submission. Not every submission will generate practice."],
                        deduplication_key=f"{EVENT_FEEDBACK_WITHOUT_PRIORITY}:feedback_record:{feedback.get('feedback_id')}",
                    ))

        for target in targets:
            events.append(JourneyEvent(
                event_type=EVENT_PRACTICE_AVAILABLE,
                title_key="journey_event_practice_available",
                description_key="journey_event_practice_available_desc",
                description_params={"target": target.get("target_code") or ""},
                source_record_type="practice_target",
                source_record_id=str(target.get("practice_target_id") or ""),
                learner_id=student_id,
                task_id=str(target.get("source_submission_id")) if target.get("source_submission_id") else None,
                submission_id=target.get("source_submission_id"),
                occurred_at=_normalize_timestamp(target.get("created_at")),
                limitations=["Practice availability is not evidence of completed practice."],
                deduplication_key=f"{EVENT_PRACTICE_AVAILABLE}:practice_target:{target.get('practice_target_id')}",
                research_detail={"target_code": target.get("target_code"), "status": target.get("status")},
            ))

        for attempt in attempts:
            events.append(JourneyEvent(
                event_type=EVENT_EXERCISE_ATTEMPTED,
                title_key="journey_event_exercise_attempted",
                description_key="journey_event_exercise_attempted_desc",
                description_params={},
                source_record_type="exercise_attempt",
                source_record_id=str(attempt.get("attempt_id") or ""),
                learner_id=student_id,
                task_id=attempt.get("exercise_id"),
                occurred_at=_normalize_timestamp(attempt.get("created_at")),
                limitations=["An attempt record exists; it does not demonstrate mastery."],
                deduplication_key=f"{EVENT_EXERCISE_ATTEMPTED}:exercise_attempt:{attempt.get('attempt_id')}",
                research_detail={"attempt_number": attempt.get("attempt_number"), "status": attempt.get("status")},
            ))

        for evaluation in evaluations:
            events.append(JourneyEvent(
                event_type=EVENT_PRACTICE_EVALUATION_RECORDED,
                title_key="journey_event_practice_evaluation_recorded",
                description_key="journey_event_practice_evaluation_recorded_desc",
                description_params={},
                source_record_type="practice_evaluation",
                source_record_id=str(evaluation.get("evaluation_id") or ""),
                learner_id=student_id,
                task_id=evaluation.get("practice_target_id"),
                occurred_at=_normalize_timestamp(evaluation.get("created_at")),
                limitations=["Evaluation is observable evidence only; it does not prove learning."],
                deduplication_key=f"{EVENT_PRACTICE_EVALUATION_RECORDED}:practice_evaluation:{evaluation.get('evaluation_id')}",
                research_detail={
                    "completion_status": evaluation.get("completion_status"),
                    "target_action_status": evaluation.get("target_action_status"),
                },
            ))

        for response in responses:
            events.append(JourneyEvent(
                event_type=EVENT_WITHIN_TASK_RESPONSE_OBSERVED,
                title_key="journey_event_within_task_response_observed",
                description_key="journey_event_within_task_response_observed_desc",
                description_params={"status": response.get("observed_status") or ""},
                source_record_type="within_task_response_candidate",
                source_record_id=str(response.get("response_id") or ""),
                learner_id=student_id,
                task_id=response.get("revision_group_id"),
                submission_id=response.get("later_submission_id"),
                occurred_at=_normalize_timestamp(response.get("created_at")),
                limitations=["A revision response is a candidate observation, not proof that feedback caused the change."],
                deduplication_key=f"{EVENT_WITHIN_TASK_RESPONSE_OBSERVED}:within_task_response_candidate:{response.get('response_id')}",
                research_detail={
                    "observed_status": response.get("observed_status"),
                    "target_code": response.get("target_code"),
                    "comparison_version": response.get("comparison_version"),
                },
            ))

        for transfer in transfers:
            events.append(JourneyEvent(
                event_type=EVENT_LATER_TASK_EVIDENCE,
                title_key="journey_event_later_task_evidence",
                description_key="journey_event_later_task_evidence_desc",
                description_params={"status": transfer.get("observed_status") or ""},
                source_record_type="transfer_evidence_candidate",
                source_record_id=str(transfer.get("transfer_evidence_id") or ""),
                learner_id=student_id,
                task_id=str(transfer.get("later_submission_id")) if transfer.get("later_submission_id") else None,
                submission_id=transfer.get("later_submission_id"),
                occurred_at=_normalize_timestamp(transfer.get("created_at")),
                limitations=["One later observation is not proof of stable transfer; it does not establish that practice caused the later pattern."],
                deduplication_key=f"{EVENT_LATER_TASK_EVIDENCE}:transfer_evidence_candidate:{transfer.get('transfer_evidence_id')}",
                research_detail={
                    "observed_status": transfer.get("observed_status"),
                    "task_comparability": transfer.get("task_comparability"),
                    "target_code": transfer.get("target_code"),
                },
            ))

        # Sort chronologically; stable secondary sort by journey stage.
        # Essay-anchored events (analysis/feedback) sort against the essay's
        # submitted time because some source timestamps are second-truncated.
        essay_submitted_at = {
            int(essay.get("essay_id") or 0): _normalize_timestamp(essay.get("submitted_at"))
            for essay in essays
        }
        events.sort(key=lambda e: (
            essay_submitted_at.get(e.submission_id, e.occurred_at),
            EVENT_STAGE_ORDER.get(e.event_type, 50),
            e.source_record_id,
            e.event_type,
        ))
        # Deduplicate by key (defensive; derivation is deterministic).
        seen: set[str] = set()
        unique: list[JourneyEvent] = []
        for event in events:
            if event.deduplication_key in seen:
                continue
            seen.add(event.deduplication_key)
            unique.append(event)

        counts = {
            "submissions": len(essays),
            "analysis_runs": len(analyses),
            "feedback_records": len(feedbacks),
            "selected_priorities": sum(
                1 for fb in feedbacks.values() if _fb_priority_count(fb) > 0
            ),
            "practice_targets": len(targets),
            "exercise_attempts": len(attempts),
            "practice_evaluations": len(evaluations),
            "within_task_responses": len(responses),
            "transfer_evidence_candidates": len(transfers),
        }

        state, derived_states = self._classify_state(
            student_id, essays, analyses, feedbacks, targets, attempts, evaluations, responses, transfers,
        )
        return {
            "student_id": student_id,
            "learner_found": True,
            "counts": counts,
            "events": [e.model_dump(mode="json") for e in unique],
            "derived_states": derived_states,
            "state": state,
        }

    @staticmethod
    def _classify_state(
        student_id: str,
        essays: list[dict],
        analyses: dict[int, dict],
        feedbacks: dict[int, dict],
        targets: list[dict],
        attempts: list[dict],
        evaluations: list[dict],
        responses: list[dict],
        transfers: list[dict],
    ) -> tuple[str, list[dict[str, Any]]]:
        derived: list[dict[str, Any]] = []
        if not essays:
            return "no_submissions", derived
        missing_analysis = [int(e["essay_id"]) for e in essays if int(e["essay_id"]) not in analyses]
        if missing_analysis:
            derived.append({
                "key": "submission_without_analysis",
                "submission_ids": missing_analysis,
                "message_key": "journey_state_submission_without_analysis",
            })
            return "submission_without_analysis", derived
        selected_priorities = sum(1 for fb in feedbacks.values() if _fb_priority_count(fb) > 0)
        no_priority = [
            int(e["essay_id"]) for e in essays
            if int(e["essay_id"]) in feedbacks and _fb_priority_count(feedbacks[int(e["essay_id"])]) == 0
        ]
        if feedbacks and selected_priorities == 0:
            derived.append({
                "key": "analysis_without_priority",
                "submission_ids": no_priority,
                "message_key": "journey_state_analysis_without_priority",
            })
            return "analysis_without_priority", derived
        if no_priority:
            derived.append({
                "key": "analysis_without_priority",
                "submission_ids": no_priority,
                "message_key": "journey_state_analysis_without_priority",
            })
        if not targets:
            derived.append({"key": "feedback_no_practice_target", "message_key": "journey_state_feedback_no_practice_target"})
            return "feedback_no_practice_target", derived
        if not attempts:
            derived.append({"key": "target_no_attempt", "message_key": "journey_state_target_no_attempt"})
            return "target_no_attempt", derived
        if not evaluations:
            derived.append({"key": "attempt_no_evaluation", "message_key": "journey_state_attempt_no_evaluation"})
            return "attempt_no_evaluation", derived
        if not responses:
            derived.append({"key": "revision_no_response", "message_key": "journey_state_revision_no_response"})
            return "revision_no_response", derived
        if not transfers:
            derived.append({"key": "later_task_evidence_none", "message_key": "journey_state_later_task_evidence_none"})
        return "journey_events", derived
