# 16 - Stage 6 WU-A/B/C/E Verification

## Focused test suite

Environment: stage5 venv, Python 3.12.13, spaCy 3.8.7 + en_core_web_sm
3.8.0, pytest 9.1.1; `--basetemp` worktree-local (Windows sandbox).

| Area | Tests | Result |
| --- | --- | --- |
| Stage-5 baseline (resource/features/groups/intelligence) | 36 | 36/36 passed (regression) |
| WU-A student harness (version, eligibility, header/path rejection, determinism, no-text-retained) | 11 | 11/11 |
| WU-B task matching (exact, prompt+timed, fallback disclosure, explicit unmatched, validation, provenance) | 8 | 8/8 |
| WU-C comparison (provenance, no normative labels, percentile points/clamping, degenerate dist, version mismatch fail-closed, unavailable states) | 10 | 10/10 |
| Stage-6 machine-checkable artifacts (register schema/classes, no textual artifact, files exist, WU-E design record, no corpus text) | 5 | 5/5 |

Total Stage-6 suite: 34/34; combined corpus suite: 70/70 passed.

## Real-artifact query boundary smoke (governed/versioned artifacts only)

Run against the registered package and the 1,050-record distribution set:

- version query: package `sweccl2-weccl20-v0.1.0`, manifest hash
  `0d8940ff...59eb9`, license `PARTIALLY_DOCUMENTED; external use
  REQUIRES_REVIEW` - OK.
- WU-A: synthetic research submission -> snapshot
  `student-feature-snapshot-v0.1.0`, 14 features, feature set
  `corpus-features-v0.1.0`, `learner_exposure=research_only` - OK.
- WU-B: `TaskSignature(ARG17, timed)` -> exact match
  `RG-prompt_id=ARG17-timed_status=timed`, no fallback; `ARG13` ->
  `RG-genre=argumentative` with disclosed fallback
  `RG-prompt_id=ARG13`; empty signature -> explicit unmatched
  ("task signature incomplete") - OK.
- WU-C: comparison against the matched group (n_effective=408):
  `text_length_tokens` value 37 -> percentile 0.0, z -3.0479;
  `connective_density` value 108.1 -> percentile 100.0, z 4.8956;
  `sentence_length_mean` value 12.33 -> percentile 14.5, z -0.9006.
  All `evidence_class=observed_descriptive`, exposure `research_only` - OK.

## Safety checks

- No raw SWECCL path/handle accepted anywhere: path-shaped submission ids
  and corpus-header input rejected (tests).
- No normative label fields exist on comparison results (structural test).
- No proficiency/mastery/learning-gain vocabulary in modules/docs/data.
- All Stage-6 artifacts classified NON-RECONSTRUCTIVE AGGREGATE ARTIFACT in
  `data/stage6_artifact_register.json`; no TEXTUAL class entry (test).
- No commit, push, or PR; pre-existing dirty/untracked files preserved.
