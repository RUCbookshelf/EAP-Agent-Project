"""Contract-shape and behavior tests for the local Wave-2 mock backend.

The mock backend is the test double that stands in for the Wave-2 API
contracts until they land at integration. Payload shapes must mirror the
documented contracts (revision_api / personalized_api / learner_api), and
scenarios must never fabricate history for learners without stored history.
"""

from __future__ import annotations

import pytest

from app.ui.wave2.client import Wave2ApiUnavailable
from app.ui.wave2.mock import MockWave2Backend, MockWave2Client


def make_essay(repeated_word: str = "parks") -> str:
    return (
        f"Cities should add more {repeated_word} because {repeated_word} give residents "
        f"space to exercise. {repeated_word} also support community events and provide "
        f"shade during hot weather. However, new {repeated_word} require land and "
        "regular maintenance. Therefore, city leaders should first identify "
        "neighborhoods with limited green space and consult residents."
    )


def make_backend(scenario: str = "new_learner") -> MockWave2Backend:
    return MockWave2Backend(scenario=scenario)


def make_task(backend: MockWave2Backend, student_id: str = "L-STU-001") -> dict:
    return backend.create_task(
        student_id=student_id,
        task_type="opinion",
        writing_context="cet4",
        writing_prompt="Should cities add more parks?",
    )


def test_create_task_contract_shape():
    backend = make_backend()
    task = make_task(backend)
    assert set(task) == {
        "task_id", "student_id", "task_type", "writing_context", "writing_prompt",
        "metadata", "modality", "classification", "status", "created_at", "limitations",
    }
    assert task["task_id"].startswith("T-")
    assert task["student_id"] == "L-STU-001"
    assert task["task_type"] == "opinion"
    assert task["writing_context"] == "cet4"
    assert task["writing_prompt"] == "Should cities add more parks?"
    assert task["modality"] == "written"
    assert task["status"] == "active"
    assert isinstance(task["metadata"], dict)
    assert task["metadata"].get("audience") is None
    assert task["metadata"].get("genre_expectations") == []


def test_create_task_validates_taxonomy():
    backend = make_backend()
    with pytest.raises(ValueError):
        backend.create_task(
            student_id="S1", task_type="not_a_type", writing_context="cet4",
            writing_prompt="Prompt",
        )
    with pytest.raises(ValueError):
        backend.create_task(
            student_id="S1", task_type="opinion", writing_context="not_a_context",
            writing_prompt="Prompt",
        )


def test_create_task_metadata_passthrough():
    backend = make_backend()
    task = backend.create_task(
        student_id="S1", task_type="argumentative", writing_context="ielts_task2",
        writing_prompt="Prompt", metadata={"audience": "examiner", "word_constraint": "250"},
    )
    assert task["metadata"]["audience"] == "examiner"
    assert task["metadata"]["word_constraint"] == "250"


def test_submit_v1_contract_shape():
    backend = make_backend()
    task = make_task(backend)
    version = backend.submit_v1(task["task_id"], make_essay())
    assert set(version) == {
        "task_id", "submission_id", "version_number", "revision_of_submission_id",
        "ancestry", "submitted_at", "task_context", "essay_text_hash", "draft_stage",
        "analysis_run_id", "analysis_version", "feedback_record_id",
        "revision_group_id", "revision_snapshot_id", "corpus_routing",
        "reanalysis_events", "limitations",
    }
    assert version["submission_id"] == 1
    assert version["version_number"] == 1
    assert version["revision_of_submission_id"] is None
    assert version["ancestry"] == [1]
    assert version["draft_stage"] == "first draft"
    assert version["essay_text_hash"]
    assert version["task_context"]["writing_prompt"] == "Should cities add more parks?"
    assert version["task_context"]["writing_context"] == "cet4"
    assert version["corpus_routing"]["written"] is True


def test_revise_is_append_only():
    backend = make_backend()
    task = make_task(backend)
    v1 = backend.submit_v1(task["task_id"], make_essay())
    v2 = backend.revise(task["task_id"], v1["submission_id"], make_essay(repeated_word="green spaces"))
    assert v2["submission_id"] == 2
    assert v2["version_number"] == 2
    assert v2["revision_of_submission_id"] == 1
    assert v2["ancestry"] == [1, 2]
    history = backend.version_history(task["task_id"])
    assert history["task_id"] == task["task_id"]
    assert len(history["versions"]) == 2
    assert history["versions"][0]["essay_text_hash"] == v1["essay_text_hash"]


def test_revise_unknown_submission_raises():
    backend = make_backend()
    task = make_task(backend)
    backend.submit_v1(task["task_id"], make_essay())
    with pytest.raises(LookupError):
        backend.revise(task["task_id"], 99, "text")


