from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.analysis import SpacyAnalyzer
from app.analysis.metric_confidence import assess_metric_confidence
from app.calibration import DiagnosticCalibrationService, EvidenceRelevanceValidator
from app.config import load_settings
from app.configuration import ConfigurationPayload
from app.database import Database
from app.database.migrations import MIGRATIONS, upgrade
from app.diagnosis import NlpHeuristicDiagnoser
from app.feedback import FeedbackValidationError, FeedbackValidator
from app.feedback.exercises import ExerciseGenerator
from app.llm import FeedbackContext, LocalDemoProvider
from app.models import DiagnosisSignal, EssaySubmission, FeedbackItem, StructuredFeedback
from app.api.main import create_app
from app.services import build_submission_service
from app.prompts import PromptBuilder
from app.services.configuration import ConfigurationService
from app.analysis import default_metric_registry
from app.configuration import default_algorithm_registry, default_prompt_registry


FIXTURES = Path(__file__).parent / "fixtures" / "diagnostic_calibration"


def payload(name: str = "first_draft.json") -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def analyze(name: str = "first_draft.json"):
    item = payload(name)
    return SpacyAnalyzer().analyze(item["essay_text"], writing_prompt=item["writing_prompt"])


def local_stack(tmp_path):
    settings = replace(load_settings(), database_path=tmp_path / "calibration.db", llm_provider="local")
    repository = Database(settings.database_path); repository.initialize()
    return repository, build_submission_service(
        settings,
        system_repository=repository._system_repository,
        submission_repository=repository._submission_repository,
        analysis_repository=repository._analysis_repository,
        calibration_repository=repository._calf_repository,
        learner_repository=repository._learner_repository,
        configuration_repository=repository._configuration_repository,
        revision_repository=repository._revision_repository,
    )


def test_metric_confidence_structure_and_high_medium_insufficient():
    result = analyze()
    metrics = {item["metric_id"]: item for item in result.metric_results}
    assert metrics["type_token_ratio"]["confidence"] == "high"
    assert metrics["connective_count"]["confidence"] == "medium"
    short = SpacyAnalyzer(mattr_window=50).analyze("Short text.", writing_prompt="Write.")
    mattr = next(item for item in short.metric_results if item["metric_id"] == "mattr")
    assert mattr["confidence"] == "insufficient" and not mattr["eligible_for_diagnosis"]


def test_fallback_metric_confidence_is_low_and_not_longitudinal(tmp_path):
    repository, service = local_stack(tmp_path)
    service.analyzer.active_analyzer = "basic"
    result = service.analyzer.analyze("A short but complete fallback text.", writing_prompt="Write.")
    assert result.metric_results
    assert all(item["confidence"] in {"low", "insufficient"} for item in result.metric_results)
    assert all(item["confidence"] == "low" for item in result.metric_results if item["status"] == "available")
    assert not any(item["eligible_for_longitudinal_comparison"] for item in result.metric_results)


def test_ttr_is_directly_reproducible_and_matches_display_counts():
    result = analyze(); lexical = result.artifacts["lexical_features"]
    protocol = lexical["type_token_ratio_protocol"]
    assert result.metrics["word_count"] == protocol["token_count_used"]
    assert result.metrics["unique_word_count"] == protocol["type_count_used"]
    assert result.metrics["type_token_ratio"] == round(protocol["type_count_used"] / protocol["token_count_used"], 4)


def test_mattr_lexical_density_and_repetition_protocols_are_reproducible():
    result = analyze(); lexical = result.artifacts["lexical_features"]
    assert {"token_definition", "normalization", "window_size", "effective_windows", "minimum_text_length"} <= lexical["mattr_protocol"].keys()
    assert lexical["mattr_protocol"]["effective_windows"] == result.metrics["word_count"] - lexical["mattr_protocol"]["window_size"] + 1
    assert lexical["lexical_density_protocol"]["content_pos"] == ["ADJ", "ADV", "NOUN", "PROPN", "VERB"]
    assert lexical["repetition_density"] == round(
        lexical["repetition_density_numerator"] / lexical["repetition_density_denominator"], 4
    )


def test_new_metric_versions_and_parser_candidate_names_are_explicit():
    result = analyze(); metrics = {item["metric_id"]: item for item in result.metric_results}
    assert metrics["type_token_ratio"]["metric_version"] == "2.0.0"
    assert metrics["mattr"]["metric_version"] == "0.6.1"
    assert metrics["repeated_content_words"]["metric_version"] == "3.0.0"
    assert "subordinate_clause_candidates" not in metrics
    assert "coordination_candidates" not in metrics
    assert metrics["clause_like_dependency_candidates"]["measurement_metadata"]["confirmed_clause_count"] is False


