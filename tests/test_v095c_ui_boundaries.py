"""v0.9.5-C UI boundary-restoration tests.

Proves that production modules under app/ui no longer import backend feature
implementation modules, that the Practice instruction contract preserves the
exact bilingual display strings, and that the Research Data export payload
contract serializes to exactly the JSON previously produced by backend
Pydantic models.
"""

from __future__ import annotations

import ast
from pathlib import Path

from app.research.schemas import ExportFilter, ExportFormat, ExportJob, PrivacyMode
from app.ui.contracts.practice import EXERCISE_INSTRUCTIONS, exercise_instruction
from app.ui.contracts.research import build_export_job_payload
from app.ui.features.student.practice import _practice_instruction


UI_ROOT = Path(__file__).resolve().parents[1] / "app" / "ui"

# Explicit allow-list for approved frontend dependencies. Anything else under
# app.* (backend feature implementation modules) is prohibited.
ALLOWED_APP_PREFIXES = ("app.config", "app.errors", "app.ui")
PROHIBITED_PREFIXES = (
    "app.practice",
    "app.research",
    "app.services",
    "app.database",
    "app.repositories",
)


def _production_ui_imports() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for path in UI_ROOT.rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    found.append((str(path), alias.name))
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.append((str(path), node.module))
    return found


def test_production_ui_never_imports_backend_implementation_modules():
    violations = [
        (path, module)
        for path, module in _production_ui_imports()
        if module.startswith(PROHIBITED_PREFIXES)
    ]
    assert violations == [], f"prohibited UI imports found: {violations}"


def test_production_ui_app_imports_use_only_the_allow_list():
    violations = [
        (path, module)
        for path, module in _production_ui_imports()
        if module.startswith("app.")
        and not module.startswith(ALLOWED_APP_PREFIXES)
    ]
    assert violations == [], f"UI imports outside the allow-list: {violations}"


def test_ui_contracts_do_not_import_backend_modules():
    for module_name in ("practice", "research"):
        source = (UI_ROOT / "contracts" / f"{module_name}.py").read_text(encoding="utf-8")
        for prefix in PROHIBITED_PREFIXES:
            assert prefix not in source


def test_practice_contract_preserves_exact_bilingual_instructions():
    expected = {
        "guided_sentence_rewrite": {
            "en": "Rewrite the following sentence to address the selected priority.",
            "zh_CN": "请重写以下句子以解决选定的优先级问题。",
        },
        "constrained_micro_revision": {
            "en": "Revise this short text under the given constraints.",
            "zh_CN": "请在给定约束下修改这段短文。",
        },
        "target_feature_identification": {
            "en": "Identify which part of the passage illustrates the selected issue.",
            "zh_CN": "请指出文章中哪个部分体现了所选问题。",
        },
    }
    assert set(EXERCISE_INSTRUCTIONS) == set(expected)
    for exercise_type, instructions in expected.items():
        assert EXERCISE_INSTRUCTIONS[exercise_type].learner_instructions == instructions
        for lang, text in instructions.items():
            assert exercise_instruction(exercise_type, lang, "fallback") == text


def test_practice_instruction_lookup_behavior_is_preserved():
    exercise = {
        "exercise_type": "guided_sentence_rewrite",
        "instructions": "Stored English instruction",
    }
    assert _practice_instruction(exercise, "en") == (
        "Rewrite the following sentence to address the selected priority."
    )
    assert _practice_instruction(exercise, "zh_CN") == "请重写以下句子以解决选定的优先级问题。"
    # Unknown exercise type falls back to the stored instruction exactly as before.
    unknown = {"exercise_type": "unknown_type", "instructions": "Stored fallback"}
    assert _practice_instruction(unknown, "en") == "Stored fallback"


def _normalize_created_at(payload: dict) -> dict:
    normalized = dict(payload)
    normalized["created_at"] = "<CREATED_AT>"
    return normalized


def test_research_export_payload_matches_backend_serialization():
    combos = [
        ("pseudonymized", ["jsonl"]),
        ("internal_research", ["csv"]),
        ("minimal_anonymous", ["jsonl", "csv"]),
    ]
    for privacy_mode, formats in combos:
        contract = build_export_job_payload(privacy_mode, formats)
        backend = ExportJob(
            filter_spec=ExportFilter(),
            privacy_mode=PrivacyMode(privacy_mode),
            formats=[ExportFormat(f) for f in formats],
        ).model_dump(mode="json")
        assert _normalize_created_at(contract) == _normalize_created_at(backend), (
            f"payload mismatch for {privacy_mode} {formats}"
        )
        # created_at must use the same UTC ISO format as the backend default.
        assert contract["created_at"].endswith("+00:00")
        assert backend["created_at"].endswith("+00:00")


def test_research_payload_privacy_and_format_values_are_unchanged():
    payload = build_export_job_payload("internal_research", ["csv"])
    assert payload["privacy_mode"] == "internal_research"
    assert payload["formats"] == ["csv"]
    assert payload["filter_spec"]["privacy_mode"] == "pseudonymized"
    assert payload["filter_spec"]["formats"] == ["jsonl"]
    assert payload["export_schema_version"] == "research-export-v0.1"
