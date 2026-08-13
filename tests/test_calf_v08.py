from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.main import create_app
from app.calf import (
    ErrorAnnotation, SyntacticUnitSegmenter, accuracy_availability, calculate_hdd,
    calculate_mtld, default_calf_registry, writing_output_rate,
)
from app.config import load_settings
from app.configuration import ConfigurationPayload
from app.database import Database, LATEST_MIGRATION_VERSION
from app.database.migrations import rollback, upgrade
from app.services.factory import build_analyzer


FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "calf_measurement" / "cases_a_m.json").read_text(encoding="utf-8")
)
REFERENCE_TOKENS = (
    "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau "
    "upsilon phi chi psi omega " * 3
    + "alpha beta gamma delta epsilon zeta eta theta iota kappa " * 3
).split()


def settings(tmp_path):
    return replace(
        load_settings(), database_path=tmp_path / "calf.db", llm_provider="local",
        deepseek_api_key=None, application_version="0.8.0", database_migration_version=10,
    )


def payload(student="CALF-V08", **updates):
    data = {
        "student_id": student, "writing_prompt": "Explain why evidence matters.",
        "genre": "argumentative essay", "draft_stage": "first draft", "timed": False,
        "time_limit_minutes": None, "tool_use": "none",
        "essay_text": FIXTURES["case_c_variation"],
        "submitted_at": datetime(2026, 7, 30, tzinfo=timezone.utc).isoformat(),
    }
    data.update(updates)
    return data


def test_construct_measurement_and_analysis_unit_registries_are_separate_and_filterable():
    registry = default_calf_registry()
    assert {item.construct_id for item in registry.list_constructs()} == {
        "lexical_complexity", "syntactic_complexity", "accuracy", "product_fluency"
    }
    assert len(registry.list_units()) == 14
    assert registry.get_specification("mtld").measurement_status == "research_metric"
    candidates = registry.list_specifications(measurement_status="automatic_candidate")
    assert candidates and all(not item.eligible_for_diagnosis for item in candidates)
    assert all(not item.eligible_for_revision_priority for item in registry.list_specifications())
    assert registry.get_specification("lexical_sophistication").measurement_status == "unavailable"
    assert registry.list_specifications(manual_annotation_required=True)


def test_metric_registry_rejects_duplicate_measurement_version():
    registry = default_calf_registry()
    with pytest.raises(ValueError, match="already registered"):
        registry.register_specification(registry.get_specification("mtld"))


def test_mtld_forward_reverse_partial_and_reference_value():
    result = calculate_mtld(REFERENCE_TOKENS, threshold=0.72)
    assert result["status"] == "available"
    assert result["forward_value"] is not None and result["reverse_value"] is not None
    assert result["combined_value"] == pytest.approx(25.435279187817258)
    assert "partial_factor" in result["forward"]
    assert result == calculate_mtld(REFERENCE_TOKENS, threshold=0.72)


def test_mtld_reverse_order_is_recorded_and_short_text_is_not_fabricated():
    short = calculate_mtld(FIXTURES["case_a_short"].lower().split())
    assert short["status"] == "insufficient_data" and short["value"] is None
    ordered = calculate_mtld(FIXTURES["case_b_repetition"].split())
    assert ordered["forward"] and ordered["reverse"]
    assert ordered["token_count"] == len(FIXTURES["case_b_repetition"].split())


def test_hdd_matches_reference_and_short_text_does_not_reduce_sample_silently():
    result = calculate_hdd(REFERENCE_TOKENS, sample_size=42)
    assert result["value"] == pytest.approx(0.4961426331615973)
    assert result["effective_sample_size"] == 42
    short = calculate_hdd("one two three".split(), sample_size=42)
    assert short["status"] == "insufficient_data" and short["value"] is None
    assert short["effective_sample_size"] is None and short["sample_size"] == 42


def test_spacy_calf_metrics_save_normalization_parameters_and_intermediates(tmp_path):
    analyzer = build_analyzer(settings(tmp_path))
    result = analyzer.analyze(FIXTURES["case_d_normalization"], writing_prompt="Prompt")
    metrics = {item["metric_id"]: item for item in result.metric_results}
    assert metrics["type_token_ratio"]["measurement_metadata"]["token_count_used"] == 6
    assert metrics["type_token_ratio"]["measurement_metadata"]["type_count_used"] == 2
    assert metrics["mtld"]["parameters"]["factor_threshold"] == 0.72
    assert metrics["hdd"]["parameters"]["sample_size"] == 42
    assert "type_frequencies" in metrics["hdd"]["intermediate_values"]
    assert metrics["lexical_density"]["measurement_metadata"]["content_pos"] == ["ADJ", "ADV", "NOUN", "PROPN", "VERB"]


