"""WU2 focused tests: practice-history and authentic-application projections.

Covers the two clearly separate learner-owned Journey projections:

- ``get_practice_history`` lists persisted Practice activity/evidence records
  (practice targets, exercise attempts, practice evaluations) and, when a
  CORE-shaped review-event reader is injected, durable ReviewEvent rows with
  the three rating channels preserved separately. The section is activity
  only; it never claims mastery/proficiency/ability/learning gain and never
  implies authentic transfer.
- ``get_authentic_application`` lists later writing/submission observations
  and the existing within-task / transfer candidate observations with
  source/later submission ids, observed status, comparability, provenance,
  and limitations. Non-comparable and insufficient observations stay
  explicitly non-comparable/insufficient; practice records never merge into
  this section.

Compatibility: ``get_journey()`` output and the pinned port-call surface are
unchanged (exact-output guard and exact call-set guard below).

All tests use deterministic stub readers or an isolated SQLite database with
the local provider only; no live provider call.
"""

from __future__ import annotations

import json

import pytest

from app.database.repository import Database
from app.journey.service import JourneyService


# ---------------------------------------------------------------------------
# Deterministic fixture records (mirror the stored JSON shapes)
# ---------------------------------------------------------------------------

LEARNER = "L-HIST"

TARGET = {
    "practice_target_id": "PT000001",
    "student_id": LEARNER,
    "source_submission_id": 1,
    "source_analysis_run_id": "AR000001",
    "source_diagnosis_id": "D-001",
    "source_priority_id": "PRIO-FB000001-0",
    "target_code": "lexical_repetition_local",
    "target_label": "Reduce lexical repetition",
    "target_scope": "within_task",
    "diagnostic_gate_status": "selected",
    "diagnostic_version": "diagnostic-v0.6.1",
    "configuration_version": "config-v0.9.0",
    "status": "completed",
    "created_at": "2026-08-01T10:03:00+00:00",
    "updated_at": "2026-08-01T10:06:00+00:00",
}

ATTEMPT = {
    "attempt_id": "EA000001",
    "exercise_id": "EX000001",
    "student_id": LEARNER,
    "attempt_number": 1,
    "response_text": "A valid response.",
    "status": "submitted",
    "timing_source": "server_timestamp",
    "hint_count": 0,
    "created_at": "2026-08-01T10:04:00+00:00",
}

EVALUATION = {
    "evaluation_id": "PE000001",
    "attempt_id": "EA000001",
    "practice_target_id": "PT000001",
    "evaluation_method": "rule_based",
    "completion_status": "completed",
    "target_action_status": "candidate_detected",
    "evidence": ["E-001"],
    "confidence": "medium",
    "evaluator_version": "practice-evaluator-v0.9.0",
    "created_at": "2026-08-01T10:05:00+00:00",
}

REVIEW_EVENT = {
    "review_event_id": "RE000001",
    "student_id": LEARNER,
    "learning_item_id": "LI000001",
    "practice_activity_id": "PA000001",
    "reviewed_at": "2026-08-01T10:06:00+00:00",
    "system_provisional_rating": "good",
    "learner_self_rating": "easy",
    "final_scheduler_rating": "good",
    "rating_rule_version": "rating-rule-v0.9.0",
    "scheduler_implementation": "py-fsrs",
    "scheduler_version": "6.3.2",
    "scheduler_parameters": {"request_retention": 0.9},
    "state_before": {"state": "learning", "step": 0},
    "state_after": {"state": "review", "step": 0},
    "scheduling_result": {
        "next_due": "2026-08-08T10:06:00+00:00",
        "note": "FSRS stability/difficulty/due are memory scheduling state only.",
    },
    "authentic_evidence_status": "insufficient",
    "provenance": {"source": "bridge-v0.1"},
    "no_transfer_implication": (
        "Practice success does not imply authentic transfer; authentic "
        "writing evidence is tracked separately and remains distinct from "
        "practice evidence."
    ),
    "limitations": ["Review records are durable observations."],
    "recorded_at": "2026-08-01T10:06:01+00:00",
}

AUTH_ORIGINAL = {
    "essay_id": 1,
    "student_id": "L-AUTH",
    "submitted_at": "2026-08-01T10:00:00+00:00",
    "revision_of_submission_id": None,
    "revision_group_id": None,
    "draft_stage": "first draft",
    "genre": "argumentative essay",
    "revision_sequence": None,
}

