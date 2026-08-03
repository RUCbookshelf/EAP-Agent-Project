from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from app.config import load_settings
from app.feedback.service import FeedbackPipeline
from app.models import EssaySubmission


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def seed(database_path: Path) -> dict[str, int]:
    settings = load_settings()
    settings = type(settings)(**{**settings.__dict__, "database_path": database_path, "llm_provider": "local"})
    pipeline = FeedbackPipeline(settings)
    data = json.loads((PROJECT_ROOT / "data" / "demo_students.json").read_text(encoding="utf-8"))
    for student in data:
        for raw in student["submissions"]:
            submission = EssaySubmission(
                student_id=student["student_id"],
                submitted_at=datetime.fromisoformat(raw["submitted_at"].replace("Z", "+00:00")),
                **{key: value for key, value in raw.items() if key != "submitted_at"},
            )
            pipeline.submit(submission, synthetic=True)
    return pipeline.database._system_repository.counts()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=PROJECT_ROOT / "data" / "demo_writing_feedback.db")
    args = parser.parse_args()
    print(json.dumps(seed(args.database), indent=2))

