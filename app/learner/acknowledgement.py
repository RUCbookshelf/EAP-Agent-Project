"""Positive longitudinal acknowledgement service (LEARNER-owned, WU2-C).

Fail-closed service over the acknowledgement contracts: every gate must pass
before a single append-only write; any failure raises ``AcknowledgementError``
with a stable kind and writes nothing. No database, migration, scheduler, or
runtime is introduced: the append-only store and the learner-scoped evidence
lookup are injected ports (the composition root wires real implementations;
tests inject in-memory doubles).

Gate order (all fail closed, no write on failure):

1. evidence lookup port present (``evidence_unavailable``);
2. explicit learner consent: granted, not revoked, correct scope, matching
   learner, not future-dated (``consent_*``);
3. non-empty source evidence IDs (``missing_evidence``);
4. acknowledgeable source kind (``invalid_source_kind``);
5. explicit verified evidence status (``invalid_evidence_status``);
6. stable provenance present and complete (``missing_provenance``);
7. policy/model/config or record version present (``missing_version``);
8. source records exist, are learner-owned, admitted, and descriptive
   (``evidence_not_found`` / ``cross_student`` / ``invalid_source_record``);
9. structural links are learner-scoped and the authentic-evidence status is
   valid (``learning_item_not_found`` / ``learning_item_owner_mismatch`` /
   ``practice_activity_not_found`` / ``practice_activity_owner_mismatch`` /
   ``review_event_not_found`` / ``review_event_owner_mismatch`` /
   ``invalid_authentic_evidence_status``);
10. no normative or causal language in the acknowledgement text
   (``normative_language`` / ``causal_language``);
11. no duplicate or conflicting acknowledgement (``duplicate_acknowledgement``
    / ``conflict``).
"""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Any, Callable, Protocol, runtime_checkable

from app.models.schemas import utc_now
from app.shared.vocabularies import EvidenceStatus

from .acknowledgement_contracts import (
    ACKNOWLEDGEMENT_CONSENT_SCOPE,
    ACKNOWLEDGEABLE_SOURCE_KINDS,
    AcknowledgementRecord,
    AcknowledgementRequest,
    AcknowledgementResult,
    AcknowledgementSourceKind,
)
from .evidence import (
    EvidenceAdmissionStatus,
    ExposureClass,
    ObservedEvidence,
    check_provenance_completeness,
)
from .normative import NormativeClaimsScanner
from .practice_provenance import PracticeActivityStatus, PracticeProvenanceRecord


# Frozen causal/change-claim wording rejected in learner-facing
# acknowledgement text. The normative scanner already rejects the frozen
# banned vocabulary; this list closes the causal-transfer boundary.
CAUSAL_LANGUAGE_TERMS: tuple[str, ...] = (
    "improved",
    "improvement",
    "improving",
    "progress",
    "progressed",
    "progression",
    "regress",
    "regression",
    "decline",
    "declined",
    "increased",
    "decreased",
    "growth",
    "transfer",
    "caused",
    "cause",
    "causes",
    "led to",
    "leads to",
    "resulted in",
    "results in",
    "due to",
    "attributed to",
    "because of",
    "brought about",
    "owed to",
    "进步",
    "改善",
    "提高",
    "提升",
    "下降",
    "退步",
    "导致",
    "归因于",
    "因为",
)


