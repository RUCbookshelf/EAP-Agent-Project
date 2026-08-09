"""Domain Pack v1 deterministic task-type classifier tests (G5 content).

Covers the qualified taxonomy contract criteria (Constraints 1-3, 6-7) and
the V1 adjudication outcomes A-1..A-8:
- classification determinism and normalization invariance (Constraint 1.2);
- opinion-vs-argumentative distinction (Constraint 2; A-8);
- precedence chain (Constraint 3; A-1, A-2, A-4);
- conflict rule (Constraint 3 application rule 2; A-3);
- unclassified handling with reason codes (Constraint 5);
- general_eap fallback semantics (Constraint 6; A-5, A-7);
- provenance (taxonomy/dictionary version, matched triggers, Constraint 2.4);
- declared task metadata validation (D-L2-10 posture).
"""

from __future__ import annotations

import pytest

from app.services.task_type_classifier import (
    REASON_AMBIGUOUS_CONFLICT,
    REASON_DECLARED_MISMATCH,
    REASON_NOT_EAP,
    REASON_NO_PROMPT,
    TaskTypeClassificationError,
    canonical_display_order,
    classify_task_definition,
    normalize_prompt,
)


def typed(prompt, declared=None):
    return classify_task_definition(prompt, declared)


class TestOpinionVsArgumentative:
    """Constraint 2 - explicit opinion-vs-argumentative distinction."""

    def test_opinion_without_evidence_mandate(self):
        result = typed("What is your opinion on studying abroad?")
        assert result.outcome == "typed"
        assert result.task_type == "opinion"

    def test_argumentative_stance_plus_evidence(self):
        result = typed(
            "Take a position on studying abroad and support it "
            "with reasons and counterarguments."
        )
        assert result.outcome == "typed"
        assert result.task_type == "argumentative"

    def test_stance_plus_evidence_wins_over_opinion_word(self):
        result = typed(
            "Do you agree or disagree with studying abroad? "
            "Support your opinion with reasons."
        )
        assert result.task_type == "argumentative"

    def test_viewpoint_plus_evidence_mandate_is_argumentative(self):
        result = typed("What is your view on X? Give reasons and examples.")
        assert result.task_type == "argumentative"

    def test_viewpoint_without_evidence_stays_opinion(self):
        result = typed("What is your own opinion on online learning?")
        assert result.task_type == "opinion"


class TestPrecedenceChain:
    """Constraint 3 - precedence for ambiguous prompts (A-1, A-2, A-4)."""

    def test_problem_solution_outranks_argumentative(self):
        # V1 adjudication A-4: chain, not conflict.
        result = typed(
            "Take a position on the causes of X and support it "
            "with reasons and counterarguments."
        )
        assert result.task_type == "problem_solution"

    def test_discussion_outranks_opinion(self):
        # V1 adjudication A-1: balanced treatment subsumes viewpoint request.
        result = typed("Discuss both views and give your own opinion.")
        assert result.task_type == "discussion"

    def test_discussion_outranks_opinion_zh(self):
        result = typed("讨论出国留学的利与弊，并给出你的看法。")
        assert result.task_type == "discussion"

    def test_argumentative_outranks_opinion(self):
        result = typed(
            "What is your opinion on X? Support your answer with reasons."
        )
        assert result.task_type == "argumentative"

    def test_problem_solution_outranks_discussion(self):
        result = typed(
            "Discuss the problem of X and propose solutions."
        )
        assert result.task_type == "problem_solution"


class TestConflictRule:
    """Constraint 3 application rule 2 - comparable-strength conflicts (A-3)."""

    def test_argumentative_plus_discussion_is_unclassified(self):
        # Canonical contract example.
        result = typed(
            "Discuss both views and take a position, arguing with evidence."
        )
        assert result.outcome == "unclassified"
        assert result.reason_code == REASON_AMBIGUOUS_CONFLICT
        assert result.task_type is None

    def test_discussion_plus_opinion_plus_evidence_is_conflict(self):
        result = typed(
            "Discuss both sides and give your opinion with reasons."
        )
        assert result.outcome == "unclassified"
        assert result.reason_code == REASON_AMBIGUOUS_CONFLICT

    def test_conflict_never_coerced_to_general_eap(self):
        result = typed(
            "Write an essay. Discuss both views and take a position, "
            "arguing with evidence."
        )
        assert result.outcome == "unclassified"
        assert result.task_type is None


class TestProblemSolutionScope:
    """Trigger-class scope incl. V1 adjudication A-7 (effects excluded)."""

    def test_causes_and_effects_matches_problem_solution(self):
        # Cause content is present; effects never extend the class by
        # themselves (A-7 closed-class reading).
        result = typed("What are the causes and effects of X?")
        assert result.task_type == "problem_solution"

    def test_effects_only_with_eap_context_falls_to_general_eap(self):
        result = typed("Write an essay about the effects of studying abroad.")
        assert result.task_type == "general_eap"

    def test_effects_only_without_eap_context_is_unclassified(self):
        result = typed("What are the effects of X?")
        assert result.outcome == "unclassified"
        assert result.reason_code == REASON_NOT_EAP

    def test_zh_problem_solution(self):
        result = typed("如何解决城市空气污染问题？")
        assert result.task_type == "problem_solution"


