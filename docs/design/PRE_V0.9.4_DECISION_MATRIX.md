# Pre-v0.9.4 Decision Matrix and Recommendation

**Date:** 2026-08-01
**Status:** decision support only. No direction approved; nothing implemented.

## Comparison matrix

Scale: 1 (poor) – 5 (excellent); effort/risk: 1 (low) – 5 (high).

| Criterion | A Refined Pixel Art | B Hybrid Pixel 2.0 | C Full Redesign | Evidence basis |
|---|---|---|---|---|
| Usability improvement | 3 | 5 | 4 | audit findings: validation gap, loading, JSON output |
| Visual distinctiveness | 5 | 5 | 2 | brand docs; product identity |
| Student suitability | 3 | 5 | 4 | readability (monospace vs sans), feedback focus |
| Researcher suitability | 3 | 5 | 4 | JSON → tables, density, Swiss grid |
| Accessibility | 4 | 5 | 4 | measured contrast/touch fixes |
| Implementation difficulty | 2 | 3 | 5 | CSS/components only vs full replacement |
| Streamlit compatibility | 5 | 4 | 2 | pixel CSS overrides work; conventional styling fights framework |
| Regression risk | 1 | 2 | 5 | scope of surface change |
| Maintenance cost | 2 | 3 | 3 | two role scopes need governance |
| Migration effort | 1 | 3 | 5 | page/component counts |
| Compatibility with current UI | 5 | 4 | 1 | token/component reuse |
| Compatibility with v0.9.3-C | 5 | 5 | 3 | v0.9.3-C is behavior-scoped; design direction orthogonal but C touches everything |
| Long-term research-product suitability | 3 | 5 | 4 | academic/audit audience needs dense, readable analysis UI |

## Recommendation: Direction B — Hybrid Pixel System 2.0

**Reasons (each tied to evidence):**

1. **It fixes the two largest measured problems.** The audit found readability
   (monospace body + 3.92:1 primary contrast) and research scanability (raw
   JSON everywhere) as the dominant issues. B addresses both: readable sans
   body for Student reading, dense Swiss-style tables for Research.
2. **It preserves the brand that was deliberately built and verified.**
   v0.9.2/v0.9.2.1 invested in the pixel identity; C discards it; A keeps it
   but leaves the readability problem unsolved. B keeps the identity with a
   controlled role split.
3. **It matches the product's two audiences.** ui-ux-pro-max product evidence
   points to approachable learning UI for the student side and
   analytical/minimal dashboard treatment for the research side; B is the only
   direction that differentiates by role rather than forcing one language.
4. **It is the best fit for the research purpose.** Researchers need dense,
   comparable, auditable views; the Swiss-style grid + tables serve that while
   Student stays task-focused.
5. **Streamlit feasibility is high.** Both languages are CSS/component-layer
   changes inside the existing injection architecture; no backend, API,
   migration, or behavior change is required.
6. **It is not the most dramatic option.** C is the most dramatic and the
   most risky; the recommendation is deliberately the moderate, evidence-first
   choice.

**Constraint changes B requires (to be approved by the user before any
implementation):**

- allow a readable sans body font (monospace retained for headings/data/IDs);
- darken the primary red for AA contrast;
- allow bounded 80–150ms motion with a `prefers-reduced-motion` guard;
- add role-scoped semantic tokens (shared primitives stay identical);
- add one SVG icon family;
- replace research `st.json` output with the existing table component.

**Decisions required from the user:**

1. Approve Direction B, or select A/C; or request a hybrid variation.
2. If B: approve the shared token contract and the role-scoped semantic layers.
3. Approve the brand-adjacent relaxations (sans body type, darkened red,
   bounded motion) as explicit design decisions — none are implemented here.
4. Decide scope/priority of a future implementation (validation gap and AA
   contrast are P0; JSON → tables and loading states are P1).
5. Confirm whether the two hardcoded Chinese-mode strings (Target ID,
   "Export:") should be fixed in a small localization change separate from any
   design direction.
6. Confirm v0.9.3-C remains separate and unimplemented.

## What would change the recommendation

- A strong product decision that the pixel identity itself must go → C.
- A constraint that monospace body text is a non-negotiable brand rule → A.
- User feedback that the two-language system is too complex to govern → A.
