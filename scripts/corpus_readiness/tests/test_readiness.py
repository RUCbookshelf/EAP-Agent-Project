"""Deterministic tests for corpus-readiness artifacts (WU1-WU6 outputs)."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.corpus_paths import get_corpus_root, get_repo_root

REPO = get_repo_root()
DATA = REPO / "docs" / "corpus-readiness" / "sweccl2" / "data"

BANNED = ("level", "score", "ability", "mastery", "gain", "cefr")


def read_csv(name: str) -> list[dict]:
    with open(DATA / name, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def test_inventory_schema_and_counts():
    rows = read_csv("physical_inventory.csv")
    assert len(rows) == 19858
    assert all(r["sha256"] for r in rows)
    from collections import Counter

    comp = Counter(r["corpus_component"] for r in rows)
    assert comp["weccl_raw"] == 4950
    assert comp["weccl_lemma"] == 4950
    assert comp["weccl_tagged"] == 4950
    assert comp["seccl_audio"] == 2139
    assert comp["seccl_texts"] == 2852
    assert comp["tools"] == 13


def test_manifest_full_coverage():
    rows = read_csv("corpus_manifest.csv")
    assert len(rows) == 4950
    assert all(r["metadata_status"] == "parsed" for r in rows)
    for dim in ("genre", "prompt_id", "major_type", "entry_year", "grade", "timed_status"):
        assert all(r[dim] for r in rows), dim


def test_derived_roundtrip_sample():
    manifest = read_csv("derived_manifest.csv")
    ok = [m for m in manifest if m["conversion_status"] == "OK"]
    assert len(ok) == 17703
    import random

    random.seed(7)
    corpus = get_corpus_root()
    for m in random.sample(ok, 25):
        src = (corpus / m["source_relative_path"]).read_bytes()
        derived = (corpus / "PREPARED" / "utf8" / m["source_relative_path"]).read_bytes()
        enc = m["encoding"]
        assert derived.decode("utf-8").encode(enc) == src


def test_documentation_vs_physical_counts_match():
    rows = read_csv("documentation_vs_physical.csv")
    mismatches = [r for r in rows if r["n_status"] != "MATCH"]
    assert mismatches == []


def test_duplicate_report_members_exist():
    rows = read_csv("duplicate_report.csv")
    raw_stems = {r["document_id"] for r in read_csv("corpus_manifest.csv")}
    for r in rows:
        for member in r["members"].split(","):
            assert Path(member).stem in raw_stems


def test_no_banned_tokens_in_field_names():
    import os
    import re

    for name in os.listdir(DATA):
        if name.endswith(".csv"):
            with open(DATA / name, encoding="utf-8-sig") as f:
                words = set(re.findall(r"[a-z]+", f.readline().lower()))
            for token in BANNED:
                assert token not in words, (name, token)


def test_seccl_manifest_counts():
    rows = read_csv("seccl_manifest.csv")
    from collections import Counter

    tasks = Counter(r["task_folder"] for r in rows)
    assert tasks == {"TASK1": 713, "TASK2": 713, "TASK3": 713, "TASK123": 713}
    assert all(r["metadata_status"] == "parsed" for r in rows)


def test_pairing_no_missing_variants():
    rows = read_csv("variant_pairing.csv")
    assert len(rows) == 4950
    for r in rows:
        assert r["raw_present"] == "True" or r["raw_present"] == "true" or r["raw_present"] == "1"
        assert r["lemma_present"] == "True" or r["lemma_present"] == "true" or r["lemma_present"] == "1"
        assert r["tagged_present"] == "True" or r["tagged_present"] == "true" or r["tagged_present"] == "1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
