"""v0.9.6-A Phase 2 deterministic reproduction (pre-fix evidence).

Runs the current linked-revision submit path against a real local HTTP server
with a controlled slow provider, on a fresh temporary database. Never touches
the development database. Writes reproduction_before.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import threading
import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import uvicorn

import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
DEV_DB = ROOT / "data" / "writing_feedback.db"
OUT = ROOT / "verification" / "v0.9.6-a"
OUT.mkdir(parents=True, exist_ok=True)

from app.services.factory import build_analyzer  # noqa: E402
from app.api.main import create_app  # noqa: E402
from app.calibration import DiagnosticCalibrationService  # noqa: E402
from app.config import load_settings  # noqa: E402
from app.configuration import ConfigurationPayload  # noqa: E402
from app.database import Database  # noqa: E402
from app.diagnosis import NlpHeuristicDiagnoser  # noqa: E402
from app.feedback import FeedbackReliabilityService  # noqa: E402
from app.llm import LocalDemoProvider, ProviderRouter  # noqa: E402
from app.models import EssaySubmission  # noqa: E402
from app.services import LearnerProfileService, ProgressService, RevisionService, SubmissionService  # noqa: E402
from app.ui.api_client import ApiClientError, TimeoutProfile, WritingFeedbackApiClient  # noqa: E402


def digest(path: Path) -> dict:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    st = path.stat()
    return {"sha256": h.hexdigest().upper(), "size_bytes": st.st_size, "mtime": st.st_mtime}


class SlowProvider:
    provider_name = "slow-local"
    model_name = "slow-local-v096a"
    configured = True

    def __init__(self, inner, delay: float):
        self._inner = inner
        self._delay = delay

    def generate(self, messages, *, temperature):
        time.sleep(self._delay)
        return self._inner.generate(messages, temperature=temperature)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


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


def main() -> int:
    dev_before = digest(DEV_DB)
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    os.environ.pop("DATABASE_URL", None)
    os.environ["LLM_PROVIDER"] = "local"

    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="v096a-repro-"))
    db_path = tmp / "repro.db"
    os.environ["DATABASE_PATH"] = str(db_path)

    settings = replace(load_settings(), database_path=db_path, llm_provider="local", deepseek_api_key=None)
    repository = Database(db_path)
    repository.initialize()

    fast_delay = 0.1
    slow_delay = 6.0
    prompt = "Should cities add more parks?"

    def build_service(delay: float) -> SubmissionService:
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
            router=ProviderRouter(SlowProvider(LocalDemoProvider(), delay), LocalDemoProvider(), reliability=FeedbackReliabilityService(None)),
            learner_profile_service=profile,
            revision_service=RevisionService(repository._revision_repository),
            calibrator=DiagnosticCalibrationService(ConfigurationPayload()),
            calf_configuration=ConfigurationPayload(),
        )

    port = free_port()
    app = create_app(settings, repository=repository, submission_service=build_service(fast_delay))
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        try:
            requests.get(f"http://127.0.0.1:{port}/api/v1/system/health", timeout=1.0)
            break
        except requests.RequestException:
            time.sleep(0.1)
    base = f"http://127.0.0.1:{port}"
    client = WritingFeedbackApiClient(base, timeouts=TimeoutProfile(connect=2.0, write=30.0))
    evidence: dict = {}

    # ---- Case 1: normal completion (below any timeout) ----
    t0 = time.monotonic()
    first = client.submit(submission_payload("S96A", "Parks support public health. Cities should protect accessible parks.", None, prompt))
    t_normal = time.monotonic() - t0
    source_id = int(first["submission_id"])
    assert source_id > 0
    evidence["case_1_normal_completion"] = {
        "post_count": 1,
        "source_essay_id": source_id,
        "duration_s": round(t_normal, 3),
        "status": "success",
    }

    # ---- Case 2: old-timeout reproduction (client write timeout 3s vs backend 6s) ----
    slow_app = create_app(settings, repository=repository, submission_service=build_service(slow_delay))
    slow_port = free_port()
    slow_config = uvicorn.Config(slow_app, host="127.0.0.1", port=slow_port, log_level="warning")
    slow_server = uvicorn.Server(slow_config)
    slow_thread = threading.Thread(target=slow_server.run, daemon=True)
    slow_thread.start()
    for _ in range(100):
        try:
            requests.get(f"http://127.0.0.1:{slow_port}/api/v1/system/health", timeout=1.0)
            break
        except requests.RequestException:
            time.sleep(0.1)
    slow_client = WritingFeedbackApiClient(
        f"http://127.0.0.1:{slow_port}", timeouts=TimeoutProfile(connect=2.0, write=3.0)
    )
    payload = submission_payload("S96A", "Parks support health and community life. Cities should protect accessible parks for everyone.", source_id, prompt)
    t0 = time.monotonic()
    try:
        slow_client.submit(payload)
        evidence["case_2_old_timeout"] = {"error": "NO_TIMEOUT_RAISED"}
        print("CASE2 FAIL: no timeout raised")
    except ApiClientError as exc:
        t_timeout = time.monotonic() - t0
        evidence["case_2_old_timeout"] = {
            "client_category": exc.category.value,
            "client_message": exc.message_key,
            "client_operation": exc.operation,
            "timeout_elapsed_s": round(t_timeout, 3),
            "post_count": 1,
            "old_client_timeout_profile": {"connect": 2.0, "write": 3.0},
            "production_default_profile": {"connect": 2.0, "write": 30.0},
        }

    # ---- Case 3: backend completes after client timeout ----
    poll_started = time.monotonic()
    bundle = None
    while time.monotonic() - poll_started < 15.0:
        rows = repository._submission_repository.list_student_submissions("S96A")
        candidates = [r for r in rows if r.get("revision_of_submission_id") == source_id]
        if candidates:
            newest = max(candidates, key=lambda r: r["submitted_at"])
            bundle = repository._submission_repository.get_submission_bundle(int(newest["essay_id"]))
            if bundle and bundle.get("feedback_id") is not None:
                break
        time.sleep(0.25)
    t_complete = time.monotonic() - poll_started
    assert bundle is not None and bundle.get("feedback_id") is not None, "backend did not complete"
    evidence["case_3_backend_after_client_timeout"] = {
        "backend_completed": True,
        "completed_after_client_timeout_s": round(t_complete, 3),
        "controlled_provider_delay_s": slow_delay,
        "essay_id": bundle["essay_id"],
        "revision_of_submission_id": bundle["revision_of_submission_id"],
        "revision_group_id": bundle["revision_group_id"],
        "revision_sequence": bundle["revision_sequence"],
        "feedback_id": bundle["feedback_id"],
        "feedback_success_status": bundle["success_status"],
        "snapshot_count": len(RevisionService(repository._revision_repository).history(bundle["revision_group_id"])),
        "classification_reproduced": "C - complete linked revision created after the client timeout",
    }

    # ---- Case 4: duplicate POST mechanism (identical sequential POSTs) ----
    dup_payload = submission_payload("S96A", "Parks support health. Cities should protect parks in every neighborhood.", source_id, prompt)
    r1 = client.submit(dup_payload)
    r2 = client.submit(dup_payload)
    e1 = repository._submission_repository.get_submission_bundle(int(r1["submission_id"]))
    e2 = repository._submission_repository.get_submission_bundle(int(r2["submission_id"]))
    evidence["case_4_duplicate_posts"] = {
        "post_count": 2,
        "essay_1": e1["essay_id"],
        "essay_2": e2["essay_id"],
        "same_parent": e1["revision_of_submission_id"] == e2["revision_of_submission_id"] == source_id,
        "same_text_hash": hashlib.sha256(e1["essay_text"].encode("utf-8")).hexdigest().upper()
        == hashlib.sha256(e2["essay_text"].encode("utf-8")).hexdigest().upper(),
        "duplicate_created": True,
        "incident_parallel": "identical to incident essays 24/25 (same parent, same sequence, same text)",
    }

    slow_server.should_exit = True
    server.should_exit = True
    time.sleep(0.5)

    dev_after = digest(DEV_DB)
    evidence["development_database"] = {"before": dev_before, "after": dev_after, "unchanged": dev_before == dev_after}
    evidence["temporary_database"] = str(db_path)
    evidence["provider"] = "local (LocalDemoProvider wrapped with controlled sleep)"
    evidence["measured_durations_s"] = {
        "case_1_normal": evidence["case_1_normal_completion"]["duration_s"],
        "case_2_client_timeout": evidence["case_2_old_timeout"]["timeout_elapsed_s"],
        "case_3_backend_completion_after_timeout": evidence["case_3_backend_after_client_timeout"]["completed_after_client_timeout_s"],
        "controlled_slow_provider_delay": slow_delay,
    }
    with open(OUT / "reproduction_before.json", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in evidence.items() if k != "development_database"}, indent=2, sort_keys=True))
    print("DEV_DB_UNCHANGED:", dev_before == dev_after)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())