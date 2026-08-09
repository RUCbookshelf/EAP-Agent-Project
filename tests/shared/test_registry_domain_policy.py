"""Tests for registry domain policy (WU5-REGISTRY-READINESS).

Covers:
- TaskTypeRegistry namespace-scoped mechanism (D-04, D-22)
- FeedbackDimensionRegistry axes validation (D-37, RT-17)
- select_for_domain additive wrapper
- Resource-requirement selection helper (D-25)
- Two namespaces coexist without collisions
- Unknown namespace rejected
- Cross-namespace id rejection
- D-22 metadata-only semantics
- legacy_unclassified handling
"""

from __future__ import annotations

import pytest

from app.domain.domain import Domain
from app.domain.registry_policy import (
    select_calf_for_domain,
    select_for_domain,
    select_resource_requirement,
)
from app.shared.feedback_dimension_registry import (
    Availability,
    FeedbackDimensionEntry,
    FeedbackDimensionRegistry,
    LearnerExposure,
    default_feedback_dimension_registry,
)
from app.shared.task_type_registry import (
    LEGACY_UNCLASSIFIED,
    REGISTERED_NAMESPACES,
    TaskTypeEntry,
    TaskTypeRegistry,
    default_task_type_registry,
)


# --- TaskTypeRegistry tests -------------------------------------------------

class TestTaskTypeRegistryNamespaces:
    def test_registered_namespaces_contain_l2_and_academic(self):
        assert "l2" in REGISTERED_NAMESPACES
        assert "academic" in REGISTERED_NAMESPACES

    def test_two_namespaces_coexist_without_collisions(self):
        registry = TaskTypeRegistry()
        registry.register(TaskTypeEntry(
            task_type_id="essay", namespace="l2", display_name="Essay"
        ))
        registry.register(TaskTypeEntry(
            task_type_id="essay", namespace="academic", display_name="Academic Essay"
        ))
        # Both exist independently.
        assert registry.has_entry("l2", "essay")
        assert registry.has_entry("academic", "essay")
        # No collision.
        l2_entry = registry.get("l2", "essay")
        academic_entry = registry.get("academic", "essay")
        assert l2_entry.display_name == "Essay"
        assert academic_entry.display_name == "Academic Essay"

    def test_unknown_namespace_rejected(self):
        registry = TaskTypeRegistry()
        with pytest.raises(ValueError, match="Unknown namespace"):
            registry.register(TaskTypeEntry(
                task_type_id="test", namespace="nonexistent"
            ))

    def test_unknown_namespace_rejected_on_get(self):
        registry = TaskTypeRegistry()
        with pytest.raises(ValueError, match="Unknown namespace"):
            registry.get("nonexistent", "test")

    def test_unknown_namespace_rejected_on_list(self):
        registry = TaskTypeRegistry()
        with pytest.raises(ValueError, match="Unknown namespace"):
            registry.list_namespace("nonexistent")

    def test_cross_namespace_id_rejection_via_duplicate(self):
        registry = TaskTypeRegistry()
        registry.register(TaskTypeEntry(
            task_type_id="essay", namespace="l2", display_name="Essay"
        ))
        # Same id in same namespace is rejected.
        with pytest.raises(ValueError, match="already registered"):
            registry.register(TaskTypeEntry(
                task_type_id="essay", namespace="l2", display_name="Essay v2"
            ))


class TestTaskTypeRegistryMetadataOnly:
    def test_no_comparability_predicate(self):
        """D-22: registry must not store a comparability predicate."""
        entry = TaskTypeEntry(
            task_type_id="test", namespace="l2", display_name="Test"
        )
        # The dataclass has no comparability attribute.
        assert not hasattr(entry, "comparability")
        assert not hasattr(entry, "comparable_to")

    def test_metadata_field_is_open_dict(self):
        """Metadata is a dict; no predefined predicate keys are enforced."""
        entry = TaskTypeEntry(
            task_type_id="test", namespace="l2",
            metadata={"custom_key": "value"}
        )
        assert entry.metadata["custom_key"] == "value"


