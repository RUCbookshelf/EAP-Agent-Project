"""v0.9.5-D frontend API-surface capture.

Builds the FastAPI application with an isolated temporary database and
extracts:
- every declared endpoint (method, path);
- every public WritingFeedbackApiClient method with its signature;
- the client method -> endpoint (method, path template) mapping;
- every `api_client.<method>(...)` call made by the twelve frontend feature
  modules;
- facade private-helper imports in tests.

Usage:
    python verification/v0.9.5-d/capture_api_surface.py --out <json>
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from app.api.main import create_app  # noqa: E402
from app.config import Settings  # noqa: E402
from app.ui.api_client import WritingFeedbackApiClient  # noqa: E402


FEATURE_FILES = {
    "student_home": ROOT / "app/ui/features/student/home.py",
    "student_writing": ROOT / "app/ui/features/student/writing.py",
    "student_feedback": ROOT / "app/ui/features/student/feedback.py",
    "student_practice": ROOT / "app/ui/features/student/practice.py",
    "student_revision": ROOT / "app/ui/features/student/revision.py",
    "student_journey": ROOT / "app/ui/features/student/journey.py",
    "research_overview": ROOT / "app/ui/features/research/overview.py",
    "research_evidence": ROOT / "app/ui/features/research/evidence.py",
    "research_calf": ROOT / "app/ui/features/research/calf.py",
    "research_learning_process": ROOT / "app/ui/features/research/learning_process.py",
    "research_data": ROOT / "app/ui/features/research/data.py",
    "research_system_audit": ROOT / "app/ui/features/research/system_audit.py",
}

# State-changing client methods (features only call a subset of these).
WRITE_CAPABLE_METHODS = frozenset({
    "submit",
    "create_exercise",
    "submit_exercise_attempt",
    "research_export_run",
    "create_human_review",
    "create_dataset_split",
    "rebuild_learner_model",
    "create_practice_target",
    "create_revision",
    "reanalyze",
    "create_configuration",
    "validate_configuration",
    "activate_configuration",
    "rollback_configuration",
    "preview_reanalysis",
    "run_reanalysis",
})

# All features receive their API client under this parameter name.
CLIENT_PARAM_NAME = "api_client"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def endpoint_surface(app) -> list[dict]:
    rows = []
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is None or methods is None:
            continue
        for method in sorted(methods):
            if method in {"HEAD", "OPTIONS"}:
                continue
            rows.append({"method": method, "path": path})
    rows.sort(key=lambda r: (r["path"], r["method"]))
    return rows


def client_methods(client) -> list[dict]:
    rows = []
    for name in sorted(dir(client)):
        if name.startswith("_"):
            continue
        member = getattr(client, name)
        if not callable(member):
            continue
        try:
            signature = str(inspect.signature(member))
        except (TypeError, ValueError):
            signature = ""
        rows.append({"name": name, "signature": signature})
    return rows


def _static_path(parts) -> str:
    text = "".join(p.value if isinstance(p, ast.Constant) else "{}" for p in parts)
    return text


def client_endpoint_map(client) -> dict[str, list[dict]]:
    """Map each client method to the HTTP method/path template(s) it requests."""
    source_path = ROOT / "app/ui/api_client.py"
    tree = ast.parse(_read(source_path))
    mapping: dict[str, list[dict]] = {}
    client_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "WritingFeedbackApiClient"
    )
    for func in client_class.body:
        if not isinstance(func, ast.FunctionDef) or func.name.startswith("_"):
            continue
        targets = []
        for node in ast.walk(func):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_request"
                and node.args
            ):
                http_method = node.args[0]
                path_arg = node.args[1]
                if isinstance(http_method, ast.Constant) and isinstance(path_arg, ast.Constant):
                    targets.append({"method": http_method.value, "path": path_arg.value})
                elif isinstance(http_method, ast.Constant) and isinstance(path_arg, ast.JoinedStr):
                    targets.append({
                        "method": http_method.value,
                        "path": _static_path(path_arg.values),
                    })
        if targets:
            mapping[func.name] = targets
    return mapping


def feature_calls() -> dict[str, dict]:
    result = {}
    for feature, path in FEATURE_FILES.items():
        tree = ast.parse(_read(path))
        calls: set[str] = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == CLIENT_PARAM_NAME
            ):
                calls.add(node.func.attr)
        result[feature] = {
            "module": str(path),
            "calls": sorted(calls),
            "write_calls": sorted(calls & WRITE_CAPABLE_METHODS),
        }
    return result


def facade_private_imports_in_tests() -> list[dict]:
    rows = []
    pattern = ("app.ui.pages.student_pages", "app.ui.pages.research_pages")
    for path in (ROOT / "tests").rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        tree = ast.parse(_read(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in pattern:
                for alias in node.names:
                    if alias.name.startswith("_"):
                        rows.append({
                            "test": str(path),
                            "module": node.module,
                            "name": alias.name,
                            "line": node.lineno,
                        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture frontend API surface.")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp_dir:
        settings = Settings(
            database_path=str(Path(tmp_dir) / "surface.db"),
            llm_provider="local",
            deepseek_api_key=None,
            deepseek_base_url="https://example.invalid",
            deepseek_model="deepseek-test",
        )
        app = create_app(settings)
        endpoints = endpoint_surface(app)

    client = WritingFeedbackApiClient(base_url="http://127.0.0.1:8000")
    client_rows = client_methods(client)
    payload = {
        "endpoints": endpoints,
        "endpoint_count": len(endpoints),
        "client_methods": client_rows,
        "client_method_count": len(client_rows),
        "client_endpoint_map": client_endpoint_map(client),
        "feature_calls": feature_calls(),
        "write_capable_methods": sorted(WRITE_CAPABLE_METHODS),
        "facade_private_imports_in_tests": facade_private_imports_in_tests(),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "endpoint_count": payload["endpoint_count"],
        "client_method_count": payload["client_method_count"],
        "feature_calls": {k: v["calls"] for k, v in payload["feature_calls"].items()},
        "client_endpoint_map": payload["client_endpoint_map"],
        "facade_private_imports_in_tests_count": len(payload["facade_private_imports_in_tests"]),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
