from __future__ import annotations

import streamlit as st

from app.config import load_settings
from app.ui.api_client import ApiClientError, WritingFeedbackApiClient


@st.cache_resource
def get_api_client() -> WritingFeedbackApiClient:
    return WritingFeedbackApiClient(load_settings().api_base_url)


def run() -> None:
    st.set_page_config(page_title="English Writing Feedback Prototype", page_icon="✍️", layout="wide")
    st.title("Intelligent English Writing Feedback Prototype v0.2")
    st.caption("Formative feedback from prototype heuristics and optional LLM support — not automatic scoring.")
    st.warning(
        "This prototype is not educationally validated, does not measure proficiency, and does not replace teacher judgment."
    )

    with st.form("essay_submission"):
        left, right = st.columns(2)
        with left:
            student_id = st.text_input("Student ID", placeholder="Use a pseudonymous ID")
            writing_prompt = st.text_area("Writing prompt", height=100)
            genre = st.selectbox("Genre", ["argumentative essay", "expository essay", "narrative essay"])
        with right:
            draft_stage = st.selectbox("Draft stage", ["first draft", "revised draft", "final draft"])
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
        }
        with st.spinner("Saving, analyzing, and generating feedback…"):
            result = get_api_client().submit(submission)
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
        st.markdown(
            f"- **{exercise['exercise_type'].replace('_', ' ').title()}** "
            f"({exercise['diagnosis_id']} · {exercise['diagnosis_category']}): "
            f"{exercise['instructions']} {exercise['exercise_content']}"
        )
    st.subheader("Longitudinal comment")
    st.write(feedback["longitudinal"]["comment"])
    st.caption("History evidence IDs: " + (", ".join(feedback["longitudinal"]["history_evidence_ids"]) or "none"))
    st.caption(feedback["uncertainty_note"])

    with st.expander("Prototype language metrics"):
        st.json(result["analysis"])
    with st.expander("Structured diagnosis signals"):
        st.json(result["diagnosis"])
