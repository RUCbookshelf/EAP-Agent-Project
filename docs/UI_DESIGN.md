# UI Design — Hybrid Pixel System 2.0 (v0.9.4-A foundation)

## Design system

The canonical design foundation is **Hybrid Pixel System 2.0**: one shared
token system for Student and Research interfaces with role-tuned semantic
aliases. The authoritative reference is
`docs/design/HYBRID_PIXEL_SYSTEM_2_0.md`; the single token source is
`app/ui/pixel_art.py` (`DESIGN_TOKENS`), which generates the injected CSS.

Key v0.9.4-A changes:

- Body prose, navigation, forms, feedback, evidence descriptions, and
  Chinese text use a readable local/system sans stack; monospace is
  constrained to technical/brand roles (IDs, versions, status codes,
  metrics, code-like values, pixel headings).
- Primary action red is `#e00047` (measured 4.93:1 on white for normal,
  hover, and active states); `#ff004d` remains only as a decorative
  non-text accent.
- `.streamlit/config.toml` aligns the Streamlit theme with the tokens
  (parity-tested).
- Focus, spacing, geometry, semantic status, density, responsive, loading,
  error, and empty-state tokens are centralized.
- Local SVG icon primitive with accessibility policy; no remote fonts or
  icons.

The v0.9.2 Pixel Art identity rules that remain in force: square corners,
hard offset shadows, solid colors, no gradients/blur/glassmorphism, no
decorative motion, status never communicated by color alone.

The remainder of this file documents the v0.9.2 Pixel Art baseline that the
hybrid foundation builds on.

---

# v0.9.2 Pixel Art baseline

## Design system

v0.9.2 introduces a coherent Pixel Art visual identity for the complete
application. The interface combines an authentic 8-bit visual language with
the clarity of an academic research application.

### Canonical color palette

Limited solid-color palette (no gradients, no semi-transparency):

| Token | Hex | Semantic use |
|-------|-----|-------------|
| `--px-dark` | `#1a1c2c` | Borders, headings, major structural elements |
| `--px-white` | `#ffffff` | Main surfaces, card backgrounds |
| `--px-surface` | `#f4f4f4` | Secondary surfaces, sidebar |
| `--px-red` | `#ff004d` | Primary action, critical state |
| `--px-green` | `#00e436` | Confirmed, available state |
| `--px-blue` | `#29adff` | Information, focus, selected state |
| `--px-yellow` | `#ffec27` | Warning, pending, attention state |
| `--px-muted` | `#6b6b7b` | Secondary text |
| `--px-disabled-bg` | `#e8e8ec` | Disabled backgrounds |

### Borders

- Desktop primary: `4px solid #1a1c2c`
- Small mobile: `2px solid #1a1c2c`
- Hairline (tables, separators): `1px solid #1a1c2c`

### Hard shadows

No blur radius; no soft elevation; no transparent drop shadows.

- Small: `2px 2px 0 #1a1c2c`
- Medium: `4px 4px 0 #1a1c2c`
- Large: `8px 8px 0 #1a1c2c`

### Radius and transitions

- All border-radius: `0px` (square corners)
- All transitions: `none`
- State changes are immediate and hard

### Typography

Monospace stack: `ui-monospace, Cascadia Mono, Cascadia Code, Consolas,
SFMono-Regular, Menlo, Monaco, Liberation Mono, Courier New, monospace`

- H1: 900 weight (heavy)
- H2-H3: 700 weight (bold)
- Body: readable monospace at 1.6 line-height
- Chinese text: rendered by system fallback fonts in the stack

### Buttons

- Default: 4px border, 4px hard shadow, solid #ff004d background, white bold text
- Hover: reduced shadow, 2px translate offset (immediate)
- Active: no shadow, 4px translate (immediate)
- Focus: visible 3px blue outline with 2px offset
- Disabled: distinct background (#e8e8ec), muted text, no shadow

### Cards

- White background, 4px dark border, 4px hard shadow
- No nested cards — replaced with sections, separators, or flat subregions
- Interactive cards: immediate shadow/position change on hover
- Static informational cards: no decorative hover movement

### Notices

All notices use 4px solid dark border with distinct backgrounds:
- Warning: yellow background, dark text
- Error: red background, white text
- Success: green background, dark text
- Info: blue background, dark text
- Limitation: light surface background, dark left border

### Form controls

Streamlit form controls are globally restyled:
- Square corners, 4px dark borders, white backgrounds
- Blue focus outline with 2px offset
- No soft focus glow, no rounded dropdowns

## Information architecture

### Student View (6 pages)
1. Home — task summary, latest status, next action
2. Writing — submission form with grouped sections
3. Feedback — strengths, max 2 priorities, evidence, next step
4. Revision — draft chain, changes, priorities, uptake
5. Practice — target, exercise, attempt, evaluation
6. Learning Journey — chronological timeline events derived from authoritative
   source records; accurate classified empty states (learner not found, no
   submissions, analysis pending, gate-suppressed priority, no practice
   target, no attempt, no evaluation, no revision, no response observation);
   errors are never displayed as empty states

### Research View (6 pages)
1. Overview — system status, provider config, data quality
2. Evidence — submission, analysis, diagnosis audit
3. CALF Measures — grouped metric cards by construct
4. Learning Process — complete evidence chain
5. Research Data — export, privacy, filters, PII, review, splits, quality
6. System Audit — diagnostic, learner model, reanalysis, admin

## Progressive disclosure

- Student View hides internal IDs, analyzer versions, metric IDs, Evidence IDs,
  confidence calculations, Diagnostic Gate internals, database identifiers,
  configuration versions, provider error details.
- Research View exposes all technical records.

## Responsive design

- Desktop: 1280x900
- Mobile: 390x844
- At <=640px: border widths reduce to 2px, shadow offsets halve, font sizes
  decrease
- Hard-shadow offsets included in overflow calculations
- No unintended horizontal overflow

## Accessibility

- WCAG 2.1 AA text contrast
- Visible keyboard focus (3px blue outline)
- Semantic headings, descriptive labels
- No status communicated by color alone
- Readable Chinese typography
- prefers-reduced-motion respected
- No flashing, rapid animation, or unnecessary motion

## Internationalization

- 271 keys in en.json and zh_CN.json (identical sets)
- Language switcher in sidebar, immediate rerender
- No reanalysis or provider calls triggered by language switch

## CSS token location

Centralized in `app/ui/pixel_art.py` — `inject_pixel_art()` function.
Design token reference files archived at `docs/design/reference/pixel-art/`.
