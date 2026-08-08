"""Shared-contract drift checks (D-27).

1. No sync-conflict duplicate files (-冲突- / -Copy / -副本 and variants)
   may appear under app/; verification must fail if they do.
2. The canonical module-set manifest (verification/shared-core-h1/
   module_set_manifest.json) is frozen; the current app/ module set must
   match it exactly.  Any addition or removal requires a manifest update
   through the shared-contract change process.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
MANIFEST = ROOT / "verification" / "shared-core-h1" / "module_set_manifest.json"

# D-27 sync-conflict markers plus common Windows-sync variants.
FORBIDDEN_MARKERS = (
    "-冲突-", "-Copy", "-copy", "-副本", "_Copy", "_copy", "_副本", " 副本", " 冲突",
)


def _module_paths() -> list[str]:
    paths = []
    for path in sorted(APP.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        paths.append(path.relative_to(APP).as_posix())
    return paths


def _conflict_files() -> list[str]:
    found = []
    for path in sorted(APP.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        if path.is_file() and any(marker in path.name for marker in FORBIDDEN_MARKERS):
            found.append(path.relative_to(APP).as_posix())
    return found


class TestSyncConflictDrift:
    def test_no_conflict_duplicate_files_under_app(self):
        found = _conflict_files()
        assert found == [], f"sync-conflict/duplicate files under app/: {found}"

    def test_no_conflict_markers_in_python_module_names(self):
        bad = [
            p.relative_to(APP).as_posix()
            for p in APP.rglob("*.py")
            if "__pycache__" not in p.parts
            and any(marker in p.name for marker in FORBIDDEN_MARKERS)
        ]
        assert bad == [], f"python modules matching conflict markers: {bad}"


class TestModuleSetManifest:
    def test_manifest_exists_and_parses(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        assert data["format"] == 1
        assert isinstance(data["modules"], list)

    def test_current_module_set_matches_manifest(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        current = _module_paths()
        manifest_set = set(data["modules"])
        current_set = set(current)
        missing = sorted(manifest_set - current_set)   # manifest entries no longer present
        added = sorted(current_set - manifest_set)     # modules not yet recorded in manifest
        assert missing == [], f"manifest entries missing from app/: {missing}"
        assert added == [], (
            f"module drift: unrecorded modules under app/: {added}; "
            "update verification/shared-core-h1/module_set_manifest.json through "
            "the shared-contract change process"
        )
        assert len(current_set) == len(current), "duplicate module paths in manifest"