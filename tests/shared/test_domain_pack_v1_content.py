"""L2 Domain Pack v1 content tests (D-26 registry-content layout).

Validates the versioned pack content under ``app/configuration/domain_packs/
l2/v1.0.0``: five-type manifest, D-L2-09 label pairs with locale parity,
the G5 trigger dictionaries, the G5 conflict-pair table, the qualified D-22
legacy mapping manifest, and the TaskTypeRegistry content parity.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.configuration.domain_packs_loader import load_pack
from app.services.task_type_classifier import (
    canonical_display_order,
    load_conflict_pairs,
    load_task_types,
    load_trigger_dictionaries,
)
from app.services.legacy_genre_mapping import load_legacy_genre_manifest
from app.shared.task_type_registry import LEGACY_UNCLASSIFIED, default_task_type_registry

_PACK_ROOT = (
    Path(__file__).resolve().parents[2]
    / "app" / "configuration" / "domain_packs" / "l2" / "v1.0.0"
)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

FIVE_TYPES = [
    "opinion", "argumentative", "discussion", "problem_solution", "general_eap",
]


class TestPackManifest:
    def test_v1_pack_loads(self):
        manifest = load_pack("l2", "v1.0.0")
        assert manifest["domain"] == "l2"
        assert manifest["version"] == "v1.0.0"
        assert manifest["pack_id"] == "l2-core-v1.0.0"

    def test_supported_task_types_are_the_five(self):
        manifest = load_pack("l2", "v1.0.0")
        assert manifest["supported_task_types"] == FIVE_TYPES

    def test_metadata_only_and_no_dimensions(self):
        manifest = load_pack("l2", "v1.0.0")
        assert manifest["dimensions"] == []
        assert manifest["resource_requirements"] == []
        assert manifest["taxonomy_version"] == "l2-task-type-taxonomy-v1.0.0"
        assert "Metadata-only" in manifest["content_status"]["note"]

    def test_discourse_organization_excluded(self):
        manifest = load_pack("l2", "v1.0.0")
        assert "discourse_organization" not in manifest["supported_task_types"]
        assert "EXCLUDED" in manifest["content_status"]["dimensions"]

    def test_v010_pack_remains_immutable_baseline(self):
        # Old snapshots are never rewritten (contract Constraint 7.4/7.5).
        manifest = load_pack("l2", "v0.1.0")
        assert manifest["supported_task_types"] == []


class TestTaskTypesContent:
    def test_display_order_is_canonical(self):
        content = load_task_types()
        assert content["display_order"] == FIVE_TYPES
        assert canonical_display_order() == FIVE_TYPES

    def test_en_labels_match_contract(self):
        content = load_task_types()
        assert content["types"]["opinion"]["display_name_en"] == "Opinion Essay"
        assert content["types"]["argumentative"]["display_name_en"] == "Argumentative Essay"
        assert content["types"]["discussion"]["display_name_en"] == "Discussion Essay"
        assert content["types"]["problem_solution"]["display_name_en"] == "Problem-Solution Essay"
        assert content["types"]["general_eap"]["display_name_en"] == "General EAP"

    def test_zh_labels_match_d_l2_09(self):
        content = load_task_types()
        expected = {
            "opinion": "观点类作文",
            "argumentative": "议论文",
            "discussion": "讨论类作文",
            "problem_solution": "问题解决类作文",
            "general_eap": "通用学术写作",
        }
        for task_type_id, label in expected.items():
            assert content["types"][task_type_id]["display_name_zh_CN"] == label

    def test_locale_keys_resolve_and_match_pack_labels(self):
        content = load_task_types()
        en = json.loads((_PROJECT_ROOT / "locales" / "en.json").read_text(encoding="utf-8"))
        zh = json.loads((_PROJECT_ROOT / "locales" / "zh_CN.json").read_text(encoding="utf-8"))
        for task_type_id in FIVE_TYPES:
            key = content["types"][task_type_id]["locale_key"]
            assert key in en and key in zh
            assert en[key] == content["types"][task_type_id]["display_name_en"]
            assert zh[key] == content["types"][task_type_id]["display_name_zh_CN"]


class TestTriggerDictionaries:
    def test_identity_fields(self):
        content = load_trigger_dictionaries()
        assert content["content_id"] == "l2-trigger-dictionaries-v1.0.0"
        assert content["taxonomy_version"] == "l2-task-type-taxonomy-v1.0.0"
        assert content["normalization"]["nfc"] is True
        assert content["normalization"]["casefold"] is True

    def test_every_type_has_groups_with_both_locales(self):
        content = load_trigger_dictionaries()
        for task_type_id in FIVE_TYPES:
            spec = content["types"][task_type_id]
            assert spec["full_match"]
            for group in spec["groups"].values():
                assert group["en"], f"{task_type_id} missing en phrases"
                assert group["zh_CN"], f"{task_type_id} missing zh_CN phrases"

    def test_zh_phrases_are_multi_character(self):
        content = load_trigger_dictionaries()
        for task_type_id in FIVE_TYPES:
            for group in content["types"][task_type_id]["groups"].values():
                for phrase in group["zh_CN"]:
                    assert len(phrase) >= 2, f"single-char zh phrase: {phrase!r}"

    def test_no_duplicate_phrases_within_groups(self):
        content = load_trigger_dictionaries()
        for task_type_id in FIVE_TYPES:
            for group in content["types"][task_type_id]["groups"].values():
                for locale in ("en", "zh_CN"):
                    phrases = group[locale]
                    assert len(phrases) == len(set(phrases))

    def test_specific_types_are_the_four(self):
        content = load_trigger_dictionaries()
        assert set(content["types"]) == set(FIVE_TYPES)


class TestConflictPairs:
    def test_only_canonical_pair_enumerated(self):
        content = load_conflict_pairs()
        assert len(content["pairs"]) == 1
        pair = content["pairs"][0]["pair"]
        assert set(pair) == {"argumentative", "discussion"}
        assert content["pairs"][0]["example"] == (
            "Discuss both views and take a position, arguing with evidence."
        )

    def test_pairs_reference_five_types_only(self):
        content = load_conflict_pairs()
        for pair_spec in content["pairs"]:
            for task_type_id in pair_spec["pair"]:
                assert task_type_id in FIVE_TYPES

    def test_rule_documents_chain_and_conflict_outcome(self):
        content = load_conflict_pairs()
        assert "ambiguous_precedence_conflict" in content["rule"]
        assert "problem_solution > argumentative > discussion > opinion > general_eap" in content["rule"]


class TestLegacyManifestContent:
    def test_qualified_manifest_embedded(self):
        manifest = load_legacy_genre_manifest()
        assert manifest["manifest_id"] == "l2-legacy-genre-mapping-v1.0.0"
        assert manifest["status"] == "QUALIFIED"
        assert manifest["rule_version"] == "v1.0.0"

    def test_approved_mappings(self):
        manifest = load_legacy_genre_manifest()
        by_id = {rule["rule_id"]: rule for rule in manifest["rules"]}
        assert by_id["M1"]["mapping"] == "argumentative"
        assert by_id["M1-zh"]["mapping"] == "argumentative"
        for rule_id in ("M0", "M2", "M2-zh", "M3", "M3-zh", "M4"):
            assert by_id[rule_id]["mapping"] == LEGACY_UNCLASSIFIED


class TestRegistryContentParity:
    def test_default_registry_registers_five_types_plus_sentinel(self):
        registry = default_task_type_registry()
        l2_ids = {entry.task_type_id for entry in registry.list_namespace("l2")}
        assert l2_ids == set(FIVE_TYPES) | {LEGACY_UNCLASSIFIED}

    def test_registry_display_names_match_pack(self):
        registry = default_task_type_registry()
        content = load_task_types()
        for task_type_id in FIVE_TYPES:
            entry = registry.get("l2", task_type_id)
            assert entry.display_name == content["types"][task_type_id]["display_name_en"]

    def test_registry_display_order_metadata(self):
        registry = default_task_type_registry()
        order = {
            registry.get("l2", task_type_id).metadata["display_order"]: task_type_id
            for task_type_id in FIVE_TYPES
        }
        assert [order[key] for key in sorted(order)] == FIVE_TYPES

    def test_metadata_only_invariants(self):
        registry = default_task_type_registry()
        for task_type_id in FIVE_TYPES:
            entry = registry.get("l2", task_type_id)
            assert entry.metadata["metadata_only"] is True
            assert not hasattr(entry, "comparability")

    def test_legacy_sentinel_references_qualified_manifest(self):
        registry = default_task_type_registry()
        sentinel = registry.get("l2", LEGACY_UNCLASSIFIED)
        assert sentinel.metadata["mapping_manifest"] == "l2-legacy-genre-mapping-v1.0.0"
        assert sentinel.metadata["role"] == "legacy_sentinel"
