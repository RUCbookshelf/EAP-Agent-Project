# Pre-v0.9.4 UI/UX Audit — Current Interface

**Date:** 2026-08-01
**Scope:** design research only; no application source, CSS, or behavior was modified.
**Method:** live FastAPI + Streamlit stack (Python 3.11, Playwright Chromium headless,
temp database copy), all twelve pages inspected with real browser interaction in four
combinations: English/Simplified-Chinese x desktop 1280x900 / mobile 390x844.

## 1. What was inspected and how

- Every Student page (Home, Writing, Feedback, Revision, Practice, Learning Journey)
  and Research page (Overview, Evidence, CALF Measures, Learning Process, Research
  Data, System Audit) was opened through the real sidebar navigation and rendered.
- Representative controls were exercised: essay submission (including an
  empty-writing-prompt submission), practice target load, journey load, evidence
  load, all eight Research Data tabs, and System Audit rendering.
- Evidence artifacts:
  - `verification/design/pre-v0.9.4/current-ui/audit_results.json`
  - `verification/design/pre-v0.9.4/current-ui/screenshots/` (48 page screenshots
    + 7 interaction screenshots, all valid 390x844 or 1280x900 PNGs)
  - `verification/design/pre-v0.9.4/uiuxpro-results/` (9 ui-ux-pro-max searches)

## 2. Quantitative baseline (all four combinations)

| Check | Result |
|---|---|
| Page renders (12 pages x 4 combos) | 48/48 rendered |
| Unexpected console errors | 0 (48/48 pages) |
| Page exceptions | 0 |
| Page-level horizontal overflow | 0 (body width == viewport width on every page) |
| Raw localization keys visible | 0 |
| Keyboard focus visibility | solid 3px `rgb(41,173,255)` outline, 2px offset (text input) |
| Desktop heading scale | h1 44px, h2 36px, body 16px monospace (Streamlit defaults + pixel CSS) |
| Mobile sidebar | hamburger `stExpandSidebarButton`; radios inside 300px sidebar overlay |
| Research Data tabs (mobile) | 8/8 reachable via controlled horizontal scroll (616px content / 358px client) |

## 3. Current Pixel Art constraints (from docs + code)

Authoritative sources: `docs/UI_DESIGN.md`, `docs/design/PIXEL_ART_DESIGN_SYSTEM.md`,
`docs/design/reference/pixel-art/pixel-art-tokens.json`, `app/ui/pixel_art.py`,
`app/ui/components.py`. Constraints currently enforced:

- Square corners everywhere (`border-radius: 0 !important` on all of `.stApp *`).
- Hard offset shadows only (`2px/4px/8px 0 #1a1c2c`), no blur, no soft elevation.
- Solid colors only; gradients and semi-transparent decorative surfaces removed
  (`background-image: none !important`).
- Zero transitions and zero animations (`transition: none !important; animation:
  none !important`), plus a `prefers-reduced-motion` block.
- Canonical palette: dark `#1a1c2c`, white `#ffffff`, surface `#f4f4f4`,
  red `#ff004d`, green `#00e436`, blue `#29adff`, yellow `#ffec27`,
  muted `#6b6b7b`, disabled `#e8e8ec`.
- Monospace-only typography stack (Cascadia/Consolas/…); Chinese via system
  fallbacks.
- Borders: 4px primary (2px <=640px), 1px hairline for tables only; primary
  components must not use 1px borders; no decorative single-side accent borders.
- No nested cards; interactive cards move immediately (hover shadow/translate).
- Buttons: red solid, white bold text; hover/active immediate translate; focus
  3px blue outline; disabled distinct bg, not opacity-only.
- Status badges carry text labels; color never carries meaning alone.
- Role separation: Student hides internal IDs/analyzer versions/config/provider
  details; Research exposes audit records.
- Responsive: 1280x900 and 390x844 targets; <=640px border/shadow/font reductions;
  no unintended horizontal overflow.

