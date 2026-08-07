"""WU6: corpus composition and documentation-vs-physical comparison.

Inputs: corpus_manifest.csv, derived UTF-8 layer.
Outputs:
  corpus_composition.csv
  documentation_vs_physical.csv
  corpus_composition.json
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

CORPUS_ROOT = Path(r"A:\[Linguistics Data] Corpus\SWECCL 2.0")
DERIVED_ROOT = CORPUS_ROOT / "PREPARED" / "utf8"
REPO_ROOT = Path(r"A:\EAP Agent Project\writing-feedback-mvp")
OUT_DIR = REPO_ROOT / "docs" / "corpus-readiness" / "sweccl2" / "data"
MANIFEST = OUT_DIR / "corpus_manifest.csv"

# Documentation expectations from the manual (see SWECCL2.0_语料库概况报告.md,
# PDF pages 26-27, tables 3.1/3.2). Counts and token totals.
DOC = {
    "total_texts": 4950,
    "total_tokens": 1248476,
    "genre": {"argumentative": (4680, 1207968), "expository": (270, 40508)},
    "major_type": {"english_major": (4359, 1131901), "non_english_major": (591, 116575)},
    "entry_year": {
        "2003": (68, 21517),
        "2004": (307, 89236),
        "2005": (1672, 445769),
        "2006": (2450, 602803),
        "2007": (453, 89151),
    },
    "grade": {"1": (1549, 371431), "2": (2172, 567046), "3": (1108, 268032), "4": (121, 41967)},
    "timed_status": {"timed": (2499, 604636), "untimed": (2451, 643840)},
    "prompt": {
        "ARG01": (133, 31382), "ARG02": (426, 90195), "ARG03": (87, 22265), "ARG04": (239, 75492),
        "ARG05": (192, 48137), "ARG06": (127, 28695), "ARG07": (177, 43238), "ARG08": (214, 61241),
        "ARG09": (154, 30959), "ARG10": (256, 64483), "ARG11": (156, 39324), "ARG12": (108, 24572),
        "ARG13": (14, 3372), "ARG14": (136, 42628), "ARG15": (126, 31211), "ARG16": (66, 18341),
        "ARG17": (656, 147984), "ARG18": (43, 12099), "ARG19": (18, 5035), "ARG20": (32, 7793),
        "ARG21": (157, 38944), "ARG22": (165, 48854), "ARG23": (391, 90069), "ARG24": (89, 22237),
        "ARG25": (99, 32173), "ARG26": (419, 147245), "EXP01": (270, 40508),
    },
}


def raw_tokens(rel: str) -> int:
    p = DERIVED_ROOT / rel
    if not p.exists():
        return 0
    lines = p.read_text(encoding="utf-8").splitlines()
    body = "\n".join(lines[1:]) if lines and lines[0].startswith("<") else "\n".join(lines)
    return len(body.split())


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8-sig")))
    docs = [r for r in rows if r["corpus"] == "weccl_2_0"]
    tokens = {r["document_id"]: raw_tokens(r["source_relative_path"]) for r in docs}

    composition: list[dict] = []
    dims = {
        "genre": lambda r: r["genre"],
        "prompt_id": lambda r: r["prompt_id"],
        "major_type": lambda r: r["major_type"],
        "entry_year": lambda r: r["entry_year"],
        "grade": lambda r: str(r["grade"]),
        "timed_status": lambda r: r["timed_status"],
    }
    for dim, fn in dims.items():
        counter = Counter(fn(r) for r in docs)
        tok_counter = Counter()
        for r in docs:
            tok_counter[fn(r)] += tokens[r["document_id"]]
        for value in sorted(counter):
            n = counter[value]
            composition.append(
                {
                    "dimension": dim,
                    "value": value,
                    "n": n,
                    "pct": round(n / len(docs) * 100, 2),
                    "physical_tokens": tok_counter[value],
                }
            )
    composition.append(
        {
            "dimension": "total",
            "value": "all",
            "n": len(docs),
            "pct": 100.0,
            "physical_tokens": sum(tokens.values()),
        }
    )
    with open(OUT_DIR / "corpus_composition.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["dimension", "value", "n", "pct", "physical_tokens"])
        writer.writeheader()
        writer.writerows(composition)

    # documentation vs physical
    cmp_rows: list[dict] = []

    def add(dim: str, value: str, doc_n, doc_tok, phys_n, phys_tok) -> None:
        n_status = "MATCH" if doc_n == phys_n else "MISMATCH"
        t_status = "MATCH" if doc_tok == phys_tok else "MISMATCH"
        cmp_rows.append(
            {
                "dimension": dim,
                "value": value,
                "doc_n": doc_n,
                "physical_n": phys_n,
                "n_status": n_status,
                "doc_tokens": doc_tok,
                "physical_tokens": phys_tok,
                "token_status": t_status,
                "note": "token counts use different counters (manual: WordSmith 5.0; physical: whitespace split, header excluded)",
            }
        )

    by_dim = {}
    for c in composition:
        by_dim.setdefault(c["dimension"], {})[c["value"]] = c
    add("total", "all", DOC["total_texts"], DOC["total_tokens"], by_dim["total"]["all"]["n"], by_dim["total"]["all"]["physical_tokens"])
    for dim, doc_map in [
        ("genre", DOC["genre"]),
        ("major_type", DOC["major_type"]),
        ("entry_year", DOC["entry_year"]),
        ("grade", DOC["grade"]),
        ("timed_status", DOC["timed_status"]),
        ("prompt_id", DOC["prompt"]),
    ]:
        for value, (doc_n, doc_tok) in doc_map.items():
            phys = by_dim[dim].get(str(value))
            if phys is None:
                cmp_rows.append({"dimension": dim, "value": value, "doc_n": doc_n, "physical_n": 0, "n_status": "MISSING", "doc_tokens": doc_tok, "physical_tokens": 0, "token_status": "MISSING", "note": "no physical records"})
            else:
                add(dim, value, doc_n, doc_tok, phys["n"], phys["physical_tokens"])

    with open(OUT_DIR / "documentation_vs_physical.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["dimension", "value", "doc_n", "physical_n", "n_status", "doc_tokens", "physical_tokens", "token_status", "note"])
        writer.writeheader()
        writer.writerows(cmp_rows)

    summary = {
        "usable_logical_texts": len(docs),
        "physical_raw_tokens_total": sum(tokens.values()),
        "documentation_total_texts": DOC["total_texts"],
        "documentation_total_tokens": DOC["total_tokens"],
        "n_mismatches": [r for r in cmp_rows if r["n_status"] != "MATCH"],
        "token_mismatch_count": sum(1 for r in cmp_rows if r["token_status"] == "MISMATCH"),
        "token_mismatch_sample": [r for r in cmp_rows if r["token_status"] == "MISMATCH"][:10],
    }
    with open(OUT_DIR / "corpus_composition.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
