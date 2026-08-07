# 01 — Current State Map
**Verified 2026-08-07 by direct inspection at HEAD `225181c559c8ad87defabb08238d8f47e51c282a` (branch master, ahead 5).**

## 1. Repository baseline

| Item | Value |
| --- | --- |
| Repository | `A:\EAP Agent Project\writing-feedback-mvp` |
| Branch / HEAD | master / `225181c` (`docs(v0.9.7-d): close work unit 4 and v0.9.7-D`) |
| Release state | v0.9.7-D COMPLETE, VERIFIED, CLOSED |
| Verification | non-live core 1237 passed / 8 skipped / 0 failed; `run.bat --verify` PASS twice; locale parity 600/600; Research smoke 6/6 |
| Database | SQLite, migration 13 applied (no 14); authority = `PRAGMA user_version` + `schema_migrations`; native runner `scripts/migrate_database.py` |
| Worktree | user-owned changes present (modified `AGENTS.md`, `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`; untracked `.agent-workflow/` (runtime planning state, noncanonical), `.claude/`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`, `CLAUDE.md`, `data/demo_journey_manifest.json`, `diagnostics/`, `verification/v0.9.7-a/.../logs/`) — preserved untouched |

## 2. Verified architecture layers

```text
Streamlit UI (app/ui) --HTTP JSON /api/v1--> FastAPI (app/api, 10 routers)
  --> services (app/services, app/journey, app/practice, app/learner, app/research, app/calibration, app/calf)
  --> repository protocols (consumer-owned; 55 Protocol classes; app/repositories/protocols.py vestigial)
  --> SQLite repositories (app/infrastructure/sqlite/repositories, 9 adapters)
  --> data/writing_feedback.db (33 tables)
```

- UI: role-based nav (Student/Research); 6 Student features (Home, Writing, Feedback, Practice, Revision, Journey); HTTP-only `api_client.py` (~64 methods); `contracts/`, `ports/` (12 feature ports), `locale.py` (en/zh_CN 600/600), `pixel_art.py::DESIGN_TOKENS` (frozen D1.3).
- API: 10 routers (`admin`, `analysis`, `calf`, `journey`, `practice`, `research`, `revisions`, `students`, `submissions`, `system`); 106 classified endpoint tuples in `tests/contracts/api_surface_contract.py`; canonical error envelope with 14 `ErrorCategory` values.
- Analysis/NLP: `app/analysis/` (spacy_analyzer + BasicAnalyzer fallback, lexical/syntactic/connective features, coordinator, registry, metric_confidence, input_quality); `app/calf/` (lexical_diversity, syntactic_units, measurement, registry with `VALIDATION_PENDING`/`UNAVAILABLE` constructs).
- LLM: `app/llm/` (base, deepseek, local_demo, router); DeepSeek disabled by default, deterministic LocalDemo fallback; versioned prompt manifests (`prompt_manifest_v0_7_1.json` etc.); schema validation + `llm_call_records` audit.
- Learner/longitudinal: `app/learner/history.py` (comparability classification + `HISTORY_LIMITATION`); `app/calibration/` (gate/evidence/service); snapshot v2 (`LPS######`) + `history_evidence_registry` (append-only).
- Practice: `app/practice/` (mapping, target_creation, task_context, completion, evaluations, service, ports, schemas); provenance `PRIO-{feedback_id}-{priority_index}`; three exercise types; evaluation `rule_based`.
- Revision: `app/revision/` (alignment, comparability, schemas). Journey: `app/journey/` (read-time cycle model + projection; no writes, no migration).

## 3. Persistence (33 tables, migration 13)

students, essays, metrics, diagnoses, feedback_records, exercises, learner_history, learner_profile_snapshots, analysis_runs, metric_results, analysis_artifacts, diagnostic_calibrations, configuration_versions (+ audit), revision_groups, revision_snapshots, practice_targets, exercise_instances, exercise_attempts, practice_evaluations, feedback_engagement_traces, within_task_response_candidates, transfer_evidence_candidates, practice_state_snapshots, history_evidence_registry, export_jobs, human_reviews, pii_candidates, analysis_units, error_annotations, llm_call_records, schema_migrations, system_versions (plus bootstrap `exercises`/`learner_history` legacy families). No corpus tables, no domain/language discriminator, no Academic entities.

## 4. Verified current product contracts (frozen, must remain intact)

learner-owned submissions; analysis; evidence-based Feedback; Feedback priority; no-priority states; insufficient-evidence states; Revision linkage; Practice targets; Practice provenance; exercise attempts; formative evaluation; evaluation-unavailable states; activity completion; Journey cycles; longitudinal event evidence; learner isolation; stable navigation; side-effect-free reads; bilingual Student UI; persistent records; research-validity boundaries (no proficiency/mastery/learning-gain claims; prototype observations only).

## 5. Known debt / audit state (verified at HEAD)

- Fixed since v0.9.5-A: router monolith split; DB god-class modularized; UI→backend schema imports removed; endpoint/client contract exists; `export_jobs` has a writer.
- Remaining: 12 leftover sync-conflict files `*-冲突-Rain_Win11.py` (unimported, shadowing risk); duplicated composition blocks in `app/api/main.py` (`_run_startup` ~line 91 vs `_build_full_app` ~line 378) reading facade private attributes; stale version constants (`Settings.application_version="0.8.0"`, `database_migration_version=10` vs migration 13, FastAPI version "0.8.0"); DDL split between `repository.SCHEMA` and `migrations.py`; JSON-only relational key component (migration 13 partial unique index on `target_json`); protocol sprawl (55 classes, `get_submission_bundle` shape repeated in 5 ports); data migrations mixed into schema migrations (migration 12); two exercise families (`exercises` legacy vs `exercise_instances`/`exercise_attempts`).
- English-centric assumptions: spaCy `en_core_web_sm` default; `BasicAnalyzer` `[A-Za-z]` regex/English connectives/stopwords.

## 6. Verified limitations

- The v0.9.5-A coupling audit predates v0.9.7-D; findings re-verified at HEAD where cited above.
- This Goal performed no code changes, so no test-suite re-run was required; verification evidence is the direct repository inspection recorded in this document.
- Corpus layer is greenfield: no corpus module, no corpus tables, only connective-resource JSONs (`connectives_v0_6_1.json` etc.).
- Genre is free text with substring-based purpose inference (`app/services/learner_model.py:333-344`) — a known inference to be replaced, never relied on.