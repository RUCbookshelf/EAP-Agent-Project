from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config import Settings
from app.database import Database


def _settings(tmp_path):
    return Settings(
        database_path=tmp_path / "v04.db", llm_provider="local", deepseek_api_key=None,
        deepseek_base_url="https://api.deepseek.com", deepseek_model="deepseek-chat",
    )


def _payload():
    return {
        "student_id": "V04_API", "writing_prompt": "Is history a lie?",
        "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
        "tool_use": "none",
        "essay_text": "History can be contested because sources differ. However, careful writers compare records. Therefore, claims should acknowledge uncertainty.",
    }


def test_analysis_runs_are_append_only_and_reanalysis_does_not_call_llm(tmp_path):
    settings = _settings(tmp_path)
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/v1/submissions", json=_payload())
        assert response.status_code == 201
        first = response.json()["analysis"]
        assert first["analysis_run_id"] == "AR000001"
        assert first["analyzer_version"] == "spacy-analyzer-v0.6.1"
        rerun = client.post("/api/v1/submissions/1/analyses")
        assert rerun.status_code == 201
        assert rerun.json()["llm_called"] is False
        assert rerun.json()["analysis"]["analysis_run_id"] == "AR000002"
        runs = client.get("/api/v1/submissions/1/analyses").json()["analysis_runs"]
        assert [item["analysis_run_id"] for item in runs] == ["AR000001", "AR000002"]
    database = Database(settings.database_path)
    assert database.counts()["feedback_records"] == 1
    assert database.counts()["analysis_runs"] == 2
    assert database.get_analysis_artifact("AR000001")["artifacts"]["tokens"]


def test_health_reports_nlp_resource_and_never_returns_secret(tmp_path):
    settings = _settings(tmp_path)
    with TestClient(create_app(settings)) as client:
        body = client.get("/api/v1/system/health").json()
        assert body["active_analyzer"] == "spacy"
        assert body["spacy_installed"] is True
        assert body["nlp_model_installed"] is True
        assert body["nlp_model_version"] == "3.8.0"
        assert "api_key" not in str(body).casefold()


def test_missing_model_fallback_reason_and_raw_text_are_persisted(tmp_path):
    settings = _settings(tmp_path)
    settings = Settings(**{**settings.__dict__, "spacy_model": "definitely_missing_model"})
    payload = _payload()
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/v1/submissions", json=payload)
        assert response.status_code == 201
        analysis = response.json()["analysis"]
        assert analysis["fallback_used"] is True
        assert "unavailable" in analysis["fallback_reason"]
        stored = client.get("/api/v1/submissions/1").json()
        assert stored["essay_text"] == payload["essay_text"]
    run = Database(settings.database_path).list_analysis_runs(1)[0]
    assert run["fallback_used"] is True
    assert run["fallback_reason"]


def test_migration_4_preserves_legacy_metrics_and_adds_analysis_tables(tmp_path):
    database = Database(tmp_path / "migration.db")
    database.initialize()
    with database.connect() as connection:
        tables = {row[0] for row in connection.execute("select name from sqlite_master where type='table'")}
    assert database.migration_version() == 7
    assert {"metrics", "analysis_runs", "metric_results", "analysis_artifacts"} <= tables
