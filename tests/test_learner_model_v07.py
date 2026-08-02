from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.configuration import ConfigurationPayload
from app.database import Database, LATEST_MIGRATION_VERSION
from app.services.learner_model import LearnerModelEngine
from app.core import HistoryEvidenceRecord, LearningTarget
from app.models import HistoryEvidence, HistoryResult
from app.prompts import PromptBuilder
from app.llm import FeedbackContext
from app.analyzer import BasicAnalyzer
from app.diagnosis import HeuristicDiagnoser
from app.models import EssaySubmission
from app.services import ProgressService
from tests.test_longitudinal_v03 import FakeRepository, record as legacy_record


FIXTURE = Path(__file__).parent / "fixtures" / "learner_model_v07" / "cases_a_i.json"


def signal(category="lexical_repetition", status="selected_priority", verified=True):
    return {
        "diagnosis_id": "D001", "category": category,
        "selection_status": status,
        "evidence_relevance_status": "verified" if verified else "insufficient_evidence",
    }


def record(index, *, genre="argumentative essay", tool="none", analyzer="spacy-analyzer-v0.6.1",
           selected=False, suppressed=False, group=None, stage="independent_submission", metric=0.5):
    calibration = {
        "diagnosis_version": "prototype-diagnosis-v0.6.1",
        "selected_priorities": [signal()] if selected else [],
        "eligible_diagnoses": [signal(status="eligible_diagnosis")] if selected else [],
        "monitored_signals": [],
        "suppressed_diagnostics": [signal(status="suppressed", verified=False)] if suppressed else [],
        "verified_strengths": [],
    }
    return {
        "essay_id": index, "student_id": "LM07", "submitted_at": datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index),
        "genre": genre, "writing_prompt": f"Argument task {index}", "draft_stage": stage,
        "timed": True, "time_limit_minutes": 45, "tool_use": tool,
        "revision_group_id": group, "revision_sequence": index if group else None,
        "analysis_version": analyzer, "analyzer_version": analyzer,
        "analysis_run_id": f"AR{index:06d}", "diagnosis_version": "prototype-diagnosis-v0.6.1",
        "metrics": {"mattr": metric},
        "versioned_metrics": {"mattr": {"value": metric, "metric_version": "0.6.1",
            "status": "available", "confidence": "medium", "eligible_for_longitudinal_comparison": True}},
        "diagnosis": {"improvement_priorities": []}, "diagnostic_calibration": calibration,
    }


def build(records):
    engine = LearnerModelEngine(ConfigurationPayload())
    representatives, excluded = engine.choose_representatives(records)
    clusters = engine.task_clusters("LM07", representatives)
    return engine, representatives, excluded, clusters


def test_case_fixture_is_versioned_and_complete():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert payload["fixture_version"] == "learner-model-regression-v0.7.0"
    assert set(payload["cases"]) == set("ABCDEFGHI")


def test_case_a_one_task_is_insufficient_and_no_persistent_pattern():
    engine, reps, excluded, clusters = build([record(1, selected=True)])
    assert engine.data_sufficiency(reps, reps, excluded, clusters).status == "insufficient"
    assert all(item.status != "persistent_pattern" for item in engine.diagnostic_trajectories(clusters, reps))
    assert all(item.trend_status == "insufficient" for item in engine.metric_trajectories(clusters, reps))


def test_case_b_two_tasks_are_pairwise_not_a_trend():
    engine, reps, _, clusters = build([record(1, metric=.4), record(2, metric=.6)])
    item = engine.metric_trajectories(clusters, reps)[0]
    assert item.trend_status == "limited_pairwise_comparison"
    assert item.direction == "insufficient_data" and item.pairwise_difference == .2


def test_case_c_selected_current_pattern_is_persistent_by_versioned_rule():
    rows = [record(1, selected=True), record(2), record(3, selected=True)]
    engine, reps, _, clusters = build(rows)
    trajectory = engine.diagnostic_trajectories(clusters, reps)[0]
    assert trajectory.status == "persistent_pattern"
    targets, evidence = engine.targets_and_evidence([trajectory], reps)
    assert len(targets) == len(evidence) == 1


def test_case_d_suppressed_current_signal_never_becomes_current_target():
    rows = [record(1, selected=True), record(2, selected=True), record(3, suppressed=True)]
    engine, reps, _, clusters = build(rows)
    trajectories = engine.diagnostic_trajectories(clusters, reps)
    assert trajectories[0].status in {"emerging_pattern", "recently_reduced_signal"}
    assert engine.targets_and_evidence(trajectories, reps)[0] == []


def test_case_e_revision_group_contributes_one_representative_by_default():
    rows = [record(1, group="RG000001", stage="first_draft"),
            record(2, group="RG000001", stage="revised_draft"),
            record(3, group="RG000001", stage="final_draft")]
    _, reps, excluded, _ = build(rows)
    assert [item["essay_id"] for item in reps] == [3]
    assert len(excluded) == 2


