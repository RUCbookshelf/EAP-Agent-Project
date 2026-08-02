# Research export pipeline and data services
from __future__ import annotations

import csv, hashlib, json, os, random
from datetime import datetime, timezone
from pathlib import Path
from io import StringIO
from typing import Any, Protocol, runtime_checkable

from app.research.scanner import scan_essay, redact_essay
from app.research.schemas import (
    DataQualityCategory, DataQualityItem, DataQualityReport,
    DatasetSplitManifest, DatasetSplitRecord,
    ExportFilter, ExportFormat, ExportJob, ExportJobStatus,
    ExportManifest, ExportRecord, ExportSchemaVersion,
    HumanReviewCreate, HumanReview, HumanReviewDecision, HumanReviewStatus, HumanReviewTarget,
    PiiAction, PiiCandidate, PiiCategory, PiiReview, PiiReviewStatus,
    PrivacyMode, ResearchExportSchema,
)

_EXPORT_BASE = 'research_exports'
_PSEUDONYM_PREFIX = 'P'


def _pseudonym(index: int) -> str:
    return f'{_PSEUDONYM_PREFIX}{index:06d}'


def _hash_file(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            sha.update(chunk)
    return sha.hexdigest()


def _csv_safe(value: Any) -> str:
    s = str(value) if value is not None else ''
    if s and s[0] in '@=+-':
        return chr(39) + s
    return s


@runtime_checkable
class ResearchSubmissionReadPort(Protocol):
    """Submission-owned read contract (ResearchDataService)."""

    def list_all_submissions(self): ...

    def list_student_submissions(self, student_id: str) -> list[dict[str, Any]]: ...

    def get_submission_bundle(self, essay_id: int) -> dict[str, Any] | None: ...


@runtime_checkable
class ResearchReviewPort(Protocol):
    """Research-owned human/PII review contract (ResearchDataService)."""

    def save_human_review(self, review) -> dict: ...

    def list_human_reviews(self, target_type: str | None = None, target_id: str | None = None) -> list[dict]: ...

    def apply_pii_review(self, submission_id: int, reviews: list) -> list[dict]: ...


@runtime_checkable
class ResearchExportReadPort(Protocol):
    """Research-owned Export Job read contract (ResearchDataService)."""

    def list_export_jobs(self) -> list[dict]: ...

    def get_export_job(self, export_id: str) -> dict | None: ...


class ResearchDataService:
    """Core service for research export, PII scanning, human review, dataset splitting, and data quality."""

    def __init__(
        self,
        submission_reader: ResearchSubmissionReadPort,
        review_repository: ResearchReviewPort,
        export_reader: ResearchExportReadPort,
    ):
        self.submission_reader = submission_reader
        self.review_repository = review_repository
        self.export_reader = export_reader

    def schema(self) -> dict:
        return ResearchExportSchema().model_dump(mode='json')

    def preview(self, job: ExportJob) -> dict[str, Any]:
        records = self._collect(job.filter_spec, job.privacy_mode)
        students = set(r.get('student_pseudonym', '') for r in records)
        return {
            'student_count': len(students),
            'essay_count': sum(1 for r in records if r['record_type'] == 'submission'),
            'included_count': len(records),
            'excluded_count': 0,
            'exclusion_reasons': [],
            'privacy_mode': job.privacy_mode.value,
            'formats': [f.value for f in job.formats],
        }

    def _collect(self, filter_spec: ExportFilter, privacy_mode: PrivacyMode | None = None) -> list[dict[str, Any]]:
        mode = privacy_mode or PrivacyMode.INTERNAL_RESEARCH
        records = []
        all_subs = self.submission_reader.list_all_submissions()
        students_seen = {}
        for sub in all_subs:
            sid = sub.get('student_id', '')
            if sid and sid not in students_seen:
                students_seen[sid] = {'student_id': sid}
        students_list = list(students_seen.values())
        pseudonym_map = {}
        for idx, student in enumerate(students_list):
            if mode == PrivacyMode.PSEUDONYMIZED:
                pseudonym_map[student['student_id']] = _pseudonym(idx + 1)
            submissions = self.submission_reader.list_student_submissions(student['student_id'])
            for sub in submissions:
                pid = sub['essay_id']
                if mode == PrivacyMode.INTERNAL_RESEARCH:
                    pseudonym = sub['student_id']
                elif mode == PrivacyMode.PSEUDONYMIZED:
                    pseudonym = pseudonym_map.get(sub['student_id'], 'UNKNOWN')
                else:
                    pseudonym = None
                records.append({
                    'export_schema_version': ExportSchemaVersion.V0_1.value,
                    'record_type': 'submission',
                    'record_id': f'SUB-{pid}',
                    'source_database_id': pid,
                    'student_pseudonym': pseudonym if mode != PrivacyMode.MINIMAL_ANONYMOUS else None,
                    'submission_id': pid,
                    'revision_group_id': sub.get('revision_group_id'),
                    'source_timestamp': (sub.get('submitted_at', '') or '')[:10] if mode == PrivacyMode.MINIMAL_ANONYMOUS else sub.get('submitted_at'),
                    'export_timestamp': datetime.now(timezone.utc).isoformat(),
                    'data_origin': 'system_generated',
                    'inclusion_status': 'included',
                    'payload': {
                        'writing_prompt': sub.get('writing_prompt', ''),
                        'genre': sub.get('genre', ''),
                        'draft_stage': sub.get('draft_stage', ''),
                        'timed': sub.get('timed', False),
                        'tool_use': sub.get('tool_use', 'none'),
                    },
                })
        return records

    def run_export(self, job: ExportJob, git_commit: str | None = None,
                   migration_version: int | None = None,
                   config_version: str | None = None) -> dict[str, Any]:
        ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
        export_dir = Path(_EXPORT_BASE) / f'export_{ts}'
        export_dir.mkdir(parents=True, exist_ok=True)
        records = self._collect(job.filter_spec, job.privacy_mode)
        record_counts = {}
        files = []

        if ExportFormat.JSONL in job.formats:
            p = export_dir / 'records.jsonl'
            with open(p, 'w', encoding='utf-8') as f:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + '\n')
            files.append(p); record_counts['jsonl'] = len(records)

        if ExportFormat.CSV in job.formats:
            p = export_dir / 'records.csv'
            if records:
                with open(p, 'w', encoding='utf-8-sig', newline='') as f:
                    w = csv.writer(f)
                    w.writerow(list(records[0].keys()))
                    for r in records:
                        w.writerow([_csv_safe(v) for v in r.values()])
            files.append(p); record_counts['csv'] = len(records)

        manifest = ExportManifest(
            export_id=job.export_id or 'EXP000001',
            created_at=datetime.now(timezone.utc).isoformat(),
            git_commit=git_commit,
            database_migration_version=migration_version,
            active_configuration_version=config_version,
            export_formats=[f.value for f in job.formats],
            export_scope='filtered',
            applied_filters=job.filter_spec.model_dump(mode='json'),
            included_record_counts=record_counts,
            excluded_record_counts={},
            privacy_mode=job.privacy_mode.value,
            removed_fields=[],
            generalized_fields=[],
            pseudonym_strategy=f'{_PSEUDONYM_PREFIX}NNNNNN (stable per batch)' if job.privacy_mode == PrivacyMode.PSEUDONYMIZED else None,
            hashing_strategy='SHA-256 per file',
            random_seed=None,
            files=[{'name': f.name, 'sha256': _hash_file(f)} for f in files],
            known_limitations=['PII scanner is regex-based and incomplete.'],
        )
        mp = export_dir / 'manifest.json'
        mp.write_text(manifest.model_dump_json(indent=2), encoding='utf-8')
        files.append(mp)
        return {
            'export_id': manifest.export_id,
            'status': ExportJobStatus.COMPLETED.value,
            'export_directory': str(export_dir),
            'file_count': len(files),
            'record_counts': record_counts,
            'manifest_path': str(mp),
            'manifest': manifest.model_dump(mode='json'),
        }

    def scan_pii(self, submission_id: int) -> list[dict[str, Any]]:
        sub = self.submission_reader.get_submission_bundle(submission_id)
        if not sub:
            raise LookupError('Submission not found')
        return scan_essay(submission_id, sub['essay_text'])

    def create_human_review(self, review: HumanReviewCreate) -> HumanReview:
        result = HumanReview(
            target_type=review.target_type, target_id=review.target_id,
            reviewer_id=review.reviewer_id, decision=review.decision,
            confidence=review.confidence, reason_code=review.reason_code,
            comment=review.comment, guideline_version=review.guideline_version,
        )
        self.review_repository.save_human_review(result)
        return result

    def get_human_reviews(self, target_type: str | None = None, target_id: str | None = None) -> list[dict]:
        return self.review_repository.list_human_reviews(target_type, target_id)

    def apply_pii_review(self, submission_id: int, reviews: list) -> list[dict]:
        """Apply PII review decisions to candidate rows for a submission."""
        sub = self.submission_reader.get_submission_bundle(submission_id)
        if not sub:
            raise LookupError("Submission not found")
        return self.review_repository.apply_pii_review(submission_id, reviews)

    def export_history(self) -> list[dict]:
        return self.export_reader.list_export_jobs()

    def export_status(self, export_id: str) -> dict:
        """Return export job status; unknown when no persisted job exists."""
        job = self.export_reader.get_export_job(export_id)
        if job:
            return job
        return {"export_id": export_id, "status": "unknown"}

    def create_dataset_split(self, payload: dict) -> dict:
        """Deterministic student-level split computation (no persistence; no schema change)."""
        students = payload.get("students") or payload.get("student_ids") or []
        seed = int(payload.get("seed", 20260730))
        train = float(payload.get("train_ratio", 0.7))
        val = float(payload.get("val_ratio", 0.15))
        test = float(payload.get("test_ratio", 0.15))
        if train <= 0 or val <= 0 or test <= 0 or abs(train + val + test - 1.0) > 1e-6:
            raise ValueError("train/val/test ratios must be positive and sum to 1")
        manifest = self.build_dataset_split(students, seed=seed, train=train, val=val, test=test)
        return manifest.model_dump(mode="json")

    def build_dataset_split(self, students: list[str], seed: int = 20260730,
                            train: float = 0.70, val: float = 0.15, test: float = 0.15) -> DatasetSplitManifest:
        rng = random.Random(seed)
        shuffled = list(students); rng.shuffle(shuffled)
        n = len(shuffled)
        n_train = max(1, int(n * train))
        n_val = max(1, int(n * val))
        n_test = n - n_train - n_val
        records = []
        for i, s in enumerate(shuffled):
            split = 'train' if i < n_train else ('validation' if i < n_train + n_val else 'test')
            records.append(DatasetSplitRecord(student_pseudonym=s, split=split))
        return DatasetSplitManifest(
            random_seed=seed, train_ratio=train, validation_ratio=val, test_ratio=test,
            student_count=n, train_count=n_train, validation_count=n_val, test_count=n_test,
            records=records,
        )

    def data_quality_report(self, filter_spec: ExportFilter | None = None) -> DataQualityReport:
        items = [
            DataQualityItem(category='accuracy_measure', status=DataQualityCategory.UNAVAILABLE,
                            count=1, description='Accuracy requires validated human annotations.'),
            DataQualityItem(category='syntactic_candidates', status=DataQualityCategory.REVIEW_REQUIRED,
                            count=0, description='Syntactic units are candidates, not validated measures.'),
        ]
        return DataQualityReport(items=items)
