"""Student Today/adaptive learning experience (Wave-3 WU4).

One coherent Today surface over the accepted L2 WU3 API through the
existing Wave-2 gateway:

- deterministic recommendation + explicit learner choice over qualified
  activities (alternate qualified activity always available);
- one practice attempt with deterministic evaluation + bounded learner
  self-rating (session-local, never saved) + next-step;
- consented Tutor recommendation (accept requires explicit visible
  consent; decline is side-effect safe; due-item / history-grounded /
  positive-observation / insufficient-history / unavailable states);
- bounded mini-writing handoff into the real Writing Intelligence
  pipeline when a session task exists (honest note + Writing navigation
  otherwise);
- graceful API degradation: when the Wave-2/WU3 namespace is unavailable,
  the page renders honest unavailable states and never fabricates content.

All rendered text is localized; raw WU3 internals (target codes, evidence
ids, scheduler ids, version labels) never appear.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st

from app.ui.components import (
    info_box,
    limitation_notice,
    neutral_box,
    section_header,
    student_action_block,
    student_context_block,
    student_page_intro,
    success_box,
)
from app.ui.features.student.navigation import _navigate_student_page
from app.ui.locale import t
from app.ui.student_context import set_selected_learner, student_id_input
from app.ui.wave2.gateway import Wave2Gateway


# Consent contract mirrors the accepted L2 WU3 Tutor consent snapshot.
CONSENT_SCOPE = "proactive_tutor_execution"
CONSENT_VERSION = "learner-consent-v0.1.0"

_RECOMMENDATION_KEY = "adaptive_recommendation"
_SELECTION_KEY = "adaptive_selection"
_EVALUATION_KEY = "adaptive_evaluation"
_TUTOR_RECOMMENDATION_KEY = "adaptive_tutor_recommendation"
_TUTOR_DECISION_KEY = "adaptive_tutor_decision"
_MINI_RESULT_KEY = "adaptive_mini_result"
_LEARNER_KEY = "adaptive_learner"
_PENDING_KEY = "adaptive_pending"

_ADAPTIVE_KEYS = (
    _RECOMMENDATION_KEY,
    _SELECTION_KEY,
    _EVALUATION_KEY,
    _TUTOR_RECOMMENDATION_KEY,
    _TUTOR_DECISION_KEY,
    _MINI_RESULT_KEY,
)


def _category_label(category: str, lang: str) -> str:
    """Localized category label with a safe fallback."""
    display = t(f"student_feedback_category_{category}", lang)
    if display.startswith("student_feedback_category_"):
        return category.replace("_", " ").title()
    return display


def _consent_snapshot(learner_id: str) -> dict[str, Any]:
    """Build the explicit consent snapshot sent with Tutor accept."""
    now = datetime.now(timezone.utc)
    return {
        "learner_id": learner_id,
        "granted": True,
        "revoked": False,
        "scope": CONSENT_SCOPE,
        "consent_version": CONSENT_VERSION,
        "granted_at": now.isoformat().replace("+00:00", "Z"),
    }


def _clear_adaptive_state() -> None:
    for key in _ADAPTIVE_KEYS:
        st.session_state.pop(key, None)


def _render_recommendation(gateway: Wave2Gateway, learner_id: str, lang: str) -> None:
    """Recommendation section: deterministic default + explicit learner choice."""
    view = st.session_state.get(_RECOMMENDATION_KEY)
    if view is None:
        view = gateway.adaptive_recommend(learner_id)
        st.session_state[_RECOMMENDATION_KEY] = view
    section_header("student_adaptive_recommend_section", lang=lang)
    state = view.get("state", "unavailable")
    if state == "recommended":
        reasons = view.get("reasons") or []
        if reasons:
            student_context_block(
                [(f" {t('student_adaptive_reasons_label', lang)}",
                  "; ".join(reasons))],
                lang,
            )
        activities = view.get("qualified_activities") or []
        if not activities:
            neutral_box("student_adaptive_unavailable", lang, dashed=True)
            return
        labels = {
            activity.get("activity_id", ""): activity.get("target_label", "")
            for activity in activities
        }
        default_id = view.get("default_activity_id") or activities[0].get("activity_id", "")
        choice = st.radio(
            t("student_adaptive_choice_label", lang),
            list(labels.values()),
            index=max(0, list(labels.values()).index(
                labels.get(default_id, list(labels.values())[0])
            )),
            key="adaptive_activity_choice",
            help=t("student_adaptive_choice_help", lang),
        )
        selected_id = next(
            (key for key, label in labels.items() if label == choice), default_id,
        )
        st.caption(
            f"{t('student_adaptive_default_choice', lang)}: "
            f"{labels.get(default_id, '')}"
        )
        if st.button(
            t("student_adaptive_use_activity", lang),
            key="adaptive_use_activity",
            type="primary",
            use_container_width=True,
        ):
            selection = gateway.adaptive_select(
                learner_id,
                view.get("recommendation_id", ""),
                selected_id,
            )
            st.session_state[_SELECTION_KEY] = selection
            st.rerun()
    elif state == "insufficient_history":
        neutral_box("student_adaptive_insufficient_history", lang, dashed=True)
    else:
        neutral_box("student_adaptive_unavailable", lang, dashed=True)


def _render_activity(activity: dict[str, Any], lang: str) -> None:
    """One selected qualified activity with provenance/evaluation context."""
    with st.container(border=True, key=f"adaptive_activity_{activity.get('activity_id', '')}"):
        st.markdown(f"**{activity.get('target_label', '')}**")
        if activity.get("instructions"):
            student_context_block(
                [(f" {t('student_adaptive_instructions_label', lang)}",
                  activity["instructions"])],
                lang,
            )
        if activity.get("source_text"):
            student_context_block(
                [(f" {t('student_adaptive_source_label', lang)}",
                  activity["source_text"])],
                lang,
            )
        criteria = activity.get("evaluation_criteria") or {}
        if criteria.get("completion_criteria") or criteria.get("observable_target_criteria"):
            rows = []
            if criteria.get("completion_criteria"):
                rows.append((f" {t('student_adaptive_criteria_label', lang)}",
                             criteria["completion_criteria"]))
            if criteria.get("observable_target_criteria"):
                rows.append((f" {t('student_adaptive_observed_label', lang)}",
                             criteria["observable_target_criteria"]))
            student_context_block(rows, lang)
        limitations = activity.get("limitations") or []
        if limitations:
            limitation_notice(" " + " ".join(limitations), lang)


def _render_practice(gateway: Wave2Gateway, learner_id: str, lang: str) -> None:
    """Practice section: one attempt + deterministic evaluation + self-rating."""
    selection = st.session_state.get(_SELECTION_KEY)
    if not selection or not selection.get("available"):
        return
    activity = selection.get("activity") or {}
    section_header("student_adaptive_activity_section", lang=lang)
    _render_activity(activity, lang)
    evaluation = st.session_state.get(_EVALUATION_KEY)
    if evaluation and evaluation.get("available"):
        section_header("student_adaptive_evaluation_section", lang=lang)
        student_context_block(
            [
                (f" {t('student_adaptive_evaluation_completion', lang)}",
                 t(f"student_practice_completion_{evaluation.get('completion_status', 'incomplete')}", lang)),
                (f" {t('student_adaptive_evaluation_action', lang)}",
                 t(f"student_practice_action_{evaluation.get('target_action_status', 'inconclusive')}", lang)),
            ],
            lang,
        )
        evidence = evaluation.get("evidence_statements") or []
        if evidence:
            student_context_block(
                [(f" {t('student_adaptive_evaluation_evidence', lang)}",
                  "; ".join(evidence))],
                lang,
            )
        # Bounded learner-owned self-rating: session-local, never saved,
        # never part of the deterministic evaluation.
        section_header("student_adaptive_self_rating_section", lang=lang)
        st.radio(
            t("student_adaptive_self_rating_label", lang),
            (
                t("student_adaptive_self_rating_clear", lang),
                t("student_adaptive_self_rating_uncertain", lang),
                t("student_adaptive_self_rating_unsure", lang),
            ),
            key="adaptive_self_rating",
            help=t("student_adaptive_self_rating_help", lang),
        )
        info_box("student_adaptive_self_rating_note", lang)
        return
    _render_attempt_form(gateway, learner_id, lang)


def _render_attempt_form(
    gateway: Wave2Gateway, learner_id: str, lang: str,
) -> None:
    if st.session_state.pop(_PENDING_KEY, False):
        info_box("student_adaptive_attempt_pending", lang)
        return
    response_text = st.text_area(
        t("student_adaptive_response_label", lang),
        key="adaptive_response",
        height=140,
        placeholder=t("student_adaptive_response_placeholder", lang),
    )
    if st.button(
        t("student_adaptive_submit_attempt", lang),
        key="adaptive_submit_attempt",
        type="primary",
        use_container_width=True,
    ):
        if not response_text.strip():
            info_box("student_adaptive_empty_response", lang)
            return
        st.session_state[_PENDING_KEY] = True
        evaluation = gateway.adaptive_evaluate(
            learner_id,
            (st.session_state.get(_SELECTION_KEY) or {}).get("activity", {}).get("activity_id", ""),
            response_text.strip(),
        )
        st.session_state.pop(_PENDING_KEY, None)
        st.session_state[_EVALUATION_KEY] = evaluation
        st.rerun()


def _render_next_step(lang: str) -> None:
    section_header("student_adaptive_next_step_section", lang=lang)
    if st.button(
        t("student_adaptive_open_journey", lang),
        key="adaptive_open_journey",
        use_container_width=True,
        on_click=_navigate_student_page,
        args=("learning_journey", lang),
    ):
        pass
    if st.button(
        t("student_adaptive_open_practice", lang),
        key="adaptive_open_practice",
        use_container_width=True,
        on_click=_navigate_student_page,
        args=("practice", lang),
    ):
        pass


def _render_tutor(gateway: Wave2Gateway, learner_id: str, lang: str) -> None:
    """Tutor section: consented accept / side-effect-safe decline."""
    section_header("student_adaptive_tutor_section", lang=lang)
    view = st.session_state.get(_TUTOR_RECOMMENDATION_KEY)
    if view is None:
        view = gateway.tutor_recommend(learner_id)
        st.session_state[_TUTOR_RECOMMENDATION_KEY] = view
    state = view.get("state", "unavailable")
    if state in {"insufficient_history", "unavailable"}:
        neutral_box(
            "student_adaptive_tutor_insufficient"
            if state == "insufficient_history"
            else "student_adaptive_tutor_unavailable",
            lang,
            dashed=True,
        )
        return
    state_label_key = {
        "due_item": "student_adaptive_tutor_due",
        "history_grounded": "student_adaptive_tutor_history",
        "positive_observation": "student_adaptive_tutor_positive",
    }.get(state, "student_adaptive_tutor_section")
    info_box(state_label_key, lang)
    student_context_block(
        [(f" {t('student_adaptive_tutor_suggestion_label', lang)}",
          view.get("suggestion", ""))],
        lang,
    )
    categories = view.get("categories") or []
    if categories:
        student_context_block(
            [(f" {t('student_adaptive_tutor_categories_label', lang)}",
              "; ".join(_category_label(item, lang) for item in categories))],
            lang,
        )
    observations = view.get("observations") or []
    if observations:
        for observation in observations:
            if observation.get("statement"):
                info_box(f" {observation['statement']}", lang)
            if observation.get("non_causal_note"):
                info_box(f" {observation['non_causal_note']}", lang)
    decision = st.session_state.get(_TUTOR_DECISION_KEY)
    if decision and decision.get("available"):
        if decision.get("decision") == "accept":
            success_box("student_adaptive_tutor_accepted", lang)
        else:
            neutral_box("student_adaptive_tutor_declined", lang, dashed=True)
        return
    consent = st.checkbox(
        t("student_adaptive_tutor_consent_label", lang),
        key="adaptive_tutor_consent",
        help=t("student_adaptive_tutor_consent_help", lang),
    )
    col_accept, col_decline = st.columns(2)
    with col_accept:
        accept_clicked = st.button(
            t("student_adaptive_tutor_accept", lang),
            key="adaptive_tutor_accept",
            type="primary",
            use_container_width=True,
        )
    with col_decline:
        decline_clicked = st.button(
            t("student_adaptive_tutor_decline", lang),
            key="adaptive_tutor_decline",
            use_container_width=True,
        )
    if decline_clicked:
        st.session_state[_TUTOR_DECISION_KEY] = gateway.tutor_decline(
            learner_id, view.get("recommendation_id", ""),
        )
        st.rerun()
    if accept_clicked:
        if not consent:
            info_box("student_adaptive_tutor_consent_required", lang)
            return
        st.session_state[_TUTOR_DECISION_KEY] = gateway.tutor_accept(
            learner_id,
            view.get("recommendation_id", ""),
            _consent_snapshot(learner_id),
        )
        st.rerun()
    limitation_notice("student_adaptive_tutor_boundary", lang)


def _render_mini_writing(gateway: Wave2Gateway, learner_id: str, lang: str) -> None:
    """Mini-writing handoff into the real pipeline when a session task exists."""
    section_header("student_adaptive_mini_section", lang=lang)
    task = st.session_state.get("wave2_task") or {}
    task_id = task.get("task_id") if isinstance(task, dict) else None
    if not task_id:
        neutral_box("student_adaptive_mini_no_task", lang, dashed=True)
        if st.button(
            t("student_adaptive_open_writing", lang),
            key="adaptive_mini_open_writing",
            use_container_width=True,
            on_click=_navigate_student_page,
            args=("student_writing_title", lang),
        ):
            pass
        return
    if st.session_state.pop(_PENDING_KEY, False):
        info_box("student_adaptive_mini_pending", lang)
        return
    info_box("student_adaptive_mini_help", lang)
    text = st.text_area(
        t("student_adaptive_mini_label", lang),
        key="adaptive_mini_text",
        height=100,
        placeholder=t("student_adaptive_mini_placeholder", lang),
    )
    if st.button(
        t("student_adaptive_mini_submit", lang),
        key="adaptive_mini_submit",
        type="primary",
        use_container_width=True,
    ):
        if not text.strip():
            info_box("student_adaptive_mini_empty", lang)
            return
        st.session_state[_PENDING_KEY] = True
        result = gateway.mini_writing(learner_id, task_id, text.strip())
        st.session_state.pop(_PENDING_KEY, None)
        st.session_state[_MINI_RESULT_KEY] = result
        st.rerun()
    result = st.session_state.get(_MINI_RESULT_KEY)
    if result and result.get("available"):
        success_box("student_adaptive_mini_result", lang)
        student_context_block(
            [(f" {t('student_adaptive_mini_word_count', lang)}",
              str(result.get("word_count") or 0))],
            lang,
        )


def render_adaptive_learning_page(gateway: Wave2Gateway, lang: str) -> None:
    """Entry point: the student Today/adaptive learning experience."""
    student_page_intro("student_adaptive_title", "student_adaptive_subtitle", lang)

    student_id = student_id_input(
        "student_id", "adaptive_student", lang, placeholder_key="student_id_placeholder",
    )
    set_selected_learner(student_id)
    learner_id = student_id.strip()
    if not learner_id:
        student_action_block(
            "student_adaptive_next_step_section",
            "student_adaptive_enter_id",
            lang,
            state="blocked",
        )
        limitation_notice("student_adaptive_boundary", lang)
        return

    student_context_block([("student_context_learner", learner_id)], lang)
    # Learner isolation: switching learners clears adaptive session state.
    if st.session_state.get(_LEARNER_KEY) != learner_id:
        _clear_adaptive_state()
        st.session_state[_LEARNER_KEY] = learner_id

    _render_recommendation(gateway, learner_id, lang)
    _render_practice(gateway, learner_id, lang)
    _render_tutor(gateway, learner_id, lang)
    _render_mini_writing(gateway, learner_id, lang)
    _render_next_step(lang)
    limitation_notice("student_adaptive_boundary", lang)


__all__ = ["render_adaptive_learning_page"]
