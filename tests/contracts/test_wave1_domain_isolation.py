"""Wave-1 domain-attribution & isolation contract (WU7, architecture-owned).

Validates the merged Shared Core discriminator against all currently
integrated domains (D-31 invariants 1-5, D-21, D-23):

    l2      = functional/default
    academic = reserved/foundation only

Production expectation: no Academic workflow surface exists, so these
tests use controlled synthetic fixtures and source-level isolation
checks (Goal section 12) instead of inventing an Academic production
route.

Invariant classes (Goal section 12): history, Journey, revision
candidates, practice provenance, research/export scope, learner-level
aggregation.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.academic.vocabulary import EvidenceStatus as AcademicEvidenceStatus
from app.domain.attribution import (
    WORKFLOW_SURFACE_DOMAIN,
    derive_attribution,
    validate_advisory,
)
from app.domain.domain import (
    DEFAULT_DOMAIN,
    DEFAULT_LANGUAGE,
    VALID_DOMAINS,
    VALID_LANGUAGES,
    Domain,
    Language,
)
from app.domain.validation import validate_domain_scope
from app.configuration.domain_packs_loader import (
    DomainPackNotFoundError,
    domain_exists,
)

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"

# L2 learner-evidence consumers that must never touch the Academic domain.
L2_CONSUMER_TREES = (
    "analysis",
    "analyzer",
    "calf",
    "calibration",
    "diagnosis",
    "feedback",
    "journey",
    "learner",
    "practice",
    "revision",
    "research",
    "services",
)


def _imports_academic(path: Path) -> list[str]:
    """Return academic-related import strings found in a python module."""
    found: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "app.academic" or node.module.startswith("app.academic."):
                found.append(f"from {node.module} import ...")
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.academic" or alias.name.startswith("app.academic."):
                    found.append(f"import {alias.name}")
    return found


class TestClosedDomainVocabulary:
    """Domain/language vocabulary stays closed; defaults are L2."""

    def test_domain_values_exact(self) -> None:
        assert {d.value for d in Domain} == {"l2", "academic"}
        assert VALID_DOMAINS == {"l2", "academic"}

    def test_language_values_exact(self) -> None:
        assert {l.value for l in Language} == {"en"}
        assert VALID_LANGUAGES == {"en"}

    def test_defaults_are_l2_en(self) -> None:
        assert DEFAULT_DOMAIN is Domain.L2
        assert DEFAULT_LANGUAGE is Language.EN


class TestServerOwnedAttribution:
    """Client cannot authoritatively relabel domain (D-21, D-36)."""

    def test_all_current_surfaces_derive_l2(self) -> None:
        assert set(WORKFLOW_SURFACE_DOMAIN.values()) == {Domain.L2}

    def test_no_academic_workflow_surface_exists(self) -> None:
        assert "academic" not in WORKFLOW_SURFACE_DOMAIN

    def test_derived_attribution_is_l2_en(self) -> None:
        attr = derive_attribution()
        assert attr.domain is Domain.L2
        assert attr.language is Language.EN
        assert attr.rule_id == "domain-attribution-v0.1.0"

    def test_academic_advisory_rejected_against_server_derivation(self) -> None:
        derived = derive_attribution()
        assert validate_advisory("academic", None, derived).ok is False
        assert validate_advisory("l2", "en", derived).ok is True
        assert validate_advisory(None, None, derived).ok is True

    def test_invalid_advisory_values_rejected(self) -> None:
        derived = derive_attribution()
        assert validate_advisory("nonexistent", None, derived).ok is False
        assert validate_advisory(None, "fr", derived).ok is False
        assert validate_advisory("l2", "zh", derived).ok is False


class TestDomainScopeValidation:
    """Export-time domain validation contract (D-36 pre-migration seam)."""

    def test_accepts_both_registered_domains(self) -> None:
        assert validate_domain_scope("l2") is Domain.L2
        assert validate_domain_scope("academic") is Domain.ACADEMIC

    def test_rejects_unknown_values(self) -> None:
        for bad in ("nonexistent", "", "L2", "domain_b", None):
            with pytest.raises(ValueError):
                validate_domain_scope(bad)  # type: ignore[arg-type]


class TestDomainPackReservation:
    """Academic namespace is registered but explicitly not functional."""

    def test_academic_pack_absent_and_not_registered(self) -> None:
        assert domain_exists("l2") is True
        assert domain_exists("academic") is False
        with pytest.raises(DomainPackNotFoundError):
            from app.configuration.domain_packs_loader import load_pack

            load_pack("academic", "v0.1.0")


class TestL2ConsumersNeverImportAcademic:
    """D-31 invariants 1/2/3/5: no Academic entity can reach learner evidence."""

    @pytest.mark.parametrize("tree", L2_CONSUMER_TREES)
    def test_consumer_tree_has_no_academic_import(self, tree: str) -> None:
        root = APP / tree
        violations: list[str] = []
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            violations.extend(
                f"{path.relative_to(APP)}: {hit}" for hit in _imports_academic(path)
            )
        assert violations == [], "\n".join(violations)

    def test_academic_package_has_no_app_imports(self) -> None:
        """Academic entities cannot contaminate L2 history by construction."""
        violations: list[str] = []
        for path in sorted((APP / "academic").rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and node.module.startswith("app.")
                ):
                    violations.append(f"{path.name}: from {node.module}")
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("app."):
                            violations.append(f"{path.name}: import {alias.name}")
        assert violations == [], "\n".join(violations)


class TestLearnerLevelAggregationBoundary:
    """Learner-level endpoints aggregate only within a single domain (D-31)."""

    def test_learner_history_table_covered_by_ancestry_resolver(self) -> None:
        from app.domain.resolver import get_table_family

        assert get_table_family("learner_history") == "derived"
        assert get_table_family("essays") == "submission"

    def test_academic_evidence_never_maps_to_shared_evidence_axis(self) -> None:
        """Academic verification states stay a distinct axis (D-06, WU6)."""
        from app.academic.entities import EvidenceVerificationStatus

        academic_values = set(AcademicEvidenceStatus.__args__)  # type: ignore[attr-defined]
        verification = set(EvidenceVerificationStatus.__args__)  # type: ignore[attr-defined]
        assert verification != academic_values
        assert verification & academic_values == {"verified"}
