# 07 — Corpus & NLP Architecture

> **AMENDMENT (Round 4 red team; decisions D-24, D-25, D-37/RT-15):** The FROZEN architecture contains only the corpus boundary contract + resource-pack descriptor (versioned, read-only, provenance-tracked). The Shared Corpus Intelligence Core (S-CIC) as a full intelligence core (reference groups, distributions/bands, comparison service, example index, availability computation) is a DEFERRED design unit, gated on (a) an authorized corpus, (b) a named consumer, (c) licensing, and (d) the D-07 min-N/coverage rules. Band/distribution/feature scope must NOT duplicate the CALF registry: CALF/measurement registries own measurement specifications, resource requirements, and band eligibility; corpus content is versioned data consumed through CALF `resource_requirement`; one band-provenance record per normative output. Ownership: corpus mechanisms + feature contract (when activated) = Corpus & NLP; admissible features, reference-group selection policy, interpretation/wording = domain departments; availability computation shared with Feedback & Learner Intelligence.


## 1. Status

The corpus layer is greenfield: no corpus module, no corpus tables, only connective-resource JSONs (`connectives_v0_4.json`, `connectives_v0_6_1.json`). The NLP foundation is strong but student-only: versioned analyzers (`spacy-analyzer-v0.8.0`, pinned `en_core_web_sm`, `nlp-config-v0.4.0`), BasicAnalyzer fallback with `fallback_used`/`fallback_reason`, per-metric versions, `MetricResult` confidence + eligibility flags, CALF constructs `VALIDATION_PENDING`/`UNAVAILABLE`, calibration gates, LLM schema validation with LocalDemo default. Everything in this document is a planned, additive layer; nothing existing changes.

## 2. Architecture

```text
Corpus (read-only, external, licensed)
  -> Shared Corpus Intelligence Core (S-CIC)
       manifests/versions | reference groups | distributions/bands |
       authentic-example index | feature contract | deterministic comparison
  -> L2 Corpus Profiles / Academic Writing Corpus Profiles (selection + interpretation only)
  -> existing student pipeline (intake, analysis, calibration, feedback, revision/practice, journey)
```

- **S-CIC owns:** manifests and versions; provenance; reference-group algebra; distributions/bands; authentic-example retrieval index (deterministic, v0.1); the shared feature contract; the comparison service; availability computation. Must NOT own: learner data, diagnosis semantics, feedback wording, pedagogy, domain taxonomies, scoring.
- **Domain profiles own:** task-taxonomy mapping (ambiguous → `unmatched`/`NR`, never guessed); reference-group selection policy; admissible features per construct; interpretation/wording contracts; example display policy. Must NOT own: statistics computation, feature extraction, retrieval internals.
- **LLM:** wording/selection inside verified slots only; never numbers, quotes, or citations not injected as slots.

## 3. Hard invariants (I1–I6)

1. **I1 — Corpus distance is never proficiency.** Banned tokens in corpus-derived field names/UI strings: `level`, `score`, `ability`, `mastery`, `gain`, `CEFR` (except explicit prohibition text); naming: `reference_band`, `percentile_rank`, `distance_metric`.
2. **I2 — Corpus is read-only reference data.** Learner text never written into the corpus; product never mutates corpus artifacts.
3. **I3 — Same feature contract for both sides.** Version mismatch ⇒ comparison unavailable, never "best-effort comparable".
4. **I4 — Explicit unavailable states.** `no reference group`, `insufficient corpus data`, `feature incompatible`, `license restricted`, `corpus not registered`; silent group widening forbidden.
5. **I5 — Deterministic math, LLM wording.** Every statistic, band, quote, citation in feedback is a verified slot produced deterministically.
6. **I6 — Observed evidence ≠ diagnostic inference ≠ feedback recommendation ≠ learning outcome.** Band movement is observed change only (`HISTORY_LIMITATION` pattern extended).

## 4. Required new abstractions (planned; YAGNI-checked)

A1 `CorpusManifest`/`CorpusVersion` (hash, source, license, hygiene); A2 `ReferenceGroup` (criteria + min-N/coverage eligibility; id `RG-{profile}-{slug}-{version}`); A3 `ReferenceDistribution` + `BandDefinition` (atomic comparison artifact); A4 `FeatureSetVersion` (feature contract resolving metric/unit/analyzer versions); A5 `ReferencePatternMatch` (status/band/percentile/distance + provenance; no score/level field by construction); A6 `AuthenticExampleRef` (provenance-bound excerpt pointer); A7 `CorpusGroundingSlot` (additive feedback block containing only verified stats/examples by id); A8 `TaskSignature` (controlled task identity; `unmatched` explicit).

## 5. Abstractions to avoid

Proficiency/score/CEFR projection (banned, I1); LLM-generated corpus statistics/quotes/citations; embeddings/vector similarity for retrieval or comparison (defer `NR`); silent reference-group widening; single global reference distribution per metric; corpus freshness auto-upgrade; writing learner text into corpora; search/infrastructure for hypothetical scale; blended opaque confidence metrics (confidence = minimum of component confidences with reasons).

## 6. Defensible comparisons and prohibited inferences (Round 2 pair 2 consensus)

- **Defensible:** same-version, same-feature-contract student↔registered-group comparisons with explicit task signature, min-N/coverage eligibility, deterministic math, all gates passing; provenance-bound band/percentile statements; existing pairwise revision/history comparisons; license-gated deterministic example retrieval (research-first).
- **Prohibited:** proficiency/mastery/CEFR/learning-gain projection; causal/transfer claims; LLM-invented quotes/stats; cross-version or fallback-analyzer comparisons; fuzzy group widening; global per-metric distributions; outcome claims without a validated-measurement gate; validating a measure against the corpus that generated its norm (circularity).
- **Reference-band classification (D-07):** bands/percentiles are observed, descriptive reference evidence; any normative interpretation requires the validated-measurement gate. Learner-facing corpus content disabled by default (D-08).

## 7. Validation dependencies

Pinned spaCy model/version capture; CALF registry statuses (`VALIDATION_PENDING`/`UNAVAILABLE` gate what may be compared/cited); `MetricResult` eligibility + metric confidence; analyzer fallback recording (comparison refused for fallback-produced features); calibration gate/priority versions; `EvidenceRelevanceValidator` extension for corpus quotes; prompt manifests + `llm_call_records` audit; learner-history comparability; configuration hashing + append-only persistence; licensing/privacy governance. Sync-conflict duplicate files (`*-冲突-Rain_Win11.py`) must be inventoried before any measurement-version claim (Round 2 pair 2, G).

## 8. Open decisions (explicit, unresolved)

D1 authorized corpora (`Researcher decision required`); D2 authentic-excerpt display (`Researcher decision required`; default no display); D3 licensing model (`Researcher decision required` per corpus); D4 band method + min-N (`Researcher decision required`); D5 task taxonomy (`Researcher decision required`); D6 proficiency-annotated corpus metadata usage (I1 applies regardless); D7 L1-matched reference groups (`NR`); D8 v0.1 feature-set scope (`NR`); D9 embedding retrieval (`NR`); D10 comparison persistence location (`Unclear`; recommendation: append-only `student_corpus_comparisons` + manifest/distribution tables); D11 frequency-resource authorization from corpus data (`Researcher decision required`); D12 UI exposure (recommendation: Research first).