def test_syntactic_units_remain_candidates_until_explicit_human_confirmation(tmp_path):
    analyzer = build_analyzer(settings(tmp_path))
    impl = analyzer.registry.get("spacy")
    doc = impl.nlp(FIXTURES["case_i_syntax"])
    segmenter = SyntacticUnitSegmenter()
    clauses = segmenter.segment_clause_candidates(doc)
    t_units = segmenter.segment_t_unit_candidates(doc)
    assert clauses and t_units
    assert all(item.validation_status == "automatic_candidate" for item in [*clauses, *t_units])
    assert not any(item.unit_id.startswith("validated") for item in [*clauses, *t_units])
    with pytest.raises(ValidationError):
        segmenter.validate_units(clauses[:1], {0: {"manual_decision": "accept"}})
    confirmed = segmenter.validate_units(clauses[:1], {0: {
        "manual_decision": "accept", "annotator_id": "R01",
        "annotation_guideline_version": "syntax-guideline-v0.8.0",
    }})
    assert confirmed[0].unit_id == "validated_clause"
    assert confirmed[0].validation_status == "human_confirmed"


def test_error_annotation_schema_and_accuracy_eligibility_are_conservative():
    candidate = ErrorAnnotation(
        submission_id=1, start_offset=0, end_offset=5, original_text="Error",
        error_category="grammar", correction="Errors", annotation_source="llm_candidate",
        annotation_status="confirmed", guideline_version="g-v1", confidence="medium",
    )
    human = ErrorAnnotation(
        submission_id=1, start_offset=0, end_offset=5, original_text="Error",
        error_category="grammar", correction="Errors", annotation_source="human",
        annotation_status="confirmed", annotator_id="R01", guideline_version="g-v1", confidence="high",
    )
    assert candidate.eligible_for_formal_accuracy is False
    assert human.eligible_for_formal_accuracy is True
    unavailable = accuracy_availability([candidate])
    assert unavailable["measurement_status"] == "unavailable" and unavailable["value"] is None
    assert "validated error annotations" in unavailable["reason"]


def test_time_limit_is_never_used_as_actual_duration_and_wpm_is_reproducible():
    unavailable = writing_output_rate(
        word_count=100, timed=True, active_writing_duration_seconds=None,
        timing_quality="unavailable", accepted_timing_quality=["verified", "estimated"],
    )
    assert unavailable["value"] is None and unavailable["time_limit_used"] is False
    result = writing_output_rate(
        word_count=100, timed=True, active_writing_duration_seconds=120,
        timing_quality="verified", accepted_timing_quality=["verified", "estimated"],
    )
    assert result["value"] == 50 and result["measurement_status"] == "descriptive_proxy"
    assert result["eligible_for_diagnosis"] is False


def test_configuration_enforces_v08_isolation_and_parameter_validation():
    config = ConfigurationPayload()
    assert config.calf_mtld_factor_threshold == 0.72 and config.calf_hdd_sample_size == 42
    assert config.calf_expose_to_deepseek is False and config.calf_syntactic_formal_metrics_enabled is False
    with pytest.raises(ValidationError):
        ConfigurationPayload(calf_expose_to_deepseek=True)
    with pytest.raises(ValidationError):
        ConfigurationPayload(calf_accuracy_automatic_metrics_enabled=True)


