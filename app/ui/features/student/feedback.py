"""Student Feedback feature (v0.9.5-C)."""

from __future__ import annotations

import streamlit as st

from app.ui.api_client import ApiClientError
from app.ui.ports.student import StudentFeedbackApiPort
from app.ui.components import (
    empty_state,
    evidence_quote,
    feedback_priority_card,
    info_box,
    limitation_notice,
    render_api_error,
    section_header,
    student_action_block,
    student_context_block,
    student_page_intro,
    technical_caption,
)
from app.ui.features.student.formatting import _feedback_category_label
from app.ui.features.student.navigation import (
    _finish_feedback_cycle,
    _navigate_priority_revision,
    _navigate_priority_practice,
    _navigate_student_page,
    _navigate_writing_revision,
)
from app.ui.features.student.session import _writing_saved_for_learner
from app.ui.locale import t
from app.ui.student_context import set_selected_learner, student_id_input


def render_feedback_content(result: dict, api_client: StudentFeedbackApiPort, lang: str) -> None:
    """Render gate-selected feedback in priority, action, evidence order."""
    del api_client  # Kept in the public renderer signature for caller compatibility.
    provider = result.get("feedback_result", {})
    feedback = provider.get("feedback", {})
    empty_states = set(result.get("ui_empty_states") or [])
    priorities = feedback.get("priority_feedback", [])
    has_priority = bool(priorities) and "NO_SELECTED_PRIORITY" not in empty_states

    section_header("student_feedback_priorities", lang=lang)
    if has_priority:
        for index, item in enumerate(priorities[:2]):
            with st.container(border=True, key=f"feedback_priority_{index}"):
                with st.container(border=True, key=f"feedback_evidence_{index}"):
                    evidence_quote(item.get("evidence_quote", ""), lang)
                feedback_priority_card(
                    category=_feedback_category_label(item.get("category", ""), lang),
                    evidence_quote_text="",
                    explanation=item.get("explanation", ""),
                    revision_guidance=item.get("revision_guidance", ""),
                    lang=lang,
                )
                st.button(
                    t("student_feedback_practice_priority", lang),
                    use_container_width=True,
                    key=f"feedback_practice_priority_{index}",
                    on_click=_navigate_priority_practice,
                    args=(int(result.get("submission_id") or 0), index, lang),
                )
    else:
        empty_state(
            "student_feedback_no_priority_title",
            "student_feedback_no_priority_desc",
            lang,
        )

    section_header("student_feedback_next", lang=lang)
    if has_priority:
        with st.container(border=True, key="feedback_next_action"):
            student_action_block(
                "student_feedback_next",
                "student_feedback_next_revise",
                lang,
            )
            st.button(
                t("student_feedback_open_revision", lang),
                type="primary",
                use_container_width=True,
                key="feedback_primary_action",
                on_click=_navigate_priority_revision,
                args=(int(result.get("submission_id") or 0), lang),
            )
            info_box("student_feedback_practice_note", lang)
    else:
        # No-priority is a valid, complete workflow branch (v0.9.6-C1):
        # the user explicitly chooses to revise this draft or to finish the
        # feedback cycle. Nothing is fabricated, submitted, or generated.
        with st.container(border=True, key="feedback_next_action"):
            student_action_block(
                "student_feedback_choose_action",
                "student_feedback_choose_action_desc",
                lang,
            )
            st.button(
                t("student_revision_revise", lang),
                type="primary",
                use_container_width=True,
                key="feedback_revise_action",
                on_click=_navigate_writing_revision,
                args=(int(result.get("submission_id") or 0), lang),
            )
            st.button(
                t("student_feedback_finish_cycle", lang),
                use_container_width=True,
                key="feedback_finish_action",
                on_click=_finish_feedback_cycle,
                args=(int(result.get("submission_id") or 0), lang),
            )

    section_header("student_feedback_evidence", lang=lang)
    evidence_items = [
        (
            _feedback_category_label(item.get("category", ""), lang),
            item.get("evidence_quote", ""),
        )
        for item in priorities[:2]
        if has_priority and item.get("evidence_quote")
    ]
    if evidence_items:
        for label, quote in evidence_items:
            st.markdown(f"**{label}**")
            evidence_quote(quote, lang)
    else:
        info_box("student_feedback_no_priority_evidence", lang)

    # A positive_finding without a structured diagnosis strength is a neutral
    # passage, never a claimed Strength (v0.9.6-C1).
    strengths = (result.get("diagnosis") or {}).get("strengths") or []
    section_header(
        "student_feedback_strengths" if strengths else "student_feedback_neutral_passage",
        lang=lang,
    )
    positive_finding = feedback.get("positive_finding", {})
    if positive_finding:
        st.write(positive_finding.get("explanation", ""))
        if positive_finding.get("evidence_quote"):
            evidence_quote(positive_finding["evidence_quote"], lang)
    else:
        info_box("student_feedback_no_strengths", lang)

    uncertainty = feedback.get("uncertainty_note", "")
    limitation_notice(
        f" {uncertainty}" if uncertainty else "student_feedback_boundary",
        lang,
    )
    technical_caption(
        f"{t('student_feedback_submission_reference', lang)}: "
        f"#{result.get('submission_id', '?')}"
    )


def render_feedback_page(api_client: StudentFeedbackApiPort, lang: str) -> None:
    """Student Feedback page: selected priority, action, evidence, limitation."""
    student_page_intro("student_feedback_title", "student_feedback_subtitle", lang)

    student_id = student_id_input(
        "student_id", "feedback_student", lang, placeholder_key="student_id_placeholder"
    )
    set_selected_learner(student_id)
    learner_id = student_id.strip()
    if not learner_id:
        student_action_block(
            "student_feedback_priorities", "student_feedback_enter_id", lang, state="blocked"
        )
        limitation_notice("student_feedback_boundary", lang)
        return

    student_context_block([("student_context_learner", learner_id)], lang)
    result = st.session_state.get("submission_result")
    if not _writing_saved_for_learner(result, learner_id):
        try:
            api_client.get_student_revision_candidates(learner_id)
        except ApiClientError as exc:
            render_api_error(exc, lang)
            return
        empty_state(
            "student_feedback_no_session_title",
            "student_feedback_no_session_desc",
            lang,
        )
        st.button(
            t("student_feedback_open_writing", lang),
            type="primary",
            use_container_width=True,
            key="feedback_primary_action",
            on_click=_navigate_student_page,
            args=("student_writing_title", lang),
        )
        limitation_notice("student_feedback_boundary", lang)
        return

    render_feedback_content(result, api_client, lang)
