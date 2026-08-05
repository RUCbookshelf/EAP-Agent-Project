# v0.9.7-D D1.0 Design Input Package (for design consultation)

**Status:** READY - D1.0 baseline and constraints package for the design
consultation (MCU D1.1). No production code, locale, or migration change.
**Date:** 2026-08-05

## 1. Baseline

- Branch `master`, HEAD `6a2e927` (v0.9.7-C closure). Migration 13;
  config-v0.9.0; locale parity 600/600; full non-live core baseline
  1132 passed / 8 skipped / 0 failed.
- Product: Streamlit 1.60 academic writing-feedback prototype. Student
  View pages: Home, Writing, Feedback, Revision, Practice, Learning
  Journey. Research View is out of scope for v0.9.7-D.
- Representative page for this stage: **Learning Journey** (page
  hierarchy, grouped records, chronology, status states, primary and
  secondary actions, empty/error states, bilingual copy, dense and sparse
  content, active and completed Practice states).

## 2. Existing rendered evidence (before references, no new screenshots)

- Journey grouped cycle UI (all four combos):
  `verification/v0.9.7-c/v0.9.7-c-wu4-20260805-r1/screenshots/`
  `en_1280x900_journey_grouped.png`, `en_390x844_journey_grouped.png`,
  `zh_1280x900_journey_grouped.png`, `zh_390x844_journey_grouped.png`,
  plus `{en,zh}_{1280x900,390x844}_journey_fresh_session.png`.
- Feedback priority, Practice task/saved/completed/re-entry (four combos
  each): same run directory `screenshots/`.
- Home, Writing saved, Revision saved, Journey full (v0.9.4-B era):
  `verification/v0.9.4-b/v0.9.4-b-20260801-r1/screenshots/`
  `home_en_1280x900.png`, `writing_en_1280x900_saved.png`,
  `revision_en_1280x900_saved.png`, `journey_en_1280x900_full.png`.

## 3. Current page hierarchy (code-derived, v0.9.7-C state)

Every Student page: `student_page_intro` (page header + purpose block) ->
shared Student ID input -> learner context block -> content sections
(`section_header` + `student_context_block` / cards / notices) -> action
block + primary button -> limitation notice.

- **Home**: purpose; workflow steps (1 Write, 2 Feedback, 3 Act); next
  action block + primary CTA; current-task section (active target context
  or state info box); latest-status section (context block); limitation.
- **Writing**: purpose; optional cycle-finished notice; saved-state panel
  (success + action + reference) OR task relationship radio + draft stage
  select, prompt section (text area + genre), timing expander, tools
  expander, draft section (essay text area), submit action + button.
- **Feedback**: purpose; priorities section (priority card + one practice
  button per priority) or no-priority empty state; next-step action block
  + primary button; evidence section (quotes); strengths/neutral passage;
  limitation; submission reference caption.
- **Revision**: purpose; saved state (original context + quote + success +
  priority addressed + observation + next steps) OR candidate select ->
  original context (prompt/stage, priorities, disabled original text,
  matching-target note) -> priority task card -> revised text area ->
  submit action.
- **Practice**: purpose; steps (target/exercise/response/evaluation);
  target section + source caption; priority task (why/direction +
  evidence quote); completed state OR exercise instructions + source
  quote + constraints -> saved response + evaluation + finish OR response
  text area + submit.
- **Journey**: purpose; learner context; per cycle: "Writing Cycle"
  section header + mono `cycle_id` caption + cycle-stage context row +
  (unlinked warning) + per-submission blocks (Original/Revised label +
  state row, "Revision of #n" caption, no-priority/insufficient info
  boxes, Open Revision button) + feedback stage (Feedback #n + priority
  count + category info boxes) + Practice activity (focus + state row,
  provenance caption or legacy/unresolved info, attempt caption,
  completed/attempt-saved/evaluation-unavailable boxes, Open Practice
  button) + limitations; then next-step action block + button;
  limitation. Raw timeline only as defensive fallback.

## 4. Repeated components (app/ui/components.py + pixel_art.py)

`page_header`, `section_header`, `card_group_header`,
`student_page_intro`, `student_task_steps`, `student_action_block`,
`student_context_block` (label/value grid), `status_badge` (exists,
currently unused by Journey), `limitation_notice`, `warning_box`,
`info_box`, `success_box`, `error_box`, `empty_state`, `loading_box`
(only Writing/Revision submit paths; other pages use `st.spinner`),
`technical_caption`, `evidence_quote`, `feedback_priority_card`,
`render_api_error`, `pixel_card`, `timeline_event` (fallback), local SVG
icons (`check`, `warning`, `info`, `error`, `arrow_right`, `empty`,
`clock`) via `icon()`.

