from __future__ import annotations

import streamlit as st

from app.config import load_settings
from app.ui.api_client import ApiClientError, WritingFeedbackApiClient


EMPTY_STATE_COPY = {
    "NO_SELECTED_PRIORITY": (
        "No evidence-supported revision priority was selected for this draft.",
        "This does not mean that the draft needs no revision. The prototype did not identify a sufficiently reliable language-level priority.",
    ),
    "NO_TARGETED_PRACTICE": (
        "No targeted practice was generated.",
        "No diagnosis passed the current selection rules, so the system did not invent an exercise.",
    ),
    "NO_PREVIOUS_PRIORITY": (
        "The previous draft did not contain a selected priority that can be tracked.",
        "Review the draft chain and current priorities instead.",
    ),
    "NO_FEEDBACK_UPTAKE_CANDIDATE": (
        "No feedback-uptake candidate was generated.",
        "No previous priority was available, evidence was insufficient, or the draft was substantially rewritten.",
    ),
    "MAJOR_REWRITE_LIMITS_ATTRIBUTION": (
        "Major rewrite limits attribution.",
        "Extensive rewriting is observable, but it is not evidence of improvement or that feedback caused the changes.",
    ),
    "INSUFFICIENT_CROSS_TASK_HISTORY": (
        "Cross-task history is insufficient.",
        "Use the Revision tab for within-task changes; additional comparable independent tasks are required for cross-task analysis.",
    ),
}


PROVIDER_STATUS_LABELS = {
    "external_success": "Success",
    "external_success_with_server_repair": "Success with local longitudinal repair",
    "request_failed": "Request failed",
    "response_parse_failed": "Response parsing failed",
    "response_validation_failed": "Response validation failed",
    "correction_failed": "Correction attempt failed",
    "fallback_success": "Local provider success",
    "fallback_failed": "Fallback failed",
}


def grouped_connectives(analysis: dict) -> dict[str, list[dict]]:
    detected = analysis.get("artifacts", {}).get("connective_features", {}).get("detected_connectives", [])
    grouped: dict[str, dict[str, dict]] = {}
    for item in detected:
        class_name = item.get("expression_class", "discourse_connective")
        expression = item.get("normalized_form") or item.get("text")
        bucket = grouped.setdefault(class_name, {})
        if expression not in bucket:
            bucket[expression] = {
                "expression": item.get("text") or expression,
                "count": int(item.get("same_form_count") or 1),
                "function": item.get("function_category", "unspecified"),
            }
    return {name: list(items.values()) for name, items in grouped.items()}


def render_empty_state(code: str) -> None:
    title, explanation = EMPTY_STATE_COPY[code]
    st.info(f"{title}\n\n{explanation}")


def render_provider_summary(result: dict, *, research_view: bool) -> None:
    provider = result["feedback_result"]
    status = result.get("feedback_provider_status") or provider.get("feedback_provider_status") or {}
    label = PROVIDER_STATUS_LABELS.get(status.get("status"), provider.get("success_status", "Unknown"))
    st.write(f"Provider: {status.get('provider') or provider['provider_name']}")
    st.write(f"Status: {label}")
    st.write(f"Validation: {provider.get('validation_status', 'not reported')}")
    st.write(f"Fallback: {'LocalDemo' if status.get('fallback_used') else 'No'}")
    if status.get("server_repair_used"):
        st.caption("The server repaired only the listed local field while retaining valid feedback sections.")
    if research_view:
        with st.expander("Provider validation details", expanded=False):
            st.json(status)


