"""WU-A - Student FeatureSnapshot harness (Stage 6, research-only).

Stage-6 WU-A provides a research harness that runs the SAME v0.1 feature
extractor (app/corpus/features.py) over student submissions and returns a
governed, versioned, numeric-only FeatureSnapshot with explicit eligibility
checks.

Licensing/design constraints (CORPUS-LICENSING-REVIEW permitted-use matrix,
scoped UD-04 resolution):

- The snapshot is a NON-RECONSTRUCTIVE AGGREGATE ARTIFACT: only numbers and
  statuses are retained; the raw submission text is never stored, logged, or
  attached to the artifact (no textual examples/excerpts).
- learner_exposure is always "research_only"; nothing in this module creates
  a production/learner-facing path (research_only never silently transitions).
- Student input must not contain the corpus header format ("<STU...>" first
  line); the corpus batch adapter strips that header from corpus texts, and
  the student side must not smuggle it in.
- No raw SWECCL path or handle can enter the harness: inputs are plain text
  only, and submission identifiers reject path-shaped values.
- No proficiency/mastery/learning-gain vocabulary; no LLM computation (I5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.corpus.errors import CorpusInvalidRequestError
from app.corpus.features import (
    FEATURE_SET_VERSION,
    SPACY_MODEL,
    SPACY_MODEL_VERSION,
    FeatureSnapshot,
    extract_features,
)

STUDENT_PROCESSING_VERSION = "student-harness-v0.1.0"
STUDENT_SNAPSHOT_ARTIFACT_VERSION = "student-feature-snapshot-v0.1.0"
ARTIFACT_CLASS = "NON-RECONSTRUCTIVE AGGREGATE ARTIFACT"

# Corpus adapter header format (scripts/corpus_intelligence/build_stage5.py
# strips a first line starting with "<STU"). Student input must not contain it.
CORPUS_HEADER_PATTERN = re.compile(r"^\s*<STU", re.IGNORECASE)

# Path-shaped submission identifiers are rejected so that no raw path or
# handle can enter the harness (ADR-06 raw-path injection denial).
_PATH_CHARS = re.compile(r"[\\/:]")


@dataclass(frozen=True)
class EligibilityCheck:
    """One machine-checkable eligibility/version check result."""

    check_id: str
    description: str
    result: str  # "pass" | "warning" | "fail"
    detail: str


@dataclass(frozen=True)
class StudentFeatureSnapshot:
    """Versioned, numeric-only feature snapshot for one student submission.

    The raw submission text is deliberately absent: the artifact class is
    NON-RECONSTRUCTIVE AGGREGATE and text_retained is structurally False.
    """

    artifact_version: str
    submission_id: str | None
    feature_set_version: str
    processing_version: str
    extractor: str
    extractor_version: str
    features: tuple[FeatureSnapshot, ...]
    eligibility: tuple[EligibilityCheck, ...]
    learner_exposure: str = "research_only"
    artifact_class: str = ARTIFACT_CLASS
    text_retained: bool = False

    @property
    def provenance(self) -> dict:
        return {
            "artifact_version": self.artifact_version,
            "feature_set_version": self.feature_set_version,
            "processing_version": self.processing_version,
            "extractor": self.extractor,
            "extractor_version": self.extractor_version,
            "learner_exposure": self.learner_exposure,
            "artifact_class": self.artifact_class,
            "text_retained": self.text_retained,
        }


def _validate_submission_id(submission_id: str | None) -> None:
    if submission_id is None:
        return
    if not isinstance(submission_id, str) or not submission_id.strip():
        raise CorpusInvalidRequestError("submission_id must be a non-empty string or None")
    if _PATH_CHARS.search(submission_id):
        raise CorpusInvalidRequestError(
            "submission_id must not contain path separators (no raw path/handle injection)"
        )
    if submission_id.startswith("<"):
        raise CorpusInvalidRequestError("submission_id must not start with '<'")


def _eligibility_checks(text: str, snapshots: list[FeatureSnapshot]) -> list[EligibilityCheck]:
    checks: list[EligibilityCheck] = []
    checks.append(EligibilityCheck(
        "feature_set_version",
        "snapshot feature set version matches the registered corpus feature contract",
        "pass" if all(s.feature_set_version == FEATURE_SET_VERSION for s in snapshots) else "fail",
        f"required {FEATURE_SET_VERSION}",
    ))
    checks.append(EligibilityCheck(
        "corpus_header_absent",
        "student input must not contain the corpus header format (<STU...>)",
        "fail" if CORPUS_HEADER_PATTERN.search(text) else "pass",
        "first-line <STU...> header rejected by the harness",
    ))
    if not text.strip():
        checks.append(EligibilityCheck(
            "minimum_evidence",
            "empty input yields zero/ unavailable features and is not a usable submission",
            "warning",
            "no non-whitespace content",
        ))
    unavailable = [s.feature_id for s in snapshots if s.analysis_status == "unavailable"]
    if unavailable:
        checks.append(EligibilityCheck(
            "feature_availability",
            "all requested features must be available for a complete comparison",
            "warning",
            f"unavailable feature(s): {', '.join(unavailable)}",
        ))
    return tuple(checks)


def extract_student_features(
    text: str,
    submission_id: str | None = None,
    feature_ids: list[str] | None = None,
) -> StudentFeatureSnapshot:
    """Extract v0.1 features from one student submission (research-only).

    Raises CorpusInvalidRequestError for corpus-header input or
    path-shaped submission identifiers (fail closed). The raw text is not
    retained in the returned snapshot.
    """
    _validate_submission_id(submission_id)
    if CORPUS_HEADER_PATTERN.search(text):
        raise CorpusInvalidRequestError(
            "student input must not contain the corpus header format (<STU...>)"
        )
    snapshots = extract_features(text, feature_ids=feature_ids)
    checks = _eligibility_checks(text, snapshots)
    return StudentFeatureSnapshot(
        artifact_version=STUDENT_SNAPSHOT_ARTIFACT_VERSION,
        submission_id=submission_id,
        feature_set_version=FEATURE_SET_VERSION,
        processing_version=STUDENT_PROCESSING_VERSION,
        extractor=f"{SPACY_MODEL} {SPACY_MODEL_VERSION}",
        extractor_version=SPACY_MODEL_VERSION,
        features=tuple(snapshots),
        eligibility=tuple(checks),
    )


def recheck_eligibility(
    snapshot: StudentFeatureSnapshot,
    required_feature_set_version: str = FEATURE_SET_VERSION,
) -> tuple[EligibilityCheck, ...]:
    """Recompute the machine-checkable eligibility/version checks."""
    if snapshot.feature_set_version != required_feature_set_version:
        return (EligibilityCheck(
            "feature_set_version",
            "snapshot feature set version matches the required version",
            "fail",
            f"snapshot {snapshot.feature_set_version} != required {required_feature_set_version}",
        ),)
    return (
        EligibilityCheck(
            "feature_set_version",
            "snapshot feature set version matches the required version",
            "pass",
            f"required {required_feature_set_version}",
        ),
        EligibilityCheck(
            "no_text_retained",
            "the snapshot must remain a non-reconstructive aggregate artifact",
            "pass" if not snapshot.text_retained else "fail",
            "text_retained=False",
        ),
    )
