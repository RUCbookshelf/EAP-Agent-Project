# Pre-v0.9.4 Page-by-Page Recommendations

**Date:** 2026-08-01
**Priority scale:** P0 = accessibility/correctness, P1 = usability, P2 = polish.

## Student View

### 1. Home
- **Purpose:** task summary, latest status, next action.
- **Primary problem:** progression is text-only; no visual state; "next action"
  is an info box with no action button.
- **Hierarchy:** status card (state) → current target → next action → boundary.
- **Layout:** single column; status badge row; next-action card with a button
  linking to Practice/Writing.
- **Component changes:** pixel progress steps; action button in next-action card.
- **Remove/consolidate:** duplicate "no targets" info boxes.
- **Terminology:** plain; keep.
- **Mobile:** stacked; buttons 44px.
- **States:** empty → illustration + "Submit your first essay" action.
- **Priority:** P1.

### 2. Writing
- **Purpose:** submission form.
- **Primary problems:** empty Writing prompt passes the UI then fails with a
  generic 422 (audit finding); long form with collapsed optional sections;
  Student ID repeated without convenience.
- **Hierarchy:** ID → task relationship → required task info → essay → submit.
- **Layout:** single column, 720px max; required fields marked; optional
  sections collapsed.
- **Component changes:** inline validation (prompt + essay), helper text,
  character count, loading state on submit, persist last-used ID.
- **Remove/consolidate:** move timing/tools fully into optional expanders
  (already done); consider hiding Timing entirely for students unless needed.
- **Task context:** show the selected prompt near the essay when revising.
- **Student ID visibility:** keep top; add "last used" convenience.
- **Drafting area:** larger default height; counter.
- **Submission action:** single primary button; disabled while submitting.
- **Validation:** field-level errors in Student-safe language.
- **Loading:** spinner in button + "Analyzing…" caption.
- **Priority:** P0 (validation gap), P1 (rest).

### 3. Feedback
- **Purpose:** strengths, priorities, evidence, next step.
- **Primary problem:** after submit the page is long; priorities and next-step
  clarity could be stronger; evidence quotes plain.
- **Hierarchy:** strengths → priorities (numbered) → evidence → next step.
- **Layout:** priority cards with numbers; quote styling; final CTA card.
- **Component changes:** numbered priority cards; "Next step" CTA with button.
- **Remove/consolidate:** none.
- **Terminology:** student-safe; keep prototype disclaimer.
- **Mobile:** cards stack; quotes scrollable if very long.
- **States:** no-priority empty state with explanation.
- **Priority:** P1.

### 4. Revision
- **Purpose:** original/revised comparison, differences, priorities, uptake.
- **Primary problem:** difference representation is ratio percentages only
  (inserted/deleted/modified); no side-by-side text comparison; limited to
  session state after submit.
- **Hierarchy:** draft chain → changes summary → priorities → uptake → boundary.
- **Layout:** draft chain timeline; changes as compact stat cards; side-by-side
  or inline diff view.
- **Component changes:** add side-by-side drafts or highlighted inline diff;
  keep limitation notice prominent.
- **Remove/consolidate:** none.
- **Evidence limitations:** clearly labeled "prototype observation".
- **Mobile:** diff stacks vertically.
- **Priority:** P1.

### 5. Practice
- **Purpose:** target, exercise, attempt, evaluation.
- **Primary problem:** page depends on a prior submission in session or manual
  ID; target/why shows internal codes; no attempt evaluation detail.
- **Hierarchy:** target card → source text → generate → exercise → response →
  attempt history.
- **Layout:** single column; step-like sections.
- **Component changes:** loading on Generate/Submit; evaluation result card;
  human-readable target labels.
- **Remove/consolidate:** raw `target_code`/`source_diagnosis_id` display (hide
  behind Research).
- **Terminology:** plain student language.
- **Mobile:** fine stacked.
- **States:** no-active-target empty state with action.
- **Priority:** P1.

### 6. Learning Journey
- **Purpose:** chronological observable events.
- **Primary problem:** plain timeline without connectors; requires button
  press; no visual chronology emphasis.