def render_submission_result(result: dict, *, research_view: bool) -> None:
    provider = result["feedback_result"]
    feedback = provider["feedback"]
    assessment = result.get("longitudinal_assessment") or feedback.get("longitudinal_assessment") or {}
    group_summary = result.get("revision_group_summary")
    trajectory = result.get("within_task_revision_trajectory")
    empty_states = set(result.get("ui_empty_states") or [])

    with st.container(border=True):
        st.markdown(f"**Saved:** Essay #{result['submission_id']}")
        st.write(f"Draft: {result.get('ui_submission', {}).get('draft_stage', 'current submission')}")
        st.write(f"Revision group: {(group_summary or {}).get('revision_group_id', 'new independent task')}")
        st.write(f"Provider: {provider['provider_name']}")
        st.write(f"Feedback status: {provider.get('validation_status', 'unknown')}")

    feedback_tab, revision_tab, progress_tab, evidence_tab, audit_tab = st.tabs(
        ["Feedback", "Revision", "Progress", "Evidence", "Research Audit"]
    )
    with feedback_tab:
        st.subheader("Positive finding")
        st.write(f'“{feedback["positive_finding"]["evidence_quote"]}”')
        st.write(feedback["positive_finding"]["explanation"])
        st.subheader("Revision priorities")
        if "NO_SELECTED_PRIORITY" in empty_states:
            render_empty_state("NO_SELECTED_PRIORITY")
        for item in feedback["priority_feedback"]:
            with st.container(border=True):
                st.markdown(f"**{item['category'].replace('_', ' ').title()}**")
                st.write(f'Evidence: “{item["evidence_quote"]}”')
                st.write(item["explanation"])
                st.write(f"Revision guidance: {item['revision_guidance']}")
        st.subheader("Targeted practice")
        if "NO_TARGETED_PRACTICE" in empty_states:
            render_empty_state("NO_TARGETED_PRACTICE")
        for exercise in feedback["exercises"]:
            source_label = "student-source sentence" if exercise.get("source_type") == "student_source_sentence" else "synthetic practice sentence"
            st.markdown(
                f"- **{exercise['exercise_type'].replace('_', ' ').title()}**: "
                f"{exercise['instructions']} {exercise['exercise_content']}  \n"
                f"  Source: {source_label}"
            )
        st.subheader("Provider status")
        render_provider_summary(result, research_view=research_view)
        st.caption(feedback["uncertainty_note"])

    with revision_tab:
        if not trajectory:
            st.info("No linked revision history is available. Submit a revision and explicitly choose its earlier draft to build a within-task trajectory.")
        else:
            st.subheader("One task, multiple drafts")
            st.write(f"Draft submissions: {group_summary['draft_submission_count']}")
            st.write(f"Revision groups: {group_summary['revision_group_count']}")
            st.write(f"Independent writing tasks: {group_summary['independent_task_count']}")
            st.write(f"Longitudinal representative drafts: {group_summary['longitudinal_representative_count']}")
            st.caption("These drafts belong to one writing task. They support within-task revision analysis but count as one independent task for cross-task analysis.")
            st.subheader("Draft chain")
            for item in trajectory["draft_chain"]:
                st.write(f"{item['revision_sequence']}. Essay #{item['submission_id']} — {item['draft_stage']} — {item['submitted_at']}")
            first_latest = trajectory.get("first_to_latest_comparison")
            if first_latest:
                st.subheader("First draft to current draft")
                changes = first_latest["token_changes"]
                st.write(f"Inserted text: {float(changes.get('inserted_ratio', 0)):.1%}")
                st.write(f"Deleted text: {float(changes.get('deleted_ratio', 0)):.1%}")
                st.write(f"Modified text: {float(changes.get('modified_ratio', 0)):.1%}")
                st.caption("High edit ratios indicate extensive rewriting, not necessarily improvement.")
            with st.expander("Pairwise draft comparisons", expanded=False):
                for item in trajectory["pairwise_comparisons"]:
                    st.write(f"Essay #{item['source_submission_id']} → Essay #{item['target_submission_id']}")
                    st.json(item["token_changes"])
            st.subheader("Previous priority status")
            if "MAJOR_REWRITE_LIMITS_ATTRIBUTION" in empty_states:
                render_empty_state("MAJOR_REWRITE_LIMITS_ATTRIBUTION")
            elif "NO_PREVIOUS_PRIORITY" in empty_states:
                render_empty_state("NO_PREVIOUS_PRIORITY")
            else:
                for item in trajectory["previous_selected_priorities"]:
                    st.write(f"- {item.get('category', 'Priority')}: {item.get('revision_guidance', 'tracked')}")
            st.subheader("Feedback uptake candidates")
            if "NO_FEEDBACK_UPTAKE_CANDIDATE" in empty_states:
                render_empty_state("NO_FEEDBACK_UPTAKE_CANDIDATE")
            for item in trajectory["feedback_uptake_candidates"]:
                st.write(f"- {item['previous_diagnosis_id']}: {item['status']} — {item['observed_change']}")
            st.caption(f"Attribution confidence: {trajectory['attribution_confidence']}. Changes do not prove learning or feedback causation.")

    with progress_tab:
        st.subheader("Cross-task longitudinal status")
        if assessment:
            st.write(f"Status: {assessment['status'].replace('_', ' ').title()}")
            st.write(f"Comparable independent tasks: {assessment['comparable_task_count']}")
            st.write(f"Minimum required: {assessment['minimum_required']}")
            st.write(f"Revision groups: {assessment['revision_group_count']}")
            st.write(f"Draft submissions: {assessment['draft_count']}")
            st.write(assessment["comment"])
            st.caption("History evidence IDs: " + (", ".join(assessment["history_evidence_ids"]) or "none"))
        else:
            render_empty_state("INSUFFICIENT_CROSS_TASK_HISTORY")

    with evidence_tab:
        analysis = result["analysis"]
        lexical = analysis.get("artifacts", {}).get("lexical_features", {})
        st.subheader("Language evidence")
        st.write("Prompt keywords: " + (", ".join(lexical.get("prompt_keywords", [])) or "none detected"))
        groups = grouped_connectives(analysis)
        discourse = groups.get("discourse_connective", [])
        st.write("Discourse-organizing expressions")
        if discourse:
            for item in discourse:
                st.write(f"- {item['expression']} — {item['count']} — {item['function']}")
        else:
            st.info("No discourse-organizing expression was detected by the current dictionary. This is not evidence that the draft lacks cohesion.")
        if research_view:
            with st.expander("Complete connective classes and counts", expanded=False):
                st.json(groups)
        st.write(f"Prototype MATTR: {analysis['metrics'].get('mattr') or 'insufficient'}")
        st.caption("MATTR describes sampled lexical variation under the current token rules; it is not a proficiency score.")
        st.write(f"Prototype lexical density: {analysis['metrics'].get('lexical_density', 'insufficient')}")
        st.caption("Lexical density is sensitive to task, length and automatic part-of-speech analysis.")

    with audit_tab:
        if not research_view:
            st.info("Switch to Research audit view to inspect raw signals, gates, versions and provider validation details.")
        else:
            st.subheader("Research audit")
            st.json({
                "analysis": result["analysis"],
                "diagnosis": result["diagnosis"],
                "diagnostic_calibration": result.get("diagnostic_calibration"),
                "provider_status": result.get("feedback_provider_status"),
                "longitudinal_assessment": assessment,
            })


