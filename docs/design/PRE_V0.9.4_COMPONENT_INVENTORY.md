# Pre-v0.9.4 Component Inventory

**Date:** 2026-08-01
**Source:** `app/ui/components.py`, `app/ui/pixel_art.py`, page implementations,
and the live audit (`verification/design/pre-v0.9.4/current-ui/audit_results.json`).

Legend: Impl = current implementation; Vis = visual problems; UX = usability
problems; Dup = duplication; Usage = where used; Resp = responsive problems;
A11y = accessibility problems; Treat = proposed design-system treatment.

## 1. Application shell
- **Impl:** Streamlit `stApp` with injected pixel CSS; wide layout; white
  background; sidebar + main column.
- **Vis:** monospace everything; no app-level brand mark beyond title text.
- **UX:** content max-width unconstrained (wide layout); long paragraphs go
  edge-to-edge on desktop.
- **Dup:** n/a.
- **Usage:** all pages.
- **Resp:** no overflow at 1280x900 or 390x844 (measured).
- **A11y:** sequential headings; fine.
- **Treat:** define content max-width (Student ~720px, Research ~1200px grid);
  add a pixel brand header.

## 2. Sidebar navigation
- **Impl:** language radio, role radio, page radio; hamburger on mobile.
- **Vis:** three stacked radio groups, text-only, 42px rows.
- **UX:** 10–11 rows on mobile; page list changes by role; no icons or grouping.
- **Dup:** radios restyled identically for three different purposes.
- **Usage:** global.
- **Resp:** hamburger overlay works; sidebar 300px.
- **A11y:** radios are keyboard accessible; 42px touch height below 44px.
- **Treat:** grouped sections (Language / View / Pages) with icons and section
  labels; 44px rows.

## 3. Page header
- **Impl:** `page_header()` — h2, 4px bottom border.
- **Vis:** consistent; good anchor.
- **UX:** subtitle caption small.
- **Dup:** none.
- **Usage:** all 12 pages.
- **Resp:** fine.
- **A11y:** h2 hierarchy correct.
- **Treat:** keep; optionally add page icon + breadcrumb on Research.

## 4. Role switcher
- **Impl:** sidebar radio (Student View / Research View).
- **Vis:** same as other radios.
- **UX:** clear; switching re-renders immediately.
- **Dup:** none.
- **Usage:** global.
- **Resp:** inside hamburger on mobile.
- **A11y:** fine.
- **Treat:** restyle as two-mode segmented control with icons.

## 5. Language switcher
- **Impl:** sidebar radio (English / 简体中文).
- **Vis:** same as other radios.
- **UX:** immediate rerender; no API calls (verified in v0.9.2.1).
- **Dup:** none.
- **Usage:** global.
- **Resp:** fine.
- **A11y:** fine.
- **Treat:** keep position; add flags/globe icon.

## 6. Student ID control
- **Impl:** `st.text_input` with placeholder "Use a pseudonymous ID".
- **Vis:** square 4px border; placeholder only, no helper text.
- **UX:** repeated on 5 pages; validation only on submit; no persisted "last
  used ID" convenience.
- **Dup:** 5 copies with different widget keys (home/writing/practice/journey/
  learning).
- **Resp:** 40px tall (below 44px).
- **A11y:** labelled; placeholder contrast depends on browser default.
- **Treat:** shared component with helper text + per-role default; 44px.

## 7. Primary button
- **Impl:** `st.button(type="primary")`; red solid, white bold text, 4px border,
  4px hard shadow; Streamlit internal 1px border remains.
- **Vis:** white-on-red 3.92:1 fails AA; 1px inner border.
- **UX:** no loading state; not disabled during async work.
- **Dup:** none.
- **Usage:** Writing submit, Practice submit, Research Data run.
- **Resp:** 40px tall.
- **A11y:** contrast fail; focus ring ok.
- **Treat:** darken red for AA; spinner-in-button loading; 44px.

## 8. Secondary button
- **Impl:** default `st.button`; surface background, dark text.
- **Vis:** consistent.
- **UX:** no loading state.
- **Dup:** none.
- **Usage:** Load Records, Load Practice Targets, Load Journey, Export buttons.
- **Resp:** 40px.
- **A11y:** contrast ok; height.
- **Treat:** add loading state; 44px; keep surface treatment.

## 9. Destructive / warning action
- **Impl:** no true destructive UI exists in the app (no deletes); dark button
  style defined (px-btn-destructive) but unused; warning notices used instead.
