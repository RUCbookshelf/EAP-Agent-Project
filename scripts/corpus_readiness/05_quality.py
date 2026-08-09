"""WU5: data quality, duplicate and integrity audit.

Checks: empty/all-nul files, header issues, token-length distribution,
non-ascii learner content, exact duplicates (within/across folders, normalized),
SECCL annotator notes, candidate exclusions (no silent deletion).
Outputs:
  quality_issues.csv
  duplicate_report.csv
  corpus_exclusions_draft.csv
"""

from __future__ import annotations

import csv
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from scripts.corpus_paths import get_repo_root, get_corpus_root

CORPUS_ROOT = get_corpus_root()
DERIVED_ROOT = CORPUS_ROOT / "PREPARED" / "utf8"
REPO_ROOT = get_repo_root()
OUT_DIR = get_readiness_out_dir()
INVENTORY = OUT_DIR / "physical_inventory.csv"

CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
NORM_RE = re.compile(r"\s+")


def norm_text(text: str) -> str:
    return NORM_RE.sub(" ", text).strip().lower()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(INVENTORY, encoding="utf-8-sig")))
    issues: list[dict] = []
    dup_groups: list[dict] = []
    exclusions: list[dict] = []

    raw_lengths: list[tuple[str, int]] = []
    for r in rows:
        rel = r["relative_path"]
        try:
            data = (CORPUS_ROOT / rel).read_bytes()
        except FileNotFoundError:
            issues.append({"relative_path": rel, "issue_type": "file_missing_since_inventory", "severity": "high", "detail": "file present at inventory time but missing now"})
            continue
        size = len(data)
        if r["extension"] == ".txt" and size == 0:
            issues.append({"relative_path": rel, "issue_type": "empty_file", "severity": "high", "detail": "0 bytes"})
        if size > 0 and data.count(b"\x00") == size:
            issues.append({"relative_path": rel, "issue_type": "all_nul_bytes", "severity": "high", "detail": f"{size} NUL bytes"})
            exclusions.append(
                {
                    "relative_path": rel,
                    "exclusion_status": "candidate",
                    "reason": "corrupt: entire file is NUL bytes (no text)",
                    "evidence": f"bytes={size}, sha256={r['sha256']}",
                }
            )

    norm_dup: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        if r["corpus_component"] != "weccl_raw":
            continue
        rel = r["relative_path"]
        text = (DERIVED_ROOT / rel).read_text(encoding="utf-8")
        lines = text.splitlines()
        body = "\n".join(lines[1:]) if lines and lines[0].startswith("<") else text
        toks = body.split()
        raw_lengths.append((Path(rel).stem, len(toks)))
        norm_dup[norm_text(body)].append(Path(rel).stem)

    lengths = [n for _, n in raw_lengths]
    sorted_lengths = sorted(lengths)
    pcts = {
        "n": len(lengths),
        "min": min(lengths),
        "p1": sorted_lengths[int(len(lengths) * 0.01)],
        "p5": sorted_lengths[int(len(lengths) * 0.05)],
        "median": statistics.median(lengths),
        "mean": round(statistics.mean(lengths), 1),
        "p95": sorted_lengths[min(int(len(lengths) * 0.95), len(lengths) - 1)],
        "max": max(lengths),
    }
    for stem, n in raw_lengths:
        if n < 30:
            issues.append(
                {"relative_path": f"WECCL20/RAW/{stem}.txt", "issue_type": "extremely_short_text", "severity": "candidate", "detail": f"{n} tokens"}
            )

    for norm, stems in sorted(norm_dup.items()):
        if len(stems) > 1:
            dup_groups.append(
                {
                    "scope": "weccl_raw",
                    "kind": "exact_duplicate_text",
                    "members": ",".join(stems),
                    "n": len(stems),
                    "detail": "identical body text after whitespace/lowercase normalization",
                }
            )

    sha_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in rows:
        if r["corpus_component"] in ("weccl_raw", "weccl_lemma", "weccl_tagged"):
            sha_groups[(r["corpus_component"], r["sha256"])].append(r["relative_path"])
    for (component, sha), paths in sorted(sha_groups.items()):
        if len(paths) > 1:
            dup_groups.append(
                {
                    "scope": component,
                    "kind": "exact_byte_duplicate",
                    "members": ",".join(paths),
                    "n": len(paths),
                    "detail": f"identical sha256 {sha[:16]}...",
                }
            )

    raw_sha = {}
    lemma_sha = {}
    for r in rows:
        if r["corpus_component"] == "weccl_raw":
            raw_sha[Path(r["relative_path"]).stem] = r["sha256"]
        elif r["corpus_component"] == "weccl_lemma":
            lemma_sha[Path(r["relative_path"]).stem] = r["sha256"]
    same_raw_lemma = [s for s in raw_sha if s in lemma_sha and raw_sha[s] == lemma_sha[s] and raw_sha[s]]
    if same_raw_lemma:
        issues.append(
            {
                "relative_path": "WECCL20 (RAW vs LEMMA)",
                "issue_type": "variant_identical_bytes",
                "severity": "candidate",
                "detail": f"{len(same_raw_lemma)} documents where LEMMA byte-identical to RAW: {','.join(same_raw_lemma[:20])}",
            }
        )

    for r in rows:
        if r["corpus_component"] in ("weccl_raw", "weccl_lemma") and r["detected_encoding"] != "ascii":
            issues.append(
                {
                    "relative_path": r["relative_path"],
                    "issue_type": "non_ascii_learner_content",
                    "severity": "info",
                    "detail": f"encoding={r['detected_encoding']}; contains non-ASCII chars (Chinese/fullwidth/punctuation) typed by learner",
                }
            )

    for r in rows:
        if r["corpus_component"] != "seccl_texts" or r["detected_encoding"] == "ascii":
            continue
        text = (DERIVED_ROOT / r["relative_path"]).read_text(encoding="utf-8")
        cn = CHINESE_RE.findall(text)
        if cn:
            issues.append(
                {
                    "relative_path": r["relative_path"],
                    "issue_type": "chinese_annotator_note_in_transcript",
                    "severity": "info",
                    "detail": f"{len(cn)} CJK chars; transcriber annotations embedded in transcript (e.g., notes like '未录完')",
                }
            )

    seccl_sha: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in rows:
        if r["corpus_component"] == "seccl_texts":
            seccl_sha[(r["relative_path"].split("/")[2], r["sha256"])].append(r["relative_path"])
    for (folder, sha), paths in sorted(seccl_sha.items()):
        if len(paths) > 1:
            dup_groups.append(
                {
                    "scope": f"seccl_texts/{folder}",
                    "kind": "exact_byte_duplicate",
                    "members": ",".join(paths),
                    "n": len(paths),
                    "detail": f"identical sha256 {sha[:16]}...",
                }
            )

    with open(OUT_DIR / "quality_issues.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["relative_path", "issue_type", "severity", "detail"])
        writer.writeheader()
        writer.writerows(issues)
    with open(OUT_DIR / "duplicate_report.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["scope", "kind", "members", "n", "detail"])
        writer.writeheader()
        writer.writerows(dup_groups)
    with open(OUT_DIR / "corpus_exclusions_draft.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["relative_path", "exclusion_status", "reason", "evidence"])
        writer.writeheader()
        writer.writerows(exclusions)

    summary = {
        "quality_issue_count": len(issues),
        "issue_type_counts": dict(Counter(i["issue_type"] for i in issues)),
        "duplicate_group_count": len(dup_groups),
        "duplicate_kind_counts": dict(Counter(d["kind"] for d in dup_groups)),
        "exclusion_candidate_count": len(exclusions),
        "raw_token_length_stats": pcts,
        "sample_issues": issues[:40],
        "sample_duplicates": dup_groups[:20],
    }
    with open(OUT_DIR / "quality_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(
        json.dumps(
            {
                "quality_issue_count": len(issues),
                "issue_type_counts": dict(Counter(i["issue_type"] for i in issues)),
                "duplicate_group_count": len(dup_groups),
                "duplicate_kind_counts": dict(Counter(d["kind"] for d in dup_groups)),
                "exclusion_candidate_count": len(exclusions),
                "raw_token_length_stats": pcts,
                "sample_issues": issues[:30],
                "sample_duplicates": dup_groups[:15],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
