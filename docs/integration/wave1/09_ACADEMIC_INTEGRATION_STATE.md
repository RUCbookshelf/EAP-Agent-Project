# 09 — Academic Integration State

**Gate:** WU11 GREEN — 2026-08-08
**Office:** Architecture & Integration (Wave-1 Integration Gate)

## 1. Explicit distinction

```text
ACADEMIC FOUNDATION INTEGRATED  ==  true  (this Wave)
ACADEMIC PRODUCT FUNCTIONAL    ==  false (by design)
```

Wave 1 reaches the first without the second (Goal section 16). Academic Python modules now coexist in the repository, but nothing exposes them as a product surface.

## 2. Status per dimension

| Dimension | Status | Evidence |
| --- | --- | --- |
| Domain models | INTEGRATED_FOUNDATION | 7 entities + ClaimEvidenceLink + CitationVerificationRecord merged; frozen Pydantic v2; 322 tests green |
| Provenance | INTEGRATED_FOUNDATION | 4 independent chains via ProvenanceGraph; deterministic; tested |
| Citation verification | INTEGRATED_FOUNDATION | local deterministic verifier + versioned rule manifest + append-only records (D-32); no external API |
| Repositories | INTEGRATED_FOUNDATION | 8 runtime_checkable protocols + in-memory adapters |
| Persistence | DEFERRED_TO_NEXT_WAVE | no SQLite; gated on migration-14 review (`06_MIGRATION_14_DECISION.md`) |
| API | NOT_REGISTERED | no router; zero FastAPI wiring; no composition-root registration |
| UI | NOT_REGISTERED | no Streamlit surface; zero UI wiring |
| Journey | NOT_REGISTERED / DEFERRED_TO_NEXT_WAVE | no Academic Journey; D-37/RT-20 honest state required before any workspace ships |
| FeedbackPolicy | DEFERRED_TO_NEXT_WAVE | Academic instance deferred per D-03 |
| Exports | NOT_REGISTERED | no academic export surface; exports remain l2-only |
| Locale | NOT_REGISTERED | zero locale changes across all merges (`git diff b171cce HEAD -- locales` empty; 600/600 contract untouched) |

## 3. No ambiguous production exposure

- Zero `app.*` imports in `app/academic` (AST contract test) — cannot be reached by any L2 service.
- Zero `app.academic` imports in 12 L2 consumer trees (contract test) — cannot reach learner data.
- No API/UI/Journey/Feedback/export registration exists; composition root unchanged for academic.
- Advisory `academic` on submissions is rejected (422); no academic workflow surface exists.
- Locale, launcher, requirements, and migration surfaces are untouched (verified diffs).

## 4. Gate statement

**WU11 GREEN.** Academic is integrated as a foundation with unambiguous non-production status; there is no ambiguous production exposure. The next-wave Academic Goals (persistence, API, UI) remain explicitly gated per `12_NEXT_WAVE_HANDOFF.md`.
