"""v0.9.6-B focused tests: first-draft and unified submission reliability.

Covers the shared private long-submit transport (both modes), unchanged
ordinary request timeouts, no automatic POST retry, exactly one POST per
logical submit, writing-page pending/consume guard, exact first-draft
reconciliation, honest unconfirmed outcomes, locale parity, and the
frontend public-method count (53).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import requests
from streamlit.testing.v1 import AppTest

from app.ui.api_client import (
    DEFAULT_TIMEOUTS,
    LONG_SUBMIT_TIMEOUTS,
    ApiClientError,
    ErrorCategory,
    TimeoutProfile,
    WritingFeedbackApiClient,
)
from app.ui.features.student.writing import (
    _reconcile_writing_submission,
    _submission_baseline,
)

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "harness_v096b_writing.py"
PROMPT = "Should cities add more parks?"
DRAFT_TEXT = "Parks support public health. Cities should protect accessible parks."


class FakeResponse:
    def __init__(self, payload, status_code=201, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._payload


class RecordingSession:
    def __init__(self, payload=None, exc=None):
        self.calls = []
        self.payload = payload or {}
        self.exc = exc

    def request(self, method, url, timeout=None, **kwargs):
        self.calls.append({"method": method, "url": url, "timeout": timeout, "kwargs": kwargs})
        if self.exc is not None:
            raise self.exc
        return FakeResponse(self.payload)


# ---------------------------------------------------------------------------
# Shared client transport
# ---------------------------------------------------------------------------

def test_first_draft_submit_uses_long_submit_timeouts():
    session = RecordingSession(payload={"submission_id": 1})
    client = WritingFeedbackApiClient("http://x", session=session)
    client.submit({"essay_text": "x"})
    assert session.calls[0]["timeout"] == (2.0, 180.0)
    assert session.calls[0]["method"] == "POST"


def test_linked_revision_still_uses_long_submit_timeouts():
    session = RecordingSession(payload={"submission_id": 1})
    client = WritingFeedbackApiClient("http://x", session=session)
    client.submit_linked_revision({"essay_text": "x"})
    assert session.calls[0]["timeout"] == (2.0, 180.0)


def test_both_public_entries_delegate_to_same_private_transport(monkeypatch):
    assert WritingFeedbackApiClient._submit_long_running.__name__ == "_submit_long_running"
    calls = []

    def spy(self, submission):
        calls.append(submission)
        return {"ok": True}

    monkeypatch.setattr(WritingFeedbackApiClient, "_submit_long_running", spy)
    client = WritingFeedbackApiClient("http://x", session=RecordingSession())
    client.submit({"kind": "first_draft"})
    client.submit_linked_revision({"kind": "linked_revision"})
    assert calls == [{"kind": "first_draft"}, {"kind": "linked_revision"}]


def test_ordinary_request_timeouts_unchanged():
    assert DEFAULT_TIMEOUTS == TimeoutProfile(connect=2.0, read=10.0, write=30.0)
    read_session = RecordingSession(payload={"submission_id": 1})
    client = WritingFeedbackApiClient("http://x", session=read_session)
    client.get_submission(1)
    assert read_session.calls[0]["timeout"] == (2.0, 10.0)
    health_session = RecordingSession(payload={"status": "ok"})
    client2 = WritingFeedbackApiClient("http://x", session=health_session)
    client2.health()
    assert health_session.calls[0]["timeout"] == (2.0, 5.0)


def test_no_automatic_retry_for_either_post():
    for method in ("submit", "submit_linked_revision"):
        session = RecordingSession(exc=requests.exceptions.ReadTimeout("slow"))
        client = WritingFeedbackApiClient("http://x", session=session)
        with pytest.raises(ApiClientError) as excinfo:
            getattr(client, method)({"essay_text": "x"})
        assert excinfo.value.category == ErrorCategory.REQUEST_TIMEOUT
        assert len(session.calls) == 1, method


def test_exactly_one_post_per_logical_submit():
    for method in ("submit", "submit_linked_revision"):
        session = RecordingSession(payload={"submission_id": 7})
        client = WritingFeedbackApiClient("http://x", session=session)
        getattr(client, method)({"essay_text": "x"})
        assert len(session.calls) == 1, method


def test_frontend_public_method_count_remains_56():
    client = WritingFeedbackApiClient(base_url="http://127.0.0.1:8000")
    methods = {
        name for name in dir(client)
        if not name.startswith("_") and callable(getattr(client, name))
    }
    assert len(methods) == 56
    assert {"submit", "submit_linked_revision"} <= methods
    assert "_submit_long_running" not in methods


# ---------------------------------------------------------------------------
# First-draft reconciliation (exact one-match rules)
# ---------------------------------------------------------------------------

class ReconcileClient:
    def __init__(self, candidates=None, bundle=None, raise_candidates=False, raise_bundle=False):
        self.candidates = candidates or []
        self.bundle = bundle
        self.raise_candidates = raise_candidates
        self.raise_bundle = raise_bundle

    def get_student_revision_candidates(self, student_id):
        if self.raise_candidates:
            raise ApiClientError(ErrorCategory.SERVICE_NOT_RUNNING, "down", operation="revision_candidates")
        return {"candidates": self.candidates}

    def get_submission(self, submission_id):
        if self.raise_bundle:
            raise ApiClientError(ErrorCategory.SERVICE_NOT_RUNNING, "down", operation="get_submission")
        return self.bundle


def _first_draft_row(essay_id=50, submitted_at="2026-08-03T11:30:00+00:00"):
    return {
        "essay_id": essay_id,
        "revision_of_submission_id": None,
        "revision_group_id": None,
        "revision_sequence": None,
        "submitted_at": submitted_at,
    }


def _bundle(essay_id=50, text=DRAFT_TEXT, feedback_present=True, student="S96D"):
    return {
        "essay_id": essay_id,
        "student_id": student,
        "essay_text": text,
        "feedback": {"priority_feedback": []} if feedback_present else None,
        "success_status": "success" if feedback_present else None,
    }


def _submission(text=DRAFT_TEXT, source=None):
    return {
        "student_id": "S96D",
        "writing_prompt": PROMPT,
        "genre": "argumentative essay",
        "essay_text": text,
        "revision_of_submission_id": source,
    }


def test_reconcile_first_draft_confirmed_success_exact_single_match():
    client = ReconcileClient(candidates=[_first_draft_row()], bundle=_bundle())
    assert _reconcile_writing_submission(client, "S96D", _submission(), None) == "CONFIRMED_SUCCESS"


def test_reconcile_first_draft_still_processing_when_downstream_incomplete():
    client = ReconcileClient(candidates=[_first_draft_row()], bundle=_bundle(feedback_present=False))
    assert _reconcile_writing_submission(client, "S96D", _submission(), None) == "STILL_PROCESSING"


def test_reconcile_first_draft_unconfirmed_zero_matches():
    client = ReconcileClient(candidates=[])
    assert _reconcile_writing_submission(client, "S96D", _submission(), None) == "UNCONFIRMED"


def test_reconcile_first_draft_unconfirmed_multiple_matches():
    client = ReconcileClient(
        candidates=[
            _first_draft_row(essay_id=50, submitted_at="2026-08-03T11:30:00+00:00"),
            _first_draft_row(essay_id=51, submitted_at="2026-08-03T11:31:00+00:00"),
        ],
        bundle=_bundle(),
    )
    assert _reconcile_writing_submission(client, "S96D", _submission(), None) == "UNCONFIRMED"


def test_reconcile_first_draft_unconfirmed_read_failure():
    client = ReconcileClient(raise_candidates=True)
    assert _reconcile_writing_submission(client, "S96D", _submission(), None) == "UNCONFIRMED"
    client = ReconcileClient(candidates=[_first_draft_row()], raise_bundle=True)
    assert _reconcile_writing_submission(client, "S96D", _submission(), None) == "UNCONFIRMED"


def test_reconcile_first_draft_unconfirmed_text_mismatch():
    client = ReconcileClient(
        candidates=[_first_draft_row()],
        bundle=_bundle(text="Completely different text."),
    )
    assert _reconcile_writing_submission(client, "S96D", _submission(), None) == "UNCONFIRMED"


def test_reconcile_first_draft_unconfirmed_student_mismatch():
    client = ReconcileClient(
        candidates=[_first_draft_row()],
        bundle=_bundle(student="OTHER"),
    )
    assert _reconcile_writing_submission(client, "S96D", _submission(), None) == "UNCONFIRMED"


def test_reconcile_first_draft_unconfirmed_baseline_blocks_older_rows():
    older = _first_draft_row(essay_id=49, submitted_at="2026-08-03T10:00:00+00:00")
    client = ReconcileClient(candidates=[older], bundle=_bundle(essay_id=49))
    assert _reconcile_writing_submission(client, "S96D", _submission(), "2026-08-03T11:00:00+00:00") == "UNCONFIRMED"


def test_reconcile_writing_revision_mode_matches_source_rows_only():
    row = {
        "essay_id": 60,
        "revision_of_submission_id": 5,
        "revision_group_id": "RG000001",
        "revision_sequence": 2,
        "submitted_at": "2026-08-03T11:30:00+00:00",
    }
    unrelated_first_draft = _first_draft_row(essay_id=61, submitted_at="2026-08-03T11:35:00+00:00")
    client = ReconcileClient(
        candidates=[row, unrelated_first_draft],
        bundle=_bundle(essay_id=60),
    )
    assert _reconcile_writing_submission(client, "S96D", _submission(source=5), None) == "CONFIRMED_SUCCESS"


def test_baseline_first_draft_mode_uses_null_source_rows():
    candidates = [
        {"essay_id": 1, "revision_of_submission_id": None, "submitted_at": "2026-08-03T10:00:00+00:00"},
        {"essay_id": 2, "revision_of_submission_id": 5, "submitted_at": "2026-08-03T12:00:00+00:00"},
    ]
    assert _submission_baseline(ReconcileClient(candidates=candidates), "S96D", _submission()) == "2026-08-03T10:00:00+00:00"


def test_baseline_revision_mode_uses_source_rows():
    candidates = [
        {"essay_id": 1, "revision_of_submission_id": None, "submitted_at": "2026-08-03T12:00:00+00:00"},
        {"essay_id": 2, "revision_of_submission_id": 5, "submitted_at": "2026-08-03T10:30:00+00:00"},
        {"essay_id": 3, "revision_of_submission_id": 5, "submitted_at": "2026-08-03T11:00:00+00:00"},
    ]
    assert _submission_baseline(ReconcileClient(candidates=candidates), "S96D", _submission(source=5)) == "2026-08-03T11:00:00+00:00"


def test_baseline_read_failure_returns_none():
    assert _submission_baseline(ReconcileClient(raise_candidates=True), "S96D", _submission()) is None


def test_reconciliation_code_has_no_file_io():
    for path in (
        ROOT / "app/ui/features/student/writing.py",
        ROOT / "app/ui/features/student/submit_reliability.py",
        ROOT / "app/ui/api_client.py",
    ):
        source = path.read_text(encoding="utf-8")
        assert "open(" not in source, path
        assert "write_text" not in source and "write_bytes" not in source, path


# ---------------------------------------------------------------------------
# Writing-page AppTest flows
# ---------------------------------------------------------------------------

def _run_writing_harness(**config):
    at = AppTest.from_file(str(HARNESS), default_timeout=90)
    for key, value in config.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, at.exception
    at.text_input(key="writing_student").set_value("S96D").run()
    assert not at.exception, at.exception
    at.text_area(key="writing_prompt_input").set_value(PROMPT).run()
    assert not at.exception, at.exception
    at.text_area(key="writing_essay").set_value(DRAFT_TEXT).run()
    assert not at.exception, at.exception
    return at


def _markdown_text(at) -> str:
    return " ".join(m.value for m in at.markdown)


def test_ui_first_draft_success_single_post_and_saved_state():
    at = _run_writing_harness(harness_behavior="success")
    at.button(key="writing_submit_primary").click().run()
    assert not at.exception, at.exception
    client = at.session_state["fake_client"]
    assert client.post_count == 1
    assert "Writing submitted" in _markdown_text(at)
    assert "writing_submit_pending" not in at.session_state


def test_ui_first_draft_unconfirmed_timeout_no_blind_retry():
    at = _run_writing_harness(harness_behavior="timeout")
    at.button(key="writing_submit_primary").click().run()
    assert not at.exception, at.exception
    client = at.session_state["fake_client"]
    assert client.post_count == 1
    text = _markdown_text(at)
    assert "timed out before the result could be confirmed" in text
    assert "Please try again" not in text
    assert "Retry" not in [b.label for b in at.button]
    assert "writing_submit_pending" in at.session_state  # held until consumed


def test_ui_first_draft_queued_click_consumed_without_second_post():
    at = _run_writing_harness(harness_behavior="timeout")
    at.button(key="writing_submit_primary").click().run()
    at.button(key="writing_submit_primary").click().run()
    client = at.session_state["fake_client"]
    assert client.post_count == 1


def test_ui_first_draft_pending_released_after_outcome_consumed():
    at = _run_writing_harness(harness_behavior="timeout")
    at.button(key="writing_submit_primary").click().run()
    at.button(key="writing_submit_primary").click().run()
    client = at.session_state["fake_client"]
    assert client.post_count == 1
    at.button(key="writing_submit_primary").click().run()
    assert client.post_count == 2  # deliberate new attempt works


def test_ui_first_draft_text_preserved_after_unconfirmed():
    at = _run_writing_harness(harness_behavior="timeout")
    at.button(key="writing_submit_primary").click().run()
    at.button(key="writing_submit_primary").click().run()
    text_area = next(ta for ta in at.text_area if ta.key == "writing_essay")
    assert text_area.value == DRAFT_TEXT


def test_ui_first_draft_confirmed_success_after_timeout():
    new_row = {
        "essay_id": 50,
        "student_id": "S96D",
        "revision_of_submission_id": None,
        "revision_group_id": None,
        "revision_sequence": None,
        "submitted_at": "2026-08-03T11:30:00+00:00",
    }
    at = _run_writing_harness(
        harness_behavior="timeout",
        harness_candidates_after=[new_row],
        harness_bundle_after=_bundle(),
    )
    at.button(key="writing_submit_primary").click().run()
    assert not at.exception, at.exception
    assert "The first draft was submitted successfully." in _markdown_text(at)


def test_ui_first_draft_still_processing_after_timeout():
    new_row = {
        "essay_id": 50,
        "student_id": "S96D",
        "revision_of_submission_id": None,
        "revision_group_id": None,
        "revision_sequence": None,
        "submitted_at": "2026-08-03T11:30:00+00:00",
    }
    at = _run_writing_harness(
        harness_behavior="timeout",
        harness_candidates_after=[new_row],
        harness_bundle_after=_bundle(feedback_present=False),
    )
    at.button(key="writing_submit_primary").click().run()
    assert not at.exception, at.exception
    assert "still being processed" in _markdown_text(at)


# ---------------------------------------------------------------------------
# Locale
# ---------------------------------------------------------------------------

def test_new_locale_keys_and_parity():
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
        "student_writing_submit_pending",
        "student_writing_timeout_confirmed_success",
        "student_writing_timeout_still_processing",
        "student_writing_timeout_unconfirmed",
    ):
        assert "/" + key in en_keys
        assert en[key] != zh[key]
# ---------------------------------------------------------------------------
# Integration: real local server, controlled slow provider
# ---------------------------------------------------------------------------

class _DelayHolder:
    def __init__(self):
        self.delay = 0.0


class _SlowProvider:
    provider_name = "slow-local"
    model_name = "slow-local-v096b"
    configured = True

    def __init__(self, inner, holder):
        self._inner = inner
        self._holder = holder

    def generate(self, messages, *, temperature):
        import time
        time.sleep(self._holder.delay)
        return self._inner.generate(messages, temperature=temperature)


@pytest.fixture(scope="module")
def api_env(tmp_path_factory):
    import socket
    import threading
    import time as _time
    from dataclasses import replace

    import uvicorn

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

    tmp = tmp_path_factory.mktemp("v096b")
    db_path = tmp / "api.db"
    settings = replace(load_settings(), database_path=db_path, llm_provider="local", deepseek_api_key=None)
    repository = Database(db_path)
    repository.initialize()
    holder = _DelayHolder()

    analyzer = build_analyzer(settings)
    progress = ProgressService(
        learner_repository=repository._learner_repository,
        configuration_repository=repository._configuration_repository,
    )
    profile = LearnerProfileService(repository=repository._learner_repository, progress_service=progress)
    service = SubmissionService(
        system_repository=repository._system_repository,
        submission_repository=repository._submission_repository,
        analysis_repository=repository._analysis_repository,
        calibration_repository=repository._calf_repository,
        analyzer=analyzer,
        diagnoser=NlpHeuristicDiagnoser(),
        router=ProviderRouter(
            _SlowProvider(LocalDemoProvider(), holder), LocalDemoProvider(),
            reliability=FeedbackReliabilityService(None),
        ),
        learner_profile_service=profile,
        revision_service=RevisionService(repository._revision_repository),
        calibrator=DiagnosticCalibrationService(ConfigurationPayload()),
        calf_configuration=ConfigurationPayload(),
    )
    app = create_app(settings, repository=repository, submission_service=service)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        try:
            requests.get(f"http://127.0.0.1:{port}/api/v1/system/health", timeout=1.0)
            break
        except Exception:
            _time.sleep(0.1)
    try:
        yield {"base": f"http://127.0.0.1:{port}", "repository": repository, "holder": holder}
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def test_controlled_slow_first_draft_succeeds_below_new_timeout(api_env):
    import time

    base, repository, holder = api_env["base"], api_env["repository"], api_env["holder"]
    holder.delay = 31.5  # longer than the old 30 s first-draft write timeout
    client = WritingFeedbackApiClient(base, timeouts=LONG_SUBMIT_TIMEOUTS)
    started = time.monotonic()
    result = client.submit({
        "student_id": "S96BSLOW", "writing_prompt": PROMPT, "genre": "argumentative essay",
        "draft_stage": "first draft", "timed": False, "time_limit_minutes": None,
        "active_writing_duration_seconds": None, "timing_source": "unknown",
        "timing_quality": "unavailable", "unexplained_interruption": False,
        "tool_use": "none", "essay_text": DRAFT_TEXT, "revision_of_submission_id": None,
    })
    elapsed = time.monotonic() - started
    assert elapsed >= 31.0
    bundle = repository._submission_repository.get_submission_bundle(int(result["submission_id"]))
    assert bundle is not None
    assert bundle["revision_of_submission_id"] is None
    assert bundle.get("feedback_id") is not None
    holder.delay = 0.0


def test_no_duplicate_first_draft_in_controlled_timeout_case(api_env):
    import time

    base, repository, holder = api_env["base"], api_env["repository"], api_env["holder"]
    holder.delay = 0.0
    client = WritingFeedbackApiClient(base, timeouts=LONG_SUBMIT_TIMEOUTS)
    holder.delay = 6.0
    with pytest.raises(ApiClientError) as excinfo:
        client._request(
            "POST", "/api/v1/submissions", operation="submit",
            json={
                "student_id": "S96BDUP", "writing_prompt": PROMPT, "genre": "argumentative essay",
                "draft_stage": "first draft", "timed": False, "time_limit_minutes": None,
                "active_writing_duration_seconds": None, "timing_source": "unknown",
                "timing_quality": "unavailable", "unexplained_interruption": False,
                "tool_use": "none", "essay_text": DRAFT_TEXT, "revision_of_submission_id": None,
            },
            profile=TimeoutProfile(connect=2.0, write=3.0),
        )
    assert excinfo.value.category == ErrorCategory.REQUEST_TIMEOUT
    holder.delay = 0.0
    deadline = time.monotonic() + 15.0
    bundle = None
    while time.monotonic() < deadline:
        rows = repository._submission_repository.list_student_submissions("S96BDUP")
        first_drafts = [r for r in rows if r.get("revision_of_submission_id") is None]
        if first_drafts:
            newest = max(first_drafts, key=lambda r: r["submitted_at"])
            bundle = repository._submission_repository.get_submission_bundle(int(newest["essay_id"]))
            if bundle and bundle.get("feedback_id") is not None:
                break
        time.sleep(0.25)
    assert bundle is not None and bundle.get("feedback_id") is not None
    drafts = [r for r in repository._submission_repository.list_student_submissions("S96BDUP")
              if r.get("revision_of_submission_id") is None]
    assert len(drafts) == 1
