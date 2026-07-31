from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def imports_under(path: Path) -> set[str]:
    imports: set[str] = set()
    for file in path.rglob("*.py"):
        tree = ast.parse(file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
    return imports


def test_core_services_are_framework_and_sqlite_independent():
    imports = imports_under(ROOT / "app" / "services")
    assert not any(name.startswith(("streamlit", "fastapi", "sqlite3", "app.database")) for name in imports)


def test_api_routes_do_not_execute_sql():
    source = (ROOT / "app" / "api" / "main.py").read_text(encoding="utf-8").casefold()
    assert "sqlite3" not in source
    assert "select " not in source and "insert " not in source and "update " not in source


def test_streamlit_is_api_client_only():
    imports = imports_under(ROOT / "app" / "ui")
    forbidden = ("app.database", "app.repositories", "app.llm", "app.analyzer", "app.diagnosis", "app.feedback")
    assert not any(name.startswith(forbidden) for name in imports)
    # v0.9.1: submission logic lives in page modules; search all UI source
    found_submit = False
    for f in (ROOT / "app" / "ui").rglob("*.py"):
        src = f.read_text(encoding="utf-8")
        if "api_client.submit" in src:
            found_submit = True
        assert "FeedbackPipeline" not in src
        assert "sqlite3" not in src
    assert found_submit, "api_client.submit must appear in at least one UI module"
