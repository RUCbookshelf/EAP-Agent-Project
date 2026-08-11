"""Locally-defined written-corpus routing protocol/fake (Wave-2 Goal C).

Consumes the modality-aware routing contract semantics (CORPUS Goal
PDW2-E): written L2 requests route to the primary written resource
(WECCL20) by default; SECCL20 is classified spoken + secondary/research_only
and is NEVER a written candidate. SECCL may only be selected by an explicit
spoken-modality opt-in (``allow_secondary=True``) under research_only
exposure and a spoken-language domain. The real CORPUS routing module lands
at integration; this module MUST NOT import it -- the protocol and
deterministic fake are defined here locally.

All outputs remain descriptive context (research_only, descriptive_only);
reference distributions are never proficiency ground truth.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.l2.wave2.models import TASK_TYPE_IDS, WRITING_CONTEXT_IDS


MODALITY_WRITTEN = "written"
MODALITY_SPOKEN = "spoken"

WECCL_PACKAGE_ID = "sweccl2-weccl20-v0.1.0"
SECCL_PACKAGE_ID = "sweccl2-seccl20-v0.1.0"

L2_WRITING_DOMAIN = "l2_writing"
L2_SPEAKING_DOMAIN = "l2_speaking"

ROUTING_PROCESSING_VERSION = "l2-writing-router-local-v0.1.0"
ROUTING_RESULT_ARTIFACT_VERSION = "l2-writing-routing-result-local-v0.1.0"


class WrittenCorpusRoutingRequest(BaseModel):
    """One routing request derived from task context (task definition only)."""

    model_config = ConfigDict(extra="forbid")

    task_type: str = Field(min_length=1, max_length=64)
    writing_context: str = Field(min_length=1, max_length=64)
    writing_prompt: str = Field(default="", max_length=4000)
    modality: Literal["written", "spoken"] = MODALITY_WRITTEN

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, value: str) -> str:
        if value not in TASK_TYPE_IDS:
            raise ValueError(
                f"Unknown task_type {value!r}; routing is defined for the "
                f"five-type L2 taxonomy only."
            )
        return value

    @field_validator("writing_context")
    @classmethod
    def validate_writing_context(cls, value: str) -> str:
        if value not in WRITING_CONTEXT_IDS:
            raise ValueError(
                f"Unknown writing_context {value!r}; valid contexts: "
                f"{list(WRITING_CONTEXT_IDS)}."
            )
        return value


@runtime_checkable
class CorpusRoutingProtocol(Protocol):
    """Modality-aware routing boundary consumed by the revision loop."""

    def route(
        self,
        request: WrittenCorpusRoutingRequest,
        *,
        domain: str = L2_WRITING_DOMAIN,
        allow_secondary: bool = False,
    ) -> "CorpusRoutingResult": ...


class CorpusRoutingResult(BaseModel):
    """One versioned routing outcome with full disclosure."""

    model_config = ConfigDict(extra="forbid")

    artifact_version: str = ROUTING_RESULT_ARTIFACT_VERSION
    processing_version: str = ROUTING_PROCESSING_VERSION
    routed: bool
    modality: str
    resolved_resource_id: str | None = None
    resolved_reference_group_id: str | None = None
    resolved_level: str | None = None
    fallback_chain: list[str] = Field(default_factory=list)
    fallback_disclosure: str | None = None
    eligibility_reasons: list[str] = Field(default_factory=list)
    reference_group_version: str = "l2-reference-groups-local-v0.1.0"
    feature_set_version: str = "corpus-features-local-v0.1.0"
    corpus_package_id: str
    manifest_hash: str = "LOCAL-FAKE-MANIFEST-001"
    unmatched_reason: str | None = None
    learner_exposure: str = "research_only"
    artifact_class: str = "NON-RECONSTRUCTIVE AGGREGATE ARTIFACT"
    descriptive_only: bool = True
    secondary: bool = False


class LocalWrittenCorpusRouter:
    """Deterministic branch-local fake of the modality-aware router.

    Written requests route to WECCL20 with a context-aware reference group;
    the fallback chain mirrors the CORPUS contract
    (same_prompt -> task_type_context -> task_type ->
    similar_written_context -> broader_distribution). SECCL is classified
    spoken + secondary and requires an explicit spoken opt-in with a
    spoken-language domain under research_only exposure.
    """

    processing_version = ROUTING_PROCESSING_VERSION

    def route(
        self,
        request: WrittenCorpusRoutingRequest,
        *,
        domain: str = L2_WRITING_DOMAIN,
        allow_secondary: bool = False,
    ) -> CorpusRoutingResult:
        if request.modality == MODALITY_SPOKEN:
            return self._route_spoken(
                request, domain=domain, allow_secondary=allow_secondary,
            )
        return self._route_written(request, domain=domain)

    def _route_written(
        self, request: WrittenCorpusRoutingRequest, *, domain: str,
    ) -> CorpusRoutingResult:
        if domain != L2_WRITING_DOMAIN:
            return self._unrouted(
                request, WECCL_PACKAGE_ID,
                [f"domain {domain!r} is not an l2_writing routing domain"],
            )
        reference_group_id = f"RG-task_type={request.task_type}-context={request.writing_context}"
        return CorpusRoutingResult(
            routed=True,
            modality=MODALITY_WRITTEN,
            resolved_resource_id=WECCL_PACKAGE_ID,
            resolved_reference_group_id=reference_group_id,
            resolved_level="task_type_context",
            fallback_chain=[
                "same_prompt", "task_type_context", "task_type",
                "similar_written_context", "broader_distribution",
            ],
            fallback_disclosure=None,
            eligibility_reasons=[],
            corpus_package_id=WECCL_PACKAGE_ID,
            learner_exposure="research_only",
            descriptive_only=True,
            secondary=False,
        )

    def _route_spoken(
        self, request: WrittenCorpusRoutingRequest, *, domain: str,
        allow_secondary: bool,
    ) -> CorpusRoutingResult:
        if not allow_secondary:
            return self._unrouted(
                request, SECCL_PACKAGE_ID,
                [
                    "SECCL20 is classified spoken + secondary/research_only; "
                    "explicit allow_secondary=True is required for spoken-modality routing",
                ],
            )
        if domain != L2_SPEAKING_DOMAIN:
            return self._unrouted(
                request, SECCL_PACKAGE_ID,
                [
                    "SECCL20 spoken routing requires the l2_speaking domain; "
                    f"requested domain {domain!r}",
                ],
            )
        return CorpusRoutingResult(
            routed=True,
            modality=MODALITY_SPOKEN,
            resolved_resource_id=SECCL_PACKAGE_ID,
            resolved_reference_group_id="RG-seccl-exam=TEM4",
            resolved_level="spoken_exam",
            fallback_chain=["spoken_exam"],
            fallback_disclosure=None,
            eligibility_reasons=[],
            corpus_package_id=SECCL_PACKAGE_ID,
            learner_exposure="research_only",
            descriptive_only=True,
            secondary=True,
        )

    def _unrouted(
        self, request: WrittenCorpusRoutingRequest, package_id: str,
        reasons: list[str],
    ) -> CorpusRoutingResult:
        return CorpusRoutingResult(
            routed=False,
            modality=request.modality,
            resolved_resource_id=None,
            resolved_reference_group_id=None,
            resolved_level=None,
            fallback_chain=[],
            fallback_disclosure=None,
            eligibility_reasons=reasons,
            corpus_package_id=package_id,
            learner_exposure="research_only",
            descriptive_only=True,
            secondary=False,
            unmatched_reason="; ".join(reasons),
        )


__all__ = [
    "CorpusRoutingProtocol",
    "CorpusRoutingResult",
    "L2_SPEAKING_DOMAIN",
    "L2_WRITING_DOMAIN",
    "LocalWrittenCorpusRouter",
    "MODALITY_SPOKEN",
    "MODALITY_WRITTEN",
    "SECCL_PACKAGE_ID",
    "WECCL_PACKAGE_ID",
    "WrittenCorpusRoutingRequest",
]
