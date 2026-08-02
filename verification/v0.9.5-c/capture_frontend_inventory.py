"""v0.9.5-C frontend contract inventory capture.

Statically extracts the renderer surface, API-client calls, session-state
keys, widget keys, locale keys, and module imports from the given UI page or
feature modules. Run before and after the feature extraction, then compare
the two JSON outputs to prove contract parity.

Usage:
    python verification/v0.9.5-c/capture_frontend_inventory.py \
        --out <json> --label <name> --files <path> [<path> ...]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DEF_RE = re.compile(r"^def (\w+)\(([^)]*)\)")
API_CALL_RE = re.compile(r"api_client\.(\w+)\(")
SESSION_KEY_RE = re.compile(r'st\.session_state\.(?:get\()?\[?"([^"\]]+)"')
WIDGET_KEY_RE = re.compile(r"\bkey=\"([^\"]+)\"")
LOCALE_KEY_RE = re.compile(r"\bt\(\"([^\"]+)\"")
IMPORT_RE = re.compile(r"^(?:from ([\w.]+) import|import ([\w.]+))")
WRITE_API_RE = re.compile(r"api_client\.(submit|create_exercise|submit_exercise_attempt|research_export_run|create_human_review|create_dataset_split|rebuild_learner_model|create_practice_target|reanalyze)\(")


def capture(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    renders: list[str] = []
    defs: list[str] = []
    api_calls: list[str] = []
    session_keys: list[str] = []
    widget_keys: list[str] = []
    locale_keys: list[str] = []
    imports: list[str] = []
    write_calls: list[str] = []

    for line in source.splitlines():
        m = DEF_RE.match(line)
        if m:
            defs.append(m.group(1))
            if m.group(1).startswith("render_"):
                renders.append(m.group(1))
        for call in API_CALL_RE.findall(line):
            api_calls.append(call)
        for call in WRITE_API_RE.findall(line):
            write_calls.append(call)
        for key in SESSION_KEY_RE.findall(line):
            session_keys.append(key)
        for key in WIDGET_KEY_RE.findall(line):
            widget_keys.append(key)
        for key in LOCALE_KEY_RE.findall(line):
            locale_keys.append(key)
        m = IMPORT_RE.match(line)
        if m:
            imports.append(m.group(1) or m.group(2))

    return {
        "file": str(path),
        "render_functions": sorted(set(renders)),
        "all_definitions": sorted(set(defs)),
        "api_client_calls": sorted(set(api_calls)),
        "write_capable_api_calls": sorted(set(write_calls)),
        "session_state_keys": sorted(set(session_keys)),
        "widget_keys": sorted(set(widget_keys)),
        "locale_keys": sorted(set(locale_keys)),
        "module_imports": sorted(set(imports)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture frontend contract inventory.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--label", default="inventory")
    parser.add_argument("--files", nargs="+", required=True)
    args = parser.parse_args()

    captures = [capture(Path(p)) for p in args.files]
    merged: dict[str, set[str]] = {}
    for item in captures:
        for key, values in item.items():
            if key == "file":
                continue
            merged.setdefault(key, set()).update(values)
    payload = {
        "label": args.label,
        "files": [str(Path(p)) for p in args.files],
        "per_file": captures,
        "aggregate": {key: sorted(values) for key, values in merged.items()},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["aggregate"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
