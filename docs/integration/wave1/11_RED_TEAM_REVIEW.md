# 11 — Fresh Cross-Department Red Team Review

**Gate:** WU13 GREEN — 2026-08-08
**Office:** Architecture & Integration (Wave-1 Integration Gate)

## 1. Reviewer

Fresh independent DeepSeek reviewer instance (Noether) that did not perform the implementation or integration work; dispatched with a read-only task packet (`.agent-workflow/wave1-integration/task-packets/wu13-red-team-packet.md`) covering all 12 checklist areas of Goal section 18. No repository writes by the reviewer.

## 2. Verdict

**GREEN-ABLE — no BLOCKING or HIGH findings.** One MEDIUM (F-01) resolved at this gate; five findings total, dispositions below.

## 3. Findings and dispositions

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| F-01 | MEDIUM | WU14 handoff deliverable not yet committed when reviewed | RESOLVED at this gate — all Wave-1 deliverables committed; `git status --short` clean afterwards (only noncanonical `.agent-workflow/` untracked) |
| F-02 | LOW | `derive_domain(surface)` ignores its argument; `WORKFLOW_SURFACE_DOMAIN` not consulted by derivation | DOCUMENTED WITH OWNER — Shared Platform & Core; contract test pins all current surfaces to `l2` and no `academic` surface; wiring required only when a second workflow surface exists (D-21 seam), same trigger as migration 14 |
| F-03 | LOW | D-31 invariants 2-4 satisfied at mechanism/contract level only (no production callers of `validate_domain_scope`/`same_domain`) | DOCUMENTED WITH OWNER — consistent with recorded SAFE_TO_DEFER (07 §4); enforcement becomes live under the migration-14 trigger; tracked in `12_NEXT_WAVE_HANDOFF.md` |
| F-04 | LOW | `CitationVerificationRecord.rule_id` set to whole-manifest version instead of per-rule id | DOCUMENTED WITH OWNER — Academic Writing department (D-32 granularity follow-up before Academic persistence wave) |
| F-05 | LOW | Isolation AST contract did not cover `app/api`, `app/ui`, `app/infrastructure`, `app/repositories` | FIXED at this gate — `L2_CONSUMER_TREES` extended to 16 trees; `tests/contracts` 43/43 pass; no academic references found in the added trees |

## 4. What the reviewer independently confirmed clean

- Migration 13 authoritative; no migration 14; no domain-column SQL.
- Corpus Stage-5 artifacts, locales, `run.bat`, requirements untouched since `b171cce`.
- No sync-conflict files under `app/` (D-27 drift check).
- No `app.academic` imports anywhere outside `app/academic`; `app/academic` imports nothing from the rest of the app.
- No academic route/UI/composition-root registration; no academic domain pack; advisory `academic` rejected.
- Shared vocabularies frozen with banned labels enforced; additive-only API snapshot diffs.
- Integration-owned changes (manifest registrations, parity allowlist, contract tests) minimal, additive, not feature development.

## 5. Post-fix re-review

Material integration changes after the review: F-05 test extension + final deliverable commits (docs 00/11/12). The changes are test-only and documentation-only; the reviewer's code-level conclusions remain unaffected. No new BLOCKING/HIGH finding arises from test-only extensions and deliverable commits.

## 6. Gate statement

**WU13 GREEN** — no unresolved BLOCKING/HIGH finding; MEDIUM resolved; LOWs fixed or documented with owners.
