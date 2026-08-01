# v0.9.4-B Student Experience Redesign Verification

**Date:** 2026-08-01
**Run ID:** `v0.9.4-b-20260801-r1`
**Result:** PASS, with one pre-existing backend limitation recorded below
**Implementation commit:** `284378e` (`feat(v0.9.4-b): redesign student experience`)

## Scope and isolation

Verification covered only the six Student pages: Home, Writing, Feedback,
Practice, Revision, and Learning Journey. Research pages received smoke checks
only. No v0.9.4-C/D, v1.0, corpus, machine-learning, external-provider, or
pilot work was started.

All stateful verification used
`verification/v0.9.4-b/v0.9.4-b-20260801-r1/isolated/writing_feedback_v094b.db`
and `LLM_PROVIDER=local`. Migration 12, `config-v0.9.0`, API schemas, domain
semantics, and the read-time Journey projection remained unchanged. The
isolated database was removed after verification.

## Static and automated gates

- Python compile: PASS for `app`, `scripts`, and `tests`.
- Static audit: PASS across 14 AST-parsed files; imports clean; 520/520 locale
  key parity; no mojibake markers, remote assets, page-local token declarations,
  page-local color literals, or new direct Student application literals.
- Pixel Art style audit: PASS, 0 violations.
- Design-system audit: PASS. Focus is 3px `#0f6dbd`; measured contrast is
  5.33:1 on white, 4.84:1 on the surface, and 3.16:1 on the dark boundary.
- Affected tests: 95 passed, 1 skipped.
- Broader Student regression: 130 passed, 2 skipped.
- Core pytest excluding externally managed live tests: 421 passed, 8 skipped,
  3 non-failing pre-existing dependency/OpenAPI warnings.

## Page and flow verification

Each focused page slice passed English desktop and Chinese mobile checks,
including clean console/page-error state, no horizontal overflow, localized
copy, stable learner context, field-local validation, idempotency, API-outage
handling, and zero writes from render/navigation/locale/refresh.

- Home: purpose, three-step orientation, one state-based action, no dashboard
  count wall.
- Writing: prompt/essay validation, exactly one valid submission, saved-state
  lock, and a Feedback next action.
- Feedback: selected priority first, evidence/strength/limit structure,
  zero-priority state, learner validation, and no provider detail in the lead.
- Practice: one target/exercise, invalid response zero-write, one authoritative
  attempt/evaluation, saved-state lock, and bilingual instructions.
- Revision: one eligible source, matching target, original context, one linked
  revision, saved-state lock, and one conservative response observation.
- Learning Journey: 12-event demo and 48-event S02 timelines with separate
  time/source/evidence/limit fields, stable ordering/deduplication, and no
  render writes.

The controlled cross-page flow used one synthetic learner and one write set.
Final counts were: 2 essays, 1 initial submission, 1 revision, 1 selected
priority, 1 target, 1 exercise, 1 attempt, 1 evaluation, 1 revision group,
1 revision snapshot, 1 response observation, and 0 engagement traces. The
Journey contained 12 stable events; locale switches, refresh, and learner
switching created no duplicates or stale learner state.

## Browser matrices

Playwright was used because the Browser plugin was unavailable.

- Legacy v0.9 suite: 6/6 checks PASS.
- Legacy v0.9.2.1 suite: PASS for all four 12-page combinations (English
  desktop, Chinese desktop, English mobile, Chinese mobile), focus/computed
  styles, role separation, rerun idempotency, and 13 screenshots.
- Required Student matrix: 24/24 renders PASS (6 pages x English/Chinese x
  desktop/mobile), supplied by the four-combination suite and corroborated by
  the six focused page slices.
- Required Research smoke subset: 6/6 PASS (Research Overview, Research Data,
  System Audit x English desktop/Chinese mobile). Research IA was unchanged.
- Browser checks found no Streamlit exceptions, unexpected console/page
  errors, raw locale keys, or horizontal overflow.

The local image-reader tool could not independently open the preserved PNGs
because its Windows sandbox helper returned `helper_unknown_error`. This does
not replace or weaken the recorded browser DOM, computed-style, accessibility,
and screenshot-generation checks, but it is an explicit visual-QA tooling
limitation for this run.

## Lifecycle and launcher

Lifecycle verification passed: `/live`, `/ready`, `/health`, `/docs`,
`/openapi.json`, Streamlit cold start, API warm restart, Student Practice
API-down classified error without `stException`, recovery, and process/port
cleanup. Health reported migration 12.

The exact final launcher command passed:

```bat
cmd /c "run.bat --verify"
```

It ran with the isolated database and local provider, confirmed all dependencies
already satisfied, migration 12, 33 tables, prompt
`feedback-prompt-v0.7.1`, `config-v0.9.0`, and 200 responses for health, docs,
and Streamlit.

## Known limitation discovered

The pre-existing `_next_practice_id` implementation slices three-character
`WTR` identifiers with `SUBSTR(response_id, 3)`. A second within-task response
can therefore collide with the first identifier. This is a backend persistence
bug outside the authorized Student presentation scope and was not fixed.
The controlled isolated fixture removed one copied demo response before the
single authoritative save; the source database was never modified. A future
backend task should repair the ID allocator and add a multi-response regression
test.

## Commit and preservation contract

The implementation and verification are split into exactly two commits. The
pre-existing user-owned paths `AGENTS.md`, `.claude/`, `CLAUDE.md`,
`RUN_VERIFICATION_V0.7.md`, and `data/demo_journey_manifest.json` are excluded
from both commits. Temporary probes, logs, caches, and the isolated database
are excluded from the verification commit.
