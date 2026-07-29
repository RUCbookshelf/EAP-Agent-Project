from __future__ import annotations

import streamlit as st

from app.config import load_settings
from app.ui.api_client import ApiClientError, WritingFeedbackApiClient


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
    except ApiClientError as exc:
        st.error(str(exc)); return
    st.json(group["group"])
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
    st.title("Intelligent English Writing Feedback Prototype v0.7")
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

    student_id = st.text_input("Student ID", placeholder="Use a pseudonymous ID")
    draft_stage = st.selectbox(
        "Draft stage", ["first draft", "revised draft", "final draft", "independent submission"]
    )
    revision_of_submission_id = None
    if draft_stage in {"revised draft", "final draft"}:
        candidates = []
        if student_id.strip():
            try:
                candidates = api_client.get_student_revision_candidates(student_id.strip()).get("candidates", [])
            except ApiClientError:
                st.info("Save an earlier draft for this student ID before linking a revision.")
        labels = {
            f"Essay #{item['essay_id']} · {item['submitted_at']} · {item['draft_stage']} · {item['writing_prompt'][:80]}": item["essay_id"]
            for item in candidates
        }
        if labels:
            selected = st.selectbox("Explicitly choose the draft being revised", list(labels))
            revision_of_submission_id = labels[selected]
        else:
            st.warning("A revised/final draft requires an explicitly selected earlier submission; matching prompts are never linked automatically.")

    with st.form("essay_submission"):
        left, right = st.columns(2)
        with left:
            writing_prompt = st.text_area("Writing prompt", height=100)
            genre = st.selectbox("Genre", ["argumentative essay", "expository essay", "narrative essay"])
        with right:
            timed = st.checkbox("Timed writing")
            time_limit_minutes = st.number_input(
                "Time limit (minutes)", min_value=1, max_value=1440, value=30,
                help="Editable at all times; saved only when Timed writing is selected.",
            )
            tool_use = st.text_input("Tool use", value="none", help="For example: none, dictionary, spellchecker")
        essay_text = st.text_area("Essay text", height=300)
        submitted = st.form_submit_button("Submit and generate feedback", type="primary")

    if not submitted:
        st.info("Enter a pseudonymous student ID, task information, and an English draft to begin.")
        return

    if draft_stage in {"revised draft", "final draft"} and revision_of_submission_id is None:
        st.error("Choose the earlier draft explicitly before submitting this revision.")
        return

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

    st.success(f"Submission saved as essay #{result['submission_id']}.")
    provider = result["feedback_result"]
    if provider["success_status"] == "fallback_success":
        st.warning("The configured external provider was unavailable or invalid; LocalDemoProvider generated this feedback.")
        if provider.get("fallback_reason"):
            st.caption(f"Fallback reason: {provider['fallback_reason']}")
    st.caption(
        f"Provider: {provider['provider_name']} · Model: {provider['model_name']} · "
        f"Status: {provider['success_status']}"
    )

    feedback = provider["feedback"]
    st.subheader("Positive finding")
    st.write(f'“{feedback["positive_finding"]["evidence_quote"]}”')
    st.write(feedback["positive_finding"]["explanation"])
    st.subheader("Revision priorities")
    for item in feedback["priority_feedback"]:
        with st.container(border=True):
            st.markdown(f"**{item['category'].replace('_', ' ').title()}**")
            st.write(f"Diagnosis: {item['diagnosis_id']}")
            st.write('Evidence quote: “{}”'.format(item["evidence_quote"]))
            st.write(item["explanation"])
            st.write(f"Revision guidance: {item['revision_guidance']}")
    st.subheader("Targeted practice")
    for exercise in feedback["exercises"]:
        source_label = (
            "student-source sentence"
            if exercise.get("source_type") == "student_source_sentence"
            else "synthetic practice sentence"
        )
        st.markdown(
            f"- **{exercise['exercise_type'].replace('_', ' ').title()}** "
            f"({exercise['diagnosis_id']} · {exercise['diagnosis_category']}): "
            f"{exercise['instructions']} {exercise['exercise_content']}  \n"
            f"  Source: {source_label}; generation: {exercise.get('generation_version', 'unknown')}"
        )
    st.subheader("Longitudinal comment")
    st.write(feedback["longitudinal"]["comment"])
    st.caption("History evidence IDs: " + (", ".join(feedback["longitudinal"]["history_evidence_ids"]) or "none"))
    st.caption(feedback["uncertainty_note"])

    revision_snapshot = result.get("revision_snapshot")
    if revision_snapshot:
        st.subheader("Revision comparison")
        st.write(
            f"Essay #{revision_snapshot['target_submission_id']} is explicitly linked as a revision of "
            f"Essay #{revision_snapshot['source_submission_id']} in {revision_snapshot['revision_group_id']}."
        )
        if revision_snapshot["major_rewrite"]:
            st.warning("Major rewrite candidate: attribution to previous feedback is especially limited.")
        token_changes = revision_snapshot["token_changes"]
        cols = st.columns(3)
        cols[0].metric("Inserted ratio", token_changes["inserted_ratio"])
        cols[1].metric("Deleted ratio", token_changes["deleted_ratio"])
        cols[2].metric("Modified ratio", token_changes["modified_ratio"])
        st.markdown("**Previous priority status**")
        for item in revision_snapshot["diagnosis_trajectories"]:
            st.write(f"- {item['diagnosis_category']}: {item['status']}")
        st.markdown("**Feedback uptake candidates**")
        for item in revision_snapshot["uptake_candidates"]:
            st.write(f"- {item['previous_diagnosis_id']}: {item['status']} — {item['observed_change']}")
        st.caption("These are observed text changes and prototype candidates, not proof of proficiency growth or feedback causation.")

    analysis = result["analysis"]
    quality_flags = analysis.get("input_quality", {}).get("quality_flags", [])
    if quality_flags:
        st.subheader("Input quality reminders")
        st.warning("These flags request confirmation; they do not prove AI use or misconduct, and no text was removed.")
        for flag in quality_flags:
            st.write(f"- {flag['category']}: `{flag['text_span']}` — {flag['recommended_action']}")
    artifacts = analysis.get("artifacts", {})
    lexical = artifacts.get("lexical_features", {})
    connective = artifacts.get("connective_features", {})
    syntactic = artifacts.get("syntactic_features", {})
    if lexical or connective or syntactic:
        st.subheader("Prototype NLP evidence")
        st.write("Prompt keywords:", ", ".join(lexical.get("prompt_keywords", [])) or "none detected")
        st.write("Detected connective expressions:", ", ".join(item["text"] for item in connective.get("detected_connectives", [])) or "none in the current dictionary")
        cols = st.columns(3)
        cols[0].metric("Prototype lexical density", analysis["metrics"].get("lexical_density", "insufficient"))
        cols[1].metric("Prototype MATTR", analysis["metrics"].get("mattr") or "insufficient")
        cols[2].metric("Long-sentence candidates", len(syntactic.get("long_sentence_candidates", [])))
        st.caption("Automatic parser and dictionary signals can be wrong; they are feedback inputs, not ability measures.")

    with st.expander("Prototype language metrics"):
        st.json(analysis)
    with st.expander("Structured diagnosis signals"):
        st.json(result["diagnosis"])
