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
