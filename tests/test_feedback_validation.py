import pytest

from app.feedback.validation import FeedbackValidationError, FeedbackValidator
from app.llm import FeedbackContext, LocalDemoProvider
from app.models import HistoryEvidence, HistoryResult, StructuredFeedback
from app.prompts import PromptBuilder


def valid_feedback(context):
    bundle = PromptBuilder().build(context)
    return LocalDemoProvider().generate(bundle.messages, temperature=0.2)


def mutate(feedback, path, value):
    payload = feedback.model_dump()
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return StructuredFeedback.model_validate(payload)


def test_unknown_diagnosis_id_fails(feedback_context):
    feedback = mutate(valid_feedback(feedback_context), ["priority_feedback", 0, "diagnosis_id"], "D999")
    with pytest.raises(FeedbackValidationError, match="unknown diagnosis_id"):
        FeedbackValidator().validate(feedback, feedback_context)


def test_category_mismatch_fails(feedback_context):
    feedback = mutate(valid_feedback(feedback_context), ["priority_feedback", 0, "category"], "invented_category")
    with pytest.raises(FeedbackValidationError, match="category does not match"):
        FeedbackValidator().validate(feedback, feedback_context)


def test_fabricated_quote_fails(feedback_context):
    feedback = mutate(valid_feedback(feedback_context), ["priority_feedback", 0, "evidence_quote"], "This sentence was never written.")
    with pytest.raises(FeedbackValidationError, match="verbatim essay substring"):
        FeedbackValidator().validate(feedback, feedback_context)


def test_verbatim_quote_allows_only_whitespace_normalization(feedback_context):
    feedback = valid_feedback(feedback_context)
    quote = feedback.positive_finding.evidence_quote.replace(" ", "\n  ")
    feedback = mutate(feedback, ["positive_finding", "evidence_quote"], quote)
    FeedbackValidator().validate(feedback, feedback_context)


def test_unknown_history_evidence_id_fails(feedback_context):
    feedback = mutate(valid_feedback(feedback_context), ["longitudinal", "history_evidence_ids"], ["H999"])
    with pytest.raises(FeedbackValidationError, match="unknown history_evidence_id"):
        FeedbackValidator().validate(feedback, feedback_context)


@pytest.mark.parametrize("claim", [
    "The student has improved substantially.",
    "The student's writing shows clear improvement.",
    "Language ability has increased.",
    "The learner has made progress.",
    "学生的能力已经提升。",
    "学生的表现明显进步。",
])
def test_no_history_forbids_deterministic_development_claim(feedback_context, claim):
    feedback = valid_feedback(feedback_context)
    feedback = mutate(feedback, ["longitudinal", "comment"], claim)
    with pytest.raises(FeedbackValidationError, match="deterministic development claim"):
        FeedbackValidator().validate(feedback, feedback_context)


def test_no_history_allows_explicitly_uncertain_statement(feedback_context):
    feedback = valid_feedback(feedback_context)
    feedback = mutate(
        feedback, ["longitudinal", "comment"],
        "Evidence is insufficient; improvement or decline cannot be judged.",
    )
    FeedbackValidator().validate(feedback, feedback_context)


def test_valid_history_evidence_supports_longitudinal_comment(feedback_context):
    history = HistoryResult(
        comparability_status="comparable", comparable_submission_count=1,
        history_evidence=[HistoryEvidence(
            history_evidence_id="H001", evidence_type="metric_change",
            description="A descriptive metric changed.", supporting_submission_ids=["E000001", "E000002"],
            comparable_submission_count=1, confidence="low",
            limitation="Prototype heuristic evidence only.",
        )],
        summary="One evidence item is available.", limitations=["Prototype heuristic evidence only."],
        comparability_reasons=["All recorded task conditions match."],
    )
    context = FeedbackContext(
        feedback_context.submission, feedback_context.analysis, feedback_context.diagnosis, history
    )
    feedback = valid_feedback(context)
    assert feedback.longitudinal.history_evidence_ids == ["H001"]
    FeedbackValidator().validate(feedback, context)


def test_exercise_must_link_valid_diagnosis(feedback_context):
    feedback = mutate(valid_feedback(feedback_context), ["exercises", 0, "diagnosis_id"], "D999")
    with pytest.raises(FeedbackValidationError, match=r"exercises\[0\] has unknown diagnosis_id"):
        FeedbackValidator().validate(feedback, feedback_context)
