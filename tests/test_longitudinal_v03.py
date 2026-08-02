from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from app.config.longitudinal import METRIC_NAMES, RULES
from app.core import LearnerProfileSnapshot
from app.services import BaselineService, ComparabilityService, ProgressService


def record(
    essay_id: int,
    word_count: float,
    *,
    student_id: str = "S001",
    genre: str = "argumentative essay",
    prompt: str = "Should cities protect public parks?",
    timed: bool = False,
    tool_use: str = "none",
    draft_stage: str = "first draft",
    category: str | None = None,
    analysis_version: str = "basic-analyzer-v0.1",
    diagnosis_version: str = "prototype-diagnosis-v0.1.1",
):
    metrics = {
        "word_count": word_count, "sentence_count": word_count / 10,
        "paragraph_count": 3, "average_sentence_length": 10,
        "unique_word_count": word_count * 0.7, "type_token_ratio": 0.7,
        "connective_count": word_count / 30, "repeated_content_words": {},
    }
    diagnosis = {"improvement_priorities": ([] if category is None else [{"category": category}])}
    return {
        "essay_id": essay_id, "student_id": student_id, "writing_prompt": prompt,
        "genre": genre, "draft_stage": draft_stage, "timed": timed,
        "time_limit_minutes": 30 if timed else None, "tool_use": tool_use,
        "essay_text": "Valid synthetic essay text.",
        "submitted_at": datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=essay_id * 14),
        "metrics": metrics, "analysis_version": analysis_version,
        "diagnosis": diagnosis, "diagnosis_version": diagnosis_version,
    }


class FakeRepository:
    def __init__(self, records): self.records, self.snapshots = records, []
    def list_visualization_records(self, student_id): return [deepcopy(x) for x in self.records if x["student_id"] == student_id]
    def save_learner_profile_snapshot(self, snapshot):
        stored = snapshot.model_copy(update={"snapshot_id": f"LP{len(self.snapshots)+1:06d}"})
        self.snapshots.append(stored.model_dump(mode="json")); return stored
    def get_latest_learner_profile(self, student_id):
        matches = [x for x in self.snapshots if x["student_id"] == student_id]
        return matches[-1] if matches else None
    def list_learner_profile_snapshots(self, student_id): return [x for x in self.snapshots if x["student_id"] == student_id]
    def get_active_configuration(self): raise RuntimeError("No active configuration in focused stub.")


def progress_service(repository):
    return ProgressService(repository, repository)


def comparisons(records):
    service = ComparabilityService(); current = records[-1]
    return {f"E{x['essay_id']:06d}": service.compare(current, x) for x in records[:-1]}


def test_same_conditions_are_comparable_and_rule_is_saved():
    result = ComparabilityService().compare(record(2, 110), record(1, 100))
    assert result.status == "comparable"
    assert result.reasons and result.rule_version == RULES.rule_version


@pytest.mark.parametrize("change,field", [
    ({"timed": True, "time_limit_minutes": 30}, "timed"),
    ({"tool_use": "dictionary"}, "tool_use"),
    ({"draft_stage": "revised draft"}, "draft_stage"),
])
def test_task_condition_mismatch_is_recorded(change, field):
    current = record(2, 100); current.update(change)
    result = ComparabilityService().compare(current, record(1, 100))
    assert result.status == "partially_comparable" and field in result.mismatched_conditions


def test_different_student_and_genre_are_not_comparable():
    service = ComparabilityService()
    assert service.compare(record(2, 100, student_id="B"), record(1, 100, student_id="A")).status == "not_comparable"
    result = service.compare(record(2, 100, genre="narrative essay"), record(1, 100))
    assert result.status == "not_comparable" and "genre" in result.mismatched_conditions


def test_prompt_and_word_count_differences_create_limits():
    current = record(2, 300, prompt="Describe a memorable journey abroad")
    result = ComparabilityService().compare(current, record(1, 80))
    assert result.status == "partially_comparable"
    assert {"writing_prompt_or_task_family", "word_count_range"} <= set(result.mismatched_conditions)
    assert len(result.reasons) >= 2


def test_time_limit_interval_and_analysis_version_limits_are_explicit():
    old = record(1, 100, timed=True, analysis_version="v1")
    current = record(2, 110, timed=True, analysis_version="v2")
    current["time_limit_minutes"] = 45
    current["submitted_at"] = old["submitted_at"] + timedelta(minutes=20)
    result = ComparabilityService().compare(current, old)
    assert result.status == "partially_comparable"
    assert {"time_limit_minutes", "submission_interval", "analysis_version"} <= set(result.mismatched_conditions)
    assert any("versions differ" in reason for reason in result.reasons)


def test_missing_metrics_is_insufficient_information():
    old = record(1, 100); old["metrics"] = {}
    result = ComparabilityService().compare(record(2, 100), old)
    assert result.status == "insufficient_information" and result.confidence == "insufficient"


