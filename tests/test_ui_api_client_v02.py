from __future__ import annotations

import requests

import pytest

from app.ui.api_client import ApiClientError, WritingFeedbackApiClient


class Response:
    def __init__(self, status, payload): self.status_code, self.payload = status, payload
    def json(self): return self.payload


class Session:
    def __init__(self, response=None, error=None): self.response, self.error, self.calls = response, error, []
    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.error: raise self.error
        return self.response


def test_streamlit_api_client_submits_to_backend():
    session = Session(Response(201, {"submission_id": 7}))
    client = WritingFeedbackApiClient("http://127.0.0.1:8000", session=session)
    assert client.submit({"essay_text": "Text"})["submission_id"] == 7
    assert session.calls[0][1].endswith("/api/v1/submissions")


def test_unavailable_api_has_friendly_error():
    client = WritingFeedbackApiClient(
        "http://127.0.0.1:8000", session=Session(error=requests.ConnectionError("offline"))
    )
    with pytest.raises(ApiClientError, match="local feedback API is unavailable"):
        client.submit({"essay_text": "Text"})


def test_api_failure_is_not_replaced_with_fake_feedback():
    client = WritingFeedbackApiClient(
        "http://127.0.0.1:8000", session=Session(Response(500, {"error": {"message": "failed"}}))
    )
    with pytest.raises(ApiClientError, match="failed"):
        client.submit({"essay_text": "Text"})


@pytest.mark.parametrize(
    ("call", "expected_suffix"),
    [
        (lambda client: client.get_revision_candidates(7), "/api/v1/submissions/7/revision-candidates"),
        (lambda client: client.get_revision_analysis(7), "/api/v1/submissions/7/revision-analysis"),
        (lambda client: client.get_revision_group("RG000001"), "/api/v1/revisions/RG000001"),
        (lambda client: client.get_revision_comparison("RG000001"), "/api/v1/revisions/RG000001/comparison"),
    ],
)
def test_streamlit_api_client_revision_reads(call, expected_suffix):
    session = Session(Response(200, {"ok": True}))
    client = WritingFeedbackApiClient("http://127.0.0.1:8000", session=session)
    assert call(client) == {"ok": True}
    assert session.calls[0][1].endswith(expected_suffix)


def test_streamlit_api_client_creates_explicit_revision():
    session = Session(Response(201, {"group": {"revision_group_id": "RG000001"}}))
    client = WritingFeedbackApiClient("http://127.0.0.1:8000", session=session)
    result = client.create_revision(1, 2)
    assert result["group"]["revision_group_id"] == "RG000001"
    assert session.calls[0][2]["json"] == {"source_submission_id": 1, "target_submission_id": 2}
