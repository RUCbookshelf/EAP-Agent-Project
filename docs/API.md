# FastAPI v1

Base URL defaults to `http://127.0.0.1:8000`. Interactive OpenAPI documentation is at `/docs`.

| Method | Path | v0.2 behavior |
|---|---|---|
| GET | `/api/v1/system/health` | API/database status, versions and a boolean LLM configuration state; never a key |
| GET | `/api/v1/system/version` | application, API, Prompt, Schema, analysis, diagnosis and migration versions |
| POST | `/api/v1/submissions` | complete protected feedback workflow |
| GET | `/api/v1/submissions/{submission_id}` | stored submission and structured results |
| GET | `/api/v1/students/{student_id}` | pseudonymous student metadata and submission count |
| GET | `/api/v1/students/{student_id}/history` | submissions and saved history records |
| GET | `/api/v1/students/{student_id}/profile` | truthful v0.2 insufficiency/planned status |
| GET | `/api/v1/students/{student_id}/progress` | truthful v0.2 insufficiency/planned status |

Errors use `{"error":{"code":"...","message":"...","details":[]}}`. Validation is 422 and missing records are 404. Errors do not expose keys, full Prompt text, or internal stack traces. Essay text is limited to 50,000 characters; required strings are stripped and cannot be blank.

Profile and progress do not fabricate trends in v0.2. Formal prototype longitudinal fields arrive in v0.3.
