# Pre-v0.9.3 Product Experience and Reliability Audit

**Date:** 2026-07-31
**Auditor:** Codex (API inspection + Playwright browser testing)
**Git commit:** 2c4eb48
**Status:** Complete

## Executive Summary

This audit evaluated the writing-feedback-mvp v0.9.2.1 application. Primary focus: user-reported S02 Learning Journey failure (30s loading then API unavailable).

### Key Findings

1. **S02 failure reproduced and root-caused.** FastAPI intermittently hangs at startup — accepts TCP but never responds to HTTP. Causes 90s client timeout then generic error. Clean restart resolves it.

2. **8 research endpoints broken (P0).** ResearchDataService, ExportJob, HumanReviewCreate used in main.py but never imported. All return HTTP 500 with generic message.

3. **Error message is misleading.** Single message for ALL RequestExceptions — does not distinguish refusal from timeout from hung process.

4. **All Learning Journeys empty.** Zero engagement traces for all students despite 9 essays with feedback.

5. **Data consistency good.** Essays/feedback/analyses match; no practice data exists.

### Issues: 2 P0, 5 P1, 7 P2, 4 P3
### Recommended: Option B (Reliability and Performance)

---

## Environment

- Python 3.11.15, Windows
- Git: 2c4eb48 (clean)
- DB: data/writing_feedback.db, migration 12, config-v0.9.0
- API: 127.0.0.1:8000, Streamlit: 8501
- API client timeout: 90s
- DeepSeek configured (deepseek-v4-flash)
- spaCy en_core_web_sm 3.8.0

### Database Contents

| Student | Essays | Feedback | Analyses | Traces | Exercises |
|---------|--------|----------|----------|--------|-----------|
| S02     | 6      | 6        | 6        | 0      | 0         |
| S03     | 2      | 2        | 2        | 0      | 0         |
| S09     | 1      | 1        | 1        | 0      | 0         |

DB backup: data/writing_feedback_pre_audit_backup.db

---

## S02 Learning Journey Root Cause

### Primary Cause
FastAPI initialization deadlock. create_app() runs synchronously at module level (app = create_app()). If spaCy loading, DB init, or service construction blocks, the entire server hangs before serving any requests.

### Evidence
- TCP handshake completed (uvicorn bound port)
- HTTP response never arrived (ASGI app never reached handler)
- Clean restart resolved it
- Hang occurred after prior session left processes

### Contributing Factors
1. No startup health gate — run.bat waits for /health but health is the hung endpoint
2. 90s client timeout — users wait long before any message
3. Generic error — Start run.bat unhelpful when run.bat already started the hung process
4. No startup logging — cannot identify blocking step
5. No stale process cleanup on restart

### S02 Content
Even with healthy API, S02 Learning Journey shows empty state. Zero engagement_traces, transfer_evidence, practice_targets, or exercise_instances exist. Empty message says Submit an essay but S02 has 6 essays.

---

## Response Times

### API (healthy)
All endpoints <35ms. Fastest: <1ms (learner-model). Slowest: 31ms (profile).

### Browser (Playwright 1280x900)
All 12 pages load in <1s. Streamlit rerun adds ~200ms per navigation.
Zero console errors. No horizontal overflow.

---

## Startup and Recovery

### Cold Start
- FastAPI: ~8s (spaCy model loading)
- Streamlit: ~10s
- Total: ~18s to usable

### Warm Start
Identical timing. No stale processes or port conflicts.

### Partial Failure
- API down, Streamlit up: error appears immediately (connection refused)
- API restart: Streamlit does NOT auto-reconnect; manual rerun needed
- Recovery: next user interaction succeeds after API restart

### Process Lifecycle
4 processes total (normal): 2 uvicorn (parent+worker), 2 streamlit (parent+worker)

---

## Error Message Audit

### API Unavailable
Trigger: ANY requests.RequestException — connection refused, timeout, DNS, SSL.
Message: The local feedback API is unavailable. Start run.bat and try again.
Problems:
1. No distinction between not started vs. started-but-hung
2. No identification of which endpoint/action failed
3. 90s timeout before message appears
4. Remedy (start run.bat) may not help if process is hung

### Internal Error (500)
Trigger: Generic Exception handler in create_app()
Message: The operation could not be completed. No secret or internal stack is exposed.
Problems:
1. Masks NameError from missing imports
2. No actionable information
3. No logging

### Other Messages
- Student not found (404): accurate
- Empty Learning Journey: misleading (says submit essay but essays exist)
- Empty Practice: accurate
- Empty Feedback: accurate

---

## Data Consistency

### Cross-table
All 3 students consistent: essays=feedback=analyses. No orphans or duplicates.

