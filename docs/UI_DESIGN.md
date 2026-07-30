# UI design v0.8

The sixth `CALF Research` tab is visible only in research view. It groups values by construct and shows status, automation, exact version/unit, formula inputs, confidence, and limitations. It explicitly explains unavailable Accuracy/sophistication and candidate syntax. Student view shows a boundary notice and no CALF total, ranking, ability, proficiency, or CEFR interpretation.

## Information hierarchy

The Streamlit submission page keeps task entry above a compact saved-result summary. Results are divided into five tabs:

1. **Feedback** — positive finding, selected revision priorities, targeted practice, provider status and uncertainty.
2. **Revision** — one-task/multiple-drafts explanation, Draft Chain, first-to-current and pairwise comparisons, prior priorities and uptake candidates.
3. **Progress** — cross-task longitudinal status, independent-task and draft/revision-group counts, History Evidence IDs and limitations.
4. **Evidence** — prompt keywords, grouped connective expressions and descriptive metrics.
5. **Research Audit** — raw analysis, diagnosis, calibration, provider status and versions.

The top summary separates saved essay ID, draft stage, Revision Group, provider and validation state. Semantic labels use plain states such as unavailable, pairwise only, provisional pattern, passed with server repair, and fallback.

## Student and research views

**Student view** is the default. It hides raw signals, internal gates, full provider diagnostics, complete connective-class JSON and version metadata. It still shows limitations and evidence IDs where needed for transparency.

**Research audit view** exposes those technical records for local prototype review. This switch is not authorization or access control; the application remains local-only.

Changing a tab or view reads `st.session_state.submission_result`. It does not resubmit the essay, rerun the analyzer, call the provider, or create a Learner Profile Snapshot. An integration test verifies feedback and snapshot row counts do not change across a view rerender.

## Submission relationship controls

The user must choose either **Start a new independent task** or **Submit a revision within an existing task**. A revision requires an explicitly selected earlier draft from the same student. Candidate labels include essay ID, time, stage, Revision Group and prompt. A matching prompt is a non-blocking warning only and never creates a relationship automatically.

## Empty states and accessibility

Primary regions render explanatory copy for `NO_SELECTED_PRIORITY`, `NO_TARGETED_PRACTICE`, `INSUFFICIENT_CROSS_TASK_HISTORY`, `NO_PREVIOUS_PRIORITY`, `NO_FEEDBACK_UPTAKE_CANDIDATE`, and `MAJOR_REWRITE_LIMITS_ATTRIBUTION`. Empty content is not described as proof that no revision is needed.

Connectives are deduplicated and grouped by expression class. Student view presents readable expression/count/function rows; research view can inspect the complete structured classes. Labels are explicit, controls are keyboard-addressable through Streamlit, contrast uses native semantic status components, and desktop/mobile Playwright captures are part of release QA.
