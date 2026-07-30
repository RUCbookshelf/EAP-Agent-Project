# PII scanner — conservative regex/dictionary-based detection. Not claimed as complete or reliable.
from __future__ import annotations

import re
from typing import Any

from .schemas import PiiCandidate, PiiCategory, PiiReviewStatus

_RULES: list[tuple[PiiCategory, 're.Pattern', str, str]] = [
    (PiiCategory.EMAIL, re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'), 'pii-email-v0.1', 'high'),
    (PiiCategory.PHONE, re.compile(r'(?:\+?86[\s-]?)?1[3-9]\d{9}'), 'pii-phone-cn-v0.1', 'high'),
    (PiiCategory.PHONE, re.compile(r'(?:\+\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'), 'pii-phone-us-v0.1', 'medium'),
    (PiiCategory.STUDENT_ID, re.compile(r'(?:student[_\s]?id|学号)[\s:：]*[A-Za-z0-9_-]{4,20}', re.IGNORECASE), 'pii-student-id-v0.1', 'high'),
    (PiiCategory.SOCIAL_HANDLE, re.compile(r'@[\w.]{3,30}'), 'pii-social-v0.1', 'low'),
]

_MARKERS = {
    PiiCategory.PERSON: '[PERSON]', PiiCategory.EMAIL: '[EMAIL]',
    PiiCategory.PHONE: '[PHONE]', PiiCategory.INSTITUTION: '[INSTITUTION]',
    PiiCategory.LOCATION: '[LOCATION]', PiiCategory.STUDENT_ID: '[STUDENT_ID]',
    PiiCategory.SOCIAL_HANDLE: '[SOCIAL_HANDLE]',
}

def scan_essay(submission_id: int, essay_text: str) -> list[dict[str, Any]]:
    candidates = []
    seen = set()
    for category, pattern, rule_id, confidence in _RULES:
        for m in pattern.finditer(essay_text):
            span = (m.start(), m.end())
            if span in seen: continue
            seen.add(span)
            candidates.append(dict(
                submission_id=submission_id, category=category.value,
                start_offset=m.start(), end_offset=m.end(), matched_text=m.group(),
                confidence=confidence, rule_id=rule_id,
                review_status=PiiReviewStatus.CANDIDATE.value,
                action=None, reviewer_id=None, reviewed_at=None,
                replacement_marker=_MARKERS.get(category, '[REDACTED]'),
            ))
    return candidates

def redact_essay(essay_text: str, confirmed_pii: list[dict[str, Any]]) -> str:
    spans = sorted(confirmed_pii, key=lambda c: c['start_offset'], reverse=True)
    result = essay_text
    for c in spans:
        marker = c.get('replacement_marker', '[REDACTED]')
        result = result[:c['start_offset']] + marker + result[c['end_offset']:]
    return result
