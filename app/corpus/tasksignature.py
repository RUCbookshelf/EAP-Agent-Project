"""WU-B - TaskSignature reference-group matching (Stage 6, research-only).

Stage-6 WU-B maps a research submission's task properties (prompt, timed
status, genre) to an approved reference group through the Stage-5
deterministic fallback hierarchy (prompt+timed -> prompt -> genre+timed ->
genre -> UNAVAILABLE), with explicit unmatched states.

Constraints:
- Same FeatureSetVersion enforcement: every match result carries the
  required feature set version; comparison (WU-C) refuses version mismatch.
- Explicit unmatched states: incomplete signatures, unknown tasks, and
  too-small groups are reported as unmatched with a reason - never silently
  broadened without disclosure.
- Requested vs resolved group always disclosed; fallback disclosure is
  preserved from the Stage-5 boundary.
- learner_exposure is always "research_only"; NON-RECONSTRUCTIVE aggregate.
- No raw corpus path or handle can enter the matcher: inputs are semantic
  task values only (prompt id, timed status, genre).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.corpus.errors import CorpusInvalidRequestError, CorpusUnavailableError
from app.corpus.features import FEATURE_SET_VERSION
from app.corpus.groups import REFERENCE_GROUP_VERSION
from app.corpus.intelligence import CorpusIntelligence

TASK_MATCH_PROCESSING_VERSION = "task-matcher-v0.1.0"
TASK_MATCH_RESULT_ARTIFACT_VERSION = "task-match-result-v0.1.0"
ARTIFACT_CLASS = "NON-RECONSTRUCTIVE AGGREGATE ARTIFACT"

_PROMPT_PATTERN = re.compile(r"^(ARG|EXP)\d{2,}$")
_TIMED_VALUES = ("timed", "untimed")
_GENRE_VALUES = ("argumentative", "expository")


@dataclass(frozen=True)
class TaskSignature:
    """Semantic task properties of one research submission.

    Values are validated on construction; an incomplete signature (no prompt
    and no genre) is legal to construct and is reported as an explicit
    unmatched state by match().
    """

    prompt_id: str | None = None
    timed_status: str | None = None
    genre: str | None = None

    def __post_init__(self) -> None:
        if self.prompt_id is not None and not _PROMPT_PATTERN.match(self.prompt_id):
            raise CorpusInvalidRequestError(
                f"invalid prompt_id {self.prompt_id!r} (expected ARG##/EXP##)"
            )
        if self.timed_status is not None and self.timed_status not in _TIMED_VALUES:
            raise CorpusInvalidRequestError(
                f"invalid timed_status {self.timed_status!r} (expected timed/untimed)"
            )
        if self.genre is not None and self.genre not in _GENRE_VALUES:
            raise CorpusInvalidRequestError(
                f"invalid genre {self.genre!r} (expected argumentative/expository)"
            )

    def derived_genre(self) -> str | None:
        """Genre derived from the prompt prefix (ARG -> argumentative, EXP -> expository)."""
        if self.genre is not None:
            return self.genre
        if self.prompt_id is not None:
            return "argumentative" if self.prompt_id.startswith("ARG") else "expository"
        return None

    def as_dict(self) -> dict:
        return {
            "prompt_id": self.prompt_id,
            "timed_status": self.timed_status,
            "genre": self.genre,
            "genre_derived": self.derived_genre(),
        }


@dataclass(frozen=True)
class TaskMatchResult:
    """One versioned matching outcome with full disclosure."""

    artifact_version: str
    processing_version: str
    matched: bool
    requested_task: dict
    resolved_reference_group_id: str | None
    resolved_reference_group: str | None
    fallback_disclosure: str | None
    reference_group_version: str
    feature_set_version: str
    corpus_package_id: str
    manifest_hash: str
    unmatched_reason: str | None
    learner_exposure: str = "research_only"
    artifact_class: str = ARTIFACT_CLASS

    @property
    def provenance(self) -> dict:
        return {
            "artifact_version": self.artifact_version,
            "processing_version": self.processing_version,
            "feature_set_version": self.feature_set_version,
            "reference_group_version": self.reference_group_version,
            "corpus_package_id": self.corpus_package_id,
            "manifest_hash": self.manifest_hash,
            "learner_exposure": self.learner_exposure,
            "artifact_class": self.artifact_class,
        }


class ReferenceGroupMatcher:
    """Maps TaskSignature -> reference group via the Stage-5 boundary."""

    def __init__(
        self,
        intelligence: CorpusIntelligence | None = None,
        *,
        required_feature_set_version: str = FEATURE_SET_VERSION,
    ) -> None:
        self.intelligence = intelligence if intelligence is not None else CorpusIntelligence()
        self.required_feature_set_version = required_feature_set_version

    def match(self, signature: TaskSignature) -> TaskMatchResult:
        resource = self.intelligence.resource
        if signature.prompt_id is None and signature.genre is None:
            return TaskMatchResult(
                artifact_version=TASK_MATCH_RESULT_ARTIFACT_VERSION,
                processing_version=TASK_MATCH_PROCESSING_VERSION,
                matched=False,
                requested_task=signature.as_dict(),
                resolved_reference_group_id=None,
                resolved_reference_group=None,
                fallback_disclosure=None,
                reference_group_version=REFERENCE_GROUP_VERSION,
                feature_set_version=self.required_feature_set_version,
                corpus_package_id=resource.corpus_package_id,
                manifest_hash=resource.manifest_hash,
                unmatched_reason=(
                    "task signature incomplete: neither prompt_id nor genre supplied"
                ),
            )
        try:
            group, fallback = self.intelligence.resolve_reference_group(
                prompt_id=signature.prompt_id,
                timed_status=signature.timed_status,
                genre=signature.genre,
            )
        except CorpusUnavailableError as exc:
            return TaskMatchResult(
                artifact_version=TASK_MATCH_RESULT_ARTIFACT_VERSION,
                processing_version=TASK_MATCH_PROCESSING_VERSION,
                matched=False,
                requested_task=signature.as_dict(),
                resolved_reference_group_id=None,
                resolved_reference_group=None,
                fallback_disclosure=None,
                reference_group_version=REFERENCE_GROUP_VERSION,
                feature_set_version=self.required_feature_set_version,
                corpus_package_id=resource.corpus_package_id,
                manifest_hash=resource.manifest_hash,
                unmatched_reason=f"no reference group available: {exc}",
            )
        return TaskMatchResult(
            artifact_version=TASK_MATCH_RESULT_ARTIFACT_VERSION,
            processing_version=TASK_MATCH_PROCESSING_VERSION,
            matched=True,
            requested_task=signature.as_dict(),
            resolved_reference_group_id=group.reference_group_id,
            resolved_reference_group=group.selection_criteria,
            fallback_disclosure=fallback,
            reference_group_version=group.version,
            feature_set_version=self.required_feature_set_version,
            corpus_package_id=resource.corpus_package_id,
            manifest_hash=resource.manifest_hash,
            unmatched_reason=None,
        )
