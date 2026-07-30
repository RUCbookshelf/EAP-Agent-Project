# Research Data Export v0.8.2

## Overview

The research export pipeline produces auditable, privacy-aware, version-traceable research data exports in JSONL and CSV formats. Three privacy modes are supported.

## Privacy Modes

- `internal_research` — full data for local researcher use; PII is not automatically redacted
- `pseudonymized` — student_id replaced with stable pseudonyms; PII candidates flagged but not auto-removed
- `minimal_anonymous` — most aggressive; PII redacted, pseudonymized IDs, minimal metadata retained

## Export Flow

1. Researcher selects privacy mode and format (JSONL/CSV)
2. ExportJob created with filter spec
3. Preview endpoint shows record counts and excluded items
4. Run endpoint generates files in `research_exports/{export_id}/`

## Schema

Export records include: submission metadata, analysis results, metric values, diagnostic calibration, feedback records, practice records, and version/configuration provenance. All are flat records for research consumption.

## Limitations

- Automated PII detection is regex-based and incomplete; human review is required before any external use
- Minimal anonymous export does not guarantee irreversible anonymization
- External ethics and data-governance approval remain necessary
- Exports are not automatically training-ready
