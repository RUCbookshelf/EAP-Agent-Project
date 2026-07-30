# Evidence Validation v0.6.1

## v0.7.1 structured reliability checks

The validator compares every structured longitudinal fact with the backend assessment, rejects unknown History Evidence IDs, and prevents trend wording above the available evidence level. It no longer treats one fixed phrase as the authoritative no-history contract. The reliability service can conservatively replace only incompatible longitudinal wording and configured risky positive-finding phrases; exact quotation, diagnosis relevance, revision evidence and ID checks remain mandatory.

Feedback evidence passes two independent checks:

1. exact presence: the quotation is a continuous verbatim span of the essay after whitespace normalization;
2. relevance: the span or recorded location actually supports the selected diagnosis.

## Relevance rules

| Category | Minimum relevant evidence |
|---|---|
| Lexical repetition | quote contains the diagnosed surface/lemma, or an explicit occurrence location does |
| Connective use | quote contains a detected expression, or records the exact adjacent sentences/paragraph boundary under review |
| Long sentence | quote is the exact flagged sentence |
| Input quality | quote corresponds to the exact flag span |
| Revision diagnosis | evidence binds to an alignment ID or recorded metric change |
| Strength | exact candidate span demonstrates the stated observable feature |

Statuses are `verified`, `partially_verified`, `irrelevant`, and `insufficient_evidence`. Only `verified` evidence can become a selected priority in v0.6.1. Irrelevant or insufficient evidence is saved with its suppression reason, omitted from FeedbackContext, and cannot generate an exercise.

DeepSeek correction may replace an invalid quotation with another exact relevant essay span. It may not reactivate a monitored or suppressed diagnosis, invent a diagnosis from raw metrics, or pad the response to two priorities. Existing Pydantic, diagnosis-ID, history-ID, redaction, one-retry, 3,600-token correction-budget, and LocalDemo fallback protections remain in force.