def test_coordination_clause_and_finite_verb_counts_are_separate():
    result = analyze(); syntax = result.artifacts["syntactic_features"]
    assert len(syntax["coordination_candidates"]) == len(syntax["coordinator_tokens"]) + len(syntax["conjunct_dependencies"])
    assert len(syntax["coordinated_structure_candidates"]) <= len(syntax["conjunct_dependencies"])
    assert set(syntax["clause_like_dependency_candidates_by_type"]) == {"acl", "advcl", "ccomp", "csubj", "relcl", "xcomp"}
    assert all("counting_rule" in item and "is_auxiliary" in item for item in syntax["finite_verb_candidates"])


def test_first_draft_bias_is_distributed_monitored_not_selected(tmp_path):
    _, service = local_stack(tmp_path)
    result = service.submit(EssaySubmission.model_validate(payload()))
    lexical = result.analysis.artifacts["lexical_features"]
    bias = next(item for item in lexical["repeated_content_word_details"] if item["lemma"] == "bias")
    assert (bias["count"], bias["sentence_ids"], bias["local_cluster_detected"]) == (3, [2, 6, 11], False)
    assert bias["density"] < 0.025
    monitored = [item for item in result.diagnosis.monitored_signals if item.evidence_metadata.get("target_lemma") == "bias"]
    assert monitored and not any(item.evidence_metadata.get("target_lemma") == "bias" for item in result.diagnosis.improvement_priorities)


def test_prompt_keywords_and_necessary_task_terms_are_downweighted(tmp_path):
    _, service = local_stack(tmp_path)
    result = service.submit(EssaySubmission.model_validate(payload()))
    lexical = result.analysis.artifacts["lexical_features"]
    assert {"history", "lie"} <= set(lexical["prompt_keywords"])
    terms = {item["lemma"]: item for item in lexical["repeated_content_word_details"]}
    assert terms["history"]["diagnostic_weight"] == "low"
    assert not any(item.evidence_metadata.get("target_lemma") in {"history", "lie"} for item in result.diagnosis.improvement_priorities)


def test_cross_paragraph_necessary_term_candidate_is_monitored():
    text = (
        "Community programs can support local readers with carefully planned lessons and accessible books. "
        "Volunteers should document each lesson before changing the plan.\n\n"
        "A community may need stable meeting times and trained coordinators for each weekly session. "
        "Participants can report which activities are useful.\n\n"
        "The community also benefits when organizers publish evidence and invite public review. "
        "This process keeps the central term visible without assuming every repetition is replaceable."
    )
    submission = EssaySubmission(student_id="TERM", writing_prompt="How should volunteers plan literacy lessons?", essay_text=text)
    analysis = SpacyAnalyzer(local_repetition_window=2).analyze(text, writing_prompt=submission.writing_prompt)
    raw = NlpHeuristicDiagnoser().diagnose(analysis)
    calibrated = DiagnosticCalibrationService(ConfigurationPayload()).calibrate(submission, analysis, raw)
    term = next(item for item in calibrated.raw_signals if item.evidence_metadata.get("target_lemma") == "community")
    assert term.evidence_metadata["is_necessary_task_term_candidate"] is True
    assert any(item.evidence_metadata.get("target_lemma") == "community" for item in calibrated.monitored_signals)


def test_local_cluster_can_enter_priority(tmp_path):
    _, service = local_stack(tmp_path)
    item = EssaySubmission(
        student_id="LOCAL", writing_prompt="How can claims be clear?", genre="argumentative essay",
        draft_stage="first draft", timed=False, tool_use="none",
        essay_text=("Writers repeat vague claims, repeat vague claims, and repeat vague claims in one short passage. "
                    "Specific evidence can clarify a reason because readers can inspect the support. " * 5),
    )
    result = service.submit(item)
    assert any(signal.category == "lexical_repetition" for signal in result.diagnosis.improvement_priorities)


