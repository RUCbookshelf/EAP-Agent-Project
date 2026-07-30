# Research export pipeline and data services
from __future__ import annotations

import csv, hashlib, json, os, random
from datetime import datetime, timezone
from pathlib import Path
from io import StringIO
from typing import Any

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


class ResearchDataService:
    """Core service for research export, PII scanning, human review, dataset splitting, and data quality."""

    def __init__(self, repository):
        self.repo = repository

    def schema(self) -> dict:
        return ResearchExportSchema().model_dump(mode='json')

    def preview(self, job: ExportJob) -> dict[str, Any]:
        records = self._collect(job.filter_spec)
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

    def _collect(self, filter_spec: ExportFilter) -> list[dict[str, Any]]:
        records = []
        students = self.repo.list_students_with_submissions()
        pseudonym_map = {}
        for idx, student in enumerate(students):
            pseudonym_map[student['student_id']] = _pseudonym(idx + 1)
            submissions = self.repo.list_student_submissions(student['student_id'])
            for sub in submissions:
                pid = sub['essay_id']
                pseudonym = pseudonym_map.get(sub['student_id'], 'UNKNOWN')
                records.append({
                    'export_schema_version': ExportSchemaVersion.V0_1.value,
                    'record_type': 'submission',
                    'record_id': f'SUB-{pid}',
                    'source_database_id': pid,
                    'student_pseudonym': pseudonym,
                    'submission_id': pid,
                    'revision_group_id': sub.get('revision_group_id'),
                    'source_timestamp': sub.get('submitted_at'),
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
        records = self._collect(job.filter_spec)
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
        sub = self.repo.get_submission_bundle(submission_id)
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
        if hasattr(self.repo, 'save_human_review'):
            self.repo.save_human_review(result)
        return result

    def get_human_reviews(self, target_type: str | None = None, target_id: str | None = None) -> list[dict]:
        if hasattr(self.repo, 'list_human_reviews'):
            return self.repo.list_human_reviews(target_type, target_id)
        return []

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
