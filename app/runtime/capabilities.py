"""Real domain capability adapters for existing-runtime execution v1.

Each adapter is a synchronous handler bound to an existing authoritative
domain entry point (import-only; no in-place modification):

* ``l2.task_type_classifier`` — ``app.services.task_type_classifier``
  (Domain Pack v1 content; the authoritative task-type taxonomy registry and
  pack JSON stay untouched; ADR-02 federation is read-only).
* ``corpus.query_distribution`` — ``app.corpus.intelligence.CorpusIntelligence``
  (CORPUS-owned governed corpus_query boundary; learner exposure stays
  ``research_only``; raw SWECCL path/handle injection is denied, ADR-06).

Raw-source denial is fail-closed: any request key reserved for raw corpus
handles or any value carrying a raw-corpus marker is rejected as
``ineligible`` before the domain entry point is touched.
"""

from __future__ import annotations

from typing import Any

from app.corpus.errors import CorpusInvalidRequestError, CorpusUnavailableError
from app.corpus.intelligence import CorpusIntelligence
from app.runtime.errors import CapabilityDeniedError, CapabilityRequestError, CapabilityUnavailableError
from app.runtime.manifest import CapabilityManifest
from app.services.task_type_classifier import (
    canonical_display_order,
    classify_task_definition,
    load_task_types,
)

# Request keys reserved for raw corpus path/handle injection (fail-closed).
_RAW_SOURCE_KEYS = (
    "raw_corpus_path",
    "raw_corpus_handle",
    "corpus_file_path",
    "source_file",
    "file_handle",
)
# Case-folded markers that identify raw SWECCL source material in any value.
_RAW_SOURCE_MARKERS = ("sweccl", "[linguistics data]")


def _reject_raw_source(request: dict[str, Any]) -> None:
    """Deny raw SWECCL path/handle injection (ADR-06 testable denial)."""
    for key in _RAW_SOURCE_KEYS:
        if key in request:
            raise CapabilityDeniedError("raw_source_denied")
    for key, value in request.items():
        if isinstance(value, str):
            folded = value.casefold()
            if any(marker in folded for marker in _RAW_SOURCE_MARKERS):
                raise CapabilityDeniedError("raw_source_denied")
        elif isinstance(value, (list, tuple)) and value:
            for item in value:
                if isinstance(item, str) and any(
                    marker in item.casefold() for marker in _RAW_SOURCE_MARKERS
                ):
                    raise CapabilityDeniedError("raw_source_denied")


class L2TaskTypeClassifierCapability:
    """Deterministic L2 task-type classification (real Domain Pack v1 classifier)."""

    manifest = CapabilityManifest(
        identity="l2.task_type_classifier",
        version="1.0.0",
        owner="L2",
        description=(
            "Deterministic L2 task-type classification of a registered task "
            "definition (Domain Pack v1 G5 dictionaries; task-routing metadata "
            "only, never learner measurement)."
        ),
        domain_eligibility=("l2",),
        scope=("classify_task_definition", "list_task_types"),
        data_access=("none",),
        source="builtin",
        enabled=True,
        audit_required=True,
        metadata={
            "backing_source": "app.services.task_type_classifier "
            "(app/configuration/domain_packs/l2/v1.0.0 authoritative pack content)",
            "taxonomy_version": "l2-task-type-taxonomy-v1.0.0",
            "classification_scope": "task_definition_only",
            "mechanism_reference": "DeepTutor manifest-first registration "
            "(read-only reference; no code copied)",
        },
    )

    def __call__(self, request: dict[str, Any]) -> dict[str, Any]:
        operation = str(request.get("operation") or self.manifest.scope[0])
        if operation == "classify_task_definition":
            result = classify_task_definition(
                request.get("prompt"),
                declared_task_type=request.get("declared_task_type"),
            )
            return {
                "task_type": result.task_type,
                "outcome": result.outcome,
                "reason_code": result.reason_code,
                "taxonomy_version": result.taxonomy_version,
                "dictionary_version": result.dictionary_version,
                "matched_triggers": list(result.matched_triggers),
                "provenance": result.provenance,
            }
        if operation == "list_task_types":
            return {
                "display_order": canonical_display_order(),
                "types": load_task_types(),
            }
        raise CapabilityRequestError(
            f"unsupported operation {operation!r} for {self.manifest.identity}"
        )