AUTH_REVISION = {
    "essay_id": 2,
    "student_id": "L-AUTH",
    "submitted_at": "2026-08-02T10:00:00+00:00",
    "revision_of_submission_id": 1,
    "revision_group_id": "RG000001",
    "draft_stage": "revised draft",
    "genre": "argumentative essay",
    "revision_sequence": 1,
}

AUTH_RESPONSE = {
    "response_id": "WTR000001",
    "student_id": "L-AUTH",
    "practice_target_id": "PT000001",
    "source_submission_id": 1,
    "later_submission_id": 2,
    "revision_group_id": "RG000001",
    "target_code": "lexical_repetition_local",
    "observed_status": "target_addressed",
    "comparison_version": "revision-comparison-v0.7.1",
    "evidence_ids": ["E-001"],
    "confidence": "limited",
    "limitations": ["A revision response is a candidate observation."],
    "created_at": "2026-08-02T10:05:00+00:00",
}

AUTH_TRANSFER_COMPARABLE = {
    "transfer_evidence_id": "TE000001",
    "student_id": "L-AUTH",
    "practice_target_id": "PT000001",
    "source_submission_id": 1,
    "later_submission_id": 3,
    "task_comparability": "comparable",
    "target_code": "lexical_repetition_local",
    "observed_status": "recurrence_signal",
    "history_evidence_ids": ["WTR000001"],
    "confidence": "limited",
    "limitations": ["One later observation is not proof of stable transfer."],
    "created_at": "2026-08-05T10:00:00+00:00",
}

AUTH_TRANSFER_NOT_COMPARABLE = {
    "transfer_evidence_id": "TE000002",
    "student_id": "L-AUTH",
    "practice_target_id": "PT000001",
    "source_submission_id": 1,
    "later_submission_id": 4,
    "task_comparability": "not_comparable",
    "target_code": "lexical_repetition_local",
    "observed_status": "not_comparable",
    "history_evidence_ids": [],
    "confidence": "limited",
    "limitations": ["Task settings differ; the observation is not comparable."],
    "created_at": "2026-08-06T10:00:00+00:00",
}

AUTH_TRANSFER_INSUFFICIENT = {
    "transfer_evidence_id": "TE000003",
    "student_id": "L-AUTH",
    "practice_target_id": "PT000001",
    "source_submission_id": 1,
    "later_submission_id": 5,
    "task_comparability": "comparable",
    "target_code": "lexical_repetition_local",
    "observed_status": "insufficient_evidence",
    "history_evidence_ids": [],
    "confidence": "limited",
    "limitations": ["Later evidence is insufficient for an observation."],
    "created_at": "2026-08-07T10:00:00+00:00",
}


# ---------------------------------------------------------------------------
# Stub readers (deterministic, call-tracking)
# ---------------------------------------------------------------------------


class StubStudentReader:
    def __init__(self, learner):
        self.learner = learner
        self.calls: list[str] = []

    def get_student(self, student_id: str):
        self.calls.append("get_student")
        return self.learner


class StubProjectionReader:
    """Faithful fake of the pinned nine-method Journey projection port,
    optionally extended with a CORE-shaped review-event read."""

    def __init__(self, **lists):
        self.lists = lists
        self.calls: list[str] = []

    def list_essays_by_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_essays_by_student")
        return list(self.lists.get("essays", []))

    def list_analysis_runs_for_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_analysis_runs_for_student")
        return list(self.lists.get("analyses", []))

    def list_feedback_records_for_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_feedback_records_for_student")
        return list(self.lists.get("feedbacks", []))

    def list_practice_targets(self, student_id: str) -> list[dict]:
        self.calls.append("list_practice_targets")
        return list(self.lists.get("targets", []))

    def list_exercise_instances(self, practice_target_id=None, student_id=None) -> list[dict]:
        self.calls.append("list_exercise_instances")
        return list(self.lists.get("exercises", []))

    def list_exercise_attempts_by_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_exercise_attempts_by_student")
        return list(self.lists.get("attempts", []))

    def list_practice_evaluations_by_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_practice_evaluations_by_student")
        return list(self.lists.get("evaluations", []))

    def list_within_task_responses(self, student_id: str) -> list[dict]:
        self.calls.append("list_within_task_responses")
        return list(self.lists.get("responses", []))

    def list_transfer_evidence_candidates(self, student_id: str) -> list[dict]:
        self.calls.append("list_transfer_evidence_candidates")
        return list(self.lists.get("transfers", []))