@st.cache_resource
def get_api_client(base_url: str) -> WritingFeedbackApiClient:
    return WritingFeedbackApiClient(base_url)


def render_progress(api_client: WritingFeedbackApiClient) -> None:
    st.header("Student progress evidence")
    st.caption("API-sourced descriptive observations; trends are not ability growth.")
    student_id = st.text_input("Student ID", key="progress_student")
    metric_id = st.selectbox(
        "Registered metric",
        ["word_count", "average_sentence_length", "mattr", "lexical_density", "connective_count"],
    )
    if not st.button("Load progress evidence"):
        return
    try:
        data = api_client.get_dashboard(student_id.strip(), metric_id)
        profile = api_client.get_learner_model(student_id.strip())
    except ApiClientError as exc:
        st.error(str(exc)); return
    st.subheader("Submission timeline")
    st.dataframe(data["timeline"], use_container_width=True)
    st.subheader("Version-separated metric segments")
    for segment in data["metric_segments"]:
        st.caption(
            f"{segment['segment_id']} · Analyzer {segment['analyzer_version']} · "
            f"Metric {segment['metric_version']} · Config {segment['configuration_version']}"
        )
        st.line_chart(
            {str(point["submission_id"]): point["value"] for point in segment["points"]},
            x_label="submission", y_label=metric_id,
        )
    st.caption(
        f"Direction: {data['trend_summary']['direction']} · Variability: "
        f"{data['trend_summary']['variability']} · Confidence: {data['trend_summary']['confidence']}"
    )
    for limitation in data["trend_summary"]["limitations"]:
        st.caption(limitation)
    st.subheader("Comparability and exclusions")
    st.json(data["comparability_summary"])
    st.subheader("Issue trajectories")
    st.json(data["issue_trajectories"])
    for limitation in data["limitations"]:
        st.caption(limitation)
    st.subheader("Current formative focus")
    sufficiency = profile.get("data_sufficiency") or {}
    st.caption(sufficiency.get("explanation", "Historical evidence is unavailable."))
    targets = profile.get("current_learning_targets", [])
    if not targets:
        st.info("No current learning target passed the current Diagnostic Gate; the system will not invent one.")
    for item in targets:
        st.write(f"- {item['category'].replace('_', ' ').title()}: {item['selection_reason']}")
    st.caption("These are task-aware text observations, not proficiency or mastery judgments.")


