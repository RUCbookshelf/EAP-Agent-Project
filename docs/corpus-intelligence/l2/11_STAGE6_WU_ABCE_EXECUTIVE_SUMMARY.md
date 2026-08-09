# 11 - Stage 6 Research-Only Preparation (WU-A/B/C/E) Executive Summary

Status: IMPLEMENTED - research-only preparation, pending independent review.
Goal: `CORPUS-STAGE6-WU-ABCE` (scoped UD-04 authorization).
Date: 2026-08-09

## What this Goal delivers

Four research-only Work Units on top of the Stage-5 Corpus Intelligence
boundary, consuming governed/versioned artifacts only:

| WU | Deliverable | Module / artifact |
| --- | --- | --- |
| WU-A | Student FeatureSnapshot harness with version/eligibility checks | `app/corpus/student.py` |
| WU-B | TaskSignature reference-group matching with explicit unmatched states | `app/corpus/tasksignature.py` |
| WU-C | Observed-descriptive comparison math (percentile/distance), no normative labels | `app/corpus/comparison.py` |
| WU-E | Expository-score-based evaluation DESIGN using the protected block | `15_STAGE6_WU_E_EVALUATION_DESIGN.md` + machine design record |

WU-D (diagnostic gating with Feedback & Learner Intelligence) is NOT in
scope: it remains gated on D-08 display policy + licensing/anonymization gate
and the D3 licensing-model determination, per the UD-04 resolution and the
Stage-6 handoff.

## Scope and authorization

- Authorization: `UD-04` `RESOLVED_FOR_SCOPED_RESEARCH_STAGE6_WU_A_B_C_E`
  (2026-08-09); binding matrix: `docs/corpus-licensing/CORPUS-LICENSING-REVIEW.md`.
- Every Stage-6 artifact is classified NON-RECONSTRUCTIVE AGGREGATE ARTIFACT
  (machine-checkable in `data/stage6_artifact_register.json`); no artifact
  contains corpus text, excerpts, or learner text.
- No WU permission is broadened; fail-closed categories stay fail-closed
  (examples/excerpts, learner-facing display, external redistribution,
  training use, raw export).
- D3 / D8 / D12 are NOT resolved by this Goal.

## Mandatory safeguards applied

1. Raw SWECCL untouched and under exclusive CORPUS access; no raw path or
   handle can enter the harness/matcher (path-shaped submission ids rejected;
   inputs are semantic values and plain text only).
2. Downstream consumers receive only governed/versioned artifacts; every
   result carries `learner_exposure="research_only"`.
3. Provenance records source package/version, processing version,
   extractor/version, reference-group/version, and artifact version on every
   result object.
4. Reconstructiveness/disclosure risk is classified per artifact and
   machine-checkable (register + tests).
5. Fail-closed behavior: corpus-header input rejected, FeatureSetVersion
   mismatch rejects comparison, unavailable features/distributions never
   imputed, unmatched reference groups explicit.
6. No textual examples/excerpts anywhere in this Goal's outputs.
7. `research_only` never silently transitions to production: no API routes,
   no database writes, no composition-root changes; app/corpus stays the only
   touched product area.

## Boundary checks

- No student-corpus comparison, diagnosis, or feedback path outside
  `app/corpus`; the existing Student flow is untouched.
- No proficiency/mastery/learning-gain vocabulary in any module, doc, or
  data artifact (verified by test in `test_comparison.py`).
- No LLM computation of corpus statistics (I5): all math is deterministic
  local code.

## Verification

See `16_STAGE6_VERIFICATION.md` for the full matrix. Baseline Stage-5 tests
remain green (36/36) and the Stage-6 suite adds WU-A/B/C/E tests.
