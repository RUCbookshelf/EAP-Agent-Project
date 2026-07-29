# FastAPI v1

Base URL defaults to `http://127.0.0.1:8000`. Interactive OpenAPI documentation is at `/docs`.

| Method | Path | Current behavior |
|---|---|---|
| GET | `/api/v1/system/health` | API/database status, versions and a boolean LLM configuration state; never a key |
| GET | `/api/v1/system/version` | application, API, Prompt, Schema, analysis, diagnosis and migration versions |
| POST | `/api/v1/submissions` | complete protected feedback workflow |
| GET | `/api/v1/submissions/{submission_id}` | stored submission and structured results |
| GET | `/api/v1/submissions/{submission_id}/diagnostic-audit` | raw/monitored/eligible/selected/suppressed calibration audit and metric confidence |
| GET | `/api/v1/students/{student_id}` | pseudonymous student metadata and submission count |
| GET | `/api/v1/students/{student_id}/history` | submissions and saved history records |
| GET | `/api/v1/submissions/{submission_id}/revision-candidates` | same-student candidates; never auto-links |
| POST | `/api/v1/revisions` | explicitly link an existing source and target draft |
| GET | `/api/v1/revisions/{revision_group_id}` | group and latest append-only Snapshot |
| GET | `/api/v1/revisions/{revision_group_id}/comparison` | latest structured revision comparison |
| GET | `/api/v1/submissions/{submission_id}/revision-analysis` | Snapshot history relevant to one submission |
| GET | `/api/v1/students/{student_id}/dashboard` | API-computed timeline, version-separated metric series, issue and exclusion evidence |
| GET/POST | `/api/v1/admin/configurations` | list/audit configurations or create an immutable draft |
| POST | `/api/v1/admin/configurations/{id}/validate` | validate registered resources and parameter compatibility |
| POST | `/api/v1/admin/configurations/{id}/activate` | activate a validated configuration; exactly one remains active |
| POST | `/api/v1/admin/configurations/{id}/rollback` | reactivate the parent without deleting either version |
| GET | `/api/v1/admin/algorithms` | safe Algorithm Registry metadata |
| GET | `/api/v1/admin/metrics` | safe Metric Registry metadata |
| GET | `/api/v1/admin/registries` | Analyzer/Metric/Algorithm/Prompt registry summary |
| POST | `/api/v1/admin/reanalysis/preview` | preview scope, versions and LLM-cost state |
| POST | `/api/v1/admin/reanalysis/run` | append reanalysis outputs; LLM off by default |

`POST /api/v1/submissions` also accepts optional `revision_of_submission_id`. Its v0.6.1 response includes a `diagnostic_calibration` summary; student feedback contains only selected evidence-verified priorities. Cross-student, self, cyclic and
duplicate links return the standard structured error envelope.

Admin routes are local-research-prototype interfaces without production authentication and must not be publicly exposed.
Their schemas do not contain keys, passwords, database credentials or complete environment values.
| GET | `/api/v1/students/{student_id}/profile` | student counts, latest Snapshot, sufficiency, issues, priorities and limits |
| GET | `/api/v1/students/{student_id}/progress` | recalculates and saves a versioned longitudinal Snapshot |
| GET | `/api/v1/submissions/{submission_id}/analyses` | list append-only AnalysisRuns |
| POST | `/api/v1/submissions/{submission_id}/analyses` | append one local reanalysis; never call an LLM |

v0.4 health also returns active Analyzer/version, spaCy and English-model availability/version, and explicit fallback state/reason. It never returns credentials. Submission analysis includes input-quality flags, metric results, resource/parameter versions and evidence artifacts.

Errors use `{"error":{"code":"...","message":"...","details":[]}}`. Validation is 422 and missing records are 404. Errors do not expose keys, full Prompt text, or internal stack traces. Essay text is limited to 50,000 characters; required strings are stripped and cannot be blank.

`progress` supports `metric`, `start_date`, `end_date`, `comparable_only` and `analysis_version`. Each successful recalculation appends a Snapshot. Unsupported metrics and invalid ranges return structured 422 errors.

Example shape (abridged):

```json
{
  "student_id": "V03_SYNTH_A",
  "baseline_status": "available",
  "snapshot_id": "LP000001",
  "analysis_version": "longitudinal-v0.3.0",
  "included_submission_ids": ["E000001", "E000002", "E000003"],
  "metric_trends": {"word_count": {"direction": "increasing", "confidence": "medium"}},
  "persistent_issues": [],
  "recently_reduced_issues": [],
  "unstable_issues": [],
  "current_priority_candidates": [],
  "confidence_summary": "Prototype longitudinal evidence is limited.",
  "limitations": ["Metric trends are not language-ability growth conclusions."]
}
```
