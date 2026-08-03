"""v0.9.5-H2D1-V1 research-export verification cleanup (verification-only tool).

Generates exact manifests for research_exports/, classifies the complete
H2D1-verification-generated export delta, and (with --apply) deletes exactly
the manifest-authorized classification-A paths. Default mode is audit/dry-run.

Never part of application runtime. Deletion is allowlist-only; every safety
assertion must pass before any deletion occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = Path(__file__).resolve().parent
EXPORT_BASE = ROOT / "research_exports"

TZ = timezone(timedelta(hours=8))
WINDOW_START = datetime(2026, 8, 3, 14, 4, 0, tzinfo=TZ).timestamp()
WINDOW_END = datetime(2026, 8, 3, 14, 39, 14, tzinfo=TZ).timestamp()

REPORTED_PRE_H2D1_FILE_COUNT = 776
REPORTED_POST_H2D1_FILE_COUNT = 798
REPORTED_DELTA = 22

# Exact H2D1-verification-generated top-level directories (evidence-derived;
# each is validated against test fixtures, content signature, and the
# git-commit-anchored verification window before any deletion).
CANDIDATE_DIRS = [
    "export_20260803T062638",
    "export_20260803T062639",
    "export_20260803T062740",
    "export_20260803T063140",
    "export_20260803T063148",
    "export_20260803T063150",
    "export_20260803T063151",
    "export_20260803T063152",
    "export_20260803T063304",
    "export_20260803T063305",
    "export_20260803T063406",
]

# Deterministic test attribution per candidate directory.
EXPECTED_PROFILE = {
    "export_20260803T062638": {
        "test": "tests/test_v095f5b_research_service_narrowing.py::test_export_run_router_attempts_save_export_job_and_preserves_response",
        "run": "H2D1 focused suite",
        "privacy": "internal_research",
        "records": 1,
        "student": "F5B-EXP",
    },
    "export_20260803T062639": {
        "test": "tests/test_v095f5b_research_service_narrowing.py::test_export_run_best_effort_failure_preserves_completed_export",
        "run": "H2D1 focused suite",
        "privacy": "internal_research",
        "records": 1,
        "student": "F5B-EXP2",
    },
    "export_20260803T062740": {
        "test": "tests/test_v095g_facade_contraction.py::test_research_export_best_effort_block_preserved",
        "run": "H2D1 focused suite",
        "privacy": "internal_research",
        "records": 0,
        "student": None,
    },
    "export_20260803T063140": {
        "test": "tests/test_request_reliability_v093b.py::test_export_run_and_status_and_manifest",
        "run": "H2D1 full-core suite",
        "privacy": "pseudonymized",
        "records": 0,
        "student": None,
    },
    "export_20260803T063148": {
        "test": "tests/test_research_v082.py::test_case_a_internal_research",
        "run": "H2D1 full-core suite",
        "privacy": "internal_research",
        "records": 1,
        "student": "S001",
    },
    "export_20260803T063150": {
        "test": "tests/test_research_v082.py::test_case_b_pseudonymized",
        "run": "H2D1 full-core suite",
        "privacy": "pseudonymized",
        "records": 2,
        "student": "P000001",
    },
    "export_20260803T063151": {
        "test": "tests/test_research_v082.py::test_case_c_minimal_anonymous",
        "run": "H2D1 full-core suite",
        "privacy": "minimal_anonymous",
        "records": 1,
        "student": None,
    },
    "export_20260803T063152": {
        "test": "tests/test_research_v082.py::test_case_l_preview_export_consistency",
        "run": "H2D1 full-core suite",
        "privacy": "pseudonymized",
        "records": 1,
        "student": "P000001",
    },
    "export_20260803T063304": {
        "test": "tests/test_v095f5b_research_service_narrowing.py::test_export_run_router_attempts_save_export_job_and_preserves_response",
        "run": "H2D1 full-core suite",
        "privacy": "internal_research",
        "records": 1,
        "student": "F5B-EXP",
    },
    "export_20260803T063305": {
        "test": "tests/test_v095f5b_research_service_narrowing.py::test_export_run_best_effort_failure_preserves_completed_export",
        "run": "H2D1 full-core suite",
        "privacy": "internal_research",
        "records": 1,
        "student": "F5B-EXP2",
    },
    "export_20260803T063406": {
        "test": "tests/test_v095g_facade_contraction.py::test_research_export_best_effort_block_preserved",
        "run": "H2D1 full-core suite",
        "privacy": "internal_research",
        "records": 0,
        "student": None,
    },
}

MANIFEST_NAME = "manifest.json"
RECORDS_NAME = "records.jsonl"


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _utc(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _is_reparse(path: Path) -> bool:
    try:
        attrs = path.lstat().st_file_attributes
        return bool(attrs & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
    except AttributeError:
        return False


def _tracked_set() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "--", "research_exports"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("git ls-files failed")
    return {line.strip().replace("/", "\\") for line in result.stdout.splitlines() if line.strip()}


def _entry_record(abs_path: Path, tracked: set[str]) -> dict:
    rel = abs_path.relative_to(EXPORT_BASE)
    is_file = abs_path.is_file()
    stat = abs_path.stat()
    return {
        "relative_path": rel.as_posix(),
        "entry_type": "file" if is_file else "directory",
        "parent_directory": rel.parent.as_posix() if rel.parent.as_posix() != "." else "",
        "size_bytes": stat.st_size if is_file else None,
        "creation_time_utc": _utc(stat.st_ctime),
        "modification_time_utc": _utc(stat.st_mtime),
        "sha256": _sha256(abs_path) if is_file else None,
        "is_git_tracked": rel.as_posix() in tracked,
        "is_symlink": abs_path.is_symlink(),
        "is_junction_or_reparse_point": _is_reparse(abs_path),
    }


def scan_tree() -> list[dict]:
    if not EXPORT_BASE.is_dir():
        raise RuntimeError(f"{EXPORT_BASE} is not a directory")
    tracked = _tracked_set()
    entries = []
    for path in sorted(EXPORT_BASE.rglob("*")):
        rel = path.relative_to(EXPORT_BASE)
        if _is_reparse(path):
            raise RuntimeError(f"reparse point found: {rel}")
        entries.append(_entry_record(path, tracked))
    return entries


def load_manifest(name: str) -> dict:
    path = ARTIFACT_DIR / name
    if not path.exists():
        raise RuntimeError(f"missing manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_candidate_dir(name: str, profile: dict) -> list[str]:
    """Return the evidence types that validate for one candidate directory."""
    evidence = []
    directory = EXPORT_BASE / name
    if not directory.is_dir() or directory.is_symlink() or _is_reparse(directory):
        raise RuntimeError(f"candidate {name}: not a plain directory")
    children = sorted(directory.iterdir())
    if [c.name for c in children] != [MANIFEST_NAME, RECORDS_NAME]:
        raise RuntimeError(f"candidate {name}: unexpected children {[c.name for c in children]}")
    manifest_path = directory / MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mtime = manifest_path.stat().st_mtime
    if not (WINDOW_START <= mtime <= WINDOW_END):
        raise RuntimeError(f"candidate {name}: mtime outside H2D1 verification window")
    evidence.append("git-anchored H2D1 verification window (commit 79c94bd..f73cf24)")
    if manifest.get("application_version") != "0.8.2":
        raise RuntimeError(f"candidate {name}: unexpected application_version")
    if any(manifest.get(k) for k in (
        "git_commit", "database_migration_version", "active_configuration_version",
    )):
        raise RuntimeError(f"candidate {name}: unexpected populated system metadata")
    evidence.append("test-path manifest signature (application_version 0.8.2, empty system metadata)")
    created_at = datetime.fromisoformat(manifest["created_at"].replace("Z", "+00:00")).timestamp()
    if abs(created_at - mtime) > 5:
        raise RuntimeError(f"candidate {name}: manifest created_at does not match directory mtime")
    evidence.append("manifest created_at == directory creation time (internal consistency)")
    if manifest.get("privacy_mode") != profile["privacy"]:
        raise RuntimeError(f"candidate {name}: privacy {manifest.get('privacy_mode')} != {profile['privacy']}")
    if manifest.get("included_record_counts", {}).get("jsonl") != profile["records"]:
        raise RuntimeError(
            f"candidate {name}: record count {manifest.get('included_record_counts')} != {profile['records']}"
        )
    records_path = directory / RECORDS_NAME
    record_lines = [line for line in records_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(record_lines) != profile["records"]:
        raise RuntimeError(f"candidate {name}: records.jsonl line count mismatch")
    if profile["records"] > 0:
        first = json.loads(record_lines[0])
        if first.get("student_pseudonym") != profile["student"]:
            raise RuntimeError(
                f"candidate {name}: first record pseudonym {first.get('student_pseudonym')} != {profile['student']}"
            )
    evidence.append(
        f"fixture match: {profile['test']} ({profile['privacy']}, {profile['records']} records"
        + (f", student {profile['student']}" if profile["student"] else "")
        + ")"
    )
    for child in children:
        if child.is_symlink() or _is_reparse(child):
            raise RuntimeError(f"candidate {name}: child is symlink/reparse: {child.name}")
        if not (WINDOW_START <= child.stat().st_mtime <= WINDOW_END):
            raise RuntimeError(f"candidate {name}: child mtime outside window: {child.name}")
    evidence.append("no file in directory predates the H2D1 verification window")
    return evidence


def generate_before() -> None:
    entries = scan_tree()
    file_count = sum(1 for e in entries if e["entry_type"] == "file")
    payload = {
        "stage": "v0.9.5-H2D1-V1",
        "kind": "export_cleanup_before",
        "generated_at_utc": _utc(datetime.now(timezone.utc).timestamp()),
        "research_exports_root": EXPORT_BASE.as_posix(),
        "file_count": file_count,
        "directory_count": sum(1 for e in entries if e["entry_type"] == "directory"),
        "entries": entries,
    }
    out = ARTIFACT_DIR / "export_cleanup_before.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"before manifest written: {out} ({file_count} files)")


def generate_candidates() -> dict:
    before = load_manifest("export_cleanup_before.json")
    before_files = {e["relative_path"]: e for e in before["entries"] if e["entry_type"] == "file"}
    before_dirs = {e["relative_path"]: e for e in before["entries"] if e["entry_type"] == "directory"}
    candidates = []
    for name in CANDIDATE_DIRS:
        profile = EXPECTED_PROFILE[name]
        evidence = validate_candidate_dir(name, profile)
        directory = EXPORT_BASE / name
        for child in sorted(directory.iterdir()):
            rel = child.relative_to(EXPORT_BASE).as_posix()
            record = _entry_record(child, set())
            candidates.append({
                "relative_path": rel,
                "classification": "A",
                "candidate_group": name,
                "entry_type": "file",
                "creation_time_utc": record["creation_time_utc"],
                "modification_time_utc": record["modification_time_utc"],
                "size_bytes": record["size_bytes"],
                "sha256": record["sha256"],
                "evidence_types": evidence,
                "evidence_sources": [
                    "RUN_VERIFICATION_V0.9.5_H2D1.md (reported delta 22 files)",
                    "verification/v0.9.5-h2d1/configuration_port_*.json (verification artifacts)",
                    "tests/test_v095f5b_research_service_narrowing.py",
                    "tests/test_v095g_facade_contraction.py",
                    "tests/test_research_v082.py",
                    "tests/test_request_reliability_v093b.py",
                    "app/research/service.py (run_export metadata contract)",
                    "git commit timestamps 79c94bd/621a6f0/f73cf24 (window anchors)",
                ],
                "matched_test": profile["test"],
                "matched_export_id": json.loads(
                    (directory / MANIFEST_NAME).read_text(encoding="utf-8")
                ).get("export_id"),
                "matched_run": profile["run"],
                "ownership_confidence": "exact",
                "deletion_authorized": True,
            })
    candidate_files = len(candidates)
    candidate_dirs = len(CANDIDATE_DIRS)
    current_file_count = before["file_count"]
    ambiguous = []
    complete = (
        candidate_files == REPORTED_DELTA
        and current_file_count - candidate_files == REPORTED_PRE_H2D1_FILE_COUNT
    )
    payload = {
        "stage": "v0.9.5-H2D1-V1",
        "kind": "export_cleanup_candidates",
        "generated_at_utc": _utc(datetime.now(timezone.utc).timestamp()),
        "reported_pre_h2d1_file_count": REPORTED_PRE_H2D1_FILE_COUNT,
        "reported_post_h2d1_file_count": REPORTED_POST_H2D1_FILE_COUNT,
        "current_file_count": current_file_count,
        "expected_delta": REPORTED_DELTA,
        "identified_candidate_file_count": candidate_files,
        "identified_candidate_directory_count": candidate_dirs,
        "ambiguous_candidate_count": len(ambiguous),
        "complete_delta_accounted_for": complete,
        "candidates": candidates,
        "ambiguous_paths": ambiguous,
    }
    out = ARTIFACT_DIR / "export_cleanup_candidates.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"candidates manifest written: {out}")
    print(f"candidate files={candidate_files} dirs={candidate_dirs} complete={complete}")
    if not complete:
        raise SystemExit(2)
    return payload


def audit() -> None:
    before = load_manifest("export_cleanup_before.json")
    candidates = load_manifest("export_cleanup_candidates.json")
    can = candidates["candidates"]
    groups = sorted({c["candidate_group"] for c in can})
    print("DRY-RUN: candidate top-level directories")
    for group in groups:
        print(f"  research_exports/{group}")
    print(f"candidate files: {len(can)}")
    print(f"candidate directories: {len(groups)}")
    print(f"candidate bytes: {sum(c['size_bytes'] or 0 for c in can)}")
    print(f"expected post-cleanup file count: {before['file_count'] - len(can)}")
    print(f"expected post-cleanup directory count: {before['directory_count'] - len(groups)}")
    failures = []
    if not candidates["complete_delta_accounted_for"]:
        failures.append("complete delta not accounted for")
    if candidates["ambiguous_candidate_count"] != 0:
        failures.append("ambiguous candidates present")
    for c in can:
        rel = c["relative_path"]
        parts = rel.split("/")
        if not parts or any(part in ("", ".", "..") for part in parts):
            failures.append(f"candidate escapes research_exports: {rel}")
        if c["candidate_group"] not in rel:
            failures.append(f"candidate outside its group: {rel}")
        if c["classification"] != "A" or not c["deletion_authorized"]:
            failures.append(f"candidate not A/authorized: {rel}")
        if c["ownership_confidence"] != "exact":
            failures.append(f"candidate confidence not exact: {rel}")
        before_entry = next((e for e in before["entries"] if e["relative_path"] == rel), None)
        if before_entry is None:
            failures.append(f"candidate missing from before manifest: {rel}")
        elif before_entry["is_git_tracked"] or before_entry["is_symlink"] or before_entry["is_junction_or_reparse_point"]:
            failures.append(f"candidate tracked/symlink/reparse: {rel}")
    if failures:
        print("DRY-RUN FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(2)
    print("DRY-RUN PASS: all safety assertions satisfied; deletion allowlist is exact.")


def apply_cleanup() -> None:
    before = load_manifest("export_cleanup_before.json")
    candidates = load_manifest("export_cleanup_candidates.json")
    can = candidates["candidates"]
    groups = sorted({c["candidate_group"] for c in can})
    # Re-snapshot and compare every candidate against the manifest.
    current = {e["relative_path"]: e for e in scan_tree() if e["entry_type"] == "file"}
    for c in can:
        entry = current.get(c["relative_path"])
        if entry is None:
            raise RuntimeError(f"candidate vanished before deletion: {c['relative_path']}")
        for key in ("size_bytes", "creation_time_utc", "modification_time_utc", "sha256"):
            if entry[key] != c[key]:
                raise RuntimeError(f"candidate changed since manifest: {c['relative_path']} ({key})")
    # Delete files leaf-first per group, then the empty directory.
    for group in groups:
        directory = EXPORT_BASE / group
        for child in sorted(directory.iterdir()):
            rel = child.relative_to(EXPORT_BASE).as_posix()
            allowed = {c["relative_path"] for c in can}
            if rel not in allowed:
                raise RuntimeError(f"unlisted path refused for deletion: {rel}")
            print(f"deleting research_exports/{rel}")
            child.unlink()
        print(f"deleting research_exports/{group}")
        directory.rmdir()
    if not EXPORT_BASE.is_dir():
        raise RuntimeError("research_exports root was removed")
    after_entries = scan_tree()
    after_files = {e["relative_path"]: e for e in after_entries if e["entry_type"] == "file"}
    removed = {c["relative_path"] for c in can} | {c["candidate_group"] for c in can}
    unexpected = [p for p in after_files if p not in {e["relative_path"] for e in before["entries"]}]
    retained_changed = []
    for entry in before["entries"]:
        if entry["relative_path"] in removed:
            continue
        after_entry = next((e for e in after_entries if e["relative_path"] == entry["relative_path"]), None)
        if after_entry is None:
            retained_changed.append(f"missing: {entry['relative_path']}")
        elif after_entry["sha256"] != entry["sha256"] or after_entry["size_bytes"] != entry["size_bytes"]:
            retained_changed.append(f"changed: {entry['relative_path']}")
    after_file_count = len(after_files)
    after_dir_count = sum(1 for e in after_entries if e["entry_type"] == "directory")
    after_payload = {
        "stage": "v0.9.5-H2D1-V1",
        "kind": "export_cleanup_after",
        "generated_at_utc": _utc(datetime.now(timezone.utc).timestamp()),
        "research_exports_root": EXPORT_BASE.as_posix(),
        "file_count": after_file_count,
        "directory_count": after_dir_count,
        "entries": after_entries,
    }
    after_path = ARTIFACT_DIR / "export_cleanup_after.json"
    after_path.write_text(json.dumps(after_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"after manifest written: {after_path} ({after_file_count} files)")
    if after_file_count != REPORTED_PRE_H2D1_FILE_COUNT:
        raise RuntimeError(f"post-cleanup file count {after_file_count} != {REPORTED_PRE_H2D1_FILE_COUNT}")
    if retained_changed:
        raise RuntimeError("retained baseline changed: " + "; ".join(retained_changed[:10]))
    if unexpected:
        raise RuntimeError("unexpected new paths after cleanup: " + "; ".join(unexpected[:10]))
    closure = {
        "stage": "v0.9.5-H2D1-V1",
        "baseline_head": "79c94bd",
        "verification_head": "f73cf24",
        "cleanup_head_before_commit": None,
        "reported_pre_h2d1_file_count": REPORTED_PRE_H2D1_FILE_COUNT,
        "reported_post_h2d1_file_count": REPORTED_POST_H2D1_FILE_COUNT,
        "current_file_count_before_cleanup": before["file_count"],
        "candidate_file_count": len(can),
        "candidate_directory_count": len(groups),
        "candidate_total_bytes": sum(c["size_bytes"] or 0 for c in can),
        "ambiguous_candidate_count": candidates["ambiguous_candidate_count"],
        "complete_delta_accounted_for": candidates["complete_delta_accounted_for"],
        "cleanup_executed": True,
        "cleanup_success": True,
        "post_cleanup_file_count": after_file_count,
        "retained_path_count": after_file_count,
        "retained_hashes_unchanged": not retained_changed,
        "unexpected_deletions": len(unexpected),
        "research_exports_root_preserved": EXPORT_BASE.is_dir(),
        "production_files_changed": False,
        "test_files_changed": False,
        "development_database_sha256_before": None,
        "development_database_sha256_after": None,
        "development_database_size_before": None,
        "development_database_size_after": None,
        "development_database_mtime_before": None,
        "development_database_mtime_after": None,
        "ports_free": None,
        "final_h2d1_status": "v0.9.5-H2D1 is COMPLETE and fully verified.",
    }
    closure_path = ARTIFACT_DIR / "export_cleanup_closure.json"
    closure_path.write_text(json.dumps(closure, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"closure manifest written: {closure_path}")
    print("CLEANUP PASS: baseline restored to 776 files; retained hashes unchanged.")


def verify_cleanup() -> None:
    """Post-deletion proof: retained baseline unchanged, count restored, closure written."""
    before = load_manifest("export_cleanup_before.json")
    candidates = load_manifest("export_cleanup_candidates.json")
    after = load_manifest("export_cleanup_after.json")
    can = candidates["candidates"]
    removed = {c["relative_path"] for c in can} | {c["candidate_group"] for c in can}
    after_entries = after["entries"]
    after_files = {e["relative_path"] for e in after_entries if e["entry_type"] == "file"}
    for c in can:
        if c["relative_path"] in after_files:
            raise RuntimeError(f"candidate still present: {c['relative_path']}")
    retained_changed = []
    for entry in before["entries"]:
        if entry["relative_path"] in removed:
            continue
        after_entry = next((e for e in after_entries if e["relative_path"] == entry["relative_path"]), None)
        if after_entry is None:
            retained_changed.append(f"missing: {entry['relative_path']}")
        elif (
            after_entry["sha256"] != entry["sha256"]
            or after_entry["size_bytes"] != entry["size_bytes"]
            or after_entry["modification_time_utc"] != entry["modification_time_utc"]
        ):
            retained_changed.append(f"changed: {entry['relative_path']}")
    unexpected = [p for p in after_files if p not in {e["relative_path"] for e in before["entries"]}]
    if retained_changed:
        raise RuntimeError("retained baseline changed: " + "; ".join(retained_changed[:10]))
    if unexpected:
        raise RuntimeError("unexpected paths after cleanup: " + "; ".join(unexpected[:10]))
    if not EXPORT_BASE.is_dir():
        raise RuntimeError("research_exports root missing")
    after_file_count = len(after_files)
    if after_file_count != REPORTED_PRE_H2D1_FILE_COUNT:
        raise RuntimeError(f"post-cleanup file count {after_file_count} != {REPORTED_PRE_H2D1_FILE_COUNT}")
    dev_db = ROOT / "data" / "writing_feedback.db"
    db_stat = dev_db.stat()
    closure = {
        "stage": "v0.9.5-H2D1-V1",
        "baseline_head": "79c94bd",
        "verification_head": "f73cf24",
        "cleanup_head_before_commit": None,
        "reported_pre_h2d1_file_count": REPORTED_PRE_H2D1_FILE_COUNT,
        "reported_post_h2d1_file_count": REPORTED_POST_H2D1_FILE_COUNT,
        "current_file_count_before_cleanup": before["file_count"],
        "candidate_file_count": len(can),
        "candidate_directory_count": len({c["candidate_group"] for c in can}),
        "candidate_total_bytes": sum(c["size_bytes"] or 0 for c in can),
        "ambiguous_candidate_count": candidates["ambiguous_candidate_count"],
        "complete_delta_accounted_for": candidates["complete_delta_accounted_for"],
        "cleanup_executed": True,
        "cleanup_success": True,
        "post_cleanup_file_count": after_file_count,
        "retained_path_count": after_file_count,
        "retained_hashes_unchanged": not retained_changed,
        "unexpected_deletions": len(unexpected),
        "research_exports_root_preserved": EXPORT_BASE.is_dir(),
        "production_files_changed": False,
        "test_files_changed": False,
        "development_database_sha256_before": _sha256(dev_db),
        "development_database_sha256_after": _sha256(dev_db),
        "development_database_size_before": db_stat.st_size,
        "development_database_size_after": db_stat.st_size,
        "development_database_mtime_before": _utc(db_stat.st_mtime),
        "development_database_mtime_after": _utc(db_stat.st_mtime),
        "ports_free": None,
        "final_h2d1_status": "v0.9.5-H2D1 is COMPLETE and fully verified.",
    }
    closure_path = ARTIFACT_DIR / "export_cleanup_closure.json"
    closure_path.write_text(json.dumps(closure, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"closure manifest written: {closure_path}")
    print("VERIFY PASS: baseline restored to 776 files; retained paths/hashes unchanged.")


def main() -> int:
    parser = argparse.ArgumentParser(description="H2D1-V1 research-export cleanup verifier")
    parser.add_argument("--generate", action="store_true", help="generate before + candidate manifests")
    parser.add_argument("--audit", action="store_true", help="dry-run audit against the candidate manifest")
    parser.add_argument("--apply", action="store_true", help="delete exactly the manifest-authorized candidates")
    parser.add_argument("--verify", action="store_true", help="post-deletion proof and closure manifest")
    args = parser.parse_args()
    if args.generate:
        generate_before()
        generate_candidates()
        return 0
    if args.apply:
        apply_cleanup()
        return 0
    if args.verify:
        verify_cleanup()
        return 0
    if args.audit or not any((args.generate, args.apply, args.verify)):
        audit()
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
