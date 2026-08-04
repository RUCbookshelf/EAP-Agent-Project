# v0.9.6-D0-R Run Verification - Frozen Priority Path Audit

**Status:** COMPLETE - primary classification D0-R-C (downstream capability
incomplete but non-blocking)
**Branch / HEAD:** master / `cd62a82` baseline; audit closure commit at end
**Date:** 2026-08-04

## Baseline

- Development database: `F78A6CEA9C1AE5A5920A2E8943C1B092F9CCF34821568C6812C51A56CD858662`,
  14,352,384 bytes, mtime 2026-08-04 15:04:53 (adopted DP0-V2 baseline) -
  byte-identical before and after every D0-R layer.
- Research exports: 776 files / 388 directories, zero delta.
- Frozen corpus: all five SHA-256 hashes revalidated against the frozen
  manifest before submission.
- Only app change since D0 preregistration (`8896828`): `app/llm/deepseek.py`
  (approved DP0 provider repair). No gate/taxonomy/schema/prompt/routing
  change.

## Live provider (approved budget)

```text
7 production submissions (5 corpus + 2 repeats)  |  budget 9
7 provider attempts                              |  budget 12
7 live provider successes | 0 corrections | 0 fallback | 0 timeouts
0 truncation | finish_reason=stop on every call | parse success | schema passed
```

Per-case classifications: D0-01, D0-02, D0-04 LIVE_PROVIDER_SUCCESS with
selected priorities (lexical_repetition D001, connective_use D001,
lexical_repetition D001); D0-03 LIVE_PROVIDER_SUCCESS_NO_PRIORITY
(preregistered sentence-structure probe); D0-05 LIVE_PROVIDER_SUCCESS_NO_PRIORITY
(legitimate strong-control outcome); repeats STABLE.

## Evidence integrity

```text
valid priorities 3 | valid no-priorities 2 | invalid 0
exact/source-faithful evidence 3/3 | fabricated 0 | semantic mismatch 0
missing fields 0 | linkage/category failures 0
```

## Downstream consumability

```text
PARTIALLY_CONSUMABLE
Feedback CONSUMABLE (real response renders fully; session-scoped browser state documented)
Revision PARTIALLY_CONSUMABLE (action + accurate no-target note; priority family not re-displayed on fresh source)
Practice PARTIALLY_CONSUMABLE (accurate missing-target state; no auto-creation - v0.9.7-B feature gap)
Home + Learning Journey CONSUMABLE (revise CTA; durable priority event)
Desktop (1280x800) and mobile (390x844) browser journeys both passed
```

## Targeted verification (full core and launcher NOT rerun)

```text
pytest -q -p no:cacheprovider tests\test_v096dp0_v2_launcher_isolation.py
  tests\test_v096dp0_provider.py tests\test_feedback_schema.py
  tests\test_feedback_validation.py tests\test_diagnostic_calibration_v061.py
  tests\test_practice_v09.py tests\test_revision_v05.py
-> 131 passed, 0 failed, 0 errors, exit 0
Preserved full-core baseline: 824 passed, 8 skipped, 0 failed, 0 errors, exit 0
```

## Classification

```text
v0.9.6-D0-R is COMPLETE.
Production priority path classification: D0-R-C.
Priority generation is valid, while downstream Revision or Practice
capability is incomplete. These findings are now v0.9.7 product-development
items.
v0.9.6 stabilization is closed.
Proceed to v0.9.7-A - Priority-Guided Learning Cycle Completion.
```

Artifacts and evidence: `verification/v0.9.6-d0-r/`; narrative in
`docs/development/V0.9.6_D0_R_PRIORITY_PATH_AUDIT.md`.
