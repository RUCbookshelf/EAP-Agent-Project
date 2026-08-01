# Pixel Art Design System v0.9.2

> Status: superseded as the live implementation reference by
> **Hybrid Pixel System 2.0** (v0.9.4-A, see
> `docs/design/HYBRID_PIXEL_SYSTEM_2_0.md`). This document remains the
> historical v0.9.2 contract; v0.9.4-A preserves its identity rules (square
> corners, hard shadows, solid colors, no motion) while changing the body
> typography role and the primary action color (`#ff004d` → `#e00047`,
> measured 4.93:1).

This document is the authoritative design-system reference for the v0.9.2
Pixel Art UI. Implementation lives in `app/ui/pixel_art.py`; the centralized
CSS custom-property token system is injected by `inject_pixel_art()`.

## Canonical color palette

Limited solid-color palette. No gradients, no semi-transparent decorative
surfaces.

| Token | Hex | Semantic use |
|-------|-----|-------------|
| `--px-dark` | `#1a1c2c` | Borders, headings, major structural elements |
| `--px-white` | `#ffffff` | Main surfaces, card backgrounds |
| `--px-surface` | `#f4f4f4` | Secondary surfaces, sidebar |
| `--px-red` | `#ff004d` | Primary action, critical state |
| `--px-green` | `#00e436` | Confirmed, available state |
| `--px-blue` | `#29adff` | Information, focus, selected state |
| `--px-yellow` | `#ffec27` | Warning, pending, attention state |
| `--px-muted` | `#6b6b7b` | Secondary text (approved neutral 1) |
| `--px-disabled-bg` | `#e8e8ec` | Disabled backgrounds (approved neutral 2) |

## Borders

- Desktop primary: `4px solid #1a1c2c`
- Small mobile (<=640px): `2px solid #1a1c2c`
- Hairline (tables, separators only): `1px solid #1a1c2c`
- Primary components must not use 1px borders
- No decorative single-side accent borders

## Hard shadows

Hard offset shadows with no blur radius, no spread-based soft elevation,
no transparency:

- Small: `2px 2px 0 #1a1c2c`
- Medium: `4px 4px 0 #1a1c2c`
- Large: `8px 8px 0 #1a1c2c`

Shadow offsets are included in overflow calculations at all viewports.

## Radius and transitions

- Canonical radius: `0px` (square corners everywhere)
- Canonical transition: `none`
- No CSS animations, no opacity fades, no smooth movement
- State changes are immediate and hard
- `prefers-reduced-motion` explicitly disables any remaining movement

## Typography

Monospace stack (local/web-safe only; no downloaded font files):

`ui-monospace, Cascadia Mono, Cascadia Code, Consolas, SFMono-Regular, Menlo,
Monaco, Liberation Mono, Courier New, monospace`

- H1: 900 weight
- H2-H3: 700 weight
- Body: readable monospace, 1.6 line height
- Chinese text renders through system fallbacks; never force a Latin-only
  pixel font onto Chinese text

## Buttons

Primary buttons: solid `#ff004d` background, white bold text, square corners,
4px `#1a1c2c` border, 4px hard shadow.

- Default: 4px border, 4px hard shadow
- Hover: reduced hard shadow (2px), immediate 2px translate
- Active: no hard shadow, immediate 4px translate
- Focus: visible 3px blue (`#29adff`) outline, 2px offset
- Disabled: `#e8e8ec` background, muted text, no shadow, not opacity-only

Secondary: `#f4f4f4` background, dark text. Destructive: dark background,
white text. All square, all immediate.

## Cards

- White or approved solid background
- Square corners, 4px dark border, 4px hard shadow
- No nested cards (replaced with sections, separators, flat subregions)
- Interactive cards: immediate shadow/position change on hover
- Static informational cards: no decorative hover movement

## Notices

All notices: 4px solid dark border, square corners.

- Warning: yellow background, dark text
- Error: red background, white text
- Success: green background, dark text
- Info: blue background, dark text
- Limitation: light surface background, dark text

## Form controls

Streamlit form controls globally restyled: square corners, 4px dark borders,
white backgrounds, dark text, blue focus outline with 2px offset. No soft
focus glow, no rounded dropdown surfaces. Native accessibility and keyboard
behavior preserved.

## Status badges

Solid-color square badges with thick border. Never rely on color alone;
badges carry text labels. Status color mapping:

- Success states: green
- Warning/pending/candidate: yellow
- Error/unavailable/blocked: red
- Neutral/other: blue

## Responsive

At widths <= 640px: border widths reduce to 2px, shadow offsets halve, font
sizes scale down. Layout stacks vertically; no horizontal overflow;
hard-shadow offsets included in overflow calculations.

## Known framework-controlled exceptions

Streamlit generates its own internal widget DOM. Some internal elements
(e.g., popover menus, tooltip internals, data-frame internals) may retain
framework-controlled styling that cannot be fully overridden. These are
documented in `docs/KNOWN_LIMITATIONS.md` and are not treated as
application-owned style violations.
