"""WU1: deterministic physical inventory of the SWECCL 2.0 corpus root.

Outputs (UTF-8 with BOM for Excel compatibility):
  docs/corpus-readiness/sweccl2/data/physical_inventory.csv
  docs/corpus-readiness/sweccl2/data/physical_inventory_summary.json

Reproducible: sorted traversal, chunked sha256, fixed column order.
Reads only; never modifies corpus files.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    from charset_normalizer import from_bytes
    HAS_CN = True
except Exception:
    HAS_CN = False

CORPUS_ROOT = Path(r"A:\[Linguistics Data] Corpus\SWECCL 2.0")
REPO_ROOT = Path(r"A:\EAP Agent Project\writing-feedback-mvp")
OUT_DIR = REPO_ROOT / "docs" / "corpus-readiness" / "sweccl2" / "data"
CHUNK = 1024 * 1024

COMPONENT_RULES = [
    (("WECCL20", "RAW"), "weccl_raw", "raw"),
    (("WECCL20", "LEMMA"), "weccl_lemma", "lemma"),
    (("WECCL20", "TAGGED"), "weccl_tagged", "tagged"),
    (("SECCL20", "AUDIO"), "seccl_audio", None),
    (("SECCL20", "TEXTS"), "seccl_texts", "transcript"),
    (("TOOLS",), "tools", None),
]


def component_of(rel_parts: tuple[str, ...]) -> tuple[str, str | None]:
    for prefixes, component, variant in COMPONENT_RULES:
        if len(rel_parts) >= len(prefixes) and tuple(rel_parts[: len(prefixes)]) == prefixes:
            return component, variant
    return "root_artifact", None


def detect_encoding(raw: bytes) -> tuple[str, str]:
    """Return (encoding, status). status in ascii/utf8/gbk/cn_detect/needs_review."""
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(CHUNK)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    errors: list[str] = []
    for dirpath, dirnames, filenames in os.walk(CORPUS_ROOT):
        dirnames[:] = [d for d in dirnames if d != "PREPARED"]  # derived layer, not source
        dirnames.sort()
        for name in sorted(filenames):
            full = Path(dirpath) / name
            rel = full.relative_to(CORPUS_ROOT)
            rel_parts = tuple(rel.parts)
            component, variant = component_of(rel_parts)
            try:
                size = full.stat().st_size
                digest = sha256_file(full)
                with open(full, "rb") as f:
                    head = f.read(65536)
                enc, enc_status = detect_encoding(head)
                status = "ok"
            except Exception as exc:  # noqa: BLE001
                size = -1
                digest = ""
                enc = ""
                enc_status = "unreadable"
                status = f"error:{type(exc).__name__}"
                errors.append(f"{rel}: {exc}")
            rows.append(
                {
                    "relative_path": rel.as_posix(),
                    "filename": name,
                    "extension": full.suffix.lower(),
                    "bytes": size,
                    "sha256": digest,
                    "detected_encoding": enc,
                    "encoding_status": enc_status,
                    "corpus_component": component,
                    "text_variant": variant if variant else "",
                    "physical_status": status,
                }
            )

    csv_path = OUT_DIR / "physical_inventory.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "relative_path",
                "filename",
                "extension",
                "bytes",
                "sha256",
                "detected_encoding",
                "encoding_status",
                "corpus_component",
                "text_variant",
                "physical_status",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    comp_counts = Counter(r["corpus_component"] for r in rows)
    variant_counts = Counter(r["text_variant"] for r in rows if r["text_variant"])
    ext_counts = Counter(r["extension"] for r in rows)
    enc_counts = Counter(r["detected_encoding"] for r in rows)
    status_counts = Counter(r["physical_status"] for r in rows)
    bytes_by_comp = defaultdict(int)
    for r in rows:
        if r["bytes"] > 0:
            bytes_by_comp[r["corpus_component"]] += r["bytes"]
    summary = {
        "corpus_root": str(CORPUS_ROOT),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "total_files": len(rows),
        "total_bytes": sum(max(r["bytes"], 0) for r in rows),
        "component_counts": dict(sorted(comp_counts.items())),
        "component_bytes": {k: v for k, v in sorted(bytes_by_comp.items())},
        "variant_counts": dict(sorted(variant_counts.items())),
        "extension_counts": dict(sorted(ext_counts.items())),
        "encoding_counts": dict(sorted(enc_counts.items())),
        "physical_status_counts": dict(sorted(status_counts.items())),
        "read_errors": errors,
    }
    with open(OUT_DIR / "physical_inventory_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in summary.items() if k != "read_errors"}, ensure_ascii=False, indent=2))
    if errors:
        print("READ ERRORS:")
        for e in errors:
            print(" ", e)


if __name__ == "__main__":
    main()
