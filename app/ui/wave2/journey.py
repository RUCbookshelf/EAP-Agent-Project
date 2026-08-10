"""Wave-2 Student Writing Studio journey (Goal PDW2-D-UX-STUDENT).

One guided writing loop rendered as an in-page step machine:

  start -> task/context -> prompt -> compose -> feedback
        -> scaffold (progressive) -> revise -> resubmit -> result
        -> history & learning items

The renderer talks only to the ``Wave2Gateway``; the gateway decides between
the guided Wave-2 contracts and the degraded standard flow. All student
surfaces are built from student-safe views (see app/ui/wave2/views.py) --
raw technical internals never render here.
"""

from __future__ import annotations

import streamlit as st

from app.ui.components import (
    empty_state,
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
from app.ui.features.student.navigation import _navigate_student_page
from app.ui.wave2.locale import wt
from app.ui.student_context import set_selected_learner, student_id_input
from app.ui.wave2.client import Wave2ApiClientError, Wave2ApiUnavailable
from app.ui.wave2.gateway import Wave2Gateway

# session-state keys ----------------------------------------------------------
W2_STEP = "wave2_step"                 # None | task | prompt | compose | feedback | scaffold | revise | result
W2_TASK = "wave2_task"                 # current task view
W2_TASK_DRAFT = "wave2_task_draft"     # task/context selections before the prompt step
W2_LEARNER = "wave2_learner_id"
W2_LAST_TEXT = "wave2_last_text"
W2_FEEDBACK = "wave2_feedback"         # feedback view (guided or standard shape)
W2_VERSION = "wave2_last_version"      # latest version view
W2_SCAFFOLD = "wave2_scaffold"         # scaffold view
W2_SCAFFOLD_CATEGORY = "wave2_scaffold_category"
W2_OBSERVATION = "wave2_observation"   # observation view
W2_MODE = "wave2_mode"                 # guided | standard
W2_HISTORY_TASKS = "wave2_session_tasks"  # task views created this session

ALL_W2_KEYS = (
    W2_STEP, W2_TASK, W2_TASK_DRAFT, W2_LEARNER, W2_LAST_TEXT, W2_FEEDBACK,
    W2_VERSION, W2_SCAFFOLD, W2_SCAFFOLD_CATEGORY, W2_OBSERVATION, W2_MODE,
    W2_HISTORY_TASKS,
)

TASK_TYPES = (
    "opinion", "argumentative", "discussion", "problem_solution", "general_eap",
)
WRITING_CONTEXTS = (
    "cet4", "cet6", "ielts_task2", "toefl_style", "course_essay",
    "email", "application", "reflective_journal", "other",
)
_RECURRENCE_KEYS = {
    "recurring", "stable", "reappeared", "first_observed", "insufficient_history",
}


def _reset_wave2_state() -> None:
    for key in ALL_W2_KEYS:
        st.session_state.pop(key, None)


def _go(step: str) -> None:
    st.session_state[W2_STEP] = step


def _category_label(category: str, lang: str) -> str:
    display = wt(f"wave2_category_{category}", lang)
    if display.startswith("wave2_category_"):
        return category.replace("_", " ").title()
    return display


def _recurrence_label(status: str, lang: str) -> str:
    if status in _RECURRENCE_KEYS:
        return wt(f"wave2_feedback_seen_{status}", lang)
    return wt("wave2_feedback_seen_insufficient_history", lang)


def _draft_stage_label(stage: str, lang: str) -> str:
    if stage == "first draft":
        return wt("wave2_draft_first", lang)
    if stage == "revised draft":
        return wt("wave2_draft_revised", lang)
    return stage


def _item_status_label(status: str, lang: str) -> str:
    display = wt(f"wave2_items_status_{status}", lang)
    if display.startswith("wave2_items_status_"):
        return status.title()
    return display


# ---------------------------------------------------------------------------
# journey renderers
# ---------------------------------------------------------------------------

def _render_start(learner_id: str, lang: str) -> None:
    student_task_steps(
        ["wave2_step_write", "wave2_step_feedback", "wave2_step_revise"], 0, lang,
    )
    if st.session_state.get(W2_TASK):
        student_action_block(
            "wave2_continue_current", "wave2_continue_current_desc", lang,
        )
        if st.button(wt("wave2_continue_current", lang), key="wave2_continue",
                     use_container_width=True, type="primary"):
            step = "feedback" if st.session_state.get(W2_FEEDBACK) else "compose"
            _go(step)
    else:
        student_action_block("wave2_start_new", "wave2_start_new_desc", lang)
        if st.button(wt("wave2_start_new", lang), key="wave2_start_new",
                     use_container_width=True, type="primary"):
            for key in (W2_TASK, W2_TASK_DRAFT, W2_FEEDBACK, W2_VERSION,
                        W2_SCAFFOLD, W2_OBSERVATION, W2_LAST_TEXT):
                st.session_state.pop(key, None)
            _go("task")
    info_box("wave2_studio_start_note", lang)


def _render_task_step(learner_id: str, lang: str) -> None:
    section_header("wave2_task_section", lang=lang)
    draft = st.session_state.get(W2_TASK_DRAFT) or {}
    labels = {wt(f"wave2_task_type_{kind}", lang): kind for kind in TASK_TYPES}
    default_index = max(0, list(TASK_TYPES).index(draft.get("task_type", "opinion")))
    task_type_label = st.selectbox(
        wt("wave2_task_type", lang), list(labels.keys()),
        index=default_index, key="wave2_task_type_input",
    )
    context_labels = {
        wt(f"wave2_context_{kind}", lang): kind for kind in WRITING_CONTEXTS
    }
    context_label = st.selectbox(
        wt("wave2_writing_context", lang), list(context_labels.keys()),
        index=0, key="wave2_context_input",
    )
    with st.container(border=True, key="wave2_task_meta"):
        audience = st.text_input(wt("wave2_audience", lang), key="wave2_meta_audience")
        purpose = st.text_input(wt("wave2_purpose", lang), key="wave2_meta_purpose")
        word_constraint = st.text_input(wt("wave2_word_constraint", lang), key="wave2_meta_words")
    if st.button(wt("wave2_task_next", lang), key="wave2_task_next",
                 use_container_width=True, type="primary"):
        st.session_state[W2_TASK_DRAFT] = {
            "task_type": labels[task_type_label],
            "writing_context": context_labels[context_label],
            "metadata": {
                "audience": audience.strip() or None,
                "purpose": purpose.strip() or None,
                "word_constraint": word_constraint.strip() or None,
            },
        }
        _go("prompt")


def _render_prompt_step(gateway: Wave2Gateway, learner_id: str, lang: str) -> None:
    section_header("wave2_prompt_section", lang=lang)
    info_box("wave2_prompt_help", lang)
    prompt_text = st.text_area(
        wt("writing_prompt", lang), key="wave2_prompt_input", height=120,
    )
    draft = st.session_state.get(W2_TASK_DRAFT) or {}
    if st.button(wt("wave2_prompt_create", lang), key="wave2_prompt_create",
                 use_container_width=True, type="primary"):
        if not prompt_text.strip():
            field_error("wave2_need_prompt", lang)
            return
        try:
            task = gateway.create_task(
                learner_id,
                draft.get("task_type", "general_eap"),
                draft.get("writing_context", "other"),
                prompt_text.strip(),
                metadata=draft.get("metadata") or {},
            )
        except (Wave2ApiClientError, Wave2ApiUnavailable) as exc:
            render_api_error(exc, lang)
            return
        st.session_state[W2_TASK] = task
        session_tasks = list(st.session_state.get(W2_HISTORY_TASKS) or [])
        if task.get("task_id"):
            session_tasks = [entry for entry in session_tasks
                             if entry.get("task_id") != task["task_id"]]
            session_tasks.append(task)
            st.session_state[W2_HISTORY_TASKS] = session_tasks
        st.session_state[W2_LEARNER] = learner_id
        _go("compose")


def _render_compose_step(gateway: Wave2Gateway, learner_id: str, lang: str) -> None:
    task = st.session_state.get(W2_TASK) or {}
    student_context_block([
        ("writing_prompt", task.get("writing_prompt", "")),
        ("student_context_learner", learner_id),
    ], lang)
    section_header("wave2_compose_section", lang=lang)
    info_box("wave2_compose_help", lang)
    essay_text = st.text_area(
        wt("wave2_essay_label", lang), key="wave2_essay_input", height=260,
    )
    if st.button(wt("wave2_submit_v1", lang), key="wave2_submit_v1",
                 use_container_width=True, type="primary"):
        if not essay_text.strip():
            field_error("wave2_need_text", lang)
            return
        try:
            outcome = gateway.submit_first(task, learner_id, essay_text.strip(), "first draft")
        except (Wave2ApiClientError, Wave2ApiUnavailable) as exc:
            render_api_error(exc, lang)
            return
        st.session_state[W2_FEEDBACK] = outcome["feedback"]
        st.session_state[W2_VERSION] = outcome["version"]
        st.session_state[W2_LAST_TEXT] = essay_text.strip()
        st.session_state[W2_MODE] = outcome["mode"]
        st.session_state[W2_LEARNER] = learner_id
        _go("feedback")


def _render_feedback_step(gateway: Wave2Gateway, learner_id: str, lang: str) -> None:
    feedback = st.session_state.get(W2_FEEDBACK) or {}
    mode = st.session_state.get(W2_MODE, gateway.mode())
    section_header("wave2_feedback_section", lang=lang)
    items = feedback.get("items") or []
    if not items:
        empty_state("wave2_feedback_empty_title", "wave2_feedback_empty_desc", lang)
    for index, item in enumerate(items):
        with st.container(border=True, key=f"wave2_feedback_item_{index}"):
            st.markdown(f"**{wt('wave2_feedback_what', lang)}**: {_category_label(item.get('category', ''), lang)}")
            st.markdown(f"**{wt('wave2_feedback_why', lang)}**: {item.get('context_text', '')}")
            st.markdown(f"**{wt('wave2_feedback_try', lang)}**: {item.get('try_text', '')}")
            st.markdown(f"**{wt('wave2_feedback_seen', lang)}**: {_recurrence_label(item.get('recurrence_status', 'insufficient_history'), lang)}")
            with st.expander(wt("wave2_feedback_evidence", lang), key=f"wave2_evidence_{index}"):
                if item.get("evidence_quote"):
                    evidence_quote(item["evidence_quote"], lang)
                else:
                    info_box("wave2_feedback_evidence_none", lang)
            if st.button(wt("wave2_scaffold_cta", lang),
                         key=f"wave2_scaffold_item_{index}",
                         use_container_width=True):
                category = item.get("category", "")
                try:
                    scaffold_view = gateway.scaffold(learner_id, category, level=None)
                except (Wave2ApiClientError, Wave2ApiUnavailable) as exc:
                    render_api_error(exc, lang)
                    scaffold_view = None
                if scaffold_view and scaffold_view.get("available"):
                    st.session_state[W2_SCAFFOLD] = scaffold_view
                    st.session_state[W2_SCAFFOLD_CATEGORY] = category
                    _go("scaffold")
                else:
                    st.session_state[W2_SCAFFOLD] = {"available": False}
                    st.session_state[W2_SCAFFOLD_CATEGORY] = category
                    _go("scaffold")

    if feedback.get("insufficiency_notice"):
        info_box("wave2_feedback_insufficient", lang)
    historical = feedback.get("historical_summary") or []
    if historical:
        section_header("wave2_feedback_history_section", lang=lang)
        for entry in historical:
            st.markdown(
                f"- {_category_label(entry.get('category', ''), lang)} · "
                f"{_recurrence_label(entry.get('recurrence_status', 'insufficient_history'), lang)}"
            )
    statements = feedback.get("global_statements") or feedback.get("local_statements") or []
    if statements:
        section_header("wave2_feedback_stable_section", lang=lang)
        for statement in statements:
            info_box(f" {statement}", lang)
    if mode == "standard":
        warning_box("wave2_standard_mode_note", lang)

    with st.container(border=True, key="wave2_feedback_actions"):
        if st.button(wt("wave2_go_revise", lang), key="wave2_go_revise",
                     use_container_width=True, type="primary"):
            _go("revise")
        if st.button(wt("wave2_go_history", lang), key="wave2_go_history",
                     use_container_width=True):
            _navigate_student_page("student_wave2_history_title", lang)
    limitation_notice("wave2_boundary", lang)
    technical_caption(f"{wt('wave2_mode', lang)}: {wt('wave2_mode_guided', lang) if mode == 'guided' else wt('wave2_mode_standard', lang)}")
# ---------------------------------------------------------------------------
# scaffold / revise / result steps
# ---------------------------------------------------------------------------

def _render_scaffold_step(gateway: Wave2Gateway, learner_id: str, lang: str) -> None:
    scaffold_view = st.session_state.get(W2_SCAFFOLD) or {}
    category = st.session_state.get(W2_SCAFFOLD_CATEGORY, "")
    section_header("wave2_scaffold_section", lang=lang)
    if not scaffold_view.get("available", True):
        warning_box("wave2_scaffold_unavailable", lang)
    else:
        level = int(scaffold_view.get("level") or 1)
        content = scaffold_view.get("content") or {}
        st.markdown(
            f"**{_category_label(category, lang)}** · "
            f"{wt('wave2_scaffold_level', lang)} {level} / 7"
        )
        with st.container(border=True, key="wave2_scaffold_content"):
            st.markdown(content.get("text", ""))
            st.markdown(f"**{wt('wave2_scaffold_action', lang)}**: {scaffold_view.get('learner_action', '')}")
        limitation_notice(f" {scaffold_view.get('never_writes_statement', '')}", lang)
        if level < 7:
            if st.button(wt("wave2_scaffold_next", lang), key="wave2_scaffold_next",
                         use_container_width=True):
                try:
                    scaffold_view = gateway.scaffold(learner_id, category, level=level + 1)
                    st.session_state[W2_SCAFFOLD] = scaffold_view
                except (Wave2ApiClientError, Wave2ApiUnavailable) as exc:
                    render_api_error(exc, lang)
        else:
            info_box("wave2_scaffold_last", lang)
    if st.button(wt("wave2_scaffold_done", lang), key="wave2_scaffold_done",
                 use_container_width=True, type="primary"):
        _go("revise")


def _render_revise_step(gateway: Wave2Gateway, learner_id: str, lang: str) -> None:
    task = st.session_state.get(W2_TASK) or {}
    last_text = st.session_state.get(W2_LAST_TEXT, "")
    feedback = st.session_state.get(W2_FEEDBACK) or {}
    categories = [_category_label(item.get("category", ""), lang)
                  for item in (feedback.get("items") or [])]
    student_context_block([
        ("writing_prompt", task.get("writing_prompt", "")),
        ("wave2_revise_targets", " · ".join(categories) if categories else "-"),
    ], lang)
    section_header("wave2_revise_section", lang=lang)
    info_box("wave2_revise_help", lang)
    revised_text = st.text_area(
        wt("wave2_revise_input_label", lang), key="wave2_revise_input",
        value=last_text, height=260,
    )
    if st.button(wt("wave2_submit_revision", lang), key="wave2_submit_revision",
                 use_container_width=True, type="primary"):
        if not revised_text.strip():
            field_error("wave2_need_text", lang)
            return
        version = st.session_state.get(W2_VERSION) or {}
        try:
            outcome = gateway.submit_revision(
                task, int(version.get("submission_id") or 0),
                revised_text.strip(), learner_id, "revised draft",
            )
        except (Wave2ApiClientError, Wave2ApiUnavailable) as exc:
            render_api_error(exc, lang)
            return
        st.session_state[W2_VERSION] = outcome["version"]
        st.session_state[W2_OBSERVATION] = outcome["observation"]
        st.session_state[W2_LAST_TEXT] = revised_text.strip()
        st.session_state[W2_MODE] = outcome["mode"]
        _go("result")


def _render_result_step(gateway: Wave2Gateway, learner_id: str, lang: str) -> None:
    observation = st.session_state.get(W2_OBSERVATION) or {}
    mode = st.session_state.get(W2_MODE, gateway.mode())
    section_header("wave2_result_section", lang=lang)
    success_box("wave2_result_received", lang)
    if not observation or observation.get("available") is False:
        info_box("wave2_result_standard_note", lang)
    else:
        if observation.get("what_changed_summary"):
            st.markdown(f"**{wt('wave2_result_changed', lang)}**: {observation['what_changed_summary']}")
        addressed = observation.get("addressed") or []
        remaining = observation.get("remaining") or []
        new_observations = observation.get("new_observations") or []
        if addressed:
            st.markdown(f"**{wt('wave2_result_addressed', lang)}**")
            for entry in addressed:
                st.markdown(f"- {_category_label(entry.get('category', ''), lang)}")
        if remaining:
            st.markdown(f"**{wt('wave2_result_remaining', lang)}**")
            for entry in remaining:
                st.markdown(f"- {_category_label(entry.get('category', ''), lang)}")
        if new_observations:
            st.markdown(f"**{wt('wave2_result_new', lang)}**")
            for entry in new_observations:
                st.markdown(f"- {_category_label(entry.get('category', ''), lang)}")
        if observation.get("no_intent_inference"):
            technical_caption(observation["no_intent_inference"])
        if mode == "guided":
            try:
                longitudinal = gateway.longitudinal(learner_id)
            except (Wave2ApiClientError, Wave2ApiUnavailable):
                longitudinal = {}
            stable_items = longitudinal.get("stable") or []
            if stable_items:
                section_header("wave2_feedback_stable_section", lang=lang)
                for entry in stable_items:
                    st.markdown(f"- {entry.get('label', '')}")
    with st.container(border=True, key="wave2_result_actions"):
        if st.button(wt("wave2_go_history", lang), key="wave2_result_history",
                     use_container_width=True, type="primary"):
            _navigate_student_page("student_wave2_history_title", lang)
        if st.button(wt("wave2_result_keep_revising", lang), key="wave2_result_revise",
                     use_container_width=True):
            _go("revise")
        if st.button(wt("wave2_result_new_task", lang), key="wave2_result_new",
                     use_container_width=True):
            _reset_wave2_state()
    limitation_notice("wave2_boundary", lang)


def render_wave2_studio_page(gateway: Wave2Gateway, lang: str) -> None:
    """Entry point: the Wave-2 Student Writing Studio journey."""
    student_page_intro("student_wave2_studio_title", "student_wave2_studio_subtitle", lang)

    learner_id = student_id_input(
        "student_id", "wave2_student", lang, placeholder_key="student_id_placeholder"
    )
    set_selected_learner(learner_id)
    learner_id = learner_id.strip()
    if not learner_id:
        student_action_block(
            "wave2_start_new", "wave2_enter_id", lang, state="blocked",
        )
        limitation_notice("wave2_boundary", lang)
        return
    student_context_block([("student_context_learner", learner_id)], lang)

    step = st.session_state.get(W2_STEP)
    if step is None:
        _render_start(learner_id, lang)
    elif step == "task":
        _render_task_step(learner_id, lang)
    elif step == "prompt":
        _render_prompt_step(gateway, learner_id, lang)
    elif step == "compose":
        _render_compose_step(gateway, learner_id, lang)
    elif step == "feedback":
        _render_feedback_step(gateway, learner_id, lang)
    elif step == "scaffold":
        _render_scaffold_step(gateway, learner_id, lang)
    elif step == "revise":
        _render_revise_step(gateway, learner_id, lang)
    elif step == "result":
        _render_result_step(gateway, learner_id, lang)
    else:
        _reset_wave2_state()


__all__ = ["render_wave2_studio_page"]