Note: `.streamlit/config.toml` does not exist in the repository; Streamlit runs on
framework defaults (the docs reference the file, but it is absent).

## 4. Constraint classification

1. **Essential brand decisions** — square corners, hard offset shadows, solid
   palette, pixel badges, immediate hover/press states, pixel page headers,
   no gradients/blur, role separation.
2. **Accessibility / usability requirements** — visible 3px focus outline,
   status not by color alone, `prefers-reduced-motion`, readable Chinese,
   no horizontal overflow, semantic headings, keyboard-operable controls.
3. **Implementation choices that could change** — monospace *body* typography
   (headings could remain pixel/mono while body moves to a readable sans);
   the exact neon accent values (red/green/blue/yellow); 4px borders on every
   control; button shadow offsets; spacing values; tab-bar styling; sidebar
   stacking order; the `transition: none` global (see 5).
4. **Obsolete / unnecessarily restrictive** — a global `transition: none` on
   *everything* blocks even 80–150ms focus/hover affordances that would improve
   perceived quality without violating the pixel brand; "1.6 line-height
   monospace for all body text" harms reading comfort for a feedback-heavy
   product and Chinese text; the no-nested-card rule is fine but not sacred.
5. **Direct conflicts with ui-ux-pro-max recommendations** —
   - Claymorphism (the skill's top design-system match for "education learning
     SaaS") conflicts with radius 0, no soft shadows, no gradients, no motion.
   - Swiss Modernism 2.0 is compatible with hard edges/grid/high contrast but
     prescribes a single accent color, which conflicts with the four-accent
     semantic status palette (red/green/blue/yellow). Resolution: keep the
     semantic status tokens, use one brand accent for primary actions.
   - Typography guidance (Atkinson Hyperlegible / Inter for readable academic
     UI) conflicts with the monospace-only body constraint.
   - 44px touch targets and 4.5:1 normal-text contrast conflict with current
     measured values (Section 6).

## 5. Accessibility measurements (evidence)

### Contrast (WCAG 2.1, computed from canonical hex values)

| Pair | Ratio | AA normal (4.5:1) |
|---|---|---|
| dark `#1a1c2c` on white | 16.85:1 | PASS |
| white on dark | 16.85:1 | PASS |
| dark on yellow `#ffec27` (warning) | 13.86:1 | PASS |
| dark on green `#00e436` (success) | 9.75:1 | PASS |
| dark on blue `#29adff` (info) | 6.83:1 | PASS |
| muted `#6b6b7b` on white | 5.23:1 | PASS |
| muted on surface `#f4f4f4` | 4.76:1 | PASS |
| **white on red `#ff004d` (primary button, error notice)** | **3.92:1** | **FAIL** |
| **muted on disabled `#e8e8ec`** | **4.28:1** | **FAIL** |

The `docs/UI_DESIGN.md` claim of "WCAG 2.1 AA text contrast" is not true for
white text on the primary red (3.92:1) or muted text on disabled backgrounds
(4.28:1). Primary-button text is 16px bold — not "large text" (needs >=18.66px
bold) — so it fails AA normal-text. This is a design-token issue, not a
framework issue: a slightly darker red (e.g., `#d4003f`) reaches ~4.7:1.

### Touch targets (mobile 390x844, measured bounding boxes)

| Control | Height | 44px target |
|---|---|---|
| Radio option (sidebar) | 42px | FAIL (2px under) |
| Button | 40px | FAIL |
| Select | 40px | FAIL |
| Tab | 40px | FAIL |
| Text input | 40px | FAIL |

### Keyboard / motion

- Focus ring confirmed visible (3px blue, 2px offset) on text inputs.
- All state changes are immediate (`transition: none`), which is accessible but
  visually abrupt; a bounded 80–150ms transition with a `prefers-reduced-motion`
  guard would not violate the pixel brand and would improve affordance.
- Badges always include text labels; color is not the only status channel.
- Heading order is sequential (h1 app title -> h2 page header -> h3 sections);
  some inline section titles use `st.subheader` (h3).

## 6. Major current UI problems (evidence-based)

1. **Primary-action contrast fails AA** — white on `#ff004d` is 3.92:1
   (pixel_art.py canonical tokens; applies to every primary button and the
   error notice).
2. **Writing form validation gap** — submitting with an empty Writing prompt
   passes the UI (only Student ID and essay text are checked,
   `app/ui/pages/student_pages.py`), then fails server-side with a generic
   "The request could not be processed because some information is invalid.
   (while submit)" 422 (`writing_prompt` is required,
   `app/api/schemas.py:64`). Reproduced live; screenshot
   `en_1280x900_writing_validation_error.png`. The student-facing message does
   not say which field is wrong.
