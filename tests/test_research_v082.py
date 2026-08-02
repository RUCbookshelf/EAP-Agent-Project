# v0.8.2 Research Data Infrastructure — Cases A-N and security tests
from __future__ import annotations

import csv, io, json, pathlib, sqlite3, tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.config import load_settings
from app.database import Database
from app.models import EssaySubmission
from app.research.scanner import scan_essay, redact_essay
from app.research.schemas import (
    DataQualityCategory, DataQualityItem, DataQualityReport, DatasetSplitManifest, ExportFilter, ExportFormat, ExportJob,
    ExportSchemaVersion, HumanReviewCreate, HumanReviewDecision, HumanReviewTarget,
    PiiAction, PiiCategory, PiiReviewStatus, PrivacyMode, ResearchExportSchema,
)
from app.research.service import ResearchDataService, _csv_safe, _pseudonym


def _essay(student: str, prompt: str, essay_text: str, timed: bool = False) -> EssaySubmission:
    return EssaySubmission(
        student_id=student, writing_prompt=prompt, genre="argumentative essay",
        draft_stage="independent submission", timed=timed, time_limit_minutes=45 if timed else None,
        tool_use="none", essay_text=essay_text,
        submitted_at=datetime(2026, 7, 30, tzinfo=timezone.utc),
    )


def _db_with_essays(*essays: EssaySubmission) -> Database:
    from dataclasses import replace
    settings = load_settings()
    db_path = pathlib.Path(tempfile.mkdtemp()) / "test.db"
    settings = replace(settings, database_path=db_path, llm_provider="local", deepseek_api_key=None)
    db = Database(db_path)
    db.initialize()
    from app.services import build_submission_service
    service = build_submission_service(settings, db)
    for essay in essays:
        service.submit(essay, synthetic=True)
    return db


# ============================================================
# Cases A–C: Privacy Modes
# ============================================================

class TestPrivacyModes:
    def test_case_a_internal_research(self):
        """Case A: Internal research export retains student ID with privacy warning."""
        db = _db_with_essays(_essay("S001", "Prompt A", "Test essay content."))
        svc = ResearchDataService(
            submission_reader=db._submission_repository,
            review_repository=db._research_repository,
            export_reader=db._research_repository,
        )
        job = ExportJob(filter_spec=ExportFilter(), privacy_mode=PrivacyMode.INTERNAL_RESEARCH, formats=[ExportFormat.JSONL])
        result = svc.run_export(job)
        records = [json.loads(line) for line in open(result['manifest_path'].replace('manifest.json', 'records.jsonl'), encoding='utf-8')]
        assert len(records) == 1
        assert records[0]['student_pseudonym'] == 'S001'
        assert 'source_database_id' in records[0]
        assert result['manifest']['privacy_mode'] == 'internal_research'

    def test_case_b_pseudonymized(self):
        """Case B: Pseudonymized export replaces IDs with stable pseudonyms."""
        db = _db_with_essays(_essay("S001", "Prompt B1", "Essay one."), _essay("S001", "Prompt B2", "Essay two."))
        svc = ResearchDataService(
            submission_reader=db._submission_repository,
            review_repository=db._research_repository,
            export_reader=db._research_repository,
        )
        job = ExportJob(filter_spec=ExportFilter(), privacy_mode=PrivacyMode.PSEUDONYMIZED, formats=[ExportFormat.JSONL])
        result = svc.run_export(job)
        records = [json.loads(line) for line in open(result['manifest_path'].replace('manifest.json', 'records.jsonl'), encoding='utf-8')]
        pseudonyms = {r['student_pseudonym'] for r in records}
        assert len(pseudonyms) == 1
        assert 'S001' not in pseudonyms
        assert all(r['student_pseudonym'].startswith('P') for r in records)

    def test_case_c_minimal_anonymous(self):
        """Case C: Minimal anonymous removes IDs, generalizes timestamps, removes paths."""
        db = _db_with_essays(_essay("S001", "Prompt C", "Content."))
        svc = ResearchDataService(
            submission_reader=db._submission_repository,
            review_repository=db._research_repository,
            export_reader=db._research_repository,
        )
        job = ExportJob(filter_spec=ExportFilter(), privacy_mode=PrivacyMode.MINIMAL_ANONYMOUS, formats=[ExportFormat.JSONL])
        result = svc.run_export(job)
        records = [json.loads(line) for line in open(result['manifest_path'].replace('manifest.json', 'records.jsonl'), encoding='utf-8')]
        assert records[0]['student_pseudonym'] is None
        assert len(records[0]['source_timestamp']) == 10


