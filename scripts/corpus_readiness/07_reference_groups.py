"""WU7: reference-group candidate design from actual metadata coverage.

Non-normative candidate design for the next Goal. Statuses use the documented
vocabulary. Min-N=30 is a conservative preparation criterion, NOT production
policy (Researcher decision required for final band/min-N policy).
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(r"A:\EAP Agent Project\writing-feedback-mvp")
OUT_DIR = REPO_ROOT / "docs" / "corpus-readiness" / "sweccl2" / "data"
MANIFEST = OUT_DIR / "corpus_manifest.csv"
DUPLICATES = OUT_DIR / "duplicate_report.csv"
MIN_N = 30


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8-sig")))
    dup_rows = list(csv.DictReader(open(DUPLICATES, encoding="utf-8-sig")))
    dup_stems = set()
    for d in dup_rows:
        for m in d["members"].split(","):
            dup_stems.add(Path(m).stem)
    dup_stems.add("WARG2081")  # corrupt raw/lemma variant

    candidates: list[dict] = []
    for prompt in sorted({r["prompt_id"] for r in rows}):
        members = [r for r in rows if r["prompt_id"] == prompt]
        n = len(members)
        candidates.append(
            {
                "candidate_group_id": f"RG-weccl-prompt-{prompt}-v0.1",
                "selection_definition": f"prompt_id={prompt}",
                "n": n,
                "coverage": 1.0,
                "metadata_reliability": "high (100% header coverage, manual-verified counts)",
                "status": status_for(n),
                "major_limitations": limitation_text(members, dup_stems, prompt),
                "recommended_use": "same-prompt comparisons; raw/tagged/lemma variants available",
                "unsupported_inference": "proficiency/mastery/learning-gain; cross-prompt normative claims",
            }
        )
    genre_groups = [
        ("RG-weccl-argumentative-v0.1", "genre=argumentative", "argumentative"),
        ("RG-weccl-expository-v0.1", "genre=expository", "expository"),
    ]
    for gid, definition, genre in genre_groups:
        members = [r for r in rows if r["genre"] == genre]
        candidates.append(
            {
                "candidate_group_id": gid,
                "selection_definition": definition,
                "n": len(members),
                "coverage": 1.0,
                "metadata_reliability": "high",
                "status": status_for(len(members)),
                "major_limitations": limitation_text(members, dup_stems, genre),
                "recommended_use": "genre-level descriptive reference; prompt is a confound unless controlled",
                "unsupported_inference": "proficiency/mastery/learning-gain; prompt-free normative claims",
            }
        )
    for dim, values in [
        ("timed_status", ["timed", "untimed"]),
        ("major_type", ["english_major", "non_english_major"]),
        ("entry_year", ["2003", "2004", "2005", "2006", "2007"]),
        ("grade", ["1", "2", "3", "4"]),
    ]:
        for value in values:
            members = [r for r in rows if r[dim] == value]
            candidates.append(
                {
                    "candidate_group_id": f"RG-weccl-{dim}-{value}-v0.1",
                    "selection_definition": f"{dim}={value}",
                    "n": len(members),
                    "coverage": 1.0,
                    "metadata_reliability": "high",
                    "status": status_for(len(members)),
                    "major_limitations": limitation_text(members, dup_stems, value),
                    "recommended_use": "descriptive composition reporting; cross-condition comparison requires prompt/task control",
                    "unsupported_inference": "proficiency/mastery/learning-gain; causal condition effects",
                }
            )
    with open(OUT_DIR / "reference_group_candidates.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "candidate_group_id", "selection_definition", "n", "coverage", "metadata_reliability",
                "status", "major_limitations", "recommended_use", "unsupported_inference",
            ],
        )
        writer.writeheader()
        writer.writerows(candidates)
    summary = {
        "min_n_criterion": MIN_N,
        "criterion_note": "conservative preparation criterion only; final policy is a Researcher decision",
        "candidate_count": len(candidates),
        "status_counts": dict(Counter(c["status"] for c in candidates)),
        "duplicate_touched_stems": len(dup_stems),
        "fallback_hierarchy": ["same prompt/task", "same genre + writing condition", "broader argumentative corpus", "UNAVAILABLE"],
    }
    with open(OUT_DIR / "reference_group_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def status_for(n: int) -> str:
    if n < MIN_N:
        return "TOO_SPARSE"
    if n < 100:
        return "PROMISING"
    return "READY_FOR_VALIDATION"


def limitation_text(members: list, dup_stems: set, label: str) -> str:
    dup_count = sum(1 for r in members if r["document_id"] in dup_stems)
    parts = [f"duplicate/flagged documents inside group: {dup_count}"]
    if len(members) < MIN_N:
        parts.append(f"N={len(members)} below conservative min-N={MIN_N}")
    return "; ".join(parts)


if __name__ == "__main__":
    main()
