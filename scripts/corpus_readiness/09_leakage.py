"""WU9: evaluation/leakage preparation.

Identifies leakage risks and protection candidates from actual data.
No final train/dev/test partitions are created (not justified at this stage).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from scripts.corpus_paths import get_repo_root, get_corpus_root

REPO_ROOT = get_repo_root()
OUT_DIR = get_readiness_out_dir()
MANIFEST = OUT_DIR / "corpus_manifest.csv"
DUPLICATES = OUT_DIR / "duplicate_report.csv"
QUALITY = OUT_DIR / "quality_issues.csv"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8-sig")))
    dup_rows = list(csv.DictReader(open(DUPLICATES, encoding="utf-8-sig")))
    quality_rows = list(csv.DictReader(open(QUALITY, encoding="utf-8-sig")))
    dup_stems = set()
    for d in dup_rows:
        for m in d["members"].split(","):
            dup_stems.add(Path(m).stem)
    corrupt = {r["relative_path"].split("/")[-1].replace(".txt", "") for r in quality_rows if r["issue_type"] == "all_nul_bytes"}

    holdouts = []
    for r in rows:
        reasons = []
        if r["document_id"] in dup_stems:
            reasons.append("duplicate-group member")
        if r["document_id"] in corrupt:
            reasons.append("corrupt variant (raw/lemma NUL); tagged-only text")
        if r["genre"] == "expository":
            reasons.append("scored expository subset (270 texts with rater scores) - high-value evaluation candidate")
        if reasons:
            holdouts.append(
                {
                    "document_id": r["document_id"],
                    "prompt_id": r["prompt_id"],
                    "genre": r["genre"],
                    "protection_reason": "; ".join(reasons),
                    "protection_status": "CANDIDATE",
                }
            )
    with open(OUT_DIR / "holdout_candidates.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["document_id", "prompt_id", "genre", "protection_reason", "protection_status"])
        writer.writeheader()
        writer.writerows(holdouts)

    plan = {
        "partitioning_status": "no final partitions created (not justified before research design)",
        "partitioning_constraints": [
            "never place duplicate-group members in both dev and eval",
            "never split same prompt across dev/eval without explicit prompt-matching design",
            "same learner across texts cannot be identified from filenames (no learner ID in WECCL filenames) - repeated-text detection is the only proxy",
            "scored expository texts must be treated as one protected block",
        ],
        "leakage_risks": [
            {"risk": "same_text_duplicate", "detail": f"{len(dup_stems)} documents in duplicate groups (byte/normalized-text level)"},
            {"risk": "same_prompt_leakage", "detail": "27 prompts; prompt-level splits required for prompt-controlled evaluation"},
            {"risk": "corrupt_variant_usage", "detail": "WARG2081 raw/lemma unusable; tagged-only"},
            {"risk": "scored_data_contamination", "detail": "270 expository texts carry human scores (exp.sav/exp.xls); using them as both reference and evaluation is circular"},
            {"risk": "unknown_learner_identity", "detail": "no learner ID in WECCL filenames; cannot guarantee same-learner isolation across documents"},
        ],
        "stable_grouping_keys": ["document_id", "prompt_id", "genre", "duplicate_group_id (derived)"],
        "holdout_candidate_count": len(holdouts),
    }
    with open(OUT_DIR / "leakage_plan.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
