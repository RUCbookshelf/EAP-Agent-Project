from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "app" / "database" / "repository.py"
OUTPUT = Path(__file__).with_name("prechange_repository_inventory.json")

OWNERS: dict[str, tuple[str, ...]] = {
    "SystemRepository": (
        "connect", "initialize", "record_versions", "counts", "ping",
        "migration_version", "transaction", "get_system_versions",
    ),
    "SubmissionRepository": (
        "save_essay", "save_feedback", "save_history", "prior_records",
        "get_feedback_record", "get_llm_calls", "get_history_record",
        "list_all_submissions", "get_submission_bundle",
        "list_student_submissions", "get_exercises",
    ),
    "AnalysisRepository": (
        "save_analysis", "save_analysis_run", "list_analysis_runs",
        "get_latest_analysis_run", "get_analysis_run", "get_metric_results",
        "get_analysis_artifact", "save_diagnosis",
    ),
    "CalfRepository": (
        "save_diagnostic_calibration", "get_diagnostic_calibration",
        "list_analysis_units", "save_error_annotations", "list_error_annotations",
    ),
    "LearnerRepository": (
        "get_student", "list_all_students", "list_student_history",
        "get_latest_learner_profile", "save_learner_profile_snapshot",
        "list_history_evidence", "list_learner_profile_snapshots",
        "list_longitudinal_records", "list_visualization_records",
    ),
    "RevisionRepository": (
        "normalize_revision_stage", "create_revision_group", "link_revision",
        "get_revision_group", "get_revision_group_for_submission",
        "list_revision_candidates", "save_revision_snapshot",
        "list_revision_snapshots", "get_latest_revision_snapshot",
    ),
    "ConfigurationRepository": (
        "list_configurations", "get_configuration", "get_active_configuration",
        "create_configuration", "set_configuration_validation",
        "activate_configuration", "list_configuration_audit",
    ),
    "PracticeRepository": (
        "save_practice_target", "list_practice_targets", "get_practice_target",
        "save_exercise_instance", "list_exercise_instances", "get_exercise_instance",
        "save_exercise_attempt", "list_exercise_attempts", "save_practice_evaluation",
        "list_practice_evaluations", "list_practice_evaluations_by_student",
        "list_essays_by_student", "list_analysis_runs_for_student",
        "list_feedback_records_for_student", "list_exercise_attempts_by_student",
        "save_feedback_engagement_trace", "list_feedback_engagement_traces",
        "save_within_task_response_candidate", "list_within_task_responses",
        "save_transfer_evidence_candidate", "list_transfer_evidence_candidates",
        "save_practice_state_snapshot", "list_practice_state_snapshots",
    ),
    "ResearchRepository": (
        "save_human_review", "list_human_reviews", "apply_pii_review",
        "save_export_job", "list_export_jobs", "get_export_job",
    ),
}

DIRECT_WRITES = {
    "record_versions", "save_essay", "save_analysis", "save_analysis_run",
    "save_diagnosis", "save_diagnostic_calibration", "save_feedback", "save_history",
    "save_error_annotations", "save_learner_profile_snapshot", "create_revision_group",
    "link_revision", "save_revision_snapshot", "create_configuration",
    "set_configuration_validation", "activate_configuration", "save_practice_target",
    "save_exercise_instance", "save_exercise_attempt", "save_practice_evaluation",
    "save_feedback_engagement_trace", "save_within_task_response_candidate",
    "save_transfer_evidence_candidate", "save_practice_state_snapshot",
    "save_human_review", "apply_pii_review", "save_export_job",
}
INFRASTRUCTURE = {"connect", "initialize", "transaction"}
PURE = {"normalize_revision_stage"}
COMPOSITE_CONNECTIONS = {
    "get_latest_analysis_run", "get_analysis_run", "create_revision_group",
    "link_revision", "get_revision_group_for_submission", "list_revision_candidates",
    "get_latest_revision_snapshot", "create_configuration",
    "set_configuration_validation", "activate_configuration",
    "list_visualization_records", "save_practice_target", "save_exercise_instance",
    "save_exercise_attempt", "save_practice_evaluation",
    "save_feedback_engagement_trace", "save_within_task_response_candidate",
    "save_transfer_evidence_candidate", "save_practice_state_snapshot",
    "save_human_review",
}
CROSS_AGGREGATE = {
    "counts", "prior_records", "get_submission_bundle", "get_student",
    "list_all_students", "list_analysis_units", "save_error_annotations",
    "list_longitudinal_records", "list_visualization_records",
    "create_revision_group", "link_revision", "get_revision_group",
    "get_revision_group_for_submission", "list_revision_candidates",
    "list_essays_by_student", "list_analysis_runs_for_student",
    "list_feedback_records_for_student",
}

SQL_START = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|PRAGMA|CREATE|ALTER|DROP|BEGIN)\b", re.I)
TABLE_READ = re.compile(r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)
TABLE_WRITE = re.compile(r"\b(?:INSERT\s+(?:OR\s+\w+\s+)?INTO|UPDATE|DELETE\s+FROM|ALTER\s+TABLE|CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?|DROP\s+TABLE)\s+([A-Za-z_][A-Za-z0-9_]*)", re.I)


