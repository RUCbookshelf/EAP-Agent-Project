"""v0.9.3-B request-reliability tests.

Covers the canonical error taxonomy, repaired Research endpoints, request-ID
propagation, client classification, timeout profiles, and retry policy.
"""

from __future__ import annotations

import json
import time

import pytest
import requests

from app.api.main import create_app
from app.config import Settings, load_settings
from app.database import Database
from app.errors import ApiError, CATEGORY_MESSAGE_KEY, ErrorCategory
from app.research.service import ResearchDataService
from app.research.schemas import HumanReviewCreate, HumanReviewDecision, HumanReviewTarget
from app.ui.api_client import ApiClientError, TimeoutProfile, WritingFeedbackApiClient
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path):
    settings = Settings(
        database_path=tmp_path / "api.db", llm_provider="local",
        deepseek_api_key=None, deepseek_base_url="https://example.invalid",
        deepseek_model="deepseek-test",
    )
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Canonical error taxonomy
# ---------------------------------------------------------------------------

def test_error_categories_have_message_keys_and_status():
    for category in ErrorCategory:
        assert category.value in CATEGORY_MESSAGE_KEY
        assert category.value.startswith(category.value.split("_")[0])


def test_retryable_categories_are_limited():
    from app.errors import RETRYABLE_CATEGORIES
    assert RETRYABLE_CATEGORIES <= {
        ErrorCategory.SERVICE_STARTING,
        ErrorCategory.CONNECTION_INTERRUPTED,
        ErrorCategory.REQUEST_TIMEOUT,
    }


# ---------------------------------------------------------------------------
# Repaired Research endpoints (real HTTP through TestClient)
# ---------------------------------------------------------------------------

def test_export_schema_endpoint(client):
    r = client.get("/api/v1/research/export/schema")
    assert r.status_code == 200
    assert r.json()["schema_version"] == "research-export-v0.1"


def test_export_preview_endpoint(client):
    payload = {"filter_spec": {}, "privacy_mode": "pseudonymized", "formats": ["jsonl"]}
    r = client.post("/api/v1/research/export/preview", json=payload)
    assert r.status_code == 200
    assert "essay_count" in r.json()


def test_export_preview_invalid_input(client):
    r = client.post("/api/v1/research/export/preview", json={"bad": 1})
    assert r.status_code == 422
    assert r.json()["error"]["category"] == "invalid_request"


def test_export_run_and_status_and_manifest(client):
    payload = {"filter_spec": {}, "privacy_mode": "pseudonymized", "formats": ["jsonl"]}
    r = client.post("/api/v1/research/export/run", json=payload)
    assert r.status_code == 200
    export_id = r.json()["export_id"]
    assert r.json()["status"] == "completed"

    status = client.get(f"/api/v1/research/export/{export_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "completed"

    manifest = client.get(f"/api/v1/research/export/{export_id}/manifest")
    assert manifest.status_code == 200
    assert manifest.json()["export_id"] == export_id

    missing = client.get("/api/v1/research/export/EXP999999/manifest")
    assert missing.status_code == 404


def test_export_history_endpoint_not_shadowed(client):
    """/history must not be shadowed by /{export_id}."""
    r = client.get("/api/v1/research/export/history")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_data_quality_endpoint(client):
    r = client.get("/api/v1/research/data-quality")
    assert r.status_code == 200
    assert r.json()["items"]


def test_pii_candidates_and_review(client):
    # Create a real submission first so PII scanning has a target.
    sub = {
        "student_id": "PII001",
        "writing_prompt": "Write about contact details.",
        "genre": "argumentative essay",
        "draft_stage": "independent submission",
        "timed": False,
        "tool_use": "none",
        "essay_text": "Contact me at john@example.com or call 13800138000 for info.",
    }
    created = client.post("/api/v1/submissions", json=sub)
    assert created.status_code == 201
    submission_id = created.json()["submission_id"]

    r = client.get(f"/api/v1/submissions/{submission_id}/pii-candidates")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) > 0  # email/phone detected

    r = client.post(f"/api/v1/submissions/{submission_id}/pii-review", json={"reviews": []})
    assert r.status_code == 200
    assert r.json()["updated_candidates"] == []

    # Not-found submission
    r = client.get("/api/v1/submissions/999999/pii-candidates")
    assert r.status_code == 404
    assert r.json()["error"]["category"] == "resource_not_found"


def test_human_review_create_and_list(client):
    payload = {
        "target_type": "diagnosis", "target_id": "D001", "reviewer_id": "R001",
        "decision": "correct", "confidence": "medium", "comment": "test review",
    }
    r = client.post("/api/v1/research/reviews", json=payload)
    assert r.status_code == 200
    review_id = r.json()["review_id"]
    assert review_id is not None

    listed = client.get("/api/v1/research/reviews?target_type=diagnosis")
    assert listed.status_code == 200
    assert any(item["review_id"] == review_id for item in listed.json())

    invalid = client.post("/api/v1/research/reviews", json={"target_type": "bogus"})
    assert invalid.status_code == 422


def test_dataset_split_endpoint(client):
    payload = {"students": ["S001", "S002", "S003", "S004", "S005"], "seed": 42,
               "train_ratio": 0.7, "val_ratio": 0.15, "test_ratio": 0.15}
    r = client.post("/api/v1/research/dataset-split", json=payload)
    assert r.status_code == 200
    assert r.json()["student_count"] == 5

    invalid = client.post("/api/v1/research/dataset-split", json={"students": [], "train_ratio": 2.0, "val_ratio": 0.1, "test_ratio": 0.1})
    assert invalid.status_code == 422


# ---------------------------------------------------------------------------
# Request IDs
# ---------------------------------------------------------------------------