def render_learner_model_audit(api_client: WritingFeedbackApiClient) -> None:
    st.header("Learner Model 2.0 audit")
    st.caption("Researcher view: task clusters, exclusions, evidence lineage and version-separated trajectories.")
    student_id = st.text_input("Student ID", key="learner_model_student")
    strategy = st.selectbox(
        "Representative draft strategy",
        ["final_or_latest", "first_draft_only", "latest_draft_only", "all_drafts_research_mode"],
    )
    preview, rebuild = st.columns(2)
    try:
        if preview.button("Preview without saving"):
            st.session_state["learner_model_audit"] = api_client.preview_learner_model(student_id.strip(), strategy)
        if rebuild.button("Rebuild append-only snapshot"):
            st.session_state["learner_model_audit"] = api_client.rebuild_learner_model(student_id.strip(), strategy)
        if student_id.strip():
            history = api_client.get_learner_model_snapshots(student_id.strip()).get("snapshots", [])
            if history:
                labels = [item.get("snapshot_id") for item in reversed(history)]
                selected_snapshot = st.selectbox("Historical snapshot", labels)
                if st.button("Load selected historical snapshot"):
                    st.session_state["learner_model_audit"] = api_client.get_learner_model_snapshot(
                        student_id.strip(), selected_snapshot
                    )
    except ApiClientError as exc:
        st.error(str(exc)); return
    profile = st.session_state.get("learner_model_audit")
    if not profile:
        return
    st.caption(
        f"Snapshot {profile.get('snapshot_id') or 'preview'} · {profile['profile_version']} · "
        f"Config {profile['configuration_version']}"
    )
    st.subheader("Data sufficiency and representative drafts")
    st.json({"data_sufficiency": profile["data_sufficiency"],
             "strategy": profile["representative_draft_strategy"],
             "source_submission_ids": profile["source_submission_ids"],
             "representative_submission_ids": profile["representative_submission_ids"],
             "excluded_submission_ids": profile["excluded_submission_ids"]})
    for title, key in (
        ("Task clusters", "task_clusters"), ("Metric trajectories", "metric_trajectories"),
        ("Diagnostic trajectories", "diagnostic_trajectories"),
        ("Current learning targets", "current_learning_targets"),
        ("Strength patterns", "strength_patterns"), ("History evidence registry", "history_evidence"),
    ):
        with st.expander(title, expanded=key in {"current_learning_targets", "diagnostic_trajectories"}):
            st.json(profile[key])


