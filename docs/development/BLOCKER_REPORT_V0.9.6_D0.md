# v0.9.6-D0 Blocker Report - Production Provider Unreliable

**Status:** BLOCKED at Phase 3 (live-provider preflight)
**Date:** 2026-08-04
**Branch / HEAD:** master / `8896828`

## Stop condition hit

> The real provider fails the bounded preflight.

The audit executed the approved bounded preflight exactly as preregistered:

1. **Preflight submission** (D0-01, student `AUDIT-D0-01`, submission 1):
   DeepSeek attempt 0 returned truncated/incomplete JSON
   (`Invalid JSON: EOF while parsing a string at line 3 column 81`);
   the router correction attempt timed out at the frozen 30 s transport
   timeout. Result fell back to `local-demo` (`fallback_success`).
2. **Single permitted recovery attempt** (D0-01, student `AUDIT-D0-01P2`,
   submission 2, reserved slot): identical pattern
   (`Invalid JSON: EOF while parsing a value at line 41 column 21`, then
   `TimeoutError`). Result again fell back to `local-demo`.

The configured real provider (DeepSeek, model `deepseek-v4-pro`) therefore
completed **zero** parseable production results. Per the audit protocol:

- the live-provider path is **not available**;
- fallback results are **not** counted as live-provider success;
- no corpus execution, repeatability, downstream, or controlled-comparison
  phases may run on fallback evidence;
- production priority-path validity **cannot be assessed** under the
  approved real-provider conditions.

## What worked

The audit isolation and the non-provider production pipeline behaved as
designed in the isolated audit database:

- analysis: `spacy-analyzer-v0.8.0`, 24 metric results, no analyzer fallback;
- Diagnostic Gate: selected `lexical_repetition` (D001, priority score
  0.6649, evidence `verified`) in both preflight submissions;
- fallback feedback was schema-valid and its evidence quote was an exact
  essay substring (source-faithful, but not live-provider evidence);
- development database untouched (SHA-256/size/mtime unchanged);
- research exports untouched (776 files / 388 directories, zero delta);
- no production source changed.

## Failure evidence (provider call level)

Both submissions show the same two-part failure:

| Attempt | Failure | Classification |
|---|---|---|
| 0 (initial) | DeepSeek output failed StructuredFeedback validation: Invalid JSON (truncated response at different positions) | `response_validation_failed` |
| 1 (router correction) | DeepSeek request failed: TimeoutError at the frozen 30 s timeout | `request_failed` |

The truncation pattern (different cut points on both calls) is consistent
with the provider response exceeding the frozen output budget
(`llm_max_tokens=1800`) or being cut off mid-response; the correction call
then exceeds the frozen 30 s transport timeout. Neither the output budget
nor the timeout may be changed inside D0 (production configuration is
frozen).

## Decision

Primary classification: **D0-E - Provider path unreliable**.

Evidence-based recommended next stage:

```text
v0.9.6-DP0 - Production Provider Reliability
```

The next stage must investigate the evidence chain first (output-budget
limits, response truncation, timeout policy, and provider behavior) and
must not lower Diagnostic Gate or priority thresholds automatically.

**Do not start** v0.9.6-D1 (priority-selected learning cycle), v0.9.6-DP
(priority generation reliability), or any downstream repair stage until the
provider path is repaired under a separately approved goal.

## Artifacts

```text
verification/v0.9.6-d0/baseline_state.json
verification/v0.9.6-d0/production_path.json
verification/v0.9.6-d0/taxonomy_finding.json
verification/v0.9.6-d0/audit_protocol.json
verification/v0.9.6-d0/audit_corpus_manifest.json
verification/v0.9.6-d0/audit_corpus_essays.json
verification/v0.9.6-d0/audit_driver.py
verification/v0.9.6-d0/driver_state.json
verification/v0.9.6-d0/preflight_result.json
verification/v0.9.6-d0/provider_call_summary.json
verification/v0.9.6-d0/database_safety.json
verification/v0.9.6-d0/research_exports_baseline.json
verification/v0.9.6-d0/research_exports_deltas.json
verification/v0.9.6-d0/research_exports_final.json
verification/v0.9.6-d0/corpus_results.json
verification/v0.9.6-d0/repeatability_results.json
verification/v0.9.6-d0/downstream_consumability.json
verification/v0.9.6-d0/final_decision.json
```
