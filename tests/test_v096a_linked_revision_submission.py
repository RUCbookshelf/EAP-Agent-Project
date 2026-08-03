"""v0.9.6-A focused tests: linked-revision submission reliability.

Covers the dedicated long-operation timeout, no automatic POST retry, the
pending/consume submit guard, bounded read-only timeout reconciliation,
accurate localized messages, linkage preservation, no-duplicate behavior in
the controlled timeout case, and locale parity. Local/fake providers only.
"""
from __future__ import annotations

import json
import socket
import threading
import time
from dataclasses import replace
from pathlib import Path

import pytest
import requests
import uvicorn
from streamlit.testing.v1 import AppTest

from app.api.main import create_app
from app.calibration import DiagnosticCalibrationService
from app.config import load_settings
from app.configuration import ConfigurationPayload
from app.database import Database
from app.diagnosis import NlpHeuristicDiagnoser
from app.feedback import FeedbackReliabilityService
from app.llm import LocalDemoProvider, ProviderRouter
from app.services import LearnerProfileService, ProgressService, RevisionService, SubmissionService
from app.services.factory import build_analyzer
from app.ui.api_client import (
    DEFAULT_TIMEOUTS,
    LONG_SUBMIT_TIMEOUTS,
    ApiClientError,
    ErrorCategory,
    TimeoutProfile,
    WritingFeedbackApiClient,
)
from app.ui.features.student.revision import _reconcile_linked_revision, _revision_baseline

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "harness_v096a_revision.py"
SOURCE_LABEL = "Should cities add more parks? \u00b7 first draft \u00b7 #1"
REVISED_TEXT = (
    "Parks support health and community life. Cities should protect accessible parks for everyone."
)