class GovernedCorpusQueryCapability:
    """Governed corpus_query over the CORPUS-owned CorpusIntelligence boundary."""

    manifest = CapabilityManifest(
        identity="corpus.query_distribution",
        version="1.0.0",
        owner="CORPUS",
        description=(
            "Governed corpus_query for versioned reference distributions "
            "(Corpus Intelligence channel; learner exposure research_only; "
            "raw SWECCL path/handle injection denied)."
        ),
        domain_eligibility=("l2", "academic", "learner", "corpus"),
        scope=("query_distribution", "corpus_version", "distribution_availability"),
        data_access=("governed_corpus_artifacts",),
        source="builtin",
        enabled=True,
        audit_required=True,
        metadata={
            "channel": "corpus_intelligence",
            "learner_exposure": "research_only",
            "raw_source_denial": True,
            "backing_source": "app.corpus.intelligence.CorpusIntelligence "
            "(CORPUS-owned governed boundary; ADR-06)",
        },
    )

    def __init__(self, intelligence: CorpusIntelligence) -> None:
        self._intelligence = intelligence

    def __call__(self, request: dict[str, Any]) -> dict[str, Any]:
        _reject_raw_source(request)
        operation = str(request.get("operation") or self.manifest.scope[0])
        if operation == "query_distribution":
            try:
                result = self._intelligence.get_feature_distribution(
                    reference_group_id=request.get("reference_group_id"),
                    feature_id=request.get("feature_id"),
                    prompt_id=request.get("prompt_id"),
                    timed_status=request.get("timed_status"),
                    genre=request.get("genre"),
                )
            except CorpusUnavailableError as exc:
                raise CapabilityUnavailableError(
                    f"{exc} (CorpusUnavailableError)"
                ) from exc
            except CorpusInvalidRequestError:
                raise
            distribution = result.distribution
            return {
                "corpus_package_id": result.corpus_package_id,
                "manifest_hash": result.manifest_hash,
                "requested_reference_group": result.requested_reference_group,
                "resolved_reference_group": result.resolved_reference_group,
                "fallback_disclosure": result.fallback_disclosure,
                "feature_id": result.feature_id,
                "feature_set_version": result.feature_set_version,
                "n_effective": result.n_effective,
                "n_raw": result.n_raw,
                "availability": result.availability,
                "limitations": list(result.limitations),
                "learner_exposure": result.learner_exposure,
                "distribution": {
                    "reference_group_id": distribution.reference_group_id,
                    "feature_id": distribution.feature_id,
                    "feature_set_version": distribution.feature_set_version,
                    "reference_group_version": distribution.reference_group_version,
                    "distribution_version": distribution.distribution_version,
                    "corpus_package_id": distribution.corpus_package_id,
                    "manifest_hash": distribution.manifest_hash,
                    "n_effective": distribution.n_effective,
                    "n_missing": distribution.n_missing,
                    "n_raw": distribution.n_raw,
                    "mean": distribution.mean,
                    "median": distribution.median,
                    "std": distribution.std,
                    "iqr": distribution.iqr,
                    "quantiles": distribution.quantiles,
                    "minimum": distribution.minimum,
                    "maximum": distribution.maximum,
                    "availability": distribution.availability,
                    "validity_flags": list(distribution.validity_flags),
                    "duplicate_policy": distribution.duplicate_policy,
                },
            }
        if operation == "corpus_version":
            return self._intelligence.get_corpus_version()
        if operation == "distribution_availability":
            return self._intelligence.get_distribution_availability(
                group_id=request.get("reference_group_id"),
                feature_id=request.get("feature_id"),
            )
        raise CapabilityRequestError(
            f"unsupported operation {operation!r} for {self.manifest.identity}"
        )


__all__ = [
    "GovernedCorpusQueryCapability",
    "L2TaskTypeClassifierCapability",
]
