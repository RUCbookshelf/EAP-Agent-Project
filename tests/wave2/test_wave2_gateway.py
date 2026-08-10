"""Gateway tests: Wave-2-first with graceful fallback to the legacy flow.

The gateway is the UI-facing facade. When the Wave-2 endpoints are
unavailable (they land at integration), the studio journey degrades to the
existing writing/feedback flow without crashing and without fabricating
Wave-2 features (scaffold engine, priority plan) that do not exist yet.
"""

from __future__ import annotations

import pytest

from app.ui.wave2.client import Wave2ApiUnavailable
from app.ui.wave2.gateway import Wave2Gateway
from app.ui.wave2.mock import MockWave2Backend, MockWave2Client


ESSAY = (
    "Cities should add more parks because parks give residents space to exercise. "
    "Parks also support community events and provide shade during hot weather. "
    "However, new parks require land and regular maintenance. Therefore, city leaders "
    "should first identify neighborhoods with limited green space and consult residents."
)

LEGACY_PRIORITIES = [
    {
        "category": "lexical_repetition",
        "evidence_quote": "Parks support public health.",
        "explanation": "The word 'parks' is repeated closely in the draft.",
        "revision_guidance": "Replace one repetition with a synonym.",
    }
]

LEGACY_JOURNEY = {
    "state": "feedback_no_practice_target",
    "events": [
        {
            "title_key": "journey_event_writing_submitted",
            "occurred_at": "2026-08-01T10:00:00Z",
            "submission_id": 5,
        }
    ],
}

LEGACY_CANDIDATES = {
    "candidates": [
        {
            "essay_id": 5,
            "student_id": "S-LEG",
            "writing_prompt": "Should cities add more parks?",
            "genre": "argumentative essay",
            "draft_stage": "first draft",
            "submitted_at": "2026-08-01T10:00:00Z",
            "feedback": {"priority_feedback": LEGACY_PRIORITIES},
        }
    ]
}


class FakeLegacyClient:
    """Scripted stand-in for the existing WritingFeedbackApiClient."""

    def __init__(self):
        self.submits = []
        self.linked_revisions = []
        self.journey = dict(LEGACY_JOURNEY)
        self.candidates = dict(LEGACY_CANDIDATES)
        self.raise_on_submit = None

    def submit(self, payload):
        if self.raise_on_submit:
            raise self.raise_on_submit
        self.submits.append(payload)
        return {
            "submission_id": 100,
            "student_id": payload["student_id"],
            "writing_prompt": payload["writing_prompt"],
            "genre": payload["genre"],
            "draft_stage": payload["draft_stage"],
            "essay_text": payload["essay_text"],
            "feedback_result": {
                "feedback": {
                    "priority_feedback": LEGACY_PRIORITIES,
                    "positive_finding": {
                        "explanation": "The draft answers the prompt directly.",
                        "evidence_quote": "",
                    },
                    "uncertainty_note": "Prototype feedback.",
                }
            },
            "history": {"comparability_status": "insufficient_history"},
        }

    def submit_linked_revision(self, payload):
        self.linked_revisions.append(payload)
        result = self.submit(payload)
        result["revision_of_submission_id"] = payload["revision_of_submission_id"]
        return result

    def get_journey(self, student_id):
        return dict(self.journey)

    def get_student_revision_candidates(self, student_id):
        return {"candidates": list(self.candidates["candidates"])}

    def get_submission(self, submission_id):
        return dict(self.candidates["candidates"][0])


def make_wave2_client(scenario="new_learner", available=True) -> MockWave2Client:
    return MockWave2Client(MockWave2Backend(scenario=scenario), available=available)


def make_gateway(wave2_client=None, legacy_client=None, mode="auto", scenario="new_learner") -> Wave2Gateway:
    return Wave2Gateway(
        wave2_client=wave2_client or make_wave2_client(scenario=scenario),
        legacy_client=legacy_client or FakeLegacyClient(),
        mode=mode,
    )


def make_task_dict() -> dict:
    return {
        "task_type": "opinion",
        "writing_context": "cet4",
        "writing_prompt": "Should cities add more parks?",
        "metadata": {},
    }


def test_auto_mode_uses_wave2_when_available():
    gateway = make_gateway(mode="auto")
    assert gateway.available() is True
    assert gateway.mode() == "guided"
    task = gateway.create_task("S1", "opinion", "cet4", "Should cities add more parks?")
    assert task["task_id"].startswith("T-")
    outcome = gateway.submit_first(task, ESSAY, "first draft")
    assert outcome["mode"] == "guided"
    assert outcome["version"]["version_number"] == 1
    assert outcome["feedback"]["history_state"] == "insufficient_history"
    assert outcome["feedback"]["items"]