class TestTaskTypeRegistryLegacyUnclassified:
    def test_legacy_unclassified_is_string(self):
        assert LEGACY_UNCLASSIFIED == "legacy_unclassified"
        assert isinstance(LEGACY_UNCLASSIFIED, str)

    def test_default_registry_has_legacy_unclassified_in_l2(self):
        registry = default_task_type_registry()
        assert registry.has_entry("l2", LEGACY_UNCLASSIFIED)
        entry = registry.get("l2", LEGACY_UNCLASSIFIED)
        assert entry.namespace == "l2"
        assert entry.task_type_id == LEGACY_UNCLASSIFIED

    def test_default_registry_academic_is_empty(self):
        registry = default_task_type_registry()
        academic_entries = registry.list_namespace("academic")
        assert academic_entries == []

    def test_legacy_unclassified_metadata_manifest_reference(self):
        registry = default_task_type_registry()
        entry = registry.get("l2", LEGACY_UNCLASSIFIED)
        # D-L2-01 resolved via the qualified taxonomy contract; the sentinel
        # now references the qualified D-22 legacy mapping manifest.
        assert entry.metadata.get("role") == "legacy_sentinel"
        assert entry.metadata.get("mapping_manifest") == "l2-legacy-genre-mapping-v1.0.0"


# --- FeedbackDimensionRegistry tests ----------------------------------------

class TestFeedbackDimensionRegistryAxes:
    def test_axes_validation(self):
        """Axes must accept only defined enum values."""
        entry = FeedbackDimensionEntry(
            dimension_id="test_dim",
            availability=Availability.AVAILABLE,
            learner_exposure=LearnerExposure.STUDENT,
        )
        assert entry.availability == Availability.AVAILABLE
        assert entry.learner_exposure == LearnerExposure.STUDENT

    def test_availability_enum_values(self):
        values = {a.value for a in Availability}
        assert values == {"available", "insufficient_evidence", "not_applicable"}

    def test_learner_exposure_enum_values(self):
        values = {le.value for le in LearnerExposure}
        assert values == {"student", "research_only"}

    def test_duplicate_dimension_rejected(self):
        registry = FeedbackDimensionRegistry()
        registry.register(FeedbackDimensionEntry(
            dimension_id="dim1", availability=Availability.AVAILABLE,
            learner_exposure=LearnerExposure.STUDENT,
        ))
        with pytest.raises(ValueError, match="already registered"):
            registry.register(FeedbackDimensionEntry(
                dimension_id="dim1", availability=Availability.AVAILABLE,
                learner_exposure=LearnerExposure.STUDENT,
            ))

    def test_unknown_dimension_rejected(self):
        registry = FeedbackDimensionRegistry()
        with pytest.raises(ValueError, match="Unknown feedback dimension"):
            registry.get("nonexistent")


class TestFeedbackDimensionRegistryQueries:
    def test_list_available(self):
        registry = FeedbackDimensionRegistry()
        registry.register(FeedbackDimensionEntry(
            dimension_id="dim1", availability=Availability.AVAILABLE,
            learner_exposure=LearnerExposure.STUDENT,
        ))
        registry.register(FeedbackDimensionEntry(
            dimension_id="dim2", availability=Availability.INSUFFICIENT_EVIDENCE,
            learner_exposure=LearnerExposure.RESEARCH_ONLY,
        ))
        available = registry.list_available()
        assert len(available) == 1
        assert available[0].dimension_id == "dim1"

    def test_list_student_visible(self):
        registry = FeedbackDimensionRegistry()
        registry.register(FeedbackDimensionEntry(
            dimension_id="dim1", availability=Availability.AVAILABLE,
            learner_exposure=LearnerExposure.STUDENT,
        ))
        registry.register(FeedbackDimensionEntry(
            dimension_id="dim2", availability=Availability.AVAILABLE,
            learner_exposure=LearnerExposure.RESEARCH_ONLY,
        ))
        student_visible = registry.list_student_visible()
        assert len(student_visible) == 1
        assert student_visible[0].dimension_id == "dim1"

    def test_default_registry_has_evidenced_dimensions(self):
        registry = default_feedback_dimension_registry()
        assert registry.has_entry("cohesion")
        assert registry.has_entry("lexical_repetition")
        assert registry.has_entry("sentence_structure")
        assert registry.has_entry("lexical_diversity")
        assert registry.has_entry("accuracy")
        assert registry.has_entry("fluency")

    def test_accuracy_dimension_has_nr_note(self):
        registry = default_feedback_dimension_registry()
        accuracy = registry.get("accuracy")
        assert accuracy.availability == Availability.INSUFFICIENT_EVIDENCE
        assert "NR" in accuracy.metadata.get("note", "")


# --- select_for_domain tests ------------------------------------------------

