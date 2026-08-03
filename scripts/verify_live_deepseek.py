from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import Settings, load_settings
from app.feedback.service import FeedbackPipeline
from app.models import EssaySubmission


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = PROJECT_ROOT / "data" / "live_deepseek_verification.json"
BLOCKER_REPORT = PROJECT_ROOT / "data" / "live_deepseek_verification_blocker.json"


def run_live_verification(database_path: Path) -> dict[str, Any]:
    loaded = load_settings()
    if os.getenv("RUN_LIVE_LLM_TESTS") != "1":
        raise RuntimeError("RUN_LIVE_LLM_TESTS must equal 1")
    if not loaded.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    settings = Settings(**{
        **loaded.__dict__, "database_path": database_path, "llm_provider": "deepseek",
    })
    pipeline = FeedbackPipeline(settings)
    now = datetime.now(timezone.utc)
    student_id = f"LIVE-V011-{now.strftime('%Y%m%d%H%M%S%f')}"
    shared = {
        "student_id": student_id,
        "writing_prompt": "Should universities provide more quiet study spaces?",
        "genre": "argumentative essay",
        "draft_stage": "first draft",
        "timed": True,
        "time_limit_minutes": 30,
        "tool_use": "none",
    }
    first = pipeline.submit(EssaySubmission(
        **shared, submitted_at=now,
        essay_text=(
            "Universities should provide more quiet study spaces because students need places to focus. "
            "Busy buildings can make careful reading difficult. Libraries help, but seats are often limited. "
            "Therefore, universities should open unused rooms for quiet study during busy weeks."
        ),
    ))
    second = pipeline.submit(EssaySubmission(
        **shared, submitted_at=now + timedelta(seconds=1),
        essay_text=(
            "Universities should provide more quiet study spaces because students complete demanding work on campus. "
            "Libraries support concentration, but available seats may disappear during assessment periods. "
            "For example, unused seminar rooms could become reservable study areas in the evening. "
            "However, institutions should also maintain separate spaces for group discussion. "
            "Therefore, a balanced plan can give students clearer choices while using existing buildings efficiently."
        ),
    ))

    if first.provider.provider_name != "deepseek" or first.provider.success_status != "success":
        raise RuntimeError("First submission did not complete with DeepSeek")
    if first.history.comparability_status != "insufficient_history":
        raise RuntimeError("First submission history status was not insufficient_history")
    if first.provider.feedback.longitudinal.history_evidence_ids:
        raise RuntimeError("First response used history evidence despite insufficient history")
    if second.history.comparability_status != "comparable" or not second.history.history_evidence:
        raise RuntimeError("Second submission did not produce structured comparable history evidence")
    if second.provider.provider_name != "deepseek" or second.provider.success_status != "success":
        raise RuntimeError("Second submission silently fell back instead of completing with DeepSeek")
    valid_history_ids = {item.history_evidence_id for item in second.history.history_evidence}
    used_history_ids = second.provider.feedback.longitudinal.history_evidence_ids
    if not used_history_ids or not set(used_history_ids) <= valid_history_ids:
        raise RuntimeError("Second DeepSeek response did not bind valid history_evidence_id values")
    request_metadata = getattr(pipeline.router.primary, "last_request_metadata", {})
    request_history_count = request_metadata.get("history_evidence_count")
    if request_history_count != len(second.history.history_evidence):
        raise RuntimeError("DeepSeek transport did not record the expected second-request history evidence count")
    stored = pipeline.database._submission_repository.get_feedback_record(second.essay_id)
    if not stored or stored["provider_name"] != "deepseek" or stored["validation_status"] != "passed":
        raise RuntimeError("Validated second DeepSeek response was not stored correctly")

    return {
        "verification_time": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "submission_ids": [f"E{first.essay_id:06d}", f"E{second.essay_id:06d}"],
        "provider": second.provider.provider_name,
        "model": second.provider.model_name,
        "prompt_version": second.provider.prompt_version,
        "system_template_hash": second.provider.system_template_hash,
        "user_template_hash": second.provider.user_template_hash,
        "rendered_prompt_hash": second.provider.rendered_prompt_hash,
        "schema_version": second.provider.schema_version,
        "second_request_history_evidence_count": request_history_count,
        "returned_history_evidence_ids": used_history_ids,
        "validation_status": second.provider.validation_status,
        "retry_count": second.provider.retry_count,
        "fallback": second.provider.success_status == "fallback_success",
        "api_key_recorded": False,
        "sensitive_request_recorded": False,
    }


def write_blocker(reason: str) -> dict[str, Any]:
    report = {
        "verification_time": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_NOT_RUN",
        "reason": reason,
        "run_live_llm_tests_enabled": os.getenv("RUN_LIVE_LLM_TESTS") == "1",
        "deepseek_api_key_configured": bool(load_settings().deepseek_api_key),
        "api_key_recorded": False,
    }
    BLOCKER_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    try:
        report = run_live_verification(PROJECT_ROOT / "data" / "live_deepseek_verification.db")
    except RuntimeError as exc:
        report = write_blocker(str(exc))
        print(json.dumps(report, indent=2))
        return 2
    DEFAULT_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
