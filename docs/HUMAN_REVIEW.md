# Human Review v0.8.2

## Overview

The human review system allows researchers to record human judgments about system outputs. Reviews are append-only and stored separately from system-generated records.

## Review Targets

Reviews can target:
- `diagnosis` — diagnostic results
- `evidence` — evidence citations and relevance
- `feedback` — StructuredFeedback output
- `revision` — revision analysis results

## Review Schema

Each review records:
- target_type and target_id
- reviewer_id (pseudonym)
- decision: correct, partially_correct, incorrect, uncertain
- confidence: high, medium, low
- comment (free text)
- guideline_version
- review_status: completed, superseded

## Boundaries

- Human review records are not a gold standard; they represent individual researcher judgments
- System records are never modified by human reviews
- Reviews are append-only; superseded reviews remain accessible
- The system does not use human reviews to automatically recalibrate diagnoses or feedback