def normalize_sql(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().rstrip(";")).strip()


def owner_for(name: str) -> str:
    matches = [owner for owner, names in OWNERS.items() if name in names]
    if len(matches) != 1:
        raise AssertionError(f"owner classification for {name}: {matches}")
    return matches[0]


def classification(name: str) -> str:
    if name in DIRECT_WRITES:
        return "write"
    if name in INFRASTRUCTURE:
        return "infrastructure_write_capable"
    if name in PURE:
        return "pure"
    return "read"


def connection_behavior(name: str) -> str:
    if name == "connect":
        return "returns_open_caller_owned_closing_connection"
    if name == "transaction":
        return "explicit_BEGIN_commit_rollback_close"
    if name in COMPOSITE_CONNECTIONS:
        return "multiple_separate_connection_scopes"
    if name in PURE:
        return "no_connection"
    return "single_with_connect_scope_auto_commit_or_rollback"


def signature(node: ast.FunctionDef) -> str:
    args = ast.unparse(node.args)
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"({args}){returns}"


def sql_inventory(node: ast.FunctionDef) -> list[dict[str, object]]:
    values: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str) and SQL_START.search(child.value):
            values.append(child.value)
    result = []
    for ordinal, value in enumerate(values, start=1):
        normalized = normalize_sql(value)
        result.append({
            "ordinal": ordinal,
            "normalized_sql": normalized,
            "sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            "tables_read": sorted(set(TABLE_READ.findall(normalized))),
            "tables_written": sorted(set(TABLE_WRITE.findall(normalized))),
        })
    return result


def called_methods(node: ast.FunctionDef) -> list[str]:
    result = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            result.append(child.func.attr)
    return sorted(set(result))


def python_files() -> list[Path]:
    app_files = [p for p in (ROOT / "app").rglob("*.py") if "ui" not in p.relative_to(ROOT / "app").parts]
    test_files = list((ROOT / "tests").rglob("*.py"))
    return sorted(set(app_files + test_files))


def scan_calls_and_protocols(method_names: set[str]) -> tuple[dict[str, list[dict[str, object]]], dict[str, list[str]]]:
    sites: dict[str, list[dict[str, object]]] = {name: [] for name in method_names}
    protocols: dict[str, list[str]] = {}
    for path in python_files():
        if path == SOURCE:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                (isinstance(base, ast.Name) and base.id == "Protocol")
                or (isinstance(base, ast.Attribute) and base.attr == "Protocol")
                for base in node.bases
            ):
                protocols[f"{rel}:{node.name}"] = [
                    item.name for item in node.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("_")
                ]
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in method_names:
                sites[node.func.attr].append({"file": rel, "line": node.lineno})
    return sites, protocols


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE))
    database = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Database")
    methods = [
        node for node in database.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    ]
    method_names = {node.name for node in methods}
    expected = set().union(*map(set, OWNERS.values()))
    if method_names != expected:
        raise AssertionError({"missing_classification": sorted(method_names - expected), "missing_methods": sorted(expected - method_names)})
    sites, protocols = scan_calls_and_protocols(method_names)
    rows = []
    for node in methods:
        sql = sql_inventory(node)
        rows.append({
            "name": node.name,
            "signature": signature(node),
            "file": SOURCE.relative_to(ROOT).as_posix(),
            "line_start": node.lineno,
            "line_end": node.end_lineno,
            "classification": classification(node.name),
            "owner": owner_for(node.name),
            "cross_aggregate": node.name in CROSS_AGGREGATE,
            "connection_behavior": connection_behavior(node.name),
            "commit_behavior": "explicit" if node.name == "transaction" else ("context_manager" if node.name not in PURE | {"connect"} else "none"),
            "rollback_behavior": "explicit_and_reraise" if node.name == "transaction" else ("sqlite_connection_context" if node.name not in PURE | {"connect"} else "none"),
            "return_annotation": ast.unparse(node.returns) if node.returns else None,
            "delegates_or_calls": called_methods(node),
            "sql": sql,
            "tables_read_direct": sorted({table for item in sql for table in item["tables_read"]}),
            "tables_written_direct": sorted({table for item in sql for table in item["tables_written"]}),
            "direct_call_sites": sites[node.name],
            "protocols_declaring_method": sorted(key for key, names in protocols.items() if node.name in names),
        })
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    payload = {
        "format_version": 1,
        "baseline_commit": head,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "public_method_count": len(rows),
        "classification_counts": {
            key: sum(row["classification"] == key for row in rows)
            for key in ("read", "write", "infrastructure_write_capable", "pure")
        },
        "owner_counts": {owner: len(names) for owner, names in OWNERS.items()},
        "cross_aggregate_method_count": sum(row["cross_aggregate"] for row in rows),
        "protocols": protocols,
        "methods": rows,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}")
    print(json.dumps({key: payload[key] for key in ("baseline_commit", "public_method_count", "classification_counts", "owner_counts", "cross_aggregate_method_count")}, indent=2))


if __name__ == "__main__":
    main()
