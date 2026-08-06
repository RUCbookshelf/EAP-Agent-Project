# v0.9.7-D Design-System Freeze Verification Report

**Status:** COMPLETE - the Student design system is FROZEN and validated
on the Journey representative page (see section 14 for the final
decision and the Kimi final verdict).
**Date:** 2026-08-06
**Governing protocol:** the owner-provided v0.9.7-D objective
(MCU D1.0..D1.3) and `docs/development/V0.9.7_D_STUDENT_DESIGN_SYSTEM.md`.

## 1. Starting and ending HEAD

- Starting HEAD: `6a2e927` (v0.9.7-C closure), branch `master`.
- Ending HEAD: recorded in section 13.

## 2. Model routing evidence

- Primary engineering agent: default model (repository inspection, Git,
  implementation, tests, verification, documentation).
- Design consultations A/B/C (mandatory kimi assignments): routed to
  **kimi-k3 via the `opencode-go/kimi-k3` channel** with the UI/UX Pro Max
  skill attached to every brief.
- Routing adaptation (recorded): the objective specified `kimi/k3[1m]`;
  that provider entry is OAuth-mode and the upstream returned 402
  ("unable to verify membership benefits") on direct probes; the
  key-authenticated `opencode-go/kimi-k3` channel was verified working
  (direct probe 200) and used for all three consultations. The moonshot
  kimi entry's stored key returned 401 on probe. No other routing change
  was made.

## 3. Kimi consultation summaries

- **A (proposal)**: `verification/v0.9.7-d/v0.9.7-d-20260805-r1/
  kimi_proposal_a.md` - "Calm ledger" direction, semantic quiet-state
  tokens, typography roles (sans headings), surface levels, action ranks,
  12-state matrix, 12 component specs, Journey composition, bilingual
  rules, acceptance checklist (VD/C/TY/SP/SF/ACT/ST/CP/J/BL/K IDs).
- **B (first-implementation critique)**: `kimi_critique_b.md` -
  FIX-BEFORE-FREEZE; 4 BLOCKING (invalid border composites, state-label
  colors, transient loading, evidence gaps), 4 HIGH-VALUE, 4 OPTIONAL,
  1 REJECT, 2 DEFER-E.
- **C (final consistency review)**: `kimi_review_c.md` (NOT READY,
  RC-01..RC-12), `kimi_review_c2.md` (NOT READY, RC2-01..RC2-10),
  `kimi_review_c3.md` (final verdict - see section 14).

## 4. UI/UX Pro Max outputs used

The design subagents applied the UI/UX Pro Max skill
(`C:\Users\16073\.agents\skills\ui-ux-pro-max\SKILL.md`): design-system
workflow runs, accessibility/touch/typography/color rule sets, and the
`--domain ux` validation pass. The kids-palette output was rejected
against the desired character; the institutional-minimal direction was
adapted to the frozen local stacks and pixel identity (remote fonts,
motion, dark mode declined/deferred).

## 5. Recommendation decision table

`verification/v0.9.7-d/v0.9.7-d-20260805-r1/engineering_decision_table.md`
- every proposal ID has an engineering disposition (ACCEPT/ADAPT/
DEFER-D/DEFER-E/REJECT); the critique findings KB-01..KB-14 and
review findings RC-01..RC-12, RC2-01..RC2-10 carry their resolutions in
`kimi_critique_b.md`, `kimi_review_c.md`, `kimi_review_c2.md`,
`kimi_review_c3.md`, and the design-system document revision log.

## 6. Implemented tokens and components

- Tokens (canonical `app/ui/pixel_art.py::DESIGN_TOKENS`): added
  `border-subtle`, `destructive`; quiet semantic tint fills/on-* pairs
  and new `accent-*` tokens; `font-display` role (headings re-pointed to
  sans), card-title size, semibold weight; icon-size tokens; 2px/1px
  border roles; mobile 2px bar scale.
- CSS: quiet notice recipes (tint + 4px/2px accent bar + icon),
  `span.px-status-badge` state families, L2/L3 container recipes scoped
  to widget-keyed classes, page/section heading classes, hardened
  `.px-divider`, button-label color pinning, radio selection emphasis.
- Components (`app/ui/components.py`): `notice()` core with state
  variants (box functions remain wrappers), `status_badge_html` +
  redesigned `status_badge` (icon + label, `data-state`), `neutral_box`
  (dashed unavailable/legacy), class-based page/section headers,
  transient loading placeholder wiring.

## 7. Journey changes

`app/ui/features/student/journey.py`: cycle cards (L2) with header row
(title + `cycle-{id}` reference + cycle-stage badge); L3 stage items for
submissions (original/revision), feedback stages, and Practice panels;
status badges on every stage; record references replace the leading-space
raw-text trick; dashed neutral notices for legacy/unresolved provenance
and evaluation unavailable; secondary record actions; unified transient
loading box; frozen order, wording, button keys, navigation, and
zero-write behavior preserved.

## 8. Tests

- New: `tests/test_v097d_design_system.py` (23 tests: tokens, shared
  components, Journey structure/status variants/action hierarchy/empty/
  error, contracts, locale, no remote resources, no page-specific CSS,
  zero writes, R2 gate fixes).
- Updated guard tests: `test_design_tokens_v094a.py` (new token
  inventory, semantic values, accent/border contrast pairs, heading
  role, testid mappings), `test_hybrid_components_v094a.py` (badge
  markup contract).
- Affected regression: 419 passed / 1 skipped at D1.2; refined suites
  134+ passed / 0 failed; focused v0.9.7-D suite green at every gate.
