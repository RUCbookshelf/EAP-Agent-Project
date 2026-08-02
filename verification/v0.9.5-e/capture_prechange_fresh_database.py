from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.calf import ErrorAnnotation
from app.config import Settings
from app.database import Database
from app.models import EssaySubmission
from app.practice.service import PracticeService
from app.research.schemas import (
    HumanReviewCreate,
    HumanReviewDecision,
    HumanReviewTarget,
)
from app.research.service import ResearchDataService
from app.services import build_submission_service


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).with_name("prechange_fresh_database.json")
DEV_DB = (ROOT / "data" / "writing_feedback.db").resolve()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_sql(value: str | None) -> str | None:
    return " ".join(value.split()) if value else None


def schema_snapshot(connection: sqlite3.Connection) -> dict:
    objects = [
        {"type": row[0], "name": row[1], "table": row[2], "sql": normalize_sql(row[3])}
        for row in connection.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        ).fetchall()
    ]
    tables = sorted(item["name"] for item in objects if item["type"] == "table")
    indexes = [item for item in objects if item["type"] == "index"]
    columns = {
        table: [dict(row) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()]
        for table in tables
    }
    foreign_keys = {
        table: [dict(row) for row in connection.execute(f"PRAGMA foreign_key_list({table})").fetchall()]
        for table in tables
    }
    canonical = json.dumps(
        {"objects": objects, "columns": columns, "foreign_keys": foreign_keys},
        sort_keys=True,
        separators=(",", ":"),
    )
    return {
        "migration_version": int(connection.execute("PRAGMA user_version").fetchone()[0]),
        "tables": tables,
        "table_count": len(tables),
        "indexes": indexes,
        "index_count": len(indexes),
        "columns": columns,
        "foreign_keys": foreign_keys,
        "foreign_key_definition_count": sum(len(value) for value in foreign_keys.values()),
        "schema_fingerprint_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def empty_counts(connection: sqlite3.Connection, tables: list[str]) -> dict[str, int]:
    return {
        table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        for table in tables
    }


def representative_crud(database: Database, settings: Settings) -> dict:
    submission = EssaySubmission(
        student_id="V095E-PRE",
        writing_prompt="Should academic writers qualify uncertain claims?",
        genre="argumentative essay",
        draft_stage="first draft",
        timed=False,
        tool_use="none",
        essay_text=(
            "Academic writers should qualify uncertain claims because evidence can remain incomplete. "
            "However, careful qualification does not weaken a justified argument. "
            "Therefore, writers should distinguish observation from interpretation."
        ),
        submitted_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )
    result = build_submission_service(settings, database).submit(submission, synthetic=True)
    essay_id = result.essay_id

    analysis = database.get_latest_analysis_run(essay_id)
    units = database.list_analysis_units(essay_id, analysis["analysis_run_id"])
    annotation = ErrorAnnotation(
        submission_id=essay_id,
        start_offset=0,
        end_offset=8,
        original_text="Academic",
        error_category="verification_candidate",
        correction="Academic",
        annotation_source="human",
        annotation_status="confirmed",
        annotator_id="V095E",
        guideline_version="error-guideline-v0.8.0",
        confidence="high",
    )
    saved_annotations = database.save_error_annotations(essay_id, [annotation])
    revision_group = database.create_revision_group(essay_id)
    profile = database.get_latest_learner_profile(submission.student_id)

    practice = PracticeService(database)
    target = practice.create_practice_target(
        student_id=submission.student_id,
        source_submission_id=essay_id,
        source_diagnosis_id="D-PRE",
        target_code="lexical_repetition_local",
        target_label="Reduce concentrated lexical repetition",
        gate_status="selected",
    )
    target = database.save_practice_target(target)
    exercise = database.save_exercise_instance(practice.generate_exercise(target, submission.essay_text))
    attempt = database.save_exercise_attempt(
        practice.submit_attempt(exercise["exercise_id"], submission.student_id, "Writers can qualify uncertain claims.", 1)
    )
    evaluation = database.save_practice_evaluation(practice.evaluate_attempt(attempt, target, submission.essay_text))

    research = ResearchDataService(
        submission_reader=database._submission_repository,
        review_repository=database._research_repository,
        export_reader=database._research_repository,
    )
    review = research.create_human_review(HumanReviewCreate(
        target_type=HumanReviewTarget.DIAGNOSIS,
        target_id="D-PRE",
        reviewer_id="V095E",
        decision=HumanReviewDecision.PARTIALLY_CORRECT,
        confidence="medium",
        reason_code="prechange_repository_crud",
        comment="",
        guideline_version="human-review-v0.1",
    ))

    database.record_versions({"v095e_prechange_probe": "769e6d8"})
    return {
        "SystemRepository": {
            "ping": database.ping(),
            "migration_version": database.migration_version(),
            "version_record": database.get_system_versions().get("v095e_prechange_probe"),
        },
        "ConfigurationRepository": {
            "active_configuration": database.get_active_configuration().version,
        },
        "SubmissionRepository": {
            "essay_id": essay_id,
            "bundle_student_id": database.get_submission_bundle(essay_id)["student_id"],
            "feedback_id": database.get_feedback_record(essay_id)["feedback_id"],
        },
        "AnalysisRepository": {
            "analysis_run_id": analysis["analysis_run_id"],
            "metric_result_count": len(database.get_metric_results(analysis["analysis_run_id"])),
        },
        "CalfRepository": {
            "analysis_unit_count": len(units),
            "error_annotation_id": saved_annotations[0].error_annotation_id,
        },
        "RevisionRepository": {
            "revision_group_id": revision_group.revision_group_id,
            "members": revision_group.member_submission_ids,
        },
        "LearnerRepository": {
            "student_id": database.get_student(submission.student_id)["student_id"],
            "snapshot_id": profile.get("snapshot_id") if profile else None,
        },
        "PracticeRepository": {
            "practice_target_id": target["practice_target_id"],
            "exercise_id": exercise["exercise_id"],
            "attempt_id": attempt["attempt_id"],
            "evaluation_id": evaluation["evaluation_id"],
        },
        "ResearchRepository": {
            "review_id": review.review_id,
            "review_count": len(database.list_human_reviews("diagnosis", "D-PRE")),
        },
    }


def main() -> None:
    dev_before = {
        "path": str(DEV_DB),
        "size": DEV_DB.stat().st_size,
        "mtime_utc": DEV_DB.stat().st_mtime_ns,
        "sha256": sha256_file(DEV_DB),
    }
    with tempfile.TemporaryDirectory(prefix="v095e-prechange-") as temp_name:
        temp_root = Path(temp_name).resolve()
        database_path = (temp_root / "prechange.db").resolve()
        os.environ.pop("DATABASE_URL", None)
        os.environ["DATABASE_PATH"] = str(database_path)
        os.environ["LLM_PROVIDER"] = "local"
        print(f"effective_database_path={database_path}")
        assert database_path.is_relative_to(temp_root)
        assert database_path != DEV_DB
        assert ROOT / "data" not in database_path.parents
        settings = Settings(
            database_path=database_path,
            llm_provider="local",
            deepseek_api_key=None,
            deepseek_base_url="https://api.deepseek.com",
            deepseek_model="deepseek-chat",
        )
        assert settings.database_path.resolve() == database_path
        database = Database(settings.database_path)
        database.initialize()
        with database.connect() as connection:
            opened = Path(connection.execute("PRAGMA database_list").fetchone()[2]).resolve()
            assert opened == database_path
            schema = schema_snapshot(connection)
            counts_before = empty_counts(connection, schema["tables"])
            active = connection.execute(
                "SELECT version FROM configuration_versions WHERE status='active'"
            ).fetchone()[0]
        crud = representative_crud(database, settings)
        with database.connect() as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_key_violations = [dict(row) for row in connection.execute("PRAGMA foreign_key_check").fetchall()]
            counts_after = empty_counts(connection, schema["tables"])
        payload = {
            "format_version": 1,
            "baseline_commit": "769e6d8b516b18a6221d59c51ac5ff1f90d37058",
            "temporary_database_path": str(database_path),
            "temporary_directory": str(temp_root),
            "database_path_assertions": {
                "inside_temporary_directory": True,
                "not_development_database": True,
                "not_data_directory": True,
                "actual_opened_path_matches": True,
                "database_url_cleared": "DATABASE_URL" not in os.environ,
                "llm_provider": os.environ["LLM_PROVIDER"],
            },
            "schema": schema,
            "active_configuration": active,
            "empty_state_row_counts": counts_before,
            "representative_crud": crud,
            "post_crud_row_counts": counts_after,
            "integrity_check": integrity,
            "foreign_key_violations": foreign_key_violations,
            "development_database_before": dev_before,
        }
        OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    dev_after = {
        "size": DEV_DB.stat().st_size,
        "mtime_utc": DEV_DB.stat().st_mtime_ns,
        "sha256": sha256_file(DEV_DB),
    }
    payload["development_database_after"] = dev_after
    payload["development_database_unchanged"] = {
        "size": dev_before["size"] == dev_after["size"],
        "mtime": dev_before["mtime_utc"] == dev_after["mtime_utc"],
        "sha256": dev_before["sha256"] == dev_after["sha256"],
    }
    payload["temporary_database_removed"] = not Path(payload["temporary_database_path"]).exists()
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "migration": payload["schema"]["migration_version"],
        "tables": payload["schema"]["table_count"],
        "indexes": payload["schema"]["index_count"],
        "foreign_keys": payload["schema"]["foreign_key_definition_count"],
        "schema_fingerprint": payload["schema"]["schema_fingerprint_sha256"],
        "active_configuration": payload["active_configuration"],
        "integrity": payload["integrity_check"],
        "foreign_key_violations": len(payload["foreign_key_violations"]),
        "development_database_unchanged": payload["development_database_unchanged"],
        "temporary_database_removed": payload["temporary_database_removed"],
    }, indent=2))


if __name__ == "__main__":
    main()