class StubProjectionReaderWithReviews(StubProjectionReader):
    """Stub projection reader that also exposes the optional CORE-shaped
    review-event read the JourneyService consumes structurally."""

    def list_review_events_by_student(self, student_id: str) -> list[dict]:
        self.calls.append("list_review_events_by_student")
        return list(self.lists.get("review_events", []))


def _practice_lists() -> dict:
    return {
        "targets": [TARGET],
        "attempts": [ATTEMPT],
        "evaluations": [EVALUATION],
    }


def _authentic_lists() -> dict:
    return {
        "essays": [AUTH_ORIGINAL, AUTH_REVISION],
        "responses": [AUTH_RESPONSE],
        "transfers": [
            AUTH_TRANSFER_COMPARABLE,
            AUTH_TRANSFER_NOT_COMPARABLE,
            AUTH_TRANSFER_INSUFFICIENT,
        ],
    }


FORBIDDEN_KEYS = ("mastery", "proficiency", "outcome", "score")


def _assert_activity_only(payload: dict) -> None:
    """No outcome/proficiency claim outside the fixed denial limitations."""
    text = json.dumps(payload)
    for record in payload["records"]:
        for key, value in record.items():
            if key == "limitations":
                assert any(
                    ("does not" in lim or "do not" in lim or " is not " in lim)
                    for lim in value
                ), record["record_id"]
            elif key == "rating_channels" and value is None:
                continue
            else:
                assert key not in FORBIDDEN_KEYS
                if isinstance(value, str):
                    assert not any(
                        token in value for token in ("mastery", "proficiency")
                    ), (record["record_id"], key, value)
    assert "learning gain" not in text or (
        "does not" in text or "do not" in text)
    assert "causal" not in text or "not" in text


def _assert_observation_only(payload: dict) -> None:
    for observation in payload["observations"]:
        for key, value in observation.items():
            if key == "limitations":
                assert any(
                    "does not" in lim
                    for lim in value
                ), observation["observation_id"]
            else:
                assert key not in FORBIDDEN_KEYS
                if isinstance(value, str):
                    assert not any(
                        token in value for token in ("mastery", "proficiency")
                    ), (observation["observation_id"], key, value)


