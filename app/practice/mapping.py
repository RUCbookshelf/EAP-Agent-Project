"""Priority-to-Practice mapping and provenance (v0.9.7-B WU2).

Production translation of exactly one persisted Feedback priority
(``feedback_records.feedback_json.priority_feedback[index]``) into a
validated Practice-target creation contract.

Frozen contract conventions (V0.9.7_B_SPEC.md section 4 / WU2):

- Authoritative source: the persisted submission bundle (essay + diagnosis +
  feedback records) loaded through the submission repository. Client input
  carries only trusted identifiers (student, submission, stable reference),
  never priority content such as category, explanation, or evidence quote.
- Stable priority reference: ``PRIO-{feedback_id}-{priority_index}`` where
  ``feedback_id`` is the persisted ``feedback_records.feedback_id`` and
  ``priority_index`` is ZERO-BASED, matching the list position inside the
  persisted ``priority_feedback`` array.
- Category mapping: the production copy of the demo TARGET_CODE_MAP; the
  demo script imports this module so the two cannot diverge.
- Evidence provenance: ``evidence_ids = [str(feedback_id)]``; the feedback
  record is the persisted evidence container for the priority quote.
- Unsupported/blank/malformed categories raise a controlled
  ``PriorityMappingError``; no target is fabricated.

The module is deterministic and free of Streamlit and rendered-text parsing.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.practice.ports import PracticeSubmissionReadPort


# Authoritative category -> supported Practice target code (WU2 production
# copy of the demo TARGET_CODE_MAP; scripts/demo_journey.py imports this).
TARGET_CODE_MAP: dict[str, str] = {
    "lexical_repetition": "lexical_repetition_local",
    "connective_use": "connective_overuse",
    "sentence_length_pattern": "long_sentence",
}

# Stable English learner-facing labels for supported categories. The
# existing locale keys (student_feedback_category_<category>) remain the
# localization source for UI rendering (WU4).
CATEGORY_LABELS: dict[str, str] = {
    "lexical_repetition": "Reduce lexical repetition",
    "connective_use": "Review connective use",
    "sentence_length_pattern": "Vary sentence length",
}

PRIORITY_REFERENCE_PREFIX = "PRIO"

_DEFAULT_DIAGNOSTIC_VERSION = "diagnostic-v0.6.1"
_DEFAULT_CONFIGURATION_VERSION = "config-v0.9.0"

_REQUIRED_PRIORITY_FIELDS = (
    "diagnosis_id",
    "category",
    "evidence_quote",
    "explanation",
    "revision_guidance",
)

_DIAGNOSIS_SIGNAL_KEYS = (
    "strengths",
    "improvement_priorities",
    "descriptive_signals",
    "raw_signals",
    "monitored_signals",
    "suppressed_signals",
)


class PriorityMappingError(Exception):
    """Controlled mapping failure with a stable machine-readable kind.

    Kinds: invalid_reference | cross_student | source_not_found |
    malformed_priority | unresolved_priority | unsupported_category.
    """

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


class PriorityContext(BaseModel):
    """Persisted priority context carried by the target contract.

    The PracticeTarget schema persists only its declared fields (extra is
    forbidden), so this context is not stored on the target; it remains
    re-resolvable from the feedback record through ``source_priority_id``.
    WU4 reads it for task rendering.
    """

    model_config = ConfigDict(extra="forbid")
    feedback_id: int
    priority_index: int
    category: str
    evidence_quote: str
    explanation: str
    revision_guidance: str
    prompt_version: str | None = None
    schema_version: str | None = None
    diagnosis_version: str | None = None
    label_key: str


class PriorityTargetContract(BaseModel):
    """Validated Practice-target creation contract produced by WU2 mapping."""

    model_config = ConfigDict(extra="forbid")
    student_id: str
    source_submission_id: int
    source_diagnosis_id: str
    source_priority_id: str
    target_code: str
    target_label: str
    evidence_ids: list[str] = Field(default_factory=list)
    diagnostic_gate_status: str = "selected"
    diagnostic_version: str = _DEFAULT_DIAGNOSTIC_VERSION
    configuration_version: str = _DEFAULT_CONFIGURATION_VERSION
    priority_context: PriorityContext


def normalize_category(category: str) -> str:
    """Conservative category normalization: strip and lowercase only."""
    return category.strip().lower() if isinstance(category, str) else ""


def map_category_to_target_code(category: str) -> str:
    """Deterministically map one category to its supported target code."""
    normalized = normalize_category(category)
    target_code = TARGET_CODE_MAP.get(normalized)
    if target_code is None:
        raise PriorityMappingError(
            "unsupported_category",
            f"Category '{category}' is not supported by any practice target.",
        )
    return target_code


def target_label_for_category(category: str) -> str:
    """Learner-facing label for one supported category."""
    normalized = normalize_category(category)
    label = CATEGORY_LABELS.get(normalized)
    if label is None:
        raise PriorityMappingError(
            "unsupported_category",
            f"Category '{category}' has no learner-facing practice label.",
        )
    return label


def build_stable_priority_reference(feedback_id: int, priority_index: int) -> str:
    """Stable zero-based reference: ``PRIO-{feedback_id}-{priority_index}``."""
    if isinstance(feedback_id, bool) or not isinstance(feedback_id, int) or feedback_id <= 0:
        raise PriorityMappingError(
            "invalid_reference", "feedback_id must be a positive integer.")
    if isinstance(priority_index, bool) or not isinstance(priority_index, int) or priority_index < 0:
        raise PriorityMappingError(
            "invalid_reference", "priority_index must be a non-negative integer.")
    return f"{PRIORITY_REFERENCE_PREFIX}-{feedback_id}-{priority_index}"


def parse_stable_priority_reference(reference: str) -> tuple[int, int]:
    """Parse a stable reference; reject malformed or fabricated values."""
    if not isinstance(reference, str):
        raise PriorityMappingError("invalid_reference", "Priority reference must be a string.")
    parts = reference.split("-")
    if len(parts) != 3 or parts[0] != PRIORITY_REFERENCE_PREFIX:
        raise PriorityMappingError("invalid_reference", "Malformed priority reference.")
    try:
        feedback_id = int(parts[1])
        priority_index = int(parts[2])
    except ValueError as exc:
        raise PriorityMappingError("invalid_reference", "Malformed priority reference.") from exc
    if str(feedback_id) != parts[1] or str(priority_index) != parts[2]:
        raise PriorityMappingError("invalid_reference", "Malformed priority reference.")
    if feedback_id <= 0 or priority_index < 0:
        raise PriorityMappingError("invalid_reference", "Malformed priority reference.")
    return feedback_id, priority_index


def _signals_from_diagnosis(diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for key in _DIAGNOSIS_SIGNAL_KEYS:
        items = diagnosis.get(key)
        if isinstance(items, list):
            signals.extend(item for item in items if isinstance(item, dict))
    return signals


def diagnosis_contains_id(diagnosis: dict[str, Any], diagnosis_id: str) -> bool:
    """True when the persisted diagnosis record contains the given signal ID."""
    return any(
        signal.get("diagnosis_id") == diagnosis_id
        for signal in _signals_from_diagnosis(diagnosis)
    )


def build_target_contract(
    bundle: dict[str, Any],
    *,
    student_id: str,
    feedback_id: int,
    priority_index: int,
) -> PriorityTargetContract:
    """Build the validated contract from one persisted submission bundle.

    Raises ``PriorityMappingError`` with a stable kind for every invalid,
    stale, malformed, cross-student, or cross-source relationship. Pure:
    no I/O, no Streamlit, deterministic.
    """
    if not isinstance(bundle, dict):
        raise PriorityMappingError("source_not_found", "Source submission bundle is missing.")
    if isinstance(priority_index, bool) or not isinstance(priority_index, int):
        raise PriorityMappingError(
            "invalid_reference", "priority_index must be a non-negative integer.")
    if priority_index < 0:
        raise PriorityMappingError(
            "invalid_reference", "priority_index must be a non-negative integer.")
    if bundle.get("student_id") != student_id:
        raise PriorityMappingError(
            "cross_student",
            "Source submission does not belong to the requested learner.",
        )
    persisted_feedback_id = bundle.get("feedback_id")
    if persisted_feedback_id is None:
        raise PriorityMappingError(
            "source_not_found",
            "No persisted feedback record exists for the source submission.",
        )
    if int(persisted_feedback_id) != int(feedback_id):
        raise PriorityMappingError(
            "unresolved_priority",
            "Priority reference does not match the persisted feedback record "
            "for the source submission.",
        )
    feedback = bundle.get("feedback")
    if not isinstance(feedback, dict):
        raise PriorityMappingError(
            "malformed_priority", "Persisted feedback structure is missing or malformed.")
    priorities = feedback.get("priority_feedback")
    if not isinstance(priorities, list):
        raise PriorityMappingError(
            "malformed_priority", "Persisted priority_feedback list is missing or malformed.")
    if priority_index < 0 or priority_index >= len(priorities):
        raise PriorityMappingError(
            "unresolved_priority",
            "Priority index is out of range for the persisted feedback record.",
        )
    item = priorities[priority_index]
    if not isinstance(item, dict):
        raise PriorityMappingError("malformed_priority", "Persisted priority item is malformed.")
    for field_name in _REQUIRED_PRIORITY_FIELDS:
        value = item.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise PriorityMappingError(
                "malformed_priority",
                f"Persisted priority item is missing required field '{field_name}'.",
            )
    category = normalize_category(item["category"])
    target_code = map_category_to_target_code(category)
    target_label = target_label_for_category(category)
    diagnosis = bundle.get("diagnosis")
    if not isinstance(diagnosis, dict):
        raise PriorityMappingError(
            "source_not_found",
            "No persisted diagnosis exists for the source submission.",
        )
    matched_signal = next(
        (
            signal
            for signal in _signals_from_diagnosis(diagnosis)
            if signal.get("diagnosis_id") == item["diagnosis_id"]
        ),
        None,
    )
    if matched_signal is None:
        raise PriorityMappingError(
            "unresolved_priority",
            "Priority diagnosis is not associated with the source submission.",
        )
    if normalize_category(matched_signal.get("category", "")) != category:
        raise PriorityMappingError(
            "unresolved_priority",
            "Priority category conflicts with the persisted diagnosis.",
        )
    reference = build_stable_priority_reference(int(persisted_feedback_id), priority_index)
    diagnosis_version = bundle.get("diagnosis_version")
    context = PriorityContext(
        feedback_id=int(persisted_feedback_id),
        priority_index=priority_index,
        category=category,
        evidence_quote=item["evidence_quote"],
        explanation=item["explanation"],
        revision_guidance=item["revision_guidance"],
        prompt_version=bundle.get("prompt_version"),
        schema_version=bundle.get("schema_version"),
        diagnosis_version=diagnosis_version,
        label_key=f"student_feedback_category_{category}",
    )
    return PriorityTargetContract(
        student_id=student_id,
        source_submission_id=int(bundle.get("essay_id", 0)),
        source_diagnosis_id=item["diagnosis_id"],
        source_priority_id=reference,
        target_code=target_code,
        target_label=target_label,
        evidence_ids=[str(persisted_feedback_id)],
        diagnostic_gate_status="selected",
        diagnostic_version=(
            str(diagnosis_version) if diagnosis_version else _DEFAULT_DIAGNOSTIC_VERSION
        ),
        configuration_version=_DEFAULT_CONFIGURATION_VERSION,
        priority_context=context,
    )


class PriorityPracticeMappingService:
    """Smallest WU3-ready entry point: resolve persisted priority to contract."""

    def __init__(self, submission_reader: PracticeSubmissionReadPort):
        self._submission_reader = submission_reader

    def resolve_target_contract(
        self,
        *,
        student_id: str,
        source_submission_id: int,
        source_priority_id: str,
    ) -> PriorityTargetContract:
        """Resolve and validate one persisted priority; never writes."""
        feedback_id, priority_index = parse_stable_priority_reference(source_priority_id)
        bundle = self._submission_reader.get_submission_bundle(source_submission_id)
        if bundle is None:
            raise PriorityMappingError("source_not_found", "Source submission not found.")
        return build_target_contract(
            bundle,
            student_id=student_id,
            feedback_id=feedback_id,
            priority_index=priority_index,
        )

    def resolve_target_contract_by_components(
        self,
        *,
        student_id: str,
        source_submission_id: int,
        priority_index: int,
    ) -> PriorityTargetContract:
        """Resolve one persisted priority from its reference components.

        Used by the WU4 explicit entry transfer: the Student UI carries only
        ``(source_submission_id, priority_index)``; the persisted feedback
        record id is resolved from the authoritative bundle and the stable
        reference is assembled here (never in UI code).
        """
        bundle = self._submission_reader.get_submission_bundle(source_submission_id)
        if bundle is None:
            raise PriorityMappingError("source_not_found", "Source submission not found.")
        if bundle.get("student_id") != student_id:
            raise PriorityMappingError(
                "cross_student",
                "Source submission does not belong to the requested learner.",
            )
        feedback_id = bundle.get("feedback_id")
        if feedback_id is None:
            raise PriorityMappingError(
                "source_not_found",
                "No persisted feedback record exists for the source submission.",
            )
        return build_target_contract(
            bundle,
            student_id=student_id,
            feedback_id=int(feedback_id),
            priority_index=priority_index,
        )
