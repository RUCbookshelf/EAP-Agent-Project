r"""WU2: encoding audit and derived canonical UTF-8 layer.

For every .txt file under the corpus root:
  1. detect encoding (ascii -> utf-8 strict -> gbk strict -> charset_normalizer)
  2. strict decode with round-trip check (derived.encode(enc) == original bytes)
  3. write a derived UTF-8 copy (original newlines preserved) under
     <CORPUS_ROOT>/PREPARED/utf8/<component>/... (corpus root resolved
     portably via scripts/corpus_paths.py; no machine-specific literal)
  4. record provenance in derived_manifest.csv

Never modifies source files.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from scripts.corpus_paths import get_repo_root, get_corpus_root

try:
    from charset_normalizer import from_bytes
    HAS_CN = True
except Exception:
    HAS_CN = False

CORPUS_ROOT = get_corpus_root()
REPO_ROOT = get_repo_root()
INVENTORY = REPO_ROOT / "docs" / "corpus-readiness" / "sweccl2" / "data" / "physical_inventory.csv"
OUT_DIR = get_readiness_out_dir()
DERIVED_ROOT = CORPUS_ROOT / "PREPARED" / "utf8"


def detect_encoding(raw: bytes) -> tuple[str, str]:
    if not raw:
        return "empty", "ascii"
    try:
        raw.decode("ascii")
        return "ascii", "ascii"
    except UnicodeDecodeError:
        pass
    try:
        raw.decode("utf-8")
        return "utf-8", "utf8"
    except UnicodeDecodeError:
        pass
    try:
        raw.decode("gbk")
        return "gbk", "gbk"
    except UnicodeDecodeError:
        pass
    if HAS_CN:
        res = from_bytes(raw[:65536]).best()
        if res is not None and res.encoding:
            return res.encoding, "cn_detect"
    return "needs_review", "needs_review"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def newline_profile(data: bytes) -> str:
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    cr = data.count(b"\r") - crlf
    if crlf == 0 and lf == 0 and cr == 0:
        return "none"
    return f"crlf={crlf},lf={lf},cr={cr}"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(INVENTORY, encoding="utf-8-sig")))
    samples: list[dict] = []
    manifest: list[dict] = []
    stats: dict = {
        "text_files": 0,
        "decoded_ok": 0,
        "needs_review": 0,
        "encoding_counter": Counter(),
        "newline_profiles": Counter(),
        "non_ascii_files_by_component": Counter(),
    }
    for r in rows:
        if r["extension"] != ".txt":
            continue
        stats["text_files"] += 1
        src = CORPUS_ROOT / r["relative_path"]
        data = src.read_bytes()
        enc, status = detect_encoding(data)
        stats["encoding_counter"][enc] += 1
        stats["newline_profiles"][newline_profile(data)] += 1
        if enc == "needs_review":
            stats["needs_review"] += 1
            manifest.append(
                {
                    "source_relative_path": r["relative_path"],
                    "source_sha256": r["sha256"],
                    "derived_relative_path": "",
                    "derived_sha256": "",
                    "encoding": enc,
                    "conversion_status": "NEEDS_REVIEW",
                    "note": "cannot decode losslessly",
                }
            )
            continue
        try:
            text = data.decode(enc)
        except UnicodeDecodeError as exc:
            stats["needs_review"] += 1
            manifest.append(
                {
                    "source_relative_path": r["relative_path"],
                    "source_sha256": r["sha256"],
                    "derived_relative_path": "",
                    "derived_sha256": "",
                    "encoding": enc,
                    "conversion_status": "NEEDS_REVIEW",
                    "note": f"decode failed: {exc}",
                }
            )
            continue
        if text.encode(enc) != data:
            stats["needs_review"] += 1
            manifest.append(
                {
                    "source_relative_path": r["relative_path"],
                    "source_sha256": r["sha256"],
                    "derived_relative_path": "",
                    "derived_sha256": "",
                    "encoding": enc,
                    "conversion_status": "NEEDS_REVIEW",
                    "note": "round-trip mismatch",
                }
            )
            continue
        stats["decoded_ok"] += 1
        if enc != "ascii":
            stats["non_ascii_files_by_component"][r["corpus_component"]] += 1
        derived = DERIVED_ROOT / r["relative_path"]
        derived.parent.mkdir(parents=True, exist_ok=True)
        out_bytes = text.encode("utf-8")
        derived.write_bytes(out_bytes)
        manifest.append(
            {
                "source_relative_path": r["relative_path"],
                "source_sha256": r["sha256"],
                "derived_relative_path": derived.relative_to(DERIVED_ROOT).as_posix(),
                "derived_sha256": sha256_bytes(out_bytes),
                "encoding": enc,
                "conversion_status": "OK",
                "note": "utf-8 derived, newlines preserved",
            }
        )
        if enc != "ascii" and len(samples) < 15:
            idx = next((i for i, x in enumerate(data) if x > 127), -1)
            ctx = data[max(0, idx - 50) : idx + 70]
            samples.append(
                {
                    "relative_path": r["relative_path"],
                    "encoding": enc,
                    "byte_offset": idx,
                    "context_gbk": ctx.decode("gbk", errors="replace") if enc == "gbk" else ctx.decode(enc, errors="replace"),
                }
            )

    manifest_path = OUT_DIR / "derived_manifest.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "source_relative_path",
                "source_sha256",
                "derived_relative_path",
                "derived_sha256",
                "encoding",
                "conversion_status",
                "note",
            ],
        )
        writer.writeheader()
        writer.writerows(manifest)

    report = {
        "derived_root": str(DERIVED_ROOT),
        "text_files": stats["text_files"],
        "decoded_ok": stats["decoded_ok"],
        "needs_review": stats["needs_review"],
        "encoding_counts": dict(sorted(stats["encoding_counter"].items())),
        "newline_profiles": dict(stats["newline_profiles"].most_common()),
        "non_ascii_files_by_component": dict(sorted(stats["non_ascii_files_by_component"].items())),
        "sample_non_ascii_contexts": samples,
    }
    with open(OUT_DIR / "encoding_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != "sample_non_ascii_contexts"}, ensure_ascii=False, indent=2))
    print("\nNON-ASCII SAMPLES:")
    for s in samples:
        print(f"  {s['relative_path']} [{s['encoding']}] @{s['byte_offset']}: {s['context_gbk']!r}")


if __name__ == "__main__":
    main()