## 5. Current canonical tokens (app/ui/pixel_art.py `DESIGN_TOKENS`)

- Colors: dark `#1a1c2c`; white/bg `#ffffff`; surface `#f4f4f4`; text
  `#1a1c2c`; text-secondary `#4a4a58`; muted `#6b6b7b`; border `#1a1c2c`;
  focus `#0f6dbd`; action `#e00047`; link `#0f6dbd`; pixel-red `#ff004d`
  (decorative only).
- Semantic: success `#00e436`, warning `#ffec27`, error `#e00047`, info
  `#29adff`, unavailable/insufficient/neutral `#f4f4f4`, candidate
  `#ffec27`, selected `#29adff`; `on-*` text pairs (AA measured).
- Typography: body = local/system sans stack (incl. Noto Sans SC,
  PingFang SC, Microsoft YaHei); mono = technical/brand roles; h1
  2rem/900, h2 1.625rem/700, h3 1.25rem/700; body 1rem; compact 0.875rem;
  label 0.8125rem; metric 1.125rem. **Headings use the mono stack**
  (brand accent) today.
- Spacing: 4/8/12/16/20/24/32/40/48 px; card-pad 16px; section-space
  32px; page-space 40px; student section alias 32px.
- Geometry: thick/thin/hairline borders 4/2/1px; radius 0px; hard offset
  shadows 2/4/8px; control height 40px (44px mobile); touch target 44px;
  student content width 720px; research 1200px.
- Motion: disabled (transition/animation none; reduced-motion block).
- Responsive: mobile breakpoint 640px; tablet 1024px.
- Theme: `.streamlit/config.toml` parity (light, `#e00047`, `#ffffff`,
  `#f4f4f4`, `#1a1c2c`, sans serif).

## 6. Key constraints

1. Streamlit 1.60: stable hooks are `data-testid` attributes and
   documented stable `.st*` classes only; never generated hashed classes.
2. Single canonical token source `pixel_art.py`; generated CSS
   (`PIXEL_CSS`, `PIXEL_COMPONENT_CSS`); tests forbid literal hex colors
   or second token maps in components/pages; no `!important` proliferation.
3. Remote-resource prohibition: no remote fonts/icons/images/CDNs;
   local inline SVG icons only; tests assert no `url(`, `@import`,
   `fonts.googleapis`, `unpkg`.
4. Bilingual: en/zh_CN key parity 600/600; no fixed-width assumptions;
   labels must wrap; Chinese renders in the sans body stack.
5. Desktop student width 720px; mobile 390px baseline must stay
   functional (44px touch targets); full mobile redesign is v0.9.7-E.
6. Frozen contracts (must not change): Journey cycle grouping, raw
   events, dedup keys, ordering, learner ownership, Practice target
   reuse, completion semantics, attempt authority, evaluation
   available/unavailable, navigation destinations, persistence, API
   request/response meanings, database schema, migration 13.
7. Wording semantics frozen: no mastery/pass/transfer/proficiency/CEFR/
   causal claims. Two fixed disclaimer phrases are allowed:
   "no priority passed the Diagnostic Gate" and the all-descriptive
   "stable transfer" limitation.
8. Pixel identity preserved unless explicitly reconciled in the design
   system: solid colors, square corners, hard offset shadows, no
   gradients/glass/soft shadows, no animation.
9. Tests guard the system: `test_design_tokens_v094a.py` (token
   inventory, contrast, selectors, icons, theme parity),
   `test_hybrid_components_v094a.py`, `test_v097c_wu3_journey_ui.py`
   (rendered text/buttons/zero writes), browser matrices (no exceptions,
   no overflow, no remote requests, no raw keys, >=44px touch targets).

## 7. Frozen product semantics (design must not change)

- Writing states: `submitted`, `analyzed`, `feedback_available`,
  `feedback_without_priority`, `insufficient_evidence`,
  `revision_submitted`.
- Practice states: `available`, `attempted`, `evaluation_available`,
  `evaluation_unavailable`, `completed`, `unavailable`.
- Actions: `open_revision` (per submission with a persisted feedback
  record), `open_practice` (per Practice target). Navigation carries
  stable references only; stale/cross-learner presets fail safely.
- Completion is activity completion only; evaluation unavailable never
  implies failure; provenance is valid/legacy/unresolved, never
  fabricated.