class TestGeneralEapFallback:
    """Constraint 6 - general_eap affirmative conditions (A-5)."""

    def test_generic_essay_prompt_is_general_eap(self):
        result = typed("Write an essay about the importance of education.")
        assert result.task_type == "general_eap"
        assert result.outcome == "typed"

    def test_zh_generic_composition_is_general_eap(self):
        result = typed("写一篇关于大学生活的小短文。")
        assert result.task_type == "general_eap"

    def test_non_eap_prompt_is_unclassified_not_general_eap(self):
        result = typed("Write a story about your holiday.")
        assert result.outcome == "unclassified"
        assert result.reason_code == REASON_NOT_EAP

    def test_general_eap_never_selected_when_specific_trigger_matched(self):
        result = typed("Write an essay. Do you agree or disagree with X?")
        assert result.task_type == "opinion"


class TestUnclassifiedHandling:
    """Constraint 5 - honest states with reason codes, no coercion."""

    def test_missing_prompt_is_unclassified_no_prompt(self):
        for prompt in (None, "", "   "):
            result = typed(prompt)
            assert result.outcome == "unclassified"
            assert result.reason_code == REASON_NO_PROMPT
            assert result.task_type is None

    def test_unclassified_never_promoted_to_general_eap(self):
        result = typed("Write a story about your holiday.")
        assert result.task_type is None
        assert result.reason_code == REASON_NOT_EAP

    def test_legacy_unclassified_sentinel_unreachable_in_classifier(self):
        result = typed("Some generic non-EAP instruction.")
        assert result.task_type is None
        assert result.provenance["legacy_sentinel_unreachable"] == "legacy_unclassified"


class TestDeclaredTaskMetadata:
    """Declared task metadata validation (D-L2-10 posture, contract 2.1)."""

    def test_declared_matching_type_confirmed(self):
        result = typed(
            "Take a position on X and support it with reasons.",
            declared="argumentative",
        )
        assert result.outcome == "typed"
        assert result.task_type == "argumentative"
        assert result.provenance["declaration_agreement"] is True

    def test_declared_mismatch_is_unclassified(self):
        result = typed(
            "Take a position on X and support it with reasons.",
            declared="opinion",
        )
        assert result.outcome == "unclassified"
        assert result.reason_code == REASON_DECLARED_MISMATCH
        assert result.task_type is None

    def test_invalid_declared_type_rejected(self):
        with pytest.raises(TaskTypeClassificationError, match="Unknown declared task type"):
            typed("What is your opinion on X?", declared="discourse_organization")

    def test_declared_with_unclassified_prompt_keeps_honest_reason(self):
        result = typed("Write a story about your holiday.", declared="opinion")
        assert result.outcome == "unclassified"
        assert result.reason_code == REASON_NOT_EAP
        assert result.provenance["declared_task_type"] == "opinion"


class TestDeterminismAndNormalization:
    """Constraint 1.2 - closed deterministic procedure; normalization."""

    def test_same_input_same_output(self):
        prompt = "Discuss both views and take a position, arguing with evidence."
        first = classify_task_definition(prompt)
        for _ in range(5):
            assert classify_task_definition(prompt) == first

    def test_whitespace_and_case_invariance(self):
        canonical = "What is your opinion on studying abroad?"
        variants = [
            "   WHAT   is your OPINION on studying   abroad?  ",
            "what is your opinion on studying abroad ?",
            "What is your opinion on  studying  abroad?",
        ]
        expected = classify_task_definition(canonical)
        for variant in variants:
            assert classify_task_definition(variant) == expected

    def test_normalize_prompt_collapses_whitespace(self):
        assert normalize_prompt("  What   IS  this?  ") == "what is this?"

    def test_word_boundary_does_not_match_substrings(self):
        # "opinion" must not match inside "opinions"; no viewpoint request.
        result = typed("Write an essay about opinions on education.")
        assert result.task_type == "general_eap"


class TestZhCNDictionaries:
    """zh_CN trigger dictionaries (D-L2-09 parity; locale-agnostic matching)."""

    def test_zh_opinion(self):
        result = typed("你怎么看待出国留学？")
        assert result.task_type == "opinion"

    def test_zh_argumentative(self):
        result = typed("你同意还是不同意出国留学？请给出你的理由。")
        assert result.task_type == "argumentative"

    def test_zh_viewpoint_plus_reason_is_argumentative(self):
        result = typed("谈谈你的观点，并说明理由。")
        assert result.task_type == "argumentative"


class TestProvenance:
    """Constraint 2.4 / 7 - versioned provenance on every outcome."""

    def test_versions_recorded(self):
        result = typed("What is your opinion on X?")
        assert result.taxonomy_version == "l2-task-type-taxonomy-v1.0.0"
        assert result.dictionary_version == "l2-domain-pack-v1.0.0"

    def test_matched_triggers_recorded(self):
        result = typed("Do you agree or disagree with X? Support with evidence.")
        phrases = {item["phrase"] for item in result.matched_triggers}
        assert "agree or disagree with" in phrases
        assert "with evidence" in phrases

    def test_canonical_display_order(self):
        assert canonical_display_order() == [
            "opinion", "argumentative", "discussion",
            "problem_solution", "general_eap",
        ]
