# FastAPI v1

Base URL defaults to `http://127.0.0.1:8000`. Interactive OpenAPI documentation is at `/docs`.

| Method | Path | Current behavior |
|---|---|---|
| GET | `/api/v1/system/health` | API/database status, versions and a boolean LLM configuration state; never a key |
| GET | `/api/v1/system/version` | application, API, Prompt, Schema, analysis, diagnosis and migration versions |
| POST | `/api/v1/submissions` | complete protected feedback workflow |
| GET | `/api/v1/submissions/{submission_id}` | stored submission and structured results |
| GET | `/api/v1/students/{student_id}` | pseudonymous student metadata and submission count |
| GET | `/api/v1/students/{student_id}/history` | submissions and saved history records |
| GET | `/api/v1/students/{student_id}/profile` | student counts, latest Snapshot, sufficiency, issues, priorities and limits |
| GET | `/api/v1/students/{student_id}/progress` | recalculates and saves a versioned longitudinal Snapshot |

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