def render_revision_page(api_client: WritingFeedbackApiClient) -> None:
    st.header("Revision comparison")
    st.caption("Observed draft changes are not proof of learning or feedback causation.")
    group_id = st.text_input("Revision Group ID", placeholder="RG000001")
    if not st.button("Load revision comparison"):
        return
    try:
        group = api_client.get_revision_group(group_id.strip())
        comparison = api_client.get_revision_comparison(group_id.strip())
        trajectory = api_client.get_revision_trajectory(group_id.strip())
    except ApiClientError as exc:
        st.error(str(exc)); return
    st.write(f"Draft submissions: {len(group['group']['member_submission_ids'])}")
    st.write("Revision groups: 1")
    st.write("Independent writing tasks: 1")
    st.write("Longitudinal representative drafts: 1")
    st.caption("These drafts support within-task revision analysis and count as one independent task for cross-task analysis.")
    st.subheader("Draft chain")
    for item in trajectory["draft_chain"]:
        st.write(f"- Essay #{item['submission_id']} · {item['draft_stage']} · {item['submitted_at']}")
    if comparison.get("major_rewrite"):
        st.warning("Major rewrite candidate: feedback attribution is especially limited.")
    st.subheader("Observed token changes")
    st.json(comparison["token_changes"])
    st.subheader("Metric and diagnosis changes")
    st.dataframe(comparison["metric_changes"], use_container_width=True)
    st.dataframe(comparison["diagnosis_trajectories"], use_container_width=True)
    st.subheader("Feedback-uptake candidates")
    st.dataframe(comparison["uptake_candidates"], use_container_width=True)
    for limitation in comparison["limitations"]:
        st.caption(limitation)


def render_diagnostic_audit(api_client: WritingFeedbackApiClient) -> None:
    st.header("Diagnostic calibration audit")
    st.caption("Researcher-only prototype evidence. Priority scores are workflow rankings, not student scores.")
    submission_id = st.number_input("Submission ID", min_value=1, value=1, step=1, key="audit_submission_id")
    if not st.button("Load diagnostic audit"):
        return
    try:
        audit = api_client.get_diagnostic_audit(int(submission_id))
    except ApiClientError as exc:
        st.error(str(exc)); return
    st.caption(
        f"Calibration {audit['calibration_version']} · Gate {audit['gate_version']} · "
        f"Diagnosis {audit['diagnosis_version']} · Config {audit['configuration_version']}"
    )
    for title, key in (
        ("Raw signals", "raw_signals"), ("Monitored signals", "monitored_signals"),
        ("Eligible diagnoses", "eligible_diagnoses"), ("Selected priorities", "selected_priorities"),
        ("Suppressed diagnoses", "suppressed_diagnostics"),
    ):
        with st.expander(title, expanded=key == "selected_priorities"):
            st.dataframe(audit[key], use_container_width=True)
    with st.expander("Metric confidence and measurement protocols"):
        st.json(audit["metric_confidence_summary"])
    with st.expander("Evidence relevance, priority components and suppression reasons"):
        st.json({
            "selected": audit["selected_priorities"],
            "monitored": audit["monitored_signals"],
            "suppressed": audit["suppressed_diagnostics"],
        })


