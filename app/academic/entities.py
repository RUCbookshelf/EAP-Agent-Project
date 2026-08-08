"""Academic Writing domain entities (Domain A).

Seven frozen Pydantic v2 models plus CitationVerificationRecord.
Self-contained: no imports from existing app modules.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Time helper
# ---------------------------------------------------------------------------


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Literal types
# ---------------------------------------------------------------------------

ProjectStatus = Literal["active", "archived"]
SourceOrigin = Literal["learner_entered", "imported_file"]
SourceAvailability = Literal["active", "unavailable", "removed"]
EvidenceKind = Literal["direct_quote", "learner_paraphrase"]
EvidenceVerificationStatus = Literal["verified", "unverified", "verification_unavailable"]
EpistemicStatus = Literal[
    "observed_descriptive", "gated_inference", "recommendation", "outcome_claim"
]
ClaimSupportState = Literal[
    "supported", "partially_supported", "unsupported", "undetermined"
]
ClaimEvidenceLinkType = Literal["supports", "contradicts", "contextualizes", "related"]
PaperSectionStatus = Literal["planned", "drafted", "reviewed"]
CitationVerificationStatus = Literal["verified", "unverified", "verification_unavailable"]
VerificationResult = Literal["verified", "unverified", "verification_unavailable"]


# ---------------------------------------------------------------------------
# ID prefix → regex helpers
# ---------------------------------------------------------------------------

_ID_PATTERN_TEMPLATE = r"^{prefix}-[A-Za-z0-9][A-Za-z0-9_-]{{0,63}}$"

_PREFIXES: dict[str, str] = {
    "rp": "rp",
    "rq": "rq",
    "src": "src",
    "ev": "ev",
    "cl": "cl",
    "sec": "sec",
    "cit": "cit",
    "vr": "vr",
}

_ID_PATTERNS: dict[str, re.Pattern[str]] = {
    name: re.compile(_ID_PATTERN_TEMPLATE.format(prefix=pfx))
    for name, pfx in _PREFIXES.items()
}


def _id_validator(field_name: str, prefix_key: str):
    """Return a field_validator that enforces prefix-NNN pattern on *field_name*."""
    pattern = _ID_PATTERNS[prefix_key]

    @field_validator(field_name, mode="before")
    @classmethod
    def _validate(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError(f"{field_name} must be a string")
        if not pattern.match(v):
            raise ValueError(
                f"{field_name} must match pattern {pattern.pattern}; got {v!r}"
            )
        return v

    return _validate


def _list_id_validator(field_name: str, prefix_key: str):
    """Return a field_validator that checks each item in a list[str] matches prefix-NNN."""
    pattern = _ID_PATTERNS[prefix_key]

    @field_validator(field_name, mode="before")
    @classmethod
    def _validate(cls, v: list[str]) -> list[str]:
        if not isinstance(v, list):
            raise ValueError(f"{field_name} must be a list")
        for i, item in enumerate(v):
            if not isinstance(item, str):
                raise ValueError(f"{field_name}[{i}] must be a string")
            if not pattern.match(item):
                raise ValueError(
                    f"{field_name}[{i}] must match pattern {pattern.pattern}; got {item!r}"
                )
        if len(set(v)) != len(v):
            raise ValueError(f"{field_name} must not contain duplicate ids")
        return v

    return _validate


def _strip_validator(*field_names: str):
    """Return a field_validator that strips and rejects blank strings."""

    @field_validator(*field_names, mode="before")
    @classmethod
    def _validate(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError(f"{field_names} must be a string")
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    return _validate


_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


class ResearchProject(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    title: str
    research_scope: str | None = None
    status: ProjectStatus = "active"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    _validate_project_id = _id_validator("project_id", "rp")
    _validate_title = _strip_validator("title")

    @field_validator("title")
    @classmethod
    def _title_length(cls, v: str) -> str:
        if len(v) > 200:
            raise ValueError("title must be at most 200 characters")
        return v

    @field_validator("research_scope")
    @classmethod
    def _scope_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 2000:
            raise ValueError("research_scope must be at most 2000 characters")
        return v


class ResearchQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    question_id: str
    project_id: str
    question_text: str
    version: int = 1
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    _validate_question_id = _id_validator("question_id", "rq")
    _validate_project_id = _id_validator("project_id", "rp")
    _validate_question_text = _strip_validator("question_text")

    @field_validator("question_text")
    @classmethod
    def _qt_length(cls, v: str) -> str:
        if len(v) > 1000:
            raise ValueError("question_text must be at most 1000 characters")
        return v

    @field_validator("version")
    @classmethod
    def _version_ge1(cls, v: int) -> int:
        if v < 1:
            raise ValueError("version must be >= 1")
        return v


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    project_id: str
    title: str
    authors: str | None = None
    year: int | None = None
    publication: str | None = None
    doi: str | None = None
    source_type: str | None = None
    origin: SourceOrigin
    availability: SourceAvailability = "active"
    file_name: str | None = None
    file_hash: str | None = None
    source_text: str | None = None
    source_text_hash: str | None = None
    version: int = 1
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    _validate_source_id = _id_validator("source_id", "src")
    _validate_project_id = _id_validator("project_id", "rp")
    _validate_title = _strip_validator("title")

    @field_validator("title")
    @classmethod
    def _title_length(cls, v: str) -> str:
        if len(v) > 500:
            raise ValueError("title must be at most 500 characters")
        return v

    @field_validator("authors")
    @classmethod
    def _authors_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 500:
            raise ValueError("authors must be at most 500 characters")
        return v

    @field_validator("year")
    @classmethod
    def _year_bounds(cls, v: int | None) -> int | None:
        if v is not None and (v < 1000 or v > 2100):
            raise ValueError("year must be between 1000 and 2100")
        return v

    @field_validator("publication")
    @classmethod
    def _pub_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 500:
            raise ValueError("publication must be at most 500 characters")
        return v

    @field_validator("doi")
    @classmethod
    def _doi_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 200:
            raise ValueError("doi must be at most 200 characters")
        return v

    @field_validator("source_type")
    @classmethod
    def _stype_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 100:
            raise ValueError("source_type must be at most 100 characters")
        return v

    @field_validator("file_name")
    @classmethod
    def _fname_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 255:
            raise ValueError("file_name must be at most 255 characters")
        return v

    @field_validator("file_hash")
    @classmethod
    def _fhash_format(cls, v: str | None) -> str | None:
        if v is not None and not _HEX64.match(v):
            raise ValueError("file_hash must be a 64-character lowercase hex string")
        return v

    @field_validator("version")
    @classmethod
    def _version_ge1(cls, v: int) -> int:
        if v < 1:
            raise ValueError("version must be >= 1")
        return v

    @model_validator(mode="after")
    def _source_text_hash_consistency(self) -> Source:
        if self.source_text is not None and self.source_text_hash is None:
            raise ValueError(
                "source_text_hash is required when source_text is present"
            )
        if self.source_text is not None and self.source_text_hash is not None:
            expected = _sha256_hex(self.source_text)
            if self.source_text_hash != expected:
                raise ValueError(
                    "source_text_hash does not match sha256(source_text)"
                )
        if self.source_text is None and self.source_text_hash is not None:
            raise ValueError(
                "source_text_hash must be None when source_text is absent"
            )
        return self

    def new_version(self, **updates) -> Source:
        """Return a new Source with version incremented and updated_at refreshed."""
        update_dict = dict(updates)
        update_dict["version"] = self.version + 1
        update_dict["updated_at"] = utc_now()
        return self.model_copy(update=update_dict)


class EvidenceUnit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str
    project_id: str
    source_id: str
    source_version: int
    kind: EvidenceKind
    locator: str
    content: str
    verification_status: EvidenceVerificationStatus = "unverified"
    epistemic_status: EpistemicStatus = "observed_descriptive"
    learner_note: str | None = None
    model_interpretation: str | None = None
    rq_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    _validate_evidence_id = _id_validator("evidence_id", "ev")
    _validate_project_id = _id_validator("project_id", "rp")
    _validate_source_id = _id_validator("source_id", "src")
    _validate_locator = _strip_validator("locator")
    _validate_content = _strip_validator("content")
    _validate_rq_ids = _list_id_validator("rq_ids", "rq")

    @field_validator("locator")
    @classmethod
    def _loc_length(cls, v: str) -> str:
        if len(v) > 500:
            raise ValueError("locator must be at most 500 characters")
        return v

    @field_validator("content")
    @classmethod
    def _content_length(cls, v: str) -> str:
        if len(v) > 20000:
            raise ValueError("content must be at most 20000 characters")
        return v

    @field_validator("source_version")
    @classmethod
    def _sv_ge1(cls, v: int) -> int:
        if v < 1:
            raise ValueError("source_version must be >= 1")
        return v

    @field_validator("learner_note")
    @classmethod
    def _ln_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 5000:
            raise ValueError("learner_note must be at most 5000 characters")
        return v

    @field_validator("model_interpretation")
    @classmethod
    def _mi_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 5000:
            raise ValueError("model_interpretation must be at most 5000 characters")
        return v


class ClaimEvidenceLink(BaseModel):
    """Typed claim-evidence relationship (frozen 05:4.4 link types)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str
    link_type: ClaimEvidenceLinkType
    created_at: datetime = Field(default_factory=utc_now)

    _validate_evidence_id = _id_validator("evidence_id", "ev")

