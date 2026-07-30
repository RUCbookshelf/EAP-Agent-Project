# Feedback provider status v0.7.1

`FeedbackProviderStatus` is an auditable execution record stored separately from formal feedback. It never indicates educational quality.

| `status` | Meaning | Fallback |
|---|---|---|
| `external_success` | External response passed unchanged | false |
| `external_success_with_server_repair` | Valid sections retained; an allowed local field repair passed revalidation | false |
| `request_failed` | Request did not return a usable response | true |
| `response_parse_failed` | Response could not be parsed into the schema; correction failed or was unavailable | true |
| `response_validation_failed` | Parsed response violated evidence/fact validation; correction failed or was unavailable | true |
| `correction_failed` | Used as the terminal reason code after the one permitted correction also failed | true |
| `fallback_success` | LocalDemo was explicitly selected or used as fallback | depends on `fallback_used` |

The object records provider/model, request status, initial validation, whether correction ran, correction validation, server-repair fields, fallback state/reason code, a sanitized deduplicated reason, and retry count (0 or 1). API keys and raw provider responses are never stored in this object.

Student view shows a concise label. Research audit view may show the structured detail. A server repair is not a retry and does not count as fallback; it is limited to configured safe positive-finding wording or a longitudinal comment that conflicts with backend facts. Exact quotation, diagnosis, evidence-ID and revision validation still run after repair.
