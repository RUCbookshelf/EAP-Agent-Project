from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from app.config import load_settings
from app.database import Database
from app.models import EssaySubmission
from app.services import build_submission_service


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "diagnostic_calibration" / "first_draft.json"
REPORT = ROOT / "data" / "live_deepseek_v061_verification.json"


def verify(*, write_report: bool = True) -> dict:
    settings = load_settings()
    if settings.llm_provider != "deepseek" or not settings.deepseek_api_key:
        raise RuntimeError("DeepSeek is not configured in the local process environment.")
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    with TemporaryDirectory() as temp_dir:
        isolated = replace(settings, database_path=Path(temp_dir) / "live_v061.db")
        repository = Database(isolated.database_path); repository.initialize()
        result = build_submission_service(isolated, repository).submit(EssaySubmission.model_validate(fixture))
        provider = result.provider
        if provider.provider_name != "deepseek" or provider.success_status != "success":
            raise RuntimeError("DeepSeek v0.6.1 verification fell back or failed.")
        if provider.validation_status != "passed":
            raise RuntimeError("StructuredFeedback validation did not pass.")
        if provider.prompt_version != "feedback-prompt-v0.6.1":
            raise RuntimeError("The calibrated prompt version was not used.")
        bias = next(
            item for item in result.analysis.artifacts["lexical_features"]["repeated_content_word_details"]
            if item["lemma"] == "bias"
        )
        report = {
            "verification_time": datetime.now(timezone.utc).isoformat(),
            "status": "PASS", "provider": provider.provider_name, "model": provider.model_name,
            "prompt_version": provider.prompt_version, "schema_version": provider.schema_version,
            "validation_status": provider.validation_status, "retry_count": provider.retry_count,
            "fallback": False, "selected_priority_count": len(result.diagnosis.improvement_priorities),
            "exercise_count": len(provider.feedback.exercises),
            "bias_count": bias["count"], "bias_sentence_ids": bias["sentence_ids"],
            "bias_local_cluster": bias["local_cluster_detected"],
            "bias_selected": any(
                item.evidence_metadata.get("target_lemma") == "bias"
                for item in result.diagnosis.improvement_priorities
            ),
            "calibration_version": result.diagnostic_calibration.calibration_version,
            "configuration_version": result.analysis.configuration_version,
            "api_key_recorded": False, "raw_response_recorded": False,
        }
    if write_report:
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