class FakeResponse:
    def __init__(self, payload, status_code=201, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._payload


class RecordingSession:
    """Records calls; optionally raises a requests exception per call."""

    def __init__(self, payload=None, exc=None):
        self.calls = []
        self.payload = payload or {}
        self.exc = exc

    def request(self, method, url, timeout=None, **kwargs):
        self.calls.append({"method": method, "url": url, "timeout": timeout, "kwargs": kwargs})
        if self.exc is not None:
            raise self.exc
        return FakeResponse(self.payload)


class DelayHolder:
    def __init__(self):
        self.delay = 0.0


class SlowProvider:
    provider_name = "slow-local"
    model_name = "slow-local-v096a"
    configured = True

    def __init__(self, inner, holder: DelayHolder):
        self._inner = inner
        self._holder = holder

    def generate(self, messages, *, temperature):
        time.sleep(self._holder.delay)
        return self._inner.generate(messages, temperature=temperature)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def build_service(settings, repository: Database, holder: DelayHolder) -> SubmissionService:
    analyzer = build_analyzer(settings)
    progress = ProgressService(
        learner_repository=repository._learner_repository,
        configuration_repository=repository._configuration_repository,
    )
    profile = LearnerProfileService(repository=repository._learner_repository, progress_service=progress)
    return SubmissionService(
        system_repository=repository._system_repository,
        submission_repository=repository._submission_repository,
        analysis_repository=repository._analysis_repository,
        calibration_repository=repository._calf_repository,
        analyzer=analyzer,
        diagnoser=NlpHeuristicDiagnoser(),
        router=ProviderRouter(
            SlowProvider(LocalDemoProvider(), holder),
            LocalDemoProvider(),
            reliability=FeedbackReliabilityService(None),
        ),
        learner_profile_service=profile,
        revision_service=RevisionService(repository._revision_repository),
        calibrator=DiagnosticCalibrationService(ConfigurationPayload()),
        calf_configuration=ConfigurationPayload(),
    )


def submission_payload(student: str, text: str, source: int | None, prompt: str) -> dict:
    return {
        "student_id": student,
        "writing_prompt": prompt,
        "genre": "argumentative essay",
        "draft_stage": "revised draft" if source else "first draft",
        "timed": False,
        "time_limit_minutes": None,
        "active_writing_duration_seconds": None,
        "timing_source": "unknown",
        "timing_quality": "unavailable",
        "unexplained_interruption": False,
        "tool_use": "none",
        "essay_text": text,
        "revision_of_submission_id": source,
    }


@pytest.fixture(scope="module")
def api_env(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("v096a")
    db_path = tmp / "api.db"
    settings = replace(
        load_settings(), database_path=db_path, llm_provider="local", deepseek_api_key=None,
    )
    repository = Database(db_path)
    repository.initialize()
    holder = DelayHolder()
    app = create_app(settings, repository=repository, submission_service=build_service(settings, repository, holder))
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        try:
            requests.get(f"http://127.0.0.1:{port}/api/v1/system/health", timeout=1.0)
            break
        except requests.RequestException:
            time.sleep(0.1)
    try:
        yield {
            "base": f"http://127.0.0.1:{port}",
            "repository": repository,
            "holder": holder,
        }
    finally:
        server.should_exit = True
        thread.join(timeout=10)


# ---------------------------------------------------------------------------
# Client timeout policy
# ---------------------------------------------------------------------------

def test_linked_revision_client_uses_dedicated_long_timeout():
    assert LONG_SUBMIT_TIMEOUTS == TimeoutProfile(connect=2.0, read=180.0, write=180.0)
    session = RecordingSession(payload={"submission_id": 1})
    client = WritingFeedbackApiClient("http://x", session=session)
    client.submit_linked_revision({"essay_text": "x"})
    assert session.calls[0]["timeout"] == (2.0, 180.0)
    assert session.calls[0]["method"] == "POST"


def test_ordinary_profiles_unchanged_and_submit_uses_long_policy():
    # v0.9.6-B unified policy: first-draft submission moved to the shared
    # long-running transport; ordinary request profiles are unchanged.
    assert DEFAULT_TIMEOUTS == TimeoutProfile(connect=2.0, read=10.0, write=30.0)
    read_session = RecordingSession(payload={"submission_id": 1})
    read_client = WritingFeedbackApiClient("http://x", session=read_session)
    read_client.get_submission(1)
    assert read_session.calls[0]["timeout"] == (2.0, 10.0)
    session = RecordingSession(payload={"submission_id": 1})
    client = WritingFeedbackApiClient("http://x", session=session)
    client.submit({"essay_text": "x"})
    assert session.calls[0]["timeout"] == (2.0, 180.0)


def test_submit_linked_revision_posts_once_and_never_retries_on_timeout():
    session = RecordingSession(exc=requests.exceptions.ReadTimeout("slow"))
    client = WritingFeedbackApiClient("http://x", session=session)
    with pytest.raises(ApiClientError) as excinfo:
        client.submit_linked_revision({"essay_text": "x"})
    assert excinfo.value.category == ErrorCategory.REQUEST_TIMEOUT
    assert excinfo.value.operation == "submit"
    assert len(session.calls) == 1  # no automatic retry for the POST


def test_submit_linked_revision_posts_once_on_success():
    session = RecordingSession(payload={"submission_id": 7})
    client = WritingFeedbackApiClient("http://x", session=session)
    result = client.submit_linked_revision({"essay_text": "x"})
    assert result["submission_id"] == 7
    assert len(session.calls) == 1


# ---------------------------------------------------------------------------
# Reconciliation logic (bounded read-only, exact evidence only)
# ---------------------------------------------------------------------------

class ReconcileClient:
    def __init__(self, candidates=None, bundle=None, raise_candidates=False, raise_bundle=False):
        self.candidates = candidates or []
        self.bundle = bundle
        self.raise_candidates = raise_candidates
        self.raise_bundle = raise_bundle
        self.candidate_calls = 0
        self.bundle_calls = 0

    def get_student_revision_candidates(self, student_id):
        self.candidate_calls += 1
        if self.raise_candidates:
            raise ApiClientError(ErrorCategory.SERVICE_NOT_RUNNING, "down", operation="revision_candidates")
        return {"candidates": self.candidates}

    def get_submission(self, submission_id):
        self.bundle_calls += 1
        if self.raise_bundle:
            raise ApiClientError(ErrorCategory.SERVICE_NOT_RUNNING, "down", operation="get_submission")
        return self.bundle


def _match_row(essay_id=50, submitted_at="2026-08-03T08:30:00+00:00"):
    return {
        "essay_id": essay_id,
        "revision_of_submission_id": 1,
        "revision_group_id": "RG000001",
        "revision_sequence": 2,
        "submitted_at": submitted_at,
    }


def test_reconcile_confirmed_success_when_feedback_present():
    client = ReconcileClient(
        candidates=[_match_row()],
        bundle={"essay_id": 50, "feedback": {"priority_feedback": []}, "success_status": "success"},
    )
    assert _reconcile_linked_revision(client, "S1", 1, None) == "CONFIRMED_SUCCESS"
    assert client.candidate_calls == 1 and client.bundle_calls == 1


def test_reconcile_still_processing_when_feedback_missing():
    client = ReconcileClient(
        candidates=[_match_row()],
        bundle={"essay_id": 50, "feedback": None, "success_status": None},
    )
    assert _reconcile_linked_revision(client, "S1", 1, None) == "STILL_PROCESSING"


def test_reconcile_unconfirmed_when_no_new_revision():
    client = ReconcileClient(candidates=[])
    assert _reconcile_linked_revision(client, "S1", 1, None) == "UNCONFIRMED"


def test_reconcile_unconfirmed_when_only_old_rows_exist():
    old = _match_row(submitted_at="2026-08-03T08:00:00+00:00")
    client = ReconcileClient(candidates=[old])
    assert _reconcile_linked_revision(client, "S1", 1, "2026-08-03T08:00:00+00:00") == "UNCONFIRMED"


def test_reconcile_unconfirmed_on_read_failure():
    client = ReconcileClient(raise_candidates=True)
    assert _reconcile_linked_revision(client, "S1", 1, None) == "UNCONFIRMED"
    client = ReconcileClient(candidates=[_match_row()], raise_bundle=True)
    assert _reconcile_linked_revision(client, "S1", 1, None) == "UNCONFIRMED"


def test_revision_baseline_uses_only_server_timestamps():
    candidates = [
        {"essay_id": 3, "revision_of_submission_id": 1, "submitted_at": "2026-08-03T08:00:00+00:00"},
        {"essay_id": 4, "revision_of_submission_id": 2, "submitted_at": "2026-08-03T09:00:00+00:00"},
        {"essay_id": 5, "revision_of_submission_id": 1, "submitted_at": "2026-08-03T08:30:00+00:00"},
    ]
    assert _revision_baseline(candidates, 1) == "2026-08-03T08:30:00+00:00"
    assert _revision_baseline(candidates, 99) is None


# ---------------------------------------------------------------------------
# AppTest user flows
# ---------------------------------------------------------------------------

def _run_harness(**config):
    at = AppTest.from_file(str(HARNESS), default_timeout=90)
    for key, value in config.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, at.exception
    at.text_input(key="revision_student").set_value("S96C").run()
    assert not at.exception, at.exception
    at.selectbox(key="revision_source_select").select(SOURCE_LABEL).run()
    assert not at.exception, at.exception
    at.text_area(key="revision_text_input").set_value(REVISED_TEXT).run()
    assert not at.exception, at.exception
    return at


def _markdown_text(at) -> str:
    return " ".join(m.value for m in at.markdown)


def test_ui_success_flow_posts_once_and_shows_saved_state():
    at = _run_harness(harness_behavior="success")
    at.button(key="revision_submit_primary").click().run()
    assert not at.exception, at.exception
    client = at.session_state["fake_client"]
    assert client.post_count == 1
    text = _markdown_text(at)
    assert "Revision submitted" in text
    assert any(b.key == "revision_primary_action" for b in at.button)


def test_ui_timeout_unconfirmed_message_and_no_blind_retry():
    at = _run_harness(harness_behavior="timeout")
    at.button(key="revision_submit_primary").click().run()
    assert not at.exception, at.exception
    client = at.session_state["fake_client"]
    assert client.post_count == 1
    text = _markdown_text(at)
    assert "timed out before the result could be confirmed" in text
    assert "Please try again" not in text
    assert "Retry" not in [b.label for b in at.button]


def test_ui_pending_guard_consumes_queued_click_without_second_post():
    at = _run_harness(harness_behavior="timeout")
    at.button(key="revision_submit_primary").click().run()
    assert not at.exception, at.exception
    client = at.session_state["fake_client"]
    assert client.post_count == 1
    at.button(key="revision_submit_primary").click().run()
    assert not at.exception, at.exception
    assert client.post_count == 1  # queued click consumed; no second POST


def test_ui_guard_released_after_outcome_consumed():
    at = _run_harness(harness_behavior="timeout")
    at.button(key="revision_submit_primary").click().run()
    at.button(key="revision_submit_primary").click().run()
    client = at.session_state["fake_client"]
    assert client.post_count == 1  # consumed
    at.button(key="revision_submit_primary").click().run()
    assert client.post_count == 2  # deliberate new attempt works


def test_ui_timeout_confirmed_success_message():
    new_row = {
        "essay_id": 50,
        "student_id": "S96C",
        "writing_prompt": "Should cities add more parks?",
        "genre": "argumentative essay",
        "draft_stage": "revised draft",
        "timed": False,
        "time_limit_minutes": None,
        "tool_use": "none",
        "submitted_at": "2026-08-03T08:30:00+00:00",
        "revision_of_submission_id": 1,
        "revision_group_id": "RG000001",
        "revision_sequence": 2,
        "revision_stage": "revised_draft",
        "original_draft_stage": "revised draft",
        "writing_started_at": None,
        "writing_submitted_at": None,
        "active_writing_duration_seconds": None,
        "timing_source": "unknown",
        "timing_quality": "unavailable",
        "unexplained_interruption": False,
    }
    at = _run_harness(
        harness_behavior="timeout",
        harness_candidates_after=[new_row],
        harness_bundle_after={"essay_id": 50, "feedback": {"priority_feedback": []}, "success_status": "success"},
    )
    at.button(key="revision_submit_primary").click().run()
    assert not at.exception, at.exception
    assert "The linked revision was submitted successfully." in _markdown_text(at)


def test_ui_timeout_still_processing_message():
    new_row = {
        "essay_id": 50,
        "student_id": "S96C",
        "writing_prompt": "Should cities add more parks?",
        "genre": "argumentative essay",
        "draft_stage": "revised draft",
        "timed": False,
        "time_limit_minutes": None,
        "tool_use": "none",
        "submitted_at": "2026-08-03T08:30:00+00:00",
        "revision_of_submission_id": 1,
        "revision_group_id": "RG000001",
        "revision_sequence": 2,
        "revision_stage": "revised_draft",
        "original_draft_stage": "revised draft",
        "writing_started_at": None,
        "writing_submitted_at": None,
        "active_writing_duration_seconds": None,
        "timing_source": "unknown",
        "timing_quality": "unavailable",
        "unexplained_interruption": False,
    }
    at = _run_harness(
        harness_behavior="timeout",
        harness_candidates_after=[new_row],
        harness_bundle_after={"essay_id": 50, "feedback": None, "success_status": None},
    )
    at.button(key="revision_submit_primary").click().run()
    assert not at.exception, at.exception
    assert "still being processed" in _markdown_text(at)


# ---------------------------------------------------------------------------
# Integration: real local server, controlled slow provider
# ---------------------------------------------------------------------------

def test_controlled_slow_linked_revision_succeeds_below_new_timeout(api_env):
    base, repository, holder = api_env["base"], api_env["repository"], api_env["holder"]
    holder.delay = 0.0
    client = WritingFeedbackApiClient(base, timeouts=LONG_SUBMIT_TIMEOUTS)
    prompt = "Should cities protect local parks?"
    source = client.submit(submission_payload(
        "S96SLOW", "Parks support public health. Cities should protect accessible parks.", None, prompt,
    ))
    holder.delay = 31.5  # longer than the old 30 s write timeout
    started = time.monotonic()
    result = client.submit_linked_revision(submission_payload(
        "S96SLOW",
        "Parks support public health and community life. Cities should protect accessible parks in every neighborhood.",
        int(source["submission_id"]), prompt,
    ))
    elapsed = time.monotonic() - started
    assert elapsed >= 31.0
    assert int(result["submission_id"]) > int(source["submission_id"])
    holder.delay = 0.0


def test_no_duplicate_revision_in_controlled_timeout_case(api_env):
    base, repository, holder = api_env["base"], api_env["repository"], api_env["holder"]
    holder.delay = 0.0
    client = WritingFeedbackApiClient(base, timeouts=TimeoutProfile(connect=2.0, write=3.0))
    prompt = "Should cities protect local parks?"
    source = client.submit(submission_payload(
        "S96DUP", "Parks support public health. Cities should protect accessible parks.", None, prompt,
    ))
    source_id = int(source["submission_id"])
    holder.delay = 6.0
    # Force a real client timeout with a shortened profile on the same POST
    # endpoint. Since v0.9.6-B, submit()/submit_linked_revision() always use
    # the fixed 180 s LONG_SUBMIT_TIMEOUTS (proven by the controlled slow
    # tests), so the timeout is simulated by invoking the shared transport
    # with an explicit short test-only profile; the POST is never retried.
    with pytest.raises(ApiClientError) as excinfo:
        client._request(
            "POST", "/api/v1/submissions", operation="submit",
            json=submission_payload(
                "S96DUP",
                "Parks support health. Cities should protect parks in every neighborhood.",
                source_id, prompt,
            ),
            profile=TimeoutProfile(connect=2.0, write=3.0),
        )
    assert excinfo.value.category == ErrorCategory.REQUEST_TIMEOUT
    holder.delay = 0.0
    deadline = time.monotonic() + 15.0
    bundle = None
    while time.monotonic() < deadline:
        rows = repository._submission_repository.list_student_submissions("S96DUP")
        matches = [r for r in rows if r.get("revision_of_submission_id") == source_id]
        if matches:
            newest = max(matches, key=lambda r: r["submitted_at"])
            bundle = repository._submission_repository.get_submission_bundle(int(newest["essay_id"]))
            if bundle and bundle.get("feedback_id") is not None:
                break
        time.sleep(0.25)
    assert bundle is not None and bundle.get("feedback_id") is not None, "backend did not complete"
    assert len([r for r in repository._submission_repository.list_student_submissions("S96DUP")
                if r.get("revision_of_submission_id") == source_id]) == 1


def test_linked_revision_identity_and_parent_group_linkage(api_env):
    base, repository = api_env["base"], api_env["repository"]
    holder = api_env["holder"]
    holder.delay = 0.0
    client = WritingFeedbackApiClient(base, timeouts=LONG_SUBMIT_TIMEOUTS)
    prompt = "Should cities protect local parks?"
    source = client.submit(submission_payload(
        "S96ID", "Parks support public health. Cities should protect accessible parks.", None, prompt,
    ))
    source_id = int(source["submission_id"])
    revised = client.submit_linked_revision(submission_payload(
        "S96ID",
        "Parks support public health and community life. Cities should protect accessible parks for everyone.",
        source_id, prompt,
    ))
    bundle = repository._submission_repository.get_submission_bundle(int(revised["submission_id"]))
    assert bundle["revision_of_submission_id"] == source_id
    assert bundle["revision_group_id"] is not None
    assert bundle["revision_sequence"] == 2
    snapshots = RevisionService(repository._revision_repository).history(bundle["revision_group_id"])
    assert any(s.target_submission_id == int(revised["submission_id"]) for s in snapshots)


# ---------------------------------------------------------------------------
# Locale parity and original-path preservation
# ---------------------------------------------------------------------------

def test_locale_new_keys_present_and_parity():
    def leaf_keys(obj, prefix=""):
        keys = set()
        for k, v in obj.items():
            p = prefix + "/" + k
            if isinstance(v, dict):
                keys |= leaf_keys(v, p)
            else:
                keys.add(p)
        return keys

    en = json.loads((ROOT / "locales/en.json").read_text(encoding="utf-8"))
    zh = json.loads((ROOT / "locales/zh_CN.json").read_text(encoding="utf-8"))
    en_keys, zh_keys = leaf_keys(en), leaf_keys(zh)
    assert en_keys == zh_keys
    for key in (
        "student_revision_submit_pending",
        "student_revision_timeout_confirmed_success",
        "student_revision_timeout_still_processing",
        "student_revision_timeout_unconfirmed",
    ):
        assert "/" + key in en_keys
        assert en[key] != zh[key]


def test_original_submit_and_writing_page_unchanged():
    # v0.9.6-B: the writing page still calls the generic client method,
    # which now uses the shared long-running transport.
    session = RecordingSession(payload={"submission_id": 1})
    client = WritingFeedbackApiClient("http://x", session=session)
    client.submit({"essay_text": "x"})
    assert session.calls[0]["timeout"] == (2.0, 180.0)
    # The writing page still calls the generic client method.
    source = (ROOT / "app/ui/features/student/writing.py").read_text(encoding="utf-8")
    assert source.count("api_client.submit(submission)") == 1
    assert "submit_linked_revision" not in source