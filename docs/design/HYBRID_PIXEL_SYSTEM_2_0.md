# Hybrid Pixel System 2.0 — Canonical Design Foundation

**Version:** hybrid-pixel-system-2.0-v0.9.4-b
**Status:** implemented (v0.9.4-A foundation; v0.9.4-B Student adoption complete; Research adoption remains v0.9.4-C)
**Canonical token source:** `app/ui/pixel_art.py` — `DESIGN_TOKENS`

## v0.9.4-B Student adoption

The Student role now applies the 720px content-width alias and shared
presentation primitives across Home, Writing, Feedback, Practice, Revision,
and Learning Journey. All six pages preserve the square geometry, hard
shadows, sans-body/technical-mono split, semantic state patterns, responsive
stacking, and local-only asset policy. Each page presents a localized purpose,
learner/task context, evidence, a ranked next action, and an explicit limit.
Research role page-level adoption remains outside this stage.

## 1. Direction

Approved direction **B — Hybrid Pixel System 2.0** (see
`docs/design/PRE_V0.9.4_DESIGN_DIRECTIONS.md` and
`docs/design/PRE_V0.9.4_DECISION_MATRIX.md`): one shared token system with
role-tuned semantic aliases. Student and Research interfaces share
foundational color tokens, semantic status tokens, typography scale,
spacing scale, geometry rules, focus treatment, icon rules, responsive
foundations, form-state semantics, loading semantics, error semantics, and
empty-state semantics.

Role-specific aliases exist for Student/Research density, content width,
and emphasis. Student aliases are applied across all six Student pages in
v0.9.4-B; Research page-level adoption remains deferred to v0.9.4-C. The
aliases remain in one design system.

## 2. Canonical token contract

One Python source of truth: `DESIGN_TOKENS` in `app/ui/pixel_art.py`.
`PIXEL_CSS` and `PIXEL_COMPONENT_CSS` are generated from it; no second token
map exists. `.streamlit/config.toml` repeats only the Streamlit-required
theme keys; `tests/test_design_tokens_v094a.py::TestThemeParity` enforces
parity.

### 2.1 Foundational colors

| Token | Value | Role |
|---|---|---|
| `--px-bg` | `#ffffff` | application background |
| `--px-surface` | `#f4f4f4` | primary surface |
| `--px-surface-elevated` | `#ffffff` | elevated surface (hard shadow only) |
| `--px-text` | `#1a1c2c` | primary text |
| `--px-text-secondary` | `#4a4a58` | secondary text |
| `--px-muted` | `#6b6b7b` | muted text |
| `--px-border` | `#1a1c2c` | border |
| `--px-focus` | `#0f6dbd` | focus outline (3px, 2px offset; >=3:1 against adjacent boundaries) |
| `--px-action` | `#e00047` | primary action (measured 4.93:1 on white) |
| `--px-action-hover` | `#e00047` | hover state (same bg; shadow/translate) |
| `--px-action-active` | `#e00047` | active state (same bg; pressed) |
| `--px-action-disabled` | `#e8e8ec` | disabled background |
| `--px-action-text` | `#ffffff` | primary action text |
| `--px-action-text-disabled` | `#5a5a68` | disabled text (5.55:1) |
| `--px-secondary-action` | `#f4f4f4` | secondary action |
| `--px-link` | `#0f6dbd` | link text |
| `--px-red` | `#ff004d` | decorative pixel red (non-text only) |

`#ff004d` is no longer used behind normal white button text or for any
text-bearing role.

### 2.2 Semantic status states

Success `#00e436` (text `#1a1c2c`), Warning `#ffec27` (text `#1a1c2c`),
Error `#e00047` (text `#ffffff`), Information `#29adff` (text `#1a1c2c`),
Unavailable `#f4f4f4` (text `#6b6b7b`), Candidate `#ffec27`,
Insufficient evidence `#f4f4f4`/`#6b6b7b`, Selected `#29adff`,
Neutral `#f4f4f4` (text `#1a1c2c`). Status meaning never depends on color
alone: badges and notices always carry text labels.

### 2.3 Typography

- Body (navigation, prose, feedback, evidence descriptions, forms, Chinese):
  local/system sans —
  `-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", "Noto Sans SC",
  "PingFang SC", "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif`.
  No remote font dependency.
- Monospace (technical/brand): request IDs, technical IDs, version numbers,
  status codes, metrics and aligned numbers, code-like values, compact
  labels, Pixel Art headings —
  `ui-monospace, "Cascadia Mono", "Cascadia Code", Consolas, SFMono-Regular,
  Menlo, Monaco, "Liberation Mono", "Courier New", monospace`.
- Scale: h1 32px/900, h2 26px/700, h3 20px/700, body 16px/1.6, compact
  14px/1.5, label 13px, metric 18px.

### 2.4 Spacing

4/8/12/16/20/24/32/40/48 px scale with aliases for inline gaps, control
gaps, card padding, section spacing, page spacing, Student density
(32px sections) and Research density (16px sections).

### 2.5 Geometry

- Borders: 4px primary (2px <=640px), 1px hairline for tables only.
- Hard shadows: `2px 2px 0`, `4px 4px 0`, `8px 8px 0 #1a1c2c` — no blur.
- Radius: `0px` everywhere (square corners).
- Focus: 3px `#29adff` outline, 2px offset.
- Control height: 40px desktop, 44px mobile; minimum touch target 44x44 on
  mobile for application-owned controls.
- Content width aliases: Student 720px, Research 1200px (defined; applied
  in later stages).

### 2.6 Responsive and motion

- Breakpoints reuse the validated 640px / 1024px system.
- Motion is disabled: no decorative animation, no non-zero transition, and
  the `prefers-reduced-motion` block is preserved.

## 3. Icon policy

- Local inline SVG only; no remote icon fonts or icon services.
- `app/ui/pixel_art.py::icon()` renders 16x16 pixel-style outline glyphs
  (square caps).
- Decorative icons are `aria-hidden`; meaningful icons carry `role="img"`
  and `aria-label`.
- Icons never carry meaning alone; status always has a text channel.

## 4. Shared component primitives

In `app/ui/components.py` (all token-driven, all with stable `data-testid`):

- `page_header`, `section_header`, `card_group_header` — mono pixel headings.
- `status_badge` — semantic status labels (`px-status-badge`).
- `limitation_notice`, `warning_box`, `info_box`, `success_box`, `error_box`
  — semantic notices with icons (`px-notice`).
- `metric_card`, `feedback_priority_card`, `evidence_quote`, `timeline_event`,
  `audit_record`, `table_container` — existing primitives hardened to tokens.
- `field_error` — inline validation (`px-field-error`, `role="alert"`).
- `loading_box` — loading state without animation (`px-loading`,
  `role="status"`, `aria-live="polite"`).
- `data_table` — compact research table (`px-table-wrap`), HTML-escaped.
- `technical_caption` — monospace technical IDs (`px-mono`).
- `validate_writing_form` — pure Writing-form validation helper.

## 5. Selector policy

Global Streamlit styling uses stable `data-testid` selectors and documented
stable `.st*` classes only; no generated hashed classes. New primitives own
stable `data-testid` attributes. Every global selector is listed in
`docs/development/V0.9.4_A_SPEC.md` section 2.5.

## 6. Adoption boundary

v0.9.4-A implements the foundation and minimal production adoption only:
Writing required-prompt validation, one loading state (Run Export), one
compact research table (Journey counts), mono technical captions, and the
two localized Research Data strings. v0.9.4-B then applies the shared
foundation across all six Student pages; Research redesign remains deferred to
v0.9.4-C.