class TestPracticeHistoryProjection:
    """Practice history is a typed activity-only section with stable IDs,
    timestamps, provenance, and honest rating-channel visibility."""

    def test_practice_records_project_as_activity_only_evidence(self):
        student = StubStudentReader({"student_id": LEARNER})
        projections = StubProjectionReader(**_practice_lists())
        service = JourneyService(student, projections)

        result = service.get_practice_history(LEARNER)

        assert result["section"] == "practice_history"
        assert result["learner_id"] == LEARNER
        assert result["available"] is True
        assert result["status"] == "available"
        assert result["rating_channel_visibility"] == "unavailable"
        assert result["counts"] == {
            "practice_targets": 1,
            "exercise_attempts": 1,
            "practice_evaluations": 1,
            "review_events": 0,
        }
        assert [r["record_id"] for r in result["records"]] == [
            "PT000001", "EA000001", "PE000001",
        ]
        assert all(r["record_kind"] == "practice_activity" for r in result["records"])
        assert all(r["evidence_kind"] == "practice" for r in result["records"])
        assert all(r["rating_channels"] is None for r in result["records"])
        assert all(r["limitations"] for r in result["records"])
        _assert_activity_only(result)

    def test_stable_ordering_and_provenance_versions(self):
        student = StubStudentReader({"student_id": LEARNER})
        projections = StubProjectionReader(**_practice_lists())
        result = JourneyService(student, projections).get_practice_history(LEARNER)

        first = JourneyService(student, projections).get_practice_history(LEARNER)
        assert first == result
        by_id = {r["record_id"]: r for r in result["records"]}
        target = by_id["PT000001"]
        assert target["activity_type"] == "practice_target"
        assert target["occurred_at"] == "2026-08-01T10:03:00.000000+00:00"
        assert target["status"] == "completed"
        assert target["provenance"]["diagnostic_version"] == "diagnostic-v0.6.1"
        assert target["provenance"]["configuration_version"] == "config-v0.9.0"
        assert target["provenance"]["source_priority_id"] == "PRIO-FB000001-0"
        evaluation = by_id["PE000001"]
        assert evaluation["activity_type"] == "practice_evaluation"
        assert evaluation["provenance"]["evaluator_version"] == "practice-evaluator-v0.9.0"
        assert evaluation["provenance"]["completion_status"] == "completed"
        attempt = by_id["EA000001"]
        assert attempt["provenance"]["attempt_number"] == 1
        assert attempt["provenance"]["exercise_id"] == "EX000001"

    def test_insufficient_history_fails_closed_descriptively(self):
        student = StubStudentReader({"student_id": LEARNER})
        projections = StubProjectionReader()
        result = JourneyService(student, projections).get_practice_history(LEARNER)

        assert result["available"] is False
        assert result["status"] == "insufficient_history"
        assert result["records"] == []
        assert result["counts"] == {
            "practice_targets": 0,
            "exercise_attempts": 0,
            "practice_evaluations": 0,
            "review_events": 0,
        }
        assert any("insufficient" in lim for lim in result["limitations"])
        assert any("no practice" in lim.lower() for lim in result["limitations"])

    def test_review_events_preserve_three_rating_channels_separately(self):
        student = StubStudentReader({"student_id": LEARNER})
        projections = StubProjectionReaderWithReviews(
            review_events=[REVIEW_EVENT], **_practice_lists())
        result = JourneyService(student, projections).get_practice_history(LEARNER)

        assert result["rating_channel_visibility"] == "available"
        assert result["counts"]["review_events"] == 1
        review = next(
            r for r in result["records"] if r["record_kind"] == "review_event")
        assert review["record_id"] == "RE000001"
        assert review["activity_type"] == "review_event"
        assert review["evidence_kind"] == "practice"
        assert review["authentic_evidence_status"] == "insufficient"
        # Channels are separate and verbatim; nothing is averaged or re-scored.
        assert review["rating_channels"] == {
            "system_provisional_rating": "good",
            "learner_self_rating": "easy",
            "final_scheduler_rating": "good",
        }
        provenance = review["provenance"]
        assert provenance["rating_rule_version"] == "rating-rule-v0.9.0"
        assert provenance["scheduler_implementation"] == "py-fsrs"
        assert provenance["scheduler_version"] == "6.3.2"
        assert provenance["scheduler_parameters"] == {"request_retention": 0.9}
        assert provenance["learning_item_id"] == "LI000001"
        assert provenance["practice_activity_id"] == "PA000001"
        assert any("memory scheduling state" in lim for lim in review["limitations"])
        assert any("does not imply" in lim for lim in review["limitations"])

    def test_review_events_are_read_through_the_optional_structural_port(self):
        student = StubStudentReader({"student_id": LEARNER})
        projections = StubProjectionReaderWithReviews(
            review_events=[REVIEW_EVENT])
        service = JourneyService(student, projections)

        service.get_practice_history(LEARNER)

        assert "list_review_events_by_student" in projections.calls

    def test_malformed_review_rows_fail_closed_without_fabrication(self):
        student = StubStudentReader({"student_id": LEARNER})
        no_id = dict(REVIEW_EVENT, review_event_id="")
        no_self_rating = dict(REVIEW_EVENT, learner_self_rating=None)
        projections = StubProjectionReaderWithReviews(
            review_events=[no_id, no_self_rating, "not-a-dict"])
        result = JourneyService(student, projections).get_practice_history(LEARNER)

        reviews = [
            r for r in result["records"] if r["record_kind"] == "review_event"]
        assert [r["record_id"] for r in reviews] == ["RE000001"]
        assert reviews[0]["rating_channels"]["learner_self_rating"] is None
        assert reviews[0]["rating_channels"]["system_provisional_rating"] == "good"
        assert reviews[0]["rating_channels"]["final_scheduler_rating"] == "good"
        assert any("unavailable" in lim for lim in reviews[0]["limitations"])

    def test_unknown_student_fails_closed_before_any_projection_read(self):
        student = StubStudentReader(None)
        projections = StubProjectionReader(**_practice_lists())
        service = JourneyService(student, projections)

        with pytest.raises(LookupError, match="Student not found."):
            service.get_practice_history("NOPE")
        assert student.calls == ["get_student"]
        assert projections.calls == []


