from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PRE = Path(__file__).with_name("prechange_repository_inventory.json")
OUTPUT = Path(__file__).with_name("postchange_repository_inventory.json")
BASELINE = "769e6d8"

OWNER_MODULE = {
    "SystemRepository": ("system.py", "SQLiteSystemRepository", "_system_repository"),
    "ConfigurationRepository": ("configuration.py", "SQLiteConfigurationRepository", "_configuration_repository"),
    "AnalysisRepository": ("analysis.py", "SQLiteAnalysisRepository", "_analysis_repository"),
    "CalfRepository": ("calf.py", "SQLiteCalfRepository", "_calf_repository"),
    "RevisionRepository": ("revision.py", "SQLiteRevisionRepository", "_revision_repository"),
    "LearnerRepository": ("learner.py", "SQLiteLearnerRepository", "_learner_repository"),
    "PracticeRepository": ("practice.py", "SQLitePracticeRepository", "_practice_repository"),
    "ResearchRepository": ("research.py", "SQLiteResearchRepository", "_research_repository"),
    "SubmissionRepository": ("submission.py", "SQLiteSubmissionRepository", "_submission_repository"),
}

TABLE_OWNERS = {
    "SystemRepository": ["schema_migrations", "system_versions"],
    "SubmissionRepository": ["students", "essays", "diagnoses", "feedback_records", "exercises", "learner_history", "llm_call_records"],
    "AnalysisRepository": ["metrics", "analysis_runs", "metric_results", "analysis_artifacts"],
    "CalfRepository": ["analysis_units", "error_annotations", "diagnostic_calibrations"],
    "RevisionRepository": ["revision_groups", "revision_snapshots"],
    "LearnerRepository": ["learner_profile_snapshots", "history_evidence_registry"],
    "PracticeRepository": ["practice_targets", "exercise_instances", "exercise_attempts", "practice_evaluations", "feedback_engagement_traces", "within_task_response_candidates", "transfer_evidence_candidates", "practice_state_snapshots"],
    "ResearchRepository": ["human_reviews", "pii_candidates", "export_jobs"],
    "ConfigurationRepository": ["configuration_versions", "configuration_audit"],
}

SQL_START = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|PRAGMA|CREATE|ALTER|DROP|BEGIN)\b", re.I)


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def method_map(class_node: ast.ClassDef) -> dict[str, ast.FunctionDef]:
    return {node.name: node for node in class_node.body if isinstance(node, ast.FunctionDef)}


def class_named(tree: ast.Module, name: str) -> ast.ClassDef:
    return next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)


def signature(node: ast.FunctionDef) -> str:
    args = ast.unparse(node.args)
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"({args}){returns}"


def sql_hashes(node: ast.FunctionDef) -> list[str]:
    result = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str) and SQL_START.search(child.value):
            normalized = re.sub(r"\s+", " ", child.value.strip().rstrip(";")).strip()
            result.append(hashlib.sha256(normalized.encode("utf-8")).hexdigest())
    return result


def delegated_owner(node: ast.FunctionDef) -> str | None:
    calls = [child for child in ast.walk(node) if isinstance(child, ast.Call)]
    attrs = []
    for call in calls:
        func = call.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Attribute):
            if isinstance(func.value.value, ast.Name) and func.value.value.id == "self":
                attrs.append(func.value.attr)
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if func.value.id == "SQLiteRevisionRepository":
                attrs.append("_revision_repository")
    return attrs[0] if len(attrs) == 1 else None


def git_text(path: str) -> str:
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT, text=True, encoding="utf-8")