def test_priority_plan_new_learner_has_no_fabricated_history():
    backend = make_backend(scenario="new_learner")
    task = make_task(backend, student_id="L-NEW-001")
    version = backend.submit_v1(task["task_id"], make_essay())
    plan = backend.priority_plan("L-NEW-001", task["task_id"], version["submission_id"])
    assert set(plan) == {
        "plan_id", "learner_id", "task_id", "submission_id", "generated_at", "items",
        "history_state", "history_reasons", "local_observations", "global_observations",
        "historical_feedback", "limitations", "claims_status",
    }
    assert plan["history_state"] == "insufficient_history"
    assert plan["history_reasons"]
    assert plan["historical_feedback"] == []
    assert plan["claims_status"] == "observation_only"
    assert 1 <= len(plan["items"]) <= 3
    item = plan["items"][0]
    assert set(item) == {
        "plan_item_id", "category", "diagnosis_id", "recurrence_status", "context",
        "action_statement", "evidence_refs", "confidence", "ordering_note", "limitations",
    }
    assert item["recurrence_status"] == "first_observed"
    assert item["action_statement"]
    assert item["ordering_note"]


def test_priority_plan_returning_learner_uses_history():
    backend = make_backend(scenario="returning_learner")
    task = make_task(backend, student_id="L-RET-001")
    version = backend.submit_v1(task["task_id"], make_essay())
    plan = backend.priority_plan("L-RET-001", task["task_id"], version["submission_id"])
    assert plan["history_state"] == "sufficient"
    assert plan["historical_feedback"]
    recurring = [h for h in plan["historical_feedback"] if h["status"] == "recurring"]
    assert recurring, "returning learner must expose a recurring historical item"
    assert recurring[0]["occurrence_count"] >= 2
    plan_categories = {item["category"] for item in plan["items"]}
    assert plan_categories & {item["category"] for item in recurring}


def test_revision_observation_contract_shape():
    backend = make_backend()
    task = make_task(backend)
    v1 = backend.submit_v1(task["task_id"], make_essay())
    v2 = backend.revise(task["task_id"], v1["submission_id"], make_essay(repeated_word="green spaces"))
    observation = backend.revision_observation(task["task_id"], v2["submission_id"])
    assert set(observation) == {
        "observation_id", "task_id", "source_submission_id", "target_submission_id",
        "observed_at", "what_changed", "feedback_areas", "new_observations",
        "apparent_independent_corrections", "no_intent_inference", "limitations",
    }
    assert observation["source_submission_id"] == 1
    assert observation["target_submission_id"] == 2
    assert observation["no_intent_inference"]
    assert isinstance(observation["what_changed"], dict)


def test_observation_reports_addressed_and_remaining():
    backend = make_backend()
    task = make_task(backend)
    v1 = backend.submit_v1(task["task_id"], make_essay())
    plan = backend.priority_plan("L-STU-001", task["task_id"], v1["submission_id"])
    categories = {item["category"] for item in plan["items"]}
    assert categories, "plan must produce at least one item for the sample essay"
    fixed = (
        "Cities should add more parks because green spaces give residents room to "
        "exercise. Parks also support community events and provide shade during hot "
        "weather. However, new parks require land and regular maintenance. Therefore, "
        "city leaders should first identify neighborhoods with limited green space "
        "and consult residents."
    )
    v2 = backend.revise(task["task_id"], v1["submission_id"], fixed)
    observation = backend.revision_observation(task["task_id"], v2["submission_id"])
    by_category = {area["category"]: area for area in observation["feedback_areas"]}
    if "lexical_repetition" in by_category:
        assert by_category["lexical_repetition"]["status"] in {"addressed", "remaining"}
    v3 = backend.revise(task["task_id"], v2["submission_id"], fixed)
    observation2 = backend.revision_observation(task["task_id"], v3["submission_id"])
    assert observation2["source_submission_id"] == 2
    assert observation2["target_submission_id"] == 3


def test_scaffold_default_first_and_progressive_levels():
    backend = make_backend()
    first = backend.scaffold("L-STU-001", "lexical_repetition")
    assert set(first) == {
        "learner_id", "category", "level", "default_first", "available_levels",
        "content", "learner_action", "never_writes_statement", "limitations",
    }
    assert first["default_first"] is True
    assert first["level"] == 1
    assert first["available_levels"] == list(range(1, 8))
    assert first["content"]["level"] == 1
    assert first["content"]["kind"]
    assert first["content"]["text"]
    assert first["learner_action"]
    assert first["never_writes_statement"]
    deeper = backend.scaffold("L-STU-001", "lexical_repetition", level=4)
    assert deeper["level"] == 4
    assert deeper["content"]["level"] == 4
    with pytest.raises(ValueError):
        backend.scaffold("L-STU-001", "lexical_repetition", level=8)


