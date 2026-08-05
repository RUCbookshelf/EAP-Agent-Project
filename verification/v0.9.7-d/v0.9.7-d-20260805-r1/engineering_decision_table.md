# v0.9.7-D D1.1 Engineering Feasibility Decision Table

**Source:** `kimi_proposal_a.md` (design consultation A, kimi-k3 via the
opencode-go channel). **Reviewer:** default engineering agent.
**Date:** 2026-08-05

Classification: ACCEPT / ADAPT / DEFER-D (later v0.9.7-D stage) /
DEFER-E (v0.9.7-E+) / REJECT. Stage column: D1 = token/document level,
WU2 = Journey implementation stage (D1.2), WU3 = critique/refinement
(D1.3).

| ID | Recommendation | Decision | Engineering reason | Stage |
|---|---|---|---|---|
| VD-01 | Calm-ledger concept | ACCEPT | Matches objective section 6; zero technical risk | D1 |
| VD-02 | Five design principles | ACCEPT | Adoption guidance for all following rules | D1 |
| VD-03 | Prohibited patterns | ACCEPT | Matches objective avoid-list; neon fills retired via C-03 | D1 |
| C-01 | `border-subtle` #8a8a9c | ACCEPT | Additive token; 3.39:1/3.08:1 >= 3:1 non-text guideline; used only for inner hairlines | D1 |
| C-02 | Action ranks + destructive reservation | ADAPT | Destructive token #a30d3d added but has no consumer yet (reserved); `#e00047` reservation enforced by re-pointing the shared Feedback priority-card title from action-red to ink | D1 |
| C-03 | Quiet semantic tints | ADAPT | Canonical `semantic.*` fills/on-* reassigned to tints/labels + new accent tokens; `selected`/`candidate` neon values retained (Research-only metric cards, out of scope); Research inherits token-level tint change, verified by smoke; guard tests updated to new pairs | D1 |
| C-04 | Product-state recipes | ACCEPT | Implemented via badge/notice/stage-item recipes on Journey | WU2 |
| C-05 | Never color alone | ACCEPT | Existing local SVG icon set + localized labels on every state surface | WU2 |
| TY-01 | Typography role tokens | ADAPT | Add `font-display`, card-title size, `weight-semibold`; page-title size keeps the existing h2 1.625rem/700 (spacing/scale guard tests untouched) | D1 |
| TY-02 | Mono-heading fix | ACCEPT | `--px-font-heading` re-pointed to sans display; mono retained for technical roles (`.px-badge`, `.px-mono`, code, metrics) | D1 |
| TY-03 | Readability rules | ACCEPT | 720px column already enforces <=75ch; no uppercase/justify/tracking added | D1 |
| TY-04 | Mono scope rule | ACCEPT | New status-badge label role is sans; mono only on Latin/digit technical strings | WU2 |
| SP-01 | Scale roles, token-only margins | ADAPT | Spacing values unchanged; shared primitives migrate inline margins to token classes (fixes S2) | WU2 |
| SP-02 | Control sizing | ACCEPT | Already `min-height` in CSS; 40/44px retained; wrap not clip | WU2 |
| SP-03 | Geometry reassignment | ADAPT | Radius 0 kept; 4px reserved for accent bars/focused panel/structural rules, 2px for cards/buttons/notices/inputs; shadows sm/md; icon-size tokens added | WU2 |
| SF-01 | Surface levels L0-L3 | ADAPT | New level CSS classes; `.px-card` becomes L2 (2px border + shadow-sm) | WU2 |
| SF-02 | Nesting rules | ACCEPT | Max L0->L2->L3; no nested shadows; one focused panel | WU2 |
| SF-03 | Context typing + Home steps | ADAPT | `student_context_block` gets L1 typing (all pages inherit); Home workflow-steps restyle is DEFER-D (Home is not the representative page) | WU2 + DEFER-D |
| ACT-01 | Rank recipes | ACCEPT | Journey actions secondary; page CTA stays primary | WU2 |
| ACT-02 | Action-row placement | ADAPT | Journey stage items hold exactly one action -> one full-width secondary button per item (Streamlit columns risk 390px overflow; existing matrix asserts no overflow); multi-button rows only on unchanged pages | WU2 |
| ACT-03 | One primary per view | ACCEPT | Enforced on Journey; K-04 check | WU2 |
| ST-01 | State matrix | ACCEPT | Badges + notices per matrix; wording frozen | WU2 |
| ST-02 | Loading/error unification | ADAPT | Journey loads with `loading_box` instead of `st.spinner`; Home/Practice spinner swap DEFER-D; error already distinguishes retryable/blocking by action presence - restyled only | WU2 + DEFER-D |
| ST-03 | Combination rules | ACCEPT | One badge per stage item; <=2 notices; no merged states | WU2 |
| CP-01 | Page header | ACCEPT | Existing `student_page_intro` restyled via token class | WU2 |
| CP-02 | Section header | ACCEPT | Existing `section_header` restyled (subtle 1px rule) | WU2 |
| CP-03 | Status badge | ACCEPT | `status_badge` gains icon + label + `data-state`; label role is sans; hybrid-component guard test updated to the new markup contract | WU2 |
| CP-04 | Action row | ADAPT | Pattern + CSS class documented; no unused component added (Journey items have <=1 action) | WU2 |
| CP-05 | Notice | ACCEPT | New `notice()` core with state variants; existing box functions become thin wrappers (guard tests unchanged) | WU2 |
| CP-06 | Empty state | ACCEPT | Existing `empty_state` restyled (quiet) | WU2 |
| CP-07 | Error state | ADAPT | `render_api_error` restyled; recoverable/blocking distinguished by action presence (already true) | WU2 |
| CP-08 | Metadata row | ACCEPT | `student_context_block` restyled as L1 + hairline rows | WU2 |
| CP-09 | Record reference | ACCEPT | `technical_caption` restyled; Journey replaces the leading-space raw-text trick (O2) with proper reference captions | WU2 |
| CP-10 | Cycle card | ACCEPT | New `.px-cycle-card` composition on Journey | WU2 |
| CP-11 | Stage item | ACCEPT | New `.px-stage-item` composition on Journey | WU2 |
| CP-12 | Practice state panel | ACCEPT | Stage-item variant with state-driven notice/badge per C-04 | WU2 |
| J-01 | Journey skeleton | ACCEPT | Frozen order preserved; cycle cards wrap existing renderers | WU2 |
| J-02 | Stage composition | ACCEPT | Badge top-right; <=2 metadata rows; record references; secondary actions | WU2 |
| J-03 | Variants | ADAPT | Empty/loading/error variants; collapsible cycles DEFER-D (default expanded) | WU2 + DEFER-D |
| BL-01 | Layout resilience | ACCEPT | min-height, wrap, no fixed widths; verified at 390px | WU2 |
| BL-02 | Text rules | ACCEPT | zh sans everywhere incl. badges; mono only on IDs | WU2 |
| K-01..K-05 | Acceptance checklist | ACCEPT | Adopted as D1.2/D1.3 verification plan; guard-test updates are explicit contract changes | WU2/WU3 |
| (subagent) | Remote serif fonts / Google Fonts | REJECT | Remote-resource prohibition; local/system stacks only | D1 |
| (subagent) | GSAP motion / animations | DEFER-E | Motion disabled by pixel identity; v0.9.7-E | D1 |
| (subagent) | Dark mode | DEFER-E | v0.9.7-E per register E1 | D1 |
| (subagent) | Kids/playful palette | REJECT | Conflicts with academic-credibility character | D1 |
| (proposal O1) | Copy touch for literal `?` strings | DEFER-D | Semantics-preserving; needs separate approval; not part of D1.2 | later |
| (register E1) | Full mobile redesign, accessibility remediation, Research UI | DEFER-E | v0.9.7-E+ | later |

## D1.1 acceptance check

1. Kimi/UI/UX Pro Max consultation occurred - PASS (kimi-k3,
   `kimi_proposal_a.md`, UI/UX Pro Max applied; routing adaptation
   documented).
2. Proposal is project-specific - PASS (grounded in real tokens/pages).
3. Tokens concrete and implementable - PASS (C-01..C-05 with values).
4. Component specifications concrete - PASS (CP-01..CP-12).
5. Journey composition specified - PASS (J-01..J-03).
6. Bilingual behavior addressed - PASS (BL-01/BL-02, TY-02, TY-04).
7. Remote resources excluded - PASS (constraint 2; REJECT row).
8. Product behavior unchanged - PASS (all wording/navigation/persistence
   contracts preserved; only presentation changes).
9. Every recommendation has an engineering disposition - PASS (table).
10. Deferred v0.9.7-E work explicit - PASS (DEFER-E rows + register E1).
11. Approved draft documented - PASS (`V0.9.7_D_STUDENT_DESIGN_SYSTEM.md`).
12. No broad page rollout begun - PASS (only Journey is the D1.2
    representative page).

**D1.1 gate: GREEN.**
