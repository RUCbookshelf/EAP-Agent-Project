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
from app.ui.features.student.submit_reliability import (
    consume_pending,
    enter_pending,
    release_pending,
)
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


def _clear_practice_intent() -> None:
    st.session_state.pop("practice_source_submission_id", None)
    st.session_state.pop("practice_priority_index", None)


def _ensure_current_exercise(
    api_client: StudentPracticeApiPort, learner_id: str, target: dict
) -> None:
    """One stable current exercise for the selected target (WU4 focused path).

    Reuses the latest existing instance and creates exactly one only when
    none exists, seeded from the persisted priority evidence quote. A failure
    is recoverable: the target stays selected and the page shows the existing
    generate step (never a blank or fabricated task).
    """
    try:
        instances = api_client.get_exercise_instances(
            target.get("practice_target_id", ""))
        if instances:
            return
        context = api_client.get_practice_target_context(
            learner_id, target.get("practice_target_id", ""))
        seed = ""
        if context.get("context_status") == "priority":
            seed = (context.get("priority_context") or {}).get("evidence_quote", "")
        created = api_client.create_exercise(
            target.get("practice_target_id", ""),
            {"practice_target": target, "source_text": seed},
        )
        if created.get("status") == "practice_not_available":
            return
        st.session_state["current_exercise_v2"] = created
    except ApiClientError:
        return


def _consume_practice_intent(api_client: StudentPracticeApiPort, learner_id: str, lang: str) -> bool:
    """Resolve one explicit Open Practice intent (v0.9.7-B WU4).

    The intent carries only persisted-reference components
    (source_submission_id, zero-based priority_index) set by Feedback or
    Revision. The server assembles the stable priority reference and runs the
    WU3 create-or-reuse; on success the returned target becomes the page
    preset. Invalid intents are cleared with an honest note; transient API
    failures keep the intent so the next rerun retries idempotently.
    Returns True when the page must rerun (intent consumed or invalid).
    """
    source = st.session_state.get("practice_source_submission_id")
    index = st.session_state.get("practice_priority_index")
    if source is None or index is None:
        return False
    try:
        target = api_client.create_practice_target({
            "student_id": learner_id,
            "source_submission_id": int(source),
            "priority_index": int(index),
        })
    except ApiClientError as exc:
        if exc.retryable:
            render_api_error(exc, lang)
            return False
        _clear_practice_intent()
        st.session_state["practice_intent_invalid"] = True
        return True
    _clear_practice_intent()
    if target.get("status") == "practice_not_available":
        st.session_state["practice_intent_invalid"] = True
        return True
    st.session_state["practice_target_preset"] = target.get("practice_target_id", "")
    _ensure_current_exercise(api_client, learner_id, target)
    return True


def _selected_active_target(targets: list[dict]) -> dict | None:
    """Select the validated preset target or the deterministic oldest active."""
    active_targets = [item for item in targets if item.get("status") == "active"]
    preset = st.session_state.pop("practice_target_preset", None)
    if preset:
        for item in active_targets:
            if item.get("practice_target_id") == preset:
                return item
    return active_targets[0] if active_targets else None


def _priority_task_context(context: dict | None) -> dict | None:
    """The resolved priority context for the focused task display."""
    if context and context.get("context_status") == "priority":
        return context.get("priority_context") or {}
    return None


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
    if _consume_practice_intent(api_client, learner_id, lang):
        st.rerun()
    if st.session_state.pop("practice_intent_invalid", None):
        info_box("student_practice_intent_invalid", lang)
    try:
        with st.spinner(t("practice_loading", lang)):
            targets = api_client.get_practice_targets(learner_id)
            selected = _selected_active_target(targets)
            context = None
            exercise = None
            attempts: list[dict] = []
            if selected:
                context = api_client.get_practice_target_context(
                    learner_id, selected.get("practice_target_id", ""))
                instances = api_client.get_exercise_instances(
                    selected.get("practice_target_id", "")
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

    if not selected:
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

    section_header("practice_target", lang=lang)
    student_context_block(
        [("student_practice_focus", selected.get("target_label", ""))], lang
    )
    technical_caption(
        f"{t('student_practice_source_submission', lang)}: "
        f"#{selected.get('source_submission_id', '?')}"
    )

    priority_context = _priority_task_context(context)
    if priority_context is not None:
        section_header("student_practice_priority_task", lang=lang)
        student_context_block(
            [
                ("student_practice_focus", selected.get("target_label", "")),
                (
                    "student_practice_why_selected",
                    priority_context.get("explanation", ""),
                ),
                (
                    "student_practice_direction",
                    priority_context.get("revision_guidance", ""),
                ),
            ],
            lang,
        )
        if priority_context.get("evidence_quote"):
            section_header("student_feedback_evidence", lang=lang)
            evidence_quote(priority_context["evidence_quote"], lang)
    elif context and context.get("context_status") == "unavailable":
        info_box("student_practice_context_unavailable", lang)

    if not exercise:
        student_task_steps(list(steps), 1, lang)
        student_action_block(
            "student_practice_current_action",
            "student_practice_action_generate",
            lang,
        )
        seeded_text = (
            priority_context.get("evidence_quote", "")
            if priority_context is not None
            else ""
        )
        source_text = st.text_area(
            t("student_practice_source_text", lang),
            key="practice_source_v2",
            height=120,
            value=seeded_text,
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
        technical_caption(
            f"{t('student_practice_attempt_reference', lang)}: "
            f"#{latest.get('attempt_id', '?')}"
        )
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

    if consume_pending("practice", "PRACTICE_ATTEMPT", lang):
        # A duplicate click or refresh raced the in-flight submission: the
        # queued action is consumed and the pending state shown; the next
        # rerun reconciles against the persisted attempt.
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
            enter_pending("practice")
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
                release_pending("practice")
                render_api_error(exc, lang)
                return
            release_pending("practice")
            st.session_state["exercise_attempts_v2"] = [attempt]
            st.rerun()
    limitation_notice("practice_boundary", lang)
