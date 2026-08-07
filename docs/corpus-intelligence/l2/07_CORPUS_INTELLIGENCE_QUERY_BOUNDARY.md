# 07 — Corpus Intelligence Query Boundary

## Interface (app/corpus/intelligence.py)

| Capability | Behavior |
| --- | --- |
| get_corpus_version() | package identity, manifest hash, license status, known limitations |
| get_resource() | registered CorpusResourceDescriptor |
| get_feature_definition(feature_id) | versioned feature contract; unknown -> error |
| get_reference_group(group_id) | group definition; unknown -> error |
| resolve_reference_group(...) | deterministic fallback with disclosure |
| get_feature_distribution(...) | distribution query by group id or prompt/timed/genre |
| get_distribution_availability(...) | availability + reason |

## Query result contract

DistributionQueryResult answers: corpus used, requested group, resolved
group, fallback disclosure, feature measured, feature/version, contributing
N, descriptive distribution, limitations, availability. Every result carries
learner_exposure="research_only"; no conclusion fields exist.

## Failure / unavailable states

- Unknown corpus package -> CorpusResourceError at registration.
- Wrong manifest hash -> CorpusResourceError (expected vs computed).
- Unknown feature -> CorpusInvalidRequestError.
- Unknown/unsupported group -> CorpusInvalidRequestError.
- Too-small group / missing distribution -> CorpusUnavailableError (or
  availability=unavailable) - never silent widening.
- Corrupt resource / missing prepared layer -> CorpusResourceError.
- License-restricted operation: learner-facing exposure is structurally
  disabled (research_only); external redistribution is out of boundary.

## Safety

- No raw corpus text is exposed through the boundary.
- No unrestricted corpus examples are exposed (licensing policy: not
  permitted at PARTIALLY_DOCUMENTED status).
- Stage 6 consumes distributions without inspecting corpus files or
  preparation CSVs.