def test_auto_mode_falls_back_to_legacy_when_unavailable():
    wave2 = make_wave2_client(available=False)
    legacy = FakeLegacyClient()
    gateway = make_gateway(wave2_client=wave2, legacy_client=legacy, mode="auto")
    assert gateway.available() is False
    assert gateway.mode() == "standard"
    task = gateway.create_task("S1", "opinion", "cet4", "Should cities add more parks?")
    assert task["task_id"] is None  # no server-side task in legacy mode
    outcome = gateway.submit_first(task, "S1", ESSAY, "first draft")
    assert outcome["mode"] == "standard"
    assert outcome["feedback"]["items"]
    assert outcome["feedback"]["items"][0]["category"] == "lexical_repetition"
    assert legacy.submits
    assert legacy.submits[0]["genre"] == "argumentative essay"
    assert legacy.submits[0]["student_id"] == "S1"


def test_forced_modes():
    gateway = make_gateway(mode="wave2")
    assert gateway.mode() == "guided"
    gateway_legacy = make_gateway(mode="legacy")
    assert gateway_legacy.mode() == "standard"
    assert gateway_legacy.available() is False


def test_legacy_scaffold_is_honestly_unavailable():
    gateway = make_gateway(mode="legacy")
    result = gateway.scaffold("S1", "lexical_repetition")
    assert result == {"available": False}


def test_guided_scaffold_reveals_progressive_levels():
    gateway = make_gateway(mode="wave2", scenario="new_learner")
    task = gateway.create_task("S1", "opinion", "cet4", "Should cities add more parks?")
    outcome = gateway.submit_first(task, ESSAY, "first draft")
    category = outcome["feedback"]["items"][0]["category"]
    first = gateway.scaffold("S1", category)
    assert first["available"] is True
    assert first["level"] == 1
    assert first["content"]["text"]
    deeper = gateway.scaffold("S1", category, level=3)
    assert deeper["level"] == 3


def test_guided_revision_returns_observation():
    gateway = make_gateway(mode="wave2", scenario="new_learner")
    task = gateway.create_task("S1", "opinion", "cet4", "Should cities add more parks?")
    outcome = gateway.submit_first(task, ESSAY, "first draft")
    revised = gateway.submit_revision(task, outcome["version"]["submission_id"], ESSAY.replace("parks", "green spaces"), "revised draft")
    assert revised["mode"] == "guided"
    assert revised["version"]["version_number"] == 2
    assert revised["observation"]["what_changed_summary"]
    assert revised["observation"]["no_intent_inference"]


def test_legacy_revision_posts_linked_revision():
    legacy = FakeLegacyClient()
    gateway = make_gateway(mode="legacy", legacy_client=legacy)
    task = gateway.create_task("S1", "opinion", "cet4", "Should cities add more parks?")
    gateway.submit_first(task, "S1", ESSAY, "first draft")
    outcome = gateway.submit_revision(task, 100, ESSAY.replace("parks", "green spaces"), "revised draft")
    assert legacy.linked_revisions
    assert legacy.linked_revisions[0]["revision_of_submission_id"] == 100
    assert outcome["mode"] == "standard"
    assert outcome["observation"] is None
    assert outcome["version"]["submission_id"] == 100


def test_returning_learner_history_view():
    gateway = make_gateway(mode="wave2", scenario="returning_learner")
    history = gateway.history("L-RET-001")
    assert history["learner_id"] == "L-RET-001"
    assert history["history_state"] == "sufficient"
    assert history["learning_items"]
    assert history["longitudinal"]["difficulties"]
    assert history["longitudinal"]["strengths"]
    assert history["longitudinal"]["stable"]
    assert history["longitudinal"]["proficiency_anchors"]


def test_new_learner_history_view_never_fabricates():
    gateway = make_gateway(mode="wave2", scenario="new_learner")
    history = gateway.history("L-NEW-001")
    assert history["history_state"] == "insufficient_history"
    assert history["tasks"] == []
    assert history["learning_items"] == []
    assert history["longitudinal"]["difficulties"] == []
    assert history["longitudinal"]["strengths"] == []


def test_legacy_history_view_builds_from_journey_and_candidates():
    gateway = make_gateway(mode="legacy")
    history = gateway.history("S-LEG")
    assert history["mode"] == "standard"
    assert history["events"]
    assert history["tasks"][0]["feedback_summary"]
    assert history["tasks"][0]["versions"]


def test_wave2_submit_failure_surfaces_classified_error():
    legacy = FakeLegacyClient()
    gateway = make_gateway(mode="legacy", legacy_client=legacy)
    legacy.raise_on_submit = Wave2ApiUnavailable("wave2 unavailable")
    with pytest.raises(Wave2ApiUnavailable):
        gateway.submit_first({"task_id": None, "writing_prompt": "P", "writing_context": "cet4"}, "S1", ESSAY, "first draft")