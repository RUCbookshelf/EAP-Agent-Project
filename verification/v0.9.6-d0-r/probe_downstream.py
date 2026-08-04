from __future__ import annotations

"""v0.9.6-D0-R Phase 5 downstream read-path probe (audit-only).

Exercises the exact production read endpoints consumed by the Feedback,
Revision, Practice, and Home pages for the selected naturally generated
priority case (D0-01 / submission 1 / AUDIT-D0R-01) plus the no-priority
cases, and records structured consumption evidence.
"""

import json
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT / "downstream_consumability.json"
BASE_URL = "http://127.0.0.1:8001"


def get(path: str) -> dict:
    response = requests.get(f"{BASE_URL}{path}", timeout=20)
    return {"status": response.status_code, "body": response.json() if response.status_code == 200 else response.text[:200]}


def main() -> None:
    student = "AUDIT-D0R-01"
    submission_id = 1
    records = {}
    records["feedback_read_path"] = get(f"/api/v1/submissions/{submission_id}")
    records["diagnostic_audit_read_path"] = get(f"/api/v1/submissions/{submission_id}/diagnostic-audit")
    records["revision_candidates_student_path"] = get(f"/api/v1/students/{student}/revision-candidates")
    records["revision_candidates_submission_path"] = get(f"/api/v1/submissions/{submission_id}/revision-candidates")
    records["practice_targets_path"] = get(f"/api/v1/students/{student}/practice-targets")
    records["journey_path"] = get(f"/api/v1/students/{student}/journey")
    records["no_priority_case_feedback"] = get("/api/v1/submissions/3")
    records["control_case_feedback"] = get("/api/v1/submissions/5")

    # Structural checks for the selected priority case (D0-01, submission 1).
    submission = records["feedback_read_path"]["body"]
    feedback = submission.get("feedback") or {}
    priority_items = feedback.get("priority_feedback") if isinstance(feedback, dict) else None
    checks = {
        "submission_http_status_200": records["feedback_read_path"]["status"] == 200,
        "submission_id_matches": submission.get("submission_id") == submission_id,
        "student_id_matches": submission.get("student_id") == student,
        "priority_feedback_present": bool(priority_items),
        "priority_category": (priority_items or [{}])[0].get("category") if priority_items else None,
        "priority_diagnosis_id": (priority_items or [{}])[0].get("diagnosis_id") if priority_items else None,
        "priority_has_evidence_quote": bool((priority_items or [{}])[0].get("evidence_quote")) if priority_items else False,
        "priority_has_explanation": bool((priority_items or [{}])[0].get("explanation")) if priority_items else False,
        "priority_has_revision_guidance": bool((priority_items or [{}])[0].get("revision_guidance")) if priority_items else False,
        "duplicate_priority_heading_risk": len(priority_items or []) > 1,
        "practice_targets_auto_created": bool(records["practice_targets_path"]["body"]),
        "journey_state": (records["journey_path"]["body"] or {}).get("state"),
        "journey_next_action": (records["journey_path"]["body"] or {}).get("next_action"),
        "revision_candidates_status_200": records["revision_candidates_student_path"]["status"] == 200
        and records["revision_candidates_submission_path"]["status"] == 200,
        "no_priority_case_priority_count": len((records["no_priority_case_feedback"]["body"].get("feedback") or {}).get("priority_feedback") or []),
        "control_case_priority_count": len((records["control_case_feedback"]["body"].get("feedback") or {}).get("priority_feedback") or []),
    }
    output = {
        "audit_stage": "v0.9.6-D0-R",
        "phase": "Phase 5 - downstream read-path consumability (API level)",
        "selected_case": {"case_id": "D0-01", "submission_id": submission_id, "student_id": student},
        "endpoints_probed": {
            "feedback": "/api/v1/submissions/{id}",
            "diagnostic_audit": "/api/v1/submissions/{id}/diagnostic-audit",
            "revision_student": "/api/v1/students/{student_id}/revision-candidates",
            "revision_submission": "/api/v1/submissions/{id}/revision-candidates",
            "practice": "/api/v1/students/{student_id}/practice-targets",
            "journey": "/api/v1/students/{student_id}/journey",
        },
        "records": records,
        "checks": checks,
        "classification": "PARTIALLY_CONSUMABLE"
        if checks["practice_targets_auto_created"] is False
        else "CONSUMABLE",
        "note": "Practice-target auto-creation absence is recorded as a product capability gap (no production component creates practice targets from generated priorities); it is a v0.9.7 feature item unless it traps the student.",
    }
    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    print(json.dumps({"checks": checks, "classification": output["classification"]}, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