class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str
    project_id: str
    claim_text: str
    support_state: ClaimSupportState = "unsupported"
    rq_ids: list[str] = Field(default_factory=list)
    section_ids: list[str] = Field(default_factory=list)
    evidence_links: list[ClaimEvidenceLink] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    _validate_claim_id = _id_validator("claim_id", "cl")
    _validate_project_id = _id_validator("project_id", "rp")
    _validate_claim_text = _strip_validator("claim_text")
    _validate_rq_ids = _list_id_validator("rq_ids", "rq")
    _validate_section_ids = _list_id_validator("section_ids", "sec")

    @field_validator("claim_text")
    @classmethod
    def _ct_length(cls, v: str) -> str:
        if len(v) > 5000:
            raise ValueError("claim_text must be at most 5000 characters")
        return v

    @model_validator(mode="after")
    def _support_state_consistency(self) -> Claim:
        if not self.evidence_links and self.support_state in ("supported", "partially_supported"):
            raise ValueError(
                "support_state supported/partially_supported requires at least one evidence link"
            )
        if self.support_state == "supported" and not any(
            link.link_type == "supports" for link in self.evidence_links
        ):
            raise ValueError("support_state supported requires at least one supports link")
        return self


class PaperSection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    section_id: str
    project_id: str
    section_title: str
    section_kind: str | None = None
    order: int = 0
    parent_section_id: str | None = None
    status: PaperSectionStatus = "planned"
    passage_span: str | None = None
    rq_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    _validate_section_id = _id_validator("section_id", "sec")
    _validate_project_id = _id_validator("project_id", "rp")
    _validate_section_title = _strip_validator("section_title")
    _validate_rq_ids = _list_id_validator("rq_ids", "rq")

    @field_validator("section_title")
    @classmethod
    def _st_length(cls, v: str) -> str:
        if len(v) > 500:
            raise ValueError("section_title must be at most 500 characters")
        return v

    @field_validator("section_kind")
    @classmethod
    def _sk_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 100:
            raise ValueError("section_kind must be at most 100 characters")
        return v

    @field_validator("order")
    @classmethod
    def _order_ge0(cls, v: int) -> int:
        if v < 0:
            raise ValueError("order must be >= 0")
        return v

    @field_validator("parent_section_id")
    @classmethod
    def _psi_pattern(cls, v: str | None) -> str | None:
        if v is not None and not _ID_PATTERNS["sec"].match(v):
            raise ValueError(
                f"parent_section_id must match pattern {_ID_PATTERNS['sec'].pattern}; got {v!r}"
            )
        return v

    @field_validator("passage_span")
    @classmethod
    def _ps_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 500:
            raise ValueError("passage_span must be at most 500 characters")
        return v