def test_case_f_g_h_genre_tool_and_analyzer_are_not_silently_joined():
    variants = [
        [record(1), record(2, genre="expository essay")],
        [record(1), record(2, tool="AI-assisted")],
        [record(1), record(2, analyzer="basic-analyzer-v0.1")],
    ]
    for rows in variants:
        engine, reps, _, clusters = build(rows)
        assert len(clusters) == 2
        assert all(len(item.representative_submission_ids) == 1 for item in clusters)


def test_case_i_zero_current_targets_is_valid():
    engine, reps, _, clusters = build([record(1), record(2), record(3)])
    trajectories = engine.diagnostic_trajectories(clusters, reps)
    assert engine.targets_and_evidence(trajectories, reps) == ([], [])


def test_three_points_create_provisional_direction_with_traceable_points():
    engine, reps, _, clusters = build([record(1, metric=.4), record(2, metric=.5), record(3, metric=.6)])
    item = engine.metric_trajectories(clusters, reps)[0]
    assert item.trend_status == "provisional_pattern"
    assert item.direction == "increasing_signal"
    assert [point.analysis_run_id for point in item.data_points] == ["AR000001", "AR000002", "AR000003"]


def test_migration_8_is_additive_and_activates_v07_configuration(tmp_path):
    database = Database(tmp_path / "v07.db"); database.initialize()
    assert database.migration_version() == LATEST_MIGRATION_VERSION == 12
    with database.connect() as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        columns = {row[1] for row in connection.execute("PRAGMA table_info(learner_profile_snapshots)")}
    assert "history_evidence_registry" in tables
    assert {"profile_version", "source_submission_ids_json", "representative_submission_ids_json"} <= columns
    active = database.get_active_configuration()
    assert active.version == "config-v0.9.0"
    assert active.parent_version and active.payload.representative_draft_strategy == "final_or_latest"


def test_learner_model_api_routes_are_documented(tmp_path):
    database = Database(tmp_path / "api.db")
    api = create_app(repository=database)
    client = TestClient(api)
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    for suffix in ("", "/task-clusters", "/metric-trajectories", "/diagnostic-trajectories",
                   "/learning-targets", "/history-evidence", "/snapshots",
                   "/snapshots/{snapshot_id}", "/preview", "/rebuild"):
        assert f"/api/v1/students/{{student_id}}/learner-model{suffix}" in paths


def test_feedback_context_screens_history_to_current_target_evidence_only():
    repository = FakeRepository([legacy_record(1, 100)])
    snapshot = ProgressService(repository, repository).create_snapshot("S001", persist=False)
    evidence = [
        HistoryEvidenceRecord(
            history_evidence_id=f"HE00000{index}", student_id="S001",
            evidence_type="diagnostic_trajectory", source_submission_ids=["E000001"],
            task_cluster_id="TC001", evidence_text=f"Evidence {index}",
            evidence_status="verified", version_compatibility="compatible", confidence="low",
        ) for index in (1, 2)
    ]
    target = LearningTarget(
        target_id="LT001", category="essay_length", status="active",
        source_trajectory_id="DTL001", supporting_submission_ids=["E000001"],
        history_evidence_ids=["HE000001"], current_evidence_id="D001",
        selection_reason="Current verified Gate selection.", confidence="low", priority=1,
    )
    snapshot = snapshot.model_copy(update={"history_evidence": evidence, "current_learning_targets": [target]})
    submission = EssaySubmission(
        student_id="S001", writing_prompt="Should parks be protected?",
        essay_text="Parks should be protected because they support public health and shared community activities.",
    )
    analysis = BasicAnalyzer().analyze(submission.essay_text)
    diagnosis = HeuristicDiagnoser().diagnose(analysis)
    history = HistoryResult(
        comparability_status="comparable", comparable_submission_count=2,
        history_evidence=[
            HistoryEvidence(history_evidence_id="H001", evidence_type="metric_change",
                            description="Unrelated legacy evidence.", supporting_submission_ids=["E000001"],
                            comparable_submission_count=1, confidence="low", limitation="prototype"),
            *[HistoryEvidence(
                history_evidence_id=item.history_evidence_id, evidence_type="diagnostic_trajectory",
                description=item.evidence_text, supporting_submission_ids=item.source_submission_ids,
                comparable_submission_count=1, confidence="low", limitation="prototype",
            ) for item in evidence],
        ], summary="Mixed history.", limitations=["prototype"], comparability_reasons=["same task class"],
    )
    bundle = PromptBuilder().build(FeedbackContext(
        submission, analysis, diagnosis, history, snapshot, None,
        {"selected_priorities": [], "exercise_generation": {}},
    ))
    payload = json.loads(bundle.messages[1]["content"])
    assert bundle.prompt_version == "feedback-prompt-v0.7.0"
    assert [item["history_evidence_id"] for item in payload["learner_history"]["history_evidence"]] == ["HE000001"]
    assert [item["history_evidence_id"] for item in payload["learner_model_context"]["relevant_history_evidence"]] == ["HE000001"]
    assert "suppressed_diagnostics" not in json.dumps(payload["learner_model_context"])
