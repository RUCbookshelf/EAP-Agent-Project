"""Deterministic synthetic Learning Journey setup (v0.9.3-C).

Creates, reports, or removes one clearly marked synthetic demo learner
(DEMO-001) and the complete conservative journey records through normal
service/repository pathways with the local deterministic provider only.

Usage:
    .venv\\Scripts\\python.exe scripts/demo_journey.py --setup
    .venv\\Scripts\\python.exe scripts/demo_journey.py --status
    .venv\\Scripts\\python.exe scripts/demo_journey.py --cleanup

Never runs automatically at application startup. Cleanup deletes only records
belonging to DEMO-001. No secrets are printed.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import sqlite3
import sys
from datetime import datetime, timezone

os.environ.setdefault("LLM_PROVIDER", "local")
os.environ.setdefault("PYTHONUTF8", "1")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import load_settings  # noqa: E402
from app.database import Database  # noqa: E402
from app.journey.service import JourneyService  # noqa: E402
from app.models import EssaySubmission  # noqa: E402
from app.practice.service import PracticeService  # noqa: E402
from app.services import build_submission_service  # noqa: E402

DEMO_LEARNER = "DEMO-001"
DEMO_PROMPT = "What actions matter for sustainability?"
DEMO_ESSAY = (
    "People should protect the environment. People should recycle more. "
    "People should save water. People should plant trees. People should reduce waste. "
    "People should use public transport. People should teach children about nature. "
    "People should value clean air."
)
DEMO_REVISED = (
    "Citizens should protect the environment. Communities can recycle more and save water. "
    "Families may plant trees and reduce waste. Schools can encourage public transport "
    "and teach children about nature. Everyone should value clean air."
)
DEMO_ATTEMPT = (
    "People can protect the environment by recycling more and saving water. "
    "Communities may plant trees and reduce waste. Schools can encourage public transport "
    "and teach children about nature, so everyone can value clean air."
)
# Diagnosis category -> supported practice target code.
TARGET_CODE_MAP = {
    "lexical_repetition": "lexical_repetition_local",
    "connective_use": "connective_overuse",
    "sentence_length_pattern": "long_sentence",
}


def _repository() -> Database:
    # When an explicit DATABASE_PATH is given, mirror it into DATABASE_URL so
    # the .env DATABASE_URL cannot redirect the script to the default database
    # (load_dotenv re-adds keys that are absent from the environment).
    if os.getenv("DATABASE_PATH"):
        os.environ["DATABASE_URL"] = f"sqlite:///{os.environ['DATABASE_PATH']}"
    settings = load_settings()
    return Database(settings.database_path)


def _manifest_path(repository: Database) -> pathlib.Path:
    return repository.path.parent / "demo_journey_manifest.json"


def _ensure_synthetic_student(repository: Database) -> None:
    if repository.get_student(DEMO_LEARNER) is None:
        with repository.connect() as conn:
            conn.execute(
                "INSERT INTO students (student_id, created_at, is_synthetic) VALUES (?, ?, 1)",
                (DEMO_LEARNER, datetime.now(timezone.utc).isoformat()),
            )
        print(f"Created synthetic learner {DEMO_LEARNER} (is_synthetic=1).")


def _backup_database(repository: Database) -> pathlib.Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = repository.path.with_name(f"writing_feedback.pre-v0.9.3c-{stamp}.db")
    src = sqlite3.connect(repository.path)
    dst = sqlite3.connect(backup)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return backup


def setup() -> int:
    repository = _repository()
    journey = JourneyService(repository)
    try:
        existing = journey.get_journey(DEMO_LEARNER)
    except LookupError:
        existing = {"counts": {}}
    counts = existing.get("counts") or {}
    fully_set_up = (
        int(counts.get("practice_targets") or 0) > 0
        and int(counts.get("exercise_attempts") or 0) > 0
        and int(counts.get("practice_evaluations") or 0) > 0
        and int(counts.get("within_task_responses") or 0) > 0
        and int(counts.get("submissions") or 0) >= 2
    )
    if fully_set_up:
        print(f"Demo journey already exists for {DEMO_LEARNER}; setup is idempotent (skipped).")
        print(json.dumps(counts, indent=2))
        _write_manifest(repository, journey.get_journey(DEMO_LEARNER))
        return 0

    backup = _backup_database(repository)
    print(f"Database backup created: {backup.name}")
    try:
        _ensure_synthetic_student(repository)

        settings = load_settings()
        submission_service = build_submission_service(settings, repository)
        practice_service = PracticeService(repository)

        original = EssaySubmission(
            student_id=DEMO_LEARNER,
            writing_prompt=DEMO_PROMPT,
            genre="argumentative essay",
            draft_stage="first draft",
            timed=False,
            tool_use="none",
            essay_text=DEMO_ESSAY,
            submitted_at=datetime.now(timezone.utc),
        )
        result = submission_service.submit(original, synthetic=True)
        essay_id = result.essay_id

        priority = None
        for signal in result.diagnosis.improvement_priorities:
            if getattr(signal, "selection_status", "") == "selected_priority":
                priority = signal
                break
        if priority is None:
            print("FAIL: no selected priority passed the Diagnostic Gate for the demo fixture.")
            print("Empty states:", result.ui_empty_states)
            _cleanup(repository)
            return 1

        target_code = TARGET_CODE_MAP.get(priority.category, priority.category)
        target = practice_service.create_practice_target(
            student_id=DEMO_LEARNER,
            source_submission_id=essay_id,
            source_diagnosis_id=priority.diagnosis_id,
            target_code=target_code,
            target_label=priority.interpretation,
            source_priority_id=f"PRIO-{essay_id}",
            evidence_ids=getattr(priority, "source_metrics", []) or [],
            gate_status="selected",
        )
        target = repository.save_practice_target(target)

        exercise = practice_service.generate_exercise(target, DEMO_ESSAY)
        if exercise.get("status") == "practice_not_available":
            raise RuntimeError(f"Exercise generation unavailable for target code '{target_code}': {exercise.get('reason')}")
        exercise = repository.save_exercise_instance(exercise)

        attempt = practice_service.submit_attempt(exercise["exercise_id"], DEMO_LEARNER, DEMO_ATTEMPT, 1)
        attempt = repository.save_exercise_attempt(attempt)
        evaluation = practice_service.evaluate_attempt(attempt, target, DEMO_ESSAY)
        evaluation = repository.save_practice_evaluation(evaluation)

        revised = EssaySubmission(
            student_id=DEMO_LEARNER,
            writing_prompt=DEMO_PROMPT,
            genre="argumentative essay",
            draft_stage="revised draft",
            timed=False,
            tool_use="none",
            essay_text=DEMO_REVISED,
            revision_of_submission_id=essay_id,
            submitted_at=datetime.now(timezone.utc),
        )
        revised_result = submission_service.submit(revised, synthetic=True)
        group_id = None
        if revised_result.revision_group_summary:
            group_id = revised_result.revision_group_summary.revision_group_id
        if not group_id and revised_result.revision_snapshot:
            group_id = revised_result.revision_snapshot.revision_group_id
        response = practice_service.evaluate_within_task_response(
            student_id=DEMO_LEARNER,
            practice_target=target,
            source_submission_id=essay_id,
            later_submission_id=revised_result.essay_id,
            revision_group_id=group_id,
            major_rewrite=False,
        )
        response = repository.save_within_task_response_candidate(response)
    except Exception as exc:  # noqa: BLE001 - roll back partial demo state
        print(f"FAIL: demo setup error: {type(exc).__name__}: {exc}")
        _cleanup(repository)
        return 1

    journey = journey.get_journey(DEMO_LEARNER)
    manifest = {
        "learner": DEMO_LEARNER,
        "backup": backup.name,
        "prompt": DEMO_PROMPT,
        "created": {
            "student": DEMO_LEARNER,
            "original_essay_id": essay_id,
            "analysis_run_ids": [r["analysis_run_id"] for r in repository.list_analysis_runs_for_student(DEMO_LEARNER)],
            "priority_category": priority.category,
            "practice_target_id": target["practice_target_id"],
            "exercise_id": exercise["exercise_id"],
            "attempt_id": attempt["attempt_id"],
            "evaluation_id": evaluation["evaluation_id"],
            "revised_essay_id": revised_result.essay_id,
            "within_task_response_id": response["response_id"],
            "revision_group_id": group_id,
        },
        "journey_state": journey["state"],
        "journey_counts": journey["counts"],
        "policy": "Synthetic demo records only. Cleanup removes only DEMO-001 records.",
    }
    _manifest_path(repository).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Demo journey created for {DEMO_LEARNER}.")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


def status() -> int:
    repository = _repository()
    journey = JourneyService(repository).get_journey(DEMO_LEARNER)
    print(f"Learner: {DEMO_LEARNER}")
    print(f"State: {journey['state']}")
    print("Counts:", json.dumps(journey["counts"], indent=2))
    print("Events:", len(journey["events"]))
    manifest = _manifest_path(repository)
    if manifest.exists():
        print("Manifest:", manifest.name)
    return 0


def _write_manifest(repository: Database, journey: dict) -> None:
    """Rebuild the manifest for an existing demo journey (idempotent setup)."""
    with repository.connect() as conn:
        essays = [r[0] for r in conn.execute(
            "SELECT essay_id FROM essays WHERE student_id=? ORDER BY essay_id", (DEMO_LEARNER,))]
        targets = [r[0] for r in conn.execute(
            "SELECT practice_target_id FROM practice_targets WHERE student_id=?", (DEMO_LEARNER,))]
        attempts = [r[0] for r in conn.execute(
            "SELECT attempt_id FROM exercise_attempts WHERE student_id=?", (DEMO_LEARNER,))]
        evaluations = [r[0] for r in conn.execute(
            "SELECT evaluation_id FROM practice_evaluations WHERE attempt_id IN "
            f"({','.join('?' * len(attempts))})", attempts)] if attempts else []
        responses = [r[0] for r in conn.execute(
            "SELECT response_id FROM within_task_response_candidates WHERE student_id=?", (DEMO_LEARNER,))]
        groups = [r[0] for r in conn.execute(
            "SELECT DISTINCT revision_group_id FROM essays WHERE student_id=? AND revision_group_id IS NOT NULL",
            (DEMO_LEARNER,))]
    manifest = {
        "learner": DEMO_LEARNER,
        "created": {
            "student": DEMO_LEARNER,
            "essay_ids": essays,
            "practice_target_ids": targets,
            "attempt_ids": attempts,
            "evaluation_ids": evaluations,
            "within_task_response_ids": responses,
            "revision_group_ids": groups,
        },
        "journey_state": journey.get("state"),
        "journey_counts": journey.get("counts"),
        "policy": "Synthetic demo records only. Cleanup removes only DEMO-001 records.",
    }
    _manifest_path(repository).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _cleanup(repository: Database, *, quiet: bool = False) -> dict[str, int]:
    deleted: dict[str, int] = {}
    with repository.connect() as conn:
        essay_ids = [r[0] for r in conn.execute("SELECT essay_id FROM essays WHERE student_id=?", (DEMO_LEARNER,))]
        run_ids = [r[0] for r in conn.execute(f"SELECT analysis_run_id FROM analysis_runs WHERE essay_id IN ({','.join('?' * len(essay_ids))})", essay_ids)] if essay_ids else []
        group_ids = [r[0] for r in conn.execute("SELECT DISTINCT revision_group_id FROM essays WHERE student_id=? AND revision_group_id IS NOT NULL", (DEMO_LEARNER,))]
        target_ids = [r[0] for r in conn.execute("SELECT practice_target_id FROM practice_targets WHERE student_id=?", (DEMO_LEARNER,))]
        attempt_ids = [r[0] for r in conn.execute("SELECT attempt_id FROM exercise_attempts WHERE student_id=?", (DEMO_LEARNER,))]

        plan = [
            ("analysis_artifacts", "analysis_run_id", run_ids),
            ("analysis_units", "analysis_run_id", run_ids),
            ("metric_results", "analysis_run_id", run_ids),
            ("llm_call_records", "essay_id", essay_ids),
            ("error_annotations", "submission_id", essay_ids),
            ("exercises", "essay_id", essay_ids),
            ("metrics", "essay_id", essay_ids),
            ("diagnoses", "essay_id", essay_ids),
            ("diagnostic_calibrations", "essay_id", essay_ids),
            ("feedback_records", "essay_id", essay_ids),
            ("analysis_runs", "essay_id", essay_ids),
            ("learner_history", "student_id", [DEMO_LEARNER]),
            ("history_evidence_registry", "student_id", [DEMO_LEARNER]),
            ("learner_profile_snapshots", "student_id", [DEMO_LEARNER]),
            ("practice_evaluations", "attempt_id", attempt_ids),
            ("practice_evaluations", "practice_target_id", target_ids),
            ("exercise_attempts", "student_id", [DEMO_LEARNER]),
            ("exercise_instances", "student_id", [DEMO_LEARNER]),
            ("within_task_response_candidates", "student_id", [DEMO_LEARNER]),
            ("transfer_evidence_candidates", "student_id", [DEMO_LEARNER]),
            ("feedback_engagement_traces", "student_id", [DEMO_LEARNER]),
            ("practice_state_snapshots", "student_id", [DEMO_LEARNER]),
            ("practice_targets", "student_id", [DEMO_LEARNER]),
            ("revision_snapshots", "revision_group_id", group_ids),
            ("revision_groups", "student_id", [DEMO_LEARNER]),
        ]
        for table, column, ids in plan:
            if not ids:
                continue
            if table == "practice_evaluations" and column == "practice_target_id" and ids == target_ids and target_ids and attempt_ids:
                # Avoid double counting rows already removed via attempt_id.
                cur = conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {column} IN ({','.join('?' * len(ids))}) "
                    f"AND attempt_id NOT IN ({','.join('?' * len(attempt_ids))})",
                    ids + attempt_ids,
                )
            else:
                cur = conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {column} IN ({','.join('?' * len(ids))})", ids
                )
            n = cur.fetchone()[0]
            if n:
                if table == "practice_evaluations" and column == "practice_target_id" and ids == target_ids and target_ids and attempt_ids:
                    conn.execute(
                        f"DELETE FROM {table} WHERE {column} IN ({','.join('?' * len(ids))}) "
                        f"AND attempt_id NOT IN ({','.join('?' * len(attempt_ids))})",
                        ids + attempt_ids,
                    )
                else:
                    conn.execute(f"DELETE FROM {table} WHERE {column} IN ({','.join('?' * len(ids))})", ids)
                deleted[f"{table}.{column}"] = deleted.get(f"{table}.{column}", 0) + n
        # Essays: revisions first (self-referencing FK), then remaining drafts.
        revision_essay_ids = [
            r[0] for r in conn.execute(
                "SELECT essay_id FROM essays WHERE student_id=? AND revision_of_submission_id IS NOT NULL",
                (DEMO_LEARNER,),
            )
        ]
        if revision_essay_ids:
            conn.execute(
                f"DELETE FROM essays WHERE essay_id IN ({','.join('?' * len(revision_essay_ids))})",
                revision_essay_ids,
            )
            deleted["essays.revisions"] = len(revision_essay_ids)
        remaining_essay_ids = [
            e for e in essay_ids if e not in set(revision_essay_ids)
        ]
        if remaining_essay_ids:
            conn.execute(
                f"DELETE FROM essays WHERE essay_id IN ({','.join('?' * len(remaining_essay_ids))})",
                remaining_essay_ids,
            )
            deleted["essays.originals"] = len(remaining_essay_ids)
        conn.execute("DELETE FROM students WHERE student_id=?", (DEMO_LEARNER,))
        deleted["students"] = 1
    return deleted


def cleanup() -> int:
    repository = _repository()
    deleted = _cleanup(repository)
    manifest = _manifest_path(repository)
    if manifest.exists():
        manifest.unlink()
    print("Cleanup complete (DEMO-001 records only).")
    print(json.dumps(deleted, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic demo Learning Journey management")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--setup", action="store_true", help="Create the demo journey (idempotent)")
    group.add_argument("--status", action="store_true", help="Report demo journey state")
    group.add_argument("--cleanup", action="store_true", help="Remove only DEMO-001 records")
    args = parser.parse_args()
    if args.setup:
        return setup()
    if args.status:
        return status()
    return cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
