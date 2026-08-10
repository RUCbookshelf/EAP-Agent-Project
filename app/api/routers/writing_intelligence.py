"""PDW1 Writing Intelligence vertical slice router (L2-owned, additive).

Exposes ``POST /api/v1/writing-intelligence/slice``: a real end-to-end,
stateless, research-only pipeline over the existing application modules:

    essay submission -> task/domain resolution -> L2 Domain Pack v1
    classification (app.services.task_type_classifier) -> text/feature
    analysis (composition-root analyzer + app.corpus.student WU-A harness)
    -> real governed Corpus Intelligence query
    (app.corpus.intelligence / ReferenceGroupMatcher / ComparisonEngine)
    -> observed evidence (app.learner.evidence ObservedEvidence /
    EvidenceAdmissionRecord) -> bounded diagnostic inference
    (app.diagnosis.HeuristicDiagnoser) -> FeedbackPolicy
    (app.learner.feedback_policy.FeedbackPolicyService) -> feedback.

Hard boundaries enforced here (WU-D / D3 / D08 / ADR-06):
- Every corpus-derived output carries ``learner_exposure="research_only"``;
  the O2 qualification records do not exist, so exposure enforcement
  resolves to the O1 ``research_only`` default and ``diagnostic_eligible``
  is False. ``displayable`` is fail-closed by the shared enforcer.
- Unavailable states are first-class: no fabricated substitution, no silent
  widening, no fallback without explicit disclosure.
- No normative proficiency/mastery/ability/learning-gain claims: before the
  response is returned, every claim-carrying string composed by this router
  (classification disclosure, diagnosis signal evidence/interpretation,
  recommendation statements, policy status/limitations, unavailable
  reasons) is scanned with the shared NormativeClaimsScanner in strict
  mode; any violation fails the request structurally (HTTP 500, sanitized
  body, nothing returned). Versioned policy/enforcer contract strings
  (e.g. NO_CLAIM_LIMITATION) are validated by the learner-side suite under
  the F1 documentation convention and are not re-emitted here.
- No corpus raw text, path, or handle is ever emitted: only numeric values,
  statuses, and versioned provenance ids cross the boundary. The corpus
  resource descriptor (which carries the prepared-layer path) is never
  serialized.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.deps import get_analyzer
from app.corpus.comparison import (
    COMPARISON_ALGORITHM_VERSION,
    COMPARISON_ARTIFACT_VERSION,
    COMPARISON_PROCESSING_VERSION,
    ComparisonEngine,
)
from app.corpus.errors import CorpusInvalidRequestError
from app.corpus.features import FEATURE_SET_VERSION
from app.corpus.intelligence import CorpusIntelligence
from app.corpus.student import (
    STUDENT_SNAPSHOT_ARTIFACT_VERSION,
    extract_student_features,
)
from app.corpus.tasksignature import ReferenceGroupMatcher, TaskSignature
from app.diagnosis import HeuristicDiagnoser
from app.learner.evidence import (
    MINIMUM_PROVENANCE_FIELDS,
    EvidenceAdmissionRecord,
    EvidenceAdmissionStatus,
    ExposureClass,
    ObservedEvidence,
    ProvenanceChain,
)
from app.learner.exposure import ExposureEnvelope, ExposureEnforcer
from app.learner.feedback_policy import (
    FeedbackPolicyService,
    default_feedback_policy,
)
from app.learner.normative import NormativeClaimsScanner
from app.models.schemas import utc_now
from app.services.task_type_classifier import (
    TaskTypeClassificationError,
    classify_task_definition,
)
from app.shared.vocabularies import EpistemicStatus


SLICE_VERSION = "writing-intelligence-slice-v0.1.0"
LEARNER_EXPOSURE = "research_only"

# Bounded feature set for the governed corpus comparison (numeric only).
SLICE_FEATURE_IDS = (
    "text_length_tokens",
    "sentence_length_mean",
    "t_unit_proxy",
    "connective_density",
)

NORMATIVE_REJECTION_DETAIL = (
    "The writing intelligence slice rejected an output candidate that failed "
    "the no-normative-claims scan; nothing was returned (structural rejection)."
)

_SCANNER = NormativeClaimsScanner()
_INTELLIGENCE: CorpusIntelligence | None = None


def _get_intelligence() -> CorpusIntelligence:
    """Lazily build the governed Corpus Intelligence facade (read-only)."""
    global _INTELLIGENCE
    if _INTELLIGENCE is None:
        _INTELLIGENCE = CorpusIntelligence()
    return _INTELLIGENCE


# ---------------------------------------------------------------------------
# Request / response contracts
# ---------------------------------------------------------------------------


class WritingIntelligenceSliceRequest(BaseModel):
    """Essay submission envelope for the research-only writing slice."""

    model_config = ConfigDict(extra="forbid")

    essay_text: str = Field(min_length=1, max_length=50_000)
    writing_prompt: str | None = Field(default=None, max_length=4000)
    declared_task_type: str | None = Field(default=None, max_length=64)
    submission_id: str | None = Field(default=None, max_length=100)
    prompt_id: str | None = Field(default=None, max_length=32)
    timed_status: str | None = Field(default=None, max_length=16)
    genre: str | None = Field(default=None, max_length=32)
    draft_stage: str | None = Field(default=None, max_length=100)
    tool_use: str | None = Field(default=None, max_length=300)

    @field_validator("essay_text", "writing_prompt", mode="before")
    @classmethod
    def _strip_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


class ClassificationStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: str
    task_type: str | None
    reason_code: str | None
    taxonomy_version: str
    dictionary_version: str
    declared_task_type: str | None = None
    fallback_disclosure: str | None = None
    provenance: dict[str, str] = Field(default_factory=dict)


class AnalysisStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analyzer_id: str
    analyzer_version: str
    backend: str
    configuration_version: str | None = None
    fallback_used: bool = False
    metrics: dict[str, float | int | None]
    provenance: dict[str, str] = Field(default_factory=dict)


class FeatureValueView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_id: str
    value: float | int | None
    unit: str
    analysis_status: str
    limitations: list[str] = Field(default_factory=list)


class FeatureSnapshotStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_version: str
    feature_set_version: str
    processing_version: str
    extractor: str
    features: list[FeatureValueView]
    eligibility: list[dict[str, str]] = Field(default_factory=list)
    text_retained: bool = False
    learner_exposure: str = LEARNER_EXPOSURE
    provenance: dict[str, str] = Field(default_factory=dict)


class ComparisonView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_id: str
    student_value: float | int | None
    student_analysis_status: str
    availability: str
    estimated_percentile: float | None
    z_distance: float | None
    percentile_method: str
    distribution_version: str
    n_effective: int
    unavailable_reason: str | None = None
    limitations: list[str] = Field(default_factory=list)
    evidence_class: str = "observed_descriptive"
    learner_exposure: str = LEARNER_EXPOSURE


class MatchView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matched: bool
    requested_task: dict[str, Any]
    resolved_reference_group_id: str | None
    resolved_reference_group: dict[str, Any] | None
    fallback_disclosure: str | None
    reference_group_version: str
    feature_set_version: str
    corpus_package_id: str
    manifest_hash: str
    unmatched_reason: str | None
    provenance: dict[str, str] = Field(default_factory=dict)


class ExposureView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exposure_class: str
    learner_exposure: str
    diagnostic_eligible: bool
    reject: bool
    reasons: list[str] = Field(default_factory=list)


class CorpusQueryStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    match: MatchView
    comparisons: list[ComparisonView] = Field(default_factory=list)
    n_available: int = 0
    n_unavailable: int = 0
    exposure: ExposureView | None = None
    provenance: dict[str, str] = Field(default_factory=dict)


class EvidenceView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    evidence_type: str
    source_event_id: str
    epistemic_status: str
    admission_status: str
    exposure_class: str
    value: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class DiagnosisSignalView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnosis_id: str
    category: str
    evidence: str
    interpretation: str
    confidence: str
    kind: str
    rule_version: str


class DiagnosisStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnosis_version: str
    limitation: str
    strengths: list[DiagnosisSignalView] = Field(default_factory=list)
    improvement_priorities: list[DiagnosisSignalView] = Field(default_factory=list)
    provenance: dict[str, str] = Field(default_factory=dict)


class RecommendationView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: str
    evidence_ids: list[str]
    priority: int
    statement: str
    epistemic_status: str


class PolicyStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: str
    policy_id: str
    policy_version: str
    status: str
    evidence_ids: list[str] = Field(default_factory=list)
    recommendations: list[RecommendationView] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    provenance: dict[str, str] = Field(default_factory=dict)


class WritingIntelligenceSliceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slice_id: str
    slice_version: str
    status: str
    learner_exposure: str = LEARNER_EXPOSURE
    classification: ClassificationStep
    analysis: AnalysisStep
    feature_snapshot: FeatureSnapshotStep
    corpus_query: CorpusQueryStep
    evidence: list[EvidenceView] = Field(default_factory=list)
    diagnosis: DiagnosisStep | None = None
    policy: PolicyStep
    provenance: dict[str, dict[str, str]] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def _classification_step(request: WritingIntelligenceSliceRequest) -> ClassificationStep:
    """L2 Domain Pack v1 task classification (task-definition scope only)."""
    result = classify_task_definition(request.writing_prompt, request.declared_task_type)
    return ClassificationStep(
        outcome=result.outcome,
        task_type=result.task_type,
        reason_code=result.reason_code,
        taxonomy_version=result.taxonomy_version,
        dictionary_version=result.dictionary_version,
        declared_task_type=request.declared_task_type,
        fallback_disclosure=(
            "Task classified as unclassified (reason_code="
            f"{result.reason_code}); no typed task-routing semantics were "
            "applied and no silent reclassification occurred (taxonomy "
            "contract Constraints 5/6)."
            if result.outcome == "unclassified"
            else None
        ),
        provenance={
            "taxonomy_version": result.taxonomy_version,
            "dictionary_version": result.dictionary_version,
            "rule_version": result.provenance.get("rule_version", ""),
            "classification_scope": "task_definition_only",
        },
    )


def _analysis_step(result) -> AnalysisStep:
    """Existing analyzer path (composition-root analyzer)."""
    metrics = {
        metric_id: result.metrics.get(metric_id)
        for metric_id in (
            "word_count",
            "sentence_count",
            "paragraph_count",
            "average_sentence_length",
            "type_token_ratio",
            "connective_count",
        )
    }
    return AnalysisStep(
        analyzer_id=result.analyzer_id,
        analyzer_version=result.analyzer_version,
        backend=result.backend,
        configuration_version=result.configuration_version,
        fallback_used=result.fallback_used,
        metrics=metrics,
        provenance={
            "analyzer_version": result.analyzer_version,
            "analysis_version": result.analysis_version,
            "configuration_version": result.configuration_version,
        },
    )


def _snapshot_step(request: WritingIntelligenceSliceRequest) -> FeatureSnapshotStep:
    """WU-A student feature snapshot harness (numeric, non-reconstructive)."""
    snapshot = extract_student_features(
        request.essay_text, submission_id=request.submission_id
    )
    return FeatureSnapshotStep(
        artifact_version=snapshot.artifact_version,
        feature_set_version=snapshot.feature_set_version,
        processing_version=snapshot.processing_version,
        extractor=snapshot.extractor,
        features=[
            FeatureValueView(
                feature_id=feature.feature_id,
                value=feature.value,
                unit=feature.unit,
                analysis_status=feature.analysis_status,
                limitations=list(feature.limitations),
            )
            for feature in snapshot.features
        ],
        eligibility=[asdict(check) for check in snapshot.eligibility],
        text_retained=snapshot.text_retained,
        learner_exposure=snapshot.learner_exposure,
        provenance={
            "artifact_version": snapshot.artifact_version,
            "feature_set_version": snapshot.feature_set_version,
            "processing_version": snapshot.processing_version,
            "extractor_version": snapshot.extractor_version,
            "learner_exposure": snapshot.learner_exposure,
            "artifact_class": snapshot.artifact_class,
        },
    )


def _match_view(match) -> MatchView:
    return MatchView(
        matched=match.matched,
        requested_task=dict(match.requested_task),
        resolved_reference_group_id=match.resolved_reference_group_id,
        resolved_reference_group=match.resolved_reference_group,
        fallback_disclosure=match.fallback_disclosure,
        reference_group_version=match.reference_group_version,
        feature_set_version=match.feature_set_version,
        corpus_package_id=match.corpus_package_id,
        manifest_hash=match.manifest_hash,
        unmatched_reason=match.unmatched_reason,
        provenance=dict(match.provenance),
    )


def _comparison_view(comparison) -> ComparisonView:
    return ComparisonView(
        feature_id=comparison.feature_id,
        student_value=comparison.student_value,
        student_analysis_status=comparison.student_analysis_status,
        availability=comparison.availability,
        estimated_percentile=comparison.estimated_percentile,
        z_distance=comparison.z_distance,
        percentile_method=comparison.percentile_method,
        distribution_version=comparison.distribution_version,
        n_effective=comparison.n_effective,
        unavailable_reason=comparison.unavailable_reason,
        limitations=list(comparison.distance_limitations),
        evidence_class=comparison.evidence_class,
        learner_exposure=comparison.learner_exposure,
    )


def _evidence_view(record: ObservedEvidence) -> EvidenceView:
    return EvidenceView(
        evidence_id=record.evidence_id,
        evidence_type=record.evidence_type,
        source_event_id=record.source_event_id,
        epistemic_status=record.epistemic_status.value,
        admission_status=record.admission_status.value,
        exposure_class=record.exposure_class.value,
        value=dict(record.value),
        provenance=record.provenance.model_dump(),
        limitations=list(record.limitations),
    )


def _signal_view(signal) -> DiagnosisSignalView:
    return DiagnosisSignalView(
        diagnosis_id=signal.diagnosis_id,
        category=signal.category,
        evidence=signal.evidence,
        interpretation=signal.interpretation,
        confidence=signal.confidence,
        kind=signal.kind,
        rule_version=signal.rule_version,
    )


def _unavailable_response(
    *,
    slice_id: str,
    reason: str,
    classification: ClassificationStep,
    analysis: AnalysisStep,
    snapshot: FeatureSnapshotStep,
    match_view: MatchView,
    policy: FeedbackPolicyService,
) -> WritingIntelligenceSliceResponse:
    limitation = (
        "Corpus intelligence query unavailable; feedback policy application "
        "fail-closed; nothing was fabricated or substituted."
    )
    return WritingIntelligenceSliceResponse(
        slice_id=slice_id,
        slice_version=SLICE_VERSION,
        status="unavailable",
        learner_exposure=LEARNER_EXPOSURE,
        classification=classification,
        analysis=analysis,
        feature_snapshot=snapshot,
        corpus_query=CorpusQueryStep(
            status="unavailable",
            match=match_view,
            provenance={
                "artifact_version": COMPARISON_ARTIFACT_VERSION,
                "processing_version": COMPARISON_PROCESSING_VERSION,
                "algorithm_version": COMPARISON_ALGORITHM_VERSION,
                "reference_group_version": match_view.reference_group_version,
                "feature_set_version": match_view.feature_set_version,
                "corpus_package_id": match_view.corpus_package_id,
                "manifest_hash": match_view.manifest_hash,
                "learner_exposure": LEARNER_EXPOSURE,
            },
        ),
        evidence=[],
        diagnosis=None,
        policy=PolicyStep(
            application_id=f"FP-{slice_id}",
            policy_id=policy.policy.policy_id,
            policy_version=policy.policy.version,
            status="unavailable",
            recommendations=[],
            limitations=[limitation, f"unavailable_reason: {reason}"],
            provenance={
                "policy_id": policy.policy.policy_id,
                "policy_version": policy.policy.version,
                "application_id": f"FP-{slice_id}",
                "enforcement": "fail-closed",
            },
        ),
        provenance={
            "classification": dict(classification.provenance),
            "analysis": dict(analysis.provenance),
            "feature_snapshot": dict(snapshot.provenance),
            "corpus_query": {
                "artifact_version": COMPARISON_ARTIFACT_VERSION,
                "processing_version": COMPARISON_PROCESSING_VERSION,
                "algorithm_version": COMPARISON_ALGORITHM_VERSION,
                "reference_group_version": match_view.reference_group_version,
                "feature_set_version": match_view.feature_set_version,
                "corpus_package_id": match_view.corpus_package_id,
                "manifest_hash": match_view.manifest_hash,
                "learner_exposure": LEARNER_EXPOSURE,
            },
            "evidence": {
                "record_version": "evidence-admissibility-record-v0.1.0",
                "provenance_minimum": ",".join(MINIMUM_PROVENANCE_FIELDS),
            },
            "diagnosis": {"diagnosis_version": "unavailable"},
            "policy": {
                "policy_id": policy.policy.policy_id,
                "policy_version": policy.policy.version,
                "application_id": f"FP-{slice_id}",
            },
        },
    )


def _run_slice(
    request: WritingIntelligenceSliceRequest, analyzer,
) -> WritingIntelligenceSliceResponse:
    slice_id = f"WI-{uuid.uuid4().hex[:12]}"

    classification = _classification_step(request)
    analysis_result = analyzer.analyze(
        request.essay_text,
        writing_prompt=request.writing_prompt or "",
        draft_stage=request.draft_stage,
        tool_use=request.tool_use,
    )
    analysis = _analysis_step(analysis_result)
    student_snapshot = extract_student_features(
        request.essay_text, submission_id=request.submission_id
    )
    snapshot = _snapshot_step(request)

    intelligence = _get_intelligence()
    signature = TaskSignature(
        prompt_id=request.prompt_id,
        timed_status=request.timed_status,
        genre=request.genre,
    )
    match = ReferenceGroupMatcher(intelligence).match(signature)
    match_view = _match_view(match)

    if not match.matched:
        reason = match.unmatched_reason or "no reference group matched"
        return _unavailable_response(
            slice_id=slice_id,
            reason=reason,
            classification=classification,
            analysis=analysis,
            snapshot=snapshot,
            match_view=match_view,
            policy=FeedbackPolicyService(),
        )

    comparison = ComparisonEngine(intelligence).compare(
        student_snapshot, match, feature_ids=list(SLICE_FEATURE_IDS)
    )
    comparison_views = [_comparison_view(item) for item in comparison.comparisons]
    if comparison.n_available == 0:
        return _unavailable_response(
            slice_id=slice_id,
            reason=(
                "no comparison available for the resolved reference group "
                f"{comparison.reference_group_id}"
            ),
            classification=classification,
            analysis=analysis,
            snapshot=snapshot,
            match_view=match_view,
            policy=FeedbackPolicyService(),
        )

    first_available = next(
        item for item in comparison.comparisons if item.availability == "available"
    )
    admission_status = (
        EvidenceAdmissionStatus.ADMISSIBLE
        if comparison.n_unavailable == 0
        else EvidenceAdmissionStatus.LIMITED
    )
    admission_reasons = (
        []
        if comparison.n_unavailable == 0
        else [
            f"{comparison.n_unavailable} feature comparison(s) unavailable; "
            "disclosure carried",
        ]
    )
    record = EvidenceAdmissionRecord(
        artifact_id=f"writing-intelligence-slice/{slice_id}",
        status=admission_status,
        reasons=admission_reasons,
        provenance=ProvenanceChain(
            source_package=first_available.corpus_package_id,
            manifest_hash=first_available.manifest_hash,
            feature_set_version=comparison.feature_set_version,
            reference_group_version=comparison.reference_group_version,
            distribution_version=first_available.distribution_version,
            processing_version=COMPARISON_PROCESSING_VERSION,
            algorithm_version=COMPARISON_ALGORITHM_VERSION,
            effective_n=first_available.n_effective,
            availability=(
                "available" if comparison.n_unavailable == 0 else "limited"
            ),
        ),
    )
    envelope = ExposureEnvelope(
        artifact_id=record.artifact_id,
        artifact_version=COMPARISON_ARTIFACT_VERSION,
        stated_exposure_class=ExposureClass.RESEARCH_ONLY,
        learner_exposure=LEARNER_EXPOSURE,
        admissibility_record=record,
        epistemic_status=EpistemicStatus.OBSERVED_DESCRIPTIVE,
        feature_set_version=comparison.feature_set_version,
        required_feature_set_version=FEATURE_SET_VERSION,
        provenance=record.provenance,
        n_effective=first_available.n_effective,
    )
    enforcement = ExposureEnforcer().enforce(envelope)

    evidence_views: list[EvidenceView] = []
    candidates: list[ObservedEvidence] = []

    for item in comparison.comparisons:
        if item.availability != "available":
            continue
        chain = ProvenanceChain(
            source_package=item.corpus_package_id,
            manifest_hash=item.manifest_hash,
            feature_set_version=item.feature_set_version,
            reference_group_version=item.reference_group_version,
            distribution_version=item.distribution_version,
            processing_version=item.processing_version,
            algorithm_version=item.algorithm_version,
            effective_n=item.n_effective,
            availability=item.availability,
        )
        admitted = ObservedEvidence(
            evidence_id=f"OE{len(evidence_views) + 1:06d}",
            source_event_id=f"SUB-{slice_id}",
            evidence_type="corpus_reference_comparison",
            observed_at=utc_now(),
            epistemic_status=EpistemicStatus.OBSERVED_DESCRIPTIVE,
            admission_status=(
                EvidenceAdmissionStatus.ADMISSIBLE
                if not item.distance_limitations
                else EvidenceAdmissionStatus.LIMITED
            ),
            admission_reason=(
                None
                if not item.distance_limitations
                else "LIMITED: distance limitations attached"
            ),
            exposure_class=ExposureClass.RESEARCH_ONLY,
            provenance=chain,
            value={
                "feature_id": item.feature_id,
                "student_value": item.student_value,
                "estimated_percentile": item.estimated_percentile,
                "z_distance": item.z_distance,
                "percentile_method": item.percentile_method,
                "n_effective": item.n_effective,
            },
            limitations=list(item.distance_limitations) + [
                "Corpus distance is observed descriptive evidence only; it "
                "carries no normative interpretation.",
                "learner_exposure=research_only; not learner-facing (D3/D08).",
            ],
        )
        candidates.append(admitted)
        evidence_views.append(_evidence_view(admitted))

    diagnosis = HeuristicDiagnoser().diagnose(analysis_result)
    diagnosis_step = DiagnosisStep(
        diagnosis_version=diagnosis.diagnosis_version,
        limitation=diagnosis.limitation,
        strengths=[_signal_view(signal) for signal in diagnosis.strengths],
        improvement_priorities=[
            _signal_view(signal) for signal in diagnosis.improvement_priorities
        ],
        provenance={"diagnosis_version": diagnosis.diagnosis_version},
    )
    for priority, signal in enumerate(
        [*diagnosis.strengths, *diagnosis.improvement_priorities], start=1
    ):
        admitted = ObservedEvidence(
            evidence_id=f"OE{len(evidence_views) + 1:06d}",
            source_event_id=f"SUB-{slice_id}",
            evidence_type="diagnostic_signal",
            observed_at=utc_now(),
            epistemic_status=EpistemicStatus.GATED_INFERENCE,
            admission_status=EvidenceAdmissionStatus.ADMISSIBLE,
            admission_reason="prototype heuristic signal; teacher review required",
            exposure_class=ExposureClass.RESEARCH_ONLY,
            provenance=ProvenanceChain(
                source_package=SLICE_VERSION,
                manifest_hash=str(
                    analysis_result.artifacts.get("analysis_text_hash")
                    or "unavailable"
                ),
                processing_version=diagnosis.diagnosis_version,
                availability="available",
            ),
            value={
                "category": signal.category,
                "confidence": signal.confidence,
                "kind": signal.kind,
                "priority_index": priority,
            },
            limitations=[diagnosis.limitation],
        )
        candidates.append(admitted)
        evidence_views.append(_evidence_view(admitted))

    policy = FeedbackPolicyService()
    application = policy.apply(
        envelope, candidates, application_id=f"FP-{slice_id}",
    )
    policy_step = PolicyStep(
        application_id=application.application_id,
        policy_id=application.policy_id,
        policy_version=application.policy_version,
        status=application.status,
        evidence_ids=list(application.evidence_ids),
        recommendations=[
            RecommendationView(
                recommendation_id=item.recommendation_id,
                evidence_ids=list(item.evidence_ids),
                priority=item.priority,
                statement=item.statement,
                epistemic_status=item.epistemic_status.value,
            )
            for item in application.recommendations
        ],
        limitations=list(application.limitations),
        provenance={
            "policy_id": application.policy_id,
            "policy_version": application.policy_version,
            "application_id": application.application_id,
            "gate_rules": ",".join(policy.policy.gate_rules),
        },
    )

    corpus_provenance = {
        "artifact_version": comparison.artifact_version,
        "processing_version": comparison.processing_version,
        "algorithm_version": COMPARISON_ALGORITHM_VERSION,
        "reference_group_version": comparison.reference_group_version,
        "feature_set_version": comparison.feature_set_version,
        "corpus_package_id": comparison.corpus_package_id,
        "manifest_hash": comparison.manifest_hash,
        "learner_exposure": comparison.learner_exposure,
    }

    return WritingIntelligenceSliceResponse(
        slice_id=slice_id,
        slice_version=SLICE_VERSION,
        status="success",
        learner_exposure=LEARNER_EXPOSURE,
        classification=classification,
        analysis=analysis,
        feature_snapshot=snapshot,
        corpus_query=CorpusQueryStep(
            status="matched",
            match=match_view,
            comparisons=comparison_views,
            n_available=comparison.n_available,
            n_unavailable=comparison.n_unavailable,
            exposure=ExposureView(
                exposure_class=enforcement.exposure_class.value,
                learner_exposure=enforcement.learner_exposure,
                diagnostic_eligible=enforcement.diagnostic_eligible,
                reject=enforcement.reject,
                reasons=list(enforcement.reasons),
            ),
            provenance=dict(corpus_provenance),
        ),
        evidence=evidence_views,
        diagnosis=diagnosis_step,
        policy=policy_step,
        provenance={
            "classification": dict(classification.provenance),
            "analysis": dict(analysis.provenance),
            "feature_snapshot": dict(snapshot.provenance),
            "corpus_query": dict(corpus_provenance),
            "evidence": {
                "record_version": "evidence-admissibility-record-v0.1.0",
                "provenance_minimum": ",".join(MINIMUM_PROVENANCE_FIELDS),
            },
            "diagnosis": dict(diagnosis_step.provenance),
            "policy": dict(policy_step.provenance),
        },
    )


# ---------------------------------------------------------------------------
# Normative-claim rejection (strict scan of router-composed strings)
# ---------------------------------------------------------------------------


def _claim_carrying_strings(payload: dict[str, Any]) -> list[str]:
    """Collect the claim-carrying strings this router composes.

    Versioned policy/enforcer contract strings (validated by the learner
    suite under the F1 documentation convention) are not re-collected here.
    """
    collected: list[str] = []

    classification = payload.get("classification") or {}
    if classification.get("fallback_disclosure"):
        collected.append(str(classification["fallback_disclosure"]))

    diagnosis = payload.get("diagnosis") or {}
    for key in ("strengths", "improvement_priorities"):
        for signal in diagnosis.get(key, []) or []:
            for field in ("evidence", "interpretation"):
                collected.append(str(signal.get(field, "")))

    policy = payload.get("policy") or {}
    if policy.get("status"):
        collected.append(str(policy["status"]))
    for limitation in policy.get("limitations", []) or []:
        collected.append(str(limitation))
    for recommendation in policy.get("recommendations", []) or []:
        collected.append(str(recommendation.get("statement", "")))

    corpus_query = payload.get("corpus_query") or {}
    if corpus_query.get("status") == "unavailable":
        collected.append("unavailable")
        match = corpus_query.get("match") or {}
        if match.get("unmatched_reason"):
            collected.append(str(match["unmatched_reason"]))

    return [text for text in collected if text]


def _normative_violations(payload: dict[str, Any]) -> list[str]:
    violations: set[str] = set()
    for text in _claim_carrying_strings(payload):
        for violation in _SCANNER.scan_text(text):
            violations.add(violation.term)
    return sorted(violations)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


router = APIRouter()


@router.post(
    "/api/v1/writing-intelligence/slice",
    response_model=WritingIntelligenceSliceResponse,
)
def run_writing_intelligence_slice(
    request: WritingIntelligenceSliceRequest,
    analyzer=Depends(get_analyzer),
) -> WritingIntelligenceSliceResponse:
    """Run the end-to-end Writing Intelligence vertical slice (research-only)."""
    try:
        result = _run_slice(request, analyzer)
    except TaskTypeClassificationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except CorpusInvalidRequestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except ValueError:
        # The FeedbackPolicyService raises ValueError only when a
        # recommendation statement trips its own normative scan.
        raise HTTPException(status_code=500, detail=NORMATIVE_REJECTION_DETAIL) from None
    violations = _normative_violations(result.model_dump(mode="python"))
    if violations:
        raise HTTPException(status_code=500, detail=NORMATIVE_REJECTION_DETAIL) from None
    return result
