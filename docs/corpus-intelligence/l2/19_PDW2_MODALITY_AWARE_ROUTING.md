# 19 — Wave-2 Goal E: Modality-Aware Corpus Product Routing

**Goal:** `PDW2-E-CORPUS-ROUTING` — modality-aware corpus routing (written
default; SECCL spoken + secondary/research_only).
**Owner:** CORPUS (Corpus & NLP)
**Worktree:** `A:\EAP Agent Project\worktrees\corpus` (branch `dept/corpus`)
**Baseline:** `59500127ca2cf798ae730cee2a5a3e16707c320c` (promoted master)
**Date:** 2026-08-10

---

## 1. Purpose and boundary

This Goal implements the modality-aware **product-routing semantics** that
L2 Writing requests use to select a corpus resource and a written reference
group. It is the upstream contract for Wave-2 Outcome A
(`PDW2-C-L2-REVISION-SCAFFOLD` depends on this Goal).

Scope boundaries (binding):

- Additive code only under `app/corpus/` (new `routing.py` + additive
  package exports) and additive tests under `tests/corpus/`.
- No raw SWECCL access changes; raw source remains CORPUS-owned and
  read-only. No corpus path or handle crosses the routing boundary (ADR-06).
- No learner-facing exposure changes; every routing result carries
  `learner_exposure="research_only"`.
- No D3/D8/D12 widening: `diagnostic_only`/`displayable` requests are
  refused by the router.
- SECCL artifacts are preserved unchanged; no SECCL artifact is deleted,
  invalidated, or reclassified away from `research_only`.
- No promotion/push/PR; candidate commit only.

## 2. Resource classification (governed)

Every corpus resource has an explicit, versioned classification record
(machine mirror: `data/corpus_resource_classification.json`).

| Package | Modality | Role | Exposure class | Domains | Secondary |
| --- | --- | --- | --- | --- | --- |
| `sweccl2-weccl20-v0.1.0` | written | primary | research_only | `l2_writing` | no |
| `sweccl2-seccl20-v0.1.0` | spoken | secondary | research_only | `l2_speaking` | yes |

The SECCL20 classification is explicit: **spoken + secondary/research_only**.
All existing SECCL artifacts (package descriptor, reference groups,
distributions, membership, feature-set and distribution version records)
are preserved with their `research_only` exposure; the classification only
records that SECCL is not a primary written reference for L2 Writing.

## 3. Eligibility model (five factors)

A resource is eligible for a routing request only when **all** factors pass
(`assess_eligibility`):

| Factor | Meaning |
| --- | --- |
| Domain relevance | Requested domain is in the classification's domains |
| Modality relevance | Classification modality matches the requested modality |
| Exposure policy | Requested exposure is in the classification's allowed set (`research_only` only; no D3/D8/D12 widening) |
| Artifact availability | A governed distribution artifact exists for the candidate (group, feature) |
| Reference-group eligibility | Candidate group exists in the governed index, availability is `available`/`limited`, and `n_effective >= min_n` |

A processed resource does **not** become eligible merely because it exists:
all five factors are evaluated independently, and every failed factor is
recorded with a machine-readable reason. SECCL's processed artifacts and
governed distributions do not make SECCL eligible for default L2 Writing
routing, because domain relevance and modality relevance both fail for
written requests.

## 4. Default routing and SECCL exclusion

- L2 Writing requests (`domain="l2_writing"`, `requested_modality="written"`)
  route to the primary written resource **WECCL20 by default**.
- SECCL20 is **excluded by default** from L2 Writing diagnostic/reference
  routing. It is not a candidate for written requests under any flag, and it
  can never satisfy an `l2_writing` request (domain relevance fails).
- SECCL may only be selected through an explicit spoken-modality opt-in:
  `requested_modality="spoken"` + `allow_secondary=True` +
  `requested_exposure="research_only"` + a spoken-language domain
  (`l2_speaking`). The result is always flagged `secondary=True` with
  `learner_exposure="research_only"`.

