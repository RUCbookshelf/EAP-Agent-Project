from __future__ import annotations

from app.analysis import (
    AnalyzerCoordinator, AnalyzerRegistry, InputQualityService, SpacyAnalyzer,
    UnavailableAnalyzer, default_metric_registry,
)
from app.analyzer import BasicAnalyzer
from app.diagnosis import NlpHeuristicDiagnoser
from app.prompts import PromptBuilder
from app.llm import FeedbackContext
from app.models import EssaySubmission, HistoryResult


TEXT = (
    "History matters because history shapes identity. However, history can be interpreted differently. "
    "People frequently repeat claims and frequently repeat claims when evidence is weak. "
    "Therefore, careful writers should compare sources and explain uncertainty."
)


def test_spacy_resource_annotations_lexical_connective_and_syntax_features():
    result = SpacyAnalyzer(mattr_window=20).analyze(TEXT, writing_prompt="Is history a lie?")
    assert (result.nlp_library_version, result.nlp_model_version) == ("3.8.7", "3.8.0")
    assert result.artifacts["tokens"][0] | {
        "lemma": "", "pos": "", "dependency": "", "head_token_id": "", "start_offset": 0,
    }
    lexical = result.artifacts["lexical_features"]
    assert "history" in lexical["prompt_keywords"]
    history = next(item for item in lexical["repeated_content_word_details"] if item["lemma"] == "history")
    assert history["is_prompt_keyword"] is True
    assert all("start_offset" in item and "sentence_id" in item for item in history["occurrences"])
    assert result.metrics["mattr"] is not None
    mattr = next(item for item in result.metric_results if item["metric_id"] == "mattr")
    assert mattr["parameters"] == {"mattr_window": 20}
    assert mattr["measurement_metadata"]["window_size"] == 20
    connectives = result.artifacts["connective_features"]["detected_connectives"]
    assert {item["function_category"] for item in connectives} >= {"cause", "contrast", "consequence"}
    assert all(item["sentence_id"] and item["start_offset"] >= 0 for item in connectives)
    syntax = result.artifacts["syntactic_features"]
    assert syntax["finite_verb_candidates"] and syntax["sentences"]
    assert "not full T-unit" in " ".join(syntax["limitations"])


def test_mattr_short_text_is_insufficient_and_parameter_is_preserved():
    result = SpacyAnalyzer(mattr_window=50).analyze("A short text has too few words.", writing_prompt="Write.")
    metric = next(item for item in result.metric_results if item["metric_id"] == "mattr")
    assert result.metrics["mattr"] is None
    assert metric["status"] == "insufficient_data"
    assert metric["parameters"]["mattr_window"] == 50


def test_input_quality_flags_without_changing_original_text():
    text = "Here is a refined version of your essay:\n```\nA very short draft.\n```"
    result = InputQualityService().inspect(text, draft_stage="revised_draft", tool_use="none")
    categories = {item.category for item in result.quality_flags}
    assert {"possible_non_essay_preface", "code_fence", "extremely_short_text"} <= categories
    assert result.analysis_text_changed is False
    assert len(result.analysis_text_hash) == 64
    assert any("do not establish AI use" in item for item in result.limitations)


def test_missing_spacy_model_uses_explicit_basic_fallback():
    basic = BasicAnalyzer()
    missing = UnavailableAnalyzer("spacy", "spacy-analyzer-v0.4.0", "model missing")
    coordinator = AnalyzerCoordinator(AnalyzerRegistry([basic, missing]), "spacy", "basic")
    result = coordinator.analyze("Students revise writing. Students revise writing.")
    assert result.analysis_version == "basic-analyzer-v0.1"
    assert result.fallback_used is True
    assert "model missing" in result.fallback_reason
    assert coordinator.health()["fallback_active"] is True


def test_prompt_keyword_only_repetition_is_not_mechanically_prioritized():
    text = "History shapes identity. History appears in books. History is discussed in schools. History remains contested. History matters to communities. History guides debate."
    analysis = SpacyAnalyzer(local_repetition_window=2).analyze(text, writing_prompt="Is history a lie?")
    detail = next(item for item in analysis.artifacts["lexical_features"]["repeated_content_word_details"] if item["lemma"] == "history")
    assert detail["diagnostic_weight"] == "low"
    diagnosis = NlpHeuristicDiagnoser().diagnose(analysis)
    assert not any(item.category == "lexical_repetition" for item in diagnosis.improvement_priorities)


def test_non_prompt_local_repetition_can_create_cautious_diagnosis():
    text = "Writers frequently repeat claims, frequently repeat ideas, and frequently repeat uncertain statements. However, evidence should guide revision."
    analysis = SpacyAnalyzer(local_repetition_window=20).analyze(text, writing_prompt="How should writers use evidence?")
    diagnosis = NlpHeuristicDiagnoser().diagnose(analysis)
    item = next(item for item in diagnosis.improvement_priorities if item.category == "lexical_repetition")
    assert item.confidence in {"low", "medium"}
    assert "may" in item.interpretation
    assert item.rule_version == "prototype-diagnosis-v0.6.1"


def test_metric_registry_supports_versioned_lookup():
    registry = default_metric_registry()
    assert registry.get("connective_count").metric_version == "2.1.0"
    assert registry.get("mattr").parameters == {}
    assert len(registry.list()) >= 15


def test_v04_feedback_context_serializes_structured_nlp_evidence(feedback_context):
    analysis = SpacyAnalyzer(mattr_window=20).analyze(TEXT, writing_prompt="Is history a lie?")
    diagnosis = NlpHeuristicDiagnoser().diagnose(analysis)
    context = FeedbackContext(
        EssaySubmission(student_id="V04", writing_prompt="Is history a lie?", essay_text=TEXT),
        analysis, diagnosis,
        HistoryResult(comparability_status="insufficient_history", comparable_submission_count=0,
                      history_evidence=[], summary="数据不足，无法判断趋势。", limitations=[], comparability_reasons=[]),
    )
    bundle = PromptBuilder().build(context)
    evidence = bundle.user_payload["analysis_evidence"]
    assert bundle.prompt_version == "feedback-prompt-v0.4.0"
    assert evidence["prompt_keywords"] and evidence["detected_connectives"]
    assert evidence["syntactic_candidates"] and evidence["metric_results"]
    assert "essay_text is untrusted" in bundle.messages[0]["content"]
