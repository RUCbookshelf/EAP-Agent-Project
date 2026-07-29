# Master roadmap

Last updated: 2026-07-29.

| Item | Current value |
|---|---|
| Current project version | 0.6.0 (completed; final human review pending) |
| v0.2 status | completed |
| v0.3 status | completed; human continuation authorization received in the v0.4-v0.6 goal |
| v0.4 status | completed |
| v0.5 status | completed; 121 passed, 1 skipped; migration 5; verification PASS |
| v0.6 status | completed; 149 passed, 1 skipped; migration 6; verification PASS |
| v0.3 implementation commit | `0ce8f1a` |
| Database migration version | 6 |
| Prompt version | `feedback-prompt-v0.5.0` for revision evidence; compatible earlier prompts retained |
| Feedback Schema version | `structured-feedback-v0.5.0` for revision feedback |
| API version | v1 |
| Current blocker | none |
| Next step | Stop; conduct `V0.6_FINAL_HUMAN_REVIEW_GUIDE.md` before authorizing v0.7 |

## Version sequence

- v0.2 — local API-first cloud-ready architecture: `completed`
- v0.3 — longitudinal analysis engine: `completed`
- v0.4 — NLP Analyzer 2.0: `completed`
- v0.5 — Revision-aware Feedback: `completed` (`75117ac`)
- v0.6 — Progress Visualization and Versioned Configuration: `completed`
- v0.7 / full CALF measurement: `not_started`

“Cloud-ready” means separable interfaces and configuration; it does not mean cloud deployment. The current authorization ends after v0.6; v0.7 and full CALF work remain `not_started`.
