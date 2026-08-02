from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

from app.database import Database, SQLiteRepository
from app.database.repository import Database as DirectDatabase
from app.infrastructure.sqlite import SQLiteConnectionManager
from app.infrastructure.sqlite.repositories import (
    SQLiteAnalysisRepository,
    SQLiteCalfRepository,
    SQLiteConfigurationRepository,
    SQLiteLearnerRepository,
    SQLitePracticeRepository,
    SQLiteResearchRepository,
    SQLiteRevisionRepository,
    SQLiteSubmissionRepository,
    SQLiteSystemRepository,
)


ROOT = Path(__file__).resolve().parents[1]
PRECHANGE = ROOT / "verification" / "v0.9.5-e" / "prechange_repository_inventory.json"
POSTCHANGE = ROOT / "verification" / "v0.9.5-e" / "postchange_repository_inventory.json"
PARITY_SCRIPT = ROOT / "verification" / "v0.9.5-e" / "compare_repository_parity.py"


def _signature(node: ast.FunctionDef) -> str:
    args = ast.unparse(node.args)
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"({args}){returns}"


def test_database_facade_public_method_set_and_signatures_match_prechange_inventory():
    expected = json.loads(PRECHANGE.read_text(encoding="utf-8"))
    tree = ast.parse((ROOT / "app" / "database" / "repository.py").read_text(encoding="utf-8"))
    facade = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Database")
    actual = {
        node.name: _signature(node)
        for node in facade.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }
    assert len(actual) == expected["public_method_count"] == 86
    assert actual == {row["name"]: row["signature"] for row in expected["methods"]}
    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "__getattr__"
        for node in ast.walk(facade)
    )


def test_database_facade_explicitly_composes_all_approved_repository_owners(tmp_path):
    database = Database(tmp_path / "not-opened.db")
    assert Database is DirectDatabase is SQLiteRepository
    assert isinstance(database._connection_manager, SQLiteConnectionManager)
    assert isinstance(database._system_repository, SQLiteSystemRepository)
    assert isinstance(database._configuration_repository, SQLiteConfigurationRepository)
    assert isinstance(database._analysis_repository, SQLiteAnalysisRepository)
    assert isinstance(database._calf_repository, SQLiteCalfRepository)
    assert isinstance(database._revision_repository, SQLiteRevisionRepository)
    assert isinstance(database._learner_repository, SQLiteLearnerRepository)
    assert isinstance(database._practice_repository, SQLitePracticeRepository)
    assert isinstance(database._research_repository, SQLiteResearchRepository)
    assert isinstance(database._submission_repository, SQLiteSubmissionRepository)
    assert not (tmp_path / "not-opened.db").exists()


def test_static_owner_sql_dependency_and_ddl_parity_contract():
    completed = subprocess.run(
        [sys.executable, str(PARITY_SCRIPT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    evidence = json.loads(POSTCHANGE.read_text(encoding="utf-8"))
    summary = evidence["summary"]
    assert evidence["failures"] == []
    assert summary["method_count_before"] == summary["method_count_after"] == 86
    assert summary["signature_drift_count"] == 0
    assert summary["implementation_signature_drift_count"] == 0
    assert summary["delegation_drift_count"] == 0
    assert summary["sql_fingerprint_drift_count"] == 0
    assert summary["schema_constant_parity"] is True
    assert summary["migrations_source_parity"] is True
    assert summary["table_owner_count"] == 33
    assert summary["table_owners_unique"] is True
    assert summary["dynamic_delegation_present"] is False
    assert summary["public_sql_in_facade"] == {}
    assert summary["prohibited_repository_imports"] == []
    assert summary["service_api_domain_diff"] == []