def test_ultimately_is_typed_and_multiple_functions_lower_connective_priority(tmp_path):
    _, service = local_stack(tmp_path)
    result = service.submit(EssaySubmission.model_validate(payload()))
    detected = result.analysis.artifacts["connective_features"]["detected_connectives"]
    ultimately = next(item for item in detected if item["normalized_form"] == "ultimately")
    assert ultimately["expression_class"] == "paragraph_organization_expression"
    assert not any(item.category == "connective_use" for item in result.diagnosis.improvement_priorities)


def test_connective_without_specific_location_is_not_priority():
    item = payload(); analysis = SpacyAnalyzer().analyze(
        "However, one claim is clear. Therefore, another claim follows. Ultimately, the argument ends.",
        writing_prompt=item["writing_prompt"],
    )
    raw = NlpHeuristicDiagnoser().diagnose(analysis)
    calibrated = DiagnosticCalibrationService(ConfigurationPayload()).calibrate(EssaySubmission.model_validate(item), analysis, raw)
    assert not any(signal.category == "connective_use" for signal in calibrated.selected_priorities)


def test_evidence_relevance_rejects_unrelated_existing_quote():
    analysis = analyze(); raw = NlpHeuristicDiagnoser().diagnose(analysis)
    signal = next(item for item in raw.raw_signals if item.category == "lexical_repetition" and item.evidence_metadata["target_lemma"] == "bias")
    assert EvidenceRelevanceValidator().validate_feedback_quote(
        signal, "Historians compare letters, laws, photographs, objects, and testimony to test claims against several kinds of evidence.", analysis
    ) == "irrelevant"


def test_revision_evidence_requires_alignment_or_metric_change_binding():
    analysis = analyze()
    unbound = DiagnosisSignal(
        diagnosis_id="D001", category="revision_uptake", evidence="A revision changed.",
        source_metrics=["revision_alignment"], interpretation="May merit review.", confidence="medium",
        limitation="Prototype.", rule_version="test", kind="improvement",
        evidence_quote_candidates=["A bias can shape which events a writer selects, but selection does not automatically make every account false."],
    )
    validator = EvidenceRelevanceValidator()
    assert validator.assess_signal(unbound, analysis)[0] == "insufficient_evidence"
    bound = unbound.model_copy(update={"evidence_metadata": {"supporting_alignment_ids": ["ALS001"]}})
    assert validator.assess_signal(bound, analysis)[0] == "verified"


def test_connective_evidence_requires_bound_location():
    analysis = analyze(); raw = NlpHeuristicDiagnoser().diagnose(analysis)
    signal = next(item for item in raw.raw_signals if item.category == "connective_use")
    assert signal.evidence_metadata["specific_location"] is True
    validator = EvidenceRelevanceValidator()
    assert validator.validate_feedback_quote(signal, signal.evidence_quote_candidates[0], analysis) == "verified"
    assert validator.validate_feedback_quote(signal, "Ultimately, history is not simply a lie; it is a disciplined argument that remains open to revision when stronger evidence appears.", analysis) == "irrelevant"


def test_descriptive_length_is_not_strength_and_zero_priority_is_allowed(tmp_path):
    _, service = local_stack(tmp_path)
    result = service.submit(EssaySubmission.model_validate(payload()))
    assert result.diagnosis.descriptive_signals
    assert all(item.category != "idea_development_space" for item in result.diagnosis.strengths)
    assert result.provider.feedback.priority_feedback == []
    assert result.provider.feedback.exercises == []


def test_exactly_285_detected_words_remain_descriptive_not_idea_quality():
    text = "Careful evidence matters. " * 95
    analysis = SpacyAnalyzer().analyze(text, writing_prompt="Why does evidence matter?")
    diagnosis = NlpHeuristicDiagnoser().diagnose(analysis)
    assert analysis.metrics["word_count"] == 285
    assert any("285" in item.evidence for item in diagnosis.descriptive_signals)
    assert not any(item.category == "idea_development_space" for item in diagnosis.strengths)


def test_local_demo_uses_selected_only_and_relevant_quotes(tmp_path):
    _, service = local_stack(tmp_path)
    item = EssaySubmission(
        student_id="DEMO", writing_prompt="How can claims be clear?", essay_text=(
            "Writers repeat vague claims, repeat vague claims, and repeat vague claims in one short passage. "
            "Specific evidence can clarify a reason because readers can inspect the support. " * 5
        ),
    )
    result = service.submit(item)
    selected_ids = {signal.diagnosis_id for signal in result.diagnosis.improvement_priorities}
    assert {feedback.diagnosis_id for feedback in result.provider.feedback.priority_feedback} <= selected_ids
    assert all(exercise.diagnosis_id in selected_ids for exercise in result.provider.feedback.exercises)
    assert all(exercise.source_type in {"student_source_sentence", "synthetic_practice_sentence"} for exercise in result.provider.feedback.exercises)


