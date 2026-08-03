from __future__ import annotations

import json
from pathlib import Path

from app.database import Database


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def audit() -> dict[str, object]:
    report_path = PROJECT_ROOT / "data" / "live_deepseek_verification.json"
    database_path = PROJECT_ROOT / "data" / "live_deepseek_verification.db"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    database = Database(database_path)
    database.initialize()
    essay_ids = [int(value.removeprefix("E")) for value in report["submission_ids"]]
    first_id, second_id = essay_ids
    first_feedback = database._submission_repository.get_feedback_record(first_id)
    second_feedback = database._submission_repository.get_feedback_record(second_id)
    first_json = json.loads(first_feedback["feedback_json"])
    second_json = json.loads(second_feedback["feedback_json"])
    second_history = database._submission_repository.get_history_record(second_id)
    history_evidence = json.loads(second_history["history_evidence_json"])
    second_calls = database._submission_repository.get_llm_calls(second_id)

    assert report["status"] == "PASS"
    assert first_feedback["provider_name"] == "deepseek"
    assert first_feedback["validation_status"] == "passed"
    assert first_json["longitudinal"]["history_evidence_ids"] == []
    assert second_feedback["provider_name"] == "deepseek"
    assert second_feedback["success_status"] == "success"
    assert second_feedback["validation_status"] == "passed"
    assert second_feedback["retry_count"] == report["retry_count"]
    assert len(history_evidence) == report["second_request_history_evidence_count"]
    assert second_json["longitudinal"]["history_evidence_ids"] == report["returned_history_evidence_ids"]
    assert set(report["returned_history_evidence_ids"]) <= {
        item["history_evidence_id"] for item in history_evidence
    }
    assert len(second_calls) == 1
    assert second_calls[0]["provider_name"] == "deepseek"
    assert second_calls[0]["validation_status"] == "passed"
    assert second_calls[0]["retry_count"] == 0
    assert second_calls[0]["fallback_reason"] is None

    with database.connect() as connection:
        columns = {
            row[1]
            for table in ("feedback_records", "llm_call_records")
            for row in connection.execute(f"PRAGMA table_info({table})")
        }
    assert "api_key" not in columns
    return {
        "status": "PASS",
        "database_path": str(database_path),
        "submission_count": 2,
        "first_provider": first_feedback["provider_name"],
        "first_history_evidence_ids": [],
        "second_provider": second_feedback["provider_name"],
        "second_history_evidence_count": len(history_evidence),
        "second_returned_history_evidence_ids": report["returned_history_evidence_ids"],
        "second_validation_status": second_feedback["validation_status"],
        "second_retry_count": second_feedback["retry_count"],
        "fallback": False,
        "api_key_column_present": False,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))