class TestSelectForDomain:
    def test_l2_returns_all_entries(self):
        entries = [
            TaskTypeEntry(task_type_id="a", namespace="l2"),
            TaskTypeEntry(task_type_id="b", namespace="l2"),
        ]
        result = select_for_domain(entries, Domain.L2)
        assert len(result) == 2

    def test_academic_returns_empty_when_no_academic_entries(self):
        entries = [
            TaskTypeEntry(task_type_id="a", namespace="l2"),
            TaskTypeEntry(task_type_id="b", namespace="l2"),
        ]
        result = select_for_domain(entries, Domain.ACADEMIC)
        assert len(result) == 0

    def test_empty_entries_returns_empty(self):
        result = select_for_domain([], Domain.L2)
        assert result == []

    def test_domain_tagged_entries_filtered_correctly(self):
        entries = [
            {"id": "a", "domain": "l2"},
            {"id": "b", "domain": "academic"},
            {"id": "c"},  # No domain tag: l2-compatible default.
        ]
        l2_result = select_for_domain(entries, Domain.L2)
        assert len(l2_result) == 2  # "a" and "c"
        academic_result = select_for_domain(entries, Domain.ACADEMIC)
        assert len(academic_result) == 1  # "b"
        assert academic_result[0]["id"] == "b"

    def test_additive_wrapper_does_not_modify_registry(self):
        """select_for_domain must not modify the source entries."""
        original = [
            TaskTypeEntry(task_type_id="a", namespace="l2"),
        ]
        result = select_for_domain(original, Domain.ACADEMIC)
        assert result == []
        # Original unchanged.
        assert len(original) == 1

    def test_select_calf_for_domain_delegates(self):
        """select_calf_for_domain is a convenience wrapper."""
        specs = [
            {"metric_id": "m1", "domain": "l2"},
        ]
        result = select_calf_for_domain(specs, Domain.L2)
        assert len(result) == 1


# --- Resource-requirement selection tests (D-25) ----------------------------

class TestResourceRequirementSelection:
    def test_filter_by_resource_requirement(self):
        class FakeSpec:
            def __init__(self, metric_id, resource_requirements):
                self.metric_id = metric_id
                self.resource_requirements = resource_requirements

        specs = [
            FakeSpec("m1", ["spacy", "corpus"]),
            FakeSpec("m2", ["spacy"]),
            FakeSpec("m3", ["corpus"]),
            FakeSpec("m4", []),
        ]
        result = select_resource_requirement(specs, "spacy")
        assert len(result) == 2
        assert {s.metric_id for s in result} == {"m1", "m2"}

    def test_filter_by_resource_requirement_empty_result(self):
        class FakeSpec:
            def __init__(self, metric_id, resource_requirements):
                self.metric_id = metric_id
                self.resource_requirements = resource_requirements

        specs = [FakeSpec("m1", ["corpus"])]
        result = select_resource_requirement(specs, "spacy")
        assert result == []

    def test_filter_by_resource_requirement_dict_entries(self):
        specs = [
            {"metric_id": "m1", "resource_requirements": ["spacy"]},
            {"metric_id": "m2", "resource_requirements": []},
        ]
        result = select_resource_requirement(specs, "spacy")
        assert len(result) == 1
        assert result[0]["metric_id"] == "m1"

    def test_filter_by_resource_requirement_no_requirements_attr(self):
        """Entries without resource_requirements are skipped."""
        class FakeSpec:
            def __init__(self, metric_id):
                self.metric_id = metric_id

        specs = [FakeSpec("m1")]
        result = select_resource_requirement(specs, "spacy")
        assert result == []


# --- Integration: default registries ----------------------------------------

class TestDefaultRegistriesIntegration:
    def test_default_task_type_registry_is_consistent(self):
        registry = default_task_type_registry()
        # l2 has at least the legacy sentinel.
        l2_entries = registry.list_namespace("l2")
        assert len(l2_entries) >= 1
        assert any(e.task_type_id == LEGACY_UNCLASSIFIED for e in l2_entries)
        # academic is empty.
        assert registry.list_namespace("academic") == []

    def test_default_feedback_dimension_registry_is_consistent(self):
        registry = default_feedback_dimension_registry()
        assert registry.count() >= 1
        # All entries have valid axes.
        for entry in registry.list_all():
            assert isinstance(entry.availability, Availability)
            assert isinstance(entry.learner_exposure, LearnerExposure)

    def test_select_for_domain_with_default_registries(self):
        """select_for_domain works with default registry entries."""
        task_registry = default_task_type_registry()
        l2_entries = task_registry.list_namespace("l2")
        result_l2 = select_for_domain(l2_entries, Domain.L2)
        assert len(result_l2) == len(l2_entries)
        result_academic = select_for_domain(l2_entries, Domain.ACADEMIC)
        assert result_academic == []
