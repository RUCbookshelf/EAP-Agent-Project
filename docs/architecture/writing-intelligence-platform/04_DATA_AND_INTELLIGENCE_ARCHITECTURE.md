# 04 — Data and Intelligence Architecture

## 1. Data ownership map

| Data family | Owner | Provenance pattern |
| --- | --- | --- |
| Submissions/essays | Shared Platform & Core (schema); domains add content fields additively | learner-owned; `revision_of_submission_id` links |
| Analysis runs/metric results/artifacts | Shared Platform & Core | append-only; `AR/AU/AL/MT` prefixed IDs; analyzer/metric/resource versions per run |
| Diagnoses + calibrations | Feedback & Learner Intelligence | `DC/DT` IDs; gate/priority versions (`diagnostic-gate-v0.6.1`, `diagnostic-priority-v0.6.1`) |
| Feedback records | Feedback & Learner Intelligence | evidence-validated; append-only; `feedback_id` |
| Revision groups/snapshots | Shared Platform & Core | append-only; `RG/RS` IDs; alignment + comparability |
| Practice targets/attempts/evaluations | Shared Platform & Core (mechanics); domain content in registries | `PRIO-{feedback_id}-{priority_index}` provenance; `PT/EA/PE/PSS` IDs |
| Learner history + profile snapshots | Shared Platform & Core (contract); domain sections | append-only; `LPS######`, `HE######`, `TC###` |
| Journey events | Shared Platform & Core | read-time projection; no writes; `journey-event-v0.9.3-c`, `journey-cycle-v0.9.7-c` |
| Configuration/audit | Shared Platform & Core | `configuration_versions` SHA-256, single-active |
| Academic entities (future) | Academic Writing Domain | four provenance chains; append-only verification outcomes |
| Corpus manifests/groups/distributions (future) | Corpus & NLP (S-CIC) | versioned, read-only, hash+license+provenance |
| Research exports/splits/PII | Research Evaluation & Data Governance | domain-scoped by default; PII scan + human review |

## 2. Epistemic-status taxonomy (Goal section 15/21; adopted D-09)

| Layer | Content | Status | Growth/proficiency display |
| --- | --- | --- | --- |
| L0 Observed evidence | metric values, parser artifacts, evidence quotes, comparability status, engineering confidence | `observed_descriptive` | No |
| L1 Diagnostic inference | gated signals, evidence relevance, confidence, gate rule version | `gated_inference` | No |
| L2 Feedback recommendation | priorities, practice targets, formative evaluations, provenance | `recommendation` | No |
| L3 Learning outcome | reserved; only validated measurement models may write | `outcome_claim` | Only after validated-measurement gate |

Invariant: a row may be downgraded for display, never upgraded. Persistence form (additive typed field vs compute-at-boundary) is `Researcher decision required`; compute-at-boundary is the interim option.

## 3. Learner evidence families (Goal section 21; never merged)

- **Submission evidence:** observed text/feature evidence of one draft (metrics, quotes, analysis artifacts, engineering confidence).
- **Revision response:** linked revised submission + revision groups/snapshots/alignment under comparability conditions (same prompt/genre/timed/tool conditions; cross-student comparison forbidden).
- **Practice response:** attempts/evaluations with `PRIO-{...}` provenance; activity completion only; evaluation-unavailable states first-class.
- **Within-task observation:** events inside one task cycle (revision response, practice attempts, feedback engagement traces).
- **Later-task observation:** independent later task meeting comparability conditions; `not_comparable` is honest; min 2 comparable independent tasks for cross-task longitudinal assessment.
- **Recurring pattern:** TraceStatus recurrence/nonrecurrence/mixed/insufficient evidence; pattern labels (`persistent`, `recurring`, `recently_reduced`); descriptive only.
No mastery score, proficiency score, or learning-gain score may exist without a separately validated measurement model.

## 4. Corpus & Intelligence pipeline (Goal section 19; planned stages)

Chain: Corpus → NLP → Student Evidence → Reference Pattern → Diagnostic Evidence → Feedback → Revision/Practice → Longitudinal Evidence.

