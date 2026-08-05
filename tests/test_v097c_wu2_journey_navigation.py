"""v0.9.7-C WU2 focused tests: safe Journey navigation.

Covers the view-model action descriptors (open_revision / open_practice
with stable references only), the Journey navigation helpers (session
state carries references only), and the destination fail-safe guards on
the Revision and Practice pages (stale and cross-learner presets render an
honest note instead of silently opening another record). Every navigation
path is verified to perform zero writes and zero creations.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("LLM_PROVIDER", "local")

from fastapi.testclient import TestClient  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

from app.api.main import create_app  # noqa: E402
from app.config import Settings  # noqa: E402
from app.ui.locale import t  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "harness_v097a_student.py"
PROMPT = "Should cities add more parks?"

REPETITION_ESSAY = (
    "People should protect the environment. People should recycle more. "
    "People should save water. People should plant trees. People should reduce waste. "
    "People should use public transport. People should teach children about nature. "
    "People should value clean air."
)
REVISION_ESSAY = (
    "Citizens should protect the environment. Communities can recycle more."
)

PRIORITIES = [
    {
        "diagnosis_id": "D001",
        "category": "lexical_repetition",
        "evidence_quote": "Parks support public health.",
        "explanation": "The phrase 'public health' is repeated closely in the draft.",
        "revision_guidance": "Replace one repetition with a synonym.",
    },
]

SOURCE_CANDIDATE = {
    "essay_id": 28,
    "student_id": "S02",
    "writing_prompt": PROMPT,
    "genre": "argumentative essay",
    "draft_stage": "final draft",
    "timed": False,
    "time_limit_minutes": None,
    "tool_use": "none",
    "submitted_at": "2026-08-04T10:00:00+00:00",
    "revision_of_submission_id": None,
    "revision_group_id": None,
    "revision_sequence": None,
    "revision_stage": None,
    "original_draft_stage": None,
    "writing_started_at": None,
    "writing_submitted_at": None,
    "active_writing_duration_seconds": None,
    "timing_source": "unknown",
    "timing_quality": "unavailable",
    "unexplained_interruption": False,
}

SOURCE_BUNDLE = {
    "essay_id": 28,
    "student_id": "S02",
    "writing_prompt": PROMPT,
    "genre": "argumentative essay",
    "draft_stage": "final draft",
    "essay_text": "Parks support public health. Cities should protect accessible parks.",
    "submitted_at": "2026-08-04T10:00:00+00:00",
    "feedback": {"priority_feedback": PRIORITIES},
}

PRIORITY_TARGET = {
    "practice_target_id": "PT000001",
    "student_id": "S02",
    "source_submission_id": 28,
    "source_diagnosis_id": "D001",
    "source_priority_id": "PRIO-1-0",
    "target_code": "lexical_repetition_local",
    "target_label": "Reduce lexical repetition",
    "evidence_ids": ["1"],
    "status": "active",
    "created_at": "2026-01-01T00:00:00+00:00",
}

COMPLETED_TARGET = dict(
    PRIORITY_TARGET, status="completed", updated_at="2026-01-02T00:00:00+00:00")

OTHER_TARGET = dict(
    PRIORITY_TARGET, practice_target_id="PT000002",
    target_label="Vary sentence length", status="active")

TARGET_CONTEXT = {
    "context_status": "valid",
    "practice_target_id": "PT000001",
    "student_id": "S02",
    "source_submission_id": 28,
    "source_priority_id": "PRIO-1-0",
    "target_code": "lexical_repetition_local",
    "target_label": "Reduce lexical repetition",
    "status": "active",
    "priority_context": {
        "category": "lexical_repetition",
        "evidence_quote": "Parks support public health.",
        "explanation": "The phrase 'public health' is repeated closely in the draft.",
        "revision_guidance": "Replace one repetition with a synonym.",
    },
    "source_writing_text": "Parks support public health.",
}

EXERCISE = {
    "exercise_id": "EX000001",
    "practice_target_id": "PT000001",
    "student_id": "S02",
    "exercise_type": "sentence_rewrite",
    "created_at": "2026-01-01T00:00:01+00:00",
}

ATTEMPT = {
    "attempt_id": "EA000001",
    "exercise_id": "EX000001",
    "student_id": "S02",
    "attempt_number": 1,
    "response_text": "A valid response reducing repetition.",
    "status": "submitted",
    "created_at": "2026-01-01T00:00:02+00:00",
}

EVALUATION = {
    "evaluation_id": "PE000001",
    "attempt_id": "EA000001",
    "practice_target_id": "PT000001",
    "evaluation_method": "rule_based",
    "completion_status": "completed",
    "target_action_status": "candidate_detected",
    "evidence": ["Response length: 37 characters"],
    "confidence": "medium",
    "limitations": ["Task-specific only."],
    "evaluator_version": "practice-evaluator-v0.9.0",
    "created_at": "2026-01-01T00:00:03+00:00",
}


# --------------------------------------------------------------------------
# API-level view-model action tests
# --------------------------------------------------------------------------

def _settings(tmp_path) -> Settings:
    return Settings(
        database_path=tmp_path / "wu2.db", llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
    )


def _submit_essay(client, student_id: str, text: str,
                  draft_stage: str = "first draft",
                  revision_of: int | None = None) -> int:
    response = client.post("/api/v1/submissions", json={
        "student_id": student_id,
        "writing_prompt": "What actions matter for sustainability?",
        "genre": "argumentative essay", "draft_stage": draft_stage,
        "timed": False, "tool_use": "none", "essay_text": text,
        **({"revision_of_submission_id": revision_of} if revision_of else {}),
    })
    assert response.status_code == 201, response.text
    return response.json()["submission_id"]


def _create_target(client, student_id: str, essay_id: int) -> dict:
    record = client.app.state.repository._submission_repository.get_feedback_record(essay_id)
    priorities = json.loads(record["feedback_json"])["priority_feedback"]
    index = next(
        i for i, item in enumerate(priorities)
        if item.get("category") == "lexical_repetition")
    response = client.post("/api/v1/practice-targets", json={
        "student_id": student_id, "source_submission_id": essay_id,
        "priority_index": index,
    })
    assert response.status_code == 200, response.text
    return response.json()


def _legacy_target(client, student_id: str, essay_id: int) -> dict:
    record = client.app.state.repository._submission_repository.get_feedback_record(essay_id)
    priorities = json.loads(record["feedback_json"])["priority_feedback"]
    item = next(
        i for i in priorities if i.get("category") == "lexical_repetition")
    response = client.post("/api/v1/practice-targets", json={
        "student_id": student_id, "source_submission_id": essay_id,
        "source_diagnosis_id": item["diagnosis_id"],
        "target_code": "lexical_repetition_local",
        "target_label": "Reduce lexical repetition",
        "gate_status": "selected",
    })
    assert response.status_code == 200, response.text
    return response.json()


def _journey(client, student_id: str) -> dict:
    response = client.get(f"/api/v1/students/{student_id}/journey")
    assert response.status_code == 200, response.text
    return response.json()


class TestCycleActions:
    """WU2: view-model action descriptors with stable references."""

    @pytest.fixture()
    def client(self, tmp_path):
        with TestClient(create_app(_settings(tmp_path))) as client:
            yield client

    def test_full_cycle_exposes_safe_actions(self, client):
        essay_id = _submit_essay(client, "W2-ACT", REPETITION_ESSAY)
        target = _create_target(client, "W2-ACT", essay_id)
        revision_id = _submit_essay(client, "W2-ACT", REVISION_ESSAY,
                                    draft_stage="revised draft",
                                    revision_of=essay_id)
        cycle = _journey(client, "W2-ACT")["cycles"][0]
        actions = cycle["available_actions"]
        assert {"action": "open_revision", "submission_id": essay_id} in actions
        assert {"action": "open_revision", "submission_id": revision_id} in actions
        assert {"action": "open_practice",
                "practice_target_id": target["practice_target_id"]} in actions
        assert all(action["action"] in ("open_revision", "open_practice")
                   for action in actions)

    def test_no_feedback_cycle_has_no_revision_action(self, client):
        essay_id = _submit_essay(client, "W2-NOFB", REPETITION_ESSAY)
        with client.app.state.repository.connect() as conn:
            conn.execute(
                "DELETE FROM feedback_records WHERE essay_id=?", (essay_id,))
        cycle = _journey(client, "W2-NOFB")["cycles"][0]
        assert cycle["available_actions"] == []

    def test_insufficient_evidence_cycle_has_no_actions(self, client):
        import sqlite3
        path = str(client.app.state.settings.database_path)
        with sqlite3.connect(path) as raw:
            raw.execute(
                "INSERT OR IGNORE INTO students (student_id, created_at, "
                "is_synthetic) VALUES ('W2-IE', '2026-08-01T00:00:00+00:00', 1)")
            raw.execute(
                """INSERT INTO essays(
                    student_id, writing_prompt, genre, draft_stage, timed,
                    tool_use, essay_text, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                ("W2-IE", "Should we act?", "argumentative essay",
                 "first draft", 0, "none", "A raw essay row.",
                 "2026-08-01T00:00:00+00:00"))
            raw.commit()
        cycle = _journey(client, "W2-IE")["cycles"][0]
        assert cycle["available_actions"] == []

    def test_legacy_target_action_exposed(self, client):
        essay_id = _submit_essay(client, "W2-LEG", REPETITION_ESSAY)
        target = _legacy_target(client, "W2-LEG", essay_id)
        cycle = _journey(client, "W2-LEG")["cycles"][0]
        assert {"action": "open_practice",
                "practice_target_id": target["practice_target_id"]} in \
            cycle["available_actions"]

    def test_unlinked_practice_target_action_exposed(self, client):
        _submit_essay(client, "W2-UNL", REPETITION_ESSAY)
        essay_id = _submit_essay(client, "W2-UNL", REPETITION_ESSAY)
        target = _create_target(client, "W2-UNL", essay_id)
        with client.app.state.repository.connect() as conn:
            row = conn.execute(
                "SELECT target_json FROM practice_targets "
                "WHERE practice_target_id=?", (target["practice_target_id"],)
            ).fetchone()
            payload = json.loads(row[0])
            payload["source_submission_id"] = 999999
            conn.execute(
                "UPDATE practice_targets SET source_submission_id=999999, "
                "target_json=? WHERE practice_target_id=?",
                (json.dumps(payload), target["practice_target_id"]))
        data = _journey(client, "W2-UNL")
        unlinked = next(
            c for c in data["cycles"]
            if c["cycle_id"] == "cycle-unlinked-practice")
        assert {"action": "open_practice",
                "practice_target_id": target["practice_target_id"]} in \
            unlinked["available_actions"]

    def test_no_feedback_action_is_ever_exposed(self, client):
        essay_id = _submit_essay(client, "W2-NOACT", REPETITION_ESSAY)
        _create_target(client, "W2-NOACT", essay_id)
        data = _journey(client, "W2-NOACT")
        for cycle in data["cycles"]:
            for action in cycle["available_actions"]:
                assert "feedback" not in action["action"]


