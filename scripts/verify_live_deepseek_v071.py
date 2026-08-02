from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
from time import perf_counter

from app.config import load_settings
from app.database import Database
from app.models import EssaySubmission
from app.services import build_submission_service


BASE_TEXT = (
    "A vague claim, a vague reason, and another vague claim appear together without enough specific support. "
    "Readers need concrete evidence because a general assertion cannot show how the proposal would work. "
    "For example, a writer can identify one consequence, explain who is affected, and connect the evidence to the claim. "
    "However, an opposing view should be represented fairly before the conclusion returns to the main position. "
) * 3


def _submission(student: str, prompt: str, day: int, *, stage: str = "independent submission",
                source: int | None = None, text: str = BASE_TEXT) -> EssaySubmission:
    return EssaySubmission(
        student_id=student, writing_prompt=prompt, genre="argumentative essay",
        draft_stage=stage, timed=True, time_limit_minutes=45, tool_use="none",
        essay_text=text, submitted_at=datetime(2026, 7, 1, tzinfo=timezone.utc) + timedelta(days=day),
        revision_of_submission_id=source,
    )


def _status(result, latency_seconds: float) -> dict:
    status = result.provider.feedback_provider_status
    return {
        "provider": status.provider,
        "model": status.model,
        "initial_validation": status.initial_validation_status,
        "correction_count": status.retry_count,
        "server_repair": status.server_repair_used,
        "server_repair_fields": status.server_repair_fields,
        "fallback": status.fallback_used,
        "fallback_reason_code": status.fallback_reason_code,
        "latency_seconds": round(latency_seconds, 3),
        "validation": result.provider.validation_status,
        "longitudinal_status": result.longitudinal_assessment.status,
        "history_evidence_ids": result.longitudinal_assessment.history_evidence_ids,
    }


def run_live_verification() -> dict:
    base = load_settings()
    if not base.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured in the local environment.")
    with tempfile.TemporaryDirectory(prefix="writing-feedback-v071-live-") as temp_dir:
        root = Path(temp_dir)

        settings_a = replace(base, database_path=root / "live-a.db", llm_provider="deepseek")
        repo_a = Database(settings_a.database_path); repo_a.initialize()
        start = perf_counter()
        live_a = build_submission_service(
            settings_a, repo_a, revision_repository=repo_a._revision_repository,
        ).submit(_submission(
            "LIVE-V071-A", "Should cities protect public parks?", 0,
        ), synthetic=True)
        report_a = _status(live_a, perf_counter() - start)
        assert report_a["provider"] == "deepseek" and not report_a["fallback"]
        assert report_a["validation"] in {"passed", "passed_with_server_repair"}
        assert report_a["longitudinal_status"] == "unavailable"
        assert report_a["history_evidence_ids"] == []

        settings_b_local = replace(base, database_path=root / "live-b.db", llm_provider="local", deepseek_api_key=None)
        repo_b = Database(settings_b_local.database_path); repo_b.initialize()
        first_b = build_submission_service(
            settings_b_local, repo_b, revision_repository=repo_b._revision_repository,
        ).submit(_submission(
            "LIVE-V071-B", "Should cities protect public parks?", 0, stage="first draft",
        ), synthetic=True)
        settings_b = replace(base, database_path=root / "live-b.db", llm_provider="deepseek")
        start = perf_counter()
        live_b = build_submission_service(
            settings_b, repo_b, revision_repository=repo_b._revision_repository,
        ).submit(_submission(
            "LIVE-V071-B", "Should cities protect public parks?", 1, stage="revised draft",
            source=first_b.essay_id,
            text=BASE_TEXT + " Therefore, city leaders should protect accessible parks in every neighborhood.",
        ), synthetic=True)
        report_b = _status(live_b, perf_counter() - start)
        assert report_b["provider"] == "deepseek" and not report_b["fallback"]
        assert report_b["longitudinal_status"] == "unavailable"
        assert live_b.revision_group_summary.draft_submission_count == 2
        assert live_b.revision_group_summary.independent_task_count == 1
        assert len(live_b.within_task_revision_trajectory.draft_chain) == 2
        assert live_b.provider.feedback.revision is not None
        assert "single draft analysis" not in live_b.longitudinal_assessment.comment.casefold()
        report_b["draft_count"] = live_b.revision_group_summary.draft_submission_count
        report_b["independent_task_count"] = live_b.revision_group_summary.independent_task_count

        settings_c_local = replace(base, database_path=root / "live-c.db", llm_provider="local", deepseek_api_key=None)
        repo_c = Database(settings_c_local.database_path); repo_c.initialize()
        local_c = build_submission_service(
            settings_c_local, repo_c, revision_repository=repo_c._revision_repository,
        )
        for index, prompt in enumerate((
            "Should schools require community service?",
            "Should cities limit private cars downtown?",
        )):
            local_c.submit(_submission("LIVE-V071-C", prompt, index * 14), synthetic=True)
        settings_c = replace(base, database_path=root / "live-c.db", llm_provider="deepseek")
        start = perf_counter()
        live_c = build_submission_service(
            settings_c, repo_c, revision_repository=repo_c._revision_repository,
        ).submit(_submission(
            "LIVE-V071-C", "Should universities record lectures?", 28,
        ), synthetic=True)
        report_c = _status(live_c, perf_counter() - start)
        available_ids = {item.history_evidence_id for item in live_c.history.history_evidence}
        assert report_c["provider"] == "deepseek" and not report_c["fallback"]
        assert report_c["longitudinal_status"] == "provisional_pattern"
        assert report_c["history_evidence_ids"]
        assert set(report_c["history_evidence_ids"]) <= available_ids
        assert "long-term trend" not in live_c.longitudinal_assessment.comment.casefold()
        assert "long term trend" not in live_c.longitudinal_assessment.comment.casefold()

        return {"live_a": report_a, "live_b": report_b, "live_c": report_c}


if __name__ == "__main__":
    print(json.dumps(run_live_verification(), ensure_ascii=False, indent=2))
