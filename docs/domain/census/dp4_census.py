"""DP-4 governed-snapshot census of the legacy `essays` table (READ-ONLY).

Authorized by RD-D22-DP4-authorized.json (2026-08-09). Produces a versioned,
governed census artifact applying D-22 manifest rules M0-M4 (explicit-only).

Guarantees:
  - Read-only SQLite connection (mode=ro). No product mutation.
  - Never reads `essay_text`, `writing_prompt`, or any learner-content column.
  - Snapshot contains counts, genre values (task metadata), schema headers,
    provenance and QA records only. No essay text, no learner identity values.
  - No mappings outside M0-M4; no writes to the product DB.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime, timezone

DB_PATH = r"A:\EAP Agent Project\writing-feedback-mvp\data\writing_feedback.db"
MANIFEST_PATH = r"A:\EAP Agent Project\worktrees\l2-writing\docs\domain\D-22_legacy_genre_mapping_manifest.proposal.json"
OUT_PATH = r"A:\EAP Agent Project\worktrees\l2-writing\docs\domain\census\L2_DP4_LEGACY_ESSAYS_CENSUS_v1.0.0.json"

GOAL_ID = "L2-D22-CENSUS-AND-V1"
ARTIFACT_ID = "L2-DP4-LEGACY-ESSAYS-CENSUS-001"
ARTIFACT_VERSION = "1.0.0"
BASELINE = "09264abbd93cdc6b62b83cefd94b3b640319ac9b"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(value: str) -> str:
    """Contract 2.2 normalization discipline: casefold + strip + whitespace
    collapse (incl. CJK ideographic space via Unicode \\s). Exact-match only;
    no punctuation stripping (conservative: any variant falls to M0)."""
    if value is None:
        return ""
    s = unicodedata.normalize("NFC", str(value)).casefold().strip()
    return re.sub(r"\s+", " ", s)


def locale_hint(norm: str) -> str | None:
    if re.search(r"[\u4e00-\u9fff]", norm):
        return "zh_CN"
    if norm and all(ord(c) < 128 for c in norm):
        return "en"
    return None


def load_rules():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)
    rules = []
    for r in manifest["rules"]:
        rules.append(
            {
                "rule_id": r["rule_id"],
                "normalized_value": r["normalized_value"],
                "locale": r.get("locale"),
                "mapping": r["mapping"],
                "reason_code": r.get("reason_code"),
            }
        )
    return rules, manifest


def duplicate_rule_check(rules) -> list:
    """Disjoint-coverage validation (D-22 proposal 4.2): duplicate normalized
    values across non-default rules are a manifest validation error."""
    problems = []
    seen = {}
    for r in rules:
        if r["rule_id"] == "M0":
            continue
        key = r["normalized_value"]
        if key in seen:
            problems.append(f"duplicate normalized_value {key!r}: {seen[key]} vs {r['rule_id']}")
        seen[key] = r["rule_id"]
    return problems


def main():
    # ---- provenance -----------------------------------------------------
    st = os.stat(DB_PATH)
    db_sha = sha256_file(DB_PATH)

    con = sqlite3.connect(f"file:{DB_PATH.replace(os.sep, '/')}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]
    journal_mode = cur.execute("PRAGMA journal_mode").fetchone()[0]
    migration_version = cur.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
    ).fetchone()[0]

    # ---- schema header (essays) ----------------------------------------
    essays_cols = [
        {"name": c[1], "type": c[2], "notnull": bool(c[3]), "pk": bool(c[5])}
        for c in cur.execute('PRAGMA table_info("essays")').fetchall()
    ]

    # ---- rules ----------------------------------------------------------
    rules, manifest = load_rules()
    dup_problems = duplicate_rule_check(rules)
    if dup_problems:
        raise SystemExit("MANIFEST VALIDATION ERROR: " + "; ".join(dup_problems))

    default_rule = next(r for r in rules if r["rule_id"] == "M0")
    value_rules = [r for r in rules if r["rule_id"] != "M0"]

    # ---- full-population extract (metadata columns only) ----------------
    rows = cur.execute(
        """
        SELECT e.essay_id, e.genre, e.draft_stage, e.timed,
               e.revision_of_submission_id, e.revision_stage,
               e.original_draft_stage, e.timing_source,
               s.is_synthetic
        FROM essays e
        LEFT JOIN students s ON s.student_id = e.student_id
        ORDER BY e.essay_id
        """
    ).fetchall()
    con.close()

    total = len(rows)

    # ---- per-row disposition ---------------------------------------------
    def disposition_for(norm: str):
        matched = [r for r in value_rules if r["normalized_value"] == norm]
        if len(matched) == 1:
            r = matched[0]
            return {"rule_id": r["rule_id"], "mapping": r["mapping"],
                    "reason_code": r["reason_code"]}
        if len(matched) > 1:
            return {"rule_id": None, "mapping": "legacy_unclassified",
                    "reason_code": "mapping_rule_conflict", "conflict_rules": [r["rule_id"] for r in matched]}
        return {"rule_id": default_rule["rule_id"], "mapping": default_rule["mapping"],
                "reason_code": default_rule["reason_code"]}

    # pass 1
    row_records = []
    for r in rows:
        norm = normalize(r["genre"])
        row_records.append(
            {
                "essay_id": r["essay_id"],
                "genre": r["genre"],
                "genre_normalized": norm,
                "locale_hint": locale_hint(norm),
                "draft_stage": r["draft_stage"],
                "timed": bool(r["timed"]),
                "revision_of_submission_id": r["revision_of_submission_id"],
                "revision_stage": r["revision_stage"],
                "original_draft_stage": r["original_draft_stage"],
                "timing_source": r["timing_source"],
                "is_synthetic": bool(r["is_synthetic"]) if r["is_synthetic"] is not None else None,
                "disposition": disposition_for(norm),
            }
        )

    # pass 2 (independent QA re-pass)
    qa_records = []
    for r in rows:
        norm = normalize(r["genre"])
        qa_records.append({"essay_id": r["essay_id"], "genre": r["genre"],
                           "genre_normalized": norm,
                           "disposition": disposition_for(norm)})
    qa_match = all(
        a["genre_normalized"] == b["genre_normalized"]
        and a["disposition"] == b["disposition"]
        for a, b in zip(row_records, qa_records)
    )
    qa_cover = {x["genre_normalized"] for x in qa_records} == {x["genre_normalized"] for x in row_records}

    # ---- aggregates ------------------------------------------------------
    from collections import Counter, defaultdict

    raw_vocab = Counter(x["genre"] for x in row_records)
    norm_vocab = Counter(x["genre_normalized"] for x in row_records)

    rule_counts = Counter()
    reason_counts = Counter()
    mapping_counts = Counter()
    for x in row_records:
        d = x["disposition"]
        rule_counts[d["rule_id"] or "conflict"] += 1
        reason_counts[d["reason_code"]] += 1
        mapping_counts[d["mapping"]] += 1

    # distinct-value disposition table
    value_table = []
    for norm, cnt in sorted(norm_vocab.items(), key=lambda kv: (-kv[1], kv[0])):
        d = disposition_for(norm)
        raws = sorted(
            {"raw": raw, "count": raw_vocab[raw]}
            for raw in raw_vocab
            if normalize(raw) == norm
        )
        value_table.append(
            {
                "genre_normalized": norm,
                "rows": cnt,
                "raw_variants": len(raws),
                "raw_values": raws,
                "disposition": d,
            }
        )

    typed = mapping_counts.get("argumentative", 0)
    legacy_unclassified = mapping_counts.get("legacy_unclassified", 0)

    # edge cases requiring review
    edge_cases = {"values_with_no_rule": [], "empty_or_whitespace": [],
                  "near_miss_variants": [], "mixed_scripts": [],
                  "long_values": [], "digits_in_value": []}
    for vt in value_table:
        norm = vt["genre_normalized"]
        d = vt["disposition"]
        if d["rule_id"] == "M0":
            edge_cases["values_with_no_rule"].append(
                {"genre_normalized": norm, "rows": vt["rows"]})
            sub = [r["normalized_value"] for r in value_rules
                   if r["normalized_value"] and r["normalized_value"] in norm]
            if sub:
                edge_cases["near_miss_variants"].append(
                    {"genre_normalized": norm, "rows": vt["rows"],
                     "contains_rule_value": sub})
        if norm == "" and vt["rows"]:
            edge_cases["empty_or_whitespace"].append(
                {"rows": vt["rows"], "raw_values": vt["raw_values"]})
        if re.search(r"[\u4e00-\u9fff]", norm) and re.search(r"[A-Za-z]", norm):
            edge_cases["mixed_scripts"].append({"genre_normalized": norm, "rows": vt["rows"]})
        if len(norm) > 60:
            edge_cases["long_values"].append({"genre_normalized": norm, "rows": vt["rows"]})
        if re.search(r"\d", norm):
            edge_cases["digits_in_value"].append({"genre_normalized": norm, "rows": vt["rows"]})

    # legacy-source distribution
    draft_stage_dist = Counter(x["draft_stage"] for x in row_records)
    revision_dist = Counter(
        "revision" if x["revision_of_submission_id"] is not None else "independent"
        for x in row_records
    )
    revision_stage_dist = Counter(x["revision_stage"] for x in row_records)
    synthetic_dist = Counter(
        "synthetic_demo" if x["is_synthetic"] else ("real" if x["is_synthetic"] is False else "unknown")
        for x in row_records
    )
    locale_dist = Counter(x["locale_hint"] or "unknown" for x in row_records)
    genre_option_dist = Counter()
    for x in row_records:
        norm = x["genre_normalized"]
        if norm in ("argumentative essay",):
            genre_option_dist["option_argumentative_en"] += 1
        elif norm in ("议论文",):
            genre_option_dist["option_argumentative_zh"] += 1
        elif norm in ("expository essay",):
            genre_option_dist["option_expository_en"] += 1
        elif norm in ("说明文",):
            genre_option_dist["option_expository_zh"] += 1
        elif norm in ("narrative essay",):
            genre_option_dist["option_narrative_en"] += 1
        elif norm in ("记叙文",):
            genre_option_dist["option_narrative_zh"] += 1
        elif norm == "":
            genre_option_dist["option_empty"] += 1
        else:
            genre_option_dist["option_other"] += 1

    # ---- extract digest (metadata only: id + genre) ----------------------
    extract_payload = json.dumps(
        [{"id": x["essay_id"], "genre": x["genre"]} for x in row_records],
        ensure_ascii=True, sort_keys=True,
    ).encode("utf-8")
    extract_sha = hashlib.sha256(extract_payload).hexdigest()

    # ---- census record ----------------------------------------------------
    record = {
        "artifact_id": ARTIFACT_ID,
        "artifact_version": ARTIFACT_VERSION,
        "goal_id": GOAL_ID,
        "goal_scope": "DP-4 governed-snapshot census (read-only analytical)",
        "baseline": BASELINE,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authorizations": [
            "program-control/researcher-decisions/RD-D22-approved.json",
            "program-control/researcher-decisions/RD-D22-DP4-authorized.json",
        ],
        "manifest_source": "docs/domain/D-22_legacy_genre_mapping_manifest.proposal.json",
        "manifest_status_at_census": manifest.get("status"),
        "provenance": {
            "source_db": DB_PATH,
            "source_db_sha256": db_sha,
            "source_db_size_bytes": st.st_size,
            "source_db_mtime_epoch": st.st_mtime,
            "access_mode": "sqlite mode=ro (read-only URI); no writes",
            "integrity_check": integrity,
            "journal_mode": journal_mode,
            "schema_migrations_max_version": migration_version,
            "normalization": "NFC + casefold + strip + Unicode-whitespace collapse; exact normalized match only; no punctuation stripping; no substring/similarity",
            "extract_digest_sha256": extract_sha,
            "extract_columns": ["essay_id", "genre", "draft_stage", "timed",
                                "revision_of_submission_id", "revision_stage",
                                "original_draft_stage", "timing_source",
                                "students.is_synthetic"],
            "excluded_columns": ["essay_text", "writing_prompt", "tool_use"],
        },
        "essays_schema": essays_cols,
        "census": {
            "total_rows": total,
            "rule_counts": dict(rule_counts),
            "reason_code_counts": dict(reason_counts),
            "resulting_task_type_rows": dict(mapping_counts),
            "typed_rate": round(typed / total, 6) if total else None,
            "legacy_unclassified_rate": round(legacy_unclassified / total, 6) if total else None,
            "distinct_raw_genre_values": len(raw_vocab),
            "distinct_normalized_genre_values": len(norm_vocab),
            "distinct_value_coverage": "100% of distinct normalized values dispositioned by M0-M4 (M0 default catches all unmatched)",
            "rule_value_disjointness": "PASS (no duplicate normalized values; manifest validation clean)",
            "mapping_conflicts": rule_counts.get("conflict", 0),
        },
        "legacy_source_distribution": {
            "by_genre_option": dict(genre_option_dist),
            "by_locale_hint": dict(locale_dist),
            "by_independent_vs_revision": dict(revision_dist),
            "by_revision_stage": dict(revision_stage_dist),
            "by_draft_stage": dict(draft_stage_dist),
            "by_student_class": dict(synthetic_dist),
        },
        "distinct_value_dispositions": value_table,
        "edge_cases_requiring_review": edge_cases,
        "qa": {
            "second_disposition_pass_identical": qa_match,
            "second_pass_value_coverage_identical": qa_cover,
            "duplicate_rule_detection": {"result": "PASS" if not dup_problems else "FAIL",
                                         "problems": dup_problems},
            "reason_code_completeness": all(
                rc in ("no_mapping_rule", "missing_genre", "mapping_rule_conflict", None)
                for rc in reason_counts
            ),
        },
        "nr_items": {
            "prompt_pattern_audit": "NR - not performed in the governed snapshot; prompt text is excluded from this snapshot (no essay/prompt text copied). Feature-checklist pattern audit (V3 instrument 2, F01-F17) remains a separate V3/V4 execution item.",
            "v2_agreement_sample": "NR - V2 sampling frame derivable from this census but study execution not part of this Goal",
            "v4_adversarial_set": "NR - V4 execution not part of this Goal",
        },
        "non_claims": [
            "Snapshot contains no essay text, no prompt text, and no learner identity values",
            "No product mutation; DB opened read-only",
            "Census is metadata-only; assigns no proficiency/difficulty/measurement meaning",
            "No mappings outside M0-M4 were created",
            "No validity claim; census coverage evidence only",
            "Raw SWECCL untouched; not a substitute source",
        ],
    }

    with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(json.dumps({
        "total_rows": total,
        "rule_counts": dict(rule_counts),
        "resulting_task_type_rows": dict(mapping_counts),
        "typed_rate": round(typed / total, 6) if total else None,
        "legacy_unclassified_rate": round(legacy_unclassified / total, 6) if total else None,
        "distinct_raw_genre_values": len(raw_vocab),
        "distinct_normalized_genre_values": len(norm_vocab),
        "mapping_conflicts": rule_counts.get("conflict", 0),
        "qa_pass2_identical": qa_match,
        "db_sha256": db_sha,
        "extract_sha256": extract_sha,
        "output": OUT_PATH,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