def test_scaffold_templates_are_category_specific():
    backend = make_backend()
    a = backend.scaffold("L1", "lexical_repetition", level=1)
    b = backend.scaffold("L1", "sentence_variety", level=1)
    assert a["content"]["text"] != b["content"]["text"]
    for level in range(1, 8):
        revealed = backend.scaffold("L1", "connective_use", level=level)
        assert revealed["content"]["text"], f"level {level} must have content"


def test_learning_item_lifecycle():
    backend = make_backend()
    task = make_task(backend)
    version = backend.submit_v1(task["task_id"], make_essay())
    plan = backend.priority_plan("L-STU-001", task["task_id"], version["submission_id"])
    item = backend.create_learning_item("L-STU-001", plan["items"][0]["plan_item_id"])
    assert set(item) == {
        "learning_item_id", "student_id", "category", "originating_evidence",
        "feedback_reference", "revision_history", "task_id", "task_context",
        "status", "created_at", "updated_at", "no_fsrs_note", "no_practice_note",
        "limitations",
    }
    assert item["status"] == "proposed"
    assert item["category"] == plan["items"][0]["category"]
    assert item["task_id"] == task["task_id"]
    assert "no_fsrs_note" in item and "no_practice_note" in item
    updated = backend.update_learning_item_status(item["learning_item_id"], "active")
    assert updated["status"] == "active"
    with pytest.raises(ValueError):
        backend.update_learning_item_status(item["learning_item_id"], "nonsense")
    with pytest.raises(LookupError):
        backend.create_learning_item("L-STU-001", "PLAN-NOPE")
    items = backend.list_learning_items("L-STU-001")["items"]
    assert len(items) == 1
    assert backend.list_learning_items("L-STU-001", status="active")["items"]
    assert backend.list_learning_items("L-STU-001", status="proposed")["items"] == []


def test_learner_views_returning_learner():
    backend = make_backend(scenario="returning_learner")
    observations = backend.list_observations("L-RET-001")
    assert observations["history_state"] == "sufficient"
    assert observations["items"]
    view = observations["items"][0]
    assert set(view) == {
        "learner_id", "observation_id", "code", "label", "observation_type",
        "occurrence_count", "qualified_occurrence_count", "prior_occurrence_count",
        "appeared_before", "first_observed_at", "last_observed_at",
        "days_since_last_observed", "contexts", "revision_response",
        "addressed_in_prior_revision", "frequency", "history_state",
        "history_reasons", "limitations", "claims_status",
    }
    assert view["appeared_before"] is True
    difficulties = backend.difficulties("L-RET-001")
    assert difficulties["items"]
    assert difficulties["items"][0]["observation_type"] == "difficulty"
    strengths = backend.strengths("L-RET-001")
    assert strengths["items"]
    assert strengths["items"][0]["observation_type"] == "strength"
    stable = backend.stable("L-RET-001")
    assert stable["items"]
    assert stable["items"][0]["stability_kind"]
    context = backend.proficiency_context("L-RET-001")
    assert context["derived_from_corpus"] is False
    assert context["anchors"]
    assert context["anchors"][0]["system"]
    assert context["anchors"][0]["declared_value"]
    evidence = backend.current_evidence("L-RET-001")
    assert evidence["items"]
    assert evidence["items"][0]["learner_id"] == "L-RET-001"


def test_learner_views_new_learner_never_fabricate():
    backend = make_backend(scenario="new_learner")
    observations = backend.list_observations("L-NEW-001")
    assert observations["items"] == []
    assert observations["history_state"] == "insufficient_history"
    difficulties = backend.difficulties("L-NEW-001")
    assert difficulties["items"] == []
    assert difficulties["history_state"] == "insufficient_history"
    assert backend.strengths("L-NEW-001")["items"] == []
    assert backend.stable("L-NEW-001")["items"] == []
    context = backend.proficiency_context("L-NEW-001")
    assert context["anchors"] == []
    assert context["history_state"] == "insufficient_history"
    assert backend.current_evidence("L-NEW-001")["items"] == []


def test_mock_client_unavailable_flag_fails_closed():
    backend = make_backend(scenario="returning_learner")
    client = MockWave2Client(backend, available=False)
    assert client.probe() is False
    with pytest.raises(Wave2ApiUnavailable):
        client.create_task(student_id="S1", task_type="opinion",
                           writing_context="cet4", writing_prompt="P")
    with pytest.raises(Wave2ApiUnavailable):
        client.list_observations("S1")
    online = MockWave2Client(backend, available=True)
    assert online.probe() is True
    assert online.list_observations("L-RET-001")["history_state"] == "sufficient"