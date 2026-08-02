"""v0.9.5-D Practice and Research UI-contract parity tests.

Proves the UI-safe contracts still match the authoritative backend
specifications and would detect future backend/UI drift.
"""

from __future__ import annotations

from app.practice.schemas import default_exercise_specifications
from app.research.schemas import ExportFilter, ExportFormat, ExportJob, PrivacyMode
from app.ui.contracts.practice import EXERCISE_INSTRUCTIONS, exercise_instruction
from app.ui.contracts.research import build_export_job_payload


# ---------------------------------------------------------------------------
# A. Practice parity
# ---------------------------------------------------------------------------


def test_practice_contract_matches_backend_for_every_exercise_type():
    backend = default_exercise_specifications()
    assert set(EXERCISE_INSTRUCTIONS) == set(backend), (
        "exercise-type set drifted from the backend specification"
    )
    for exercise_type, backend_spec in backend.items():
        ui_contract = EXERCISE_INSTRUCTIONS[exercise_type]
        assert ui_contract.exercise_type == exercise_type
        for lang in ("en", "zh_CN"):
            assert ui_contract.learner_instructions[lang] == (
                backend_spec.learner_instructions[lang]
            ), f"{exercise_type} {lang} instruction drifted"


def test_practice_fallback_behavior_matches_backend():
    backend = default_exercise_specifications()
    for exercise_type, backend_spec in backend.items():
        # Same lookup chain: lang -> en -> stored fallback.
        assert exercise_instruction(
            exercise_type, "en", "fallback"
        ) == backend_spec.learner_instructions["en"]
        assert exercise_instruction(
            exercise_type, "zh_CN", "fallback"
        ) == backend_spec.learner_instructions["zh_CN"]
        assert exercise_instruction(
            exercise_type, "unsupported_lang", "fallback"
        ) == backend_spec.learner_instructions["en"]
    assert exercise_instruction("unknown_type", "en", "stored fallback") == "stored fallback"


def test_practice_stable_identifiers_match_backend():
    backend = default_exercise_specifications()
    for exercise_type in EXERCISE_INSTRUCTIONS:
        assert exercise_type in backend
        assert EXERCISE_INSTRUCTIONS[exercise_type].exercise_type == exercise_type


# ---------------------------------------------------------------------------
# B. Research export payload parity
# ---------------------------------------------------------------------------


def _normalize(payload: dict) -> dict:
    normalized = dict(payload)
    normalized["created_at"] = "<CREATED_AT>"
    return normalized


PRIVACY_MODES = ("pseudonymized", "internal_research", "minimal_anonymous")
FORMAT_COMBOS = (["jsonl"], ["csv"], ["jsonl", "csv"])


def test_research_payload_parity_all_privacy_formats():
    for privacy in PRIVACY_MODES:
        for formats in FORMAT_COMBOS:
            ui_payload = build_export_job_payload(privacy, formats)
            backend_payload = ExportJob(
                filter_spec=ExportFilter(),
                privacy_mode=PrivacyMode(privacy),
                formats=[ExportFormat(f) for f in formats],
            ).model_dump(mode="json")
            assert _normalize(ui_payload) == _normalize(backend_payload), (
                f"payload mismatch: {privacy} {formats}"
            )


def test_research_payload_default_filter_structure_matches_backend():
    backend_filter = ExportFilter().model_dump(mode="json")
    ui_payload = build_export_job_payload("pseudonymized", ["jsonl"])
    assert ui_payload["filter_spec"] == backend_filter
    # Absent-vs-default field structure: the UI contract sends the full
    # serialized shape, including explicitly-None optional fields.
    assert set(ui_payload.keys()) == {
        "export_id", "export_schema_version", "filter_spec", "privacy_mode",
        "formats", "status", "created_at", "completed_at", "export_directory",
        "file_count", "record_counts", "excluded_counts", "manifest_path",
    }


def test_research_payload_enum_strings_and_timestamps():
    for privacy in PRIVACY_MODES:
        for formats in FORMAT_COMBOS:
            ui_payload = build_export_job_payload(privacy, formats)
            assert ui_payload["privacy_mode"] == privacy
            assert ui_payload["formats"] == formats
            assert ui_payload["filter_spec"]["privacy_mode"] == "pseudonymized"
            assert ui_payload["filter_spec"]["formats"] == ["jsonl"]
            assert ui_payload["export_schema_version"] == "research-export-v0.1"
            assert ui_payload["status"] == "preview"
            assert ui_payload["created_at"].endswith("+00:00")
            assert "T" in ui_payload["created_at"]