class TestAuthenticApplicationProjection:
    """Authentic writing application observations stay a separate channel:
    later submissions plus within-task / transfer candidates with verbatim
    comparability and observed status."""

    def test_later_submissions_and_candidates_keep_source_and_later_ids(self):
        student = StubStudentReader({"student_id": "L-AUTH"})
        projections = StubProjectionReader(**_authentic_lists())
        result = JourneyService(student, projections).get_authentic_application("L-AUTH")

        assert result["section"] == "authentic_application"
        assert result["available"] is True
        assert result["status"] == "present"
        assert result["counts"] == {
            "later_submissions": 1,
            "within_task_responses": 1,
            "later_task_evidence": 3,
        }
        by_id = {o["observation_id"]: o for o in result["observations"]}
        later = by_id["2"]
        assert later["observation_kind"] == "later_submission"
        assert later["source_submission_id"] == 1
        assert later["later_submission_id"] == 2
        assert later["observed_status"] == "submitted"
        assert later["comparability"] == "within_task_revision"
        assert later["task_id"] == "RG000001"
        assert later["provenance"]["draft_stage"] == "revised draft"
        assert later["provenance"]["revision_sequence"] == 1
        within = by_id["WTR000001"]
        assert within["observation_kind"] == "within_task_response"
        assert within["source_submission_id"] == 1
        assert within["later_submission_id"] == 2
        assert within["observed_status"] == "target_addressed"
        assert within["comparability"] == "within_task"
        assert within["comparison_version"] == "revision-comparison-v0.7.1"
        assert within["provenance"]["evidence_ids"] == ["E-001"]
        transfer = by_id["TE000001"]
        assert transfer["observation_kind"] == "later_task_evidence"
        assert transfer["source_submission_id"] == 1
        assert transfer["later_submission_id"] == 3
        assert transfer["observed_status"] == "recurrence_signal"
        assert transfer["comparability"] == "comparable"
        assert transfer["provenance"]["history_evidence_ids"] == ["WTR000001"]
        assert transfer["provenance"]["confidence"] == "limited"
        _assert_observation_only(result)

    def test_non_comparable_and_insufficient_observations_stay_explicit(self):
        student = StubStudentReader({"student_id": "L-AUTH"})
        projections = StubProjectionReader(**_authentic_lists())
        result = JourneyService(student, projections).get_authentic_application("L-AUTH")

        by_id = {o["observation_id"]: o for o in result["observations"]}
        assert by_id["TE000002"]["comparability"] == "not_comparable"
        assert by_id["TE000002"]["observed_status"] == "not_comparable"
        assert by_id["TE000003"]["comparability"] == "comparable"
        assert by_id["TE000003"]["observed_status"] == "insufficient_evidence"
        assert any("not comparable" in lim.lower() for lim in by_id["TE000002"]["limitations"])
        assert any("insufficient" in lim.lower() for lim in by_id["TE000003"]["limitations"])

    def test_practice_records_never_merge_into_authentic_section(self):
        student = StubStudentReader({"student_id": "L-AUTH"})
        projections = StubProjectionReader(
            **_authentic_lists(), **_practice_lists())
        result = JourneyService(student, projections).get_authentic_application("L-AUTH")

        observation_ids = [o["observation_id"] for o in result["observations"]]
        assert "PT000001" not in observation_ids
        assert "EA000001" not in observation_ids
        assert "PE000001" not in observation_ids
        assert all(
            o["observation_kind"] in {
                "later_submission", "within_task_response", "later_task_evidence",
            }
            for o in result["observations"]
        )
        assert "practice_targets" not in result["counts"]
        assert any("separate" in lim or "distinct" in lim for lim in result["limitations"])

    def test_insufficient_authentic_evidence_fails_closed_descriptively(self):
        student = StubStudentReader({"student_id": "L-AUTH"})
        projections = StubProjectionReader(essays=[AUTH_ORIGINAL])
        result = JourneyService(student, projections).get_authentic_application("L-AUTH")

        assert result["available"] is False
        assert result["status"] == "insufficient"
        assert result["observations"] == []
        assert result["counts"] == {
            "later_submissions": 0,
            "within_task_responses": 0,
            "later_task_evidence": 0,
        }
        assert any("insufficient" in lim for lim in result["limitations"])

    def test_unknown_student_fails_closed_before_any_projection_read(self):
        student = StubStudentReader(None)
        projections = StubProjectionReader(**_authentic_lists())
        service = JourneyService(student, projections)

        with pytest.raises(LookupError, match="Student not found."):
            service.get_authentic_application("NOPE")
        assert student.calls == ["get_student"]
        assert projections.calls == []


