"""Wave-2 Goal C -- two-level writing task model tests (TDD red phase).

The five-type task_type taxonomy must remain unchanged from the qualified
L2 taxonomy contract (``l2-task-type-taxonomy-v1.0.0``, Domain Pack v1);
writing_context/genre is a separate second level with optional metadata.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.l2.wave2.models import (
    LEGACY_UNCLASSIFIED,
    TASK_TYPE_IDS,
    WRITING_CONTEXT_IDS,
    WritingTask,
    WritingTaskMetadata,
)
from app.shared.task_type_registry import default_task_type_registry


class TestTaskTypeTaxonomyUnchanged:
    def test_five_types_match_registry_l2_namespace(self) -> None:
        registry = default_task_type_registry()
        registry_ids = {
            entry.task_type_id for entry in registry.list_namespace("l2")
        }
        assert set(TASK_TYPE_IDS) == registry_ids - {LEGACY_UNCLASSIFIED}
        assert sorted(TASK_TYPE_IDS) == [
            "argumentative", "discussion", "general_eap", "opinion",
            "problem_solution",
        ]
        assert LEGACY_UNCLASSIFIED in registry_ids

    def test_writing_contexts_cover_required_genres(self) -> None:
        assert set(WRITING_CONTEXT_IDS) == {
            "cet4", "cet6", "ielts_task2", "toefl_style", "course_essay",
            "email", "application", "reflective_journal", "other",
        }


class TestWritingTaskModel:
    def _task(self, **overrides) -> WritingTask:
        values = dict(
            task_id="WT000001",
            student_id="L-RETURN-01",
            task_type="argumentative",
            writing_context="ielts_task2",
            writing_prompt="Take a position on studying abroad and support it with reasons.",
            metadata=WritingTaskMetadata(
                audience="IELTS examiner",
                purpose="persuade the reader",
                word_constraint="at least 250 words",
                assessment_environment="timed exam",
                genre_expectations=["clear position", "reasons and examples"],
            ),
        )
        values.update(overrides)
        return WritingTask(**values)

    def test_task_round_trip_with_metadata(self) -> None:
        task = self._task()
        assert task.task_type == "argumentative"
        assert task.writing_context == "ielts_task2"
        assert task.writing_prompt.startswith("Take a position")
        assert task.metadata.audience == "IELTS examiner"
        assert task.metadata.word_constraint == "at least 250 words"
        assert task.metadata.genre_expectations == ["clear position", "reasons and examples"]
        assert task.modality == "written"
        assert task.status == "active"

    def test_legacy_unclassified_sentinel_allowed(self) -> None:
        task = self._task(task_type=LEGACY_UNCLASSIFIED)
        assert task.task_type == LEGACY_UNCLASSIFIED

    def test_unknown_task_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._task(task_type="persuasive_essay")

    def test_unknown_writing_context_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._task(writing_context="b2_essay")

    def test_blank_prompt_rejected(self) -> None:
        with pytest.raises(ValidationError):
            self._task(writing_prompt="   ")

    def test_optional_metadata_defaults_empty(self) -> None:
        task = self._task(metadata=WritingTaskMetadata())
        assert task.metadata.audience is None
        assert task.metadata.purpose is None
        assert task.metadata.genre_expectations == []
