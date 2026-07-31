from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config import Settings
from app.database import Database
from app.models import AnalysisResult, DiagnosisResult, DiagnosisSignal, EssaySubmission


def seed(repository: Database, student: str, values: list[int], *, genre="argumentative essay"):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index, value in enumerate(values):
        essay_id = repository.save_essay(EssaySubmission(
            student_id=student, writing_prompt="Should cities protect public parks?",
            genre=genre, draft_stage="first draft", timed=False, tool_use="none",
            essay_text="Synthetic essay text supports transparent testing.",
            submitted_at=start + timedelta(days=index * 14),
        ), synthetic=True)
        repository.save_analysis(essay_id, AnalysisResult(
            metrics={
                "word_count": value, "sentence_count": value / 10, "paragraph_count": 3,
                "average_sentence_length": 10, "unique_word_count": value * .7,
                "type_token_ratio": .7, "connective_count": value / 30,
                "repeated_content_words": {},
            }, analysis_version="basic-analyzer-v0.1", limitations="prototype",
        ))
        repository.save_diagnosis(essay_id, DiagnosisResult(
            strengths=[], improvement_priorities=[DiagnosisSignal(
                diagnosis_id="D001", category="lexical_repetition", evidence="prototype",
                source_metrics=["repeated_content_words"], interpretation="May warrant review.",
                confidence="low", limitation="prototype", rule_version="prototype-diagnosis-v0.1.1",
                kind="improvement",
            )], diagnosis_version="prototype-diagnosis-v0.1.1", limitation="prototype",
        ))


def client_and_repository(tmp_path):
    settings = Settings(
        database_path=tmp_path / "longitudinal-api.db", llm_provider="local",
        deepseek_api_key=None, deepseek_base_url="https://example.invalid", deepseek_model="demo",
    )
    repository = Database(settings.database_path); repository.initialize()
    return TestClient(create_app(settings, repository=repository)), repository


def test_progress_and_profile_api_success_and_queries(tmp_path):
    client, repository = client_and_repository(tmp_path)
    seed(repository, "LONG001", [100, 120, 145, 170])
    with client:
        progress = client.get("/api/v1/students/LONG001/progress?metric=word_count&comparable_only=true")
        assert progress.status_code == 200
        body = progress.json()
        assert body["analysis_version"] == "longitudinal-v0.3.0"
        assert list(body["metric_trends"]) == ["word_count"]
        assert body["metric_trends"]["word_count"]["direction"] == "increasing"
        profile = client.get("/api/v1/students/LONG001/profile")
        assert profile.status_code == 200
        assert profile.json()["comparable_submission_count"] == 4
        assert profile.json()["latest_snapshot"]["snapshot_id"].startswith("LP")
        filtered = client.get(
            "/api/v1/students/LONG001/progress?metric=word_count&start_date=2026-01-15&analysis_version=basic-analyzer-v0.1"
        )
        assert filtered.status_code == 200
        assert filtered.json()["metric_trends"]["word_count"]["data_points"] == 3


def test_insufficient_history_and_unknown_student(tmp_path):
    client, repository = client_and_repository(tmp_path)
    seed(repository, "SHORT001", [100, 110])
    with client:
        response = client.get("/api/v1/students/SHORT001/progress")
        assert response.status_code == 200
        assert response.json()["baseline_status"] == "insufficient_history"
        assert all(item["direction"] == "insufficient_data" for item in response.json()["metric_trends"].values())
        assert client.get("/api/v1/students/MISSING/progress").status_code == 404
        assert client.get("/api/v1/students/MISSING/profile").status_code == 404


def test_progress_query_validation_and_error_shape(tmp_path):
    client, repository = client_and_repository(tmp_path)
    seed(repository, "QUERY001", [100, 110, 120])
    with client:
        invalid_metric = client.get("/api/v1/students/QUERY001/progress?metric=overall_score")
        assert invalid_metric.status_code == 422
        assert invalid_metric.json()["error"]["category"] in ("invalid_request", "validation_error")
        invalid_range = client.get("/api/v1/students/QUERY001/progress?start_date=2026-03-01&end_date=2026-01-01")
        assert invalid_range.status_code == 422 and invalid_range.json()["error"]["category"] in ("invalid_request", "request_error")
        no_version = client.get("/api/v1/students/QUERY001/progress?analysis_version=missing")
        assert no_version.status_code == 422


def test_api_omits_proficiency_scores_cefr_and_prompt_text(tmp_path):
    client, repository = client_and_repository(tmp_path)
    seed(repository, "SAFE001", [100, 120, 140])
    with client:
        text = client.get("/api/v1/students/SAFE001/progress").text.casefold()
        assert '"cefr"' not in text
        assert '"overall_score"' not in text and '"proficiency_score"' not in text
        assert "should cities protect public parks" not in text
        assert "deepseek_api_key" not in text


def test_three_api_submissions_feed_filtered_snapshot_evidence_to_feedback(tmp_path):
    client, repository = client_and_repository(tmp_path)
    base = {
        "student_id": "LLMSNAP01", "writing_prompt": "Should cities protect public parks?",
        "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
        "time_limit_minutes": None, "tool_use": "none",
        "essay_text": "Cities should protect parks because parks support health. Therefore, leaders should preserve green space.",
    }
    with client:
        bodies = []
        for index in range(3):
            payload = {**base, "submitted_at": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index * 14)).isoformat()}
            response = client.post("/api/v1/submissions", json=payload)
            assert response.status_code == 201
            bodies.append(response.json())
        third = bodies[-1]
        evidence = third["history"]["history_evidence"]
        assert any(item["evidence_type"] == "metric_trend" for item in evidence)
        allowed = {item["history_evidence_id"] for item in evidence}
        used = set(third["feedback_result"]["feedback"]["longitudinal"]["history_evidence_ids"])
        assert used <= allowed
        profile = repository.get_latest_learner_profile("LLMSNAP01")
        if not profile.get("current_learning_targets"):
            assert not used
        snapshots = repository.list_learner_profile_snapshots("LLMSNAP01")
        assert len(snapshots) == 3 and snapshots[-1]["baseline_status"] == "available"