### Empty Areas
All students: 0 engagement_traces, 0 transfer_evidence, 0 exercise_instances, 0 practice_targets.

### Learner Model
S02: 6 submissions, 2 task clusters, 4 revision drafts excluded. Analyzer incompatibility between v0.6.1 and v0.8.0 correctly detected. Baseline: insufficient_history.

---

## Navigation and State

### Role Switching
Preserves page selection. Student ID NOT preserved across roles.

### Language Switching
All 271 keys present in en + zh_CN. No English leakage in Chinese mode. No raw keys.

### Student ID
Per-page input (not shared). S02 must be re-entered on each navigation. Blank shows prompt. Invalid returns 404. Spaces stripped.

### Two-Step Pattern
Learning Journey and Practice need: (1) enter ID triggers rerun, (2) click load button. Not communicated to user.

---

## Responsive and Localization

### Desktop (1280x900)
All 12 pages render correctly. No overflow. Focus outlines visible.

### Mobile (390x844)
Home page renders. Sidebar collapses (Streamlit standard). Radio options need hamburger toggle.

### Localization
English and Chinese both correct on tested pages. All strings use locale system.

---

## Accessibility
- WCAG AA contrast maintained
- Keyboard focus: 3px blue outline
- No color-only status
- prefers-reduced-motion respected
- Monospace may reduce readability for some users

---

## Issue Register

### P0 — Unusable
| ID | Title |
|----|-------|
| REL-001 | FastAPI intermittent startup hang — TCP accepted, HTTP never served |
| ERR-001 | 8 research endpoints broken — ResearchDataService/ExportJob/HumanReviewCreate not imported |

### P1 — Core Journey Blocked
| ID | Title |
|----|-------|
| ERR-002 | Generic API-unavailable error for all request failures |
| PERF-001 | 90s client timeout with no progress feedback |
| UX-001 | Learning Journey always empty — no practice data exists |
| OBS-001 | Generic 500 handler hides all internal errors |
| REL-002 | No auto-recovery after API restart |

### P2 — Substantial Friction
| ID | Title |
|----|-------|
| UX-002 | Two-step interaction not communicated |
| UX-003 | Student ID not shared across Student View pages |
| DATA-001 | Empty Journey message contradicts existing essay data |
| RESP-001 | Mobile sidebar requires hamburger toggle |
| ERR-003 | No loading progress during API calls |
| UX-004 | Research Overview shows analyzer as aggregate count |
| I18N-001 | Error details English-only |

### P3 — Minor
| ID | Title |
|----|-------|
| UX-005 | Deploy button visible |
| UX-006 | Monospace may reduce readability |
| RESP-002 | Button 1px border limitation |
| UX-007 | Radio page nav triggers full rerun |

---

## Test Limitations
- No live DeepSeek testing (quota)
- No essay submission (avoids data creation)
- No practice exercise generation (no targets exist)
- Mobile testing limited to Home and Journey
- Chinese limited to Home and Journey
- No browser back/forward testing
- Broken endpoints not testable

---

## Decisions Required

1. v0.9.3 scope approval
2. Missing import fix priority
3. Practice data seeding for demo
4. Startup logging depth
5. Error message taxonomy

---

## Proposed v0.9.3 Scope

### Option A — Reliability Hotfix (Recommended)
Fix REL-001, REL-002, ERR-001, ERR-002.
- Startup health gate + stale process cleanup
- Fix 8 missing imports
- Classify errors: refused vs timeout vs internal
Risk: Low. v1.0 impact: Minimal.

### Option B — Reliability and Performance
Option A + PERF-001, OBS-001, UX-001, DATA-001.
- Reduce timeout to 15s
- Health polling in Streamlit
- Startup logging
- Seed minimal engagement traces
- Fix empty-state messages
Risk: Low-Medium. v1.0 impact: Positive.

### Option C — Product Hardening
Option B + UX-002, UX-003, UX-004, ERR-003, I18N-001.
- Share student ID across pages
- Loading indicators
- Fix Research Overview layout
- Full localization audit
Risk: Medium. v1.0 impact: Moderate.

---

## v1.0 Corpus Replay Readiness
**Can proceed with P0 fixes.** Database stable at migration 12. API performance excellent (<35ms). Must fix REL-001 and ERR-001 first.

---

## Deliverables
- docs/development/PRE_V0.9.3_PRODUCT_EXPERIENCE_AUDIT.md (this file)
- verification/product-audit/pre-v0.9.3/screenshots/ (14 screenshots)
- verification/product-audit/pre-v0.9.3/logs/ (browser console + API audit)
- verification/product-audit/pre-v0.9.3/issues.json (machine-readable)
- data/writing_feedback_pre_audit_backup.db

## Final State
No application code modified. No DB changes. Audit artifacts only.
