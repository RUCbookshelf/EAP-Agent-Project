from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import PROJECT_ROOT
from app.database import Database
from app.models import AnalysisResult, DiagnosisResult, DiagnosisSignal, EssaySubmission
from app.services import ProgressService


def metrics(word_count: int) -> dict:
    return {
        "word_count": word_count, "sentence_count": max(1, word_count // 10),
        "paragraph_count": 3, "average_sentence_length": 10,
        "unique_word_count": round(word_count * .7), "type_token_ratio": .7,
        "connective_count": max(1, word_count // 30), "repeated_content_words": {},
    }


def diagnosis(categories: list[str]) -> DiagnosisResult:
    signals = [DiagnosisSignal(
        diagnosis_id=f"D{index:03d}", category=category, evidence="Synthetic structured signal.",
        source_metrics=["word_count"], interpretation="This prototype signal may warrant review.",
        confidence="low", limitation="Synthetic heuristic test data.",
        rule_version="prototype-diagnosis-v0.1.1", kind="improvement",
    ) for index, category in enumerate(categories[:2], 1)]
    return DiagnosisResult(
        strengths=[], improvement_priorities=signals,
        diagnosis_version="prototype-diagnosis-v0.1.1", limitation="Synthetic heuristic test data.",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=PROJECT_ROOT / "data" / "demo_longitudinal.db")
    args = parser.parse_args()
    repository = Database(args.database); repository.initialize()
    source = json.loads((PROJECT_ROOT / "data" / "demo_longitudinal_students.json").read_text(encoding="utf-8"))
    summaries = []
    for student in source["students"]:
        student_id = student["student_id"]
        if repository._learner_repository.get_student(student_id) is None:
            for index, item in enumerate(student["submissions"]):
                essay_id = repository._submission_repository.save_essay(EssaySubmission(
                    student_id=student_id,
                    writing_prompt="Should cities protect public parks?",
                    genre=item.get("genre", "argumentative essay"),
                    draft_stage=item.get("draft_stage", "first draft"),
                    timed=item.get("timed", False),
                    time_limit_minutes=item.get("time_limit_minutes"),
                    tool_use=item.get("tool_use", "none"),
                    essay_text="This is repeatable synthetic text for longitudinal prototype verification.",
                    submitted_at=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index * 14),
                ), synthetic=True)
                repository._analysis_repository.save_analysis(essay_id, AnalysisResult(
                    metrics=metrics(item["word_count"]), analysis_version="basic-analyzer-v0.1",
                    limitations="Synthetic prototype metrics.",
                ))
                repository._analysis_repository.save_diagnosis(essay_id, diagnosis(item["categories"]))
        snapshot = ProgressService(repository).create_snapshot(student_id)
        summaries.append({
            "student_id": student_id, "snapshot_id": snapshot.snapshot_id,
            "baseline_status": snapshot.baseline_status,
            "included": len(snapshot.included_submission_ids),
            "word_count_direction": snapshot.metric_trends["word_count"].direction,
            "persistent": [x.diagnosis_category for x in snapshot.persistent_issues],
            "recently_reduced": [x.diagnosis_category for x in snapshot.recently_reduced_issues],
        })
    print(json.dumps({"status": "PASS", "database": str(args.database), "students": summaries}, indent=2))


if __name__ == "__main__":
    main()
