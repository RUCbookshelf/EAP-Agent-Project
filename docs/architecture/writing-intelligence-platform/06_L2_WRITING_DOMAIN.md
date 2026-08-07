# 06 — L2 Writing Domain

## 1. Positioning

Domain B — L2 Writing Development Agent: second-language learners completing argumentative and related non-research writing tasks. The current verified system (v0.9.7-D) is this domain's starting point and its default path. Domain A complexity must not leak into the L2 workflow.

## 2. What the current system already covers (verified)

The full local-feature evidence loop: submission → analysis → calibration gate → evidence-verified Feedback (positive finding, 1–2 priorities, exercises, longitudinal comment, uncertainty note) → Revision (groups/snapshots/alignment, within-task trajectory) → Practice (targets with `PRIO-{feedback_id}-{priority_index}` provenance, attempts, formative evaluation) → Journey (read-time cycles with honest states). Covered contracts: no-priority states, insufficient-evidence states, evaluation-unavailable states, activity completion, learner isolation, stable navigation, side-effect-free reads, bilingual Student UI, persistent records, research-validity boundaries.

## 3. Genuine gaps (evidence-based)

1. Typed task identity: genre is free text; comparability uses exact genre equality; `purpose` is derived by substring inference (`app/services/learner_model.py:333-344`) — an inference that must not survive.
2. Genre/task-type expectations (moves, paragraphing) — none exist.
3. Discourse/organization evidence — absent; feasibility of deterministic organization evidence `Unclear` (spike needed).
4. Accuracy dimension — explicitly unavailable (CALF returns accuracy as unavailable without validated error annotations).
5. Corpus profiles — none; `REF-LD-SOPHISTICATION-PENDING` with explicit "no authorized frequency resource" reason.
6. Content/task-fulfillment measurement — absent, and stays absent for L2 v1.

## 4. L2 v1 architecture (content + typed metadata layer; no new services)

- **Typed task identity:** additive, optional, enumerated `task_type` (`opinion`, `argumentative`, `discussion`, `problem_solution`, `general_eap` catch-all — exact enumeration `Researcher decision required`); `genre` stays free text for backward compatibility; task type becomes the comparability/clustering key under a new rule version (append-only; old snapshots untouched).
- **L2 Domain Pack:** versioned configuration + resources (task-type definitions, per-type expectations, supported diagnosis categories and practice target codes, locale keys, evidence requirements) through the existing configuration-version machinery (immutable versions, validation, activation, rollback, SHA-256).
- **Feedback-dimension envelope (v1):** available — lexical repetition/range, cohesion/connectives, sentence/structure; candidate — discourse-organization (only if a feasibility spike confirms deterministic evidence); unavailable — local accuracy/grammar, task fulfillment/content quality, sophistication (rendered as evaluation-unavailable states).
- **Practice:** keep the three deterministic exercise types (`guided_sentence_rewrite`, `constrained_micro_revision`, `target_feature_identification`); extend target codes only where an evidence-backed diagnosis category exists.
- **Longitudinal:** conservative rule — same `task_type` + same normalized prompt = comparable; same type with different prompts stays `not_comparable`; later-task recurrence continues through existing TraceStatus semantics.

## 5. Domain boundary rules

- No source use, citation, register, rhetorical-sophistication, or research-writing content enters the L2 workflow.
- No project container, no whole-paper surface, no sources workspace (YAGNI for L2).
- No new Journey event types; no separate L2 database/profile/Journey.
- Learner-owned prompts remain inviolable; no task bank / curated assignment workflow.

## 6. Legacy-genre reconciliation (never inferred)

Historical rows hold arbitrary genre strings; mapping legacy genres to `task_type` stays explicit (`NR`/`Unclear` where ambiguous; `expository`/`narrative` → `Unclear`, never guessed). This is a data-governance decision for Research Evaluation + L2 Domain.

## 7. Open decisions (explicit, unresolved)

- D-L2-01 task-type enumeration and labels; D-L2-02 `task_type` persisted vs derived (`NR`; recommendation: additive typed field); D-L2-03 dimension-envelope membership incl. discourse_organization (`Researcher decision required`; feasibility `Unclear`); D-L2-04 corpus-profile contents/authorization (`NR`); D-L2-05 new practice target codes/exercise types (`Researcher decision required`); D-L2-06 organization-feature resource reuse (`Unclear`); D-L2-07 Academic sharing of TaskTypeRegistry (`Unclear`; resolved to namespace-scoping in D-04); D-L2-08 Domain Pack shipping form (`NR`; recommendation: configuration version + resources); D-L2-09 zh_CN naming/ordering (parity contract applies); D-L2-10 typed task-type picker in the UI (`Unclear`; deferred beyond this Goal).