| Stage | Owner | Deterministic vs LLM | Key contract |
| --- | --- | --- | --- |
| P1 Corpus registration & manifest | S-CIC + Research Evaluation | deterministic | `CorpusManifest` + content hash + license + hygiene flags |
| P2 Reference group definition | S-CIC + profiles | deterministic | `ReferenceGroup` criteria + min-N/coverage eligibility |
| P3 Corpus feature extraction | S-CIC | deterministic (spaCy; no LLM on corpus) | same `FeatureSetVersion` as student side |
| P4 Reference distributions & bands | S-CIC | deterministic | `ReferenceDistribution`; versioned band method; coverage stats |
| P5 Authentic example index | S-CIC | deterministic (v0.1 lexical/structure) | `AuthenticExampleRef`; license/anonymization gates |
| P6 Task/genre matching | domain profiles | deterministic | `TaskSignature`; `unmatched` is explicit, never guessed |
| P7 Student NLP extraction | shared pipeline | deterministic | existing analyzer/metric versions; fallback recorded |
| P8 Student NLP snapshot | shared pipeline | deterministic | append-only snapshot; versions + confidence + eligibility |
| P9 Student–corpus comparison | S-CIC | deterministic only | `ReferencePatternMatch`; gate failures -> `not computed` with reasons |
| P10 Corpus-grounded diagnostic evidence | shared calibration (extended) | deterministic gating | corpus evidence cited by id; gate version bumped |
| P11 Feedback | LLM wording + deterministic slots | LLM selects/phrases only | `CorpusGroundingSlot`; validator rejects invalid slots |
| P12 Revision/Practice linkage | shared pipeline | deterministic target mapping | existing provenance chains; no new tables |
| P13 Longitudinal evidence | shared history + S-CIC | deterministic assembly | observed band movement only; re-baseline on corpus version drift |

Hard invariants (I1–I6): corpus distance is never proficiency/mastery/learning-gain (naming contract; banned tokens: `level`, `score`, `ability`, `mastery`, `gain`, `CEFR` in corpus-derived fields/UI); corpus read-only; same feature contract both sides; explicit unavailable states (no silent group widening); deterministic math + LLM wording in verified slots only; observed ≠ inference ≠ recommendation ≠ outcome. Learner-facing corpus content disabled by default (D-08).

## 5. Versioning and identifiers policy

- Version identifiers follow existing `-vX.Y.Z` conventions; component versions in `system_versions`; prompt manifests content-hashed; configuration single-active.
- New relational keys go in real columns, never inside JSON blobs (migration-13 JSON-only key treated as immutable content, not query surface).
- Version single-sourcing is a Horizon 1 prerequisite (D-20); migration 14+ additive with defaults, no data backfill, one-step non-destructive rollback preserved (D-17).
- Corpus/feature/band version mismatches always yield explicit unavailable states, never "best-effort comparable" (I3/I4).

## 6. Migration policy (planning rules for future implementation Goals)

- One migration stream; additive-only; schema truth consolidated (DDL split resolved as a debt fix before migration 14).
- Any migration affecting more than one department requires Architecture & Integration review (migration owner, order, backward compatibility, rollout dependency, rollback requirements, affected departments, integration tests).
- No migration may be introduced by this Goal; migration 13 remains the authority.

## 7. Domain threading map (Round 4 resolution D-23/D-36/D-28)

Domain resolution rule: **derived through submission ancestry for all learner-evidence tables via ONE resolver service**; additive columns only where no ancestry exists. `language` = submission language (closed vocabulary), explicitly distinct from UI locale (bilingual contract untouched) and learner L1 (per-submission declared context); dropped if no consumer emerges in Horizon 1.

| Table family | Resolution | Notes |
| --- | --- | --- |
| essays/submissions | additive `domain` (+ `language`) column, `DEFAULT 'l2'`, `CHECK (domain IN ('l2','academic'))` in migration 14 | authoritative value server-derived (D-21); client assertion advisory only |
| analysis_runs, metric_results, analysis_artifacts | derived via submission ancestry | resolver service |
| diagnoses, diagnostic_calibrations | derived via analysis-run ancestry | |
| feedback_records | derived via submission ancestry | feedback_id is globally unique; PRIO provenance cross-domain safe |
| revision_groups, revision_snapshots | derived via submission ancestry | |
| practice_targets, exercise_instances, exercise_attempts, practice_evaluations, practice_state_snapshots | derived via submission ancestry | domain equality required for revision-candidate/practice linking |
| learner_history, learner_profile_snapshots, history_evidence_registry | derived via submission ancestry; comparability requires same domain | highest-priority isolation surface |
| within_task_response_candidates, transfer_evidence_candidates, feedback_engagement_traces | derived via submission ancestry | isolation contract tests |
| llm_call_records | domain-neutral audit record; domain carried on payload | never filtered silently |
| export_jobs, human_reviews, pii_candidates | domain-scoped by default at export time (D-19); unknown domain values rejected/quarantined until CHECK exists (D-36) | |
| configuration_versions, system_versions, schema_migrations | domain-neutral | |
| Academic entities (future) | additive tables under Academic namespace | four provenance chains |

Until migration 14 exists, app-layer validation + export-time validation reject/quarantine unknown domain values.