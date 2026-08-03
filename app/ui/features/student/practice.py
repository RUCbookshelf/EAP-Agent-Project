"""Student Practice feature (v0.9.5-C)."""

from __future__ import annotations

import streamlit as st

from app.ui.api_client import ApiClientError
from app.ui.ports.student import StudentPracticeApiPort
from app.ui.components import (
    evidence_quote,
    field_error,
    info_box,
    limitation_notice,
    render_api_error,
    section_header,
    student_action_block,
    student_context_block,
    student_page_intro,
    student_task_steps,
    success_box,
    technical_caption,
    warning_box,
)
from app.ui.contracts.practice import exercise_instruction
from app.ui.features.student.navigation import _navigate_student_page
from app.ui.locale import t
from app.ui.student_context import set_selected_learner, student_id_input


def _practice_instruction(exercise: dict, lang: str) -> str:
    """Read the learner instruction from the authoritative UI-safe contract."""
    return exercise_instruction(
        exercise.get("exercise_type", ""), lang, exercise.get("instructions", "")
    )


def _practice_constraint_label(constraint: str, lang: str) -> str:
    """Localize the two frozen deterministic-template constraints."""
    key = {
        "Retain original meaning.": "student_practice_constraint_retain",
        "Do not add unsupported content.": "student_practice_constraint_no_unsupported",
    }.get(constraint)
    return t(key, lang) if key else constraint


def _practice_status_label(prefix: str, value: str, lang: str) -> str:
    """Localize known conservative evaluation values without changing them."""
    key = f"student_practice_{prefix}_{value}"
    localized = t(key, lang)
    return localized if localized != key else value.replace("_", " ").title()


def _practice_attempt_with_cached_evaluation(loaded: list[dict]) -> list[dict]:
    """Keep a just-returned evaluation visible across the immediate rerun."""
    cached = {
        item.get("attempt_id"): item.get("evaluation")
        for item in st.session_state.get("exercise_attempts_v2", [])
        if item.get("attempt_id") and item.get("evaluation")
    }
    for item in loaded:
        if item.get("attempt_id") in cached:
            item["evaluation"] = cached[item["attempt_id"]]
    return loaded


