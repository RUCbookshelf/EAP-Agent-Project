# Research Data Schema v0.8.2

## Export Record Structure

Each export record is a flat JSON object keyed by submission_id with the following groups:

### Submission Metadata
- student_id (pseudonymized per privacy mode)
- writing_prompt, genre, draft_stage
- timed, time_limit_minutes, active_writing_duration_seconds
- timing_source, timing_quality
- tool_use, submitted_at

### Analysis Results
- analyzer_id, analyzer_version, analysis_run_id
- metric_results (keyed by metric_id with value, version, confidence)
- nlp_library, nlp_model_name, nlp_model_version

### Diagnostic Calibration
- diagnosis_version, configuration_version
- eligible, selected, suppressed diagnoses
- priority scores, evidence validation results

### Feedback Records
- provider_name, model_name, prompt_version
- success_status, fallback_reason, validation_status
- StructuredFeedback (positive_finding, priority_feedback, exercises)
- uncertainty_note

### Practice Records (v0.9+)
- practice_targets, exercise_instances, exercise_attempts
- practice_evaluations, feedback_engagement_traces
- within_task_response_candidates, transfer_evidence_candidates

## Manifest

Each export includes a manifest.json with:
- export_id, created_at, completed_at
- privacy_mode, formats
- record_counts, excluded_counts
- git_commit, migration_version, config_version
