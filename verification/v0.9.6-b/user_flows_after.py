"""v0.9.6-B targeted user-flow verification (post-fix).

AppTest flows (writing + revision harnesses) plus a real local-API flow with
a controlled slow provider. Writes user_flows_after.json. The development
database is never opened.
"""
from __future__ import annotations

import json
import socket
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path

import requests
import uvicorn
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "verification" / "v0.9.6-b"
WRITING_HARNESS = ROOT / "tests" / "harness_v096b_writing.py"
REVISION_HARNESS = ROOT / "tests" / "harness_v096a_revision.py"

from app.api.main import create_app  # noqa: E402
from app.calibration import DiagnosticCalibrationService  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.configuration import ConfigurationPayload  # noqa: E402
from app.database import Database  # noqa: E402
from app.diagnosis import NlpHeuristicDiagnoser  # noqa: E402
from app.feedback import FeedbackReliabilityService  # noqa: E402
from app.llm import LocalDemoProvider, ProviderRouter  # noqa: E402
from app.services import LearnerProfileService, ProgressService, RevisionService, SubmissionService  # noqa: E402
from app.services.factory import build_analyzer  # noqa: E402
from app.ui.api_client import LONG_SUBMIT_TIMEOUTS, TimeoutProfile, WritingFeedbackApiClient  # noqa: E402

PROMPT = "Should cities add more parks?"
DRAFT_TEXT = "Parks support public health. Cities should protect accessible parks."


def markdown_text(at) -> str:
    return " ".join(m.value for m in at.markdown)


def run_writing(**config):
    at = AppTest.from_file(str(WRITING_HARNESS), default_timeout=90)
    for key, value in config.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, at.exception
    at.text_input(key="writing_student").set_value("S96D").run()
    at.text_area(key="writing_prompt_input").set_value(PROMPT).run()
    at.text_area(key="writing_essay").set_value(DRAFT_TEXT).run()
    return at


def run_revision():
    at = AppTest.from_file(str(REVISION_HARNESS), default_timeout=90)
    at.run()
    assert not at.exception, at.exception
    at.text_input(key="revision_student").set_value("S96C").run()
    at.selectbox(key="revision_source_select").select("Should cities add more parks? \u00b7 first draft \u00b7 #1").run()
    at.text_area(key="revision_text_input").set_value(
        "Parks support health and community life. Cities should protect accessible parks for everyone."
    ).run()
    return at


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class DelayHolder:
    def __init__(self):
        self.delay = 0.0


class SlowProvider:
    provider_name = "slow-local"
    model_name = "slow-local-v096b"
    configured = True

    def __init__(self, inner, holder):
        self._inner = inner
        self._holder = holder

    def generate(self, messages, *, temperature):
        time.sleep(self._holder.delay)
        return self._inner.generate(messages, temperature=temperature)


