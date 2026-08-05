# v0.9.7-B Work Unit 2 - Priority-to-Practice Mapping and Provenance

**Stage:** v0.9.7-B Work Unit 2 (implementation)
**Status:** COMPLETE - all WU2 acceptance criteria satisfied; WU3 is the next
planned work unit; v0.9.7-B as a whole is NOT complete.
**Date:** 2026-08-05
**Governing protocol:** docs/development/V0.9.7_B_SPEC.md (frozen by WU1) and
the owner-provided WU2 work-unit document.

## 1. Starting and post-work Git state

- Branch: `master` (unchanged).
- Starting HEAD: `7fdf875` (`docs(v0.9.7-b): freeze practice workflow protocol`).
- Post-work HEAD: recorded in section 22 after the focused commits.
- Worktree before implementation (all pre-existing user-owned, preserved):
  modified `AGENTS.md`, `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`;
  untracked `.claude/`, `CLAUDE.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
  `data/demo_journey_manifest.json`; plus the gitignored v0.9.7-a run `logs/`.

## 2. WU2 objective and strict boundaries

WU2 implements the minimum safe production contract that transforms one
persisted Feedback priority into a valid, traceable Practice-target creation
payload, plus the provenance forwarding and ownership/source validation that
must precede any priority-derived target write.

Implemented: stable priority resolution, deterministic category-to-target
mapping, a validated target creation contract, durable provenance forwarding
(`source_priority_id`, `evidence_ids`), ownership/source relationship
validation, and the WU3-ready service entry point.

Not implemented (explicit WU2 non-goals, verified by tests): automatic target
creation from the Student UI, create-or-reuse idempotency, one-active-target
enforcement, the Practice attempt loop, target completion, post-Practice next
steps, new Journey events, and the full v0.9.7-B learning cycle.

## 3. Mapping contract

- Authoritative priority source: the persisted submission bundle
  (`SQLiteSubmissionRepository.get_submission_bundle`, app/infrastructure/
  sqlite/repositories/submission.py:151-181) which joins `essays`, `metrics`,
  `diagnoses`, `feedback_records` (latest), and `learner_history`. The exact
  priority item is
  `feedback_records.feedback_json.priority_feedback[priority_index]`.
- Inputs (trusted identifiers only): `student_id`, `source_submission_id`,
  `source_priority_id`. The client never supplies category, explanation,
  evidence quote, or revision guidance; those are loaded from persistence and
  conflicting client values are rejected or ignored server-side.
- Outputs: `PriorityTargetContract` (app/practice/mapping.py) containing every
  `PracticeTarget` field (student, source submission, source diagnosis,
  stable priority reference, target code/label, evidence_ids, gate status,
  diagnostic/configuration versions) plus a `priority_context` block with the
  persisted priority content and creation versions for WU4 task rendering.
- The contract is validated by Pydantic (`extra="forbid"`) and proven
  constructible as an existing `PracticeTarget` (test
  `test_contract_fits_existing_practice_target_schema`).

## 4. Stable priority reference

- Format: `PRIO-{feedback_id}-{priority_index}`.
- `feedback_id` is the persisted `feedback_records.feedback_id` (INTEGER
  PRIMARY KEY, unique per essay); `priority_index` is ZERO-BASED and directly
  identifies the list position inside the persisted `priority_feedback` array
  (documented in the module docstring and enforced by
  `build_stable_priority_reference` / `parse_stable_priority_reference`).
- Guarantees: the same persisted priority always produces the same reference;
  different indexes/records produce different references; the reference
  resolves to exactly one priority item; malformed, stale, out-of-range,
  negative, non-numeric, and legacy demo references (`PRIO-{essay_id}`) are
  rejected with a controlled `PriorityMappingError(kind="invalid_reference")`.
- A reference for another feedback record is rejected during resolution
  (bundle `feedback_id` must equal the reference's `feedback_id`).

## 5. Category-to-target-code mapping

Authoritative production map (app/practice/mapping.py, single source of
truth; `scripts/demo_journey.py` now imports it instead of defining its own):

| Category | Target code |
|---|---|
| `lexical_repetition` | `lexical_repetition_local` |
| `connective_use` | `connective_overuse` |
| `sentence_length_pattern` | `long_sentence` |

- Normalization is explicit and conservative: strip + lowercase only.
- Unknown, blank, malformed, or unsupported categories raise a controlled
  `PriorityMappingError(kind="unsupported_category")`; no target is
  fabricated and the API returns 422 with zero writes.
- Learner-facing labels: `CATEGORY_LABELS` (English defaults; locale keys
  `student_feedback_category_<category>` remain the UI localization source):
  "Reduce lexical repetition", "Review connective use" (the diagnosis flags
  too few connectives, so the label is neutral), "Vary sentence length".

## 6. Provenance model

Every priority-derived target persists (queryable columns and/or `target_json`):

- `student_id` - the learner;
- `source_submission_id` - the source essay;
- `source_priority_id` - the stable reference, encoding `feedback_id` +
  `priority_index`;
- `source_diagnosis_id` - the priority item's `diagnosis_id` (validated
  against the persisted diagnosis record);
- `evidence_ids = [str(feedback_id)]` - the persisted feedback record is the
  evidence container for the priority quote (frozen B_SPEC representation);
- `diagnostic_version` - persisted `diagnoses.diagnosis_version` when present,
  else the schema default; `configuration_version` - `config-v0.9.0`;
- `status` - `active` (no completion semantics in WU2).

`feedback_id`, `priority_index`, `prompt_version`, `schema_version`,
`evidence_quote`, `explanation`, `revision_guidance`, and `label_key` are
carried by the contract's `priority_context`. They are NOT stored on the
target because `PracticeTarget` uses `extra="forbid"` (app/practice/
schemas.py:31) and no schema change is permitted in WU2; they remain
re-resolvable from the feedback record through `source_priority_id` at any
time. This exact gap is recorded for WU4 (task rendering re-derives the
context from persistence).

## 7. Ownership and source-validation sequence

`PriorityPracticeMappingService.resolve_target_contract` (app/practice/
mapping.py) executes, before any write:

1. Parse the stable reference (reject malformed/fabricated values).
2. Load the persisted submission bundle (404 if missing).
3. Learner ownership: bundle `student_id` must equal the requested learner
   (cross-student -> 403, no details leaked).
4. Feedback association: a persisted `feedback_id` must exist and equal the
   reference's `feedback_id` (missing -> 404; mismatched -> 422).
5. Priority resolution: `priority_feedback` must be a list, the index in
   range, the item a dict with all five required fields non-blank
   (malformed -> 422; stale/out-of-range -> 422).
6. Diagnosis relationship: the item's `diagnosis_id` must exist in the
   persisted diagnosis signals and its category must match (missing
   diagnosis -> 404; unrelated diagnosis/category conflict -> 422).
7. Mapping and evidence: category maps to a supported target code; evidence
   is derived only from the persisted feedback record (client-supplied
   evidence IDs are never trusted; conflicting payload values -> 422).

On any failure: no target is written, no partial provenance is written, no
false success is returned, and existing records are unchanged (verified by
count checks in the API tests).

## 8. API forwarding changes

`POST /api/v1/practice-targets` (app/api/routers/practice.py):

- `source_priority_id` and `evidence_ids` are now forwarded through every
  layer: API request -> router -> `PracticeService.create_practice_target`
  (already schema-supported) -> `SQLitePracticeRepository.save_practice_target`
  -> persisted `target_json` -> API response -> `GET
  /api/v1/students/{id}/practice-targets` retrieval. Previously both fields
  were dropped at the HTTP boundary (audit G3).
- Priority-derived requests (payload contains `source_priority_id`) are
  resolved and validated by the mapping service before creation; conflicting
  `target_code`/`target_label`/`evidence_ids` payload values are rejected
  (422), and all authoritative content is loaded from persistence.
- Legacy requests without `source_priority_id` keep their existing behavior;
  `evidence_ids` supplied by legacy callers are now forwarded instead of
  dropped.
- No new endpoint was added (the frozen router endpoint-name contract is
  preserved); the WU3-ready entry point is the service method
  `PriorityPracticeMappingService.resolve_target_contract`.
- The handler gained `Depends(get_practice_submission_reader)`; the frozen
  H2D2 dependency-graph snapshot was refreshed for exactly this one new
  dependency (delta documented in section 18).

## 9. Persistence behavior

- Priority-derived target creation persists one `practice_targets` row with
  the full provenance (verified by direct SQL read of `target_json` and via
  the retrieval endpoint in `test_provenance_reaches_persistence_and_retrieval`).
- The response is the saved target model dump; it contains
  `source_priority_id` and `evidence_ids` and no `priority_context` (not a
  schema field).
- Validation failures perform zero writes (verified by row counts before and
  after every failing request in `test_validation_failure_produces_zero_writes`
  and the per-case API tests).

## 10. Legacy compatibility

- Legacy target creation without `source_priority_id` still works and
  persists `source_priority_id: null`, `evidence_ids: []` when none are sent
  (`test_legacy_target_creation_without_provenance_works`).
- Legacy `evidence_ids` are forwarded (`test_legacy_evidence_ids_are_forwarded`).
- The full legacy Practice flow (target -> exercise -> attempt -> evaluation)
  and the Journey projection remain intact
  (`test_practice_flow_and_journey_remain_intact`; affected regression 408
  passed; full non-live core 936 passed).
- Existing DEMO-001 rows and their non-canonical `PRIO-{essay_id}` references
  are untouched; the demo script's category map now imports the production
  map with byte-identical entries and the demo setup smoke passed on a fresh
  isolated database.

## 11. Migration and schema decision

No migration and no schema change. Evidence: the existing `PracticeTarget`
model already declares `source_priority_id` and `evidence_ids`
(app/practice/schemas.py:37-53), the `practice_targets` table persists the
full entity JSON (migration 12, app/database/migrations.py), and the
priority-derived contract fits the existing schema without new fields
(`test_contract_fits_existing_practice_target_schema`). The only storage gap
(priority context fields on the target) is documented in section 6 and does
not require WU2 storage: the reference re-resolves them from persistence.

## 12. `_next_practice_id` decision

- WU2 production writes use only the two-character prefix `PT` (target
  creation), matching the unaffected allocator path; exercises (`EX`),
  attempts (`EA`), and evaluations (`PE`) are unchanged. No WU2 code or test
  writes `FET`, `WTR`, or `PSS` prefixes.
- The known three-character-prefix collision defect
  (docs/KNOWN_LIMITATIONS.md:3-6) remains untouched and is explicitly
  preserved; the required allocator repair is recorded for WU3 (the first
  unit that may write affected prefixes) per the frozen WU2 boundary.
- No WU2 claim implies the defect is resolved.

## 13. Malformed-data handling

- Malformed `priority_feedback` (missing/not-a-list/blank fields) -> controlled
  `PriorityMappingError(kind="malformed_priority")` -> API 422, zero writes.
- Missing feedback record / diagnosis -> 404; stale index / mismatched
  feedback / unrelated diagnosis / category conflict / fabricated reference
  -> 422; cross-student -> 403.
- Unknown categories -> 422 with no misleading target.
- Legacy targets lacking provenance remain readable (no retroactive
  fabrication). Broader repository-wide malformed-row repair remains out of
  scope and is recorded for the appropriate later unit.

## 14. Modified files and purposes

- `app/practice/mapping.py` (new): production category map and labels,
  stable reference build/parse, `PriorityTargetContract`/`PriorityContext`,
  pure `build_target_contract`, and the WU3-ready
  `PriorityPracticeMappingService`.
- `app/api/routers/practice.py`: forwards `source_priority_id`/`evidence_ids`;
  resolves and validates priority-derived requests before any write; maps
  mapping errors to the canonical API error statuses (403/404/422); no new
  endpoint.
- `scripts/demo_journey.py`: imports `TARGET_CODE_MAP` from the production
  module (removed its local copy) so demo and production cannot diverge;
  demo behavior unchanged.
- `tests/test_v097b_wu2_priority_mapping.py` (new): 76 focused WU2 tests.
- `verification/v0.9.5-h2d2/dependency_graph_before.json` and
  `dependency_graph_after.json`: refreshed for the one new router dependency
  (see section 18).
- `RUN_VERIFICATION_V0.9.7_B_WU2.md` (this report) and project-state docs
  (PROJECT_STATE.md, docs/development/CURRENT_TASK_STATE.md,
  docs/development/MASTER_ROADMAP.md): WU1/WU2 status, WU3 next, v0.9.7-B
  incomplete.

No locale files changed (parity 555/555); no design tokens; no Journey code;
no migration; no UI behavior change.

## 15. Tests added or changed

New: `tests/test_v097b_wu2_priority_mapping.py` (76 tests, isolated DBs,
local provider only):

- Stable reference: determinism, index/record uniqueness, zero-based
  convention, out-of-range/negative/malformed/legacy references rejected.
- Category mapping: all three supported categories, conservative
  normalization, unknown/blank/malformed rejection, demo imports the
  production map.
- Mapping service: expected contract, authoritative values from persistence,
  evidence provenance, every supported category, schema fit, fabricated
  reference and missing bundle rejection.
- Ownership/source validation: cross-student, mismatched feedback, stale
  index, missing feedback/diagnosis, malformed list/item, unrelated
  diagnosis, category conflict.
- API forwarding and persistence: provenance reaches SQL + retrieval,
  all supported categories create mapped targets, unmapped category fails
  safely, malformed/fabricated/out-of-range/cross-student/missing-submission/
  conflicting payloads return 403/404/422, client priority content cannot
  override persistence, zero writes on failure.
- Legacy compatibility: no-provenance creation, evidence forwarding, full
  practice flow + Journey intact.
- Scope guards: no auto-creation from submission, no completion transition,
  no WU3 duplicate prevention.

No existing test was deleted, skipped, or weakened. The H2D2 snapshot files
were regenerated (evidence refresh, not a test change).

## 16. Focused, affected, full-core, and launcher results

- Focused: `tests/test_v097b_wu2_priority_mapping.py` -> 76 passed.
- Static: `python -m compileall -q app scripts tests` OK;
  `scripts/pixel_art_style_audit.py` PASS (0 violations);
  `git diff --check` clean on all WU2 files.
- Affected regression (23 files covering feedback persistence, submission
  bundles, diagnosis ownership, practice targets/API/repositories, attempts/
  evaluations, Journey projection, v0.9.7-A Feedback->Revision flow, API/
  service parity, student page baselines, router contracts):
  408 passed, exit 0.
- Full non-live core (canonical DP0-V1 environment: PYTHONUTF8=1,
  PYTHON_DOTENV_DISABLED=1, LLM_PROVIDER=local, fresh isolated
  DATABASE_PATH, DATABASE_URL removed, 26-entry SERVICE_API_DIFF_ALLOWLIST,
  `--ignore=tests/live`): 936 passed / 8 skipped / exit 0
  (C:\tmp\wu2-fullcore-r2\full_core_output.txt). The first full-core attempt
  hit one pre-existing timing flake in
  `tests/test_v095b_router_contract.py::test_business_route_gated_until_ready_
  while_health_available`: a background startup thread from a prior test's
  lifespan completes `_run_startup` mid-test and re-transitions the global
  lifecycle to READY, opening the readiness gate; the test passes in
  isolation and passed on the identical-env re-run. It is unrelated to the
  WU2 surface (no lifecycle/lifespan/main code changed) and is reported as a
  known pre-existing test-isolation flake.
- Launcher: `cmd /c "run.bat --verify"` PASS - health 200, docs 200,
  streamlit 200; isolated auto-provisioned temp DB; migrate/initialize/
  smoke steps exit 0.
- Locale parity: 555/555 symmetric, no empty values.
- Demo smoke: `scripts/demo_journey.py --setup` on a fresh initialized
  isolated DB completed the full demo journey (migration 12) using the
  production map import.

## 17. Change-impact review

- Router contract: endpoint function names and route surface unchanged
  (test_v095b_router_contract, test_v095d_api_contract, test_v095d_parity
  pass); one dependency added to `POST /api/v1/practice-targets`.
- Ports: no `app/practice/ports.py` change; the mapper depends only on the
  existing `PracticeSubmissionReadPort`.
- Service purity: `PracticeService` untouched; the new mapper is a separate
  module with its own reader port.
- Repository parity: no repository change; `_next_practice_id` SQL untouched
  (compare_repository_parity PASS inside test_v095e).
- H2D2 dependency-graph snapshot: regenerated from the runtime; routes
  identical (81), OpenAPI normalized identical, depends_calls delta is
  exactly one new entry - `get_practice_submission_reader` on
  create_practice_target (plus line-number shifts in practice.py caused by
  the inserted helper). This is the first post-H2D2 router dependency
  change; it is required by the frozen WU2 API-forwarding and
  validation-before-persistence contract and was refreshed with the
  before/after pair kept consistent.
- UI: no Student UI change; no automatic target creation from any page
  (scope-guard tests + no UI files modified).
- Journey: no code change; projection verified with priority-derived targets
  via the legacy flow test and full core.

## 18. Known limitations

- Priority context (evidence quote, explanation, revision guidance, prompt/
  schema versions) is not stored on the target; WU4 must re-resolve it from
  the feedback record via `source_priority_id` (documented gap, section 6).
- Legacy/externally created targets still accept client-supplied
  `evidence_ids` without source-context validation (unchanged pre-WU2
  behavior; priority-derived evidence is strictly derived from persistence).
- The pre-existing `_next_practice_id` 3-char-prefix defect and MAX+1 race
  remain (recorded for WU3).
- Pre-existing full-core timing flake in test_v095b readiness-gate test
  (documented in section 16).
- H2D2 dependency-graph snapshots were refreshed for the required router
  dependency change (delta in section 17).

## 19. Deferred WU3-WU6 work

- WU3: idempotent create-or-reuse (logical key
  `(student_id, source_submission_id, source_priority_id)`), lookup-before-
  create, additive partial unique index (migration 13), general target
  ownership validation, `_next_practice_id` allocator repair decision.
- WU4: focused task + attempt loop (priority context rendering, seeded
  source text, attempt pending guard, ownership validation, error recovery,
  re-entry).
- WU5: evaluation/completion semantics (COMPLETED status, finish/continue).
- WU6: Journey integration verification, full matrix, detect_changes review.

## 20. Acceptance-criteria status

All 24 WU2 acceptance criteria are satisfied:

1. One exact persisted Feedback priority resolves from trusted identifiers -
   satisfied (mapping service + tests).
2. Authoritative content loaded from persistence, not the client - satisfied.
3. Stable reference with one documented convention - satisfied
   (`PRIO-{feedback_id}-{index}`, zero-based).
4. Reference resolves to one exact priority item - satisfied.
5. Supported categories map deterministically - satisfied.
6. Unknown/malformed categories fail safely - satisfied (422, zero writes).
7. Mapping service produces a complete validated contract - satisfied.
8. `source_priority_id` forwarded and genuinely persisted - satisfied
   (SQL + retrieval verified).
9. `evidence_ids` forwarded/persisted per supported provenance - satisfied
   (`[str(feedback_id)]`).
10. Learner/submission/feedback/diagnosis/priority/evidence relationships
    validated before persistence - satisfied.
11. Cross-student/cross-source/cross-feedback/cross-diagnosis/fabricated
    relationships rejected - satisfied (403/422).
12. Validation failure: no partial write, no false success - satisfied.
13. Existing non-priority targets remain compatible - satisfied.
14. Existing attempt/evaluation/Journey behavior intact - satisfied.
15. No Student UI path auto-creates a target - satisfied (no UI change;
    scope guards).
16. No WU3 idempotency/one-active-target behavior claimed - satisfied
    (test proves duplicates are still created).
17. Migration decision evidence-based, no unnecessary schema change -
    satisfied.
18. `_next_practice_id` impact resolved for WU2 and assigned to WU3 -
    satisfied.
19. Focused/affected/full-core/launcher verification pass - satisfied
    (76; 408; 936/8/exit 0; run.bat PASS).
20. No behavior outside frozen WU2 scope changed - satisfied (impact
    review).
21. User-owned files untouched and uncommitted - satisfied (section 22).
22. `git diff --check` clean and change-impact review done - satisfied.
23. Reproducible file/line/test/command/log evidence recorded - satisfied
    (this report; full-core log; test file).
24. v0.9.7-B described as incomplete with WU3 next - satisfied.

## 21. Final Git state and preserved user-owned files

- Commits: listed in section 22 (recorded after commit).
- Final `git status --short` recorded after the commits; the preserved
  user-owned entries (`AGENTS.md`, `.claude/`, `CLAUDE.md`,
  `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`,
  `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
  `data/demo_journey_manifest.json`) remain unchanged and uncommitted.

## 22. Commit list

- `f3a2a12` `feat(v0.9.7-b): add priority-to-practice mapping and provenance`
  - app/practice/mapping.py (new), app/api/routers/practice.py,
    scripts/demo_journey.py, verification/v0.9.5-h2d2/dependency_graph_
    before/after.json (H2D2 snapshot refresh for the one new router
    dependency).
- `62fd3a2` `test(v0.9.7-b): verify mapping ownership and persistence`
  - tests/test_v097b_wu2_priority_mapping.py (new, 76 tests).
- `806b1dd` `docs(v0.9.7-b): close work unit 2`
  - RUN_VERIFICATION_V0.9.7_B_WU2.md (new), PROJECT_STATE.md,
    docs/development/CURRENT_TASK_STATE.md, docs/development/MASTER_ROADMAP.md.

Post-work HEAD: `10f3349`. Branch `master` unchanged. No push or pull
request was opened (not instructed).
