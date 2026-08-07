"""Tests for the domain/language discriminator (WU3-DISCRIMINATOR).

Covers:
- Closed vocabulary enforcement
- Server derivation for all current surfaces
- Advisory field handling (absent, matching, mismatch, invalid)
- Serialization round-trip on API
- Legacy payload compatibility (additive-only)
- Attribution rule/version presence in response
- Client cannot relabel historical records
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.domain.domain import Domain, Language, VALID_DOMAINS, VALID_LANGUAGES
from app.domain.attribution import (
    ATTRIBUTION_RULE_ID,
    ATTRIBUTION_RULE_VERSION,
    AttributionResult,
    derive_attribution,
    derive_domain,
    derive_language,
    validate_advisory,
    AdvisoryValidation,
)
from app.domain.validation import validate_domain_scope
from app.api.main import create_app
from app.config import Settings


# --- Helpers -----------------------------------------------------------------

def _make_test_client():
    """Create a test client with a temporary database."""
    tmp_dir = tempfile.mkdtemp()
    settings = Settings(
        database_path=str(Path(tmp_dir) / "test.db"),
        llm_provider="local",
        deepseek_api_key=None,
        deepseek_base_url="https://example.invalid",
        deepseek_model="deepseek-test",
    )
    app = create_app(settings)
    return TestClient(app)


# --- Vocabulary tests --------------------------------------------------------

class TestDomainVocabulary:
    def test_domain_enum_has_l2_and_academic(self):
        assert Domain.L2.value == "l2"
        assert Domain.ACADEMIC.value == "academic"

    def test_valid_domains_is_closed_set(self):
        assert VALID_DOMAINS == {"l2", "academic"}

    def test_language_enum_has_en(self):
        assert Language.EN.value == "en"

    def test_valid_languages_is_closed_set(self):
        assert VALID_LANGUAGES == {"en"}

    def test_domain_is_str_enum(self):
        assert isinstance(Domain.L2, str)
        assert Domain.L2 == "l2"

    def test_language_is_str_enum(self):
        assert isinstance(Language.EN, str)
        assert Language.EN == "en"


class TestDomainScopeValidation:
    def test_valid_domain_returns_enum(self):
        assert validate_domain_scope("l2") == Domain.L2
        assert validate_domain_scope("academic") == Domain.ACADEMIC

    def test_invalid_domain_raises(self):
        with pytest.raises(ValueError, match="unknown domain"):
            validate_domain_scope("nonexistent")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="unknown domain"):
            validate_domain_scope("")


# --- Derivation tests --------------------------------------------------------

class TestDerivation:
    def test_derive_domain_returns_l2(self):
        assert derive_domain() == Domain.L2

    def test_derive_domain_ignores_surface(self):
        assert derive_domain("submissions") == Domain.L2
        assert derive_domain("academic") == Domain.L2
        assert derive_domain(None) == Domain.L2

    def test_derive_language_returns_en(self):
        assert derive_language() == Language.EN

    def test_derive_language_ignores_surface(self):
        assert derive_language("submissions") == Language.EN
        assert derive_language(None) == Language.EN

    def test_derive_attribution_returns_l2_en(self):
        result = derive_attribution()
        assert result.domain == Domain.L2
        assert result.language == Language.EN
        assert result.rule_id == ATTRIBUTION_RULE_ID
        assert result.rule_version == ATTRIBUTION_RULE_VERSION

    def test_attribution_constants(self):
        assert ATTRIBUTION_RULE_ID == "domain-attribution-v0.1.0"
        assert ATTRIBUTION_RULE_VERSION == "0.1.0"

    def test_all_current_surfaces_derive_l2_en(self):
        for surface in ("submissions", "revisions", "practice", "research", None):
            result = derive_attribution(surface)
            assert result.domain == Domain.L2, f"surface={surface}"
            assert result.language == Language.EN, f"surface={surface}"


# --- Advisory validation tests -----------------------------------------------

class TestAdvisoryValidation:
    def test_both_absent_accepts(self):
        result = validate_advisory(None, None, derive_attribution())
        assert result.ok is True

    def test_matching_domain_accepts(self):
        result = validate_advisory("l2", None, derive_attribution())
        assert result.ok is True

    def test_matching_language_accepts(self):
        result = validate_advisory(None, "en", derive_attribution())
        assert result.ok is True

    def test_both_matching_accepts(self):
        result = validate_advisory("l2", "en", derive_attribution())
        assert result.ok is True

    def test_mismatched_domain_rejects(self):
        # "academic" is valid but mismatches the derived "l2"
        result = validate_advisory("academic", None, derive_attribution())
        assert result.ok is False
        assert "domain mismatch" in result.reason

    def test_invalid_domain_rejects(self):
        result = validate_advisory("nonexistent", None, derive_attribution())
        assert result.ok is False
        assert "invalid domain" in result.reason

    def test_invalid_language_rejects(self):
        # "zh" is not in VALID_LANGUAGES
        result = validate_advisory(None, "zh", derive_attribution())
        assert result.ok is False
        assert "invalid language" in result.reason

    def test_academic_domain_rejected_as_mismatch(self):
        result = validate_advisory("academic", "en", derive_attribution())
        assert result.ok is False
        assert "domain mismatch" in result.reason

    def test_mismatched_domain_with_valid_value(self):
        # "academic" is in VALID_DOMAINS but mismatches derived "l2"
        result = validate_advisory("academic", None, derive_attribution())
        assert result.ok is False
        assert "domain mismatch" in result.reason


# --- API serialization tests -------------------------------------------------

class TestAPISerialization:
    def test_legacy_payload_without_advisory_accepted(self):
        """Legacy payloads (no advisory fields) must still be accepted."""
        client = _make_test_client()
        payload = {
            "student_id": "STU-001",
            "writing_prompt": "Write an essay about climate change.",
            "essay_text": "Climate change is a significant global issue.",
        }
        resp = client.post("/api/v1/submissions", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        # Server-derived fields must be present.
        assert body["domain"] == "l2"
        assert body["language"] == "en"
        assert body["domain_attribution_rule"] == "domain-attribution-v0.1.0"
        assert body["domain_attribution_version"] == "0.1.0"

    def test_matching_advisory_accepted(self):
        """Matching advisory fields are accepted without re-attribution."""
        client = _make_test_client()
        payload = {
            "student_id": "STU-002",
            "writing_prompt": "Write about technology.",
            "essay_text": "Technology shapes modern life.",
            "advisory_domain": "l2",
            "advisory_language": "en",
        }
        resp = client.post("/api/v1/submissions", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["domain"] == "l2"
        assert body["language"] == "en"

    def test_mismatched_advisory_domain_returns_422(self):
        """Client advisory 'academic' must be rejected (no academic surface)."""
        client = _make_test_client()
        payload = {
            "student_id": "STU-003",
            "writing_prompt": "Write about education.",
            "essay_text": "Education is important.",
            "advisory_domain": "academic",
        }
        resp = client.post("/api/v1/submissions", json=payload)
        assert resp.status_code == 422

    def test_invalid_domain_string_returns_422(self):
        """Invalid domain string must be rejected."""
        client = _make_test_client()
        payload = {
            "student_id": "STU-004",
            "writing_prompt": "Write about history.",
            "essay_text": "History repeats itself.",
            "advisory_domain": "nonexistent",
        }
        resp = client.post("/api/v1/submissions", json=payload)
        assert resp.status_code == 422

    def test_invalid_language_string_returns_422(self):
        """Invalid language string must be rejected."""
        client = _make_test_client()
        payload = {
            "student_id": "STU-005",
            "writing_prompt": "Write about art.",
            "essay_text": "Art expresses emotions.",
            "advisory_language": "fr",
        }
        resp = client.post("/api/v1/submissions", json=payload)
        assert resp.status_code == 422

    def test_client_cannot_relabel_historical(self):
        """Client cannot relabel: advisory mismatch is always rejected."""
        client = _make_test_client()
        # First submission (accepted)
        payload1 = {
            "student_id": "STU-006",
            "writing_prompt": "Write about science.",
            "essay_text": "Science discovers truth.",
        }
        resp1 = client.post("/api/v1/submissions", json=payload1)
        assert resp1.status_code == 201
        sub_id = resp1.json()["submission_id"]

        # GET response does not expose domain fields (POST-only attribution).
        resp_get = client.get(f"/api/v1/submissions/{sub_id}")
        assert resp_get.status_code == 200

        # Attempt to relabel via POST with mismatched advisory -> 422.
        payload2 = {
            "student_id": "STU-006",
            "writing_prompt": "Write about science.",
            "essay_text": "Science discovers truth.",
            "advisory_domain": "academic",
        }
        resp2 = client.post("/api/v1/submissions", json=payload2)
        assert resp2.status_code == 422

    def test_submission_response_schema_includes_attribution_fields(self):
        """The SubmissionResponse schema must include all attribution fields."""
        from app.api.schemas import SubmissionResponse
        fields = set(SubmissionResponse.model_fields)
        assert "domain" in fields
        assert "language" in fields
        assert "domain_attribution_rule" in fields
        assert "domain_attribution_version" in fields

    def test_create_request_schema_includes_advisory_fields(self):
        """The SubmissionCreateRequest schema must include advisory fields."""
        from app.api.schemas import SubmissionCreateRequest
        fields = set(SubmissionCreateRequest.model_fields)
        assert "advisory_domain" in fields
        assert "advisory_language" in fields
