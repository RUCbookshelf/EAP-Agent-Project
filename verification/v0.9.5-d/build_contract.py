"""v0.9.5-D contract builder.

Generates tests/contracts/api_surface_contract.py from the measured API
surface (verification/v0.9.5-d/api_surface_before.json) plus the documented
classification reasons. The generated file is the version-controlled
approved contract; the contract tests validate it against the live runtime.

Endpoint keys use the real declared paths (e.g. {submission_id}); the
client endpoint map keeps the source f-string placeholder shape ({}).

Usage:
    python verification/v0.9.5-d/build_contract.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tests" / "contracts" / "api_surface_contract.py"


def _norm(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "{p}", path)


# Documented reasons for intentionally unwrapped endpoints (method, path).
UNWRAPPED_REASONS = {
    ("GET", "/api/v1/admin/algorithms"): "admin-only registry inspection",
    ("GET", "/api/v1/admin/metrics"): "admin-only registry inspection",
    ("GET", "/api/v1/calf/analysis-units"): "registry inspection; future feature",
    ("GET", "/api/v1/calf/metrics/{p}"): "registry inspection; future feature",
    ("GET", "/api/v1/research/export/{p}"): "export job status; not part of current Streamlit product",
    ("GET", "/api/v1/students/{p}"): "aggregate student read; accessed through other endpoints",
    ("GET", "/api/v1/students/{p}/calf-trajectories"): "CALF trajectories; future feature",
    ("GET", "/api/v1/students/{p}/history"): "learner history read; not part of current Streamlit product",
    ("GET", "/api/v1/students/{p}/learner-model/diagnostic-trajectories"): "learner-model detail read; not part of current Streamlit product",
    ("GET", "/api/v1/students/{p}/learner-model/history-evidence"): "learner-model detail read; not part of current Streamlit product",
    ("GET", "/api/v1/students/{p}/learner-model/learning-targets"): "learner-model detail read; not part of current Streamlit product",
    ("GET", "/api/v1/students/{p}/learner-model/metric-trajectories"): "learner-model detail read; not part of current Streamlit product",
    ("GET", "/api/v1/students/{p}/learner-model/task-clusters"): "learner-model detail read; not part of current Streamlit product",
    ("GET", "/api/v1/students/{p}/profile"): "learner profile read; not part of current Streamlit product",
    ("GET", "/api/v1/students/{p}/progress"): "learner progress read; not part of current Streamlit product",
    ("GET", "/api/v1/submissions/{p}/analysis-units"): "analysis-unit inspection; future feature",
    ("GET", "/api/v1/submissions/{p}/error-annotations"): "error-annotation inspection; future feature",
    ("GET", "/api/v1/submissions/{p}/syntactic-units"): "syntactic-unit inspection; future feature",
    ("GET", "/api/v1/system/version"): "API/debug inspection",
    ("GET", "/docs"): "framework API documentation",
    ("GET", "/docs/oauth2-redirect"): "framework API documentation",
    ("GET", "/openapi.json"): "framework API documentation",
    ("GET", "/redoc"): "framework API documentation",
    ("POST", "/api/v1/submissions/{p}/calf/reanalyze"): "CALF reanalysis action; future feature",
    ("POST", "/api/v1/submissions/{p}/error-annotations/import"): "error-annotation import; future feature",
    ("POST", "/api/v1/submissions/{p}/pii-review"): "PII review workflow; not part of current Streamlit product",
}

# Documented status for unused/obsolete client methods.
UNUSED_METHOD_REASONS = {
    "activate_configuration": "admin configuration action; not in current UI",
    "create_configuration": "admin configuration action; not in current UI",
    "create_practice_target": "practice-target creation; not in current UI",
    "create_revision": "revision linking; not in current UI",
    "get_calf": "CALF submission read; not in current UI",
    "get_calf_constructs": "CALF registry read; not in current UI",
    "get_calf_metrics": "CALF registry read; not in current UI",
    "get_dashboard": "dashboard read; not in current UI",
    "get_learner_model": "learner-model read; not in current UI",
    "get_learner_model_snapshot": "learner-model read; not in current UI",
    "get_learner_model_snapshots": "learner-model read; not in current UI",
    "get_registries": "admin registry inspection; not in current UI",
    "get_revision_analysis": "revision detail read; not in current UI",
    "get_revision_candidates": "revision detail read; not in current UI",
    "get_revision_comparison": "revision detail read; not in current UI",
    "get_revision_group": "revision detail read; not in current UI",
    "get_revision_trajectory": "revision detail read; not in current UI",
    "lifecycle_state": "convenience helper; not an HTTP wrapper (no endpoint mapping)",
    "list_human_reviews": "review listing; not in current UI",
    "live": "lifecycle inspection used by the app shell, not feature modules",
    "preview_reanalysis": "admin reanalysis preview; not in current UI",
    "ready": "lifecycle inspection used by the app shell, not feature modules",
    "reanalyze": "reanalysis action; not in current UI",
    "research_export_manifest": "manifest read; not in current UI (run response carries the manifest)",
    "research_export_schema": "export schema inspection; not in current UI",
    "rollback_configuration": "admin configuration action; not in current UI",
    "run_reanalysis": "admin reanalysis run; not in current UI",
    "validate_configuration": "admin configuration action; not in current UI",
}


def main() -> int:
    surface = json.loads(
        (ROOT / "verification/v0.9.5-d/api_surface_before.json").read_text(encoding="utf-8")
    )

    # Real endpoint keys; normalized matching against client map paths.
    endpoints = {(e["method"], e["path"]) for e in surface["endpoints"]}

    endpoint_to_methods = {}
    for method, targets in surface["client_endpoint_map"].items():
        for target in targets:
            endpoint_to_methods.setdefault(
                (target["method"], _norm(target["path"])), []
            ).append(method)
    endpoint_to_methods.setdefault(("GET", "/api/v1/research/reviews"), []).append(
        "list_human_reviews"
    )

    used = {}
    for feature, info in surface["feature_calls"].items():
        for method in info["calls"]:
            used.setdefault(method, []).append(feature)

    endpoint_classification = {}
    for endpoint in sorted(endpoints):
        normalized = (endpoint[0], _norm(endpoint[1]))
        methods = endpoint_to_methods.get(normalized, [])
        if not methods:
            endpoint_classification[endpoint] = "C"
        elif any(m in used for m in methods):
            endpoint_classification[endpoint] = "A"
        else:
            endpoint_classification[endpoint] = "B"

    method_names = [m["name"] for m in surface["client_methods"]]
    method_classification = {}
    for method in method_names:
        if method in used:
            method_classification[method] = "A"
        elif any(method in v for v in endpoint_to_methods.values()):
            method_classification[method] = "B"
        else:
            method_classification[method] = "C"

    feature_ports = {
        "student_home": "StudentHomeApiPort",
        "student_writing": "StudentWritingApiPort",
        "student_feedback": "StudentFeedbackApiPort",
        "student_practice": "StudentPracticeApiPort",
        "student_revision": "StudentRevisionApiPort",
        "student_journey": "StudentJourneyApiPort",
        "research_overview": "ResearchOverviewApiPort",
        "research_evidence": "ResearchEvidenceApiPort",
        "research_calf": "ResearchCalfApiPort",
        "research_learning_process": "ResearchLearningProcessApiPort",
        "research_data": "ResearchDataApiPort",
        "research_system_audit": "ResearchSystemAuditApiPort",
    }
    port_methods = {port: set() for port in set(feature_ports.values())}
    for feature, port in feature_ports.items():
        port_methods[port].update(surface["feature_calls"][feature]["calls"])
    port_methods = {port: sorted(methods) for port, methods in port_methods.items()}

    derived_map = {
        method: sorted({(t["method"], t["path"]) for t in targets})
        for method, targets in surface["client_endpoint_map"].items()
    }
    derived_map.setdefault("list_human_reviews", [("GET", "/api/v1/research/reviews")])

    lines = [
        '"""Approved v0.9.5-D frontend API-surface contract (generated).',
        "",
        "This file is the version-controlled, approved endpoint/client/feature",
        "classification contract. It is generated deterministically by",
        "verification/v0.9.5-d/build_contract.py from the measured API surface",
        "and is validated against the live runtime by tests/test_v095d_api_contract.py.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "ENDPOINT_CLASSIFICATION: dict[tuple[str, str], str] = {",
    ]
    for endpoint in sorted(endpoints):
        lines.append(f"    {endpoint!r}: {endpoint_classification[endpoint]!r},")
    lines += [
        "}",
        "",
        "ENDPOINT_UNWRAPPED_REASON: dict[tuple[str, str], str] = {",
    ]
    for endpoint in sorted(endpoints):
        if endpoint_classification[endpoint] == "C":
            normalized = (endpoint[0], _norm(endpoint[1]))
            lines.append(f"    {endpoint!r}: {UNWRAPPED_REASONS[normalized]!r},")
    lines += [
        "}",
        "",
        "CLIENT_METHOD_CLASSIFICATION: dict[str, str] = {",
    ]
    for method in sorted(method_names):
        lines.append(f"    {method!r}: {method_classification[method]!r},")
    lines += [
        "}",
        "",
        "CLIENT_METHOD_STATUS: dict[str, str] = {",
    ]
    for method in sorted(method_names):
        if method_classification[method] != "A":
            lines.append(f"    {method!r}: {UNUSED_METHOD_REASONS[method]!r},")
    lines += [
        "}",
        "",
        "FEATURE_PORTS: dict[str, str] = {",
    ]
    for feature, port in sorted(feature_ports.items()):
        lines.append(f"    {feature!r}: {port!r},")
    lines += [
        "}",
        "",
        "PORT_METHODS: dict[str, list[str]] = {",
    ]
    for port, methods in sorted(port_methods.items()):
        lines.append(f"    {port!r}: {methods!r},")
    lines += [
        "}",
        "",
        "CLIENT_ENDPOINT_MAP: dict[str, list[tuple[str, str]]] = {",
    ]
    for method, targets in sorted(derived_map.items()):
        lines.append(f"    {method!r}: {sorted(targets)!r},")
    lines += [
        "}",
        "",
        "FACADE_PRIVATE_HELPER_ALLOWLIST: tuple[str, ...] = (",
        '    "tests/test_v095c_feature_extraction.py",',
        ")",
        "",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    from collections import Counter
    print(f"wrote {OUT} ({len(endpoints)} endpoints, {len(method_names)} methods)")
    print("endpoint classes:", Counter(endpoint_classification.values()))
    print("method classes:", Counter(method_classification.values()))
    print("port method counts:", {k: len(v) for k, v in port_methods.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