def render_admin(api_client: WritingFeedbackApiClient) -> None:
    st.header("Local researcher administration")
    st.warning("Local-only prototype. Do not expose this interface directly on a public network.")
    try:
        configs = api_client.get_configurations()
        registries = api_client.get_registries()
    except ApiClientError as exc:
        st.error(str(exc)); return
    st.subheader("Active and historical configurations")
    st.caption(f"Active: {configs['active_configuration_id']}")
    st.dataframe(configs["configurations"], use_container_width=True)
    active = next(item for item in configs["configurations"] if item["status"] == "active")
    with st.expander("All active prototype parameters and ranges"):
        st.json(active["payload"])
        st.caption("These values are working assumptions, not literature-validated thresholds.")
    with st.expander("Create a configuration draft"):
        mattr = st.number_input("MATTR window", 10, 500, int(active["payload"]["mattr_window"]))
        long_sentence = st.number_input("Long-sentence threshold", 10, 100, int(active["payload"]["long_sentence_threshold"]))
        temperature = st.number_input("LLM temperature", 0.0, 2.0, float(active["payload"]["llm_temperature"]), 0.1)
        note = st.text_input("Required change note")
        if st.button("Create draft"):
            payload = dict(active["payload"])
            payload.update(mattr_window=int(mattr), long_sentence_threshold=int(long_sentence), llm_temperature=float(temperature))
            try:
                created = api_client.create_configuration({"payload": payload, "change_note": note})
                st.success(f"Created {created['configuration_id']}; validate before activation.")
            except ApiClientError as exc:
                st.error(str(exc))
    selected = st.selectbox("Configuration action target", [item["configuration_id"] for item in configs["configurations"]])
    selected_item = next(item for item in configs["configurations"] if item["configuration_id"] == selected)
    differences = {
        key: {"active": active["payload"].get(key), "selected": selected_item["payload"].get(key)}
        for key in active["payload"]
        if active["payload"].get(key) != selected_item["payload"].get(key)
    }
    st.caption("Differences from active configuration")
    st.json(differences)
    confirm_configuration_action = st.checkbox("I confirm this local activation or rollback action.")
    left, middle, right = st.columns(3)
    try:
        if left.button("Validate"): st.json(api_client.validate_configuration(selected))
        if middle.button("Activate validated version", disabled=not confirm_configuration_action):
            st.json(api_client.activate_configuration(selected))
        if right.button("Rollback active version", disabled=not confirm_configuration_action):
            st.json(api_client.rollback_configuration(selected, "Confirmed local rollback."))
    except ApiClientError as exc:
        st.error(str(exc))
    st.subheader("Registries and resource status")
    for name in ("analyzers", "metrics", "algorithms", "prompts"):
        with st.expander(name.title()): st.json(registries[name])
    st.subheader("Append-only reanalysis")
    scope_type = st.selectbox("Scope", ["submission", "revision_group", "student", "analysis_run"])
    scope_id = st.text_input("Scope ID")
    call_llm = st.checkbox("Explicitly regenerate LLM feedback (may incur API charges)")
    confirm_reanalysis = st.checkbox("I confirm this append-only reanalysis scope.")
    request = {"scope_type": scope_type, "scope_id": scope_id, "call_llm": call_llm, "confirm_llm_cost": call_llm}
    try:
        if st.button("Preview reanalysis"): st.json(api_client.preview_reanalysis(request))
        if st.button("Run reanalysis", type="primary", disabled=not confirm_reanalysis):
            st.json(api_client.run_reanalysis(request))
    except ApiClientError as exc:
        st.error(str(exc))


