# 09 — Feature Feasibility

Data: `data/feature_candidate_registry.csv` (10 families).

## Priority shortlist (READY or PROMISING)

| ID | Feature | Status | Variant | Notes |
| --- | --- | --- | --- | --- |
| F-LEX-LENGTH | text length | READY | raw | deterministic; length profile documented |
| F-SYN-LENGTH | sentence length / T-unit proxies | READY | raw/tagged | punctuation-aware splitting |
| F-SYN-POS | POS distribution | READY | tagged | CLAWS4 historical tags; mapping decision needed |
| F-DISC-CONNECTIVES | connectives/cohesion devices | READY | raw | existing product connectives resources |
| F-LEX-DIVERSITY | lexical diversity | PROMISING | raw | length-normalized variants only |
| F-LEX-PHRASEOLOGY | n-grams/collocations | PROMISING | raw/lemma | same-prompt control required |
| F-SYN-SUBORD | subordination/clause patterns | PROMISING | tagged/raw | parse-error recording required |
| F-DISC-STANCE | stance/hedging/boosting | PROMISING | raw/tagged | signal lists need validation |

## Requires validation (do not implement first)

- F-LEX-FREQ (lexical frequency/sophistication): blocked by missing authorized
  frequency resource (architecture D11 open; REF-LD-SOPHISTICATION-PENDING).
- F-DISC-COHESION (lexical cohesion): no validated measurement in the
  architecture; D-L2-03 feasibility spike required; embeddings deferred (D9).

## Feasibility basis

- RAW: reliable for length, diversity (normalized), phraseology, connectives.
- TAGGED: 100% format-valid historical CLAWS4 annotation, usable for POS
  distribution and pattern-based syntax after tag-mapping validation.
- LEMMA: usable for vocabulary work; 2 artifact files flagged.
- Deterministic tooling baseline: pinned spaCy (en_core_web_sm) exists in the
  product repo; Colligator/PatCount patterns can inform feature definitions.
- Length sensitivity: median 242 tokens; features must be rate-normalized or
  length-partitioned.

## Constraints

- Same feature contract on corpus and student sides (I3); version mismatch
  means unavailable, never best-effort.
- Deterministic math only; no LLM-generated corpus statistics (I5).
- Feature naming honors the banned-token contract.
