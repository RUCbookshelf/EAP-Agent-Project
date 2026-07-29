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
    source = (ROOT / "app" / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    assert "api_client.submit" in source
    assert "FeedbackPipeline" not in source and "sqlite3" not in source