- **Hierarchy:** timeline → boundary notice.
- **Layout:** vertical timeline with connecting rule; date grouping.
- **Component changes:** timeline connector; empty state with action.
- **Evidence status:** statuses localized; transfer evidence clearly bounded.
- **Avoid unsupported claims:** keep "descriptive only" boundary.
- **Mobile:** fine.
- **Priority:** P2.

## Research View

### 7. Overview
- **Purpose:** system status, provider config, data quality.
- **Primary problem:** data quality shown as raw JSON; statuses not
  structured.
- **Hierarchy:** health cards → provider row → data quality summary table →
  warnings.
- **Layout:** KPI cards (analyzer, version, model) kept; data quality as table.
- **Component changes:** px-table-wrap for quality; status badges.
- **Mobile:** cards stack.
- **States:** degraded provider → warning box (exists).
- **Priority:** P1.

### 8. Evidence
- **Purpose:** submission, analysis, diagnosis audit.
- **Primary problem:** everything is `st.json` in expanders.
- **Hierarchy:** submission summary → analysis metrics table → diagnosis audit
  table.
- **Layout:** summary cards + tables with expandable raw JSON for full detail.
- **Component changes:** metric/analysis tables; keep expander JSON as
  "raw record" fallback.
- **Mobile:** tables scroll horizontally inside containers.
- **Priority:** P1.

### 9. CALF Measures
- **Purpose:** grouped metric cards by construct.
- **Primary problem:** only renders after a session submission; no direct
  query; cards dense but fine.
- **Hierarchy:** construct groups → cards.
- **Layout:** grid (desktop) / 1 column (mobile) — current behavior.
- **Component changes:** compact card variant; direct submission selector.
- **States:** no-result empty state (exists).
- **Priority:** P2.

### 10. Learning Process
- **Purpose:** complete evidence chain.
- **Primary problem:** expander-per-record with JSON; hard to scan.
- **Hierarchy:** targets → engagement traces → transfer evidence, as tables
  with expandable rows.
- **Component changes:** table rows with expander detail; status badges.
- **Mobile:** horizontal scroll inside container.
- **Priority:** P1.

### 11. Research Data
- **Purpose:** eight workflows (Export Preview, Privacy Mode, Dataset Filters,
  PII Review, Human Review, Dataset Split, Data Quality, Export History).
- **Primary problem:** 8-tab navigation on mobile requires horizontal scroll
  (controlled, verified); results render as JSON; Dataset Filters is a
  placeholder; Privacy Mode is informational.
- **Navigation:** keep tabs; consider a more compact tab bar on mobile or a
  select fallback for the 8th tab; verify reachability (done in closure).
- **Filters:** placeholder documented; no change without product decision.
- **Export preview:** render as count cards + table preview instead of JSON.
- **Privacy state:** keep informational card; add icon.
- **Human Review:** localize "Target ID" label (hardcoded English);
  form validation.
- **Dataset Split / Data Quality / Export History:** table outputs; status
  badges; duplicate-write notices.
- **Mobile:** tab bar scroll retained; buttons 44px.
- **Priority:** P0 (localization residuals), P1 (JSON → tables).

### 12. System Audit
- **Purpose:** diagnostic audit, learner model, reanalysis, admin.
- **Primary problem:** tab4 loads configurations JSON automatically; everything
  JSON.
- **Hierarchy:** tabs → section forms → result tables.
- **Component changes:** config table; learner model preview as table;
  reanalysis note kept.
- **Mobile:** tabs scroll internally (same pattern as Research Data).
- **Priority:** P1.

## Cross-cutting recommendations

- Replace raw `st.json` research output with the existing but unused
  `px-table-wrap` tables (component already exists).
- One shared field/button/notice component set with AA tokens and 44px mobile
  targets.
- Inline validation on Writing (prompt + essay) so the server 422 is never the
  first feedback.
- Loading feedback on every async button.
- Sidebar: grouped sections + icons; 44px rows.
- Localize the two remaining hardcoded Research Data strings.
