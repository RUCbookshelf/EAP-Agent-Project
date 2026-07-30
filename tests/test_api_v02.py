from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.config import Settings


def make_client(tmp_path, *, provider="local"):
    settings = Settings(
        database_path=tmp_path / "api.db", llm_provider=provider,
        deepseek_api_key=None, deepseek_base_url="https://example.invalid",
        deepseek_model="deepseek-test",
    )
    return TestClient(create_app(settings))


def payload(student_id="API001"):
    return {
        "student_id": student_id,
        "writing_prompt": "Should cities add parks?",
        "genre": "argumentative essay", "draft_stage": "first draft",
        "timed": False, "time_limit_minutes": None, "tool_use": "none",
        "essay_text": "Cities need parks because parks support health. Therefore, leaders should protect green spaces.",
    }


def test_health_version_and_docs(tmp_path):
    with make_client(tmp_path) as client:
        health = client.get("/api/v1/system/health")
        assert health.status_code == 200
        assert health.json() | {"ignored": True}
        assert health.json()["database_status"] == "connected"
        assert health.json()["llm_api_configured"] is False
        assert "deepseek_api_key" not in health.text.casefold()
        assert client.get("/api/v1/system/version").json()["application_version"] == "0.7.1"
        assert client.get("/docs").status_code == 200


def test_submission_get_history_and_v02_placeholders(tmp_path):
    with make_client(tmp_path) as client:
        created = client.post("/api/v1/submissions", json=payload())
        assert created.status_code == 201
        body = created.json()
        assert body["feedback_result"]["provider_name"] == "local-demo"
        assert body["feedback_result"]["validation_status"] == "passed"
        submission_id = body["submission_id"]
        assert client.get(f"/api/v1/submissions/{submission_id}").status_code == 200
        assert client.get("/api/v1/students/API001").json()["submission_count"] == 1
        assert len(client.get("/api/v1/students/API001/history").json()["submissions"]) == 1
        assert client.get("/api/v1/students/API001/profile").json()["history_sufficiency"] == "insufficient_history"
        assert client.get("/api/v1/students/API001/progress").json()["baseline_status"] == "insufficient_history"


def test_api_errors_are_consistent_and_safe(tmp_path):
    with make_client(tmp_path) as client:
        missing = client.get("/api/v1/submissions/999")
        assert missing.status_code == 404 and missing.json()["error"]["code"] == "not_found"
        student = client.get("/api/v1/students/UNKNOWN")
        assert student.status_code == 404 and student.json()["error"]["code"] == "not_found"
        invalid = payload()
        invalid["essay_text"] = "   "
        response = client.post("/api/v1/submissions", json=invalid)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
        assert "traceback" not in response.text.casefold() and "api key" not in response.text.casefold()


def test_no_key_deepseek_configuration_falls_back(tmp_path):
    with make_client(tmp_path, provider="deepseek") as client:
        response = client.post("/api/v1/submissions", json=payload("FALLBACK01"))
        assert response.status_code == 201
        result = response.json()["feedback_result"]
        assert result["success_status"] == "fallback_success"
        assert result["provider_name"] == "local-demo"
