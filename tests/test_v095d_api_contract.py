"""v0.9.5-D endpoint/client/feature contract enforcement tests.

Validates the approved tests/contracts/api_surface_contract.py against the
live runtime: the 80 endpoint path+method set, the 56 public client methods,
their classifications, the Feature -> Port allowance, and the facade
private-helper import policy.
"""

from __future__ import annotations

import ast
import inspect
import re
import tempfile
from pathlib import Path

from app.api.main import create_app
from app.config import Settings
from app.ui.api_client import WritingFeedbackApiClient
from tests.contracts.api_surface_contract import (
    CLIENT_ENDPOINT_MAP,
    CLIENT_METHOD_CLASSIFICATION,
    CLIENT_METHOD_STATUS,
    ENDPOINT_CLASSIFICATION,
    ENDPOINT_UNWRAPPED_REASON,
    FACADE_PRIVATE_HELPER_ALLOWLIST,
    FEATURE_PORTS,
    PORT_METHODS,
)


ROOT = Path(__file__).resolve().parents[1]
FEATURES_ROOT = ROOT / "app" / "ui" / "features"

FEATURE_FILES = {
    "student_home": "student/home.py",
    "student_writing": "student/writing.py",
    "student_feedback": "student/feedback.py",
    "student_practice": "student/practice.py",
    "student_revision": "student/revision.py",
    "student_journey": "student/journey.py",
    "research_overview": "research/overview.py",
    "research_evidence": "research/evidence.py",
    "research_calf": "research/calf.py",
    "research_learning_process": "research/learning_process.py",
    "research_data": "research/data.py",
    "research_system_audit": "research/system_audit.py",
}


def _norm(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "{p}", path)


def _runtime_endpoints() -> set[tuple[str, str]]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        settings = Settings(
            database_path=str(Path(tmp_dir) / "surface.db"),
            llm_provider="local",
            deepseek_api_key=None,
            deepseek_base_url="https://example.invalid",
            deepseek_model="deepseek-test",
        )
        app = create_app(settings)
        endpoints = set()
        for route in app.routes:
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None)
            if path is None or methods is None:
                continue
            for method in methods:
                if method not in {"HEAD", "OPTIONS"}:
                    endpoints.add((method, path))
    return endpoints


def _runtime_client_methods() -> set[str]:
    client = WritingFeedbackApiClient(base_url="http://127.0.0.1:8000")
    return {
        name
        for name in dir(client)
        if not name.startswith("_") and callable(getattr(client, name))
    }


def _client_endpoint_map_from_source() -> dict[str, list[tuple[str, str]]]:
    source = (ROOT / "app/ui/api_client.py").read_text(encoding="utf-8-sig")
    tree = ast.parse(source)
    client_class = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "WritingFeedbackApiClient"
    )
    def _request_targets(func) -> list[tuple[str, str]]:
        targets = []
        for node in ast.walk(func):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_request"
                and len(node.args) >= 2
            ):
                method_arg, path_arg = node.args[0], node.args[1]
                if not isinstance(method_arg, ast.Constant):
                    continue
                if isinstance(path_arg, ast.Constant):
                    targets.append((method_arg.value, path_arg.value))
                elif isinstance(path_arg, ast.JoinedStr):
                    path_text = "".join(
                        part.value if isinstance(part, ast.Constant) else "{}"
                        for part in path_arg.values
                    )
                    targets.append((method_arg.value, path_text))
        return targets

    helper_targets: dict[str, list[tuple[str, str]]] = {}
    for func in client_class.body:
        if isinstance(func, ast.FunctionDef) and func.name.startswith("_"):
            helper_targets[func.name] = _request_targets(func)

    mapping: dict[str, list[tuple[str, str]]] = {}
    for func in client_class.body:
        if not isinstance(func, ast.FunctionDef) or func.name.startswith("_"):
            continue
        targets = _request_targets(func)
        for node in ast.walk(func):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_submit_long_running"
            ):
                targets.extend(helper_targets.get("_submit_long_running", []))
        if targets:
            mapping[func.name] = targets
    return mapping


def _feature_calls() -> dict[str, set[str]]:
    result = {}
    for feature, relative in FEATURE_FILES.items():
        path = FEATURES_ROOT / relative
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        calls: set[str] = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "api_client"
            ):
                calls.add(node.func.attr)
        result[feature] = calls
    return result


def test_endpoint_set_matches_runtime_and_is_fully_classified():
    runtime = _runtime_endpoints()
    assert len(runtime) == 80
    assert runtime == set(ENDPOINT_CLASSIFICATION)
    for endpoint, classification in ENDPOINT_CLASSIFICATION.items():
        assert classification in {"A", "B", "C"}
        if classification == "C":
            assert endpoint in ENDPOINT_UNWRAPPED_REASON
    assert set(ENDPOINT_UNWRAPPED_REASON) == {
        endpoint for endpoint, cls in ENDPOINT_CLASSIFICATION.items() if cls == "C"
    }


def test_client_method_set_matches_runtime_and_is_fully_classified():
    runtime = _runtime_client_methods()
    assert runtime == set(CLIENT_METHOD_CLASSIFICATION)
    for method, classification in CLIENT_METHOD_CLASSIFICATION.items():
        assert classification in {"A", "B", "C"}
        if classification != "A":
            assert method in CLIENT_METHOD_STATUS
    assert set(CLIENT_METHOD_STATUS) == {
        method for method, cls in CLIENT_METHOD_CLASSIFICATION.items() if cls != "A"
    }


