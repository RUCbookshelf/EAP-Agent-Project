from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import Settings, load_settings
from app.feedback.service import FeedbackPipeline
from app.models import EssaySubmission


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    loaded = load_settings()
    settings = Settings(**{**loaded.__dict__, "database_path": PROJECT_ROOT / "data" / "verification.db"})
    pipeline = FeedbackPipeline(settings)
    timestamp = datetime.now(timezone.utc)
    shared = {
        "student_id": "VERIFY001",
        "writing_prompt": "Should universities provide more quiet study spaces?",
        "genre": "argumentative essay",
        "timed": False,
        "tool_use": "none",
    }
    first = pipeline.submit(EssaySubmission(
        **shared, draft_stage="first draft", submitted_at=timestamp,
        essay_text=(
            "Universities need quiet study spaces because students need places to focus. "
            "Students often study in busy buildings, and busy buildings make study difficult. "
            "Quiet spaces help students read, plan, and write. Therefore, universities should open more rooms."
        ),
    ))
    second = pipeline.submit(EssaySubmission(
        **shared, draft_stage="revised draft", submitted_at=timestamp + timedelta(seconds=1),
        essay_text=(
            "Universities should provide more quiet study spaces because learners complete different kinds of work on campus. "
            "Libraries support concentration, but available seats may disappear during assessment periods. For example, unused seminar rooms could become reservable study areas in the evening. "
            "However, silent rooms alone will not meet every need. Institutions should also maintain spaces for group discussion and accessible technology. "
            "A balanced plan would give students clear choices while using existing buildings efficiently."
        ),
    ))
    output = {
        "deepseek_key_configured": bool(loaded.deepseek_api_key),
        "first": {"essay_id": first.essay_id, "provider": first.provider.provider_name, "status": first.provider.success_status},
        "second": {
            "essay_id": second.essay_id, "provider": second.provider.provider_name,
            "status": second.provider.success_status, "comparable_history_count": second.comparable_history_count,
            "history_summary": second.history_summary,
        },
        "database_counts": pipeline.database._system_repository.counts(),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