class TestJourneyCompatibilityPreserved:
    """get_journey() output and the pinned port-call surface stay unchanged."""

    PINNED_EMPTY = {
        "student_id": "EMPTY",
        "learner_found": True,
        "counts": {
            "submissions": 0,
            "analysis_runs": 0,
            "feedback_records": 0,
            "selected_priorities": 0,
            "practice_targets": 0,
            "exercise_attempts": 0,
            "practice_evaluations": 0,
            "within_task_responses": 0,
            "transfer_evidence_candidates": 0,
        },
        "events": [],
        "derived_states": [],
        "state": "no_submissions",
        "cycles": [],
        "cycles_version": "journey-cycle-v0.9.7-c",
    }

    def test_empty_journey_output_byte_identical(self):
        student = StubStudentReader({"student_id": "EMPTY"})
        projections = StubProjectionReader()
        result = JourneyService(student, projections).get_journey("EMPTY")
        assert result == self.PINNED_EMPTY

    def test_populated_journey_output_unchanged(self):
        student = StubStudentReader({"student_id": "JSTUB"})
        projections = StubProjectionReader(
            essays=[{
                "essay_id": 1, "student_id": "JSTUB", "writing_prompt": "p",
                "genre": "argumentative essay", "draft_stage": "first draft",
                "timed": False, "tool_use": "none",
                "submitted_at": "2026-08-01T10:00:00+00:00",
                "revision_of_submission_id": None, "revision_group_id": None,
            }],
            analyses=[{
                "essay_id": 1, "analysis_run_id": "AR000001",
                "analyzer_id": "basic", "analyzer_version": "spacy-analyzer-v0.8.0",
                "configuration_version": "config-v0.9.0",
                "created_at": "2026-08-01T10:01:00+00:00",
            }],
            feedbacks=[{
                "essay_id": 1, "feedback_id": "FB000001",
                "provider_name": "local_demo", "success_status": "success",
                "created_at": "2026-08-01T10:02:00+00:00",
                "feedback_json": {"priority_feedback": [{"id": "P1"}]},
            }],
            targets=[{
                "practice_target_id": "PT000001", "source_submission_id": 1,
                "target_code": "lexical_repetition_local", "status": "pending",
                "created_at": "2026-08-01T10:03:00+00:00",
            }],
            exercises=[{
                "exercise_id": "EX000001", "practice_target_id": "PT000001",
                "student_id": "JSTUB", "exercise_type": "sentence_rewrite",
                "created_at": "2026-08-01T10:03:30+00:00",
            }],
            attempts=[{
                "attempt_id": "AT000001", "exercise_id": "EX000001",
                "created_at": "2026-08-01T10:04:00+00:00",
                "attempt_number": 1, "status": "submitted",
            }],
            evaluations=[{
                "evaluation_id": "PE000001", "practice_target_id": "PT000001",
                "created_at": "2026-08-01T10:05:00+00:00",
                "completion_status": "completed", "target_action_status": "addressed",
            }],
            responses=[{
                "response_id": "WTR000001", "observed_status": "major_rewrite",
                "revision_group_id": "RG000001", "later_submission_id": 2,
                "created_at": "2026-08-01T10:06:00+00:00",
                "comparison_version": "v0.9.0",
            }],
            transfers=[{
                "transfer_evidence_id": "TE000001", "observed_status": "addressed",
                "later_submission_id": 3, "created_at": "2026-08-01T10:07:00+00:00",
                "task_comparability": "comparable", "target_code": "lexical_repetition_local",
            }],
        )
        result = JourneyService(student, projections).get_journey("JSTUB")
        assert result["counts"] == {
            "submissions": 1, "analysis_runs": 1, "feedback_records": 1,
            "selected_priorities": 1, "practice_targets": 1,
            "exercise_attempts": 1, "practice_evaluations": 1,
            "within_task_responses": 1, "transfer_evidence_candidates": 1,
        }
        assert [e["event_type"] for e in result["events"]] == [
            "writing_submitted", "analysis_completed", "feedback_available",
            "feedback_priority_available", "practice_available",
            "exercise_attempted", "practice_evaluation_recorded",
            "within_task_response_observed", "later_task_evidence",
        ]
        assert result["state"] == "journey_events"

    def test_get_journey_calls_exactly_the_pinned_nine_port_methods(self):
        student = StubStudentReader({"student_id": "JSTUB"})
        projections = StubProjectionReader(
            essays=[dict(AUTH_ORIGINAL, student_id="JSTUB")],
            targets=[TARGET],
            attempts=[ATTEMPT],
            evaluations=[EVALUATION],
            responses=[AUTH_RESPONSE],
            transfers=[AUTH_TRANSFER_COMPARABLE],
        )
        JourneyService(student, projections).get_journey("JSTUB")
        assert set(projections.calls) == {
            "list_essays_by_student",
            "list_analysis_runs_for_student",
            "list_feedback_records_for_student",
            "list_practice_targets",
            "list_exercise_instances",
            "list_exercise_attempts_by_student",
            "list_practice_evaluations_by_student",
            "list_within_task_responses",
            "list_transfer_evidence_candidates",
        }

    def test_projection_methods_use_only_existing_learner_owned_ports(self):
        student = StubStudentReader({"student_id": LEARNER})
        projections = StubProjectionReaderWithReviews(
            **_practice_lists(), **_authentic_lists())
        service = JourneyService(student, projections)

        service.get_practice_history(LEARNER)
        assert set(projections.calls) == {
            "list_practice_targets",
            "list_exercise_attempts_by_student",
            "list_practice_evaluations_by_student",
            "list_review_events_by_student",
        }
        projections.calls.clear()
        service.get_authentic_application("L-AUTH")
        assert set(projections.calls) == {
            "list_essays_by_student",
            "list_within_task_responses",
            "list_transfer_evidence_candidates",
        }


