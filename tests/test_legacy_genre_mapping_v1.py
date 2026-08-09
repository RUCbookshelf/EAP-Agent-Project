"""D-22 legacy genre mapping tests (qualified manifest v1.0.0, explicit-only).

Covers the approved manifest application (M0-M4 incl. zh_CN rules), the
no-inference invariant (no substring/similarity/taxonomy-definition guessing),
normalization discipline, provenance records, and census parity (DP-4).
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.legacy_genre_mapping import (
    LEGACY_UNCLASSIFIED,
    load_legacy_genre_manifest,
    map_legacy_genre,
    normalize_genre_value,
)

_CENSUS = (
    Path(__file__).resolve().parents[1]
    / "docs" / "domain" / "census" / "L2_DP4_LEGACY_ESSAYS_CENSUS_v1.0.0.json"
)


class TestExplicitRules:
    """Approved rules map exactly and only their documented values."""

    def test_m1_argumentative_essay(self):
        result = map_legacy_genre("argumentative essay")
        assert result.mapping == "argumentative"
        assert result.rule_id == "M1"
        assert result.reason_code is None

    def test_m1_zh_yi_lun_wen(self):
        result = map_legacy_genre("议论文")
        assert result.mapping == "argumentative"
        assert result.rule_id == "M1-zh"

    def test_m2_expository_is_explicit_no_map(self):
        result = map_legacy_genre("expository essay")
        assert result.mapping == LEGACY_UNCLASSIFIED
        assert result.rule_id == "M2"
        assert result.reason_code == "no_mapping_rule"

    def test_m2_zh_shuo_ming_wen(self):
        result = map_legacy_genre("说明文")
        assert result.mapping == LEGACY_UNCLASSIFIED
        assert result.rule_id == "M2-zh"

    def test_m3_narrative_is_explicit_no_map(self):
        result = map_legacy_genre("narrative essay")
        assert result.mapping == LEGACY_UNCLASSIFIED
        assert result.rule_id == "M3"

    def test_m3_zh_ji_xu_wen(self):
        result = map_legacy_genre("记叙文")
        assert result.mapping == LEGACY_UNCLASSIFIED
        assert result.rule_id == "M3-zh"

    def test_m4_missing_value(self):
        for value in ("", "   ", None):
            result = map_legacy_genre(value)
            assert result.mapping == LEGACY_UNCLASSIFIED
            assert result.rule_id == "M4"
            assert result.reason_code == "missing_genre"

    def test_m0_default_for_unmapped_values(self):
        result = map_legacy_genre("fantasy essay")
        assert result.mapping == LEGACY_UNCLASSIFIED
        assert result.rule_id == "M0"
        assert result.reason_code == "no_mapping_rule"


class TestNoInference:
    """Constraint 4 - no substring, similarity, or definition inference."""

    def test_substring_never_matches(self):
        # "argument" appears as a substring; no exact rule exists for this
        # value. The legacy substring inference would have said "argument";
        # the explicit manifest must say legacy_unclassified.
        result = map_legacy_genre("argumentative writing task")
        assert result.mapping == LEGACY_UNCLASSIFIED
        assert result.rule_id == "M0"

    def test_near_miss_never_matches(self):
        result = map_legacy_genre("argumentative essays")
        assert result.mapping == LEGACY_UNCLASSIFIED
        assert result.rule_id == "M0"

    def test_case_and_whitespace_normalization_only(self):
        result = map_legacy_genre("  Argumentative   ESSAY  ")
        assert result.mapping == "argumentative"
        assert result.rule_id == "M1"

    def test_zh_whitespace_normalization(self):
        result = map_legacy_genre("  议论文  ")
        assert result.mapping == "argumentative"
        assert result.rule_id == "M1-zh"

    def test_general_eap_never_assigned_from_genre(self):
        assert map_legacy_genre("academic essay").mapping == LEGACY_UNCLASSIFIED


class TestDeterminismAndProvenance:
    """Closed deterministic procedure with write-time provenance records."""

    def test_same_input_same_output(self):
        results = [map_legacy_genre("argumentative essay") for _ in range(5)]
        assert all(item == results[0] for item in results)

    def test_provenance_fields(self):
        result = map_legacy_genre("argumentative essay")
        assert result.manifest_id == "l2-legacy-genre-mapping-v1.0.0"
        assert result.rule_version == "v1.0.0"
        assert result.taxonomy_version == "l2-task-type-taxonomy-v1.0.0"
        assert result.approvals == ("RD-D22", "DP-4")
        assert result.rationale

    def test_normalize_genre_value_discipline(self):
        assert normalize_genre_value("  Argumentative \t ESSAY ") == "argumentative essay"
        assert normalize_genre_value(None) == ""


class TestCensusParity:
    """DP-4 governed-snapshot parity: the manifest reproduces the census."""

    def test_census_distribution_reproduced(self):
        census = json.loads(_CENSUS.read_text(encoding="utf-8"))
        distribution = census["legacy_source_distribution"]["by_genre_option"]
        total = 0
        by_rule: dict[str, int] = {}
        for option, count in distribution.items():
            genre = {
                "option_argumentative_en": "argumentative essay",
                "option_argumentative_zh": "议论文",
            }[option]
            result = map_legacy_genre(genre)
            by_rule[result.rule_id] = by_rule.get(result.rule_id, 0) + count
            total += count
        assert total == census["census"]["total_rows"] == 29
        assert by_rule == {"M1": 26, "M1-zh": 3}
        assert census["census"]["resulting_task_type_rows"] == {"argumentative": 29}

    def test_census_qa_clean(self):
        census = json.loads(_CENSUS.read_text(encoding="utf-8"))
        assert "PASS" in census["census"]["rule_value_disjointness"]
        assert census["census"]["mapping_conflicts"] == 0


class TestManifestContent:
    """Pack-embedded manifest matches the qualified authority."""

    def test_manifest_identity_and_status(self):
        manifest = load_legacy_genre_manifest()
        assert manifest["manifest_id"] == "l2-legacy-genre-mapping-v1.0.0"
        assert manifest["status"] == "QUALIFIED"
        assert manifest["rule_version"] == "v1.0.0"
        assert {rule["rule_id"] for rule in manifest["rules"]} == {
            "M0", "M1", "M1-zh", "M2", "M2-zh", "M3", "M3-zh", "M4",
        }

    def test_approved_rules_have_disjoint_values(self):
        manifest = load_legacy_genre_manifest()
        values = [
            rule["normalized_value"]
            for rule in manifest["rules"] if rule["rule_id"] != "M0"
        ]
        assert len(values) == len(set(values))

    def test_approvals_recorded(self):
        manifest = load_legacy_genre_manifest()
        decisions = {item["decision_id"] for item in manifest["approvals"]}
        assert decisions == {"RD-D22", "DP-4"}
