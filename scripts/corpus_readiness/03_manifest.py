"""WU3: canonical corpus manifest from physical files.

WECCL: iterate the union of document stems across RAW/LEMMA/TAGGED; parse the
header from RAW (preferred) or TAGGED (fallback, e.g., corrupt RAW variants).
SECCL: parse transcript headers (8 tags) + path-derived task/year/group.

Outputs:
  corpus_manifest.csv
  metadata_coverage.csv
  seccl_manifest.csv
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

CORPUS_ROOT = Path(r"A:\[Linguistics Data] Corpus\SWECCL 2.0")
DERIVED_ROOT = CORPUS_ROOT / "PREPARED" / "utf8"
REPO_ROOT = Path(r"A:\EAP Agent Project\writing-feedback-mvp")
OUT_DIR = REPO_ROOT / "docs" / "corpus-readiness" / "sweccl2" / "data"
INVENTORY = OUT_DIR / "physical_inventory.csv"

WECCL_HEADER_RE = re.compile(
    r"^<STU(?P<major>[12])><(?P<prompt>ARG\d{2}|EXP\d{2})><YEAR(?P<year>\d{2})>"
    r"<GRADE(?P<grade>[1-4])><(?P<timed>TIMED|UNTIMED)>"
)
SECCL_HEADER_RE = re.compile(
    r"^<SPOKEN><(?P<exam>TEM4|TEM8)><GRADE(?P<grade>\d)><YEAR(?P<year>\d{2})>"
    r"<GROUP(?P<group>\d{3})><TASKTYPE[ 1-3]*><SEX[^>]*><RANK=(?P<rank>\d)>"
)


def read_derived(rel: str) -> str | None:
    p = DERIVED_ROOT / rel
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8")


def is_all_nul(rel: str) -> bool:
    p = CORPUS_ROOT / rel
    if not p.exists():
        return True
    data = p.read_bytes()
    return len(data) > 0 and data.count(b"\x00") == len(data)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(INVENTORY, encoding="utf-8-sig")))
    weccl_by_stem: dict[str, dict] = defaultdict(dict)
    seccl_rows: list[dict] = []
    for r in rows:
        if r["corpus_component"] in ("weccl_raw", "weccl_lemma", "weccl_tagged"):
            stem = Path(r["relative_path"]).stem
            weccl_by_stem[stem][r["corpus_component"]] = r
        elif r["corpus_component"] == "seccl_texts":
            seccl_rows.append(r)

    weccl_out: list[dict] = []
    header_issues: list[str] = []
    for stem in sorted(weccl_by_stem):
        v = weccl_by_stem[stem]
        raw_rel = v.get("weccl_raw", {}).get("relative_path", "")
        tagged_rel = v.get("weccl_tagged", {}).get("relative_path", "")
        text = None
        metadata_source = ""
        if raw_rel and not is_all_nul(raw_rel):
            text = read_derived(raw_rel)
            metadata_source = "raw"
        if text is None and tagged_rel:
            text = read_derived(tagged_rel)
            metadata_source = "tagged"
        m = WECCL_HEADER_RE.match(text) if text else None
        prefix = stem[:4]
        if m is None:
            header_issues.append(f"{stem}: header not matched (metadata_source={metadata_source})")
            continue
        g = m.groupdict()
        genre = "argumentative" if g["prompt"].startswith("ARG") else "expository"
        filename_genre = "argumentative" if prefix == "WARG" else ("expository" if prefix == "WEXP" else "UNKNOWN")
        weccl_out.append(
            {
                "document_id": stem,
                "source_relative_path": raw_rel or tagged_rel,
                "derived_relative_path": raw_rel or tagged_rel,
                "source_sha256": v.get("weccl_raw", {}).get("sha256", v.get("weccl_tagged", {}).get("sha256", "")),
                "corpus": "weccl_2_0",
                "domain": "l2_writing",
                "genre": genre,
                "genre_from_filename": filename_genre,
                "prompt_id": g["prompt"],
                "major_type": "english_major" if g["major"] == "1" else "non_english_major",
                "entry_year": f"20{g['year']}",
                "grade": int(g["grade"]),
                "timed_status": "timed" if g["timed"] == "TIMED" else "untimed",
                "header_raw": m.group(0),
                "metadata_status": "parsed",
                "metadata_source": metadata_source,
                "raw_usable": "yes" if (raw_rel and not is_all_nul(raw_rel)) else ("no" if raw_rel else "missing"),
                "lemma_usable": "yes" if ("weccl_lemma" in v and not is_all_nul(v["weccl_lemma"]["relative_path"])) else ("no" if "weccl_lemma" in v else "missing"),
                "tagged_usable": "yes" if ("weccl_tagged" in v and not is_all_nul(v["weccl_tagged"]["relative_path"])) else ("no" if "weccl_tagged" in v else "missing"),
            }
        )

    seccl_out: list[dict] = []
    for r in seccl_rows:
        rel = r["relative_path"]
        parts = rel.split("/")
        task_folder = parts[2]
        year = parts[3] if len(parts) > 3 else ""
        group = parts[4] if len(parts) > 4 else ""
        fname = parts[-1]
        text = read_derived(rel) or ""
        m = SECCL_HEADER_RE.match(text)
        header_raw = text.splitlines()[0] if text else ""
        if m is None:
            header_issues.append(f"{rel}: seccl header not matched")
        g = m.groupdict() if m else {}
        task_no = ""
        if task_folder.startswith("TASK"):
            task_no = task_folder[4:] if task_folder != "TASK123" else "123"
        role = fname.split(".")[0][-1:] if fname else ""
        seccl_out.append(
            {
                "transcript_id": fname.replace(".txt", ""),
                "source_relative_path": rel,
                "source_sha256": r["sha256"],
                "exam": g.get("exam", "UNKNOWN"),
                "task_folder": task_folder,
                "task_no": task_no,
                "year_folder": year,
                "year_tag": f"20{g.get('year', '??')}" if g.get("year") else "",
                "group_folder": group,
                "grade": g.get("grade", ""),
                "rank": g.get("rank", ""),
                "role_in_task3": role,
                "header_raw": header_raw[:200],
                "metadata_status": "parsed" if m else "unparsed",
            }
        )

    with open(OUT_DIR / "corpus_manifest.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "document_id", "source_relative_path", "derived_relative_path", "source_sha256",
                "corpus", "domain", "genre", "genre_from_filename", "prompt_id", "major_type",
                "entry_year", "grade", "timed_status", "header_raw", "metadata_status",
                "metadata_source", "raw_usable", "lemma_usable", "tagged_usable",
            ],
        )
        writer.writeheader()
        writer.writerows(weccl_out)
    with open(OUT_DIR / "seccl_manifest.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "transcript_id", "source_relative_path", "source_sha256", "exam", "task_folder",
                "task_no", "year_folder", "year_tag", "group_folder", "grade", "rank",
                "role_in_task3", "header_raw", "metadata_status",
            ],
        )
        writer.writeheader()
        writer.writerows(seccl_out)

    dims = {
        "genre": Counter(x["genre"] for x in weccl_out),
        "prompt_id": Counter(x["prompt_id"] for x in weccl_out),
        "major_type": Counter(x["major_type"] for x in weccl_out),
        "entry_year": Counter(x["entry_year"] for x in weccl_out),
        "grade": Counter(x["grade"] for x in weccl_out),
        "timed_status": Counter(x["timed_status"] for x in weccl_out),
    }
    coverage = []
    for dim, counter in dims.items():
        present = sum(counter.values())
        coverage.append(
            {
                "dimension": dim,
                "populated_n": present,
                "total_n": len(weccl_out),
                "coverage_pct": round(present / len(weccl_out) * 100, 2) if weccl_out else 0.0,
                "distinct_values": len(counter),
                "values": json.dumps(dict(sorted(counter.items())), ensure_ascii=False),
            }
        )
    for dim, counter in {
        "exam": Counter(x["exam"] for x in seccl_out),
        "task_folder": Counter(x["task_folder"] for x in seccl_out),
        "year_folder": Counter(x["year_folder"] for x in seccl_out),
        "metadata_status": Counter(x["metadata_status"] for x in seccl_out),
    }.items():
        present = sum(counter.values())
        coverage.append(
            {
                "dimension": f"seccl_{dim}",
                "populated_n": present,
                "total_n": len(seccl_out),
                "coverage_pct": round(present / len(seccl_out) * 100, 2) if seccl_out else 0.0,
                "distinct_values": len(counter),
                "values": json.dumps(dict(sorted(counter.items())), ensure_ascii=False),
            }
        )
    with open(OUT_DIR / "metadata_coverage.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["dimension", "populated_n", "total_n", "coverage_pct", "distinct_values", "values"])
        writer.writeheader()
        writer.writerows(coverage)

    summary = {
        "weccl_manifest_rows": len(weccl_out),
        "seccl_manifest_rows": len(seccl_out),
        "header_issue_count": len(header_issues),
        "header_issues": header_issues[:50],
        "dimensions": coverage,
    }
    with open(OUT_DIR / "manifest_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