def test_endpoint_wrapper_state_matches_client_source():
    derived = _client_endpoint_map_from_source()
    derived.setdefault("list_human_reviews", [("GET", "/api/v1/research/reviews")])
    assert derived == CLIENT_ENDPOINT_MAP, "client endpoint map drifted"
    wrapped = {
        (method, _norm(path))
        for targets in derived.values()
        for method, path in targets
    }
    for endpoint, classification in ENDPOINT_CLASSIFICATION.items():
        is_wrapped = (endpoint[0], _norm(endpoint[1])) in wrapped
        if classification in {"A", "B"}:
            assert is_wrapped, f"{endpoint} is classified {classification} but has no wrapper"
        else:
            assert not is_wrapped, f"{endpoint} is classified C but has a wrapper"


def test_no_silent_wrapper_or_endpoint_drift():
    derived = _client_endpoint_map_from_source()
    derived.setdefault("list_human_reviews", [("GET", "/api/v1/research/reviews")])
    runtime_methods = _runtime_client_methods()
    contract_methods = set(CLIENT_METHOD_CLASSIFICATION)
    assert runtime_methods == contract_methods, "client method set drifted"
    obsolete = {
        method for method, cls in CLIENT_METHOD_CLASSIFICATION.items() if cls == "C"
    }
    assert set(derived) == contract_methods - obsolete, "wrapper set drifted"
    for method, classification in CLIENT_METHOD_CLASSIFICATION.items():
        targets = derived.get(method, [])
        if classification == "C":
            assert targets == [], f"obsolete method {method} unexpectedly maps to endpoints"
        else:
            assert targets, f"classified method {method} has no endpoint mapping"
            for http_method, path in targets:
                matched = next(
                    endpoint for endpoint in ENDPOINT_CLASSIFICATION
                    if endpoint[0] == http_method and _norm(endpoint[1]) == _norm(path)
                )
                assert ENDPOINT_CLASSIFICATION[matched] in {"A", "B"}, (
                    f"{method} wraps an unwrapped or unknown endpoint {(http_method, path)}"
                )


def test_feature_calls_are_owned_by_their_port_and_port_has_no_unused_methods():
    used_by_features = {method for calls in _feature_calls().values() for method in calls}
    assert used_by_features <= set(CLIENT_METHOD_CLASSIFICATION)
    for feature, port in FEATURE_PORTS.items():
        calls = _feature_calls()[feature]
        allowed = set(PORT_METHODS[port])
        assert calls <= allowed, f"{feature} calls methods outside {port}: {calls - allowed}"
        assert allowed <= calls, f"{port} exposes unused methods: {allowed - calls}"
        assert calls == allowed, f"{feature}/{port} method sets differ"
    # Cross-feature guards.
    student_methods = set()
    research_methods = set()
    for feature, port in FEATURE_PORTS.items():
        if port.startswith("Student"):
            student_methods |= set(PORT_METHODS[port])
        else:
            research_methods |= set(PORT_METHODS[port])
    research_only = {
        "get_analyses", "get_configurations", "get_diagnostic_audit",
        "get_engagement_traces", "get_pii_candidates", "get_transfer_evidence",
        "preview_learner_model", "rebuild_learner_model", "research_data_quality",
        "research_export_history", "research_export_preview", "research_export_run",
        "create_dataset_split", "create_human_review", "health",
    }
    student_write = {"submit", "create_exercise", "submit_exercise_attempt"}
    assert not (student_methods & research_only), "Student feature gained Research/Admin methods"
    assert not (research_methods & student_write), "Research feature gained Student write methods"


def test_every_port_method_exists_on_the_concrete_client_with_compatible_signature():
    client = WritingFeedbackApiClient(base_url="http://127.0.0.1:8000")
    for port, methods in PORT_METHODS.items():
        for method in methods:
            client_method = getattr(client, method, None)
            assert callable(client_method), f"{port}.{method} missing on concrete client"
            # Bound client methods already exclude self.
            client_params = list(inspect.signature(client_method).parameters)
            port_module = __import__(
                "app.ui.ports.student" if port.startswith("Student") else "app.ui.ports.research",
                fromlist=[port],
            )
            port_method = getattr(port_module, port).__dict__[method]
            port_params = list(inspect.signature(port_method).parameters)[1:]  # drop self
            assert port_params == client_params, (
                f"{port}.{method} params {port_params} != client {client_params}"
            )


def test_facade_private_helper_imports_are_restricted_to_allowlist():
    pattern = ("app.ui.pages.student_pages", "app.ui.pages.research_pages")
    offenders = []
    for path in (ROOT / "tests").rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in pattern:
                for alias in node.names:
                    if alias.name.startswith("_"):
                        relative = str(path).replace(str(ROOT) + "\\", "").replace("\\", "/")
                        if relative not in FACADE_PRIVATE_HELPER_ALLOWLIST:
                            offenders.append(f"{relative}:{node.lineno}: {alias.name}")
    assert offenders == [], f"new facade private-helper imports: {offenders}"


def test_ports_do_not_import_backend_or_concrete_client():
    for path in (ROOT / "app" / "ui" / "ports").rglob("*.py"):
        if path.name == "__init__.py":
            continue
        source = path.read_text(encoding="utf-8")
        for needle in ("app.practice", "app.research.schemas", "app.services",
                       "app.database", "app.repositories", "app.ui.api_client"):
            assert needle not in source, f"{path} imports {needle}"


def test_features_do_not_type_against_the_concrete_client():
    for path in FEATURES_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "app.ui.api_client":
                names = [alias.name for alias in node.names]
                assert "WritingFeedbackApiClient" not in names, (
                    f"{path} imports the concrete client"
                )
            if isinstance(node, ast.Name) and node.id == "WritingFeedbackApiClient":
                assert False, f"{path} references the concrete client"
