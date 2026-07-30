# Dataset Splitting v0.8.2

## Overview

The dataset split system creates student-level train/val/test splits for research reproducibility.

## Split Strategy

- Splitting is at the student level (all submissions from one student go to the same split)
- Default ratios: 70% train, 15% validation, 15% test
- Splits are deterministic given a seed

## API

- `POST /api/v1/research/dataset-split` — create a split
- Returns: split_id, student assignments per split, counts

## Boundaries

- Splits are metadata assignments only; they do not automatically generate export files
- The splitting system does not balance by genre, proficiency, or any outcome variable
- Splits should be reviewed for representativeness before use
- This is a research utility, not a certified data pipeline