# --------------------------------------------------------------------------
# Navigation helper tests
# --------------------------------------------------------------------------

NAVIGATION_SCRIPT = """
import streamlit as st
from app.ui.features.student.navigation import (
    _navigate_journey_practice,
    _navigate_journey_revision,
)

mode = st.session_state.get("probe_mode")
if mode == "revision":
    _navigate_journey_revision(
        int(st.session_state["probe_source"]), "en")
elif mode == "practice":
    _navigate_journey_practice(
        str(st.session_state["probe_target"]), "en")
st.write(st.session_state.get("sidebar_page", ""))
"""


class TestNavigationHelpers:
    """WU2: helpers carry stable references only."""

    def test_journey_revision_helper_sets_stable_reference(self):
        at = AppTest.from_string(NAVIGATION_SCRIPT, default_timeout=30)
        at.session_state["probe_mode"] = "revision"
        at.session_state["probe_source"] = 28
        at.run()
        assert not at.exception, at.exception
        assert at.session_state["revision_source_preset"] == 28
        assert at.session_state["sidebar_page"] == t("student_revision_title", "en")

    def test_journey_practice_helper_sets_stable_reference_and_clears_intent(self):
        at = AppTest.from_string(NAVIGATION_SCRIPT, default_timeout=30)
        at.session_state["probe_mode"] = "practice"
        at.session_state["probe_target"] = "PT000001"
        at.session_state["practice_source_submission_id"] = 28
        at.session_state["practice_priority_index"] = 0
        at.run()
        assert not at.exception, at.exception
        assert at.session_state["practice_target_preset"] == "PT000001"
        assert "practice_source_submission_id" not in at.session_state
        assert "practice_priority_index" not in at.session_state
        assert at.session_state["sidebar_page"] == t("practice", "en")