def main() -> None:
    pre = json.loads(PRE.read_text(encoding="utf-8"))
    facade_path = ROOT / "app" / "database" / "repository.py"
    facade_tree = parse(facade_path)
    facade = class_named(facade_tree, "Database")
    facade_methods = method_map(facade)

    implementations: dict[str, tuple[Path, ast.FunctionDef]] = {}
    for owner, (filename, class_name, _) in OWNER_MODULE.items():
        path = ROOT / "app" / "infrastructure" / "sqlite" / "repositories" / filename
        methods = method_map(class_named(parse(path), class_name))
        for name, node in methods.items():
            implementations[f"{owner}:{name}"] = (path, node)
    manager_path = ROOT / "app" / "infrastructure" / "sqlite" / "connection.py"
    manager_methods = method_map(class_named(parse(manager_path), "SQLiteConnectionManager"))

    rows = []
    failures = []
    for baseline in pre["methods"]:
        name = baseline["name"]
        owner = baseline["owner"]
        facade_node = facade_methods.get(name)
        implementation_path, implementation_node = implementations.get(
            f"{owner}:{name}", (Path("<missing>"), None)
        )
        sql_node = manager_methods[name] if name in {"connect", "transaction"} else implementation_node
        signature_ok = facade_node is not None and signature(facade_node) == baseline["signature"]
        implementation_signature_ok = (
            implementation_node is not None and signature(implementation_node) == baseline["signature"]
        )
        expected_attr = OWNER_MODULE[owner][2]
        delegation_ok = facade_node is not None and delegated_owner(facade_node) == expected_attr
        before_sql = [item["sha256"] for item in baseline["sql"]]
        after_sql = sql_hashes(sql_node) if sql_node else []
        sql_ok = before_sql == after_sql
        row = {
            "name": name,
            "owner": owner,
            "facade_signature": signature(facade_node) if facade_node else None,
            "signature_parity": signature_ok,
            "implementation_file": implementation_path.relative_to(ROOT).as_posix() if implementation_path.is_absolute() else str(implementation_path),
            "implementation_signature_parity": implementation_signature_ok,
            "explicit_delegation_parity": delegation_ok,
            "sql_fingerprints_before": before_sql,
            "sql_fingerprints_after": after_sql,
            "sql_fingerprint_parity": sql_ok,
        }
        rows.append(row)
        if not all((signature_ok, implementation_signature_ok, delegation_ok, sql_ok)):
            failures.append({key: row[key] for key in ("name", "signature_parity", "implementation_signature_parity", "explicit_delegation_parity", "sql_fingerprint_parity")})

    private_sql = {}
    baseline_tree = ast.parse(git_text("app/database/repository.py"))
    baseline_private = method_map(class_named(baseline_tree, "Database"))
    for owner, private_names in {
        "ConfigurationRepository": ["_configuration_from_row", "_insert_configuration_audit"],
        "PracticeRepository": ["_next_practice_id"],
        "ResearchRepository": ["_next_research_id"],
    }.items():
        for name in private_names:
            _, current = implementations[f"{owner}:{name}"]
            parity = sql_hashes(baseline_private[name]) == sql_hashes(current)
            private_sql[name] = parity
            if not parity:
                failures.append({"private_sql": name})

    schema_before = next(
        node.value.value for node in baseline_tree.body
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "SCHEMA" for target in node.targets)
    )
    schema_after = next(
        node.value.value for node in facade_tree.body
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "SCHEMA" for target in node.targets)
    )
    migrations_before = git_text("app/database/migrations.py").replace("\r\n", "\n")
    migrations_after = (ROOT / "app" / "database" / "migrations.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    repository_files = sorted((ROOT / "app" / "infrastructure" / "sqlite" / "repositories").glob("*.py"))
    prohibited_imports = []
    for path in repository_files:
        text = path.read_text(encoding="utf-8")
        for prohibited in ("app.database.repository", "fastapi", "streamlit", "app.api", "app.ui", "app.services"):
            if prohibited in text:
                prohibited_imports.append({"file": path.relative_to(ROOT).as_posix(), "import": prohibited})
    dynamic_delegation = any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "__getattr__"
        for node in ast.walk(facade)
    )
    public_sql_in_facade = {
        name: sql_hashes(node) for name, node in facade_methods.items()
        if not name.startswith("_") and sql_hashes(node)
    }
    all_tables = [table for tables in TABLE_OWNERS.values() for table in tables]
    service_diff = subprocess.check_output(
        ["git", "diff", "--name-only", BASELINE, "--", "app/services", "app/journey", "app/practice", "app/research", "app/api"],
        cwd=ROOT, text=True,
    ).splitlines()
    allowed_diff = {
        item for item in os.environ.get("SERVICE_API_DIFF_ALLOWLIST", "").split(",") if item
    }
    service_diff = [path for path in service_diff if path not in allowed_diff]
    summary = {
        "method_count_before": pre["public_method_count"],
        "method_count_after": len([name for name in facade_methods if not name.startswith("_")]),
        "missing_methods": sorted(set(row["name"] for row in pre["methods"]) - set(facade_methods)),
        "added_methods": sorted(set(name for name in facade_methods if not name.startswith("_")) - set(row["name"] for row in pre["methods"])),
        "signature_drift_count": sum(not row["signature_parity"] for row in rows),
        "implementation_signature_drift_count": sum(not row["implementation_signature_parity"] for row in rows),
        "delegation_drift_count": sum(not row["explicit_delegation_parity"] for row in rows),
        "sql_fingerprint_drift_count": sum(not row["sql_fingerprint_parity"] for row in rows),
        "private_sql_parity": private_sql,
        "schema_constant_parity": schema_before == schema_after,
        "migrations_source_parity": migrations_before == migrations_after,
        "table_owner_count": len(all_tables),
        "table_owners_unique": len(all_tables) == len(set(all_tables)) == 33,
        "dynamic_delegation_present": dynamic_delegation,
        "public_sql_in_facade": public_sql_in_facade,
        "prohibited_repository_imports": prohibited_imports,
        "service_api_domain_diff": service_diff,
    }
    for key in (
        "schema_constant_parity", "migrations_source_parity", "table_owners_unique"
    ):
        if not summary[key]:
            failures.append({key: summary[key]})
    if dynamic_delegation or public_sql_in_facade or prohibited_imports or service_diff:
        failures.append({
            "dynamic_delegation": dynamic_delegation,
            "public_sql_in_facade": public_sql_in_facade,
            "prohibited_imports": prohibited_imports,
            "service_api_domain_diff": service_diff,
        })
    payload = {
        "format_version": 1,
        "baseline_commit": BASELINE,
        "table_owners": TABLE_OWNERS,
        "summary": summary,
        "methods": rows,
        "failures": failures,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if failures:
        print(json.dumps({"failures": failures}, indent=2), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