def test_priority_score_is_transparent_and_not_an_overall_score(tmp_path):
    _, service = local_stack(tmp_path)
    item = EssaySubmission(
        student_id="SCORE", writing_prompt="How can claims be clear?",
        essay_text=("Writers repeat vague claims, repeat vague claims, and repeat vague claims in one short passage. "
                    "Specific evidence can clarify a reason because readers can inspect the support. " * 5),
    )
    result = service.submit(item)
    selected = result.diagnosis.improvement_priorities[0]
    assert 0 <= selected.priority_score <= 1
    assert {"evidence_strength", "metric_confidence", "diagnosis_confidence", "actionability",
            "pedagogical_value", "history_relevance", "genre_context",
            "prompt_term_penalty", "low_confidence_penalty"} <= selected.score_components.keys()


def test_repeated_selected_category_contributes_history_relevance(tmp_path):
    _, service = local_stack(tmp_path)
    text = ("Writers repeat vague claims, repeat vague claims, and repeat vague claims in one short passage. "
            "Specific evidence can clarify a reason because readers can inspect the support. " * 5)
    common = dict(student_id="HIST", writing_prompt="How can claims be clear?", genre="argumentative essay", essay_text=text)
    first = service.submit(EssaySubmission(**common))
    assert first.diagnosis.improvement_priorities
    second = service.submit(EssaySubmission(**common))
    lexical = next(item for item in second.diagnostic_calibration.eligible_diagnoses if item.category == "lexical_repetition")
    assert lexical.score_components["history_relevance"] == 0.8


def test_low_confidence_priority_has_at_most_one_exercise():
    signal = DiagnosisSignal(
        diagnosis_id="D001", category="sentence_structure_candidate", evidence="Sentence candidate.",
        source_metrics=["average_sentence_length"], interpretation="May merit review.", confidence="low",
        limitation="Prototype.", rule_version="test", kind="improvement", selection_status="selected_priority",
        evidence_relevance_status="verified", evidence_quote_candidates=["Sentence candidate."],
    )
    assert len(ExerciseGenerator().generate([signal])) == 1
    assert ExerciseGenerator().generate([signal.model_copy(update={"selection_status": "monitored_signal"})]) == []
    assert ExerciseGenerator().generate([signal.model_copy(update={"evidence_relevance_status": "insufficient_evidence"})]) == []


def test_feedback_validator_cannot_restore_monitored_diagnosis(tmp_path):
    _, service = local_stack(tmp_path)
    result = service.submit(EssaySubmission.model_validate(payload()))
    context = FeedbackContext(
        EssaySubmission.model_validate(payload()), result.analysis, result.diagnosis, result.history,
        diagnostic_calibration=result.diagnostic_calibration.prompt_payload(),
    )
    base = result.provider.feedback.model_dump()
    base["priority_feedback"] = [{
        "diagnosis_id": "D000", "category": "lexical_repetition",
        "evidence_quote": "A bias can shape which events a writer selects, but selection does not automatically make every account false.",
        "explanation": "Invalid restoration.", "revision_guidance": "Invalid.",
    }]
    invalid = StructuredFeedback.model_validate(base)
    with pytest.raises(FeedbackValidationError):
        FeedbackValidator().validate(invalid, context)


def test_migration_7_and_append_only_calibration_repository(tmp_path):
    repository, service = local_stack(tmp_path)
    result = service.submit(EssaySubmission.model_validate(payload()))
    assert repository._system_repository.migration_version() == 13
    with repository.connect() as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(metric_results)")}
        count = connection.execute("SELECT COUNT(*) FROM diagnostic_calibrations WHERE essay_id=?", (result.essay_id,)).fetchone()[0]
    assert {"confidence", "measurement_metadata_json", "eligible_for_diagnosis"} <= columns
    assert count == 1 and repository._calf_repository.get_diagnostic_calibration(result.essay_id).calibration_id


