"""WU4: RAW/LEMMA/TAGGED relationship audit for WECCL 2.0.

Per logical document (filename stem): presence, usability, hashes, token counts,
header equality, TAGGED tag-format validity, LEMMA artifacts.
Outputs:
  variant_pairing.csv
  legacy_annotation_quality.json
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from scripts.corpus_paths import get_repo_root, get_corpus_root

CORPUS_ROOT = get_corpus_root()
DERIVED_ROOT = CORPUS_ROOT / "PREPARED" / "utf8"
REPO_ROOT = get_repo_root()
OUT_DIR = get_readiness_out_dir()
INVENTORY = OUT_DIR / "physical_inventory.csv"

VARIANT_DIRS = {
    "raw": "WECCL20/RAW",
    "lemma": "WECCL20/LEMMA",
    "tagged": "WECCL20/TAGGED",
}
# word_TAG where TAG contains no underscore (covers ._. ,_, ?_? I_PPIS1 ...)
TAG_TOKEN_RE = re.compile(r"^.+_[^_]+$")


def token_count(text: str) -> int:
    lines = text.splitlines()
    body = "\n".join(lines[1:]) if lines and lines[0].startswith("<") else text
    return len(body.split())


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(INVENTORY, encoding="utf-8-sig")))
    by_stem: dict[str, dict] = defaultdict(dict)
    for r in rows:
        if r["corpus_component"] in ("weccl_raw", "weccl_lemma", "weccl_tagged"):
            stem = Path(r["relative_path"]).stem
            variant = r["corpus_component"].split("_")[1]
            by_stem[stem][variant] = r

    pairing: list[dict] = []
    quality: dict = {
        "total_documents": len(by_stem),
        "missing_variants": Counter(),
        "corrupt_variants": Counter(),
        "header_mismatch_docs": [],
        "tag_format_invalid_tokens": {},
        "tag_format_low_docs": [],
        "lemma_tab_artifact_files": [],
        "token_ratio_stats": {},
        "token_ratio_outliers": [],
    }
    ratios: list[float] = []
    for stem in sorted(by_stem):
        v = by_stem[stem]
        rec = {
            "document_id": stem,
            "raw_present": "raw" in v,
            "lemma_present": "lemma" in v,
            "tagged_present": "tagged" in v,
        }
        texts: dict[str, str] = {}
        counts: dict[str, int] = {}
        for variant, dirname in VARIANT_DIRS.items():
            if variant not in v:
                rec[f"{variant}_usable"] = "missing"
                quality["missing_variants"][variant] += 1
                continue
            r = v[variant]
            rel = r["relative_path"]
            src_bytes = (CORPUS_ROOT / rel).read_bytes()
            all_nul = len(src_bytes) > 0 and src_bytes.count(b"\x00") == len(src_bytes)
            if all_nul:
                rec[f"{variant}_usable"] = "corrupt_all_nul"
                quality["corrupt_variants"][variant] += 1
                continue
            rec[f"{variant}_usable"] = "usable"
            rec[f"{variant}_sha256"] = r["sha256"]
            rec[f"{variant}_bytes"] = int(r["bytes"])
            text = (DERIVED_ROOT / rel).read_text(encoding="utf-8")
            texts[variant] = text
            counts[variant] = token_count(text)
            rec[f"{variant}_tokens"] = counts[variant]

        headers = {k: t.splitlines()[0] for k, t in texts.items()}
        if len(set(headers.values())) > 1:
            quality["header_mismatch_docs"].append(
                {"document_id": stem, "headers": headers}
            )
        rec["header_identical_across_variants"] = len(set(headers.values())) <= 1
        rec["header_raw"] = headers.get("raw", headers.get("tagged", ""))

        if "raw" in counts and "tagged" in counts and counts["raw"] > 0:
            ratio = counts["tagged"] / counts["raw"]
            rec["tagged_raw_token_ratio"] = round(ratio, 3)
            ratios.append(ratio)
            if ratio < 0.7 or ratio > 1.6:
                quality["token_ratio_outliers"].append(
                    {"document_id": stem, "raw": counts["raw"], "tagged": counts["tagged"], "ratio": round(ratio, 3)}
                )

        if "tagged" in texts:
            body = "\n".join(texts["tagged"].splitlines()[1:])
            toks = body.split()
            bad = [t for t in toks if not TAG_TOKEN_RE.match(t)]
            rate = (len(toks) - len(bad)) / len(toks) if toks else 0.0
            rec["tagged_format_rate"] = round(rate, 4)
            if bad:
                quality["tag_format_invalid_tokens"][stem] = {
                    "invalid": len(bad),
                    "total": len(toks),
                    "rate": round(rate, 4),
                    "samples": sorted(set(bad))[:10],
                }
                if rate < 0.98:
                    quality["tag_format_low_docs"].append(
                        {"document_id": stem, "rate": round(rate, 4), "invalid": len(bad), "total": len(toks)}
                    )

        if "lemma" in texts and "\t" in texts["lemma"]:
            quality["lemma_tab_artifact_files"].append(stem)
        pairing.append(rec)

    if ratios:
        ratios_sorted = sorted(ratios)
        n = len(ratios_sorted)
        quality["token_ratio_stats"] = {
            "n": n,
            "min": round(ratios_sorted[0], 3),
            "p1": round(ratios_sorted[int(n * 0.01)], 3),
            "p5": round(ratios_sorted[int(n * 0.05)], 3),
            "median": round(ratios_sorted[n // 2], 3),
            "p95": round(ratios_sorted[min(int(n * 0.95), n - 1)], 3),
            "max": round(ratios_sorted[-1], 3),
        }

    with open(OUT_DIR / "variant_pairing.csv", "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = sorted({k for rec in pairing for k in rec})
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(pairing)

    quality["missing_variants"] = dict(quality["missing_variants"])
    quality["corrupt_variants"] = dict(quality["corrupt_variants"])
    with open(OUT_DIR / "legacy_annotation_quality.json", "w", encoding="utf-8") as f:
        json.dump(quality, f, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "total_documents": quality["total_documents"],
                "missing_variants": quality["missing_variants"],
                "corrupt_variants": quality["corrupt_variants"],
                "header_mismatch_docs": quality["header_mismatch_docs"],
                "tag_format_low_docs": quality["tag_format_low_docs"][:20],
                "tag_format_low_doc_count": len(quality["tag_format_low_docs"]),
                "docs_with_invalid_tag_tokens": len(quality["tag_format_invalid_tokens"]),
                "invalid_token_sample": list(quality["tag_format_invalid_tokens"].items())[:5],
                "lemma_tab_artifact_files": quality["lemma_tab_artifact_files"],
                "token_ratio_stats": quality["token_ratio_stats"],
                "token_ratio_outlier_count": len(quality["token_ratio_outliers"]),
                "token_ratio_outliers": quality["token_ratio_outliers"][:20],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
