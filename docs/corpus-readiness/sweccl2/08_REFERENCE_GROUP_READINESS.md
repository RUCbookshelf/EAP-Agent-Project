# 08 — Reference-Group Readiness

Data: `data/reference_group_candidates.csv` (42 candidates).
This is a CANDIDATE design for the next Goal, not production policy.

## Statuses (conservative preparation criterion: min-N 30; final policy is a
Researcher decision)

| Status | Groups |
| --- | --- |
| READY_FOR_VALIDATION | 33 |
| PROMISING | 7 |
| TOO_SPARSE | 2 (ARG13 N=14, ARG19 N=18) |
| METADATA_UNRELIABLE | 0 |
| NOT_SUPPORTED | 0 |

## Candidate hierarchy (fallback order)

- same prompt/task (27 prompt groups)
- same genre + writing condition (argumentative; expository; timed/untimed;
  grade; major type; entry year)
- broader argumentative learner corpus
- UNAVAILABLE

## Viable groups (examples)

- Same-prompt groups with N >= 100: ARG17 (656), ARG02 (426), ARG26 (419),
  ARG23 (391), ARG10 (256), ARG04 (239), ARG08 (214), ARG05 (192), ARG07
  (177), ARG22 (165), ARG11 (156), ARG09 (154), ARG15 (126), ARG06 (127),
  ARG01 (133), ARG14 (136), ARG21 (157).
- Genre-level: argumentative 4,680; expository 270 (single prompt, scored).
- Condition groups: timed 2,499; untimed 2,451; grade 1-4 (1,549/2,172/1,108/
  121); major 4,359/591; years 68-2,450.

## Unsupported or constrained groups

- ARG13 (14) and ARG19 (18): too sparse for reference distributions.
- Entry years 2003 (68), 2007 (453): usable descriptively, fragile for
  distributional norms.
- Non-english_major (591): usable but smaller; cross-major comparisons need
  prompt control.
- Any group without prompt/genre control: descriptive only.

## Hard constraints carried forward

- Reference bands/percentiles are observed descriptive evidence only;
  normative interpretation requires the validated-measurement gate (D-07).
- No proficiency/mastery/learning-gain vocabulary in group or band naming.
- Duplicate-group members (240 documents) must be reconciled before any
  group is used for evaluation.
- Same-feature-contract requirement (I3) applies to every future comparison.
