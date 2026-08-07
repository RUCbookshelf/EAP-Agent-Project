# 09 — Stage 5 Verification

## Focused tests (36/36 passed)

Environment: stage5 venv, Python 3.12.13, spaCy 3.8.14 + en_core_web_sm 3.8.0,
pytest 9.1.1.

| Area | Tests | Result |
| --- | --- | --- |
| Resource | valid load, determinism, tampered hash, unknown package, missing root, row-count mismatch, missing manifest file, hash recompute | 8/8 |
| Features | all features, length, empty, short, non-ASCII, malformed, POS sum, connective determinism, repeatability, batch==single, unknown feature, definitions, corrupt input | 13/13 |
| Groups | approved set, sparse exclusion, same-prompt, prompt+timed, sparse fallback, unknown group, membership consistency, duplicate-policy effect | 8/8 |
| Intelligence | version, definitions, group lookup, fallback resolution, distribution query, missing distribution, unknown feature | 7/7 |

## Query boundary smoke (real artifacts)

- version query: package + hash + license OK
- ARG17+timed x connective_density: exact group resolved, n_effective=408,
  median=39.03 per 1000 tokens, exposure research_only
- genre=argumentative x text_length_tokens: n=4,560, median 286 tokens
- ARG13 request: resolved via fallback to genre (disclosed), no silent
  widening
- unknown feature / missing distribution: explicit errors

## Reproducibility rerun result

Rerun of build_stage5.py produces a byte-identical `reference_distributions.jsonl`: SHA-256 = `900ee3524b9093f8b011147534c5174b6c6e68b8b0a1232ff64e57c2a98ce73d` on both runs (verified with Get-FileHash and Python hashlib; 854,262 bytes). Note: `distribution_version.json` contains a build timestamp and intentionally differs between runs.

## Stage 5/6 boundary check

No student-corpus comparison, no diagnosis, no feedback path exists in
app/corpus; the existing Student flow is untouched (app/ diff empty outside
app/corpus + docs + scripts).