def run() -> None:
    api_client = get_api_client(load_settings().api_base_url)
    st.set_page_config(page_title="English Writing Feedback Prototype", page_icon="✍️", layout="wide")
    st.title("Intelligent English Writing Feedback Prototype v0.7.1")
    st.caption("Formative feedback from prototype heuristics and optional LLM support — not automatic scoring.")
    st.warning(
        "This prototype is not educationally validated, does not measure proficiency, and does not replace teacher judgment."
    )
    try:
        health = api_client.health()
        st.caption(
            f"Analyzer: {health.get('active_analyzer')} · {health.get('active_analyzer_version')} · "
            f"NLP model: {health.get('nlp_model_name') or 'not applicable'} "
            f"{health.get('nlp_model_version') or ''}"
        )
        requested_provider = health.get("llm_provider")
        if requested_provider == "deepseek" and health.get("llm_api_configured"):
            st.caption(
                "Feedback provider: DeepSeek is configured. LocalDemo is used only if "
                "the API request or response validation fails."
            )
        elif requested_provider == "deepseek":
            st.warning(
                "Feedback provider: DeepSeek is selected, but no API key was loaded by "
                "the running API process. Restart after saving the local .env file."
            )
        else:
            st.caption("Feedback provider: LocalDemo is explicitly selected for this running API process.")
        if health.get("analyzer_fallback_active"):
            st.warning("The requested NLP analyzer is unavailable; the API will record and use BasicAnalyzer fallback.")
    except ApiClientError:
        st.info("Analyzer status will appear after the local API is available.")

    page = st.sidebar.radio(
        "Research prototype page",
        ["Essay submission", "Student progress", "Learner Model audit", "Revision comparison", "Diagnostic audit", "Local administration"],
    )
    if page == "Student progress":
        render_progress(api_client); return
    if page == "Revision comparison":
        render_revision_page(api_client); return
    if page == "Learner Model audit":
        render_learner_model_audit(api_client); return
    if page == "Diagnostic audit":
        render_diagnostic_audit(api_client); return
    if page == "Local administration":
        render_admin(api_client); return

    view_mode = st.radio(
        "View mode", ["Student view", "Research audit view"], horizontal=True,
        help="Student view hides internal gates and raw provider diagnostics.",
    )
    research_view = view_mode == "Research audit view"
    student_id = st.text_input("Student ID", placeholder="Use a pseudonymous ID")
    task_relationship = st.radio(
        "Task relationship",
        ["Start a new independent task", "Submit a revision within an existing task"],
        help="A revision remains part of one writing task and does not add a cross-task observation.",
    )
    is_revision = task_relationship == "Submit a revision within an existing task"
    draft_stage = st.selectbox(
        "Draft stage", ["revised draft", "final draft"] if is_revision else ["first draft", "independent submission"]
    )
    revision_of_submission_id = None
    candidates = []
    if student_id.strip():
        try:
            candidates = api_client.get_student_revision_candidates(student_id.strip()).get("candidates", [])
        except ApiClientError:
            candidates = []
    if is_revision:
        labels = {
            f"Essay #{item['essay_id']} · {item['submitted_at']} · {item['draft_stage']} · "
            f"{item.get('revision_group_id') or 'unlinked task'} · {item['writing_prompt'][:80]}": item["essay_id"]
            for item in candidates
        }
        if labels:
            selected = st.selectbox("Explicitly choose the draft being revised", list(labels))
            revision_of_submission_id = labels[selected]
            selected_item = next(item for item in candidates if item["essay_id"] == revision_of_submission_id)
            st.caption(
                f"Selected Essay #{selected_item['essay_id']} · {selected_item['submitted_at']} · "
                f"{selected_item['draft_stage']} · Revision Group: {selected_item.get('revision_group_id') or 'will be created'}"
            )
            st.info("This draft will be treated as a revision within the selected task, not as a new independent writing task.")
        else:
            st.warning("A revised/final draft requires an explicitly selected earlier submission; matching prompts are never linked automatically.")

    with st.form("essay_submission"):
        writing_prompt = st.text_area("Writing prompt", height=100)
        genre = st.selectbox("Genre", ["argumentative essay", "expository essay", "narrative essay"])
        timed = st.checkbox("Timed writing")
        time_limit_minutes = st.number_input(
            "Time limit (minutes)", min_value=1, max_value=1440, value=30,
            help="Editable at all times; saved only when Timed writing is selected.",
        )
        tool_use = st.text_input("Tool use", value="none", help="For example: none, dictionary, spellchecker")
        essay_text = st.text_area("Essay text", height=300)
        submitted = st.form_submit_button("Submit and generate feedback", type="primary")

    if not submitted:
        saved_result = st.session_state.get("submission_result")
        if saved_result:
            render_submission_result(saved_result, research_view=research_view)
        else:
            st.info("Enter a pseudonymous student ID, task information, and an English draft to begin.")
        return

    if is_revision and revision_of_submission_id is None:
        st.error("Choose the earlier draft explicitly before submitting this revision.")
        return

    if not is_revision and any(
        item.get("writing_prompt", "").strip().casefold() == writing_prompt.strip().casefold()
        for item in candidates
    ):
        st.warning("A similar prompt already exists. Confirm whether this is a new independent task or another revision. The current selection starts a new task and no relationship will be created automatically.")

    try:
        submission = {
            "student_id": student_id,
            "writing_prompt": writing_prompt,
            "genre": genre,
            "draft_stage": draft_stage,
            "timed": timed,
            "time_limit_minutes": int(time_limit_minutes) if timed else None,
            "tool_use": tool_use,
            "essay_text": essay_text,
            "revision_of_submission_id": revision_of_submission_id,
        }
        with st.spinner("Saving, analyzing, and generating feedback…"):
            result = api_client.submit(submission)
    except ApiClientError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error("The submission could not be completed. No API key or internal stack is displayed.")
        return

    result["ui_submission"] = {"draft_stage": draft_stage, "task_relationship": task_relationship}
    st.session_state["submission_result"] = result
    st.success(f"Submission saved as essay #{result['submission_id']}.")
    render_submission_result(result, research_view=research_view)