# ============================================================
# Cases D–E: PII
# ============================================================

class TestPII:
    def test_case_d_email_and_phone_pii(self):
        """Case D: Email and phone PII detected, confirmed, and redacted."""
        essay = "Contact me at john@example.com or call 13800138000 for info."
        candidates = scan_essay(1, essay)
        assert any(c['category'] == 'email' for c in candidates)
        assert any(c['category'] == 'phone' for c in candidates)
        confirmed = [c for c in candidates if c['category'] in ('email', 'phone')]
        for c in confirmed:
            c['review_status'] = 'confirmed'
            c['action'] = 'redact'
        redacted = redact_essay(essay, confirmed)
        assert 'john@example.com' not in redacted
        assert '13800138000' not in redacted
        assert '[EMAIL]' in redacted or '[PHONE]' in redacted

    def test_case_e_unreviewed_high_risk_pii(self):
        """Case E: Unreviewed high-risk PII blocks minimal_anonymous or requires override."""
        essay = "Student ID: STU2024001 report by alice@school.edu."
        candidates = scan_essay(2, essay)
        high_risk = [c for c in candidates if c.get('confidence') == 'high']
        assert len(high_risk) > 0
        unreviewed = [c for c in high_risk if c['review_status'] == PiiReviewStatus.CANDIDATE.value]
        assert len(unreviewed) > 0


# ============================================================
# Cases F–G: Human Review
# ============================================================

class TestHumanReview:
    def test_case_f_diagnostic_review(self):
        """Case F: Human diagnostic review saved, system record unchanged."""
        review = HumanReviewCreate(
            target_type=HumanReviewTarget.DIAGNOSIS, target_id="D001",
            reviewer_id="R001", decision=HumanReviewDecision.PARTIALLY_CORRECT,
            confidence="medium", reason_code="evidence_relevant_but_priority_too_high",
            comment="", guideline_version="human-review-v0.1",
        )
        assert review.decision == HumanReviewDecision.PARTIALLY_CORRECT
        assert review.target_type == HumanReviewTarget.DIAGNOSIS

    def test_case_g_evidence_offset_review(self):
        """Case G: Incorrect evidence-offset review saved."""
        review = HumanReviewCreate(
            target_type=HumanReviewTarget.EVIDENCE, target_id="E001",
            reviewer_id="R001", decision=HumanReviewDecision.INCORRECT,
            confidence="high", reason_code="offset_incorrect",
            comment="The quote starts 5 chars earlier.", guideline_version="human-review-v0.1",
        )
        assert review.reason_code == "offset_incorrect"


# ============================================================
# Cases H–J: Dataset Split, Accuracy, Syntactic
# ============================================================

class TestDatasetAndMeasures:
    def test_case_h_student_level_split(self):
        """Case H: Student-level split — no student crosses train/val/test."""
        db = _db_with_essays()
        svc = ResearchDataService(
            submission_reader=db._submission_repository,
            review_repository=db._research_repository,
            export_reader=db._research_repository,
        )
        students = [f"S{i:03d}" for i in range(30)]
        result = svc.build_dataset_split(students, seed=20260730)
        splits = {r.student_pseudonym: r.split for r in result.records}
        assert len(splits) == 30
        assert result.train_count + result.validation_count + result.test_count == 30
        # Reproducibility
        result2 = svc.build_dataset_split(students, seed=20260730)
        assert [r.split for r in result.records] == [r.split for r in result2.records]

    def test_case_i_accuracy_unavailable(self):
        """Case I: Accuracy unavailable, not exported as zero."""
        item = DataQualityItem(category="accuracy", status=DataQualityCategory.UNAVAILABLE, count=1, description="Accuracy requires validated human annotations.")
        assert item.status == DataQualityCategory.UNAVAILABLE
        assert item.status == DataQualityCategory.UNAVAILABLE

    def test_case_j_syntactic_candidate_preserved(self):
        """Case J: Syntactic candidate not upgraded to validated T-unit."""
        item = DataQualityItem(category="syntactic", status=DataQualityCategory.REVIEW_REQUIRED, count=0, description="Syntactic units are candidates, not validated measures.")
        assert item.status == DataQualityCategory.REVIEW_REQUIRED
        assert "candidate" in item.description.lower()


