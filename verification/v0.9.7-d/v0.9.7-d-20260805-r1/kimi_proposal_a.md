# Design Proposal A — Calm, Credible Student Workspace (v0.9.7-D / D1.1)

**Author:** Senior product designer (design consultation A)
**Date:** 2026-08-05
**Baseline:** v0.9.7-C closure (HEAD `6a2e927`), per `design_input_package_v1.md`
**Inputs read:** `design_input_package_v1.md`; before-screenshots (Journey grouped en/zh desktop+mobile, Feedback priority, Practice task/completed, Writing saved, Revision saved, Home); `app/ui/pixel_art.py` `DESIGN_TOKENS` + `build_css_vars()` (read-only, to ground token mapping); UI/UX Pro Max skill database (see "UI/UX Pro Max guidance applied").
**Scope:** Visual-system consultation only. This document proposes tokens, components, layout rules, state patterns, and acceptance criteria. It changes no production code, tests, or locales, and runs no git commands. Every change below is a recommendation for the engineering decision table; any adopted token change lands in the single canonical source `app/ui/pixel_art.py::DESIGN_TOKENS` with its guard tests updated by engineering.

---

## Constraints (restated)

1. Preserve v0.9.7-B/C behavior and wording semantics: Journey cycle grouping, raw events, ordering, dedup, learner ownership, Practice reuse/completion/attempt/evaluation semantics, navigation destinations, persistence. No mastery/pass/transfer/proficiency/CEFR/causal claims. Only two fixed disclaimer phrases exist: "no priority passed the Diagnostic Gate" and the all-descriptive "stable transfer" limitation.
2. No remote fonts, icons, images, CDNs, or UI resources.
3. Work within Streamlit and the current local CSS/component architecture: single canonical token source `app/ui/pixel_art.py`; `data-testid` hooks and documented stable classes only; never generated hashed classes.
4. Support English and Chinese (en/zh_CN parity; no fixed-width assumptions).
5. Avoid text embedded in decorative images.
6. Preserve existing mobile functionality without attempting the full v0.9.7-E redesign.
7. No backend or data-model changes.
8. No new product features.
9. Prefer reusable shared rules over page-specific styling.
10. Journey is the representative implementation page.

---

## UI/UX Pro Max guidance applied

Skill: `C:\Users\16073\.agents\skills\ui-ux-pro-max\SKILL.md` (read fully). Methods used:

