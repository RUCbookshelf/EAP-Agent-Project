"""Research Governance Validators (WU11).

Department-owned, lightweight, deterministic, read-only validation for the
Research Evaluation & Data Governance foundation (research-governance-foundation-v0.1.0).

Validators implemented here:
  1. policy-file schema validation            (validate_policy_artifact / validate_policy_registry)
  2. prohibited measurement-claim vocabulary  (contains_prohibited_claim / validate_claim_template)
  3. reference-group eligibility              (validate_reference_group_eligibility)
  4. evaluation-protection checks             (validate_evaluation_protection)
  5. duplicate-group leakage checks           (validate_duplicate_group_leakage)
  6. version provenance checks                (validate_version_provenance)
  7. deterministic audit sampler              (select_sample)
  8. Stage-6 admissibility assessment         (assess_admissibility)

Pure standard library; no application, Corpus, Feedback, or UI imports.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]
FOUNDATION_DIR = REPO_ROOT / "docs" / "departments" / "research-evaluation-governance" / "foundation"
POLICY_DIR = FOUNDATION_DIR / "policies"
L2_DATA_DIR = REPO_ROOT / "docs" / "corpus-intelligence" / "l2" / "data"
RD_DATA_DIR = REPO_ROOT / "docs" / "corpus-readiness" / "sweccl2" / "data"

POLICY_SCHEMA_PATH = POLICY_DIR / "policy_schema.json"

KNOWN_VERSIONS = {
    "corpus_package_id": "sweccl2-weccl20-v0.1.0",
    "manifest_hash": "0d8940ff84613807c11c0e492c61fb8d39fc1152a386061f9711a41487659eb9",
    "feature_set_version": "corpus-features-v0.1.0",
    "reference_group_version": "reference-groups-v0.1.0",
    "distribution_version": "reference-distributions-v0.1.0",
}

POLICY_ARTIFACTS = [
    ("corpus-use", "corpus_use_policy.json"),
    ("evaluation-protection", "evaluation_protection_policy.json"),
    ("duplicate-handling", "duplicate_policy.json"),
    ("reference-group-eligibility", "reference_group_eligibility_policy.json"),
    ("measurement-claim", "measurement_claim_policy.json"),
    ("stage6-evidence-admissibility", "stage6_evidence_admissibility_policy.json"),
    ("feedback-audit-sampling", "audit_sampling_policy.json"),
    ("evaluation-leakage", "evaluation_leakage_policy.json"),
]

FRAMEWORK_POLICY = {
    "policy_family": "evaluation-policy-versioning",
    "policy_id": "evaluation-policy-versioning",
    "policy_version": "evaluation-policy-versioning-v0.1.0",
}

# I1 naming contract (ARCH-07:27) - word-boundary banned tokens.
_BANNED_TOKEN_RE = re.compile(r"\b(?:level|score|ability|mastery|gain|cefr)\b", re.IGNORECASE)

# Frozen product wording exemption: "priority score" (and its field form
# priority_score) is the existing product field name (app/calibration/service.py)
# and a canonical claim template in 07; I1 applies to corpus-derived fields/UI
# strings, so this frozen term is exempt from the token check.
_FROZEN_PRIORITY_SCORE_RE = re.compile(r"priority[\s_]score", re.IGNORECASE)

# Explicit-prohibition context markers (I1 "except explicit prohibition text").
_PROHIBITION_MARKERS = (
    "does not establish",
    "does not mean",
    "does not show",
    "is not",
    "are not",
    "never",
    "prohibit",
    "without",
    "not a",
    "not evidence",
    "not a claim",
)

# Configuration positive-finding risky ability phrases
# (app/configuration/schemas.py positive_finding_risky_ability_phrases) plus
# documented policy additions (07 §4.2: mastered, the learner improved/declined).
RISKY_ABILITY_PHRASES = (
    "strong linguistic control",
    "advanced proficiency",
    "mastery",
    "mastered",
    "the learner improved",
    "the learner declined",
    "native-like",
    "superior writing ability",
    "high rhetorical awareness",
    "excellent command of english",
    "sophisticated writer",
    "high-level writer",
    "superior ability",
)

# Semantic learner-quality patterns prohibited in every claim class (07 §2).
_QUALITY_PATTERNS = (
    re.compile(r"\bthe learner\s+is\s+(a\s+)?(good|great|excellent|poor|weak|strong|advanced|superior|fluent|proficient)\s+writer\b", re.IGNORECASE),
    re.compile(r"\boutperforms peers\b", re.IGNORECASE),
    re.compile(r"\babove grade level\b", re.IGNORECASE),
    re.compile(r"\bhas mastered\b", re.IGNORECASE),
    re.compile(r"\bshows mastery\b", re.IGNORECASE),
    re.compile(r"\bis proficient\b", re.IGNORECASE),
    re.compile(r"\bdemonstrates advanced\b", re.IGNORECASE),
    re.compile(r"\bweak in\b", re.IGNORECASE),
    re.compile(r"\bstable weakness\b", re.IGNORECASE),
    re.compile(r"\brepetitive writer\b", re.IGNORECASE),
    re.compile(r"\bmeans you mastered\b", re.IGNORECASE),
    re.compile(r"\byou have learned\b", re.IGNORECASE),
    re.compile(r"\byour level\b", re.IGNORECASE),
)

# Required measurement anchors per evidence class (07 §2 templates).
_TEMPLATE_ANCHORS = {
    "observed_feature": ("word count", "density", "count", "ratio", "proportion", "tokens", "value is", "mean", "median", "percentile", "band", "at sentence", "quote", "length"),
    "reference_comparison": ("reference distribution", "reference group", "percentile", "percent", "band"),
    "diagnostic_inference": ("gate", "priority", "signal", "monitored", "admitted", "evidence"),
    "feedback_recommendation": ("priority", "revise", "practice", "activity completed", "recommend"),
    "longitudinal": ("comparable", "earlier", "previous", "across", "trend", "pattern"),
}

MIN_REFERENCE_N = 30
EXPECTED_GROUP_COUNT = 75
EXPECTED_DISTRIBUTION_COUNT = 1050
HOLDOUT_EXPECTED_TOTAL = 511
HOLDOUT_EXPECTED_SCORED = 270
HOLDOUT_EXPECTED_DUPLICATE = 240
HOLDOUT_EXPECTED_CORRUPT = 1

SAMPLER_VERSION = "audit-sampler-v0.1.0"
SYSTEMATIC_SAMPLE_CAP = 50
ON_DEMAND_SAMPLE_CAP = 20

PROVENANCE_FIELDS = (
    "reference_group_id",
    "feature_id",
    "feature_set_version",
    "reference_group_version",
    "distribution_version",
    "corpus_package_id",
    "manifest_hash",
)

SCORE_FIELD_MARKERS = ("rater", "average_score", "score")


# ---------------------------------------------------------------------------
# JSON schema validation (minimal draft-07 subset for policy_schema.json)
# ---------------------------------------------------------------------------

def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _schema_errors(value: Any, schema: dict, path: str = "$") -> list[str]:
    """Validate one value against a minimal JSON-schema draft-07 subset."""
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type is not None and not _matches_type(value, expected_type):
        errors.append(f"{path}: expected type '{expected_type}', got {type(value).__name__}")
        return errors
    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{path}: missing required property '{required}'")
        for key, item in value.items():
            if key in schema.get("properties", {}):
                errors.extend(_schema_errors(item, schema["properties"][key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected property '{key}'")
    if isinstance(value, list):
        items_schema = schema.get("items")
        if items_schema is not None:
            for index, item in enumerate(value):
                errors.extend(_schema_errors(item, items_schema, f"{path}[{index}]"))
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            errors.append(f"{path}: expected at least {min_items} items")
    if isinstance(value, str):
        pattern = schema.get("pattern")
        if pattern is not None and not re.search(pattern, value):
            errors.append(f"{path}: does not match pattern {pattern}")
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            errors.append(f"{path}: shorter than minLength {min_length}")
        if schema.get("format") == "date" and not _DATE_RE.match(value):
            errors.append(f"{path}: invalid date format")
    enum = schema.get("enum")
    if enum is not None and value not in enum:
        errors.append(f"{path}: value {value!r} not in enum {enum}")
    const = schema.get("const")
    if const is not None and value != const:
        errors.append(f"{path}: expected const {const!r}, got {value!r}")
    return errors


def load_policy_schema() -> dict:
    with open(POLICY_SCHEMA_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_policy_artifact(path: Path) -> dict:
    """Validate one policy JSON artifact against policy_schema.json + consistency rules."""
    result = {"path": str(path.relative_to(REPO_ROOT)), "valid": False, "errors": []}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        result["errors"].append(f"unreadable or invalid JSON: {exc}")
        return result
    schema = load_policy_schema()
    errors = _schema_errors(payload, schema)
    if not isinstance(payload, dict):
        result["errors"].extend(errors)
        return result
    policy_id = payload.get("policy_id", "")
    policy_version = payload.get("policy_version", "")
    semver_match = re.fullmatch(r"^[a-z0-9-]+-v([0-9]+\.[0-9]+\.[0-9]+)$", policy_version)
    if semver_match is None:
        errors.append("policy_version must be <slug>-v<major>.<minor>.<patch>")
    elif policy_version != f"{policy_id}-v{semver_match.group(1)}":
        errors.append("policy_version must equal policy_id + '-v' + semver")
    if payload.get("status") != "ratified":
        errors.append("foundation artifacts must be status=ratified")
    statements = payload.get("statements", [])
    if not statements:
        errors.append("at least one statement required")
    for statement in statements:
        if not isinstance(statement, dict):
            continue
        statement_id = statement.get("statement_id", "")
        if not re.fullmatch(r"^[A-Z][A-Z0-9-]+$", statement_id):
            errors.append(f"invalid statement_id {statement_id!r}")
        if not statement.get("evidence"):
            errors.append(f"statement {statement_id} has no evidence")
        if not statement.get("class"):
            errors.append(f"statement {statement_id} has no class")
    result["errors"] = errors
    result["valid"] = not errors
    return result


def validate_all_policy_artifacts() -> list[dict]:
    results = []
    for _family, filename in POLICY_ARTIFACTS:
        results.append(validate_policy_artifact(POLICY_DIR / filename))
    return results

# ---------------------------------------------------------------------------
# Measurement-claim guardrails (WU7)
# ---------------------------------------------------------------------------

def contains_prohibited_claim(text: str, *, prohibition_exempt: bool = False) -> list[str]:
    """Return prohibited-token/phrase hits in a claim-like string.

    - Word-boundary banned tokens per I1 (ARCH-07:27), with the frozen product
      term "priority score" exempt (documented in 07 §4).
    - Risky ability phrases (07 §4.2).
    - When prohibition_exempt=True (explicit prohibition text, e.g. the mandated
      HISTORY_LIMITATION disclaimer), hits inside a negation/prohibition context
      window are skipped, per I1's "except explicit prohibition text" exception.
    """
    findings: list[str] = []
    for match in _BANNED_TOKEN_RE.finditer(text):
        if _FROZEN_PRIORITY_SCORE_RE.search(text[max(0, match.start() - 12): match.end() + 8]):
            continue
        if prohibition_exempt and _in_prohibition_context(text, match.start()):
            continue
        findings.append(f"banned token '{match.group(0).lower()}'")
    lowered = text.lower()
    for phrase in RISKY_ABILITY_PHRASES:
        start = lowered.find(phrase)
        if start == -1:
            continue
        if prohibition_exempt and _in_prohibition_context(text, start):
            continue
        findings.append(f"risky ability phrase '{phrase}'")
    return findings


def _in_prohibition_context(text: str, position: int) -> bool:
    window = text[max(0, position - 70): position + 20].lower()
    return any(marker in window for marker in _PROHIBITION_MARKERS)


def validate_disclaimer_text(text: str) -> dict:
    """Validate mandated disclaimer/prohibition text (e.g. HISTORY_LIMITATION)."""
    findings = contains_prohibited_claim(text, prohibition_exempt=True)
    return {"permitted": not findings, "findings": findings}


def _quality_pattern_hits(text: str) -> list[str]:
    return [pattern.pattern for pattern in _QUALITY_PATTERNS if pattern.search(text)]


def validate_claim_template(text: str, evidence_class: str) -> dict:
    """Check a statement against 07 templates for one evidence class.

    A claim is permitted only when it carries the class measurement anchor,
    contains no prohibited vocabulary (without exemption), and makes no
    learner-quality assertion.
    """
    findings = contains_prohibited_claim(text)
    if evidence_class == "learning_outcome":
        findings.append("learning outcome claims are reserved; none permitted today")
    else:
        anchors = _TEMPLATE_ANCHORS.get(evidence_class, ())
        lowered = text.lower()
        if anchors and not any(anchor in lowered for anchor in anchors):
            findings.append(f"missing required {evidence_class} measurement anchor")
    quality_hits = _quality_pattern_hits(text)
    findings.extend(f"prohibited quality assertion: {pattern}" for pattern in quality_hits)
    return {"evidence_class": evidence_class, "permitted": not findings, "findings": findings}


def validate_claim_text(text: str, evidence_class: str) -> dict:
    """Backward-compatible wrapper: template validation per evidence class."""
    return validate_claim_template(text, evidence_class)


# ---------------------------------------------------------------------------
# Corpus artifact readers (read-only, cached)
# ---------------------------------------------------------------------------

def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    # utf-8-sig: readiness CSVs carry a UTF-8 BOM in the first header cell.
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


@lru_cache(maxsize=1)
def load_membership() -> dict[str, set[str]]:
    rows = _read_csv_rows(L2_DATA_DIR / "reference_group_membership.csv")
    groups: dict[str, set[str]] = {}
    for row in rows:
        groups.setdefault(row["reference_group_id"], set()).add(row["document_id"])
    return groups


@lru_cache(maxsize=1)
def load_distributions() -> tuple[dict[str, Any], ...]:
    records = []
    with open(L2_DATA_DIR / "reference_distributions.jsonl", "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return tuple(records)


@lru_cache(maxsize=1)
def load_duplicate_report() -> tuple[dict[str, str], ...]:
    return tuple(_read_csv_rows(RD_DATA_DIR / "duplicate_report.csv"))


@lru_cache(maxsize=1)
def load_holdout_candidates() -> tuple[dict[str, str], ...]:
    return tuple(_read_csv_rows(RD_DATA_DIR / "holdout_candidates.csv"))


@lru_cache(maxsize=1)
def load_corpus_manifest() -> dict[str, dict[str, str]]:
    rows = _read_csv_rows(RD_DATA_DIR / "corpus_manifest.csv")
    return {row["document_id"]: row for row in rows}


def _member_stem(member: str) -> str:
    """Normalize a duplicate-report member to its document stem (Path(member).stem)."""
    return Path(member.strip()).stem


def _fold_duplicates() -> tuple[set[str], dict[str, set[str]], set[str], set[str]]:
    """Deterministic document-level fold (last-wins) of the scope-level duplicate report.

    Returns (affected_documents, groups_by_key, canonical_ids, non_canonical_ids).
    Group key = the row index of a document's last occurrence (fold semantics recorded
    in the methodology review: Path(member).stem normalization + last-wins).
    """
    rows = load_duplicate_report()
    last_row: dict[str, int] = {}
    for index, row in enumerate(rows):
        members = [member.strip() for member in row.get("members", "").split(",") if member.strip()]
        for member in members:
            last_row[_member_stem(member)] = index
    groups: dict[int, set[str]] = {}
    for document, row_index in last_row.items():
        groups.setdefault(row_index, set()).add(document)
    affected = set(last_row)
    canonical: set[str] = set()
    for members in groups.values():
        canonical.add(min(members))
    non_canonical = affected - canonical
    return affected, {str(key): value for key, value in groups.items()}, canonical, non_canonical


# ---------------------------------------------------------------------------
# WU6 / WU8 reference-group eligibility + provenance validators
# ---------------------------------------------------------------------------

def validate_reference_group_eligibility() -> dict:
    """Check the 75 approved groups / 1,050 distributions against policy 06."""
    findings: list[str] = []
    membership = load_membership()
    distributions = load_distributions()
    group_ids = sorted(membership)
    if len(group_ids) != EXPECTED_GROUP_COUNT:
        findings.append(f"expected {EXPECTED_GROUP_COUNT} approved groups, found {len(group_ids)}")
    if len(distributions) != EXPECTED_DISTRIBUTION_COUNT:
        findings.append(f"expected {EXPECTED_DISTRIBUTION_COUNT} distribution records, found {len(distributions)}")
    pairs = {(record.get("reference_group_id"), record.get("feature_id")) for record in distributions}
    expected_pairs = {(group, feature) for group in group_ids for feature in {record.get("feature_id") for record in distributions}}
    if len(pairs) != EXPECTED_DISTRIBUTION_COUNT or pairs != expected_pairs:
        findings.append(f"group x feature coverage mismatch: {len(pairs)} unique pairs")
    for record in distributions:
        group = record.get("reference_group_id", "")
        n_effective = record.get("n_effective")
        n_missing = record.get("n_missing", 0)
        complete_case = (n_effective - n_missing) if isinstance(n_effective, int) and isinstance(n_missing, int) else None
        if isinstance(n_effective, int) and n_effective != len(membership.get(group, set())):
            findings.append(f"{group} {record.get('feature_id')}: n_effective {n_effective} != membership rows {len(membership.get(group, set()))}")
        if not isinstance(n_effective, int) or n_effective < MIN_REFERENCE_N:
            findings.append(f"{group} {record.get('feature_id')}: n_effective below {MIN_REFERENCE_N}")
        if complete_case is not None and complete_case < MIN_REFERENCE_N:
            findings.append(f"{group} {record.get('feature_id')}: complete-case N {complete_case} below {MIN_REFERENCE_N}")
        if record.get("availability") != "available":
            findings.append(f"{group} {record.get('feature_id')}: availability {record.get('availability')!r}")
        if record.get("duplicate_policy") != "effective_sample_excludes_non_canonical_duplicate_members":
            findings.append(f"{group}: duplicate_policy not recorded")
        for token in ("ARG13", "ARG19"):
            if token in group:
                findings.append(f"unapproved standalone group present: {group}")
    for key in ("feature_set_version", "reference_group_version", "distribution_version", "corpus_package_id", "manifest_hash"):
        for record in distributions:
            if record.get(key) != KNOWN_VERSIONS[key]:
                findings.append(f"provenance mismatch {key}: {record.get(key)!r}")
                break
    _affected, _groups, canonical, non_canonical = _fold_duplicates()
    leaked = sorted(doc for doc in non_canonical if any(doc in members for members in membership.values()))
    if leaked:
        findings.append(f"non-canonical duplicate members leaked into reference membership: {leaked[:5]} ... ({len(leaked)})")
    if len(non_canonical) != HOLDOUT_EXPECTED_DUPLICATE // 2:
        findings.append(f"fold produced {len(non_canonical)} non-canonical members (expected 120)")
    return {"check": "reference_group_eligibility", "valid": not findings, "findings": findings,
            "group_count": len(group_ids), "distribution_count": len(distributions),
            "min_complete_case_n": _min_complete_case(distributions)}


def _min_complete_case(distributions: tuple[dict[str, Any], ...]) -> int | None:
    values = []
    for record in distributions:
        n_effective = record.get("n_effective")
        n_missing = record.get("n_missing", 0)
        if isinstance(n_effective, int) and isinstance(n_missing, int):
            values.append(n_effective - n_missing)
    return min(values) if values else None


def validate_version_provenance() -> dict:
    """Check the 7-field provenance chain on every distribution record."""
    findings: list[str] = []
    records = load_distributions()
    for index, record in enumerate(records):
        missing = [field for field in PROVENANCE_FIELDS if not record.get(field)]
        if missing:
            findings.append(f"record {index}: missing provenance fields {missing}")
    for key, expected in KNOWN_VERSIONS.items():
        for index, record in enumerate(records):
            if record.get(key) != expected:
                findings.append(f"record {index}: {key} = {record.get(key)!r}, expected {expected!r}")
                break
    return {"check": "version_provenance", "valid": not findings, "findings": findings,
            "record_count": len(records)}

# ---------------------------------------------------------------------------
# WU4 evaluation-protection validator
# ---------------------------------------------------------------------------

def validate_evaluation_protection() -> dict:
    """Check the 270 scored block, duplicate/corrupt holdout rows, and score-field absence."""
    findings: list[str] = []
    holdout = load_holdout_candidates()
    scored = {row["document_id"] for row in holdout if row.get("protection_reason", "").startswith("scored expository subset")}
    duplicate = {row["document_id"] for row in holdout if row.get("protection_reason") == "duplicate-group member"}
    corrupt = {row["document_id"] for row in holdout if row.get("protection_reason", "").startswith("corrupt variant")}
    if len(holdout) != HOLDOUT_EXPECTED_TOTAL:
        findings.append(f"holdout total {len(holdout)} != {HOLDOUT_EXPECTED_TOTAL}")
    if len(scored) != HOLDOUT_EXPECTED_SCORED:
        findings.append(f"scored block {len(scored)} != {HOLDOUT_EXPECTED_SCORED}")
    if len(duplicate) != HOLDOUT_EXPECTED_DUPLICATE:
        findings.append(f"duplicate members {len(duplicate)} != {HOLDOUT_EXPECTED_DUPLICATE}")
    if len(corrupt) != HOLDOUT_EXPECTED_CORRUPT:
        findings.append(f"corrupt variant rows {len(corrupt)} != {HOLDOUT_EXPECTED_CORRUPT}")
    overlap = sorted(scored & duplicate)
    if overlap:
        findings.append(f"scored block overlaps duplicate members: {overlap}")
    if any(row.get("protection_status") != "CANDIDATE" for row in holdout):
        findings.append("holdout protection_status not CANDIDATE for all rows")
    records = load_distributions()
    for record in records:
        for key in record:
            lowered = key.lower()
            if any(marker in lowered for marker in SCORE_FIELD_MARKERS):
                findings.append(f"score-like field in distribution record: {key}")
                break
    membership_header = Path(L2_DATA_DIR / "reference_group_membership.csv").read_text(encoding="utf-8").splitlines()[0]
    if membership_header.strip() != "reference_group_id,document_id,role":
        findings.append(f"unexpected membership header: {membership_header!r}")
    return {"check": "evaluation_protection", "valid": not findings, "findings": findings,
            "scored_count": len(scored), "duplicate_count": len(duplicate), "corrupt_count": len(corrupt)}


# ---------------------------------------------------------------------------
# WU10 duplicate-group leakage validator
# ---------------------------------------------------------------------------

def validate_duplicate_group_leakage(plan: dict) -> dict:
    """Validate a future partition plan against policy 10 (reusable, deterministic)."""
    findings: list[str] = []
    required = ("version", "policy_version", "grouping_keys", "sides")
    for field in required:
        if field not in plan:
            findings.append(f"plan missing required field '{field}'")
    if not isinstance(plan.get("sides"), dict) or not plan["sides"]:
        findings.append("plan.sides must be a non-empty mapping of side -> document ids")
        return {"check": "duplicate_group_leakage", "status": "FAIL", "findings": findings}
    if plan.get("claims_learner_isolation") is True:
        findings.append("learner-level isolation cannot be claimed for WECCL (no learner IDs)")
    prompt_matching = bool(plan.get("prompt_matching_design"))
    if prompt_matching and not str(plan.get("prompt_matching_design_reason") or "").strip():
        findings.append("prompt_matching_design=true requires prompt_matching_design_reason (recorded grouping + justification)")
    side_of: dict[str, str] = {}
    manifest = load_corpus_manifest()
    for side, documents in plan["sides"].items():
        for document in documents:
            if document not in manifest:
                findings.append(f"unknown document id {document!r} in side {side!r}")
            if document in side_of:
                findings.append(f"document {document} appears in multiple sides")
            side_of[document] = side
    _affected, groups, _canonical, _non_canonical = _fold_duplicates()
    for group_key, members in groups.items():
        sides = {side_of[member] for member in members if member in side_of}
        if len(sides) > 1:
            findings.append(f"duplicate group {group_key} split across sides {sorted(sides)}")
    prompts: dict[str, set[str]] = {}
    for document in side_of:
        prompt = (manifest.get(document) or {}).get("prompt_id", "")
        if prompt:
            prompts.setdefault(prompt, set()).add(side_of[document])
    for prompt, sides in sorted(prompts.items()):
        if len(sides) > 1 and not prompt_matching:
            findings.append(f"prompt {prompt} split across sides {sorted(sides)} without prompt_matching_design")
    scored = {row["document_id"] for row in load_holdout_candidates() if row.get("protection_reason", "").startswith("scored expository subset")}
    block_sides = {side_of[doc] for doc in scored if doc in side_of}
    if len(block_sides) > 1:
        findings.append(f"270 scored block split across sides {sorted(block_sides)}")
    side_types = plan.get("side_types", {})
    for document in side_of:
        if document == "WARG2081":
            side = side_of[document]
            if side_types.get(side, "mixed") != "tagged":
                findings.append("WARG2081 (corrupt RAW/LEMMA) may only enter a side explicitly declared side_type=tagged")
    status = "PASS" if not findings else "FAIL"
    return {"check": "duplicate_group_leakage", "status": status, "findings": findings}


# ---------------------------------------------------------------------------
# WU9 deterministic audit sampler (isolated harness)
# ---------------------------------------------------------------------------

def select_sample(records: Iterable[Any], rate_percent: int, seed: str = SAMPLER_VERSION,
                  cap: int = SYSTEMATIC_SAMPLE_CAP) -> list[Any]:
    """Deterministic hash-based sampling (audit-sampler-v0.1.0).

    A record is selected when sha256(seed|id) % 100 < rate_percent, capped at
    `cap` records per batch (09 §4; stratum overrides are applied by the caller:
    the selected sample is the union of systematic selection and 100% high-risk
    strata, with stratum-priority ordering under the cap).
    """
    if not 0 <= rate_percent <= 100:
        raise ValueError("rate_percent must be within 0..100")
    if cap < 1:
        raise ValueError("cap must be >= 1")
    selected: list[Any] = []
    for record in records:
        record_id = record if isinstance(record, str) else record.get("id")
        digest = hashlib.sha256(f"{seed}|{record_id}".encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:8], "big") % 100
        if bucket < rate_percent:
            selected.append(record)
    return selected[:cap]


def apply_stratum_sampling(systematic: list[Any], high_risk: list[Any],
                           cap: int = SYSTEMATIC_SAMPLE_CAP) -> list[Any]:
    """Combine systematic selection with 100% high-risk strata under the cap (09 §4).

    High-risk records are prioritized; remaining capacity is filled by systematic
    selection in deterministic order.
    """
    seen: set[str] = set()
    merged: list[Any] = []
    for record in high_risk + systematic:
        record_id = record if isinstance(record, str) else record.get("id")
        if record_id in seen:
            continue
        seen.add(record_id)
        merged.append(record)
    return merged[:cap]

# ---------------------------------------------------------------------------
# WU8 Stage-6 evidence admissibility
# ---------------------------------------------------------------------------

ADMISSIBILITY_REQUIRED_FIELDS = (
    "corpus_package_id",
    "manifest_hash",
    "feature_set_version",
    "reference_group_version",
    "distribution_version",
    "requested_reference_group",
    "resolved_reference_group",
    "fallback_disclosure",
    "feature_id",
    "n_effective",
    "n_raw",
    "n_missing",
    "availability",
    "validity_flags",
    "feature_reproducible",
    "comparison_direction",
    "epistemic_status",
    "learner_exposure",
    "provenance",
)


def _score_field_hits(record: dict) -> list[str]:
    hits: list[str] = []
    for key in record:
        lowered = str(key).lower()
        if lowered in ("priority_score", "priority score"):
            continue
        if any(marker in lowered for marker in SCORE_FIELD_MARKERS):
            hits.append(key)
    provenance = record.get("provenance")
    if isinstance(provenance, dict):
        for key in provenance:
            lowered = str(key).lower()
            if lowered in ("priority_score", "priority score"):
                continue
            if any(marker in lowered for marker in SCORE_FIELD_MARKERS):
                hits.append(f"provenance.{key}")
    return hits


def assess_admissibility(record: dict) -> tuple[str, list[str]]:
    """Return (ADMISSIBLE|LIMITED|UNAVAILABLE|INVALID, reasons) for a Stage-6 record.

    Precedence (08 §3, F14 resolution): INVALID (prohibited use) is checked first,
    then UNAVAILABLE (record-level version/availability/N failures), then LIMITED.
    """
    reasons: list[str] = []
    missing = [field for field in ADMISSIBILITY_REQUIRED_FIELDS if field not in record]
    if missing:
        return "INVALID", [f"missing required fields: {', '.join(missing)}"]
    text_fields = [str(record.get(field, "")) for field in
                   ("requested_reference_group", "resolved_reference_group", "comparison_direction")]
    prohibited = []
    for text in text_fields:
        prohibited.extend(contains_prohibited_claim(text))
    if prohibited:
        return "INVALID", [f"prohibited claim vocabulary: {', '.join(prohibited)}"]
    score_hits = _score_field_hits(record)
    if score_hits:
        return "INVALID", [f"score fields present: {', '.join(score_hits)} (EP-06)"]
    if record.get("epistemic_status") != "observed_descriptive":
        return "INVALID", [f"epistemic_status {record.get('epistemic_status')!r} (must be observed_descriptive)"]
    if record.get("learner_exposure") != "research_only":
        return "INVALID", [f"learner_exposure {record.get('learner_exposure')!r} (must be research_only)"]
    if record.get("comparison_direction") != "descriptive":
        return "INVALID", [f"comparison_direction {record.get('comparison_direction')!r} (must be descriptive)"]
    if record.get("feature_reproducible") is not True:
        return "INVALID", ["feature value not reproducible under the same feature contract"]
    requested = str(record.get("requested_reference_group", ""))
    resolved = str(record.get("resolved_reference_group", ""))
    fallback = record.get("fallback_disclosure")
    if (fallback is None or str(fallback).strip() == "") and resolved != requested:
        return "INVALID", ["fallback_disclosure null/empty while resolved != requested (null only on exact match)"]
    provenance = record.get("provenance")
    if not isinstance(provenance, dict):
        return "UNAVAILABLE", ["provenance must be the 7-field distribution chain"]
    missing_provenance = [field for field in PROVENANCE_FIELDS if not provenance.get(field)]
    if missing_provenance:
        return "UNAVAILABLE", [f"incomplete provenance chain, missing: {', '.join(missing_provenance)}"]
    for key in ("corpus_package_id", "manifest_hash", "feature_set_version", "reference_group_version", "distribution_version"):
        if record.get(key) != KNOWN_VERSIONS[key]:
            return "UNAVAILABLE", [f"{key} mismatch: {record.get(key)!r}"]
    membership = load_membership()
    if resolved not in membership:
        return "UNAVAILABLE", [f"resolved group {resolved!r} not in the approved reference-group set"]
    feature_id = str(record.get("feature_id", ""))
    distribution = next((item for item in load_distributions()
                         if item.get("reference_group_id") == resolved and item.get("feature_id") == feature_id), None)
    if distribution is None:
        return "UNAVAILABLE", [f"no distribution record for {resolved} x {feature_id}"]
    if distribution.get("availability") != "available":
        return "UNAVAILABLE", [f"distribution availability {distribution.get('availability')!r}"]
    if record.get("availability") != "available":
        return "UNAVAILABLE", [f"availability {record.get('availability')!r}"]
    n_effective = record.get("n_effective")
    n_raw = record.get("n_raw")
    n_missing = record.get("n_missing", 0)
    if not isinstance(n_effective, int) or n_effective < MIN_REFERENCE_N:
        return "UNAVAILABLE", [f"n_effective {n_effective!r} below {MIN_REFERENCE_N}"]
    if not isinstance(n_raw, int) or n_raw < 1 or n_raw < n_effective:
        return "UNAVAILABLE", [f"n_raw {n_raw!r} must be >= 1 and >= n_effective"]
    if distribution.get("n_effective") != n_effective:
        return "UNAVAILABLE", [f"n_effective {n_effective} does not match the distribution record ({distribution.get('n_effective')})"]
    if not isinstance(n_missing, int) or n_missing < 0 or n_missing > n_effective:
        return "UNAVAILABLE", [f"n_missing {n_missing!r} invalid"]
    if (n_effective - n_missing) < MIN_REFERENCE_N:
        return "UNAVAILABLE", [f"complete-case N {n_effective - n_missing} below {MIN_REFERENCE_N}"]
    validity_flags = record.get("validity_flags") or []
    limited_reasons: list[str] = []
    if fallback is not None and str(fallback).strip() != "":
        limited_reasons.append("fallback disclosure present")
    if isinstance(n_missing, int) and n_missing > 0:
        limited_reasons.append(f"missingness {n_missing}")
    if validity_flags:
        limited_reasons.append(f"validity flags: {validity_flags}")
    if limited_reasons:
        return "LIMITED", limited_reasons
    return "ADMISSIBLE", []


# ---------------------------------------------------------------------------
# Policy registry
# ---------------------------------------------------------------------------

POLICY_REGISTRY_PATH = POLICY_DIR / "policy_registry.json"

# Policy-artifact hash normalization rule (POLICY-HASH-1; Wave-1 CRLF debt
# follow-up GOV-CRLF-HASH-FOLLOWUP): the canonical content hash of a policy JSON
# artifact is SHA-256 over its LF-normalized bytes - every CRLF sequence is
# converted to LF before hashing (the Git blob form). Working-tree line-ending
# conversion (core.autocrlf / .gitattributes) therefore never changes registry
# hashes; the recorded artifact_hash values in policy_registry.json are
# LF-canonical and verify identically for LF and CRLF checkouts alike.


def _lf_canonical_bytes(data: bytes) -> bytes:
    """Normalize CRLF line endings to LF (canonical Git blob form)."""
    return data.replace(b"\r\n", b"\n")


def _policy_artifact_digest_bytes(data: bytes) -> str:
    """SHA-256 of LF-canonical artifact bytes (POLICY-HASH-1)."""
    return hashlib.sha256(_lf_canonical_bytes(data)).hexdigest()


def _policy_artifact_digest(path: Path) -> str:
    """SHA-256 of the LF-canonical bytes of a policy artifact file (POLICY-HASH-1)."""
    return _policy_artifact_digest_bytes(path.read_bytes())


def load_policy_registry() -> dict:
    with open(POLICY_REGISTRY_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_policy_registry() -> dict:
    """Check the policy registry: artifacts exist, hashes match, versions align."""
    findings: list[str] = []
    registry = load_policy_registry()
    entries = registry.get("policies", [])
    if not entries:
        findings.append("registry has no policy entries")
    families = {entry.get("policy_family") for entry in entries}
    if FRAMEWORK_POLICY["policy_family"] not in families:
        findings.append("registry missing the evaluation-policy-versioning framework entry (RD-POL-002)")
    for entry in entries:
        artifact = entry.get("artifact")
        if not artifact:
            continue  # framework entry (markdown + schema based)
        path = POLICY_DIR / artifact
        if not path.exists():
            findings.append(f"artifact missing: {artifact}")
            continue
        digest = _policy_artifact_digest(path)
        if digest != entry.get("artifact_hash"):
            findings.append(f"hash mismatch for {artifact}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            findings.append(f"artifact unreadable {artifact}: {exc}")
            continue
        if payload.get("policy_id") != entry.get("policy_id"):
            findings.append(f"policy_id mismatch in registry entry {entry.get('policy_id')}")
        if payload.get("policy_version") != entry.get("policy_version"):
            findings.append(f"policy_version mismatch in registry entry {entry.get('policy_id')}")
        if payload.get("status") != "ratified":
            findings.append(f"registry entry {entry.get('policy_id')} not ratified")
    return {"check": "policy_registry", "valid": not findings, "findings": findings,
            "entry_count": len(entries)}


# ---------------------------------------------------------------------------
# Aggregate runner
# ---------------------------------------------------------------------------

def run_all_validators() -> dict:
    """Run the artifact/data validators; used by 11_VERIFICATION.md and tests."""
    policy_results = validate_all_policy_artifacts()
    checks = {
        "policy_artifacts": {"valid": all(item["valid"] for item in policy_results),
                             "detail": policy_results},
        "policy_registry": validate_policy_registry(),
        "reference_group_eligibility": validate_reference_group_eligibility(),
        "evaluation_protection": validate_evaluation_protection(),
        "version_provenance": validate_version_provenance(),
    }
    return {"valid": all(check["valid"] for check in checks.values()),
            "checks": checks}
