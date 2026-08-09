"""WU11 governance-validator tests (department-owned; deterministic; read-only).

Covers the policy tables, the independent-review resolutions (F1-F14), and the
POLICY-HASH-1 CRLF line-ending normalization rule (GOV-CRLF-HASH-FOLLOWUP).
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from app.research.governance import validators as v


def _repo_tmp(payload):
    """Write a payload into a repo-local temp dir (sandbox-safe) and return (path, dir)."""
    tmp_dir = Path(tempfile.mkdtemp(dir=v.REPO_ROOT, prefix=".gov-test-"))
    path = tmp_dir / "bad.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, tmp_dir


# ---------------------------------------------------------------------------
# Policy artifact schema validation (WU2/WU11)
# ---------------------------------------------------------------------------

def test_policy_artifacts_all_valid():
    results = v.validate_all_policy_artifacts()
    assert len(results) == len(v.POLICY_ARTIFACTS)
    for result in results:
        assert result["valid"], f"{result['path']}: {result['errors']}"


def test_policy_artifact_schema_rejects_bad_payload():
    artifact, tmp_dir = _repo_tmp({
        "policy_id": "bad",
        "policy_version": "bad-v0.1.0",
        "policy_family": "corpus-use",
        "status": "draft",
        "owner": "someone-else",
        "effective_date": "not-a-date",
        "ratification_decision_id": "RD-POL-003",
        "description": "too short",
        "scope": [],
        "statements": [],
        "references": [],
    })
    try:
        result = v.validate_policy_artifact(artifact)
        assert not result["valid"]
        messages = "\n".join(result["errors"])
        assert "expected type 'object'" not in messages  # sanity: payload is an object
        assert any("missing required" in message or "status" in message for message in result["errors"])
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_policy_schema_rejects_unknown_property():
    schema = v.load_policy_schema()
    errors = v._schema_errors({"policy_id": "x", "unknown": 1}, schema)
    assert any("unexpected property 'unknown'" in message for message in errors)


# ---------------------------------------------------------------------------
# Measurement-claim guardrails (WU7; F1/F2/F4/F12 resolutions)
# ---------------------------------------------------------------------------

def test_banned_vocabulary_guardrails():
    assert v.contains_prohibited_claim("the learner has advanced proficiency") == ["risky ability phrase 'advanced proficiency'"]
    assert v.contains_prohibited_claim("the learner mastered this skill") != []
    assert v.contains_prohibited_claim("the learner improved") != []  # longitudinal claim phrase
    assert v.contains_prohibited_claim("improved feature values are observable") == []  # context rule, not token rule
    assert v.contains_prohibited_claim("a score of 8") != []
    assert v.contains_prohibited_claim("feature availability is research_only") == []  # substring false positive guard
    assert v.contains_prohibited_claim("proficiency is never claimed") == []  # I1 token list excludes proficiency; phrase check covers "advanced proficiency"


def test_frozen_priority_score_term_exempt():
    # F2: the canonical 07 §2.3 template uses the frozen product term "priority score".
    assert v.contains_prohibited_claim("priority score P (workflow ranking only)") == []


def test_history_limitation_disclaimer_passes():
    # F1: the mandated disclaimer is explicit prohibition text (I1 exception).
    disclaimer = (
        "This evidence is produced by prototype heuristic metrics and diagnoses; it does not establish "
        "language-ability improvement, decline, mastery, or regression."
    )
    result = v.validate_disclaimer_text(disclaimer)
    assert result["permitted"], result["findings"]


def test_claim_template_rejects_learner_quality():
    # F4: semantic quality assertions must fail even without banned vocabulary.
    result = v.validate_claim_template("The learner is a good writer", "observed_feature")
    assert not result["permitted"]
    assert any("quality assertion" in finding for finding in result["findings"])


def test_claim_template_permitted_examples():
    assert v.validate_claim_template("word count is 342 (spacy-analyzer-v0.8.0)", "observed_feature")["permitted"]
    assert v.validate_claim_template(
        "this feature value is near the upper part of this reference distribution (group RG-prompt_id=ARG17-timed_status=timed, n_effective=408)",
        "reference_comparison")["permitted"]
    assert v.validate_claim_template(
        "priority score P (workflow ranking only); gate diagnostic-gate-v0.6.1", "diagnostic_inference")["permitted"]


def test_claim_template_learning_outcome_reserved():
    result = v.validate_claim_template("the learner reached level C1", "learning_outcome")
    assert not result["permitted"]


def test_claim_template_rejects_cross_student_comparison():
    result = v.validate_claim_template("the learner outperforms peers in this reference group", "reference_comparison")
    assert not result["permitted"]


# ---------------------------------------------------------------------------
# Reference-group eligibility (WU6)
# ---------------------------------------------------------------------------

def test_reference_group_eligibility_real_artifacts():
    result = v.validate_reference_group_eligibility()
    assert result["valid"], result["findings"]
    assert result["group_count"] == 75
    assert result["distribution_count"] == 1050
    assert result["min_complete_case_n"] >= 30


def test_fold_duplicates_matches_stage5_facts():
    affected, groups, canonical, non_canonical = v._fold_duplicates()
    assert len(affected) == 240
    assert len(groups) == 120
    assert len(canonical) == 120
    assert len(non_canonical) == 120


# ---------------------------------------------------------------------------
# Evaluation protection (WU4)
# ---------------------------------------------------------------------------

def test_evaluation_protection_real_artifacts():
    result = v.validate_evaluation_protection()
    assert result["valid"], result["findings"]
    assert result["scored_count"] == 270
    assert result["duplicate_count"] == 240
    assert result["corrupt_count"] == 1


# ---------------------------------------------------------------------------
# Version provenance (WU8)
# ---------------------------------------------------------------------------

def test_version_provenance_real_artifacts():
    result = v.validate_version_provenance()
    assert result["valid"], result["findings"]
    assert result["record_count"] == 1050


# ---------------------------------------------------------------------------
# Deterministic audit sampler (WU9)
# ---------------------------------------------------------------------------

def test_sampler_deterministic():
    records = [{"id": f"R{i:06d}"} for i in range(500)]
    first = v.select_sample(records, 5)
    second = v.select_sample(records, 5)
    assert [item["id"] for item in first] == [item["id"] for item in second]
    assert 0 < len(first) < len(records)
    rate = len(first) / len(records)
    assert 0.03 <= rate <= 0.07


def test_sampler_seed_changes_sample():
    records = [{"id": f"R{i:06d}"} for i in range(500)]
    baseline = [item["id"] for item in v.select_sample(records, 5)]
    reseeded = [item["id"] for item in v.select_sample(records, 5, seed="audit-sampler-v0.1.1")]
    assert baseline != reseeded


def test_sampler_rejects_bad_rate():
    with pytest.raises(ValueError):
        v.select_sample(["a"], 101)


def test_stratum_sampling_prioritizes_high_risk():
    systematic = [{"id": f"S{i:02d}"} for i in range(10)]
    high_risk = [{"id": "H001"}, {"id": "H002"}]
    merged = v.apply_stratum_sampling(systematic, high_risk, cap=5)
    assert [item["id"] for item in merged[:2]] == ["H001", "H002"]
    assert len(merged) == 5


# ---------------------------------------------------------------------------
# Stage-6 admissibility (WU8; F3/F6 resolutions)
# ---------------------------------------------------------------------------

def _provenance():
    return {
        "reference_group_id": "RG-prompt_id=ARG17-timed_status=timed",
        "feature_id": "connective_density",
        "feature_set_version": "corpus-features-v0.1.0",
        "reference_group_version": "reference-groups-v0.1.0",
        "distribution_version": "reference-distributions-v0.1.0",
        "corpus_package_id": "sweccl2-weccl20-v0.1.0",
        "manifest_hash": "0d8940ff84613807c11c0e492c61fb8d39fc1152a386061f9711a41487659eb9",
    }


def _admissible_record():
    return {
        "corpus_package_id": "sweccl2-weccl20-v0.1.0",
        "manifest_hash": "0d8940ff84613807c11c0e492c61fb8d39fc1152a386061f9711a41487659eb9",
        "feature_set_version": "corpus-features-v0.1.0",
        "reference_group_version": "reference-groups-v0.1.0",
        "distribution_version": "reference-distributions-v0.1.0",
        "requested_reference_group": "RG-prompt_id=ARG17-timed_status=timed",
        "resolved_reference_group": "RG-prompt_id=ARG17-timed_status=timed",
        "fallback_disclosure": None,
        "feature_id": "connective_density",
        "n_effective": 408,
        "n_raw": 509,
        "n_missing": 0,
        "availability": "available",
        "validity_flags": [],
        "feature_reproducible": True,
        "comparison_direction": "descriptive",
        "epistemic_status": "observed_descriptive",
        "learner_exposure": "research_only",
        "provenance": _provenance(),
    }


def test_admissibility_statuses():
    assert v.assess_admissibility(_admissible_record()) == ("ADMISSIBLE", [])
    record = _admissible_record()
    record["fallback_disclosure"] = "RG-genre=argumentative"
    status, reasons = v.assess_admissibility(record)
    assert status == "LIMITED" and reasons
    record = _admissible_record()
    record["feature_set_version"] = "corpus-features-v0.2.0"
    status, reasons = v.assess_admissibility(record)
    assert status == "UNAVAILABLE" and "feature_set_version" in reasons[0]
    record = _admissible_record()
    record["requested_reference_group"] = "RG-prompt_id=ARG13"
    record["resolved_reference_group"] = "RG-prompt_id=ARG13"
    record["fallback_disclosure"] = "RG-prompt_id=ARG13"
    status, _ = v.assess_admissibility(record)
    assert status == "UNAVAILABLE"
    record = _admissible_record()
    record["comparison_direction"] = "the learner has advanced proficiency"
    status, reasons = v.assess_admissibility(record)
    assert status == "INVALID"
    record = _admissible_record()
    record["n_effective"] = 20
    status, _ = v.assess_admissibility(record)
    assert status == "UNAVAILABLE"
    record = _admissible_record()
    del record["learner_exposure"]
    status, reasons = v.assess_admissibility(record)
    assert status == "INVALID" and "missing required" in reasons[0]


def test_admissibility_enforces_08_rows():
    # F3: score fields -> INVALID (EP-06).
    record = _admissible_record()
    record["Average_score"] = 75
    status, reasons = v.assess_admissibility(record)
    assert status == "INVALID" and "score fields" in reasons[0]
    # F3: partial provenance -> UNAVAILABLE.
    record = _admissible_record()
    record["provenance"] = {"distribution_version": "reference-distributions-v0.1.0"}
    status, reasons = v.assess_admissibility(record)
    assert status == "UNAVAILABLE" and "provenance" in reasons[0]
    # F3: n_raw sanity -> UNAVAILABLE.
    record = _admissible_record()
    record["n_raw"] = 0
    status, reasons = v.assess_admissibility(record)
    assert status == "UNAVAILABLE" and "n_raw" in reasons[0]
    # F3: fallback null with resolved != requested -> INVALID.
    record = _admissible_record()
    record["requested_reference_group"] = "RG-genre=argumentative"
    status, reasons = v.assess_admissibility(record)
    assert status == "INVALID" and "fallback_disclosure" in reasons[0]
    # F6: group not in approved set -> UNAVAILABLE.
    record = _admissible_record()
    record["resolved_reference_group"] = "RG-prompt_id=XXX99"
    record["fallback_disclosure"] = "RG-prompt_id=XXX99"
    status, reasons = v.assess_admissibility(record)
    assert status == "UNAVAILABLE" and "approved reference-group set" in reasons[0]
    # F6: missing distribution record -> UNAVAILABLE.
    record = _admissible_record()
    record["feature_id"] = "unknown_feature_xyz"
    status, reasons = v.assess_admissibility(record)
    assert status == "UNAVAILABLE" and "no distribution record" in reasons[0]
    # F6: n_effective mismatch with the distribution record -> UNAVAILABLE.
    record = _admissible_record()
    record["n_effective"] = 407
    status, reasons = v.assess_admissibility(record)
    assert status == "UNAVAILABLE" and "does not match the distribution record" in reasons[0]


# ---------------------------------------------------------------------------
# Duplicate-group leakage (WU10; F10 resolution)
# ---------------------------------------------------------------------------

def _real_duplicate_pair():
    affected, groups, canonical, non_canonical = v._fold_duplicates()
    pair = next(iter(groups.values()))
    return pair, canonical


def test_leakage_plan_split_duplicate_group_fails():
    pair, canonical = _real_duplicate_pair()
    members = list(pair)
    plan = {
        "version": "partition-v0.0.1",
        "policy_version": "evaluation-leakage-policy-v0.1.0",
        "grouping_keys": ["document_id", "prompt_id", "duplicate_group_id"],
        "sides": {"dev": [members[0]], "eval": [members[1]]},
        "prompt_matching_design": False,
        "claims_learner_isolation": False,
    }
    result = v.validate_duplicate_group_leakage(plan)
    assert result["status"] == "FAIL"
    assert any("duplicate group" in finding for finding in result["findings"])


def test_leakage_plan_intact_duplicate_group_passes():
    pair, canonical = _real_duplicate_pair()
    members = list(pair)
    manifest = v.load_corpus_manifest()
    prompt = manifest[members[0]]["prompt_id"]
    sibling = next(doc for doc, row in manifest.items() if row["prompt_id"] != prompt and doc not in members)
    plan = {
        "version": "partition-v0.0.1",
        "policy_version": "evaluation-leakage-policy-v0.1.0",
        "grouping_keys": ["document_id", "prompt_id", "duplicate_group_id"],
        "sides": {"dev": members, "eval": [sibling]},
        "prompt_matching_design": False,
        "claims_learner_isolation": False,
    }
    result = v.validate_duplicate_group_leakage(plan)
    assert result["status"] == "PASS", result["findings"]


def test_leakage_plan_learner_isolation_claim_fails():
    plan = {
        "version": "partition-v0.0.1",
        "policy_version": "evaluation-leakage-policy-v0.1.0",
        "grouping_keys": ["document_id"],
        "sides": {"dev": ["WARG0001"], "eval": ["WARG0002"]},
        "prompt_matching_design": False,
        "claims_learner_isolation": True,
    }
    result = v.validate_duplicate_group_leakage(plan)
    assert result["status"] == "FAIL"
    assert any("learner" in finding.lower() for finding in result["findings"])


def test_leakage_plan_warg2081_requires_tagged_declaration():
    plan = {
        "version": "partition-v0.0.1",
        "policy_version": "evaluation-leakage-policy-v0.1.0",
        "grouping_keys": ["document_id"],
        "sides": {"dev": ["WARG2081"]},
        "side_types": {"dev": "raw"},
        "prompt_matching_design": False,
        "claims_learner_isolation": False,
    }
    result = v.validate_duplicate_group_leakage(plan)
    assert result["status"] == "FAIL"
    assert any("WARG2081" in finding for finding in result["findings"])
    plan["side_types"] = {"dev": "tagged"}
    result = v.validate_duplicate_group_leakage(plan)
    assert result["status"] == "PASS", result["findings"]


def test_leakage_plan_unknown_id_fails():
    plan = {
        "version": "partition-v0.0.1",
        "policy_version": "evaluation-leakage-policy-v0.1.0",
        "grouping_keys": ["document_id"],
        "sides": {"dev": ["WARG0001"], "eval": ["WARG99999"]},
        "prompt_matching_design": False,
        "claims_learner_isolation": False,
    }
    result = v.validate_duplicate_group_leakage(plan)
    assert result["status"] == "FAIL"
    assert any("unknown document id" in finding for finding in result["findings"])


def test_leakage_plan_prompt_design_requires_reason():
    plan = {
        "version": "partition-v0.0.1",
        "policy_version": "evaluation-leakage-policy-v0.1.0",
        "grouping_keys": ["document_id", "prompt_id"],
        "sides": {"dev": ["WARG0001"], "eval": ["WARG0002"]},
        "prompt_matching_design": True,
        "claims_learner_isolation": False,
    }
    result = v.validate_duplicate_group_leakage(plan)
    assert result["status"] == "FAIL"
    assert any("prompt_matching_design_reason" in finding for finding in result["findings"])


# ---------------------------------------------------------------------------
# Policy registry (WU2; F11 resolution)
# ---------------------------------------------------------------------------

def test_policy_registry_consistency():
    result = v.validate_policy_registry()
    assert result["valid"], result["findings"]
    assert result["entry_count"] == len(v.POLICY_ARTIFACTS) + 1  # 8 artifacts + framework entry


# ---------------------------------------------------------------------------
# Policy registry hash normalization (POLICY-HASH-1; GOV-CRLF-HASH-FOLLOWUP)
# ---------------------------------------------------------------------------

def test_policy_registry_hashes_are_lf_canonical():
    # Recorded artifact hashes must equal the LF-canonical digest regardless of
    # the working-tree line endings the checkout happens to have.
    registry = v.load_policy_registry()
    checked = 0
    for entry in registry["policies"]:
        artifact = entry.get("artifact")
        if not artifact:
            continue
        path = v.POLICY_DIR / artifact
        assert path.exists(), artifact
        assert v._policy_artifact_digest(path) == entry["artifact_hash"], artifact
        checked += 1
    assert checked == len(v.POLICY_ARTIFACTS)


def test_policy_hash_normalizes_crlf_to_lf():
    # The digest must be invariant under CRLF<->LF conversion (POLICY-HASH-1).
    path = v.POLICY_DIR / "corpus_use_policy.json"
    on_disk = path.read_bytes()
    lf_form = on_disk.replace(b"\r\n", b"\n")
    crlf_form = lf_form.replace(b"\n", b"\r\n")
    assert lf_form != crlf_form  # artifact is multi-line; the conversion is meaningful
    assert v._policy_artifact_digest_bytes(on_disk) == v._policy_artifact_digest_bytes(lf_form)
    assert v._policy_artifact_digest_bytes(crlf_form) == v._policy_artifact_digest_bytes(lf_form)
    assert v._policy_artifact_digest(path) == v._policy_artifact_digest_bytes(lf_form)


def test_policy_registry_valid_under_crlf_checkout(monkeypatch, tmp_path):
    # Simulate core.autocrlf=true: identical content stored as CRLF bytes.
    policies_copy = Path(tmp_path) / "policies"
    shutil.copytree(v.POLICY_DIR, policies_copy)
    for file_path in policies_copy.iterdir():
        if file_path.is_file():
            data = file_path.read_bytes()
            if b"\r\n" not in data:
                file_path.write_bytes(data.replace(b"\n", b"\r\n"))
    monkeypatch.setattr(v, "POLICY_DIR", policies_copy)
    monkeypatch.setattr(v, "POLICY_REGISTRY_PATH", policies_copy / "policy_registry.json")
    result = v.validate_policy_registry()
    assert result["valid"], result["findings"]
    assert result["entry_count"] == len(v.POLICY_ARTIFACTS) + 1


def test_policy_registry_detects_hash_mismatch(monkeypatch, tmp_path):
    # Content changes must still be detected after line-ending normalization.
    policies_copy = Path(tmp_path) / "policies"
    shutil.copytree(v.POLICY_DIR, policies_copy)
    artifact = policies_copy / "corpus_use_policy.json"
    artifact.write_bytes(artifact.read_bytes() + b" ")
    monkeypatch.setattr(v, "POLICY_DIR", policies_copy)
    monkeypatch.setattr(v, "POLICY_REGISTRY_PATH", policies_copy / "policy_registry.json")
    result = v.validate_policy_registry()
    assert not result["valid"]
    assert any("hash mismatch for corpus_use_policy.json" in finding for finding in result["findings"])


# ---------------------------------------------------------------------------
# Aggregate runner
# ---------------------------------------------------------------------------

def test_run_all_validators():
    summary = v.run_all_validators()
    assert summary["valid"], summary
    assert set(summary["checks"]) == {"policy_artifacts", "policy_registry", "reference_group_eligibility", "evaluation_protection", "version_provenance"}