3. **Monospace body text** — all body copy is monospace, which suits the pixel
   brand but is measurably harder to read for long feedback/evidence text and
   renders Chinese through mixed system fallbacks. ui-ux-pro-max typography
   guidance (Atkinson Hyperlegible / Inter, 16px+, 1.5–1.75 line-height)
   directly targets this problem.
4. **No loading feedback on most actions** — `st.spinner` exists only on essay
   submission; Load Records / Load Practice Targets / Load Learning Journey
   buttons give no in-progress feedback and are not disabled during the call.
5. **Touch targets under 44px** on mobile for all interactive controls.
6. **Raw JSON as the research display** — Research Evidence, Learning Process,
   System Audit, and Overview's data-quality section render `st.json` blobs;
   `table_container` (px-table-wrap) and `status_badge` exist in components.py
   but are unused. Scanning long JSON is the largest Research-View usability
   gap.
7. **No icon system** — navigation and buttons are text-only; there is no
   consistent icon language (ui-ux-pro-max icons search returned no database
   match; general guidance: one SVG family such as Phosphor/Lucide).
8. **Zero-motion UI** — the global `transition: none !important` makes hover and
   focus feedback instantaneous; acceptable but abrupt, and it prevents subtle
   affordance cues that would help state clarity.
9. **Mobile sidebar discovery** — navigation is behind a hamburger; the sidebar
   stacks language + role + page radios (10–11 rows) and requires scrolling.
   Functional (verified) but heavy.
10. **Localization residuals** — two hardcoded English strings in Research Data
    (Human Review "Target ID" label and "Export:" success prefix) documented in
    the v0.9.3-B closure; everything else verified localized (295-key parity).
11. **`.streamlit/config.toml` missing** — documented configuration for the
    Streamlit runtime is absent; framework defaults apply.
12. **Primary button 1px border** — Streamlit's internal button border (1px)
    is not fully overridden (known framework limitation from v0.9.2.1).

## 7. What works well (keep)

- Consistency: components (`page_header`, `section_header`, `info_box`,
  `warning_box`, `limitation_notice`, `empty_state`) are used uniformly across
  the 12 pages.
- Role separation is real and verified: Student pages hide internal identifiers,
  analyzer versions, provider details, and configuration versions.
- Empty states are handled consistently (message + explanation + next action).
- Error presentation is role-appropriate and localized; research errors carry
  request IDs, category, HTTP status, and retryability.
- Localization works: 295/295 key parity, zero raw keys, zero overflow in
  Chinese desktop and mobile.
- No unintended horizontal overflow anywhere; the mobile tab bar's internal
  scrolling is controlled and usable.
- The pixel identity gives the product a distinctive, memorable look that is
  unique among generic educational dashboards.

## 8. Pixel Art: helps or obstructs?

Helps: brand distinctiveness, consistency, playful-but-serious tone, hard
state changes that feel responsive, strong heading borders that anchor pages.

Obstructs: readability (monospace body + Chinese fallbacks), AA contrast on the
primary action, touch ergonomics at small sizes, density and scanability of
research data (hard borders + cards consume vertical space; raw JSON blocks),
and any motion-based affordance.

Net: the identity is worth preserving; the constraints that hurt are the
typography rule, the primary-action color, the touch sizes, and the research
display pattern — all changeable without abandoning the brand.