def test_baseline_requires_three_and_excludes_noncomparable():
    records = [record(1, 100), record(2, 110)]
    baseline = BaselineService().build("S001", records, comparisons(records), "E000002")
    assert baseline.baseline_status == "insufficient_history" and not baseline.metric_summaries
    records.append(record(3, 120))
    available = BaselineService().build("S001", records, comparisons(records), "E000003")
    assert available.baseline_status == "available" and len(available.included_submission_ids) == 3
    mixed = [record(1, 100, genre="narrative essay"), record(2, 110), record(3, 120)]
    excluded = BaselineService().build("S001", mixed, comparisons(mixed), "E000003")
    assert "E000001" in excluded.excluded_submission_ids


@pytest.mark.parametrize("values,expected", [
    ([100, 120, 150, 180], "increasing"),
    ([180, 150, 120, 100], "decreasing"),
    ([100, 101, 99, 100], "stable"),
    ([100, 190, 105, 180], "fluctuating"),
])
def test_transparent_trend_directions(values, expected):
    service = progress_service(FakeRepository([record(i + 1, value) for i, value in enumerate(values)]))
    trend = service.create_snapshot("S001", persist=False).metric_trends["word_count"]
    assert trend.direction == expected
    if expected == "fluctuating": assert trend.variability == "high" and trend.confidence == "low"


def test_trend_insufficient_exclusion_and_length_limit():
    insufficient = progress_service(FakeRepository([record(1, 100), record(2, 120)])).create_snapshot("S001", persist=False)
    assert insufficient.metric_trends["word_count"].direction == "insufficient_data"
    mixed = [record(1, 50, genre="narrative essay"), record(2, 100), record(3, 120), record(4, 150)]
    snapshot = progress_service(FakeRepository(mixed)).create_snapshot("S001", persist=False)
    assert "E000001" not in snapshot.metric_trends["word_count"].included_submission_ids
    assert any("text length" in x.casefold() for x in snapshot.metric_trends["type_token_ratio"].limitations)
    rendered = snapshot.model_dump_json().casefold()
    assert "cefr" not in rendered and "overall ability score" not in rendered


def test_partially_comparable_records_only_enter_when_requested():
    records = [record(1, 100, tool_use="dictionary"), record(2, 120), record(3, 140)]
    strict = progress_service(FakeRepository(records)).create_snapshot("S001", persist=False)
    inclusive = progress_service(FakeRepository(records)).create_snapshot("S001", comparable_only=False, persist=False)
    assert "E000001" not in strict.metric_trends["word_count"].included_submission_ids
    assert "E000001" in inclusive.metric_trends["word_count"].included_submission_ids


def test_issue_persistent_recurring_and_recently_reduced():
    persistent = [record(i, 100 + i, category="lexical_repetition") for i in range(1, 5)]
    p = progress_service(FakeRepository(persistent)).create_snapshot("S001", persist=False)
    assert p.persistent_issues[0].status == "persistent"
    recurring = [record(1, 100, category="lexical_repetition"), record(2, 105), record(3, 110, category="lexical_repetition")]
    r = progress_service(FakeRepository(recurring)).create_snapshot("S001", persist=False)
    assert r.unstable_issues[0].status == "recurring"
    reduced = [record(1, 100, category="lexical_repetition"), record(2, 105, category="lexical_repetition"), record(3, 110), record(4, 115)]
    x = progress_service(FakeRepository(reduced)).create_snapshot("S001", persist=False)
    assert x.recently_reduced_issues[0].status == "recently_reduced"
    assert x.recently_reduced_issues[0].supporting_submission_ids == ["E000001", "E000002"]


def test_one_absence_is_not_reduced_and_version_change_lowers_confidence():
    records = [record(1, 100, category="lexical_repetition"), record(2, 110, category="lexical_repetition"), record(3, 120)]
    snapshot = progress_service(FakeRepository(records)).create_snapshot("S001", persist=False)
    assert not snapshot.recently_reduced_issues
    changed = [record(i, 100 + i, category="lexical_repetition", diagnosis_version=("v1" if i < 4 else "v2")) for i in range(1, 5)]
    issue = progress_service(FakeRepository(changed)).create_snapshot("S001", persist=False).persistent_issues[0]
    assert issue.confidence == "low" and any("versions differ" in x for x in issue.limitations)


def test_snapshot_versions_priorities_and_recalculation_append():
    repository = FakeRepository([record(i, 100 + i * 20, category="lexical_repetition") for i in range(1, 5)])
    service = progress_service(repository)
    first = service.create_snapshot("S001")
    second = service.create_snapshot("S001")
    assert first.snapshot_id != second.snapshot_id and len(repository.snapshots) == 2
    assert second.configuration_version == RULES.configuration_version
    assert second.analysis_version == RULES.analysis_version
    assert second.included_submission_ids == ["E000001", "E000002", "E000003", "E000004"]
    assert len(second.current_priority_candidates) <= 3
