# Data Quality v0.8.2

## Data Quality Report

The `/api/v1/research/data-quality` endpoint produces a report including:

### Submission Completeness
- Total submissions, students, revision groups
- Submissions with analysis, diagnosis, feedback
- Missing record counts per type

### Version Coverage
- Distribution of analysis_versions, diagnosis_versions, configuration_versions
- Outdated or legacy-version records

### Privacy Mode Coverage
- PII scan coverage (submissions scanned vs total)
- Human review coverage (targets reviewed vs total)

### Timing Quality
- Submissions with actual vs estimated vs missing durations
- Timing source distribution

## Limitations

- The report is descriptive only; it does not assess data fitness for any specific research purpose
- Missing data is flagged but not imputed
- Small sample sizes are noted but not blocked
