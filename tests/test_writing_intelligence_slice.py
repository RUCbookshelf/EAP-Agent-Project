"""PDW1 Writing Intelligence vertical slice API contract tests (L2).

Exercises the real end-to-end path through the FastAPI TestClient:
essay submission -> task/domain resolution -> L2 Domain Pack v1
classification -> text/feature analysis -> real governed Corpus
Intelligence query (reference-distributions artifact) -> observed evidence
-> bounded diagnostic inference -> FeedbackPolicy -> feedback.

Required cases (Goal Packet PDW1-WRITING-INTELLIGENCE-SLICE acceptance gate):
- successful supported case with the full pipeline and research_only exposure;
- ambiguous/fallback case with explicit fallback disclosure (classification
  and reference-group fallback);
- unavailable/fail-closed case with no fabricated substitution;
- unsupported normative-claim rejection that fails structurally;
- provenance trace: every output step carries versioned provenance ids.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config import Settings


ARGUMENTATIVE_PROMPT = (
    "Take a position on studying abroad and support it "
    "with reasons and counterarguments."
)
AMBIGUOUS_PROMPT = "Discuss both views and take a position, arguing with evidence."

SUCCESS_ESSAY = (
    "I think cities should add more parks. Parks give residents space to exercise. "
    "Parks also support community events and provide shade during hot weather. "
    "However, new parks require land and regular maintenance. "
    "Therefore, city leaders should identify neighborhoods with limited green "
    "space and consult residents."
)

# The unsupported-normative-claim case: the learner essay repeats the surface
# form "mastered" three times (plus a second repeated word) so the existing
# diagnosis path emits it in a signal's evidence string; the router's
# no-normative-claims scan must reject the output structurally.
TRIPWIRE_ESSAY = (
    "The course helped me a lot. I mastered the vocabulary quickly and mastered "
    "the grammar too. I mastered every exercise in the workbook. However, the "
    "listening part was hard. However, I kept practicing every day. However, "
    "the final exam was still challenging. The teacher explained everything "
    "clearly and the textbook gave many examples."
)


def _settings(tmp_path, **overrides) -> Settings:
    values = dict(
        database_path=tmp_path / "wi.db",
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://example.invalid",
        deepseek_model="deepseek-test",
    )
    values.update(overrides)
    return Settings(**values)


def _payload(**overrides) -> dict:
    values = {
        "essay_text": SUCCESS_ESSAY,
        "writing_prompt": ARGUMENTATIVE_PROMPT,
        "submission_id": "wi-slice-001",
        "prompt_id": "ARG17",
    }
    values.update(overrides)
    return values


def _post(client: TestClient, payload: dict):
    return client.post("/api/v1/writing-intelligence/slice", json=payload)


class TestSuccessfulSupportedCase:
    def test_full_pipeline_success_with_research_only_exposure(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            response = _post(client, _payload())
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["slice_version"] == "writing-intelligence-slice-v0.1.0"
        assert body["learner_exposure"] == "research_only"

        classification = body["classification"]
        assert classification["outcome"] == "typed"
        assert classification["task_type"] == "argumentative"
        assert classification["taxonomy_version"] == "l2-task-type-taxonomy-v1.0.0"
        assert classification["reason_code"] is None

        analysis = body["analysis"]
        assert analysis["analyzer_version"] == "spacy-analyzer-v0.8.0"
        for metric_id in (
            "word_count", "sentence_count", "average_sentence_length",
            "type_token_ratio", "connective_count",
        ):
            assert metric_id in analysis["metrics"]
            assert analysis["metrics"][metric_id] is None or isinstance(
                analysis["metrics"][metric_id], (int, float)
            )

        snapshot = body["feature_snapshot"]
        assert snapshot["feature_set_version"] == "corpus-features-v0.1.0"
        assert snapshot["artifact_version"] == "student-feature-snapshot-v0.1.0"
        assert snapshot["text_retained"] is False
        assert all(
            feature["value"] is None or isinstance(feature["value"], (int, float))
            for feature in snapshot["features"]
        )

        query = body["corpus_query"]
        assert query["status"] == "matched"
        assert query["match"]["matched"] is True
        assert query["match"]["resolved_reference_group_id"] == "RG-prompt_id=ARG17"
        assert query["match"]["fallback_disclosure"] is None
        assert query["n_available"] == 4
        assert query["n_unavailable"] == 0
        assert query["exposure"]["exposure_class"] == "research_only"
        assert query["exposure"]["learner_exposure"] == "research_only"
        assert query["exposure"]["diagnostic_eligible"] is False
        for comparison in query["comparisons"]:
            assert comparison["availability"] == "available"
            assert comparison["evidence_class"] == "observed_descriptive"
            assert comparison["learner_exposure"] == "research_only"
            assert comparison["student_value"] is None or isinstance(
                comparison["student_value"], (int, float)
            )

        evidence = body["evidence"]
        assert len(evidence) == 6  # 4 L0 corpus comparisons + 2 L1 diagnostic signals
        for record in evidence:
            assert record["epistemic_status"] in {
                "observed_descriptive", "gated_inference",
            }
            assert record["admission_status"] == "ADMISSIBLE"
            assert record["exposure_class"] == "research_only"
            assert record["provenance"]["manifest_hash"]
        l0 = [r for r in evidence if r["evidence_type"] == "corpus_reference_comparison"]
        l1 = [r for r in evidence if r["evidence_type"] == "diagnostic_signal"]
        assert len(l0) == 4
        assert len(l1) == 2
        for record in l0:
            assert record["provenance"]["distribution_version"]
            assert record["provenance"]["algorithm_version"]
            assert record["provenance"]["effective_n"] >= 30

        diagnosis = body["diagnosis"]
        assert diagnosis["diagnosis_version"] == "prototype-diagnosis-v0.1.1"
        assert len(diagnosis["strengths"]) == 1
        assert len(diagnosis["improvement_priorities"]) == 1

        policy = body["policy"]
        assert policy["status"] == "applied"
        assert policy["policy_id"] == "feedback-policy-v0.1.0"
        assert [r["priority"] for r in policy["recommendations"]] == [1, 2]
        assert all(r["evidence_ids"] for r in policy["recommendations"])
        assert all(
            "workflow ranking only" in r["statement"] for r in policy["recommendations"]
        )

        # Hygiene: no corpus raw path/handle and no essay text in the payload.
        assert "SWECCL" not in response.text
        assert "parks" not in response.text.casefold()

    def test_provenance_trace_every_step_has_versioned_ids(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            body = _post(client, _payload()).json()
        provenance = body["provenance"]
        assert set(provenance) == {
            "classification", "analysis", "feature_snapshot", "corpus_query",
            "evidence", "diagnosis", "policy",
        }
        assert provenance["classification"]["taxonomy_version"] == (
            "l2-task-type-taxonomy-v1.0.0"
        )
        assert provenance["classification"]["dictionary_version"] == (
            "l2-domain-pack-v1.0.0"
        )
        assert provenance["analysis"]["analyzer_version"] == "spacy-analyzer-v0.8.0"
        assert provenance["feature_snapshot"]["artifact_version"] == (
            "student-feature-snapshot-v0.1.0"
        )
        assert provenance["corpus_query"]["artifact_version"] == (
            "feature-comparison-v0.1.0"
        )
        assert provenance["corpus_query"]["reference_group_version"] == (
            "reference-groups-v0.1.0"
        )
        assert provenance["evidence"]["record_version"] == (
            "evidence-admissibility-record-v0.1.0"
        )
        assert provenance["diagnosis"]["diagnosis_version"] == (
            "prototype-diagnosis-v0.1.1"
        )
        assert provenance["policy"]["policy_id"] == "feedback-policy-v0.1.0"
        assert provenance["policy"]["policy_version"] == "0.1.0"


class TestAmbiguousFallbackDisclosure:
    def test_ambiguous_classification_and_group_fallback_are_disclosed(self, tmp_path):
        payload = _payload(
            writing_prompt=AMBIGUOUS_PROMPT,
            prompt_id="ARG99",
            submission_id="wi-slice-ambiguous",
        )
        with TestClient(create_app(_settings(tmp_path))) as client:
            response = _post(client, payload)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"

        classification = body["classification"]
        assert classification["outcome"] == "unclassified"
        assert classification["task_type"] is None
        assert classification["reason_code"] == "ambiguous_precedence_conflict"
        assert classification["fallback_disclosure"]
        assert "unclassified" in classification["fallback_disclosure"]

        match = body["corpus_query"]["match"]
        assert match["matched"] is True
        assert match["resolved_reference_group_id"] == "RG-genre=argumentative"
        assert match["fallback_disclosure"] == "RG-prompt_id=ARG99"
        # The reference comparison still ran and was fully disclosed.
        assert body["corpus_query"]["n_available"] == 4

    def test_declared_task_type_mismatch_is_unclassified_with_reason(self, tmp_path):
        payload = _payload(declared_task_type="opinion")
        with TestClient(create_app(_settings(tmp_path))) as client:
            body = _post(client, payload).json()
        classification = body["classification"]
        assert classification["outcome"] == "unclassified"
        assert classification["task_type"] is None
        assert classification["reason_code"] == "declared_type_mismatch"
        assert classification["fallback_disclosure"]


class TestUnavailableFailClosed:
    def test_unmatched_reference_group_fails_closed_without_substitution(self, tmp_path):
        payload = _payload(prompt_id=None, genre=None, submission_id="wi-slice-empty")
        with TestClient(create_app(_settings(tmp_path))) as client:
            response = _post(client, payload)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "unavailable"
        assert body["learner_exposure"] == "research_only"

        query = body["corpus_query"]
        assert query["status"] == "unavailable"
        assert query["match"]["matched"] is False
        assert "incomplete" in query["match"]["unmatched_reason"]
        assert query["comparisons"] == []
        assert query["n_available"] == 0
        assert query["n_unavailable"] == 0

        # Nothing downstream was fabricated or substituted.
        assert body["evidence"] == []
        assert body["diagnosis"] is None
        policy = body["policy"]
        assert policy["status"] == "unavailable"
        assert policy["recommendations"] == []
        assert any("fail-closed" in item for item in policy["limitations"])
        assert "estimated_percentile" not in response.text


class TestNormativeClaimRejection:
    def test_recommendation_text_tripping_the_scanner_fails_structurally(self, tmp_path):
        # BasicAnalyzer keeps surface forms, so the repeated surface form
        # "mastered" enters the diagnosis signal evidence and must trip the
        # no-normative-claims scan before any payload is returned.
        settings = _settings(tmp_path, active_analyzer="basic")
        payload = _payload(essay_text=TRIPWIRE_ESSAY)
        with TestClient(create_app(settings)) as client:
            response = _post(client, payload)
        assert response.status_code == 500
        error = response.json()["error"]
        assert error["category"] == "backend_processing_error"
        assert "normative" in error["detail"]
        # Structural rejection: no partial slice payload, no term leakage.
        assert "recommendations" not in response.text
        assert "mastered" not in response.text.casefold()