## 5. WECCL written fallback chain

Where metadata permit, the router prefers more relevant written groups in
this exact order (full chain disclosed on every result):

1. `same_prompt` — `RG-prompt_id=<prompt>`
2. `task_type_context` — `RG-genre=<genre>-timed_status=<timed>`
3. `task_type` — `RG-genre=<genre>`
4. `similar_written_context` — `RG-timed_status=<timed>`
5. `broader_distribution` — `RG-all` (package-level all-written candidate)

Disclosure rules (fail closed):

- Every level tried and every failed level with its reason is disclosed in
  `fallback_chain` / `unmatched_reason`; silent broadening is impossible.
- `fallback_disclosure` records the most-preferred level whenever a later
  level resolves.
- The `task_type_context` groups are not present in the governed
  reference-group index today; that level is disclosed as unavailable rather
  than silently skipped.
- `RG-all` is a routing-level descriptor (membership computed from the
  authoritative index manifest and duplicate policy); it still requires a
  governed distribution artifact. No governed all-corpus distribution exists
  in Wave 2, so the broadest level is disclosed as unavailable — never
  fabricated.
- Reference distributions remain **descriptive context only**. The router
  never emits proficiency, mastery, CEFR, ability, or learning-gain claims,
  and `descriptive_only=True` on every result.

## 6. Module contract

`app/corpus/routing.py`:

- `classify_resource(package_id) -> ResourceClassification`
- `assess_eligibility(classification, *, domain, requested_modality,
  requested_exposure, reference_group_availability, n_effective, min_n,
  artifact_available) -> ResourceEligibility`
- `L2WritingRouter.route(signature, *, feature_id, domain,
  requested_modality, requested_exposure, allow_secondary) -> RoutingResult`

Versions:

| Field | Value |
| --- | --- |
| artifact_version | `l2-writing-routing-result-v0.1.0` |
| processing_version | `l2-writing-router-v0.1.0` |
| reference_group_version | `reference-groups-v0.1.0` (WECCL) |
| seccl_reference_group_version | `seccl-reference-groups-v0.1.0` (spoken opt-in) |
| learner_exposure | `research_only` (always) |
| artifact_class | `NON-RECONSTRUCTIVE AGGREGATE ARTIFACT` |

## 7. Tests

`tests/corpus/test_routing.py` (26 tests, TDD: written first, observed
failing on the missing module, then implemented):

- written-default routing (resource selection, same-prompt resolution);
- SECCL excluded by default (never a written candidate even with SECCL
  artifacts present; eligibility factors fail);
- explicit spoken/secondary/research_only classification (both packages,
  unknown package rejection);
- spoken opt-in gating (`allow_secondary`, research_only only);
- WECCL fallback chain (all five levels + chain exhaustion + incomplete
  signature);
- eligibility gating (artifact availability, min-N, exposure policy, group
  absence disclosure);
- descriptive-only semantics, provenance/exposure fields, banned-vocabulary
  absence, raw-path leak hygiene.

Full corpus suite: 133 passed (107 baseline + 26 new).

## 8. Verification

| Check | Result | Evidence |
| --- | --- | --- |
| Git preflight (root/branch/HEAD) | PASS | `worktrees/corpus`, `dept/corpus`, HEAD `59500127...` = assigned baseline |
| Pre-existing untracked evidence preserved | PASS | 4 pre-existing files under `docs/integration/` untouched |
| TDD red phase | PASS | `ModuleNotFoundError: app.corpus.routing` before implementation |
| TDD green phase | PASS | 26/26 routing tests |
| Existing corpus suites stay green | PASS | `pytest tests/corpus` 133 passed |
| Write boundary | PASS | only `app/corpus/`, `tests/corpus/`, `docs/corpus-intelligence/l2/`, `docs/integration/` in the authorized worktree |
| Resource hygiene | PASS | no junk artifacts; `.pytest_cache` scratch only |
| Raw SWECCL untouched | PASS | no writes to the raw source; no raw paths in routing results (leak-hygiene test) |