# --------------------------------------------------------------------------
# Destination guard tests (AppTest harness)
# --------------------------------------------------------------------------

def _run_harness(**config):
    at = AppTest.from_file(str(HARNESS), default_timeout=90)
    for key, value in config.items():
        at.session_state[key] = json.loads(json.dumps(value))
    at.run()
    assert not at.exception, at.exception
    return at


def _markdown_text(at) -> str:
    return " ".join(m.value for m in at.markdown)


def _button_labels(at) -> dict:
    return {button.key: button.label for button in at.button}


def _fake_client(at):
    return at.session_state["fake_client"]


class TestRevisionDestinationGuard:
    """WU2: Revision destination accepts only resolvable presets."""

    def test_valid_preset_opens_requested_source_without_writes(self):
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="S02",
            revision_source_preset=28,
            harness_candidates=[SOURCE_CANDIDATE],
            harness_source_bundle=SOURCE_BUNDLE,
        )
        text = _markdown_text(at)
        assert t("student_revision_priority_task", "en") in text
        assert "revision_submit_primary" in _button_labels(at)
        assert "revision_source_preset" not in at.session_state
        client = _fake_client(at)
        assert client.revision_post_count == 0
        assert client.post_count == 0
        assert client.target_create_count == 0
        assert client.attempt_post_count == 0
        assert client.complete_count == 0

    def test_stale_preset_fails_safely_with_note(self):
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="S02",
            revision_source_preset=999,
            harness_candidates=[SOURCE_CANDIDATE],
            harness_source_bundle=SOURCE_BUNDLE,
        )
        assert t("student_revision_preset_invalid", "en") in _markdown_text(at)
        assert "revision_source_preset" not in at.session_state
        assert _fake_client(at).revision_post_count == 0

    def test_cross_learner_preset_fails_safely_with_note(self):
        # The preset references a source that is not among this learner's
        # candidates (learner-scoped API response).
        at = _run_harness(
            sidebar_page=t("student_revision_title", "en"),
            selected_student_id="S02",
            revision_source_preset=77,
            harness_candidates=[SOURCE_CANDIDATE],
            harness_source_bundle=SOURCE_BUNDLE,
        )
        assert t("student_revision_preset_invalid", "en") in _markdown_text(at)
        assert _fake_client(at).revision_post_count == 0