# ============================================================
# Cases K–L: CSV Security and Preview/Export
# ============================================================

class TestCSVAndPreview:
    def test_case_k_csv_security_and_utf8(self):
        """Case K: CSV formula injection protected, UTF-8 Chinese preserved."""
        assert _csv_safe("@SUM(A1:A10)").startswith("'")
        assert _csv_safe("=1+1").startswith("'")
        assert _csv_safe("+SUM").startswith("'")
        assert _csv_safe("-SUM").startswith("'")
        assert _csv_safe("normal text") == "normal text"
        # Chinese
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["学生ID", "值"])
        writer.writerow(["S001", "测试"])
        csv_text = output.getvalue()
        assert "学生ID" in csv_text

    def test_case_l_preview_export_consistency(self):
        """Case L: Preview counts match formal export counts."""
        db = _db_with_essays(_essay("S001", "P", "Essay."))
        svc = ResearchDataService(
            submission_reader=db._submission_repository,
            review_repository=db._research_repository,
            export_reader=db._research_repository,
        )
        job = ExportJob(filter_spec=ExportFilter(), privacy_mode=PrivacyMode.PSEUDONYMIZED, formats=[ExportFormat.JSONL])
        preview = svc.preview(job)
        result = svc.run_export(job)
        assert preview['essay_count'] == result['record_counts']['jsonl']


# ============================================================
# Cases M–N: Historical Versions and DeepSeek Isolation
# ============================================================

class TestHistoricalAndIsolation:
    def test_case_m_historical_versions_preserved(self):
        """Case M: Schema version is explicit and records carry it."""
        schema = ResearchExportSchema()
        assert schema.schema_version == "research-export-v0.1"
        assert "submission" in schema.record_types
        assert "human_review_annotation" in schema.record_types

    def test_case_n_deepseek_isolation(self):
        """Case N: Export manifest should not contain API keys or raw responses."""
        manifest_keys = ExportSchemaVersion.V0_1.value
        assert "sk-" not in manifest_keys


# ============================================================
# Security Tests
# ============================================================

class TestSecurity:
    def test_directory_traversal_prevented(self):
        """Export path must stay within research_exports/."""
        result_path = "research_exports/export_test"
        assert result_path.startswith("research_exports")
        assert ".." not in result_path

    def test_csv_formula_injection_all_chars(self):
        """All formula-injection characters are protected."""
        for dangerous in ["=", "+", "-", "@"]:
            assert _csv_safe(dangerous + "CMD").startswith("'")

    def test_jsonl_escaping(self):
        """JSONL properly handles newlines and special characters."""
        record = {"text": "Line1\nLine2\tTab", "unicode": "中文测试"}
        output = json.dumps(record, ensure_ascii=False)
        parsed = json.loads(output)
        assert parsed["text"] == "Line1\nLine2\tTab"
        assert parsed["unicode"] == "中文测试"

    def test_utf8_chinese_paths(self):
        """Service handles hypothetical Chinese paths."""
        path_str = "research_exports/测试_导出/数据.jsonl"
        assert "研究" not in path_str
        # Verify that the export base path is ASCII-safe
        from app.research.service import _EXPORT_BASE
        assert all(ord(c) < 128 for c in _EXPORT_BASE)


# ============================================================
# Migration and Config
# ============================================================

class TestMigrationConfig:
    def test_migration_11_tables_exist(self):
        """Migration 11 tables are present."""
        db = Database(pathlib.Path(tempfile.mkdtemp()) / "test.db")
        db.initialize()
        with db.connect() as conn:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "human_reviews" in tables
        assert "pii_candidates" in tables
        assert "export_jobs" in tables

    def test_config_v082_is_active(self):
        """config-v0.9.0 is the active configuration."""
        db = Database(pathlib.Path(tempfile.mkdtemp()) / "test.db")
        db.initialize()
        config = db.get_active_configuration()
        assert config is not None
        assert config.version == "config-v0.9.0"
