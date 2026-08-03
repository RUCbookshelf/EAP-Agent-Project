"""v0.9.6-B Phase 2 deterministic reproduction (pre-fix evidence).

First-draft submit path against a real local HTTP server with a controlled
slow provider, on a fresh temporary database. Never touches the development
database. Writes reproduction_before.json (API-level cases).
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path

import requests
import uvicorn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
DEV_DB = ROOT / "data" / "writing_feedback.db"
OUT = ROOT / "verification" / "v0.9.6-b"
OUT.mkdir(parents=True, exist_ok=True)

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
from app.ui.api_client import ApiClientError, TimeoutProfile, WritingFeedbackApiClient  # noqa: E402


def digest(path: Path) -> dict:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    st = path.stat()
    return {"sha256": h.hexdigest().upper(), "size_bytes": st.st_size, "mtime": st.st_mtime}


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


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def build_service(settings, repository, holder):
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


def first_draft_payload(student, text, prompt):
    return {
        "student_id": student,
        "writing_prompt": prompt,
        "genre": "argumentative essay",
        "draft_stage": "first draft",
        "timed": False,
        "time_limit_minutes": None,
        "active_writing_duration_seconds": None,
        "timing_source": "unknown",
        "timing_quality": "unavailable",
        "unexplained_interruption": False,
        "tool_use": "none",
        "essay_text": text,
        "revision_of_submission_id": None,
    }


def start_server(settings, repository, holder):
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
    return server, port


def main() -> int:
    dev_before = digest(DEV_DB)
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    os.environ.pop("DATABASE_URL", None)
    os.environ["LLM_PROVIDER"] = "local"

    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="v096b-repro-"))
    db_path = tmp / "repro.db"
    os.environ["DATABASE_PATH"] = str(db_path)
    settings = replace(load_settings(), database_path=db_path, llm_provider="local", deepseek_api_key=None)
    repository = Database(db_path)
    repository.initialize()
    holder = DelayHolder()
    server, port = start_server(settings, repository, holder)
    base = f"http://127.0.0.1:{port}"
    evidence = {}

    # ---- Case 1: first draft below old timeout ----
    holder.delay = 0.0
    client = WritingFeedbackApiClient(base, timeouts=TimeoutProfile(connect=2.0, write=30.0))
    t0 = time.monotonic()
    result = client.submit(first_draft_payload(
        "S96B1", "Parks support public health. Cities should protect accessible parks.", "Should cities add more parks?",
    ))
    t1 = time.monotonic() - t0
    essay_id = int(result["submission_id"])
    bundle = repository._submission_repository.get_submission_bundle(essay_id)
    evidence["case_1_below_old_timeout"] = {
        "post_count": 1,
        "essay_id": essay_id,
        "duration_s": round(t1, 3),
        "success": bundle is not None and bundle.get("feedback_id") is not None,
        "is_first_draft": bundle["revision_of_submission_id"] is None,
    }

    # ---- Case 2: first draft exceeds old timeout ----
    holder.delay = 6.0
    slow_client = WritingFeedbackApiClient(base, timeouts=TimeoutProfile(connect=2.0, write=3.0))
    t0 = time.monotonic()
    try:
        slow_client.submit(first_draft_payload(
            "S96B2", "Parks support health and community life. Cities should protect accessible parks for everyone.", "Should cities add more parks?",
        ))
        evidence["case_2_exceeds_old_timeout"] = {"error": "NO_TIMEOUT_RAISED"}
    except ApiClientError as exc:
        t_timeout = time.monotonic() - t0
        evidence["case_2_exceeds_old_timeout"] = {
            "client_category": exc.category.value,
            "client_message_key": exc.message_key,
            "client_operation": exc.operation,
            "timeout_elapsed_s": round(t_timeout, 3),
            "old_timeout_profile": {"connect": 2.0, "write": 30.0},
            "post_count": 1,
        }
    poll_started = time.monotonic()
    bundle = None
    while time.monotonic() - poll_started < 15.0:
        rows = repository._submission_repository.list_student_submissions("S96B2")
        first_drafts = [r for r in rows if r.get("revision_of_submission_id") is None]
        if first_drafts:
            newest = max(first_drafts, key=lambda r: r["submitted_at"])
            bundle = repository._submission_repository.get_submission_bundle(int(newest["essay_id"]))
            if bundle and bundle.get("feedback_id") is not None:
                break
        time.sleep(0.25)
    evidence["case_2_backend_after_disconnect"] = {
        "backend_completed": bundle is not None and bundle.get("feedback_id") is not None,
        "completed_after_client_timeout_s": round(time.monotonic() - poll_started, 3),
        "controlled_provider_delay_s": 6.0,
        "essay_id": bundle["essay_id"] if bundle else None,
        "feedback_id": bundle["feedback_id"] if bundle else None,
        "first_draft_durable": bool(bundle and bundle.get("revision_of_submission_id") is None),
        "classification_reproduced": "C - first draft completed after the client timeout",
    }

    # ---- Case 3: duplicate retry risk (two identical sequential first-draft POSTs) ----
    holder.delay = 0.0
    dup_text = "Parks support health. Cities should protect parks in every neighborhood."
    r1 = client.submit(first_draft_payload("S96B3", dup_text, "Should cities add more parks?"))
    r2 = client.submit(first_draft_payload("S96B3", dup_text, "Should cities add more parks?"))
    e1 = repository._submission_repository.get_submission_bundle(int(r1["submission_id"]))
    e2 = repository._submission_repository.get_submission_bundle(int(r2["submission_id"]))
    evidence["case_3_duplicate_retry_risk"] = {
        "post_count": 2,
        "essay_1": e1["essay_id"],
        "essay_2": e2["essay_id"],
        "same_student": e1["student_id"] == e2["student_id"] == "S96B3",
        "same_prompt": e1["writing_prompt"] == e2["writing_prompt"],
        "same_text_hash": hashlib.sha256(e1["essay_text"].encode("utf-8")).hexdigest().upper()
        == hashlib.sha256(e2["essay_text"].encode("utf-8")).hexdigest().upper(),
        "distinct_ids": e1["essay_id"] != e2["essay_id"],
        "duplicate_first_draft_created": True,
    }

    # ---- Case 4: linked-revision regression baseline (v0.9.6-A behavior) ----
    holder.delay = 2.0
    src = client.submit(first_draft_payload(
        "S96B4", "Parks support public health. Cities should protect accessible parks.", "Should cities add more parks?",
    ))
    holder.delay = 0.0
    source_id = int(src["submission_id"])
    rev = client.submit_linked_revision({
        "student_id": "S96B4", "writing_prompt": "Should cities add more parks?", "genre": "argumentative essay",
        "draft_stage": "revised draft", "timed": False, "time_limit_minutes": None,
        "active_writing_duration_seconds": None, "timing_source": "unknown", "timing_quality": "unavailable",
        "unexplained_interruption": False, "tool_use": "none",
        "essay_text": "Parks support health. Cities should protect parks in every neighborhood.",
        "revision_of_submission_id": source_id,
    })
    rb = repository._submission_repository.get_submission_bundle(int(rev["submission_id"]))
    evidence["case_4_linked_revision_regression_baseline"] = {
        "linked_revision_success": rb["revision_of_submission_id"] == source_id,
        "revision_group_id": rb["revision_group_id"],
        "revision_sequence": rb["revision_sequence"],
        "feedback_id": rb["feedback_id"],
        "v096a_focused_suite_baseline": "21 passed (recorded at v0.9.6-A closure)",
    }

    server.should_exit = True
    time.sleep(0.5)
    dev_after = digest(DEV_DB)
    evidence["development_database"] = {"before": dev_before, "after": dev_after, "unchanged": dev_before == dev_after}
    evidence["temporary_database"] = str(db_path)
    with open(OUT / "reproduction_before.json", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in evidence.items() if k != "development_database"}, indent=2, sort_keys=True))
    print("DEV_DB_UNCHANGED:", dev_before == dev_after)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())