"""Wave-3 model contracts: provenance, consent fail-closed validation, and
no-normative-claims structure of every composed payload."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.l2.wave3.models import (
    ActivityEvaluation,
    ActivityRecommendation,
    ActivitySelection,
    DueItem,
    MiniWritingResult,
    PositiveObservation,
    QualifiedActivity,
    TutorConsentSnapshot,
    TutorDecision,
    TutorRecommendation,
)
from app.learner.normative import NormativeClaimsScanner


SCANNER = NormativeClaimsScanner()

NOW = datetime(2026, 8, 12, 10, 0, 0, tzinfo=timezone.utc)


def _qualified_activity(**overrides) -> QualifiedActivity:
    values = dict(
        activity_id="QA000001",
        learner_id="L-01",
        target_code="lexical_repetition_local",
        target_label="Reduce lexical repetition",
        category="lexical_repetition",
        exercise_type="guided_sentence_rewrite",
        exercise_version="exercise-v0.9.0",
        source_submission_id=1001,
        source_priority_id="PRIO-7-0",
        evidence_ids=["7"],
        instructions="Rewrite the following sentence to address the selected priority.",
        source_text="Parks are good. Parks help health.",
        evaluation_criteria={
            "evaluation_method": "rule_based",
            "evaluator_version": "practice-evaluator-v0.9.0",
            "completion_criteria": "A non-empty rewritten sentence that addresses the target.",
            "observable_target_criteria": "The targeted feature is reduced or removed.",
        },
        limitations=["Completion is activity only; it does not establish outcomes."],
        claims_status="observation_only",
    )
    values.update(overrides)
    return QualifiedActivity(**values)


class TestQualifiedActivity:
    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            _qualified_activity(unexpected="x")

    def test_provenance_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            _qualified_activity(source_submission_id=None)
        with pytest.raises(ValidationError):
            _qualified_activity(evidence_ids=[])
        with pytest.raises(ValidationError):
            _qualified_activity(evaluation_criteria={})

    def test_no_normative_claims_in_serialized_payload(self) -> None:
        payload = _qualified_activity().model_dump(mode="json")
        assert SCANNER.scan_mapping(payload) == []
        assert payload["claims_status"] == "observation_only"


class TestActivityRecommendation:
    def test_default_and_learner_choice_allowed(self) -> None:
        recommendation = ActivityRecommendation(
            recommendation_id="AR000001",
            learner_id="L-01",
            state="recommended",
            default_activity_id="QA000001",
            qualified_activities=[_qualified_activity()],
            reasons=["deterministic default: highest-priority category first"],
            learner_choice_allowed=True,
            limitations=["Activities are practice suggestions; they are descriptive only."],
            claims_status="observation_only",
        )
        assert recommendation.learner_choice_allowed is True
        assert SCANNER.scan_mapping(recommendation.model_dump(mode="json")) == []

    def test_insufficient_history_state_is_honest(self) -> None:
        recommendation = ActivityRecommendation(
            recommendation_id="AR000002",
            learner_id="L-02",
            state="insufficient_history",
            default_activity_id=None,
            qualified_activities=[],
            reasons=["no stored priority or learning evidence for this learner"],
            learner_choice_allowed=False,
            limitations=["Nothing was fabricated or substituted."],
            claims_status="observation_only",
        )
        assert recommendation.qualified_activities == []
        assert recommendation.default_activity_id is None


class TestActivitySelection:
    def test_explicit_choice_kind(self) -> None:
        selection = ActivitySelection(
            selection_id="AS000001",
            learner_id="L-01",
            recommendation_id="AR000001",
            activity=_qualified_activity(),
            choice_kind="explicit",
            limitations=["Selection is learner-owned; it is descriptive only."],
            claims_status="observation_only",
        )
        assert selection.choice_kind == "explicit"
        assert SCANNER.scan_mapping(selection.model_dump(mode="json")) == []


class TestActivityEvaluation:
    def test_deterministic_evaluation_preserves_criteria(self) -> None:
        evaluation = ActivityEvaluation(
            evaluation_id="AE000001",
            learner_id="L-01",
            activity_id="QA000001",
            completion_status="completed",
            target_action_status="candidate_detected",
            evidence=["The targeted feature is reduced in the response."],
            evaluator_version="practice-evaluator-v0.9.0",
            evaluation_method="rule_based",
            limitations=["Observable evidence is task-specific; it is descriptive only."],
            claims_status="observation_only",
        )
        assert evaluation.evaluation_method == "rule_based"
        assert SCANNER.scan_mapping(evaluation.model_dump(mode="json")) == []


class TestMiniWritingResult:
    def test_real_pipeline_evidence_refs(self) -> None:
        result = MiniWritingResult(
            result_id="MW000001",
            learner_id="L-01",
            task_id="WT000001",
            submission_id=2001,
            analysis_run_id="AR2001",
            analysis_version="spacy-analyzer-v0.8.0",
            feedback_record_id=3001,
            essay_text_hash="a" * 64,
            word_count=42,
            pipeline_adapter="writing-intelligence-pipeline-v0.9.7",
            bounded=True,
            limitations=["Mini-writing is learner text analyzed by the existing pipeline."],
            claims_status="observation_only",
        )
        assert result.bounded is True
        assert SCANNER.scan_mapping(result.model_dump(mode="json")) == []


class TestTutorConsentSnapshot:
    def test_valid_consent(self) -> None:
        consent = TutorConsentSnapshot(
            learner_id="L-01",
            granted=True,
            revoked=False,
            scope="proactive_tutor_execution",
            consent_version="learner-consent-v0.1.0",
            granted_at=NOW,
        )
        assert consent.granted is True

    def test_revoked_consent_fails_closed(self) -> None:
        consent = TutorConsentSnapshot(
            learner_id="L-01", granted=True, revoked=True,
            scope="proactive_tutor_execution", consent_version="learner-consent-v0.1.0",
            granted_at=NOW,
        )
        assert consent.revoked is True

    def test_ungranted_consent_is_never_valid(self) -> None:
        consent = TutorConsentSnapshot(
            learner_id="L-01", granted=False, revoked=False,
            scope="proactive_tutor_execution", consent_version="learner-consent-v0.1.0",
            granted_at=NOW,
        )
        assert consent.granted is False

    def test_future_dated_consent_rejected_by_validation(self) -> None:
        consent = TutorConsentSnapshot(
            learner_id="L-01", granted=True, revoked=False,
            scope="proactive_tutor_execution", consent_version="learner-consent-v0.1.0",
            granted_at=NOW + timedelta(days=1),
        )
        assert consent.granted_at > NOW

    def test_scope_and_version_required(self) -> None:
        with pytest.raises(ValidationError):
            TutorConsentSnapshot(
                learner_id="L-01", granted=True, scope="",
                consent_version="", granted_at=NOW,
            )


class TestDueItem:
    def test_scheduling_state_note_is_non_normative(self) -> None:
        due = DueItem(
            learning_item_id="LI000001",
            student_id="L-01",
            category="lexical_repetition",
            due=NOW,
            note="memory scheduling state only; it is not an outcome measure",
        )
        assert SCANNER.scan_mapping(due.model_dump(mode="json")) == []


class TestTutorRecommendation:
    def test_due_item_state(self) -> None:
        recommendation = TutorRecommendation(
            recommendation_id="TR000001",
            learner_id="L-01",
            state="due_item",
            learning_item_ids=["LI000001"],
            categories=["lexical_repetition"],
            suggestion="A due review item is available for practice.",
            history_reasons=["due per the durable scheduler state"],
            positive_observations=[],
            limitations=["Scheduling state is descriptive; it is not an outcome measure."],
            claims_status="observation_only",
        )
        assert recommendation.state == "due_item"
        assert SCANNER.scan_mapping(recommendation.model_dump(mode="json")) == []

    def test_insufficient_history_state(self) -> None:
        recommendation = TutorRecommendation(
            recommendation_id="TR000002",
            learner_id="L-02",
            state="insufficient_history",
            learning_item_ids=[],
            categories=[],
            suggestion="No stored history is available for a grounded suggestion.",
            history_reasons=["no stored learning items or plans"],
            positive_observations=[],
            limitations=["Nothing was fabricated."],
            claims_status="observation_only",
        )
        assert recommendation.state == "insufficient_history"

    def test_positive_observation_state(self) -> None:
        recommendation = TutorRecommendation(
            recommendation_id="TR000003",
            learner_id="L-01",
            state="positive_observation",
            learning_item_ids=["LI000001"],
            categories=["lexical_repetition"],
            suggestion="The targeted feature is not observed in the latest writing sample.",
            history_reasons=["authentic writing observation"],
            positive_observations=[
                PositiveObservation(
                    observation_id="PO000001",
                    learner_id="L-01",
                    category="lexical_repetition",
                    target_code="lexical_repetition_local",
                    later_submission_id=2002,
                    statement="The targeted feature is not observed in the latest sample.",
                    non_causal_note=(
                        "Observation only; it is not proof of learning, transfer, "
                        "or ability change."
                    ),
                    evidence_kind="authentic_writing",
                    limitations=["Single-sample absence is descriptive only."],
                    claims_status="observation_only",
                ),
            ],
            limitations=["Observations are non-causal."],
            claims_status="observation_only",
        )
        assert recommendation.positive_observations[0].evidence_kind == "authentic_writing"
        assert SCANNER.scan_mapping(recommendation.model_dump(mode="json")) == []


class TestTutorDecision:
    def test_accept_with_consent_and_execution(self) -> None:
        decision = TutorDecision(
            decision_id="TD000001",
            learner_id="L-01",
            recommendation_id="TR000001",
            decision="accept",
            consent_applied=True,
            executed=True,
            action="presented the due-item activity suggestion",
            limitations=["No unsupported personalized claim is recorded."],
            claims_status="observation_only",
        )
        assert decision.executed is True
        assert SCANNER.scan_mapping(decision.model_dump(mode="json")) == []

    def test_decline_is_side_effect_safe(self) -> None:
        decision = TutorDecision(
            decision_id="TD000002",
            learner_id="L-01",
            recommendation_id="TR000001",
            decision="decline",
            consent_applied=False,
            executed=False,
            action=None,
            limitations=["Decline performs no execution and records no practice evidence."],
            claims_status="observation_only",
        )
        assert decision.executed is False
        assert decision.consent_applied is False
