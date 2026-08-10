"""Wave-2 Goal E — modality-aware corpus product routing.

L2 Writing requests route to written corpus resources (WECCL20) by default.
Corpus eligibility is a five-factor gate: domain relevance, modality
relevance, exposure policy, artifact availability, and existing
reference-group eligibility. A processed resource does not become eligible
merely because it exists.

SECCL20 is classified spoken + secondary/research_only and is excluded from
default L2 Writing diagnostic/reference routing; all existing SECCL artifacts
and their research_only exposure are preserved unchanged. SECCL may only be
selected by an explicit spoken-modality opt-in (``allow_secondary=True``)
under research_only exposure and a spoken-language domain.

WECCL written reference matching prefers, where metadata permit: same prompt
-> same task type + relevant context -> same task type -> similar written
context/genre -> broader Chinese university learner writing distribution.
Reference distributions remain descriptive context, never proficiency ground
truth. No D3/D8/D12 exposure widening is performed by this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.corpus.distributions import ReferenceDistribution
from app.corpus.errors import (
    CorpusInvalidRequestError,
    CorpusResourceError,
)
from app.corpus.features import FEATURE_DEFINITIONS, FEATURE_SET_VERSION
from app.corpus.groups import MIN_N, REFERENCE_GROUP_VERSION, ReferenceGroupIndex
from app.corpus.intelligence import CorpusIntelligence
from app.corpus.resource import get_corpus_resource
from app.corpus.seccl import (
    SECCL_REFERENCE_GROUP_VERSION,
    SECCL_PACKAGE_ID,
    SecclReferenceGroupIndex,
    load_seccl_manifest,
)
from app.corpus.tasksignature import TaskSignature

MODALITY_WRITTEN = "written"
MODALITY_SPOKEN = "spoken"

ROLE_PRIMARY = "primary"
ROLE_SECONDARY = "secondary"

WECCL_PACKAGE_ID = "sweccl2-weccl20-v0.1.0"

L2_WRITING_DOMAIN = "l2_writing"
L2_SPEAKING_DOMAIN = "l2_speaking"

# Package-level all-written candidate for the broadest fallback level. It is
# a routing-level descriptor, not a governed index group: membership is
# computed from the authoritative index manifest and duplicate policy, and a
# governed distribution artifact must still exist for it to be eligible.
ALL_WRITTEN_GROUP_ID = "RG-all"

ROUTING_PROCESSING_VERSION = "l2-writing-router-v0.1.0"
ROUTING_RESULT_ARTIFACT_VERSION = "l2-writing-routing-result-v0.1.0"
ARTIFACT_CLASS = "NON-RECONSTRUCTIVE AGGREGATE ARTIFACT"

# Only research_only is allowed in this Goal. diagnostic_only/displayable
# require D3/D8/D12 qualification (O2 gates); this Goal never widens exposure.
ALLOWED_EXPOSURES = ("research_only",)
_KNOWN_EXPOSURES = ("research_only", "diagnostic_only", "displayable", "hidden", "unavailable")

CHAIN_LEVELS = (
    "same_prompt",
    "task_type_context",
    "task_type",
    "similar_written_context",
    "broader_distribution",
)

ROUTING_REPO_ROOT = Path(r"A:\EAP Agent Project\writing-feedback-mvp")
ROUTING_DATA = ROUTING_REPO_ROOT / "docs" / "corpus-intelligence" / "l2" / "data"
SECCL_MANIFEST_PATH = (
    ROUTING_REPO_ROOT / "docs" / "corpus-readiness" / "sweccl2" / "data" / "seccl_manifest.csv"
)


@dataclass(frozen=True)
class ResourceClassification:
    """Explicit, governed classification of one corpus resource."""

    corpus_package_id: str
    modality: str
    role: str
    secondary: bool
    exposure_class: str
    learner_exposure: str
    allowed_exposures: tuple[str, ...]
    domains: tuple[str, ...]
    rationale: str


_CLASSIFICATIONS: dict[str, ResourceClassification] = {
    WECCL_PACKAGE_ID: ResourceClassification(
        corpus_package_id=WECCL_PACKAGE_ID,
        modality=MODALITY_WRITTEN,
        role=ROLE_PRIMARY,
        secondary=False,
        exposure_class="research_only",
        learner_exposure="research_only",
        allowed_exposures=ALLOWED_EXPOSURES,
        domains=(L2_WRITING_DOMAIN,),
        rationale=(
            "WECCL20 written essays are the primary written reference corpus "
            "for L2 Writing routing."
        ),
    ),
    SECCL_PACKAGE_ID: ResourceClassification(
        corpus_package_id=SECCL_PACKAGE_ID,
        modality=MODALITY_SPOKEN,
        role=ROLE_SECONDARY,
        secondary=True,
        exposure_class="research_only",
        learner_exposure="research_only",
        allowed_exposures=ALLOWED_EXPOSURES,
        domains=(L2_SPEAKING_DOMAIN,),
        rationale=(
            "SECCL20 is a spoken transcript corpus (TEM4); secondary for "
            "L2 Writing and research_only. All existing SECCL artifacts and "
            "their research_only exposure are preserved unchanged."
        ),
    ),
}


def classify_resource(package_id: str) -> ResourceClassification:
    """Return the explicit modality/role/exposure classification of a resource."""
    classification = _CLASSIFICATIONS.get(package_id)
    if classification is None:
        raise CorpusInvalidRequestError(f"unknown corpus resource: {package_id}")
    return classification


@dataclass(frozen=True)
class ResourceEligibility:
    """Five-factor eligibility record for one routing candidate."""

    corpus_package_id: str
    eligible: bool
    domain_relevance: bool
    modality_relevance: bool
    exposure_policy: bool
    artifact_availability: bool
    reference_group_eligibility: bool
    reference_group_availability: str | None
    reasons: tuple[str, ...]


def assess_eligibility(
    classification: ResourceClassification,
    *,
    domain: str = L2_WRITING_DOMAIN,
    requested_modality: str = MODALITY_WRITTEN,
    requested_exposure: str = "research_only",
    reference_group_availability: str = "unavailable",
    n_effective: int = 0,
    min_n: int = MIN_N,
    artifact_available: bool = False,
) -> ResourceEligibility:
    """Evaluate the five eligibility factors for one candidate."""
    domain_relevance = domain in classification.domains
    modality_relevance = classification.modality == requested_modality
    exposure_policy = requested_exposure in classification.allowed_exposures
    reference_group_eligibility = (
        reference_group_availability in ("available", "limited")
        and n_effective >= min_n
    )
    reasons: list[str] = []
    if not domain_relevance:
        reasons.append(
            f"domain {domain!r} not in classification domains {classification.domains!r}"
        )
    if not modality_relevance:
        reasons.append(
            f"modality {classification.modality!r} does not match requested "
            f"modality {requested_modality!r}"
        )
    if not exposure_policy:
        reasons.append(
            f"requested exposure {requested_exposure!r} not allowed "
            f"(allowed: {classification.allowed_exposures!r}; no D3/D8/D12 widening)"
        )
    if not reference_group_eligibility:
        reasons.append(
            f"reference group unavailable (availability "
            f"{reference_group_availability!r}, n_effective {n_effective} < min_n {min_n})"
        )
    if not artifact_available:
        reasons.append("no governed distribution artifact for (group, feature)")
    return ResourceEligibility(
        corpus_package_id=classification.corpus_package_id,
        eligible=all(
            (domain_relevance, modality_relevance, exposure_policy,
             reference_group_eligibility, artifact_available)
        ),
        domain_relevance=domain_relevance,
        modality_relevance=modality_relevance,
        exposure_policy=exposure_policy,
        artifact_availability=artifact_available,
        reference_group_eligibility=reference_group_eligibility,
        reference_group_availability=reference_group_availability,
        reasons=tuple(reasons),
    )


@dataclass(frozen=True)
class RoutingResource:
    """Minimal provenance view of one registered corpus resource."""

    corpus_package_id: str
    manifest_hash: str
    provenance: dict = field(default_factory=dict)


def default_resource_registry(data_dir: Path = ROUTING_DATA) -> dict[str, RoutingResource]:
    """Build the routing registry from governed artifacts only."""
    weccl = get_corpus_resource()
    seccl_descriptor = data_dir / "seccl" / "seccl_package_descriptor.json"
    if not seccl_descriptor.is_file():
        raise CorpusResourceError(f"seccl package descriptor missing: {seccl_descriptor}")
    try:
        record = json.loads(seccl_descriptor.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise CorpusResourceError(f"seccl package descriptor unreadable: {exc}") from exc
    if record.get("corpus_package_id") != SECCL_PACKAGE_ID:
        raise CorpusResourceError("seccl package descriptor identity mismatch")
    return {
        WECCL_PACKAGE_ID: RoutingResource(
            corpus_package_id=weccl.corpus_package_id,
            manifest_hash=weccl.manifest_hash,
            provenance=weccl.provenance,
        ),
        SECCL_PACKAGE_ID: RoutingResource(
            corpus_package_id=SECCL_PACKAGE_ID,
            manifest_hash=str(record.get("manifest_hash", "")),
            provenance={
                "corpus_package_id": SECCL_PACKAGE_ID,
                "source_corpus": record.get("source_corpus", ""),
                "manifest_hash": record.get("manifest_hash", ""),
                "generator": record.get("generator", ""),
                "generated_at": record.get("generated_at", ""),
            },
        ),
    }


@dataclass(frozen=True)
class RoutingResult:
    """One versioned modality-aware routing outcome with full disclosure."""

    artifact_version: str
    processing_version: str
    routed: bool
    request: dict
    resolved_resource_id: str | None
    resolved_reference_group_id: str | None
    resolved_reference_group: dict | None
    resolved_level: str | None
    fallback_chain: tuple[str, ...]
    fallback_disclosure: str | None
    eligibility: ResourceEligibility | None
    reference_group_version: str
    feature_set_version: str
    corpus_package_id: str
    manifest_hash: str
    unmatched_reason: str | None
    learner_exposure: str = "research_only"
    artifact_class: str = ARTIFACT_CLASS
    descriptive_only: bool = True
    secondary: bool = False

    @property
    def provenance(self) -> dict:
        return {
            "artifact_version": self.artifact_version,
            "processing_version": self.processing_version,
            "corpus_package_id": self.corpus_package_id,
            "manifest_hash": self.manifest_hash,
            "reference_group_version": self.reference_group_version,
            "feature_set_version": self.feature_set_version,
            "learner_exposure": self.learner_exposure,
            "artifact_class": self.artifact_class,
            "descriptive_only": self.descriptive_only,
        }


class L2WritingRouter:
    """Modality-aware router for L2 Writing corpus requests.

    Written requests default to the primary written resource (WECCL20) and
    resolve a reference group through the WECCL fallback chain. Spoken
    requests are refused unless ``allow_secondary=True``, and even then only
    under research_only exposure with a spoken-language domain.
    """

    def __init__(
        self,
        *,
        intelligence: CorpusIntelligence | None = None,
        index: ReferenceGroupIndex | None = None,
        distributions: dict[tuple[str, str], ReferenceDistribution] | None = None,
        seccl_index: SecclReferenceGroupIndex | None = None,
        resources: dict[str, RoutingResource] | None = None,
        min_n: int = MIN_N,
        feature_set_version: str = FEATURE_SET_VERSION,
        reference_group_version: str = REFERENCE_GROUP_VERSION,
        seccl_reference_group_version: str = SECCL_REFERENCE_GROUP_VERSION,
    ) -> None:
        if intelligence is None and index is None and distributions is None:
            intelligence = CorpusIntelligence()
        self.intelligence = intelligence
        self.index = index if index is not None else (
            intelligence.index if intelligence is not None else ReferenceGroupIndex()
        )
        self.distributions = distributions if distributions is not None else (
            intelligence.distributions if intelligence is not None else {}
        )
        self.seccl_index = seccl_index if seccl_index is not None else (
            SecclReferenceGroupIndex(manifest=load_seccl_manifest(SECCL_MANIFEST_PATH))
        )
        self.resources = resources if resources is not None else default_resource_registry()
        self.min_n = min_n
        self.feature_set_version = feature_set_version
        self.reference_group_version = reference_group_version
        self.seccl_reference_group_version = seccl_reference_group_version

    def written_chain_candidates(self, signature: TaskSignature) -> tuple[tuple[str, str | None], ...]:
        """Deterministic WECCL fallback chain (level id, candidate group id)."""
        genre = signature.derived_genre()
        return (
            ("same_prompt", f"RG-prompt_id={signature.prompt_id}" if signature.prompt_id else None),
            (
                "task_type_context",
                f"RG-genre={genre}-timed_status={signature.timed_status}"
                if genre and signature.timed_status else None,
            ),
            ("task_type", f"RG-genre={genre}" if genre else None),
            (
                "similar_written_context",
                f"RG-timed_status={signature.timed_status}" if signature.timed_status else None,
            ),
            ("broader_distribution", ALL_WRITTEN_GROUP_ID),
        )

    def _all_written_group(self) -> tuple[str, int] | None:
        """Package-level all-written descriptor from the index manifest.

        Membership follows the same duplicate policy as the index
        (lexicographically smallest document per duplicate group is canonical).
        """
        manifest = self.index.manifest
        if not manifest:
            return None
        duplicates = self.index.duplicates
        canonical: dict[str, str] = {}
        for doc, group in duplicates.items():
            if group not in canonical or doc < canonical[group]:
                canonical[group] = doc
        n_effective = 0
        for row in manifest:
            doc = row["document_id"]
            group = duplicates.get(doc)
            if group is None or doc == canonical[group]:
                n_effective += 1
        availability = "available" if n_effective >= self.min_n else "unavailable"
        return availability, n_effective

    def _artifact_available(self, group_id: str, feature_id: str) -> bool:
        dist = self.distributions.get((group_id, feature_id))
        return dist is not None and dist.availability != "unavailable"

    def _resource_for(self, package_id: str) -> RoutingResource:
        resource = self.resources.get(package_id)
        if resource is not None:
            return resource
        return RoutingResource(corpus_package_id=package_id, manifest_hash="")

    def _unrouted(
        self,
        *,
        request: dict,
        package_id: str,
        reason: str,
        chain: tuple[str, ...],
        eligibility: ResourceEligibility | None,
        reference_group_version: str,
    ) -> RoutingResult:
        resource = self._resource_for(package_id)
        return RoutingResult(
            artifact_version=ROUTING_RESULT_ARTIFACT_VERSION,
            processing_version=ROUTING_PROCESSING_VERSION,
            routed=False,
            request=request,
            resolved_resource_id=None,
            resolved_reference_group_id=None,
            resolved_reference_group=None,
            resolved_level=None,
            fallback_chain=chain,
            fallback_disclosure=None,
            eligibility=eligibility,
            reference_group_version=reference_group_version,
            feature_set_version=self.feature_set_version,
            corpus_package_id=resource.corpus_package_id,
            manifest_hash=resource.manifest_hash,
            unmatched_reason=reason,
        )

    def route(
        self,
        signature: TaskSignature,
        *,
        feature_id: str = "text_length_tokens",
        domain: str = L2_WRITING_DOMAIN,
        requested_modality: str = MODALITY_WRITTEN,
        requested_exposure: str = "research_only",
        allow_secondary: bool = False,
    ) -> RoutingResult:
        """Route one L2 Writing task request to an eligible corpus resource."""
        if requested_modality not in (MODALITY_WRITTEN, MODALITY_SPOKEN):
            raise CorpusInvalidRequestError(
                f"invalid requested_modality {requested_modality!r} "
                f"(expected written/spoken)"
            )
        if requested_exposure not in _KNOWN_EXPOSURES:
            raise CorpusInvalidRequestError(
                f"invalid requested_exposure {requested_exposure!r}"
            )
        if feature_id not in FEATURE_DEFINITIONS:
            raise CorpusInvalidRequestError(f"unknown feature: {feature_id}")
        request = {
            "domain": domain,
            "requested_modality": requested_modality,
            "requested_exposure": requested_exposure,
            "allow_secondary": allow_secondary,
            "feature_id": feature_id,
            "task": signature.as_dict(),
        }
        if requested_modality == MODALITY_WRITTEN:
            return self._route_written(
                signature, feature_id=feature_id, domain=domain,
                requested_exposure=requested_exposure, request=request,
            )
        return self._route_spoken(
            feature_id=feature_id, domain=domain,
            requested_exposure=requested_exposure, request=request,
            allow_secondary=allow_secondary,
        )

    def _route_written(
        self,
        signature: TaskSignature,
        *,
        feature_id: str,
        domain: str,
        requested_exposure: str,
        request: dict,
    ) -> RoutingResult:
        classification = classify_resource(WECCL_PACKAGE_ID)
        if signature.prompt_id is None and signature.genre is None:
            return self._unrouted(
                request=request,
                package_id=WECCL_PACKAGE_ID,
                reason="task signature incomplete: neither prompt_id nor genre supplied",
                chain=tuple(level for level, _ in self.written_chain_candidates(signature)),
                eligibility=None,
                reference_group_version=self.reference_group_version,
            )
        chain = self.written_chain_candidates(signature)
        first_eligibility: ResourceEligibility | None = None
        level_reasons: list[str] = []
        for level_id, group_id in chain:
            if group_id is None:
                continue
            if level_id == "broader_distribution":
                all_group = self._all_written_group()
                if all_group is None:
                    level_reasons.append(
                        f"{level_id} unavailable (no governed all-written membership)"
                    )
                    continue
                group_availability, n_effective = all_group
                selection_criteria: dict = {"package_level": "all_written"}
                group_version = self.reference_group_version
            else:
                if group_id not in self.index.groups:
                    level_reasons.append(
                        f"{level_id} unavailable (group {group_id!r} not in "
                        "governed reference-group index)"
                    )
                    continue
                group = self.index.get(group_id)
                group_availability = group.availability
                n_effective = group.n_effective
                selection_criteria = dict(group.selection_criteria)
                group_version = group.version
            artifact_available = self._artifact_available(group_id, feature_id)
            eligibility = assess_eligibility(
                classification,
                domain=domain,
                requested_modality=MODALITY_WRITTEN,
                requested_exposure=requested_exposure,
                reference_group_availability=group_availability,
                n_effective=n_effective,
                min_n=self.min_n,
                artifact_available=artifact_available,
            )
            if first_eligibility is None:
                first_eligibility = eligibility
            if eligibility.eligible:
                resource = self._resource_for(WECCL_PACKAGE_ID)
                return RoutingResult(
                    artifact_version=ROUTING_RESULT_ARTIFACT_VERSION,
                    processing_version=ROUTING_PROCESSING_VERSION,
                    routed=True,
                    request=request,
                    resolved_resource_id=WECCL_PACKAGE_ID,
                    resolved_reference_group_id=group_id,
                    resolved_reference_group=selection_criteria,
                    resolved_level=level_id,
                    fallback_chain=tuple(level for level, _ in chain),
                    fallback_disclosure=None if level_id == "same_prompt" else "same_prompt",
                    eligibility=eligibility,
                    reference_group_version=group_version,
                    feature_set_version=self.feature_set_version,
                    corpus_package_id=resource.corpus_package_id,
                    manifest_hash=resource.manifest_hash,
                    unmatched_reason=None,
                    learner_exposure="research_only",
                    secondary=False,
                )
            level_reasons.append(f"{level_id} unavailable ({'; '.join(eligibility.reasons)})")
        reason = "no eligible written reference group: " + "; ".join(level_reasons)
        return self._unrouted(
            request=request,
            package_id=WECCL_PACKAGE_ID,
            reason=reason,
            chain=tuple(level for level, _ in chain),
            eligibility=first_eligibility,
            reference_group_version=self.reference_group_version,
        )

    def _route_spoken(
        self,
        *,
        feature_id: str,
        domain: str,
        requested_exposure: str,
        request: dict,
        allow_secondary: bool,
    ) -> RoutingResult:
        classification = classify_resource(SECCL_PACKAGE_ID)
        if not allow_secondary:
            return self._unrouted(
                request=request,
                package_id=SECCL_PACKAGE_ID,
                reason=(
                    "SECCL20 is classified spoken + secondary/research_only; "
                    "explicit allow_secondary=True is required for spoken-modality routing"
                ),
                chain=("spoken_exam",),
                eligibility=None,
                reference_group_version=self.seccl_reference_group_version,
            )
        group_id = "RG-seccl-exam=TEM4"
        if self.seccl_index is None or group_id not in self.seccl_index.groups:
            return self._unrouted(
                request=request,
                package_id=SECCL_PACKAGE_ID,
                reason="no governed SECCL reference-group index",
                chain=("spoken_exam",),
                eligibility=None,
                reference_group_version=self.seccl_reference_group_version,
            )
        group = self.seccl_index.get(group_id)
        artifact_available = self._artifact_available(group_id, feature_id)
        eligibility = assess_eligibility(
            classification,
            domain=domain,
            requested_modality=MODALITY_SPOKEN,
            requested_exposure=requested_exposure,
            reference_group_availability=group.availability,
            n_effective=group.n_effective,
            min_n=self.min_n,
            artifact_available=artifact_available,
        )
        if not eligibility.eligible:
            return self._unrouted(
                request=request,
                package_id=SECCL_PACKAGE_ID,
                reason="spoken reference unavailable: " + "; ".join(eligibility.reasons),
                chain=("spoken_exam",),
                eligibility=eligibility,
                reference_group_version=self.seccl_reference_group_version,
            )
        resource = self._resource_for(SECCL_PACKAGE_ID)
        return RoutingResult(
            artifact_version=ROUTING_RESULT_ARTIFACT_VERSION,
            processing_version=ROUTING_PROCESSING_VERSION,
            routed=True,
            request=request,
            resolved_resource_id=SECCL_PACKAGE_ID,
            resolved_reference_group_id=group_id,
            resolved_reference_group=dict(group.selection_criteria),
            resolved_level="spoken_exam",
            fallback_chain=("spoken_exam",),
            fallback_disclosure=None,
            eligibility=eligibility,
            reference_group_version=self.seccl_reference_group_version,
            feature_set_version=self.feature_set_version,
            corpus_package_id=resource.corpus_package_id,
            manifest_hash=resource.manifest_hash,
            unmatched_reason=None,
            learner_exposure="research_only",
            secondary=True,
        )
