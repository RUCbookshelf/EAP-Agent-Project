# Pre-v0.9.4 Design Token Options

**Date:** 2026-08-01
**Status:** proposals only. No production token file was modified.

Current token source of truth: `app/ui/pixel_art.py` CSS custom properties +
`docs/design/reference/pixel-art/pixel-art-tokens.json`.

## Shared global tokens (all directions)

These stay stable regardless of direction:

| Token | Value |
|---|---|
| Background | `#ffffff` |
| Surface | `#f4f4f4` |
| Elevated surface | `#ffffff` + hard shadow (no blur) |
| Primary text | `#1a1c2c` |
| Secondary text | `#6b6b7b` |
| Success | `#00e436` (text `#1a1c2c`) |
| Warning | `#ffec27` (text `#1a1c2c`) |
| Error | red, text white — value per direction (A/B darken to `#d4003f`) |
| Information | `#29adff` (text `#1a1c2c`) |
| Unavailable | surface bg + muted text |
| Candidate | yellow (same as warning) |
| Insufficient evidence | muted text + surface bg |
| Border widths | 4px primary / 2px <=640px / 1px table hairlines |
| Shadow offsets | 2/4/8px hard, `#1a1c2c`, no blur |
| Spacing scale | 4/8/12/16/24/32/48 |
| Breakpoints | 640 / 1024 (mobile-first; targets 390 and 1280) |
| Focus outline | 3px `#29adff`, 2px offset |
| Radius | `0px` (A and B); C may use 8–12px |
| Motion | none (A); 80–150ms with reduced-motion guard (B); 150–200ms (C) |

## Direction A — Refined Pixel Art tokens

### Shared

| Token | Value |
|---|---|
| Primary action bg | `#d4003f` (AA-safe red) |
| Primary action text | `#ffffff` |
| Secondary action bg | `#f4f4f4`, text `#1a1c2c` |
| Destructive bg | `#1a1c2c`, text `#ffffff` |
| Disabled bg | `#e8e8ec`, text `#5a5a68` |

### Typography (shared)

| Token | Value |
|---|---|
| Font family | monospace stack (unchanged) |
| H1 | 32px/900 |
| H2 | 26px/900 |
| H3 | 20px/700 |
| Body | 16px/400, line-height 1.6 |
| Data/label | 13px tabular |

### Layout

| Token | Value |
|---|---|
| Max content width | 1080px (Research), 760px (Student reading) |
| Card padding | 16px |
| Section gap | 32px |

### Icon / table

| Token | Value |
|---|---|
| Icon size | 16/20/24px, 2px stroke, square caps |
| Table density | 13px, 8px cell padding, sticky header |

### Role-scoped (A)

| Scope | Token | Value |
|---|---|---|
| Student | Accent emphasis | red primary, yellow encouragement badges |
| Research | Accent emphasis | blue primary actions, dense tables |

## Direction B — Hybrid Pixel System 2.0 tokens

### Shared base (as above) plus:

| Token | Value |
|---|---|
| Font family body | Inter / Atkinson Hyperlegible (Student), Inter (Research) |
| Font family data | monospace tabular |
| H1 | 30px/800 (Student) / 24px/700 (Research) |
| H2 | 24px/800 / 20px/700 |
| H3 | 19px/700 / 16px/700 |
| Body | 16px/1.6 / 14px/1.5 |
| Max content width | 720px (Student column) / 1200px (Research grid) |
| Card padding | 20px / 12px |
| Section gap | 40px / 16px |
| Table density | — / 13px, 6px cell padding |

### Student-specific semantic tokens

| Token | Value |
|---|---|
| Primary action | red `#d4003f`, white text |
| Encouragement accent | yellow `#ffec27` for progress/celebration |
| Illustration palette | dark + red + yellow + green (pixel figures) |
| Spacing rhythm | 24–48px sections |

### Research-specific semantic tokens

| Token | Value |
|---|---|
| Primary action | blue `#29adff` with dark text (or dark bg for AA) |
| Brand accent | blue; status colors remain semantic |
| Grid | 12 columns, 8px base gap |
| Density | 8–16px spacing rhythm |
| Table density | 13px, 6px cell padding, sticky header, zebra rows |

## Direction C — Full Professional Redesign tokens

### Shared (conventional SaaS)

| Token | Value |
|---|---|
| Primary | `#0D9488` (LMS teal) or `#1E3A5F` (academic navy) |
| Accent | `#D97706` (amber) or `#B45309` (citation gold) |
| Background | `#F0FDFA` / `#F8FAFC` |
| Surface | `#ffffff` |
| Elevated surface | `#ffffff` + soft shadow (8px blur, 12–16px radius) |
| Text | `#134E4A` / `#0F172A` |
| Muted | `#64748B` |
| Error | `#DC2626` |
| Radius | 8px (cards), 12px (modals), 20px (buttons) |
| Shadow | soft 2-tier elevation |
| Motion | 150–200ms, reduced-motion guard |
| Typography | Inter or Atkinson Hyperlegible 16px/1.6; serif option for
  scholarly headings (Crimson Pro) |
| Max content width | 1200px |
| Breakpoints | 375/768/1024/1440 |
| Focus outline | 2px primary + 2px offset |
| Icon size | 16/20/24px Lucide/Phosphor |
| Table density | 14px, 8px padding |

## Token governance note

- A keeps one component set and only fixes values.
- B introduces two role-scoped semantic layers on top of shared primitives —
  this requires a documented token contract (shared → role → component) and a
  style audit script to prevent drift.
- C replaces the token system entirely and invalidates the existing pixel
  reference files and verification tooling.

No production token file was modified by this study.
