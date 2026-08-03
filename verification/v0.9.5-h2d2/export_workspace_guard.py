"""v0.9.5-H2D2 research-export workspace guard (verification-only tool).

Ensures verification layers do not leave export output behind:
- --check: assert the current research_exports/ tree exactly matches the
  approved baseline manifest (776 files / 388 dirs, paths and hashes).
- --delta: identify newly added top-level export directories since the
  baseline, with per-path ownership evidence (absent from baseline +
  test-export content signature), and write test_export_deltas.json.
- --restore: delete exactly the allowlisted delta paths (leaf-first) and
  re-verify the baseline; write research_exports_final.json.

Never part of application runtime. No wildcard deletion; no root deletion;
no modification of baseline entries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = Path(__file__).resolve().parent
EXPORT_BASE = ROOT / "research_exports"
BASELINE = ARTIFACT_DIR / "research_exports_baseline.json"
DELTA = ARTIFACT_DIR / "test_export_deltas.json"
FINAL = ARTIFACT_DIR / "research_exports_final.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def scan() -> dict[str, dict]:
    entries = {}
    for path in sorted(EXPORT_BASE.rglob("*")):
        rel = path.relative_to(EXPORT_BASE).as_posix()
        is_file = path.is_file()
        stat = path.stat()
        entries[rel] = {
            "relative_path": rel,
            "entry_type": "file" if is_file else "directory",
            "size_bytes": stat.st_size if is_file else None,
            "creation_time_utc": utc(stat.st_ctime),
            "modification_time_utc": utc(stat.st_mtime),
            "sha256": sha256(path) if is_file else None,
            "is_symlink": path.is_symlink(),
        }
    return entries


def baseline_payload() -> dict:
    if not BASELINE.exists():
        raise RuntimeError(f"baseline manifest missing: {BASELINE}")
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def check() -> None:
    base = baseline_payload()
    base_entries = {e["relative_path"]: e for e in base["entries"]}
    current = scan()
    failures = []
    for rel, entry in base_entries.items():
        cur = current.get(rel)
        if cur is None:
            failures.append(f"baseline path missing: {rel}")
        elif entry["entry_type"] == "file" and (
            cur["sha256"] != entry["sha256"] or cur["size_bytes"] != entry["size_bytes"]
        ):
            failures.append(f"baseline file changed: {rel}")
    for rel in current:
        if rel not in base_entries:
            failures.append(f"unexpected addition: {rel}")
    file_count = sum(1 for e in current.values() if e["entry_type"] == "file")
    dir_count = sum(1 for e in current.values() if e["entry_type"] == "directory")
    if file_count != base["file_count"] or dir_count != base["directory_count"]:
        failures.append(f"count drift: {file_count}/{dir_count} vs {base['file_count']}/{base['directory_count']}")
    if failures:
        print("BASELINE CHECK FAILED:")
        for f in failures[:20]:
            print("  -", f)
        raise SystemExit(2)
    print(f"BASELINE OK: {file_count} files / {dir_count} dirs; all baseline paths and hashes unchanged.")


def capture_delta() -> None:
    base = baseline_payload()
    base_entries = {e["relative_path"] for e in base["entries"]}
    current = scan()
    additions = [rel for rel in sorted(current) if rel not in base_entries]
    new_dirs = sorted({rel.split("/", 1)[0] for rel in additions if "/" in rel})
    delta_entries = []
    for directory in new_dirs:
        children = sorted(rel for rel in additions if rel.startswith(directory + "/"))
        if children != [f"{directory}/manifest.json", f"{directory}/records.jsonl"]:
            raise RuntimeError(f"unexpected children in new directory {directory}: {children}")
        manifest_path = EXPORT_BASE / directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        mtime = manifest_path.stat().st_mtime
        if manifest.get("application_version") != "0.8.2":
            raise RuntimeError(f"{directory}: unexpected application_version")
        if any(manifest.get(k) for k in ("git_commit", "database_migration_version", "active_configuration_version")):
            raise RuntimeError(f"{directory}: unexpected populated system metadata")
        created_at = datetime.fromisoformat(manifest["created_at"].replace("Z", "+00:00")).timestamp()
        if abs(created_at - mtime) > 5:
            raise RuntimeError(f"{directory}: created_at mismatch")
        for rel in children:
            entry = current[rel]
            delta_entries.append({
                "relative_path": rel,
                "classification": "A",
                "candidate_group": directory,
                "entry_type": entry["entry_type"],
                "creation_time_utc": entry["creation_time_utc"],
                "modification_time_utc": entry["modification_time_utc"],
                "size_bytes": entry["size_bytes"],
                "sha256": entry["sha256"],
                "evidence_types": [
                    "absent from approved pre-layer baseline manifest",
                    "test-export content signature (application_version 0.8.2, empty system metadata)",
                    "manifest created_at == directory creation time",
                ],
                "ownership_confidence": "exact",
                "deletion_authorized": True,
            })
    payload = {
        "stage": "v0.9.5-H2D2",
        "kind": "test_export_deltas",
        "detected_at_utc": utc(datetime.now(timezone.utc).timestamp()),
        "baseline_file_count": base["file_count"],
        "baseline_directory_count": base["directory_count"],
        "added_directory_count": len(new_dirs),
        "added_file_count": len(delta_entries),
        "ambiguous_count": 0,
        "entries": delta_entries,
    }
    DELTA.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"delta manifest written: {DELTA} ({len(delta_entries)} files in {len(new_dirs)} dirs)")


def restore() -> None:
    delta = json.loads(DELTA.read_text(encoding="utf-8"))
    if delta.get("ambiguous_count", 0) != 0:
        raise RuntimeError("ambiguous delta entries present; refusing deletion")
    current = scan()
    for entry in delta["entries"]:
        cur = current.get(entry["relative_path"])
        if cur is None:
            continue  # already absent
        if cur["sha256"] != entry["sha256"] or cur["size_bytes"] != entry["size_bytes"]:
            raise RuntimeError(f"delta path changed since capture: {entry['relative_path']}")
        if cur["is_symlink"]:
            raise RuntimeError(f"delta path is a symlink: {entry['relative_path']}")
    groups = sorted({e["candidate_group"] for e in delta["entries"]})
    for group in groups:
        directory = EXPORT_BASE / group
        for child in sorted(directory.iterdir()):
            rel = child.relative_to(EXPORT_BASE).as_posix()
            allowed = {e["relative_path"] for e in delta["entries"]}
            if rel not in allowed:
                raise RuntimeError(f"unlisted path refused: {rel}")
            print(f"deleting research_exports/{rel}")
            child.unlink()
        print(f"deleting research_exports/{group}")
        directory.rmdir()
    if not EXPORT_BASE.is_dir():
        raise RuntimeError("research_exports root removed")
    final_entries = scan()
    final = {
        "stage": "v0.9.5-H2D2",
        "kind": "research_exports_final",
        "file_count": sum(1 for e in final_entries.values() if e["entry_type"] == "file"),
        "directory_count": sum(1 for e in final_entries.values() if e["entry_type"] == "directory"),
        "entries": [final_entries[rel] for rel in sorted(final_entries)],
    }
    FINAL.write_text(json.dumps(final, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"final manifest written: {FINAL}")
    check()


def main() -> int:
    parser = argparse.ArgumentParser(description="H2D2 research-export workspace guard")
    parser.add_argument("--check", action="store_true", help="verify baseline unchanged")
    parser.add_argument("--delta", action="store_true", help="capture test-export delta manifest")
    parser.add_argument("--restore", action="store_true", help="delete exact delta and restore baseline")
    args = parser.parse_args()
    if args.delta:
        capture_delta()
        return 0
    if args.restore:
        restore()
        return 0
    check()
    return 0


if __name__ == "__main__":
    sys.exit(main())
