# Privacy and De-identification v0.8.2

## PII Detection

The system uses regex-based PII scanning on submission text:
- Email addresses
- Phone numbers (multiple formats)
- Names (simple heuristics, not reliable)
- Geographic locations (city/country names)
- Institutional identifiers

Each PII candidate is stored in `pii_candidates` table with category, offsets, matched text, confidence, and review status.

## PII Review Workflow

1. Researcher runs PII scan on a submission
2. Candidates are displayed with review options: confirm (redact), reject (keep)
3. Confirmed PII candidates can be redacted with replacement markers
4. Review records are stored append-only

## Privacy Modes in Export

| Mode | student_id | PII in text | Metadata |
|------|-----------|-------------|----------|
| internal_research | original | preserved | full |
| pseudonymized | hash-based pseudonym | flagged | full |
| minimal_anonymous | removed | redacted | minimal |

## Limitations

- Automated PII detection is incomplete; it will miss many real PII instances and may flag false positives
- This system is a research prototype, not a certified de-identification tool
- No irreversible anonymization is guaranteed
- Human review and external ethics approval remain required before any data sharing