class TestPracticeDestinationGuard:
    """WU2: Practice destination opens learner-owned targets only."""

    def test_valid_active_preset_opens_target_and_creates_nothing(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            practice_target_preset="PT000001",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=TARGET_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        text = _markdown_text(at)
        assert "Reduce lexical repetition" in text
        assert "practice_submit" in _button_labels(at)
        assert "practice_target_preset" not in at.session_state
        client = _fake_client(at)
        assert client.target_create_count == 0
        assert client.attempt_post_count == 0
        assert client.complete_count == 0

    def test_valid_completed_preset_keeps_completed_state(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            practice_target_preset="PT000001",
            harness_targets=[COMPLETED_TARGET],
            harness_target_context=TARGET_CONTEXT,
            harness_exercises=[EXERCISE],
            harness_attempts=[ATTEMPT],
            harness_evaluations=[EVALUATION],
        )
        text = _markdown_text(at)
        assert t("student_practice_completed_title", "en") in text
        assert t("student_practice_completed_saved", "en") in text
        assert "EA000001" in text
        assert "practice_finish" not in _button_labels(at)

    def test_stale_preset_fails_safely_with_note(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            practice_target_preset="PT999999",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=TARGET_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        assert t("student_practice_preset_invalid", "en") in _markdown_text(at)
        # The deterministic oldest-active rule still renders an honest page.
        assert "Reduce lexical repetition" in _markdown_text(at)
        client = _fake_client(at)
        assert client.target_create_count == 0
        assert client.attempt_post_count == 0

    def test_cross_learner_preset_fails_safely_with_note(self):
        foreign = dict(PRIORITY_TARGET, student_id="S99")
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            practice_target_preset="PT000001",
            harness_targets=[foreign],
        )
        assert t("student_practice_preset_invalid", "en") in _markdown_text(at)
        assert _fake_client(at).target_create_count == 0

    def test_rerun_keeps_journey_selection_stable(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            practice_target_preset="PT000001",
            harness_targets=[PRIORITY_TARGET, OTHER_TARGET],
            harness_target_context=TARGET_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        assert "Reduce lexical repetition" in _markdown_text(at)
        at.run()
        assert not at.exception, at.exception
        text = _markdown_text(at)
        assert "Reduce lexical repetition" in text
        assert "Vary sentence length" not in text

    def test_navigation_renders_perform_zero_writes(self):
        at = _run_harness(
            sidebar_page=t("practice", "en"),
            selected_student_id="S02",
            practice_target_preset="PT999999",
            harness_targets=[PRIORITY_TARGET],
            harness_target_context=TARGET_CONTEXT,
            harness_exercises=[EXERCISE],
        )
        client = _fake_client(at)
        assert client.post_count == 0
        assert client.revision_post_count == 0
        assert client.target_create_count == 0
        assert client.attempt_post_count == 0
        assert client.complete_count == 0
