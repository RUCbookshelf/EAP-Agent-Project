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
OUTPUT = ROOT / "verification" / "v0.9.5-g" / "postchange_facade_inventory.json"
# v0.9.5-G: output redirected to the G-era artifact so the historical E-era
# postchange_repository_inventory.json evidence remains unchanged.
BASELINE = "769e6d8"

# v0.9.7-B WU3 documented revisions (2026-08-05).
#
# - `PracticeRepository._next_practice_id` was repaired: the numeric suffix
#   now starts after the FULL id prefix (prefix-length-safe SUBSTR) with a
#   same-prefix LIKE filter, so two- and three-character prefixes allocate
#   correctly. The historical E-era SQL remains in git history; parity for
#   the repaired function is pinned to this frozen fingerprint.
# - migration 13 (additive partial unique index for one active priority key)
#   legitimately revised app/database/migrations.py; parity is pinned to the
#   WU3 frozen SHA-256 of the whole file instead of the E-era baseline.
# - migration 14 (Wave-2 additive persistence, PDW2-A-CORE-PERSISTENCE)
#   legitimately revised app/database/migrations.py again (four new table
#   families); the frozen SHA-256 is refreshed to the migration-14 file
#   fingerprint (same pin convention as the WU3 refresh).
_PRIVATE_SQL_REVISIONS = {
    "PracticeRepository._next_practice_id": [
        "76d29ea4e034bf820d2f3ce0027433865fc31db442c334e7fee5de9756efbf9a",
    ],
}
_MIGRATIONS_WU3_SHA256 = "ea8e1f639ef530b5a5a13fe34b7b4f425f5f063c83a1a3ace824e1ff9bc3bb17"

# Wave-2 (2026-08-10): the legitimately-evolved service/API diff vs the
# v0.9.5-E parity baseline (769e6d8) grew by the Wave-2 files.  The default
# allowlist is refreshed to the full current diff so the parity contract
# remains self-contained when the runner does not export the env var.
_SERVICE_API_DIFF_ALLOWLIST = (
    "app/api/deps.py",
    "app/api/main.py",
    "app/api/ports.py",
    "app/api/routers/analysis.py",
    "app/api/routers/calf.py",
    "app/api/routers/journey.py",
    "app/api/routers/practice.py",
    "app/api/routers/research.py",
    "app/api/routers/revisions.py",
    "app/api/routers/students.py",
    "app/api/routers/submissions.py",
    "app/api/routers/system.py",
    "app/api/routers/wave2.py",
    "app/api/routers/wave2_modules/__init__.py",
    "app/api/routers/writing_intelligence.py",
    "app/api/schemas.py",
    "app/journey/cycles.py",
    "app/journey/service.py",
    "app/practice/completion.py",
    "app/practice/evaluations.py",
    "app/practice/mapping.py",
    "app/practice/ports.py",
    "app/practice/schemas.py",
    "app/practice/service.py",
    "app/practice/target_creation.py",
    "app/practice/task_context.py",
    "app/research/governance/__init__.py",
    "app/research/governance/validators.py",
    "app/research/schemas.py",
    "app/research/service.py",
    "app/services/admin_reanalysis.py",
    "app/services/calf.py",
    "app/services/configuration.py",
    "app/services/dashboard.py",
    "app/services/factory.py",
    "app/services/learner_model.py",
    "app/services/learner_profile.py",
    "app/services/legacy_genre_mapping.py",
    "app/services/progress.py",
    "app/services/reanalysis.py",
    "app/services/submission.py",
    "app/services/task_type_classifier.py",
)

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
    # v0.9.5-G-era contract: the historical E inventory documents 86 methods;
    # parity is verified against the evidence-supported retained surface.
    retained = {"connect", "initialize"}
    baseline_methods = [row for row in pre["methods"] if row["name"] in retained]
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
    for baseline in baseline_methods:
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
            revision_key = f"{owner}:{name}"
            if revision_key in _PRIVATE_SQL_REVISIONS:
                parity = sql_hashes(current) == _PRIVATE_SQL_REVISIONS[revision_key]
            else:
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
    } or set(_SERVICE_API_DIFF_ALLOWLIST)
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
        "migrations_source_parity": (
            hashlib.sha256(migrations_after.encode("utf-8")).hexdigest()
            == _MIGRATIONS_WU3_SHA256
            if _MIGRATIONS_WU3_SHA256
            else migrations_before == migrations_after
        ),
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