- Full non-live core (canonical env, 33-entry allowlist,
  `--ignore=tests/live`): **1158 passed / 8 skipped / 0 failed / exit 0**
  (log: `C:\tmp\d12-fullcore\full_core_output.txt`).
- Launcher: not rerun - no launcher/environment/startup code change
  (decision recorded per the stage verification strategy).
- Static: `compileall` OK; `scripts/design_system_audit_v094a.py` PASS;
  `scripts/pixel_art_style_audit.py` PASS; `git diff --check` clean on
  all v0.9.7-D files (the pre-existing user-owned `AGENTS.md` trailing
  whitespace is preserved and not staged).

## 9. Rendered combinations

`verification/v0.9.7-d/v0.9.7-d-20260805-r1/d1_browser_matrix.py` +
`rendered_page_matrix_evidence.json`: en/zh x 1280x900/390x844 with a
real production stack (local provider, isolated DB, two seeded cycles per
learner). Every combination: 2 cycle cards (only keyed containers
framed), 12 stage items, badge states success/info/neutral, sans page
title (computed), white primary-CTA labels (computed), dashed legacy
notice (computed), 4px/2px page-title rule, main column 720px max-width,
0 exceptions, 0 console/page errors, 0 remote requests, 0 overflow,
0 raw keys, 0 forbidden claims, mobile targets >= 44px, whole-DB zero
writes, bottom and mid captures byte-distinct.

## 10. Screenshots

`verification/v0.9.7-d/v0.9.7-d-20260805-r1/screenshots/`:
`{en,zh}_{1280x900,390x844}_journey_{design_system,bottom,mid}.png`
(12 captures) plus the before references under
`verification/v0.9.7-c/v0.9.7-c-wu4-20260805-r1/screenshots/`.

## 11. Before/after findings

- Before: flat block stack, mono headings (zh crowding), neon full-bleed
  notices, plain-text state rows, full-width ambiguous record buttons,
  mixed inline spacing, no visible cycle grouping.
- After: bordered cycle cards with header/badge, quiet tint states with
  icon+label, sans headings both locales, dashed unavailable/legacy
  channels, secondary record actions, token-only spacing, transient
  loading, consistent surfaces; measured AA pairs on all state labels
  and white-on-red primary CTA restored.

## 12. Deferred issues

DEFER-D (later v0.9.7-D stages): Home workflow-step restyle and
Home/Practice spinner unification, collapsible Journey cycles, O1 copy
touch, KB-09 mono learner-ID role, mobile type-scale half of KB-13.
DEFER-E (v0.9.7-E+): full mobile redesign, dark mode, animation,
illustration/branding assets, full accessibility remediation, Research
UI. No migration, no new dependency, no API/backend/domain change.

## 13. Commits

1. `f70c553` docs(v0.9.7-d): define and approve Student design direction
   (D1.1)
2. `a256639` feat(v0.9.7-d): add shared Student design foundations
   (tokens, CSS, components)
3. `ed057bd` feat(v0.9.7-d): apply design system to Journey reference
   page
4. `2b68aa1` test(v0.9.7-d): verify Journey design-system implementation
   (focused tests + rendered matrix)
5. `94b0758` fix(v0.9.7-d): refine representative UI from Kimi design
   review (KB-01..KB-14)
6. `e6cbc37` fix(v0.9.7-d): scope surface hooks to keyed containers and
   capture honest below-fold evidence (RC-01, RC-02)
7. `992363d` fix(v0.9.7-d): resolve re-review gates RC2-01..RC2-03 and
   reconcile docs RC2-04..RC2-08
8. docs(v0.9.7-d): freeze Student design system (closure; hash in
   section 13/14)

Ending HEAD: recorded with the closure commit.

## 14. Final freeze decision

- Final Kimi verdict (`kimi_review_c3.md`): **READY WITH DOCUMENTED
  LIMITATIONS** - all gates RC2-01..RC2-03 pixel-verified resolved,
  RC2-04..RC2-10 resolved, rollout ready for the Writing slice per
  design-system section 19.
- Remaining items RC3-01..RC3-05 resolved in this freeze closure:
  RC3-01/02 (section 5 shadow and 4px-border lists corrected to match
  implementation), RC3-03 (rendered field-error assertion added to
  `test_v097d_design_system.py`; computed-color verification carried by
  the Writing rollout slice), RC3-04 (cycle-card gap wording corrected),
  RC3-05 (computed-style evidence persisted in
  `rendered_page_matrix_evidence.json`).
- The design system is declared **FROZEN - validated on Student Journey
  representative page** (`docs/development/V0.9.7_D_STUDENT_DESIGN_SYSTEM.md`).
- Ending HEAD: the closure commit `docs(v0.9.7-d): freeze Student design
  system` (exact hash recorded in the final chat report).
- Final `git status --short` after the closure commit: only the preserved
  user-owned entries remain (modified `AGENTS.md`,
  `RUN_VERIFICATION_V0.7.md`, `RUN_VERIFICATION_V0.8.2.md`; untracked
  `.claude/`, `CLAUDE.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
  `data/demo_journey_manifest.json`, pre-existing v0.9.7-a run logs).

> **The v0.9.7-D Student design system is frozen and validated on the
> Journey representative page. It is ready for controlled rollout across
> Writing, Feedback, Revision, and Practice in the next v0.9.7-D stage.**

## 15. User-owned files

`AGENTS.md`, `.claude/`, `CLAUDE.md`, `RUN_VERIFICATION_V0.7.md`,
`RUN_VERIFICATION_V0.8.2.md`, `ARCHITECTURE_COUPLING_AUDIT_V0.9.5_A.md`,
and `data/demo_journey_manifest.json` were never modified, staged,
committed, or deleted. Final `git status --short` in section 14.
