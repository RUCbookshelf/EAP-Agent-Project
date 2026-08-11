"""Route/method and availability-classification tests for Wave2ApiClient."""

from __future__ import annotations

import requests
import pytest

from app.ui.wave2.client import Wave2ApiClient, Wave2ApiClientError, Wave2ApiUnavailable


class Response:
    def __init__(self, status, payload):
        self.status_code, self.payload = status, payload
    def json(self):
        return self.payload


class Session:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []
    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.error:
            raise self.error
        return self.response


def make_client(session) -> Wave2ApiClient:
    return Wave2ApiClient("http://127.0.0.1:8000", session=session)


@pytest.mark.parametrize(
    ("call", "method", "suffix"),
    [
        (lambda c: c.create_task("S1", "opinion", "cet4", "Prompt"), "POST", "/api/v1/wave2/revision/tasks"),
        (lambda c: c.get_task("T-0001"), "GET", "/api/v1/wave2/revision/tasks/T-0001"),
        (lambda c: c.submit_v1("T-0001", "Text"), "POST", "/api/v1/wave2/revision/tasks/T-0001/submissions"),
        (lambda c: c.revise("T-0001", 1, "Text"), "POST", "/api/v1/wave2/revision/tasks/T-0001/submissions/1/revisions"),
        (lambda c: c.version_history("T-0001"), "GET", "/api/v1/wave2/revision/tasks/T-0001/versions"),
        (lambda c: c.revision_observation("T-0001", 2), "GET", "/api/v1/wave2/revision/tasks/T-0001/versions/2/observation"),
        (lambda c: c.priority_plan("S1", "T-0001", 1), "POST", "/api/v1/wave2/personalized/priority-plan"),
        (lambda c: c.scaffold("S1", "lexical_repetition"), "POST", "/api/v1/wave2/personalized/scaffold"),
        (lambda c: c.list_learning_items("S1"), "GET", "/api/v1/wave2/personalized/learning-items"),
        (lambda c: c.create_learning_item("S1", "PLAN-1"), "POST", "/api/v1/wave2/personalized/learning-items"),
        (lambda c: c.update_learning_item_status("LI-1", "active"), "PATCH", "/api/v1/wave2/personalized/learning-items/LI-1"),
        (lambda c: c.list_observations("S1"), "GET", "/api/v1/wave2/learner/observations"),
        (lambda c: c.difficulties("S1"), "GET", "/api/v1/wave2/learner/difficulties"),
        (lambda c: c.strengths("S1"), "GET", "/api/v1/wave2/learner/strengths"),
        (lambda c: c.stable("S1"), "GET", "/api/v1/wave2/learner/stable"),
        (lambda c: c.proficiency_context("S1"), "GET", "/api/v1/wave2/learner/proficiency-context"),
        (lambda c: c.current_evidence("S1"), "GET", "/api/v1/wave2/learner/evidence"),
    ],
)
def test_wave2_client_routes(call, method, suffix):
    session = Session(Response(200, {"ok": True}))
    client = make_client(session)
    assert call(client) == {"ok": True}
    assert session.calls[0][0] == method
    assert session.calls[0][1].split("?")[0].endswith(suffix)


def test_create_task_sends_documented_body():
    session = Session(Response(201, {"task_id": "T-0001"}))
    client = make_client(session)
    client.create_task(
        "S1", "opinion", "cet4", "Prompt",
        metadata={"audience": "examiner"}, declared_task_type="opinion",
    )
    body = session.calls[0][2]["json"]
    assert body == {
        "student_id": "S1", "task_type": "opinion", "writing_context": "cet4",
        "writing_prompt": "Prompt", "metadata": {"audience": "examiner"},
        "declared_task_type": "opinion",
    }


def test_scaffold_sends_level_and_category():
    session = Session(Response(200, {"ok": True}))
    client = make_client(session)
    client.scaffold("S1", "lexical_repetition", level=3)
    body = session.calls[0][2]["json"]
    assert body["category"] == "lexical_repetition"
    assert body["level"] == 3


def test_learning_items_status_filter_uses_query_param():
    session = Session(Response(200, {"items": []}))
    client = make_client(session)
    client.list_learning_items("S1", status="active")
    assert "student_id=S1" in session.calls[0][1]
    assert "status=active" in session.calls[0][1]


def test_connection_error_is_unavailable():
    client = make_client(Session(error=requests.ConnectionError("refused")))
    with pytest.raises(Wave2ApiUnavailable):
        client.list_observations("S1")
    assert client.probe() is False


def test_http_404_and_503_are_unavailable():
    for status in (404, 405, 503):
        client = make_client(Session(Response(status, {"detail": "not found"})))
        with pytest.raises(Wave2ApiUnavailable):
            client.list_observations("S1")
        assert client.probe() is False


def test_other_http_errors_are_classified_client_errors():
    for status in (422, 500):
        client = make_client(Session(Response(status, {"detail": "boom"})))
        with pytest.raises(Wave2ApiClientError) as exc_info:
            client.list_observations("S1")
        assert exc_info.value.http_status == status


def test_probe_true_on_200():
    client = make_client(Session(Response(200, {"learner_id": "p", "items": []})))
    assert client.probe() is True
    assert client.probe() is True  # cached
    assert len(client.session.calls) == 1