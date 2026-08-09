"""WU8: NLP feature feasibility registry.

Classifies feature families against the physically available variants
(RAW/LEMMA/TAGGED), deterministic tooling baseline (pinned spaCy en_core_web_sm
exists in the product repo), and documented corpus characteristics.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from scripts.corpus_paths import get_repo_root, get_corpus_root

REPO_ROOT = get_repo_root()
OUT_DIR = get_readiness_out_dir()

FEATURES = [
    {
        "feature_id": "F-LEX-LENGTH",
        "family": "lexical",
        "feature": "text length (tokens/words)",
        "status": "READY",
        "required_text_variant": "raw",
        "required_tooling": "whitespace/POS-aware tokenizer (spaCy pinned)",
        "expected_robustness": "high; deterministic",
        "length_sensitivity": "core feature; corpus length distribution documented (median 242, p1 99, p95 407 tokens)",
        "genre_sensitivity": "moderate (expository vs argumentative)",
        "known_validity_issue": "token counting differs across tools (WordSmith vs spaCy); define one counter",
        "potential_feedback_relevance": "high (length/development)",
    },
    {
        "feature_id": "F-LEX-DIVERSITY",
        "family": "lexical",
        "feature": "lexical diversity (TTR/STTR, MTLD if valid)",
        "status": "PROMISING",
        "required_text_variant": "raw",
        "required_tooling": "spaCy tokenizer + length normalization",
        "expected_robustness": "medium; length-dependent",
        "length_sensitivity": "high (TTR strongly length-dependent; use STTR/type-token curves)",
        "genre_sensitivity": "moderate",
        "known_validity_issue": "TTR inflation/deflation with length; duplicate texts distort",
        "potential_feedback_relevance": "high (repetition/range)",
    },
    {
        "feature_id": "F-LEX-FREQ",
        "family": "lexical",
        "feature": "lexical frequency/sophistication (wordlist-based)",
        "status": "REQUIRES_VALIDATION",
        "required_text_variant": "lemma",
        "required_tooling": "frequency wordlists (e.g., BNC/COCA lists) + authorization",
        "expected_robustness": "medium; list coverage for learner variants",
        "length_sensitivity": "moderate",
        "genre_sensitivity": "moderate",
        "known_validity_issue": "no authorized frequency resource exists in the architecture (D11 open); REF-LD-SOPHISTICATION-PENDING",
        "potential_feedback_relevance": "medium (sophistication) - blocked by resource authorization",
    },
    {
        "feature_id": "F-LEX-PHRASEOLOGY",
        "family": "lexical",
        "feature": "phraseology (n-grams, collocations, lexical bundles)",
        "status": "PROMISING",
        "required_text_variant": "raw/lemma",
        "required_tooling": "deterministic n-gram extraction; optional POS filtering via tagged",
        "expected_robustness": "medium; needs same-prompt control",
        "length_sensitivity": "high (frequency thresholds)",
        "genre_sensitivity": "high (prompt/genre confounds)",
        "known_validity_issue": "spurious bundles in learner data; reference-group comparability required",
        "potential_feedback_relevance": "high (phrase use)",
    },
    {
        "feature_id": "F-SYN-LENGTH",
        "family": "syntax",
        "feature": "sentence length / T-unit proxies",
        "status": "READY",
        "required_text_variant": "raw/tagged",
        "required_tooling": "sentence splitter (spaCy) on raw; punctuation tags on tagged",
        "expected_robustness": "high on raw; punctuation artifacts in learner writing",
        "length_sensitivity": "n/a (is a length feature)",
        "genre_sensitivity": "moderate",
        "known_validity_issue": "learner punctuation errors affect sentence splitting",
        "potential_feedback_relevance": "high (sentence/structure)",
    },
    {
        "feature_id": "F-SYN-POS",
        "family": "syntax",
        "feature": "POS distribution (noun/verb/adjective ratios, nominalization)",
        "status": "READY",
        "required_text_variant": "tagged (CLAWS4 historical) or spaCy retagging",
        "required_tooling": "CLAWS4 tags are historical; feature contract must define tag mapping",
        "expected_robustness": "high if using existing TAGGED; validate CLAWS4 tagset coverage",
        "length_sensitivity": "low",
        "genre_sensitivity": "moderate",
        "known_validity_issue": "legacy annotation is historical, not canonical; CLAWS4 vs spaCy tagset mapping needed",
        "potential_feedback_relevance": "high (grammar/structure proxies)",
    },
    {
        "feature_id": "F-SYN-SUBORD",
        "family": "syntax",
        "feature": "subordination/clause structures (finite/nonfinite clause ratios, that-clauses, passives)",
        "status": "PROMISING",
        "required_text_variant": "tagged (patterns) + raw (spaCy parse)",
        "required_tooling": "regular-expression patterns over CLAWS4 tags (Colligator-style); spaCy dependency parse",
        "expected_robustness": "medium; learner fragments complicate parsing",
        "length_sensitivity": "moderate",
        "genre_sensitivity": "high (argumentation norms)",
        "known_validity_issue": "parse errors on learner text must be recorded (fallback_used pattern); validation on subset",
        "potential_feedback_relevance": "high (structure)",
    },
    {
        "feature_id": "F-DISC-CONNECTIVES",
        "family": "discourse",
        "feature": "connectives/cohesive devices (documented resource connectives_v0_6_1.json)",
        "status": "READY",
        "required_text_variant": "raw",
        "required_tooling": "existing connectives JSON resources in product repo",
        "expected_robustness": "high; deterministic string matching",
        "length_sensitivity": "moderate (rate by text length)",
        "genre_sensitivity": "moderate",
        "known_validity_issue": "overlaps with lexical features; define one ownership",
        "potential_feedback_relevance": "high (cohesion)",
    },
    {
        "feature_id": "F-DISC-COHESION",
        "family": "discourse",
        "feature": "lexical cohesion (repetition, synonymy chains, reference chains)",
        "status": "REQUIRES_VALIDATION",
        "required_text_variant": "lemma",
        "required_tooling": "deterministic coreference/semantic resources; NOT embeddings (D9 deferred)",
        "expected_robustness": "low-medium without validated resources",
        "length_sensitivity": "high",
        "genre_sensitivity": "high",
        "known_validity_issue": "no validated cohesion measurement in architecture; D-L2-03 feasibility spike needed",
        "potential_feedback_relevance": "high (organization/cohesion) but feasibility unclear",
    },
    {
        "feature_id": "F-DISC-STANCE",
        "family": "discourse",
        "feature": "stance/hedging/boosting/metadiscourse signals",
        "status": "PROMISING",
        "required_text_variant": "raw/tagged",
        "required_tooling": "curated signal lists (deterministic) + POS context",
        "expected_robustness": "medium; list coverage",
        "length_sensitivity": "moderate",
        "genre_sensitivity": "high (argumentative vs expository)",
        "known_validity_issue": "signal lists need validation against argument structure",
        "potential_feedback_relevance": "high (argument-related discourse)",
    },
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "feature_candidate_registry.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(FEATURES[0].keys()))
        writer.writeheader()
        writer.writerows(FEATURES)
    summary = {
        "feature_count": len(FEATURES),
        "status_counts": {},
        "priority_shortlist": [f["feature_id"] for f in FEATURES if f["status"] in ("READY", "PROMISING")],
        "requires_validation": [f["feature_id"] for f in FEATURES if f["status"] == "REQUIRES_VALIDATION"],
        "not_supported": [f["feature_id"] for f in FEATURES if f["status"] == "NOT_SUPPORTED"],
        "note": "shortlist is evidence-based candidate design; final feature set is a domain/CALF decision",
    }
    for f in FEATURES:
        summary["status_counts"][f["status"]] = summary["status_counts"].get(f["status"], 0) + 1
    with open(OUT_DIR / "feature_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
