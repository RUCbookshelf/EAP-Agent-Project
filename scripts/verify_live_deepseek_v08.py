from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from time import perf_counter

from app.config import load_settings
from app.database import Database
from app.models import EssaySubmission
from app.services import CalfService, build_submission_service


ORDINARY_TEXT = (
    "City parks deserve stable public funding because they provide shared places for exercise, rest, and community events. "
    "A neighborhood without safe green space gives children and older residents fewer low-cost opportunities to be active. "
    "For example, a city can publish maintenance costs and attendance data before deciding which facilities need repairs. "
    "Some residents may prefer other spending priorities, but transparent evidence allows that concern to be weighed fairly. "
) * 3
SHORT_TEXT = "Public parks matter because communities need safe shared space."


def _submission(student: str, text: str, *, duration: float | None = None) -> EssaySubmission:
    now = datetime(2026, 7, 30, 8, 0, tzinfo=timezone.utc)
    return EssaySubmission(
        student_id=student,
        writing_prompt="Should cities protect public parks?",
        genre="argumentative essay",
        draft_stage="independent submission",
        timed=True,
        time_limit_minutes=45,
        tool_use="none",
        essay_text=text,
        submitted_at=now,
        active_writing_duration_seconds=duration,
        timing_source="client_timer" if duration else "unknown",
        timing_quality="verified" if duration else "unavailable",
    )


def _provider_status(result, latency_seconds: float) -> dict:
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
        "validation": result.provider.validation_status,
        "latency_seconds": round(latency_seconds, 3),
    }


def _metric(result, metric_id: str) -> dict:
    return next(item for item in result.analysis.metric_results if item["metric_id"] == metric_id)


def _assert_feedback_isolation(result) -> None:
    calf_only = {"mtld", "hdd", "writing_output_rate_wpm", "lexical_sophistication"}
    selected_ids = {item.diagnosis_id for item in result.provider.feedback.priority_feedback}
    selected_signals = [item for item in result.diagnosis.all_signals if item.diagnosis_id in selected_ids]
    assert all(calf_only.isdisjoint(signal.source_metrics) for signal in selected_signals)


def run_live_verification() -> dict:
    base = load_settings()
    if not base.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured in the local environment.")
    with tempfile.TemporaryDirectory(prefix="writing-feedback-v08-live-") as temp_dir:
        root = Path(temp_dir)

        deepseek_settings = replace(base, database_path=root / "deepseek.db", llm_provider="deepseek")
        deepseek_repo = Database(deepseek_settings.database_path)
        deepseek_repo.initialize()
        service = build_submission_service(
            deepseek_settings,
            system_repository=deepseek_repo._system_repository,
            submission_repository=deepseek_repo._submission_repository,
            analysis_repository=deepseek_repo._analysis_repository,
            calibration_repository=deepseek_repo._calf_repository,
            learner_repository=deepseek_repo._learner_repository,
            configuration_repository=deepseek_repo._configuration_repository,
            revision_repository=deepseek_repo._revision_repository,
        )

        started = perf_counter()
        live_a = service.submit(_submission("LIVE-V08-A", ORDINARY_TEXT), synthetic=True)
        report_a = _provider_status(live_a, perf_counter() - started)
        assert report_a["provider"] == "deepseek" and not report_a["fallback"]
        assert report_a["validation"] in {"passed", "passed_with_server_repair"}
        _assert_feedback_isolation(live_a)
        report_a.update({
            "analysis_version": live_a.analysis.analysis_version,
            "configuration_version": live_a.analysis.configuration_version,
            "migration_version": deepseek_repo._system_repository.migration_version(),
            "mtld_status": _metric(live_a, "mtld")["status"],
            "hdd_status": _metric(live_a, "hdd")["status"],
            "calf_priority_isolation": "passed",
        })

        started = perf_counter()
        live_b = service.submit(_submission("LIVE-V08-B", SHORT_TEXT), synthetic=True)
        report_b = _provider_status(live_b, perf_counter() - started)
        assert report_b["provider"] == "deepseek" and not report_b["fallback"]
        assert report_b["validation"] in {"passed", "passed_with_server_repair"}
        assert _metric(live_b, "hdd")["status"] == "insufficient_data"
        assert _metric(live_b, "hdd")["value"] is None
        _assert_feedback_isolation(live_b)
        report_b.update({"hdd_status": "insufficient_data", "hdd_value": None, "fake_zero": False})

        local_settings = replace(base, database_path=root / "local.db", llm_provider="local", deepseek_api_key=None)
        local_repo = Database(local_settings.database_path)
        local_repo.initialize()
        local_service = build_submission_service(
            local_settings,
            system_repository=local_repo._system_repository,
            submission_repository=local_repo._submission_repository,
            analysis_repository=local_repo._analysis_repository,
            calibration_repository=local_repo._calf_repository,
            learner_repository=local_repo._learner_repository,
            configuration_repository=local_repo._configuration_repository,
            revision_repository=local_repo._revision_repository,
        )
        live_c = local_service.submit(_submission("LIVE-V08-C", ORDINARY_TEXT), synthetic=True)
        c_wpm = _metric(live_c, "writing_output_rate_wpm")
        assert c_wpm["status"] == "insufficient_data" and c_wpm["value"] is None

        live_d = local_service.submit(_submission("LIVE-V08-D", ORDINARY_TEXT, duration=900), synthetic=True)
        d_wpm = _metric(live_d, "writing_output_rate_wpm")
        expected = _metric(live_d, "word_count")["value"] / 15
        assert d_wpm["status"] == "available"
        assert abs(d_wpm["value"] - expected) < 1e-12
        report_d = {
            "word_count": _metric(live_d, "word_count")["value"],
            "actual_duration_seconds": 900,
            "time_limit_minutes": 45,
            "wpm": d_wpm["value"],
            "reproducible_formula": "word_count / (actual_duration_seconds / 60)",
        }

        report_c = {
            "time_limit_minutes": 45,
            "actual_duration_seconds": None,
            "wpm_status": c_wpm["status"],
            "wpm_value": c_wpm["value"],
            "time_limit_used_as_duration": False,
        }
        calf_report = CalfService(
            calf_repository=local_repo._calf_repository,
            submission_reader=local_repo._submission_repository,
            analysis_reader=local_repo._analysis_repository,
            student_reader=local_repo._learner_repository,
        ).submission_report(live_d.essay_id)
        assert calf_report["interpretation_boundary"]
        assert calf_report["accuracy_annotation_availability"]["measurement_status"] == "unavailable"
        return {"live_a": report_a, "live_b": report_b, "live_c": report_c, "live_d": report_d}


if __name__ == "__main__":
    print(json.dumps(run_live_verification(), ensure_ascii=False, indent=2))