def render_practice_page(api_client: StudentPracticeApiPort, lang: str) -> None:
    """Student Practice page: one explicit target-to-evaluation sequence."""
    student_page_intro("practice", "student_practice_purpose", lang)

    student_id = student_id_input(
        "student_id", "practice_student_v2", lang, placeholder_key="student_id_placeholder"
    )
    set_selected_learner(student_id)
    learner_id = student_id.strip()
    steps = (
        "student_practice_step_target",
        "student_practice_step_exercise",
        "student_practice_step_response",
        "student_practice_step_evaluation",
    )
    if not learner_id:
        student_task_steps(list(steps), 0, lang)
        student_action_block(
            "student_practice_current_action",
            "student_practice_enter_id",
            lang,
            state="blocked",
        )
        limitation_notice("practice_boundary", lang)
        return

    student_context_block([("student_context_learner", learner_id)], lang)
    try:
        with st.spinner(t("practice_loading", lang)):
            targets = api_client.get_practice_targets(learner_id)
            active_targets = [item for item in targets if item.get("status") == "active"]
            exercise = None
            attempts: list[dict] = []
            if active_targets:
                instances = api_client.get_exercise_instances(
                    active_targets[0].get("practice_target_id", "")
                )
                if instances:
                    exercise = instances[-1]
                    loaded_attempts = api_client.get_exercise_attempts(
                        exercise.get("exercise_id", "")
                    )
                    attempts = _practice_attempt_with_cached_evaluation(loaded_attempts)
    except ApiClientError as exc:
        render_api_error(exc, lang)
        return

    st.session_state["practice_targets_v2"] = targets
    if exercise:
        st.session_state["current_exercise_v2"] = exercise
    else:
        st.session_state.pop("current_exercise_v2", None)
    st.session_state["exercise_attempts_v2"] = attempts

    if not active_targets:
        student_task_steps(list(steps), 0, lang)
        if st.session_state.get("no_priority_reviewed"):
            # A finished no-priority cycle legitimately has no practice
            # target (v0.9.6-C1): explain the reason instead of implying failure.
            info_box("student_practice_skipped_no_priority", lang)
        student_action_block(
            "student_practice_current_action",
            "student_practice_no_target_action",
            lang,
            state="blocked",
        )
        st.button(
            t("student_feedback_open_writing", lang),
            type="primary",
            use_container_width=True,
            key="practice_primary_action",
            on_click=_navigate_student_page,
            args=("student_writing_title", lang),
        )
        limitation_notice("practice_boundary", lang)
        return

    selected = active_targets[0]
    section_header("practice_target", lang=lang)
    student_context_block(
        [("student_practice_focus", selected.get("target_label", ""))], lang
    )
    technical_caption(
        f"{t('student_practice_source_submission', lang)}: "
        f"#{selected.get('source_submission_id', '?')}"
    )

    if not exercise:
        student_task_steps(list(steps), 1, lang)
        student_action_block(
            "student_practice_current_action",
            "student_practice_action_generate",
            lang,
        )
        source_text = st.text_area(
            t("student_practice_source_text", lang),
            key="practice_source_v2",
            height=120,
            placeholder=t("student_practice_source_placeholder", lang),
        )
        if st.button(
            t("generate_exercise", lang),
            key="practice_gen",
            type="primary",
            use_container_width=True,
        ):
            payload = {"practice_target": selected, "source_text": source_text}
            try:
                created = api_client.create_exercise(
                    selected.get("practice_target_id", ""), payload
                )
            except ApiClientError as exc:
                render_api_error(exc, lang)
                return
            if created.get("status") == "practice_not_available":
                warning_box("practice_not_available", lang)
                return
            st.session_state["current_exercise_v2"] = created
            st.session_state["exercise_attempts_v2"] = []
            st.rerun()
        limitation_notice("practice_boundary", lang)
        return

    section_header("exercise_instructions", lang=lang)
    student_context_block(
        [("exercise_instructions", _practice_instruction(exercise, lang))], lang
    )
    if exercise.get("source_text"):
        evidence_quote(exercise["source_text"], lang)
    constraints = exercise.get("constraints", [])
    if constraints:
        st.markdown(
            "**" + t("exercise_constraints", lang) + "**" + chr(10)
            + chr(10).join(
                f"- {_practice_constraint_label(item, lang)}" for item in constraints
            )
        )

    if attempts:
        student_task_steps(list(steps), 4, lang)
        latest = attempts[-1]
        success_box("student_practice_attempt_saved", lang)
        section_header("student_practice_saved_response", lang=lang)
        student_context_block(
            [("student_practice_saved_response", latest.get("response_text", ""))], lang
        )
        section_header("practice_evaluation_label", lang=lang)
        evaluation = latest.get("evaluation")
        if evaluation:
            student_context_block(
                [
                    (
                        "practice_evaluation_completion",
                        _practice_status_label(
                            "completion", evaluation.get("completion_status", ""), lang
                        ),
                    ),
                    (
                        "practice_evaluation_action",
                        _practice_status_label(
                            "action", evaluation.get("target_action_status", ""), lang
                        ),
                    ),
                ],
                lang,
            )
        else:
            info_box("student_practice_evaluation_unavailable", lang)
        student_action_block(
            "student_practice_current_action",
            "student_practice_action_revision",
            lang,
        )
        st.button(
            t("student_home_go_revision", lang),
            type="primary",
            use_container_width=True,
            key="practice_primary_action",
            on_click=_navigate_student_page,
            args=("student_revision_title", lang),
        )
        limitation_notice("practice_boundary", lang)
        return

    student_task_steps(list(steps), 2, lang)
    student_action_block(
        "student_practice_current_action",
        "student_practice_action_respond",
        lang,
    )
    response_text = st.text_area(
        t("response_field", lang),
        key="practice_response_v2",
        height=160,
        placeholder=t("student_practice_response_placeholder", lang),
    )
    if st.button(
        t("submit_attempt", lang),
        key="practice_submit",
        type="primary",
        use_container_width=True,
    ):
        if not response_text.strip():
            field_error("student_practice_empty_response", lang)
        else:
            payload = {
                "student_id": learner_id,
                "response_text": response_text,
                "attempt_number": 1,
            }
            try:
                attempt = api_client.submit_exercise_attempt(
                    exercise.get("exercise_id", ""), payload
                )
            except ApiClientError as exc:
                render_api_error(exc, lang)
                return
            st.session_state["exercise_attempts_v2"] = [attempt]
            st.rerun()
    limitation_notice("practice_boundary", lang)
