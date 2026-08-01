# RUN VERIFICATION v0.9.3 (integrated A + B + C)

Date: 2026-08-01
Version: v0.9.3 — runtime reliability, research API integrity, product journey
hardening

Implementation commits: d128734, 2fd768f (A), 5154749 (B), v0.9.3-C
implementation commit (see Git log); verification commits f03dcbb (A),
f4aa30c (B), v0.9.3-C verification commit (see Git log).

## 1. Integrated acceptance evidence (rerun in this closure)

| # | Check | Result |
|---|---|---|
| 1 | Full core pytest suite | 324 passed, 8 skipped |
| 2 | Cases A-R | 110 passed |
| 3 | Live/browser suites (legacy + v0.9.3-C) | 6/6 PASS; 3/3 PASS (13 screenshots); journey browser verification PASS |
| 4 | Pixel Art static style audit | PASS (0 violations) |
| 5 | Lifecycle /live, /ready, /health | 200 / 200 (ready=true) / 200 (migration 12) |
| 5 | Startup + degraded + API recovery | PASS (v0.9.3-A tests; recovery_check PASS) |
| 6 | Three clean cold starts (run.bat --verify) | PASS x3 |
| 7 | One warm restart | ready in 1.88 s |
| 8 | All eight repaired Research endpoints | PASS (v0.9.3-B matrix + tests) |
| 9 | All eight Research Data subsections | PASS (desktop + 390x844, EN/ZH) |
| 10 | Canonical error-taxonomy scenarios | PASS |
| 11 | Timeout profiles | PASS (connect 2s / read 10s / write 30s / long-read 60s) |
| 12 | GET-only retry policy | PASS |
| 13 | No automatic write retry | PASS (browser + unit evidence) |
| 14 | Request-ID propagation | PASS (headers + error bodies + logs) |
| 15 | Sanitized logging | PASS (request metadata only; credential scan clean) |
| 16 | Deterministic demo setup | PASS (DEMO-001 manifest) |
| 17 | Complete Student journey | PASS (submission -> feedback -> practice -> revision -> Journey) |
| 18 | Complete Researcher journey | PASS (Overview -> Evidence -> CALF -> Learning Process -> Data -> Audit) |
| 19 | Learning Journey complete state | PASS (DEMO-001: journey_events with full chain) |
| 20 | Learning Journey empty states | PASS (taxonomy states verified) |
| 21 | Journey ordering and deduplication | PASS (stage-aware sort; unique dedup keys) |
| 22 | Practice and revision idempotency | PASS (1 -> 1 instances; no duplicate attempts/revisions) |
| 23 | S02 direct regression | PASS (HTTP 200, 16 ms, request id fa679e6f118f44d1, events rendered, no generic error) |
| 24 | S01 Journey retrieval | PASS (accurate learner-not-found state) |
| 25 | Nonexistent learner (S999) | PASS (accurate learner-not-found state) |
| 26 | English desktop 1280x900 | PASS |
| 27 | Chinese desktop 1280x900 | PASS |
| 28 | English 390x844 | PASS |
| 29 | Chinese 390x844 | PASS |
| 30 | Browser console errors | 0 |
| 31 | Page exceptions | 0 |
| 32 | Horizontal overflow | 0 |
| 33 | Focus visibility | PASS (3px blue outline, 2px offset) |
| 34 | Localization parity | PASS (368 keys en == zh_CN) |
| 35 | Raw localization-key check | PASS (0 raw keys in verified flows) |
| 36 | `cmd /c "run.bat --verify"` | PASS |
| 37 | FastAPI HTTP status | 200 |
| 38 | API docs HTTP status | 200 |
| 39 | Streamlit HTTP status | 200 |
| 40 | Migration version | 12 (unchanged) |
| 41 | Active configuration | config-v0.9.0 (unchanged) |
| 42 | Credential scan | PASS |
| 43 | Sensitive-file scan | PASS |
| 44 | Documentation tracking | PASS (reports + doc updates committed) |
| 45 | Final `git status --short` | see report; only intended tracked work + preserved user-owned changes |

## 2. v0.9.3 release state

- REL-001, ERR-001, ERR-002, PERF-001 (A/B) closed; UX-001, DATA-001, UX-002,
  UX-003, ERR-003 (C) closed.
- Learning Journey now renders real, source-backed events; empty states are
  accurate; the deterministic demo journey is repeatable and idempotent;
  cleanup is scoped to demo records.
- No mastery, acquisition, learning-gain, causal, transfer, proficiency, or
  CEFR claim exists anywhere in the journey output.
- v0.9.4 UI implementation has NOT started; v1.0 corpus work has NOT started.

## 3. Preserved user-owned changes

`AGENTS.md` (modified), `.claude/` and `CLAUDE.md` (untracked) were present
before this goal and are preserved untouched outside the implementation and
verification commits.