- **Vis:** n/a.
- **UX:** n/a.
- **Dup:** none.
- **Usage:** none.
- **Resp:** n/a.
- **A11y:** n/a.
- **Treat:** define a confirmation pattern (expand-to-confirm or dialog
  equivalent) before any future destructive action.

## 10. Text input
- **Impl:** `st.text_input`; 4px border, white bg, blue focus outline.
- **Vis:** ok.
- **UX:** no inline validation; no helper text.
- **Dup:** n/a.
- **Usage:** Student ID, tool use, learner model, Human Review target.
- **Resp:** 40px.
- **A11y:** focus ring verified; height.
- **Treat:** shared field component with label + helper + inline error; 44px.

## 11. Text area
- **Impl:** `st.text_area`; 4px border.
- **Vis:** large open area; ok.
- **UX:** Writing prompt vs Essay text fields have different heights (80 vs
  300) with no character count or validation hint; empty prompt passes UI.
- **Dup:** two text areas on Writing page.
- **Resp:** fine.
- **A11y:** labelled.
- **Treat:** inline validation (required prompt + essay), character count,
  helper text.

## 12. Select control
- **Impl:** `st.selectbox`; 4px border.
- **Vis:** ok.
- **UX:** options mostly raw codes in Research (strategy, timing source).
- **Dup:** n/a.
- **Usage:** genre, draft stage, target type, decision, strategy.
- **Resp:** 40px.
- **A11y:** ok.
- **Treat:** label localization and human-readable option labels in Research.

## 13. Loading state
- **Impl:** `st.spinner` on essay submit only; no other loading feedback.
- **Vis:** spinner is default Streamlit (not pixel-styled).
- **UX:** load actions feel unresponsive.
- **Dup:** none.
- **Usage:** submit only.
- **Resp:** ok.
- **A11y:** spinner has no text for screen readers beyond default.
- **Treat:** pixel-styled in-button spinner + disabled state for all async
  actions; text announcement ("Loading…" localized).

## 14. Error notice
- **Impl:** `render_api_error` → `px-notice-error` (red bg, white text) or
  `st.error`; role-split details (research shows category/request id/status).
- **Vis:** white-on-red 3.92:1 fails AA.
- **UX:** student message generic; no field-level recovery path (e.g., Writing
  422).
- **Dup:** 21 call sites.
- **Usage:** all pages.
- **Resp:** ok.
- **A11y:** contrast fail; localized.
- **Treat:** AA red, icon, inline field errors where validation fails.

## 15. Warning notice
- **Impl:** `px-notice-warning` (yellow, dark text).
- **Vis:** ok.
- **UX:** used for boundaries and pending states; consistent.
- **Dup:** 8 call sites.
- **Usage:** boundaries, no-candidates, major rewrite.
- **Resp:** ok.
- **A11y:** contrast pass.
- **Treat:** add icon; keep.

## 16. Limitation notice
- **Impl:** `px-notice-limitation` (surface bg, dark text).
- **Vis:** plain; easy to skim past.
- **UX:** appears on most pages (9 sites) — important boundary messaging that
  may be visually underweighted.
- **Dup:** 9 sites.
- **Usage:** boundaries across Student/Research.
- **Resp:** ok.
- **A11y:** contrast pass.
- **Treat:** stronger "research boundary" icon + label so it is not confused
  with informational content.

## 17. Success notice
- **Impl:** `px-notice-success` (green, dark text); 4 sites.
- **Vis:** ok.
- **UX:** appears after submission/attempt save.
- **Resp:** ok.
- **A11y:** contrast pass; text included.
- **Treat:** keep; add icon.

## 18. Empty state
- **Impl:** `empty_state()` px-empty box; 10 sites; several pages use
  `info_box` for empty prompts.
- **Vis:** bordered box, centered text.
- **UX:** message + explanation but no action button (ui-ux-pro-max: empty
  states should offer an action).
- **Dup:** empty_state vs info_box used interchangeably for empty prompts.
- **Usage:** feedback no-priority, journey empty, audit empty.
- **Resp:** ok.
- **A11y:** ok.
- **Treat:** unify into one empty-state component with an optional action.

## 19. Feedback priority card
- **Impl:** `feedback_priority_card()` — red category title, quote, explanation,
  revision guidance, practice link.
- **Vis:** strong; quote box styled.
- **UX:** good actionability; next-step box below.
- **Dup:** 2 sites (feedback + after submit).
- **Resp:** ok.
- **A11y:** ok.
- **Treat:** keep; add "Next step" call-to-action card and priority numbering.