- **Step 2 workflow (`--design-system`)** run twice. First result ("kids education": Baloo 2 / Comic Neue, teal, playful) was rejected against the desired product character (calm, credible, not childish). Second run (`--variance 2 --motion 1`, "university academic research writing tool, professional, credible, minimal") returned an institutional-minimal direction (restrained palette, high-contrast action, WCAG AA emphasis) that informed Sections A–B. Its Google Fonts import and serif pairing were **declined** (constraint 2: no remote resources; pixel identity), keeping the existing local/system stacks.
- **Priority table §1 Accessibility (CRITICAL):** `color-contrast` (≥4.5:1 text), `focus-states`, `color-not-only` → Sections B, G, K (every state gets icon + localized text, never color alone).
- **§2 Touch & Interaction (CRITICAL):** `touch-target-size` (≥44px), `touch-spacing`, `loading-buttons` → Sections D, F.
- **§4 Style Selection:** `style-match`, `consistency`, `state-clarity`, `elevation-consistent`, `primary-action` (exactly one primary CTA per view) → Sections A, E, F.
- **§5 Layout & Responsive:** `spacing-scale` (4/8px rhythm), `visual-hierarchy` (size/spacing/contrast, not color alone), `line-length-control` → Sections D, E, I.
- **§6 Typography & Color:** `font-scale`, `weight-hierarchy`, `color-semantic` (semantic tokens, no raw hex), `line-height` (1.5–1.75), `truncation-strategy` (wrap, don't truncate), `number-tabular` (mono for IDs/figures) → Sections B, C, J.
- **§8 Forms & Feedback:** `empty-states`, `error-clarity`, `error-recovery`, `disabled-states`, `loading-states`, `success-feedback` → Sections G, H.
- **`--domain ux` validation pass** ("forms empty-state loading error accessibility contrast focus", 14 rules): error placement near context, aria-live/role=alert for errors, empty states with helpful message + action, spinner/skeleton beyond 300ms → Sections G, K.
- **Pre-Delivery Checklist** adopted into Section K.
- **Deliberately not adopted:** micro-interactions/GSAP motion (product motion is disabled; pixel identity), exaggerated oversized typography, hero/landing pattern, remote serif fonts, kids palette, dark mode (deferred to v0.9.7-E per register E1).

---

## A. Visual direction

**VD-01 — Concept: "Calm ledger."** A quiet record-keeping workspace: white page, ink structure, tinted state washes, and one red reserved for forward action. The pixel identity is retained as *structural crispness* — square corners, solid fills, hard offset shadows on interactive surfaces — and demoted from arcade loudness to an editorial-technical register: monospace survives only where it carries meaning (IDs, references, version, metrics). Intended emotional tone: calm, credible, focused, supportive without being childish; a place where a learner trusts what they read because nothing is shouting.

**VD-02 — Design principles (priority order, matching package §9).**

1. Comprehension before decoration: every visual element carries state or structure; nothing is ornamental except the (small, deliberate) pixel texture.
2. Quiet by default, loud by exception: states use tinted surfaces; solid saturated fills appear only on the single primary action.
3. One loud thing per view: one primary action and at most one focused panel per page region.
4. Hierarchy through spacing, border weight, and typography — not through more colors.
5. Shared rules over page-specific styling: every rule below is defined once and reused across all six Student pages.

**VD-03 — Prohibited visual patterns (with current offenders).** Neon full-bleed banners (today's `#00e436` success bar, `#ffec27` warning bar, `#29adff` info fills — register S3); gamified solid step tiles (Home "1 Write / Complete" green block); gradients, glassmorphism, soft shadows, rounded corners; badge walls; color-only state signaling; emoji as icons; icon-only critical actions; marketing hero blocks; decorative animation; per-page ad-hoc hex values (forbidden by tests); uppercase or letter-spaced Chinese text; text embedded in decorative images; remote assets of any kind.

---

## B. Semantic color system

All values are defined once in `DESIGN_TOKENS` and consumed via the generated `--px-*` custom properties. Contrast ratios below were measured with the WCAG relative-luminance formula on 2026-08-05.

**C-01 — Base and neutral tokens (keep existing; add one).**

| Token | Value | CSS var | Use | Contrast evidence |
|---|---|---|---|---|
| app background | `#ffffff` (keep) | `--px-bg` | page canvas | — |
| primary surface | `#ffffff` (keep) | `--px-white` | cards, focused panel | — |
| secondary surface | `#f4f4f4` (keep) | `--px-surface` | sidebar, subtle containers, metadata rows | — |
| elevated/focused surface | `#ffffff` + shadow-md (keep) | `--px-surface-elevated` | focused panel only (E) | — |
| primary text | `#1a1c2c` (keep) | `--px-text` | headings, body | 16.85:1 on white; 15.32:1 on surface |
| secondary text | `#4a4a58` (keep) | `--px-text-secondary` | intros, secondary body | 8.71:1 on white |
| muted text | `#6b6b7b` (keep) | `--px-muted` | metadata, helper, references | 5.23:1 on white; 4.76:1 on surface |
| border (structural) | `#1a1c2c` (keep) | `--px-border` | card outlines, focused panel, controls | — |
| **border-subtle (NEW)** | `#8a8a9c` | `--px-border-subtle` | hairline separators, nested-item outlines, metadata rules | 3.39:1 on white; 3.08:1 on surface (passes 3:1 non-text UI guideline) |
| focus | `#0f6dbd` (keep) | `--px-focus` | 3px focus outline, 2px offset | 5.33:1 on white; 4.84:1 on surface |

Usage rule: `border` (ink) for card outlines, controls, and the focused panel; `border-subtle` only for inner separators and nested-item hairlines; never for control outlines or anything that alone signals interactivity.

**C-02 — Action tokens (keep; add destructive; add reservation rules).**

| Rank | Tokens | Notes |
|---|---|---|
| primary action | bg `#e00047`, text `#ffffff` (4.93:1), border-thin ink, shadow-sm (keep) | solid fill; the only saturated solid surface in the product |
| secondary action | bg `#f4f4f4`, text `#1a1c2c`, border-thin ink (keep) | default for record-level actions |
| tertiary / text action | text `#0f6dbd`, no fill, underline on hover/focus (keep link token) | low-emphasis inline actions |
| destructive (NEW, reserved) | `#a30d3d` on tint `#fdeaef` (6.78:1 measured) | no current Student surface needs it; token reserved so a future need cannot improvise; always paired with a confirmation pattern |
| disabled | bg `#e8e8ec`, text `#5a5a68` (5.55:1), no shadow, `not-allowed` cursor (keep) | always accompanied by a reason in helper text where the cause is not obvious |

Reservation rules: `#e00047` means "forward action" and nothing else — it must not paint nav selection, badges, category titles, or decorative blocks (today's crimson priority-title and crimson nav marker violate this). Selection/current-location uses the selected/info blue family or plain ink emphasis. `pixel-red #ff004d` stays decorative-only, non-text.

**C-03 — Quiet semantic state tokens (core fix for register S3).** Every state notice/badge is: tinted background + 4px left accent bar (solid) + local SVG icon + bold localized status label + body text in `--px-text`. Full-bleed neon fills are retired from notices.

| State | bg tint (NEW) | accent / badge border (NEW) | label text on tint (NEW) | Icon | Measured AA |
|---|---|---|---|---|---|
| informational | `#e8f3fb` | `#0f6dbd` | `#0b4f86` | `info` | 7.53:1 label; 4.73:1 accent |
| success / completed | `#e6f6ec` | `#1c7a45` | `#14532d` | `check` | 8.14:1 label; 4.79:1 accent |
| warning / attention | `#fdf6d8` | `#a16207` | `#713f12` | `warning` | 7.99:1 label; 4.54:1 accent |
| error | `#fdeaef` | `#c01048` | `#a30d3d` | `error` | 6.78:1 label; 5.34:1 accent |
| neutral / unavailable / insufficient | `#f4f4f4` | `#6b6b7b` | `#4a4a58` | per G | 7.92:1 label |

The legacy neon values (`#00e436`, `#ffec27`, `#29adff`) are replaced in the canonical `semantic` map; pixel character is preserved through solid tints, square corners, and the hard accent bar — not through saturation.

**C-04 — Product-specific state mapping.**

| Product state | Surface recipe |
|---|---|
| active Practice (available / in progress) | info tint + 2px `#0f6dbd` border on the stage item + info-family badge; the 2px colored border is the "selected/live" signal |
| evaluation unavailable | neutral tint + **dashed** 2px `#6b6b7b` border + `clock` icon + existing localized text; dashed = "recorded, not assessable", never error red |
| legacy / unlinked / unresolved provenance | neutral tint + dashed border + `info` icon + explicit provenance text via record reference; never fabricated links |
| submitted / completed confirmations | success tint notice immediately after save; on later renders, a success badge on the stage item (not a persistent banner) |
| no priority ("no priority passed the Diagnostic Gate") / insufficient evidence | neutral tint + `info` icon; these are outcomes, not errors — never warning yellow or error red |
| limitation / disclaimer notices | neutral or warning tint per existing semantics; wording untouched |

**C-05 — Never color alone.** Every state surface must include (a) one icon from the existing local SVG set (`check`, `warning`, `info`, `error`, `arrow_right`, `empty`, `clock`) and (b) a localized text label. Dashed vs solid border is the secondary channel distinguishing "unavailable/legacy" from plain neutral. Color pairs alone never carry meaning (skill `color-not-only`, `color-not-decorative-only`).

---

## C. Typography hierarchy

**TY-01 — Role tokens and scale (add role aliases to `DESIGN_TOKENS.typography`; sizes ride the existing scale).**

| Role | Font stack | Size / weight / line-height | Use |
|---|---|---|---|
| page title | sans (NEW role `--px-font-display`) | 1.75rem / 700 / 1.25 | one per page |
| page introduction | sans | 1rem / 400 / 1.6, `--px-text-secondary` | purpose block under title |
| section heading | sans (display role) | 1.25rem / 700 / 1.3 | major sections |
| card title | sans (display role) | 1.0625rem / 600 / 1.35 (add `weight-semibold: 600`) | cycle cards, priority cards, panels |
| body | sans (existing `--px-font-body`) | 1rem / 400 / 1.6 (keep) | prose |
| metadata | sans | 0.875rem / 400 / 1.5, muted | label/value facts |
| helper text | sans | 0.875rem / 400 / 1.5, muted | under controls |
| status label | sans | 0.8125rem / 700 / 1.4 | badges, state labels |
| button text | sans | 1rem / 700 (primary), 1rem / 600 (secondary/tertiary) | actions |
| technical/mono | mono (existing `--px-font-mono`) | 0.875rem / 400 | IDs, references, version, metrics |

**TY-02 — Mono-heading reconciliation (fixes register S1).** Re-point `--px-font-heading` from `var(--px-font-mono)` to the sans display role in `DESIGN_TOKENS` (one canonical line). Monospace is preserved — deliberately and visibly — for brand-technical roles: app version string, `cycle-*` IDs, `Submission #n` references, metrics, code-like values. This keeps the pixel/technical texture as an accent instead of a wall. Chinese headings then render in Noto Sans SC / PingFang SC / Microsoft YaHei via the existing stack, eliminating the mono-CJK crowding seen in the zh screenshots; English headings keep a technical voice through weight 700 and square structure rather than mono letterforms.

**TY-03 — Readability rules.** Body line-length stays ≤ ~75 characters (the existing 720px student column already enforces this); body line-height 1.6 serves both locales; no justified text; no negative letter-spacing; no uppercase transforms anywhere (they break Chinese and are unnecessary for English — status labels use weight + color instead).

**TY-04 — Mono scope rule.** Mono is applied to Latin/digit technical strings only (skill `number-tabular`). It must never wrap zh prose, notices, or button labels; a mono ID inside a zh sentence renders as inline mono while the sentence stays sans.

---

## D. Spacing and sizing scale

**SP-01 — Scale roles (keep the 4px-base scale; assign roles; fix register C2).**

| Role | Token | Value |
|---|---|---|
| micro (icon gaps, badge padding) | `--px-space-1` | 4px |
| inline (label↔value, icon↔text) | `--px-space-2` / `--px-inline-gap` | 8px |
| control gap (between controls) | `--px-space-3` | 12px |
| card padding (default) | `--px-card-pad` | 16px |
| card padding (student alias, keep) | density `student-card-pad` | 20px |
| section spacing | `--px-section-space` | 32px |
| page spacing | `--px-page-space` | 40px |

Rule: no literal pixel margins/paddings in components — every gap resolves to a token (this removes today's mixed inline 20px vs 32px section rhythm).

**SP-02 — Control sizing.** Control height 40px desktop / 44px mobile (keep); minimum touch target 44×44px (keep; skill `touch-target-size`); buttons and inputs use `min-height` (never fixed `height`) so bilingual labels may wrap to two lines without clipping; adjacent targets keep ≥8px separation.

**SP-03 — Geometry and icon sizes.** Radius 0 everywhere (pixel identity, keep). Border-weight assignment: 4px reserved for state accent bars and the focused panel; 2px for card/button/notice outlines; 1px hairline (in `border-subtle`) for nested items and metadata separators. Shadows: `shadow-sm` (2px) on interactive cards and buttons; `shadow-md` (4px) on the focused panel; `shadow-lg` (8px) stays defined but unused on Student pages. Icon size tokens (NEW): `icon-sm` 16px (badges, inline), `icon-md` 20px (notices), `icon-lg` 24px (empty states).

---

## E. Surface hierarchy

**SF-01 — Surface levels (token-mapped; fixes register C3).**

| Level | Name | Recipe | Use |
|---|---|---|---|
| L0 | plain page section | `--px-bg`, no border | page canvas, direct prose |
| L1 | subtle container | `--px-surface`, 1px `border-subtle` or none, pad 16 | context/metadata blocks, intro purpose block |
| L2 | primary card | `--px-white`, 2px ink border, `shadow-sm`, pad 20 (student) | cycle cards, priority cards, state panels |
| L3 | nested stage item | `--px-white`, 1px `border-subtle`, no shadow, pad 12/16 | stage items inside L2 |
| notice | state tint | C-03 recipe (tint + 4px accent bar + icon + label) | all state/limitation messages |
| empty state | L0/L1 + dashed 1px `border-subtle` (optional), muted icon | absences with next step |
| focused panel | `--px-surface-elevated`, 4px ink border, `shadow-md`, pad 20 | the single "act here now" block (e.g., current practice step) |

**SF-02 — Nesting rules.** Maximum depth L0 → L2 → L3; a bordered surface never sits inside an L3; notices attach to L1/L2, never nest inside L3 content; one focused panel per page; L3 items in one L2 share one recipe (no per-item restyling); shadows never appear on nested levels.

**SF-03 — Context block typing (fixes P3).** `student_context_block` is formally typed as L1 with a metadata-row interior (H, CP-08). Hierarchy between "current task" and "latest status" (Home) is expressed by level and border weight — current task = L2, latest status = L1 — never by adding new colors. Home workflow steps become an L1 numbered list with status badges, replacing the gamified solid tiles.

---

## F. Action hierarchy

**ACT-01 — Ranks and recipes.** Per C-02: primary = solid `#e00047`; secondary = surface + 2px ink border; tertiary = text-only link blue; destructive = reserved deep red with confirmation; disabled = `#e8e8ec`/`#5a5a68` plus a helper-text reason when non-obvious; pending = the action becomes disabled and a unified loading indicator appears adjacent to the action row (button wording never changes — wording is frozen; skill `loading-buttons`).

**ACT-02 — Placement and grouping.** Actions live in an action row at the end of the block they act on: horizontal, gap 12px, order primary → secondary → tertiary, left-aligned (both en and zh are LTR). Below 640px the row stacks vertically, full-width, same order. Destructive actions are isolated by ≥24px from other actions. The page-level primary CTA sits in the next-step action block, after content and before the limitation notice.

**ACT-03 — Quantity rules (fixes register C1).** Exactly one primary action per page view (skill `primary-action`); record-level navigation actions (`Open Revision`, `Open Practice`) are always secondary rank — today's full-width default-looking Journey buttons become secondary buttons in the stage item's action row, full-width only in the mobile stack. Tertiary is reserved for low-stakes inline affordances; no new tertiary destinations are introduced.

---

## G. State system

**ST-01 — Record and system state matrix.** Badge text always comes from existing localized state labels (wording frozen); the badge component (H, CP-03) is activated on Journey, fixing register S3's plain-text state rows.

| State | Surface / border | Icon | Badge | Text channel | Action |
|---|---|---|---|---|---|
| active (Practice available/in progress) | L3 + 2px `#0f6dbd` border | `arrow_right` | info family | existing target/focus text | secondary Open Practice |
| completed | success tint notice (fresh) / success badge (later) | `check` | success family | existing completion text | per page flow |
| submitted | success tint notice on save; badge on stage item thereafter | `check` | success family | existing reference text | per page flow |
| feedback available | success badge on feedback stage item | `check` | success family | existing count/category text | secondary (existing nav) |
| no priority | neutral tint notice | `info` | neutral | fixed phrase "no priority passed the Diagnostic Gate" (unchanged) | existing next step |
| insufficient evidence | neutral tint notice | `info` | neutral | existing insufficiency text; never error styling | existing |
| evaluation unavailable | neutral tint + dashed 2px border | `clock` | neutral | existing unavailable text; never implies failure | secondary Open Practice |
| legacy / unlinked | neutral tint + dashed border | `info` | neutral | provenance text (valid/legacy/unresolved) via record reference | none fabricated |
| loading | unified loading box: neutral tint + `clock` + localized text | `clock` | — | existing loading strings | — |
| empty | empty-state recipe (E) | `empty` | — | helpful message + existing next-step wording | optional secondary |
| recoverable error | error tint notice + retry-capable action in its action row | `error` | — | cause + recovery path (existing strings) | secondary retry |
| blocking error | error tint notice, no action, explanation + reference | `error` | — | explanation text; never red full-bleed | none |

**ST-02 — System state unification (fixes S4, P4).** One loading component (`loading_box` recipe: neutral tint, `clock` icon, text) replaces `st.spinner` on Home/Journey/Practice — presentational only, no behavior change. One error component with two variants (recoverable / blocking) replaces the `render_api_error` + inline `st.error` mix on Student pages; recoverable always shows its recovery action near the error context (skill `error-recovery`, `error-placement`).

**ST-03 — Combination rules.** A stage item shows exactly one status badge at a time; at most two notices stack inside one stage item; status text is present even when an icon is present; when several sub-states co-occur (e.g., completed Practice with evaluation unavailable), the badge reports record state and the notice reports the sub-state — no merged or invented states.

---

## H. Core component specifications

Each spec: purpose / structure / token mapping / states / bilingual notes / acceptance criterion.

**CP-01 — Page header.** Purpose: orient the learner. Structure: page title (TY-01) + page introduction + optional disclaimer notice directly beneath. Tokens: `--px-font-display`, `--px-text-secondary`, `--px-page-space` above, 8px title→intro gap. States: none. Bilingual: zh title in sans; intro wraps at any width. Acceptance: computed `font-family` of the page title matches the sans stack in both locales; intro never truncates at 390px.

**CP-02 — Section header.** Purpose: delimit major sections. Structure: section-heading text + full-width 1px `border-subtle` rule (replaces today's heavy black bar). Tokens: 32px space above, 16px below. States: none. Bilingual: zh renders in sans 700. Acceptance: rule uses `--px-border-subtle`; spacing resolves to tokens only.

**CP-03 — Status badge.** Purpose: compact record-state chip (activates the existing unused `status_badge`). Structure: 16px icon + status-label text; square; tint bg + 1px accent border per C-03/C-04. Tokens: padding 4px/8px, `--px-space-2` icon gap. States: all ST-01 record states. Bilingual: no uppercase; label may wrap. Acceptance: badge always contains icon + text (never a dot or color alone); present on Journey cycle-stage row and every stage item with a record state.

**CP-04 — Action row.** Purpose: one grouped action zone per block. Structure: horizontal flex, 12px gap, rank order per ACT-02; stacks full-width below 640px. Tokens: control heights SP-02. States: normal / disabled / pending per ACT-01. Bilingual: buttons use `min-height`, labels wrap. Acceptance: ≤1 primary per row; all targets ≥44×44px at 390px width.

**CP-05 — Notice.** Purpose: inline state/limitation message. Structure: C-03 recipe (tint + 4px accent bar + 20px icon + bold label line + body). One component with a `state` variant absorbs today's `warning_box`/`info_box`/`success_box`/`error_box` visuals. Tokens: pad 16, 16px bottom margin. States: success/info/warning/error/neutral; dashed variant for unavailable/legacy. Bilingual: label and body wrap; zh sans. Acceptance: no full-bleed neon fill remains anywhere; every notice has icon + text; label pairs meet AA per C-03.

**CP-06 — Empty state.** Purpose: explain absence and point forward. Structure: 24px `empty` icon (muted) + message (body, secondary) + optional secondary action; surface per E. Tokens: 24px padding, `--px-muted`. States: default. Bilingual: message wraps. Acceptance: never a blank region; message + (where defined) action render in both locales.

**CP-07 — Error state.** Purpose: communicate failure with recovery. Structure: notice variant=error; recoverable adds its existing recovery action in an action row; blocking adds explanation body only. Tokens: error set from C-03. States: recoverable / blocking. Bilingual: error text wraps; no raw technical keys shown. Acceptance: the two variants are visually and textually distinguishable (action presence + label); Student pages no longer mix `st.error` with `render_api_error`.

**CP-08 — Metadata row.** Purpose: label/value facts (learner, references, counts). Structure: two-column grid — label column auto-sized, max 45%; value column wraps; 1px `border-subtle` hairline between rows. Tokens: label = metadata role muted; value = body (mono only for IDs). States: default / quiet. Bilingual: no fixed label width; longest en label at 390px wraps without overlap. Acceptance: no horizontal scroll in the grid at 390px in either locale.

**CP-09 — Record reference.** Purpose: provenance traceability (`cycle-*`, `Submission #n`, `Feedback #n`). Structure: mono compact text, muted; optional sans prefix label. Tokens: `--px-font-mono`, 0.875rem, `--px-muted`. States: default. Bilingual: mono only on Latin/digit runs; zh prefix labels stay sans. Acceptance: computed mono font-family on the ID; reference wraps/breaks instead of truncating.

**CP-10 — Cycle card.** Purpose: group one writing cycle (fixes register C4). Structure: L2 card; header row = card title ("Writing Cycle") + record-reference chip (`cycle-{id}` mono) + cycle-stage badge; body = ordered stage items (CP-11). Tokens: L2 recipe (2px ink border, `shadow-sm`, pad 20); 24px between cards. States: default; may contain the unlinked warning notice. Bilingual: header row wraps (title, chip, badge may reflow to two lines at 390px). Acceptance: each cycle is a distinct bordered card in the DOM with its own header; cycle distinction no longer relies on a lone mono caption.

**CP-11 — Stage item.** Purpose: one stage (submission, feedback, practice) inside a cycle card (fixes P1). Structure: L3 inset block; top row = stage label (card-title 600) + status badge (right, reflows below at narrow widths); then ≤2 metadata rows; then any notices; then its action row (secondary only). Tokens: 1px `border-subtle`, pad 12/16, 8px internal gaps. States: per ST-01. Bilingual: label + badge wrap without overlap. Acceptance: exactly one badge per item; no shadows; nesting rules SF-02 hold.

**CP-12 — Practice state panel.** Purpose: represent Practice consistently on Journey and Practice pages. Structure: stage-item variant whose notice is state-driven per C-04/G: available (info, 2px blue border), attempted (info tint, `clock`), evaluation available (info), evaluation unavailable (neutral dashed, `clock`), completed (success), unavailable/legacy (neutral dashed + provenance text). Tokens: C-04 set. States: the six Practice states. Bilingual: all labels from existing locale keys. Acceptance: each of the six states has a distinct non-color channel (icon, border style, and/or badge text); all pairs AA.

---

## I. Journey representative-page composition

**J-01 — Page skeleton (fixed order; no behavior change).** Page header (title + introduction) → disclaimer notice (quiet info) → learner context block (L1 metadata rows) → writing-cycle cards (existing frozen ordering) → next-step action block (single primary) → limitation notice. Cycle hierarchy: each cycle = one CP-10 card; stages appear inside in the existing frozen order — submissions (Original, then Revised with its "Revision of #n" reference) → feedback stage → Practice activity; the unlinked warning notice attaches to its cycle card. This converts today's flat block stack into visible cycle grouping without touching grouping logic, ordering, dedup, or raw events.

**J-02 — Stage composition and placement.** Stage items per CP-11. Practice is placed after the feedback stage inside its cycle card (current position preserved). Status placement: badge top-right of the stage item; state detail as a quiet notice inside the same item (no-priority, insufficient, evaluation-unavailable, attempt-saved). Action placement: `Open Revision` / `Open Practice` as secondary buttons in the item's action row (fixes C1). Metadata density: ≤2 metadata rows visible per stage item; provenance and references render as record references (mono, muted), replacing the leading-space raw-text trick (register O2) with the proper label primitive.

**J-03 — Variants.** Empty journey: CP-06 with existing next-step wording. Loading: unified loading box (ST-02). Errors: CP-07 recoverable/blocking. Collapse/expand: **optional and deferrable** — a native `st.expander` per cycle, default expanded, is the only acceptable mechanism; it adds no state, no backend, and no new semantics. If engineering judges even this as added complexity for this stage, all cycles stay expanded (default recommendation: stay expanded).

---

## J. Bilingual resilience

**BL-01 — Layout resilience rules.** No fixed widths or heights on any text container; controls use `min-height`; buttons, badges, metadata labels, and notice bodies wrap (skill `truncation-strategy`: wrap, never truncate); metadata grid label column is content-sized (max 45%), never pixel-fixed; mixed technical references (mono ID inside zh prose) keep baseline alignment via inline mono styling; all grids and rows reflow at 390px with token gaps. Both locales are designed for the longer of the pair: en strings sized with ~30% growth headroom, zh verified against crowding at small widths.

**BL-02 — Text rules.** zh renders in the sans stack everywhere including headings, badges, and status labels (TY-02); no uppercase, no letter-spacing, no fixed-width assumptions in any locale; status labels use weight + color, not case; mono is confined to Latin/digit IDs. Verification covers the longest current en labels and their zh counterparts at both 390px and 1280px, plus mixed-locale strings (zh sentence containing a mono `cycle-*` reference).

---

## K. Acceptance checklist

**K-01 — Token and source integrity.** All visual values resolve from `DESIGN_TOKENS`/generated CSS; no literal hex in components or pages; no second token map; `.streamlit/config.toml` parity test passes; browser matrix confirms zero remote requests and no `url(`/`@import`/remote-font references.

**K-02 — Contrast.** All text pairs ≥4.5:1 (C-01/C-03 table values are the contract); focus outline ≥3:1 against adjacent surfaces; control/state borders ≥3:1 where they delineate components; verified by the token contrast guard test updated to the new pairs.

**K-03 — Behavior and wording preservation.** Full non-live core baseline green (1132 passed / 8 skipped as of the v0.9.7-C baseline, or its successor); locale parity 600/600; zero wording changes (optional register O1 copy touch only if separately approved); Journey guard test (`test_v097c_wu3_journey_ui`) green: rendered text, buttons, zero writes.

**K-04 — Rendered structure.** Browser matrix en/zh × 390/1280 via `data-testid` and stable class hooks (never hashed classes): no horizontal overflow; all touch targets ≥44px; page titles computed in the sans stack in both locales; every notice carries icon + text; exactly one primary action per page; status badges present on Journey cycle and stage rows; loading presentation is the same component on all six Student pages.

**K-05 — State coverage.** All twelve G-system states (ST-01) rendered in verification evidence across the existing screenshot states (Journey grouped/fresh, Feedback priority/no-priority, Practice task/saved/completed/re-entry, Writing/Revision saved): each shows its icon + text channel, correct tint/border recipe, and correct action rank; recoverable and blocking errors are distinguishable in both channels.

---

## Out of scope / deferred

Full mobile redesign, dark mode, animation system, illustration system, new branding assets, full accessibility remediation beyond the criteria above, Research View changes (register E1, v0.9.7-E+). Optional register O1 copy touch (`?` artifacts) is a separate, semantics-preserving decision. No backend, data-model, navigation, wording, or feature changes are proposed anywhere in this document.