class TestRealRepositoryConsumption:
    """The projections consume the real SQLite practice repository without
    new persistence or migration (isolated temporary database)."""

    def _database(self, tmp_path) -> Database:
        database = Database(tmp_path / "wu2_hist.db")
        database.initialize()
        with database.connect() as conn:
            conn.execute(
                "INSERT INTO students (student_id, created_at, is_synthetic) "
                "VALUES (?, ?, ?)",
                (LEARNER, "2026-08-01T09:00:00+00:00", 1),
            )
        return database

    def test_projections_read_real_repository_records_read_only(self, tmp_path):
        database = self._database(tmp_path)
        repo = database._practice_repository
        repo.save_practice_target(TARGET)
        repo.save_exercise_instance({
            "exercise_id": "EX000001", "practice_target_id": "PT000001",
            "student_id": LEARNER, "source_submission_id": 1,
            "exercise_type": "guided_sentence_rewrite",
            "instructions": "Rewrite the sentence.",
            "source_text": "People should recycle.",
        })
        repo.save_exercise_attempt(ATTEMPT)
        repo.save_practice_evaluation(EVALUATION)

        service = JourneyService(
            database._learner_repository, database._practice_repository)
        history = service.get_practice_history(LEARNER)

        assert history["status"] == "available"
        assert history["rating_channel_visibility"] == "unavailable"
        assert [r["record_id"] for r in history["records"]] == [
            "PT000001", "EA000001", "PE000001",
        ]
        authentic = service.get_authentic_application(LEARNER)
        assert authentic["status"] == "insufficient"
        assert authentic["observations"] == []

        # Reads are side-effect free and the Journey output is unchanged.
        before = {t: len(r) for t, r in [
            (t, service.get_journey(LEARNER)["events"]) for t in ("a", "b")
        ]}
        assert before["a"] == before["b"]
        assert history == service.get_practice_history(LEARNER)
        assert authentic == service.get_authentic_application(LEARNER)

    def test_real_repository_without_review_reader_reports_channels_unavailable(
            self, tmp_path):
        database = self._database(tmp_path)
        repo = database._practice_repository
        repo.save_practice_target(TARGET)
        service = JourneyService(
            database._learner_repository, database._practice_repository)
        result = service.get_practice_history(LEARNER)
        assert result["rating_channel_visibility"] == "unavailable"
        assert any("rating channels" in lim for lim in result["limitations"])