## 20. Evidence quotation
- **Impl:** `evidence_quote()` / inline `px-quote`; italic, surface bg.
- **Vis:** ok.
- **UX:** no source/evidence-id context in Student (intentional).
- **Dup:** 4 sites.
- **Resp:** long quotes wrap; ok.
- **A11y:** italic serif/mono readability.
- **Treat:** keep; add clear quotation marks; allow horizontal scroll for very
  long quotes.

## 21. Metric card
- **Impl:** `metric_card()`; value, status badge, confidence/unit/version,
  limitations.
- **Vis:** consistent; grid on desktop, single column mobile.
- **UX:** CALF measures page only; information-dense but clear.
- **Dup:** 2 sites (CALF only).
- **Usage:** CALF Measures.
- **Resp:** grid collapses to 1 column <=640px.
- **A11y:** ok.
- **Treat:** Research-dense compact variant; consistent badge semantics.

## 22. Status label / badge
- **Impl:** `status_badge()` defined but **unused**; pages use inline
  `px-badge` spans inside metric_card and raw status strings in cards.
- **Vis:** consistent where used.
- **UX:** statuses sometimes shown as raw codes (e.g., `observed_status`
  strings in Research cards) without localization.
- **Dup:** two mechanisms (component vs inline span).
- **Usage:** CALF, home status, practice attempts.
- **Resp:** ok.
- **A11y:** text labels included; colors not sole channel.
- **Treat:** make `status_badge` the single status primitive; localize status
  labels; add compact variant.

## 23. Timeline event
- **Impl:** `timeline_event()`; square marker + content.
- **Vis:** clean.
- **UX:** Learning Journey only; no connecting line between events; chronology
  readable.
- **Dup:** 2 sites.
- **Resp:** ok.
- **A11y:** ok.
- **Treat:** add vertical connector; Research variant as compact table.

## 24. Progress / process indicator
- **Impl:** none. Task progression is conveyed by text labels ("target
  identified → practice available → …") in Home cards and Journey events.
- **Vis:** n/a.
- **UX:** students cannot see a visual progression state.
- **Dup:** n/a.
- **Usage:** n/a.
- **Resp:** n/a.
- **A11y:** n/a.
- **Treat:** pixel-style progress steps for the task chain (target → practice
  → attempt → revision → transfer).

## 25. Filter controls
- **Impl:** Research Data "Dataset Filters" tab is a placeholder
  (`research_data_filters_placeholder`); no filter controls exist.
- **Vis:** n/a.
- **UX:** filters promised by nav, not implemented (documented placeholder).
- **Dup:** none.
- **Usage:** Research Data.
- **Treat:** if filters arrive in a later version, use shared select/multi
  components with applied-filter chips.

## 26. Data table
- **Impl:** `table_container()` (px-table-wrap) defined but **unused**;
  research data is rendered as `st.json` blobs.
- **Vis:** raw JSON: collapsed whitespace, hard to scan.
- **UX:** the single biggest Research-View usability gap (Evidence, Learning
  Process, System Audit, Overview data quality, Export History).
- **Dup:** n/a.
- **Usage:** none (component dormant).
- **Resp:** st.json overflows handled by container, but not readable.
- **A11y:** JSON is not table-semantics.
- **Treat:** replace JSON with px-table-wrap tables + expandable detail rows;
  Research density tokens.

## 27. Export preview
- **Impl:** Export Preview tab: privacy mode select + format multiselect +
  Preview button; result rendered via `st.json`.
- **Vis:** raw JSON output.
- **UX:** works; output not formatted as a summary.
- **Dup:** none.
- **Usage:** Research Data.
- **Resp:** ok.
- **A11y:** ok.
- **Treat:** render preview as count summary cards + record table preview.

## 28. Modal / confirmation equivalent
- **Impl:** none. `st.expander` is used for progressive disclosure (audit
  records, writing form sections).
- **Vis:** n/a.
- **UX:** no destructive actions exist, so no confirmation is needed today.
- **Dup:** n/a.
- **Usage:** expanders on Writing, Evidence, Learning, Audit.
- **Resp:** ok.
- **A11y:** expanders keyboard accessible.
- **Treat:** define a pixel dialog pattern before any future destructive or
  irreversible action.

## 29. Mobile navigation behavior
- **Impl:** hamburger + sidebar overlay; radios; tab bar internal scroll on
  Research Data/System Audit.
- **Vis:** sidebar covers content when open.
- **UX:** long stacked radio list; no grouping; touch targets 40–42px.
- **Dup:** n/a.
- **Usage:** all mobile pages.
- **Resp:** verified no overflow.
- **A11y:** keyboard focus order works; height below 44px.
- **Treat:** grouped sidebar, 44px targets, sticky section headers.
