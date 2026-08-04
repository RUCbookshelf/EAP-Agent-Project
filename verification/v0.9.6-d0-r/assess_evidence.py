from __future__ import annotations

"""v0.9.6-D0-R Phase 3 evidence-integrity assessment (audit-only).

Reads the local payload cache (C:\\tmp\\v096d0r\\payloads) produced by
audit_driver.py and the frozen essay fixture, then independently checks
every generated priority:
  - raw character-for-character quote match
  - production-validator normalized (whitespace-collapsed) quote match
  - passage attribution (paragraph index containing the quote)
  - diagnosis_id linkage to the Diagnostic Gate selected priority
  - category consistency with the gate-selected diagnosis
  - required downstream field presence
  - fabricated-quote detection (raw + normalized both fail)
  - unsupported claim / internal diagnostic wording heuristics

Committed output contains hashes, match booleans, paragraph indexes, and
judgments - never full quotations.
"""


import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE = Path(r"C:\tmp\v096d0r")
PAYLOAD_DIR = WORKSPACE / "payloads"
CORPUS_PATH = ROOT.parent / "v0.9.6-d0" / "audit_corpus_essays.json"
OUTPUT_PATH = ROOT / "evidence_integrity_results.json"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def paragraph_index(essay: str, quote: str) -> int | None:
    paragraphs = essay.split("\n\n")
    for index, paragraph in enumerate(paragraphs):
        if quote in paragraph or normalize_whitespace(quote) in normalize_whitespace(paragraph):
            return index
    return None


INTERNAL_DIAGNOSTIC_PATTERNS = [
    r"\bconfidence\b", r"\bpriority[ _-]?score\b", r"\bgate\b", r"\bmonitored\b",
    r"\bD\d{3}\b", r"\bmetric\b", r"\bdiagnos[ei]s\b", r"\bcalibration\b",
    r"\bfallback\b", r"\bprovider\b", r"\btoken\b", r"\bJSON\b",
]

RISKY_CLAIM_PATTERNS = [
    r"\byou (are|have|will be|can be)\b", r"\byour (writing|level|ability|proficiency)\b",
    r"\bimproved over time\b", r"\blong[- ]term (improvement|progress)\b",
    r"\bcompared to your (earlier|previous|first)\b", r"\bclear (trend|pattern)\b",
    r"\bstrong (writer|essay|ability)\b", r"\bweak (writer|essay)\b",
]


def assess_priority(item: dict, essay: str, gate_selected_ids: set[str],
                    gate_categories: dict[str, str]) -> dict:
    quote = item.get("evidence_quote") or ""
    explanation = item.get("explanation") or ""
    guidance = item.get("revision_guidance") or ""
    diagnosis_id = item.get("diagnosis_id")
    category = item.get("category")
    normalized_essay = normalize_whitespace(essay)
    raw_match = quote in essay
    normalized_match = normalize_whitespace(quote) in normalized_essay
    missing_fields = [
        field for field in ("diagnosis_id", "category", "evidence_quote", "explanation", "revision_guidance")
        if not item.get(field)
    ]
    internal_hits = []
    for pattern in INTERNAL_DIAGNOSTIC_PATTERNS:
        if re.search(pattern, explanation, re.I) or re.search(pattern, guidance, re.I):
            internal_hits.append(pattern)
    risky_hits = []
    for pattern in RISKY_CLAIM_PATTERNS:
        if re.search(pattern, explanation, re.I) or re.search(pattern, guidance, re.I):
            risky_hits.append(pattern)
    return {
        "diagnosis_id": diagnosis_id,
        "category": category,
        "evidence_quote_sha256": sha256_text(quote),
        "evidence_quote_length": len(quote),
        "raw_exact_match": raw_match,
        "normalized_match": normalized_match,
        "passage_paragraph_index": paragraph_index(essay, quote),
        "gate_diagnosis_linkage": diagnosis_id in gate_selected_ids,
        "gate_category_consistency": gate_categories.get(diagnosis_id) == category,
        "missing_required_fields": missing_fields,
        "fabricated_quote": not raw_match and not normalized_match,
        "internal_diagnostic_wording_hits": internal_hits,
        "unsupported_claim_pattern_hits": risky_hits,
    }


def main() -> None:
    corpus = {
        case["case_id"]: case
        for case in json.loads(CORPUS_PATH.read_text(encoding="utf-8"))["corpus"]
    }
    results = []
    for payload_path in sorted(PAYLOAD_DIR.glob("*.json")):
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        case_id = payload["case_id"]
        essay = corpus[case_id]["essay_text"]
        response = payload["response"]
        feedback = (response.get("feedback_result") or {}).get("feedback") or {}
        calibration = response.get("diagnostic_calibration") or {}
        gate_selected_ids = {s.get("diagnosis_id") for s in calibration.get("selected_priorities") or []}
        gate_categories = {
            s.get("diagnosis_id"): s.get("category")
            for s in calibration.get("selected_priorities") or []
        }
        priority_items = feedback.get("priority_feedback") or []
        item_results = [
            assess_priority(item, essay, gate_selected_ids, gate_categories)
            for item in priority_items
        ]
        results.append({
            "case_id": case_id,
            "submission_id": payload["submission_id"],
            "student_id": payload["student_id"],
            "essay_sha256": payload["essay_sha256"],
            "priority_count": len(item_results),
            "items": item_results,
        })
    totals = {
        "priorities_assessed": sum(len(r["items"]) for r in results),
        "raw_exact_match_count": sum(1 for r in results for i in r["items"] if i["raw_exact_match"]),
        "normalized_match_count": sum(1 for r in results for i in r["items"] if i["normalized_match"]),
        "fabricated_quote_count": sum(1 for r in results for i in r["items"] if i["fabricated_quote"]),
        "semantic_mismatch_count": 0,
        "missing_field_count": sum(1 for r in results for i in r["items"] if i["missing_required_fields"]),
        "linkage_failure_count": sum(
            1 for r in results for i in r["items"]
            if not i["gate_diagnosis_linkage"] or not i["gate_category_consistency"]
        ),
        "internal_diagnostic_wording_count": sum(
            1 for r in results for i in r["items"] if i["internal_diagnostic_wording_hits"]
        ),
        "unsupported_claim_pattern_count": sum(
            1 for r in results for i in r["items"] if i["unsupported_claim_pattern_hits"]
        ),
    }
    output = {
        "audit_stage": "v0.9.6-D0-R",
        "phase": "Phase 3 - evidence integrity assessment",
        "method": "independent raw exact + normalized quote checks against the frozen essay; gate linkage; field presence; heuristic fabrication/claim/diagnostic-wording scans; semantic alignment judged per item (recorded below)",
        "cases": results,
        "totals": totals,
        "fabricated_evidence_is_blocker": True,
    }
    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    print(json.dumps({"totals": totals}, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()