## 8. Known inconsistencies (register)

SYSTEM
- S1. All headings (incl. page titles) use the mono stack; Chinese
  headings fall back to mono CJK faces and the "pixel" look crowds the
  page title hierarchy. No typography role tokens for page/section/
  card titles exist.
- S2. Shared primitives repeat inline `style="..."` rules (page_header,
  section_header, card_group_header, technical_caption, status_badge,
  metric_card, feedback_priority_card) instead of token-driven classes;
  duplicated border/padding/margin rules.
- S3. Status presentation is inconsistent: Journey state labels render as
  plain context-grid rows while `status_badge` exists unused; notices use
  full-bleed loud semantic backgrounds (yellow/blue/green) throughout,
  creating visual noise on dense pages.
- S4. Loading presentation differs by page: `st.spinner` (Home, Journey,
  Practice) vs `loading_box` (Writing, Revision submit paths).

COMPONENT
- C1. Journey action buttons are full-width default (secondary-looking)
  buttons; primary actions elsewhere are `type="primary"`; there is no
  tertiary/text action pattern and no defined action grouping.
- C2. Section spacing mixes inline 20px margins with the 32px student
  section token; the spacing scale is not applied consistently.
- C3. `student_context_block` (label/value grid) is the de-facto card on
  most pages; `px-card` appears only in Feedback priority cards - no
  defined surface hierarchy (subtle container vs primary card vs nested
  stage item).
- C4. Multiple Journey cycles differ only by a mono `cycle-{id}` caption
  under a repeated "Writing Cycle" header; cycle distinction is weak.

PAGE
- P1. Journey cycle content is a flat stack of blocks with no visible
  card surface; stage items are not visually grouped; Practice gets a
  section header but submissions do not; original/revision distinction
  relies on a label pair only.
- P2. Feedback uses white cards with action-red category titles;
  Practice/Journey/Revision use context grids and quotes - equivalent
  record types look unrelated across pages.
- P3. Home "current task" and "latest status" both render as context
  blocks with no hierarchy difference.
- P4. Empty states are consistent (`empty_state`), but error states mix
  `render_api_error` boxes with inline `st.error` (streamlit_app);
  no shared recoverable/blocking distinction on Student pages.

D-OPTIONAL
- O1. Four retained English strings contain a literal `?` (e.g.
  "Loading learning journey?", "Reviewed ? no eligible priority");
  pre-existing, documented, semantics-preserving copy touch only.
- O2. Journey category notes use the leading-space raw-text trick
  (`info_box(" " + t(...))`); replace with a proper label primitive
  during the Journey refactor.

DEFER-E
- E1. Full mobile redesign, dark mode, animation system, illustration
  system, new branding assets, full accessibility remediation, Research
  UI changes - v0.9.7-E / later stages.

## 9. Desired product character

Calm, credible, focused academic writing-learning workspace -
contemporary, structured, legible, supportive without being childish,
polished without decorative excess. Priority order: comprehension ->
hierarchy -> consistency -> action clarity -> aesthetic refinement.
Prohibited: gradients, glassmorphism, excessive shadows, oversized hero
sections, gamification, neon colors, excessive rounding, unnecessary
animations, icon-only critical actions, page-specific styling,
landing-page patterns, dense badge walls, remote resources.

## 10. Required proposal contents (D1.1 ask)

Produce: A) visual direction; B) semantic color system (app background,
primary/secondary/elevated surfaces, text tiers, border, focus, action
tiers, info/success/warning/error states, active Practice, evaluation
unavailable, legacy/unlinked) - never color alone; C) typography
hierarchy (page title, page intro, section heading, card title, body,
metadata, helper text, status label, button text; local/system font
stacks only); D) spacing/sizing scale; E) surface hierarchy; F) action
hierarchy (primary/secondary/tertiary/destructive/disabled/pending +
placement rules); G) state system (active, completed, submitted,
feedback available, evaluation unavailable, insufficient evidence, no
priority, legacy/unlinked, loading, empty, recoverable error, blocking
error); H) core component specs (page header, section header, status
badge, action row, notice, empty state, error state, metadata row, record
reference, cycle card, stage item, Practice state panel); I) Journey
representative-page composition; J) bilingual resilience; K) measurable
acceptance checklist. Every recommendation must map to a reusable token,
component, layout rule, state pattern, or verifiable criterion. Do not
propose backend/data changes, new features, remote resources, or the
v0.9.7-E mobile redesign.
