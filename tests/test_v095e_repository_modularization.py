from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

from app.database import Database
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
POSTCHANGE = ROOT / "verification" / "v0.9.5-g" / "postchange_facade_inventory.json"
PARITY_SCRIPT = ROOT / "verification" / "v0.9.5-e" / "compare_repository_parity.py"


def _signature(node: ast.FunctionDef) -> str:
    args = ast.unparse(node.args)
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"({args}){returns}"


RETAINED_G = {"connect", "initialize"}


def test_database_facade_public_method_set_and_signatures_match_g_era_contract():
    """G-era facade-contraction contract.

    The historical E inventory (86 methods in prechange_repository_inventory.json)
    is preserved unchanged as evidence. After v0.9.5-G, the Database public
    surface is the evidence-supported infrastructure set: connect, initialize.
    """
    expected = json.loads(PRECHANGE.read_text(encoding="utf-8"))
    assert expected["public_method_count"] == 86  # historical E evidence untouched
    tree = ast.parse((ROOT / "app" / "database" / "repository.py").read_text(encoding="utf-8"))
    facade = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Database")
    actual = {
        node.name: _signature(node)
        for node in facade.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }
    assert set(actual) == RETAINED_G
    retained_signatures = {row["name"]: row["signature"] for row in expected["methods"]}
    assert actual == {name: retained_signatures[name] for name in RETAINED_G}
    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "__getattr__"
        for node in ast.walk(facade)
    )


def test_removed_facade_methods_still_exist_on_aggregate_repositories():
    """Every removed facade method remains intact on its aggregate Repository."""
    ledger = json.loads(
        (ROOT / "verification" / "v0.9.5-g" / "removal_ledger.json").read_text(encoding="utf-8"))
    assert len(ledger["removed"]) == 84
    for entry in ledger["removed"]:
        repo_source = (
            ROOT / "app" / "infrastructure" / "sqlite" / "repositories"
            / f"{entry['aggregate_owner']}.py"
        ).read_text(encoding="utf-8")
        assert f"def {entry['method']}(" in repo_source, (
            f"{entry['method']} missing on {entry['aggregate_owner']} repository")


def test_database_facade_explicitly_composes_all_approved_repository_owners(tmp_path):
    database = Database(tmp_path / "not-opened.db")
    assert Database is DirectDatabase
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
    assert summary["method_count_before"] == 86  # historical E evidence
    assert summary["method_count_after"] == 2  # G-era retained surface
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