class AcknowledgementError(Exception):
    """Fail-closed acknowledgement failure with a stable machine kind."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


class AcknowledgementStoreConflictError(Exception):
    """Append-only store conflict raised by durable stores (defense in depth).

    The service pre-checks duplicates, but a durable store may still reject
    the write (for example after a restart), so ``acknowledge`` translates
    this exception to ``AcknowledgementError`` with the store's kind and
    message. Defined here (mirroring CORE's repository-conflict pattern)
    and imported by the durable SQLite repository.
    """

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


@runtime_checkable
class AcknowledgementStorePort(Protocol):
    """Append-only acknowledgement store; no update/delete surface."""

    def append(self, record: AcknowledgementRecord) -> None: ...

    def get(self, acknowledgement_id: str) -> AcknowledgementRecord | None: ...

    def list_for_learner(self, learner_id: str) -> list[AcknowledgementRecord]: ...


@runtime_checkable
class AcknowledgementEvidencePort(Protocol):
    """Learner-scoped lookup over already admitted source records."""

    def owner_of(self, source_id: str) -> str | None: ...

    def get_record(self, learner_id: str, source_id: str) -> Any | None: ...


def _stable_acknowledgement_id(
    learner_id: str,
    source_kind: AcknowledgementSourceKind,
    evidence_ids: list[str],
    text: str,
    record_version: str,
) -> str:
    """Deterministic acknowledgement id (reconstructible, like CORE's stable
    card id); identical requests collide and are rejected as duplicates."""

    material = "|".join(
        [learner_id, source_kind.value, *sorted(evidence_ids), text, record_version]
    )
    digest = sha256(material.encode("utf-8")).hexdigest()
    return f"ACK-{digest[:16]}"


class AcknowledgementService:
    """Fail-closed positive longitudinal acknowledgement service."""

    def __init__(
        self,
        store: AcknowledgementStorePort,
        *,
        evidence_port: AcknowledgementEvidencePort | None = None,
        scanner: NormativeClaimsScanner | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store
        self.evidence_port = evidence_port
        self.scanner = scanner or NormativeClaimsScanner()
        self._now = now or utc_now

    def acknowledge(
        self, request: AcknowledgementRequest,
    ) -> AcknowledgementResult:
        """Validate every gate and append one record; raises on any failure."""

        self._check_evidence_port()
        self._check_consent(request)
        self._check_evidence_ids(request)
        self._check_source_kind(request)
        self._check_evidence_status(request)
        self._check_provenance(request)
        self._check_versions(request)
        self._check_source_records(request)
        self._check_links(request)
        self._check_text(request)
        self._check_duplicates(request)

        acknowledgement_id = (
            request.acknowledgement_id
            or _stable_acknowledgement_id(
                request.learner_id,
                request.source_kind,
                request.source_evidence_ids,
                request.acknowledgement_text,
                request.record_version,
            )
        )
        record = AcknowledgementRecord(
            acknowledgement_id=acknowledgement_id,
            learner_id=request.learner_id,
            source_kind=request.source_kind,
            source_evidence_ids=request.source_evidence_ids,
            source_event_ids=request.source_event_ids,
            learning_item_id=request.learning_item_id,
            authentic_evidence_status=request.authentic_evidence_status,
            practice_activity_id=request.practice_activity_id,
            review_event_id=request.review_event_id,
            evidence_status=request.evidence_status,
            epistemic_status=request.epistemic_status,
            provenance=request.provenance,
            policy_version=request.policy_version,
            model_version=request.model_version,
            config_version=request.config_version,
            record_version=request.record_version,
            acknowledgement_text=request.acknowledgement_text,
            consent=request.consent,
            observed_span_start=request.observed_span_start,
            observed_span_end=request.observed_span_end,
            recorded_at=self._now(),
        )
        # Defensive: the assembled record itself must scan clean in
        # documentation mode (limitations state the prohibition).
        violations = self.scanner.scan_pydantic(record, documentation=True)
        if violations:
            raise AcknowledgementError(
                "normative_language",
                "The assembled acknowledgement record contains normative language.",
            )
        try:
            self.store.append(record)
        except AcknowledgementStoreConflictError as exc:
            raise AcknowledgementError(exc.kind, exc.message) from exc
        return AcknowledgementResult(acknowledged=True, record=record)

    def list_for_learner(self, learner_id: str) -> list[AcknowledgementRecord]:
        return list(self.store.list_for_learner(learner_id))

    # ------------------------------------------------------------------
    # Gates
    # ------------------------------------------------------------------

    def _check_evidence_port(self) -> None:
        if self.evidence_port is None:
            raise AcknowledgementError(
                "evidence_unavailable",
                "No evidence lookup is composed; acknowledgement cannot verify "
                "learner ownership and admission.",
            )

    def _check_consent(self, request: AcknowledgementRequest) -> None:
        consent = request.consent
        if consent is None:
            raise AcknowledgementError(
                "consent_missing",
                "Explicit learner consent is required for learner-facing "
                "acknowledgement.",
            )
        if not consent.granted:
            raise AcknowledgementError(
                "consent_denied", "Learner consent was not granted."
            )
        if consent.revoked:
            raise AcknowledgementError(
                "consent_revoked", "Learner consent is revoked."
            )
        if consent.scope != ACKNOWLEDGEMENT_CONSENT_SCOPE:
            raise AcknowledgementError(
                "consent_scope_mismatch",
                "Learner consent does not cover learner-facing acknowledgement.",
            )
        if consent.learner_id != request.learner_id:
            raise AcknowledgementError(
                "consent_learner_mismatch",
                "Learner consent belongs to a different learner.",
            )
        if consent.granted_at > self._now():
            raise AcknowledgementError(
                "consent_invalid", "Learner consent is dated in the future."
            )

    def _check_evidence_ids(self, request: AcknowledgementRequest) -> None:
        if not request.source_evidence_ids:
            raise AcknowledgementError(
                "missing_evidence",
                "At least one non-empty source evidence id is required.",
            )

    def _check_source_kind(self, request: AcknowledgementRequest) -> None:
        if request.source_kind not in ACKNOWLEDGEABLE_SOURCE_KINDS:
            raise AcknowledgementError(
                "invalid_source_kind",
                f"Source kind {request.source_kind.value} is not acknowledgeable: "
                "acknowledgements cover observed evidence or bounded "
                "practice/history signals only.",
            )

    def _check_evidence_status(self, request: AcknowledgementRequest) -> None:
        if request.evidence_status != EvidenceStatus.VERIFIED:
            raise AcknowledgementError(
                "invalid_evidence_status",
                "Only verified evidence may be acknowledged learner-facing.",
            )

    def _check_provenance(self, request: AcknowledgementRequest) -> None:
        provenance = request.provenance
        if provenance is None:
            raise AcknowledgementError(
                "missing_provenance",
                "Stable provenance is required for acknowledgement.",
            )
        result = check_provenance_completeness(provenance)
        if not result.complete:
            raise AcknowledgementError(
                "missing_provenance",
                f"Provenance is incomplete; missing={result.missing}.",
            )

    def _check_versions(self, request: AcknowledgementRequest) -> None:
        if not request.record_version:
            raise AcknowledgementError(
                "missing_version", "A record version is required."
            )
        if not any(
            (
                request.policy_version,
                request.model_version,
                request.config_version,
            )
        ):
            raise AcknowledgementError(
                "missing_version",
                "At least one of policy/model/config version is required.",
            )

    def _check_source_records(self, request: AcknowledgementRequest) -> None:
        for source_id in request.source_evidence_ids:
            owner = self.evidence_port.owner_of(source_id)
            if owner is None:
                raise AcknowledgementError(
                    "evidence_not_found",
                    f"Source evidence {source_id} was not found.",
                )
            if owner != request.learner_id:
                raise AcknowledgementError(
                    "cross_student",
                    f"Source evidence {source_id} belongs to another learner.",
                )
            record = self.evidence_port.get_record(request.learner_id, source_id)
            if record is None:
                raise AcknowledgementError(
                    "evidence_not_found",
                    f"Source evidence {source_id} was not found for this learner.",
                )
            self._validate_source_record(request.source_kind, source_id, record)

    def _validate_source_record(
        self,
        kind: AcknowledgementSourceKind,
        source_id: str,
        record: Any,
    ) -> None:
        if kind == AcknowledgementSourceKind.OBSERVED_EVIDENCE:
            if not isinstance(record, ObservedEvidence):
                self._invalid_source_record(source_id)
            if record.admission_status != EvidenceAdmissionStatus.ADMISSIBLE:
                self._invalid_source_record(source_id)
            if record.epistemic_status.value != "observed_descriptive":
                self._invalid_source_record(source_id)
            if record.exposure_class == ExposureClass.UNAVAILABLE:
                self._invalid_source_record(source_id)
            return
        if kind in {
            AcknowledgementSourceKind.PRACTICE_ACTIVITY,
            AcknowledgementSourceKind.PRACTICE_RESULT,
        }:
            if not isinstance(record, PracticeProvenanceRecord):
                self._invalid_source_record(source_id)
            if record.admission_status != EvidenceAdmissionStatus.ADMISSIBLE:
                self._invalid_source_record(source_id)
            if record.outcome_claim != "none":
                self._invalid_source_record(source_id)
            if record.activity_status != PracticeActivityStatus.COMPLETED:
                self._invalid_source_record(source_id)
            if (
                kind == AcknowledgementSourceKind.PRACTICE_RESULT
                and not record.evaluation_id
            ):
                self._invalid_source_record(source_id)
            return
        if kind == AcknowledgementSourceKind.HISTORY_SIGNAL:
            if not hasattr(record, "evidence_type") or not hasattr(record, "limitation"):
                self._invalid_source_record(source_id)
            if getattr(record, "outcome_claim", "none") != "none":
                self._invalid_source_record(source_id)
            status = getattr(record, "evidence_status", None)
            if status is not None and str(status) != "verified":
                self._invalid_source_record(source_id)
            return
        self._invalid_source_record(source_id)

    def _check_links(self, request: AcknowledgementRequest) -> None:
        """Structural link gates: learner-owned anchors and valid status.

        Provided ``learning_item_id`` / ``practice_activity_id`` /
        ``review_event_id`` links must resolve through the evidence port to
        the requesting learner; anything else fails closed with no write.
        Because the CORE ``review_events`` table is absent on this branch,
        a review link fails closed until INT composes CORE. The
        authentic-evidence status is validated at runtime because records
        are mutable after construction.
        """

        for field, label, not_found, mismatch in (
            (
                "learning_item_id",
                "learning item",
                "learning_item_not_found",
                "learning_item_owner_mismatch",
            ),
            (
                "practice_activity_id",
                "practice activity",
                "practice_activity_not_found",
                "practice_activity_owner_mismatch",
            ),
            (
                "review_event_id",
                "review event",
                "review_event_not_found",
                "review_event_owner_mismatch",
            ),
        ):
            source_id = getattr(request, field)
            if source_id is None:
                continue
            owner = self.evidence_port.owner_of(source_id)
            if owner is None:
                raise AcknowledgementError(
                    not_found,
                    f"{label} {source_id} was not found.",
                )
            if owner != request.learner_id:
                raise AcknowledgementError(
                    mismatch,
                    f"{label} {source_id} belongs to another learner.",
                )
        if request.authentic_evidence_status not in (None, "insufficient", "present"):
            raise AcknowledgementError(
                "invalid_authentic_evidence_status",
                "authentic_evidence_status must be None, 'insufficient', "
                "or 'present'.",
            )

    def _check_text(self, request: AcknowledgementRequest) -> None:
        violations = self.scanner.scan_text(request.acknowledgement_text)
        if violations:
            raise AcknowledgementError(
                "normative_language",
                "The acknowledgement text contains normative or ability language: "
                + ", ".join(sorted({v.term for v in violations})),
            )
        lowered = request.acknowledgement_text.casefold()
        causal = [term for term in CAUSAL_LANGUAGE_TERMS if term in lowered]
        if causal:
            raise AcknowledgementError(
                "causal_language",
                "The acknowledgement text contains causal or change language: "
                + ", ".join(causal),
            )

    def _check_duplicates(self, request: AcknowledgementRequest) -> None:
        if request.acknowledgement_id is not None:
            for existing in self.store.list_for_learner(request.learner_id):
                if existing.acknowledgement_id == request.acknowledgement_id:
                    raise AcknowledgementError(
                        "conflict",
                        "The acknowledgement id conflicts with an existing record.",
                    )
        target_key = (
            request.source_kind,
            frozenset(request.source_evidence_ids),
        )
        for existing in self.store.list_for_learner(request.learner_id):
            existing_key = (
                existing.source_kind,
                frozenset(existing.source_evidence_ids),
            )
            if existing_key == target_key:
                raise AcknowledgementError(
                    "duplicate_acknowledgement",
                    "This evidence set is already acknowledged for this learner.",
                )

    @staticmethod
    def _invalid_source_record(source_id: str) -> None:
        raise AcknowledgementError(
            "invalid_source_record",
            f"Source record {source_id} is not admissible, descriptive, "
            "learner-facing evidence.",
        )


__all__ = [
    "ACKNOWLEDGEMENT_CONSENT_SCOPE",
    "AcknowledgementError",
    "AcknowledgementEvidencePort",
    "AcknowledgementService",
    "AcknowledgementStoreConflictError",
    "AcknowledgementStorePort",
    "CAUSAL_LANGUAGE_TERMS",
    "_stable_acknowledgement_id",
]