def test_migration_10_is_additive_and_logical_rollback_preserves_rows(tmp_path):
    path = tmp_path / "migration.db"
    db = Database(path); db.initialize()
    assert db._system_repository.migration_version() == LATEST_MIGRATION_VERSION and db._configuration_repository.get_active_configuration().version == "config-v0.9.0"
    with db.connect() as connection:
        assert {"analysis_units", "error_annotations"} <= {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "active_writing_duration_seconds" in {row[1] for row in connection.execute("PRAGMA table_info(essays)")}
        assert rollback(connection, 15) == 15
        assert rollback(connection, 14) == 14
        assert rollback(connection, 13) == 13
        assert rollback(connection, 12) == 12
        assert rollback(connection, 11) == 11
    assert db._configuration_repository.get_active_configuration().version == "config-v0.8.2"
    with db.connect() as connection:
        assert upgrade(connection) == LATEST_MIGRATION_VERSION
        assert db._configuration_repository.get_active_configuration().version == "config-v0.9.0"


def test_api_registry_submission_units_annotations_and_reanalysis_are_append_only(tmp_path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post("/api/v1/submissions", json=payload(
            timed=True, time_limit_minutes=30, active_writing_duration_seconds=120,
            timing_source="imported", timing_quality="verified",
        ))
        assert response.status_code == 201
        body = response.json(); submission_id = body["submission_id"]
        assert client.get("/api/v1/calf/constructs").status_code == 200
        assert client.get("/api/v1/calf/metrics/mtld").json()["eligible_for_diagnosis"] is False
        report = client.get(f"/api/v1/submissions/{submission_id}/calf").json()
        wpm = next(item for item in report["metric_results"] if item["metric_id"] == "writing_output_rate_wpm")
        assert wpm["value"] is not None and wpm["measurement_status"] == "descriptive_proxy"
        units = client.get(f"/api/v1/submissions/{submission_id}/syntactic-units").json()["syntactic_units"]
        assert units and not any(item["unit_id"] == "validated_t_unit" for item in units)
        essay_text = payload()["essay_text"]
        annotation = {
            "submission_id": submission_id, "start_offset": 0, "end_offset": 5,
            "original_text": essay_text[:5], "error_category": "test_category", "correction": "Alpha",
            "annotation_source": "human", "annotation_status": "confirmed", "annotator_id": "R01",
            "guideline_version": "error-guideline-v0.8.0", "confidence": "high",
        }
        imported = client.post(
            f"/api/v1/submissions/{submission_id}/error-annotations/import", json=[annotation]
        )
        assert imported.status_code == 201
        assert imported.json()["error_annotations"][0]["eligible_for_formal_accuracy"] is True
        before = len(client.get(f"/api/v1/submissions/{submission_id}/analyses").json()["analysis_runs"])
        reanalysis = client.post(f"/api/v1/submissions/{submission_id}/calf/reanalyze")
        assert reanalysis.status_code == 201 and reanalysis.json()["llm_called"] is False
        after = len(client.get(f"/api/v1/submissions/{submission_id}/analyses").json()["analysis_runs"])
        assert after == before + 1 and reanalysis.json()["history_overwritten"] is False


def test_case_g_limit_only_returns_unavailable_wpm_without_fake_zero(tmp_path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post("/api/v1/submissions", json=payload(**FIXTURES["case_g_limit_only"]))
        assert response.status_code == 201
        metric = next(item for item in response.json()["analysis"]["metric_results"]
                      if item["metric_id"] == "writing_output_rate_wpm")
        assert metric["value"] is None and metric["status"] == "insufficient_data"
        assert metric["measurement_metadata"]["time_limit_used"] is False


def test_case_l_longitudinal_series_do_not_bridge_metric_or_unit_versions(tmp_path):
    with TestClient(create_app(settings(tmp_path))) as client:
        for index in range(2):
            body = payload(student="CALF-L", submitted_at=datetime(
                2026, 7, 30 + index, tzinfo=timezone.utc
            ).isoformat())
            assert client.post("/api/v1/submissions", json=body).status_code == 201
        series = client.get("/api/v1/students/CALF-L/calf-trajectories").json()["series"]
        assert all(item["version_compatibility_rule"] == "exact" for item in series)
        keys = [(item["metric_id"], item["metric_version"], item["analysis_unit_version"]) for item in series]
        assert len(keys) == len(set(keys))


def test_case_m_calf_metrics_do_not_become_feedback_priorities_or_prompt_evidence(tmp_path):
    with TestClient(create_app(settings(tmp_path))) as client:
        response = client.post("/api/v1/submissions", json=payload(student="CALF-M"))
        assert response.status_code == 201
        body = response.json()
        priority_sources = {
            source for item in body["diagnosis"]["improvement_priorities"] for source in item["source_metrics"]
        }
        assert not {"mtld", "hdd", "writing_output_rate_wpm"} & priority_sources
        assert all(item["diagnosis_id"].startswith("D") for item in body["feedback_result"]["feedback"]["priority_feedback"])


def test_student_view_contains_no_calf_total_or_ability_rating():
    # v0.9.1: CALF rendering is in research_pages.py; search all UI source
    ui_root = Path(__file__).parents[1] / "app" / "ui"
    combined = "".join(f.read_text(encoding="utf-8") for f in ui_root.rglob("*.py"))
    assert "CALF total" not in combined and "writing proficiency score" not in combined
    assert "calf_student_boundary" in combined or "render_calf_classified" in combined
