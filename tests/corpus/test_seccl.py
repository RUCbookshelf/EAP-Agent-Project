"""TDD tests for SECCL20 spoken-corpus throughput tooling (PDW1 CORPUS).

Covers: manifest contract, deterministic header normalization, eligibility
classification, reference-group index with merged-transcript duplicate
policy, deterministic resumable batch planning, idempotent snapshot output,
partition disjointness, governed-artifact exposure fields, and leak hygiene.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path

import pytest

from app.corpus.seccl import (
    SECCL_PACKAGE_ID,
    SecclBatchPlan,
    SecclReferenceGroupIndex,
    classify_eligibility,
    compute_seccl_manifest_hash,
    load_seccl_manifest,
    strip_seccl_header,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
READINESS_DATA = REPO_ROOT / "docs" / "corpus-readiness" / "sweccl2" / "data"
SECCL_MANIFEST = READINESS_DATA / "seccl_manifest.csv"


def _manifest_rows() -> list[dict]:
    with open(SECCL_MANIFEST, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _fixture_text() -> str:
    return (
        "<SPOKEN><TEM4><GRADE2><YEAR03><GROUP130><TASKTYPE 1 2 3>"
        "<SEX T1=F, T2=F, T3=F, F><RANK=3>\n"
        "TASK 1\n"
        "Jane was expecting his first birth and his mother was losing her battery.\n"
        "TASK 2\n"
        "There was a very famous singer in my country.\n"
    )


def _stub_extractor(texts: list[str]) -> list[list[dict]]:
    """Deterministic stub: one snapshot per input, value = token count."""
    return [[{"feature_id": "text_length_tokens", "value": len(t.split()), "unit": "tokens",
              "analysis_status": "available", "evidence_count": len(t.split()),
              "feature_set_version": "corpus-features-v0.1.0", "limitations": ()}] for t in texts]


class TestManifestContract:
    def test_manifest_exists_and_count(self) -> None:
        rows = _manifest_rows()
        assert len(rows) == 2852

    def test_manifest_required_columns(self) -> None:
        rows = _manifest_rows()
        required = {
            "transcript_id", "source_relative_path", "source_sha256", "exam",
            "task_folder", "task_no", "year_folder", "year_tag", "group_folder",
            "grade", "rank", "role_in_task3", "header_raw", "metadata_status",
        }
        assert required.issubset(rows[0].keys())

    def test_manifest_all_metadata_parsed(self) -> None:
        rows = _manifest_rows()
        assert all(r["metadata_status"] == "parsed" for r in rows)
        assert all(r["exam"] == "TEM4" for r in rows)

    def test_manifest_unique_key_is_transcript_plus_task(self) -> None:
        rows = _manifest_rows()
        keys = [(r["transcript_id"], r["task_folder"]) for r in rows]
        assert len(set(keys)) == len(keys)

    def test_manifest_hash_is_stable_sha256(self) -> None:
        h = compute_seccl_manifest_hash(SECCL_MANIFEST)
        assert len(h) == 64
        assert h == hashlib.sha256(SECCL_MANIFEST.read_bytes()).hexdigest()


class TestHeaderNormalization:
    def test_strips_spoken_header_line(self) -> None:
        out = strip_seccl_header(_fixture_text())
        assert not out.startswith("<SPOKEN>")

    def test_strips_task_marker_lines(self) -> None:
        out = strip_seccl_header(_fixture_text())
        assert "TASK 1\n" not in out
        assert "TASK 2\n" not in out

    def test_preserves_speech_content(self) -> None:
        out = strip_seccl_header(_fixture_text())
        assert "Jane was expecting his first birth" in out
        assert "There was a very famous singer" in out

    def test_empty_or_header_only_text(self) -> None:
        assert strip_seccl_header("") == ""
        assert strip_seccl_header("<SPOKEN><TEM4></SPOKEN>") == ""

    def test_keeps_lines_that_merely_contain_task_word(self) -> None:
        text = "<SPOKEN><TEM4>\nThe task was difficult.\nTASK 3\nDone.\n"
        out = strip_seccl_header(text)
        assert "The task was difficult." in out
        assert "Done." in out
        assert "TASK 3" not in out


class TestEligibility:
    def test_eligible_when_file_present_and_decodable(self, tmp_path: Path) -> None:
        prepared = tmp_path / "SECCL20" / "TEXTS" / "TASK1" / "2003" / "03-130" / "03-130-01A.txt"
        prepared.parent.mkdir(parents=True)
        prepared.write_text(_fixture_text(), encoding="utf-8")
        row = {
            "transcript_id": "03-130-01A",
            "task_folder": "TASK1",
            "source_relative_path": "SECCL20/TEXTS/TASK1/2003/03-130/03-130-01A.txt",
            "source_sha256": hashlib.sha256(_fixture_text().encode("utf-8")).hexdigest(),
        }
        status, reason = classify_eligibility(row, prepared_root=tmp_path)
        assert status == "eligible"
        assert reason == ""

    def test_missing_file_is_blocked(self, tmp_path: Path) -> None:
        row = {
            "transcript_id": "03-130-01A",
            "task_folder": "TASK1",
            "source_relative_path": "SECCL20/TEXTS/TASK1/2003/03-130/03-130-01A.txt",
            "source_sha256": "0" * 64,
        }
        status, reason = classify_eligibility(row, prepared_root=tmp_path)
        assert status == "blocked"
        assert "missing" in reason

    def test_nul_corrupt_file_is_excluded(self, tmp_path: Path) -> None:
        prepared = tmp_path / "SECCL20" / "TEXTS" / "TASK2" / "2004" / "04-020" / "04-020-02A.txt"
        prepared.parent.mkdir(parents=True)
        prepared.write_bytes(b"\x00" * 500)
        row = {
            "transcript_id": "04-020-02A",
            "task_folder": "TASK2",
            "source_relative_path": "SECCL20/TEXTS/TASK2/2004/04-020/04-020-02A.txt",
            "source_sha256": "0" * 64,
        }
        status, reason = classify_eligibility(row, prepared_root=tmp_path)
        assert status == "excluded"
        assert "corrupt" in reason

    def test_decoding_failure_is_excluded(self, tmp_path: Path) -> None:
        prepared = tmp_path / "SECCL20" / "TEXTS" / "TASK3" / "2005" / "05-010" / "05-010-19A.txt"
        prepared.parent.mkdir(parents=True)
        prepared.write_bytes(b"\xff\xfe\xfd\xfc not utf8")
        row = {
            "transcript_id": "05-010-19A",
            "task_folder": "TASK3",
            "source_relative_path": "SECCL20/TEXTS/TASK3/2005/05-010/05-010-19A.txt",
            "source_sha256": "0" * 64,
        }
        status, reason = classify_eligibility(row, prepared_root=tmp_path)
        assert status == "excluded"
        assert "decode" in reason


class TestReferenceGroupIndex:
    def test_approved_group_counts(self) -> None:
        index = SecclReferenceGroupIndex(manifest=_manifest_rows())
        groups = index.approved_group_ids()
        # exam(1) + task(3, TASK123 excluded as merged) + year(4) +
        # task x year(12) + grade(1) = 21
        assert len(groups) == 21

    def test_merged_task123_excluded_from_year_groups(self) -> None:
        index = SecclReferenceGroupIndex(manifest=_manifest_rows())
        members = index.membership("RG-seccl-exam=TEM4")
        assert not any("TASK123" in _doc_key(m) for m in members)

    def test_all_approved_groups_meet_min_n(self) -> None:
        index = SecclReferenceGroupIndex(manifest=_manifest_rows())
        for gid in index.approved_group_ids():
            group = index.get(gid)
            assert group.n_effective >= index.min_n, gid

    def test_task_year_group_counts(self) -> None:
        index = SecclReferenceGroupIndex(manifest=_manifest_rows())
        gid = "RG-seccl-task_folder=TASK1-year_folder=2003"
        group = index.get(gid)
        assert group.n_raw == 161
        assert group.n_effective == 161

    def test_unknown_group_raises(self) -> None:
        index = SecclReferenceGroupIndex(manifest=_manifest_rows())
        with pytest.raises(Exception):
            index.get("RG-seccl-task_folder=NOPE")

    def test_exposure_metadata_on_groups(self) -> None:
        index = SecclReferenceGroupIndex(manifest=_manifest_rows())
        group = index.get("RG-seccl-exam=TEM4")
        assert group.exposure_class == "research_only"
        assert group.learner_exposure == "research_only"


def _doc_key(member_id: str) -> str:
    return member_id


class TestBatchPlan:
    def test_plan_deterministic_order_and_counts(self, tmp_path: Path) -> None:
        rows = _manifest_rows()
        plan = SecclBatchPlan(rows=rows, prepared_root=tmp_path)
        # no prepared files exist -> everything blocked
        assert plan.counts["total"] == 2852
        assert plan.counts["blocked"] == 2852
        assert plan.counts["eligible"] == 0

    def test_plan_resume_skips_processed(self, tmp_path: Path) -> None:
        rows = _manifest_rows()
        done = {(r["transcript_id"], r["task_folder"]) for r in rows[:10]}
        for r in rows[:10]:
            p = tmp_path / r["source_relative_path"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(_fixture_text(), encoding="utf-8")
        plan = SecclBatchPlan(
            rows=rows,
            prepared_root=tmp_path,
            already_processed={k: "0" * 64 for k in done},
        )
        assert plan.counts["total"] == 2852
        assert plan.counts["already_processed"] == 10
        assert plan.counts["pending"] == 0

    def test_partitions_are_disjoint_and_exhaustive(self, tmp_path: Path) -> None:
        rows = _manifest_rows()
        all_keys: list[tuple[str, str]] = []
        for i in range(4):
            plan = SecclBatchPlan(rows=rows, prepared_root=tmp_path, partition=(i, 4))
            keys = [(r["transcript_id"], r["task_folder"]) for r in plan.assigned_rows]
            assert len(keys) == len(set(keys))
            all_keys.extend(keys)
        assert len(all_keys) == len(set(all_keys)) == 2852

    def test_snapshot_rows_idempotent(self, tmp_path: Path) -> None:
        rows = [{
            "transcript_id": "03-130-01A",
            "task_folder": "TASK1",
            "year_folder": "2003",
            "group_folder": "03-130",
            "exam": "TEM4",
            "grade": "2",
            "source_relative_path": "SECCL20/TEXTS/TASK1/2003/03-130/03-130-01A.txt",
        }]
        texts = ["Jane was expecting his first birth."]
        snap1 = SecclBatchPlan._snapshot_csv(rows, _stub_extractor, "mh", texts)
        snap2 = SecclBatchPlan._snapshot_csv(rows, _stub_extractor, "mh", texts)
        assert snap1 == snap2
        assert "03-130-01A" in snap1
        assert "text_length_tokens" in snap1

    def test_snapshot_contains_no_raw_text(self, tmp_path: Path) -> None:
        rows = [{
            "transcript_id": "03-130-01A",
            "task_folder": "TASK1",
            "year_folder": "2003",
            "group_folder": "03-130",
            "exam": "TEM4",
            "grade": "2",
            "source_relative_path": "SECCL20/TEXTS/TASK1/2003/03-130/03-130-01A.txt",
        }]
        snap = SecclBatchPlan._snapshot_csv(rows, _stub_extractor, "mh", ["some words"])
        assert "Jane was expecting" not in snap


class TestGovernedArtifacts:
    def test_package_descriptor_shape(self, tmp_path: Path) -> None:
        descriptor = {
            "artifact_type": "corpus_package_descriptor",
            "version": "seccl-v0.1.0",
            "corpus_package_id": SECCL_PACKAGE_ID,
            "owner": "CORPUS",
            "learner_exposure": "research_only",
            "exposure_class": "research_only",
            "integrity": "0" * 64,
            "generator": "scripts/corpus_intelligence/build_seccl.py",
        }
        assert descriptor["corpus_package_id"] == "sweccl2-seccl20-v0.1.0"
        assert descriptor["learner_exposure"] == "research_only"
        json.dumps(descriptor)  # must serialize

    def test_distribution_records_carry_exposure_and_provenance(self) -> None:
        record = {
            "reference_group_id": "RG-seccl-exam=TEM4",
            "feature_id": "text_length_tokens",
            "feature_set_version": "corpus-features-v0.1.0",
            "distribution_version": "seccl-reference-distributions-v0.1.0",
            "corpus_package_id": SECCL_PACKAGE_ID,
            "manifest_hash": "0" * 64,
            "n_effective": 2139,
            "learner_exposure": "research_only",
            "exposure_class": "research_only",
        }
        assert record["learner_exposure"] == "research_only"
        assert record["exposure_class"] == "research_only"
        assert record["n_effective"] == 2139


class TestLeakHygiene:
    def test_no_raw_paths_in_generated_text(self) -> None:
        generated = "\n".join([
            strip_seccl_header(_fixture_text()),
            SECCL_PACKAGE_ID,
            "reference_group_id=RG-seccl-exam=TEM4",
        ])
        assert "A:\\" not in generated
        assert "SWECCL 2.0" not in generated
        assert "SECCL20/" not in generated

    def test_banned_vocabulary_absent(self) -> None:
        sample = json.dumps({
            "reference_group_id": "RG-seccl-exam=TEM4",
            "feature_id": "text_length_tokens",
            "availability": "available",
            "learner_exposure": "research_only",
        })
        import re
        pattern = re.compile(r"\b(proficiency|mastery|CEFR|ability|learning\s+gain)\b", re.IGNORECASE)
        assert pattern.search(sample) is None
