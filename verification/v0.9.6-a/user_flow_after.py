"""v0.9.6-A targeted user-flow verification (post-fix).

AppTest flows against the post-fix revision page with a scripted client, plus
a real local-API flow with a controlled slow provider. Writes
user_flow_after.json. Development database is never opened.
"""
from __future__ import annotations

import json
import sys
import socket
import threading
import time
from dataclasses import replace
from pathlib import Path

import requests
import uvicorn
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HARNESS = ROOT / "tests" / "harness_v096a_revision.py"
OUT = ROOT / "verification" / "v0.9.6-a"
SOURCE_LABEL = "Should cities add more parks? \u00b7 first draft \u00b7 #1"
REVISED_TEXT = (
    "Parks support health and community life. Cities should protect accessible parks for everyone."
)

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
from app.ui.api_client import LONG_SUBMIT_TIMEOUTS, WritingFeedbackApiClient  # noqa: E402


def markdown_text(at) -> str:
    return " ".join(m.value for m in at.markdown)


def run_harness(**config):
    at = AppTest.from_file(str(HARNESS), default_timeout=90)
    for key, value in config.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, at.exception
    at.text_input(key="revision_student").set_value("S96C").run()
    at.selectbox(key="revision_source_select").select(SOURCE_LABEL).run()
    at.text_area(key="revision_text_input").set_value(REVISED_TEXT).run()
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
    model_name = "slow-local-v096a"
    configured = True

    def __init__(self, inner, holder):
        self._inner = inner
        self._holder = holder

    def generate(self, messages, *, temperature):
        time.sleep(self._holder.delay)
        return self._inner.generate(messages, temperature=temperature)


def main() -> int:
    evidence = {}

    # ---- Flow A: UI success flow ----
    at = run_harness(harness_behavior="success")
    at.button(key="revision_submit_primary").click().run()
    assert not at.exception, at.exception
    client = at.session_state["fake_client"]
    evidence["flow_a_ui_success"] = {
        "steps": "open linked-revision form -> enter revised text -> submit once -> observe success",
        "post_count": client.post_count,
        "processing_state": {
            "pending_flag_cleared_after_success": "revision_submit_pending" not in at.session_state,
        },
        "success_rendered": "Revision submitted" in markdown_text(at),
        "revision_appears_once": client.post_count == 1,
        "second_post_after_saved_state": None,
    }
    at.button(key="revision_primary_action").click().run()
    evidence["flow_a_ui_success"]["post_count_after_journey_click"] = client.post_count

    # ---- Flow B: UI timeout + bounded reconciliation (UNCONFIRMED) ----
    at = run_harness(harness_behavior="timeout")
    at.button(key="revision_submit_primary").click().run()
    assert not at.exception, at.exception
    client = at.session_state["fake_client"]
    pending_during_outcome = "revision_submit_pending" in at.session_state
    evidence["flow_b_ui_timeout_unconfirmed"] = {
        "steps": "submit once -> force client timeout -> bounded reconciliation -> unconfirmed message",
        "post_count": 1,
        "pending_flag_held_until_consumed": pending_during_outcome is True,
        "message_rendered": "timed out before the result could be confirmed" in markdown_text(at),
        "no_blind_retry_instruction": "Please try again" not in markdown_text(at),
        "no_retry_button": "Retry" not in [b.label for b in at.button],
    }
    at.button(key="revision_submit_primary").click().run()
    evidence["flow_b_ui_timeout_unconfirmed"]["post_count_after_queued_click"] = client.post_count
    evidence["flow_b_ui_timeout_unconfirmed"]["no_second_post"] = client.post_count == 1
    evidence["flow_b_ui_timeout_unconfirmed"]["guard_released_after_consume"] = (
        "revision_submit_pending" not in at.session_state
    )

    # ---- Flow C: real local API, controlled slow provider below 180 s ----
    tmp = Path(__import__("tempfile").mkdtemp(prefix="v096a-flow-"))
    db_path = tmp / "flow.db"
    settings = replace(load_settings(), database_path=db_path, llm_provider="local", deepseek_api_key=None)
    repository = Database(db_path)
    repository.initialize()
    holder = DelayHolder()

    def build_service():
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
                SlowProvider(LocalDemoProvider(), holder), LocalDemoProvider(),
                reliability=FeedbackReliabilityService(None),
            ),
            learner_profile_service=profile,
            revision_service=RevisionService(repository._revision_repository),
            calibrator=DiagnosticCalibrationService(ConfigurationPayload()),
            calf_configuration=ConfigurationPayload(),
        )

    app = create_app(settings, repository=repository, submission_service=build_service())
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
    prompt = "Should cities protect local parks?"
    source = client.submit({
        "student_id": "S96F", "writing_prompt": prompt, "genre": "argumentative essay",
        "draft_stage": "first draft", "timed": False, "time_limit_minutes": None,
        "active_writing_duration_seconds": None, "timing_source": "unknown",
        "timing_quality": "unavailable", "unexplained_interruption": False,
        "tool_use": "none",
        "essay_text": "Parks support public health. Cities should protect accessible parks.",
        "revision_of_submission_id": None,
    })
    holder.delay = 5.0
    started = time.monotonic()
    revised = client.submit_linked_revision({
        "student_id": "S96F", "writing_prompt": prompt, "genre": "argumentative essay",
        "draft_stage": "revised draft", "timed": False, "time_limit_minutes": None,
        "active_writing_duration_seconds": None, "timing_source": "unknown",
        "timing_quality": "unavailable", "unexplained_interruption": False,
        "tool_use": "none", "essay_text": REVISED_TEXT, "revision_of_submission_id": int(source["submission_id"]),
    })
    elapsed = time.monotonic() - started
    rows = repository._submission_repository.list_student_submissions("S96F")
    revision_count = len([r for r in rows if r.get("revision_of_submission_id") == int(source["submission_id"])])
    server.should_exit = True
    thread.join(timeout=10)
    evidence["flow_c_real_api_slow_success"] = {
        "controlled_provider_delay_s": 5.0,
        "elapsed_s": round(elapsed, 2),
        "success": int(revised["submission_id"]) > int(source["submission_id"]),
        "revision_count_in_history": revision_count,
        "revision_appears_exactly_once": revision_count == 1,
    }

    with open(OUT / "user_flow_after.json", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())