"""Academic Writing entity tests — focused happy-path + rejection matrix."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.academic.entities import (
    CitationLink,
    CitationVerificationRecord,
    Claim,
    ClaimEvidenceLink,
    EvidenceUnit,
    PaperSection,
    ResearchProject,
    ResearchQuestion,
    Source,
    _sha256_hex,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _project(**overrides) -> ResearchProject:
    defaults = dict(project_id="rp-abc123", title="Test Project")
    defaults.update(overrides)
    return ResearchProject(**defaults)


def _question(**overrides) -> ResearchQuestion:
    defaults = dict(
        question_id="rq-abc123",
        project_id="rp-abc123",
        question_text="How does X affect Y?",
    )
    defaults.update(overrides)
    return ResearchQuestion(**defaults)


def _source(**overrides) -> Source:
    defaults = dict(
        source_id="src-abc123",
        project_id="rp-abc123",
        title="Smith 2020",
        origin="learner_entered",
    )
    defaults.update(overrides)
    return Source(**defaults)


def _evidence(**overrides) -> EvidenceUnit:
    defaults = dict(
        evidence_id="ev-abc123",
        project_id="rp-abc123",
        source_id="src-abc123",
        source_version=1,
        kind="direct_quote",
        locator="p. 12",
        content="Some evidence text",
    )
    defaults.update(overrides)
    return EvidenceUnit(**defaults)


def _claim(**overrides) -> Claim:
    defaults = dict(
        claim_id="cl-abc123",
        project_id="rp-abc123",
        claim_text="X improves Y",
    )
    defaults.update(overrides)
    return Claim(**defaults)


def _section(**overrides) -> PaperSection:
    defaults = dict(
        section_id="sec-abc123",
        project_id="rp-abc123",
        section_title="Introduction",
    )
    defaults.update(overrides)
    return PaperSection(**defaults)


def _citation(**overrides) -> CitationLink:
    defaults = dict(
        citation_id="cit-abc123",
        project_id="rp-abc123",
        claim_id="cl-abc123",
        source_id="src-abc123",
    )
    defaults.update(overrides)
    return CitationLink(**defaults)


def _vr(**overrides) -> CitationVerificationRecord:
    defaults = dict(
        record_id="vr-abc123",
        citation_id="cit-abc123",
        rule_id="rule-1",
        rule_version="1.0",
        run_time=_NOW,
        result="unverified",
    )
    defaults.update(overrides)
    return CitationVerificationRecord(**defaults)


_ALL_BUILDERS = [_project, _question, _source, _evidence, _claim, _section, _citation, _vr]


# ===========================================================================
# 1. Happy-path tests
# ===========================================================================


class TestHappyPath:
    def test_project(self) -> None:
        p = _project()
        assert p.project_id == "rp-abc123"
        assert p.title == "Test Project"
        assert p.status == "active"
        assert p.research_scope is None
        assert p.created_at is not None
        assert p.updated_at is not None

    def test_question(self) -> None:
        q = _question()
        assert q.question_id == "rq-abc123"
        assert q.project_id == "rp-abc123"
        assert q.version == 1

    def test_source_defaults(self) -> None:
        s = _source()
        assert s.source_id == "src-abc123"
        assert s.availability == "active"
        assert s.version == 1
        assert s.file_hash is None
        assert s.source_text is None
        assert s.source_text_hash is None

    def test_source_with_text_hash(self) -> None:
        text = "Hello world"
        h = _sha256_hex(text)
        s = _source(source_text=text, source_text_hash=h)
        assert s.source_text_hash == h

    def test_evidence(self) -> None:
        e = _evidence()
        assert e.evidence_id == "ev-abc123"
        assert e.verification_status == "unverified"
        assert e.epistemic_status == "observed_descriptive"
        assert e.rq_ids == []
        assert e.learner_note is None
        assert e.model_interpretation is None

    def test_claim(self) -> None:
        c = _claim()
        assert c.claim_id == "cl-abc123"
        assert c.support_state == "unsupported"
        assert c.rq_ids == []
        assert c.section_ids == []
        assert c.evidence_links == []

    def test_section(self) -> None:
        sec = _section()
        assert sec.section_id == "sec-abc123"
        assert sec.status == "planned"
        assert sec.order == 0
        assert sec.parent_section_id is None
        assert sec.rq_ids == []

    def test_citation(self) -> None:
        cit = _citation()
        assert cit.citation_id == "cit-abc123"
        assert cit.verification_status == "unverified"
        assert cit.evidence_id is None
        assert cit.passage_span is None

    def test_verification_record(self) -> None:
        vr = _vr()
        assert vr.record_id == "vr-abc123"
        assert vr.result == "unverified"
        assert vr.run_time == _NOW
        assert vr.matched_spans == []
        assert vr.created_at is not None


# ===========================================================================
# 2. ID prefix validation
# ===========================================================================


class TestIdValidation:
    @pytest.mark.parametrize(
        "builder,field,bad_id",
        [
            (_project, "project_id", "xx-abc"),
            (_question, "question_id", "xx-abc"),
            (_question, "project_id", "xx-abc"),
            (_source, "source_id", "xx-abc"),
            (_source, "project_id", "xx-abc"),
            (_evidence, "evidence_id", "xx-abc"),
            (_evidence, "project_id", "xx-abc"),
            (_evidence, "source_id", "xx-abc"),
            (_claim, "claim_id", "xx-abc"),
            (_claim, "project_id", "xx-abc"),
            (_section, "section_id", "xx-abc"),
            (_section, "project_id", "xx-abc"),
            (_citation, "citation_id", "xx-abc"),
            (_citation, "project_id", "xx-abc"),
            (_citation, "claim_id", "xx-abc"),
            (_citation, "source_id", "xx-abc"),
            (_vr, "record_id", "xx-abc"),
            (_vr, "citation_id", "xx-abc"),
        ],
    )
    def test_wrong_prefix_rejected(
        self, builder, field: str, bad_id: str
    ) -> None:
        with pytest.raises(ValidationError, match="must match pattern"):
            builder(**{field: bad_id})

    def test_correct_prefix_accepted(self) -> None:
        p = _project(project_id="rp-Xy1_-Zz9")
        assert p.project_id == "rp-Xy1_-Zz9"

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _project(project_id="")


# ===========================================================================
# 3. Blank / max-length text fields
# ===========================================================================


class TestTextRejection:
    def test_project_title_blank(self) -> None:
        with pytest.raises(ValidationError):
            _project(title="   ")

    def test_project_title_too_long(self) -> None:
        with pytest.raises(ValidationError):
            _project(title="x" * 201)

    def test_question_text_blank(self) -> None:
        with pytest.raises(ValidationError):
            _question(question_text="  ")

    def test_source_title_blank(self) -> None:
        with pytest.raises(ValidationError):
            _source(title="  ")

    def test_evidence_locator_blank(self) -> None:
        with pytest.raises(ValidationError):
            _evidence(locator="  ")

    def test_evidence_content_blank(self) -> None:
        with pytest.raises(ValidationError):
            _evidence(content="  ")

    def test_claim_text_blank(self) -> None:
        with pytest.raises(ValidationError):
            _claim(claim_text="  ")

    def test_section_title_blank(self) -> None:
        with pytest.raises(ValidationError):
            _section(section_title="  ")


# ===========================================================================
# 4. extra="forbid" rejection
# ===========================================================================


class TestExtraForbid:
    @pytest.mark.parametrize("builder", _ALL_BUILDERS)
    def test_unknown_field_rejected(self, builder) -> None:
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            builder(unknown_field="oops")


# ===========================================================================
# 5. frozen=True rejection + model_copy
# ===========================================================================


class TestFrozen:
    def test_assignment_raises(self) -> None:
        p = _project()
        with pytest.raises(ValidationError):
            p.title = "New"  # type: ignore[misc]

    def test_source_new_version(self) -> None:
        s = _source(version=3)
        s2 = s.new_version(title="Updated")
        assert s2.version == 4
        assert s2.title == "Updated"
        assert s2.source_id == s.source_id


# ===========================================================================
# 6. Source hash consistency
# ===========================================================================


class TestSourceHashConsistency:
    def test_text_present_hash_matches(self) -> None:
        text = "Exact match text"
        h = _sha256_hex(text)
        s = _source(source_text=text, source_text_hash=h)
        assert s.source_text_hash == h

    def test_text_present_hash_mismatch(self) -> None:
        with pytest.raises(ValidationError, match="does not match"):
            _source(
                source_text="Hello",
                source_text_hash="a" * 64,
            )

    def test_text_absent_hash_present_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must be None"):
            _source(source_text=None, source_text_hash="a" * 64)

    def test_text_present_hash_absent_rejected(self) -> None:
        with pytest.raises(ValidationError, match="required when source_text"):
            _source(source_text="Hello", source_text_hash=None)

    def test_file_hash_bad_format(self) -> None:
        with pytest.raises(ValidationError, match="file_hash"):
            _source(file_hash="not-hex")

    def test_year_out_of_bounds(self) -> None:
        with pytest.raises(ValidationError):
            _source(year=999)
        with pytest.raises(ValidationError):
            _source(year=2101)


# ===========================================================================
# 7. Serialization round-trips
# ===========================================================================


class TestSerializationRoundTrip:
    @pytest.mark.parametrize(
        "builder,kwargs",
        [
            (_project, {}),
            (_question, {}),
            (_source, {}),
            (
                _source,
                {"source_text": "X", "source_text_hash": _sha256_hex("X")},
            ),
            (_evidence, {}),
            (_claim, {}),
            (_section, {}),
            (_citation, {}),
            (_vr, {}),
        ],
    )
    def test_round_trip(self, builder, kwargs: dict) -> None:
        obj = builder(**kwargs)
        json_str = obj.model_dump_json()
        cls = type(obj)
        restored = cls.model_validate_json(json_str)
        assert restored == obj


# ===========================================================================
# 8. List defaults
# ===========================================================================


class TestListDefaults:
    def test_evidence_rq_ids_default(self) -> None:
        e = _evidence()
        assert e.rq_ids == []
        assert e.rq_ids is not None

    def test_evidence_rq_ids_accept_valid(self) -> None:
        e = _evidence(rq_ids=["rq-abc", "rq-def123"])
        assert len(e.rq_ids) == 2

    def test_claim_rq_ids_reject_bad_prefix(self) -> None:
        with pytest.raises(ValidationError):
            _claim(rq_ids=["xx-bad"])

    def test_claim_section_ids_default(self) -> None:
        c = _claim()
        assert c.section_ids == []
        assert c.evidence_links == []

    def test_claim_section_ids_accept_valid(self) -> None:
        c = _claim(
            section_ids=["sec-abc123"],
            evidence_links=[ClaimEvidenceLink(evidence_id="ev-xyz999", link_type="supports")],
        )
        assert len(c.section_ids) == 1
        assert len(c.evidence_links) == 1
        assert c.evidence_links[0].link_type == "supports"

    def test_section_rq_ids_default(self) -> None:
        sec = _section()
        assert sec.rq_ids == []

    def test_duplicate_ids_rejected(self) -> None:
        with pytest.raises(ValidationError, match="duplicate"):
            _evidence(rq_ids=["rq-abc", "rq-abc"])

    def test_verification_record_matched_spans_default(self) -> None:
        vr = _vr()
        assert vr.matched_spans == []


# ===========================================================================
# 8b. Claim support-state invariants
# ===========================================================================


class TestClaimSupportState:
    def test_supported_without_links_rejected(self) -> None:
        with pytest.raises(ValidationError, match="requires at least one evidence link"):
            _claim(support_state="supported")

    def test_partially_supported_without_links_rejected(self) -> None:
        with pytest.raises(ValidationError, match="requires at least one evidence link"):
            _claim(support_state="partially_supported")

    def test_supported_requires_supports_link(self) -> None:
        with pytest.raises(ValidationError, match="requires at least one supports link"):
            _claim(
                support_state="supported",
                evidence_links=[
                    ClaimEvidenceLink(evidence_id="ev-abc123", link_type="contradicts")
                ],
            )

    def test_supported_with_supports_link_ok(self) -> None:
        c = _claim(
            support_state="supported",
            evidence_links=[
                ClaimEvidenceLink(evidence_id="ev-abc123", link_type="supports")
            ],
        )
        assert c.support_state == "supported"

    def test_partially_supported_with_link_ok(self) -> None:
        c = _claim(
            support_state="partially_supported",
            evidence_links=[
                ClaimEvidenceLink(evidence_id="ev-abc123", link_type="contextualizes")
            ],
        )
        assert c.support_state == "partially_supported"

    def test_unsupported_without_links_ok(self) -> None:
        assert _claim(support_state="unsupported").support_state == "unsupported"

    def test_undetermined_without_links_ok(self) -> None:
        assert _claim(support_state="undetermined").support_state == "undetermined"

    def test_none_title_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            _project(title=None)


# ===========================================================================
# 9. CitationVerificationRecord required fields
# ===========================================================================


class TestVerificationRecord:
    def test_run_time_required(self) -> None:
        with pytest.raises(ValidationError):
            CitationVerificationRecord(
                record_id="vr-abc123",
                citation_id="cit-abc123",
                rule_id="rule-1",
                rule_version="1.0",
                result="verified",
                # run_time missing
            )

    def test_result_required(self) -> None:
        with pytest.raises(ValidationError):
            CitationVerificationRecord(
                record_id="vr-abc123",
                citation_id="cit-abc123",
                rule_id="rule-1",
                rule_version="1.0",
                run_time=_NOW,
                # result missing
            )

    def test_source_revision_hash_bad_format(self) -> None:
        with pytest.raises(ValidationError, match="source_revision_hash"):
            _vr(source_revision_hash="not-hex")

    def test_created_by_default_system(self) -> None:
        assert _vr().created_by == "system"

    def test_verified_requires_hash(self) -> None:
        with pytest.raises(ValidationError, match="requires source_revision_hash"):
            _vr(result="verified", source_revision_hash=None)

    def test_verification_unavailable_requires_no_hash(self) -> None:
        with pytest.raises(ValidationError, match="to be None"):
            _vr(result="verification_unavailable", source_revision_hash="a" * 64)

    def test_unverified_result_allows_hash(self) -> None:
        vr = _vr(result="unverified", source_revision_hash="b" * 64)
        assert vr.result == "unverified"