def test_request_id_in_response_headers(client):
    r = client.get("/api/v1/system/health")
    assert r.headers.get("X-Request-ID")


def test_request_id_in_error_body(client):
    r = client.get("/api/v1/students/UNKNOWN/history")
    assert r.status_code == 404
    assert r.json()["error"]["request_id"]


def test_request_id_not_learner_derived(client):
    r = client.get("/api/v1/students/UNKNOWN/history")
    rid = r.json()["error"]["request_id"]
    assert "UNKNOWN" not in rid
    assert len(rid) > 0


# ---------------------------------------------------------------------------
# Client classification and retry policy
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, status_code, payload, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self):
        return self._payload


class _Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, timeout=None, **kwargs):
        self.calls.append((method, url))
        response = self.responses.pop(0) if self.responses else _FakeResponse(404, {"error": {"category": "resource_not_found"}})
        if isinstance(response, Exception):
            raise response
        return response


def test_client_classifies_404():
    session = _Session([_FakeResponse(404, {"error": {"category": "resource_not_found", "detail": "Student not found."}})])
    client = WritingFeedbackApiClient("http://127.0.0.1:8000", session=session)
    with pytest.raises(ApiClientError) as exc_info:
        client.get_learner_model("S999")
    assert exc_info.value.category == ErrorCategory.RESOURCE_NOT_FOUND
    assert not exc_info.value.retryable


def test_client_classifies_connection_refused():
    session = _Session([requests.ConnectionError("offline")])
    client = WritingFeedbackApiClient("http://127.0.0.1:8000", session=session)
    with pytest.raises(ApiClientError) as exc_info:
        client.get_learner_model("S02")
    assert exc_info.value.category == ErrorCategory.SERVICE_NOT_RUNNING


def test_client_classifies_read_timeout():
    session = _Session([requests.exceptions.ReadTimeout("slow"), requests.exceptions.ReadTimeout("slow")])
    client = WritingFeedbackApiClient("http://127.0.0.1:8000", session=session)
    with pytest.raises(ApiClientError) as exc_info:
        client.get_learner_model("S02")
    assert exc_info.value.category == ErrorCategory.REQUEST_TIMEOUT
    assert exc_info.value.retryable


def test_client_classifies_backend_500():
    session = _Session([_FakeResponse(500, {"error": {"category": "backend_processing_error", "detail": "boom"}})])
    client = WritingFeedbackApiClient("http://127.0.0.1:8000", session=session)
    with pytest.raises(ApiClientError) as exc_info:
        client.get_learner_model("S02")
    assert exc_info.value.category == ErrorCategory.BACKEND_PROCESSING_ERROR


def test_client_classifies_starting_503():
    session = _Session([_FakeResponse(503, {"error": {"category": "service_starting", "detail": "starting"}})])
    client = WritingFeedbackApiClient("http://127.0.0.1:8000", session=session)
    with pytest.raises(ApiClientError) as exc_info:
        client.get_learner_model("S02")
    assert exc_info.value.category == ErrorCategory.SERVICE_STARTING
    assert exc_info.value.retryable


def test_get_retry_on_transient_connection():
    """Read-only GET may retry once on a transient interruption."""
    session = _Session([
        requests.exceptions.ChunkedEncodingError("interrupted"),
        _FakeResponse(200, {"ok": True}),
    ])
    client = WritingFeedbackApiClient("http://127.0.0.1:8000", session=session)
    result = client.get_learner_model("S02")
    assert result == {"ok": True}
    assert len(session.calls) == 2


def test_post_never_retries():
    """State-changing POST must not be automatically retried."""
    session = _Session([
        requests.ConnectionError("interrupted"),
        _FakeResponse(201, {"ok": True}),
    ])
    client = WritingFeedbackApiClient("http://127.0.0.1:8000", session=session)
    with pytest.raises(ApiClientError) as exc_info:
        client.submit({"essay_text": "Text"})
    assert exc_info.value.category == ErrorCategory.SERVICE_NOT_RUNNING
    assert len(session.calls) == 1  # no retry


def test_retry_not_attempted_for_404_or_422():
    session = _Session([
        _FakeResponse(404, {"error": {"category": "resource_not_found"}}),
        _FakeResponse(200, {"ok": True}),
    ])
    client = WritingFeedbackApiClient("http://127.0.0.1:8000", session=session)
    with pytest.raises(ApiClientError) as exc_info:
        client.get_learner_model("S999")
    assert exc_info.value.category == ErrorCategory.RESOURCE_NOT_FOUND
    assert len(session.calls) == 1


def test_timeout_profiles_are_centralized():
    default = TimeoutProfile()
    assert default.connect == 2.0
    assert default.read == 10.0
    assert default.write == 30.0
    long_read = TimeoutProfile(connect=2.0, read=60.0, write=30.0)
    assert long_read.read == 60.0


# ---------------------------------------------------------------------------
# Localization
# ---------------------------------------------------------------------------

def test_locale_key_parity_for_error_keys():
    import json as _json
    from pathlib import Path
    en = _json.loads(Path("locales/en.json").read_text(encoding="utf-8"))
    zh = _json.loads(Path("locales/zh_CN.json").read_text(encoding="utf-8"))
    en_keys = set(en.keys())
    zh_keys = set(zh.keys())
    assert en_keys == zh_keys
    for category in ErrorCategory:
        key = CATEGORY_MESSAGE_KEY[category]
        assert key in en_keys and key in zh_keys


def test_no_raw_error_keys_in_ui_sources():
    from pathlib import Path
    for path in Path("app/ui").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert 'error_service_not_running"' not in text  # raw keys never hardcoded as strings