class CitationLink(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    citation_id: str
    project_id: str
    claim_id: str
    source_id: str
    evidence_id: str | None = None
    passage_span: str | None = None
    verification_status: CitationVerificationStatus = "unverified"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    _validate_citation_id = _id_validator("citation_id", "cit")
    _validate_project_id = _id_validator("project_id", "rp")
    _validate_claim_id = _id_validator("claim_id", "cl")
    _validate_source_id = _id_validator("source_id", "src")

    @field_validator("evidence_id")
    @classmethod
    def _ei_pattern(cls, v: str | None) -> str | None:
        if v is not None and not _ID_PATTERNS["ev"].match(v):
            raise ValueError(
                f"evidence_id must match pattern {_ID_PATTERNS['ev'].pattern}; got {v!r}"
            )
        return v

    @field_validator("passage_span")
    @classmethod
    def _ps_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 500:
            raise ValueError("passage_span must be at most 500 characters")
        return v


class CitationVerificationRecord(BaseModel):
    """D-32 append-only verification record per CitationLink."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: str
    citation_id: str
    rule_id: str
    rule_version: str
    source_revision_hash: str | None = None
    matched_spans: list[str] = Field(default_factory=list)
    run_time: datetime  # always explicit, no default
    result: VerificationResult
    created_by: Literal["system", "learner"] = "system"
    created_at: datetime = Field(default_factory=utc_now)

    _validate_record_id = _id_validator("record_id", "vr")
    _validate_citation_id = _id_validator("citation_id", "cit")

    @field_validator("rule_id")
    @classmethod
    def _ri_length(cls, v: str) -> str:
        if len(v) > 100:
            raise ValueError("rule_id must be at most 100 characters")
        return v

    @field_validator("rule_id")
    @classmethod
    def _ri_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("rule_id must not be blank")
        return v

    @field_validator("rule_version")
    @classmethod
    def _rv_length(cls, v: str) -> str:
        if len(v) > 100:
            raise ValueError("rule_version must be at most 100 characters")
        return v

    @field_validator("rule_version")
    @classmethod
    def _rv_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("rule_version must not be blank")
        return v

    @field_validator("source_revision_hash")
    @classmethod
    def _srh_format(cls, v: str | None) -> str | None:
        if v is not None and not _HEX64.match(v):
            raise ValueError(
                "source_revision_hash must be a 64-character lowercase hex string"
            )
        return v

    @model_validator(mode="after")
    def _result_hash_consistency(self) -> CitationVerificationRecord:
        if self.result == "verified" and self.source_revision_hash is None:
            raise ValueError("verified result requires source_revision_hash")
        if self.result == "verification_unavailable" and self.source_revision_hash is not None:
            raise ValueError(
                "verification_unavailable result requires source_revision_hash to be None"
            )
        return self
