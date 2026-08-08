# 04 — Shared Contract Convergence

**Gate:** WU6 GREEN — 2026-08-08
**Office:** Architecture & Integration (Wave-1 Integration Gate)

## 1. Context

The Academic Writing Foundation was developed in parallel with Shared Platform & Core H1 and intentionally created domain-local vocabulary mirrors (`app/academic/vocabulary.py`, marked `INTEGRATION_POINT`). After all three department merges, the authoritative shared definitions from `app/shared/vocabularies.py` are now present in the same integrated baseline. WU6 resolved the minimum integration seam between them.

## 2. Ownership rules applied (frozen architecture)

```text
Shared Platform & Core owns shared vocabulary.      (D-05, 03 §3, 02 §4)
Academic owns Academic verification semantics.      (Academic handoff §15)
Research Governance owns admissibility/measurement policy.  (charter)
```

Distinct axes that must never collapse (D-06, D-09, WU6 rules):

```text
Academic verification status  !=  shared evidence status  !=  epistemic status
```

## 3. Convergence disposition

Disposition chosen: **domain-local distinct type with documented mapping + contract test proving exact mirror** (Goal section 11 acceptable list).

| Symbol | Shared (authoritative) | Academic (local) | Seam |
| --- | --- | --- | --- |
| EvidenceStatus | `app/shared/vocabularies.py` — 8 frozen values | `app/academic/vocabulary.py` — `Literal` mirror of the same 8 values | contract test proves exact set equality |
| EpistemicStatus | `app/shared/vocabularies.py` — 4 frozen layers | `app/academic/entities.py` — `Literal` of the same 4 values; rank map in `vocabulary.py` | contract test proves exact set equality + layering order + downgrade-only semantics |
| Academic verification states | n/a (domain axis) | `EvidenceVerificationStatus`/`CitationVerificationStatus` = `verified/unverified/verification_unavailable` | adapter `academic_verification_to_shared` maps to shared evidence status; closed vocabulary (unknown raises) |
| Downgrade-only behavior | layering order in shared enum | `epistemic_downgrade_allowed` helper | contract test proves helper == rank comparison over the shared order |
| Banned labels | `BANNED_LEARNER_LABELS` | — | contract test proves disjoint from all Academic value sets |

## 4. Integration-owned code changes

| Change | Why integration owns it | Which frozen contract requires it | Why it is not feature development | Tests |
| --- | --- | --- | --- | --- |
| `tests/contracts/test_wave1_vocabulary_convergence.py` (13 tests) | The mirror seam only exists because two departments developed in parallel; only the integration baseline can compare both sides. | D-05 (shared vocabulary owned by Shared Core), D-06/D-09 (axis separation), Goal section 11 (drift must be test-covered) | Pure contract test; imports existing definitions; zero product behavior change. | 13 passed on integrated baseline |

No production code was modified for convergence: the Academic mirror remains domain-local (no shared import, preserving its foundation-time isolation), the shared vocabulary remains authoritative, and the contract test locks the equivalence — the minimum integration seam per Goal section 11.

## 5. Explicitly NOT converged (by design)

- No `academic_epistemic_to_shared` function exists or was added (cross-axis conflation guard; test-enforced).
- Academic verification states were not renamed to shared evidence statuses (domain axis).
- Shared vocabulary was not extended with Academic values (no competing global definitions).
- No string-equality shortcuts or semantic coercion were introduced.

## 6. WU2 architecture-drift review record

WU2 compared all department changes against the frozen register (D-09, D-17/D-36, D-20/D-29, D-21, D-22, D-23, D-24, D-25, D-26, D-27, D-31, D-32, D-37):

| Frozen decision | Verification result |
| --- | --- |
| D-09 epistemic layering | Shared 4-layer enum + Academic mirror with identical values; downgrade-only helper; observed != inference != recommendation != outcome enforced structurally |
| D-17/D-36 additive API fields; migration 13 | `advisory_domain`/`advisory_language` optional; additive response fields; migration 13 retained; `validate_domain_scope` provided (wiring = WU8 seam) |
| D-20/D-29 version single-sourcing | `app/version.py` single source; evidence streams independent; contract test present |
| D-21 server-derived attribution | `derive_attribution` + advisory validation (mismatch/invalid -> 422); no client relabel path |
| D-22 task_type metadata-only | `TaskTypeRegistry` mechanism; `legacy_unclassified` sentinel; no comparability predicate |
| D-23 one resolver | `SubmissionDomainResolver` + table-family map + `same_domain`; single shared service |
| D-24 Corpus boundary | boundary contract only; no Stage-6; no comparison service |
| D-25 CALF resource ownership | `select_resource_requirement` mechanism; CALF registries untouched |
| D-26 per-domain packs | `domain_packs/{domain}/{version}` layout; `l2/v0.1.0` present; academic explicitly absent |
| D-27 drift control | `tests/test_shared_core_drift.py` + module manifest; sync-conflict markers forbidden |
| D-31 domain isolation | named invariants; resolver predicates; integration contract tests added in WU7 |
| D-32 citation verification records | Academic `CitationVerificationRecord` + versioned rule manifest; local deterministic only |
| D-37 registry axes / banned labels | `availability` + `learner_exposure` axes; banned labels drift-test enforced |

L2 diagnostic evidence vs Academic EvidenceUnit: **separate by construction** — `app/academic/` contains zero `app.*` imports (AST-verified), so no L2 evidence object can enter an Academic entity, and vice versa.

**No BLOCKING drift found; no department silently redefined a frozen shared contract.**
