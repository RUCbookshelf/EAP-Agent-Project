from __future__ import annotations

import ast
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "app" / "database" / "repository.py"
TARGET = ROOT / "app" / "infrastructure" / "sqlite" / "repositories"

GROUPS = {
    "submission.py": {
        "class": "SQLiteSubmissionRepository",
        "imports": """import json
from collections.abc import Callable
from typing import Any

from app.infrastructure.sqlite.connection import SQLiteConnectionManager
from app.models import EssaySubmission, HistoryResult, ProviderResult
""",
        "init": """    def __init__(self, connection_manager: SQLiteConnectionManager,
                 revision_stage_normalizer: Callable[[str], str]):
        self._connection_manager = connection_manager
        self._normalize_revision_stage = revision_stage_normalizer
""",
        "methods": [
            "save_essay", "save_feedback", "save_history", "prior_records",
            "get_feedback_record", "get_llm_calls", "get_history_record",
            "list_all_submissions", "get_submission_bundle",
            "list_student_submissions", "get_exercises",
        ],
        "private": [],
        "replace": {"self.normalize_revision_stage": "self._normalize_revision_stage"},
    },
    "practice.py": {
        "class": "SQLitePracticeRepository",
        "imports": """import json

from app.infrastructure.sqlite.connection import SQLiteConnectionManager
""",
        "init": """    def __init__(self, connection_manager: SQLiteConnectionManager):
        self._connection_manager = connection_manager
""",
        "methods": [
            "save_practice_target", "list_practice_targets", "get_practice_target",
            "save_exercise_instance", "list_exercise_instances", "get_exercise_instance",
            "save_exercise_attempt", "list_exercise_attempts", "save_practice_evaluation",
            "list_practice_evaluations", "list_practice_evaluations_by_student",
            "list_essays_by_student", "list_analysis_runs_for_student",
            "list_feedback_records_for_student", "list_exercise_attempts_by_student",
            "save_feedback_engagement_trace", "list_feedback_engagement_traces",
            "save_within_task_response_candidate", "list_within_task_responses",
            "save_transfer_evidence_candidate", "list_transfer_evidence_candidates",
            "save_practice_state_snapshot", "list_practice_state_snapshots",
        ],
        "private": ["_next_practice_id"],
        "replace": {},
    },
    "research.py": {
        "class": "SQLiteResearchRepository",
        "imports": """import json

from app.infrastructure.sqlite.connection import SQLiteConnectionManager
""",
        "init": """    def __init__(self, connection_manager: SQLiteConnectionManager):
        self._connection_manager = connection_manager
""",
        "methods": [
            "save_human_review", "list_human_reviews", "apply_pii_review",
            "save_export_job", "list_export_jobs", "get_export_job",
        ],
        "private": ["_next_research_id"],
        "replace": {},
    },
}


def main() -> None:
    source = subprocess.check_output(
        ["git", "show", "769e6d8:app/database/repository.py"],
        cwd=ROOT, text=True, encoding="utf-8",
    )
    tree = ast.parse(source)
    database = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Database")
    functions = {
        node.name: ast.get_source_segment(source, node)
        for node in database.body
        if isinstance(node, ast.FunctionDef)
    }
    TARGET.mkdir(parents=True, exist_ok=True)
    for filename, spec in GROUPS.items():
        blocks = []
        for name in [*spec["private"], *spec["methods"]]:
            block = functions[name]
            block = block.replace("self.connect()", "self._connection_manager.connect()")
            for old, new in spec["replace"].items():
                block = block.replace(old, new)
            block = textwrap.indent(block, "    ")
            blocks.append(block)
        content = (
            "from __future__ import annotations\n\n"
            + spec["imports"].rstrip()
            + "\n\n\nclass "
            + spec["class"]
            + ":\n"
            + spec["init"].rstrip()
            + "\n\n"
            + "\n\n".join(blocks)
            + "\n"
        )
        path = TARGET / filename
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
