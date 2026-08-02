"""v0.9.5-D Port definition tests.

Pins the twelve Port classes to the approved contract (names, method sets,
parameter compatibility) and proves WritingFeedbackApiClient remains the sole
concrete HTTP client.
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path
from typing import Protocol

import app.ui.ports.research as research_ports
import app.ui.ports.student as student_ports
from app.ui.api_client import WritingFeedbackApiClient
from tests.contracts.api_surface_contract import PORT_METHODS


ROOT = Path(__file__).resolve().parents[1]


def _port_classes():
    ports = {}
    for module in (student_ports, research_ports):
        for name, member in vars(module).items():
            if isinstance(member, type) and name.endswith("ApiPort"):
                ports[name] = member
    return ports


def test_twelve_ports_exist_with_approved_methods():
    ports = _port_classes()
    assert set(ports) == set(PORT_METHODS)
    for name, methods in PORT_METHODS.items():
        declared = {
            attr
            for attr in vars(ports[name])
            if not attr.startswith("_") and callable(getattr(ports[name], attr))
        }
        assert declared == set(methods), f"{name}: {declared} != {methods}"


def test_concrete_client_is_the_only_http_implementation():
    # The concrete client exists exactly once and is not subclassed/replaced.
    assert WritingFeedbackApiClient.__module__ == "app.ui.api_client"
    # Feature modules define no classes (no per-feature wrapper objects).
    for path in (ROOT / "app/ui/features").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            assert not isinstance(node, ast.ClassDef), f"unexpected class in {path}"
    # Port modules define only typing.Protocol classes.
    for name, port in _port_classes().items():
        assert issubclass(port, Protocol), f"{name} is not a Protocol"


def test_port_parameter_shapes_match_concrete_client():
    client = WritingFeedbackApiClient(base_url="http://127.0.0.1:8000")
    for port, methods in PORT_METHODS.items():
        port_module = research_ports if port.startswith("Research") else student_ports
        port_class = getattr(port_module, port)
        for method in methods:
            # Bound client methods already exclude self.
            client_signature = inspect.signature(getattr(client, method))
            port_signature = inspect.signature(port_class.__dict__[method])
            client_params = list(client_signature.parameters.values())
            port_params = list(port_signature.parameters.values())[1:]  # drop self
            assert [p.name for p in client_params] == [p.name for p in port_params]
            assert [p.kind for p in client_params] == [p.kind for p in port_params]
            for c_param, p_param in zip(client_params, port_params):
                assert c_param.default == p_param.default, (
                    f"{port}.{method} default mismatch for {c_param.name}"
                )


def test_port_modules_are_self_contained():
    for path in (ROOT / "app/ui/ports").rglob("*.py"):
        if path.name == "__init__.py":
            continue
        source = path.read_text(encoding="utf-8-sig")
        imports = re.findall(r"^\s*(?:from ([\w.]+) import|import ([\w.]+))", source, re.M)
        modules = [m[0] or m[1] for m in imports]
        for module in modules:
            assert module.startswith(("typing", "__future__")), (
                f"{path} imports {module}"
            )
