"""No-normative-claims scanner tests (WU-D F7/F11; N7 banned vocabulary)."""

from __future__ import annotations

from app.learner.normative import (
    BANNED_NORMATIVE_TERMS,
    NormativeClaimsScanner,
    RISKY_ABILITY_PHRASES,
)
from app.shared.vocabularies import BANNED_LEARNER_LABELS


SCANNER = NormativeClaimsScanner()


class TestScannerEnglish:
    def test_banned_label_flagged(self) -> None:
        violations = SCANNER.scan_text("The learner achieved mastery of X.")
        assert any(v.term == "mastery" for v in violations)

    def test_proficiency_flagged(self) -> None:
        assert any(v.term == "proficiency" for v in SCANNER.scan_text(
            "This result implies proficiency."
        ))

    def test_learning_gain_flagged(self) -> None:
        assert any(v.term == "learning gain" for v in SCANNER.scan_text(
            "The practice produced a learning gain."
        ))

    def test_cefr_flagged(self) -> None:
        assert any(v.term == "cefr" for v in SCANNER.scan_text(
            "The learner is at CEFR B2."
        ))

    def test_risky_ability_phrase_flagged(self) -> None:
        assert any(v.term.casefold() in RISKY_ABILITY_PHRASES for v in SCANNER.scan_text(
            "Shows advanced proficiency in writing."
        ))

    def test_clean_text_has_no_violations(self) -> None:
        assert SCANNER.scan_text(
            "Feature value 412 was observed; reference comparison within "
            "declared group RG-014 (descriptive evidence only).",
        ) == []


class TestScannerChinese:
    def test_chinese_development_claim_flagged(self) -> None:
        assert SCANNER.scan_text("该学生的写作能力已经提升。") != []

    def test_chinese_clean_text_ok(self) -> None:
        assert SCANNER.scan_text("观察到词汇重复 3 次（仅描述性证据）。") == []


class TestDocumentationExemption:
    def test_prohibition_context_exempt_in_documentation_mode(self) -> None:
        text = (
            "This evidence does not establish language-ability improvement, "
            "decline, mastery, or regression."
        )
        assert SCANNER.scan_text(text, documentation=False) != []
        assert SCANNER.scan_text(text, documentation=True) == []

    def test_strict_mode_flags_even_prohibition_text(self) -> None:
        text = "Proficiency claims are never permitted."
        assert SCANNER.scan_text(text, documentation=False) != []
        assert SCANNER.scan_text(text, documentation=True) == []

    def test_mapping_scan_reports_locations(self) -> None:
        payload = {"summary": "The learner has mastered revision.", "ok": "clean"}
        violations = SCANNER.scan_mapping(payload)
        assert any(v.location == "summary" for v in violations)
        assert not any(v.location == "ok" for v in violations)


class TestVocabularyDisjointness:
    def test_banned_labels_covered_by_scanner_terms(self) -> None:
        assert BANNED_LEARNER_LABELS <= BANNED_NORMATIVE_TERMS

    def test_learner_vocabularies_never_use_banned_labels(self) -> None:
        from app.learner.evidence import EvidenceAdmissionStatus, ExposureClass
        from app.learner.practice_provenance import PracticeActivityStatus

        values = {s.value for s in EvidenceAdmissionStatus}
        values |= {c.value for c in ExposureClass}
        values |= {s.value for s in PracticeActivityStatus}
        assert values.isdisjoint(BANNED_LEARNER_LABELS)


class TestPracticeRecordScan:
    def test_activity_only_record_scans_clean(self) -> None:
        from datetime import datetime, timezone

        from app.learner.practice_provenance import (
            PRACTICE_ACTIVITY_LIMITATION,
            PracticeActivityStatus,
            PracticeProvenanceRecord,
        )

        record = PracticeProvenanceRecord(
            record_id="PP000001",
            student_id="S001",
            practice_target_id="PT000001",
            exercise_id="EX000001",
            exercise_version="exercise-v0.9.0",
            activity_status=PracticeActivityStatus.COMPLETED,
            occurred_at=datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc),
            limitations=[PRACTICE_ACTIVITY_LIMITATION],
        )
        # Prohibition text is F1-exempt in documentation mode, which is the
        # mode practice-provenance validation uses; strict mode flags the
        # limitation wording, proving the scanner still works.
        assert SCANNER.scan_pydantic(record, documentation=True) == []
        assert SCANNER.scan_pydantic(record) != []