def test_v06_database_upgrades_without_losing_historical_essay(tmp_path):
    path = tmp_path / "v06.db"
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    for version in range(1, 7):
        MIGRATIONS[version][1](connection)
        connection.execute(f"PRAGMA user_version={version}")
    connection.execute("INSERT INTO students(student_id,created_at,is_synthetic) VALUES ('LEGACY','2026-07-29T00:00:00+00:00',1)")
    connection.execute(
        "INSERT INTO essays(student_id,writing_prompt,genre,draft_stage,timed,tool_use,essay_text,submitted_at) VALUES (?,?,?,?,?,?,?,?)",
        ("LEGACY", "Legacy prompt", "argumentative essay", "first draft", 0, "none", "Preserved historical essay.", "2026-07-29T00:01:00+00:00"),
    )
    connection.commit()
    assert upgrade(connection) == 13
    assert connection.execute("SELECT essay_text FROM essays WHERE student_id='LEGACY'").fetchone()[0] == "Preserved historical essay."
    assert connection.execute("SELECT version FROM configuration_versions WHERE status='active'").fetchone()[0] == "config-v0.9.0"
    connection.close()


def test_configuration_v061_is_new_active_child_and_old_preserved(tmp_path):
    repository, _ = local_stack(tmp_path)
    active = repository._configuration_repository.get_active_configuration()
    assert active.version == "config-v0.9.0"
    assert repository._configuration_repository.get_configuration("config-v0.6.1") is not None
    assert active.payload.lexical_repetition_minimum_count == 4
    assert active.payload.active_prompt_version == "feedback-prompt-v0.7.1"


def test_direct_rollback_to_preserved_v06_configuration(tmp_path):
    repository, service = local_stack(tmp_path)
    configurations = ConfigurationService(repository._configuration_repository, service.analyzer.registry, default_metric_registry())
    rolled = configurations.rollback(repository._configuration_repository.get_active_configuration().configuration_id, reason="Human review rollback test.")
    assert rolled.version == "config-v0.8.2"
    assert repository._configuration_repository.get_configuration("config-v0.8.2").status == "active"
    assert repository._configuration_repository.get_configuration("config-v0.9.0").status == "inactive"


def test_api_exposes_research_audit_but_student_feedback_is_filtered(tmp_path):
    settings = replace(load_settings(), database_path=tmp_path / "api.db", llm_provider="local")
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/v1/submissions", json=payload())
        assert response.status_code == 201
        body = response.json(); essay_id = body["submission_id"]
        assert len(body["diagnosis"]["improvement_priorities"]) <= 2
        audit = client.get(f"/api/v1/submissions/{essay_id}/diagnostic-audit")
        assert audit.status_code == 200
        assert {"raw_signals", "monitored_signals", "selected_priorities", "suppressed_diagnostics"} <= audit.json().keys()


def test_prompt_contains_selected_calibration_not_suppressed_noise(tmp_path):
    _, service = local_stack(tmp_path)
    result = service.submit(EssaySubmission.model_validate(payload()))
    context = FeedbackContext(
        EssaySubmission.model_validate(payload()), result.analysis, result.diagnosis, result.history,
        diagnostic_calibration=result.diagnostic_calibration.prompt_payload(),
    )
    bundle = PromptBuilder().build(context)
    assert bundle.prompt_version == "feedback-prompt-v0.6.1"
    assert bundle.user_payload["diagnoses"] == [item.model_dump(mode="json") for item in result.diagnosis.all_signals]
    assert "suppressed_diagnostics" not in bundle.user_payload["diagnostic_calibration"]
    selected_sources = {metric for item in result.diagnosis.all_signals for metric in item.source_metrics}
    assert {item["name"] for item in bundle.user_payload["metrics"]} <= selected_sources


def test_no_debug_metric_index_expression_remains():
    source = (Path(__file__).parents[1] / "app" / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    assert "metric_results[14]" not in source


def test_revision_workflow_retains_calibration_and_does_not_mark_monitored_bias_solved(tmp_path):
    repository, service = local_stack(tmp_path)
    first = service.submit(EssaySubmission.model_validate(payload()))
    revised_data = payload("revised_draft.json")
    revised_data["revision_of_submission_id"] = first.essay_id
    revised = service.submit(EssaySubmission.model_validate(revised_data))
    assert revised.revision_snapshot is not None
    assert revised.diagnostic_calibration.diagnosis_version == "prototype-diagnosis-v0.6.1"
    trajectories = revised.revision_snapshot.diagnosis_trajectories
    assert not any(item.get("category") == "lexical_repetition" and item.get("status") in {"solved", "mastered"} for item in trajectories)
    assert repository._calf_repository.get_diagnostic_calibration(first.essay_id).monitored_signals
