from __future__ import annotations

import streamlit as st

from app.config import load_settings
from app.ui.api_client import ApiClientError, WritingFeedbackApiClient


@st.cache_resource
def get_api_client(base_url: str) -> WritingFeedbackApiClient:
    return WritingFeedbackApiClient(base_url)


def run() -> None:
    api_client = get_api_client(load_settings().api_base_url)
    st.set_page_config(page_title="English Writing Feedback Prototype", page_icon="✍️", layout="wide")
    st.title("Intelligent English Writing Feedback Prototype v0.5")
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
        if health.get("analyzer_fallback_active"):
            st.warning("The requested NLP analyzer is unavailable; the API will record and use BasicAnalyzer fallback.")
    except ApiClientError:
        st.info("Analyzer status will appear after the local API is available.")

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
                disabled=not timed,
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