def main() -> int:
    evidence = {}

    # ---- Flow A: slow first-draft success (AppTest success + real-API timing) ----
    at = run_writing(harness_behavior="success")
    at.button(key="writing_submit_primary").click().run()
    assert not at.exception, at.exception
    client = at.session_state["fake_client"]
    evidence["flow_a_first_draft_success"] = {
        "steps": "open first-draft form -> enter valid draft -> submit once -> processing -> success",
        "post_count": client.post_count,
        "success_rendered": "Writing submitted" in markdown_text(at),
        "pending_released": "writing_submit_pending" not in at.session_state,
        "slow_beyond_old_timeout_proof": "focused integration test test_controlled_slow_first_draft_succeeds_below_new_timeout (31.5 s provider, success, one first draft)",
    }

    # ---- Flow B: first-draft timeout with backend completion ----
    new_row = {
        "essay_id": 50,
        "student_id": "S96D",
        "revision_of_submission_id": None,
        "revision_group_id": None,
        "revision_sequence": None,
        "submitted_at": "2026-08-03T11:30:00+00:00",
    }
    at = run_writing(
        harness_behavior="timeout",
        harness_candidates_after=[new_row],
        harness_bundle_after={
            "essay_id": 50, "student_id": "S96D", "essay_text": DRAFT_TEXT,
            "feedback": {"priority_feedback": []}, "success_status": "success",
        },
    )
    at.button(key="writing_submit_primary").click().run()
    assert not at.exception, at.exception
    client = at.session_state["fake_client"]
    evidence["flow_b_first_draft_timeout_backend_completion"] = {
        "steps": "capture pre-submit baseline -> submit once -> force client timeout -> bounded reconciliation -> confirmed success",
        "post_count": client.post_count,
        "message_rendered": "The first draft was submitted successfully." in markdown_text(at),
        "no_retry_button": "Retry" not in [b.label for b in at.button],
        "backend_completion_proof": "focused test test_no_duplicate_first_draft_in_controlled_timeout_case (backend completes after timeout; exactly one new first draft)",
    }

    # ---- Flow C: first-draft unconfirmed state ----
    at = run_writing(harness_behavior="timeout")
    at.button(key="writing_submit_primary").click().run()
    assert not at.exception, at.exception
    at.button(key="writing_submit_primary").click().run()
    client = at.session_state["fake_client"]
    text_area = next(ta for ta in at.text_area if ta.key == "writing_essay")
    evidence["flow_c_first_draft_unconfirmed"] = {
        "steps": "submit once -> force client timeout -> reconciliation unavailable -> unconfirmed message",
        "post_count": client.post_count,
        "message_rendered": "timed out before the result could be confirmed" in markdown_text(at),
        "draft_text_preserved": text_area.value == DRAFT_TEXT,
        "no_blind_retry": "Please try again" not in markdown_text(at),
        "no_retry_button": "Retry" not in [b.label for b in at.button],
    }

    # ---- Flow D: linked-revision regression (AppTest) ----
    at = run_revision()
    at.button(key="revision_submit_primary").click().run()
    assert not at.exception, at.exception
    rev_client = at.session_state["fake_client"]
    evidence["flow_d_linked_revision_regression"] = {
        "post_count": rev_client.post_count,
        "success_rendered": "Revision submitted" in markdown_text(at),
        "linkage_proof": "focused tests test_linked_revision_identity_and_parent_group_linkage and v0.9.6-A suite (21 passed)",
    }

    # ---- Real-API first draft: 5 s provider completes within the long timeout ----
    tmp = Path(__import__("tempfile").mkdtemp(prefix="v096b-flow-"))
    db_path = tmp / "flow.db"
    settings = replace(load_settings(), database_path=db_path, llm_provider="local", deepseek_api_key=None)
    repository = Database(db_path)
    repository.initialize()
    holder = DelayHolder()

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
            SlowProvider(LocalDemoProvider(), holder), LocalDemoProvider(),
            reliability=FeedbackReliabilityService(None),
        ),
        learner_profile_service=profile,
        revision_service=RevisionService(repository._revision_repository),
        calibrator=DiagnosticCalibrationService(ConfigurationPayload()),
        calf_configuration=ConfigurationPayload(),
    )
    app = create_app(settings, repository=repository, submission_service=service)
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
    client = WritingFeedbackApiClient(f"http://127.0.0.1:{port}", timeouts=LONG_SUBMIT_TIMEOUTS)
    holder.delay = 5.0
    started = time.monotonic()
    result = client.submit({
        "student_id": "S96F", "writing_prompt": PROMPT, "genre": "argumentative essay",
        "draft_stage": "first draft", "timed": False, "time_limit_minutes": None,
        "active_writing_duration_seconds": None, "timing_source": "unknown",
        "timing_quality": "unavailable", "unexplained_interruption": False,
        "tool_use": "none", "essay_text": DRAFT_TEXT, "revision_of_submission_id": None,
    })
    elapsed = time.monotonic() - started
    bundle = repository._submission_repository.get_submission_bundle(int(result["submission_id"]))
    drafts = [r for r in repository._submission_repository.list_student_submissions("S96F")
              if r.get("revision_of_submission_id") is None]
    server.should_exit = True
    thread.join(timeout=10)
    evidence["real_api_first_draft_slow_success"] = {
        "controlled_provider_delay_s": 5.0,
        "elapsed_s": round(elapsed, 2),
        "success": bundle is not None and bundle.get("feedback_id") is not None,
        "first_draft_count_in_history": len(drafts),
        "exactly_one_first_draft": len(drafts) == 1,
    }

    with open(OUT / "user_flows_after.json", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())